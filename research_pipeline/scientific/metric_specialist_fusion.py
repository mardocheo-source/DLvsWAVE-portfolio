#!/usr/bin/env python3
"""Fuse V14 timing systems with an overall core and metric specialists."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common_v14 import (
    SYSTEMS,
    internal_local_maxima,
    score_quality,
    tied_percentile,
    write_json,
)


DEFAULT_METRICS = {
    "event_rank": ("event_percentile_skill", 0.10),
    "near_peak_alignment": ("near_peak_alignment_skill", 0.08),
    "local_prominence": ("local_prominence_skill", 0.09),
    "delayed_false_peak_control": ("delayed_false_peak_control", 0.08),
    "peak_persistence": ("peak_persistence_skill", 0.07),
    "false_peak_control": ("false_peak_control", 0.10),
    "background_brier": ("brier_skill", 0.08),
    "hard_negative_rejection": (
        "derived.hard_negative_rejection_skill",
        0.14,
    ),
    "event_control_margin": (
        "derived.event_control_margin_skill",
        0.17,
    ),
    "background_separation": (
        "derived.background_separation_skill",
        0.09,
    ),
}

FALSE_POSITIVE_METRIC_KEYS = {
    "derived.hard_negative_rejection_skill",
    "derived.event_control_margin_skill",
    "derived.background_separation_skill",
    "false_peak_control",
    "delayed_false_peak_control",
    "brier_skill",
}

VALIDATION_FRAME_CACHE: dict[Path, pd.DataFrame] = {}


def cached_validation_frame(path: Path) -> pd.DataFrame:
    resolved = path.resolve()
    if resolved not in VALIDATION_FRAME_CACHE:
        VALIDATION_FRAME_CACHE[resolved] = pd.read_csv(resolved)
    return VALIDATION_FRAME_CACHE[resolved]


def load_metrics(path: Path | None) -> dict[str, tuple[str, float]]:
    if path is None:
        return dict(DEFAULT_METRICS)
    payload = json.loads(path.expanduser().resolve().read_text())
    rows = payload.get("metrics")
    if not isinstance(rows, dict) or not rows:
        raise ValueError("Metric configuration must contain a non-empty metrics object")
    metrics: dict[str, tuple[str, float]] = {}
    for label, row in rows.items():
        metric_key = str(row["metric_key"])
        importance = float(row["importance"])
        if importance <= 0:
            raise ValueError(f"Metric importance must be positive: {label}")
        metrics[str(label)] = (metric_key, importance)
    return metrics


def normalize_weights(values: dict[str, float]) -> dict[str, float]:
    total = float(sum(max(0.0, value) for value in values.values()))
    if total <= 0:
        return {name: 1.0 / len(values) for name in values}
    return {name: max(0.0, value) / total for name, value in values.items()}


def false_positive_fold_metrics(
    frame: pd.DataFrame,
    score: np.ndarray,
    raw_score: np.ndarray,
    margin_scale: float,
    minimum_margin: float,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Measure target/control separation while retaining other real events."""
    actual = frame["actual"].to_numpy(int)
    event_indices = np.flatnonzero(actual == 1)
    hard_mask = (
        frame.get("hard_negative_control", pd.Series(0, index=frame.index))
        .fillna(0)
        .to_numpy(int)
        == 1
    )
    control_indices = np.flatnonzero(hard_mask)
    if target_date is None:
        if len(event_indices) != 1:
            raise ValueError(
                "target_date is required when a timing validation fold contains "
                "multiple real events"
            )
        event_index = int(event_indices[0])
    else:
        dates = frame["date"].astype(str).str.slice(0, 10).to_numpy()
        matches = np.flatnonzero((actual == 1) & (dates == str(target_date)[:10]))
        if len(matches) != 1:
            raise ValueError(
                f"Validation target {target_date} must resolve to exactly one "
                f"positive row; found {len(matches)}"
            )
        event_index = int(matches[0])
    if not len(control_indices):
        raise ValueError(
            "False-positive-aware fusion requires at least one configured "
            "hard-negative control in every fold"
        )
    event_score = float(score[event_index])
    event_raw = float(raw_score[event_index])
    hardest_control_index = int(
        control_indices[np.argmax(raw_score[control_indices])]
    )
    hardest_control_score = float(score[hardest_control_index])
    hardest_control_raw = float(raw_score[hardest_control_index])
    calibrated_margin = event_score - hardest_control_score
    raw_margin = event_raw - hardest_control_raw
    score_ranks = tied_percentile(score)
    control_rank = float(np.max(score_ranks[control_indices]))
    normal_negative = (actual == 0) & ~hard_mask
    if np.any(normal_negative):
        background_separation = float(
            np.mean(raw_score[normal_negative] <= event_raw - minimum_margin)
        )
        background_score_mean = float(np.mean(score[normal_negative]))
        background_raw_mean = float(np.mean(raw_score[normal_negative]))
    else:
        background_separation = 1.0
        background_score_mean = 0.0
        background_raw_mean = 0.0
    margin_skill = float(
        np.clip(0.5 + raw_margin / (2.0 * margin_scale), 0.0, 1.0)
    )
    hard_negative_rejection = float(1.0 - control_rank)
    false_positive_skill = float(
        0.50 * margin_skill
        + 0.30 * hard_negative_rejection
        + 0.20 * background_separation
    )
    return {
        "event_index": event_index,
        "known_event_count_in_fold": int(len(event_indices)),
        "hardest_control_index": hardest_control_index,
        "event_score": event_score,
        "event_raw_score": event_raw,
        "hardest_control_score": hardest_control_score,
        "hardest_control_raw_score": hardest_control_raw,
        "event_control_margin_calibrated": calibrated_margin,
        "event_control_margin_raw": raw_margin,
        "event_control_margin_skill": margin_skill,
        "hard_negative_rank_percentile": control_rank,
        "hard_negative_rejection_skill": hard_negative_rejection,
        "background_separation_skill": background_separation,
        "background_score_mean": background_score_mean,
        "background_raw_score_mean": background_raw_mean,
        "hard_negatives_below_event": bool(raw_margin >= minimum_margin),
        "minimum_required_raw_margin": minimum_margin,
        "false_positive_skill": false_positive_skill,
    }


def read_system_evidence(
    run_dir: Path,
    metrics: dict[str, tuple[str, float]],
    margin_scale: float,
    minimum_margin: float,
) -> tuple[list[Path], dict[str, Any]]:
    model_root = run_dir / "04_models/timing"
    steps = sorted(
        path
        for path in model_root.iterdir()
        if path.is_dir()
        and len(path.name) > 3
        and path.name[:2].isdigit()
        and path.name[2] == "_"
    )
    if len(steps) < 2:
        raise ValueError(
            f"Expected at least two outer timing steps, found {len(steps)}"
        )
    evidence: dict[str, Any] = {}
    for system in SYSTEMS:
        summaries = [
            json.loads((step / system / "summary.json").read_text())
            for step in steps
        ]
        overall_folds = [
            float(summary["origin_quality_25train_75validation"])
            for summary in summaries
        ]
        validation_quality = [
            float(summary["validation_metrics"]["quality_higher_is_better"])
            for summary in summaries
        ]
        predictions = [
            pd.read_csv(step / system / "validation_predictions.csv")
            for step in steps
        ]
        derived_folds = [
            false_positive_fold_metrics(
                frame,
                frame["score_percentile_not_probability"].to_numpy(float),
                frame["raw_score"].to_numpy(float),
                margin_scale,
                minimum_margin,
                target_date=step.name.split("_", 2)[1],
            )
            for step, frame in zip(steps, predictions)
        ]
        metric_rows: dict[str, dict[str, float]] = {}
        for label, (key, _) in metrics.items():
            if key.startswith("derived."):
                derived_key = key.removeprefix("derived.")
                values = [float(row[derived_key]) for row in derived_folds]
            else:
                values = [
                    float(summary["validation_metrics"].get(key, 0.0))
                    for summary in summaries
                ]
            metric_rows[label] = {
                "mean": float(np.mean(values)),
                "worst": float(np.min(values)),
                "robust": float(0.80 * np.mean(values) + 0.20 * np.min(values)),
            }
        evidence[system] = {
            "overall_quality_mean": float(np.mean(overall_folds)),
            "overall_quality_worst": float(np.min(overall_folds)),
            "validation_quality_mean": float(np.mean(validation_quality)),
            "validation_quality_worst": float(np.min(validation_quality)),
            "validation_quality_folds": validation_quality,
            "false_positive_folds": derived_folds,
            "hard_negative_below_event_count": int(
                sum(row["hard_negatives_below_event"] for row in derived_folds)
            ),
            "false_positive_quality_mean": float(
                np.mean([row["false_positive_skill"] for row in derived_folds])
            ),
            "false_positive_quality_worst": float(
                np.min([row["false_positive_skill"] for row in derived_folds])
            ),
            "metrics": metric_rows,
        }
    return steps, evidence


def build_portfolios(
    evidence: dict[str, Any],
    metrics: dict[str, tuple[str, float]],
    minimum_specialist_overall: float,
    top_n: int,
    portfolio_overall_weight: float,
) -> dict[str, Any]:
    eligible = [
        system
        for system, row in evidence.items()
        if row["overall_quality_mean"] >= minimum_specialist_overall
    ]
    portfolios: dict[str, Any] = {}
    for label, (_, importance) in metrics.items():
        ranked = sorted(
            eligible,
            key=lambda system: (
                evidence[system]["metrics"][label]["robust"],
                evidence[system]["overall_quality_mean"],
            ),
            reverse=True,
        )
        selected = ranked[:top_n]
        raw = {
            system: (
                portfolio_overall_weight
                * evidence[system]["overall_quality_mean"]
                + (1.0 - portfolio_overall_weight)
                * evidence[system]["metrics"][label]["robust"]
            )
            for system in selected
        }
        weights = normalize_weights(raw)
        best_metric = max(
            evidence[system]["metrics"][label]["robust"] for system in selected
        )
        portfolios[label] = {
            "metric_key": metrics[label][0],
            "importance": importance,
            "systems": selected,
            "weights": weights,
            "reliability": float(importance * best_metric),
        }
    return portfolios


def core_weights(
    evidence: dict[str, Any],
    minimum_core_overall: float,
    maximum_core_systems: int,
) -> tuple[dict[str, float], bool]:
    ranked = sorted(
        evidence,
        key=lambda system: evidence[system]["overall_quality_mean"],
        reverse=True,
    )
    accepted = [
        system
        for system in ranked
        if evidence[system]["overall_quality_mean"] >= minimum_core_overall
    ][:maximum_core_systems]
    fallback = False
    if not accepted:
        accepted = ranked[: min(3, len(ranked))]
        fallback = True
    best = max(evidence[system]["overall_quality_mean"] for system in accepted)
    raw = {
        system: math.exp(
            (evidence[system]["overall_quality_mean"] - best) / 0.08
        )
        + 0.05
        for system in accepted
    }
    return normalize_weights(raw), fallback


def specialist_weights(
    portfolios: dict[str, Any],
    included_metrics: list[str],
    metric_reliability_override: dict[str, float] | None = None,
) -> dict[str, float]:
    reliability = normalize_weights(
        metric_reliability_override
        if metric_reliability_override is not None
        else {
            label: portfolios[label]["reliability"]
            for label in included_metrics
        }
    )
    aggregate: dict[str, float] = defaultdict(float)
    for label in included_metrics:
        for system, weight in portfolios[label]["weights"].items():
            aggregate[system] += reliability[label] * weight
    return normalize_weights(dict(aggregate))


def final_system_weights(
    core: dict[str, float],
    specialist: dict[str, float],
    core_share: float,
) -> dict[str, float]:
    names = sorted(set(core).union(specialist))
    return normalize_weights(
        {
            system: (
                core_share * core.get(system, 0.0)
                + (1.0 - core_share) * specialist.get(system, 0.0)
            )
            for system in names
        }
    )


def contribution_trace(
    selected: dict[str, Any],
    core: dict[str, float],
    portfolios: dict[str, Any],
    evidence: dict[str, Any],
    portfolio_overall_weight: float,
) -> dict[str, Any]:
    """Decompose every final system weight into core and per-metric pieces."""
    core_share = float(selected["core_share"])
    specialist_share = 1.0 - core_share
    included_metrics = list(selected["included_metrics"])
    normalized_metric_reliability = normalize_weights(
        selected.get("metric_reliability_weights")
        or {
            label: float(portfolios[label]["reliability"])
            for label in included_metrics
        }
    )
    core_components = []
    system_components: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"core": 0.0, "metrics": defaultdict(float)}
    )
    for system, weight in core.items():
        final_contribution = core_share * float(weight)
        system_components[system]["core"] = final_contribution
        core_components.append(
            {
                "system": system,
                "within_core_weight": float(weight),
                "overall_quality_mean": float(
                    evidence[system]["overall_quality_mean"]
                ),
                "final_fusion_contribution": final_contribution,
            }
        )

    metric_components = []
    for label in included_metrics:
        portfolio = portfolios[label]
        normalized_share = float(normalized_metric_reliability[label])
        final_metric_share = specialist_share * normalized_share
        systems = []
        for system, weight in portfolio["weights"].items():
            final_contribution = final_metric_share * float(weight)
            system_components[system]["metrics"][label] = final_contribution
            systems.append(
                {
                    "system": system,
                    "within_metric_weight": float(weight),
                    "metric_robust_quality": float(
                        evidence[system]["metrics"][label]["robust"]
                    ),
                    "overall_quality_mean": float(
                        evidence[system]["overall_quality_mean"]
                    ),
                    "final_fusion_contribution": final_contribution,
                }
            )
        metric_components.append(
            {
                "metric": label,
                "metric_key": portfolio["metric_key"],
                "nominal_importance": float(portfolio["importance"]),
                "reliability": float(portfolio["reliability"]),
                "normalized_share_within_specialists": normalized_share,
                "final_fusion_share": final_metric_share,
                "systems": systems,
            }
        )

    expected_weights = selected["system_weights"]
    system_totals = []
    for system in sorted(expected_weights):
        core_contribution = float(system_components[system]["core"])
        metric_contributions = {
            label: float(value)
            for label, value in system_components[system]["metrics"].items()
        }
        specialist_contribution = float(sum(metric_contributions.values()))
        reconstructed = core_contribution + specialist_contribution
        expected = float(expected_weights[system])
        system_totals.append(
            {
                "system": system,
                "core_contribution": core_contribution,
                "metric_contributions": metric_contributions,
                "specialist_contribution": specialist_contribution,
                "reconstructed_final_weight": reconstructed,
                "expected_final_weight": expected,
                "absolute_reconstruction_error": abs(reconstructed - expected),
            }
        )
    maximum_error = max(
        row["absolute_reconstruction_error"] for row in system_totals
    )
    return {
        "schema": "v14.metric_specialist_contribution_trace.v1",
        "generated_from": (
            "metric portfolios, reliability, core weights and selected trial; "
            "no report values are hardcoded"
        ),
        "selected_trial_id": int(selected["trial_id"]),
        "selected_metric_set": selected["metric_set"],
        "included_metrics": included_metrics,
        "fusion_formula": (
            "final_system_weight = core_share * within_core_weight + "
            "specialist_share * sum(normalized_metric_reliability * "
            "within_metric_weight)"
        ),
        "core_share": core_share,
        "specialist_share": specialist_share,
        "portfolio_overall_quality_share": portfolio_overall_weight,
        "portfolio_metric_quality_share": 1.0 - portfolio_overall_weight,
        "core_components": core_components,
        "metric_components": metric_components,
        "system_totals": system_totals,
        "checks": {
            "core_component_sum": float(
                sum(row["final_fusion_contribution"] for row in core_components)
            ),
            "metric_component_sum": float(
                sum(row["final_fusion_share"] for row in metric_components)
            ),
            "final_system_weight_sum": float(sum(expected_weights.values())),
            "maximum_absolute_reconstruction_error": maximum_error,
            "weights_reconstructed": bool(maximum_error <= 1e-12),
        },
    }


def direct_system_contribution_trace(
    selected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    systems = [
        {
            "system": system,
            "within_metric_weight": float(weight),
            "metric_robust_quality": float(
                evidence[system]["false_positive_quality_worst"]
            ),
            "overall_quality_mean": float(
                evidence[system]["overall_quality_mean"]
            ),
            "final_fusion_contribution": float(weight),
        }
        for system, weight in sorted(
            selected["system_weights"].items(),
            key=lambda row: row[1],
            reverse=True,
        )
    ]
    system_totals = [
        {
            "system": row["system"],
            "core_contribution": 0.0,
            "metric_contributions": {
                "false_positive_aware_direct_search": row[
                    "final_fusion_contribution"
                ]
            },
            "specialist_contribution": row["final_fusion_contribution"],
            "reconstructed_final_weight": row["final_fusion_contribution"],
            "expected_final_weight": row["final_fusion_contribution"],
            "absolute_reconstruction_error": 0.0,
        }
        for row in systems
    ]
    return {
        "schema": "v14.metric_specialist_contribution_trace.v1",
        "generated_from": (
            "seeded false-positive-aware direct-system search; no report "
            "values or model names are hardcoded"
        ),
        "selected_trial_id": int(selected["trial_id"]),
        "selected_metric_set": selected["metric_set"],
        "included_metrics": ["false_positive_aware_direct_search"],
        "fusion_formula": "final_system_weight = selected direct-system weight",
        "core_share": 0.0,
        "specialist_share": 1.0,
        "portfolio_overall_quality_share": None,
        "portfolio_metric_quality_share": None,
        "core_components": [],
        "metric_components": [
            {
                "metric": "false_positive_aware_direct_search",
                "metric_key": "multi_metric_validation_objective",
                "nominal_importance": 1.0,
                "reliability": float(selected["selection_objective"]),
                "normalized_share_within_specialists": 1.0,
                "final_fusion_share": 1.0,
                "systems": systems,
            }
        ],
        "system_totals": system_totals,
        "checks": {
            "core_component_sum": 0.0,
            "metric_component_sum": 1.0,
            "final_system_weight_sum": float(
                sum(selected["system_weights"].values())
            ),
            "maximum_absolute_reconstruction_error": 0.0,
            "weights_reconstructed": True,
        },
    }


def direct_system_candidate_pool(
    evidence: dict[str, Any],
    per_criterion: int,
) -> list[str]:
    """Select a model-name-agnostic union of complementary specialists."""
    criteria = [
        lambda row: row["overall_quality_mean"],
        lambda row: row["validation_quality_mean"],
        lambda row: row["validation_quality_worst"],
        lambda row: row["false_positive_quality_mean"],
        lambda row: row["false_positive_quality_worst"],
    ]
    fold_count = len(next(iter(evidence.values()))["validation_quality_folds"])
    for fold_index in range(fold_count):
        criteria.extend(
            [
                lambda row, index=fold_index: row["validation_quality_folds"][
                    index
                ],
                lambda row, index=fold_index: row["false_positive_folds"][
                    index
                ]["event_control_margin_skill"],
                lambda row, index=fold_index: row["false_positive_folds"][
                    index
                ]["hard_negative_rejection_skill"],
            ]
        )
    selected: set[str] = set()
    for criterion in criteria:
        selected.update(
            sorted(
                evidence,
                key=lambda system: (
                    criterion(evidence[system]),
                    evidence[system]["overall_quality_mean"],
                ),
                reverse=True,
            )[:per_criterion]
        )
    return sorted(selected)


def validation_scores(
    steps: list[Path],
    weights: dict[str, float],
    event_radius: int,
    margin_scale: float,
    minimum_margin: float,
    include_frames: bool = False,
) -> tuple[list[dict[str, Any]], list[np.ndarray], list[pd.DataFrame]]:
    folds: list[dict[str, Any]] = []
    scores: list[np.ndarray] = []
    frames: list[pd.DataFrame] = []
    for step in steps:
        system_rows = {
            system: cached_validation_frame(
                step / system / "validation_predictions.csv"
            )
            for system in weights
        }
        reference = next(iter(system_rows.values()))
        score = sum(
            weight
            * system_rows[system]["score_percentile_not_probability"].to_numpy(float)
            for system, weight in weights.items()
        )
        raw_score = sum(
            weight * system_rows[system]["raw_score"].to_numpy(float)
            for system, weight in weights.items()
        )
        actual = reference["actual"].to_numpy(int)
        metrics = score_quality(
            actual, score, np.arange(len(score), dtype=int), event_radius
        )
        target_date = step.name.split("_", 2)[1]
        target_matches = np.flatnonzero(
            (actual == 1)
            & (
                reference["date"]
                .astype(str)
                .str.slice(0, 10)
                .to_numpy()
                == target_date
            )
        )
        if len(target_matches) != 1:
            raise ValueError(
                f"Validation target {target_date} must resolve to exactly one "
                f"positive row; found {len(target_matches)}"
            )
        target_index = int(target_matches[0])
        profile_matches = [
            row
            for row in metrics["event_profiles"]
            if int(row["event_global_index"]) == target_index
        ]
        if len(profile_matches) != 1:
            raise ValueError(
                f"No unique score-quality profile for target {target_date}"
            )
        profile = profile_matches[0]
        false_positive = false_positive_fold_metrics(
            reference,
            score,
            raw_score,
            margin_scale,
            minimum_margin,
            target_date=target_date,
        )
        folds.append(
            {
                "step": step.name,
                "quality_higher_is_better": metrics["quality_higher_is_better"],
                "strict_local_peak": bool(profile["strict_local_peak"]),
                "event_percentile_skill": profile["event_percentile_skill"],
                "argmax_offset_slots": profile["argmax_offset_slots"],
                "weak_peak_retention_skill": profile["weak_peak_retention_skill"],
                "delayed_false_peak_control": profile[
                    "delayed_false_peak_control"
                ],
                "false_positive": false_positive,
                "metrics": metrics,
            }
        )
        scores.append(score)
        if include_frames:
            selected_frame = reference.copy()
            selected_frame.insert(0, "step", step.name)
            selected_frame["selected_raw_score"] = raw_score
            selected_frame["selected_score_not_probability"] = score
            selected_frame["selected_is_internal_local_peak"] = (
                internal_local_maxima(score).astype(int)
            )
            for key, value in false_positive.items():
                if key not in {"event_index", "hardest_control_index"}:
                    selected_frame[f"fold_{key}"] = value
            frames.append(selected_frame)
    return folds, scores, frames


def candidate_metric_sets(portfolios: dict[str, Any]) -> list[tuple[str, list[str]]]:
    labels = list(portfolios)
    ordered = sorted(
        labels,
        key=lambda label: portfolios[label]["reliability"],
        reverse=True,
    )
    candidates: list[tuple[str, list[str]]] = [("all_metrics", labels)]
    candidates.extend(
        (f"without_{excluded}", [label for label in labels if label != excluded])
        for excluded in labels
    )
    candidates.append(("top4_reliable_metrics", ordered[:4]))
    false_positive = [
        label
        for label in labels
        if portfolios[label]["metric_key"] in FALSE_POSITIVE_METRIC_KEYS
    ]
    if false_positive:
        candidates.append(("false_positive_metrics", false_positive))
    candidates.extend((f"only_{label}", [label]) for label in labels)
    unique: list[tuple[str, list[str]]] = []
    seen: set[tuple[str, ...]] = set()
    for name, included in candidates:
        fingerprint = tuple(sorted(included))
        if included and fingerprint not in seen:
            unique.append((name, included))
            seen.add(fingerprint)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--minimum-core-overall", type=float, default=0.65)
    parser.add_argument("--minimum-specialist-overall", type=float, default=0.55)
    parser.add_argument("--maximum-core-systems", type=int, default=5)
    parser.add_argument("--specialists-per-metric", type=int, default=2)
    parser.add_argument("--event-radius", type=int, default=6)
    parser.add_argument(
        "--interval-days",
        type=int,
        default=None,
        help="Forecast interval length; defaults to run_manifest.json.",
    )
    parser.add_argument(
        "--metric-config-json",
        type=Path,
        default=None,
        help=(
            "Optional JSON defining metric keys and importance weights. "
            "Built-in defaults are used only when omitted."
        ),
    )
    parser.add_argument(
        "--portfolio-overall-weight",
        type=float,
        default=0.65,
        help=(
            "Overall-quality share inside each metric portfolio; the remaining "
            "share is the robust metric-specific quality."
        ),
    )
    parser.add_argument(
        "--candidate-core-shares",
        default="0.00,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90",
        help="Comma-separated overall-core shares tested by fusion ablation.",
    )
    parser.add_argument(
        "--selection-mean-weight",
        type=float,
        default=0.80,
        help="Mean-fold share in the fusion selection objective.",
    )
    parser.add_argument(
        "--selection-quality-weight",
        type=float,
        default=0.35,
        help="Overall timing-quality share in the final trial objective.",
    )
    parser.add_argument(
        "--selection-false-positive-weight",
        type=float,
        default=0.55,
        help="Hard-negative/background separation share in the trial objective.",
    )
    parser.add_argument(
        "--selection-exact-peak-weight",
        type=float,
        default=0.10,
        help="Exact held-out peak share in the trial objective.",
    )
    parser.add_argument(
        "--false-positive-mean-weight",
        type=float,
        default=0.50,
        help="Mean-fold share inside the false-positive objective.",
    )
    parser.add_argument(
        "--event-control-margin-scale",
        type=float,
        default=0.20,
        help="Raw-score margin mapped to a full [0,1] margin skill span.",
    )
    parser.add_argument(
        "--minimum-event-control-margin",
        type=float,
        default=0.0,
        help="Minimum raw event-minus-control margin required in every fold.",
    )
    parser.add_argument(
        "--require-controls-below-event",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Restrict selection to trials whose real-event raw score is above "
            "the hard negative in every fold when any such trial exists."
        ),
    )
    parser.add_argument(
        "--random-metric-mix-trials",
        type=int,
        default=0,
        help=(
            "Additional seeded Dirichlet mixtures of metric portfolios; zero "
            "keeps only the structured ablation grid."
        ),
    )
    parser.add_argument(
        "--random-metric-mix-seed",
        type=int,
        default=581449,
    )
    parser.add_argument(
        "--random-metric-concentration",
        type=float,
        default=8.0,
        help="Dirichlet concentration around configured metric importances.",
    )
    parser.add_argument(
        "--direct-system-mix-trials",
        type=int,
        default=0,
        help=(
            "Additional seeded sparse system mixtures selected by the same "
            "multi-metric objective. An exhaustive pair grid is also evaluated."
        ),
    )
    parser.add_argument("--direct-system-mix-seed", type=int, default=581453)
    parser.add_argument(
        "--direct-system-pool-per-criterion",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--direct-system-maximum-members",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--minimum-fusion-validation-mean",
        type=float,
        default=0.70,
    )
    parser.add_argument(
        "--minimum-fusion-validation-worst",
        type=float,
        default=0.65,
    )
    args = parser.parse_args()
    if not 0.0 <= args.portfolio_overall_weight <= 1.0:
        parser.error("--portfolio-overall-weight must be in [0, 1]")
    if not 0.0 <= args.selection_mean_weight <= 1.0:
        parser.error("--selection-mean-weight must be in [0, 1]")
    objective_weights = np.asarray(
        [
            args.selection_quality_weight,
            args.selection_false_positive_weight,
            args.selection_exact_peak_weight,
        ],
        float,
    )
    if np.any(objective_weights < 0) or not np.isclose(objective_weights.sum(), 1.0):
        parser.error(
            "selection quality/false-positive/exact-peak weights must be "
            "non-negative and sum to 1"
        )
    if not 0.0 <= args.false_positive_mean_weight <= 1.0:
        parser.error("--false-positive-mean-weight must be in [0, 1]")
    if args.event_control_margin_scale <= 0:
        parser.error("--event-control-margin-scale must be positive")
    if args.random_metric_mix_trials < 0:
        parser.error("--random-metric-mix-trials cannot be negative")
    if args.random_metric_concentration <= 0:
        parser.error("--random-metric-concentration must be positive")
    if args.direct_system_mix_trials < 0:
        parser.error("--direct-system-mix-trials cannot be negative")
    if args.direct_system_pool_per_criterion < 1:
        parser.error("--direct-system-pool-per-criterion must be positive")
    if args.direct_system_maximum_members < 2:
        parser.error("--direct-system-maximum-members must be at least two")
    candidate_core_shares = [
        float(value.strip())
        for value in args.candidate_core_shares.split(",")
        if value.strip()
    ]
    if not candidate_core_shares or any(
        not 0.0 <= value <= 1.0 for value in candidate_core_shares
    ):
        parser.error("--candidate-core-shares must contain values in [0, 1]")

    run_dir = args.run_dir.resolve()
    if args.interval_days is None:
        manifest = json.loads((run_dir / "00_config/run_manifest.json").read_text())
        interval_days = int(manifest["parameters"]["interval_days"])
    else:
        interval_days = int(args.interval_days)
    if interval_days < 1:
        parser.error("--interval-days must be positive")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metric_definitions = load_metrics(args.metric_config_json)
    steps, evidence = read_system_evidence(
        run_dir,
        metric_definitions,
        args.event_control_margin_scale,
        args.minimum_event_control_margin,
    )
    core, core_fallback = core_weights(
        evidence, args.minimum_core_overall, args.maximum_core_systems
    )
    portfolios = build_portfolios(
        evidence,
        metric_definitions,
        args.minimum_specialist_overall,
        args.specialists_per_metric,
        args.portfolio_overall_weight,
    )

    trials: list[dict[str, Any]] = []
    trial_id = 0
    def evaluate_candidate(
        candidate_family: str,
        core_share: float,
        metric_set_name: str,
        included_metrics: list[str],
        metric_mix: dict[str, float] | None = None,
        direct_weights: dict[str, float] | None = None,
    ) -> None:
        nonlocal trial_id
        trial_id += 1
        if direct_weights is None:
            specialist = specialist_weights(
                portfolios,
                included_metrics,
                metric_mix,
            )
            weights = final_system_weights(core, specialist, core_share)
        else:
            weights = normalize_weights(direct_weights)
        folds, _, _ = validation_scores(
            steps,
            weights,
            args.event_radius,
            args.event_control_margin_scale,
            args.minimum_event_control_margin,
        )
        qualities = np.asarray(
            [fold["quality_higher_is_better"] for fold in folds], float
        )
        false_positive_qualities = np.asarray(
            [fold["false_positive"]["false_positive_skill"] for fold in folds],
            float,
        )
        general_objective = float(
            args.selection_mean_weight * qualities.mean()
            + (1.0 - args.selection_mean_weight) * qualities.min()
        )
        false_positive_objective = float(
            args.false_positive_mean_weight * false_positive_qualities.mean()
            + (1.0 - args.false_positive_mean_weight)
            * false_positive_qualities.min()
        )
        exact_peak_count = int(
            sum(fold["strict_local_peak"] for fold in folds)
        )
        hard_negative_below_event_count = int(
            sum(
                fold["false_positive"]["hard_negatives_below_event"]
                for fold in folds
            )
        )
        metric_weights = (
            {}
            if direct_weights is not None
            else normalize_weights(
                metric_mix
                if metric_mix is not None
                else {
                    label: portfolios[label]["reliability"]
                    for label in included_metrics
                }
            )
        )
        trials.append(
            {
                "trial_id": trial_id,
                "candidate_family": candidate_family,
                "core_share": core_share,
                "metric_set": metric_set_name,
                "included_metrics": included_metrics,
                "metric_reliability_weights": metric_weights,
                "validation_quality_mean": float(qualities.mean()),
                "validation_quality_worst": float(qualities.min()),
                "exact_peak_count": exact_peak_count,
                "hard_negative_below_event_count": (
                    hard_negative_below_event_count
                ),
                "false_positive_quality_mean": float(
                    false_positive_qualities.mean()
                ),
                "false_positive_quality_worst": float(
                    false_positive_qualities.min()
                ),
                "general_quality_objective": general_objective,
                "false_positive_objective": false_positive_objective,
                "selection_objective": float(
                    args.selection_quality_weight * general_objective
                    + args.selection_false_positive_weight
                    * false_positive_objective
                    + args.selection_exact_peak_weight
                    * (exact_peak_count / len(folds))
                ),
                "system_weights": weights,
                "folds": folds,
            }
        )

    for core_share in candidate_core_shares:
        for metric_set_name, included_metrics in candidate_metric_sets(portfolios):
            evaluate_candidate(
                "structured_ablation",
                core_share,
                metric_set_name,
                included_metrics,
            )

    if args.random_metric_mix_trials:
        rng = np.random.default_rng(args.random_metric_mix_seed)
        all_metrics = list(portfolios)
        false_positive_metrics = [
            label
            for label in all_metrics
            if portfolios[label]["metric_key"] in FALSE_POSITIVE_METRIC_KEYS
        ]
        for random_id in range(args.random_metric_mix_trials):
            included_metrics = (
                false_positive_metrics
                if false_positive_metrics and random_id % 3 == 0
                else all_metrics
            )
            importance = np.asarray(
                [portfolios[label]["importance"] for label in included_metrics],
                float,
            )
            alpha = 0.20 + args.random_metric_concentration * (
                importance / importance.sum()
            )
            draw = rng.dirichlet(alpha)
            metric_mix = {
                label: float(weight)
                for label, weight in zip(included_metrics, draw)
            }
            core_share = float(rng.choice(candidate_core_shares))
            evaluate_candidate(
                "seeded_random_metric_mix",
                core_share,
                f"random_metric_mix_{random_id + 1:05d}",
                included_metrics,
                metric_mix,
            )

    direct_pool: list[str] = []
    if args.direct_system_mix_trials:
        direct_pool = direct_system_candidate_pool(
            evidence,
            args.direct_system_pool_per_criterion,
        )
        pair_grid = np.linspace(0.05, 0.95, 19)
        pair_id = 0
        for left_index, left in enumerate(direct_pool):
            for right in direct_pool[left_index + 1 :]:
                for left_weight in pair_grid:
                    pair_id += 1
                    evaluate_candidate(
                        "exhaustive_direct_system_pair",
                        0.0,
                        f"direct_pair_{pair_id:05d}",
                        [],
                        direct_weights={
                            left: float(left_weight),
                            right: float(1.0 - left_weight),
                        },
                    )
        rng = np.random.default_rng(args.direct_system_mix_seed)
        maximum_members = min(
            args.direct_system_maximum_members,
            len(direct_pool),
        )
        for random_id in range(args.direct_system_mix_trials):
            member_count = int(rng.integers(2, maximum_members + 1))
            members = rng.choice(
                direct_pool,
                size=member_count,
                replace=False,
            ).tolist()
            draw = rng.dirichlet(np.full(member_count, 0.35))
            evaluate_candidate(
                "seeded_direct_system_mix",
                0.0,
                f"direct_system_mix_{random_id + 1:05d}",
                [],
                direct_weights={
                    system: float(weight)
                    for system, weight in zip(members, draw)
                },
            )
    eligible_trials = trials
    constraint_applied = False
    if args.require_controls_below_event:
        constrained = [
            row
            for row in trials
            if row["hard_negative_below_event_count"] == len(steps)
        ]
        if constrained:
            eligible_trials = constrained
            constraint_applied = True
    selected = max(
        eligible_trials,
        key=lambda row: (
            row["selection_objective"],
            row["hard_negative_below_event_count"],
            row["exact_peak_count"],
            -row["core_share"],
        ),
    )
    _, _, selected_validation_frames = validation_scores(
        steps,
        selected["system_weights"],
        args.event_radius,
        args.event_control_margin_scale,
        args.minimum_event_control_margin,
        include_frames=True,
    )

    standard_validation = pd.read_csv(
        run_dir / "05_ensemble/timing/validation_predictions.csv"
    )
    standard_folds = []
    for step_name, group in standard_validation.groupby("step", sort=False):
        standard_metrics = score_quality(
            group["actual"].to_numpy(int),
            group["score_percentile_not_probability"].to_numpy(float),
            np.arange(len(group), dtype=int),
            args.event_radius,
        )
        standard_folds.append(
            {
                "step": step_name,
                "quality_higher_is_better": standard_metrics[
                    "quality_higher_is_better"
                ],
                "strict_local_peak": standard_metrics["event_profiles"][0][
                    "strict_local_peak"
                ],
            }
        )

    forecast_systems = pd.read_csv(
        run_dir / "05_ensemble/timing/system_forecast_predictions.csv"
    )
    selected_weights = selected["system_weights"]
    direct_selection = selected["candidate_family"] in {
        "exhaustive_direct_system_pair",
        "seeded_direct_system_mix",
    }
    if direct_selection:
        selected_specialist = selected_weights
        trace = direct_system_contribution_trace(selected, evidence)
    else:
        selected_specialist = specialist_weights(
            portfolios,
            selected["included_metrics"],
            selected["metric_reliability_weights"],
        )
        trace = contribution_trace(
            selected,
            core,
            portfolios,
            evidence,
            args.portfolio_overall_weight,
        )
    trace_path = output_dir / "metric_fusion_contribution_trace.json"
    write_json(trace_path, trace)
    core_forecast = sum(
        weight * forecast_systems[system].to_numpy(float)
        for system, weight in core.items()
    )
    specialist_forecast = sum(
        weight * forecast_systems[system].to_numpy(float)
        for system, weight in selected_specialist.items()
    )
    fused_forecast = sum(
        weight * forecast_systems[system].to_numpy(float)
        for system, weight in selected_weights.items()
    )
    forecast_dates = pd.to_datetime(forecast_systems["date"], format="%Y-%m-%d")
    forecast = pd.DataFrame(
        {
            "date": forecast_systems["date"].astype(str),
            "slot_end_inclusive": (
                forecast_dates + pd.Timedelta(days=interval_days - 1)
            ).dt.strftime("%Y-%m-%d"),
            "metric_specialist_score_not_probability": fused_forecast,
            "overall_core_score": core_forecast,
            "specialist_score": specialist_forecast,
            "core_share": selected["core_share"],
            "specialist_share": 1.0 - selected["core_share"],
        }
    )
    forecast["forecast_rank_percentile"] = forecast[
        "metric_specialist_score_not_probability"
    ].rank(method="average", pct=True)
    forecast = forecast.sort_values("date").reset_index(drop=True)
    forecast_path = output_dir / "metric_specialist_fusion_forecast.csv"
    forecast.to_csv(forecast_path, index=False)
    selected_validation = pd.concat(
        selected_validation_frames,
        ignore_index=True,
    )
    selected_validation_path = (
        output_dir / "false_positive_aware_validation_predictions.csv"
    )
    selected_validation.to_csv(selected_validation_path, index=False)

    trial_table = pd.DataFrame(
        [
            {
                key: value
                for key, value in trial.items()
                if key
                not in {
                    "system_weights",
                    "folds",
                    "included_metrics",
                    "metric_reliability_weights",
                }
            }
            | {
                "included_metrics": ",".join(trial["included_metrics"]),
                "metric_reliability_weights": json.dumps(
                    trial["metric_reliability_weights"],
                    sort_keys=True,
                ),
                "system_weights": json.dumps(trial["system_weights"], sort_keys=True),
            }
            for trial in trials
        ]
    ).sort_values(
        ["selection_objective", "exact_peak_count"],
        ascending=[False, False],
    )
    trial_table.to_csv(output_dir / "metric_fusion_ablation_trials.csv", index=False)

    gate_pass = bool(
        selected["validation_quality_mean"]
        >= args.minimum_fusion_validation_mean
        and selected["validation_quality_worst"]
        >= args.minimum_fusion_validation_worst
        and selected["exact_peak_count"] == len(steps)
        and selected["hard_negative_below_event_count"] == len(steps)
    )
    payload = {
        "status": "PASS" if gate_pass else "LOW_CONFIDENCE_REPORTED",
        "score_semantics": (
            "weighted empirical validation ranks; not calibrated earthquake probabilities"
        ),
        "quality_thresholds": {
            "minimum_core_overall": args.minimum_core_overall,
            "minimum_specialist_overall": args.minimum_specialist_overall,
            "fusion_validation_mean": args.minimum_fusion_validation_mean,
            "fusion_validation_worst": args.minimum_fusion_validation_worst,
        },
        "fusion_search_parameters": {
            "metric_config_json": (
                str(args.metric_config_json.expanduser().resolve())
                if args.metric_config_json
                else None
            ),
            "metric_count": len(metric_definitions),
            "portfolio_overall_weight": args.portfolio_overall_weight,
            "portfolio_metric_weight": 1.0 - args.portfolio_overall_weight,
            "candidate_core_shares": candidate_core_shares,
            "selection_mean_weight": args.selection_mean_weight,
            "selection_worst_weight": 1.0 - args.selection_mean_weight,
            "selection_quality_weight": args.selection_quality_weight,
            "selection_false_positive_weight": (
                args.selection_false_positive_weight
            ),
            "selection_exact_peak_weight": args.selection_exact_peak_weight,
            "false_positive_mean_weight": args.false_positive_mean_weight,
            "false_positive_worst_weight": (
                1.0 - args.false_positive_mean_weight
            ),
            "event_control_margin_scale": args.event_control_margin_scale,
            "minimum_event_control_margin": args.minimum_event_control_margin,
            "require_controls_below_event": args.require_controls_below_event,
            "control_constraint_applied": constraint_applied,
            "random_metric_mix_trials": args.random_metric_mix_trials,
            "random_metric_mix_seed": args.random_metric_mix_seed,
            "random_metric_concentration": args.random_metric_concentration,
            "direct_system_mix_trials": args.direct_system_mix_trials,
            "direct_system_mix_seed": args.direct_system_mix_seed,
            "direct_system_pool_per_criterion": (
                args.direct_system_pool_per_criterion
            ),
            "direct_system_maximum_members": (
                args.direct_system_maximum_members
            ),
            "direct_system_candidate_pool": direct_pool,
            "specialists_per_metric": args.specialists_per_metric,
        },
        "core_fallback_used": core_fallback,
        "core_weights": core,
        "metric_portfolios": portfolios,
        "selected_trial": selected,
        "contribution_trace": {
            "path": str(trace_path),
            "schema": trace["schema"],
            "weights_reconstructed": trace["checks"][
                "weights_reconstructed"
            ],
            "maximum_absolute_reconstruction_error": trace["checks"][
                "maximum_absolute_reconstruction_error"
            ],
        },
        "standard_fusion_validation": standard_folds,
        "false_positive_aware_validation": {
            "path": str(selected_validation_path),
            "hard_negative_below_event_count": selected[
                "hard_negative_below_event_count"
            ],
            "fold_count": len(steps),
            "false_positive_quality_mean": selected[
                "false_positive_quality_mean"
            ],
            "false_positive_quality_worst": selected[
                "false_positive_quality_worst"
            ],
        },
        "system_evidence": evidence,
        "forecast": {
            "path": str(forecast_path),
            "rows": len(forecast),
            "top_slots": forecast.nlargest(
                min(6, len(forecast)),
                "metric_specialist_score_not_probability",
            )[
                [
                    "date",
                    "slot_end_inclusive",
                    "metric_specialist_score_not_probability",
                    "forecast_rank_percentile",
                ]
            ].to_dict(orient="records"),
        },
    }
    write_json(output_dir / "metric_specialist_fusion_summary.json", payload)

    lines = [
        "# V14 metric-specialist timing fusion",
        "",
        f"Status: **{payload['status']}**.",
        "",
        (
            f"Selected core share: **{selected['core_share']:.0%}**; "
            f"specialist share: **{1-selected['core_share']:.0%}**."
        ),
        "",
        (
            f"Validation quality mean/worst: "
            f"**{selected['validation_quality_mean']:.3f}/"
            f"{selected['validation_quality_worst']:.3f}**; "
            f"exact peaks: **{selected['exact_peak_count']}/{len(steps)}**."
        ),
        "",
        (
            "False-positive quality mean/worst: "
            f"**{selected['false_positive_quality_mean']:.3f}/"
            f"{selected['false_positive_quality_worst']:.3f}**; "
            "hard negatives below their paired real event: "
            f"**{selected['hard_negative_below_event_count']}/"
            f"{len(steps)}**."
        ),
        "",
        "## Overall core",
        "",
        "| system | weight | overall quality |",
        "| --- | ---: | ---: |",
    ]
    for system, weight in sorted(core.items(), key=lambda row: row[1], reverse=True):
        lines.append(
            f"| {system} | {weight:.4f} | "
            f"{evidence[system]['overall_quality_mean']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Metric specialist portfolios",
            "",
            (
                "The rows below are generated from "
                "`metric_fusion_contribution_trace.json`. The final contribution "
                "already includes both the specialist share and the normalized "
                "reliability of the metric."
            ),
            "",
            "| metric | final fusion share | selected systems |",
            "| --- | ---: | --- |",
        ]
    )
    for component in trace["metric_components"]:
        systems = ", ".join(
            f"{row['system']} {row['within_metric_weight']:.1%}"
            for row in component["systems"]
        )
        lines.append(
            f"| {component['metric']} | "
            f"{component['final_fusion_share']:.4f} | {systems} |"
        )
    lines.extend(
        [
            "",
            "## Forecast ranking",
            "",
            "| start | end inclusive | score | percentile |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for row in payload["forecast"]["top_slots"]:
        lines.append(
            f"| {row['date']} | {row['slot_end_inclusive']} | "
            f"{row['metric_specialist_score_not_probability']:.4f} | "
            f"{row['forecast_rank_percentile']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Scores are experimental ranks, not probabilities or earthquake warnings.",
            "",
        ]
    )
    (output_dir / "METRIC_SPECIALIST_FUSION.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(json.dumps(payload["selected_trial"], indent=2), flush=True)


if __name__ == "__main__":
    main()

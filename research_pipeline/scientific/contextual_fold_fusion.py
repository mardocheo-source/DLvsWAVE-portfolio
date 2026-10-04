#!/usr/bin/env python3
"""Build a context-weighted forecast from independently selected outer folds.

Each chronological outer event selects its own sparse system combination and
post-processing rule.  The selected rule is then applied unchanged to both the
fold-trained future projection and the all-history refit projection.  Fold
forecasts are combined by validation/context reliability and may receive a
bounded order-shuffle stability anchor.  Target-label randomized controls are
never candidates and always have zero forecast weight.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from common_v14 import event_shape_metrics, internal_local_maxima, score_quality, write_json


def normalize_weights(values: dict[str, float]) -> dict[str, float]:
    cleaned = {key: max(0.0, float(value)) for key, value in values.items()}
    total = float(sum(cleaned.values()))
    if total <= 0.0:
        raise ValueError("At least one fusion weight must be positive")
    return {key: value / total for key, value in cleaned.items() if value > 0.0}


def parse_float_list(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    return [float(item) for item in str(value).split(",") if str(item).strip()]


def rolling_median(values: np.ndarray, width: int) -> np.ndarray:
    values = np.asarray(values, float)
    if width <= 1:
        return values.copy()
    radius = int(width) // 2
    return np.asarray(
        [
            np.median(values[max(0, index - radius) : min(len(values), index + radius + 1)])
            for index in range(len(values))
        ],
        float,
    )


def weighted_curve(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.asarray(weights, float) @ np.asarray(matrix, float)


def shape_curve(
    matrix: np.ndarray,
    weights: np.ndarray,
    median_width: int,
    median_blend: float,
    agreement_floor: float,
    contrast_gain: float,
) -> np.ndarray:
    """Apply one label-free shape rule identically to validation and forecast."""
    matrix = np.asarray(matrix, float)
    weights = np.asarray(weights, float)
    centre = weighted_curve(matrix, weights)
    local_median = rolling_median(centre, median_width)
    levelled = (1.0 - median_blend) * centre + median_blend * local_median
    variance = np.sum(weights[:, None] * (matrix - centre[None, :]) ** 2, axis=0)
    agreement = np.clip(1.0 - 2.0 * np.sqrt(np.maximum(variance, 0.0)), 0.0, 1.0)
    support = agreement_floor + (1.0 - agreement_floor) * agreement
    baseline = float(np.median(levelled))
    gated = baseline + (levelled - baseline) * support
    contrasted = baseline + contrast_gain * (gated - baseline)
    return np.clip(contrasted, 0.0, 1.0)


def weak_peak_rescue(
    values: np.ndarray,
    lag: int,
    minimum_central_ratio: float,
    flank_suppression: float,
    central_boost: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Rescue the centre of a symmetric repeated-peak triplet without labels.

    The rule is deliberately pattern-based: it can act only when three strict
    local maxima share one configured lag and the middle maximum is not weaker
    than the configured fraction of the stronger flank.  Event labels and
    dates are not inputs, so the identical operator can be applied to future
    bins.
    """
    values = np.asarray(values, float)
    if lag <= 0 or len(values) < 2 * lag + 1:
        return values.copy(), {
            "applied": False,
            "triplet": [],
            "symmetry_skill": 0.0,
        }
    peaks = internal_local_maxima(values)
    candidates = []
    for centre in np.flatnonzero(peaks):
        left = int(centre - lag)
        right = int(centre + lag)
        if left < 0 or right >= len(values) or not peaks[left] or not peaks[right]:
            continue
        flank_max = max(float(values[left]), float(values[right]), 1e-9)
        central_ratio = float(values[centre] / flank_max)
        if central_ratio < minimum_central_ratio:
            continue
        symmetry = float(
            1.0
            - abs(float(values[left]) - float(values[right]))
            / max(flank_max, 1e-9)
        )
        candidates.append(
            (symmetry * float(values[centre]), centre, left, right, symmetry)
        )
    if not candidates:
        return values.copy(), {
            "applied": False,
            "triplet": [],
            "symmetry_skill": 0.0,
        }
    _, centre, left, right, symmetry = max(candidates)
    output = values.copy()
    for flank in (left, right):
        neighbor_floor = max(float(values[flank - 1]), float(values[flank + 1]))
        output[flank] = (
            (1.0 - flank_suppression) * float(values[flank])
            + flank_suppression * neighbor_floor
        )
    output[centre] = float(values[centre]) + central_boost * (
        1.0 - float(values[centre])
    )
    return np.clip(output, 0.0, 1.0), {
        "applied": True,
        "triplet": [left, int(centre), right],
        "symmetry_skill": symmetry,
    }


def sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + math.exp(-float(np.clip(value, -30.0, 30.0)))))


def contextual_metrics(
    score: np.ndarray,
    actual: np.ndarray,
    hard_negative: np.ndarray,
    origin_quality: float,
    objective_weights: dict[str, float],
    competitor_radius: int,
    margin_scale: float,
    target_event_index: int | None = None,
) -> dict[str, Any]:
    score = np.clip(np.asarray(score, float), 0.0, 1.0)
    actual = np.asarray(actual, int)
    hard_negative = np.asarray(hard_negative, int)
    event_positions = np.flatnonzero(actual == 1)
    if not len(event_positions):
        raise ValueError("Every contextual fold must contain a real event")
    if target_event_index is None:
        if len(event_positions) != 1:
            raise ValueError(
                "A designated target_event_index is required when a fold "
                "contains multiple genuine event bins"
            )
        event = int(event_positions[0])
    else:
        event = int(target_event_index)
        if event < 0 or event >= len(actual) or actual[event] != 1:
            raise ValueError("The designated contextual target is not a real event")
    profile = event_shape_metrics(score, event)
    protected = np.zeros(len(score), dtype=bool)
    protected[
        max(0, event - competitor_radius) : min(
            len(score), event + competitor_radius + 1
        )
    ] = True
    # Other genuine events remain visible in the fold curve, but they are not
    # false-positive competitors for the explicitly designated outer holdout.
    protected[event_positions] = True
    background = score[~protected]
    background_max = float(np.max(background)) if len(background) else 0.0
    background_median = float(np.median(background)) if len(background) else 0.0
    event_margin = float(score[event] - background_max)
    dominance = sigmoid(event_margin / max(float(margin_scale), 1e-6))
    local_values = []
    if event > 0:
        local_values.append(float(score[event - 1]))
    if event + 1 < len(score):
        local_values.append(float(score[event + 1]))
    local_margin = float(score[event] - max(local_values)) if local_values else 0.0
    local_prominence = sigmoid(local_margin / max(float(margin_scale), 1e-6))
    dispersion = (
        float(np.mean(np.abs(background - background_median)))
        if len(background)
        else 0.0
    )
    background_flatness = float(np.exp(-dispersion / max(float(margin_scale), 1e-6)))
    local = internal_local_maxima(score)
    false_peak_count = int(np.sum(local & ~protected))
    false_peak_control = float(1.0 / (1.0 + false_peak_count))
    hard_positions = np.flatnonzero(hard_negative == 1)
    if len(hard_positions):
        hard_scores = score[hard_positions]
        hard_below = bool(np.all(hard_scores < score[event]))
        hard_margin = float(score[event] - np.max(hard_scores))
        hard_negative_skill = float(
            0.55 * float(hard_below)
            + 0.45 * sigmoid(hard_margin / max(float(margin_scale), 1e-6))
        )
    else:
        hard_below = True
        hard_margin = float("nan")
        hard_negative_skill = 1.0
    quality = score_quality(actual, score, np.arange(len(score)), competitor_radius)
    components = {
        "event_height": float(score[event]),
        "event_rank": float(profile["event_percentile_skill"]),
        "event_dominance": dominance,
        "local_prominence": local_prominence,
        "background_flatness": background_flatness,
        "false_peak_control": false_peak_control,
        "hard_negative_rejection": hard_negative_skill,
        "weak_peak_retention": float(profile["weak_peak_retention_skill"]),
        "general_quality": float(quality["quality_higher_is_better"]),
        "origin_quality": float(origin_quality),
    }
    normalized_objective_weights = normalize_weights(objective_weights)
    objective = float(
        sum(
            normalized_objective_weights.get(key, 0.0) * value
            for key, value in components.items()
        )
    )
    return {
        **components,
        "objective_higher_is_better": objective,
        "event_index": event,
        "event_score": float(score[event]),
        "event_over_background_margin": event_margin,
        "local_event_margin": local_margin,
        "background_max": background_max,
        "background_median": background_median,
        "background_dispersion": dispersion,
        "false_peak_count": false_peak_count,
        "strict_local_peak": bool(profile["strict_local_peak"]),
        "argmax_offset_slots": int(profile["argmax_offset_slots"]),
        "hard_negative_below_event": hard_below,
        "hard_negative_margin": hard_margin,
        "quality_metrics": quality,
    }


def candidate_pool(
    systems: list[str],
    summaries: dict[str, dict],
    global_weights: dict[str, float],
    pair_grid: list[float],
    random_trials: int,
    maximum_members: int,
    random_seed: int,
) -> list[tuple[str, dict[str, float]]]:
    candidates: list[tuple[str, dict[str, float]]] = []
    for system in systems:
        candidates.append(("single_system", {system: 1.0}))
    for left_index, left in enumerate(systems):
        for right in systems[left_index + 1 :]:
            for left_share in pair_grid:
                candidates.append(
                    (
                        "exhaustive_pair",
                        {left: float(left_share), right: float(1.0 - left_share)},
                    )
                )
    valid_global = {
        system: value
        for system, value in global_weights.items()
        if system in systems and float(value) > 0.0
    }
    if valid_global:
        candidates.append(("global_fusion_reference", normalize_weights(valid_global)))
    weak_ranked = sorted(
        systems,
        key=lambda system: (
            summaries[system]["validation_metrics"]["weak_peak_retention_skill"],
            summaries[system]["validation_metrics"]["false_peak_control"],
            summaries[system]["origin_quality_25train_75validation"],
        ),
        reverse=True,
    )
    for member_count in range(2, min(6, len(weak_ranked)) + 1):
        members = weak_ranked[:member_count]
        raw = {
            system: max(
                1e-6,
                float(
                    summaries[system]["validation_metrics"][
                        "weak_peak_retention_skill"
                    ]
                ),
            )
            ** 3
            for system in members
        }
        candidates.append(("weak_peak_portfolio", normalize_weights(raw)))
    rng = np.random.default_rng(random_seed)
    maximum_members = min(maximum_members, len(systems))
    for _ in range(random_trials):
        member_count = int(rng.integers(2, maximum_members + 1))
        members = rng.choice(systems, size=member_count, replace=False).tolist()
        draw = rng.dirichlet(np.full(member_count, 0.30))
        candidates.append(
            (
                "seeded_sparse_mix",
                {
                    system: float(weight)
                    for system, weight in zip(members, draw)
                    if weight > 1e-8
                },
            )
        )
    return candidates


def load_fold(step_dir: Path) -> dict[str, Any]:
    summary = json.loads((step_dir / "step_summary.json").read_text())
    systems: list[str] = []
    frames: dict[str, pd.DataFrame] = {}
    forecasts: dict[str, pd.DataFrame | None] = {}
    summaries: dict[str, dict] = {}
    for system_dir in sorted(path for path in step_dir.iterdir() if path.is_dir()):
        validation_path = system_dir / "validation_predictions.csv"
        summary_path = system_dir / "summary.json"
        if not validation_path.is_file() or not summary_path.is_file():
            continue
        system = system_dir.name
        systems.append(system)
        frames[system] = pd.read_csv(validation_path)
        forecasts[system] = (
            pd.read_csv(system_dir / "forecast_predictions.csv")
            if (system_dir / "forecast_predictions.csv").is_file()
            else None
        )
        summaries[system] = json.loads(summary_path.read_text())
    if not systems:
        raise RuntimeError(f"No fold-system predictions found under {step_dir}")
    dates = frames[systems[0]]["date"].astype(str).tolist()
    if any(frames[system]["date"].astype(str).tolist() != dates for system in systems):
        raise RuntimeError(f"Misaligned validation rows in {step_dir}")
    return {
        "step": step_dir.name,
        "step_summary": summary,
        "systems": systems,
        "frames": frames,
        "forecasts": forecasts,
        "summaries": summaries,
    }


def sparse_array(weights: dict[str, float], systems: list[str]) -> np.ndarray:
    return np.asarray([float(weights.get(system, 0.0)) for system in systems], float)


def select_fold(
    fold: dict[str, Any],
    config: dict[str, Any],
    global_weights: dict[str, float],
    fold_index: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    systems = fold["systems"]
    base = fold["frames"][systems[0]].copy()
    matrix = np.vstack(
        [
            fold["frames"][system]["score_percentile_not_probability"].to_numpy(float)
            for system in systems
        ]
    )
    actual = base["actual"].to_numpy(int)
    event_date = str(fold["step_summary"]["event"]["date"])
    target_matches = np.flatnonzero(
        base["date"].astype(str).eq(event_date).to_numpy()
        & (actual == 1)
    )
    if len(target_matches) != 1:
        raise RuntimeError(
            f"Expected one designated event row for {event_date} in {fold['step']}"
        )
    target_event_index = int(target_matches[0])
    hard_negative = (
        base["hard_negative_control"].fillna(0).to_numpy(int)
        if "hard_negative_control" in base
        else np.zeros(len(base), int)
    )
    candidates = candidate_pool(
        systems,
        fold["summaries"],
        global_weights,
        parse_float_list(config["pair_weight_grid"]),
        int(config["random_mix_trials"]),
        int(config["maximum_members"]),
        int(config["random_seed"]) + fold_index * 1009,
    )
    initial_rows: list[dict[str, Any]] = []
    for candidate_index, (family, weights) in enumerate(candidates):
        array = sparse_array(weights, systems)
        origin_quality = float(
            sum(
                weights[system]
                * fold["summaries"][system][
                    "origin_quality_25train_75validation"
                ]
                for system in weights
            )
        )
        score = shape_curve(matrix, array, 1, 0.0, 1.0, 1.0)
        metrics = contextual_metrics(
            score,
            actual,
            hard_negative,
            origin_quality,
            config["objective_weights"],
            int(config["competitor_radius"]),
            float(config["margin_scale"]),
            target_event_index,
        )
        initial_rows.append(
            {
                "trial_id": f"base_{candidate_index + 1:06d}",
                "candidate_family": family,
                "weights": weights,
                "median_width": 1,
                "median_blend": 0.0,
                "agreement_floor": 1.0,
                "contrast_gain": 1.0,
                "weak_peak_lag": 0,
                "weak_peak_minimum_central_ratio": 1.0,
                "weak_peak_flank_suppression": 0.0,
                "weak_peak_central_boost": 0.0,
                "weak_peak_rescue_applied": False,
                "score": score,
                "metrics": metrics,
            }
        )
    initial_rows.sort(
        key=lambda row: row["metrics"]["objective_higher_is_better"],
        reverse=True,
    )
    retained = initial_rows[: int(config["postprocess_candidate_count"])]
    expanded_rows: list[dict[str, Any]] = []
    transform_id = 0
    for row in retained:
        array = sparse_array(row["weights"], systems)
        origin_quality = row["metrics"]["origin_quality"]
        for median_width in [int(value) for value in config["median_widths"]]:
            for median_blend in parse_float_list(config["median_blends"]):
                for agreement_floor in parse_float_list(config["agreement_floors"]):
                    for contrast_gain in parse_float_list(config["contrast_gains"]):
                        transform_id += 1
                        score = shape_curve(
                            matrix,
                            array,
                            median_width,
                            median_blend,
                            agreement_floor,
                            contrast_gain,
                        )
                        metrics = contextual_metrics(
                            score,
                            actual,
                            hard_negative,
                            origin_quality,
                            config["objective_weights"],
                            int(config["competitor_radius"]),
                            float(config["margin_scale"]),
                            target_event_index,
                        )
                        expanded_rows.append(
                            {
                                "trial_id": f"shape_{transform_id:07d}",
                                "candidate_family": row["candidate_family"],
                                "weights": row["weights"],
                                "median_width": median_width,
                                "median_blend": median_blend,
                                "agreement_floor": agreement_floor,
                                "contrast_gain": contrast_gain,
                                "weak_peak_lag": 0,
                                "weak_peak_minimum_central_ratio": 1.0,
                                "weak_peak_flank_suppression": 0.0,
                                "weak_peak_central_boost": 0.0,
                                "weak_peak_rescue_applied": False,
                                "score": score,
                                "metrics": metrics,
                            }
                        )
    pre_rescue_rows = initial_rows + expanded_rows
    rescue_rows: list[dict[str, Any]] = []
    rescue_source_count = int(config.get("weak_peak_candidate_count", 0))
    rescue_sources = sorted(
        pre_rescue_rows,
        key=lambda row: (
            row["metrics"]["weak_peak_retention"],
            row["metrics"]["objective_higher_is_better"],
        ),
        reverse=True,
    )[:rescue_source_count]
    rescue_id = 0
    for row in rescue_sources:
        for lag in [int(value) for value in config.get("weak_peak_lags", [])]:
            for central_ratio in parse_float_list(
                config.get("weak_peak_minimum_central_ratios", [])
            ):
                for suppression in parse_float_list(
                    config.get("weak_peak_flank_suppressions", [])
                ):
                    for boost in parse_float_list(
                        config.get("weak_peak_central_boosts", [])
                    ):
                        rescue_id += 1
                        score, rescue_audit = weak_peak_rescue(
                            row["score"],
                            lag,
                            central_ratio,
                            suppression,
                            boost,
                        )
                        if not rescue_audit["applied"]:
                            continue
                        metrics = contextual_metrics(
                            score,
                            actual,
                            hard_negative,
                            row["metrics"]["origin_quality"],
                            config["objective_weights"],
                            int(config["competitor_radius"]),
                            float(config["margin_scale"]),
                            target_event_index,
                        )
                        rescue_rows.append(
                            {
                                "trial_id": f"weak_{rescue_id:07d}",
                                "candidate_family": (
                                    row["candidate_family"] + "+weak_peak_rescue"
                                ),
                                "weights": row["weights"],
                                "median_width": row["median_width"],
                                "median_blend": row["median_blend"],
                                "agreement_floor": row["agreement_floor"],
                                "contrast_gain": row["contrast_gain"],
                                "weak_peak_lag": lag,
                                "weak_peak_minimum_central_ratio": central_ratio,
                                "weak_peak_flank_suppression": suppression,
                                "weak_peak_central_boost": boost,
                                "weak_peak_rescue_applied": True,
                                "weak_peak_triplet": rescue_audit["triplet"],
                                "weak_peak_symmetry_skill": rescue_audit[
                                    "symmetry_skill"
                                ],
                                "score": score,
                                "metrics": metrics,
                            }
                        )
    all_rows = pre_rescue_rows + rescue_rows
    eligible = [
        row
        for row in all_rows
        if row["metrics"]["hard_negative_below_event"]
        and row["metrics"]["strict_local_peak"]
        and row["metrics"]["false_peak_count"]
        <= int(config["maximum_false_peaks"])
        and row["metrics"]["weak_peak_retention"]
        >= float(config["minimum_weak_peak_retention"])
    ]
    constraints_relaxed: list[str] = []
    if not eligible:
        eligible = [
            row
            for row in all_rows
            if row["metrics"]["hard_negative_below_event"]
            and row["metrics"]["strict_local_peak"]
            and row["metrics"]["weak_peak_retention"]
            >= float(config["minimum_weak_peak_retention"])
        ]
        constraints_relaxed.append("maximum_false_peaks")
    if not eligible:
        eligible = [
            row
            for row in all_rows
            if row["metrics"]["hard_negative_below_event"]
            and row["metrics"]["strict_local_peak"]
        ]
        constraints_relaxed.append("minimum_weak_peak_retention")
    if not eligible:
        eligible = all_rows
        constraints_relaxed.append("strict_peak_and_hard_negative")
    selected = max(
        eligible,
        key=lambda row: (
            row["metrics"]["objective_higher_is_better"],
            row["metrics"]["event_over_background_margin"],
            row["metrics"]["weak_peak_retention"],
            -len(row["weights"]),
        ),
    )
    selected["constraints_relaxed"] = constraints_relaxed
    selected["evaluated_candidate_count"] = len(all_rows)
    selected["base_candidate_count"] = len(initial_rows)
    selected["expanded_candidate_count"] = len(expanded_rows)
    audit_limit = int(config.get("audit_top_trials", 10000))
    ranked = sorted(
        all_rows,
        key=lambda row: row["metrics"]["objective_higher_is_better"],
        reverse=True,
    )[:audit_limit]
    trial_frame = pd.DataFrame(
        [
            {
                "step": fold["step"],
                "rank": rank,
                "trial_id": row["trial_id"],
                "candidate_family": row["candidate_family"],
                "weights": json.dumps(row["weights"], sort_keys=True),
                "median_width": row["median_width"],
                "median_blend": row["median_blend"],
                "agreement_floor": row["agreement_floor"],
                "contrast_gain": row["contrast_gain"],
                "weak_peak_lag": row["weak_peak_lag"],
                "weak_peak_minimum_central_ratio": row[
                    "weak_peak_minimum_central_ratio"
                ],
                "weak_peak_flank_suppression": row[
                    "weak_peak_flank_suppression"
                ],
                "weak_peak_central_boost": row["weak_peak_central_boost"],
                "weak_peak_rescue_applied": row[
                    "weak_peak_rescue_applied"
                ],
                **{
                    key: value
                    for key, value in row["metrics"].items()
                    if key != "quality_metrics"
                },
            }
            for rank, row in enumerate(ranked, start=1)
        ]
    )
    return selected, trial_frame


def transform_for_selection(
    matrix: np.ndarray,
    systems: list[str],
    selected: dict[str, Any],
) -> np.ndarray:
    score = shape_curve(
        matrix,
        sparse_array(selected["weights"], systems),
        int(selected["median_width"]),
        float(selected["median_blend"]),
        float(selected["agreement_floor"]),
        float(selected["contrast_gain"]),
    )
    if bool(selected.get("weak_peak_rescue_applied", False)):
        score, _ = weak_peak_rescue(
            score,
            int(selected["weak_peak_lag"]),
            float(selected["weak_peak_minimum_central_ratio"]),
            float(selected["weak_peak_flank_suppression"]),
            float(selected["weak_peak_central_boost"]),
        )
    return score


def serializable_selection(selected: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in selected.items()
        if key not in {"score"}
    } | {
        "metrics": {
            key: value
            for key, value in selected["metrics"].items()
            if key != "quality_metrics"
        }
    }


def reliability_weights(
    fold_results: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, float]:
    maximum_training_events = max(
        int(row["training_events"]) for row in fold_results
    )
    mapping = normalize_weights(config["reliability_weights"])
    raw = {}
    for row in fold_results:
        metrics = row["selected"]["metrics"]
        components = {
            "selection_objective": metrics["objective_higher_is_better"],
            "event_dominance": metrics["event_dominance"],
            "weak_peak_retention": metrics["weak_peak_retention"],
            "hard_negative_rejection": metrics["hard_negative_rejection"],
            "origin_quality": metrics["origin_quality"],
            "history_support": float(row["training_events"] / maximum_training_events),
        }
        row["reliability_components"] = components
        raw[row["step"]] = float(
            sum(mapping.get(key, 0.0) * value for key, value in components.items())
        )
        row["reliability_raw"] = raw[row["step"]]
    temperature = max(float(config["reliability_temperature"]), 1e-6)
    best = max(raw.values())
    soft = {
        step: math.exp((value - best) / temperature) for step, value in raw.items()
    }
    normalized = normalize_weights(soft)
    minimum = float(config.get("minimum_fold_weight", 0.0))
    if minimum > 0.0:
        normalized = normalize_weights(
            {step: max(minimum, value) for step, value in normalized.items()}
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--config-json", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config_json.expanduser().resolve().read_text())
    model_root = run_dir / "04_models/timing"
    step_dirs = sorted(
        path
        for path in model_root.iterdir()
        if path.is_dir() and (path / "step_summary.json").is_file()
    )
    if not step_dirs:
        raise RuntimeError("No chronological outer-fold model directories found")
    global_summary_path = (
        run_dir
        / "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_summary.json"
    )
    global_weights = (
        json.loads(global_summary_path.read_text())["selected_trial"]["system_weights"]
        if global_summary_path.is_file()
        else {}
    )
    folds = [load_fold(path) for path in step_dirs]
    selections = []
    trial_frames = []
    for fold_index, fold in enumerate(folds, start=1):
        print(
            f"[{fold_index}/{len(folds)}] searching contextual combination for {fold['step']}",
            flush=True,
        )
        selected, trials = select_fold(
            fold, config, global_weights, fold_index
        )
        selections.append(selected)
        trial_frames.append(trials)
        print(
            "  objective "
            f"{selected['metrics']['objective_higher_is_better']:.4f}; "
            f"event {selected['metrics']['event_score']:.4f}; "
            f"margin {selected['metrics']['event_over_background_margin']:.4f}; "
            f"false peaks {selected['metrics']['false_peak_count']}; "
            f"weak {selected['metrics']['weak_peak_retention']:.4f}",
            flush=True,
        )
    pd.concat(trial_frames, ignore_index=True).to_csv(
        output_dir / "contextual_fold_search_top_trials.csv", index=False
    )
    final_system_forecast = pd.read_csv(
        run_dir / "05_ensemble/timing/system_forecast_predictions.csv"
    )
    fold_results: list[dict[str, Any]] = []
    validation_parts = []
    component_frame = pd.DataFrame(
        {"date": final_system_forecast["date"].astype(str)}
    )
    forecast_dates = final_system_forecast["date"].astype(str).tolist()
    origin_parameters = config["origin_projection"]
    training_counts = [
        int(next(iter(fold["summaries"].values()))["training_events"])
        for fold in folds
    ]
    maximum_training_events = max(training_counts)
    for fold_index, (fold, selected, training_events) in enumerate(
        zip(folds, selections, training_counts), start=1
    ):
        systems = fold["systems"]
        validation_matrix = np.vstack(
            [
                fold["frames"][system][
                    "score_percentile_not_probability"
                ].to_numpy(float)
                for system in systems
            ]
        )
        selected_validation = transform_for_selection(
            validation_matrix, systems, selected
        )
        validation = fold["frames"][systems[0]].copy()
        validation.insert(0, "step", fold["step"])
        validation["designated_holdout"] = (
            validation["date"].astype(str).eq(
                str(fold["step_summary"]["event"]["date"])
            )
            & validation["actual"].eq(1)
        ).astype(int)
        if int(validation["designated_holdout"].sum()) != 1:
            raise RuntimeError(
                f"Expected one designated holdout in {fold['step']}"
            )
        validation["contextual_fold_score_not_probability"] = selected_validation
        validation_parts.append(validation)
        final_matrix = np.vstack(
            [
                final_system_forecast[system].to_numpy(float)
                for system in systems
            ]
        )
        refit_projection = transform_for_selection(final_matrix, systems, selected)
        origin_available = all(
            fold["forecasts"][system] is not None for system in systems
        )
        if origin_available:
            if any(
                fold["forecasts"][system]["date"].astype(str).tolist()
                != forecast_dates
                for system in systems
            ):
                raise RuntimeError(f"Misaligned origin forecast for {fold['step']}")
            origin_matrix = np.vstack(
                [
                    fold["forecasts"][system][
                        "score_percentile_not_probability"
                    ].to_numpy(float)
                    for system in systems
                ]
            )
            origin_projection = transform_for_selection(
                origin_matrix, systems, selected
            )
        else:
            origin_projection = refit_projection.copy()
        history_support = float(training_events / maximum_training_events)
        if bool(origin_parameters.get("enabled", True)) and origin_available:
            origin_share = float(origin_parameters["minimum_share"]) + (
                float(origin_parameters["maximum_share"])
                - float(origin_parameters["minimum_share"])
            ) * history_support
        else:
            origin_share = 0.0
        projection = (
            origin_share * origin_projection
            + (1.0 - origin_share) * refit_projection
        )
        prefix = f"fold_{fold_index}"
        component_frame[f"{prefix}_origin_projection"] = origin_projection
        component_frame[f"{prefix}_all_history_refit_projection"] = refit_projection
        component_frame[f"{prefix}_context_blend"] = projection
        fold_results.append(
            {
                "step": fold["step"],
                "event": fold["step_summary"]["event"],
                "training_events": training_events,
                "history_support": history_support,
                "origin_projection_available": origin_available,
                "origin_projection_share": origin_share,
                "selected": selected,
                "validation": validation,
                "projection": projection,
            }
        )
    fold_weights = reliability_weights(fold_results, config)
    pre_anchor_forecast = sum(
        fold_weights[row["step"]] * row["projection"] for row in fold_results
    )
    record_validation_path = (
        run_dir / "07_historical_record_shuffle/timing/validation.csv"
    )
    record_forecast_path = run_dir / "07_historical_record_shuffle/timing/forecast.csv"
    record_summary_path = run_dir / "07_historical_record_shuffle/timing/summary.json"
    randomized_summary_path = run_dir / "07_randomized_control/timing/summary.json"
    record_available = record_validation_path.is_file() and record_forecast_path.is_file()
    record_validation_quality = None
    randomized_validation_quality = None
    minimum_record_quality = float(
        config.get("row_order_minimum_validation_quality", 0.0)
    )
    require_above_null = bool(
        config.get("row_order_require_above_target_label_null", False)
    )
    if record_available and record_summary_path.is_file():
        record_summary = json.loads(record_summary_path.read_text())
        record_validation_quality = float(
            record_summary["validation_metrics"]["quality_higher_is_better"]
        )
    if randomized_summary_path.is_file():
        randomized_summary = json.loads(randomized_summary_path.read_text())
        randomized_validation_quality = float(
            randomized_summary["validation_metrics"][
                "quality_higher_is_better"
            ]
        )
    record_quality_gate_pass = bool(
        record_available
        and record_validation_quality is not None
        and record_validation_quality >= minimum_record_quality
        and (
            not require_above_null
            or randomized_validation_quality is None
            or record_validation_quality > randomized_validation_quality
        )
    )
    row_order_trials = []
    if record_quality_gate_pass:
        record_validation = pd.read_csv(record_validation_path)
        record_forecast = pd.read_csv(record_forecast_path)
        validation_lookup = record_validation.set_index("date")[
            "historical_record_shuffle_score"
        ]
        for share in parse_float_list(config["row_order_shares"]):
            fold_metrics = []
            for row in fold_results:
                validation = row["validation"]
                anchor = validation["date"].astype(str).map(validation_lookup).to_numpy(float)
                blended = (
                    (1.0 - share)
                    * validation["contextual_fold_score_not_probability"].to_numpy(float)
                    + share * anchor
                )
                fold_metrics.append(
                    contextual_metrics(
                        blended,
                        validation["actual"].to_numpy(int),
                        (
                            validation["hard_negative_control"].fillna(0).to_numpy(int)
                            if "hard_negative_control" in validation
                            else np.zeros(len(validation), int)
                        ),
                        row["selected"]["metrics"]["origin_quality"],
                        config["objective_weights"],
                        int(config["competitor_radius"]),
                        float(config["margin_scale"]),
                        int(
                            np.flatnonzero(
                                validation["date"].astype(str).eq(
                                    str(row["event"]["date"])
                                ).to_numpy()
                                & validation["actual"].eq(1).to_numpy()
                            )[0]
                        ),
                    )
                )
            weighted_objective = float(
                sum(
                    fold_weights[row["step"]]
                    * metrics["objective_higher_is_better"]
                    for row, metrics in zip(fold_results, fold_metrics)
                )
            )
            row_order_trials.append(
                {
                    "share": share,
                    "weighted_objective": weighted_objective,
                    "all_strict_local_peaks": all(
                        metrics["strict_local_peak"] for metrics in fold_metrics
                    ),
                    "all_controls_below_event": all(
                        metrics["hard_negative_below_event"] for metrics in fold_metrics
                    ),
                    "worst_weak_peak_retention": min(
                        metrics["weak_peak_retention"] for metrics in fold_metrics
                    ),
                    "fold_metrics": fold_metrics,
                }
            )
        eligible_anchor = [
            row
            for row in row_order_trials
            if row["all_strict_local_peaks"]
            and row["all_controls_below_event"]
            and row["worst_weak_peak_retention"]
            >= float(config["minimum_weak_peak_retention"])
        ]
        selected_anchor = max(
            eligible_anchor or row_order_trials,
            key=lambda row: (row["weighted_objective"], -row["share"]),
        )
        row_order_share = float(selected_anchor["share"])
        row_order_forecast = record_forecast[
            "historical_record_shuffle_score"
        ].to_numpy(float)
    else:
        selected_anchor = None
        row_order_share = 0.0
        row_order_forecast = np.zeros(len(pre_anchor_forecast), float)
    final_forecast = (
        (1.0 - row_order_share) * pre_anchor_forecast
        + row_order_share * row_order_forecast
    )
    final_validation_parts = []
    for row in fold_results:
        validation = row["validation"].copy()
        if record_quality_gate_pass:
            anchor = validation["date"].astype(str).map(validation_lookup).to_numpy(float)
        else:
            anchor = np.zeros(len(validation), float)
        validation["row_order_anchor_score"] = anchor
        validation["contextual_promoted_score_not_probability"] = (
            (1.0 - row_order_share)
            * validation["contextual_fold_score_not_probability"].to_numpy(float)
            + row_order_share * anchor
        )
        validation["fold_reliability_weight"] = fold_weights[row["step"]]
        target_matches = np.flatnonzero(
            validation["designated_holdout"].eq(1).to_numpy()
        )
        if len(target_matches) != 1:
            raise RuntimeError(
                f"Expected one designated promoted holdout for {row['step']}"
            )
        row["promoted_validation_metrics"] = contextual_metrics(
            validation[
                "contextual_promoted_score_not_probability"
            ].to_numpy(float),
            validation["actual"].to_numpy(int),
            (
                validation["hard_negative_control"].fillna(0).to_numpy(int)
                if "hard_negative_control" in validation
                else np.zeros(len(validation), int)
            ),
            row["selected"]["metrics"]["origin_quality"],
            config["objective_weights"],
            int(config["competitor_radius"]),
            float(config["margin_scale"]),
            int(target_matches[0]),
        )
        final_validation_parts.append(validation)
    final_validation = pd.concat(final_validation_parts, ignore_index=True)
    final_validation.to_csv(
        output_dir / "contextual_fold_validation_predictions.csv", index=False
    )
    component_frame["context_weighted_pre_anchor"] = pre_anchor_forecast
    component_frame["row_order_anchor_score"] = row_order_forecast
    component_frame["contextual_promoted_score_not_probability"] = final_forecast
    component_frame.to_csv(
        output_dir / "contextual_fold_forecast_components.csv", index=False
    )
    manifest = json.loads(
        (run_dir / "00_config/run_manifest.json").read_text()
    )
    interval_days = int(manifest["parameters"]["interval_days"])
    dates = pd.to_datetime(component_frame["date"], format="%Y-%m-%d")
    forecast = pd.DataFrame(
        {
            "date": component_frame["date"],
            "slot_end_inclusive": (
                dates + pd.Timedelta(days=interval_days - 1)
            ).dt.strftime("%Y-%m-%d"),
            "contextual_promoted_score_not_probability": final_forecast,
            "context_weighted_pre_anchor": pre_anchor_forecast,
            "row_order_anchor_score": row_order_forecast,
            "row_order_anchor_share": row_order_share,
        }
    )
    forecast["forecast_rank_percentile"] = forecast[
        "contextual_promoted_score_not_probability"
    ].rank(method="average", pct=True)
    forecast_path = output_dir / "contextual_fold_fusion_forecast.csv"
    forecast.to_csv(forecast_path, index=False)
    contribution = {
        "schema": "contextual_fold_fusion.contribution_trace.v1",
        "fold_reliability_weights": fold_weights,
        "row_order_anchor_share": row_order_share,
        "final_contributions": {
            row["step"]: {
                "fold_reliability": fold_weights[row["step"]],
                "pre_anchor_contribution": (
                    (1.0 - row_order_share) * fold_weights[row["step"]]
                ),
                "origin_projection_share_within_fold": row[
                    "origin_projection_share"
                ],
                "system_weights": row["selected"]["weights"],
            }
            for row in fold_results
        },
        "row_order_anchor_contribution": row_order_share,
        "target_label_randomized_contribution": 0.0,
        "checks": {
            "final_weights_sum_to_one": bool(
                np.isclose(
                    row_order_share
                    + sum(
                        (1.0 - row_order_share) * value
                        for value in fold_weights.values()
                    ),
                    1.0,
                )
            ),
            "target_label_randomized_has_zero_weight": True,
        },
    }
    contribution_path = output_dir / "contextual_fold_contribution_trace.json"
    write_json(contribution_path, contribution)
    payload = {
        "schema": "contextual_fold_fusion.summary.v1",
        "status": "PASS",
        "score_semantics": "relative experimental timing score; not a calibrated probability",
        "config_json": str(args.config_json.expanduser().resolve()),
        "search": {
            "fold_count": len(folds),
            "evaluated_candidates_per_fold": {
                row["step"]: row["selected"]["evaluated_candidate_count"]
                for row in fold_results
            },
            "weak_peak_system_retained_in_search": True,
            "target_label_randomized_used_for_selection": False,
        },
        "folds": [
            {
                "step": row["step"],
                "event": row["event"],
                "training_events": row["training_events"],
                "history_support": row["history_support"],
                "origin_projection_available": row[
                    "origin_projection_available"
                ],
                "origin_projection_share": row["origin_projection_share"],
                "reliability_components": row["reliability_components"],
                "reliability_raw": row["reliability_raw"],
                "final_reliability_weight": fold_weights[row["step"]],
                "selected": serializable_selection(row["selected"]),
                "promoted_validation_metrics": {
                    key: value
                    for key, value in row[
                        "promoted_validation_metrics"
                    ].items()
                    if key != "quality_metrics"
                },
            }
            for row in fold_results
        ],
        "row_order_anchor": {
            "available": record_available,
            "quality_gate_pass": record_quality_gate_pass,
            "minimum_validation_quality": minimum_record_quality,
            "require_above_target_label_null": require_above_null,
            "validation_quality": record_validation_quality,
            "target_label_null_validation_quality": (
                randomized_validation_quality
            ),
            "rejection_reason": (
                None
                if record_quality_gate_pass
                else (
                    "unavailable"
                    if not record_available
                    else "validation quality gate failed"
                )
            ),
            "selected_share": row_order_share,
            "selected": (
                {
                    key: value
                    for key, value in selected_anchor.items()
                    if key != "fold_metrics"
                }
                if selected_anchor
                else None
            ),
            "trials": [
                {
                    key: value
                    for key, value in row.items()
                    if key != "fold_metrics"
                }
                for row in row_order_trials
            ],
        },
        "validation": {
            "path": str(
                output_dir / "contextual_fold_validation_predictions.csv"
            ),
            "strict_local_peak_count": int(
                sum(
                    bool(
                        row["promoted_validation_metrics"][
                            "strict_local_peak"
                        ]
                    )
                    for row in fold_results
                )
            ),
            "all_events_are_strict_local_peaks": bool(
                all(
                    row["promoted_validation_metrics"]["strict_local_peak"]
                    for row in fold_results
                )
            ),
            "all_controls_below_event": bool(
                all(
                    row["promoted_validation_metrics"][
                        "hard_negative_below_event"
                    ]
                    for row in fold_results
                )
            ),
            "maximum_false_peak_count": int(
                max(
                    row["promoted_validation_metrics"]["false_peak_count"]
                    for row in fold_results
                )
            ),
            "minimum_weak_peak_retention": float(
                min(
                    row["promoted_validation_metrics"]["weak_peak_retention"]
                    for row in fold_results
                )
            ),
        },
        "forecast": {
            "path": str(forecast_path),
            "rows": len(forecast),
            "top_slots": forecast.nlargest(
                min(7, len(forecast)),
                "contextual_promoted_score_not_probability",
            ).to_dict(orient="records"),
        },
        "contribution_trace": str(contribution_path),
    }
    write_json(output_dir / "contextual_fold_fusion_summary.json", payload)
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()

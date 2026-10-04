#!/usr/bin/env python3
"""Fast-select an exact historical start and compact series before ablation.

The complete fixed-cadence grid is a lookup matrix only. Candidate compact histories
retain dense event neighborhoods and select a small number of rows from every
inter-event gap.  Gap rows are a reproducible mix of proximity-weighted and
uniform-random samples.  Candidate quality weights are runtime parameters.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common_v14 import TIMING_META, empirical_percentile, score_quality, write_json
from quantile_preprocessing import QuantileBinTransformer


def parse_ints(value: str) -> list[int]:
    return sorted({int(item.strip()) for item in value.split(",") if item.strip()})


def parse_floats(value: str) -> list[float]:
    return sorted({float(item.strip()) for item in value.split(",") if item.strip()})


def dense_event_rows(
    positives: np.ndarray,
    historical: np.ndarray,
    k_event: int,
) -> set[int]:
    historical_set = set(np.asarray(historical, int).tolist())
    keep: set[int] = set()
    for event in positives:
        keep.update(
            index
            for index in range(int(event) - k_event, int(event) + k_event + 1)
            if index in historical_set
        )
    return keep


def weighted_without_replacement(
    rng: np.random.Generator,
    values: np.ndarray,
    count: int,
    weights: np.ndarray | None,
) -> np.ndarray:
    values = np.asarray(values, int)
    count = min(max(0, int(count)), len(values))
    if count == 0:
        return np.asarray([], int)
    probability = None
    if weights is not None:
        probability = np.asarray(weights, float)
        probability = probability / probability.sum()
    return np.asarray(
        rng.choice(values, size=count, replace=False, p=probability), int
    )


def compact_indices(
    y: np.ndarray,
    historical: np.ndarray,
    k_event: int,
    k_between: int,
    proximity_fraction: float,
    seed: int,
    forced_negative_rows: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    historical = np.asarray(historical, int)
    positives = historical[y[historical] == 1]
    dense = dense_event_rows(positives, historical, k_event)
    forced_negative_rows = np.asarray(
        [] if forced_negative_rows is None else forced_negative_rows, dtype=int
    )
    dense.update(forced_negative_rows.tolist())
    available = np.asarray(
        [index for index in historical if int(index) not in dense], int
    )
    rng = np.random.default_rng(seed)
    gap_rows: list[int] = []
    gap_audit: list[dict[str, Any]] = []

    # searchsorted assigns rows to: prefix, every inter-event gap, and suffix.
    gap_ids = np.searchsorted(positives, available, side="right")
    for gap_id in range(len(positives) + 1):
        pool = available[gap_ids == gap_id]
        requested = min(k_between, len(pool))
        proximity_count = min(
            requested, int(round(requested * proximity_fraction))
        )
        if len(pool):
            distance = np.min(
                np.abs(pool[:, None] - positives[None, :]), axis=1
            ).astype(float)
            weights = 1.0 / np.maximum(distance, 1.0)
        else:
            weights = np.asarray([], float)
        near = weighted_without_replacement(
            rng, pool, proximity_count, weights if len(pool) else None
        )
        remaining = np.asarray(
            [index for index in pool if index not in set(near.tolist())], int
        )
        random_rows = weighted_without_replacement(
            rng, remaining, requested - len(near), None
        )
        selected = np.concatenate([near, random_rows]).astype(int)
        gap_rows.extend(selected.tolist())
        gap_audit.append(
            {
                "gap_id": gap_id,
                "available_rows": len(pool),
                "selected_rows": len(selected),
                "proximity_rows": len(near),
                "random_rows": len(random_rows),
            }
        )
    selected = np.asarray(sorted(dense.union(gap_rows)), int)
    return selected, {
        "positive_bins": len(positives),
        "dense_rows": len(dense),
        "gap_rows": len(set(gap_rows)),
        "selected_historical_rows": len(selected),
        "forced_hard_negative_rows": len(forced_negative_rows),
        "gaps": gap_audit,
    }


def fit_fast_models(
    X: np.ndarray,
    y: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    event_radius: int,
    seed: int,
    quantile_bins: int,
    training_objective_weight: float,
    validation_objective_weight: float,
) -> dict[str, Any]:
    if quantile_bins >= 2:
        transformer = QuantileBinTransformer(quantile_bins).fit(X[train])
        train_X = transformer.transform(X[train])
        validation_X = transformer.transform(X[validation])
    else:
        train_X = X[train]
        validation_X = X[validation]
    models = {
        "logistic": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=0.25,
                max_iter=800,
                class_weight="balanced",
                solver="liblinear",
                random_state=seed,
            ),
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=72,
            max_depth=7,
            min_samples_leaf=2,
            class_weight="balanced",
            max_features="sqrt",
            random_state=seed + 17,
            n_jobs=1,
        ),
    }
    training_scores: dict[str, np.ndarray] = {}
    validation_scores: dict[str, np.ndarray] = {}
    for name, model in models.items():
        model.fit(train_X, y[train])
        raw_train = model.predict_proba(train_X)[:, 1]
        raw_validation = model.predict_proba(validation_X)[:, 1]
        training_scores[name] = empirical_percentile(raw_train, raw_train)
        validation_scores[name] = empirical_percentile(raw_train, raw_validation)
    training_scores["logistic_extra_trees"] = np.mean(
        np.vstack([training_scores["logistic"], training_scores["extra_trees"]]),
        axis=0,
    )
    validation_scores["logistic_extra_trees"] = np.mean(
        np.vstack(
            [validation_scores["logistic"], validation_scores["extra_trees"]]
        ),
        axis=0,
    )
    systems: dict[str, Any] = {}
    for name in training_scores:
        training_metrics = score_quality(
            y[train], training_scores[name], train, event_radius
        )
        validation_metrics = score_quality(
            y[validation],
            validation_scores[name],
            validation,
            event_radius,
        )
        systems[name] = {
            "training_quality": training_metrics["quality_higher_is_better"],
            "validation_quality": validation_metrics["quality_higher_is_better"],
            "combined_25train_75validation": (
                training_objective_weight
                * training_metrics["quality_higher_is_better"]
                + validation_objective_weight
                * validation_metrics["quality_higher_is_better"]
            ),
            "training_metrics": training_metrics,
            "validation_metrics": validation_metrics,
        }
    return systems


def evaluate_candidate(
    frame: pd.DataFrame,
    X: np.ndarray,
    y: np.ndarray,
    historical: np.ndarray,
    outer_events: np.ndarray,
    k_event: int,
    k_between: int,
    proximity_fraction: float,
    event_radius: int,
    seed: int,
    quantile_bins: int,
    training_objective_weight: float,
    validation_objective_weight: float,
    forced_negative_rows: np.ndarray | None = None,
    history_start_date: str | None = None,
    minimum_prevalidation_events: int = 0,
    selection_training_weight: float = 0.20,
    selection_validation_mean_weight: float = 0.60,
    selection_validation_worst_weight: float = 0.20,
    selection_exact_peak_weight: float = 0.0,
) -> dict[str, Any]:
    compact, compact_audit = compact_indices(
        y,
        historical,
        k_event,
        k_between,
        proximity_fraction,
        seed,
        forced_negative_rows,
    )
    folds: list[dict[str, Any]] = []
    for fold_id, event in enumerate(outer_events):
        validation = np.arange(
            int(event) - event_radius,
            int(event) + event_radius + 1,
            dtype=int,
        )
        validation = validation[np.isin(validation, historical)]
        train = compact[compact < validation.min()]
        if int(y[train].sum()) < 5:
            raise RuntimeError("Fast k-factor candidate has fewer than five train events")
        systems = fit_fast_models(
            X,
            y,
            train,
            validation,
            event_radius,
            seed + fold_id * 1009,
            quantile_bins,
            training_objective_weight,
            validation_objective_weight,
        )
        proxy = systems["logistic_extra_trees"]
        profile = proxy["validation_metrics"]["event_profiles"][0]
        folds.append(
            {
                "fold": fold_id + 1,
                "event_slot": str(frame.iloc[event]["date"]),
                "training_rows": len(train),
                "training_events": int(y[train].sum()),
                "training_quality": proxy["training_quality"],
                "validation_quality": proxy["validation_quality"],
                "combined_25train_75validation": proxy[
                    "combined_25train_75validation"
                ],
                "strict_local_peak": bool(profile["strict_local_peak"]),
                "event_percentile_skill": profile["event_percentile_skill"],
                "argmax_offset_slots": profile["argmax_offset_slots"],
                "systems": systems,
            }
        )
    combined = np.asarray(
        [fold["combined_25train_75validation"] for fold in folds], float
    )
    validation = np.asarray([fold["validation_quality"] for fold in folds], float)
    training = np.asarray([fold["training_quality"] for fold in folds], float)
    prevalidation_events = int(
        y[historical[historical < int(np.min(outer_events))]].sum()
    )
    exact_peaks = int(
        sum(bool(fold["strict_local_peak"]) for fold in folds)
    )
    selection_objective = float(
        selection_training_weight * training.mean()
        + selection_validation_mean_weight * validation.mean()
        + selection_validation_worst_weight * validation.min()
        + selection_exact_peak_weight * (exact_peaks / len(folds))
    )
    return {
        "history_start_date": (
            str(history_start_date)
            if history_start_date is not None
            else str(frame.iloc[historical[0]]["date"])
        ),
        "history_start_event_id": str(
            frame.loc[
                frame["date"].astype(str).str.slice(0, 10).eq(
                    str(history_start_date)[:10]
                ),
                "event_id",
            ].iloc[0]
        ),
        "history_start_event_magnitude": float(
            frame.loc[
                frame["date"].astype(str).str.slice(0, 10).eq(
                    str(history_start_date)[:10]
                ),
                "event_mag",
            ].iloc[0]
        ),
        "pre_first_validation_event_count": prevalidation_events,
        "eligible_for_final_nested_validation": bool(
            prevalidation_events >= minimum_prevalidation_events
        ),
        "history_first_retained_date": str(frame.iloc[compact[0]]["date"]),
        "k_event": k_event,
        "k_between": k_between,
        "proximity_fraction": proximity_fraction,
        "selected_historical_rows": len(compact),
        "training_quality_mean": float(training.mean()),
        "validation_quality_mean": float(validation.mean()),
        "validation_quality_worst": float(validation.min()),
        "combined_quality_mean": float(combined.mean()),
        "combined_quality_worst": float(combined.min()),
        "exact_validation_peak_count": exact_peaks,
        "fast_objective": float(0.80 * combined.mean() + 0.20 * combined.min()),
        "selection_objective": selection_objective,
        "folds": folds,
        "compact_audit": compact_audit,
        "compact_indices": compact,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-master", required=True, type=Path)
    parser.add_argument("--output-compact-master", required=True, type=Path)
    parser.add_argument("--output-trials-csv", required=True, type=Path)
    parser.add_argument("--output-selection-json", required=True, type=Path)
    parser.add_argument("--output-selected-indices-csv", required=True, type=Path)
    parser.add_argument("--outer-validation-slots", required=True)
    parser.add_argument(
        "--history-start-dates",
        default="",
        help=(
            "Comma-separated exact master-slot starts tested jointly with every "
            "k-factor combination. Empty preserves the legacy earliest-row start."
        ),
    )
    parser.add_argument(
        "--minimum-prevalidation-events",
        type=int,
        default=0,
        help=(
            "Minimum positive bins required before the first outer holdout. "
            "Use five plus the final inner-validation event count so a fast "
            "candidate cannot be promoted when the final nested fit is infeasible."
        ),
    )
    parser.add_argument("--k-events", default="6,8,12,18,24")
    parser.add_argument("--k-between", default="2,4,8,12,18,24")
    parser.add_argument("--proximity-fractions", default="0.50,0.75,1.0")
    parser.add_argument("--event-radius", type=int, default=6)
    parser.add_argument("--random-seed", type=int, default=713079)
    parser.add_argument("--training-objective-weight", type=float, default=0.25)
    parser.add_argument("--validation-objective-weight", type=float, default=0.75)
    parser.add_argument("--selection-training-weight", type=float, default=0.20)
    parser.add_argument(
        "--selection-validation-mean-weight", type=float, default=0.60
    )
    parser.add_argument(
        "--selection-validation-worst-weight", type=float, default=0.20
    )
    parser.add_argument("--selection-exact-peak-weight", type=float, default=0.0)
    parser.add_argument(
        "--quantile-bins",
        type=int,
        default=0,
        help=(
            "Optional training-fold empirical quantile bins used by the fast "
            "k-factor proxy; 0 disables discretization."
        ),
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1,
        help="Print one progress line every N candidates (and at both endpoints).",
    )
    parser.add_argument(
        "--selection-rank",
        type=int,
        default=1,
        help=(
            "Materialize this one-based rank after evaluating the complete "
            "grid. The ranking itself is always written in full."
        ),
    )
    args = parser.parse_args()
    if args.progress_every < 1:
        raise ValueError("progress-every must be positive")
    if not np.isclose(
        args.training_objective_weight + args.validation_objective_weight, 1.0
    ):
        raise ValueError("training and validation objective weights must sum to one")
    if not np.isclose(
        args.selection_training_weight
        + args.selection_validation_mean_weight
        + args.selection_validation_worst_weight
        + args.selection_exact_peak_weight,
        1.0,
    ):
        raise ValueError("compact selection weights must sum to one")

    frame = pd.read_csv(args.full_master, low_memory=False)
    y = frame["timing_target"].to_numpy(int)
    historical = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
    )
    forced_negative_rows = (
        historical[
            frame.iloc[historical]["hard_negative_control"].fillna(0).astype(int).eq(1).to_numpy()
        ]
        if "hard_negative_control" in frame
        else np.asarray([], dtype=int)
    )
    names = [column for column in frame if column not in TIMING_META]
    X = frame[names].to_numpy(float)
    if not np.isfinite(X).all():
        raise ValueError("Full master contains non-finite model features")
    requested_slots = [
        item.strip() for item in args.outer_validation_slots.split(",") if item.strip()
    ]
    outer_events = []
    for slot in requested_slots:
        matches = np.flatnonzero(frame["date"].astype(str).eq(slot).to_numpy())
        if len(matches) != 1 or y[matches[0]] != 1:
            raise ValueError(f"Outer validation slot is not a unique positive: {slot}")
        outer_events.append(int(matches[0]))
    outer_events_array = np.asarray(sorted(outer_events), int)

    k_events = parse_ints(args.k_events)
    k_between_values = parse_ints(args.k_between)
    proximity_fractions = parse_floats(args.proximity_fractions)
    if min(k_events) < args.event_radius:
        raise ValueError("Every k_event must be at least the validation event radius")
    if any(not 0 <= value <= 1 for value in proximity_fractions):
        raise ValueError("Proximity fractions must lie in [0, 1]")

    requested_start_dates = [
        item.strip()
        for item in str(args.history_start_dates).split(",")
        if item.strip()
    ]
    history_start_dates = requested_start_dates or [
        str(frame.iloc[historical[0]]["date"])
    ]
    dates = frame["date"].astype(str).str.slice(0, 10)
    missing_starts = [
        value for value in history_start_dates if not dates.eq(value).any()
    ]
    if missing_starts:
        raise ValueError(f"History start dates are not exact master slots: {missing_starts}")

    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    total = (
        len(history_start_dates)
        * len(k_events)
        * len(k_between_values)
        * len(proximity_fractions)
    )
    candidate_id = 0
    for history_start_date in history_start_dates:
        candidate_historical = historical[
            dates.iloc[historical].ge(history_start_date).to_numpy()
        ]
        candidate_forced_negatives = forced_negative_rows[
            np.isin(forced_negative_rows, candidate_historical)
        ]
        for k_event in k_events:
            for k_between in k_between_values:
                for proximity_fraction in proximity_fractions:
                    candidate_id += 1
                    if (
                        candidate_id == 1
                        or candidate_id == total
                        or candidate_id % args.progress_every == 0
                    ):
                        print(
                            f"[{candidate_id}/{total}] start={history_start_date} "
                            f"k_event={k_event} k_between={k_between} "
                            f"proximity={proximity_fraction:.2f}",
                            flush=True,
                        )
                    try:
                        result = evaluate_candidate(
                            frame,
                            X,
                            y,
                            candidate_historical,
                            outer_events_array,
                            k_event,
                            k_between,
                            proximity_fraction,
                            args.event_radius,
                            args.random_seed + candidate_id * 101,
                            args.quantile_bins,
                            args.training_objective_weight,
                            args.validation_objective_weight,
                            candidate_forced_negatives,
                            history_start_date,
                            args.minimum_prevalidation_events,
                            args.selection_training_weight,
                            args.selection_validation_mean_weight,
                            args.selection_validation_worst_weight,
                            args.selection_exact_peak_weight,
                        )
                    except (RuntimeError, ValueError) as error:
                        skipped.append(
                            {
                                "candidate_id": candidate_id,
                                "history_start_date": history_start_date,
                                "k_event": k_event,
                                "k_between": k_between,
                                "proximity_fraction": proximity_fraction,
                                "reason": str(error),
                            }
                        )
                        continue
                    result["candidate_id"] = candidate_id
                    candidates.append(result)

    if not candidates:
        raise RuntimeError("Every start-date/k-factor candidate was rejected")

    ranked = sorted(
        candidates,
        key=lambda row: (
            row["eligible_for_final_nested_validation"],
            row["selection_objective"],
            row["validation_quality_mean"],
            row["exact_validation_peak_count"],
            -row["selected_historical_rows"],
        ),
        reverse=True,
    )
    eligible_ranked = [
        row for row in ranked if row["eligible_for_final_nested_validation"]
    ]
    if not eligible_ranked:
        raise RuntimeError(
            "No start-date/k-factor candidate supports the final nested validation"
        )
    if not 1 <= args.selection_rank <= len(eligible_ranked):
        raise ValueError(
            f"selection-rank must be between 1 and {len(eligible_ranked)}, inclusive"
        )
    selected = eligible_ranked[args.selection_rank - 1]
    selected_indices = np.asarray(selected.pop("compact_indices"), int)
    forecast_indices = np.flatnonzero(frame["is_forecast"].eq(1).to_numpy())
    compact_rows = np.asarray(
        sorted(set(selected_indices.tolist()).union(forecast_indices.tolist())), int
    )
    compact_master = frame.iloc[compact_rows].reset_index(drop=True)

    summary_rows = []
    detailed = []
    for rank, row in enumerate(ranked, start=1):
        indices = row.pop("compact_indices", None)
        summary_rows.append(
            {
                "rank": rank,
                "candidate_id": row["candidate_id"],
                "history_start_date": row["history_start_date"],
                "history_start_event_id": row["history_start_event_id"],
                "history_start_event_magnitude": row[
                    "history_start_event_magnitude"
                ],
                "pre_first_validation_event_count": row[
                    "pre_first_validation_event_count"
                ],
                "eligible_for_final_nested_validation": row[
                    "eligible_for_final_nested_validation"
                ],
                "history_first_retained_date": row["history_first_retained_date"],
                "k_event": row["k_event"],
                "k_between": row["k_between"],
                "proximity_fraction": row["proximity_fraction"],
                "selected_historical_rows": row["selected_historical_rows"],
                "training_quality_mean": row["training_quality_mean"],
                "validation_quality_mean": row["validation_quality_mean"],
                "validation_quality_worst": row["validation_quality_worst"],
                "combined_quality_mean": row["combined_quality_mean"],
                "combined_quality_worst": row["combined_quality_worst"],
                "exact_validation_peak_count": row["exact_validation_peak_count"],
                "fast_objective": row["fast_objective"],
                "selection_objective": row["selection_objective"],
            }
        )
        detailed.append(row)

    selection = {
        "status": "COMPLETE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": (
            "Fast Logistic+ExtraTrees proxy; fold quality is "
            f"{args.training_objective_weight:.0%} training and "
            f"{args.validation_objective_weight:.0%} validation. Promotion is "
            f"{args.selection_training_weight:.0%} training mean + "
            f"{args.selection_validation_mean_weight:.0%} validation mean + "
            f"{args.selection_validation_worst_weight:.0%} worst validation fold + "
            f"{args.selection_exact_peak_weight:.0%} exact-peak rate."
        ),
        "preprocessing": {
            "mode": (
                "training-fold empirical quantiles"
                if args.quantile_bins >= 2
                else "raw proxy features"
            ),
            "quantile_bins": args.quantile_bins,
            "fit_scope": "independently on each candidate fold's training rows",
        },
        "sampling_rule": (
            "Keep every row within +/-k_event of every positive bin. In each "
            "prefix/inter-event/suffix gap choose k_between rows, split between "
            "inverse-distance proximity sampling and uniform deterministic random sampling."
        ),
        "outer_validation_slots": requested_slots,
        "history_start_dates_tested": history_start_dates,
        "history_start_search_is_exact_event_aligned": True,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible_ranked),
        "minimum_prevalidation_events": args.minimum_prevalidation_events,
        "skipped_candidate_count": len(skipped),
        "skipped_candidates": skipped,
        "materialized_rank": args.selection_rank,
        "selected": {
            key: value
            for key, value in selected.items()
            if key not in {"folds", "compact_audit"}
        },
        "selected_folds": selected["folds"],
        "selected_compact_audit": selected["compact_audit"],
        "output": {
            "historical_rows": len(selected_indices),
            "forecast_rows": len(forecast_indices),
            "total_rows": len(compact_master),
            "features": len(names),
        },
        "all_candidates": detailed,
    }

    for path in (
        args.output_compact_master,
        args.output_trials_csv,
        args.output_selection_json,
        args.output_selected_indices_csv,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    compact_master.to_csv(args.output_compact_master, index=False)
    pd.DataFrame(summary_rows).to_csv(args.output_trials_csv, index=False)
    write_json(args.output_selection_json, selection)
    pd.DataFrame(
        {
            "full_master_index": selected_indices,
            "date": frame.iloc[selected_indices]["date"].astype(str).to_numpy(),
            "timing_target": y[selected_indices],
        }
    ).to_csv(args.output_selected_indices_csv, index=False)
    print(json.dumps(selection["selected"], indent=2), flush=True)


if __name__ == "__main__":
    main()

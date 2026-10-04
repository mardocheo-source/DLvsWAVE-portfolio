#!/usr/bin/env python3
"""Parameterized timing pipeline with validation-gated peak isolation."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
import json
import os
from pathlib import Path
import signal
import time
import warnings

os.environ.setdefault("MPLCONFIGDIR", "/tmp/japan-180d-deephistory-v14")

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from quantile_preprocessing import QuantileBinTransformer

from common_v14 import (
    BASES,
    PROJECT,
    SYSTEMS,
    TIMING_META,
    empirical_percentile,
    evaluate_feature_set,
    export_lcs_rules,
    fit_real_binary,
    internal_local_maxima,
    isolated_indices,
    model_configuration,
    positive_weights,
    rank_features,
    sample_timing,
    score_quality,
    sha256,
    tie_aware_consensus,
    tied_percentile,
    write_json,
)


SEED = 560601
EXPECTED_MASTER_SHA256 = "c90eef6e46fd77152c07decb2fa0c2f97599ded37ae3decc2b8decf503921464"
PROXY_BASES = BASES
PROXY_SYSTEMS = SYSTEMS
BASES = (*BASES, "screening_anchor")
SYSTEMS = {
    **SYSTEMS,
    "screening_anchor": ("screening_anchor",),
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Leakage-aware timing with a gated peak-isolation search"
    )
    value.add_argument("--validation-event-count", type=int, default=2)
    value.add_argument(
        "--outer-validation-slots",
        default=None,
        help=(
            "Comma-separated exact slot starts to use as chronological "
            "outer validation events. When omitted, the latest "
            "--validation-event-count positive slots are used."
        ),
    )
    value.add_argument("--inner-validation-events", type=int, default=3)
    value.add_argument(
        "--training-mode",
        choices=("sequential", "one_shot", "randomized", "historical_record_shuffle"),
        default="sequential",
        help=(
            "sequential runs the primary chronological pipeline; one_shot runs "
            "one real-label validation fit and one full-history forecast fit; randomized "
            "runs the one-shot label-permutation control; "
            "historical_record_shuffle permutes complete training records "
            "while preserving every feature-target pair. Controls never "
            "overwrite or contribute weight to the primary forecast."
        ),
    )
    value.add_argument("--random-seed", type=int, default=560699)
    value.add_argument(
        "--historical-record-seed",
        type=int,
        default=560733,
        help="First permutation seed for historical_record_shuffle.",
    )
    value.add_argument(
        "--historical-record-repeats",
        type=int,
        default=1,
        help=(
            "Number of independently permuted intact-record fits; aggregate "
            "predictions are written without validation-based repeat selection."
        ),
    )
    value.add_argument(
        "--historical-record-aggregation",
        choices=("mean", "median"),
        default="mean",
        help="Label-free aggregation across historical-record permutations.",
    )
    value.add_argument(
        "--historical-record-model-seed-base",
        type=int,
        default=560601,
        help=(
            "Fixed model seed base across record permutations so the experiment "
            "isolates training-order sensitivity."
        ),
    )
    value.add_argument(
        "--resume-completed-folds",
        action="store_true",
        help=(
            "Reuse fully persisted outer-fold predictions and summaries, then "
            "resume ensemble/final fitting without repeating feature ablation."
        ),
    )
    value.add_argument(
        "--precompacted-master",
        action="store_true",
        help=(
            "Treat historical rows as the already selected k-factor compact series. "
            "Do not perform a second temporal history sampling after feature search."
        ),
    )
    value.add_argument(
        "--interval-days",
        type=int,
        default=60,
        help="Exact fixed grid cadence in days; V14 configures 180 days.",
    )
    value.add_argument(
        "--history-start-years",
        default="1920",
        help="Comma-separated training-history start years tested after feature search.",
    )
    value.add_argument(
        "--history-event-radii",
        default="2,3",
        help="Comma-separated event-neighbourhood radii tested during history search.",
    )
    value.add_argument(
        "--history-between-records",
        default="3,4",
        help="Comma-separated between-event row counts tested during history search.",
    )
    value.add_argument(
        "--outer-history-policy",
        choices=("inner_search", "master_fingerprint"),
        default="inner_search",
        help=(
            "Select history only on inner folds, or reuse the explicitly "
            "audited master-screening fingerprint for every outer fit."
        ),
    )
    value.add_argument(
        "--master-selection-json",
        default="",
        help=(
            "Master-search selection JSON used when --outer-history-policy "
            "is master_fingerprint."
        ),
    )
    value.add_argument(
        "--screening-anchor-seed-base",
        type=int,
        default=0,
        help=(
            "Seed used by the selected master-screening anchor in fold 1; "
            "later folds add 101 deterministically."
        ),
    )
    value.add_argument("--event-radius", type=int, default=6)
    value.add_argument("--gate-maximum-argmax-offset-slots", type=int, default=1)
    value.add_argument("--gate-minimum-event-percentile-skill", type=float, default=0.92)
    value.add_argument("--gate-minimum-weak-peak-retention-skill", type=float, default=0.72)
    value.add_argument("--gate-minimum-delayed-false-peak-control", type=float, default=0.45)
    value.add_argument(
        "--gate-maximum-competing-false-peak-count",
        type=int,
        default=0,
    )
    value.add_argument(
        "--gate-false-peak-competitor-margin",
        type=float,
        default=0.02,
        help=(
            "A non-event local maximum is a competing false peak when its "
            "score is at least event_score minus this margin."
        ),
    )
    value.add_argument("--gate-minimum-fold-quality", type=float, default=0.65)
    value.add_argument("--gate-minimum-mean-quality", type=float, default=0.70)
    value.add_argument(
        "--gate-allow-sole-weak-peaks",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    value.add_argument("--feature-min", type=int, default=5)
    value.add_argument("--probe-budget", type=int, default=32)
    value.add_argument("--probe-block-size", type=int, default=4)
    value.add_argument("--quality-tolerance", type=float, default=0.008)
    value.add_argument("--total-quality-tolerance", type=float, default=0.020)
    value.add_argument("--system-floor-tolerance", type=float, default=0.040)
    value.add_argument("--weak-peak-tolerance", type=float, default=0.080)
    value.add_argument("--epochs-scale", type=float, default=0.75)
    value.add_argument(
        "--final-attempt-time-limit-seconds",
        type=float,
        default=0.0,
        help=(
            "Hard wall-clock limit for each final base-model fit plus inference. "
            "Zero preserves the legacy unlimited behaviour."
        ),
    )
    value.add_argument(
        "--model-profile",
        choices=("standard", "deep", "xdeep"),
        default="standard",
        help=(
            "Capacity profile applied consistently to LCS, KAN, deep nets, "
            "logistic/tree anchors, and their hybrid systems."
        ),
    )
    value.add_argument(
        "--quantile-bins",
        type=int,
        default=0,
        help=(
            "Fit an empirical ordinal quantizer independently on each training "
            "fold. Zero disables it; V17 uses four bins with levels "
            "0, 1/3, 2/3 and 1."
        ),
    )
    value.add_argument(
        "--model-overrides-json",
        default="",
        help="JSON of promoted per-family hyperparameters from a fast screen.",
    )
    value.add_argument("--actual-guard-epochs-scale", type=float, default=0.55)
    value.add_argument(
        "--calibration-mode",
        choices=("midrank_ecdf", "linear_interpolated"),
        default="midrank_ecdf",
        help=(
            "Label-free mapping of model outputs against the chronological "
            "training reference. Linear interpolation preserves within-bin "
            "ordering on small compact masters."
        ),
    )
    value.add_argument(
        "--hard-negative-replay",
        type=int,
        default=1,
        help=(
            "Effective multiplicity of configured hard-negative training rows. "
            "The control flag is used only for sampling and is never a feature."
        ),
    )
    value.add_argument(
        "--forecast-start",
        default="2026-07-15",
        help="Visible retrospective forecast window; the exact grid may begin earlier.",
    )
    value.add_argument(
        "--forecast-grid-start",
        default="2026-07-11",
        help=(
            "First exact slot start; all rows on or after this date "
            "are excluded from model fitting."
        ),
    )
    value.add_argument("--forecast-end", default="2026-09-04")
    value.add_argument("--region-label", default="Japan")
    value.add_argument("--timing-magnitude-threshold", type=float, default=7.9)
    value.add_argument(
        "--timing-validation-magnitude-threshold",
        type=float,
        default=None,
        help=(
            "Optional lower floor allowed only for explicitly configured outer "
            "timing holdouts; defaults to --timing-magnitude-threshold."
        ),
    )
    value.add_argument(
        "--hard-negative-training-magnitude-threshold",
        type=float,
        default=None,
    )
    value.add_argument(
        "--hard-negative-validation-magnitude-threshold",
        type=float,
        default=None,
    )
    value.add_argument("--location-magnitude-threshold", type=float, default=7.1)
    value.add_argument(
        "--location-validation-magnitude-threshold",
        type=float,
        default=None,
        help=(
            "Outer location-holdout floor recorded in the run contract; defaults "
            "to --location-magnitude-threshold. Location fitting is executed by "
            "the shared localization runner with the same value."
        ),
    )
    value.add_argument(
        "--expected-master-sha256",
        default=EXPECTED_MASTER_SHA256,
        help="Audited timing-master checksum; pass an empty string to disable.",
    )
    value.add_argument("--training-objective-weight", type=float, default=0.25)
    value.add_argument("--validation-objective-weight", type=float, default=0.75)
    value.add_argument("--peak-search-trials", type=int, default=24000)
    value.add_argument("--ensemble-weight-floor", type=float, default=0.002)
    value.add_argument("--alias-max-lag", type=int, default=6)
    value.add_argument("--alias-symmetry-tolerance", type=int, default=0)
    value.add_argument("--alias-suppression-radius", type=int, default=1)
    value.add_argument(
        "--alias-strengths",
        default="0.40,0.60,0.75,0.85,0.92",
        help="Comma-separated soft suppression strengths tested by outer validation.",
    )
    value.add_argument("--minimum-isolation-gain", type=float, default=0.010)
    value.add_argument(
        "--credible-peak-min-prominence",
        type=float,
        default=0.02,
        help=(
            "Minimum local prominence for a non-event maximum to count as a "
            "credible false peak; the event peak itself is never thresholded away."
        ),
    )
    value.add_argument(
        "--isolation-metric-weights",
        default=(
            "exact_peak=0.22,event_rank=0.14,local_prominence=0.14,"
            "global_competitor=0.12,false_peak_control=0.16,"
            "false_peak_energy=0.12,background_control=0.10"
        ),
        help="Comma-separated higher-is-better metric weights; values must sum to one.",
    )
    return value


def validate_args(args) -> None:
    if args.validation_event_count < 1:
        raise ValueError("validation-event-count must be positive")
    if args.quantile_bins not in {0} and args.quantile_bins < 2:
        raise ValueError("quantile-bins must be zero (disabled) or at least two")
    if args.historical_record_repeats < 1:
        raise ValueError("historical-record-repeats must be positive")
    if args.interval_days < 1:
        raise ValueError("interval-days must be positive")
    if args.final_attempt_time_limit_seconds < 0:
        raise ValueError("final-attempt-time-limit-seconds cannot be negative")
    if args.inner_validation_events < 2:
        raise ValueError("At least two inner events are required")
    for name in (
        "history_start_years",
        "history_event_radii",
        "history_between_records",
    ):
        values = [
            int(item.strip())
            for item in str(getattr(args, name)).split(",")
            if item.strip()
        ]
        if not values or any(value < 0 for value in values):
            raise ValueError(f"{name.replace('_', '-')} must contain non-negative integers")
    if args.feature_min < 5:
        raise ValueError("feature-min cannot be below the user-defined floor of five")
    if args.hard_negative_replay < 1:
        raise ValueError("hard-negative-replay must be at least one")
    if args.probe_block_size < 1 or args.probe_budget < args.probe_block_size:
        raise ValueError("Invalid probing budget")
    if not np.isclose(
        args.training_objective_weight + args.validation_objective_weight, 1.0
    ):
        raise ValueError("training and validation objective weights must sum to one")
    if min(args.training_objective_weight, args.validation_objective_weight) <= 0:
        raise ValueError("training and validation objective weights must be positive")
    if args.peak_search_trials < len(SYSTEMS):
        raise ValueError("peak-search-trials must be at least the system count")
    if not 0 <= args.ensemble_weight_floor < 1 / len(SYSTEMS):
        raise ValueError("ensemble-weight-floor is incompatible with system count")
    if args.alias_max_lag < 1:
        raise ValueError("alias-max-lag must be at least one slot")
    if args.alias_suppression_radius < 0:
        raise ValueError("alias-suppression-radius cannot be negative")
    if args.alias_max_lag >= 2 and args.event_radius < args.alias_max_lag + 1:
        raise ValueError(
            "False-peak search is structurally inapplicable: with censored "
            "window endpoints, event-radius must be at least alias-max-lag + 1"
        )
    if not 0 <= args.credible_peak_min_prominence < 1:
        raise ValueError("credible-peak-min-prominence must be in [0, 1)")
    if (
        args.gate_maximum_competing_false_peak_count < 0
        or args.gate_false_peak_competitor_margin < 0.0
    ):
        raise ValueError("Invalid competing-false-peak gate")
    alias_strengths = [float(value) for value in args.alias_strengths.split(",")]
    if not alias_strengths or any(value <= 0 or value >= 1 for value in alias_strengths):
        raise ValueError("alias-strengths must contain values in (0, 1)")
    metric_weights = {
        key.strip(): float(number)
        for key, number in (
            item.split("=", 1)
            for item in args.isolation_metric_weights.split(",")
            if item.strip()
        )
    }
    expected_metrics = {
        "exact_peak",
        "event_rank",
        "local_prominence",
        "global_competitor",
        "false_peak_control",
        "false_peak_energy",
        "background_control",
    }
    if set(metric_weights) != expected_metrics or not np.isclose(
        sum(metric_weights.values()), 1.0
    ):
        raise ValueError(
            "isolation-metric-weights must define every supported metric and sum to one"
        )
    grid_start = pd.Timestamp(args.forecast_grid_start)
    visible_start = pd.Timestamp(args.forecast_start)
    if not (
        grid_start
        <= visible_start
        < grid_start + pd.Timedelta(days=args.interval_days)
    ):
        raise ValueError("forecast-start must fall inside the first exact grid slot")


def select_outer_events(
    frame: pd.DataFrame,
    historical: np.ndarray,
    y: np.ndarray,
    args,
) -> tuple[np.ndarray, dict]:
    """Resolve validation events from CLI slots, with a count-based fallback."""
    positive = historical[y[historical] == 1]
    if not args.outer_validation_slots:
        if len(positive) < args.validation_event_count:
            raise RuntimeError("Insufficient positive slots for outer validation")
        selected = positive[-args.validation_event_count :]
        return selected, {
            "mode": "latest_positive_slots",
            "requested_count": int(args.validation_event_count),
            "resolved_slots": frame.iloc[selected]["date"].astype(str).tolist(),
        }

    requested = [
        pd.Timestamp(value.strip()).strftime("%Y-%m-%d")
        for value in args.outer_validation_slots.split(",")
        if value.strip()
    ]
    if not requested or len(requested) != len(set(requested)):
        raise ValueError(
            "outer-validation-slots must contain unique comma-separated dates"
        )
    positive_dates = frame.iloc[positive]["date"].astype(str)
    resolved = []
    missing = []
    for slot in requested:
        matches = positive[positive_dates.eq(slot).to_numpy()]
        if len(matches) != 1:
            missing.append(slot)
        else:
            resolved.append(int(matches[0]))
    if missing:
        raise ValueError(
            "Requested validation slots are not unique positive historical rows: "
            + ", ".join(missing)
        )
    selected = np.asarray(sorted(resolved), dtype=int)
    return selected, {
        "mode": "explicit_exact_slot_starts",
        "requested_slots": requested,
        "resolved_slots": frame.iloc[selected]["date"].astype(str).tolist(),
    }


def manifest(args, frame: pd.DataFrame, names: list[str], safe_features: list[int]):
    master = PROJECT / "01_inputs/timing_master.csv"
    payload = {
        "pipeline": PROJECT.name,
        "created_at": pd.Timestamp.now(tz="Asia/Tokyo").isoformat(),
        "parameters": vars(args),
        "base_model_configurations": {
            member: (
                {
                    "family": "screening-anchor ensemble",
                    "implementation": (
                        "mean of L2 logistic regression and ExtraTrees; "
                        "chronologically refitted in every fold"
                    ),
                    "logistic_C": 0.25,
                    "extra_trees_estimators": 64,
                    "extra_trees_max_depth": 6,
                    "extra_trees_min_samples_leaf": 3,
                    "calibration_reference": "selected training sample",
                }
                if member == "screening_anchor"
                else model_configuration(
                    member,
                    args.epochs_scale,
                    len(safe_features),
                )
            )
            for member in BASES
        },
        "input": {
            "master": str(master),
            "sha256": sha256(master),
            "expected_sha256": args.expected_master_sha256 or None,
            "rows": len(frame),
            "total_features": len(names),
            "native_safe_start_features": len(safe_features),
        },
        "contracts": {
            "target": (
                f"{args.region_label} training target M>="
                f"{args.timing_magnitude_threshold:g}; explicitly configured outer "
                "holdouts may use M>="
                f"{(args.timing_validation_magnitude_threshold if args.timing_validation_magnitude_threshold is not None else args.timing_magnitude_threshold):g}"
            ),
            "hard_negative_controls": (
                "selected worldwide non-Japan "
                "event bins remain target 0; training/validation floors are "
                f"M>={(args.hard_negative_training_magnitude_threshold if args.hard_negative_training_magnitude_threshold is not None else args.timing_magnitude_threshold):g}/"
                f"{(args.hard_negative_validation_magnitude_threshold if args.hard_negative_validation_magnitude_threshold is not None else args.timing_magnitude_threshold):g}; "
                "their model event magnitude and coordinates are neutralized, while "
                "identity/place are metadata and original values remain audit-only"
                if "hard_negative_control" in frame
                and frame["hard_negative_control"].fillna(0).astype(int).any()
                else "disabled"
            ),
            "stress_test": False,
            "metric_direction": "every selection metric is normalized so higher is better",
            "feature_policy": (
                "start from the v4 native-safe set; statistical ranking orders probes "
                "but cannot remove a feature; practical proxy and real-model guards decide"
            ),
            "outer_validation": (
                "incremental chronological folds resolved from parameters; an event "
                "is excluded from its own training and becomes available only to "
                "later folds"
            ),
            "forecast_training_cutoff": (
                f"all rows on or after {args.forecast_grid_start} are excluded from "
                "training"
            ),
            "grid": (
                f"all rows align to exact fixed {args.interval_days}-day source slots; "
                "historical rows may be sparse after pre-feature k-factor compaction, "
                "while forecast rows remain contiguous; date is the inclusive slot "
                "start and slot_end_inclusive is start + interval - 1 day"
            ),
            "peak_isolation": (
                "all system variants retain positive ensemble weight; a symmetric "
                "alias penalty is applied only when every outer fold retains the "
                "event peak and the configured multi-metric objective improves"
            ),
            "scientific_scope": (
                "retrospective research diagnostic, not an operational earthquake "
                "prediction; this run alone is insufficient for a definitive "
                "physical-connection conclusion"
            ),
        },
    }
    if (
        args.expected_master_sha256
        and payload["input"]["sha256"] != args.expected_master_sha256
    ):
        raise RuntimeError("Timing master checksum differs from the audited v4/v5 master")
    write_json(PROJECT / "00_config/run_manifest.json", payload)


def inner_split(
    y: np.ndarray,
    outer_train_pool: np.ndarray,
    event_count: int,
    radius: int,
):
    positives = outer_train_pool[y[outer_train_pool] == 1]
    if len(positives) <= event_count:
        raise ValueError("Not enough events for chronological inner validation")
    chosen = positives[-event_count:]
    validation = isolated_indices(chosen, radius, len(y))
    validation = validation[np.isin(validation, outer_train_pool)]
    train_pool = outer_train_pool[outer_train_pool < validation.min()]
    if int(y[train_pool].sum()) < 5:
        raise ValueError("The inner training fold has fewer than five events")
    return train_pool, validation, chosen


def history_candidates(args) -> list[dict]:
    """Return the complete parameter-driven history-search grid."""
    start_years = sorted(
        {
            int(item.strip())
            for item in str(args.history_start_years).split(",")
            if item.strip()
        }
    )
    radii = sorted(
        {
            int(item.strip())
            for item in str(args.history_event_radii).split(",")
            if item.strip()
        }
    )
    between_counts = sorted(
        {
            int(item.strip())
            for item in str(args.history_between_records).split(",")
            if item.strip()
        }
    )
    return [
        {
            "start_year": start_year,
            "event_radius": radius,
            "between_records_per_event": between,
        }
        for start_year in start_years
        for radius in radii
        for between in between_counts
    ]


def acceptance(
    candidate: dict,
    current: dict,
    reference: dict,
    args,
) -> tuple[bool, list[str]]:
    reasons = []
    if (
        candidate["aggregate_quality_higher_is_better"]
        < current["aggregate_quality_higher_is_better"] - args.quality_tolerance
    ):
        reasons.append("current_quality_damage")
    if (
        candidate["aggregate_quality_higher_is_better"]
        < reference["aggregate_quality_higher_is_better"]
        - args.total_quality_tolerance
    ):
        reasons.append("cumulative_quality_damage")
    if (
        candidate["system_quality_min"]
        < reference["system_quality_min"] - args.system_floor_tolerance
    ):
        reasons.append("system_floor_damage")
    if (
        candidate["weak_peak_retention_min"]
        < reference["weak_peak_retention_min"] - args.weak_peak_tolerance
    ):
        reasons.append("weak_peak_damage")
    return not reasons, reasons


def compact_evaluation(payload: dict) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if key != "base_scores"
    }


def smart_ablation(
    step_name: str,
    X: np.ndarray,
    y: np.ndarray,
    dates: pd.Series,
    names: list[str],
    initial_features: list[int],
    inner_train_pool: np.ndarray,
    inner_validation: np.ndarray,
    args,
    seed: int,
) -> dict:
    output = PROJECT / f"03_feature_research/timing/{step_name}"
    output.mkdir(parents=True, exist_ok=True)
    if args.precompacted_master:
        training = np.asarray(inner_train_pool, int)
    else:
        default_history = history_candidates(args)[0]
        training = sample_timing(
            inner_train_pool, dates, y, **default_history
        )
    search_X = X
    if args.quantile_bins >= 2:
        quantizer = QuantileBinTransformer(args.quantile_bins).fit(
            X[training][:, initial_features]
        )
        search_X = X.copy()
        search_X[:, initial_features] = quantizer.transform(
            X[:, initial_features]
        )
    ranking, ranking_audit = rank_features(
        search_X[training], y[training], initial_features, names, seed
    )
    ranking_audit["preprocessing"] = (
        quantizer.audit()
        if args.quantile_bins >= 2
        else {"mode": "raw_proxy_features", "n_bins": 0}
    )
    write_json(output / "statistical_ranking.json", ranking_audit)
    baseline = evaluate_feature_set(
        search_X,
        y,
        training,
        inner_train_pool,
        inner_validation,
        initial_features,
        args.event_radius,
        seed + 100,
    )
    current_features = list(initial_features)
    current = baseline
    low_to_high = list(reversed(ranking))
    trials: list[dict] = []
    keys: list[dict] = []
    attempted: set[int] = set()
    cursor = 0
    trial_id = 0

    while len(attempted) < args.probe_budget and cursor < len(low_to_high):
        block = []
        while (
            cursor < len(low_to_high)
            and len(block) < args.probe_block_size
            and len(attempted) + len(block) < args.probe_budget
        ):
            feature = low_to_high[cursor]
            cursor += 1
            if feature in current_features and feature not in attempted:
                block.append(feature)
        if not block:
            continue
        attempted.update(block)
        trial_id += 1
        candidate_features = [
            feature for feature in current_features if feature not in set(block)
        ]
        candidate = evaluate_feature_set(
            search_X,
            y,
            training,
            inner_train_pool,
            inner_validation,
            candidate_features,
            args.event_radius,
            seed + 100,
        )
        accepted, reasons = acceptance(candidate, current, baseline, args)
        trials.append(
            {
                "trial": trial_id,
                "phase": "block_probe",
                "removed": [names[index] for index in block],
                "feature_count_before": len(current_features),
                "feature_count_after": len(candidate_features),
                "accepted": accepted,
                "reasons": reasons,
                "quality_before": current["aggregate_quality_higher_is_better"],
                "quality_after": candidate["aggregate_quality_higher_is_better"],
                "weak_peak_before": current["weak_peak_retention_min"],
                "weak_peak_after": candidate["weak_peak_retention_min"],
                "system_floor_before": current["system_quality_min"],
                "system_floor_after": candidate["system_quality_min"],
            }
        )
        if accepted and len(candidate_features) >= args.feature_min:
            current_features = candidate_features
            current = candidate
            continue

        for feature in block:
            if feature not in current_features or len(current_features) <= args.feature_min:
                continue
            trial_id += 1
            candidate_features = [
                value for value in current_features if value != feature
            ]
            candidate = evaluate_feature_set(
                search_X,
                y,
                training,
                inner_train_pool,
                inner_validation,
                candidate_features,
                args.event_radius,
                seed + 100,
            )
            accepted_one, reasons_one = acceptance(
                candidate, current, baseline, args
            )
            quality_damage = float(
                current["aggregate_quality_higher_is_better"]
                - candidate["aggregate_quality_higher_is_better"]
            )
            weak_damage = float(
                current["weak_peak_retention_min"]
                - candidate["weak_peak_retention_min"]
            )
            system_damage = {
                system: float(
                    current["systems"][system]["combined_25train_75validation"]
                    - candidate["systems"][system][
                        "combined_25train_75validation"
                    ]
                )
                for system in PROXY_SYSTEMS
            }
            trials.append(
                {
                    "trial": trial_id,
                    "phase": "individual_probe",
                    "removed": [names[feature]],
                    "feature_count_before": len(current_features),
                    "feature_count_after": len(candidate_features),
                    "accepted": accepted_one,
                    "reasons": reasons_one,
                    "quality_before": current["aggregate_quality_higher_is_better"],
                    "quality_after": candidate["aggregate_quality_higher_is_better"],
                    "quality_damage": quality_damage,
                    "weak_peak_before": current["weak_peak_retention_min"],
                    "weak_peak_after": candidate["weak_peak_retention_min"],
                    "weak_peak_damage": weak_damage,
                    "system_floor_before": current["system_quality_min"],
                    "system_floor_after": candidate["system_quality_min"],
                }
            )
            if accepted_one:
                current_features = candidate_features
                current = candidate
            else:
                keys.append(
                    {
                        "feature": names[feature],
                        "index": int(feature),
                        "quality_damage": quality_damage,
                        "weak_peak_damage": weak_damage,
                        "largest_system_damage": max(system_damage.values()),
                        "most_damaged_system": max(
                            system_damage, key=system_damage.get
                        ),
                        "rejection_reasons": reasons_one,
                        "system_damage_higher_positive_means_more_important": system_damage,
                    }
                )

    pd.DataFrame(
        [
            {
                **row,
                "removed": json.dumps(row["removed"], ensure_ascii=False),
                "reasons": json.dumps(row["reasons"], ensure_ascii=False),
            }
            for row in trials
        ]
    ).to_csv(output / "ablation_trials.csv", index=False)
    keys = sorted(
        keys,
        key=lambda row: (
            -max(row["quality_damage"], row["weak_peak_damage"]),
            -row["largest_system_damage"],
        ),
    )
    write_json(output / "key_features.json", keys)
    result = {
        "starting_feature_count": len(initial_features),
        "selected_feature_count_before_real_guard": len(current_features),
        "selected_indices_before_real_guard": current_features,
        "selected_features_before_real_guard": [
            names[index] for index in current_features
        ],
        "baseline": compact_evaluation(baseline),
        "selected_proxy_evaluation": compact_evaluation(current),
        "attempted_feature_count": len(attempted),
        "removed_feature_count": len(initial_features) - len(current_features),
        "key_features": keys,
        "trial_count": len(trials),
        "selection_uses_outer_event": False,
    }
    write_json(output / "proxy_selection.json", result)
    return {
        **result,
        "selected_indices": current_features,
        "training_sample": training,
    }


def fit_real_bank(
    X: np.ndarray,
    y: np.ndarray,
    train_sample: np.ndarray,
    reference_pool: np.ndarray,
    predict_sets: dict[str, np.ndarray],
    features: list[int],
    seed: int,
    epochs_scale: float,
    calibration_mode: str = "midrank_ecdf",
    screening_anchor_seed: int | None = None,
) -> dict:
    attempt_limit = float(
        os.environ.get("DLVSWAVE_FINAL_ATTEMPT_TIMEOUT_SECONDS", "0")
    )
    old_alarm_handler = None
    if attempt_limit > 0:
        old_alarm_handler = signal.getsignal(signal.SIGALRM)

        def raise_attempt_timeout(signum, frame):
            del signum, frame
            raise TimeoutError(
                f"Final model attempt exceeded {attempt_limit:.3f} seconds"
            )

        signal.signal(signal.SIGALRM, raise_attempt_timeout)
    quantile_bins = int(os.environ.get("DLVSWAVE_QUANTILE_BINS", "0"))
    scaler = (
        QuantileBinTransformer(quantile_bins)
        if quantile_bins >= 2
        else StandardScaler()
    )
    scaler.fit(X[train_sample][:, features])
    fit_X = scaler.transform(X[train_sample][:, features])
    reference_X = scaler.transform(X[reference_pool][:, features])
    transformed = {
        name: scaler.transform(X[indices][:, features])
        for name, indices in predict_sets.items()
    }
    models = {}
    raw_reference = {}
    reference_scores = {}
    raw_outputs = {name: {} for name in predict_sets}
    outputs = {name: {} for name in predict_sets}
    runtimes = {}
    for member_id, member in enumerate(BASES):
        member_started = time.perf_counter()
        if attempt_limit > 0:
            signal.setitimer(signal.ITIMER_REAL, attempt_limit)
        member_seed = (
            int(screening_anchor_seed)
            if member == "screening_anchor"
            and screening_anchor_seed is not None
            else seed + member_id * 53
        )
        if member == "screening_anchor":
            logistic = LogisticRegression(
                C=0.25,
                class_weight="balanced",
                max_iter=800,
                solver="liblinear",
                random_state=member_seed,
            )
            trees = ExtraTreesClassifier(
                n_estimators=64,
                max_depth=6,
                min_samples_leaf=3,
                class_weight="balanced",
                max_features="sqrt",
                random_state=member_seed + 17,
                n_jobs=1,
            )
            logistic.fit(fit_X, y[train_sample])
            trees.fit(fit_X, y[train_sample])
            model = {
                "logistic": logistic,
                "extra_trees": trees,
            }
            fitted = (logistic, trees)
            calibration_members = [
                fitted_model.predict_proba(fit_X)[:, 1]
                for fitted_model in fitted
            ]
            reference_members = [
                fitted_model.predict_proba(reference_X)[:, 1]
                for fitted_model in fitted
            ]
            raw_reference[member] = np.mean(
                np.vstack(reference_members),
                axis=0,
            )
            reference_scores[member] = np.mean(
                np.vstack(
                    [
                        empirical_percentile(
                            calibration,
                            reference,
                            calibration_mode,
                        )
                        for calibration, reference in zip(
                            calibration_members,
                            reference_members,
                        )
                    ]
                ),
                axis=0,
            )
            for name, values in transformed.items():
                prediction_members = [
                    fitted_model.predict_proba(values)[:, 1]
                    for fitted_model in fitted
                ]
                raw_outputs[name][member] = np.mean(
                    np.vstack(prediction_members),
                    axis=0,
                )
                outputs[name][member] = np.mean(
                    np.vstack(
                        [
                            empirical_percentile(
                                calibration,
                                prediction,
                                calibration_mode,
                            )
                            for calibration, prediction in zip(
                                calibration_members,
                                prediction_members,
                            )
                        ]
                    ),
                    axis=0,
                )
            models[member] = model
            runtimes[member] = {
                "fit_and_inference_seconds": float(time.perf_counter() - member_started),
                "time_limit_seconds": attempt_limit,
                "finished_within_time_limit": True,
                "training_rows": int(len(train_sample)),
                "feature_count": int(len(features)),
            }
            if attempt_limit > 0:
                signal.setitimer(signal.ITIMER_REAL, 0)
            continue
        else:
            model, predict = fit_real_binary(
                member,
                fit_X,
                y[train_sample],
                member_seed,
                epochs_scale,
            )
            calibration_reference = None
        raw_reference[member] = predict(reference_X)
        reference_scores[member] = empirical_percentile(
            (
                calibration_reference
                if calibration_reference is not None
                else raw_reference[member]
            ),
            raw_reference[member],
            calibration_mode,
        )
        for name, values in transformed.items():
            raw_outputs[name][member] = predict(values)
            outputs[name][member] = empirical_percentile(
                (
                    calibration_reference
                    if calibration_reference is not None
                    else raw_reference[member]
                ),
                raw_outputs[name][member],
                calibration_mode,
            )
        models[member] = model
        runtimes[member] = {
            "fit_and_inference_seconds": float(time.perf_counter() - member_started),
            "time_limit_seconds": attempt_limit,
            "finished_within_time_limit": True,
            "training_rows": int(len(train_sample)),
            "feature_count": int(len(features)),
        }
        if attempt_limit > 0:
            signal.setitimer(signal.ITIMER_REAL, 0)
    if attempt_limit > 0:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm_handler)
    return {
        "models": models,
        "scaler": scaler,
        "raw_reference": raw_reference,
        "reference_scores": reference_scores,
        "raw_outputs": raw_outputs,
        "outputs": outputs,
        "runtimes": runtimes,
        "preprocessing": (
            scaler.audit()
            if isinstance(scaler, QuantileBinTransformer)
            else {"mode": "training_fold_standard_scaler", "n_bins": 0}
        ),
    }


def replay_hard_negative_rows(
    frame: pd.DataFrame,
    sample: np.ndarray,
    multiplicity: int,
) -> np.ndarray:
    """Replay hard negatives for fitting without exposing their flag as a feature."""
    sample = np.asarray(sample, int)
    if multiplicity <= 1 or "hard_negative_control" not in frame:
        return sample
    flags = (
        frame.loc[sample, "hard_negative_control"]
        .fillna(0)
        .to_numpy(int)
    )
    controls = sample[flags == 1]
    if not len(controls):
        return sample
    return np.concatenate((sample, np.repeat(controls, multiplicity - 1)))


def real_guard(
    step_name: str,
    X: np.ndarray,
    y: np.ndarray,
    frame: pd.DataFrame,
    names: list[str],
    train_sample: np.ndarray,
    train_pool: np.ndarray,
    validation: np.ndarray,
    baseline_features: list[int],
    selected_features: list[int],
    args,
    seed: int,
) -> dict:
    variants = {
        "native_safe_baseline": baseline_features,
        "smart_ablation_candidate": selected_features,
    }
    evaluations = {}
    for variant, features in variants.items():
        effective_sample = replay_hard_negative_rows(
            frame,
            train_sample,
            args.hard_negative_replay,
        )
        bank = fit_real_bank(
            X,
            y,
            effective_sample,
            train_pool,
            {"validation": validation},
            features,
            seed,
            args.actual_guard_epochs_scale,
            args.calibration_mode,
        )
        systems = {}
        for system, members in SYSTEMS.items():
            train_score = np.mean(
                np.vstack([bank["reference_scores"][member] for member in members]),
                axis=0,
            )
            validation_score = np.mean(
                np.vstack(
                    [bank["outputs"]["validation"][member] for member in members]
                ),
                axis=0,
            )
            training_metrics = score_quality(
                y[train_pool], train_score, train_pool, args.event_radius
            )
            validation_metrics = score_quality(
                y[validation], validation_score, validation, args.event_radius
            )
            systems[system] = {
                "training": training_metrics,
                "validation": validation_metrics,
                "combined_25train_75validation": float(
                    0.25 * training_metrics["quality_higher_is_better"]
                    + 0.75 * validation_metrics["quality_higher_is_better"]
                ),
            }
        qualities = np.asarray(
            [row["combined_25train_75validation"] for row in systems.values()]
        )
        weak = np.asarray(
            [
                row["validation"]["weak_peak_retention_skill"]
                for row in systems.values()
            ]
        )
        evaluations[variant] = {
            "feature_count": len(features),
            "aggregate_quality_higher_is_better": float(
                0.50 * np.median(qualities)
                + 0.35 * np.quantile(qualities, 0.25)
                + 0.15 * np.min(qualities)
            ),
            "system_quality_min": float(np.min(qualities)),
            "weak_peak_retention_min": float(np.min(weak)),
            "systems": systems,
        }
    baseline = evaluations["native_safe_baseline"]
    candidate = evaluations["smart_ablation_candidate"]
    reasons = []
    if (
        candidate["aggregate_quality_higher_is_better"]
        < baseline["aggregate_quality_higher_is_better"]
        - args.total_quality_tolerance
    ):
        reasons.append("real_model_quality_damage")
    if (
        candidate["system_quality_min"]
        < baseline["system_quality_min"] - args.system_floor_tolerance
    ):
        reasons.append("real_model_system_floor_damage")
    if (
        candidate["weak_peak_retention_min"]
        < baseline["weak_peak_retention_min"] - args.weak_peak_tolerance
    ):
        reasons.append("real_model_weak_peak_damage")
    passed = not reasons
    result = {
        "status": "PASS" if passed else "ROLLBACK",
        "reasons": reasons,
        "evaluations": evaluations,
        "selected_feature_count_after_guard": (
            len(selected_features) if passed else len(baseline_features)
        ),
    }
    write_json(
        PROJECT / f"03_feature_research/timing/{step_name}/real_model_guard.json",
        result,
    )
    return {
        **result,
        "selected_indices": selected_features if passed else baseline_features,
    }


def choose_history(
    step_name: str,
    X: np.ndarray,
    y: np.ndarray,
    dates: pd.Series,
    train_pool: np.ndarray,
    validation: np.ndarray,
    features: list[int],
    args,
    seed: int,
) -> dict:
    if args.precompacted_master:
        selected = {
            "config": {
                "precompacted": True,
                "selection_source": "compact_k_factor_selection.json",
            },
            "training_rows": int(len(train_pool)),
            "training_events": int(y[train_pool].sum()),
            "selection_basis": "pre_feature_fast_k_factor_search",
        }
        write_json(
            PROJECT / f"03_feature_research/timing/{step_name}/history_search.json",
            {
                "policy": "precompacted_master",
                "trials": [],
                "selected": selected,
            },
        )
        return selected
    trials = []
    for config_id, config in enumerate(history_candidates(args)):
        sample = sample_timing(train_pool, dates, y, **config)
        if int(y[sample].sum()) < 5:
            continue
        evaluation = evaluate_feature_set(
            X,
            y,
            sample,
            train_pool,
            validation,
            features,
            args.event_radius,
            seed,
        )
        trials.append(
            {
                "config": config,
                "training_rows": len(sample),
                "training_events": int(y[sample].sum()),
                "aggregate_quality_higher_is_better": evaluation[
                    "aggregate_quality_higher_is_better"
                ],
                "system_quality_min": evaluation["system_quality_min"],
                "weak_peak_retention_min": evaluation["weak_peak_retention_min"],
            }
        )
    if not trials:
        raise RuntimeError("No history candidate has enough events")
    if args.outer_history_policy == "master_fingerprint":
        selection_path = (
            Path(args.master_selection_json).expanduser().resolve()
            if args.master_selection_json
            else PROJECT / "02_master_search/master_search_selection.json"
        )
        selected = json.loads(selection_path.read_text())["selected"]
        required_config = {
            "start_year": int(selected["history_start_year"]),
            "event_radius": int(selected["history_event_radius"]),
            "between_records_per_event": int(
                selected["history_between_records"]
            ),
        }
        matching = [
            row for row in trials if row["config"] == required_config
        ]
        if len(matching) != 1:
            raise RuntimeError(
                "The selected master history fingerprint is absent from the "
                "configured downstream history grid"
            )
        best = {
            **matching[0],
            "selection_basis": "audited_master_fingerprint",
            "master_selection_json": str(selection_path),
        }
    else:
        best = {
            **max(
                trials,
                key=lambda row: (
                    row["aggregate_quality_higher_is_better"],
                    row["weak_peak_retention_min"],
                ),
            ),
            "selection_basis": "inner_validation_search",
        }
    write_json(
        PROJECT / f"03_feature_research/timing/{step_name}/history_search.json",
        {
            "policy": args.outer_history_policy,
            "trials": trials,
            "selected": best,
        },
    )
    return best


def prediction_frame(
    frame: pd.DataFrame,
    indices: np.ndarray,
    raw_score: np.ndarray,
    score: np.ndarray,
    consensus: np.ndarray,
) -> pd.DataFrame:
    columns = [
        "date",
        "slot_end_inclusive",
        "timing_target",
        "event_mag",
        "event_latitude",
        "event_longitude",
        "event_id",
    ]
    columns.extend(
        column
        for column in (
            "observed_max_mag",
            "observed_event_time",
            "observed_event_latitude",
            "observed_event_longitude",
            "observed_event_id",
        )
        if column in frame
    )
    columns.extend(
        column
        for column in (
            "hard_negative_control",
            "hard_negative_scope",
            "hard_negative_event_ids",
            "hard_negative_places",
        )
        if column in frame
    )
    result = frame.loc[indices, columns].reset_index(drop=True)
    result = result.rename(columns={"timing_target": "actual"})
    result["raw_score"] = raw_score
    result["score_percentile_not_probability"] = score
    result["tie_aware_consensus"] = consensus
    result["is_internal_local_peak"] = internal_local_maxima(score).astype(int)
    result["score_rank_percentile"] = tied_percentile(score)
    return result


def rolling_median(values: np.ndarray, width: int = 3) -> np.ndarray:
    """Centered edge-safe median used only to identify short worst-system anomalies."""
    values = np.asarray(values, float)
    radius = width // 2
    return np.asarray(
        [
            np.median(values[max(0, index - radius) : min(len(values), index + radius + 1)])
            for index in range(len(values))
        ],
        float,
    )


def worst_pattern_penalty(
    system_scores: dict[str, np.ndarray],
    worst_systems: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Return the worst-system centre and a bounded peak/depression anomaly penalty."""
    worst_centre = np.mean(
        np.vstack([system_scores[name] for name in worst_systems]),
        axis=0,
    )
    anomaly = np.abs(worst_centre - rolling_median(worst_centre, width=3))
    scale = float(np.quantile(anomaly, 0.90)) if len(anomaly) else 0.0
    if scale <= 1e-12:
        penalty = np.zeros_like(anomaly)
    else:
        penalty = np.clip(anomaly / scale, 0.0, 1.0)
    return worst_centre, penalty


def apply_worst_pattern_penalty(
    normal_score: np.ndarray,
    penalty: np.ndarray,
    strength: float,
) -> np.ndarray:
    """Soft-only suppression; no slot is erased and the output remains in [0, 1]."""
    normal_score = np.asarray(normal_score, float)
    penalty = np.asarray(penalty, float)
    attenuation = strength * penalty * (0.35 + 0.65 * normal_score)
    return np.clip(normal_score - attenuation, 0.0, 1.0)


def penalty_metric_row(
    mode: str,
    strength: float,
    step_metrics: list[dict],
) -> dict:
    profiles = [metric["event_profiles"][0] for metric in step_metrics]
    return {
        "mode": mode,
        "strength": float(strength),
        "mean_quality_higher_is_better": float(
            np.mean([metric["quality_higher_is_better"] for metric in step_metrics])
        ),
        "mean_weak_peak_retention": float(
            np.mean([profile["weak_peak_retention_skill"] for profile in profiles])
        ),
        "mean_delayed_false_peak_control": float(
            np.mean([profile["delayed_false_peak_control"] for profile in profiles])
        ),
        "mean_false_peak_control": float(
            np.mean([profile["false_peak_control"] for profile in profiles])
        ),
        "strict_local_peak_count": int(
            np.sum([profile["strict_local_peak"] for profile in profiles])
        ),
        "false_peak_count": int(
            np.sum([profile["false_peak_count"] for profile in profiles])
        ),
    }


def penalty_objective(row: dict) -> float:
    """All components are skills where larger is better."""
    return float(
        0.45 * row["mean_quality_higher_is_better"]
        + 0.25 * row["mean_weak_peak_retention"]
        + 0.20 * row["mean_delayed_false_peak_control"]
        + 0.10 * row["mean_false_peak_control"]
    )


def choose_subtractive_mode(
    steps: list[dict],
    frame: pd.DataFrame,
    y: np.ndarray,
    weights: dict[str, float],
    args,
) -> dict:
    """Select a penalty strength only when outer validation demonstrates real gain."""
    mean_system_quality = {
        system: float(
            np.mean(
                [
                    step["systems"][system]["summary"][
                        "origin_quality_25train_75validation"
                    ]
                    for step in steps
                ]
            )
        )
        for system in SYSTEMS
    }
    ranked = sorted(mean_system_quality, key=mean_system_quality.get, reverse=True)
    worst_systems = ranked[-args.worst_system_count :]
    normal_scores = []
    penalties = []
    system_scores_by_step = []
    for step in steps:
        normal = np.zeros(len(step["validation"]), float)
        for base in BASES:
            system = (
                base
                if base in SYSTEMS
                else (
                    base if base.startswith("deep_") else f"{base}_only"
                )
            )
            normal += weights[base] * step["systems"][system]["score"]
        system_scores = {
            system: step["systems"][system]["score"] for system in SYSTEMS
        }
        _, penalty = worst_pattern_penalty(system_scores, worst_systems)
        normal_scores.append(normal)
        penalties.append(penalty)
        system_scores_by_step.append(system_scores)

    candidates = [("normal", 0.0)]
    candidates.extend(
        ("subtractive", float(value))
        for value in args.penalty_strengths.split(",")
    )
    trials = []
    trial_scores = {}
    for mode, strength in candidates:
        step_metrics = []
        scores = []
        for step, normal, penalty in zip(steps, normal_scores, penalties):
            score = (
                normal
                if mode == "normal"
                else apply_worst_pattern_penalty(normal, penalty, strength)
            )
            scores.append(score)
            step_metrics.append(
                score_quality(
                    y[step["validation"]],
                    score,
                    step["validation"],
                    args.event_radius,
                )
            )
        row = penalty_metric_row(mode, strength, step_metrics)
        row["objective_higher_is_better"] = penalty_objective(row)
        trials.append(row)
        trial_scores[(mode, strength)] = scores

    baseline = trials[0]
    eligible = []
    for row in trials[1:]:
        gain = (
            row["objective_higher_is_better"]
            - baseline["objective_higher_is_better"]
        )
        row["objective_gain_vs_normal"] = float(gain)
        row["passes_real_advantage_gate"] = bool(
            gain >= args.penalty_minimum_gain
            and row["strict_local_peak_count"] >= baseline["strict_local_peak_count"]
            and row["false_peak_count"] <= baseline["false_peak_count"]
            and row["mean_quality_higher_is_better"]
            >= baseline["mean_quality_higher_is_better"] - 0.005
            and row["mean_weak_peak_retention"]
            >= baseline["mean_weak_peak_retention"] - 0.025
            and row["mean_delayed_false_peak_control"]
            > baseline["mean_delayed_false_peak_control"]
        )
        if row["passes_real_advantage_gate"]:
            eligible.append(row)
    baseline["objective_gain_vs_normal"] = 0.0
    baseline["passes_real_advantage_gate"] = True
    selected = (
        max(eligible, key=lambda row: row["objective_higher_is_better"])
        if eligible
        else baseline
    )
    best_subtractive = max(
        trials[1:],
        key=lambda row: row["objective_higher_is_better"],
    )
    selected_key = (selected["mode"], float(selected["strength"]))
    audit = {
        "status": "SUBTRACTIVE_ACCEPTED" if eligible else "NORMAL_RETAINED",
        "selected_mode": selected["mode"],
        "selected_strength": float(selected["strength"]),
        "diagnostic_subtractive_strength": float(best_subtractive["strength"]),
        "diagnostic_subtractive_objective": float(
            best_subtractive["objective_higher_is_better"]
        ),
        "worst_system_count": args.worst_system_count,
        "worst_systems": worst_systems,
        "system_quality_ranking_best_to_worst": [
            {
                "rank": rank + 1,
                "system": system,
                "quality_higher_is_better": mean_system_quality[system],
            }
            for rank, system in enumerate(ranked)
        ],
        "gate": (
            "objective gain >= configured minimum; no lost strict local peak; "
            "no extra false peak; quality and weak retention within guards; "
            "delayed-false-peak control must strictly improve"
        ),
        "trials": trials,
    }
    write_json(PROJECT / "05_ensemble/timing/subtractive_gate.json", audit)
    pd.DataFrame(trials).to_csv(
        PROJECT / "05_ensemble/timing/subtractive_trials.csv",
        index=False,
    )
    return {
        **audit,
        "normal_scores": normal_scores,
        "penalties": penalties,
        "selected_scores": trial_scores[selected_key],
    }


def parse_isolation_metric_weights(args) -> dict[str, float]:
    return {
        key.strip(): float(number)
        for key, number in (
            item.split("=", 1)
            for item in args.isolation_metric_weights.split(",")
            if item.strip()
        )
    }


def peak_isolation_profile(
    score: np.ndarray,
    actual: np.ndarray,
    metric_weights: dict[str, float],
    credible_peak_min_prominence: float,
    false_peak_competitor_margin: float,
    target_event_index: int | None = None,
) -> dict:
    """Measure whether a designated event is isolated from non-event competitors.

    A validation neighbourhood may legitimately contain more than one positive
    interval.  Those additional known events must remain visible in the chart and
    must not be relabelled as false peaks.  ``target_event_index`` identifies the
    fold's chronological holdout inside the local score array; the other positive
    intervals are excluded only from the *false*-competitor background.
    """
    score = np.asarray(score, float)
    actual = np.asarray(actual, int)
    event_indices = np.flatnonzero(actual == 1)
    if target_event_index is None:
        if len(event_indices) != 1:
            raise ValueError(
                "A target_event_index is required when a validation fold "
                "contains multiple known events"
            )
        event_index = int(event_indices[0])
    else:
        event_index = int(target_event_index)
        if not 0 <= event_index < len(actual) or actual[event_index] != 1:
            raise ValueError(
                "The designated outer timing target must be a positive row "
                "inside its validation fold"
            )
    peaks = np.flatnonzero(internal_local_maxima(score))
    credible_peaks = np.asarray(
        [
            index
            for index in peaks
            if score[index] - max(score[index - 1], score[index + 1])
            >= credible_peak_min_prominence
        ],
        int,
    )
    known_event_neighbourhood = np.zeros(len(score), dtype=bool)
    for known_event_index in event_indices:
        known_event_neighbourhood[
            max(0, int(known_event_index) - 1) : min(
                len(score), int(known_event_index) + 2
            )
        ] = True
    false_peaks = credible_peaks[~known_event_neighbourhood[credible_peaks]]
    competing_false_peaks = false_peaks[
        score[false_peaks]
        >= score[event_index] - false_peak_competitor_margin
    ]
    background = score[~known_event_neighbourhood]
    if not len(background):
        background = np.delete(score, event_index)
    neighbours = score[
        np.asarray(
            [
                index
                for index in (event_index - 1, event_index + 1)
                if 0 <= index < len(score)
            ],
            int,
        )
    ]
    local_margin = float(score[event_index] - np.max(neighbours))
    global_margin = float(score[event_index] - np.max(background))
    event_rank = float(tied_percentile(score)[event_index])
    baseline = float(np.median(background))
    false_energy = float(
        np.sum(np.maximum(score[false_peaks] - baseline, 0.0))
    )
    skills = {
        "exact_peak": float(event_index in peaks),
        "event_rank": event_rank,
        "local_prominence": float(np.clip(0.5 + 2.0 * local_margin, 0.0, 1.0)),
        "global_competitor": float(np.clip(0.5 + 2.0 * global_margin, 0.0, 1.0)),
        "false_peak_control": float(1.0 / (1.0 + len(false_peaks))),
        "false_peak_energy": float(1.0 / (1.0 + 4.0 * false_energy)),
        "background_control": float(
            np.clip(1.0 - np.mean(background), 0.0, 1.0)
        ),
    }
    objective = float(
        sum(metric_weights[name] * skills[name] for name in metric_weights)
    )
    return {
        **skills,
        "objective_higher_is_better": objective,
        "event_index": event_index,
        "event_score": float(score[event_index]),
        "argmax_offset_slots": int(
            np.argmax(
                np.where(
                    known_event_neighbourhood
                    & (np.arange(len(score)) != event_index),
                    -np.inf,
                    score,
                )
            )
            - event_index
        ),
        "known_event_count_in_fold": int(len(event_indices)),
        "local_margin": local_margin,
        "global_margin": global_margin,
        "false_peak_count": int(len(false_peaks)),
        "false_peak_indices": false_peaks.astype(int).tolist(),
        "competing_false_peak_count": int(len(competing_false_peaks)),
        "competing_false_peak_indices": (
            competing_false_peaks.astype(int).tolist()
        ),
        "false_peak_competitor_margin": float(
            false_peak_competitor_margin
        ),
    }


def apply_symmetric_alias_penalty(
    score: np.ndarray,
    lag: int,
    strength: float,
    symmetry_tolerance: int,
    suppression_radius: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Softly attenuate outer peaks in a repeated, symmetric three-peak pattern."""
    score = np.asarray(score, float)
    result = score.copy()
    penalty = np.zeros(len(score), float)
    if lag <= 0 or strength <= 0:
        return result, penalty
    peaks = np.flatnonzero(internal_local_maxima(score))
    for left_index in range(len(peaks)):
        for centre_index in range(left_index + 1, len(peaks)):
            for right_index in range(centre_index + 1, len(peaks)):
                left = int(peaks[left_index])
                centre = int(peaks[centre_index])
                right = int(peaks[right_index])
                left_gap = centre - left
                right_gap = right - centre
                if (
                    abs(left_gap - lag) > symmetry_tolerance
                    or abs(right_gap - lag) > symmetry_tolerance
                    or abs(left_gap - right_gap) > symmetry_tolerance
                ):
                    continue
                for outer in (left, right):
                    start = max(0, outer - suppression_radius)
                    end = min(len(score), outer + suppression_radius + 1)
                    penalty[start:end] = np.maximum(
                        penalty[start:end],
                        strength,
                    )
    background = float(np.median(score))
    result = (1.0 - penalty) * result + penalty * background
    return np.clip(result, 0.0, 1.0), penalty


def normalized_positive_weights(
    values: np.ndarray,
    floor: float,
) -> np.ndarray:
    values = np.maximum(np.asarray(values, float), 0.0)
    if not np.any(values):
        values = np.ones_like(values)
    values /= values.sum()
    return floor + (1.0 - floor * len(values)) * values


def isolation_profile_passes_peak_gate(profile: dict, args) -> bool:
    """Preselect ensembles whose held-out event is globally dominant."""
    return bool(
        profile["exact_peak"]
        and abs(profile["argmax_offset_slots"])
        <= args.gate_maximum_argmax_offset_slots
        and profile["event_rank"]
        >= args.gate_minimum_event_percentile_skill
        and profile["competing_false_peak_count"]
        <= args.gate_maximum_competing_false_peak_count
    )


def fold_target_local_index(step: dict, frame: pd.DataFrame) -> int:
    """Locate the configured holdout row inside a persisted fold window."""
    validation = np.asarray(step["validation"], int)
    target_date = str(step["event"]["date"])[:10]
    local_dates = (
        frame.iloc[validation]["date"].astype(str).str.slice(0, 10).to_numpy()
    )
    matches = np.flatnonzero(local_dates == target_date)
    if len(matches) != 1:
        raise ValueError(
            f"Fold {step['step']} must contain its designated target date "
            f"exactly once; found {len(matches)} matches for {target_date}"
        )
    target = int(matches[0])
    if int(frame.iloc[validation[target]]["timing_target"]) != 1:
        raise ValueError(
            f"Fold {step['step']} target date {target_date} is not a positive bin"
        )
    return target


def designated_event_profile(
    metrics: dict,
    target_global_index: int,
) -> dict:
    """Return the profile for one explicit target when other events coexist."""
    matches = [
        profile
        for profile in metrics["event_profiles"]
        if int(profile["event_global_index"]) == int(target_global_index)
    ]
    if len(matches) != 1:
        raise ValueError(
            "The designated validation event profile could not be identified "
            f"uniquely for global row {target_global_index}"
        )
    return matches[0]


def choose_peak_isolation_ensemble(
    steps: list[dict],
    frame: pd.DataFrame,
    y: np.ndarray,
    args,
) -> dict:
    """Search all-system weights, then gate a learned symmetric-alias penalty."""
    systems = list(SYSTEMS)
    metric_weights = parse_isolation_metric_weights(args)
    floor = float(args.ensemble_weight_floor)
    system_training_quality = np.asarray(
        [
            np.mean(
                [
                    step["systems"][system]["summary"]["training_metrics"][
                        "quality_higher_is_better"
                    ]
                    for step in steps
                ]
            )
            for system in systems
        ],
        float,
    )
    system_origin_quality = np.asarray(
        [
            np.mean(
                [
                    step["systems"][system]["summary"][
                        "origin_quality_25train_75validation"
                    ]
                    for step in steps
                ]
            )
            for system in systems
        ],
        float,
    )
    fold_system_scores = [
        np.vstack([step["systems"][system]["score"] for system in systems])
        for step in steps
    ]
    fold_actual = [y[step["validation"]] for step in steps]
    fold_target_indices = [fold_target_local_index(step, frame) for step in steps]

    candidates: list[tuple[str, np.ndarray]] = []
    candidates.append(
        (
            "origin_quality",
            normalized_positive_weights(system_origin_quality, floor),
        )
    )
    for index, system in enumerate(systems):
        emphasis = np.zeros(len(systems), float)
        emphasis[index] = 1.0
        candidates.append(
            (
                f"emphasize_{system}",
                normalized_positive_weights(emphasis, floor),
            )
        )
    for temperature in (0.5, 1.0, 2.0, 4.0):
        values = np.power(
            np.maximum(system_origin_quality, 1e-6),
            temperature,
        )
        candidates.append(
            (
                f"origin_temperature_{temperature:g}",
                normalized_positive_weights(values, floor),
            )
        )
    rng = np.random.default_rng(SEED + 88000)
    remaining = max(0, args.peak_search_trials - len(candidates))
    for trial in range(remaining):
        concentration = 0.25 + 2.75 * (trial % 7) / 6.0
        weights = normalized_positive_weights(
            rng.dirichlet(np.full(len(systems), concentration)),
            floor,
        )
        candidates.append((f"dirichlet_{trial + 1:05d}", weights))

    weight_trials = []
    weight_payload = []
    for name, weights in candidates:
        profiles = []
        for scores, actual, target_event_index in zip(
            fold_system_scores,
            fold_actual,
            fold_target_indices,
        ):
            profiles.append(
                peak_isolation_profile(
                    weights @ scores,
                    actual,
                    metric_weights,
                    args.credible_peak_min_prominence,
                    args.gate_false_peak_competitor_margin,
                    target_event_index=target_event_index,
                )
            )
        validation_mean = float(
            np.mean([profile["objective_higher_is_better"] for profile in profiles])
        )
        validation_minimum = float(
            np.min([profile["objective_higher_is_better"] for profile in profiles])
        )
        robust_validation = 0.80 * validation_mean + 0.20 * validation_minimum
        training_quality = float(weights @ system_training_quality)
        total = float(
            args.training_objective_weight * training_quality
            + args.validation_objective_weight * robust_validation
        )
        row = {
            "candidate": name,
            "training_quality_higher_is_better": training_quality,
            "validation_mean_higher_is_better": validation_mean,
            "validation_minimum_higher_is_better": validation_minimum,
            "robust_validation_higher_is_better": robust_validation,
            "total_objective_higher_is_better": total,
            "exact_peak_count": int(sum(profile["exact_peak"] for profile in profiles)),
            "globally_dominant_peak_count": int(
                sum(
                    isolation_profile_passes_peak_gate(profile, args)
                    for profile in profiles
                )
            ),
            "minimum_event_rank": float(
                min(profile["event_rank"] for profile in profiles)
            ),
            "maximum_absolute_argmax_offset_slots": int(
                max(
                    abs(profile["argmax_offset_slots"])
                    for profile in profiles
                )
            ),
            "false_peak_count": int(
                sum(profile["false_peak_count"] for profile in profiles)
            ),
            "competing_false_peak_count": int(
                sum(
                    profile["competing_false_peak_count"]
                    for profile in profiles
                )
            ),
        }
        row.update(
            {
                f"weight_{system}": float(weights[index])
                for index, system in enumerate(systems)
            }
        )
        weight_trials.append(row)
        weight_payload.append((total, name, weights, profiles))

    weight_payload.sort(key=lambda item: item[0], reverse=True)
    eligible_weights = [
        item
        for item in weight_payload
        if all(
            isolation_profile_passes_peak_gate(profile, args)
            for profile in item[3]
        )
    ]
    baseline = eligible_weights[0] if eligible_weights else weight_payload[0]
    alias_candidates = [(0, 0.0)]
    alias_candidates.extend(
        (lag, float(strength))
        for lag in range(2, args.alias_max_lag + 1)
        for strength in args.alias_strengths.split(",")
    )
    alias_trials = []
    alias_payload = []
    alias_weight_payload = []
    seen_weight_names = set()
    for item in [*eligible_weights[:64], *weight_payload[:64]]:
        if item[1] in seen_weight_names:
            continue
        seen_weight_names.add(item[1])
        alias_weight_payload.append(item)
    for _, weight_name, weights, _ in alias_weight_payload:
        normal_scores = [weights @ values for values in fold_system_scores]
        for lag, strength in alias_candidates:
            profiles = []
            selected_scores = []
            penalties = []
            for normal, actual, target_event_index in zip(
                normal_scores,
                fold_actual,
                fold_target_indices,
            ):
                selected, penalty = apply_symmetric_alias_penalty(
                    normal,
                    lag,
                    strength,
                    args.alias_symmetry_tolerance,
                    args.alias_suppression_radius,
                )
                selected_scores.append(selected)
                penalties.append(penalty)
                profiles.append(
                    peak_isolation_profile(
                        selected,
                        actual,
                        metric_weights,
                        args.credible_peak_min_prominence,
                        args.gate_false_peak_competitor_margin,
                        target_event_index=target_event_index,
                    )
                )
            validation_mean = float(
                np.mean(
                    [profile["objective_higher_is_better"] for profile in profiles]
                )
            )
            validation_minimum = float(
                np.min(
                    [profile["objective_higher_is_better"] for profile in profiles]
                )
            )
            robust_validation = 0.80 * validation_mean + 0.20 * validation_minimum
            training_quality = float(weights @ system_training_quality)
            total = float(
                args.training_objective_weight * training_quality
                + args.validation_objective_weight * robust_validation
            )
            row = {
                "weight_candidate": weight_name,
                "alias_lag_slots": int(lag),
                "alias_strength": float(strength),
                "training_quality_higher_is_better": training_quality,
                "validation_mean_higher_is_better": validation_mean,
                "validation_minimum_higher_is_better": validation_minimum,
                "total_objective_higher_is_better": total,
                "exact_peak_count": int(
                    sum(profile["exact_peak"] for profile in profiles)
                ),
                "globally_dominant_peak_count": int(
                    sum(
                        isolation_profile_passes_peak_gate(profile, args)
                        for profile in profiles
                    )
                ),
                "false_peak_count": int(
                    sum(profile["false_peak_count"] for profile in profiles)
                ),
                "competing_false_peak_count": int(
                    sum(
                        profile["competing_false_peak_count"]
                        for profile in profiles
                    )
                ),
                "effective_candidate": bool(
                    any(np.any(penalty > 0) for penalty in penalties)
                ),
            }
            alias_trials.append(row)
            alias_payload.append(
                (
                    total,
                    weight_name,
                    weights,
                    lag,
                    strength,
                    normal_scores,
                    selected_scores,
                    penalties,
                    profiles,
                )
            )

    dominant_no_alias = [
        item
        for item in alias_payload
        if item[3] == 0
        and all(
            isolation_profile_passes_peak_gate(profile, args)
            for profile in item[8]
        )
    ]
    no_alias_has_dominant_peaks = bool(dominant_no_alias)
    no_alias = max(
        dominant_no_alias
        or [item for item in alias_payload if item[3] == 0],
        key=lambda item: item[0],
    )
    accepted = []
    for item in alias_payload:
        (
            total,
            _,
            _,
            lag,
            strength,
            _,
            _,
            _,
            profiles,
        ) = item
        if lag == 0:
            continue
        accepted_by_gate = bool(
            total - no_alias[0] >= args.minimum_isolation_gain
            and all(
                isolation_profile_passes_peak_gate(profile, args)
                for profile in profiles
            )
            and sum(profile["false_peak_count"] for profile in profiles)
            < sum(profile["false_peak_count"] for profile in no_alias[8])
            and all(
                profile["objective_higher_is_better"]
                >= baseline_profile["objective_higher_is_better"] - 0.01
                for profile, baseline_profile in zip(profiles, no_alias[8])
            )
        )
        if accepted_by_gate:
            accepted.append(item)
    selected = max(accepted, key=lambda item: item[0]) if accepted else no_alias
    effective_alias_candidates = int(
        sum(
            bool(row["effective_candidate"])
            for row in alias_trials
            if int(row["alias_lag_slots"]) > 0
        )
    )
    (
        selected_total,
        selected_weight_name,
        selected_weights,
        selected_lag,
        selected_strength,
        selected_normal_scores,
        selected_scores,
        selected_penalties,
        selected_profiles,
    ) = selected
    pd.DataFrame(weight_trials).sort_values(
        "total_objective_higher_is_better",
        ascending=False,
    ).to_csv(PROJECT / "05_ensemble/timing/peak_weight_trials.csv", index=False)
    pd.DataFrame(alias_trials).sort_values(
        "total_objective_higher_is_better",
        ascending=False,
    ).to_csv(PROJECT / "05_ensemble/timing/alias_gate_trials.csv", index=False)
    audit = {
        "status": (
            "ALIAS_PENALTY_ACCEPTED"
            if accepted
            else (
                "NO_APPLICABLE_ALIAS_PATTERN"
                if effective_alias_candidates == 0
                else (
                    "NO_ALIAS_PENALTY"
                    if no_alias_has_dominant_peaks
                    else "NO_ALIAS_PENALTY_NO_EXACT_WEEKLY_BASELINE"
                )
            )
        ),
        "metric_direction": "all component metrics are normalized; higher is better",
        "metric_weights": metric_weights,
        "objective_weights": {
            "training": args.training_objective_weight,
            "validation": args.validation_objective_weight,
            "validation_robust_mean": 0.80,
            "validation_worst_fold": 0.20,
        },
        "search": {
            "weight_candidates": len(weight_trials),
            "dominant_weight_candidates": len(eligible_weights),
            "alias_candidates": len(alias_trials),
            "effective_alias_candidates": effective_alias_candidates,
            "positive_weight_floor": floor,
            "minimum_isolation_gain": args.minimum_isolation_gain,
            "credible_peak_min_prominence": args.credible_peak_min_prominence,
            "false_peak_competitor_margin": (
                args.gate_false_peak_competitor_margin
            ),
        },
        "baseline_without_alias": {
            "total_objective_higher_is_better": float(no_alias[0]),
            "weight_candidate": no_alias[1],
            "both_validation_peaks_exact": bool(
                all(profile["exact_peak"] for profile in no_alias[8])
            ),
            "both_validation_peaks_globally_dominant": (
                no_alias_has_dominant_peaks
            ),
            "profiles": no_alias[8],
        },
        "selected": {
            "total_objective_higher_is_better": float(selected_total),
            "weight_candidate": selected_weight_name,
            "alias_lag_slots": int(selected_lag),
            "alias_strength": float(selected_strength),
            "profiles": selected_profiles,
            "system_weights": {
                system: float(selected_weights[index])
                for index, system in enumerate(systems)
            },
        },
        "gate": (
            "accept alias suppression only when total gain reaches the configured "
            "minimum, every outer event remains an exact local peak, total false "
            "peaks decrease, and no fold loses more than 0.01 isolation skill"
        ),
    }
    write_json(PROJECT / "05_ensemble/timing/peak_isolation_gate.json", audit)
    return {
        **audit,
        "systems": systems,
        "weights": selected_weights,
        "normal_scores": selected_normal_scores,
        "selected_scores": selected_scores,
        "penalties": selected_penalties,
    }


def fit_outer_step(
    step_name: str,
    event_row: pd.Series,
    X: np.ndarray,
    y: np.ndarray,
    frame: pd.DataFrame,
    names: list[str],
    outer_train_pool: np.ndarray,
    validation: np.ndarray,
    features: list[int],
    history: dict,
    args,
    seed: int,
    forecast: np.ndarray | None = None,
    model_output_root: Path | None = None,
    screening_anchor_seed: int | None = None,
) -> dict:
    models_root = (
        Path(model_output_root)
        if model_output_root is not None
        else PROJECT / "04_models/timing"
    )
    config = history["config"]
    sample = (
        np.asarray(outer_train_pool, int)
        if config.get("precompacted")
        else sample_timing(outer_train_pool, frame["date"], y, **config)
    )
    effective_sample = replay_hard_negative_rows(
        frame,
        sample,
        args.hard_negative_replay,
    )
    predict_sets = {"validation": validation}
    if forecast is not None and len(forecast):
        predict_sets["forecast"] = np.asarray(forecast, int)
    bank = fit_real_bank(
        X,
        y,
        effective_sample,
        outer_train_pool,
        predict_sets,
        features,
        seed,
        args.epochs_scale,
        args.calibration_mode,
        screening_anchor_seed,
    )
    export_lcs_rules(
        bank["models"]["lcs"],
        [names[index] for index in features],
        models_root / step_name / "lcs_rules.json",
        {
            "step": step_name,
            "training_cutoff": frame.iloc[outer_train_pool[-1]]["date"],
            "feature_count": len(features),
        },
    )
    systems = {}
    for system, members in SYSTEMS.items():
        train_score = np.mean(
            np.vstack([bank["reference_scores"][member] for member in members]),
            axis=0,
        )
        raw_validation = np.mean(
            np.vstack([bank["raw_outputs"]["validation"][member] for member in members]),
            axis=0,
        )
        validation_score = np.mean(
            np.vstack([bank["outputs"]["validation"][member] for member in members]),
            axis=0,
        )
        consensus = tie_aware_consensus(bank["outputs"]["validation"], members)
        training_metrics = score_quality(
            y[outer_train_pool], train_score, outer_train_pool, args.event_radius
        )
        validation_metrics = score_quality(
            y[validation], validation_score, validation, args.event_radius
        )
        origin = float(
            0.25 * training_metrics["quality_higher_is_better"]
            + 0.75 * validation_metrics["quality_higher_is_better"]
        )
        system_dir = models_root / step_name / system
        system_dir.mkdir(parents=True, exist_ok=True)
        predictions = prediction_frame(
            frame,
            validation,
            raw_validation,
            validation_score,
            consensus,
        )
        predictions.to_csv(system_dir / "validation_predictions.csv", index=False)
        forecast_predictions = None
        if "forecast" in bank["outputs"]:
            raw_forecast = np.mean(
                np.vstack(
                    [
                        bank["raw_outputs"]["forecast"][member]
                        for member in members
                    ]
                ),
                axis=0,
            )
            forecast_score = np.mean(
                np.vstack(
                    [
                        bank["outputs"]["forecast"][member]
                        for member in members
                    ]
                ),
                axis=0,
            )
            forecast_consensus = tie_aware_consensus(
                bank["outputs"]["forecast"], members
            )
            forecast_predictions = prediction_frame(
                frame,
                np.asarray(forecast, int),
                raw_forecast,
                forecast_score,
                forecast_consensus,
            )
            forecast_predictions.to_csv(
                system_dir / "forecast_predictions.csv", index=False
            )
        summary = {
            "system": system,
            "members": list(members),
            "feature_count": len(features),
            "history": config,
            "training_rows": len(sample),
            "effective_training_rows": len(effective_sample),
            "hard_negative_replay": args.hard_negative_replay,
            "training_events": int(y[sample].sum()),
            "training_metrics": training_metrics,
            "validation_metrics": validation_metrics,
            "origin_quality_25train_75validation": origin,
            "member_runtimes": {
                member: bank["runtimes"][member] for member in members
            },
            "system_runtime_seconds_sum_members": float(
                sum(
                    bank["runtimes"][member]["fit_and_inference_seconds"]
                    for member in members
                )
            ),
            "preprocessing": bank["preprocessing"],
            "score_semantics": (
                "empirical percentile against the chronological pre-validation "
                "reference pool; not a calibrated event probability"
            ),
        }
        write_json(system_dir / "summary.json", summary)
        systems[system] = {
            "summary": summary,
            "score": validation_score,
            "raw_score": raw_validation,
            "consensus": consensus,
            "predictions": predictions,
            "forecast_predictions": forecast_predictions,
        }
    return {
        "step": step_name,
        "event": {
            "date": event_row["date"],
            "slot_end": event_row["slot_end_inclusive"],
            "magnitude": float(event_row["event_mag"]),
            "event_id": event_row["event_id"],
            "latitude": float(event_row["event_latitude"]),
            "longitude": float(event_row["event_longitude"]),
        },
        "features": features,
        "history": history,
        "training_rows": len(sample),
        "training_events": int(y[sample].sum()),
        "validation": validation,
        "systems": systems,
    }


def load_completed_outer_step(
    step_name: str,
    validation: np.ndarray,
    names: list[str],
) -> dict:
    """Restore one fully persisted fold for an ensemble-stage resume."""
    step_dir = PROJECT / f"04_models/timing/{step_name}"
    step_path = step_dir / "step_summary.json"
    if not step_path.is_file():
        raise FileNotFoundError(step_path)
    step_summary = json.loads(step_path.read_text())
    selected_names = step_summary["selected_features"]
    missing = [feature for feature in selected_names if feature not in names]
    if missing:
        raise RuntimeError(
            f"Persisted fold features are absent from the master: {missing[:3]}"
        )
    systems = {}
    for system in SYSTEMS:
        system_dir = step_dir / system
        summary = json.loads((system_dir / "summary.json").read_text())
        predictions = pd.read_csv(system_dir / "validation_predictions.csv")
        forecast_path = system_dir / "forecast_predictions.csv"
        forecast_predictions = (
            pd.read_csv(forecast_path) if forecast_path.is_file() else None
        )
        if len(predictions) != len(validation):
            raise RuntimeError(
                f"Persisted validation length mismatch for {step_name}/{system}"
            )
        systems[system] = {
            "summary": summary,
            "score": predictions[
                "score_percentile_not_probability"
            ].to_numpy(float),
            "raw_score": predictions["raw_score"].to_numpy(float),
            "consensus": predictions["tie_aware_consensus"].to_numpy(float),
            "predictions": predictions,
            "forecast_predictions": forecast_predictions,
        }
    return {
        "step": step_name,
        "event": step_summary["event"],
        "features": [names.index(feature) for feature in selected_names],
        "history": step_summary["history"],
        "training_rows": int(
            next(iter(systems.values()))["summary"]["training_rows"]
        ),
        "training_events": int(
            next(iter(systems.values()))["summary"]["training_events"]
        ),
        "validation": validation,
        "systems": systems,
        "ablation": step_summary.get("ablation", {}),
        "guard": step_summary.get("real_model_guard", {}),
    }


def run(args) -> dict:
    for directory in (
        PROJECT / "00_config",
        PROJECT / "02_audit",
        PROJECT / "03_feature_research/timing",
        PROJECT / "04_models/timing",
        PROJECT / "05_ensemble/timing",
        PROJECT / "logs",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for obsolete in (
        PROJECT / "05_ensemble/timing/subtractive_gate.json",
        PROJECT / "05_ensemble/timing/subtractive_trials.csv",
    ):
        if obsolete.exists():
            obsolete.unlink()
    frame = pd.read_csv(PROJECT / "01_inputs/timing_master.csv", low_memory=False)
    try:
        grid_dates = [
            date.fromisoformat(str(value)[:10]) for value in frame["date"]
        ]
        grid_ends = [
            date.fromisoformat(str(value)[:10])
            for value in frame["slot_end_inclusive"]
        ]
    except ValueError as error:
        raise RuntimeError("Timing master contains an invalid ISO date") from error
    expected_ends = [
        value + timedelta(days=args.interval_days - 1) for value in grid_dates
    ]
    grid_anchor = date.fromisoformat(args.forecast_grid_start)
    aligned_to_grid = [
        (value - grid_anchor).days % args.interval_days == 0
        for value in grid_dates
    ]
    forecast_grid_dates = [
        value
        for value, is_forecast in zip(
            grid_dates, frame["is_forecast"].to_numpy(int)
        )
        if is_forecast == 1
    ]
    forecast_differences = np.diff(
        np.asarray(
            [(value - grid_anchor).days for value in forecast_grid_dates],
            dtype=int,
        )
    )
    if (
        grid_dates != sorted(grid_dates)
        or len(grid_dates) != len(set(grid_dates))
        or not all(aligned_to_grid)
        or (
            len(forecast_differences)
            and not np.all(forecast_differences == args.interval_days)
        )
        or grid_ends != expected_ends
    ):
        raise RuntimeError(
            f"Timing master rows are not aligned to the exact {args.interval_days}-day "
            "source grid or the forecast section is not contiguous"
        )
    names = [column for column in frame if column not in TIMING_META]
    X = frame[names].to_numpy(float)
    y = frame["timing_target"].to_numpy(int)
    safe_payload = json.loads(
        (PROJECT / "01_inputs/v4_native_safe_features.json").read_text()
    )
    safe_names = safe_payload["features"]
    missing = [name for name in safe_names if name not in names]
    if missing:
        raise RuntimeError(f"Native-safe features missing from master: {missing[:3]}")
    initial_features = [names.index(name) for name in safe_names]
    manifest(args, frame, names, initial_features)
    dates = frame["date"].astype(str).str.slice(0, 10)
    frozen_grid_start = args.forecast_grid_start
    historical = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
        & dates.lt(frozen_grid_start).to_numpy()
    )
    forecast_mask = (
        dates.ge(frozen_grid_start).to_numpy()
        & dates.le(args.forecast_end).to_numpy()
    )
    forecast = np.flatnonzero(forecast_mask)
    outer_events, outer_selection = select_outer_events(frame, historical, y, args)
    steps = []
    for step_id, event in enumerate(outer_events):
        event_row = frame.iloc[event]
        step_name = f"{step_id + 1:02d}_{event_row['date']}_{event_row['event_id']}"
        validation = isolated_indices(np.asarray([event]), args.event_radius, len(frame))
        validation = validation[np.isin(validation, historical)]
        if args.resume_completed_folds:
            try:
                restored = load_completed_outer_step(
                    step_name,
                    validation,
                    names,
                )
            except (FileNotFoundError, KeyError, RuntimeError, ValueError) as error:
                print(
                    f"[{step_name}] completed-fold resume unavailable: {error}",
                    flush=True,
                )
            else:
                print(
                    f"[{step_name}] restored persisted fold; skipping ablation/refit",
                    flush=True,
                )
                steps.append(restored)
                continue
        outer_train_pool = historical[historical < validation.min()]
        inner_train_pool, inner_validation, inner_events = inner_split(
            y,
            outer_train_pool,
            args.inner_validation_events,
            args.event_radius,
        )
        print(f"[{step_name}] intelligent proxy ablation", flush=True)
        ablation = smart_ablation(
            step_name,
            X,
            y,
            frame["date"],
            names,
            initial_features,
            inner_train_pool,
            inner_validation,
            args,
            SEED + step_id * 20000,
        )
        print(f"[{step_name}] real LCS/KAN/PyTorch guard", flush=True)
        guard = real_guard(
            step_name,
            X,
            y,
            frame,
            names,
            ablation["training_sample"],
            inner_train_pool,
            inner_validation,
            initial_features,
            ablation["selected_indices"],
            args,
            SEED + step_id * 20000 + 8000,
        )
        features = guard["selected_indices"]
        print(f"[{step_name}] history search after features", flush=True)
        history = choose_history(
            step_name,
            X,
            y,
            frame["date"],
            inner_train_pool,
            inner_validation,
            features,
            args,
            SEED + step_id * 20000 + 12000,
        )
        print(f"[{step_name}] outer validation fit", flush=True)
        outer = fit_outer_step(
            step_name,
            event_row,
            X,
            y,
            frame,
            names,
            outer_train_pool,
            validation,
            features,
            history,
            args,
            SEED + step_id * 20000 + 16000,
            forecast=forecast,
            screening_anchor_seed=(
                args.screening_anchor_seed_base + step_id * 101
                if args.screening_anchor_seed_base
                else None
            ),
        )
        step_summary = {
            "step": step_name,
            "event": outer["event"],
            "outer_training_cutoff": frame.iloc[outer_train_pool[-1]]["date"],
            "outer_training_events_available": int(y[outer_train_pool].sum()),
            "inner_validation_events": [
                {
                    "date": frame.iloc[index]["date"],
                    "magnitude": float(frame.iloc[index]["event_mag"]),
                    "event_id": frame.iloc[index]["event_id"],
                }
                for index in inner_events
            ],
            "ablation": {
                key: value
                for key, value in ablation.items()
                if key not in {"selected_indices", "training_sample"}
            },
            "real_model_guard": {
                key: value for key, value in guard.items() if key != "selected_indices"
            },
            "selected_feature_count": len(features),
            "selected_features": [names[index] for index in features],
            "history": history,
        }
        write_json(
            PROJECT / f"04_models/timing/{step_name}/step_summary.json",
            step_summary,
        )
        outer["ablation"] = ablation
        outer["guard"] = guard
        steps.append(outer)

    # Conservative cross-fold distillation: keep a feature if either fold retained it.
    # A feature important to one chronological regime is never removed by averaging.
    feature_union = sorted(set().union(*(set(step["features"]) for step in steps)))
    history_counter = Counter(
        json.dumps(step["history"]["config"], sort_keys=True) for step in steps
    )
    final_history = json.loads(history_counter.most_common(1)[0][0])

    base_quality = {}
    for base in BASES:
        system = (
            base
            if base in SYSTEMS
            else (
                base if base.startswith("deep_") else f"{base}_only"
            )
        )
        base_quality[base] = float(
            np.mean(
                [
                    step["systems"][system]["summary"][
                        "origin_quality_25train_75validation"
                    ]
                    for step in steps
                ]
            )
        )
    weights = positive_weights(base_quality)
    weight_frame = pd.DataFrame(
        [
            {
                "base": base,
                "mean_origin_quality_higher_is_better": base_quality[base],
                "positive_weight": weights[base],
            }
            for base in BASES
        ]
    )
    weight_frame.to_csv(PROJECT / "05_ensemble/timing/base_weights.csv", index=False)

    isolation_selection = choose_peak_isolation_ensemble(
        steps,
        frame,
        y,
        args,
    )
    system_weight_frame = pd.DataFrame(
        [
            {
                "system": system,
                "positive_weight": float(isolation_selection["weights"][index]),
            }
            for index, system in enumerate(isolation_selection["systems"])
        ]
    )
    system_weight_frame.to_csv(
        PROJECT / "05_ensemble/timing/peak_isolation_system_weights.csv",
        index=False,
    )
    validation_rows = []
    gate_rows = []
    for step_index, step in enumerate(steps):
        normal_score = isolation_selection["normal_scores"][step_index]
        score = isolation_selection["selected_scores"][step_index]
        pattern_penalty = isolation_selection["penalties"][step_index]
        consensus = np.zeros(len(step["validation"]), float)
        for system, system_weight in zip(
            isolation_selection["systems"],
            isolation_selection["weights"],
        ):
            consensus += system_weight * step["systems"][system]["consensus"]
        raw = np.zeros(len(score), float)
        predictions = prediction_frame(
            frame,
            step["validation"],
            np.full(len(raw), np.nan),
            score,
            consensus,
        )
        predictions.insert(0, "step", step["step"])
        predictions["normal_score_percentile"] = normal_score
        predictions["symmetric_alias_penalty"] = pattern_penalty
        predictions["selected_timing_mode"] = isolation_selection["status"]
        validation_rows.append(predictions)
        metrics = score_quality(
            y[step["validation"]], score, step["validation"], args.event_radius
        )
        target_local_index = fold_target_local_index(step, frame)
        target_global_index = int(step["validation"][target_local_index])
        profile = designated_event_profile(metrics, target_global_index)
        isolation_profile = isolation_selection["selected"]["profiles"][
            step_index
        ]
        sole_weak_peak = bool(
            not profile["strict_local_peak"]
            and args.gate_allow_sole_weak_peaks
            and profile["weak_peak_retention_skill"]
            >= args.gate_minimum_weak_peak_retention_skill
            and abs(profile["argmax_offset_slots"])
            <= args.gate_maximum_argmax_offset_slots
            and isolation_profile["competing_false_peak_count"]
            <= args.gate_maximum_competing_false_peak_count
        )
        local_shape_ok = bool(
            profile["strict_local_peak"] or sole_weak_peak
        )
        dominant_peak = bool(
            local_shape_ok
            and abs(profile["argmax_offset_slots"])
            <= args.gate_maximum_argmax_offset_slots
            and profile["event_percentile_skill"]
            >= args.gate_minimum_event_percentile_skill
            and profile["weak_peak_retention_skill"]
            >= args.gate_minimum_weak_peak_retention_skill
            and profile["delayed_false_peak_control"]
            >= args.gate_minimum_delayed_false_peak_control
            and isolation_profile["competing_false_peak_count"]
            <= args.gate_maximum_competing_false_peak_count
            and metrics["quality_higher_is_better"]
            >= args.gate_minimum_fold_quality
        )
        gate_rows.append(
            {
                "step": step["step"],
                "event_date": step["event"]["date"],
                "magnitude": step["event"]["magnitude"],
                "event_id": step["event"]["event_id"],
                "latitude": step["event"]["latitude"],
                "longitude": step["event"]["longitude"],
                "strict_local_peak": profile["strict_local_peak"],
                "sole_weak_peak_accepted": sole_weak_peak,
                "qualified_peak": dominant_peak,
                "dominant_peak": dominant_peak,
                "argmax_offset_slots": profile["argmax_offset_slots"],
                "event_percentile_skill": profile[
                    "event_percentile_skill"
                ],
                "weak_peak_retention_skill": profile[
                    "weak_peak_retention_skill"
                ],
                "delayed_false_peak_control": profile[
                    "delayed_false_peak_control"
                ],
                "quality_higher_is_better": metrics[
                    "quality_higher_is_better"
                ],
                "isolation_objective_higher_is_better": isolation_selection[
                    "selected"
                ]["profiles"][step_index]["objective_higher_is_better"],
                "false_peak_count": isolation_profile["false_peak_count"],
                "competing_false_peak_count": isolation_profile[
                    "competing_false_peak_count"
                ],
                "selected_timing_mode": isolation_selection["status"],
            }
        )
    validation_frame = pd.concat(validation_rows, ignore_index=True)
    validation_frame.to_csv(
        PROJECT / "05_ensemble/timing/validation_predictions.csv", index=False
    )
    gate_frame = pd.DataFrame(gate_rows)
    gate_frame.to_csv(PROJECT / "05_ensemble/timing/validation_gate.csv", index=False)

    final_sample = (
        np.asarray(historical, int)
        if args.precompacted_master
        else sample_timing(historical, frame["date"], y, **final_history)
    )
    final_effective_sample = replay_hard_negative_rows(
        frame,
        final_sample,
        args.hard_negative_replay,
    )
    print("[final] fit conservative union and out-of-sample forecast", flush=True)
    final_bank = fit_real_bank(
        X,
        y,
        final_effective_sample,
        historical,
        {"forecast": forecast},
        feature_union,
        SEED + 70000,
        args.epochs_scale,
        args.calibration_mode,
        (
            args.screening_anchor_seed_base + len(steps) * 101
            if args.screening_anchor_seed_base
            else None
        ),
    )
    export_lcs_rules(
        final_bank["models"]["lcs"],
        [names[index] for index in feature_union],
        PROJECT / "04_models/timing/final/lcs_rules.json",
        {
            "step": "final",
            "training_cutoff": frame.iloc[historical[-1]]["date"],
            "feature_policy": "conservative union of both chronological folds",
        },
    )
    final_system_scores = {
        system: np.mean(
            np.vstack(
                [
                    final_bank["outputs"]["forecast"][member]
                    for member in members
                ]
            ),
            axis=0,
        )
        for system, members in SYSTEMS.items()
    }
    final_score = np.zeros(len(forecast), float)
    final_consensus = np.zeros(len(forecast), float)
    for system, system_weight in zip(
        isolation_selection["systems"],
        isolation_selection["weights"],
    ):
        final_score += system_weight * final_system_scores[system]
        members = SYSTEMS[system]
        system_consensus = np.mean(
            np.vstack(
                [
                    (
                        tied_percentile(
                            final_bank["outputs"]["forecast"][member]
                        )
                        >= 0.75
                    ).astype(float)
                    for member in members
                ]
            ),
            axis=0,
        )
        final_consensus += system_weight * system_consensus
    selected_forecast_score, final_penalty = apply_symmetric_alias_penalty(
        final_score,
        isolation_selection["selected"]["alias_lag_slots"],
        isolation_selection["selected"]["alias_strength"],
        args.alias_symmetry_tolerance,
        args.alias_suppression_radius,
    )
    per_system_forecast = pd.DataFrame(
        {
            "date": frame.iloc[forecast]["date"].astype(str).to_numpy(),
            **{
                system: final_system_scores[system]
                for system in isolation_selection["systems"]
            },
        }
    )
    per_system_forecast.to_csv(
        PROJECT / "05_ensemble/timing/system_forecast_predictions.csv",
        index=False,
    )
    forecast_frame = prediction_frame(
        frame,
        forecast,
        np.full(len(forecast), np.nan),
        selected_forecast_score,
        final_consensus,
    )
    forecast_frame["normal_score_percentile"] = final_score
    forecast_frame["symmetric_alias_penalty"] = final_penalty
    forecast_frame["selected_timing_mode"] = isolation_selection["status"]
    forecast_frame["visible_window_starts"] = args.forecast_start
    forecast_frame.to_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv", index=False
    )
    final_features = {
        "policy": (
            "conservative union: retained if either chronological fold considered "
            "the feature useful; not selected by a target feature count"
        ),
        "feature_count": len(feature_union),
        "indices": feature_union,
        "features": [names[index] for index in feature_union],
        "fold_feature_counts": {
            step["step"]: len(step["features"]) for step in steps
        },
    }
    write_json(
        PROJECT / "03_feature_research/timing/final_conservative_features.json",
        final_features,
    )
    gate_pass = bool(
        np.all(gate_frame["dominant_peak"].to_numpy(bool))
        and float(
            gate_frame["quality_higher_is_better"].mean()
        )
        >= args.gate_minimum_mean_quality
    )
    summary = {
        "status": "COMPLETE",
        "validation_gate": "PASS" if gate_pass else "FAIL_REPORTED_NOT_TUNED",
        "outer_validation_selection": outer_selection,
        "outer_validation_events": [step["event"] for step in steps],
        "gate_rule": (
            "each outer event must be a strict local maximum or an allowed "
            "sole weak peak and must satisfy: |argmax offset|<="
            f"{args.gate_maximum_argmax_offset_slots}, event percentile>="
            f"{args.gate_minimum_event_percentile_skill:.2f}, retention>="
            f"{args.gate_minimum_weak_peak_retention_skill:.2f}, delayed "
            "false-peak control>="
            f"{args.gate_minimum_delayed_false_peak_control:.2f}, competing "
            "false peaks<="
            f"{args.gate_maximum_competing_false_peak_count} using margin "
            f"{args.gate_false_peak_competitor_margin:.3f}, fold quality>="
            f"{args.gate_minimum_fold_quality:.2f}, and mean fold quality>="
            f"{args.gate_minimum_mean_quality:.2f}"
        ),
        "base_quality": base_quality,
        "base_weights": weights,
        "peak_isolation": {
            key: value
            for key, value in isolation_selection.items()
            if key
            not in {
                "normal_scores",
                "penalties",
                "selected_scores",
                "weights",
                "systems",
            }
        },
        "final_features": final_features,
        "final_history": final_history,
        "training_rows": len(final_sample),
        "effective_training_rows": len(final_effective_sample),
        "hard_negative_replay": args.hard_negative_replay,
        "calibration_mode": args.calibration_mode,
        "preprocessing": final_bank["preprocessing"],
        "training_events": int(y[final_sample].sum()),
        "forecast_rows": len(forecast),
        "forecast": {
            "visible_start": args.forecast_start,
            "exact_grid_start": args.forecast_grid_start,
            "training_cutoff": frame.iloc[historical[-1]]["date"],
        },
        "location": "not run yet: timing stage completes before V14 localization",
    }
    write_json(PROJECT / "05_ensemble/timing/final_summary.json", summary)
    return summary


def main() -> None:
    args = parser().parse_args()
    os.environ["DLVSWAVE_MODEL_PROFILE"] = args.model_profile
    os.environ["DLVSWAVE_QUANTILE_BINS"] = str(args.quantile_bins)
    os.environ["DLVSWAVE_FINAL_ATTEMPT_TIMEOUT_SECONDS"] = str(
        args.final_attempt_time_limit_seconds
    )
    if args.model_overrides_json:
        os.environ["DLVSWAVE_MODEL_OVERRIDES_JSON"] = str(
            Path(args.model_overrides_json).expanduser().resolve()
        )
    else:
        os.environ.pop("DLVSWAVE_MODEL_OVERRIDES_JSON", None)
    validate_args(args)
    start = time.time()
    if args.training_mode == "randomized":
        from randomized_control import run_randomized_timing

        summary = run_randomized_timing(args)
        summary["elapsed_seconds"] = time.time() - start
        write_json(
            PROJECT / "07_randomized_control/timing/completion.json",
            summary,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
        return
    if args.training_mode == "one_shot":
        from one_shot_timing import run_one_shot_timing

        summary = run_one_shot_timing(args)
        summary["elapsed_seconds"] = time.time() - start
        write_json(
            PROJECT / "05_ensemble/timing/one_shot/completion.json",
            summary,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
        return
    if args.training_mode == "historical_record_shuffle":
        from historical_record_shuffle import run_historical_record_shuffle

        summary = run_historical_record_shuffle(args)
        summary["elapsed_seconds"] = time.time() - start
        write_json(
            PROJECT / "07_historical_record_shuffle/timing/completion.json",
            summary,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
        return
    summary = run(args)
    summary["elapsed_seconds"] = time.time() - start
    write_json(PROJECT / "00_config/completion.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

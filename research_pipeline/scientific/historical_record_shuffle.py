#!/usr/bin/env python3
"""Incremental order-sensitivity control using intact historical records.

Only the order of complete training rows changes. Feature vectors and targets
remain paired, chronological outer cutoffs and validation holdouts are
unchanged, and primary ensemble weights are reused without control-specific
validation tuning.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

import run_pipeline as pipeline
from common_v14 import (
    PROJECT,
    TIMING_META,
    isolated_indices,
    sample_timing,
    score_quality,
    write_json,
)

SYSTEMS = pipeline.SYSTEMS


def _aggregate(values: list[np.ndarray], method: str) -> np.ndarray:
    matrix = np.vstack(values)
    if method == "mean":
        return np.mean(matrix, axis=0)
    if method == "median":
        return np.median(matrix, axis=0)
    raise ValueError(f"Unknown aggregation: {method}")


def _system_weights() -> tuple[list[str], np.ndarray]:
    weights = pd.read_csv(
        PROJECT / "05_ensemble/timing/peak_isolation_system_weights.csv"
    )
    systems = weights["system"].astype(str).tolist()
    missing = sorted(set(systems).difference(SYSTEMS))
    if missing:
        raise RuntimeError(f"Unknown persisted systems: {missing}")
    values = weights["positive_weight"].to_numpy(float)
    if np.any(values < 0) or not np.isclose(values.sum(), 1.0):
        raise RuntimeError("Persisted primary system weights are invalid")
    return systems, values


def _fuse_bank(
    bank: dict,
    evaluation: str,
    systems: list[str],
    weights: np.ndarray,
) -> np.ndarray:
    fused = None
    for system, weight in zip(systems, weights):
        members = SYSTEMS[system]
        score = np.mean(
            np.vstack(
                [bank["outputs"][evaluation][member] for member in members]
            ),
            axis=0,
        )
        fused = weight * score if fused is None else fused + weight * score
    return np.asarray(fused, float)


def _step_directories() -> list[Path]:
    return sorted(
        path.parent
        for path in (PROJECT / "04_models/timing").glob(
            "[0-9][0-9]_*/step_summary.json"
        )
    )


def _permuted_sample(
    sample: np.ndarray,
    seed: int,
) -> np.ndarray:
    shuffled = np.random.default_rng(seed).permutation(sample)
    if not np.array_equal(np.sort(shuffled), np.sort(sample)):
        raise RuntimeError("Record permutation changed training membership")
    return shuffled


def run_historical_record_shuffle(args) -> dict:
    control_started = time.perf_counter()
    destination = PROJECT / "07_historical_record_shuffle/timing"
    destination.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(PROJECT / "01_inputs/timing_master.csv", low_memory=False)
    names = [column for column in frame if column not in TIMING_META]
    name_to_index = {name: index for index, name in enumerate(names)}
    X = frame[names].to_numpy(float)
    actual = frame["timing_target"].to_numpy(int)
    dates = frame["date"].astype(str).str.slice(0, 10)
    primary = json.loads(
        (PROJECT / "05_ensemble/timing/final_summary.json").read_text()
    )
    systems, system_weights = _system_weights()
    selected_isolation = primary["peak_isolation"]["selected"]
    historical = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
        & dates.lt(args.forecast_grid_start).to_numpy()
    )
    forecast = np.flatnonzero(
        dates.ge(args.forecast_grid_start).to_numpy()
        & dates.le(args.forecast_end).to_numpy()
    )

    step_dirs = _step_directories()
    if len(step_dirs) != len(primary["outer_validation_events"]):
        raise RuntimeError("Persisted incremental fold count is inconsistent")
    repeat_validation_parts: list[list[np.ndarray]] = [
        [] for _ in range(args.historical_record_repeats)
    ]
    repeat_forecast_scores: list[np.ndarray] = []
    repeat_rows: list[dict] = []
    repeat_runtime_seconds = np.zeros(
        args.historical_record_repeats, dtype=float
    )
    repeat_validation_fit_seconds = np.zeros(
        args.historical_record_repeats, dtype=float
    )
    repeat_forecast_fit_seconds = np.zeros(
        args.historical_record_repeats, dtype=float
    )
    fold_audit: list[dict] = []
    validation_indices_all: list[np.ndarray] = []

    for fold_index, step_dir in enumerate(step_dirs):
        step = json.loads((step_dir / "step_summary.json").read_text())
        features = [name_to_index[name] for name in step["selected_features"]]
        event_slot = str(step["event"]["date"])
        event_matches = np.flatnonzero(
            frame["date"].astype(str).eq(event_slot).to_numpy()
            & frame["timing_target"].eq(1).to_numpy()
        )
        if len(event_matches) != 1:
            raise RuntimeError(f"Expected one event at {event_slot}")
        validation = isolated_indices(
            event_matches, args.event_radius, len(frame)
        )
        validation = validation[np.isin(validation, historical)]
        validation_indices_all.append(validation)
        outer_train_pool = historical[historical < validation.min()]
        sample = (
            np.asarray(outer_train_pool, int)
            if args.precompacted_master
            else sample_timing(
                outer_train_pool,
                frame["date"],
                actual,
                **step["history"]["config"],
            )
        )
        effective_sample = pipeline.replay_hard_negative_rows(
            frame,
            sample,
            args.hard_negative_replay,
        )
        fold_repeat_scores: list[np.ndarray] = []
        for repeat in range(args.historical_record_repeats):
            fit_started = time.perf_counter()
            print(
                f"[historical-record shuffle] validation fold "
                f"{fold_index + 1}/{len(step_dirs)}, repeat "
                f"{repeat + 1}/{args.historical_record_repeats}",
                flush=True,
            )
            permutation_seed = (
                args.historical_record_seed + repeat * 1009 + fold_index * 97
            )
            shuffled_sample = _permuted_sample(
                effective_sample,
                permutation_seed,
            )
            bank = pipeline.fit_real_bank(
                X,
                actual,
                shuffled_sample,
                outer_train_pool,
                {"validation": validation},
                features,
                args.historical_record_model_seed_base
                + fold_index * 20000
                + 16000,
                args.epochs_scale,
                args.calibration_mode,
                screening_anchor_seed=(
                    args.screening_anchor_seed_base + fold_index * 101
                    if args.screening_anchor_seed_base
                    else None
                ),
            )
            score = _fuse_bank(
                bank, "validation", systems, system_weights
            )
            score, _ = pipeline.apply_symmetric_alias_penalty(
                score,
                int(selected_isolation["alias_lag_slots"]),
                float(selected_isolation["alias_strength"]),
                args.alias_symmetry_tolerance,
                args.alias_suppression_radius,
            )
            fold_repeat_scores.append(score)
            elapsed = time.perf_counter() - fit_started
            repeat_runtime_seconds[repeat] += elapsed
            repeat_validation_fit_seconds[repeat] += elapsed
            print(
                f"[historical-record shuffle] completed validation fold "
                f"{fold_index + 1}, repeat {repeat + 1} in "
                f"{elapsed:.2f}s",
                flush=True,
            )
            repeat_validation_parts[repeat].append(score)
        aggregated = _aggregate(
            fold_repeat_scores, args.historical_record_aggregation
        )
        fold_metrics = score_quality(
            actual[validation], aggregated, validation, args.event_radius
        )
        fold_audit.append(
            {
                "step": step["step"],
                "event_slot": event_slot,
                "training_cutoff": frame.iloc[outer_train_pool[-1]]["date"],
                "training_rows": len(sample),
                "training_events": int(actual[sample].sum()),
                "feature_count": len(features),
                "history": step["history"]["config"],
                "feature_target_pair_integrity": True,
                "validation_metrics": fold_metrics,
            }
        )

    validation_indices = np.concatenate(validation_indices_all)
    repeat_validation_scores = [
        np.concatenate(parts) for parts in repeat_validation_parts
    ]
    for repeat, scores in enumerate(repeat_validation_scores):
        metrics = score_quality(
            actual[validation_indices],
            scores,
            validation_indices,
            args.event_radius,
        )
        repeat_rows.append(
            {
                "repeat": repeat + 1,
                "permutation_seed": args.historical_record_seed + repeat * 1009,
                "quality_higher_is_better": metrics[
                    "quality_higher_is_better"
                ],
                "strict_local_peak_rate": metrics["strict_local_peak_rate"],
                "weak_peak_retention_skill": metrics[
                    "weak_peak_retention_skill"
                ],
                "delayed_false_peak_control": metrics[
                    "delayed_false_peak_control"
                ],
            }
        )

    final_features = [
        name_to_index[name] for name in primary["final_features"]["features"]
    ]
    final_sample = (
        np.asarray(historical, int)
        if args.precompacted_master
        else sample_timing(
            historical,
            frame["date"],
            actual,
            **primary["final_history"],
        )
    )
    final_effective_sample = pipeline.replay_hard_negative_rows(
        frame,
        final_sample,
        args.hard_negative_replay,
    )
    for repeat in range(args.historical_record_repeats):
        fit_started = time.perf_counter()
        print(
            f"[historical-record shuffle] forecast repeat "
            f"{repeat + 1}/{args.historical_record_repeats}",
            flush=True,
        )
        permutation_seed = args.historical_record_seed + repeat * 1009 + 7919
        shuffled_sample = _permuted_sample(
            final_effective_sample,
            permutation_seed,
        )
        bank = pipeline.fit_real_bank(
            X,
            actual,
            shuffled_sample,
            historical,
            {"forecast": forecast},
            final_features,
            args.historical_record_model_seed_base + 70000,
            args.epochs_scale,
            args.calibration_mode,
            screening_anchor_seed=(
                args.screening_anchor_seed_base
                + len(primary["outer_validation_events"]) * 101
                if args.screening_anchor_seed_base
                else None
            ),
        )
        score = _fuse_bank(bank, "forecast", systems, system_weights)
        score, _ = pipeline.apply_symmetric_alias_penalty(
            score,
            int(selected_isolation["alias_lag_slots"]),
            float(selected_isolation["alias_strength"]),
            args.alias_symmetry_tolerance,
            args.alias_suppression_radius,
        )
        repeat_forecast_scores.append(score)
        elapsed = time.perf_counter() - fit_started
        repeat_runtime_seconds[repeat] += elapsed
        repeat_forecast_fit_seconds[repeat] += elapsed
        print(
            f"[historical-record shuffle] completed forecast repeat "
            f"{repeat + 1} in {elapsed:.2f}s",
            flush=True,
        )

    for repeat, row in enumerate(repeat_rows):
        row["validation_fit_seconds"] = float(
            repeat_validation_fit_seconds[repeat]
        )
        row["forecast_fit_seconds"] = float(
            repeat_forecast_fit_seconds[repeat]
        )
        row["total_fit_seconds"] = float(repeat_runtime_seconds[repeat])

    validation_matrix = np.vstack(repeat_validation_scores)
    forecast_matrix = np.vstack(repeat_forecast_scores)
    aggregate_validation = _aggregate(
        repeat_validation_scores, args.historical_record_aggregation
    )
    aggregate_forecast = _aggregate(
        repeat_forecast_scores, args.historical_record_aggregation
    )
    validation_metrics = score_quality(
        actual[validation_indices],
        aggregate_validation,
        validation_indices,
        args.event_radius,
    )

    validation_output = frame.iloc[validation_indices][
        [
            "date",
            "slot_end_inclusive",
            "timing_target",
            "event_mag",
            "event_latitude",
            "event_longitude",
            "event_id",
        ]
    ].reset_index(drop=True)
    validation_output = validation_output.rename(
        columns={"timing_target": "actual"}
    )
    validation_output["historical_record_shuffle_score"] = aggregate_validation
    validation_output["shuffle_score_std"] = validation_matrix.std(axis=0)
    validation_output["fold"] = np.concatenate(
        [
            np.repeat(f"holdout_{index + 1}", len(indices))
            for index, indices in enumerate(validation_indices_all)
        ]
    )
    validation_output.to_csv(destination / "validation.csv", index=False)

    forecast_output = frame.iloc[forecast][
        ["date", "slot_end_inclusive"]
    ].reset_index(drop=True)
    forecast_output["historical_record_shuffle_score"] = aggregate_forecast
    forecast_output["shuffle_score_std"] = forecast_matrix.std(axis=0)
    forecast_output["shuffle_score_min"] = forecast_matrix.min(axis=0)
    forecast_output["shuffle_score_max"] = forecast_matrix.max(axis=0)
    forecast_output.to_csv(destination / "forecast.csv", index=False)
    pd.DataFrame(repeat_rows).to_csv(
        destination / "repeat_metrics.csv", index=False
    )

    summary = {
        "status": "COMPLETE",
        "purpose": "training-order sensitivity control",
        "domain": "timing",
        "training_mode": "historical_record_shuffle",
        "incremental": True,
        "feature_target_pairs_preserved": True,
        "training_membership_preserved": True,
        "chronological_training_order_preserved": False,
        "outer_cutoffs_preserved": True,
        "validation_targets_untouched": True,
        "reverse_order_test_executed": False,
        "permutation_seed": int(args.historical_record_seed),
        "repeats": int(args.historical_record_repeats),
        "aggregation": args.historical_record_aggregation,
        "fixed_model_seed_base": int(
            args.historical_record_model_seed_base
        ),
        "primary_system_weights_reused": {
            system: float(weight)
            for system, weight in zip(systems, system_weights)
        },
        "folds": fold_audit,
        "validation_metrics": validation_metrics,
        "repeat_metrics": repeat_rows,
        "forecast_rows": len(forecast),
        "forecast_training_rows": len(final_sample),
        "forecast_training_events": int(actual[final_sample].sum()),
        "runtime": {
            "wall_seconds": float(time.perf_counter() - control_started),
            "repeat_total_fit_seconds": repeat_runtime_seconds.tolist(),
            "mean_repeat_total_fit_seconds": float(
                np.mean(repeat_runtime_seconds)
            ),
        },
        "does_not_affect_primary_forecast": True,
        "score_semantics": (
            "empirical percentiles; not calibrated event probabilities"
        ),
    }
    write_json(destination / "summary.json", summary)
    return summary

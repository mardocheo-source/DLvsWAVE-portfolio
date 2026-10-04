#!/usr/bin/env python3
"""Real-label one-shot timing validation plus one full-history forecast fit."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import run_pipeline as pipeline
from common_v14 import (
    PROJECT,
    TIMING_META,
    isolated_indices,
    positive_weights,
    score_quality,
    write_json,
)


def system_scores(base_scores: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        system: np.mean(
            np.vstack([base_scores[member] for member in members]), axis=0
        )
        for system, members in pipeline.SYSTEMS.items()
    }


def training_quality_weights(
    actual: np.ndarray,
    sample: np.ndarray,
    scores: dict[str, np.ndarray],
    event_radius: int,
) -> tuple[dict[str, float], dict[str, float]]:
    qualities = {
        system: float(
            score_quality(actual[sample], values, sample, event_radius)[
                "quality_higher_is_better"
            ]
        )
        for system, values in scores.items()
    }
    return positive_weights(qualities), qualities


def run_one_shot_timing(args) -> dict:
    destination = PROJECT / "05_ensemble/timing/one_shot"
    destination.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(PROJECT / "01_inputs/timing_master.csv", low_memory=False)
    names = [column for column in frame if column not in TIMING_META]
    X = frame[names].to_numpy(float)
    actual = frame["timing_target"].to_numpy(int)
    dates = frame["date"].astype(str).str.slice(0, 10)
    primary = json.loads(
        (PROJECT / "05_ensemble/timing/final_summary.json").read_text()
    )
    feature_payload = json.loads(
        (
            PROJECT
            / "03_feature_research/timing/final_conservative_features.json"
        ).read_text()
    )
    features = [names.index(name) for name in feature_payload["features"]]
    resolved = primary["outer_validation_selection"]["resolved_slots"]
    event_indices = np.asarray(
        [
            int(frame.index[frame["date"].astype(str).eq(slot)][0])
            for slot in resolved
        ],
        dtype=int,
    )
    validation_parts = [
        isolated_indices(np.asarray([event]), args.event_radius, len(frame))
        for event in event_indices
    ]
    validation = np.unique(np.concatenate(validation_parts))
    validation = validation[
        dates.iloc[validation].lt(args.forecast_grid_start).to_numpy()
    ]
    historical = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
    )
    validation_train = historical[historical < validation.min()]
    if int(actual[validation_train].sum()) < 5:
        raise RuntimeError("One-shot validation has fewer than five train events")
    forecast = np.flatnonzero(
        dates.ge(args.forecast_grid_start).to_numpy()
        & dates.le(args.forecast_end).to_numpy()
    )
    forecast_train = historical[dates.iloc[historical].lt(args.forecast_grid_start).to_numpy()]

    validation_bank = pipeline.fit_real_bank(
        X,
        actual,
        validation_train,
        validation_train,
        {"training": validation_train, "validation": validation},
        features,
        int(args.random_seed) + 19001,
        float(args.epochs_scale),
        args.calibration_mode,
        screening_anchor_seed=int(args.random_seed) + 19009,
    )
    validation_systems = {
        area: system_scores(base)
        for area, base in validation_bank["outputs"].items()
    }
    validation_weights, validation_training_qualities = training_quality_weights(
        actual,
        validation_train,
        validation_systems["training"],
        args.event_radius,
    )
    fused_validation = sum(
        validation_weights[system] * validation_systems["validation"][system]
        for system in pipeline.SYSTEMS
    )
    validation_metrics = score_quality(
        actual[validation], fused_validation, validation, args.event_radius
    )

    forecast_bank = pipeline.fit_real_bank(
        X,
        actual,
        forecast_train,
        forecast_train,
        {"training": forecast_train, "forecast": forecast},
        features,
        int(args.random_seed) + 19101,
        float(args.epochs_scale),
        args.calibration_mode,
        screening_anchor_seed=int(args.random_seed) + 19109,
    )
    forecast_systems = {
        area: system_scores(base)
        for area, base in forecast_bank["outputs"].items()
    }
    forecast_weights, forecast_training_qualities = training_quality_weights(
        actual,
        forecast_train,
        forecast_systems["training"],
        args.event_radius,
    )
    fused_forecast = sum(
        forecast_weights[system] * forecast_systems["forecast"][system]
        for system in pipeline.SYSTEMS
    )

    validation_output = frame.iloc[validation][
        [
            "date",
            "slot_end_inclusive",
            "timing_target",
            "event_mag",
            "event_id",
            "hard_negative_control",
            "hard_negative_places",
        ]
    ].reset_index(drop=True)
    validation_output = validation_output.rename(columns={"timing_target": "actual"})
    validation_output["one_shot_score_not_probability"] = fused_validation
    validation_output["fold"] = ""
    for fold_number, indices in enumerate(validation_parts, 1):
        mask = validation_output["date"].isin(
            frame.iloc[indices]["date"].astype(str)
        )
        validation_output.loc[mask, "fold"] = f"holdout_{fold_number}"
    validation_output.to_csv(destination / "validation.csv", index=False)

    forecast_output = frame.iloc[forecast][
        ["date", "slot_end_inclusive"]
    ].reset_index(drop=True)
    forecast_output["one_shot_score_not_probability"] = fused_forecast
    forecast_output.to_csv(destination / "forecast.csv", index=False)
    pd.DataFrame(
        {
            "system": list(validation_weights),
            "validation_fit_training_quality": [
                validation_training_qualities[name] for name in validation_weights
            ],
            "validation_fit_weight": list(validation_weights.values()),
            "forecast_fit_training_quality": [
                forecast_training_qualities[name] for name in validation_weights
            ],
            "forecast_fit_weight": [forecast_weights[name] for name in validation_weights],
        }
    ).to_csv(destination / "system_weights.csv", index=False)

    summary = {
        "status": "COMPLETE",
        "purpose": "real-label one-shot validation plus one full-history forecast refit",
        "training_mode": "one_shot",
        "incremental": False,
        "validation_selection_uses_holdout_scores": False,
        "system_weights_source": "training quality only",
        "validation_train_cutoff": str(frame.iloc[validation_train[-1]]["date"]),
        "validation_train_rows": int(len(validation_train)),
        "validation_train_events": int(actual[validation_train].sum()),
        "validation_events": int(len(event_indices)),
        "validation_metrics": validation_metrics,
        "forecast_train_cutoff": str(frame.iloc[forecast_train[-1]]["date"]),
        "forecast_train_rows": int(len(forecast_train)),
        "forecast_train_events": int(actual[forecast_train].sum()),
        "forecast_rows": int(len(forecast)),
        "feature_count": int(len(features)),
        "preprocessing": validation_bank["preprocessing"],
        "final_attempt_time_limit_seconds": float(
            args.final_attempt_time_limit_seconds
        ),
        "validation_member_runtimes": validation_bank["runtimes"],
        "forecast_member_runtimes": forecast_bank["runtimes"],
        "score_semantics": "relative experimental score; not a calibrated probability",
    }
    write_json(destination / "summary.json", summary)
    write_json(destination / "completion.json", summary)
    return summary

"""One-shot randomized-label controls for timing and localization.

These controls deliberately destroy the historical feature/target alignment
inside training while preserving event counts, feature rows, forecast rows and
the untouched chronological holdouts.  They are null experiments and never
replace the primary sequential forecast or contribute ensemble weight to it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from quantile_preprocessing import QuantileBinTransformer

import run_pipeline as pipeline

from common_v14 import (
    BASES,
    LOCATION_META,
    PROJECT,
    SYSTEMS,
    TIMING_META,
    empirical_percentile,
    fit_real_binary,
    isolated_indices,
    positive_weights,
    sample_timing,
    score_quality,
    tied_percentile,
    write_json,
)

TIMING_BASES = pipeline.BASES
TIMING_SYSTEMS = pipeline.SYSTEMS


def _timing_system_scores(
    base_scores: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    return {
        system: np.mean(
            np.vstack([base_scores[member] for member in members]),
            axis=0,
        )
        for system, members in TIMING_SYSTEMS.items()
    }


def _fit_binary_bases(
    X: np.ndarray,
    y: np.ndarray,
    sample: np.ndarray,
    evaluations: dict[str, np.ndarray],
    features: list[int],
    *,
    seed: int,
    epochs_scale: float,
    calibration_mode: str,
    screening_anchor_seed: int | None,
) -> dict[str, dict[str, np.ndarray]]:
    bank = pipeline.fit_real_bank(
        X,
        y,
        sample,
        sample,
        evaluations,
        features,
        seed,
        epochs_scale,
        calibration_mode,
        screening_anchor_seed=screening_anchor_seed,
    )
    return bank["outputs"]


def run_randomized_timing(args) -> dict:
    destination = PROJECT / "07_randomized_control/timing"
    destination.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(PROJECT / "01_inputs/timing_master.csv", low_memory=False)
    names = [column for column in frame if column not in TIMING_META]
    X = frame[names].to_numpy(float)
    actual = frame["timing_target"].to_numpy(int)
    dates = frame["date"].astype(str).str.slice(0, 10)
    feature_payload = json.loads(
        (
            PROJECT
            / "03_feature_research/timing/final_conservative_features.json"
        ).read_text()
    )
    features = [names.index(name) for name in feature_payload["features"]]
    primary = json.loads(
        (PROJECT / "05_ensemble/timing/final_summary.json").read_text()
    )
    resolved = primary["outer_validation_selection"]["resolved_slots"]
    event_indices = np.asarray(
        [
            int(frame.index[frame["date"].astype(str).eq(slot)][0])
            for slot in resolved
        ],
        int,
    )
    validation_parts = [
        isolated_indices(np.asarray([event]), args.event_radius, len(frame))
        for event in event_indices
    ]
    validation = np.unique(np.concatenate(validation_parts))
    validation = validation[
        dates.iloc[validation].lt(args.forecast_grid_start).to_numpy()
    ]
    train_pool = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
        & (np.arange(len(frame)) < validation.min())
    )
    original_positive_count = int(actual[train_pool].sum())
    rng = np.random.default_rng(args.random_seed)
    randomized = actual.copy()
    randomized[train_pool] = 0
    randomized_positive_indices = np.sort(
        rng.choice(train_pool, size=original_positive_count, replace=False)
    )
    randomized[randomized_positive_indices] = 1

    history = primary["final_history"]
    sample = (
        np.asarray(train_pool, int)
        if args.precompacted_master
        else sample_timing(
            train_pool,
            frame["date"],
            randomized,
            **history,
        )
    )
    forecast = np.flatnonzero(
        dates.ge(args.forecast_grid_start).to_numpy()
        & dates.le(args.forecast_end).to_numpy()
    )
    epochs_scale = min(float(args.epochs_scale), 0.40)
    outputs = _fit_binary_bases(
        X,
        randomized,
        sample,
        {
            "training": sample,
            "validation": validation,
            "forecast": forecast,
        },
        features,
        seed=args.random_seed,
        epochs_scale=epochs_scale,
        calibration_mode=args.calibration_mode,
        screening_anchor_seed=(
            int(args.screening_anchor_seed_base)
            if args.screening_anchor_seed_base
            else int(args.random_seed)
        ),
    )
    systems = {
        area: _timing_system_scores(base_scores)
        for area, base_scores in outputs.items()
    }
    rows = []
    qualities = {}
    for system in TIMING_SYSTEMS:
        training_metrics = score_quality(
            randomized[sample],
            systems["training"][system],
            sample,
            args.event_radius,
        )
        validation_metrics = score_quality(
            actual[validation],
            systems["validation"][system],
            validation,
            args.event_radius,
        )
        combined = (
            args.training_objective_weight
            * training_metrics["quality_higher_is_better"]
            + args.validation_objective_weight
            * validation_metrics["quality_higher_is_better"]
        )
        qualities[system] = float(combined)
        rows.append(
            {
                "system": system,
                "training_quality_higher_is_better": training_metrics[
                    "quality_higher_is_better"
                ],
                "validation_quality_higher_is_better": validation_metrics[
                    "quality_higher_is_better"
                ],
                "combined_quality_higher_is_better": combined,
            }
        )
    weights = positive_weights(qualities)
    ranking = pd.DataFrame(rows).sort_values(
        "combined_quality_higher_is_better", ascending=False
    )
    ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
    ranking["positive_weight"] = ranking["system"].map(weights)
    ranking.to_csv(destination / "system_ranking.csv", index=False)

    fused_validation = sum(
        weights[system] * systems["validation"][system]
        for system in TIMING_SYSTEMS
    )
    fused_forecast = sum(
        weights[system] * systems["forecast"][system]
        for system in TIMING_SYSTEMS
    )
    validation_output = frame.iloc[validation][
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
    validation_output["randomized_control_score"] = fused_validation
    validation_output["fold"] = ""
    for fold_number, (event, indices) in enumerate(
        zip(event_indices, validation_parts), 1
    ):
        mask = validation_output["date"].isin(
            frame.iloc[indices]["date"].astype(str)
        )
        validation_output.loc[mask, "fold"] = f"holdout_{fold_number}"
    validation_output.to_csv(destination / "validation.csv", index=False)

    forecast_output = frame.iloc[forecast][
        ["date", "slot_end_inclusive"]
    ].reset_index(drop=True)
    forecast_output["randomized_control_score"] = fused_forecast
    forecast_output.to_csv(destination / "forecast.csv", index=False)
    validation_metrics = score_quality(
        actual[validation],
        fused_validation,
        validation,
        args.event_radius,
    )
    summary = {
        "status": "COMPLETE",
        "purpose": "randomized-label scientific null control",
        "domain": "timing",
        "training_mode": "randomized",
        "validation_design": "one_shot",
        "incremental": False,
        "seed": int(args.random_seed),
        "label_scramble": (
            "training positive slots were relocated uniformly without replacement; "
            "event count was preserved and configured validation slots were untouched"
        ),
        "training_cutoff": frame.iloc[train_pool[-1]]["date"],
        "training_pool_rows": len(train_pool),
        "training_positive_count_preserved": original_positive_count,
        "training_sample_rows": len(sample),
        "training_sample_positive_rows": int(randomized[sample].sum()),
        "features": len(features),
        "history": history,
        "history_fingerprint_reused_without_change": True,
        "validation_slots": resolved,
        "validation_metrics": validation_metrics,
        "forecast_rows": len(forecast),
        "epochs_scale": epochs_scale,
        "does_not_affect_primary_forecast": True,
    }
    write_json(destination / "summary.json", summary)
    return summary


def _normalize_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, float)
    values = np.clip(values, 1e-9, None)
    return values / values.sum(axis=1, keepdims=True)


def _location_quality(
    actual: np.ndarray,
    probability: np.ndarray,
    zones: pd.DataFrame,
) -> dict:
    actual = np.asarray(actual, int)
    predicted = np.argmax(probability, axis=1) + 1
    top_two = np.argsort(-probability, axis=1)[:, :2] + 1
    exact = float(np.mean(predicted == actual))
    top_two_skill = float(
        np.mean([target in choices for target, choices in zip(actual, top_two)])
    )
    centres = zones.set_index("zone")[["center_latitude", "center_longitude"]]
    actual_xy = centres.loc[actual].to_numpy(float)
    predicted_xy = centres.loc[predicted].to_numpy(float)
    distance = np.sqrt(np.sum((actual_xy - predicted_xy) ** 2, axis=1))
    distance_skill = float(np.exp(-np.mean(distance) / 8.0))
    return {
        "exact_zone_accuracy": exact,
        "top_two_zone_accuracy": top_two_skill,
        "centroid_distance_skill": distance_skill,
        "quality_higher_is_better": float(
            0.50 * exact + 0.25 * top_two_skill + 0.25 * distance_skill
        ),
    }


def run_randomized_location(args) -> dict:
    destination = PROJECT / "07_randomized_control/location"
    destination.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(
        PROJECT / "01_inputs/location_master.csv", low_memory=False
    )
    events = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_event_catalog.csv"
    )
    zones = pd.read_csv(PROJECT / "05_ensemble/location_zones.csv")
    summary_primary = json.loads(
        (PROJECT / "05_ensemble/location_zone_summary.json").read_text()
    )
    names = [column for column in master if column not in LOCATION_META]
    features = [
        names.index(name)
        for name in summary_primary["selected_features"]["features"]
    ]
    historical = master.loc[master["is_forecast"].eq(0)].copy()
    master_dates = master["date"].astype(str).str.slice(0, 10)
    forecast_frame = master.loc[
        master["is_forecast"].eq(1)
        & master_dates.ge(args.forecast_grid_start)
        & master_dates.le(args.forecast_end)
    ].copy()
    event_zone = events.set_index("event_id")["zone"]
    historical["zone"] = historical["event_id"].map(event_zone)
    historical = historical.loc[historical["zone"].notna()].reset_index(drop=True)
    labels = historical["zone"].to_numpy(int)
    X_train_all = historical[names].to_numpy(float)
    X_forecast = forecast_frame[names].to_numpy(float)
    validation_count = int(args.validation_events)
    train_indices = np.arange(0, len(historical) - validation_count, dtype=int)
    validation_indices = np.arange(
        len(historical) - validation_count, len(historical), dtype=int
    )
    rng = np.random.default_rng(args.random_seed)
    shuffled_labels = labels.copy()
    shuffled_labels[train_indices] = rng.permutation(labels[train_indices])
    scaler = (
        QuantileBinTransformer(args.quantile_bins)
        if getattr(args, "quantile_bins", 0) >= 2
        else StandardScaler()
    )
    scaler.fit(X_train_all[train_indices][:, features])
    train_X = scaler.transform(X_train_all[train_indices][:, features])
    validation_X = scaler.transform(X_train_all[validation_indices][:, features])
    forecast_X = scaler.transform(X_forecast[:, features])
    zone_count = len(zones)
    epochs_scale = min(float(args.epochs_scale), 0.35)
    base_probabilities = {
        "training": {},
        "validation": {},
        "forecast": {},
    }
    for base_index, base in enumerate(BASES):
        matrices = {
            "training": np.zeros((len(train_indices), zone_count)),
            "validation": np.zeros((len(validation_indices), zone_count)),
            "forecast": np.zeros((len(forecast_frame), zone_count)),
        }
        for zone in range(1, zone_count + 1):
            target = (shuffled_labels[train_indices] == zone).astype(int)
            _, predict = fit_real_binary(
                base,
                train_X,
                target,
                args.random_seed + base_index * 1009 + zone * 37,
                epochs_scale=epochs_scale,
            )
            reference = predict(train_X)
            matrices["training"][:, zone - 1] = empirical_percentile(
                reference, reference
            )
            matrices["validation"][:, zone - 1] = empirical_percentile(
                reference, predict(validation_X)
            )
            matrices["forecast"][:, zone - 1] = empirical_percentile(
                reference, predict(forecast_X)
            )
        for area in matrices:
            base_probabilities[area][base] = _normalize_rows(matrices[area])

    system_probabilities = {
        area: {
            system: _normalize_rows(
                np.mean(
                    np.stack(
                        [base_probabilities[area][member] for member in members]
                    ),
                    axis=0,
                )
            )
            for system, members in SYSTEMS.items()
        }
        for area in base_probabilities
    }
    rows = []
    qualities = {}
    for system in SYSTEMS:
        training_metrics = _location_quality(
            shuffled_labels[train_indices],
            system_probabilities["training"][system],
            zones,
        )
        validation_metrics = _location_quality(
            labels[validation_indices],
            system_probabilities["validation"][system],
            zones,
        )
        combined = 0.25 * training_metrics["quality_higher_is_better"] + 0.75 * validation_metrics[
            "quality_higher_is_better"
        ]
        qualities[system] = float(combined)
        rows.append(
            {
                "system": system,
                "training_quality_higher_is_better": training_metrics[
                    "quality_higher_is_better"
                ],
                "validation_quality_higher_is_better": validation_metrics[
                    "quality_higher_is_better"
                ],
                "combined_quality_higher_is_better": combined,
            }
        )
    weights = positive_weights(qualities)
    ranking = pd.DataFrame(rows).sort_values(
        "combined_quality_higher_is_better", ascending=False
    )
    ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
    ranking["positive_weight"] = ranking["system"].map(weights)
    ranking.to_csv(destination / "system_ranking.csv", index=False)
    validation_probability = _normalize_rows(
        sum(
            weights[system] * system_probabilities["validation"][system]
            for system in SYSTEMS
        )
    )
    forecast_probability = _normalize_rows(
        sum(
            weights[system] * system_probabilities["forecast"][system]
            for system in SYSTEMS
        )
    )
    validation_output = historical.iloc[validation_indices][
        [
            "date",
            "event_time",
            "mag",
            "latitude",
            "longitude",
            "event_id",
            "zone",
        ]
    ].rename(columns={"zone": "actual_zone"})
    validation_output["predicted_zone"] = (
        np.argmax(validation_probability, axis=1) + 1
    )
    validation_output["predicted_zone_confidence"] = np.max(
        validation_probability, axis=1
    )
    validation_output.to_csv(destination / "validation.csv", index=False)
    forecast_output = pd.DataFrame(
        {
            "date": forecast_frame["date"].astype(str).to_numpy(),
            "predicted_zone": np.argmax(forecast_probability, axis=1) + 1,
            "predicted_zone_confidence": np.max(
                forecast_probability, axis=1
            ),
        }
    )
    forecast_output.to_csv(destination / "forecast.csv", index=False)
    validation_metrics = _location_quality(
        labels[validation_indices], validation_probability, zones
    )
    summary = {
        "status": "COMPLETE",
        "purpose": "randomized-label scientific null control",
        "domain": "localization",
        "training_mode": "randomized",
        "validation_design": "one_shot",
        "incremental": False,
        "seed": int(args.random_seed),
        "label_scramble": (
            "training geographic-zone labels were permuted without replacement; "
            "zone frequencies and the last configured holdout events were preserved"
        ),
        "training_events": len(train_indices),
        "validation_events": len(validation_indices),
        "features": len(features),
        "zone_count": zone_count,
        "validation_metrics": validation_metrics,
        "forecast_rows": len(forecast_frame),
        "epochs_scale": epochs_scale,
        "preprocessing": (
            scaler.audit()
            if isinstance(scaler, QuantileBinTransformer)
            else {"mode": "training_fold_standard_scaler", "n_bins": 0}
        ),
        "does_not_affect_primary_forecast": True,
    }
    write_json(destination / "summary.json", summary)
    return summary

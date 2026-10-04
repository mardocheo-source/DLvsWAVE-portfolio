#!/usr/bin/env python3
"""Parameterized weekly one-shot joint seismic-zone localization for v12."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import warnings

os.environ.setdefault("MPLCONFIGDIR", "/tmp/joint-cluster-location-v9")

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from quantile_preprocessing import QuantileBinTransformer

from common_v6 import (
    BASES,
    LOCATION_META,
    PROJECT,
    REPO,
    SYSTEMS,
    export_lcs_rules,
    fit_real_binary,
    model_configuration,
    positive_weights,
    proxy,
    rank_features,
    sha256,
    write_json,
)


SEED = 570701
EXPECTED_LOCATION_SHA256 = (
    "2c32608240bba389b73446a3b0458026977d7583ac5219b94581e5d5679af99e"
)
EXPECTED_TIMING_SHA256 = (
    "c90eef6e46fd77152c07decb2fa0c2f97599ded37ae3decc2b8decf503921464"
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="v12 parameterized weekly joint seismic-zone location model"
    )
    value.add_argument("--interval-days", type=int, default=7)
    value.add_argument("--magnitude-threshold", type=float, default=7.9)
    value.add_argument(
        "--validation-magnitude-threshold",
        type=float,
        default=None,
        help=(
            "Optional lower floor for the final chronological holdouts only; "
            "training continues to use --magnitude-threshold."
        ),
    )
    value.add_argument(
        "--training-mode",
        choices=("sequential", "randomized"),
        default="sequential",
        help=(
            "sequential runs the primary one-shot location model; randomized "
            "runs a separate one-shot training-label permutation control."
        ),
    )
    value.add_argument("--random-seed", type=int, default=570799)
    value.add_argument("--validation-events", type=int, default=5)
    value.add_argument("--inner-validation-events", type=int, default=5)
    value.add_argument(
        "--indirect-validation-magnitude-threshold",
        type=float,
        default=0.0,
        help=(
            "Optional lower magnitude floor for a separate, never-tuned indirect "
            "location audit; zero disables it."
        ),
    )
    value.add_argument("--indirect-validation-events", type=int, default=0)
    value.add_argument(
        "--minimum-validation-zones",
        type=int,
        default=1,
        help=(
            "Required number of distinct learned zones in the chronological "
            "outer holdout. The default preserves legacy runs; values above "
            "one make a non-discriminating single-zone holdout fail loudly."
        ),
    )
    value.add_argument(
        "--minimum-predictive-construction-events",
        type=int,
        default=9,
        help=(
            "Minimum M-threshold master events strictly before the inner and "
            "outer location holdouts."
        ),
    )
    value.add_argument("--minimum-zones", type=int, default=3)
    value.add_argument(
        "--maximum-zones",
        type=int,
        default=5,
        help=(
            "Upper bound for automatic zone-count search; five is the default "
            "because location outer validation contains at most five events."
        ),
    )
    value.add_argument("--minimum-zone-events", type=int, default=5)
    value.add_argument(
        "--zone-catalog",
        default=str(REPO / "constant_explorer/japan_usgs_m6_1900_20260517.csv"),
        help=(
            "Earthquake catalog used only to learn joint geographic zones. "
            "Predictive feature training continues to use location_master.csv."
        ),
    )
    value.add_argument(
        "--zone-construction-magnitude-threshold",
        type=float,
        default=7.1,
        help=(
            "Magnitude floor used only to learn geographic zone boundaries; "
            "the predictive target keeps --magnitude-threshold."
        ),
    )
    value.add_argument("--zone-catalog-start", default="1900-01-01")
    value.add_argument("--map-latitude-min", type=float, default=28.0)
    value.add_argument("--map-latitude-max", type=float, default=47.0)
    value.add_argument("--map-longitude-min", type=float, default=128.0)
    value.add_argument("--map-longitude-max", type=float, default=149.5)
    value.add_argument("--feature-min", type=int, default=5)
    value.add_argument("--probe-budget", type=int, default=24)
    value.add_argument("--probe-block-size", type=int, default=4)
    value.add_argument("--proxy-quality-tolerance", type=float, default=0.008)
    value.add_argument("--real-quality-tolerance", type=float, default=0.015)
    value.add_argument("--epochs-scale", type=float, default=0.55)
    value.add_argument(
        "--quantile-bins",
        type=int,
        default=0,
        help=(
            "Fit feature quantiles on each location training split only; zero "
            "disables and four emits levels 0, 1/3, 2/3 and 1."
        ),
    )
    value.add_argument(
        "--model-overrides-json",
        default="",
        help="JSON of promoted per-family hyperparameters from a fast screen.",
    )
    value.add_argument("--forecast-grid-start", default="2026-07-17")
    value.add_argument("--forecast-visible-start", default="2026-07-17")
    value.add_argument("--forecast-end", default="2026-08-21")
    value.add_argument(
        "--expected-location-master-sha256",
        default=EXPECTED_LOCATION_SHA256,
        help="Audited location-master checksum; pass an empty string to disable.",
    )
    value.add_argument(
        "--expected-timing-master-sha256",
        default=EXPECTED_TIMING_SHA256,
        help="Audited timing-master checksum; pass an empty string to disable.",
    )
    return value


def validate_args(args) -> None:
    if args.interval_days < 1:
        raise ValueError("interval-days must be positive")
    if (
        args.validation_magnitude_threshold is not None
        and args.validation_magnitude_threshold > args.magnitude_threshold
    ):
        raise ValueError(
            "validation-magnitude-threshold cannot exceed the training threshold"
        )
    if args.quantile_bins not in {0} and args.quantile_bins < 2:
        raise ValueError("quantile-bins must be zero or at least two")
    if not 2 <= args.validation_events <= 5:
        raise ValueError("Location validation must contain between two and five events")
    if args.inner_validation_events < 1:
        raise ValueError("At least one inner validation event is required")
    if not 1 <= args.minimum_validation_zones <= args.validation_events:
        raise ValueError(
            "minimum-validation-zones must be between one and validation-events"
        )
    if args.minimum_predictive_construction_events < 3:
        raise ValueError(
            "minimum-predictive-construction-events must be at least three"
        )
    if args.minimum_zones < 3 or args.maximum_zones < args.minimum_zones:
        raise ValueError("Invalid zone range")
    if args.minimum_zone_events < 2:
        raise ValueError("minimum-zone-events is too small")
    if args.feature_min < 5:
        raise ValueError("Feature floor cannot be below five")
    if not (
        args.map_latitude_min < args.map_latitude_max
        and args.map_longitude_min < args.map_longitude_max
    ):
        raise ValueError("Invalid map bounds")
    grid = pd.Timestamp(args.forecast_grid_start)
    visible = pd.Timestamp(args.forecast_visible_start)
    if not (
        grid
        <= visible
        < grid + pd.Timedelta(days=args.interval_days)
    ):
        raise ValueError("Visible start must fall inside the first exact grid slot")


def deduplicate_slots(history: pd.DataFrame) -> pd.DataFrame:
    value = history.copy()
    value["slot_key"] = value["slot_start"].fillna(value["date"]).astype(str)
    value = value.sort_values(
        ["slot_key", "mag", "event_time"],
        ascending=[True, False, True],
    )
    return (
        value.drop_duplicates("slot_key", keep="first")
        .sort_values("event_time")
        .reset_index(drop=True)
    )


def load_zone_catalog(args, cutoff: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Load a broader, geography-only catalog without leaking outer holdouts."""
    path = Path(args.zone_catalog).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    catalog = pd.read_csv(path, low_memory=False)
    required = {"time", "mag", "latitude", "longitude", "id"}
    missing = sorted(required.difference(catalog.columns))
    if missing:
        raise ValueError(f"Zone catalog is missing columns: {missing}")
    catalog["event_time"] = pd.to_datetime(catalog["time"], utc=True, errors="coerce")
    cutoff_utc = pd.Timestamp(cutoff)
    cutoff_utc = (
        cutoff_utc.tz_localize("UTC")
        if cutoff_utc.tzinfo is None
        else cutoff_utc.tz_convert("UTC")
    )
    start_utc = pd.Timestamp(args.zone_catalog_start, tz="UTC")
    filtered = catalog.loc[
        catalog["event_time"].ge(start_utc)
        & catalog["event_time"].lt(cutoff_utc)
        & pd.to_numeric(catalog["mag"], errors="coerce").ge(
            args.zone_construction_magnitude_threshold
        )
        & pd.to_numeric(catalog["latitude"], errors="coerce").between(
            args.map_latitude_min, args.map_latitude_max
        )
        & pd.to_numeric(catalog["longitude"], errors="coerce").between(
            args.map_longitude_min, args.map_longitude_max
        )
    ].copy()
    landmarks = filtered.loc[
        filtered["event_time"].dt.strftime("%Y-%m").eq("1923-09"),
        ["event_time", "mag", "latitude", "longitude", "id", "place"],
    ].rename(columns={"id": "event_id"})
    selected = filtered.copy()
    selected["event_id"] = selected["id"].astype(str)
    selected["date"] = selected["event_time"].dt.strftime("%Y-%m-%d")
    # Use the same explicit start-labelled grid as the timing master.  Pandas
    # ``W-FRI`` periods end on Friday (and therefore start on Saturday), which
    # would silently put geography-only records on a different weekly grid.
    grid_origin = pd.Timestamp(args.forecast_grid_start).normalize()
    event_naive = selected["event_time"].dt.tz_localize(None)
    slot_offsets = np.floor(
        (event_naive - grid_origin) / pd.Timedelta(days=args.interval_days)
    ).astype(int)
    selected["slot_start"] = (
        grid_origin
        + pd.to_timedelta(slot_offsets * args.interval_days, unit="D")
    ).dt.strftime("%Y-%m-%d")
    selected = deduplicate_slots(selected)
    audit = {
        "path": str(path),
        "sha256": sha256(path),
        "start": args.zone_catalog_start,
        "exclusive_cutoff": cutoff_utc.isoformat(),
        "magnitude_threshold": args.zone_construction_magnitude_threshold,
        "predictive_target_magnitude_threshold": args.magnitude_threshold,
        "geographic_bounds": {
            "latitude": [args.map_latitude_min, args.map_latitude_max],
            "longitude": [args.map_longitude_min, args.map_longitude_max],
        },
        "rows_after_filter_and_slot_deduplication": len(selected),
        "september_1923_landmarks": landmarks.to_dict("records"),
        "predictive_features_used": False,
    }
    return selected.reset_index(drop=True), audit


def geographic_embedding(
    latitude: np.ndarray,
    longitude: np.ndarray,
    reference_latitude: float,
    reference_longitude: float,
) -> np.ndarray:
    """Local metric embedding in kilometres around configured map centre."""
    latitude = np.asarray(latitude, float)
    longitude = np.asarray(longitude, float)
    cosine_latitude = np.cos(np.deg2rad(reference_latitude))
    north = (latitude - reference_latitude) * 111.2
    east = (longitude - reference_longitude) * 111.2 * cosine_latitude
    return np.column_stack([east, north])


def haversine_km(
    latitude_a: np.ndarray,
    longitude_a: np.ndarray,
    latitude_b: np.ndarray,
    longitude_b: np.ndarray,
) -> np.ndarray:
    latitude_a = np.deg2rad(np.asarray(latitude_a, float))
    longitude_a = np.deg2rad(np.asarray(longitude_a, float))
    latitude_b = np.deg2rad(np.asarray(latitude_b, float))
    longitude_b = np.deg2rad(np.asarray(longitude_b, float))
    d_latitude = latitude_b - latitude_a
    d_longitude = longitude_b - longitude_a
    value = (
        np.sin(d_latitude / 2.0) ** 2
        + np.cos(latitude_a)
        * np.cos(latitude_b)
        * np.sin(d_longitude / 2.0) ** 2
    )
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(np.clip(value, 0.0, 1.0)))


def fit_zones(events: pd.DataFrame, args) -> tuple[GaussianMixture, dict, pd.DataFrame]:
    reference_latitude = (args.map_latitude_min + args.map_latitude_max) / 2.0
    reference_longitude = (args.map_longitude_min + args.map_longitude_max) / 2.0
    coordinates = geographic_embedding(
        events["latitude"],
        events["longitude"],
        reference_latitude,
        reference_longitude,
    )
    trials = []
    fitted: dict[int, tuple[GaussianMixture, np.ndarray]] = {}
    for zones in range(args.minimum_zones, args.maximum_zones + 1):
        model = GaussianMixture(
            n_components=zones,
            covariance_type="full",
            reg_covar=1e-3,
            n_init=12,
            max_iter=500,
            random_state=SEED + zones,
        ).fit(coordinates)
        labels = model.predict(coordinates)
        counts = np.bincount(labels, minlength=zones)
        valid = bool(np.min(counts) >= args.minimum_zone_events)
        silhouette = (
            float(silhouette_score(coordinates, labels))
            if valid and len(np.unique(labels)) > 1
            else -1.0
        )
        trials.append(
            {
                "zones": zones,
                "bic": float(model.bic(coordinates)),
                "silhouette_higher_is_better": silhouette,
                "minimum_cluster_events": int(np.min(counts)),
                "valid_minimum_size": valid,
            }
        )
        fitted[zones] = (model, labels)
    valid_trials = [row for row in trials if row["valid_minimum_size"]]
    if not valid_trials:
        raise RuntimeError("No cluster count satisfies the minimum zone size")
    bic_values = np.asarray([row["bic"] for row in valid_trials], float)
    bic_skill = (
        np.ones(len(valid_trials), float)
        if np.ptp(bic_values) <= 1e-12
        else (np.max(bic_values) - bic_values) / np.ptp(bic_values)
    )
    for row, skill in zip(valid_trials, bic_skill):
        row["bic_skill_higher_is_better"] = float(skill)
        row["selection_quality_higher_is_better"] = float(
            0.80 * row["silhouette_higher_is_better"] + 0.20 * skill
        )
    selected_trial = max(
        valid_trials,
        key=lambda row: (
            row["selection_quality_higher_is_better"],
            row["silhouette_higher_is_better"],
        ),
    )
    model, original_labels = fitted[int(selected_trial["zones"])]
    means = model.means_
    order = np.lexsort((means[:, 0], means[:, 1]))
    original_to_zone = {
        int(original): int(zone + 1) for zone, original in enumerate(order)
    }
    labels = np.asarray([original_to_zone[int(label)] for label in original_labels])
    zone_rows = []
    for original in order:
        zone = original_to_zone[int(original)]
        members = events.iloc[np.flatnonzero(original_labels == original)]
        latitude = members["latitude"].to_numpy(float)
        longitude = members["longitude"].to_numpy(float)
        centre_latitude = float(np.mean(latitude))
        centre_longitude = float(np.mean(longitude))
        zone_rows.append(
            {
                "zone": zone,
                "events": len(members),
                "center_latitude": centre_latitude,
                "center_longitude": centre_longitude,
                "raw_latitude_low": float(
                    max(args.map_latitude_min, np.quantile(latitude, 0.05) - 0.45)
                ),
                "raw_latitude_high": float(
                    min(args.map_latitude_max, np.quantile(latitude, 0.95) + 0.45)
                ),
                "raw_longitude_low": float(
                    max(args.map_longitude_min, np.quantile(longitude, 0.05) - 0.55)
                ),
                "raw_longitude_high": float(
                    min(args.map_longitude_max, np.quantile(longitude, 0.95) + 0.55)
                ),
                "longitude_low": float(
                    max(args.map_longitude_min, np.min(longitude) - 0.30)
                ),
                "longitude_high": float(
                    min(args.map_longitude_max, np.max(longitude) + 0.30)
                ),
                "gmm_original_component": int(original),
                "covariance_east_north_km2": model.covariances_[original].tolist(),
            }
        )
    zones = pd.DataFrame(zone_rows)
    # Keep the learned GMM assignments, but make the displayed north/south
    # envelopes exhaustive. Midpoints between adjacent learned centroids ensure
    # that central Japan cannot disappear between quantile rectangles.
    centers = zones["center_latitude"].to_numpy(float)
    boundaries = (centers[:-1] + centers[1:]) / 2.0
    zones["latitude_low"] = np.r_[args.map_latitude_min, boundaries]
    zones["latitude_high"] = np.r_[boundaries, args.map_latitude_max]
    zones["zone_name"] = [
        "southern"
        if index == 0
        else "northern"
        if index == len(zones) - 1
        else f"central_{index}"
        for index in range(len(zones))
    ]
    audit = {
        "construction_rows": len(events),
        "selection_rule": (
            "full-covariance Gaussian mixtures; 80% geometric separation "
            "(silhouette) + 20% BIC skill; "
            "every zone must satisfy the minimum event count"
        ),
        "trials": trials,
        "selected": selected_trial,
        "original_component_to_numbered_zone": original_to_zone,
        "embedding_reference": {
            "latitude": reference_latitude,
            "longitude": reference_longitude,
        },
        "display_envelope_rule": (
            "raw GMM latitude quantiles are preserved as raw_latitude_low/high; "
            "display latitude bands use adjacent learned-centroid midpoints and "
            "cover the configured map range continuously without gaps; longitude "
            "display bounds include the complete learned cluster range while raw "
            "longitude quantiles remain separately audited"
        ),
    }
    return model, audit, zones


def assign_zones(
    model: GaussianMixture,
    audit: dict,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> np.ndarray:
    reference = audit["embedding_reference"]
    original = model.predict(
        geographic_embedding(
            latitude,
            longitude,
            float(reference["latitude"]),
            float(reference["longitude"]),
        )
    )
    mapping = {
        int(key): int(value)
        for key, value in audit["original_component_to_numbered_zone"].items()
    }
    return np.asarray([mapping[int(label)] for label in original], int)


def geographic_zone_grid(
    model: GaussianMixture,
    audit: dict,
    args,
    resolution_degrees: float = 0.10,
) -> pd.DataFrame:
    """Materialize the complete GMM decision territory for report maps."""
    latitudes = np.arange(
        args.map_latitude_min,
        args.map_latitude_max + resolution_degrees / 2.0,
        resolution_degrees,
    )
    longitudes = np.arange(
        args.map_longitude_min,
        args.map_longitude_max + resolution_degrees / 2.0,
        resolution_degrees,
    )
    longitude_mesh, latitude_mesh = np.meshgrid(longitudes, latitudes)
    zones = assign_zones(
        model,
        audit,
        latitude_mesh.ravel(),
        longitude_mesh.ravel(),
    )
    return pd.DataFrame(
        {
            "latitude": latitude_mesh.ravel(),
            "longitude": longitude_mesh.ravel(),
            "zone": zones,
        }
    )


def align_probability(model, values: np.ndarray, classes: int) -> np.ndarray:
    raw = np.asarray(model.predict_proba(values), float)
    output = np.zeros((len(values), classes), float)
    for source, label in enumerate(np.asarray(model.classes_, int)):
        if 1 <= label <= classes:
            output[:, label - 1] = raw[:, source]
    return output / np.maximum(output.sum(axis=1, keepdims=True), 1e-12)


def zone_metrics(
    actual_zone: np.ndarray,
    probability: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    zones: pd.DataFrame,
) -> dict:
    actual_zone = np.asarray(actual_zone, int)
    probability = np.asarray(probability, float)
    predicted_zone = np.argmax(probability, axis=1) + 1
    ranking = np.argsort(-probability, axis=1) + 1
    exact = float(np.mean(predicted_zone == actual_zone))
    top_two = float(
        np.mean(
            [
                actual_zone[index] in ranking[index, : min(2, probability.shape[1])]
                for index in range(len(actual_zone))
            ]
        )
    )
    true_probability = float(
        np.mean(probability[np.arange(len(actual_zone)), actual_zone - 1])
    )
    centers = zones.set_index("zone")
    predicted_latitude = np.asarray(
        [centers.loc[zone, "center_latitude"] for zone in predicted_zone],
        float,
    )
    predicted_longitude = np.asarray(
        [centers.loc[zone, "center_longitude"] for zone in predicted_zone],
        float,
    )
    distance = haversine_km(
        latitude,
        longitude,
        predicted_latitude,
        predicted_longitude,
    )
    distance_skill = float(np.clip(1.0 - np.mean(distance) / 1400.0, 0.0, 1.0))
    quality = float(
        0.35 * exact
        + 0.15 * top_two
        + 0.25 * true_probability
        + 0.25 * distance_skill
    )
    return {
        "n": len(actual_zone),
        "exact_zone_accuracy": exact,
        "top_two_zone_accuracy": top_two,
        "true_zone_probability_skill": true_probability,
        "distance_skill": distance_skill,
        "mean_centroid_distance_km": float(np.mean(distance)),
        "quality_higher_is_better": quality,
        "actual_zones": actual_zone.tolist(),
        "predicted_zones": predicted_zone.tolist(),
        "predicted_center_latitudes": predicted_latitude.tolist(),
        "predicted_center_longitudes": predicted_longitude.tolist(),
        "distances_km": distance.tolist(),
        "metric_direction": "all selection skills: higher is better",
    }


def proxy_evaluation(
    X: np.ndarray,
    labels: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    features: list[int],
    zones: pd.DataFrame,
    seed: int,
) -> dict:
    classes = len(zones)
    base = {"training": {}, "validation": {}}
    for member_id, member in enumerate(BASES):
        model = proxy(member, seed + member_id * 97)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X[train][:, features], labels[train])
        base["training"][member] = align_probability(
            model, X[train][:, features], classes
        )
        base["validation"][member] = align_probability(
            model, X[validation][:, features], classes
        )
    systems = {}
    for system, members in SYSTEMS.items():
        training_probability = np.mean(
            np.stack([base["training"][member] for member in members]), axis=0
        )
        validation_probability = np.mean(
            np.stack([base["validation"][member] for member in members]), axis=0
        )
        training_metrics = zone_metrics(
            labels[train],
            training_probability,
            latitude[train],
            longitude[train],
            zones,
        )
        validation_metrics = zone_metrics(
            labels[validation],
            validation_probability,
            latitude[validation],
            longitude[validation],
            zones,
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
    exact = np.asarray(
        [row["validation"]["exact_zone_accuracy"] for row in systems.values()]
    )
    return {
        "feature_count": len(features),
        "aggregate_quality_higher_is_better": float(
            0.55 * np.median(qualities)
            + 0.30 * np.quantile(qualities, 0.25)
            + 0.15 * np.min(qualities)
        ),
        "system_quality_min": float(np.min(qualities)),
        "validation_exact_median": float(np.median(exact)),
        "systems": systems,
    }


def intelligent_ablation(
    X: np.ndarray,
    labels: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    names: list[str],
    initial: list[int],
    train: np.ndarray,
    validation: np.ndarray,
    zones: pd.DataFrame,
    args,
) -> list[int]:
    search_X = X
    if args.quantile_bins >= 2:
        quantizer = QuantileBinTransformer(args.quantile_bins).fit(
            X[train][:, initial]
        )
        search_X = X.copy()
        search_X[:, initial] = quantizer.transform(X[:, initial])
    ranking, ranking_audit = rank_features(
        search_X[train], labels[train], initial, names, SEED + 100
    )
    ranking_audit["preprocessing"] = (
        quantizer.audit()
        if args.quantile_bins >= 2
        else {"mode": "raw_proxy_features", "n_bins": 0}
    )
    write_json(
        PROJECT / "03_feature_research/location_zones/feature_ranking.json",
        ranking_audit,
    )
    removal_order = list(reversed(ranking))
    baseline = proxy_evaluation(
        search_X,
        labels,
        latitude,
        longitude,
        train,
        validation,
        initial,
        zones,
        SEED + 200,
    )
    current_features = list(initial)
    current = baseline
    trials = []
    attempted = 0
    trial_id = 0
    while attempted < min(args.probe_budget, len(removal_order)):
        block = [
            index
            for index in removal_order[
                attempted : attempted + args.probe_block_size
            ]
            if index in current_features
        ]
        attempted += args.probe_block_size
        if not block or len(current_features) - len(block) < args.feature_min:
            continue
        trial_id += 1
        candidate_features = [
            index for index in current_features if index not in set(block)
        ]
        candidate = proxy_evaluation(
            search_X,
            labels,
            latitude,
            longitude,
            train,
            validation,
            candidate_features,
            zones,
            SEED + 200 + trial_id,
        )
        accepted = bool(
            candidate["aggregate_quality_higher_is_better"]
            >= current["aggregate_quality_higher_is_better"]
            - args.proxy_quality_tolerance
            and candidate["system_quality_min"]
            >= baseline["system_quality_min"] - 0.04
            and candidate["validation_exact_median"]
            >= baseline["validation_exact_median"] - 0.10
        )
        trials.append(
            {
                "trial": trial_id,
                "removed_features": [names[index] for index in block],
                "feature_count_after": len(candidate_features),
                "aggregate_quality_higher_is_better": candidate[
                    "aggregate_quality_higher_is_better"
                ],
                "validation_exact_median": candidate[
                    "validation_exact_median"
                ],
                "accepted": accepted,
            }
        )
        if accepted:
            current_features = candidate_features
            current = candidate
    pd.DataFrame(trials).to_csv(
        PROJECT / "03_feature_research/location_zones/ablation_trials.csv",
        index=False,
    )
    write_json(
        PROJECT / "03_feature_research/location_zones/proxy_summary.json",
        {
            "baseline_feature_count": len(initial),
            "selected_feature_count": len(current_features),
            "baseline": baseline,
            "selected": current,
        },
    )
    return current_features


def fit_real_multiclass(
    kind: str,
    X: np.ndarray,
    labels: np.ndarray,
    classes: int,
    seed: int,
    epochs_scale: float,
):
    models = []
    predictors = []
    for class_index in range(classes):
        target = (labels == class_index + 1).astype(int)
        model, predict = fit_real_binary(
            kind,
            X,
            target,
            seed + class_index * 31,
            epochs_scale,
        )
        models.append(model)
        predictors.append(predict)

    def predict(values: np.ndarray) -> np.ndarray:
        raw = np.column_stack([function(values) for function in predictors])
        raw = np.clip(raw, 1e-8, None)
        return raw / np.maximum(raw.sum(axis=1, keepdims=True), 1e-12)

    return models, predict


def fit_real_bank(
    X: np.ndarray,
    labels: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    forecast_X: np.ndarray,
    indirect_X: np.ndarray | None,
    features: list[int],
    args,
    seed: int,
) -> dict:
    scaler = (
        QuantileBinTransformer(args.quantile_bins)
        if args.quantile_bins >= 2
        else StandardScaler()
    )
    scaler.fit(X[train][:, features])
    X_train = scaler.transform(X[train][:, features])
    X_validation = scaler.transform(X[validation][:, features])
    X_forecast = scaler.transform(forecast_X[:, features])
    X_indirect = (
        scaler.transform(indirect_X[:, features])
        if indirect_X is not None and len(indirect_X)
        else None
    )
    classes = int(np.max(labels))
    models = {}
    outputs = {"training": {}, "validation": {}, "forecast": {}, "indirect": {}}
    runtimes = {}
    for member_id, member in enumerate(BASES):
        member_started = time.perf_counter()
        model, predict = fit_real_multiclass(
            member,
            X_train,
            labels[train],
            classes,
            seed + member_id * 1000,
            args.epochs_scale,
        )
        models[member] = model
        outputs["training"][member] = predict(X_train)
        outputs["validation"][member] = predict(X_validation)
        outputs["forecast"][member] = predict(X_forecast)
        if X_indirect is not None:
            outputs["indirect"][member] = predict(X_indirect)
        runtimes[member] = {
            "fit_and_inference_seconds": float(time.perf_counter() - member_started),
            "binary_fits": int(classes),
            "training_rows": int(len(train)),
            "feature_count": int(len(features)),
        }
    return {
        "models": models,
        "outputs": outputs,
        "scaler": scaler,
        "runtimes": runtimes,
        "preprocessing": (
            scaler.audit()
            if isinstance(scaler, QuantileBinTransformer)
            else {"mode": "training_fold_standard_scaler", "n_bins": 0}
        ),
    }


def evaluate_real_bank(
    bank: dict,
    labels: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    train: np.ndarray,
    validation: np.ndarray,
    zones: pd.DataFrame,
) -> tuple[dict, pd.DataFrame]:
    systems = {}
    rows = []
    for system, members in SYSTEMS.items():
        training_probability = np.mean(
            np.stack([bank["outputs"]["training"][member] for member in members]),
            axis=0,
        )
        validation_probability = np.mean(
            np.stack([bank["outputs"]["validation"][member] for member in members]),
            axis=0,
        )
        training_metrics = zone_metrics(
            labels[train],
            training_probability,
            latitude[train],
            longitude[train],
            zones,
        )
        validation_metrics = zone_metrics(
            labels[validation],
            validation_probability,
            latitude[validation],
            longitude[validation],
            zones,
        )
        origin = float(
            0.25 * training_metrics["quality_higher_is_better"]
            + 0.75 * validation_metrics["quality_higher_is_better"]
        )
        systems[system] = {
            "training_metrics": training_metrics,
            "validation_metrics": validation_metrics,
            "origin_quality_25train_75validation": origin,
            "training_probability": training_probability,
            "validation_probability": validation_probability,
            "forecast_probability": np.mean(
                np.stack(
                    [bank["outputs"]["forecast"][member] for member in members]
                ),
                axis=0,
            ),
        }
        rows.append(
            {
                "system": system,
                "origin_quality_25train_75validation": origin,
                "training_quality": training_metrics["quality_higher_is_better"],
                "validation_quality": validation_metrics["quality_higher_is_better"],
                "validation_exact_zone": validation_metrics[
                    "exact_zone_accuracy"
                ],
                "validation_top_two_zone": validation_metrics[
                    "top_two_zone_accuracy"
                ],
                "validation_mean_centroid_distance_km": validation_metrics[
                    "mean_centroid_distance_km"
                ],
            }
        )
    return systems, pd.DataFrame(rows)


def weighted_system_probability(
    systems: dict,
    ranking: pd.DataFrame,
    split: str,
    selected_names: list[str],
    hard_vote: bool,
    temperature: float = 0.08,
) -> np.ndarray:
    selected = ranking.set_index("system").loc[selected_names].reset_index()
    quality = selected["origin_quality_25train_75validation"].to_numpy(float)
    weights = np.exp((quality - np.max(quality)) / temperature)
    weights /= weights.sum()
    sample = systems[selected_names[0]][f"{split}_probability"]
    fused = np.zeros_like(sample)
    for weight, system in zip(weights, selected_names):
        probability = systems[system][f"{split}_probability"]
        if hard_vote:
            contribution = np.zeros_like(probability)
            contribution[
                np.arange(len(contribution)), np.argmax(probability, axis=1)
            ] = 1.0
        else:
            contribution = probability
        fused += float(weight) * contribution
    return fused / np.maximum(fused.sum(axis=1, keepdims=True), 1e-12)


def prior_correct(probability: np.ndarray, priors: np.ndarray, strength: float):
    corrected = probability / np.maximum(priors[None, :], 1e-8) ** strength
    return corrected / np.maximum(corrected.sum(axis=1, keepdims=True), 1e-12)


def diverse_systems(ranking: pd.DataFrame, count: int = 3) -> list[str]:
    ordered = ranking["system"].tolist()
    selected = [ordered[0]]
    while len(selected) < count:
        candidates = [name for name in ordered if name not in selected]
        best = max(
            candidates,
            key=lambda name: (
                np.mean(
                    [
                        1.0
                        - len(set(SYSTEMS[name]) & set(SYSTEMS[chosen]))
                        / len(set(SYSTEMS[name]) | set(SYSTEMS[chosen]))
                        for chosen in selected
                    ]
                ),
                -ordered.index(name),
            ),
        )
        selected.append(best)
    return selected


def select_fusion(
    systems: dict,
    ranking: pd.DataFrame,
    labels: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    validation: np.ndarray,
    zones: pd.DataFrame,
    training_labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    ordered = ranking["system"].tolist()
    top_three = ordered[:3]
    bases = [
        base if base.startswith("deep_") else f"{base}_only" for base in BASES
    ]
    diverse = diverse_systems(ranking, count=3)
    definitions = {
        "best_single": ([ordered[0]], False),
        "top3_hard_vote": (top_three, True),
        "top3_soft_probability": (top_three, False),
        "diverse3_soft_probability": (diverse, False),
        "five_bases_soft_probability": (bases, False),
        "all16_quality_soft_probability": (ordered, False),
    }
    priors = np.bincount(
        np.asarray(training_labels, int) - 1,
        minlength=len(zones),
    ).astype(float)
    priors /= priors.sum()
    candidates = {}
    for name, (members, hard) in definitions.items():
        validation_probability = weighted_system_probability(
            systems, ranking, "validation", members, hard
        )
        forecast_probability = weighted_system_probability(
            systems, ranking, "forecast", members, hard
        )
        candidates[name] = (validation_probability, forecast_probability, members)
        if not hard:
            for strength in (0.35, 0.65, 1.0):
                corrected_name = f"{name}_prior_correct_{strength:.2f}"
                candidates[corrected_name] = (
                    prior_correct(validation_probability, priors, strength),
                    prior_correct(forecast_probability, priors, strength),
                    members,
                )
    trials = []
    for name, (validation_probability, _, members) in candidates.items():
        metrics = zone_metrics(
            labels[validation],
            validation_probability,
            latitude[validation],
            longitude[validation],
            zones,
        )
        trials.append(
            {
                "fusion": name,
                "members": members,
                "quality_higher_is_better": metrics[
                    "quality_higher_is_better"
                ],
                "exact_zone_accuracy": metrics["exact_zone_accuracy"],
                "top_two_zone_accuracy": metrics["top_two_zone_accuracy"],
                "mean_centroid_distance_km": metrics[
                    "mean_centroid_distance_km"
                ],
                "unique_predicted_zones": len(set(metrics["predicted_zones"])),
            }
        )
    selected = max(
        trials,
        key=lambda row: (
            row["quality_higher_is_better"],
            row["exact_zone_accuracy"],
            row["top_two_zone_accuracy"],
            row["unique_predicted_zones"],
        ),
    )
    validation_probability, forecast_probability, _ = candidates[selected["fusion"]]
    audit = {
        "selection_rule": (
            "highest outer-validation quality; exact and top-two accuracy then "
            "prediction diversity break ties; all metrics higher-is-better except "
            "reported centroid distance"
        ),
        "zone_training_priors": priors.tolist(),
        "selected": selected,
        "trials": trials,
    }
    return validation_probability, forecast_probability, audit


def main() -> None:
    args = parser().parse_args()
    if args.model_overrides_json:
        os.environ["DLVSWAVE_MODEL_OVERRIDES_JSON"] = str(
            Path(args.model_overrides_json).expanduser().resolve()
        )
    else:
        os.environ.pop("DLVSWAVE_MODEL_OVERRIDES_JSON", None)
    validate_args(args)
    started = time.time()
    for directory in (
        PROJECT / "02_audit",
        PROJECT / "03_feature_research/location_zones",
        PROJECT / "04_models/location_zones",
        PROJECT / "05_ensemble",
        PROJECT / "07_randomized_control/location",
        PROJECT / "logs",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    if args.training_mode == "randomized":
        from randomized_control import run_randomized_location

        summary = run_randomized_location(args)
        summary["elapsed_seconds"] = time.time() - started
        write_json(
            PROJECT / "07_randomized_control/location/completion.json",
            summary,
        )
        print(
            json.dumps(summary, indent=2, ensure_ascii=False, default=str),
            flush=True,
        )
        return
    obsolete_check = PROJECT / "05_ensemble/kumamoto_location_check.json"
    if obsolete_check.exists():
        obsolete_check.unlink()
    location_path = PROJECT / "01_inputs/location_master.csv"
    timing_path = PROJECT / "01_inputs/timing_master.csv"
    if (
        args.expected_location_master_sha256
        and sha256(location_path) != args.expected_location_master_sha256
    ):
        raise RuntimeError("Location master checksum mismatch")
    if (
        args.expected_timing_master_sha256
        and sha256(timing_path) != args.expected_timing_master_sha256
    ):
        raise RuntimeError("Timing master checksum mismatch")
    location = pd.read_csv(location_path, low_memory=False)
    timing = pd.read_csv(timing_path, low_memory=False)
    historical = deduplicate_slots(location.loc[location["is_forecast"].eq(0)])
    validation_floor = float(
        args.validation_magnitude_threshold
        if args.validation_magnitude_threshold is not None
        else args.magnitude_threshold
    )
    validation_candidates = historical.loc[
        historical["mag"].ge(validation_floor)
    ].tail(args.validation_events).copy()
    if len(validation_candidates) != args.validation_events:
        raise RuntimeError(
            "Insufficient events at the configured location-validation floor"
        )
    first_validation_time = pd.to_datetime(
        validation_candidates.iloc[0]["event_time"], utc=True
    )
    historical_times = pd.to_datetime(historical["event_time"], utc=True)
    validation_slots = set(validation_candidates["slot_start"].astype(str))
    training_events = historical.loc[
        historical["mag"].ge(args.magnitude_threshold)
        & historical_times.lt(first_validation_time)
        & ~historical["slot_start"].astype(str).isin(validation_slots)
    ].copy()
    events = pd.concat(
        [training_events, validation_candidates], ignore_index=True
    ).reset_index(drop=True)
    indirect_events = pd.DataFrame(columns=historical.columns)
    if (
        args.indirect_validation_events > 0
        and 0 < args.indirect_validation_magnitude_threshold < args.magnitude_threshold
    ):
        indirect_events = historical.loc[
            historical["mag"].ge(args.indirect_validation_magnitude_threshold)
            & historical["mag"].lt(args.magnitude_threshold)
            & ~historical["event_id"].astype(str).isin(
                validation_candidates["event_id"].astype(str)
            )
        ].tail(args.indirect_validation_events).reset_index(drop=True)
    outer_train_count = len(events) - args.validation_events
    inner_train_count = outer_train_count - args.inner_validation_events
    if inner_train_count < args.minimum_predictive_construction_events:
        raise RuntimeError(
            "Insufficient strictly separated zone-construction events: "
            f"available={inner_train_count}, "
            f"minimum={args.minimum_predictive_construction_events}"
        )
    predictive_zone_construction = events.iloc[:inner_train_count].copy()
    zone_cutoff = pd.to_datetime(
        events.iloc[inner_train_count]["event_time"], utc=True
    )
    zone_construction, zone_catalog_audit = load_zone_catalog(args, zone_cutoff)
    zone_model, zone_audit, zones = fit_zones(zone_construction, args)
    zone_audit["catalog"] = zone_catalog_audit
    zone_audit["predictive_master_construction_rows"] = len(
        predictive_zone_construction
    )
    labels = assign_zones(
        zone_model,
        zone_audit,
        events["latitude"],
        events["longitude"],
    )
    events["zone"] = labels
    indirect_labels = (
        assign_zones(
            zone_model,
            zone_audit,
            indirect_events["latitude"],
            indirect_events["longitude"],
        )
        if len(indirect_events)
        else np.asarray([], dtype=int)
    )
    if len(indirect_events):
        indirect_events["zone"] = indirect_labels
    validation_labels = labels[-args.validation_events :]
    validation_zone_count = int(len(np.unique(validation_labels)))
    zone_audit["outer_validation_zone_diversity"] = {
        "required_distinct_zones": int(args.minimum_validation_zones),
        "observed_distinct_zones": validation_zone_count,
        "validation_zones": validation_labels.astype(int).tolist(),
        "status": (
            "PASS"
            if validation_zone_count >= args.minimum_validation_zones
            else "FAIL"
        ),
        "selection_scope": (
            "zone count and construction parameters are configuration inputs; "
            "outer holdout coordinates are used here only as an acceptance guard"
        ),
    }
    if validation_zone_count < args.minimum_validation_zones:
        raise RuntimeError(
            "Chronological location validation is geographically "
            "non-discriminating: "
            f"observed {validation_zone_count} distinct zone(s), required "
            f"{args.minimum_validation_zones}. Change the configured zone "
            "construction/count and rerun; do not report single-zone exact "
            "accuracy as localization discrimination."
        )
    events.to_csv(PROJECT / "05_ensemble/location_zone_event_catalog.csv", index=False)
    zones.to_csv(PROJECT / "05_ensemble/location_zones.csv", index=False)
    zone_grid = geographic_zone_grid(zone_model, zone_audit, args)
    zone_grid.to_csv(
        PROJECT / "05_ensemble/location_zone_decision_grid.csv",
        index=False,
    )
    write_json(PROJECT / "02_audit/location_zone_search.json", zone_audit)

    names = [column for column in location if column not in LOCATION_META]
    safe_payload = json.loads(
        (PROJECT / "01_inputs/v4_location_native_safe_features.json").read_text()
    )
    safe_names = safe_payload["features"]
    missing_location = [name for name in safe_names if name not in names]
    missing_timing = [name for name in safe_names if name not in timing]
    if missing_location or missing_timing:
        raise RuntimeError(
            f"Safe features missing: location={missing_location[:2]}, "
            f"timing={missing_timing[:2]}"
        )
    initial_features = [names.index(name) for name in safe_names]
    X = events[names].to_numpy(float)
    indirect_X = (
        indirect_events[names].to_numpy(float)
        if len(indirect_events)
        else None
    )
    latitude = events["latitude"].to_numpy(float)
    longitude = events["longitude"].to_numpy(float)
    inner_train = np.arange(inner_train_count)
    inner_validation = np.arange(inner_train_count, outer_train_count)
    outer_train = np.arange(outer_train_count)
    outer_validation = np.arange(outer_train_count, len(events))

    # ISO date strings compare chronologically and keep years before pandas'
    # nanosecond Timestamp lower bound (the deep-history master starts in 0684).
    timing_dates = timing["date"].astype(str).str.slice(0, 10)
    forecast_mask = timing_dates.ge(args.forecast_grid_start) & timing_dates.le(
        args.forecast_end
    )
    forecast_frame = timing.loc[forecast_mask].copy().reset_index(drop=True)
    forecast_frame["slot_start"] = forecast_frame["date"]
    forecast_X = forecast_frame[names].to_numpy(float)

    print("[location-v12] intelligent cluster-feature ablation", flush=True)
    selected_features = intelligent_ablation(
        X,
        labels,
        latitude,
        longitude,
        names,
        initial_features,
        inner_train,
        inner_validation,
        zones,
        args,
    )
    print("[location-v12] real-model baseline guard", flush=True)
    baseline_bank = fit_real_bank(
        X,
        labels,
        outer_train,
        outer_validation,
        forecast_X,
        indirect_X,
        initial_features,
        args,
        SEED + 10000,
    )
    candidate_bank = fit_real_bank(
        X,
        labels,
        outer_train,
        outer_validation,
        forecast_X,
        indirect_X,
        selected_features,
        args,
        SEED + 20000,
    )
    baseline_systems, baseline_ranking = evaluate_real_bank(
        baseline_bank,
        labels,
        latitude,
        longitude,
        outer_train,
        outer_validation,
        zones,
    )
    candidate_systems, candidate_ranking = evaluate_real_bank(
        candidate_bank,
        labels,
        latitude,
        longitude,
        outer_train,
        outer_validation,
        zones,
    )
    baseline_quality = float(
        np.median(baseline_ranking["origin_quality_25train_75validation"])
    )
    candidate_quality = float(
        np.median(candidate_ranking["origin_quality_25train_75validation"])
    )
    baseline_exact = float(np.median(baseline_ranking["validation_exact_zone"]))
    candidate_exact = float(np.median(candidate_ranking["validation_exact_zone"]))
    guard_pass = bool(
        candidate_quality >= baseline_quality - args.real_quality_tolerance
        and candidate_exact >= baseline_exact
    )
    bank = candidate_bank if guard_pass else baseline_bank
    systems = candidate_systems if guard_pass else baseline_systems
    ranking = candidate_ranking if guard_pass else baseline_ranking
    features = selected_features if guard_pass else initial_features
    guard = {
        "status": "PASS" if guard_pass else "ROLLBACK",
        "baseline_feature_count": len(initial_features),
        "candidate_feature_count": len(selected_features),
        "selected_feature_count": len(features),
        "baseline_median_quality": baseline_quality,
        "candidate_median_quality": candidate_quality,
        "baseline_median_exact_zone": baseline_exact,
        "candidate_median_exact_zone": candidate_exact,
    }
    write_json(
        PROJECT / "03_feature_research/location_zones/real_model_guard.json",
        guard,
    )

    ranking = ranking.sort_values(
        "origin_quality_25train_75validation", ascending=False
    ).reset_index(drop=True)
    ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
    ranking.to_csv(PROJECT / "05_ensemble/location_zone_system_ranking.csv", index=False)
    per_system_directory = PROJECT / "04_models/location_zones/system_predictions"
    per_system_directory.mkdir(parents=True, exist_ok=True)
    for system, payload in systems.items():
        validation_system = pd.DataFrame(
            payload["validation_probability"],
            columns=[f"zone_{zone}_probability" for zone in range(1, len(zones) + 1)],
        )
        validation_system.insert(0, "actual_zone", labels[outer_validation])
        validation_system.insert(
            0, "date", events.iloc[outer_validation]["date"].to_numpy()
        )
        validation_system.to_csv(
            per_system_directory / f"{system}_validation.csv", index=False
        )
    validation_probability, forecast_probability, fusion_audit = select_fusion(
        systems,
        ranking,
        labels,
        latitude,
        longitude,
        outer_validation,
        zones,
        labels[outer_train],
    )
    write_json(PROJECT / "05_ensemble/location_zone_fusion_gate.json", fusion_audit)
    pd.DataFrame(fusion_audit["trials"]).to_csv(
        PROJECT / "05_ensemble/location_zone_fusion_trials.csv", index=False
    )
    validation_metrics = zone_metrics(
        labels[outer_validation],
        validation_probability,
        latitude[outer_validation],
        longitude[outer_validation],
        zones,
    )
    predicted_validation = np.argmax(validation_probability, axis=1) + 1
    predicted_forecast = np.argmax(forecast_probability, axis=1) + 1
    validation_output = events.iloc[outer_validation][
        ["date", "slot_start", "event_time", "mag", "latitude", "longitude", "event_id", "zone"]
    ].reset_index(drop=True)
    validation_output = validation_output.rename(columns={"zone": "actual_zone"})
    validation_output["predicted_zone"] = predicted_validation
    validation_output["predicted_zone_confidence"] = np.max(
        validation_probability, axis=1
    )
    for zone in range(1, len(zones) + 1):
        validation_output[f"zone_{zone}_vote"] = validation_probability[:, zone - 1]
    validation_output.to_csv(
        PROJECT / "05_ensemble/location_zone_validation.csv", index=False
    )
    indirect_metrics = None
    if len(indirect_events):
        top = ranking.head(min(3, len(ranking))).copy()
        top_weights = np.maximum(
            top["origin_quality_25train_75validation"].to_numpy(float), 1e-6
        )
        top_weights /= top_weights.sum()
        indirect_probability = np.zeros((len(indirect_events), len(zones)), float)
        for system_weight, system in zip(top_weights, top["system"]):
            members = SYSTEMS[str(system)]
            system_probability = np.mean(
                np.stack([bank["outputs"]["indirect"][member] for member in members]),
                axis=0,
            )
            indirect_probability += system_weight * system_probability
        indirect_metrics = zone_metrics(
            indirect_labels,
            indirect_probability,
            indirect_events["latitude"].to_numpy(float),
            indirect_events["longitude"].to_numpy(float),
            zones,
        )
        indirect_output = indirect_events[
            ["date", "slot_start", "event_time", "mag", "latitude", "longitude", "event_id", "zone"]
        ].copy().rename(columns={"zone": "actual_zone"})
        indirect_output["predicted_zone"] = np.argmax(indirect_probability, axis=1) + 1
        indirect_output["predicted_zone_confidence"] = np.max(
            indirect_probability, axis=1
        )
        for zone in range(1, len(zones) + 1):
            indirect_output[f"zone_{zone}_vote"] = indirect_probability[:, zone - 1]
        indirect_output.to_csv(
            PROJECT / "05_ensemble/location_zone_indirect_validation.csv", index=False
        )
        write_json(
            PROJECT / "05_ensemble/location_zone_indirect_validation.json",
            {
                "status": "COMPLETE",
                "selection_independence": (
                    "lower-magnitude rows did not train models, select features, "
                    "choose zones, tune systems or choose fusion weights"
                ),
                "magnitude_range": [
                    args.indirect_validation_magnitude_threshold,
                    args.magnitude_threshold,
                ],
                "events": indirect_output.to_dict("records"),
                "metrics": indirect_metrics,
                "fusion": "quality-weighted top-three primary-validation systems",
            },
        )
    zone_lookup = zones.set_index("zone")
    forecast_output = pd.DataFrame(
        {
            "date": forecast_frame["date"],
            "slot_start": forecast_frame["date"],
            "slot_end_inclusive": (
                pd.to_datetime(forecast_frame["date"])
                + pd.Timedelta(days=args.interval_days - 1)
            ).dt.strftime("%Y-%m-%d"),
            "predicted_zone": predicted_forecast,
            "predicted_zone_confidence": np.max(forecast_probability, axis=1),
            "visible_window_starts": args.forecast_visible_start,
        }
    )
    forecast_output["zone_center_latitude"] = [
        zone_lookup.loc[zone, "center_latitude"] for zone in predicted_forecast
    ]
    forecast_output["zone_center_longitude"] = [
        zone_lookup.loc[zone, "center_longitude"] for zone in predicted_forecast
    ]
    for zone in range(1, len(zones) + 1):
        forecast_output[f"zone_{zone}_vote"] = forecast_probability[:, zone - 1]
    forecast_output.to_csv(
        PROJECT / "05_ensemble/location_zone_forecast.csv", index=False
    )

    lcs_models = bank["models"]["lcs"]
    rule_directory = PROJECT / "04_models/location_zones"
    rule_directory.mkdir(parents=True, exist_ok=True)
    for stale_rule in rule_directory.glob("lcs_zone_*_rules.json"):
        stale_rule.unlink()
    for zone_index, model in enumerate(lcs_models, 1):
        export_lcs_rules(
            model,
            [names[index] for index in features],
            rule_directory / f"lcs_zone_{zone_index}_rules.json",
            {
                "target": f"zone_{zone_index}_vs_rest",
                "zone_count": len(zones),
                "feature_count": len(features),
                "training_events": len(outer_train),
            },
        )
    summary = {
        "status": "COMPLETE",
        "run_parameters": vars(args),
        "base_model_configurations": {
            member: model_configuration(
                member,
                args.epochs_scale,
                len(features),
            )
            for member in BASES
        },
        "base_model_runtimes": bank["runtimes"],
        "preprocessing": bank["preprocessing"],
        "magnitude_threshold": args.magnitude_threshold,
        "training_magnitude_threshold": args.magnitude_threshold,
        "validation_magnitude_threshold": validation_floor,
        "deduplication": (
            f"largest magnitude event in each exact {args.interval_days}-day slot"
        ),
        "training_events": len(outer_train),
        "validation_events": events.iloc[outer_validation][
            ["event_time", "mag", "latitude", "longitude", "event_id", "zone"]
        ].to_dict("records"),
        "zone_construction_events": len(zone_construction),
        "zone_catalog": zone_catalog_audit,
        "predictive_master_zone_construction_events": len(
            predictive_zone_construction
        ),
        "zone_count": len(zones),
        "zone_decision_grid": {
            "rows": len(zone_grid),
            "resolution_degrees": 0.10,
            "complete_map_coverage": True,
            "semantics": (
                "each grid cell is assigned to exactly one GMM zone; rectangular "
                "envelopes are summaries and are not classification boundaries"
            ),
        },
        "zones": zones.to_dict("records"),
        "feature_guard": guard,
        "selected_features": {
            "count": len(features),
            "features": [names[index] for index in features],
        },
        "top_three_systems": ranking.head(3)[
            ["rank", "system", "origin_quality_25train_75validation"]
        ].to_dict("records"),
        "fusion_gate": fusion_audit,
        "validation_metrics": validation_metrics,
        "indirect_validation": (
            {
                "event_count": int(len(indirect_events)),
                "magnitude_floor": args.indirect_validation_magnitude_threshold,
                "metrics": indirect_metrics,
                "used_for_selection": False,
            }
            if len(indirect_events)
            else {"event_count": 0, "status": "DISABLED_OR_NO_ELIGIBLE_EVENTS"}
        ),
        "validation_design": {
            "mode": "one_shot",
            "incremental": False,
            "minimum_distinct_zones": int(args.minimum_validation_zones),
            "observed_distinct_zones": validation_zone_count,
            "zone_diversity_status": "PASS",
            "description": (
                "one feature set, one outer holdout and one fitted fusion are used "
                "for all configured location-validation events and forecast slots"
            ),
        },
        "forecast_window": {
            "visible_start": args.forecast_visible_start,
            "exact_grid_start": args.forecast_grid_start,
            "end": args.forecast_end,
        },
        "scientific_scope": (
            "retrospective research diagnostic; zones are data-derived geographic "
            "categories, not tectonic-plate truth or an operational warning"
        ),
        "elapsed_seconds": time.time() - started,
    }
    write_json(PROJECT / "05_ensemble/location_zone_summary.json", summary)
    print(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        flush=True,
    )


if __name__ == "__main__":
    main()

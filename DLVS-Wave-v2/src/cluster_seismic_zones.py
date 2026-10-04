#!/usr/bin/env python3
"""Learn auditable south-to-north Japanese seismic zones and build a zone target.

The command accepts geographic and temporal bounds, searches between two and
five Gaussian-mixture cluster systems, keeps the final chronological events out
of zone construction, and exports a geographic decision map.  When a weekly
feature master is supplied it also creates an event-conditioned master whose
sole seismic target is ``seis_core_zone``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture


LOGGER = logging.getLogger("dlvs_wave.zone_clusters")
SEED = 842024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find 2–5 Japanese seismic clusters and optionally build a weekly zone-target master",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--event-catalog", required=True)
    parser.add_argument("--feature-master")
    parser.add_argument("--recent-master-events", help="Optional weekly master used only to append newer pre-cutoff events")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--time-min", default="1900-01-01")
    parser.add_argument("--time-max", default="2026-07-31")
    parser.add_argument("--latitude-min", type=float, default=24.0)
    parser.add_argument("--latitude-max", type=float, default=46.5)
    parser.add_argument("--longitude-min", type=float, default=122.0)
    parser.add_argument("--longitude-max", type=float, default=150.5)
    parser.add_argument("--magnitude-min", type=float, default=6.9)
    parser.add_argument("--minimum-zones", type=int, default=2)
    parser.add_argument("--maximum-zones", type=int, default=5)
    parser.add_argument("--minimum-zone-events", type=int, default=12)
    parser.add_argument("--validation-events", type=int, default=24)
    parser.add_argument("--bootstrap-repeats", type=int, default=10)
    parser.add_argument("--grid-resolution-degrees", type=float, default=0.10)
    parser.add_argument("--forecast-start", default="2026-08-03")
    parser.add_argument("--forecast-end", default="2026-10-26")
    parser.add_argument("--seed", type=int, default=SEED)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(payload: Any, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_args(args: argparse.Namespace) -> None:
    if not 2 <= args.minimum_zones <= args.maximum_zones <= 5:
        raise ValueError("Zone search must satisfy 2 <= minimum <= maximum <= 5")
    if args.minimum_zone_events < 3:
        raise ValueError("--minimum-zone-events must be at least 3")
    if args.validation_events < 5:
        raise ValueError("At least five untouched validation events are required")
    if args.bootstrap_repeats < 3:
        raise ValueError("At least three bootstrap repetitions are required")
    if not (args.latitude_min < args.latitude_max and args.longitude_min < args.longitude_max):
        raise ValueError("Invalid geographic bounds")
    if pd.Timestamp(args.time_min) > pd.Timestamp(args.time_max):
        raise ValueError("--time-min occurs after --time-max")
    if pd.Timestamp(args.forecast_start) > pd.Timestamp(args.forecast_end):
        raise ValueError("--forecast-start occurs after --forecast-end")


def _catalog_columns(frame: pd.DataFrame) -> dict[str, str]:
    choices = {
        "event_time": ("time", "event_time", "datetime", "date"),
        "magnitude": ("mag", "magnitude", "seis_core_magnitude"),
        "latitude": ("latitude", "lat", "seis_core_latitude"),
        "longitude": ("longitude", "lon", "seis_core_longitude"),
        "depth": ("depth", "seis_core_depth"),
        "event_id": ("id", "event_id", "seis_core_id"),
        "place": ("place", "location"),
    }
    resolved: dict[str, str] = {}
    for semantic, candidates in choices.items():
        match = next((column for column in candidates if column in frame.columns), None)
        if match is not None:
            resolved[semantic] = match
    required = {"event_time", "magnitude", "latitude", "longitude"}
    missing = sorted(required.difference(resolved))
    if missing:
        raise ValueError(f"Event catalog lacks semantic columns: {missing}")
    return resolved


def _normalise_catalog(path: Path, source: str) -> pd.DataFrame:
    raw = pd.read_csv(path, low_memory=False)
    columns = _catalog_columns(raw)
    output = pd.DataFrame(
        {
            "event_time": pd.to_datetime(raw[columns["event_time"]], utc=True, errors="coerce"),
            "magnitude": pd.to_numeric(raw[columns["magnitude"]], errors="coerce"),
            "latitude": pd.to_numeric(raw[columns["latitude"]], errors="coerce"),
            "longitude": pd.to_numeric(raw[columns["longitude"]], errors="coerce"),
            "depth": (
                pd.to_numeric(raw[columns["depth"]], errors="coerce")
                if "depth" in columns
                else np.nan
            ),
            "event_id": (
                raw[columns["event_id"]].fillna("").astype(str)
                if "event_id" in columns
                else [f"{source}_{index:06d}" for index in range(len(raw))]
            ),
            "place": (
                raw[columns["place"]].fillna("").astype(str)
                if "place" in columns
                else ""
            ),
            "source": source,
        }
    )
    return output


def load_events(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    catalog_path = Path(args.event_catalog).expanduser().resolve()
    if not catalog_path.is_file():
        raise FileNotFoundError(catalog_path)
    frames = [_normalise_catalog(catalog_path, "catalog")]
    source_manifest = {"event_catalog": {"path": str(catalog_path), "sha256": _sha256(catalog_path)}}
    if args.recent_master_events:
        recent_path = Path(args.recent_master_events).expanduser().resolve()
        if not recent_path.is_file():
            raise FileNotFoundError(recent_path)
        frames.append(_normalise_catalog(recent_path, "recent_master"))
        source_manifest["recent_master_events"] = {
            "path": str(recent_path),
            "sha256": _sha256(recent_path),
        }
    events = pd.concat(frames, ignore_index=True)
    start = pd.Timestamp(args.time_min, tz="UTC")
    end = pd.Timestamp(args.time_max, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    events = events.loc[
        events["event_time"].between(start, end)
        & events["magnitude"].ge(args.magnitude_min)
        & events["latitude"].between(args.latitude_min, args.latitude_max)
        & events["longitude"].between(args.longitude_min, args.longitude_max)
    ].dropna(subset=["event_time", "magnitude", "latitude", "longitude"]).copy()
    if len(events) <= args.validation_events + args.maximum_zones * args.minimum_zone_events:
        raise RuntimeError("Too few events for the requested holdout and minimum zone sizes")
    source_priority = events["source"].map({"catalog": 0, "recent_master": 1}).fillna(2)
    events["source_priority"] = source_priority
    # The predictive master is weekly.  Collapse catalog and recent-master
    # supplements onto the same Monday-starting slot before any clustering so
    # the same earthquake cannot be counted twice at different timestamp
    # resolutions and multiple events cannot leak through one seven-day row.
    events["event_week"] = (
        events["event_time"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    )
    events.sort_values(
        ["event_week", "magnitude", "source_priority", "event_time"],
        ascending=[True, False, True, True],
        inplace=True,
    )
    events.drop_duplicates("event_week", keep="first", inplace=True)
    events.sort_values("event_time", inplace=True)
    events.reset_index(drop=True, inplace=True)
    return events, source_manifest


def geographic_embedding(
    latitude: np.ndarray,
    longitude: np.ndarray,
    reference_latitude: float,
    reference_longitude: float,
) -> np.ndarray:
    latitude = np.asarray(latitude, dtype=float)
    longitude = np.asarray(longitude, dtype=float)
    north = (latitude - reference_latitude) * 111.2
    east = (longitude - reference_longitude) * 111.2 * math.cos(math.radians(reference_latitude))
    return np.column_stack((east, north))


def _bootstrap_stability(
    coordinates: np.ndarray,
    labels: np.ndarray,
    zones: int,
    repeats: int,
    seed: int,
) -> float:
    generator = np.random.default_rng(seed)
    scores: list[float] = []
    for repeat in range(repeats):
        sample = generator.integers(0, len(coordinates), size=len(coordinates))
        try:
            bootstrap = GaussianMixture(
                n_components=zones,
                covariance_type="full",
                reg_covar=1e-3,
                n_init=4,
                max_iter=400,
                random_state=seed + repeat + 1,
            ).fit(coordinates[sample])
            scores.append(float(adjusted_rand_score(labels, bootstrap.predict(coordinates))))
        except Exception:
            scores.append(0.0)
    return float(np.median(scores))


def fit_zone_system(
    events: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[GaussianMixture, dict[str, Any], pd.DataFrame, pd.DataFrame]:
    events = events.sort_values("event_time").reset_index(drop=True).copy()
    events["split_role"] = "cluster_fit"
    events.loc[events.index[-args.validation_events :], "split_role"] = "model_validation"
    construction = events.loc[events["split_role"].eq("cluster_fit")].copy()
    reference_latitude = (args.latitude_min + args.latitude_max) / 2.0
    reference_longitude = (args.longitude_min + args.longitude_max) / 2.0
    coordinates = geographic_embedding(
        construction["latitude"].to_numpy(),
        construction["longitude"].to_numpy(),
        reference_latitude,
        reference_longitude,
    )
    trials: list[dict[str, Any]] = []
    fitted: dict[int, tuple[GaussianMixture, np.ndarray]] = {}
    for zones in range(args.minimum_zones, args.maximum_zones + 1):
        model = GaussianMixture(
            n_components=zones,
            covariance_type="full",
            reg_covar=1e-3,
            n_init=16,
            max_iter=600,
            random_state=args.seed + zones,
        ).fit(coordinates)
        labels = model.predict(coordinates)
        counts = np.bincount(labels, minlength=zones)
        valid = bool(counts.min() >= args.minimum_zone_events)
        silhouette = float(silhouette_score(coordinates, labels)) if valid else -1.0
        stability = (
            _bootstrap_stability(
                coordinates,
                labels,
                zones,
                args.bootstrap_repeats,
                args.seed + zones * 100,
            )
            if valid
            else 0.0
        )
        proportions = counts / max(1, counts.sum())
        balance = float(-np.sum(proportions * np.log(np.maximum(proportions, 1e-12))) / np.log(zones))
        trials.append(
            {
                "zones": zones,
                "bic": float(model.bic(coordinates)),
                "silhouette": silhouette,
                "bootstrap_adjusted_rand_stability": stability,
                "cluster_balance_entropy": balance,
                "minimum_cluster_events": int(counts.min()),
                "valid_minimum_size": valid,
            }
        )
        fitted[zones] = (model, labels)
    valid_trials = [trial for trial in trials if trial["valid_minimum_size"]]
    if not valid_trials:
        raise RuntimeError("No candidate zone count satisfies --minimum-zone-events")
    bic = np.asarray([trial["bic"] for trial in valid_trials], dtype=float)
    bic_skill = np.ones(len(bic)) if np.ptp(bic) <= 1e-12 else (bic.max() - bic) / np.ptp(bic)
    for trial, skill in zip(valid_trials, bic_skill):
        trial["bic_skill"] = float(skill)
        trial["selection_quality"] = float(
            0.45 * np.clip((trial["silhouette"] + 1.0) / 2.0, 0.0, 1.0)
            + 0.25 * skill
            + 0.20 * np.clip(trial["bootstrap_adjusted_rand_stability"], 0.0, 1.0)
            + 0.10 * trial["cluster_balance_entropy"]
        )
    selected = max(valid_trials, key=lambda row: (row["selection_quality"], row["silhouette"]))
    model, construction_labels = fitted[int(selected["zones"])]
    component_latitudes = []
    for component in range(int(selected["zones"])):
        members = construction.loc[construction_labels == component]
        component_latitudes.append((component, float(members["latitude"].mean())))
    ordered_components = [component for component, _ in sorted(component_latitudes, key=lambda item: item[1])]
    component_to_zone = {int(component): index + 1 for index, component in enumerate(ordered_components)}
    all_coordinates = geographic_embedding(
        events["latitude"].to_numpy(),
        events["longitude"].to_numpy(),
        reference_latitude,
        reference_longitude,
    )
    events["zone"] = [component_to_zone[int(component)] for component in model.predict(all_coordinates)]
    zone_rows: list[dict[str, Any]] = []
    for zone in range(1, int(selected["zones"]) + 1):
        fit_members = events.loc[events["split_role"].eq("cluster_fit") & events["zone"].eq(zone)]
        all_members = events.loc[events["zone"].eq(zone)]
        zone_rows.append(
            {
                "zone": zone,
                "zone_name": f"zone_{zone}_south_to_north",
                "construction_events": len(fit_members),
                "all_events": len(all_members),
                "validation_events": int(all_members["split_role"].eq("model_validation").sum()),
                "center_latitude": float(fit_members["latitude"].mean()),
                "center_longitude": float(fit_members["longitude"].mean()),
                "latitude_q05": float(fit_members["latitude"].quantile(0.05)),
                "latitude_q95": float(fit_members["latitude"].quantile(0.95)),
                "longitude_q05": float(fit_members["longitude"].quantile(0.05)),
                "longitude_q95": float(fit_members["longitude"].quantile(0.95)),
            }
        )
    definitions = pd.DataFrame(zone_rows).sort_values("zone").reset_index(drop=True)
    if not definitions["center_latitude"].is_monotonic_increasing:
        raise AssertionError("Zone numbering is not monotonic south-to-north")
    audit = {
        "selection_rule": (
            "45% silhouette separation + 25% relative BIC skill + 20% bootstrap ARI stability "
            "+ 10% cluster-balance entropy; minimum event count is mandatory"
        ),
        "selected_zone_count": int(selected["zones"]),
        "selected_trial": selected,
        "trials": trials,
        "construction_events": len(construction),
        "untouched_model_validation_events": args.validation_events,
        "construction_end": construction["event_time"].max().isoformat(),
        "model_validation_start": events.loc[events["split_role"].eq("model_validation"), "event_time"].min().isoformat(),
        "component_to_south_north_zone": component_to_zone,
        "embedding_reference": {"latitude": reference_latitude, "longitude": reference_longitude},
    }
    return model, audit, definitions, events


def build_decision_grid(
    model: GaussianMixture,
    audit: dict[str, Any],
    args: argparse.Namespace,
) -> pd.DataFrame:
    step = args.grid_resolution_degrees
    latitudes = np.arange(args.latitude_min, args.latitude_max + step / 2.0, step)
    longitudes = np.arange(args.longitude_min, args.longitude_max + step / 2.0, step)
    longitude_mesh, latitude_mesh = np.meshgrid(longitudes, latitudes)
    reference = audit["embedding_reference"]
    components = model.predict(
        geographic_embedding(
            latitude_mesh.ravel(),
            longitude_mesh.ravel(),
            float(reference["latitude"]),
            float(reference["longitude"]),
        )
    )
    mapping = {int(key): int(value) for key, value in audit["component_to_south_north_zone"].items()}
    zones = np.asarray([mapping[int(component)] for component in components], dtype=int)
    return pd.DataFrame(
        {"latitude": latitude_mesh.ravel(), "longitude": longitude_mesh.ravel(), "zone": zones}
    )


def plot_zone_map(
    grid: pd.DataFrame,
    definitions: pd.DataFrame,
    events: pd.DataFrame,
    output_path: Path,
    args: argparse.Namespace,
    title: str = "Japan M6.9+ seismic zones learned before the forecast cutoff",
    zone_probabilities: dict[int, float] | None = None,
) -> None:
    from mpl_toolkits.basemap import Basemap

    zone_count = len(definitions)
    base_colors = list(plt.get_cmap("viridis", zone_count).colors)
    if zone_probabilities:
        colors = []
        for zone, color in enumerate(base_colors, start=1):
            probability = float(zone_probabilities.get(zone, 0.0))
            blend = 0.78 - 0.62 * probability
            colors.append(tuple((1.0 - blend) * channel + blend for channel in color))
    else:
        colors = base_colors
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(0.5, zone_count + 1.5), zone_count)
    latitudes = np.sort(grid["latitude"].unique())
    longitudes = np.sort(grid["longitude"].unique())
    zone_mesh = grid.pivot(index="latitude", columns="longitude", values="zone").loc[latitudes, longitudes]
    figure, axis = plt.subplots(figsize=(10.8, 9.4), constrained_layout=True)
    mapping = Basemap(
        projection="cyl",
        llcrnrlat=args.latitude_min,
        urcrnrlat=args.latitude_max,
        llcrnrlon=args.longitude_min,
        urcrnrlon=args.longitude_max,
        resolution="i",
        ax=axis,
    )
    longitude_mesh, latitude_mesh = np.meshgrid(longitudes, latitudes)
    mapping.pcolormesh(longitude_mesh, latitude_mesh, zone_mesh.to_numpy(), cmap=cmap, norm=norm, latlon=True, alpha=0.72)
    mapping.drawcoastlines(linewidth=0.8, color="#263238")
    mapping.drawcountries(linewidth=0.55, color="#455a64")
    mapping.drawparallels(np.arange(24, 47, 2), labels=[1, 0, 0, 0], fontsize=8, linewidth=0.25, color="#607d8b")
    mapping.drawmeridians(np.arange(122, 151, 3), labels=[0, 0, 0, 1], fontsize=8, linewidth=0.25, color="#607d8b")
    for role, marker, size, label in (
        ("cluster_fit", "o", 22, "cluster-construction events"),
        ("model_validation", "^", 44, "untouched validation events"),
    ):
        subset = events.loc[events["split_role"].eq(role)]
        mapping.scatter(
            subset["longitude"], subset["latitude"], latlon=True,
            c=subset["zone"], cmap=cmap, norm=norm, marker=marker,
            s=size, edgecolors="black", linewidths=0.35, alpha=0.82, label=label,
        )
    for row in definitions.itertuples():
        probability_text = ""
        if zone_probabilities:
            probability_text = f"\nP={zone_probabilities.get(int(row.zone), 0.0):.1%}"
        axis.text(
            row.center_longitude,
            row.center_latitude,
            f"Z{int(row.zone)}{probability_text}",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "alpha": 0.82, "edgecolor": "#263238"},
            zorder=8,
        )
    axis.set_title(title, fontsize=13, fontweight="bold", pad=14)
    axis.legend(loc="lower left", framealpha=0.92, fontsize=8)
    colorbar = figure.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axis, orientation="vertical", fraction=0.036, pad=0.035,
        ticks=np.arange(1, zone_count + 1),
    )
    colorbar.set_label("Zone index (south → north)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


def _assign_weekly_slots(events: pd.DataFrame, master_dates: pd.Series) -> pd.DataFrame:
    ordered = pd.Series(pd.to_datetime(master_dates)).sort_values().drop_duplicates().reset_index(drop=True)
    origin = ordered.iloc[0]
    event_naive = events["event_time"].dt.tz_convert("UTC").dt.tz_localize(None)
    steps = np.floor((event_naive - origin).dt.total_seconds() / (7 * 86400)).astype(int)
    assigned = events.copy()
    assigned["date"] = origin + pd.to_timedelta(steps * 7, unit="D")
    allowed = set(ordered)
    assigned = assigned.loc[assigned["date"].isin(allowed)].copy()
    assigned.sort_values(
        ["date", "magnitude", "source_priority"],
        ascending=[True, False, True],
        inplace=True,
    )
    assigned.drop_duplicates("date", keep="first", inplace=True)
    return assigned.sort_values("date").reset_index(drop=True)


def build_zone_target_master(
    events: pd.DataFrame,
    feature_master_path: Path,
    output_path: Path,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    feature_master = pd.read_csv(feature_master_path, low_memory=False)
    date_column = "date" if "date" in feature_master.columns else feature_master.columns[0]
    feature_master[date_column] = pd.to_datetime(feature_master[date_column], errors="coerce")
    feature_master.dropna(subset=[date_column], inplace=True)
    feature_master.sort_values(date_column, inplace=True)
    feature_master.drop_duplicates(date_column, keep="first", inplace=True)
    weekly_events = _assign_weekly_slots(events, feature_master[date_column])
    cutoff = pd.Timestamp(args.time_max)
    forecast_start = pd.Timestamp(args.forecast_start)
    forecast_end = pd.Timestamp(args.forecast_end)
    seismic_columns = [column for column in feature_master.columns if column.startswith("seis_")]
    numeric_features = [
        column
        for column in feature_master.columns
        if column not in seismic_columns
        and column != date_column
        and pd.api.types.is_numeric_dtype(feature_master[column])
        and pd.to_numeric(feature_master[column], errors="coerce").notna().all()
        and float(pd.to_numeric(feature_master[column], errors="coerce").std(ddof=0)) > 1e-12
    ]
    if len(numeric_features) < 5:
        raise RuntimeError("Feature master exposes fewer than five finite non-constant non-seismic features")
    indexed_features = feature_master.set_index(date_column)
    historical_rows: list[dict[str, Any]] = []
    for event in weekly_events.loc[weekly_events["date"].le(cutoff)].itertuples():
        feature_row = indexed_features.loc[pd.Timestamp(event.date), numeric_features]
        row = {
            "date": pd.Timestamp(event.date),
            "seis_core_zone": int(event.zone),
            "event_magnitude": float(event.magnitude),
            "event_latitude": float(event.latitude),
            "event_longitude": float(event.longitude),
            "event_id": str(event.event_id),
            "split_role": str(event.split_role),
            "is_forecast": 0,
        }
        row.update(feature_row.to_dict())
        historical_rows.append(row)
    future_rows: list[dict[str, Any]] = []
    future = feature_master.loc[feature_master[date_column].between(forecast_start, forecast_end)]
    for source in future.itertuples(index=False):
        source_dict = dict(zip(future.columns, source))
        row = {
            "date": pd.Timestamp(source_dict[date_column]),
            "seis_core_zone": 0,
            "event_magnitude": np.nan,
            "event_latitude": np.nan,
            "event_longitude": np.nan,
            "event_id": "",
            "split_role": "forecast",
            "is_forecast": 1,
        }
        row.update({column: source_dict[column] for column in numeric_features})
        future_rows.append(row)
    target_master = pd.DataFrame(historical_rows + future_rows).sort_values("date").reset_index(drop=True)
    if len(historical_rows) == 0 or len(future_rows) == 0:
        raise RuntimeError("Event-conditioned target master lacks historical or forecast rows")
    target_master["date"] = pd.to_datetime(target_master["date"]).dt.strftime("%Y-%m-%d")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_master.to_csv(output_path, index=False)
    manifest = {
        "feature_master": {"path": str(feature_master_path), "sha256": _sha256(feature_master_path)},
        "output_master": str(output_path),
        "historical_event_rows": len(historical_rows),
        "cluster_construction_rows": int((target_master["split_role"] == "cluster_fit").sum()),
        "untouched_validation_rows": int((target_master["split_role"] == "model_validation").sum()),
        "forecast_rows": len(future_rows),
        "forecast_range": [args.forecast_start, args.forecast_end],
        "target": "seis_core_zone",
        "predictive_feature_count": len(numeric_features),
        "predictive_features": numeric_features,
        "excluded_seismic_columns": seismic_columns,
        "conditioning": "location conditional on an M6.9+ event; not an occurrence model",
    }
    return target_master, manifest


def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    events, sources = load_events(args)
    model, audit, definitions, assigned_events = fit_zone_system(events, args)
    grid = build_decision_grid(model, audit, args)
    definitions.to_csv(output_dir / "zone_definitions.csv", index=False)
    assigned_events.assign(event_time=assigned_events["event_time"].astype(str)).to_csv(
        output_dir / "zone_event_assignments.csv", index=False
    )
    pd.DataFrame(audit["trials"]).to_csv(output_dir / "zone_selection_trials.csv", index=False)
    grid.to_csv(output_dir / "zone_decision_grid.csv", index=False)
    _atomic_json({**audit, "sources": sources}, output_dir / "zone_clustering_audit.json")
    _atomic_json(definitions.to_dict(orient="records"), output_dir / "zone_definitions.json")
    for suffix in ("png", "pdf"):
        plot_zone_map(grid, definitions, assigned_events, output_dir / f"zone_map.{suffix}", args)
    master_manifest = None
    master_path = None
    if args.feature_master:
        feature_master_path = Path(args.feature_master).expanduser().resolve()
        master_path = output_dir.parent / "02_master" / "zone_target_master.csv"
        _, master_manifest = build_zone_target_master(
            assigned_events, feature_master_path, master_path, args
        )
        _atomic_json(master_manifest, master_path.with_name("zone_target_master_manifest.json"))
    readme = f"""# Geographic seismic-zone construction

- Time window: `{args.time_min}` through `{args.time_max}` (inclusive).
- Magnitude filter: `M >= {args.magnitude_min}`.
- Bounds: `{args.latitude_min}..{args.latitude_max} N`, `{args.longitude_min}..{args.longitude_max} E`.
- Search: `{args.minimum_zones}..{args.maximum_zones}` zones; selected: **{audit['selected_zone_count']}**.
- Construction events: `{audit['construction_events']}`.
- Untouched model-validation events: `{audit['untouched_model_validation_events']}`.
- Numbering: **zone 1 south → zone {audit['selected_zone_count']} north**.

The cluster boundaries use no event from the model-validation tail. The map is
a broad research partition, not a fault-level localization or a hazard map.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    result = {
        "output_dir": str(output_dir),
        "selected_zone_count": audit["selected_zone_count"],
        "construction_events": audit["construction_events"],
        "validation_events": audit["untouched_model_validation_events"],
        "master_path": str(master_path) if master_path else None,
        "master_manifest": master_manifest,
    }
    _atomic_json(result, output_dir / "completion.json")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = run(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

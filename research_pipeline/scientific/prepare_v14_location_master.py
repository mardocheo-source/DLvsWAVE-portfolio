#!/usr/bin/env python3
"""Build the V14 conditional-localization master from audited real coordinates."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


LOCATION_META = [
    "date",
    "event_time",
    "slot_start",
    "mag",
    "depth",
    "latitude",
    "longitude",
    "event_id",
    "is_forecast",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--catalog-csv", type=Path, required=True)
    value.add_argument(
        "--supplemental-catalog-csv",
        type=Path,
        default=None,
        help=(
            "Optional USGS-format regional catalogue used to add lower-magnitude "
            "events for indirect location validation."
        ),
    )
    value.add_argument("--supplemental-minimum-magnitude", type=float, default=0.0)
    value.add_argument(
        "--catalog-outside-master-policy",
        choices=("error", "drop"),
        default="error",
        help=(
            "How to handle catalogue events that have no audited timing slot. "
            "'drop' excludes and records them; 'error' preserves the strict "
            "legacy behaviour."
        ),
    )
    value.add_argument("--anchor-date", default="2026-01-01")
    value.add_argument("--interval-days", type=int, default=180)
    value.add_argument("--full-timing-master", type=Path, required=True)
    value.add_argument("--compact-timing-master", type=Path, required=True)
    value.add_argument("--timing-safe-features", type=Path, required=True)
    value.add_argument("--bin-membership-csv", type=Path, required=True)
    value.add_argument("--output-master", type=Path, required=True)
    value.add_argument("--output-safe-features", type=Path, required=True)
    value.add_argument("--output-audit-json", type=Path, required=True)
    value.add_argument("--forecast-start", default="2026-01-01")
    value.add_argument("--forecast-end", default="2028-12-31")
    value.add_argument("--map-latitude-min", type=float, default=28.0)
    value.add_argument("--map-latitude-max", type=float, default=47.0)
    value.add_argument("--map-longitude-min", type=float, default=128.0)
    value.add_argument("--map-longitude-max", type=float, default=149.5)
    return value


def event_to_slot(bin_membership: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in bin_membership.itertuples(index=False):
        identifiers = str(row.event_ids).split(";")
        for identifier in identifiers:
            if identifier in mapping:
                raise RuntimeError(f"Event assigned to multiple bins: {identifier}")
            mapping[identifier] = str(row.slot_start)
    return mapping


def main() -> None:
    args = parser().parse_args()
    catalog = pd.read_csv(args.catalog_csv, low_memory=False)
    full = pd.read_csv(args.full_timing_master, low_memory=False)
    compact = pd.read_csv(args.compact_timing_master, low_memory=False)
    membership = pd.read_csv(args.bin_membership_csv, low_memory=False)
    safe_payload = json.loads(args.timing_safe_features.read_text(encoding="utf-8"))
    features = list(safe_payload["features"])

    missing_full = [name for name in features if name not in full]
    missing_compact = [name for name in features if name not in compact]
    if missing_full or missing_compact:
        raise RuntimeError(
            f"Missing features: full={missing_full[:3]}, compact={missing_compact[:3]}"
        )
    slot_by_event = event_to_slot(membership)
    missing_slots = sorted(set(catalog["event_id"]) - set(slot_by_event))
    if missing_slots:
        if args.catalog_outside_master_policy == "error":
            raise RuntimeError(f"Catalog events missing from bin audit: {missing_slots}")
        outside_master = catalog.loc[
            catalog["event_id"].astype(str).isin(missing_slots)
        ].copy()
        catalog = catalog.loc[
            ~catalog["event_id"].astype(str).isin(missing_slots)
        ].copy()
    else:
        outside_master = catalog.iloc[0:0].copy()

    supplemental_rows = 0
    if args.supplemental_catalog_csv is not None:
        supplemental = pd.read_csv(args.supplemental_catalog_csv, low_memory=False)
        required = {"id", "time", "mag", "depth", "latitude", "longitude"}
        missing = sorted(required.difference(supplemental.columns))
        if missing:
            raise ValueError(f"Supplemental location catalogue is missing: {missing}")
        supplemental = supplemental.loc[
            pd.to_numeric(supplemental["mag"], errors="coerce").ge(
                args.supplemental_minimum_magnitude
            )
        ].copy()
        supplemental["event_id"] = supplemental["id"].astype(str)
        supplemental["date"] = supplemental["time"].astype(str).str.slice(0, 10)
        supplemental["source"] = "USGS_FDSN_SUPPLEMENTAL_LOCATION"
        anchor_day = date.fromisoformat(args.anchor_date)
        for event_id, event_day_text in supplemental[["event_id", "date"]].itertuples(
            index=False, name=None
        ):
            event_day = date.fromisoformat(str(event_day_text))
            offset = (event_day - anchor_day).days // args.interval_days
            slot_by_event[str(event_id)] = (
                anchor_day + timedelta(days=offset * args.interval_days)
            ).isoformat()
        aligned_columns = list(catalog.columns)
        for column in aligned_columns:
            if column not in supplemental:
                supplemental[column] = np.nan
        supplemental = supplemental[aligned_columns]
        supplemental_rows = len(supplemental)
        catalog = (
            pd.concat([catalog, supplemental], ignore_index=True)
            .sort_values(["date", "mag"], ascending=[True, False])
            .drop_duplicates("event_id", keep="first")
            .reset_index(drop=True)
        )

    catalog = catalog.copy()
    catalog["latitude"] = pd.to_numeric(catalog["latitude"], errors="coerce")
    catalog["longitude"] = pd.to_numeric(catalog["longitude"], errors="coerce")
    catalog["mag"] = pd.to_numeric(catalog["mag"], errors="coerce")
    catalog["depth"] = pd.to_numeric(catalog["depth"], errors="coerce")
    finite_coordinates = np.isfinite(catalog["latitude"]) & np.isfinite(
        catalog["longitude"]
    )
    inside_bounds = (
        catalog["latitude"].between(args.map_latitude_min, args.map_latitude_max)
        & catalog["longitude"].between(
            args.map_longitude_min, args.map_longitude_max
        )
    )
    eligible = finite_coordinates & inside_bounds & np.isfinite(catalog["mag"])
    geolocated_all = catalog.loc[eligible].copy()
    excluded = catalog.loc[~eligible].copy()
    # Fixed-width ISO days preserve chronological ordering for ancient years
    # outside pandas' nanosecond Timestamp range.
    event_days = geolocated_all["date"].astype(str).str.slice(0, 10)
    forward_mask = event_days.ge(args.forecast_start)
    withheld_forward = geolocated_all.loc[forward_mask].copy()
    geolocated = geolocated_all.loc[~forward_mask].copy()
    if geolocated.empty:
        raise RuntimeError(
            "No geolocated training event remains before the forecast start"
        )
    geolocated["slot_start"] = geolocated["event_id"].map(slot_by_event)

    full_by_date = full.set_index("date", drop=False)
    event_rows: list[dict[str, object]] = []
    for event in geolocated.itertuples(index=False):
        if event.slot_start not in full_by_date.index:
            raise RuntimeError(f"Slot missing from full master: {event.slot_start}")
        source = full_by_date.loc[event.slot_start]
        if isinstance(source, pd.DataFrame):
            raise RuntimeError(f"Duplicate full-master slot: {event.slot_start}")
        row: dict[str, object] = {
            "date": str(event.date),
            "event_time": str(event.time),
            "slot_start": str(event.slot_start),
            "mag": float(event.mag),
            "depth": float(event.depth) if np.isfinite(event.depth) else np.nan,
            "latitude": float(event.latitude),
            "longitude": float(event.longitude),
            "event_id": str(event.event_id),
            "is_forecast": 0,
        }
        row.update({name: float(source[name]) for name in features})
        event_rows.append(row)

    compact_dates = compact["date"].astype(str).str.slice(0, 10)
    forecast = compact.loc[
        compact["is_forecast"].eq(1)
        & compact_dates.ge(args.forecast_start)
        & compact_dates.le(args.forecast_end)
    ].copy()
    forecast_rows: list[dict[str, object]] = []
    for _, source in forecast.iterrows():
        row = {
            "date": str(source["date"]),
            "event_time": "",
            "slot_start": str(source["date"]),
            "mag": np.nan,
            "depth": np.nan,
            "latitude": np.nan,
            "longitude": np.nan,
            "event_id": "",
            "is_forecast": 1,
        }
        row.update({name: float(source[name]) for name in features})
        forecast_rows.append(row)

    output = pd.DataFrame(event_rows + forecast_rows, columns=LOCATION_META + features)
    numeric = output[features].to_numpy(float)
    if not np.isfinite(numeric).all():
        raise RuntimeError("Location predictor matrix contains non-finite values")
    args.output_master.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_master, index=False)

    slot_counts = (
        geolocated.groupby("slot_start", as_index=False)
        .agg(event_count=("event_id", "size"), maximum_magnitude=("mag", "max"))
        .sort_values("slot_start")
    )
    duplicate_slots = slot_counts.loc[slot_counts["event_count"].gt(1)]
    safe_location = {
        "domain": "conditional_localization",
        "feature_count": len(features),
        "features": features,
        "shared_with_timing_master": True,
        "coordinate_policy": (
            "only finite observed catalog coordinates inside the configured Japan "
            "bounds are used; missing historical coordinates are never imputed"
        ),
        "source_timing_safe_features": str(args.timing_safe_features.resolve()),
        "source_timing_safe_features_sha256": sha256(args.timing_safe_features),
    }
    write_json(args.output_safe_features, safe_location)
    audit = {
        "status": "COMPLETE",
        "catalog_rows": len(catalog),
        "catalog_outside_master_policy": args.catalog_outside_master_policy,
        "catalog_outside_master_rows": len(outside_master),
        "catalog_outside_master_events": outside_master[
            ["date", "event_id", "source", "mag", "latitude", "longitude"]
        ].to_dict("records"),
        "supplemental_catalog_rows": supplemental_rows,
        "supplemental_minimum_magnitude": args.supplemental_minimum_magnitude,
        "geolocated_event_rows": len(geolocated),
        "withheld_forward_event_rows": len(withheld_forward),
        "withheld_forward_events": withheld_forward[
            ["date", "event_id", "mag", "latitude", "longitude"]
        ].to_dict("records"),
        "forecast_training_cutoff_exclusive": str(args.forecast_start),
        "forward_events_never_used_as_location_training_targets": True,
        "excluded_event_rows": len(excluded),
        "excluded_events": excluded[
            ["date", "event_id", "source", "latitude", "longitude"]
        ].to_dict("records"),
        "geolocated_distinct_slots": int(geolocated["slot_start"].nunique()),
        "duplicate_geolocated_slots": duplicate_slots.to_dict("records"),
        "deduplication_contract": (
            "the modeling stage keeps the largest-magnitude event in each exact "
            "configured timing slot; tied magnitudes are ordered by event time"
        ),
        "forecast_rows": len(forecast),
        "feature_count": len(features),
        "output_rows": len(output),
        "output_master_sha256": sha256(args.output_master),
        "coordinate_bounds": {
            "latitude": [args.map_latitude_min, args.map_latitude_max],
            "longitude": [args.map_longitude_min, args.map_longitude_max],
        },
        "scientific_scope": (
            "localization is conditional on an event occurring in a timing bin and "
            "does not alter timing probability"
        ),
    }
    write_json(args.output_audit_json, audit)
    print(json.dumps(audit, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the deep-history Sanriku-Hokkaido timing catalog and sparse weekly grid."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


JST = timezone(timedelta(hours=9))
ANCHOR = pd.Timestamp("1900-01-06")
FORECAST_START = pd.Timestamp("2026-08-01")
FORECAST_LAST_START = pd.Timestamp("2026-09-26")
CUTOFF_UTC = pd.Timestamp("2026-07-31T15:00:00Z")
REGION = (38.8, 46.0, 140.0, 150.5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slot_start_jst(times: pd.Series) -> pd.Series:
    local = pd.to_datetime(times, utc=True).dt.tz_convert(JST).dt.tz_localize(None)
    days = (local.dt.normalize() - ANCHOR).dt.days
    return ANCHOR + pd.to_timedelta((days // 7) * 7, unit="D")


def load_usgs(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    frame["time_utc"] = pd.to_datetime(frame.time, utc=True, errors="coerce")
    for column in ("mag", "latitude", "longitude", "depth"):
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    return frame.loc[frame.time_utc.notna() & frame.time_utc.lt(CUTOFF_UTC)].copy()


def strongest_by_slot(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.sort_values(["slot_start", "mag", "time_utc"], ascending=[True, False, True])
        .drop_duplicates("slot_start", keep="first")
        .sort_values("slot_start")
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regional-usgs", required=True, type=Path)
    parser.add_argument("--world-usgs", required=True, type=Path)
    parser.add_argument("--historical-csv", required=True, type=Path)
    parser.add_argument("--output-target-catalog", required=True, type=Path)
    parser.add_argument("--output-periods", required=True, type=Path)
    parser.add_argument("--output-audit", required=True, type=Path)
    parser.add_argument("--background-count", type=int, default=520)
    parser.add_argument("--event-radius", type=int, default=8)
    parser.add_argument("--hard-negative-radius", type=int, default=2)
    args = parser.parse_args()

    regional = load_usgs(args.regional_usgs)
    world = load_usgs(args.world_usgs)
    historical = pd.read_csv(args.historical_csv, low_memory=False)
    historical["time_utc"] = pd.to_datetime(historical.time, utc=True, errors="raise")
    for column in ("mag", "latitude", "longitude", "depth"):
        historical[column] = pd.to_numeric(historical.get(column), errors="coerce")

    lat_min, lat_max, lon_min, lon_max = REGION
    inside = regional.latitude.between(lat_min, lat_max) & regional.longitude.between(lon_min, lon_max)
    instrumental = regional.loc[inside & regional.mag.ge(7.9)].copy()
    instrumental["source"] = "USGS_FDSN"
    instrumental["timing_region_member"] = 1
    instrumental["location_eligible"] = 1
    instrumental["date_uncertainty_days"] = 0
    instrumental["date_precision"] = "timestamp"
    instrumental["event_name"] = ""
    instrumental["primary_source"] = "https://earthquake.usgs.gov/earthquakes/eventpage/" + instrumental.id.astype(str)
    instrumental["supporting_source"] = ""
    instrumental["notes"] = "Instrumental/catalog timestamp and coordinates"

    columns = [
        "time", "time_utc", "latitude", "longitude", "depth", "mag", "event_name",
        "place", "id", "source", "timing_region_member", "location_eligible",
        "date_uncertainty_days", "date_precision", "primary_source", "supporting_source", "notes",
    ]
    combined = pd.concat([historical[columns], instrumental[columns]], ignore_index=True, sort=False)
    combined["slot_start"] = slot_start_jst(combined.time_utc)
    targets = strongest_by_slot(combined.loc[combined.mag.ge(7.9) & combined.timing_region_member.eq(1)].copy())
    targets["slot_end_exclusive"] = targets.slot_start + pd.Timedelta(days=7)
    targets["event_time_jst"] = targets.time_utc.dt.tz_convert(JST)
    targets["event_inside_slot"] = (
        targets.event_time_jst.dt.tz_localize(None).ge(targets.slot_start)
        & targets.event_time_jst.dt.tz_localize(None).lt(targets.slot_end_exclusive)
    )
    args.output_target_catalog.parent.mkdir(parents=True, exist_ok=True)
    targets.to_csv(args.output_target_catalog, index=False)

    world_inside = world.latitude.between(lat_min, lat_max) & world.longitude.between(lon_min, lon_max)
    hard = world.loc[~world_inside & world.mag.ge(7.9)].copy()
    hard["slot_start"] = slot_start_jst(hard.time_utc)
    hard = strongest_by_slot(hard)

    earliest = pd.Timestamp(targets.slot_start.min())
    all_grid = pd.date_range(earliest, FORECAST_LAST_START, freq="7D")
    preforecast = all_grid[all_grid < FORECAST_START]
    positions = np.unique(np.rint(np.linspace(0, len(preforecast) - 1, args.background_count)).astype(int))
    selected: set[pd.Timestamp] = set()
    reasons: dict[pd.Timestamp, set[str]] = {}

    def add(date: pd.Timestamp, reason: str) -> None:
        date = pd.Timestamp(date).normalize()
        if earliest <= date <= FORECAST_LAST_START:
            selected.add(date)
            reasons.setdefault(date, set()).add(reason)

    for date in preforecast[positions]:
        add(date, "uniform_deep_history_background")
    for date in targets.slot_start:
        for lag in range(-args.event_radius, args.event_radius + 1):
            add(pd.Timestamp(date) + pd.Timedelta(days=7 * lag), "regional_target_neighborhood")
    for date in hard.slot_start:
        for lag in range(-args.hard_negative_radius, args.hard_negative_radius + 1):
            add(pd.Timestamp(date) + pd.Timedelta(days=7 * lag), "world_nonregional_hard_negative")
    for date in pd.date_range(FORECAST_START, FORECAST_LAST_START, freq="7D"):
        add(date, "prospective_forecast")

    period_rows = [
        {"date": date.strftime("%Y-%m-%d"), "selection_reason": ";".join(sorted(reasons[date]))}
        for date in sorted(selected)
    ]
    args.output_periods.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(period_rows).to_csv(args.output_periods, index=False)

    audit = {
        "status": "PASS" if bool(targets.event_inside_slot.all()) else "FAIL",
        "target_definition": "M>=7.9, 38.8<=lat<=46 and 140<=lon<=150.5 for instrumental rows; official corridor membership for historical rows without imputed coordinates",
        "region_bounds": {"latitude_min": lat_min, "latitude_max": lat_max, "longitude_min": lon_min, "longitude_max": lon_max},
        "target_count": len(targets),
        "historical_timing_target_count": int(targets.source.eq("official_historical_attachment").sum()),
        "location_eligible_target_count": int(targets.location_eligible.eq(1).sum()),
        "first_target_slot": earliest.strftime("%Y-%m-%d"),
        "last_target_slot": pd.Timestamp(targets.slot_start.max()).strftime("%Y-%m-%d"),
        "period_count": len(period_rows),
        "historical_coordinates_imputed": False,
        "cutoff": {"utc_end_exclusive": CUTOFF_UTC.isoformat(), "august_2026_seismic_rows_used": 0},
        "inputs": {
            "regional_usgs": str(args.regional_usgs.resolve()),
            "regional_usgs_sha256": sha256(args.regional_usgs),
            "world_usgs": str(args.world_usgs.resolve()),
            "world_usgs_sha256": sha256(args.world_usgs),
            "historical_csv": str(args.historical_csv.resolve()),
            "historical_csv_sha256": sha256(args.historical_csv),
        },
        "targets": targets[["id", "time_utc", "slot_start", "mag", "source", "location_eligible", "event_name", "place"]].to_dict(orient="records"),
    }
    args.output_audit.parent.mkdir(parents=True, exist_ok=True)
    args.output_audit.write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"status": audit["status"], "targets": len(targets), "historical": audit["historical_timing_target_count"], "location_eligible": audit["location_eligible_target_count"], "periods": len(period_rows)}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Select the exact sparse weekly epochs needed by the V21 prospective run."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


JST = timezone(timedelta(hours=9))
ANCHOR = datetime(1900, 1, 6)
FORECAST_START = datetime(2026, 8, 1)
FORECAST_LAST_START = datetime(2026, 9, 26)
CUTOFF_UTC = pd.Timestamp("2026-07-31T15:00:00Z")
BOUNDS = (28.0, 47.0, 128.0, 149.5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slot_start_jst(times: pd.Series) -> pd.Series:
    local = pd.to_datetime(times, utc=True).dt.tz_convert(JST).dt.tz_localize(None)
    days = (local.dt.normalize() - pd.Timestamp(ANCHOR)).dt.days
    return pd.Timestamp(ANCHOR) + pd.to_timedelta((days // 7) * 7, unit="D")


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    frame["time_utc"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    for column in ("mag", "latitude", "longitude", "depth"):
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    frame = frame.loc[frame.time_utc.notna() & (frame.time_utc < CUTOFF_UTC)].copy()
    frame["slot_start"] = slot_start_jst(frame.time_utc)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--japan-catalog", required=True)
    parser.add_argument("--world-catalog", required=True)
    parser.add_argument("--output-periods", required=True)
    parser.add_argument("--output-audit", required=True)
    parser.add_argument("--background-count", type=int, default=320)
    parser.add_argument("--event-radius", type=int, default=8)
    parser.add_argument("--hard-negative-radius", type=int, default=2)
    args = parser.parse_args()

    japan_path = Path(args.japan_catalog).resolve()
    world_path = Path(args.world_catalog).resolve()
    japan = load(japan_path)
    world = load(world_path)
    lat_min, lat_max, lon_min, lon_max = BOUNDS
    targets = japan.loc[japan.mag >= 7.9].sort_values("time_utc").copy()
    outside = ~(
        world.latitude.between(lat_min, lat_max)
        & world.longitude.between(lon_min, lon_max)
    )
    hard = world.loc[outside & (world.mag >= 7.9)].sort_values("time_utc").copy()

    all_grid = pd.date_range(ANCHOR, FORECAST_LAST_START, freq="7D")
    preforecast = all_grid[all_grid < pd.Timestamp(FORECAST_START)]
    positions = np.unique(
        np.rint(np.linspace(0, len(preforecast) - 1, args.background_count)).astype(int)
    )
    selected: set[pd.Timestamp] = set(preforecast[positions].tolist())
    reasons: dict[pd.Timestamp, set[str]] = {}

    def add(date: pd.Timestamp, reason: str) -> None:
        date = pd.Timestamp(date).normalize()
        if pd.Timestamp(ANCHOR) <= date <= pd.Timestamp(FORECAST_LAST_START):
            selected.add(date)
            reasons.setdefault(date, set()).add(reason)

    for date in preforecast[positions]:
        add(date, "uniform_between_event_background")
    for date in targets.slot_start:
        for lag in range(-args.event_radius, args.event_radius + 1):
            add(date + pd.Timedelta(days=7 * lag), "japan_target_neighborhood")
    for date in hard.slot_start:
        for lag in range(-args.hard_negative_radius, args.hard_negative_radius + 1):
            add(date + pd.Timedelta(days=7 * lag), "world_non_japan_negative_neighborhood")
    for date in pd.date_range(FORECAST_START, FORECAST_LAST_START, freq="7D"):
        add(date, "prospective_forecast")

    rows = [
        {"date": date.strftime("%Y-%m-%d"), "selection_reason": ";".join(sorted(reasons.get(date, {"background"})))}
        for date in sorted(selected)
    ]
    output = Path(args.output_periods).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)

    target_rows = [
        {
            "time_utc": row.time_utc.isoformat(),
            "slot_start_jst": row.slot_start.strftime("%Y-%m-%d"),
            "magnitude": float(row.mag),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "event_id": str(getattr(row, "id", "")),
        }
        for row in targets.itertuples(index=False)
    ]
    hard_rows = [
        {
            "time_utc": row.time_utc.isoformat(),
            "slot_start_jst": row.slot_start.strftime("%Y-%m-%d"),
            "magnitude": float(row.mag),
            "latitude": float(row.latitude),
            "longitude": float(row.longitude),
            "event_id": str(getattr(row, "id", "")),
        }
        for row in hard.itertuples(index=False)
    ]
    audit = {
        "status": "PASS",
        "cutoff": {
            "jst_end_exclusive": "2026-08-01T00:00:00+09:00",
            "utc_end_exclusive": CUTOFF_UTC.isoformat(),
            "august_events_used": 0,
        },
        "weekly_grid": {
            "timezone": "Asia/Tokyo",
            "anchor": ANCHOR.strftime("%Y-%m-%d 00:00 JST"),
            "forecast_slots": [
                date.strftime("%Y-%m-%d")
                for date in pd.date_range(FORECAST_START, FORECAST_LAST_START, freq="7D")
            ],
        },
        "inputs": {
            "japan_catalog": str(japan_path),
            "japan_sha256": sha256(japan_path),
            "world_catalog": str(world_path),
            "world_sha256": sha256(world_path),
        },
        "period_count": len(rows),
        "japan_target_events": target_rows,
        "world_non_japan_negative_events": hard_rows,
    }
    audit_path = Path(args.output_audit).resolve()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"period_count": len(rows), "targets": len(target_rows), "hard_negatives": len(hard_rows)}, indent=2))


if __name__ == "__main__":
    main()

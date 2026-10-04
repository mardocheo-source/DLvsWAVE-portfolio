"""Persist the exact UTC source-time to weekly-master assignment for a completed run."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _identifier(frame: pd.DataFrame) -> pd.Series:
    for column in ("id", "event_id", "code"):
        if column in frame:
            return frame[column].fillna("").astype(str)
    return pd.Series([""] * len(frame), index=frame.index, dtype="object")


def _prepare(
    path: str | Path,
    *,
    role: str,
    threshold: float,
    cutoff: pd.Timestamp,
    bbox: dict[str, list[float]],
) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    required = {"time", "mag", "latitude", "longitude"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Catalog {path} is missing columns: {sorted(missing)}")
    frame["source_time_utc"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    frame["mag"] = pd.to_numeric(frame["mag"], errors="coerce")
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame = frame.loc[
        frame["source_time_utc"].notna()
        & frame["mag"].ge(threshold)
        & frame["source_time_utc"].le(cutoff)
    ].copy()
    lat_min, lat_max = bbox["latitude"]
    lon_min, lon_max = bbox["longitude"]
    frame["inside_extended_japan"] = (
        frame["latitude"].between(lat_min, lat_max)
        & frame["longitude"].between(lon_min, lon_max)
    )
    if role == "foreign_hard_negative":
        frame = frame.loc[~frame["inside_extended_japan"]].copy()
    normalized = frame["source_time_utc"].dt.normalize()
    monday = normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")
    frame["assigned_master_week"] = monday.dt.tz_localize(None)
    frame["assignment_offset_hours"] = (
        (frame["source_time_utc"] - monday).dt.total_seconds() / 3600.0
    )
    frame["catalog_role"] = role
    frame["event_id"] = _identifier(frame)
    frame["source_time_utc"] = frame["source_time_utc"].map(lambda value: value.isoformat())
    return frame[[
        "catalog_role", "event_id", "source_time_utc", "assigned_master_week",
        "assignment_offset_hours", "mag", "latitude", "longitude", "inside_extended_japan",
    ]]


def run(run_dir: Path) -> dict[str, Any]:
    root = run_dir.resolve()
    audit_path = root / "01_data" / "dataset_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    paths = audit["input_paths"]
    cutoff = pd.Timestamp(audit["cutoff_utc"])
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    threshold = float(audit["magnitude_threshold"])
    bbox = audit["japan_extended_bbox"]
    japan = _prepare(
        paths["japan_catalog"], role="japan_positive_source", threshold=threshold,
        cutoff=cutoff, bbox=bbox,
    )
    foreign = _prepare(
        paths["world_catalog"], role="foreign_hard_negative", threshold=threshold,
        cutoff=cutoff, bbox=bbox,
    )
    assignments = pd.concat([japan, foreign], ignore_index=True).sort_values(
        ["assigned_master_week", "source_time_utc", "catalog_role"]
    )
    output_csv = root / "01_data" / "source_event_timestamp_week_assignment.csv"
    assignments.to_csv(output_csv, index=False)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "conversion": "parse source timestamp as UTC exactly once; assign to UTC Monday 00:00 weekly key",
        "threshold": threshold,
        "cutoff_utc": cutoff.isoformat(),
        "rows": int(len(assignments)),
        "japan_source_events": int(assignments["catalog_role"].eq("japan_positive_source").sum()),
        "foreign_hard_negative_events": int(assignments["catalog_role"].eq("foreign_hard_negative").sum()),
        "offset_hours_min": float(assignments["assignment_offset_hours"].min()),
        "offset_hours_max": float(assignments["assignment_offset_hours"].max()),
        "output_csv": str(output_csv),
    }
    output_json = root / "01_data" / "source_event_timestamp_week_assignment.json"
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(run(args.run_dir), indent=2))

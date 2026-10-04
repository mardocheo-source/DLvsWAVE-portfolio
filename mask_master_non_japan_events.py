#!/usr/bin/env python3
"""Silence non-Japan event bins in an already-built master CSV.

The intended workflow is:
1. Build the astronomical master from real worldwide earthquake dates.
2. Quantize/prepare the master normally.
3. Run this script so only Japan-box events remain positive; all other event
   bins become negative anchors with mag/depth/latitude/longitude set to 0.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from datetime import date
from typing import Any


def _to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_day(value: str) -> date | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _inside_box(lat: float | None, lon: float | None, args: argparse.Namespace) -> bool:
    if lat is None or lon is None:
        return False
    return args.japan_lat_min <= lat <= args.japan_lat_max and args.japan_lon_min <= lon <= args.japan_lon_max


def _zero_seismic_fields(row: dict[str, str]) -> None:
    for col in ("mag", "depth", "latitude", "longitude"):
        if col in row:
            row[col] = "0"


def _load_japan_events_by_bin(
    events_csv: Path | None,
    master_rows: list[dict[str, str]],
    args: argparse.Namespace,
) -> dict[str, dict[str, str]]:
    if events_csv is None:
        return {}
    first_day = _parse_day(master_rows[0].get("date", "")) if master_rows else None
    if first_day is None:
        raise ValueError("Cannot map events to master bins: first master row has no valid date")
    with events_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Events CSV has no header: {events_csv}")
        events = [dict(row) for row in reader]

    by_bin: dict[str, dict[str, str]] = {}
    for event in events:
        mag = _to_float(event.get("mag"))
        lat = _to_float(event.get("latitude"))
        lon = _to_float(event.get("longitude"))
        day = _parse_day(event.get("time") or event.get("date") or "")
        if mag is None or mag < args.positive_threshold or day is None:
            continue
        if not _inside_box(lat, lon, args):
            continue
        idx = (day - first_day).days // args.step_days
        if idx < 0 or idx >= len(master_rows):
            continue
        bin_date = master_rows[idx].get("date", "")
        prev = by_bin.get(bin_date)
        prev_mag = _to_float(prev.get("mag")) if prev else None
        if prev is None or prev_mag is None or mag > prev_mag:
            by_bin[bin_date] = {
                "date": bin_date,
                "event_time": event.get("time", ""),
                "mag": f"{mag:g}",
                "depth": str(event.get("depth") or "0"),
                "latitude": str(event.get("latitude") or "0"),
                "longitude": str(event.get("longitude") or "0"),
                "id": event.get("id", ""),
                "place": event.get("place", ""),
            }
    return by_bin


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn non-Japan master event bins into negative anchors.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--manifest-json", default="")
    parser.add_argument(
        "--events-csv",
        default="",
        help=(
            "Optional original world event CSV. When provided, Japan-positive bins are "
            "identified from event dates, not only from the selected event stored in the master row."
        ),
    )
    parser.add_argument("--step-days", type=int, default=30)
    parser.add_argument("--japan-lat-min", type=float, default=28.0)
    parser.add_argument("--japan-lat-max", type=float, default=44.0)
    parser.add_argument("--japan-lon-min", type=float, default=128.0)
    parser.add_argument("--japan-lon-max", type=float, default=147.0)
    parser.add_argument("--positive-threshold", type=float, default=0.1)
    parser.add_argument(
        "--keep-nonpositive-seismic-fields",
        action="store_true",
        help="Leave depth/lat/lon on rows that are already non-events. Default zeros them for clarity.",
    )
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    manifest_json = Path(args.manifest_json) if args.manifest_json else None

    with input_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {input_csv}")
        fieldnames = list(reader.fieldnames)
        rows = [dict(row) for row in reader]

    japan_events_by_bin = _load_japan_events_by_bin(
        Path(args.events_csv) if args.events_csv else None,
        rows,
        args,
    )

    kept_japan_positive: list[dict[str, Any]] = []
    silenced_non_japan: list[dict[str, Any]] = []
    positive_before = 0
    positive_after = 0

    out_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        out = dict(row)
        row_date = row.get("date", "")
        mag = _to_float(row.get("mag"))
        lat = _to_float(row.get("latitude"))
        lon = _to_float(row.get("longitude"))
        is_positive = mag is not None and mag >= args.positive_threshold
        source_japan_event = japan_events_by_bin.get(row_date)
        if source_japan_event is not None:
            positive_before += int(is_positive)
            positive_after += 1
            for col in ("mag", "depth", "latitude", "longitude"):
                if col in out:
                    out[col] = source_japan_event[col]
            kept_japan_positive.append(
                {
                    "row": idx,
                    "date": row_date,
                    "event_time": source_japan_event.get("event_time", ""),
                    "mag": _to_float(source_japan_event.get("mag")),
                    "latitude": _to_float(source_japan_event.get("latitude")),
                    "longitude": _to_float(source_japan_event.get("longitude")),
                    "depth": _to_float(source_japan_event.get("depth")),
                    "id": source_japan_event.get("id", ""),
                    "place": source_japan_event.get("place", ""),
                    "preserved_from_events_csv": True,
                }
            )
        elif is_positive:
            positive_before += 1
            if _inside_box(lat, lon, args):
                positive_after += 1
                kept_japan_positive.append(
                    {
                        "row": idx,
                        "date": row_date,
                        "mag": mag,
                        "latitude": lat,
                        "longitude": lon,
                        "depth": _to_float(row.get("depth")),
                        "preserved_from_events_csv": False,
                    }
                )
            else:
                silenced_non_japan.append(
                    {
                        "row": idx,
                        "date": row_date,
                        "source_mag": mag,
                        "source_latitude": lat,
                        "source_longitude": lon,
                        "source_depth": _to_float(row.get("depth")),
                    }
                )
                _zero_seismic_fields(out)
        elif not args.keep_nonpositive_seismic_fields:
            _zero_seismic_fields(out)
        out_rows.append(out)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    manifest = {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "policy": (
            "Rows with mag>=positive_threshold inside the Japan bbox remain positive; "
            "all other positive rows are converted to mag/depth/latitude/longitude=0."
        ),
        "japan_bbox": {
            "lat_min": args.japan_lat_min,
            "lat_max": args.japan_lat_max,
            "lon_min": args.japan_lon_min,
            "lon_max": args.japan_lon_max,
        },
        "positive_threshold": args.positive_threshold,
        "events_csv": args.events_csv or None,
        "step_days": args.step_days,
        "japan_positive_bins_from_events_csv": len(japan_events_by_bin),
        "rows": len(rows),
        "positive_before": positive_before,
        "positive_after": positive_after,
        "silenced_non_japan": len(silenced_non_japan),
        "kept_japan_positive_rows": kept_japan_positive,
        "silenced_non_japan_rows": silenced_non_japan,
    }
    if manifest_json is not None:
        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print(
        "[mask] positives before/after: "
        f"{positive_before}/{positive_after}; silenced non-Japan: {len(silenced_non_japan)}"
    )
    print(f"[mask] output: {output_csv}")


if __name__ == "__main__":
    main()

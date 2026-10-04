#!/usr/bin/env python3
"""Build Japan/Nankai events with global non-Japan M8+ negative anchors.

The output keeps the original Japan/Nankai positive events unchanged and adds
selected large earthquakes outside the Japan box as mag=0 rows. This lets the
master assign the correct astronomy period around major global earthquakes
while keeping them as negative examples for the Japan/Nankai M8+ target.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import OrderedDict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JAPAN_BOX = (28.0, 44.0, 128.0, 147.0)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _date_key(value: str) -> date:
    text = str(value or "").strip()
    if len(text) < 10:
        return date.min
    return date.fromisoformat(text[:10])


def _inside_box(lat: float, lon: float, box: tuple[float, float, float, float]) -> bool:
    lat_min, lat_max, lon_min, lon_max = box
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def _dedupe_by_days(rows: list[dict[str, str]], dedupe_days: int) -> list[dict[str, str]]:
    if dedupe_days <= 0:
        return rows
    selected: list[dict[str, str]] = []
    for row in sorted(rows, key=lambda r: (-float(r["_source_mag"]), _date_key(r["time"]))):
        row_day = _date_key(row["time"])
        too_close = False
        for kept in selected:
            kept_day = _date_key(kept["time"])
            if abs((row_day - kept_day).days) <= dedupe_days:
                too_close = True
                break
        if not too_close:
            selected.append(row)
    return sorted(selected, key=lambda r: _date_key(r["time"]))


def build_augmented_events(
    japan_events_csv: Path,
    world_events_csv: Path,
    output_csv: Path,
    manifest_json: Path | None,
    min_mag: float,
    max_negative_events: int,
    dedupe_days: int,
    japan_box: tuple[float, float, float, float],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    japan_fields, japan_rows = _read_rows(japan_events_csv)
    _, world_rows = _read_rows(world_events_csv)
    japan_rows_all = japan_rows
    if start_date is not None:
        japan_rows = [row for row in japan_rows if _date_key(row.get("time", "")) >= start_date]
    if end_date is not None:
        japan_rows = [row for row in japan_rows if _date_key(row.get("time", "")) <= end_date]

    candidates: list[dict[str, str]] = []
    skipped_inside_japan = 0
    skipped_under_mag = 0
    skipped_bad_coords = 0

    for src in world_rows:
        src_day = _date_key(str(src.get("time") or ""))
        if start_date is not None and src_day < start_date:
            continue
        if end_date is not None and src_day > end_date:
            continue
        mag = _safe_float(src.get("mag"))
        lat = _safe_float(src.get("latitude"))
        lon = _safe_float(src.get("longitude"))
        if mag is None or mag < min_mag:
            skipped_under_mag += 1
            continue
        if lat is None or lon is None:
            skipped_bad_coords += 1
            continue
        if _inside_box(lat, lon, japan_box):
            skipped_inside_japan += 1
            continue

        out = {field: "" for field in japan_fields}
        src_id = str(src.get("id") or src.get("time") or len(candidates)).strip()
        out["id"] = f"negative_global_m8_non_japan__{src_id}"
        out["time"] = str(src.get("time") or "").strip()
        out["latitude"] = ""
        out["longitude"] = ""
        out["depth"] = ""
        out["mag"] = "0"
        out["magType"] = "negative_anchor"
        out["net"] = str(src.get("net") or "world").strip()
        out["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        src_place = str(src.get("place") or "").strip()
        out["place"] = (
            "NEGATIVE_ANCHOR non-Japan M8+ "
            f"source_mag={mag:g} source_lat={lat:g} source_lon={lon:g}"
            + (f" source_place={src_place}" if src_place else "")
        )
        out["type"] = str(src.get("type") or "earthquake").strip()
        out["status"] = "negative_anchor_non_japan_m8"
        out["locationSource"] = str(src.get("locationSource") or src.get("net") or "world").strip()
        out["magSource"] = str(src.get("magSource") or src.get("net") or "world").strip()
        out["_source_mag"] = f"{mag:.6g}"
        out["_source_lat"] = f"{lat:.6g}"
        out["_source_lon"] = f"{lon:.6g}"
        candidates.append(out)

    selected = _dedupe_by_days(candidates, dedupe_days)
    if max_negative_events > 0 and len(selected) > max_negative_events:
        top = sorted(selected, key=lambda r: (-float(r["_source_mag"]), _date_key(r["time"])))
        selected = sorted(top[:max_negative_events], key=lambda r: _date_key(r["time"]))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    positive_output_rows = [
        {field: row.get(field, "") for field in japan_fields}
        for row in japan_rows
    ]
    negative_output_rows = [
        {field: row.get(field, "") for field in japan_fields}
        for row in selected
    ]
    output_rows = sorted(
        positive_output_rows + negative_output_rows,
        key=lambda r: (_date_key(r.get("time", "")), str(r.get("id", ""))),
    )
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=japan_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    manifest: dict[str, Any] = OrderedDict()
    manifest["japan_events_csv"] = str(japan_events_csv)
    manifest["world_events_csv"] = str(world_events_csv)
    manifest["output_csv"] = str(output_csv)
    manifest["negative_anchor_policy"] = (
        "global M8+ earthquakes outside Japan bbox are added with mag=0; "
        "lat/lon/depth are left blank so downstream non-event defaults are used"
    )
    manifest["japan_bbox"] = {
        "lat_min": japan_box[0],
        "lat_max": japan_box[1],
        "lon_min": japan_box[2],
        "lon_max": japan_box[3],
    }
    manifest["min_mag"] = min_mag
    manifest["max_negative_events"] = max_negative_events
    manifest["dedupe_days"] = dedupe_days
    manifest["start_date"] = start_date.isoformat() if start_date else None
    manifest["end_date"] = end_date.isoformat() if end_date else None
    manifest["positive_japan_rows_source"] = len(japan_rows_all)
    manifest["positive_japan_rows"] = len(japan_rows)
    manifest["candidate_negative_rows"] = len(candidates)
    manifest["selected_negative_rows"] = len(selected)
    manifest["skipped_inside_japan_bbox"] = skipped_inside_japan
    manifest["skipped_under_min_mag"] = skipped_under_mag
    manifest["skipped_bad_coords"] = skipped_bad_coords
    manifest["selected_negative_anchors"] = [
        {
            "id": row.get("id", ""),
            "time": row.get("time", ""),
            "source_mag": float(row["_source_mag"]),
            "source_lat": float(row["_source_lat"]),
            "source_lon": float(row["_source_lon"]),
            "place": row.get("place", ""),
        }
        for row in selected
    ]

    if manifest_json is not None:
        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add global non-Japan M8+ earthquakes as mag=0 negative anchors."
    )
    parser.add_argument("--japan-events-csv", required=True)
    parser.add_argument("--world-events-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--manifest-json", default="")
    parser.add_argument("--min-mag", type=float, default=8.0)
    parser.add_argument("--max-negative-events", type=int, default=48)
    parser.add_argument("--dedupe-days", type=int, default=30)
    parser.add_argument("--japan-lat-min", type=float, default=DEFAULT_JAPAN_BOX[0])
    parser.add_argument("--japan-lat-max", type=float, default=DEFAULT_JAPAN_BOX[1])
    parser.add_argument("--japan-lon-min", type=float, default=DEFAULT_JAPAN_BOX[2])
    parser.add_argument("--japan-lon-max", type=float, default=DEFAULT_JAPAN_BOX[3])
    parser.add_argument("--start-date", default="", help="Optional inclusive event start date YYYY-MM-DD.")
    parser.add_argument("--end-date", default="", help="Optional inclusive event end date YYYY-MM-DD.")
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    manifest = build_augmented_events(
        japan_events_csv=Path(args.japan_events_csv),
        world_events_csv=Path(args.world_events_csv),
        output_csv=Path(args.output_csv),
        manifest_json=Path(args.manifest_json) if args.manifest_json else None,
        min_mag=args.min_mag,
        max_negative_events=args.max_negative_events,
        dedupe_days=args.dedupe_days,
        japan_box=(args.japan_lat_min, args.japan_lat_max, args.japan_lon_min, args.japan_lon_max),
        start_date=start_date,
        end_date=end_date,
    )
    print(
        "[negative anchors] selected "
        f"{manifest['selected_negative_rows']}/{manifest['candidate_negative_rows']} "
        "global non-Japan M8+ rows"
    )
    print(f"[negative anchors] output: {manifest['output_csv']}")


if __name__ == "__main__":
    main()

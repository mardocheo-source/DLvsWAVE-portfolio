#!/usr/bin/env python3
"""Extract essential earthquake events from a merged astro/USGS master CSV.

The master files in this project can contain hundreds of daily astro rows plus
only a small number of actual earthquake rows.  This script writes a compact
event catalog with only the fields needed by seismic analysis:

    time,latitude,longitude,depth,mag
"""
from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from tasks import parse_datetime_like


ESSENTIAL_FIELDS = ["time", "latitude", "longitude", "depth", "mag"]


def optional_float(value: Any) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def find_col(header: list[str], requested: str, candidates: tuple[str, ...]) -> str | None:
    if requested and requested != "auto":
        return requested if requested in header else None
    lower = {c.strip().lower(): c for c in header}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def format_time(value: str) -> str:
    dt = parse_datetime_like(value)
    if dt is None:
        return str(value or "").strip()
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt.strftime("%Y-%m-%dT00:00:00.000Z")
    millis = int(dt.microsecond / 1000)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{millis:03d}Z"


def extract_events(args: argparse.Namespace) -> dict[str, Any]:
    input_csv = Path(args.input_csv)
    if not input_csv.exists():
        raise FileNotFoundError(f"Master CSV non trovato: {input_csv}")
    if input_csv.is_dir():
        raise ValueError(f"Il path e' una directory, non un CSV: {input_csv}")

    output_csv = Path(args.output_csv) if args.output_csv else input_csv.with_name("earthquakes.events.csv")
    with input_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV senza header: {input_csv}")
        header = list(reader.fieldnames)
        rows = list(reader)

    date_col = find_col(header, args.date_col, ("date", "time", "datetime", "timestamp", "origin_time"))
    mag_col = find_col(header, args.mag_col, ("mag", "magnitude", "mw", "ml"))
    lat_col = find_col(header, args.lat_col, ("latitude", "lat"))
    lon_col = find_col(header, args.lon_col, ("longitude", "lon", "lng"))
    depth_col = find_col(header, args.depth_col, ("depth", "depth_km", "depthkm"))
    required = {
        "date/time": date_col,
        "mag": mag_col,
        "latitude": lat_col,
        "longitude": lon_col,
        "depth": depth_col,
    }
    missing = [name for name, col in required.items() if col is None]
    if missing:
        raise ValueError(f"Colonne richieste non trovate nel master: {missing}")

    out_rows: list[dict[str, Any]] = []
    for row_no, row in enumerate(rows, start=2):
        mag = optional_float(row.get(mag_col))
        lat = optional_float(row.get(lat_col))
        lon = optional_float(row.get(lon_col))
        depth = optional_float(row.get(depth_col))
        if mag is None or lat is None or lon is None or depth is None:
            continue
        if mag <= float(args.min_mag):
            continue
        item: dict[str, Any] = {
            "time": format_time(str(row.get(date_col, ""))),
            "latitude": lat,
            "longitude": lon,
            "depth": depth,
            "mag": mag,
        }
        if args.include_source_row:
            item["source_row"] = row_no
        out_rows.append(item)

    out_rows.sort(key=lambda r: parse_datetime_like(r["time"]) or datetime.min)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(ESSENTIAL_FIELDS)
    if args.include_source_row:
        fields.append("source_row")
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)
    return {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "input_rows": len(rows),
        "event_rows": len(out_rows),
        "fields": fields,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", required=True, help="master_with_usgs_core_astrofmt.csv")
    ap.add_argument("--output-csv", default="",
                    help="default: earthquakes.events.csv next to the master")
    ap.add_argument("--date-col", default="auto")
    ap.add_argument("--mag-col", default="auto")
    ap.add_argument("--lat-col", default="auto")
    ap.add_argument("--lon-col", default="auto")
    ap.add_argument("--depth-col", default="auto")
    ap.add_argument("--min-mag", type=float, default=0.0,
                    help="rows with mag <= min-mag are treated as non-events")
    ap.add_argument("--include-source-row", action="store_true",
                    help="add source_row for traceability; off by default to keep the CSV essential")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = extract_events(args)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise SystemExit(f"ERRORE extract_earthquake_events: {exc}") from exc
    print(f"Input rows : {result['input_rows']}")
    print(f"Event rows : {result['event_rows']}")
    print(f"Output CSV : {result['output_csv']}")
    print(f"Fields     : {','.join(result['fields'])}")


if __name__ == "__main__":
    main()

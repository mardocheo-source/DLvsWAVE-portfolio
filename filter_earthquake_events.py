#!/usr/bin/env python3
"""Filter an earthquake CSV by magnitude/date while preserving its schema."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


def _parse_day(value: str) -> date:
    text = str(value or "").strip()
    if len(text) < 10:
        return date.min
    return date.fromisoformat(text[:10])


def _to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter earthquake event rows for DLvsWAVE masters.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--manifest-json", default="")
    parser.add_argument("--min-mag", type=float, required=True)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--sort-ascending", action="store_true", default=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    manifest_json = Path(args.manifest_json) if args.manifest_json else None
    start_day = date.fromisoformat(args.start_date) if args.start_date else None
    end_day = date.fromisoformat(args.end_date) if args.end_date else None

    with input_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {input_csv}")
        fieldnames = list(reader.fieldnames)
        rows = [dict(row) for row in reader]

    kept: list[dict[str, str]] = []
    skipped_under_mag = 0
    skipped_outside_dates = 0
    skipped_bad_mag = 0

    for row in rows:
        mag = _to_float(row.get("mag"))
        if mag is None:
            skipped_bad_mag += 1
            continue
        if mag < args.min_mag:
            skipped_under_mag += 1
            continue
        row_day = _parse_day(row.get("time") or row.get("date") or "")
        if start_day is not None and row_day < start_day:
            skipped_outside_dates += 1
            continue
        if end_day is not None and row_day > end_day:
            skipped_outside_dates += 1
            continue
        kept.append(row)

    kept.sort(key=lambda r: (_parse_day(r.get("time") or r.get("date") or ""), str(r.get("id", ""))))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    manifest = {
        "title": args.title,
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "min_mag": args.min_mag,
        "start_date": start_day.isoformat() if start_day else None,
        "end_date": end_day.isoformat() if end_day else None,
        "input_rows": len(rows),
        "kept_rows": len(kept),
        "skipped_under_mag": skipped_under_mag,
        "skipped_outside_dates": skipped_outside_dates,
        "skipped_bad_mag": skipped_bad_mag,
        "first_kept_time": kept[0].get("time", "") if kept else None,
        "last_kept_time": kept[-1].get("time", "") if kept else None,
    }
    if manifest_json is not None:
        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print(f"[events] kept {len(kept)}/{len(rows)} rows with mag >= {args.min_mag:g}")
    print(f"[events] output: {output_csv}")


if __name__ == "__main__":
    main()

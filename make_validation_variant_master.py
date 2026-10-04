#!/usr/bin/env python3
"""Create anti-leak validation variants of a DLvsWAVE CSV master.

The forecast rows are never shuffled.  Only rows strictly before
--forecast-start-date are transformed, while the output date column remains the
original serial/grid slot.  That makes reverse/random validation operate on
record order without leaking forecast-period labels or features into training.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build normal/reverse/random validation master variants.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--manifest-json", required=True)
    p.add_argument("--mapping-csv", required=True)
    p.add_argument("--variant", choices=["normal", "reverse", "random"], required=True)
    p.add_argument("--forecast-start-date", required=True)
    p.add_argument("--date-column", default="date")
    p.add_argument("--random-seed", type=int, default=8675309)
    return p.parse_args()


def parse_date(value: str) -> datetime:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d")


def main() -> None:
    args = parse_args()
    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    manifest_path = Path(args.manifest_json)
    mapping_path = Path(args.mapping_csv)

    if not in_path.exists():
        raise FileNotFoundError(f"Input master not found: {in_path}")

    with in_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if args.date_column not in fieldnames:
        raise ValueError(f"Date column not found: {args.date_column}")

    forecast_start = parse_date(args.forecast_start_date)
    pre_indices = [
        i for i, row in enumerate(rows)
        if parse_date(row[args.date_column]) < forecast_start
    ]
    forecast_indices = [
        i for i, row in enumerate(rows)
        if parse_date(row[args.date_column]) >= forecast_start
    ]

    source_for_slot = list(range(len(rows)))
    if args.variant == "reverse":
        reversed_pre = list(reversed(pre_indices))
        for slot_idx, source_idx in zip(pre_indices, reversed_pre):
            source_for_slot[slot_idx] = source_idx
    elif args.variant == "random":
        shuffled = list(pre_indices)
        rng = random.Random(args.random_seed)
        rng.shuffle(shuffled)
        for slot_idx, source_idx in zip(pre_indices, shuffled):
            source_for_slot[slot_idx] = source_idx

    out_rows = []
    mapping_rows = []
    pre_index_set = set(pre_indices)
    forecast_index_set = set(forecast_indices)
    for slot_idx, source_idx in enumerate(source_for_slot):
        slot_row = rows[slot_idx]
        source_row = rows[source_idx]
        out_row = dict(source_row)
        out_row[args.date_column] = slot_row[args.date_column]
        out_rows.append(out_row)
        mapping_rows.append({
            "slot_index": slot_idx,
            "slot_date": slot_row[args.date_column],
            "source_index": source_idx,
            "source_date": source_row[args.date_column],
            "is_pre_forecast": int(slot_idx in pre_index_set),
            "is_forecast_row": int(slot_idx in forecast_index_set),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    with mapping_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "slot_index", "slot_date", "source_index", "source_date",
                "is_pre_forecast", "is_forecast_row",
            ],
        )
        writer.writeheader()
        writer.writerows(mapping_rows)

    manifest = {
        "script": Path(__file__).name,
        "input_csv": str(in_path),
        "output_csv": str(out_path),
        "mapping_csv": str(mapping_path),
        "variant": args.variant,
        "forecast_start_date": args.forecast_start_date,
        "date_column": args.date_column,
        "random_seed": args.random_seed if args.variant == "random" else None,
        "row_count": len(rows),
        "pre_forecast_row_count": len(pre_indices),
        "forecast_row_count": len(forecast_indices),
        "leakage_guard": (
            "Rows with date >= forecast_start_date are kept in their original "
            "slot and source position. Only pre-forecast rows are permuted."
        ),
        "train_after_test_allowed": False,
        "validation_axis": "serial_slot_order",
        "source_chronology_note": (
            "Reverse/random intentionally break original source chronology for "
            "pre-forecast rows. Causal train/test separation is therefore "
            "defined by output serial slot order, not source_date order."
        ),
        "date_semantics": (
            "Output date is the serial/grid slot date. Non-date values come "
            "from source_index according to mapping_csv."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"[OK] variant={args.variant} rows={len(rows)} pre_forecast={len(pre_indices)} forecast={len(forecast_indices)}")
    print(f"[OK] output:   {out_path}")
    print(f"[OK] manifest: {manifest_path}")
    print(f"[OK] mapping:  {mapping_path}")


if __name__ == "__main__":
    main()

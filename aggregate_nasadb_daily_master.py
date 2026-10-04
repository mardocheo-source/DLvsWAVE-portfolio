#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Aggregate a 1-day nasaDb master into slot rows using median values, "
            "with optional per-body min/max/mean derived fields."
        )
    )
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--manifest-json", default="")
    p.add_argument("--slot-start-date", required=True)
    p.add_argument("--slot-end-date", required=True)
    p.add_argument("--slot-step-interval", default="30d")
    p.add_argument("--advanced-body-stats", choices=["0", "1"], default="0")
    p.add_argument("--advanced-group-size", type=int, default=4)
    return p.parse_args()


def parse_iso_day(value: str) -> date:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def parse_step_days(value: str) -> int:
    raw = str(value).strip().lower()
    if raw.endswith("d"):
        raw = raw[:-1]
    days = int(raw)
    if days <= 0:
        raise ValueError("slot step interval must be > 0 days")
    return days


def safe_float(value: str) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def fmt(value: float) -> str:
    text = f"{value:.12g}"
    return text


def detect_date_column(fieldnames: list[str]) -> str:
    for candidate in ("date", "time", "datetime"):
        if candidate in fieldnames:
            return candidate
    raise ValueError("input CSV must include one of: date, time, datetime")


def body_prefix(column_name: str) -> str:
    if "_" not in column_name:
        return ""
    return column_name.rsplit("_", 1)[0]


def is_seismic_column(column_name: str) -> bool:
    return column_name in {"mag", "depth", "latitude", "longitude", "target"}


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    manifest_json = Path(args.manifest_json) if args.manifest_json else None

    slot_start = parse_iso_day(args.slot_start_date)
    slot_end = parse_iso_day(args.slot_end_date)
    step_days = parse_step_days(args.slot_step_interval)

    if slot_end < slot_start:
        raise ValueError("slot end date must be >= slot start date")

    with input_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValueError("input CSV has no header")
        day_col = detect_date_column(fieldnames)
        rows = list(reader)

    numeric_columns: list[str] = []
    for col in fieldnames:
        if col == day_col:
            continue
        for row in rows:
            value = safe_float(str(row.get(col, "")).strip())
            if value is not None:
                numeric_columns.append(col)
                break

    slots: dict[date, list[dict[str, str]]] = defaultdict(list)
    accepted_rows = 0
    skipped_rows = 0
    for row in rows:
        raw_day = str(row.get(day_col, "")).strip()
        if not raw_day:
            skipped_rows += 1
            continue
        try:
            d = parse_iso_day(raw_day)
        except Exception:
            skipped_rows += 1
            continue
        if d < slot_start or d > slot_end:
            skipped_rows += 1
            continue
        offset_days = (d - slot_start).days
        slot_idx = offset_days // step_days
        bucket_day = slot_start + timedelta(days=slot_idx * step_days)
        slots[bucket_day].append(row)
        accepted_rows += 1

    slot_days = sorted(slots.keys())
    if not slot_days:
        raise ValueError("no rows fall into requested slot range")

    out_fieldnames = list(fieldnames)
    if day_col != "date":
        out_fieldnames = ["date"] + [c for c in out_fieldnames if c != "date"]

    advanced = args.advanced_body_stats == "1"
    advanced_columns: list[str] = []
    body_groups: dict[str, list[str]] = {}
    if advanced:
        candidates = [c for c in numeric_columns if not is_seismic_column(c)]
        grouped: dict[str, list[str]] = defaultdict(list)
        for col in candidates:
            prefix = body_prefix(col)
            if prefix:
                grouped[prefix].append(col)
        for prefix, cols in grouped.items():
            cols_sorted = sorted(cols)
            if len(cols_sorted) >= args.advanced_group_size:
                body_groups[prefix] = cols_sorted[: args.advanced_group_size]
                advanced_columns.extend(
                    [
                        f"{prefix}__slot4_min",
                        f"{prefix}__slot4_max",
                        f"{prefix}__slot4_mean",
                    ]
                )
        out_fieldnames.extend(advanced_columns)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    written_rows = 0
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        for slot_day in slot_days:
            bucket = slots[slot_day]
            out_row: dict[str, str] = {k: "" for k in out_fieldnames}
            out_row["date"] = slot_day.isoformat()

            for col in fieldnames:
                if col == day_col:
                    continue
                vals: list[float] = []
                last_text = ""
                for row in bucket:
                    raw = str(row.get(col, "")).strip()
                    if raw and not last_text:
                        last_text = raw
                    num = safe_float(raw)
                    if num is not None:
                        vals.append(num)
                if vals:
                    out_row[col] = fmt(float(median(vals)))
                else:
                    out_row[col] = last_text

            if advanced and body_groups:
                for prefix, cols in body_groups.items():
                    slot_vals = [safe_float(out_row.get(c, "")) for c in cols]
                    nums = [v for v in slot_vals if v is not None]
                    if not nums:
                        continue
                    out_row[f"{prefix}__slot4_min"] = fmt(min(nums))
                    out_row[f"{prefix}__slot4_max"] = fmt(max(nums))
                    out_row[f"{prefix}__slot4_mean"] = fmt(sum(nums) / len(nums))

            writer.writerow(out_row)
            written_rows += 1

    if manifest_json:
        manifest = {
            "input_csv": str(input_csv),
            "output_csv": str(output_csv),
            "slot_start_date": slot_start.isoformat(),
            "slot_end_date": slot_end.isoformat(),
            "slot_step_days": step_days,
            "input_rows": len(rows),
            "accepted_daily_rows": accepted_rows,
            "skipped_rows": skipped_rows,
            "output_slot_rows": written_rows,
            "numeric_columns": len(numeric_columns),
            "advanced_body_stats": advanced,
            "advanced_group_size": args.advanced_group_size,
            "advanced_groups": {k: v for k, v in sorted(body_groups.items())},
            "advanced_columns": advanced_columns,
        }
        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

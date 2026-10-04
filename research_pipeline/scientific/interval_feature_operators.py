#!/usr/bin/env python3
"""Build fixed-interval astronomical summaries from a finer Horizons grid.

The output keeps the value observed at the interval start and optionally adds
minimum, median and maximum columns for selected ephemeris fields.  Selection
is expressed with command-line arguments so the same implementation can be
used for any region, cadence, body set or forecast window.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd


FEATURE = re.compile(
    r"^body:(?P<body>[^|]+)\|center:(?P<center>[^|]+)\|"
    r"frame:(?P<frame>[^|]+)\|eph:(?P<eph>[^|]+)\|op:(?P<op>[^|]+)$"
)


def iso(value: object) -> date:
    """Parse an ISO day without pandas' year-1677 lower bound."""
    return date.fromisoformat(str(value)[:10])


def csv_set(value: str) -> set[str]:
    return {item.strip() for item in str(value).split(",") if item.strip()}


def csv_list(value: str) -> list[str]:
    return list(
        dict.fromkeys(item.strip() for item in str(value).split(",") if item.strip())
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--input-fine-master", type=Path, required=True)
    value.add_argument("--output-master", type=Path, required=True)
    value.add_argument("--audit-json", type=Path, required=True)
    value.add_argument(
        "--anchor-date",
        required=True,
        help="Reference date that fixes the target-interval phase.",
    )
    value.add_argument(
        "--start-date",
        default="",
        help=(
            "First target interval to emit. When omitted, the earliest complete "
            "target interval aligned to --anchor-date is inferred from the fine grid."
        ),
    )
    value.add_argument("--end-date", required=True)
    value.add_argument("--source-step-days", type=int, required=True)
    value.add_argument("--target-step-days", type=int, required=True)
    value.add_argument(
        "--operators",
        default="min,median,max",
        help="Comma-separated interval operators: min, median, max, mean.",
    )
    value.add_argument(
        "--ephemerides",
        default="x,y,z,range,range_rate,lighttime",
        help="Ephemeris fields that receive interval operators; '*' selects all.",
    )
    value.add_argument(
        "--bodies",
        default="*",
        help="Comma-separated JPL body identifiers; '*' selects all.",
    )
    value.add_argument(
        "--include-start-values",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    value.add_argument(
        "--require-complete-windows",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return value


def aggregate(values: np.ndarray, operator: str) -> float:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return float("nan")
    functions = {
        "min": np.min,
        "median": np.median,
        "max": np.max,
        "mean": np.mean,
    }
    if operator not in functions:
        raise ValueError(f"Unsupported interval operator: {operator}")
    return float(functions[operator](finite))


def main() -> None:
    args = parser().parse_args()
    if args.source_step_days < 1 or args.target_step_days < 1:
        raise ValueError("Source and target steps must be positive")
    if args.target_step_days % args.source_step_days:
        raise ValueError("target-step-days must be divisible by source-step-days")
    samples_per_window = args.target_step_days // args.source_step_days
    operators = csv_list(args.operators)
    ephemerides = csv_set(args.ephemerides)
    bodies = csv_set(args.bodies)
    frame = pd.read_csv(args.input_fine_master, low_memory=False)
    if "date" not in frame:
        raise ValueError("Fine master is missing the date column")
    dates = [iso(value) for value in frame["date"]]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("Fine-master dates must be unique and increasing")
    date_to_row = {value: index for index, value in enumerate(dates)}

    feature_meta: dict[str, dict[str, str]] = {}
    selected: list[str] = []
    for column in frame.columns:
        match = FEATURE.match(column)
        if not match or match.group("op") != "val":
            continue
        meta = match.groupdict()
        feature_meta[column] = meta
        if (
            ("*" in ephemerides or meta["eph"] in ephemerides)
            and ("*" in bodies or meta["body"] in bodies)
        ):
            selected.append(column)
    if not selected:
        raise ValueError("No astronomical columns matched the operator selectors")
    selected_matrix = frame[selected].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    operator_functions = {
        "min": np.nanmin,
        "median": np.nanmedian,
        "max": np.nanmax,
        "mean": np.nanmean,
    }
    unsupported = sorted(set(operators).difference(operator_functions))
    if unsupported:
        raise ValueError(f"Unsupported interval operators: {unsupported}")

    anchor = iso(args.anchor_date)
    end = iso(args.end_date)
    if args.start_date:
        target_start = iso(args.start_date)
    else:
        source_start = dates[0]
        phase = (source_start - anchor).days % args.target_step_days
        target_start = (
            source_start
            if phase == 0
            else source_start + timedelta(days=args.target_step_days - phase)
        )
    if (target_start - anchor).days % args.target_step_days:
        raise ValueError(
            "start-date is not aligned to anchor-date at target-step-days cadence"
        )
    if target_start > end:
        raise ValueError("start-date must not be after end-date")
    target_dates: list[date] = []
    cursor = target_start
    while cursor <= end:
        target_dates.append(cursor)
        cursor += timedelta(days=args.target_step_days)

    rows: list[dict[str, object]] = []
    incomplete: list[dict[str, object]] = []
    metadata = [column for column in frame.columns if column not in feature_meta]
    start_features = list(feature_meta) if args.include_start_values else []
    retained_start_columns = list(dict.fromkeys(metadata + start_features))
    for interval_start in target_dates:
        sample_dates = [
            interval_start + timedelta(days=i * args.source_step_days)
            for i in range(samples_per_window)
        ]
        missing = [value.isoformat() for value in sample_dates if value not in date_to_row]
        if missing:
            incomplete.append(
                {"start": interval_start.isoformat(), "missing": missing}
            )
            if args.require_complete_windows:
                continue
        available = [date_to_row[value] for value in sample_dates if value in date_to_row]
        if not available:
            continue
        start_index = date_to_row.get(interval_start, available[0])
        row: dict[str, object] = frame.loc[
            start_index, retained_start_columns
        ].to_dict()
        row["date"] = interval_start.isoformat()
        window_matrix = selected_matrix[np.asarray(available, dtype=int)]
        for operator in operators:
            aggregated = operator_functions[operator](window_matrix, axis=0)
            for column, value in zip(selected, aggregated):
                output_name = column.rsplit("|op:", 1)[0] + f"|op:{operator}"
                row[output_name] = float(value)
        rows.append(row)

    if args.require_complete_windows and incomplete:
        preview = incomplete[:3]
        raise RuntimeError(
            f"{len(incomplete)} target windows are incomplete; examples={preview}"
        )
    output = pd.DataFrame(rows)
    args.output_master.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_master, index=False)
    operator_columns = [column for column in output if "|op:" in column and not column.endswith("|op:val")]
    payload = {
        "schema": "interval_feature_operators.audit.v1",
        "input_fine_master": str(args.input_fine_master.resolve()),
        "output_master": str(args.output_master.resolve()),
        "anchor_date": anchor.isoformat(),
        "start_date": target_start.isoformat(),
        "end_date": end.isoformat(),
        "source_step_days": args.source_step_days,
        "target_step_days": args.target_step_days,
        "samples_per_interval": samples_per_window,
        "operators": operators,
        "selected_ephemerides": sorted(ephemerides),
        "selected_bodies": sorted(bodies),
        "start_value_feature_count": len(start_features),
        "operator_source_feature_count": len(selected),
        "generated_operator_feature_count": len(operator_columns),
        "output_rows": len(output),
        "output_columns": len(output.columns),
        "incomplete_windows": incomplete,
        "temporal_semantics": (
            "Every row is keyed by the target interval start. Aggregate columns "
            "use only fine-grid samples at start + n*source_step strictly inside "
            "that target interval; no sample from a later interval is used."
        ),
    }
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()

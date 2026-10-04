#!/usr/bin/env python3
"""Sanitize a numeric DLvsWAVE master CSV.

The training loader intentionally rejects blank feature cells. Legacy nasaDb
downloads can contain short ephemeris gaps for a body/date block, especially
with rich fullAstro presets. This script fills those gaps deterministically
without touching the date column.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill blank/NaN numeric cells in a master CSV.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--report-json", default="")
    parser.add_argument(
        "--skip-cols",
        default="date",
        help="Comma-separated columns to preserve as-is; default: date.",
    )
    parser.add_argument(
        "--method",
        default="ffill_bfill_median_zero",
        choices=["ffill_bfill_median_zero", "median_zero", "zero"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    in_path = Path(args.input_csv)
    out_path = Path(args.output_csv)
    if not in_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_path}")

    skip_cols = {item.strip() for item in args.skip_cols.split(",") if item.strip()}
    df = pd.read_csv(in_path, dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError(f"Input CSV is empty: {in_path}")

    report = {
        "input_csv": str(in_path),
        "output_csv": str(out_path),
        "method": args.method,
        "skip_cols": sorted(skip_cols),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "filled_cells_total": 0,
        "columns_with_fills": [],
    }

    for col in df.columns:
        if col in skip_cols:
            continue

        raw = df[col].astype(str).str.strip()
        missing_mask = raw.eq("") | raw.str.lower().isin({"nan", "none", "null"})
        if not missing_mask.any():
            # Still validate that non-skipped columns are numeric.
            converted = pd.to_numeric(raw, errors="coerce")
            bad = converted.isna()
            if bad.any():
                examples = raw[bad].head(3).tolist()
                raise ValueError(f"Non-numeric values in column {col!r}: {examples}")
            df[col] = converted
            continue

        converted = pd.to_numeric(raw.mask(missing_mask), errors="coerce")
        bad_nonmissing = converted.isna() & ~missing_mask
        if bad_nonmissing.any():
            examples = raw[bad_nonmissing].head(3).tolist()
            raise ValueError(f"Non-numeric values in column {col!r}: {examples}")

        before_missing = int(converted.isna().sum())
        filled = converted
        if args.method == "ffill_bfill_median_zero":
            filled = filled.ffill().bfill()
        if args.method in {"ffill_bfill_median_zero", "median_zero"} and filled.isna().any():
            median = converted.dropna().median()
            if pd.notna(median):
                filled = filled.fillna(float(median))
        if args.method == "zero" or filled.isna().any():
            filled = filled.fillna(0.0)

        after_missing = int(filled.isna().sum())
        filled_count = before_missing - after_missing
        report["filled_cells_total"] += filled_count
        report["columns_with_fills"].append(
            {
                "column": col,
                "missing_before": before_missing,
                "missing_after": after_missing,
                "filled": filled_count,
            }
        )
        df[col] = filled

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"[sanitize] input:  {in_path}")
    print(f"[sanitize] output: {out_path}")
    print(f"[sanitize] filled cells: {report['filled_cells_total']}")
    print(f"[sanitize] columns with fills: {len(report['columns_with_fills'])}")


if __name__ == "__main__":
    main()

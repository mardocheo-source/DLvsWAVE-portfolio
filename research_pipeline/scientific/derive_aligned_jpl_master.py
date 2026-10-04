#!/usr/bin/env python3
"""Derive an exact coarser JPL grid from an anchor-aligned finer master."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-master", required=True, type=Path)
    parser.add_argument("--output-master", required=True, type=Path)
    parser.add_argument("--audit-json", required=True, type=Path)
    parser.add_argument("--source-step-days", required=True, type=int)
    parser.add_argument("--target-step-days", required=True, type=int)
    parser.add_argument("--anchor-date", required=True)
    args = parser.parse_args()

    if args.target_step_days % args.source_step_days:
        raise ValueError("Target cadence must be an integer multiple of source cadence")
    source = pd.read_csv(args.source_master, low_memory=False)
    dates = pd.to_datetime(source["date"], format="%Y-%m-%d")
    deltas = dates.diff().dropna().dt.days.unique().tolist()
    if deltas != [args.source_step_days]:
        raise ValueError(f"Unexpected source cadence: {deltas}")
    anchor = datetime.strptime(args.anchor_date, "%Y-%m-%d")
    offsets = (dates - anchor).dt.days
    mask = offsets.mod(args.target_step_days).eq(0)
    output = source.loc[mask].reset_index(drop=True)
    output_dates = pd.to_datetime(output["date"], format="%Y-%m-%d")
    target_deltas = output_dates.diff().dropna().dt.days.unique().tolist()
    if target_deltas != [args.target_step_days]:
        raise ValueError(f"Derived grid is not exact: {target_deltas}")
    anchor_hits = output["date"].astype(str).eq(args.anchor_date).sum()
    if anchor_hits != 1:
        raise ValueError(f"Expected one anchor row, found {anchor_hits}")

    args.output_master.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output_master, index=False)
    audit = {
        "status": "COMPLETE",
        "method": "exact anchor-aligned stride; astronomical values are not interpolated",
        "source_master": str(args.source_master.resolve()),
        "source_sha256": digest(args.source_master),
        "source_step_days": args.source_step_days,
        "target_step_days": args.target_step_days,
        "stride": args.target_step_days // args.source_step_days,
        "anchor_date": args.anchor_date,
        "source_rows": len(source),
        "output_rows": len(output),
        "first_date": str(output.iloc[0]["date"]),
        "last_date": str(output.iloc[-1]["date"]),
        "output_master": str(args.output_master.resolve()),
        "output_sha256": digest(args.output_master),
    }
    args.audit_json.parent.mkdir(parents=True, exist_ok=True)
    args.audit_json.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()

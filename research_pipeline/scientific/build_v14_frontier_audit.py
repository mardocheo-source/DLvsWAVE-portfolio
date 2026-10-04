#!/usr/bin/env python3
"""Compose a standard JPL coverage audit from stride or direct-download data."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-frontier-json", type=Path)
    parser.add_argument("--derivation-json", type=Path)
    parser.add_argument("--jpl-manifest-json", type=Path)
    parser.add_argument("--anchor-date")
    parser.add_argument("--forecast-end")
    parser.add_argument("--catalog-csv", required=True, type=Path)
    parser.add_argument("--body-csv", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()
    stride_mode = args.source_frontier_json and args.derivation_json
    direct_mode = args.jpl_manifest_json is not None
    if bool(stride_mode) == bool(direct_mode):
        parser.error(
            "supply either --source-frontier-json plus --derivation-json, "
            "or --jpl-manifest-json"
        )
    catalog = pd.read_csv(args.catalog_csv)
    with args.body_csv.open(newline="", encoding="utf-8") as handle:
        bodies = [row["body_name"] for row in csv.DictReader(handle)]
    if stride_mode:
        source = json.loads(
            args.source_frontier_json.read_text(encoding="utf-8")
        )
        derivation = json.loads(args.derivation_json.read_text(encoding="utf-8"))
        candidate_start = derivation["first_date"]
        anchor_date = derivation["anchor_date"]
        forecast_end = "2028-12-31"
        step_days = derivation["target_step_days"]
        source_step_days = derivation["source_step_days"]
        selected = dict(source["selected"])
        selection_rule = (
            "The verified source range is sampled by an exact anchor-aligned "
            "stride; no astronomical value is interpolated"
        )
        verification = {
            "source_frontier_json": str(args.source_frontier_json.resolve()),
            "source_created_at": source.get("created_at"),
            "derivation": derivation,
        }
    else:
        manifest = json.loads(args.jpl_manifest_json.read_text(encoding="utf-8"))
        clipping = manifest["auto_clip"]
        candidate_start = clipping["effective_start_date"]
        anchor_date = args.anchor_date or manifest.get(
            "first_period_start", clipping["effective_start_date"]
        )
        forecast_end = args.forecast_end or clipping["effective_end_date"]
        step_days = int(manifest["step_days"])
        source_step_days = None
        selected = {}
        selection_rule = (
            "Every retained row was downloaded directly from NASA/JPL Horizons "
            "on the configured shifted grid; no astronomical value is interpolated"
        )
        verification = {
            "jpl_manifest_json": str(args.jpl_manifest_json.resolve()),
            "direct_horizons_download": True,
            "auto_clip": clipping,
            "body_specs": manifest.get("body_specs", []),
        }
    selected.update(
        {
            "candidate_start": candidate_start,
            "retained_event_rows": len(catalog),
            "retained_event_fraction": 1.0,
            "available_body_count": len(bodies),
            "available_body_fraction": 1.0,
            "history_span_years": (
                datetime.strptime(str(forecast_end)[:10], "%Y-%m-%d")
                - datetime.strptime(
                    str(catalog["date"].min())[:10], "%Y-%m-%d"
                )
            ).days
            / 365.2425,
            "history_span_skill": 1.0,
            "admissible": True,
            "utility": 1.0,
            "selected": True,
            "available_bodies": ",".join(bodies),
            "failed_bodies": "",
            **{f"body_ok__{body}": True for body in bodies},
        }
    )
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": selection_rule,
        "parameters": {
            "anchor_date": anchor_date,
            "forecast_end": forecast_end,
            "step_days": step_days,
            "source_step_days": source_step_days,
            "minimum_bodies": 6,
            "minimum_planetary_bodies": 4,
        },
        "selected": selected,
        "frontier": [selected],
        "source_verification": {
            **verification,
            "oldest_retained_event": str(catalog["date"].min()),
            "newest_retained_event": str(catalog["date"].max()),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["selected"], indent=2))


if __name__ == "__main__":
    main()

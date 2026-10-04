#!/usr/bin/env python3
"""Verify that V22 timing and location use the identical frozen events."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    results = project / "05_results"
    summary = json.loads((results / "summary.json").read_text())
    timing = pd.read_csv(results / "timing_validation_window_predictions.csv")
    timing = timing.loc[timing.group == "frozen_audit"]
    location = pd.read_csv(results / "location_frozen_audit_ensemble.csv")
    prepared = pd.read_csv(results / "prepared_weekly_dataset.csv")
    forecast = pd.read_csv(results / "forecast_weekly_aug_sep_2026.csv")
    expected = summary["leakage_contract"]["frozen_timing_audit_events"]
    timing_events = timing.event_slot.drop_duplicates().astype(str).tolist()
    location_events = location.event_slot.astype(str).tolist()
    event_rows = prepared.loc[prepared.timing_target == 1]
    bounds = summary["data"]["target_region_bounds"]
    checks = {
        "same_frozen_events_timing_location": timing_events == expected == location_events,
        "four_frozen_events": len(expected) == 4,
        "nine_rows_per_timing_window": timing.groupby("event_slot").size().eq(9).all(),
        "all_windows_are_minus4_to_plus4": all(group.window_position.tolist() == list(range(-4, 5)) for _, group in timing.groupby("event_slot", sort=False)),
        "one_event_center_per_window": timing.groupby("event_slot").is_event_slot.sum().eq(1).all(),
        "ten_independent_target_events": len(event_rows) == 10,
        "all_targets_inside_region": bool(
            event_rows.event_latitude.between(bounds["latitude_min"], bounds["latitude_max"]).all()
            and event_rows.event_longitude.between(bounds["longitude_min"], bounds["longitude_max"]).all()
        ),
        "forecast_has_nine_slots": len(forecast) == 9,
        "no_august_observations_used": summary["cutoff"]["august_seismic_observations_used"] == 0,
        "composite_png_exists": (results / "hokkaido_validation_location_forecast_composite.png").exists(),
        "composite_data_exists": (results / "validation_composite_data.json").exists(),
    }
    checks = {key: bool(value) for key, value in checks.items()}
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "region_bounds": bounds,
        "frozen_events_shared_by_timing_and_location": expected,
        "timing_gate": summary["timing"]["gate_status"],
        "location_gate": summary["location_conditional_on_timing_peak"]["gate_status"],
    }
    output = project / "02_audit/regional_final_verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

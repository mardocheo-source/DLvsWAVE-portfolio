#!/usr/bin/env python3
"""Fail-closed artifact and epoch-contract checks for the V21 weekly run."""
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
    manifest = json.loads((project / "00_config/jpl_manifest.json").read_text())
    summary = json.loads((project / "05_results/summary.json").read_text())
    requested = pd.read_csv(project / "00_config/period_starts.csv")
    raw = pd.read_csv(project / "01_inputs/fresh_weekly_astro_float.csv", low_memory=False)
    sanitized = pd.read_csv(project / "01_inputs/fresh_weekly_astro_sanitized.csv", low_memory=False)
    forecast = pd.read_csv(project / "05_results/forecast_weekly_aug_sep_2026.csv")
    body_specs = manifest.get("body_specs", [])
    checks = {
        "all_21_bodies_present": len(body_specs) == 21,
        "all_body_epochs_verified": bool(body_specs) and all(row.get("epoch_alignment_verified") is True for row in body_specs),
        "maximum_epoch_error_within_tolerance": bool(body_specs) and max(float(row.get("maximum_epoch_error_days", 1)) for row in body_specs) <= 1e-8,
        "jst_epoch_offset_exact": float(manifest.get("epoch_offset_hours_from_labelled_start", 999)) == -9.0,
        "raw_dates_equal_requested_dates": raw.date.astype(str).tolist() == requested.date.astype(str).tolist(),
        "sanitized_dates_equal_raw_dates": sanitized.date.astype(str).tolist() == raw.date.astype(str).tolist(),
        "forecast_has_nine_slots": len(forecast) == 9,
        "forecast_starts_august_1": str(forecast.slot_start_jst.iloc[0]) == "2026-08-01",
        "forecast_ends_september_26_slot": str(forecast.slot_start_jst.iloc[-1]) == "2026-09-26",
        "no_august_observations_used": int(summary["cutoff"]["august_seismic_observations_used"]) == 0,
        "timing_peak_reported": bool(summary["timing"].get("peak_slot_start_jst")),
        "most_likely_zone_reported": bool(summary["location_conditional_on_timing_peak"].get("most_likely_zone")),
        "frozen_timing_audit_has_four_events": len(summary["leakage_contract"].get("frozen_timing_audit_events", [])) == 4,
        "frozen_hard_negatives_excluded": summary["leakage_contract"].get("frozen_non_japan_controls_excluded_from_final_training") is True,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "maximum_epoch_error_days": max(float(row.get("maximum_epoch_error_days", 1)) for row in body_specs) if body_specs else None,
        "timing_gate_status": summary["timing"]["gate_status"],
        "location_gate_status": summary["location_conditional_on_timing_peak"]["gate_status"],
    }
    path = project / "02_audit/final_verification.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

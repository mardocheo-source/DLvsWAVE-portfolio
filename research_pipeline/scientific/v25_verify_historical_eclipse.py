#!/usr/bin/env python3
"""Verify V25 historical, ephemeris, eclipse, split and result consistency."""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import torch


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    inputs = project / "01_inputs"
    audit_dir = project / "02_audit"
    results = project / "05_results"
    audit_dir.mkdir(parents=True, exist_ok=True)

    catalog_audit = read_json(audit_dir / "catalog_period_audit.json")
    eclipse_audit = read_json(audit_dir / "eclipse_feature_audit.json")
    sanitization = read_json(audit_dir / "sanitization.json")
    manifest = read_json(project / "00_config/jpl_manifest.json")
    summary = read_json(results / "summary.json")

    targets = pd.read_csv(inputs / "corridor_targets_m79_deep_history.csv")
    targets["slot_start"] = pd.to_datetime(targets.slot_start)
    master = pd.read_csv(inputs / "deep_history_weekly_astro_eclipses.csv", low_memory=False)
    master["date"] = pd.to_datetime(master.date)
    eclipse_columns = [name for name in master.columns if name.startswith("eclipse:")]
    body_probe = pd.read_csv(audit_dir / "jpl_body_probe_1611_2026.csv")
    primary_probe = body_probe.loc[body_probe.primary_model_use.eq("yes")]

    selections = pd.read_csv(results / "nested_outer_selections.csv")
    timing = pd.read_csv(results / "timing_ensemble_fold_metrics.csv")
    windows = pd.read_csv(results / "timing_validation_window_predictions.csv")
    location = pd.read_csv(results / "location_frozen_audit_ensemble.csv")
    ablations = pd.read_csv(results / "final_body_field_ablation_summary.csv")

    expected_validation = set(targets.slot_start.tail(3))
    timing_slots = set(pd.to_datetime(timing.event_slot))
    window_slots = set(pd.to_datetime(windows.event_slot))
    location_slots = set(pd.to_datetime(location.event_slot))
    summary_slots = set(pd.to_datetime(summary["leakage_contract"]["reporting_validation_events"]))
    expected_train_counts = [12, 13, 14]
    reported_train_counts = selections.train_positive_event_count.astype(int).tolist()

    target_eclipse = targets[["id", "event_name", "slot_start", "mag", "location_eligible"]].merge(
        master[["date", *eclipse_columns]], left_on="slot_start", right_on="date", how="left", validate="one_to_one"
    ).drop(columns="date")
    target_eclipse.to_csv(audit_dir / "target_eclipse_week_audit.csv", index=False)

    body_specs = manifest.get("body_specs", [])
    selected_features = summary["search"].get("final_selected_features", [])
    eclipse_field_values = set(
        ablations.loc[ablations.dimension.eq("field_group"), "value"].astype(str)
    )
    body_values = set(ablations.loc[ablations.dimension.eq("body_group"), "value"].astype(str))
    timing_checks = summary["timing"]["gate_checks"]
    location_checks = summary["location_conditional_on_timing_peak"]["gate_checks"]
    expected_timing_status = "PASS" if all(timing_checks.values()) else "FAIL_REPORTED_NOT_VALIDATED"
    expected_location_status = "PASS" if all(location_checks.values()) else "FAIL_REPORTED_WITH_LOW_CONFIDENCE"

    checks = {
        "catalog_build_audit_passed": catalog_audit.get("status") == "PASS",
        "fifteen_independent_timing_targets": len(targets) == 15 and targets.slot_start.nunique() == 15,
        "four_historical_timing_only_targets": int(targets.source.eq("official_historical_attachment").sum()) == 4 and int(targets.location_eligible.eq(0).sum()) == 4,
        "eleven_location_eligible_targets": int(targets.location_eligible.eq(1).sum()) == 11,
        "historical_coordinates_not_imputed": bool(targets.loc[targets.location_eligible.eq(0), ["latitude", "longitude"]].isna().all().all()),
        "all_events_inside_assigned_week": bool(targets.event_inside_slot.astype(str).str.lower().eq("true").all()),
        "all_target_weeks_present_in_master": set(targets.slot_start).issubset(set(master.date)),
        "master_has_1339_unique_week_rows": len(master) == 1339 and master.date.nunique() == 1339,
        "jpl_sanitization_passed_without_drops": sanitization.get("status") == "PASS" and not sanitization.get("dropped_columns"),
        "eleven_primary_bodies_pass_endpoint_probe": len(primary_probe) == 11 and primary_probe.probe_1611_2026.eq("PASS").all(),
        "eleven_manifest_bodies_exact_epoch_aligned": len(body_specs) == 11 and all(item.get("epoch_alignment_verified") and item.get("maximum_epoch_error_days") == 0.0 for item in body_specs),
        "eclipse_calculation_audit_passed": eclipse_audit.get("status") == "PASS",
        "seventeen_complete_eclipse_features": len(eclipse_columns) == 17 and not master[eclipse_columns].isna().any().any(),
        "same_three_validation_events_for_timing_and_location": timing_slots == window_slots == location_slots == summary_slots == expected_validation,
        "outer_training_positive_counts_are_12_13_14": reported_train_counts == expected_train_counts,
        "final_forecast_fit_uses_all_15_targets": int(summary["timing"]["final_fit_counts"]["train_positive_event_count"]) == 15,
        "validation_is_smaller_than_development": int(summary["data"]["validation_event_count"]) == 3 < int(summary["data"]["development_event_count"]),
        "all_selected_start_years_are_1611": bool(selections.start_year.astype(int).eq(1611).all()) and int(summary["search"]["final_config"]["start_year"]) == 1611,
        "eclipse_controls_were_screened": {"all", "no_eclipse", "eclipse_only"}.issubset(eclipse_field_values),
        "all_deep_body_ablation_groups_were_screened": len(body_values) >= 8,
        "selected_features_are_recorded": len(selected_features) > 0 and len(selected_features) <= int(summary["search"]["final_allowed_feature_count"]),
        "training_signal_not_zeroed": float(summary["timing"]["training_metrics"]["quality"]) >= 0.55,
        "cpu_run_recorded_without_xpu": summary["compute"]["deep_device"] == "cpu" and summary["compute"]["kan_device"] == "cpu" and summary["compute"]["xpu_used"] is False,
        "timing_gate_status_matches_checks": summary["timing"]["gate_status"] == expected_timing_status,
        "location_gate_status_matches_checks": summary["location_conditional_on_timing_peak"]["gate_status"] == expected_location_status,
        "composite_graph_exists": (results / "historical_eclipse_validation_location_forecast_composite.png").is_file() and (results / "historical_eclipse_validation_location_forecast_composite.png").stat().st_size > 0,
    }
    checks = {name: bool(value) for name, value in checks.items()}

    xpu_available = bool(hasattr(torch, "xpu") and torch.xpu.is_available())
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "meaning": "PASS verifies pipeline consistency and provenance; timing/location scientific gates remain separate and must not be promoted after failure.",
        "checks": checks,
        "event_counts": {
            "timing_targets": len(targets),
            "historical_timing_only": int(targets.location_eligible.eq(0).sum()),
            "location_eligible": int(targets.location_eligible.eq(1).sum()),
            "development": int(summary["data"]["development_event_count"]),
            "validation": int(summary["data"]["validation_event_count"]),
            "outer_fit_positive_counts": reported_train_counts,
            "final_fit": summary["timing"]["final_fit_counts"],
        },
        "astronomy": {
            "primary_bodies": primary_probe.body_name.tolist(),
            "jpl_feature_count": int(manifest["astro_column_count"]),
            "eclipse_feature_count": len(eclipse_columns),
            "earthquake_weeks_with_any_global_eclipse": int(target_eclipse["eclipse:any_global|op:any_in_week"].sum()),
        },
        "compute": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cpu_threads": torch.get_num_threads(),
            "xpu_available": xpu_available,
            "xpu_count": int(torch.xpu.device_count()) if hasattr(torch, "xpu") else 0,
            "cuda_available": bool(torch.cuda.is_available()),
            "run_device": "cpu",
        },
        "model_gate_status": {
            "timing": summary["timing"]["gate_status"],
            "location": summary["location_conditional_on_timing_peak"]["gate_status"],
        },
    }
    (audit_dir / "final_verification.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

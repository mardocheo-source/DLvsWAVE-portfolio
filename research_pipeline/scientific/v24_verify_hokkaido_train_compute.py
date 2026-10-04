#!/usr/bin/env python3
"""Verify V24b split, event-slot alignment, compute device and output consistency."""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import v21_weekly_recency_forecast as core  # noqa: E402
import v23_hokkaido_extended_search as ext  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--source-dir", required=True)
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    source = Path(args.source_dir).resolve()
    results = project / "05_results"
    audit_dir = project / "02_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    summary = json.loads((results / "summary.json").read_text())
    upstream = json.loads((source / "02_audit/final_verification.json").read_text())
    selections = pd.read_csv(results / "nested_outer_selections.csv")
    timing = pd.read_csv(results / "timing_ensemble_fold_metrics.csv")
    windows = pd.read_csv(results / "timing_validation_window_predictions.csv")
    location = pd.read_csv(results / "location_frozen_audit_ensemble.csv")
    master = pd.read_csv(source / "01_inputs/fresh_weekly_astro_sanitized.csv", usecols=["date"])
    master_dates = set(pd.to_datetime(master.date))

    japan = core.load_catalog(source / "01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv")
    inside = japan.latitude.between(ext.REGION[0], ext.REGION[1]) & japan.longitude.between(ext.REGION[2], ext.REGION[3])
    targets = core.strongest_by_slot(japan.loc[(japan.mag >= 7.9) & inside].copy())
    target_slots = [pd.Timestamp(value) for value in targets.slot_start]
    validation_slots = [pd.Timestamp(value) for value in target_slots[-2:]]
    expected_training_counts = [target_slots.index(slot) for slot in validation_slots]

    event_catalog = targets[["id", "time_utc", "slot_start", "mag", "latitude", "longitude", "depth", "place"]].copy()
    event_catalog["time_jst"] = event_catalog.time_utc.dt.tz_convert(core.JST)
    event_catalog["slot_end_exclusive_jst"] = event_catalog.slot_start + pd.Timedelta(days=7)
    event_catalog["event_inside_assigned_slot"] = (
        event_catalog.time_jst.dt.tz_localize(None).ge(event_catalog.slot_start)
        & event_catalog.time_jst.dt.tz_localize(None).lt(event_catalog.slot_end_exclusive_jst)
    )
    event_catalog["slot_present_in_astro_master"] = event_catalog.slot_start.isin(master_dates)
    event_catalog.to_csv(audit_dir / "target_event_slot_audit.csv", index=False)

    timing_slots = set(pd.to_datetime(timing.event_slot))
    window_slots = set(pd.to_datetime(windows.event_slot))
    location_slots = set(pd.to_datetime(location.event_slot))
    summary_slots = set(pd.to_datetime(summary["leakage_contract"]["reporting_validation_events"]))
    reported_train_counts = selections.train_positive_event_count.astype(int).tolist()
    source_code = (HERE / "v23_hokkaido_extended_search.py").read_text()
    xpu_available = bool(hasattr(torch, "xpu") and torch.xpu.is_available())
    xpu_count = int(torch.xpu.device_count()) if hasattr(torch, "xpu") else 0

    checks = {
        "upstream_astronomical_epoch_audit_passed": upstream.get("status") == "PASS" and upstream.get("maximum_epoch_error_days") == 0.0,
        "ten_independent_regional_target_slots": len(targets) == 10 and targets.slot_start.nunique() == 10,
        "all_event_times_inside_assigned_jst_slots": bool(event_catalog.event_inside_assigned_slot.all()),
        "all_target_slots_present_in_astro_master": bool(event_catalog.slot_present_in_astro_master.all()),
        "same_two_validation_events_for_timing_windows_location_and_summary": timing_slots == window_slots == location_slots == summary_slots == set(validation_slots),
        "outer_training_positive_counts_are_8_and_9": reported_train_counts == expected_training_counts == [8, 9],
        "final_forecast_fit_uses_all_ten_targets": summary["timing"]["final_fit_counts"]["train_positive_event_count"] == 10,
        "validation_is_smaller_than_development": summary["data"]["validation_event_count"] == 2 < summary["data"]["development_event_count"],
        "all_selected_start_years_preserve_1931_event": bool((selections.start_year <= 1930).all()) and int(summary["search"]["final_config"]["start_year"]) <= 1930,
        "training_signal_not_zeroed": float(summary["timing"]["training_metrics"]["quality"]) >= 0.55,
        "deep_and_kan_configured_for_cpu": source_code.count('device="cpu"') >= 2 and summary["compute"]["deep_device"] == "cpu" and summary["compute"]["kan_device"] == "cpu",
        "summary_records_no_xpu_use": summary["compute"]["xpu_used"] is False,
        "timing_failure_reported_without_promotion": summary["timing"]["gate_status"] == "FAIL_REPORTED_NOT_VALIDATED" and not bool(timing.exact_peak.any()),
        "location_failure_reported_without_promotion": summary["location_conditional_on_timing_peak"]["gate_status"] == "FAIL_REPORTED_WITH_LOW_CONFIDENCE" and not bool(location.zone_hit.any()),
        "composite_graph_exists": (results / "hokkaido_validation_location_forecast_composite.png").stat().st_size > 0,
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "meaning": "PASS means pipeline consistency only; forecast model gates are evaluated separately",
        "checks": checks,
        "event_counts": {
            "total_regional_targets": len(targets),
            "development_targets": int(summary["data"]["development_event_count"]),
            "validation_targets": int(summary["data"]["validation_event_count"]),
            "outer_fit_positive_counts": reported_train_counts,
            "outer_fit_total_rows": selections.train_row_count.astype(int).tolist(),
            "outer_fit_negative_rows": selections.train_negative_row_count.astype(int).tolist(),
            "final_fit": summary["timing"]["final_fit_counts"],
        },
        "compute": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cpu_threads": torch.get_num_threads(),
            "xpu_available": xpu_available,
            "xpu_count": xpu_count,
            "cuda_available": torch.cuda.is_available(),
            "run_device": "cpu",
        },
        "validation_events": event_catalog.tail(2).to_dict(orient="records"),
        "model_gate_status": {
            "timing": summary["timing"]["gate_status"],
            "location": summary["location_conditional_on_timing_peak"]["gate_status"],
        },
    }
    core.write_json(audit_dir / "final_verification.json", payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

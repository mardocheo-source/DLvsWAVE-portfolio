#!/usr/bin/env python3
"""Artifact and disclosure checks for the parameter-driven V14 pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader


PROJECT = Path(
    os.environ.get(
        "DLVSWAVE_PROJECT_DIR",
        str(Path(__file__).resolve().parents[1]),
    )
).expanduser().resolve()


def read_json(relative: str) -> dict:
    return json.loads((PROJECT / relative).read_text(encoding="utf-8"))


def main() -> None:
    config = read_json("00_config/pipeline_request.json")
    catalog = pd.read_csv(PROJECT / "01_inputs/mega_quakes_of_japan_v14.csv")
    full = pd.read_csv(PROJECT / "01_inputs/timing_master_full.csv", low_memory=False)
    compact = pd.read_csv(PROJECT / "01_inputs/timing_master.csv", low_memory=False)
    controls = pd.read_csv(PROJECT / "02_audit/world_non_japan_hard_negatives.csv")
    compact_trials = pd.read_csv(PROJECT / "02_master_search/compact_k_factor_trials.csv")
    compact_selection = read_json("02_master_search/compact_k_factor_selection.json")
    timing = read_json("05_ensemble/timing/final_summary.json")
    metric = read_json(
        "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_summary.json"
    )
    randomized = read_json("07_randomized_control/timing/summary.json")
    historical = read_json("07_historical_record_shuffle/timing/summary.json")
    history_audit = read_json("06_report/forecast_history_comparison_audit.json")
    location = read_json("05_ensemble/location_zone_summary.json")
    reliability = read_json("05_ensemble/location_reliability_assessment.json")
    report_check = read_json("06_report/self_check_v14_standard.json")
    forecast = pd.read_csv(
        PROJECT
        / "05_ensemble/timing/metric_specialist_fusion/metric_specialist_fusion_forecast.csv"
    )
    validation = pd.read_csv(PROJECT / "05_ensemble/timing/validation_predictions.csv")
    checks: dict[str, bool] = {}

    floor = float(config["japan_target_minimum_magnitude"])
    checks["unified_japan_floor_is_applied"] = bool(
        pd.to_numeric(catalog["mag"], errors="coerce").ge(floor).all()
        and not catalog["date"].astype(str).str.startswith("2003-").any()
    )
    checks["catalog_matches_m83_definition"] = len(catalog) == 11
    full_dates = pd.to_datetime(full["date"], format="%Y-%m-%d")
    checks["full_master_exact_180_day_grid"] = bool(
        set(full_dates.diff().dropna().dt.days) == {config["interval_days"]}
    )
    checks["forecast_has_seven_complete_intervals"] = bool(
        len(forecast) == 7
        and set(pd.to_datetime(forecast["date"]).diff().dropna().dt.days)
        == {config["interval_days"]}
        and pd.Timestamp(forecast.iloc[-1]["slot_end_inclusive"])
        >= pd.Timestamp(config["forecast_end"])
    )
    expected_trials = (
        len(config["compact_search"]["k_events"])
        * len(config["compact_search"]["k_between"])
        * len(config["compact_search"]["proximity_fractions"])
    )
    checks["all_configured_k_factor_combinations_were_tested"] = bool(
        len(compact_trials) == expected_trials
        and compact_selection["candidate_count"] == expected_trials
    )
    validation_controls = controls[controls["scope"].str.startswith("validation_fold_")]
    checks["world_controls_cover_training_and_both_validation_folds"] = bool(
        controls["scope"].eq("training").sum()
        == config["hard_negatives"]["training_count"]
        and len(validation_controls) == 2
        and validation_controls["scope"].nunique() == 2
    )
    checks["hard_negative_model_values_are_neutral"] = bool(
        controls["model_timing_target"].eq(0).all()
        and controls["model_event_mag"].eq(0).all()
        and controls["model_event_latitude"].eq(0).all()
        and controls["model_event_longitude"].eq(0).all()
        and compact.loc[compact["hard_negative_control"].eq(1), "timing_target"].eq(0).all()
    )
    checks["validation_graph_contains_named_world_controls"] = bool(
        validation["hard_negative_control"].fillna(0).astype(int).sum() == 2
        and validation.loc[
            validation["hard_negative_control"].fillna(0).astype(int).eq(1),
            "hard_negative_places",
        ].notna().all()
    )
    checks["timing_fusion_promotion_matches_quality_and_control_gate"] = bool(
        metric["status"] == "PASS"
        and metric["selected_trial"]["validation_quality_mean"]
        >= config["fusion"]["minimum_validation_mean"]
        and metric["selected_trial"]["validation_quality_worst"]
        >= config["fusion"]["minimum_validation_worst"]
        and metric["selected_trial"]["exact_peak_count"] == 2
        and metric["selected_trial"]["hard_negative_below_event_count"] == 2
    )
    history_quality = historical["validation_metrics"]["quality_higher_is_better"]
    null_quality = randomized["validation_metrics"]["quality_higher_is_better"]
    checks["historical_order_line_obeys_automatic_gate"] = bool(
        (
            history_audit["status"] == "INCLUDED"
            and history_audit["automatic_gate_pass"]
            and history_quality >= history_audit["minimum_validation_quality"]
            and (
                history_quality > null_quality
                if history_audit["require_above_randomized_labels"]
                else True
            )
        )
        or (
            history_audit["status"] == "EXCLUDED"
            and not history_audit["automatic_gate_pass"]
        )
    )
    checks["location_holdout_is_multizone_but_small_sample_capped"] = bool(
        location["validation_design"]["observed_distinct_zones"] == 2
        and reliability["status"] == "LIMITED"
        and np.isclose(
            reliability["applied_reliability_weight"],
            config["location"]["small_sample_reliability_cap"],
        )
    )
    checks["standard_report_self_check_passes"] = report_check["status"] == "PASS"
    pdf = PROJECT / "06_report/V14_PROFESSIONAL_REPORT.pdf"
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    checks["professional_report_is_complete"] = bool(len(reader.pages) >= 35)
    checks["requested_causation_sentence_is_preserved"] = (
        "Astronomical associations in this experiment it's not enough to establish causation."
        in text
    )

    failures = [name for name, passed in checks.items() if not passed]
    payload = {
        "status": "PASS" if not failures else "FAIL",
        "project": str(PROJECT),
        "check_count": len(checks),
        "failed_checks": failures,
        "checks": checks,
        "summary": {
            "catalog_events": len(catalog),
            "positive_bins": int(full["timing_target"].sum()),
            "compact_rows": len(compact),
            "k_factor_trials": len(compact_trials),
            "training_hard_negative_events": int(controls["scope"].eq("training").sum()),
            "validation_hard_negative_events": len(validation_controls),
            "timing_validation_gate": timing["validation_gate"],
            "metric_fusion_status": metric["status"],
            "historical_order_quality": history_quality,
            "randomized_label_quality": null_quality,
            "location_reliability_weight": reliability["applied_reliability_weight"],
            "forecast_rows": len(forecast),
            "report_pages": len(reader.pages),
        },
    }
    destination = PROJECT / "06_report/self_check_v14.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

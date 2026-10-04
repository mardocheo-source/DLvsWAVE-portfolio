#!/usr/bin/env python3
"""Check V19 exact-start search, timing controls, budgets and report integrity."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    request = read_json(project / "00_config/pipeline_request.json")
    report_request = read_json(project / "00_config/standard_report_request.json")
    master_audit = read_json(
        project / "02_master_search/master_search_selection.json"
    )
    compact_selection = read_json(
        project / "02_master_search/compact_k_factor_selection.json"
    )
    compact_trials = pd.read_csv(
        project / "02_master_search/compact_k_factor_trials.csv"
    )
    safe = read_json(project / "01_inputs/v4_native_safe_features.json")
    full = pd.read_csv(project / "01_inputs/timing_master_full.csv", low_memory=False)
    compact = pd.read_csv(project / "01_inputs/timing_master.csv", low_memory=False)
    validation = pd.read_csv(
        project
        / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_validation_predictions.csv"
    )
    forecast = pd.read_csv(
        project
        / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_fusion_forecast.csv"
    )
    controls = pd.read_csv(project / "02_audit/world_non_japan_hard_negatives.csv")
    one_shot = read_json(project / "05_ensemble/timing/one_shot/summary.json")
    one_shot_validation = pd.read_csv(
        project / "05_ensemble/timing/one_shot/validation.csv"
    )
    one_shot_forecast = pd.read_csv(
        project / "05_ensemble/timing/one_shot/forecast.csv"
    )
    threshold = read_json(
        project
        / "05_ensemble/timing/validation_threshold_projection/validation_peak_threshold.json"
    )
    discrete = pd.read_csv(
        project
        / "05_ensemble/timing/validation_threshold_projection/discretized_forecast.csv"
    )
    diagnostics = read_json(project / "06_report/v19_diagnostics.json")
    equal_budget = pd.read_csv(
        project / "03_feature_research/final_attempt_equal_time_quality.csv"
    )

    report_check = read_json(
        project
        / "06_report"
        / f"self_check_{report_request['report_file_tag']}.json"
    )
    pdf = project / "06_report" / f"{report_request['report_basename']}.pdf"
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    checks: dict[str, bool] = {}
    checks["configured_v19_90_day_pipeline"] = bool(
        str(request["pipeline_version"]).lower() == "v19"
        and request["interval_days"] == 90
    )
    anchor = date.fromisoformat(request["anchor_date"])
    focus_start = anchor - timedelta(days=90)
    checks["fixed_august_31_focus_slot_and_september_successor"] = bool(
        focus_start == date(2026, 6, 3)
        and focus_start + timedelta(days=89) == date(2026, 8, 31)
        and anchor == date(2026, 9, 1)
    )
    master_dates = [
        date.fromisoformat(value[:10]) for value in full["date"].astype(str)
    ]
    checks["master_is_exact_90_day_start_value_grid"] = bool(
        all(b - a == timedelta(days=90) for a, b in zip(master_dates, master_dates[1:]))
        and request.get("interval_features") is None
        and request["feature_controls"]["interval_operators"] == []
        and request["feature_controls"]["sampling_position"] == "slot_start"
    )
    feature_names = safe["features"]
    checks["raw_start_features_include_calendar_and_jpl_moon_phase"] = bool(
        request["preprocessing"]["quantile_bins"] == 0
        and not any("|op:min" in name or "|op:median" in name or "|op:max" in name for name in feature_names)
        and "calendar_month" in feature_names
        and "calendar_month_sin" in feature_names
        and "calendar_month_cos" in feature_names
        and "moon_phase_fraction_at_slot_start" in feature_names
        and "moon_elongation_cos_at_slot_start" in feature_names
    )
    calendar = master_audit["calendar_contract"]
    checks["gregorian_calendar_contract_is_explicit_and_unambiguous"] = bool(
        calendar["system"] == "proleptic_gregorian"
        and calendar["all_master_dates_after_gregorian_reform"]
        and "proleptic Gregorian" in calendar["date_arithmetic"]
    )

    configured_starts = request["compact_search"]["history_start_dates"]
    expected_trials = (
        len(configured_starts)
        * len(request["compact_search"]["k_events"])
        * len(request["compact_search"]["k_between"])
        * len(request["compact_search"]["proximity_fractions"])
    )
    checks["exact_start_event_and_k_factors_were_searched_jointly"] = bool(
        set(compact_trials["history_start_date"].astype(str)) == set(configured_starts)
        and len(compact_trials) <= expected_trials
        and len(compact_trials) >= expected_trials - compact_selection["skipped_candidate_count"]
        and compact_selection["history_start_search_is_exact_event_aligned"]
        and compact_selection["history_start_dates_tested"] == configured_starts
        and "oldest" not in compact_selection["selection_rule"].lower()
    )
    selected_start = compact_selection["selected"]["history_start_date"]
    checks["materialized_compact_master_obeys_selected_exact_start"] = bool(
        selected_start in configured_starts
        and compact.loc[compact["is_forecast"].eq(0), "date"].astype(str).min()
        >= selected_start
        and float(compact_selection["selected"]["history_start_event_magnitude"])
        >= 7.9
    )

    configured_slots = set(request["timing"]["validation_slots"])
    holdouts = validation.loc[validation["designated_holdout"].eq(1)]
    checks["three_distinct_m79_timing_holdouts_are_present"] = bool(
        len(configured_slots) == 3
        and validation["step"].nunique() == 3
        and len(holdouts) == 3
        and set(holdouts["date"].astype(str)) == configured_slots
        and holdouts["event_mag"].ge(7.9).all()
    )
    checks["training_and_timing_validation_thresholds_are_m79"] = bool(
        request["japan_training_minimum_magnitude"]
        == request["japan_timing_validation_minimum_magnitude"]
        == 7.9
    )
    checks["non_japan_hard_negatives_are_neutral_and_replayed"] = bool(
        request["timing"]["hard_negative_replay"] >= 2
        and controls["model_timing_target"].eq(0).all()
        and controls["model_event_mag"].eq(0).all()
        and controls["model_event_latitude"].eq(0).all()
        and controls["model_event_longitude"].eq(0).all()
        and compact.loc[compact["hard_negative_control"].eq(1), "timing_target"].eq(0).all()
    )
    checks["contextual_forecast_has_six_complete_90_day_bins"] = bool(
        len(forecast) == 6
        and forecast["date"].astype(str).tolist()[3] == "2026-06-03"
        and forecast["slot_end_inclusive"].astype(str).tolist()[3] == "2026-08-31"
        and np.isfinite(
            forecast["contextual_promoted_score_not_probability"].to_numpy(float)
        ).all()
    )
    checks["one_shot_real_label_validation_and_forecast_are_complete"] = bool(
        one_shot["status"] == "COMPLETE"
        and one_shot["training_mode"] == "one_shot"
        and one_shot["validation_selection_uses_holdout_scores"] is False
        and one_shot["validation_events"] == 3
        and one_shot_validation["actual"].sum() == 3
        and len(one_shot_forecast) == 6
    )
    runtime_rows = list(one_shot["validation_member_runtimes"].values()) + list(
        one_shot["forecast_member_runtimes"].values()
    )
    time_limit = float(request["timing"]["final_attempt_time_limit_seconds"])
    checks["every_one_shot_final_member_obeys_hard_time_limit"] = bool(
        time_limit > 0
        and runtime_rows
        and all(row["finished_within_time_limit"] for row in runtime_rows)
        and all(row["time_limit_seconds"] == time_limit for row in runtime_rows)
        and all(row["fit_and_inference_seconds"] <= time_limit for row in runtime_rows)
    )
    checks["equal_time_quality_table_and_composite_chart_exist"] = bool(
        len(equal_budget) >= 7
        and equal_budget["time_budget_seconds"].eq(time_limit).all()
        and np.isfinite(equal_budget["quality_reached_under_equal_time_cap"]).all()
        and diagnostics["final_attempt_time_budget"]["time_budget_seconds"] == time_limit
    )
    checks["weak_peak_operator_is_preserved"] = bool(
        threshold["weak_peak_operator"]["enabled"]
        and threshold["weak_peak_operator"]["minimum_retention"]
        == request["validation_threshold_projection"]["weak_peak_minimum_retention"]
    )
    checks["validation_only_threshold_is_projected_unchanged_to_forecast"] = bool(
        threshold["selection_uses_validation_only"]
        and threshold["forecast_was_not_used_for_threshold_selection"]
        and threshold["validation_event_count"] == 3
        and threshold["selected_metrics"]["event_recall"] >= 1.0
        and len(discrete) == len(forecast) == 6
        and discrete["validation_derived_threshold"].nunique() == 1
        and np.isclose(
            discrete["validation_derived_threshold"].iloc[0],
            threshold["selected_threshold"],
        )
    )

    for name in (
        "v19_training_start_search.png",
        "v19_final_attempt_time_budget.png",
        "v19_one_shot_timing.png",
    ):
        with Image.open(project / "06_report" / name) as image:
            checks[f"{name}_is_high_resolution"] = bool(
                image.width >= 5000
                and min(image.info.get("dpi", (0, 0))) >= report_request["dpi"] - 1
            )
    checks["professional_report_contains_v19_specific_sections"] = bool(
        report_check["status"] == "PASS"
        and len(reader.pages) >= report_request["minimum_pages"]
        and "exact historical training start sensitivity" in normalized_text
        and "budgeted final attempts" in normalized_text
        and "one shot timing validation and forecast" in normalized_text
        and "validation derived discrete threshold" in normalized_text
    )
    checks["requested_causation_sentence_is_preserved"] = (
        "Astronomical associations in this experiment it's not enough to establish causation."
        in text
    )

    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "results": {
            "selected_history_start": selected_start,
            "start_candidates": len(configured_starts),
            "completed_start_k_trials": len(compact_trials),
            "timing_holdouts": len(holdouts),
            "forecast_bins": len(forecast),
            "threshold": threshold["selected_threshold"],
            "report_pages": len(reader.pages),
        },
    }
    destination = project / "06_report/self_check_v19.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

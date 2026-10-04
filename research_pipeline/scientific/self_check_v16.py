#!/usr/bin/env python3
"""Validate shifted-grid V16 timing, leakage and magnitude-calibration claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()

    request = read_json(project / "00_config/pipeline_request.json")
    report_request = read_json(
        project / "00_config/standard_report_request.json"
    )
    catalog = pd.read_csv(project / "01_inputs/mega_quakes_of_japan_v16.csv")
    full = pd.read_csv(project / "01_inputs/timing_master_full.csv", low_memory=False)
    compact = pd.read_csv(project / "01_inputs/timing_master.csv", low_memory=False)
    controls = pd.read_csv(project / "02_audit/world_non_japan_hard_negatives.csv")
    compact_trials = pd.read_csv(
        project / "02_master_search/compact_k_factor_trials.csv"
    )
    compact_selection = read_json(
        project / "02_master_search/compact_k_factor_selection.json"
    )
    contextual_dir = project / request["contextual_fusion"]["output_directory"]
    contextual = read_json(
        contextual_dir / "contextual_fold_fusion_summary.json"
    )
    trace = read_json(Path(contextual["contribution_trace"]))
    validation = pd.read_csv(contextual["validation"]["path"])
    forecast = pd.read_csv(contextual["forecast"]["path"])
    magnitude = read_json(
        project
        / request["magnitude_recalibration"]["output_directory"]
        / "conditional_magnitude_summary.json"
    )
    magnitude_png = Path(magnitude["outputs"]["standalone_png"])
    primary = pd.read_csv(
        project / "05_ensemble/timing/forecast_primary_selection.csv"
    )
    location_audit = read_json(project / "02_audit/location_master_audit.json")
    location_reliability = read_json(
        project / "05_ensemble/location_reliability_assessment.json"
    )
    report_check = read_json(
        project
        / "06_report"
        / f"self_check_{report_request['report_file_tag']}.json"
    )
    pdf_path = project / "06_report" / f"{report_request['report_basename']}.pdf"
    reader = PdfReader(pdf_path)
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = " ".join(pdf_text.lower().split())

    checks: dict[str, bool] = {}
    checks["configured_v16_pipeline"] = str(
        request["pipeline_version"]
    ).lower().startswith("v16")
    floor = float(request["japan_target_minimum_magnitude"])
    checks["unified_japan_magnitude_floor_is_applied"] = bool(
        pd.to_numeric(catalog["mag"], errors="coerce").ge(floor).all()
        and validation.loc[validation["actual"].eq(1), "event_mag"].ge(floor).all()
    )
    full_dates = pd.to_datetime(full["date"], format="%Y-%m-%d")
    checks["master_is_exact_180_day_grid"] = bool(
        set(full_dates.diff().dropna().dt.days) == {int(request["interval_days"])}
    )
    expected_forecast_dates = ["2025-10-03", "2026-04-01", "2026-09-28"]
    checks["forecast_uses_exact_shifted_grid_and_requested_scope"] = bool(
        forecast["date"].astype(str).tolist() == expected_forecast_dates
        and str(forecast.iloc[-1]["slot_end_inclusive"]) == request["forecast_end"]
    )
    v15_forecast_path = (
        project.parent
        / "japan-m83plus-180d-2026-2028-contextual-v15/"
        "05_ensemble/timing/contextual_fold_fusion/contextual_fold_fusion_forecast.csv"
    )
    if v15_forecast_path.is_file():
        v15_forecast = pd.read_csv(v15_forecast_path)
        shift = (
            pd.Timestamp(forecast.iloc[0]["date"])
            - pd.Timestamp(v15_forecast.iloc[0]["date"])
        ).days
        checks["v16_origin_is_independently_shifted_from_v15"] = shift == -90
    else:
        checks["v16_origin_is_independently_shifted_from_v15"] = True

    expected_trials = (
        len(request["compact_search"]["k_events"])
        * len(request["compact_search"]["k_between"])
        * len(request["compact_search"]["proximity_fractions"])
    )
    checks["all_configured_master_k_factors_were_searched"] = bool(
        len(compact_trials) == expected_trials
        and int(compact_selection["candidate_count"]) == expected_trials
    )
    checks["world_hard_negatives_are_neutral_and_limited"] = bool(
        controls["model_timing_target"].eq(0).all()
        and controls["model_event_mag"].eq(0).all()
        and controls["model_event_latitude"].eq(0).all()
        and controls["model_event_longitude"].eq(0).all()
        and int((compact["hard_negative_control"] == 1).sum())
        <= int(request["hard_negatives"]["training_count"])
        + int(request["hard_negatives"]["validation_per_fold"])
        * len(request["timing"]["validation_slots"])
    )
    checks["post_origin_japan_events_never_leak_into_targets"] = bool(
        compact.loc[
            pd.to_datetime(compact["date"], format="mixed").ge(
                pd.Timestamp(request["forecast_start"])
            ),
            "timing_target",
        ].eq(0).all()
        and location_audit["forward_events_never_used_as_location_training_targets"]
        and int(location_audit["withheld_forward_event_rows"]) >= 1
    )
    checks["contextual_search_uses_independent_fold_combinations"] = bool(
        contextual["status"] == "PASS"
        and len(contextual["folds"]) == 2
        and contextual["folds"][0]["selected"]["weights"]
        != contextual["folds"][1]["selected"]["weights"]
    )
    checks["false_peaks_and_world_controls_pass"] = bool(
        contextual["validation"]["all_events_are_strict_local_peaks"]
        and contextual["validation"]["all_controls_below_event"]
        and int(contextual["validation"]["maximum_false_peak_count"]) == 0
    )
    relaxed = [
        item
        for fold in contextual["folds"]
        for item in fold["selected"].get("constraints_relaxed", [])
    ]
    checks["weak_peak_rescue_is_retained_and_relaxations_are_audited"] = bool(
        contextual["search"]["weak_peak_system_retained_in_search"]
        and any(fold["selected"]["weak_peak_rescue_applied"] for fold in contextual["folds"])
        and "minimum_weak_peak_retention" in relaxed
    )
    checks["target_randomization_has_zero_forecast_weight"] = bool(
        np.isclose(trace["target_label_randomized_contribution"], 0.0)
        and trace["checks"]["target_label_randomized_has_zero_weight"]
    )
    after = pd.Timestamp(
        report_request["forecast_peak_modes"]["first_peak_not_before"]
    )
    eligible = forecast.loc[
        pd.to_datetime(forecast["date"]).ge(after)
        & forecast["contextual_promoted_score_not_probability"].ge(
            float(report_request["forecast_peak_modes"]["first_occurrence_threshold"])
        )
    ]
    checks["primary_forecast_focus_respects_json_not_before_rule"] = bool(
        len(primary) == 1
        and not eligible.empty
        and str(primary.iloc[0]["date"]) == str(eligible.iloc[0]["date"])
        and str(primary.iloc[0]["date"]) == "2026-09-28"
    )
    focus = magnitude["focus_window"]
    checks["magnitude_result_is_explicitly_conditional"] = bool(
        magnitude["status"] == "COMPLETE_CONDITIONAL_NOT_EVENT_FORECAST"
        and "only if an additional target event occurs" in magnitude["conditional_statement"]
        and magnitude["score_semantics"].endswith("not a calibrated probability")
    )
    checks["magnitude_fit_uses_out_of_sample_and_completed_origin_anchors"] = bool(
        int(magnitude["calibration"]["anchor_count"]) >= 3
        and {row["anchor_kind"] for row in magnitude["calibration"]["anchors"]}
        == {"chronological holdout", "completed forecast-origin interval"}
        and any(
            row["event_id"] == "us6000rtdt"
            for row in magnitude["calibration"]["anchors"]
        )
    )
    checks["recent_events_are_context_not_training_targets"] = bool(
        {row["id"] for row in focus["observed_reference_events"]}
        >= {"us6000sri7", "us6000tgb9"}
        and np.isclose(float(focus["observed_floor_magnitude"]), 7.4)
    )
    checks["conditional_magnitude_numbers_are_finite_and_bounded"] = bool(
        np.isfinite(
            [
                focus["conditional_lower_magnitude"],
                focus["conditional_central_magnitude"],
                focus["conditional_upper_magnitude"],
            ]
        ).all()
        and focus["conditional_lower_magnitude"]
        <= focus["conditional_central_magnitude"]
        <= focus["conditional_upper_magnitude"]
        <= magnitude["calibration"]["maximum_allowed_magnitude"]
    )
    with Image.open(magnitude_png) as image:
        width, height = image.size
        png_dpi = image.info.get("dpi", (0, 0))
    checks["standalone_magnitude_png_is_high_resolution"] = bool(
        width >= 6000
        and height >= 3000
        and min(png_dpi) >= int(report_request["dpi"]) - 1
    )
    checks["location_is_multi_zone_but_reliability_capped"] = bool(
        int(location_reliability["distinct_validation_zones"]) >= 2
        and float(location_reliability["applied_reliability_weight"])
        <= float(request["location"]["small_sample_reliability_cap"])
    )
    checks["professional_report_embeds_magnitude_section"] = bool(
        report_check["status"] == "PASS"
        and len(reader.pages) >= int(report_request["minimum_pages"])
        and "conditional magnitude recalibration" in normalized_text
        and "magnitude is estimated only if an additional target event occurs"
        in normalized_text
    )
    checks["requested_causation_sentence_is_preserved"] = (
        "Astronomical associations in this experiment it's not enough to establish causation."
        in pdf_text
    )

    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "status": "PASS" if not failed else "FAIL",
        "project": str(project),
        "check_count": len(checks),
        "failed_checks": failed,
        "checks": checks,
        "results": {
            "forecast_scores": forecast[
                ["date", "slot_end_inclusive", "contextual_promoted_score_not_probability"]
            ].to_dict("records"),
            "primary_focus": primary.iloc[0].to_dict(),
            "conditional_magnitude_focus": focus,
            "location_reliability_weight": location_reliability[
                "applied_reliability_weight"
            ],
            "report_pages": len(reader.pages),
            "magnitude_png_pixels": [width, height],
        },
    }
    destination = project / "06_report/self_check_v16.json"
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

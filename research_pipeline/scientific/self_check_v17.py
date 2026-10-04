#!/usr/bin/env python3
"""Check V17 interval operators, quantization, validation and report integrity."""
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


def dates(path: Path) -> list[date]:
    return [date.fromisoformat(str(value)[:10]) for value in pd.read_csv(path, usecols=["date"])["date"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    request = read_json(project / "00_config/pipeline_request.json")
    report_request = read_json(project / "00_config/standard_report_request.json")
    operators = read_json(project / request["interval_features"]["audit_json"])
    manifest = read_json(project / "00_config/run_manifest.json")
    selection = read_json(project / request["hyperparameter_screen"]["output_selection_json"])
    runtime = read_json(project / request["hyperparameter_screen"]["output_runtime_json"])
    diagnostics = read_json(project / "06_report/v17_diagnostics.json")
    timing_validation = pd.read_csv(
        project / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_validation_predictions.csv"
    )
    timing_forecast = pd.read_csv(
        project / "05_ensemble/timing/contextual_fold_fusion/contextual_fold_fusion_forecast.csv"
    )
    location = read_json(project / "05_ensemble/location_zone_summary.json")
    indirect = read_json(project / "05_ensemble/location_zone_indirect_validation.json")
    controls = pd.read_csv(project / "02_audit/world_non_japan_hard_negatives.csv")
    compact = pd.read_csv(project / "01_inputs/timing_master.csv", low_memory=False)
    full_timing = pd.read_csv(
        project / "01_inputs/timing_master_full.csv", low_memory=False
    )
    membership = pd.read_csv(project / "02_audit/event_bin_membership.csv")
    report_check = read_json(
        project / "06_report" / f"self_check_{report_request['report_file_tag']}.json"
    )
    pdf = project / "06_report" / f"{report_request['report_basename']}.pdf"
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    fine_dates = dates(project / request["jpl_master"]["output_master"])
    aggregate_dates = dates(project / request["interval_features"]["output_master"])
    checks = {}
    checks["configured_v17_pipeline"] = str(request["pipeline_version"]).lower() == "v17"
    checks["fine_horizons_grid_is_exact"] = bool(
        all(
            later - earlier == timedelta(days=request["interval_features"]["source_step_days"])
            for earlier, later in zip(fine_dates, fine_dates[1:])
        )
    )
    checks["aggregate_grid_is_exact"] = bool(
        all(
            later - earlier == timedelta(days=request["interval_days"])
            for earlier, later in zip(aggregate_dates, aggregate_dates[1:])
        )
    )
    checks["astronomical_rows_and_timing_targets_are_aligned"] = bool(
        full_timing["date"].astype(str).str.slice(0, 10).tolist()
        == [value.isoformat() for value in aggregate_dates]
    )
    membership_dates_are_inside_slots = True
    for row in membership.itertuples(index=False):
        slot_start = date.fromisoformat(str(row.slot_start)[:10])
        slot_end = date.fromisoformat(str(row.slot_end_inclusive)[:10])
        for event_value in str(row.event_dates).split(";"):
            event_value = event_value.strip()
            if not event_value:
                continue
            event_date = date.fromisoformat(event_value[:10])
            if not slot_start <= event_date <= slot_end:
                membership_dates_are_inside_slots = False
                break
        if not membership_dates_are_inside_slots:
            break
    forecast_start = date.fromisoformat(str(request["forecast_start"])[:10])
    configured_validation_slots = {
        str(value)[:10] for value in request["timing"]["validation_slots"]
    }
    training_floor = float(
        request.get(
            "japan_training_minimum_magnitude",
            request["japan_target_minimum_magnitude"],
        )
    )
    validation_floor = float(
        request.get("japan_validation_minimum_magnitude", training_floor)
    )
    membership_target_policy_is_valid = all(
        int(row.target)
        == int(
            date.fromisoformat(str(row.slot_start)[:10]) < forecast_start
            and (
                float(row.maximum_magnitude) >= training_floor
                or str(row.slot_start)[:10] in configured_validation_slots
            )
        )
        for row in membership.itertuples(index=False)
    )
    checks["every_event_is_rounded_to_its_true_slot_start"] = bool(
        membership_dates_are_inside_slots
        and membership["slot_start"].astype(str).isin(
            full_timing["date"].astype(str)
        ).all()
        and membership_target_policy_is_valid
    )
    configured_body_count = len(
        pd.read_csv(project / request["jpl_master"]["body_csv"])
    )
    expected_operator_features = (
        configured_body_count
        * len(request["interval_features"]["ephemerides"])
        * len(request["interval_features"]["operators"])
    )
    checks["min_median_max_operator_features_are_complete"] = bool(
        operators["generated_operator_feature_count"] == expected_operator_features
        and operators["samples_per_interval"]
        == request["interval_days"] // request["interval_features"]["source_step_days"]
        and not operators["incomplete_windows"]
    )
    levels = request["preprocessing"]["levels"]
    checks["four_bin_quantile_levels_are_exact"] = bool(
        request["preprocessing"]["quantile_bins"] == 4
        and np.allclose(levels, np.linspace(0, 1, 4))
        and manifest["parameters"]["quantile_bins"] == 4
    )
    checks["quantiles_are_declared_training_fold_only"] = (
        "training" in request["preprocessing"]["fit_scope"].lower()
        and "fold" in request["preprocessing"]["fit_scope"].lower()
    )
    required_families = {
        "lcs", "kan", "deep_tiny", "deep_wide", "deep_regularized", "logistic", "extra_trees"
    }
    checks["all_model_families_were_screened_and_promoted"] = bool(
        set(selection["models"]) == required_families
        and {row["family"] for row in runtime["selected"]} == required_families
        and all(np.isfinite(row["runtime_seconds_mean"]) and row["runtime_seconds_mean"] > 0 for row in runtime["selected"])
    )
    holdout_rows = timing_validation.loc[
        timing_validation["designated_holdout"].eq(1)
    ]
    checks["configured_chronological_timing_holdouts_are_aligned"] = bool(
        timing_validation["step"].nunique() == len(configured_validation_slots)
        and len(holdout_rows) == len(configured_validation_slots)
        and holdout_rows["event_mag"].ge(validation_floor).all()
        and set(holdout_rows["date"].astype(str)) == configured_validation_slots
    )
    historical_positive = full_timing.loc[
        full_timing["is_forecast"].eq(0) & full_timing["timing_target"].eq(1)
    ]
    checks["training_and_validation_magnitude_floors_are_separated"] = bool(
        historical_positive.loc[
            ~historical_positive["date"].astype(str).isin(configured_validation_slots),
            "event_mag",
        ].ge(training_floor).all()
        and holdout_rows["event_mag"].ge(validation_floor).all()
    )
    checks["forecast_grid_and_values_are_finite"] = bool(
        len(timing_forecast) == 3
        and np.isfinite(timing_forecast["contextual_promoted_score_not_probability"]).all()
    )
    checks["non_japan_hard_negatives_are_neutral"] = bool(
        controls["model_timing_target"].eq(0).all()
        and controls["model_event_mag"].eq(0).all()
        and controls["model_event_latitude"].eq(0).all()
        and controls["model_event_longitude"].eq(0).all()
        and compact.loc[compact["hard_negative_control"].eq(1), "timing_target"].eq(0).all()
        and controls.loc[
            controls["scope"].eq("training"),
            "original_magnitude_audit_only",
        ].ge(request["world_hard_negative_training_minimum_magnitude"]).all()
        and controls.loc[
            controls["scope"].str.startswith("validation_fold_"),
            "original_magnitude_audit_only",
        ].ge(request["world_hard_negative_validation_minimum_magnitude"]).all()
    )
    checks["primary_location_validation_is_expanded_and_multizone"] = bool(
        len(location["validation_events"]) == request["location"]["validation_events"]
        and location["validation_design"]["observed_distinct_zones"]
        >= request["location"]["minimum_validation_zones"]
        and all(
            float(row["mag"]) >= validation_floor
            for row in location["validation_events"]
        )
    )
    indirect_events = pd.DataFrame(indirect["events"])
    selection_independence = indirect["selection_independence"].lower()
    checks["indirect_lower_magnitude_validation_is_selection_independent"] = bool(
        len(indirect_events) == request["location"]["indirect_validation_events"]
        and indirect_events["mag"].ge(request["location"]["indirect_validation_magnitude_threshold"]).all()
        and indirect_events["mag"].lt(request["japan_target_minimum_magnitude"]).all()
        and ("never" in selection_independence or "did not" in selection_independence)
        and location["indirect_validation"].get("used_for_selection") is False
    )
    checks["boundary_center_plot_contract_is_audited"] = bool(
        "boundaries" in diagnostics["plot_geometry_contract"].lower()
        and "centred" in diagnostics["plot_geometry_contract"].lower()
    )
    for name in (
        "v17_model_runtime_quality.png",
        "v17_system_hybrid_runtime_quality.png",
        "v17_location_indirect_validation.png",
    ):
        with Image.open(project / "06_report" / name) as image:
            checks[f"{name}_is_high_resolution"] = bool(
                image.width >= 5000 and min(image.info.get("dpi", (0, 0))) >= report_request["dpi"] - 1
            )
    # PDF text extraction can discard en dashes and other punctuation, so match
    # section titles after normalizing them to whitespace-separated words.
    normalized_text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    checks["professional_report_passes_and_contains_v17_sections"] = bool(
        report_check["status"] == "PASS"
        and len(reader.pages) >= report_request["minimum_pages"]
        and "runtime and quality speed compromise" in normalized_text
        and "full system and hybrid runtime quality comparison" in normalized_text
        and "indirect lower magnitude localization" in normalized_text
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
            "operator_features": operators["generated_operator_feature_count"],
            "quantile_levels": levels,
            "timing_holdouts": len(holdout_rows),
            "location_holdouts": len(location["validation_events"]),
            "indirect_location_events": len(indirect_events),
            "report_pages": len(reader.pages),
        },
    }
    destination = project / "06_report/self_check_v17.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

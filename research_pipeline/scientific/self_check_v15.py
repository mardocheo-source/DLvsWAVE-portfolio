#!/usr/bin/env python3
"""Validate a parameter-driven fold-contextual timing pipeline and report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pypdf import PdfReader


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def strict_event_peak(frame: pd.DataFrame, score_column: str) -> bool:
    actual = frame["actual"].to_numpy(int)
    score = frame[score_column].to_numpy(float)
    positions = np.flatnonzero(actual == 1)
    if len(positions) != 1:
        return False
    index = int(positions[0])
    return bool(
        0 < index < len(score) - 1
        and score[index] > score[index - 1]
        and score[index] > score[index + 1]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, type=Path)
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()

    request = read_json(project / "00_config/pipeline_request.json")
    report_request = read_json(
        project / "00_config/standard_report_request.json"
    )
    fusion_config = read_json(
        project / request["contextual_fusion"]["config_json"]
    )
    catalog_paths = sorted(
        project.glob("01_inputs/mega_quakes_of_japan_*.csv")
    )
    if not catalog_paths:
        raise FileNotFoundError("Japan megaquake catalogue is absent")
    catalog = pd.read_csv(catalog_paths[-1])
    full = pd.read_csv(
        project / "01_inputs/timing_master_full.csv", low_memory=False
    )
    compact = pd.read_csv(
        project / "01_inputs/timing_master.csv", low_memory=False
    )
    controls = pd.read_csv(
        project / "02_audit/world_non_japan_hard_negatives.csv"
    )
    compact_trials = pd.read_csv(
        project / "02_master_search/compact_k_factor_trials.csv"
    )
    compact_selection = read_json(
        project / "02_master_search/compact_k_factor_selection.json"
    )
    contextual_dir = (
        project / request["contextual_fusion"]["output_directory"]
    )
    summary = read_json(
        contextual_dir / "contextual_fold_fusion_summary.json"
    )
    trace = read_json(Path(summary["contribution_trace"]))
    validation = pd.read_csv(summary["validation"]["path"])
    forecast = pd.read_csv(summary["forecast"]["path"])
    primary = pd.read_csv(
        project / "05_ensemble/timing/forecast_primary_selection.csv"
    )
    report_check = read_json(
        project
        / "06_report"
        / f"self_check_{report_request['report_file_tag']}.json"
    )
    pdf_path = (
        project / "06_report" / f"{report_request['report_basename']}.pdf"
    )
    reader = PdfReader(pdf_path)
    page_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(page_text)

    checks: dict[str, bool] = {}
    floor = float(request["japan_target_minimum_magnitude"])
    checks["configured_v15_pipeline"] = str(
        request["pipeline_version"]
    ).lower().startswith("v15")
    checks["unified_japan_magnitude_floor_is_applied"] = bool(
        pd.to_numeric(catalog["mag"], errors="coerce").ge(floor).all()
    )
    checks["events_below_m83_are_not_validation_targets"] = bool(
        validation.loc[validation["actual"].eq(1), "event_mag"].ge(floor).all()
    )
    dates = pd.to_datetime(full["date"], format="%Y-%m-%d")
    checks["master_uses_configured_fixed_day_grid"] = bool(
        set(dates.diff().dropna().dt.days) == {int(request["interval_days"])}
    )
    expected_trials = (
        len(request["compact_search"]["k_events"])
        * len(request["compact_search"]["k_between"])
        * len(request["compact_search"]["proximity_fractions"])
    )
    checks["all_configured_master_k_factors_were_searched"] = bool(
        len(compact_trials) == expected_trials
        and int(compact_selection["candidate_count"]) == expected_trials
    )
    checks["hard_negative_rows_have_neutral_model_targets"] = bool(
        controls["model_timing_target"].eq(0).all()
        and controls["model_event_mag"].eq(0).all()
        and controls["model_event_latitude"].eq(0).all()
        and controls["model_event_longitude"].eq(0).all()
        and compact.loc[
            compact["hard_negative_control"].eq(1), "timing_target"
        ].eq(0).all()
    )

    fold_directories = sorted(
        path
        for path in (project / "04_models/timing").iterdir()
        if path.is_dir() and path.name[:2].isdigit()
    )
    projected_system_sets = [
        {
            path.parent.name
            for path in fold.glob("*/forecast_predictions.csv")
        }
        for fold in fold_directories
    ]
    checks["every_fold_has_per_system_future_projections"] = bool(
        len(projected_system_sets) == int(summary["search"]["fold_count"])
        and all(projected_system_sets)
        and all(
            systems == projected_system_sets[0]
            for systems in projected_system_sets[1:]
        )
    )
    checks["deep_contextual_search_budget_was_executed"] = all(
        int(value) >= int(fusion_config["random_mix_trials"])
        for value in summary["search"]["evaluated_candidates_per_fold"].values()
    )
    selected_weights = [
        fold["selected"]["weights"] for fold in summary["folds"]
    ]
    checks["folds_retain_independent_model_combinations"] = bool(
        len(selected_weights) >= 2 and selected_weights[0] != selected_weights[1]
    )
    score_column = "contextual_promoted_score_not_probability"
    checks["every_real_holdout_is_a_strict_local_peak"] = bool(
        summary["validation"]["all_events_are_strict_local_peaks"]
        and all(
            strict_event_peak(group.reset_index(drop=True), score_column)
            for _, group in validation.groupby("step", sort=False)
        )
    )
    checks["false_peak_and_hard_negative_constraints_pass"] = bool(
        int(summary["validation"]["maximum_false_peak_count"]) == 0
        and summary["validation"]["all_controls_below_event"]
    )
    checks["weak_peak_system_is_retained"] = bool(
        summary["search"]["weak_peak_system_retained_in_search"]
        and float(summary["validation"]["minimum_weak_peak_retention"])
        >= float(fusion_config["minimum_weak_peak_retention"])
    )
    checks["fold_reliability_weights_form_a_distribution"] = bool(
        np.isclose(
            sum(
                float(fold["final_reliability_weight"])
                for fold in summary["folds"]
            ),
            1.0,
        )
        and all(
            float(fold["final_reliability_weight"]) > 0
            for fold in summary["folds"]
        )
    )
    checks["control_weight_policy_is_respected"] = bool(
        float(trace["row_order_anchor_contribution"]) > 0
        and np.isclose(trace["target_label_randomized_contribution"], 0.0)
        and trace["checks"]["final_weights_sum_to_one"]
        and trace["checks"]["target_label_randomized_has_zero_weight"]
    )
    checks["forecast_grid_covers_configured_end"] = bool(
        set(pd.to_datetime(forecast["date"]).diff().dropna().dt.days)
        == {int(request["interval_days"])}
        and pd.Timestamp(forecast.iloc[-1]["slot_end_inclusive"])
        >= pd.Timestamp(request["forecast_end"])
    )
    threshold = float(
        report_request["forecast_peak_modes"]["first_occurrence_threshold"]
    )
    qualifying = forecast.loc[forecast[score_column].ge(threshold)]
    expected_primary = (
        qualifying.iloc[0]
        if not qualifying.empty
        else forecast.loc[forecast[score_column].idxmax()]
    )
    checks["primary_forecast_selection_matches_json_rule"] = bool(
        len(primary) == 1
        and str(primary.iloc[0]["selection_mode"]) == "first_occurrence"
        and str(primary.iloc[0]["date"]) == str(expected_primary["date"])
        and np.isclose(
            float(primary.iloc[0]["score"]),
            float(expected_primary[score_column]),
        )
    )
    checks["standard_report_self_check_passes"] = (
        report_check["status"] == "PASS"
    )
    contextual_pages = [
        index
        for index, text in enumerate(page_text)
        if "Contextual incremental timing validation" in text
    ]
    checks["contextual_provenance_page_has_only_requested_two_curves"] = bool(
        len(contextual_pages) == 1
        and "held-out real-event indicator" in page_text[contextual_pages[0]]
        and "promoted contextual fusion" in page_text[contextual_pages[0]]
        and "target-label" not in page_text[contextual_pages[0]].lower()
    )
    checks["target_label_randomization_is_on_a_separate_page"] = bool(
        any(
            "randomized one-shot timing control" in text.lower()
            and "randomized-label timing score" in text.lower()
            for text in page_text
        )
    )
    checks["professional_report_is_complete_and_high_resolution"] = bool(
        len(reader.pages) >= int(report_request["minimum_pages"])
        and int(report_check["raster_dpi"]) >= int(report_request["dpi"])
    )
    checks["requested_causation_sentence_is_preserved"] = (
        "Astronomical associations in this experiment it's not enough to establish causation."
        in full_text
    )

    failures = [name for name, passed in checks.items() if not passed]
    payload = {
        "status": "PASS" if not failures else "FAIL",
        "project": str(project),
        "check_count": len(checks),
        "failed_checks": failures,
        "checks": checks,
        "summary": {
            "catalog_events": int(len(catalog)),
            "compact_rows": int(len(compact)),
            "folds": int(len(summary["folds"])),
            "systems_projected_per_fold": (
                len(projected_system_sets[0]) if projected_system_sets else 0
            ),
            "candidates_per_fold": summary["search"][
                "evaluated_candidates_per_fold"
            ],
            "row_order_anchor_share": trace["row_order_anchor_share"],
            "target_label_randomized_share": trace[
                "target_label_randomized_contribution"
            ],
            "primary_forecast_date": str(primary.iloc[0]["date"]),
            "primary_forecast_score": float(primary.iloc[0]["score"]),
            "global_maximum_date": str(
                forecast.loc[forecast[score_column].idxmax(), "date"]
            ),
            "report_pages": int(len(reader.pages)),
        },
    }
    destination = project / "06_report/self_check_v15.json"
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

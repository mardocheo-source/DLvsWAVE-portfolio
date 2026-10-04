#!/usr/bin/env python3
"""Fail loudly when a V20 time-connection contract is not reproduced."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from PIL import Image
import pandas as pd
from pypdf import PdfReader


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-dir", type=Path, required=True)
    return value


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_project_path(project: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (project / path).resolve()


def configured_time_band_sources(settings: dict) -> list[dict]:
    sources = settings.get("time_band_forecast_sources")
    if sources:
        return [dict(source) for source in sources]
    return [
        {
            "label": "Sequential weighted",
            "forecast_csv": settings["time_band_forecast_csv"],
            "validation_summary_key": "nested_sequential_weighted",
        }
    ]


def main() -> None:
    args = parser().parse_args()
    project = args.project_dir.resolve()
    config = read_json(project / "00_config/pipeline_request.json")
    manifest = read_json(project / "02_audit/event_time_master_manifest.json")
    summary = read_json(project / "05_ensemble/time_band_summary.json")
    report = read_json(project / "06_report/v20_report_manifest.json")
    master = pd.read_csv(project / "01_inputs/event_time_master.csv", low_memory=False)
    events = master[master["sample_kind"].eq("event")].copy()
    candidates = master[master["sample_kind"].eq("forecast_candidate")].copy()
    validation = pd.read_csv(project / "05_ensemble/time_band_validation.csv")
    weighted = pd.read_csv(project / "05_ensemble/time_band_weighted_forecast.csv")
    one_shot = pd.read_csv(project / "05_ensemble/time_band_one_shot_forecast.csv")

    event_local = pd.to_datetime(events["sample_time_local"], format="mixed", utc=True).dt.tz_convert("Asia/Tokyo")
    feature_local = pd.to_datetime(events["feature_epoch_utc"], format="mixed", utc=True).dt.tz_convert("Asia/Tokyo")
    candidate_local = pd.to_datetime(candidates["feature_epoch_utc"], format="mixed", utc=True).dt.tz_convert("Asia/Tokyo")
    feature_names = list(manifest["feature_names"])
    direct_tokens = ("hour", "minute", "second", "target_band", "candidate_band")
    checks = {}
    checks["special_v20_time_connection_pipeline"] = bool(
        config["pipeline_version"] == "v20"
        and config["time_target"]["band_hours"] == 6
        and config["time_target"]["timezone"] == "Asia/Tokyo"
    )
    checks["event_features_use_same_local_day_and_band_centres"] = bool(
        (event_local.dt.date == feature_local.dt.date).all()
        and set(feature_local.dt.hour.unique()).issubset({3, 9, 15, 21})
    )
    checks["forecast_uses_daily_four_band_jpl_sampling"] = bool(
        config["forecast"]["sample_stride_days"] == 1
        and len(candidates) == 2160
        and set(candidate_local.dt.hour.unique()) == {3, 9, 15, 21}
        and candidates.groupby("forecast_slot_start").size().eq(360).all()
    )
    checks["source_v19_master_was_not_reused_as_90_day_astronomy"] = bool(
        manifest["timestamp_policy"]["feature_epoch_policy"]
        == "center_of_observed_six_hour_local_band"
        and manifest["unique_jpl_epochs"] >= 2180
    )
    checks["only_trusted_japan_region_timestamps_are_training_records"] = bool(
        len(events) == 24
        and events["source"].eq("USGS_FDSN").all()
        and events["mag"].ge(7.9).all()
        and events["latitude"].between(24, 48).all()
        and events["longitude"].between(122, 154).all()
    )
    checks["historical_conventional_midnight_and_non_japan_hard_negatives_absent"] = bool(
        not events["event_id"].astype(str).str.contains("historical_attachment").any()
        and manifest["non_japan_hard_negative_rows"] == 0
        and summary["data"]["non_japan_hard_negative_rows"] == 0
    )
    checks["all_four_target_bands_are_represented"] = bool(
        events["target_band"].nunique() == 4
        and set(events["target_band"].unique()) == {0, 1, 2, 3}
    )
    checks["nine_outer_holdouts_cover_all_four_bands"] = bool(
        summary["data"]["outer_validation_events"] == 9
        and summary["data"]["outer_validation_distinct_bands"] == 4
        and validation[validation["method"].eq("nested_sequential_weighted")]["event_id"].nunique() == 9
    )
    checks["no_direct_clock_or_target_features"] = bool(
        not any(any(token in name.lower() for token in direct_tokens) for name in feature_names)
        and summary["feature_search"]["uses_direct_hour_features"] is False
    )
    checks["feature_and_hyperparameter_selection_precede_outer_holdouts"] = bool(
        summary["feature_search"]["selection_uses_outer_holdouts"] is False
        and read_json(project / "03_feature_research/time_band_selected_model_overrides.json")["selection_uses_outer_holdouts"] is False
    )
    methods = set(validation["method"])
    checks["weighted_one_shot_and_randomized_null_validations_exist"] = bool(
        {
            "nested_sequential_weighted",
            "one_shot_pre_holdout",
            "target_label_permutation_null",
        }.issubset(methods)
        and validation.groupby("method").size().eq(9).all()
    )
    checks["weak_band_and_adjacent_tolerance_are_reported"] = bool(
        summary["target"]["weak_band_probability_ratio"] > 0
        and "qualified_accuracy_exact_or_weak" in summary["validation"]["nested_sequential_weighted"]
        and "adjacent_or_exact_accuracy" in summary["validation"]["nested_sequential_weighted"]
    )
    checks["sequential_validation_exceeds_randomized_label_null"] = bool(
        summary["validation"]["nested_sequential_weighted"]["quality_higher_is_better"]
        > summary["validation"]["target_label_permutation_null"]["quality_higher_is_better"]
    )
    checks["one_shot_is_reported_even_when_weaker"] = bool(
        summary["validation"]["one_shot_pre_holdout"]["events"] == 9
        and summary["validation"]["one_shot_pre_holdout"]["quality_higher_is_better"] >= 0
    )
    checks["weighted_and_one_shot_conditional_forecasts_are_complete"] = bool(
        len(weighted) == len(config["forecast"]["slots"]) == len(one_shot)
        and weighted["sampled_candidate_epochs"].eq(360).all()
        and one_shot["sampled_candidate_epochs"].eq(360).all()
    )
    checks["randomized_null_has_zero_forecast_weight"] = bool(
        summary["null_control_contributes_to_forecast"] is False
    )
    checks["every_final_attempt_obeys_hard_wall_time_limit"] = bool(
        summary["runtime"]["all_finished_within_limit"] is True
        and summary["runtime"]["maximum_attempt_seconds"]
        <= summary["runtime"]["hard_limit_seconds_per_family_attempt"]
    )
    image_names = [
        "v20_event_time_catalog.png",
        "v20_model_search.png",
        "v20_weighted_validation.png",
        "v20_one_shot_validation.png",
        "v20_validation_comparison.png",
        "v20_time_band_forecast.png",
        "v20_feature_ranking.png",
        "v20_runtime_audit.png",
    ]
    historical = config["report"].get("historical_forecast_comparison", {})
    if historical.get("enabled", False):
        image_names.append(Path(historical["output_png"]).name)
    high_resolution = True
    for name in image_names:
        path = project / "06_report" / name
        if not path.is_file():
            high_resolution = False
            break
        with Image.open(path) as image:
            high_resolution &= image.width >= 5000 and image.height >= 3000
    checks["all_v20_figures_are_high_resolution"] = bool(high_resolution)
    pdf_path = project / "06_report/V20_TIME_CONNECTION_REPORT.pdf"
    pdf = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in pdf.pages]
    text = "\n".join(page_texts)
    checks["professional_english_report_has_required_sections"] = bool(
        len(pdf.pages) >= int(config["report"]["minimum_pages"])
        and "Same-day astronomy" in text
        and "One-shot outer validation" in text
        and "Conditional time-band forecast" in text
    )
    checks["requested_causation_sentence_is_preserved"] = bool(
        config["report"]["required_causation_sentence"] in text
    )
    issue_iso = str(report.get("issued_at_iso8601", ""))
    issue_display = str(report.get("issued_at_display", ""))
    try:
        parsed_issue = datetime.fromisoformat(issue_iso)
    except ValueError:
        parsed_issue = None
    markdown_text = (project / "06_report/V20_TIME_CONNECTION_REPORT.md").read_text(encoding="utf-8")
    checks["report_issue_datetime_is_visible_and_machine_traceable"] = bool(
        parsed_issue is not None
        and parsed_issue.utcoffset() is not None
        and report.get("issue_timezone") == config["report"]["issue_timezone"]
        and f"REPORT ISSUED · {issue_display}" in page_texts[0]
        and f"Issued {issue_display}" in page_texts[11]
        and issue_iso in markdown_text
        and issue_display in markdown_text
    )
    if historical.get("enabled", False):
        trace_path = resolve_project_path(project, historical["output_trace_json"])
        historical_trace = read_json(trace_path) if trace_path.is_file() else {}
        source = pd.read_csv(resolve_project_path(project, historical["source_forecast_csv"]))
        date_column = historical.get("source_date_column", "date")
        end_column = historical.get("source_slot_end_inclusive_column", "slot_end_inclusive")
        score_column = historical.get("source_score_column", "score_percentile_not_probability")
        expected_peak = source.loc[pd.to_numeric(source[score_column]).idxmax()]
        expected_start = pd.Timestamp(expected_peak[date_column]).normalize()
        if end_column in source:
            expected_end = pd.Timestamp(expected_peak[end_column]).normalize() + pd.Timedelta(days=1)
        else:
            expected_end = expected_start + pd.Timedelta(days=int(historical["source_resolution_days"]))
        expected_estimates = []
        for source_settings in configured_time_band_sources(historical):
            band_source = pd.read_csv(resolve_project_path(project, source_settings["forecast_csv"]))
            band_starts = pd.to_datetime(band_source["forecast_slot_start"]).dt.normalize()
            band_ends = pd.to_datetime(band_source["forecast_slot_end"]).dt.normalize() + pd.Timedelta(days=1)
            expected_band_rows = band_source[band_starts.le(expected_start) & band_ends.ge(expected_end)]
            if len(expected_band_rows) != 1:
                expected_estimates.append(None)
                continue
            expected_band = expected_band_rows.iloc[0]
            band = int(expected_band["predicted_band"])
            validation = summary["validation"][source_settings["validation_summary_key"]]
            expected_estimates.append(
                {
                    "label": str(source_settings["label"]),
                    "start_inclusive": str(expected_band["forecast_slot_start"]),
                    "end_inclusive": str(expected_band["forecast_slot_end"]),
                    "predicted_band_label": str(expected_band["predicted_band_label"]),
                    "conditional_relative_share_not_probability": float(
                        expected_band[f"band_{band}_score_not_probability"]
                    ),
                    "validation_exact_accuracy": float(validation["exact_accuracy"]),
                    "validation_adjacent_or_exact_accuracy": float(validation["adjacent_or_exact_accuracy"]),
                    "validation_quality_higher_is_better": float(validation["quality_higher_is_better"]),
                }
            )
        checks["configured_historical_forecast_is_reproduced_from_source_data"] = bool(
            historical_trace.get("source_pipeline_label") == historical["source_pipeline_label"]
            and historical_trace.get("source_report_page") == int(historical["source_report_page"])
            and historical_trace.get("source_resolution_days") == int(historical["source_resolution_days"])
            and historical_trace.get("historical_peak", {}).get("start_inclusive") == f"{expected_start:%Y-%m-%d}"
            and historical_trace.get("historical_peak", {}).get("end_exclusive") == f"{expected_end:%Y-%m-%d}"
            and abs(
                float(historical_trace.get("historical_peak", {}).get("score_not_probability", 0.0))
                - float(expected_peak[score_column])
            ) < 1e-9
        )
        actual_estimates = historical_trace.get("v20_time_band_estimates", [])
        estimate_matches = len(actual_estimates) == len(expected_estimates) and all(
            expected is not None
            and actual.get("label") == expected["label"]
            and actual.get("start_inclusive") == expected["start_inclusive"]
            and actual.get("end_inclusive") == expected["end_inclusive"]
            and actual.get("predicted_band_label") == expected["predicted_band_label"]
            and abs(
                float(actual.get("conditional_relative_share_not_probability", -1.0))
                - expected["conditional_relative_share_not_probability"]
            ) < 1e-9
            and abs(float(actual.get("validation_exact_accuracy", -1.0)) - expected["validation_exact_accuracy"]) < 1e-9
            and abs(
                float(actual.get("validation_adjacent_or_exact_accuracy", -1.0))
                - expected["validation_adjacent_or_exact_accuracy"]
            ) < 1e-9
            and abs(
                float(actual.get("validation_quality_higher_is_better", -1.0))
                - expected["validation_quality_higher_is_better"]
            ) < 1e-9
            for actual, expected in zip(actual_estimates, expected_estimates)
        )
        checks["historical_peak_has_all_configured_v20_time_band_overlays"] = bool(estimate_matches)
        checks["forecast_is_page_12_and_historical_comparison_follows_on_page_13"] = bool(
            len(page_texts) >= 13
            and "Conditional time-band forecast" in page_texts[11]
            and f"Previous {historical['source_pipeline_label']} seven-day forecast with V20 time-band overlay" in page_texts[12]
        )
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "status": status,
        "check_count": len(checks),
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "checks": checks,
        "results": {
            "trusted_events": len(events),
            "outer_holdouts": 9,
            "forecast_daily_candidates": len(candidates),
            "selected_features": summary["feature_search"]["selected_features"],
            "weighted_exact_accuracy": summary["validation"]["nested_sequential_weighted"]["exact_accuracy"],
            "one_shot_exact_accuracy": summary["validation"]["one_shot_pre_holdout"]["exact_accuracy"],
            "report_pages": len(pdf.pages),
        },
    }
    (project / "06_report/self_check_v20.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2), flush=True)
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

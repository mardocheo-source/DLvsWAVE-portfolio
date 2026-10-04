#!/usr/bin/env python3
"""Build standard-renderer inputs from completed pipeline artifacts.

The filename is retained for backwards compatibility with existing recipes.  The
adapter itself discovers the pipeline version and optional promoted timing
families from their persisted JSON/CSV artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()

    manifest = read_json(project / "00_config/run_manifest.json")
    location_audit = read_json(project / "02_audit/location_master_audit.json")
    timing_summary = read_json(project / "05_ensemble/timing/final_summary.json")
    metric_summary = read_json(
        project
        / "05_ensemble/timing/metric_specialist_fusion"
        / "metric_specialist_fusion_summary.json"
    )
    metric_trace = read_json(
        project
        / "05_ensemble/timing/metric_specialist_fusion"
        / "metric_fusion_contribution_trace.json"
    )
    contextual_dir = (
        project / "05_ensemble/timing/contextual_fold_fusion"
    )
    contextual_summary_path = (
        contextual_dir / "contextual_fold_fusion_summary.json"
    )
    contextual_summary = (
        read_json(contextual_summary_path)
        if contextual_summary_path.is_file()
        else None
    )
    contextual_trace = None
    if contextual_summary is not None:
        trace_path = Path(contextual_summary["contribution_trace"])
        if not trace_path.is_absolute():
            trace_path = project / trace_path
        contextual_trace = read_json(trace_path)
    magnitude_summary_path = (
        project
        / "05_ensemble/magnitude_recalibration/"
        "conditional_magnitude_summary.json"
    )
    magnitude_summary = (
        read_json(magnitude_summary_path)
        if magnitude_summary_path.is_file()
        else None
    )
    location_summary = read_json(
        project / "05_ensemble/location_zone_summary.json"
    )
    reliability = read_json(
        project / "05_ensemble/location_reliability_assessment.json"
    )
    compact = read_json(
        project / "02_master_search/compact_k_factor_selection.json"
    )
    frontier = read_json(project / "02_audit/jpl_history_frontier.json")
    catalog_audit = read_json(project / "02_audit/mega_quake_catalog_audit.json")
    hard_negative_audit = read_json(
        project / "02_audit/world_non_japan_hard_negatives.json"
    )
    interval_operator_path = project / "02_audit/interval_feature_operators.json"
    interval_operator_audit = (
        read_json(interval_operator_path) if interval_operator_path.is_file() else None
    )
    model_screen_path = project / "03_feature_research/model_runtime_quality_audit.json"
    model_screen_audit = (
        read_json(model_screen_path) if model_screen_path.is_file() else None
    )
    indirect_location_path = project / "05_ensemble/location_zone_indirect_validation.json"
    indirect_location = (
        read_json(indirect_location_path) if indirect_location_path.is_file() else None
    )

    timing_master = project / "01_inputs/timing_master.csv"
    location_master = project / "01_inputs/location_master.csv"
    location_frame = pd.read_csv(location_master, low_memory=False)
    historical = location_frame.loc[location_frame["is_forecast"].eq(0)]
    forecast = location_frame.loc[location_frame["is_forecast"].eq(1)]
    location_features = [
        column
        for column in location_frame
        if column
        not in {
            "date",
            "event_time",
            "slot_start",
            "mag",
            "depth",
            "latitude",
            "longitude",
            "event_id",
            "is_forecast",
        }
    ]
    catalog_candidates = sorted(
        project.glob("01_inputs/mega_quakes_of_japan_*.csv")
    )
    if not catalog_candidates:
        raise FileNotFoundError(
            "No 01_inputs/mega_quakes_of_japan_*.csv catalogue was found"
        )
    catalog_path = catalog_candidates[-1]
    pipeline_version = str(manifest["pipeline"]).rsplit("-", 1)[-1]
    standard_location_audit = {
        **location_audit,
        "schema_version": (
            f"{pipeline_version}.standard_location_master_adapter.v1"
        ),
        "interval_days": int(manifest["parameters"]["interval_days"]),
        "magnitude_threshold": float(
            manifest["parameters"]["location_magnitude_threshold"]
        ),
        "validation_magnitude_threshold": float(
            manifest["parameters"].get(
                "location_validation_magnitude_threshold",
                manifest["parameters"]["location_magnitude_threshold"],
            )
        ),
        "minimum_historical_rows": 4,
        "region_bounds": location_audit["coordinate_bounds"],
        "catalog": {
            "path": str(catalog_path.resolve()),
            "sha256": sha256(catalog_path),
        },
        "timing_master": {
            "path": str(timing_master.resolve()),
            "sha256": sha256(timing_master),
        },
        "output": {
            "path": str(location_master.resolve()),
            "sha256": sha256(location_master),
            "historical_event_rows": int(len(historical)),
            "historical_distinct_slots": int(historical["slot_start"].nunique()),
            "forecast_rows": int(len(forecast)),
            "feature_count": len(location_features),
        },
        "forecast_grid": {
            "start": str(forecast["date"].min()),
            "end": str(manifest["parameters"]["forecast_end"]),
        },
        "historical_events": historical[
            [
                "date",
                "event_time",
                "slot_start",
                "mag",
                "latitude",
                "longitude",
                "event_id",
            ]
        ].to_dict("records"),
    }
    write_json(
        project / "02_audit/monthly_location_master_audit.json",
        standard_location_audit,
    )

    joint = pd.read_csv(
        project / "05_ensemble/timing_location_joint_forecast.csv"
    )
    joint_score_column = (
        "primary_timing_score_not_probability"
        if "primary_timing_score_not_probability" in joint
        else "metric_specialist_score_not_probability"
    )
    top_joint = joint.nlargest(8, joint_score_column)
    timing_payload = {
        "primary_summary": timing_summary,
        "promoted_family": (
            "contextual_fold_fusion"
            if contextual_summary is not None
            else "metric_specialist"
        ),
        "metric_specialist": {
            "role": (
                "reference_candidate"
                if contextual_summary is not None
                else "promoted"
            ),
            "status": metric_summary["status"],
            "score_semantics": metric_summary["score_semantics"],
            "selected_trial": metric_summary["selected_trial"],
            "core_weights": metric_summary["core_weights"],
            "metric_portfolios": metric_summary["metric_portfolios"],
            "contribution_trace": metric_trace,
            "forecast_csv": str(
                project
                / "05_ensemble/timing/metric_specialist_fusion"
                / "metric_specialist_fusion_forecast.csv"
            ),
        },
    }
    if contextual_summary is not None:
        timing_payload["contextual_fold_fusion"] = {
            "role": "promoted",
            "status": contextual_summary["status"],
            "score_semantics": contextual_summary["score_semantics"],
            "summary": contextual_summary,
            "contribution_trace": contextual_trace,
            "validation_csv": contextual_summary["validation"]["path"],
            "forecast_csv": contextual_summary["forecast"]["path"],
        }
    composite = {
        "schema_version": f"{pipeline_version}.standard_report_composite.v1",
        "status": "COMPLETE",
        "source_pipeline": manifest["pipeline"],
        "purpose": (
            "single machine-readable input for the global V10/V11/V12-style "
            "renderer; values are composed from persisted pipeline outputs"
        ),
        "timing": timing_payload,
        "localization": {
            "summary": location_summary,
            "reliability": reliability,
            "validation_csv": str(
                project / "05_ensemble/location_zone_validation.csv"
            ),
            "forecast_csv": str(
                project / "05_ensemble/location_zone_forecast.csv"
            ),
            **(
                {"indirect_validation": indirect_location}
                if indirect_location is not None
                else {}
            ),
        },
        "joint_timing_location": {
            "formula": reliability["joint_forecast"]["formula"],
            "score_is_probability": False,
            "reliability_weight": reliability[
                "applied_reliability_weight"
            ],
            "forecast_csv": str(
                project / "05_ensemble/timing_location_joint_forecast.csv"
            ),
            "rows": len(joint),
            "top_rows": top_joint.to_dict("records"),
        },
        "deep_history": {
            "catalog": catalog_audit,
            "jpl_frontier": frontier,
            "compact_master": compact,
            "world_non_japan_hard_negatives": hard_negative_audit,
            **(
                {"interval_feature_operators": interval_operator_audit}
                if interval_operator_audit is not None
                else {}
            ),
            **(
                {"model_runtime_quality": model_screen_audit}
                if model_screen_audit is not None
                else {}
            ),
        },
        **(
            {
                "conditional_magnitude_recalibration": {
                    "summary": magnitude_summary,
                    "summary_json": str(magnitude_summary_path),
                    "forecast_csv": magnitude_summary["outputs"]["forecast_csv"],
                    "standalone_png": magnitude_summary["outputs"]["standalone_png"],
                }
            }
            if magnitude_summary is not None
            else {}
        ),
        "report_overrides": {
            "final_statement": (
                "Astronomical associations in this experiment it's not enough "
                "to establish causation."
            )
        },
    }
    destination = project / "00_config/report_composite_data.json"
    write_json(destination, composite)
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "standard_location_audit": str(
                    project / "02_audit/monthly_location_master_audit.json"
                ),
                "composite_report_json": str(destination),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

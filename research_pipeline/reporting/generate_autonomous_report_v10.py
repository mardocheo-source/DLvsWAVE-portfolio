#!/usr/bin/env python3
"""Generate a complete report from an audited pipeline project directory.

No region, magnitude, date or validation event is embedded here. The renderer
discovers those values from the project's run manifest and model artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


REQUIRED_ARTIFACTS = (
    "00_config/run_manifest.json",
    "05_ensemble/timing/final_summary.json",
    "05_ensemble/timing/peak_isolation_gate.json",
    "05_ensemble/timing/alias_gate_trials.csv",
    "05_ensemble/timing/forecast_predictions.csv",
    "05_ensemble/timing/validation_predictions.csv",
    "05_ensemble/timing/validation_gate.csv",
    "05_ensemble/timing/peak_isolation_system_weights.csv",
    "02_audit/location_zone_search.json",
    "05_ensemble/location_zone_summary.json",
    "05_ensemble/location_zone_forecast.csv",
    "05_ensemble/location_zone_validation.csv",
    "05_ensemble/location_zones.csv",
    "05_ensemble/location_zone_decision_grid.csv",
    "05_ensemble/location_zone_event_catalog.csv",
    "05_ensemble/location_zone_system_ranking.csv",
    "05_ensemble/location_zone_fusion_trials.csv",
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Generate narrative JSON, figures, Markdown, linked PDF and "
            "self-checks from one completed pipeline directory."
        )
    )
    value.add_argument("--project-dir", required=True)
    value.add_argument(
        "--repo-dir",
        default=str(Path(__file__).resolve().parents[2]),
        help="DLvsWAVE source repository containing model backends.",
    )
    value.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter with the report dependencies installed.",
    )
    value.add_argument(
        "--renderer",
        default=str(Path(__file__).with_name("render_v10_report.py")),
    )
    value.add_argument(
        "--dpi",
        type=int,
        default=360,
        help="Raster figure export resolution; report-native text stays vector.",
    )
    value.add_argument(
        "--report-version",
        default="v10",
        help="Reader-facing report version and default file tag.",
    )
    value.add_argument(
        "--report-basename",
        help="PDF/Markdown basename; defaults to VERSION_REPORT.",
    )
    value.add_argument(
        "--report-file-tag",
        help="Suffix used for generated figures and self-check JSON.",
    )
    value.add_argument(
        "--require-historical-record-shuffle",
        action="store_true",
        help=(
            "Require and render the intact historical-record order control."
        ),
    )
    value.add_argument(
        "--require-standard-controls",
        action="store_true",
        help=(
            "Require both timing and localization randomized-label controls."
        ),
    )
    value.add_argument(
        "--minimum-pages",
        type=int,
        default=23,
        help="Fail the renderer self-check if the PDF has fewer pages.",
    )
    value.add_argument("--check-only", action="store_true")
    return value


def discover(project: Path) -> dict:
    missing = [
        relative
        for relative in REQUIRED_ARTIFACTS
        if not (project / relative).is_file()
    ]
    manifest_path = project / "00_config/run_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.is_file()
        else None
    )
    composite_path = project / "00_config/report_composite_data.json"
    return {
        "project_dir": str(project),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "missing_artifacts": missing,
        "manifest_pipeline": manifest.get("pipeline") if manifest else None,
        "manifest_parameters": manifest.get("parameters") if manifest else None,
        "composite_report_data": (
            str(composite_path) if composite_path.is_file() else None
        ),
        "ready": not missing and manifest is not None,
    }


def main() -> None:
    args = parser().parse_args()
    project = Path(args.project_dir).expanduser().resolve()
    repo = Path(args.repo_dir).expanduser().resolve()
    renderer = Path(args.renderer).expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    discovery = discover(project)
    if args.require_historical_record_shuffle:
        historical_required = [
            "07_historical_record_shuffle/timing/summary.json",
            "07_historical_record_shuffle/timing/validation.csv",
            "07_historical_record_shuffle/timing/forecast.csv",
            "05_ensemble/timing/forecast_peak_modes.json",
            "05_ensemble/timing/forecast_peak_modes.csv",
            "02_audit/monthly_location_master_audit.json",
        ]
        historical_missing = [
            relative
            for relative in historical_required
            if not (project / relative).is_file()
        ]
        discovery["required_artifacts"].extend(historical_required)
        discovery["missing_artifacts"].extend(historical_missing)
        discovery["ready"] = bool(
            discovery["ready"] and not historical_missing
        )
    if args.require_standard_controls:
        control_required = [
            "07_randomized_control/timing/summary.json",
            "07_randomized_control/timing/validation.csv",
            "07_randomized_control/timing/forecast.csv",
            "07_randomized_control/location/summary.json",
            "07_randomized_control/location/validation.csv",
            "07_randomized_control/location/forecast.csv",
        ]
        control_missing = [
            relative
            for relative in control_required
            if not (project / relative).is_file()
        ]
        discovery["required_artifacts"].extend(control_required)
        discovery["missing_artifacts"].extend(control_missing)
        discovery["ready"] = bool(
            discovery["ready"] and not control_missing
        )
    audit_path = project / "00_config/report_artifact_discovery.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(discovery, indent=2) + "\n")
    if not discovery["ready"]:
        raise SystemExit(
            "Report artifacts are incomplete: "
            + ", ".join(discovery["missing_artifacts"])
        )
    if args.check_only:
        print(f"Artifact discovery PASS: {audit_path}")
        return
    if not renderer.is_file():
        raise FileNotFoundError(renderer)
    environment = os.environ.copy()
    environment["DLVSWAVE_PROJECT_DIR"] = str(project)
    environment["DLVSWAVE_REPO_DIR"] = str(repo)
    environment["DLVSWAVE_REPORT_DPI"] = str(args.dpi)
    report_version = args.report_version.lower()
    report_basename = (
        args.report_basename or f"{report_version.upper()}_REPORT"
    )
    report_file_tag = args.report_file_tag or report_version
    environment["DLVSWAVE_REPORT_VERSION"] = report_version
    environment["DLVSWAVE_REPORT_BASENAME"] = report_basename
    environment["DLVSWAVE_REPORT_FILE_TAG"] = report_file_tag
    environment["DLVSWAVE_REQUIRE_HISTORICAL_RECORD_SHUFFLE"] = (
        "1" if args.require_historical_record_shuffle else "0"
    )
    environment["DLVSWAVE_REPORT_MINIMUM_PAGES"] = str(
        args.minimum_pages
    )
    subprocess.run(
        [args.python, str(renderer)],
        cwd=str(repo),
        env=environment,
        check=True,
    )
    self_check_path = (
        project / f"06_report/self_check_{report_file_tag}.json"
    )
    self_check = json.loads(self_check_path.read_text())
    if self_check.get("status") != "PASS":
        raise RuntimeError(f"Report self-check failed: {self_check_path}")
    print(
        "Autonomous report PASS: "
        f"{project / '06_report' / f'{report_basename}.pdf'}"
    )


if __name__ == "__main__":
    main()

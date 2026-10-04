#!/usr/bin/env python3
"""Orchestrate the complete parameter-driven v10-style report.

The report content is discovered from pipeline artifacts. This wrapper supplies
presentation parameters only; region, targets, dates, observer, features,
models, scores and zones are read by the shared autonomous renderer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def parser() -> argparse.ArgumentParser:
    script = Path(__file__).resolve()
    repo_default = script.parents[2]
    project_default = script.parents[1]
    template_default = script.parent
    value = argparse.ArgumentParser(
        description=(
            "Generate the complete standard timing/localization report from "
            "one completed pipeline directory."
        )
    )
    value.add_argument("--project-dir", default=str(project_default))
    value.add_argument("--repo-dir", default=str(repo_default))
    value.add_argument(
        "--template-pipeline-dir",
        default=str(template_default),
        help=(
            "Pipeline directory containing the shared autonomous report "
            "generator and renderer."
        ),
    )
    value.add_argument("--python", default=sys.executable)
    value.add_argument(
        "--report-config-json",
        default=None,
        help=(
            "Optional JSON presentation/selection configuration. Explicit "
            "CLI arguments override JSON values."
        ),
    )
    value.add_argument("--report-version", default="v12")
    value.add_argument("--report-basename", default="V12_REPORT")
    value.add_argument("--report-file-tag", default="v12")
    value.add_argument("--dpi", type=int, default=360)
    value.add_argument("--minimum-pages", type=int, default=35)
    value.add_argument(
        "--comparison-style",
        choices=("line",),
        default="line",
        help="Comparison charts use point-aligned lines on common bins.",
    )
    value.add_argument(
        "--require-standard-controls",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    value.add_argument(
        "--include-historical-record-shuffle",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    value.add_argument("--first-peak-quantile", type=float, default=0.75)
    value.add_argument(
        "--first-peak-minimum-max-fraction",
        type=float,
        default=0.85,
    )
    value.add_argument("--first-peak-radius", type=int, default=1)
    value.add_argument("--first-peak-not-before", default=None)
    value.add_argument(
        "--forecast-highlight-threshold",
        type=float,
        default=None,
        help=(
            "Optionally highlight every forecast bin whose selected composite "
            "score meets this threshold. No threshold is assumed by default."
        ),
    )
    value.add_argument(
        "--forecast-highlight-fallback",
        choices=("maximum", "first_significant"),
        default="maximum",
        help=(
            "Bin to highlight when no score reaches the configured threshold."
        ),
    )
    value.add_argument(
        "--forecast-primary-selection",
        choices=("first_occurrence", "absolute_peak"),
        default="absolute_peak",
        help=(
            "Single timing rule used to focus the timing, localization and "
            "joint forecast pages."
        ),
    )
    value.add_argument("--forecast-primary-score-csv", default=None)
    value.add_argument("--forecast-primary-score-column", default=None)
    value.add_argument("--forecast-primary-source-label", default=None)
    value.add_argument(
        "--forecast-first-occurrence-threshold",
        type=float,
        default=None,
    )
    value.add_argument(
        "--forecast-first-occurrence-fallback",
        choices=("absolute_peak", "error"),
        default="absolute_peak",
    )
    value.add_argument(
        "--forecast-history-comparison",
        choices=("auto", "show", "hide"),
        default="auto",
        help=(
            "Whether to plot the intact historical-record shuffle beside the "
            "primary forecast. Auto applies validation and integrity gates."
        ),
    )
    value.add_argument(
        "--forecast-history-min-validation-quality",
        type=float,
        default=0.5,
    )
    value.add_argument(
        "--forecast-history-require-above-null",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    value.add_argument(
        "--include-boundary-peaks",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    value.add_argument(
        "--include-observed-event-context-page",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Include the optional observed-event page. It is disabled by "
            "default so no event-specific page is silently hardcoded."
        ),
    )
    value.add_argument(
        "--forecast-overlay-csv",
        default=None,
        help=(
            "Optional external CSV whose dated values are added as points to "
            "the timing forecast chart."
        ),
    )
    value.add_argument("--forecast-overlay-date-column", default="date")
    value.add_argument("--forecast-overlay-value-column", default="value")
    value.add_argument("--forecast-overlay-label-column", default="label")
    value.add_argument(
        "--forecast-overlay-margin",
        type=float,
        default=0.08,
        help=(
            "Visual margin used only when external values are outside [0,1]; "
            "min-max projection maps them into [margin, 1-margin]."
        ),
    )
    value.add_argument("--check-only", action="store_true")
    return value


def parse_arguments() -> argparse.Namespace:
    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument("--report-config-json", default=None)
    known, _ = preliminary.parse_known_args()
    value = parser()
    if known.report_config_json:
        config_path = Path(known.report_config_json).expanduser().resolve()
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Report configuration JSON must contain an object")
        payload = payload.get("standard_report", payload)
        defaults = {
            key: item
            for key, item in payload.items()
            if key not in {"forecast_peak_modes", "forecast_overlay"}
        }
        peak_mapping = {
            "first_peak_quantile": "first_peak_quantile",
            "first_peak_minimum_max_fraction": (
                "first_peak_minimum_max_fraction"
            ),
            "local_peak_radius": "first_peak_radius",
            "include_boundary_peaks": "include_boundary_peaks",
            "first_peak_not_before": "first_peak_not_before",
            "highlight_threshold": "forecast_highlight_threshold",
            "highlight_fallback": "forecast_highlight_fallback",
            "primary_selection": "forecast_primary_selection",
            "primary_score_csv": "forecast_primary_score_csv",
            "primary_score_column": "forecast_primary_score_column",
            "primary_source_label": "forecast_primary_source_label",
            "first_occurrence_threshold": (
                "forecast_first_occurrence_threshold"
            ),
            "first_occurrence_fallback": (
                "forecast_first_occurrence_fallback"
            ),
            "history_comparison": "forecast_history_comparison",
            "history_min_validation_quality": (
                "forecast_history_min_validation_quality"
            ),
            "history_require_above_null": (
                "forecast_history_require_above_null"
            ),
        }
        for key, item in payload.get("forecast_peak_modes", {}).items():
            if key not in peak_mapping:
                raise ValueError(f"Unknown forecast_peak_modes key: {key}")
            defaults[peak_mapping[key]] = item
        overlay_mapping = {
            "csv": "forecast_overlay_csv",
            "date_column": "forecast_overlay_date_column",
            "value_column": "forecast_overlay_value_column",
            "label_column": "forecast_overlay_label_column",
            "visual_margin": "forecast_overlay_margin",
        }
        for key, item in payload.get("forecast_overlay", {}).items():
            if key not in overlay_mapping and key != "projection_formula":
                raise ValueError(f"Unknown forecast_overlay key: {key}")
            if key in overlay_mapping:
                defaults[overlay_mapping[key]] = item
        valid_destinations = {action.dest for action in value._actions}
        unknown = sorted(set(defaults).difference(valid_destinations))
        if unknown:
            raise ValueError(f"Unknown standard-report JSON keys: {unknown}")
        value.set_defaults(**defaults)
    return value.parse_args()


def main() -> None:
    args = parse_arguments()
    project = Path(args.project_dir).expanduser().resolve()
    repo = Path(args.repo_dir).expanduser().resolve()
    template = Path(args.template_pipeline_dir).expanduser().resolve()
    generator = template / "generate_autonomous_report_v10.py"
    renderer = template / "render_v10_report.py"
    if not generator.is_file() or not renderer.is_file():
        raise FileNotFoundError(
            f"Standard report template is incomplete: {template}"
        )
    primary_score_path = None
    if args.forecast_primary_score_csv:
        primary_score_path = Path(args.forecast_primary_score_csv).expanduser()
        if not primary_score_path.is_absolute():
            primary_score_path = project / primary_score_path
        primary_score_path = primary_score_path.resolve()
    parameters = {
        "project_dir": str(project),
        "repo_dir": str(repo),
        "template_pipeline_dir": str(template),
        "report_config_json": (
            str(Path(args.report_config_json).expanduser().resolve())
            if args.report_config_json
            else None
        ),
        "report_version": args.report_version,
        "report_basename": args.report_basename,
        "report_file_tag": args.report_file_tag,
        "dpi": args.dpi,
        "minimum_pages": args.minimum_pages,
        "comparison_style": args.comparison_style,
        "require_standard_controls": args.require_standard_controls,
        "include_historical_record_shuffle": (
            args.include_historical_record_shuffle
        ),
        "forecast_peak_modes": {
            "first_peak_quantile": args.first_peak_quantile,
            "first_peak_minimum_max_fraction": (
                args.first_peak_minimum_max_fraction
            ),
            "local_peak_radius": args.first_peak_radius,
            "include_boundary_peaks": args.include_boundary_peaks,
            "first_peak_not_before": args.first_peak_not_before,
            "highlight_threshold": args.forecast_highlight_threshold,
            "highlight_fallback": args.forecast_highlight_fallback,
            "primary_selection": args.forecast_primary_selection,
            "primary_score_csv": (
                str(primary_score_path) if primary_score_path else None
            ),
            "primary_score_column": args.forecast_primary_score_column,
            "primary_source_label": args.forecast_primary_source_label,
            "first_occurrence_threshold": (
                args.forecast_first_occurrence_threshold
            ),
            "first_occurrence_fallback": (
                args.forecast_first_occurrence_fallback
            ),
            "history_comparison": args.forecast_history_comparison,
            "history_min_validation_quality": (
                args.forecast_history_min_validation_quality
            ),
            "history_require_above_null": (
                args.forecast_history_require_above_null
            ),
        },
        "include_observed_event_context_page": (
            args.include_observed_event_context_page
        ),
        "forecast_overlay": {
            "csv": (
                str(Path(args.forecast_overlay_csv).expanduser().resolve())
                if args.forecast_overlay_csv
                else None
            ),
            "date_column": args.forecast_overlay_date_column,
            "value_column": args.forecast_overlay_value_column,
            "label_column": args.forecast_overlay_label_column,
            "visual_margin": args.forecast_overlay_margin,
            "projection_formula": (
                "identity when every value is in [0,1]; otherwise "
                "margin + (1-2*margin)*(value-min)/(max-min)"
            ),
        },
    }
    audit = project / "00_config/standard_report_parameters.json"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(parameters, indent=2) + "\n")
    project_peak_selector = project / "pipeline/select_forecast_peak_modes.py"
    template_peak_selector = template / "select_forecast_peak_modes.py"
    peak_selector = (
        project_peak_selector
        if project_peak_selector.is_file()
        else template_peak_selector
    )
    if args.include_historical_record_shuffle:
        if not peak_selector.is_file():
            raise FileNotFoundError(
                "Forecast peak-mode selector is missing from both the project "
                f"and standard template: {project_peak_selector}, "
                f"{template_peak_selector}"
            )
        peak_command = [
            args.python,
            str(peak_selector),
            "--project-dir",
            str(project),
            "--first-peak-quantile",
            str(args.first_peak_quantile),
            "--first-peak-minimum-max-fraction",
            str(args.first_peak_minimum_max_fraction),
            "--local-peak-radius",
            str(args.first_peak_radius),
            (
                "--include-boundary-peaks"
                if args.include_boundary_peaks
                else "--no-include-boundary-peaks"
            ),
        ]
        if args.first_peak_not_before:
            peak_command.extend(
                ["--first-peak-not-before", args.first_peak_not_before]
            )
        occurrence_threshold = args.forecast_first_occurrence_threshold
        if occurrence_threshold is None:
            occurrence_threshold = args.forecast_highlight_threshold
        peak_command.extend(
            [
                "--primary-selection",
                args.forecast_primary_selection,
                "--first-occurrence-fallback",
                args.forecast_first_occurrence_fallback,
            ]
        )
        if args.forecast_primary_score_csv:
            peak_command.extend(
                ["--primary-score-csv", args.forecast_primary_score_csv]
            )
        if args.forecast_primary_score_column:
            peak_command.extend(
                [
                    "--primary-score-column",
                    args.forecast_primary_score_column,
                ]
            )
        if args.forecast_primary_source_label:
            peak_command.extend(
                [
                    "--primary-source-label",
                    args.forecast_primary_source_label,
                ]
            )
        if occurrence_threshold is not None:
            peak_command.extend(
                ["--first-occurrence-threshold", str(occurrence_threshold)]
            )
        subprocess.run(
            peak_command,
            cwd=str(repo),
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print(
            "Forecast peak modes regenerated: "
            f"{project / '05_ensemble/timing/forecast_peak_modes.json'}"
        )
    command = [
        args.python,
        str(generator),
        "--project-dir",
        str(project),
        "--repo-dir",
        str(repo),
        "--python",
        args.python,
        "--renderer",
        str(renderer),
        "--dpi",
        str(args.dpi),
        "--report-version",
        args.report_version,
        "--report-basename",
        args.report_basename,
        "--report-file-tag",
        args.report_file_tag,
        "--minimum-pages",
        str(args.minimum_pages),
    ]
    if args.require_standard_controls:
        command.append("--require-standard-controls")
    if args.include_historical_record_shuffle:
        command.append("--require-historical-record-shuffle")
    if args.check_only:
        command.append("--check-only")
    environment = os.environ.copy()
    environment["DLVSWAVE_COMPARISON_STYLE"] = args.comparison_style
    environment["DLVSWAVE_INCLUDE_OBSERVED_EVENT_CONTEXT"] = (
        "1" if args.include_observed_event_context_page else "0"
    )
    if not 0.0 <= args.forecast_history_min_validation_quality <= 1.0:
        raise ValueError(
            "forecast-history-min-validation-quality must be within [0,1]"
        )
    environment["DLVSWAVE_FORECAST_HISTORY_COMPARISON"] = (
        args.forecast_history_comparison
    )
    environment["DLVSWAVE_FORECAST_HISTORY_MIN_VALIDATION_QUALITY"] = str(
        args.forecast_history_min_validation_quality
    )
    environment["DLVSWAVE_FORECAST_HISTORY_REQUIRE_ABOVE_NULL"] = (
        "1" if args.forecast_history_require_above_null else "0"
    )
    if args.forecast_highlight_threshold is not None:
        if not 0.0 <= args.forecast_highlight_threshold <= 1.0:
            raise ValueError(
                "forecast-highlight-threshold must be between zero and one"
            )
        environment["DLVSWAVE_FORECAST_HIGHLIGHT_THRESHOLD"] = str(
            args.forecast_highlight_threshold
        )
        environment["DLVSWAVE_FORECAST_HIGHLIGHT_FALLBACK"] = (
            args.forecast_highlight_fallback
        )
    else:
        environment.pop("DLVSWAVE_FORECAST_HIGHLIGHT_THRESHOLD", None)
        environment.pop("DLVSWAVE_FORECAST_HIGHLIGHT_FALLBACK", None)
    if args.forecast_overlay_csv:
        overlay_path = Path(args.forecast_overlay_csv).expanduser().resolve()
        if not overlay_path.is_file():
            raise FileNotFoundError(
                f"Forecast overlay CSV not found: {overlay_path}"
            )
        if not 0.0 <= args.forecast_overlay_margin < 0.5:
            raise ValueError(
                "forecast-overlay-margin must satisfy 0 <= margin < 0.5"
            )
        environment["DLVSWAVE_FORECAST_OVERLAY_CSV"] = str(overlay_path)
        environment["DLVSWAVE_FORECAST_OVERLAY_DATE_COLUMN"] = (
            args.forecast_overlay_date_column
        )
        environment["DLVSWAVE_FORECAST_OVERLAY_VALUE_COLUMN"] = (
            args.forecast_overlay_value_column
        )
        environment["DLVSWAVE_FORECAST_OVERLAY_LABEL_COLUMN"] = (
            args.forecast_overlay_label_column
        )
        environment["DLVSWAVE_FORECAST_OVERLAY_MARGIN"] = str(
            args.forecast_overlay_margin
        )
    else:
        environment.pop("DLVSWAVE_FORECAST_OVERLAY_CSV", None)
    subprocess.run(
        command,
        cwd=str(repo),
        env=environment,
        check=True,
    )


if __name__ == "__main__":
    main()

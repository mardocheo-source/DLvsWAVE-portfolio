#!/usr/bin/env python3
"""Estimate conditional magnitude from out-of-sample timing-score anchors.

This module deliberately separates two questions.  The upstream timing model
provides a relative score for each interval.  This module estimates magnitude
*conditional on an additional target event occurring*; it never converts that
score into an event probability and never asserts that an event must occur.

All event dates, thresholds, floor policies, input paths and presentation
parameters are supplied by JSON/CLI so the implementation can be reused by
future pipelines without event-specific source edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/v16-magnitude-matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCORE_COLUMN = "contextual_promoted_score_not_probability"


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


def resolve(project: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (project / path).resolve()


def robust_line(
    x: Iterable[float],
    y: Iterable[float],
    minimum_slope: float,
    maximum_slope: float,
) -> tuple[float, float]:
    """Theil-Sen-style line using the median of pairwise slopes."""
    x_array = np.asarray(list(x), dtype=float)
    y_array = np.asarray(list(y), dtype=float)
    slopes = []
    for left in range(len(x_array)):
        for right in range(left + 1, len(x_array)):
            distance = x_array[right] - x_array[left]
            if abs(distance) > 1e-12:
                slopes.append((y_array[right] - y_array[left]) / distance)
    raw_slope = float(np.median(slopes)) if slopes else 0.0
    slope = float(np.clip(raw_slope, minimum_slope, maximum_slope))
    intercept = float(np.median(y_array - slope * x_array))
    return slope, intercept


def actual_rows(validation: pd.DataFrame) -> pd.DataFrame:
    if "designated_holdout" in validation:
        rows = validation.loc[
            validation["designated_holdout"].astype(float).gt(0)
        ].copy()
    else:
        rows = validation.loc[validation["actual"].astype(float).gt(0)].copy()
    required = {"date", "event_mag", SCORE_COLUMN}
    missing = required.difference(rows.columns)
    if missing:
        raise KeyError(f"Validation input is missing columns: {sorted(missing)}")
    rows["anchor_kind"] = "chronological holdout"
    rows["anchor_label"] = rows.apply(
        lambda row: (
            f"holdout {row['date']} · M{float(row['event_mag']):.1f}"
        ),
        axis=1,
    )
    return rows[
        ["date", SCORE_COLUMN, "event_mag", "event_id", "anchor_kind", "anchor_label"]
    ].rename(columns={"event_mag": "magnitude"})


def catalog_calibration_rows(
    forecast: pd.DataFrame,
    catalog: pd.DataFrame,
    as_of: pd.Timestamp,
    threshold: float,
) -> pd.DataFrame:
    """Add completed, genuinely forecast-origin interval/event pairs."""
    events = catalog.copy()
    events["event_date"] = pd.to_datetime(
        events["date"], format="mixed", utc=True, errors="coerce"
    )
    events["mag"] = pd.to_numeric(events["mag"], errors="coerce")
    records = []
    for row in forecast.itertuples(index=False):
        start = pd.Timestamp(getattr(row, "date"), tz="UTC")
        end = pd.Timestamp(getattr(row, "slot_end_inclusive"), tz="UTC")
        if end >= as_of:
            continue
        selected = events.loc[
            events["event_date"].between(start, end, inclusive="both")
            & events["mag"].ge(threshold)
        ]
        if selected.empty:
            continue
        event = selected.loc[selected["mag"].idxmax()]
        records.append(
            {
                "date": start.strftime("%Y-%m-%d"),
                SCORE_COLUMN: float(getattr(row, SCORE_COLUMN)),
                "magnitude": float(event["mag"]),
                "event_id": str(event.get("event_id", "")),
                "anchor_kind": "completed forecast-origin interval",
                "anchor_label": (
                    f"completed {start:%Y-%m-%d} · M{float(event['mag']):.1f}"
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def overlap_days(
    start: pd.Timestamp,
    end: pd.Timestamp,
    focus_start: pd.Timestamp,
    focus_end: pd.Timestamp,
) -> int:
    left = max(start, focus_start)
    right = min(end, focus_end)
    return max(0, int((right - left).days) + 1)


def calibration_diagnostics(
    anchors: pd.DataFrame,
    minimum_slope: float,
    maximum_slope: float,
) -> list[dict]:
    diagnostics = []
    if len(anchors) < 3:
        return diagnostics
    for index, held in anchors.iterrows():
        training = anchors.drop(index)
        slope, intercept = robust_line(
            training[SCORE_COLUMN],
            training["magnitude"],
            minimum_slope,
            maximum_slope,
        )
        estimate = intercept + slope * float(held[SCORE_COLUMN])
        diagnostics.append(
            {
                "held_out_anchor": held["anchor_label"],
                "actual_magnitude": float(held["magnitude"]),
                "estimated_magnitude": float(estimate),
                "absolute_error": float(abs(estimate - held["magnitude"])),
            }
        )
    return diagnostics


def make_figure(
    output: Path,
    anchors: pd.DataFrame,
    forecast: pd.DataFrame,
    focus_rows: pd.DataFrame,
    recent: pd.DataFrame,
    summary: dict,
    dpi: int,
) -> None:
    configuration = summary["configuration"]
    display_version = str(configuration.get("display_version", "experimental"))
    region_label = str(configuration.get("region_label", "configured region"))
    interval_days = int(configuration.get("interval_days", 0))
    if interval_days < 1:
        interval_days = int(
            (
                pd.Timestamp(forecast.iloc[0]["end"])
                - pd.Timestamp(forecast.iloc[0]["start"])
            ).days
            + 1
        )
    timing_series_label = str(
        configuration.get(
            "timing_series_label", f"{display_version} contextual timing score"
        )
    )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
        }
    )
    fig = plt.figure(figsize=(15.2, 8.6), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.35], height_ratios=[1.0, 1.0])
    calibration_ax = fig.add_subplot(grid[:, 0])
    timing_ax = fig.add_subplot(grid[0, 1])
    magnitude_ax = fig.add_subplot(grid[1, 1])

    colors = {
        "chronological holdout": "#28577f",
        "completed forecast-origin interval": "#2f8b57",
    }
    for kind, group in anchors.groupby("anchor_kind", sort=False):
        calibration_ax.scatter(
            group[SCORE_COLUMN],
            group["magnitude"],
            s=90,
            color=colors.get(kind, "#566573"),
            edgecolor="white",
            linewidth=1.2,
            label=kind,
            zorder=4,
        )
        for row in group.itertuples(index=False):
            calibration_ax.annotate(
                row.anchor_label,
                (getattr(row, SCORE_COLUMN), row.magnitude),
                xytext=(6, 7),
                textcoords="offset points",
                fontsize=8.5,
            )
    x_min = max(0.0, min(anchors[SCORE_COLUMN].min(), forecast[SCORE_COLUMN].min()) - 0.08)
    x_max = min(1.0, max(anchors[SCORE_COLUMN].max(), forecast[SCORE_COLUMN].max()) + 0.08)
    x_line = np.linspace(x_min, x_max, 160)
    slope = float(summary["calibration"]["slope"])
    intercept = float(summary["calibration"]["intercept"])
    calibration_ax.plot(
        x_line,
        intercept + slope * x_line,
        color="#b56d09",
        linewidth=2.4,
        label="robust conditional fit",
    )
    focus = summary["focus_window"]
    calibration_ax.errorbar(
        focus["weighted_timing_score"],
        focus["conditional_central_magnitude"],
        yerr=[
            [focus["conditional_central_magnitude"] - focus["conditional_lower_magnitude"]],
            [focus["conditional_upper_magnitude"] - focus["conditional_central_magnitude"]],
        ],
        fmt="D",
        markersize=8,
        color="#c53b35",
        capsize=5,
        label=(
            f"{configuration['focus_start']} to "
            f"{configuration['focus_end']} focus (conditional)"
        ),
        zorder=5,
    )
    calibration_ax.set_title("Out-of-sample score-to-magnitude anchors")
    calibration_ax.set_xlabel("relative timing score (not probability)")
    calibration_ax.set_ylabel("target-event magnitude")
    calibration_ax.grid(True, alpha=0.25)
    calibration_ax.legend(loc="best", fontsize=8.5)

    x = np.arange(len(forecast), dtype=float) + 0.5
    boundaries = np.arange(len(forecast) + 1, dtype=float)

    def apply_interval_axis(axis) -> None:
        axis.set_xticks(boundaries)
        axis.set_xticklabels([""] * len(boundaries))
        axis.set_xticks(x, minor=True)
        axis.set_xticklabels(
            forecast["interval_label"],
            minor=True,
            rotation=12,
            ha="right",
        )
        axis.tick_params(axis="x", which="minor", length=0, pad=4)
        axis.set_xlim(0.0, float(len(forecast)))
        axis.grid(True, axis="x", which="major", alpha=0.3)
        axis.grid(False, axis="x", which="minor")

    timing_ax.plot(
        x,
        forecast[SCORE_COLUMN],
        color="#344bc2",
        marker="o",
        linewidth=2.7,
        label=timing_series_label,
    )
    for row in focus_rows.itertuples(index=False):
        index = int(forecast.index[forecast["date"].eq(row.date)][0])
        timing_ax.axvspan(index, index + 1.0, color="#e99a32", alpha=0.15)
    apply_interval_axis(timing_ax)
    timing_ax.set_ylabel("relative score")
    timing_ax.set_ylim(0, max(1.0, float(forecast[SCORE_COLUMN].max()) + 0.1))
    timing_ax.grid(True, axis="y", alpha=0.2)
    timing_ax.set_title(
        f"Shifted {interval_days}-day {display_version} timing intervals"
    )
    timing_ax.legend(loc="best", fontsize=8.5)

    magnitude_ax.errorbar(
        x,
        forecast["conditional_central_magnitude"],
        yerr=np.vstack(
            [
                forecast["conditional_central_magnitude"]
                - forecast["conditional_lower_magnitude"],
                forecast["conditional_upper_magnitude"]
                - forecast["conditional_central_magnitude"],
            ]
        ),
        fmt="o-",
        color="#b56d09",
        ecolor="#d7a24b",
        capsize=6,
        linewidth=2.5,
        label="conditional magnitude estimate",
    )
    if not recent.empty:
        for row in recent.itertuples(index=False):
            event_date = pd.Timestamp(row.time)
            matching = forecast.loc[
                forecast["start"].le(event_date) & forecast["end"].ge(event_date)
            ]
            if matching.empty:
                continue
            index = int(matching.index[0])
            magnitude_ax.scatter(
                [x[index]], [row.mag], marker="*", s=125, color="#c53b35", zorder=5
            )
            if str(row.id) in set(summary["configuration"]["reference_event_ids"]):
                magnitude_ax.annotate(
                    f"observed {event_date:%Y-%m-%d} · M{float(row.mag):.1f}",
                    (x[index], row.mag),
                    xytext=(7, -15),
                    textcoords="offset points",
                    fontsize=8.3,
                )
    magnitude_ax.axhline(
        focus["observed_floor_magnitude"],
        color="#c53b35",
        linestyle="--",
        linewidth=1.3,
        label=f"observed focus maximum M{focus['observed_floor_magnitude']:.1f}",
    )
    apply_interval_axis(magnitude_ax)
    magnitude_ax.set_ylabel("magnitude if another target event occurs")
    magnitude_ax.grid(True, axis="y", alpha=0.2)
    magnitude_ax.set_title("Conditional magnitude, with observational context")
    magnitude_ax.legend(loc="best", fontsize=8.2)

    fig.suptitle(
        f"{display_version} conditional magnitude recalibration — "
        f"{region_label} shifted timing grid\n"
        "The timing score does not establish that an additional event will occur",
        fontsize=18,
        fontweight="bold",
        color="#172f49",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--config-json", type=Path, required=True)
    parser.add_argument(
        "--validation-csv",
        default="05_ensemble/timing/contextual_fold_fusion/contextual_fold_validation_predictions.csv",
    )
    parser.add_argument(
        "--forecast-csv",
        default="05_ensemble/timing/contextual_fold_fusion/contextual_fold_fusion_forecast.csv",
    )
    parser.add_argument("--catalog-csv", required=True)
    parser.add_argument("--recent-events-csv", required=True)
    parser.add_argument(
        "--output-dir", default="05_ensemble/magnitude_recalibration"
    )
    args = parser.parse_args()

    project = args.project_dir.expanduser().resolve()
    config_path = resolve(project, args.config_json)
    config = read_json(config_path)
    validation_path = resolve(project, args.validation_csv)
    forecast_path = resolve(project, args.forecast_csv)
    catalog_path = resolve(project, args.catalog_csv)
    recent_path = resolve(project, args.recent_events_csv)
    output_dir = resolve(project, args.output_dir)

    validation = pd.read_csv(validation_path, low_memory=False)
    forecast = pd.read_csv(forecast_path, low_memory=False)
    catalog = pd.read_csv(catalog_path, low_memory=False)
    recent = pd.read_csv(recent_path, low_memory=False)
    for required in ("date", "slot_end_inclusive", SCORE_COLUMN):
        if required not in forecast:
            raise KeyError(f"Forecast input is missing {required!r}")

    forecast["start"] = pd.to_datetime(forecast["date"], utc=True)
    forecast["end"] = pd.to_datetime(forecast["slot_end_inclusive"], utc=True)
    forecast["interval_label"] = forecast.apply(
        lambda row: f"[{row['date']},\n{row['slot_end_inclusive']}]", axis=1
    )
    as_of = pd.Timestamp(config["as_of_date"], tz="UTC")
    focus_start = pd.Timestamp(config["focus_start"], tz="UTC")
    focus_end = pd.Timestamp(config["focus_end"], tz="UTC")
    observation_start = pd.Timestamp(
        config.get("observation_context_start", config["focus_start"]),
        tz="UTC",
    )
    target_threshold = float(config["target_magnitude_threshold"])

    anchors = actual_rows(validation)
    completed = catalog_calibration_rows(
        forecast, catalog, as_of, target_threshold
    )
    if not completed.empty:
        anchors = pd.concat([anchors, completed], ignore_index=True)
    anchors = anchors.drop_duplicates(subset=["date", "event_id"], keep="first")
    if len(anchors) < 2:
        raise ValueError("At least two independent magnitude anchors are required")

    minimum_slope = float(config["minimum_slope"])
    maximum_slope = float(config["maximum_slope"])
    slope, intercept = robust_line(
        anchors[SCORE_COLUMN],
        anchors["magnitude"],
        minimum_slope,
        maximum_slope,
    )
    fitted = intercept + slope * anchors[SCORE_COLUMN].to_numpy(dtype=float)
    residuals = anchors["magnitude"].to_numpy(dtype=float) - fitted
    lower_residual = float(
        np.quantile(residuals, float(config["lower_quantile"]), method="linear")
    )
    upper_residual = float(
        np.quantile(residuals, float(config["upper_quantile"]), method="linear")
    )
    half_width = float(config["minimum_interval_half_width"])
    lower_residual = min(lower_residual, -half_width)
    upper_residual = max(upper_residual, half_width)
    maximum_allowed = float(anchors["magnitude"].max()) + float(
        config["maximum_extrapolation_above_training"]
    )

    raw = intercept + slope * forecast[SCORE_COLUMN].to_numpy(dtype=float)
    floor_policy = str(config["conditional_floor_policy"])
    if floor_policy == (
        "maximum of target threshold and magnitude already observed in the configured observation context"
    ):
        target_floor = target_threshold
    elif floor_policy == "maximum magnitude already observed in the focus interval":
        target_floor = 0.0
    else:
        raise ValueError(f"Unsupported conditional_floor_policy: {floor_policy}")
    forecast["conditional_raw_magnitude"] = raw
    forecast["conditional_central_magnitude"] = np.clip(
        np.maximum(raw, target_floor), 0, maximum_allowed
    )
    forecast["conditional_lower_magnitude"] = np.clip(
        np.maximum(raw + lower_residual, target_floor), 0, maximum_allowed
    )
    forecast["conditional_upper_magnitude"] = np.clip(
        np.maximum(raw + upper_residual, forecast["conditional_central_magnitude"]),
        0,
        maximum_allowed,
    )
    forecast["overlap_days_with_focus"] = [
        overlap_days(start, end, focus_start, focus_end)
        for start, end in zip(forecast["start"], forecast["end"])
    ]
    focus_rows = forecast.loc[forecast["overlap_days_with_focus"].gt(0)].copy()
    if focus_rows.empty:
        raise ValueError("No forecast interval overlaps the configured focus window")

    recent["time"] = pd.to_datetime(
        recent["time"], utc=True, errors="coerce"
    )
    recent["mag"] = pd.to_numeric(recent["mag"], errors="coerce")
    observed = recent.loc[
        recent["time"].between(
            observation_start,
            min(focus_end, as_of),
            inclusive="both",
        )
        & recent["mag"].ge(float(config["minimum_observed_magnitude"]))
    ].copy()
    if observed.empty:
        observed_floor = 0.0
    else:
        observed_floor = float(observed["mag"].max())

    aggregation = str(
        config.get("focus_score_aggregation", "overlap_day_weighted_mean")
    )
    if aggregation != "overlap_day_weighted_mean":
        raise ValueError(f"Unsupported focus_score_aggregation: {aggregation}")
    weights = focus_rows["overlap_days_with_focus"].to_numpy(dtype=float)
    weighted_score = float(np.average(focus_rows[SCORE_COLUMN], weights=weights))
    raw_focus = float(intercept + slope * weighted_score)
    conditional_floor = max(target_floor, observed_floor)
    central_focus = max(raw_focus, conditional_floor)
    central_focus = min(central_focus, maximum_allowed)
    lower_focus = min(
        central_focus,
        max(conditional_floor, min(maximum_allowed, raw_focus + lower_residual)),
    )
    upper_focus = max(
        central_focus,
        min(maximum_allowed, raw_focus + upper_residual),
    )
    headroom = central_focus - observed_floor
    diagnostics = calibration_diagnostics(
        anchors, minimum_slope, maximum_slope
    )

    exported = forecast[
        [
            "date",
            "slot_end_inclusive",
            SCORE_COLUMN,
            "conditional_raw_magnitude",
            "conditional_lower_magnitude",
            "conditional_central_magnitude",
            "conditional_upper_magnitude",
            "overlap_days_with_focus",
        ]
    ].copy()
    csv_path = output_dir / "conditional_magnitude_forecast.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    exported.to_csv(csv_path, index=False, float_format="%.9f")

    focus_intervals = focus_rows[
        [
            "date",
            "slot_end_inclusive",
            SCORE_COLUMN,
            "conditional_lower_magnitude",
            "conditional_central_magnitude",
            "conditional_upper_magnitude",
            "overlap_days_with_focus",
        ]
    ].to_dict("records")
    conclusion = (
        "The fitted conditional centre exceeds the largest focus-window event observed so far."
        if headroom > 0.05
        else "The fitted conditional centre does not resolve meaningful magnitude headroom above the largest focus-window event observed so far."
    )
    summary = {
        "schema": "conditional_magnitude_recalibration.summary.v1",
        "status": "COMPLETE_CONDITIONAL_NOT_EVENT_FORECAST",
        "score_semantics": "relative experimental timing score; not a calibrated probability",
        "conditional_statement": str(config["conditional_statement"]),
        "configuration": config,
        "inputs": {
            "validation": {"path": str(validation_path), "sha256": sha256(validation_path)},
            "forecast": {"path": str(forecast_path), "sha256": sha256(forecast_path)},
            "catalog": {"path": str(catalog_path), "sha256": sha256(catalog_path)},
            "recent_events": {"path": str(recent_path), "sha256": sha256(recent_path)},
        },
        "calibration": {
            "method": str(config["calibration_method"]),
            "anchor_count": int(len(anchors)),
            "anchors": anchors.to_dict("records"),
            "slope": slope,
            "intercept": intercept,
            "residual_lower": lower_residual,
            "residual_upper": upper_residual,
            "maximum_allowed_magnitude": maximum_allowed,
            "leave_one_anchor_out": diagnostics,
            "mean_absolute_error": (
                float(np.mean([row["absolute_error"] for row in diagnostics]))
                if diagnostics
                else None
            ),
        },
        "focus_window": {
            "start": focus_start.strftime("%Y-%m-%d"),
            "end": focus_end.strftime("%Y-%m-%d"),
            "as_of_date": as_of.strftime("%Y-%m-%d"),
            "observation_context_start": observation_start.strftime("%Y-%m-%d"),
            "score_aggregation": aggregation,
            "weighted_timing_score": weighted_score,
            "raw_fitted_magnitude": raw_focus,
            "observed_floor_magnitude": observed_floor,
            "conditional_lower_magnitude": lower_focus,
            "conditional_central_magnitude": central_focus,
            "conditional_upper_magnitude": upper_focus,
            "headroom_above_observed_floor": headroom,
            "overlapping_intervals": focus_intervals,
            "observed_reference_events": observed[
                ["time", "mag", "id", "place", "latitude", "longitude", "depth"]
            ].to_dict("records"),
            "interpretation": conclusion,
        },
        "limitations": [
            "The sample of genuinely out-of-sample magnitude anchors is very small.",
            "Historical and instrumental magnitudes are not measurement-equivalent.",
            "The configured target/observed floor is a reporting condition, not a physical law.",
            "No timing score in this artifact is an event probability.",
        ],
        "outputs": {
            "forecast_csv": str(csv_path),
            "standalone_png": str(output_dir / str(config["standalone_png_name"])),
        },
    }
    summary_path = output_dir / "conditional_magnitude_summary.json"
    write_json(summary_path, summary)
    png_path = output_dir / str(config["standalone_png_name"])
    make_figure(
        png_path,
        anchors,
        forecast,
        focus_rows,
        observed,
        summary,
        int(config["image_dpi"]),
    )
    summary["outputs"]["summary_json"] = str(summary_path)
    summary["outputs"]["standalone_png_sha256"] = sha256(png_path)
    write_json(summary_path, summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "focus_window": summary["focus_window"],
                "png": str(png_path),
                "summary": str(summary_path),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()

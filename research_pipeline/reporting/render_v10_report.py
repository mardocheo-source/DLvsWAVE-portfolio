#!/usr/bin/env python3
"""Render the English v10 clean-baseline research report."""
from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path
import re
import sys
import textwrap
from functools import lru_cache

os.environ.setdefault("MPLCONFIGDIR", "/tmp/peak-isolation-v10-report")

# The visual language follows the established V10 standard, but every helper
# is now shipped beside this renderer.  Report generation therefore does not
# depend on an ignored or mutable historical study directory under ``DB``.
_REPORT_TEMPLATE_SUPPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPORT_TEMPLATE_SUPPORT))

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link

from common_v6 import PROJECT, score_quality, sha256, write_json
from build_report_narrative import build_narrative
from build_workflow_manifest import build_workflow
from report_time_scale import (
    infer_time_scale,
    interval_end,
    interval_label,
)


REPORT = PROJECT / "06_report"
ZONE_COLORS = {
    1: "#e15759",
    2: "#4e79a7",
    3: "#59a14f",
    4: "#f28e2b",
    5: "#b07aa1",
    6: "#76b7b2",
    7: "#edc949",
}
SYSTEM_DISPLAY_NAMES = {
    "lcs_only": "LCS only",
    "kan_only": "KAN only",
    "deep_tiny": "Deep learning — tiny",
    "deep_wide": "Deep learning — wide",
    "deep_regularized": "Deep learning — regularized",
    "lcs_kan": "LCS + KAN",
    "lcs_deep_tiny": "LCS + Deep tiny",
    "lcs_deep_wide": "LCS + Deep wide",
    "lcs_deep_regularized": "LCS + Deep regularized",
    "kan_deep_tiny": "KAN + Deep tiny",
    "kan_deep_wide": "KAN + Deep wide",
    "kan_deep_regularized": "KAN + Deep regularized",
    "lcs_kan_deep_tiny": "LCS + KAN + Deep tiny",
    "lcs_kan_deep_wide": "LCS + KAN + Deep wide",
    "lcs_kan_deep_regularized": "LCS + KAN + Deep regularized",
    "deep_ensemble": "Deep ensemble — tiny + wide + regularized",
    "screening_anchor": "Screening anchor — logistic + ExtraTrees",
    "logistic_only": "Logistic regression",
    "extra_trees_only": "ExtraTrees",
    "logistic_extra_trees": "Logistic regression + ExtraTrees",
}
BASE_COMPONENT_NAMES = {
    "lcs": "LCS",
    "kan": "KAN",
    "deep_tiny": "Deep learning — tiny",
    "deep_wide": "Deep learning — wide",
    "deep_regularized": "Deep learning — regularized",
    "screening_anchor": "Screening anchor — logistic + ExtraTrees",
}
PEAK_SOURCE_LABELS = {
    "chronological_incremental": "chronological incremental",
    "historical_record_shuffle": "intact historical-record shuffle",
}
PEAK_SELECTION_LABELS = {
    "first_significant_peak": "first significant peak",
    "maximum_peak": "global maximum",
}
PRIMARY_SELECTION_LABELS = {
    "first_occurrence": "first qualifying occurrence",
    "absolute_peak": "absolute peak",
    **PEAK_SELECTION_LABELS,
}


@lru_cache(maxsize=1)
def report_composite() -> dict:
    """Load optional pipeline-specific report data without hard-coded values."""
    path = PROJECT / "00_config/report_composite_data.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Report composite must be a JSON object: {path}")
    return payload


@lru_cache(maxsize=1)
def report_target_magnitude_threshold() -> float:
    """Discover the configured regional target floor for generic wording."""
    request = PROJECT / "00_config/pipeline_request.json"
    if request.is_file():
        payload = json.loads(request.read_text(encoding="utf-8"))
        if "japan_training_minimum_magnitude" in payload:
            return float(payload["japan_training_minimum_magnitude"])
        if "japan_target_minimum_magnitude" in payload:
            return float(payload["japan_target_minimum_magnitude"])
        target = payload.get("target", {})
        if isinstance(target, dict) and "minimum_magnitude" in target:
            return float(target["minimum_magnitude"])
    manifest = PROJECT / "00_config/run_manifest.json"
    if manifest.is_file():
        parameters = json.loads(manifest.read_text(encoding="utf-8")).get(
            "parameters", {}
        )
        if "timing_magnitude_threshold" in parameters:
            return float(parameters["timing_magnitude_threshold"])
    return 7.9


def report_target_magnitude_label() -> str:
    return f"{report_target_magnitude_threshold():g}"


@lru_cache(maxsize=1)
def report_validation_magnitude_threshold() -> float:
    """Return the explicitly configured outer-holdout magnitude floor."""
    request = PROJECT / "00_config/pipeline_request.json"
    if request.is_file():
        payload = json.loads(request.read_text(encoding="utf-8"))
        if "japan_timing_validation_minimum_magnitude" in payload:
            return float(payload["japan_timing_validation_minimum_magnitude"])
        if "japan_validation_minimum_magnitude" in payload:
            return float(payload["japan_validation_minimum_magnitude"])
    return report_target_magnitude_threshold()


def report_validation_magnitude_label() -> str:
    return f"{report_validation_magnitude_threshold():g}"


@lru_cache(maxsize=1)
def report_location_validation_magnitude_threshold() -> float:
    """Return the independently configured location-holdout magnitude floor."""
    request = PROJECT / "00_config/pipeline_request.json"
    if request.is_file():
        payload = json.loads(request.read_text(encoding="utf-8"))
        if "japan_location_validation_minimum_magnitude" in payload:
            return float(payload["japan_location_validation_minimum_magnitude"])
        if "japan_validation_minimum_magnitude" in payload:
            return float(payload["japan_validation_minimum_magnitude"])
    return report_target_magnitude_threshold()


@lru_cache(maxsize=1)
def report_grid_offset() -> dict:
    """Load the optional, pipeline-declared comparison-grid contract."""
    request = PROJECT / "00_config/pipeline_request.json"
    if not request.is_file():
        return {}
    payload = json.loads(request.read_text(encoding="utf-8"))
    grid = payload.get("grid_offset", {})
    return grid if isinstance(grid, dict) else {}


REPORT_DPI = int(os.environ.get("DLVSWAVE_REPORT_DPI", "360"))
REPORT_VERSION = os.environ.get("DLVSWAVE_REPORT_VERSION", "v10").lower()
REPORT_BASENAME = os.environ.get(
    "DLVSWAVE_REPORT_BASENAME",
    f"{REPORT_VERSION.upper()}_REPORT",
)
REPORT_FILE_TAG = os.environ.get(
    "DLVSWAVE_REPORT_FILE_TAG",
    REPORT_VERSION,
).lower()
REPORT_MINIMUM_PAGES = int(
    os.environ.get("DLVSWAVE_REPORT_MINIMUM_PAGES", "23")
)
COMPARISON_STYLE = os.environ.get(
    "DLVSWAVE_COMPARISON_STYLE",
    "line",
).lower()
if COMPARISON_STYLE != "line":
    raise ValueError(
        "DLVSWAVE_COMPARISON_STYLE must be 'line'; comparison bars are not "
        "part of the standard report contract."
    )
REQUIRE_HISTORICAL_RECORD_SHUFFLE = (
    os.environ.get(
        "DLVSWAVE_REQUIRE_HISTORICAL_RECORD_SHUFFLE",
        "0",
    )
    == "1"
)
INCLUDE_OBSERVED_EVENT_CONTEXT = (
    os.environ.get("DLVSWAVE_INCLUDE_OBSERVED_EVENT_CONTEXT", "0") == "1"
)
FORECAST_OVERLAY_CSV = os.environ.get(
    "DLVSWAVE_FORECAST_OVERLAY_CSV",
    "",
).strip()
FORECAST_OVERLAY_DATE_COLUMN = os.environ.get(
    "DLVSWAVE_FORECAST_OVERLAY_DATE_COLUMN",
    "date",
)
FORECAST_OVERLAY_VALUE_COLUMN = os.environ.get(
    "DLVSWAVE_FORECAST_OVERLAY_VALUE_COLUMN",
    "value",
)
FORECAST_OVERLAY_LABEL_COLUMN = os.environ.get(
    "DLVSWAVE_FORECAST_OVERLAY_LABEL_COLUMN",
    "label",
)
FORECAST_OVERLAY_MARGIN = float(
    os.environ.get("DLVSWAVE_FORECAST_OVERLAY_MARGIN", "0.08")
)
_FORECAST_HIGHLIGHT_THRESHOLD_TEXT = os.environ.get(
    "DLVSWAVE_FORECAST_HIGHLIGHT_THRESHOLD", ""
).strip()
FORECAST_HIGHLIGHT_THRESHOLD = (
    float(_FORECAST_HIGHLIGHT_THRESHOLD_TEXT)
    if _FORECAST_HIGHLIGHT_THRESHOLD_TEXT
    else None
)
FORECAST_HIGHLIGHT_FALLBACK = os.environ.get(
    "DLVSWAVE_FORECAST_HIGHLIGHT_FALLBACK", "maximum"
).strip().lower()
if FORECAST_HIGHLIGHT_THRESHOLD is not None and not (
    0.0 <= FORECAST_HIGHLIGHT_THRESHOLD <= 1.0
):
    raise ValueError("forecast highlight threshold must be in [0,1]")
if FORECAST_HIGHLIGHT_FALLBACK not in {"maximum", "first_significant"}:
    raise ValueError(
        "forecast highlight fallback must be maximum or first_significant"
    )
FORECAST_HISTORY_COMPARISON = os.environ.get(
    "DLVSWAVE_FORECAST_HISTORY_COMPARISON", "auto"
).strip().lower()
FORECAST_HISTORY_MIN_VALIDATION_QUALITY = float(
    os.environ.get(
        "DLVSWAVE_FORECAST_HISTORY_MIN_VALIDATION_QUALITY", "0.5"
    )
)
FORECAST_HISTORY_REQUIRE_ABOVE_NULL = (
    os.environ.get(
        "DLVSWAVE_FORECAST_HISTORY_REQUIRE_ABOVE_NULL", "1"
    )
    == "1"
)
if FORECAST_HISTORY_COMPARISON not in {"auto", "show", "hide"}:
    raise ValueError("forecast history comparison must be auto, show or hide")
if not 0.0 <= FORECAST_HISTORY_MIN_VALIDATION_QUALITY <= 1.0:
    raise ValueError("forecast history minimum quality must be within [0,1]")
PAGE_WIDTH_IN = 11.7
PAGE_HEIGHT_IN = 8.3
PAGE_WIDTH_PT = PAGE_WIDTH_IN * 72.0
PAGE_HEIGHT_PT = PAGE_HEIGHT_IN * 72.0


def diagnostic_peak_mode_frame() -> pd.DataFrame:
    """Return all audited peak-rule diagnostics joined to localization."""
    path = PROJECT / "05_ensemble/timing/forecast_peak_modes.csv"
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def forecast_peak_mode_frame() -> pd.DataFrame:
    """Return the single configured selection used to focus report pages."""
    primary = (
        PROJECT / "05_ensemble/timing/forecast_primary_selection.csv"
    )
    if primary.is_file():
        return pd.read_csv(primary)
    return diagnostic_peak_mode_frame()


def selection_mode_label(mode: str) -> str:
    return PRIMARY_SELECTION_LABELS.get(
        str(mode), str(mode).replace("_", " ")
    )


def selection_mode_color(mode: str) -> str:
    return {
        "first_occurrence": "#b7791f",
        "first_significant_peak": "#b7791f",
        "absolute_peak": "#c53030",
        "maximum_peak": "#c53030",
    }.get(str(mode), "#4c51bf")


def historical_forecast_comparison() -> tuple[pd.DataFrame, dict]:
    """Gate the intact-record shuffle as evidence, never as a null forecast."""
    directory = PROJECT / "07_historical_record_shuffle/timing"
    summary_path = directory / "summary.json"
    forecast_path = directory / "forecast.csv"
    null_summary_path = PROJECT / "07_randomized_control/timing/summary.json"
    available = summary_path.is_file() and forecast_path.is_file()
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if available
        else {}
    )
    null_summary = (
        json.loads(null_summary_path.read_text(encoding="utf-8"))
        if null_summary_path.is_file()
        else {}
    )
    history_quality = float(
        summary.get("validation_metrics", {}).get(
            "quality_higher_is_better", float("nan")
        )
    )
    null_quality = float(
        null_summary.get("validation_metrics", {}).get(
            "quality_higher_is_better", float("nan")
        )
    )
    integrity_pass = bool(
        summary.get("feature_target_pairs_preserved")
        and summary.get("training_membership_preserved")
        and summary.get("outer_cutoffs_preserved")
        and summary.get("validation_targets_untouched")
    )
    quality_pass = bool(
        np.isfinite(history_quality)
        and history_quality >= FORECAST_HISTORY_MIN_VALIDATION_QUALITY
    )
    above_null = bool(
        np.isfinite(history_quality)
        and np.isfinite(null_quality)
        and history_quality > null_quality
    )
    automatic_gate = bool(
        available
        and summary.get("status") == "COMPLETE"
        and integrity_pass
        and quality_pass
        and (
            above_null
            if FORECAST_HISTORY_REQUIRE_ABOVE_NULL
            else True
        )
    )
    included = bool(
        FORECAST_HISTORY_COMPARISON == "show"
        or (
            FORECAST_HISTORY_COMPARISON == "auto"
            and automatic_gate
        )
    )
    if FORECAST_HISTORY_COMPARISON == "show" and not available:
        raise FileNotFoundError(
            "Historical forecast comparison was forced but its artifacts are missing"
        )
    reasons = []
    if not available:
        reasons.append("artifacts unavailable")
    if available and not integrity_pass:
        reasons.append("historical integrity contract failed")
    if available and not quality_pass:
        reasons.append(
            "validation quality below configured minimum"
        )
    if (
        available
        and FORECAST_HISTORY_REQUIRE_ABOVE_NULL
        and not above_null
    ):
        reasons.append("validation quality does not exceed randomized labels")
    audit = {
        "status": "INCLUDED" if included else "EXCLUDED",
        "mode": FORECAST_HISTORY_COMPARISON,
        "semantics": (
            "intact historical-record order sensitivity comparison; not the "
            "randomized-label null test"
        ),
        "forecast_csv": str(forecast_path),
        "summary_json": str(summary_path),
        "available": available,
        "integrity_pass": integrity_pass,
        "history_validation_quality": (
            history_quality if np.isfinite(history_quality) else None
        ),
        "minimum_validation_quality": (
            FORECAST_HISTORY_MIN_VALIDATION_QUALITY
        ),
        "quality_pass": quality_pass,
        "randomized_label_quality": (
            null_quality if np.isfinite(null_quality) else None
        ),
        "require_above_randomized_labels": (
            FORECAST_HISTORY_REQUIRE_ABOVE_NULL
        ),
        "above_randomized_labels": above_null,
        "automatic_gate_pass": automatic_gate,
        "exclusion_reasons": reasons,
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT / "forecast_history_comparison_audit.json", audit)
    return (
        pd.read_csv(forecast_path)
        if included
        else pd.DataFrame(),
        audit,
    )


def forecast_overlay_frame(
    forecast: pd.DataFrame,
    *,
    persist_audit: bool = True,
) -> tuple[pd.DataFrame, dict | None]:
    """Load and project an optional external CSV onto the timing Y axis."""
    if not FORECAST_OVERLAY_CSV:
        return pd.DataFrame(), None
    path = Path(FORECAST_OVERLAY_CSV).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Forecast overlay CSV not found: {path}")
    if not 0.0 <= FORECAST_OVERLAY_MARGIN < 0.5:
        raise ValueError("forecast overlay margin must satisfy 0 <= margin < 0.5")
    external = pd.read_csv(path)
    required = {
        FORECAST_OVERLAY_DATE_COLUMN,
        FORECAST_OVERLAY_VALUE_COLUMN,
    }
    missing = sorted(required.difference(external.columns))
    if missing:
        raise ValueError(
            f"Forecast overlay CSV is missing required columns: {missing}"
        )
    values = pd.to_numeric(
        external[FORECAST_OVERLAY_VALUE_COLUMN],
        errors="coerce",
    )
    dates = pd.to_datetime(
        external[FORECAST_OVERLAY_DATE_COLUMN],
        errors="coerce",
    ).dt.tz_localize(None)
    valid_numeric = values.notna() & np.isfinite(values)
    external = external.loc[valid_numeric & dates.notna()].copy()
    external["source_date"] = dates.loc[external.index]
    external["raw_value"] = values.loc[external.index].astype(float)
    if external.empty:
        raise ValueError("Forecast overlay CSV has no finite dated values")

    starts = pd.to_datetime(forecast["date"], errors="raise").dt.normalize()
    interval_days = int(
        json.loads(
            (PROJECT / "00_config/run_manifest.json").read_text()
        )["parameters"]["interval_days"]
    )
    start_values = starts.to_numpy(dtype="datetime64[ns]")
    source_values = external["source_date"].to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(start_values, source_values, side="right") - 1
    in_grid = (positions >= 0) & (positions < len(starts))
    clipped = np.clip(positions, 0, max(len(starts) - 1, 0))
    interval_ends = (
        start_values[clipped]
        + np.timedelta64(interval_days, "D")
    )
    in_grid &= source_values < interval_ends
    external = external.loc[in_grid].copy()
    positions = positions[in_grid]
    if external.empty:
        raise ValueError(
            "Forecast overlay CSV has no dates inside the displayed forecast bins"
        )
    external["bin_index"] = positions.astype(int)
    external["bin_start"] = starts.iloc[positions].dt.strftime(
        "%Y-%m-%d"
    ).to_numpy()

    raw = external["raw_value"].to_numpy(float)
    already_unit_interval = bool(np.all((raw >= 0.0) & (raw <= 1.0)))
    if already_unit_interval:
        projected = raw.copy()
        projection_mode = "identity_0_1"
        formula = "y_plot = y_external because every external value is in [0, 1]"
    else:
        raw_min = float(np.min(raw))
        raw_max = float(np.max(raw))
        if raw_max > raw_min:
            normalized = (raw - raw_min) / (raw_max - raw_min)
            projected = (
                FORECAST_OVERLAY_MARGIN
                + (1.0 - 2.0 * FORECAST_OVERLAY_MARGIN) * normalized
            )
            formula = (
                "y_plot = margin + (1 - 2*margin) * "
                "(y_external - min_external) / "
                "(max_external - min_external)"
            )
        else:
            projected = np.full_like(raw, 0.5, dtype=float)
            formula = (
                "y_plot = 0.5 because all non-[0,1] external values are equal"
            )
        projection_mode = "minmax_with_visual_margin"
    external["projected_y"] = projected
    if FORECAST_OVERLAY_LABEL_COLUMN in external:
        external["point_label"] = external[
            FORECAST_OVERLAY_LABEL_COLUMN
        ].fillna("").astype(str)
    else:
        external["point_label"] = ""

    # Preserve every point. Small deterministic offsets reveal multiple
    # observations falling inside the same seven-day bin.
    external["plot_x"] = external["bin_index"].astype(float)
    for _, indices in external.groupby("bin_index", sort=False).groups.items():
        ordered = list(indices)
        if len(ordered) > 1:
            external.loc[ordered, "plot_x"] += np.linspace(
                -0.12,
                0.12,
                len(ordered),
            )

    audit = {
        "status": "COMPLETE",
        "source_csv": str(path),
        "date_column": FORECAST_OVERLAY_DATE_COLUMN,
        "value_column": FORECAST_OVERLAY_VALUE_COLUMN,
        "label_column": (
            FORECAST_OVERLAY_LABEL_COLUMN
            if FORECAST_OVERLAY_LABEL_COLUMN in external
            else None
        ),
        "source_rows": int(len(values)),
        "displayed_rows": int(len(external)),
        "projection_mode": projection_mode,
        "visual_margin": FORECAST_OVERLAY_MARGIN,
        "raw_min": float(np.min(raw)),
        "raw_max": float(np.max(raw)),
        "projected_min": float(np.min(projected)),
        "projected_max": float(np.max(projected)),
        "formula": formula,
        "date_mapping": (
            "each external date is assigned to the displayed interval "
            "[bin_start, bin_start + interval_days)"
        ),
    }
    if persist_audit:
        REPORT.mkdir(parents=True, exist_ok=True)
        external[
            [
                "source_date",
                "raw_value",
                "bin_start",
                "bin_index",
                "plot_x",
                "projected_y",
                "point_label",
            ]
        ].to_csv(
            REPORT / "forecast_external_overlay_projected.csv",
            index=False,
        )
        write_json(REPORT / "forecast_external_overlay_audit.json", audit)
    return external, audit


def compact_mode_sources(values) -> str:
    labels = {
        "chronological_incremental": "incremental",
        "historical_record_shuffle": "record shuffle",
    }
    return " + ".join(labels.get(str(value), str(value)) for value in values)


def figure_image_box(map_layout: bool = False) -> tuple[float, float, float, float]:
    """Return figure-image placement as (x0, y0, width, height) in figure fractions."""
    if map_layout:
        return (0.018, 0.052, 0.635, 0.815)
    return (0.035, 0.315, 0.93, 0.545)


def fit_image_in_box(
    image_width: int,
    image_height: int,
    box: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Fit image into a figure-fraction box; return page points (x, y, w, h)."""
    x0_frac, y0_frac, width_frac, height_frac = box
    box_x = x0_frac * PAGE_WIDTH_PT
    box_y = y0_frac * PAGE_HEIGHT_PT
    box_w = width_frac * PAGE_WIDTH_PT
    box_h = height_frac * PAGE_HEIGHT_PT
    image_aspect = image_width / max(image_height, 1)
    box_aspect = box_w / max(box_h, 1e-9)
    if image_aspect >= box_aspect:
        draw_w = box_w
        draw_h = box_w / image_aspect
    else:
        draw_h = box_h
        draw_w = box_h * image_aspect
    draw_x = box_x + (box_w - draw_w) / 2.0
    draw_y = box_y + (box_h - draw_h) / 2.0
    return draw_x, draw_y, draw_w, draw_h


def embed_png_on_page(
    page,
    image_path: Path,
    box: tuple[float, float, float, float],
) -> None:
    """Place a high-resolution PNG onto a PDF page without re-rasterizing."""
    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        image_width, image_height = rgb.size
        draw_x, draw_y, draw_w, draw_h = fit_image_in_box(
            image_width, image_height, box
        )
        resolution = image_width / max(draw_w / 72.0, 1e-9)
        buffer = BytesIO()
        rgb.save(buffer, format="PDF", resolution=resolution)
        buffer.seek(0)
    image_page = PdfReader(buffer).pages[0]
    page.merge_translated_page(image_page, draw_x, draw_y, over=True)


@lru_cache(maxsize=1)
def report_time_scale():
    frame = pd.read_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv",
        usecols=["date"],
    )
    return infer_time_scale(frame["date"])


def finish(fig, path: Path):
    fig.savefig(
        path,
        dpi=REPORT_DPI,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def exact_slot_labels(frame: pd.DataFrame) -> list[str]:
    starts = pd.to_datetime(frame["date"])
    scale = report_time_scale()
    return [interval_label(start, scale, multiline=True) for start in starts]


def apply_interval_boundary_axis(
    axis,
    boundary_positions: np.ndarray,
    center_positions: np.ndarray,
    center_labels: list[str],
    *,
    rotation: float = 28,
    fontsize: float = 8.0,
) -> None:
    """Put grid lines on interval boundaries and labels below slot centres.

    Major ticks carry the boundary grid and intentionally have no labels;
    minor ticks sit at the centre of each interval and carry the interval text.
    This prevents a start-labelled point from being visually mistaken for a
    value measured exactly on the separating grid line.
    """
    boundaries = np.asarray(boundary_positions, float)
    centers = np.asarray(center_positions, float)
    if len(centers) != len(center_labels):
        raise ValueError("Interval centres and labels must be aligned")
    axis.set_xticks(boundaries)
    axis.set_xticklabels([""] * len(boundaries))
    axis.set_xticks(centers, minor=True)
    axis.set_xticklabels(
        center_labels,
        minor=True,
        rotation=rotation,
        ha="right",
        fontsize=fontsize,
    )
    axis.tick_params(axis="x", which="major", length=4)
    axis.tick_params(axis="x", which="minor", length=0, pad=4)
    axis.grid(True, axis="x", which="major", color="#9aa6b2", alpha=0.25, linewidth=0.75)
    axis.grid(False, axis="x", which="minor")


@lru_cache(maxsize=1)
def catalog_event_dates() -> dict[str, str]:
    """Discover event dates from the pipeline catalogue without version literals."""
    candidates = sorted((PROJECT / "01_inputs").glob("mega_quakes_of_japan_*.csv"))
    for path in reversed(candidates):
        try:
            frame = pd.read_csv(path, usecols=["event_id", "time"])
        except (ValueError, OSError):
            continue
        return {
            str(row.event_id): pd.Timestamp(row.time).strftime("%Y-%m-%d")
            for row in frame.itertuples()
        }
    return {}


def event_date_from_identifier(event_id: str, fallback: str) -> str:
    """Resolve the catalogue date without embedding particular validation events."""
    catalog_date = catalog_event_dates().get(str(event_id))
    if catalog_date is not None:
        return catalog_date
    match = re.search(r"official(\d{8})", str(event_id))
    if match:
        return pd.Timestamp(match.group(1)).strftime("%Y-%m-%d")
    return pd.Timestamp(fallback).strftime("%Y-%m-%d")


def timing_validation_figure(path: Path):
    contextual_path = (
        PROJECT
        / "05_ensemble/timing/contextual_fold_fusion/"
        "contextual_fold_validation_predictions.csv"
    )
    focused_path = (
        PROJECT
        / "05_ensemble/timing/metric_specialist_fusion/"
        "false_positive_aware_validation_predictions.csv"
    )
    contextual = contextual_path.is_file()
    if contextual:
        frame = pd.read_csv(contextual_path)
        score_column = "contextual_promoted_score_not_probability"
        raw_score_column = score_column
        peak_column = None
        curve_label = "promoted fold-contextual fusion"
    elif focused_path.is_file():
        frame = pd.read_csv(focused_path)
        score_column = "selected_score_not_probability"
        raw_score_column = "selected_raw_score"
        peak_column = "selected_is_internal_local_peak"
        curve_label = "false-positive-aware validation score"
    else:
        frame = pd.read_csv(
            PROJECT / "05_ensemble/timing/validation_predictions.csv"
        )
        score_column = "score_percentile_not_probability"
        raw_score_column = "raw_score"
        peak_column = "is_internal_local_peak"
        curve_label = "ensemble validation score"
    gate = pd.read_csv(PROJECT / "05_ensemble/timing/validation_gate.csv")
    steps = list(frame["step"].drop_duplicates())
    fig, axis = plt.subplots(figsize=(16.2, 7.0))
    cursor = 0.0
    tick_positions: list[float] = []
    tick_labels: list[str] = []
    fold_centers: list[tuple[float, str]] = []
    for fold_index, step in enumerate(steps, 1):
        data = frame.loc[frame["step"].eq(step)].reset_index(drop=True)
        gate_row = gate.loc[gate["step"].eq(step)].iloc[0]
        actual_event_date = event_date_from_identifier(
            gate_row.get("event_id", ""),
            gate_row["event_date"],
        )
        x = cursor + np.arange(len(data), dtype=float) + 0.5
        score = data[score_column].to_numpy(float)
        raw_score = data[raw_score_column].to_numpy(float)
        target_mask = (
            data["designated_holdout"].fillna(0).to_numpy(int) == 1
            if "designated_holdout" in data
            else data["actual"].to_numpy(int) == 1
        )
        target_matches = np.flatnonzero(target_mask)
        if len(target_matches) != 1:
            raise RuntimeError(
                f"Expected one designated timing holdout for {step}"
            )
        event_index = int(target_matches[0])
        axis.axvspan(
            x[0] - 0.5,
            x[-1] + 0.5,
            color="#4e79a7" if fold_index % 2 else "#f28e2b",
            alpha=0.035,
            zorder=0,
        )
        if fold_index > 1:
            axis.axvline(
                x[0] - 0.5,
                color="#6b7280",
                linewidth=1.1,
                linestyle=":",
                alpha=0.75,
                zorder=2,
            )
        axis.plot(
            x,
            score,
            color="#2b70b8",
            marker="o",
            markersize=5,
            linestyle="-",
            linewidth=2.2,
            label=curve_label if fold_index == 1 else None,
            zorder=4,
        )
        axis.scatter(
            [x[event_index]],
            [score[event_index]],
            marker="*",
            s=210,
            color="#d62728",
            edgecolor="white",
            linewidth=1.0,
            label="held-out Japan event" if fold_index == 1 else None,
            zorder=8,
        )
        if "hard_negative_control" in data:
            control_indices = np.flatnonzero(
                data["hard_negative_control"].fillna(0).to_numpy(int) == 1
            )
            if len(control_indices):
                axis.scatter(
                    x[control_indices],
                    score[control_indices],
                    marker="X",
                    s=105,
                    color="#f28e2b",
                    edgecolor="white",
                    linewidth=0.9,
                    label=(
                        "selected non-Japan "
                        f"M≥{report_validation_magnitude_label()} hard negative"
                        if fold_index == 1
                        else None
                    ),
                    zorder=7,
                )
                for control_index in control_indices:
                    place = str(data.iloc[control_index].get("hard_negative_places", ""))
                    label = "\n".join(textwrap.wrap(place, width=24))
                    raw_margin = raw_score[event_index] - raw_score[control_index]
                    control_score = float(score[control_index])
                    if control_score <= 0.22:
                        control_offset = 42
                        control_va = "bottom"
                    elif control_score >= 0.70 or control_index <= event_index:
                        control_offset = -38
                        control_va = "top"
                    else:
                        control_offset = 42
                        control_va = "bottom"
                    axis.annotate(
                        f"NON-JAPAN CONTROL\n{label}\n"
                        f"score {control_score:.3f} · "
                        f"event margin {raw_margin:+.3f}",
                        (x[control_index], control_score),
                        xytext=(0, control_offset),
                        textcoords="offset points",
                        ha="center",
                        va=control_va,
                        fontsize=6.6,
                        color="#9a4b13",
                        weight="bold",
                        bbox=dict(
                            boxstyle="round,pad=0.18",
                            facecolor="#fff7ed",
                            edgecolor="#f28e2b",
                            alpha=0.9,
                        ),
                        zorder=8,
                    )
        event_x = float(x[event_index])
        axis.axvspan(
            event_x - 0.5,
            event_x + 0.5,
            color="#e15759",
            alpha=0.13,
            zorder=1,
        )
        if peak_column is None:
            peak_indices = np.asarray(
                [
                    index
                    for index in range(1, len(score) - 1)
                    if score[index] > score[index - 1]
                    and score[index] > score[index + 1]
                ],
                dtype=int,
            )
        else:
            peak_indices = np.flatnonzero(data[peak_column].to_numpy(int))
        # The dedicated real-event box already contains its date and score.
        # Repeating a second point label at the same coordinate makes dense
        # multi-fold charts illegible, so annotate only other local peaks.
        for index in sorted(set(peak_indices.tolist()) - {event_index}):
            axis.annotate(
                f"{data.iloc[index]['date']}\nscore {score[index]:.3f}",
                (x[index], score[index]),
                xytext=(0, 12),
                textcoords="offset points",
                ha="center",
                fontsize=6.8,
                color="#455466",
                weight="bold" if index == event_index else "normal",
            )
        axis.text(
            event_x,
            max(0.04, score[event_index] - 0.22),
            f"REAL EVENT\n{actual_event_date} · M{gate_row['magnitude']:.2f}\n"
            f"{gate_row['latitude']:.2f}°N, {gate_row['longitude']:.2f}°E\n"
            f"score {score[event_index]:.3f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="#b22222",
            weight="bold",
            bbox=dict(
                boxstyle="round,pad=0.20",
                facecolor="white",
                edgecolor="#e8b4b4",
                alpha=0.82,
            ),
            zorder=6,
        )
        for index, date in enumerate(pd.to_datetime(data["date"])):
            if index % 2 == 0 or index == event_index or index == len(data) - 1:
                tick_positions.append(float(x[index]))
                tick_labels.append(
                    interval_label(
                        date, report_time_scale(), multiline=True
                    )
                )
        fold_centers.append(
            (
                float(np.mean(x)),
                f"FOLD {fold_index}\n"
                f"{actual_event_date} · M{gate_row['magnitude']:.2f}\n"
                f"{gate_row['latitude']:.2f}°N · {gate_row['longitude']:.2f}°E",
            )
        )
        cursor = float(x[-1] + 0.5)

    for center, label in fold_centers:
        axis.text(
            center,
            1.145,
            label,
            ha="center",
            va="top",
            fontsize=7.2,
            weight="bold",
            color="#303b46",
            linespacing=1.05,
        )
    apply_interval_boundary_axis(
        axis,
        np.arange(0.0, cursor + 0.1, 1.0),
        np.asarray(tick_positions, float),
        tick_labels,
        rotation=42,
        fontsize=8,
    )
    axis.set_xlim(0.0, cursor)
    axis.set_ylim(-0.04, 1.20)
    axis.set_yticks(np.linspace(0, 1, 6))
    axis.set_xlabel(
        f"each label is one {report_time_scale().display_singular} "
        "[start, end); "
        "the dotted divider marks the next incremental fold"
    )
    axis.set_ylabel(
        "relative timing score (0–1; not a calibrated probability)"
    )
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.23, linewidth=0.7)
    axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.24),
        ncol=2,
        frameon=False,
    )
    fig.suptitle(
        (
            "Fold-contextual incremental timing validation\n"
            "Each fold keeps its own selected combination and reliability"
            if contextual
            else "False-positive-aware incremental timing validation\n"
            "Japan events and non-Japan hard controls share the same score axis"
        ),
        y=0.985,
        fontsize=15,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, path)


def timing_validation_event_figures() -> list[Path]:
    """Create one automatically named, self-contained page per outer event."""
    contextual_path = (
        PROJECT
        / "05_ensemble/timing/contextual_fold_fusion/"
        "contextual_fold_validation_predictions.csv"
    )
    focused_path = (
        PROJECT
        / "05_ensemble/timing/metric_specialist_fusion/"
        "false_positive_aware_validation_predictions.csv"
    )
    contextual = contextual_path.is_file()
    focused = focused_path.is_file() and not contextual
    frame = pd.read_csv(
        contextual_path
        if contextual
        else (
            focused_path
            if focused
            else PROJECT / "05_ensemble/timing/validation_predictions.csv"
        )
    )
    gate = pd.read_csv(PROJECT / "05_ensemble/timing/validation_gate.csv")
    for stale in REPORT.glob("timing_validation_event_*.png"):
        stale.unlink()
    outputs = []
    for rank, step in enumerate(frame["step"].drop_duplicates(), 1):
        data = frame.loc[frame["step"].eq(step)].reset_index(drop=True)
        gate_row = gate.loc[gate["step"].eq(step)].iloc[0]
        target_mask = (
            data["designated_holdout"].fillna(0).to_numpy(int) == 1
            if "designated_holdout" in data
            else data["actual"].to_numpy(int) == 1
        )
        target_matches = np.flatnonzero(target_mask)
        if len(target_matches) != 1:
            raise RuntimeError(
                f"Expected one designated timing holdout for {step}"
            )
        event_index = int(target_matches[0])
        score = data[
            "contextual_promoted_score_not_probability"
            if contextual
            else (
                "selected_score_not_probability"
                if focused
                else "score_percentile_not_probability"
            )
        ].to_numpy(float)
        normal = (
            score
            if focused or contextual
            else data["normal_score_percentile"].to_numpy(float)
        )
        actual = data["actual"].to_numpy(int)
        x = np.arange(len(data))
        path = REPORT / (
            f"timing_validation_event_{rank:02d}_"
            f"{str(gate_row['event_date'])}.png"
        )
        fig, axis = plt.subplots(figsize=(12.5, 6.2))
        axis.plot(
            x,
            actual,
            color="#d62728",
            linestyle="--",
            linewidth=1.8,
            label="actual event line",
            zorder=2,
        )
        axis.plot(
            x,
            normal,
            color="#2b70b8",
            marker="o",
            linewidth=2.2,
            label=(
                "promoted fold-contextual fusion score"
                if contextual
                else (
                    "false-positive-aware fusion score"
                    if focused
                    else "normal ensemble score"
                )
            ),
            zorder=3,
        )
        if "hard_negative_control" in data:
            control_indices = np.flatnonzero(
                data["hard_negative_control"].fillna(0).to_numpy(int) == 1
            )
            if len(control_indices):
                axis.scatter(
                    x[control_indices],
                    score[control_indices],
                    marker="X",
                    s=115,
                    color="#f28e2b",
                    edgecolor="white",
                    linewidth=1.0,
                    label=(
                        "selected non-Japan "
                        f"M≥{report_validation_magnitude_label()} hard negative"
                    ),
                    zorder=7,
                )
                for control_index in control_indices:
                    place = str(data.iloc[control_index].get("hard_negative_places", ""))
                    axis.annotate(
                        "NON-JAPAN CONTROL\n"
                        + "\n".join(textwrap.wrap(place, width=26))
                        + f"\nscore {score[control_index]:.3f}",
                        (x[control_index], score[control_index]),
                        xytext=(0, 46),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color="#9a4b13",
                        weight="bold",
                    )
        if not focused and not np.allclose(score, normal):
            axis.plot(
                x,
                score,
                color="#7a5195",
                marker="s",
                linestyle="--",
                linewidth=2.0,
                label="validation-selected score",
                zorder=4,
            )
        axis.axvspan(
            event_index - 0.45,
            event_index + 0.45,
            color="#e15759",
            alpha=0.10,
        )
        peak_indices = np.flatnonzero(
            data[
                "selected_is_internal_local_peak"
                if focused
                else "is_internal_local_peak"
            ].to_numpy(int)
        )
        for index in sorted(set(peak_indices.tolist() + [event_index])):
            axis.annotate(
                f"{data.iloc[index]['date'][5:]}\n{score[index]:.3f}",
                (index, score[index]),
                xytext=(0, 12),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                color="#b22222" if index == event_index else "#455466",
                weight="bold" if index == event_index else "normal",
            )
        axis.set_xticks(x)
        axis.set_xticklabels(data["date"].str[5:], rotation=40, ha="right")
        axis.set_ylim(-0.04, 1.10)
        axis.set_xlabel(
            f"configured {report_time_scale().display_singular} start"
        )
        axis.set_ylabel("score / binary actual")
        axis.grid(True, color="#9aa6b2", alpha=0.25, linewidth=0.7)
        axis.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=3,
            frameon=False,
        )
        location = (
            f"{gate_row['latitude']:.3f}°N, {gate_row['longitude']:.3f}°E"
            if {"latitude", "longitude"}.issubset(gate.columns)
            else "location unavailable"
        )
        fig.suptitle(
            f"Outer timing validation {rank}\n"
            f"{gate_row['event_date']}, M{gate_row['magnitude']:.2f}, {location}\n"
            f"event ID {gate_row.get('event_id', 'unavailable')}; "
            f"exact local peak={bool(gate_row['strict_local_peak'])}; "
            f"global offset={int(gate_row['argmax_offset_slots']):+d} slot(s)",
            y=0.985,
            fontsize=12,
            weight="bold",
        )
        fig.tight_layout(rect=(0, 0, 1, 0.88))
        finish(fig, path)
        outputs.append(path)
    return outputs


def timing_penalty_figure(path: Path):
    audit = json.loads(
        (PROJECT / "05_ensemble/timing/peak_isolation_gate.json").read_text()
    )
    before = audit["baseline_without_alias"]["profiles"]
    after = audit["selected"]["profiles"]
    x = np.arange(len(after))
    labels = [f"increment {index + 1}" for index in x]
    fig, axis = plt.subplots(figsize=(10.8, 5.7))
    before_values = [
        row["objective_higher_is_better"] for row in before
    ]
    after_values = [
        row["objective_higher_is_better"] for row in after
    ]
    width = 0.34
    before_bars = axis.bar(
        x - width / 2,
        before_values,
        width,
        label="Baseline without suppression",
        color="#9fb3c8",
    )
    after_bars = axis.bar(
        x + width / 2,
        after_values,
        width,
        label=(
            "Selected decision (baseline retained)"
            if audit["status"] != "ALIAS_PENALTY_ACCEPTED"
            else "Selected decision (suppression accepted)"
        ),
        color="#2b70b8",
    )
    axis.bar_label(
        before_bars,
        labels=[f"{value:.3f}" for value in before_values],
        padding=4,
        fontsize=8.5,
    )
    axis.bar_label(
        after_bars,
        labels=[f"{value:.3f}" for value in after_values],
        padding=4,
        fontsize=8.5,
        weight="bold",
    )
    axis.set_xticks(x)
    axis.set_xticklabels(labels)
    axis.set_ylim(0, max(1.16, max(before_values + after_values) + 0.18))
    axis.set_ylabel(
        "peak-isolation skill (0–1; larger means better separation)"
    )
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.25)
    axis.legend(
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        fontsize=8.5,
        loc="upper left",
        ncol=2,
    )
    axis.set_title(
        "Held-out isolation skill: unsuppressed baseline versus selected decision",
        fontsize=10.5,
        pad=10,
    )
    search_count = int(audit["search"]["alias_candidates"])
    effective_count = int(
        audit["search"].get("effective_alias_candidates", search_count)
    )
    if audit["status"] == "NO_APPLICABLE_ALIAS_PATTERN":
        decision_text = (
            f"search executed ({search_count:,} trials; "
            f"{effective_count:,} effective); no repeated alias pattern was "
            "present, so the unsuppressed baseline was retained"
        )
    elif audit["status"] == "NO_ALIAS_PENALTY":
        required_gain = float(
            audit["search"].get("minimum_isolation_gain", 0.01)
        )
        baseline_clean = all(
            bool(profile.get("exact_peak"))
            and int(profile.get("false_peak_count", 0)) == 0
            for profile in before
        )
        baseline_note = (
            "baseline already had exact held-out peaks and zero false peaks; "
            if baseline_clean
            else ""
        )
        decision_text = (
            f"search executed ({search_count:,} candidates; "
            f"{effective_count:,} structurally applicable); {baseline_note}\n"
            f"no suppression achieved the required +{required_gain:.3f} gain "
            "while preserving validation, so the baseline was retained"
        )
    else:
        decision_text = (
            f"search executed ({search_count:,} suppression candidates); "
            "validation accepted a non-zero filter"
        )
    fig.suptitle(
        f"{decision_text}\n"
        f"selected repetition distance "
        f"{audit['selected']['alias_lag_slots']} intervals · "
        f"selected filtering strength {audit['selected']['alias_strength']:.2f}",
        fontsize=10.5,
        weight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.90))
    finish(fig, path)


def timing_ranking_figure(path: Path):
    manifest = json.loads((PROJECT / "00_config/run_manifest.json").read_text())
    train_weight = float(
        manifest["parameters"].get("training_objective_weight", 0.25)
    )
    validation_weight = float(
        manifest["parameters"].get("validation_objective_weight", 0.75)
    )
    fold_directories = sorted(
        path
        for path in (PROJECT / "04_models/timing").iterdir()
        if path.is_dir()
    )
    rows = []
    for system, display_name in SYSTEM_DISPLAY_NAMES.items():
        summaries = []
        for fold in fold_directories:
            summary_path = fold / system / "summary.json"
            if summary_path.is_file():
                summaries.append(json.loads(summary_path.read_text()))
        if not summaries:
            continue
        training_quality = float(
            np.mean(
                [
                    item["training_metrics"]["quality_higher_is_better"]
                    for item in summaries
                ]
            )
        )
        validation_quality = float(
            np.mean(
                [
                    item["validation_metrics"]["quality_higher_is_better"]
                    for item in summaries
                ]
            )
        )
        rows.append(
            {
                "system": system,
                "display_name": display_name,
                "training_quality": training_quality,
                "validation_quality": validation_quality,
                "combined_quality": (
                    train_weight * training_quality
                    + validation_weight * validation_quality
                ),
                "folds": len(summaries),
            }
        )
    frame = pd.DataFrame(rows).sort_values(
        "combined_quality", ascending=True
    ).reset_index(drop=True)
    frame["rank"] = (
        frame["combined_quality"].rank(method="first", ascending=False).astype(int)
    )
    frame.to_csv(
        PROJECT / "05_ensemble/timing/timing_system_quality_report.csv",
        index=False,
    )
    fig, axis = plt.subplots(figsize=(12.6, 7.2))
    y = np.arange(len(frame))
    training = frame["training_quality"].to_numpy(float)
    validation = frame["validation_quality"].to_numpy(float)
    for index in range(len(frame)):
        axis.plot(
            [training[index], validation[index]],
            [index, index],
            color="#aeb8c2",
            linewidth=2.0,
        )
    axis.scatter(
        training,
        y,
        color="#2b70b8",
        s=42,
        label="training quality",
        zorder=3,
    )
    axis.scatter(
        validation,
        y,
        color="#f28e2b",
        marker="D",
        s=42,
        label="held-out validation quality",
        zorder=3,
    )
    for index, row in enumerate(frame.itertuples()):
        axis.text(
            min(training[index], validation[index]) - 0.012,
            index,
            str(row.rank),
            ha="right",
            va="center",
            fontsize=8,
            weight="bold",
        )
        if row.rank <= 3:
            axis.text(
                max(training[index], validation[index]) + 0.015,
                index,
                str(row.rank),
                ha="center",
                va="center",
                color="white",
                weight="bold",
                bbox=dict(
                    boxstyle="circle,pad=0.25",
                    facecolor="#e15759",
                    edgecolor="none",
                ),
            )
    axis.set_yticks(y)
    axis.set_yticklabels(frame["display_name"], fontsize=8)
    minimum = max(0.0, min(training.min(), validation.min()) - 0.06)
    maximum = min(1.0, max(training.max(), validation.max()) + 0.08)
    axis.set_xlim(minimum, maximum)
    axis.set_xlabel(
        "normalized model quality (0–1; farther right is better)"
    )
    axis.grid(True, axis="x", color="#9aa6b2", alpha=0.25)
    axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
    )
    axis.set_title("Timing systems — training quality versus held-out validation quality\n"
        f"rank uses {train_weight:.0%} training + "
        f"{validation_weight:.0%} validation")
    fig.tight_layout(rect=(0, 0.08, 1, 1.0))
    finish(fig, path)


def _legacy_timing_forecast_figure(path: Path):
    data = pd.read_csv(PROJECT / "05_ensemble/timing/forecast_predictions.csv")
    x = np.arange(len(data), dtype=float) + 0.5
    selected = data["score_percentile_not_probability"].to_numpy(float)
    best_index = int(np.argmax(selected))
    colors = [
        "#f28e2b" if index == best_index else "#4e79a7"
        for index in range(len(data))
    ]
    fig, axis = plt.subplots(figsize=(14.8, 6.0))
    bars = axis.bar(
        x,
        selected,
        width=0.72,
        color=colors,
        edgecolor="white",
        linewidth=0.8,
    )
    axis.bar_label(
        bars,
        labels=[f"{score:.3f}" for score in selected],
        padding=4,
        fontsize=8.5,
        weight="bold",
    )
    apply_interval_boundary_axis(
        axis,
        np.arange(len(data) + 1, dtype=float),
        x,
        exact_slot_labels(data),
        rotation=32,
    )
    axis.set_xlim(0.0, float(len(data)))
    scale = report_time_scale()
    axis.set_xlabel(
        f"Every label is one complete {scale.display_singular} [start – end): "
        "start included, end excluded"
    )
    axis.set_ylabel(
        "empirical timing rank (0–1; larger means stronger relative signal)"
    )
    axis.set_ylim(0, 1.04)
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.25)
    best_start = pd.Timestamp(data.iloc[best_index]["date"])
    best_end = interval_end(best_start, scale)
    axis.text(
        x[best_index],
        max(0.04, selected[best_index] / 2),
        "HIGHEST-RANKED\nWINDOW",
        ha="center",
        va="center",
        fontsize=8,
        color="white",
        weight="bold",
    )
    axis.set_title(
        f"Timing forecast by complete {scale.display_singular}\n"
        f"Highest empirical rank {selected[best_index]:.3f}: "
        f"[{best_start:%Y-%m-%d} – {best_end:%Y-%m-%d})",
        weight="bold",
    )
    fig.tight_layout()
    finish(fig, path)


def timing_forecast_figure(path: Path):
    """Render one uncluttered score series and its configured primary selection."""
    selection = forecast_peak_mode_frame()
    if selection.empty:
        _legacy_timing_forecast_figure(path)
        return
    row = selection.iloc[0]
    score_path_text = str(row.get("score_csv", "")).strip()
    score_column = str(row.get("score_column", "")).strip()
    if score_path_text and score_column:
        score_frame = pd.read_csv(Path(score_path_text))
    else:
        score_frame = pd.read_csv(
            PROJECT / "05_ensemble/timing/forecast_predictions.csv"
        )
        score_column = "score_percentile_not_probability"
    if score_column not in score_frame:
        raise ValueError(f"Selected timing score column is absent: {score_column}")
    dates = score_frame["date"].astype(str).tolist()
    selected_date = str(row["date"])
    if selected_date not in dates:
        raise RuntimeError("Primary timing selection is outside the displayed grid")
    selected_index = dates.index(selected_date)
    scores = score_frame[score_column].to_numpy(float)
    x = np.arange(len(score_frame), dtype=float) + 0.5
    historical, history_audit = historical_forecast_comparison()
    historical_scores = None
    if not historical.empty:
        if historical["date"].astype(str).tolist() != dates:
            raise RuntimeError(
                "Historical-record comparison does not share the primary grid"
            )
        historical_scores = historical[
            "historical_record_shuffle_score"
        ].to_numpy(float)
    source_label = str(row.get("source_mode", "selected score")).replace(
        "_", " "
    )
    fig, axis = plt.subplots(figsize=(14.8, 5.8))
    axis.plot(
        x,
        scores,
        color="#4c51bf",
        marker="o",
        markersize=5.2,
        markerfacecolor="white",
        markeredgewidth=1.5,
        linewidth=2.5,
        label=source_label,
        zorder=3,
    )
    if historical_scores is not None:
        axis.plot(
            x,
            historical_scores,
            color="#2f855a",
            marker="s",
            markersize=4.7,
            linestyle="--",
            linewidth=1.9,
            label=(
                "intact historical-record shuffle "
                f"(validation {history_audit['history_validation_quality']:.3f})"
            ),
            zorder=2,
        )

    highlight_indices: list[int] = []
    if FORECAST_HIGHLIGHT_THRESHOLD is not None:
        highlight_indices = np.flatnonzero(
            scores >= FORECAST_HIGHLIGHT_THRESHOLD
        ).tolist()
        axis.axhline(
            FORECAST_HIGHLIGHT_THRESHOLD,
            color="#c05621",
            linestyle="--",
            linewidth=1.5,
            alpha=0.85,
            label=f"configured score floor {FORECAST_HIGHLIGHT_THRESHOLD:.2f}",
            zorder=1,
        )
    if not highlight_indices:
        highlight_indices = [selected_index]
    for index in highlight_indices:
        if index == selected_index:
            continue
        axis.axvspan(
            index,
            index + 1.0,
            color="#ed8936",
            alpha=0.055,
            zorder=0,
        )
    axis.scatter(
        x[highlight_indices],
        scores[highlight_indices],
        s=78,
        color="#ed8936",
        edgecolor="white",
        linewidth=1.1,
        label=(
            f"bins meeting ≥ {FORECAST_HIGHLIGHT_THRESHOLD:.2f}"
            if FORECAST_HIGHLIGHT_THRESHOLD is not None
            else "selected peak"
        ),
        zorder=5,
    )
    for order, index in enumerate(highlight_indices):
        if index == selected_index:
            continue
        offset = 12 if order % 2 == 0 else -20
        axis.annotate(
            f"{scores[index]:.3f}",
            (x[index], scores[index]),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if offset > 0 else "top",
            fontsize=8.0,
            color="#9c4221",
            weight="bold",
        )

    mode = str(row["selection_mode"])
    focus_color = selection_mode_color(mode)
    axis.axvspan(
        selected_index,
        selected_index + 1.0,
        color=focus_color,
        alpha=0.18,
        zorder=0,
    )
    axis.axvline(
        x[selected_index],
        color=focus_color,
        linewidth=1.8,
        alpha=0.75,
        zorder=1,
    )
    axis.scatter(
        [x[selected_index]],
        [scores[selected_index]],
        s=235,
        facecolor="#fffaf0",
        edgecolor=focus_color,
        linewidth=3.0,
        zorder=7,
    )
    selected_start = pd.Timestamp(selected_date)
    selected_end = interval_end(selected_start, report_time_scale())
    axis.annotate(
        f"{selection_mode_label(mode).upper()}\n"
        f"[{selected_start:%Y-%m-%d} – {selected_end:%Y-%m-%d})  ·  "
        f"score {scores[selected_index]:.3f}",
        (x[selected_index], scores[selected_index]),
        xytext=(18, 32),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=8.7,
        color=focus_color,
        weight="bold",
        bbox=dict(
            boxstyle="round,pad=0.32",
            facecolor="white",
            edgecolor=focus_color,
            alpha=0.94,
        ),
        arrowprops=dict(
            arrowstyle="-|>",
            color=focus_color,
            linewidth=1.3,
        ),
        zorder=8,
    )
    overlay, overlay_audit = forecast_overlay_frame(score_frame)
    if not overlay.empty:
        overlay_label = (
            "external CSV points"
            if overlay_audit["projection_mode"] == "identity_0_1"
            else "external CSV points (min–max projected)"
        )
        axis.scatter(
            overlay["plot_x"].to_numpy(float) + 0.5,
            overlay["projected_y"].to_numpy(float),
            marker="o",
            s=58,
            facecolor="#d53f8c",
            edgecolor="white",
            linewidth=0.9,
            label=overlay_label,
            zorder=7,
        )
        for row in overlay.itertuples():
            if row.point_label:
                axis.annotate(
                    row.point_label,
                    (row.plot_x + 0.5, row.projected_y),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=6.6,
                    color="#97266d",
                )

    tick_step = max(1, int(np.ceil(len(x) / 9)))
    labelled_indices = set(range(0, len(x), tick_step)) | {
        selected_index,
        len(x) - 1,
    }
    apply_interval_boundary_axis(
        axis,
        np.arange(len(score_frame) + 1, dtype=float),
        x,
        [
            interval_label(
                pd.Timestamp(score_frame.iloc[index]["date"]),
                report_time_scale(),
                multiline=True,
            )
            if index in labelled_indices else ""
            for index in range(len(score_frame))
        ],
        rotation=25,
        fontsize=8.2,
    )
    axis.set_xlim(0.0, float(len(score_frame)))
    displayed_score_arrays = [scores]
    if historical_scores is not None:
        displayed_score_arrays.append(historical_scores)
    if not overlay.empty:
        displayed_score_arrays.append(
            overlay["projected_y"].to_numpy(float)
        )
    all_displayed_scores = np.concatenate(displayed_score_arrays)
    lower = max(0.0, float(np.min(all_displayed_scores)) - 0.10)
    upper = min(1.05, float(np.max(all_displayed_scores)) + 0.16)
    if upper - lower < 0.38:
        upper = min(1.05, lower + 0.38)
    axis.set_ylim(lower, upper)
    scale = report_time_scale()
    axis.set_xlabel(
        f"Complete {scale.display_singular} bins; selected annotation gives the exact [start, end) interval"
    )
    axis.set_ylabel(
        "relative timing score (0–1; not a calibrated probability)"
    )
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.25)
    axis.legend(
        loc="lower left",
        ncol=1,
        fontsize=8.0,
        frameon=False,
    )
    axis.set_title(
        f"Timing forecast — {source_label}\n"
        f"primary rule: {selection_mode_label(mode)}",
        weight="bold",
        pad=10,
    )
    fig.tight_layout()
    finish(fig, path)


def forecast_event_context_figure(path: Path):
    """Plot the weekly forecast relative to the observed 28 July event."""
    context = json.loads(
        (
            PROJECT / "05_ensemble/timing/forecast_event_context.json"
        ).read_text()
    )
    primary = pd.read_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv"
    )
    history_path = (
        PROJECT / "07_historical_record_shuffle/timing/forecast.csv"
    )
    history = pd.read_csv(history_path) if history_path.is_file() else None
    x = np.arange(len(primary), dtype=float) + 0.5
    primary_scores = primary[
        "score_percentile_not_probability"
    ].to_numpy(float)
    fig, axis = plt.subplots(figsize=(14.4, 5.8))
    axis.plot(
        x,
        primary_scores,
        color="#1f4e79",
        marker="o",
        linewidth=2.5,
        label="chronological incremental",
    )
    if history is not None:
        axis.plot(
            x,
            history["historical_record_shuffle_score"].to_numpy(float),
            color="#2f855a",
            marker="s",
            linestyle="--",
            linewidth=2.1,
            label="intact historical-record shuffle",
        )
    date_to_index = {
        str(value): index
        for index, value in enumerate(primary["date"].astype(str))
    }
    role_style = {
        "observed_reference_event_bin": (
            "#6b7280",
            "X",
            "observed M6.8 reference bin",
        ),
        "first_significant_post_event_peak": (
            "#d97706",
            "^",
            "first significant post-event peak",
        ),
        "maximum_post_event_peak": (
            "#c53030",
            "*",
            "maximum post-event peak",
        ),
    }
    used_roles = set()
    for selection in context["selections"]:
        role = selection["role"]
        index = date_to_index[str(selection["date"])]
        color, marker, label = role_style[role]
        if role == "observed_reference_event_bin":
            axis.axvspan(
                index,
                index + 1.0,
                color=color,
                alpha=0.10,
                zorder=0,
            )
        axis.scatter(
            [x[index]],
            [primary_scores[index]],
            marker=marker,
            s=170 if marker == "*" else 100,
            color=color,
            edgecolor="white",
            linewidth=0.9,
            label=label if role not in used_roles else None,
            zorder=5,
        )
        used_roles.add(role)
        axis.annotate(
            f"{primary_scores[index]:.3f}",
            (x[index], primary_scores[index]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=color,
            weight="bold",
        )
    anchor = context["anchor_event"]
    apply_interval_boundary_axis(
        axis,
        np.arange(len(primary) + 1, dtype=float),
        x,
        exact_slot_labels(primary),
        rotation=25,
        fontsize=8,
    )
    axis.set_xlim(0.0, float(len(primary)))
    displayed_scores = [primary_scores]
    if history is not None:
        displayed_scores.append(
            history["historical_record_shuffle_score"].to_numpy(float)
        )
    all_displayed_scores = np.concatenate(displayed_scores)
    lower = max(0.0, float(np.min(all_displayed_scores)) - 0.12)
    upper = min(1.24, float(np.max(all_displayed_scores)) + 0.25)
    if upper - lower < 0.45:
        upper = min(1.24, lower + 0.45)
    axis.set_ylim(lower, upper)
    axis.set_ylabel("relative timing score (not probability or magnitude)")
    axis.set_xlabel("weekly bin labels use [start, end); date is bin start")
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.25)
    axis.legend(
        loc="upper center",
        ncol=3,
        fontsize=7.7,
        frameon=True,
        facecolor="white",
        framealpha=0.94,
        borderpad=0.8,
    )
    axis.set_title(
        "Focused weekly revalidation after the observed reference event\n"
        f"{anchor['time'][:10]} · M{anchor['magnitude']:.1f} · "
        "future peaks rank the experimental "
        f"M{report_target_magnitude_label()}+ timing signal only",
        fontsize=10.5,
        weight="bold",
        pad=10,
    )
    fig.tight_layout()
    finish(fig, path)


def map_axis(fig=None, rect=None):
    if fig is None:
        fig, axis = plt.subplots(figsize=(10.2, 8.2))
    else:
        axis = fig.add_subplot(rect)
    zone_grid = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_decision_grid.csv"
    )
    latitude_min = float(zone_grid["latitude"].min())
    latitude_max = float(zone_grid["latitude"].max())
    longitude_min = float(zone_grid["longitude"].min())
    longitude_max = float(zone_grid["longitude"].max())
    latitude_margin = max(0.25, 0.025 * (latitude_max - latitude_min))
    longitude_margin = max(0.25, 0.025 * (longitude_max - longitude_min))
    map_view = Basemap(
        projection="merc",
        llcrnrlon=longitude_min - longitude_margin,
        llcrnrlat=latitude_min - latitude_margin,
        urcrnrlon=longitude_max + longitude_margin,
        urcrnrlat=latitude_max + latitude_margin,
        resolution="i",
        ax=axis,
    )
    map_view.drawmapboundary(fill_color="#eaf4fb")
    map_view.fillcontinents(color="#f2efe5", lake_color="#eaf4fb")
    map_view.drawcoastlines(color="#666666", linewidth=0.7)
    map_view.drawcountries(color="#888888", linewidth=0.4)
    map_view.drawparallels(
        np.linspace(latitude_min, latitude_max, 9),
        labels=[1, 0, 0, 0],
        color="#9aa6b2",
        linewidth=0.4,
        dashes=[2, 3],
        fontsize=8,
    )
    map_view.drawmeridians(
        np.linspace(longitude_min, longitude_max, 11),
        labels=[0, 0, 0, 1],
        color="#9aa6b2",
        linewidth=0.4,
        dashes=[2, 3],
        fontsize=8,
    )
    return fig, axis, map_view


def draw_zone_decision_regions(axis, map_view, alpha: float = 0.18) -> int:
    """Draw exhaustive GMM territories; every map cell has exactly one zone."""
    grid = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_decision_grid.csv"
    )
    latitudes = np.sort(grid["latitude"].unique())
    longitudes = np.sort(grid["longitude"].unique())
    zone_matrix = (
        grid.pivot(index="latitude", columns="longitude", values="zone")
        .reindex(index=latitudes, columns=longitudes)
        .to_numpy(int)
    )
    longitude_mesh, latitude_mesh = np.meshgrid(longitudes, latitudes)
    x, y = map_view(longitude_mesh, latitude_mesh)
    maximum_zone = int(zone_matrix.max())
    cmap = ListedColormap(
        [ZONE_COLORS[zone] for zone in range(1, maximum_zone + 1)]
    )
    norm = BoundaryNorm(
        np.arange(0.5, maximum_zone + 1.5, 1.0),
        cmap.N,
    )
    map_view.pcolormesh(
        x,
        y,
        zone_matrix,
        cmap=cmap,
        norm=norm,
        shading="nearest",
        alpha=alpha,
        ax=axis,
        zorder=1,
    )
    if maximum_zone > 1:
        map_view.contour(
            x,
            y,
            zone_matrix,
            levels=np.arange(1.5, maximum_zone, 1.0),
            colors="#596579",
            linewidths=0.75,
            alpha=0.70,
            ax=axis,
            zorder=2,
        )
    map_view.drawcoastlines(color="#5f6368", linewidth=0.8, zorder=3)
    map_view.drawcountries(color="#777777", linewidth=0.45, zorder=3)
    return maximum_zone


def add_zone_number(axis, map_view, zone: dict, selected: bool = False):
    zone_id = int(zone["zone"])
    center_x, center_y = map_view(
        zone["center_longitude"], zone["center_latitude"]
    )
    axis.text(
        center_x,
        center_y,
        str(zone_id),
        ha="center",
        va="center",
        fontsize=15 if selected else 12,
        weight="bold",
        color="white",
        bbox=dict(
            boxstyle="circle,pad=0.34",
            facecolor=ZONE_COLORS[zone_id],
            edgecolor="black" if selected else "white",
            linewidth=2.0 if selected else 1.0,
        ),
        zorder=7,
    )


def add_zone_rectangle(axis, map_view, zone: dict, alpha: float, linewidth: float):
    x1, y1 = map_view(zone["longitude_low"], zone["latitude_low"])
    x2, y2 = map_view(zone["longitude_high"], zone["latitude_high"])
    color = ZONE_COLORS[int(zone["zone"])]
    axis.add_patch(
        Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            facecolor=color,
            edgecolor=color,
            alpha=alpha,
            linewidth=linewidth,
        )
    )


def location_zone_map(path: Path, summary: dict):
    events = pd.read_csv(PROJECT / "05_ensemble/location_zone_event_catalog.csv")
    fig, axis, map_view = map_axis()
    draw_zone_decision_regions(axis, map_view, alpha=0.20)
    for zone in summary["zones"]:
        add_zone_number(axis, map_view, zone)
    for zone, group in events.groupby("zone"):
        x, y = map_view(group["longitude"].to_numpy(), group["latitude"].to_numpy())
        axis.scatter(
            x,
            y,
            s=20,
            color=ZONE_COLORS[int(zone)],
            edgecolor="white",
            linewidth=0.35,
            alpha=0.80,
            label=f"zone {int(zone)} events",
            zorder=5,
        )
    axis.set_title(
        f"Learned geographic seismic zones — predictive target "
        f"M≥{summary['magnitude_threshold']:.1f}\n"
        f"Zone geometry uses pre-cutoff catalogue coordinates "
        f"M≥{summary['zone_catalog']['magnitude_threshold']:.1f} · "
        f"{summary['zone_construction_events']} construction events; "
        f"{summary['zone_count']} numbered zones\n"
        "Colours cover the complete map; dots are historical construction events",
        weight="bold",
    )
    finish(fig, path)


def location_validation_figure(path: Path):
    data = pd.read_csv(PROJECT / "05_ensemble/location_zone_validation.csv")
    x = np.arange(len(data))
    zones = pd.read_csv(PROJECT / "05_ensemble/location_zones.csv")
    maximum_zone = int(zones["zone"].max())
    fig, axis = plt.subplots(figsize=(13.8, 6.6))
    exact_match = np.array_equal(
        data["actual_zone"].to_numpy(int),
        data["predicted_zone"].to_numpy(int),
    )
    reliability = report_composite().get("localization", {}).get(
        "reliability", {}
    )
    single_zone_holdout = (
        int(reliability.get("distinct_validation_zones", 0)) == 1
    )
    display_offset = 0.045 if exact_match else 0.0
    actual_display = data["actual_zone"].to_numpy(float) - display_offset
    predicted_display = data["predicted_zone"].to_numpy(float) + display_offset
    axis.plot(
        x,
        actual_display,
        color="#d62728",
        marker="o",
        markersize=11,
        linewidth=5.0,
        alpha=0.48,
        label="actual validation-zone trend",
        zorder=3,
    )
    axis.plot(
        x,
        predicted_display,
        color="#2b70b8",
        marker="s",
        markersize=7,
        linestyle="--",
        linewidth=2.6,
        label="ensemble-predicted zone trend",
        zorder=4,
    )
    for index, row in enumerate(data.itertuples()):
        matched = int(row.actual_zone) == int(row.predicted_zone)
        axis.annotate(
            f"{'MATCH' if matched else 'MISS'}\n"
            f"real Z{int(row.actual_zone)} · predicted Z{int(row.predicted_zone)}",
            (index, actual_display[index]),
            xytext=(0, 16 if index % 2 == 0 else -38),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
            color="#276749" if matched else "#b22222",
            weight="bold",
        )
    labels = [
        f"{row.date}\nM{row.mag:.1f}\n{row.event_id}"
        for row in data.itertuples()
    ]
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=24, ha="right", fontsize=8)
    axis.set_yticks(np.arange(1, maximum_zone + 1))
    axis.set_ylim(0.5, maximum_zone + 0.5)
    axis.set_ylabel("numbered joint seismic zone")
    axis.set_xlabel("chronological outer-validation events")
    axis.grid(True, color="#9aa6b2", alpha=0.28, linewidth=0.8)
    axis.legend(
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 1.13),
    )
    fig.suptitle(
        "Location validation — actual versus ensemble-predicted zone trend\n"
        + (
            (
                f"Exact agreement {len(data)}/{len(data)}, but every holdout is "
                f"Zone {int(reliability['majority_zone'])}: exact accuracy is "
                "non-discriminating; confidence and distance are assessed next"
            )
            if exact_match and single_zone_holdout
            else (
                f"Perfect overlap — 100% exact-zone agreement ({len(data)}/{len(data)}); "
                "±0.045 display offset makes both lines visible"
            )
            if exact_match
            else f"discrete Y axis spans every learned zone: 1–{maximum_zone}"
        ),
        fontsize=15,
        weight="bold",
        y=0.98,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    finish(fig, path)


def location_ranking_figure(path: Path):
    data = pd.read_csv(PROJECT / "05_ensemble/location_zone_system_ranking.csv")
    data = data.sort_values("rank", ascending=False)
    y = np.arange(len(data))
    fig, axis = plt.subplots(figsize=(12.5, 7.2))
    training = data["training_quality"].to_numpy(float)
    validation = data["validation_quality"].to_numpy(float)
    for index in range(len(data)):
        axis.plot(
            [training[index], validation[index]],
            [index, index],
            color="#aeb8c2",
            linewidth=2.0,
        )
    axis.scatter(training, y, color="#2b70b8", label="training quality", zorder=3)
    axis.scatter(validation, y, color="#f28e2b", marker="D", label="validation quality", zorder=3)
    for index, row in enumerate(data.itertuples()):
        axis.text(
            min(training[index], validation[index]) - 0.012,
            index,
            str(row.rank),
            ha="right",
            va="center",
            fontsize=8,
            weight="bold",
        )
        if row.rank <= 3:
            axis.text(
                max(training[index], validation[index]) + 0.015,
                index,
                str(row.rank),
                ha="center",
                va="center",
                color="white",
                weight="bold",
                bbox=dict(boxstyle="circle,pad=0.25", facecolor="#e15759", edgecolor="none"),
            )
    axis.set_yticks(y)
    axis.set_yticklabels(data["system"])
    axis.set_xlabel("quality — higher is better")
    axis.grid(True, axis="x", color="#9aa6b2", alpha=0.25)
    axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
    )
    axis.set_title("Joint-zone system ranking — ranks 1, 2 and 3 marked in-grid")
    fig.tight_layout(rect=(0, 0.08, 1, 1.0))
    finish(fig, path)


def fusion_display_name(raw_name: str) -> str:
    """Translate internal fusion tokens into reader-facing descriptions."""
    raw_name = str(raw_name)
    match = re.search(r"_prior_correct_([0-9.]+)$", raw_name)
    strength = float(match.group(1)) if match else None
    base = raw_name[: match.start()] if match else raw_name
    base_names = {
        "best_single": "Best individual zone model",
        "top3_hard_vote": "Top three models — majority vote",
        "top3_soft_probability": "Top three models — weighted scores",
        "diverse3_soft_probability": "Three diverse models — weighted scores",
        "five_bases_soft_probability": "Five base models — weighted scores",
        "all16_quality_soft_probability": "All sixteen systems — quality-weighted scores",
        "top3_soft_probability_diversity_guard": (
            "Top three diverse models — reliability-guarded weighted scores"
        ),
    }
    label = base_names.get(base, base.replace("_", " ").title())
    if strength is not None:
        label += (
            f"\n+ historical-zone frequency adjustment "
            f"{strength:.0%}"
        )
    else:
        label += "\n+ no historical-frequency adjustment"
    return label


def fusion_ranking_figure(path: Path):
    data = pd.read_csv(PROJECT / "05_ensemble/location_zone_fusion_trials.csv")
    data = data.sort_values("quality_higher_is_better", ascending=False).head(12)
    data = data.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(data))
    fig, axis = plt.subplots(figsize=(13.8, 8.2))
    min_val = data["quality_higher_is_better"].min()
    max_val = data["quality_higher_is_better"].max()
    axis.hlines(
        y,
        min_val - 0.02,
        data["quality_higher_is_better"],
        color="#aeb8c2",
        linewidth=2,
    )
    axis.scatter(
        data["quality_higher_is_better"],
        y,
        color="#2b70b8",
        s=50,
        zorder=3,
    )
    rank = np.arange(len(data), 0, -1)
    for index, value in enumerate(rank):
        if value <= 3:
            axis.text(
                data["quality_higher_is_better"].iloc[index] + 0.005,
                index,
                str(value),
                ha="center",
                va="center",
                color="white",
                weight="bold",
                fontsize=9,
                bbox=dict(boxstyle="circle,pad=0.25", facecolor="#e15759", edgecolor="none"),
            )
        else:
            axis.text(
                data["quality_higher_is_better"].iloc[index] + 0.003,
                index,
                str(value),
                va="center",
                weight="bold",
                fontsize=10.5,
            )
    axis.set_yticks(y)
    axis.set_yticklabels(
        [fusion_display_name(value) for value in data["fusion"]],
        fontsize=10.5,
    )
    axis.set_xlim(min_val - 0.03, max_val + 0.045)
    axis.set_xlabel("outer-validation quality — higher is better", fontsize=11)
    axis.grid(True, axis="x", color="#9aa6b2", alpha=0.25)
    axis.set_title(
        "Location fusion comparison — best 12 configurations\n"
        "35% / 65% / 100% indicate adjustment strength for historically "
        "common zones; they are not accuracy values",
        fontsize=12.5,
        weight="bold",
    )
    fig.tight_layout()
    finish(fig, path)


def location_forecast_figure(path: Path):
    """Essential fused localization forecast on a discrete zone axis."""
    data = pd.read_csv(PROJECT / "05_ensemble/location_zone_forecast.csv")
    zones = pd.read_csv(PROJECT / "05_ensemble/location_zones.csv")
    maximum_zone = int(zones["zone"].max())
    x = np.arange(len(data), dtype=float) + 0.5
    predicted = data["predicted_zone"].to_numpy(int)
    confidence = data["predicted_zone_confidence"].to_numpy(float)
    peak_modes = forecast_peak_mode_frame()
    if peak_modes.empty:
        timing = pd.read_csv(
            PROJECT / "05_ensemble/timing/forecast_predictions.csv"
        )
        timing_focus = timing.loc[
            timing["score_percentile_not_probability"].idxmax()
        ]
        peak_modes = pd.DataFrame(
            [
                {
                    "source_mode": "chronological_incremental",
                    "selection_mode": "maximum_peak",
                    "date": str(timing_focus["date"]),
                    "coincides_with_other_selection": True,
                }
            ]
        )
    date_to_index = {
        str(date): index
        for index, date in enumerate(data["date"].astype(str))
    }
    band_handles: dict[str, Patch] = {}
    fig, axis = plt.subplots(figsize=(14.8, 6.2))
    for date, group in peak_modes.groupby("date", sort=False):
        focus_index = date_to_index[str(date)]
        focus_x = x[focus_index]
        mode = str(group.iloc[0]["selection_mode"])
        color = selection_mode_color(mode)
        mode_label = selection_mode_label(mode)
        axis.axvspan(
            focus_index,
            focus_index + 1.0,
            color=color,
            alpha=0.12,
            zorder=0,
        )
        sources = compact_mode_sources(
            sorted(group["source_mode"].astype(str).unique())
        )
        axis.text(
            focus_x,
            maximum_zone + 0.74,
            f"{mode_label.upper()}\n{sources}",
            ha="center",
            va="top",
            fontsize=7.3,
            color=color,
            weight="bold",
        )
        axis.scatter(
            [focus_x],
            [predicted[focus_index]],
            s=175,
            facecolor="none",
            edgecolor=color,
            linewidth=2.2,
            zorder=6,
        )
        band_handles.setdefault(
            mode_label,
            Patch(
                facecolor=color,
                alpha=0.18,
                label=f"{mode_label} timing slot",
            ),
        )
    axis.plot(
        x,
        predicted,
        color="#2b70b8",
        linewidth=2.8,
        marker="s",
        markersize=6,
        label="fused forecast zone",
    )
    for index, (zone, score) in enumerate(zip(predicted, confidence)):
        axis.annotate(
            f"Z{zone} · {score:.3f}",
            (x[index], zone),
            xytext=(
                0,
                -24 if zone == maximum_zone else 12,
            ),
            textcoords="offset points",
            ha="center",
            fontsize=7.3,
            color="#334e68",
        )
    axis.set_xlim(0.0, float(len(data)))
    axis.set_ylim(0.5, maximum_zone + 1.0)
    axis.set_yticks(np.arange(1, maximum_zone + 1))
    axis.set_ylabel("fused forecast zone")
    apply_interval_boundary_axis(
        axis,
        np.arange(len(data) + 1, dtype=float),
        x,
        exact_slot_labels(data),
        rotation=34,
        fontsize=7.5,
    )
    axis.set_xlabel(
        f"each X label is one {report_time_scale().display_singular} "
        "[start, end); boundary intervals are shown in full"
    )
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.26)
    handles, labels = axis.get_legend_handles_labels()
    handles.extend(band_handles.values())
    labels.extend(handle.get_label() for handle in band_handles.values())
    axis.legend(
        handles,
        labels,
        loc="lower center",
        ncol=min(3, len(handles)),
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        fontsize=7.8,
    )
    axis.set_title(
        f"One-shot localization forecast on the configured "
        f"{report_time_scale().display_singular} grid\n"
        "one fitted location model; the band follows the configured primary "
        "timing selection",
        weight="bold",
        pad=9,
    )
    fig.tight_layout()
    finish(fig, path)


def centroid_coordinate_figure(path: Path):
    """Render coordinate values implied by the categorical zone forecast."""
    forecast = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_forecast.csv"
    )
    validation = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_validation.csv"
    )
    zones = pd.read_csv(PROJECT / "05_ensemble/location_zones.csv").set_index(
        "zone"
    )
    peak_modes = forecast_peak_mode_frame()
    forecast["centroid_latitude"] = forecast["predicted_zone"].map(
        zones["center_latitude"]
    )
    forecast["centroid_longitude"] = forecast["predicted_zone"].map(
        zones["center_longitude"]
    )
    validation["predicted_centroid_latitude"] = validation[
        "predicted_zone"
    ].map(zones["center_latitude"])
    validation["predicted_centroid_longitude"] = validation[
        "predicted_zone"
    ].map(zones["center_longitude"])
    x_forecast = np.arange(len(forecast), dtype=float) + 0.5
    x_validation = np.arange(len(validation))
    date_to_index = {
        str(date): index
        for index, date in enumerate(forecast["date"].astype(str))
    }
    selected_indices = {
        date_to_index[str(date)]
        for date in peak_modes["date"].astype(str).unique()
    } if not peak_modes.empty else set()
    fig, axes = plt.subplots(2, 2, figsize=(15.6, 8.2))
    forecast_specs = [
        (
            axes[0, 0],
            "centroid_latitude",
            "Latitude implied by selected zone",
            "latitude (degrees north)",
            "#2b70b8",
        ),
        (
            axes[0, 1],
            "centroid_longitude",
            "Longitude implied by selected zone",
            "longitude (degrees east)",
            "#7a5195",
        ),
    ]
    for axis, column, title, ylabel, color in forecast_specs:
        for date, group in peak_modes.groupby("date", sort=False):
            focus_index = date_to_index[str(date)]
            band_color = selection_mode_color(
                str(group.iloc[0]["selection_mode"])
            )
            axis.axvspan(
                focus_index,
                focus_index + 1.0,
                color=band_color,
                alpha=0.10,
                zorder=0,
            )
        axis.plot(
            x_forecast,
            forecast[column],
            color=color,
            marker="o",
            linewidth=2.3,
        )
        for index, value in enumerate(forecast[column]):
            changed = (
                index == 0
                or not np.isclose(
                    value,
                    float(forecast[column].iloc[index - 1]),
                )
            )
            if changed or index in selected_indices:
                axis.annotate(
                    f"{value:.2f}°",
                    (x_forecast[index], value),
                    xytext=(0, 9),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                )
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        apply_interval_boundary_axis(
            axis,
            np.arange(len(forecast) + 1, dtype=float),
            x_forecast,
            exact_slot_labels(forecast),
            rotation=24,
            fontsize=7.0,
        )
        axis.set_xlim(0.0, float(len(forecast)))
        axis.grid(True, axis="y", color="#9aa6b2", alpha=0.24)

    validation_specs = [
        (
            axes[1, 0],
            "latitude",
            "predicted_centroid_latitude",
            "Validation latitude: real event versus predicted-zone centroid",
            "latitude (degrees north)",
        ),
        (
            axes[1, 1],
            "longitude",
            "predicted_centroid_longitude",
            "Validation longitude: real event versus predicted-zone centroid",
            "longitude (degrees east)",
        ),
    ]
    validation_labels = [
        f"{row.date}\nM{row.mag:.1f}"
        for row in validation.itertuples()
    ]
    for axis, actual_column, centroid_column, title, ylabel in validation_specs:
        axis.plot(
            x_validation,
            validation[actual_column],
            color="#d62728",
            marker="o",
            linewidth=2.2,
            label="real event coordinate",
        )
        axis.plot(
            x_validation,
            validation[centroid_column],
            color="#2b70b8",
            marker="s",
            linestyle="--",
            linewidth=2.0,
            label="centroid of predicted zone",
        )
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.set_xticks(x_validation)
        axis.set_xticklabels(
            validation_labels, rotation=28, ha="right", fontsize=7
        )
        axis.grid(True, color="#9aa6b2", alpha=0.24)
        axis.legend(
            frameon=True,
            facecolor="white",
            framealpha=0.90,
            fontsize=7.2,
            ncol=1,
            loc="best",
        )
    fig.suptitle(
        "Centroid coordinate interpretation of the same zone forecast\n"
        "These latitude/longitude values are zone reference points, "
        "not an independent coordinate prediction",
        fontsize=14,
        weight="bold",
    )
    fig.subplots_adjust(
        left=0.07,
        right=0.985,
        bottom=0.13,
        top=0.84,
        wspace=0.22,
        hspace=0.56,
    )
    finish(fig, path)


def location_forecast_technical_figure(path: Path):
    data = pd.read_csv(PROJECT / "05_ensemble/location_zone_forecast.csv")
    x = np.arange(len(data), dtype=float) + 0.5
    step_x = np.arange(len(data) + 1, dtype=float)
    zone_columns = [column for column in data if column.startswith("zone_") and column.endswith("_vote")]
    fig, axes = plt.subplots(2, 1, figsize=(14.8, 7.4), sharex=True)
    for zone, column in enumerate(zone_columns, 1):
        values = data[column].to_numpy(float)
        axes[0].step(
            step_x,
            np.r_[values, values[-1]],
            where="post",
            color=ZONE_COLORS[zone],
            label=f"zone {zone} score",
        )
        axes[0].scatter(x, values, s=18, color=ZONE_COLORS[zone], zorder=4)
    axes[1].step(
        step_x,
        np.r_[data["predicted_zone"], data["predicted_zone"].iloc[-1]],
        where="post",
        color="#2b70b8",
        linewidth=2.2,
        label="selected joint zone",
    )
    confidence = data["predicted_zone_confidence"].to_numpy(float)
    axes[1].step(
        step_x,
        np.r_[confidence, confidence[-1]],
        where="post",
        color="#f28e2b",
        linestyle="--",
        label="selected-zone score",
    )
    for axis in axes:
        axis.set_xlim(0, len(data))
        axis.grid(True, color="#9aa6b2", alpha=0.25)
        axis.legend(loc="upper center", ncol=3, frameon=False, fontsize=8)
    axes[0].set_ylabel("zone score")
    axes[1].set_ylabel("zone / score")
    apply_interval_boundary_axis(
        axes[1],
        step_x,
        x,
        exact_slot_labels(data),
        rotation=35,
        fontsize=7.5,
    )
    axes[1].set_xlabel(
        f"each X label is one {report_time_scale().display_singular} "
        "[start, end)"
    )
    fig.suptitle(
        "Technical diagnostic — score assigned to every geographic zone",
        fontsize=15,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    finish(fig, path)


def final_zone_map(path: Path, summary: dict):
    forecast = pd.read_csv(PROJECT / "05_ensemble/location_zone_forecast.csv")
    peak_modes = forecast_peak_mode_frame()
    if peak_modes.empty:
        timing = pd.read_csv(
            PROJECT / "05_ensemble/timing/forecast_predictions.csv"
        )
        timing_row = timing.loc[
            timing["score_percentile_not_probability"].idxmax()
        ]
        selected_rows = pd.DataFrame(
            [
                {
                    "date": str(timing_row["date"]),
                    "selection_mode": "maximum_peak",
                    "source_mode": "chronological_incremental",
                    "predicted_zone": int(
                        forecast.loc[
                            forecast["date"].eq(timing_row["date"]),
                            "predicted_zone",
                        ].iloc[0]
                    ),
                }
            ]
        )
    else:
        selected_rows = peak_modes.copy()
    selected_zones = set(selected_rows["predicted_zone"].astype(int))
    fig, axis, map_view = map_axis()
    draw_zone_decision_regions(axis, map_view, alpha=0.17)
    selected_zone_rows = []
    for zone in summary["zones"]:
        is_selected = int(zone["zone"]) in selected_zones
        if is_selected:
            selected_zone_rows.append(zone)
            add_zone_rectangle(
                axis,
                map_view,
                zone,
                alpha=0.24,
                linewidth=3.2,
            )
        add_zone_number(axis, map_view, zone, selected=is_selected)
    if len(selected_zone_rows) != len(selected_zones):
        raise RuntimeError(
            f"Selected zones {selected_zones} are absent from summary"
        )
    descriptions = []
    for date, group in selected_rows.groupby("date", sort=False):
        start = pd.Timestamp(date)
        interval_finish = interval_end(start, report_time_scale())
        mode_text = selection_mode_label(
            str(group.iloc[0]["selection_mode"])
        )
        sources = compact_mode_sources(
            sorted(group["source_mode"].astype(str).unique())
        )
        descriptions.append(
            f"{mode_text} "
            f"[{start:%Y-%m-%d} – {interval_finish:%Y-%m-%d}) → "
            f"zone {int(group.iloc[0]['predicted_zone'])} "
            f"({sources})"
        )
    selected_zone_text = ", ".join(
        f"zone {int(zone['zone'])}: "
        f"{zone['center_latitude']:.2f}°N, "
        f"{zone['center_longitude']:.2f}°E"
        for zone in selected_zone_rows
    )
    axis.set_title(
        "Timing-selected localization modes\n"
        + "\n".join(descriptions)
        + f"\nSelected centroid reference: {selected_zone_text}",
        fontsize=9.5,
        wrap=True,
        weight="bold",
    )
    finish(fig, path)


def markdown_table(frame: pd.DataFrame) -> str:
    value = frame.copy()
    for column in value:
        value[column] = value[column].map(
            lambda item: f"{item:.4f}"
            if isinstance(item, (float, np.floating))
            else str(item)
        )
    lines = [
        "| " + " | ".join(value.columns) + " |",
        "| " + " | ".join(["---"] * len(value.columns)) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(item).replace("|", "\\|") for item in row) + " |"
        for row in value.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def build_markdown(
    figures: list[Path],
    timing_event_figures: list[Path],
    timing_summary: dict,
    location_summary: dict,
):
    timing_forecast = pd.read_csv(PROJECT / "05_ensemble/timing/forecast_predictions.csv")
    location_forecast = pd.read_csv(PROJECT / "05_ensemble/location_zone_forecast.csv")
    manifest = json.loads((PROJECT / "00_config/run_manifest.json").read_text())
    narrative = json.loads(
        (PROJECT / "00_config/report_narrative.json").read_text()
    )
    parameters = manifest["parameters"]
    context_path = (
        PROJECT / "05_ensemble/timing/forecast_event_context.json"
    )
    context = (
        json.loads(context_path.read_text())
        if INCLUDE_OBSERVED_EVENT_CONTEXT and context_path.is_file()
        else None
    )
    context_explanation = None
    if context is not None:
        anchor = context["anchor_event"]
        first = next(
            row
            for row in context["selections"]
            if row["role"] == "first_significant_post_event_peak"
        )
        maximum = next(
            row
            for row in context["selections"]
            if row["role"] == "maximum_post_event_peak"
        )
        context_explanation = {
            "question": (
                "After the observed reference event, which weekly intervals "
                "rank first and highest in this focused "
                f"M{report_target_magnitude_label()}+ experiment?"
            ),
            "reading": (
                "Both training histories are lines on identical weekly bins. "
                "The gray X is the bin containing the observed event; the "
                "triangle and star identify post-event first and maximum peaks."
            ),
            "result": (
                f"The M{anchor['magnitude']:.1f} reference event maps to its "
                f"weekly bin. The first post-event selection starts "
                f"{first['date']}; the post-event maximum starts "
                f"{maximum['date']}."
            ),
            "caution": (
                "The vertical score does not predict magnitude and is not an "
                "earthquake probability. A higher score than the reference bin "
                "does not imply an event larger than the observed earthquake."
            ),
        }
    astro_audit_path = PROJECT / "00_config/astro_source_audit.json"
    observer = (
        json.loads(astro_audit_path.read_text())
        .get("required_contract", {})
        .get("observer", {})
        if astro_audit_path.is_file()
        else {}
    )
    observer_markdown = (
        f" **Observer:** {observer.get('label', 'configured')} at "
        f"{observer['latitude']:g}° N, {observer['longitude']:g}° E, "
        f"{observer['elevation_km']:g} km."
        if {
            "latitude",
            "longitude",
            "elevation_km",
        }.issubset(observer)
        else ""
    )
    primary_selection = forecast_peak_mode_frame()
    if primary_selection.empty:
        selected_timing = timing_forecast.loc[
            timing_forecast["score_percentile_not_probability"].idxmax()
        ]
    else:
        selected_timing = timing_forecast.loc[
            timing_forecast["date"].astype(str).eq(
                str(primary_selection.iloc[0]["date"])
            )
        ].iloc[0]
    selected_location = location_forecast.loc[
        location_forecast["date"].eq(selected_timing["date"])
    ].iloc[0]
    selected_start = pd.Timestamp(selected_timing["date"])
    scale = report_time_scale()
    selected_end = interval_end(selected_start, scale)
    zones = pd.DataFrame(location_summary["zones"])[
        [
            "zone",
            "zone_name",
            "events",
            "latitude_low",
            "latitude_high",
            "longitude_low",
            "longitude_high",
        ]
    ]
    zone_search = json.loads(
        (PROJECT / "02_audit/location_zone_search.json").read_text()
    )
    selected_zone_count = int(zone_search["selected"]["zones"])
    zone_trials = pd.DataFrame(zone_search["trials"])[
        [
            "zones",
            "silhouette_higher_is_better",
            "bic_skill_higher_is_better",
            "selection_quality_higher_is_better",
            "minimum_cluster_events",
        ]
    ].copy()
    zone_trials["selected"] = zone_trials["zones"].eq(selected_zone_count)
    peak_modes = forecast_peak_mode_frame()
    if peak_modes.empty:
        timing_selection_lines = [
            f"The selected local maximum applies to "
            f"`[{selected_start:%Y-%m-%d} – {selected_end:%Y-%m-%d})`, "
            f"with score "
            f"`{selected_timing['score_percentile_not_probability']:.3f}`.",
            "",
        ]
    else:
        peak_table = peak_modes[
            [
                "source_mode",
                "selection_mode",
                "date",
                "slot_end_inclusive",
                "score",
                "predicted_zone",
                "predicted_zone_confidence",
            ]
        ].copy()
        peak_table.columns = [
            "training history",
            "selection rule",
            "slot start",
            "slot end inclusive",
            "timing score",
            "location zone",
            "zone score",
        ]
        timing_selection_lines = [
            "The report uses one parameterized primary selection. Other peak "
            "rules remain in the machine-readable diagnostic audit but do not "
            "compete visually on the forecast page.",
            "",
            markdown_table(peak_table),
            "",
        ]
    if peak_modes.empty:
        essential_map_lines = [
            f"For the highest-scoring timing interval "
            f"`[{selected_start:%Y-%m-%d} – {selected_end:%Y-%m-%d})` the "
            f"fused localization selects zone "
            f"`{int(selected_location['predicted_zone'])}` with score "
            f"`{selected_location['predicted_zone_confidence']:.3f}`.",
            "",
        ]
    else:
        unique_mode_zones = sorted(
            peak_modes["predicted_zone"].astype(int).unique()
        )
        essential_map_lines = [
            "The map outlines the localization zone associated with the "
            "configured primary timing selection. The complete selection "
            "record appears in the Timing forecast section.",
            "",
            f"Unique selected localization zones: `{unique_mode_zones}`.",
            "",
        ]
    glossary_lines = []
    for item in narrative["vocabulary"]:
        glossary_lines.extend(
            [f"- **{item['term']}:** {item['definition']}", ""]
        )
    model_lines = []
    for item in narrative["model_families"]:
        model_lines.extend(
            [
                f"### {item['name']} — {item['expanded']}",
                "",
                f"{item['explanation']} {item['report_variants']}",
                "",
            ]
        )

    grid = report_grid_offset()
    grid_markdown_lines: list[str] = []
    if all(
        key in grid
        for key in (
            "reference_anchor_date",
            "reference_interval_days",
            "resolved_anchor_date",
            "offset_days_modulo_interval",
        )
    ):
        grid_markdown_lines = [
            "## Temporal grid overlap",
            "",
            f"This run uses {int(parameters['interval_days'])}-day bins anchored "
            f"at `{grid['resolved_anchor_date']}`. The declared reference "
            f"pipeline `{grid.get('reference_pipeline', 'reference')}` uses "
            f"{int(grid['reference_interval_days'])}-day bins anchored at "
            f"`{grid['reference_anchor_date']}`.",
            "",
            f"The audited relation is `(new anchor − reference anchor) mod "
            f"{int(parameters['interval_days'])} days = "
            f"{int(grid['offset_days_modulo_interval'])} days`. This changes "
            "bin overlap only; it does not merge model scores across pipelines.",
            "",
        ]

    def explanation_lines(key: str) -> list[str]:
        item = narrative["figures"][key]
        return [
            f"**Question answered:** {item['question']}",
            "",
            f"**How to read it:** {item['reading']}",
            "",
            f"**Result in this run:** {item['result']}",
            "",
            f"**Limitation:** {item['caution']}",
            "",
        ]

    lines = [
        f"# Experimental {parameters['region_label']} earthquake timing and localization forecast",
        "",
        "**Methods:** KAN, LCS and deep-learning ensembles using Solar System "
        f"body-position features. **Forecast window:** "
        f"{parameters['forecast_start']}–{parameters['forecast_end']}. "
        f"**Region:** {parameters['region_label']}. **Outputs:** "
        f"{scale.display_plural} and numbered "
        f"joint geographic zones.{observer_markdown}",
        "",
        "## Autonomous agentic pipeline",
        "",
        narrative["executive_purpose"]["plain_language"],
        "",
        narrative["executive_purpose"]["why_agentic"],
        "",
        narrative["executive_purpose"]["what_is_new"],
        "",
        *grid_markdown_lines,
        "## Vocabulary used in the report",
        "",
        *glossary_lines,
        "## Model families and report variants",
        "",
        *model_lines,
        "## Essential result map",
        "",
        f"![Essential result map]({figures[10].name})",
        "",
        *explanation_lines("essential_map"),
        *essential_map_lines,
        "The coloured background is the exhaustive GMM classification: every "
        "map cell belongs to exactly one numbered zone. Only the selected zone's "
        "core historical envelope is shown as a high-contrast rectangle; that "
        "rectangle is not the full zone boundary.",
        "",
        "## Timing forecast",
        "",
        f"![Timing forecast]({figures[3].name})",
        "",
        *explanation_lines("timing_forecast"),
        *timing_selection_lines,
        "Curves use start-based interval markers: the marker is the interval "
        "start and the value "
        "extends forward until the next slot start. Thus the peak belongs to the "
        "whole interval; it is not a prediction for its final calendar date.",
        "",
        "## Timing validation",
        "",
        f"![Timing validation]({figures[0].name})",
        "",
        *explanation_lines("timing_validation"),
        "This is one continuous chart for every parameter-resolved outer event. "
        "Validation is incremental, not one-shot: each later fold refits the "
        "pipeline using all earlier eligible history, while its own event remains "
        f"held out. Each fold retains its surrounding exact "
        f"{scale.display_plural}. The blue line is the false-positive-aware "
        "fusion score; red stars are held-out Japan events and orange crosses "
        "are the frozen non-Japan controls. Every marker uses the same score "
        "axis, and the annotations report event-minus-control raw-score margins. "
        "Scores are relative diagnostics, not calibrated probabilities.",
        "",
        "## Localization forecast",
        "",
        f"![Localization forecast]({figures[8].name})",
        "",
        *explanation_lines("location_forecast"),
        "The vertical axis contains zone identifiers, not latitude. Localization "
        "is a one-shot forecast: one feature set, holdout design and fitted fusion "
        "produce every displayed slot. It is not incrementally refitted from one "
        "forecast slot to the next. The timing-selection table above supplies the "
        "location zone for the configured primary timing selection.",
        "",
        "## Localization validation",
        "",
        f"![Localization validation]({figures[5].name})",
        "",
        *explanation_lines("location_validation"),
        "The discrete vertical axis runs from zone 1 through "
        f"zone {location_summary['zone_count']}. The solid line is the real "
        "chronological zone trend and the dashed line is the fused prediction. "
        "A ±0.045 display-only offset is used only when the complete real and "
        "predicted sequences would otherwise overlap exactly.",
        "",
        f"Exact-zone accuracy is `{location_summary['validation_metrics']['exact_zone_accuracy']:.2f}` "
        f"on only {len(location_summary['validation_events'])} holdout events; "
        "this sample is too small to establish operational validity.",
        "",
        "## Latitude and longitude implied by forecast zones",
        "",
        f"![Centroid coordinate interpretation]({figures[12].name})",
        "",
        *explanation_lines("centroid_coordinates"),
        "# Technical appendix",
        "",
        "## Zone construction and complete classification territories",
        "",
        f"![Zone construction]({figures[4].name})",
        "",
        *explanation_lines("zone_construction"),
        markdown_table(zones),
        "",
        "### Zone-count selection",
        "",
        markdown_table(zone_trials),
        "",
        f"The full-covariance GMM was fitted without the "
        f"{len(location_summary['validation_events'])} outer location "
        "validation events. Geographic silhouette receives 80% weight and BIC "
        f"skill 20%, with a configured minimum of "
        f"{location_summary['run_parameters']['minimum_zone_events']} "
        "construction events in every component. "
        "The geography-only catalog starts "
        f"at `{location_summary['zone_catalog']['start']}` and is filtered using "
        f"M≥{location_summary['zone_catalog']['magnitude_threshold']:.1f} and "
        "the configured geographic bounds; these rows define zones only, while "
        f"the predictive localization target remains "
        f"M≥{location_summary['magnitude_threshold']:.1f}. Zone numbers "
        "are ordered from the southernmost centroid to the northernmost centroid.",
        "",
        "## Timing peak-isolation diagnostics",
        "",
        f"![Peak-isolation gate]({figures[1].name})",
        "",
        *explanation_lines("peak_isolation"),
        f"![Timing system ranking]({figures[2].name})",
        "",
        *explanation_lines("timing_weights"),
        f"The validation gate status is "
        f"**{timing_summary['peak_isolation']['status']}**. "
        "Every system variant retains a positive weight. A status of "
        "`NO_ALIAS_PENALTY` means the suppression search ran but retained the "
        "unsuppressed baseline; `NO_APPLICABLE_ALIAS_PATTERN` means the weekly "
        "windows were structurally valid but contained no repeated pattern for "
        "the operator to attenuate. A non-zero filter is used only when the configured "
        "higher-is-better objective improves, all real validation peaks remain "
        "exact local maxima and credible false peaks decrease.",
        "",
        "## Localization ranking diagnostics",
        "",
        f"![Localization system ranking]({figures[6].name})",
        "",
        *explanation_lines("location_systems"),
        f"![Localization fusion ranking]({figures[7].name})",
        "",
        *explanation_lines("location_fusion"),
        "# Conclusions",
        "",
        "## What was achieved",
        "",
        *[f"- {item}" for item in narrative["conclusion"]["demonstrated"]],
        "",
        "## Practical advantages",
        "",
        *[
            f"- {item}"
            for item in narrative["conclusion"]["practical_advantages"]
        ],
        "",
        "## Evidence limits and open research question",
        "",
        *[
            f"- {item}"
            for item in narrative["conclusion"]["evidence_limits"]
        ],
        "",
        narrative["conclusion"]["final_statement"],
        "",
        "This remains a retrospective research diagnostic, not an earthquake "
        "warning. Scores are not calibrated earthquake probabilities.",
    ]
    path = REPORT / f"{REPORT_BASENAME}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def add_report_footer(fig, page_number: int):
    fig.text(
        0.045,
        0.018,
        "Research diagnostic only · scores are not calibrated probabilities",
        fontsize=7.5,
        color="#7b8794",
    )
    fig.text(
        0.955,
        0.018,
        str(page_number),
        fontsize=8,
        color="#7b8794",
        ha="right",
    )


def add_page_heading(
    fig,
    title: str,
    subtitle: str | None = None,
    *,
    fontsize: float | None = None,
) -> float:
    """Draw a clipping-safe report heading and a consistent separator rule."""
    title = str(title)
    if fontsize is None:
        fontsize = 21.0 if len(title) <= 58 else 18.0 if len(title) <= 82 else 16.5
    fig.text(
        0.05,
        0.952,
        title,
        fontsize=fontsize,
        weight="bold",
        color="#102a43",
        va="top",
        ha="left",
    )
    fig.add_artist(
        Line2D(
            [0.05, 0.95],
            [0.892, 0.892],
            transform=fig.transFigure,
            color="#cbd5e1",
            linewidth=0.9,
        )
    )
    if subtitle:
        fig.text(
            0.05,
            0.870,
            subtitle,
            fontsize=9.5,
            color="#52606d",
            va="top",
        )
        return 0.835
    return 0.865


def add_text_card(
    fig,
    x: float,
    y: float,
    width: float,
    height: float,
    heading: str,
    body: str,
    *,
    wrap: int,
    heading_color: str = "#102a43",
    facecolor: str = "#f5f7fa",
    fontsize: float = 9.0,
):
    wrapped_body = "\n".join(
        textwrap.fill(line, wrap) if line.strip() else ""
        for line in body.splitlines()
    )
    body_lines = max(1, len(wrapped_body.splitlines()))
    available_body_points = (
        fig.get_size_inches()[1] * height * 72.0 * 0.72
    )
    fitted_body_fontsize = min(
        fontsize,
        max(
            4.8,
            available_body_points / (body_lines * 1.28),
        ),
    )
    axis = fig.add_axes([x, y, width, height])
    axis.axis("off")
    axis.add_patch(
        Rectangle(
            (0, 0),
            1,
            1,
            transform=axis.transAxes,
            facecolor=facecolor,
            edgecolor="#d9e2ec",
            linewidth=0.9,
        )
    )
    axis.text(
        0.035,
        0.91,
        heading,
        transform=axis.transAxes,
        fontsize=fontsize + 0.7,
        color=heading_color,
        weight="bold",
        va="top",
    )
    axis.text(
        0.035,
        0.78,
        wrapped_body,
        transform=axis.transAxes,
        fontsize=fitted_body_fontsize,
        color="#334e68",
        va="top",
        linespacing=1.28,
        clip_on=True,
    )


def render_vocabulary_page(pdf, narrative: dict, page_number: int):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "How to read this report — vocabulary",
        "These definitions apply throughout the report. Technical labels never represent earthquake probability unless explicitly stated.",
    )
    vocabulary = narrative["vocabulary"]
    split = (len(vocabulary) + 1) // 2
    columns = [vocabulary[:split], vocabulary[split:]]
    for column_index, column in enumerate(columns):
        x = 0.05 + column_index * 0.47
        y = 0.84
        for item in column:
            fig.text(
                x,
                y,
                item["term"],
                fontsize=10.2,
                weight="bold",
                color="#1f4e79",
                va="top",
            )
            definition = textwrap.fill(item["definition"], 70)
            fig.text(
                x,
                y - 0.025,
                definition,
                fontsize=8.4,
                color="#334e68",
                va="top",
                linespacing=1.18,
            )
            line_count = definition.count("\n") + 1
            y -= 0.055 + 0.019 * line_count
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_formula_page(pdf, narrative: dict, page_number: int):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Worked formulas behind the vocabulary",
        "The examples explain how report terms are calculated. They are selection and ranking calculations, not earthquake probabilities.",
    )
    positions = [
        (0.05, 0.585, 0.43, 0.255),
        (0.52, 0.585, 0.43, 0.255),
        (0.05, 0.315, 0.43, 0.235),
        (0.52, 0.315, 0.43, 0.235),
        (0.05, 0.065, 0.90, 0.22),
    ]
    for item, (x, y, width, height) in zip(
        narrative["formula_examples"], positions
    ):
        body = (
            f"Formula\n{item['formula']}\n\n"
            f"Symbols\n{item['symbols']}\n\n"
            f"Worked example\n{item['worked_example']}"
        )
        add_text_card(
            fig,
            x,
            y,
            width,
            height,
            item["title"],
            body,
            wrap=72 if width < 0.5 else 140,
            fontsize=6.8 if width < 0.5 else 7.1,
            facecolor="#f8fafc",
        )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def _aligned_interval_starts(
    anchor: pd.Timestamp,
    interval_days: int,
    visible_start: pd.Timestamp,
    visible_end_exclusive: pd.Timestamp,
) -> list[pd.Timestamp]:
    """Return every aligned interval start intersecting a visible date range."""
    step = pd.Timedelta(days=interval_days)
    first = anchor + ((visible_start - anchor).days // interval_days) * step
    starts: list[pd.Timestamp] = []
    cursor = first
    while cursor < visible_end_exclusive:
        if cursor + step > visible_start:
            starts.append(cursor)
        cursor += step
    return starts


def render_grid_overlap_page(
    pdf,
    parameters: dict,
    grid: dict,
    page_number: int,
):
    """Visualize an optional reference grid against this run's shifted grid."""
    current_days = int(parameters["interval_days"])
    reference_days = int(grid["reference_interval_days"])
    current_anchor = pd.Timestamp(grid["resolved_anchor_date"])
    reference_anchor = pd.Timestamp(grid["reference_anchor_date"])
    visible_start = pd.Timestamp(parameters["forecast_start"])
    visible_end = pd.Timestamp(parameters["forecast_end"]) + pd.Timedelta(days=1)
    offset = int(grid["offset_days_modulo_interval"])
    current_starts = _aligned_interval_starts(
        current_anchor, current_days, visible_start, visible_end
    )
    reference_starts = _aligned_interval_starts(
        reference_anchor, reference_days, visible_start, visible_end
    )

    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Temporal grid overlap",
        "The shifted grid is a declared experimental design choice; interval bars show exactly which calendar days overlap the reference pipeline.",
    )
    axis = fig.add_axes([0.16, 0.36, 0.78, 0.40])
    rows = [
        (reference_starts, reference_days, 1.05, "#f6ad55", "reference"),
        (current_starts, current_days, 0.30, "#4c51bf", "current"),
    ]
    for starts, width_days, y, color, label in rows:
        for index, start in enumerate(starts):
            left = mdates.date2num(start.to_pydatetime())
            axis.broken_barh(
                [(left, width_days)],
                (y, 0.42),
                facecolors=color,
                alpha=0.38 if index % 2 == 0 else 0.62,
                edgecolors=color,
                linewidth=1.2,
            )
            end_inclusive = start + pd.Timedelta(days=width_days - 1)
            centre = start + pd.Timedelta(days=width_days / 2)
            if centre >= visible_start and centre <= visible_end:
                axis.text(
                    centre,
                    y + 0.21,
                    f"{start:%Y-%m-%d}\n{end_inclusive:%Y-%m-%d}",
                    ha="center",
                    va="center",
                    fontsize=6.5 if width_days <= 100 else 7.2,
                    color="#102a43",
                    weight="bold" if label == "current" else "normal",
                )
    for boundary in current_starts:
        axis.axvline(boundary, color="#4c51bf", linewidth=0.8, alpha=0.38)
    for boundary in reference_starts:
        axis.axvline(
            boundary, color="#c27803", linewidth=0.8, alpha=0.32,
            linestyle="--"
        )
    axis.set_xlim(visible_start, visible_end)
    axis.set_ylim(0.05, 1.72)
    axis.set_yticks([0.51, 1.26])
    axis.set_yticklabels(
        [
            f"current {current_days}-day grid",
            f"reference {reference_days}-day grid",
        ],
        fontsize=9,
        weight="bold",
    )
    axis.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    axis.tick_params(axis="x", labelrotation=30, labelsize=8)
    axis.grid(axis="x", color="#cbd5e1", linewidth=0.65, alpha=0.55)
    axis.set_title(
        f"{grid.get('reference_pipeline', 'reference pipeline')} versus {REPORT_VERSION.upper()}",
        fontsize=11.5,
        weight="bold",
        color="#102a43",
        pad=12,
    )
    fig.text(
        0.075,
        0.275,
        f"Declared offset: ({current_anchor:%Y-%m-%d} − {reference_anchor:%Y-%m-%d}) "
        f"mod {current_days} days = {offset} days. The current run therefore uses "
        f"{current_days}-day bins beginning at {current_anchor:%Y-%m-%d}; the comparison "
        f"grid uses {reference_days}-day bins anchored at {reference_anchor:%Y-%m-%d}.",
        fontsize=9.3,
        color="#334e68",
        va="top",
        wrap=True,
    )
    fig.text(
        0.075,
        0.18,
        "The overlap changes which calendar observations share a target bin. It does not "
        "create extra observations, interpolate targets, or combine the reference forecast "
        "with this run's model scores.",
        fontsize=9.3,
        color="#52606d",
        va="top",
        wrap=True,
    )
    add_report_footer(fig, page_number)
    fig.savefig(
        REPORT / f"temporal_grid_overlap_{REPORT_FILE_TAG}.png",
        dpi=REPORT_DPI,
        facecolor="white",
    )
    pdf.savefig(fig)
    plt.close(fig)


def _workflow_evidence_lines(stage: dict) -> str:
    lines = []
    for key, value in stage["evidence"].items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, float):
            rendered = f"{value:.3f}"
        elif isinstance(value, list):
            rendered = ", ".join(map(str, value))
        else:
            rendered = str(value)
        lines.append(f"{label}: {rendered}")
    return "\n".join(lines)


def _draw_report_table(
    fig,
    box: tuple[float, float, float, float],
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    *,
    fontsize: float = 7.2,
    header_color: str = "#1f4e79",
):
    """Draw a vector table whose cells wrap and resize inside their columns."""
    if len(headers) != len(widths):
        raise ValueError("Table headers and widths must have the same length")
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("Every table row must match the header column count")
    axis = fig.add_axes(box)
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    # Supplied widths are layout priors.  Blend them with observed text demand
    # so a new pipeline cannot silently force a long label over its neighbour.
    base = np.asarray(widths, dtype=float)
    base /= base.sum()
    demand = []
    for column, header in enumerate(headers):
        lengths = [len(str(header))]
        lengths.extend(len(str(row[column])) for row in rows)
        demand.append(max(4.0, min(34.0, float(np.percentile(lengths, 90)))))
    demand = np.asarray(demand, dtype=float)
    demand /= demand.sum()
    widths = (0.58 * base + 0.42 * demand).tolist()

    figure_width, figure_height = fig.get_size_inches()

    def wrap_cell(value: object, column: int, font_size: float) -> tuple[str, int, float]:
        text = str(value).strip()
        column_points = figure_width * box[2] * widths[column] * 72.0
        capacity = max(4, int((column_points * 0.90) / max(font_size * 0.56, 1)))
        paragraphs = text.splitlines() or [""]
        lines: list[str] = []
        for paragraph in paragraphs:
            lines.extend(
                textwrap.wrap(
                    paragraph,
                    width=capacity,
                    break_long_words=True,
                    break_on_hyphens=True,
                )
                or [""]
            )
        cell_font = font_size
        if len(lines) > 2:
            # Prefer two readable lines; reduce only this cell's font when its
            # content is exceptionally long instead of crossing a boundary.
            target_capacity = max(capacity, int(np.ceil(len(text) / 2)))
            lines = textwrap.wrap(
                text,
                width=target_capacity,
                break_long_words=True,
                break_on_hyphens=True,
            )
            if len(lines) > 2:
                midpoint = max(1, len(text) // 2)
                split = text.rfind(" ", 0, midpoint + 1)
                if split < 1:
                    split = midpoint
                lines = [text[:split].strip(), text[split:].strip()]
            cell_font = max(
                4.2,
                font_size
                * min(1.0, (2.0 * capacity) / max(len(text), 1)),
            )
        return "\n".join(lines[:2]), max(1, len(lines[:2])), cell_font

    provisional_header = [
        wrap_cell(header, column, fontsize)
        for column, header in enumerate(headers)
    ]
    provisional_rows = [
        [wrap_cell(value, column, fontsize) for column, value in enumerate(row)]
        for row in rows
    ]
    line_units = [
        max(item[1] for item in provisional_header) + 0.35,
        *[
            max(item[1] for item in row) + 0.35
            for row in provisional_rows
        ],
    ]
    available_points = figure_height * box[3] * 72.0
    fitted_fontsize = min(
        fontsize,
        max(4.8, available_points / max(sum(line_units), 1.0) * 0.54),
    )
    header_cells = [
        wrap_cell(header, column, fitted_fontsize)
        for column, header in enumerate(headers)
    ]
    row_cells = [
        [
            wrap_cell(value, column, fitted_fontsize)
            for column, value in enumerate(row)
        ]
        for row in rows
    ]
    line_units = [
        max(item[1] for item in header_cells) + 0.35,
        *[max(item[1] for item in row) + 0.35 for row in row_cells],
    ]
    unit_height = 1.0 / max(sum(line_units), 1.0)
    x_positions = np.cumsum([0.0, *widths])
    cursor = 1.0
    header_height = line_units[0] * unit_height
    for column, (header, _, cell_font) in enumerate(header_cells):
        axis.add_patch(
            Rectangle(
                (x_positions[column], cursor - header_height),
                widths[column],
                header_height,
                facecolor=header_color,
                edgecolor="white",
                linewidth=0.8,
            )
        )
        axis.text(
            x_positions[column] + widths[column] * 0.04,
            cursor - header_height / 2,
            str(header),
            color="white",
            fontsize=cell_font,
            weight="bold",
            ha="left",
            va="center",
            linespacing=1.0,
            clip_on=True,
        )
    cursor -= header_height
    for row_index, row in enumerate(row_cells):
        row_height = line_units[row_index + 1] * unit_height
        y = cursor - row_height
        color = "#f8fafc" if row_index % 2 == 0 else "#edf2f7"
        for column, (value, _, cell_font) in enumerate(row):
            axis.add_patch(
                Rectangle(
                    (x_positions[column], y),
                    widths[column],
                    row_height,
                    facecolor=color,
                    edgecolor="#d9e2ec",
                    linewidth=0.55,
                )
            )
            axis.text(
                x_positions[column] + widths[column] * 0.04,
                y + row_height / 2,
                str(value),
                color="#243b53",
                fontsize=cell_font,
                ha="left",
                va="center",
                linespacing=1.0,
                clip_on=True,
            )
        cursor = y
    return axis


def _pretty_parameter(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return " → ".join(str(item) for item in value)
    if isinstance(value, float):
        if value != 0 and abs(value) < 0.001:
            return f"{value:.1e}"
        return f"{value:g}"
    return str(value)


def _parameter_label(name: str) -> str:
    labels = {
        "ga_frequency": "Genetic-algorithm frequency",
        "hidden_sizes": "Hidden neurons by layer",
        "hidden_width": "KAN hidden width",
        "hidden_layers": "KAN hidden layers",
        "spline_grid": "Spline grid size",
        "learning_rate": "Learning rate",
        "regularization_lambda": "Regularization λ",
        "weight_decay": "Weight decay",
        "population_size": "Rule-population size",
        "max_active_conditions": "Maximum active rule conditions",
        "export_rule_count": "Rules exported for audit",
        "positive_weight": "Positive-class weighting",
        "positive_replay": "Positive-example replay",
        "validation_split": "Internal validation fraction",
        "early_stop_patience": "Early-stop patience",
        "final_retrain_full_train": "Retrain on complete training set",
        "batch_size": "Batch size",
        "device": "Compute device",
        "implementation": "Implementation",
        "family": "Model family",
        "activation": "Activation",
        "dropout": "Dropout",
        "epochs": "Training epochs",
    }
    return labels.get(name, name.replace("_", " ").capitalize())


def render_workflow_overview_page(pdf, workflow: dict, page_number: int):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Reproducible workflow — complete execution order",
        "This diagram is generated from report_workflow.json, which is itself derived from the completed run artifacts.",
    )
    axis = fig.add_axes([0.035, 0.16, 0.93, 0.68])
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    source_boxes = [
        (
            0.01,
            0.68,
            "Solar System\npositions",
            "Audited ephemeris\nfeature fields",
            "#e0f2fe",
        ),
        (
            0.01,
            0.28,
            "Earthquake\ncatalogue",
            "Times, magnitudes\nand coordinates",
            "#fee2e2",
        ),
    ]
    for x, y, heading, body, color in source_boxes:
        axis.add_patch(
            Rectangle(
                (x, y),
                0.135,
                0.20,
                facecolor=color,
                edgecolor="#7b8794",
                linewidth=1.2,
            )
        )
        axis.text(
            x + 0.0675,
            y + 0.135,
            heading,
            ha="center",
            va="center",
            fontsize=8.6,
            weight="bold",
            color="#102a43",
        )
        axis.text(
            x + 0.0675,
            y + 0.055,
            body,
            ha="center",
            va="center",
            fontsize=6.9,
            color="#334e68",
        )
    stages = workflow["stages"]
    stage_width = 0.14
    stage_y = 0.48
    stage_height = 0.30
    stage_positions = [
        (0.19 + index * 0.157, stage_y) for index in range(len(stages))
    ]
    phase_colors = ["#eaf4ff", "#f3efff", "#eefaf4", "#fff7e8", "#eef2f7"]
    for index, (stage, (x, y)) in enumerate(zip(stages, stage_positions)):
        axis.add_patch(
            Rectangle(
                (x, y),
                stage_width,
                stage_height,
                facecolor=phase_colors[index % len(phase_colors)],
                edgecolor="#2b70b8",
                linewidth=1.5,
            )
        )
        axis.add_patch(
            plt.Circle(
                (x + 0.018, y + stage_height - 0.032),
                0.018,
                facecolor="#2b70b8",
                edgecolor="white",
                linewidth=0.8,
            )
        )
        axis.text(
            x + 0.018,
            y + stage_height - 0.032,
            str(stage["order"]),
            ha="center",
            va="center",
            fontsize=7.4,
            color="white",
            weight="bold",
        )
        axis.text(
            x + 0.043,
            y + stage_height - 0.034,
            f"PHASE {stage['order']}",
            ha="left",
            va="center",
            fontsize=7.3,
            color="#2b70b8",
            weight="bold",
        )
        axis.text(
            x + stage_width / 2,
            y + 0.165,
            textwrap.fill(stage["title"], 18),
            ha="center",
            va="center",
            fontsize=7.1,
            weight="bold",
            color="#102a43",
            linespacing=1.05,
        )
        axis.text(
            x + stage_width / 2,
            y + 0.035,
            f"{len(stage['operations'])} operations\n"
            f"{len(stage['audit_files'])} audit sources",
            ha="center",
            va="center",
            fontsize=6.2,
            color="#52606d",
        )
        if index < len(stages) - 1:
            axis.annotate(
                "",
                xy=(stage_positions[index + 1][0] - 0.004, y + stage_height / 2),
                xytext=(x + stage_width + 0.004, y + stage_height / 2),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#52606d",
                    linewidth=1.5,
                    shrinkA=0,
                    shrinkB=0,
                ),
            )
    # Two source streams merge through an orthogonal bus before phase 1.
    bus_x = 0.166
    source_centres = [0.78, 0.38]
    phase_centre = stage_y + stage_height / 2
    for source_y in source_centres:
        axis.plot(
            [0.145, bus_x],
            [source_y, source_y],
            color="#52606d",
            linewidth=1.4,
        )
    axis.plot(
        [bus_x, bus_x],
        [min(source_centres), max(source_centres)],
        color="#52606d",
        linewidth=1.4,
    )
    axis.annotate(
        "",
        xy=(stage_positions[0][0] - 0.004, phase_centre),
        xytext=(bus_x, phase_centre),
        arrowprops=dict(
            arrowstyle="-|>",
            color="#52606d",
            linewidth=1.5,
            shrinkA=0,
            shrinkB=0,
        ),
    )
    axis.text(
        0.50,
        0.35,
        "Evidence enters once; every later decision is traceable to the preceding audited phase",
        ha="center",
        fontsize=9.8,
        weight="bold",
        color="#102a43",
    )
    axis.text(
        0.50,
        0.23,
        textwrap.fill(
            "The master contract is fixed first. Feature removal is then tested "
            "before model comparison; timing and location are searched under "
            "their distinct validation designs; only validated outputs enter "
            "fusion and the checked report. This ordering prevents a visually "
            "attractive final graph from bypassing data or holdout controls.",
            132,
        ),
        ha="center",
        va="center",
        fontsize=8.8,
        color="#334e68",
    )
    axis.text(
        0.50,
        0.07,
        "Machine-readable source: 00_config/report_workflow.json",
        ha="center",
        fontsize=8.5,
        color="#1f4e79",
        weight="bold",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_feature_evidence_page(
    pdf, workflow: dict, domain: str, page_number: int
):
    evidence = workflow["feature_evidence"]
    payload = evidence[domain]
    domain_title = "Timing" if domain == "timing" else "Localization"
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        f"{domain_title} feature search — top {payload['display_limit']} celestial fields",
        (
            f"Generated from {payload['audit_count']} ranking audit(s). "
            "Rank score is a selection aid, not physical importance or earthquake probability."
        ),
    )
    rows = [
        [
            str(item["display_rank"]),
            item.get("measurement", item["feature"]),
            item["body_name"],
            item["body_category"],
            f"{item['mean_rank_across_audits']:.2f}",
            f"{item['ranking_score_higher_is_better']:.3f}",
        ]
        for item in payload["top_features"]
    ]
    _draw_report_table(
        fig,
        (0.05, 0.15, 0.90, 0.67),
        [
            "#",
            "Feature field",
            "Celestial body",
            "Class",
            "Mean rank ↓",
            "Rank score ↑",
        ],
        rows,
        [0.04, 0.28, 0.16, 0.24, 0.14, 0.14],
        fontsize=6.1,
    )
    fig.text(
        0.05,
        0.105,
        textwrap.fill(
            f"{payload['total_ranked_features']} feature measurements were ranked. "
            f"Body names and classes come from {evidence['catalogue']}. "
            "Mean rank is lower-is-better; rank score reverses and normalizes "
            "that direction so all selection scores point the same way.",
            150,
        ),
        fontsize=8.1,
        color="#52606d",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_body_summary_page(pdf, workflow: dict, page_number: int):
    evidence = workflow["feature_evidence"]
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Celestial bodies represented in the complete feature rankings",
        (
            "Repeated measurements are collapsed to one automatically decoded "
            "celestial body. Technical target identifiers remain in the JSON audit."
        ),
    )
    sections = [
        ("Timing", evidence["timing"], 0.50),
        ("Localization", evidence["localization"], 0.13),
    ]
    for title, payload, y in sections:
        fig.text(
            0.05,
            y + 0.29,
            f"{title} ranking — {len(payload['celestial_bodies'])} unique JPL targets",
            fontsize=11,
            weight="bold",
            color="#1f4e79",
        )
        rows = [
            [
                item["body_name"],
                item["body_category"],
                str(item["ranked_measurement_count"]),
                str(item["best_feature_rank"]),
                "yes" if item["represented_in_top_features"] else "additional body",
            ]
            for item in payload["celestial_bodies"]
        ]
        _draw_report_table(
            fig,
            (0.05, y, 0.90, 0.26),
            [
                "Celestial body",
                "Class",
                "Ranked fields",
                "Best field rank",
                "Top-20 status",
            ],
            rows,
            [0.23, 0.25, 0.14, 0.15, 0.23],
            fontsize=7.0,
        )
    fig.text(
        0.05,
        0.08,
        "“Additional body” means that the target is present in the complete ranking but none of its measurements reached the displayed top 20.",
        fontsize=8.2,
        color="#52606d",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_model_ranking_evidence_page(
    pdf,
    workflow: dict,
    domain: str,
    page_number: int,
):
    evidence = workflow["model_evidence"][domain]
    domain_title = "Timing" if domain == "timing" else "Localization"
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        f"{domain_title} model search — top three trained systems",
        "The ranking and metrics are read from the completed run; the report does not select or rename a winner manually.",
    )
    rows = []
    for item in evidence["top_systems"]:
        context = item["training_context"]
        context_items = [
            f"{key.replace('_across_folds', '').replace('_', ' ')}: "
            f"{str(value).replace('_', '-')}"
            for key, value in context.items()
        ]
        context_text = "\n".join(
            " · ".join(context_items[index : index + 2])
            for index in range(0, len(context_items), 2)
        )
        rows.append(
            [
                str(item["rank"]),
                textwrap.fill(item["display_name"], 26),
                textwrap.fill(
                    " + ".join(
                        BASE_COMPONENT_NAMES.get(
                            component,
                            component.replace("_", " ").title(),
                        )
                        for component in item["components"]
                    ),
                    25,
                ),
                f"{item['training_quality']:.3f}",
                f"{item['validation_quality']:.3f}",
                f"{item['combined_quality']:.3f}",
                context_text,
            ]
        )
    _draw_report_table(
        fig,
        (0.05, 0.50, 0.90, 0.32),
        [
            "#",
            "System",
            "Executed components",
            "Train ↑",
            "Validation ↑",
            "Combined ↑",
            "Training context",
        ],
        rows,
        [0.04, 0.18, 0.18, 0.08, 0.09, 0.09, 0.34],
        fontsize=6.8,
    )
    if domain == "timing" and evidence["top_systems"]:
        fold_rows = []
        for detail in evidence["top_systems"][0].get("fold_details", []):
            magnitude = detail["held_out_event_magnitude"]
            fold_rows.append(
                [
                    str(detail["fold"]),
                    (
                        f"{detail['held_out_event_slot']} · "
                        f"M{float(magnitude):.2f}"
                        if isinstance(magnitude, (int, float))
                        else str(detail["held_out_event_slot"])
                    ),
                    str(detail["feature_count"]),
                    str(detail["training_events"]),
                    str(detail["training_rows"]),
                    str(detail["event_radius"]),
                    str(detail["history_start_year"]),
                ]
            )
        _draw_report_table(
            fig,
            (0.05, 0.355, 0.90, 0.105),
            [
                "Fold",
                "Configured selection-validation event",
                "Features",
                "Train events",
                "Train rows",
                "Radius",
                "Start year",
            ],
            fold_rows,
            [0.06, 0.30, 0.11, 0.13, 0.12, 0.10, 0.12],
            fontsize=6.7,
        )
        fig.text(
            0.05,
            0.325,
            (
                "A range such as 182–209 therefore means fold 1 and fold 2 used "
                "different guarded feature counts; it is not two values in one fit. "
                "Training/validation qualities above are averages across these folds."
            ),
            fontsize=7.6,
            color="#52606d",
        )
    else:
        fig.text(
            0.05,
            0.425,
            (
                "Localization is one-shot: the displayed feature, training-event "
                "and holdout counts belong to one common fit, not incremental folds."
            ),
            fontsize=8.0,
            color="#52606d",
        )
    add_text_card(
        fig,
        0.05,
        0.105,
        0.28,
        0.17,
        "How the order is produced",
        f"Quality uses {workflow['model_evidence']['quality_formula']}. "
        "Every metric shown has been oriented so a larger value is better.",
        wrap=43,
        fontsize=8.2,
        facecolor="#edf6ff",
    )
    add_text_card(
        fig,
        0.36,
        0.105,
        0.28,
        0.17,
        "What a hybrid row means",
        "A hybrid is the score fusion of the listed trained components. "
        "Its component architectures are documented on the following parameter pages.",
        wrap=43,
        fontsize=8.2,
        facecolor="#f5f3ff",
        heading_color="#5b21b6",
    )
    add_text_card(
        fig,
        0.67,
        0.105,
        0.28,
        0.17,
        "Important limit",
        "These are model-selection qualities on the configured evidence split. "
        "They are neither event probabilities nor proof of a physical mechanism.",
        wrap=43,
        fontsize=8.2,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_model_parameter_page(
    pdf,
    workflow: dict,
    domain: str,
    components: list[str],
    page_number: int,
):
    evidence = workflow["model_evidence"][domain]
    domain_title = "Timing" if domain == "timing" else "Localization"
    configurations = {}
    for system in evidence["top_systems"]:
        configurations.update(system["component_configurations"])
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        f"{domain_title} model search — executed component parameters",
        f"Automatically derived from the same executable configuration used for training; epoch scale in this run: {evidence['epochs_scale']:g}.",
    )
    positions = [(0.05, 0.12, 0.43, 0.70), (0.52, 0.12, 0.43, 0.70)]
    for component, position in zip(components, positions):
        parameters = configurations[component]
        display = BASE_COMPONENT_NAMES.get(
            component,
            SYSTEM_DISPLAY_NAMES.get(
                component,
                component.replace("_", " ").title(),
            ),
        )
        fig.text(
            position[0],
            position[1] + position[3] + 0.018,
            display,
            fontsize=11.2,
            weight="bold",
            color="#1f4e79",
        )
        rows = [
            [
                textwrap.fill(_parameter_label(name), 34),
                textwrap.fill(_pretty_parameter(value), 34),
            ]
            for name, value in parameters.items()
        ]
        _draw_report_table(
            fig,
            position,
            ["Parameter", "Executed value"],
            rows,
            [0.58, 0.42],
            fontsize=7.2,
        )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_workflow_phase_page(
    pdf,
    stage: dict,
    page_number: int,
):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        f"Workflow phase {stage['order']} — {stage['title']}",
        fontsize=17.5,
    )
    add_text_card(
        fig,
        0.05,
        0.68,
        0.285,
        0.19,
        "Inputs",
        "\n".join(f"• {item}" for item in stage["inputs"]),
        wrap=43,
        fontsize=8.1,
        facecolor="#edf6ff",
    )
    add_text_card(
        fig,
        0.357,
        0.68,
        0.593,
        0.19,
        "Operations in execution order",
        "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(stage["operations"], 1)
        ),
        wrap=92,
        fontsize=8.1,
    )
    add_text_card(
        fig,
        0.05,
        0.43,
        0.44,
        0.19,
        "Acceptance / selection rule",
        stage["decision_rule"],
        wrap=69,
        fontsize=8.3,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_text_card(
        fig,
        0.51,
        0.43,
        0.44,
        0.19,
        "Evidence from this run",
        _workflow_evidence_lines(stage),
        wrap=68,
        fontsize=8.0,
        facecolor="#f0fdf4",
        heading_color="#166534",
    )
    add_text_card(
        fig,
        0.05,
        0.18,
        0.44,
        0.19,
        "Outputs and audit trail",
        "Outputs:\n"
        + "\n".join(f"• {item}" for item in stage["outputs"])
        + "\n\nAudits:\n"
        + "\n".join(f"• {item}" for item in stage["audit_files"]),
        wrap=70,
        fontsize=7.4,
    )
    add_text_card(
        fig,
        0.51,
        0.18,
        0.44,
        0.19,
        "Value added versus a single-model shortcut",
        stage["value_added"],
        wrap=68,
        fontsize=8.3,
        facecolor="#f5f3ff",
        heading_color="#5b21b6",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_methods_page(pdf, narrative: dict, page_number: int):
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Model families compared by the autonomous pipeline",
    )
    purpose = narrative["executive_purpose"]
    add_text_card(
        fig,
        0.05,
        0.735,
        0.90,
        0.14,
        "What makes this pipeline agentic?",
        purpose["why_agentic"],
        wrap=145,
        facecolor="#edf6ff",
        fontsize=9.0,
    )
    fig.text(
        0.05,
        0.695,
        "Relationship to the reproducible workflow",
        fontsize=11,
        weight="bold",
        color="#102a43",
    )
    fig.text(
        0.05,
        0.655,
        textwrap.fill(
            "The preceding workflow pages record the exact order, inputs, decisions, "
            "artifacts and value added. This page defines the four model-family labels "
            "used in the timing and localization comparison charts.",
            138,
        ),
        fontsize=9.8,
        color="#1f4e79",
        weight="bold",
        va="top",
        linespacing=1.15,
    )
    positions = [
        (0.05, 0.38),
        (0.52, 0.38),
        (0.05, 0.095),
        (0.52, 0.095),
    ]
    for model, (x, y) in zip(narrative["model_families"], positions):
        body = (
            f"{model['expanded']}. {model['explanation']}\n\n"
            f"Names used here: {model['report_variants']}"
        )
        add_text_card(
            fig,
            x,
            y,
            0.43,
            0.245,
            model["name"],
            body,
            wrap=67,
            fontsize=8.5,
        )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_figure_page(
    pdf,
    figure_path: Path,
    title: str,
    explanation: dict,
    page_number: int,
    *,
    map_layout: bool = False,
    figure_overlays: list[dict] | None = None,
):
    """Render chrome for a figure page; PNG is embedded natively after PdfPages."""
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(fig, title, fontsize=17.5)
    image_box = figure_image_box(map_layout)
    # Reserve the image area without rasterizing the PNG into the PDF page.
    placeholder = fig.add_axes(list(image_box))
    placeholder.set_xticks([])
    placeholder.set_yticks([])
    for spine in placeholder.spines.values():
        spine.set_visible(False)
    placeholder.set_facecolor("white")
    if map_layout:
        fields = [
            ("Question answered", explanation["question"]),
            ("How to read the graphic", explanation["reading"]),
            ("What this run shows", explanation["result"]),
            ("Important limitation", explanation["caution"]),
        ]
        y = 0.72
        for index, (heading, body) in enumerate(fields):
            height = 0.17 if index != 1 else 0.22
            add_text_card(
                fig,
                0.665,
                y,
                0.295,
                height,
                heading,
                body,
                wrap=46,
                fontsize=8.1,
                facecolor="#f8fafc" if index < 3 else "#fff7ed",
                heading_color="#102a43" if index < 3 else "#9a3412",
            )
            y -= height + 0.025
    else:
        fields = [
            ("Question answered", explanation["question"]),
            ("How to read", explanation["reading"]),
            ("Result in this run", explanation["result"]),
            ("Limitation", explanation["caution"]),
        ]
        for index, (heading, body) in enumerate(fields):
            add_text_card(
                fig,
                0.04 + index * 0.235,
                0.06,
                0.22,
                0.205,
                heading,
                body,
                wrap=33,
                fontsize=7.7,
                facecolor="#f8fafc" if index < 3 else "#fff7ed",
                heading_color="#102a43" if index < 3 else "#9a3412",
            )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)
    if figure_overlays is not None:
        figure_overlays.append(
            {
                "page_index": page_number - 1,
                "image_path": Path(figure_path),
                "box": image_box,
            }
        )


def render_randomized_control_page(
    pdf,
    workflow: dict,
    domain: str,
    page_number: int,
):
    """Render the separate one-shot label-permutation control."""
    control = workflow["randomized_control"]["controls"][domain]
    base = PROJECT / f"07_randomized_control/{domain}"
    validation = pd.read_csv(base / "validation.csv")
    forecast = pd.read_csv(base / "forecast.csv")
    domain_title = "Timing" if domain == "timing" else "Localization"
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        f"Scientific curiosity — randomized one-shot {domain_title.lower()} control",
        (
            "Training labels are permuted while counts and configured evaluation "
            "rows are preserved. This control is separate from the primary forecast."
        ),
        fontsize=17.0,
    )
    if domain == "timing":
        validation_axis = fig.add_axes([0.07, 0.49, 0.86, 0.31])
        x_values = []
        labels = []
        cursor = 0
        for fold in validation["fold"].drop_duplicates():
            part = validation.loc[validation["fold"].eq(fold)]
            x = np.arange(len(part)) + cursor
            x_values.extend(x.tolist())
            labels.extend(part["date"].str[5:].tolist())
            cursor = int(x[-1]) + 3
        x = np.asarray(x_values)
        validation_axis.plot(
            x,
            validation["actual"].to_numpy(float),
            color="#d62728",
            linewidth=2.0,
            label="unchanged real-event line",
        )
        validation_axis.plot(
            x,
            validation["randomized_control_score"].to_numpy(float),
            color="#4e79a7",
            linestyle="--",
            marker="o",
            markersize=3.5,
            linewidth=1.8,
            label="one-shot randomized-control score",
        )
        validation_axis.set_xticks(x[::2])
        validation_axis.set_xticklabels(
            [labels[index] for index in range(0, len(labels), 2)],
            rotation=35,
            ha="right",
            fontsize=7,
        )
        validation_axis.set_ylim(-0.04, 1.05)
        validation_axis.set_ylabel("score / actual")
        validation_axis.set_title(
            "Configured timing selection-validation rows evaluated in one fit",
            fontsize=10.5,
        )
        validation_axis.grid(True, color="#9aa6b2", alpha=0.22)
        validation_axis.legend(frameon=False, ncol=2, fontsize=7.5)

        forecast_axis = fig.add_axes([0.07, 0.25, 0.86, 0.17])
        x = np.arange(len(forecast))
        forecast_axis.plot(
            x,
            forecast["randomized_control_score"],
            color="#9fb3c8",
            marker="o",
            linewidth=2.0,
            label="randomized-label timing score",
        )
        for index, score in enumerate(
            forecast["randomized_control_score"].to_numpy(float)
        ):
            forecast_axis.annotate(
                f"{score:.3f}",
                (index, score),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                fontsize=7.2,
            )
        forecast_axis.set_xticks(x)
        forecast_axis.set_xticklabels(
            [
                interval_label(date, report_time_scale(), multiline=True)
                for date in pd.to_datetime(forecast["date"])
            ],
            rotation=25,
            ha="right",
            fontsize=7,
        )
        forecast_axis.set_ylim(0, 1.05)
        forecast_axis.set_ylabel("null-control score")
        forecast_axis.set_title(
            "Configured-window output from the randomized training-label control",
            fontsize=10.5,
        )
        forecast_axis.grid(True, color="#9aa6b2", alpha=0.22)
        forecast_axis.legend(frameon=False, fontsize=7.5)
        metric_text = (
            f"Validation quality: {control['validation_metrics']['quality_higher_is_better']:.3f}; "
            f"training positives preserved: {control['training_positive_count_preserved']}; "
            f"seed: {control['seed']}."
        )
    else:
        validation_axis = fig.add_axes([0.07, 0.49, 0.86, 0.31])
        x = np.arange(len(validation))
        actual = validation["actual_zone"].to_numpy(float)
        predicted = validation["predicted_zone"].to_numpy(float)
        offset = 0.035 if np.array_equal(actual, predicted) else 0.0
        validation_axis.plot(
            x,
            actual + offset,
            color="#d62728",
            marker="o",
            linewidth=2.0,
            label="actual validation zone",
        )
        validation_axis.plot(
            x,
            predicted - offset,
            color="#4e79a7",
            linestyle="--",
            marker="s",
            linewidth=2.0,
            label="randomized-control predicted zone",
        )
        validation_axis.set_xticks(x)
        validation_axis.set_xticklabels(
            validation["date"], rotation=0, ha="center", fontsize=7.2
        )
        validation_axis.set_yticks(
            np.arange(1, int(control["zone_count"]) + 1)
        )
        validation_axis.set_ylim(0.7, int(control["zone_count"]) + 0.3)
        validation_axis.set_ylabel("numbered geographic zone")
        validation_axis.set_title(
            "One-shot localization holdout after training-zone permutation",
            fontsize=10.5,
        )
        validation_axis.grid(True, color="#9aa6b2", alpha=0.22)
        validation_axis.legend(frameon=False, ncol=2, fontsize=7.5)

        forecast_axis = fig.add_axes([0.07, 0.25, 0.86, 0.17])
        x = np.arange(len(forecast))
        forecast_axis.plot(
            x,
            forecast["predicted_zone"],
            color="#7a5195",
            marker="o",
            linewidth=2.0,
        )
        forecast_axis.set_xticks(x)
        forecast_axis.set_xticklabels(
            [
                interval_label(date, report_time_scale(), multiline=True)
                for date in pd.to_datetime(forecast["date"])
            ],
            rotation=25,
            ha="right",
            fontsize=7,
        )
        forecast_axis.set_yticks(
            np.arange(1, int(control["zone_count"]) + 1)
        )
        forecast_axis.set_ylim(0.7, int(control["zone_count"]) + 0.3)
        forecast_axis.set_ylabel("null-control zone")
        forecast_axis.set_title(
            "Configured-window output from the randomized training-label control",
            fontsize=10.5,
        )
        forecast_axis.grid(True, color="#9aa6b2", alpha=0.22)
        metric_text = (
            f"Exact-zone validation: {control['validation_metrics']['exact_zone_accuracy']:.0%}; "
            f"top-two validation: {control['validation_metrics']['top_two_zone_accuracy']:.0%}; "
            f"seed: {control['seed']}."
        )
    fig.text(0.07, 0.125, metric_text, fontsize=8.1, color="#334e68")
    fig.text(
        0.07,
        0.085,
        textwrap.fill(
            "Interpretation: one permutation is a sensitivity check, not a formal "
            "significance distribution. Its output is shown only for comparison "
            "and has zero weight in the sequential timing/location result.",
            145,
        ),
        fontsize=7.9,
        color="#9a3412",
        weight="bold",
        va="top",
        linespacing=1.15,
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_contextual_fold_validation_page(
    pdf,
    page_number: int,
    validation_path: Path,
    summary_path: Path,
):
    """Render one uncluttered provenance chart for contextual V15-style runs."""
    frame = pd.read_csv(validation_path)
    summary = json.loads(summary_path.read_text())
    score_column = "contextual_promoted_score_not_probability"
    steps = frame["step"].drop_duplicates().astype(str).tolist()
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    row_order_share = float(
        summary.get("row_order_anchor", {}).get("selected_share", 0.0)
    )
    add_page_heading(
        fig,
        "Contextual incremental timing validation",
        (
            "Two curves only. The promoted fusion includes its parameterized "
            "order-preserving stability anchor."
        ),
        fontsize=18.0,
    )
    axis = fig.add_axes([0.07, 0.35, 0.86, 0.43])
    x = np.arange(len(frame), dtype=float) + 0.5
    actual = frame["actual"].to_numpy(float)
    score = frame[score_column].to_numpy(float)
    axis.plot(
        x,
        actual,
        color="#c53030",
        linewidth=2.5,
        drawstyle="steps-mid",
        label="held-out real-event indicator",
        zorder=4,
    )
    axis.plot(
        x,
        score,
        color="#6b46c1",
        marker="D",
        markersize=5.2,
        linewidth=2.8,
        label="promoted contextual fusion",
        zorder=5,
    )
    cursor = 0
    fold_cards = []
    for fold_index, step in enumerate(steps, start=1):
        positions = np.flatnonzero(frame["step"].astype(str).eq(step).to_numpy())
        if fold_index > 1:
            axis.axvline(
                float(positions[0]),
                color="#64748b",
                linewidth=1.1,
                linestyle=":",
                alpha=0.8,
                zorder=2,
            )
        axis.axvspan(
            float(positions[0]),
            float(positions[-1]) + 1.0,
            color="#4e79a7" if fold_index % 2 else "#f28e2b",
            alpha=0.035,
            zorder=0,
        )
        if "designated_holdout" in frame:
            designated = frame["designated_holdout"].fillna(0).to_numpy(int)
            event_positions = positions[designated[positions] == 1]
        else:
            event_positions = positions[actual[positions].astype(int) == 1]
        if len(event_positions) != 1:
            raise RuntimeError(
                f"Contextual validation fold {step} has no unique designated event"
            )
        event_position = int(event_positions[0])
        event_date = event_date_from_identifier(
            str(frame.iloc[event_position].get("event_id", "")),
            str(frame.iloc[event_position]["date"]),
        )
        axis.annotate(
            f"real event {event_date}\n"
            f"bin start {frame.iloc[event_position]['date']}\n"
            f"fusion {score[event_position]:.3f}",
            (x[event_position], score[event_position]),
            xytext=(0, 28),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="#5b21b6",
            weight="bold",
            arrowprops={
                "arrowstyle": "-|>",
                "color": "#6b46c1",
                "linewidth": 1.0,
            },
        )
        fold_payload = summary["folds"][fold_index - 1]
        metrics = fold_payload["selected"]["metrics"]
        fold_cards.append(
            (
                f"Fold {fold_index} · event {event_date}",
                (
                    f"Held-out bin starts {fold_payload['event']['date']}. "
                    f"Reliability weight {fold_payload['final_reliability_weight']:.1%}. "
                    f"Event score before stability anchor {metrics['event_score']:.3f}; "
                    f"background margin +{metrics['event_over_background_margin']:.3f}; "
                    f"false peaks {int(metrics['false_peak_count'])}; weak-peak "
                    f"retention {metrics['weak_peak_retention']:.3f}."
                ),
            )
        )
        cursor += len(positions)
    apply_interval_boundary_axis(
        axis,
        np.arange(len(frame) + 1, dtype=float),
        x,
        frame["date"].astype(str).tolist(),
        rotation=34,
        fontsize=7.0,
    )
    axis.set_xlim(0.0, float(len(frame)))
    axis.set_ylim(-0.04, 1.13)
    axis.set_yticks(np.linspace(0.0, 1.0, 6))
    axis.set_ylabel("relative validation score / binary event indicator")
    axis.set_xlabel(
        f"complete {report_time_scale().display_plural}; dotted divider = next outer fold"
    )
    axis.grid(True, axis="y", color="#9aa6b2", alpha=0.24, linewidth=0.7)
    axis.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=2,
        frameon=True,
        facecolor="white",
        framealpha=0.94,
        fontsize=8.0,
    )
    card_count = len(fold_cards) + 1
    gap = 0.012
    total_width = 0.88
    card_width = (total_width - gap * (card_count - 1)) / card_count
    for index, (heading, body) in enumerate(fold_cards):
        add_text_card(
            fig,
            0.06 + index * (card_width + gap),
            0.075,
            card_width,
            0.19,
            heading,
            body,
            wrap=max(28, int(46 * card_width / 0.28)),
            fontsize=7.6,
            facecolor="#f6f8fb",
        )
    add_text_card(
        fig,
        0.06 + len(fold_cards) * (card_width + gap),
        0.075,
        card_width,
        0.19,
        "Promoted fusion",
        (
            f"The order-preserving row shuffle contributes {row_order_share:.1%}. "
            "It changes historical row order while keeping every feature–target "
            "pair intact."
        ),
        wrap=max(28, int(46 * card_width / 0.28)),
        fontsize=7.6,
        facecolor="#f5f3ff",
        heading_color="#5b21b6",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_historical_record_comparison_page(pdf, page_number: int):
    """Trace the promoted forecast beside chronology and both random controls."""
    contextual_directory = (
        PROJECT / "05_ensemble/timing/contextual_fold_fusion"
    )
    contextual_validation_path = (
        contextual_directory / "contextual_fold_validation_predictions.csv"
    )
    contextual_summary_path = (
        contextual_directory / "contextual_fold_fusion_summary.json"
    )
    if contextual_validation_path.is_file() and contextual_summary_path.is_file():
        render_contextual_fold_validation_page(
            pdf,
            page_number,
            contextual_validation_path,
            contextual_summary_path,
        )
        return
    primary_validation = pd.read_csv(
        PROJECT / "05_ensemble/timing/validation_predictions.csv"
    )
    primary_forecast = pd.read_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv"
    )
    record_directory = PROJECT / "07_historical_record_shuffle/timing"
    record_validation = pd.read_csv(record_directory / "validation.csv")
    record_forecast = pd.read_csv(record_directory / "forecast.csv")
    record_summary = json.loads(
        (record_directory / "summary.json").read_text()
    )
    label_directory = PROJECT / "07_randomized_control/timing"
    label_validation = pd.read_csv(label_directory / "validation.csv")
    label_forecast = pd.read_csv(label_directory / "forecast.csv")
    label_summary = json.loads(
        (label_directory / "summary.json").read_text()
    )
    global_directory = (
        PROJECT / "05_ensemble/timing/metric_specialist_fusion"
    )
    global_validation_path = (
        global_directory / "false_positive_aware_validation_predictions.csv"
    )
    global_forecast_path = (
        global_directory / "metric_specialist_fusion_forecast.csv"
    )
    global_summary_path = (
        global_directory / "metric_specialist_fusion_summary.json"
    )
    has_global_fusion = bool(
        global_validation_path.is_file()
        and global_forecast_path.is_file()
        and global_summary_path.is_file()
    )
    if has_global_fusion:
        global_validation = pd.read_csv(global_validation_path)
        global_forecast = pd.read_csv(global_forecast_path)
        global_summary = json.loads(global_summary_path.read_text())
        global_validation_score_column = next(
            column
            for column in (
                "selected_score_not_probability",
                "metric_specialist_score_not_probability",
                "score_percentile_not_probability",
            )
            if column in global_validation.columns
        )
        global_forecast_score_column = next(
            column
            for column in (
                "metric_specialist_score_not_probability",
                "selected_score_not_probability",
                "score_percentile_not_probability",
            )
            if column in global_forecast.columns
        )
    else:
        global_validation = primary_validation
        global_forecast = primary_forecast
        global_summary = {}
        global_validation_score_column = "score_percentile_not_probability"
        global_forecast_score_column = "score_percentile_not_probability"
    peak_modes = forecast_peak_mode_frame()
    if not (
        primary_validation["date"].astype(str).tolist()
        == record_validation["date"].astype(str).tolist()
        == label_validation["date"].astype(str).tolist()
        == global_validation["date"].astype(str).tolist()
    ):
        raise RuntimeError(
            "Promoted timing result and controls do not share validation rows"
        )
    if not (
        primary_forecast["date"].astype(str).tolist()
        == record_forecast["date"].astype(str).tolist()
        == label_forecast["date"].astype(str).tolist()
        == global_forecast["date"].astype(str).tolist()
    ):
        raise RuntimeError(
            "Promoted timing result and controls do not share the forecast grid"
        )

    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN),
        facecolor="white",
    )
    add_page_heading(
        fig,
        "Timing provenance — promoted forecast and randomized controls",
        (
            "Same rows and bins: purple is the promoted forecast source; "
            "row-order shuffle keeps feature–target pairs, while target-label "
            "shuffle breaks them."
        ),
        fontsize=17.0,
    )
    validation_axis = fig.add_axes([0.07, 0.53, 0.86, 0.25])
    x_validation = np.arange(len(primary_validation))
    validation_axis.plot(
        x_validation,
        primary_validation["actual"].to_numpy(float),
        color="#c53030",
        linewidth=2.3,
        label="actual event indicator",
        zorder=4,
    )
    validation_axis.plot(
        x_validation,
        primary_validation[
            "score_percentile_not_probability"
        ].to_numpy(float),
        color="#1f4e79",
        marker="o",
        linewidth=2.0,
        label="chronological incremental",
    )
    if has_global_fusion:
        validation_axis.plot(
            x_validation,
            global_validation[
                global_validation_score_column
            ].to_numpy(float),
            color="#6b46c1",
            marker="D",
            markersize=4.8,
            linewidth=2.7,
            label="promoted global fusion (forecast source)",
            zorder=5,
        )
    validation_axis.plot(
        x_validation,
        record_validation[
            "historical_record_shuffle_score"
        ].to_numpy(float),
        color="#2f855a",
        marker="s",
        linestyle="--",
        linewidth=1.9,
        label="row-order shuffle (feature–target pairs kept)",
    )
    validation_axis.fill_between(
        x_validation,
        record_validation[
            "historical_record_shuffle_score"
        ].to_numpy(float)
        - record_validation["shuffle_score_std"].to_numpy(float),
        record_validation[
            "historical_record_shuffle_score"
        ].to_numpy(float)
        + record_validation["shuffle_score_std"].to_numpy(float),
        color="#2f855a",
        alpha=0.12,
        linewidth=0,
    )
    validation_axis.plot(
        x_validation,
        label_validation["randomized_control_score"].to_numpy(float),
        color="#dd6b20",
        marker="X",
        linestyle=":",
        linewidth=1.9,
        label="target-label shuffle (feature link broken)",
    )
    validation_axis.set_xticks(x_validation)
    validation_axis.set_xticklabels(
        primary_validation["date"].astype(str),
        rotation=32,
        ha="right",
        fontsize=7,
    )
    validation_axis.set_ylim(-0.04, 1.16)
    validation_axis.set_ylabel("validation score / actual")
    validation_axis.set_title(
        "Validation — real events, promoted fusion, baseline and both controls",
        fontsize=10.5,
    )
    validation_axis.grid(True, color="#9aa6b2", alpha=0.22)
    validation_axis.legend(
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        ncol=3,
        fontsize=6.7,
        loc="upper center",
    )

    forecast_axis = fig.add_axes([0.07, 0.20, 0.86, 0.24])
    x_forecast = np.arange(len(primary_forecast))
    forecast_axis.plot(
        x_forecast,
        primary_forecast[
            "score_percentile_not_probability"
        ].to_numpy(float),
        color="#1f4e79",
        marker="o",
        linewidth=2.1,
        label="chronological incremental",
    )
    if has_global_fusion:
        forecast_axis.plot(
            x_forecast,
            global_forecast[
                global_forecast_score_column
            ].to_numpy(float),
            color="#6b46c1",
            marker="D",
            markersize=5.0,
            linewidth=2.8,
            label="promoted global fusion (forecast source)",
            zorder=5,
        )
    forecast_axis.plot(
        x_forecast,
        record_forecast[
            "historical_record_shuffle_score"
        ].to_numpy(float),
        color="#2f855a",
        marker="s",
        linestyle="--",
        linewidth=1.9,
        label="row-order shuffle (feature–target pairs kept)",
    )
    forecast_axis.fill_between(
        x_forecast,
        record_forecast["shuffle_score_min"].to_numpy(float),
        record_forecast["shuffle_score_max"].to_numpy(float),
        color="#2f855a",
        alpha=0.12,
        linewidth=0,
        label="record-shuffle repeat range",
    )
    forecast_axis.plot(
        x_forecast,
        label_forecast["randomized_control_score"].to_numpy(float),
        color="#dd6b20",
        marker="X",
        linestyle=":",
        linewidth=1.9,
        label="target-label shuffle (feature link broken)",
    )
    if not peak_modes.empty:
        date_to_index = {
            str(date): index
            for index, date in enumerate(primary_forecast["date"].astype(str))
        }
        score_lookup = {
            "chronological_incremental": primary_forecast[
                "score_percentile_not_probability"
            ].to_numpy(float),
            "historical_record_shuffle": record_forecast[
                "historical_record_shuffle_score"
            ].to_numpy(float),
        }
        for date, group in peak_modes.groupby("date", sort=False):
            index = date_to_index[str(date)]
            mode = str(group.iloc[0]["selection_mode"])
            color = selection_mode_color(mode)
            forecast_axis.axvspan(
                index - 0.35,
                index + 0.35,
                color=color,
                alpha=0.07,
                zorder=0,
                label=(
                    f"configured {selection_mode_label(mode)} slot"
                    if date == peak_modes.iloc[0]["date"]
                    else None
                ),
            )
            if has_global_fusion:
                selected_score = float(
                    global_forecast.iloc[index][
                        global_forecast_score_column
                    ]
                )
                forecast_axis.scatter(
                    [index],
                    [selected_score],
                    s=105,
                    facecolors="none",
                    edgecolors=color,
                    linewidths=2.0,
                    zorder=7,
                )
                forecast_axis.annotate(
                    f"selected by global fusion\n{selected_score:.3f}",
                    (index, selected_score),
                    xytext=(10, 18),
                    textcoords="offset points",
                    fontsize=7.0,
                    color=color,
                    weight="bold",
                    arrowprops={
                        "arrowstyle": "-",
                        "color": color,
                        "linewidth": 0.9,
                    },
                    zorder=8,
                )
    forecast_axis.set_xticks(x_forecast)
    forecast_axis.set_xticklabels(
        exact_slot_labels(primary_forecast),
        rotation=24,
        ha="right",
        fontsize=7,
    )
    forecast_axis.set_ylim(0, 1.18)
    forecast_axis.set_ylabel("relative timing score")
    forecast_axis.set_title(
        "Forecast — the same four scoring histories on identical bins",
        fontsize=10.5,
    )
    forecast_axis.grid(True, color="#9aa6b2", alpha=0.22)
    forecast_axis.legend(
        frameon=True,
        facecolor="white",
        framealpha=0.92,
        ncol=3,
        fontsize=6.6,
        loc="upper center",
    )

    primary_metrics = score_quality(
        primary_validation["actual"].to_numpy(int),
        primary_validation[
            "score_percentile_not_probability"
        ].to_numpy(float),
        np.arange(len(primary_validation)),
        int(
            json.loads(
                (PROJECT / "00_config/run_manifest.json").read_text()
            )["parameters"]["event_radius"]
        ),
    )
    if has_global_fusion:
        selected_trial = global_summary["selected_trial"]
        global_metric_text = (
            "Promoted global fusion validation — mean/worst fold "
            f"{selected_trial['validation_quality_mean']:.3f}/"
            f"{selected_trial['validation_quality_worst']:.3f}; "
            "hard-negative controls below their paired events "
            f"{selected_trial['hard_negative_below_event_count']}/2. "
        )
    else:
        global_metric_text = ""
    fig.text(
        0.07,
        0.085,
        textwrap.fill(
            (
                global_metric_text
                + "Comparison qualities — chronological "
                f"{primary_metrics['quality_higher_is_better']:.3f}; "
                "row-order shuffle "
                f"{record_summary['validation_metrics']['quality_higher_is_better']:.3f}; "
                "target-label shuffle "
                f"{label_summary['validation_metrics']['quality_higher_is_better']:.3f}. "
                "Only the purple promoted-fusion curve determines the reported "
                "forecast selection; both randomized curves have zero forecast weight."
            ),
            150,
        ),
        fontsize=7.8,
        color="#334e68",
        va="top",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_clean_baseline_comparison_page(pdf, page_number: int):
    """Compare the clean sequential result against the randomized-label control."""
    audit = json.loads(
        (PROJECT / "08_comparison/clean_baseline_audit.json").read_text()
    )
    clean_master = audit["candidate_master"]
    clean_timing = audit["candidate_timing"]
    clean_location = audit["candidate_location"]
    randomized = audit["candidate_randomized_control"]
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(
        fig,
        "Clean sequential result versus randomized-label control",
        (
            "Both arms use the same model code and configured evaluation rows. "
            "The randomized arm only permutes training labels."
        ),
        fontsize=17.0,
    )
    table_axis = fig.add_axes([0.06, 0.61, 0.88, 0.19])
    table_axis.axis("off")
    rows = [
        [
            "Timing master",
            f"{clean_master['timing_rows']:,} rows · "
            f"{clean_master['timing_positive_events']} events · "
            f"{clean_master['timing_safe_features']} guarded fields",
            "Same features and holdouts; training labels permuted",
        ],
        [
            "Localization master",
            f"{clean_master['location_rows']:,} rows · "
            f"{clean_master['location_safe_features']} guarded fields",
            "Same zones and holdouts; training zone labels permuted",
        ],
        [
            "Timing validation quality",
            f"{clean_timing['validation_mean_isolation_quality']:.3f}",
            f"{randomized['timing_quality']:.3f}",
        ],
        [
            "Location exact validation",
            f"{clean_location['validation_exact_zone_accuracy']:.0%}",
            f"{randomized['location_exact_zone_accuracy']:.0%}",
        ],
    ]
    table = table_axis.table(
        cellText=rows,
        colLabels=[
            "Evidence",
            "Clean sequential",
            "Randomized-label control",
        ],
        cellLoc="left",
        colLoc="left",
        bbox=[0, 0, 1, 1],
        colWidths=[0.24, 0.38, 0.38],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.2)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        cell.set_linewidth(0.7)
        if row == 0:
            cell.set_facecolor("#17324d")
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        elif row % 2:
            cell.set_facecolor("#f8fafc")

    chart = fig.add_axes([0.07, 0.27, 0.53, 0.27])
    labels = [
        "forecast\npeak margin",
        "timing validation\nisolation quality",
        "location exact\nvalidation",
    ]
    clean_values = [
        clean_timing["peak_margin"],
        clean_timing["validation_mean_isolation_quality"],
        clean_location["validation_exact_zone_accuracy"],
    ]
    random_values = [
        np.nan,
        randomized["timing_quality"],
        randomized["location_exact_zone_accuracy"],
    ]
    x = np.arange(len(labels))
    for values, label, color, marker in (
        (clean_values, "clean sequential", "#2b6cb0", "o"),
        (random_values, "randomized labels", "#dd6b20", "s"),
    ):
        chart.plot(
            x,
            values,
            color=color,
            marker=marker,
            linewidth=2.0,
            label=label,
        )
        for index, value in enumerate(values):
            if np.isfinite(value):
                chart.annotate(
                    f"{value:.3f}",
                    (index, value),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7.3,
                )
    chart.set_xticks(x)
    chart.set_xticklabels(labels, fontsize=8)
    chart.set_ylim(0, 1.25)
    chart.set_ylabel("normalized higher-is-better value")
    chart.grid(True, axis="y", color="#94a3b8", alpha=0.22)
    chart.legend(
        frameon=False,
        fontsize=7.3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.28),
        ncol=2,
    )

    add_text_card(
        fig,
        0.64,
        0.39,
        0.30,
        0.15,
        "Clean sequential result",
        (
            f"Selected timing slot starts {clean_timing['peak_slot_start']} "
            f"with peak margin {clean_timing['peak_margin']:.3f}. "
            f"Associated localization is zone "
            f"{clean_location['peak_timing_slot_zone']} "
            f"(score {clean_location['peak_timing_slot_zone_score']:.3f})."
        ),
        wrap=48,
        fontsize=8.0,
        facecolor="#edf6ff",
        heading_color="#1f4e79",
    )
    add_text_card(
        fig,
        0.64,
        0.21,
        0.30,
        0.15,
        "Randomized-label control",
        (
            f"Sequential timing quality is "
            f"{clean_timing['validation_mean_isolation_quality']:.3f}; "
            f"randomized timing is {randomized['timing_quality']:.3f}. "
            f"Sequential location is "
            f"{clean_location['validation_exact_zone_accuracy']:.0%} exact; "
            f"randomized location is "
            f"{randomized['location_exact_zone_accuracy']:.0%}."
        ),
        wrap=48,
        fontsize=8.0,
        facecolor="#eefbf3",
        heading_color="#166534",
    )
    fig.text(
        0.07,
        0.14,
        (
            "The primary reported forecast uses only the clean sequential arm. "
            "Randomized-label output is shown solely for comparison."
        ),
        fontsize=9.0,
        color="#102a43",
        weight="bold",
    )
    fig.text(
        0.07,
        0.105,
        (
            "The randomized experiment is a one-permutation sensitivity check, "
            "not a formal null distribution, and it has zero primary weight."
        ),
        fontsize=8.2,
        color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_conclusion_page(pdf, narrative: dict, page_number: int):
    conclusion = narrative["conclusion"]
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Conclusions — achieved result, advantages and evidence limits",
    )
    sections = [
        (
            "What was achieved",
            conclusion["demonstrated"],
            "#edf6ff",
            "#1f4e79",
        ),
        (
            "Practical advantages of the approach",
            conclusion["practical_advantages"],
            "#f0fdf4",
            "#166534",
        ),
        (
            "Evidence limits and open research question",
            conclusion["evidence_limits"],
            "#fff7ed",
            "#9a3412",
        ),
    ]
    y_positions = [0.65, 0.38, 0.145]
    heights = [0.20, 0.20, 0.19]
    for (heading, items, facecolor, heading_color), y, height in zip(
        sections, y_positions, heights
    ):
        body = "\n".join(f"• {item}" for item in items)
        add_text_card(
            fig,
            0.05,
            y,
            0.90,
            height,
            heading,
            body,
            wrap=145,
            fontsize=8.8,
            facecolor=facecolor,
            heading_color=heading_color,
        )
    fig.text(
        0.06,
        0.092,
        textwrap.fill(conclusion["final_statement"], 125),
        fontsize=8.9,
        color="#102a43",
        weight="bold",
        va="top",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_extended_master_search_page(pdf, page_number: int):
    """Render the optional JSON/CSV-driven compact-master sensitivity audit."""
    root = PROJECT / "08_extended_search/master_screen"
    candidates = pd.read_csv(root / "all_master_candidates.csv")
    summary = json.loads(
        (root / "extended_master_search_summary.json").read_text(encoding="utf-8")
    )
    best = (
        candidates.sort_values("global_rank")
        .groupby("hard_negative_training_actual", as_index=False)
        .first()
        .sort_values("hard_negative_training_actual")
    )
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Extended temporal-master and hard-negative sensitivity",
        subtitle=(
            f"{len(candidates):,} candidates; chronological holdouts and "
            "world-control validation events frozen across every comparison"
        ),
    )
    left = fig.add_axes([0.07, 0.48, 0.54, 0.34])
    x = np.arange(len(best))
    width = 0.34
    left.bar(
        x - width / 2,
        best["validation_quality_mean"],
        width,
        label="validation mean",
        color="#2f75b5",
    )
    left.bar(
        x + width / 2,
        best["validation_quality_worst"],
        width,
        label="worst fold",
        color="#f28e2b",
    )
    left.set_xticks(x, best["hard_negative_training_actual"].astype(int))
    left.set_xlabel("retained non-Japan training controls")
    left.set_ylabel("quality (higher is better)")
    left.set_ylim(0, max(0.7, float(best["validation_quality_mean"].max()) + 0.12))
    left.grid(axis="y", alpha=0.25)
    left.legend(frameon=False, fontsize=8, loc="upper right")
    left.set_title("Best compact master at each negative-control level", fontsize=10.5, weight="bold")

    right = fig.add_axes([0.67, 0.48, 0.27, 0.34])
    bars = right.barh(
        x,
        best["selected_historical_rows"],
        color="#76b7b2",
        edgecolor="white",
    )
    right.set_yticks(x, best["hard_negative_training_actual"].astype(int))
    right.invert_yaxis()
    right.set_xlabel("historical rows")
    right.set_ylabel("non-Japan controls")
    right.grid(axis="x", alpha=0.25)
    right.set_title("Resulting compact-series size", fontsize=10.5, weight="bold")
    for bar, (_, row) in zip(bars, best.iterrows()):
        right.text(
            max(4.0, bar.get_width() - max(best["selected_historical_rows"]) * 0.02),
            bar.get_y() + bar.get_height() / 2,
            f"kE {int(row['k_event'])} · kB {int(row['k_between'])}",
            va="center",
            ha="right",
            fontsize=7.2,
            color="white",
            weight="bold",
        )

    winner = summary["winner"]
    controls = summary.get("frozen_validation_controls", [])
    add_text_card(
        fig, 0.05, 0.16, 0.285, 0.22,
        "Question answered",
        "How do event-neighbourhood density, between-event sampling and retained world negatives change fast chronological validation?",
        wrap=45,
        fontsize=8.0,
    )
    add_text_card(
        fig, 0.357, 0.16, 0.285, 0.22,
        "Selected screen result",
        (
            f"{int(winner['hard_negative_training_actual'])} controls; "
            f"k_event={int(winner['k_event'])}, k_between={int(winner['k_between'])}, "
            f"proximity={float(winner['proximity_fraction']):.2f}; "
            f"{int(winner['selected_historical_rows'])} historical rows; "
            f"mean/worst={float(winner['validation_quality_mean']):.3f}/"
            f"{float(winner['validation_quality_worst']):.3f}."
        ),
        wrap=45,
        fontsize=8.0,
        facecolor="#edf6ff",
        heading_color="#1f4e79",
    )
    add_text_card(
        fig, 0.665, 0.16, 0.285, 0.22,
        "Control integrity",
        (
            f"Non-Japan controls were never removed. {len(controls)} validation "
            "controls stayed fixed; their original magnitude and coordinates "
            "remain audit-only and cannot leak into astronomical features."
        ),
        wrap=45,
        fontsize=8.0,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_extended_model_search_page(pdf, page_number: int):
    """Render optional feature/capacity/hybrid research from persisted CSV."""
    path = (
        PROJECT
        / "08_extended_search/timing_models/timing_model_research_ranking.csv"
    )
    ranking = pd.read_csv(path).sort_values("rank").head(10)
    fig = plt.figure(figsize=(11.7, 8.3), facecolor="white")
    add_page_heading(
        fig,
        "Extended timing feature, capacity and hybrid-model search",
        subtitle=(
            "Every row reruns feature ranking, conservative ablation, real-model "
            "guards, LCS/KAN/deep/logistic/tree systems and metric-specialist fusion"
        ),
        fontsize=18.0,
    )
    labels = [
        "\n".join(textwrap.wrap(str(value).replace("_", " "), 21))
        for value in ranking["name"]
    ]
    y = np.arange(len(ranking))
    top = fig.add_axes([0.25, 0.47, 0.69, 0.36])
    height = 0.34
    top.barh(
        y - height / 2,
        ranking["fusion_validation_mean"],
        height,
        color="#2f75b5",
        label="fusion validation mean",
    )
    top.barh(
        y + height / 2,
        ranking["fusion_validation_worst"],
        height,
        color="#f28e2b",
        label="worst fold",
    )
    if "fusion_false_positive_worst" in ranking:
        top.scatter(
            ranking["fusion_false_positive_worst"],
            y,
            marker="D",
            s=38,
            color="#2e8b57",
            edgecolor="white",
            linewidth=0.6,
            label="false-positive skill · worst fold",
            zorder=5,
        )
    top.set_yticks(y, labels, fontsize=7.7)
    top.invert_yaxis()
    displayed_maximum = float(ranking["fusion_validation_mean"].max())
    if "fusion_false_positive_worst" in ranking:
        displayed_maximum = max(
            displayed_maximum,
            float(ranking["fusion_false_positive_worst"].max()),
        )
    top.set_xlim(0, max(1.0, displayed_maximum + 0.18))
    top.set_xlabel("quality (higher is better)")
    top.grid(axis="x", alpha=0.25)
    legend_handles, legend_labels = top.get_legend_handles_labels()
    fig.legend(
        legend_handles,
        legend_labels,
        frameon=False,
        fontsize=7.4,
        loc="lower center",
        bbox_to_anchor=(0.60, 0.825),
        ncol=3,
    )
    for index, row in ranking.reset_index(drop=True).iterrows():
        top.text(
            max(row["fusion_validation_mean"], row["fusion_validation_worst"]) + 0.012,
            index,
            f"{int(row['fusion_exact_peak_count'])}/2 peaks · "
            f"{int(row.get('hard_negative_below_event_count', 0))}/2 controls",
            va="center",
            fontsize=6.7,
            color="#334e68",
        )

    winner = ranking.iloc[0]
    add_text_card(
        fig, 0.05, 0.16, 0.285, 0.22,
        "How to read",
        "Blue rewards average chronological performance; orange exposes the weaker holdout; green marks false-positive skill on that fold. Row suffixes report exact peaks and suppressed controls.",
        wrap=45,
        fontsize=8.0,
    )
    add_text_card(
        fig, 0.357, 0.16, 0.285, 0.22,
        "Selected configuration",
        (
            f"{str(winner['name']).replace('_', ' ')}; profile={winner['model_profile']}; "
            f"epoch scale={float(winner['epochs_scale']):.2f}; "
            f"mean/worst={float(winner['fusion_validation_mean']):.3f}/"
            f"{float(winner['fusion_validation_worst']):.3f}; "
            f"false-positive mean/worst="
            f"{float(winner['fusion_false_positive_mean']):.3f}/"
            f"{float(winner['fusion_false_positive_worst']):.3f}; "
            f"exact peaks={int(winner['fusion_exact_peak_count'])}/2."
        ),
        wrap=45,
        fontsize=8.0,
        facecolor="#edf6ff",
        heading_color="#1f4e79",
    )
    add_text_card(
        fig, 0.665, 0.16, 0.285, 0.22,
        "Interpretation",
        "Green diamonds expose hard-negative/background rejection on the weaker fold. Larger deep/xdeep profiles remain JSON-selectable but are rejected when either timing quality or false-positive control falls.",
        wrap=45,
        fontsize=8.0,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def _friendly_metric_name(value: str) -> str:
    return str(value).replace("_", " ").replace("brier", "Brier").title()


def render_contextual_contribution_page(pdf, page_number: int, payload: dict):
    """Show how fold-specific systems become the promoted forecast."""
    summary = payload["summary"]
    trace = payload["contribution_trace"]
    folds = summary["folds"]
    actual_event_dates = {
        str(fold["step"]): event_date_from_identifier(
            str(fold["event"].get("event_id", "")),
            str(fold["event"]["date"]),
        )
        for fold in folds
    }
    contribution_rows = []
    for fold in folds:
        step = str(fold["step"])
        fold_trace = trace["final_contributions"][step]
        for system, weight in fold_trace["system_weights"].items():
            contribution_rows.append(
                {
                    "fold": step,
                    "event": actual_event_dates[step],
                    "system": system,
                    "within_fold": float(weight),
                    "final": float(weight)
                    * float(fold_trace["pre_anchor_contribution"]),
                }
            )
    system_names = list(
        dict.fromkeys(row["system"] for row in contribution_rows)
    )
    system_colors = {
        system: plt.get_cmap("tab10")(index % 10)
        for index, system in enumerate(system_names)
    }
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(
        fig,
        "Fold-contextual timing fusion — audited forecast composition",
        (
            "Each holdout selects its own model mix; that mix is projected "
            "forward and weighted by its validation reliability."
        ),
        fontsize=17.5,
    )
    final_axis = fig.add_axes([0.09, 0.62, 0.82, 0.16])
    left = 0.0
    for row in contribution_rows:
        final_axis.barh(
            [0],
            [row["final"]],
            left=left,
            height=0.55,
            color=system_colors[row["system"]],
            edgecolor="white",
            linewidth=0.7,
        )
        if row["final"] >= 0.055:
            final_axis.text(
                left + row["final"] / 2,
                0,
                f"{row['final']:.1%}",
                ha="center",
                va="center",
                fontsize=7.2,
                color="white",
                weight="bold",
            )
        left += row["final"]
    anchor = float(trace["row_order_anchor_contribution"])
    final_axis.barh(
        [0],
        [anchor],
        left=left,
        height=0.55,
        color="#94a3b8",
        edgecolor="white",
    )
    final_axis.set_xlim(0, 1)
    final_axis.set_yticks([])
    final_axis.set_xlabel("absolute contribution to the promoted forecast")
    final_axis.set_title("Final contribution after fold reliability and stability anchor")
    final_axis.grid(True, axis="x", alpha=0.20)
    legend_handles = [
        Patch(
            facecolor=system_colors[system],
            edgecolor="white",
            label=SYSTEM_DISPLAY_NAMES.get(
                system, str(system).replace("_", " ")
            ),
        )
        for system in system_names
    ]
    if anchor > 1e-12:
        legend_handles.append(
            Patch(
                facecolor="#94a3b8",
                edgecolor="white",
                label="Feature–target preserving row-order anchor",
            )
        )
    final_axis.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.40),
        ncol=min(5, max(1, len(legend_handles))),
        fontsize=6.3,
        frameon=False,
    )

    fold_axis = fig.add_axes([0.12, 0.26, 0.76, 0.18])
    y = np.arange(len(folds))
    for fold_index, fold in enumerate(folds):
        step = str(fold["step"])
        fold_rows = [row for row in contribution_rows if row["fold"] == step]
        fold_left = 0.0
        for row in fold_rows:
            fold_axis.barh(
                [fold_index],
                [row["within_fold"]],
                left=fold_left,
                height=0.55,
                color=system_colors[row["system"]],
                edgecolor="white",
                linewidth=0.7,
            )
            if row["within_fold"] >= 0.12:
                fold_axis.text(
                    fold_left + row["within_fold"] / 2,
                    fold_index,
                    str(row["system"]).replace("_", " "),
                    ha="center",
                    va="center",
                    fontsize=7.0,
                    color="white",
                    weight="bold",
                )
            fold_left += row["within_fold"]
    fold_axis.set_xlim(0, 1)
    fold_axis.set_yticks(y)
    fold_axis.set_yticklabels(
        [
            f"Fold {index + 1}\nevent "
            f"{actual_event_dates[str(fold['step'])]}"
            for index, fold in enumerate(folds)
        ],
        fontsize=8,
    )
    fold_axis.invert_yaxis()
    fold_axis.set_title("Different combinations retained for different historical contexts")
    fold_axis.grid(True, axis="x", alpha=0.20)

    reliability_text = "; ".join(
        f"{actual_event_dates[str(fold['step'])]}: "
        f"{float(fold['final_reliability_weight']):.1%}"
        for fold in folds
    )
    projection_text = "; ".join(
        f"{actual_event_dates[str(fold['step'])]}: "
        f"{float(fold['origin_projection_share']):.1%} origin / "
        f"{1.0 - float(fold['origin_projection_share']):.1%} all-history refit"
        for fold in folds
    )
    add_text_card(
        fig, 0.07, 0.075, 0.265, 0.15,
        "Fold reliability",
        reliability_text,
        wrap=38,
        fontsize=7.5,
    )
    add_text_card(
        fig, 0.367, 0.075, 0.265, 0.15,
        "Projection blend",
        projection_text,
        wrap=38,
        fontsize=7.5,
    )
    add_text_card(
        fig, 0.665, 0.075, 0.265, 0.15,
        "Control weights",
        (
            f"Order-preserving anchor {anchor:.1%}; target-label randomized "
            f"{float(trace['target_label_randomized_contribution']):.1%}. "
            "The latter is a null control, never a forecast source."
        ),
        wrap=38,
        fontsize=7.5,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_composite_timing_page(pdf, page_number: int):
    """Render the full two-way decomposition from the persisted JSON trace."""
    timing_payload = report_composite()["timing"]
    if (
        timing_payload.get("promoted_family") == "contextual_fold_fusion"
        and timing_payload.get("contextual_fold_fusion")
    ):
        render_contextual_contribution_page(
            pdf,
            page_number,
            timing_payload["contextual_fold_fusion"],
        )
        return
    specialist = timing_payload["metric_specialist"]
    trace = specialist["contribution_trace"]
    trial = specialist["selected_trial"]
    system_rows = sorted(
        trace["system_totals"],
        key=lambda row: float(row["reconstructed_final_weight"]),
        reverse=True,
    )
    system_names = [row["system"] for row in system_rows]
    metric_rows = trace["metric_components"]
    has_core = float(trace["core_share"]) > 1e-12
    source_names = [
        *(["overall_core"] if has_core else []),
        *[row["metric"] for row in metric_rows],
    ]
    system_colors = {
        name: plt.get_cmap("tab10")(index % 10)
        for index, name in enumerate(system_names)
    }
    source_colors = {
        name: plt.get_cmap("Set2")(index % 8)
        for index, name in enumerate(source_names)
    }
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(
        fig,
        "False-positive-aware timing fusion — full contribution trace",
    )
    left = fig.add_axes([0.20, 0.27, 0.35, 0.55])
    component_labels = [
        *(
            [f"Overall-quality core ({float(trace['core_share']):.1%})"]
            if has_core
            else []
        ),
        *[
            f"{_friendly_metric_name(row['metric'])} "
            f"({float(row['final_fusion_share']):.1%})"
            for row in metric_rows
        ],
    ]
    component_y = np.arange(len(component_labels))
    component_sources = [
        *(
            [
                {
                    row["system"]: float(row["core_contribution"])
                    for row in system_rows
                }
            ]
            if has_core
            else []
        ),
        *[
            {
                row["system"]: float(
                    row["metric_contributions"].get(metric["metric"], 0.0)
                )
                for row in system_rows
            }
            for metric in metric_rows
        ],
    ]
    component_left = np.zeros(len(component_labels), dtype=float)
    for system in system_names:
        values = np.array(
            [source.get(system, 0.0) for source in component_sources],
            dtype=float,
        )
        left.barh(
            component_y,
            values,
            left=component_left,
            color=system_colors[system],
            label=SYSTEM_DISPLAY_NAMES.get(
                system, system.replace("_", " ").title()
            ),
        )
        for index, value in enumerate(values):
            if value >= 0.018:
                left.text(
                    component_left[index] + value / 2,
                    index,
                    f"{value:.1%}",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white",
                    weight="bold",
                )
        component_left += values
    left.set_yticks(component_y)
    left.set_yticklabels(component_labels, fontsize=7.0)
    left.invert_yaxis()
    left.set_xlabel("absolute contribution to final timing weight")
    left.set_title("Each fusion component, stacked by system", weight="bold")
    left.grid(True, axis="x", alpha=0.22)
    left.legend(
        frameon=False,
        fontsize=5.8,
        ncol=2,
        loc="lower right",
    )

    right = fig.add_axes([0.68, 0.27, 0.27, 0.55])
    system_y = np.arange(len(system_rows))
    source_left = np.zeros(len(system_rows), dtype=float)
    for source in source_names:
        if source == "overall_core":
            values = np.array(
                [float(row["core_contribution"]) for row in system_rows]
            )
            label = "Overall-quality core"
        else:
            values = np.array(
                [
                    float(row["metric_contributions"].get(source, 0.0))
                    for row in system_rows
                ]
            )
            label = _friendly_metric_name(source)
        right.barh(
            system_y,
            values,
            left=source_left,
            color=source_colors[source],
            label=label,
        )
        source_left += values
    right.set_yticks(system_y)
    right.set_yticklabels(
        [
            SYSTEM_DISPLAY_NAMES.get(
                row["system"], row["system"].replace("_", " ").title()
            )
            for row in system_rows
        ],
        fontsize=6.8,
    )
    right.invert_yaxis()
    right.set_xlabel("final system weight")
    right.set_title("Each system weight, decomposed by source", weight="bold")
    right.grid(True, axis="x", alpha=0.22)
    for index, value in enumerate(source_left):
        right.text(
            value + 0.004,
            index,
            f"{value:.1%}",
            va="center",
            fontsize=6.8,
            weight="bold",
        )
    right.legend(
        frameon=False,
        fontsize=5.7,
        ncol=1,
        loc="lower right",
    )

    if trace.get("portfolio_metric_quality_share") is None:
        safeguard_details = (
            "The selected seeded direct-system mixture is evaluated by the "
            "declared timing-quality, exact-peak and false-positive objective; "
            "its automatically selected system weights are shown above."
        )
    else:
        safeguard_details = (
            f"The overall-quality core retains {float(trace['core_share']):.0%} "
            f"of the final score and metric specialists receive "
            f"{float(trace['specialist_share']):.0%}. Within each specialist "
            f"portfolio, metric evidence contributes "
            f"{float(trace['portfolio_metric_quality_share']):.0%} and overall "
            f"quality contributes "
            f"{float(trace['portfolio_overall_quality_share']):.0%}."
        )

    add_text_card(
        fig,
        0.06,
        0.09,
        0.88,
        0.125,
        "Selection result and safeguards",
        (
            f"Selected trial {int(trial['trial_id'])}: "
            f"mean validation quality {float(trial['validation_quality_mean']):.3f}; "
            f"worst-fold quality {float(trial['validation_quality_worst']):.3f}; "
            f"exact held-out peaks {int(trial['exact_peak_count'])}. "
            f"{safeguard_details} "
            "All values on this page are read from report_composite_data.json."
        ),
        wrap=150,
        fontsize=8.4,
        facecolor="#f5f3ff",
        heading_color="#553c9a",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_composite_location_page(pdf, page_number: int):
    """Report geographic validation evidence and the reliability cap."""
    payload = report_composite()["localization"]
    reliability = payload["reliability"]
    validation = pd.read_csv(Path(payload["validation_csv"]))
    confidence = reliability["true_zone_confidence"]
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(fig, "Localization validation — confidence, distance and reliability")
    left = fig.add_axes([0.07, 0.43, 0.35, 0.38])
    labels = ["Selected location\nmodel", "Training-zone\nprior", "Randomized-label\ncontrol"]
    values = [
        float(confidence["primary_soft_fusion"]),
        float(confidence["training_prior_baseline"]),
        float(confidence["randomized_label_control"]),
    ]
    bars = left.bar(labels, values, color=["#2b70b8", "#9aa6b2", "#f28e2b"])
    left.set_ylim(0, 1.05)
    left.set_ylabel("mean confidence assigned to the true zone")
    left.set_title("Discriminating validation metric", weight="bold")
    left.grid(True, axis="y", alpha=0.22)
    for bar, value in zip(bars, values):
        left.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.3f}", ha="center", fontsize=8, weight="bold")

    right = fig.add_axes([0.51, 0.43, 0.43, 0.38])
    event_labels = [str(value)[:10] for value in validation["date"]]
    distances = validation.get(
        "centroid_distance_km",
        pd.Series(np.nan, index=validation.index),
    ).to_numpy(float)
    if np.isnan(distances).all():
        summary = payload["summary"]["validation_metrics"]
        distances = np.asarray(summary["distances_km"], dtype=float)
    confidence_values = validation["predicted_zone_confidence"].to_numpy(float)
    x = np.arange(len(validation))
    right.bar(x - 0.18, confidence_values, width=0.36, color="#59a14f", label="true-zone confidence")
    distance_scaled = distances / max(float(np.max(distances)), 1.0)
    right.bar(x + 0.18, distance_scaled, width=0.36, color="#76b7b2", label="centroid distance (scaled)")
    right.set_xticks(x)
    right.set_xticklabels(event_labels, rotation=25, ha="right", fontsize=7.5)
    right.set_ylim(0, 1.08)
    right.set_title("All chronological holdout events", weight="bold")
    right.legend(frameon=False, fontsize=7.4)
    right.grid(True, axis="y", alpha=0.22)
    for index, distance in enumerate(distances):
        right.text(index + 0.18, distance_scaled[index] + 0.025, f"{distance:.0f} km", ha="center", fontsize=6.7)

    distinct_zones = int(reliability["distinct_validation_zones"])
    if distinct_zones < 2:
        card_title = "Why exact accuracy is not used alone"
        card_body = (
            f"Exact-zone accuracy is {float(reliability['exact_zone_accuracy']):.0%}, "
            f"but all {int(reliability['validation_events'])} chronological holdouts "
            f"belong to Zone {int(reliability['majority_zone'])}; exact accuracy "
            "therefore cannot measure multi-zone discrimination. The selected "
            f"model assigns {values[0]:.3f} mean confidence to the true zone "
            f"versus {values[1]:.3f} for the prior and {values[2]:.3f} for "
            f"randomized labels. Reliability is capped at "
            f"{float(reliability['applied_reliability_weight']):.0%}. "
            f"Reason: {reliability['reason_for_cap']}."
        )
    else:
        actual_counts = validation["actual_zone"].value_counts().sort_index()
        count_text = ", ".join(
            f"Zone {int(zone)}: {int(count)}"
            for zone, count in actual_counts.items()
        )
        card_title = "Multi-zone chronological validation and reliability"
        card_body = (
            f"The holdout covers {distinct_zones} zones ({count_text}). Primary "
            f"exact accuracy is {float(reliability['exact_zone_accuracy']):.0%}; "
            f"the training-prior baseline is "
            f"{float(reliability['majority_exact_zone_accuracy']):.0%} and "
            f"randomized-label exact accuracy is "
            f"{float(reliability['randomized_exact_zone_accuracy']):.0%}. "
            f"Mean true-zone confidence is {values[0]:.3f} for the selected "
            f"model, {values[1]:.3f} for the prior and {values[2]:.3f} for "
            f"randomized labels. The resulting experimental location weight "
            f"is {float(reliability['applied_reliability_weight']):.1%}; this "
            "low weight preserves the weak-control result instead of overstating it."
        )
    add_text_card(
        fig,
        0.06,
        0.105,
        0.88,
        0.245,
        card_title,
        card_body,
        wrap=148,
        fontsize=8.5,
        facecolor="#fff7ed",
        heading_color="#9a3412",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def render_composite_joint_page(pdf, page_number: int):
    """Show the persisted reliability-tempered timing × location forecast."""
    payload = report_composite()["joint_timing_location"]
    frame = pd.read_csv(Path(payload["forecast_csv"]))
    timing_column = (
        "primary_timing_score_not_probability"
        if "primary_timing_score_not_probability" in frame
        else "metric_specialist_score_not_probability"
    )
    timing_label = (
        "fold-contextual timing total"
        if report_composite().get("timing", {}).get("promoted_family")
        == "contextual_fold_fusion"
        else "timing composite total"
    )
    x = np.arange(len(frame), dtype=float) + 0.5
    fig = plt.figure(
        figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
    )
    add_page_heading(fig, "Experimental joint timing × conditional localization")
    axis = fig.add_axes([0.07, 0.28, 0.88, 0.55])
    primary_selection = forecast_peak_mode_frame()
    focus_index = None
    focus_mode = None
    if not primary_selection.empty:
        selected_date = str(primary_selection.iloc[0]["date"])
        frame_dates = frame["date"].astype(str).tolist()
        if selected_date in frame_dates:
            focus_index = frame_dates.index(selected_date)
            focus_mode = str(primary_selection.iloc[0]["selection_mode"])
            axis.axvspan(
                focus_index,
                focus_index + 1.0,
                color=selection_mode_color(focus_mode),
                alpha=0.10,
                label=(
                    f"{selection_mode_label(focus_mode)} location focus"
                ),
                zorder=0,
            )
    bottom = np.zeros(len(frame), dtype=float)
    zone_count = len(
        report_composite()["localization"]["reliability"][
            "training_zone_priors"
        ]
    )
    for zone in range(1, zone_count + 1):
        values = frame[f"joint_zone_{zone}_experimental_score"].to_numpy(float)
        axis.bar(
            x,
            values,
            bottom=bottom,
            width=0.78,
            color=ZONE_COLORS[zone],
            label=f"Zone {zone} contribution",
        )
        bottom += values
    axis.plot(
        x,
        frame[timing_column].to_numpy(float),
        color="#102a43",
        marker="o",
        linewidth=1.6,
        label=timing_label,
        zorder=4,
    )
    if focus_index is not None and focus_mode is not None:
        focus_total = float(
            frame.iloc[focus_index][timing_column]
        )
        axis.annotate(
            f"{selection_mode_label(focus_mode)}\n"
            f"Zone {int(primary_selection.iloc[0]['predicted_zone'])}",
            (x[focus_index], focus_total),
            xytext=(0, 28),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=selection_mode_color(focus_mode),
            weight="bold",
            arrowprops=dict(
                arrowstyle="-|>",
                color=selection_mode_color(focus_mode),
                linewidth=1.1,
            ),
        )
    apply_interval_boundary_axis(
        axis,
        np.arange(len(frame) + 1, dtype=float),
        x,
        exact_slot_labels(frame),
        rotation=32,
        fontsize=7.2,
    )
    axis.set_xlim(0.0, float(len(frame)))
    axis.set_ylabel("experimental relative score — not a probability")
    axis.set_xlabel("complete forecast windows [start, end)")
    axis.grid(True, axis="y", alpha=0.22)
    axis.legend(ncol=min(5, zone_count + 1), frameon=False, fontsize=7.4, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    add_text_card(
        fig,
        0.06,
        0.08,
        0.88,
        0.13,
        "Reading rule",
        (
            "Bar height is the timing composite; colored segments allocate that same "
            "score conditionally across the learned zones. Localization reliability "
            f"is limited to {float(payload['reliability_weight']):.0%}; the remaining "
            "share follows the historical training-zone prior. No segment is a "
            "calibrated earthquake probability."
        ),
        wrap=150,
        fontsize=8.4,
        facecolor="#edf6ff",
        heading_color="#1f4e79",
    )
    add_report_footer(fig, page_number)
    pdf.savefig(fig)
    plt.close(fig)


def build_pdf(
    figures: list[Path],
    timing_event_figures: list[Path],
    timing_summary: dict,
    location_summary: dict,
):
    manifest = json.loads((PROJECT / "00_config/run_manifest.json").read_text())
    narrative = json.loads(
        (PROJECT / "00_config/report_narrative.json").read_text()
    )
    workflow = json.loads(
        (PROJECT / "00_config/report_workflow.json").read_text()
    )
    parameters = manifest["parameters"]
    composite = report_composite()
    astro_audit_path = PROJECT / "00_config/astro_source_audit.json"
    observer = (
        json.loads(astro_audit_path.read_text())
        .get("required_contract", {})
        .get("observer", {})
        if astro_audit_path.is_file()
        else {}
    )
    observer_cover = (
        f"\nobserver: {observer.get('label', 'configured')} · "
        f"{observer['latitude']:g}° N, {observer['longitude']:g}° E · "
        f"{observer['elevation_km']:g} km"
        if {
            "latitude",
            "longitude",
            "elevation_km",
        }.issubset(observer)
        else ""
    )
    context_path = (
        PROJECT / "05_ensemble/timing/forecast_event_context.json"
    )
    context_explanation = None
    if INCLUDE_OBSERVED_EVENT_CONTEXT and context_path.is_file():
        context = json.loads(context_path.read_text())
        anchor = context["anchor_event"]
        first = next(
            row
            for row in context["selections"]
            if row["role"] == "first_significant_post_event_peak"
        )
        maximum = next(
            row
            for row in context["selections"]
            if row["role"] == "maximum_post_event_peak"
        )
        context_explanation = {
            "question": (
                "After the observed reference event, which weekly intervals "
                "rank first and highest in this focused "
                f"M{report_target_magnitude_label()}+ experiment?"
            ),
            "reading": (
                "Both training histories are lines on identical weekly bins. "
                "The gray X is the bin containing the observed event; the "
                "triangle and star identify post-event first and maximum peaks."
            ),
            "result": (
                f"The M{anchor['magnitude']:.1f} reference event maps to its "
                f"weekly bin. The first post-event selection starts "
                f"{first['date']}; the post-event maximum starts "
                f"{maximum['date']}."
            ),
            "caution": (
                "The vertical score does not predict magnitude and is not an "
                "earthquake probability. A higher score than the reference bin "
                "does not imply an event larger than the observed earthquake."
            ),
        }
    magnitude_payload = composite.get("conditional_magnitude_recalibration")
    magnitude_explanation = None
    magnitude_figure = None
    if magnitude_payload:
        magnitude_summary = magnitude_payload["summary"]
        magnitude_focus = magnitude_summary["focus_window"]
        magnitude_calibration = magnitude_summary["calibration"]
        magnitude_figure = Path(magnitude_payload["standalone_png"])
        if not magnitude_figure.is_absolute():
            magnitude_figure = PROJECT / magnitude_figure
        magnitude_explanation = {
            "question": (
                "If an additional target event occurs in the configured focus "
                "window, what magnitude is compatible with the V16 timing "
                "score and its out-of-sample anchors?"
            ),
            "reading": (
                "The left panel fits magnitude to genuinely held-out timing "
                "scores. The right panels show the shifted timing grid and "
                "conditional magnitude intervals. Stars are observations, not "
                "training targets."
            ),
            "result": (
                f"For {magnitude_focus['start']} through "
                f"{magnitude_focus['end']}, the conditional centre is "
                f"M{magnitude_focus['conditional_central_magnitude']:.2f} "
                f"with an experimental interval of "
                f"M{magnitude_focus['conditional_lower_magnitude']:.2f}–"
                f"{magnitude_focus['conditional_upper_magnitude']:.2f}. "
                f"The largest event observed by "
                f"{magnitude_focus['as_of_date']} is "
                f"M{magnitude_focus['observed_floor_magnitude']:.1f}. "
                f"Before applying the configured target-magnitude floor, the "
                f"robust fit is M{magnitude_focus['raw_fitted_magnitude']:.2f}. "
                f"{magnitude_focus['interpretation']}"
            ),
            "caution": (
                f"{magnitude_summary['conditional_statement']} The fit uses "
                f"only {magnitude_calibration['anchor_count']} independent "
                "magnitude anchors, so its interval is exploratory."
            ),
        }
    workflow_pages = [
        {
            "title": "Reproducible workflow overview",
            "kind": "workflow_overview",
            "section": "workflow",
        }
    ]
    for stage in workflow["stages"]:
        workflow_pages.append(
            {
                "title": (
                    f"Workflow phase {stage['order']} — {stage['title']}"
                ),
                "kind": "workflow_phase",
                "stage": stage,
                "section": "workflow",
            }
        )
        if stage["id"] == "feature_search":
            workflow_pages.extend(
                [
                    {
                        "title": "Timing feature-search evidence — top 20 fields",
                        "kind": "feature_evidence",
                        "domain": "timing",
                        "section": "workflow",
                    },
                    {
                        "title": "Localization feature-search evidence — top 20 fields",
                        "kind": "feature_evidence",
                        "domain": "localization",
                        "section": "workflow",
                    },
                    {
                        "title": "Celestial-body summary across complete rankings",
                        "kind": "body_summary",
                        "section": "workflow",
                    },
                ]
            )
        if stage["id"] in {"timing_models", "location_models"}:
            domain = (
                "timing" if stage["id"] == "timing_models" else "localization"
            )
            domain_title = (
                "Timing" if domain == "timing" else "Localization"
            )
            workflow_pages.append(
                {
                    "title": f"{domain_title} top-three model evidence",
                    "kind": "model_ranking_evidence",
                    "domain": domain,
                    "section": "workflow",
                }
            )
            components = []
            for system in workflow["model_evidence"][domain]["top_systems"]:
                for component in system["components"]:
                    if component not in components:
                        components.append(component)
            chunks = [
                components[index : index + 2]
                for index in range(0, len(components), 2)
            ]
            for chunk_index, chunk in enumerate(chunks, 1):
                suffix = (
                    f" ({chunk_index}/{len(chunks)})"
                    if len(chunks) > 1
                    else ""
                )
                workflow_pages.append(
                    {
                        "title": (
                            f"{domain_title} executed model parameters{suffix}"
                        ),
                        "kind": "model_parameters",
                        "domain": domain,
                        "components": chunk,
                        "section": "workflow",
                    }
                )
    diagnostics_tag = REPORT_VERSION
    diagnostics_path = REPORT / f"{diagnostics_tag}_diagnostics.json"
    if not diagnostics_path.is_file():
        diagnostics_path = REPORT / "v17_diagnostics.json"
    diagnostics = (
        json.loads(diagnostics_path.read_text(encoding="utf-8"))
        if diagnostics_path.is_file()
        else {}
    )
    runtime_figure_path = REPORT / f"{diagnostics_tag}_model_runtime_quality.png"
    hybrid_runtime_figure_path = REPORT / f"{diagnostics_tag}_system_hybrid_runtime_quality.png"
    indirect_location_figure_path = REPORT / f"{diagnostics_tag}_location_indirect_validation.png"
    training_start_figure_path = REPORT / f"{diagnostics_tag}_training_start_search.png"
    final_budget_figure_path = REPORT / f"{diagnostics_tag}_final_attempt_time_budget.png"
    one_shot_timing_figure_path = REPORT / f"{diagnostics_tag}_one_shot_timing.png"
    discrete_timing_figure_path = (
        PROJECT
        / "05_ensemble/timing/validation_threshold_projection"
        / f"{diagnostics_tag}_timing_forecast_discretized.png"
    )
    runtime_payload = diagnostics.get("runtime_quality", {})
    indirect_payload = diagnostics.get("indirect_location") or {}
    hybrid_runtime_payload = diagnostics.get(
        "system_hybrid_runtime_quality", {}
    )
    training_start_payload = diagnostics.get("training_start_search") or {}
    final_budget_payload = diagnostics.get("final_attempt_time_budget") or {}
    one_shot_payload = diagnostics.get("one_shot_timing") or {}
    runtime_explanation = {
        "question": "Which promoted family balances validation quality and computational cost?",
        "reading": (
            "The left panel reports measured fit-plus-inference wall time on a "
            "log scale. The right compares false-positive-aware scientific quality "
            "with the configured 85% quality + 15% speed compromise KPI."
        ),
        "result": (
            f"The fast screen evaluated {int(runtime_payload.get('candidate_trials', 0))} "
            f"configurations across {int(runtime_payload.get('families', 0))} families. "
            "One configuration per family was promoted before the full hybrid search."
        ),
        "caution": (
            "Wall time depends on this machine and sample size. Speed breaks ties "
            "within a family; it does not replace chronological validation quality."
        ),
    }
    indirect_explanation = {
        "question": "Does the selected location approach retain discrimination on lower-magnitude events?",
        "reading": (
            "Red is the observed data-derived zone and dashed blue is the prediction. "
            f"Vertical grid lines are exact {parameters['interval_days']}-day boundaries; points and labels sit "
            "at interval centres."
        ),
        "result": (
            f"The independent diagnostic contains {int(indirect_payload.get('events', 0))} "
            f"events and {int(indirect_payload.get('exact_matches', 0))} exact zone "
            f"matches (accuracy {float(indirect_payload.get('exact_accuracy', 0.0)):.3f})."
        ),
        "caution": (
            "These lower-magnitude rows never tune zones, features, systems or fusion "
            "weights. They are an indirect continuity check, not a replacement for "
            "the primary M-threshold holdout."
        ),
    }
    hybrid_runtime_explanation = {
        "question": "How do individual systems and hybrid combinations trade validation quality against compute time?",
        "reading": (
            "The left panel shows measured member-fit cost on a logarithmic axis. "
            "The right reports robust chronological quality and the secondary "
            "85% quality + 15% speed KPI."
        ),
        "result": (
            f"The audit compares {int(hybrid_runtime_payload.get('systems', 0))} "
            f"systems across {int(hybrid_runtime_payload.get('folds', 0))} folds. "
            f"The highest compromise rank is "
            f"{str(hybrid_runtime_payload.get('top_system', {}).get('system', 'not available')).replace('_', ' ')}."
        ),
        "caution": (
            "Hybrid runtime is the measured sum of its independently trained "
            "members; shared-fit reuse can make wall-clock deployment cheaper. "
            "Speed remains a secondary criterion."
        ),
    }
    training_start_explanation = {
        "question": "Which exact historical event should begin the compact training history?",
        "reading": (
            "Each start-date group shows the best jointly searched k-event, "
            "k-between and proximity combination. Blue is mean validation "
            "quality, orange is the worst fold, and the table preserves all "
            "selected k-factors and row counts."
        ),
        "result": (
            f"The search compared {int(training_start_payload.get('start_candidates', 0))} "
            "exact event-aligned starts instead of assuming that the oldest "
            "available event is optimal."
        ),
        "caution": (
            "The selected start is validation-dependent and is therefore part "
            "of model selection, not independent evidence of predictive validity."
        ),
    }
    final_budget_explanation = {
        "question": "At the same hard wall-time cap, which final system retains the best real-peak and false-positive quality?",
        "reading": (
            "The left panel stacks measured runtime and unused budget. The right "
            "compares robust validation quality, false-peak control and the "
            "quality reached under the common cap; the table gives exact values."
        ),
        "result": (
            f"The common cap is {float(final_budget_payload.get('time_budget_seconds', 0)):.0f}s; "
            f"{int(final_budget_payload.get('finished_within_limit', 0))} of "
            f"{int(final_budget_payload.get('systems', 0))} systems completed within it."
        ),
        "caution": (
            "Runtime is machine- and sample-dependent. A system that finishes "
            "early is not artificially trained for the unused portion of the cap."
        ),
    }
    one_shot_explanation = {
        "question": "Does one real-label fit recover all held-out timing events, and what does one full-history refit forecast?",
        "reading": (
            "The upper chart scores every holdout context with one model fitted "
            "before the earliest event. The lower chart is one separate full-history "
            "forecast fit. Red stars are real M-threshold events; orange crosses "
            "are non-Japan controls."
        ),
        "result": (
            f"The one-shot diagnostic covers {int(one_shot_payload.get('validation_events', 0))} "
            f"real holdouts with quality {float(one_shot_payload.get('validation_quality', 0)):.3f}."
        ),
        "caution": (
            "The one-shot result is a complementary stability diagnostic; the "
            "primary promoted forecast remains the chronological fold-contextual fusion."
        ),
    }
    discrete_timing_explanation = {
        "question": "Which forecast bins remain peaks after applying the decision threshold learned only from real held-out events?",
        "reading": (
            "The upper chart preserves the analog score and validation-derived "
            "threshold. The lower chart applies that threshold once to produce "
            "peak/flat states; forecast values never retune the threshold."
        ),
        "result": (
            "The analog and discretized views are shown together so a near-threshold "
            "bin cannot be mistaken for either a calibrated probability or a hard certainty."
        ),
        "caution": (
            "Only the configured chronological holdouts calibrate this experimental "
            "threshold, so the resulting binary states remain sample-sensitive."
        ),
    }
    grid_offset_payload = report_grid_offset()
    grid_overlap_available = all(
        key in grid_offset_payload
        for key in (
            "reference_anchor_date",
            "reference_interval_days",
            "resolved_anchor_date",
            "offset_days_modulo_interval",
        )
    )
    page_plan = [
        {
            "title": "Reading guide and vocabulary",
            "kind": "vocabulary",
            "section": "guide",
        },
        {
            "title": "Worked formulas and examples",
            "kind": "formulas",
            "section": "guide",
        },
        *(
            [
                {
                    "title": "Temporal grid overlap",
                    "kind": "grid_overlap",
                    "section": "guide",
                }
            ]
            if grid_overlap_available
            else []
        ),
        *workflow_pages,
        {
            "title": "Model families compared",
            "kind": "methods",
            "section": "guide",
        },
        {
            "title": "Essential timing and localization result",
            "kind": "figure",
            "figure": figures[10],
            "explanation": "essential_map",
            "map_layout": True,
            "section": "result",
        },
        {
            "title": "Timing forecast",
            "kind": "figure",
            "figure": figures[3],
            "explanation": "timing_forecast",
            "section": "result",
        },
        *(
            [
                {
                    "title": "Timing forecast — validation-derived discrete threshold",
                    "kind": "figure",
                    "figure": discrete_timing_figure_path,
                    "explanation_payload": discrete_timing_explanation,
                    "section": "result",
                }
            ]
            if discrete_timing_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Conditional magnitude recalibration",
                    "kind": "figure",
                    "figure": magnitude_figure,
                    "explanation_payload": magnitude_explanation,
                    "section": "result",
                }
            ]
            if magnitude_explanation is not None
            and magnitude_figure is not None
            and magnitude_figure.is_file()
            else []
        ),
        *(
            [
                {
                    "title": (
                        "Fold-contextual timing fusion"
                        if composite.get("timing", {}).get(
                            "promoted_family"
                        )
                        == "contextual_fold_fusion"
                        else "Metric-specialist timing fusion"
                    ),
                    "kind": "composite_timing",
                    "section": "result",
                }
            ]
            if composite.get("timing", {}).get("metric_specialist")
            else []
        ),
        *(
            [
                {
                    "title": (
                        "Focused weekly revalidation after the observed event"
                    ),
                    "kind": "figure",
                    "figure": figures[13],
                    "explanation_payload": context_explanation,
                    "section": "result",
                }
            ]
            if context_explanation is not None
            else []
        ),
        {
            "title": "Incremental timing validation",
            "kind": "figure",
            "figure": figures[0],
            "explanation": "timing_validation",
            "section": "result",
        },
        *(
            [
                {
                    "title": "One-shot timing validation and forecast",
                    "kind": "figure",
                    "figure": one_shot_timing_figure_path,
                    "explanation_payload": one_shot_explanation,
                    "section": "result",
                }
            ]
            if one_shot_timing_figure_path.is_file()
            else []
        ),
        {
            "title": "One-shot localization forecast",
            "kind": "figure",
            "figure": figures[8],
            "explanation": "location_forecast",
            "section": "result",
        },
        *(
            [
                {
                    "title": "Experimental joint timing and conditional localization",
                    "kind": "composite_joint",
                    "section": "result",
                }
            ]
            if composite.get("joint_timing_location")
            else []
        ),
        {
            "title": "One-shot localization validation",
            "kind": "figure",
            "figure": figures[5],
            "explanation": "location_validation",
            "section": "result",
        },
        *(
            [
                {
                    "title": "Indirect lower-magnitude localization validation",
                    "kind": "figure",
                    "figure": indirect_location_figure_path,
                    "explanation_payload": indirect_explanation,
                    "section": "result",
                }
            ]
            if indirect_location_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Localization reliability assessment",
                    "kind": "composite_location",
                    "section": "result",
                }
            ]
            if composite.get("localization", {}).get("reliability")
            else []
        ),
        {
            "title": "Latitude and longitude implied by forecast zones",
            "kind": "figure",
            "figure": figures[12],
            "explanation": "centroid_coordinates",
            "section": "result",
        },
        {
            "title": "Technical method — construction of geographic zones",
            "kind": "figure",
            "figure": figures[4],
            "explanation": "zone_construction",
            "map_layout": True,
            "section": "technical",
        },
        {
            "title": "Technical method — false-peak isolation",
            "kind": "figure",
            "figure": figures[1],
            "explanation": "peak_isolation",
            "section": "technical",
        },
        {
            "title": "Technical method — timing training and validation quality",
            "kind": "figure",
            "figure": figures[2],
            "explanation": "timing_weights",
            "section": "technical",
        },
        *(
            [
                {
                    "title": "Exact historical training-start sensitivity",
                    "kind": "figure",
                    "figure": training_start_figure_path,
                    "explanation_payload": training_start_explanation,
                    "section": "technical",
                }
            ]
            if training_start_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Budgeted final attempts — equal-time quality",
                    "kind": "figure",
                    "figure": final_budget_figure_path,
                    "explanation_payload": final_budget_explanation,
                    "section": "technical",
                }
            ]
            if final_budget_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Model-family runtime and quality–speed compromise",
                    "kind": "figure",
                    "figure": runtime_figure_path,
                    "explanation_payload": runtime_explanation,
                    "section": "technical",
                }
            ]
            if runtime_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Full-system and hybrid runtime–quality comparison",
                    "kind": "figure",
                    "figure": hybrid_runtime_figure_path,
                    "explanation_payload": hybrid_runtime_explanation,
                    "section": "technical",
                }
            ]
            if hybrid_runtime_figure_path.is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Extended temporal-master sensitivity",
                    "kind": "extended_master_search",
                    "section": "technical",
                }
            ]
            if (
                PROJECT
                / "08_extended_search/master_screen/extended_master_search_summary.json"
            ).is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Extended feature and model-capacity search",
                    "kind": "extended_model_search",
                    "section": "technical",
                }
            ]
            if (
                PROJECT
                / "08_extended_search/timing_models/timing_model_research_ranking.csv"
            ).is_file()
            else []
        ),
        {
            "title": "Technical method — localization system comparison",
            "kind": "figure",
            "figure": figures[6],
            "explanation": "location_systems",
            "section": "technical",
        },
        {
            "title": "Technical method — localization fusion comparison",
            "kind": "figure",
            "figure": figures[7],
            "explanation": "location_fusion",
            "section": "technical",
        },
        *(
            [
                {
                    "title": (
                        (
                            "Promoted contextual validation and "
                            "order-preserving anchor"
                        )
                        if (
                            PROJECT
                            / "05_ensemble/timing/contextual_fold_fusion/"
                            "contextual_fold_fusion_summary.json"
                        ).is_file()
                        else (
                            "Chronological versus intact-record and "
                            "label-randomized timing"
                        )
                    ),
                    "kind": "historical_record_comparison",
                    "section": "control",
                }
            ]
            if (
                PROJECT
                / "07_historical_record_shuffle/timing/summary.json"
            ).is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Clean sequential versus randomized-label control",
                    "kind": "clean_baseline_comparison",
                    "section": "control",
                }
            ]
            if (PROJECT / "08_comparison/clean_baseline_audit.json").is_file()
            else []
        ),
        *(
            [
                {
                    "title": "Randomized one-shot timing control",
                    "kind": "randomized_control",
                    "domain": "timing",
                    "section": "control",
                },
                {
                    "title": "Randomized one-shot localization control",
                    "kind": "randomized_control",
                    "domain": "location",
                    "section": "control",
                },
            ]
            if workflow.get("randomized_control", {}).get("available")
            else []
        ),
        {
            "title": "Conclusions",
            "kind": "conclusion",
            "section": "conclusion",
        },
    ]
    for page_number, item in enumerate(page_plan, start=3):
        item["page"] = page_number
    contents_columns = 3 if len(page_plan) > 22 else 2
    contents_rows = int(np.ceil(len(page_plan) / contents_columns))
    contents_width = 0.88 / contents_columns
    contents_step = min(0.071, 0.66 / max(1, contents_rows - 1))
    for index, item in enumerate(page_plan):
        column = index // contents_rows
        row = index % contents_rows
        item["toc_x"] = 0.05 + column * contents_width
        item["toc_y"] = 0.82 - row * contents_step
        item["toc_width"] = contents_width - 0.025

    pdf_path = REPORT / f"{REPORT_BASENAME}.pdf"
    figure_overlays: list[dict] = []
    with PdfPages(pdf_path) as pdf:
        # Page 1 — report cover.
        fig = plt.figure(figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN))
        fig.patch.set_facecolor("#102a43")
        axis = fig.add_axes([0, 0, 1, 1])
        axis.axis("off")
        axis.add_patch(
            Rectangle(
                (0.055, 0.10),
                0.012,
                0.80,
                transform=axis.transAxes,
                facecolor="#f6ad55",
                edgecolor="none",
            )
        )
        fig.text(
            0.10,
            0.82,
            "AUTONOMOUS AGENTIC MULTI-MODEL RESEARCH PIPELINE",
            fontsize=13,
            color="#9fb3c8",
            weight="bold",
        )
        fig.text(
            0.10,
            0.68,
            f"{parameters['region_label']} earthquake timing\nand localization study",
            fontsize=29,
            color="white",
            weight="bold",
            linespacing=1.15,
        )
        fig.text(
            0.10,
            0.535,
            "LCS RULE LEARNING · KAN · PYTORCH DEEP LEARNING · HYBRIDS",
            fontsize=13.5,
            color="#f6ad55",
            weight="bold",
        )
        fig.text(
            0.10,
            0.44,
            "Solar System body-position features are screened by an automated\n"
            "pipeline that audits data, removes features cautiously, compares\n"
            "new and conventional neural methods, validates chronologically,\n"
            "fuses the models and generates an auditable report.\n\n"
            "This agentic workflow is designed to shorten model-screening and\n"
            "reporting time substantially while preserving every major decision.",
            fontsize=12.2,
            color="#d9e2ec",
            linespacing=1.28,
            va="top",
        )
        fig.text(
            0.10,
            0.20,
            f"Region: {parameters['region_label']}   ·   "
            f"window: {parameters['forecast_start']} to {parameters['forecast_end']}\n"
            f"training target: M≥{parameters['timing_magnitude_threshold']:g}   ·   "
            f"outer holdouts: M≥"
            f"{parameters.get('timing_validation_magnitude_threshold', parameters['timing_magnitude_threshold']):g}\n"
            f"location training: M≥{parameters['location_magnitude_threshold']:g}   ·   "
            f"location holdouts: M≥"
            f"{parameters.get('location_validation_magnitude_threshold', report_location_validation_magnitude_threshold()):g}"
            f"{observer_cover}",
            fontsize=11.5,
            color="white",
            linespacing=1.45,
        )
        fig.text(
            0.10,
            0.08,
            "Research diagnostic only · not an earthquake warning · "
            "scores are not calibrated probabilities",
            fontsize=10,
            color="#9fb3c8",
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2 — clickable contents.
        fig = plt.figure(
            figsize=(PAGE_WIDTH_IN, PAGE_HEIGHT_IN), facecolor="white"
        )
        fig.text(
            0.07,
            0.92,
            "Contents",
            fontsize=25,
            weight="bold",
            color="#102a43",
        )
        fig.add_artist(
            Line2D(
                [0.07, 0.93],
                [0.895, 0.895],
                transform=fig.transFigure,
                color="#cbd5e1",
                linewidth=0.9,
            )
        )
        fig.text(
            0.07,
            0.865,
            "Definitions and methods come before results; every graph page includes a plain-language reading guide.",
            fontsize=11,
            color="#52606d",
        )
        for item in page_plan:
            color = {
                "guide": "#1f4e79",
                "workflow": "#5b21b6",
                "result": "#102a43",
                "technical": "#627d98",
                "control": "#9a3412",
                "conclusion": "#166534",
            }[item["section"]]
            x = item["toc_x"]
            y = item["toc_y"]
            fig.text(
                x,
                y,
                textwrap.fill(
                    item["title"],
                    30 if contents_columns == 3 else 43,
                ),
                fontsize=7.4 if contents_columns == 3 else 8.4,
                color=color,
                va="top",
                linespacing=1.05,
            )
            fig.text(
                x + item["toc_width"],
                y,
                str(item["page"]),
                fontsize=8.0 if contents_columns == 3 else 8.8,
                color=color,
                ha="right",
                va="top",
            )
            fig.add_artist(
                Line2D(
                    [x, x + item["toc_width"]],
                    [y - 0.047, y - 0.047],
                    transform=fig.transFigure,
                    color="#d9e2ec",
                    linewidth=0.8,
                )
            )
        fig.text(
            0.07,
            0.065,
            "Time notation used everywhere: [start, end) means start included and end excluded. "
            "Click any contents row to open that page.",
            fontsize=9.5,
            color="#334e68",
        )
        pdf.savefig(fig)
        plt.close(fig)

        for item in page_plan:
            if item["kind"] == "vocabulary":
                render_vocabulary_page(pdf, narrative, item["page"])
            elif item["kind"] == "formulas":
                render_formula_page(pdf, narrative, item["page"])
            elif item["kind"] == "grid_overlap":
                render_grid_overlap_page(
                    pdf,
                    parameters,
                    grid_offset_payload,
                    item["page"],
                )
            elif item["kind"] == "workflow_overview":
                render_workflow_overview_page(pdf, workflow, item["page"])
            elif item["kind"] == "workflow_phase":
                render_workflow_phase_page(
                    pdf, item["stage"], item["page"]
                )
            elif item["kind"] == "feature_evidence":
                render_feature_evidence_page(
                    pdf, workflow, item["domain"], item["page"]
                )
            elif item["kind"] == "body_summary":
                render_body_summary_page(pdf, workflow, item["page"])
            elif item["kind"] == "model_ranking_evidence":
                render_model_ranking_evidence_page(
                    pdf,
                    workflow,
                    item["domain"],
                    item["page"],
                )
            elif item["kind"] == "model_parameters":
                render_model_parameter_page(
                    pdf,
                    workflow,
                    item["domain"],
                    item["components"],
                    item["page"],
                )
            elif item["kind"] == "methods":
                render_methods_page(pdf, narrative, item["page"])
            elif item["kind"] == "figure":
                explanation = item.get("explanation_payload")
                if explanation is None:
                    explanation = narrative["figures"][
                        item["explanation"]
                    ]
                render_figure_page(
                    pdf,
                    item["figure"],
                    item["title"],
                    explanation,
                    item["page"],
                    map_layout=item.get("map_layout", False),
                    figure_overlays=figure_overlays,
                )
            elif item["kind"] == "conclusion":
                render_conclusion_page(pdf, narrative, item["page"])
            elif item["kind"] == "randomized_control":
                render_randomized_control_page(
                    pdf, workflow, item["domain"], item["page"]
                )
            elif item["kind"] == "historical_record_comparison":
                render_historical_record_comparison_page(
                    pdf, item["page"]
                )
            elif item["kind"] == "clean_baseline_comparison":
                render_clean_baseline_comparison_page(pdf, item["page"])
            elif item["kind"] == "composite_timing":
                render_composite_timing_page(pdf, item["page"])
            elif item["kind"] == "composite_location":
                render_composite_location_page(pdf, item["page"])
            elif item["kind"] == "composite_joint":
                render_composite_joint_page(pdf, item["page"])
            elif item["kind"] == "extended_master_search":
                render_extended_master_search_page(pdf, item["page"])
            elif item["kind"] == "extended_model_search":
                render_extended_model_search_page(pdf, item["page"])

    reader = PdfReader(pdf_path)
    overlays_by_page = {
        int(overlay["page_index"]): overlay for overlay in figure_overlays
    }
    writer = PdfWriter()
    # Rebuild every page onto a fresh blank page so image XObjects stay local
    # to the target page (append_pages_from_reader can share Resources).
    for page_index, source_page in enumerate(reader.pages):
        width = float(source_page.mediabox.width)
        height = float(source_page.mediabox.height)
        page = writer.add_blank_page(width=width, height=height)
        page.merge_page(source_page)
        overlay = overlays_by_page.get(page_index)
        if overlay is None:
            continue
        image_path = Path(overlay["image_path"])
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        embed_png_on_page(page, image_path, tuple(overlay["box"]))
    writer.add_outline_item("Cover", 0)
    writer.add_outline_item("Contents", 1)
    contents_page = writer.pages[1]
    page_width = float(contents_page.mediabox.width)
    page_height = float(contents_page.mediabox.height)
    for item in page_plan:
        x = item["toc_x"]
        y = item["toc_y"]
        writer.add_outline_item(item["title"], item["page"] - 1)
        writer.add_annotation(
            page_number=1,
            annotation=Link(
                rect=(
                    x * page_width,
                    (y - 0.05) * page_height,
                    (x + item["toc_width"]) * page_width,
                    (y + 0.01) * page_height,
                ),
                target_page_index=item["page"] - 1,
            ),
        )
    linked_path = pdf_path.with_name(f"{REPORT_BASENAME}_linked.pdf")
    with linked_path.open("wb") as stream:
        writer.write(stream)
    os.replace(linked_path, pdf_path)
    return pdf_path


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(
        (PROJECT / "00_config/run_manifest.json").read_text()
    )
    parameters = manifest["parameters"]
    workflow = build_workflow()
    write_json(PROJECT / "00_config/report_workflow.json", workflow)
    narrative = build_narrative()
    requested_final_statement = (
        report_composite().get("report_overrides", {}).get("final_statement")
    )
    if requested_final_statement:
        narrative["conclusion"]["final_statement"] = str(
            requested_final_statement
        )
    composite_location = report_composite().get("localization", {})
    location_reliability = composite_location.get("reliability", {})
    if int(location_reliability.get("distinct_validation_zones", 0)) == 1:
        primary_confidence = location_reliability["true_zone_confidence"][
            "primary_soft_fusion"
        ]
        prior_confidence = location_reliability["true_zone_confidence"][
            "training_prior_baseline"
        ]
        random_confidence = location_reliability["true_zone_confidence"][
            "randomized_label_control"
        ]
        narrative["figures"]["location_validation"]["result"] = (
            f"All {int(location_reliability['validation_events'])} held-out "
            f"events are assigned to their observed Zone "
            f"{int(location_reliability['majority_zone'])}, but exact accuracy "
            "is non-discriminating because every holdout belongs to that same "
            f"zone. Mean true-zone confidence is {primary_confidence:.3f}, "
            f"compared with {prior_confidence:.3f} for the training-zone prior "
            f"and {random_confidence:.3f} for randomized labels."
        )
        narrative["figures"]["location_validation"]["caution"] = (
            f"Localization reliability is capped at "
            f"{float(location_reliability['applied_reliability_weight']):.0%}: "
            f"{location_reliability['reason_for_cap']}."
        )
    fingerprint_path = (
        PROJECT / "02_master_search/timing_fingerprint_formula.json"
    )
    selection_path = (
        PROJECT / "02_master_search/master_search_selection.json"
    )
    if fingerprint_path.is_file() and selection_path.is_file():
        fingerprint = json.loads(fingerprint_path.read_text())
        selection_payload = json.loads(selection_path.read_text())
        selected_fingerprint = selection_payload["selected"]
        threshold = float(parameters["timing_magnitude_threshold"])
        validation_threshold = float(
            parameters.get("timing_validation_magnitude_threshold", threshold)
        )
        validation_slots_text = str(
            parameters.get("outer_validation_slots", "configured outer slots")
        ).replace(",", ", ")
        interval_days = int(selection_payload["grid"]["interval_days"])
        gate = fingerprint["strict_gate"]
        narrative["formula_examples"][4] = {
            "title": (
                f"M{threshold:g}+ timing fingerprint and strict candidate gate"
            ),
            "formula": (
                f"y_t=1 iff M>={threshold:g} occurs in the "
                f"{interval_days}-day bin starting at t; "
                f"explicit outer holdouts may use M>={validation_threshold:g}; "
                "F=0.30R+0.25A+0.20P+0.15D+0.10C; "
                "S=0.35Qmean+0.25Qworst+0.20Fmean+0.10Fworst"
                "+0.10 clip(0.5+(Qseq-Qrnd)/2,0,1)"
            ),
            "symbols": (
                "R=event percentile, A=near-peak alignment, P=local "
                "prominence, D=delayed-false-peak control, C=false-peak "
                "control. Training retains k_event complete records around "
                f"each M{threshold:g}+ event and k_between intact random "
                "records between successive events."
            ),
            "worked_example": (
                f"Selected fingerprint: start={selected_fingerprint['history_start_year']}, "
                f"validation radius={selected_fingerprint['validation_radius']} bins, "
                f"k_event={selected_fingerprint['history_event_radius']} per side, "
                f"k_between={selected_fingerprint['history_between_records']}; "
                f"gate requires |argmax offset|<={gate['maximum_argmax_offset_slots']}, "
                f"event rank>={gate['minimum_event_percentile_skill']:.2f}, "
                f"mean/worst quality>={gate['minimum_validation_quality_mean']:.2f}/"
                f"{gate['minimum_validation_quality_worst']:.2f}, competing "
                "false peaks<="
                f"{gate['maximum_competing_false_peak_count']} within "
                f"{gate['false_peak_competitor_margin']:.3f} of the event "
                "score, and sequential-random gap>="
                f"{gate['minimum_sequential_minus_random']:.2f}. The outer slots "
                f"{validation_slots_text} screened these choices, so they are "
                "selection-validation targets rather than untouched external tests."
            ),
        }
    executed_fingerprint_path = (
        PROJECT / "02_audit/executed_timing_fingerprint.json"
    )
    if executed_fingerprint_path.is_file():
        executed = json.loads(executed_fingerprint_path.read_text())
        anchor = executed["screening_anchor"]
        intervention = executed.get("agent_method_intervention")
        fusion = executed["timing_fusion"]
        isolation = executed["false_peak_isolation"]
        anchor_weight = float(
            fusion["weights"].get("screening_anchor", 0.0)
        )
        narrative["formula_examples"][0] = {
            "title": "Chronologically refitted screening anchor",
            "formula": anchor["formula"],
            "symbols": (
                "p_logistic and p_extra_trees are fitted only on the eligible "
                "training sample. ECDF_train converts each model separately "
                "to an empirical rank before their mean is taken."
            ),
            "worked_example": (
                f"Logistic C={anchor['logistic_C']:.2f}; "
                f"{anchor['extra_trees_estimators']} trees, max depth "
                f"{anchor['extra_trees_max_depth']}, min leaf "
                f"{anchor['extra_trees_min_samples_leaf']}. Seed base "
                f"{anchor['seed_base']}; fold seed adds 101 × fold index."
            ),
        }
        narrative["formula_examples"][1] = {
            "title": "Selected fusion and false-peak isolation",
            "formula": (
                f"E_t=Σ_s w_s score_s(t); anchor weight={anchor_weight:.3f}. "
                + isolation["formula"]
            ),
            "symbols": (
                "Weights are non-negative and sum to one. Isolation changes "
                "only outer members of a validation-approved symmetric "
                "three-peak pattern; median(E) is the fold background."
            ),
            "worked_example": (
                f"This run selected lag={isolation['lag_slots']} bins and "
                f"strength={isolation['strength']:.2f}; isolation objective "
                f"{isolation['objective_before']:.3f} → "
                f"{isolation['objective_after']:.3f}. All exact weights are "
                "stored in 02_audit/executed_timing_fingerprint.json."
            ),
        }
        if intervention:
            narrative["figures"]["timing_forecast"]["caution"] = (
                "Agent-method note: the AI agent introduced Logistic + "
                "ExtraTrees rank mean after the original LCS, KAN and Deep "
                "candidates failed to make both selection-validation events "
                "global maxima. It was not an automatic fallback: it entered "
                "as a permanent candidate. Its "
                f"{intervention['selected_weight']:.3f} weight was selected "
                "parametrically; forecast dates were not in that objective."
            )
    if FORECAST_OVERLAY_CSV:
        overlay_forecast = pd.read_csv(
            PROJECT / "05_ensemble/timing/forecast_predictions.csv"
        )
        _, overlay_formula_audit = forecast_overlay_frame(overlay_forecast)
        narrative["formula_examples"][3] = {
            "title": "Optional external forecast-point projection",
            "formula": overlay_formula_audit["formula"],
            "symbols": (
                "External dates are assigned to [bin_start, bin_start+7 days). "
                "Identity is used only when every external value is already "
                "inside [0,1]; otherwise min and max come only from the "
                "supplied CSV."
            ),
            "worked_example": (
                f"This run uses {overlay_formula_audit['projection_mode']} "
                f"with margin={overlay_formula_audit['visual_margin']:.2f}; "
                f"raw range {overlay_formula_audit['raw_min']:.3f}–"
                f"{overlay_formula_audit['raw_max']:.3f} maps to "
                f"{overlay_formula_audit['projected_min']:.3f}–"
                f"{overlay_formula_audit['projected_max']:.3f}."
            ),
        }
    isolation_for_narrative = json.loads(
        (
            PROJECT / "05_ensemble/timing/peak_isolation_gate.json"
        ).read_text()
    )
    if isolation_for_narrative["status"] == "NO_ALIAS_PENALTY":
        baseline = isolation_for_narrative["baseline_without_alias"]
        selected = isolation_for_narrative["selected"]
        search = isolation_for_narrative["search"]
        false_before = sum(
            int(profile.get("false_peak_count", 0))
            for profile in baseline["profiles"]
        )
        false_after = sum(
            int(profile.get("false_peak_count", 0))
            for profile in selected["profiles"]
        )
        narrative["figures"]["peak_isolation"]["result"] = (
            "Combined isolation skill changes from "
            f"{baseline['total_objective_higher_is_better']:.3f} to "
            f"{selected['total_objective_higher_is_better']:.3f}; credible "
            f"false peaks change from {false_before} to {false_after}. The "
            f"search enumerated {int(search['alias_candidates']):,} candidates; "
            f"{int(search.get('effective_alias_candidates', 0)):,} were "
            "structurally applicable. The baseline already had exact held-out "
            "peaks and zero false peaks, and no suppression produced the "
            f"required +{float(search['minimum_isolation_gain']):.3f} gain "
            "while preserving validation, so the unsuppressed baseline was "
            "retained."
        )
    write_json(PROJECT / "00_config/report_narrative.json", narrative)
    for obsolete in [
        *REPORT.glob("*_v7.png"),
        REPORT / "V7_REPORT.md",
        REPORT / "V7_REPORT.pdf",
        REPORT / "self_check_v7.json",
    ]:
        if obsolete.exists():
            obsolete.unlink()
    timing_summary = json.loads(
        (PROJECT / "05_ensemble/timing/final_summary.json").read_text()
    )
    location_summary = json.loads(
        (PROJECT / "05_ensemble/location_zone_summary.json").read_text()
    )
    isolation_audit = json.loads(
        (PROJECT / "05_ensemble/timing/peak_isolation_gate.json").read_text()
    )
    figures = [
        REPORT / f"timing_incremental_validation_{REPORT_FILE_TAG}.png",
        REPORT / f"timing_peak_isolation_gate_{REPORT_FILE_TAG}.png",
        REPORT / f"timing_system_weights_{REPORT_FILE_TAG}.png",
        REPORT / f"timing_forecast_{REPORT_FILE_TAG}.png",
        REPORT / f"location_numbered_zones_{REPORT_FILE_TAG}.png",
        REPORT / f"location_one_shot_validation_{REPORT_FILE_TAG}.png",
        REPORT / f"location_system_ranking_{REPORT_FILE_TAG}.png",
        REPORT / f"location_fusion_ranking_{REPORT_FILE_TAG}.png",
        REPORT / f"location_one_shot_forecast_{REPORT_FILE_TAG}.png",
        REPORT / f"removed_page_{REPORT_FILE_TAG}.png",
        REPORT / f"final_timing_location_map_{REPORT_FILE_TAG}.png",
        REPORT / f"removed_zone_score_diagnostic_{REPORT_FILE_TAG}.png",
        REPORT
        / f"location_centroid_coordinate_interpretation_{REPORT_FILE_TAG}.png",
        REPORT / f"forecast_event_context_{REPORT_FILE_TAG}.png",
    ]
    timing_validation_figure(figures[0])
    for stale in REPORT.glob("timing_validation_event_*.png"):
        stale.unlink()
    timing_event_figures: list[Path] = []
    timing_penalty_figure(figures[1])
    timing_ranking_figure(figures[2])
    timing_forecast_figure(figures[3])
    context_path = (
        PROJECT / "05_ensemble/timing/forecast_event_context.json"
    )
    if INCLUDE_OBSERVED_EVENT_CONTEXT and context_path.is_file():
        forecast_event_context_figure(figures[13])
    elif figures[13].exists():
        figures[13].unlink()
    location_zone_map(figures[4], location_summary)
    location_validation_figure(figures[5])
    location_ranking_figure(figures[6])
    fusion_ranking_figure(figures[7])
    location_forecast_figure(figures[8])
    for obsolete in (figures[9], figures[11]):
        if obsolete.exists():
            obsolete.unlink()
    final_zone_map(figures[10], location_summary)
    centroid_coordinate_figure(figures[12])
    markdown = build_markdown(
        figures, timing_event_figures, timing_summary, location_summary
    )
    pdf = build_pdf(
        figures, timing_event_figures, timing_summary, location_summary
    )

    timing_forecast = pd.read_csv(
        PROJECT / "05_ensemble/timing/forecast_predictions.csv"
    )
    location_forecast = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_forecast.csv"
    )
    timing_dates = pd.to_datetime(timing_forecast["date"])
    location_dates = pd.to_datetime(location_forecast["date"])
    zone_frame = pd.DataFrame(location_summary["zones"]).sort_values("zone")
    zone_grid = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_decision_grid.csv"
    )
    zone_events = pd.read_csv(
        PROJECT / "05_ensemble/location_zone_event_catalog.csv"
    )
    grid_resolution = float(
        location_summary["zone_decision_grid"]["resolution_degrees"]
    )
    grid_latitude_min = float(zone_grid["latitude"].min())
    grid_longitude_min = float(zone_grid["longitude"].min())
    grid_lookup = {
        (round(float(row.latitude), 6), round(float(row.longitude), 6)): int(
            row.zone
        )
        for row in zone_grid.itertuples()
    }
    event_grid_zones = []
    for row in zone_events.itertuples():
        latitude = (
            round((float(row.latitude) - grid_latitude_min) / grid_resolution)
            * grid_resolution
            + grid_latitude_min
        )
        longitude = (
            round((float(row.longitude) - grid_longitude_min) / grid_resolution)
            * grid_resolution
            + grid_longitude_min
        )
        event_grid_zones.append(
            grid_lookup[(round(latitude, 6), round(longitude, 6))]
        )
    latitude_bands_are_contiguous = bool(
        np.allclose(
            zone_frame["latitude_high"].to_numpy(float)[:-1],
            zone_frame["latitude_low"].to_numpy(float)[1:],
        )
    )
    pdf_reader = PdfReader(pdf)
    pdf_text = "\n".join(
        page.extract_text() or "" for page in pdf_reader.pages
    )
    normalized_pdf_text = re.sub(r"\s+", " ", pdf_text).lower()
    astro_audit_path = PROJECT / "00_config/astro_source_audit.json"
    astro_audit = (
        json.loads(astro_audit_path.read_text())
        if astro_audit_path.is_file()
        else {}
    )
    observer = astro_audit.get("required_contract", {}).get("observer", {})
    location_master_audit_path = (
        PROJECT / "02_audit/monthly_location_master_audit.json"
    )
    location_master_audit = (
        json.loads(location_master_audit_path.read_text())
        if location_master_audit_path.is_file()
        else {}
    )
    peak_mode_audit_path = (
        PROJECT / "05_ensemble/timing/forecast_peak_modes.json"
    )
    peak_mode_audit = (
        json.loads(peak_mode_audit_path.read_text())
        if peak_mode_audit_path.is_file()
        else {}
    )
    peak_mode_frame = forecast_peak_mode_frame()
    diagnostic_peak_frame = diagnostic_peak_mode_frame()
    history_comparison_audit = json.loads(
        (REPORT / "forecast_history_comparison_audit.json").read_text()
    )
    alias_trial_path = (
        PROJECT / "05_ensemble/timing/alias_gate_trials.csv"
    )
    audited_minor_names = set(
        astro_audit.get("required_contract", {})
        .get("minor_bodies", {})
        .values()
    )
    timing_body_names = {
        item["body_name"]
        for item in workflow["feature_evidence"]["timing"][
            "celestial_bodies"
        ]
    }
    location_body_names = {
        item["body_name"]
        for item in workflow["feature_evidence"]["localization"][
            "celestial_bodies"
        ]
    }
    pdf_annotation_count = 0
    for page in pdf_reader.pages:
        annotations = page.get("/Annots")
        if annotations is not None:
            pdf_annotation_count += len(annotations.get_object())
    checks = {
        "timing_master_is_readable": (PROJECT / "01_inputs/timing_master.csv").stat().st_size > 0,
        "location_master_is_readable": (PROJECT / "01_inputs/location_master.csv").stat().st_size > 0,
        "training_cutoff_before_visible_window": pd.Timestamp(
            timing_summary["forecast"]["training_cutoff"]
        )
        < pd.Timestamp(timing_summary["forecast"]["visible_start"]),
        "configured_interval_timing_grid_is_consistent": bool(
            infer_time_scale(timing_dates).to_dict()
            == report_time_scale().to_dict()
        ),
        "configured_interval_location_grid_is_consistent": bool(
            infer_time_scale(location_dates).to_dict()
            == report_time_scale().to_dict()
        ),
        "forecast_slot_starts_are_inside_configured_window": bool(
            timing_dates.min()
            >= pd.Timestamp(parameters["forecast_grid_start"])
            and timing_dates.max()
            <= pd.Timestamp(parameters["forecast_end"])
            and location_dates.min()
            >= pd.Timestamp(parameters["forecast_grid_start"])
            and location_dates.max()
            <= pd.Timestamp(parameters["forecast_end"])
        ),
        "peak_isolation_gate_declared": timing_summary["peak_isolation"]["status"]
        in {
            "NO_APPLICABLE_ALIAS_PATTERN",
            "NO_ALIAS_PENALTY",
            "NO_ALIAS_PENALTY_NO_EXACT_WEEKLY_BASELINE",
            "ALIAS_PENALTY_ACCEPTED",
        },
        "peak_isolation_objective_improves": (
            isolation_audit["selected"]["total_objective_higher_is_better"]
            >= isolation_audit["baseline_without_alias"][
                "total_objective_higher_is_better"
            ]
        ),
        "false_peak_search_was_executed_and_decision_is_explicit": (
            alias_trial_path.is_file()
            and len(pd.read_csv(alias_trial_path)) > 0
            and int(isolation_audit["search"]["alias_candidates"]) > 0
            and (
                (
                    isolation_audit["status"]
                    in {
                        "NO_APPLICABLE_ALIAS_PATTERN",
                        "NO_ALIAS_PENALTY",
                        "NO_ALIAS_PENALTY_NO_EXACT_WEEKLY_BASELINE",
                    }
                    and int(
                        isolation_audit["selected"]["alias_lag_slots"]
                    )
                    == 0
                    and float(
                        isolation_audit["selected"]["alias_strength"]
                    )
                    == 0.0
                    and "unsuppressed baseline was retained"
                    in normalized_pdf_text
                )
                or (
                    isolation_audit["status"]
                    == "ALIAS_PENALTY_ACCEPTED"
                    and float(
                        isolation_audit["selected"]["alias_strength"]
                    )
                    > 0.0
                )
            )
        ),
        "credible_false_peaks_do_not_increase": (
            sum(
                row["false_peak_count"]
                for row in isolation_audit["selected"]["profiles"]
            )
            <= sum(
                row["false_peak_count"]
                for row in isolation_audit["baseline_without_alias"]["profiles"]
            )
        ),
        "every_timing_system_retains_positive_weight": all(
            weight > 0
            for weight in isolation_audit["selected"]["system_weights"].values()
        ),
        "location_validation_is_one_shot": (
            location_summary["validation_design"]["mode"] == "one_shot"
            and not location_summary["validation_design"]["incremental"]
        ),
        "location_master_was_rebuilt_from_the_v12_timing_master": (
            location_master_audit.get("status") == "COMPLETE"
            and location_master_audit.get("timing_master", {}).get("sha256")
            == sha256(PROJECT / "01_inputs/timing_master.csv")
            and location_master_audit.get("output", {}).get("sha256")
            == sha256(PROJECT / "01_inputs/location_master.csv")
            and int(
                location_master_audit.get("output", {}).get(
                    "historical_event_rows",
                    0,
                )
            )
            > 0
            and int(
                location_master_audit.get("output", {}).get(
                    "forecast_rows",
                    0,
                )
            )
            == len(location_forecast)
        ),
        "diagnostic_peak_modes_and_primary_selection_are_audited": (
            peak_mode_audit.get("status") == "COMPLETE"
            and len(diagnostic_peak_frame) == 4
            and set(diagnostic_peak_frame["source_mode"])
            == {
                "chronological_incremental",
                "historical_record_shuffle",
            }
            and set(diagnostic_peak_frame["selection_mode"])
            == {"first_significant_peak", "maximum_peak"}
            and len(peak_mode_frame) == 1
            and set(peak_mode_frame["selection_mode"]).issubset(
                {"first_occurrence", "absolute_peak"}
            )
            and peak_mode_frame["predicted_zone"].notna().all()
            and selection_mode_label(
                str(peak_mode_frame.iloc[0]["selection_mode"])
            )
            in normalized_pdf_text
        ),
        "historical_order_comparison_obeys_validation_gate": (
            history_comparison_audit["mode"]
            == FORECAST_HISTORY_COMPARISON
            and (
                (
                    FORECAST_HISTORY_COMPARISON == "hide"
                    and history_comparison_audit["status"] == "EXCLUDED"
                )
                or (
                    FORECAST_HISTORY_COMPARISON == "show"
                    and history_comparison_audit["status"] == "INCLUDED"
                )
                or (
                    FORECAST_HISTORY_COMPARISON == "auto"
                    and (
                        history_comparison_audit["status"] == "INCLUDED"
                    )
                    == bool(
                        history_comparison_audit["automatic_gate_pass"]
                    )
                )
            )
            and "not the randomized-label null test"
            in history_comparison_audit["semantics"]
        ),
        "configured_outer_timing_peak_outcome_is_disclosed": bool(
            int(
                pd.read_csv(PROJECT / "05_ensemble/timing/validation_gate.csv")[
                    "strict_local_peak"
                ].sum()
            )
            == len(timing_summary["outer_validation_events"])
            or (
                timing_summary.get("validation_gate")
                == "FAIL_REPORTED_NOT_TUNED"
                and "strict local maxima" in normalized_pdf_text
            )
        ),
        "single_combined_timing_validation_figure": figures[0].exists()
        and not timing_event_figures
        and not any(REPORT.glob("timing_validation_event_*.png")),
        "joint_location_zones_include_central_band": location_summary["zone_count"]
        >= 3,
        "summary_envelope_latitude_bands_are_contiguous": latitude_bands_are_contiguous,
        "complete_gmm_map_coverage": bool(
            zone_grid["zone"].notna().all()
            and set(zone_grid["zone"].astype(int))
            == set(range(1, location_summary["zone_count"] + 1))
        ),
        "every_catalog_event_has_a_valid_zone": bool(
            zone_events["zone"].notna().all()
            and zone_events["zone"].astype(int).between(
                1, location_summary["zone_count"]
            ).all()
        ),
        "every_event_matches_its_displayed_gmm_territory": bool(
            np.array_equal(
                zone_events["zone"].to_numpy(int),
                np.asarray(event_grid_zones, int),
            )
        ),
        "zone_catalog_contains_construction_events": (
            location_summary["zone_catalog"][
                "rows_after_filter_and_slot_deduplication"
            ]
            > 0
        ),
        "configured_location_holdout_count_is_supported": (
            2 <= len(location_summary["validation_events"]) <= 5
            and len(location_summary["validation_events"])
            == int(location_summary["run_parameters"]["validation_events"])
        ),
        "all_figures_exist": all(
            path.exists() and path.stat().st_size > 1000
            for path in [
                *[
                    path
                    for index, path in enumerate(figures)
                    if index not in (
                        {9, 11}
                        | ({13} if not INCLUDE_OBSERVED_EVENT_CONTEXT else set())
                    )
                ],
                *timing_event_figures,
            ]
        ),
        "reports_exist": markdown.exists() and pdf.exists(),
        "parameter_driven_report_narrative_exists": (
            (PROJECT / "00_config/report_narrative.json").exists()
            and (PROJECT / "00_config/report_workflow.json").exists()
            and len(narrative["formula_examples"]) >= 5
            and workflow["stage_count"] == 5
            and workflow["schema_version"] == "1.1"
            and len(
                workflow["feature_evidence"]["timing"]["top_features"]
            )
            > 0
            and len(
                workflow["feature_evidence"]["localization"]["top_features"]
            )
            > 0
            and len(
                workflow["model_evidence"]["timing"]["top_systems"]
            )
            == 3
            and len(
                workflow["model_evidence"]["localization"]["top_systems"]
            )
            == 3
            and len(narrative["vocabulary"]) >= 10
            and set(narrative["figures"])
            == {
                "essential_map",
                "timing_forecast",
                "timing_validation",
                "location_forecast",
                "location_validation",
                "zone_construction",
                "peak_isolation",
                "timing_weights",
                "location_systems",
                "location_fusion",
                "centroid_coordinates",
            }
        ),
        "celestial_body_tables_are_populated": bool(
            timing_body_names and location_body_names
        ),
        "audited_minor_bodies_are_present_in_both_complete_rankings": (
            not audited_minor_names
            or (
                audited_minor_names.issubset(timing_body_names)
                and audited_minor_names.issubset(location_body_names)
            )
        ),
        "parameterized_observer_is_reported": (
            not observer
            or (
                str(observer.get("label", "")).lower()
                in normalized_pdf_text
                and f"{float(observer['latitude']):g}° n"
                in normalized_pdf_text
                and f"{float(observer['longitude']):g}° e"
                in normalized_pdf_text
            )
        ),
        "workflow_formulas_and_time_scale_are_explained": (
            "worked formulas behind the vocabulary" in pdf_text.lower()
            and "reproducible workflow" in pdf_text.lower()
            and "top 20 celestial fields" in pdf_text.lower()
            and "executed component parameters" in pdf_text.lower()
            and "nasa/jpl horizons target identifiers" in pdf_text.lower()
            and "randomized one-shot timing control" in pdf_text.lower()
            and "randomized one-shot localization control" in pdf_text.lower()
            and report_time_scale().display_singular.lower()
            in pdf_text.lower()
        ),
        "complete_standard_localization_section_is_rendered": all(
            title in normalized_pdf_text
            for title in (
                "one-shot localization forecast",
                "one-shot localization validation",
                "latitude and longitude implied by forecast zones",
                "technical method construction of geographic zones",
                "technical method localization system comparison",
                "technical method localization fusion comparison",
                "randomized one-shot localization control",
            )
        ),
        "historical_record_line_comparison_is_rendered": (
            (
                (
                    "contextual incremental timing validation"
                    in normalized_pdf_text
                    and "promoted contextual fusion" in normalized_pdf_text
                    and "order-preserving row shuffle" in normalized_pdf_text
                )
                if (
                    PROJECT
                    / "05_ensemble/timing/contextual_fold_fusion/"
                    "contextual_fold_fusion_summary.json"
                ).is_file()
                else (
                    "timing provenance promoted forecast and randomized controls"
                    in normalized_pdf_text
                    and "row-order shuffle" in normalized_pdf_text
                    and "target-label shuffle" in normalized_pdf_text
                    and "promoted global fusion" in normalized_pdf_text
                )
            )
            if REQUIRE_HISTORICAL_RECORD_SHUFFLE
            else True
        ),
        "record_shuffle_ensemble_gate_is_not_a_report_page": (
            "record-shuffle ensemble gate" not in pdf_text.lower()
            and "historical-record ensemble gate" not in pdf_text.lower()
        ),
        "parameterized_comparisons_use_lines": (
            COMPARISON_STYLE == "line"
            and (
                (
                    "contextual incremental timing validation"
                    in normalized_pdf_text
                )
                if (
                    PROJECT
                    / "05_ensemble/timing/contextual_fold_fusion/"
                    "contextual_fold_fusion_summary.json"
                ).is_file()
                else (
                    "timing provenance promoted forecast and randomized controls"
                    in normalized_pdf_text
                )
                if REQUIRE_HISTORICAL_RECORD_SHUFFLE
                else True
            )
        ),
        "internal_fusion_tokens_do_not_leak_to_report": not any(
            token in pdf_text
            for token in (
                "prior_correct",
                "best_single",
                "top3_soft_probability",
            )
        ),
        "scientific_question_is_left_open_but_not_claimed": (
            requested_final_statement in pdf_text
            if requested_final_statement
            else (
                "insufficient to establish definitively" in pdf_text
                and "Further independent" in pdf_text
                and "prospective and larger-sample" in pdf_text
            )
        ),
        "optional_composite_json_sections_are_rendered": (
            all(
                phrase in normalized_pdf_text
                for phrase in (
                    (
                        "fold-contextual timing fusion"
                        if report_composite().get("timing", {}).get(
                            "promoted_family"
                        )
                        == "contextual_fold_fusion"
                        else "metric-specialist timing fusion"
                    ),
                    "localization reliability assessment",
                    "experimental joint timing and conditional localization",
                )
            )
            if report_composite()
            else True
        ),
        "contents_links_cover_every_report_section": (
            pdf_annotation_count == len(pdf_reader.pages) - 2
        ),
        "professional_report_has_guide_workflow_and_conclusion": (
            len(pdf_reader.pages) >= REPORT_MINIMUM_PAGES
            and pdf_text.count("Workflow phase") >= workflow["stage_count"]
            and "Conclusions" in pdf_text
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    write_json(
        REPORT / f"self_check_{REPORT_FILE_TAG}.json",
        {
            "status": status,
            "checks": checks,
            "report_language": "English",
            "time_slot_convention": "[slot start, next slot start)",
            "time_scale": report_time_scale().to_dict(),
            "raster_dpi": REPORT_DPI,
            "comparison_style": COMPARISON_STYLE,
            "minimum_pages": REPORT_MINIMUM_PAGES,
            "report_version": REPORT_VERSION,
            "report_basename": REPORT_BASENAME,
            "pdf_annotations": pdf_annotation_count,
            "figures": [
                str(path)
                for path in [
                    *[
                        path
                        for index, path in enumerate(figures)
                        if index not in {9, 11}
                    ],
                    *timing_event_figures,
                ]
            ],
            "markdown": str(markdown),
            "pdf": str(pdf),
            "narrative_json": str(
                PROJECT / "00_config/report_narrative.json"
            ),
            "workflow_json": str(
                PROJECT / "00_config/report_workflow.json"
            ),
        },
    )
    print(f"English {REPORT_VERSION} report: {markdown}")
    print(f"English {REPORT_VERSION} PDF: {pdf}")
    print(f"Self-check: {status}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render a parameterized English timing report, figures, and PDF.

Run-specific presentation values are supplied through CLI arguments or
resolved from the persisted run manifest. Every chart is emitted as both a
high-resolution PNG and a vector SVG.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/japan-180d-deephistory-v14")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


COLORS = {
    "blue": "#2f6f9f",
    "orange": "#d97706",
    "green": "#2f855a",
    "red": "#c53030",
    "gray": "#6b7280",
    "light": "#e5e7eb",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def save_figure(fig: plt.Figure, path: Path, raster_dpi: int) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=raster_dpi, bbox_inches="tight")
    fig.savefig(path.with_suffix(".svg"), format="svg", bbox_inches="tight")
    plt.close(fig)


def validation_figure(
    run_dir: Path,
    fusion: dict[str, Any],
    output: Path,
    *,
    interval_days: int,
    region_label: str,
    raster_dpi: int,
) -> None:
    weights = fusion["selected_trial"]["system_weights"]
    standard = pd.read_csv(
        run_dir / "05_ensemble/timing/validation_predictions.csv"
    )
    steps = sorted(
        path
        for path in (run_dir / "04_models/timing").iterdir()
        if path.is_dir() and path.name[:2] in {"01", "02"}
    )
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for axis, step in zip(axes, steps):
        rows = {
            system: pd.read_csv(step / system / "validation_predictions.csv")
            for system in weights
        }
        reference = next(iter(rows.values()))
        metric_score = sum(
            weight
            * rows[system]["score_percentile_not_probability"].to_numpy(float)
            for system, weight in weights.items()
        )
        standard_rows = standard.loc[standard["step"].eq(step.name)]
        standard_score = standard_rows[
            "score_percentile_not_probability"
        ].to_numpy(float)
        actual_position = int(np.flatnonzero(reference["actual"].to_numpy(int))[0])
        offsets = np.arange(len(reference)) - actual_position
        axis.plot(
            offsets,
            metric_score,
            marker="o",
            linewidth=2.5,
            color=COLORS["blue"],
            label="metric-specialist fusion",
        )
        axis.plot(
            offsets,
            standard_score,
            marker="s",
            linewidth=1.7,
            color=COLORS["orange"],
            alpha=0.85,
            label="standard ensemble",
        )
        axis.axvline(0, color=COLORS["red"], linestyle="--", linewidth=1.5)
        axis.set_ylim(0, 1.02)
        axis.set_ylabel("score (not a probability)")
        axis.set_title(
            f"Holdout {reference.iloc[actual_position]['date']} — "
            "event in the central bin",
            loc="left",
            fontweight="bold",
        )
        axis.grid(alpha=0.2)
        axis.legend(loc="best")
    axes[-1].set_xlabel(
        f"offset from the event bin ({interval_days}-day units)"
    )
    fig.suptitle(
        f"{region_label} chronological validation — latest two distinct positive bins",
        fontsize=15,
        fontweight="bold",
    )
    save_figure(fig, output, raster_dpi)


def forecast_figure(
    forecast: pd.DataFrame,
    output: Path,
    *,
    interval_days: int,
    region_label: str,
    configured_forecast_end: str,
    highlight_count: int,
    raster_dpi: int,
) -> None:
    dates = pd.to_datetime(forecast["date"], format="%Y-%m-%d")
    score = forecast["metric_specialist_score_not_probability"].to_numpy(float)
    top = set(
        np.argsort(score)[-min(highlight_count, len(score)) :].tolist()
    )
    colors = [
        COLORS["orange"] if index in top else COLORS["blue"]
        for index in range(len(score))
    ]
    fig, axis = plt.subplots(figsize=(14, 6))
    axis.bar(dates, score, width=46, color=colors, alpha=0.9)
    axis.plot(dates, score, color="#244a64", linewidth=1.2, alpha=0.65)
    for index in sorted(top):
        slot_start = str(forecast.iloc[index]["date"])
        slot_end = str(forecast.iloc[index]["slot_end_inclusive"])
        axis.annotate(
            f"{score[index]:.3f}",
            (dates.iloc[index], score[index]),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            fontweight="bold",
        )
        axis.text(
            dates.iloc[index],
            score[index] / 2.0,
            f"from {slot_start} to {slot_end}",
            rotation=90,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white",
        )
    axis.set_ylim(0, max(0.82, score.max() + 0.08))
    axis.set_ylabel("fused score (not a probability)")
    axis.set_xlabel(f"start of the {interval_days}-day bin")
    axis.set_title(
        (
            f"{region_label} experimental timing forecast — "
            f"{forecast.iloc[0]['date']} through bins covering "
            f"{configured_forecast_end}"
        ),
        loc="left",
        fontweight="bold",
    )
    axis.grid(axis="y", alpha=0.25)
    fig.autofmt_xdate()
    save_figure(fig, output, raster_dpi)


def contribution_figure(
    trace: dict[str, Any], output: Path, *, raster_dpi: int
) -> None:
    system_totals = sorted(
        trace["system_totals"],
        key=lambda row: row["expected_final_weight"],
        reverse=True,
    )
    systems = [row["system"] for row in system_totals]
    palette = plt.get_cmap("tab10")
    system_colors = {
        system: palette(index % 10) for index, system in enumerate(systems)
    }
    metric_components = trace["metric_components"]
    has_core = float(trace["core_share"]) > 1e-12
    component_rows = (
        [
            {
                "label": f"overall core ({trace['core_share']:.1%})",
                "values": {
                    row["system"]: row["final_fusion_contribution"]
                    for row in trace["core_components"]
                },
            }
        ]
        if has_core
        else []
    ) + [
        {
            "label": (
                f"{row['metric'].replace('_', ' ')} "
                f"({row['final_fusion_share']:.1%})"
            ),
            "values": {
                system["system"]: system["final_fusion_contribution"]
                for system in row["systems"]
            },
        }
        for row in metric_components
    ]

    fig, axes = plt.subplots(1, 2, figsize=(17, 9))
    y = np.arange(len(component_rows))
    left = np.zeros(len(component_rows), dtype=float)
    for system in systems:
        values = np.asarray(
            [row["values"].get(system, 0.0) for row in component_rows],
            dtype=float,
        )
        bars = axes[0].barh(
            y,
            values,
            left=left,
            color=system_colors[system],
            label=system,
        )
        for bar, value in zip(bars, values):
            if value >= 0.018:
                axes[0].text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.1%}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        left += values
    axes[0].set_yticks(y, [row["label"] for row in component_rows])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("absolute contribution to the final weight")
    axes[0].set_title(
        "Each fusion component, stacked by system",
        loc="left",
        fontweight="bold",
    )
    axes[0].grid(axis="x", alpha=0.2)
    axes[0].legend(
        title="system",
        fontsize=8,
        title_fontsize=9,
        loc="lower right",
    )

    source_names = (["overall core"] if has_core else []) + [
        row["metric"].replace("_", " ") for row in metric_components
    ]
    source_colors = {
        source: plt.get_cmap("Set2")(index % 8)
        for index, source in enumerate(source_names)
    }
    y_system = np.arange(len(system_totals))
    left_system = np.zeros(len(system_totals), dtype=float)
    for source in source_names:
        if source == "overall core":
            values = np.asarray(
                [row["core_contribution"] for row in system_totals],
                dtype=float,
            )
        else:
            metric_key = source.replace(" ", "_")
            values = np.asarray(
                [
                    row["metric_contributions"].get(metric_key, 0.0)
                    for row in system_totals
                ],
                dtype=float,
            )
        axes[1].barh(
            y_system,
            values,
            left=left_system,
            color=source_colors[source],
            label=source,
        )
        left_system += values
    for index, total in enumerate(left_system):
        axes[1].text(
            total + 0.004,
            index,
            f"{total:.1%}",
            ha="left",
            va="center",
            fontsize=8,
            fontweight="bold",
        )
    axes[1].set_yticks(y_system, systems)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("final system weight")
    axes[1].set_title(
        "Each system weight, decomposed by source",
        loc="left",
        fontweight="bold",
    )
    axes[1].grid(axis="x", alpha=0.2)
    axes[1].legend(
        title="contribution source",
        fontsize=8,
        title_fontsize=9,
        loc="lower right",
    )
    fig.suptitle(
        "Automatic trace of the overall + metric-specialist fusion",
        fontsize=16,
        fontweight="bold",
    )
    save_figure(fig, output, raster_dpi)


def compact_search_figure(
    trials: pd.DataFrame, output: Path, *, raster_dpi: int
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    scatter = axes[0].scatter(
        trials["selected_historical_rows"],
        trials["fast_objective"],
        c=trials["k_event"],
        s=35 + 45 * trials["proximity_fraction"],
        cmap="viridis",
        alpha=0.78,
    )
    winner = trials.iloc[0]
    axes[0].scatter(
        [winner["selected_historical_rows"]],
        [winner["fast_objective"]],
        s=180,
        facecolors="none",
        edgecolors=COLORS["red"],
        linewidths=2.4,
        label="selected",
    )
    axes[0].set_xlabel("compact historical records")
    axes[0].set_ylabel("fast objective: 25% train / 75% validation")
    axes[0].set_title(
        f"{len(trials)} k-factor combinations", loc="left", fontweight="bold"
    )
    axes[0].grid(alpha=0.2)
    axes[0].legend()
    fig.colorbar(scatter, ax=axes[0], label="k_event")

    top = trials.head(12).sort_values("fast_objective")
    labels = [
        f"kE={int(row.k_event)} kB={int(row.k_between)} p={row.proximity_fraction:.2f}"
        for row in top.itertuples()
    ]
    axes[1].barh(labels, top["fast_objective"], color=COLORS["green"])
    axes[1].set_xlabel("fast objective")
    axes[1].set_title("Top configurations", loc="left", fontweight="bold")
    axes[1].grid(axis="x", alpha=0.2)
    fig.suptitle(
        "Compact historical master selection before feature ablation",
        fontsize=15,
        fontweight="bold",
    )
    save_figure(fig, output, raster_dpi)


def model_figure(
    fusion: dict[str, Any], output: Path, *, raster_dpi: int
) -> None:
    evidence = fusion["system_evidence"]
    ranking = sorted(
        (
            (system, row["overall_quality_mean"])
            for system, row in evidence.items()
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    top = ranking[:12]
    weights = fusion["selected_trial"]["system_weights"]
    final_weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    labels = [item[0] for item in reversed(top)]
    values = [item[1] for item in reversed(top)]
    axes[0].barh(labels, values, color=COLORS["blue"])
    axes[0].axvline(
        0.65, color=COLORS["red"], linestyle="--", label="core gate"
    )
    axes[0].set_xlabel("overall quality")
    axes[0].set_title("System quality", loc="left", fontweight="bold")
    axes[0].legend()
    axes[0].grid(axis="x", alpha=0.2)

    labels = [item[0] for item in reversed(final_weights)]
    values = [item[1] for item in reversed(final_weights)]
    axes[1].barh(labels, values, color=COLORS["orange"])
    axes[1].set_xlabel("final weight")
    axes[1].set_title(
        "Overall + specialist fusion", loc="left", fontweight="bold"
    )
    axes[1].grid(axis="x", alpha=0.2)
    fig.suptitle(
        "LCS / KAN / deep / Logistic / ExtraTrees comparison",
        fontsize=15,
        fontweight="bold",
    )
    save_figure(fig, output, raster_dpi)


def pdf_text_page(pdf: PdfPages, title: str, paragraphs: list[str]) -> None:
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.06, 0.93, title, fontsize=22, fontweight="bold", va="top")
    y = 0.84
    for paragraph in paragraphs:
        wrapped = textwrap.fill(paragraph, width=108)
        fig.text(0.07, y, wrapped, fontsize=11, va="top", linespacing=1.45)
        y -= 0.045 * (wrapped.count("\n") + 1) + 0.035
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def pdf_image_page(pdf: PdfPages, image_path: Path, title: str) -> None:
    image = plt.imread(image_path)
    fig = plt.figure(figsize=(11.69, 8.27))
    axis = fig.add_axes([0.03, 0.04, 0.94, 0.90])
    axis.imshow(image)
    axis.axis("off")
    fig.suptitle(title, fontsize=16, fontweight="bold")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--report-stem",
        default="V14_REPORT",
        help="Output basename for the Markdown and PDF reports.",
    )
    parser.add_argument(
        "--figure-tag",
        default="v14",
        help="Safe suffix used for generated figure filenames.",
    )
    parser.add_argument(
        "--report-title",
        default="",
        help="Optional report title; inferred from the run manifest when omitted.",
    )
    parser.add_argument(
        "--region-label",
        default="",
        help="Optional region label; inferred from the run manifest when omitted.",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        default=0,
        help="Bin width; inferred from the run manifest when zero.",
    )
    parser.add_argument(
        "--forecast-end",
        default="",
        help="Configured forecast horizon; inferred from the run manifest when omitted.",
    )
    parser.add_argument(
        "--highlight-count",
        type=int,
        default=3,
        help="Number of highest forecast bars to highlight and label.",
    )
    parser.add_argument(
        "--top-table-count",
        type=int,
        default=6,
        help="Number of forecast bins included in ranking tables.",
    )
    parser.add_argument(
        "--image-dpi",
        type=int,
        default=360,
        help="Raster PNG resolution. A vector SVG companion is always emitted.",
    )
    args = parser.parse_args()
    if args.highlight_count < 1 or args.top_table_count < 1:
        parser.error("highlight and table counts must be positive")
    if args.image_dpi < 150:
        parser.error("--image-dpi must be at least 150")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.figure_tag):
        parser.error("--figure-tag may contain only letters, digits, dot, dash, underscore")
    run_dir = args.run_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(run_dir / "00_config/run_manifest.json")
    parameters = manifest["parameters"]
    region_label = args.region_label or str(parameters["region_label"])
    interval_days = args.interval_days or int(parameters["interval_days"])
    configured_forecast_end = args.forecast_end or str(
        parameters["forecast_end"]
    )
    pipeline_label = str(manifest["pipeline"])
    report_title = args.report_title or (
        f"{region_label} mega-earthquake timing forecast — {pipeline_label}"
    )
    magnitude_threshold = float(parameters["timing_magnitude_threshold"])
    validation_magnitude_threshold = float(
        parameters.get("timing_validation_magnitude_threshold", magnitude_threshold)
    )

    catalog_audit = load_json(
        run_dir / "02_audit/mega_quake_catalog_audit.json"
    )
    frontier = load_json(run_dir / "02_audit/jpl_history_frontier.json")
    compact = load_json(
        run_dir / "02_master_search/compact_k_factor_selection.json"
    )
    primary = load_json(run_dir / "05_ensemble/timing/final_summary.json")
    fusion = load_json(
        run_dir
        / "05_ensemble/timing/metric_specialist_fusion/"
        "metric_specialist_fusion_summary.json"
    )
    trace = load_json(
        run_dir
        / "05_ensemble/timing/metric_specialist_fusion/"
        "metric_fusion_contribution_trace.json"
    )
    randomized = load_json(
        run_dir / "07_randomized_control/timing/summary.json"
    )
    shuffled = load_json(
        run_dir / "07_historical_record_shuffle/timing/summary.json"
    )
    forecast = pd.read_csv(
        run_dir
        / "05_ensemble/timing/metric_specialist_fusion/"
        "metric_specialist_fusion_forecast.csv"
    )
    trials = pd.read_csv(
        run_dir / "02_master_search/compact_k_factor_trials.csv"
    )

    figures = {
        "validation": output_dir / f"timing_validation_{args.figure_tag}.png",
        "forecast": output_dir / f"timing_forecast_{args.figure_tag}.png",
        "compact": output_dir / f"compact_k_factor_search_{args.figure_tag}.png",
        "models": output_dir / f"model_metric_fusion_{args.figure_tag}.png",
        "contributions": output_dir / f"metric_contributions_{args.figure_tag}.png",
    }
    validation_figure(
        run_dir,
        fusion,
        figures["validation"],
        interval_days=interval_days,
        region_label=region_label,
        raster_dpi=args.image_dpi,
    )
    forecast_figure(
        forecast,
        figures["forecast"],
        interval_days=interval_days,
        region_label=region_label,
        configured_forecast_end=configured_forecast_end,
        highlight_count=args.highlight_count,
        raster_dpi=args.image_dpi,
    )
    compact_search_figure(
        trials, figures["compact"], raster_dpi=args.image_dpi
    )
    model_figure(fusion, figures["models"], raster_dpi=args.image_dpi)
    contribution_figure(
        trace, figures["contributions"], raster_dpi=args.image_dpi
    )

    selected = compact["selected"]
    selected_trial = fusion["selected_trial"]
    top_slots = fusion["forecast"]["top_slots"][: args.top_table_count]
    core = fusion["core_weights"]
    available_bodies = [
        body
        for body in str(frontier["selected"]["available_bodies"]).split(",")
        if body
    ]
    available_body_count = int(frontier["selected"]["available_body_count"])
    body_contract_count = len(available_bodies)
    forecast_start = str(forecast.iloc[0]["date"])
    forecast_coverage_end = str(forecast.iloc[-1]["slot_end_inclusive"])
    outer_slots = primary["outer_validation_selection"]["resolved_slots"]
    direct_fusion = trace.get("portfolio_overall_quality_share") is None
    fusion_description = (
        "The selected false-positive-aware direct search assigns the complete "
        "fusion weight to the audited system mixture. Candidate systems were "
        "selected automatically from complementary overall, fold-specific, "
        "hard-negative and background-rejection criteria; seeded sparse mixes "
        "and an exhaustive pair grid were evaluated with the declared objective."
        if direct_fusion
        else (
            f"The selected fusion assigns **{trace['core_share']:.0%}** to the "
            f"overall-quality core and **{trace['specialist_share']:.0%}** to "
            "metric-specialist portfolios. Within the specialist component, each "
            "metric's reliability determines its share. Within a metric, system "
            f"weights combine {trace['portfolio_overall_quality_share']:.0%} "
            f"overall quality and {trace['portfolio_metric_quality_share']:.0%} "
            "metric-specific quality."
        )
    )
    report_lines = [
        f"# {report_title}",
        "",
        f"**Resolution:** exact {interval_days}-day bins.  ",
        (
            f"**Forecast:** {forecast_start} through the bin covering "
            f"{configured_forecast_end}; persisted coverage ends "
            f"{forecast_coverage_end}.  "
        ),
        "**Scope:** experimental timing only; no localization forecast.",
        "",
        "## Catalog and astronomical master",
        "",
        (
            f"The unified catalog contains **{catalog_audit['total_rows']} events**: "
            f"{catalog_audit['historical_rows']} supplied historical events and "
            f"{catalog_audit['usgs_rows']} USGS events discovered at M≥"
            f"{validation_magnitude_threshold:g}. Training positives use M≥"
            f"{magnitude_threshold:g}; explicit chronological holdouts may use "
            f"M≥{validation_magnitude_threshold:g}."
        ),
        "",
        (
            f"JPL Horizons provides **{available_body_count}/"
            f"{body_contract_count} configured bodies** from the "
            f"{frontier['selected']['candidate_start']} bin. The selected frontier "
            f"retains {frontier['selected']['retained_event_rows']} catalog events."
        ),
        "",
        "## Temporal compaction before feature research",
        "",
        (
            f"The search evaluated **{compact['candidate_count']} combinations**. "
            f"Selected configuration: `k_event={selected['k_event']}`, "
            f"`k_between={selected['k_between']}`, proximity fraction "
            f"`{selected['proximity_fraction']:.2f}`. The training master contains "
            f"{compact['output']['historical_rows']} compact historical records "
            "instead of the continuous lookup grid."
        ),
        "",
        f"![K-factor search]({figures['compact'].with_suffix('.svg').name})",
        "",
        "## Validation and models",
        "",
        (
            f"Primary gate: **{primary['validation_gate']}**. The metric-specialist "
            f"fusion achieved mean validation quality "
            f"**{selected_trial['validation_quality_mean']:.3f}**, worst-fold "
            f"quality **{selected_trial['validation_quality_worst']:.3f}**, and "
            f"{selected_trial['exact_peak_count']}/{len(outer_slots)} exact peaks. "
            f"The distinct validation bins were {', '.join(outer_slots)}."
        ),
        "",
        (
            f"Randomized-label control quality: "
            f"**{randomized['validation_metrics']['quality_higher_is_better']:.3f}**. "
            f"Historical-record order-shuffle quality: "
            f"**{shuffled['validation_metrics']['quality_higher_is_better']:.3f}**."
        ),
        "",
        f"![Chronological validation]({figures['validation'].with_suffix('.svg').name})",
        "",
        f"![Models and weights]({figures['models'].with_suffix('.svg').name})",
        "",
        "## Metric-specialist fusion: selected models and contributions",
        "",
        fusion_description,
        "",
        (
            "The following table and chart are generated directly from the "
            "[automatic fusion contribution trace]"
            "(../05_ensemble/timing/metric_specialist_fusion/"
            "metric_fusion_contribution_trace.json), rather than manually entered "
            "report values."
        ),
        "",
        (
            f"![Metric contributions]"
            f"({figures['contributions'].with_suffix('.svg').name})"
        ),
        "",
        "| selected metric | final fusion share | systems within metric | contributions to final weight |",
        "| --- | ---: | --- | --- |",
    ]
    for component in trace["metric_components"]:
        within = ", ".join(
            f"`{row['system']}` {row['within_metric_weight']:.1%}"
            for row in component["systems"]
        )
        contributions = ", ".join(
            f"`{row['system']}` {row['final_fusion_contribution']:.4f}"
            for row in component["systems"]
        )
        report_lines.append(
            f"| `{component['metric']}` | "
            f"{component['final_fusion_share']:.2%} | {within} | "
            f"{contributions} |"
        )
    report_lines.extend(
        [
            "",
            "### Final system-weight decomposition",
            "",
            "| system | core contribution | metric contribution | final weight |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(
        trace["system_totals"],
        key=lambda item: item["expected_final_weight"],
        reverse=True,
    ):
        report_lines.append(
            f"| `{row['system']}` | {row['core_contribution']:.4f} | "
            f"{row['specialist_contribution']:.4f} | "
            f"{row['expected_final_weight']:.4f} |"
        )
    report_lines.extend(
        [
            "",
            "## Timing forecast",
            "",
            f"![Forecast]({figures['forecast'].with_suffix('.svg').name})",
            "",
            "| rank | start | inclusive end | score | percentile |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )
    for rank, row in enumerate(top_slots, 1):
        report_lines.append(
            f"| {rank} | {row['date']} | {row['slot_end_inclusive']} | "
            f"{row['metric_specialist_score_not_probability']:.4f} | "
            f"{row['forecast_rank_percentile']:.4f} |"
        )
    report_lines.extend(
        [
            "",
            "## Overall fusion core",
            "",
            "| system | weight within core | overall quality |",
            "| --- | ---: | ---: |",
        ]
    )
    for system, weight in sorted(core.items(), key=lambda item: item[1], reverse=True):
        report_lines.append(
            f"| {system} | {weight:.4f} | "
            f"{fusion['system_evidence'][system]['overall_quality_mean']:.4f} |"
        )
    report_lines.extend(
        [
            "",
            "## Limitations",
            "",
            (
                "The latest two distinct positive bins were used as selection-validation "
                "for both k-factor search and fusion selection; they are not an "
                "independent external test. The historical catalog includes uncertain "
                "pre-instrumental estimates. Scores are empirical ranks, not calibrated "
                "probabilities, predicted magnitudes, or earthquake warnings."
            ),
            "",
        ]
    )
    report_md = output_dir / f"{args.report_stem}.md"
    report_md.write_text("\n".join(report_lines), encoding="utf-8")

    pdf_path = output_dir / f"{args.report_stem}.pdf"
    with PdfPages(pdf_path) as pdf:
        pdf_text_page(
            pdf,
            report_title,
            [
                (
                    f"Experimental {interval_days}-day timing pipeline for "
                    f"{region_label}, using a USGS M≥{magnitude_threshold:g} "
                    "discovery query and complete retention of the supplied "
                    "historical catalog."
                ),
                (
                    f"Catalog: {catalog_audit['total_rows']} events. JPL master: "
                    f"{available_body_count}/{body_contract_count} configured bodies "
                    f"from {frontier['selected']['candidate_start']}. Compact master: "
                    f"{compact['output']['historical_rows']} historical records."
                ),
                (
                    f"Metric-specialist validation: mean "
                    f"{selected_trial['validation_quality_mean']:.3f}, worst "
                    f"{selected_trial['validation_quality_worst']:.3f}, "
                    f"exact peaks {selected_trial['exact_peak_count']}/"
                    f"{len(outer_slots)}."
                ),
                (
                    "This document reports retrospective research signals. It is "
                    "not an operational earthquake prediction or warning system."
                ),
            ],
        )
        pdf_image_page(pdf, figures["compact"], "Compact-master search")
        pdf_image_page(pdf, figures["validation"], "Chronological validation")
        pdf_image_page(pdf, figures["models"], "Systems and fusion")
        method_details = [
            (
                "The false-positive-aware direct search evaluates an exhaustive "
                "pair grid plus seeded sparse mixtures from an automatically "
                "selected complementary system pool. Selection combines timing "
                "quality, hard-negative/background control and exact peaks."
                if direct_fusion
                else (
                    "For each metric, eligible systems are ranked using robust "
                    "metric-specific quality and overall quality. The within-metric "
                    f"weight combines {trace['portfolio_overall_quality_share']:.0%} "
                    f"overall and {trace['portfolio_metric_quality_share']:.0%} "
                    "metric-specific quality. Selected metric reliabilities are "
                    "normalized within the specialist share."
                )
            ),
            (
                f"Automatic trace: {trace['schema']}. Weight reconstruction: "
                f"{'PASS' if trace['checks']['weights_reconstructed'] else 'FAIL'}; "
                "maximum absolute error "
                f"{trace['checks']['maximum_absolute_reconstruction_error']:.2e}."
            ),
            (
                f"The selected search retained {len(trace['metric_components'])} "
                f"contribution group(s) and used the candidate named "
                f"{selected_trial['metric_set']}."
            ),
        ]
        pdf_text_page(
            pdf,
            "Metric-specialist fusion — method and traceability",
            [
                (
                    f"Overall share: {trace['core_share']:.0%}. Metric-specialist "
                    f"share: {trace['specialist_share']:.0%}."
                ),
                *method_details,
            ],
        )
        pdf_text_page(
            pdf,
            "Selected metric-specialist portfolios",
            [
                (
                    f"{component['metric'].replace('_', ' ')} — final fusion share "
                    f"{component['final_fusion_share']:.2%}; "
                    + ", ".join(
                        f"{row['system']} {row['within_metric_weight']:.1%} "
                        f"(final contribution "
                        f"{row['final_fusion_contribution']:.4f})"
                        for row in component["systems"]
                    )
                    + "."
                )
                for component in trace["metric_components"]
            ],
        )
        pdf_image_page(
            pdf,
            figures["contributions"],
            "Overall and metric-specialist contributions",
        )
        pdf_image_page(
            pdf,
            figures["forecast"],
            f"Timing forecast through {configured_forecast_end}",
        )
        pdf_text_page(
            pdf,
            "Highest-scoring forecast windows",
            [
                (
                    f"{index}. {row['date']} → {row['slot_end_inclusive']}: "
                    f"score {row['metric_specialist_score_not_probability']:.4f}, "
                    f"percentile {row['forecast_rank_percentile']:.4f}."
                )
                for index, row in enumerate(top_slots, 1)
            ]
            + [
                "These values are uncalibrated relative scores and must not be "
                "interpreted as earthquake probabilities."
            ],
        )
    render_manifest = {
        "schema": "timing_report_render.v1",
        "generator": str(Path(__file__).resolve()),
        "language": "en",
        "run_dir": str(run_dir),
        "pipeline": pipeline_label,
        "parameters": {
            "report_stem": args.report_stem,
            "figure_tag": args.figure_tag,
            "report_title": report_title,
            "region_label": region_label,
            "interval_days": interval_days,
            "forecast_end": configured_forecast_end,
            "highlight_count": args.highlight_count,
            "top_table_count": args.top_table_count,
            "image_dpi": args.image_dpi,
            "vector_companion_format": "svg",
        },
        "dependencies": ["Python", "NumPy", "pandas", "Matplotlib"],
        "artifacts": {
            "markdown": str(report_md),
            "pdf": str(pdf_path),
            "figures_png": [str(path) for path in figures.values()],
            "figures_svg": [
                str(path.with_suffix(".svg")) for path in figures.values()
            ],
        },
    }
    render_manifest_path = output_dir / "report_render_manifest.json"
    render_manifest_path.write_text(
        json.dumps(render_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Report Markdown: {report_md}")
    print(f"Report PDF:      {pdf_path}")
    print(f"Render manifest: {render_manifest_path}")
    for path in figures.values():
        print(f"Figure:          {path}")


if __name__ == "__main__":
    main()

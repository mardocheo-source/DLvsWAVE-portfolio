"""
DLVS-Wave v2.0: Section Divider & Cover Page Generator.
Creates publication-grade visual section cover sheets and executive index pages
in standard A4 Landscape (11.693 x 8.268 inches) format, perfectly filling the page.
Includes geodetic coordinates, temporal bounding boxes, catalog specifications,
prominent UTC & JST publication timestamps, and embedded mini-maps.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger("uncompressed_pipeline.cover_generator")

# Standard A4 Landscape in inches
A4_WIDTH = 11.693
A4_HEIGHT = 8.268


def generate_executive_title_cover_page(
    title: str,
    subtitle: str,
    metadata: dict[str, str],
    output_pdf: Path,
    output_png: Path | None = None,
    mini_map_png: Path | None = None,
    energy_callout: str = "M ≥ 7.7+ MEGATHRUST",
    spatial_callout: str = "M ≥ 6.8+ SHINDO 6+",
    show_location_map: bool = False,
) -> Path:
    """
    Generates the main executive dossier cover page in full-bleed A4 Landscape format.
    Includes spatio-temporal boundary details, prominent timestamp (UTC & JST),
    and prominent energy threshold callouts.
    """
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(A4_WIDTH, A4_HEIGHT), dpi=240)
    fig.patch.set_facecolor("#0F172A")  # Deep slate navy

    # Main layout axes
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#0F172A")
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)

    # Current Timestamps
    now_utc = datetime.now(timezone.utc)
    ts_utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    # JST is UTC+9
    now_jst = pd.to_datetime(now_utc).tz_convert("Asia/Tokyo") if hasattr(pd, "to_datetime") else None
    ts_str = f"Publication & Synthesis Timestamp: {ts_utc_str} | {now_jst.strftime('%Y-%m-%d %H:%M JST')}"

    # Header Title Banner
    ax.text(0.50, 0.93, title, ha="center", va="center", fontsize=17.5, fontweight="bold", color="#F8FAFC")
    ax.text(0.50, 0.88, subtitle, ha="center", va="center", fontsize=11.0, color="#38BDF8", style="italic")

    # Prominent Timestamp Banner under Title
    ax.text(
        0.50, 0.84,
        ts_str,
        ha="center", va="center", fontsize=9.0, fontweight="bold", color="#F1F5F9",
        bbox=dict(boxstyle="round,pad=0.30", facecolor="#1E293B", edgecolor="#0284C7", alpha=0.90, linewidth=1.0)
    )
    ax.plot([0.08, 0.92], [0.81, 0.81], color="#0284C7", linewidth=2.0)

    # Left Column: Detailed Spatio-Temporal Parameters (X: 0.08 -> 0.58)
    start_y = 0.75
    y_step = 0.075

    for idx, (label, val) in enumerate(metadata.items()):
        y_pos = start_y - (idx * y_step)
        ax.text(
            0.08, y_pos, label.upper(),
            ha="left", va="center", fontsize=8.0, fontweight="bold", color="#38BDF8",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#1E293B", edgecolor="#0284C7", alpha=0.85, linewidth=0.8),
        )
        ax.text(0.08, y_pos - 0.032, val, ha="left", va="center", fontsize=9.2, fontweight="bold", color="#F1F5F9")

    # Right Column: High-Visibility Energy Threshold Callouts & Cartographic Inset (X: 0.60 -> 0.92)
    ax.text(
        0.76, 0.75, "PRIMARY CRITICAL ENERGY GATE",
        ha="center", va="center", fontsize=11.0, fontweight="bold", color="#F87171"
    )
    ax.text(
        0.76, 0.69, energy_callout,
        ha="center", va="center", fontsize=18.0, fontweight="bold", color="#EF4444",
        bbox=dict(boxstyle="square,pad=0.45", facecolor="#450A0A", edgecolor="#DC2626", linewidth=1.8),
    )

    ax.text(
        0.76, 0.62, "SPATIAL FAULTS LOCALIZATION",
        ha="center", va="center", fontsize=10.0, fontweight="bold", color="#38BDF8"
    )
    ax.text(
        0.76, 0.57, spatial_callout,
        ha="center", va="center", fontsize=14.0, fontweight="bold", color="#38BDF8",
        bbox=dict(boxstyle="square,pad=0.35", facecolor="#082F49", edgecolor="#0284C7", linewidth=1.4),
    )

    # Inset Map if provided
    if show_location_map and mini_map_png and Path(mini_map_png).exists():
        try:
            img = plt.imread(str(mini_map_png))
            map_ax = fig.add_axes([0.62, 0.16, 0.28, 0.36])
            map_ax.imshow(img)
            map_ax.axis("off")
            map_ax.set_title("Target Seismotectonic Zones", fontsize=8.5, color="#94A3B8", pad=4)
        except Exception as e:
            logger.warning("Could not embed mini map: %s", e)
    else:
        # Method-specific maps belong with their own evidence, not on the cover.
        for y, heading, body in [
            (.46, 'NEURAL LOCATION', 'KAN + Deep ResNet + LCS\nLearned associations between inputs\nand historical earthquake zones.'),
            (.32, 'HISTORICAL LOCATION', 'Weighted historical analogs\nSimilar past conditions vote\nfor candidate earthquake zones.'),
            (.18, 'READ THE METHODS SEPARATELY', 'The two methods can disagree.\nTheir maps and validation appear\nin the Location Forecast section.')]:
            ax.text(.76,y,heading,ha='center',color='#38BDF8',fontsize=9,weight='bold')
            ax.text(.76,y-.035,body,ha='center',va='top',color='#F1F5F9',fontsize=8.5,linespacing=1.4)

    # Footer notice with explicit timestamp
    ax.text(
        0.50, 0.06,
        f"DLVS-Wave v2.0 Publication Standards | Strictly Parametric Calibration | Generated: {ts_utc_str}\n"
        "Experimental Astroseismic & Deep Neural Physics Conglomerate | For Scientific Evaluation Only",
        ha="center", va="center", fontsize=8.0, color="#64748B", style="italic"
    )

    # Freeze limits
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)

    fig.savefig(output_pdf, format="pdf")
    if output_png:
        fig.savefig(output_png, format="png", dpi=240)
    plt.close(fig)
    return output_pdf


def generate_section_divider_page(
    section_number: str,
    section_title: str,
    section_description: str,
    key_highlights: list[str],
    output_pdf: Path,
    output_png: Path | None = None,
) -> Path:
    """Generates an explicit section divider cover sheet in A4 Landscape format."""
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(A4_WIDTH, A4_HEIGHT), dpi=240)
    fig.patch.set_facecolor("#F8FAFC")

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#F8FAFC")
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)

    is_super = "SUPER-FUSION" in section_number
    badge_bg = "#FEF2F2" if is_super else "#F0F9FF"
    badge_edge = "#EF4444" if is_super else "#0284C7"
    badge_txt = "#DC2626" if is_super else "#0369A1"
    line_col = "#DC2626" if is_super else "#0284C7"

    # Section Badge
    ax.text(
        0.50, 0.73,
        section_number.upper(),
        ha="center", va="center",
        fontsize=13.0, fontweight="bold",
        color=badge_txt,
        bbox=dict(boxstyle="round,pad=0.45", facecolor=badge_bg, edgecolor=badge_edge, linewidth=1.5),
    )

    # Main Title
    ax.text(0.50, 0.64, section_title, ha="center", va="center", fontsize=18.0, fontweight="bold", color="#0F172A")
    ax.plot([0.15, 0.85], [0.59, 0.59], color=line_col, linewidth=2.0)

    # Subtitle / Description
    ax.text(0.50, 0.54, section_description, ha="center", va="center", fontsize=10.5, color="#475569", style="italic")

    # Key Highlights Box
    box_y = 0.44
    for idx, item in enumerate(key_highlights):
        y_pos = box_y - (idx * 0.065)
        ax.plot([0.22, 0.23], [y_pos, y_pos], color=line_col, linewidth=3.0)
        ax.text(0.25, y_pos, item, ha="left", va="center", fontsize=9.8, fontweight="bold", color="#1E293B")

    # Footer note
    ax.text(
        0.50, 0.07,
        "DLVS-Wave v2.0 Structured Scientific Dossier | Autonomous Multi-Level Seismotectonic Architecture",
        ha="center", va="center", fontsize=8.0, color="#94A3B8", style="italic"
    )

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)

    fig.savefig(output_pdf, format="pdf")
    if output_png:
        fig.savefig(output_png, format="png", dpi=240)
    plt.close(fig)
    return output_pdf

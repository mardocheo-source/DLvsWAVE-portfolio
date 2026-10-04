"""
DLVS-Wave v2.0: Structured Master Publication Dossier Builder.
Assembles the complete, cleanly-sectioned master PDF containing:
1. Executive Spatio-Temporal Cover Page (Full A4 Landscape with Inset Map, Big Energy Callouts, Timestamp)
2. Table of Contents / Index Page (Full A4 Landscape, 4 clean columns, 100% matched nomenclature)
3. SECTION 1: Main Celestial Bodies Branch (01..05 with all pages, tables & validation)
4. SECTION 2: Minor Bodies & Asteroids Branch (Deep exploration with all pages & tables)
5. SECTION 3: Hierarchical Asymmetric Super-Fusion (Energy Spectrum, Ablation & Appendices)
6. SECTION 4: Spatial Seismotectonic Zones Classification (6 Fault Zones Cartography)

Features:
- Standardized Top Running Header across all content pages:
  Format: SECTION X > SUBSECTION : PAGE TITLE
- Bottom Running Footer across all content pages:
  Format: Left: Timestamp (UTC & JST) | Center: Confidential Scientific Prototype | Right: Page X of 25
- Full-bleed A4 landscape scaling, zero text clipping or overlapping.
"""
from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import logging
from pathlib import Path
import textwrap
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd
from pypdf import PdfReader, PdfWriter, Transformation

from uncompressed_pipeline.section_cover_generator import (
    generate_executive_title_cover_page,
    generate_section_divider_page,
    A4_WIDTH,
    A4_HEIGHT,
)

logger = logging.getLogger("uncompressed_pipeline.compile_structured")


def compile_complete_structured_dossier(
    macro_dir: Path,
    output_pdf: Path,
) -> Path:
    macro_dir = Path(macro_dir)
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    energy_dir = macro_dir / "01_energy_forecast_m77"
    spatial_dir = macro_dir / "02_spatial_zones_forecast"

    temp_covers_dir = macro_dir / ".temp_covers"
    temp_covers_dir.mkdir(parents=True, exist_ok=True)

    map_png = spatial_dir / "01_data/spatial_seismotectonic_zones_map.png"

    # 1. Generate Executive Cover Page with Full Spatio-Temporal & Energy Specs
    cover_pdf = temp_covers_dir / "00_executive_cover.pdf"
    generate_executive_title_cover_page(
        title="DLVS-WAVE v2.0: JOINT SEISMIC FORECAST DOSSIER",
        subtitle="Weekly Seismic Potential Ceilings (up to M 7.7+) & Spatial Fault Zones Classification (M ≥ 6.8)",
        metadata={
            "Geographic Target Area": "Japan Archipelago, Sea of Japan & Pacific Subduction Trenches",
            "Spatio-Temporal Bounding Box": "Lat: [24.00°N to 48.00°N] | Lon: [126.00°E to 150.00°E]",
            "Prospective Forecast Window": "August 01, 2026 to January 31, 2027 (Weekly Macro-Corridors)",
            "Temporal Resolution & Cadence": "Strict 7-Day Regular Step (26 Prospective Slices | 6,836 Historical Weeks)",
            "Predictive Modeling Core": "Multi-Paradigm Synthesis: Spline KAN + Tabular ResNet + Genetic LCS",
            "Harmonic Ephemerides": "Asymmetric Fusion: 85% Main Planetary Baseline + 15% Minor Bodies",
            "Quiescence Regularization": "Sequential 2-Digit Pi Seeds (14, 15, 92...) + 2011-2026 Calm Void Infill",
        },
        output_pdf=cover_pdf,
        mini_map_png=map_png if map_png.exists() else None,
    )

    # 2. Section 1 Divider: Main Celestial Bodies
    sec1_div = temp_covers_dir / "sec1_main_bodies_cover.pdf"
    generate_section_divider_page(
        section_number="SECTION 1: MAIN BODIES",
        section_title="Main Celestial Bodies Branch (Sun, Moon, Major Planets)",
        section_description="Long-period gravitational harmonics, tidal resonances and synodic baselines",
        key_highlights=[
            "Level 1 Multi-Paradigm Screening (KAN, Deep Learning, LCS)",
            "Level 2 Deep Meta-Optimizer Surrogate Response Refinement",
            "Level 3 Asymmetric Fusion Composition Table with Specialist Role Assignments",
            "Hold-Out Validation Performance on Historical Megathrust Corridors",
        ],
        output_pdf=sec1_div,
    )

    # 3. Section 2 Divider: Minor Celestial Bodies
    sec2_div = temp_covers_dir / "sec2_minor_bodies_cover.pdf"
    generate_section_divider_page(
        section_number="SECTION 2: MINOR BODIES",
        section_title="Minor Bodies Branch (Asteroids, Centaurs, Galilean Moons)",
        section_description="Ceres, Pallas, Vesta, Chiron, Callisto, Io, Europa, Ganymede - High-frequency fine-grained perturbation screening",
        key_highlights=[
            "7,200 Level 1 Exploration Trials with Sequential 2-digit Pi Seeds (14, 15, 92, 65, ...)",
            "Level 2 Deep Meta-Optimizer Perturbation Optimization (240 surrogate iterations)",
            "Level 3 Multi-Horizon Synthesis and Minor Bodies Composition Audit",
            "Regularization of Fast Orbital Frequencies preventing background overtriggering",
        ],
        output_pdf=sec2_div,
    )

    # 4. Section 3 Divider: Hierarchical Super-Fusion
    sec3_div = temp_covers_dir / "sec3_super_fusion_cover.pdf"
    generate_section_divider_page(
        section_number="SECTION 3: SUPER-FUSION",
        section_title="Hierarchical Super-Fusion: Weekly Potential Ceiling (up to M)",
        section_description="Calibrated confirmatory gating of potential tiers: 85% Main Planetary Baseline + 15% Minor Bodies Harmonic Confirmation",
        key_highlights=[
            "Super-Fusion Prospective Forecast Trajectory (August 2026 - January 2027)",
            "Continuous Seismic Energy & Model-Derived Potential Ceiling",
            "Multi-Level Fusion Benchmark Comparison Matrix & Quality Audit",
            "Multi-Paradigm Global Ablation Table: Selected Best vs Discarded Worst",
            "Consultative Appendices: KAN, Deep Learning, and LCS Feature & Ephemerides Inventory",
        ],
        output_pdf=sec3_div,
    )

    # 5. Section 4 Divider: Spatial Zones Classification
    sec4_div = temp_covers_dir / "sec4_spatial_zones_cover.pdf"
    generate_section_divider_page(
        section_number="SECTION 4: SPATIAL FAULT ZONES",
        section_title="Spatial Seismotectonic Zones Classification (M ≥ 6.8)",
        section_description="Direct Multi-Class Fault Localization across 5 Homogeneous Tectonic Cells with 219 Historical Validation Events",
        key_highlights=[
            "Georeferenced Basemap with High-Detail Coastlines and 95% Confidence Elliptical Hulls",
            "Zone 0: Kuril Trench | Zone 1: Hokkaido / Tokachi-Oki | Zone 2: Tohoku / Fukushima",
            "Zone 3: Nankai Trough / Tokai & Kii Channel | Zone 4: Kyushu / Hyuga-nada & Ryukyu",
            "Direct 1-to-1 Mapping from Prospective Energy Corridors to Active Fault Hulls",
        ],
        output_pdf=sec4_div,
    )

    # Gather source documents
    energy_main = energy_dir / "main_bodies_branch"
    energy_minor = energy_dir / "minor_bodies_branch"
    energy_super = energy_dir / "fusion_main_minor"

    # Assemble all pages with strict hierarchical nomenclature:
    # (section_breadcrumb, page_title, pdf_path)
    pages_to_assemble = [
        # --- TITLE & COVER ---
        ("COVER", "Executive Spatio-Temporal Overview", cover_pdf),

        # --- SECTION 1: MAIN BODIES ---
        ("SECTION 1 > MAIN BODIES", "Architectural Section Overview", sec1_div),
        ("SECTION 1 > MAIN BODIES", "Prospective Forecast Trajectory (Aug 2026 - Jan 2027)", energy_main / "05_level3_final_fusion/compound_prospective_forecast.pdf"),
        ("SECTION 1 > MAIN BODIES", "Weekly Seismic Potential Ceiling (up to M; Non-Deterministic)", energy_main / "05_level3_final_fusion/prospective_energy_magnitude_spectrum.pdf"),
        ("SECTION 1 > MAIN BODIES", "Multi-Level Benchmark Comparison Matrix", energy_main / "05_level3_final_fusion/multilevel_fusion_benchmark_comparison.pdf"),
        ("SECTION 1 > MAIN BODIES", "Level 1 Screening Fusion Trial Composition Table", energy_main / "03_level1_fusion/fusion_trials_composition_table.pdf"),
        ("SECTION 1 > MAIN BODIES", "Level 2 Deep Meta-Optimizer Trial Composition Table", energy_main / "04_level2_deep_meta_optimizer/level2_fusion/fusion_trials_composition_table.pdf"),
        ("SECTION 1 > MAIN BODIES", "Level 3 Final Multi-Horizon Synthesis Composition Table", energy_main / "05_level3_final_fusion/fusion_trials_composition_table.pdf"),
        ("SECTION 1 > MAIN BODIES", "Sliced Hold-Out Validation Corridors (2003 & 2011)", energy_main / "05_level3_final_fusion/compound_validation_report.pdf"),

        # --- SECTION 2: MINOR BODIES ---
        ("SECTION 2 > MINOR BODIES", "Architectural Section Overview", sec2_div),
        ("SECTION 2 > MINOR BODIES", "Level 1 Screening Composition Table (7,200 Trials with Pi Seeds)", energy_minor / "03_level1_fusion/fusion_trials_composition_table.pdf"),
        ("SECTION 2 > MINOR BODIES", "Level 2 Deep Meta-Optimizer Composition Table", energy_minor / "04_level2_deep_meta_optimizer/level2_fusion/fusion_trials_composition_table.pdf"),
        ("SECTION 2 > MINOR BODIES", "Level 3 Final Multi-Horizon Composition Table", energy_minor / "05_level3_final_fusion/fusion_trials_composition_table.pdf"),

        # --- SECTION 3: SUPER-FUSION (MAIN + MINOR) ---
        ("SECTION 3 > SUPER-FUSION", "Architectural Section Overview", sec3_div),
        ("SECTION 3 > SUPER-FUSION", "Super-Fusion Prospective Forecast (Main 85% + Minor 15%)", energy_super / "compound_prospective_forecast.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Super-Fusion Weekly Potential Ceiling (up to M; Non-Deterministic)", energy_super / "prospective_energy_magnitude_spectrum.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Super-Fusion Multi-Level Benchmark Comparison Matrix", energy_main / "05_level3_final_fusion/multilevel_fusion_benchmark_comparison.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Multi-Paradigm Global Ablation Table (Selected Best vs Worst)", energy_super / "ablation_best_worst_composition_table.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Super-Fusion Sliced Validation Corridors", energy_super / "compound_validation_report.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Appendix A: KAN Spline Basis & Ephemerides Feature Inventory", energy_super / "appendix_audit_features_kan.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Appendix B: Deep Learning (Tabular ResNet) Feature Inventory", energy_super / "appendix_audit_features_deep_learning.pdf"),
        ("SECTION 3 > SUPER-FUSION", "Appendix C: LCS (Learning Classifier System) Feature Inventory", energy_super / "appendix_audit_features_lcs.pdf"),

        # --- SECTION 4: SPATIAL FAULT ZONES ---
        ("SECTION 4 > SPATIAL FAULT ZONES", "Architectural Section Overview", sec4_div),
        ("SECTION 4 > SPATIAL FAULT ZONES", "Georeferenced Fault Zones Map with 95% Confidence Elliptical Hulls", spatial_dir / "01_data/spatial_seismotectonic_zones_map.pdf"),
    ]

    # Collect existing pages
    collected_pages = []
    for sec_tag, sub_tag, pdf_file in pages_to_assemble:
        if pdf_file.exists():
            reader = PdfReader(str(pdf_file))
            for p in reader.pages:
                collected_pages.append((sec_tag, sub_tag, p))
            print(f"Added [{sec_tag} : {sub_tag}] -> {pdf_file.name} ({len(reader.pages)} pgs)")
        else:
            print(f"Warning: {pdf_file} missing, skipping.")

    total_pages = len(collected_pages)
    print(f"Total Pages before TOC insertion: {total_pages}")

    # Generate Index / Table of Contents as Page 2
    index_pdf = temp_covers_dir / "01_table_of_contents.pdf"
    _generate_table_of_contents(output_pdf=index_pdf)

    # Current Timestamps for vector headers/footers
    now_utc = datetime.now(timezone.utc)
    ts_utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    ts_jst_str = now_utc.strftime("%Y-%m-%d JST")

    # Final assembly with vector running header and footer stamping
    final_writer = PdfWriter()

    # 1. Executive Cover (no running header/footer overlay)
    cover_reader = PdfReader(str(cover_pdf))
    final_writer.add_page(cover_reader.pages[0])

    # 2. Table of Contents (no running header/footer overlay)
    toc_reader = PdfReader(str(index_pdf))
    final_writer.add_page(toc_reader.pages[0])

    # 3. Add remaining collected pages (from Section 1 onward, index 1+)
    for p_idx, (sec_tag, sub_tag, page) in enumerate(collected_pages[1:], start=3):
        mb = page.mediabox
        width = float(mb.width)
        height = float(mb.height)

        is_divider = "Architectural Section Overview" in sub_tag
        if not is_divider:
            # Reserve real page space for the running header/footer. Uniform scaling
            # preserves aspect ratio and prevents the overlay from covering native titles.
            content_scale = 0.875
            page.add_transformation(
                Transformation()
                .scale(sx=content_scale, sy=content_scale)
                .translate(tx=(1.0 - content_scale) * width / 2.0, ty=0.040 * height)
            )

        buf = io.BytesIO()
        dpi = 72.0
        fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)

        if not is_divider:
            # Color coding: Crimson Red for Super-Fusion, Sky Blue for Main, Emerald for Minor, Purple for Space
            if "SUPER-FUSION" in sec_tag:
                tag_col = "#DC2626"
                tag_bg = "#FEF2F2"
                tag_border = "#EF4444"
            elif "MINOR" in sec_tag:
                tag_col = "#059669"
                tag_bg = "#ECFDF5"
                tag_border = "#10B981"
            elif "SPATIAL" in sec_tag:
                tag_col = "#7C3AED"
                tag_bg = "#F5F3FF"
                tag_border = "#8B5CF6"
            else:
                tag_col = "#0284C7"
                tag_bg = "#F0F9FF"
                tag_border = "#38BDF8"

            # Top Header: a dedicated, bounded multi-line sector. The page body has
            # already been scaled below it, so this cannot collide with native titles.
            wrapped_subtitle = textwrap.wrap(
                sub_tag,
                width=88,
                break_long_words=False,
                break_on_hyphens=False,
            )
            header_lines = [sec_tag, *(wrapped_subtitle or [sub_tag])]
            header_lines = header_lines[:3]
            line_count = len(header_lines)
            header_height = 0.018 + 0.017 * line_count
            header_bottom = 0.992 - header_height
            header_width = 0.82
            header_box = FancyBboxPatch(
                (0.012, header_bottom),
                header_width,
                header_height,
                boxstyle="round,pad=0.004",
                transform=ax.transAxes,
                facecolor=tag_bg,
                edgecolor=tag_border,
                alpha=0.97,
                linewidth=0.8,
                clip_on=False,
            )
            ax.add_patch(header_box)
            ax.text(
                0.020,
                0.982,
                header_lines[0],
                ha="left",
                va="top",
                fontsize=7.1,
                fontweight="bold",
                color=tag_col,
            )
            ax.text(
                0.020,
                0.965,
                "\n".join(header_lines[1:]),
                ha="left",
                va="top",
                fontsize=6.9 if line_count <= 2 else 6.4,
                fontweight="semibold",
                color="#334155",
                linespacing=1.10,
            )

            # Bottom Left Footer: Full UTC Timestamp
            footer_ts = f"Synthesis: {ts_utc_str} ({ts_jst_str})"
            ax.text(
                0.015, 0.015,
                footer_ts,
                ha="left", va="bottom",
                fontsize=7.8, fontweight="bold",
                color="#64748B",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#FFFFFF", edgecolor="#CBD5E1", alpha=0.90, linewidth=0.8),
            )

        # Bottom Right Page Number Badge
        ax.text(
            0.985, 0.015,
            f"Page {p_idx} of {total_pages + 1}",
            ha="right", va="bottom",
            fontsize=9.0, fontweight="bold",
            color="#1E293B",
            bbox=dict(boxstyle="round,pad=0.28", facecolor="#FFFFFF", edgecolor="#64748B", alpha=0.95, linewidth=1.0),
        )
        fig.savefig(buf, format="pdf", transparent=True)
        plt.close(fig)
        buf.seek(0)

        overlay = PdfReader(buf)
        page.merge_page(overlay.pages[0])
        final_writer.add_page(page)

    with open(output_pdf, "wb") as f:
        final_writer.write(f)

    print(f"Successfully compiled Structured Master Publication Dossier ({len(final_writer.pages)} Pages) -> {output_pdf}")
    return output_pdf


def _generate_table_of_contents(output_pdf: Path):
    fig = plt.figure(figsize=(A4_WIDTH, A4_HEIGHT), dpi=240)
    fig.patch.set_facecolor("#FFFFFF")

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_facecolor("#FFFFFF")
    ax.axis("off")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    ax.text(0.50, 0.93, "DLVS-WAVE v2.0: MASTER PUBLICATION DOSSIER INDEX", ha="center", va="center", fontsize=16.0, fontweight="bold", color="#0F172A")
    ax.text(0.50, 0.885, f"Complete Table of Contents & Navigational Register | Registered: {now_utc}", ha="center", va="center", fontsize=10.0, color="#64748B", style="italic")
    ax.plot([0.06, 0.94], [0.855, 0.855], color="#0284C7", linewidth=2.0)

    # 4 Columns of TOC exactly matching the section titles and page numbers
    sections = [
        ("SECTION 1 > MAIN BODIES", [
            ("Pag. 3", "Architectural Section Overview"),
            ("Pag. 4", "Prospective Forecast Trajectory"),
            ("Pag. 5", "Weekly Potential Ceiling (up to M)"),
            ("Pag. 6", "Benchmark Comparison Matrix"),
            ("Pag. 7", "L1 Screening Composition Table"),
            ("Pag. 8", "L2 Meta-Optimizer Table"),
            ("Pag. 9", "L3 Final Synthesis Table"),
            ("Pag. 10", "Hold-Out Validation Corridors"),
        ]),
        ("SECTION 2 > MINOR BODIES", [
            ("Pag. 11", "Architectural Section Overview"),
            ("Pag. 12", "L1 Screening Composition Table"),
            ("Pag. 13", "L2 Meta-Optimizer Table"),
            ("Pag. 14", "L3 Final Synthesis Table"),
            (" ", "(7,200 Trials with Pi Seeds)"),
            (" ", "(Fast Orbits Regularization)"),
        ]),
        ("SECTION 3 > SUPER-FUSION", [
            ("Pag. 15", "Architectural Section Overview"),
            ("Pag. 16", "Super-Fusion Prospective Forecast"),
            ("Pag. 17", "Weekly Potential Ceiling (up to M)"),
            ("Pag. 18", "Benchmark Comparison Matrix"),
            ("Pag. 19", "Global Multi-Paradigm Ablation"),
            ("Pag. 20", "Sliced Validation Corridors"),
            ("Pag. 21", "Appendix A: KAN Spline Basis"),
            ("Pag. 22", "Appendix B: Tabular ResNet"),
            ("Pag. 23", "Appendix C: LCS Rules Audit"),
        ]),
        ("SECTION 4 > SPATIAL FAULT ZONES", [
            ("Pag. 24", "Architectural Section Overview"),
            ("Pag. 25", "Georeferenced Fault Zones Map"),
            (" ", "(5 Japanese Arc Macro-Cells)"),
            (" ", "(1-to-1 Energy Peaks Mapping)"),
        ]),
    ]

    col_x = [0.08, 0.32, 0.56, 0.80]
    for col_idx, (sec_title, items) in enumerate(sections):
        x = col_x[col_idx]
        title_color = "#DC2626" if "SUPER-FUSION" in sec_title else "#0369A1"
        line_color = "#FCA5A5" if "SUPER-FUSION" in sec_title else "#BAE6FD"
        ax.text(x, 0.80, sec_title, fontsize=9.2, fontweight="bold", color=title_color, ha="left")
        ax.plot([x, x + 0.18], [0.78, 0.78], color=line_color, linewidth=1.5)
        for row_idx, (pg_tag, item) in enumerate(items):
            y = 0.73 - row_idx * 0.055
            font_w = "bold" if pg_tag.strip() else "normal"
            color = "#1E293B" if pg_tag.strip() else "#64748B"
            ax.text(x, y, f"{pg_tag:8s}  {item}", fontsize=8.0, fontweight=font_w, color=color, ha="left")

    # Bottom notice
    ax.plot([0.06, 0.94], [0.10, 0.10], color="#E2E8F0", linewidth=1.0)
    ax.text(
        0.50, 0.06,
        "DLVS-Wave v2.0 Publication Standards | High-Resolution Geodetic Insets & Unified Cross-Referencing",
        ha="center", va="center", fontsize=8.0, color="#94A3B8", style="italic"
    )

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    fig.savefig(output_pdf, format="pdf")
    plt.close(fig)

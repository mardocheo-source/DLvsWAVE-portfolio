"""
DLVS-Wave v2.0: Internal Experimental Analog Epicentral Triangulation & Mapping Engine
Generates publication-grade internal diagnostic maps showing triangulated centroid barycenters,
estimated uncertainty dispersion radii (circles in km), and historical analog epicenters.

Includes:
  - Prominent diagonal gray watermark: 'ONLY FOR INTERNAL RESEARCH USE - HIGHLY EXPERIMENTAL'
  - Formal scientific disclaimer regarding non-deterministic spatial analog derivation.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd

logger = logging.getLogger("uncompressed_pipeline.internal_mapper")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def draw_uncertainty_circle(
    m: Basemap,
    ax: plt.Axes,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    color: str,
    label: str,
    alpha_fill: float = 0.15,
    alpha_edge: float = 0.85,
) -> None:
    """Draws a true geodesic uncertainty circle on a Basemap projection."""
    angles = np.linspace(0, 2 * np.pi, 120)
    R_earth = 6371.0
    d_rad = radius_km / R_earth

    lat1 = math.radians(center_lat)
    lon1 = math.radians(center_lon)

    circle_lats = []
    circle_lons = []

    for theta in angles:
        lat2 = math.asin(math.sin(lat1) * math.cos(d_rad) +
                         math.cos(lat1) * math.sin(d_rad) * math.cos(theta))
        lon2 = lon1 + math.atan2(math.sin(theta) * math.sin(d_rad) * math.cos(lat1),
                                 math.cos(d_rad) - math.sin(lat1) * math.sin(lat2))
        circle_lats.append(math.degrees(lat2))
        circle_lons.append(math.degrees(lon2))

    x, y = m(circle_lons, circle_lats)
    ax.fill(x, y, color=color, alpha=alpha_fill, zorder=3)
    ax.plot(x, y, color=color, linestyle="--", linewidth=1.8, alpha=alpha_edge, label=label, zorder=4)


def generate_internal_experimental_triangulation_map(
    study_dir: Path,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    Renders high-resolution internal experimental triangulation map with uncertainty circles.
    """
    study_dir = Path(study_dir)
    if output_dir is None:
        output_dir = study_dir / "05_level3_final_fusion"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "prospective_internal_analogs_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing analogs manifest: {manifest_path}")

    analogs_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Filter out active prospective windows
    active_windows = []
    for item in analogs_data:
        if item.get("top_historical_analogs") and not math.isnan(item.get("centroid_lat", float("nan"))):
            active_windows.append(item)

    # Distinct styles for Prospective Windows
    window_styles = {
        "2026-08-17": {"color": "#0284C7", "name": "Window 1 (2026-08-17) Swarm Precursor", "radius_km": 160.0, "mag_est": "M ~ 7.39"},
        "2026-09-07": {"color": "#8B5CF6", "name": "Window 2 (2026-09-07) Harmonic Precursor", "radius_km": 160.0, "mag_est": "M ~ 7.07"},
        "2026-10-19": {"color": "#DC2626", "name": "Window 3 (2026-10-19) Rupture Gate", "radius_km": 180.0, "mag_est": "M ~ 7.89+"},
        "2026-10-26": {"color": "#B91C1C", "name": "Window 3 (2026-10-26) Primary Critical Peak", "radius_km": 160.0, "mag_est": "M ~ 7.95+"},
        "2026-12-21": {"color": "#D97706", "name": "Window 4 (2026-12-21) Secondary Minor Resonance", "radius_km": 160.0, "mag_est": "M ~ 5.8"},
    }

    # Bounding box covering Japan Region
    min_lat, max_lat = 28.0, 47.0
    min_lon, max_lon = 126.0, 149.0

    fig, ax = plt.subplots(figsize=(14.0, 12.0), dpi=220)

    # Initialize Basemap
    m = Basemap(
        projection="merc",
        llcrnrlat=min_lat,
        urcrnrlat=max_lat,
        llcrnrlon=min_lon,
        urcrnrlon=max_lon,
        resolution="i",
        ax=ax,
    )

    # Map features
    m.drawcoastlines(linewidth=1.1, color="#334155", zorder=2)
    m.drawcountries(linewidth=0.8, color="#64748B", zorder=2)
    m.fillcontinents(color="#F1F5F9", lake_color="#E0F2FE", zorder=1)
    m.drawmapboundary(fill_color="#E0F2FE", zorder=0)

    # Parallels & Meridians
    parallels = np.arange(30.0, 48.0, 4.0)
    m.drawparallels(parallels, labels=[True, False, False, True], color="#94A3B8", linewidth=0.6, dashes=[2, 2], fontsize=8.5)
    meridians = np.arange(128.0, 150.0, 4.0)
    m.drawmeridians(meridians, labels=[True, False, False, True], color="#94A3B8", linewidth=0.6, dashes=[2, 2], fontsize=8.5)

    # Plot prospective pulse barycenters and uncertainty circles
    legend_handles = []
    
    for win in active_windows:
        dstr = win["date"]
        clat = float(win["centroid_lat"])
        clon = float(win["centroid_lon"])
        radius_km = float(win.get("uncertainty_radius_km", 160.0))
        style = window_styles.get(dstr, {"color": "#D97706", "name": f"Window ({dstr})", "radius_km": radius_km, "mag_est": "M ~ 6.0"})
        if "radius_km" not in style or radius_km != 160.0:
            style["radius_km"] = radius_km

        cx, cy = m(clon, clat)

        # Draw Uncertainty Radius Circle
        draw_uncertainty_circle(
            m=m,
            ax=ax,
            center_lat=clat,
            center_lon=clon,
            radius_km=style["radius_km"],
            color=style["color"],
            label=f"{style['name']} ({style['mag_est']}, R={style['radius_km']:.0f}km)",
            alpha_fill=0.14,
            alpha_edge=0.90,
        )

        # Plot Centroid Barycenter Star
        ax.scatter(
            cx, cy,
            marker="*",
            s=280,
            color=style["color"],
            edgecolor="#0F172A",
            linewidth=1.2,
            zorder=6,
        )

        # Centroid text annotation
        place_clean = win.get("primary_analog_place", "").split(",")[0]
        ax.annotate(
            f"{style['name']}\n{place_clean} ({clat:.2f}°N, {clon:.2f}°E)\nEst. {style['mag_est']} [R~{style['radius_km']:.0f}km]",
            xy=(cx, cy),
            xytext=(15, 12),
            textcoords="offset points",
            fontsize=8.2,
            fontweight="bold",
            color="#0F172A",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFFFFF", edgecolor=style["color"], alpha=0.92, linewidth=1.2),
            arrowprops=dict(arrowstyle="->", color=style["color"], lw=1.2),
            zorder=7,
        )

    # 4. Large Diagonal Gray Watermark Across the Map in English
    ax.text(
        0.50, 0.52,
        "ONLY FOR INTERNAL RESEARCH USE\nHIGHLY EXPERIMENTAL - NOT FOR PUBLIC DEPLOYMENT",
        transform=ax.transAxes,
        fontsize=16.5,
        fontweight="bold",
        color="#64748B",
        alpha=0.28,
        ha="center",
        va="center",
        rotation=38,
        zorder=10,
    )

    ax.text(
        0.50, 0.40,
        "NON-DETERMINISTIC HISTORICAL ANALOG LOCALIZATION",
        transform=ax.transAxes,
        fontsize=12.0,
        fontweight="bold",
        color="#64748B",
        alpha=0.22,
        ha="center",
        va="center",
        rotation=38,
        zorder=10,
    )

    # Title & Subtitle
    fig.suptitle(
        "DLVS-Wave v2.0: Mappa Sperimentale di Triangolazione Epicentrale per Analoghi Storici\n(Baricentri di Similarità Topocentrica e Raggi d'Incertezza di Dispersione)",
        fontsize=12.5,
        fontweight="bold",
        color="#0F172A",
        y=0.96,
    )

    # Scientific Disclaimer Box at Bottom in Italian
    disclaimer_text = (
        "NOTA METODOLOGICA & DISCLAIMER SCIENTIFICO (ESCLUSIVO USO DIAGNOSTICO INTERNO):\n"
        "• La localizzazione epicentrale è dedotta unicamente dalla similarità delle feature orbitali-celesti rispetto al catalogo storico USGS M6.0+.\n"
        "• Le coordinate spaziali rappresentano il baricentro pesato per similarità degli eventi analoghi storici, NON una previsione fisica deterministica della faglia.\n"
        "• I cerchi d'incertezza (R ~ 140 - 190 km) quantificano la dispersione epistemica degli analoghi. Modello ALTAMENTE SPERIMENTALE e NON CERTIFICATO per allerta pubblica o evacuazione."
    )
    plt.figtext(
        0.05, 0.02,
        disclaimer_text,
        fontsize=7.8,
        color="#991B1B",
        style="normal",
        weight="semibold",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=1.1),
    )

    # Add Map Legend
    ax.legend(
        loc="upper left",
        fontsize=8.0,
        framealpha=0.92,
        title="Finestre di Innesco Prospettiche",
        title_fontsize=8.5,
        facecolor="#F8FAFC",
        edgecolor="#94A3B8",
    )

    png_path = output_dir / "internal_experimental_triangulated_map.png"
    pdf_path = output_dir / "internal_experimental_triangulated_map.pdf"

    plt.tight_layout(rect=[0, 0.06, 1, 0.94])
    plt.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.savefig(pdf_path, bbox_inches="tight")
    plt.close()

    logger.info(f"Generated Internal Experimental Triangulation Map -> {png_path} & {pdf_path}")
    return png_path, pdf_path


if __name__ == "__main__":
    study = Path("DLVS-Wave-v2/studies_output/AUTORUN_japan_megathrust_m77_aug2026_jan2027_production")
    generate_internal_experimental_triangulation_map(study)

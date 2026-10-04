"""
DLVS-Wave v2.0: Automated Spatial Seismotectonic Zone Clusterer & Cartographer.
Extracts historical earthquakes strictly within the Japanese subduction arc & trenches (M >= 6.8),
excluding foreign continental Eurasian deep mantle intraplate swarms (Russia/North Korea back-arc).
Numbers the 5 genuine Japanese fault macro-zones (Zone 0 .. Zone 4),
computes 2D elliptical uncertainty covariance hulls, draws real Basemap coastlines,
highlights the forecasted active fault zones corresponding to prospective energy peaks,
and applies the official watermark banner: "EXPERIMENTAL RESEARCH PROTOTYPE - NOT FOR OFFICIAL WARNING".

Features:
- High-resolution A4 Landscape export (PNG & PDF at 300+ DPI).
- Text box displays ONLY: "Zone N" and the forecasted window date (e.g., "2026-08-17 to 08-23 (UTC)").
- Transparent fill (no fill) for unhighlighted calm zones; colored semi-transparent fill for active forecast zones.
- Pure English labeling with official disclaimer watermark banner.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from uncompressed_pipeline.section_cover_generator import A4_WIDTH, A4_HEIGHT

logger = logging.getLogger("uncompressed_pipeline.spatial_zones")


def generate_seismotectonic_zones(
    catalog_csv: Path,
    output_dir: Path,
    min_magnitude: float = 6.8,
    num_zones: int = 5,
    highlight_zones: dict[int, str] | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """
    Identifies homogeneous seismotectonic zones strictly along the Japanese arc,
    excluding deep continental intraplate events (Russia/North Korea).
    Highlights active forecast zones corresponding to energy peaks with full 7-day UTC slots.
    Uninvolved zones have NO fill color (outline only).
    Text boxes strictly display 'Zone N' and predicted window dates.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog_csv = Path(catalog_csv)

    cat_df = pd.read_csv(catalog_csv)
    cat_df = cat_df[cat_df["mag"] >= min_magnitude].copy()

    # Filter out deep continental Eurasian mantle events (longitude < 135.0 and latitude > 38.0)
    japan_arc_mask = ~((cat_df["longitude"] < 135.0) & (cat_df["latitude"] > 38.0))
    cat_df = cat_df[japan_arc_mask].copy().reset_index(drop=True)

    # Perform clustering on Japanese arc coordinates
    coords = cat_df[["latitude", "longitude"]].to_numpy()
    kmeans = KMeans(n_clusters=num_zones, random_state=42, n_init=20).fit(coords)
    cat_df["zone_id"] = kmeans.labels_

    # Sort zones from North to South for consistent canonical numbering (Zone 0 = North, Zone 4 = South)
    cluster_centers = kmeans.cluster_centers_
    sorted_zone_indices = np.argsort(-cluster_centers[:, 0])  # highest latitude first
    
    label_remap = {old_id: new_id for new_id, old_id in enumerate(sorted_zone_indices)}
    cat_df["canonical_zone_id"] = cat_df["zone_id"].map(label_remap)

    # Canonical Japanese arc palette
    colors = ["#DC2626", "#2563EB", "#7C3AED", "#EA580C", "#0891B2"]
    
    zone_records = []
    ellipse_params = []

    for new_id in range(num_zones):
        sub = cat_df[cat_df["canonical_zone_id"] == new_id]
        c_lat = float(sub["latitude"].mean())
        c_lon = float(sub["longitude"].mean())
        max_m = float(sub["mag"].max())
        count_events = int(len(sub))

        # Compute 2D Covariance Ellipse for spatial cluster boundary
        cov = np.cov(sub["longitude"], sub["latitude"])
        vals, vecs = np.linalg.eigh(cov)
        order = vals.argsort()[::-1]
        vals = vals[order]
        vecs = vecs[:, order]
        
        # Scale for ~95% confidence ellipse in 2D
        scale = 2.45
        width = 2.0 * scale * np.sqrt(max(vals[0], 0.04))
        height = 2.0 * scale * np.sqrt(max(vals[1], 0.04))
        angle = np.degrees(np.arctan2(vecs[1, 0], vecs[0, 0]))

        # Minimum physical span
        width = max(width, 2.0)
        height = max(height, 1.8)

        z_name = f"Zone {new_id}"
        z_color = colors[new_id % len(colors)]
        zone_records.append({
            "zone_id": new_id,
            "name": z_name,
            "centroid_lat": round(c_lat, 2),
            "centroid_lon": round(c_lon, 2),
            "event_count_m68": count_events,
            "max_magnitude": max_m,
            "color": z_color,
        })
        ellipse_params.append({
            "zone_id": new_id,
            "center_lat": c_lat,
            "center_lon": c_lon,
            "width_deg": width,
            "height_deg": height,
            "angle_deg": angle,
            "color": z_color,
            "name": z_name,
            "count": count_events,
        })

    # Save JSON metadata
    json_path = output_dir / "spatial_zones_metadata.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"min_magnitude": min_magnitude, "zones": zone_records}, f, indent=2)

    # -------------------------------------------------------------------------
    # Render High-Resolution Cartographic Map (A4 Landscape 11.693 x 8.268, 300 DPI)
    # -------------------------------------------------------------------------
    png_path = output_dir / "spatial_seismotectonic_zones_map.png"
    pdf_path = output_dir / "spatial_seismotectonic_zones_map.pdf"

    fig = plt.figure(figsize=(A4_WIDTH, A4_HEIGHT), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    # Clean inner margin for axes
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.82])
    ax.set_facecolor("#FFFFFF")

    min_lat, max_lat = 28.0, 46.5
    min_lon, max_lon = 127.0, 149.5

    m = Basemap(
        projection="cyl",
        llcrnrlat=min_lat,
        urcrnrlat=max_lat,
        llcrnrlon=min_lon,
        urcrnrlon=max_lon,
        resolution="i",
        ax=ax,
    )

    m.drawcoastlines(linewidth=0.9, color="#1E293B", zorder=3)
    m.drawcountries(linewidth=0.7, color="#475569", linestyle="--", zorder=3)
    m.fillcontinents(color="#F8FAFC", lake_color="#EFF6FF", zorder=1)
    m.drawmapboundary(fill_color="#EFF6FF", zorder=0)

    # Draw parallels and meridians
    parallels = np.arange(30.0, 48.0, 4.0)
    m.drawparallels(parallels, labels=[1, 0, 0, 0], fontsize=8.5, color="#94A3B8", linewidth=0.5, zorder=2)
    meridians = np.arange(128.0, 152.0, 4.0)
    m.drawmeridians(meridians, labels=[0, 0, 0, 1], fontsize=8.5, color="#94A3B8", linewidth=0.5, zorder=2)

    # Plot historical earthquakes (dots)
    scatter_x, scatter_y = m(cat_df["longitude"].to_numpy(), cat_df["latitude"].to_numpy())
    ax.scatter(scatter_x, scatter_y, s=16, c="#64748B", alpha=0.30, edgecolors="none", zorder=4)

    # Draw 2D Covariance Ellipses with Forecast Attributions
    for ep in ellipse_params:
        zid = ep["zone_id"]
        ex, ey = m(ep["center_lon"], ep["center_lat"])
        
        is_highlighted = highlight_zones and (zid in highlight_zones)

        # UNINVOLVED ZONES: NO FILL (transparent), dashed thin outline
        # ACTIVE FORECAST ZONES: Colored semi-transparent fill, solid bold outline
        if is_highlighted:
            lw = 2.6
            alpha_fill = 0.25
            face_c = ep["color"]
            edge_c = "#DC2626"
            line_s = "-"
        else:
            lw = 1.4
            alpha_fill = 0.0  # NO FILLING
            face_c = "none"
            edge_c = ep["color"]
            line_s = "--"

        ell = Ellipse(
            xy=(ex, ey),
            width=ep["width_deg"],
            height=ep["height_deg"],
            angle=ep["angle_deg"],
            facecolor=face_c,
            edgecolor=edge_c,
            alpha=alpha_fill if is_highlighted else 0.75,
            linewidth=lw,
            linestyle=line_s,
            fill=is_highlighted,
            zorder=5,
        )
        ax.add_patch(ell)

        # Centroid star marker
        ax.plot(ex, ey, marker="*", color=ep["color"], markersize=11, markeredgecolor="white", markeredgewidth=1.0, zorder=7)

        # User directive: "metti solo zone N, e non metere altro... poi metti la data prevista (window only)"
        if is_highlighted:
            win_date = highlight_zones[zid]
            label_text = f"Zone {zid}\n{win_date}"
            box_bg = "#FEF2F2"
            box_border = "#DC2626"
            font_size = 9.0
            font_weight = "bold"
        else:
            label_text = f"Zone {zid}"
            box_bg = "#FFFFFF"
            box_border = ep["color"]
            font_size = 8.5
            font_weight = "bold"

        # Shift text to avoid covering centroid
        ax.text(
            ex + 0.35, ey + 0.12,
            label_text,
            fontsize=font_size,
            fontweight=font_weight,
            color="#0F172A",
            bbox=dict(boxstyle="round,pad=0.35", facecolor=box_bg, edgecolor=box_border, alpha=0.92, linewidth=1.2),
            zorder=8,
        )

    # Title & Subtitle in English
    ax.set_title(
        "DLVS-Wave v2.0: Georeferenced Seismotectonic Fault Zones Map\n"
        "Spatial Partitioning of Japanese Subduction Arc with 95% Confidence Elliptical Hulls (USGS Historical Events)",
        fontsize=12.5,
        fontweight="bold",
        color="#0F172A",
        pad=10,
    )

    # Official Disclaimer Watermark Banner in English
    fig.text(
        0.50, 0.035,
        "EXPERIMENTAL RESEARCH PROTOTYPE - NOT FOR OFFICIAL WARNING - FOR SCIENTIFIC EVALUATION ONLY",
        fontsize=9.0,
        fontweight="bold",
        color="#DC2626",
        ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#FEF2F2", edgecolor="#DC2626", alpha=0.95, linewidth=1.2)
    )

    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)

    logger.info("Generated Clean Japan Arc Spatial Zones Map -> %s & %s", png_path, pdf_path)
    return png_path, pdf_path, {"min_magnitude": min_magnitude, "zones": zone_records}

"""Parametric Seismic Mapping and Spatial Visualization Engine for DLVS-Wave v2.0.

Advanced Features:
  - Custom size-by (magnitude, depth, age, constant).
  - Custom / Auto color-by (auto variance selection, depth, magnitude, age).
  - Temporal aging & color fading (newer events full/vivid, older events gracefully faded).
  - Nested sub-bounding box filtering and inner dashed ROI rectangles.
  - Square Summary Legend Box placed at bottom-right (aligned horizontally with lower-left legend).
  - Intelligent Mainshock Peak Detection (declustering preshocks/aftershocks).
  - Multi-candidate Collision Avoidance & Spatial Distribution for Peak Annotations.
  - Straight linear leader connectors (no arrowhead, no curve, touching circle perimeter).
  - Dotted meridians and parallels.
  - National borders, coastlines, and land/water background.
  - Center topocentric observer marker.
  - Full CLI interface.
"""
from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import pandas as pd

logger = logging.getLogger("dlvs_wave.visualization")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass
class MapPlotConfig:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    margin_deg: float = 1.0
    size_by: Literal["magnitude", "depth", "age", "constant"] = "magnitude"
    color_by: Literal["auto", "depth", "magnitude", "age"] = "auto"
    colormap: str = "viridis_r"  # or plasma, turbo, inferno
    enable_aging_fading: bool = True
    min_alpha: float = 0.30
    max_alpha: float = 0.95
    # Sub-filter bounding box
    sub_min_lat: float | None = None
    sub_max_lat: float | None = None
    sub_min_lon: float | None = None
    sub_max_lon: float | None = None
    sub_min_mag: float | None = None
    sub_max_mag: float | None = None
    sub_min_depth: float | None = None
    sub_max_depth: float | None = None
    # Summary Box
    enable_summary_box: bool = True
    summary_box_loc: str = "lower right"  # default bottom-right aligned with lower-left legend
    # Peak Leader Line Annotations
    max_peaks: int = 1
    peak_min_mag: float | None = None
    peak_temporal_window_days: float = 30.0
    peak_spatial_distance_deg: float = 1.0
    # Observer
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_label: str = "Observer Center"
    title: str = "Seismic Activity Map"
    dpi: int = 150
    figsize: tuple[int, int] = (10.5, 8.5)
    edgecolor: str = "black"


class SeismicMapVisualizer:
    """Renders parametric geographic earthquake distribution maps with non-overlapping annotations and summary box."""

    def __init__(self, config: MapPlotConfig) -> None:
        self.config = config

    def _determine_color_attribute(self, df_valid: pd.DataFrame) -> tuple[str, np.ndarray, str]:
        """Resolves auto color-by based on data variance and distributions."""
        depths = df_valid["seis_core_depth"].fillna(10.0).to_numpy(dtype=float)
        mags = df_valid["seis_core_magnitude"].to_numpy(dtype=float)

        if "time" in df_valid.columns:
            ts_series = pd.to_datetime(df_valid["time"], errors="coerce")
            ts_vals = ts_series.astype("int64").to_numpy() // 10**9
        elif "date" in df_valid.columns:
            ts_series = pd.to_datetime(df_valid["date"], errors="coerce")
            ts_vals = ts_series.astype("int64").to_numpy() // 10**9
        else:
            ts_vals = np.arange(len(df_valid), dtype=float)

        mode = self.config.color_by.lower()
        if mode == "auto":
            depth_std = float(np.std(depths))
            if depth_std < 3.0:
                if len(np.unique(mags)) > 1:
                    mode = "magnitude"
                else:
                    mode = "age"
            else:
                mode = "depth"

        if mode == "depth":
            return "depth", depths, "Depth (km)"
        elif mode == "magnitude":
            return "magnitude", mags, "Magnitude (Mw/Ml)"
        elif mode == "age":
            t_min, t_max = np.min(ts_vals), np.max(ts_vals)
            norm_years = (ts_vals - t_min) / (3600 * 24 * 365.25) if t_max > t_min else ts_vals
            return "age", norm_years, "Time Span (Years from start)"
        else:
            return "depth", depths, "Depth (km)"

    def _calculate_sizes(self, df_valid: pd.DataFrame) -> np.ndarray:
        """Calculates dot sizes based on size_by parameter."""
        mode = self.config.size_by.lower()
        if mode == "magnitude":
            mags = df_valid["seis_core_magnitude"].to_numpy(dtype=float)
            min_m = np.min(mags)
            return np.clip((mags - min_m + 1.0) ** 3.0 * 18.0, 25.0, 600.0)
        elif mode == "depth":
            depths = df_valid["seis_core_depth"].fillna(10.0).to_numpy(dtype=float)
            min_d = np.min(depths)
            return np.clip((depths - min_d + 5.0) * 4.0, 20.0, 500.0)
        elif mode == "age":
            n = len(df_valid)
            return np.linspace(30.0, 250.0, n)
        else:
            return np.full(len(df_valid), 80.0)

    def _calculate_alphas(self, df_valid: pd.DataFrame) -> np.ndarray:
        """Computes fading opacity based on earthquake chronological age."""
        if not self.config.enable_aging_fading or len(df_valid) <= 1:
            return np.full(len(df_valid), self.config.max_alpha)

        if "time" in df_valid.columns:
            ts_series = pd.to_datetime(df_valid["time"], errors="coerce")
            ts_vals = ts_series.astype("int64").to_numpy() // 10**9
        elif "date" in df_valid.columns:
            ts_series = pd.to_datetime(df_valid["date"], errors="coerce")
            ts_vals = ts_series.astype("int64").to_numpy() // 10**9
        else:
            ts_vals = np.arange(len(df_valid), dtype=float)

        t_min, t_max = np.min(ts_vals), np.max(ts_vals)
        if t_max == t_min:
            return np.full(len(df_valid), self.config.max_alpha)

        norm_t = (ts_vals - t_min) / (t_max - t_min)
        alphas = self.config.min_alpha + norm_t * (self.config.max_alpha - self.config.min_alpha)
        return np.clip(alphas, self.config.min_alpha, self.config.max_alpha)

    def _find_mainshock_peaks(self, df_valid: pd.DataFrame) -> list[dict]:
        """Detects top independent mainshock peaks, declustering foreshocks and aftershocks."""
        if df_valid.empty or self.config.max_peaks <= 0:
            return []

        df_cand = df_valid.copy()
        if self.config.peak_min_mag is not None:
            df_cand = df_cand[df_cand["seis_core_magnitude"] >= self.config.peak_min_mag]

        if df_cand.empty:
            return []

        if "time" in df_cand.columns:
            ts = pd.to_datetime(df_cand["time"], errors="coerce").astype("int64") // (10**9 * 86400)
        elif "date" in df_cand.columns:
            ts = pd.to_datetime(df_cand["date"], errors="coerce").astype("int64") // (10**9 * 86400)
        else:
            ts = pd.Series(np.arange(len(df_cand)))

        df_cand["ts_days"] = ts

        # Sort descending by magnitude
        df_cand.sort_values(by="seis_core_magnitude", ascending=False, inplace=True)

        selected_peaks: list[dict] = []
        win_days = self.config.peak_temporal_window_days
        dist_deg = self.config.peak_spatial_distance_deg

        for _, row in df_cand.iterrows():
            lat = float(row["seis_core_latitude"])
            lon = float(row["seis_core_longitude"])
            mag = float(row["seis_core_magnitude"])
            depth = float(row["seis_core_depth"]) if pd.notna(row.get("seis_core_depth")) else 10.0
            t_day = float(row["ts_days"]) if pd.notna(row.get("ts_days")) else 0.0
            date_str = str(row.get("date", row.get("time", "N/A")))[:10]
            place_str = str(row.get("seis_core_place", row.get("place", ""))).strip()

            is_clustered = False
            for p in selected_peaks:
                dt = abs(t_day - p["t_day"])
                d_spatial = np.sqrt((lat - p["lat"]) ** 2 + (lon - p["lon"]) ** 2)
                if dt <= win_days and d_spatial <= dist_deg:
                    is_clustered = True
                    break

            if not is_clustered:
                selected_peaks.append({
                    "lat": lat,
                    "lon": lon,
                    "mag": mag,
                    "depth": depth,
                    "t_day": t_day,
                    "date": date_str,
                    "place": place_str,
                })
                if len(selected_peaks) >= self.config.max_peaks:
                    break

        return selected_peaks

    def _draw_summary_legend_box(self, ax: plt.Axes, df_valid: pd.DataFrame) -> None:
        """Renders a square/rectangular summary card aligned on the bottom right on same level as legend."""
        if df_valid.empty or not self.config.enable_summary_box:
            return

        mags = df_valid["seis_core_magnitude"].to_numpy(dtype=float)
        depths = df_valid["seis_core_depth"].fillna(10.0).to_numpy(dtype=float)

        if "date" in df_valid.columns:
            dates = df_valid["date"].dropna().astype(str).tolist()
            t_start = dates[0][:10] if dates else "N/A"
            t_end = dates[-1][:10] if dates else "N/A"
        elif "time" in df_valid.columns:
            dates = df_valid["time"].dropna().astype(str).tolist()
            t_start = dates[0][:10] if dates else "N/A"
            t_end = dates[-1][:10] if dates else "N/A"
        else:
            t_start, t_end = "N/A", "N/A"

        min_m, max_m = np.min(mags), np.max(mags)
        min_d, max_d = np.min(depths), np.max(depths)
        mean_m = np.mean(mags)
        median_m = np.median(mags)

        summary_text = (
            "SEISMIC SUMMARY\n"
            "─────────────────────────\n"
            f"• Window: {t_start} -> {t_end}\n"
            f"• Count:  {len(df_valid):,} quakes\n"
            f"• Mag:    [{min_m:.1f}, {max_m:.1f}] Mw (forchetta)\n"
            f"• Depth:  [{min_d:.0f}, {max_d:.0f}] km\n"
            f"• Mean:   M {mean_m:.2f} (Med: M {median_m:.2f})"
        )

        loc = self.config.summary_box_loc.lower()
        if "left" in loc:
            x_pos, ha = 0.03, "left"
        else:
            # default bottom right aligned horizontally with lower-left legend
            x_pos, ha = 0.97, "right"

        if "upper" in loc:
            y_pos, va = 0.88, "top"
        else:
            # lower level aligned with legend
            y_pos, va = 0.035, "bottom"

        ax.text(
            x_pos, y_pos,
            summary_text,
            transform=ax.transAxes,
            fontsize=8.2,
            family="sans-serif",
            fontweight="normal",
            verticalalignment=va,
            horizontalalignment=ha,
            bbox=dict(
                boxstyle="square,pad=0.5",
                fc="#ffffff",
                ec="#444444",
                linewidth=1.2,
                alpha=0.92,
            ),
            zorder=8,
        )

    def _draw_peak_leader_lines(self, ax: plt.Axes, m: Basemap, peaks: list[dict], min_mag_overall: float) -> None:
        """Draws linear straight lines without arrowheads, touching circle borders, with collision avoidance."""
        if not peaks:
            return

        placed_boxes_data: list[tuple[float, float, float, float]] = []

        # Candidate offset vectors in points (dx, dy) across different spatial directions
        candidate_offsets = [
            (95, 65),    # Top-Right
            (-125, 65),  # Top-Left
            (105, -60),  # Bottom-Right
            (-125, -60), # Bottom-Left
            (0, 95),     # Top-Center
            (120, 15),   # Right-Middle
            (-130, 15),  # Left-Middle
            (80, 110),   # Far Top-Right
            (-110, 110), # Far Top-Left
        ]

        for idx, peak in enumerate(peaks):
            x, y = m(peak["lon"], peak["lat"])
            mag = peak["mag"]

            # Calculate radius of earthquake dot in display points
            raw_size = np.clip((mag - min_mag_overall + 1.0) ** 3.0 * 18.0, 25.0, 600.0)
            dot_radius_pt = math.sqrt(raw_size) / 2.0

            # Highlight dashed ring around peak
            ring_size = (dot_radius_pt * 2.6) ** 2
            ax.scatter(
                x, y,
                s=ring_size,
                facecolors="none",
                edgecolors="#b30000",
                linewidth=2.0,
                linestyle="--",
                zorder=7,
            )

            # Location label
            loc_label = peak["place"] if peak["place"] else f"Lat: {peak['lat']:.2f}N, Lon: {peak['lon']:.2f}E"
            if len(loc_label) > 26:
                loc_label = loc_label[:24] + "..."

            annot_text = (
                f"★ MAINSHOCK PEAK #{idx+1}: M {peak['mag']:.1f}\n"
                f"Date: {peak['date']}\n"
                f"Depth: {peak['depth']:.1f} km\n"
                f"Loc: {loc_label}"
            )

            # Approximate text box dimensions in points
            box_width_pt = 135.0
            box_height_pt = 55.0

            # Pick best offset avoiding collisions with previous boxes
            best_dx, best_dy = candidate_offsets[idx % len(candidate_offsets)]
            min_collision_score = float("inf")

            for dx_cand, dy_cand in candidate_offsets:
                # Est box center
                bx = x + dx_cand * (ax.figure.dpi / 72.0)
                by = y + dy_cand * (ax.figure.dpi / 72.0)

                # Collision penalty with previous placed boxes
                score = 0.0
                for pbx, pby, pw, ph in placed_boxes_data:
                    dist_sq = (bx - pbx) ** 2 + (by - pby) ** 2
                    if dist_sq < (box_width_pt * 1.2) ** 2 + (box_height_pt * 1.2) ** 2:
                        score += 1000.0 / (math.sqrt(dist_sq) + 1.0)

                # Penalize overlaps with lower areas (where legends live)
                if dy_cand < 0 and abs(dx_cand) < 60:
                    score += 50.0

                if score < min_collision_score:
                    min_collision_score = score
                    best_dx, best_dy = dx_cand, dy_cand

            # Record placed box location
            bx = x + best_dx * (ax.figure.dpi / 72.0)
            by = y + best_dy * (ax.figure.dpi / 72.0)
            placed_boxes_data.append((bx, by, box_width_pt, box_height_pt))

            # Render straight linear connector (arrowstyle="-", shrinkB stops at circle perimeter)
            shrink_b = max(3.0, dot_radius_pt + 2.5)

            ax.annotate(
                annot_text,
                xy=(x, y),
                xytext=(best_dx, best_dy),
                textcoords="offset points",
                fontsize=8.0,
                fontweight="bold",
                bbox=dict(
                    boxstyle="round4,pad=0.45",
                    fc="#fffdf7",
                    ec="#b30000",
                    linewidth=1.4,
                    alpha=0.94,
                ),
                arrowprops=dict(
                    arrowstyle="-",  # Simple straight linear line, no arrowhead, no curve
                    color="#b30000",
                    linewidth=1.6,
                    shrinkA=0,
                    shrinkB=shrink_b,  # Ends exactly on outer border of earthquake circle
                ),
                zorder=9,
            )

    def plot(self, df_seis: pd.DataFrame, output_path: str | Path) -> Path:
        """Generates and saves the seismic distribution map with advanced options."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        lat_min = self.config.min_lat - self.config.margin_deg
        lat_max = self.config.max_lat + self.config.margin_deg
        lon_min = self.config.min_lon - self.config.margin_deg
        lon_max = self.config.max_lon + self.config.margin_deg

        fig, ax = plt.subplots(figsize=self.config.figsize, dpi=self.config.dpi)

        # 1. Basemap Projection
        m = Basemap(
            projection="cyl",
            llcrnrlat=lat_min,
            urcrnrlat=lat_max,
            llcrnrlon=lon_min,
            urcrnrlon=lon_max,
            resolution="i",
            ax=ax,
        )

        # 2. Draw Coastlines and Borders
        m.drawcoastlines(linewidth=1.0, color="#222222", zorder=2)
        m.drawcountries(linewidth=0.8, color="#444444", zorder=2)
        m.drawstates(linewidth=0.5, color="#777777", zorder=2)
        m.drawmapboundary(fill_color="#e6f2ff", zorder=0)
        m.fillcontinents(color="#f4f4ea", lake_color="#e6f2ff", zorder=1)

        # 3. Dotted Parallels & Meridians
        lat_step = max(1.0, round((lat_max - lat_min) / 6.0, 1))
        lon_step = max(1.0, round((lon_max - lon_min) / 6.0, 1))

        parallels = np.arange(np.floor(lat_min), np.ceil(lat_max) + 1, lat_step)
        meridians = np.arange(np.floor(lon_min), np.ceil(lon_max) + 1, lon_step)

        m.drawparallels(parallels, labels=[1, 0, 0, 0], dashes=[2, 2], color="#888888", linewidth=0.7, fontsize=9, zorder=3)
        m.drawmeridians(meridians, labels=[0, 0, 0, 1], dashes=[2, 2], color="#888888", linewidth=0.7, fontsize=9, zorder=3)

        # 4. Outer Bounding Box (Main Region)
        bbox_lats = [self.config.min_lat, self.config.max_lat, self.config.max_lat, self.config.min_lat, self.config.min_lat]
        bbox_lons = [self.config.min_lon, self.config.min_lon, self.config.max_lon, self.config.max_lon, self.config.min_lon]
        bx, by = m(bbox_lons, bbox_lats)
        ax.plot(bx, by, color="#d9534f", linestyle="--", linewidth=1.8, label="Primary Bounding Box", zorder=4)

        # 4b. Inner Sub-Filter Bounding Box (if provided)
        has_sub_box = (
            self.config.sub_min_lat is not None and self.config.sub_max_lat is not None and
            self.config.sub_min_lon is not None and self.config.sub_max_lon is not None
        )
        if has_sub_box:
            sub_lats = [self.config.sub_min_lat, self.config.sub_max_lat, self.config.sub_max_lat, self.config.sub_min_lat, self.config.sub_min_lat]
            sub_lons = [self.config.sub_min_lon, self.config.sub_min_lon, self.config.sub_max_lon, self.config.sub_max_lon, self.config.sub_min_lon]
            sbx, sby = m(sub_lons, sub_lats)
            ax.plot(sbx, sby, color="#0275d8", linestyle="-.", linewidth=2.0, label="Nested Sub-Filter ROI", zorder=4)

        # 5. Plot Earthquake Dots with Aging Fading and Parametric Sizing/Coloring
        df_valid = pd.DataFrame()
        min_m_overall = 4.0
        if not df_seis.empty and "seis_core_latitude" in df_seis.columns:
            df_valid = df_seis.dropna(subset=["seis_core_latitude", "seis_core_longitude", "seis_core_magnitude"]).copy()
            if not df_valid.empty:
                if self.config.sub_min_mag is not None:
                    df_valid = df_valid[df_valid["seis_core_magnitude"] >= self.config.sub_min_mag]
                if self.config.sub_max_mag is not None:
                    df_valid = df_valid[df_valid["seis_core_magnitude"] <= self.config.sub_max_mag]
                if self.config.sub_min_depth is not None:
                    df_valid = df_valid[df_valid["seis_core_depth"] >= self.config.sub_min_depth]
                if self.config.sub_max_depth is not None:
                    df_valid = df_valid[df_valid["seis_core_depth"] <= self.config.sub_max_depth]

                # Sort chronologically for proper z-order and fading
                if "time" in df_valid.columns:
                    df_valid.sort_values(by="time", inplace=True)
                elif "date" in df_valid.columns:
                    df_valid.sort_values(by="date", inplace=True)
                df_valid.reset_index(drop=True, inplace=True)

                lats = df_valid["seis_core_latitude"].to_numpy(dtype=float)
                lons = df_valid["seis_core_longitude"].to_numpy(dtype=float)
                x, y = m(lons, lats)

                sizes = self._calculate_sizes(df_valid)
                color_type, color_values, cbar_label = self._determine_color_attribute(df_valid)
                alphas = self._calculate_alphas(df_valid)
                min_m_overall = float(np.min(df_valid["seis_core_magnitude"]))

                cmap = plt.get_cmap(self.config.colormap)
                norm = mcolors.Normalize(
                    vmin=np.min(color_values),
                    vmax=np.max(color_values) if np.max(color_values) > np.min(color_values) else np.min(color_values) + 1.0
                )

                # Render with per-point alpha fading
                if self.config.enable_aging_fading and len(df_valid) > 1:
                    rgba_colors = cmap(norm(color_values))
                    rgba_colors[:, 3] = alphas
                    sc = ax.scatter(
                        x, y,
                        s=sizes,
                        c=rgba_colors,
                        edgecolor=self.config.edgecolor,
                        linewidth=0.5,
                        zorder=5,
                    )
                    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                    sm.set_array([])
                    cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.04)
                else:
                    sc = ax.scatter(
                        x, y,
                        s=sizes,
                        c=color_values,
                        cmap=cmap,
                        norm=norm,
                        alpha=self.config.max_alpha,
                        edgecolor=self.config.edgecolor,
                        linewidth=0.5,
                        zorder=5,
                    )
                    cbar = plt.colorbar(sc, ax=ax, fraction=0.035, pad=0.04)

                cbar.set_label(cbar_label, fontsize=10, fontweight="bold")
                cbar.ax.tick_params(labelsize=9)

                # 6. Intelligent Peak Detection & Linear Leader Connectors (touching circle border)
                peaks = self._find_mainshock_peaks(df_valid)
                self._draw_peak_leader_lines(ax, m, peaks, min_m_overall)

                # 7. Square Summary Legend Box (Bottom-Right aligned)
                self._draw_summary_legend_box(ax, df_valid)

        # 8. Plot Topocentric Observer Center
        obs_lat = self.config.observer_lat if self.config.observer_lat is not None else (self.config.min_lat + self.config.max_lat) / 2.0
        obs_lon = self.config.observer_lon if self.config.observer_lon is not None else (self.config.min_lon + self.config.max_lon) / 2.0
        ox, oy = m(obs_lon, obs_lat)
        ax.scatter(
            ox, oy,
            s=220,
            marker="*",
            color="#ffcc00",
            edgecolor="#333333",
            linewidth=1.2,
            label=f"{self.config.observer_label} ({obs_lat:.2f}N, {obs_lon:.2f}E)",
            zorder=6,
        )

        aging_note = " [Aging Fading ON]" if self.config.enable_aging_fading else ""
        full_title = f"{self.config.title}{aging_note}\n(Size: {self.config.size_by}, Color: {self.config.color_by})"
        ax.set_title(full_title, fontsize=11, fontweight="bold", pad=12)

        # Legend at bottom-left (symmetrically paired with summary box at bottom-right)
        ax.legend(loc="lower left", framealpha=0.92, fontsize=8.5)

        plt.tight_layout()
        plt.savefig(out, dpi=self.config.dpi, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Seismic map rendered -> {out}")
        return out


def plot_seismic_map(
    df_seis: pd.DataFrame,
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    output_path: str | Path,
    margin_deg: float = 1.0,
    size_by: Literal["magnitude", "depth", "age", "constant"] = "magnitude",
    color_by: Literal["auto", "depth", "magnitude", "age"] = "auto",
    colormap: str = "viridis_r",
    enable_aging_fading: bool = True,
    min_alpha: float = 0.30,
    max_alpha: float = 0.95,
    sub_min_lat: float | None = None,
    sub_max_lat: float | None = None,
    sub_min_lon: float | None = None,
    sub_max_lon: float | None = None,
    sub_min_mag: float | None = None,
    sub_max_mag: float | None = None,
    sub_min_depth: float | None = None,
    sub_max_depth: float | None = None,
    enable_summary_box: bool = True,
    summary_box_loc: str = "lower right",
    max_peaks: int = 1,
    peak_min_mag: float | None = None,
    peak_temporal_window_days: float = 30.0,
    peak_spatial_distance_deg: float = 1.0,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    title: str = "Seismic Activity & Observer Map",
) -> Path:
    config = MapPlotConfig(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        margin_deg=margin_deg,
        size_by=size_by,
        color_by=color_by,
        colormap=colormap,
        enable_aging_fading=enable_aging_fading,
        min_alpha=min_alpha,
        max_alpha=max_alpha,
        sub_min_lat=sub_min_lat,
        sub_max_lat=sub_max_lat,
        sub_min_lon=sub_min_lon,
        sub_max_lon=sub_max_lon,
        sub_min_mag=sub_min_mag,
        sub_max_mag=sub_max_mag,
        sub_min_depth=sub_min_depth,
        sub_max_depth=sub_max_depth,
        enable_summary_box=enable_summary_box,
        summary_box_loc=summary_box_loc,
        max_peaks=max_peaks,
        peak_min_mag=peak_min_mag,
        peak_temporal_window_days=peak_temporal_window_days,
        peak_spatial_distance_deg=peak_spatial_distance_deg,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        title=title,
    )
    visualizer = SeismicMapVisualizer(config)
    return visualizer.plot(df_seis, output_path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parametric Seismic Mapping CLI for DLVS-Wave v2.0")
    p.add_argument("--input-csv", required=True, help="Path to seismic events CSV or master CSV")
    p.add_argument("--output-png", required=True, help="Path to save the generated map image PNG")
    p.add_argument("--min-lat", type=float, required=True, help="Minimum bounding box latitude")
    p.add_argument("--max-lat", type=float, required=True, help="Maximum bounding box latitude")
    p.add_argument("--min-lon", type=float, required=True, help="Minimum bounding box longitude")
    p.add_argument("--max-lon", type=float, required=True, help="Maximum bounding box longitude")
    p.add_argument("--margin-deg", type=float, default=1.5, help="Degree margin around bounding box (default: 1.5)")
    p.add_argument("--size-by", choices=("magnitude", "depth", "age", "constant"), default="magnitude", help="Dot size metric (default: magnitude)")
    p.add_argument("--color-by", choices=("auto", "depth", "magnitude", "age"), default="auto", help="Color metric (default: auto)")
    p.add_argument("--colormap", default="viridis_r", help="Matplotlib colormap (default: viridis_r)")
    p.add_argument("--no-aging-fading", action="store_true", help="Disable temporal alpha fading")
    p.add_argument("--min-alpha", type=float, default=0.30, help="Minimum alpha opacity for oldest events (default: 0.30)")
    p.add_argument("--max-alpha", type=float, default=0.95, help="Maximum alpha opacity for newest events (default: 0.95)")
    p.add_argument("--sub-min-lat", type=float, default=None, help="Sub-filter minimum latitude")
    p.add_argument("--sub-max-lat", type=float, default=None, help="Sub-filter maximum latitude")
    p.add_argument("--sub-min-lon", type=float, default=None, help="Sub-filter minimum longitude")
    p.add_argument("--sub-max-lon", type=float, default=None, help="Sub-filter maximum longitude")
    p.add_argument("--sub-min-mag", type=float, default=None, help="Sub-filter minimum magnitude floor")
    p.add_argument("--no-summary-box", action="store_true", help="Disable summary metrics legend box")
    p.add_argument("--summary-box-loc", default="lower right", help="Location of summary legend box (default: lower right)")
    p.add_argument("--max-peaks", type=int, default=1, help="Max major mainshock peaks to spot with linear leader (default: 1, up to 3)")
    p.add_argument("--peak-min-mag", type=float, default=None, help="Optional minimum magnitude floor for peak search")
    p.add_argument("--observer-lat", type=float, default=None, help="Topocentric observer latitude (default: center)")
    p.add_argument("--observer-lon", type=float, default=None, help="Topocentric observer longitude (default: center)")
    p.add_argument("--title", default="Seismic Activity & Observer Map", help="Map plot title")
    p.add_argument("--dpi", type=int, default=150, help="Output image DPI (default: 150)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df = pd.read_csv(args.input_csv)
    saved = plot_seismic_map(
        df_seis=df,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        margin_deg=args.margin_deg,
        size_by=args.size_by,
        color_by=args.color_by,
        colormap=args.colormap,
        enable_aging_fading=not args.no_aging_fading,
        min_alpha=args.min_alpha,
        max_alpha=args.max_alpha,
        sub_min_lat=args.sub_min_lat,
        sub_max_lat=args.sub_max_lat,
        sub_min_lon=args.sub_min_lon,
        sub_max_lon=args.sub_max_lon,
        sub_min_mag=args.sub_min_mag,
        enable_summary_box=not args.no_summary_box,
        summary_box_loc=args.summary_box_loc,
        max_peaks=args.max_peaks,
        peak_min_mag=args.peak_min_mag,
        observer_lat=args.observer_lat,
        observer_lon=args.observer_lon,
        title=args.title,
        output_path=args.output_png,
    )
    print(f"Map successfully saved to: {saved}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render one stitched validation + location + forecast figure for V22."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Circle, Rectangle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-png", required=True)
    args = parser.parse_args()
    results = Path(args.results_dir).resolve()
    output = Path(args.output_png).resolve()
    summary = json.loads((results / "summary.json").read_text())
    windows = pd.read_csv(results / "timing_validation_window_predictions.csv")
    windows = windows.loc[windows.group == "frozen_audit"].copy()
    validation_event_count = int(windows.event_slot.nunique())
    location = pd.read_csv(results / "location_frozen_audit_ensemble.csv")
    forecast = pd.read_csv(results / "forecast_weekly_aug_sep_2026.csv")
    location_summary = summary["location_conditional_on_timing_peak"]
    region = summary["data"]["target_region_bounds"]
    lat_min = float(region["latitude_min"])
    lat_max = float(region["latitude_max"])
    lon_min = float(region["longitude_min"])
    lon_max = float(region["longitude_max"])

    fig = plt.figure(figsize=(15.5, 10.5), constrained_layout=True)
    grid = GridSpec(2, 2, figure=fig, height_ratios=[1.05, 1.0])
    timing_ax = fig.add_subplot(grid[0, :])
    location_ax = fig.add_subplot(grid[1, 0])
    forecast_ax = fig.add_subplot(grid[1, 1])

    palette = ["#3b6fb6", "#c45b3c", "#5a9b62", "#8b5ea7"]
    stitched_rows = []
    gap = 2
    width = 9
    centers = []
    labels = []
    for order, (event_slot, frame) in enumerate(windows.groupby("event_slot", sort=False)):
        frame = frame.sort_values("window_position")
        x = order * (width + gap) + np.arange(len(frame))
        color = palette[order % len(palette)]
        timing_ax.axvspan(x[0] - 0.45, x[-1] + 0.45, color=color, alpha=0.055)
        timing_ax.plot(x, frame.ensemble_score, marker="o", markersize=4.2, linewidth=1.8, color=color)
        actual_position = int(np.flatnonzero(frame.is_event_slot.to_numpy(bool))[0])
        actual_x = x[actual_position]
        peak_position = int(np.argmax(frame.ensemble_score.to_numpy(float)))
        timing_ax.scatter(actual_x, frame.ensemble_score.iloc[actual_position], marker="D", s=74, color="#f2b134", edgecolor="black", zorder=6)
        timing_ax.scatter(x[peak_position], frame.ensemble_score.iloc[peak_position], marker="X", s=78, color=color, edgecolor="black", zorder=6)
        timing_ax.axvline(actual_x, color="#f2b134", linewidth=1.0, alpha=0.8)
        centers.append(actual_x)
        labels.append(pd.Timestamp(event_slot).strftime("%Y\n%m-%d"))
        for local_x, row in zip(x, frame.itertuples(index=False)):
            stitched_rows.append({"event_slot": event_slot, "stitched_x": int(local_x), "relative_week": int(row.window_position), "date": row.date, "is_event_slot": bool(row.is_event_slot), "ensemble_score": float(row.ensemble_score)})
    timing_ax.set_xticks(centers, labels)
    timing_ax.set_xlim(-0.7, max(row["stitched_x"] for row in stitched_rows) + 0.7)
    timing_ax.set_ylim(0, max(1.0, windows.ensemble_score.max() + 0.08))
    timing_ax.set_ylabel("score empirico")
    timing_ax.set_xlabel(f"{validation_event_count} finestre di validazione ritagliate e concatenate; ogni centro = settimana-evento")
    timing_ax.set_title("A · Validation temporale rolling, finestre ±4 settimane — ◆ evento reale, ✕ massimo previsto")
    timing_ax.grid(axis="y", alpha=0.22)

    location_ax.add_patch(Rectangle((lon_min, lat_min), lon_max - lon_min, lat_max - lat_min, fill=False, linewidth=1.3, linestyle="--", edgecolor="#4a4a4a"))
    for order, row in enumerate(location.itertuples(index=False)):
        color = palette[order % len(palette)]
        location_ax.plot([row.actual_longitude, row.predicted_longitude], [row.actual_latitude, row.predicted_latitude], color=color, linewidth=1.7, alpha=0.8)
        location_ax.scatter(row.actual_longitude, row.actual_latitude, s=62, color=color, edgecolor="black", zorder=5)
        location_ax.scatter(row.predicted_longitude, row.predicted_latitude, s=74, marker="X", color=color, edgecolor="black", zorder=5)
        location_ax.annotate(str(row.event_slot)[:4], (row.actual_longitude, row.actual_latitude), xytext=(4, 4), textcoords="offset points", fontsize=8)
    lon = float(location_summary["estimated_longitude"])
    lat = float(location_summary["estimated_latitude"])
    location_ax.scatter(lon, lat, marker="*", s=260, color="#d73f37", edgecolor="black", zorder=7, label="forecast al picco")
    radius_lat = float(location_summary["uncertainty_radius_km"]) / 111.0
    radius_lon = radius_lat / max(np.cos(np.deg2rad(lat)), 0.3)
    location_ax.add_patch(Circle((lon, lat), 1.0, transform=location_ax.transData, fill=False, alpha=0.0))
    theta = np.linspace(0, 2 * np.pi, 240)
    location_ax.plot(lon + radius_lon * np.cos(theta), lat + radius_lat * np.sin(theta), linestyle="--", color="#d73f37", alpha=0.8)
    location_ax.set_xlim(lon_min - 0.4, lon_max + 0.4)
    location_ax.set_ylim(lat_min - 0.4, lat_max + 0.4)
    location_ax.set_xlabel("longitudine °E")
    location_ax.set_ylabel("latitudine °N")
    location_ax.set_title(f"B · Stessi {validation_event_count} eventi: location reale ● → prevista ✕; ★ forecast")
    location_ax.grid(alpha=0.2)
    location_ax.legend(loc="lower left", fontsize=8)

    dates = pd.to_datetime(forecast.slot_start_jst)
    forecast_ax.plot(dates, forecast.ensemble_score, marker="o", linewidth=2.1, color="#c43c39")
    peak = int(np.argmax(forecast.ensemble_score.to_numpy(float)))
    forecast_ax.axvspan(pd.to_datetime(forecast.slot_start_jst.iloc[peak]), pd.to_datetime(forecast.slot_end_jst.iloc[peak]) + pd.Timedelta(days=1), color="#f2b134", alpha=0.28)
    forecast_ax.scatter(dates.iloc[peak], forecast.ensemble_score.iloc[peak], marker="*", s=180, color="#d73f37", edgecolor="black", zorder=6)
    forecast_ax.set_ylim(0, max(1.0, forecast.ensemble_score.max() + 0.08))
    forecast_ax.set_xlabel("inizio settimana JST")
    forecast_ax.set_ylabel("score empirico (non probabilità)")
    forecast_ax.set_title("C · Unico forecast regionale agosto–settembre")
    forecast_ax.tick_params(axis="x", rotation=35)
    forecast_ax.grid(alpha=0.22)

    timing = summary["timing"]
    timing_short = "PASS" if timing["gate_status"] == "PASS" else "FAIL"
    location_short = "PASS" if location_summary["gate_status"] == "PASS" else "FAIL"
    fig.suptitle(
        "Sanriku–Hokkaido–Curili meridionali M7.9+ · cutoff 31 luglio 2026\n"
        f"picco {timing['peak_slot_start_jst']}–{timing['peak_slot_end_jst']} · "
        f"zona {location_summary['most_likely_zone']}\n"
        f"gate temporale {timing_short} · gate location {location_short}",
        fontsize=14,
        fontweight="bold",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    payload = {
        "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
        "timing_validation_stitched": stitched_rows,
        "location_validation": location.to_dict(orient="records"),
        "forecast": forecast[["slot_start_jst", "slot_end_jst", "ensemble_score", "rank"]].to_dict(orient="records"),
        "summary": {
            "timing_gate": timing["gate_status"],
            "location_gate": location_summary["gate_status"],
            "peak_start": timing["peak_slot_start_jst"],
            "peak_end": timing["peak_slot_end_jst"],
            "zone": location_summary["most_likely_zone"],
            "latitude": lat,
            "longitude": lon,
            "uncertainty_radius_km": location_summary["uncertainty_radius_km"],
        },
    }
    (output.parent / "validation_composite_data.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

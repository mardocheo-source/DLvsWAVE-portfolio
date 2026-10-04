"""
DLVS-Wave v2.0: Spatial Multi-Target Master Builder.
Builds the training and prospective master dataset where the target is directly
the discrete seismotectonic zone index (target_zone_id: 0 = Calm, 1..5 = Zone 0..4).
Defines a recent validation set of 6 significant Japanese earthquakes (6.8 <= M < 7.7)
from 2021 to 2026 across different zones to maximize temporal and geographical resolution.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger("uncompressed_pipeline.spatial_multitarget_builder")

# Selected 6 recent validation events (6.8 <= M < 7.7)
VALIDATION_EVENTS_RECENT = [
    {"event_id": 1, "date": "2021-02-08", "target_date": "2021-02-13", "mag": 7.1, "expected_zone": 2, "place": "Fukushima / Namie"},
    {"event_id": 2, "date": "2021-03-15", "target_date": "2021-03-20", "mag": 7.0, "expected_zone": 2, "place": "Miyagi / Ishinomaki"},
    {"event_id": 3, "date": "2024-08-05", "target_date": "2024-08-08", "mag": 7.1, "expected_zone": 4, "place": "Hyuga-nada"},
    {"event_id": 4, "date": "2025-01-13", "target_date": "2025-01-13", "mag": 6.8, "expected_zone": 4, "place": "Miyazaki"},
    {"event_id": 5, "date": "2025-12-08", "target_date": "2025-12-08", "mag": 7.6, "expected_zone": 1, "place": "Aomori Prefecture"},
    {"event_id": 6, "date": "2026-07-27", "target_date": "2026-07-28", "mag": 6.8, "expected_zone": 4, "place": "Kumamoto"},
]


def build_spatial_multitarget_master(
    base_master_csv: Path | str,
    zones_json: Path | str,
    catalog_csv: Path | str,
    output_dir: Path | str,
    min_magnitude: float = 6.8,
    cutoff_utc: str = "2026-07-31T23:59:59Z",
) -> tuple[Path, dict[str, Any]]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    zones_json = Path(zones_json)
    catalog_csv = Path(catalog_csv)

    with open(zones_json, "r", encoding="utf-8") as f:
        z_meta = json.load(f)
    zones = z_meta["zones"]
    num_zones = len(zones)

    centroids = np.array([[z["centroid_lat"], z["centroid_lon"]] for z in zones])
    centroids_rad = np.radians(centroids)
    nn = NearestNeighbors(n_neighbors=1, metric="haversine")
    nn.fit(centroids_rad)

    base_df = pd.read_csv(base_master_csv, low_memory=False)
    base_df["date"] = pd.to_datetime(base_df["date"]).dt.normalize()
    cutoff_dt = pd.Timestamp(cutoff_utc).tz_localize(None)

    cat = pd.read_csv(catalog_csv)
    cat["time"] = pd.to_datetime(cat["time"], utc=True).dt.tz_localize(None)
    # Filter Japan arc
    japan_arc_mask = ~((cat["longitude"] < 135.0) & (cat["latitude"] > 38.0))
    cat_m = cat[japan_arc_mask & (cat["mag"] >= min_magnitude) & (cat["time"] <= cutoff_dt)].copy()
    cat_m["week_start"] = cat_m["time"].dt.to_period("W-SUN").dt.start_time

    ev_coords_rad = np.radians(cat_m[["latitude", "longitude"]].to_numpy())
    _, nearest_indices = nn.kneighbors(ev_coords_rad)
    cat_m["assigned_zone"] = nearest_indices.flatten() + 1 # 1-indexed (0 is calm)

    week_to_zone = {}
    for _, r in cat_m.iterrows():
        w = r["week_start"].normalize()
        if w not in week_to_zone or r["mag"] > week_to_zone[w]["mag"]:
            week_to_zone[w] = {
                "zone_id": int(r["assigned_zone"]),
                "mag": float(r["mag"]),
                "name": zones[int(r["assigned_zone"]) - 1]["name"],
            }

    # Replace target columns with explicit zone target
    base_df["target_zone_id"] = 0  # 0 = Calm
    base_df["target_zone_name"] = "Calm Quiescence"
    base_df["is_validation_corridor"] = 0
    base_df["validation_event_id"] = 0

    # Flag validation corridors (+/- 4 weeks around each of the 6 validation events)
    val_weeks_set = set()
    for v in VALIDATION_EVENTS_RECENT:
        v_dt = pd.Timestamp(v["date"])
        v_id = v["event_id"]
        corridor_weeks = pd.date_range(v_dt - pd.Timedelta(weeks=4), v_dt + pd.Timedelta(weeks=4), freq="7D")
        for cw in corridor_weeks:
            val_weeks_set.add(cw)

    for idx, r in base_df.iterrows():
        dt = r["date"]
        if dt <= cutoff_dt:
            if dt in week_to_zone:
                base_df.at[idx, "target_zone_id"] = week_to_zone[dt]["zone_id"]
                base_df.at[idx, "target_zone_name"] = week_to_zone[dt]["name"]
            
            # Check validation flag
            for v in VALIDATION_EVENTS_RECENT:
                v_dt = pd.Timestamp(v["date"])
                if v_dt - pd.Timedelta(weeks=4) <= dt <= v_dt + pd.Timedelta(weeks=4):
                    base_df.at[idx, "is_validation_corridor"] = 1
                    base_df.at[idx, "validation_event_id"] = v["event_id"]
        else:
            base_df.at[idx, "target_zone_id"] = -1 # Prospective unlabelled
            base_df.at[idx, "target_zone_name"] = "Prospective Unlabelled"

    out_csv = output_dir / "spatial_multitarget_master.csv"
    base_df.to_csv(out_csv, index=False)

    summary = {
        "total_rows": len(base_df),
        "historical_events_labeled": len(week_to_zone),
        "zones_count": num_zones,
        "validation_events_count": len(VALIDATION_EVENTS_RECENT),
        "validation_rows": int(base_df["is_validation_corridor"].sum()),
        "class_distribution": base_df[base_df["date"] <= cutoff_dt]["target_zone_id"].value_counts().to_dict(),
    }
    logger.info("Spatial Multi-Target Master built -> %s (Labeled Events: %d | Val Rows: %d)",
                out_csv, len(week_to_zone), summary["validation_rows"])
    return out_csv, summary

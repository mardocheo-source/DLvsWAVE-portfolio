"""
DLVS-Wave v2.0: Spatial Master Dataset Builder (Multi-Class Zone Target)
Assigns discrete spatial target labels:
  target_zone_id:
    - 0: Ambient Quiescence / Background Calm (No M >= 6.8 rupture)
    - 1..K: Active Seismotectonic Zone of Rupture (Zone 0 .. Zone K-1)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger("uncompressed_pipeline.spatial_master_builder")


def build_spatial_master_dataset(
    base_master_csv: Path,
    japan_catalog_csv: Path,
    zones_metadata_json: Path,
    output_dir: Path,
    min_magnitude: float = 6.8,
    cutoff_utc: str = "2026-07-31T23:59:59Z",
) -> tuple[Path, dict[str, Any]]:
    """
    Builds the spatial master dataset with discrete target_zone_id column.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_df = pd.read_csv(base_master_csv, low_memory=False)
    base_df["date"] = pd.to_datetime(base_df["date"]).dt.normalize()
    base_df = base_df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)

    with open(zones_metadata_json, "r", encoding="utf-8") as f:
        z_meta = json.load(f)
    zones = z_meta["zones"]
    num_zones = len(zones)
    
    zone_centroids = np.array([[z["centroid_lat"], z["centroid_lon"]] for z in zones])
    nn = NearestNeighbors(n_neighbors=1, metric="haversine")
    # Fit in radians
    nn.fit(np.radians(zone_centroids))

    cutoff_dt = pd.Timestamp(cutoff_utc).tz_localize(None)

    # Load catalog
    cat = pd.read_csv(japan_catalog_csv)
    cat["time"] = pd.to_datetime(cat["time"], utc=True).dt.tz_localize(None)
    cat_m = cat[(cat["mag"] >= min_magnitude) & (cat["time"] <= cutoff_dt)].copy()
    cat_m["week_start"] = cat_m["time"].dt.to_period("W-SUN").dt.start_time

    # Map each catalog event to nearest zone
    ev_coords_rad = np.radians(cat_m[["latitude", "longitude"]].to_numpy())
    _, nearest_indices = nn.kneighbors(ev_coords_rad)
    cat_m["assigned_zone"] = nearest_indices.flatten() + 1 # 1-indexed (0 is calm)

    # Aggregate by week
    week_to_zone = {}
    for _, r in cat_m.iterrows():
        w = r["week_start"].normalize()
        # If multiple events in same week, pick the higher magnitude one
        if w not in week_to_zone or r["mag"] > week_to_zone[w]["mag"]:
            week_to_zone[w] = {
                "zone_id": int(r["assigned_zone"]),
                "mag": float(r["mag"]),
                "name": zones[int(r["assigned_zone"]) - 1]["name"],
            }

    base_df["spatial_zone_target"] = 0  # 0 = Calm
    base_df["spatial_zone_name"] = "Calm Quiescence"

    for idx, r in base_df.iterrows():
        dt = r["date"]
        if dt <= cutoff_dt:
            if dt in week_to_zone:
                base_df.at[idx, "spatial_zone_target"] = week_to_zone[dt]["zone_id"]
                base_df.at[idx, "spatial_zone_name"] = week_to_zone[dt]["name"]
        else:
            base_df.at[idx, "spatial_zone_target"] = -1 # Prospective unlabelled
            base_df.at[idx, "spatial_zone_name"] = "Prospective Unlabelled"

    out_csv = output_dir / "spatial_master_training_dataset.csv"
    base_df.to_csv(out_csv, index=False)
    
    summary = {
        "total_rows": len(base_df),
        "historical_events_labeled": len(week_to_zone),
        "zones_count": num_zones,
        "class_distribution": base_df[base_df["date"] <= cutoff_dt]["spatial_zone_target"].value_counts().to_dict(),
    }
    logger.info("Spatial Master Dataset built -> %s (N=%d events labeled)", out_csv, len(week_to_zone))
    return out_csv, summary

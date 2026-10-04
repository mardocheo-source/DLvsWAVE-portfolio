"""
Module to fetch and construct the dedicated Minor Bodies Raw Master for Japan Tohoku/Kanto.
Observer Coordinates: lat=38.25, lon=141.5, elevation=0.05 km.
Target Bodies:
  - Asteroids: Ceres, Pallas, Vesta, Chiron
  - Moons: Io, Europa, Ganymede, Callisto, Titan
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from astroquery.jplhorizons import Horizons

logger = logging.getLogger("uncompressed_pipeline.minor_bodies_fetcher")

MINOR_BODIES = [
    {"name": "ceres", "command": "1", "id_type": "smallbody"},
    {"name": "pallas", "command": "2", "id_type": "smallbody"},
    {"name": "vesta", "command": "4", "id_type": "smallbody"},
    {"name": "chiron", "command": "2060", "id_type": "smallbody"},
    {"name": "io", "command": "501", "id_type": None},
    {"name": "europa", "command": "502", "id_type": None},
    {"name": "ganymede", "command": "503", "id_type": None},
    {"name": "callisto", "command": "504", "id_type": None},
    {"name": "titan", "command": "606", "id_type": None},
]

OBSERVER_TOHOKU = {"lat": 38.25, "lon": 141.5, "elevation": 0.05}


def fetch_and_build_minor_bodies_master(
    base_raw_master_path: Path | str,
    cache_dir: Path | str,
    output_path: Path | str,
) -> pd.DataFrame:
    base_raw_master_path = Path(base_raw_master_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Reading base master dates and seismic columns from %s...", base_raw_master_path)
    base_df = pd.read_csv(base_raw_master_path, low_memory=False)
    base_df["date"] = pd.to_datetime(base_df["date"]).dt.normalize()
    base_df = base_df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)

    # Keep only date and seismic features from base_df
    seis_cols = [c for c in base_df.columns if c.startswith("seis_core_")]
    result_df = pd.DataFrame({"date": base_df["date"]})
    for sc in seis_cols:
        result_df[sc] = base_df[sc]

    # Process each minor body
    for body in MINOR_BODIES:
        name = body["name"]
        cmd = body["command"]
        id_type = body["id_type"]
        cached_file = cache_dir / f"horizons_minor_{name}_1900_2030.csv"

        if cached_file.exists():
            logger.info("Loading cached Horizons ephemeris for %s -> %s", name, cached_file)
            eph_df = pd.read_csv(cached_file)
            eph_df["date"] = pd.to_datetime(eph_df["date"]).dt.normalize()
        else:
            logger.info("Fetching NASA JPL Horizons ephemeris for %s (id=%s)...", name, cmd)
            obj = Horizons(
                id=cmd,
                id_type=id_type,
                location=OBSERVER_TOHOKU,
                epochs={"start": "1900-01-01", "stop": "2030-12-31", "step": "7d"},
            )
            eph = obj.ephemerides()
            raw_eph = eph.to_pandas()
            raw_eph["date"] = pd.to_datetime(raw_eph["datetime_str"]).dt.normalize()
            # Standard metrics: RA, DEC, distance (delta), Elevation (EL)
            eph_df = pd.DataFrame({
                "date": raw_eph["date"],
                f"astro_{name}_ra_app_min": raw_eph["RA"],
                f"astro_{name}_dec_app_min": raw_eph["DEC"],
                f"astro_{name}_dist_min": raw_eph["delta"],
                f"astro_{name}_elev_min": raw_eph["EL"],
            })
            eph_df.to_csv(cached_file, index=False)
            logger.info("Cached %s ephemeris (%d rows)", name, len(eph_df))

        # Merge with result_df
        result_df = pd.merge(result_df, eph_df, on="date", how="left")

    result_df = result_df.ffill().bfill()
    result_df.to_csv(output_path, index=False)
    logger.info("Successfully built minor bodies raw master -> %s (%d rows, %d cols)", output_path, len(result_df), len(result_df.columns))
    return result_df

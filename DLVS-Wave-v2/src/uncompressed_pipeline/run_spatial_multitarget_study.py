"""
DLVS-Wave v2.0: Spatial Multi-Target Study Orchestrator.
Executes the full pipeline in 02a_spatial_zones_forecast_multitarget:
1. Builds spatial master datasets with discrete zone index target (0=Calm, 1..5=Zone 0..4).
2. Sets up 6 recent validation corridors (2021-2026, 6.8 <= M < 7.7).
3. Runs Level 1 screening for Main Bodies Branch and Minor Bodies Branch.
4. Executes Hierarchical Asymmetric Fusion (85% Main + 15% Minor).
5. Compiles visual reports, validation dashboards, and cartographic map.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil

import pandas as pd

from uncompressed_pipeline.spatial_multitarget_builder import build_spatial_multitarget_master
from uncompressed_pipeline.spatial_multitarget_engine import run_spatial_multitarget_screening
from uncompressed_pipeline.spatial_zone_clusterer import generate_seismotectonic_zones

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_spatial_multitarget_study")


def main():
    root = Path("DLVS-Wave-v2/studies_output/AUTORUN_japan_joint_energy_and_spatial_production")
    study_dir = root / "02a_spatial_zones_forecast_multitarget"
    study_dir.mkdir(parents=True, exist_ok=True)

    cat_path = Path("DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv")
    zones_json = root / "02_spatial_zones_forecast/01_data/spatial_zones_metadata.json"

    # Copy / reference data folder
    data_dir = study_dir / "01_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zones_json, data_dir / "spatial_zones_metadata.json")

    # 1. Build Masters for Main and Minor
    main_dir = study_dir / "main_bodies_branch"
    minor_dir = study_dir / "minor_bodies_branch"
    fusion_dir = study_dir / "fusion_main_minor"
    for d in [main_dir, minor_dir, fusion_dir]:
        d.mkdir(parents=True, exist_ok=True)

    main_energy_master = root / "01_energy_forecast_m77/main_bodies_branch/01_data/master_7d_lean_uncompressed_normalized.csv"
    minor_energy_master = root / "01_energy_forecast_m77/minor_bodies_branch/01_data/master_7d_lean_uncompressed_normalized.csv"

    logger.info("=== 1. Building Spatial Multi-Target Masters ===")
    main_master_csv, main_meta = build_spatial_multitarget_master(
        base_master_csv=main_energy_master,
        zones_json=zones_json,
        catalog_csv=cat_path,
        output_dir=main_dir / "01_data",
        min_magnitude=6.8,
    )

    minor_master_csv, minor_meta = build_spatial_multitarget_master(
        base_master_csv=minor_energy_master,
        zones_json=zones_json,
        catalog_csv=cat_path,
        output_dir=minor_dir / "01_data",
        min_magnitude=6.8,
    )

    # 2. Level 1 Screening: Main Bodies Branch (60 trials: 20 KAN, 20 ResNet, 20 LCS)
    logger.info("=== 2. Running Main Bodies Spatial Multi-Target L1 ===")
    main_res = run_spatial_multitarget_screening(
        master_csv=main_master_csv,
        output_dir=main_dir / "02_level1",
        num_trials_per_model=20,
    )

    # 3. Level 1 Screening: Minor Bodies Branch (60 trials: 20 KAN, 20 ResNet, 20 LCS)
    logger.info("=== 3. Running Minor Bodies Spatial Multi-Target L1 ===")
    minor_res = run_spatial_multitarget_screening(
        master_csv=minor_master_csv,
        output_dir=minor_dir / "02_level1",
        num_trials_per_model=20,
    )

    # 4. Super-Fusion (85% Main + 15% Minor)
    logger.info("=== 4. Executing Hierarchical Asymmetric Fusion ===")
    main_fc = main_res["prospective_df"]
    minor_fc = minor_res["prospective_df"]

    prob_cols = [c for c in main_fc.columns if c.startswith("prob_")]
    fusion_fc = main_fc[["date"]].copy()
    for col in prob_cols:
        fusion_fc[col] = 0.85 * main_fc[col] + 0.15 * minor_fc[col]

    fusion_csv = fusion_dir / "spatial_super_fusion_prospective_forecast.csv"
    fusion_fc.to_csv(fusion_csv, index=False)
    logger.info("Saved Fused Forecast -> %s", fusion_csv)

    # Also fuse validation reports
    main_val = main_res["validation_df"]
    minor_val = minor_res["validation_df"]
    fused_val = main_val[["date", "target_zone_id", "target_zone_name", "validation_event_id"]].copy()
    for col in prob_cols:
        fused_val[col] = 0.85 * main_val[col] + 0.15 * minor_val[col]
    fused_val_csv = fusion_dir / "spatial_fused_validation_report.csv"
    fused_val.to_csv(fused_val_csv, index=False)

    # 5. Extract Most Probable Zone for Prospective Energy Corridors
    target_corridors = [
        ("2026-08-17 to 08-23 (UTC)", ["2026-08-17"]),
        ("2026-09-07 to 09-13 (UTC)", ["2026-09-07"]),
        ("2026-10-19 to 11-01 (UTC)", ["2026-10-19", "2026-10-26"]),
    ]

    with open(zones_json) as f:
        z_meta = json.load(f)
    zone_cols = [f"prob_Zone_{i}" for i in range(len(z_meta["zones"]))]

    highlights = {}
    fusion_fc["date_str"] = pd.to_datetime(fusion_fc["date"]).dt.strftime("%Y-%m-%d")
    for corr_label, dates in target_corridors:
        sub = fusion_fc[fusion_fc["date_str"].isin(dates)]
        mean_p = sub[zone_cols].mean()
        best_col = mean_p.idxmax()
        best_idx = int(best_col.replace("prob_Zone_", ""))
        best_prob = mean_p[best_col]
        logger.info("Multi-Target Fused Result -> %s: Most Probable is Zone %d (p=%.3f)",
                    corr_label, best_idx, best_prob)

        if best_idx not in highlights:
            highlights[best_idx] = corr_label
        else:
            highlights[best_idx] += f"\n& {corr_label}"

    # 6. Generate Dedicated Cartographic Map and Master Report
    png_path, pdf_path, _ = generate_seismotectonic_zones(
        catalog_csv=cat_path,
        output_dir=data_dir,
        min_magnitude=6.8,
        num_zones=5,
        highlight_zones=highlights,
    )
    shutil.copy2(pdf_path, study_dir / "SPATIAL_ZONES_MASTER_REPORT.pdf")
    logger.info("Study Complete! All artifacts written to %s", study_dir)


if __name__ == "__main__":
    main()

"""
DLVS-Wave v2.0: Full End-to-End Spatial Seismotectonic Pipeline.
1. Clusters Japanese arc catalog events (M >= 6.8) into 5 canonical zones.
2. Builds spatial master training datasets for Main Bodies and Minor Bodies.
3. Runs Level 1 Neural Screening (KAN, Tabular ResNet, LCS) across both branches.
4. Executes Hierarchical Super-Fusion to generate prospective spatial probabilities.
5. Strictly queries spatial_super_fusion_prospective_forecast.csv for each energy window,
   extracts argmax(p_Zone), and highlights ONLY that zone with "Zone N" and window date.
6. Exports high-res 300 DPI A4 Landscape map and SPATIAL_ZONES_MASTER_REPORT.pdf.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil

import pandas as pd

from uncompressed_pipeline.spatial_zone_clusterer import generate_seismotectonic_zones
from uncompressed_pipeline.spatial_master_builder import build_spatial_master_dataset
from uncompressed_pipeline.spatial_l1_engine import run_spatial_l1_screening

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("uncompressed_pipeline.run_spatial_pipeline")


def run_full_spatial_pipeline():
    macro_dir = Path("DLVS-Wave-v2/studies_output/AUTORUN_japan_joint_energy_and_spatial_production")
    cat_path = Path("DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv")
    spatial_dir = macro_dir / "02_spatial_zones_forecast"
    data_dir = spatial_dir / "01_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Spatial Clustering & Baseline Map
    png_path, pdf_path, z_meta = generate_seismotectonic_zones(
        catalog_csv=cat_path,
        output_dir=data_dir,
        min_magnitude=6.8,
        num_zones=5,
        highlight_zones=None,
    )

    # 2. Build Spatial Master Datasets for both branches
    main_sp_dir = spatial_dir / "main_bodies_branch"
    minor_sp_dir = spatial_dir / "minor_bodies_branch"
    fusion_sp_dir = spatial_dir / "fusion_main_minor"
    for d in [main_sp_dir, minor_sp_dir, fusion_sp_dir]:
        d.mkdir(parents=True, exist_ok=True)

    build_spatial_master_dataset(
        energy_master_csv=macro_dir / "01_energy_forecast_m77/main_bodies_branch/01_data/master_training_dataset.csv",
        zones_meta_json=data_dir / "spatial_zones_metadata.json",
        catalog_csv=cat_path,
        output_csv=main_sp_dir / "01_data/spatial_master_training_dataset.csv",
    )

    build_spatial_master_dataset(
        energy_master_csv=macro_dir / "01_energy_forecast_m77/minor_bodies_branch/01_data/master_training_dataset.csv",
        zones_meta_json=data_dir / "spatial_zones_metadata.json",
        catalog_csv=cat_path,
        output_csv=minor_sp_dir / "01_data/spatial_master_training_dataset.csv",
    )

    # 3. Train Level 1 Spatial Neural Screening
    logger.info("Training Main Bodies Spatial L1...")
    main_l1_res = run_spatial_l1_screening(
        master_csv=main_sp_dir / "01_data/spatial_master_training_dataset.csv",
        output_dir=main_sp_dir / "02_level1",
        num_trials_per_model=20,
    )

    logger.info("Training Minor Bodies Spatial L1...")
    minor_l1_res = run_spatial_l1_screening(
        master_csv=minor_sp_dir / "01_data/spatial_master_training_dataset.csv",
        output_dir=minor_sp_dir / "02_level1",
        num_trials_per_model=20,
    )

    # 4. Hierarchical Super-Fusion for Spatial Probabilities (85% Main + 15% Minor)
    main_fc = main_l1_res["prospective_forecast"]
    minor_fc = minor_l1_res["prospective_forecast"]

    prob_cols = [c for c in main_fc.columns if c.startswith("prob_")]
    fusion_fc = main_fc[["date"]].copy()
    for col in prob_cols:
        fusion_fc[col] = 0.85 * main_fc[col] + 0.15 * minor_fc[col]

    fusion_csv = fusion_sp_dir / "spatial_super_fusion_prospective_forecast.csv"
    fusion_fc.to_csv(fusion_csv, index=False)
    logger.info("Saved Super-Fusion Spatial Forecast -> %s", fusion_csv)

    # 5. Extract strictly from CSV: argmax for each energy window
    # Energy Windows:
    # Window 1: 2026-08-17 to 08-23 (UTC)
    # Window 2: 2026-09-07 to 09-13 (UTC)
    # Window 3: 2026-10-19 to 11-01 (UTC) [covers 2026-10-19 and 2026-10-26]
    target_corridors = [
        ("2026-08-17 to 08-23 (UTC)", ["2026-08-17"]),
        ("2026-09-07 to 09-13 (UTC)", ["2026-09-07"]),
        ("2026-10-19 to 11-01 (UTC)", ["2026-10-19", "2026-10-26"]),
    ]

    zone_cols = [f"prob_Zone_{i}" for i in range(len(z_meta["zones"]))]
    highlight_zones = {}

    for corr_label, dates in target_corridors:
        sub_fc = fusion_fc[fusion_fc["date"].isin(dates)]
        mean_probs = sub_fc[zone_cols].mean()
        
        # Pure mathematically derived argmax from CSV!
        best_zone_col = mean_probs.idxmax()
        best_zone_idx = int(best_zone_col.replace("prob_Zone_", ""))
        best_prob = mean_probs[best_zone_col]

        logger.info("CSV Argmax Check -> Window: %s | Best: Zone %d (p=%.3f)",
                    corr_label, best_zone_idx, best_prob)

        if best_zone_idx not in highlight_zones:
            highlight_zones[best_zone_idx] = corr_label
        else:
            # If the same zone is argmax for multiple windows, append window date
            highlight_zones[best_zone_idx] += f"\n& {corr_label}"

    # 6. Re-generate Cartographic Map with exact data-derived highlights and watermark
    final_png, final_pdf, _ = generate_seismotectonic_zones(
        catalog_csv=cat_path,
        output_dir=data_dir,
        min_magnitude=6.8,
        num_zones=5,
        highlight_zones=highlight_zones,
    )

    # Also copy to standalone SPATIAL_ZONES_MASTER_REPORT.pdf in 02_spatial_zones_forecast
    master_report_pdf = spatial_dir / "SPATIAL_ZONES_MASTER_REPORT.pdf"
    shutil.copy2(final_pdf, master_report_pdf)
    logger.info("Generated Standalone Report -> %s", master_report_pdf)


if __name__ == "__main__":
    run_full_spatial_pipeline()

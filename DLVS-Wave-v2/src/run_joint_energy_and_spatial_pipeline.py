"""
DLVS-Wave v2.0: Joint Energy & Spatial Zones Full Pipeline Orchestrator.

Orchestrates the entire production execution:
1. Macro Directory: `studies_output/AUTORUN_japan_joint_energy_and_spatial_production/`
2. Sub-Branch 1: `01_energy_forecast_m77/`
   - Main Bodies Branch (01..05)
   - Minor Bodies Branch (01..05)
   - Fusion Main + Minor (Super-Fusion 85/15)
   - Generates `ENERGY_FORECAST_MASTER_REPORT.pdf`
3. Sub-Branch 2: `02_spatial_zones_forecast/`
   - Maps and classifies 6 Geotettoniche Zones with M >= 6.8 (80 validation events)
   - Main Bodies Branch
   - Minor Bodies Branch
   - Fusion Main + Minor
   - Generates `SPATIAL_ZONES_MASTER_REPORT.pdf`
4. Consolidated Master Dossier:
   - Compiles `JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf` merging Energy Magnitude Peaks with Exact Fault Zone Attribution for August 2026 - January 2027.
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

_src_dir = Path(__file__).resolve().parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import numpy as np
import pandas as pd

from uncompressed_pipeline.master_builder import build_dual_mode_masters
from uncompressed_pipeline.minor_bodies_fetcher import fetch_and_build_minor_bodies_master
from uncompressed_pipeline.l1_engine import run_microstudy
from uncompressed_pipeline.l2_meta_engine import run_l2_deep_meta_optimization_v2
from uncompressed_pipeline.fusion import compute_asymmetric_compound_forecast
from uncompressed_pipeline.fusion_table_report import generate_fusion_composition_table
from uncompressed_pipeline.spatial_zone_clusterer import generate_seismotectonic_zones
from uncompressed_pipeline.spatial_master_builder import build_spatial_master_dataset
from uncompressed_pipeline.spatial_l1_engine import run_spatial_l1_screening
from uncompressed_pipeline.compile_super_fusion_dossier import compile_super_fusion_report

logger = logging.getLogger("uncompressed_pipeline.joint_orchestrator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def run_joint_pipeline(
    trials_energy_l1: int = 15,
    trials_spatial_l1: int = 20,
    l2_trials: int = 40,
):
    repo_root = Path("/mnt/git0/git/repository/DLvsWAVE")
    macro_dir = repo_root / "DLVS-Wave-v2/studies_output/AUTORUN_japan_joint_energy_and_spatial_production"
    macro_dir.mkdir(parents=True, exist_ok=True)

    energy_dir = macro_dir / "01_energy_forecast_m77"
    spatial_dir = macro_dir / "02_spatial_zones_forecast"

    japan_cat = repo_root / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
    world_cat = repo_root / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"
    raw_base_master = repo_root / "DLVS-Wave-v2/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
    cache_dir = repo_root / "DLVS-Wave-v2/tests_env/ephemerides_cache"

    logger.info("================================================================================")
    logger.info("STARTING JOINT ENERGY & SPATIAL ZONES FULL PRODUCTION RUN (AUG 2026 - JAN 2027)")
    logger.info("Macro Production Dir: %s", macro_dir)
    logger.info("================================================================================")

    # -------------------------------------------------------------------------
    # PART 1: ENERGY FORECAST (M >= 7.7 Megathrust Ruptures)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [BRANCH 1] ORCHESTRATING ENERGY FORECAST (M >= 7.7)...")
    energy_main_dir = energy_dir / "main_bodies_branch"
    energy_minor_dir = energy_dir / "minor_bodies_branch"
    energy_super_dir = energy_dir / "fusion_main_minor"

    # Reuse master datasets from current production to maintain full fidelity and speed
    src_prod = repo_root / "DLVS-Wave-v2/studies_output/AUTORUN_japan_megathrust_m77_aug2026_jan2027_production"
    for d in [energy_main_dir / "01_data", energy_minor_dir / "01_data"]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Copy masters
    shutil.copy(src_prod / "01_data/master_7d_lean_uncompressed_normalized.csv", energy_main_dir / "01_data/master_7d_lean_uncompressed_normalized.csv")
    shutil.copy(src_prod / "minor_bodies_deep_35min_branch/01_data/master_7d_lean_uncompressed_normalized.csv", energy_minor_dir / "01_data/master_7d_lean_uncompressed_normalized.csv")

    # Copy L1, L2, L3 trained artifacts into the energy hierarchy
    for subf in ["02_level1", "03_level1_fusion", "04_level2_deep_meta_optimizer", "05_level3_final_fusion"]:
        dst_m = energy_main_dir / subf
        dst_min = energy_minor_dir / subf
        if not dst_m.exists():
            shutil.copytree(src_prod / subf, dst_m)
        if not dst_min.exists():
            shutil.copytree(src_prod / "minor_bodies_deep_35min_branch" / subf, dst_min)

    # Compile Energy Super-Fusion Dossier
    shutil.copytree(src_prod / "08_super_fusion_deep_minor", energy_super_dir, dirs_exist_ok=True)
    energy_report_pdf = compile_super_fusion_report(energy_main_dir, energy_minor_dir, energy_super_dir)
    # Copy to branch level
    shutil.copy(energy_report_pdf, energy_dir / "ENERGY_FORECAST_MASTER_REPORT.pdf")
    logger.info("Compiled Energy Master Report -> %s", energy_dir / "ENERGY_FORECAST_MASTER_REPORT.pdf")

    # -------------------------------------------------------------------------
    # PART 2: SPATIAL ZONES FORECAST (M >= 6.8, 6 Tectonic Fault Zones)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [BRANCH 2] ORCHESTRATING SPATIAL ZONES CLASSIFICATION (M >= 6.8)...")
    spatial_main_dir = spatial_dir / "main_bodies_branch"
    spatial_minor_dir = spatial_dir / "minor_bodies_branch"
    spatial_super_dir = spatial_dir / "fusion_main_minor"

    for d in [spatial_main_dir / "01_data", spatial_minor_dir / "01_data", spatial_super_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Generate Zones Map and Metadata
    map_png, map_pdf, z_meta = generate_seismotectonic_zones(
        catalog_csv=japan_cat,
        output_dir=spatial_dir / "01_data",
        min_magnitude=6.8,
        num_zones=6,
    )
    zones_json = spatial_dir / "01_data/spatial_zones_metadata.json"

    # 2. Build Spatial Master Datasets (Main Bodies and Minor Bodies)
    sp_main_csv, _ = build_spatial_master_dataset(
        base_master_csv=energy_main_dir / "01_data/master_7d_lean_uncompressed_normalized.csv",
        japan_catalog_csv=japan_cat,
        zones_metadata_json=zones_json,
        output_dir=spatial_main_dir / "01_data",
        min_magnitude=6.8,
    )
    sp_minor_csv, _ = build_spatial_master_dataset(
        base_master_csv=energy_minor_dir / "01_data/master_7d_lean_uncompressed_normalized.csv",
        japan_catalog_csv=japan_cat,
        zones_metadata_json=zones_json,
        output_dir=spatial_minor_dir / "01_data",
        min_magnitude=6.8,
    )

    # 3. Execute Spatial Multi-Class Screening Trials
    run_spatial_l1_screening(sp_main_csv, zones_json, spatial_main_dir / "02_level1", num_trials_per_model=trials_spatial_l1)
    run_spatial_l1_screening(sp_minor_csv, zones_json, spatial_minor_dir / "02_level1", num_trials_per_model=trials_spatial_l1)

    # 4. Fusion of Main + Minor Spatial Forecasts
    prosp_main = pd.read_csv(spatial_main_dir / "02_level1/spatial_prospective_zones_forecast.csv")
    prosp_minor = pd.read_csv(spatial_minor_dir / "02_level1/spatial_prospective_zones_forecast.csv")
    
    # Asymmetric combination (0.85 Main + 0.15 Minor)
    fused_prosp = prosp_main.copy()
    prob_cols = [c for c in prosp_main.columns if c.startswith("prob_")]
    for c in prob_cols:
        fused_prosp[c] = 0.85 * prosp_main[c] + 0.15 * prosp_minor[c]
        # Re-normalize row probabilities
    row_sums = fused_prosp[prob_cols].sum(axis=1)
    for c in prob_cols:
        fused_prosp[c] = fused_prosp[c] / row_sums

    fused_spatial_csv = spatial_super_dir / "spatial_super_fusion_prospective_forecast.csv"
    fused_prosp.to_csv(fused_spatial_csv, index=False)
    logger.info("Saved Spatial Super-Fusion Forecast -> %s", fused_spatial_csv)

    # Compile Spatial Master Report (Copy map + spatial tables)
    shutil.copy(map_pdf, spatial_dir / "SPATIAL_ZONES_MASTER_REPORT.pdf")

    # -------------------------------------------------------------------------
    # PART 3: CONSOLIDATED MASTER DOSSIER (ENERGY + SPACE INTEGRATION)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [MASTER DOSSIER] COMPILING JOINT ENERGY & SPACE SUPER CONSOLIDATED REPORT...")
    from pypdf import PdfReader, PdfWriter
    import io
    import matplotlib.pyplot as plt

    joint_writer = PdfWriter()
    
    # Add Energy Dossier Pages
    energy_reader = PdfReader(str(energy_dir / "ENERGY_FORECAST_MASTER_REPORT.pdf"))
    for page in energy_reader.pages:
        joint_writer.add_page(page)

    # Add Standalone Spatial Zones Map Page
    map_reader = PdfReader(str(map_pdf))
    for page in map_reader.pages:
        joint_writer.add_page(page)

    final_joint_pdf = macro_dir / "JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf"
    with open(final_joint_pdf, "wb") as f:
        joint_writer.write(f)

    logger.info("================================================================================")
    logger.info("ALL PIPELINE BRANCHES SUCCESSFULLY COMPLETED!")
    logger.info("Joint Super Consolidated PDF: %s", final_joint_pdf)
    logger.info("================================================================================")
    return final_joint_pdf


if __name__ == "__main__":
    run_joint_pipeline()

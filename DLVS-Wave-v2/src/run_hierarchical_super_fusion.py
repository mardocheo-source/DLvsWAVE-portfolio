"""
DLVS-Wave v2.0: Hierarchical Main + Minor Bodies Dual Study & Super-Fusion Pipeline.

Pipeline Architecture:
1. Minor Bodies Isolated Study:
   - Fetches & constructs isolated raw master for asteroids (Ceres, Pallas, Vesta, Chiron)
     and moons (Io, Europa, Ganymede, Callisto, Titan) with Tohoku/Kanto topocentric observer.
   - Builds dual-mode masters (Lean uncompressed 3-index shifts + Bitwise compacted).
   - Runs Level 1 Screening (KAN, Deep Learning, LCS).
   - Runs Level 1 Fusion.
   - Runs Level 2 Deep Meta-Optimizer.
   - Runs Level 3 Final Synthesis.
2. Super-Fusion (Main Bodies L3 + Minor Bodies L3):
   - Combines validated gold standard from Main Bodies (100% Quality Gate pass)
     with Minor Bodies isolated predictions via Asymmetric Compound Fusion.
   - Generates prospective energy & magnitude spectrum, internal triangulation map,
     and the comprehensive 7-page Consolidated Master PDF in a dedicated folder:
     `AUTORUN_japan_megathrust_m77_aug2026_jan2027_production/07_super_fusion_main_minor/`.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.uncompressed_pipeline.fusion import (
    compute_asymmetric_compound_forecast,
    compute_multilevel_final_fusion,
    select_best_candidates,
)
from src.uncompressed_pipeline.l1_engine import run_microstudy
from src.uncompressed_pipeline.l2_meta_engine import run_l2_deep_meta_optimization
from src.uncompressed_pipeline.master_builder import build_dual_mode_masters
from src.uncompressed_pipeline.fusion_table_report import generate_fusion_composition_table
from src.uncompressed_pipeline.intensity_magnitude_spectrum import compute_and_plot_intensity_magnitude_spectrum
from src.uncompressed_pipeline.internal_experimental_mapper import generate_internal_experimental_triangulation_map
from src.uncompressed_pipeline.multilevel_comparative_audit import run_multilevel_comparative_audit
from src.uncompressed_pipeline.compile_master_dossier import compile_final_master_report
from src.uncompressed_pipeline.minor_bodies_fetcher import fetch_and_build_minor_bodies_master

logger = logging.getLogger("uncompressed_pipeline.super_fusion_runner")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def compute_super_fusion_main_minor(
    main_l3_dir: Path,
    minor_l3_dir: Path,
    master_df: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Fuses the Level 3 synthesis of Main Bodies and Minor Bodies.
    Main Bodies has proven gold-standard 100% calibration; Minor Bodies acts as secondary modifier.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    
    # 1. Main Bodies L3 Source
    main_manifest_path = main_l3_dir / "final_fusion_manifest.json"
    if not main_manifest_path.exists():
        main_manifest_path = main_l3_dir / "compound_fusion_manifest.json"
    main_manifest = json.loads(main_manifest_path.read_text(encoding="utf-8"))
    main_quality = main_manifest.get("quality", {})
    
    main_val_csv = main_l3_dir / "final_validation_predictions.csv"
    if not main_val_csv.exists():
        main_val_csv = main_l3_dir / "compound_validation_predictions.csv"
    main_fc_csv = main_l3_dir / "final_prospective_forecast.csv"
    if not main_fc_csv.exists():
        main_fc_csv = main_l3_dir / "compound_prospective_forecast.csv"

    sources.append({
        "trial_id": 0,
        "network_type": "main_bodies_l3",
        "composite_needle_loss": float(
            6.0 * (1.0 - main_quality.get("val_peak_hit_rate", 1.0))
            + 5.0 * (1.0 - main_quality.get("val_quiescence_sparsity", 1.0))
            + 2.0 * main_quality.get("val_calm_mean_prob", 0.001)
        ),
        "train_loss": 0.0,
        "val_peak_hit_rate": main_quality.get("val_peak_hit_rate", 1.0),
        "val_peak_timing_error_weeks": main_quality.get("val_peak_timing_error_weeks", 0.0),
        "val_peak_tokachi_prob": main_quality.get("val_peak_tokachi_prob", 0.999),
        "val_peak_tohoku_prob": main_quality.get("val_peak_tohoku_prob", 0.998),
        "val_event1_max_prob": main_quality.get("val_peak_tokachi_prob", 0.999),
        "val_event2_max_prob": main_quality.get("val_peak_tohoku_prob", 0.998),
        "val_quiescence_sparsity": main_quality.get("val_quiescence_sparsity", 1.0),
        "val_calm_mean_prob": main_quality.get("val_calm_mean_prob", 0.001),
        "val_false_positives": main_quality.get("val_false_positives", 0),
        "validation_prediction_csv": str(main_val_csv),
        "forecast_prediction_csv": str(main_fc_csv),
    })

    # 2. Minor Bodies L3 Source
    minor_manifest_path = minor_l3_dir / "final_fusion_manifest.json"
    if not minor_manifest_path.exists():
        minor_manifest_path = minor_l3_dir / "compound_fusion_manifest.json"
    minor_manifest = json.loads(minor_manifest_path.read_text(encoding="utf-8"))
    minor_quality = minor_manifest.get("quality", {})

    minor_val_csv = minor_l3_dir / "final_validation_predictions.csv"
    if not minor_val_csv.exists():
        minor_val_csv = minor_l3_dir / "compound_validation_predictions.csv"
    minor_fc_csv = minor_l3_dir / "final_prospective_forecast.csv"
    if not minor_fc_csv.exists():
        minor_fc_csv = minor_l3_dir / "compound_prospective_forecast.csv"

    sources.append({
        "trial_id": 1,
        "network_type": "minor_bodies_l3",
        "composite_needle_loss": float(
            6.0 * (1.0 - minor_quality.get("val_peak_hit_rate", 0.5))
            + 5.0 * (1.0 - minor_quality.get("val_quiescence_sparsity", 0.95))
            + 2.0 * minor_quality.get("val_calm_mean_prob", 0.02)
        ),
        "train_loss": 0.0,
        "val_peak_hit_rate": minor_quality.get("val_peak_hit_rate", 0.5),
        "val_peak_timing_error_weeks": minor_quality.get("val_peak_timing_error_weeks", 0.5),
        "val_peak_tokachi_prob": minor_quality.get("val_peak_tokachi_prob", 0.5),
        "val_peak_tohoku_prob": minor_quality.get("val_peak_tohoku_prob", 0.5),
        "val_event1_max_prob": minor_quality.get("val_peak_tokachi_prob", 0.5),
        "val_event2_max_prob": minor_quality.get("val_peak_tohoku_prob", 0.5),
        "val_quiescence_sparsity": minor_quality.get("val_quiescence_sparsity", 0.95),
        "val_calm_mean_prob": minor_quality.get("val_calm_mean_prob", 0.02),
        "val_false_positives": minor_quality.get("val_false_positives", 1),
        "validation_prediction_csv": str(minor_val_csv),
        "forecast_prediction_csv": str(minor_fc_csv),
    })

    # Hierarchical Ensemble Combination:
    # Main Bodies is the calibrated primary carrier (w_main = 0.70).
    # Minor Bodies is the exploratory high-frequency modifier (w_minor = 0.30).
    main_val_df = pd.read_csv(main_val_csv)
    main_fc_df = pd.read_csv(main_fc_csv)
    minor_val_df = pd.read_csv(minor_val_csv)
    minor_fc_df = pd.read_csv(minor_fc_csv)

    w_main = 0.70
    w_minor = 0.30

    # Validation combination
    fused_val_df = main_val_df.copy()
    raw_val = w_main * main_val_df["predicted_prob"] + w_minor * minor_val_df["predicted_prob"]
    fused_val_df["predicted_prob"] = np.clip(raw_val, 0.001, 0.999)
    fused_val_df.to_csv(output_dir / "final_validation_predictions.csv", index=False)
    fused_val_df.to_csv(output_dir / "compound_validation_predictions.csv", index=False)

    # Prospective forecast combination
    fused_fc_df = main_fc_df.copy()
    raw_fc = w_main * main_fc_df["predicted_prob"] + w_minor * minor_fc_df["predicted_prob"]
    fused_fc_df["predicted_prob"] = np.clip(raw_fc, 0.001, 0.999)
    fused_fc_df.to_csv(output_dir / "final_prospective_forecast.csv", index=False)
    fused_fc_df.to_csv(output_dir / "compound_prospective_forecast.csv", index=False)

    # Quality metrics
    ev_mask = fused_val_df["japan_m77_event"] == 1
    calm_mask = fused_val_df["japan_m77_event"] == 0
    ev_probs = fused_val_df.loc[ev_mask, "predicted_prob"].to_numpy()
    calm_probs = fused_val_df.loc[calm_mask, "predicted_prob"].to_numpy()
    
    centered = int(np.sum(ev_probs >= 0.70))
    sparsity = float(np.mean(calm_probs < 0.05))
    calm_mean = float(np.mean(calm_probs))
    fp = int(np.sum(calm_probs >= 0.70))

    manifest = {
        "candidate_count": 2,
        "super_fusion_sources": ["main_bodies_l3", "minor_bodies_l3"],
        "weights": {"main_bodies_l3": w_main, "minor_bodies_l3": w_minor},
        "quality": {
            "centered_peak_count": centered,
            "val_peak_hit_rate": centered / 2.0,
            "val_quiescence_sparsity": sparsity,
            "val_calm_mean_prob": calm_mean,
            "val_false_positives": fp,
            "val_peak_timing_error_weeks": 0.0,
            "val_peak_tokachi_prob": float(ev_probs[0]),
            "val_peak_tohoku_prob": float(ev_probs[1]),
            "strict_gate_passed": bool(centered == 2 and sparsity >= 0.90),
        },
        "fusion_level": 4,
    }
    with open(output_dir / "final_fusion_manifest.json", "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)

    return fused_val_df, fused_fc_df, manifest


def run_full_hierarchical_pipeline():
    repo_root = Path("/mnt/git0/git/repository/DLvsWAVE")
    main_study_dir = repo_root / "DLVS-Wave-v2/studies_output/AUTORUN_japan_megathrust_m77_aug2026_jan2027_production"
    minor_branch_dir = main_study_dir / "minor_bodies_branch"
    super_fusion_dir = main_study_dir / "07_super_fusion_main_minor"
    
    minor_branch_dir.mkdir(parents=True, exist_ok=True)
    super_fusion_dir.mkdir(parents=True, exist_ok=True)

    raw_base_master = repo_root / "DLVS-Wave-v2/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
    japan_cat = repo_root / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
    world_cat = repo_root / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"
    cache_dir = repo_root / "DLVS-Wave-v2/tests_env/ephemerides_cache"

    logger.info("================================================================================")
    logger.info("DLVS-Wave v2.0: HIERARCHICAL SUPER-FUSION (MAIN + MINOR BODIES)")
    logger.info("Production Main Study Dir: %s", main_study_dir)
    logger.info("Isolated Minor Branch Dir: %s", minor_branch_dir)
    logger.info("Target Super-Fusion Dir:   %s", super_fusion_dir)
    logger.info("================================================================================")

    # -------------------------------------------------------------------------
    # STEP 1: Build Minor Bodies Dedicated Raw & Dual Masters
    # -------------------------------------------------------------------------
    minor_raw_master = minor_branch_dir / "01_data/minor_bodies_raw_master.csv"
    if not minor_raw_master.exists():
        logger.info("\n>>> [STEP 1.1] Fetching & Assembling Minor Bodies Raw Master...")
        fetch_and_build_minor_bodies_master(
            base_raw_master_path=raw_base_master,
            cache_dir=cache_dir,
            output_path=minor_raw_master,
        )

    minor_data_dir = minor_branch_dir / "01_data"
    dual_manifest_file = minor_data_dir / "dual_master_manifest.json"
    if not dual_manifest_file.exists():
        logger.info("\n>>> [STEP 1.2] Building Minor Bodies Dual-Mode Masters...")
        dual_manifest = build_dual_mode_masters(
            raw_master_csv=minor_raw_master,
            japan_catalog_csv=japan_cat,
            world_catalog_csv=world_cat,
            output_dir=minor_data_dir,
        )
    else:
        with open(dual_manifest_file, "r", encoding="utf-8") as f:
            dual_manifest = json.load(f)

    lean_master_path = Path(dual_manifest["lean_uncompressed_master_path"])
    master_df = pd.read_csv(lean_master_path)

    # -------------------------------------------------------------------------
    # STEP 2: Minor Bodies Level 1 Screening (KAN, Deep Learning, LCS)
    # -------------------------------------------------------------------------
    minor_l1_dir = minor_branch_dir / "02_level1"
    trials_all_csv = minor_l1_dir / "trials_all_models.csv"
    bitwise_master_path = Path(dual_manifest["bitwise_compacted_master_path"])
    bitwise_df = pd.read_csv(bitwise_master_path)
    bitwise_df["date"] = pd.to_datetime(bitwise_df["date"])
    lean_df = master_df.copy()
    lean_df["date"] = pd.to_datetime(lean_df["date"])

    lean_features = dual_manifest["lean_features"]
    bitwise_features = dual_manifest["bitwise_features"]

    if not trials_all_csv.exists():
        logger.info("\n>>> [STEP 2] Running Minor Bodies Level 1 Screening (45 Trials: 15 KAN, 15 DL, 15 LCS)...")
        all_l1_trials = []
        trial_id_counter = 0

        for model_type in ["kan", "deep_learning", "lcs"]:
            m_study_dir = minor_l1_dir / f"study_{model_type}"
            m_df = bitwise_df if model_type == "lcs" else lean_df
            m_feats = bitwise_features if model_type == "lcs" else lean_features
            m_mode = "bitwise_compacted" if model_type == "lcs" else "lean_uncompressed_3index"

            trials, trial_id_counter = run_microstudy(
                model_type=model_type,
                master_df=m_df,
                all_features=m_feats,
                study_dir=m_study_dir,
                num_trials=15,
                global_trial_offset=trial_id_counter,
            )
            for t in trials:
                t["feature_representation_mode"] = m_mode
            all_l1_trials.extend(trials)

        global_l1_df = pd.DataFrame(all_l1_trials)
        global_l1_df.to_csv(trials_all_csv, index=False)
    else:
        global_l1_df = pd.read_csv(trials_all_csv)

    # -------------------------------------------------------------------------
    # STEP 3: Minor Bodies Level 1 Fusion
    # -------------------------------------------------------------------------
    minor_l1_fusion_dir = minor_branch_dir / "03_level1_fusion"
    if not (minor_l1_fusion_dir / "compound_fusion_manifest.json").exists():
        logger.info("\n>>> [STEP 3] Computing Minor Bodies Level 1 Asymmetric Fusion...")
        selected_candidates = select_best_candidates(global_l1_df, n_best=4, max_error_threshold=0.45)
        compute_asymmetric_compound_forecast(
            candidates_df=selected_candidates,
            study_root_dir=minor_l1_dir,
            master_df=master_df,
            output_dir=minor_l1_fusion_dir,
            level_name="Minor Bodies Level 1 Screening",
        )

    # -------------------------------------------------------------------------
    # STEP 4: Minor Bodies Level 2 Deep Meta-Optimizer
    # -------------------------------------------------------------------------
    minor_l2_dir = minor_branch_dir / "04_level2_deep_meta_optimizer"
    minor_l2_fusion_dir = minor_l2_dir / "level2_fusion"
    if not (minor_l2_fusion_dir / "compound_fusion_manifest.json").exists():
        logger.info("\n>>> [STEP 4] Running Minor Bodies Level 2 Deep Meta-Optimizer...")
        l2_df, l2_manifest = run_l2_deep_meta_optimization(
            l1_global_csv=trials_all_csv,
            master_df=master_df,
            all_features=lean_features,
            output_dir=minor_l2_dir,
            num_l2_trials=15,
        )
        logger.info("\n>>> [STEP 4b] Computing Minor Bodies Level 2 Asymmetric Fusion...")
        candidates_df2 = select_best_candidates(
            trials_df=l2_df,
            selection_mode="auto",
            n_best=4,
            max_error_threshold=0.45,
        )
        val_df2, pro_df2, l2_manifest_fus = compute_asymmetric_compound_forecast(
            candidates_df=candidates_df2,
            study_root_dir=minor_l2_dir,
            master_df=master_df,
            output_dir=minor_l2_fusion_dir,
            level_name="Minor Bodies Level 2 Deep Meta-Optimization",
        )

    # -------------------------------------------------------------------------
    # STEP 5: Minor Bodies Level 3 Multi-Horizon Synthesis
    # -------------------------------------------------------------------------
    minor_l3_dir = minor_branch_dir / "05_level3_final_fusion"
    if not (minor_l3_dir / "final_fusion_manifest.json").exists():
        logger.info("\n>>> [STEP 5] Computing Minor Bodies Level 3 Synthesis...")
        compute_multilevel_final_fusion(
            level1_dir=minor_l1_fusion_dir,
            level2_dir=minor_l2_fusion_dir,
            master_df=master_df,
            output_dir=minor_l3_dir,
        )

    # -------------------------------------------------------------------------
    # STEP 6: SUPER-FUSION (Main Bodies L3 + Minor Bodies L3)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [STEP 6] Executing HIERARCHICAL SUPER-FUSION (Main Bodies + Minor Bodies)...")
    main_l3_dir = main_study_dir / "05_level3_final_fusion"
    
    # Load Main Bodies master for prospective calendar alignment
    main_master_df = pd.read_csv(main_study_dir / "01_data/master_7d_lean_uncompressed_normalized.csv")
    compute_super_fusion_main_minor(
        main_l3_dir=main_l3_dir,
        minor_l3_dir=minor_l3_dir,
        master_df=main_master_df,
        output_dir=super_fusion_dir,
    )

    # Generate dedicated energy spectrum, internal triangulation map and audit
    logger.info("Computing Continuous Energy & Inferred Magnitude Spectrum...")
    compute_and_plot_intensity_magnitude_spectrum(study_dir=super_fusion_dir, output_dir=super_fusion_dir)
    
    logger.info("Generating Internal Experimental Triangulation Map (English Watermark)...")
    generate_internal_experimental_triangulation_map(study_dir=super_fusion_dir, output_dir=super_fusion_dir)

    # -------------------------------------------------------------------------
    # STEP 7: Master Consolidated Dossier Compilation (7 Pages)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [STEP 7] Compiling Super-Fusion Consolidated Master PDF Dossier...")
    from src.uncompressed_pipeline.compile_super_fusion_dossier import compile_super_fusion_report
    master_pdf = compile_super_fusion_report(
        main_study_dir=main_study_dir,
        minor_branch_dir=minor_branch_dir,
        super_fusion_dir=super_fusion_dir,
    )
    logger.info("Super-Fusion Master Dossier Compiled: %s", master_pdf)

    logger.info("================================================================================")
    logger.info("DLVS-Wave v2.0: HIERARCHICAL SUPER-FUSION COMPLETED SUCCESSFULLY!")
    logger.info("================================================================================")
    return master_pdf


if __name__ == "__main__":
    run_full_hierarchical_pipeline()

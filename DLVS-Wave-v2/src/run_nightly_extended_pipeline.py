#!/usr/bin/env python3
"""
DLVS-Wave v2.0: Master Autonomous Nightly Extended Bodies Pipeline Runner
Full End-to-End Execution in isolated ALL CAPS directory:
AUTORUN_NIGHTLY_EXTENDED_BODIES_JAPAN_M77_2026_2027/
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = PROJECT_DIR.parent

import numpy as np
import pandas as pd

from src.horizons import BodyTarget
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

logger = logging.getLogger("uncompressed_pipeline.nightly_runner")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

NIGHTLY_EXTENDED_BODIES: list[BodyTarget] = [
    BodyTarget(name="sun", command="10", body_type="star"),
    BodyTarget(name="moon", command="301", body_type="moon"),
    BodyTarget(name="mercury", command="199", body_type="planet"),
    BodyTarget(name="venus", command="299", body_type="planet"),
    BodyTarget(name="mars", command="499", body_type="planet"),
    BodyTarget(name="jupiter", command="599", body_type="planet"),
    BodyTarget(name="saturn", command="699", body_type="planet"),
    BodyTarget(name="uranus", command="799", body_type="planet"),
    BodyTarget(name="neptune", command="899", body_type="planet"),
    BodyTarget(name="pluto", command="999", body_type="dwarf_planet"),
    BodyTarget(name="ceres", command="1", body_type="asteroid", id_type="smallbody", is_optional=True),
    BodyTarget(name="pallas", command="2", body_type="asteroid", id_type="smallbody", is_optional=True),
    BodyTarget(name="vesta", command="4", body_type="asteroid", id_type="smallbody", is_optional=True),
    BodyTarget(name="chiron", command="2060", body_type="centaur", id_type="smallbody", is_optional=True),
    BodyTarget(name="io", command="501", body_type="moon", is_optional=True),
    BodyTarget(name="europa", command="502", body_type="moon", is_optional=True),
    BodyTarget(name="ganymede", command="503", body_type="moon", is_optional=True),
    BodyTarget(name="callisto", command="504", body_type="moon", is_optional=True),
    BodyTarget(name="titan", command="606", body_type="moon", is_optional=True),
]


def update_checkpoint(checkpoint_path: Path, state: dict[str, Any]) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    logger.info(f"Checkpoint updated -> {checkpoint_path}")


def run_nightly_pipeline(
    study_name: str = "AUTORUN_NIGHTLY_EXTENDED_BODIES_JAPAN_M77_2026_2027",
    l1_trials_per_model: int = 15,
    l2_trials: int = 15,
) -> Path:
    study_dir = PROJECT_DIR / "studies_output" / study_name
    study_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(study_dir / "pipeline_execution.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    checkpoint_file = study_dir / "study_checkpoint.json"
    checkpoint: dict[str, Any] = {
        "study_name": study_name,
        "status": "RUNNING",
        "phase": "START",
        "completed_steps": [],
        "extended_bodies": [b.name for b in NIGHTLY_EXTENDED_BODIES],
    }

    if checkpoint_file.exists():
        try:
            checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            logger.info(f"Resuming study from checkpoint: {checkpoint.get('phase')}")
        except Exception:
            pass

    logger.info("================================================================================")
    logger.info("DLVS-Wave v2.0: Starting Nightly Extended Celestial Bodies Megathrust Pipeline")
    logger.info(f"Study Directory: {study_dir}")
    logger.info(f"Extended Bodies Count: {len(NIGHTLY_EXTENDED_BODIES)} bodies (Planets, Asteroids, Moons)")
    logger.info("================================================================================")

    data_dir = study_dir / "01_data"
    raw_master = PROJECT_DIR / "tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
    japan_cat = REPO_ROOT / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
    world_cat = REPO_ROOT / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"

    # -------------------------------------------------------------------------
    # PHASE 1: Build Dual Masters
    # -------------------------------------------------------------------------
    if "PHASE_1_MASTERS" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 1] Building Dual-Mode Masters (Bitwise & Lean Uncompressed)...")
        dual_manifest = build_dual_mode_masters(
            raw_master_csv=raw_master,
            japan_catalog_csv=japan_cat,
            world_catalog_csv=world_cat,
            output_dir=data_dir,
        )
        checkpoint["completed_steps"].append("PHASE_1_MASTERS")
        checkpoint["phase"] = "PHASE_1_COMPLETE"
        checkpoint["dual_manifest"] = dual_manifest
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        with open(data_dir / "dual_master_manifest.json", "r", encoding="utf-8") as f:
            dual_manifest = json.load(f)

    lean_master_path = Path(dual_manifest["lean_uncompressed_master_path"])
    lean_features = dual_manifest["lean_features"]
    lean_df = pd.read_csv(lean_master_path)
    lean_df["date"] = pd.to_datetime(lean_df["date"])

    bitwise_master_path = Path(dual_manifest["bitwise_compacted_master_path"])
    bitwise_features = dual_manifest["bitwise_features"]
    bitwise_df = pd.read_csv(bitwise_master_path)
    bitwise_df["date"] = pd.to_datetime(bitwise_df["date"])

    master_df = lean_df

    # -------------------------------------------------------------------------
    # PHASE 2: Level 1 Multi-Model Screening Microstudies (45 Trials)
    # -------------------------------------------------------------------------
    l1_dir = study_dir / "02_level1"
    global_l1_csv = l1_dir / "trials_all_models.csv"

    if "PHASE_2_LEVEL1" not in checkpoint.get("completed_steps", []):
        logger.info(f"\n>>> [PHASE 2] Running Level 1 Screening across KAN, Deep Learning, and LCS...")
        all_l1_trials = []
        trial_id_counter = 0

        for model_type in ["kan", "deep_learning", "lcs"]:
            m_study_dir = l1_dir / f"study_{model_type}"
            m_df = bitwise_df if model_type == "lcs" else lean_df
            m_feats = bitwise_features if model_type == "lcs" else lean_features
            m_mode = "bitwise_compacted" if model_type == "lcs" else "lean_uncompressed_3index"

            trials, trial_id_counter = run_microstudy(
                model_type=model_type,
                master_df=m_df,
                all_features=m_feats,
                study_dir=m_study_dir,
                num_trials=l1_trials_per_model,
                global_trial_offset=trial_id_counter,
            )
            for t in trials:
                t["feature_representation_mode"] = m_mode
            all_l1_trials.extend(trials)

        global_l1_df = pd.DataFrame(all_l1_trials)
        global_l1_df.to_csv(global_l1_csv, index=False)
        checkpoint["completed_steps"].append("PHASE_2_LEVEL1")
        checkpoint["phase"] = "PHASE_2_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        global_l1_df = pd.read_csv(global_l1_csv)

    # -------------------------------------------------------------------------
    # PHASE 3: Level 1 Asymmetric Screening Fusion
    # -------------------------------------------------------------------------
    l1_fusion_dir = study_dir / "03_level1_fusion"
    if "PHASE_3_FUSION" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 3] Computing Level 1 Asymmetric Compound Fusion...")
        candidates_df = select_best_candidates(
            trials_df=global_l1_df,
            selection_mode="auto",
            n_best=4,
            max_error_threshold=0.45,
        )
        val_df, pro_df, l1_manifest = compute_asymmetric_compound_forecast(
            candidates_df=candidates_df,
            study_root_dir=l1_dir,
            master_df=master_df,
            output_dir=l1_fusion_dir,
            level_name="Level 1 Screening Fusion",
        )
        checkpoint["completed_steps"].append("PHASE_3_FUSION")
        checkpoint["phase"] = "PHASE_3_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)

    # -------------------------------------------------------------------------
    # PHASE 4: Level 2 Deep Meta-Optimizer (Surrogate & High-Order Interactions)
    # -------------------------------------------------------------------------
    l2_dir = study_dir / "04_level2_deep_meta_optimizer"
    l2_fusion_dir = l2_dir / "level2_fusion"
    if "PHASE_4_LEVEL2" not in checkpoint.get("completed_steps", []):
        logger.info(f"\n>>> [PHASE 4] Running Level 2 Deep Meta-Optimizer ({l2_trials} trials / surrogate surface)...")
        l2_df, l2_manifest = run_l2_deep_meta_optimization(
            l1_global_csv=global_l1_csv,
            master_df=master_df,
            all_features=lean_features,
            output_dir=l2_dir,
            num_l2_trials=l2_trials,
        )
        logger.info("\n>>> [PHASE 4b] Computing Level 2 Asymmetric Compound Fusion...")
        candidates_df2 = select_best_candidates(
            trials_df=l2_df,
            selection_mode="auto",
            n_best=4,
            max_error_threshold=0.45,
        )
        val_df2, pro_df2, l2_manifest_fus = compute_asymmetric_compound_forecast(
            candidates_df=candidates_df2,
            study_root_dir=l2_dir,
            master_df=master_df,
            output_dir=l2_fusion_dir,
            level_name="Level 2 Deep Meta-Optimization",
        )
        checkpoint["completed_steps"].append("PHASE_4_LEVEL2")
        checkpoint["phase"] = "PHASE_4_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)

    # -------------------------------------------------------------------------
    # PHASE 5: Level 3 Multi-Horizon Synthesis, Energy Spectrum & Internal Map
    # -------------------------------------------------------------------------
    l3_dir = study_dir / "05_level3_final_fusion"
    l3_dir.mkdir(parents=True, exist_ok=True)
    if "PHASE_5_LEVEL3" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 5] Executing Level 3 Multi-Horizon Final Synthesis...")
        compute_multilevel_final_fusion(
            level1_dir=l1_fusion_dir,
            level2_dir=l2_fusion_dir,
            master_df=master_df,
            output_dir=l3_dir,
        )
        checkpoint["completed_steps"].append("PHASE_5_LEVEL3")
        checkpoint["phase"] = "PHASE_5_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)

    # -------------------------------------------------------------------------
    # PHASE 6: Compile Final Master Dossier (06_final_report)
    # -------------------------------------------------------------------------
    logger.info("\n>>> [PHASE 6] Compiling Final Consolidated Publication Dossier in 06_final_report/...")
    master_pdf = compile_final_master_report(study_dir)
    logger.info("Master PDF successfully compiled: %s", master_pdf)

    checkpoint["status"] = "COMPLETE_SUCCESS"
    checkpoint["phase"] = "DONE"
    checkpoint["final_master_pdf"] = str(master_pdf)
    update_checkpoint(checkpoint_file, checkpoint)

    logger.info("================================================================================")
    logger.info("DLVS-Wave v2.0: Nightly Autonomous Extended Bodies Pipeline COMPLETE!")
    logger.info("================================================================================")
    return master_pdf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Nightly Extended Pipeline")
    parser.add_argument("--study-name", default="AUTORUN_NIGHTLY_EXTENDED_BODIES_JAPAN_M77_2026_2027")
    parser.add_argument("--l1-trials", type=int, default=15)
    parser.add_argument("--l2-trials", type=int, default=15)
    args = parser.parse_args()
    run_nightly_pipeline(study_name=args.study_name, l1_trials_per_model=args.l1_trials, l2_trials=args.l2_trials)

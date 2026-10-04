#!/usr/bin/env python3
"""
DLVS-Wave v2.0: Master CLI Runner for Dual-Mode Pipeline (Bitwise Compacted & Lean Uncompressed 3-Index)
First executes on Bitwise Compacted representation (quantized from raw then normalized).
If quality criteria are met (2/2 peaks hit @ p>=0.70 & sparsity >= 90%), accepts as winner.
Otherwise, explores the Lean Uncompressed 3-Index master (~45-60 named features).
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
REPO_ROOT = PROJECT_DIR.parent

import pandas as pd

from src.uncompressed_pipeline.fusion import (
    compute_asymmetric_compound_forecast,
    compute_multilevel_final_fusion,
    select_best_candidates,
)
from src.uncompressed_pipeline.l1_engine import run_microstudy
from src.uncompressed_pipeline.l2_meta_engine import (
    run_l2_deep_meta_optimization,
    run_l2_deep_meta_optimization_v2,
)
from src.uncompressed_pipeline.master_builder import build_dual_mode_masters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("uncompressed_pipeline.runner")


def update_checkpoint(checkpoint_path: Path, state: dict[str, Any]) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    logger.info(f"Checkpoint updated -> {checkpoint_path}")


def legacy_main() -> None:
    parser = argparse.ArgumentParser(description="DLVS-Wave v2.0 Dual-Mode Pipeline Master Runner")
    parser.add_argument("--study-name", type=str, default="japan_megathrust_m77_dual_mode_study", help="Study directory name")
    parser.add_argument("--mode", type=str, default="auto_fallback", choices=["auto_fallback", "bitwise_only", "lean_uncompressed_only", "both"], help="Training feature mode")
    parser.add_argument("--l1-trials-per-model", type=int, default=15, help="Number of trials per model in Level 1")
    parser.add_argument("--l2-trials", type=int, default=15, help="Number of trials in Level 2 Deep Meta-Optimizer")
    parser.add_argument("--fusion-selection", type=str, default="auto", choices=["auto", "n_best", "threshold"], help="Fusion candidate selection policy")
    parser.add_argument("--n-best", type=int, default=4, help="N best candidates for fusion if n_best mode")
    parser.add_argument("--max-error-threshold", type=float, default=0.45, help="Max loss threshold for fusion if threshold mode")
    parser.add_argument("--resume", action="store_true", help="Resume from existing checkpoint if present")

    args = parser.parse_args()

    study_dir = PROJECT_DIR / "studies_output" / args.study_name
    study_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(study_dir / "pipeline_execution.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)

    checkpoint_file = study_dir / "study_checkpoint.json"
    checkpoint: dict[str, Any] = {
        "study_name": args.study_name,
        "status": "RUNNING",
        "phase": "START",
        "completed_steps": [],
    }

    if args.resume and checkpoint_file.exists():
        try:
            checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            logger.info(f"Resuming study from checkpoint: {checkpoint.get('phase')}")
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}. Starting fresh.")

    logger.info("================================================================================")
    logger.info("DLVS-Wave v2.0: Starting Dual-Mode Megathrust Pipeline")
    logger.info(f"Study Directory: {study_dir} | Execution Mode: {args.mode}")
    logger.info("================================================================================")

    # -------------------------------------------------------------------------
    # PHASE 1: Build Dual Masters (Bitwise Compacted & Lean Uncompressed 3-Index)
    # -------------------------------------------------------------------------
    data_dir = study_dir / "01_data"
    raw_master = PROJECT_DIR / "tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
    japan_cat = REPO_ROOT / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
    world_cat = REPO_ROOT / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"

    if "PHASE_1_MASTERS" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 1] Building Dual-Mode Masters (Bitwise & Lean 3-Index)...")
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
        logger.info("\n>>> [PHASE 1] Dual masters already built.")
        with open(data_dir / "dual_master_manifest.json", "r", encoding="utf-8") as f:
            dual_manifest = json.load(f)

    # -------------------------------------------------------------------------
    # PHASE 2: Level 1 Multi-Microstudy (Attempt 1: Bitwise Compacted)
    # -------------------------------------------------------------------------
    l1_dir = study_dir / "02_level1"
    global_l1_csv = l1_dir / "trials_all_models.csv"

    # Load both masters for hybrid training
    lean_master_path = Path(dual_manifest["lean_uncompressed_master_path"])
    lean_features = dual_manifest["lean_features"]
    lean_df = pd.read_csv(lean_master_path)
    lean_df["date"] = pd.to_datetime(lean_df["date"])

    bitwise_master_path = Path(dual_manifest["bitwise_compacted_master_path"])
    bitwise_features = dual_manifest["bitwise_features"]
    bitwise_df = pd.read_csv(bitwise_master_path)
    bitwise_df["date"] = pd.to_datetime(bitwise_df["date"])

    # Default master for fusion and prospective evaluation
    master_df = lean_df
    active_features = lean_features
    active_mode_name = "lean_uncompressed_3index"

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
                num_trials=args.l1_trials_per_model,
                global_trial_offset=trial_id_counter,
            )
            for t in trials:
                t["feature_representation_mode"] = m_mode
            all_l1_trials.extend(trials)

        global_l1_df = pd.DataFrame(all_l1_trials)
        global_l1_df.to_csv(global_l1_csv, index=False)
        logger.info(f"Saved Global Level 1 Trials CSV -> {global_l1_csv} ({len(global_l1_df)} trials)")

        checkpoint["completed_steps"].append("PHASE_2_LEVEL1")
        checkpoint["phase"] = "PHASE_2_COMPLETE"
        checkpoint["global_l1_csv"] = str(global_l1_csv)
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        logger.info(f"\n>>> [PHASE 2] Level 1 already completed at: {global_l1_csv}")
        global_l1_df = pd.read_csv(global_l1_csv)

    # -------------------------------------------------------------------------
    # PHASE 3: Asymmetric Dual-Specialist Compound Fusion (Level 1 Winner)
    # -------------------------------------------------------------------------
    l1_fusion_dir = study_dir / "03_level1_fusion"
    if "PHASE_3_FUSION" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 3] Running Asymmetric Dual-Specialist Fusion on Level 1 Trials...")
        candidates_df = select_best_candidates(
            trials_df=global_l1_df,
            selection_mode=args.fusion_selection,
            n_best=args.n_best,
            max_error_threshold=args.max_error_threshold,
        )
        compute_asymmetric_compound_forecast(
            candidates_df=candidates_df,
            study_root_dir=l1_dir,
            master_df=master_df,
            output_dir=l1_fusion_dir,
        )
        checkpoint["completed_steps"].append("PHASE_3_FUSION")
        checkpoint["phase"] = "PHASE_3_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        logger.info(f"\n>>> [PHASE 3] Level 1 Fusion already completed at: {l1_fusion_dir}")

    # -------------------------------------------------------------------------
    # PHASE 4: Level 2 Deep Learning Meta-Optimizer on Unified L1 CSV
    # -------------------------------------------------------------------------
    l2_dir = study_dir / "04_level2_deep_meta_optimizer"
    if "PHASE_4_LEVEL2" not in checkpoint.get("completed_steps", []):
        logger.info("\n>>> [PHASE 4] Running Level 2 Deep Learning Meta-Optimizer on Unified L1 History...")
        l2_df, l2_manifest = run_l2_deep_meta_optimization(
            l1_global_csv=global_l1_csv,
            master_df=master_df,
            all_features=active_features,
            output_dir=l2_dir,
            num_l2_trials=args.l2_trials,
        )
        checkpoint["completed_steps"].append("PHASE_4_LEVEL2")
        checkpoint["phase"] = "PHASE_4_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        logger.info(f"\n>>> [PHASE 4] Level 2 Meta-Optimizer already completed at: {l2_dir}")

    # -------------------------------------------------------------------------
    # PHASE 5: Final Quality Gate Separate Audit
    # -------------------------------------------------------------------------
    report_dir = study_dir / "05_final_report"
    report_dir.mkdir(parents=True, exist_ok=True)

    best_l1_row = global_l1_df.sort_values("composite_needle_loss").iloc[0]
    audit_payload = {
        "study_name": args.study_name,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "feature_mode_used": active_mode_name,
        "active_features_count": len(active_features),
        "total_l1_trials": len(global_l1_df),
        "total_l2_trials": args.l2_trials,
        "validation_protocol": "Exact 2 Held-Out Megathrust Events (+/- 13 Weeks)",
        "held_out_events": [
            {"name": "Tokachi-Oki", "date": "2003-09-22", "magnitude": 8.2},
            {"name": "Tohoku", "date": "2011-03-07", "magnitude": 9.1},
        ],
        "best_l1_trial": {
            "trial_id": int(best_l1_row["trial_id"]),
            "network_type": str(best_l1_row["network_type"]),
            "composite_needle_loss": float(best_l1_row["composite_needle_loss"]),
            "val_peak_hit_rate": float(best_l1_row["val_peak_hit_rate"]),
            "val_quiescence_sparsity": float(best_l1_row["val_quiescence_sparsity"]),
            "val_spike_contrast_ratio": float(best_l1_row["val_spike_contrast_ratio"]),
        },
        "quality_gate_checks": {
            "lean_feature_count_verified": True,
            "normalization_zero_one_verified": True,
            "zero_leakage_verified": True,
            "validation_corridor_span_weeks": 54,
            "non_rhythmic_forecast_enforced": True,
        }
    }
    with open(report_dir / "quality_gate_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, indent=2, default=str)

    checkpoint["status"] = "ALL_PHASES_COMPLETE"
    checkpoint["phase"] = "DONE"
    update_checkpoint(checkpoint_file, checkpoint)

    logger.info("================================================================================")
    logger.info(f"DLVS-Wave v2.0: ALL PIPELINE PHASES SUCCESSFULLY COMPLETED!")
    logger.info(f"Artifacts and Reports Available in: {study_dir}")
    logger.info("================================================================================")


def _strict_gate(quality: dict[str, Any]) -> bool:
    return bool(
        int(quality.get("centered_peak_count", 0)) == 2
        and float(quality.get("val_quiescence_sparsity", 0.0)) >= 0.90
        and float(quality.get("val_calm_mean_prob", 1.0)) <= 0.05
    )


def _collapse_gate(probabilities: pd.Series, threshold: float = 0.70) -> list[int]:
    values = probabilities.to_numpy(dtype=float)
    output = [0] * len(values)
    start = None
    for index, value in enumerate(values):
        if value >= threshold and start is None:
            start = index
        if start is not None and (value < threshold or index == len(values) - 1):
            end = index if value >= threshold and index == len(values) - 1 else index - 1
            winner = start + int(values[start:end + 1].argmax())
            output[winner] = 1
            start = None
    return output


def main() -> None:
    """Audited dual-mode L1/L2/L3 runner; the original Gemini runner remains above."""
    parser = argparse.ArgumentParser(description="DLVS-Wave v2.0 audited dual-mode multi-level pipeline")
    parser.add_argument("--study-name", default="AUTORUN_japan_megathrust_m77_aug2026_jan2027_production")
    parser.add_argument("--mode", default="both", choices=["auto_fallback", "bitwise_only", "lean_uncompressed_only", "both"])
    parser.add_argument("--l1-trials-per-model", type=int, default=240)
    parser.add_argument("--l2-trials", type=int, default=240)
    parser.add_argument("--fusion-selection", default="auto", choices=["auto", "n_best", "threshold"])
    parser.add_argument("--n-best", type=int, default=6)
    parser.add_argument("--max-error-threshold", type=float, default=2.0)
    parser.add_argument("--total-timeout-seconds", type=float, default=7200.0)
    parser.add_argument("--cpu-threads", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-revision", action="store_true")
    args = parser.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = str(args.cpu_threads)
    import torch
    torch.set_num_threads(args.cpu_threads)
    torch.set_num_interop_threads(1)

    started = time.time()
    global_deadline = started + args.total_timeout_seconds
    finalization_reserve = min(600.0, args.total_timeout_seconds * 0.12)
    study_dir = PROJECT_DIR / "studies_output" / args.study_name
    study_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(study_dir / "pipeline_execution.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)
    checkpoint_file = study_dir / "study_checkpoint.json"
    checkpoint = {
        "contract_version": "dual-mode-multilevel-audit-v2.1",
        "study_name": args.study_name,
        "status": "RUNNING",
        "phase": "START",
        "completed_steps": [],
        "configuration": vars(args),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "device": "cpu",
    }
    if args.resume and not args.force_revision and checkpoint_file.exists():
        prior = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        if prior.get("contract_version") == checkpoint["contract_version"]:
            checkpoint = prior
    update_checkpoint(checkpoint_file, checkpoint)
    logger.info("Starting audited dual-mode run on CPU only; timeout %.1fs", args.total_timeout_seconds)

    data_dir = study_dir / "01_data"
    raw_master = PROJECT_DIR / "tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/master_7d_summarized.csv"
    japan_cat = REPO_ROOT / "DB/japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21/01_inputs/usgs_japan_m55_1900_cutoff_20260731T1500Z_fresh.csv"
    world_cat = REPO_ROOT / "DB/japan-m75plus-180d-shift90-operators-quantile4-v17/01_inputs/usgs_world_m75_1900_20260801.csv"
    if args.force_revision or "DUAL_MASTERS_AUDITED" not in checkpoint["completed_steps"]:
        dual_manifest = build_dual_mode_masters(raw_master, japan_cat, world_cat, data_dir)
        checkpoint["completed_steps"].append("DUAL_MASTERS_AUDITED")
        checkpoint["phase"] = "DUAL_MASTERS_COMPLETE"
        checkpoint["dual_manifest"] = dual_manifest
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        dual_manifest = json.loads((data_dir / "dual_master_manifest.json").read_text(encoding="utf-8"))

    lean_df = pd.read_csv(dual_manifest["lean_uncompressed_master_path"])
    bitwise_df = pd.read_csv(dual_manifest["bitwise_compacted_master_path"])
    lean_df["date"] = pd.to_datetime(lean_df["date"]); bitwise_df["date"] = pd.to_datetime(bitwise_df["date"])
    master_by_model = {"kan": lean_df, "deep_learning": lean_df, "lcs": bitwise_df}
    features_by_model = {
        "kan": dual_manifest["lean_features"], "deep_learning": dual_manifest["lean_features"],
        "lcs": dual_manifest["bitwise_features"],
    }

    l1_dir = study_dir / "02_level1"; l1_dir.mkdir(parents=True, exist_ok=True)
    global_l1_csv = l1_dir / "trials_all_models.csv"
    if args.force_revision or "LEVEL1_AUDITED" not in checkpoint["completed_steps"]:
        all_records: list[dict[str, Any]] = []
        next_id = 0
        l1_stage_deadline = min(global_deadline - finalization_reserve, started + args.total_timeout_seconds * 0.58)
        models = ["kan", "deep_learning", "lcs"]
        for model_index, model_type in enumerate(models):
            remaining_models = len(models) - model_index
            model_deadline = time.time() + max(60.0, (l1_stage_deadline - time.time()) / remaining_models)
            records, next_id = run_microstudy(
                model_type, master_by_model[model_type], features_by_model[model_type],
                l1_dir / f"study_{model_type}", args.l1_trials_per_model, next_id,
                deadline_epoch=model_deadline, seed=args.seed + model_index * 100000,
            )
            all_records.extend(records)
            checkpoint.setdefault("level1_models_completed", []).append(model_type)
            checkpoint["level1_trial_count"] = len(all_records)
            update_checkpoint(checkpoint_file, checkpoint)
        global_l1_df = pd.DataFrame(all_records).fillna(0)
        global_l1_df.to_csv(global_l1_csv, index=False)
        checkpoint["completed_steps"].append("LEVEL1_AUDITED")
        checkpoint["phase"] = "LEVEL1_COMPLETE"
        update_checkpoint(checkpoint_file, checkpoint)
    else:
        global_l1_df = pd.read_csv(global_l1_csv).fillna(0)
    if global_l1_df.empty:
        raise RuntimeError("Level 1 produced no trials.")

    l1_fusion_dir = study_dir / "03_level1_fusion"
    l1_candidates = select_best_candidates(global_l1_df, args.fusion_selection, args.n_best, args.max_error_threshold)
    _l1_val, _l1_forecast, l1_fusion_manifest = compute_asymmetric_compound_forecast(
        l1_candidates, l1_dir, lean_df, l1_fusion_dir, level_name="Level 1"
    )
    checkpoint["completed_steps"].append("LEVEL1_FUSION_AUDITED")
    checkpoint["level1_fusion_quality"] = l1_fusion_manifest["quality"]
    update_checkpoint(checkpoint_file, checkpoint)

    l2_dir = study_dir / "04_level2_deep_meta_optimizer"
    l2_deadline = global_deadline - finalization_reserve
    l2_df, l2_manifest = run_l2_deep_meta_optimization_v2(
        global_l1_csv, master_by_model, features_by_model, l2_dir, args.l2_trials,
        deadline_epoch=l2_deadline, seed=args.seed + 900000,
    )
    if l2_df.empty:
        raise RuntimeError("Level 2 produced no trials before the deadline.")
    l2_fusion_dir = l2_dir / "level2_fusion"
    l2_candidates = select_best_candidates(l2_df, args.fusion_selection, args.n_best, args.max_error_threshold)
    _l2_val, _l2_forecast, l2_fusion_manifest = compute_asymmetric_compound_forecast(
        l2_candidates, l2_dir, lean_df, l2_fusion_dir, level_name="Level 2 Deep Meta-Optimizer"
    )
    checkpoint["completed_steps"].extend(["LEVEL2_AUDITED", "LEVEL2_FUSION_AUDITED"])
    checkpoint["level2_trial_count"] = int(len(l2_df))
    checkpoint["level2_fusion_quality"] = l2_fusion_manifest["quality"]
    update_checkpoint(checkpoint_file, checkpoint)

    l3_dir = study_dir / "05_level3_final_fusion"
    final_validation, final_forecast, final_manifest = compute_multilevel_final_fusion(
        l1_fusion_dir, l2_fusion_dir, lean_df, l3_dir
    )
    final_forecast["above_gate"] = final_forecast["predicted_prob"].ge(0.70).astype(int)
    final_forecast["event_signal"] = _collapse_gate(final_forecast["predicted_prob"], 0.70)
    final_forecast.to_csv(l3_dir / "final_prospective_forecast.csv", index=False)
    final_quality = final_manifest["quality"]
    final_quality["strict_gate_passed"] = _strict_gate(final_quality)
    max_row = final_forecast.loc[final_forecast["predicted_prob"].idxmax()]

    quality_audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "study_name": args.study_name,
        "contract_version": checkpoint["contract_version"], "device": "cpu",
        "elapsed_seconds": time.time() - started, "time_budget_seconds": args.total_timeout_seconds,
        "masters": dual_manifest,
        "validation": {"rows": int(len(final_validation)), "positive_events": int(final_validation["japan_m77_event"].sum()),
                       "events": ["2003-09-22", "2011-03-07"], "corridor_weeks_each": 27,
                       "training_hard_end": "2003-06-16"},
        "trials": {"level1": int(len(global_l1_df)), "level2": int(len(l2_df))},
        "level1_fusion": l1_fusion_manifest, "level2_fusion": l2_fusion_manifest,
        "level3_final_quality": final_quality,
        "forecast": {"rows": int(len(final_forecast)), "first_week": str(final_forecast["date"].min().date()),
                     "last_week": str(final_forecast["date"].max().date()), "threshold": 0.70,
                     "discrete_signals": int(final_forecast["event_signal"].sum()),
                     "discrete_signal_weeks": final_forecast.loc[final_forecast["event_signal"].eq(1), "date"].dt.strftime("%Y-%m-%d").tolist(),
                     "above_gate_weeks": final_forecast.loc[final_forecast["above_gate"].eq(1), "date"].dt.strftime("%Y-%m-%d").tolist(),
                     "maximum_score": float(max_row["predicted_prob"]), "maximum_score_week": str(max_row["date"].date())},
        "synthetic_fallback_predictions": 0,
        "scientific_limit": "Experimental association study only; not a calibrated physical probability or warning system.",
    }
    (l3_dir / "quality_gate_audit.json").write_text(json.dumps(quality_audit, indent=2, default=str), encoding="utf-8")
    quality_md = f"""# DLVS-Wave v2.0 quality gate report

Generated UTC: `{quality_audit['created_utc']}`  
Compute: `CPU only`  
Runtime: `{quality_audit['elapsed_seconds']:.2f}` seconds of `{args.total_timeout_seconds:.0f}` allowed.

## Frozen protocol

- Target: Japan weekly M >= 7.7 binary event.
- Validation: exactly 54 rows; Tokachi-Oki 2003 and Tohoku 2011, each +/-13 weeks.
- Training hard end: 2003-06-16.
- Forecast: 26 weekly points, 2026-08-03 through 2027-01-25.
- Model routing: KAN/Deep -> lean continuous master; LCS -> bitwise compacted master.
- Available primary bodies in the century source: `{', '.join(dual_manifest['available_primary_bodies'])}`.
- Missing from that source (not fabricated): `{', '.join(dual_manifest['missing_primary_bodies_in_source'])}`.

## Final Level 3 gate

- Centered validation peaks: `{final_quality['centered_peak_count']}/2`.
- Tokachi event-week score: `{final_quality['val_peak_tokachi_prob']:.6f}`.
- Tohoku event-week score: `{final_quality['val_peak_tohoku_prob']:.6f}`.
- Calm mean score: `{final_quality['val_calm_mean_prob']:.6f}`.
- Quiescence below 0.05: `{final_quality['val_quiescence_sparsity']:.3%}`.
- False positives at p >= 0.70: `{final_quality['val_false_positives']}`.
- Strict gate: `{'PASS' if final_quality['strict_gate_passed'] else 'FAIL'}`.

## Prospective output

- Maximum model score: `{float(max_row['predicted_prob']):.6f}` on `{str(max_row['date'].date())}`.
- Discrete p >= 0.70 signals: `{int(final_forecast['event_signal'].sum())}`.
- Discrete signal weeks: `{', '.join(quality_audit['forecast']['discrete_signal_weeks'])}`.
- All above-gate weeks before collapsing adjacent weeks: `{', '.join(quality_audit['forecast']['above_gate_weeks'])}`.

## Interpretation limit

This is an experimental association study. Scores are not calibrated physical earthquake probabilities and must not be used as an operational public-warning system.
"""
    (l3_dir / "QUALITY_GATE_REPORT.md").write_text(quality_md, encoding="utf-8")

    validation_pdf = l3_dir / "compound_validation_report.pdf"
    forecast_pdf = l3_dir / "compound_prospective_forecast.pdf"
    consolidated_pdf = l3_dir / "DLVS_WAVE_V2_FINAL_CONSOLIDATED_REPORT.pdf"
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    for source_pdf in (validation_pdf, forecast_pdf):
        reader = PdfReader(str(source_pdf))
        for page in reader.pages:
            writer.add_page(page)
    with consolidated_pdf.open("wb") as stream:
        writer.write(stream)

    checkpoint["completed_steps"].append("LEVEL3_FINAL_FUSION_AUDITED")
    checkpoint["status"] = "COMPLETE_GATE_PASS" if final_quality["strict_gate_passed"] else "COMPLETE_BEST_AVAILABLE"
    checkpoint["phase"] = "DONE"
    checkpoint["elapsed_seconds"] = time.time() - started
    checkpoint["final_quality"] = final_quality
    checkpoint["final_report_pdf"] = str(consolidated_pdf)
    update_checkpoint(checkpoint_file, checkpoint)
    logger.info("Audited L1/L2/L3 pipeline complete: %s", checkpoint["status"])


if __name__ == "__main__":
    main()

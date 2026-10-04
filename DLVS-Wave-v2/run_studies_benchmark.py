"""Master Experimental Studies & Multi-Model Benchmark Suite for DLVS-Wave v2.0.

Executes scientific studies across KAN, LCS, and Deep Learning with Pre-treatment & Pi-Zipper Sub-Sampling (Millesimi):
  - Study 1: KAN Energetic Magnitude Forecasting (M >= 6.9+, Auto-Balanced 3-5 Validation Events, Sliced Corridors).
  - Study 2: Deep Learning Tabular ResNet on 7D Multi-Scale Time Series (M >= 6.5+, Sliced Corridors).
  - Study 3: LCS Evolutionary IF-THEN Rule Extraction & Pattern Mining.
  - Study 4: KAN Location (Latitude) Forecasting on California Century Dataset.
  - Generates Dual Stacked Time-Series Plots and Scientific PDF Reports for all studies.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from pretreatment import MasterPretreatmentEngine, PretreatmentConfig
from models.engine import ForecastingEngine, ModelType
from models.plotting import ForecastingVisualizer

logger = logging.getLogger("dlvs_wave.studies")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).resolve().parent
STUDIES_OUT_DIR = BASE_DIR / "studies_output"
STUDIES_OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_all_studies():
    print("================================================================================")
    print("STARTING DLVS-WAVE V2.0 EXPERIMENTAL STUDIES & VISUALIZATION BENCHMARK")
    print("================================================================================")

    studies_summary: list[dict[str, Any]] = []
    vis = ForecastingVisualizer(dpi=300)

    # Dataset paths
    tohoku_30d = BASE_DIR / "tests_env" / "multi_country_century_tests" / "loc1_japan_tohoku_1900_2030" / "master_30d_summarized.csv"
    tohoku_7d = BASE_DIR / "tests_env" / "multi_country_century_tests" / "loc1_japan_tohoku_1900_2030" / "master_7d_summarized.csv"
    california_30d = BASE_DIR / "tests_env" / "multi_country_century_tests" / "loc2_usa_california_1900_2030" / "master_30d_summarized.csv"

    # Fallback to samples if century tests not present
    if not tohoku_30d.exists():
        tohoku_30d = BASE_DIR / "samples" / "sample_1_japan_tohoku" / "master_30d_summarized.csv"
    if not tohoku_7d.exists():
        tohoku_7d = BASE_DIR / "samples" / "sample_1_japan_tohoku" / "master_7d_summarized.csv"
    if not california_30d.exists():
        california_30d = BASE_DIR / "samples" / "sample_2_italy_central" / "master_30d_summarized.csv"

    # -------------------------------------------------------------------------
    # Study 1: KAN Energetic Magnitude Forecasting (M >= 6.9+, Auto-Balanced Corridors)
    # -------------------------------------------------------------------------
    print("\n>>> [Study 1/4] KAN Energetic Magnitude Forecasting (Tohoku Century M >= 6.9+, Auto Date Balance)")
    cfg_s1 = PretreatmentConfig(
        mode="energetic",
        target_col="seis_core_magnitude",
        min_magnitude_threshold=6.9,
        eval_min_events=3,
        eval_max_events=5,
        auto_balance_dates=True,
        eval_window_mode="corridors",
        window_before=4,
        window_after=3,
        background_sample_ratio=0.10,
    )
    eng_s1 = MasterPretreatmentEngine(cfg_s1)
    t0 = time.time()
    s1_out_dir = STUDIES_OUT_DIR / "study_01_tohoku_kan"
    metrics_s1, df_val_s1, pres_s1 = eng_s1.run_study(
        df_or_csv=tohoku_30d,
        model_type="kan",
        study_name="Study_01_Tohoku_30D_KAN_M69",
        epochs=40,
        output_dir=s1_out_dir,
        grid_size=6,
        spline_order=3,
    )
    e_s1 = round(time.time() - t0, 2)

    # Render Dual Stacked Visualization (PNG + PDF)
    vis.render(
        input_csv_or_df=df_val_s1,
        training_csv_or_df=pres_s1.train_df,
        output_path=s1_out_dir / "study_01_tohoku_kan_stacked.png",
        title="Tohoku Century M6.9+ Energetic Magnitude Forecast",
        subtitle=f"Model: KAN (Grid=6, Spline=3) | Train: {pres_s1.train_final_rows} rows | Sliced Eval Windows: {pres_s1.eval_rows} rows",
        roi_name="Japan Tohoku Subduction Zone",
        target_name="seis_core_magnitude",
        eval_window_mode="corridors",
    )
    vis.render(
        input_csv_or_df=df_val_s1,
        training_csv_or_df=pres_s1.train_df,
        output_path=s1_out_dir / "study_01_tohoku_kan_report.pdf",
        title="Tohoku Century M6.9+ Energetic Magnitude Forecast",
        subtitle=f"Model: KAN (Grid=6, Spline=3) | Train: {pres_s1.train_final_rows} rows | Sliced Eval Windows: {pres_s1.eval_rows} rows",
        roi_name="Japan Tohoku Subduction Zone",
        target_name="seis_core_magnitude",
        eval_window_mode="corridors",
    )

    print(f"  [✓] Study 1 Finished in {e_s1}s! Train Rows: {pres_s1.train_final_rows}, Val MSE: {metrics_s1.mse:.4f}, Peak Hit: {metrics_s1.peak_hit_rate:.1%}")
    studies_summary.append({
        "study_id": "Study_01_Tohoku_30D_KAN_M69",
        "paradigm": "KAN",
        "modality": "energetic",
        "train_rows": pres_s1.train_final_rows,
        "eval_rows": pres_s1.eval_rows,
        "mse": metrics_s1.mse,
        "rmse": metrics_s1.rmse,
        "r2": metrics_s1.r2,
        "peak_hit_rate": metrics_s1.peak_hit_rate,
        "elapsed_s": e_s1,
    })

    # -------------------------------------------------------------------------
    # Study 2: Deep Learning Tabular ResNet on Tohoku 7D Master (M >= 6.5+)
    # -------------------------------------------------------------------------
    print("\n>>> [Study 2/4] Deep Learning Tabular ResNet on Tohoku 7D Master (M >= 6.5+ Sliced Corridors)")
    cfg_s2 = PretreatmentConfig(
        mode="energetic",
        target_col="seis_core_magnitude",
        min_magnitude_threshold=6.5,
        eval_min_events=3,
        eval_max_events=5,
        auto_balance_dates=True,
        eval_window_mode="corridors",
        window_before=4,
        window_after=3,
        background_sample_ratio=0.10,
    )
    eng_s2 = MasterPretreatmentEngine(cfg_s2)
    t0 = time.time()
    s2_out_dir = STUDIES_OUT_DIR / "study_02_tohoku_deep_learning"
    metrics_s2, df_val_s2, pres_s2 = eng_s2.run_study(
        df_or_csv=tohoku_7d,
        model_type="deep_learning",
        study_name="Study_02_Tohoku_7D_DeepResNet_M65",
        epochs=35,
        output_dir=s2_out_dir,
        hidden_dim=64,
        num_layers=3,
    )
    e_s2 = round(time.time() - t0, 2)

    vis.render(
        input_csv_or_df=df_val_s2,
        training_csv_or_df=pres_s2.train_df,
        output_path=s2_out_dir / "study_02_tohoku_deep_learning_stacked.png",
        title="Tohoku 7D Multi-Scale Energetic Deep ResNet Forecast",
        subtitle=f"Model: Deep Tabular ResNet (Dim=64, L=3) | Train: {pres_s2.train_final_rows} rows | Sliced Eval Windows: {pres_s2.eval_rows} rows",
        roi_name="Japan Tohoku Subduction Zone",
        target_name="seis_core_magnitude",
        eval_window_mode="corridors",
    )
    vis.render(
        input_csv_or_df=df_val_s2,
        training_csv_or_df=pres_s2.train_df,
        output_path=s2_out_dir / "study_02_tohoku_deep_learning_report.pdf",
        title="Tohoku 7D Multi-Scale Energetic Deep ResNet Forecast",
        subtitle=f"Model: Deep Tabular ResNet (Dim=64, L=3) | Train: {pres_s2.train_final_rows} rows | Sliced Eval Windows: {pres_s2.eval_rows} rows",
        roi_name="Japan Tohoku Subduction Zone",
        target_name="seis_core_magnitude",
        eval_window_mode="corridors",
    )

    print(f"  [✓] Study 2 Finished in {e_s2}s! Train Rows: {pres_s2.train_final_rows}, Val MSE: {metrics_s2.mse:.4f}, Peak Hit: {metrics_s2.peak_hit_rate:.1%}")
    studies_summary.append({
        "study_id": "Study_02_Tohoku_7D_DeepResNet_M65",
        "paradigm": "Deep Learning",
        "modality": "energetic",
        "train_rows": pres_s2.train_final_rows,
        "eval_rows": pres_s2.eval_rows,
        "mse": metrics_s2.mse,
        "rmse": metrics_s2.rmse,
        "r2": metrics_s2.r2,
        "peak_hit_rate": metrics_s2.peak_hit_rate,
        "elapsed_s": e_s2,
    })

    # -------------------------------------------------------------------------
    # Study 3: LCS Evolutionary Rule Mining on Tohoku 30D Master
    # -------------------------------------------------------------------------
    print("\n>>> [Study 3/4] LCS Evolutionary Rule Mining on Tohoku 30D Master")
    cfg_s3 = PretreatmentConfig(
        mode="energetic",
        target_col="seis_core_magnitude",
        min_magnitude_threshold=6.5,
        eval_min_events=3,
        eval_max_events=5,
        auto_balance_dates=True,
        eval_window_mode="corridors",
        window_before=3,
        window_after=2,
        background_sample_ratio=0.15,
    )
    eng_s3 = MasterPretreatmentEngine(cfg_s3)
    t0 = time.time()
    s3_out_dir = STUDIES_OUT_DIR / "study_03_tohoku_lcs"
    metrics_s3, df_val_s3, pres_s3 = eng_s3.run_study(
        df_or_csv=tohoku_30d,
        model_type="lcs",
        study_name="Study_03_Tohoku_30D_LCS_Rules",
        epochs=20,
        output_dir=s3_out_dir,
        population_size=120,
        learning_rate=0.10,
    )
    e_s3 = round(time.time() - t0, 2)

    vis.render(
        input_csv_or_df=df_val_s3,
        training_csv_or_df=pres_s3.train_df,
        output_path=s3_out_dir / "study_03_tohoku_lcs_stacked.png",
        title="Tohoku 30D LCS Evolutionary Rule Validation",
        subtitle=f"Model: LCS Genetic Rule Discovery (Pop=120, LR=0.10) | Train: {pres_s3.train_final_rows} rows | Sliced Eval Windows: {pres_s3.eval_rows} rows",
        roi_name="Japan Tohoku Subduction Zone",
        target_name="seis_core_magnitude",
        eval_window_mode="corridors",
    )

    print(f"  [✓] Study 3 Finished in {e_s3}s! Train Rows: {pres_s3.train_final_rows}, Val MSE: {metrics_s3.mse:.4f}, Peak Hit: {metrics_s3.peak_hit_rate:.1%}")
    studies_summary.append({
        "study_id": "Study_03_Tohoku_30D_LCS_Rules",
        "paradigm": "LCS",
        "modality": "energetic",
        "train_rows": pres_s3.train_final_rows,
        "eval_rows": pres_s3.eval_rows,
        "mse": metrics_s3.mse,
        "rmse": metrics_s3.rmse,
        "r2": metrics_s3.r2,
        "peak_hit_rate": metrics_s3.peak_hit_rate,
        "elapsed_s": e_s3,
    })

    # -------------------------------------------------------------------------
    # Study 4: KAN Location (Latitude) Forecasting on California 30D Master
    # -------------------------------------------------------------------------
    print("\n>>> [Study 4/4] KAN Location (Latitude) Forecasting on California 30D Master")
    cfg_s4 = PretreatmentConfig(
        mode="location",
        target_col="seis_core_latitude",
        min_magnitude_threshold=5.5,
        window_before=3,
        window_after=2,
        background_sample_ratio=0.15,
        train_start_date="1920-01-01",
        train_end_date="2015-12-31",
        eval_start_date="2016-01-01",
        eval_end_date="2026-08-01",
        eval_window_mode="continuous",
    )
    eng_s4 = MasterPretreatmentEngine(cfg_s4)
    t0 = time.time()
    s4_out_dir = STUDIES_OUT_DIR / "study_04_california_location_kan"
    metrics_s4, df_val_s4, pres_s4 = eng_s4.run_study(
        df_or_csv=california_30d,
        model_type="kan",
        study_name="Study_04_California_30D_KAN_Latitude",
        epochs=35,
        output_dir=s4_out_dir,
        grid_size=5,
        spline_order=3,
    )
    e_s4 = round(time.time() - t0, 2)

    vis.render(
        input_csv_or_df=df_val_s4,
        training_csv_or_df=pres_s4.train_df,
        output_path=s4_out_dir / "study_04_california_location_kan_stacked.png",
        title="California Century Epicenter Latitude Forecast",
        subtitle=f"Model: KAN Location (Grid=5, Spline=3) | Train: {pres_s4.train_final_rows} rows | Continuous Eval: {pres_s4.eval_rows} rows",
        roi_name="California Fault Complex (USGS)",
        target_name="seis_core_latitude",
        eval_window_mode="continuous",
    )

    print(f"  [✓] Study 4 Finished in {e_s4}s! Train Rows: {pres_s4.train_final_rows}, Val MSE: {metrics_s4.mse:.4f}, Peak Hit: {metrics_s4.peak_hit_rate:.1%}")
    studies_summary.append({
        "study_id": "Study_04_California_30D_KAN_Latitude",
        "paradigm": "KAN",
        "modality": "location",
        "train_rows": pres_s4.train_final_rows,
        "eval_rows": pres_s4.eval_rows,
        "mse": metrics_s4.mse,
        "rmse": metrics_s4.rmse,
        "r2": metrics_s4.r2,
        "peak_hit_rate": metrics_s4.peak_hit_rate,
        "elapsed_s": e_s4,
    })

    # -------------------------------------------------------------------------
    # Final Benchmark Report Table
    # -------------------------------------------------------------------------
    df_summary = pd.DataFrame(studies_summary)
    df_summary.to_csv(STUDIES_OUT_DIR / "benchmark_studies_summary.csv", index=False)

    print("\n" + "=" * 80)
    print("ALL 4 SCIENTIFIC STUDIES COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(df_summary[["study_id", "paradigm", "modality", "train_rows", "eval_rows", "mse", "peak_hit_rate", "elapsed_s"]].to_string(index=False))


if __name__ == "__main__":
    run_all_studies()

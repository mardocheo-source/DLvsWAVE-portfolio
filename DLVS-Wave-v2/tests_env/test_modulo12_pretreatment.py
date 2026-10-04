"""Test Modulo 12: Master Pretreatment Engine & Pi-Zipper (Cerniera di Pi) Sub-Sampling."""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from pretreatment import MasterPretreatmentEngine, PretreatmentConfig, PI_DIGIT_TRIPLETS


def test_pi_zipper_stepping():
    print("[TEST 12.1] Testing Pi-Zipper (Cerniera di Pi) Continuous Stepping Algorithm...")
    assert len(PI_DIGIT_TRIPLETS) == 100
    assert PI_DIGIT_TRIPLETS[0] == 141
    assert PI_DIGIT_TRIPLETS[1] == 592

    # 1000 background indices at 10% sampling ratio
    bg_indices = list(range(1000))
    sampled = MasterPretreatmentEngine.sample_pi_zipper(bg_indices, sample_ratio=0.10, seed=42)

    # Must produce ~90..110 samples
    assert 85 <= len(sampled) <= 115, f"Unexpected sample count: {len(sampled)}"

    # Check stride smoothness (no consecutive duplicate steps, no gaps > 20)
    steps = [sampled[i+1] - sampled[i] for i in range(len(sampled) - 1)]
    assert min(steps) >= 5, f"Step too small: {min(steps)}"
    assert max(steps) <= 16, f"Step too large: {max(steps)}"
    print(f"  [✓] Pi-Zipper (Cerniera) Verified! {len(bg_indices)} background rows -> {len(sampled)} sampled rows (stride span: [{min(steps)}..{max(steps)}])!")


def test_event_corridor_extraction():
    print("[TEST 12.2] Testing Peak Event Context Corridors [t - 4, t + 3]...")
    dates = pd.date_range("2024-01-01", periods=100, freq="D").strftime("%Y-%m-%d")
    mags = [0.0] * 100
    mags[20] = 7.8
    mags[60] = 8.2

    df_synthetic = pd.DataFrame({
        "date": dates,
        "seis_core_magnitude": mags,
        "seis_core_latitude": [38.0] * 100,
        "seis_core_longitude": [142.0] * 100,
        "seis_core_depth": [25.0] * 100,
        "astro_var_1": np.linspace(1, 100, 100),
        "astro_var_2": np.sin(np.linspace(1, 100, 100)),
    })

    cfg = PretreatmentConfig(
        mode="energetic",
        target_col="seis_core_magnitude",
        min_magnitude_threshold=7.0,
        window_before=4,
        window_after=3,
        background_sample_ratio=0.10,
        train_start_date="2024-01-01",
        train_end_date="2024-03-20",  # 80 days
        eval_start_date="2024-03-21",
        eval_end_date="2024-04-10",   # 20 days
    )
    engine = MasterPretreatmentEngine(cfg)
    res = engine.process(df_synthetic)

    # Corridors: day 16..23 (8 days) and day 56..63 (8 days) = 16 mandatory days
    assert res.train_corridor_rows == 16, f"Expected 16 corridor days, got {res.train_corridor_rows}"
    assert 5 <= res.train_background_rows <= 10, f"Unexpected background sample count: {res.train_background_rows}"
    assert res.train_final_rows == res.train_corridor_rows + res.train_background_rows

    assert "seis_core_latitude" not in res.train_df.columns
    assert "seis_core_longitude" not in res.train_df.columns
    assert "seis_core_depth" not in res.train_df.columns
    assert "seis_core_magnitude" in res.train_df.columns
    print(f"  [✓] Peak Corridors Verified ({res.train_corridor_rows} corridor + {res.train_background_rows} Pi-zipper background = {res.train_final_rows} total train rows)!")


def test_modality_isolation_location():
    print("[TEST 12.3] Testing Location Modality Target Isolation...")
    dates = pd.date_range("2024-01-01", periods=20, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame({
        "date": dates,
        "seis_core_magnitude": [5.0] * 20,
        "seis_core_latitude": [37.5 + 0.1 * i for i in range(20)],
        "seis_core_longitude": [140.0] * 20,
        "seis_core_depth": [15.0] * 20,
        "astro_val": np.linspace(0, 10, 20),
    })
    cfg = PretreatmentConfig(mode="location", target_col="seis_core_latitude", background_sample_ratio=1.0)
    engine = MasterPretreatmentEngine(cfg)
    res = engine.process(df)

    assert "seis_core_latitude" in res.train_df.columns
    assert "seis_core_magnitude" not in res.train_df.columns
    assert "seis_core_longitude" not in res.train_df.columns
    assert "seis_core_depth" not in res.train_df.columns
    print("  [✓] Location Modality Target Isolation Verified 100%!")


def test_study_execution_on_real_samples():
    print("[TEST 12.4] Running End-to-End Study on Tohoku Reference Dataset...")
    sample_csv = Path(__file__).resolve().parent.parent / "samples" / "sample_1_japan_tohoku" / "master_1d_uncompressed.csv"
    if not sample_csv.exists():
        print("  [!] Skipping real sample test: sample CSV missing.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = PretreatmentConfig(
            mode="energetic",
            target_col="seis_core_magnitude",
            min_magnitude_threshold=5.0,
            window_before=3,
            window_after=2,
            background_sample_ratio=0.20,
            train_start_date="2024-01-01",
            train_end_date="2024-03-31",
            eval_start_date="2024-04-01",
            eval_end_date="2024-04-30",
            eval_window_mode="continuous",
        )
        engine = MasterPretreatmentEngine(cfg)

        metrics, df_val, p_res = engine.run_study(
            df_or_csv=sample_csv,
            model_type="kan",
            study_name="Study_Tohoku_M5_KAN",
            epochs=30,
            output_dir=tmpdir,
            grid_size=4,
            spline_order=3,
        )

        assert (Path(tmpdir) / "Study_Tohoku_M5_KAN_validation.csv").exists()
        assert (Path(tmpdir) / "Study_Tohoku_M5_KAN_metrics.json").exists()
        assert len(df_val) == 30
        print(f"  [✓] Study Complete! Train Rows: {p_res.train_final_rows}, Eval Days: {p_res.eval_rows}, Val MSE: {metrics.mse:.4f}")



def test_auto_date_balancing_and_eval_corridors():
    print("[TEST 12.5] Testing Auto Date Balancing (eval_min_events 3..5) & Eval Corridor Slicing...")
    dates = pd.date_range("2020-01-01", periods=100, freq="D").strftime("%Y-%m-%d")
    mags = [3.0] * 100
    # Add 8 peak events
    for p_idx in [10, 25, 40, 55, 70, 80, 90, 95]:
        mags[p_idx] = 7.2

    df = pd.DataFrame({
        "date": dates,
        "seis_core_magnitude": mags,
        "astro_feature1": np.linspace(0, 10, 100),
    })

    cfg = PretreatmentConfig(
        mode="energetic",
        target_col="seis_core_magnitude",
        min_magnitude_threshold=6.9,
        eval_min_events=3,
        eval_max_events=5,
        auto_balance_dates=True,
        eval_window_mode="corridors",
        window_before=2,
        window_after=2,
        background_sample_ratio=0.10,
    )
    engine = MasterPretreatmentEngine(cfg)
    res = engine.process(df)

    assert 3 <= res.eval_major_events_count <= 5
    assert res.eval_rows < 50
    print(f"  [✓] Auto Date Balancing Verified: {res.eval_major_events_count} major events in eval ({res.eval_rows} corridor rows)!")


if __name__ == "__main__":
    test_pi_zipper_stepping()
    test_event_corridor_extraction()
    test_modality_isolation_location()
    test_study_execution_on_real_samples()
    test_auto_date_balancing_and_eval_corridors()


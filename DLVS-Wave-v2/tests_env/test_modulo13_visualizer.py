"""Test Modulo 13: Forecasting & Validation Visualizer (Dual Stacked Layout & PDF Export)."""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from models.plotting import ForecastingVisualizer


def test_visualizer_validation_stacked():
    print("[TEST 13.1] Testing Validation Plot Rendering with Stacked Training Panel...")
    dates_eval = pd.date_range("2024-04-01", periods=30, freq="D").strftime("%Y-%m-%d")
    df_eval = pd.DataFrame({
        "date": dates_eval,
        "actual": [0.0 if i % 5 != 0 else 6.2 for i in range(30)],
        "predicted_seis_core_magnitude": [0.1 + 0.05 * i for i in range(30)],
        "error": [0.0] * 30,
        "abs_error": [0.0] * 30,
    })

    dates_train = pd.date_range("2024-01-01", periods=90, freq="D").strftime("%Y-%m-%d")
    df_train = pd.DataFrame({
        "date": dates_train,
        "seis_core_magnitude": [0.0 if i % 10 != 0 else 7.1 for i in range(90)],
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        out_png = Path(tmpdir) / "test_stacked_plot.png"
        out_pdf = Path(tmpdir) / "test_report.pdf"

        vis = ForecastingVisualizer(dpi=150)
        vis.render(
            input_csv_or_df=df_eval,
            training_csv_or_df=df_train,
            output_path=out_png,
            title="Test Validation Forecast",
            roi_name="Test Region",
            model_name="KAN",
            target_name="seis_core_magnitude",
        )
        assert out_png.exists()
        assert out_png.stat().st_size > 10000

        vis.render(
            input_csv_or_df=df_eval,
            training_csv_or_df=df_train,
            output_path=out_pdf,
            title="Test Validation Report",
        )
        assert out_pdf.exists()
        assert out_pdf.stat().st_size > 5000

        print(f"  [✓] Dual Stacked PNG ({out_png.stat().st_size} bytes) & PDF ({out_pdf.stat().st_size} bytes) Generated Successfully!")


def test_visualizer_pure_forecast():
    print("[TEST 13.2] Testing Pure Forecast Single Panel Trajectory...")
    dates_fc = pd.date_range("2026-09-01", periods=20, freq="D").strftime("%Y-%m-%d")
    df_fc = pd.DataFrame({
        "date": dates_fc,
        "forecasted_mag": np.sin(np.linspace(0, np.pi, 20)) * 3.0 + 4.0,
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        out_png = Path(tmpdir) / "test_pure_forecast.png"
        vis = ForecastingVisualizer(dpi=150)
        vis.render(
            input_csv_or_df=df_fc,
            output_path=out_png,
            title="Pure Forecast Stream",
            target_name="forecasted_mag",
        )
        assert out_png.exists()
        assert out_png.stat().st_size > 10000
        print("  [✓] Pure Forecast Single Panel Verified!")


def test_visualizer_sliced_corridors():
    print("[TEST 13.3] Testing Sliced Corridor Rendering with Gap Dividers...")
    # Discontinuous dates simulating 3 event corridors
    dates_eval = ["2021-04-10", "2021-04-15", "2021-04-20",
                  "2022-02-10", "2022-02-15", "2022-02-20",
                  "2025-12-01", "2025-12-05", "2025-12-10"]
    df_eval = pd.DataFrame({
        "date": dates_eval,
        "actual": [0.0, 7.1, 0.0, 0.0, 7.3, 0.0, 0.0, 7.6, 0.0],
        "predicted_seis_core_magnitude": [0.2, 5.5, 0.1, 0.3, 6.0, 0.2, 0.1, 6.8, 0.1],
        "error": [0.0] * 9,
        "abs_error": [0.0] * 9,
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        out_png = Path(tmpdir) / "test_corridor_plot.png"
        vis = ForecastingVisualizer(dpi=150)
        vis.render(
            input_csv_or_df=df_eval,
            output_path=out_png,
            title="Test Sliced Corridors",
            eval_window_mode="corridors",
        )
        assert out_png.exists()
        assert out_png.stat().st_size > 10000
        print("  [✓] Sliced Corridor Gap Dividers & Plot Verified!")


if __name__ == "__main__":
    test_visualizer_validation_stacked()
    test_visualizer_pure_forecast()
    test_visualizer_sliced_corridors()


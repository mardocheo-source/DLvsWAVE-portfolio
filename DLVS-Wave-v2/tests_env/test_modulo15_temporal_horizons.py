"""Test Modulo 15: progressive validation horizons and multi-page reports."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.models.plotting import ForecastingVisualizer
from src.temporal_validation import build_progressive_horizon_metrics, derive_temporal_ensemble_weights


def _validation(predicted_second_peak: float = 0.0) -> pd.DataFrame:
    dates = list(pd.date_range("2025-01-01", periods=5, freq="7D")) + list(
        pd.date_range("2025-04-01", periods=5, freq="7D")
    )
    actual = [0.0, 0.0, 7.4, 0.0, 0.0, 0.0, 0.0, 7.2, 0.0, 0.0]
    predicted = [0.0, 0.0, 7.2, 0.0, 0.0, 0.0, 0.0, predicted_second_peak, 0.0, 0.0]
    return pd.DataFrame(
        {"date": dates, "actual": actual, "predicted_seis_core_magnitude": predicted}
    )


def _forecast() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=30, freq="7D"),
            "forecasted_seis_core_magnitude": np.linspace(0.0, 7.0, 30),
        }
    )


def test_progressive_certification_and_translation() -> None:
    print("[TEST 15.1] Testing progressive temporal certification and date translation...")
    metrics = build_progressive_horizon_metrics(
        _validation(), _forecast(), peak_threshold=6.9, max_events=2, window_span=1
    )
    assert len(metrics) == 2
    assert bool(metrics.iloc[0]["cumulative_supported"])
    assert not bool(metrics.iloc[1]["cumulative_supported"])
    assert bool(metrics.iloc[0]["consecutive_supported"])
    assert not bool(metrics.iloc[1]["consecutive_supported"])
    first_lead = pd.Timestamp(metrics.iloc[0]["window_end_date"]) - pd.Timestamp(
        metrics.iloc[0]["validation_origin_date"]
    )
    translated_lead = pd.Timestamp(metrics.iloc[0]["forecast_equivalent_end_date"]) - pd.Timestamp(
        metrics.iloc[0]["forecast_origin_date"]
    )
    assert first_lead == translated_lead
    print("  [✓] W1 is supported, cumulative W2 degrades, and lead duration is translated exactly.")


def test_temporal_weights_favor_supported_model() -> None:
    print("[TEST 15.2] Testing stage-specific ensemble weighting...")
    good = build_progressive_horizon_metrics(
        _validation(predicted_second_peak=7.0), _forecast(), peak_threshold=6.9, max_events=2, window_span=1
    )
    degrading = build_progressive_horizon_metrics(
        _validation(predicted_second_peak=0.0), _forecast(), peak_threshold=6.9, max_events=2, window_span=1
    )
    weights = derive_temporal_ensemble_weights({"good": good, "degrading": degrading})
    assert np.allclose(weights[["weight_good", "weight_degrading"]].sum(axis=1), 1.0)
    assert weights.iloc[1]["weight_good"] > 0.95
    print("  [✓] A model passing the cumulative stage receives dominant event-centric weight.")


def test_four_page_forecast_report() -> None:
    print("[TEST 15.3] Testing validation + metrics + forecast + temporal PDF pages...")
    validation = _validation()
    forecast = _forecast()
    temporal = build_progressive_horizon_metrics(
        validation, forecast, peak_threshold=6.9, max_events=2, window_span=1
    )
    training = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=20, freq="30D"),
            "seis_core_magnitude": [7.0 if index in (5, 15) else 0.0 for index in range(20)],
            "feature": np.arange(20),
        }
    )
    metrics = {
        "sample_count": 10, "mse": 3.0, "rmse": np.sqrt(3.0), "mae": 0.8, "r2": 0.2,
        "pearson_corr": 0.4, "peak_hit_rate": 0.5, "peak_magnitude_bias": -0.2,
        "peak_timing_error": 1.0, "depression_mae": 0.1, "precision": 1.0, "recall": 0.5,
        "f1_score": 2 / 3, "true_positives": 1, "false_positives": 0, "false_negatives": 1,
        "true_negatives": 8, "directional_accuracy": 0.7,
    }
    with tempfile.TemporaryDirectory() as temporary_dir:
        output = Path(temporary_dir) / "four_page_report.pdf"
        figure = ForecastingVisualizer(dpi=90).render(
            validation,
            training,
            output,
            metrics,
            forecast_csv_or_df=forecast,
            temporal_metrics_csv_or_df=temporal,
            temporal_forecast_csv_or_df=forecast,
            target_name="seis_core_magnitude",
            eval_max_events=2,
            eval_min_mag=6.9,
            eval_window_span=1,
        )
        plt.close(figure)
        assert len(PdfReader(output).pages) == 4
        assert output.stat().st_size > 20_000
    print("  [✓] Four-page PDF report generated and reopened successfully.")


def run_modulo15_suite() -> None:
    test_progressive_certification_and_translation()
    test_temporal_weights_favor_supported_model()
    test_four_page_forecast_report()


if __name__ == "__main__":
    run_modulo15_suite()

"""Test Modulo 11: Machine Learning & Forecasting Models (KAN, LCS, Deep Learning) & Unified Engine."""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from models.deep_learning import DeepLearningForecastingModel
from models.engine import ForecastingEngine, create_forecasting_model
from models.kan import KANForecastingModel
from models.lcs import LCSForecastingModel


def create_mock_dataset(n_samples: int = 100) -> tuple[pd.DataFrame, pd.Series]:
    """Generates synthetic physics dataset with known non-linear pattern: y = sin(x1) * cos(x2) + 0.5 * x3."""
    np.random.seed(42)
    X = pd.DataFrame({
        "astro_var_1": np.random.uniform(-3.0, 3.0, n_samples),
        "astro_var_2": np.random.uniform(-3.0, 3.0, n_samples),
        "astro_var_3": np.random.uniform(-3.0, 3.0, n_samples),
        "astro_var_4": np.random.uniform(-3.0, 3.0, n_samples),
    })
    y = np.sin(X["astro_var_1"]) * np.cos(X["astro_var_2"]) + 0.5 * X["astro_var_3"] + np.random.normal(0, 0.05, n_samples)
    return X, y


def test_kan_model():
    print("[TEST 11.1] Testing Kolmogorov-Arnold Network (KAN) with Tunable Splines...")
    X, y = create_mock_dataset(120)
    model = KANForecastingModel(grid_size=6, spline_order=3)

    params = model.get_tunable_params()
    assert params["grid_size"] == 6
    assert params["spline_order"] == 3

    info = model.fit(X.iloc[:90], y.iloc[:90], epochs=50, verbose=False)
    assert info["model"] == "KAN"
    assert model.is_fitted

    metrics, df_eval = model.evaluate(X.iloc[90:], y.iloc[90:])
    assert metrics.sample_count == 30
    assert metrics.mse >= 0.0
    print(f"  [✓] KAN Fit & Eval Passed! Val MSE: {metrics.mse:.4f}, R²: {metrics.r2:.4f}")

    # Test Save & Load
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        model.save(tmp.name)
        loaded_model = KANForecastingModel()
        loaded_model.load(tmp.name)
        preds_orig = model.predict(X.iloc[90:])
        preds_loaded = loaded_model.predict(X.iloc[90:])
        np.testing.assert_allclose(preds_orig, preds_loaded, atol=1e-5)
    print("  [✓] KAN Checkpoint Save/Load Verified 100%!")


def test_lcs_model():
    print("[TEST 11.2] Testing Learning Classifier System (LCS) Rule-Based Pattern Discovery...")
    X, y = create_mock_dataset(100)
    model = LCSForecastingModel(population_size=80, learning_rate=0.15)

    params = model.get_tunable_params()
    assert params["population_size"] == 80
    assert params["learning_rate"] == 0.15

    info = model.fit(X.iloc[:80], y.iloc[:80], epochs=25, verbose=False)
    assert info["model"] == "LCS"
    assert len(model.population) <= 80
    assert model.is_fitted

    metrics, df_eval = model.evaluate(X.iloc[80:], y.iloc[80:])
    assert metrics.sample_count == 20
    print(f"  [✓] LCS Discovered {len(model.population)} Rules! Val MSE: {metrics.mse:.4f}")

    # Test Save & Load JSON Rules
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        model.save(tmp.name)
        loaded_model = LCSForecastingModel()
        loaded_model.load(tmp.name)
        assert len(loaded_model.population) == len(model.population)
        preds_orig = model.predict(X.iloc[80:])
        preds_loaded = loaded_model.predict(X.iloc[80:])
        np.testing.assert_allclose(preds_orig, preds_loaded, atol=1e-4)
    print("  [✓] LCS JSON Rule Persistence Verified 100%!")


def test_deep_learning_model():
    print("[TEST 11.3] Testing Deep Learning Tabular ResNet...")
    X, y = create_mock_dataset(120)
    model = DeepLearningForecastingModel(hidden_dim=32, num_layers=2)

    params = model.get_tunable_params()
    assert params["hidden_dim"] == 32
    assert params["num_layers"] == 2

    info = model.fit(X.iloc[:90], y.iloc[:90], epochs=50, verbose=False)
    assert info["model"] == "Deep Learning"
    assert model.is_fitted

    metrics, df_eval = model.evaluate(X.iloc[90:], y.iloc[90:])
    assert metrics.sample_count == 30
    assert metrics.mse >= 0.0
    print(f"  [✓] Deep Learning Fit & Eval Passed! Val MSE: {metrics.mse:.4f}, R²: {metrics.r2:.4f}")

    # Test Save & Load
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        model.save(tmp.name)
        loaded_model = DeepLearningForecastingModel()
        loaded_model.load(tmp.name)
        preds_orig = model.predict(X.iloc[90:])
        preds_loaded = loaded_model.predict(X.iloc[90:])
        np.testing.assert_allclose(preds_orig, preds_loaded, atol=1e-5)
    print("  [✓] Deep Learning Checkpoint Save/Load Verified 100%!")


def test_forecasting_engine_modes():
    print("[TEST 11.4] Testing Unified ForecastingEngine (Validation & Forecasting Streams)...")
    # Build complete mock master CSV
    dates = pd.date_range("2024-01-01", periods=60, freq="D").strftime("%Y-%m-%d")
    df_mock = pd.DataFrame({
        "date": dates,
        "seis_core_magnitude": np.random.uniform(4.0, 7.5, 60),
        "astro_var_1": np.linspace(10, 50, 60),
        "astro_var_2": np.linspace(0.1, 0.9, 60),
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        input_csv = Path(tmpdir) / "test_master.csv"
        df_mock.to_csv(input_csv, index=False)

        val_csv = Path(tmpdir) / "val_output.csv"
        metrics_json = Path(tmpdir) / "metrics.json"
        ckpt_path = Path(tmpdir) / "model_ckpt.pt"

        # 1. Validation Mode
        engine = ForecastingEngine(model_type="kan", grid_size=4, spline_order=3)
        metrics, df_val = engine.run_validation(
            input_data=input_csv,
            target_col="seis_core_magnitude",
            train_ratio=0.75,
            epochs=30,
            model_save_path=ckpt_path,
            output_csv=val_csv,
            output_metrics_json=metrics_json,
        )

        assert val_csv.exists()
        assert metrics_json.exists()
        assert "predicted_seis_core_magnitude" in df_val.columns
        assert "actual" in df_val.columns
        assert "error" in df_val.columns
        print("  [✓] Engine Validation Mode Stream Generated & Verified!")

        # 2. Pure Forecasting Mode with Custom Column Name
        fc_csv = Path(tmpdir) / "forecast_output.csv"
        df_fc = engine.run_forecast(
            input_data=input_csv,
            target_col="seis_core_magnitude",
            output_target_name="forecasted_mag",
            model_load_path=ckpt_path,
            output_csv=fc_csv,
        )

        assert fc_csv.exists()
        assert list(df_fc.columns) == ["date", "forecasted_mag"]
        assert len(df_fc) == 60
        print("  [✓] Engine Pure Forecasting Stream [date, forecasted_mag] Verified!")


if __name__ == "__main__":
    test_kan_model()
    test_lcs_model()
    test_deep_learning_model()
    test_forecasting_engine_modes()

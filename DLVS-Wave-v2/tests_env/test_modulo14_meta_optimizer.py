"""Test Modulo 14: Phase 2 deep-surrogate meta-optimizer."""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pandas as pd
import torch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.meta_optimizer.engine import DeepMetaOptimizer
from src.meta_optimizer.plotting import plot_phase2_convergence_report
from src.meta_optimizer.surrogate import DeepSurrogateModel, ParameterEncoder, compute_expected_improvement
from src.models.base import ModelMetrics
from src.pretreatment import PretreatmentResult


def _phase1_frame(model_type: str = "lcs", rows: int = 9) -> pd.DataFrame:
    records = []
    for index in range(rows):
        common = {
            "trial_number": index,
            "objective_loss": 11.0 - index * 0.2,
            "val_mse": 9.0 - index * 0.1,
            "val_f1_score": 0.15 + index * 0.01,
            "val_depression_mae": 1.0 + index * 0.01,
            "train_start_date": f"{1900 + (index % 9) * 10}-01-01",
            "window_before": 2 + index % 5,
            "window_after": 2 + (index + 1) % 5,
            "background_sample_ratio": 0.05 + (index % 5) * 0.05,
        }
        if model_type == "lcs":
            common.update(
                population_size=50 + (index % 9) * 25,
                learning_rate=0.05 + (index % 6) * 0.05,
                crossover_rate=0.6 + (index % 4) * 0.1,
                mutation_rate=0.02 + (index % 5) * 0.02,
            )
        elif model_type == "kan":
            common.update(grid_size=3 + index % 6, spline_order=2 + index % 3, learning_rate=0.002)
        else:
            common.update(hidden_dim=[32, 64, 96, 128][index % 4], num_layers=2 + index % 4,
                          dropout=(index % 6) * 0.05, learning_rate=0.001)
        records.append(common)
    return pd.DataFrame(records)


def _master_frame(rows: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    magnitude = np.zeros(rows, dtype=np.float32)
    for index, value in zip((50, 120, 190, 260, 340, 430), (7.0, 7.2, 6.9, 7.1, 7.3, 7.0)):
        magnitude[index] = value
    return pd.DataFrame(
        {
            "date": pd.date_range("1900-01-01", periods=rows, freq="365D").strftime("%Y-%m-%d"),
            "seis_core_magnitude": magnitude,
            "astro_feature_a": np.sin(np.linspace(0, 9, rows)),
            "astro_feature_b": rng.normal(size=rows),
        }
    )


def _metrics(mse: float = 1.0, f1: float = 0.75, depression: float = 0.5, samples: int = 7) -> ModelMetrics:
    return ModelMetrics(
        mse=mse, rmse=float(np.sqrt(mse)), mae=0.7, r2=0.2, pearson_corr=0.4,
        peak_hit_rate=0.8, directional_accuracy=0.6, true_positives=2, false_positives=1,
        false_negatives=0, true_negatives=4, precision=2 / 3, recall=1.0, f1_score=f1,
        peak_magnitude_bias=-0.2, peak_timing_error=1.0, depression_mae=depression,
        sample_count=samples,
    )


def test_parameter_domains_and_differentiable_ei() -> None:
    print("[TEST 14.1] Testing parameter projection and differentiable MC-Dropout EI...")
    examples = {
        "kan": {"train_start_date": "1950-01-01", "window_before": 3, "window_after": 5,
                "background_sample_ratio": 0.15, "grid_size": 7, "spline_order": 3, "learning_rate": 0.004},
        "deep_learning": {"train_start_date": "1960-01-01", "window_before": 4, "window_after": 6,
                          "background_sample_ratio": 0.20, "hidden_dim": 96, "num_layers": 4,
                          "dropout": 0.15, "learning_rate": 0.001},
        "lcs": {"train_start_date": "1970-01-01", "window_before": 5, "window_after": 2,
                "background_sample_ratio": 0.10, "population_size": 175, "learning_rate": 0.20,
                "crossover_rate": 0.8, "mutation_rate": 0.06},
    }
    for model_type, params in examples.items():
        encoder = ParameterEncoder(model_type)
        decoded = encoder.decode(encoder.encode(params))
        assert encoder.canonical_key(decoded) == encoder.canonical_key(params)

    model = DeepSurrogateModel(in_dim=7, hidden_dim=16, num_blocks=1)
    latent = torch.full((1, 7), 0.5, requires_grad=True)
    mean, std = model.predict_with_uncertainty(latent, n_samples=5, differentiable=True)
    loss = -compute_expected_improvement(mean, std, best_loss=0.0).mean()
    loss.backward()
    assert latent.grad is not None and torch.isfinite(latent.grad).all()
    print("  [✓] All model domains round-trip and EI propagates finite latent gradients.")


def test_incremental_resume_and_plotting() -> None:
    print("[TEST 14.2] Testing incremental persistence, resume, and comparison plotting...")
    with tempfile.TemporaryDirectory() as temporary_dir:
        root = Path(temporary_dir)
        trials_path = root / "optuna_trials_lcs.csv"
        _phase1_frame().to_csv(trials_path, index=False)
        output = root / "phase2_deep_meta_opt"

        def fake_fit(self, params, trial_number):
            evaluation = pd.DataFrame(
                {"date": pd.date_range("2020-01-01", periods=7, freq="7D").strftime("%Y-%m-%d"),
                 "seis_core_magnitude": [0, 0, 7, 0, 0, 7.1, 0], "astro_feature_a": np.arange(7)}
            )
            result = PretreatmentResult(
                train_df=evaluation.copy(), eval_df=evaluation, target_col="seis_core_magnitude",
                feature_cols=["astro_feature_a"], total_raw_rows=14, train_corridor_rows=5,
                train_background_rows=2, train_final_rows=7, eval_rows=7,
                eval_major_events_count=2, study_id="fake", metadata={"date_col": "date"},
            )
            validation = _metrics(mse=0.8 + trial_number * 0.02, f1=0.8, depression=0.4)
            comparison = pd.DataFrame(
                {"actual": evaluation["seis_core_magnitude"], "predicted": evaluation["seis_core_magnitude"] * 0.9,
                 "error": np.zeros(7), "abs_error": np.zeros(7)}
            )
            return _metrics(), validation, comparison, result, None

        optimizer = DeepMetaOptimizer(
            trials_path, _master_frame(), "lcs", output_dir=output, device="cpu", timeout_seconds=20,
            max_meta_trials=2, surrogate_epochs=2, retrain_epochs=1, candidate_batch_size=2,
        )
        optimizer._fit_and_evaluate = types.MethodType(fake_fit, optimizer)
        first = optimizer.run()
        assert first["meta_iterations"] == 2 and first["successful_meta_trials"] == 2
        records = pd.read_csv(output / "meta_trials_lcs.csv")
        assert len(records) == 2 and records["meta_trial_number"].is_unique
        assert set(records["actual_device"]) == {"cpu"}

        resumed = DeepMetaOptimizer(
            trials_path, _master_frame(), "lcs", output_dir=output, device="cpu", timeout_seconds=20,
            max_meta_trials=3, surrogate_epochs=2, retrain_epochs=1, candidate_batch_size=1,
        )
        resumed._fit_and_evaluate = types.MethodType(fake_fit, resumed)
        second = resumed.run()
        assert second["meta_iterations"] == 3
        assert len(pd.read_csv(output / "meta_trials_lcs.csv")) == 3
        assert (output / "phase2_comparison_lcs.json").exists()
        png_path = output / "comparison.png"
        paths = plot_phase2_convergence_report(trials_path, output, "lcs", png_path)
        assert Path(paths["png"]).stat().st_size > 10_000
        print("  [✓] Atomic records resume without duplication and comparison chart is generated.")


def test_real_cpu_lcs_smoke() -> None:
    print("[TEST 14.3] Running one real pretreatment → LCS evaluation on CPU...")
    with tempfile.TemporaryDirectory() as temporary_dir:
        root = Path(temporary_dir)
        trials_path = root / "optuna_trials_lcs.csv"
        _phase1_frame().to_csv(trials_path, index=False)
        optimizer = DeepMetaOptimizer(
            trials_path, _master_frame(), "lcs", output_dir=root / "phase2", device="cpu",
            timeout_seconds=30, max_meta_trials=1, surrogate_epochs=2, retrain_epochs=1,
            candidate_batch_size=1, model_epochs=1,
        )
        result = optimizer.run()
        assert result["actual_device"] == "cpu"
        assert result["meta_iterations"] == 1
        assert result["successful_meta_trials"] == 1
        assert (root / "phase2" / "meta_trials_lcs.csv").exists()
        print("  [✓] Real Phase 2 candidate completed through the CPU-only LCS path.")


def run_modulo14_suite() -> None:
    test_parameter_domains_and_differentiable_ei()
    test_incremental_resume_and_plotting()
    test_real_cpu_lcs_smoke()


if __name__ == "__main__":
    run_modulo14_suite()

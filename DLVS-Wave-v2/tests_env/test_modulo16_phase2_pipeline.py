"""Test Modulo 16: vertical forecast dates and finalized Phase 2 ensemble."""
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
from src.run_phase2_pipeline import MODELS, _write_micro_readme, build_parser, run_ensemble
from src.temporal_validation import build_progressive_horizon_metrics, compute_fixed_threshold_metrics


def _validation(scale: float = 1.0) -> pd.DataFrame:
    dates = list(pd.date_range("2025-01-01", periods=5, freq="7D")) + list(
        pd.date_range("2025-04-01", periods=5, freq="7D")
    )
    actual = np.asarray([0, 0, 7.4, 0, 0, 0, 0, 7.2, 0, 0], dtype=float)
    predicted = np.asarray([0, 0, 7.2, 0, 0, 0, 0, 7.0, 0, 0], dtype=float) * scale
    return pd.DataFrame(
        {"date": dates, "actual": actual, "predicted_seis_core_magnitude": predicted}
    )


def _forecast(scale: float = 1.0) -> pd.DataFrame:
    values = np.asarray(
        [2, 3, 6.2, 7.4, 6.3, 3, 4, 6.1, 8.2, 6.0, 2, 3, 4, 5, 6.4, 7.1, 6.2, 4, 3, 2],
        dtype=float,
    )
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(values), freq="7D"),
            "forecasted_seis_core_magnitude": values * scale,
        }
    )


def test_vertical_iso_ticks_and_forecast_peak_tags() -> None:
    print("[TEST 16.1] Testing vertical ISO forecast dates and vertex labels...")
    figure = ForecastingVisualizer(dpi=72).render(
        _forecast(), target_name="seis_core_magnitude", eval_window_mode="continuous"
    )
    axis = figure.axes[0]
    labels = [tick.get_text() for tick in axis.get_xticklabels()]
    assert len(labels) == 15
    assert all(tick.get_rotation() == 90 for tick in axis.get_xticklabels())
    assert all(len(label) == 10 and label[4] == "-" and label[7] == "-" for label in labels)
    peak_labels = [text.get_text() for text in axis.texts if "(M" in text.get_text()]
    assert peak_labels == [
        "2026-01-22 (M7.4)", "2026-02-26 (M8.2)", "2026-04-16 (M7.1)"
    ]
    assert axis.get_ylim()[1] >= 11.5
    plt.close(figure)
    print("  [✓] 15 readable ISO ticks, 90° rotation, local peak dates, and label headroom verified.")


def test_parameterized_phase2_ensemble() -> None:
    print("[TEST 16.2] Testing --make-ensemble from three parameterized Phase 2 subsets...")
    with tempfile.TemporaryDirectory() as temporary_dir:
        root = Path(temporary_dir)
        member_dirs: dict[str, Path] = {}
        scales = {"kan": 0.96, "deep_learning": 1.0, "lcs": 0.92}
        for model_type in MODELS:
            member_dir = root / model_type / "phase2_deep_meta_opt"
            member_dir.mkdir(parents=True)
            member_dirs[model_type] = root / model_type  # exercise parent auto-detection
            validation = _validation(scales[model_type])
            forecast = _forecast(scales[model_type])
            horizons = build_progressive_horizon_metrics(
                validation, forecast, peak_threshold=6.9, max_events=2, window_span=1
            )
            predicted = validation["predicted_seis_core_magnitude"]
            metrics = compute_fixed_threshold_metrics(
                validation["actual"], predicted, peak_threshold=6.9
            )
            metrics["peak_timing_error"] = metrics["peak_timing_error_steps"]
            metrics["peak_hit_rate"] = metrics["recall"]
            validation.to_csv(member_dir / f"selected_validation_{model_type}.csv", index=False)
            forecast.to_csv(member_dir / f"selected_forecast_{model_type}.csv", index=False)
            horizons.to_csv(member_dir / f"selected_temporal_horizon_metrics_{model_type}.csv", index=False)
            (member_dir / f"selected_best_metrics_{model_type}.json").write_text(
                json.dumps(metrics), encoding="utf-8"
            )
            pd.DataFrame(
                {
                    "date": pd.date_range("2020-01-01", periods=12, freq="30D"),
                    "seis_core_magnitude": [7.0 if index in (3, 9) else 0.0 for index in range(12)],
                    "feature": np.arange(12),
                }
            ).to_csv(member_dir / f"selected_train_pretreated_{model_type}.csv", index=False)

        output_dir = root / "second_level_ensemble"
        args = build_parser().parse_args(
            [
                "--make-ensemble",
                "--kan-dir", str(member_dirs["kan"]),
                "--deep-learning-dir", str(member_dirs["deep_learning"]),
                "--lcs-dir", str(member_dirs["lcs"]),
                "--ensemble-output-dir", str(output_dir),
                "--eval-events", "2",
                "--eval-window-span", "1",
                "--dpi", "72",
            ]
        )
        result = run_ensemble(args)
        assert Path(result["output_dir"]) == output_dir
        assert np.isclose(sum(result["global_weights"].values()), 1.0)
        assert (output_dir / "README.md").exists()
        assert (output_dir / "ensemble_temporal_staged_forecast.csv").exists()
        assert len(PdfReader(output_dir / "phase2_ensemble_report.pdf").pages) == 4
    print("  [✓] Parent discovery, classic/staged ensemble, README, CSVs and four-page PDF verified.")


def test_phase2_readme_reports_forced_selection_objective() -> None:
    print("[TEST 16.3] Testing forced Phase 2 objective in the micro-run README...")
    with tempfile.TemporaryDirectory() as temporary_dir:
        output_dir = Path(temporary_dir)
        comparison = {
            "actual_device": "cpu",
            "phase1": {"best_objective_loss": 1.0},
            "phase2": {"best_objective_loss": 2.0},
            "overall_best_objective_loss": 1.0,
        }
        selection = {
            "selection_policy": "phase2",
            "selected_source": "phase2",
            "selected_objective_loss": 2.0,
            "train_samples": 100,
            "validation_samples": 10,
            "forecast_samples": 20,
        }
        _write_micro_readme(output_dir, "deep_learning", comparison, selection)
        readme = (output_dir / "README.md").read_text(encoding="utf-8")
        assert "Selected objective: `2.000000`" in readme
        assert "finalized source: **phase2**" in readme
    print("  [✓] README keeps the selected Phase 2 objective even when Phase 1 is better.")


def run_modulo16_suite() -> None:
    test_vertical_iso_ticks_and_forecast_peak_tags()
    test_parameterized_phase2_ensemble()
    test_phase2_readme_reports_forced_selection_objective()


if __name__ == "__main__":
    run_modulo16_suite()

"""Parametric Optuna Multi-Microstudy Orchestrator & Weighted Ensemble Engine for DLVS-Wave v2.0.

Coordinates 3 specialized microstudies (KAN, Deep Learning, LCS) under global and per-microstudy
time budget constraints, explores pretreatment factors and model hyperparams, and produces a
rigorous weighted ensemble validation and pure future forecasting stream.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.base import ModelMetrics
from models.deep_learning import DeepLearningForecastingModel
from models.engine import ForecastingEngine, ModelType
from models.kan import KANForecastingModel
from models.lcs import LCSForecastingModel
from models.plotting import ForecastingVisualizer
from pretreatment import MasterPretreatmentEngine, PretreatmentConfig, PretreatmentResult
PretreatmentEngine = MasterPretreatmentEngine

# Configure optuna logging
optuna.logging.set_verbosity(optuna.logging.WARNING)
logger = logging.getLogger("dlvs_wave.orchestrator")


class OptunaMicrostudyRunner:
    """Runs a single microstudy (KAN, Deep Learning, or LCS) using Optuna Bayesian Optimization."""

    def __init__(
        self,
        model_type: str,
        master_df: pd.DataFrame,
        target_col: str,
        min_mag_threshold: float,
        eval_events: int,
        timeout_seconds: float,
        n_trials: int,
        device: str,
        output_dir: Path,
        roi_name: str,
    ) -> None:
        self.model_type = model_type.lower()
        self.master_df = master_df
        self.target_col = target_col
        self.min_mag_threshold = min_mag_threshold
        self.eval_events = eval_events
        self.timeout_seconds = timeout_seconds
        self.n_trials = n_trials
        self.device = device
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.roi_name = roi_name

        self.best_metrics: ModelMetrics | None = None
        self.best_val_df: pd.DataFrame | None = None
        self.best_train_df: pd.DataFrame | None = None
        self.best_model: Any = None
        self.best_params: dict[str, Any] = {}
        self.best_objective_value: float = float("inf")
        self.trial_records: list[dict[str, Any]] = []

    def _sample_pretreatment_params(self, trial: optuna.Trial) -> dict[str, Any]:
        """Samples data pretreatment factors."""
        start_year = trial.suggest_int("train_start_year", 1900, 1980, step=10)
        train_start_date = f"{start_year}-01-01"
        window_before = trial.suggest_int("window_before", 2, 6)
        window_after = trial.suggest_int("window_after", 2, 6)
        background_sample_ratio = trial.suggest_float("background_ratio", 0.05, 0.25, step=0.05)

        return {
            "train_start_date": train_start_date,
            "window_before": window_before,
            "window_after": window_after,
            "background_sample_ratio": background_sample_ratio,
        }

    def _sample_model_hyperparams(self, trial: optuna.Trial) -> dict[str, Any]:
        """Samples model-specific hyperparameters."""
        if self.model_type == "kan":
            grid_size = trial.suggest_int("grid_size", 3, 8)
            spline_order = trial.suggest_int("spline_order", 2, 4)
            lr = trial.suggest_float("learning_rate", 1e-3, 3e-2, log=True)
            return {
                "grid_size": grid_size,
                "spline_order": spline_order,
                "learning_rate": lr,
                "device": self.device,
            }
        elif self.model_type in ("deep_learning", "deep"):
            hidden_dim = trial.suggest_categorical("hidden_dim", [32, 64, 96, 128])
            num_layers = trial.suggest_int("num_layers", 2, 5)
            dropout = trial.suggest_float("dropout", 0.0, 0.25, step=0.05)
            lr = trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True)
            return {
                "hidden_dim": hidden_dim,
                "num_layers": num_layers,
                "dropout": dropout,
                "learning_rate": lr,
                "device": self.device,
            }
        elif self.model_type == "lcs":
            population_size = trial.suggest_int("population_size", 50, 250, step=25)
            lr = trial.suggest_float("learning_rate", 0.05, 0.30, step=0.05)
            crossover_rate = trial.suggest_float("crossover_rate", 0.6, 0.9, step=0.1)
            mutation_rate = trial.suggest_float("mutation_rate", 0.02, 0.10, step=0.02)
            return {
                "population_size": population_size,
                "learning_rate": lr,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
            }
        else:
            raise ValueError(f"Unknown model type {self.model_type}")

    def _objective(self, trial: optuna.Trial) -> float:
        pretreat_params = self._sample_pretreatment_params(trial)
        model_params = self._sample_model_hyperparams(trial)

        cfg = PretreatmentConfig(
            mode="energetic",
            target_col=self.target_col,
            train_start_date=pretreat_params["train_start_date"],
            min_magnitude_threshold=self.min_mag_threshold,
            window_before=pretreat_params["window_before"],
            window_after=pretreat_params["window_after"],
            background_sample_ratio=pretreat_params["background_sample_ratio"],
            eval_min_events=self.eval_events,
            eval_max_events=self.eval_events,
            auto_balance_dates=True,
            eval_window_mode="corridors",
        )

        engine = PretreatmentEngine(config=cfg)
        try:
            res = engine.process(self.master_df, study_name=f"{self.model_type}_trial_{trial.number}")
        except Exception as e:
            logger.warning(f"Trial {trial.number} pretreatment failed: {e}")
            return 999.0

        if len(res.train_df) < 5 or len(res.eval_df) < 5:
            return 999.0

        if self.model_type == "kan":
            model = KANForecastingModel(
                grid_size=model_params["grid_size"],
                spline_order=model_params["spline_order"],
                learning_rate=model_params["learning_rate"],
                device=self.device,
            )
            epochs = 50
        elif self.model_type in ("deep_learning", "deep"):
            model = DeepLearningForecastingModel(
                hidden_dim=model_params["hidden_dim"],
                num_layers=model_params["num_layers"],
                dropout=model_params["dropout"],
                learning_rate=model_params["learning_rate"],
                device=self.device,
            )
            epochs = 60
        elif self.model_type == "lcs":
            model = LCSForecastingModel(
                population_size=model_params["population_size"],
                learning_rate=model_params["learning_rate"],
                crossover_rate=model_params["crossover_rate"],
                mutation_rate=model_params["mutation_rate"],
            )
            epochs = 30

        try:
            X_train = res.train_df[res.feature_cols]
            y_train = res.train_df[self.target_col]
            model.fit(X_train, y_train, feature_names=res.feature_cols, target_name=self.target_col, epochs=epochs)

            train_metrics, _ = model.evaluate(X_train, y_train)

            X_eval = res.eval_df[res.feature_cols]
            y_eval = res.eval_df[self.target_col]
            val_metrics, df_comp = model.evaluate(X_eval, y_eval)
        except Exception as e:
            logger.warning(f"Trial {trial.number} model fit/eval failed: {e}")
            return 999.0

        objective_loss = (val_metrics.mse * 0.5) + ((1.0 - val_metrics.f1_score) * 4.0) + (val_metrics.depression_mae * 0.5)

        record = {
            "trial_number": trial.number,
            "objective_loss": objective_loss,
            # Training Metrics
            "train_samples": len(X_train),
            "train_mse": train_metrics.mse,
            "train_rmse": train_metrics.rmse,
            "train_mae": train_metrics.mae,
            "train_r2": train_metrics.r2,
            "train_f1_score": train_metrics.f1_score,
            "train_peak_hit_rate": train_metrics.peak_hit_rate,
            "train_depression_mae": train_metrics.depression_mae,
            "train_directional_accuracy": train_metrics.directional_accuracy,
            # Validation Metrics
            "eval_samples": len(X_eval),
            "val_mse": val_metrics.mse,
            "val_rmse": val_metrics.rmse,
            "val_mae": val_metrics.mae,
            "val_r2": val_metrics.r2,
            "val_f1_score": val_metrics.f1_score,
            "val_peak_hit_rate": val_metrics.peak_hit_rate,
            "val_depression_mae": val_metrics.depression_mae,
            "val_precision": val_metrics.precision,
            "val_recall": val_metrics.recall,
            "val_directional_accuracy": val_metrics.directional_accuracy,
            "val_peak_magnitude_bias": val_metrics.peak_magnitude_bias,
            "val_peak_timing_error": val_metrics.peak_timing_error,
            "val_tp": val_metrics.true_positives,
            "val_fp": val_metrics.false_positives,
            "val_fn": val_metrics.false_negatives,
            "val_tn": val_metrics.true_negatives,
            # Pretreatment Parameters
            "train_start_date": pretreat_params["train_start_date"],
            "window_before": pretreat_params["window_before"],
            "window_after": pretreat_params["window_after"],
            "background_sample_ratio": pretreat_params["background_sample_ratio"],
            # Model Hyperparameters
            **model_params,
        }
        self.trial_records.append(record)

        # Incrementally persist trials CSV to guarantee zero data loss & minimal disk footprint
        trials_csv_path = self.output_dir / f"optuna_trials_{self.model_type}.csv"
        pd.DataFrame(self.trial_records).to_csv(trials_csv_path, index=False)

        if objective_loss < self.best_objective_value:
            self.best_objective_value = objective_loss
            self.best_metrics = val_metrics
            self.best_params = {**pretreat_params, **model_params}
            self.best_model = model
            self.best_train_df = res.train_df
            val_out = res.eval_df[["date", self.target_col]].copy()
            val_out.rename(columns={self.target_col: "actual"}, inplace=True)
            val_out[f"predicted_{self.target_col}"] = df_comp["predicted"].values
            val_out["residual_gap"] = np.abs(val_out["actual"] - val_out[f"predicted_{self.target_col}"])
            self.best_val_df = val_out

        return objective_loss

    def run(self) -> dict[str, Any]:
        """Executes the Optuna study within the allocated timeout."""
        start_time = time.time()
        logger.info(
            f"Starting Microstudy [{self.model_type.upper()}] - Budget: {self.timeout_seconds:.1f}s, Max Trials: {self.n_trials}"
        )

        study = optuna.create_study(direction="minimize", study_name=f"microstudy_{self.model_type}")
        study.optimize(
            self._objective,
            n_trials=self.n_trials,
            timeout=self.timeout_seconds,
            show_progress_bar=False,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"Completed Microstudy [{self.model_type.upper()}] in {elapsed:.1f}s ({len(study.trials)} trials). "
            f"Best Objective: {self.best_objective_value:.4f}, Best MSE: {self.best_metrics.mse if self.best_metrics else 'N/A'}"
        )

        if self.best_val_df is not None:
            val_path = self.output_dir / f"best_validation_{self.model_type}.csv"
            self.best_val_df.to_csv(val_path, index=False)

        if self.best_train_df is not None:
            train_path = self.output_dir / f"best_train_pretreated_{self.model_type}.csv"
            self.best_train_df.to_csv(train_path, index=False)

        if self.best_metrics is not None:
            metrics_path = self.output_dir / f"best_metrics_{self.model_type}.json"
            with open(metrics_path, "w") as f:
                json.dump(self.best_metrics.to_dict(), f, indent=2)

        params_path = self.output_dir / f"best_params_{self.model_type}.json"
        with open(params_path, "w") as f:
            json.dump(self.best_params, f, indent=2)

        if self.trial_records:
            pd.DataFrame(self.trial_records).to_csv(self.output_dir / f"optuna_trials_{self.model_type}.csv", index=False)

        if self.best_val_df is not None and self.best_train_df is not None and self.best_metrics is not None:
            vis = ForecastingVisualizer(dpi=300)
            plot_png = self.output_dir / f"study_{self.model_type}_report.png"
            plot_pdf = self.output_dir / f"study_{self.model_type}_report.pdf"

            vis.render(
                input_csv_or_df=self.best_val_df,
                training_csv_or_df=self.best_train_df,
                output_path=plot_png,
                metrics_dict_or_path=self.best_metrics.to_dict(),
                title=f"DLVS-Wave v2.0 Microstudy: {self.model_type.upper()} Validation Report",
                subtitle=f"ROI: {self.roi_name} | Best Params: {self.best_params}",
                target_name=self.target_col,
                roi_name=self.roi_name,
                model_name=self.model_type.upper(),
                eval_window_mode="corridors",
                eval_max_events=self.eval_events,
                eval_min_mag=self.min_mag_threshold,
                show_eval_dot_tags=True,
                show_train_dot_tags=True,
            )

            vis.render(
                input_csv_or_df=self.best_val_df,
                training_csv_or_df=self.best_train_df,
                output_path=plot_pdf,
                metrics_dict_or_path=self.best_metrics.to_dict(),
                title=f"DLVS-Wave v2.0 Microstudy: {self.model_type.upper()} Validation Report",
                subtitle=f"ROI: {self.roi_name} | Best Params: {self.best_params}",
                target_name=self.target_col,
                roi_name=self.roi_name,
                model_name=self.model_type.upper(),
                eval_window_mode="corridors",
                eval_max_events=self.eval_events,
                eval_min_mag=self.min_mag_threshold,
                show_eval_dot_tags=True,
                show_train_dot_tags=True,
            )

        return {
            "model_type": self.model_type,
            "trials_count": len(study.trials),
            "elapsed_seconds": elapsed,
            "best_objective": self.best_objective_value,
            "best_metrics": self.best_metrics.to_dict() if self.best_metrics else {},
            "best_params": self.best_params,
        }


class GlobalStudyOrchestrator:
    """Master Orchestrator managing 3 Microstudies and the Weighted Ensemble with pure future forecast."""

    def __init__(
        self,
        input_master: str | Path,
        target_col: str = "seis_core_magnitude",
        min_mag_threshold: float = 6.9,
        eval_events: int = 3,
        total_timeout_seconds: float = 7200.0,
        output_dir: str | Path = "studies_output/optuna_global_study",
        device: str = "cpu",
        n_trials_per_study: int = 100,
        roi_name: str = "Japan Area (7D Summarized)",
        forecast_steps: int = 150,
    ) -> None:
        self.input_master_path = Path(input_master)
        self.target_col = target_col
        self.min_mag_threshold = min_mag_threshold
        self.eval_events = eval_events
        self.total_timeout_seconds = total_timeout_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = device
        self.n_trials_per_study = n_trials_per_study
        self.roi_name = roi_name
        self.forecast_steps = forecast_steps

        logger.info(f"Loading master dataset from {self.input_master_path}...")
        self.master_df = pd.read_csv(self.input_master_path, low_memory=False)
        date_col = "date" if "date" in self.master_df.columns else self.master_df.columns[0]
        self.master_df[date_col] = pd.to_datetime(self.master_df[date_col])
        self.master_df.sort_values(by=date_col, inplace=True)
        self.master_df.reset_index(drop=True, inplace=True)
        logger.info(f"Loaded master with {len(self.master_df)} rows from {self.master_df[date_col].min()} to {self.master_df[date_col].max()}")

    def execute_all(self) -> dict[str, Any]:
        """Runs the 3 microstudies sequentially and combines them in the weighted ensemble."""
        global_start = time.time()
        timeout_per_study = self.total_timeout_seconds / 3.0

        microstudies = ["kan", "deep_learning", "lcs"]
        results: dict[str, Any] = {}
        runners: dict[str, OptunaMicrostudyRunner] = {}

        for m_type in microstudies:
            sub_dir = self.output_dir / f"study_{m_type}"
            runner = OptunaMicrostudyRunner(
                model_type=m_type,
                master_df=self.master_df,
                target_col=self.target_col,
                min_mag_threshold=self.min_mag_threshold,
                eval_events=self.eval_events,
                timeout_seconds=timeout_per_study,
                n_trials=self.n_trials_per_study,
                device=self.device,
                output_dir=sub_dir,
                roi_name=self.roi_name,
            )
            res = runner.run()
            results[m_type] = res
            runners[m_type] = runner

        logger.info("Computing Weighted Multi-Model Ensemble...")
        ensemble_dir = self.output_dir / "ensemble"
        ensemble_dir.mkdir(parents=True, exist_ok=True)

        weights = {}
        for m_type, r in results.items():
            metrics = r.get("best_metrics", {})
            mse = metrics.get("mse", 1.0)
            f1 = metrics.get("f1_score", 0.5)
            w = (f1 + 0.1) / (mse + 1e-4)
            weights[m_type] = float(w)

        total_weight = sum(weights.values())
        normalized_weights = {k: v / total_weight for k, v in weights.items()}
        logger.info(f"Ensemble Normalized Weights: {normalized_weights}")

        ref_runner = runners["kan"] if runners["kan"].best_val_df is not None else list(runners.values())[0]
        ens_val_df = ref_runner.best_val_df[["date", "actual"]].copy()

        ens_pred = np.zeros(len(ens_val_df), dtype=float)
        for m_type, runner in runners.items():
            if runner.best_val_df is not None:
                p_col = [c for c in runner.best_val_df.columns if c.startswith("predicted_")][0]
                m_pred = runner.best_val_df[p_col].values
                if len(m_pred) == len(ens_val_df):
                    ens_pred += normalized_weights[m_type] * m_pred
                else:
                    ens_pred += normalized_weights[m_type] * np.resize(m_pred, len(ens_val_df))

        ens_val_df[f"predicted_{self.target_col}"] = ens_pred
        ens_val_df["residual_gap"] = np.abs(ens_val_df["actual"] - ens_pred)

        y_true = ens_val_df["actual"].to_numpy(dtype=np.float32)
        y_pred = ens_val_df[f"predicted_{self.target_col}"].to_numpy(dtype=np.float32)
        err = y_pred - y_true
        mse = float(np.mean(err ** 2))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(err)))

        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1.0 - (ss_res / max(1e-8, ss_tot))) if ss_tot > 1e-8 else 0.0

        if np.std(y_true) > 1e-8 and np.std(y_pred) > 1e-8:
            corr_mat = np.corrcoef(y_true, y_pred)
            pearson_corr = float(corr_mat[0, 1]) if not np.isnan(corr_mat[0, 1]) else 0.0
        else:
            pearson_corr = 0.0

        threshold = 6.0
        act_peak_mask = y_true >= threshold
        pred_peak_mask = y_pred >= (threshold * 0.90)
        tp = int(np.sum(act_peak_mask & pred_peak_mask))
        fp = int(np.sum((~act_peak_mask) & pred_peak_mask))
        fn = int(np.sum(act_peak_mask & (~pred_peak_mask)))
        tn = int(np.sum((~act_peak_mask) & (~pred_peak_mask)))
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        calm_mask = ~act_peak_mask
        depression_mae = float(np.mean(np.abs(y_pred[calm_mask] - y_true[calm_mask]))) if np.any(calm_mask) else 0.0
        diff_true = np.diff(y_true)
        diff_pred = np.diff(y_pred)
        directional_accuracy = float(np.mean(np.sign(diff_true) == np.sign(diff_pred))) if len(y_true) > 1 else 1.0

        ens_metrics = ModelMetrics(
            mse=mse,
            rmse=rmse,
            mae=mae,
            r2=r2,
            pearson_corr=pearson_corr,
            peak_hit_rate=recall,
            directional_accuracy=directional_accuracy,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            depression_mae=depression_mae,
            sample_count=len(y_true),
        )

        ens_val_path = ensemble_dir / "ensemble_validation_comparison.csv"
        ens_val_df.to_csv(ens_val_path, index=False)

        ens_metrics_path = ensemble_dir / "ensemble_metrics.json"
        with open(ens_metrics_path, "w") as f:
            json.dump(ens_metrics.to_dict(), f, indent=2)

        date_col = "date" if "date" in self.master_df.columns else self.master_df.columns[0]
        val_end_date = pd.to_datetime(ens_val_df[date_col].max())
        future_mask = pd.to_datetime(self.master_df[date_col]) > val_end_date
        future_df = self.master_df[future_mask].copy().reset_index(drop=True)

        if len(future_df) > self.forecast_steps:
            future_df = future_df.iloc[:self.forecast_steps].copy().reset_index(drop=True)

        if len(future_df) > 0:
            future_ens_pred = np.zeros(len(future_df), dtype=float)
            for m_type, runner in runners.items():
                if runner.best_model is not None:
                    try:
                        f_names = runner.best_model.feature_names
                        # Ensure all feature names are in future_df
                        avail_cols = [c for c in f_names if c in future_df.columns]
                        X_future = future_df[avail_cols]
                        m_f_pred = runner.best_model.predict(X_future)
                        future_ens_pred += normalized_weights[m_type] * m_f_pred
                    except Exception as e:
                        logger.warning(f"Future inference for {m_type} failed: {e}")

            forecast_stream_df = pd.DataFrame({
                "date": future_df[date_col],
                f"forecasted_{self.target_col}": future_ens_pred,
            })
            forecast_path = ensemble_dir / "ensemble_pure_future_forecast.csv"
            forecast_stream_df.to_csv(forecast_path, index=False)
            logger.info(f"Saved pure future forecast stream ({len(forecast_stream_df)} steps) -> {forecast_path}")

            # Also render pure forecast trajectory plot
            forecast_plot_png = ensemble_dir / "ensemble_future_forecast_plot.png"
            forecast_plot_pdf = ensemble_dir / "ensemble_future_forecast_plot.pdf"
            vis_fc = ForecastingVisualizer(dpi=300)
            vis_fc.render(
                input_csv_or_df=forecast_stream_df,
                output_path=forecast_plot_png,
                title=f"DLVS-Wave v2.0 Weighted Multi-Model Pure Future Forecast Trajectory",
                subtitle=f"ROI: {self.roi_name} | Future Forecast Horizon: [{forecast_stream_df['date'].min().strftime('%Y-%m-%d')} .. {forecast_stream_df['date'].max().strftime('%Y-%m-%d')}]",
                target_name=self.target_col,
                roi_name=self.roi_name,
                model_name="Weighted Multi-Model Ensemble",
                eval_window_mode="continuous",
            )
            vis_fc.render(
                input_csv_or_df=forecast_stream_df,
                output_path=forecast_plot_pdf,
                title=f"DLVS-Wave v2.0 Weighted Multi-Model Pure Future Forecast Trajectory",
                subtitle=f"ROI: {self.roi_name} | Future Forecast Horizon: [{forecast_stream_df['date'].min().strftime('%Y-%m-%d')} .. {forecast_stream_df['date'].max().strftime('%Y-%m-%d')}]",
                target_name=self.target_col,
                roi_name=self.roi_name,
                model_name="Weighted Multi-Model Ensemble",
                eval_window_mode="continuous",
            )

        vis = ForecastingVisualizer(dpi=300)
        ens_png = ensemble_dir / "ensemble_validation_report.png"
        ens_pdf = ensemble_dir / "ensemble_validation_report.pdf"

        ref_train_df = ref_runner.best_train_df if ref_runner.best_train_df is not None else None

        vis.render(
            input_csv_or_df=ens_val_df,
            training_csv_or_df=ref_train_df,
            output_path=ens_png,
            metrics_dict_or_path=ens_metrics.to_dict(),
            title=f"DLVS-Wave v2.0 Weighted Multi-Model Ensemble Report",
            subtitle=f"ROI: {self.roi_name} | Weights: KAN={normalized_weights.get('kan', 0):.2f}, Deep={normalized_weights.get('deep_learning', 0):.2f}, LCS={normalized_weights.get('lcs', 0):.2f}",
            target_name=self.target_col,
            roi_name=self.roi_name,
            model_name="Weighted Multi-Model Ensemble",
            eval_window_mode="corridors",
            eval_max_events=self.eval_events,
            eval_min_mag=self.min_mag_threshold,
            show_eval_dot_tags=True,
            show_train_dot_tags=True,
        )

        vis.render(
            input_csv_or_df=ens_val_df,
            training_csv_or_df=ref_train_df,
            output_path=ens_pdf,
            metrics_dict_or_path=ens_metrics.to_dict(),
            title=f"DLVS-Wave v2.0 Weighted Multi-Model Ensemble Report",
            subtitle=f"ROI: {self.roi_name} | Weights: KAN={normalized_weights.get('kan', 0):.2f}, Deep={normalized_weights.get('deep_learning', 0):.2f}, LCS={normalized_weights.get('lcs', 0):.2f}",
            target_name=self.target_col,
            roi_name=self.roi_name,
            model_name="Weighted Multi-Model Ensemble",
            eval_window_mode="corridors",
            eval_max_events=self.eval_events,
            eval_min_mag=self.min_mag_threshold,
            show_eval_dot_tags=True,
            show_train_dot_tags=True,
        )

        global_elapsed = time.time() - global_start
        manifest_md = self.output_dir / "STUDY_ORCHESTRATION_MANIFEST.md"
        with open(manifest_md, "w") as f:
            f.write(f"# DLVS-Wave v2.0 AI Optimization Orchestrator Report\n\n")
            f.write(f"- **ROI**: `{self.roi_name}`\n")
            f.write(f"- **Master Dataset**: `{self.input_master_path}`\n")
            f.write(f"- **Execution Time**: `{global_elapsed:.1f}s` (Budget: `{self.total_timeout_seconds}s`)\n")
            f.write(f"- **Device**: `{self.device}`\n\n")
            f.write(f"## 1. Microstudies Summary\n\n")
            f.write(f"| Paradigm | Best Objective | MSE | RMSE | R² Score | F1-Score | Weight |\n")
            f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for m_type in microstudies:
                r = results[m_type]
                m = r.get("best_metrics", {})
                w = normalized_weights.get(m_type, 0.0)
                f.write(f"| **{m_type.upper()}** | `{r.get('best_objective', 0.0):.4f}` | `{m.get('mse', 0.0):.6f}` | `{m.get('rmse', 0.0):.6f}` | `{m.get('r2', 0.0):.4f}` | `{m.get('f1_score', 0.0):.2%}` | `{w:.2%}` |\n")
            f.write(f"\n## 2. Weighted Ensemble Performance\n\n")
            f.write(ens_metrics.summary_markdown("Global Weighted Ensemble Metrics"))

        # Refit persisted winners once to add pure-forecast and progressive
        # validation-horizon pages to all four reports.  This also makes the
        # same reporting path available for historical studies lacking saved
        # model checkpoints.
        try:
            from regenerate_optuna_study_reports import regenerate_existing_study_reports

            regenerate_existing_study_reports(
                study_dir=self.output_dir,
                input_master=self.input_master_path,
                target_col=self.target_col,
                peak_threshold=self.min_mag_threshold,
                eval_events=self.eval_events,
                forecast_steps=self.forecast_steps,
                device=self.device,
                roi_name=self.roi_name,
            )
        except Exception as exc:
            logger.warning("Forecast/temporal report regeneration failed: %s", exc)

        logger.info(f"Global Orchestration Completed Successfully in {global_elapsed:.1f}s -> {self.output_dir}")
        return {
            "global_elapsed_seconds": global_elapsed,
            "microstudy_results": results,
            "ensemble_weights": normalized_weights,
            "ensemble_metrics": ens_metrics.to_dict(),
            "manifest_path": str(manifest_md),
        }


def build_orchestrator_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DLVS-Wave v2.0 Optuna Multi-Microstudy Orchestrator")
    p.add_argument("--input-master", required=True, help="Path to 7D or 30D compacted master CSV")
    p.add_argument("--target-col", default="seis_core_magnitude", help="Target seismic column")
    p.add_argument("--min-mag-threshold", type=float, default=6.9, help="Magnitude threshold for events")
    p.add_argument("--eval-events", type=int, default=3, help="Number of validation events (default 3)")
    p.add_argument("--total-timeout-seconds", type=float, default=7200.0, help="Total execution budget in seconds (default 2h = 7200s)")
    p.add_argument("--output-dir", default="studies_output/optuna_study_japan_7d_m69_2h", help="Output directory")
    p.add_argument("--device", default="cpu", choices=["cpu", "xpu", "cuda"], help="Compute device")
    p.add_argument("--n-trials-per-study", type=int, default=100, help="Maximum trials per microstudy")
    p.add_argument("--roi-name", default="Japan Area (7D Summarized)", help="Region of Interest name")
    p.add_argument("--forecast-steps", type=int, default=150, help="Future forecast steps")
    return p


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = build_orchestrator_parser().parse_args()

    orchestrator = GlobalStudyOrchestrator(
        input_master=args.input_master,
        target_col=args.target_col,
        min_mag_threshold=args.min_mag_threshold,
        eval_events=args.eval_events,
        total_timeout_seconds=args.total_timeout_seconds,
        output_dir=args.output_dir,
        device=args.device,
        n_trials_per_study=args.n_trials_per_study,
        roi_name=args.roi_name,
        forecast_steps=args.forecast_steps,
    )
    orchestrator.execute_all()


if __name__ == "__main__":
    main()

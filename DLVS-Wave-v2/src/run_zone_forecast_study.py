#!/usr/bin/env python3
"""CPU-only Optuna study for conditional Japanese seismic-zone localization.

This module intentionally models *where* an already assumed M6.9+ event would
fall.  It does not model whether an earthquake will occur.  Three regression
families (KAN, deep learning and LCS) predict the ordinal south-to-north zone
index and are selected with location-specific validation metrics.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import torch
from sklearn.metrics import balanced_accuracy_score, f1_score

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cluster_seismic_zones import plot_zone_map
from models.deep_learning import DeepLearningForecastingModel
from models.kan import KANForecastingModel
from models.lcs import LCSForecastingModel


LOGGER = logging.getLogger("dlvs_wave.zone_study")
MODEL_TYPES = ("kan", "deep_learning", "lcs")
TARGET = "seis_core_zone"
METADATA_COLUMNS = {
    "date",
    TARGET,
    "event_magnitude",
    "event_latitude",
    "event_longitude",
    "event_id",
    "split_role",
    "is_forecast",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Two-hour CPU-only KAN/Deep/LCS conditional zone study",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-master", required=True)
    parser.add_argument("--cluster-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--total-timeout-seconds", type=float, default=7200.0)
    parser.add_argument("--n-trials-per-study", type=int, default=10000)
    parser.add_argument("--recent-validation-weight", type=float, default=3.0)
    parser.add_argument("--target-date", default="2026-08-24")
    parser.add_argument("--seed", type=int, default=842024)
    parser.add_argument("--device", choices=["cpu"], default="cpu")
    parser.add_argument("--smoke-epochs", type=int, default=None)
    return parser


def _atomic_json(payload: Any, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_args(args: argparse.Namespace) -> None:
    if args.device != "cpu":
        raise ValueError("The location study is intentionally CPU-only")
    if args.total_timeout_seconds <= 0 or args.total_timeout_seconds > 7200:
        raise ValueError("--total-timeout-seconds must be in (0, 7200]")
    if args.n_trials_per_study < 1:
        raise ValueError("--n-trials-per-study must be positive")
    if args.recent_validation_weight < 1.0:
        raise ValueError("--recent-validation-weight must be >= 1")


def haversine_km(
    latitude_a: np.ndarray,
    longitude_a: np.ndarray,
    latitude_b: np.ndarray,
    longitude_b: np.ndarray,
) -> np.ndarray:
    lat_a = np.deg2rad(np.asarray(latitude_a, dtype=float))
    lon_a = np.deg2rad(np.asarray(longitude_a, dtype=float))
    lat_b = np.deg2rad(np.asarray(latitude_b, dtype=float))
    lon_b = np.deg2rad(np.asarray(longitude_b, dtype=float))
    d_lat = lat_b - lat_a
    d_lon = lon_b - lon_a
    value = np.sin(d_lat / 2.0) ** 2 + np.cos(lat_a) * np.cos(lat_b) * np.sin(d_lon / 2.0) ** 2
    return 6371.0088 * 2.0 * np.arcsin(np.sqrt(np.clip(value, 0.0, 1.0)))


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(np.asarray(values, float) * weights) / np.maximum(weights.sum(), 1e-12))


def evaluate_zones(
    actual: np.ndarray,
    predicted_continuous: np.ndarray,
    definitions: pd.DataFrame,
    latitude: np.ndarray | None = None,
    longitude: np.ndarray | None = None,
    recent_weight: float = 1.0,
) -> dict[str, Any]:
    actual = np.asarray(actual, dtype=int).ravel()
    predicted_continuous = np.asarray(predicted_continuous, dtype=float).ravel()
    zone_count = len(definitions)
    predicted_zone = np.clip(np.rint(predicted_continuous), 1, zone_count).astype(int)
    weights = np.exp(np.linspace(0.0, math.log(max(1.0, recent_weight)), len(actual)))
    weights /= weights.mean()
    error = np.abs(predicted_continuous - actual)
    rounded_error = np.abs(predicted_zone - actual)
    exact = predicted_zone == actual
    adjacent = rounded_error <= 1
    result: dict[str, Any] = {
        "sample_count": len(actual),
        "mae_zone_continuous": float(np.mean(error)),
        "rmse_zone_continuous": float(np.sqrt(np.mean((predicted_continuous - actual) ** 2))),
        "recent_weighted_mae_zone": _weighted_mean(error, weights),
        "exact_zone_accuracy": float(np.mean(exact)),
        "recent_weighted_exact_accuracy": _weighted_mean(exact.astype(float), weights),
        "adjacent_zone_accuracy": float(np.mean(adjacent)),
        "recent_weighted_adjacent_accuracy": _weighted_mean(adjacent.astype(float), weights),
        "macro_f1": float(f1_score(actual, predicted_zone, labels=range(1, zone_count + 1), average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted_zone)),
        "actual_zone": actual.tolist(),
        "predicted_zone": predicted_zone.tolist(),
        "predicted_continuous": predicted_continuous.tolist(),
    }
    if latitude is not None and longitude is not None:
        centers = definitions.set_index("zone")
        predicted_latitude = np.asarray([centers.loc[zone, "center_latitude"] for zone in predicted_zone], float)
        predicted_longitude = np.asarray([centers.loc[zone, "center_longitude"] for zone in predicted_zone], float)
        distance = haversine_km(latitude, longitude, predicted_latitude, predicted_longitude)
        result["mean_centroid_distance_km"] = float(np.mean(distance))
        result["recent_weighted_centroid_distance_km"] = _weighted_mean(distance, weights)
        result["centroid_distances_km"] = distance.tolist()
    else:
        result["mean_centroid_distance_km"] = None
        result["recent_weighted_centroid_distance_km"] = None
    return result


def selection_objective(
    train_metrics: dict[str, Any],
    validation_metrics: dict[str, Any],
    zone_count: int,
) -> float:
    scale = max(1.0, float(zone_count - 1))
    distance_term = min(1.0, float(validation_metrics["recent_weighted_centroid_distance_km"] or 1500.0) / 1500.0)
    return float(
        0.30 * validation_metrics["recent_weighted_mae_zone"] / scale
        + 0.20 * (1.0 - validation_metrics["recent_weighted_exact_accuracy"])
        + 0.15 * (1.0 - validation_metrics["recent_weighted_adjacent_accuracy"])
        + 0.15 * (1.0 - validation_metrics["macro_f1"])
        + 0.10 * train_metrics["mae_zone_continuous"] / scale
        + 0.10 * distance_term
    )


def _model_and_epochs(model_type: str, params: dict[str, Any], epochs_override: int | None = None):
    if model_type == "kan":
        model = KANForecastingModel(
            grid_size=int(params["grid_size"]),
            spline_order=int(params["spline_order"]),
            learning_rate=float(params["learning_rate"]),
            device="cpu",
        )
        epochs = 50
    elif model_type == "deep_learning":
        model = DeepLearningForecastingModel(
            hidden_dim=int(params["hidden_dim"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
            learning_rate=float(params["learning_rate"]),
            device="cpu",
        )
        epochs = 60
    elif model_type == "lcs":
        model = LCSForecastingModel(
            population_size=int(params["population_size"]),
            learning_rate=float(params["learning_rate"]),
            crossover_rate=float(params["crossover_rate"]),
            mutation_rate=float(params["mutation_rate"]),
        )
        epochs = 30
    else:
        raise ValueError(model_type)
    return model, int(epochs_override or epochs)


def _plot_zone_series(
    frame: pd.DataFrame,
    definitions: pd.DataFrame,
    output_path: Path,
    prediction_column: str,
    title: str,
    target_date: str | None = None,
    actual_column: str | None = None,
) -> None:
    value = frame.copy()
    value["date"] = pd.to_datetime(value["date"])
    zone_count = len(definitions)
    figure, axis = plt.subplots(figsize=(13.6, 6.8), constrained_layout=True)
    if actual_column and actual_column in value:
        axis.step(value["date"], value[actual_column], where="mid", color="#1565c0", linewidth=1.7, marker="o", label="actual zone")
    axis.plot(value["date"], value[prediction_column], color="#d32f2f", linewidth=2.0, marker="o", markersize=4, label="continuous prediction")
    rounded = np.clip(np.rint(value[prediction_column]), 1, zone_count)
    axis.step(value["date"], rounded, where="mid", color="#2e7d32", linewidth=1.3, linestyle="--", label="rounded zone")
    if target_date:
        target = pd.Timestamp(target_date)
        axis.axvline(target, color="#6a1b9a", linewidth=1.7, linestyle=":", label=f"target week {target.date()}")
        exact = value.loc[value["date"].eq(target)]
        if len(exact):
            row = exact.iloc[0]
            axis.annotate(
                f"{target.date()}\n{row[prediction_column]:.2f} → Z{int(np.clip(np.rint(row[prediction_column]), 1, zone_count))}",
                xy=(target, row[prediction_column]), xytext=(0, 38), textcoords="offset points",
                ha="center", va="bottom", rotation=90,
                arrowprops={"arrowstyle": "-|>", "color": "#6a1b9a", "lw": 1.0},
                bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "alpha": 0.9, "edgecolor": "#6a1b9a"},
            )
    labels = [f"Z{int(row.zone)} ({row.center_latitude:.1f}°N)" for row in definitions.itertuples()]
    axis.set_yticks(range(1, zone_count + 1), labels)
    axis.set_ylim(0.5, zone_count + 0.8)
    axis.set_xlabel("Week / historical event date")
    axis.set_ylabel("Zone index (south → north)")
    axis.set_title(title, fontweight="bold")
    axis.grid(True, alpha=0.25)
    axis.tick_params(axis="x", rotation=90)
    axis.legend(loc="upper left", ncol=2, framealpha=0.92)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(figure)


@dataclass
class Winner:
    model_type: str
    model: Any
    params: dict[str, Any]
    feature_names: list[str]
    objective: float
    train_metrics: dict[str, Any]
    validation_metrics: dict[str, Any]
    validation: pd.DataFrame
    forecast: pd.DataFrame
    elapsed_seconds: float
    successful_trials: int
    attempted_trials: int


class ZoneMicrostudy:
    def __init__(
        self,
        model_type: str,
        master: pd.DataFrame,
        definitions: pd.DataFrame,
        timeout_seconds: float,
        n_trials: int,
        recent_validation_weight: float,
        output_dir: Path,
        seed: int,
        target_date: str,
        smoke_epochs: int | None,
    ) -> None:
        self.model_type = model_type
        self.master = master
        self.definitions = definitions
        self.timeout_seconds = timeout_seconds
        self.n_trials = n_trials
        self.recent_validation_weight = recent_validation_weight
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.target_date = target_date
        self.smoke_epochs = smoke_epochs
        self.zone_count = len(definitions)
        self.training = master.loc[master["split_role"].eq("cluster_fit")].copy().sort_values("date")
        self.validation_source = master.loc[master["split_role"].eq("model_validation")].copy().sort_values("date")
        self.forecast_source = master.loc[master["is_forecast"].eq(1)].copy().sort_values("date")
        self.all_features = [
            column for column in master.columns
            if column not in METADATA_COLUMNS and pd.api.types.is_numeric_dtype(master[column])
        ]
        if len(self.all_features) < 5:
            raise RuntimeError("Fewer than five location features are available")
        self.records: list[dict[str, Any]] = []
        self.best: Winner | None = None

    def _sample_params(self, trial: optuna.Trial) -> dict[str, Any]:
        start_year = trial.suggest_int("train_start_year", 1900, 1980, step=10)
        recent_multiplier = trial.suggest_int("recent_oversample_multiplier", 1, 3)
        recent_fraction = trial.suggest_categorical("recent_oversample_fraction", [0.20, 0.35, 0.50])
        feature_stride = trial.suggest_int("feature_ablation_stride", 1, 4)
        feature_offset = 0 if feature_stride == 1 else trial.suggest_int("feature_ablation_offset", 0, feature_stride - 1)
        params: dict[str, Any] = {
            "train_start_year": start_year,
            "recent_oversample_multiplier": recent_multiplier,
            "recent_oversample_fraction": recent_fraction,
            "feature_ablation_stride": feature_stride,
            "feature_ablation_offset": feature_offset,
        }
        if self.model_type == "kan":
            params.update(
                grid_size=trial.suggest_int("grid_size", 3, 8),
                spline_order=trial.suggest_int("spline_order", 2, 4),
                learning_rate=trial.suggest_float("learning_rate", 1e-3, 3e-2, log=True),
            )
        elif self.model_type == "deep_learning":
            params.update(
                hidden_dim=trial.suggest_categorical("hidden_dim", [32, 64, 96, 128]),
                num_layers=trial.suggest_int("num_layers", 2, 5),
                dropout=trial.suggest_float("dropout", 0.0, 0.25, step=0.05),
                learning_rate=trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True),
            )
        else:
            params.update(
                population_size=trial.suggest_int("population_size", 50, 250, step=25),
                learning_rate=trial.suggest_float("learning_rate", 0.05, 0.30, step=0.05),
                crossover_rate=trial.suggest_float("crossover_rate", 0.6, 0.9, step=0.1),
                mutation_rate=trial.suggest_float("mutation_rate", 0.02, 0.10, step=0.02),
            )
        return params

    def _features(self, params: dict[str, Any]) -> list[str]:
        stride = int(params["feature_ablation_stride"])
        offset = int(params["feature_ablation_offset"])
        if stride == 1:
            return list(self.all_features)
        selected = [feature for index, feature in enumerate(self.all_features) if index % stride != offset]
        return selected if len(selected) >= 5 else list(self.all_features)

    def _fit_candidate(self, params: dict[str, Any], trial_number: int) -> Winner:
        torch.manual_seed(self.seed + trial_number)
        np.random.seed(self.seed + trial_number)
        started = time.monotonic()
        train = self.training.loc[pd.to_datetime(self.training["date"]).dt.year.ge(int(params["train_start_year"]))].copy()
        if len(train) < 30 or train[TARGET].nunique() < self.zone_count:
            raise RuntimeError("Training subset is too small or omits a zone")
        features = self._features(params)
        recent_count = max(1, int(math.ceil(len(train) * float(params["recent_oversample_fraction"]))))
        recent = train.tail(recent_count)
        multiplier = int(params["recent_oversample_multiplier"])
        fit_train = pd.concat([train] + [recent] * (multiplier - 1), ignore_index=True)
        model, epochs = _model_and_epochs(self.model_type, params, self.smoke_epochs)
        model.fit(
            fit_train[features], fit_train[TARGET], feature_names=features,
            target_name=TARGET, epochs=epochs,
        )
        train_prediction = model.predict(train[features])
        validation_prediction = model.predict(self.validation_source[features])
        train_metrics = evaluate_zones(
            train[TARGET], train_prediction, self.definitions,
            train["event_latitude"], train["event_longitude"], recent_weight=1.0,
        )
        validation_metrics = evaluate_zones(
            self.validation_source[TARGET], validation_prediction, self.definitions,
            self.validation_source["event_latitude"], self.validation_source["event_longitude"],
            recent_weight=self.recent_validation_weight,
        )
        objective = selection_objective(train_metrics, validation_metrics, self.zone_count)
        validation = self.validation_source[
            ["date", TARGET, "event_magnitude", "event_latitude", "event_longitude", "event_id"]
        ].copy()
        validation.rename(columns={TARGET: "actual_zone"}, inplace=True)
        validation["predicted_zone_continuous"] = validation_prediction
        validation["predicted_zone"] = np.clip(np.rint(validation_prediction), 1, self.zone_count).astype(int)
        forecast_prediction = model.predict(self.forecast_source[features])
        forecast = self.forecast_source[["date"]].copy()
        forecast["forecasted_zone_continuous"] = forecast_prediction
        forecast["forecasted_zone"] = np.clip(np.rint(forecast_prediction), 1, self.zone_count).astype(int)
        return Winner(
            model_type=self.model_type,
            model=model,
            params=params,
            feature_names=features,
            objective=objective,
            train_metrics=train_metrics,
            validation_metrics=validation_metrics,
            validation=validation,
            forecast=forecast,
            elapsed_seconds=time.monotonic() - started,
            successful_trials=0,
            attempted_trials=0,
        )

    def _objective(self, trial: optuna.Trial) -> float:
        params = self._sample_params(trial)
        record: dict[str, Any] = {"trial_number": trial.number, **params, "actual_device": "cpu"}
        try:
            candidate = self._fit_candidate(params, trial.number)
            record.update(
                status="success",
                objective_loss=candidate.objective,
                feature_count=len(candidate.feature_names),
                train_rows=candidate.train_metrics["sample_count"],
                train_mae=candidate.train_metrics["mae_zone_continuous"],
                train_exact_accuracy=candidate.train_metrics["exact_zone_accuracy"],
                validation_rows=candidate.validation_metrics["sample_count"],
                validation_mae=candidate.validation_metrics["mae_zone_continuous"],
                validation_recent_weighted_mae=candidate.validation_metrics["recent_weighted_mae_zone"],
                validation_exact_accuracy=candidate.validation_metrics["exact_zone_accuracy"],
                validation_adjacent_accuracy=candidate.validation_metrics["adjacent_zone_accuracy"],
                validation_macro_f1=candidate.validation_metrics["macro_f1"],
                validation_centroid_distance_km=candidate.validation_metrics["mean_centroid_distance_km"],
                elapsed_seconds=candidate.elapsed_seconds,
            )
            if self.best is None or candidate.objective < self.best.objective:
                self.best = candidate
                LOGGER.info(
                    "New %s location best trial %d: loss %.6f, exact %.3f, adjacent %.3f, MAE %.3f",
                    self.model_type, trial.number, candidate.objective,
                    candidate.validation_metrics["exact_zone_accuracy"],
                    candidate.validation_metrics["adjacent_zone_accuracy"],
                    candidate.validation_metrics["mae_zone_continuous"],
                )
        except Exception as exc:
            record.update(status="failed", objective_loss=999.0, error=f"{type(exc).__name__}: {exc}")
            LOGGER.warning("%s trial %d failed: %s", self.model_type, trial.number, exc)
        self.records.append(record)
        pd.DataFrame(self.records).to_csv(self.output_dir / f"optuna_zone_trials_{self.model_type}.csv", index=False)
        return float(record["objective_loss"])

    def run(self) -> Winner:
        started = time.monotonic()
        LOGGER.info(
            "Starting conditional-zone microstudy %s: %.1fs, CPU, %d training and %d validation events",
            self.model_type, self.timeout_seconds, len(self.training), len(self.validation_source),
        )
        study = optuna.create_study(direction="minimize", study_name=f"zone_{self.model_type}")
        study.optimize(self._objective, n_trials=self.n_trials, timeout=self.timeout_seconds, show_progress_bar=False)
        if self.best is None:
            raise RuntimeError(f"No successful {self.model_type} trial")
        self.best.elapsed_seconds = time.monotonic() - started
        self.best.attempted_trials = len(self.records)
        self.best.successful_trials = sum(record["status"] == "success" for record in self.records)
        self.best.validation.to_csv(self.output_dir / f"best_zone_validation_{self.model_type}.csv", index=False)
        self.best.forecast.to_csv(self.output_dir / f"best_zone_forecast_{self.model_type}.csv", index=False)
        _atomic_json(self.best.params, self.output_dir / f"best_zone_params_{self.model_type}.json")
        _atomic_json(
            {
                "objective_loss": self.best.objective,
                "train_metrics": self.best.train_metrics,
                "validation_metrics": self.best.validation_metrics,
                "attempted_trials": self.best.attempted_trials,
                "successful_trials": self.best.successful_trials,
                "actual_device": "cpu",
                "elapsed_seconds": self.best.elapsed_seconds,
                "feature_count": len(self.best.feature_names),
                "feature_names": self.best.feature_names,
            },
            self.output_dir / f"best_zone_metrics_{self.model_type}.json",
        )
        for suffix in ("png", "pdf"):
            _plot_zone_series(
                self.best.validation,
                self.definitions,
                self.output_dir / f"zone_validation_{self.model_type}.{suffix}",
                prediction_column="predicted_zone_continuous",
                actual_column="actual_zone",
                title=f"{self.model_type.upper()} conditional-zone validation (24 untouched events)",
            )
            _plot_zone_series(
                self.best.forecast,
                self.definitions,
                self.output_dir / f"zone_forecast_{self.model_type}.{suffix}",
                prediction_column="forecasted_zone_continuous",
                target_date=self.target_date,
                title=f"{self.model_type.upper()} conditional zone forecast — event occurrence assumed",
            )
        readme = f"""# {self.model_type.upper()} conditional-zone microstudy

- Actual device: **CPU**.
- Attempts: `{self.best.attempted_trials}`; successful: `{self.best.successful_trials}`.
- Training events: `{len(self.training)}` before time/record ablations.
- Untouched validation events: `{len(self.validation_source)}`.
- Best objective: `{self.best.objective:.6f}` (lower is better).
- Exact validation zone accuracy: `{self.best.validation_metrics['exact_zone_accuracy']:.2%}`.
- Adjacent-zone validation accuracy: `{self.best.validation_metrics['adjacent_zone_accuracy']:.2%}`.
- Validation continuous-zone MAE: `{self.best.validation_metrics['mae_zone_continuous']:.4f}`.

This is a conditional location model. It is not an earthquake occurrence or
hazard forecast.
"""
        (self.output_dir / "README.md").write_text(readme, encoding="utf-8")
        return self.best


def _member_zone_probability(prediction: float, sigma: float, zone_count: int) -> np.ndarray:
    zones = np.arange(1, zone_count + 1, dtype=float)
    probability = np.exp(-0.5 * ((zones - prediction) / max(0.45, sigma)) ** 2)
    return probability / np.maximum(probability.sum(), 1e-12)


def _run_ensemble(
    winners: dict[str, Winner],
    definitions: pd.DataFrame,
    cluster_dir: Path,
    output_dir: Path,
    final_dir: Path,
    target_date: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    raw_weights = {
        model_type: max(0.05, math.exp(-4.0 * winner.objective))
        for model_type, winner in winners.items()
    }
    total = sum(raw_weights.values())
    weights = {model_type: weight / total for model_type, weight in raw_weights.items()}
    reference = winners["kan"].validation[["date", "actual_zone", "event_magnitude", "event_latitude", "event_longitude", "event_id"]].copy()
    prediction = np.zeros(len(reference), dtype=float)
    for model_type, winner in winners.items():
        column = f"predicted_{model_type}"
        reference[column] = winner.validation["predicted_zone_continuous"].to_numpy(float)
        prediction += weights[model_type] * reference[column].to_numpy(float)
    reference["predicted_zone_continuous"] = prediction
    reference["predicted_zone"] = np.clip(np.rint(prediction), 1, len(definitions)).astype(int)
    metrics = evaluate_zones(
        reference["actual_zone"], prediction, definitions,
        reference["event_latitude"], reference["event_longitude"], recent_weight=3.0,
    )
    reference.to_csv(output_dir / "ensemble_zone_validation.csv", index=False)
    forecasts = winners["kan"].forecast[["date"]].copy()
    ensemble_forecast = np.zeros(len(forecasts), dtype=float)
    for model_type, winner in winners.items():
        column = f"forecasted_{model_type}"
        forecasts[column] = winner.forecast["forecasted_zone_continuous"].to_numpy(float)
        ensemble_forecast += weights[model_type] * forecasts[column].to_numpy(float)
    forecasts["forecasted_zone_continuous"] = ensemble_forecast
    forecasts["forecasted_zone"] = np.clip(np.rint(ensemble_forecast), 1, len(definitions)).astype(int)
    forecasts.to_csv(output_dir / "ensemble_zone_forecast.csv", index=False)
    _atomic_json({"weights": weights, "metrics": metrics}, output_dir / "ensemble_zone_metrics.json")
    for suffix in ("png", "pdf"):
        _plot_zone_series(
            reference, definitions, output_dir / f"ensemble_zone_validation.{suffix}",
            prediction_column="predicted_zone_continuous", actual_column="actual_zone",
            title="Weighted KAN + Deep + LCS conditional-zone validation",
        )
        _plot_zone_series(
            forecasts, definitions, output_dir / f"ensemble_zone_forecast.{suffix}",
            prediction_column="forecasted_zone_continuous", target_date=target_date,
            title="Conditional zone forecast — event occurrence assumed externally",
        )
    target = forecasts.loc[pd.to_datetime(forecasts["date"]).eq(pd.Timestamp(target_date))]
    if len(target) != 1:
        raise RuntimeError(f"Target date {target_date} is absent or duplicated in the forecast")
    target_row = target.iloc[0]
    probability = np.zeros(len(definitions), dtype=float)
    member_details: dict[str, Any] = {}
    for model_type, winner in winners.items():
        member_prediction = float(target_row[f"forecasted_{model_type}"])
        residual = winner.validation["predicted_zone_continuous"].to_numpy(float) - winner.validation["actual_zone"].to_numpy(float)
        sigma = max(0.45, float(np.sqrt(np.mean(residual ** 2))))
        member_probability = _member_zone_probability(member_prediction, sigma, len(definitions))
        probability += weights[model_type] * member_probability
        member_details[model_type] = {
            "weight": weights[model_type],
            "continuous_prediction": member_prediction,
            "rounded_zone": int(np.clip(np.rint(member_prediction), 1, len(definitions))),
            "validation_residual_sigma": sigma,
            "zone_probability": {str(index + 1): float(value) for index, value in enumerate(member_probability)},
        }
    probability /= probability.sum()
    top_zone = int(np.argmax(probability) + 1)
    definitions_indexed = definitions.set_index("zone")
    top_definition = definitions_indexed.loc[top_zone].to_dict()
    target_payload = {
        "target_week": target_date,
        "conditioning": "location conditional on an independently assumed M6.9+ event",
        "ensemble_continuous_zone": float(target_row["forecasted_zone_continuous"]),
        "ensemble_rounded_zone": int(target_row["forecasted_zone"]),
        "probability_top_zone": top_zone,
        "probability_top_zone_mass": float(probability[top_zone - 1]),
        "zone_probability": {str(index + 1): float(value) for index, value in enumerate(probability)},
        "top_zone_definition": top_definition,
        "member_details": member_details,
        "warning": "Research-only conditional localization; not evidence that an earthquake will occur.",
    }
    _atomic_json(target_payload, final_dir / "estimated_zone_2026-08-24.json")
    pd.DataFrame(
        {
            "zone": np.arange(1, len(definitions) + 1),
            "probability": probability,
            "center_latitude": definitions["center_latitude"],
            "center_longitude": definitions["center_longitude"],
        }
    ).to_csv(final_dir / "estimated_zone_2026-08-24_distribution.csv", index=False)
    grid = pd.read_csv(cluster_dir / "zone_decision_grid.csv")
    events = pd.read_csv(cluster_dir / "zone_event_assignments.csv")
    map_args = SimpleNamespace(
        latitude_min=float(grid["latitude"].min()),
        latitude_max=float(grid["latitude"].max()),
        longitude_min=float(grid["longitude"].min()),
        longitude_max=float(grid["longitude"].max()),
    )
    probabilities = {index + 1: float(value) for index, value in enumerate(probability)}
    for suffix in ("png", "pdf"):
        plot_zone_map(
            grid, definitions, events, final_dir / f"estimated_zone_2026-08-24_map.{suffix}", map_args,
            title=f"Conditional location for week {target_date}: highest mass Z{top_zone} ({probability[top_zone - 1]:.1%})",
            zone_probabilities=probabilities,
        )
    final_md = f"""# Conditional location estimate — week of {target_date}

- Highest probability zone: **Z{top_zone}**.
- Probability mass assigned to Z{top_zone}: **{probability[top_zone - 1]:.2%}**.
- Learned centroid: **{top_definition['center_latitude']:.3f} N, {top_definition['center_longitude']:.3f} E**.
- Ensemble continuous index: **{float(target_row['forecasted_zone_continuous']):.3f}**.

The estimate is conditional on an event already being assumed for that week.
It does not predict occurrence, exact coordinates, damage or hazard. Zone
probabilities inherit uncertainty from only 24 untouched validation events.
"""
    (final_dir / "RESULT.md").write_text(final_md, encoding="utf-8")
    ensemble_readme = "# Conditional-zone ensemble\n\n" + final_md
    (output_dir / "README.md").write_text(ensemble_readme, encoding="utf-8")
    return {"weights": weights, "metrics": metrics, "target": target_payload}


def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    started = time.monotonic()
    master_path = Path(args.input_master).expanduser().resolve()
    cluster_dir = Path(args.cluster_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    micro_root = output_dir / "03_microstudies"
    ensemble_dir = output_dir / "04_ensemble"
    final_dir = output_dir / "05_final"
    master = pd.read_csv(master_path, low_memory=False)
    master["date"] = pd.to_datetime(master["date"])
    definitions = pd.read_csv(cluster_dir / "zone_definitions.csv")
    if not definitions["center_latitude"].is_monotonic_increasing:
        raise RuntimeError("Zone definitions are not numbered south-to-north")
    timeout_per_model = args.total_timeout_seconds / len(MODEL_TYPES)
    winners: dict[str, Winner] = {}
    for index, model_type in enumerate(MODEL_TYPES):
        runner = ZoneMicrostudy(
            model_type=model_type,
            master=master,
            definitions=definitions,
            timeout_seconds=timeout_per_model,
            n_trials=args.n_trials_per_study,
            recent_validation_weight=args.recent_validation_weight,
            output_dir=micro_root / f"study_{model_type}",
            seed=args.seed + index * 10000,
            target_date=args.target_date,
            smoke_epochs=args.smoke_epochs,
        )
        winners[model_type] = runner.run()
    ensemble = _run_ensemble(
        winners, definitions, cluster_dir, ensemble_dir, final_dir, args.target_date
    )
    result = {
        "actual_device": "cpu",
        "elapsed_seconds": time.monotonic() - started,
        "requested_timeout_seconds": args.total_timeout_seconds,
        "input_master": str(master_path),
        "cluster_dir": str(cluster_dir),
        "microstudies": {
            model_type: {
                "attempted_trials": winner.attempted_trials,
                "successful_trials": winner.successful_trials,
                "best_objective": winner.objective,
                "validation_metrics": winner.validation_metrics,
            }
            for model_type, winner in winners.items()
        },
        "ensemble": ensemble,
    }
    _atomic_json(result, output_dir / "completion.json")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    result = run(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

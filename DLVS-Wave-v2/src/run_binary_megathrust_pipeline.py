"""Autonomous two-level CPU pipeline for a Japan-wide binary M7.7+ study."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.binary_megathrust_data import (
    DATE_COLUMN,
    TARGET_COLUMN,
    BinaryDataConfig,
    TrialSplit,
    build_trial_split,
    build_validation_corridor_index,
    select_features,
)
from src.binary_megathrust_models import BinaryMetrics, binary_metrics, make_binary_model
from src.binary_megathrust_report import create_binary_report, create_model_plot
from src.master_fusion import build_clean_binary_megathrust_master
from src.pretreatment import PI_DIGIT_TRIPLETS


LOGGER = logging.getLogger("dlvs_wave.binary_megathrust")
MODELS = ("kan", "deep_learning", "lcs")


PARAMETER_SPECS: dict[str, dict[str, tuple[Any, ...]]] = {
    "kan": {
        "train_start_year": ("int", 1900, 1960, 20),
        "window_before": ("int", 2, 7, 1),
        "window_after": ("int", 2, 7, 1),
        "background_ratio": ("float", 0.05, 0.30),
        "background_chunk_weeks": ("int", 2, 13, 1),
        "feature_count": ("categorical", [16, 24, 32, 48]),
        "grid_size": ("int", 3, 5, 1),
        "spline_order": ("int", 2, 3, 1),
        "hidden_dim": ("categorical", [8, 12, 16]),
        "learning_rate": ("logfloat", 5e-4, 2e-2),
        "weight_decay": ("logfloat", 1e-6, 1e-3),
        "focal_alpha": ("float", 0.65, 0.90),
        "focal_gamma": ("float", 1.0, 3.0),
        "probability_bias": ("float", -8.0, 0.0),
        "epochs": ("categorical", [20, 30, 40]),
    },
    "deep_learning": {
        "train_start_year": ("int", 1900, 1960, 20),
        "window_before": ("int", 2, 7, 1),
        "window_after": ("int", 2, 7, 1),
        "background_ratio": ("float", 0.05, 0.30),
        "background_chunk_weeks": ("int", 2, 13, 1),
        "feature_count": ("categorical", [24, 48, 72, 96]),
        "hidden_dim": ("categorical", [32, 64, 96]),
        "num_layers": ("int", 2, 4, 1),
        "dropout": ("float", 0.0, 0.30),
        "learning_rate": ("logfloat", 1e-4, 1e-2),
        "weight_decay": ("logfloat", 1e-6, 1e-3),
        "focal_alpha": ("float", 0.65, 0.90),
        "focal_gamma": ("float", 1.0, 3.0),
        "probability_bias": ("float", -8.0, 0.0),
        "epochs": ("categorical", [20, 35, 50]),
    },
    "lcs": {
        "train_start_year": ("int", 1900, 1960, 20),
        "window_before": ("int", 2, 7, 1),
        "window_after": ("int", 2, 7, 1),
        "background_ratio": ("float", 0.05, 0.30),
        "background_chunk_weeks": ("int", 2, 13, 1),
        "feature_count": ("categorical", [12, 16, 24, 32]),
        "population_size": ("int", 60, 180, 20),
        "learning_rate": ("float", 0.05, 0.30),
        "crossover_rate": ("float", 0.60, 0.90),
        "mutation_rate": ("float", 0.02, 0.12),
        "probability_bias": ("float", -4.0, 4.0),
        "distance_temperature": ("logfloat", 0.10, 5.0),
        "epochs": ("categorical", [10, 20, 30]),
    },
}


def configure_window_space(
    before_min: int,
    before_max: int,
    after_min: int,
    after_max: int,
) -> None:
    """Apply one explicit corridor contract to every model family."""
    bounds = (before_min, before_max, after_min, after_max)
    if not all(2 <= int(value) <= 7 for value in bounds):
        raise ValueError("All window bounds must be between 2 and 7 weeks")
    if before_min > before_max or after_min > after_max:
        raise ValueError("Window minimum cannot exceed its maximum")
    for model_type in MODELS:
        PARAMETER_SPECS[model_type]["window_before"] = ("int", int(before_min), int(before_max), 1)
        PARAMETER_SPECS[model_type]["window_after"] = ("int", int(after_min), int(after_max), 1)


@dataclass
class CandidateResult:
    record: dict[str, Any]
    split: TrialSplit
    features: list[str]
    validation_probability: np.ndarray
    training_probability: np.ndarray


class Surrogate(nn.Module):
    def __init__(self, dimensions: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(dimensions, 64),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(64, 64),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(64, 1),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.network(values).squeeze(-1)

    def predict_mc(
        self,
        values: torch.Tensor,
        *,
        samples: int = 20,
        differentiable: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return Monte-Carlo Dropout mean and standard deviation."""
        del differentiable  # gradients remain enabled unless the caller enters no_grad
        self.train()
        draws = torch.stack([self(values) for _ in range(max(2, int(samples)))], dim=0)
        return draws.mean(dim=0), draws.std(dim=0, unbiased=False).clamp_min(1e-6)


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _atomic_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _suggest(trial: optuna.Trial, model_type: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, spec in PARAMETER_SPECS[model_type].items():
        kind = spec[0]
        if kind == "int":
            params[name] = (
                int(spec[1])
                if int(spec[1]) == int(spec[2])
                else trial.suggest_int(name, int(spec[1]), int(spec[2]), step=int(spec[3]))
            )
        elif kind == "float":
            params[name] = trial.suggest_float(name, float(spec[1]), float(spec[2]))
        elif kind == "logfloat":
            params[name] = trial.suggest_float(name, float(spec[1]), float(spec[2]), log=True)
        else:
            params[name] = trial.suggest_categorical(name, list(spec[1]))
    return params


def _parameter_names(model_type: str) -> list[str]:
    return list(PARAMETER_SPECS[model_type])


def _encode(model_type: str, params: dict[str, Any]) -> np.ndarray:
    encoded: list[float] = []
    for name, spec in PARAMETER_SPECS[model_type].items():
        value = params[name]
        kind = spec[0]
        if kind == "categorical":
            choices = list(spec[1])
            index = choices.index(value) if value in choices else int(np.argmin(np.abs(np.asarray(choices, float) - float(value))))
            encoded.append(index / max(1, len(choices) - 1))
        elif kind == "logfloat":
            encoded.append((math.log(float(value)) - math.log(float(spec[1]))) / (math.log(float(spec[2])) - math.log(float(spec[1]))))
        else:
            span = float(spec[2]) - float(spec[1])
            encoded.append(0.0 if span == 0.0 else (float(value) - float(spec[1])) / span)
    return np.clip(np.asarray(encoded, dtype=np.float32), 0.0, 1.0)


def _decode(model_type: str, vector: np.ndarray) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for value, (name, spec) in zip(np.clip(vector, 0.0, 1.0), PARAMETER_SPECS[model_type].items()):
        kind = spec[0]
        if kind == "categorical":
            choices = list(spec[1])
            params[name] = choices[int(round(float(value) * (len(choices) - 1)))]
        elif kind == "logfloat":
            params[name] = float(math.exp(math.log(float(spec[1])) + float(value) * (math.log(float(spec[2])) - math.log(float(spec[1])))))
        elif kind == "int":
            if int(spec[1]) == int(spec[2]):
                params[name] = int(spec[1])
            else:
                raw = float(spec[1]) + float(value) * (float(spec[2]) - float(spec[1]))
                step = int(spec[3])
                params[name] = int(round((raw - int(spec[1])) / step) * step + int(spec[1]))
                params[name] = int(np.clip(params[name], int(spec[1]), int(spec[2])))
        else:
            params[name] = float(spec[1]) + float(value) * (float(spec[2]) - float(spec[1]))
    return params


def _canonical(model_type: str, params: dict[str, Any]) -> tuple[Any, ...]:
    values = []
    for name in _parameter_names(model_type):
        value = params[name]
        values.append(round(float(value), 8) if isinstance(value, float) else value)
    return tuple(values)


def _record_params(model_type: str, record: dict[str, Any]) -> dict[str, Any]:
    return {name: record[name] for name in _parameter_names(model_type)}


def _quality_gate(record: dict[str, Any]) -> bool:
    return int(record.get("val_fp", 999999)) <= 1 and float(record.get("val_recall", 0.0)) >= 0.50


def _successful(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in records
        if row.get("status") == "success" and float(row.get("objective_loss", 999.0)) < 500.0
    ]


def _best(records: list[dict[str, Any]], gated: bool = False) -> dict[str, Any] | None:
    candidates = [row for row in _successful(records) if not gated or _quality_gate(row)]
    return min(candidates, key=lambda row: float(row["objective_loss"])) if candidates else None


def _metrics_columns(prefix: str, metrics: BinaryMetrics) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.to_dict().items() if key != "objective_loss"}


def event_peak_diagnostics(
    validation_dates: pd.Series,
    probability: np.ndarray | pd.Series,
    corridor_index: pd.DataFrame,
    threshold: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Measure predicted-peak displacement independently inside each event slice."""
    predictions = pd.DataFrame({
        "row_date": pd.to_datetime(validation_dates).to_numpy(),
        "probability": np.asarray(probability, dtype=float),
    })
    indexed = corridor_index.copy()
    indexed["row_date"] = pd.to_datetime(indexed["row_date"])
    merged = indexed.merge(predictions, on="row_date", how="left", validate="many_to_one")
    rows: list[dict[str, Any]] = []
    for (event_number, event_id), episode in merged.groupby(["event_number", "event_id"], sort=True):
        episode = episode.dropna(subset=["probability"]).copy()
        if episode.empty or not episode["relative_week"].eq(0).any():
            raise ValueError(f"Incomplete validation corridor for event {event_id}")
        actual = episode.loc[episode["relative_week"].eq(0)].iloc[0]
        peak = episode.loc[episode["probability"].idxmax()]
        near = episode.loc[episode["relative_week"].abs().le(1)]
        signed_error = int(peak["relative_week"])
        rows.append({
            "event_number": int(event_number),
            "event_id": str(event_id),
            "actual_event_date": pd.Timestamp(actual["event_date"]).date().isoformat(),
            "event_magnitude": float(actual["event_magnitude"]),
            "predicted_peak_date": pd.Timestamp(peak["row_date"]).date().isoformat(),
            "signed_peak_error_weeks": signed_error,
            "absolute_peak_error_weeks": abs(signed_error),
            "probability_at_actual_week": float(actual["probability"]),
            "maximum_corridor_probability": float(peak["probability"]),
            "gate_hit_actual_week": int(float(actual["probability"]) >= threshold),
            "gate_hit_plusminus_1week": int(bool(near["probability"].ge(threshold).any())),
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No event-level peak diagnostics could be computed")
    span = max(1, int(indexed["relative_week"].abs().max()))
    hit_rate = float(frame["gate_hit_plusminus_1week"].mean())
    summary = {
        "event_peak_count": int(len(frame)),
        "event_peak_mae_weeks": float(frame["absolute_peak_error_weeks"].mean()),
        "event_peak_max_error_weeks": int(frame["absolute_peak_error_weeks"].max()),
        "event_peak_signed_mean_weeks": float(frame["signed_peak_error_weeks"].mean()),
        "event_gate_hit_plusminus_1week_rate": hit_rate,
        "event_peak_span_weeks": span,
    }
    return summary, frame


def evaluate_candidate(
    model_type: str,
    params: dict[str, Any],
    clean: pd.DataFrame,
    feature_candidates: list[str],
    *,
    validation_event_count: int,
    validation_weeks_before: int,
    validation_weeks_after: int,
    decision_threshold: float,
    seed: int,
    phase: str,
    trial_number: int,
    epochs_override: int | None = None,
) -> CandidateResult:
    split = build_trial_split(
        clean,
        window_before=int(params["window_before"]),
        window_after=int(params["window_after"]),
        background_ratio=float(params["background_ratio"]),
        train_start_year=int(params["train_start_year"]),
        validation_event_count=validation_event_count,
        seed=seed,
        background_chunk_weeks=int(params["background_chunk_weeks"]),
        validation_weeks_before=validation_weeks_before,
        validation_weeks_after=validation_weeks_after,
    )
    features = select_features(split.train, feature_candidates, int(params["feature_count"]))
    if not features:
        raise ValueError("No usable compacted predictors selected")
    _seed_everything(seed)
    model = make_binary_model(model_type, params, seed)
    epochs = int(epochs_override if epochs_override is not None else params["epochs"])
    model.fit(split.train[features], split.train[TARGET_COLUMN], epochs=epochs)
    train_probability = model.predict_proba(split.train[features])
    validation_probability = model.predict_proba(split.validation[features])
    train_metrics = binary_metrics(split.train[TARGET_COLUMN], train_probability, decision_threshold)
    val_metrics = binary_metrics(split.validation[TARGET_COLUMN], validation_probability, decision_threshold)
    peak_summary, _ = event_peak_diagnostics(
        split.validation[DATE_COLUMN],
        validation_probability,
        split.validation_corridor_index,
        decision_threshold,
    )
    # Peak displacement remains a separately reported diagnostic.  It is not a
    # hidden addend: model selection follows the exact user-declared loss.
    combined_objective = float(val_metrics.objective_loss)
    record = {
        "phase": phase,
        "trial_number": int(trial_number),
        "status": "success",
        "objective_loss": combined_objective,
        "classification_objective_loss": float(val_metrics.objective_loss),
        "peak_distance_penalty": 0.0,
        "peak_miss_penalty": 0.0,
        "objective_contract": (
            "FocalLoss + 3*(1-F1) + 3.5*FP_Rate + 2.5*FN_Rate + 0.5*Depression_MAE"
        ),
        "seed": int(seed),
        "selected_feature_count": len(features),
        "selected_features": "|".join(features),
        "train_samples": len(split.train),
        "validation_samples": len(split.validation),
        "validation_start": split.validation_start.date().isoformat(),
        "validation_event_weeks": "|".join(value.date().isoformat() for value in split.validation_event_weeks),
        "validation_weeks_before": int(validation_weeks_before),
        "validation_weeks_after": int(validation_weeks_after),
        "pi_triplets_used": "|".join(
            str(value) for value in split.training_background_chunks.get(
                "pi_triplet", pd.Series(dtype=int)
            ).tolist()
        ),
        "background_chunk_count": len(split.training_background_chunks),
        **peak_summary,
        **_metrics_columns("train", train_metrics),
        **_metrics_columns("val", val_metrics),
        **params,
    }
    return CandidateResult(record, split, features, validation_probability, train_probability)


def _run_level1_model(
    model_type: str,
    clean: pd.DataFrame,
    features: list[str],
    output_dir: Path,
    *,
    timeout_seconds: float,
    max_trials: int,
    validation_event_count: int,
    validation_weeks_before: int,
    validation_weeks_after: int,
    decision_threshold: float,
    base_seed: int,
    epochs_override: int | None,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    trials_path = output_dir / f"optuna_trials_{model_type}.csv"
    records = pd.read_csv(trials_path).where(pd.notna, None).to_dict(orient="records") if trials_path.exists() else []
    known = {int(row["trial_number"]) for row in records if row.get("trial_number") is not None}
    storage = f"sqlite:///{output_dir / 'optuna_study.sqlite3'}"
    study = optuna.create_study(
        direction="minimize",
        study_name=f"japan_m77_binary_{model_type}",
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=base_seed, multivariate=True),
    )
    if not study.trials:
        # Guarantee a bottom-up ablation pass before TPE takes over.  Partial
        # enqueued parameter dictionaries leave every other dimension tunable.
        feature_domain = list(PARAMETER_SPECS[model_type]["feature_count"][1])
        for feature_count in sorted(feature_domain):
            study.enqueue_trial({"feature_count": feature_count})

    def objective(trial: optuna.Trial) -> float:
        if trial.number in known:
            previous = next(row for row in records if int(row["trial_number"]) == trial.number)
            return float(previous.get("objective_loss", 999.0))
        params = _suggest(trial, model_type)
        seed = base_seed + trial.number
        try:
            result = evaluate_candidate(
                model_type,
                params,
                clean,
                features,
                validation_event_count=validation_event_count,
                validation_weeks_before=validation_weeks_before,
                validation_weeks_after=validation_weeks_after,
                decision_threshold=decision_threshold,
                seed=seed,
                phase="level1",
                trial_number=trial.number,
                epochs_override=epochs_override,
            )
            record = result.record
        except Exception as exc:  # one invalid configuration must not stop a timed study
            LOGGER.exception("%s Level 1 trial %d failed", model_type, trial.number)
            record = {
                "phase": "level1",
                "trial_number": trial.number,
                "status": "failed",
                "objective_loss": 999.0,
                "seed": seed,
                "error": f"{type(exc).__name__}: {exc}",
                **params,
            }
        records.append(record)
        known.add(trial.number)
        _atomic_csv(pd.DataFrame(records).sort_values("trial_number"), trials_path)
        if record.get("status") == "success":
            trial.set_user_attr("val_fp", int(record["val_fp"]))
            trial.set_user_attr("val_recall", float(record["val_recall"]))
        return float(record["objective_loss"])

    finished_trials = sum(1 for trial in study.trials if trial.state.is_finished())
    remaining = max(0, int(max_trials) - finished_trials)
    if remaining:
        LOGGER.info("Level 1 %s: up to %d additional trials, %.0fs budget", model_type, remaining, timeout_seconds)
        study.optimize(objective, n_trials=remaining, timeout=max(1.0, timeout_seconds), show_progress_bar=False)
    successful = _successful(records)
    overall = _best(records)
    gated = _best(records, gated=True)
    _atomic_json(
        {
            "model": model_type,
            "successful_trials": len(successful),
            "quality_gate": {"max_false_positives": 1, "min_recall": 0.50},
            "quality_gate_passed": gated is not None,
            "best_overall": overall,
            "best_gate_passing": gated,
        },
        output_dir / f"best_params_{model_type}.json",
    )
    return records


def _fit_surrogate(model_type: str, records: list[dict[str, Any]], seed: int, epochs: int) -> tuple[Surrogate, float, float]:
    _seed_everything(seed)
    x = np.stack([_encode(model_type, _record_params(model_type, row)) for row in records])
    y = np.asarray([float(row["objective_loss"]) for row in records], dtype=np.float32)
    mean, std = float(y.mean()), float(y.std())
    if std < 1e-6:
        std = 1.0
    tensor_x = torch.as_tensor(x, dtype=torch.float32)
    tensor_y = torch.as_tensor((y - mean) / std, dtype=torch.float32)
    model = Surrogate(x.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    for _ in range(max(1, int(epochs))):
        optimizer.zero_grad(set_to_none=True)
        loss = nn.functional.smooth_l1_loss(model(tensor_x), tensor_y)
        loss.backward()
        optimizer.step()
    return model.eval(), mean, std


def _latent_candidate(
    model_type: str,
    surrogate: Surrogate,
    best_params: dict[str, Any],
    best_loss_scaled: float,
    rng: np.random.Generator,
    attempt: int,
) -> tuple[dict[str, Any], str]:
    start = _encode(model_type, best_params)
    jitter = rng.normal(0.0, min(0.22, 0.025 + attempt * 0.003), len(start)).astype(np.float32)
    latent = nn.Parameter(torch.as_tensor(np.clip(start + jitter, 0.0, 1.0), dtype=torch.float32))
    optimizer = torch.optim.Adam([latent], lr=0.04)
    standard_normal = torch.distributions.Normal(torch.tensor(0.0), torch.tensor(1.0))
    for _ in range(45):
        optimizer.zero_grad(set_to_none=True)
        mean, std = surrogate.predict_mc(
            latent.clamp(0.0, 1.0).unsqueeze(0), samples=16, differentiable=True
        )
        improvement = torch.as_tensor(best_loss_scaled, dtype=mean.dtype) - mean
        z_score = improvement / std
        expected_improvement = (
            improvement * standard_normal.cdf(z_score)
            + std * torch.exp(standard_normal.log_prob(z_score))
        ).clamp_min(0.0).mean()
        regularization = 0.015 * torch.mean((latent - torch.as_tensor(start)) ** 2)
        (-expected_improvement + regularization).backward()
        optimizer.step()
    vector = latent.detach().clamp(0.0, 1.0).numpy()
    return _decode(model_type, vector), "mc_dropout_expected_improvement_gradient"


def _run_level2_model(
    model_type: str,
    level1_records: list[dict[str, Any]],
    clean: pd.DataFrame,
    features: list[str],
    output_dir: Path,
    *,
    timeout_seconds: float,
    max_trials: int,
    validation_event_count: int,
    validation_weeks_before: int,
    validation_weeks_after: int,
    decision_threshold: float,
    base_seed: int,
    surrogate_epochs: int,
    epochs_override: int | None,
    quality_gate_policy: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    level1_best = _best(level1_records)
    gated_level1 = _best(level1_records, gated=True)
    baseline = gated_level1 if quality_gate_policy == "enforce" else level1_best
    if baseline is None:
        payload = {"model": model_type, "status": "skipped", "reason": "No eligible successful Level 1 trial"}
        _atomic_json(payload, output_dir / f"meta_best_params_{model_type}.json")
        return [], payload
    training_records = _successful(level1_records)
    if len(training_records) < 5:
        payload = {"model": model_type, "status": "skipped", "reason": "Fewer than 5 successful Level 1 trials"}
        _atomic_json(payload, output_dir / f"meta_best_params_{model_type}.json")
        return [], payload

    meta_path = output_dir / f"meta_trials_{model_type}.csv"
    meta_records = pd.read_csv(meta_path).where(pd.notna, None).to_dict(orient="records") if meta_path.exists() else []
    seen = {_canonical(model_type, _record_params(model_type, row)) for row in training_records + _successful(meta_records)}
    rng = np.random.default_rng(base_seed + 10000)
    start = time.monotonic()
    iteration = len(meta_records)
    surrogate: Surrogate | None = None
    surrogate_mean = 0.0
    surrogate_std = 1.0
    while iteration < max_trials and time.monotonic() - start < timeout_seconds:
        if surrogate is None or iteration % 5 == 0:
            surrogate, surrogate_mean, surrogate_std = _fit_surrogate(
                model_type, training_records + _successful(meta_records), base_seed + iteration, surrogate_epochs
            )
        eligible_meta = _successful(meta_records)
        if quality_gate_policy == "enforce":
            eligible_meta = [row for row in eligible_meta if _quality_gate(row)]
        combined_best = min([baseline, *eligible_meta], key=lambda row: float(row["objective_loss"]))
        params, method = _latent_candidate(
            model_type,
            surrogate,
            _record_params(model_type, combined_best),
            (float(combined_best["objective_loss"]) - surrogate_mean) / surrogate_std,
            rng,
            iteration,
        )
        attempts = 0
        while _canonical(model_type, params) in seen and attempts < 100:
            params = _decode(model_type, rng.random(len(_parameter_names(model_type))))
            method = "random_fallback"
            attempts += 1
        seen.add(_canonical(model_type, params))
        seed = base_seed + 100000 + iteration
        try:
            result = evaluate_candidate(
                model_type,
                params,
                clean,
                features,
                validation_event_count=validation_event_count,
                validation_weeks_before=validation_weeks_before,
                validation_weeks_after=validation_weeks_after,
                decision_threshold=decision_threshold,
                seed=seed,
                phase="level2",
                trial_number=iteration,
                epochs_override=epochs_override,
            )
            record = result.record
            record["meta_trial_number"] = iteration
            record["proposal_method"] = method
        except Exception as exc:
            LOGGER.exception("%s Level 2 trial %d failed", model_type, iteration)
            record = {
                "phase": "level2",
                "trial_number": iteration,
                "meta_trial_number": iteration,
                "proposal_method": method,
                "status": "failed",
                "objective_loss": 999.0,
                "seed": seed,
                "error": f"{type(exc).__name__}: {exc}",
                **params,
            }
        meta_records.append(record)
        _atomic_csv(pd.DataFrame(meta_records).sort_values("meta_trial_number"), meta_path)
        iteration += 1

    phase2_best = _best(meta_records)
    phase2_gated = _best(meta_records, gated=True)
    # A Level 2 output is always emitted from the best Level 2 candidate, even when
    # it does not improve Level 1. The baseline is used only as a fallback if all
    # Level 2 candidates fail technically.
    selection = phase2_gated if quality_gate_policy == "enforce" else phase2_best
    selection = selection or baseline
    payload = {
        "model": model_type,
        "status": "completed",
        "quality_gate_policy": quality_gate_policy,
        "level1_best": level1_best,
        "level1_gate_winner": gated_level1,
        "phase2_best": phase2_best,
        "phase2_gate_winner": phase2_gated,
        "selected_source": selection["phase"],
        "selected_params": _record_params(model_type, selection),
        "selected_record": selection,
        "phase2_improved_vs_level1": bool(
            phase2_best and level1_best
            and float(phase2_best["objective_loss"]) < float(level1_best["objective_loss"])
        ),
        "selected_quality_gate_passed": _quality_gate(selection),
    }
    _atomic_json(payload, output_dir / f"meta_best_params_{model_type}.json")
    return meta_records, payload


def collapse_gate_runs(probability: pd.Series, threshold: float) -> np.ndarray:
    """Keep one maximum-probability week from each consecutive gate exceedance."""
    values = probability.to_numpy(dtype=float)
    above = np.isfinite(values) & (values >= threshold)
    output = np.zeros(len(values), dtype=np.int8)
    index = 0
    while index < len(values):
        if not above[index]:
            index += 1
            continue
        end = index + 1
        while end < len(values) and above[end]:
            end += 1
        output[index + int(np.nanargmax(values[index:end]))] = 1
        index = end
    return output


def _finalize_model(
    model_type: str,
    selected_record: dict[str, Any],
    clean: pd.DataFrame,
    feature_candidates: list[str],
    output_dir: Path,
    config: BinaryDataConfig,
    decision_threshold: float,
    epochs_override: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    params = _record_params(model_type, selected_record)
    seed = int(selected_record["seed"])
    holdout = evaluate_candidate(
        model_type,
        params,
        clean,
        feature_candidates,
        validation_event_count=config.validation_event_count,
        validation_weeks_before=config.validation_weeks_before,
        validation_weeks_after=config.validation_weeks_after,
        decision_threshold=decision_threshold,
        seed=seed,
        phase="selected_refit_holdout",
        trial_number=int(selected_record["trial_number"]),
        epochs_override=epochs_override,
    )
    validation_columns = [DATE_COLUMN, TARGET_COLUMN, "sample_role"]
    if "japan_max_magnitude" in holdout.split.validation:
        validation_columns.append("japan_max_magnitude")
    validation = holdout.split.validation[validation_columns].copy()
    validation.rename(columns={TARGET_COLUMN: "actual"}, inplace=True)
    if "japan_max_magnitude" in validation:
        validation.rename(columns={"japan_max_magnitude": "event_magnitude"}, inplace=True)
    validation[f"probability_{model_type}"] = holdout.validation_probability
    training_context = holdout.split.train[[DATE_COLUMN, "japan_max_magnitude"]].copy()
    training_context["japan_max_magnitude"] = training_context["japan_max_magnitude"].fillna(0.0)

    # The prospective refit honors the same hard chronological cutoff as the
    # reported validation.  No post-corridor-start observation is fitted.
    full_train = holdout.split.train.copy()
    full_background_chunks = holdout.split.training_background_chunks.copy()
    full_features = select_features(full_train, feature_candidates, int(params["feature_count"]))
    model = make_binary_model(model_type, params, seed + 200000)
    epochs = int(epochs_override if epochs_override is not None else params["epochs"])
    model.fit(full_train[full_features], full_train[TARGET_COLUMN], epochs=epochs)
    forecast_source = clean.loc[
        clean[DATE_COLUMN].between(pd.Timestamp(config.forecast_start), pd.Timestamp(config.forecast_end))
    ].copy()
    probability = model.predict_proba(forecast_source[full_features])
    forecast = forecast_source[[DATE_COLUMN]].copy()
    forecast[f"probability_{model_type}"] = probability
    forecast["above_confidence_gate"] = (probability >= decision_threshold).astype(np.int8)
    forecast["event_signal"] = collapse_gate_runs(forecast[f"probability_{model_type}"], decision_threshold)

    suffix = ".json" if model_type == "lcs" else ".pt"
    model_path = output_dir / f"selected_model_{model_type}{suffix}"
    model.save(model_path, params)
    metrics = binary_metrics(validation["actual"], validation[f"probability_{model_type}"], decision_threshold)
    peak_summary, peak_frame = event_peak_diagnostics(
        validation[DATE_COLUMN],
        validation[f"probability_{model_type}"],
        holdout.split.validation_corridor_index,
        decision_threshold,
    )
    metrics_payload = metrics.to_dict()
    metrics_payload["classification_objective_loss"] = float(metrics.objective_loss)
    metrics_payload["objective_loss"] = float(holdout.record["objective_loss"])
    metrics_payload.update(peak_summary)
    details = {
        "model": model_type,
        "selected_source": selected_record["phase"],
        "params": params,
        "holdout_metrics": metrics_payload,
        "event_peak_diagnostics": peak_frame.to_dict(orient="records"),
        "holdout_features": holdout.features,
        "forecast_refit_features": full_features,
        "full_training_samples": len(full_train),
        "model_path": str(model_path),
        "quality_gate_passed": metrics.fp <= 1 and metrics.recall >= 0.50,
        "validation_weeks_before": config.validation_weeks_before,
        "validation_weeks_after": config.validation_weeks_after,
        "pi_sampling": "three-digit millesimi from pretreatment.PI_DIGIT_TRIPLETS",
        "holdout_background_chunk_count": len(holdout.split.training_background_chunks),
        "full_refit_background_chunk_count": len(full_background_chunks),
    }
    _atomic_csv(validation, output_dir / f"selected_validation_{model_type}.csv")
    _atomic_csv(forecast, output_dir / f"selected_forecast_{model_type}.csv")
    _atomic_csv(training_context, output_dir / f"selected_training_context_{model_type}.csv")
    _atomic_csv(
        holdout.split.validation_corridor_index,
        output_dir / f"selected_validation_corridor_index_{model_type}.csv",
    )
    _atomic_csv(peak_frame, output_dir / f"selected_event_peak_diagnostics_{model_type}.csv")
    _atomic_csv(
        holdout.split.training_background_chunks,
        output_dir / f"selected_training_pi_chunks_{model_type}.csv",
    )
    _atomic_csv(
        full_background_chunks,
        output_dir / f"selected_full_refit_pi_chunks_{model_type}.csv",
    )
    _atomic_json(details, output_dir / f"selected_manifest_{model_type}.json")
    return validation, forecast, training_context, details


def _weights(metrics: dict[str, dict[str, Any]]) -> dict[str, float]:
    raw: dict[str, float] = {}
    for model, values in metrics.items():
        validation_quality = (
            0.45 * float(values.get("f1", 0.0))
            + 0.25 * float(values.get("precision", 0.0))
            + 0.20 * float(values.get("recall", 0.0))
            + 0.10 * float(values.get("auc", 0.5))
        )
        false_positive_factor = 1.0 / (1.0 + float(values.get("fp", 0)))
        objective_factor = 1.0 / (1.0 + float(values.get("objective_loss", 999.0)))
        # Cubing the composite validation score intentionally concentrates weight
        # on the models with the strongest frozen holdout performance.
        raw[model] = max(1e-12, validation_quality**3 * false_positive_factor * objective_factor)
    total = sum(raw.values())
    return {model: value / total for model, value in raw.items()}


def _merge_validation(frames: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    for model, frame in frames.items():
        columns = [DATE_COLUMN, "actual", f"probability_{model}"]
        if merged is None and "event_magnitude" in frame:
            columns.insert(2, "event_magnitude")
        merged = frame[columns].copy() if merged is None else merged.merge(frame[columns], on=[DATE_COLUMN, "actual"], how="inner")
    assert merged is not None
    merged["probability_ensemble"] = sum(
        weights[model] * merged[f"probability_{model}"] for model in frames
    )
    return merged.sort_values(DATE_COLUMN).reset_index(drop=True)


def _merge_forecast(frames: dict[str, pd.DataFrame], weights: dict[str, float]) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    for model, frame in frames.items():
        columns = [DATE_COLUMN, f"probability_{model}"]
        merged = frame[columns].copy() if merged is None else merged.merge(frame[columns], on=DATE_COLUMN, how="inner")
    assert merged is not None
    merged["ensemble_probability"] = sum(
        weights[model] * merged[f"probability_{model}"] for model in frames
    )
    return merged.sort_values(DATE_COLUMN).reset_index(drop=True)


def _write_readme(output_dir: Path, args: argparse.Namespace, summary: dict[str, Any]) -> None:
    content = f"""# Japan-wide binary megathrust study

This directory contains an autonomous, CPU-only, two-level research pipeline.

- Target: weekly Japan-extended event indicator for `M >= {args.magnitude_threshold:.1f}`.
- Cutoff: `{args.cutoff_utc}`; rows after the cutoff are unlabelled prospective rows.
- Forecast: `{args.forecast_start}` through `{args.forecast_end}`.
- Predictors: `{summary['feature_count']}` compacted astronomical fields only.
- Hard negatives: foreign events at or above the target threshold are explicitly labelled `0`.
- Training windows explored: before `{args.window_before_min}..{args.window_before_max}` weeks; after `{args.window_after_min}..{args.window_after_max}` weeks.
- Training quiet background: contiguous inter-event chunks selected deterministically with three-digit millesimi of pi mixed into each trial seed.
- Validation: exactly `{args.validation_weeks_before}` weekly indices before and `{args.validation_weeks_after}` after each of the two held-out events.
- Quality gate: validation `FP <= 1` and `Recall >= 0.50`; policy `{args.quality_gate_policy}`.
- In advisory mode, the gate is reported but never suppresses L1, L2, or the best-available forecast.
- Digital gate: ensemble score `>= {args.decision_threshold:.2f}`, collapsed to one peak per consecutive run.

The reported scores are experimental model outputs, not calibrated physical earthquake probabilities or an operational warning system.
"""
    (output_dir / "README.md").write_text(content, encoding="utf-8")


def _write_stage_readme(
    output_dir: Path,
    *,
    stage: str,
    model_type: str,
    selected_record: dict[str, Any],
    details: dict[str, Any],
    graph_path: Path,
) -> None:
    metrics = details["holdout_metrics"]
    gate_passed = int(metrics["fp"]) <= 1 and float(metrics["recall"]) >= 0.50
    content = f"""# {stage} - {model_type}

This directory contains the automatically generated best-available `{stage}` output for `{model_type}`.

- Selected phase: `{selected_record.get('phase', stage.lower())}`
- Objective loss: `{float(metrics['objective_loss']):.6f}`
- Precision: `{float(metrics['precision']):.6f}`
- Recall: `{float(metrics['recall']):.6f}`
- F1: `{float(metrics['f1']):.6f}`
- False positives: `{int(metrics['fp'])}`
- False negatives: `{int(metrics['fn'])}`
- AUC: `{float(metrics['auc']):.6f}`
- Mean absolute event-peak error: `{float(metrics.get('event_peak_mae_weeks', float('nan'))):.3f}` weeks
- Maximum event-peak error: `{float(metrics.get('event_peak_max_error_weeks', float('nan'))):.3f}` weeks
- Event gate-hit rate within +/-1 week: `{float(metrics.get('event_gate_hit_plusminus_1week_rate', 0.0)):.3f}`
- Advisory quality gate: `{'PASS' if gate_passed else 'FAIL'}`
- Graph: `{graph_path.name}`

The advisory quality gate does not suppress this output. Research use only; the score is not a calibrated physical earthquake probability.
"""
    (output_dir / "README.md").write_text(content, encoding="utf-8")


def _gate_failure_text(metrics: dict[str, Any]) -> str:
    failures: list[str] = []
    if int(metrics.get("fp", 999)) > 1:
        failures.append(f"FP={int(metrics['fp'])} > 1")
    if float(metrics.get("recall", 0.0)) < 0.50:
        failures.append(f"Recall={float(metrics['recall']):.3f} < 0.500")
    return "; ".join(failures) if failures else "none"


def _write_quality_report(
    path: Path,
    *,
    level1_records: dict[str, list[dict[str, Any]]],
    level2_payloads: dict[str, dict[str, Any]],
    selected_details: dict[str, dict[str, Any]],
    ensemble_metrics: dict[str, Any] | None,
    weights: dict[str, float],
    gate_policy: str,
    decision_threshold: float,
) -> Path:
    created = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Forecast quality report",
        "",
        f"Generated UTC: `{created}`",
        f"Quality-gate policy: `{gate_policy}`",
        "",
        "## Gate definition and operational behavior",
        "",
        "The declared historical certification gate is `FP <= 1` and `Recall >= 0.50` on the frozen validation set.",
        "Validation uses the original chronological master slices around every held-out event; training background chunks are not reused.",
        "In `advisory` mode, failure is recorded here but does not block Level 1 outputs, Level 2 optimization,",
        "model forecasts, the ensemble, or the discrete decision gate.",
        f"The prospective digital threshold is `p >= {decision_threshold:.2f}`.",
        "",
        "## Level 1 best trials",
        "",
        "| Model | Trials | Objective | Precision | Recall | F1 | FP | FN | Peak MAE (w) | Gate | Failed criteria |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for model in MODELS:
        record = _best(level1_records[model])
        if record is None:
            lines.append(f"| {model} | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | FAIL | no successful trial |")
            continue
        values = {
            "precision": float(record.get("val_precision", 0.0)),
            "recall": float(record.get("val_recall", 0.0)),
            "f1": float(record.get("val_f1", 0.0)),
            "fp": int(record.get("val_fp", 0)),
            "fn": int(record.get("val_fn", 0)),
            "auc": float(record.get("val_auc", 0.5)),
        }
        passed = _quality_gate(record)
        lines.append(
            f"| {model} | {len(_successful(level1_records[model]))} | {float(record['objective_loss']):.6f} | "
            f"{values['precision']:.3f} | {values['recall']:.3f} | {values['f1']:.3f} | {values['fp']} | "
            f"{values['fn']} | {float(record.get('event_peak_mae_weeks', float('nan'))):.3f} | "
            f"{'PASS' if passed else 'FAIL'} | {_gate_failure_text(values)} |"
        )
    lines.extend([
        "",
        "## Level 2 selected trials",
        "",
        "Each row is the best successful Level 2 candidate for that model. It is retained even if it is not better than Level 1.",
        "",
        "| Model | Objective | Precision | Recall | F1 | FP | FN | Peak MAE (w) | Improved vs L1 | Gate | Failed criteria |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|---|",
    ])
    for model in MODELS:
        payload = level2_payloads.get(model, {})
        details = selected_details.get(model)
        if details is None:
            lines.append(f"| {model} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | FAIL | {payload.get('reason', 'no output')} |")
            continue
        metrics = details["holdout_metrics"]
        passed = int(metrics["fp"]) <= 1 and float(metrics["recall"]) >= 0.50
        lines.append(
            f"| {model} | {float(metrics['objective_loss']):.6f} | {float(metrics['precision']):.3f} | "
            f"{float(metrics['recall']):.3f} | {float(metrics['f1']):.3f} | {int(metrics['fp'])} | "
            f"{int(metrics['fn'])} | {float(metrics.get('event_peak_mae_weeks', float('nan'))):.3f} | "
            f"{'yes' if payload.get('phase2_improved_vs_level1') else 'no'} | {'PASS' if passed else 'FAIL'} | "
            f"{_gate_failure_text(metrics)} |"
        )
    lines.extend([
        "",
        "## Validation-weighted ensemble",
        "",
        "Weights use `(0.45*F1 + 0.25*precision + 0.20*recall + 0.10*AUC)^3 / ((1+FP)*(1+objective))`,",
        "then normalize to one. The cubic term deliberately gives more influence to stronger validation results.",
        "",
    ])
    for model, weight in weights.items():
        lines.append(f"- `{model}`: `{weight:.8f}`")
    if ensemble_metrics is not None:
        passed = int(ensemble_metrics["fp"]) <= 1 and float(ensemble_metrics["recall"]) >= 0.50
        lines.extend([
            "",
            f"Ensemble objective: `{float(ensemble_metrics['objective_loss']):.6f}`; precision: `{float(ensemble_metrics['precision']):.3f}`; "
            f"recall: `{float(ensemble_metrics['recall']):.3f}`; F1: `{float(ensemble_metrics['f1']):.3f}`; "
            f"FP: `{int(ensemble_metrics['fp'])}`; FN: `{int(ensemble_metrics['fn'])}`; AUC: `{float(ensemble_metrics['auc']):.3f}`.",
            f"Mean absolute event-peak error: `{float(ensemble_metrics.get('event_peak_mae_weeks', float('nan'))):.3f}` weeks; "
            f"maximum: `{float(ensemble_metrics.get('event_peak_max_error_weeks', float('nan'))):.3f}` weeks.",
            f"Certification result: `{'PASS' if passed else 'FAIL'}`. Failed criteria: `{_gate_failure_text(ensemble_metrics)}`.",
        ])
    lines.extend([
        "",
        "## Scientific limitation",
        "",
        "These are retrospective experimental associations and prospective model scores, not calibrated physical earthquake",
        "probabilities. Gate success or failure does not establish causal forecasting skill and this output must not be used",
        "as an operational public-warning system.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.device != "cpu":
        raise ValueError("This pipeline is intentionally CPU-only")
    configure_window_space(
        args.window_before_min,
        args.window_before_max,
        args.window_after_min,
        args.window_after_max,
    )
    torch.set_num_threads(max(1, int(args.cpu_threads)))
    torch.set_num_interop_threads(max(1, min(2, int(args.cpu_threads))))
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    output_dir = Path(args.output_dir).resolve()
    data_dir = output_dir / "01_data"
    level1_dir = output_dir / "02_level1"
    final_dir = output_dir / "04_final"
    report_dir = output_dir / "05_report"
    for directory in (data_dir, level1_dir, final_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    config = BinaryDataConfig(
        magnitude_threshold=args.magnitude_threshold,
        cutoff_utc=args.cutoff_utc,
        forecast_start=args.forecast_start,
        forecast_end=args.forecast_end,
        validation_event_count=args.validation_event_count,
        validation_weeks_before=args.validation_weeks_before,
        validation_weeks_after=args.validation_weeks_after,
    )
    input_paths = {
        "daily_source_master": Path(args.input_master).resolve(),
        "japan_catalog": Path(args.japan_catalog).resolve(),
        "world_catalog": Path(args.world_catalog).resolve(),
    }
    cached_master = data_dir / "clean_master_binary_7d.csv"
    cached_audit = data_dir / "dataset_audit.json"
    if cached_master.exists() and cached_audit.exists():
        dataset_summary = json.loads(cached_audit.read_text(encoding="utf-8"))
        expected_contract = {
            "magnitude_threshold": float(args.magnitude_threshold),
            "forecast_start": str(pd.Timestamp(args.forecast_start).date()),
            "forecast_end": str(pd.Timestamp(args.forecast_end).date()),
            "validation_weeks_before": int(args.validation_weeks_before),
            "validation_weeks_after": int(args.validation_weeks_after),
            "shift_weeks": int(args.shift_weeks),
        }
        mismatches = {
            key: (dataset_summary.get(key), value)
            for key, value in expected_contract.items()
            if dataset_summary.get(key) != value
        }
        if mismatches:
            raise ValueError(f"Cached clean-master contract mismatch: {mismatches}")
        clean = pd.read_csv(cached_master, low_memory=False)
        clean[DATE_COLUMN] = pd.to_datetime(clean[DATE_COLUMN], errors="raise")
        features = sorted(column for column in clean if column.startswith("packed_astro_container_"))
        LOGGER.info("Resuming from audited clean master: %s", cached_master)
    else:
        clean, features, dataset_summary = build_clean_binary_megathrust_master(
            input_paths["daily_source_master"],
            input_paths["japan_catalog"],
            input_paths["world_catalog"],
            data_dir,
            magnitude_threshold=args.magnitude_threshold,
            cutoff_utc=args.cutoff_utc,
            forecast_start=args.forecast_start,
            forecast_end=args.forecast_end,
            validation_weeks_before=args.validation_weeks_before,
            validation_weeks_after=args.validation_weeks_after,
            shift_weeks=args.shift_weeks,
        )
    _atomic_csv(clean, data_dir / "clean_master_binary_7d.csv")
    _atomic_csv(
        clean.loc[
            clean["is_japan_positive"].eq(1) | clean["is_world_hard_negative"].eq(1),
            [DATE_COLUMN, TARGET_COLUMN, "sample_role", "japan_max_magnitude", "foreign_max_magnitude", "japan_event_ids", "foreign_event_ids"],
        ],
        data_dir / "event_and_hard_negative_index.csv",
    )
    dataset_summary["input_sha256"] = {name: _sha256(path) for name, path in input_paths.items()}
    dataset_summary["input_paths"] = {name: str(path) for name, path in input_paths.items()}
    _atomic_json(dataset_summary, data_dir / "dataset_audit.json")
    historical = clean.loc[clean[TARGET_COLUMN].notna()].copy()
    held_out_events = (
        historical.loc[historical[TARGET_COLUMN].eq(1), DATE_COLUMN]
        .drop_duplicates()
        .sort_values()
        .tail(args.validation_event_count)
        .tolist()
    )
    validation_corridor_index = build_validation_corridor_index(
        historical,
        held_out_events,
        weeks_before=args.validation_weeks_before,
        weeks_after=args.validation_weeks_after,
    )
    _atomic_csv(validation_corridor_index, data_dir / "validation_corridor_index.csv")
    _write_readme(output_dir, args, dataset_summary)

    started = time.monotonic()
    optimization_budget = max(30.0, float(args.total_timeout_seconds) - float(args.finalization_reserve_seconds))
    level1_budget = optimization_budget * float(args.level1_fraction)
    level1_records: dict[str, list[dict[str, Any]]] = {}
    for model_type in MODELS:
        level1_records[model_type] = _run_level1_model(
            model_type,
            clean,
            features,
            level1_dir / f"study_{model_type}",
            timeout_seconds=level1_budget / len(MODELS),
            max_trials=args.n_trials_per_model,
            validation_event_count=args.validation_event_count,
            validation_weeks_before=args.validation_weeks_before,
            validation_weeks_after=args.validation_weeks_after,
            decision_threshold=args.decision_threshold,
            base_seed=args.seed + MODELS.index(model_type) * 10000,
            epochs_override=args.model_epochs,
        )

    level1_graphs: dict[str, str] = {}
    for model_type in MODELS:
        level1_record = _best(
            level1_records[model_type], gated=args.quality_gate_policy == "enforce"
        )
        if level1_record is None:
            continue
        stage_dir = level1_dir / f"study_{model_type}" / "best_output"
        validation, forecast, training_context, details = _finalize_model(
            model_type,
            level1_record,
            clean,
            features,
            stage_dir,
            config,
            args.decision_threshold,
            args.model_epochs,
        )
        graph = create_model_plot(
            validation,
            forecast,
            training_context,
            details["holdout_metrics"],
            stage_dir / f"level1_best_validation_forecast_{model_type}.png",
            model_name=model_type,
            stage_name="Level 1",
            threshold=args.decision_threshold,
            magnitude_threshold=args.magnitude_threshold,
            params=details["params"],
            validation_event_count=args.validation_event_count,
            validation_window_span=max(args.validation_weeks_before, args.validation_weeks_after),
        )
        _write_stage_readme(
            stage_dir,
            stage="Level 1",
            model_type=model_type,
            selected_record=level1_record,
            details=details,
            graph_path=graph,
        )
        level1_graphs[model_type] = str(graph)

    eligible = [
        model for model in MODELS
        if _best(level1_records[model], gated=args.quality_gate_policy == "enforce") is not None
    ]
    elapsed = time.monotonic() - started
    remaining = max(0.0, optimization_budget - elapsed)
    level2_payloads: dict[str, dict[str, Any]] = {}
    eligible_processed = 0
    for model_type in MODELS:
        eligible_left = max(1, len(eligible) - eligible_processed)
        timeout = remaining / eligible_left if model_type in eligible else 1.0
        _, payload = _run_level2_model(
            model_type,
            level1_records[model_type],
            clean,
            features,
            level1_dir / f"study_{model_type}" / "phase2_deep_meta_opt",
            timeout_seconds=timeout,
            max_trials=args.max_meta_trials,
            validation_event_count=args.validation_event_count,
            validation_weeks_before=args.validation_weeks_before,
            validation_weeks_after=args.validation_weeks_after,
            decision_threshold=args.decision_threshold,
            base_seed=args.seed + MODELS.index(model_type) * 10000,
            surrogate_epochs=args.surrogate_epochs,
            epochs_override=args.model_epochs,
            quality_gate_policy=args.quality_gate_policy,
        )
        level2_payloads[model_type] = payload
        if model_type in eligible:
            eligible_processed += 1
            elapsed = time.monotonic() - started
            remaining = max(0.0, optimization_budget - elapsed)

    selected: dict[str, dict[str, Any]] = {}
    for model_type in eligible:
        payload = level2_payloads[model_type]
        record = payload.get("selected_record") or _best(
            level1_records[model_type], gated=args.quality_gate_policy == "enforce"
        )
        if record is not None:
            selected[model_type] = record

    validation_frames: dict[str, pd.DataFrame] = {}
    forecast_frames: dict[str, pd.DataFrame] = {}
    selected_details: dict[str, dict[str, Any]] = {}
    training_frames: dict[str, pd.DataFrame] = {}
    level2_graphs: dict[str, str] = {}
    for model_type, record in selected.items():
        stage_dir = level1_dir / f"study_{model_type}" / "phase2_deep_meta_opt" / "best_output"
        validation, forecast, training_context, details = _finalize_model(
            model_type,
            record,
            clean,
            features,
            stage_dir,
            config,
            args.decision_threshold,
            args.model_epochs,
        )
        graph = create_model_plot(
            validation,
            forecast,
            training_context,
            details["holdout_metrics"],
            stage_dir / f"level2_best_validation_forecast_{model_type}.png",
            model_name=model_type,
            stage_name="Level 2",
            threshold=args.decision_threshold,
            magnitude_threshold=args.magnitude_threshold,
            params=details["params"],
            validation_event_count=args.validation_event_count,
            validation_window_span=max(args.validation_weeks_before, args.validation_weeks_after),
        )
        _write_stage_readme(
            stage_dir,
            stage="Level 2",
            model_type=model_type,
            selected_record=record,
            details=details,
            graph_path=graph,
        )
        validation_frames[model_type] = validation
        forecast_frames[model_type] = forecast
        selected_details[model_type] = details
        training_frames[model_type] = training_context
        level2_graphs[model_type] = str(graph)

    model_metrics: dict[str, dict[str, Any]] = {}
    for model_type in MODELS:
        if model_type in selected_details:
            model_metrics[model_type] = selected_details[model_type]["holdout_metrics"]
        else:
            best = _best(level1_records[model_type])
            if best:
                model_metrics[model_type] = {
                    "precision": best.get("val_precision", 0.0),
                    "recall": best.get("val_recall", 0.0),
                    "f1": best.get("val_f1", 0.0),
                    "fp": best.get("val_fp", 0),
                    "fn": best.get("val_fn", 0),
                    "auc": best.get("val_auc", 0.5),
                    "objective_loss": best.get("objective_loss", 999.0),
                }

    ensemble_metrics: dict[str, Any] | None = None
    ensemble_peak_frame = pd.DataFrame()
    certified = False
    if selected:
        weight_values = _weights({model: selected_details[model]["holdout_metrics"] for model in selected})
        validation_ensemble = _merge_validation(validation_frames, weight_values)
        ensemble_metric_object = binary_metrics(
            validation_ensemble["actual"], validation_ensemble["probability_ensemble"], args.decision_threshold
        )
        ensemble_metrics = ensemble_metric_object.to_dict()
        ensemble_peak_summary, ensemble_peak_frame = event_peak_diagnostics(
            validation_ensemble[DATE_COLUMN],
            validation_ensemble["probability_ensemble"],
            validation_corridor_index,
            args.decision_threshold,
        )
        ensemble_metrics["classification_objective_loss"] = float(ensemble_metric_object.objective_loss)
        ensemble_metrics.update(ensemble_peak_summary)
        ensemble_metrics["peak_distance_penalty"] = 0.0
        ensemble_metrics["peak_miss_penalty"] = 0.0
        ensemble_metrics["objective_loss"] = float(ensemble_metric_object.objective_loss)
        certified = ensemble_metric_object.fp <= 1 and ensemble_metric_object.recall >= 0.50
        forecast_ensemble = _merge_forecast(forecast_frames, weight_values)
        forecast_ensemble["above_confidence_gate"] = (
            forecast_ensemble["ensemble_probability"] >= args.decision_threshold
        ).astype(np.int8)
        forecast_ensemble["event_signal"] = collapse_gate_runs(
            forecast_ensemble["ensemble_probability"], args.decision_threshold
        )
        forecast_ensemble["validation_gate_certified"] = int(certified)
    else:
        weight_values = {}
        validation_ensemble = pd.DataFrame()
        forecast_ensemble = clean.loc[
            clean[DATE_COLUMN].between(pd.Timestamp(config.forecast_start), pd.Timestamp(config.forecast_end)),
            [DATE_COLUMN],
        ].copy()
        forecast_ensemble["ensemble_probability"] = np.nan
        forecast_ensemble["above_confidence_gate"] = 0
        forecast_ensemble["event_signal"] = 0
        forecast_ensemble["validation_gate_certified"] = 0

    _atomic_csv(validation_ensemble, final_dir / "ensemble_validation.csv")
    _atomic_csv(ensemble_peak_frame, final_dir / "ensemble_event_peak_diagnostics.csv")
    _atomic_csv(forecast_ensemble, final_dir / "ensemble_forecast_aug_dec2026.csv")
    _atomic_json(
        {
            "weights": weight_values,
            "metrics": ensemble_metrics,
            "certified": certified,
            "quality_gate_policy": args.quality_gate_policy,
            "quality_gate": {"max_false_positives": 1, "min_recall": 0.50},
            "decision_threshold": args.decision_threshold,
            "selected_models": list(selected),
            "validation_contract": {
                "event_count": args.validation_event_count,
                "weeks_before": args.validation_weeks_before,
                "weeks_after": args.validation_weeks_after,
                "source": "original chronological master slices",
            },
            "training_sampling": {
                "window_before_range": [args.window_before_min, args.window_before_max],
                "window_after_range": [args.window_after_min, args.window_after_max],
                "background": "contiguous inter-event chunks selected with pi millesimi and trial seed",
                "pi_digit_triplets_millesimi": list(PI_DIGIT_TRIPLETS),
            },
            "weight_formula": (
                "(0.45*F1 + 0.25*precision + 0.20*recall + 0.10*AUC)^3 "
                "/ ((1+FP)*(1+objective_loss)), normalized"
            ),
        },
        final_dir / "ensemble_manifest.json",
    )

    quality_report = _write_quality_report(
        report_dir / "QUALITY_GATE_REPORT.md",
        level1_records=level1_records,
        level2_payloads=level2_payloads,
        selected_details=selected_details,
        ensemble_metrics=ensemble_metrics,
        weights=weight_values,
        gate_policy=args.quality_gate_policy,
        decision_threshold=args.decision_threshold,
    )
    quality_audit_path = report_dir / "quality_gate_audit.json"
    quality_audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "objective_contract": (
            "FocalLoss + 3*(1-F1) + 3.5*FP_Rate + 2.5*FN_Rate + 0.5*Depression_MAE"
        ),
        "gate_contract": {"max_false_positives": 1, "min_recall": 0.50},
        "validation_contract": {
            "event_count": 2,
            "event_weeks": dataset_summary.get("validation_event_weeks", []),
            "weeks_before": args.validation_weeks_before,
            "weeks_after": args.validation_weeks_after,
            "expected_rows": 54,
            "training_hard_end": dataset_summary.get("training_hard_end"),
        },
        "level1": {model: _best(records) for model, records in level1_records.items()},
        "level2": {
            model: payload.get("selected_record") for model, payload in level2_payloads.items()
        },
        "ensemble": ensemble_metrics,
        "ensemble_event_peak_diagnostics": ensemble_peak_frame.to_dict(orient="records"),
        "passed": bool(certified),
        "outputs_generated_even_on_failure": True,
    }
    _atomic_json(quality_audit, quality_audit_path)

    any_model_gate_pass = any(
        bool(details.get("quality_gate_passed")) for details in selected_details.values()
    )
    if not certified and not any_model_gate_pass:
        improvement_plan = report_dir / "QUALITY_GATE_IMPROVEMENT_PLAN.md"
        improvement_plan.write_text(
            "# Quality-gate improvement plan\n\n"
            "All selected models and the ensemble missed at least one declared validation gate. "
            "The current forecast is still emitted as best-available research output, without certification.\n\n"
            "1. Freeze a second, untouched chronological test pair before any further search.\n"
            "2. Expand only the pre-2003 catalogue and astronomy coverage; do not reuse the two selection events for tuning.\n"
            "3. Run nested walk-forward ablations of feature families before increasing network capacity.\n"
            "4. Calibrate the digital threshold on training-only out-of-fold predictions and then freeze it.\n"
            "5. Compare event-centred precision/recall with quiet-period false-alarm duration, not only row-wise scores.\n"
            "6. Reject improvements that increase training/validation divergence or shift either predicted event peak outside the certified timing tolerance.\n",
            encoding="utf-8",
        )

    report_png, report_pdf = create_binary_report(
        validation_ensemble,
        forecast_ensemble,
        training_frames[max(weight_values, key=weight_values.get)] if weight_values else pd.DataFrame(),
        model_metrics,
        ensemble_metrics,
        dataset_summary,
        list(selected),
        report_dir / "japan_megathrust_binary_forecast.png",
        report_dir / "japan_megathrust_binary_forecast.pdf",
        threshold=args.decision_threshold,
        certified=certified,
    )
    manifest = {
        "pipeline": "DLVS-Wave v2.0 Japan-wide binary megathrust two-level pipeline",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "device": "cpu",
        "cpu_threads": args.cpu_threads,
        "elapsed_seconds": time.monotonic() - started,
        "configuration": vars(args),
        "dataset": dataset_summary,
        "level1": {
            model: {
                "successful_trials": len(_successful(records)),
                "best_overall": _best(records),
                "best_gate_passing": _best(records, gated=True),
            }
            for model, records in level1_records.items()
        },
        "level2": level2_payloads,
        "ensemble": {
            "selected_models": list(selected),
            "weights": weight_values,
            "metrics": ensemble_metrics,
            "certified": certified,
            "discrete_signal_count": int(forecast_ensemble["event_signal"].sum()),
        },
        "outputs": {
            "forecast_csv": str(final_dir / "ensemble_forecast_aug_dec2026.csv"),
            "validation_csv": str(final_dir / "ensemble_validation.csv"),
            "validation_corridor_index_csv": str(data_dir / "validation_corridor_index.csv"),
            "report_png": str(report_png),
            "report_pdf": str(report_pdf),
            "quality_report_md": str(quality_report),
            "quality_gate_audit_json": str(quality_audit_path),
            "level1_graphs": level1_graphs,
            "level2_graphs": level2_graphs,
        },
        "scientific_limit": (
            "Experimental association study only. Scores are not calibrated physical earthquake probabilities "
            "and are not suitable for operational warnings or safety decisions."
        ),
    }
    _atomic_json(manifest, output_dir / "run_manifest.json")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CPU-only two-level binary Japan megathrust research pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-master", required=True)
    parser.add_argument("--japan-catalog", required=True)
    parser.add_argument("--world-catalog", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--magnitude-threshold", type=float, default=7.7)
    parser.add_argument("--cutoff-utc", default="2026-07-31T23:59:59Z")
    parser.add_argument("--forecast-start", default="2026-08-01")
    parser.add_argument("--forecast-end", default="2026-12-31")
    parser.add_argument("--shift-weeks", type=int, default=13)
    parser.add_argument("--validation-event-count", type=int, default=2)
    parser.add_argument("--validation-weeks-before", type=int, default=13)
    parser.add_argument("--validation-weeks-after", type=int, default=13)
    parser.add_argument("--window-before-min", type=int, default=2)
    parser.add_argument("--window-before-max", type=int, default=7)
    parser.add_argument("--window-after-min", type=int, default=2)
    parser.add_argument("--window-after-max", type=int, default=7)
    parser.add_argument("--decision-threshold", type=float, default=0.70)
    parser.add_argument(
        "--quality-gate-policy",
        choices=["advisory", "enforce"],
        default="advisory",
        help="Advisory reports quality failures without suppressing optimization or forecasts",
    )
    parser.add_argument("--total-timeout-seconds", type=float, default=10800.0)
    parser.add_argument("--finalization-reserve-seconds", type=float, default=600.0)
    parser.add_argument("--level1-fraction", type=float, default=0.60)
    parser.add_argument("--n-trials-per-model", type=int, default=180)
    parser.add_argument("--max-meta-trials", type=int, default=80)
    parser.add_argument("--surrogate-epochs", type=int, default=120)
    parser.add_argument("--model-epochs", type=int, default=None, help="Override all trial epochs for smoke tests")
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--cpu-threads", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--device", choices=["cpu"], default="cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = build_parser().parse_args(argv)
    if not 0.0 < args.decision_threshold < 1.0:
        raise ValueError("decision-threshold must be in (0, 1)")
    if not 0.0 < args.level1_fraction < 1.0:
        raise ValueError("level1-fraction must be in (0, 1)")
    if args.validation_event_count != 2:
        raise ValueError("This run contract requires exactly two validation events")
    if args.validation_weeks_before < 1 or args.validation_weeks_after < 1:
        raise ValueError("validation weekly index margins must both be positive")
    manifest = run(args)
    print(json.dumps({"output_dir": args.output_dir, "ensemble": manifest["ensemble"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

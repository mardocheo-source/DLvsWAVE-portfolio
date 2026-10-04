"""Phase 2 deep-surrogate meta-optimization engine.

The engine learns from successful Phase 1 trials, proposes legal candidates in
the original search space, evaluates every candidate through the same
pretreatment/model path, and persists every attempt before continuing.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from src.meta_optimizer.surrogate import (
    DeepSurrogateModel,
    InverseConditionalGenerator,
    ParameterEncoder,
    compute_expected_improvement,
)
from src.models.base import BaseForecastingModel, ModelMetrics
from src.models.deep_learning import DeepLearningForecastingModel
from src.models.kan import KANForecastingModel
from src.models.lcs import LCSForecastingModel
from src.pretreatment import MasterPretreatmentEngine, PretreatmentConfig, PretreatmentResult

logger = logging.getLogger("dlvs_wave.meta_optimizer")

TARGET_COLUMNS = ("objective_loss", "val_mse", "val_f1_score", "val_depression_mae")
FAILED_OBJECTIVE = 999.0


def _json_safe(value: Any) -> Any:
    """Convert numpy/pandas values to strict JSON-compatible Python values."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if pd.isna(value):
        return None
    return value


class DeepMetaOptimizer:
    """Active Phase 2 optimizer shared by KAN, deep-learning, and LCS studies."""

    def __init__(
        self,
        input_trials_csv: Path | str,
        master_df: pd.DataFrame | Path | str,
        model_type: str,
        target_col: str = "seis_core_magnitude",
        min_mag_threshold: float = 6.9,
        eval_events: int = 3,
        timeout_seconds: float = 600.0,
        output_dir: Path | str | None = None,
        device: str = "cpu",
        retrain_frequency: int = 5,
        seed: int = 42,
        max_meta_trials: int | None = None,
        surrogate_epochs: int = 100,
        retrain_epochs: int = 40,
        candidate_batch_size: int = 4,
        model_epochs: int | None = None,
        resume: bool = True,
    ) -> None:
        self.input_trials_csv = Path(input_trials_csv)
        normalized_model = model_type.lower()
        self.model_type = "deep_learning" if normalized_model == "deep" else normalized_model
        self.target_col = target_col
        self.min_mag_threshold = float(min_mag_threshold)
        self.eval_events = int(eval_events)
        self.timeout_seconds = float(timeout_seconds)
        self.requested_device = device.lower()
        self.retrain_frequency = int(retrain_frequency)
        self.seed = int(seed)
        self.max_meta_trials = max_meta_trials
        self.surrogate_epochs = int(surrogate_epochs)
        self.retrain_epochs = int(retrain_epochs)
        self.candidate_batch_size = int(candidate_batch_size)
        self.model_epochs = model_epochs
        self.resume = bool(resume)

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.eval_events < 1:
            raise ValueError("eval_events must be at least 1")
        if self.retrain_frequency < 1 or self.candidate_batch_size < 1:
            raise ValueError("retrain_frequency and candidate_batch_size must be at least 1")
        if self.max_meta_trials is not None and self.max_meta_trials < 1:
            raise ValueError("max_meta_trials must be at least 1")
        if self.surrogate_epochs < 1 or self.retrain_epochs < 1:
            raise ValueError("surrogate training epochs must be at least 1")

        if isinstance(master_df, (str, Path)):
            master_path = Path(master_df)
            if not master_path.exists():
                raise FileNotFoundError(f"Master CSV not found: {master_path}")
            self.master_df = pd.read_csv(master_path, low_memory=False)
        else:
            self.master_df = master_df.copy()
        if self.target_col not in self.master_df.columns:
            raise ValueError(f"Target column '{self.target_col}' is absent from the master dataset")

        self.output_dir = Path(output_dir) if output_dir else self.input_trials_csv.parent / "phase2_deep_meta_opt"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.meta_csv_path = self.output_dir / f"meta_trials_{self.model_type}.csv"

        self.encoder = ParameterEncoder(self.model_type)
        self.torch_device, self.actual_device = self._resolve_device(self.requested_device)
        self.surrogate = DeepSurrogateModel(self.encoder.dim, hidden_dim=64, num_blocks=2).to(self.torch_device)
        self.generator = InverseConditionalGenerator(target_dim=4, param_dim=self.encoder.dim, hidden_dim=64).to(
            self.torch_device
        )

        self.phase1_records: list[dict[str, Any]] = []
        self.meta_records: list[dict[str, Any]] = []
        self.phase1_best_loss = float("inf")
        self.phase1_best_params: dict[str, Any] = {}
        self.phase1_best_record: dict[str, Any] = {}
        self.phase2_best_loss = float("inf")
        self.phase2_best_params: dict[str, Any] = {}
        self.phase2_best_metrics: dict[str, Any] | None = None
        self.phase2_best_validation: pd.DataFrame | None = None
        self._target_mean = np.zeros(4, dtype=np.float32)
        self._target_std = np.ones(4, dtype=np.float32)
        self._rng = np.random.default_rng(self.seed)

        self._seed_everything(self.seed)
        self._load_phase1_trials()
        if self.resume:
            self._load_existing_meta_trials()
        self._refresh_seen_keys()

    @staticmethod
    def _resolve_device(requested: str) -> tuple[torch.device, str]:
        """Resolve requested hardware without touching unavailable accelerators."""
        if requested == "cuda" and torch.cuda.is_available():
            return torch.device("cuda"), "cuda"
        if requested == "xpu" and hasattr(torch, "xpu") and torch.xpu.is_available():
            return torch.device("xpu"), "xpu"
        if requested not in {"cpu", "cuda", "xpu"}:
            raise ValueError("device must be one of: cpu, cuda, xpu")
        if requested != "cpu":
            logger.warning("Requested device '%s' is unavailable; using CPU", requested)
        return torch.device("cpu"), "cpu"

    @staticmethod
    def _seed_everything(seed: int) -> None:
        np.random.seed(seed)
        torch.manual_seed(seed)

    def _params_from_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self.encoder.decode(self.encoder.encode(record))

    def _load_phase1_trials(self) -> None:
        if not self.input_trials_csv.exists():
            raise FileNotFoundError(f"Trials CSV not found: {self.input_trials_csv}")
        frame = pd.read_csv(self.input_trials_csv)
        required = {"objective_loss", "val_mse", "val_f1_score", "val_depression_mae"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"Phase 1 CSV lacks required columns: {', '.join(missing)}")
        if "train_start_date" not in frame.columns and "train_start_year" not in frame.columns:
            raise ValueError("Phase 1 CSV requires train_start_date or train_start_year")
        missing_params = [name for name in self.encoder.names if name != "train_start_year" and name not in frame.columns]
        if missing_params:
            raise ValueError(f"Phase 1 CSV lacks search parameters: {', '.join(missing_params)}")

        numeric = frame[list(required)].apply(pd.to_numeric, errors="coerce")
        valid_mask = np.isfinite(numeric).all(axis=1) & (numeric["objective_loss"] < 500.0)
        valid = frame.loc[valid_mask].copy()
        if len(valid) < 5:
            raise ValueError(f"At least 5 successful Phase 1 trials are required; found {len(valid)}")
        self.phase1_records = valid.to_dict(orient="records")
        best_index = pd.to_numeric(valid["objective_loss"]).idxmin()
        self.phase1_best_record = valid.loc[best_index].to_dict()
        self.phase1_best_loss = float(self.phase1_best_record["objective_loss"])
        self.phase1_best_params = self._params_from_record(self.phase1_best_record)
        logger.info(
            "Loaded %d successful Phase 1 %s trials; best objective %.6f",
            len(valid),
            self.model_type,
            self.phase1_best_loss,
        )

    def _load_existing_meta_trials(self) -> None:
        if not self.meta_csv_path.exists():
            return
        frame = pd.read_csv(self.meta_csv_path)
        self.meta_records = frame.where(pd.notna(frame), None).to_dict(orient="records")
        successful = self._successful_meta_records()
        if successful:
            best = min(successful, key=lambda row: float(row["objective_loss"]))
            self.phase2_best_loss = float(best["objective_loss"])
            self.phase2_best_params = self._params_from_record(best)
            self.phase2_best_metrics = self._validation_metrics_from_record(best)
        logger.info(
            "Resumed %d Phase 2 attempts (%d successful) from %s",
            len(self.meta_records),
            len(successful),
            self.meta_csv_path,
        )

    def _successful_meta_records(self) -> list[dict[str, Any]]:
        successful: list[dict[str, Any]] = []
        for record in self.meta_records:
            try:
                loss = float(record.get("objective_loss", FAILED_OBJECTIVE))
            except (TypeError, ValueError):
                continue
            if record.get("status", "success") == "success" and math.isfinite(loss) and loss < 500:
                successful.append(record)
        return successful

    def _training_records(self) -> list[dict[str, Any]]:
        return self.phase1_records + self._successful_meta_records()

    def _refresh_seen_keys(self) -> None:
        self._seen_keys = {self.encoder.canonical_key(record) for record in self._training_records()}
        for record in self.meta_records:
            try:
                self._seen_keys.add(self.encoder.canonical_key(record))
            except (KeyError, TypeError, ValueError):
                continue

    def _build_tensors(self) -> tuple[torch.Tensor, torch.Tensor]:
        records = self._training_records()
        encoded = np.stack([self.encoder.encode(record) for record in records]).astype(np.float32)
        targets = np.asarray(
            [
                [
                    float(record["objective_loss"]),
                    float(record.get("val_mse", record.get("mse"))),
                    float(record.get("val_f1_score", record.get("f1_score"))),
                    float(record.get("val_depression_mae", record.get("depression_mae"))),
                ]
                for record in records
            ],
            dtype=np.float32,
        )
        self._target_mean = targets.mean(axis=0)
        self._target_std = targets.std(axis=0)
        self._target_std[self._target_std < 1e-6] = 1.0
        normalized = (targets - self._target_mean) / self._target_std
        return (
            torch.as_tensor(encoded, dtype=torch.float32, device=self.torch_device),
            torch.as_tensor(normalized, dtype=torch.float32, device=self.torch_device),
        )

    def _train_surrogate(self, epochs: int) -> None:
        features, targets = self._build_tensors()
        optimizer = optim.AdamW(
            list(self.surrogate.parameters()) + list(self.generator.parameters()), lr=3e-3, weight_decay=1e-4
        )
        self.surrogate.train()
        self.generator.train()
        zero_noise = torch.zeros(
            len(features), self.generator.latent_noise_dim, dtype=features.dtype, device=self.torch_device
        )
        for _ in range(epochs):
            optimizer.zero_grad(set_to_none=True)
            surrogate_loss = nn.functional.smooth_l1_loss(self.surrogate.stacked(features), targets)
            best_mask = targets[:, 0] <= torch.quantile(targets[:, 0], 0.35)
            generated = self.generator(targets[best_mask], zero_noise[best_mask])
            generator_loss = nn.functional.mse_loss(generated, features[best_mask])
            (surrogate_loss + 0.5 * generator_loss).backward()
            optimizer.step()

    def _combined_best(self) -> tuple[float, dict[str, Any]]:
        if self.phase2_best_loss < self.phase1_best_loss:
            return self.phase2_best_loss, self.phase2_best_params
        return self.phase1_best_loss, self.phase1_best_params

    def _propose_candidates(self, n_candidates: int) -> list[dict[str, Any]]:
        """Mix conditional generation, differentiable EI, and local exploration."""
        proposals: list[dict[str, Any]] = []
        local_keys: set[tuple[Any, ...]] = set()
        self.surrogate.eval()
        self.generator.eval()
        best_loss, best_params = self._combined_best()

        ideal_raw = np.asarray([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
        ideal_scaled = (ideal_raw - self._target_mean) / self._target_std
        generator_count = max(1, n_candidates // 2)
        target = torch.as_tensor(ideal_scaled, device=self.torch_device).unsqueeze(0).repeat(generator_count, 1)
        with torch.no_grad():
            generated_vectors = self.generator(target).cpu().numpy()

        raw_proposals: list[tuple[np.ndarray, str]] = [(vector, "conditional_generator") for vector in generated_vectors]

        best_vector = self.encoder.encode(best_params)
        latent = nn.Parameter(torch.as_tensor(best_vector, dtype=torch.float32, device=self.torch_device))
        latent_optimizer = optim.Adam([latent], lr=0.04)
        scaled_best_loss = (best_loss - float(self._target_mean[0])) / float(self._target_std[0])
        for _ in range(35):
            latent_optimizer.zero_grad(set_to_none=True)
            clipped = latent.clamp(0.0, 1.0).unsqueeze(0)
            mean, std = self.surrogate.predict_with_uncertainty(
                clipped, n_samples=12, differentiable=True
            )
            acquisition = compute_expected_improvement(mean, std, scaled_best_loss)
            (-acquisition.mean()).backward()
            latent_optimizer.step()
        raw_proposals.append((latent.detach().clamp(0.0, 1.0).cpu().numpy(), "expected_improvement"))

        attempts = 0
        while len(raw_proposals) < n_candidates * 4 and attempts < n_candidates * 12:
            scale = 0.08 if attempts < n_candidates * 4 else 0.20
            vector = np.clip(best_vector + self._rng.normal(0.0, scale, self.encoder.dim), 0.0, 1.0)
            raw_proposals.append((vector, "local_jitter"))
            attempts += 1

        for vector, source in raw_proposals:
            params = self.encoder.decode(vector)
            key = self.encoder.canonical_key(params)
            if key in self._seen_keys or key in local_keys:
                continue
            params["proposal_method"] = source
            proposals.append(params)
            local_keys.add(key)
            if len(proposals) >= n_candidates:
                break

        random_attempts = 0
        while len(proposals) < n_candidates and random_attempts < 200:
            params = self.encoder.decode(self._rng.random(self.encoder.dim))
            key = self.encoder.canonical_key(params)
            random_attempts += 1
            if key in self._seen_keys or key in local_keys:
                continue
            params["proposal_method"] = "random_fallback"
            proposals.append(params)
            local_keys.add(key)
        return proposals

    def _make_model(self, params: dict[str, Any]) -> tuple[BaseForecastingModel, int]:
        if self.model_type == "kan":
            model: BaseForecastingModel = KANForecastingModel(
                grid_size=int(params["grid_size"]),
                spline_order=int(params["spline_order"]),
                learning_rate=float(params["learning_rate"]),
                device=self.actual_device,
            )
            default_epochs = 50
        elif self.model_type == "deep_learning":
            model = DeepLearningForecastingModel(
                hidden_dim=int(params["hidden_dim"]),
                num_layers=int(params["num_layers"]),
                dropout=float(params["dropout"]),
                learning_rate=float(params["learning_rate"]),
                device=self.actual_device,
            )
            default_epochs = 60
        else:
            model = LCSForecastingModel(
                population_size=int(params["population_size"]),
                learning_rate=float(params["learning_rate"]),
                crossover_rate=float(params["crossover_rate"]),
                mutation_rate=float(params["mutation_rate"]),
            )
            default_epochs = 30
        return model, self.model_epochs if self.model_epochs is not None else default_epochs

    def _fit_and_evaluate(
        self, params: dict[str, Any], trial_number: int
    ) -> tuple[ModelMetrics, ModelMetrics, pd.DataFrame, PretreatmentResult, BaseForecastingModel]:
        """Run one real candidate; isolated as a test seam for fast lifecycle tests."""
        config = PretreatmentConfig(
            mode="energetic",
            target_col=self.target_col,
            train_start_date=str(params["train_start_date"]),
            min_magnitude_threshold=self.min_mag_threshold,
            window_before=int(params["window_before"]),
            window_after=int(params["window_after"]),
            background_sample_ratio=float(params["background_sample_ratio"]),
            seed=self.seed + trial_number,
            eval_min_events=self.eval_events,
            eval_max_events=self.eval_events,
            auto_balance_dates=True,
            eval_window_mode="corridors",
        )
        result = MasterPretreatmentEngine(config).process(
            self.master_df, study_name=f"meta_{self.model_type}_{trial_number}"
        )
        if len(result.train_df) < 5 or len(result.eval_df) < 5 or not result.feature_cols:
            raise ValueError("Pretreatment produced fewer than 5 train/eval rows or no numeric features")

        self._seed_everything(self.seed + trial_number)
        model, epochs = self._make_model(params)
        train_x = result.train_df[result.feature_cols]
        train_y = result.train_df[self.target_col]
        model.fit(
            train_x,
            train_y,
            feature_names=result.feature_cols,
            target_name=self.target_col,
            epochs=epochs,
        )
        train_metrics, _ = model.evaluate(train_x, train_y)
        eval_x = result.eval_df[result.feature_cols]
        eval_y = result.eval_df[self.target_col]
        validation_metrics, comparison = model.evaluate(eval_x, eval_y)
        return train_metrics, validation_metrics, comparison, result, model

    @staticmethod
    def _metric_fields(prefix: str, metrics: ModelMetrics) -> dict[str, Any]:
        fields = metrics.to_dict()
        return {f"{prefix}_{name}": value for name, value in fields.items()}

    @staticmethod
    def _validation_metrics_from_record(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key.removeprefix("val_"): value
            for key, value in record.items()
            if key.startswith("val_") and value is not None
        }

    def _persist_meta_records(self) -> None:
        if not self.meta_records:
            return
        temporary = self.meta_csv_path.with_suffix(self.meta_csv_path.suffix + ".tmp")
        pd.DataFrame(self.meta_records).to_csv(temporary, index=False)
        os.replace(temporary, self.meta_csv_path)

    def _evaluate_candidate(self, params: dict[str, Any], iteration: int, trial_number: int) -> float:
        started = time.time()
        proposal_method = str(params.get("proposal_method", "unknown"))
        clean_params = {key: value for key, value in params.items() if key != "proposal_method"}
        record: dict[str, Any] = {
            "meta_trial_number": trial_number,
            "meta_iteration": iteration,
            "status": "failed",
            "proposal_method": proposal_method,
            "objective_loss": FAILED_OBJECTIVE,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            **clean_params,
        }
        try:
            train_metrics, val_metrics, comparison, result, _model = self._fit_and_evaluate(
                clean_params, trial_number
            )
            objective = (
                0.5 * val_metrics.mse
                + 4.0 * (1.0 - val_metrics.f1_score)
                + 0.5 * val_metrics.depression_mae
            )
            if not math.isfinite(objective):
                raise ValueError("Candidate produced a non-finite objective")
            record.update(
                {
                    "status": "success",
                    "objective_loss": float(objective),
                    "train_samples": len(result.train_df),
                    "eval_samples": len(result.eval_df),
                    "eval_major_events": result.eval_major_events_count,
                    **self._metric_fields("train", train_metrics),
                    **self._metric_fields("val", val_metrics),
                }
            )
            if objective < self.phase2_best_loss:
                self.phase2_best_loss = float(objective)
                self.phase2_best_params = clean_params.copy()
                self.phase2_best_metrics = val_metrics.to_dict()
                date_col = str(result.metadata.get("date_col", "date"))
                if date_col not in result.eval_df.columns:
                    date_col = result.eval_df.columns[0]
                validation = pd.DataFrame(
                    {
                        "date": result.eval_df[date_col].values,
                        "actual": comparison["actual"].values,
                        f"predicted_{self.target_col}": comparison["predicted"].values,
                        "error": comparison["error"].values,
                        "abs_error": comparison["abs_error"].values,
                    }
                )
                self.phase2_best_validation = validation
                self._atomic_csv(
                    validation, self.output_dir / f"meta_best_validation_{self.model_type}.csv"
                )
                logger.info(
                    "New Phase 2 best trial %d: objective %.6f, validation F1 %.3f",
                    trial_number,
                    objective,
                    val_metrics.f1_score,
                )
        except Exception as exc:  # Persist failures: long searches must remain auditable.
            record["error"] = f"{type(exc).__name__}: {exc}"[:1000]
            objective = FAILED_OBJECTIVE
            logger.warning("Phase 2 trial %d failed: %s", trial_number, record["error"])
        finally:
            record["elapsed_seconds"] = time.time() - started
            self.meta_records.append(record)
            self._seen_keys.add(self.encoder.canonical_key(clean_params))
            self._persist_meta_records()
        return float(objective)

    @staticmethod
    def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        frame.to_csv(temporary, index=False)
        os.replace(temporary, path)

    @staticmethod
    def _atomic_json(payload: dict[str, Any], path: Path) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(payload), handle, indent=2, allow_nan=False)
        os.replace(temporary, path)

    def _next_trial_number(self) -> int:
        existing: list[int] = []
        for record in self.meta_records:
            try:
                existing.append(int(record["meta_trial_number"]))
            except (KeyError, TypeError, ValueError):
                continue
        return max(existing, default=-1) + 1

    def _comparison_payload(self, elapsed: float) -> dict[str, Any]:
        phase2_available = math.isfinite(self.phase2_best_loss)
        overall_loss, overall_params = self._combined_best()
        phase1_metrics = self._validation_metrics_from_record(self.phase1_best_record)
        return {
            "model_type": self.model_type,
            "phase1": {
                "successful_trials": len(self.phase1_records),
                "best_objective_loss": self.phase1_best_loss,
                "best_params": self.phase1_best_params,
                "best_validation_metrics": phase1_metrics,
            },
            "phase2": {
                "attempted_trials": len(self.meta_records),
                "successful_trials": len(self._successful_meta_records()),
                "best_objective_loss": self.phase2_best_loss if phase2_available else None,
                "best_params": self.phase2_best_params if phase2_available else None,
                "best_validation_metrics": self.phase2_best_metrics,
                "improvement_vs_phase1": self.phase1_best_loss - self.phase2_best_loss if phase2_available else None,
            },
            "overall_winner": "phase2" if phase2_available and self.phase2_best_loss < self.phase1_best_loss else "phase1",
            "overall_best_objective_loss": overall_loss,
            "overall_best_params": overall_params,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            "elapsed_seconds": elapsed,
            "validation_scope": {
                "kind": "selection_validation_reused_from_phase1_protocol",
                "independent_holdout": False,
                "warning": (
                    "Phase 2 selects candidates on the same validation protocol used to rank Phase 1. "
                    "Its delta is optimization evidence, not an unbiased generalization estimate; use a later untouched time block for confirmation."
                ),
            },
        }

    def _persist_final_artifacts(self, elapsed: float) -> dict[str, Any]:
        comparison = self._comparison_payload(elapsed)
        self._atomic_json(
            self.phase2_best_params if math.isfinite(self.phase2_best_loss) else {},
            self.output_dir / f"meta_best_params_{self.model_type}.json",
        )
        self._atomic_json(
            self.phase2_best_metrics or {},
            self.output_dir / f"meta_best_metrics_{self.model_type}.json",
        )
        self._atomic_json(comparison, self.output_dir / f"phase2_comparison_{self.model_type}.json")

        p2_loss = comparison["phase2"]["best_objective_loss"]
        p2_loss_text = f"{p2_loss:.6f}" if p2_loss is not None else "N/A"
        improvement = comparison["phase2"]["improvement_vs_phase1"]
        improvement_text = f"{improvement:+.6f}" if improvement is not None else "N/A"
        report = (
            f"# Phase 2 Deep Meta-Optimization — {self.model_type.upper()}\n\n"
            f"- Phase 1: {len(self.phase1_records)} successful trials; best objective `{self.phase1_best_loss:.6f}`.\n"
            f"- Phase 2: {len(self.meta_records)} attempts, {len(self._successful_meta_records())} successful; "
            f"best objective `{p2_loss_text}`.\n"
            f"- Improvement (Phase 1 minus Phase 2): `{improvement_text}`.\n"
            f"- Overall winner: **{comparison['overall_winner']}**.\n"
            f"- Compute device: requested `{self.requested_device}`, actual `{self.actual_device}`.\n\n"
            "## Validation limitation\n\n"
            f"{comparison['validation_scope']['warning']}\n"
        )
        report_path = self.output_dir / f"phase2_comparison_{self.model_type}.md"
        temporary = report_path.with_suffix(report_path.suffix + ".tmp")
        temporary.write_text(report, encoding="utf-8")
        os.replace(temporary, report_path)
        return comparison

    def run(self) -> dict[str, Any]:
        """Execute active search until timeout or the requested total trial cap."""
        started = time.time()
        logger.info(
            "Starting Phase 2 %s search on %s (timeout %.1fs, existing attempts %d)",
            self.model_type,
            self.actual_device,
            self.timeout_seconds,
            len(self.meta_records),
        )
        self._train_surrogate(self.surrogate_epochs)
        next_trial = self._next_trial_number()
        successful_since_retrain = 0
        iteration = 0

        while time.time() - started < self.timeout_seconds:
            if self.max_meta_trials is not None and len(self.meta_records) >= self.max_meta_trials:
                break
            iteration += 1
            candidates = self._propose_candidates(self.candidate_batch_size)
            if not candidates:
                logger.warning("No unseen legal candidate could be generated; stopping search")
                break
            for candidate in candidates:
                if time.time() - started >= self.timeout_seconds:
                    break
                if self.max_meta_trials is not None and len(self.meta_records) >= self.max_meta_trials:
                    break
                objective = self._evaluate_candidate(candidate, iteration, next_trial)
                next_trial += 1
                if objective < 500:
                    successful_since_retrain += 1
                if successful_since_retrain >= self.retrain_frequency:
                    self._train_surrogate(self.retrain_epochs)
                    successful_since_retrain = 0

        elapsed = time.time() - started
        comparison = self._persist_final_artifacts(elapsed)
        logger.info(
            "Phase 2 finished in %.1fs: %d attempts, %d successful, winner %s",
            elapsed,
            len(self.meta_records),
            len(self._successful_meta_records()),
            comparison["overall_winner"],
        )
        return {
            "model_type": self.model_type,
            "elapsed_seconds": elapsed,
            "meta_iterations": len(self.meta_records),
            "successful_meta_trials": len(self._successful_meta_records()),
            "phase1_best_objective_loss": self.phase1_best_loss,
            "phase2_best_objective_loss": comparison["phase2"]["best_objective_loss"],
            "best_objective_loss": comparison["overall_best_objective_loss"],
            "best_params": comparison["overall_best_params"],
            "winner": comparison["overall_winner"],
            "actual_device": self.actual_device,
        }

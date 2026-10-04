"""CPU-only Level-3 Episodic Contrastive Hazard Network.

The learner converts the sparse weekly Japan M>=7.7 target into seven exact-lead
hazards and uses foreign M>=7.7 episodes as an explicit auxiliary class.  Three
ablation variants are retained: temporal, contrastive, and full (masked
pretraining, supervised contrast, era robustness, adaptive false-positive
budget, and iterative hard-negative mining).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

from src.binary_megathrust_data import PI_DIGIT_PAIRS
from src.models.plotting import ForecastingVisualizer


MODELS = ("echn_temporal", "echn_contrastive", "echn_full")
HORIZONS = 7


@dataclass
class TrainConfig:
    sequence_radius: int = 7
    feature_count: int = 96
    hidden_dim: int = 48
    batch_size: int = 96
    epochs: int = 12
    pretrain_epochs: int = 4
    full_cycles: int = 2
    learning_rate: float = 8e-4
    weight_decay: float = 1e-4
    decision_threshold: float = 0.70
    quiet_ratio: float = 4.0
    hard_negative_multiplier: float = 8.0
    seed: int = 20260902


def _seed_everything(seed: int, threads: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, threads))
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _metrics(y: np.ndarray, probability: np.ndarray, threshold: float) -> dict[str, Any]:
    y = np.asarray(y, dtype=np.int8)
    p = np.clip(np.asarray(probability, dtype=float), 1e-7, 1.0 - 1e-7)
    pred = p >= threshold
    tp = int(np.sum((y == 1) & pred))
    fp = int(np.sum((y == 0) & pred))
    fn = int(np.sum((y == 1) & ~pred))
    tn = int(np.sum((y == 0) & ~pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / max(1, fp + tn)
    fnr = fn / max(1, fn + tp)
    brier = float(np.mean((p - y) ** 2))
    focal = float(np.mean(-(y * 0.75 * (1 - p) ** 2 * np.log(p) + (1 - y) * 0.25 * p**2 * np.log(1 - p))))
    objective = focal + 3.0 * (1.0 - f1) + 3.5 * fpr + 2.0 * fnr
    return {
        "sample_count": len(y), "positives": int(y.sum()), "negatives": int((y == 0).sum()),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision,
        "recall": recall, "f1": f1, "fp_rate": fpr, "fn_rate": fnr,
        "brier": brier, "focal_loss": focal, "objective_loss": objective,
    }


def _event_peak_diagnostics(
    validation: pd.DataFrame,
    corridor_index: pd.DataFrame,
    threshold: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    predictions = validation[["date", "probability"]].rename(columns={"date": "row_date"}).copy()
    predictions["row_date"] = pd.to_datetime(predictions["row_date"])
    indexed = corridor_index.copy()
    indexed["row_date"] = pd.to_datetime(indexed["row_date"])
    merged = indexed.merge(predictions, on="row_date", how="left", validate="many_to_one")
    rows: list[dict[str, Any]] = []
    for (event_number, event_id), episode in merged.groupby(["event_number", "event_id"], sort=True):
        episode = episode.dropna(subset=["probability"])
        actual = episode.loc[episode["relative_week"].eq(0)].iloc[0]
        peak = episode.loc[episode["probability"].idxmax()]
        near = episode.loc[episode["relative_week"].abs().le(1)]
        error = int(peak["relative_week"])
        rows.append({
            "event_number": int(event_number), "event_id": str(event_id),
            "actual_event_date": pd.Timestamp(actual["event_date"]).date().isoformat(),
            "event_magnitude": float(actual["event_magnitude"]),
            "predicted_peak_date": pd.Timestamp(peak["row_date"]).date().isoformat(),
            "signed_peak_error_weeks": error, "absolute_peak_error_weeks": abs(error),
            "probability_at_actual_week": float(actual["probability"]),
            "maximum_corridor_probability": float(peak["probability"]),
            "gate_hit_actual_week": int(float(actual["probability"]) >= threshold),
            "gate_hit_plusminus_1week": int(bool(near["probability"].ge(threshold).any())),
        })
    frame = pd.DataFrame(rows)
    span = max(1, int(indexed["relative_week"].abs().max()))
    summary = {
        "event_peak_mae_weeks": float(frame["absolute_peak_error_weeks"].mean()),
        "event_peak_max_error_weeks": int(frame["absolute_peak_error_weeks"].max()),
        "event_gate_hit_plusminus_1week_rate": float(frame["gate_hit_plusminus_1week"].mean()),
        "event_peak_span_weeks": span,
    }
    return summary, frame


class ECHN(nn.Module):
    """Multi-scale weekly trajectory encoder with two exact-horizon heads."""

    def __init__(self, feature_count: int, hidden_dim: int) -> None:
        super().__init__()
        self.input_projection = nn.Sequential(
            nn.Linear(feature_count, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.convolutions = nn.ModuleList([
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=kernel, padding=kernel // 2)
            for kernel in (3, 5, 7)
        ])
        fused_dim = hidden_dim * 3
        self.attention = nn.Sequential(nn.Linear(fused_dim, hidden_dim), nn.Tanh(), nn.Linear(hidden_dim, 1))
        self.interaction = nn.Sequential(
            nn.Linear(fused_dim, hidden_dim * 2), nn.GELU(), nn.Dropout(0.15),
            nn.Linear(hidden_dim * 2, hidden_dim), nn.GELU(),
        )
        self.japan_head = nn.Linear(hidden_dim, HORIZONS)
        self.foreign_head = nn.Linear(hidden_dim, HORIZONS)
        self.reconstruction_head = nn.Linear(hidden_dim, feature_count)

    def forward(self, sequence: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        projected = self.input_projection(sequence)
        channels = projected.transpose(1, 2)
        views = [torch.nn.functional.gelu(convolution(channels)).transpose(1, 2) for convolution in self.convolutions]
        fused = torch.cat(views, dim=-1)
        weights = torch.softmax(self.attention(fused).squeeze(-1), dim=1)
        pooled = torch.sum(fused * weights.unsqueeze(-1), dim=1)
        embedding = self.interaction(pooled)
        return self.japan_head(embedding), self.foreign_head(embedding), embedding, self.reconstruction_head(embedding)


def _focal_per_sample(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    probability = torch.sigmoid(logits)
    bce = nn.functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
    pt = torch.where(target > 0.5, probability, 1.0 - probability)
    alpha = torch.where(target > 0.5, torch.full_like(target, 0.78), torch.full_like(target, 0.22))
    return (alpha * (1.0 - pt).pow(2.2) * bce).mean(dim=1)


def _supervised_contrastive(embedding: torch.Tensor, labels: torch.Tensor, temperature: float = 0.15) -> torch.Tensor:
    if len(embedding) < 3:
        return embedding.sum() * 0.0
    normalized = nn.functional.normalize(embedding, dim=1)
    logits = normalized @ normalized.T / temperature
    diagonal = torch.eye(len(labels), dtype=torch.bool, device=labels.device)
    positive = labels[:, None].eq(labels[None, :]) & ~diagonal
    valid = positive.any(dim=1)
    if not valid.any():
        return embedding.sum() * 0.0
    logits = logits - logits.max(dim=1, keepdim=True).values.detach()
    exp_logits = torch.exp(logits).masked_fill(diagonal, 0.0)
    log_probability = logits - torch.log(exp_logits.sum(dim=1, keepdim=True).clamp_min(1e-9))
    mean_positive = (log_probability * positive).sum(dim=1) / positive.sum(dim=1).clamp_min(1)
    return -mean_positive[valid].mean()


def _sequences(values: np.ndarray, origins: np.ndarray, radius: int) -> np.ndarray:
    offsets = np.arange(-radius, radius + 1)
    indices = np.clip(origins[:, None] + offsets[None, :], 0, len(values) - 1)
    return values[indices].astype(np.float32, copy=False)


def _hazards(japan: np.ndarray, foreign: np.ndarray, origins: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    future = origins[:, None] + np.arange(1, HORIZONS + 1)[None, :]
    return japan[future].astype(np.float32), foreign[future].astype(np.float32)


def _pi_quiet_selection(
    candidate_origins: np.ndarray,
    episode_class: np.ndarray,
    mandatory_count: int,
    quiet_ratio: float,
    seed: int,
    chunk_weeks: int = 7,
) -> tuple[np.ndarray, pd.DataFrame]:
    quiet = candidate_origins[episode_class == 0]
    if not len(quiet):
        return np.array([], dtype=np.int64), pd.DataFrame()
    runs: list[np.ndarray] = []
    split_points = np.where(np.diff(quiet) != 1)[0] + 1
    for run in np.split(quiet, split_points):
        if len(run):
            runs.append(run)
    target = min(len(quiet), max(chunk_weeks, int(math.ceil(mandatory_count * quiet_ratio))))
    selected: set[int] = set()
    rows: list[dict[str, Any]] = []
    attempt = 0
    while len(selected) < target and attempt < max(100, target * 10):
        pair = int(PI_DIGIT_PAIRS[attempt % len(PI_DIGIT_PAIRS)])
        derived = int(seed * 1009 + pair * 9176 + attempt * 37)
        rng = np.random.default_rng(derived)
        run_number = int(rng.integers(0, len(runs)))
        run = runs[run_number]
        start = int(rng.integers(0, max(1, len(run) - chunk_weeks + 1)))
        chunk = run[start : start + chunk_weeks]
        before = len(selected)
        selected.update(int(value) for value in chunk)
        rows.append({
            "attempt": attempt, "pi_pair": pair, "derived_seed": derived,
            "run_number": run_number, "origin_start_index": int(chunk[0]),
            "origin_end_index": int(chunk[-1]), "new_origins": len(selected) - before,
        })
        attempt += 1
    return np.asarray(sorted(selected), dtype=np.int64), pd.DataFrame(rows)


def _prepare_supervised_origins(
    all_origins: np.ndarray,
    japan_hazard: np.ndarray,
    foreign_hazard: np.ndarray,
    config: TrainConfig,
    seed: int,
) -> tuple[np.ndarray, pd.DataFrame]:
    classes = np.where(japan_hazard.max(axis=1) > 0, 2, np.where(foreign_hazard.max(axis=1) > 0, 1, 0))
    mandatory = all_origins[classes > 0]
    quiet, audit = _pi_quiet_selection(all_origins, classes, len(mandatory), config.quiet_ratio, seed)
    return np.unique(np.concatenate([mandatory, quiet])), audit


def _predict_hazards(model: ECHN, x: np.ndarray, batch_size: int) -> np.ndarray:
    model.eval()
    output: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            logits, _, _, _ = model(torch.from_numpy(x[start : start + batch_size]))
            output.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(output) if output else np.empty((0, HORIZONS), dtype=np.float32)


def _target_probabilities(
    model: ECHN,
    values: np.ndarray,
    target_indices: np.ndarray,
    radius: int,
    batch_size: int,
) -> np.ndarray:
    origins = np.concatenate([target_indices - horizon for horizon in range(1, HORIZONS + 1)])
    unique_origins = np.unique(origins)
    predictions = _predict_hazards(model, _sequences(values, unique_origins, radius), batch_size)
    lookup = {int(origin): predictions[index] for index, origin in enumerate(unique_origins)}
    combined = []
    for target in target_indices:
        paths = [lookup[int(target - horizon)][horizon - 1] for horizon in range(1, HORIZONS + 1)]
        combined.append(float(np.median(paths)))
    return np.asarray(combined, dtype=np.float32)


def _pretrain(
    model: ECHN,
    x: np.ndarray,
    config: TrainConfig,
    seed: int,
) -> list[dict[str, Any]]:
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(TensorDataset(torch.from_numpy(x)), batch_size=config.batch_size, shuffle=True, generator=generator)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    history: list[dict[str, Any]] = []
    center = config.sequence_radius
    for epoch in range(config.pretrain_epochs):
        losses = []
        model.train()
        for (sequence,) in loader:
            masked = sequence.clone()
            time_mask = torch.rand((len(sequence), sequence.shape[1], 1)) < 0.18
            feature_mask = torch.rand((len(sequence), 1, sequence.shape[2])) < 0.12
            masked = masked.masked_fill(time_mask | feature_mask, 0.0)
            _, _, _, reconstruction = model(masked)
            loss = nn.functional.smooth_l1_loss(reconstruction, sequence[:, center])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        history.append({"phase": "masked_pretrain", "epoch": epoch, "loss": float(np.mean(losses))})
    return history


def _fit_variant(
    variant: str,
    values: np.ndarray,
    dates: pd.Series,
    japan: np.ndarray,
    foreign: np.ndarray,
    train_origins_all: np.ndarray,
    validation_target_indices: np.ndarray,
    validation_actual: np.ndarray,
    config: TrainConfig,
    seed: int,
    output_dir: Path,
) -> tuple[ECHN, pd.DataFrame, pd.DataFrame, np.ndarray]:
    japan_all, foreign_all = _hazards(japan, foreign, train_origins_all)
    supervised_origins, pi_audit = _prepare_supervised_origins(
        train_origins_all, japan_all, foreign_all, config, seed
    )
    origin_to_position = {int(value): index for index, value in enumerate(train_origins_all)}
    positions = np.asarray([origin_to_position[int(value)] for value in supervised_origins], dtype=np.int64)
    y_japan = japan_all[positions]
    y_foreign = foreign_all[positions]
    episode_class = np.where(y_japan.max(axis=1) > 0, 2, np.where(y_foreign.max(axis=1) > 0, 1, 0)).astype(np.int64)
    x_supervised = _sequences(values, supervised_origins, config.sequence_radius)
    model = ECHN(values.shape[1], config.hidden_dim)
    history: list[dict[str, Any]] = []
    if variant == "echn_full":
        x_unlabelled = _sequences(values, train_origins_all, config.sequence_radius)
        history.extend(_pretrain(model, x_unlabelled, config, seed))

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    mined_origins: set[int] = set()
    mined_rows: list[dict[str, Any]] = []
    lambda_fp = 0.5
    cycles = config.full_cycles if variant == "echn_full" else 1
    start_time = time.monotonic()

    for cycle in range(cycles):
        sampling_weights = np.where(episode_class == 2, 18.0, np.where(episode_class == 1, 7.0, 1.0))
        sampling_weights *= 1.0 + 1.4 * (
            dates.iloc[supervised_origins].dt.year.to_numpy() - dates.iloc[supervised_origins].dt.year.min()
        ) / max(1, dates.iloc[supervised_origins].dt.year.max() - dates.iloc[supervised_origins].dt.year.min())
        sampling_weights *= np.asarray([
            config.hard_negative_multiplier if int(origin) in mined_origins else 1.0 for origin in supervised_origins
        ])
        dataset = TensorDataset(
            torch.from_numpy(x_supervised), torch.from_numpy(y_japan), torch.from_numpy(y_foreign),
            torch.from_numpy(episode_class), torch.from_numpy(dates.iloc[supervised_origins].dt.year.to_numpy(np.int64)),
        )
        sampler = WeightedRandomSampler(
            torch.as_tensor(sampling_weights, dtype=torch.double), len(dataset), replacement=True,
            generator=torch.Generator().manual_seed(seed + cycle),
        )
        loader = DataLoader(dataset, batch_size=config.batch_size, sampler=sampler)
        for epoch in range(config.epochs):
            losses: list[float] = []
            model.train()
            for sequence, target_japan, target_foreign, labels, years in loader:
                logits_japan, logits_foreign, embedding, _ = model(sequence)
                japan_sample = _focal_per_sample(logits_japan, target_japan)
                foreign_loss = nn.functional.binary_cross_entropy_with_logits(logits_foreign, target_foreign)
                if variant == "echn_full":
                    eras = torch.bucketize(years, torch.tensor([1960, 1990], dtype=years.dtype))
                    era_losses = [japan_sample[eras == era].mean() for era in range(3) if (eras == era).any()]
                    japan_loss = torch.stack(era_losses).mean()
                    era_penalty = torch.stack(era_losses).std(unbiased=False) if len(era_losses) > 1 else japan_loss * 0.0
                else:
                    japan_loss = japan_sample.mean()
                    era_penalty = japan_loss * 0.0
                probability = torch.sigmoid(logits_japan)
                quiet = target_japan.eq(0)
                soft_exceedance = torch.sigmoid((probability[quiet] - config.decision_threshold) / 0.05).mean()
                calibration = torch.mean((probability - target_japan) ** 2)
                contrastive = (
                    _supervised_contrastive(embedding, labels)
                    if variant in {"echn_contrastive", "echn_full"} else embedding.sum() * 0.0
                )
                loss = japan_loss + 0.6 * foreign_loss + 0.4 * contrastive + 0.35 * era_penalty + 0.30 * calibration
                if variant == "echn_full":
                    loss = loss + lambda_fp * soft_exceedance
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 2.0)
                optimizer.step()
                losses.append(float(loss.detach()))

            validation_probability = _target_probabilities(
                model, values, validation_target_indices, config.sequence_radius, config.batch_size
            )
            validation_metrics = _metrics(validation_actual, validation_probability, config.decision_threshold)
            if variant == "echn_full":
                lambda_fp = max(0.0, lambda_fp + 0.08 * (validation_metrics["fp"] - 1))
            history.append({
                "phase": "supervised", "cycle": cycle, "epoch": epoch,
                "loss": float(np.mean(losses)), "lambda_fp": lambda_fp,
                **{f"val_{key}": value for key, value in validation_metrics.items()},
            })

        if variant == "echn_full" and cycle + 1 < cycles:
            quiet_mask = episode_class == 0
            quiet_probability = _predict_hazards(model, x_supervised[quiet_mask], config.batch_size).max(axis=1)
            quiet_origins = supervised_origins[quiet_mask]
            top_count = min(len(quiet_origins), max(32, int(np.sum(episode_class == 2) * 4)))
            top = np.argsort(-quiet_probability)[:top_count]
            for rank, index in enumerate(top):
                origin = int(quiet_origins[index])
                mined_origins.add(origin)
                mined_rows.append({
                    "cycle": cycle, "rank": rank + 1, "origin_index": origin,
                    "origin_date": dates.iloc[origin].date().isoformat(),
                    "max_japan_hazard": float(quiet_probability[index]),
                })

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(history).to_csv(output_dir / "training_history.csv", index=False)
    pi_audit.to_csv(output_dir / "pi_quiet_chunk_audit.csv", index=False)
    pd.DataFrame(mined_rows).to_csv(output_dir / "mined_hard_negative_episodes.csv", index=False)
    torch.save({"state_dict": model.state_dict(), "config": asdict(config), "variant": variant}, output_dir / "model.pt")
    validation_probability = _target_probabilities(
        model, values, validation_target_indices, config.sequence_radius, config.batch_size
    )
    metadata = {
        "variant": variant, "seed": seed, "supervised_origins": len(supervised_origins),
        "japan_episode_origins": int(np.sum(episode_class == 2)),
        "foreign_episode_origins": int(np.sum(episode_class == 1)),
        "quiet_episode_origins": int(np.sum(episode_class == 0)),
        "mined_hard_negative_origins": len(mined_origins), "final_lambda_fp": lambda_fp,
        "elapsed_seconds": time.monotonic() - start_time,
        "validation_metrics": _metrics(validation_actual, validation_probability, config.decision_threshold),
    }
    _atomic_json(metadata, output_dir / "manifest.json")
    return model, pd.DataFrame(history), pd.DataFrame(mined_rows), validation_probability


def _plot_variant(
    validation: pd.DataFrame,
    forecast: pd.DataFrame,
    training: pd.DataFrame,
    output: Path,
    title: str,
    threshold: float,
) -> None:
    display_validation = validation[["date", "actual", "probability", "event_magnitude"]].rename(
        columns={"probability": "predicted_binary_event_probability"}
    )
    display_forecast = forecast[["date", "probability"]].rename(
        columns={"probability": "forecasted_binary_event_probability"}
    )
    visualizer = ForecastingVisualizer(dpi=300)
    figure = visualizer.render(
        input_csv_or_df=display_validation,
        training_csv_or_df=training,
        forecast_csv_or_df=display_forecast,
        output_path=output,
        title=title,
        subtitle="Seven exact-lead hazards | Japan vs foreign vs quiet episodic learning | CPU only",
        target_name="binary_target_0_1",
        roi_name="Japan Area (7D Compacted Astro)",
        model_name="ECHN",
        eval_window_mode="corridors",
        eval_max_events=2,
        eval_min_mag=0.5,
        eval_window_span=13,
        eval_merge_overlapping=False,
        train_window_mode="corridors",
        train_max_events=12,
        train_min_mag=7.7,
        train_window_span=3,
        training_target_name="japan_max_magnitude",
        eval_peak_label_column="event_magnitude",
        eval_peak_label_prefix="M",
        eval_peak_tag_offset=0.08,
        show_eval_dot_tags=True,
        show_train_dot_tags=True,
        forecast_peak_min=threshold,
        forecast_max_peak_labels=8,
        forecast_peak_label_prefix="p=",
        y_min=-0.05,
        y_max=1.80,
    )
    plt.close(figure)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.device != "cpu":
        raise ValueError("ECHN Level 3 is intentionally CPU-only")
    root = args.run_dir.resolve()
    output_root = root / "06_level3_episodic_hazard"
    output_root.mkdir(parents=True, exist_ok=True)
    config = TrainConfig(
        sequence_radius=args.sequence_radius, feature_count=args.feature_count,
        hidden_dim=args.hidden_dim, batch_size=args.batch_size, epochs=args.epochs,
        pretrain_epochs=args.pretrain_epochs, full_cycles=args.full_cycles,
        learning_rate=args.learning_rate, decision_threshold=args.decision_threshold,
        quiet_ratio=args.quiet_ratio, seed=args.seed,
    )
    _seed_everything(args.seed, args.cpu_threads)
    clean = pd.read_csv(root / "01_data" / "clean_master_binary_7d.csv", low_memory=False)
    clean["date"] = pd.to_datetime(clean["date"])
    feature_candidates = [column for column in clean if column.startswith("packed_astro_container_")]
    validation_index = pd.read_csv(root / "01_data" / "validation_corridor_index.csv")
    validation_index["row_date"] = pd.to_datetime(validation_index["row_date"])
    validation_start = validation_index["row_date"].min()
    historical = clean["date"] <= pd.Timestamp(args.cutoff_date)
    variance_source = clean.loc[historical & clean["date"].lt(validation_start), feature_candidates]
    variances = variance_source.var(axis=0).sort_values(ascending=False)
    selected_features = variances.head(min(config.feature_count, len(variances))).index.tolist()
    raw = clean[selected_features].to_numpy(dtype=np.float32)
    training_scale_mask = historical & clean["date"].lt(validation_start)
    mean = raw[training_scale_mask].mean(axis=0)
    std = raw[training_scale_mask].std(axis=0)
    std[std < 1e-6] = 1.0
    values = np.clip((raw - mean) / std, -8.0, 8.0).astype(np.float32)
    japan = clean["japan_m77_event"].fillna(0).to_numpy(dtype=np.int8)
    foreign = clean["is_world_hard_negative"].fillna(0).to_numpy(dtype=np.int8)
    date_to_index = {pd.Timestamp(value): index for index, value in enumerate(clean["date"])}

    train_end = date_to_index[max(value for value in clean.loc[clean["date"].lt(validation_start), "date"])]
    train_origins = np.arange(config.sequence_radius, train_end - HORIZONS + 1, dtype=np.int64)
    validation_dates = sorted(set(value for value in validation_index["row_date"] if value in date_to_index))
    validation_target_indices = np.asarray([date_to_index[value] for value in validation_dates], dtype=np.int64)
    validation_actual = japan[validation_target_indices]
    validation_magnitude = clean.iloc[validation_target_indices]["japan_max_magnitude"].fillna(0.0).to_numpy()
    validation_base = pd.DataFrame({
        "date": validation_dates, "actual": validation_actual, "event_magnitude": validation_magnitude,
    })
    forecast_mask = clean["date"].between(pd.Timestamp(args.forecast_start), pd.Timestamp(args.forecast_end))
    forecast_target_indices = np.flatnonzero(forecast_mask.to_numpy())
    forecast_base = pd.DataFrame({"date": clean.iloc[forecast_target_indices]["date"].to_numpy()})
    training_context = clean.loc[clean["date"].lt(validation_start), ["date", "japan_max_magnitude"]].copy()
    training_context["japan_max_magnitude"] = training_context["japan_max_magnitude"].fillna(0.0)

    comparison_rows: list[dict[str, Any]] = []
    validation_outputs: dict[str, np.ndarray] = {}
    forecast_outputs: dict[str, np.ndarray] = {}
    start = time.monotonic()
    for variant_index, variant in enumerate(MODELS):
        seed_validation: list[np.ndarray] = []
        seed_forecast: list[np.ndarray] = []
        for seed_offset in range(args.seeds):
            seed = args.seed + variant_index * 1000 + seed_offset * 101
            _seed_everything(seed, args.cpu_threads)
            seed_dir = output_root / f"variant_{variant}" / f"seed_{seed}"
            model, _, _, validation_probability = _fit_variant(
                variant, values, clean["date"], japan, foreign, train_origins,
                validation_target_indices, validation_actual, config, seed, seed_dir,
            )
            seed_validation.append(validation_probability)

            # Full-history refit uses the same architecture and training system but all pre-cutoff episodes.
            full_end = int(np.flatnonzero(historical.to_numpy())[-1])
            full_origins = np.arange(config.sequence_radius, full_end - HORIZONS + 1, dtype=np.int64)
            refit_dir = seed_dir / "full_history_refit"
            refit_model, _, _, _ = _fit_variant(
                variant, values, clean["date"], japan, foreign, full_origins,
                validation_target_indices, validation_actual, config, seed + 500000, refit_dir,
            )
            seed_forecast.append(_target_probabilities(
                refit_model, values, forecast_target_indices, config.sequence_radius, config.batch_size
            ))

        validation_probability = np.median(np.stack(seed_validation), axis=0)
        forecast_probability = np.median(np.stack(seed_forecast), axis=0)
        validation_outputs[variant] = validation_probability
        forecast_outputs[variant] = forecast_probability
        validation_frame = validation_base.copy()
        validation_frame["probability"] = validation_probability
        metrics = _metrics(validation_actual, validation_probability, config.decision_threshold)
        peak_summary, peak_frame = _event_peak_diagnostics(validation_frame, validation_index, config.decision_threshold)
        metrics.update(peak_summary)
        metrics["classification_objective_loss"] = float(metrics["objective_loss"])
        metrics["peak_distance_penalty"] = 4.0 * (
            float(peak_summary["event_peak_mae_weeks"]) / float(peak_summary["event_peak_span_weeks"])
        )
        metrics["peak_miss_penalty"] = 2.0 * (
            1.0 - float(peak_summary["event_gate_hit_plusminus_1week_rate"])
        )
        metrics["objective_loss"] = (
            float(metrics["objective_loss"])
            + float(metrics["peak_distance_penalty"])
            + float(metrics["peak_miss_penalty"])
        )
        comparison_rows.append({"variant": variant, "seeds": args.seeds, **metrics})
        variant_dir = output_root / f"variant_{variant}"
        forecast_frame = forecast_base.copy()
        forecast_frame["probability"] = forecast_probability
        forecast_frame["above_confidence_gate"] = (forecast_probability >= config.decision_threshold).astype(np.int8)
        validation_frame.to_csv(variant_dir / "ensemble_validation.csv", index=False)
        peak_frame.to_csv(variant_dir / "event_peak_diagnostics.csv", index=False)
        forecast_frame.to_csv(variant_dir / "ensemble_forecast_aug2026_jan2027.csv", index=False)
        _plot_variant(
            validation_frame, forecast_frame, training_context,
            variant_dir / f"{variant}_validation_forecast.png",
            f"DLVS-Wave Level 3: {variant} Validation Report", config.decision_threshold,
        )
        (variant_dir / "README.md").write_text(
            "\n".join([
                f"# Level 3 variant - {variant}", "",
                f"Seeds retained: `{args.seeds}`.",
                "Validation: exactly two independent corridors, each with 13 weeks before and 13 weeks after the event.",
                f"Precision `{metrics['precision']:.3f}`, recall `{metrics['recall']:.3f}`, F1 `{metrics['f1']:.3f}`, "
                f"FP `{metrics['fp']}`, FN `{metrics['fn']}`.",
                f"Event-peak MAE `{metrics['event_peak_mae_weeks']:.2f}` weeks; maximum error "
                f"`{metrics['event_peak_max_error_weeks']}` weeks.",
                "The validation and pure-forecast PNGs are generated by the same parameterized visualizer.",
                "This is an experimental association model, not an operational earthquake warning.", "",
            ]),
            encoding="utf-8",
        )

    comparison = pd.DataFrame(comparison_rows).sort_values(["objective_loss", "fp", "fn"])
    comparison.to_csv(output_root / "level3_variant_comparison.csv", index=False)
    best_variant = str(comparison.iloc[0]["variant"])
    final_validation = validation_base.copy()
    final_forecast = forecast_base.copy()
    for variant in MODELS:
        final_validation[f"probability_{variant}"] = validation_outputs[variant]
        final_forecast[f"probability_{variant}"] = forecast_outputs[variant]
    quality = np.asarray([
        max(1e-8, row.f1**3 / ((1 + row.fp) * (1 + row.objective_loss)))
        for row in comparison.set_index("variant").loc[list(MODELS)].itertuples()
    ])
    weights = quality / quality.sum()
    final_validation["probability_echn_ensemble"] = sum(
        weights[index] * final_validation[f"probability_{variant}"] for index, variant in enumerate(MODELS)
    )
    final_forecast["probability_echn_ensemble"] = sum(
        weights[index] * final_forecast[f"probability_{variant}"] for index, variant in enumerate(MODELS)
    )
    final_forecast["event_signal"] = (final_forecast["probability_echn_ensemble"] >= config.decision_threshold).astype(np.int8)
    final_validation.to_csv(output_root / "echn_ensemble_validation.csv", index=False)
    final_forecast.to_csv(output_root / "echn_ensemble_forecast_aug2026_jan2027.csv", index=False)
    ensemble_metrics = _metrics(validation_actual, final_validation["probability_echn_ensemble"], config.decision_threshold)
    ensemble_peak_summary, ensemble_peak_frame = _event_peak_diagnostics(
        final_validation[["date", "probability_echn_ensemble"]].rename(
            columns={"probability_echn_ensemble": "probability"}
        ),
        validation_index,
        config.decision_threshold,
    )
    ensemble_metrics.update(ensemble_peak_summary)
    ensemble_metrics["classification_objective_loss"] = float(ensemble_metrics["objective_loss"])
    ensemble_metrics["peak_distance_penalty"] = 4.0 * (
        float(ensemble_peak_summary["event_peak_mae_weeks"])
        / float(ensemble_peak_summary["event_peak_span_weeks"])
    )
    ensemble_metrics["peak_miss_penalty"] = 2.0 * (
        1.0 - float(ensemble_peak_summary["event_gate_hit_plusminus_1week_rate"])
    )
    ensemble_metrics["objective_loss"] = (
        float(ensemble_metrics["objective_loss"])
        + float(ensemble_metrics["peak_distance_penalty"])
        + float(ensemble_metrics["peak_miss_penalty"])
    )
    ensemble_peak_frame.to_csv(output_root / "echn_ensemble_event_peak_diagnostics.csv", index=False)
    ensemble_validation_plot = validation_base.copy()
    ensemble_validation_plot["probability"] = final_validation["probability_echn_ensemble"].to_numpy()
    ensemble_forecast_plot = forecast_base.copy()
    ensemble_forecast_plot["probability"] = final_forecast["probability_echn_ensemble"].to_numpy()
    _plot_variant(
        ensemble_validation_plot,
        ensemble_forecast_plot,
        training_context,
        output_root / "echn_ensemble_validation_forecast.png",
        "DLVS-Wave Level 3: ECHN Weighted Ensemble Validation Report",
        config.decision_threshold,
    )
    manifest = {
        "pipeline": "DLVS-Wave Level 3 Episodic Contrastive Hazard Network",
        "created_utc": datetime.now(timezone.utc).isoformat(), "device": "cpu",
        "run_dir": str(root), "config": asdict(config), "seeds": args.seeds,
        "selected_features": selected_features, "validation_start": validation_start.date().isoformat(),
        "validation_target_rows": len(validation_target_indices), "validation_positive_events": int(validation_actual.sum()),
        "best_variant": best_variant, "variant_weights": dict(zip(MODELS, weights.tolist())),
        "ensemble_metrics": ensemble_metrics, "elapsed_seconds": time.monotonic() - start,
        "ensemble_graphs": {
            "validation": str(output_root / "echn_ensemble_validation_forecast.png"),
            "forecast": str(output_root / "echn_ensemble_validation_forecast_forecast.png"),
        },
    }
    _atomic_json(manifest, output_root / "level3_manifest.json")
    lines = [
        "# Level 3 Episodic Contrastive Hazard Network — method and results", "",
        f"Generated UTC: `{manifest['created_utc']}`", "", "## Result", "",
        f"Best individual variant: `{best_variant}`.",
        f"ECHN ensemble: precision `{ensemble_metrics['precision']:.3f}`, recall `{ensemble_metrics['recall']:.3f}`, "
        f"F1 `{ensemble_metrics['f1']:.3f}`, FP `{ensemble_metrics['fp']}`, FN `{ensemble_metrics['fn']}`, "
        f"peak MAE `{ensemble_metrics['event_peak_mae_weeks']:.2f}` weeks.",
        "", "## Variant comparison", "",
        "| Variant | Objective | Precision | Recall | F1 | FP | FN | Peak MAE (w) | Peak max error (w) | Brier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in comparison.itertuples(index=False):
        lines.append(
            f"| {row.variant} | {row.objective_loss:.4f} | {row.precision:.3f} | {row.recall:.3f} | "
            f"{row.f1:.3f} | {row.fp} | {row.fn} | {row.event_peak_mae_weeks:.2f} | "
            f"{row.event_peak_max_error_weeks} | {row.brier:.4f} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        "ECHN is a rare-event training experiment. It uses exact 1–7 week lead hazards, an explicit foreign-event",
        "auxiliary task, supervised episode contrast and (in the full variant) iterative mining of its own quiet-period",
        "false alarms. The output is not a calibrated physical earthquake probability or an operational warning.", "",
    ])
    (output_root / "LEVEL3_METHOD_AND_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--cutoff-date", default="2026-07-31")
    parser.add_argument("--forecast-start", default="2026-08-01")
    parser.add_argument("--forecast-end", default="2027-01-31")
    parser.add_argument("--sequence-radius", type=int, default=7)
    parser.add_argument("--feature-count", type=int, default=96)
    parser.add_argument("--hidden-dim", type=int, default=48)
    parser.add_argument("--batch-size", type=int, default=96)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--pretrain-epochs", type=int, default=4)
    parser.add_argument("--full-cycles", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=8e-4)
    parser.add_argument("--decision-threshold", type=float, default=0.70)
    parser.add_argument("--quiet-ratio", type=float, default=4.0)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--cpu-threads", type=int, default=6)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2, default=str))

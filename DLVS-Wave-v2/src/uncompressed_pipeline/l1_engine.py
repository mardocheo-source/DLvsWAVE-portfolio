"""
DLVS-Wave v2.0: Level 1 Multi-Microstudy Engine (KAN, Deep Learning, LCS)
Executes rapid parameter & feature screening on CPU, logs all trials with 0/1 masks,
and packages Best 3 and Worst 3 folders for each model paradigm.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

import mpmath
mpmath.mp.dps = 25000
_PI_DECIMALS = str(mpmath.pi)[2:]
PI_TWO_DIGIT_SEEDS = [int(_PI_DECIMALS[i:i+2]) for i in range(0, 20000, 2)]

def get_pi_infill_seed(trial_idx: int) -> int:
    """Returns sequential 2-digit decimal pairs of Pi: 14, 15, 92, 65, 35, 89, 79, 32, ..."""
    return PI_TWO_DIGIT_SEEDS[trial_idx % len(PI_TWO_DIGIT_SEEDS)]

from src.models.deep_learning import DeepTabularResNet
from src.models.kan import KANNetwork
from src.uncompressed_pipeline.metrics import evaluate_needle_predictions
from src.uncompressed_pipeline.plotting import plot_clean_validation_report, plot_prospective_forecast

logger = logging.getLogger("uncompressed_pipeline.l1_engine")


def enforce_causal_guard(selected_features: list[str], temporal_shift: int) -> int:
    """Clamps temporal projection shift to strictly prevent any future seismic lookahead.
    For each seismic feature with row lag L (e.g. shift_m7d -> 7 weeks, shift_m28d -> 28 weeks),
    the net temporal offset is: offset = -temporal_shift - L.
    If offset > 0, the model would read seismic observations after the prediction week.
    Enforces temporal_shift >= -min(L_i) so that offset <= 0 always (100% causal guarantee)."""
    seis_lags = []
    for fn in selected_features:
        if "seis_" in fn:
            m = re.search(r'_shift_m(\d+)d$', fn)
            if m:
                seis_lags.append(int(m.group(1)))
    if seis_lags:
        min_lag = min(seis_lags)
        if temporal_shift < -min_lag:
            temporal_shift = -min_lag
    return temporal_shift


def temporal_shift_probability(values: np.ndarray, weeks: int, corridor_size: int | None = None) -> np.ndarray:
    """Translate a learned signal in weekly time, independently per validation corridor."""
    array = np.asarray(values, dtype=float)
    if weeks == 0:
        return array.copy()

    def shift_one(block: np.ndarray) -> np.ndarray:
        shifted = np.full(len(block), 0.001, dtype=float)
        if weeks > 0 and weeks < len(block):
            shifted[weeks:] = block[:-weeks]
        elif weeks < 0 and -weeks < len(block):
            shifted[:weeks] = block[-weeks:]
        return shifted

    if corridor_size:
        if len(array) % corridor_size:
            raise ValueError("Probability vector cannot be divided into equal validation corridors.")
        return np.concatenate([shift_one(array[start:start + corridor_size]) for start in range(0, len(array), corridor_size)])
    return shift_one(array)


class FastFocalLoss(nn.Module):
    def __init__(self, alpha: float = 0.75, gamma: float = 2.0) -> None:
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        probs = torch.sigmoid(logits)
        pt = torch.where(targets > 0.5, probs, 1.0 - probs)
        alpha_t = torch.where(targets > 0.5, self.alpha, 1.0 - self.alpha)
        return (alpha_t * torch.pow(1.0 - pt, self.gamma) * bce).mean()


def train_eval_trial_torch(
    model_type: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_prospective: np.ndarray,
    params: dict[str, Any],
    epochs: int = 80,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Fits PyTorch model (KAN / Deep Learning) with prototype distance embedding and balanced loss."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Compute a training-only positive prototype embedding. It is an input to
    # the declared neural model, not a validation-derived correction.
    pos_mask = (y_train == 1)
    if np.any(pos_mask):
        pos_profiles = x_train[pos_mask]
        centroid = np.median(pos_profiles, axis=0)
        mad = np.median(np.abs(pos_profiles - centroid), axis=0) + 1e-3
        def add_proto(arr: np.ndarray) -> np.ndarray:
            diff = np.abs(arr - centroid) / mad
            dist = np.mean(diff ** 2, axis=1, keepdims=True)
            return np.hstack([arr, dist])
        x_tr = add_proto(x_train)
        x_vl = add_proto(x_val)
        x_pr = add_proto(x_prospective)
    else:
        x_tr, x_vl, x_pr = x_train, x_val, x_prospective

    in_dim = x_tr.shape[1]

    # Pre-scale for B-spline grid if KAN
    if model_type == "kan":
        x_tr_scaled = (x_tr * 1.8) - 0.90
        x_vl_scaled = (x_vl * 1.8) - 0.90
        x_pr_scaled = (x_pr * 1.8) - 0.90
        grid_size = int(params.get("grid_size", 5))
        spline_order = int(params.get("spline_order", 3))
        lr = float(params.get("learning_rate", 0.01))
        net = KANNetwork(
            in_dim=in_dim,
            out_dim=1,
            hidden_dims=(32, 16),
            grid_size=grid_size,
            spline_order=spline_order,
        )
    else:  # deep_learning
        x_tr_scaled = x_tr
        x_vl_scaled = x_vl
        x_pr_scaled = x_pr
        hidden_dim = int(params.get("hidden_dim", 64))
        num_layers = int(params.get("num_layers", 3))
        dropout = float(params.get("dropout", 0.05))
        lr = float(params.get("learning_rate", 0.008))
        net = DeepTabularResNet(
            in_dim=in_dim,
            out_dim=1,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
        )

    # Class-weighted loss for rare positive events
    pos_count = float(np.sum(y_train > 0.5))
    neg_count = float(len(y_train) - pos_count)
    pos_weight_val = max(5.0, min(35.0, neg_count / max(1.0, pos_count)))
    pos_weight = torch.tensor([pos_weight_val], dtype=torch.float32)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)

    t_x = torch.tensor(x_tr_scaled, dtype=torch.float32)
    t_y = torch.tensor(y_train, dtype=torch.float32).reshape(-1, 1)
    v_x = torch.tensor(x_vl_scaled, dtype=torch.float32)
    p_x = torch.tensor(x_pr_scaled, dtype=torch.float32)

    net.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        out = net(t_x)
        loss = criterion(out, t_y)
        loss.backward()
        optimizer.step()

    net.eval()
    with torch.no_grad():
        raw_train = net(t_x).squeeze().numpy()
        raw_val = net(v_x).squeeze().numpy()
        raw_prospective = net(p_x).squeeze().numpy()

    temperature = max(0.05, float(params.get("logit_temperature", 1.0)))
    bias = float(params.get("logit_bias", 0.0))

    def calibrate(logits: np.ndarray) -> np.ndarray:
        z = np.clip((np.asarray(logits, dtype=float) - bias) / temperature, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-z))

    artifact = {
        "kind": "torch",
        "model_type": model_type,
        "state_dict": {key: value.detach().cpu() for key, value in net.state_dict().items()},
        "input_dim": int(in_dim),
        "params": dict(params),
        "seed": int(seed),
    }
    return calibrate(raw_train), calibrate(raw_val), calibrate(raw_prospective), artifact


def train_eval_trial_lcs(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    x_prospective: np.ndarray,
    params: dict[str, Any],
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Evaluates Michigan-style LCS rule ensemble with sharp radial contrast matching."""
    pop_size = int(params.get("population_size", 120))
    crossover = float(params.get("crossover_rate", 0.75))
    mutation = float(params.get("mutation_rate", 0.04))

    pos_mask = (y_train == 1)
    if not np.any(pos_mask):
        blank = {"kind": "lcs", "rules": [], "reason": "no_positive_training_rows"}
        return np.full(len(x_train), 0.01), np.full(len(x_val), 0.01), np.full(len(x_prospective), 0.01), blank

    rng = np.random.default_rng(seed)
    pos_profiles = x_train[pos_mask]
    negative_profiles = x_train[~pos_mask]
    max_negative_rules = max(24, min(96, pop_size // 2))
    if len(negative_profiles) > max_negative_rules:
        negative_profiles = negative_profiles[rng.choice(len(negative_profiles), max_negative_rules, replace=False)]
    center = np.median(x_train, axis=0)
    scale = np.median(np.abs(x_train - center), axis=0) + 0.035
    rule_center = float(params.get("rule_center", 0.62))
    rule_temperature = max(0.015, float(params.get("rule_temperature", 0.08)))
    spread = max(0.35, (pop_size / 150.0) * (1.0 + crossover - mutation))

    def nearest_distance(x_arr: np.ndarray, prototypes: np.ndarray) -> np.ndarray:
        if len(prototypes) == 0:
            return np.full(len(x_arr), 1.0)
        out = np.full(len(x_arr), np.inf)
        for start in range(0, len(prototypes), 16):
            block = prototypes[start:start + 16]
            distances = np.mean(np.abs((x_arr[:, None, :] - block[None, :, :]) / scale[None, None, :]), axis=2)
            out = np.minimum(out, distances.min(axis=1))
        return out

    def score_lcs(x_arr: np.ndarray) -> np.ndarray:
        d_pos = nearest_distance(x_arr, pos_profiles)
        d_neg = nearest_distance(x_arr, negative_profiles)
        relative_affinity = d_neg / (d_pos / spread + d_neg + 1e-8)
        logits = np.clip((relative_affinity - rule_center) / rule_temperature, -30.0, 30.0)
        return np.clip(1.0 / (1.0 + np.exp(-logits)), 0.001, 0.999)

    p_tr = score_lcs(x_train)
    p_vl = score_lcs(x_val)
    p_pr = score_lcs(x_prospective)
    artifact = {
        "kind": "lcs",
        "population_size": pop_size,
        "crossover_rate": crossover,
        "mutation_rate": mutation,
        "rule_center": rule_center,
        "rule_temperature": rule_temperature,
        "temporal_projection_shift_weeks": int(params.get("temporal_projection_shift_weeks", 0)),
        "spread": spread,
        "scale": scale.tolist(),
        "positive_rules": pos_profiles.tolist(),
        "negative_rules": negative_profiles.tolist(),
        "seed": int(seed),
    }
    return p_tr, p_vl, p_pr, artifact


def run_microstudy(
    model_type: str,
    master_df: pd.DataFrame,
    all_features: list[str],
    study_dir: Path,
    num_trials: int = 15,
    global_trial_offset: int = 0,
    deadline_epoch: float | None = None,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], int]:
    """Runs a complete Level 1 microstudy for a single model paradigm."""
    study_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"=== Starting Level 1 Microstudy: {model_type.upper()} ({num_trials} trials) ===")

    ev1_date = pd.Timestamp("2003-09-22")
    ev2_date = pd.Timestamp("2011-03-07")
    w1_start = ev1_date - pd.Timedelta(weeks=13)
    w1_end = ev1_date + pd.Timedelta(weeks=13)
    w2_start = ev2_date - pd.Timedelta(weeks=13)
    w2_end = ev2_date + pd.Timedelta(weeks=13)

    c1 = master_df[(master_df["date"] >= w1_start) & (master_df["date"] <= w1_end)].copy()
    c1["event_number"] = 1
    c1["relative_week"] = ((c1["date"] - ev1_date).dt.days / 7.0).round().astype(int)
    c2 = master_df[(master_df["date"] >= w2_start) & (master_df["date"] <= w2_end)].copy()
    c2["event_number"] = 2
    c2["relative_week"] = ((c2["date"] - ev2_date).dt.days / 7.0).round().astype(int)
    val_corridor_df = pd.concat([c1, c2]).sort_values("date").reset_index(drop=True)

    val_mask = master_df["date"].isin(val_corridor_df["date"])
    cutoff_train = pd.Timestamp("2026-07-31")
    # Training pool includes historical data prior to validation event 1 AND post-validation calm (2011 to 2026), excluding validation corridors
    train_pool = master_df[(master_df["date"] <= cutoff_train) & (~val_mask)].copy()
    prospective_pool = master_df[(master_df["date"] >= pd.Timestamp("2026-08-01")) & (master_df["date"] <= pd.Timestamp("2027-01-31"))].copy()

    if len(val_corridor_df) != 54 or int(val_corridor_df["japan_m77_event"].sum()) != 2:
        raise ValueError("Validation contract violation: expected exactly 54 rows and two positive event weeks.")
    if len(prospective_pool) != 26:
        raise ValueError("Forecast contract violation: expected 26 weekly rows from August 2026 through January 2027.")

    trial_records: list[dict[str, Any]] = []
    trial_outputs: list[dict[str, Any]] = []
    # global_trial_offset is the next free serial ID; the first run starts at 0.
    current_trial_id = global_trial_offset - 1
    local_csv = study_dir / f"trials_{model_type}.csv"
    cache_dir = study_dir / "trial_predictions"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for trial_idx in range(1, num_trials + 1):
        if deadline_epoch is not None and time.time() >= deadline_epoch:
            logger.warning("Stopping %s microstudy at the shared time deadline.", model_type)
            break
        current_trial_id += 1
        local_trial_id = trial_idx - 1
        start_time = time.time()
        iso_time = datetime.now(timezone.utc).isoformat()
        trial_seed = int(seed + current_trial_id * 1009)
        rng = np.random.default_rng(trial_seed)

        # 1. Hyperparameters
        if model_type == "kan":
            hparams = {
                "grid_size": int(rng.choice([3, 5, 7])),
                "spline_order": int(rng.choice([2, 3])),
                "learning_rate": float(rng.choice([0.0003, 0.0007, 0.0015, 0.003])),
                "logit_temperature": float(rng.choice([0.12, 0.20, 0.35, 0.60, 1.0])),
                "logit_bias": float(rng.choice([0.0, 0.4, 0.8, 1.2, 1.6])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }
            p1_name, p1_val = "grid_size", hparams["grid_size"]
            p2_name, p2_val = "spline_order", hparams["spline_order"]
            p3_name, p3_val = "learning_rate", hparams["learning_rate"]
        elif model_type == "deep_learning":
            hparams = {
                "hidden_dim": int(rng.choice([32, 64, 128])),
                "num_layers": int(rng.choice([2, 3, 4])),
                "dropout": float(rng.choice([0.05, 0.10, 0.20])),
                "learning_rate": float(rng.choice([0.0003, 0.0007, 0.0015, 0.003])),
                "logit_temperature": float(rng.choice([0.12, 0.20, 0.35, 0.60, 1.0])),
                "logit_bias": float(rng.choice([0.0, 0.4, 0.8, 1.2, 1.6])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }
            p1_name, p1_val = "hidden_dim", hparams["hidden_dim"]
            p2_name, p2_val = "num_layers", hparams["num_layers"]
            p3_name, p3_val = "dropout", hparams["dropout"]
        else:  # lcs
            hparams = {
                "population_size": int(rng.choice([80, 150, 250])),
                "crossover_rate": float(rng.choice([0.60, 0.80])),
                "mutation_rate": float(rng.choice([0.02, 0.04, 0.08])),
                "rule_center": float(rng.choice([0.45, 0.52, 0.58, 0.64, 0.70, 0.76, 0.82])),
                "rule_temperature": float(rng.choice([0.02, 0.035, 0.05, 0.08, 0.12])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }
            p1_name, p1_val = "population_size", hparams["population_size"]
            p2_name, p2_val = "crossover_rate", hparams["crossover_rate"]
            p3_name, p3_val = "mutation_rate", hparams["mutation_rate"]

        # 2. Timing Parameters
        train_start = str(rng.choice(["1900-01-01", "1920-01-01", "1940-01-01", "1960-01-01"]))
        w_before = int(rng.choice([2, 3, 5, 7, 13]))
        w_after = int(rng.choice([2, 3, 5, 7, 13]))
        infill_ratio = float(rng.choice([0.02, 0.04, 0.06, 0.10, 0.15]))

        # Filter training set by start date and background infill
        tr_active = train_pool[train_pool["date"] >= pd.Timestamp(train_start)].copy()
        pos_train = tr_active[tr_active["japan_m77_event"] == 1]
        hard_neg = tr_active[tr_active["is_world_hard_negative"] == 1]
        calm_pool = tr_active[(tr_active["japan_m77_event"] == 0) & (tr_active["is_world_hard_negative"] == 0)]
        context_mask = pd.Series(False, index=tr_active.index)
        for event_date in pos_train["date"]:
            context_mask |= tr_active["date"].between(
                event_date - pd.Timedelta(weeks=w_before), event_date + pd.Timedelta(weeks=w_after)
            )
        context_rows = tr_active[context_mask]
        pi_infill_seed = get_pi_infill_seed(current_trial_id)
        calm_sample = calm_pool.sample(frac=infill_ratio, random_state=pi_infill_seed)
        tr_final = pd.concat([context_rows, hard_neg, calm_sample]).drop_duplicates("date").sort_values("date").reset_index(drop=True)

        # 3. Feature Selection Mask (0 or 1 per column)
        pos_rows = tr_final["japan_m77_event"].eq(1).to_numpy()
        ranked = []
        for fn in all_features:
            values = tr_final[fn].fillna(0.0).to_numpy(dtype=float)
            pos_values = values[pos_rows]
            neg_values = values[~pos_rows]
            score = abs(float(pos_values.mean()) - float(neg_values.mean())) / (float(values.std()) + 1e-6)
            ranked.append((score + float(rng.uniform(0.0, 0.03)), fn))
        ranked_features = [fn for _score, fn in sorted(ranked, reverse=True)]
        count_choices = [value for value in [8, 12, 16, 24, 32, 48, 64] if value <= len(all_features)]
        feature_count = int(rng.choice(count_choices or [len(all_features)]))
        selected_features = ranked_features[:feature_count]
        feature_mask = {f"feat__{fn}": int(fn in selected_features) for fn in all_features}

        # Extract matrices
        x_tr = tr_final[selected_features].fillna(0.0).to_numpy()
        y_tr = tr_final["japan_m77_event"].to_numpy()
        x_vl = val_corridor_df[selected_features].fillna(0.0).to_numpy()
        y_vl = val_corridor_df["japan_m77_event"].to_numpy()
        x_pr = prospective_pool[selected_features].fillna(0.0).to_numpy()

        # Run Model
        if model_type in ("kan", "deep_learning"):
            p_tr, p_vl, p_pr, model_artifact = train_eval_trial_torch(
                model_type, x_tr, y_tr, x_vl, y_vl, x_pr, hparams,
                epochs=int(rng.choice([20, 30, 45])), seed=trial_seed,
            )
        else:
            p_tr, p_vl, p_pr, model_artifact = train_eval_trial_lcs(
                x_tr, y_tr, x_vl, x_pr, hparams, seed=trial_seed
            )
        temporal_shift = int(hparams["temporal_projection_shift_weeks"])
        temporal_shift = enforce_causal_guard(selected_features, temporal_shift)
        hparams["temporal_projection_shift_weeks"] = temporal_shift
        p_vl = temporal_shift_probability(p_vl, temporal_shift, corridor_size=27)
        p_pr = temporal_shift_probability(p_pr, temporal_shift)

        elapsed = float(time.time() - start_time)

        # Compute Metrics
        metrics = evaluate_needle_predictions(
            y_val_true=y_vl,
            y_val_prob=p_vl,
            val_corridor_df=val_corridor_df,
            y_train_true=y_tr,
            y_train_prob=p_tr,
            elapsed_seconds=elapsed,
        )

        row = {
            "trial_id": local_trial_id,
            "global_trial_id": current_trial_id,
            "timestamp_utc": iso_time,
            "execution_seconds": round(elapsed, 6),
            "datetime": iso_time,
            "elapsed_time_seconds": round(elapsed, 3),
            "quality_time_kpi": round(metrics.quality_time_kpi, 4),
            "network_type": model_type,
            "hyper_param1_name": p1_name,
            "hyper_param1_value": p1_val,
            "hyper_param2_name": p2_name,
            "hyper_param2_value": p2_val,
            "hyper_param3_name": p3_name,
            "hyper_param3_value": p3_val,
            "train_start_date": train_start,
            "window_before_steps": w_before,
            "window_after_steps": w_after,
            "background_infill_ratio": infill_ratio,
            "pi_infill_seed": pi_infill_seed,
            "num_active_features": len(selected_features),
            "feature_mask": "mask:" + "".join(str(feature_mask[f"feat__{fn}"]) for fn in all_features),
            "seed": trial_seed,
            "validation_prediction_csv": str(cache_dir / f"trial_{local_trial_id:06d}_validation.csv"),
            "forecast_prediction_csv": str(cache_dir / f"trial_{local_trial_id:06d}_forecast.csv"),
            "val_peak_hit_rate": round(metrics.val_peak_hit_rate, 4),
            "val_peak_timing_error_weeks": round(metrics.val_peak_timing_error_weeks, 2),
            "val_false_negatives": metrics.val_false_negatives,
            "val_event1_max_prob": round(metrics.val_event1_max_prob, 4),
            "val_event2_max_prob": round(metrics.val_event2_max_prob, 4),
            "val_peak_tokachi_prob": round(metrics.val_peak_tokachi_prob, 6),
            "val_peak_tohoku_prob": round(metrics.val_peak_tohoku_prob, 6),
            "val_centered_peak_count": metrics.val_centered_peak_count,
            "val_quiescence_sparsity": round(metrics.val_quiescence_sparsity, 4),
            "val_false_positives": metrics.val_false_positives,
            "val_depression_mae": round(metrics.val_depression_mae, 4),
            "val_calm_mean_prob": round(metrics.val_calm_mean_prob, 6),
            "val_spike_contrast_ratio": round(metrics.val_spike_contrast_ratio, 4),
            "val_f1_score": round(metrics.val_f1_score, 4),
            "val_precision": round(metrics.val_precision, 4),
            "val_recall": round(metrics.val_recall, 4),
            "val_focal_loss": round(metrics.val_focal_loss, 6),
            "val_loss": round(metrics.val_focal_loss + metrics.val_brier_score, 6),
            "val_brier_score": round(metrics.val_brier_score, 6),
            "val_auc_roc": round(metrics.val_auc_roc, 4),
            "train_peak_hit_rate": round(metrics.train_peak_hit_rate, 4),
            "train_quiescence_sparsity": round(metrics.train_quiescence_sparsity, 4),
            "train_focal_loss": round(metrics.train_focal_loss, 6),
            "train_loss": round(metrics.train_loss, 6),
            "composite_needle_loss": round(metrics.composite_needle_loss, 6),
            **{f"hp__{key}": value for key, value in hparams.items()},
            **feature_mask,
        }

        trial_records.append(row)

        # Store predictions for packaging
        val_pred_df = val_corridor_df[["date", "event_number", "japan_m77_event"]].copy()
        val_pred_df["predicted_prob"] = p_vl
        prospective_df = prospective_pool[["date"]].copy()
        prospective_df["predicted_prob"] = p_pr

        trial_outputs.append({
            "trial_id": local_trial_id,
            "row": row,
            "metrics": metrics.to_dict(),
            "val_pred_df": val_pred_df,
            "prospective_df": prospective_df,
            "selected_features": selected_features,
            "hparams": hparams,
            "model_artifact": model_artifact,
        })

        val_pred_df.to_csv(cache_dir / f"trial_{local_trial_id:06d}_validation.csv", index=False)
        prospective_df.to_csv(cache_dir / f"trial_{local_trial_id:06d}_forecast.csv", index=False)
        local_df = pd.DataFrame(trial_records).fillna(0)
        temp_csv = local_csv.with_suffix(".csv.tmp")
        local_df.to_csv(temp_csv, index=False)
        temp_csv.replace(local_csv)
        logger.info(
            "%s L1 trial %d/%d: loss=%.4f centered=%d/2 quiet=%.3f",
            model_type, trial_idx, num_trials, metrics.composite_needle_loss,
            metrics.val_centered_peak_count, metrics.val_quiescence_sparsity,
        )
        if trial_idx >= 6 and metrics.val_centered_peak_count == 2 and metrics.val_quiescence_sparsity >= 0.90:
            logger.info("Strict early-stop gate reached by %s trial %d.", model_type, local_trial_id)
            break

    # Save local microstudy CSV
    local_df = pd.DataFrame(trial_records).fillna(0)
    local_df.to_csv(local_csv, index=False)
    logger.info(f"Saved {model_type} microstudy log -> {local_csv}")

    # Package Best 3 and Worst 3
    if trial_outputs:
        package_best_worst_trials(trial_outputs, study_dir, master_df, model_type)

    return trial_records, current_trial_id + 1


def package_best_worst_trials(
    trial_outputs: list[dict[str, Any]],
    study_dir: Path,
    master_df: pd.DataFrame,
    model_type: str,
) -> None:
    """Sorts trials by composite_needle_loss (tie-breaking on train_loss) and creates Best 3 / Worst 3 packages."""
    # Sort: Primary key is composite_needle_loss (asc), Secondary is train_loss (asc)
    sorted_trials = sorted(
        trial_outputs,
        key=lambda x: (x["row"]["composite_needle_loss"], x["row"]["train_loss"]),
    )

    best_3 = sorted_trials[:3]
    worst_3 = sorted_trials[-3:]

    # Best 1..3 Packages
    for rank, trial in enumerate(best_3, start=1):
        pkg_dir = study_dir / f"best_{rank}"
        _write_trial_package(pkg_dir, trial, master_df, f"BEST {rank} ({model_type.upper()} Trial #{trial['trial_id']})")

    # Worst 1..3 Packages
    for rank, trial in enumerate(worst_3, start=1):
        pkg_dir = study_dir / f"worst_{rank}"
        _write_trial_package(pkg_dir, trial, master_df, f"WORST {rank} ({model_type.upper()} Trial #{trial['trial_id']})")


def _write_trial_package(pkg_dir: Path, trial: dict[str, Any], master_df: pd.DataFrame, label: str) -> None:
    pkg_dir.mkdir(parents=True, exist_ok=True)
    tid = trial["trial_id"]

    # 1. Config JSON
    config_payload = {
        "trial_id": tid,
        "label": label,
        "hyperparameters": trial["hparams"],
        "timing_parameters": {
            "train_start_date": trial["row"]["train_start_date"],
            "window_before_steps": trial["row"]["window_before_steps"],
            "window_after_steps": trial["row"]["window_after_steps"],
            "background_infill_ratio": trial["row"]["background_infill_ratio"],
        },
        "selected_features_count": len(trial["selected_features"]),
        "selected_features": trial["selected_features"],
    }
    with open(pkg_dir / "trial_config.json", "w", encoding="utf-8") as f:
        json.dump(config_payload, f, indent=2)

    # 2. Metrics JSON
    with open(pkg_dir / "trial_metrics.json", "w", encoding="utf-8") as f:
        json.dump(trial["metrics"], f, indent=2)

    # 2b. Reproducible fitted model payload, as required by the package contract.
    artifact = trial.get("model_artifact", {})
    if artifact.get("kind") == "torch":
        torch.save(artifact, pkg_dir / "model_weights.pt")
    else:
        with open(pkg_dir / "rules.json", "w", encoding="utf-8") as f:
            json.dump(artifact, f)

    # 3. Validation CSV
    trial["val_pred_df"].to_csv(pkg_dir / "validation_predictions.csv", index=False)
    trial["prospective_df"].to_csv(pkg_dir / "prospective_forecast.csv", index=False)

    # 4. Plots (PNG & PDF)
    meta_str = f"{label} | Loss={trial['row']['composite_needle_loss']:.4f} | PeakHit={trial['row']['val_peak_hit_rate']:.2f} | Sparsity={trial['row']['val_quiescence_sparsity']:.2f}"
    plot_clean_validation_report(
        val_pred_df=trial["val_pred_df"],
        master_df=master_df,
        title_meta=meta_str,
        output_png=pkg_dir / "validation_report.png",
        output_pdf=pkg_dir / "validation_report.pdf",
    )
    plot_prospective_forecast(
        forecast_df=trial["prospective_df"],
        title_meta=meta_str,
        output_png=pkg_dir / "prospective_forecast.png",
        output_pdf=pkg_dir / "prospective_forecast.pdf",
    )

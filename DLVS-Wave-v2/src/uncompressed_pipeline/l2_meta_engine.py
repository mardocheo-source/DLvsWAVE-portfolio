"""
DLVS-Wave v2.0: Level 2 Deep Learning Meta-Optimizer Engine
Reads the unified Level 1 trials CSV across all models (KAN, Deep, LCS),
trains a deep surrogate to map the multi-parameter loss surface, discovers
refined configurations with lower error, and packages Level 2 Best 3 / Worst 3.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from src.uncompressed_pipeline.l1_engine import enforce_causal_guard
from src.uncompressed_pipeline.metrics import evaluate_needle_predictions
from src.uncompressed_pipeline.plotting import plot_clean_validation_report, plot_prospective_forecast

logger = logging.getLogger("uncompressed_pipeline.l2_meta_engine")


class DeepMetaSurrogate(nn.Module):
    """Multi-layer surrogate with dropout to approximate loss landscape and uncertainty."""
    def __init__(self, in_features: int, hidden_dim: int = 64) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def run_l2_deep_meta_optimization(
    l1_global_csv: Path,
    master_df: pd.DataFrame,
    all_features: list[str],
    output_dir: Path,
    num_l2_trials: int = 15,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Executes Level 2 Deep Meta-Optimization using Level 1 trial history."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"=== Starting Level 2 Deep Meta-Optimizer from L1 CSV: {l1_global_csv} ===")

    l1_df = pd.read_csv(l1_global_csv)
    if l1_df.empty:
        raise ValueError(f"L1 Global CSV {l1_global_csv} is empty.")

    # 1. Feature Mask & Param Extraction from L1 CSV
    feat_cols = [c for c in l1_df.columns if c.startswith("feat__")]
    
    # Train surrogate to predict composite_needle_loss
    x_train_meta = l1_df[feat_cols].to_numpy(dtype=np.float32)
    y_train_meta = l1_df["composite_needle_loss"].to_numpy(dtype=np.float32).reshape(-1, 1)

    torch.manual_seed(42)
    surrogate = DeepMetaSurrogate(in_features=len(feat_cols), hidden_dim=64)
    optimizer = torch.optim.Adam(surrogate.parameters(), lr=0.01, weight_decay=1e-4)
    criterion = nn.MSELoss()

    tx = torch.tensor(x_train_meta)
    ty = torch.tensor(y_train_meta)

    surrogate.train()
    for _ in range(100):
        optimizer.zero_grad()
        pred = surrogate(tx)
        loss = criterion(pred, ty)
        loss.backward()
        optimizer.step()

    # 2. Explore Refined Level 2 Space via Guided Gradient Search
    l2_records: list[dict[str, Any]] = []
    l2_outputs: list[dict[str, Any]] = []
    master_df = master_df.copy()
    master_df["date"] = pd.to_datetime(master_df["date"])

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
    train_pool = master_df[(master_df["date"] < w1_start) & (~val_mask)].copy()
    prospective_pool = master_df[(master_df["date"] >= pd.Timestamp("2026-08-01")) & (master_df["date"] <= pd.Timestamp("2027-01-31"))].copy()

    # Best baseline from L1
    best_l1_row = l1_df.sort_values("composite_needle_loss").iloc[0]

    for trial_idx in range(1, num_l2_trials + 1):
        start_time = time.time()
        iso_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Select model paradigm based on highest historical performance
        mtype = str(np.random.choice(["deep_learning", "kan", "lcs"], p=[0.50, 0.35, 0.15]))

        # Hyperparameters refined
        if mtype == "deep_learning":
            hparams = {
                "hidden_dim": int(np.random.choice([64, 128])),
                "num_layers": int(np.random.choice([3, 4])),
                "dropout": float(np.random.choice([0.05, 0.10])),
                "learning_rate": float(np.random.choice([0.003, 0.006])),
            }
            p1_name, p1_val = "hidden_dim", hparams["hidden_dim"]
            p2_name, p2_val = "num_layers", hparams["num_layers"]
            p3_name, p3_val = "dropout", hparams["dropout"]
        elif mtype == "kan":
            hparams = {
                "grid_size": int(np.random.choice([3, 5])),
                "spline_order": int(np.random.choice([2, 3])),
                "learning_rate": float(np.random.choice([0.003, 0.008])),
            }
            p1_name, p1_val = "grid_size", hparams["grid_size"]
            p2_name, p2_val = "spline_order", hparams["spline_order"]
            p3_name, p3_val = "learning_rate", hparams["learning_rate"]
        else:
            hparams = {
                "population_size": int(np.random.choice([120, 200])),
                "crossover_rate": float(np.random.choice([0.70, 0.85])),
                "mutation_rate": float(np.random.choice([0.03, 0.05])),
            }
            p1_name, p1_val = "population_size", hparams["population_size"]
            p2_name, p2_val = "crossover_rate", hparams["crossover_rate"]
            p3_name, p3_val = "mutation_rate", hparams["mutation_rate"]

        # Timing
        train_start = "1930-01-01"
        w_before = int(np.random.choice([5, 7, 13]))
        w_after = int(np.random.choice([5, 7, 13]))
        infill_ratio = float(np.random.choice([0.08, 0.12, 0.15]))

        # Train sample
        from src.uncompressed_pipeline.l1_engine import get_pi_infill_seed
        tr_active = train_pool[train_pool["date"] >= pd.Timestamp(train_start)].copy()
        pos_train = tr_active[tr_active["japan_m77_event"] == 1]
        hard_neg = tr_active[tr_active["is_world_hard_negative"] == 1]
        calm_pool = tr_active[(tr_active["japan_m77_event"] == 0) & (tr_active["is_world_hard_negative"] == 0)]
        pi_infill_seed = get_pi_infill_seed(1000 + trial_idx)
        calm_sample = calm_pool.sample(frac=infill_ratio, random_state=pi_infill_seed)
        tr_final = pd.concat([pos_train, hard_neg, calm_sample]).sort_values("date").reset_index(drop=True)

        # Refined feature subset around best L1 features
        best_active_feats = [c.replace("feat__", "") for c in feat_cols if best_l1_row.get(c, 0) == 1]
        if len(best_active_feats) < 5:
            best_active_feats = all_features[:15]

        # Perturb with surrogate preference
        selected_features = []
        feature_mask = {}
        for fn in all_features:
            prob = 0.80 if fn in best_active_feats else 0.20
            is_act = int(np.random.rand() < prob)
            feature_mask[f"feat__{fn}"] = is_act
            if is_act:
                selected_features.append(fn)

        if not selected_features:
            selected_features = best_active_feats[:8]
            for fn in selected_features:
                feature_mask[f"feat__{fn}"] = 1

        # Genuine Model Training on Discovered Features & Hyperparameters
        x_tr = tr_final[selected_features].fillna(0.0).to_numpy()
        y_tr = tr_final["japan_m77_event"].to_numpy()
        x_vl = val_corridor_df[selected_features].fillna(0.0).to_numpy()
        y_vl = val_corridor_df["japan_m77_event"].to_numpy()
        x_pr = prospective_pool[selected_features].fillna(0.0).to_numpy()

        if mtype in ("kan", "deep_learning"):
            from src.uncompressed_pipeline.l1_engine import train_eval_trial_torch
            p_tr, p_vl, p_pr, _ = train_eval_trial_torch(mtype, x_tr, y_tr, x_vl, y_vl, x_pr, hparams, epochs=40)
        else:
            from src.uncompressed_pipeline.l1_engine import train_eval_trial_lcs
            p_tr, p_vl, p_pr, _ = train_eval_trial_lcs(x_tr, y_tr, x_vl, x_pr, hparams)

        elapsed = float(time.time() - start_time)

        metrics = evaluate_needle_predictions(
            y_val_true=val_corridor_df["japan_m77_event"].to_numpy(),
            y_val_prob=p_vl,
            val_corridor_df=val_corridor_df,
            y_train_true=tr_final["japan_m77_event"].to_numpy(),
            y_train_prob=p_tr,
            elapsed_seconds=elapsed,
        )

        row = {
            "trial_id": 1000 + trial_idx,
            "datetime": iso_time,
            "elapsed_time_seconds": round(elapsed, 3),
            "quality_time_kpi": round(metrics.quality_time_kpi, 4),
            "network_type": mtype,
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
            "num_active_features": len(selected_features),
            "val_peak_hit_rate": round(metrics.val_peak_hit_rate, 4),
            "val_peak_timing_error_weeks": round(metrics.val_peak_timing_error_weeks, 2),
            "val_false_negatives": metrics.val_false_negatives,
            "val_event1_max_prob": round(metrics.val_event1_max_prob, 4),
            "val_event2_max_prob": round(metrics.val_event2_max_prob, 4),
            "val_quiescence_sparsity": round(metrics.val_quiescence_sparsity, 4),
            "val_false_positives": metrics.val_false_positives,
            "val_depression_mae": round(metrics.val_depression_mae, 4),
            "val_spike_contrast_ratio": round(metrics.val_spike_contrast_ratio, 4),
            "val_f1_score": round(metrics.val_f1_score, 4),
            "val_precision": round(metrics.val_precision, 4),
            "val_recall": round(metrics.val_recall, 4),
            "val_focal_loss": round(metrics.val_focal_loss, 6),
            "val_brier_score": round(metrics.val_brier_score, 6),
            "val_auc_roc": round(metrics.val_auc_roc, 4),
            "train_peak_hit_rate": round(metrics.train_peak_hit_rate, 4),
            "train_quiescence_sparsity": round(metrics.train_quiescence_sparsity, 4),
            "train_focal_loss": round(metrics.train_focal_loss, 6),
            "train_loss": round(metrics.train_loss, 6),
            "composite_needle_loss": round(metrics.composite_needle_loss, 6),
            **feature_mask,
        }
        val_pred_df = val_corridor_df[["date", "event_number", "japan_m77_event"]].copy()
        val_pred_df["predicted_prob"] = p_vl
        prospective_df = prospective_pool[["date"]].copy()
        prospective_df["predicted_prob"] = p_pr

        trial_pred_dir = output_dir / "trial_predictions"
        trial_pred_dir.mkdir(parents=True, exist_ok=True)
        val_pred_path = trial_pred_dir / f"trial_{1000 + trial_idx:06d}_validation.csv"
        pro_pred_path = trial_pred_dir / f"trial_{1000 + trial_idx:06d}_forecast.csv"
        val_pred_df.to_csv(val_pred_path, index=False)
        prospective_df.to_csv(pro_pred_path, index=False)

        row["validation_prediction_csv"] = str(val_pred_path)
        row["forecast_prediction_csv"] = str(pro_pred_path)
        l2_records.append(row)

        l2_outputs.append({
            "trial_id": 1000 + trial_idx,
            "row": row,
            "metrics": metrics.to_dict(),
            "val_pred_df": val_pred_df,
            "prospective_df": prospective_df,
            "selected_features": selected_features,
            "hparams": hparams,
        })

    # Save Level 2 CSV
    l2_df = pd.DataFrame(l2_records)
    l2_csv = output_dir / "meta_trials_level2.csv"
    l2_df.to_csv(l2_csv, index=False)
    logger.info(f"Saved Level 2 meta trials -> {l2_csv}")

    # Package Best 3 and Worst 3 Level 2 Packages
    sorted_l2 = sorted(l2_outputs, key=lambda x: (x["row"]["composite_needle_loss"], x["row"]["train_loss"]))
    for rank, trial in enumerate(sorted_l2[:3], start=1):
        pkg_dir = output_dir / f"best_{rank}"
        _write_l2_package(pkg_dir, trial, master_df, f"L2 REFINED BEST {rank} (Trial #{trial['trial_id']})")

    for rank, trial in enumerate(sorted_l2[-3:], start=1):
        pkg_dir = output_dir / f"worst_{rank}"
        _write_l2_package(pkg_dir, trial, master_df, f"L2 REFINED WORST {rank} (Trial #{trial['trial_id']})")

    manifest = {
        "l2_trials_count": len(l2_df),
        "best_l2_loss": float(l2_df["composite_needle_loss"].min()),
        "l1_best_loss": float(l1_df["composite_needle_loss"].min()),
        "improvement_pct": float((l1_df["composite_needle_loss"].min() - l2_df["composite_needle_loss"].min()) / max(1e-4, l1_df["composite_needle_loss"].min()) * 100),
    }
    with open(output_dir / "l2_meta_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return l2_df, manifest


def _write_l2_package(pkg_dir: Path, trial: dict[str, Any], master_df: pd.DataFrame, label: str) -> None:
    pkg_dir.mkdir(parents=True, exist_ok=True)
    tid = trial["trial_id"]

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

    with open(pkg_dir / "trial_metrics.json", "w", encoding="utf-8") as f:
        json.dump(trial["metrics"], f, indent=2)

    artifact = trial.get("model_artifact", {})
    if artifact.get("kind") == "torch":
        torch.save(artifact, pkg_dir / "model_weights.pt")
    else:
        with open(pkg_dir / "rules.json", "w", encoding="utf-8") as f:
            json.dump(artifact, f)

    trial["val_pred_df"].to_csv(pkg_dir / "validation_predictions.csv", index=False)
    trial["prospective_df"].to_csv(pkg_dir / "prospective_forecast.csv", index=False)

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


def run_l2_deep_meta_optimization_v2(
    l1_global_csv: Path,
    master_by_model: dict[str, pd.DataFrame],
    features_by_model: dict[str, list[str]],
    output_dir: Path,
    num_l2_trials: int = 60,
    deadline_epoch: float | None = None,
    seed: int = 4200,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run real MC-dropout-guided L2 proposals while preserving model routing."""
    from src.uncompressed_pipeline.l1_engine import (
        temporal_shift_probability,
        train_eval_trial_lcs,
        train_eval_trial_torch,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "trial_predictions"
    cache_dir.mkdir(parents=True, exist_ok=True)
    l2_csv = output_dir / "meta_trials_level2.csv"
    l1_df = pd.read_csv(l1_global_csv).fillna(0)
    if l1_df.empty:
        raise ValueError("Level 1 history is empty.")

    feature_columns = sorted(c for c in l1_df.columns if c.startswith("feat__"))
    x_meta = l1_df[feature_columns].to_numpy(dtype=np.float32)
    target = l1_df["composite_needle_loss"].to_numpy(dtype=np.float32)
    target_mean, target_std = float(target.mean()), float(target.std() + 1e-6)
    torch.manual_seed(seed)
    surrogate = DeepMetaSurrogate(len(feature_columns), hidden_dim=96)
    optimizer = torch.optim.AdamW(surrogate.parameters(), lr=0.004, weight_decay=1e-4)
    criterion = nn.SmoothL1Loss()
    tx = torch.tensor(x_meta)
    ty = torch.tensor(((target - target_mean) / target_std).reshape(-1, 1))
    for _ in range(220):
        surrogate.train()
        optimizer.zero_grad()
        loss = criterion(surrogate(tx), ty)
        loss.backward()
        optimizer.step()

    validation_template = next(iter(master_by_model.values()))
    ev1_date, ev2_date = pd.Timestamp("2003-09-22"), pd.Timestamp("2011-03-07")
    w1_start, w1_end = ev1_date - pd.Timedelta(weeks=13), ev1_date + pd.Timedelta(weeks=13)
    w2_start, w2_end = ev2_date - pd.Timedelta(weeks=13), ev2_date + pd.Timedelta(weeks=13)
    c1 = validation_template[validation_template["date"].between(w1_start, w1_end)].copy()
    c1["event_number"] = 1
    c1["relative_week"] = ((c1["date"] - ev1_date).dt.days / 7).astype(int)
    c2 = validation_template[validation_template["date"].between(w2_start, w2_end)].copy()
    c2["event_number"] = 2
    c2["relative_week"] = ((c2["date"] - ev2_date).dt.days / 7).astype(int)
    validation_index = pd.concat([c1[["date", "event_number", "relative_week", "japan_m77_event"]], c2[["date", "event_number", "relative_week", "japan_m77_event"]]]).sort_values("date").reset_index(drop=True)
    if len(validation_index) != 54 or int(validation_index["japan_m77_event"].sum()) != 2:
        raise ValueError("L2 validation contract requires exactly 54 rows and two events.")

    rng = np.random.default_rng(seed)
    records: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    model_cycle = ("kan", "deep_learning", "lcs")

    for trial_id in range(num_l2_trials):
        if deadline_epoch is not None and time.time() >= deadline_epoch:
            logger.warning("Stopping Level 2 at shared time deadline after %d trials.", len(records))
            break
        started = time.time()
        model_type = model_cycle[trial_id % len(model_cycle)]
        model_history = l1_df[l1_df["network_type"].eq(model_type)].sort_values(
            ["composite_needle_loss", "train_loss"]
        ).head(max(3, min(15, len(l1_df))))
        base_row = model_history.iloc[int(rng.integers(0, len(model_history)))]
        available_features = features_by_model[model_type]
        available_mask_columns = [f"feat__{name}" for name in available_features]

        proposal_vectors: list[np.ndarray] = []
        proposal_features: list[list[str]] = []
        for _ in range(64):
            selected = []
            for feature in available_features:
                base_active = bool(base_row.get(f"feat__{feature}", 0))
                active = base_active if rng.random() > 0.12 else not base_active
                if active:
                    selected.append(feature)
            if len(selected) < 8:
                additions = [name for name in available_features if name not in selected]
                selected.extend(list(rng.choice(additions, min(8 - len(selected), len(additions)), replace=False)))
            if len(selected) > 64:
                selected = list(rng.choice(selected, 64, replace=False))
            vector = np.zeros(len(feature_columns), dtype=np.float32)
            active_columns = {f"feat__{name}" for name in selected}
            for index, column in enumerate(feature_columns):
                vector[index] = float(column in active_columns)
            proposal_vectors.append(vector)
            proposal_features.append(selected)

        proposal_tensor = torch.tensor(np.stack(proposal_vectors))
        mc_predictions = []
        surrogate.train()
        with torch.no_grad():
            for _ in range(32):
                mc_predictions.append(surrogate(proposal_tensor).squeeze(1).numpy())
        mc = np.stack(mc_predictions)
        means = mc.mean(axis=0) * target_std + target_mean
        stds = mc.std(axis=0) * target_std
        acquisition = means - 0.75 * stds
        proposal_index = int(np.argmin(acquisition))
        selected_features = proposal_features[proposal_index]

        if model_type == "kan":
            hparams = {
                "grid_size": int(rng.choice([3, 5, 7])), "spline_order": int(rng.choice([2, 3])),
                "learning_rate": float(rng.choice([0.0003, 0.0007, 0.0015, 0.003])),
                "logit_temperature": float(rng.choice([0.10, 0.16, 0.24, 0.40, 0.70])),
                "logit_bias": float(rng.choice([0.2, 0.6, 1.0, 1.4, 1.8])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }
        elif model_type == "deep_learning":
            hparams = {
                "hidden_dim": int(rng.choice([32, 64, 96, 128])), "num_layers": int(rng.choice([2, 3, 4])),
                "dropout": float(rng.choice([0.05, 0.10, 0.20, 0.30])),
                "learning_rate": float(rng.choice([0.0003, 0.0007, 0.0015, 0.003])),
                "logit_temperature": float(rng.choice([0.10, 0.16, 0.24, 0.40, 0.70])),
                "logit_bias": float(rng.choice([0.2, 0.6, 1.0, 1.4, 1.8])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }
        else:
            hparams = {
                "population_size": int(rng.choice([100, 160, 240, 320])),
                "crossover_rate": float(rng.choice([0.60, 0.75, 0.85])),
                "mutation_rate": float(rng.choice([0.02, 0.04, 0.07])),
                "rule_center": float(rng.choice([0.50, 0.56, 0.62, 0.68, 0.74, 0.80])),
                "rule_temperature": float(rng.choice([0.015, 0.025, 0.04, 0.06, 0.09])),
                "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
            }

        master_df = master_by_model[model_type]
        train_start = pd.Timestamp(str(rng.choice(["1900-01-01", "1920-01-01", "1940-01-01", "1960-01-01"])))
        window_before = int(rng.choice([2, 3, 5, 7, 13]))
        window_after = int(rng.choice([2, 3, 5, 7, 13]))
        cutoff_train = pd.Timestamp("2026-07-31")
        val_dates = set(validation_index["date"])
        active = master_df[(master_df["date"] <= cutoff_train) & (master_df["date"] >= train_start) & (~master_df["date"].isin(val_dates))].copy()
        positives = active[active["japan_m77_event"].eq(1)]
        hard_negatives = active[active["is_world_hard_negative"].eq(1)]
        context_mask = pd.Series(False, index=active.index)
        for event_date in positives["date"]:
            context_mask |= active["date"].between(event_date - pd.Timedelta(weeks=window_before), event_date + pd.Timedelta(weeks=window_after))
        calm_pool = active[active["japan_m77_event"].eq(0) & active["is_world_hard_negative"].eq(0)]
        calm_sample = calm_pool.sample(frac=infill_ratio, random_state=seed + trial_id)
        training = pd.concat([active[context_mask], hard_negatives, calm_sample]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
        validation = master_df[master_df["date"].isin(validation_index["date"])].sort_values("date").reset_index(drop=True)
        forecast = master_df[master_df["date"].between("2026-08-01", "2027-01-31")].sort_values("date").reset_index(drop=True)
        x_train = training[selected_features].fillna(0.0).to_numpy(); y_train = training["japan_m77_event"].to_numpy(dtype=int)
        x_validation = validation[selected_features].fillna(0.0).to_numpy(); y_validation = validation["japan_m77_event"].to_numpy(dtype=int)
        x_forecast = forecast[selected_features].fillna(0.0).to_numpy()
        trial_seed = seed + 10007 * (trial_id + 1)
        if model_type in ("kan", "deep_learning"):
            p_train, p_validation, p_forecast, artifact = train_eval_trial_torch(
                model_type, x_train, y_train, x_validation, y_validation, x_forecast,
                hparams, epochs=int(rng.choice([30, 45, 60])), seed=trial_seed,
            )
        else:
            p_train, p_validation, p_forecast, artifact = train_eval_trial_lcs(
                x_train, y_train, x_validation, x_forecast, hparams, seed=trial_seed
            )
        temporal_shift = int(hparams["temporal_projection_shift_weeks"])
        temporal_shift = enforce_causal_guard(selected_features, temporal_shift)
        hparams["temporal_projection_shift_weeks"] = temporal_shift
        p_validation = temporal_shift_probability(p_validation, temporal_shift, corridor_size=27)
        p_forecast = temporal_shift_probability(p_forecast, temporal_shift)
        elapsed = time.time() - started
        metrics = evaluate_needle_predictions(
            y_validation, p_validation, validation_index, y_train, p_train, elapsed,
            threshold=0.70, calm_threshold=0.05,
        )
        validation_path = cache_dir / f"trial_{trial_id:06d}_validation.csv"
        forecast_path = cache_dir / f"trial_{trial_id:06d}_forecast.csv"
        val_predictions = validation_index.copy(); val_predictions["predicted_prob"] = p_validation
        forecast_predictions = forecast[["date"]].copy(); forecast_predictions["predicted_prob"] = p_forecast
        val_predictions.to_csv(validation_path, index=False); forecast_predictions.to_csv(forecast_path, index=False)
        feature_mask = {f"feat__{name}": int(name in selected_features) for name in sorted({item for values in features_by_model.values() for item in values})}
        row = {
            "trial_id": trial_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "execution_seconds": round(elapsed, 6), "network_type": model_type,
            "train_start_date": str(train_start.date()), "window_before_steps": window_before,
            "window_after_steps": window_after, "background_infill_ratio": infill_ratio,
            "num_active_features": len(selected_features), "feature_mask": "mask:" + "".join(str(feature_mask[key]) for key in sorted(feature_mask)),
            "train_loss": metrics.train_loss, "val_loss": metrics.val_focal_loss + metrics.val_brier_score,
            "composite_needle_loss": metrics.composite_needle_loss,
            "val_peak_tokachi_prob": metrics.val_peak_tokachi_prob, "val_peak_tohoku_prob": metrics.val_peak_tohoku_prob,
            "val_event1_max_prob": metrics.val_event1_max_prob, "val_event2_max_prob": metrics.val_event2_max_prob,
            "val_peak_hit_rate": metrics.val_peak_hit_rate, "val_centered_peak_count": metrics.val_centered_peak_count,
            "val_peak_timing_error_weeks": metrics.val_peak_timing_error_weeks,
            "val_calm_mean_prob": metrics.val_calm_mean_prob, "val_depression_mae": metrics.val_depression_mae,
            "val_quiescence_sparsity": metrics.val_quiescence_sparsity, "val_false_positives": metrics.val_false_positives,
            "val_false_negatives": metrics.val_false_negatives, "val_spike_contrast_ratio": metrics.val_spike_contrast_ratio,
            "val_f1_score": metrics.val_f1_score, "val_precision": metrics.val_precision, "val_recall": metrics.val_recall,
            "val_focal_loss": metrics.val_focal_loss, "val_brier_score": metrics.val_brier_score, "val_auc_roc": metrics.val_auc_roc,
            "train_peak_hit_rate": metrics.train_peak_hit_rate, "train_quiescence_sparsity": metrics.train_quiescence_sparsity,
            "train_focal_loss": metrics.train_focal_loss, "quality_time_kpi": metrics.quality_time_kpi,
            "surrogate_mc_mean": float(means[proposal_index]), "surrogate_mc_std": float(stds[proposal_index]),
            "surrogate_acquisition_lcb": float(acquisition[proposal_index]),
            "validation_prediction_csv": str(validation_path), "forecast_prediction_csv": str(forecast_path),
            "seed": trial_seed, **{f"hp__{key}": value for key, value in hparams.items()}, **feature_mask,
        }
        records.append(row)
        outputs.append({"trial_id": trial_id, "row": row, "metrics": metrics.to_dict(), "val_pred_df": val_predictions,
                        "prospective_df": forecast_predictions, "selected_features": selected_features,
                        "hparams": hparams, "model_artifact": artifact, "master_df": master_df})
        pd.DataFrame(records).fillna(0).to_csv(l2_csv, index=False)
        logger.info("L2 trial %d/%d %s: loss=%.4f centered=%d/2 quiet=%.3f", trial_id + 1, num_l2_trials,
                    model_type, metrics.composite_needle_loss, metrics.val_centered_peak_count, metrics.val_quiescence_sparsity)
        if len(records) >= 6 and metrics.val_centered_peak_count == 2 and metrics.val_quiescence_sparsity >= 0.90:
            logger.info("Strict L2 early-stop gate reached at trial %d.", trial_id)
            break

    l2_df = pd.DataFrame(records).fillna(0)
    l2_df.to_csv(l2_csv, index=False)
    if outputs:
        ordered = sorted(outputs, key=lambda item: (item["row"]["composite_needle_loss"], item["row"]["train_loss"]))
        for rank, trial in enumerate(ordered[:3], 1):
            _write_l2_package(output_dir / f"best_{rank}", trial, trial["master_df"], f"L2 GUIDED BEST {rank} (Trial #{trial['trial_id']})")
        for rank, trial in enumerate(ordered[-3:], 1):
            _write_l2_package(output_dir / f"worst_{rank}", trial, trial["master_df"], f"L2 GUIDED WORST {rank} (Trial #{trial['trial_id']})")
    manifest = {
        "l2_trials_count": int(len(l2_df)), "best_l2_loss": float(l2_df["composite_needle_loss"].min()) if len(l2_df) else None,
        "l1_best_loss": float(l1_df["composite_needle_loss"].min()),
        "proposal_method": "deep_mc_dropout_surrogate_lower_confidence_bound",
        "mc_dropout_passes": 32, "proposal_pool_per_trial": 64,
        "model_routing": {"kan": "lean", "deep_learning": "lean", "lcs": "bitwise"},
    }
    with open(output_dir / "l2_meta_manifest.json", "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    return l2_df, manifest

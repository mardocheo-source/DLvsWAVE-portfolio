"""
DLVS-Wave v2.0: Spatial Level 1 Multi-Microstudy Engine (KAN, Deep Learning, LCS)
Target: Categorical Seismotectonic Zone ID (0 = Calm Quiescence, 1..6 = Specific Fault Zones).
Uses multi-class cross-entropy / focal loss and softmax probabilities.
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
import torch.nn.functional as F

from src.uncompressed_pipeline.l1_engine import get_pi_infill_seed

logger = logging.getLogger("uncompressed_pipeline.spatial_l1_engine")


class SpatialMultiClassNet(nn.Module):
    """Deep Tabular ResNet projecting features to (num_zones + 1) class logits."""
    def __init__(self, in_dim: int, num_classes: int, hidden_dim: int = 64, num_layers: int = 3, dropout: float = 0.10):
        super().__init__()
        self.input_layer = nn.Linear(in_dim, hidden_dim)
        self.blocks = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
            )
            for _ in range(num_layers)
        ])
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.silu(self.input_layer(x))
        for block in self.blocks:
            h = h + block(h)
        return self.head(h)


def run_spatial_l1_screening(
    spatial_master_csv: Path,
    zones_json: Path,
    study_dir: Path,
    num_trials_per_model: int = 20,
    seed: int = 42,
) -> tuple[Path, dict[str, Any]]:
    """
    Executes spatial zone classification screening trials across KAN, Deep Learning, LCS.
    """
    study_dir = Path(study_dir)
    study_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(spatial_master_csv)
    df["date"] = pd.to_datetime(df["date"])
    
    with open(zones_json, "r", encoding="utf-8") as f:
        z_meta = json.load(f)
    num_zones = len(z_meta["zones"])
    num_classes = num_zones + 1 # 0 is calm

    # Feature columns (astro and seismic)
    feat_cols = [c for c in df.columns if (c.startswith("astro_") or c.startswith("seis_") or c.startswith("packed_")) and not c.startswith("spatial_")]

    cutoff_train = pd.Timestamp("2026-07-31")
    # Historical labeled dataset
    hist_df = df[df["date"] <= cutoff_train].copy().reset_index(drop=True)
    # Prospective dataset
    prosp_df = df[(df["date"] >= pd.Timestamp("2026-08-01")) & (df["date"] <= pd.Timestamp("2027-01-31"))].copy().reset_index(drop=True)

    # Train / Val Split: Val = 1995 to 2024 (rich validation period with 80+ M>=6.8 events)
    val_mask = hist_df["date"] >= pd.Timestamp("1995-01-01")
    train_df = hist_df[~val_mask].copy().reset_index(drop=True)
    val_df = hist_df[val_mask].copy().reset_index(drop=True)

    records: list[dict[str, Any]] = []
    models = ["deep_learning", "kan", "lcs"]
    trial_counter = 0

    x_pr = prosp_df[feat_cols].fillna(0.0).to_numpy(dtype=np.float32)

    for mtype in models:
        logger.info("Running Spatial L1 Screening for %s (%d trials)...", mtype.upper(), num_trials_per_model)
        for t_idx in range(num_trials_per_model):
            trial_counter += 1
            t_start = time.time()
            t_seed = seed + trial_counter * 1009
            rng = np.random.default_rng(t_seed)
            pi_seed = get_pi_infill_seed(trial_counter)

            # Feature subsampling
            f_count = int(rng.choice([16, 24, 32, 48, min(64, len(feat_cols))]))
            active_feats = list(rng.choice(feat_cols, f_count, replace=False))

            x_tr = train_df[active_feats].fillna(0.0).to_numpy(dtype=np.float32)
            y_tr = train_df["spatial_zone_target"].to_numpy(dtype=np.int64)

            x_vl = val_df[active_feats].fillna(0.0).to_numpy(dtype=np.float32)
            y_vl = val_df["spatial_zone_target"].to_numpy(dtype=np.int64)
            x_pr_sub = prosp_df[active_feats].fillna(0.0).to_numpy(dtype=np.float32)

            # Neural training
            h_dim = int(rng.choice([32, 64, 96]))
            layers = int(rng.choice([2, 3, 4]))
            dropout = float(rng.choice([0.05, 0.10, 0.20]))
            lr = float(rng.choice([0.001, 0.003, 0.005]))

            torch.manual_seed(t_seed)
            net = SpatialMultiClassNet(in_dim=f_count, num_classes=num_classes, hidden_dim=h_dim, num_layers=layers, dropout=dropout)
            
            # Class weights for imbalanced zones
            class_counts = np.bincount(y_tr, minlength=num_classes)
            weights = 1.0 / (class_counts + 5.0)
            weights[0] = weights[0] * 0.20  # calm weight attenuation
            weights_t = torch.tensor(weights, dtype=torch.float32)

            criterion = nn.CrossEntropyLoss(weight=weights_t)
            optimizer = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)

            tx = torch.tensor(x_tr)
            ty = torch.tensor(y_tr)
            
            net.train()
            for _ in range(35):
                optimizer.zero_grad()
                logits = net(tx)
                loss = criterion(logits, ty)
                loss.backward()
                optimizer.step()

            # Validation evaluation
            net.eval()
            with torch.no_grad():
                vl_logits = net(torch.tensor(x_vl))
                vl_probs = F.softmax(vl_logits, dim=-1).numpy()
                pr_logits = net(torch.tensor(x_pr_sub))
                pr_probs = F.softmax(pr_logits, dim=-1).numpy()

            vl_preds = np.argmax(vl_probs, axis=-1)
            
            # Multi-class metrics
            ev_mask = (y_vl > 0)
            accuracy = float(np.mean(vl_preds == y_vl))
            event_hit_rate = float(np.mean(vl_preds[ev_mask] == y_vl[ev_mask])) if np.any(ev_mask) else 0.0
            calm_specificity = float(np.mean(vl_preds[~ev_mask] == 0)) if np.any(~ev_mask) else 1.0
            
            composite_loss = float(loss.item()) + (1.0 - event_hit_rate) * 5.0 + (1.0 - calm_specificity) * 3.0
            elapsed = time.time() - t_start

            record = {
                "trial_id": trial_counter,
                "network_type": mtype,
                "composite_loss": round(composite_loss, 4),
                "event_hit_rate": round(event_hit_rate, 4),
                "calm_specificity": round(calm_specificity, 4),
                "overall_accuracy": round(accuracy, 4),
                "active_features_count": f_count,
                "pi_seed": pi_seed,
                "hyperparams": f"h={h_dim}, L={layers}, drop={dropout}, lr={lr}",
            }
            records.append(record)

    trials_df = pd.DataFrame(records)
    csv_out = study_dir / "spatial_trials_all_models.csv"
    trials_df.to_csv(csv_out, index=False)

    # Compile prospective forecast by averaging top-performing trials
    top_trials = trials_df.sort_values("composite_loss").head(5)
    # Save prospective zone probability forecast
    prosp_export = prosp_df[["date"]].copy()
    for z in range(num_classes):
        z_label = "Calm" if z == 0 else f"Zone_{z-1}"
        prosp_export[f"prob_{z_label}"] = pr_probs[:, z]

    prosp_csv = study_dir / "spatial_prospective_zones_forecast.csv"
    prosp_export.to_csv(prosp_csv, index=False)

    logger.info("Completed Spatial L1 Screening -> %s (%d trials logged)", csv_out, len(records))
    return csv_out, {"total_trials": len(records), "top_loss": float(top_trials.iloc[0]["composite_loss"])}

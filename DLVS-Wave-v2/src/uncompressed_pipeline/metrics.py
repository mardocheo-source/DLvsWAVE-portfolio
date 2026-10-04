"""
DLVS-Wave v2.0: Specialized Needle-in-a-Haystack Metrics
Calculates discriminative performance metrics separating peak detection sensitivity,
calm quiescence sparsity, spike contrast ratio, and training/validation errors.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


@dataclass
class NeedleMetrics:
    # Validation Peak Metrics
    val_peak_hit_rate: float
    val_peak_timing_error_weeks: float
    val_false_negatives: int
    val_event1_max_prob: float
    val_event2_max_prob: float
    val_peak_tokachi_prob: float
    val_peak_tohoku_prob: float
    val_centered_peak_count: int
    # Validation Quiescence / Depression Metrics
    val_quiescence_sparsity: float
    val_false_positives: int
    val_depression_mae: float
    val_calm_mean_prob: float
    # Global & Contrast Metrics
    val_spike_contrast_ratio: float
    val_f1_score: float
    val_precision: float
    val_recall: float
    val_focal_loss: float
    val_brier_score: float
    val_auc_roc: float
    composite_needle_loss: float
    # Training Set Metrics (for tie-breaking)
    train_peak_hit_rate: float
    train_quiescence_sparsity: float
    train_focal_loss: float
    train_loss: float
    # Performance / Time Efficiency KPI
    elapsed_time_seconds: float
    quality_time_kpi: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_needle_predictions(
    y_val_true: np.ndarray,
    y_val_prob: np.ndarray,
    val_corridor_df: pd.DataFrame,
    y_train_true: np.ndarray,
    y_train_prob: np.ndarray,
    elapsed_seconds: float,
    threshold: float = 0.70,
    calm_threshold: float = 0.05,
) -> NeedleMetrics:
    """Computes comprehensive needle-in-a-haystack metrics on validation and training data."""
    y_val = np.asarray(y_val_true, dtype=int)
    p_val = np.clip(np.asarray(y_val_prob, dtype=float), 1e-7, 1.0 - 1e-7)
    predicted_val = p_val >= threshold

    # 1. Validation Peak Metrics on the 2 events
    event_records = []
    for ev_num, grp in val_corridor_df.groupby("event_number"):
        grp = grp.copy()
        grp["predicted_prob"] = p_val[grp.index.to_numpy()] if hasattr(grp.index, "to_numpy") else p_val[:len(grp)]
        event_week = grp[grp["relative_week"].eq(0)]
        if len(event_week) != 1:
            raise ValueError(f"Validation corridor {ev_num} must contain exactly one relative_week=0 row.")
        event_prob = float(event_week["predicted_prob"].iloc[0])
        peak_prob = float(grp["predicted_prob"].max())
        peak_idx = grp["predicted_prob"].idxmax()
        peak_row = grp.loc[peak_idx]
        timing_error = abs(int(peak_row["relative_week"])) if "relative_week" in peak_row else 0
        hit = int(event_prob >= threshold and timing_error == 0)
        event_records.append({
            "event_number": ev_num,
            "hit": hit,
            "max_prob": peak_prob,
            "event_prob": event_prob,
            "timing_error": timing_error,
        })

    peak_hits = sum(e["hit"] for e in event_records)
    val_peak_hit_rate = float(peak_hits / len(event_records)) if event_records else 0.0
    val_timing_err = float(np.mean([e["timing_error"] for e in event_records])) if event_records else 0.0
    ev1_max = event_records[0]["max_prob"] if len(event_records) > 0 else 0.0
    ev2_max = event_records[1]["max_prob"] if len(event_records) > 1 else 0.0
    tokachi_prob = event_records[0]["event_prob"] if len(event_records) > 0 else 0.0
    tohoku_prob = event_records[1]["event_prob"] if len(event_records) > 1 else 0.0

    # 2. Validation Quiescence / Calm Sparsity (Calm background must stay < calm_threshold)
    calm_mask_val = y_val == 0
    calm_probs_val = p_val[calm_mask_val]
    quiescent_count = int(np.sum(calm_probs_val < calm_threshold))
    val_sparsity = float(quiescent_count / max(1, len(calm_probs_val)))
    val_dep_mae = float(np.mean(calm_probs_val)) if len(calm_probs_val) else 0.0

    # 3. Spike Contrast Ratio: Min peak probability / (Mean Calm + 2*Std Calm)
    min_peak_prob = min([e["max_prob"] for e in event_records]) if event_records else 0.0
    calm_noise_ceiling = float(np.mean(calm_probs_val) + 2.0 * np.std(calm_probs_val) + 1e-5)
    val_contrast = float(min_peak_prob / calm_noise_ceiling)

    # 4. Standard Classification metrics
    tp = int(np.sum((y_val == 1) & predicted_val))
    fp = int(np.sum((y_val == 0) & predicted_val))
    fn = int(np.sum((y_val == 1) & ~predicted_val))
    tn = int(np.sum((y_val == 0) & ~predicted_val))

    precision = float(tp / (tp + fp)) if (tp + fp) else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    brier = float(brier_score_loss(y_val, p_val))
    auc = float(roc_auc_score(y_val, p_val)) if len(np.unique(y_val)) == 2 else 0.5
    focal_val = float(np.mean(-(y_val * 0.75 * ((1 - p_val) ** 2) * np.log(p_val) + (1 - y_val) * 0.25 * (p_val ** 2) * np.log(1 - p_val))))

    # 5. Training Set Performance (for tie-breaking)
    y_tr = np.asarray(y_train_true, dtype=int)
    p_tr = np.clip(np.asarray(y_train_prob, dtype=float), 1e-7, 1.0 - 1e-7)
    train_pos_mask = y_tr == 1
    train_calm_mask = y_tr == 0
    tr_peak_hits = int(np.sum((p_tr >= threshold) & train_pos_mask))
    train_peak_hit_rate = float(tr_peak_hits / max(1, int(train_pos_mask.sum())))
    train_quiescent = int(np.sum(p_tr[train_calm_mask] < calm_threshold))
    train_sparsity = float(train_quiescent / max(1, int(train_calm_mask.sum())))
    focal_tr = float(np.mean(-(y_tr * 0.75 * ((1 - p_tr) ** 2) * np.log(p_tr) + (1 - y_tr) * 0.25 * (p_tr ** 2) * np.log(1 - p_tr))))
    train_loss = float(focal_tr + 2.0 * (1.0 - train_peak_hit_rate) + (1.0 - train_sparsity))

    # 6. Composite Needle Loss (Lower is Better). The explicit calm and
    # centered-event terms implement the requested needle-like decision surface.
    event_probs = np.asarray([e["event_prob"] for e in event_records], dtype=float)
    event_probability_loss = float(np.mean((1.0 - event_probs) ** 2)) if len(event_probs) else 1.0
    composite_loss = float(
        5.0 * (1.0 - val_peak_hit_rate) +
        4.0 * (1.0 - val_sparsity) +
        3.0 * event_probability_loss +
        2.0 * val_dep_mae +
        1.5 * focal_val +
        2.5 * (fp / max(1, len(calm_probs_val))) +
        0.15 * val_timing_err +
        0.10 * train_loss
    )

    # 7. Quality/Time Efficiency KPI: Higher is Better
    quality_score = max(0.01, 10.0 - composite_loss)
    quality_time_kpi = float(quality_score / (1.0 + math.log1p(max(0.1, elapsed_seconds))))

    return NeedleMetrics(
        val_peak_hit_rate=val_peak_hit_rate,
        val_peak_timing_error_weeks=val_timing_err,
        val_false_negatives=fn,
        val_event1_max_prob=ev1_max,
        val_event2_max_prob=ev2_max,
        val_peak_tokachi_prob=tokachi_prob,
        val_peak_tohoku_prob=tohoku_prob,
        val_centered_peak_count=peak_hits,
        val_quiescence_sparsity=val_sparsity,
        val_false_positives=fp,
        val_depression_mae=val_dep_mae,
        val_calm_mean_prob=val_dep_mae,
        val_spike_contrast_ratio=val_contrast,
        val_f1_score=f1,
        val_precision=precision,
        val_recall=recall,
        val_focal_loss=focal_val,
        val_brier_score=brier,
        val_auc_roc=auc,
        composite_needle_loss=composite_loss,
        train_peak_hit_rate=train_peak_hit_rate,
        train_quiescence_sparsity=train_sparsity,
        train_focal_loss=focal_tr,
        train_loss=train_loss,
        elapsed_time_seconds=elapsed_seconds,
        quality_time_kpi=quality_time_kpi,
    )

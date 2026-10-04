#!/usr/bin/env python3
"""Leakage-aware weekly Japan M7.9+ timing and conditional location forecast.

This run is deliberately prospective: the seismic snapshot ends at 00:00 JST
on 2026-08-01.  Astronomical covariates extend into the forecast, but no
earthquake observation from August or September is read by this program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import warnings
from dataclasses import asdict
from datetime import timedelta, timezone
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from deep_nets import DeepConfig, DeepNet  # noqa: E402
from kan_backend import KANConfig, KANReadout  # noqa: E402
from lcs import LCSConfig, UCSPredictor  # noqa: E402


JST = timezone(timedelta(hours=9))
ANCHOR = pd.Timestamp("1900-01-06")
FORECAST_START = pd.Timestamp("2026-08-01")
FORECAST_LAST_START = pd.Timestamp("2026-09-26")
CUTOFF_UTC = pd.Timestamp("2026-07-31T15:00:00Z")
BOUNDS = (28.0, 47.0, 128.0, 149.5)
ZONE_MODE = "japan"
ANGULAR_FIELDS = {"AZ", "ObsEclLon", "PABLon", "RA", "RA_app", "alpha_true"}
MODEL_NAMES = (
    "logistic",
    "extra_trees",
    "hist_gradient",
    "deep_tiny",
    "deep_regularized",
    "kan",
    "lcs",
)
LOCATION_MODELS = ("ridge", "extra_trees", "random_forest", "hist_gradient", "analog")
FIELD = re.compile(r"\|eph:([^|]+)\|")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slot_start_jst(times: pd.Series) -> pd.Series:
    local = pd.to_datetime(times, utc=True).dt.tz_convert(JST).dt.tz_localize(None)
    days = (local.dt.normalize() - ANCHOR).dt.days
    return ANCHOR + pd.to_timedelta((days // 7) * 7, unit="D")


def load_catalog(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    frame["time_utc"] = pd.to_datetime(frame.time, utc=True, errors="coerce")
    for column in ("mag", "latitude", "longitude", "depth"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.loc[frame.time_utc.notna() & (frame.time_utc < CUTOFF_UTC)].copy()
    frame["slot_start"] = slot_start_jst(frame.time_utc)
    return frame


def strongest_by_slot(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.sort_values(["slot_start", "mag", "time_utc"], ascending=[True, False, True])
        .drop_duplicates("slot_start", keep="first")
        .sort_values("slot_start")
        .reset_index(drop=True)
    )


def transformed_features(master: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    metadata = {"date", "mag", "depth", "latitude", "longitude"}
    arrays: list[np.ndarray] = []
    names: list[str] = []
    for column in master.columns:
        if column in metadata:
            continue
        values = pd.to_numeric(master[column], errors="coerce").to_numpy(float)
        if not np.isfinite(values).all() or np.std(values) < 1e-14:
            continue
        match = FIELD.search(column)
        field = match.group(1) if match else ""
        if field in ANGULAR_FIELDS:
            radians = np.deg2rad(values)
            arrays.extend([np.sin(radians), np.cos(radians)])
            names.extend([column + "|cyclic:sin", column + "|cyclic:cos"])
        else:
            arrays.append(values)
            names.append(column)
    dates = pd.to_datetime(master.date)
    midpoint = dates + pd.Timedelta(days=3, hours=12)
    year_phase = 2 * np.pi * (midpoint.dt.dayofyear.to_numpy(float) - 1) / 365.2425
    arrays.extend([np.sin(year_phase), np.cos(year_phase)])
    names.extend(["calendar:annual_sin", "calendar:annual_cos"])
    X = np.column_stack(arrays).astype(float)
    if not np.isfinite(X).all():
        raise RuntimeError("Non-finite transformed astronomical features")
    return X, names


def recency_weights(dates: pd.Series, reference: pd.Timestamp, half_life_years: float, floor: float = 0.20) -> np.ndarray:
    age_years = np.maximum((reference - pd.to_datetime(dates)).dt.days.to_numpy(float) / 365.2425, 0.0)
    values = floor + (1.0 - floor) * np.exp(-np.log(2.0) * age_years / half_life_years)
    return values / np.mean(values)


def date_window_indices(date_to_index: dict[pd.Timestamp, int], center: pd.Timestamp, radius: int) -> np.ndarray:
    values = [
        date_to_index[center + pd.Timedelta(days=7 * lag)]
        for lag in range(-radius, radius + 1)
        if center + pd.Timedelta(days=7 * lag) in date_to_index
    ]
    return np.asarray(values, int)


def sample_training_indices(
    dates: pd.Series,
    y: np.ndarray,
    hard_train: np.ndarray,
    hard_audit: np.ndarray,
    limit: pd.Timestamp,
    event_radius: int,
    between_per_event: int,
) -> np.ndarray:
    eligible = np.flatnonzero((dates < limit).to_numpy() & ~hard_audit)
    positives = eligible[y[eligible] == 1]
    keep: set[int] = set(eligible[hard_train[eligible]].tolist())
    for event in positives:
        distance = np.abs((dates.iloc[eligible] - dates.iloc[event]).dt.days.to_numpy())
        keep.update(eligible[distance <= event_radius * 7].tolist())
    available = np.asarray([i for i in eligible if i not in keep], int)
    requested = min(len(available), max(0, between_per_event * len(positives)))
    if requested:
        positions = np.unique(np.rint(np.linspace(0, len(available) - 1, requested)).astype(int))
        keep.update(available[positions].tolist())
    keep.update(positives.tolist())
    return np.asarray(sorted(keep), int)


def rank_features(X: np.ndarray, y: np.ndarray, weights: np.ndarray, count: int, seed: int) -> np.ndarray:
    usable = np.flatnonzero(np.std(X, axis=0) > 1e-12)
    if len(usable) <= count:
        return usable
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mi = np.nan_to_num(mutual_info_classif(X[:, usable], y, random_state=seed), nan=0.0)
    forest = ExtraTreesClassifier(
        n_estimators=160,
        max_depth=8,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=seed + 1,
        n_jobs=-1,
    ).fit(X[:, usable], y, sample_weight=weights)
    ranks = []
    for values in (mi, forest.feature_importances_):
        order = np.argsort(-values, kind="mergesort")
        rank = np.empty(len(order), int)
        rank[order] = np.arange(len(order))
        ranks.append(rank)
    order = np.argsort(np.mean(np.vstack(ranks), axis=0), kind="mergesort")
    return usable[order[:count]]


def balanced_weights(y: np.ndarray, recency: np.ndarray) -> np.ndarray:
    y = np.asarray(y, int)
    positives = max(int(y.sum()), 1)
    negatives = max(int((y == 0).sum()), 1)
    multiplier = min(8.0, negatives / positives)
    values = np.asarray(recency, float) * np.where(y == 1, multiplier, 1.0)
    return values / np.mean(values)


def empirical_percentile(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    reference = np.sort(np.asarray(reference, float))
    values = np.asarray(values, float)
    if len(reference) == 0 or np.std(reference) < 1e-12:
        return np.full(len(values), 0.5)
    left = np.searchsorted(reference, values, side="left")
    right = np.searchsorted(reference, values, side="right")
    return ((left + right) / 2.0 + 0.5) / (len(reference) + 1.0)


def fit_binary_model(
    name: str,
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    seed: int,
) -> tuple[Callable[[np.ndarray], np.ndarray], dict]:
    scaler = StandardScaler().fit(X)
    Xs = np.clip(scaler.transform(X), -8, 8)
    if name == "logistic":
        model = LogisticRegression(C=0.25, max_iter=1200, solver="liblinear", random_state=seed)
        model.fit(Xs, y, sample_weight=weights)
        raw = lambda values: model.predict_proba(np.clip(scaler.transform(values), -8, 8))[:, 1]
        meta = {"family": "L2 logistic", "C": 0.25}
    elif name == "extra_trees":
        model = ExtraTreesClassifier(n_estimators=240, max_depth=8, min_samples_leaf=2, max_features="sqrt", random_state=seed, n_jobs=-1)
        model.fit(Xs, y, sample_weight=weights)
        raw = lambda values: model.predict_proba(np.clip(scaler.transform(values), -8, 8))[:, list(model.classes_).index(1)]
        meta = {"family": "ExtraTrees", "estimators": 240}
    elif name == "hist_gradient":
        model = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15, learning_rate=0.055, l2_regularization=0.5, random_state=seed)
        model.fit(Xs, y, sample_weight=weights)
        raw = lambda values: model.predict_proba(np.clip(scaler.transform(values), -8, 8))[:, 1]
        meta = {"family": "histogram gradient boosting", "iterations": 120}
    elif name.startswith("deep_"):
        regularized = name == "deep_regularized"
        cfg = DeepConfig(
            hidden_sizes=[48, 24] if regularized else [20],
            activation="silu" if regularized else "relu",
            output_activation="sigmoid",
            dropout=0.22 if regularized else 0.0,
            epochs=70 if regularized else 55,
            batch_size=32,
            lr=8e-4 if regularized else 1.5e-3,
            weight_decay=2e-3 if regularized else 1e-4,
            loss="binary_cross_entropy",
            validation_split=0.12,
            early_stop_patience=10,
            final_retrain_full_train=True,
            sample_weights=weights.tolist(),
            seed=seed,
            device="cpu",
        )
        model = DeepNet(cfg).fit(Xs, y)
        raw = lambda values: np.clip(model.predict(np.clip(scaler.transform(values), -8, 8)), 0, 1)
        meta = {"family": "PyTorch MLP", "config": asdict(cfg) | {"sample_weights": "stored separately"}}
    elif name == "kan":
        cfg = KANConfig(hidden_width=3, hidden_layers=1, grid=3, epochs=22, lr=0.018, lamb=0.001, seed=seed, device="cpu")
        model = KANReadout(cfg).fit(Xs, y, sample_weight=weights)
        raw = lambda values: np.clip(model.predict(np.clip(scaler.transform(values), -8, 8)), 0, 1)
        meta = {"family": "spline KAN", "config": asdict(cfg)}
    elif name == "lcs":
        cfg = LCSConfig(population_size=220, epochs=38, ga_frequency=30, validation_split=0.0, early_stop_patience=0, final_retrain_full_train=False, positive_weight="auto", positive_replay="auto", max_active_conditions=min(12, X.shape[1]), sample_weights=weights.tolist(), seed=seed)
        model = UCSPredictor(cfg).fit(Xs, y)
        raw = lambda values: np.clip(model.predict_score(np.clip(scaler.transform(values), -8, 8)), 0, 1)
        meta = {"family": "UCS Learning Classifier System", "config": asdict(cfg) | {"sample_weights": "stored separately"}}
    else:
        raise KeyError(name)
    return raw, meta


def peak_metrics(score: np.ndarray, actual: int) -> dict:
    score = np.asarray(score, float)
    peak = int(np.argmax(score))
    ranks = pd.Series(score).rank(method="average", pct=True).to_numpy(float)
    offset = peak - actual
    if 0 < actual < len(score) - 1:
        prominence = score[actual] - max(score[actual - 1], score[actual + 1])
    else:
        prominence = 0.0
    scale = max(float(np.quantile(score, 0.9) - np.quantile(score, 0.1)), float(np.std(score)), 1e-6)
    prominence_skill = float(1 / (1 + np.exp(-4 * prominence / scale)))
    quality = float(0.40 * ranks[actual] + 0.35 * math.exp(-abs(offset)) + 0.25 * prominence_skill)
    return {
        "actual_position": int(actual),
        "peak_position": peak,
        "argmax_offset_slots": int(offset),
        "exact_peak": bool(offset == 0),
        "within_one_slot": bool(abs(offset) <= 1),
        "event_percentile": float(ranks[actual]),
        "prominence_skill": prominence_skill,
        "quality": quality,
        "score_std": float(np.std(score)),
    }


def training_signal(y: np.ndarray, score: np.ndarray) -> dict:
    y = np.asarray(y, int)
    prevalence = float(np.mean(y))
    ap = float(average_precision_score(y, score)) if len(np.unique(y)) == 2 else prevalence
    ap_skill = float(np.clip((ap - prevalence) / max(1 - prevalence, 1e-9), 0, 1))
    ranks = pd.Series(score).rank(method="average", pct=True).to_numpy(float)
    event_rank = float(np.mean(ranks[y == 1])) if y.sum() else 0.0
    return {
        "average_precision": ap,
        "average_precision_skill": ap_skill,
        "mean_positive_percentile": event_rank,
        "score_std": float(np.std(score)),
        "quality": float(0.45 * ap_skill + 0.45 * event_rank + 0.10 * min(np.std(score) / 0.10, 1.0)),
    }


def softmax_weights(qualities: dict[str, float], temperature: float = 0.08, floor: float = 0.03) -> dict[str, float]:
    names = list(qualities)
    values = np.asarray([qualities[name] for name in names], float)
    raw = np.exp((values - np.max(values)) / temperature) + floor
    raw /= raw.sum()
    return {name: float(raw[i]) for i, name in enumerate(names)}


def optimize_timing_weights(
    predictions: dict[tuple[str, str, pd.Timestamp], np.ndarray],
    model_names: list[str],
    dev_slots: list[pd.Timestamp],
    fold_table: pd.DataFrame,
    initial: dict[str, float],
    seed: int,
    trials: int = 24000,
) -> tuple[dict[str, float], pd.DataFrame]:
    """Select ensemble weights on development folds only.

    Exact and one-slot peak alignment dominate the objective.  Fold weights
    increase chronologically but start at 0.35, so early folds are never zeroed.
    """
    cube = np.asarray(
        [[predictions[("development", name, slot)] for name in model_names] for slot in dev_slots],
        float,
    )
    actual = cube.shape[2] // 2
    rng = np.random.default_rng(seed)
    candidates = [np.asarray([initial[name] for name in model_names], float)]
    candidates.append(np.full(len(model_names), 1.0 / len(model_names)))
    candidates.extend(np.eye(len(model_names)))
    for concentration in (0.18, 0.50, 1.0, 2.5):
        candidates.extend(rng.dirichlet(np.full(len(model_names), concentration), size=trials // 4))
    recent = np.linspace(0.35, 1.0, len(dev_slots))
    train_quality = np.asarray(
        [
            fold_table[(fold_table.group == "development") & (fold_table.model == name)].training_quality.mean()
            for name in model_names
        ],
        float,
    )
    rows = []
    for trial, weights in enumerate(candidates):
        scores = np.einsum("fmn,m->fn", cube, weights)
        metrics = [peak_metrics(score, actual) for score in scores]
        exact = np.asarray([row["exact_peak"] for row in metrics], float)
        within = np.asarray([row["within_one_slot"] for row in metrics], float)
        quality = np.asarray([row["quality"] for row in metrics], float)
        entropy = -float(np.sum(np.where(weights > 0, weights * np.log(np.maximum(weights, 1e-15)), 0))) / max(math.log(len(weights)), 1e-9)
        objective = float(
            0.46 * np.average(exact, weights=recent)
            + 0.24 * np.average(within, weights=recent)
            + 0.22 * np.average(quality, weights=recent)
            + 0.06 * np.dot(weights, train_quality)
            + 0.02 * entropy
        )
        rows.append(
            {
                "trial": trial,
                "objective": objective,
                "exact_rate_recent_weighted": float(np.average(exact, weights=recent)),
                "within_one_rate_recent_weighted": float(np.average(within, weights=recent)),
                "quality_recent_weighted": float(np.average(quality, weights=recent)),
                "training_quality_weighted": float(np.dot(weights, train_quality)),
                "weight_entropy": entropy,
                **{f"weight_{name}": float(weights[i]) for i, name in enumerate(model_names)},
            }
        )
    table = pd.DataFrame(rows).sort_values("objective", ascending=False).reset_index(drop=True)
    best = {name: float(table.loc[0, f"weight_{name}"]) for name in model_names}
    return best, table


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = np.deg2rad([lat1, lat2])
    dp = p2 - p1
    dl = np.deg2rad(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(6371.0088 * 2 * np.arctan2(np.sqrt(a), np.sqrt(max(1 - a, 0))))


def zone_name(lat: float, lon: float) -> str:
    if ZONE_MODE == "hokkaido_corridor":
        if lon >= 147.5 or lat >= 44.5:
            return "Etorofu–Curili meridionali"
        if lon >= 145.0:
            return "Nemuro–Kunashir/Shikotan"
        if lat >= 41.2:
            return "Tokachi–Hokkaido sud-orientale"
        return "Sanriku–Morioka/Hachinohe"
    if lat >= 41.5 and lon >= 142.0:
        return "Hokkaido–Curili meridionali"
    if lat >= 36.5 and lon >= 140.0:
        return "Tohoku–fossa del Giappone"
    if lon >= 138.0 and lat < 36.5:
        return "Kanto–Izu/Ogasawara"
    if 31.0 <= lat < 36.5 and 132.0 <= lon < 138.0:
        return "Nankai–Shikoku/Kii"
    if lat < 33.0 and lon < 132.0:
        return "Kyushu–Ryukyu"
    return "Giappone centrale/margine interno"


def location_feature_indices(X: np.ndarray, target: np.ndarray, count: int = 18) -> np.ndarray:
    correlations = []
    for j in range(X.shape[1]):
        scores = []
        for k in range(2):
            if np.std(X[:, j]) < 1e-12:
                scores.append(0.0)
            else:
                scores.append(abs(float(np.nan_to_num(np.corrcoef(X[:, j], target[:, k])[0, 1]))))
        correlations.append(max(scores))
    return np.argsort(-np.asarray(correlations), kind="mergesort")[: min(count, X.shape[1])]


def fit_location_model(name: str, X: np.ndarray, target: np.ndarray, weights: np.ndarray, seed: int) -> Callable[[np.ndarray], np.ndarray]:
    scaler = StandardScaler().fit(X)
    Xs = np.clip(scaler.transform(X), -8, 8)
    if name == "ridge":
        model = Ridge(alpha=5.0).fit(Xs, target, sample_weight=weights)
        return lambda values: model.predict(np.clip(scaler.transform(values), -8, 8))
    if name == "extra_trees":
        model = ExtraTreesRegressor(n_estimators=320, max_depth=7, min_samples_leaf=2, max_features="sqrt", random_state=seed, n_jobs=-1).fit(Xs, target, sample_weight=weights)
        return lambda values: model.predict(np.clip(scaler.transform(values), -8, 8))
    if name == "random_forest":
        model = RandomForestRegressor(n_estimators=320, max_depth=7, min_samples_leaf=2, max_features=0.7, random_state=seed, n_jobs=-1).fit(Xs, target, sample_weight=weights)
        return lambda values: model.predict(np.clip(scaler.transform(values), -8, 8))
    if name == "hist_gradient":
        models = [HistGradientBoostingRegressor(max_iter=120, max_leaf_nodes=7, learning_rate=0.05, l2_regularization=2.0, random_state=seed + k).fit(Xs, target[:, k], sample_weight=weights) for k in range(2)]
        return lambda values: np.column_stack([model.predict(np.clip(scaler.transform(values), -8, 8)) for model in models])
    if name == "analog":
        def predict(values: np.ndarray) -> np.ndarray:
            out = []
            for row in np.clip(scaler.transform(values), -8, 8):
                distance = np.sqrt(np.mean((Xs - row) ** 2, axis=1))
                nearest = np.argsort(distance)[: min(5, len(distance))]
                local_w = weights[nearest] / np.maximum(distance[nearest], 0.05) ** 2
                out.append(np.average(target[nearest], axis=0, weights=local_w))
            return np.asarray(out)
        return predict
    raise KeyError(name)


def run_location(
    X: np.ndarray,
    names: list[str],
    event_indices: np.ndarray,
    event_rows: pd.DataFrame,
    dev_slots: list[pd.Timestamp],
    audit_slots: list[pd.Timestamp],
    peak_X: np.ndarray,
    out_dir: Path,
    seed: int,
) -> dict:
    slot_to_position = {pd.Timestamp(slot): i for i, slot in enumerate(event_rows.slot_start)}
    dev_records: list[dict] = []
    fold_predictions: dict[tuple[str, pd.Timestamp], np.ndarray] = {}
    for group, slots in (("development", dev_slots), ("frozen_audit", audit_slots)):
        for fold_no, slot in enumerate(slots, 1):
            position = slot_to_position[slot]
            train_positions = np.arange(position)
            target = event_rows[["latitude", "longitude"]].to_numpy(float)
            train_X = X[event_indices[train_positions]]
            train_y = target[train_positions]
            weights = recency_weights(event_rows.slot_start.iloc[train_positions], slot, 40.0)
            selected = location_feature_indices(train_X, train_y, count=18)
            for model_no, model_name in enumerate(LOCATION_MODELS):
                predictor = fit_location_model(model_name, train_X[:, selected], train_y, weights, seed + position * 101 + model_no)
                pred = predictor(X[event_indices[[position]]][:, selected])[0]
                pred[0] = np.clip(pred[0], BOUNDS[0], BOUNDS[1])
                pred[1] = np.clip(pred[1], BOUNDS[2], BOUNDS[3])
                fold_predictions[(model_name, slot)] = pred
                error = haversine_km(target[position, 0], target[position, 1], pred[0], pred[1])
                dev_records.append({"group": group, "fold": fold_no, "event_slot": slot.strftime("%Y-%m-%d"), "model": model_name, "actual_latitude": target[position, 0], "actual_longitude": target[position, 1], "predicted_latitude": pred[0], "predicted_longitude": pred[1], "error_km": error, "zone_hit": zone_name(*pred) == zone_name(*target[position])})
    validation = pd.DataFrame(dev_records)
    validation.to_csv(out_dir / "location_validation.csv", index=False)
    dev_quality = {}
    for model_name in LOCATION_MODELS:
        rows = validation[(validation.group == "development") & (validation.model == model_name)]
        recent = np.linspace(0.35, 1.0, len(rows))
        dev_quality[model_name] = float(np.average(np.exp(-rows.error_km.to_numpy(float) / 450.0), weights=recent))
    model_weights = softmax_weights(dev_quality, temperature=0.12, floor=0.04)

    audit_ensemble = []
    for slot in audit_slots:
        pred = sum(model_weights[name] * fold_predictions[(name, slot)] for name in LOCATION_MODELS)
        position = slot_to_position[slot]
        actual = event_rows.loc[position, ["latitude", "longitude"]].to_numpy(float)
        prior = event_rows.iloc[:position]
        baseline_weights = recency_weights(prior.slot_start, slot, 40.0)
        baseline = np.average(prior[["latitude", "longitude"]].to_numpy(float), axis=0, weights=baseline_weights)
        audit_ensemble.append({"event_slot": slot.strftime("%Y-%m-%d"), "actual_latitude": actual[0], "actual_longitude": actual[1], "predicted_latitude": pred[0], "predicted_longitude": pred[1], "error_km": haversine_km(*actual, *pred), "zone_hit": zone_name(*pred) == zone_name(*actual), "recency_baseline_latitude": baseline[0], "recency_baseline_longitude": baseline[1], "recency_baseline_error_km": haversine_km(*actual, *baseline)})
    audit_frame = pd.DataFrame(audit_ensemble)
    audit_frame.to_csv(out_dir / "location_frozen_audit_ensemble.csv", index=False)

    all_target = event_rows[["latitude", "longitude"]].to_numpy(float)
    weights = recency_weights(event_rows.slot_start, FORECAST_START, 40.0)
    selected = location_feature_indices(X[event_indices], all_target, count=18)
    final_predictions = []
    for model_no, model_name in enumerate(LOCATION_MODELS):
        predictor = fit_location_model(model_name, X[event_indices][:, selected], all_target, weights, seed + 9000 + model_no)
        pred = predictor(peak_X[:, selected])[0]
        pred[0] = np.clip(pred[0], BOUNDS[0], BOUNDS[1])
        pred[1] = np.clip(pred[1], BOUNDS[2], BOUNDS[3])
        final_predictions.append({"model": model_name, "weight": model_weights[model_name], "latitude": float(pred[0]), "longitude": float(pred[1]), "zone": zone_name(*pred)})
    final_frame = pd.DataFrame(final_predictions)
    final_frame.to_csv(out_dir / "location_peak_model_predictions.csv", index=False)
    point = np.average(final_frame[["latitude", "longitude"]].to_numpy(float), axis=0, weights=final_frame.weight)
    zone_votes = final_frame.groupby("zone").weight.sum().sort_values(ascending=False)
    errors = audit_frame.error_km.to_numpy(float)
    baseline_errors = audit_frame.recency_baseline_error_km.to_numpy(float)
    radius80 = float(np.quantile(errors, 0.80)) if len(errors) else float("nan")
    gate_checks = {
        "median_error_le_250_km": bool(np.median(errors) <= 250) if len(errors) else False,
        "q80_error_le_350_km": bool(radius80 <= 350) if len(errors) else False,
        "zone_hit_rate_ge_0_75": bool(audit_frame.zone_hit.mean() >= 0.75) if len(errors) else False,
        "median_error_improves_recency_baseline_by_30pct": bool(np.median(errors) <= 0.70 * np.median(baseline_errors)) if len(errors) else False,
    }
    return {
        "most_likely_zone": str(zone_votes.index[0]),
        "zone_vote": float(zone_votes.iloc[0]),
        "estimated_latitude": float(point[0]),
        "estimated_longitude": float(point[1]),
        "audit_median_error_km": float(np.median(errors)) if len(errors) else None,
        "audit_q80_error_km": radius80 if len(errors) else None,
        "audit_recency_baseline_median_error_km": float(np.median(baseline_errors)) if len(errors) else None,
        "audit_median_error_improvement_vs_recency_baseline": float(1.0 - np.median(errors) / np.median(baseline_errors)) if len(errors) else None,
        "audit_zone_hit_rate": float(audit_frame.zone_hit.mean()) if len(errors) else None,
        "uncertainty_radius_km": radius80 if len(errors) else None,
        "gate_checks": gate_checks,
        "gate_status": "PASS" if all(gate_checks.values()) else "FAIL_REPORTED_WITH_LOW_CONFIDENCE",
        "model_weights": model_weights,
        "selected_features": [names[i] for i in selected],
    }


def main() -> None:
    global BOUNDS, ZONE_MODE
    parser = argparse.ArgumentParser()
    parser.add_argument("--astro-master", required=True)
    parser.add_argument("--japan-catalog", required=True)
    parser.add_argument("--world-catalog", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=621731)
    parser.add_argument(
        "--region-bounds",
        nargs=4,
        type=float,
        metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"),
        default=list(BOUNDS),
    )
    parser.add_argument("--zone-mode", choices=("japan", "hokkaido_corridor"), default="japan")
    parser.add_argument("--development-event-count", type=int, default=5)
    parser.add_argument("--audit-event-count", type=int, default=4)
    parser.add_argument("--run-name", default="japan-m79plus-7d-aug-sep2026-cutoff-jul31-recency-globalneg-v21")
    parser.add_argument("--run-title", default="Giappone M7.9+")
    parser.add_argument(
        "--reuse-search-if-present",
        action="store_true",
        help="Resume after a downstream failure by reusing the already written sampling search.",
    )
    args = parser.parse_args()
    BOUNDS = tuple(float(value) for value in args.region_bounds)
    ZONE_MODE = args.zone_mode
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    astro_path = Path(args.astro_master).resolve()
    japan_path = Path(args.japan_catalog).resolve()
    world_path = Path(args.world_catalog).resolve()

    master = pd.read_csv(astro_path, low_memory=False).sort_values("date").reset_index(drop=True)
    master["date"] = pd.to_datetime(master.date)
    if master.date.duplicated().any():
        raise RuntimeError("Duplicate astronomical period labels")
    X, feature_names = transformed_features(master)
    japan = load_catalog(japan_path)
    world = load_catalog(world_path)
    inside_target = (
        japan.latitude.between(BOUNDS[0], BOUNDS[1])
        & japan.longitude.between(BOUNDS[2], BOUNDS[3])
    )
    targets = strongest_by_slot(japan.loc[(japan.mag >= 7.9) & inside_target].copy())
    outside = ~(world.latitude.between(BOUNDS[0], BOUNDS[1]) & world.longitude.between(BOUNDS[2], BOUNDS[3]))
    hard_events = strongest_by_slot(world.loc[outside & (world.mag >= 7.9)].copy())
    date_to_index = {pd.Timestamp(date): i for i, date in enumerate(master.date)}
    missing_targets = sorted(set(targets.slot_start).difference(date_to_index))
    if missing_targets:
        raise RuntimeError(f"Missing astronomical rows for target slots: {missing_targets}")

    y = np.zeros(len(master), int)
    event_mag = np.full(len(master), np.nan)
    event_lat = np.full(len(master), np.nan)
    event_lon = np.full(len(master), np.nan)
    for row in targets.itertuples(index=False):
        i = date_to_index[pd.Timestamp(row.slot_start)]
        y[i] = 1
        event_mag[i], event_lat[i], event_lon[i] = row.mag, row.latitude, row.longitude
    hard_by_slot = hard_events.loc[~hard_events.slot_start.isin(targets.slot_start)].copy()
    recent_pool = hard_by_slot.loc[hard_by_slot.mag >= 8.3].sort_values("time_utc")
    if recent_pool.slot_start.nunique() < 8:
        recent_pool = hard_by_slot.loc[hard_by_slot.mag >= 8.1].sort_values("time_utc")
    audit_slots = set(recent_pool.drop_duplicates("slot_start", keep="last").tail(8).slot_start)
    hard_train = np.zeros(len(master), bool)
    hard_audit = np.zeros(len(master), bool)
    for row in hard_by_slot.itertuples(index=False):
        slot = pd.Timestamp(row.slot_start)
        if slot not in date_to_index:
            continue
        if slot in audit_slots:
            hard_audit[date_to_index[slot]] = True
        else:
            hard_train[date_to_index[slot]] = True

    dataset = master[["date"]].copy()
    dataset["date"] = dataset.date.dt.strftime("%Y-%m-%d")
    dataset["timing_target"] = y
    dataset["event_mag"] = event_mag
    dataset["event_latitude"] = event_lat
    dataset["event_longitude"] = event_lon
    dataset["world_non_japan_hard_negative_train"] = hard_train
    dataset["world_non_japan_hard_negative_frozen_audit"] = hard_audit
    dataset["is_forecast"] = (master.date >= FORECAST_START) & (master.date <= FORECAST_LAST_START)
    dataset.to_csv(out_dir / "prepared_weekly_dataset.csv", index=False)

    positive_slots = targets.slot_start.tolist()
    audit_count = int(args.audit_event_count)
    development_count = int(args.development_event_count)
    if len(positive_slots) < audit_count + development_count + 3:
        raise RuntimeError(
            f"Only {len(positive_slots)} independent target slots; need at least "
            f"{audit_count + development_count + 3} for the requested split"
        )
    dev_slots = [pd.Timestamp(value) for value in positive_slots[-(audit_count + development_count):-audit_count]]
    frozen_slots = [pd.Timestamp(value) for value in positive_slots[-audit_count:]]
    search_path = out_dir / "sampling_recency_search.csv"
    reuse_search = bool(args.reuse_search_if_present and search_path.exists())
    configs = [] if reuse_search else [
        {"event_radius": radius, "between_per_event": between, "half_life_years": half_life, "feature_count": features}
        for radius in (4, 6, 8)
        for between in (2, 4)
        for half_life in (20.0, 40.0, 80.0)
        for features in (24, 36)
    ]
    search_rows = []
    for config_no, config in enumerate(configs):
        qualities, train_qualities, exact = [], [], []
        for fold_no, event_slot in enumerate(dev_slots):
            validation = date_window_indices(date_to_index, event_slot, 4)
            limit = event_slot - pd.Timedelta(days=28)
            train = sample_training_indices(master.date, y, hard_train, hard_audit, limit, config["event_radius"], config["between_per_event"])
            recency = recency_weights(master.date.iloc[train], event_slot, config["half_life_years"])
            weights = balanced_weights(y[train], recency)
            selected = rank_features(X[train], y[train], weights, config["feature_count"], args.seed + config_no * 100 + fold_no)
            member_scores = []
            member_train = []
            for model_no, model_name in enumerate(("logistic", "extra_trees")):
                predictor, _ = fit_binary_model(model_name, X[train][:, selected], y[train], weights, args.seed + config_no * 1000 + fold_no * 10 + model_no)
                raw_train = predictor(X[train][:, selected])
                member_train.append(empirical_percentile(raw_train, raw_train))
                member_scores.append(empirical_percentile(raw_train, predictor(X[validation][:, selected])))
            score = np.mean(member_scores, axis=0)
            train_score = np.mean(member_train, axis=0)
            actual = int(np.flatnonzero(y[validation] == 1)[0])
            metrics = peak_metrics(score, actual)
            qualities.append(metrics["quality"])
            exact.append(metrics["exact_peak"])
            train_qualities.append(training_signal(y[train], train_score)["quality"])
        fold_weight = np.linspace(0.35, 1.0, len(qualities))
        objective = float(0.70 * np.average(qualities, weights=fold_weight) + 0.20 * np.mean(train_qualities) + 0.10 * np.mean(exact))
        search_rows.append({"config_id": config_no, **config, "development_quality_recent_weighted": np.average(qualities, weights=fold_weight), "development_exact_rate": np.mean(exact), "training_quality_mean": np.mean(train_qualities), "objective": objective})
    if reuse_search:
        search = pd.read_csv(search_path).sort_values("objective", ascending=False).reset_index(drop=True)
        print(f"[RESUME] Reusing completed sampling/recency search: {search_path}", flush=True)
    else:
        search = pd.DataFrame(search_rows).sort_values("objective", ascending=False).reset_index(drop=True)
        search.to_csv(search_path, index=False)
    print(f"[MODELS] Selected sampling/recency config from {len(search)} trials", flush=True)
    selected_config = {key: search.loc[0, key].item() if hasattr(search.loc[0, key], "item") else search.loc[0, key] for key in ("event_radius", "between_per_event", "half_life_years", "feature_count")}
    selected_config["event_radius"] = int(selected_config["event_radius"])
    selected_config["between_per_event"] = int(selected_config["between_per_event"])
    selected_config["feature_count"] = int(selected_config["feature_count"])
    selected_config["half_life_years"] = float(selected_config["half_life_years"])

    predictions: dict[tuple[str, str, pd.Timestamp], np.ndarray] = {}
    fold_rows = []
    model_meta: dict[str, dict] = {}
    for group, slots in (("development", dev_slots), ("frozen_audit", frozen_slots)):
        print(f"[MODELS] Running {group} folds ({len(slots)} events)", flush=True)
        for fold_no, event_slot in enumerate(slots, 1):
            validation = date_window_indices(date_to_index, event_slot, 4)
            limit = event_slot - pd.Timedelta(days=28)
            train = sample_training_indices(master.date, y, hard_train, hard_audit, limit, selected_config["event_radius"], selected_config["between_per_event"])
            recency = recency_weights(master.date.iloc[train], event_slot, selected_config["half_life_years"])
            weights = balanced_weights(y[train], recency)
            selected = rank_features(X[train], y[train], weights, selected_config["feature_count"], args.seed + 20000 + fold_no + (0 if group == "development" else 1000))
            actual = int(np.flatnonzero(y[validation] == 1)[0])
            for model_no, model_name in enumerate(MODEL_NAMES):
                try:
                    predictor, meta = fit_binary_model(model_name, X[train][:, selected], y[train], weights, args.seed + 30000 + fold_no * 100 + model_no + (0 if group == "development" else 1000))
                    model_meta.setdefault(model_name, meta)
                    raw_train = predictor(X[train][:, selected])
                    train_score = empirical_percentile(raw_train, raw_train)
                    score = empirical_percentile(raw_train, predictor(X[validation][:, selected]))
                    metrics = peak_metrics(score, actual)
                    train_metrics = training_signal(y[train], train_score)
                    predictions[(group, model_name, event_slot)] = score
                    fold_rows.append({"group": group, "fold": fold_no, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, **metrics, "training_quality": train_metrics["quality"], "training_positive_percentile": train_metrics["mean_positive_percentile"], "training_score_std": train_metrics["score_std"], "status": "OK"})
                except Exception as exc:
                    fold_rows.append({"group": group, "fold": fold_no, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, "status": "ERROR", "error": str(exc)})
    fold_table = pd.DataFrame(fold_rows)
    fold_table.to_csv(out_dir / "timing_model_fold_metrics.csv", index=False)
    complete_models = [name for name in MODEL_NAMES if ((fold_table.model == name) & (fold_table.status == "OK")).sum() == len(dev_slots) + len(frozen_slots)]
    if len(complete_models) < 3:
        raise RuntimeError(f"Fewer than three model families completed all folds: {complete_models}")
    dev_quality = {}
    for name in complete_models:
        rows = fold_table[(fold_table.group == "development") & (fold_table.model == name)]
        dev_quality[name] = float(0.85 * np.average(rows.quality, weights=np.linspace(0.35, 1.0, len(rows))) + 0.15 * rows.training_quality.mean())
    initial_weights = softmax_weights(dev_quality)
    model_weights, weight_search = optimize_timing_weights(
        predictions,
        complete_models,
        dev_slots,
        fold_table,
        initial_weights,
        args.seed + 41000,
    )
    weight_search.head(2500).to_csv(out_dir / "timing_weight_search_top2500.csv", index=False)
    write_json(
        out_dir / "timing_weight_selection.json",
        {
            "policy": "24,000 deterministic Dirichlet trials plus uniform, individual and development-quality candidates; development folds only",
            "selected_weights": model_weights,
            "selected_metrics": weight_search.iloc[0].to_dict(),
            "frozen_audit_used_for_selection": False,
        },
    )
    print(
        "[ENSEMBLE] Development-selected exact rate "
        f"{weight_search.loc[0, 'exact_rate_recent_weighted']:.3f}; "
        f"within-one {weight_search.loc[0, 'within_one_rate_recent_weighted']:.3f}",
        flush=True,
    )

    ensemble_rows = []
    validation_prediction_rows = []
    for group, slots in (("development", dev_slots), ("frozen_audit", frozen_slots)):
        for fold_no, event_slot in enumerate(slots, 1):
            score = sum(model_weights[name] * predictions[(group, name, event_slot)] for name in complete_models)
            validation = date_window_indices(date_to_index, event_slot, 4)
            actual = int(np.flatnonzero(y[validation] == 1)[0])
            ensemble_rows.append({"group": group, "fold": fold_no, "event_slot": event_slot.strftime("%Y-%m-%d"), **peak_metrics(score, actual)})
            for position, (index, value) in enumerate(zip(validation, score)):
                validation_prediction_rows.append(
                    {
                        "group": group,
                        "fold": fold_no,
                        "event_slot": event_slot.strftime("%Y-%m-%d"),
                        "window_position": position - actual,
                        "date": master.date.iloc[index].strftime("%Y-%m-%d"),
                        "is_event_slot": bool(position == actual),
                        "ensemble_score": float(value),
                    }
                )
    ensemble_table = pd.DataFrame(ensemble_rows)
    ensemble_table.to_csv(out_dir / "timing_ensemble_fold_metrics.csv", index=False)
    pd.DataFrame(validation_prediction_rows).to_csv(out_dir / "timing_validation_window_predictions.csv", index=False)

    final_train = sample_training_indices(master.date, y, hard_train, hard_audit, FORECAST_START, selected_config["event_radius"], selected_config["between_per_event"])
    final_recency = recency_weights(master.date.iloc[final_train], FORECAST_START, selected_config["half_life_years"])
    final_weights = balanced_weights(y[final_train], final_recency)
    final_features = rank_features(X[final_train], y[final_train], final_weights, selected_config["feature_count"], args.seed + 50000)
    forecast = np.flatnonzero(((master.date >= FORECAST_START) & (master.date <= FORECAST_LAST_START)).to_numpy())
    audit_negative_indices = np.flatnonzero(hard_audit)
    forecast_frame = pd.DataFrame({"slot_start_jst": master.date.iloc[forecast].dt.strftime("%Y-%m-%d"), "slot_end_jst": (master.date.iloc[forecast] + pd.Timedelta(days=6)).dt.strftime("%Y-%m-%d")}).reset_index(drop=True)
    final_train_scores = {}
    final_negative_scores = {}
    for model_no, model_name in enumerate(complete_models):
        predictor, _ = fit_binary_model(model_name, X[final_train][:, final_features], y[final_train], final_weights, args.seed + 60000 + model_no)
        raw_train = predictor(X[final_train][:, final_features])
        final_train_scores[model_name] = empirical_percentile(raw_train, raw_train)
        forecast_frame[model_name] = empirical_percentile(raw_train, predictor(X[forecast][:, final_features]))
        final_negative_scores[model_name] = empirical_percentile(raw_train, predictor(X[audit_negative_indices][:, final_features])) if len(audit_negative_indices) else np.asarray([])
    forecast_frame["ensemble_score"] = sum(model_weights[name] * forecast_frame[name] for name in complete_models)
    forecast_frame["rank"] = forecast_frame.ensemble_score.rank(method="min", ascending=False).astype(int)
    informative_models = [name for name in complete_models if float(np.std(forecast_frame[name])) >= 1e-6]
    model_peak_votes = pd.Series(
        [forecast_frame.slot_start_jst.iloc[int(np.argmax(forecast_frame[name]))] for name in informative_models]
    ).value_counts()
    near_optimum = weight_search[
        weight_search.objective >= float(weight_search.objective.iloc[0]) - 0.01
    ].copy()
    weight_columns = [f"weight_{name}" for name in complete_models]
    sensitivity_scores = near_optimum[weight_columns].to_numpy(float) @ forecast_frame[list(complete_models)].to_numpy(float).T
    sensitivity_peaks = np.argmax(sensitivity_scores, axis=1)
    sensitivity = pd.DataFrame(
        {
            "trial": near_optimum.trial.to_numpy(int),
            "objective": near_optimum.objective.to_numpy(float),
            "peak_slot_start_jst": [forecast_frame.slot_start_jst.iloc[i] for i in sensitivity_peaks],
        }
    )
    sensitivity.to_csv(out_dir / "timing_near_optimum_peak_sensitivity.csv", index=False)
    sensitivity_counts = sensitivity.peak_slot_start_jst.value_counts(normalize=True)
    quality_weight_score = sum(initial_weights[name] * forecast_frame[name] for name in complete_models)
    peak_stability = {
        "selected_peak": str(forecast_frame.slot_start_jst.iloc[int(np.argmax(forecast_frame.ensemble_score))]),
        "development_quality_softmax_peak": str(forecast_frame.slot_start_jst.iloc[int(np.argmax(quality_weight_score))]),
        "informative_model_peak_votes": {str(key): int(value) for key, value in model_peak_votes.items()},
        "informative_model_majority_fraction": float(model_peak_votes.iloc[0] / len(informative_models)),
        "near_optimum_weight_trial_count": int(len(sensitivity)),
        "near_optimum_peak_fractions": {str(key): float(value) for key, value in sensitivity_counts.items()},
        "near_optimum_consensus_fraction": float(sensitivity_counts.iloc[0]),
    }
    forecast_frame.to_csv(out_dir / "forecast_weekly_aug_sep_2026.csv", index=False)
    peak_position = int(np.argmax(forecast_frame.ensemble_score.to_numpy(float)))
    peak_index = int(forecast[peak_position])

    train_ensemble = sum(model_weights[name] * final_train_scores[name] for name in complete_models)
    train_metrics = training_signal(y[final_train], train_ensemble)
    negative_ensemble = sum(model_weights[name] * final_negative_scores[name] for name in complete_models) if len(audit_negative_indices) else np.asarray([])
    hard_negative_table = pd.DataFrame({"slot_start_jst": master.date.iloc[audit_negative_indices].dt.strftime("%Y-%m-%d"), "ensemble_score": negative_ensemble})
    hard_negative_table.to_csv(out_dir / "frozen_world_hard_negative_scores.csv", index=False)
    audit = ensemble_table[ensemble_table.group == "frozen_audit"]
    timing_checks = {
        "frozen_exact_peak_rate_ge_0_75": bool(audit.exact_peak.mean() >= 0.75),
        "frozen_all_within_one_slot": bool(audit.within_one_slot.all()),
        "frozen_mean_event_percentile_ge_0_85": bool(audit.event_percentile.mean() >= 0.85),
        "frozen_mean_quality_ge_0_70": bool(audit.quality.mean() >= 0.70),
        "training_quality_ge_0_55": bool(train_metrics["quality"] >= 0.55),
        "training_score_non_degenerate": bool(train_metrics["score_std"] >= 0.05),
        "hard_negative_mean_below_0_65": bool(np.mean(negative_ensemble) < 0.65) if len(negative_ensemble) else False,
        "hard_negative_p90_below_0_85": bool(np.quantile(negative_ensemble, 0.9) < 0.85) if len(negative_ensemble) else False,
        "informative_model_peak_majority_ge_0_70": bool(peak_stability["informative_model_majority_fraction"] >= 0.70),
        "near_optimum_weight_peak_consensus_ge_0_70": bool(peak_stability["near_optimum_consensus_fraction"] >= 0.70),
    }

    event_indices = np.asarray([date_to_index[pd.Timestamp(slot)] for slot in targets.slot_start], int)
    print("[LOCATION] Running chronological spatial validation and final zone ensemble", flush=True)
    location = run_location(X, feature_names, event_indices, targets, dev_slots, frozen_slots, X[[peak_index]], out_dir, args.seed + 70000)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    ax = axes[0]
    ax.plot(pd.to_datetime(forecast_frame.slot_start_jst), forecast_frame.ensemble_score, marker="o", color="#c43c39", linewidth=2.2, label="ensemble settimanale")
    ax.axvspan(pd.to_datetime(forecast_frame.loc[peak_position, "slot_start_jst"]), pd.to_datetime(forecast_frame.loc[peak_position, "slot_end_jst"]) + pd.Timedelta(days=1), color="#f2b134", alpha=0.28, label="massimo")
    ax.set_title(f"Forecast temporale {args.run_title} — cutoff fine luglio")
    ax.set_ylabel("score empirico (non probabilità)")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.scatter(targets.longitude, targets.latitude, c=np.arange(len(targets)), cmap="viridis", s=30, alpha=0.75, label="eventi storici")
    ax.scatter(location["estimated_longitude"], location["estimated_latitude"], marker="*", s=220, color="#c43c39", edgecolor="black", label="stima al picco")
    radius_deg = (location["uncertainty_radius_km"] or 0) / 111.0
    ax.add_patch(plt.Circle((location["estimated_longitude"], location["estimated_latitude"]), radius_deg, fill=False, linestyle="--", color="#c43c39", alpha=0.75))
    ax.set_xlim(BOUNDS[2] - 1, BOUNDS[3] + 1)
    ax.set_ylim(BOUNDS[0] - 1, BOUNDS[1] + 1)
    ax.set_xlabel("longitudine")
    ax.set_ylabel("latitudine")
    ax.set_title("Zona condizionale e raggio CV all'80%")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "forecast_timing_location.png", dpi=180)
    plt.close(fig)

    timing_status = "PASS" if all(timing_checks.values()) else "FAIL_REPORTED_NOT_VALIDATED"
    summary = {
        "run": args.run_name,
        "run_title": args.run_title,
        "scientific_status": "experimental pattern-model output; not an operational earthquake prediction",
        "cutoff": {"jst_end_exclusive": "2026-08-01T00:00:00+09:00", "utc_end_exclusive": CUTOFF_UTC.isoformat(), "august_seismic_observations_used": 0},
        "timing": {
            "gate_status": timing_status,
            "gate_checks": timing_checks,
            "peak_slot_start_jst": forecast_frame.loc[peak_position, "slot_start_jst"],
            "peak_slot_end_jst": forecast_frame.loc[peak_position, "slot_end_jst"],
            "peak_ensemble_score": float(forecast_frame.loc[peak_position, "ensemble_score"]),
            "frozen_audit_exact_rate": float(audit.exact_peak.mean()),
            "frozen_audit_within_one_rate": float(audit.within_one_slot.mean()),
            "frozen_audit_mean_event_percentile": float(audit.event_percentile.mean()),
            "frozen_audit_mean_quality": float(audit.quality.mean()),
            "training_metrics": train_metrics,
            "model_weights": model_weights,
            "peak_stability": peak_stability,
            "selected_sampling_recency_config": selected_config,
            "selected_features": [feature_names[i] for i in final_features],
        },
        "location_conditional_on_timing_peak": location,
        "data": {
            "japan_target_event_count": int(len(targets)),
            "target_region_bounds": {"latitude_min": BOUNDS[0], "latitude_max": BOUNDS[1], "longitude_min": BOUNDS[2], "longitude_max": BOUNDS[3]},
            "zone_mode": ZONE_MODE,
            "training_world_hard_negative_slots": int(hard_train.sum()),
            "frozen_recent_world_hard_negative_slots": int(hard_audit.sum()),
            "astronomical_rows": int(len(master)),
            "astronomical_features_before_selection": int(X.shape[1]),
            "astro_master_sha256": sha256(astro_path),
            "japan_catalog_sha256": sha256(japan_path),
            "world_catalog_sha256": sha256(world_path),
        },
        "leakage_contract": {
            "development_events": [slot.strftime("%Y-%m-%d") for slot in dev_slots],
            "frozen_timing_audit_events": [slot.strftime("%Y-%m-%d") for slot in frozen_slots],
            "sampling_and_recency_selected_only_on_development": True,
            "model_weights_selected_only_on_development": True,
            "ensemble_peak_weight_trials": 24000,
            "frozen_non_japan_controls_excluded_from_final_training": True,
            "feature_selection_refit_inside_each_fold": True,
        },
        "model_metadata": model_meta,
    }
    write_json(out_dir / "summary.json", summary)
    report = f"""# V21 — forecast settimanale prospettico {args.run_title}

## Risultato

- **Cutoff sismico:** 1 agosto 2026 00:00 JST (31 luglio 15:00 UTC). Nessun evento di agosto o settembre è usato.
- **Settimana col massimo score:** **{summary['timing']['peak_slot_start_jst']} – {summary['timing']['peak_slot_end_jst']} JST**.
- **Zona più probabile condizionata al picco:** **{location['most_likely_zone']}**, centro {location['estimated_latitude']:.2f} N, {location['estimated_longitude']:.2f} E.
- **Raggio d'incertezza spaziale CV (80%):** {location['uncertainty_radius_km']:.0f} km.
- **Gate temporale:** `{timing_status}`. **Gate spaziale:** `{location['gate_status']}`.

Lo score è un rango empirico comparabile tra modelli, non una probabilità calibrata di terremoto. La zona viene sempre riportata come richiesto, ma il gate stabilisce se la precisione storica è sufficiente.

## Rigorosità prospettica

La scelta di campionamento, raggio attorno agli eventi, quantità di record intermedi, emivita di recenza e numero di feature usa soltanto {len(dev_slots)} fold di sviluppo ({', '.join(summary['leakage_contract']['development_events'])}). I {len(frozen_slots)} eventi {', '.join(summary['leakage_contract']['frozen_timing_audit_events'])} restano congelati fino all'audit. Gli otto grandi eventi recenti fuori dalla regione target sono esclusi dal training finale e misurano le false attivazioni.

I pesi temporali hanno pavimento 0.20: i record antichi non vengono mai azzerati; il contributo cresce verso il cutoff con emivita selezionata di {selected_config['half_life_years']:.0f} anni.

## Audit temporale congelato

- picco esatto: {audit.exact_peak.mean():.0%}
- entro una settimana: {audit.within_one_slot.mean():.0%}
- percentile medio dell'evento: {audit.event_percentile.mean():.3f}
- qualità media: {audit.quality.mean():.3f}
- qualità training finale: {train_metrics['quality']:.3f}; deviazione score training: {train_metrics['score_std']:.3f}
- voto dei modelli informativi sul massimo: {peak_stability['informative_model_peak_votes']}; consenso massimo {peak_stability['informative_model_majority_fraction']:.0%}
- massimo con pesi alternativi basati sulla qualità media: {peak_stability['development_quality_softmax_peak']}

## Audit spaziale congelato

- errore geodetico mediano: {location['audit_median_error_km']:.0f} km
- errore geodetico 80° percentile: {location['audit_q80_error_km']:.0f} km
- baseline di sola recenza, errore mediano: {location['audit_recency_baseline_median_error_km']:.0f} km; miglioramento: {location['audit_median_error_improvement_vs_recency_baseline']:.0%}
- zona corretta: {location['audit_zone_hit_rate']:.0%}
- voto dei modelli per la zona finale: {location['zone_vote']:.0%}

## Interpretazione

Questo è un esperimento di pattern recognition su {len(targets)} soli eventi target, non una previsione sismologica operativa. Se un gate è `FAIL`, il massimo e la zona restano l'output matematico dei modelli ma non soddisfano la precisione predefinita e non vanno presentati come evidenza affidabile di un “Big One”.
"""
    (out_dir / "REPORT.md").write_text(report)
    print(json.dumps({"timing_gate": timing_status, "peak": [summary['timing']['peak_slot_start_jst'], summary['timing']['peak_slot_end_jst']], "location_gate": location["gate_status"], "zone": location["most_likely_zone"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

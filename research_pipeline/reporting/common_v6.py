#!/usr/bin/env python3
"""Leakage-aware timing utilities for the v6 intelligent-ablation pipeline."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler


PROJECT = Path(
    os.environ.get(
        "DLVSWAVE_PROJECT_DIR",
        str(Path(__file__).resolve().parents[1]),
    )
).expanduser().resolve()
REPO = Path(
    os.environ.get(
        "DLVSWAVE_REPO_DIR",
        str(Path(__file__).resolve().parents[2]),
    )
).expanduser().resolve()
sys.path.insert(0, str(REPO))

from deep_nets import DeepConfig, DeepNet  # noqa: E402
from kan_backend import KANConfig, KANReadout  # noqa: E402
from lcs import LCSConfig, UCSPredictor  # noqa: E402


BASES = ("lcs", "kan", "deep_tiny", "deep_wide", "deep_regularized")
SYSTEMS = {
    "lcs_only": ("lcs",),
    "kan_only": ("kan",),
    "deep_tiny": ("deep_tiny",),
    "deep_wide": ("deep_wide",),
    "deep_regularized": ("deep_regularized",),
    "lcs_kan": ("lcs", "kan"),
    "lcs_deep_tiny": ("lcs", "deep_tiny"),
    "lcs_deep_wide": ("lcs", "deep_wide"),
    "lcs_deep_regularized": ("lcs", "deep_regularized"),
    "kan_deep_tiny": ("kan", "deep_tiny"),
    "kan_deep_wide": ("kan", "deep_wide"),
    "kan_deep_regularized": ("kan", "deep_regularized"),
    "lcs_kan_deep_tiny": ("lcs", "kan", "deep_tiny"),
    "lcs_kan_deep_wide": ("lcs", "kan", "deep_wide"),
    "lcs_kan_deep_regularized": ("lcs", "kan", "deep_regularized"),
    "deep_ensemble": ("deep_tiny", "deep_wide", "deep_regularized"),
}
TIMING_META = {
    "date",
    "slot_end_inclusive",
    "timing_target",
    "event_mag",
    "event_latitude",
    "event_longitude",
    "event_id",
    "observed_max_mag",
    "observed_event_time",
    "observed_event_latitude",
    "observed_event_longitude",
    "observed_event_id",
    "is_forecast",
    "stress_target_m70",
    "stress_target_m68",
    "stress_target_m65",
    "complete_at_catalog_snapshot",
}
LOCATION_META = {
    "date",
    "event_time",
    "slot_start",
    "mag",
    "depth",
    "latitude",
    "longitude",
    "event_id",
    "is_forecast",
}


def write_json(path: str | Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n"
    )


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def isolated_indices(events: np.ndarray, radius: int, n: int) -> np.ndarray:
    values: set[int] = set()
    for event in np.asarray(events, int):
        values.update(range(max(0, event - radius), min(n, event + radius + 1)))
    return np.asarray(sorted(values), int)


def sample_timing(
    indices: np.ndarray,
    dates: pd.Series,
    target: np.ndarray,
    start_year: int,
    event_radius: int,
    between_records_per_event: int,
) -> np.ndarray:
    """Select event neighborhoods plus an evenly spaced number of between rows.

    ``between_records_per_event`` is deliberately an integer count. It is never
    interpreted as a fraction of all negatives.
    """
    indices = np.asarray(indices, int)
    years = pd.to_datetime(dates.iloc[indices]).dt.year.to_numpy()
    eligible = indices[years >= int(start_year)]
    positive = eligible[np.asarray(target, int)[eligible] == 1]
    eligible_set = set(eligible.tolist())
    keep: set[int] = set()
    for event in positive:
        keep.update(
            value
            for value in range(event - event_radius, event + event_radius + 1)
            if value in eligible_set
        )
    available = np.asarray(
        [value for value in eligible if value not in keep], dtype=int
    )
    requested = min(
        len(available),
        max(0, int(between_records_per_event)) * len(positive),
    )
    if requested:
        positions = np.linspace(0, len(available) - 1, requested)
        chosen = available[np.unique(np.rint(positions).astype(int))]
        keep.update(chosen.tolist())
    keep.update(positive.tolist())
    return np.asarray(sorted(keep), int)


def repeat_rare(X: np.ndarray, y: np.ndarray, maximum: int = 8):
    y = np.asarray(y, int)
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    if not len(positive) or not len(negative):
        return np.asarray(X), y
    repeat = min(maximum, max(1, int(round(len(negative) / len(positive)))))
    selected = np.concatenate([negative, np.repeat(positive, repeat)])
    return np.asarray(X)[selected], y[selected]


def tied_percentile(values: np.ndarray) -> np.ndarray:
    """Average percentile ranks; invariant to the order of equal values."""
    values = np.asarray(values, float)
    if not len(values):
        return values
    return pd.Series(values).rank(method="average", pct=True).to_numpy(float)


def internal_local_maxima(values: np.ndarray) -> np.ndarray:
    """Strict internal maxima; diagnostic-window endpoints are censored."""
    values = np.asarray(values, float)
    mask = np.zeros(len(values), dtype=bool)
    if len(values) >= 3:
        mask[1:-1] = (
            (values[1:-1] > values[:-2])
            & (values[1:-1] > values[2:])
        )
    return mask


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + math.exp(-float(np.clip(value, -30.0, 30.0)))))


def event_shape_metrics(score: np.ndarray, actual: int) -> dict:
    """All metrics use one direction: larger values mean better performance."""
    score = np.asarray(score, float)
    actual = int(actual)
    percentile = tied_percentile(score)
    peak = int(np.argmax(score))
    near_alignment = float(math.exp(-abs(peak - actual) / 1.5))
    if 0 < actual < len(score) - 1:
        neighbor = max(score[actual - 1], score[actual + 1])
        delta = float(score[actual] - neighbor)
        strict = bool(score[actual] > score[actual - 1] and score[actual] > score[actual + 1])
    else:
        delta = 0.0
        strict = False
    scale = max(
        float(np.quantile(score, 0.90) - np.quantile(score, 0.10)),
        float(np.std(score)),
        1e-6,
    )
    prominence_skill = _sigmoid(4.0 * delta / scale)
    ideal = np.exp(-np.abs(np.arange(len(score)) - actual))
    if np.std(score) > 1e-12:
        correlation = float(np.nan_to_num(np.corrcoef(score, ideal)[0, 1]))
    else:
        correlation = 0.0
    trend_skill = float(np.clip((correlation + 1.0) / 2.0, 0.0, 1.0))
    delayed = score[actual + 2 :]
    delayed_control = (
        _sigmoid(2.0 * (float(score[actual]) - float(np.max(delayed))) / scale)
        if len(delayed)
        else 1.0
    )
    transformations = [score]
    if len(score) >= 3:
        transformations.append(np.convolve(score, [0.25, 0.50, 0.25], mode="same"))
    if len(score) >= 5:
        transformations.append(
            np.convolve(score, [0.10, 0.20, 0.40, 0.20, 0.10], mode="same")
        )
    survival = []
    for transformed in transformations:
        transformed_percentile = tied_percentile(transformed)
        transformed_peak = int(np.argmax(transformed))
        survival.append(
            max(
                float(abs(transformed_peak - actual) <= 1),
                float(transformed_percentile[actual] >= 0.75),
            )
        )
    persistence = float(np.mean(survival))
    weak_peak_retention = float(
        0.30 * percentile[actual]
        + 0.25 * prominence_skill
        + 0.25 * near_alignment
        + 0.20 * persistence
    )
    local = internal_local_maxima(score)
    allowed = np.zeros(len(score), dtype=bool)
    allowed[max(0, actual - 1) : min(len(score), actual + 2)] = True
    false_peaks = int(np.sum(local & ~allowed))
    false_peak_control = float(1.0 / (1.0 + false_peaks))
    return {
        "event_score": float(score[actual]),
        "event_percentile_skill": float(percentile[actual]),
        "argmax_offset_slots": int(peak - actual),
        "near_peak_alignment_skill": near_alignment,
        "signed_local_prominence": delta,
        "local_prominence_skill": prominence_skill,
        "strict_local_peak": strict,
        "trend_skill": trend_skill,
        "delayed_false_peak_control": delayed_control,
        "peak_persistence_skill": persistence,
        "weak_peak_retention_skill": weak_peak_retention,
        "false_peak_control": false_peak_control,
        "false_peak_count": false_peaks,
    }


def score_quality(
    target: np.ndarray,
    score: np.ndarray,
    global_indices: np.ndarray,
    radius: int,
) -> dict:
    """Return only higher-is-better normalized performance components."""
    target = np.asarray(target, int)
    score = np.clip(np.asarray(score, float), 0.0, 1.0)
    global_indices = np.asarray(global_indices, int)
    if not (len(target) == len(score) == len(global_indices)):
        raise ValueError("target, score and global_indices must be aligned")
    prevalence = float(np.mean(target)) if len(target) else 0.0
    if 0 < int(target.sum()) < len(target):
        order = np.argsort(-score, kind="mergesort")
        ranked_target = target[order]
        precision = np.cumsum(ranked_target) / (np.arange(len(target)) + 1)
        average_precision = float(
            np.sum(precision * ranked_target) / max(int(target.sum()), 1)
        )
    else:
        average_precision = prevalence
    ap_skill = float(
        np.clip(
            (average_precision - prevalence) / max(1.0 - prevalence, 1e-9),
            0.0,
            1.0,
        )
    )
    brier_skill = float(np.clip(1.0 - np.mean((score - target) ** 2), 0.0, 1.0))
    lookup = {int(index): position for position, index in enumerate(global_indices)}
    event_profiles = []
    for event_global in global_indices[target == 1]:
        window_global = [
            value
            for value in range(int(event_global) - radius, int(event_global) + radius + 1)
            if value in lookup
        ]
        if len(window_global) < 3:
            continue
        positions = np.asarray([lookup[value] for value in window_global], int)
        actual = int(window_global.index(int(event_global)))
        profile = event_shape_metrics(score[positions], actual)
        profile["event_global_index"] = int(event_global)
        event_profiles.append(profile)
    morphology_keys = (
        "event_percentile_skill",
        "near_peak_alignment_skill",
        "local_prominence_skill",
        "trend_skill",
        "delayed_false_peak_control",
        "peak_persistence_skill",
        "weak_peak_retention_skill",
        "false_peak_control",
    )
    morphology = {
        key: float(np.mean([row[key] for row in event_profiles]))
        if event_profiles
        else 0.0
        for key in morphology_keys
    }
    quality = float(
        0.07 * ap_skill
        + 0.07 * brier_skill
        + 0.13 * morphology["event_percentile_skill"]
        + 0.14 * morphology["near_peak_alignment_skill"]
        + 0.15 * morphology["local_prominence_skill"]
        + 0.08 * morphology["trend_skill"]
        + 0.13 * morphology["delayed_false_peak_control"]
        + 0.10 * morphology["peak_persistence_skill"]
        + 0.08 * morphology["weak_peak_retention_skill"]
        + 0.05 * morphology["false_peak_control"]
    )
    return {
        "n": int(len(target)),
        "positives": int(target.sum()),
        "average_precision_skill": ap_skill,
        "brier_skill": brier_skill,
        **morphology,
        "strict_local_peak_rate": float(
            np.mean([row["strict_local_peak"] for row in event_profiles])
        )
        if event_profiles
        else 0.0,
        "quality_higher_is_better": quality,
        "event_profiles": event_profiles,
        "metric_direction": "all normalized skills: higher is better",
    }


def proxy(kind: str, seed: int):
    if kind == "lcs":
        return ExtraTreesClassifier(
            n_estimators=52,
            max_depth=7,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        )
    if kind == "kan":
        return make_pipeline(
            StandardScaler(),
            SplineTransformer(n_knots=4, degree=2, include_bias=False),
            LogisticRegression(
                max_iter=260, class_weight="balanced", random_state=seed
            ),
        )
    configs = {
        "deep_tiny": (48, 7, 0.08, 0.05),
        "deep_wide": (70, 31, 0.055, 0.10),
        "deep_regularized": (60, 15, 0.05, 1.0),
    }
    iterations, leaves, learning_rate, regularization = configs[kind]
    return HistGradientBoostingClassifier(
        max_iter=iterations,
        max_leaf_nodes=leaves,
        learning_rate=learning_rate,
        l2_regularization=regularization,
        random_state=seed,
    )


def predict_binary(model, X: np.ndarray) -> np.ndarray:
    probability = model.predict_proba(X)
    classes = np.asarray(model.classes_, int)
    if 1 not in classes:
        return np.zeros(len(X), float)
    column = int(np.flatnonzero(classes == 1)[0])
    return np.asarray(probability[:, column], float)


def rank_features(
    X: np.ndarray, y: np.ndarray, feature_indices: list[int], names: list[str], seed: int
) -> tuple[list[int], dict]:
    local_X = np.asarray(X[:, feature_indices], float)
    y = np.asarray(y, int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mutual = np.nan_to_num(
            mutual_info_classif(local_X, y, random_state=seed), nan=0.0
        )
    forest = RandomForestClassifier(
        n_estimators=180,
        max_depth=9,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
    ).fit(local_X, y)
    extra = ExtraTreesClassifier(
        n_estimators=180,
        max_depth=10,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=seed + 1,
        n_jobs=-1,
    ).fit(local_X, y)
    components = (mutual, forest.feature_importances_, extra.feature_importances_)
    positions = []
    for component in components:
        order = np.argsort(-np.asarray(component, float), kind="mergesort")
        rank = np.empty(len(order), int)
        rank[order] = np.arange(len(order))
        positions.append(rank)
    mean_rank = np.mean(np.vstack(positions), axis=0)
    local_order = np.argsort(mean_rank, kind="mergesort")
    ordered = [int(feature_indices[index]) for index in local_order]
    audit = {
        "method": "mean rank: mutual information + random forest + extra trees",
        "ranking": [
            {
                "rank": rank + 1,
                "index": int(feature_indices[local]),
                "feature": names[feature_indices[local]],
                "mean_rank": float(mean_rank[local]),
                "mutual_information": float(mutual[local]),
                "random_forest": float(forest.feature_importances_[local]),
                "extra_trees": float(extra.feature_importances_[local]),
            }
            for rank, local in enumerate(local_order)
        ],
    }
    return ordered, audit


def evaluate_feature_set(
    X: np.ndarray,
    y: np.ndarray,
    train_sample: np.ndarray,
    train_evaluation: np.ndarray,
    validation: np.ndarray,
    features: list[int],
    radius: int,
    seed: int,
) -> dict:
    base_scores = {"training": {}, "validation": {}}
    for member_id, member in enumerate(BASES):
        model = proxy(member, seed + member_id * 97)
        fit_X, fit_y = repeat_rare(X[train_sample][:, features], y[train_sample])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(fit_X, fit_y)
        base_scores["training"][member] = predict_binary(
            model, X[train_evaluation][:, features]
        )
        base_scores["validation"][member] = predict_binary(
            model, X[validation][:, features]
        )
    systems = {}
    for system, members in SYSTEMS.items():
        training_score = np.mean(
            np.vstack([base_scores["training"][member] for member in members]), axis=0
        )
        validation_score = np.mean(
            np.vstack([base_scores["validation"][member] for member in members]), axis=0
        )
        training_metrics = score_quality(
            y[train_evaluation], training_score, train_evaluation, radius
        )
        validation_metrics = score_quality(
            y[validation], validation_score, validation, radius
        )
        combined = float(
            0.25 * training_metrics["quality_higher_is_better"]
            + 0.75 * validation_metrics["quality_higher_is_better"]
        )
        systems[system] = {
            "training": training_metrics,
            "validation": validation_metrics,
            "combined_25train_75validation": combined,
        }
    qualities = np.asarray(
        [payload["combined_25train_75validation"] for payload in systems.values()]
    )
    weak = np.asarray(
        [
            payload["validation"]["weak_peak_retention_skill"]
            for payload in systems.values()
        ]
    )
    aggregate = float(
        0.50 * np.median(qualities)
        + 0.35 * np.quantile(qualities, 0.25)
        + 0.15 * np.min(qualities)
    )
    return {
        "feature_count": len(features),
        "aggregate_quality_higher_is_better": aggregate,
        "system_quality_min": float(np.min(qualities)),
        "system_quality_median": float(np.median(qualities)),
        "weak_peak_retention_min": float(np.min(weak)),
        "weak_peak_retention_median": float(np.median(weak)),
        "systems": systems,
        "base_scores": base_scores,
    }


def model_configuration(
    kind: str,
    epochs_scale: float = 1.0,
    feature_count: int | None = None,
) -> dict:
    """Return the executable model configuration used by ``fit_real_binary``.

    Keeping this metadata beside model construction lets autonomous reports
    describe a run without maintaining a second, manually copied parameter
    table.  ``feature_count`` only affects LCS's active-condition ceiling.
    """
    if kind == "lcs":
        active_conditions = (
            min(12, int(feature_count)) if feature_count is not None else 12
        )
        return {
            "family": "Learning Classifier System",
            "implementation": "UCS rule population",
            "population_size": 280,
            "epochs": max(18, int(round(46 * epochs_scale))),
            "ga_frequency": 30,
            "positive_weight": "automatic",
            "positive_replay": "automatic",
            "max_active_conditions": active_conditions,
            "export_rule_count": 30,
            "validation_split": 0.0,
            "early_stop_patience": 0,
            "final_retrain_full_train": False,
        }
    if kind == "kan":
        return {
            "family": "Kolmogorov–Arnold Network",
            "implementation": "spline KAN readout",
            "hidden_width": 3,
            "hidden_layers": 1,
            "spline_grid": 3,
            "epochs": max(12, int(round(26 * epochs_scale))),
            "learning_rate": 0.018,
            "regularization_lambda": 0.001,
            "device": "CPU",
        }
    if kind == "screening_anchor":
        return {
            "family": "screening-anchor ensemble",
            "implementation": (
                "mean of separately empirical-ranked L2 logistic regression "
                "and ExtraTrees; chronologically refitted in every fold"
            ),
            "logistic_C": 0.25,
            "logistic_solver": "liblinear",
            "extra_trees_estimators": 64,
            "extra_trees_max_depth": 6,
            "extra_trees_min_samples_leaf": 3,
            "extra_trees_max_features": "sqrt",
            "class_weight": "balanced",
            "calibration_reference": "selected training sample",
            "device": "CPU",
        }
    if kind == "logistic":
        return {
            "family": "regularized logistic regression",
            "implementation": "StandardScaler + L2 logistic regression",
            "C": 0.25,
            "max_iter": 800,
            "class_weight": "balanced",
            "solver": "liblinear",
            "calibration_reference": "selected training sample",
            "device": "CPU",
        }
    if kind == "extra_trees":
        return {
            "family": "ExtraTrees ensemble",
            "implementation": "balanced extremely randomized trees",
            "estimators": 128,
            "max_depth": 7,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "class_weight": "balanced",
            "calibration_reference": "selected training sample",
            "device": "CPU",
        }
    deep = {
        "deep_tiny": {
            "hidden_sizes": [20],
            "activation": "ReLU",
            "dropout": 0.0,
            "epochs": max(35, int(round(75 * epochs_scale))),
            "batch_size": 32,
            "learning_rate": 1.5e-3,
            "weight_decay": 1e-4,
        },
        "deep_wide": {
            "hidden_sizes": [96, 48],
            "activation": "GELU",
            "dropout": 0.10,
            "epochs": max(45, int(round(100 * epochs_scale))),
            "batch_size": 32,
            "learning_rate": 1e-3,
            "weight_decay": 2e-4,
        },
        "deep_regularized": {
            "hidden_sizes": [48, 24],
            "activation": "SiLU",
            "dropout": 0.22,
            "epochs": max(45, int(round(95 * epochs_scale))),
            "batch_size": 32,
            "learning_rate": 8e-4,
            "weight_decay": 2e-3,
        },
    }
    if kind not in deep:
        raise KeyError(f"Unknown base model: {kind}")
    return {
        "family": "PyTorch deep neural network",
        "implementation": kind.removeprefix("deep_").replace("_", " "),
        **deep[kind],
        "validation_split": 0.12,
        "early_stop_patience": 10,
        "final_retrain_full_train": True,
        "device": "CPU",
    }


def fit_real_binary(
    kind: str,
    X: np.ndarray,
    y: np.ndarray,
    seed: int,
    epochs_scale: float = 1.0,
):
    X_fit, y_fit = repeat_rare(np.asarray(X, float), np.asarray(y, int))
    if kind == "lcs":
        parameters = model_configuration(kind, epochs_scale, X.shape[1])
        model = UCSPredictor(
            LCSConfig(
                population_size=parameters["population_size"],
                epochs=parameters["epochs"],
                ga_frequency=parameters["ga_frequency"],
                validation_split=parameters["validation_split"],
                early_stop_patience=parameters["early_stop_patience"],
                final_retrain_full_train=parameters["final_retrain_full_train"],
                positive_weight="auto",
                positive_replay="auto",
                max_active_conditions=parameters["max_active_conditions"],
                export_rule_count=parameters["export_rule_count"],
                seed=seed,
            )
        ).fit(X_fit, y_fit)
        return model, lambda values: np.clip(model.predict_score(values), 0.0, 1.0)
    if kind == "kan":
        parameters = model_configuration(kind, epochs_scale, X.shape[1])
        model = KANReadout(
            KANConfig(
                hidden_width=parameters["hidden_width"],
                hidden_layers=parameters["hidden_layers"],
                grid=parameters["spline_grid"],
                epochs=parameters["epochs"],
                lr=parameters["learning_rate"],
                lamb=parameters["regularization_lambda"],
                seed=seed,
                device="cpu",
            )
        ).fit(X_fit, y_fit)
        return model, lambda values: np.clip(model.predict(values), 0.0, 1.0)
    parameters = model_configuration(kind, epochs_scale, X.shape[1])
    config = DeepConfig(
        hidden_sizes=parameters["hidden_sizes"],
        activation=parameters["activation"].lower(),
        dropout=parameters["dropout"],
        epochs=parameters["epochs"],
        batch_size=parameters["batch_size"],
        lr=parameters["learning_rate"],
        weight_decay=parameters["weight_decay"],
    )
    config.seed = seed
    config.device = "cpu"
    config.validation_split = 0.12
    config.early_stop_patience = 10
    config.final_retrain_full_train = True
    model = DeepNet(config).fit(X_fit, y_fit)
    return model, lambda values: np.clip(model.predict(values), 0.0, 1.0)


def empirical_percentile(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Monotone, label-free calibration against the pre-validation distribution."""
    reference = np.sort(np.asarray(reference, float))
    values = np.asarray(values, float)
    if not len(reference) or np.std(reference) < 1e-12:
        return np.full(len(values), 0.5, float)
    left = np.searchsorted(reference, values, side="left")
    right = np.searchsorted(reference, values, side="right")
    return ((left + right) / 2.0 + 0.5) / (len(reference) + 1.0)


def positive_weights(
    qualities: dict[str, float], temperature: float = 0.10, floor: float = 0.05
) -> dict[str, float]:
    names = list(qualities)
    values = np.asarray([qualities[name] for name in names], float)
    raw = np.exp((values - np.max(values)) / max(temperature, 1e-9)) + floor
    raw /= raw.sum()
    return {name: float(raw[index]) for index, name in enumerate(names)}


def tie_aware_consensus(base_scores: dict[str, np.ndarray], members: tuple[str, ...]):
    votes = []
    for member in members:
        percentile = tied_percentile(base_scores[member])
        votes.append((percentile >= 0.75).astype(float))
    return np.mean(np.vstack(votes), axis=0)


def export_lcs_rules(
    model, feature_names: list[str], path: str | Path, context: dict
) -> None:
    population = sorted(
        model.population,
        key=lambda rule: (
            float(rule.fitness) * float(rule.accuracy) * int(rule.numerosity),
            int(rule.experience),
        ),
        reverse=True,
    )
    rules = []
    for rank, rule in enumerate(population[:30], 1):
        rules.append(
            {
                "rank": rank,
                "action": int(rule.action),
                "fitness": float(rule.fitness),
                "accuracy": float(rule.accuracy),
                "experience": int(rule.experience),
                "numerosity": int(rule.numerosity),
                "conditions_scaled": [
                    {
                        "feature": feature_names[int(index)],
                        "low": float(low),
                        "high": float(high),
                    }
                    for index, low, high in rule.conditions
                ],
            }
        )
    write_json(
        path,
        {
            "model": "UCS Learning Classifier System",
            "context": context,
            "coordinate_system": "standardized feature units",
            "rules": rules,
        },
    )


def two_stage_edges(values: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    """Four ordered bands obtained by a median split followed by two child medians."""
    values = np.asarray(values, float)
    root = float(np.median(values))
    lower = values[values < root]
    upper = values[values >= root]
    lower_median = (
        float(np.median(lower)) if len(lower) else (float(bounds[0]) + root) / 2.0
    )
    upper_median = (
        float(np.median(upper)) if len(upper) else (root + float(bounds[1])) / 2.0
    )
    edges = np.asarray(
        [float(bounds[0]), lower_median, root, upper_median, float(bounds[1])],
        float,
    )
    for index in range(1, len(edges)):
        if edges[index] <= edges[index - 1]:
            edges[index] = edges[index - 1] + 1e-6
    return edges


def leaf_labels(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.clip(
        np.digitize(np.asarray(values, float), np.asarray(edges)[1:-1], right=False),
        0,
        3,
    ).astype(int)


def aligned_multiclass_probability(model, values: np.ndarray, classes: int = 4):
    raw = np.asarray(model.predict_proba(values), float)
    output = np.zeros((len(values), classes), float)
    for source, label in enumerate(np.asarray(model.classes_, int)):
        if 0 <= int(label) < classes:
            output[:, int(label)] = raw[:, source]
    return output / np.maximum(output.sum(axis=1, keepdims=True), 1e-12)


def coordinate_metrics(
    actual: np.ndarray,
    probability: np.ndarray,
    edges: np.ndarray,
) -> dict:
    """Location-coordinate skills, all normalized so that higher is better."""
    actual = np.asarray(actual, float)
    probability = np.asarray(probability, float)
    edges = np.asarray(edges, float)
    actual_leaf = leaf_labels(actual, edges)
    predicted_leaf = np.argmax(probability, axis=1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    predicted_center = centers[predicted_leaf]
    absolute_error = np.abs(actual - predicted_center)
    exact = float(np.mean(actual_leaf == predicted_leaf))
    adjacent = float(np.mean(np.abs(actual_leaf - predicted_leaf) <= 1))
    mae_skill = float(
        np.clip(
            1.0 - np.mean(absolute_error) / max(edges[-1] - edges[0], 1e-9),
            0.0,
            1.0,
        )
    )
    if (
        len(actual) > 1
        and np.std(actual) > 1e-12
        and np.std(predicted_center) > 1e-12
    ):
        trend = float(np.nan_to_num(np.corrcoef(actual, predicted_center)[0, 1]))
    else:
        trend = 0.0
    trend_skill = float(np.clip((trend + 1.0) / 2.0, 0.0, 1.0))
    true_band_probability = float(
        np.mean(probability[np.arange(len(actual)), actual_leaf])
    )
    quality = float(
        0.30 * exact
        + 0.15 * adjacent
        + 0.20 * mae_skill
        + 0.15 * trend_skill
        + 0.20 * true_band_probability
    )
    return {
        "n": int(len(actual)),
        "exact_band_accuracy": exact,
        "adjacent_band_accuracy": adjacent,
        "mae_skill": mae_skill,
        "trend_skill": trend_skill,
        "true_band_probability_skill": true_band_probability,
        "quality_higher_is_better": quality,
        "mae_degrees": float(np.mean(absolute_error)),
        "absolute_errors_degrees": absolute_error.tolist(),
        "actual_bands": actual_leaf.tolist(),
        "predicted_bands": predicted_leaf.tolist(),
        "predicted_centers": predicted_center.tolist(),
        "metric_direction": "all selection skills: higher is better",
    }


def fit_threshold_tree(
    kind: str,
    X: np.ndarray,
    leaf: np.ndarray,
    seed: int,
    epochs_scale: float,
):
    """Fit a two-level binary tree that yields four ordered threshold bands."""
    leaf = np.asarray(leaf, int)
    root_target = (leaf >= 2).astype(int)
    lower = np.flatnonzero(leaf < 2)
    upper = np.flatnonzero(leaf >= 2)
    if len(np.unique(root_target)) < 2:
        raise ValueError("Location root threshold has only one class")
    root_model, root_predict = fit_real_binary(
        kind, X, root_target, seed, epochs_scale
    )

    def fit_child(indices: np.ndarray, target: np.ndarray, child_seed: int):
        if len(indices) == 0 or len(np.unique(target)) < 2:
            value = float(np.mean(target)) if len(target) else 0.5
            return None, lambda values: np.full(len(values), value, float)
        return fit_real_binary(
            kind, X[indices], target, child_seed, epochs_scale
        )

    lower_model, lower_predict = fit_child(
        lower, leaf[lower], seed + 1
    )
    upper_model, upper_predict = fit_child(
        upper, (leaf[upper] == 3).astype(int), seed + 2
    )

    def predict(values: np.ndarray):
        root = root_predict(values)
        lower_probability = lower_predict(values)
        upper_probability = upper_predict(values)
        probability = np.column_stack(
            [
                (1.0 - root) * (1.0 - lower_probability),
                (1.0 - root) * lower_probability,
                root * (1.0 - upper_probability),
                root * upper_probability,
            ]
        )
        return probability / np.maximum(
            probability.sum(axis=1, keepdims=True), 1e-12
        )

    return {
        "root": root_model,
        "lower": lower_model,
        "upper": upper_model,
    }, predict


def coordinate_output(
    frame: pd.DataFrame,
    latitude_probability: np.ndarray,
    longitude_probability: np.ndarray,
    latitude_edges: np.ndarray,
    longitude_edges: np.ndarray,
) -> pd.DataFrame:
    latitude_band = np.argmax(latitude_probability, axis=1)
    longitude_band = np.argmax(longitude_probability, axis=1)
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "slot_start": frame["slot_start"].to_numpy(),
            "latitude_band": latitude_band,
            "latitude_low": latitude_edges[latitude_band],
            "latitude_high": latitude_edges[latitude_band + 1],
            "latitude_center": (
                latitude_edges[latitude_band] + latitude_edges[latitude_band + 1]
            )
            / 2.0,
            "longitude_band": longitude_band,
            "longitude_low": longitude_edges[longitude_band],
            "longitude_high": longitude_edges[longitude_band + 1],
            "longitude_center": (
                longitude_edges[longitude_band] + longitude_edges[longitude_band + 1]
            )
            / 2.0,
            "latitude_confidence": np.max(latitude_probability, axis=1),
            "longitude_confidence": np.max(longitude_probability, axis=1),
        }
    )

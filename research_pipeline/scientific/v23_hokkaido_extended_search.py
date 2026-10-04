#!/usr/bin/env python3
"""Extended, development-only ablation and neural search for Hokkaido V23."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import warnings
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


REPO = Path(__file__).resolve().parents[2]
SCIENTIFIC = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCIENTIFIC))
import v21_weekly_recency_forecast as core  # noqa: E402
from deep_nets import DeepConfig, DeepNet  # noqa: E402
from kan_backend import KANConfig, KANReadout  # noqa: E402
from lcs import LCSConfig, UCSPredictor  # noqa: E402


REGION = (39.5, 46.0, 140.0, 150.5)
BODY = re.compile(r"body:([^|]+)\|")
FIELD = re.compile(r"\|eph:([^|]+)\|")
MODEL_NAMES = (
    "logistic",
    "extra_trees",
    "hist_gradient",
    "deep_relu_tiny",
    "deep_tanh",
    "deep_gelu_wide",
    "deep_silu_deep",
    "deep_leaky",
    "kan_small",
    "kan_wide",
    "lcs_sparse",
    "lcs_wide",
)


BODY_GROUPS = {
    "all": None,
    "major_no_minor": {"sun", "mercury", "venus", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"},
    "luminaries_inner": {"sun", "moon", "mercury", "venus", "mars"},
    "outer_and_moons": {"moon", "jupiter", "saturn", "uranus", "neptune", "pluto", "io", "europa", "ganymede", "callisto", "titan"},
    "no_minor": {"sun", "mercury", "venus", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "io", "europa", "ganymede", "callisto", "titan"},
    "no_jovian_moons": {"sun", "mercury", "venus", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "titan", "bennu", "eris", "sedna", "apophis", "2012_vp113", "2015_tg387"},
    "no_sun": "exclude:sun",
    "no_moon": "exclude:moon",
    "no_inner_planets": "exclude:mercury,venus,mars",
    "no_giants": "exclude:jupiter,saturn,uranus,neptune",
    "minor_only": {"bennu", "eris", "sedna", "apophis", "2012_vp113", "2015_tg387"},
}

FIELD_GROUPS = {
    "all": None,
    "no_eclipse": None,
    "eclipse_only": "eclipse_only",
    "angles": {"AZ", "DEC", "DEC_app", "EL", "ObsEclLat", "ObsEclLon", "PABLat", "PABLon", "RA", "RA_app", "alpha_true"},
    "rates_distance": {"DEC_rate", "RA_rate", "r", "r_rate", "ang_width"},
    "distance_motion": {"r", "r_rate", "ang_width"},
    "no_horizon": "exclude:AZ,EL",
    "observer_apparent": {"AZ", "EL", "RA_app", "DEC_app", "ang_width"},
    "longitude_phase": {"ObsEclLon", "PABLon", "RA", "RA_app", "alpha_true"},
}


def feature_mask(names: list[str], body_group: str, field_group: str) -> np.ndarray:
    body_rule = BODY_GROUPS[body_group]
    field_rule = FIELD_GROUPS[field_group]
    indices = []
    for i, name in enumerate(names):
        if name.startswith("eclipse:"):
            if field_group in {"all", "eclipse_only"}:
                indices.append(i)
            continue
        if name.startswith("calendar:"):
            if field_group in {"all", "no_eclipse"}:
                indices.append(i)
            continue
        body_match = BODY.search(name)
        field_match = FIELD.search(name)
        if not body_match or not field_match:
            continue
        body = body_match.group(1)
        field = field_match.group(1)
        body_ok = True
        if isinstance(body_rule, set):
            body_ok = body in body_rule
        elif isinstance(body_rule, str) and body_rule.startswith("exclude:"):
            body_ok = body not in set(body_rule.split(":", 1)[1].split(","))
        field_ok = field_group != "eclipse_only"
        if isinstance(field_rule, set):
            field_ok = field in field_rule
        elif isinstance(field_rule, str) and field_rule.startswith("exclude:"):
            field_ok = field not in set(field_rule.split(":", 1)[1].split(","))
        if body_ok and field_ok:
            indices.append(i)
    return np.asarray(indices, int)


def sample_asymmetric(
    dates: pd.Series,
    y: np.ndarray,
    hard_train: np.ndarray,
    hard_audit: np.ndarray,
    limit: pd.Timestamp,
    pre_radius: int,
    post_radius: int,
    between_per_event: int,
    hard_fraction: float,
    start_year: int,
) -> np.ndarray:
    eligible = np.flatnonzero(
        (dates < limit).to_numpy()
        & (dates.dt.year.to_numpy() >= start_year)
        & ~hard_audit
    )
    positives = eligible[y[eligible] == 1]
    hard = eligible[hard_train[eligible]]
    if len(hard) and hard_fraction < 0.999:
        count = max(1, int(round(len(hard) * hard_fraction)))
        positions = np.unique(np.rint(np.linspace(0, len(hard) - 1, count)).astype(int))
        hard = hard[positions]
    keep: set[int] = set(hard.tolist())
    for event in positives:
        delta = (dates.iloc[eligible] - dates.iloc[event]).dt.days.to_numpy()
        keep.update(eligible[(delta >= -pre_radius * 7) & (delta <= post_radius * 7)].tolist())
    available = np.asarray([i for i in eligible if i not in keep], int)
    requested = min(len(available), max(0, between_per_event * len(positives)))
    if requested:
        positions = np.unique(np.rint(np.linspace(0, len(available) - 1, requested)).astype(int))
        keep.update(available[positions].tolist())
    keep.update(positives.tolist())
    return np.asarray(sorted(keep), int)


def fast_rank(X: np.ndarray, y: np.ndarray, weights: np.ndarray, count: int, seed: int) -> np.ndarray:
    usable = np.flatnonzero(np.std(X, axis=0) > 1e-12)
    if len(usable) <= count:
        return usable
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mi = np.nan_to_num(mutual_info_classif(X[:, usable], y, random_state=seed), nan=0.0)
    forest = ExtraTreesClassifier(
        n_estimators=48,
        max_depth=7,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=seed + 1,
        n_jobs=-1,
    ).fit(X[:, usable], y, sample_weight=weights)
    components = []
    for values in (mi, forest.feature_importances_):
        order = np.argsort(-values, kind="mergesort")
        rank = np.empty(len(order), int)
        rank[order] = np.arange(len(order))
        components.append(rank)
    return usable[np.argsort(np.mean(np.vstack(components), axis=0), kind="mergesort")[:count]]


def fit_fast(name: str, X: np.ndarray, y: np.ndarray, weights: np.ndarray, seed: int) -> Callable[[np.ndarray], np.ndarray]:
    scaler = StandardScaler().fit(X)
    Xs = np.clip(scaler.transform(X), -8, 8)
    if name == "logistic":
        model = LogisticRegression(C=0.25, max_iter=1000, solver="liblinear", random_state=seed).fit(Xs, y, sample_weight=weights)
    elif name == "extra_trees":
        model = ExtraTreesClassifier(n_estimators=96, max_depth=7, min_samples_leaf=2, max_features="sqrt", random_state=seed, n_jobs=-1).fit(Xs, y, sample_weight=weights)
    else:
        model = HistGradientBoostingClassifier(max_iter=90, max_leaf_nodes=15, learning_rate=0.055, l2_regularization=0.5, random_state=seed).fit(Xs, y, sample_weight=weights)
    return lambda values: model.predict_proba(np.clip(scaler.transform(values), -8, 8))[:, list(model.classes_).index(1)]


def fit_extended(name: str, X: np.ndarray, y: np.ndarray, weights: np.ndarray, seed: int) -> tuple[Callable[[np.ndarray], np.ndarray], dict]:
    if name in {"logistic", "extra_trees", "hist_gradient"}:
        predictor, meta = core.fit_binary_model(name, X, y, weights, seed)
        return predictor, meta
    scaler = StandardScaler().fit(X)
    Xs = np.clip(scaler.transform(X), -8, 8)
    if name.startswith("deep_"):
        settings = {
            "deep_relu_tiny": ([20], "relu", 0.0, 55, 1.5e-3, 1e-4),
            "deep_tanh": ([32, 16], "tanh", 0.10, 70, 1.0e-3, 5e-4),
            "deep_gelu_wide": ([96, 48], "gelu", 0.12, 85, 8e-4, 8e-4),
            "deep_silu_deep": ([64, 32, 16], "silu", 0.25, 90, 7e-4, 2e-3),
            "deep_leaky": ([48, 24], "leakyrelu", 0.16, 75, 9e-4, 1e-3),
        }
        hidden, activation, dropout, epochs, lr, decay = settings[name]
        cfg = DeepConfig(
            hidden_sizes=hidden,
            activation=activation,
            output_activation="sigmoid",
            dropout=dropout,
            epochs=epochs,
            batch_size=32,
            lr=lr,
            weight_decay=decay,
            loss="binary_cross_entropy",
            validation_split=0.15,
            early_stop_patience=12,
            final_retrain_full_train=True,
            sample_weights=weights.tolist(),
            seed=seed,
            device="cpu",
        )
        model = DeepNet(cfg).fit(Xs, y)
        return (lambda values: np.clip(model.predict(np.clip(scaler.transform(values), -8, 8)), 0, 1)), {"family": "PyTorch MLP", "variant": name, "config": asdict(cfg) | {"sample_weights": "stored separately"}}
    if name.startswith("kan_"):
        wide = name == "kan_wide"
        cfg = KANConfig(hidden_width=5 if wide else 2, hidden_layers=1, grid=4 if wide else 2, epochs=32 if wide else 22, lr=0.014 if wide else 0.020, lamb=0.0015 if wide else 0.0008, seed=seed, device="cpu")
        model = KANReadout(cfg).fit(Xs, y, sample_weight=weights)
        return (lambda values: np.clip(model.predict(np.clip(scaler.transform(values), -8, 8)), 0, 1)), {"family": "spline KAN", "variant": name, "config": asdict(cfg)}
    if name.startswith("lcs_"):
        wide = name == "lcs_wide"
        cfg = LCSConfig(population_size=420 if wide else 180, epochs=55 if wide else 34, ga_frequency=28, validation_split=0.0, early_stop_patience=0, final_retrain_full_train=False, positive_weight="auto", positive_replay="auto", max_active_conditions=min(16 if wide else 8, X.shape[1]), sample_weights=weights.tolist(), seed=seed)
        model = UCSPredictor(cfg).fit(Xs, y)
        return (lambda values: np.clip(model.predict_score(np.clip(scaler.transform(values), -8, 8)), 0, 1)), {"family": "UCS LCS", "variant": name, "config": asdict(cfg) | {"sample_weights": "stored separately"}}
    raise KeyError(name)


def config_indices(config: dict, names: list[str]) -> np.ndarray:
    return feature_mask(names, config["body_group"], config["field_group"])


def training_for_fold(config: dict, master: pd.DataFrame, y: np.ndarray, hard_train: np.ndarray, hard_audit: np.ndarray, event_slot: pd.Timestamp) -> np.ndarray:
    return sample_asymmetric(
        master.date,
        y,
        hard_train,
        hard_audit,
        event_slot - pd.Timedelta(days=28),
        int(config["pre_radius"]),
        int(config["post_radius"]),
        int(config["between_per_event"]),
        float(config["hard_fraction"]),
        int(config["start_year"]),
    )


def screen_config(config: dict, config_id: int, X: np.ndarray, names: list[str], master: pd.DataFrame, y: np.ndarray, hard_train: np.ndarray, hard_audit: np.ndarray, dev_slots: list[pd.Timestamp], date_to_index: dict[pd.Timestamp, int], seed: int) -> dict:
    allowed = config_indices(config, names)
    if len(allowed) < 8:
        raise RuntimeError("too few allowed features")
    fold_metrics = []
    train_metrics = []
    for fold, event_slot in enumerate(dev_slots):
        train = training_for_fold(config, master, y, hard_train, hard_audit, event_slot)
        validation = core.date_window_indices(date_to_index, event_slot, 4)
        recency = core.recency_weights(master.date.iloc[train], event_slot, float(config["half_life_years"]))
        weights = core.balanced_weights(y[train], recency)
        local = fast_rank(X[train][:, allowed], y[train], weights, int(config["feature_count"]), seed + config_id * 31 + fold)
        selected = allowed[local]
        val_members, train_members = [], []
        for model_no, model_name in enumerate(("logistic", "extra_trees", "hist_gradient")):
            predictor = fit_fast(model_name, X[train][:, selected], y[train], weights, seed + config_id * 1000 + fold * 10 + model_no)
            raw_train = predictor(X[train][:, selected])
            train_members.append(core.empirical_percentile(raw_train, raw_train))
            val_members.append(core.empirical_percentile(raw_train, predictor(X[validation][:, selected])))
        score = np.mean(val_members, axis=0)
        actual = int(np.flatnonzero(y[validation] == 1)[0])
        fold_metrics.append(core.peak_metrics(score, actual))
        train_metrics.append(core.training_signal(y[train], np.mean(train_members, axis=0)))
    recent = np.linspace(0.35, 1.0, len(dev_slots))
    exact = np.asarray([row["exact_peak"] for row in fold_metrics], float)
    within = np.asarray([row["within_one_slot"] for row in fold_metrics], float)
    quality = np.asarray([row["quality"] for row in fold_metrics], float)
    train_quality = np.asarray([row["quality"] for row in train_metrics], float)
    objective = float(0.48 * np.average(exact, weights=recent) + 0.22 * np.average(within, weights=recent) + 0.20 * np.average(quality, weights=recent) + 0.10 * np.average(train_quality, weights=recent))
    return {
        "config_id": config_id,
        **config,
        "allowed_feature_count": len(allowed),
        "dev_exact_recent_weighted": float(np.average(exact, weights=recent)),
        "dev_within_one_recent_weighted": float(np.average(within, weights=recent)),
        "dev_quality_recent_weighted": float(np.average(quality, weights=recent)),
        "training_quality_recent_weighted": float(np.average(train_quality, weights=recent)),
        "screen_objective": objective,
    }


def generate_configs(seed: int, count: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    patterns = [(2, 2), (4, 4), (6, 6), (8, 8), (8, 2), (2, 8), (6, 0), (0, 6)]
    values = []
    # Wrappers may deliberately replace BODY_GROUPS (for example, the V25
    # 1611--2026 run excludes bodies without a defensible full-span ephemeris).
    # Keep the deterministic baseline valid under those restricted universes.
    baseline_body_group = "all" if "all" in BODY_GROUPS else next(iter(BODY_GROUPS))
    baseline = {"body_group": baseline_body_group, "field_group": "all", "pre_radius": 6, "post_radius": 6, "between_per_event": 2, "half_life_years": 80.0, "feature_count": 36, "hard_fraction": 1.0, "start_year": 1900}
    values.append(baseline)
    # Reserve deterministic one-factor ablations before the random combinations
    # so every reasonably sized search measures each body and field family at
    # least once, including eclipse-only and no-eclipse controls.
    for field_group in FIELD_GROUPS:
        row = {**baseline, "field_group": field_group}
        if field_group == "eclipse_only":
            row["feature_count"] = 18
        if row not in values:
            values.append(row)
    for body_group in BODY_GROUPS:
        row = {**baseline, "body_group": body_group}
        if row not in values:
            values.append(row)
    while len(values) < count:
        pre, post = patterns[int(rng.integers(len(patterns)))]
        row = {
            "body_group": str(rng.choice(list(BODY_GROUPS))),
            "field_group": str(rng.choice(list(FIELD_GROUPS))),
            "pre_radius": pre,
            "post_radius": post,
            "between_per_event": int(rng.choice([0, 2, 4, 8])),
            "half_life_years": float(rng.choice([10.0, 20.0, 40.0, 80.0])),
            "feature_count": int(rng.choice([18, 30, 42])),
            "hard_fraction": float(rng.choice([0.5, 1.0])),
            "start_year": int(rng.choice([1900, 1930, 1940])),
        }
        if row not in values:
            values.append(row)
    return values


def summarize_ablation(screen: pd.DataFrame, column: str) -> pd.DataFrame:
    baseline = float(screen.loc[screen.config_id == 0, "screen_objective"].iloc[0])
    rows = []
    for value, frame in screen.groupby(column):
        rows.append({
            "dimension": column,
            "value": value,
            "trials": len(frame),
            "best_objective": frame.screen_objective.max(),
            "median_objective": frame.screen_objective.median(),
            "best_minus_baseline": frame.screen_objective.max() - baseline,
            "median_minus_baseline": frame.screen_objective.median() - baseline,
        })
    return pd.DataFrame(rows).sort_values("best_objective", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--astro-master", required=True)
    parser.add_argument("--japan-catalog", required=True)
    parser.add_argument("--world-catalog", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--screen-trials", type=int, default=320)
    parser.add_argument("--full-configs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=623911)
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    core.BOUNDS = REGION
    core.ZONE_MODE = "hokkaido_corridor"

    master = pd.read_csv(args.astro_master, low_memory=False).sort_values("date").reset_index(drop=True)
    master["date"] = pd.to_datetime(master.date)
    X, names = core.transformed_features(master)
    japan = core.load_catalog(Path(args.japan_catalog))
    world = core.load_catalog(Path(args.world_catalog))
    inside = japan.latitude.between(REGION[0], REGION[1]) & japan.longitude.between(REGION[2], REGION[3])
    targets = core.strongest_by_slot(japan.loc[(japan.mag >= 7.9) & inside].copy())
    outside = ~(world.latitude.between(REGION[0], REGION[1]) & world.longitude.between(REGION[2], REGION[3]))
    hard_events = core.strongest_by_slot(world.loc[outside & (world.mag >= 7.9)].copy())
    date_to_index = {pd.Timestamp(date): i for i, date in enumerate(master.date)}
    y = np.zeros(len(master), int)
    for slot in targets.slot_start:
        y[date_to_index[pd.Timestamp(slot)]] = 1
    hard_by_slot = hard_events.loc[~hard_events.slot_start.isin(targets.slot_start)].copy()
    recent_pool = hard_by_slot.loc[hard_by_slot.mag >= 8.3].sort_values("time_utc")
    if recent_pool.slot_start.nunique() < 8:
        recent_pool = hard_by_slot.loc[hard_by_slot.mag >= 8.1].sort_values("time_utc")
    audit_negative_slots = set(recent_pool.drop_duplicates("slot_start", keep="last").tail(8).slot_start)
    hard_train = np.zeros(len(master), bool)
    hard_audit = np.zeros(len(master), bool)
    for slot in hard_by_slot.slot_start:
        slot = pd.Timestamp(slot)
        if slot in date_to_index:
            (hard_audit if slot in audit_negative_slots else hard_train)[date_to_index[slot]] = True
    positive_slots = [pd.Timestamp(value) for value in targets.slot_start]
    dev_slots = positive_slots[2:6]
    frozen_slots = positive_slots[-4:]
    if dev_slots[-1] >= frozen_slots[0]:
        raise RuntimeError("Development and frozen folds overlap")

    configs = generate_configs(args.seed, args.screen_trials)
    screen_rows = []
    for config_id, config in enumerate(configs):
        try:
            row = screen_config(config, config_id, X, names, master, y, hard_train, hard_audit, dev_slots, date_to_index, args.seed)
            row["status"] = "OK"
        except Exception as exc:
            row = {"config_id": config_id, **config, "status": "ERROR", "error": str(exc), "screen_objective": -1.0}
        screen_rows.append(row)
        if (config_id + 1) % 20 == 0:
            print(f"[SCREEN] {config_id + 1}/{len(configs)}", flush=True)
    screen = pd.DataFrame(screen_rows).sort_values("screen_objective", ascending=False).reset_index(drop=True)
    screen.to_csv(out / "extended_screen_trials.csv", index=False)
    ablations = pd.concat([summarize_ablation(screen[screen.status == "OK"], column) for column in ("body_group", "field_group", "pre_radius", "post_radius", "between_per_event", "half_life_years", "hard_fraction", "start_year")], ignore_index=True)
    ablations.to_csv(out / "ablation_effects.csv", index=False)

    selected_screen = screen[screen.status == "OK"].head(args.full_configs).copy()
    full_rows = []
    full_payloads: dict[int, dict] = {}
    for rank, row in selected_screen.iterrows():
        config_id = int(row.config_id)
        config = {key: row[key] for key in ("body_group", "field_group", "pre_radius", "post_radius", "between_per_event", "half_life_years", "feature_count", "hard_fraction", "start_year")}
        config.update({key: int(config[key]) for key in ("pre_radius", "post_radius", "between_per_event", "feature_count", "start_year")})
        config.update({key: float(config[key]) for key in ("half_life_years", "hard_fraction")})
        allowed = config_indices(config, names)
        predictions: dict[tuple[str, str, pd.Timestamp], np.ndarray] = {}
        fold_records = []
        model_meta = {}
        print(f"[FULL] config {rank + 1}/{len(selected_screen)} id={config_id}", flush=True)
        for fold, event_slot in enumerate(dev_slots, 1):
            train = training_for_fold(config, master, y, hard_train, hard_audit, event_slot)
            validation = core.date_window_indices(date_to_index, event_slot, 4)
            recency = core.recency_weights(master.date.iloc[train], event_slot, config["half_life_years"])
            weights = core.balanced_weights(y[train], recency)
            local = core.rank_features(X[train][:, allowed], y[train], weights, config["feature_count"], args.seed + config_id * 100 + fold)
            selected = allowed[local]
            actual = int(np.flatnonzero(y[validation] == 1)[0])
            for model_no, model_name in enumerate(MODEL_NAMES):
                try:
                    predictor, meta = fit_extended(model_name, X[train][:, selected], y[train], weights, args.seed + config_id * 10000 + fold * 100 + model_no)
                    model_meta.setdefault(model_name, meta)
                    raw_train = predictor(X[train][:, selected])
                    train_score = core.empirical_percentile(raw_train, raw_train)
                    val_score = core.empirical_percentile(raw_train, predictor(X[validation][:, selected]))
                    predictions[("development", model_name, event_slot)] = val_score
                    metrics = core.peak_metrics(val_score, actual)
                    tmetrics = core.training_signal(y[train], train_score)
                    fold_records.append({"group": "development", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, "training_quality": tmetrics["quality"], "status": "OK", **metrics})
                except Exception as exc:
                    fold_records.append({"group": "development", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, "status": "ERROR", "error": str(exc)})
        fold_table = pd.DataFrame(fold_records)
        complete = [name for name in MODEL_NAMES if ((fold_table.model == name) & (fold_table.status == "OK")).sum() == len(dev_slots)]
        if len(complete) < 5:
            continue
        quality = {name: float(fold_table[(fold_table.model == name) & (fold_table.status == "OK")].quality.mean()) for name in complete}
        initial = core.softmax_weights(quality)
        weights_selected, weight_search = core.optimize_timing_weights(predictions, complete, dev_slots, fold_table, initial, args.seed + config_id, trials=8000)
        best = weight_search.iloc[0]
        full_rows.append({"config_id": config_id, **config, "complete_models": len(complete), "dev_weight_objective": best.objective, "dev_exact_recent_weighted": best.exact_rate_recent_weighted, "dev_within_one_recent_weighted": best.within_one_rate_recent_weighted, "dev_quality_recent_weighted": best.quality_recent_weighted, "dev_training_quality": best.training_quality_weighted})
        full_payloads[config_id] = {"config": config, "allowed": allowed, "complete": complete, "weights": weights_selected, "fold_table": fold_table, "model_meta": model_meta}
    full = pd.DataFrame(full_rows).sort_values(["dev_exact_recent_weighted", "dev_within_one_recent_weighted", "dev_quality_recent_weighted", "dev_training_quality"], ascending=False).reset_index(drop=True)
    full.to_csv(out / "full_neural_config_comparison.csv", index=False)
    if full.empty:
        raise RuntimeError("No full neural configuration completed")
    best_id = int(full.loc[0, "config_id"])
    payload = full_payloads[best_id]
    config = payload["config"]
    allowed = payload["allowed"]
    complete = payload["complete"]
    model_weights = payload["weights"]
    print(f"[SELECTED] config_id={best_id} models={len(complete)}", flush=True)

    audit_predictions = {}
    audit_records = []
    validation_rows = []
    for fold, event_slot in enumerate(frozen_slots, 1):
        train = training_for_fold(config, master, y, hard_train, hard_audit, event_slot)
        validation = core.date_window_indices(date_to_index, event_slot, 4)
        recency = core.recency_weights(master.date.iloc[train], event_slot, config["half_life_years"])
        weights = core.balanced_weights(y[train], recency)
        local = core.rank_features(X[train][:, allowed], y[train], weights, config["feature_count"], args.seed + 80000 + fold)
        selected = allowed[local]
        member_scores = {}
        for model_no, model_name in enumerate(complete):
            predictor, _ = fit_extended(model_name, X[train][:, selected], y[train], weights, args.seed + 81000 + fold * 100 + model_no)
            raw_train = predictor(X[train][:, selected])
            member_scores[model_name] = core.empirical_percentile(raw_train, predictor(X[validation][:, selected]))
        score = sum(model_weights[name] * member_scores[name] for name in complete)
        actual = int(np.flatnonzero(y[validation] == 1)[0])
        metrics = core.peak_metrics(score, actual)
        audit_records.append({"group": "frozen_audit", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), **metrics})
        for position, (index, value) in enumerate(zip(validation, score)):
            validation_rows.append({"group": "frozen_audit", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), "window_position": position - actual, "date": master.date.iloc[index].strftime("%Y-%m-%d"), "is_event_slot": position == actual, "ensemble_score": float(value)})
    audit_table = pd.DataFrame(audit_records)
    audit_table.to_csv(out / "timing_ensemble_fold_metrics.csv", index=False)
    pd.DataFrame(validation_rows).to_csv(out / "timing_validation_window_predictions.csv", index=False)

    final_train = sample_asymmetric(master.date, y, hard_train, hard_audit, core.FORECAST_START, config["pre_radius"], config["post_radius"], config["between_per_event"], config["hard_fraction"], config["start_year"])
    final_recency = core.recency_weights(master.date.iloc[final_train], core.FORECAST_START, config["half_life_years"])
    final_weights = core.balanced_weights(y[final_train], final_recency)
    final_local = core.rank_features(X[final_train][:, allowed], y[final_train], final_weights, config["feature_count"], args.seed + 90000)
    final_features = allowed[final_local]
    forecast_idx = np.flatnonzero(((master.date >= core.FORECAST_START) & (master.date <= core.FORECAST_LAST_START)).to_numpy())
    negative_idx = np.flatnonzero(hard_audit)
    forecast = pd.DataFrame({"slot_start_jst": master.date.iloc[forecast_idx].dt.strftime("%Y-%m-%d"), "slot_end_jst": (master.date.iloc[forecast_idx] + pd.Timedelta(days=6)).dt.strftime("%Y-%m-%d")}).reset_index(drop=True)
    train_scores, negative_scores = {}, {}
    for model_no, model_name in enumerate(complete):
        predictor, _ = fit_extended(model_name, X[final_train][:, final_features], y[final_train], final_weights, args.seed + 91000 + model_no)
        raw_train = predictor(X[final_train][:, final_features])
        train_scores[model_name] = core.empirical_percentile(raw_train, raw_train)
        forecast[model_name] = core.empirical_percentile(raw_train, predictor(X[forecast_idx][:, final_features]))
        negative_scores[model_name] = core.empirical_percentile(raw_train, predictor(X[negative_idx][:, final_features]))
    forecast["ensemble_score"] = sum(model_weights[name] * forecast[name] for name in complete)
    forecast["rank"] = forecast.ensemble_score.rank(method="min", ascending=False).astype(int)
    forecast.to_csv(out / "forecast_weekly_aug_sep_2026.csv", index=False)
    peak_position = int(np.argmax(forecast.ensemble_score.to_numpy(float)))
    peak_index = int(forecast_idx[peak_position])
    train_score = sum(model_weights[name] * train_scores[name] for name in complete)
    training_metrics = core.training_signal(y[final_train], train_score)
    negative_score = sum(model_weights[name] * negative_scores[name] for name in complete)
    pd.DataFrame({"slot_start_jst": master.date.iloc[negative_idx].dt.strftime("%Y-%m-%d"), "ensemble_score": negative_score}).to_csv(out / "frozen_world_hard_negative_scores.csv", index=False)

    event_indices = np.asarray([date_to_index[pd.Timestamp(slot)] for slot in targets.slot_start], int)
    location = core.run_location(X, names, event_indices, targets, positive_slots[3:6], frozen_slots, X[[peak_index]], out, args.seed + 100000)
    timing_checks = {
        "frozen_exact_peak_rate_ge_0_75": bool(audit_table.exact_peak.mean() >= 0.75),
        "frozen_all_within_one_slot": bool(audit_table.within_one_slot.all()),
        "frozen_mean_event_percentile_ge_0_85": bool(audit_table.event_percentile.mean() >= 0.85),
        "frozen_mean_quality_ge_0_70": bool(audit_table.quality.mean() >= 0.70),
        "training_quality_ge_0_55": bool(training_metrics["quality"] >= 0.55),
        "hard_negative_mean_below_0_65": bool(np.mean(negative_score) < 0.65),
        "hard_negative_p90_below_0_85": bool(np.quantile(negative_score, 0.9) < 0.85),
    }
    timing_status = "PASS" if all(timing_checks.values()) else "FAIL_REPORTED_NOT_VALIDATED"
    ablation_top = ablations.sort_values("best_minus_baseline", ascending=False).head(20).to_dict(orient="records")
    summary = {
        "run": "hokkaido-morioka-south-kurils-m79plus-7d-v23-extended-neural-ablation",
        "scientific_status": "experimental pattern-model output; not an operational earthquake prediction",
        "cutoff": {"jst_end_exclusive": "2026-08-01T00:00:00+09:00", "august_seismic_observations_used": 0},
        "search": {"screen_trials": len(screen), "full_neural_configs": len(full), "model_families": list(MODEL_NAMES), "selected_config_id": best_id, "selected_config": config, "selected_model_weights": model_weights, "top_ablation_effects": ablation_top},
        "timing": {"gate_status": timing_status, "gate_checks": timing_checks, "peak_slot_start_jst": forecast.loc[peak_position, "slot_start_jst"], "peak_slot_end_jst": forecast.loc[peak_position, "slot_end_jst"], "peak_ensemble_score": float(forecast.loc[peak_position, "ensemble_score"]), "frozen_audit_exact_rate": float(audit_table.exact_peak.mean()), "frozen_audit_within_one_rate": float(audit_table.within_one_slot.mean()), "frozen_audit_mean_event_percentile": float(audit_table.event_percentile.mean()), "frozen_audit_mean_quality": float(audit_table.quality.mean()), "training_metrics": training_metrics},
        "location_conditional_on_timing_peak": location,
        "data": {"target_event_count": len(targets), "target_region_bounds": {"latitude_min": REGION[0], "latitude_max": REGION[1], "longitude_min": REGION[2], "longitude_max": REGION[3]}, "astronomical_rows": len(master), "astronomical_features": X.shape[1]},
        "leakage_contract": {"development_events": [slot.strftime("%Y-%m-%d") for slot in dev_slots], "frozen_timing_audit_events": [slot.strftime("%Y-%m-%d") for slot in frozen_slots], "frozen_audit_used_for_search": False, "same_frozen_events_for_timing_and_location": True},
    }
    core.write_json(out / "summary.json", summary)
    report = f"""# V23 extended neural/ablation search — Morioka–Hokkaido–Curili meridionali

- Screen combinations: {len(screen)}; full neural configurations: {len(full)}; model families: {len(MODEL_NAMES)}.
- Selected peak: **{summary['timing']['peak_slot_start_jst']} – {summary['timing']['peak_slot_end_jst']} JST**.
- Conditional location: **{location['most_likely_zone']}**, {location['estimated_latitude']:.2f} N, {location['estimated_longitude']:.2f} E, radius CV80 {location['uncertainty_radius_km']:.0f} km.
- Timing gate: `{timing_status}`; location gate: `{location['gate_status']}`.

## Frozen timing audit

- exact peak: {audit_table.exact_peak.mean():.0%}
- within one week: {audit_table.within_one_slot.mean():.0%}
- mean event percentile: {audit_table.event_percentile.mean():.3f}
- mean quality: {audit_table.quality.mean():.3f}
- final training quality: {training_metrics['quality']:.3f}

All {len(screen)} screen trials and all neural/model-weight choices used only the development folds {', '.join(summary['leakage_contract']['development_events'])}. The audit events {', '.join(summary['leakage_contract']['frozen_timing_audit_events'])} were applied once after selection.
"""
    (out / "REPORT.md").write_text(report)
    print(json.dumps({"timing_gate": timing_status, "peak": [summary["timing"]["peak_slot_start_jst"], summary["timing"]["peak_slot_end_jst"]], "location_gate": location["gate_status"], "zone": location["most_likely_zone"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

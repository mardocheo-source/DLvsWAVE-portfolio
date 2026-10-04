#!/usr/bin/env python3
"""Train and validate the parameter-driven V20 six-hour time-band experiment."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import signal
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from common_v14 import (
    BASES,
    SYSTEMS,
    fit_real_binary,
    positive_weights,
    proxy,
    rank_features,
    write_json,
)


PROJECT: Path


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-dir", type=Path, required=True)
    value.add_argument("--config", type=Path, default=None)
    return value


def resolve(project: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project / path).resolve()


@contextmanager
def hard_time_limit(seconds: float, label: str):
    """Apply a real wall-clock limit to a complete multiclass fit attempt."""
    seconds = float(seconds)
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def timeout_handler(_signum, _frame):
        raise TimeoutError(f"{label} exceeded the {seconds:g}s hard limit")

    previous = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous)


def circular_distance(actual: np.ndarray, predicted: np.ndarray, classes: int) -> np.ndarray:
    delta = np.abs(np.asarray(actual, int) - np.asarray(predicted, int))
    return np.minimum(delta, classes - delta)


def time_band_metrics(
    actual: np.ndarray,
    probability: np.ndarray,
    weak_ratio: float,
    adjacent_credit: float,
) -> dict:
    actual = np.asarray(actual, int)
    probability = np.asarray(probability, float)
    classes = probability.shape[1]
    predicted = np.argmax(probability, axis=1)
    distance = circular_distance(actual, predicted, classes)
    true_probability = probability[np.arange(len(actual)), actual]
    maximum = np.max(probability, axis=1)
    exact = predicted == actual
    weak = (~exact) & (distance <= 1) & (true_probability >= weak_ratio * maximum)
    qualified = exact | weak
    graded = np.where(exact, 1.0, np.where(distance == 1, adjacent_credit, 0.0))
    one_hot = np.eye(classes)[actual]
    brier = np.sum((probability - one_hot) ** 2, axis=1)
    uniform_brier = 1.0 - 1.0 / classes
    brier_skill = np.clip(1.0 - brier / uniform_brier, 0.0, 1.0)
    confidence_lift = np.clip(
        (true_probability - 1.0 / classes) / (1.0 - 1.0 / classes), 0.0, 1.0
    )
    quality_rows = (
        0.30 * exact.astype(float)
        + 0.20 * qualified.astype(float)
        + 0.15 * graded
        + 0.20 * confidence_lift
        + 0.15 * brier_skill
    )
    return {
        "events": int(len(actual)),
        "exact_accuracy": float(np.mean(exact)),
        "qualified_accuracy_exact_or_weak": float(np.mean(qualified)),
        "adjacent_or_exact_accuracy": float(np.mean(distance <= 1)),
        "mean_circular_band_error": float(np.mean(distance)),
        "mean_true_band_probability": float(np.mean(true_probability)),
        "multiclass_brier_skill": float(np.mean(brier_skill)),
        "quality_higher_is_better": float(np.mean(quality_rows)),
        "weak_recoveries": int(np.sum(weak)),
        "predicted_bands": predicted.tolist(),
        "circular_band_errors": distance.tolist(),
        "true_band_probabilities": true_probability.tolist(),
        "qualified_rows": qualified.tolist(),
        "quality_rows": quality_rows.tolist(),
    }


def align_probability(model, values: np.ndarray, classes: int) -> np.ndarray:
    raw = np.asarray(model.predict_proba(values), float)
    output = np.zeros((len(values), classes), float)
    for index, label in enumerate(np.asarray(model.classes_, int)):
        if 0 <= int(label) < classes:
            output[:, int(label)] = raw[:, index]
    output = np.clip(output, 1e-9, None)
    return output / output.sum(axis=1, keepdims=True)


def fit_multiclass_ovr(
    kind: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_predict: np.ndarray,
    classes: int,
    seed: int,
    epochs_scale: float,
    time_limit_seconds: float,
) -> tuple[np.ndarray, dict]:
    scaler = StandardScaler().fit(X_train)
    train_scaled = scaler.transform(X_train)
    predict_scaled = scaler.transform(X_predict)
    predictions = []
    started = time.perf_counter()
    with hard_time_limit(time_limit_seconds, f"{kind} multiclass final attempt"):
        for class_index in range(classes):
            target = (np.asarray(y_train, int) == class_index).astype(int)
            _, predict = fit_real_binary(
                kind,
                train_scaled,
                target,
                seed + class_index * 101,
                epochs_scale,
            )
            predictions.append(np.asarray(predict(predict_scaled), float))
    probability = np.column_stack(predictions)
    probability = np.clip(probability, 1e-9, None)
    probability /= probability.sum(axis=1, keepdims=True)
    elapsed = float(time.perf_counter() - started)
    return probability, {
        "family": kind,
        "seconds": elapsed,
        "binary_fits": classes,
        "training_events": int(len(y_train)),
        "feature_count": int(X_train.shape[1]),
        "hard_time_limit_seconds": float(time_limit_seconds),
        "finished_within_time_limit": bool(elapsed <= time_limit_seconds),
    }


def direct_proxy_probability(kind: str, X_train, y_train, X_test, classes, seed):
    model = proxy(kind, seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(X_train, y_train)
    return align_probability(model, X_test, classes)


def chronological_predictions(
    kind: str,
    X: np.ndarray,
    y: np.ndarray,
    validation_indices: list[int],
    features: list[int],
    classes: int,
    seed: int,
    epochs_scale: float,
    time_limit_seconds: float,
) -> tuple[np.ndarray, list[dict]]:
    rows = []
    runtime = []
    for fold, event_index in enumerate(validation_indices):
        train = np.arange(event_index, dtype=int)
        probability, audit = fit_multiclass_ovr(
            kind,
            X[train][:, features],
            y[train],
            X[[event_index]][:, features],
            classes,
            seed + fold * 1009,
            epochs_scale,
            time_limit_seconds,
        )
        rows.append(probability[0])
        runtime.append({"fold": fold + 1, "event_index": event_index, **audit})
    return np.vstack(rows), runtime


def system_probability(base: dict[str, np.ndarray], members: tuple[str, ...]) -> np.ndarray:
    return np.mean(np.stack([base[member] for member in members]), axis=0)


def select_diverse_systems(
    rows: list[dict], maximum: int, minimum_diversity: float
) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (-row["quality"], row["system"]))
    selected = []
    for row in ordered:
        members = set(row["members_list"])
        if not selected:
            selected.append(row)
        else:
            diversity = [
                1.0
                - len(members.intersection(set(existing["members_list"])))
                / max(len(members.union(set(existing["members_list"]))), 1)
                for existing in selected
            ]
            if max(diversity) >= minimum_diversity:
                selected.append(row)
        if len(selected) >= maximum:
            break
    return selected


def compose_fusion(
    system_scores: dict[str, np.ndarray], weights: dict[str, float]
) -> np.ndarray:
    output = np.zeros_like(next(iter(system_scores.values())))
    for system, weight in weights.items():
        output += float(weight) * system_scores[system]
    output = np.clip(output, 1e-9, None)
    return output / output.sum(axis=1, keepdims=True)


def feature_count_search(
    X: np.ndarray,
    y: np.ndarray,
    ranked: list[int],
    inner_indices: list[int],
    candidates: list[int],
    classes: int,
    weak_ratio: float,
    adjacent_credit: float,
    seed: int,
) -> tuple[list[int], pd.DataFrame]:
    trials = []
    for count in candidates:
        features = ranked[: min(int(count), len(ranked))]
        predictions = []
        started = time.perf_counter()
        for fold, event_index in enumerate(inner_indices):
            train = np.arange(event_index, dtype=int)
            logistic = direct_proxy_probability(
                "logistic",
                X[train][:, features],
                y[train],
                X[[event_index]][:, features],
                classes,
                seed + fold * 101,
            )
            trees = direct_proxy_probability(
                "extra_trees",
                X[train][:, features],
                y[train],
                X[[event_index]][:, features],
                classes,
                seed + 5000 + fold * 101,
            )
            predictions.append(0.5 * logistic[0] + 0.5 * trees[0])
        probability = np.vstack(predictions)
        metrics = time_band_metrics(
            y[inner_indices], probability, weak_ratio, adjacent_credit
        )
        trials.append(
            {
                "feature_count": len(features),
                "quality": metrics["quality_higher_is_better"],
                "exact_accuracy": metrics["exact_accuracy"],
                "qualified_accuracy": metrics["qualified_accuracy_exact_or_weak"],
                "mean_circular_band_error": metrics["mean_circular_band_error"],
                "runtime_seconds": float(time.perf_counter() - started),
            }
        )
    frame = pd.DataFrame(trials).sort_values(
        ["quality", "qualified_accuracy", "feature_count"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    best_count = int(frame.iloc[0]["feature_count"])
    return ranked[:best_count], frame


def screen_hyperparameters(
    config: dict,
    candidate_path: Path,
    X: np.ndarray,
    y: np.ndarray,
    inner_indices: list[int],
    features: list[int],
    classes: int,
    weak_ratio: float,
    adjacent_credit: float,
    output_dir: Path,
) -> tuple[dict, pd.DataFrame]:
    screen = config["hyperparameter_screen"]
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    families = payload.get("families", payload)
    scratch = output_dir / ".active_v20_override.json"
    trials = []
    total = sum(len(items) for items in families.values())
    completed = 0
    for family_id, (family, candidates) in enumerate(families.items()):
        for candidate_id, candidate in enumerate(candidates):
            completed += 1
            name = str(candidate.get("name", f"candidate_{candidate_id + 1}"))
            print(f"[{completed}/{total}] V20 screen {family}: {name}", flush=True)
            override = candidate.get("screen", candidate.get("override", {}))
            promoted = candidate.get("promote", override)
            write_json(scratch, {"models": {family: override}})
            os.environ["DLVSWAVE_MODEL_OVERRIDES_JSON"] = str(scratch)
            started = time.perf_counter()
            status = "COMPLETE"
            failure = ""
            try:
                probability, runtimes = chronological_predictions(
                    family,
                    X,
                    y,
                    inner_indices,
                    features,
                    classes,
                    int(screen["random_seed"]) + family_id * 10000 + candidate_id * 1000,
                    float(screen["epochs_scale"]),
                    float(screen["final_attempt_time_limit_seconds"]),
                )
                metrics = time_band_metrics(
                    y[inner_indices], probability, weak_ratio, adjacent_credit
                )
            except Exception as error:
                probability = np.empty((0, classes))
                runtimes = []
                metrics = {
                    "quality_higher_is_better": 0.0,
                    "exact_accuracy": 0.0,
                    "qualified_accuracy_exact_or_weak": 0.0,
                    "mean_circular_band_error": classes / 2,
                }
                status = "FAILED"
                failure = f"{type(error).__name__}: {error}"
            runtime = float(time.perf_counter() - started)
            trials.append(
                {
                    "family": family,
                    "candidate": name,
                    "status": status,
                    "quality": float(metrics["quality_higher_is_better"]),
                    "exact_accuracy": float(metrics["exact_accuracy"]),
                    "qualified_accuracy": float(
                        metrics["qualified_accuracy_exact_or_weak"]
                    ),
                    "mean_circular_band_error": float(
                        metrics["mean_circular_band_error"]
                    ),
                    "runtime_seconds": runtime,
                    "maximum_fold_runtime_seconds": float(
                        max((row["seconds"] for row in runtimes), default=0.0)
                    ),
                    "screen_override_json": json.dumps(override, sort_keys=True),
                    "promoted_override_json": json.dumps(promoted, sort_keys=True),
                    "failure": failure,
                }
            )
    frame = pd.DataFrame(trials)
    complete = frame[frame["status"].eq("COMPLETE")].copy()
    if complete.empty:
        raise RuntimeError("Every V20 hyperparameter candidate failed")
    complete["speed_skill"] = complete.groupby("family")["runtime_seconds"].transform(
        lambda values: values.min() / np.maximum(values, 1e-9)
    )
    complete["selection_score"] = (
        float(screen["quality_weight"]) * complete["quality"]
        + float(screen["speed_weight"]) * complete["speed_skill"]
    )
    frame = frame.merge(
        complete[["family", "candidate", "speed_skill", "selection_score"]],
        on=["family", "candidate"],
        how="left",
    )
    selected = {}
    for family, group in complete.groupby("family", sort=False):
        winner = group.sort_values(
            ["selection_score", "quality"], ascending=False, kind="mergesort"
        ).iloc[0]
        selected[str(family)] = {
            "candidate": str(winner["candidate"]),
            "screen_quality": float(winner["quality"]),
            "screen_runtime_seconds": float(winner["runtime_seconds"]),
            "override": json.loads(winner["promoted_override_json"]),
        }
    selection = {
        "schema": "v20.time_band_hyperparameter_selection.v1",
        "models": {family: row["override"] for family, row in selected.items()},
        "selected": selected,
        "selection_uses_outer_holdouts": False,
        "inner_validation_events": len(inner_indices),
    }
    return selection, frame.sort_values(
        ["family", "selection_score"], ascending=[True, False], kind="mergesort"
    )


def aggregate_forecast(
    candidates: pd.DataFrame,
    probability: np.ndarray,
    labels: list[str],
) -> pd.DataFrame:
    rows = []
    working = candidates.reset_index(drop=True).copy()
    working["self_band_compatibility"] = probability[
        np.arange(len(working)), working["candidate_band"].to_numpy(int)
    ]
    for (start, end), group in working.groupby(
        ["forecast_slot_start", "forecast_slot_end"], sort=False
    ):
        compatibility = np.asarray(
            [
                group.loc[group["candidate_band"].eq(band), "self_band_compatibility"].mean()
                for band in range(len(labels))
            ],
            float,
        )
        compatibility = np.clip(compatibility, 1e-12, None)
        distribution = compatibility / compatibility.sum()
        row = {
            "forecast_slot_start": start,
            "forecast_slot_end": end,
            "sampled_candidate_epochs": int(len(group)),
            "predicted_band": int(np.argmax(distribution)),
            "predicted_band_label": labels[int(np.argmax(distribution))],
        }
        for band, label in enumerate(labels):
            row[f"band_{band}_label"] = label
            row[f"band_{band}_score_not_probability"] = float(distribution[band])
            row[f"band_{band}_raw_compatibility"] = float(compatibility[band])
        rows.append(row)
    return pd.DataFrame(rows)


def attach_timing_scores(project: Path, config: dict, frame: pd.DataFrame) -> pd.DataFrame:
    value = frame.copy()
    source = config["forecast"].get("timing_score_csv")
    if source:
        path = resolve(project, source)
        timing = pd.read_csv(path)
        score_columns = [column for column in timing if "score_not_probability" in column]
        if score_columns:
            lookup = dict(zip(timing["date"].astype(str), timing[score_columns[0]].astype(float)))
            value["v19_timing_score_not_probability"] = value[
                "forecast_slot_start"
            ].map(lookup)
    return value


def weighted_focus_distribution(frame: pd.DataFrame, focus: list[str], classes: int) -> dict:
    selected = frame[frame["forecast_slot_start"].isin(focus)].copy()
    if selected.empty:
        selected = frame.copy()
    if "v19_timing_score_not_probability" in selected:
        weights = selected["v19_timing_score_not_probability"].fillna(0.0).to_numpy(
            dtype=float, copy=True
        )
    else:
        weights = np.ones(len(selected), float)
    if weights.sum() <= 0:
        weights = np.ones(len(selected), float)
    weights /= weights.sum()
    distribution = np.asarray(
        [
            np.sum(weights * selected[f"band_{band}_score_not_probability"].to_numpy(float))
            for band in range(classes)
        ]
    )
    distribution /= distribution.sum()
    return {
        "focus_slots": selected["forecast_slot_start"].astype(str).tolist(),
        "slot_weights": weights.tolist(),
        "band_scores_not_probabilities": distribution.tolist(),
        "predicted_band": int(np.argmax(distribution)),
    }


def prediction_rows(
    events: pd.DataFrame,
    indices: list[int],
    probability: np.ndarray,
    labels: list[str],
    method: str,
    metrics: dict,
) -> pd.DataFrame:
    selected = events.iloc[indices].reset_index(drop=True)
    predicted = np.argmax(probability, axis=1)
    rows = pd.DataFrame(
        {
            "method": method,
            "event_time_utc": selected["sample_time_utc"],
            "event_time_local": selected["sample_time_local"],
            "event_id": selected["event_id"],
            "place": selected["place"],
            "mag": selected["mag"],
            "actual_band": selected["target_band"].astype(int),
            "actual_band_label": selected["target_band_label"],
            "predicted_band": predicted,
            "predicted_band_label": [labels[item] for item in predicted],
            "circular_band_error": metrics["circular_band_errors"],
            "true_band_score": metrics["true_band_probabilities"],
            "qualified_exact_or_weak": metrics["qualified_rows"],
            "row_quality": metrics["quality_rows"],
        }
    )
    for band, label in enumerate(labels):
        rows[f"band_{band}_label"] = label
        rows[f"band_{band}_score_not_probability"] = probability[:, band]
    return rows


def main() -> None:
    global PROJECT
    args = parser().parse_args()
    PROJECT = args.project_dir.resolve()
    config_path = args.config or PROJECT / "00_config/pipeline_request.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    os.environ["DLVSWAVE_PROJECT_DIR"] = str(PROJECT)
    os.environ["DLVSWAVE_REPO_DIR"] = str(Path(__file__).resolve().parents[2])
    os.environ["DLVSWAVE_MODEL_PROFILE"] = "deep"

    master = pd.read_csv(PROJECT / "01_inputs/event_time_master.csv", low_memory=False)
    manifest = json.loads(
        (PROJECT / "02_audit/event_time_master_manifest.json").read_text(encoding="utf-8")
    )
    feature_names = list(manifest["feature_names"])
    X_all = master[feature_names].to_numpy(float)
    event_mask = master["sample_kind"].eq("event").to_numpy()
    forecast_mask = master["sample_kind"].eq("forecast_candidate").to_numpy()
    events = master[event_mask].reset_index(drop=True)
    candidates = master[forecast_mask].reset_index(drop=True)
    X = X_all[event_mask]
    X_forecast = X_all[forecast_mask]
    y = events["target_band"].to_numpy(int)
    target = config["time_target"]
    labels = list(target["band_labels"])
    classes = len(labels)
    weak_ratio = float(target["weak_band_probability_ratio"])
    adjacent_credit = float(target["adjacent_band_credit"])
    outer_count = int(target["required_outer_validation_events"])
    outer_indices = list(range(len(events) - outer_count, len(events)))
    pre_outer = np.arange(outer_indices[0], dtype=int)
    inner_count = int(config["feature_search"]["inner_validation_events"])
    inner_indices = list(range(len(pre_outer) - inner_count, len(pre_outer)))
    ranking_train = np.arange(inner_indices[0], dtype=int)
    if len(np.unique(y[ranking_train])) != classes:
        raise ValueError("Pre-inner ranking split does not contain all time bands")
    if len(np.unique(y[outer_indices])) < int(target["required_distinct_outer_bands"]):
        raise ValueError("Outer holdouts do not contain the requested time-band variation")

    ranking_scaler = StandardScaler().fit(X[ranking_train])
    ranked, ranking_audit = rank_features(
        ranking_scaler.transform(X[ranking_train]),
        y[ranking_train],
        list(range(len(feature_names))),
        feature_names,
        int(config["feature_search"]["random_seed"]),
    )
    features, feature_trials = feature_count_search(
        X,
        y,
        ranked,
        inner_indices,
        list(config["feature_search"]["candidate_counts"]),
        classes,
        weak_ratio,
        adjacent_credit,
        int(config["feature_search"]["random_seed"]),
    )
    ranking = pd.DataFrame(ranking_audit["ranking"])
    ranking["selected"] = ranking["index"].isin(features)
    ranking.to_csv(PROJECT / "03_feature_research/time_band_feature_ranking.csv", index=False)
    feature_trials.to_csv(
        PROJECT / "03_feature_research/time_band_feature_count_trials.csv", index=False
    )

    selection, screen_trials = screen_hyperparameters(
        config,
        resolve(PROJECT, config["candidate_config_json"]),
        X,
        y,
        inner_indices,
        features,
        classes,
        weak_ratio,
        adjacent_credit,
        PROJECT / "03_feature_research",
    )
    selection_path = PROJECT / "03_feature_research/time_band_selected_model_overrides.json"
    write_json(selection_path, selection)
    screen_trials.to_csv(
        PROJECT / "03_feature_research/time_band_hyperparameter_trials.csv", index=False
    )
    os.environ["DLVSWAVE_MODEL_OVERRIDES_JSON"] = str(selection_path)

    final_limit = float(config["hyperparameter_screen"]["final_attempt_time_limit_seconds"])
    epochs_scale = float(config["hyperparameter_screen"]["epochs_scale"])
    base_inner = {}
    runtime_rows = []
    for family_id, family in enumerate(BASES):
        probability, runtime = chronological_predictions(
            family,
            X,
            y,
            inner_indices,
            features,
            classes,
            620300 + family_id * 10000,
            epochs_scale,
            final_limit,
        )
        base_inner[family] = probability
        runtime_rows.extend({"phase": "inner_system_selection", **row} for row in runtime)

    system_rows = []
    system_inner = {}
    for system, members in SYSTEMS.items():
        if not set(members).issubset(base_inner):
            continue
        probability = system_probability(base_inner, members)
        metrics = time_band_metrics(y[inner_indices], probability, weak_ratio, adjacent_credit)
        system_inner[system] = probability
        system_rows.append(
            {
                "system": system,
                "members": " + ".join(members),
                "members_list": list(members),
                "quality": metrics["quality_higher_is_better"],
                "exact_accuracy": metrics["exact_accuracy"],
                "qualified_accuracy": metrics["qualified_accuracy_exact_or_weak"],
                "mean_circular_band_error": metrics["mean_circular_band_error"],
            }
        )
    fusion_config = config["fusion"]
    selected_systems = select_diverse_systems(
        system_rows,
        int(fusion_config["maximum_systems"]),
        float(fusion_config["minimum_system_diversity"]),
    )
    inner_weights = positive_weights(
        {row["system"]: row["quality"] for row in selected_systems},
        temperature=float(fusion_config["weight_temperature"]),
        floor=float(fusion_config["weight_floor"]),
    )
    pd.DataFrame(
        [{k: v for k, v in row.items() if k != "members_list"} for row in system_rows]
    ).sort_values("quality", ascending=False).to_csv(
        PROJECT / "03_feature_research/time_band_system_search.csv", index=False
    )

    base_outer = {}
    for family_id, family in enumerate(BASES):
        probability, runtime = chronological_predictions(
            family,
            X,
            y,
            outer_indices,
            features,
            classes,
            620500 + family_id * 10000,
            epochs_scale,
            final_limit,
        )
        base_outer[family] = probability
        runtime_rows.extend({"phase": "outer_sequential_validation", **row} for row in runtime)
    outer_system_scores = {
        row["system"]: system_probability(base_outer, tuple(row["members_list"]))
        for row in selected_systems
    }
    weighted_validation = compose_fusion(outer_system_scores, inner_weights)
    weighted_metrics = time_band_metrics(
        y[outer_indices], weighted_validation, weak_ratio, adjacent_credit
    )

    one_shot_base = {}
    for family_id, family in enumerate(BASES):
        probability, audit = fit_multiclass_ovr(
            family,
            X[pre_outer][:, features],
            y[pre_outer],
            X[outer_indices][:, features],
            classes,
            620700 + family_id * 10000,
            epochs_scale,
            final_limit,
        )
        one_shot_base[family] = probability
        runtime_rows.append({"phase": "one_shot_validation", "fold": 1, **audit})
    one_shot_system = {
        row["system"]: system_probability(one_shot_base, tuple(row["members_list"]))
        for row in selected_systems
    }
    one_shot_validation = compose_fusion(one_shot_system, inner_weights)
    one_shot_metrics = time_band_metrics(
        y[outer_indices], one_shot_validation, weak_ratio, adjacent_credit
    )

    null_probability = None
    null_metrics = None
    if bool(config.get("null_control", {}).get("enabled", False)):
        rng = np.random.default_rng(int(config["null_control"]["seed"]))
        permuted = rng.permutation(y[pre_outer])
        null_base = {}
        required_families = sorted(
            {member for row in selected_systems for member in row["members_list"]}
        )
        for family_id, family in enumerate(required_families):
            probability, audit = fit_multiclass_ovr(
                family,
                X[pre_outer][:, features],
                permuted,
                X[outer_indices][:, features],
                classes,
                620900 + family_id * 10000,
                epochs_scale,
                final_limit,
            )
            null_base[family] = probability
            runtime_rows.append({"phase": "randomized_target_null", "fold": 1, **audit})
        null_systems = {
            row["system"]: system_probability(null_base, tuple(row["members_list"]))
            for row in selected_systems
        }
        null_probability = compose_fusion(null_systems, inner_weights)
        null_metrics = time_band_metrics(
            y[outer_indices], null_probability, weak_ratio, adjacent_credit
        )

    # Forecast weights may use completed outer validation, but outer predictions
    # above remain untouched by this second-stage reliability estimate.
    system_outer_quality = {
        system: time_band_metrics(
            y[outer_indices], probability, weak_ratio, adjacent_credit
        )["quality_higher_is_better"]
        for system, probability in outer_system_scores.items()
    }
    forecast_weights = positive_weights(
        system_outer_quality,
        temperature=float(fusion_config["weight_temperature"]),
        floor=float(fusion_config["weight_floor"]),
    )

    all_indices = np.arange(len(events), dtype=int)
    primary_forecast_base = {}
    one_shot_forecast_base = {}
    for family_id, family in enumerate(BASES):
        probability, audit = fit_multiclass_ovr(
            family,
            X[:, features],
            y,
            X_forecast[:, features],
            classes,
            621100 + family_id * 10000,
            epochs_scale,
            final_limit,
        )
        primary_forecast_base[family] = probability
        runtime_rows.append({"phase": "weighted_full_history_forecast", "fold": 1, **audit})
        probability, audit = fit_multiclass_ovr(
            family,
            X[:, features],
            y,
            X_forecast[:, features],
            classes,
            621300 + family_id * 10000,
            epochs_scale,
            final_limit,
        )
        one_shot_forecast_base[family] = probability
        runtime_rows.append({"phase": "one_shot_full_history_forecast", "fold": 1, **audit})

    primary_forecast_system = {
        row["system"]: system_probability(
            primary_forecast_base, tuple(row["members_list"])
        )
        for row in selected_systems
    }
    one_shot_forecast_system = {
        row["system"]: system_probability(
            one_shot_forecast_base, tuple(row["members_list"])
        )
        for row in selected_systems
    }
    primary_candidate_probability = compose_fusion(
        primary_forecast_system, forecast_weights
    )
    one_shot_candidate_probability = compose_fusion(
        one_shot_forecast_system, inner_weights
    )
    primary_forecast = attach_timing_scores(
        PROJECT,
        config,
        aggregate_forecast(candidates, primary_candidate_probability, labels),
    )
    one_shot_forecast = attach_timing_scores(
        PROJECT,
        config,
        aggregate_forecast(candidates, one_shot_candidate_probability, labels),
    )
    focus = list(config["forecast"].get("focus_slots", []))
    primary_focus = weighted_focus_distribution(primary_forecast, focus, classes)
    one_shot_focus = weighted_focus_distribution(one_shot_forecast, focus, classes)

    validation_frames = [
        prediction_rows(
            events, outer_indices, weighted_validation, labels,
            "nested_sequential_weighted", weighted_metrics
        ),
        prediction_rows(
            events, outer_indices, one_shot_validation, labels,
            "one_shot_pre_holdout", one_shot_metrics
        ),
    ]
    if null_probability is not None and null_metrics is not None:
        validation_frames.append(
            prediction_rows(
                events, outer_indices, null_probability, labels,
                "target_label_permutation_null", null_metrics
            )
        )
    validation = pd.concat(validation_frames, ignore_index=True)
    validation.to_csv(PROJECT / "05_ensemble/time_band_validation.csv", index=False)
    primary_forecast.to_csv(
        PROJECT / "05_ensemble/time_band_weighted_forecast.csv", index=False
    )
    one_shot_forecast.to_csv(
        PROJECT / "05_ensemble/time_band_one_shot_forecast.csv", index=False
    )
    pd.DataFrame(runtime_rows).to_csv(
        PROJECT / "04_models/time_band_final_attempt_runtimes.csv", index=False
    )

    summary = {
        "schema": "v20.time_connection.summary.v1",
        "status": "COMPLETE",
        "experimental": True,
        "score_semantics": "relative conditional time-band score; not a calibrated probability and not an event-occurrence forecast",
        "target": {
            "timezone": target["timezone"],
            "band_hours": target["band_hours"],
            "labels": labels,
            "weak_band_probability_ratio": weak_ratio,
            "adjacent_band_credit": adjacent_credit,
        },
        "data": {
            "trusted_japan_events": int(len(events)),
            "non_japan_hard_negative_rows": 0,
            "outer_validation_events": int(len(outer_indices)),
            "outer_validation_event_ids": events.iloc[outer_indices]["event_id"].astype(str).tolist(),
            "outer_validation_distinct_bands": int(events.iloc[outer_indices]["target_band"].nunique()),
        },
        "feature_search": {
            "available_features": int(len(feature_names)),
            "selected_features": int(len(features)),
            "selected_feature_names": [feature_names[index] for index in features],
            "uses_direct_hour_features": False,
            "selection_uses_outer_holdouts": False,
        },
        "selected_systems": [
            {
                "system": row["system"],
                "members": row["members_list"],
                "inner_quality": row["quality"],
                "validation_weight": inner_weights[row["system"]],
                "forecast_weight": forecast_weights[row["system"]],
                "outer_quality": system_outer_quality[row["system"]],
            }
            for row in selected_systems
        ],
        "validation": {
            "nested_sequential_weighted": weighted_metrics,
            "one_shot_pre_holdout": one_shot_metrics,
            "target_label_permutation_null": null_metrics,
            "variation_tolerance": "exact, circular-adjacent and weak-band-qualified metrics are all reported",
        },
        "forecast": {
            "weighted_focus": primary_focus,
            "one_shot_focus": one_shot_focus,
            "weighted_rows": int(len(primary_forecast)),
            "one_shot_rows": int(len(one_shot_forecast)),
            "conditional_semantics": "band scores are conditional on an event occurring in the corresponding V19 timing slot",
        },
        "runtime": {
            "hard_limit_seconds_per_family_attempt": final_limit,
            "attempts": int(len(runtime_rows)),
            "all_finished_within_limit": bool(
                all(row["finished_within_time_limit"] for row in runtime_rows)
            ),
            "maximum_attempt_seconds": float(
                max(row["seconds"] for row in runtime_rows)
            ),
        },
        "null_control_contributes_to_forecast": False,
    }
    write_json(PROJECT / "05_ensemble/time_band_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

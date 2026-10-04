#!/usr/bin/env python3
"""Chronologically screen model-family hyperparameters and record runtime.

The screen deliberately uses a fixed, training-only feature ranking and small
candidate budgets.  It selects one configuration inside each model family;
the main pipeline subsequently compares the promoted families and hybrids with
its full nested feature/history procedure.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from common_v14 import (
    TIMING_META,
    empirical_percentile,
    fit_real_binary,
    isolated_indices,
    rank_features,
    score_quality,
    write_json,
)
from quantile_preprocessing import QuantileBinTransformer


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--timing-master", type=Path, required=True)
    value.add_argument("--safe-features-json", type=Path, required=True)
    value.add_argument("--candidate-config-json", type=Path, required=True)
    value.add_argument("--validation-slots", required=True)
    value.add_argument("--forecast-start", required=True)
    value.add_argument("--event-radius", type=int, default=3)
    value.add_argument("--feature-limit", type=int, default=32)
    value.add_argument("--quantile-bins", type=int, default=4)
    value.add_argument("--epochs-scale", type=float, default=1.0)
    value.add_argument("--random-seed", type=int, default=617171)
    value.add_argument("--quality-weight", type=float, default=0.85)
    value.add_argument("--speed-weight", type=float, default=0.15)
    value.add_argument("--output-trials-csv", type=Path, required=True)
    value.add_argument("--output-selection-json", type=Path, required=True)
    value.add_argument("--output-runtime-json", type=Path, required=True)
    return value


def main() -> None:
    args = parser().parse_args()
    if args.quantile_bins not in {0} and args.quantile_bins < 2:
        raise ValueError("quantile-bins must be zero (raw) or at least two")
    if not np.isclose(args.quality_weight + args.speed_weight, 1.0):
        raise ValueError("quality-weight and speed-weight must sum to one")
    frame = pd.read_csv(args.timing_master, low_memory=False)
    names = [column for column in frame if column not in TIMING_META]
    X = frame[names].to_numpy(float)
    y = frame["timing_target"].to_numpy(int)
    dates = frame["date"].astype(str).str.slice(0, 10)
    historical = np.flatnonzero(
        frame["is_forecast"].eq(0).to_numpy()
        & frame["complete_at_catalog_snapshot"].eq(1).to_numpy()
        & dates.lt(args.forecast_start).to_numpy()
    )
    requested = [item.strip() for item in args.validation_slots.split(",") if item.strip()]
    events = []
    for slot in requested:
        match = np.flatnonzero(dates.eq(slot).to_numpy() & y.astype(bool))
        if len(match) != 1:
            raise ValueError(f"Validation slot is not one unique positive row: {slot}")
        events.append(int(match[0]))
    events = sorted(events)
    earliest_validation = isolated_indices(
        np.asarray([events[0]]), args.event_radius, len(frame)
    )
    ranking_train = historical[historical < earliest_validation.min()]
    safe_payload = json.loads(args.safe_features_json.read_text(encoding="utf-8"))
    safe_names = safe_payload["features"]
    safe_indices = [names.index(name) for name in safe_names]
    ranking_transformer = (
        QuantileBinTransformer(args.quantile_bins)
        if args.quantile_bins >= 2
        else StandardScaler()
    ).fit(X[ranking_train])
    ranked, ranking_audit = rank_features(
        ranking_transformer.transform(X[ranking_train]),
        y[ranking_train],
        safe_indices,
        names,
        args.random_seed,
    )
    ranking_audit["preprocessing"] = (
        ranking_transformer.audit()
        if isinstance(ranking_transformer, QuantileBinTransformer)
        else {
            "mode": "training_fold_standard_scaler",
            "n_bins": 0,
            "fit_scope": "training rows only; validation and forecast use unchanged fitted scale",
        }
    )
    features = ranked[: min(args.feature_limit, len(ranked))]

    candidates_payload = json.loads(
        args.candidate_config_json.read_text(encoding="utf-8")
    )
    families = candidates_payload.get("families", candidates_payload)
    total_candidates = sum(len(candidates) for candidates in families.values())
    completed_candidates = 0
    scratch = args.output_selection_json.parent / ".active_model_screen_override.json"
    trials: list[dict] = []
    for family_id, (kind, candidates) in enumerate(families.items()):
        for candidate_id, candidate in enumerate(candidates):
            completed_candidates += 1
            name = str(candidate.get("name", f"candidate_{candidate_id + 1}"))
            print(
                f"[{completed_candidates}/{total_candidates}] screen "
                f"family={kind} candidate={name}",
                flush=True,
            )
            screen_override = candidate.get("screen", candidate.get("override", {}))
            promoted_override = candidate.get("promote", screen_override)
            write_json(scratch, {"models": {kind: screen_override}})
            os.environ["DLVSWAVE_MODEL_OVERRIDES_JSON"] = str(scratch.resolve())
            fold_rows = []
            failure = ""
            for fold_id, event in enumerate(events):
                validation = isolated_indices(
                    np.asarray([event]), args.event_radius, len(frame)
                )
                validation = validation[np.isin(validation, historical)]
                train = historical[historical < validation.min()]
                if len(np.unique(y[train])) < 2:
                    failure = "training split has fewer than two target classes"
                    break
                transformer = (
                    QuantileBinTransformer(args.quantile_bins)
                    if args.quantile_bins >= 2
                    else StandardScaler()
                ).fit(X[train][:, features])
                train_X = transformer.transform(X[train][:, features])
                validation_X = transformer.transform(X[validation][:, features])
                started = time.perf_counter()
                try:
                    _, predict = fit_real_binary(
                        kind,
                        train_X,
                        y[train],
                        args.random_seed + family_id * 10000 + candidate_id * 1000 + fold_id * 71,
                        args.epochs_scale,
                    )
                    reference = predict(train_X)
                    score = empirical_percentile(
                        reference, predict(validation_X), "linear_interpolated"
                    )
                    metrics = score_quality(
                        y[validation], score, validation, args.event_radius
                    )
                except Exception as error:  # preserve failed scientific trials
                    failure = f"{type(error).__name__}: {error}"
                    break
                fold_rows.append(
                    {
                        "runtime_seconds": float(time.perf_counter() - started),
                        "quality": float(metrics["quality_higher_is_better"]),
                        "false_peak_control": float(metrics["false_peak_control"]),
                        "delayed_false_peak_control": float(
                            metrics["delayed_false_peak_control"]
                        ),
                        "weak_peak_retention": float(metrics["weak_peak_retention_skill"]),
                    }
                )
            if fold_rows and not failure:
                scientific = float(
                    0.50 * np.mean([row["quality"] for row in fold_rows])
                    + 0.20 * np.mean([row["false_peak_control"] for row in fold_rows])
                    + 0.15 * np.mean(
                        [row["delayed_false_peak_control"] for row in fold_rows]
                    )
                    + 0.15 * np.mean([row["weak_peak_retention"] for row in fold_rows])
                )
                row = {
                    "family": kind,
                    "candidate": name,
                    "status": "COMPLETE",
                    "folds": len(fold_rows),
                    "scientific_quality": scientific,
                    "validation_quality_mean": float(
                        np.mean([value["quality"] for value in fold_rows])
                    ),
                    "false_peak_control_mean": float(
                        np.mean([value["false_peak_control"] for value in fold_rows])
                    ),
                    "delayed_false_peak_control_mean": float(
                        np.mean([value["delayed_false_peak_control"] for value in fold_rows])
                    ),
                    "weak_peak_retention_mean": float(
                        np.mean([value["weak_peak_retention"] for value in fold_rows])
                    ),
                    "runtime_seconds_mean": float(
                        np.mean([value["runtime_seconds"] for value in fold_rows])
                    ),
                    "runtime_seconds_total": float(
                        np.sum([value["runtime_seconds"] for value in fold_rows])
                    ),
                    "screen_override_json": json.dumps(screen_override, sort_keys=True),
                    "promoted_override_json": json.dumps(promoted_override, sort_keys=True),
                    "failure": "",
                }
            else:
                row = {
                    "family": kind,
                    "candidate": name,
                    "status": "FAILED",
                    "folds": len(fold_rows),
                    "scientific_quality": 0.0,
                    "validation_quality_mean": 0.0,
                    "false_peak_control_mean": 0.0,
                    "delayed_false_peak_control_mean": 0.0,
                    "weak_peak_retention_mean": 0.0,
                    "runtime_seconds_mean": float("nan"),
                    "runtime_seconds_total": float(
                        np.sum([value["runtime_seconds"] for value in fold_rows])
                    ),
                    "screen_override_json": json.dumps(screen_override, sort_keys=True),
                    "promoted_override_json": json.dumps(promoted_override, sort_keys=True),
                    "failure": failure,
                }
            trials.append(row)
            print(
                f"[{completed_candidates}/{total_candidates}] {row['status']} "
                f"quality={row['scientific_quality']:.3f} "
                f"runtime/fold={row['runtime_seconds_mean']:.3f}s",
                flush=True,
            )

    trial_frame = pd.DataFrame(trials)
    trial_frame["speed_skill_within_family"] = 0.0
    trial_frame["quality_speed_kpi"] = 0.0
    selected_models = {}
    selected_rows = []
    for family, positions in trial_frame.groupby("family").groups.items():
        positions = list(positions)
        complete = trial_frame.loc[positions, "status"].eq("COMPLETE")
        valid_positions = list(trial_frame.loc[positions].index[complete])
        if not valid_positions:
            raise RuntimeError(f"All hyperparameter candidates failed for {family}")
        runtimes = trial_frame.loc[valid_positions, "runtime_seconds_mean"].to_numpy(float)
        fastest = max(float(np.min(runtimes)), 1e-9)
        speed = np.clip(fastest / np.maximum(runtimes, fastest), 0.0, 1.0)
        trial_frame.loc[valid_positions, "speed_skill_within_family"] = speed
        kpi = (
            args.quality_weight
            * trial_frame.loc[valid_positions, "scientific_quality"].to_numpy(float)
            + args.speed_weight * speed
        )
        trial_frame.loc[valid_positions, "quality_speed_kpi"] = kpi
        best_position = valid_positions[int(np.argmax(kpi))]
        best = trial_frame.loc[best_position]
        selected_models[family] = json.loads(best["promoted_override_json"])
        selected_rows.append(
            {
                "family": family,
                "candidate": best["candidate"],
                "scientific_quality": float(best["scientific_quality"]),
                "runtime_seconds_mean": float(best["runtime_seconds_mean"]),
                "speed_skill_within_family": float(best["speed_skill_within_family"]),
                "quality_speed_kpi": float(best["quality_speed_kpi"]),
            }
        )

    args.output_trials_csv.parent.mkdir(parents=True, exist_ok=True)
    trial_frame.to_csv(args.output_trials_csv, index=False)
    selection = {
        "schema": "model_hyperparameter_screen.selection.v1",
        "models": selected_models,
        "selected_candidates": selected_rows,
        "validation_slots": requested,
        "event_radius": args.event_radius,
        "quantile_bins": args.quantile_bins,
        "quantile_levels": np.linspace(0.0, 1.0, args.quantile_bins).tolist(),
        "feature_count": len(features),
        "features": [names[index] for index in features],
        "feature_ranking": ranking_audit,
        "selection_objective": {
            "scientific_quality_components": {
                "validation_quality": 0.50,
                "false_peak_control": 0.20,
                "delayed_false_peak_control": 0.15,
                "weak_peak_retention": 0.15,
            },
            "quality_weight": args.quality_weight,
            "speed_weight": args.speed_weight,
            "speed_normalization": "fastest mean fold runtime / candidate mean fold runtime within family",
        },
    }
    write_json(args.output_selection_json, selection)
    write_json(
        args.output_runtime_json,
        {
            "schema": "model_runtime_quality.audit.v1",
            "selected": selected_rows,
            "all_trials_csv": str(args.output_trials_csv.resolve()),
            "runtime_scope": "fit plus training-reference and validation inference",
            "timing_method": "time.perf_counter wall-clock seconds",
        },
    )
    if scratch.exists():
        scratch.unlink()
    os.environ.pop("DLVSWAVE_MODEL_OVERRIDES_JSON", None)
    print(json.dumps(selection, indent=2), flush=True)


if __name__ == "__main__":
    main()

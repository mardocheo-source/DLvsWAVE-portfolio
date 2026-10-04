"""Modulo 6: Optuna Hierarchical Prefix Feature Space Optimizer for DLVS-Wave v2.0.

Optimizes feature subsets by exploiting prefix hierarchies:
  - Macro-groups (e.g. astro_sun, astro_moon, astro_jupiter, seis_core)
  - Metrics (e.g. dist, ra_icrf, azim, elev, illum_frac)
  - Aggregations (e.g. min, max, mean, median)
"""
from __future__ import annotations
from pathlib import Path

import logging
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np
import optuna
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import KFold

from naming import parse_field_name

logger = logging.getLogger("dlvs_wave.optimizer")
optuna.logging.set_verbosity(optuna.logging.WARNING)

METADATA_COLS = ("date", "time", "seis_core_id", "id", "event_id")


@dataclass
class FeatureHierarchy:
    all_features: list[str]
    prefixes: set[str]
    groups: set[str]
    metrics: set[str]
    aggregations: set[str]
    group_to_features: dict[str, list[str]]
    metric_to_features: dict[str, list[str]]
    agg_to_features: dict[str, list[str]]


def build_feature_hierarchy(columns: Sequence[str], df: pd.DataFrame | None = None) -> FeatureHierarchy:
    prefixes = set()
    groups = set()
    metrics = set()
    aggregations = set()
    group_to_features: dict[str, list[str]] = {}
    metric_to_features: dict[str, list[str]] = {}
    agg_to_features: dict[str, list[str]] = {}
    all_features = []

    for col in columns:
        if col in METADATA_COLS:
            continue
        if df is not None and col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue

        parsed = parse_field_name(col)
        if parsed is None:
            continue
        
        # Don't treat string IDs as features
        if parsed.metric.lower() in ("id", "event_id", "name"):
            continue

        all_features.append(col)
        prefixes.add(parsed.prefix)
        groups.add(parsed.group_key)
        metrics.add(parsed.metric)
        if parsed.aggregation:
            aggregations.add(parsed.aggregation)

        group_to_features.setdefault(parsed.group_key, []).append(col)
        metric_to_features.setdefault(parsed.metric, []).append(col)
        if parsed.aggregation:
            agg_to_features.setdefault(parsed.aggregation, []).append(col)

    return FeatureHierarchy(
        all_features=all_features,
        prefixes=prefixes,
        groups=groups,
        metrics=metrics,
        aggregations=aggregations,
        group_to_features=group_to_features,
        metric_to_features=metric_to_features,
        agg_to_features=agg_to_features,
    )


class PrefixFeatureOptimizer:
    """Explores combinatorial feature space using Optuna and hierarchical prefixes."""

    def __init__(
        self,
        df: pd.DataFrame,
        target_col: str = "seis_core_magnitude",
        hierarchy: FeatureHierarchy | None = None,
    ) -> None:
        self.df = df.copy()
        self.target_col = target_col
        feature_cols = [
            c for c in df.columns
            if c != target_col and c not in METADATA_COLS and pd.api.types.is_numeric_dtype(df[c])
        ]
        self.hierarchy = hierarchy or build_feature_hierarchy(feature_cols, df=self.df)

    def _sample_selected_features(self, trial: optuna.Trial) -> list[str]:
        """Dynamically activates/deactivates macro-groups, metrics, and aggregations."""
        active_groups = set()
        for g in sorted(self.hierarchy.groups):
            if trial.suggest_categorical(f"group_{g}", [True, False]):
                active_groups.add(g)

        if not active_groups and self.hierarchy.groups:
            active_groups.add(sorted(self.hierarchy.groups)[0])

        active_metrics = set()
        for m in sorted(self.hierarchy.metrics):
            if trial.suggest_categorical(f"metric_{m}", [True, False]):
                active_metrics.add(m)

        if not active_metrics and self.hierarchy.metrics:
            active_metrics.add(sorted(self.hierarchy.metrics)[0])

        active_aggs = set()
        if self.hierarchy.aggregations:
            for a in sorted(self.hierarchy.aggregations):
                if trial.suggest_categorical(f"agg_{a}", [True, False]):
                    active_aggs.add(a)

        selected = []
        for feat in self.hierarchy.all_features:
            parsed = parse_field_name(feat)
            if parsed is None:
                continue
            if parsed.group_key not in active_groups:
                continue
            if parsed.metric not in active_metrics:
                continue
            if parsed.aggregation and active_aggs and parsed.aggregation not in active_aggs:
                continue
            selected.append(feat)

        return selected

    def optimize(
        self,
        n_trials: int = 15,
        cv_splits: int = 3,
        objective_evaluator: Callable[[pd.DataFrame, list[str], str], float] | None = None,
    ) -> tuple[dict[str, Any], list[str], optuna.Study]:
        """Runs Optuna optimization study."""
        df_clean = self.df.dropna(subset=[self.target_col]) if self.target_col in self.df.columns else self.df.copy()
        if df_clean.empty or len(df_clean) < cv_splits:
            df_clean = self.df.fillna(0.0)

        def default_evaluator(data: pd.DataFrame, features: list[str], target: str) -> float:
            if not features:
                return float("inf")
            # Select strictly numeric columns and fill na
            X = data[features].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
            y = data[target].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float) if target in data.columns else np.random.randn(len(data))
            
            if len(data) < cv_splits * 2:
                model = RandomForestRegressor(n_estimators=10, random_state=42, max_depth=3)
                model.fit(X, y)
                preds = model.predict(X)
                return float(mean_squared_error(y, preds))

            kf = KFold(n_splits=cv_splits, shuffle=True, random_state=42)
            scores = []
            for train_idx, val_idx in kf.split(X):
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y[train_idx], y[val_idx]
                model = RandomForestRegressor(n_estimators=15, random_state=42, max_depth=3)
                model.fit(X_tr, y_tr)
                preds = model.predict(X_val)
                scores.append(mean_squared_error(y_val, preds))
            return float(np.mean(scores))

        eval_fn = objective_evaluator or default_evaluator

        def objective(trial: optuna.Trial) -> float:
            selected_features = self._sample_selected_features(trial)
            trial.set_user_attr("selected_features", selected_features)
            trial.set_user_attr("feature_count", len(selected_features))
            if not selected_features:
                return float("inf")
            return eval_fn(df_clean, selected_features, self.target_col)

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials)

        best_trial = study.best_trial
        best_features = best_trial.user_attrs.get("selected_features", [])

        summary = {
            "best_trial_number": best_trial.number,
            "best_score": round(best_trial.value, 5),
            "selected_feature_count": len(best_features),
            "best_params": best_trial.params,
        }

        logger.info(f"Optimization completed. Best Score: {summary['best_score']} with {len(best_features)} features.")
        return summary, best_features, study

import argparse
import json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Optuna Hierarchical Prefix Feature Space Optimizer CLI for DLVS-Wave v2.0")
    p.add_argument("--input-csv", required=True, help="Path to input master CSV dataset")
    p.add_argument("--target-col", default="seis_core_magnitude", help="Target column to predict (default: seis_core_magnitude)")
    p.add_argument("--trials", type=int, default=10, help="Number of Optuna optimization trials (default: 10)")
    p.add_argument("--cv-splits", type=int, default=3, help="Cross-validation splits (default: 3)")
    p.add_argument("--output-json", required=True, help="Path to save Optuna summary JSON report")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df = pd.read_csv(args.input_csv)
    optimizer = PrefixFeatureOptimizer(df, target_col=args.target_col)
    summary, best_feats, study = optimizer.optimize(n_trials=args.trials, cv_splits=args.cv_splits)
    
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Optuna Optimization Finished: Best Score = {summary['best_score']} with {len(best_feats)} features.")
    print(f"Summary saved to: {out_path}")


if __name__ == "__main__":
    main()

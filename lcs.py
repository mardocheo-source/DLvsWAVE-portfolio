"""
Learning Classifier System v2: UCS binario puro Python.

Implementazione minimale per classificazione event-based: regole a intervalli
su feature continue, azione binaria, fitness supervisionata event-aware.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import copy
import warnings

import numpy as np


@dataclass
class LCSConfig:
    population_size: int = 500
    epochs: int = 100
    ga_frequency: int = 50
    mutation_rate: float = 0.04
    crossover_rate: float = 0.8
    wildcard_prob: float = 0.5
    positive_wildcard_prob: Optional[float] = None
    positive_covering_multiplier: int = 1
    tournament_size: int = 5
    fitness_alpha: float = 0.1
    fitness_beta: float = 5.0
    deletion_threshold: int = 20
    do_subsumption: bool = True
    min_fitness_for_subsumption: float = 0.9
    binary_threshold: float = 0.1
    validation_split: float = 0.2
    validation_event_count: int = 0
    validation_event_start: Optional[int] = None
    validation_pre_records: int = 0
    validation_post_records: int = 0
    validation_isolated_windows: bool = False
    early_stop_patience: int = 25
    restore_best_population: bool = True
    final_retrain_full_train: bool = True
    fitness_mode: str = "event"
    positive_weight: Union[str, float] = "auto"
    max_positive_weight: float = 20.0
    positive_replay: Union[str, int] = "auto"
    max_positive_replay: int = 20
    positive_vote_weight: Union[str, float] = "auto"
    max_positive_vote_weight: float = 6.0
    selection_metric: str = "event_composite"
    max_active_conditions: Optional[int] = None
    export_rule_count: int = 20
    sample_weights: Optional[list] = None
    seed: int = 0
    verbose: bool = False


LCS_PRESETS = {
    "tiny": LCSConfig(population_size=100, epochs=50),
    "default": LCSConfig(population_size=500, epochs=100),
    "large": LCSConfig(population_size=1000, epochs=200),
    "wide": LCSConfig(population_size=2000, epochs=100),
}


@dataclass
class Classifier:
    conditions: List[Tuple[int, float, float]]
    action: int
    fitness: float = 0.0
    accuracy: float = 0.5
    experience: int = 0
    numerosity: int = 1
    timestamp: int = 0
    tp: float = 0.0
    tn: float = 0.0
    fp: float = 0.0
    fn: float = 0.0

    def matches(self, x) -> bool:
        for idx, lo, hi in self.conditions:
            value = float(x[idx])
            if value < lo or value > hi:
                return False
        return True


class UCSPredictor:
    def __init__(self, cfg: Optional[LCSConfig] = None):
        self.cfg = cfg or LCSConfig()
        self.population = []
        self.feature_ranges = None
        self.majority_class = 0
        self.history = None
        self.validation_info = None
        self.best_epoch = None
        self.best_validation_metrics = None
        self.positive_weight_ = 1.0
        self.positive_replay_ = 1
        self.positive_vote_weight_ = 1.0
        self._rng = np.random.RandomState(self.cfg.seed)
        self._total_steps = 0

    def fit(self, X, y, validation_data=None, context_datetimes=None):
        X = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=float).reshape(-1)
        if X.ndim != 2:
            raise ValueError("X deve essere una matrice 2D")
        if len(X) != len(y_arr):
            raise ValueError("X e y hanno lunghezze diverse")

        uniq = np.unique(y_arr)
        if not (len(uniq) <= 2 and set(np.round(uniq, 12)).issubset({0.0, 1.0})):
            warnings.warn(
                "UCSPredictor e' binario: y continuo/sparso binarizzato con "
                f"threshold={self.cfg.binary_threshold}",
                RuntimeWarning,
            )
        y_bin = (y_arr >= self.cfg.binary_threshold).astype(int)
        train_idx, val_idx, validation_info = self._resolve_validation_split(
            X, y_bin, validation_data=validation_data, context_datetimes=context_datetimes
        )
        if validation_data is not None:
            X_fit = X
            y_fit = y_bin
            X_val, y_val = validation_data
            X_val = np.asarray(X_val, dtype=float)
            y_val = (np.asarray(y_val, dtype=float).reshape(-1) >= self.cfg.binary_threshold).astype(int)
        else:
            X_fit = X[train_idx]
            y_fit = y_bin[train_idx]
            X_val = X[val_idx] if val_idx.size > 0 else None
            y_val = y_bin[val_idx] if val_idx.size > 0 else None

        self.majority_class = int(np.round(np.mean(y_bin))) if len(y_bin) else 0
        self.history = {
            "mean_fitness": [],
            "covering_events": [],
            "ga_events": [],
            "population_size": [],
            "val_score": [],
            "val_f1": [],
            "val_recall": [],
            "val_bal_acc": [],
            "best_epoch": None,
            "stopped_at": None,
        }
        self.validation_info = validation_info
        self.best_epoch = None
        self.best_validation_metrics = None
        full_sample_weights = self.cfg.sample_weights
        fit_sample_weights = None
        if full_sample_weights is not None:
            weights_arr = np.asarray(full_sample_weights, dtype=float).reshape(-1)
            if validation_data is None and len(weights_arr) == len(y_bin):
                fit_sample_weights = weights_arr[train_idx]
            elif len(weights_arr) == len(y_fit):
                fit_sample_weights = weights_arr
        self._prepare_training_state(X_fit, y_fit, reset_rng=True,
                                     sample_weights=fit_sample_weights)

        best_population = None
        best_score = -np.inf
        best_epoch = 0
        patience_left = int(self.cfg.early_stop_patience)
        for epoch in range(int(self.cfg.epochs)):
            covering_events, ga_events, mean_fitness = self._run_training_epoch(X_fit, y_fit)
            self.history["mean_fitness"].append(mean_fitness)
            self.history["covering_events"].append(int(covering_events))
            self.history["ga_events"].append(int(ga_events))
            self.history["population_size"].append(int(len(self.population)))
            val_metrics = self._validation_metrics(X_val, y_val)
            val_score = float(val_metrics.get("score", 0.0))
            self.history["val_score"].append(val_score)
            self.history["val_f1"].append(float(val_metrics.get("f1", 0.0)))
            self.history["val_recall"].append(float(val_metrics.get("recall", 0.0)))
            self.history["val_bal_acc"].append(float(val_metrics.get("bal_acc", 0.0)))
            if val_score > best_score + 1e-12:
                best_score = val_score
                best_epoch = epoch + 1
                best_population = self._clone_population()
                self.best_validation_metrics = val_metrics
                patience_left = int(self.cfg.early_stop_patience)
            elif int(self.cfg.early_stop_patience) > 0:
                patience_left -= 1

            if self.cfg.verbose and (epoch % 10 == 0 or epoch == self.cfg.epochs - 1):
                print(
                    f"  lcs epoch {epoch + 1:4d}/{self.cfg.epochs} "
                    f"fitness={mean_fitness:.4f} pop={len(self.population)} "
                    f"cover={covering_events} ga={ga_events} "
                    f"val={val_score:.4f} f1={val_metrics.get('f1', 0.0):.3f} "
                    f"r={val_metrics.get('recall', 0.0):.3f} "
                    f"bal={val_metrics.get('bal_acc', 0.0):.3f} best={best_epoch} "
                    f"pos_w={self.positive_weight_:.1f} replay={self.positive_replay_} "
                    f"vote_w={self.positive_vote_weight_:.2f}"
                )
            if int(self.cfg.early_stop_patience) > 0 and patience_left <= 0:
                self.history["stopped_at"] = epoch + 1
                break

        self.best_epoch = int(best_epoch) if best_epoch else None
        self.history["best_epoch"] = self.best_epoch
        if (bool(self.cfg.final_retrain_full_train)
                and self.best_epoch is not None
                and validation_data is None
                and val_idx.size > 0):
            self._final_retrain_full_train(X, y_bin, self.best_epoch,
                                           sample_weights=full_sample_weights)
        elif best_population is not None and bool(self.cfg.restore_best_population):
            self.population = best_population
        return self

    def predict(self, X):
        return (self.predict_score(X) >= 0.5).astype(int)

    def predict_score(self, X):
        """Return the normalized positive vote for each sample.

        UCS is a rule system rather than a probabilistic classifier, so these
        values are uncalibrated confidence scores.  Callers that need
        probabilities should calibrate them on data not used for fitting.
        """
        X = np.asarray(X, dtype=float)
        scores = []
        for x in X:
            match_set = self._match_set(x)
            if not match_set:
                scores.append(float(self.majority_class))
                continue
            votes = {0: 0.0, 1: 0.0}
            for rule in match_set:
                weight = max(float(rule.fitness), 1e-12) * max(int(rule.numerosity), 1)
                votes[int(rule.action)] += weight
            votes[1] *= max(float(self.positive_vote_weight_), 1.0)
            if votes[0] == votes[1] == 0.0:
                scores.append(float(self.majority_class))
            else:
                scores.append(votes[1] / max(votes[0] + votes[1], 1e-12))
        return np.asarray(scores, dtype=float)

    @property
    def n_params(self):
        return sum(
            sum(1 for c in rule.conditions if c[1] != -np.inf or c[2] != np.inf)
            for rule in self.population
        )

    def top_rules(self, k=20, feature_names=None):
        ordered = sorted(
            self.population,
            key=lambda r: (float(r.fitness) * int(r.numerosity), int(r.experience)),
            reverse=True,
        )
        out = []
        for i, rule in enumerate(ordered[:k]):
            active_conditions = [
                cond for cond in rule.conditions
                if not self._is_wildcard_condition(cond)
            ]
            rule_metrics = self._rule_metrics(rule)
            out.append({
                "rank": i + 1,
                "conditions": [(int(idx), float(lo), float(hi)) for idx, lo, hi in rule.conditions],
                "conditions_human": self._conditions_human(
                    active_conditions,
                    feature_names=feature_names,
                    include_wildcards=False,
                ),
                "active_conditions_human": self._conditions_human(
                    active_conditions,
                    feature_names=feature_names,
                    include_wildcards=False,
                ),
                "n_active_conditions": int(len(active_conditions)),
                "n_wildcard_conditions": int(len(rule.conditions) - len(active_conditions)),
                "action": int(rule.action),
                "fitness": float(rule.fitness),
                "numerosity": int(rule.numerosity),
                "experience": int(rule.experience),
                "accuracy": float(rule.accuracy),
                "tp": float(rule.tp),
                "tn": float(rule.tn),
                "fp": float(rule.fp),
                "fn": float(rule.fn),
                "rule_f1": float(rule_metrics.get("f1", 0.0)),
                "rule_recall": float(rule_metrics.get("recall", 0.0)),
                "rule_bal_acc": float(rule_metrics.get("bal_acc", 0.0)),
                "rule_action_correctness": float(self._rule_action_correctness(rule)),
            })
        return out

    def _resolve_validation_split(self, X, y_bin, validation_data=None, context_datetimes=None):
        n = len(y_bin)
        if validation_data is not None or n < 3 or float(self.cfg.validation_split) <= 0:
            return np.arange(n, dtype=int), np.asarray([], dtype=int), {
                "strategy": "external" if validation_data is not None else "disabled",
                "validation_split": float(self.cfg.validation_split),
                "train_size": int(n),
                "val_size": 0 if validation_data is None else int(len(validation_data[0])),
            }
        event_split = self._resolve_validation_event_window(y_bin)
        if event_split is not None:
            tr_idx, val_idx, info = event_split
            info["validation_split"] = float(self.cfg.validation_split)
            return tr_idx, val_idx, info
        val_size = int(round(float(self.cfg.validation_split) * n))
        val_size = max(1, min(n - 1, val_size))
        indices = np.arange(n, dtype=int)
        if self._datetimes_monotonic(context_datetimes):
            split_at = n - val_size
            positives = indices[y_bin == 1]
            if positives.size > 0 and not np.any(y_bin[split_at:] == 1):
                split_at = max(1, int(positives[-1]))
            tr_idx = indices[:split_at]
            val_idx = indices[split_at:]
            return tr_idx, val_idx, {
                "strategy": "chronological_tail",
                "validation_split": float(self.cfg.validation_split),
                "train_size": int(len(tr_idx)),
                "val_size": int(len(val_idx)),
                "val_positives": int(np.sum(y_bin[val_idx] == 1)),
            }

        positives = indices[y_bin == 1]
        negatives = indices[y_bin == 0]
        if positives.size >= 2 and negatives.size >= 2:
            pos_val = max(1, min(positives.size - 1, int(round(val_size * positives.size / n))))
            neg_val = max(1, min(negatives.size - 1, val_size - pos_val))
            pos_perm = self._rng.permutation(positives)
            neg_perm = self._rng.permutation(negatives)
            val_idx = np.sort(np.concatenate((pos_perm[:pos_val], neg_perm[:neg_val])))
            tr_mask = np.ones(n, dtype=bool)
            tr_mask[val_idx] = False
            tr_idx = indices[tr_mask]
            return tr_idx, val_idx, {
                "strategy": "stratified_random",
                "validation_split": float(self.cfg.validation_split),
                "train_size": int(len(tr_idx)),
                "val_size": int(len(val_idx)),
                "val_positives": int(np.sum(y_bin[val_idx] == 1)),
            }

        perm = self._rng.permutation(indices)
        val_idx = np.sort(perm[:val_size])
        tr_idx = np.sort(perm[val_size:])
        return tr_idx, val_idx, {
            "strategy": "random",
            "validation_split": float(self.cfg.validation_split),
            "train_size": int(len(tr_idx)),
            "val_size": int(len(val_idx)),
        }

    def _resolve_validation_event_window(self, y_bin):
        event_count = max(0, int(self.cfg.validation_event_count))
        if event_count <= 0:
            return None
        y_bin = np.asarray(y_bin, dtype=int)
        n = len(y_bin)
        event_idx = np.flatnonzero(y_bin == 1)
        if event_idx.size == 0:
            return None
        if self.cfg.validation_event_start is None:
            end_event_pos = int(event_idx.size - 1)
            start_event_pos = max(0, end_event_pos - event_count + 1)
        else:
            if self.cfg.validation_event_start < 0:
                start_event_pos = int(event_idx.size + self.cfg.validation_event_start)
            else:
                start_event_pos = int(self.cfg.validation_event_start)
            start_event_pos = max(0, min(start_event_pos, int(event_idx.size - 1)))
            end_event_pos = min(int(event_idx.size - 1), start_event_pos + event_count - 1)
        pre = max(0, int(self.cfg.validation_pre_records))
        post = max(0, int(self.cfg.validation_post_records))
        isolated = bool(self.cfg.validation_isolated_windows)

        if isolated:
            selected_events = event_idx[start_event_pos:end_event_pos + 1]
            pieces = []
            for ev in selected_events:
                lo = max(0, int(ev) - pre)
                hi = min(n - 1, int(ev) + post)
                if lo <= hi:
                    pieces.append(np.arange(lo, hi + 1, dtype=int))
            if not pieces:
                return None
            val_idx = np.unique(np.concatenate(pieces))
            start_idx = int(val_idx[0])
            tr_idx = np.arange(0, start_idx, dtype=int)
            strategy = "event_isolated_windows"
        else:
            start_idx = max(0, int(event_idx[start_event_pos]) - pre)
            end_idx = min(n - 1, int(event_idx[end_event_pos]) + post)
            val_idx = np.arange(start_idx, end_idx + 1, dtype=int)
            tr_idx = np.arange(0, start_idx, dtype=int)
            strategy = "event_window"

        if tr_idx.size == 0 or val_idx.size == 0:
            return None
        info = {
            "strategy": strategy,
            "requested_event_count": int(event_count),
            "used_event_count": int(np.sum(y_bin[val_idx] == 1)),
            "pre_records": int(pre),
            "post_records": int(post),
            "isolated_windows": isolated,
            "event_start": None if self.cfg.validation_event_start is None else int(self.cfg.validation_event_start),
            "resolved_event_start_pos": int(start_event_pos),
            "resolved_event_end_pos": int(end_event_pos),
            "val_start": int(val_idx[0]),
            "val_end": int(val_idx[-1]),
            "train_size": int(len(tr_idx)),
            "val_size": int(len(val_idx)),
            "val_positives": int(np.sum(y_bin[val_idx] == 1)),
        }
        return tr_idx, val_idx, info

    def _datetimes_monotonic(self, context_datetimes):
        if context_datetimes is None:
            return False
        values = [dt for dt in context_datetimes if dt is not None]
        if len(values) < 2:
            return False
        return all(values[i] <= values[i + 1] for i in range(len(values) - 1))

    def _resolve_positive_weight(self, y_bin):
        value = self.cfg.positive_weight
        if isinstance(value, str) and value.strip().lower() == "auto":
            positives = int(np.sum(np.asarray(y_bin) == 1))
            negatives = int(np.sum(np.asarray(y_bin) == 0))
            if positives <= 0:
                return 1.0
            return float(np.clip(negatives / max(positives, 1), 1.0, float(self.cfg.max_positive_weight)))
        return float(max(1.0, float(value)))

    def _resolve_positive_replay(self, y_bin):
        value = self.cfg.positive_replay
        if isinstance(value, str) and value.strip().lower() == "auto":
            positives = int(np.sum(np.asarray(y_bin) == 1))
            negatives = int(np.sum(np.asarray(y_bin) == 0))
            if positives <= 0:
                return 1
            replay = int(round(negatives / max(positives, 1)))
            return int(np.clip(replay, 1, int(self.cfg.max_positive_replay)))
        return int(max(1, int(value)))

    def _resolve_positive_vote_weight(self):
        value = self.cfg.positive_vote_weight
        if isinstance(value, str) and value.strip().lower() == "auto":
            vote_weight = np.sqrt(max(float(self.positive_weight_), 1.0))
            return float(np.clip(vote_weight, 1.0, float(self.cfg.max_positive_vote_weight)))
        return float(max(1.0, float(value)))

    def _epoch_indices(self, y_fit):
        base = np.arange(len(y_fit), dtype=int)
        weighted_extra = []
        weights = getattr(self, "sample_weights_", None)
        if weights is not None and len(weights) == len(y_fit):
            weights = np.asarray(weights, dtype=float).reshape(-1)
            whole = np.floor(np.maximum(weights, 1.0) - 1.0).astype(int)
            for idx, reps in enumerate(whole):
                if reps > 0:
                    weighted_extra.extend([idx] * int(min(reps, 20)))
            frac = np.maximum(weights, 1.0) - 1.0 - whole
            draws = np.flatnonzero(self._rng.rand(len(frac)) < frac)
            weighted_extra.extend([int(i) for i in draws])
        if int(self.positive_replay_) <= 1 and not weighted_extra:
            return base
        positives = np.flatnonzero(np.asarray(y_fit, dtype=int) == 1)
        chunks = [base]
        if positives.size > 0 and int(self.positive_replay_) > 1:
            chunks.append(np.tile(positives, int(self.positive_replay_) - 1))
        if weighted_extra:
            chunks.append(np.asarray(weighted_extra, dtype=int))
        return np.concatenate(chunks).astype(int)

    def _prepare_training_state(self, X_fit, y_fit, reset_rng=False, sample_weights=None):
        self.positive_weight_ = self._resolve_positive_weight(y_fit)
        self.positive_replay_ = self._resolve_positive_replay(y_fit)
        self.positive_vote_weight_ = self._resolve_positive_vote_weight()
        weights = sample_weights if sample_weights is not None else self.cfg.sample_weights
        if weights is not None and len(weights) == len(y_fit):
            weights = np.asarray(weights, dtype=float).reshape(-1)
            weights = np.maximum(weights, 1e-9)
            weights = weights / max(float(np.mean(weights)), 1e-9)
            self.sample_weights_ = weights
        else:
            self.sample_weights_ = None
        self.feature_ranges = {
            "min": X_fit.min(axis=0),
            "max": X_fit.max(axis=0),
            "std": np.maximum(X_fit.std(axis=0), 1e-8),
        }
        self.population = []
        if reset_rng:
            self._rng = np.random.RandomState(self.cfg.seed)
        self._total_steps = 0

    def _run_training_epoch(self, X_fit, y_fit):
        indices = self._epoch_indices(y_fit)
        self._rng.shuffle(indices)
        covering_events = 0
        ga_events = 0
        for idx in indices:
            x = X_fit[int(idx)]
            target = int(y_fit[int(idx)])
            match_set = self._match_set(x)
            correct_set = [rule for rule in match_set if rule.action == target]

            if not match_set or not correct_set:
                new_rules = self._covering_rules(x, target)
                self.population.extend(new_rules)
                match_set.extend(new_rules)
                correct_set.extend(new_rules)
                covering_events += 1

            self._update_fitness(match_set, target)
            if self.cfg.do_subsumption and correct_set:
                self._subsumption(correct_set)

            self._total_steps += 1
            if self.cfg.ga_frequency > 0 and self._total_steps % self.cfg.ga_frequency == 0:
                self._run_ga(match_set, x)
                ga_events += 1

            self._enforce_population_limit()
        mean_fitness = float(np.mean([r.fitness for r in self.population])) if self.population else 0.0
        return int(covering_events), int(ga_events), mean_fitness

    def _final_retrain_full_train(self, X, y_bin, best_epoch, sample_weights=None):
        self._prepare_training_state(X, y_bin, reset_rng=True, sample_weights=sample_weights)
        retrain_mean_fitness = []
        retrain_covering_events = []
        retrain_ga_events = []
        for _ in range(int(best_epoch)):
            cover, ga, mean_fit = self._run_training_epoch(X, y_bin)
            retrain_mean_fitness.append(float(mean_fit))
            retrain_covering_events.append(int(cover))
            retrain_ga_events.append(int(ga))
        self.history["retrain_info"] = {
            "strategy": "full_train_retrain",
            "best_epoch": int(best_epoch),
            "total_train_size": int(len(X)),
            "positive_weight": float(self.positive_weight_),
            "positive_replay": int(self.positive_replay_),
            "positive_vote_weight": float(self.positive_vote_weight_),
            "sample_weighting": bool(self.sample_weights_ is not None),
        }
        self.history["retrain_mean_fitness"] = retrain_mean_fitness
        self.history["retrain_covering_events"] = retrain_covering_events
        self.history["retrain_ga_events"] = retrain_ga_events

    def _validation_metrics(self, X_val, y_val):
        if X_val is None or y_val is None or len(y_val) == 0:
            return {"score": 0.0, "f1": 0.0, "recall": 0.0, "bal_acc": 0.0}
        pred = self.predict(X_val)
        return self._classification_metrics(y_val, pred)

    def _classification_metrics(self, y_true, y_pred):
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)
        tp = float(np.sum((y_true == 1) & (y_pred == 1)))
        tn = float(np.sum((y_true == 0) & (y_pred == 0)))
        fp = float(np.sum((y_true == 0) & (y_pred == 1)))
        fn = float(np.sum((y_true == 1) & (y_pred == 0)))
        precision = tp / max(tp + fp, 1e-12)
        recall = tp / max(tp + fn, 1e-12)
        specificity = tn / max(tn + fp, 1e-12)
        f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
        bal_acc = 0.5 * (recall + specificity)
        score = self._metric_score({
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "bal_acc": bal_acc,
        })
        fallback = ""
        if not np.any(y_true == 1):
            score = bal_acc
            fallback = "no_positive_validation_bal_acc"
        elif recall <= 0.0:
            score = 0.0
        return {
            "score": float(score),
            "f1": float(f1),
            "precision": float(precision),
            "recall": float(recall),
            "specificity": float(specificity),
            "bal_acc": float(bal_acc),
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "fallback": fallback,
        }

    def _match_set(self, x):
        return [rule for rule in self.population if rule.matches(x)]

    def _covering_rules(self, x, action):
        multiplier = 1
        if int(action) == 1:
            multiplier = max(1, int(self.cfg.positive_covering_multiplier))
        return [self._covering_rule(x, action) for _ in range(multiplier)]

    def _covering_rule(self, x, action):
        n_features = x.shape[0]
        conditions = []
        non_wildcards = 0
        wildcard_prob = float(self.cfg.wildcard_prob)
        if int(action) == 1 and self.cfg.positive_wildcard_prob is not None:
            wildcard_prob = float(self.cfg.positive_wildcard_prob)
        wildcard_prob = float(np.clip(wildcard_prob, 0.0, 0.999))
        for i in range(n_features):
            if self._rng.rand() < wildcard_prob:
                conditions.append((i, -np.inf, np.inf))
                continue
            lo, hi = self._range_around_value(i, x[i])
            conditions.append((i, lo, hi))
            non_wildcards += 1
        if non_wildcards == 0 and n_features > 0:
            i = int(self._rng.randint(0, n_features))
            lo, hi = self._range_around_value(i, x[i])
            conditions[i] = (i, lo, hi)
        conditions = self._enforce_active_budget(conditions)
        return Classifier(conditions=conditions, action=int(action), timestamp=self._total_steps)

    def _enforce_active_budget(self, conditions):
        cap = self.cfg.max_active_conditions
        if cap is None or int(cap) <= 0:
            return conditions
        cap = int(cap)
        active_idx = [
            i for i, (_, lo, hi) in enumerate(conditions)
            if lo != -np.inf or hi != np.inf
        ]
        if len(active_idx) <= cap:
            return conditions
        n_to_drop = len(active_idx) - cap
        drop_positions = self._rng.choice(len(active_idx), size=n_to_drop, replace=False)
        for pos in np.atleast_1d(drop_positions):
            i = active_idx[int(pos)]
            feature_idx, _, _ = conditions[i]
            conditions[i] = (feature_idx, -np.inf, np.inf)
        return conditions

    def _range_around_value(self, feature_idx, value):
        sigma = float(self.feature_ranges["std"][feature_idx])
        lo = float(value) - sigma
        hi = float(value) + sigma
        fmin = float(self.feature_ranges["min"][feature_idx])
        fmax = float(self.feature_ranges["max"][feature_idx])
        return max(fmin, lo), min(fmax, hi)

    def _update_fitness(self, match_set, target):
        lr = float(self.cfg.fitness_alpha)
        for rule in match_set:
            rule.experience += 1
            action = int(rule.action)
            target = int(target)
            if action == 1 and target == 1:
                rule.tp += self.positive_weight_
            elif action == 0 and target == 0:
                rule.tn += 1.0
            elif action == 1 and target == 0:
                rule.fp += 1.0
            else:
                rule.fn += self.positive_weight_

            event_metrics = self._rule_metrics(rule)
            reward = self._rule_score(rule, event_metrics)
            effective_lr = min(1.0, lr * (self.positive_weight_ if target == 1 else 1.0))
            rule.accuracy += effective_lr * (reward - float(rule.accuracy))
            rule.accuracy = float(np.clip(rule.accuracy, 0.0, 1.0))
            rule.fitness = float((rule.accuracy ** float(self.cfg.fitness_beta)) * lr)

    def _rule_metrics(self, rule):
        tp = float(rule.tp)
        tn = float(rule.tn)
        fp = float(rule.fp)
        fn = float(rule.fn)
        precision = tp / max(tp + fp, 1e-12)
        recall = tp / max(tp + fn, 1e-12)
        specificity = tn / max(tn + fp, 1e-12)
        f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
        bal_acc = 0.5 * (recall + specificity)
        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "bal_acc": float(bal_acc),
        }

    def _metric_score(self, metrics):
        metric = str(self.cfg.selection_metric).strip().lower()
        f1 = float(metrics.get("f1", 0.0))
        bal_acc = float(metrics.get("bal_acc", 0.0))
        recall = float(metrics.get("recall", 0.0))
        precision = float(metrics.get("precision", 0.0))
        if metric == "event_composite_additive":
            return float(0.50 * f1 + 0.20 * bal_acc + 0.15 * recall + 0.15 * precision)
        if metric == "f1":
            return float(f1)
        if metric in ("bal_acc", "balanced_accuracy"):
            return float(bal_acc)
        return float(f1 * bal_acc)

    def _rule_action_correctness(self, rule):
        tp = float(rule.tp)
        tn = float(rule.tn)
        fp = float(rule.fp)
        fn = float(rule.fn)
        if int(rule.action) == 1:
            return float(tp / max(tp + fp, 1e-12))
        return float(tn / max(tn + fn, 1e-12))

    def _rule_score(self, rule, metrics):
        # Global validation can use F1*BalAcc, but a single UCS rule only sees
        # samples it matches. Scoring action=0 rules with positive-class F1 would
        # collapse their fitness to zero and bias the population toward all-1.
        return float(self._rule_action_correctness(rule))

    def _run_ga(self, match_set, x):
        if not match_set:
            return
        parent1 = self._tournament(match_set)
        parent2 = self._tournament(match_set)
        child1 = self._clone(parent1)
        child2 = self._clone(parent2)
        if self._rng.rand() < self.cfg.crossover_rate:
            child1, child2 = self._crossover(child1, child2)
        self._mutate(child1, x)
        self._mutate(child2, x)
        child1.fitness = max(parent1.fitness, 1e-12) * 0.5
        child2.fitness = max(parent2.fitness, 1e-12) * 0.5
        child1.accuracy = parent1.accuracy
        child2.accuracy = parent2.accuracy
        child1.experience = 0
        child2.experience = 0
        child1.numerosity = 1
        child2.numerosity = 1
        child1.timestamp = self._total_steps
        child2.timestamp = self._total_steps
        self.population.extend([child1, child2])
        self._delete_low_fitness_rules(n=2)

    def _tournament(self, candidates):
        size = min(max(1, int(self.cfg.tournament_size)), len(candidates))
        idx = self._rng.choice(len(candidates), size=size, replace=len(candidates) < size)
        sampled = [candidates[int(i)] for i in np.atleast_1d(idx)]
        return max(sampled, key=lambda r: (float(r.fitness) * int(r.numerosity), int(r.experience)))

    def _clone(self, rule):
        return Classifier(
            conditions=[(int(i), float(lo), float(hi)) for i, lo, hi in rule.conditions],
            action=int(rule.action),
            fitness=float(rule.fitness),
            accuracy=float(rule.accuracy),
            experience=int(rule.experience),
            numerosity=1,
            timestamp=int(rule.timestamp),
            tp=float(rule.tp),
            tn=float(rule.tn),
            fp=float(rule.fp),
            fn=float(rule.fn),
        )

    def _clone_population(self):
        return copy.deepcopy(self.population)

    def _crossover(self, child1, child2):
        new1 = []
        new2 = []
        for cond1, cond2 in zip(child1.conditions, child2.conditions):
            if self._rng.rand() < 0.5:
                new1.append(cond2)
                new2.append(cond1)
            else:
                new1.append(cond1)
                new2.append(cond2)
        child1.conditions = self._enforce_active_budget(new1)
        child2.conditions = self._enforce_active_budget(new2)
        if self._rng.rand() < 0.5:
            child1.action, child2.action = child2.action, child1.action
        return child1, child2

    def _mutate(self, rule, x):
        mutated_non_wild = 0
        conditions = []
        for feature_idx, lo, hi in rule.conditions:
            if self._rng.rand() >= self.cfg.mutation_rate:
                conditions.append((feature_idx, lo, hi))
                if lo != -np.inf or hi != np.inf:
                    mutated_non_wild += 1
                continue

            if lo == -np.inf and hi == np.inf:
                nlo, nhi = self._range_around_value(feature_idx, x[feature_idx])
            elif self._rng.rand() < 0.25:
                nlo, nhi = -np.inf, np.inf
            else:
                sigma = float(self.feature_ranges["std"][feature_idx])
                shift = self._rng.normal(0.0, 0.25 * sigma)
                width_delta = self._rng.normal(0.0, 0.15 * sigma)
                center_lo = float(lo) + shift - width_delta
                center_hi = float(hi) + shift + width_delta
                fmin = float(self.feature_ranges["min"][feature_idx])
                fmax = float(self.feature_ranges["max"][feature_idx])
                nlo = max(fmin, min(center_lo, center_hi))
                nhi = min(fmax, max(center_lo, center_hi))
            conditions.append((feature_idx, float(nlo), float(nhi)))
            if nlo != -np.inf or nhi != np.inf:
                mutated_non_wild += 1

        if mutated_non_wild == 0 and conditions:
            feature_idx = int(self._rng.randint(0, len(conditions)))
            i, _, _ = conditions[feature_idx]
            lo, hi = self._range_around_value(i, x[i])
            conditions[feature_idx] = (i, lo, hi)
        rule.conditions = self._enforce_active_budget(conditions)
        if self._rng.rand() < self.cfg.mutation_rate:
            rule.action = 1 - int(rule.action)

    def _delete_low_fitness_rules(self, n=1):
        for _ in range(int(n)):
            experienced = [
                (i, r) for i, r in enumerate(self.population)
                if int(r.experience) > int(self.cfg.deletion_threshold)
            ]
            pool = experienced if experienced else list(enumerate(self.population))
            if not pool:
                return
            worst_idx, _ = min(
                pool,
                key=lambda item: (
                    float(item[1].fitness),
                    float(item[1].accuracy),
                    -int(item[1].experience),
                    int(item[1].numerosity),
                ),
            )
            self.population.pop(int(worst_idx))

    def _enforce_population_limit(self):
        limit = max(1, int(self.cfg.population_size))
        while len(self.population) > limit:
            self._delete_low_fitness_rules(n=1)

    def _subsumption(self, correct_set):
        candidates = [
            r for r in correct_set
            if float(r.fitness) > float(self.cfg.min_fitness_for_subsumption)
        ]
        if not candidates:
            return
        generalizer = max(
            candidates,
            key=lambda r: (
                self._generality(r),
                float(r.fitness) * int(r.numerosity),
                int(r.experience),
            ),
        )
        remove_ids = []
        for rule in correct_set:
            if rule is generalizer:
                continue
            if self._is_more_general(generalizer, rule):
                generalizer.numerosity += int(rule.numerosity)
                remove_ids.append(id(rule))
        if remove_ids:
            remove = set(remove_ids)
            self.population = [r for r in self.population if id(r) not in remove]

    def _generality(self, rule):
        return sum(1 for _, lo, hi in rule.conditions if lo == -np.inf and hi == np.inf)

    def _is_more_general(self, general, specific):
        if int(general.action) != int(specific.action):
            return False
        strictly = False
        for (_, glo, ghi), (_, slo, shi) in zip(general.conditions, specific.conditions):
            if glo > slo or ghi < shi:
                return False
            if glo < slo or ghi > shi:
                strictly = True
        return strictly

    def _is_wildcard_condition(self, condition):
        _, lo, hi = condition
        return lo == -np.inf and hi == np.inf

    def _conditions_human(self, conditions, feature_names=None, include_wildcards=True):
        out = []
        feature_names = feature_names or []
        for idx, lo, hi in conditions:
            if not include_wildcards and lo == -np.inf and hi == np.inf:
                continue
            base = f"x{int(idx) + 1}"
            if int(idx) < len(feature_names):
                base += f" ({feature_names[int(idx)]})"
            if lo == -np.inf and hi == np.inf:
                out.append(f"{base} is *")
            elif lo == -np.inf:
                out.append(f"{base} <= {hi:.6g}")
            elif hi == np.inf:
                out.append(f"{base} >= {lo:.6g}")
            else:
                out.append(f"{base} in [{lo:.6g}, {hi:.6g}]")
        return out

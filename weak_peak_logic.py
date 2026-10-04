"""Reusable logical operator for weak but temporally aligned score peaks.

The operator is intentionally fitted on training data only.  It stores a weak
threshold, a strong threshold, local prominence and a temporal radius, then
applies the same contract unchanged to validation and forecast scores.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class WeakPeakConfig:
    weak_threshold: float
    strong_threshold: float
    min_prominence: float
    event_radius: int
    objective: float = 0.0


class WeakPeakLogicOperator:
    def __init__(self, config: WeakPeakConfig | None = None):
        self.config = config
        self.training_metrics: dict | None = None
        self.search_trials: int = 0

    @staticmethod
    def _local_prominence(scores: np.ndarray, index: int, radius: int) -> float:
        lo = max(0, index - radius)
        hi = min(len(scores), index + radius + 1)
        neighbors = np.concatenate((scores[lo:index], scores[index + 1 : hi]))
        if len(neighbors) == 0:
            return float(scores[index])
        return float(scores[index] - np.max(neighbors))

    @classmethod
    def apply_config(
        cls, scores: np.ndarray, config: WeakPeakConfig
    ) -> tuple[np.ndarray, np.ndarray]:
        scores = np.clip(np.asarray(scores, dtype=float).reshape(-1), 0.0, 1.0)
        binary = np.zeros(len(scores), dtype=int)
        reason = np.full(len(scores), "zero", dtype=object)
        strong = scores >= float(config.strong_threshold)
        binary[strong] = 1
        reason[strong] = "strong_threshold"
        radius = max(1, int(config.event_radius))
        for index, value in enumerate(scores):
            if binary[index] or value < float(config.weak_threshold):
                continue
            lo = max(0, index - radius)
            hi = min(len(scores), index + radius + 1)
            if value + 1e-12 < float(np.max(scores[lo:hi])):
                continue
            prominence = cls._local_prominence(scores, index, radius)
            if prominence + 1e-12 >= float(config.min_prominence):
                binary[index] = 1
                reason[index] = "weak_local_peak"
        return binary, reason

    @staticmethod
    def metrics(
        scores: np.ndarray,
        target: np.ndarray,
        binary: np.ndarray,
        event_radius: int,
    ) -> dict:
        scores = np.asarray(scores, dtype=float).reshape(-1)
        target = np.asarray(target, dtype=int).reshape(-1)
        binary = np.asarray(binary, dtype=int).reshape(-1)
        events = np.flatnonzero(target == 1)
        detections = np.flatnonzero(binary == 1)
        radius = max(1, int(event_radius))
        distances = []
        covered = []
        for event in events:
            distance = (
                min(abs(int(event) - int(detection)) for detection in detections)
                if len(detections)
                else radius + 1
            )
            distances.append(distance)
            covered.append(distance <= radius)
        true_detection = np.zeros(len(detections), dtype=bool)
        for index, detection in enumerate(detections):
            true_detection[index] = bool(
                len(events)
                and np.min(np.abs(events - int(detection))) <= radius
            )
        negatives = max(int(np.sum(target == 0)), 1)
        false_detections = int(np.sum(~true_detection))
        coverage = float(np.mean(covered)) if covered else 0.0
        precision = (
            float(np.mean(true_detection)) if len(true_detection) else 0.0
        )
        mean_distance = float(np.mean(distances)) if distances else float(radius + 1)
        alignment = max(0.0, 1.0 - mean_distance / float(radius + 1))
        false_positive_rate = false_detections / negatives
        if len(events):
            positions = np.arange(len(scores))
            nearest = np.min(np.abs(positions[:, None] - events[None, :]), axis=1)
            ideal = np.exp(-nearest / max(float(radius), 1.0))
            trend = (
                float(np.corrcoef(scores, ideal)[0, 1])
                if np.std(scores) > 1e-12 and np.std(ideal) > 1e-12
                else 0.0
            )
            trend = float(np.nan_to_num(trend, nan=0.0))
        else:
            trend = 0.0
        objective = (
            0.32 * coverage
            + 0.20 * precision
            + 0.20 * alignment
            + 0.16 * max(trend, 0.0)
            + 0.12 * max(0.0, 1.0 - false_positive_rate)
        )
        return {
            "event_count": int(len(events)),
            "detection_count": int(len(detections)),
            "event_coverage": coverage,
            "detection_precision": precision,
            "event_peak_distances": [int(value) for value in distances],
            "mean_peak_distance": mean_distance,
            "alignment": alignment,
            "trend_correlation": trend,
            "false_detections": false_detections,
            "false_positive_rate": float(false_positive_rate),
            "objective": float(objective),
        }

    def fit(self, scores: np.ndarray, target: np.ndarray) -> "WeakPeakLogicOperator":
        scores = np.clip(np.asarray(scores, dtype=float).reshape(-1), 0.0, 1.0)
        target = np.asarray(target, dtype=int).reshape(-1)
        if len(scores) != len(target):
            raise ValueError("scores and target must have the same length")
        if not np.any(target == 1):
            raise ValueError("weak-peak fitting needs at least one positive event")
        positive_scores = scores[target == 1]
        nonzero = scores[scores > 0]
        weak_candidates = np.unique(
            np.clip(
                np.concatenate(
                    (
                        np.asarray([0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20]),
                        np.quantile(nonzero, [0.10, 0.25, 0.40, 0.55])
                        if len(nonzero)
                        else np.asarray([0.10]),
                        np.quantile(positive_scores, [0.10, 0.30, 0.50]),
                    )
                ),
                0.001,
                0.80,
            )
        )
        strong_candidates = np.unique(
            np.clip(
                np.concatenate(
                    (
                        np.asarray([0.35, 0.50, 0.65, 0.80]),
                        np.quantile(scores, [0.80, 0.90, 0.95]),
                    )
                ),
                0.10,
                0.99,
            )
        )
        prominence_candidates = np.asarray([0.0, 0.01, 0.025, 0.05, 0.10])
        best = None
        trials = 0
        for radius in (1, 2, 3):
            for weak in weak_candidates:
                for strong in strong_candidates:
                    if strong < weak:
                        continue
                    for prominence in prominence_candidates:
                        trials += 1
                        config = WeakPeakConfig(
                            weak_threshold=float(weak),
                            strong_threshold=float(strong),
                            min_prominence=float(prominence),
                            event_radius=radius,
                        )
                        binary, _ = self.apply_config(scores, config)
                        metrics = self.metrics(scores, target, binary, radius)
                        key = (
                            metrics["objective"],
                            metrics["event_coverage"],
                            -metrics["mean_peak_distance"],
                            -metrics["false_positive_rate"],
                            float(weak),
                        )
                        if best is None or key > best[0]:
                            best = (key, config, metrics)
        assert best is not None
        self.config = WeakPeakConfig(
            **{
                **asdict(best[1]),
                "objective": float(best[2]["objective"]),
            }
        )
        self.training_metrics = best[2]
        self.search_trials = trials
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        if self.config is None:
            raise RuntimeError("WeakPeakLogicOperator is not fitted")
        return self.apply_config(scores, self.config)[0]

    def explain(self, scores: np.ndarray) -> dict:
        if self.config is None:
            raise RuntimeError("WeakPeakLogicOperator is not fitted")
        binary, reason = self.apply_config(scores, self.config)
        return {
            "score": np.asarray(scores, dtype=float).tolist(),
            "logical_prediction": binary.tolist(),
            "reason": reason.tolist(),
        }

    def to_dict(self) -> dict:
        if self.config is None:
            raise RuntimeError("WeakPeakLogicOperator is not fitted")
        return {
            "operator": "weak_peak_logic_v1",
            "config": asdict(self.config),
            "training_metrics": self.training_metrics,
            "search_trials": self.search_trials,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )

    @classmethod
    def load(cls, path: str | Path) -> "WeakPeakLogicOperator":
        payload = json.loads(Path(path).read_text())
        operator = cls(WeakPeakConfig(**payload["config"]))
        operator.training_metrics = payload.get("training_metrics")
        operator.search_trials = int(payload.get("search_trials", 0))
        return operator

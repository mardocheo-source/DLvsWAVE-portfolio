#!/usr/bin/env python3
"""Leakage-safe empirical quantile discretization for scientific pipelines."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class QuantileBinTransformer:
    """Map each feature to evenly spaced ordinal levels using training quantiles.

    With four bins the emitted levels are exactly ``0, 1/3, 2/3, 1``.  Cut
    points are learned independently for each feature and exclusively from the
    rows supplied to :meth:`fit`; callers must therefore instantiate one
    transformer per chronological fold.
    """

    n_bins: int = 4

    def __post_init__(self) -> None:
        if self.n_bins < 2:
            raise ValueError("n_bins must be at least two")
        self.quantiles_: np.ndarray | None = None
        self.levels_ = np.linspace(0.0, 1.0, self.n_bins)

    def fit(self, values: np.ndarray) -> "QuantileBinTransformer":
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or not matrix.shape[0]:
            raise ValueError("Quantile fit requires a non-empty two-dimensional matrix")
        probabilities = np.arange(1, self.n_bins, dtype=float) / self.n_bins
        try:
            self.quantiles_ = np.nanquantile(
                matrix, probabilities, axis=0, method="linear"
            ).T
        except TypeError:  # NumPy < 1.22 compatibility
            self.quantiles_ = np.nanquantile(
                matrix, probabilities, axis=0, interpolation="linear"
            ).T
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.quantiles_ is None:
            raise RuntimeError("QuantileBinTransformer has not been fitted")
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != self.quantiles_.shape[0]:
            raise ValueError("Transform feature count differs from fitted quantiles")
        output = np.empty_like(matrix, dtype=float)
        for feature in range(matrix.shape[1]):
            column = matrix[:, feature]
            cuts = self.quantiles_[feature]
            bins = np.searchsorted(cuts, column, side="right")
            output[:, feature] = self.levels_[np.clip(bins, 0, self.n_bins - 1)]
            output[~np.isfinite(column), feature] = 0.0
        return output

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)

    def audit(self) -> dict:
        if self.quantiles_ is None:
            raise RuntimeError("QuantileBinTransformer has not been fitted")
        duplicate_cut_features = int(
            np.sum(np.any(np.diff(self.quantiles_, axis=1) <= 0.0, axis=1))
        )
        return {
            "mode": "training_fold_empirical_quantiles",
            "n_bins": int(self.n_bins),
            "output_levels": self.levels_.tolist(),
            "feature_count": int(self.quantiles_.shape[0]),
            "features_with_tied_cut_points": duplicate_cut_features,
            "fit_scope": "training rows only; validation and forecast never fit cut points",
        }


class IdentityTransformer:
    """Small sklearn-compatible identity used by optional preprocessing paths."""

    def fit(self, values: np.ndarray) -> "IdentityTransformer":
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(values, dtype=float)

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.transform(values)

    def audit(self) -> dict:
        return {"mode": "identity", "n_bins": 0}

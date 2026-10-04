"""CPU-first probabilistic models and asymmetric metrics for binary events."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score

from src.models.base import FeatureScaler
from src.models.deep_learning import DeepTabularResNet
from src.models.kan import KANNetwork
from src.models.lcs import LCSForecastingModel


@dataclass
class BinaryMetrics:
    sample_count: int
    positives: int
    negatives: int
    focal_loss: float
    bce_loss: float
    depression_mae: float
    precision: float
    recall: float
    f1: float
    fp_rate: float
    fn_rate: float
    auc: float
    tp: int
    fp: int
    fn: int
    tn: int
    threshold: float
    objective_loss: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def focal_loss_numpy(y_true: np.ndarray, probability: np.ndarray, alpha: float = 0.75, gamma: float = 2.0) -> float:
    y = np.asarray(y_true, dtype=np.float64)
    p = np.clip(np.asarray(probability, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    pt = np.where(y == 1, p, 1.0 - p)
    alpha_t = np.where(y == 1, alpha, 1.0 - alpha)
    return float(np.mean(-alpha_t * np.power(1.0 - pt, gamma) * np.log(pt)))


def binary_metrics(
    y_true: Sequence[float],
    probability: Sequence[float],
    threshold: float,
    *,
    alpha: float = 0.75,
    gamma: float = 2.0,
) -> BinaryMetrics:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.clip(np.asarray(probability, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    predicted = p >= float(threshold)
    tp = int(np.sum((y == 1) & predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    tn = int(np.sum((y == 0) & ~predicted))
    precision = float(tp / (tp + fp)) if tp + fp else 0.0
    recall = float(tp / (tp + fn)) if tp + fn else 0.0
    f1 = float(2.0 * precision * recall / (precision + recall)) if precision + recall else 0.0
    fp_rate = float(fp / (fp + tn)) if fp + tn else 0.0
    fn_rate = float(fn / (fn + tp)) if fn + tp else 0.0
    bce = float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1.0 - p))))
    auc = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else 0.5
    focal = focal_loss_numpy(y, p, alpha=alpha, gamma=gamma)
    # Positive-only shortfall: a model collapsed near zero receives a value
    # close to one even if the quiet majority dominates ordinary MAE.
    positive_mask = y == 1
    depression_mae = (
        float(np.mean(np.maximum(0.0, 1.0 - p[positive_mask])))
        if positive_mask.any() else 0.0
    )
    objective = (
        focal
        + 3.0 * (1.0 - f1)
        + 3.5 * fp_rate
        + 2.5 * fn_rate
        + 0.5 * depression_mae
    )
    return BinaryMetrics(
        sample_count=len(y),
        positives=int(np.sum(y == 1)),
        negatives=int(np.sum(y == 0)),
        focal_loss=focal,
        bce_loss=bce,
        depression_mae=depression_mae,
        precision=precision,
        recall=recall,
        f1=f1,
        fp_rate=fp_rate,
        fn_rate=fn_rate,
        auc=auc,
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        threshold=float(threshold),
        objective_loss=float(objective),
    )


class FocalBCEWithLogits(nn.Module):
    def __init__(self, alpha: float = 0.75, gamma: float = 2.0) -> None:
        super().__init__()
        self.alpha = float(alpha)
        self.gamma = float(gamma)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        probability = torch.sigmoid(logits)
        pt = torch.where(target > 0.5, probability, 1.0 - probability)
        alpha_t = torch.where(
            target > 0.5,
            torch.full_like(target, self.alpha),
            torch.full_like(target, 1.0 - self.alpha),
        )
        return (alpha_t * torch.pow(1.0 - pt, self.gamma) * bce).mean()


class _TorchBinaryModel:
    def __init__(
        self,
        *,
        learning_rate: float,
        weight_decay: float,
        focal_alpha: float,
        focal_gamma: float,
        probability_bias: float,
        seed: int,
    ) -> None:
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.focal_alpha = float(focal_alpha)
        self.focal_gamma = float(focal_gamma)
        self.probability_bias = float(probability_bias)
        self.seed = int(seed)
        self.device = torch.device("cpu")
        self.scaler: FeatureScaler
        self.model: nn.Module
        self.feature_names: list[str] = []

    def _make_network(self, input_dim: int) -> nn.Module:
        raise NotImplementedError

    def fit(self, x: pd.DataFrame, y: pd.Series, *, epochs: int, batch_size: int = 64) -> None:
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        self.scaler = FeatureScaler(method="standardize")
        x_scaled = self.scaler.fit_transform(x, x.columns)
        self.feature_names = list(x.columns)
        y_array = y.to_numpy(dtype=np.float32).reshape(-1, 1)
        self.model = self._make_network(x_scaled.shape[1]).to(self.device)
        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
        )
        criterion = FocalBCEWithLogits(self.focal_alpha, self.focal_gamma)
        tensor_x = torch.as_tensor(x_scaled, dtype=torch.float32)
        tensor_y = torch.as_tensor(y_array, dtype=torch.float32)
        class_count = np.bincount(y.to_numpy(dtype=np.int8), minlength=2).astype(float)
        weights = np.where(y_array.ravel() == 1, class_count.sum() / max(class_count[1], 1.0), 1.0)
        generator = torch.Generator().manual_seed(self.seed)
        sampler = torch.utils.data.WeightedRandomSampler(
            torch.as_tensor(weights, dtype=torch.double), len(weights), replacement=True, generator=generator
        )
        loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(tensor_x, tensor_y),
            batch_size=min(int(batch_size), len(tensor_x)),
            sampler=sampler,
        )
        self.model.train()
        for _ in range(int(epochs)):
            for batch_x, batch_y in loader:
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(self.model(batch_x.to(self.device)), batch_y.to(self.device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
                optimizer.step()

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        transformed = self.scaler.transform(x[self.feature_names])
        self.model.eval()
        with torch.no_grad():
            logits = self.model(torch.as_tensor(transformed, dtype=torch.float32, device=self.device))
            return torch.sigmoid(logits + self.probability_bias).cpu().numpy().ravel()

    def save(self, path: str | Path, params: dict[str, Any]) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "params": params,
                "feature_names": self.feature_names,
                "scaler": self.scaler.to_dict(),
                "state_dict": self.model.state_dict(),
            },
            destination,
        )


class BinaryKANModel(_TorchBinaryModel):
    def __init__(self, *, grid_size: int, spline_order: int, hidden_dim: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.grid_size = int(grid_size)
        self.spline_order = int(spline_order)
        self.hidden_dim = int(hidden_dim)

    def _make_network(self, input_dim: int) -> nn.Module:
        return KANNetwork(
            in_dim=input_dim,
            out_dim=1,
            hidden_dims=(self.hidden_dim, max(4, self.hidden_dim // 2)),
            grid_size=self.grid_size,
            spline_order=self.spline_order,
        )


class BinaryResNetModel(_TorchBinaryModel):
    def __init__(self, *, hidden_dim: int, num_layers: int, dropout: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.hidden_dim = int(hidden_dim)
        self.num_layers = int(num_layers)
        self.dropout = float(dropout)

    def _make_network(self, input_dim: int) -> nn.Module:
        return DeepTabularResNet(
            in_dim=input_dim,
            out_dim=1,
            hidden_dim=self.hidden_dim,
            num_layers=self.num_layers,
            dropout=self.dropout,
        )


class BinaryLCSModel:
    def __init__(
        self,
        *,
        population_size: int,
        learning_rate: float,
        mutation_rate: float,
        crossover_rate: float,
        seed: int,
        probability_bias: float,
        distance_temperature: float,
        **_: Any,
    ) -> None:
        self.seed = int(seed)
        self.probability_bias = float(probability_bias)
        self.distance_temperature = float(distance_temperature)
        self.model = LCSForecastingModel(
            population_size=int(population_size),
            learning_rate=float(learning_rate),
            mutation_rate=float(mutation_rate),
            crossover_rate=float(crossover_rate),
        )
        self.feature_names: list[str] = []

    def fit(self, x: pd.DataFrame, y: pd.Series, *, epochs: int, batch_size: int = 64) -> None:
        del batch_size
        np.random.seed(self.seed)
        self.feature_names = list(x.columns)
        positives = np.flatnonzero(y.to_numpy(dtype=np.int8) == 1)
        repeats = min(
            2,
            max(1, int(np.ceil(max(1, len(y) - len(positives)) / max(1, len(positives)) / 8))),
        )
        if len(positives):
            augmented_x = pd.concat([x, *[x.iloc[positives]] * repeats], ignore_index=True)
            augmented_y = pd.concat([y, *[y.iloc[positives]] * repeats], ignore_index=True)
        else:
            augmented_x, augmented_y = x, y
        self.model.fit(
            augmented_x,
            augmented_y,
            feature_names=self.feature_names,
            target_name="japan_m77_event",
            epochs=int(epochs),
        )

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        scaled = self.model.scaler.transform(x[self.feature_names])
        positive_rules = [rule for rule in self.model.population if rule.action >= 0.5]
        negative_rules = [rule for rule in self.model.population if rule.action < 0.5]
        if not positive_rules or not negative_rules:
            raw = np.clip(self.model.predict(x[self.feature_names]), 1e-5, 1.0 - 1e-5)
            logits = np.log(raw / (1.0 - raw)) + self.probability_bias
            return 1.0 / (1.0 + np.exp(-logits))

        def closest_distance(sample: np.ndarray, rules: list[Any]) -> float:
            distances = []
            for rule in rules:
                outside = np.maximum(0.0, rule.lows - sample) + np.maximum(0.0, sample - rule.highs)
                distance = float(np.mean(outside)) / max(0.05, float(rule.fitness))
                distances.append(distance)
            return min(distances)

        logits = np.empty(len(scaled), dtype=np.float64)
        for index, sample in enumerate(scaled):
            positive_distance = closest_distance(sample, positive_rules)
            negative_distance = closest_distance(sample, negative_rules)
            logits[index] = (
                (negative_distance - positive_distance) / max(1e-4, self.distance_temperature)
                + self.probability_bias
            )
        logits = np.clip(logits, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-logits))

    def save(self, path: str | Path, params: dict[str, Any]) -> None:
        del params
        self.model.save(path)


def make_binary_model(model_type: str, params: dict[str, Any], seed: int):
    common = {
        "learning_rate": float(params["learning_rate"]),
        "seed": int(seed),
    }
    if model_type == "kan":
        return BinaryKANModel(
            grid_size=int(params["grid_size"]),
            spline_order=int(params["spline_order"]),
            hidden_dim=int(params["hidden_dim"]),
            weight_decay=float(params["weight_decay"]),
            focal_alpha=float(params["focal_alpha"]),
            focal_gamma=float(params["focal_gamma"]),
            probability_bias=float(params["probability_bias"]),
            **common,
        )
    if model_type == "deep_learning":
        return BinaryResNetModel(
            hidden_dim=int(params["hidden_dim"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
            weight_decay=float(params["weight_decay"]),
            focal_alpha=float(params["focal_alpha"]),
            focal_gamma=float(params["focal_gamma"]),
            probability_bias=float(params["probability_bias"]),
            **common,
        )
    if model_type == "lcs":
        return BinaryLCSModel(
            population_size=int(params["population_size"]),
            mutation_rate=float(params["mutation_rate"]),
            crossover_rate=float(params["crossover_rate"]),
            probability_bias=float(params["probability_bias"]),
            distance_temperature=float(params["distance_temperature"]),
            **common,
        )
    raise ValueError(f"Unknown binary model type: {model_type}")

"""Neural surrogate components for DLVS-Wave Phase 2 meta-optimization.

The surrogate operates in a normalized continuous parameter space.  Decoding
always projects a proposal back onto the exact Phase 1 search domains so the
downstream models never receive an invalid hyperparameter vector.
"""
from __future__ import annotations

import math
from contextlib import nullcontext
from typing import Any

import numpy as np
import torch
import torch.nn as nn


class ParameterEncoder:
    """Bidirectional encoder for shared and model-specific hyperparameters."""

    def __init__(self, model_type: str) -> None:
        normalized = model_type.lower()
        self.model_type = "deep_learning" if normalized == "deep" else normalized
        self.param_specs = self._get_specs(self.model_type)
        self.dim = len(self.param_specs)
        self.names = [spec["name"] for spec in self.param_specs]

    @staticmethod
    def _get_specs(model_type: str) -> list[dict[str, Any]]:
        base_specs: list[dict[str, Any]] = [
            {"name": "train_start_year", "type": "discrete", "domain": list(range(1900, 1990, 10))},
            {"name": "window_before", "type": "integer", "min": 2, "max": 6},
            {"name": "window_after", "type": "integer", "min": 2, "max": 6},
            {"name": "background_sample_ratio", "type": "discrete", "domain": [0.05, 0.10, 0.15, 0.20, 0.25]},
        ]
        if model_type == "kan":
            specific = [
                {"name": "grid_size", "type": "integer", "min": 3, "max": 8},
                {"name": "spline_order", "type": "integer", "min": 2, "max": 4},
                {"name": "learning_rate", "type": "continuous_log", "min": 1e-3, "max": 3e-2},
            ]
        elif model_type == "deep_learning":
            specific = [
                {"name": "hidden_dim", "type": "discrete", "domain": [32, 64, 96, 128]},
                {"name": "num_layers", "type": "integer", "min": 2, "max": 5},
                {"name": "dropout", "type": "discrete", "domain": [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]},
                {"name": "learning_rate", "type": "continuous_log", "min": 1e-4, "max": 1e-2},
            ]
        elif model_type == "lcs":
            specific = [
                {"name": "population_size", "type": "discrete", "domain": list(range(50, 251, 25))},
                {"name": "learning_rate", "type": "discrete", "domain": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]},
                {"name": "crossover_rate", "type": "discrete", "domain": [0.60, 0.70, 0.80, 0.90]},
                {"name": "mutation_rate", "type": "discrete", "domain": [0.02, 0.04, 0.06, 0.08, 0.10]},
            ]
        else:
            raise ValueError(f"Unsupported model_type: {model_type}")
        return base_specs + specific

    @staticmethod
    def _finite_float(value: Any, fallback: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return fallback
        return numeric if math.isfinite(numeric) else fallback

    def encode(self, params: dict[str, Any]) -> np.ndarray:
        """Encode a parameter dictionary into a clipped ``[0, 1]`` vector."""
        encoded = np.zeros(self.dim, dtype=np.float32)
        for index, spec in enumerate(self.param_specs):
            name = spec["name"]
            value = params.get(name)
            if name == "train_start_year" and value is None:
                raw_date = params.get("train_start_date", "1900-01-01")
                try:
                    value = int(str(raw_date).split("-", 1)[0])
                except (TypeError, ValueError):
                    value = 1900

            kind = spec["type"]
            if kind == "discrete":
                domain = np.asarray(spec["domain"], dtype=float)
                numeric = self._finite_float(value, float(domain[0]))
                nearest = int(np.argmin(np.abs(domain - numeric)))
                encoded[index] = nearest / max(1, len(domain) - 1)
            elif kind == "integer":
                minimum, maximum = float(spec["min"]), float(spec["max"])
                numeric = self._finite_float(value, minimum)
                encoded[index] = (numeric - minimum) / (maximum - minimum)
            elif kind == "continuous_log":
                minimum, maximum = float(spec["min"]), float(spec["max"])
                numeric = float(np.clip(self._finite_float(value, minimum), minimum, maximum))
                encoded[index] = (math.log10(numeric) - math.log10(minimum)) / (
                    math.log10(maximum) - math.log10(minimum)
                )
            else:  # pragma: no cover - guarded by the static specification
                raise ValueError(f"Unsupported parameter type: {kind}")
        return np.clip(encoded, 0.0, 1.0)

    def decode(self, vector: np.ndarray | torch.Tensor) -> dict[str, Any]:
        """Project a continuous vector back onto valid typed domains."""
        if isinstance(vector, torch.Tensor):
            vector = vector.detach().cpu().numpy()
        values = np.clip(np.asarray(vector, dtype=np.float32).reshape(-1), 0.0, 1.0)
        if len(values) != self.dim:
            raise ValueError(f"Expected {self.dim} encoded values, received {len(values)}")

        params: dict[str, Any] = {}
        for index, spec in enumerate(self.param_specs):
            normalized = float(values[index])
            kind = spec["type"]
            if kind == "discrete":
                domain = spec["domain"]
                position = int(round(normalized * (len(domain) - 1)))
                params[spec["name"]] = domain[max(0, min(len(domain) - 1, position))]
            elif kind == "integer":
                minimum, maximum = int(spec["min"]), int(spec["max"])
                params[spec["name"]] = int(np.clip(round(minimum + normalized * (maximum - minimum)), minimum, maximum))
            elif kind == "continuous_log":
                minimum, maximum = float(spec["min"]), float(spec["max"])
                value = 10 ** (math.log10(minimum) + normalized * (math.log10(maximum) - math.log10(minimum)))
                params[spec["name"]] = float(np.clip(value, minimum, maximum))

        year = int(params["train_start_year"])
        params["train_start_date"] = f"{year:04d}-01-01"
        return params

    def canonical_key(self, params: dict[str, Any]) -> tuple[Any, ...]:
        """Return a stable key after projection onto the legal search space."""
        canonical = self.decode(self.encode(params))
        key: list[Any] = []
        for name in self.names:
            value = canonical[name]
            key.append(round(value, 12) if isinstance(value, float) else value)
        return tuple(key)


class ResidualDenseBlock(nn.Module):
    """LayerNorm residual block that remains valid for one-point EI batches."""

    def __init__(self, dim: int, dropout: float = 0.15) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
        )
        self.activation = nn.GELU()

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.activation(inputs + self.block(inputs))


class DeepSurrogateModel(nn.Module):
    """Four-head tabular surrogate with Monte-Carlo Dropout uncertainty."""

    OUTPUT_NAMES = ("loss", "mse", "f1", "depression_mae")

    def __init__(self, in_dim: int, hidden_dim: int = 64, num_blocks: int = 2, dropout: float = 0.15) -> None:
        super().__init__()
        self.in_proj = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU())
        self.blocks = nn.ModuleList(ResidualDenseBlock(hidden_dim, dropout) for _ in range(num_blocks))
        self.dropout_layer = nn.Dropout(dropout)
        self.heads = nn.ModuleDict({name: nn.Linear(hidden_dim, 1) for name in self.OUTPUT_NAMES})

    def forward(self, inputs: torch.Tensor) -> dict[str, torch.Tensor]:
        hidden = self.in_proj(inputs)
        for block in self.blocks:
            hidden = block(hidden)
        hidden = self.dropout_layer(hidden)
        return {name: head(hidden) for name, head in self.heads.items()}

    def stacked(self, inputs: torch.Tensor) -> torch.Tensor:
        outputs = self.forward(inputs)
        return torch.cat([outputs[name] for name in self.OUTPUT_NAMES], dim=1)

    def _enable_mc_dropout(self) -> None:
        self.eval()
        for module in self.modules():
            if isinstance(module, nn.Dropout):
                module.train()

    def predict_with_uncertainty(
        self,
        inputs: torch.Tensor,
        n_samples: int = 25,
        output_name: str = "loss",
        differentiable: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return MC-Dropout mean/std, optionally preserving input gradients."""
        if output_name not in self.OUTPUT_NAMES:
            raise ValueError(f"Unknown surrogate output: {output_name}")
        if n_samples < 2:
            raise ValueError("n_samples must be at least 2")
        previous_training = self.training
        self._enable_mc_dropout()
        context = nullcontext() if differentiable else torch.no_grad()
        with context:
            samples = torch.stack([self.forward(inputs)[output_name] for _ in range(n_samples)], dim=0)
            mean = samples.mean(dim=0)
            std = samples.std(dim=0, unbiased=False).clamp_min(1e-6)
        self.train(previous_training)
        return mean, std


def compute_expected_improvement(mu: torch.Tensor, sigma: torch.Tensor, best_loss: float | torch.Tensor) -> torch.Tensor:
    """Expected Improvement for minimization, in the surrogate target scale."""
    sigma = sigma.clamp_min(1e-7)
    best = torch.as_tensor(best_loss, dtype=mu.dtype, device=mu.device)
    improvement = best - mu
    z_score = improvement / sigma
    standard_normal = torch.distributions.Normal(
        torch.tensor(0.0, dtype=mu.dtype, device=mu.device),
        torch.tensor(1.0, dtype=mu.dtype, device=mu.device),
    )
    return (improvement * standard_normal.cdf(z_score) + sigma * torch.exp(standard_normal.log_prob(z_score))).clamp_min(0.0)


class ExpectedImprovementAcquisition(nn.Module):
    """Small module wrapper useful for gradient-based latent optimization."""

    def __init__(self, best_loss: float) -> None:
        super().__init__()
        self.best_loss = float(best_loss)

    def forward(self, mu: torch.Tensor, sigma: torch.Tensor) -> torch.Tensor:
        return compute_expected_improvement(mu, sigma, self.best_loss)


class InverseConditionalGenerator(nn.Module):
    """Generate normalized hyperparameters conditioned on normalized targets."""

    def __init__(self, target_dim: int = 4, param_dim: int = 7, hidden_dim: int = 64, latent_noise_dim: int = 8) -> None:
        super().__init__()
        self.latent_noise_dim = latent_noise_dim
        self.net = nn.Sequential(
            nn.Linear(target_dim + latent_noise_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, param_dim),
            nn.Sigmoid(),
        )

    def forward(self, target_metrics: torch.Tensor, noise: torch.Tensor | None = None) -> torch.Tensor:
        if noise is None:
            noise = torch.randn(
                target_metrics.size(0), self.latent_noise_dim, dtype=target_metrics.dtype, device=target_metrics.device
            )
        if noise.shape != (target_metrics.size(0), self.latent_noise_dim):
            raise ValueError("noise has an incompatible shape")
        return self.net(torch.cat([target_metrics, noise], dim=-1))

"""KAN backend/readout for DLvsWAVE.

This module wraps `pykan` behind the same small fit/predict surface used by
the other readouts.  The defaults are deliberately conservative: KAN is useful
as an interpretable spline-like comparator, but it can be expensive if the
network is allowed to grow too much.
"""
import contextlib
import io
import os
from dataclasses import asdict, dataclass, replace

import numpy as np
from sklearn.preprocessing import StandardScaler

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

try:
    import torch
    from kan import KAN
    KAN_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    torch = None
    KAN = None
    KAN_AVAILABLE = False


@dataclass
class KANConfig:
    hidden_width: int = 2
    hidden_layers: int = 1
    grid: int = 3
    spline_order: int = 3
    epochs: int = 35
    lr: float = 0.02
    lamb: float = 0.0
    opt: str = "Adam"
    seed: int = 0
    device: str = "cpu"
    update_grid: bool = False
    scale_features: bool = True
    target_scale: bool = True
    verbose: bool = False


KAN_PRESETS = {
    "tiny": KANConfig(hidden_width=2, hidden_layers=1, grid=3, epochs=35, lr=0.02),
    "small": KANConfig(hidden_width=4, hidden_layers=1, grid=3, epochs=60, lr=0.015),
    "wide": KANConfig(hidden_width=6, hidden_layers=1, grid=4, epochs=80, lr=0.01),
}


def serialize_kan_cfg(cfg):
    if cfg is None:
        return None
    return asdict(cfg)


class KANReadout:
    """Small sklearn-style readout backed by pykan.KAN."""

    def __init__(self, cfg=None):
        self.cfg = cfg or KANConfig()
        self.model = None
        self.x_scaler_ = None
        self.y_mean_ = 0.0
        self.y_std_ = 1.0
        self.n_params = 0
        self.history = {}

    def _prepare_x_fit(self, X):
        X = np.asarray(X, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if self.cfg.scale_features:
            self.x_scaler_ = StandardScaler()
            X = self.x_scaler_.fit_transform(X).astype(np.float32)
            X = np.tanh(X).astype(np.float32)
        return X

    def _prepare_x_predict(self, X):
        X = np.asarray(X, dtype=np.float32)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if self.cfg.scale_features and self.x_scaler_ is not None:
            X = self.x_scaler_.transform(X).astype(np.float32)
            X = np.tanh(X).astype(np.float32)
        return X

    def _prepare_y_fit(self, y):
        y = np.asarray(y, dtype=np.float32).reshape(-1, 1)
        if self.cfg.target_scale:
            self.y_mean_ = float(np.mean(y))
            self.y_std_ = float(np.std(y))
            if self.y_std_ < 1e-9:
                self.y_std_ = 1.0
            y = ((y - self.y_mean_) / self.y_std_).astype(np.float32)
        return y

    def fit(self, X, y, sample_weight=None):
        if not KAN_AVAILABLE:
            raise RuntimeError("pykan/torch non disponibile: installa pykan nella venv")
        Xp = self._prepare_x_fit(X)
        yp = self._prepare_y_fit(y)
        width = [int(Xp.shape[1])]
        width.extend([int(self.cfg.hidden_width)] * max(1, int(self.cfg.hidden_layers)))
        width.append(1)
        device = self.cfg.device
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch, "xpu") and torch.xpu.is_available():
                device = "xpu"
            else:
                device = "cpu"
        elif device == "xpu":
            if not (hasattr(torch, "xpu") and torch.xpu.is_available()):
                raise RuntimeError("KAN device xpu richiesto, ma torch.xpu non e' disponibile")
        self.model = KAN(
            width=width,
            grid=int(self.cfg.grid),
            k=int(self.cfg.spline_order),
            seed=int(self.cfg.seed),
            symbolic_enabled=False,
            auto_save=False,
            save_act=False,
            device=device,
        )
        dataset = {
            "train_input": torch.tensor(Xp, dtype=torch.float32, device=device),
            "train_label": torch.tensor(yp, dtype=torch.float32, device=device),
            "test_input": torch.tensor(Xp, dtype=torch.float32, device=device),
            "test_label": torch.tensor(yp, dtype=torch.float32, device=device),
        }
        steps = max(1, int(self.cfg.epochs))
        kwargs = {
            "opt": str(self.cfg.opt),
            "steps": steps,
            "lr": float(self.cfg.lr),
            "lamb": float(self.cfg.lamb),
            "update_grid": bool(self.cfg.update_grid),
            "log": max(steps + 1, 2),
            "batch": -1,
            "save_fig": False,
        }
        if sample_weight is not None:
            w = np.asarray(sample_weight, dtype=np.float32).reshape(-1, 1)
            if len(w) == len(yp):
                wt = torch.tensor(w, dtype=torch.float32, device=device)
                kwargs["loss_fn"] = lambda pred, target: torch.mean((pred - target) ** 2 * wt)
        if self.cfg.verbose:
            self.history = self.model.fit(dataset, **kwargs) or {}
        else:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.history = self.model.fit(dataset, **kwargs) or {}
        self.n_params = int(sum(p.numel() for p in self.model.parameters()))
        return self

    def predict(self, X):
        if self.model is None:
            raise RuntimeError("KANReadout non ancora fittato")
        Xp = self._prepare_x_predict(X)
        device = next(self.model.parameters()).device
        with torch.no_grad():
            pred = self.model(torch.tensor(Xp, dtype=torch.float32, device=device))
        out = pred.detach().cpu().numpy().reshape(-1)
        if self.cfg.target_scale:
            out = out * self.y_std_ + self.y_mean_
        return np.asarray(out, dtype=float)

    def clone_with(self, **updates):
        return KANReadout(cfg=replace(self.cfg, **updates))

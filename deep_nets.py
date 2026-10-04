"""
Deep learning baselines in PyTorch.

Due componenti:

1. DeepNet: MLP completo end-to-end (input grezzo -> y).
   Baseline "deep learning standard" per confronto onesto vs feature banks.

2. TorchMLPReadout: MLP usato COME readout sopra un feature bank.
   Sostituisce sklearn MLPRegressor con piu' flessibilita'
   (activation, dropout, weight_decay, batch_size, early stopping).

Entrambi hanno auto-config: dato n_input e n_output, decidono hidden sizes
di default, ma tutto e' customizzabile via DeepConfig.
"""
from dataclasses import dataclass, field, asdict, replace
from typing import List, Optional
import numpy as np
import time

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------

ACTIVATIONS = {
    "relu":      lambda: nn.ReLU(),
    "gelu":      lambda: nn.GELU(),
    "tanh":      lambda: nn.Tanh(),
    "silu":      lambda: nn.SiLU(),
    "leakyrelu": lambda: nn.LeakyReLU(0.01),
    "elu":       lambda: nn.ELU(),
}


@dataclass
class DeepConfig:
    """Config per DeepNet e TorchMLPReadout.
    Valori None = auto-config in base a n_input."""
    hidden_sizes: Optional[List[int]] = None   # None -> auto
    activation: str = "gelu"
    output_activation: str = "linear"         # "linear" | "sigmoid"
    dropout: float = 0.0
    batch_norm: bool = False
    epochs: int = 200
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    optimizer: str = "adamw"                  # adamw | adam | rmsprop | sgd
    loss: str = "mse"                         # mse | mae | binary_cross_entropy
    early_stop_patience: int = 20              # 0 = disabilitato
    validation_split: float = 0.1
    context_datetimes: Optional[list] = None
    auto_val_fraction_from_test: bool = True
    external_test_size: Optional[int] = None
    final_retrain_full_train: bool = True
    scale_features: bool = False
    target_window_threshold: Optional[float] = None
    target_window_event_count: int = 0
    target_window_event_start: Optional[int] = None
    target_window_pre_records: int = 0
    target_window_post_records: int = 0
    target_window_isolated_windows: bool = False
    validation_metric: str = "mse"             # "mse" | "f1" | "event_composite"
    validation_threshold: Optional[float] = None
    sample_weights: Optional[list] = None
    device: str = "auto"                       # "auto" | "cpu" | "cuda" | "xpu"
    seed: int = 0
    verbose: bool = False

    def resolve_hidden(self, n_input: int) -> List[int]:
        """Auto-config se hidden_sizes e' None.
        Regola: 3 layer decrescenti, dim = 4x input clipped [32, 256]."""
        if self.hidden_sizes is not None:
            return list(self.hidden_sizes)
        base = max(32, min(256, n_input * 4))
        return [base, base // 2, base // 4]

    def resolve_device(self) -> str:
        requested = str(self.device or "auto").strip().lower()
        if requested != "auto":
            if requested == "cuda" and (not TORCH_AVAILABLE or not torch.cuda.is_available()):
                raise RuntimeError("DeepNet device 'cuda' richiesto ma torch.cuda non e' disponibile")
            if requested == "xpu" and not torch_xpu_available():
                raise RuntimeError("DeepNet device 'xpu' richiesto ma torch.xpu non e' disponibile")
            return requested
        if TORCH_AVAILABLE and torch.cuda.is_available():
            return "cuda"
        if torch_xpu_available():
            return "xpu"
        return "cpu"


def torch_xpu_available() -> bool:
    if not TORCH_AVAILABLE:
        return False
    xpu = getattr(torch, "xpu", None)
    if xpu is None or not hasattr(xpu, "is_available"):
        return False
    try:
        return bool(xpu.is_available())
    except Exception:
        return False


# Preset comuni (selezionabili via --deep-preset)
DEEP_PRESETS = {
    "tiny":    DeepConfig(hidden_sizes=[16], activation="relu", epochs=100),
    "small":   DeepConfig(hidden_sizes=[32, 16], activation="relu", epochs=150),
    "default": DeepConfig(hidden_sizes=None, activation="gelu", epochs=200),
    "deep":    DeepConfig(hidden_sizes=[128, 128, 64, 32], activation="gelu",
                          dropout=0.1, epochs=300),
    "wide":    DeepConfig(hidden_sizes=[256, 128], activation="gelu",
                          dropout=0.1, epochs=200),
}


# ---------------------------------------------------------------------
# Architettura
# ---------------------------------------------------------------------

def build_mlp(n_in: int, n_out: int, cfg: DeepConfig) -> "nn.Module":
    if not TORCH_AVAILABLE:
        raise ImportError("torch non installato")
    hidden = cfg.resolve_hidden(n_in)
    act_factory = ACTIVATIONS.get(cfg.activation, ACTIVATIONS["gelu"])
    layers = []
    prev = n_in
    for h in hidden:
        layers.append(nn.Linear(prev, h))
        if cfg.batch_norm:
            layers.append(nn.BatchNorm1d(h))
        layers.append(act_factory())
        if cfg.dropout > 0:
            layers.append(nn.Dropout(cfg.dropout))
        prev = h
    layers.append(nn.Linear(prev, n_out))
    output_activation = str(cfg.output_activation or "linear").strip().lower()
    if output_activation == "sigmoid":
        layers.append(nn.Sigmoid())
    elif output_activation != "linear":
        raise ValueError(f"Unsupported deep output activation: {cfg.output_activation}")
    return nn.Sequential(*layers)


def _optimizer(model, cfg: DeepConfig):
    name = str(cfg.optimizer or "adamw").strip().lower()
    common = {"lr": cfg.lr, "weight_decay": cfg.weight_decay}
    if name == "adamw":
        return torch.optim.AdamW(model.parameters(), **common)
    if name == "adam":
        return torch.optim.Adam(model.parameters(), **common)
    if name == "rmsprop":
        return torch.optim.RMSprop(model.parameters(), **common)
    if name == "sgd":
        return torch.optim.SGD(model.parameters(), momentum=0.9, **common)
    raise ValueError(f"Unsupported deep optimizer: {cfg.optimizer}")


def _loss(cfg: DeepConfig):
    name = str(cfg.loss or "mse").strip().lower()
    if name == "mse":
        return nn.MSELoss()
    if name == "mae":
        return nn.L1Loss()
    if name in {"binary_cross_entropy", "bce"}:
        if str(cfg.output_activation).strip().lower() != "sigmoid":
            raise ValueError("binary_cross_entropy requires output_activation=sigmoid")
        return nn.BCELoss()
    raise ValueError(f"Unsupported deep loss: {cfg.loss}")


def count_params(model) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _datetimes_monotonic(context_datetimes):
    if context_datetimes is None:
        return False
    values = [dt for dt in context_datetimes if dt is not None]
    if len(values) < 2:
        return False
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))


def _resolve_validation_size(n, cfg: DeepConfig):
    if n <= 1:
        return 0
    if cfg.auto_val_fraction_from_test and cfg.external_test_size is not None:
        val_fraction = float(cfg.external_test_size) / float(n + int(cfg.external_test_size))
    else:
        val_fraction = float(cfg.validation_split)
    n_val = max(1, int(round(val_fraction * n)))
    return min(n - 1, n_val)


def _select_validation_indices(y_train, cfg: DeepConfig):
    n = len(y_train)
    if n <= 1:
        idx = np.arange(n, dtype=int)
        return idx, idx, {
            "strategy": "single_sample_fallback",
            "val_size": int(len(idx)),
        }
    n_val = _resolve_validation_size(n, cfg)

    threshold = cfg.target_window_threshold
    event_count = max(0, int(cfg.target_window_event_count))
    event_start = cfg.target_window_event_start
    pre_records = max(0, int(cfg.target_window_pre_records))
    post_records = max(0, int(cfg.target_window_post_records))
    isolated_windows = bool(cfg.target_window_isolated_windows)

    if threshold is not None and event_count > 0 and n > 1:
        y_flat = np.asarray(y_train, dtype=float).reshape(-1)
        event_idx = np.flatnonzero(y_flat >= threshold)
        if event_idx.size > 0:
            if event_start is None:
                end_event_pos = int(event_idx.size - 1)
                start_event_pos = max(0, end_event_pos - event_count + 1)
                end_idx = n - 1
                strategy = "tail_events_isolated" if isolated_windows else "tail_events_to_end"
            else:
                if event_start < 0:
                    start_event_pos = int(event_idx.size + event_start)
                else:
                    start_event_pos = int(event_start)
                start_event_pos = max(0, min(start_event_pos, int(event_idx.size - 1)))
                end_event_pos = min(int(event_idx.size - 1), start_event_pos + event_count - 1)
                end_idx = min(n - 1, int(event_idx[end_event_pos]) + post_records)
                strategy = "sliding_event_isolated" if isolated_windows else "sliding_event_window"

            start_idx = max(0, int(event_idx[start_event_pos]) - pre_records)
            start_idx = min(start_idx, n - 1)

            if isolated_windows:
                selected_events = event_idx[start_event_pos:end_event_pos + 1]
                pieces = []
                for ev in selected_events:
                    lo = max(0, int(ev) - pre_records)
                    hi = min(n - 1, int(ev) + post_records)
                    if lo <= hi:
                        pieces.append(np.arange(lo, hi + 1, dtype=int))
                if pieces:
                    val_idx = np.unique(np.concatenate(pieces))
                    # In temporal event validation, keep the validator strictly in
                    # the future of the training slice. This avoids using records
                    # between/after isolated validation events to tune early stop.
                    tr_idx = np.arange(0, int(val_idx[0]), dtype=int)
                    if tr_idx.size > 0 and val_idx.size > 0:
                        return tr_idx, val_idx, {
                            "strategy": strategy,
                            "threshold": float(threshold),
                            "requested_event_count": int(event_count),
                            "used_event_count": int(np.sum(y_flat[val_idx] >= threshold)),
                            "pre_records": int(pre_records),
                            "post_records": int(post_records),
                            "isolated_windows": True,
                            "event_start": None if event_start is None else int(event_start),
                            "resolved_event_start_pos": int(start_event_pos),
                            "resolved_event_end_pos": int(end_event_pos),
                            "val_start": int(val_idx[0]),
                            "val_end": int(val_idx[-1]),
                        }
            else:
                val_idx = np.arange(start_idx, end_idx + 1, dtype=int)
                tr_idx = np.concatenate((
                    np.arange(0, start_idx, dtype=int),
                    np.arange(end_idx + 1, n, dtype=int),
                ))
                if tr_idx.size > 0 and val_idx.size > 0:
                    return tr_idx, val_idx, {
                        "strategy": strategy,
                        "threshold": float(threshold),
                        "requested_event_count": int(event_count),
                        "used_event_count": int(np.sum(y_flat[val_idx] >= threshold)),
                        "pre_records": int(pre_records),
                        "post_records": int(post_records),
                        "isolated_windows": False,
                        "event_start": None if event_start is None else int(event_start),
                        "resolved_event_start_pos": int(start_event_pos),
                        "resolved_event_end_pos": int(end_event_pos),
                        "val_start": int(start_idx),
                        "val_end": int(end_idx),
                    }

    if n_val > 0 and _datetimes_monotonic(cfg.context_datetimes):
        split_at = n - n_val
        tr_idx = np.arange(0, split_at, dtype=int)
        val_idx = np.arange(split_at, n, dtype=int)
        strategy = (
            "chronological_tail_auto_fraction"
            if cfg.auto_val_fraction_from_test and cfg.external_test_size is not None
            else "chronological_tail_fixed_fraction"
        )
        return tr_idx, val_idx, {
            "strategy": strategy,
            "val_size": int(len(val_idx)),
        }

    idx = np.random.permutation(n)
    val_idx, tr_idx = idx[:n_val], idx[n_val:]
    return tr_idx, val_idx, {
        "strategy": "random_seeded_fallback",
        "val_size": int(len(val_idx)),
    }


# ---------------------------------------------------------------------
# Training loop riutilizzabile
# ---------------------------------------------------------------------

def _make_loader(X_tr, y_tr, cfg, sample_weights=None):
    if sample_weights is None:
        ds = TensorDataset(X_tr, y_tr)
    else:
        weights = torch.FloatTensor(sample_weights).view(-1, 1).to(X_tr.device)
        ds = TensorDataset(X_tr, y_tr, weights)
    return DataLoader(ds, batch_size=cfg.batch_size, shuffle=True)


def _binary_validation_metrics(y_true, y_pred, threshold, metric_name):
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    thr = 0.5 if threshold is None else float(threshold)
    y_true_evt = y_true >= thr
    y_pred_evt = y_pred >= thr
    tp = float(np.sum(y_true_evt & y_pred_evt))
    tn = float(np.sum((~y_true_evt) & (~y_pred_evt)))
    fp = float(np.sum((~y_true_evt) & y_pred_evt))
    fn = float(np.sum(y_true_evt & (~y_pred_evt)))
    precision = tp / max(tp + fp, 1e-12)
    recall = tp / max(tp + fn, 1e-12)
    specificity = tn / max(tn + fp, 1e-12)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    bal_acc = 0.5 * (recall + specificity)

    name = str(metric_name or "mse").strip().lower()
    fallback = ""
    if not np.any(y_true_evt):
        score = bal_acc
        fallback = "no_positive_validation_bal_acc"
    elif name == "f1":
        score = f1
    else:
        score = f1 * bal_acc

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
        "threshold": float(thr),
        "fallback": fallback,
    }


def train_torch_model(model, X_train, y_train, cfg: DeepConfig):
    """Allena model su (X_train, y_train). Ritorna history dict.
    Early stopping su validation split interno.
    Tutti input sono numpy arrays."""
    device = cfg.resolve_device()
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    X = torch.FloatTensor(X_train)
    y = torch.FloatTensor(y_train).view(-1, 1)

    # Split train/val
    tr_idx_np, val_idx_np, val_info = _select_validation_indices(y_train, cfg)
    tr_idx = torch.LongTensor(tr_idx_np)
    val_idx = torch.LongTensor(val_idx_np)
    X_tr, y_tr = X[tr_idx].to(device), y[tr_idx].to(device)
    X_val, y_val = X[val_idx].to(device), y[val_idx].to(device)
    sample_weights = None
    if cfg.sample_weights is not None:
        weights_np = np.asarray(cfg.sample_weights, dtype=float).reshape(-1)
        if len(weights_np) == len(X_train):
            weights_np = np.maximum(weights_np, 1e-9)
            sample_weights = weights_np[tr_idx_np]

    model = model.to(device)
    opt = _optimizer(model, cfg)
    loss_fn = _loss(cfg)

    loader = _make_loader(X_tr, y_tr, cfg, sample_weights=sample_weights)

    validation_metric = str(cfg.validation_metric or "mse").strip().lower()
    if validation_metric not in ("mse", "f1", "event_composite"):
        validation_metric = "mse"
    higher_is_better = validation_metric != "mse"
    history = {
        "train_loss": [],
        "val_loss": [],
        "val_score": [],
        "val_f1": [],
        "val_bal_acc": [],
        "epoch_times": [],
    }
    best_val = -float("inf") if higher_is_better else float("inf")
    best_state = None
    best_epoch = 0
    patience_left = cfg.early_stop_patience
    best_metric_detail = None

    for epoch in range(cfg.epochs):
        t0 = time.perf_counter()
        model.train()
        tr_losses = []
        for batch in loader:
            if len(batch) == 3:
                xb, yb, wb = batch
            else:
                xb, yb = batch
                wb = None
            opt.zero_grad()
            pred = model(xb)
            if wb is None:
                loss = loss_fn(pred, yb)
            else:
                loss = torch.mean((pred - yb) ** 2 * wb)
            loss.backward()
            opt.step()
            tr_losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = loss_fn(val_pred, y_val).item()
            val_pred_np = val_pred.detach().cpu().numpy().reshape(-1)
            y_val_np = y_val.detach().cpu().numpy().reshape(-1)

        metric_detail = None
        monitor_value = float(val_loss)
        if higher_is_better:
            metric_detail = _binary_validation_metrics(
                y_val_np, val_pred_np, cfg.validation_threshold, validation_metric
            )
            monitor_value = float(metric_detail["score"])

        history["train_loss"].append(float(np.mean(tr_losses)))
        history["val_loss"].append(val_loss)
        history["val_score"].append(float(monitor_value))
        history["val_f1"].append(float((metric_detail or {}).get("f1", 0.0)))
        history["val_bal_acc"].append(float((metric_detail or {}).get("bal_acc", 0.0)))
        history["epoch_times"].append(time.perf_counter() - t0)

        if cfg.verbose and (epoch % 20 == 0 or epoch == cfg.epochs - 1):
            msg = (f"  epoch {epoch:4d}  train={history['train_loss'][-1]:.4f}"
                   f"  val={val_loss:.4f}")
            if higher_is_better:
                msg += (f"  {validation_metric}={monitor_value:.4f}"
                        f" f1={history['val_f1'][-1]:.3f}"
                        f" bal={history['val_bal_acc'][-1]:.3f}")
            print(msg)

        # Early stopping
        if cfg.early_stop_patience > 0:
            improved = (
                monitor_value > best_val + 1e-6
                if higher_is_better
                else monitor_value < best_val - 1e-6
            )
            if improved:
                best_val = monitor_value
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                best_epoch = epoch + 1
                best_metric_detail = metric_detail
                patience_left = cfg.early_stop_patience
            else:
                patience_left -= 1
                if patience_left <= 0:
                    if best_state is not None:
                        model.load_state_dict(best_state)
                    history["stopped_at"] = epoch
                    break
        else:
            improved = (
                monitor_value > best_val + 1e-6
                if higher_is_better
                else monitor_value < best_val - 1e-6
            )
            if not improved:
                continue
            best_val = monitor_value
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            best_epoch = epoch + 1
            best_metric_detail = metric_detail

    if best_state is not None:
        model.load_state_dict(best_state)
    if best_epoch <= 0:
        best_epoch = max(1, len(history["train_loss"]))

    if cfg.final_retrain_full_train and best_epoch > 0:
        torch.manual_seed(cfg.seed)
        np.random.seed(cfg.seed)
        retrain_model = build_mlp(X.shape[1], y.shape[1], cfg).to(device)
        opt = _optimizer(retrain_model, cfg)
        loss_fn = _loss(cfg)
        full_weights = None
        if cfg.sample_weights is not None:
            full_weights = np.asarray(cfg.sample_weights, dtype=float).reshape(-1)
            if len(full_weights) != len(X_train):
                full_weights = None
        full_loader = _make_loader(X.to(device), y.to(device), cfg, sample_weights=full_weights)
        retrain_losses = []
        for _ in range(best_epoch):
            retrain_model.train()
            epoch_losses = []
            for batch in full_loader:
                if len(batch) == 3:
                    xb, yb, wb = batch
                else:
                    xb, yb = batch
                    wb = None
                opt.zero_grad()
                pred = retrain_model(xb)
                if wb is None:
                    loss = loss_fn(pred, yb)
                else:
                    loss = torch.mean((pred - yb) ** 2 * wb)
                loss.backward()
                opt.step()
                epoch_losses.append(loss.item())
            retrain_losses.append(float(np.mean(epoch_losses)))
        model = retrain_model
        history["retrain_info"] = {
            "strategy": "full_train_retrain",
            "best_epoch": int(best_epoch),
            "total_train_size": int(len(X_train)),
            "sample_weighting": bool(cfg.sample_weights is not None),
        }
        history["retrain_loss"] = retrain_losses
    else:
        history["retrain_info"] = {
            "strategy": "skipped",
            "best_epoch": int(best_epoch),
            "total_train_size": int(len(X_train)),
        }

    history["device"] = device
    history["n_params"] = count_params(model)
    history["validation_info"] = val_info
    history["sample_weighting"] = bool(cfg.sample_weights is not None)
    history["validation_metric"] = validation_metric
    history["validation_threshold"] = (
        None if cfg.validation_threshold is None else float(cfg.validation_threshold)
    )
    history["best_validation_score"] = float(best_val)
    if best_metric_detail is not None:
        history["best_validation_metrics"] = best_metric_detail
    history["best_epoch"] = int(best_epoch)
    return model, history


def predict_torch(model, X, device=None):
    if device is None:
        device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        Xt = torch.FloatTensor(X).to(device)
        pred = model(Xt).cpu().numpy().flatten()
    return pred


# ---------------------------------------------------------------------
# Wrappers con interfaccia fit/predict compatibile con benchmark.py
# ---------------------------------------------------------------------

class DeepNet:
    """MLP end-to-end. Input grezzo -> y.
    Baseline 'deep learning standard' vs feature banks."""
    def __init__(self, cfg: Optional[DeepConfig] = None):
        self.cfg = cfg or DeepConfig()
        self.model = None
        self.history = None
        self.x_mean_ = None
        self.x_std_ = None
        self.y_mean_ = 0.0
        self.y_std_ = 1.0
        self.target_scaled_ = True

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        self.x_mean_ = np.mean(X, axis=0)
        self.x_std_ = np.maximum(np.std(X, axis=0), 1e-8)
        bounded_binary_output = (
            str(self.cfg.output_activation).strip().lower() == "sigmoid"
            or str(self.cfg.loss).strip().lower()
            in {"binary_cross_entropy", "bce"}
        )
        self.target_scaled_ = not bounded_binary_output
        self.y_mean_ = float(np.mean(y)) if self.target_scaled_ else 0.0
        self.y_std_ = (
            float(max(np.std(y), 1e-8)) if self.target_scaled_ else 1.0
        )
        X_scaled = (X - self.x_mean_) / self.x_std_
        y_scaled = (y - self.y_mean_) / self.y_std_
        self.model = build_mlp(X_scaled.shape[1], 1, self.cfg)
        train_cfg = self.cfg
        if self.cfg.validation_threshold is not None:
            train_cfg = replace(
                self.cfg,
                validation_threshold=(
                    float(self.cfg.validation_threshold) - self.y_mean_
                ) / self.y_std_,
            )
        self.model, self.history = train_torch_model(self.model, X_scaled, y_scaled, train_cfg)
        if self.cfg.validation_threshold is not None:
            self.history["validation_threshold_raw"] = float(self.cfg.validation_threshold)
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        X_scaled = (X - self.x_mean_) / self.x_std_
        return predict_torch(self.model, X_scaled) * self.y_std_ + self.y_mean_

    @property
    def n_params(self):
        return count_params(self.model) if self.model else 0


class TorchMLPReadout:
    """MLP come readout sopra feature bank. Sostituisce sklearn MLPRegressor."""
    def __init__(self, cfg: Optional[DeepConfig] = None):
        self.cfg = cfg or DeepConfig()
        self.model = None
        self.history = None
        self.x_mean_ = None
        self.x_std_ = None

    def fit(self, Phi, y):
        Phi = np.asarray(Phi, dtype=float)
        if self.cfg.scale_features:
            self.x_mean_ = np.mean(Phi, axis=0)
            self.x_std_ = np.maximum(np.std(Phi, axis=0), 1e-8)
            Phi_fit = (Phi - self.x_mean_) / self.x_std_
        else:
            Phi_fit = Phi
        self.model = build_mlp(Phi_fit.shape[1], 1, self.cfg)
        self.model, self.history = train_torch_model(self.model, Phi_fit, y, self.cfg)
        return self

    def predict(self, Phi):
        Phi = np.asarray(Phi, dtype=float)
        if self.cfg.scale_features:
            Phi = (Phi - self.x_mean_) / self.x_std_
        return predict_torch(self.model, Phi)

    @property
    def n_params(self):
        return count_params(self.model) if self.model else 0

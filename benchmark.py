"""
Benchmark: feature banks + readout, con supporto DeepNet end-to-end in torch.
"""
import math
import time
import warnings
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from dataclasses import asdict, replace
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             precision_score, recall_score, f1_score,
                             balanced_accuracy_score)

from feature_banks import BANKS
from tasks import generate_dataset

try:
    from deep_nets import (DeepNet, TorchMLPReadout, DeepConfig,
                           DEEP_PRESETS, TORCH_AVAILABLE)
except ImportError:
    TORCH_AVAILABLE = False
    DEEP_PRESETS = {}

from lcs import UCSPredictor, LCSConfig, LCS_PRESETS

try:
    from kan_backend import (KANReadout, KANConfig, KAN_PRESETS, KAN_AVAILABLE,
                             serialize_kan_cfg)
except ImportError:
    KAN_AVAILABLE = False
    KAN_PRESETS = {}
    KANConfig = None
    KANReadout = None
    serialize_kan_cfg = lambda cfg: None


READOUTS = {
    "ridge":  lambda: Ridge(alpha=1.0),
    "linear": lambda: LinearRegression(),
    "mlp":    lambda: Pipeline([
        ("scaler", StandardScaler()),
        ("mlp", MLPRegressor(hidden_layer_sizes=(32,),
                             max_iter=_resolve_max_iter(500),
                             random_state=0,
                             early_stopping=False)),
    ]),
}

_RUNTIME_MAX_ITER = None
HYBRID_BANK = "__hybrid__"
KAN_BANK = "__kan__"
KAN_HYBRID_BANK = "__kan_hybrid__"


def configure_runtime_controls(max_iter=None):
    global _RUNTIME_MAX_ITER
    if max_iter is None:
        _RUNTIME_MAX_ITER = None
        return
    _RUNTIME_MAX_ITER = max(1, int(max_iter))


def _resolve_max_iter(default_value):
    if _RUNTIME_MAX_ITER is None:
        return int(default_value)
    return int(_RUNTIME_MAX_ITER)


def _resolve_deep_cfg_runtime(cfg):
    if cfg is None or _RUNTIME_MAX_ITER is None:
        return cfg
    return replace(cfg, epochs=int(_RUNTIME_MAX_ITER))


def _resolve_lcs_cfg_runtime(cfg):
    if cfg is None or _RUNTIME_MAX_ITER is None:
        return cfg
    return replace(cfg, epochs=int(_RUNTIME_MAX_ITER))


def _resolve_kan_cfg_runtime(cfg):
    if cfg is None or _RUNTIME_MAX_ITER is None:
        return cfg
    return replace(cfg, epochs=int(_RUNTIME_MAX_ITER))


def _resolve_n_jobs(n_jobs):
    try:
        value = int(n_jobs)
    except (TypeError, ValueError):
        value = 1
    if value <= 0:
        return max(1, os.cpu_count() or 1)
    return max(1, value)


def _bank_preprocessing_summary(bank_name):
    if bank_name in ("chebyshev", "morlet_wavelet"):
        bank_scaling = "minmax_to_minus1_plus1_fit_on_train"
    elif bank_name in ("random_fourier", "prime_fourier"):
        bank_scaling = "bounded_cosine_features_no_fitted_scaler"
    elif bank_name == "random_projection":
        bank_scaling = "bounded_tanh_projection_no_fitted_scaler"
    elif bank_name == "passthrough":
        bank_scaling = "raw_input_no_bank_scaler"
    else:
        bank_scaling = "bank_specific"
    return {
        "bank": bank_name,
        "bank_transform_scaling": bank_scaling,
    }


def _readout_preprocessing_summary(readout_name, readout=None):
    if readout_name == "mlp":
        return {
            "readout": readout_name,
            "readout_scaler": "StandardScaler_on_bank_features_fit_on_train",
        }
    if TORCH_AVAILABLE and isinstance(readout, TorchMLPReadout):
        return {
            "readout": readout_name,
            "readout_scaler": (
                "zscore_on_bank_features_fit_on_train"
                if bool(readout.cfg.scale_features)
                else "none"
            ),
        }
    if KAN_AVAILABLE and KANReadout is not None and isinstance(readout, KANReadout):
        return {
            "readout": readout_name,
            "readout_scaler": "zscore_then_tanh_on_bank_features_fit_on_train",
            "target_scaler": "zscore_on_y_fit_on_train",
            "kan_cfg": serialize_kan_cfg(readout.cfg),
        }
    return {
        "readout": readout_name,
        "readout_scaler": "none",
    }


def _bank_readout_preprocessing_summary(bank_name, readout_name, readout=None):
    summary = _bank_preprocessing_summary(bank_name)
    summary.update(_readout_preprocessing_summary(readout_name, readout=readout))
    return summary


def _serialize_deep_cfg(cfg):
    if cfg is None:
        return None
    return {k: v for k, v in asdict(cfg).items()
            if k not in ("context_datetimes", "sample_weights")}


def _serialize_lcs_cfg(cfg):
    if cfg is None:
        return None
    return {k: v for k, v in asdict(cfg).items() if k not in ("sample_weights",)}


def _serialize_kan_history(history):
    if not history:
        return {}
    out = {}
    for key, value in dict(history).items():
        arr = np.asarray(value)
        if arr.ndim == 0:
            try:
                out[key] = float(arr)
            except (TypeError, ValueError):
                out[key] = str(value)
            continue
        values = []
        for item in arr.reshape(-1).tolist():
            try:
                values.append(float(item))
            except (TypeError, ValueError):
                values.append(str(item))
        out[key] = values
    return out


def make_training_sample_weights(y_train, metric_profile=None, cfg=None):
    cfg = cfg or {}
    if not cfg.get("enabled", False):
        return None
    y = np.asarray(y_train, dtype=float).reshape(-1)
    n = len(y)
    if n <= 0:
        return None
    weights = np.ones(n, dtype=float)

    mode = str(cfg.get("recency_mode", "exp") or "none").lower()
    strength = max(0.0, float(cfg.get("recency_strength", 1.0) or 0.0))
    if mode != "none" and n > 1 and strength > 0:
        progress = np.linspace(0.0, 1.0, n)
        if mode == "linear":
            weights *= (1.0 + strength * progress)
        elif mode == "exp":
            weights *= np.exp(strength * progress)

    event_weight = cfg.get("event_weight", "auto")
    threshold = cfg.get("event_threshold")
    if threshold is None and metric_profile is not None:
        threshold = metric_profile.get("threshold")
    if threshold is not None and str(event_weight).strip().lower() != "none":
        positives = y >= float(threshold)
        pos = int(np.sum(positives))
        neg = int(n - pos)
        if pos > 0:
            if isinstance(event_weight, str) and event_weight.strip().lower() == "auto":
                boost = neg / max(pos, 1)
                boost = min(float(cfg.get("max_event_weight", 8.0) or 8.0), max(1.0, boost))
            else:
                boost = max(1.0, float(event_weight))
            weights[positives] *= boost

    weights = np.maximum(weights, 1e-9)
    weights /= max(float(np.mean(weights)), 1e-9)
    return weights


def _fit_readout(readout, X, y, sample_weights=None):
    if sample_weights is None:
        readout.fit(X, y)
        return
    sample_weights = np.asarray(sample_weights, dtype=float).reshape(-1)
    if len(sample_weights) != len(y):
        readout.fit(X, y)
        return
    if isinstance(readout, Pipeline):
        last_name = list(readout.named_steps.keys())[-1]
        try:
            readout.fit(X, y, **{f"{last_name}__sample_weight": sample_weights})
            return
        except (TypeError, ValueError):
            pass
        readout.fit(X, y)
        return
    try:
        readout.fit(X, y, sample_weight=sample_weights)
        return
    except (TypeError, ValueError):
        pass
    readout.fit(X, y)


def _fit_lcs_model(lcs_cfg, X_train, y_train, seed=0, metric_profile=None,
                   training_weight_cfg=None, context_datetimes_train=None):
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    cfg = replace(
        _resolve_lcs_cfg_runtime(lcs_cfg),
        seed=int(seed) + int(lcs_cfg.seed),
        sample_weights=None if sample_weights is None else sample_weights.tolist(),
    )
    predictor = UCSPredictor(cfg=cfg)
    t0 = time.perf_counter()
    predictor.fit(X_train, y_train, context_datetimes=context_datetimes_train)
    train_time = time.perf_counter() - t0
    return predictor, cfg, sample_weights, train_time


def _fit_kan_model(kan_cfg, X_train, y_train, seed=0, metric_profile=None,
                   training_weight_cfg=None):
    if not KAN_AVAILABLE:
        raise RuntimeError("KAN non disponibile: installa pykan nella venv")
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    cfg = replace(
        _resolve_kan_cfg_runtime(kan_cfg),
        seed=int(seed) + int(kan_cfg.seed),
        scale_features=True,
    )
    model = KANReadout(cfg=cfg)
    t0 = time.perf_counter()
    model.fit(X_train, y_train, sample_weight=sample_weights)
    train_time = time.perf_counter() - t0
    return model, cfg, sample_weights, train_time


def _fit_partner_model(partner_spec, X_train, y_train, seed=0, metric_profile=None,
                       training_weight_cfg=None, deep_preset_cfgs=None,
                       custom_deep_cfg=None, context_datetimes_train=None,
                       external_test_size=None):
    t0 = time.perf_counter()
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    kind = str(partner_spec.get("kind", "bank")).lower()
    if kind == "deep":
        if not TORCH_AVAILABLE:
            raise RuntimeError("torch non disponibile")
        preset = partner_spec.get("preset")
        if preset == "custom":
            cfg = custom_deep_cfg
        else:
            deep_preset_cfgs = deep_preset_cfgs or {}
            cfg = deep_preset_cfgs.get(preset, DEEP_PRESETS.get(preset))
        if cfg is None:
            raise ValueError(f"Config deep non disponibile per hybrid partner {preset}")
        cfg = _inject_train_context_cfg(
            cfg, tr_idx=np.arange(len(X_train)),
            te_idx=np.arange(int(external_test_size or 0)),
            context_datetimes=context_datetimes_train,
            scale_features=True,
        )
        cfg = replace(
            _resolve_deep_cfg_runtime(cfg), seed=int(seed), scale_features=True,
            sample_weights=None if sample_weights is None else sample_weights.tolist(),
        )
        model = DeepNet(cfg=cfg)
        model.fit(X_train, y_train)
        return {
            "kind": "deep",
            "model": model,
            "n_params": int(model.n_params),
            "sample_weights": sample_weights,
            "deep_cfg": cfg,
            "preprocessing": {
                "kind": "deep",
                "input_scaler": "zscore_on_raw_X_fit_on_train",
                "target_scaler": "zscore_on_y_fit_on_train",
            },
            "train_time_s": float(time.perf_counter() - t0),
        }

    bank_name = partner_spec.get("bank")
    readout_name = partner_spec.get("readout")
    if not bank_name or not readout_name:
        raise ValueError(
            "Hybrid partner incompleto: attesi campi 'bank' e 'readout', "
            f"ricevuto {partner_spec!r}"
        )
    bank = BANKS[bank_name](seed)
    bank.fit(X_train)
    Phi_train = bank.transform(X_train)
    readout = READOUTS[readout_name]()
    if TORCH_AVAILABLE and isinstance(readout, TorchMLPReadout):
        readout.cfg = _inject_train_context_cfg(
            _resolve_deep_cfg_runtime(readout.cfg),
            tr_idx=np.arange(len(X_train)),
            te_idx=np.arange(int(external_test_size or 0)),
            context_datetimes=context_datetimes_train,
            scale_features=False,
        )
        readout.cfg = replace(
            readout.cfg,
            sample_weights=None if sample_weights is None else sample_weights.tolist(),
        )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning,
                                module=r"sklearn\.neural_network\._multilayer_perceptron")
        _fit_readout(readout, Phi_train, y_train, sample_weights=sample_weights)
    return {
        "kind": "bank",
        "bank": bank,
        "readout": readout,
        "phi_dim": int(bank.n_output_features),
        "n_params": int(_get_n_params(readout, bank.n_output_features)),
        "sample_weights": sample_weights,
        "preprocessing": _bank_readout_preprocessing_summary(
            bank_name, readout_name, readout=readout
        ),
        "train_time_s": float(time.perf_counter() - t0),
    }


def _predict_partner_model(partner_model, X):
    if partner_model["kind"] == "deep":
        return np.asarray(partner_model["model"].predict(X), dtype=float)
    Phi = partner_model["bank"].transform(X)
    return np.asarray(partner_model["readout"].predict(Phi), dtype=float)


def _hybrid_readout_label(lcs_label, partner_spec, mode, alpha):
    bank_alias = {
        "passthrough": "pt",
        "random_projection": "rp",
        "morlet_wavelet": "mw",
    }
    lcs_short = str(lcs_label).replace("ucs_", "")
    if lcs_short == "custom":
        lcs_short = "cus"
    if partner_spec.get("kind") == "deep":
        partner = f"dn{partner_spec.get('preset')}"
    else:
        bank = bank_alias.get(partner_spec.get("bank"), partner_spec.get("bank"))
        readout = str(partner_spec.get("readout", ""))
        readout_alias = {"ridge": "r", "linear": "lin"}.get(readout, readout[:3])
        partner = f"{bank}{readout_alias}"
    mode = str(mode).lower()
    if mode == "weighted":
        return f"hyb_{lcs_short}_{partner}_w{float(alpha):.2f}".replace(".", "p")
    mode_alias = {"and": "and", "or": "or"}.get(mode, mode[:3])
    return f"hyb_{lcs_short}_{partner}_{mode_alias}"


def _kan_hybrid_readout_label(kan_label, partner_spec, mode, alpha):
    bank_alias = {
        "passthrough": "pt",
        "random_projection": "rp",
        "morlet_wavelet": "mw",
    }
    kan_short = str(kan_label).replace("kan_", "")
    if partner_spec.get("kind") == "deep":
        partner = f"dn{partner_spec.get('preset')}"
    else:
        bank = bank_alias.get(partner_spec.get("bank"), partner_spec.get("bank"))
        readout = str(partner_spec.get("readout", ""))
        readout_alias = {"ridge": "r", "linear": "lin"}.get(readout, readout[:3])
        partner = f"{bank}{readout_alias}"
    mode = str(mode).lower()
    if mode == "weighted":
        return f"khyb_{kan_short}_{partner}_w{float(alpha):.2f}".replace(".", "p")
    mode_alias = {"and": "and", "or": "or"}.get(mode, mode[:3])
    return f"khyb_{kan_short}_{partner}_{mode_alias}"


def _partner_cache_key(partner_spec):
    kind = str(partner_spec.get("kind", "bank")).lower()
    if kind == "deep":
        return ("deep", str(partner_spec.get("preset", "")))
    return (
        "bank",
        str(partner_spec.get("bank", "")),
        str(partner_spec.get("readout", "")),
    )


def _lcs_cfg_items(lcs_presets, custom_lcs_cfg, lcs_preset_cfgs):
    items = []
    for preset in lcs_presets or []:
        cfg = (lcs_preset_cfgs or {}).get(preset, LCS_PRESETS.get(preset))
        if cfg is not None:
            items.append((f"ucs_{preset}", cfg))
    if custom_lcs_cfg is not None:
        items.append(("ucs_custom", custom_lcs_cfg))
    return items


def _kan_cfg_items(kan_presets, kan_preset_cfgs):
    items = []
    for preset in kan_presets or []:
        cfg = (kan_preset_cfgs or {}).get(preset, KAN_PRESETS.get(preset))
        if cfg is not None:
            items.append((f"kan_{preset}", cfg))
    return items


def _trial_allowed(trial_filter, kind, *, bank=None, readout=None,
                   preset=None, lcs_label=None, hybrid_readout=None):
    if not trial_filter:
        return True
    if kind == "bank":
        allowed = trial_filter.get("bank_readouts")
        return allowed is None or (bank, readout) in allowed
    if kind == "deep":
        allowed = trial_filter.get("deep_labels")
        label = "deepnet_custom" if preset == "custom" else f"deepnet_{preset}"
        return allowed is None or label in allowed
    if kind == "lcs":
        allowed = trial_filter.get("lcs_labels")
        return allowed is None or lcs_label in allowed
    if kind == "kan":
        allowed = trial_filter.get("kan_labels")
        return allowed is None or preset in allowed
    if kind == "hybrid":
        allowed = trial_filter.get("hybrid_readouts")
        return allowed is None or hybrid_readout in allowed
    if kind == "kan_hybrid":
        allowed = trial_filter.get("kan_hybrid_readouts")
        return allowed is None or hybrid_readout in allowed
    return True


def _trial_count(banks, readouts, deep_presets, custom_deep_cfg,
                 lcs_items, hybrid_specs, trial_filter=None,
                 kan_items=None, kan_hybrid_specs=None):
    grid = sum(
        1 for bn in banks for rn in readouts
        if _trial_allowed(trial_filter, "bank", bank=bn, readout=rn)
    )
    deep_count = sum(
        1 for preset in deep_presets
        if _trial_allowed(trial_filter, "deep", preset=preset)
    )
    if custom_deep_cfg is not None and _trial_allowed(
        trial_filter, "deep", preset="custom"
    ):
        deep_count += 1
    lcs_count = sum(
        1 for lcs_label, _ in lcs_items
        if _trial_allowed(trial_filter, "lcs", lcs_label=lcs_label)
    )
    kan_items = kan_items or []
    kan_count = sum(
        1 for kan_label, _ in kan_items
        if _trial_allowed(trial_filter, "kan", preset=kan_label)
    )
    hybrid_count = 0
    for lcs_label, _ in lcs_items:
        for spec in hybrid_specs:
            readout = _hybrid_readout_label(
                lcs_label,
                spec.get("partner", {}),
                spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if _trial_allowed(trial_filter, "hybrid", hybrid_readout=readout):
                hybrid_count += 1
    kan_hybrid_count = 0
    for kan_label, _ in kan_items:
        for spec in kan_hybrid_specs or []:
            readout = _kan_hybrid_readout_label(
                kan_label,
                spec.get("partner", {}),
                spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if _trial_allowed(trial_filter, "kan_hybrid", hybrid_readout=readout):
                kan_hybrid_count += 1
    return grid + deep_count + lcs_count + hybrid_count + kan_count + kan_hybrid_count


def _binarize_lcs_target(y, cfg):
    return (np.asarray(y, dtype=float).reshape(-1) >= float(cfg.binary_threshold)).astype(int)


def _lcs_metric_profile(metric_profile):
    if metric_profile is None:
        return None
    profile = dict(metric_profile)
    profile["kind"] = "event"
    profile["threshold"] = 0.5
    profile["prediction_threshold"] = 0.5
    profile["positive_scale"] = 1.0
    profile["score_label"] = f"event_{profile.get('score_mode', 'isolation')}"
    return profile


def _event_threshold(metric_profile, fallback=0.5):
    if metric_profile is not None and metric_profile.get("threshold") is not None:
        return float(metric_profile["threshold"])
    return float(fallback)


def _partner_event_score(y_pred, threshold):
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    threshold = float(threshold)
    if threshold <= 0:
        return (y_pred > 0).astype(float)
    return np.clip(y_pred / max(threshold, 1e-12), 0.0, 1.0)


def _combine_hybrid_predictions(lcs_pred, partner_pred, mode, alpha,
                                event_threshold, hybrid_threshold=0.5):
    lcs_evt = np.asarray(lcs_pred, dtype=int).reshape(-1)
    partner_pred = np.asarray(partner_pred, dtype=float).reshape(-1)
    partner_evt = partner_pred >= float(event_threshold)
    mode = str(mode or "and").strip().lower()
    if mode == "or":
        return np.asarray((lcs_evt == 1) | partner_evt, dtype=int)
    if mode == "weighted":
        partner_score = _partner_event_score(partner_pred, event_threshold)
        score = float(alpha) * lcs_evt.astype(float) + (1.0 - float(alpha)) * partner_score
        return np.asarray(score >= float(hybrid_threshold), dtype=int)
    return np.asarray((lcs_evt == 1) & partner_evt, dtype=int)


def _inject_train_context_cfg(cfg, tr_idx=None, te_idx=None, context_datetimes=None,
                              scale_features=None):
    if cfg is None:
        return None
    updates = {}
    if context_datetimes is not None and tr_idx is not None:
        updates["context_datetimes"] = [context_datetimes[int(i)] for i in tr_idx]
    if te_idx is not None:
        updates["external_test_size"] = int(len(te_idx))
    if scale_features is not None:
        updates["scale_features"] = bool(scale_features)
    if not updates:
        return cfg
    return replace(cfg, **updates)

# Readout torch auto-registrati per ogni preset
if TORCH_AVAILABLE:
    def _make_torch_readout_factory(cfg):
        return lambda: TorchMLPReadout(cfg=replace(_resolve_deep_cfg_runtime(cfg),
                                                   scale_features=False))
    for _name, _cfg in DEEP_PRESETS.items():
        READOUTS[f"torch_{_name}"] = _make_torch_readout_factory(_cfg)

# Readout KAN auto-registrati per ogni preset disponibile.
if KAN_AVAILABLE:
    def _make_kan_readout_factory(cfg):
        return lambda: KANReadout(cfg=_resolve_kan_cfg_runtime(cfg))
    for _name, _cfg in KAN_PRESETS.items():
        READOUTS[f"kan_{_name}"] = _make_kan_readout_factory(_cfg)


def compute_overall_kpi(mse_test, inference_time_us, n_params,
                        weights=None, mse_ref=1.0):
    s_mse = 1.0 / (1.0 + mse_test / max(mse_ref, 1e-9))
    return float(s_mse)


def resolve_metric_profile(y_ref, mode="auto", threshold=None,
                           prediction_threshold=None,
                           score_mode="isolation"):
    y = np.asarray(y_ref, dtype=float).reshape(-1)
    detected_event = _detect_event_target(y)
    selected_mode = mode
    if mode == "auto":
        selected_mode = "event" if detected_event else "regression"

    if selected_mode == "event":
        if threshold is None:
            positive = y[y > 0]
            if positive.size > 0:
                threshold = max(float(np.min(positive)) * 0.5, 1e-12)
            else:
                threshold = 0.5
        positives = y[y >= threshold]
        positive_scale = float(np.mean(np.abs(positives))) if positives.size > 0 else 1.0
        positive_scale = max(positive_scale, 1e-9)
        pred_threshold = threshold if prediction_threshold is None else float(prediction_threshold)
        return {
            "kind": "event",
            "threshold": float(threshold),
            "prediction_threshold": float(pred_threshold),
            "positive_scale": positive_scale,
            "score_mode": str(score_mode or "isolation"),
            "score_label": f"event_{str(score_mode or 'isolation')}",
        }

    return {
        "kind": "regression",
        "threshold": None,
        "positive_scale": None,
        "score_label": "regression_composite",
    }


_SHAPE_WEIGHT_DEFAULT = 0.6


def configure_shape_weight(value):
    """Imposta il peso globale di shape_overall nello scoring (0..1)."""
    global _SHAPE_WEIGHT_DEFAULT
    try:
        v = float(value)
    except (TypeError, ValueError):
        return
    _SHAPE_WEIGHT_DEFAULT = max(0.0, min(1.0, v))


def compute_overall_score(result, metric_profile, mse_ref=1.0, weights=None,
                          shape_weight=None):
    if shape_weight is None:
        shape_weight = _SHAPE_WEIGHT_DEFAULT
    extra = result.get("extra", {})
    s_shape = float(extra.get("shape_overall", 0.0))
    if metric_profile["kind"] == "event":
        s_f1 = float(extra.get("event_f1", 0.0))
        s_bal = float(extra.get("event_bal_acc", 0.0))
        s_rec = float(extra.get("event_recall", 0.0))
        s_prec = float(extra.get("event_precision", 0.0))
        s_spec = float(extra.get("event_specificity", 0.0))
        pos_mae = extra.get("positive_mae")
        pos_scale = max(float(metric_profile.get("positive_scale") or 1.0), 1e-9)
        s_pos = 0.0 if pos_mae is None else 1.0 / (1.0 + float(pos_mae) / pos_scale)
        components = {
            "f1": s_f1,
            "bal_acc": s_bal,
            "precision": s_prec,
            "recall": s_rec,
            "specificity": s_spec,
            "pos_fit": s_pos,
            "shape_overall": s_shape,
            "peak_score": float(extra.get("peak_score", 0.0)),
            "depression_score": float(extra.get("depression_score", 0.0)),
        }
        score_mode = str(metric_profile.get("score_mode", "isolation") or "isolation").lower()
        if score_mode in ("legacy", "additive"):
            base = (
                0.50 * s_f1
                + 0.20 * s_bal
                + 0.15 * s_rec
                + 0.15 * s_pos
            )
        else:
            base = (
                0.35 * s_f1
                + 0.15 * s_bal
                + 0.15 * s_prec
                + 0.15 * s_rec
                + 0.10 * s_spec
                + 0.10 * s_pos
            )
        sw = max(0.0, min(1.0, float(shape_weight)))
        legacy_score = (1.0 - sw) * base + sw * s_shape
        components["base_event"] = float(base)
        components["shape_weight"] = sw

        # Readability-aware composite (event mode):
        # rw=0    -> legacy_score  (back-compat, default)
        # rw>0    -> (1-rw) * legacy_score + rw * readability
        # readability = mean(quiet_fidelity, peak_separation_score) gia' in extra
        rw = max(0.0, min(0.95, float(metric_profile.get("readability_weight", 0.0) or 0.0)))
        floor = max(0.0, min(1.0, float(metric_profile.get("readability_floor", 0.0) or 0.0)))
        s_readability = float(extra.get("readability", 0.0) or 0.0)
        components["readability"] = s_readability
        components["readability_weight"] = rw
        if rw > 0.0:
            score = (1.0 - rw) * legacy_score + rw * s_readability
        else:
            score = legacy_score
        # Floor: penalita' soft sui modelli illeggibili (alarm-curve inutilizzabile)
        if floor > 0.0 and s_readability < floor:
            penalty = max(0.0, s_readability / floor)
            score = float(score) * penalty
            components["readability_floor"] = floor
            components["readability_floor_penalty"] = penalty
        return float(score), components

    fit_score = compute_overall_kpi(
        result["mse_test"], result["inference_time_us"], result["n_effective_params"],
        weights=weights, mse_ref=mse_ref,
    )
    r2_score_norm = max(0.0, min(1.0, (float(result["r2"]) + 1.0) / 2.0))
    base = 0.85 * fit_score + 0.15 * r2_score_norm
    sw = max(0.0, min(1.0, float(shape_weight)))
    score = (1.0 - sw) * base + sw * s_shape
    components = {
        "fit": fit_score,
        "r2": r2_score_norm,
        "shape_overall": s_shape,
        "peak_score": float(extra.get("peak_score", 0.0)),
        "depression_score": float(extra.get("depression_score", 0.0)),
        "base_regression": float(base),
        "shape_weight": sw,
    }
    return float(score), components


def _get_n_params(readout, phi_dim):
    if hasattr(readout, "n_params"):
        return readout.n_params
    if isinstance(readout, Pipeline):
        readout = readout.named_steps.get("mlp", readout)
    if isinstance(readout, MLPRegressor):
        total = 0
        sizes = [phi_dim] + list(readout.hidden_layer_sizes) + [1]
        for a, b in zip(sizes[:-1], sizes[1:]):
            total += a * b + b
        return total
    return phi_dim + 1


def _detect_event_target(y):
    y = np.asarray(y, dtype=float)
    if y.size == 0:
        return False
    uniq = np.unique(y)
    if len(uniq) <= 2 and set(np.round(uniq, 12)).issubset({0.0, 1.0}):
        return True
    zero_frac = float(np.mean(np.isclose(y, 0.0)))
    return zero_frac >= 0.8 and np.all(y >= 0.0) and np.any(y > 0.0)


def detect_topological_peaks(y, threshold=None):
    """Picchi topologici: ogni sequenza salita -> top (1+ punti, flat ammesso) -> discesa.

    Bordi: primo/ultimo punto, se sopra threshold, agiscono da "low virtuale" e completano
    un picco al bordo. Threshold opzionale: se passato, il top deve essere >= threshold.

    Ritorna lista di dict {start, end, top_idx, top_value}.
    """
    y = [float(v) for v in y]
    n = len(y)
    if n == 0:
        return []
    peaks = []
    i = 0
    while i < n:
        if i == 0:
            is_rise_start = (threshold is None) or (y[0] >= threshold)
        else:
            is_rise_start = y[i] > y[i - 1]
        if not is_rise_start:
            i += 1
            continue
        peak_start = i
        j = i
        top_value = y[j]
        top_idx = j
        while j + 1 < n and y[j + 1] >= y[j]:
            j += 1
            if y[j] > top_value:
                top_value = y[j]
                top_idx = j
        if j + 1 < n and y[j + 1] < y[j]:
            if threshold is None or top_value >= threshold:
                peaks.append({"start": peak_start, "end": j,
                              "top_idx": top_idx, "top_value": top_value})
            i = j + 1
        elif j + 1 == n:
            if threshold is None or top_value >= threshold:
                peaks.append({"start": peak_start, "end": j,
                              "top_idx": top_idx, "top_value": top_value})
            break
        else:
            i = j + 1
    return peaks


def _flip_series(y):
    arr = np.asarray(y, dtype=float)
    if arr.size == 0:
        return arr, 0.0, 0.0
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    flipped = (vmax + vmin) - arr
    return flipped, vmin, vmax


def _match_peaks_by_containment(real_peaks, pred_peaks):
    """Un picco reale e' matched se il suo top_idx cade nello span [start,end] di un
    picco previsto. Il picco previsto puo' essere piu' largo del reale: contano i margini.
    Ritorna (matched_pairs, matched_real_count, sync_offsets).
    """
    pairs = []
    used_pred = set()
    for real in real_peaks:
        rt = real["top_idx"]
        for k, pred in enumerate(pred_peaks):
            if k in used_pred:
                continue
            if pred["start"] <= rt <= pred["end"]:
                offset = abs(rt - pred["top_idx"])
                pairs.append((real, pred, offset))
                used_pred.add(k)
                break
    matched = len(pairs)
    sync_offsets = [p[2] for p in pairs]
    return pairs, matched, sync_offsets


def _shape_score_side(real_peaks, pred_peaks):
    """peaks_score = recall * count_ratio (penalizza over-prediction)."""
    n_real = len(real_peaks)
    n_pred = len(pred_peaks)
    if n_real == 0 and n_pred == 0:
        return 1.0, {"actual": 0, "pred": 0, "matched": 0,
                     "recall": 1.0, "precision": 1.0, "count_ratio": 1.0,
                     "sync_mean": 0.0, "sync_max": 0.0}
    if n_real == 0:
        return 0.0, {"actual": 0, "pred": n_pred, "matched": 0,
                     "recall": 0.0, "precision": 0.0, "count_ratio": 0.0,
                     "sync_mean": 0.0, "sync_max": 0.0}
    _, matched, offsets = _match_peaks_by_containment(real_peaks, pred_peaks)
    recall = matched / n_real
    precision = matched / n_pred if n_pred > 0 else 0.0
    count_ratio = (min(n_real, n_pred) / max(n_real, n_pred)) if n_pred > 0 else 0.0
    sync_mean = float(np.mean(offsets)) if offsets else 0.0
    sync_max = float(np.max(offsets)) if offsets else 0.0
    score = recall * count_ratio
    return float(score), {
        "actual": int(n_real),
        "pred": int(n_pred),
        "matched": int(matched),
        "recall": float(recall),
        "precision": float(precision),
        "count_ratio": float(count_ratio),
        "sync_mean": sync_mean,
        "sync_max": sync_max,
    }


def compute_shape_metrics(y_true, y_pred, threshold=None):
    """Metriche shape: picchi topologici + depressioni (su serie flippata).
    Ritorna dict con dettagli di picchi/depressioni e shape_overall (50/50)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    real_peaks = detect_topological_peaks(y_true, threshold=threshold)
    pred_peaks = detect_topological_peaks(y_pred, threshold=threshold)
    peak_score, peak_info = _shape_score_side(real_peaks, pred_peaks)

    y_true_flip, true_min, true_max = _flip_series(y_true)
    y_pred_flip, pred_min, pred_max = _flip_series(y_pred)
    if threshold is not None:
        depr_thr_true = (true_max + true_min) - float(threshold)
        depr_thr_pred = (pred_max + pred_min) - float(threshold)
    else:
        depr_thr_true = None
        depr_thr_pred = None
    real_deps = detect_topological_peaks(y_true_flip, threshold=depr_thr_true)
    pred_deps = detect_topological_peaks(y_pred_flip, threshold=depr_thr_pred)
    depr_score, depr_info = _shape_score_side(real_deps, pred_deps)

    shape_overall = 0.5 * peak_score + 0.5 * depr_score
    return {
        "shape_overall": float(shape_overall),
        "peak_score": float(peak_score),
        "depression_score": float(depr_score),
        "peaks": peak_info,
        "depressions": depr_info,
    }


def compute_quiet_fidelity(y_true, y_pred, threshold, pred_threshold):
    """Quanto e' silenzioso il modello quando l'attuale e' silenzioso.

    Misura il livello del segnale predetto dove l'attuale non ha eventi.
    Idealmente: quando actual < threshold, |pred| dovrebbe essere ~0 e
    comunque MOLTO sotto pred_threshold (la soglia di allarme).

    Ritorna [0, 1]:
      1.0 = pred completamente silenzioso nelle zone calme (modello leggibile)
      0.0 = pred sopra la soglia di allarme nelle zone calme (modello che
            "alza la voce sempre" -> illeggibile come allerta)
    None se non ci sono zone calme.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.size == 0 or yp.size == 0:
        return None
    is_quiet = yt < float(threshold)
    if not np.any(is_quiet):
        return 1.0
    pred_in_quiet = np.abs(yp[is_quiet])
    if pred_in_quiet.size == 0:
        return 1.0
    pred_thr_pos = max(float(pred_threshold), 1e-6)
    noise_floor = float(np.mean(pred_in_quiet) / pred_thr_pos)
    return float(max(0.0, 1.0 - min(1.0, noise_floor)))


def compute_peak_baseline_separation(y_true, y_pred, threshold):
    """Quanto i picchi predetti svettano sopra il fondo.

    Calcola il rapporto tra |pred| medio nelle zone-evento (actual >= thr)
    e |pred| medio nelle zone-calme. Restituisce (ratio, score):
      - ratio: rapporto grezzo (utile per il CSV, da 1 a +inf)
      - score in [0, 1]: log10(ratio) saturato a 1 quando ratio>=10.
    Ritorna (None, None) se mancano sia eventi sia calme.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.size == 0 or yp.size == 0:
        return None, None
    is_peak = yt >= float(threshold)
    is_quiet = ~is_peak
    if not np.any(is_peak) or not np.any(is_quiet):
        return None, None
    mean_peak = float(np.mean(np.abs(yp[is_peak])))
    mean_quiet = float(np.mean(np.abs(yp[is_quiet])))
    ratio = mean_peak / max(mean_quiet, 1e-6)
    if ratio <= 1.0:
        score = 0.0
    else:
        score = min(1.0, math.log10(ratio) / math.log10(10.0))
    return float(ratio), float(score)


def _extra_metrics(y_true, y_pred, metric_profile=None):
    extra = {
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }

    if metric_profile and metric_profile["kind"] == "event":
        thr = float(metric_profile["threshold"])
        pred_thr = float(metric_profile.get("prediction_threshold", thr))
        y_true_evt = np.asarray(y_true) >= thr
        y_pred_evt = np.asarray(y_pred) >= pred_thr
        tp = int(np.sum(y_true_evt & y_pred_evt))
        tn = int(np.sum(~y_true_evt & ~y_pred_evt))
        fp = int(np.sum(~y_true_evt & y_pred_evt))
        fn = int(np.sum(y_true_evt & ~y_pred_evt))
        specificity = tn / max(tn + fp, 1)
        extra.update({
            "event_precision": float(precision_score(y_true_evt, y_pred_evt, zero_division=0)),
            "event_recall": float(recall_score(y_true_evt, y_pred_evt, zero_division=0)),
            "event_f1": float(f1_score(y_true_evt, y_pred_evt, zero_division=0)),
            "event_bal_acc": float(balanced_accuracy_score(y_true_evt, y_pred_evt)),
            "event_specificity": float(specificity),
            "event_tp": tp,
            "event_tn": tn,
            "event_fp": fp,
            "event_fn": fn,
            "target_mode": "event",
            "event_threshold": thr,
            "event_prediction_threshold": pred_thr,
        })
        if np.any(y_true_evt):
            extra["positive_mae"] = float(mean_absolute_error(
                np.asarray(y_true)[y_true_evt], np.asarray(y_pred)[y_true_evt]
            ))
        shape = compute_shape_metrics(y_true, y_pred, threshold=thr)
        extra["shape_overall"] = shape["shape_overall"]
        extra["peak_score"] = shape["peak_score"]
        extra["depression_score"] = shape["depression_score"]
        extra["peaks_info"] = shape["peaks"]
        extra["depressions_info"] = shape["depressions"]

        # Readability metrics: quanto la curva predetta e' usabile come
        # allerta visiva. Sempre calcolate e salvate, anche se readability_weight=0.
        qf = compute_quiet_fidelity(y_true, y_pred, thr, pred_thr)
        sep_ratio, sep_score = compute_peak_baseline_separation(y_true, y_pred, thr)
        if qf is not None:
            extra["quiet_fidelity"] = float(qf)
        if sep_ratio is not None:
            extra["peak_baseline_ratio"] = float(sep_ratio)
        if sep_score is not None:
            extra["peak_separation_score"] = float(sep_score)
        components_for_readability = [v for v in (qf, sep_score) if v is not None]
        if components_for_readability:
            extra["readability"] = float(
                sum(components_for_readability) / len(components_for_readability)
            )
    else:
        extra["target_mode"] = "regression"
        shape = compute_shape_metrics(y_true, y_pred, threshold=None)
        extra["shape_overall"] = shape["shape_overall"]
        extra["peak_score"] = shape["peak_score"]
        extra["depression_score"] = shape["depression_score"]
        extra["peaks_info"] = shape["peaks"]
        extra["depressions_info"] = shape["depressions"]

    return extra


def _build_stratify_labels(y):
    if not _detect_event_target(y):
        return None
    labels = (np.asarray(y, dtype=float) > 0).astype(int)
    counts = np.bincount(labels, minlength=2)
    if np.min(counts) < 2:
        return None
    return labels


def _context_datetimes_monotonic(context_datetimes):
    if context_datetimes is None:
        return False
    values = [dt for dt in context_datetimes if dt is not None]
    if len(values) < 2:
        return False
    return all(values[i] <= values[i + 1] for i in range(len(values) - 1))


def _resolve_time_series_enabled(window_cfg, context_datetimes=None):
    mode = str((window_cfg or {}).get("time_series", "auto")).strip().lower()
    if mode == "on":
        return True
    if mode == "off":
        return False
    return _context_datetimes_monotonic(context_datetimes)


def _format_index_span(indices):
    indices = np.sort(np.asarray(indices, dtype=int))
    if indices.size == 0:
        return "n/a"
    return f"{int(indices[0])}..{int(indices[-1])}"


def enforce_train_before_test(train_idx, test_idx, *, window_cfg=None,
                              context_datetimes=None, split_info=None,
                              warning_label="Train window"):
    train_idx = np.sort(np.asarray(train_idx, dtype=int))
    test_idx = np.sort(np.asarray(test_idx, dtype=int))
    info = dict(split_info or {})

    time_series_mode = str((window_cfg or {}).get("time_series", "auto")).strip().lower()
    if time_series_mode not in {"auto", "on", "off"}:
        raise ValueError("--time-series deve essere auto, on oppure off")
    allow_after_test = bool((window_cfg or {}).get("allow_train_after_test", False))
    time_series_enabled = _resolve_time_series_enabled(window_cfg, context_datetimes=context_datetimes)

    info["time_series_mode"] = time_series_mode
    info["time_series_enabled"] = bool(time_series_enabled)
    info["allow_train_after_test"] = bool(allow_after_test)
    info["train_after_test_dropped"] = 0
    info["train_after_test_warning"] = None

    if train_idx.size == 0 or test_idx.size == 0 or not time_series_enabled:
        return train_idx, info

    test_start = int(np.min(test_idx))
    after_test_idx = train_idx[train_idx >= test_start]
    if after_test_idx.size == 0:
        return train_idx, info

    info["train_after_test_count"] = int(after_test_idx.size)
    info["train_after_test_range"] = _format_index_span(after_test_idx)
    if allow_after_test:
        message = (
            "[time-series warning] --allow-train-after-test attivo. "
            f"{warning_label} contiene {int(after_test_idx.size)} righe DOPO il test window "
            f"(indici {_format_index_span(after_test_idx)}). Questo e' leak temporale se il "
            "fenomeno ha memoria. Assicurati che il dataset sia genuinamente IID."
        )
        print(message)
        info["train_after_test_warning"] = "allowed"
        return train_idx, info

    clipped_train_idx = train_idx[train_idx < test_start]
    message = (
        f"[time-series warning] {warning_label} conteneva {int(after_test_idx.size)} righe "
        f"dopo il test window (indici {_format_index_span(after_test_idx)}). "
        "Autoclip attivo: droppate. Per disattivare, usa --allow-train-after-test."
    )
    print(message)
    info["train_after_test_dropped"] = int(after_test_idx.size)
    info["train_after_test_warning"] = "autoclipped"
    return clipped_train_idx, info


def _build_isolated_event_indices(event_positions, pre, post, n):
    """Union of micro-windows [ev-pre .. ev+post] for each event position."""
    pieces = []
    for ev in event_positions:
        lo = max(0, int(ev) - pre)
        hi = min(n - 1, int(ev) + post)
        if lo <= hi:
            pieces.append(np.arange(lo, hi + 1, dtype=int))
    if not pieces:
        return np.asarray([], dtype=int)
    return np.unique(np.concatenate(pieces))


def _build_random_negative_indices(
    y,
    threshold,
    selected_events,
    existing_test_idx,
    count,
    seed,
    n,
):
    """Sample quiet rows between selected events and add them to validation."""
    count = max(0, int(count or 0))
    if count <= 0 or selected_events.size < 2:
        return np.asarray([], dtype=int)

    selected_events = np.sort(np.asarray(selected_events, dtype=int))
    lo = int(selected_events[0])
    hi = int(selected_events[-1])
    if hi <= lo:
        return np.asarray([], dtype=int)

    y_arr = np.asarray(y, dtype=float).reshape(-1)
    existing = set(int(i) for i in np.asarray(existing_test_idx, dtype=int).reshape(-1))
    candidates = [
        i for i in range(max(0, lo + 1), min(n - 1, hi - 1) + 1)
        if i not in existing and float(y_arr[i]) < float(threshold)
    ]
    if not candidates:
        return np.asarray([], dtype=int)

    rng = np.random.default_rng(int(seed or 0))
    take = min(count, len(candidates))
    sampled = rng.choice(np.asarray(candidates, dtype=int), size=take, replace=False)
    return np.sort(sampled.astype(int))


def _resolve_target_window_indices(y, window_cfg, context_datetimes=None):
    if not window_cfg:
        return None

    threshold = window_cfg.get("threshold")
    event_count = max(0, int(window_cfg.get("event_count", 0)))
    event_start = window_cfg.get("event_start")
    pre_records = max(0, int(window_cfg.get("pre_records", 0)))
    post_records = max(0, int(window_cfg.get("post_records", 0)))
    isolated_windows = bool(window_cfg.get("isolated_windows", False))
    y = np.asarray(y, dtype=float).reshape(-1)
    n = len(y)

    if n < 2 or threshold is None or event_count <= 0:
        return None

    event_idx = np.flatnonzero(y >= threshold)
    if event_idx.size == 0:
        return None

    if event_start is None:
        end_event_pos = int(event_idx.size - 1)
        start_event_pos = max(0, end_event_pos - event_count + 1)
        end_idx = min(n - 1, int(event_idx[end_event_pos]) + post_records)
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
    original_end_idx = int(end_idx)

    force_autoclip = bool(window_cfg.get("force_autoclip", False))
    no_autoclip = bool(window_cfg.get("no_autoclip", False)
                       or window_cfg.get("suppress_autodate_clipping", False))
    explicit_event_window = threshold is not None and event_count > 0
    apply_autoclip = (
        context_datetimes is not None
        and not no_autoclip
        and (force_autoclip or not explicit_event_window)
    )
    autodate_clipped = False
    clip_last_index = None
    clip_last_datetime = None
    if no_autoclip:
        autoclip_status = "disabled"
        autoclip_reason = "no_autoclip"
    elif force_autoclip:
        autoclip_status = "pending" if context_datetimes is not None else "unavailable"
        autoclip_reason = "force_autoclip"
    elif explicit_event_window:
        autoclip_status = "skipped"
        autoclip_reason = "explicit_event_window"
    else:
        autoclip_status = "pending" if context_datetimes is not None else "unavailable"
        autoclip_reason = "default"

    if apply_autoclip:
        now = datetime.now()
        valid_idx = [i for i, dt in enumerate(context_datetimes) if dt is not None and dt <= now]
        if valid_idx:
            clip_last_index = int(valid_idx[-1])
            clip_last_datetime = context_datetimes[clip_last_index]
            autoclip_status = "applied"
            if end_idx > clip_last_index:
                end_idx = clip_last_index
                autodate_clipped = True
        else:
            return None

    effective_end_idx = clip_last_index if clip_last_index is not None else (n - 1)

    if isolated_windows:
        selected_events = event_idx[start_event_pos:end_event_pos + 1]
        selected_events = selected_events[selected_events <= effective_end_idx]
        if selected_events.size == 0:
            return None
        test_idx = _build_isolated_event_indices(
            selected_events, pre_records, post_records, effective_end_idx + 1
        )
        test_idx = test_idx[test_idx <= effective_end_idx]
        if test_idx.size == 0:
            return None
        random_negative_count = max(0, int(window_cfg.get("random_negative_count", 0) or 0))
        random_negative_seed = int(window_cfg.get("random_negative_seed", 0) or 0)
        random_negatives = _build_random_negative_indices(
            y,
            threshold,
            selected_events,
            test_idx,
            random_negative_count,
            random_negative_seed,
            effective_end_idx + 1,
        )
        if random_negatives.size > 0:
            test_idx = np.unique(np.concatenate((test_idx, random_negatives)))
        all_effective = np.arange(0, effective_end_idx + 1, dtype=int)
        train_idx = all_effective[~np.isin(all_effective, test_idx)]
    else:
        random_negative_count = 0
        random_negative_seed = 0
        random_negatives = np.asarray([], dtype=int)
        test_idx = np.arange(start_idx, end_idx + 1, dtype=int)
        train_idx = np.concatenate((
            np.arange(0, start_idx, dtype=int),
            np.arange(end_idx + 1, effective_end_idx + 1, dtype=int),
        ))

    split_info = {
        "strategy": strategy,
        "threshold": float(threshold),
        "requested_event_count": int(event_count),
        "used_event_count": int(np.sum(y[test_idx] >= threshold)),
        "pre_records": int(pre_records),
        "post_records": int(post_records),
        "isolated_windows": bool(isolated_windows),
        "random_negative_count_requested": int(random_negative_count),
        "random_negative_count_used": int(random_negatives.size),
        "random_negative_seed": int(random_negative_seed),
        "random_negative_indices": [int(i) for i in random_negatives.tolist()],
        "event_start": None if event_start is None else int(event_start),
        "resolved_event_start_pos": int(start_event_pos),
        "resolved_event_end_pos": int(end_event_pos),
        "test_start": int(test_idx[0]) if test_idx.size > 0 else int(start_idx),
        "test_end": int(test_idx[-1]) if test_idx.size > 0 else int(end_idx),
        "original_test_end": int(original_end_idx),
        "effective_end": int(effective_end_idx),
        "n_train": int(train_idx.size),
        "n_test": int(test_idx.size),
        "autodate_clipped": bool(autodate_clipped),
        "clip_last_index": clip_last_index,
        "clip_last_datetime": None if clip_last_datetime is None else clip_last_datetime.isoformat(sep=" "),
        "autoclip_status": autoclip_status,
        "autoclip_reason": autoclip_reason,
        "force_autoclip": bool(force_autoclip),
        "no_autoclip": bool(no_autoclip),
    }
    train_idx, split_info = enforce_train_before_test(
        train_idx, test_idx,
        window_cfg=window_cfg,
        context_datetimes=context_datetimes,
        split_info=split_info,
    )
    split_info["n_train"] = int(train_idx.size)
    split_info["n_test"] = int(test_idx.size)
    if train_idx.size == 0 or test_idx.size == 0:
        return None

    return {
        "train_idx": train_idx,
        "test_idx": test_idx,
        "info": split_info,
    }


def resolve_target_window_indices(y, window_cfg, context_datetimes=None):
    return _resolve_target_window_indices(y, window_cfg, context_datetimes=context_datetimes)


def resolve_context_window_indices(context_datetimes, start_dt, end_dt=None):
    if context_datetimes is None or start_dt is None:
        return None
    if end_dt is not None and end_dt < start_dt:
        return None
    matched = np.asarray([
        i for i, dt in enumerate(context_datetimes)
        if dt is not None and dt >= start_dt and (end_dt is None or dt <= end_dt)
    ], dtype=int)
    if matched.size == 0:
        return None
    return {
        "indices": matched,
        "info": {
            "requested_start": start_dt.isoformat(sep=" "),
            "requested_end": None if end_dt is None else end_dt.isoformat(sep=" "),
            "resolved_start": int(matched[0]),
            "resolved_end": int(matched[-1]),
            "n_rows": int(matched.size),
        },
    }


def predict_with_result(result, X_train, y_train, X_pred, seed=0,
                        deep_preset_cfgs=None, custom_deep_cfg=None,
                        metric_profile=None, training_weight_cfg=None):
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    X_pred = np.asarray(X_pred, dtype=float)
    extra = result.get("extra", {}) or {}
    bank_value = str(result.get("bank", ""))

    if extra.get("inverted_twin") or bank_value.endswith("__INV"):
        source_bank = extra.get("inverted_from") or ""
        if not source_bank or str(source_bank).endswith("__INV"):
            source_bank = bank_value[:-5] if bank_value.endswith("__INV") else source_bank
        if not source_bank:
            raise ValueError(f"Sorgente invertita non disponibile per bank={bank_value!r}")
        source_result = dict(result)
        source_result["bank"] = source_bank
        source_extra = dict(extra)
        source_extra.pop("inverted_twin", None)
        source_extra.pop("immediate_inverted_twin", None)
        source_extra.pop("inverted_from", None)
        source_extra.pop("inverted_from_serial", None)
        source_result["extra"] = source_extra
        y_pred_source = predict_with_result(
            source_result, X_train, y_train, X_pred, seed=seed,
            deep_preset_cfgs=deep_preset_cfgs, custom_deep_cfg=custom_deep_cfg,
            metric_profile=metric_profile, training_weight_cfg=training_weight_cfg,
        )
        artifacts = (result.get("_artifacts", {}) or {})
        y_ref = artifacts.get("y_true_test")
        if y_ref is None:
            y_ref = y_train
        return np.asarray(_invert_predictions_array(y_ref, y_pred_source, metric_profile), dtype=float)

    if result.get("bank") == "__none__":
        if not TORCH_AVAILABLE:
            raise RuntimeError("torch non disponibile")
        readout = result.get("readout", "")
        if readout == "deepnet_custom":
            cfg = custom_deep_cfg
        elif readout.startswith("deepnet_"):
            preset = readout[len("deepnet_"):]
            deep_preset_cfgs = deep_preset_cfgs or {}
            cfg = deep_preset_cfgs.get(preset, DEEP_PRESETS.get(preset))
        else:
            raise ValueError(f"Readout deep non riconosciuto: {readout}")
        if cfg is None:
            raise ValueError(f"Config deep non disponibile per {readout}")
        sample_weights = make_training_sample_weights(
            y_train, metric_profile=metric_profile, cfg=training_weight_cfg
        )
        cfg = replace(
            _resolve_deep_cfg_runtime(cfg), scale_features=True,
            sample_weights=None if sample_weights is None else sample_weights.tolist(),
        )
        net = DeepNet(cfg=replace(cfg, seed=seed))
        net.fit(X_train, y_train)
        return np.asarray(net.predict(X_pred), dtype=float)

    if result.get("bank") == "__lcs__":
        cfg_payload = (result.get("extra", {}) or {}).get("lcs_cfg") or {}
        valid = {f.name for f in LCSConfig.__dataclass_fields__.values()}
        cfg_kwargs = {k: v for k, v in cfg_payload.items() if k in valid}
        cfg = LCSConfig(**cfg_kwargs) if cfg_kwargs else LCSConfig(seed=seed)
        sample_weights = make_training_sample_weights(
            y_train, metric_profile=metric_profile, cfg=training_weight_cfg
        )
        cfg = replace(cfg, sample_weights=None if sample_weights is None else sample_weights.tolist())
        ucs = UCSPredictor(cfg=cfg)
        ucs.fit(X_train, y_train)
        return np.asarray(ucs.predict(X_pred), dtype=float)

    if result.get("bank") == HYBRID_BANK:
        hybrid_cfg = (result.get("extra", {}) or {}).get("hybrid_cfg") or {}
        lcs_payload = hybrid_cfg.get("lcs_cfg") or {}
        valid = {f.name for f in LCSConfig.__dataclass_fields__.values()}
        cfg_kwargs = {k: v for k, v in lcs_payload.items() if k in valid}
        cfg = LCSConfig(**cfg_kwargs) if cfg_kwargs else LCSConfig(seed=seed)
        sample_weights = make_training_sample_weights(
            y_train, metric_profile=metric_profile, cfg=training_weight_cfg
        )
        cfg = replace(cfg, sample_weights=None if sample_weights is None else sample_weights.tolist())
        lcs_predictor = UCSPredictor(cfg=cfg)
        lcs_predictor.fit(X_train, y_train)
        partner = _fit_partner_model(
            hybrid_cfg.get("partner", {}), X_train, y_train, seed=seed,
            metric_profile=metric_profile, training_weight_cfg=training_weight_cfg,
            deep_preset_cfgs=deep_preset_cfgs, custom_deep_cfg=custom_deep_cfg,
        )
        event_thr = float(hybrid_cfg.get(
            "event_threshold", _event_threshold(metric_profile, fallback=cfg.binary_threshold)
        ))
        lcs_pred = lcs_predictor.predict(X_pred)
        partner_pred = _predict_partner_model(partner, X_pred)
        return np.asarray(_combine_hybrid_predictions(
            lcs_pred, partner_pred,
            hybrid_cfg.get("mode", "and"),
            float(hybrid_cfg.get("alpha", 0.5)),
            event_thr,
            float(hybrid_cfg.get("hybrid_threshold", 0.5)),
        ), dtype=float)

    if result.get("bank") == KAN_BANK:
        cfg_payload = (result.get("extra", {}) or {}).get("kan_cfg") or {}
        valid = {f.name for f in KANConfig.__dataclass_fields__.values()} if KANConfig else set()
        cfg_kwargs = {k: v for k, v in cfg_payload.items() if k in valid}
        cfg = KANConfig(**cfg_kwargs) if cfg_kwargs else KANConfig(seed=seed)
        model = KANReadout(cfg=replace(_resolve_kan_cfg_runtime(cfg), seed=seed))
        sample_weights = make_training_sample_weights(
            y_train, metric_profile=metric_profile, cfg=training_weight_cfg
        )
        model.fit(X_train, y_train, sample_weight=sample_weights)
        return np.asarray(model.predict(X_pred), dtype=float)

    if result.get("bank") == KAN_HYBRID_BANK:
        hybrid_cfg = (result.get("extra", {}) or {}).get("kan_hybrid_cfg") or {}
        kan_payload = hybrid_cfg.get("kan_cfg") or {}
        valid = {f.name for f in KANConfig.__dataclass_fields__.values()} if KANConfig else set()
        cfg_kwargs = {k: v for k, v in kan_payload.items() if k in valid}
        cfg = KANConfig(**cfg_kwargs) if cfg_kwargs else KANConfig(seed=seed)
        sample_weights = make_training_sample_weights(
            y_train, metric_profile=metric_profile, cfg=training_weight_cfg
        )
        kan_model = KANReadout(cfg=replace(_resolve_kan_cfg_runtime(cfg), seed=seed))
        kan_model.fit(X_train, y_train, sample_weight=sample_weights)
        partner = _fit_partner_model(
            hybrid_cfg.get("partner", {}), X_train, y_train, seed=seed,
            metric_profile=metric_profile, training_weight_cfg=training_weight_cfg,
            deep_preset_cfgs=deep_preset_cfgs, custom_deep_cfg=custom_deep_cfg,
        )
        event_thr = float(hybrid_cfg.get(
            "event_threshold", _event_threshold(metric_profile, fallback=0.5)
        ))
        kan_pred = np.asarray(kan_model.predict(X_pred) >= event_thr, dtype=int)
        partner_pred = _predict_partner_model(partner, X_pred)
        return np.asarray(_combine_hybrid_predictions(
            kan_pred, partner_pred,
            hybrid_cfg.get("mode", "and"),
            float(hybrid_cfg.get("alpha", 0.5)),
            event_thr,
            float(hybrid_cfg.get("hybrid_threshold", 0.5)),
        ), dtype=float)

    bank_name = result.get("bank")
    readout_name = result.get("readout")
    bank = BANKS[bank_name](seed)
    bank.fit(X_train)
    Phi_train = bank.transform(X_train)
    Phi_pred = bank.transform(X_pred)
    readout = READOUTS[readout_name]()
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning,
                                module=r"sklearn\.neural_network\._multilayer_perceptron")
        _fit_readout(readout, Phi_train, y_train, sample_weights=sample_weights)
    return np.asarray(readout.predict(Phi_pred), dtype=float)


def run_single(bank_name, readout_name, X_train, y_train, X_test, y_test, seed=0,
               metric_profile=None, X_forecast=None, y_forecast=None, forecast_indices=None,
               context_datetimes_train=None, external_test_size=None,
               training_weight_cfg=None):
    bank = BANKS[bank_name](seed)
    bank.fit(X_train)
    Phi_train = bank.transform(X_train)
    Phi_test = bank.transform(X_test)

    readout = READOUTS[readout_name]()
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    if TORCH_AVAILABLE and isinstance(readout, TorchMLPReadout):
        readout.cfg = _inject_train_context_cfg(
            _resolve_deep_cfg_runtime(readout.cfg),
            tr_idx=np.arange(len(X_train)),
            te_idx=np.arange(int(external_test_size or len(X_test))),
            context_datetimes=context_datetimes_train,
            scale_features=False,
        )
        readout.cfg = replace(
            readout.cfg,
            sample_weights=None if sample_weights is None else sample_weights.tolist(),
        )
    t0 = time.perf_counter()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning,
                                module=r"sklearn\.neural_network\._multilayer_perceptron")
        _fit_readout(readout, Phi_train, y_train, sample_weights=sample_weights)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred_test = readout.predict(Phi_test)
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    mse_train = float(mean_squared_error(y_train, readout.predict(Phi_train)))
    mse_test = float(mean_squared_error(y_test, y_pred_test))
    mae_test = float(mean_absolute_error(y_test, y_pred_test))
    r2 = float(r2_score(y_test, y_pred_test))
    n_params = _get_n_params(readout, bank.n_output_features)
    extra = _extra_metrics(y_test, y_pred_test, metric_profile=metric_profile)
    extra["preprocessing"] = _bank_readout_preprocessing_summary(
        bank_name, readout_name, readout=readout
    )
    if TORCH_AVAILABLE and isinstance(readout, TorchMLPReadout):
        extra["deep_cfg"] = _serialize_deep_cfg(readout.cfg)
    if hasattr(readout, "history") and readout.history and readout.history.get("validation_info"):
        extra["validation_info"] = readout.history["validation_info"]
        if readout.history.get("retrain_info"):
            extra["retrain_info"] = readout.history["retrain_info"]
    if sample_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(sample_weights)),
            "min": float(np.min(sample_weights)),
            "max": float(np.max(sample_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
    }
    if X_forecast is not None and forecast_indices is not None:
        Phi_forecast = bank.transform(X_forecast)
        y_pred_forecast = readout.predict(Phi_forecast)
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": bank_name, "readout": readout_name, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(n_params),
        "extra": extra,
        "_artifacts": artifacts,
    }


def run_single_deepnet(deep_cfg, X_train, y_train, X_test, y_test, seed=0,
                       cfg_label="deepnet", metric_profile=None,
                       X_forecast=None, y_forecast=None, forecast_indices=None,
                       training_weight_cfg=None):
    """DeepNet end-to-end. bank='__none__' significa no feature bank."""
    if not TORCH_AVAILABLE:
        raise RuntimeError("torch non disponibile")
    from dataclasses import replace
    sample_weights = make_training_sample_weights(
        y_train, metric_profile=metric_profile, cfg=training_weight_cfg
    )
    cfg = replace(
        _resolve_deep_cfg_runtime(deep_cfg), seed=seed, scale_features=True,
        sample_weights=None if sample_weights is None else sample_weights.tolist(),
    )
    net = DeepNet(cfg=cfg)

    t0 = time.perf_counter()
    net.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    y_pred_test = net.predict(X_test)
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    mse_train = float(mean_squared_error(y_train, net.predict(X_train)))
    mse_test = float(mean_squared_error(y_test, y_pred_test))
    mae_test = float(mean_absolute_error(y_test, y_pred_test))
    r2 = float(r2_score(y_test, y_pred_test))
    extra = _extra_metrics(y_test, y_pred_test, metric_profile=metric_profile)
    extra["deep_cfg"] = _serialize_deep_cfg(cfg)
    extra["preprocessing"] = {
        "kind": "deep",
        "input_scaler": "zscore_on_raw_X_fit_on_train",
        "target_scaler": "zscore_on_y_fit_on_train",
        "scope": "end_to_end",
    }
    if getattr(net, "history", None) and net.history.get("validation_info"):
        extra["validation_info"] = net.history["validation_info"]
        if net.history.get("retrain_info"):
            extra["retrain_info"] = net.history["retrain_info"]
    if sample_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(sample_weights)),
            "min": float(np.min(sample_weights)),
            "max": float(np.max(sample_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
    }
    if X_forecast is not None and forecast_indices is not None:
        y_pred_forecast = net.predict(X_forecast)
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": "__none__", "readout": cfg_label, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(net.n_params),
        "extra": extra,
        "_artifacts": artifacts,
    }


def _lcs_result_from_fit(lcs_fit, X_train, y_train, X_test, y_test, seed=0,
                         cfg_label="ucs_default", metric_profile=None,
                         X_forecast=None, y_forecast=None, forecast_indices=None):
    predictor, cfg, sample_weights, train_time = lcs_fit
    y_train_bin = _binarize_lcs_target(y_train, cfg)
    y_test_bin = _binarize_lcs_target(y_test, cfg)
    lcs_profile = _lcs_metric_profile(metric_profile)

    t0 = time.perf_counter()
    y_pred_test = predictor.predict(X_test)
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    y_pred_train = predictor.predict(X_train)
    mse_train = float(mean_squared_error(y_train_bin, y_pred_train))
    mse_test = float(mean_squared_error(y_test_bin, y_pred_test))
    mae_test = float(mean_absolute_error(y_test_bin, y_pred_test))
    r2 = float(r2_score(y_test_bin, y_pred_test))
    extra = _extra_metrics(y_test_bin, y_pred_test, metric_profile=lcs_profile)
    extra["lcs_cfg"] = _serialize_lcs_cfg(cfg)
    extra["preprocessing"] = {
        "kind": "lcs",
        "input_scaler": "none",
        "target_transform": "binary_threshold",
        "binary_threshold": float(cfg.binary_threshold),
    }
    if predictor.history:
        extra["lcs_history"] = predictor.history
    if predictor.validation_info:
        extra["validation_info"] = predictor.validation_info
    if predictor.best_validation_metrics:
        extra["lcs_best_validation"] = predictor.best_validation_metrics
    if predictor.best_epoch is not None:
        extra["lcs_best_epoch"] = int(predictor.best_epoch)
    extra["lcs_positive_weight"] = float(getattr(predictor, "positive_weight_", 1.0))
    extra["lcs_positive_replay"] = int(getattr(predictor, "positive_replay_", 1))
    extra["lcs_positive_vote_weight"] = float(getattr(predictor, "positive_vote_weight_", 1.0))
    if sample_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(sample_weights)),
            "min": float(np.min(sample_weights)),
            "max": float(np.max(sample_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test_bin, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
        "best_rules": predictor.top_rules(k=max(1, int(getattr(cfg, "export_rule_count", 20) or 20))),
    }
    if X_forecast is not None and forecast_indices is not None:
        y_forecast_bin = _binarize_lcs_target(y_forecast, cfg)
        y_pred_forecast = predictor.predict(X_forecast)
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast_bin, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": "__lcs__", "readout": cfg_label, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(predictor.n_params),
        "extra": extra,
        "_artifacts": artifacts,
    }


def run_single_lcs(lcs_cfg, X_train, y_train, X_test, y_test, seed=0,
                   cfg_label="ucs_default", metric_profile=None,
                   X_forecast=None, y_forecast=None, forecast_indices=None,
                   context_datetimes_train=None, training_weight_cfg=None):
    lcs_fit = _fit_lcs_model(
        lcs_cfg, X_train, y_train, seed=seed, metric_profile=metric_profile,
        training_weight_cfg=training_weight_cfg,
        context_datetimes_train=context_datetimes_train,
    )
    return _lcs_result_from_fit(
        lcs_fit, X_train, y_train, X_test, y_test, seed=seed,
        cfg_label=cfg_label, metric_profile=metric_profile,
        X_forecast=X_forecast, y_forecast=y_forecast,
        forecast_indices=forecast_indices,
    )


def _kan_result_from_fit(kan_fit, X_train, y_train, X_test, y_test, seed=0,
                         cfg_label="kan_tiny", metric_profile=None,
                         X_forecast=None, y_forecast=None, forecast_indices=None):
    model, cfg, sample_weights, train_time = kan_fit

    t0 = time.perf_counter()
    y_pred_test = model.predict(X_test)
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    y_pred_train = model.predict(X_train)
    mse_train = float(mean_squared_error(y_train, y_pred_train))
    mse_test = float(mean_squared_error(y_test, y_pred_test))
    mae_test = float(mean_absolute_error(y_test, y_pred_test))
    r2 = float(r2_score(y_test, y_pred_test))
    extra = _extra_metrics(y_test, y_pred_test, metric_profile=metric_profile)
    extra["kan_cfg"] = serialize_kan_cfg(cfg)
    extra["preprocessing"] = {
        "kind": "kan",
        "input_scaler": "zscore_then_tanh_fit_on_train",
        "target_scaler": "zscore_on_y_fit_on_train",
    }
    if getattr(model, "history", None):
        extra["kan_history"] = _serialize_kan_history(model.history)
    if sample_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(sample_weights)),
            "min": float(np.min(sample_weights)),
            "max": float(np.max(sample_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
        "kan_summary": {
            "label": cfg_label,
            "n_params": int(getattr(model, "n_params", 0)),
            "cfg": serialize_kan_cfg(cfg),
        },
    }
    if X_forecast is not None and forecast_indices is not None:
        y_pred_forecast = model.predict(X_forecast)
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": KAN_BANK, "readout": cfg_label, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(getattr(model, "n_params", 0)),
        "extra": extra,
        "_artifacts": artifacts,
    }


def run_single_kan(kan_cfg, X_train, y_train, X_test, y_test, seed=0,
                   cfg_label="kan_tiny", metric_profile=None,
                   X_forecast=None, y_forecast=None, forecast_indices=None,
                   training_weight_cfg=None):
    kan_fit = _fit_kan_model(
        kan_cfg, X_train, y_train, seed=seed, metric_profile=metric_profile,
        training_weight_cfg=training_weight_cfg,
    )
    return _kan_result_from_fit(
        kan_fit, X_train, y_train, X_test, y_test, seed=seed,
        cfg_label=cfg_label, metric_profile=metric_profile,
        X_forecast=X_forecast, y_forecast=y_forecast,
        forecast_indices=forecast_indices,
    )


def run_single_kan_hybrid(kan_cfg, partner_spec, X_train, y_train, X_test, y_test,
                          seed=0, kan_label="kan_tiny", mode="and", alpha=0.5,
                          hybrid_threshold=0.5, metric_profile=None,
                          X_forecast=None, y_forecast=None, forecast_indices=None,
                          context_datetimes_train=None, external_test_size=None,
                          training_weight_cfg=None, deep_preset_cfgs=None,
                          custom_deep_cfg=None, prefit_kan=None,
                          prefit_partner=None):
    if prefit_kan is None:
        prefit_kan = _fit_kan_model(
            kan_cfg, X_train, y_train, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
        )
        reused_kan = False
    else:
        reused_kan = True
    kan_model, cfg, kan_weights, kan_train_time = prefit_kan

    if prefit_partner is None:
        partner = _fit_partner_model(
            partner_spec, X_train, y_train, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg, deep_preset_cfgs=deep_preset_cfgs,
            custom_deep_cfg=custom_deep_cfg,
            context_datetimes_train=context_datetimes_train,
            external_test_size=external_test_size,
        )
        reused_partner = False
    else:
        partner = prefit_partner
        reused_partner = True
    partner_train_time = float(partner.get("train_time_s", 0.0))
    train_time = float(kan_train_time) + partner_train_time
    event_thr = _event_threshold(metric_profile, fallback=0.5)
    event_profile = _lcs_metric_profile(metric_profile)
    y_test_bin = (np.asarray(y_test, dtype=float).reshape(-1) >= float(event_thr)).astype(int)
    y_train_bin = (np.asarray(y_train, dtype=float).reshape(-1) >= float(event_thr)).astype(int)

    t0 = time.perf_counter()
    kan_pred_test_raw = kan_model.predict(X_test)
    kan_pred_test = np.asarray(kan_pred_test_raw >= float(event_thr), dtype=int)
    partner_pred_test = _predict_partner_model(partner, X_test)
    y_pred_test = _combine_hybrid_predictions(
        kan_pred_test, partner_pred_test, mode, alpha, event_thr, hybrid_threshold
    )
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    kan_pred_train = np.asarray(kan_model.predict(X_train) >= float(event_thr), dtype=int)
    partner_pred_train = _predict_partner_model(partner, X_train)
    y_pred_train = _combine_hybrid_predictions(
        kan_pred_train, partner_pred_train, mode, alpha, event_thr, hybrid_threshold
    )
    mse_train = float(mean_squared_error(y_train_bin, y_pred_train))
    mse_test = float(mean_squared_error(y_test_bin, y_pred_test))
    mae_test = float(mean_absolute_error(y_test_bin, y_pred_test))
    r2 = float(r2_score(y_test_bin, y_pred_test))

    readout_label = _kan_hybrid_readout_label(kan_label, partner_spec, mode, alpha)
    extra = _extra_metrics(y_test_bin, y_pred_test, metric_profile=event_profile)
    extra["kan_hybrid_cfg"] = {
        "kan_label": kan_label,
        "kan_cfg": serialize_kan_cfg(cfg),
        "partner": dict(partner_spec),
        "mode": str(mode),
        "alpha": float(alpha),
        "hybrid_threshold": float(hybrid_threshold),
        "event_threshold": float(event_thr),
    }
    extra["hybrid_cache"] = {
        "reused_kan": bool(reused_kan),
        "reused_partner": bool(reused_partner),
        "kan_train_time_s": float(kan_train_time),
        "partner_train_time_s": float(partner_train_time),
    }
    extra["kan_cfg"] = serialize_kan_cfg(cfg)
    extra["preprocessing"] = {
        "kind": "kan_hybrid",
        "kan": {
            "input_scaler": "zscore_then_tanh_fit_on_train",
            "target_scaler": "zscore_on_y_fit_on_train",
            "event_threshold": float(event_thr),
        },
        "partner": partner.get("preprocessing"),
    }
    if kan_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(kan_weights)),
            "min": float(np.min(kan_weights)),
            "max": float(np.max(kan_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test_bin, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
        "kan_summary": {
            "label": kan_label,
            "n_params": int(getattr(kan_model, "n_params", 0)),
            "cfg": serialize_kan_cfg(cfg),
        },
    }
    if X_forecast is not None and forecast_indices is not None:
        y_forecast_bin = (np.asarray(y_forecast, dtype=float).reshape(-1) >= float(event_thr)).astype(int)
        kan_pred_forecast = np.asarray(kan_model.predict(X_forecast) >= float(event_thr), dtype=int)
        partner_pred_forecast = _predict_partner_model(partner, X_forecast)
        y_pred_forecast = _combine_hybrid_predictions(
            kan_pred_forecast, partner_pred_forecast, mode, alpha,
            event_thr, hybrid_threshold,
        )
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast_bin, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": KAN_HYBRID_BANK, "readout": readout_label, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(getattr(kan_model, "n_params", 0)) + int(partner.get("n_params", 0)),
        "extra": extra,
        "_artifacts": artifacts,
    }


def run_single_hybrid(lcs_cfg, partner_spec, X_train, y_train, X_test, y_test,
                      seed=0, lcs_label="ucs", mode="and", alpha=0.5,
                      hybrid_threshold=0.5, metric_profile=None,
                      X_forecast=None, y_forecast=None, forecast_indices=None,
                      context_datetimes_train=None, external_test_size=None,
                      training_weight_cfg=None, deep_preset_cfgs=None,
                      custom_deep_cfg=None, prefit_lcs=None,
                      prefit_partner=None):
    if prefit_lcs is None:
        prefit_lcs = _fit_lcs_model(
            lcs_cfg, X_train, y_train, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
            context_datetimes_train=context_datetimes_train,
        )
        reused_lcs = False
    else:
        reused_lcs = True
    lcs_predictor, cfg, lcs_weights, lcs_train_time = prefit_lcs

    if prefit_partner is None:
        partner = _fit_partner_model(
            partner_spec, X_train, y_train, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg, deep_preset_cfgs=deep_preset_cfgs,
            custom_deep_cfg=custom_deep_cfg,
            context_datetimes_train=context_datetimes_train,
            external_test_size=external_test_size,
        )
        reused_partner = False
    else:
        partner = prefit_partner
        reused_partner = True
    partner_train_time = float(partner.get("train_time_s", 0.0))
    train_time = float(lcs_train_time) + partner_train_time
    event_thr = _event_threshold(metric_profile, fallback=cfg.binary_threshold)
    lcs_profile = _lcs_metric_profile(metric_profile)
    y_train_bin = _binarize_lcs_target(y_train, cfg)
    y_test_bin = _binarize_lcs_target(y_test, cfg)

    t0 = time.perf_counter()
    lcs_pred_test = lcs_predictor.predict(X_test)
    partner_pred_test = _predict_partner_model(partner, X_test)
    y_pred_test = _combine_hybrid_predictions(
        lcs_pred_test, partner_pred_test, mode, alpha, event_thr, hybrid_threshold
    )
    inf_time_us = (time.perf_counter() - t0) * 1e6 / max(len(X_test), 1)

    lcs_pred_train = lcs_predictor.predict(X_train)
    partner_pred_train = _predict_partner_model(partner, X_train)
    y_pred_train = _combine_hybrid_predictions(
        lcs_pred_train, partner_pred_train, mode, alpha, event_thr, hybrid_threshold
    )
    mse_train = float(mean_squared_error(y_train_bin, y_pred_train))
    mse_test = float(mean_squared_error(y_test_bin, y_pred_test))
    mae_test = float(mean_absolute_error(y_test_bin, y_pred_test))
    r2 = float(r2_score(y_test_bin, y_pred_test))

    readout_label = _hybrid_readout_label(lcs_label, partner_spec, mode, alpha)
    extra = _extra_metrics(y_test_bin, y_pred_test, metric_profile=lcs_profile)
    extra["hybrid_cfg"] = {
        "lcs_label": lcs_label,
        "lcs_cfg": _serialize_lcs_cfg(cfg),
        "partner": dict(partner_spec),
        "mode": str(mode),
        "alpha": float(alpha),
        "hybrid_threshold": float(hybrid_threshold),
        "event_threshold": float(event_thr),
    }
    extra["hybrid_cache"] = {
        "reused_lcs": bool(reused_lcs),
        "reused_partner": bool(reused_partner),
        "lcs_train_time_s": float(lcs_train_time),
        "partner_train_time_s": float(partner_train_time),
    }
    extra["lcs_cfg"] = _serialize_lcs_cfg(cfg)
    extra["preprocessing"] = {
        "kind": "hybrid",
        "lcs": {
            "input_scaler": "none",
            "target_transform": "binary_threshold",
            "binary_threshold": float(cfg.binary_threshold),
        },
        "partner": partner.get("preprocessing"),
    }
    if lcs_predictor.history:
        extra["lcs_history"] = lcs_predictor.history
    if lcs_predictor.validation_info:
        extra["validation_info"] = lcs_predictor.validation_info
    if lcs_predictor.best_validation_metrics:
        extra["lcs_best_validation"] = lcs_predictor.best_validation_metrics
    if lcs_predictor.best_epoch is not None:
        extra["lcs_best_epoch"] = int(lcs_predictor.best_epoch)
    if lcs_weights is not None:
        extra["training_sample_weighting"] = {
            "mean": float(np.mean(lcs_weights)),
            "min": float(np.min(lcs_weights)),
            "max": float(np.max(lcs_weights)),
        }

    artifacts = {
        "y_true_test": np.asarray(y_test_bin, dtype=float),
        "y_pred_test": np.asarray(y_pred_test, dtype=float),
        "best_rules": lcs_predictor.top_rules(k=max(1, int(getattr(cfg, "export_rule_count", 20) or 20))),
    }
    if X_forecast is not None and forecast_indices is not None:
        y_forecast_bin = _binarize_lcs_target(y_forecast, cfg)
        lcs_pred_forecast = lcs_predictor.predict(X_forecast)
        partner_pred_forecast = _predict_partner_model(partner, X_forecast)
        y_pred_forecast = _combine_hybrid_predictions(
            lcs_pred_forecast, partner_pred_forecast, mode, alpha,
            event_thr, hybrid_threshold,
        )
        artifacts["forecast_indices"] = np.asarray(forecast_indices, dtype=int)
        artifacts["y_true_forecast"] = np.asarray(y_forecast_bin, dtype=float)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_forecast, dtype=float)

    return {
        "bank": HYBRID_BANK, "readout": readout_label, "seed": int(seed),
        "mse_train": mse_train, "mse_test": mse_test, "mae_test": mae_test, "r2": r2,
        "inference_time_us": float(inf_time_us),
        "train_time_s": float(train_time),
        "n_effective_params": int(lcs_predictor.n_params) + int(partner.get("n_params", 0)),
        "extra": extra,
        "_artifacts": artifacts,
    }


def _finalize_trial_result(r, metric_profile, mse_ref, kpi_weights, *, lcs_score=False):
    profile = _lcs_metric_profile(metric_profile) if lcs_score else metric_profile
    r["overall_kpi"], score_components = compute_overall_score(
        r, profile, mse_ref=mse_ref, weights=kpi_weights
    )
    r.setdefault("extra", {})
    r["extra"]["score_components"] = score_components
    if lcs_score:
        r["extra"]["score_kind"] = "event"
        r["extra"]["score_label"] = "event_composite"
    else:
        r["extra"]["score_kind"] = metric_profile["kind"]
        r["extra"]["score_label"] = metric_profile["score_label"]
    return r


def _run_synthetic_seed_trials(seed, task_name, banks, readouts, n_train, n_test,
                               noise_std, kpi_weights, deep_presets,
                               custom_deep_cfg, deep_preset_cfgs, lcs_items,
                               metric_profile, training_weight_cfg, hybrid_specs,
                               kan_items, kan_hybrid_specs,
                               trial_filter, mse_ref):
    X_tr, y_tr = generate_dataset(task_name, n_train, seed=seed, noise_std=noise_std)
    X_te, y_te = generate_dataset(task_name, n_test, seed=seed + 1000, noise_std=0.0)
    out = []

    for bn in banks:
        for rn in readouts:
            if not _trial_allowed(trial_filter, "bank", bank=bn, readout=rn):
                continue
            r = run_single(bn, rn, X_tr, y_tr, X_te, y_te, seed=seed,
                           metric_profile=metric_profile,
                           external_test_size=len(y_te),
                           training_weight_cfg=training_weight_cfg)
            r.update({"task": task_name, "n_train": n_train,
                      "n_test": n_test, "noise_std": noise_std})
            out.append(_finalize_trial_result(
                r, metric_profile, mse_ref, kpi_weights
            ))

    for preset in deep_presets:
        if not _trial_allowed(trial_filter, "deep", preset=preset):
            continue
        cfg = deep_preset_cfgs.get(preset, DEEP_PRESETS.get(preset))
        if cfg is None:
            continue
        cfg = _inject_train_context_cfg(cfg, te_idx=np.arange(len(y_te)),
                                        scale_features=True)
        r = run_single_deepnet(cfg, X_tr, y_tr, X_te, y_te,
                               seed=seed, cfg_label=f"deepnet_{preset}",
                               metric_profile=metric_profile,
                               training_weight_cfg=training_weight_cfg)
        r.update({"task": task_name, "n_train": n_train,
                  "n_test": n_test, "noise_std": noise_std})
        out.append(_finalize_trial_result(
            r, metric_profile, mse_ref, kpi_weights
        ))

    if custom_deep_cfg is not None and _trial_allowed(
        trial_filter, "deep", preset="custom"
    ):
        cfg = _inject_train_context_cfg(custom_deep_cfg, te_idx=np.arange(len(y_te)),
                                        scale_features=True)
        r = run_single_deepnet(cfg, X_tr, y_tr, X_te, y_te,
                               seed=seed, cfg_label="deepnet_custom",
                               metric_profile=metric_profile,
                               training_weight_cfg=training_weight_cfg)
        r.update({"task": task_name, "n_train": n_train,
                  "n_test": n_test, "noise_std": noise_std})
        out.append(_finalize_trial_result(
            r, metric_profile, mse_ref, kpi_weights
        ))

    partner_fit_cache = {}
    for lcs_label, lcs_cfg in lcs_items:
        lcs_fit = _fit_lcs_model(
            lcs_cfg, X_tr, y_tr, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
        )
        if _trial_allowed(trial_filter, "lcs", lcs_label=lcs_label):
            r = _lcs_result_from_fit(
                lcs_fit, X_tr, y_tr, X_te, y_te,
                seed=seed, cfg_label=lcs_label, metric_profile=metric_profile,
            )
            r.update({"task": task_name, "n_train": n_train,
                      "n_test": n_test, "noise_std": noise_std})
            out.append(_finalize_trial_result(
                r, metric_profile, mse_ref, kpi_weights
            ))

        for spec in hybrid_specs:
            partner_spec = spec.get("partner", {})
            hybrid_readout = _hybrid_readout_label(
                lcs_label, partner_spec, spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if not _trial_allowed(trial_filter, "hybrid", hybrid_readout=hybrid_readout):
                continue
            partner_key = _partner_cache_key(partner_spec)
            if partner_key not in partner_fit_cache:
                partner_fit_cache[partner_key] = _fit_partner_model(
                    partner_spec, X_tr, y_tr, seed=seed,
                    metric_profile=metric_profile,
                    training_weight_cfg=training_weight_cfg,
                    deep_preset_cfgs=deep_preset_cfgs,
                    custom_deep_cfg=custom_deep_cfg,
                    external_test_size=len(y_te),
                )
            r = run_single_hybrid(
                lcs_cfg, partner_spec, X_tr, y_tr, X_te, y_te,
                seed=seed, lcs_label=lcs_label,
                mode=spec.get("mode", "and"),
                alpha=float(spec.get("alpha", 0.5)),
                hybrid_threshold=float(spec.get("hybrid_threshold", 0.5)),
                metric_profile=metric_profile,
                training_weight_cfg=training_weight_cfg,
                deep_preset_cfgs=deep_preset_cfgs,
                custom_deep_cfg=custom_deep_cfg,
                prefit_lcs=lcs_fit,
                prefit_partner=partner_fit_cache[partner_key],
            )
            r.update({"task": task_name, "n_train": n_train,
                      "n_test": n_test, "noise_std": noise_std})
            out.append(_finalize_trial_result(
                r, metric_profile, mse_ref, kpi_weights, lcs_score=True
            ))
    kan_partner_fit_cache = {}
    for kan_label, kan_cfg in kan_items:
        kan_fit = _fit_kan_model(
            kan_cfg, X_tr, y_tr, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
        )
        if _trial_allowed(trial_filter, "kan", preset=kan_label):
            r = _kan_result_from_fit(
                kan_fit, X_tr, y_tr, X_te, y_te,
                seed=seed, cfg_label=kan_label, metric_profile=metric_profile,
            )
            r.update({"task": task_name, "n_train": n_train,
                      "n_test": n_test, "noise_std": noise_std})
            out.append(_finalize_trial_result(
                r, metric_profile, mse_ref, kpi_weights
            ))

        for spec in kan_hybrid_specs:
            partner_spec = spec.get("partner", {})
            hybrid_readout = _kan_hybrid_readout_label(
                kan_label, partner_spec, spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if not _trial_allowed(trial_filter, "kan_hybrid", hybrid_readout=hybrid_readout):
                continue
            partner_key = _partner_cache_key(partner_spec)
            if partner_key not in kan_partner_fit_cache:
                kan_partner_fit_cache[partner_key] = _fit_partner_model(
                    partner_spec, X_tr, y_tr, seed=seed,
                    metric_profile=metric_profile,
                    training_weight_cfg=training_weight_cfg,
                    deep_preset_cfgs=deep_preset_cfgs,
                    custom_deep_cfg=custom_deep_cfg,
                    external_test_size=len(y_te),
                )
            r = run_single_kan_hybrid(
                kan_cfg, partner_spec, X_tr, y_tr, X_te, y_te,
                seed=seed, kan_label=kan_label,
                mode=spec.get("mode", "and"),
                alpha=float(spec.get("alpha", 0.5)),
                hybrid_threshold=float(spec.get("hybrid_threshold", 0.5)),
                metric_profile=metric_profile,
                training_weight_cfg=training_weight_cfg,
                deep_preset_cfgs=deep_preset_cfgs,
                custom_deep_cfg=custom_deep_cfg,
                prefit_kan=kan_fit,
                prefit_partner=kan_partner_fit_cache[partner_key],
            )
            r.update({"task": task_name, "n_train": n_train,
                      "n_test": n_test, "noise_std": noise_std})
            out.append(_finalize_trial_result(
                r, metric_profile, mse_ref, kpi_weights, lcs_score=True
            ))
    return out


def _run_dataset_seed_trials(seed, X, y, dataset_name, banks, readouts, n_train,
                             n_test, kpi_weights, deep_presets, custom_deep_cfg,
                             deep_preset_cfgs, lcs_items, target_window_cfg,
                             metric_profile, context_datetimes, forecast_indices,
                             forecast_info, training_weight_cfg, hybrid_specs,
                             kan_items, kan_hybrid_specs,
                             trial_filter, mse_ref, feature_selection_cfg=None):
    fixed_window = _resolve_target_window_indices(
        y, target_window_cfg, context_datetimes=context_datetimes
    )
    if target_window_cfg is not None and fixed_window is None:
        raise ValueError("Impossibile costruire la target window richiesta sul dataset")

    if fixed_window is not None:
        tr_idx = fixed_window["train_idx"]
        te_idx = fixed_window["test_idx"]
        split_info = dict(fixed_window["info"])
    else:
        stratify = _build_stratify_labels(y)
        indices = np.arange(len(X))
        tr_idx, te_idx = train_test_split(
            indices, train_size=n_train, test_size=n_test, random_state=seed,
            shuffle=True, stratify=stratify
        )
        tr_idx = np.sort(np.asarray(tr_idx, dtype=int))
        te_idx = np.sort(np.asarray(te_idx, dtype=int))
        split_info = {
            "strategy": "random_split",
            "n_train": int(len(tr_idx)),
            "n_test": int(len(te_idx)),
        }

    X_tr = np.asarray(X[tr_idx], dtype=float)
    X_te = np.asarray(X[te_idx], dtype=float)
    y_tr = np.asarray(y[tr_idx], dtype=float)
    y_te = np.asarray(y[te_idx], dtype=float)

    # Feature selection if requested
    feature_names = None
    if feature_selection_cfg is not None:
        k_best = feature_selection_cfg.get("k_best")
        threshold = feature_selection_cfg.get("threshold")
        percentile = feature_selection_cfg.get("percentile")
        min_features = feature_selection_cfg.get("min_features")
        max_features = feature_selection_cfg.get("max_features")
        raw_names = feature_selection_cfg.get("feature_names")
        
        # If any of the selectors or min/max constraints is active
        if (k_best is not None and k_best > 0) or \
           (threshold is not None and threshold > 0.0) or \
           (percentile is not None and percentile > 0.0) or \
           (min_features is not None and min_features > 0) or \
           (max_features is not None and max_features > 0):
            
            # 1. Variance filter: remove zero variance columns from X_tr
            variances = np.var(X_tr, axis=0)
            active_indices = np.flatnonzero(variances > 1e-6)
            constant_indices = np.flatnonzero(variances <= 1e-6)
            
            if len(active_indices) == 0:
                print("[feature-selection] Warning: All features have zero variance on training set!")
                active_indices = np.arange(X_tr.shape[1])
                
            # 2. Compute mutual information on active features
            X_tr_active = X_tr[:, active_indices]
            from sklearn.feature_selection import mutual_info_classif
            mi_scores = mutual_info_classif(X_tr_active, y_tr, discrete_features=True, random_state=42)
            
            # Map score to each feature index
            feature_scores = {idx: float(score) for idx, score in zip(active_indices, mi_scores)}
            for idx in constant_indices:
                feature_scores[idx] = 0.0
                
            # 3. Select subset based on criteria
            sorted_active = sorted(active_indices, key=lambda i: feature_scores[i], reverse=True)
            
            if k_best is not None and k_best > 0:
                selected_list = sorted_active[:k_best]
            elif percentile is not None and percentile > 0.0:
                k = max(1, int(len(active_indices) * percentile))
                selected_list = sorted_active[:k]
            elif threshold is not None:
                selected_list = [i for i in active_indices if feature_scores[i] >= threshold]
            else:
                selected_list = list(sorted_active)
                
            # Apply min/max bounds dynamically
            if min_features is not None and min_features > 0:
                if len(selected_list) < min_features:
                    selected_list = sorted_active[:min_features]
                    
            if max_features is not None and max_features > 0:
                if len(selected_list) > max_features:
                    selected_list = sorted_active[:max_features]
                    
            # Convert back to sorted list of unique selected indices
            selected_indices = sorted(list(set(selected_list)))
            if len(selected_indices) == 0:
                # Fallback: keep at least the top feature to prevent empty matrix
                top_idx = max(active_indices, key=lambda i: feature_scores[i])
                selected_indices = [int(top_idx)]
                
            # Apply selection to matrices
            X_tr = X_tr[:, selected_indices]
            X_te = X_te[:, selected_indices]
            
            # Keep track of selected feature names for metadata
            if raw_names is not None:
                feature_names = [raw_names[i] for i in selected_indices]
                
            print(f"[feature-selection] Selected {len(selected_indices)} / {X.shape[1]} features (MI max: {max(feature_scores.values()):.6f})")

    context_datetimes_train = None
    if context_datetimes is not None:
        context_datetimes_train = [context_datetimes[int(i)] for i in tr_idx]
    X_fc = None
    y_fc = None
    if forecast_indices is not None:
        X_fc = np.asarray(X[forecast_indices], dtype=float)
        # Apply feature selection to forecast matrix too
        if feature_selection_cfg is not None and (
            (k_best is not None and k_best > 0) or 
            (threshold is not None and threshold > 0.0) or 
            (percentile is not None and percentile > 0.0) or
            (min_features is not None and min_features > 0) or
            (max_features is not None and max_features > 0)
        ):
            X_fc = X_fc[:, selected_indices]
        y_fc = np.asarray(y[forecast_indices], dtype=float)

    def _attach_dataset_meta(result):
        result.update({"task": dataset_name, "n_train": len(X_tr),
                       "n_test": len(X_te), "noise_std": 0.0})
        result.setdefault("extra", {})
        result["extra"]["split_info"] = split_info
        if forecast_info is not None:
            result["extra"]["forecast_info"] = forecast_info
        result.setdefault("_artifacts", {})
        result["_artifacts"]["test_indices"] = np.asarray(te_idx, dtype=int)
        return result

    out = []
    for bn in banks:
        for rn in readouts:
            if not _trial_allowed(trial_filter, "bank", bank=bn, readout=rn):
                continue
            r = run_single(bn, rn, X_tr, y_tr, X_te, y_te, seed=seed,
                           metric_profile=metric_profile,
                           X_forecast=X_fc, y_forecast=y_fc,
                           forecast_indices=forecast_indices,
                           context_datetimes_train=context_datetimes_train,
                           external_test_size=len(te_idx),
                           training_weight_cfg=training_weight_cfg)
            out.append(_finalize_trial_result(
                _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights
            ))

    for preset in deep_presets:
        if not _trial_allowed(trial_filter, "deep", preset=preset):
            continue
        cfg = deep_preset_cfgs.get(preset, DEEP_PRESETS.get(preset))
        if cfg is None:
            continue
        cfg = _inject_train_context_cfg(
            cfg, tr_idx=tr_idx, te_idx=te_idx,
            context_datetimes=context_datetimes, scale_features=True,
        )
        r = run_single_deepnet(cfg, X_tr, y_tr, X_te, y_te,
                               seed=seed, cfg_label=f"deepnet_{preset}",
                               metric_profile=metric_profile,
                               X_forecast=X_fc, y_forecast=y_fc,
                               forecast_indices=forecast_indices,
                               training_weight_cfg=training_weight_cfg)
        out.append(_finalize_trial_result(
            _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights
        ))

    if custom_deep_cfg is not None and _trial_allowed(
        trial_filter, "deep", preset="custom"
    ):
        cfg = _inject_train_context_cfg(
            custom_deep_cfg, tr_idx=tr_idx, te_idx=te_idx,
            context_datetimes=context_datetimes, scale_features=True,
        )
        r = run_single_deepnet(cfg, X_tr, y_tr, X_te, y_te,
                               seed=seed, cfg_label="deepnet_custom",
                               metric_profile=metric_profile,
                               X_forecast=X_fc, y_forecast=y_fc,
                               forecast_indices=forecast_indices,
                               training_weight_cfg=training_weight_cfg)
        out.append(_finalize_trial_result(
            _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights
        ))

    partner_fit_cache = {}
    for lcs_label, lcs_cfg in lcs_items:
        lcs_fit = _fit_lcs_model(
            lcs_cfg, X_tr, y_tr, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
            context_datetimes_train=context_datetimes_train,
        )
        if _trial_allowed(trial_filter, "lcs", lcs_label=lcs_label):
            r = _lcs_result_from_fit(
                lcs_fit, X_tr, y_tr, X_te, y_te,
                seed=seed, cfg_label=lcs_label, metric_profile=metric_profile,
                X_forecast=X_fc, y_forecast=y_fc,
                forecast_indices=forecast_indices,
            )
            out.append(_finalize_trial_result(
                _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights
            ))

        for spec in hybrid_specs:
            partner_spec = spec.get("partner", {})
            hybrid_readout = _hybrid_readout_label(
                lcs_label, partner_spec, spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if not _trial_allowed(trial_filter, "hybrid", hybrid_readout=hybrid_readout):
                continue
            partner_key = _partner_cache_key(partner_spec)
            if partner_key not in partner_fit_cache:
                partner_fit_cache[partner_key] = _fit_partner_model(
                    partner_spec, X_tr, y_tr, seed=seed,
                    metric_profile=metric_profile,
                    training_weight_cfg=training_weight_cfg,
                    deep_preset_cfgs=deep_preset_cfgs,
                    custom_deep_cfg=custom_deep_cfg,
                    context_datetimes_train=context_datetimes_train,
                    external_test_size=len(te_idx),
                )
            r = run_single_hybrid(
                lcs_cfg, partner_spec, X_tr, y_tr, X_te, y_te,
                seed=seed, lcs_label=lcs_label,
                mode=spec.get("mode", "and"),
                alpha=float(spec.get("alpha", 0.5)),
                hybrid_threshold=float(spec.get("hybrid_threshold", 0.5)),
                metric_profile=metric_profile,
                X_forecast=X_fc, y_forecast=y_fc,
                forecast_indices=forecast_indices,
                context_datetimes_train=context_datetimes_train,
                external_test_size=len(te_idx),
                training_weight_cfg=training_weight_cfg,
                deep_preset_cfgs=deep_preset_cfgs,
                custom_deep_cfg=custom_deep_cfg,
                prefit_lcs=lcs_fit,
                prefit_partner=partner_fit_cache[partner_key],
            )
            out.append(_finalize_trial_result(
                _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights,
                lcs_score=True,
            ))
    kan_partner_fit_cache = {}
    for kan_label, kan_cfg in kan_items:
        kan_fit = _fit_kan_model(
            kan_cfg, X_tr, y_tr, seed=seed, metric_profile=metric_profile,
            training_weight_cfg=training_weight_cfg,
        )
        if _trial_allowed(trial_filter, "kan", preset=kan_label):
            r = _kan_result_from_fit(
                kan_fit, X_tr, y_tr, X_te, y_te,
                seed=seed, cfg_label=kan_label, metric_profile=metric_profile,
                X_forecast=X_fc, y_forecast=y_fc,
                forecast_indices=forecast_indices,
            )
            out.append(_finalize_trial_result(
                _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights
            ))

        for spec in kan_hybrid_specs:
            partner_spec = spec.get("partner", {})
            hybrid_readout = _kan_hybrid_readout_label(
                kan_label, partner_spec, spec.get("mode", "and"),
                float(spec.get("alpha", 0.5)),
            )
            if not _trial_allowed(trial_filter, "kan_hybrid", hybrid_readout=hybrid_readout):
                continue
            partner_key = _partner_cache_key(partner_spec)
            if partner_key not in kan_partner_fit_cache:
                kan_partner_fit_cache[partner_key] = _fit_partner_model(
                    partner_spec, X_tr, y_tr, seed=seed,
                    metric_profile=metric_profile,
                    training_weight_cfg=training_weight_cfg,
                    deep_preset_cfgs=deep_preset_cfgs,
                    custom_deep_cfg=custom_deep_cfg,
                    context_datetimes_train=context_datetimes_train,
                    external_test_size=len(te_idx),
                )
            r = run_single_kan_hybrid(
                kan_cfg, partner_spec, X_tr, y_tr, X_te, y_te,
                seed=seed, kan_label=kan_label,
                mode=spec.get("mode", "and"),
                alpha=float(spec.get("alpha", 0.5)),
                hybrid_threshold=float(spec.get("hybrid_threshold", 0.5)),
                metric_profile=metric_profile,
                X_forecast=X_fc, y_forecast=y_fc,
                forecast_indices=forecast_indices,
                context_datetimes_train=context_datetimes_train,
                external_test_size=len(te_idx),
                training_weight_cfg=training_weight_cfg,
                deep_preset_cfgs=deep_preset_cfgs,
                custom_deep_cfg=custom_deep_cfg,
                prefit_kan=kan_fit,
                prefit_partner=kan_partner_fit_cache[partner_key],
            )
            out.append(_finalize_trial_result(
                _attach_dataset_meta(r), metric_profile, mse_ref, kpi_weights,
                lcs_score=True,
            ))
    if feature_names is not None:
        for r in out:
            r.setdefault("extra", {})
            r["extra"]["feature_cols"] = feature_names
    return out


def _run_seed_job(job):
    configure_runtime_controls(job.get("runtime_max_iter"))
    if job["kind"] == "synthetic":
        return _run_synthetic_seed_trials(**job["kwargs"])
    return _run_dataset_seed_trials(**job["kwargs"])


def _collect_seed_jobs(jobs, total, progress_cb=None, n_jobs=1):
    n_jobs = min(_resolve_n_jobs(n_jobs), len(jobs))
    results_by_idx = {}
    done = 0
    if n_jobs <= 1:
        for idx, job in enumerate(jobs):
            seed_results = _run_seed_job(job)
            results_by_idx[idx] = seed_results
            for r in list(seed_results):
                done += 1
                if progress_cb:
                    extra_results = progress_cb(done, total, r)
                    if extra_results:
                        seed_results.extend(list(extra_results))
        return [r for idx in range(len(jobs)) for r in results_by_idx.get(idx, [])]

    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        future_to_idx = {
            executor.submit(_run_seed_job, job): idx
            for idx, job in enumerate(jobs)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            seed_results = future.result()
            results_by_idx[idx] = seed_results
            for r in list(seed_results):
                done += 1
                if progress_cb:
                    extra_results = progress_cb(done, total, r)
                    if extra_results:
                        seed_results.extend(list(extra_results))
    return [r for idx in range(len(jobs)) for r in results_by_idx.get(idx, [])]


def run_benchmark(task_name, banks, readouts, n_train, n_test, seeds,
                  noise_std=0.0, kpi_weights=None, progress_cb=None,
                  deep_presets=None, custom_deep_cfg=None, deep_preset_cfgs=None,
                  lcs_presets=None, custom_lcs_cfg=None, lcs_preset_cfgs=None,
                  kan_presets=None, kan_preset_cfgs=None,
                  metric_mode="auto", metric_threshold=None,
                  metric_prediction_threshold=None,
                  metric_score_mode="isolation",
                  training_weight_cfg=None, hybrid_specs=None,
                  kan_hybrid_specs=None,
                  trial_filter=None, n_jobs=1):
    deep_presets = deep_presets or []
    deep_preset_cfgs = deep_preset_cfgs or {}
    lcs_presets = lcs_presets or []
    lcs_preset_cfgs = lcs_preset_cfgs or {}
    kan_presets = kan_presets or []
    kan_preset_cfgs = kan_preset_cfgs or {}
    hybrid_specs = hybrid_specs or []
    kan_hybrid_specs = kan_hybrid_specs or []

    lcs_items = _lcs_cfg_items(lcs_presets, custom_lcs_cfg, lcs_preset_cfgs)
    kan_items = _kan_cfg_items(kan_presets, kan_preset_cfgs)
    total = len(seeds) * _trial_count(
        banks, readouts, deep_presets, custom_deep_cfg,
        lcs_items, hybrid_specs, trial_filter=trial_filter,
        kan_items=kan_items, kan_hybrid_specs=kan_hybrid_specs,
    )

    _, y_ref = generate_dataset(task_name, n_train, seed=seeds[0], noise_std=noise_std)
    mse_ref = float(np.var(y_ref)) + 1e-9
    metric_profile = resolve_metric_profile(
        y_ref, mode=metric_mode, threshold=metric_threshold,
        prediction_threshold=metric_prediction_threshold,
        score_mode=metric_score_mode,
    )

    jobs = []
    for seed in seeds:
        jobs.append({
            "kind": "synthetic",
            "runtime_max_iter": _RUNTIME_MAX_ITER,
            "kwargs": {
                "seed": seed,
                "task_name": task_name,
                "banks": banks,
                "readouts": readouts,
                "n_train": n_train,
                "n_test": n_test,
                "noise_std": noise_std,
                "kpi_weights": kpi_weights,
                "deep_presets": deep_presets,
                "custom_deep_cfg": custom_deep_cfg,
                "deep_preset_cfgs": deep_preset_cfgs,
                "lcs_items": lcs_items,
                "metric_profile": metric_profile,
                "training_weight_cfg": training_weight_cfg,
                "hybrid_specs": hybrid_specs,
                "kan_items": kan_items,
                "kan_hybrid_specs": kan_hybrid_specs,
                "trial_filter": trial_filter,
                "mse_ref": mse_ref,
            },
        })
    return _collect_seed_jobs(jobs, total, progress_cb=progress_cb, n_jobs=n_jobs)


def run_benchmark_dataset(X, y, dataset_name, banks, readouts, n_train, n_test, seeds,
                          kpi_weights=None, progress_cb=None,
                          deep_presets=None, custom_deep_cfg=None, deep_preset_cfgs=None,
                          lcs_presets=None, custom_lcs_cfg=None, lcs_preset_cfgs=None,
                          kan_presets=None, kan_preset_cfgs=None,
                          target_window_cfg=None, metric_mode="auto",
                          metric_threshold=None, metric_prediction_threshold=None,
                          metric_score_mode="isolation", context_datetimes=None,
                          forecast_indices=None, forecast_info=None,
                          training_weight_cfg=None, hybrid_specs=None,
                          kan_hybrid_specs=None,
                          trial_filter=None, n_jobs=1, feature_selection_cfg=None):
    deep_presets = deep_presets or []
    deep_preset_cfgs = deep_preset_cfgs or {}
    lcs_presets = lcs_presets or []
    lcs_preset_cfgs = lcs_preset_cfgs or {}
    kan_presets = kan_presets or []
    kan_preset_cfgs = kan_preset_cfgs or {}
    hybrid_specs = hybrid_specs or []
    kan_hybrid_specs = kan_hybrid_specs or []

    lcs_items = _lcs_cfg_items(lcs_presets, custom_lcs_cfg, lcs_preset_cfgs)
    kan_items = _kan_cfg_items(kan_presets, kan_preset_cfgs)
    total = len(seeds) * _trial_count(
        banks, readouts, deep_presets, custom_deep_cfg,
        lcs_items, hybrid_specs, trial_filter=trial_filter,
        kan_items=kan_items, kan_hybrid_specs=kan_hybrid_specs,
    )

    y = np.asarray(y, dtype=float)
    mse_ref = float(np.var(y)) + 1e-9
    metric_profile = resolve_metric_profile(
        y, mode=metric_mode, threshold=metric_threshold,
        prediction_threshold=metric_prediction_threshold,
        score_mode=metric_score_mode,
    )

    if target_window_cfg is None and n_train + n_test > len(X):
        raise ValueError(
            f"Richiesti n_train+n_test={n_train + n_test}, ma il CSV ha solo {len(X)} righe"
        )

    fixed_window = _resolve_target_window_indices(
        y, target_window_cfg, context_datetimes=context_datetimes
    )
    if target_window_cfg is not None and fixed_window is None:
        raise ValueError("Impossibile costruire la target window richiesta sul dataset")

    jobs = []
    X_arr = np.asarray(X, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    for seed in seeds:
        jobs.append({
            "kind": "dataset",
            "runtime_max_iter": _RUNTIME_MAX_ITER,
            "kwargs": {
                "seed": seed,
                "X": X_arr,
                "y": y_arr,
                "dataset_name": dataset_name,
                "banks": banks,
                "readouts": readouts,
                "n_train": n_train,
                "n_test": n_test,
                "kpi_weights": kpi_weights,
                "deep_presets": deep_presets,
                "custom_deep_cfg": custom_deep_cfg,
                "deep_preset_cfgs": deep_preset_cfgs,
                "lcs_items": lcs_items,
                "target_window_cfg": target_window_cfg,
                "metric_profile": metric_profile,
                "context_datetimes": context_datetimes,
                "forecast_indices": forecast_indices,
                "forecast_info": forecast_info,
                "training_weight_cfg": training_weight_cfg,
                "hybrid_specs": hybrid_specs,
                "kan_items": kan_items,
                "kan_hybrid_specs": kan_hybrid_specs,
                "trial_filter": trial_filter,
                "mse_ref": mse_ref,
                "feature_selection_cfg": feature_selection_cfg,
            },
        })
    return _collect_seed_jobs(jobs, total, progress_cb=progress_cb, n_jobs=n_jobs)


def _invert_predictions_array(y_true, y_pred, metric_profile=None):
    """Inverte y_pred preservando la forma. Per modalita' event ritorna 1-clip(y_pred).
    Per regressione: autoscale di y_pred sul range di y_true e specchio attorno
    al valor medio di [min, max]. Se y_true e' costante o vuoto fa flip nativo."""
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if metric_profile and (metric_profile.get("kind") == "event"):
        return np.clip(1.0 - yp, 0.0, 1.0)
    yt_finite = yt[np.isfinite(yt)] if yt.size else yt
    yp_finite = yp[np.isfinite(yp)] if yp.size else yp
    if yt_finite.size == 0 or yp_finite.size == 0:
        return -yp
    t_min, t_max = float(yt_finite.min()), float(yt_finite.max())
    p_min, p_max = float(yp_finite.min()), float(yp_finite.max())
    if abs(t_max - t_min) < 1e-12 or abs(p_max - p_min) < 1e-12:
        return yp.copy()
    yp_norm = (yp - p_min) / (p_max - p_min)
    yp_scaled = t_min + yp_norm * (t_max - t_min)
    return (t_max + t_min) - yp_scaled


def make_inverted_twin_result(result, metric_profile, kpi_weights=None,
                              mse_ref=1.0):
    """Costruisce un twin invertito di un trial: clona il result, inverte
    y_pred (test e forecast) e ricomputa metriche/kpi. Il bank diventa
    f"{bank}__INV". Ritorna None se artefatti mancanti."""
    import copy as _copy
    artifacts_in = (result or {}).get("_artifacts", {}) or {}
    y_true = artifacts_in.get("y_true_test")
    y_pred = artifacts_in.get("y_pred_test")
    if y_true is None or y_pred is None or len(y_true) == 0 or len(y_pred) == 0:
        return None
    twin = _copy.deepcopy(result)
    artifacts = twin.setdefault("_artifacts", {})
    y_pred_inv = _invert_predictions_array(y_true, y_pred, metric_profile)
    artifacts["y_pred_test"] = np.asarray(y_pred_inv, dtype=float)

    y_pred_fc = artifacts_in.get("y_pred_forecast")
    if y_pred_fc is not None:
        y_pred_fc_inv = _invert_predictions_array(y_true, y_pred_fc, metric_profile)
        artifacts["y_pred_forecast"] = np.asarray(y_pred_fc_inv, dtype=float)

    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred_inv, dtype=float)
    twin["mse_test"] = float(mean_squared_error(y_true_arr, y_pred_arr))
    twin["mae_test"] = float(mean_absolute_error(y_true_arr, y_pred_arr))
    twin["r2"] = float(r2_score(y_true_arr, y_pred_arr))
    new_extra = _extra_metrics(y_true_arr, y_pred_arr, metric_profile=metric_profile)
    preserved = ("ranking_weight", "backtest_info", "recent_validation_info",
                 "forecast_info", "split_info", "preprocessing", "deep_cfg",
                 "lcs_cfg", "hybrid_cfg", "hybrid_cache",
                 "kan_cfg", "kan_hybrid_cfg",
                 "training_sample_weighting", "validation_info", "retrain_info",
                 "dataset_path", "target_col", "feature_cols", "skip_cols")
    for k in preserved:
        if k in (twin.get("extra", {}) or {}):
            new_extra[k] = twin["extra"][k]
    twin["extra"] = new_extra
    twin["extra"]["inverted_twin"] = True
    twin["extra"]["inverted_from"] = result.get("bank")

    bank = result.get("bank", "")
    if not str(bank).endswith("__INV"):
        twin["bank"] = f"{bank}__INV"

    twin["overall_kpi"], score_components = compute_overall_score(
        twin, metric_profile, mse_ref=mse_ref, weights=kpi_weights
    )
    twin["extra"]["score_components"] = score_components
    twin["extra"]["score_kind"] = metric_profile["kind"]
    twin["extra"]["score_label"] = metric_profile["score_label"]
    return twin


def aggregate_results(results):
    from collections import defaultdict
    groups = defaultdict(list)
    for r in results:
        groups[(r["bank"], r["readout"])].append(r)

    def _weights(runs):
        values = [
            float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
            for r in runs
        ]
        return np.asarray(values, dtype=float)

    def _weighted_mean(values, weights):
        values = np.asarray(values, dtype=float)
        if values.size == 0:
            return 0.0
        if weights.size != values.size or np.sum(weights) <= 0:
            return float(np.mean(values))
        return float(np.average(values, weights=weights))

    def _weighted_std(values, weights):
        values = np.asarray(values, dtype=float)
        if values.size == 0:
            return 0.0
        if weights.size != values.size or np.sum(weights) <= 0:
            return float(np.std(values))
        mean = np.average(values, weights=weights)
        return float(np.sqrt(np.average((values - mean) ** 2, weights=weights)))

    agg = []
    for (bank, readout), runs in groups.items():
        weights = _weights(runs)
        agg.append({
            "bank": bank, "readout": readout,
            "mse_test_mean":  _weighted_mean([r["mse_test"] for r in runs], weights),
            "mse_test_std":   _weighted_std([r["mse_test"] for r in runs], weights),
            "mae_test_mean":  _weighted_mean([r.get("mae_test", 0.0) for r in runs], weights),
            "r2_mean":        _weighted_mean([r["r2"] for r in runs], weights),
            "kpi_mean":       _weighted_mean([r["overall_kpi"] for r in runs], weights),
            "kpi_std":        _weighted_std([r["overall_kpi"] for r in runs], weights),
            "inference_us":   _weighted_mean([r["inference_time_us"] for r in runs], weights),
            "train_s":        _weighted_mean([r["train_time_s"] for r in runs], weights),
            "n_params":       int(_weighted_mean([r["n_effective_params"] for r in runs], weights)),
            "n_seeds":        len(runs),
            "weight_sum":     float(np.sum(weights)),
            "weighted_ranking": bool(np.any(np.abs(weights - weights[0]) > 1e-12)),
            "target_mode":    runs[0].get("extra", {}).get("target_mode", "regression"),
            "score_kind":     runs[0].get("extra", {}).get("score_kind", "regression"),
            "score_label":    runs[0].get("extra", {}).get("score_label", "regression_composite"),
        })
        for key in ("event_precision", "event_recall", "event_f1",
                    "event_bal_acc", "event_specificity"):
            values = [r.get("extra", {}).get(key) for r in runs if key in r.get("extra", {})]
            if values:
                metric_weights = np.asarray([
                    float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
                    for r in runs if key in r.get("extra", {})
                ], dtype=float)
                agg[-1][f"{key}_mean"] = _weighted_mean(values, metric_weights)
        values = [r.get("extra", {}).get("positive_mae") for r in runs
                  if r.get("extra", {}).get("positive_mae") is not None]
        if values:
            metric_weights = np.asarray([
                float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
                for r in runs if r.get("extra", {}).get("positive_mae") is not None
            ], dtype=float)
            agg[-1]["positive_mae_mean"] = _weighted_mean(values, metric_weights)
        score_keys = set()
        for r in runs:
            score_keys.update(r.get("extra", {}).get("score_components", {}).keys())
        for key in sorted(score_keys):
            values = [r.get("extra", {}).get("score_components", {}).get(key)
                      for r in runs if key in r.get("extra", {}).get("score_components", {})]
            if values:
                metric_weights = np.asarray([
                    float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
                    for r in runs if key in r.get("extra", {}).get("score_components", {})
                ], dtype=float)
                agg[-1][f"score_{key}_mean"] = _weighted_mean(values, metric_weights)
    agg.sort(key=lambda r: -r["kpi_mean"])
    return agg


def significance(agg):
    if len(agg) < 2:
        return True
    w, r2 = agg[0], agg[1]
    return (w["kpi_mean"] - w["kpi_std"]) > (r2["kpi_mean"] + r2["kpi_std"])

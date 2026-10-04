"""Reference joint-study fusion mathematics, generalized to N inner events.

Uses the same peak/depression strategies, 11 alpha values, 91 centers,
seven temperatures and composite objective as fusion.py. All searches use
inner data; the recent outer validation is evaluated without fitting.
"""
from __future__ import annotations
import numpy as np


def event_windows(y, radius=13):
    centers = np.flatnonzero(np.asarray(y) == 1)
    return [(i, np.arange(max(0, i-radius), min(len(y), i+radius+1))) for i in centers]


def profile(y, score):
    y, score = np.asarray(y, int), np.asarray(score, float)
    windows = event_windows(y)
    errors = [abs(int(indices[np.argmax(score[indices])]) - i) for i, indices in windows]
    centered = [score[i] >= .7 and error == 0 for (i, _), error in zip(windows, errors)]
    calm = score[y == 0]
    return {"hit_rate": float(np.mean(centered)), "timing_error": float(np.mean(errors)),
            "minimum_event_score": float(score[y == 1].min()), "sparsity": float(np.mean(calm < .05)),
            "calm_mean": float(calm.mean()), "false_positives": int(np.sum(calm >= .7))}


def strategy(matrix, weights, name):
    if name == "weighted_mean": return np.asarray(weights) @ matrix
    if name == "specialist_envelope": return matrix.max(axis=0)
    if name == "specialist_q90": return np.quantile(matrix, .9, axis=0)
    if name == "depression_floor": return matrix.min(axis=0)
    if name == "depression_q10": return np.quantile(matrix, .1, axis=0)
    raise ValueError(name)


def apply_reference_fusion(matrix, specification):
    peak = strategy(matrix, specification["peak_weights"], specification["peak_strategy"])
    calm = strategy(matrix, specification["calm_weights"], specification["calm_strategy"])
    raw = specification["alpha"] * peak + (1-specification["alpha"]) * calm
    return np.clip(1 / (1 + np.exp(-np.clip((raw-specification["center"]) / specification["temperature"], -30, 30))), .001, .999)


def fit_reference_fusion(y, matrix):
    y, matrix = np.asarray(y, int), np.asarray(matrix, float)
    if set(np.unique(y)) != {0, 1}: raise ValueError("Fusion requires both event and non-event inner samples")
    profiles = [profile(y, p) for p in matrix]
    wp = np.array([max(.1, .25 + 4*p["hit_rate"] + p["minimum_event_score"] - .1*p["timing_error"]) for p in profiles])
    wc = np.array([max(.1, .25 + 5*p["sparsity"] - .15*p["false_positives"] - 3*p["calm_mean"]) for p in profiles])
    wp /= wp.sum(); wc /= wc.sum()
    centers = np.linspace(.05, .95, 91)
    windows = event_windows(y)
    best = None
    for peak_name in ["weighted_mean", "specialist_envelope", "specialist_q90"]:
      peak = strategy(matrix, wp, peak_name)
      for calm_name in ["weighted_mean", "depression_floor", "depression_q10"]:
       calm = strategy(matrix, wc, calm_name)
       for alpha in np.linspace(0, 1, 11):
        raw = alpha*peak + (1-alpha)*calm
        for temperature in [.015, .025, .04, .06, .09, .14, .22]:
            p = 1 / (1 + np.exp(-np.clip((raw[None,:] - centers[:,None]) / temperature, -30, 30)))
            background = p[:,y == 0]
            errors = np.stack([np.abs(indices[np.argmax(p[:,indices], axis=1)] - i) for i,indices in windows], axis=1)
            event_p = p[:,y == 1]
            centered = ((event_p >= .7) & (errors == 0)).sum(axis=1)
            sparsity = (background < .05).mean(axis=1)
            calm_mean = background.mean(axis=1)
            fp = (background >= .7).sum(axis=1)
            loss = 6*(1-centered/len(windows)) + 5*(1-sparsity) + 2*calm_mean + 2*((1-event_p)**2).mean(axis=1) + .1*errors.mean(axis=1) + .1*fp
            for index in np.argsort(loss)[:1]:
                key = (float(loss[index]), -int(centered[index]), -float(sparsity[index]), float(calm_mean[index]))
                if best is None or key < best[0]:
                    best = (key, {"alpha": float(alpha), "center": float(centers[index]), "temperature": temperature,
                            "peak_strategy": peak_name, "calm_strategy": calm_name,
                            "peak_weights": wp.tolist(), "calm_weights": wc.tolist(), "inner_loss": float(loss[index]),
                            "inner_event_count": len(windows), "kind": "reference_parametric_asymmetric_fusion"})
    return best[1]

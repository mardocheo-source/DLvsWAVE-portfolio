"""Chronological adapters for the joint production model families.

The original run-specific entry points retain their historical contracts. These
adapters reuse their model implementations with explicit split boundaries.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, log_loss, roc_auc_score
from sklearn.preprocessing import MinMaxScaler

from uncompressed_pipeline.l1_engine import train_eval_trial_lcs, train_eval_trial_torch, temporal_shift_probability, get_pi_infill_seed, enforce_causal_guard
from uncompressed_pipeline.l2_meta_engine import DeepMetaSurrogate
from uncompressed_pipeline.spatial_multitarget_engine import SpatialDiscreteNet
from src.models.kan import KANNetwork
from uncompressed_pipeline.nested_data import atomic_json, timestamp, assign_zones
from uncompressed_pipeline.nested_reference_fusion import fit_reference_fusion, apply_reference_fusion
from uncompressed_pipeline.intensity_magnitude_spectrum import reference_potential_spectrum


class ModelBudgetExceeded(RuntimeError):
    pass


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise ModelBudgetExceeded("node_compute_budget_exhausted")


def binary_metrics(actual, score, threshold=0.7):
    actual, score = np.asarray(actual, int), np.asarray(score, float)
    hit = score >= threshold
    tp, fp = int(np.sum(hit & (actual == 1))), int(np.sum(hit & (actual == 0)))
    fn, tn = int(np.sum(~hit & (actual == 1))), int(np.sum(~hit & (actual == 0)))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": tp / max(1, tp + fn),
            "false_alarm_fraction": fp / max(1, fp + tn), "precision": tp / max(1, tp + fp),
            "brier_score": float(np.mean((score - actual) ** 2)),
            "roc_auc": float(roc_auc_score(actual, score)) if len(np.unique(actual)) == 2 else None,
            "samples": len(actual), "threshold": threshold}


def spatial_metrics(actual, score, centers, frame, majority_class):
    predicted = np.argmax(score, axis=1)
    xyz = np.asarray(centers)[predicted]
    from uncompressed_pipeline.nested_data import unit_vectors
    distance = np.arccos(np.clip(np.sum(unit_vectors(frame.latitude, frame.longitude) * xyz, axis=1), -1, 1)) * 6371.0088
    accuracy = float(accuracy_score(actual, predicted))
    majority = float(np.mean(np.asarray(actual) == majority_class))
    return {"samples": len(actual), "distinct_slots": int(frame.slot.nunique()),
            "represented_zones": len(np.unique(actual)), "accuracy": accuracy,
            "macro_f1": float(f1_score(actual, predicted, labels=np.arange(len(centers)), average="macro", zero_division=0)),
            "mean_centroid_distance_km": float(distance.mean()), "median_centroid_distance_km": float(np.median(distance)),
            "majority_baseline_accuracy": majority, "skill_over_majority": accuracy - majority,
            "log_loss": float(log_loss(actual, np.clip(score, 1e-8, 1), labels=np.arange(len(centers))))}


def make_energy_frame(astro, events, split, config):
    frame = astro.copy()
    reference = timestamp(config["reference_date"])
    frame["role"] = np.where(frame.date >= reference, "forecast", "training")
    complete = frame.date + pd.Timedelta(days=config["interval_days"]) <= reference
    # Exclude a partially observed current interval, do not call it negative.
    frame = frame.loc[complete | (frame.role == "forecast")].copy()
    positive_slots = set(events.loc[events.mag >= split["threshold"], "slot"])
    frame["target"] = frame.date.isin(positive_slots).astype(float)
    frame.loc[frame.role == "forecast", "target"] = np.nan
    frame.loc[(frame.date >= timestamp(split["validation_start"])) & (frame.role != "forecast"), "role"] = "validation"
    return frame.reset_index(drop=True)


def make_spatial_frame(astro, events, split, zones, config):
    eligible = events.loc[(events.mag >= split["threshold"]) & events.complete_slot].copy()
    eligible["target"] = assign_zones(eligible, zones["centers"])
    merged = eligible.merge(astro, left_on="slot", right_on="date", how="left", validate="many_to_one")
    features = [c for c in astro if c.startswith("astro_")]
    if merged[features].isna().any().any():
        raise ValueError("event_has_no_astronomical_slot")
    merged["role"] = np.where(merged.slot >= timestamp(split["validation_start"]), "validation", "training")
    # No row is introduced for a historical interval without events.
    future = astro.loc[astro.date >= timestamp(config["reference_date"])].copy()
    future["target"], future["role"] = np.nan, "forecast"
    return pd.concat([merged, future], ignore_index=True).sort_values("date").reset_index(drop=True)


def inner_boundary(frame, config):
    train = frame.loc[frame.role == "training"]
    positives = train.loc[train.target > 0.5] if "slot" not in frame else train
    dates = sorted(positives.date.unique())
    n = config["validation"]["inner_events"]
    if len(dates) <= n:
        raise ValueError("insufficient_inner_training_events")
    return pd.Timestamp(dates[-n])


def sample_params(rng, family, dimension):
    params = {"feature_count": int(rng.choice([n for n in [8, 12, 16, 24, 32, 48, 64] if n <= dimension] or [dimension])),
              "learning_rate": float(rng.choice([0.0003, 0.0007, 0.0015, 0.003])),
              "hidden_dim": int(rng.choice([32, 64, 128])), "num_layers": int(rng.choice([2, 3, 4])),
              "dropout": float(rng.choice([0.05, 0.1, 0.2])), "grid_size": int(rng.choice([3, 5, 7])),
              "spline_order": int(rng.choice([2, 3])), "population_size": int(rng.choice([80, 150, 250])),
              "crossover_rate": float(rng.choice([.6, .8])), "mutation_rate": float(rng.choice([.02, .04, .08])),
              "logit_temperature": float(rng.choice([.12, .20, .35, .60, 1.])),
              "logit_bias": float(rng.choice([0., .4, .8, 1.2, 1.6])),
              "rule_center": float(rng.choice([.45, .52, .58, .64, .70, .76, .82])),
              "rule_temperature": float(rng.choice([.02, .035, .05, .08, .12])),
              "temporal_projection_shift_weeks": int(rng.integers(-13, 14)),
              "train_start_year": int(rng.choice([1900, 1920, 1940, 1960])),
              "window_before": int(rng.choice([2, 3, 5, 7, 13])),
              "window_after": int(rng.choice([2, 3, 5, 7, 13])),
              "background_ratio": float(rng.choice([.02, .04, .06, .10, .15])),
              "mask_strategy": str(rng.choice(["ranked", "ranked_mutated", "random"]))}
    params["features"] = sorted(rng.choice(dimension, params["feature_count"], replace=False).tolist())
    params["feature_dimension"] = dimension
    return params


def encoded(params, family):
    return [float(family == f) for f in ["kan", "deep_learning", "lcs"]] + [params["feature_count"] / 40,
        params["learning_rate"] / 0.003, params["hidden_dim"] / 64, params["num_layers"] / 3,
        params["dropout"] / 0.1, params["grid_size"] / 5, params["population_size"] / 160,
        params["logit_temperature"], params["logit_bias"] / 1.6, params["rule_center"], params["rule_temperature"] / .12,
        params["temporal_projection_shift_weeks"] / 13, (params["train_start_year"]-1900)/60,
        params["window_before"]/13, params["window_after"]/13, params["background_ratio"]/.15] + [float(i in params["features"]) for i in range(params["feature_dimension"])]


def sample_training(frame, params, component, seed, config):
    active = frame.loc[frame.date >= pd.Timestamp(year=params["train_start_year"], month=1, day=1)].copy()
    if component == "location":
        if active.id.isna().any(): raise ValueError("Spatial training contains a non-event filler")
        return active
    pos = active.loc[active.target == 1]
    if len(pos) < 3: raise ValueError("Insufficient events after candidate history truncation")
    context = np.zeros(len(active), bool)
    for date in pos.date:
        context |= active.date.between(date-pd.Timedelta(days=config["interval_days"]*params["window_before"]),
                                      date+pd.Timedelta(days=config["interval_days"]*params["window_after"])).to_numpy()
    calm = active.loc[active.target == 0].sample(frac=params["background_ratio"], random_state=get_pi_infill_seed(seed))
    return pd.concat([active.loc[context], calm]).drop_duplicates("date").sort_values("date")


def fit_family(family, train, evaluation, future, features, params, component, classes, config, seed):
    train = sample_training(train, params, component, seed, config)
    active = [features[i] for i in params["features"]]
    scaler = MinMaxScaler().fit(train[active])
    xtr, xev, xfu = [np.clip(scaler.transform(f[active]), 0, 1).astype(np.float32) for f in (train, evaluation, future)]
    ytr, yev = train.target.to_numpy(int), evaluation.target.to_numpy(int)
    if component == "energy":
        if len(np.unique(ytr)) != 2:
            raise ValueError("energy_training_requires_events_and_negatives")
        if family == "lcs":
            ptr, ev, fu, artifact = train_eval_trial_lcs(xtr, ytr, xev, xfu, params, seed)
        else:
            ptr, ev, fu, artifact = train_eval_trial_torch(family, xtr, ytr, xev, yev, xfu, params,
                                                     epochs=config["models"]["epochs"], seed=seed)
    elif family == "lcs":
        predictions, artifacts = [], []
        for zone in range(classes):
            _, pe, pf, art = train_eval_trial_lcs(xtr, (ytr == zone).astype(int), xev, xfu, params, seed + zone)
            predictions.append((pe, pf)); artifacts.append(art)
        ev, fu = [np.stack([p[i] for p in predictions], axis=1) for i in [0, 1]]
        ev /= ev.sum(axis=1, keepdims=True); fu /= fu.sum(axis=1, keepdims=True)
        artifact = {"kind": "event_only_lcs_one_vs_rest", "classes": artifacts}
    else:
        torch.manual_seed(seed)
        if family == "kan":
            net = KANNetwork(in_dim=len(active), out_dim=classes, hidden_dims=(32, 16),
                             grid_size=params["grid_size"], spline_order=params["spline_order"])
            xtr, xev, xfu = [(x * 1.8) - .9 for x in [xtr, xev, xfu]]
        else:
            net = SpatialDiscreteNet(len(active), classes, params["hidden_dim"], params["num_layers"], params["dropout"])
        counts = np.bincount(ytr, minlength=classes)
        weights = torch.tensor((1 / np.maximum(counts, 1)).astype(np.float32))
        optimizer = torch.optim.AdamW(net.parameters(), lr=params["learning_rate"], weight_decay=1e-4)
        criterion = torch.nn.CrossEntropyLoss(weight=weights)
        net.train()
        tx, ty = torch.tensor(xtr), torch.tensor(ytr, dtype=torch.long)
        for _ in range(config["models"]["epochs"]):
            optimizer.zero_grad(); loss = criterion(net(tx), ty); loss.backward(); optimizer.step()
        net.eval()
        with torch.no_grad():
            ev = torch.softmax(net(torch.tensor(xev)), -1).numpy()
            fu = torch.softmax(net(torch.tensor(xfu)), -1).numpy()
        artifact = {"kind": "torch", "model_type": family, "classes": classes, "state_dict": net.state_dict()}
    if component == "energy":
        shift = enforce_causal_guard(active, int(params["temporal_projection_shift_weeks"]))
        ev, fu = temporal_shift_probability(np.atleast_1d(ev), shift), temporal_shift_probability(np.atleast_1d(fu), shift)
        p = np.clip(ptr, 1e-7, 1-1e-7)
        focal = np.mean(-(ytr*.75*(1-p)**2*np.log(p) + (1-ytr)*.25*p**2*np.log(1-p)))
        artifact["train_loss"] = float(focal + 2*(1-np.mean(p[ytr == 1] >= .7)) + 1-np.mean(p[ytr == 0] < .05))
    if not np.isfinite(ev).all() or not np.isfinite(fu).all():
        raise ValueError("nonfinite_model_predictions")
    if component == "location":
        ev, fu = [np.asarray(a, dtype=np.float64) for a in (ev, fu)]
        ev /= ev.sum(axis=1, keepdims=True)
        fu /= fu.sum(axis=1, keepdims=True)
    artifact.update({"feature_names": active, "scaler_min": scaler.min_.tolist(), "scaler_scale": scaler.scale_.tolist(),
                     "params": params, "seed": seed, "component": component,
                     "train_end": str(train.date.max()), "train_rows": len(train)})
    return np.atleast_1d(ev), np.atleast_1d(fu), artifact


def selection_loss(actual, score, component, classes, train_loss=0.):
    if component == "energy":
        y = np.asarray(actual, int)
        from uncompressed_pipeline.nested_reference_fusion import profile
        p = np.clip(score, 1e-7, 1-1e-7)
        metrics = profile(y, p)
        focal = np.mean(-(y*.75*(1-p)**2*np.log(p) + (1-y)*.25*p**2*np.log(1-p)))
        return float(5*(1-metrics["hit_rate"]) + 4*(1-metrics["sparsity"]) + 3*np.mean((1-p[y == 1])**2) +
                     2*metrics["calm_mean"] + 1.5*focal + 2.5*metrics["false_positives"]/max(1,np.sum(y == 0)) + .15*metrics["timing_error"] + .10*train_loss)
    return float(log_loss(actual, np.clip(score, 1e-8, 1), labels=np.arange(classes)))


def fusion_weights(inner_y, matrix, component):
    if component == "location":
        losses = [log_loss(inner_y, np.clip(p, 1e-8, 1), labels=np.arange(matrix.shape[2])) for p in matrix]
        weights = 1 / np.maximum(losses, 1e-5)
        return {"weights": (weights / weights.sum()).tolist(), "kind": "inner_loss_weighted_zone_scores"}
    # Preserve separate peak and depression specialists from the reference family.
    y = np.asarray(inner_y, int)
    peak = np.maximum(.1, .25 + 4 * (matrix[:, y == 1] >= .7).mean(axis=1) + matrix[:, y == 1].min(axis=1))
    calm = np.maximum(.1, .25 + 5 * (matrix[:, y == 0] < .05).mean(axis=1) - 3 * matrix[:, y == 0].mean(axis=1))
    peak, calm = peak / peak.sum(), calm / calm.sum()
    candidates = []
    for alpha in np.linspace(0, 1, 11):
        weight = alpha * peak + (1 - alpha) * calm
        score = weight @ matrix
        candidates.append((selection_loss(y, score, component, 2), float(alpha), weight))
    loss, alpha, weight = min(candidates, key=lambda v: v[0])
    return {"weights": weight.tolist(), "kind": "inner_selected_peak_depression_fusion", "alpha": alpha,
            "peak_weights": peak.tolist(), "depression_weights": calm.tolist(), "inner_loss": loss}


def run_branch(frame, config, component, directory, deadline, zones=None):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    features = [c for c in frame if c.startswith("astro_")]
    train = frame.loc[frame.role == "training"].copy()
    val = frame.loc[frame.role == "validation"].copy()
    future = frame.loc[frame.role == "forecast"].copy()
    if min(len(train), len(val), len(future)) == 0:
        raise ValueError("empty_training_validation_or_forecast_partition")
    boundary = inner_boundary(frame, config)
    inner_train, inner_val = train.loc[train.date < boundary], train.loc[train.date >= boundary]
    classes = 2 if component == "energy" else zones["count"]
    if component == "energy" and inner_val.target.nunique() != 2:
        raise ValueError("inner_energy_validation_lacks_positive_or_negative_class")
    records, fitted = [], []
    rng = np.random.default_rng(config["models"]["seed"])
    families = config["models"]["families"]
    search_deadline = time.monotonic() + .60 * max(0, deadline - time.monotonic())
    study_root = next((p for p in directory.parents if (p / "study_config.json").exists()), directory)

    def progress(message):
        line = f"{pd.Timestamp.now(tz='UTC').isoformat()} | {directory.parent.parent.name} | {component} | {directory.name} | {message}"
        print(line, flush=True)
        (study_root / "PROGRESS.md").write_text("# Live progress\n\n" + line + "\n\nSee execution.log and each branch trial_history.json / trials.csv.\n")
        with (study_root / "execution.log").open("a") as stream: stream.write(line + "\n")

    def trial(family, params, stage):
        check_deadline(deadline)
        trial_id = len(records)
        seed = config["models"]["seed"] + trial_id
        if params["mask_strategy"] != "random":
            x = inner_train[features].to_numpy(float)
            labels = inner_train.target.to_numpy(int)
            between = np.stack([x[labels == c].mean(axis=0) for c in np.unique(labels)])
            ranks = np.std(between, axis=0) / (x.std(axis=0) + 1e-6) + rng.uniform(0, .03, len(features))
            selected = np.argsort(ranks)[-params["feature_count"]:]
            if params["mask_strategy"] == "ranked_mutated":
                remaining = np.setdiff1d(np.arange(len(features)), selected)
                count = min(len(remaining), max(1, len(selected)//4))
                selected[:count] = rng.choice(remaining, count, replace=False)
            params["features"] = sorted(selected.tolist())
        try:
            ev, _, art = fit_family(family, inner_train, inner_val, future, features, params, component, classes, config, seed)
            loss = selection_loss(inner_val.target, ev, component, classes, art.get("train_loss", 0.))
            status = "completed"
        except ValueError as error:
            ev, loss, status = None, 999., f"rejected: {error}"
        row = {"trial": trial_id, "family": family, "stage": stage, "inner_loss": loss, "params": params, "seed": seed, "status": status}
        records.append(row); fitted.append(ev)
        atomic_json(directory / "trial_history.json", records)
        csv_rows = [{**{k:v for k,v in r.items() if k != 'params'}, **{f"hp_{k}":v for k,v in r["params"].items() if k != "features"},
                     **{f"feature__{name}": int(i in r["params"]["features"]) for i,name in enumerate(features)}} for r in records]
        pd.DataFrame(csv_rows).to_csv(directory / "trials.csv", index=False)
        progress(f"trial {trial_id+1} | {stage} | {family} | {params['feature_count']} features | inner loss {loss:.5f} | {status}")
        return row

    for round_index in range(config["models"]["trials_per_family"]):
        if round_index and time.monotonic() >= search_deadline: break
        for family in families:
            trial(family, sample_params(rng, family, len(features)), "model_L1")
    # Reuse the reference deep surrogate to select refinement candidates using inner loss only.
    torch.manual_seed(config["models"]["seed"])
    surrogate = DeepMetaSurrogate(len(encoded(records[0]["params"], records[0]["family"])), hidden_dim=32)
    successful = [r for r in records if r["status"] == "completed"]
    if not successful: raise ValueError("No viable model after broad candidate search")
    xx = torch.tensor([encoded(r["params"], r["family"]) for r in successful], dtype=torch.float32)
    yy = torch.tensor([r["inner_loss"] for r in successful], dtype=torch.float32).reshape(-1, 1)
    optimizer = torch.optim.Adam(surrogate.parameters(), lr=.003)
    for _ in range(config["models"]["surrogate_epochs"]):
        optimizer.zero_grad(); loss = torch.nn.functional.mse_loss(surrogate(xx), yy); loss.backward(); optimizer.step()
    pool = [(family, sample_params(rng, family, len(features))) for family in families for _ in range(max(12, config["models"]["meta_trials"] * 4))]
    surrogate.eval()
    with torch.no_grad():
        predicted = surrogate(torch.tensor([encoded(p, f) for f, p in pool], dtype=torch.float32)).ravel().numpy()
    for idx in np.argsort(predicted)[:config["models"]["meta_trials"]]:
        if any(r["stage"] == "model_L2" for r in records) and time.monotonic() >= search_deadline: break
        family, params = pool[idx]; trial(family, params, "model_L2")
    torch.save(surrogate.state_dict(), directory / "meta_surrogate.pt")
    winners = []
    for stage in ["model_L1", "model_L2"]:
        for family in families:
            candidates = [r for r in records if r["stage"] == stage and r["family"] == family and r["status"] == "completed"]
            if candidates: winners.append(min(candidates, key=lambda r: r["inner_loss"]))
    inner_predictions = np.stack([fitted[r["trial"]] for r in winners])
    if component == "energy":
        l1_indices = [i for i,r in enumerate(winners) if r["stage"] == "model_L1"]
        l2_indices = [i for i,r in enumerate(winners) if r["stage"] == "model_L2"]
        if not l2_indices: raise ValueError("No completed L2 refinement; cannot fabricate a multilevel forecast")
        fusion_l1 = fit_reference_fusion(inner_val.target, inner_predictions[l1_indices])
        fusion_l2 = fit_reference_fusion(inner_val.target, inner_predictions[l2_indices])
        stage_inner = np.stack([apply_reference_fusion(inner_predictions[l1_indices], fusion_l1), apply_reference_fusion(inner_predictions[l2_indices], fusion_l2)])
        fusion_l3 = fit_reference_fusion(inner_val.target, stage_inner)
        fusion = {"kind": "reference_L1_L2_L3", "l1": fusion_l1, "l2": fusion_l2, "l3": fusion_l3}
    else:
        fusion = fusion_weights(inner_val.target.to_numpy(int), inner_predictions, component)
    outer_predictions, future_predictions = [], []
    full_train = frame.loc[frame.role != "forecast"].copy()
    for winner in winners:
        progress(f"Refitting selected {winner['stage']} / {winner['family']} trial {winner['trial']} for outer validation and future")
        check_deadline(deadline)
        ev, _, artifact = fit_family(winner["family"], train, val, future, features, winner["params"], component, classes, config, winner["seed"])
        torch.save(artifact, directory / f"{winner['family']}_outer_model.pt")
        check_deadline(deadline)
        # The prospective refit is distinct; outer predictions are never recomputed with this model.
        _, fu, artifact = fit_family(winner["family"], full_train, val, future, features, winner["params"], component, classes, config, winner["seed"])
        torch.save(artifact, directory / f"{winner['family']}_prospective_model.pt")
        outer_predictions.append(ev); future_predictions.append(fu)
    if component == "energy":
        all_ev, all_fu = np.stack(outer_predictions), np.stack(future_predictions)
        ev1, ev2 = apply_reference_fusion(all_ev[l1_indices], fusion_l1), apply_reference_fusion(all_ev[l2_indices], fusion_l2)
        fu1, fu2 = apply_reference_fusion(all_fu[l1_indices], fusion_l1), apply_reference_fusion(all_fu[l2_indices], fusion_l2)
        ev = apply_reference_fusion(np.stack([ev1, ev2]), fusion_l3)
        fu = apply_reference_fusion(np.stack([fu1, fu2]), fusion_l3)
        for stage, score in [("03_level1_fusion", fu1), ("04_level2_deep_meta_optimizer/level2_fusion", fu2), ("05_level3_final_fusion", fu)]:
            destination = directory / stage; destination.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"date": future.date, "predicted_prob": score}).to_csv(destination / "compound_prospective_forecast.csv", index=False)
        activation, potential = reference_potential_spectrum(fu1, fu2, fu)
        spectrum = pd.DataFrame({"date": future.date, "score_l1": fu1, "score_l2": fu2, "score_l3": fu,
                                 "activation_density": activation, "potential_magnitude_ceiling_up_to": potential})
        spectrum.to_csv(directory / "prospective_energy_magnitude_spectrum.csv", index=False)
    else:
        weight = np.asarray(fusion["weights"])
        ev = np.tensordot(weight, np.stack(outer_predictions), axes=1)
        fu = np.tensordot(weight, np.stack(future_predictions), axes=1)
    val_output = val[[c for c in ["date", "id", "mag", "latitude", "longitude", "slot", "target"] if c in val]].copy()
    future_output = future[["date"]].copy()
    names = ["score"] if component == "energy" else [f"zone_score_{i}" for i in range(classes)]
    for i, name in enumerate(names):
        val_output[name] = ev if component == "energy" else ev[:, i]
        future_output[name] = fu if component == "energy" else fu[:, i]
    val_output.to_csv(directory / "validation_predictions.csv", index=False)
    future_output.to_csv(directory / "forecast_predictions.csv", index=False)
    frame.to_csv(directory / "model_master.csv", index=False)
    majority = int(train.target.value_counts().index[0])
    metrics = binary_metrics(val.target, ev, config["quality"]["energy_score_threshold"]) if component == "energy" else spatial_metrics(val.target, ev, zones["centers"], val, majority)
    summary = {"component": component, "features": features, "training_rows": len(train), "validation_rows": len(val),
               "inner_training_end": str(inner_train.date.max()), "inner_validation_start": str(boundary),
               "outer_training_end": str(train.date.max()), "outer_validation_start": str(val.date.min()),
               "outer_validation_end": str(val.date.max()), "prospective_training_end": str(full_train.date.max()),
               "winners": winners, "fusion": fusion, "metrics": metrics, "majority_class": majority,
               "score_semantics": "Uncalibrated model score; spatial outputs conditional on an eligible event.",
               "spatial_training_without_calm": component == "location"}
    atomic_json(directory / "summary.json", summary)
    return {"validation": val_output, "forecast": future_output, "summary": summary}

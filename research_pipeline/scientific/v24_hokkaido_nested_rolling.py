#!/usr/bin/env python3
"""Nested rolling-origin Hokkaido search with a train-heavy final validation split."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import v21_weekly_recency_forecast as core
import v23_hokkaido_extended_search as ext


def build_data(astro: Path, japan_path: Path, world_path: Path):
    core.BOUNDS = ext.REGION
    core.ZONE_MODE = "hokkaido_corridor"
    master = pd.read_csv(astro, low_memory=False).sort_values("date").reset_index(drop=True)
    master["date"] = pd.to_datetime(master.date)
    X, names = core.transformed_features(master)
    japan = core.load_catalog(japan_path)
    world = core.load_catalog(world_path)
    inside = japan.latitude.between(ext.REGION[0], ext.REGION[1]) & japan.longitude.between(ext.REGION[2], ext.REGION[3])
    if "timing_region_member" in japan:
        inside |= pd.to_numeric(japan.timing_region_member, errors="coerce").fillna(0).eq(1)
    targets = core.strongest_by_slot(japan.loc[(japan.mag >= 7.9) & inside].copy())
    outside = ~(world.latitude.between(ext.REGION[0], ext.REGION[1]) & world.longitude.between(ext.REGION[2], ext.REGION[3]))
    hard_events = core.strongest_by_slot(world.loc[outside & (world.mag >= 7.9)].copy())
    date_to_index = {pd.Timestamp(date): i for i, date in enumerate(master.date)}
    y = np.zeros(len(master), int)
    for slot in targets.slot_start:
        y[date_to_index[pd.Timestamp(slot)]] = 1
    hard_by_slot = hard_events.loc[~hard_events.slot_start.isin(targets.slot_start)].copy()
    recent = hard_by_slot.loc[hard_by_slot.mag >= 8.3].sort_values("time_utc")
    if recent.slot_start.nunique() < 8:
        recent = hard_by_slot.loc[hard_by_slot.mag >= 8.1].sort_values("time_utc")
    frozen_negative_slots = set(recent.drop_duplicates("slot_start", keep="last").tail(8).slot_start)
    hard_train = np.zeros(len(master), bool)
    hard_audit = np.zeros(len(master), bool)
    for slot in hard_by_slot.slot_start:
        slot = pd.Timestamp(slot)
        if slot in date_to_index:
            (hard_audit if slot in frozen_negative_slots else hard_train)[date_to_index[slot]] = True
    return master, X, names, targets, y, hard_train, hard_audit, date_to_index


def normalize_config(row: pd.Series) -> dict:
    config = {key: row[key] for key in ("body_group", "field_group", "pre_radius", "post_radius", "between_per_event", "half_life_years", "feature_count", "hard_fraction", "start_year")}
    for key in ("pre_radius", "post_radius", "between_per_event", "feature_count", "start_year"):
        config[key] = int(config[key])
    for key in ("half_life_years", "hard_fraction"):
        config[key] = float(config[key])
    return config


def fit_inner_portfolio(config: dict, config_id: int, inner_slots: list[pd.Timestamp], master: pd.DataFrame, X: np.ndarray, names: list[str], y: np.ndarray, hard_train: np.ndarray, hard_audit: np.ndarray, date_to_index: dict[pd.Timestamp, int], seed: int):
    allowed = ext.config_indices(config, names)
    predictions = {}
    records = []
    for fold, event_slot in enumerate(inner_slots, 1):
        train = ext.training_for_fold(config, master, y, hard_train, hard_audit, event_slot)
        validation = core.date_window_indices(date_to_index, event_slot, 4)
        recency = core.recency_weights(master.date.iloc[train], event_slot, config["half_life_years"])
        sample_weights = core.balanced_weights(y[train], recency)
        local = core.rank_features(X[train][:, allowed], y[train], sample_weights, config["feature_count"], seed + config_id * 101 + fold)
        selected = allowed[local]
        actual = int(np.flatnonzero(y[validation] == 1)[0])
        for model_no, model_name in enumerate(ext.MODEL_NAMES):
            try:
                predictor, _ = ext.fit_extended(model_name, X[train][:, selected], y[train], sample_weights, seed + config_id * 10000 + fold * 100 + model_no)
                raw_train = predictor(X[train][:, selected])
                val_score = core.empirical_percentile(raw_train, predictor(X[validation][:, selected]))
                train_score = core.empirical_percentile(raw_train, raw_train)
                predictions[("development", model_name, event_slot)] = val_score
                metrics = core.peak_metrics(val_score, actual)
                training = core.training_signal(y[train], train_score)
                records.append({"group": "development", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, "training_quality": training["quality"], "status": "OK", **metrics})
            except Exception as exc:
                records.append({"group": "development", "fold": fold, "event_slot": event_slot.strftime("%Y-%m-%d"), "model": model_name, "status": "ERROR", "error": str(exc)})
    table = pd.DataFrame(records)
    complete = [name for name in ext.MODEL_NAMES if ((table.model == name) & (table.status == "OK")).sum() == len(inner_slots)]
    if len(complete) < 5:
        raise RuntimeError(f"Only {len(complete)} complete models")
    qualities = {name: float(table[(table.model == name) & (table.status == "OK")].quality.mean()) for name in complete}
    initial = core.softmax_weights(qualities)
    model_weights, search = core.optimize_timing_weights(predictions, complete, inner_slots, table, initial, seed + config_id, trials=6000)
    return allowed, complete, model_weights, search.iloc[0].to_dict()


def select_nested(configs: list[dict], inner_slots: list[pd.Timestamp], master: pd.DataFrame, X: np.ndarray, names: list[str], y: np.ndarray, hard_train: np.ndarray, hard_audit: np.ndarray, date_to_index: dict[pd.Timestamp, int], seed: int, label: str, top_configs: int = 6):
    rows = []
    for config_id, config in enumerate(configs):
        try:
            row = ext.screen_config(config, config_id, X, names, master, y, hard_train, hard_audit, inner_slots, date_to_index, seed)
            row["status"] = "OK"
        except Exception as exc:
            row = {"config_id": config_id, **config, "screen_objective": -1.0, "status": "ERROR", "error": str(exc)}
        row["outer_label"] = label
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("screen_objective", ascending=False).reset_index(drop=True)
    errors = []
    for _, row in table[table.status == "OK"].head(top_configs).iterrows():
        config_id = int(row.config_id)
        config = normalize_config(row)
        try:
            allowed, complete, weights, metrics = fit_inner_portfolio(config, config_id, inner_slots, master, X, names, y, hard_train, hard_audit, date_to_index, seed + 200000)
            candidate = {"config_id": config_id, "config": config, "allowed": allowed, "complete": complete, "weights": weights, "inner_metrics": metrics}
            errors.append(candidate)
        except Exception:
            continue
    if not errors:
        raise RuntimeError(f"No nested portfolio completed for {label}")
    errors.sort(key=lambda item: (item["inner_metrics"]["exact_rate_recent_weighted"], item["inner_metrics"]["within_one_rate_recent_weighted"], item["inner_metrics"]["quality_recent_weighted"], item["inner_metrics"]["training_quality_weighted"]), reverse=True)
    return errors[0], table


def predict_outer(selection: dict, event_slot: pd.Timestamp, master: pd.DataFrame, X: np.ndarray, y: np.ndarray, hard_train: np.ndarray, hard_audit: np.ndarray, date_to_index: dict[pd.Timestamp, int], seed: int):
    config = selection["config"]
    allowed = selection["allowed"]
    train = ext.training_for_fold(config, master, y, hard_train, hard_audit, event_slot)
    validation = core.date_window_indices(date_to_index, event_slot, 4)
    recency = core.recency_weights(master.date.iloc[train], event_slot, config["half_life_years"])
    sample_weights = core.balanced_weights(y[train], recency)
    local = core.rank_features(X[train][:, allowed], y[train], sample_weights, config["feature_count"], seed)
    selected = allowed[local]
    scores = {}
    for model_no, model_name in enumerate(selection["complete"]):
        predictor, _ = ext.fit_extended(model_name, X[train][:, selected], y[train], sample_weights, seed + 100 + model_no)
        raw_train = predictor(X[train][:, selected])
        scores[model_name] = core.empirical_percentile(raw_train, predictor(X[validation][:, selected]))
    ensemble = sum(selection["weights"][name] * scores[name] for name in selection["complete"])
    diagnostics = {
        "train_row_count": int(len(train)),
        "train_positive_event_count": int(y[train].sum()),
        "train_negative_row_count": int((y[train] == 0).sum()),
    }
    return validation, ensemble, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--astro-master", required=True)
    parser.add_argument("--japan-catalog", required=True)
    parser.add_argument("--world-catalog", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config-trials", type=int, default=96)
    parser.add_argument("--top-configs", type=int, default=6)
    parser.add_argument("--validation-event-count", type=int, default=2, choices=(2, 3))
    parser.add_argument("--force-start-year", type=int)
    parser.add_argument("--run-name", default="hokkaido-morioka-south-kurils-m79plus-7d-v24b-train8-validation2-nested")
    parser.add_argument("--seed", type=int, default=624731)
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    master, X, names, targets, y, hard_train, hard_audit, date_to_index = build_data(Path(args.astro_master), Path(args.japan_catalog), Path(args.world_catalog))
    positive_slots = [pd.Timestamp(value) for value in targets.slot_start]
    outer_slots = positive_slots[-args.validation_event_count:]
    # Starting in 1940 would silently discard the 1931 target. Generate a
    # larger deterministic pool and retain every available prior target.
    config_pool = ext.generate_configs(args.seed, max(args.config_trials * 6, args.config_trials + 64))
    if args.force_start_year is None:
        configs = [config for config in config_pool if int(config["start_year"]) <= 1930][:args.config_trials]
    else:
        configs = []
        for original in config_pool:
            config = {**original, "start_year": int(args.force_start_year)}
            if config not in configs:
                configs.append(config)
            if len(configs) == args.config_trials:
                break
    if len(configs) < args.config_trials:
        raise RuntimeError(f"Only {len(configs)} train-preserving configurations available")
    outer_records = []
    window_records = []
    selection_rows = []
    for outer_no, event_slot in enumerate(outer_slots, 1):
        position = positive_slots.index(event_slot)
        inner_slots = positive_slots[2:position]
        print(f"[NESTED {outer_no}/{len(outer_slots)}] outer={event_slot.date()} inner_folds={len(inner_slots)}", flush=True)
        selection, trials = select_nested(configs, inner_slots, master, X, names, y, hard_train, hard_audit, date_to_index, args.seed + outer_no * 1000000, event_slot.strftime("%Y-%m-%d"), args.top_configs)
        trials.head(20).to_csv(out / f"nested_screen_top20_{event_slot.strftime('%Y%m%d')}.csv", index=False)
        validation, score, diagnostics = predict_outer(selection, event_slot, master, X, y, hard_train, hard_audit, date_to_index, args.seed + outer_no * 2000000)
        actual = int(np.flatnonzero(y[validation] == 1)[0])
        metrics = core.peak_metrics(score, actual)
        outer_records.append({"group": "frozen_audit", "fold": outer_no, "event_slot": event_slot.strftime("%Y-%m-%d"), **metrics})
        selection_rows.append({"outer_event": event_slot.strftime("%Y-%m-%d"), "inner_fold_count": len(inner_slots), **diagnostics, "config_id": selection["config_id"], **selection["config"], **{f"inner_{key}": value for key, value in selection["inner_metrics"].items() if isinstance(value, (int, float, np.integer, np.floating))}, "complete_models": len(selection["complete"]), "model_weights_json": json.dumps(selection["weights"])})
        for p, (index, value) in enumerate(zip(validation, score)):
            window_records.append({"group": "frozen_audit", "fold": outer_no, "event_slot": event_slot.strftime("%Y-%m-%d"), "window_position": p - actual, "date": master.date.iloc[index].strftime("%Y-%m-%d"), "is_event_slot": p == actual, "ensemble_score": float(value)})
    audit = pd.DataFrame(outer_records)
    audit.to_csv(out / "timing_ensemble_fold_metrics.csv", index=False)
    pd.DataFrame(window_records).to_csv(out / "timing_validation_window_predictions.csv", index=False)
    pd.DataFrame(selection_rows).to_csv(out / "nested_outer_selections.csv", index=False)

    print("[FINAL] selecting forecast algorithm on all historical rolling folds", flush=True)
    final_inner = positive_slots[2:]
    final_selection, final_trials = select_nested(configs, final_inner, master, X, names, y, hard_train, hard_audit, date_to_index, args.seed + 9000000, "forecast", args.top_configs)
    final_trials.to_csv(out / "final_forecast_screen_trials.csv", index=False)
    ablation_rows = []
    successful_trials = final_trials.loc[final_trials.status == "OK"].copy()
    for dimension in ("body_group", "field_group"):
        for value, frame in successful_trials.groupby(dimension, dropna=False):
            ablation_rows.append({
                "dimension": dimension,
                "value": value,
                "trial_count": int(len(frame)),
                "best_screen_objective": float(frame.screen_objective.max()),
                "median_screen_objective": float(frame.screen_objective.median()),
            })
    pd.DataFrame(ablation_rows).to_csv(out / "final_body_field_ablation_summary.csv", index=False)
    config = final_selection["config"]
    allowed = final_selection["allowed"]
    train = ext.sample_asymmetric(master.date, y, hard_train, hard_audit, core.FORECAST_START, config["pre_radius"], config["post_radius"], config["between_per_event"], config["hard_fraction"], config["start_year"])
    recency = core.recency_weights(master.date.iloc[train], core.FORECAST_START, config["half_life_years"])
    sample_weights = core.balanced_weights(y[train], recency)
    local = core.rank_features(X[train][:, allowed], y[train], sample_weights, config["feature_count"], args.seed + 9100000)
    selected = allowed[local]
    forecast_idx = np.flatnonzero(((master.date >= core.FORECAST_START) & (master.date <= core.FORECAST_LAST_START)).to_numpy())
    negative_idx = np.flatnonzero(hard_audit)
    forecast = pd.DataFrame({"slot_start_jst": master.date.iloc[forecast_idx].dt.strftime("%Y-%m-%d"), "slot_end_jst": (master.date.iloc[forecast_idx] + pd.Timedelta(days=6)).dt.strftime("%Y-%m-%d")}).reset_index(drop=True)
    train_scores, negative_scores = {}, {}
    for model_no, model_name in enumerate(final_selection["complete"]):
        predictor, _ = ext.fit_extended(model_name, X[train][:, selected], y[train], sample_weights, args.seed + 9200000 + model_no)
        raw_train = predictor(X[train][:, selected])
        train_scores[model_name] = core.empirical_percentile(raw_train, raw_train)
        forecast[model_name] = core.empirical_percentile(raw_train, predictor(X[forecast_idx][:, selected]))
        negative_scores[model_name] = core.empirical_percentile(raw_train, predictor(X[negative_idx][:, selected]))
    forecast["ensemble_score"] = sum(final_selection["weights"][name] * forecast[name] for name in final_selection["complete"])
    forecast["rank"] = forecast.ensemble_score.rank(method="min", ascending=False).astype(int)
    forecast.to_csv(out / "forecast_weekly_aug_sep_2026.csv", index=False)
    peak_position = int(np.argmax(forecast.ensemble_score.to_numpy(float)))
    peak_index = int(forecast_idx[peak_position])
    train_ensemble = sum(final_selection["weights"][name] * train_scores[name] for name in final_selection["complete"])
    training = core.training_signal(y[train], train_ensemble)
    final_fit_counts = {
        "train_row_count": int(len(train)),
        "train_positive_event_count": int(y[train].sum()),
        "train_negative_row_count": int((y[train] == 0).sum()),
        "hard_negative_row_count": int(hard_train[train].sum()),
    }
    negative_ensemble = sum(final_selection["weights"][name] * negative_scores[name] for name in final_selection["complete"])
    pd.DataFrame({"slot_start_jst": master.date.iloc[negative_idx].dt.strftime("%Y-%m-%d"), "ensemble_score": negative_ensemble}).to_csv(out / "frozen_world_hard_negative_scores.csv", index=False)
    location_eligible = targets.latitude.notna() & targets.longitude.notna()
    if "location_eligible" in targets:
        location_eligible &= pd.to_numeric(targets.location_eligible, errors="coerce").fillna(0).eq(1)
    location_targets = targets.loc[location_eligible].reset_index(drop=True)
    location_slots = [pd.Timestamp(value) for value in location_targets.slot_start]
    location_outer_slots = [slot for slot in outer_slots if slot in set(location_slots)]
    if len(location_outer_slots) != len(outer_slots):
        raise RuntimeError("Every reporting validation event must have observed coordinates")
    event_indices = np.asarray([date_to_index[pd.Timestamp(slot)] for slot in location_targets.slot_start], int)
    location_dev_slots = location_slots[2:-args.validation_event_count]
    location = core.run_location(X, names, event_indices, location_targets, location_dev_slots, location_outer_slots, X[[peak_index]], out, args.seed + 9300000)
    checks = {
        "validation_all_exact_peaks": bool(audit.exact_peak.all()),
        "validation_all_within_one_slot": bool(audit.within_one_slot.all()),
        "validation_mean_event_percentile_ge_0_85": bool(audit.event_percentile.mean() >= 0.85),
        "validation_mean_quality_ge_0_70": bool(audit.quality.mean() >= 0.70),
        "training_quality_ge_0_55": bool(training["quality"] >= 0.55),
        "hard_negative_mean_below_0_65": bool(np.mean(negative_ensemble) < 0.65),
        "hard_negative_p90_below_0_85": bool(np.quantile(negative_ensemble, .9) < .85),
    }
    status = "PASS" if all(checks.values()) else "FAIL_REPORTED_NOT_VALIDATED"
    outer_training = pd.DataFrame(selection_rows)[["outer_event", "train_row_count", "train_positive_event_count", "train_negative_row_count"]].to_dict(orient="records")
    summary = {
        "run": args.run_name,
        "scientific_status": "experimental pattern-model output; not an operational earthquake prediction",
        "cutoff": {"jst_end_exclusive": "2026-08-01T00:00:00+09:00", "august_seismic_observations_used": 0},
        "compute": {"deep_device": "cpu", "kan_device": "cpu", "xpu_used": False, "reason": "tiny tabular folds: accelerator transfer and compile overhead dominate"},
        "search": {"fixed_config_candidates_per_outer_fold": len(configs), "full_portfolios_per_selection": args.top_configs, "model_families": list(ext.MODEL_NAMES), "nested_outer_selection": True, "forced_start_year": args.force_start_year, "final_config": config, "final_model_weights": final_selection["weights"], "final_allowed_feature_count": int(len(allowed)), "final_selected_features": [names[i] for i in selected]},
        "timing": {"gate_status": status, "gate_checks": checks, "peak_slot_start_jst": forecast.loc[peak_position, "slot_start_jst"], "peak_slot_end_jst": forecast.loc[peak_position, "slot_end_jst"], "peak_ensemble_score": float(forecast.loc[peak_position, "ensemble_score"]), "validation_exact_rate": float(audit.exact_peak.mean()), "validation_within_one_rate": float(audit.within_one_slot.mean()), "validation_mean_event_percentile": float(audit.event_percentile.mean()), "validation_mean_quality": float(audit.quality.mean()), "outer_fold_training_counts": outer_training, "final_fit_counts": final_fit_counts, "training_metrics": training},
        "location_conditional_on_timing_peak": location,
        "data": {"target_event_count": len(targets), "location_eligible_target_count": len(location_targets), "validation_event_count": len(outer_slots), "development_event_count": len(positive_slots) - len(outer_slots), "target_region_bounds": {"latitude_min": ext.REGION[0], "latitude_max": ext.REGION[1], "longitude_min": ext.REGION[2], "longitude_max": ext.REGION[3]}},
        "leakage_contract": {"reporting_validation_events": [slot.strftime("%Y-%m-%d") for slot in outer_slots], "each_outer_fold_selected_only_from_earlier_events": True, "same_validation_events_for_timing_and_location": True, "historically_virgin_holdout": False, "note": "The reporting events belong to an iterated research lineage and are not a historically untouched discovery test; nested rolling selection remains earlier-events-only inside this run"},
    }
    core.write_json(out / "summary.json", summary)
    (out / "REPORT.md").write_text(f"""# {args.run_name} — nested rolling validation

- Split: {len(positive_slots) - len(outer_slots)} eventi di sviluppo e {len(outer_slots)} eventi finali di validazione temporale/location.
- Eventi positivi effettivamente usati nei fit esterni: {', '.join(str(row['train_positive_event_count']) for row in outer_training)}.
- Fit finale 2026: {final_fit_counts['train_positive_event_count']} eventi positivi e {final_fit_counts['train_negative_row_count']} righe negative ({final_fit_counts['train_row_count']} righe totali).
- Nested validation exact: {audit.exact_peak.mean():.0%}; within one week: {audit.within_one_slot.mean():.0%}; quality: {audit.quality.mean():.3f}.
- Forecast peak: **{summary['timing']['peak_slot_start_jst']} – {summary['timing']['peak_slot_end_jst']} JST**.
- Location: **{location['most_likely_zone']}**, {location['estimated_latitude']:.2f} N, {location['estimated_longitude']:.2f} E, CV80 radius {location['uncertainty_radius_km']:.0f} km.
- Timing gate: `{status}`; location gate: `{location['gate_status']}`.
- Compute: Deep e KAN su **CPU**; XPU non usata.

Per ogni evento di validazione, configurazione, feature e pesi sono scelti soltanto sugli eventi precedenti. I {len(outer_slots)} eventi di reporting appartengono però a una linea di ricerca iterata: questa procedura è priva di leakage interno, ma non costituisce un holdout storicamente vergine.
""")
    print(json.dumps({"timing_gate": status, "peak": [summary["timing"]["peak_slot_start_jst"], summary["timing"]["peak_slot_end_jst"]], "location_gate": location["gate_status"], "zone": location["most_likely_zone"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

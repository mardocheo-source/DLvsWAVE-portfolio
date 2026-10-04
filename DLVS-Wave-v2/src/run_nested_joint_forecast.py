#!/usr/bin/env python3
"""New geographic nesting around the authoritative joint production family."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import sys
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent)]
os.environ.setdefault("MPLCONFIGDIR", "/tmp/dlvs-nested-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/dlvs-nested-cache")

import numpy as np
import pandas as pd
import torch
from pypdf import PdfWriter

from uncompressed_pipeline.nested_data import (atomic_json, timestamp, fingerprint, slot_dates, normalize_catalog,
    DownloadBudget, fetch_catalog, fetch_astronomy, scope_catalog, zone_geometry, select_validation, fit_spherical_zones, plan_spatial_validation)
from uncompressed_pipeline.nested_models import (make_energy_frame, make_spatial_frame, run_branch, binary_metrics, spatial_metrics)
from uncompressed_pipeline.nested_report import compile_node_report


def validate_config(config):
    if not 0 <= config["max_geo_level"] <= 4 or config["interval_days"] < 1:
        raise ValueError("Invalid geographic depth or cadence")
    if config["branch_width"] < 1 or config["max_nodes"] < 1:
        raise ValueError("Node and branch limits must be positive")
    if timestamp(config["training_start"]) >= timestamp(config["reference_date"]):
        raise ValueError("Training must start before reference")
    p = config["validation"]
    if not 1 <= p["initial_months"] <= p["maximum_months"] or p["step_months"] < 1:
        raise ValueError("Invalid recent-window policy")
    if not 0 < p["maximum_withheld_fraction"] < 1:
        raise ValueError("Invalid withheld fraction")
    for component in ["energy", "location"]:
        v = config[component]
        if not 1 <= v["minimum_events"] <= v["desired_events"] or v["minimum_magnitude"] > v["magnitude"]:
            raise ValueError("Invalid event count or threshold policy")
    if config["models"]["trials_per_family"] < 1 or config["models"]["epochs"] < 1:
        raise ValueError("Models must actually be fitted")
    if not 0 <= config["models"]["main_weight"] <= 1:
        raise ValueError("Invalid branch fusion weight")
    if any(v <= 0 for v in config["budgets"].values()):
        raise ValueError("Budgets must be positive")


def config_hash(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def enqueue_saved_children(state, config):
    """Reconcile report-committed decisions after interruption before queue update."""
    for parent in list(state["nodes"]):
        if parent["status"] != "completed" or not parent.get("report"):
            continue
        if parent["level"] >= config["max_geo_level"]:
            continue
        selection = parent.get("selection", {})
        for child in selection.get("candidates", []):
            if child["zone"] not in selection.get("selected_zones", []): continue
            if any(n.get("parent") == parent["id"] and n["path"] == child["path"] for n in state["nodes"]): continue
            if len(state["nodes"]) >= config["max_nodes"]:
                state["stop_reason"] = "maximum_node_budget_reached"
                return
            child_id = f"n{len(state['nodes']):03d}_zone{child['zone']}"
            state["nodes"].append({"id": child_id, "level": parent["level"] + 1, "parent": parent["id"],
                "parent_windows": selection.get("forecast_windows", []), "path": child["path"],
                "geometry": child["geometry"], "status": "not_run", "directory": f"L{parent['level']+1}/nodes/{child_id}"})


def snapshot_sources(root, config):
    import importlib.metadata
    manifest = {"python": sys.version, "files": {}, "packages": {}, "reference_report_sha256": fingerprint(REPO / config["reference_report"])}
    for path in HERE.rglob("*.py"):
        rel = path.relative_to(REPO)
        destination = root / "source_snapshot" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        manifest["files"][str(rel)] = fingerprint(destination)
    for package in ["torch", "numpy", "pandas", "scikit-learn", "astroquery", "matplotlib", "pypdf"]:
        manifest["packages"][package] = importlib.metadata.version(package)
    atomic_json(root / "source_manifest.json", manifest)


def combine_branches(main, minor, component, folder, node, config):
    folder.mkdir(parents=True, exist_ok=True)
    names = ["score"] if component == "energy" else [c for c in main["forecast"] if c.startswith("zone_score_")]
    outputs = {}
    weight = config["models"]["main_weight"]
    for domain in ["validation", "forecast"]:
        a, b = main[domain], minor[domain]
        if not a.date.reset_index(drop=True).equals(b.date.reset_index(drop=True)):
            raise ValueError("main_minor_date_alignment_mismatch")
        if "id" in a and not a.id.reset_index(drop=True).equals(b.id.reset_index(drop=True)):
            raise ValueError("main_minor_event_alignment_mismatch")
        result = a.copy()
        result[names] = weight * a[names].to_numpy() + (1 - weight) * b[names].to_numpy()
        result.to_csv(folder / f"{domain}_predictions.csv", index=False)
        outputs[domain] = result
    val = outputs["validation"]
    if component == "energy":
        metrics = binary_metrics(val.target, val.score, config["quality"]["energy_score_threshold"])
    else:
        metrics = spatial_metrics(val.target, val[names].to_numpy(), node["zones"]["centers"], val, main["summary"]["majority_class"])
    summary = {"metrics": metrics, "main_weight": weight, "minor_weight": 1 - weight,
               "score_semantics": "Uncalibrated score; magnitude threshold is the event definition, not a predicted magnitude."}
    atomic_json(folder / "summary.json", summary)
    if component == "energy":
        from uncompressed_pipeline.intensity_magnitude_spectrum import reference_potential_spectrum
        parent = folder.parent
        a = pd.read_csv(parent / "main_bodies_branch/prospective_energy_magnitude_spectrum.csv")
        b = pd.read_csv(parent / "minor_bodies_branch/prospective_energy_magnitude_spectrum.csv")
        spectrum = a[["date"]].copy()
        for name in ["score_l1", "score_l2", "score_l3"]:
            spectrum[name] = weight * a[name] + (1-weight) * b[name]
        activation, magnitude = reference_potential_spectrum(spectrum.score_l1, spectrum.score_l2, spectrum.score_l3)
        spectrum["activation_density"] = activation
        spectrum["potential_magnitude_ceiling_up_to"] = magnitude
        spectrum.to_csv(folder / "prospective_energy_magnitude_spectrum.csv", index=False)
    return {**outputs, "summary": summary}


def select_children(node, results, config):
    energy, spatial = results["energy"], results["location"]
    em, sm = energy["summary"]["metrics"], spatial["summary"]["metrics"]
    q = config["quality"]
    reasons = []
    if em["recall"] < q["minimum_energy_recall"]: reasons.append("energy_recall_gate_failed")
    if em["false_alarm_fraction"] > q["maximum_false_alarm_fraction"]: reasons.append("energy_false_alarm_gate_failed")
    if sm["represented_zones"] < config["location"]["minimum_validation_zones"]: reasons.append("spatial_validation_lacks_zone_diversity")
    if sm["skill_over_majority"] <= q["minimum_spatial_skill_over_majority"]: reasons.append("spatial_model_did_not_improve_on_training_majority_baseline")
    forecast = energy["forecast"]
    values = forecast.score.to_numpy()
    peak = np.array([v >= q["energy_score_threshold"] and (i == 0 or v > values[i-1]) and
                     (i == len(values)-1 or v >= values[i+1]) for i, v in enumerate(values)])
    peak_dates = forecast.loc[peak, "date"]
    windows = [{"start": str(d), "end_exclusive": str(d + pd.Timedelta(days=config["interval_days"])),
                "score": float(forecast.loc[forecast.date == d, "score"].iloc[0])} for d in peak_dates]
    if not windows:
        reasons.append("no_forecast_peak_above_fixed_threshold")
        if config.get("continuation_policy") == "best_available":
            peak[:] = False
            peak[int(np.argmax(values))] = True
            peak_dates = forecast.loc[peak, "date"]
            windows = [{"start": str(d), "end_exclusive": str(d+pd.Timedelta(days=config["interval_days"])),
                        "score": float(forecast.loc[forecast.date == d, "score"].iloc[0]), "selection": "best_available_below_gate"} for d in peak_dates]
    candidates = []
    if len(peak_dates):
        condition = spatial["forecast"].loc[spatial["forecast"].date.isin(peak_dates)]
        for zone in range(node["zones"]["count"]):
            path = node["path"] + [{"centers": node["zones"]["centers"], "zone": zone}]
            geometry = zone_geometry(path)
            ratio = geometry["area_fraction"] / max(node["geometry"]["area_fraction"], 1e-12)
            score = float(condition[f"zone_score_{zone}"].mean())
            minimum_diameter = config["zones"]["minimum_diameter_km"]
            if config.get("continuation_policy") != "best_available": minimum_diameter = max(minimum_diameter, sm["median_centroid_distance_km"])
            useful = geometry["diameter_km"] >= minimum_diameter and ratio <= config["zones"]["maximum_child_area_ratio"]
            candidates.append({"zone": zone, "score": score, "area_ratio": ratio, "admissible_geometry": useful,
                               "geometry": geometry, "path": path})
    candidates.sort(key=lambda c: (-c["score"], c["zone"]))
    quality_notes = reasons.copy()
    if config.get("continuation_policy") == "best_available": reasons = []
    selected = [c for c in candidates if c["admissible_geometry"]][:config["branch_width"]] if not reasons else []
    if not selected and not reasons: reasons.append("no_useful_geographic_contraction")
    if node["level"] >= config["max_geo_level"]:
        selected = []; reasons.append("maximum_geographic_depth_reached")
    parent_windows = node.get("parent_windows", [])
    divergence = None
    if windows and parent_windows:
        child_best = max(windows, key=lambda w: w["score"])
        parent_best = max(parent_windows, key=lambda w: w["score"])
        a, b = timestamp(child_best["start"]), timestamp(parent_best["start"])
        divergence = {"peak_start_displacement_days": int((a-b).days), "best_windows_overlap": abs((a-b).days) < config["interval_days"]}
    return {"forecast_windows": windows, "parent_divergence": divergence, "candidates": candidates,
            "selected_zones": [c["zone"] for c in selected], "stop_reasons": reasons,
            "quality_notes": quality_notes, "continuation_policy": config.get("continuation_policy", "quality_gated"),
            "rule": "Mean conditional zone score at fixed-threshold energy local maxima, subject to outer quality and geometry gates."}, selected


def write_study(root, state, config):
    lines = ["# Nested joint study", "", f"Status: {state['status']}", f"Reference: {config['reference_date']}",
             f"Synthetic demonstration: {state.get('synthetic', False)}", "", "| Level | Node | Status | Stop reason | Report |", "|---|---|---|---|---|"]
    rows = []
    for level in range(config["max_geo_level"] + 1):
        level_dir = root / f"L{level}"; level_dir.mkdir(exist_ok=True)
        nodes = [n for n in state["nodes"] if n["level"] == level]
        status = "not_run" if not nodes else ("completed" if all(n["status"] == "completed" for n in nodes) else "interrupted" if any(n["status"] == "interrupted" for n in nodes) else "failed" if any(n["status"] == "failed" for n in nodes) else "running" if any(n["status"] == "running" for n in nodes) else "not_run")
        level_lines = [f"# Geographic level {level}", "", f"Status: {status}", ""]
        writer, pages = PdfWriter(), 0
        for node in nodes:
            rel = f"{node['directory']}/06_report/JOINT_ENERGY_AND_SPACE_SUPER_CONSOLIDATED_REPORT.pdf"
            report = root / rel
            lines.append(f"| L{level} | {node['id']} | {node['status']} | {node.get('stop_reason', '')} | {'[PDF](' + rel + ')' if report.exists() else 'Pending'} |")
            level_lines.append(f"- {node['id']}: {node['status']}; {node.get('stop_reason', '')}")
            if report.exists():
                writer.append(str(report)); pages += 1
                level_lines.append(f"  [Node report]({os.path.relpath(report, level_dir)})")
            rows.append({"level": level, "node": node["id"], "status": node["status"], "stop_reason": node.get("stop_reason"),
                         "energy_threshold": node.get("energy_split", {}).get("threshold"),
                         "location_threshold": node.get("location_split", {}).get("threshold"),
                         "energy_validation_events": node.get("energy_split", {}).get("validation_events"),
                         "location_validation_events": node.get("location_split", {}).get("validation_events"),
                         "energy_recall": node.get("metrics", {}).get("energy", {}).get("recall"),
                         "location_accuracy": node.get("metrics", {}).get("location", {}).get("accuracy"),
                         "report": rel if report.exists() else None})
        if not nodes: lines.append(f"| L{level} | - | not_run | No admitted parent node | - |")
        (level_dir / "level_report.md").write_text("\n".join(level_lines) + "\n")
        atomic_json(level_dir / "level_state.json", {"status": status, "nodes": [n["id"] for n in nodes]})
        if pages:
            tmp = level_dir / "level_report.pdf.tmp"
            with tmp.open("wb") as stream: writer.write(stream)
            tmp.replace(level_dir / "level_report.pdf")
    (root / "study_summary.md").write_text("\n".join(lines) + "\n")
    pd.DataFrame(rows).to_csv(root / "levels_comparison.csv", index=False)
    atomic_json(root / "study_state.json", state)


def synthetic_data(config):
    rng = np.random.default_rng(123)
    reference = timestamp(config["reference_date"])
    dates = pd.date_range(timestamp(config["training_start"]), reference - pd.Timedelta(days=8), freq="14D")
    rows = []
    for i, date in enumerate(dates):
        lat, lon = [(35, 140), (-20, -70), (5, 95)][i % 3]
        rows.append({"id": f"SYNTHETIC_{i}", "time": str(date), "latitude": lat + rng.normal(0, 3),
                     "longitude": lon + rng.normal(0, 3), "mag": 7.8 if i % 5 == 0 else 6.9})
    events = normalize_catalog(pd.DataFrame(rows), config)
    grid = pd.date_range(timestamp(config["training_start"]), reference + pd.Timedelta(days=config["horizon_days"]), freq=f"{config['interval_days']}D")
    astro = pd.DataFrame({"date": grid})
    for j in range(24): astro[f"astro_SYNTHETIC_{j}"] = np.sin(np.arange(len(grid)) / (j+2))
    return events, {"main": astro, "minor": astro.copy()}


def run(config, resume=None, smoke=False, fetch_only=False, reuse_data=None, study_dir=None):
    validate_config(config)
    torch.set_num_threads(config["models"]["cpu_threads"])
    if smoke:
        config = copy.deepcopy(config)
        config["training_start"] = "2000-01-03T00:00:00Z"
        config["max_geo_level"] = 0
        config["models"].update({"trials_per_family": 1, "meta_trials": 1, "epochs": 2, "surrogate_epochs": 3})
        config["study_id"] = "SYNTHETIC_SMOKE"
    started = time.monotonic()
    if resume:
        root = Path(resume).resolve()
        saved = json.loads((root / "study_config.json").read_text())
        if config_hash(saved) != config_hash(config): raise ValueError("Resume configuration differs from frozen study config")
        state = json.loads((root / "study_state.json").read_text())
        state["status"] = "running"
        state.pop("stop_reason", None)
        manifest_path = root / "source_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            for rel, sha in manifest["files"].items():
                if fingerprint(REPO / rel) != sha:
                    raise ValueError("Source changed since this run; start a new run with --reuse-data instead of mixing code versions")
    else:
        root = Path(study_dir).resolve() if study_dir else REPO / config["output_root"] / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{config['study_id']}_{uuid.uuid4().hex[:8]}"
        if study_dir:
            if not root.is_relative_to(REPO / "studies_output") or (root / "study_state.json").exists():
                raise ValueError("Explicit new study directory must be unused and inside studies_output")
            root.mkdir(parents=True, exist_ok=True)
        else: root.mkdir(parents=True, exist_ok=False)
        atomic_json(root / "study_config.json", config)
        state = {"status": "running", "synthetic": smoke, "active_seconds": 0, "nodes": [
            {"id": "n000_world", "level": 0, "parent": None, "path": [], "geometry": zone_geometry([]), "status": "not_run", "directory": "L0/nodes/n000_world"}]}
        snapshot_sources(root, config)
        if reuse_data:
            source = Path(reuse_data).resolve() / "shared_data"
            for name in ["catalog_snapshot", "ephemerides"]:
                if (source / name).exists(): shutil.copytree(source / name, root / "shared_data" / name)
            atomic_json(root / "reused_data.json", {"source_study": str(Path(reuse_data).resolve()), "scope": "Only checksum-verified raw catalog and ephemeris snapshots; no fitted models or forecast artifacts."})
    enqueue_saved_children(state, config)
    print(f"STUDY_DIR={root}", flush=True)
    log = root / "execution.log"
    def log_message(value):
        print(value, flush=True)
        with log.open("a") as stream: stream.write(f"{datetime.now(timezone.utc).isoformat()} {value}\n")
        (root / "PROGRESS.md").write_text(f"# Live study progress\n\n{datetime.now(timezone.utc).isoformat()}\n\n{value}\n\nSee study_summary.md, study_state.json and execution.log.\n")
    previous = state["active_seconds"]
    write_study(root, state, config)
    try:
        if smoke:
            catalog, synthetic_astro = synthetic_data(config)
        else:
            budget = DownloadBudget(root / "shared_data", config)
            catalog = fetch_catalog(root / "shared_data", config, budget)
        log_message(f"Catalog ready: {len(catalog)} unique events")
        if fetch_only:
            state["status"] = "catalog_ready"
            return root
        for node in state["nodes"]:
            if node["status"] == "completed": continue
            elapsed = previous + time.monotonic() - started
            if elapsed >= config["budgets"]["total_seconds"]:
                state["status"] = "interrupted"; state["stop_reason"] = "study_time_budget_exhausted"; break
            directory = root / node["directory"]
            if directory.exists() and node["status"] in ["running", "failed", "interrupted"]:
                archive = directory.parent / f"{directory.name}_attempt_{uuid.uuid4().hex[:8]}"
                directory.rename(archive)
                node.setdefault("previous_attempts", []).append(str(archive.relative_to(root)))
            directory.mkdir(parents=True, exist_ok=True)
            node["status"] = "running"; node.pop("stop_reason", None)
            atomic_json(directory / "node_config.json", {"node": node, "config": config})
            write_study(root, state, config)
            events = scope_catalog(catalog, node["path"])
            events.to_csv(directory / "catalog_events.csv", index=False)
            atomic_json(directory / "input_fingerprint.json", {"catalog_sha256": fingerprint(directory / "catalog_events.csv")})
            node_deadline = time.monotonic() + min(config["budgets"]["node_seconds"], config["budgets"]["total_seconds"] - elapsed)
            children = []
            def timeout_handler(signum, frame): raise TimeoutError("node_time_budget_exhausted")
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.setitimer(signal.ITIMER_REAL, max(1, node_deadline - time.monotonic()))
            try:
                log_message(f"{node['id']}: {len(events)} catalog events; selecting recent splits")
                for component in ["energy", "location"]:
                    node[f"{component}_split"] = select_validation(events, config, component)
                node["location_split"], planned_zones = plan_spatial_validation(events, config)
                atomic_json(directory / "split_audit.json", {c: node[f"{c}_split"] for c in ["energy", "location"]})
                if any(node[f"{c}_split"]["status"] != "sufficient" for c in ["energy", "location"]):
                    node["stop_reason"] = "insufficient_data_after_bounded_magnitude_adaptation"
                else:
                    spatial = node["location_split"]
                    node["zones"] = planned_zones
                    atomic_json(directory / "zones.json", node["zones"])
                    if smoke: astronomy = synthetic_astro
                    else:
                        log_message(f"{node['id']}: obtaining observer-specific main/minor ephemerides")
                        budget = DownloadBudget(root / "shared_data", config)
                        astronomy = fetch_astronomy(root / "shared_data", config, node, budget)
                    results = {}
                    remaining_branches = 4
                    for component in ["energy", "location"]:
                        base = directory / ("01_energy_forecast" if component == "energy" else "02_spatial_zones_forecast")
                        branches = {}
                        for branch in ["main", "minor"]:
                            log_message(f"{node['id']}: fitting {component} / {branch} bodies")
                            frame = make_energy_frame(astronomy[branch], events, node["energy_split"], config) if component == "energy" else make_spatial_frame(astronomy[branch], events, spatial, node["zones"], config)
                            branch_deadline = time.monotonic() + max(1, (node_deadline-time.monotonic()-30)/remaining_branches)
                            branches[branch] = run_branch(frame, config, component, base / f"{branch}_bodies_branch", branch_deadline, node.get("zones"))
                            remaining_branches -= 1
                        results[component] = combine_branches(branches["main"], branches["minor"], component, base / "fusion_main_minor", node, config)
                    node["metrics"] = {c: r["summary"]["metrics"] for c, r in results.items()}
                    node["selection"], children = select_children(node, results, config)
                    node["stop_reason"] = "; ".join(node["selection"]["stop_reasons"])
                node["status"] = "completed"
            except (KeyboardInterrupt, TimeoutError) as error:
                node["status"] = "interrupted"; node["stop_reason"] = str(error) or "user_interrupt"
            except ValueError as error:
                if "insufficient" in str(error):
                    node["status"] = "completed"; node["stop_reason"] = str(error)
                else:
                    node["status"] = "failed"; node["stop_reason"] = str(error)
                    (directory / "error.txt").write_text(traceback.format_exc())
            except Exception as error:
                node["status"] = "failed"; node["stop_reason"] = f"{type(error).__name__}: {error}"
                (directory / "error.txt").write_text(traceback.format_exc())
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old_handler)
            atomic_json(directory / "selection.json", node.get("selection", {"stop_reason": node.get("stop_reason")}))
            # The report is a prerequisite for admitting children, never an end-of-run afterthought.
            report = compile_node_report(directory, node, events, config)
            node["report"] = str(report.relative_to(root))
            atomic_json(directory / "node_state.json", node)
            state["active_seconds"] = previous + time.monotonic() - started
            write_study(root, state, config)
            log_message(f"{node['id']}: {node['status']} | {node.get('stop_reason')} | report saved")
            if node["status"] == "completed":
                enqueue_saved_children(state, config)
            else:
                state["status"] = node["status"]
                break
            write_study(root, state, config)
        if state["status"] == "running": state["status"] = "completed"
    except (KeyboardInterrupt, Exception) as error:
        state["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        state["stop_reason"] = f"{type(error).__name__}: {error}"
        (root / "error.txt").write_text(traceback.format_exc())
        log_message(state["stop_reason"])
    finally:
        state["active_seconds"] = previous + time.monotonic() - started
        write_study(root, state, config)
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=REPO / "master/nested_joint_config.json")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--reuse-data", type=Path, help="Reuse audited raw data from a prior study; always refit models")
    parser.add_argument("--study-dir", type=Path, help="Prepared new directory under studies_output; must not contain a previous study state")
    args = parser.parse_args()
    root = run(json.loads(args.config.read_text()), args.resume, args.smoke, args.fetch_only, args.reuse_data, args.study_dir)
    status = json.loads((root / "study_state.json").read_text())["status"]
    print(f"FINAL_STATUS={status}", flush=True)
    raise SystemExit(0 if status in ["completed", "catalog_ready"] else 1)

"""
CLI principale.
Comandi:
  list                      : mostra task/banks/readouts/deep presets
  generate --task ...       : genera CSV
  train    --task ...       : benchmark completo
  top                       : leaderboard dal DB

Deep learning options (solo train):
    --max-iter 200                    : override unico per epoche/iterazioni modelli iterativi
  --deep-presets default,deep     : attiva DeepNet end-to-end con preset
  --deep-custom                   : attiva DeepNet con config da flag custom
  --deep-hidden 128,64,32         : hidden sizes (custom)
  --deep-activation gelu          : relu|gelu|tanh|silu|leakyrelu|elu
  --deep-dropout 0.1
  --deep-epochs 200
  --deep-lr 0.001
  --deep-batch-size 64
  --deep-weight-decay 1e-4
  --deep-batch-norm               : flag, attiva batch norm
  --deep-device auto|cpu|cuda|xpu
"""
import argparse
import copy
import csv
import glob
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import math
from datetime import timedelta
import numpy as np

from artifacts import (timestamp_slug, ensure_run_dir, export_best_trial, safe_slug,
                       write_json, write_run_signature, write_run_index_csv,
                       write_ranking_bar_png, write_technique_summary_png,
                       write_lcs_rules_map_png, write_series_png, json_safe,
                       write_collage_png, write_all_trials_validation_csv,
                       decode_location_series, is_location_analog_display,
                       location_display_subtitle)
from tasks import (TASKS, generate_dataset, save_csv, load_csv, load_csv_dataset,
                   is_csv_task, parse_datetime_like)
from feature_banks import BANKS
from benchmark import (run_benchmark, run_benchmark_dataset,
                       aggregate_results, READOUTS, significance,
                       resolve_target_window_indices, resolve_metric_profile,
                       resolve_context_window_indices, predict_with_result,
                       configure_runtime_controls, enforce_train_before_test,
                       configure_shape_weight, detect_topological_peaks,
                       make_inverted_twin_result)
from storage import init_db, insert_result, query_top

try:
    from deep_nets import DeepConfig, DEEP_PRESETS, TORCH_AVAILABLE, ACTIVATIONS
except ImportError:
    TORCH_AVAILABLE = False
    DEEP_PRESETS = {}
    ACTIVATIONS = {}

from lcs import LCSConfig, LCS_PRESETS

try:
    from kan_backend import KANConfig, KAN_PRESETS, KAN_AVAILABLE
except ImportError:
    KAN_AVAILABLE = False
    KAN_PRESETS = {}
    KANConfig = None


def cmd_list(args):
    print("TASK DISPONIBILI")
    for name, spec in TASKS.items():
        print(f"  {name:18s}  features={spec['n_features']}  range={spec['range']}")
    print("\nFEATURE BANKS")
    for name in BANKS:
        print(f"  {name}")
    print("\nREADOUTS")
    for name in READOUTS:
        print(f"  {name}")
    if TORCH_AVAILABLE:
        print("\nDEEP PRESETS (end-to-end, no feature bank)")
        for name, cfg in DEEP_PRESETS.items():
            h = cfg.hidden_sizes if cfg.hidden_sizes else "auto"
            print(f"  {name:10s} hidden={h} act={cfg.activation} "
                  f"epochs={cfg.epochs} dropout={cfg.dropout}")
        print("\nATTIVAZIONI DISPONIBILI")
        print(f"  {', '.join(ACTIVATIONS.keys())}")
    else:
        print("\n[torch non installato: deep learning non disponibile]")
    print("\nLCS PRESETS (UCS event-based, puro Python)")
    for name, cfg in LCS_PRESETS.items():
        print(f"  {name:10s} pop={cfg.population_size} epochs={cfg.epochs} "
              f"ga_freq={cfg.ga_frequency} wildcard={cfg.wildcard_prob}")
    if KAN_AVAILABLE:
        print("\nKAN PRESETS (interpretable spline/event-based)")
        for name, cfg in KAN_PRESETS.items():
            print(f"  {name:10s} width={cfg.hidden_width} grid={cfg.grid} "
                  f"epochs={cfg.epochs} lr={cfg.lr}")
    else:
        print("\n[KAN non disponibile: backend interpretabile KAN disattivato]")


def cmd_generate(args):
    X, y = generate_dataset(args.task, args.n, seed=args.seed, noise_std=args.noise)
    save_csv(X, y, args.out)
    print(f"Generati {len(X)} samples (d={X.shape[1]}) -> {args.out}")


def cmd_explore_constants(args):
    from seismic_constant_explorer import run_from_namespace

    args.command_line = " ".join(shlex.quote(x) for x in sys.argv)
    try:
        result = run_from_namespace(args)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERRORE explore-constants: {exc}")
        raise SystemExit(2) from exc
    print(f"Candidate CSV: {result['candidate_csv']}")
    print(f"Summary JSON : {result['summary_json']}")
    print(f"Report MD    : {result['report_md']}")
    if result.get("png"):
        print(f"PNG          : {result['png']}")
    if result.get("pair_csv"):
        print(f"Event pairs  : {result['pair_csv']}")
    if result.get("control_csv"):
        print(f"Controls CSV : {result['control_csv']}")
    top = result.get("top_candidates") or []
    if top:
        best = top[0]
        rel_error = best.get("known_rel_error")
        rel_text = f"{float(rel_error):.4g}" if rel_error not in ("", None) else "n/a"
        print(
            "Best candidate: "
            f"{best['metric']} median={float(best['median']):.6g} "
            f"scope={best['scope']} group={best['group_value']} "
            f"known={best.get('known_name') or 'n/a'} rel_err={rel_text}"
        )


def cmd_constant_forecast(args):
    from seismic_constant_forecaster import run_from_namespace

    args.command_line = " ".join(shlex.quote(x) for x in sys.argv)
    try:
        result = run_from_namespace(args)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERRORE constant-forecast: {exc}")
        raise SystemExit(2) from exc
    summary = result.get("summary", {})
    forecast = summary.get("forecast", {})
    print(f"Validation CSV: {result['validation_csv']}")
    print(f"Forecast CSV  : {result['forecast_csv']}")
    if result.get("daily_csv"):
        print(f"Daily CSV     : {result['daily_csv']}")
    if result.get("daily_png"):
        print(f"Daily PNG     : {result['daily_png']}")
    print(f"Summary JSON  : {result['summary_json']}")
    print(f"Report MD     : {result['report_md']}")
    if forecast:
        print(
            "Forecast window: "
            f"{forecast.get('forecast_start')} -> {forecast.get('forecast_end')} "
            f"(median {forecast.get('forecast_median')})"
        )
        print(
            "Validation: "
            f"hit_rate={summary.get('hit_rate')} "
            f"evaluated={summary.get('validation_evaluated')}"
        )


def _validate_csv_path(path: str) -> None:
    """Valida path CSV con messaggi chiari. Exit con codice 2 su errore."""
    if not path or path.strip() == "":
        print("ERRORE: path del task non specificato.")
        raise SystemExit(2)
    if "..." in path:
        print(f"ERRORE: path contiene '...' letterale: {path}")
        print("  Sembra un placeholder non sostituito. Usa il path completo del CSV.")
        raise SystemExit(2)
    if not os.path.exists(path):
        print(f"ERRORE: file non trovato: {path}")
        print(f"  Directory corrente: {os.getcwd()}")
        parent = os.path.dirname(path) or "."
        if os.path.isdir(parent):
            print(f"  Directory parent esiste: {parent}")
            try:
                siblings = [f for f in os.listdir(parent) if f.endswith(".csv")]
                if siblings:
                    print("  CSV disponibili in quella directory:")
                    for s in siblings[:10]:
                        print(f"    {s}")
            except PermissionError:
                pass
        else:
            print(f"  Directory parent non esiste: {parent}")
        raise SystemExit(2)
    if os.path.isdir(path):
        print(f"ERRORE: path e' una directory, non un file: {path}")
        raise SystemExit(2)
    if not os.access(path, os.R_OK):
        print(f"ERRORE: file non leggibile (permessi): {path}")
        raise SystemExit(2)
    if not path.lower().endswith(".csv"):
        print(f"AVVISO: file non ha estensione .csv: {path}")
        print("  Il codice proseguira' ma potrebbe fallire nel parsing.")
    try:
        if os.path.getsize(path) == 0:
            print(f"ERRORE: file vuoto: {path}")
            raise SystemExit(2)
    except OSError as e:
        print(f"ERRORE: impossibile leggere size del file: {e}")
        raise SystemExit(2)


_INCREMENTAL_TRIALS_SINK = {
    "path": None,
    "started_at": None,
    "next_serial": 0,
    "best_trials": [],
}
_IMMEDIATE_INVERSION_CONTEXT = None


def _set_incremental_trials_sink(path):
    """Apre (se non esiste) `incremental_trials.csv` nella run dir.
    Le righe vengono accodate dal progress callback in tempo reale."""
    if path is None:
        _INCREMENTAL_TRIALS_SINK["path"] = None
        _INCREMENTAL_TRIALS_SINK["started_at"] = None
        _INCREMENTAL_TRIALS_SINK["next_serial"] = 0
        _INCREMENTAL_TRIALS_SINK["best_trials"] = []
        return
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("trial_serial,timestamp_local,elapsed_s,task,bank,readout,seed,role,window_no,"
                    "is_inverted_twin,inverted_from_serial,inverted_from,"
                    "overall_kpi,mse_test,event_f1,event_recall,"
                    "event_bal_acc,shape_overall,"
                    "quiet_fidelity,peak_baseline_ratio,peak_separation_score,readability,"
                    "inference_time_us,train_time_s,n_effective_params\n")
    _INCREMENTAL_TRIALS_SINK["path"] = path
    _INCREMENTAL_TRIALS_SINK["started_at"] = time.time()
    _INCREMENTAL_TRIALS_SINK["next_serial"] = _infer_next_incremental_serial(path)
    _INCREMENTAL_TRIALS_SINK["best_trials"] = []


def _infer_next_incremental_serial(path):
    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            max_serial = 0
            row_count = 0
            for row in reader:
                row_count += 1
                try:
                    max_serial = max(max_serial, int(row.get("trial_serial") or 0))
                except (TypeError, ValueError):
                    pass
            return max(max_serial, row_count)
    except Exception:
        return 0


def _ensure_trial_serial(r):
    extra = r.setdefault("extra", {})
    current = extra.get("trial_serial")
    if current not in (None, ""):
        try:
            return int(current)
        except (TypeError, ValueError):
            pass
    _INCREMENTAL_TRIALS_SINK["next_serial"] = int(
        _INCREMENTAL_TRIALS_SINK.get("next_serial", 0) or 0
    ) + 1
    serial = int(_INCREMENTAL_TRIALS_SINK["next_serial"])
    extra["trial_serial"] = serial
    return serial


def _ensure_trial_serials(results):
    for r in results or []:
        _ensure_trial_serial(r)


def _append_incremental_trial_row(r):
    path = _INCREMENTAL_TRIALS_SINK.get("path")
    if not path:
        return
    extra = r.get("extra", {}) or {}
    trial_serial = _ensure_trial_serial(r)
    role = "main"
    window_no = ""
    if extra.get("backtest_info"):
        role = "backtest"
        window_no = extra["backtest_info"].get("window_no", "")
    elif extra.get("recent_validation_info"):
        role = "recent_val"
    try:
        from datetime import datetime as _dt
        started = _INCREMENTAL_TRIALS_SINK.get("started_at") or time.time()
        elapsed = max(0.0, time.time() - started)
        with open(path, "a") as f:
            f.write(
                f"{trial_serial},"
                f"{_dt.now().isoformat(timespec='seconds')},"
                f"{elapsed:.2f},"
                f"{r.get('task','')},{r.get('bank','')},{r.get('readout','')},"
                f"{r.get('seed','')},{role},{window_no},"
                f"{1 if extra.get('inverted_twin') else 0},"
                f"{extra.get('inverted_from_trial_serial', '')},"
                f"{extra.get('inverted_from', '')},"
                f"{r.get('overall_kpi', 0.0):.6f},"
                f"{r.get('mse_test', 0.0):.6f},"
                f"{extra.get('event_f1', '')},"
                f"{extra.get('event_recall', '')},"
                f"{extra.get('event_bal_acc', '')},"
                f"{extra.get('shape_overall', '')},"
                f"{extra.get('quiet_fidelity', '')},"
                f"{extra.get('peak_baseline_ratio', '')},"
                f"{extra.get('peak_separation_score', '')},"
                f"{extra.get('readability', '')},"
                f"{r.get('inference_time_us', 0.0):.3f},"
                f"{r.get('train_time_s', 0.0):.3f},"
                f"{int(r.get('n_effective_params', 0) or 0)}\n"
            )
    except Exception as _err:
        pass  # non bloccare il run su un IO transitorio


def _incremental_role(result):
    extra = result.get("extra", {}) or {}
    if extra.get("backtest_info"):
        return f"backtest_w{extra['backtest_info'].get('window_no', '')}"
    if extra.get("recent_validation_info"):
        return "recent_validation"
    return "main"


def _update_incremental_best3(result):
    ctx = _IMMEDIATE_INVERSION_CONTEXT or {}
    csv_meta = ctx.get("csv_meta")
    if csv_meta is None:
        return
    path = _INCREMENTAL_TRIALS_SINK.get("path")
    if not path:
        return
    artifacts = result.get("_artifacts", {}) or {}
    if artifacts.get("test_indices") is None or artifacts.get("y_pred_test") is None:
        return
    best_trials = _INCREMENTAL_TRIALS_SINK.setdefault("best_trials", [])
    best_trials.append(result)
    _compact_incremental_best_trials(best_trials)
    _write_incremental_best3_snapshot(best_trials, csv_meta, ctx.get("args"))


def _compact_incremental_best_trials(best_trials, keep_per_role=12):
    grouped = {}
    for trial in best_trials:
        grouped.setdefault(_incremental_role(trial), []).append(trial)
    kept = []
    for trials in grouped.values():
        trials.sort(key=lambda r: float(r.get("overall_kpi", 0.0) or 0.0), reverse=True)
        kept.extend(trials[:keep_per_role])
    best_trials[:] = kept


def _write_incremental_best3_snapshot(all_trials, csv_meta, args):
    run_dir = os.path.dirname(os.path.abspath(_INCREMENTAL_TRIALS_SINK.get("path", "")))
    if not run_dir or not all_trials:
        return
    out_dir = os.path.join(run_dir, "incremental_best3")
    try:
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        index_rows = []
        role_groups = {}
        for trial in all_trials:
            role_groups.setdefault(_incremental_role(trial), []).append(trial)

        role_order = {"main": 0, "recent_validation": 1}
        roles = sorted(role_groups, key=lambda r: (role_order.get(r, 10), r))
        for role in roles:
            role_trials = sorted(
                role_groups[role],
                key=lambda r: float(r.get("overall_kpi", 0.0) or 0.0),
                reverse=True,
            )[:3]
            role_dir = os.path.join(out_dir, safe_slug(role))
            os.makedirs(role_dir, exist_ok=True)
            for rank, trial in enumerate(role_trials, start=1):
                extra = trial.get("extra", {}) or {}
                serial = _ensure_trial_serial(trial)
                inv = "INV" if extra.get("inverted_twin") else "RAW"
                prefix = (
                    f"INCREMENTAL BEST {rank}/3 | role={role} | T{serial:05d} | "
                    f"{inv} | comparable within role"
                )
                exported = export_best_trial(
                    role_dir,
                    None,
                    trial,
                    csv_meta,
                    plot_autoscale=not getattr(args, "no_plot_autoscale", False),
                    rank_idx=rank,
                    title_prefix=prefix,
                )
                payload = {
                    "snapshot": "incremental_best3_by_role",
                    "comparison_scope": "same_role_only",
                    "rank": rank,
                    "trial_serial": serial,
                    "role": role,
                    "bank": trial.get("bank"),
                    "readout": trial.get("readout"),
                    "seed": trial.get("seed"),
                    "overall_kpi": trial.get("overall_kpi"),
                    "mse_test": trial.get("mse_test"),
                    "inverted_twin": bool(extra.get("inverted_twin")),
                    "inverted_from_trial_serial": extra.get("inverted_from_trial_serial"),
                    "inversion_reason": extra.get("inversion_reason"),
                    "ranking_weight": extra.get("ranking_weight", 1.0),
                    "score_components": extra.get("score_components"),
                    "test_csv": exported.get("test_csv"),
                    "test_png": exported.get("test_png"),
                    "validation_combined_csv": exported.get("validation_combined_csv"),
                }
                write_json(exported["json"], payload)
                index_rows.append(payload)
        write_json(os.path.join(out_dir, "incremental_best3_index.json"), index_rows)
        _write_incremental_best3_index_csv(
            os.path.join(out_dir, "incremental_best3_index.csv"),
            index_rows,
        )
        with open(os.path.join(out_dir, "README.txt"), "w") as f:
            f.write(
                "incremental_best3 is role-aware.\n"
                "Do not compare KPI across different role folders as if they were the same test set.\n"
                "Use each folder as a comparable top-3 for that temporal slice/window.\n"
            )
    except Exception as err:
        print(f"[warn] incremental best3 snapshot failed: {err}")


def _write_incremental_best3_index_csv(path, rows):
    fieldnames = [
        "role", "rank", "trial_serial", "bank", "readout", "seed",
        "overall_kpi", "mse_test", "inverted_twin",
        "inverted_from_trial_serial", "ranking_weight", "test_csv", "test_png",
        "validation_combined_csv",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows or []:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _set_immediate_inversion_context(args=None, metric_profile=None, kpi_weights=None,
                                     csv_meta=None):
    global _IMMEDIATE_INVERSION_CONTEXT
    if args is None:
        _IMMEDIATE_INVERSION_CONTEXT = None
        return
    _IMMEDIATE_INVERSION_CONTEXT = {
        "args": args,
        "metric_profile": metric_profile,
        "kpi_weights": kpi_weights,
        "csv_meta": csv_meta,
    }


def _prediction_has_nonflat_peaks(result, metric_profile, min_std):
    artifacts = result.get("_artifacts", {}) or {}
    y_pred = artifacts.get("y_pred_test")
    if y_pred is None or len(y_pred) == 0:
        return False, 0.0, 0
    try:
        pred_arr = np.asarray(y_pred, dtype=float).reshape(-1)
        std_val = float(np.std(pred_arr))
    except Exception:
        return False, 0.0, 0
    if std_val < float(min_std):
        return False, std_val, 0
    threshold = None
    if (metric_profile or {}).get("kind") == "event":
        threshold = (metric_profile or {}).get("threshold")
    peaks = detect_topological_peaks(pred_arr, threshold=threshold)
    return len(peaks) > 0, std_val, len(peaks)


def _maybe_make_immediate_inverted_twin(source):
    ctx = _IMMEDIATE_INVERSION_CONTEXT or {}
    args = ctx.get("args")
    if args is None or not bool(getattr(args, "invert_twin_enabled", True)):
        return None
    threshold = float(getattr(args, "invert_twin_immediate_threshold", 0.0) or 0.0)
    if threshold <= 0.0:
        return None
    extra = source.get("extra", {}) or {}
    bank = str(source.get("bank", ""))
    if bank.endswith("__INV") or extra.get("inverted_twin"):
        return None
    if extra.get("immediate_inverted_twin_generated"):
        return None
    try:
        if float(source.get("overall_kpi", 0.0) or 0.0) > threshold:
            return None
    except (TypeError, ValueError):
        return None
    metric_profile = ctx.get("metric_profile") or {}
    min_std = max(0.0, float(getattr(args, "invert_twin_min_std", 1e-6) or 0.0))
    has_peaks, std_val, n_peaks = _prediction_has_nonflat_peaks(
        source, metric_profile, min_std
    )
    if not has_peaks:
        return None
    csv_meta = ctx.get("csv_meta")
    y_ref = np.asarray((csv_meta or {}).get("y", []), dtype=float) if csv_meta else None
    mse_ref = float(np.var(y_ref)) + 1e-9 if y_ref is not None and y_ref.size > 0 else 1.0
    twin = make_inverted_twin_result(
        source, metric_profile,
        kpi_weights=ctx.get("kpi_weights"),
        mse_ref=mse_ref,
    )
    if twin is None:
        return None
    source_serial = _ensure_trial_serial(source)
    source.setdefault("extra", {})["immediate_inverted_twin_generated"] = True
    twin_extra = twin.setdefault("extra", {})
    twin_extra["immediate_inverted_twin"] = True
    twin_extra["inverted_from_trial_serial"] = source_serial
    twin_extra["inverted_from_readout"] = source.get("readout")
    twin_extra["inverted_from_seed"] = source.get("seed")
    twin_extra["inversion_reason"] = (
        f"immediate_low_overall<={threshold:g}_std={std_val:.6g}_peaks={n_peaks}"
    )
    return twin


def _progress(done, total, r):
    pct = done / total * 100
    now = time.perf_counter()
    state = getattr(_progress, "_state", None)
    if (
        state is None
        or state.get("total") != total
        or done <= 1
        or done < state.get("last_done", 0)
    ):
        state = {"total": total, "start": now, "last_done": 0}
        setattr(_progress, "_state", state)
    state["last_done"] = done
    elapsed = max(0.0, now - state["start"])
    sec_per_trial = elapsed / done if done > 0 else 0.0
    remaining = max(0, total - done)
    eta_seconds = sec_per_trial * remaining if sec_per_trial > 0 else 0.0
    trials_per_min = 60.0 / sec_per_trial if sec_per_trial > 0 else 0.0
    b = r.get("bank", "")
    bank_display = _display_bank(b)
    extra = r.get("extra", {})
    if extra.get("score_kind") == "event":
        score_detail = (f"overall={r['overall_kpi']:.4f} "
                        f"f1={extra.get('event_f1', 0.0):.3f} "
                        f"r={extra.get('event_recall', 0.0):.3f} "
                        f"bal={extra.get('event_bal_acc', 0.0):.3f}")
    else:
        score_detail = (f"overall={r['overall_kpi']:.4f} "
                        f"fit={extra.get('score_components', {}).get('fit', 0.0):.3f} "
                        f"mse={r['mse_test']:.4f}")
    print(f"[{done:3d}/{total}] {pct:5.1f}%  "
          f"eta={_format_duration(eta_seconds)} "
          f"speed={sec_per_trial:.1f}s/tr {trials_per_min:.1f}tr/min  "
          f"{bank_display:18s} {r['readout']:20s} seed={r['seed']} "
          f"{score_detail}")
    _append_incremental_trial_row(r)
    _update_incremental_best3(r)
    twin = _maybe_make_immediate_inverted_twin(r)
    if twin is not None:
        _append_incremental_trial_row(twin)
        _update_incremental_best3(twin)
        twin_extra = twin.get("extra", {}) or {}
        print("        INV immediate "
              f"T{int(twin_extra.get('trial_serial', 0)):05d} "
              f"from T{int(twin_extra.get('inverted_from_trial_serial', 0)):05d} "
              f"{_display_bank(twin.get('bank', ''))}/{twin.get('readout', '')} "
              f"overall={twin.get('overall_kpi', 0.0):.4f}")
        return [twin]
    return []


def _parse_hidden(s):
    if not s:
        return None
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _parse_csv_arg(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_float_csv(value):
    return [float(item) for item in _parse_csv_arg(value)]


def _parse_seeds_spec(value, derived_count=None):
    """Interpreta --seeds nei formati supportati.

    Ritorna una lista di interi.
    Formati:
      "5"          -> [0,1,2,3,4]              (count puro, default storico)
      "4:3"        -> [4,5,6]                  (BASE:COUNT)
      "4+3"        -> [4,5,6]                  (BASE+COUNT, alias)
      "@4"         -> [4,5,6,7,8]              (BASE soltanto, count = derived_count or 5)
      "seed:4"     -> [4,5,6,7,8]              (alias di "@4")
      "1,2,9"      -> [1,2,9]                  (lista esatta)
    """
    if isinstance(value, int):
        return list(range(max(1, value)))
    raw = str(value or "").strip()
    if not raw:
        return [0]
    # Lista esatta
    if "," in raw:
        out = []
        for tok in raw.split(","):
            tok = tok.strip()
            if not tok:
                continue
            out.append(int(tok))
        if not out:
            raise ValueError(f"--seeds lista vuota: {value!r}")
        return out
    # BASE:COUNT o seed:BASE
    if ":" in raw:
        left, right = raw.split(":", 1)
        left = left.strip()
        right = right.strip()
        if left.lower() in ("seed", "s", "base"):
            base = int(right)
            count = int(derived_count) if derived_count else 5
            return [base + i for i in range(max(1, count))]
        base = int(left)
        count = int(right)
        return [base + i for i in range(max(1, count))]
    if "+" in raw and not raw.startswith("+") and not raw.startswith("-"):
        left, right = raw.split("+", 1)
        base = int(left)
        count = int(right)
        return [base + i for i in range(max(1, count))]
    if raw.startswith("@"):
        base = int(raw[1:])
        count = int(derived_count) if derived_count else 5
        return [base + i for i in range(max(1, count))]
    # Plain integer: count puro (compat storica)
    n = int(raw)
    if n < 0:
        raise ValueError(f"--seeds negativo non supportato: {value!r}")
    if n == 0:
        return [0]
    return list(range(n))


def _arg_provided(dest):
    flag = "--" + str(dest).replace("_", "-")
    return any(arg == flag or arg.startswith(flag + "=") for arg in sys.argv[1:])


def _inherit_index_path(path):
    path = str(path or "").strip()
    if not path:
        return ""
    if os.path.isdir(path):
        path = os.path.join(path, "best_trials_index.csv")
    return path


def _json_cell(value, default=None):
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _row_score(row):
    for key in ("overall_mean", "overall", "kpi_mean"):
        try:
            return float(row.get(key))
        except (TypeError, ValueError):
            continue
    return 0.0


def _read_inherit_index(path):
    index_path = _inherit_index_path(path)
    if not index_path or not os.path.exists(index_path):
        raise ValueError(f"Indice inherit non trovato: {path}")
    with open(index_path, newline="") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r.get("bank") and r.get("readout")]
    if not rows:
        raise ValueError(f"Indice inherit senza trial utilizzabili: {index_path}")
    rows.sort(key=_row_score, reverse=True)
    return index_path, rows


_ALWAYS_INCLUDE_DEFAULT = "lcs,lcs_hybrid"


# ---------------------------------------------------------------------
# CLI presets
# ---------------------------------------------------------------------
# Permettono di evitare lunghe catene di flag. Si attivano con
# `--preset NAME` (anche piu' nomi separati da virgola). Le definizioni
# sono ordinate: i preset successivi possono ereditare via `extends` un
# preset gia' definito (max una catena, niente cicli).
#
# Comportamento di merge: gli argomenti del preset vengono iniettati
# prima degli argomenti utente, quindi l'utente puo' sempre sovrascrivere
# (last-write-wins di argparse). Per attivare piu' preset componibili
# usa: --preset japan-event-l1,shape-strict.

PRESETS = {
    "japan-event-base": {
        "description": "Configurazione base Japan event-based: target window 1 evento, "
                        "backtest 1 finestra, recent validation, ranking + training "
                        "recency-aware. Non include forecast/hybrid/LCS/seeds: usalo "
                        "come fondamenta o aggiungilo a un altro preset.",
        "args": [
            "--metric-mode", "auto",
            "--metric-target-threshold", "0.1",
            "--metric-prediction-threshold", "0.5",
            "--event-score-mode", "isolation",
            "--target-window-threshold", "0.1",
            "--target-window-event-count", "1",
            "--target-window-pre-records", "5",
            "--target-window-post-records", "3",
            "--isolated-event-windows",
            "--backtest-event-windows",
            "--backtest-event-count", "2",
            "--backtest-step-events", "1",
            "--backtest-pre-records", "5",
            "--backtest-post-records", "3",
            "--backtest-min-train-events", "2",
            "--backtest-max-windows", "1",
            "--backtest-recency-weight", "exp",
            "--backtest-recency-strength", "1.0",
            "--recent-validation-window",
            "--recent-validation-event-count", "1",
            "--recent-validation-pre-records", "5",
            "--recent-validation-post-records", "3",
            "--recent-validation-weight", "3.0",
            "--train-recency-weight", "exp",
            "--train-recency-strength", "1.0",
            "--train-event-weight", "auto",
            "--train-max-event-weight", "8.0",
        ],
    },
    "japan-event": {
        "description": "Run completo Japan event-based: base + forecast 2026 + hybrid LCS "
                        "esteso (passthrough/random_projection ridge + deep tiny/small) "
                        "+ final-eval default. 4 seed da base 4, max-iter 300.",
        "extends": "japan-event-base",
        "args": [
            "--forecast-start-date", "2026-03-05",
            "--forecast-end-date", "2026-12-30",
            "--forecast-trainset", "train2forecast",
            "--enable-lcs-in-max",
            "--hybrid-lcs",
            "--hybrid-partners",
            "passthrough:ridge,random_projection:ridge,deep:tiny,deep:small",
            "--hybrid-modes", "and,weighted",
            "--hybrid-alphas", "0.35,0.5,0.75",
            "--hybrid-threshold", "0.5",
            "--final-eval-rank-power", "1.0",
            "--final-eval-low-threshold", "1e-9",
            "--final-eval-negative-weight", "3.0",
            "--seeds", "4:4",
            "--max-iter", "300",
        ],
    },
    "japan-event-l1": {
        "description": "japan-event + auto-inherit L1 (un livello di refinement automatico "
                        "sui best del run principale, sempre LCS+hybrid inclusi).",
        "extends": "japan-event",
        "args": ["--auto-inherit-levels", "1"],
    },
    "japan-event-l3": {
        "description": "japan-event + auto-inherit L3 (refinement aggressivo a 3 livelli). "
                        "Ogni livello eredita dai best del precedente + always-include.",
        "extends": "japan-event",
        "args": ["--auto-inherit-levels", "3"],
    },
    "japan-event-posthyb": {
        "description": "japan-event senza auto-inherit: dopo il run principale esegue "
                        "automaticamente post_hybrid_artifacts sul best_trials_index prodotto.",
        "extends": "japan-event",
        "args": ["--post-hybrid-artifacts"],
    },
    "japan-event-fast": {
        "description": "Smoke test rapido Japan event-based: baseline puri + LCS default, "
                        "no hybrid, 2 seed, max-iter 100. Per controllo finestre/forecast.",
        "extends": "japan-event-base",
        "args": [
            "--banks", "passthrough,random_projection",
            "--readouts", "ridge",
            "--lcs-presets", "default",
            "--seeds", "2",
            "--max-iter", "100",
            "--forecast-start-date", "2026-03-05",
            "--forecast-end-date", "2026-12-30",
            "--forecast-trainset", "train2forecast",
        ],
    },
    "shape-strict": {
        "description": "Shape filter aggressivo per final evaluation: best=0.15, worst=0.05, "
                        "power=2.0. Componibile con qualunque altro preset.",
        "args": [
            "--final-eval-best-fraction", "0.15",
            "--final-eval-worst-fraction", "0.05",
            "--final-eval-shape-power", "2.0",
        ],
    },
    "shape-off": {
        "description": "Disattiva shape filter (per confronto con vecchio comportamento "
                        "negative-inertia). Componibile con qualunque altro preset.",
        "args": ["--no-final-eval-shape-filter"],
    },
    "hybrid-deep-extended": {
        "description": "Hybrid partner DeepNet esteso a tiny+small+default+wide. Componibile: "
                        "sovrascrive --hybrid-partners se presente in un altro preset.",
        "args": [
            "--hybrid-lcs",
            "--hybrid-partners",
            "passthrough:ridge,random_projection:ridge,deep:tiny,deep:small,deep:default,deep:wide",
        ],
    },
}


def _resolve_preset_args(name, _seen=None):
    """Espande il preset name in lista di args (ricorsivo via extends).

    Solleva ValueError se il preset non esiste o se c'e' un ciclo di extends.
    """
    if _seen is None:
        _seen = set()
    name = name.strip()
    if not name:
        return []
    if name in _seen:
        raise ValueError(f"--preset cycle: {name}")
    if name not in PRESETS:
        avail = ", ".join(sorted(PRESETS))
        raise ValueError(f"--preset sconosciuto: '{name}'. Disponibili: {avail}")
    _seen.add(name)
    out = []
    parent = PRESETS[name].get("extends")
    if parent:
        out.extend(_resolve_preset_args(parent, _seen))
    out.extend(list(PRESETS[name].get("args") or []))
    return out


def _expand_preset_argv(argv):
    """Sostituisce '--preset NAME[,NAME2]' nella lista argv con gli args del preset.

    Supporta sia '--preset NAME' che '--preset=NAME'. La sostituzione e'
    posizionale: il preset viene espanso al posto del flag, cosi' i flag
    successivi dell'utente possono sovrascriverlo.
    """
    out = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--preset":
            if i + 1 >= len(argv):
                raise ValueError("--preset richiede un nome (es. --preset japan-event-l1)")
            names = argv[i + 1]
            for name in names.split(","):
                out.extend(_resolve_preset_args(name))
            i += 2
        elif tok.startswith("--preset="):
            names = tok.split("=", 1)[1]
            for name in names.split(","):
                out.extend(_resolve_preset_args(name))
            i += 1
        else:
            out.append(tok)
            i += 1
    return out


def _print_presets_and_exit():
    print("CLI presets disponibili:")
    print("  Uso: --preset NAME oppure --preset N1,N2 (componibile)")
    print()
    for name in sorted(PRESETS):
        p = PRESETS[name]
        desc = p.get("description", "(no description)")
        ext = p.get("extends")
        ext_lbl = f" [extends: {ext}]" if ext else ""
        print(f"  {name}{ext_lbl}")
        for line in _wrap_help(desc, indent=6):
            print(line)
        print()
    sys.exit(0)


def _wrap_help(text, indent=4, width=80):
    import textwrap
    return textwrap.wrap(text, width=width,
                         initial_indent=" " * indent,
                         subsequent_indent=" " * indent)


def _resolve_always_include_banks(args):
    """Risolvi --always-include in lista di bank slug interni.

    Token speciali:
      lcs                -> __lcs__
      lcs_hybrid|hybrid  -> __hybrid__
      kan                -> __kan__
      kan_hybrid         -> __kan_hybrid__
    Altri token sono usati come bank name letterale.
    """
    if bool(getattr(args, "no_always_include", False)):
        return []
    raw = str(getattr(args, "always_include", _ALWAYS_INCLUDE_DEFAULT) or "")
    out = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        low = tok.lower()
        if low == "lcs":
            out.append("__lcs__")
        elif low in ("lcs_hybrid", "lcs-hybrid", "hybrid"):
            out.append("__hybrid__")
        elif low == "kan":
            out.append("__kan__")
        elif low in ("kan_hybrid", "kan-hybrid"):
            out.append("__kan_hybrid__")
        else:
            out.append(tok)
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def _select_inherited_rows(rows, best_n, include_best_bank=False, always_include_banks=None):
    best_n = max(1, int(best_n or 1))
    selected = list(rows[:best_n])
    if include_best_bank:
        seen_banks = set()
        for row in rows:
            bank = row.get("bank")
            if bank in seen_banks:
                continue
            selected.append(row)
            seen_banks.add(bank)
            if len(seen_banks) >= best_n:
                break
    if always_include_banks:
        for bank in always_include_banks:
            for row in rows:
                if row.get("bank") == bank:
                    selected.append(row)
                    break
    out = []
    seen = set()
    for row in selected:
        key = (row.get("bank"), row.get("readout"))
        if key in seen:
            continue
        out.append(row)
        seen.add(key)
    out.sort(key=_row_score, reverse=True)
    return out


def _deep_preset_from_readout(readout):
    readout = str(readout or "")
    if readout == "deepnet_custom":
        return "custom"
    if readout.startswith("deepnet_"):
        return readout[len("deepnet_"):]
    return None


def _lcs_preset_from_readout(readout):
    readout = str(readout or "")
    if readout == "ucs_custom":
        return "custom"
    if readout.startswith("ucs_"):
        return readout[len("ucs_"):]
    return None


def _kan_preset_from_readout(readout):
    readout = str(readout or "")
    if readout.startswith("kan_"):
        return readout[len("kan_"):]
    return None


def _set_arg_from_params(args, params, key):
    if key not in params or _arg_provided(key):
        return
    setattr(args, key, params[key])


def _apply_inherited_run(args):
    inherit_path = getattr(args, "inherit", "") or getattr(args, "inherit_from", "")
    if not inherit_path:
        args._inherit_trial_filter = None
        args._inherit_summary = None
        return

    index_path, rows = _read_inherit_index(inherit_path)
    include_best_bank = bool(getattr(args, "inherit_best_bank", False))
    if getattr(args, "inherit_no_best_bank", False):
        include_best_bank = False
    always_banks = _resolve_always_include_banks(args)
    selected = _select_inherited_rows(
        rows,
        getattr(args, "best", 5),
        include_best_bank=include_best_bank,
        always_include_banks=always_banks,
    )
    params = _json_cell(selected[0].get("params"), default={}) or {}

    inherit_keys = [
        "task", "target_cols_list", "skip_cols_list",
        "n_train", "n_test", "noise", "db", "verbose",
        "w_mse", "w_speed", "w_params",
        "metric_mode", "metric_target_threshold",
        "metric_prediction_threshold", "event_score_mode",
        "no_final_evaluation", "final_eval_rank_power",
        "final_eval_low_threshold", "no_final_eval_negative_inertia",
        "final_eval_negative_weight",
        "no_final_eval_shape_filter", "final_eval_best_fraction",
        "final_eval_worst_fraction", "final_eval_shape_power",
        "readability_weight", "readability_floor",
        "always_include", "no_always_include",
        "target_window_threshold", "target_window_event_count",
        "target_window_event_start", "target_window_pre_records",
        "target_window_post_records", "suppress_autodate_clipping",
        "force_autoclip", "no_autoclip", "time_series",
        "allow_train_after_test", "train_start_date", "train_end_date",
        "forecast_start_date", "forecast_end_date", "forecast_trainset",
        "backtest_event_windows", "backtest_event_count",
        "backtest_pre_records", "backtest_post_records",
        "backtest_step_events", "backtest_min_train_events",
        "backtest_max_windows", "backtest_include_final_window",
        "backtest_recency_weight", "backtest_recency_strength",
        "recent_validation_window", "recent_validation_event_count",
        "recent_validation_pre_records", "recent_validation_post_records",
        "recent_validation_min_train_events", "recent_validation_weight",
        "validation_max_lookback_records",
        "no_train_sample_weighting", "train_recency_weight",
        "train_recency_strength", "train_event_weight",
        "train_max_event_weight", "deep_activation", "deep_batch_norm",
        "deep_batch_size", "deep_custom", "deep_device", "deep_dropout",
        "deep_epochs", "deep_hidden", "deep_lr", "deep_weight_decay",
        "deep_validation_metric", "deep_validation_threshold",
        "deep_val_target_threshold", "deep_val_event_count",
        "deep_val_pre_records", "deep_val_post_records",
        "lcs_custom", "lcs_population_size", "lcs_epochs",
        "lcs_ga_frequency", "lcs_mutation_rate", "lcs_crossover_rate",
        "lcs_wildcard_prob", "lcs_positive_wildcard_prob",
        "lcs_positive_covering_multiplier", "lcs_tournament_size",
        "lcs_seed", "lcs_binary_threshold", "lcs_validation_split",
        "lcs_val_event_count", "lcs_val_event_start",
        "lcs_val_pre_records", "lcs_val_post_records",
        "isolated_event_windows", "lcs_early_stop_patience",
        "lcs_no_restore_best", "lcs_no_final_retrain",
        "lcs_fitness_mode", "lcs_positive_weight",
        "lcs_max_positive_weight", "lcs_positive_replay",
        "lcs_max_positive_replay", "lcs_positive_vote_weight",
        "lcs_max_positive_vote_weight", "lcs_selection_metric",
        "lcs_export_rule_count",
        "lcs_max_active_conditions", "lcs_min_fitness_for_subsumption",
        "hybrid_lcs", "hybrid_modes",
        "hybrid_alphas", "hybrid_threshold", "hybrid_partners",
        "enable_kan", "kan_presets", "all_kan_presets",
        "hybrid_kan", "enable_kan_in_max", "kan_device",
        "max_iter", "seeds", "jobs", "invert_twin_immediate_threshold",
    ]
    for key in inherit_keys:
        _set_arg_from_params(args, params, key)

    bank_readouts = set()
    deep_labels = set()
    lcs_labels = set()
    hybrid_readouts = set()
    kan_labels = set()
    kan_hybrid_readouts = set()
    deep_presets = set()
    lcs_presets = set()
    kan_presets = set()

    for row in selected:
        bank = row.get("bank")
        readout = row.get("readout")
        if bank == "__none__":
            deep_labels.add(readout)
            preset = _deep_preset_from_readout(readout)
            if preset == "custom":
                args.deep_custom = True
            elif preset:
                deep_presets.add(preset)
        elif bank == "__lcs__":
            lcs_labels.add(readout)
            preset = _lcs_preset_from_readout(readout)
            if preset == "custom":
                args.lcs_custom = True
            elif preset:
                lcs_presets.add(preset)
        elif bank == "__hybrid__":
            hybrid_readouts.add(readout)
            args.hybrid_lcs = True
            if "cus" in str(readout):
                args.lcs_custom = True
        elif bank == "__kan__":
            kan_labels.add(readout)
            preset = _kan_preset_from_readout(readout)
            if preset:
                kan_presets.add(preset)
            args.enable_kan = True
        elif bank == "__kan_hybrid__":
            kan_hybrid_readouts.add(readout)
            args.hybrid_kan = True
            args.enable_kan = True
        else:
            bank_readouts.add((bank, readout))

    args.all_banks = False
    args.all_readouts = False
    args.all_deep_presets = False
    args.all_lcs_presets = False
    if bank_readouts:
        args.no_banks = False
        args.banks = ",".join(sorted({b for b, _ in bank_readouts}))
        args.readouts = ",".join(sorted({r for _, r in bank_readouts}))
    else:
        args.no_banks = True
        args.banks = ""
    args.deep_presets = ",".join(sorted(deep_presets))
    args.lcs_presets = ",".join(sorted(lcs_presets))
    args.kan_presets = ",".join(sorted(kan_presets))
    if not lcs_labels and not hybrid_readouts and not lcs_presets:
        args.lcs_custom = False
        args.lcs_presets = ""
    if not hybrid_readouts:
        args.hybrid_lcs = False
    if not kan_labels and not kan_hybrid_readouts and not kan_presets:
        args.enable_kan = False
        args.kan_presets = ""
    if not kan_hybrid_readouts:
        args.hybrid_kan = False

    args._inherit_trial_filter = {
        "bank_readouts": bank_readouts,
        "deep_labels": deep_labels,
        "lcs_labels": lcs_labels,
        "hybrid_readouts": hybrid_readouts,
        "kan_labels": kan_labels,
        "kan_hybrid_readouts": kan_hybrid_readouts,
    }
    args._inherit_summary = {
        "index_path": index_path,
        "requested_best": int(getattr(args, "best", 5) or 5),
        "always_include": list(always_banks),
        "selected": [
            {
                "bank": row.get("bank"),
                "readout": row.get("readout"),
                "score": _row_score(row),
            }
            for row in selected
        ],
    }


def _resolve_deep_val_cfg(args):
    event_count = int(getattr(args, "deep_val_event_count", 0) or 0)
    if event_count <= 0:
        event_count = int(getattr(args, "lcs_val_event_count", 0) or 0)
    threshold = getattr(args, "deep_val_target_threshold", None)
    if threshold is None:
        threshold = _resolve_lcs_binary_threshold(args)
    pre_records = int(getattr(args, "deep_val_pre_records", -1))
    post_records = int(getattr(args, "deep_val_post_records", -1))
    if pre_records < 0:
        pre_records = int(getattr(args, "lcs_val_pre_records", 0) or 0)
    if post_records < 0:
        post_records = int(getattr(args, "lcs_val_post_records", 0) or 0)
    validation_metric = str(getattr(args, "deep_validation_metric", "mse") or "mse")
    validation_threshold = getattr(args, "deep_validation_threshold", None)
    if validation_threshold is None:
        validation_threshold = getattr(args, "deep_val_target_threshold", None)
    if validation_threshold is None:
        validation_threshold = getattr(args, "metric_target_threshold", None)
    if validation_threshold is None:
        validation_threshold = getattr(args, "target_window_threshold", None)
    if validation_threshold is None:
        validation_threshold = getattr(args, "lcs_binary_threshold", None)
    if validation_threshold is None:
        validation_threshold = 0.5
    return {
        "threshold": threshold,
        "event_count": event_count,
        "pre_records": pre_records,
        "post_records": post_records,
        "validation_metric": validation_metric,
        "validation_threshold": validation_threshold,
        "isolated_windows": bool(getattr(args, "isolated_event_windows", False)),
    }


def _build_custom_deep_cfg(args):
    if not args.deep_custom:
        return None
    if not TORCH_AVAILABLE:
        print("ERRORE: torch non installato, --deep-custom non disponibile")
        sys.exit(1)
    deep_val = _resolve_deep_val_cfg(args)
    return DeepConfig(
        hidden_sizes=_parse_hidden(args.deep_hidden),
        activation=args.deep_activation,
        dropout=args.deep_dropout,
        batch_norm=args.deep_batch_norm,
        epochs=args.max_iter if args.max_iter is not None else args.deep_epochs,
        batch_size=args.deep_batch_size,
        lr=args.deep_lr,
        weight_decay=args.deep_weight_decay,
        target_window_threshold=deep_val["threshold"],
        target_window_event_count=deep_val["event_count"],
        target_window_pre_records=deep_val["pre_records"],
        target_window_post_records=deep_val["post_records"],
        target_window_isolated_windows=deep_val["isolated_windows"],
        validation_metric=deep_val["validation_metric"],
        validation_threshold=deep_val["validation_threshold"],
        device=args.deep_device,
        verbose=args.verbose,
    )


def _resolve_lcs_binary_threshold(args):
    if getattr(args, "lcs_binary_threshold", None) is not None:
        return args.lcs_binary_threshold
    if getattr(args, "target_window_threshold", None) is not None:
        return args.target_window_threshold
    return LCSConfig().binary_threshold


def _resolve_lcs_seed(args):
    return int(getattr(args, "lcs_seed", 0) or 0)


def _build_custom_lcs_cfg(args):
    if not getattr(args, "lcs_custom", False):
        return None
    return LCSConfig(
        population_size=args.lcs_population_size,
        epochs=args.max_iter if args.max_iter is not None else args.lcs_epochs,
        ga_frequency=args.lcs_ga_frequency,
        mutation_rate=args.lcs_mutation_rate,
        crossover_rate=args.lcs_crossover_rate,
        wildcard_prob=args.lcs_wildcard_prob,
        positive_wildcard_prob=args.lcs_positive_wildcard_prob,
        positive_covering_multiplier=args.lcs_positive_covering_multiplier,
        tournament_size=args.lcs_tournament_size,
        binary_threshold=_resolve_lcs_binary_threshold(args),
        validation_split=args.lcs_validation_split,
        validation_event_count=args.lcs_val_event_count,
        validation_event_start=args.lcs_val_event_start,
        validation_pre_records=args.lcs_val_pre_records,
        validation_post_records=args.lcs_val_post_records,
        validation_isolated_windows=bool(getattr(args, "isolated_event_windows", False)),
        early_stop_patience=args.lcs_early_stop_patience,
        restore_best_population=not args.lcs_no_restore_best,
        final_retrain_full_train=not args.lcs_no_final_retrain,
        fitness_mode=args.lcs_fitness_mode,
        positive_weight=args.lcs_positive_weight,
        max_positive_weight=args.lcs_max_positive_weight,
        positive_replay=args.lcs_positive_replay,
        max_positive_replay=args.lcs_max_positive_replay,
        positive_vote_weight=args.lcs_positive_vote_weight,
        max_positive_vote_weight=args.lcs_max_positive_vote_weight,
        selection_metric=args.lcs_selection_metric,
        max_active_conditions=(int(args.lcs_max_active_conditions)
                               if int(args.lcs_max_active_conditions or 0) > 0 else None),
        export_rule_count=max(1, int(getattr(args, "lcs_export_rule_count", 20) or 20)),
        min_fitness_for_subsumption=float(args.lcs_min_fitness_for_subsumption),
        seed=_resolve_lcs_seed(args),
        verbose=args.verbose,
    )


def _resolve_target_window_threshold(args):
    if args.target_window_threshold is not None:
        return args.target_window_threshold
    if args.target_window_event_count > 0:
        return 0.0
    return None


def _resolve_deep_preset_cfgs(deep_presets, args):
    deep_val = _resolve_deep_val_cfg(args)
    out = {}
    for name in deep_presets:
        cfg = DEEP_PRESETS.get(name)
        if cfg is None:
            continue
        out[name] = DeepConfig(**{
            **cfg.__dict__,
            "target_window_threshold": deep_val["threshold"],
            "target_window_event_count": deep_val["event_count"],
            "target_window_pre_records": deep_val["pre_records"],
            "target_window_post_records": deep_val["post_records"],
            "target_window_isolated_windows": deep_val["isolated_windows"],
            "validation_metric": deep_val["validation_metric"],
            "validation_threshold": deep_val["validation_threshold"],
        })
    return out


def _load_extra_deep_presets(path: str) -> dict:
    text = str(path or "").strip()
    if not text:
        return {}
    cfg_path = os.path.abspath(os.path.expanduser(text))
    with open(cfg_path, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict) and "presets" in payload:
        items = payload.get("presets") or []
    elif isinstance(payload, dict):
        items = [{"name": k, **(v or {})} for k, v in payload.items()]
    else:
        raise ValueError("--deep-preset-configs-json deve contenere un oggetto o {'presets': [...]}")

    valid = set(DeepConfig.__dataclass_fields__)
    out = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        cfg_payload = {k: v for k, v in item.items() if k in valid}
        out[name] = DeepConfig(**cfg_payload)
    return out


def _resolve_lcs_preset_cfgs(lcs_presets, args):
    threshold = _resolve_lcs_binary_threshold(args)
    seed = _resolve_lcs_seed(args)
    out = {}
    for name in lcs_presets:
        cfg = LCS_PRESETS.get(name)
        if cfg is None:
            continue
        epochs = args.max_iter if args.max_iter is not None else cfg.epochs
        out[name] = LCSConfig(
            population_size=cfg.population_size,
            epochs=epochs,
            ga_frequency=cfg.ga_frequency,
            mutation_rate=cfg.mutation_rate,
            crossover_rate=cfg.crossover_rate,
            wildcard_prob=cfg.wildcard_prob,
            positive_wildcard_prob=args.lcs_positive_wildcard_prob,
            positive_covering_multiplier=args.lcs_positive_covering_multiplier,
            tournament_size=cfg.tournament_size,
            fitness_alpha=cfg.fitness_alpha,
            fitness_beta=cfg.fitness_beta,
            deletion_threshold=cfg.deletion_threshold,
            do_subsumption=cfg.do_subsumption,
            min_fitness_for_subsumption=float(args.lcs_min_fitness_for_subsumption),
            binary_threshold=threshold,
            validation_split=args.lcs_validation_split,
            validation_event_count=args.lcs_val_event_count,
            validation_event_start=args.lcs_val_event_start,
            validation_pre_records=args.lcs_val_pre_records,
            validation_post_records=args.lcs_val_post_records,
            validation_isolated_windows=bool(getattr(args, "isolated_event_windows", False)),
            early_stop_patience=args.lcs_early_stop_patience,
            restore_best_population=not args.lcs_no_restore_best,
            final_retrain_full_train=not args.lcs_no_final_retrain,
            fitness_mode=args.lcs_fitness_mode,
            positive_weight=args.lcs_positive_weight,
            max_positive_weight=args.lcs_max_positive_weight,
            positive_replay=args.lcs_positive_replay,
            max_positive_replay=args.lcs_max_positive_replay,
            positive_vote_weight=args.lcs_positive_vote_weight,
            max_positive_vote_weight=args.lcs_max_positive_vote_weight,
            selection_metric=args.lcs_selection_metric,
            max_active_conditions=(int(args.lcs_max_active_conditions)
                                   if int(args.lcs_max_active_conditions or 0) > 0 else None),
            export_rule_count=max(1, int(getattr(args, "lcs_export_rule_count", 20) or 20)),
            seed=seed,
            verbose=args.verbose,
        )
    return out


def _resolve_kan_preset_cfgs(kan_presets, args):
    out = {}
    kan_quiet = bool(getattr(args, "kan_quiet", False))
    for name in kan_presets:
        cfg = KAN_PRESETS.get(name)
        if cfg is None:
            continue
        epochs = args.max_iter if args.max_iter is not None else cfg.epochs
        out[name] = KANConfig(
            hidden_width=cfg.hidden_width,
            hidden_layers=cfg.hidden_layers,
            grid=cfg.grid,
            spline_order=cfg.spline_order,
            epochs=epochs,
            lr=cfg.lr,
            lamb=cfg.lamb,
            opt=cfg.opt,
            seed=cfg.seed,
            device=getattr(args, "kan_device", "cpu"),
            update_grid=cfg.update_grid,
            scale_features=cfg.scale_features,
            target_scale=cfg.target_scale,
            verbose=(bool(getattr(args, "verbose", False)) and not kan_quiet),
        )
    return out


def _target_window_requested(args):
    return (_resolve_target_window_threshold(args) is not None
            or args.target_window_event_count > 0
            or args.target_window_event_start is not None
            or args.target_window_pre_records > 0
            or args.target_window_post_records > 0)


def _resolve_target_window_cfg(args):
    if not _target_window_requested(args):
        return None
    return {
        "threshold": _resolve_target_window_threshold(args),
        "event_count": args.target_window_event_count,
        "event_start": args.target_window_event_start,
        "pre_records": args.target_window_pre_records,
        "post_records": args.target_window_post_records,
        "isolated_windows": bool(getattr(args, "isolated_event_windows", False)),
        "suppress_autodate_clipping": args.suppress_autodate_clipping,
        "force_autoclip": args.force_autoclip,
        "no_autoclip": args.no_autoclip,
        "time_series": args.time_series,
        "allow_train_after_test": args.allow_train_after_test,
    }


def _resolve_metric_threshold(args):
    if args.metric_target_threshold is not None:
        return args.metric_target_threshold
    if args.target_window_threshold is not None:
        return args.target_window_threshold
    return None


def _resolve_metric_prediction_threshold(args):
    value = getattr(args, "metric_prediction_threshold", None)
    if value is None:
        return None
    return float(value)


def _value_has_time(value):
    s = str(value or "").strip()
    if not s:
        return False
    return ("T" in s) or (":" in s)


def _parse_cli_datetime(value, *, end_of_day=False):
    dt = parse_datetime_like(value)
    if dt is None:
        raise ValueError(f"Data/ora non valida: {value}")
    if end_of_day and not _value_has_time(value):
        dt = dt + timedelta(days=1) - timedelta(microseconds=1)
    return dt


def _forecast_window_requested(args):
    return bool(getattr(args, "forecast_start_date", ""))


def _resolve_forecast_window_cfg(args):
    if not _forecast_window_requested(args):
        return None
    start_raw = args.forecast_start_date
    end_raw = args.forecast_end_date or None
    start_dt = _parse_cli_datetime(start_raw, end_of_day=False)
    end_dt = _parse_cli_datetime(end_raw, end_of_day=True) if end_raw else None
    if end_dt is not None and end_dt < start_dt:
        raise ValueError("--forecast-end-date deve essere >= --forecast-start-date")
    return {
        "start_raw": start_raw,
        "end_raw": end_raw,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


def _resolve_train_range_cfg(args):
    start_raw = getattr(args, "train_start_date", "")
    end_raw = getattr(args, "train_end_date", "")
    if not start_raw and not end_raw:
        return None
    start_dt = _parse_cli_datetime(start_raw, end_of_day=False) if start_raw else None
    end_dt = _parse_cli_datetime(end_raw, end_of_day=True) if end_raw else None
    if start_dt is not None and end_dt is not None and end_dt < start_dt:
        raise ValueError("--train-end-date deve essere >= --train-start-date")
    return {
        "start_raw": start_raw or None,
        "end_raw": end_raw or None,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


def _subset_csv_meta(csv_meta, start_idx, end_idx=None):
    out = dict(csv_meta)
    if end_idx is None:
        end_idx = len(csv_meta["y"]) - 1
    sl = slice(start_idx, end_idx + 1)
    out["X"] = np.asarray(csv_meta["X"][sl], dtype=float)
    out["y"] = np.asarray(csv_meta["y"][sl], dtype=float)
    if csv_meta.get("context_values") is not None:
        out["context_values"] = list(csv_meta["context_values"][sl])
    if csv_meta.get("context_datetimes") is not None:
        out["context_datetimes"] = list(csv_meta["context_datetimes"][sl])
    if csv_meta.get("row_indices") is not None:
        out["row_indices"] = np.asarray(csv_meta["row_indices"][sl], dtype=int)
    out["effective_start_index"] = int(start_idx)
    out["effective_end_index"] = int(end_idx)
    return out


def _resolve_period_segments(indices):
    idx = np.sort(np.asarray(indices, dtype=int))
    if idx.size == 0:
        return []
    segments = []
    start = prev = int(idx[0])
    for value in idx[1:]:
        value = int(value)
        if value == prev + 1:
            prev = value
            continue
        segments.append((start, prev))
        start = prev = value
    segments.append((start, prev))
    return segments


def _validation_anchor_and_min_idx(y_len, args, forecast_window=None):
    max_lookback = int(getattr(args, "validation_max_lookback_records", 0) or 0)
    if forecast_window is not None and len(forecast_window.get("indices", [])) > 0:
        anchor_idx = min(y_len - 1, int(np.min(forecast_window["indices"])) - 1)
    else:
        anchor_idx = y_len - 1
    anchor_idx = max(0, int(anchor_idx))
    if max_lookback <= 0:
        return anchor_idx, 0, 0
    min_idx = max(0, anchor_idx - max_lookback + 1)
    return anchor_idx, min_idx, max_lookback


def _resolve_backtest_window_cfgs(y, args, target_window_cfg=None,
                                  forecast_window=None):
    if not getattr(args, "backtest_event_windows", False):
        return []
    threshold = _resolve_metric_threshold(args)
    if threshold is None:
        threshold = _resolve_target_window_threshold(args)
    if threshold is None:
        raise ValueError("--backtest-event-windows richiede una soglia evento")
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    event_idx = np.flatnonzero(y_arr >= float(threshold))
    if event_idx.size == 0:
        raise ValueError("Backtest event-window richiesto, ma non ci sono eventi")

    requested_event_count = int(getattr(args, "backtest_event_count", 0) or 0)
    if requested_event_count <= 0:
        requested_event_count = int((target_window_cfg or {}).get("event_count", 0) or 1)
    requested_event_count = max(1, requested_event_count)
    step_events = max(1, int(getattr(args, "backtest_step_events", 1) or 1))
    min_train_events = max(0, int(getattr(args, "backtest_min_train_events", 4) or 0))
    max_windows = max(0, int(getattr(args, "backtest_max_windows", 0) or 0))
    pre_records = int(getattr(args, "backtest_pre_records", -1))
    post_records = int(getattr(args, "backtest_post_records", -1))
    if pre_records < 0:
        pre_records = int((target_window_cfg or {}).get("pre_records", 0) or 0)
    if post_records < 0:
        post_records = int((target_window_cfg or {}).get("post_records", 0) or 0)

    anchor_idx, validation_min_idx, max_lookback = _validation_anchor_and_min_idx(
        len(y_arr), args, forecast_window=forecast_window
    )
    event_count = requested_event_count
    starts = []
    autoclip_event_count = False
    while event_count >= 1:
        last_start = int(event_idx.size - event_count)
        if last_start < min_train_events:
            candidate_starts = []
        else:
            exclude_final = bool(target_window_cfg) and not bool(getattr(args, "backtest_include_final_window", False))
            if exclude_final:
                final_count = max(1, int((target_window_cfg or {}).get("event_count", event_count) or event_count))
                final_start = max(0, int(event_idx.size - final_count))
                last_start = min(last_start, final_start - event_count)
            candidate_starts = (
                list(range(min_train_events, last_start + 1, step_events))
                if last_start >= min_train_events else []
            )
        if max_lookback > 0:
            candidate_starts = [
                pos for pos in candidate_starts
                if int(event_idx[pos]) >= validation_min_idx
                and int(event_idx[pos + event_count - 1]) <= anchor_idx
            ]
        if candidate_starts or event_count <= 1 or max_lookback <= 0:
            starts = candidate_starts
            break
        event_count -= 1
        autoclip_event_count = True

    if not starts:
        raise ValueError(
            "Backtest non ha finestre compatibili"
            + (f" con validation_max_lookback_records={max_lookback}" if max_lookback > 0 else "")
        )
    if max_windows > 0 and len(starts) > max_windows:
        starts = starts[-max_windows:]

    base = dict(target_window_cfg or {})
    base.update({
        "threshold": float(threshold),
        "event_count": int(event_count),
        "requested_event_count": int(requested_event_count),
        "pre_records": int(pre_records),
        "post_records": int(post_records),
        "suppress_autodate_clipping": True,
        "force_autoclip": False,
        "no_autoclip": True,
        "time_series": getattr(args, "time_series", "auto"),
        "allow_train_after_test": getattr(args, "allow_train_after_test", False),
        "validation_max_lookback_records": int(max_lookback),
        "validation_min_idx": int(validation_min_idx),
        "validation_anchor_idx": int(anchor_idx),
        "autoclip_event_count": bool(autoclip_event_count),
    })
    windows = []
    for ordinal, start_pos in enumerate(starts, start=1):
        cfg = dict(base)
        cfg["event_start"] = int(start_pos)
        cfg["backtest_window_no"] = int(ordinal)
        cfg["backtest_event_start_pos"] = int(start_pos)
        cfg["backtest_event_end_pos"] = int(start_pos + event_count - 1)
        cfg["backtest_total_windows"] = int(len(starts))
        windows.append(cfg)
    return windows


def _resolve_event_window_params(args, target_window_cfg=None, prefix="recent_validation"):
    threshold = _resolve_metric_threshold(args)
    if threshold is None:
        threshold = _resolve_target_window_threshold(args)
    if threshold is None:
        raise ValueError("La validation event-window richiede una soglia evento")

    event_count = int(getattr(args, f"{prefix}_event_count", 0) or 0)
    if event_count <= 0:
        event_count = int((target_window_cfg or {}).get("event_count", 0) or 0)
    if event_count <= 0:
        event_count = int(getattr(args, "backtest_event_count", 0) or 0)
    event_count = max(1, event_count)

    pre_records = int(getattr(args, f"{prefix}_pre_records", -1))
    post_records = int(getattr(args, f"{prefix}_post_records", -1))
    if pre_records < 0:
        pre_records = int((target_window_cfg or {}).get("pre_records", 0) or 0)
    if post_records < 0:
        post_records = int((target_window_cfg or {}).get("post_records", 0) or 0)
    return float(threshold), int(event_count), int(pre_records), int(post_records)


def _resolve_recent_validation_window_cfg(y, args, target_window_cfg=None,
                                          forecast_window=None):
    if not getattr(args, "recent_validation_window", False):
        return None
    threshold, event_count, pre_records, post_records = _resolve_event_window_params(
        args, target_window_cfg=target_window_cfg, prefix="recent_validation"
    )
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    event_idx = np.flatnonzero(y_arr >= threshold)
    if event_idx.size == 0:
        raise ValueError("Recent validation richiesta, ma non ci sono eventi")

    max_idx = len(y_arr) - 1
    if forecast_window is not None and len(forecast_window.get("indices", [])) > 0:
        max_idx = min(max_idx, int(np.min(forecast_window["indices"])) - 1)
    if max_idx < 0:
        raise ValueError("Recent validation impossibile: forecast parte prima del dataset")

    eligible_end_positions = [
        pos for pos, idx in enumerate(event_idx)
        if int(idx) + post_records <= max_idx
    ]
    if not eligible_end_positions:
        raise ValueError("Recent validation impossibile: nessun evento prima del forecast")
    end_pos = int(eligible_end_positions[-1])
    requested_event_count = int(event_count)
    anchor_idx, validation_min_idx, max_lookback = _validation_anchor_and_min_idx(
        len(y_arr), args, forecast_window=forecast_window
    )
    autoclip_event_count = False
    while event_count > 1:
        candidate_start_pos = end_pos - event_count + 1
        if candidate_start_pos < 0:
            event_count -= 1
            autoclip_event_count = True
            continue
        if max_lookback <= 0 or int(event_idx[candidate_start_pos]) >= validation_min_idx:
            break
        event_count -= 1
        autoclip_event_count = True
    start_pos = end_pos - event_count + 1
    if start_pos < 0:
        raise ValueError("Recent validation impossibile: pochi eventi disponibili")
    if max_lookback > 0 and int(event_idx[start_pos]) < validation_min_idx:
        raise ValueError(
            "Recent validation impossibile: ultimo evento fuori dal limite "
            f"validation_max_lookback_records={max_lookback}"
        )

    min_train_events = int(getattr(args, "recent_validation_min_train_events", -1))
    if min_train_events < 0:
        min_train_events = max(0, int(getattr(args, "backtest_min_train_events", 4) or 0))
    if start_pos < min_train_events:
        raise ValueError(
            "Recent validation impossibile: pochi eventi storici prima della finestra "
            f"(richiesti min_train_events={min_train_events})"
        )

    base = dict(target_window_cfg or {})
    base.update({
        "threshold": float(threshold),
        "event_count": int(event_count),
        "requested_event_count": int(requested_event_count),
        "event_start": int(start_pos),
        "pre_records": int(pre_records),
        "post_records": int(post_records),
        "suppress_autodate_clipping": True,
        "force_autoclip": False,
        "no_autoclip": True,
        "time_series": getattr(args, "time_series", "auto"),
        "allow_train_after_test": getattr(args, "allow_train_after_test", False),
        "recent_validation_event_start_pos": int(start_pos),
        "recent_validation_event_end_pos": int(end_pos),
        "recent_validation_max_idx": int(max_idx),
        "validation_max_lookback_records": int(max_lookback),
        "validation_min_idx": int(validation_min_idx),
        "validation_anchor_idx": int(anchor_idx),
        "autoclip_event_count": bool(autoclip_event_count),
        "random_negative_count": max(0, int(getattr(args, "recent_validation_random_negatives", 0) or 0)),
        "random_negative_seed": int(getattr(args, "recent_validation_random_seed", 0) or 0),
    })
    return base


def _backtest_recency_weight(window_no, total_windows, args):
    mode = str(getattr(args, "backtest_recency_weight", "none") or "none").lower()
    strength = max(0.0, float(getattr(args, "backtest_recency_strength", 1.0) or 0.0))
    if mode == "none" or total_windows <= 0:
        return 1.0
    progress = 1.0 if total_windows <= 1 else (int(window_no) - 1) / float(total_windows - 1)
    if mode == "linear":
        return float(1.0 + strength * progress)
    if mode == "exp":
        return float(math.exp(strength * progress))
    return 1.0


def _resolve_training_weight_cfg(args, metric_threshold=None):
    if getattr(args, "no_train_sample_weighting", False):
        return {"enabled": False}
    event_weight = getattr(args, "train_event_weight", "auto")
    return {
        "enabled": True,
        "recency_mode": getattr(args, "train_recency_weight", "exp"),
        "recency_strength": float(getattr(args, "train_recency_strength", 1.0) or 0.0),
        "event_weight": event_weight,
        "max_event_weight": float(getattr(args, "train_max_event_weight", 8.0) or 8.0),
        "event_threshold": metric_threshold,
    }


def _format_context_value(csv_meta, idx):
    context_values = csv_meta.get("context_values")
    if context_values is None:
        return str(idx)
    return str(context_values[int(idx)])


def _print_period_summary(label, indices, csv_meta):
    segments = _resolve_period_segments(indices)
    if not segments:
        return
    if len(segments) > 3:
        start_idx = segments[0][0]
        end_idx = segments[-1][1]
        print(f"{label}: {len(indices)} record, {len(segments)} segmenti non contigui,"
              f" range={_format_context_value(csv_meta, start_idx)} -> {_format_context_value(csv_meta, end_idx)}"
              f" (row {int(csv_meta['row_indices'][start_idx])} -> {int(csv_meta['row_indices'][end_idx])})")
        return
    for seg_no, (start_idx, end_idx) in enumerate(segments, start=1):
        prefix = label if len(segments) == 1 else f"{label} segment {seg_no}"
        n_rows = end_idx - start_idx + 1
        print(f"{prefix}: {n_rows} record,"
              f" {_format_context_value(csv_meta, start_idx)} -> {_format_context_value(csv_meta, end_idx)}"
              f" (row {int(csv_meta['row_indices'][start_idx])} -> {int(csv_meta['row_indices'][end_idx])})")


def _resolve_time_series_cfg(args):
    return {
        "time_series": args.time_series,
        "allow_train_after_test": args.allow_train_after_test,
    }


def _resolve_forecast_fit_indices(result, n_rows, forecast_indices, mode,
                                  time_series_cfg=None, context_datetimes=None):
    artifacts = result.get("_artifacts", {})
    test_idx = np.sort(np.asarray(artifacts.get("test_indices", []), dtype=int))
    if test_idx.size == 0:
        return None, None
    forecast_indices = np.sort(np.asarray(forecast_indices, dtype=int))
    if forecast_indices.size == 0:
        return None, None
    forecast_start = int(forecast_indices[0])
    all_idx = np.arange(int(n_rows), dtype=int)
    train_idx = all_idx[~np.isin(all_idx, test_idx)]
    train_start = int(train_idx[0]) if train_idx.size else 0
    before_forecast_mask = all_idx < forecast_start

    if mode == "train+test":
        fit_idx = np.sort(np.unique(np.concatenate((train_idx, test_idx))))
        info = {
            "mode": mode,
        }
        fit_idx, info = enforce_train_before_test(
            fit_idx, forecast_indices,
            window_cfg=time_series_cfg,
            context_datetimes=context_datetimes,
            split_info=info,
            warning_label="Forecast fit window",
        )
        info["resolved_start"] = None if fit_idx.size == 0 else int(fit_idx[0])
        info["resolved_end"] = None if fit_idx.size == 0 else int(fit_idx[-1])
        info["n_rows"] = int(fit_idx.size)
        return fit_idx, info

    if mode == "train2test":
        end_idx = min(forecast_start - 1, int(np.max(test_idx)))
    elif mode == "train2forecast":
        end_idx = forecast_start - 1
    else:
        raise ValueError(f"forecast-trainset non riconosciuto: {mode}")

    if end_idx < train_start:
        return None, {
            "mode": mode,
            "resolved_start": None,
            "resolved_end": None,
            "n_rows": 0,
        }
    fit_idx = np.arange(train_start, end_idx + 1, dtype=int)
    info = {
        "mode": mode,
    }
    fit_idx = fit_idx[before_forecast_mask[fit_idx]]
    fit_idx, info = enforce_train_before_test(
        fit_idx, forecast_indices,
        window_cfg=time_series_cfg,
        context_datetimes=context_datetimes,
        split_info=info,
        warning_label="Forecast fit window",
    )
    info["resolved_start"] = None if fit_idx.size == 0 else int(fit_idx[0])
    info["resolved_end"] = None if fit_idx.size == 0 else int(fit_idx[-1])
    info["n_rows"] = int(fit_idx.size)
    return fit_idx, info


def _populate_requested_forecast(best_trial, csv_meta, forecast_window, args,
                                 deep_preset_cfgs, custom_cfg,
                                 metric_profile=None, training_weight_cfg=None):
    if forecast_window is None:
        return
    fit_idx, fit_info = _resolve_forecast_fit_indices(
        best_trial, len(csv_meta["X"]), forecast_window["indices"], args.forecast_trainset,
        time_series_cfg=_resolve_time_series_cfg(args),
        context_datetimes=csv_meta.get("context_datetimes"),
    )
    if fit_idx is None or len(fit_idx) == 0:
        raise ValueError("Forecast trainset vuoto: impossibile generare il forecast richiesto")
    X_fit = np.asarray(csv_meta["X"][fit_idx], dtype=float)
    y_fit = np.asarray(csv_meta["y"][fit_idx], dtype=float)
    X_fc = np.asarray(csv_meta["X"][forecast_window["indices"]], dtype=float)
    y_fc = np.asarray(csv_meta["y"][forecast_window["indices"]], dtype=float)

    feature_cols = best_trial.get("extra", {}).get("feature_cols")
    if feature_cols is not None:
        name_to_idx = {name: i for i, name in enumerate(csv_meta["feature_cols"])}
        selected_indices = [name_to_idx[name] for name in feature_cols if name in name_to_idx]
        X_fit = X_fit[:, selected_indices]
        X_fc = X_fc[:, selected_indices]

    y_pred_fc = predict_with_result(
        best_trial, X_fit, y_fit, X_fc, seed=best_trial["seed"],
        deep_preset_cfgs=deep_preset_cfgs, custom_deep_cfg=custom_cfg,
        metric_profile=metric_profile, training_weight_cfg=training_weight_cfg,
    )
    best_trial.setdefault("_artifacts", {})
    best_trial["_artifacts"]["forecast_indices"] = np.asarray(forecast_window["indices"], dtype=int)
    best_trial["_artifacts"]["y_true_forecast"] = np.asarray(y_fc, dtype=float)
    best_trial["_artifacts"]["y_pred_forecast"] = np.asarray(y_pred_fc, dtype=float)
    best_trial.setdefault("extra", {})
    info = dict(forecast_window["info"])
    info["trainset_mode"] = args.forecast_trainset
    info["fit_start"] = fit_info.get("resolved_start")
    info["fit_end"] = fit_info.get("resolved_end")
    info["fit_rows"] = fit_info.get("n_rows")
    best_trial["extra"]["forecast_info"] = info


def _format_overall_detail(row):
    if row.get("score_kind") == "event":
        return (f"{row['kpi_mean']:.4f} (F1={row.get('event_f1_mean', 0.0):.3f} "
                f"P={row.get('event_precision_mean', 0.0):.3f} "
                f"R={row.get('event_recall_mean', 0.0):.3f} "
                f"Bal={row.get('event_bal_acc_mean', 0.0):.3f})")
    return (f"{row['kpi_mean']:.4f} (fit={row.get('score_fit_mean', 0.0):.3f} "
            f"r2={row.get('score_r2_mean', 0.0):.3f})")


def _display_bank(bank):
    if bank == "__none__":
        return "(end-to-end)"
    if bank == "__lcs__":
        return "(lcs)"
    if bank == "__hybrid__":
        return "(hybrid)"
    if bank == "__kan__":
        return "(kan)"
    if bank == "__kan_hybrid__":
        return "(kan-hybrid)"
    return bank


def _print_metric_legend(metric_profile):
    print("Direzione metriche: Overall ↑ meglio, MSE ↓ meglio, MAE ↓ meglio, R2 ↑ meglio")
    if metric_profile["kind"] == "event":
        print("Ranking: ordinato per Overall ↑ basato solo sulle metriche di test")
        if metric_profile.get("score_mode") == "isolation":
            print("Componenti Overall: F1 ↑, Balanced Accuracy ↑, Precision ↑, Specificity ↑, fit positivi ↑")
        else:
            print("Componenti Overall: F1 ↑, Balanced Accuracy ↑, Recall ↑, fit sui positivi ↑")
    else:
        print("Ranking: ordinato per Overall ↑ basato solo sulle metriche di test")
        print("Componenti Overall: fit da MSE test normalizzato ↑, R2 test ↑")


def _describe_metric_choice(y, metric_profile, requested_mode):
    y = list(y)
    n = len(y)
    positives = sum(1 for v in y if v > 0)
    zero_frac = 0.0 if n == 0 else sum(1 for v in y if abs(v) < 1e-12) / n
    if metric_profile["kind"] == "event":
        reason = (f"target sparso/zero-inflated: positivi={positives}/{n}, "
                  f"zero_frac={zero_frac:.3f}")
    else:
        reason = f"target continuo: positivi={positives}/{n}, zero_frac={zero_frac:.3f}"
    return (f"kind={metric_profile['kind']} threshold={metric_profile['threshold']} "
            f"pred_threshold={metric_profile.get('prediction_threshold')} "
            f"score_mode={metric_profile.get('score_mode')} "
            f"requested={requested_mode} reason={reason}")


def _resolve_train_config(args):
    tasks = _parse_csv_arg(getattr(args, "task", ""))
    if getattr(args, "all_tasks", False) and not (len(tasks) == 1 and is_csv_task(tasks[0])):
        tasks = list(TASKS.keys())

    banks = _parse_csv_arg(getattr(args, "banks", ""))
    if getattr(args, "no_banks", False):
        banks = []
    elif getattr(args, "all_banks", False) or not banks:
        banks = list(BANKS.keys())

    readouts = _parse_csv_arg(getattr(args, "readouts", ""))
    if getattr(args, "all_readouts", False):
        readouts = [
            name for name in READOUTS.keys()
            if (not str(name).startswith("kan_")
                or getattr(args, "enable_kan", False)
                or getattr(args, "enable_kan_in_max", False))
        ]
    elif not readouts:
        readouts = ["ridge"]

    deep_presets = _parse_csv_arg(getattr(args, "deep_presets", ""))
    if getattr(args, "all_deep_presets", False):
        deep_presets = list(DEEP_PRESETS.keys())

    lcs_presets = _parse_csv_arg(getattr(args, "lcs_presets", ""))
    if getattr(args, "all_lcs_presets", False):
        lcs_presets = list(LCS_PRESETS.keys())
    if getattr(args, "hybrid_lcs", False) and not lcs_presets and not getattr(args, "lcs_custom", False):
        lcs_presets = ["default"]

    kan_requested = (
        getattr(args, "enable_kan", False)
        or getattr(args, "hybrid_kan", False)
        or getattr(args, "enable_kan_in_max", False)
        or getattr(args, "all_kan_presets", False)
    )
    kan_presets = _parse_csv_arg(getattr(args, "kan_presets", "")) if kan_requested else []
    if getattr(args, "all_kan_presets", False):
        kan_presets = list(KAN_PRESETS.keys())
    if getattr(args, "enable_kan", False) and not kan_presets:
        kan_presets = ["tiny"]
    if getattr(args, "hybrid_kan", False) and not kan_presets:
        kan_presets = ["tiny"]
    return tasks, banks, readouts, deep_presets, lcs_presets, kan_presets


def _resolve_hybrid_specs(args, banks, readouts, deep_presets, enabled_attr="hybrid_lcs"):
    if not getattr(args, enabled_attr, False):
        return []
    modes = _parse_csv_arg(getattr(args, "hybrid_modes", "and,weighted"))
    alphas = _parse_float_csv(getattr(args, "hybrid_alphas", "0.5")) or [0.5]
    threshold = float(getattr(args, "hybrid_threshold", 0.5) or 0.5)

    partners = []
    manual = _parse_csv_arg(getattr(args, "hybrid_partners", ""))
    if manual:
        for item in manual:
            if item.startswith("deep:"):
                partners.append({"kind": "deep", "preset": item.split(":", 1)[1]})
                continue
            if ":" in item:
                bank, readout = item.split(":", 1)
            else:
                bank, readout = item, "ridge"
            partners.append({"kind": "bank", "bank": bank, "readout": readout})
    else:
        for bank in banks:
            for readout in readouts:
                partners.append({"kind": "bank", "bank": bank, "readout": readout})
        for preset in deep_presets:
            partners.append({"kind": "deep", "preset": preset})
        if getattr(args, "deep_custom", False):
            partners.append({"kind": "deep", "preset": "custom"})

    specs = []
    for partner in partners:
        for mode in modes:
            mode = mode.strip().lower()
            if mode == "weighted":
                for alpha in alphas:
                    specs.append({
                        "partner": partner,
                        "mode": "weighted",
                        "alpha": float(alpha),
                        "hybrid_threshold": threshold,
                    })
            elif mode in ("and", "or"):
                specs.append({
                    "partner": partner,
                    "mode": mode,
                    "alpha": 0.5,
                    "hybrid_threshold": threshold,
                })
    return specs


def _format_duration(seconds):
    seconds = max(0.0, float(seconds))
    if seconds < 10:
        return f"{seconds:.1f}s"
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _aggregate_by_bank(results):
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        groups[r["bank"]].append(r)

    def _weights(runs):
        return np.asarray([
            float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
            for r in runs
        ], dtype=float)

    def _weighted_mean(values, weights):
        values = np.asarray(values, dtype=float)
        if values.size == 0:
            return 0.0
        if weights.size != values.size or np.sum(weights) <= 0:
            return float(np.mean(values))
        return float(np.average(values, weights=weights))

    agg = []
    for bank, runs in groups.items():
        weights = _weights(runs)
        agg.append({
            "bank": bank,
            "mse_test_mean": _weighted_mean([r["mse_test"] for r in runs], weights),
            "kpi_mean": _weighted_mean([r["overall_kpi"] for r in runs], weights),
            "inference_us": _weighted_mean([r["inference_time_us"] for r in runs], weights),
            "train_s": _weighted_mean([r["train_time_s"] for r in runs], weights),
            "n_params": int(_weighted_mean([r["n_effective_params"] for r in runs], weights)),
            "n_runs": len(runs),
            "n_tasks": len({r["task"] for r in runs}),
            "readouts": len({r["readout"] for r in runs}),
            "weight_sum": float(np.sum(weights)),
            "weighted_ranking": bool(np.any(np.abs(weights - weights[0]) > 1e-12)),
            "score_kind": runs[0].get("extra", {}).get("score_kind", "regression"),
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
    agg.sort(key=lambda r: -r["kpi_mean"])
    return agg


def _aggregate_by_bank_readout(results):
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        groups[(r["bank"], r["readout"])].append(r)

    def _weights(runs):
        return np.asarray([
            float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
            for r in runs
        ], dtype=float)

    def _weighted_mean(values, weights):
        values = np.asarray(values, dtype=float)
        if values.size == 0:
            return 0.0
        if weights.size != values.size or np.sum(weights) <= 0:
            return float(np.mean(values))
        return float(np.average(values, weights=weights))

    agg = []
    for (bank, readout), runs in groups.items():
        weights = _weights(runs)
        agg.append({
            "bank": bank,
            "readout": readout,
            "mse_test_mean": _weighted_mean([r["mse_test"] for r in runs], weights),
            "kpi_mean": _weighted_mean([r["overall_kpi"] for r in runs], weights),
            "n_runs": len(runs),
            "n_tasks": len({r["task"] for r in runs}),
            "weight_sum": float(np.sum(weights)),
            "weighted_ranking": bool(np.any(np.abs(weights - weights[0]) > 1e-12)),
            "score_kind": runs[0].get("extra", {}).get("score_kind", "regression"),
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
        score_components = {}
        score_weights = {}
        for r in runs:
            for key, value in r.get("extra", {}).get("score_components", {}).items():
                score_components.setdefault(key, []).append(value)
                score_weights.setdefault(key, []).append(
                    float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
                )
        for key, values in score_components.items():
            agg[-1][f"score_{key}_mean"] = _weighted_mean(
                values, np.asarray(score_weights.get(key, []), dtype=float)
            )
    agg.sort(key=lambda r: -r["kpi_mean"])
    return agg


def _print_task_eta(task_idx, total_tasks, started_at):
    elapsed = time.perf_counter() - started_at
    avg_task_s = elapsed / max(task_idx, 1)
    remaining_tasks = max(total_tasks - task_idx, 0)
    eta_s = avg_task_s * remaining_tasks
    print(f"Tempo: trascorso {_format_duration(elapsed)}  "
          f"media/task {_format_duration(avg_task_s)}  "
          f"stimato residuo {_format_duration(eta_s)}")


def _select_best_trial_for_winner(results, winner):
    matching = [
        r for r in results
        if r["bank"] == winner["bank"] and r["readout"] == winner["readout"]
    ]
    if not matching:
        return None
    def key(r):
        weight = float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
        is_recent = 1 if r.get("extra", {}).get("recent_validation_info") else 0
        return (float(r["overall_kpi"]) * weight, is_recent, float(r["overall_kpi"]), -r["mse_test"])
    return max(matching, key=key)


def _select_recent_validation_trial(results, bank, readout):
    matching = [
        r for r in results
        if r["bank"] == bank
        and r["readout"] == readout
        and r.get("extra", {}).get("recent_validation_info")
    ]
    if not matching:
        return None
    return max(matching, key=lambda r: (r["overall_kpi"], -r["mse_test"]))


def _collect_window_trials_for_combined(results, bank, readout, seed):
    """Tutti i trial dello stesso modello su finestre diverse (main/backtest/recent_val).

    Ritorna lista di dict ordinati cronologicamente (per primo test_index), ognuno con:
      {'trial': ..., 'role': 'main'|'backtest'|'recent_val', 'window_no': int|None,
       'start_idx': int}
    Deduplica trial con identici test_indices preferendo: main > recent_val > backtest.
    """
    candidates = []
    for r in results:
        if r["bank"] != bank or r["readout"] != readout or r.get("seed") != seed:
            continue
        ti = r.get("_artifacts", {}).get("test_indices")
        if ti is None or len(ti) == 0:
            continue
        try:
            start = int(ti[0])
        except (TypeError, ValueError):
            continue
        extra = r.get("extra", {}) or {}
        if extra.get("recent_validation_info"):
            role = "recent_val"
            wno = None
        elif extra.get("backtest_info"):
            role = "backtest"
            wno = int(extra["backtest_info"].get("window_no") or 0)
        else:
            role = "main"
            wno = None
        candidates.append({"trial": r, "role": role, "window_no": wno,
                           "start_idx": start, "end_idx": int(ti[-1])})

    role_priority = {"main": 0, "recent_val": 1, "backtest": 2}
    candidates.sort(key=lambda c: (c["start_idx"], role_priority.get(c["role"], 9)))
    deduped = []
    seen_spans = set()
    for c in candidates:
        span = (c["start_idx"], c["end_idx"])
        if span in seen_spans:
            continue
        seen_spans.add(span)
        deduped.append(c)
    return deduped


def _select_best_trials_for_agg(results, agg_rows):
    selected = []
    for row in agg_rows:
        best_trial = _select_best_trial_for_winner(results, row)
        if best_trial is not None:
            selected.append((row, best_trial))
    return selected


def _classify_keep_set(best_trials, args):
    """Decide quali (winner_row, best_trial) ottengono l'export per-trial completo.

    Ritorna (keep_set_indices, best_indices, worst_indices). LCS/hybrid sono
    SEMPRE in keep_set come riferimento, ma non contano nei bordi best/worst.
    Se keep_best == keep_worst == 0 -> keep_set = tutto (legacy, no-op).
    """
    n = len(best_trials)
    if n == 0:
        return set(), set(), set()
    keep_best = max(0, int(getattr(args, "keep_best", 0) or 0))
    keep_worst = max(0, int(getattr(args, "keep_worst", 0) or 0))
    if keep_best == 0 and keep_worst == 0:
        return set(range(n)), set(), set()

    # ordina per kpi_mean desc (best in alto)
    order = sorted(range(n),
                   key=lambda i: -float(best_trials[i][0].get("kpi_mean", 0.0)))
    n_best = min(keep_best, n)
    n_worst = min(keep_worst, max(0, n - n_best))
    best_indices = set(order[:n_best])
    worst_indices = set(order[n - n_worst:]) if n_worst > 0 else set()
    keep_set = set(best_indices) | set(worst_indices)
    # whitelist: interpretable/hybrid sempre dentro
    for i, (_, trial) in enumerate(best_trials):
        if str(trial.get("bank", "")) in ("__lcs__", "__hybrid__", "__kan__", "__kan_hybrid__"):
            keep_set.add(i)
    return keep_set, best_indices, worst_indices


def _select_best_trials_per_bank_from_agg(results, agg_rows):
    selected = []
    seen = set()
    for row in agg_rows:
        bank = row.get("bank")
        if bank in seen:
            continue
        best_trial = _select_best_trial_for_winner(results, row)
        if best_trial is not None:
            selected.append((row, best_trial))
            seen.add(bank)
    return selected


def _select_best_lcs_rule_trial(results):
    candidates = [
        r for r in results
        if r.get("bank") in ("__lcs__", "__hybrid__")
        and r.get("_artifacts", {}).get("best_rules")
    ]
    if not candidates:
        return None
    def key(r):
        weight = float(r.get("extra", {}).get("ranking_weight", 1.0) or 1.0)
        is_recent = 1 if r.get("extra", {}).get("recent_validation_info") else 0
        return (float(r.get("overall_kpi", 0.0)) * weight, is_recent, float(r.get("overall_kpi", 0.0)))
    return max(candidates, key=key)


def _export_summary_charts(run_dir, task_name, results, agg, csv_meta):
    charts_dir = os.path.join(run_dir, "summary_charts")
    os.makedirs(charts_dir, exist_ok=True)
    task_slug = safe_slug(os.path.splitext(os.path.basename(task_name))[0])
    ranking_path = os.path.join(charts_dir, f"{task_slug}__ranking_all_variants.png")
    technique_path = os.path.join(charts_dir, f"{task_slug}__ranking_by_technique.png")
    write_ranking_bar_png(
        ranking_path,
        agg,
        title=f"Ranking finale - {os.path.basename(task_name)}",
    )
    write_technique_summary_png(
        technique_path,
        agg,
        title=f"Riepilogo per tecnica - {os.path.basename(task_name)}",
    )
    exported = {
        "ranking_all_variants_png": ranking_path,
        "ranking_by_technique_png": technique_path,
    }
    rule_trial = _select_best_lcs_rule_trial(results)
    if rule_trial is not None:
        rules_path = os.path.join(charts_dir, f"{task_slug}__lcs_rules_map.png")
        write_lcs_rules_map_png(
            rules_path,
            rule_trial,
            csv_meta,
            title=f"Regole LCS usate - {os.path.basename(task_name)}",
        )
        exported["lcs_rules_map_png"] = rules_path
    return exported


def _final_eval_enabled(args):
    return not bool(getattr(args, "no_final_evaluation", False))


def _rank_weight_lookup(agg_rows, rank_power):
    n = len(agg_rows or [])
    out = {}
    if n <= 0:
        return out
    power = max(0.0, float(rank_power or 0.0))
    for rank, row in enumerate(agg_rows, start=1):
        weight = float((n - rank + 1) ** power)
        out[(row.get("bank"), row.get("readout"))] = {
            "rank": int(rank),
            "rank_weight": weight,
            "rank_score": float(row.get("kpi_mean", row.get("overall", 0.0)) or 0.0),
        }
    return out


def _final_eval_is_event(metric_profile):
    return str((metric_profile or {}).get("kind", "")).lower() == "event"


def _final_eval_actual_value(raw_value, metric_profile):
    value = float(raw_value)
    if _final_eval_is_event(metric_profile):
        threshold = (metric_profile or {}).get("threshold")
        if threshold is None:
            return value
        return 1.0 if value >= float(threshold) else 0.0
    return value


def _final_eval_prediction_value(raw_value, metric_profile):
    value = float(raw_value)
    if not math.isfinite(value):
        return None
    if _final_eval_is_event(metric_profile):
        pred_threshold = (metric_profile or {}).get("prediction_threshold")
        if pred_threshold is None or float(pred_threshold) <= 0:
            target_threshold = (metric_profile or {}).get("threshold", 0.5)
            return 1.0 if value >= float(target_threshold) else 0.0
        return max(0.0, min(1.0, value / float(pred_threshold)))
    return value


def _final_eval_context(csv_meta, idx):
    values = csv_meta.get("context_values")
    if values is None:
        return ""
    return values[int(idx)]


def _final_eval_row_index(csv_meta, idx):
    rows = csv_meta.get("row_indices")
    if rows is None:
        return int(idx)
    return int(rows[int(idx)])


def _select_inversion_candidates(results, args):
    """Identifica i (bank, readout, seed) i cui *test result* sono nel bottom
    --invert-twin-fraction per shape_overall AND con std(y_pred_test) >
    --invert-twin-min-std. Esclude bank LCS/hybrid (riferimento puro) e i twin
    gia' invertiti. Ritorna un set di chiavi (bank, readout, seed)."""
    if not bool(getattr(args, "invert_twin_enabled", True)):
        return set()
    fraction = getattr(args, "invert_twin_fraction", None)
    if fraction is None:
        fraction = float(getattr(args, "final_eval_worst_fraction", 0.10) or 0.0)
    fraction = max(0.0, min(1.0, float(fraction)))
    if fraction <= 0:
        return set()
    min_std = max(0.0, float(getattr(args, "invert_twin_min_std", 1e-6) or 0.0))

    candidates = []
    for r in results or []:
        bank = str(r.get("bank", ""))
        if bank.endswith("__INV"):
            continue
        extra = r.get("extra", {}) or {}
        if extra.get("backtest_info") or extra.get("recent_validation_info"):
            continue
        artifacts = r.get("_artifacts", {}) or {}
        y_pred = artifacts.get("y_pred_test")
        if y_pred is None or len(y_pred) == 0:
            continue
        try:
            std_val = float(np.std(np.asarray(y_pred, dtype=float)))
        except Exception:
            continue
        if std_val < min_std:
            continue
        candidates.append({
            "key": (r.get("bank"), r.get("readout"), r.get("seed")),
            "shape_overall": float(extra.get("shape_overall", 0.0)),
        })

    if not candidates:
        return set()
    candidates.sort(key=lambda c: c["shape_overall"])
    n = len(candidates)
    n_pick = max(1, int(math.ceil(n * fraction)))
    return {c["key"] for c in candidates[:n_pick]}


def _build_inverted_twins(results, metric_profile, kpi_weights, csv_meta, args):
    """Per ogni (bank, readout, seed) identificato dal selettore, clona TUTTI i
    suoi result (test/backtest/recent_val) come twin invertiti. Ritorna la
    lista dei nuovi twin."""
    candidate_keys = _select_inversion_candidates(results, args)
    if not candidate_keys:
        return []
    y_ref = np.asarray(csv_meta.get("y", []), dtype=float) if csv_meta else None
    if y_ref is not None and y_ref.size > 0:
        mse_ref = float(np.var(y_ref)) + 1e-9
    else:
        mse_ref = 1.0
    twins = []
    for r in results:
        key = (r.get("bank"), r.get("readout"), r.get("seed"))
        if key not in candidate_keys:
            continue
        if (r.get("extra", {}) or {}).get("immediate_inverted_twin_generated"):
            continue
        twin = make_inverted_twin_result(
            r, metric_profile, kpi_weights=kpi_weights, mse_ref=mse_ref
        )
        if twin is not None:
            twins.append(twin)
    return twins


def _classify_trials_for_shape_filter(results, metric_profile, args):
    """Classify each trial by validation shape. Returns None when the filter is
    disabled (legacy behaviour). When enabled returns a dict keyed on id(result):
        {"action": "include"|"invert"|"exclude", "reason": str}

    Rules (default ON):
      - 0 picchi predetti in validation -> exclude (variazione assente, plot frastagliato senza shape)
      - i restanti vengono ordinati per shape_overall desc:
            top    --final-eval-best-fraction   -> include  (peaks/depressions vicini al reale)
            bottom --final-eval-worst-fraction  -> invert   (peaks lontani: invertendo combaciano)
            middle                              -> exclude  (mediocri: non aggiungono segnale)
    """
    if bool(getattr(args, "no_final_eval_shape_filter", False)):
        return None

    is_event = _final_eval_is_event(metric_profile)
    raw_threshold = (metric_profile or {}).get("threshold") if is_event else None
    threshold = float(raw_threshold) if raw_threshold is not None else None

    decisions = {}
    candidates = []
    for result in results or []:
        artifacts = result.get("_artifacts", {}) or {}
        indices = artifacts.get("test_indices")
        y_pred = artifacts.get("y_pred_test")
        if indices is None or y_pred is None or len(indices) == 0:
            continue
        y_pred_arr = np.asarray(y_pred, dtype=float).reshape(-1)
        pred_peaks = detect_topological_peaks(y_pred_arr, threshold=threshold)
        rid = id(result)
        if len(pred_peaks) == 0:
            decisions[rid] = {"action": "exclude", "reason": "no_predicted_peaks"}
            continue
        extra = result.get("extra", {}) or {}
        candidates.append({
            "id": rid,
            "shape_overall": float(extra.get("shape_overall", 0.0)),
            "peak_score": float(extra.get("peak_score", 0.0)),
            "n_peaks": len(pred_peaks),
        })

    if not candidates:
        return decisions

    candidates.sort(key=lambda c: -c["shape_overall"])
    n = len(candidates)
    best_fraction = max(0.0, min(1.0, float(getattr(args, "final_eval_best_fraction", 0.25) or 0.0)))
    worst_fraction = max(0.0, min(1.0, float(getattr(args, "final_eval_worst_fraction", 0.10) or 0.0)))
    n_best = int(math.ceil(n * best_fraction)) if best_fraction > 0 else 0
    n_worst = int(math.ceil(n * worst_fraction)) if worst_fraction > 0 else 0
    if n_best > 0:
        n_best = max(1, n_best)
    if n_worst > 0:
        n_worst = max(1, n_worst)
    if n_best + n_worst > n:
        n_worst = max(0, n - n_best)

    best_ids = {c["id"] for c in candidates[:n_best]} if n_best > 0 else set()
    worst_ids = {c["id"] for c in candidates[n - n_worst:]} if n_worst > 0 else set()
    for c in candidates:
        if c["id"] in best_ids:
            decisions[c["id"]] = {"action": "include", "reason": "top_shape"}
        elif c["id"] in worst_ids:
            decisions[c["id"]] = {"action": "invert", "reason": "bottom_shape_invertible"}
        else:
            decisions[c["id"]] = {"action": "exclude", "reason": "mediocre"}
    return decisions


def _iter_final_eval_segments(results, forecast_trials):
    for result in results or []:
        artifacts = result.get("_artifacts", {}) or {}
        indices = artifacts.get("test_indices")
        y_pred = artifacts.get("y_pred_test")
        if indices is not None and y_pred is not None and len(indices) > 0:
            yield "validation", result, indices, y_pred
    seen_forecast = set()
    for result in forecast_trials or []:
        artifacts = result.get("_artifacts", {}) or {}
        indices = artifacts.get("forecast_indices")
        y_pred = artifacts.get("y_pred_forecast")
        if indices is None or y_pred is None or len(indices) == 0:
            continue
        key = (result.get("bank"), result.get("readout"), result.get("seed"), tuple(map(int, indices)))
        if key in seen_forecast:
            continue
        seen_forecast.add(key)
        yield "forecast", result, indices, y_pred


def _export_final_evaluation(run_dir, task_name, results, agg, csv_meta,
                             forecast_trials, metric_profile, args):
    if not _final_eval_enabled(args):
        return None
    rank_lookup = _rank_weight_lookup(agg, getattr(args, "final_eval_rank_power", 1.0))
    if not rank_lookup:
        return None

    task_slug = safe_slug(os.path.splitext(os.path.basename(task_name))[0])
    task_dir = os.path.join(run_dir, task_slug)
    os.makedirs(task_dir, exist_ok=True)
    stem = f"{task_slug}__final_evaluation"
    json_path = os.path.join(task_dir, stem + ".json")
    location_display = is_location_analog_display(csv_meta)
    location_note = location_display_subtitle(csv_meta)

    y_all = np.asarray(csv_meta.get("y", []), dtype=float).reshape(-1)
    stores = {"validation": {}, "forecast": {}}
    low_threshold = float(getattr(args, "final_eval_low_threshold", 1e-9) or 0.0)
    negative_enabled = not bool(getattr(args, "no_final_eval_negative_inertia", False))
    negative_weight = max(1.0, float(getattr(args, "final_eval_negative_weight", 3.0) or 1.0))

    classifications = _classify_trials_for_shape_filter(results, metric_profile, args)
    shape_filter_enabled = classifications is not None
    shape_power = max(0.0, float(getattr(args, "final_eval_shape_power", 0.0) or 0.0))

    source_trials = 0
    reverse_trials = 0
    excluded_trials = 0
    excluded_reasons = {}
    for phase, result, indices, y_pred in _iter_final_eval_segments(results, forecast_trials):
        key = (result.get("bank"), result.get("readout"))
        rank_info = rank_lookup.get(key)
        if rank_info is None:
            continue

        decision_action = None
        decision_reason = None
        if shape_filter_enabled:
            decision = classifications.get(id(result))
            if decision is None:
                excluded_trials += 1
                excluded_reasons["no_validation"] = excluded_reasons.get("no_validation", 0) + 1
                continue
            decision_action = decision["action"]
            decision_reason = decision["reason"]
            if decision_action == "exclude":
                excluded_trials += 1
                excluded_reasons[decision_reason] = excluded_reasons.get(decision_reason, 0) + 1
                continue

        indices = list(indices)
        preds = list(y_pred)
        n = min(len(indices), len(preds))
        if n <= 0:
            continue
        pred_values = []
        for pred in preds[:n]:
            value = _final_eval_prediction_value(pred, metric_profile)
            if value is not None:
                pred_values.append(value)
        if not pred_values:
            continue
        source_trials += 1
        if shape_filter_enabled:
            reverse_mode = (decision_action == "invert")
        else:
            total_estimation = float(sum(max(0.0, v) for v in pred_values))
            reverse_mode = bool(negative_enabled and total_estimation <= low_threshold)
        if reverse_mode:
            reverse_trials += 1
        extra = result.get("extra", {}) or {}
        window_weight = float(extra.get("ranking_weight", 1.0) or 1.0)
        base_weight = float(rank_info["rank_weight"]) * max(0.0, window_weight)
        if reverse_mode:
            base_weight *= negative_weight
        elif shape_filter_enabled and shape_power > 0 and decision_action == "include":
            shape_overall = max(0.0, float(extra.get("shape_overall", 0.0)))
            base_weight *= shape_overall ** shape_power
        if base_weight <= 0:
            continue

        phase_store = stores.setdefault(phase, {})
        for idx, pred in zip(indices[:n], preds[:n]):
            idx = int(idx)
            if idx < 0 or idx >= len(y_all):
                continue
            pred_value = _final_eval_prediction_value(pred, metric_profile)
            if pred_value is None:
                continue
            if reverse_mode:
                pred_value = 1.0 - pred_value if _final_eval_is_event(metric_profile) else -pred_value
            actual = _final_eval_actual_value(y_all[idx], metric_profile)
            item = phase_store.setdefault(idx, {
                "index": idx,
                "context": _final_eval_context(csv_meta, idx),
                "row_index": _final_eval_row_index(csv_meta, idx),
                "actual_raw": float(y_all[idx]),
                "actual": float(actual),
                "weighted_pred_sum": 0.0,
                "total_weight": 0.0,
                "normal_weight": 0.0,
                "reverse_weight": 0.0,
                "contributors": 0,
                "reverse_contributors": 0,
                "phase": phase,
                "best_rank": int(rank_info["rank"]),
            })
            item["weighted_pred_sum"] += float(pred_value) * base_weight
            item["total_weight"] += base_weight
            if reverse_mode:
                item["reverse_weight"] += base_weight
                item["reverse_contributors"] += 1
            else:
                item["normal_weight"] += base_weight
            item["contributors"] += 1
            item["best_rank"] = min(item["best_rank"], int(rank_info["rank"]))

    fieldnames = [
        "context", "row_index", "phase", "actual_raw", "actual", "predicted",
        "total_weight", "normal_weight", "reverse_weight", "contributors",
        "reverse_contributors", "best_rank", "source_index",
    ]

    def build_rows(store):
        out = []
        for idx in sorted(store):
            item = store[idx]
            total_weight = item["total_weight"]
            predicted = item["weighted_pred_sum"] / total_weight if total_weight > 0 else 0.0
            actual_value = float(item["actual"])
            predicted_value = float(predicted)
            actual_raw_value = float(item["actual_raw"])
            if location_display:
                actual_decoded = decode_location_series(
                    csv_meta, [item["actual_raw"]], actual=True
                )[0]
                predicted_decoded = decode_location_series(
                    csv_meta, [predicted], actual=False
                )[0]
                actual_value = actual_decoded
                actual_raw_value = actual_decoded
                predicted_value = predicted_decoded
            out.append({
                "context": item["context"],
                "row_index": item["row_index"],
                "phase": item["phase"],
                "actual_raw": actual_raw_value,
                "actual": actual_value,
                "predicted": predicted_value,
                "total_weight": float(total_weight),
                "normal_weight": float(item["normal_weight"]),
                "reverse_weight": float(item["reverse_weight"]),
                "contributors": int(item["contributors"]),
                "reverse_contributors": int(item["reverse_contributors"]),
                "best_rank": int(item["best_rank"]),
                "source_index": int(item["index"]),
            })
        return out

    def write_phase_outputs(phase, rows):
        csv_path = os.path.join(task_dir, f"{stem}__{phase}.csv")
        png_path = os.path.join(task_dir, f"{stem}__{phase}.png")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        title = f"FINAL EVALUATION {phase.upper()} | rank-weighted ensemble  rows={len(rows)}"
        if shape_filter_enabled:
            best_frac = float(getattr(args, "final_eval_best_fraction", 0.25) or 0.0)
            worst_frac = float(getattr(args, "final_eval_worst_fraction", 0.10) or 0.0)
            subtitle = (
                f"rank_power={getattr(args, 'final_eval_rank_power', 1.0)} "
                f"shape_filter=on best={best_frac:g} worst={worst_frac:g} "
                f"shape_power={shape_power:g} reverse_weight_x={negative_weight:g} "
                f"included={source_trials - reverse_trials} inverted={reverse_trials} "
                f"excluded={excluded_trials} "
                "point dates = period start"
            )
        else:
            subtitle = (
                f"rank_power={getattr(args, 'final_eval_rank_power', 1.0)} "
                f"shape_filter=off negative_inertia={'on' if negative_enabled else 'off'} "
                f"low_total<={low_threshold:g} reverse_weight_x={negative_weight:g} "
                "point dates = period start"
            )
        if location_note:
            subtitle = f"{subtitle} | {location_note}"
        write_series_png(
            png_path,
            [r["actual"] for r in rows],
            [r["predicted"] for r in rows],
            context_values=csv_meta.get("context_values"),
            indices=[r["source_index"] for r in rows],
            title=title,
            subtitle=subtitle,
        )
        return {"csv": csv_path, "png": png_path, "rows": len(rows)}

    outputs = {}
    total_rows = 0
    for phase in ("validation", "forecast"):
        rows = build_rows(stores.get(phase, {}))
        if not rows:
            continue
        outputs[phase] = write_phase_outputs(phase, rows)
        total_rows += len(rows)

    payload = {
        "task": task_name,
        "dataset_path": csv_meta.get("path"),
        "target_col": csv_meta.get("target_col"),
        "score_kind": (metric_profile or {}).get("kind"),
        "metric_profile": json_safe(metric_profile),
        "rank_power": getattr(args, "final_eval_rank_power", 1.0),
        "negative_inertia": {
            "enabled": negative_enabled,
            "low_threshold": low_threshold,
            "negative_weight": negative_weight,
            "reverse_trials": reverse_trials,
        },
        "shape_filter": {
            "enabled": shape_filter_enabled,
            "best_fraction": float(getattr(args, "final_eval_best_fraction", 0.25) or 0.0),
            "worst_fraction": float(getattr(args, "final_eval_worst_fraction", 0.10) or 0.0),
            "shape_power": shape_power,
            "excluded_trials": excluded_trials,
            "excluded_reasons": excluded_reasons,
        },
        "source_trials": source_trials,
        "rows": total_rows,
        "outputs": outputs,
    }
    write_json(json_path, payload)
    outputs["json"] = json_path
    outputs["rows"] = total_rows
    return outputs


def _build_run_signature_payload(args, dataset_path=None):
    rerun_cli = shlex.join([sys.executable] + sys.argv)
    return {
        "timestamp": timestamp_slug(),
        "command": getattr(args, "cmd", ""),
        "argv": sys.argv,
        "rerun_cli": rerun_cli,
        "cwd": os.getcwd(),
        "dataset_path": dataset_path,
        "args": json_safe(vars(args)),
    }


def _trial_model_config(result):
    extra = result.get("extra", {}) or {}
    keys = (
        "preprocessing",
        "deep_cfg",
        "lcs_cfg",
        "hybrid_cfg",
        "kan_cfg",
        "kan_hybrid_cfg",
        "validation_info",
        "retrain_info",
        "lcs_best_validation",
        "lcs_best_epoch",
        "training_sample_weighting",
    )
    payload = {
        "bank": result.get("bank"),
        "readout": result.get("readout"),
        "seed": result.get("seed"),
        "n_effective_params": result.get("n_effective_params"),
    }
    for key in keys:
        if key in extra and extra.get(key) is not None:
            payload[key] = extra.get(key)
    return json_safe(payload)


def _build_best_trial_signature(args, task_name, result, winner, csv_meta):
    rerun_cli = shlex.join([sys.executable] + sys.argv)
    extra = result.get("extra", {})
    return {
        "task": task_name,
        "dataset_path": csv_meta.get("path"),
        "target_col": csv_meta.get("target_col"),
        "context_col": csv_meta.get("context_col"),
        "bank": result.get("bank"),
        "readout": result.get("readout"),
        "seed": result.get("seed"),
        "feature_cols": extra.get("feature_cols"),
        "skip_cols": extra.get("skip_cols"),
        "winner_summary": {
            "overall": winner.get("kpi_mean"),
            "mse_mean": winner.get("mse_test_mean"),
            "mae_mean": winner.get("mae_test_mean"),
            "r2_mean": winner.get("r2_mean"),
            "score_kind": winner.get("score_kind"),
        },
        "trial_metrics": {
            "overall": result.get("overall_kpi"),
            "mse_test": result.get("mse_test"),
            "mae_test": result.get("mae_test"),
            "r2": result.get("r2"),
            "event_precision": extra.get("event_precision"),
            "event_recall": extra.get("event_recall"),
            "event_f1": extra.get("event_f1"),
            "event_bal_acc": extra.get("event_bal_acc"),
            "event_specificity": extra.get("event_specificity"),
            "positive_mae": extra.get("positive_mae"),
        },
        "model_config": _trial_model_config(result),
        "split_info": extra.get("split_info"),
        "forecast_info": extra.get("forecast_info"),
        "score_components": extra.get("score_components"),
        "params": json_safe(vars(args)),
        "argv": sys.argv,
        "rerun_cli": rerun_cli,
    }


def _run_post_hybrid_artifacts(args, artifact_index_paths):
    if not getattr(args, "post_hybrid_artifacts", False):
        return
    if not artifact_index_paths:
        print("[post-hybrid] Nessun best_trials_index.csv disponibile: skip.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_mode = getattr(args, "post_hybrid_mode", "artifacts")
    artifacts_script_path = os.path.join(base_dir, "post_hybrid_artifacts.py")
    smart_script_path = os.path.join(base_dir, "post_hybrid_pair_smart.py")
    common_window_script_path = os.path.join(base_dir, "forecast_common_window.py")

    def _split_common_sources(values):
        out = []
        for value in values or []:
            for item in str(value).split(","):
                item = item.strip()
                if item:
                    out.append(item)
        return out

    def _run_forecast_common_window(run_dir, smart_out_dir):
        if not getattr(args, "forecast_common_window", False):
            return
        source_paths = _split_common_sources(getattr(args, "forecast_common_sources", []))
        smart_candidates = []
        canonical = os.path.join(smart_out_dir, "smart_fusion_final__forecast.csv")
        if os.path.exists(canonical):
            smart_candidates.append(canonical)
        smart_candidates.extend(
            sorted(glob.glob(os.path.join(smart_out_dir, "**", "smart_fusion_final__forecast.csv"),
                             recursive=True))
        )
        for candidate in smart_candidates:
            if candidate not in source_paths and os.path.exists(candidate):
                source_paths.append(candidate)
                break
        existing = []
        missing = []
        for path in source_paths:
            if os.path.exists(path):
                existing.append(path)
            else:
                missing.append(path)
        if missing:
            print("[forecast-common] Sorgenti mancanti ignorate:")
            for path in missing:
                print(f"  - {path}")
        if len(existing) < 2:
            print("[forecast-common] Servono almeno 2 forecast CSV esistenti: skip.")
            return
        out_dir = getattr(args, "forecast_common_out_dir", "") or os.path.join(
            smart_out_dir, "common_detected_window"
        )
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, "common_detected_forecast_window.csv")
        out_png = os.path.join(out_dir, "common_detected_forecast_window.png")
        out_json = os.path.join(out_dir, "common_detected_forecast_window.json")
        cmd = [
            sys.executable, common_window_script_path,
            "--output-csv", out_csv,
            "--output-png", out_png,
            "--output-json", out_json,
            "--score-column", getattr(args, "forecast_common_score_column", "auto"),
            "--threshold", str(getattr(args, "forecast_common_threshold", 0.5)),
            "--title", "Final common detected forecast window",
        ] + existing
        print()
        print("=" * 80)
        print("[forecast-common] Common detected window")
        print(f"Output dir:   {out_dir}")
        print("Sources:")
        for path in existing:
            print(f"  - {path}")
        print(f"Command:      {shlex.join(cmd)}")
        print("=" * 80)
        subprocess.run(cmd, check=True)

    for dataset_path, index_path in artifact_index_paths.items():
        run_dir = os.path.dirname(os.path.abspath(index_path))
        out_dir = getattr(args, "post_hybrid_out_dir", "")

        def _run_cmd(label, out_dir_value, cmd):
            print()
            print("=" * 80)
            print(f"[post-hybrid] {label}")
            print(f"Dataset:      {dataset_path}")
            print(f"Source index: {index_path}")
            print(f"Output dir:   {out_dir_value}")
            print(f"Command:      {shlex.join(cmd)}")
            print("=" * 80)
            subprocess.run(cmd, check=True)

        if script_mode in ("artifacts", "both"):
            artifacts_out_dir = out_dir or os.path.join(run_dir, "post_hybrid_checks")
            cmd = [
                sys.executable, artifacts_script_path,
                "--index-csv", index_path,
                "--out-dir", artifacts_out_dir,
                "--logic", getattr(args, "post_hybrid_logic", "and"),
                "--normalize", getattr(args, "post_hybrid_normalize", "auto"),
                "--score-column", getattr(args, "post_hybrid_score_column", "predicted"),
                "--alpha", str(getattr(args, "post_hybrid_alpha", 0.5)),
                "--threshold", str(getattr(args, "post_hybrid_threshold", 0.5)),
                "--calibrate", getattr(args, "post_hybrid_calibrate", "validation"),
                "--calibrate-metric", getattr(args, "post_hybrid_calibrate_metric", "f1"),
                "--min-recall", str(getattr(args, "post_hybrid_min_recall", 0.0)),
                "--top-candidates", str(getattr(args, "post_hybrid_top_candidates", 30)),
                "--top-pairs", str(getattr(args, "post_hybrid_top_pairs", 20)),
                "--forecast-guard", getattr(args, "post_hybrid_forecast_guard", "auto"),
                "--max-rules", str(getattr(args, "post_hybrid_max_rules", 20)),
            ]
            if getattr(args, "post_hybrid_proposal_only", False):
                cmd.append("--proposal-only")
            _run_cmd("Auto artifacts", artifacts_out_dir, cmd)

        if script_mode in ("smart", "both"):
            smart_out_dir = out_dir or os.path.join(run_dir, "post_hybrid_checks_smart")
            dataset_subfolder = os.path.splitext(os.path.basename(str(dataset_path)))[0]
            smart_cmd = [
                sys.executable, smart_script_path,
                run_dir,
                "--out-dir", smart_out_dir,
                "--dataset-subfolder", dataset_subfolder,
                "--score-column", getattr(args, "post_hybrid_score_column", "predicted"),
            ]
            smart_cmd += ["--max-rules", str(getattr(args, "post_hybrid_max_rules", 20))]
            smart_cmd += ["--max-peaks", str(getattr(args, "post_hybrid_max_peaks", 1))]
            final_peak_max = int(getattr(args, "post_hybrid_final_peak_max", 0) or 0)
            if final_peak_max > 0:
                smart_cmd += ["--final-peak-max", str(final_peak_max)]
            if getattr(args, "post_hybrid_peak_and", False):
                smart_cmd.append("--peak-and")
                smart_cmd += ["--peak-window", str(getattr(args, "post_hybrid_peak_window", 1))]
                smart_cmd += ["--peak-floor", str(getattr(args, "post_hybrid_peak_floor", 0.30))]
                smart_cmd += ["--peak-max", str(getattr(args, "post_hybrid_peak_max", 1))]
            _run_cmd("Auto smart", smart_out_dir, smart_cmd)
            _run_forecast_common_window(run_dir, smart_out_dir)


def cmd_train(args):
    _apply_inherited_run(args)
    extra_deep_presets = _load_extra_deep_presets(getattr(args, "deep_preset_configs_json", ""))
    if extra_deep_presets:
        DEEP_PRESETS.update(extra_deep_presets)
    tasks, banks, readouts, deep_presets, lcs_presets, kan_presets = _resolve_train_config(args)
    try:
        seeds = _parse_seeds_spec(args.seeds, derived_count=getattr(args, "seed_count", None))
    except (TypeError, ValueError) as exc:
        print(f"ERRORE: --seeds non interpretabile ({exc})")
        sys.exit(1)
    args._seeds_resolved = seeds
    target_window_cfg = _resolve_target_window_cfg(args)
    metric_threshold = _resolve_metric_threshold(args)
    metric_prediction_threshold = _resolve_metric_prediction_threshold(args)
    metric_score_mode = getattr(args, "event_score_mode", "isolation")
    forecast_window_cfg = _resolve_forecast_window_cfg(args)
    train_range_cfg = _resolve_train_range_cfg(args)
    show_progress = args.verbose or getattr(args, "cmd", "") == "train-max"

    if not tasks:
        print("ERRORE: specifica almeno un task con --task")
        sys.exit(1)

    for task in tasks:
        if is_csv_task(task):
            continue
        if task not in TASKS:
            print(f"ERRORE: task sconosciuto '{task}'. Disponibili: {list(TASKS)}")
            sys.exit(1)
    if target_window_cfg is not None and any(not is_csv_task(task) for task in tasks):
        print("ERRORE: --target-window-* e' disponibile solo in modalita' CSV")
        sys.exit(1)
    if getattr(args, "backtest_event_windows", False) and any(not is_csv_task(task) for task in tasks):
        print("ERRORE: --backtest-event-windows e' disponibile solo in modalita' CSV")
        sys.exit(1)
    if forecast_window_cfg is not None and any(not is_csv_task(task) for task in tasks):
        print("ERRORE: --forecast-start-date/--forecast-end-date sono disponibili solo in modalita' CSV")
        sys.exit(1)
    if train_range_cfg is not None and any(not is_csv_task(task) for task in tasks):
        print("ERRORE: --train-start-date/--train-end-date sono disponibili solo in modalita' CSV")
        sys.exit(1)

    for b in banks:
        if b not in BANKS:
            print(f"ERRORE: bank sconosciuto '{b}'. Disponibili: {list(BANKS)}")
            sys.exit(1)
    for r in readouts:
        if r not in READOUTS:
            print(f"ERRORE: readout sconosciuto '{r}'. Disponibili: {list(READOUTS)}")
            sys.exit(1)
    for p in deep_presets:
        if p not in DEEP_PRESETS:
            print(f"ERRORE: deep preset sconosciuto '{p}'. "
                  f"Disponibili: {list(DEEP_PRESETS)}")
            sys.exit(1)
    for p in lcs_presets:
        if p not in LCS_PRESETS:
            print(f"ERRORE: LCS preset sconosciuto '{p}'. "
                  f"Disponibili: {list(LCS_PRESETS)}")
            sys.exit(1)
    if kan_presets and not KAN_AVAILABLE:
        print("ERRORE: KAN richiesto ma pykan non e' disponibile nella venv")
        sys.exit(1)
    for p in kan_presets:
        if p not in KAN_PRESETS:
            print(f"ERRORE: KAN preset sconosciuto '{p}'. "
                  f"Disponibili: {list(KAN_PRESETS)}")
            sys.exit(1)
    if args.max_iter is not None and args.max_iter < 1:
        print("ERRORE: --max-iter deve essere >= 1")
        sys.exit(1)

    configure_runtime_controls(args.max_iter)
    configure_shape_weight(getattr(args, "shape_weight", 0.6))

    custom_cfg = _build_custom_deep_cfg(args)
    deep_preset_cfgs = _resolve_deep_preset_cfgs(deep_presets, args)
    custom_lcs_cfg = _build_custom_lcs_cfg(args)
    lcs_preset_cfgs = _resolve_lcs_preset_cfgs(lcs_presets, args)
    kan_preset_cfgs = _resolve_kan_preset_cfgs(kan_presets, args)
    hybrid_specs = _resolve_hybrid_specs(args, banks, readouts, deep_presets)
    kan_hybrid_specs = _resolve_hybrid_specs(args, banks, readouts, deep_presets,
                                             enabled_attr="hybrid_kan")
    for spec in list(hybrid_specs) + list(kan_hybrid_specs):
        partner = spec.get("partner", {})
        if partner.get("kind") == "deep":
            preset = partner.get("preset")
            if preset != "custom" and preset not in DEEP_PRESETS:
                print(f"ERRORE: hybrid deep preset sconosciuto '{preset}'")
                sys.exit(1)
        else:
            if partner.get("bank") not in BANKS:
                print(f"ERRORE: hybrid bank sconosciuto '{partner.get('bank')}'")
                sys.exit(1)
            if partner.get("readout") not in READOUTS:
                print(f"ERRORE: hybrid readout sconosciuto '{partner.get('readout')}'")
                sys.exit(1)
    deep_val_report = _resolve_deep_val_cfg(args)

    print(f"Task: {tasks if len(tasks) > 1 else tasks[0]}")
    print(f"Banks: {banks}")
    print(f"Readouts: {readouts}")
    if args.max_iter is not None:
        print(f"Max iter/epochs override: {args.max_iter}")
    seeds_label = f"{len(seeds)} ({seeds})" if len(seeds) <= 12 else f"{len(seeds)} (first={seeds[:6]}...)"
    if target_window_cfg is not None:
        print(f"Seeds: {seeds_label}  Train/Test: ricavati da target window")
    else:
        print(f"Seeds: {seeds_label}  Train: {args.n_train}  Test: {args.n_test}")
    print(f"Noise std: {args.noise}")
    print(f"Metric mode: {args.metric_mode}")
    if metric_prediction_threshold is not None:
        print(f"Event prediction threshold: {metric_prediction_threshold}")
    print(f"Event score mode: {metric_score_mode}")
    jobs = int(getattr(args, "jobs", 1) or 1)
    if jobs <= 0:
        jobs = os.cpu_count() or 1
    print(f"Parallel jobs: {jobs}")
    if _final_eval_enabled(args):
        shape_filter_on = not bool(getattr(args, "no_final_eval_shape_filter", False))
        print("Final evaluation:"
              f" rank_power={getattr(args, 'final_eval_rank_power', 1.0)}"
              f" shape_filter={'on' if shape_filter_on else 'off'}"
              f" best={getattr(args, 'final_eval_best_fraction', 0.25)}"
              f" worst={getattr(args, 'final_eval_worst_fraction', 0.10)}"
              f" shape_power={getattr(args, 'final_eval_shape_power', 0.0)}"
              f" negative_inertia={not getattr(args, 'no_final_eval_negative_inertia', False)}"
              f" low_threshold={getattr(args, 'final_eval_low_threshold', 1e-9)}"
              f" reverse_weight_x={getattr(args, 'final_eval_negative_weight', 3.0)}")
    if deep_presets:
        print(f"DeepNet end-to-end presets: {deep_presets}")
    if custom_cfg:
        print(f"DeepNet custom: hidden={custom_cfg.resolve_hidden(0) if custom_cfg.hidden_sizes else 'auto'}"
              f" act={custom_cfg.activation} dropout={custom_cfg.dropout}"
              f" epochs={custom_cfg.epochs}")
    if deep_presets or custom_cfg:
        print("DeepNet validation:"
              f" metric={deep_val_report['validation_metric']}"
              f" threshold={deep_val_report['validation_threshold']}"
              f" val_events={deep_val_report['event_count']}"
              f" val_pre={deep_val_report['pre_records']}"
              f" val_post={deep_val_report['post_records']}")
    if lcs_presets:
        print(f"LCS presets: {lcs_presets}")
    if kan_presets:
        print(f"KAN presets: {kan_presets}")
        if getattr(args, "kan_quiet", False):
            print("KAN progress: quiet (pykan per-epoch progress suppressed; trial-level progress remains)")
        for name in kan_presets:
            cfg = kan_preset_cfgs.get(name)
            if cfg:
                print("KAN preset:"
                      f" name={name}"
                      f" width={cfg.hidden_width}"
                      f" layers={cfg.hidden_layers}"
                      f" grid={cfg.grid}"
                      f" epochs={cfg.epochs}"
                      f" lr={cfg.lr}"
                      f" device={cfg.device}")
    if custom_lcs_cfg:
        print("LCS custom:"
              f" pop={custom_lcs_cfg.population_size}"
              f" epochs={custom_lcs_cfg.epochs}"
              f" ga_freq={custom_lcs_cfg.ga_frequency}"
              f" mut={custom_lcs_cfg.mutation_rate}"
              f" cx={custom_lcs_cfg.crossover_rate}"
              f" wildcard={custom_lcs_cfg.wildcard_prob}"
              f" pos_wildcard={custom_lcs_cfg.positive_wildcard_prob}"
              f" pos_cover={custom_lcs_cfg.positive_covering_multiplier}"
              f" threshold={custom_lcs_cfg.binary_threshold}"
              f" val_split={custom_lcs_cfg.validation_split}"
              f" val_events={custom_lcs_cfg.validation_event_count}"
              f" val_pre={custom_lcs_cfg.validation_pre_records}"
              f" val_post={custom_lcs_cfg.validation_post_records}"
              f" patience={custom_lcs_cfg.early_stop_patience}"
              f" fitness={custom_lcs_cfg.fitness_mode}"
              f" pos_weight={custom_lcs_cfg.positive_weight}"
              f" pos_replay={custom_lcs_cfg.positive_replay}"
              f" pos_vote={custom_lcs_cfg.positive_vote_weight}"
              f" selection={custom_lcs_cfg.selection_metric}"
              f" restore_best={custom_lcs_cfg.restore_best_population}"
              f" final_retrain={custom_lcs_cfg.final_retrain_full_train}")
    if hybrid_specs:
        print(f"Hybrid LCS trials: {len(hybrid_specs)} partner/mode per LCS config")
    if kan_hybrid_specs:
        print(f"Hybrid KAN trials: {len(kan_hybrid_specs)} partner/mode per KAN config")
    if getattr(args, "_inherit_summary", None):
        summary = args._inherit_summary
        always_lbl = ",".join(summary.get("always_include") or []) or "(none)"
        print("Inherited targeted run:"
              f" source={summary['index_path']}"
              f" best={summary['requested_best']}"
              f" always_include={always_lbl}"
              f" selected={len(summary['selected'])}")
        for item in summary["selected"][:12]:
            print(f"  inherit {item['score']:.4f}  {item['bank']}/{item['readout']}")
    if target_window_cfg is not None:
        print("Target window:"
              f" threshold>={target_window_cfg['threshold']}"
              f" count={target_window_cfg['event_count']}"
              f" start={target_window_cfg['event_start']}"
              f" pre_records={target_window_cfg['pre_records']}"
              f" post_records={target_window_cfg['post_records']}"
              f" isolated={target_window_cfg.get('isolated_windows', False)}")
        if target_window_cfg.get("no_autoclip") or target_window_cfg.get("suppress_autodate_clipping"):
            print("Autoclip: disabled")
        elif target_window_cfg.get("force_autoclip"):
            print("Autoclip: forced")
        elif target_window_cfg.get("threshold") is not None and target_window_cfg.get("event_count", 0) > 0:
            print("Autoclip: skipped (explicit event window)")
        else:
            print("Autoclip: auto")
        print(f"Time-series policy: {args.time_series}"
              f"{' + allow train-after-test' if args.allow_train_after_test else ''}")
    if forecast_window_cfg is not None:
        print("Forecast window richiesta:"
              f" start={forecast_window_cfg['start_raw']}"
              f" end={forecast_window_cfg['end_raw'] or '(fino alla fine del dataset)'}")
        print(f"Forecast trainset: {args.forecast_trainset}")
    if args.backtest_event_windows:
        print("Backtest ranking:"
              f" recency={args.backtest_recency_weight}"
              f" strength={args.backtest_recency_strength}")
    if args.no_train_sample_weighting:
        print("Training sample weighting: disabled")
    else:
        print("Training sample weighting:"
              f" recency={args.train_recency_weight}"
              f" strength={args.train_recency_strength}"
              f" event_weight={args.train_event_weight}"
              f" max_event_weight={args.train_max_event_weight}")
    if args.recent_validation_window:
        print("Recent validation:"
              f" event_count={args.recent_validation_event_count or '(auto)'}"
              f" pre={args.recent_validation_pre_records if args.recent_validation_pre_records >= 0 else '(auto)'}"
              f" post={args.recent_validation_post_records if args.recent_validation_post_records >= 0 else '(auto)'}"
              f" weight={args.recent_validation_weight}"
              f" max_lookback={args.validation_max_lookback_records or '(off)'}")
    if train_range_cfg is not None:
        print("Train date range richiesto:"
              f" start={train_range_cfg['start_raw'] or '(inizio file)'}"
              f" end={train_range_cfg['end_raw'] or '(fine file)'}")
    print()

    kpi_w = {"mse": args.w_mse, "speed": args.w_speed, "compactness": args.w_params}
    task_summaries = []
    all_results = []
    started_at = time.perf_counter()

    # Risolvi --db relativo nella dir del primo CSV task se l'utente ha
    # passato solo un nome file. Cosi il DB sta accanto al master.csv.
    db_path = args.db
    db_has_dir = bool(os.path.dirname(db_path))
    if not db_has_dir:
        first_csv = next((t for t in tasks if is_csv_task(t)), None)
        if first_csv is not None:
            csv_dir = os.path.dirname(os.path.abspath(first_csv))
            resolved = os.path.join(csv_dir, db_path)
            print(f"DB path risolto: {resolved}")
            db_path = resolved
            args.db = resolved

    conn = init_db(db_path)
    run_stamp = timestamp_slug()
    artifact_run_dirs = {}
    artifact_index_rows = {}
    artifact_index_paths = {}
    try:
        for idx, task_name in enumerate(tasks, start=1):
            csv_meta = None
            forecast_window = None
            if len(tasks) > 1:
                print(f"\n=== Task {task_name} ({idx}/{len(tasks)}) ===")

            if is_csv_task(task_name):
                _validate_csv_path(task_name)
                try:
                    csv_meta = load_csv_dataset(
                        task_name,
                        target_cols_list=args.target_cols_list,
                        skip_cols_list=args.skip_cols_list,
                    )
                except ValueError as e:
                    print(f"Errore lettura CSV: {e}")
                    print("  Verifica che le colonne target/skip esistano nell'header.")
                    raise SystemExit(2)
                if train_range_cfg is not None:
                    if not csv_meta.get("context_col") or csv_meta.get("context_datetimes") is None:
                        raise ValueError(
                            "Train date range richiesto, ma il CSV non ha una colonna date/time "
                            "parseabile completamente"
                        )
                    matching = np.flatnonzero([
                        dt is not None
                        and (train_range_cfg["start_dt"] is None or dt >= train_range_cfg["start_dt"])
                        and (train_range_cfg["end_dt"] is None or dt <= train_range_cfg["end_dt"])
                        for dt in csv_meta["context_datetimes"]
                    ])
                    if matching.size == 0:
                        raise ValueError("Nessun record trovato nel range richiesto da --train-start-date/--train-end-date")
                    csv_meta = _subset_csv_meta(csv_meta, int(matching[0]), int(matching[-1]))
                forecast_window = None
                if csv_meta["multi_target_requested"]:
                    requested = ",".join(csv_meta["requested_target_cols"])
                    print("multi target non ancora implementato, uso la prima colonna:"
                          f" {csv_meta['target_col']} (richieste: {requested})")
                print(f"CSV: {task_name}")
                print(f"Target: {csv_meta['target_col']}")
                print(f"Feature usate: {len(csv_meta['feature_cols'])}")

                # Crea la run_dir SUBITO (prima del benchmark) cosi i file
                # incrementali (incremental_trials.csv, ecc.) cominciano a
                # popolarsi mentre i trial girano.
                dataset_path_eager = csv_meta["path"]
                if dataset_path_eager not in artifact_run_dirs:
                    inherit_parent_dirs = getattr(args, "_inherit_parent_run_dirs", {}) or {}
                    inherit_level_no = int(getattr(args, "_inherit_level_no", 0) or 0)
                    artifact_run_dirs[dataset_path_eager] = ensure_run_dir(
                        dataset_path_eager, args.cmd, run_stamp,
                        parent_dir=inherit_parent_dirs.get(dataset_path_eager),
                        level=inherit_level_no,
                    )
                    artifact_index_rows[dataset_path_eager] = []
                    write_run_signature(
                        artifact_run_dirs[dataset_path_eager],
                        _build_run_signature_payload(args, dataset_path=dataset_path_eager),
                    )
                    print(f"Artifact dir: {artifact_run_dirs[dataset_path_eager]}")
                _set_incremental_trials_sink(
                    os.path.join(artifact_run_dirs[dataset_path_eager],
                                 "incremental_trials.csv")
                )
                if csv_meta.get("context_col") and csv_meta.get("context_values"):
                    print("Periodo dataset effettivo:"
                          f" {_format_context_value(csv_meta, 0)}"
                          f" -> {_format_context_value(csv_meta, len(csv_meta['y']) - 1)}"
                          f" (row {int(csv_meta['row_indices'][0])} -> {int(csv_meta['row_indices'][-1])})")
                metric_profile = resolve_metric_profile(
                    csv_meta["y"], mode=args.metric_mode, threshold=metric_threshold,
                    prediction_threshold=metric_prediction_threshold,
                    score_mode=metric_score_mode,
                )
                metric_profile["readability_weight"] = float(
                    getattr(args, "readability_weight", 0.0) or 0.0
                )
                metric_profile["readability_floor"] = float(
                    getattr(args, "readability_floor", 0.0) or 0.0
                )
                training_weight_cfg = _resolve_training_weight_cfg(
                    args, metric_threshold=metric_profile.get("threshold")
                )
                _set_immediate_inversion_context(
                    args=args, metric_profile=metric_profile,
                    kpi_weights=kpi_w, csv_meta=csv_meta,
                )
                feature_selection_cfg = {
                    "k_best": getattr(args, "feature_selection_k_best", None),
                    "threshold": getattr(args, "feature_selection_threshold", None),
                    "percentile": getattr(args, "feature_selection_percentile", None),
                    "min_features": getattr(args, "feature_selection_min_features", None),
                    "max_features": getattr(args, "feature_selection_max_features", None),
                    "feature_names": csv_meta["feature_cols"]
                }
                if (feature_selection_cfg["k_best"] is not None or
                    feature_selection_cfg["threshold"] is not None or
                    feature_selection_cfg["percentile"] is not None or
                    feature_selection_cfg["min_features"] is not None or
                    feature_selection_cfg["max_features"] is not None):
                    print("Feature selection attiva:"
                          f" k_best={feature_selection_cfg['k_best']}"
                          f" threshold={feature_selection_cfg['threshold']}"
                          f" percentile={feature_selection_cfg['percentile']}"
                          f" min_features={feature_selection_cfg['min_features']}"
                          f" max_features={feature_selection_cfg['max_features']}")
                print("Metriche auto: "
                      + _describe_metric_choice(csv_meta["y"], metric_profile, args.metric_mode))
                _print_metric_legend(metric_profile)
                if csv_meta["skip_cols"]:
                    print(f"Skip cols: {csv_meta['skip_cols']}")
                if forecast_window_cfg is not None:
                    if not csv_meta.get("context_col") or csv_meta.get("context_datetimes") is None:
                        raise ValueError(
                            "Forecast date window richiesta, ma il CSV non ha una colonna date/time "
                            "parseabile completamente"
                        )
                    forecast_window = resolve_context_window_indices(
                        csv_meta["context_datetimes"],
                        forecast_window_cfg["start_dt"],
                        forecast_window_cfg["end_dt"],
                    )
                    if forecast_window is None:
                        raise ValueError("Nessun record trovato nella forecast window richiesta")
                    print("Forecast window risolta:"
                          f" row_start={forecast_window['info']['resolved_start']}"
                          f" row_end={forecast_window['info']['resolved_end']}"
                          f" n_rows={forecast_window['info']['n_rows']}")
                    _print_period_summary("Forecast period", forecast_window["indices"], csv_meta)
                if target_window_cfg is not None:
                    resolved_window = resolve_target_window_indices(
                        csv_meta["y"], target_window_cfg,
                        context_datetimes=csv_meta.get("context_datetimes"),
                    )
                    if resolved_window is not None:
                        split_info = resolved_window["info"]
                        print(f"Train/Test ricavati: {split_info['n_train']} / {split_info['n_test']}")
                        print("Target window risolta:"
                              f" test_start={split_info['test_start']}"
                              f" test_end={split_info['test_end']}"
                              f" used_events={split_info['used_event_count']}")
                        autoclip_status = split_info.get("autoclip_status")
                        autoclip_reason = split_info.get("autoclip_reason")
                        if autoclip_status == "applied":
                            clip_dt = split_info.get("clip_last_datetime")
                            clip_display = clip_dt or split_info.get("clip_last_index")
                            print(f"Autoclip: applied up to {clip_display}")
                        elif autoclip_status == "skipped" and autoclip_reason == "explicit_event_window":
                            print("Autoclip: skipped (explicit event window)")
                        elif autoclip_status == "disabled":
                            print("Autoclip: disabled")
                        elif autoclip_status == "unavailable":
                            print("Autoclip: unavailable (no parsed datetime context)")
                        if (split_info.get("test_end") is not None
                                and split_info.get("effective_end") is not None
                                and split_info.get("test_end") < split_info.get("effective_end")
                                and not split_info.get("autodate_clipped")):
                            print("Target window end:"
                                  f" {_format_context_value(csv_meta, split_info['test_end'])}"
                                  f" (row {int(csv_meta['row_indices'][split_info['test_end']])}),"
                                  f" dataset_end={_format_context_value(csv_meta, split_info['effective_end'])}"
                                  f" (row {int(csv_meta['row_indices'][split_info['effective_end']])})")
                        _print_period_summary("Train period", resolved_window["train_idx"], csv_meta)
                        _print_period_summary("Test period", resolved_window["test_idx"], csv_meta)
                        if forecast_window is not None:
                            forecast_fit_idx, _ = _resolve_forecast_fit_indices(
                                {"_artifacts": {"test_indices": resolved_window["test_idx"]}},
                                len(csv_meta["y"]),
                                forecast_window["indices"],
                                args.forecast_trainset,
                                time_series_cfg=_resolve_time_series_cfg(args),
                                context_datetimes=csv_meta.get("context_datetimes"),
                            )
                            if forecast_fit_idx is not None and len(forecast_fit_idx) > 0:
                                _print_period_summary("Forecast fit period", forecast_fit_idx, csv_meta)
                        if split_info.get("autodate_clipped"):
                            print("Autodate clipping:"
                                  f" original_test_end={split_info.get('original_test_end')}"
                                  f" clipped_test_end={split_info.get('test_end')}")
                backtest_windows = _resolve_backtest_window_cfgs(
                    csv_meta["y"], args, target_window_cfg=target_window_cfg,
                    forecast_window=forecast_window,
                )
                try:
                    recent_validation_cfg = _resolve_recent_validation_window_cfg(
                        csv_meta["y"], args, target_window_cfg=target_window_cfg,
                        forecast_window=forecast_window,
                    )
                except ValueError as exc:
                    if not getattr(args, "recent_validation_skip_if_unavailable", False):
                        raise
                    recent_validation_cfg = None
                    print(f"Recent validation skipped: {exc}")
                if backtest_windows:
                    print("Backtest event-window:"
                          f" windows={len(backtest_windows)}"
                          f" event_count={backtest_windows[0]['event_count']}"
                          f" pre_records={backtest_windows[0]['pre_records']}"
                          f" post_records={backtest_windows[0]['post_records']}"
                          f" step_events={args.backtest_step_events}"
                          f" max_lookback={backtest_windows[0].get('validation_max_lookback_records', 0) or '(off)'}"
                          f" recency={args.backtest_recency_weight}"
                          f" strength={args.backtest_recency_strength}")
                    results = []
                    for bt_no, bt_cfg in enumerate(backtest_windows, start=1):
                        resolved_bt = resolve_target_window_indices(
                            csv_meta["y"], bt_cfg,
                            context_datetimes=csv_meta.get("context_datetimes"),
                        )
                        if resolved_bt is not None:
                            info = resolved_bt["info"]
                            print("Backtest window"
                                  f" {bt_no}/{len(backtest_windows)}:"
                                  f" test_start={info['test_start']}"
                                  f" test_end={info['test_end']}"
                                  f" used_events={info['used_event_count']}")
                            _print_period_summary("Backtest test period",
                                                  resolved_bt["test_idx"], csv_meta)
                        bt_name = (f"{os.path.basename(task_name)}"
                                   f"__bt{bt_no:03d}_ev{bt_cfg['backtest_event_start_pos']}"
                                   f"-{bt_cfg['backtest_event_end_pos']}")
                        bt_results = run_benchmark_dataset(
                            X=csv_meta["X"], y=csv_meta["y"], dataset_name=bt_name,
                            banks=banks, readouts=readouts,
                            n_train=args.n_train, n_test=args.n_test, seeds=seeds,
                            kpi_weights=kpi_w,
                            progress_cb=_progress if show_progress else None,
                            deep_presets=deep_presets, custom_deep_cfg=custom_cfg,
                            deep_preset_cfgs=deep_preset_cfgs,
                            lcs_presets=lcs_presets, custom_lcs_cfg=custom_lcs_cfg,
                            lcs_preset_cfgs=lcs_preset_cfgs,
                            kan_presets=kan_presets,
                            kan_preset_cfgs=kan_preset_cfgs,
                            hybrid_specs=hybrid_specs,
                            kan_hybrid_specs=kan_hybrid_specs,
                            target_window_cfg=bt_cfg,
                            metric_mode=args.metric_mode,
                            metric_threshold=metric_threshold,
                            metric_prediction_threshold=metric_prediction_threshold,
                            metric_score_mode=metric_score_mode,
                            context_datetimes=csv_meta.get("context_datetimes"),
                            training_weight_cfg=training_weight_cfg,
                            trial_filter=getattr(args, "_inherit_trial_filter", None),
                            n_jobs=jobs,
                            feature_selection_cfg=feature_selection_cfg,
                        )
                        for r in bt_results:
                            r.setdefault("extra", {})
                            ranking_weight = _backtest_recency_weight(
                                bt_no, len(backtest_windows), args
                            )
                            r["extra"]["backtest_info"] = {
                                "window_no": int(bt_no),
                                "total_windows": int(len(backtest_windows)),
                                "event_start_pos": int(bt_cfg["backtest_event_start_pos"]),
                                "event_end_pos": int(bt_cfg["backtest_event_end_pos"]),
                                "event_count": int(bt_cfg["event_count"]),
                                "requested_event_count": int(bt_cfg.get("requested_event_count", bt_cfg["event_count"])),
                                "pre_records": int(bt_cfg["pre_records"]),
                                "post_records": int(bt_cfg["post_records"]),
                                "validation_max_lookback_records": int(bt_cfg.get("validation_max_lookback_records", 0)),
                                "autoclip_event_count": bool(bt_cfg.get("autoclip_event_count", False)),
                                "ranking_weight": float(ranking_weight),
                            }
                            r["extra"]["ranking_weight"] = float(ranking_weight)
                        results.extend(bt_results)
                    if recent_validation_cfg is not None:
                        resolved_recent = resolve_target_window_indices(
                            csv_meta["y"], recent_validation_cfg,
                            context_datetimes=csv_meta.get("context_datetimes"),
                        )
                        recent_window_info = {}
                        if resolved_recent is not None:
                            info = resolved_recent["info"]
                            recent_window_info = dict(info)
                            print("Recent validation window:"
                                  f" test_start={info['test_start']}"
                                  f" test_end={info['test_end']}"
                                  f" used_events={info['used_event_count']}"
                                  f" random_negatives={info.get('random_negative_count_used', 0)}"
                                  f" weight={args.recent_validation_weight}")
                            _print_period_summary("Recent validation period",
                                                  resolved_recent["test_idx"], csv_meta)
                        recent_name = (f"{os.path.basename(task_name)}"
                                       f"__recent_ev{recent_validation_cfg['recent_validation_event_start_pos']}"
                                       f"-{recent_validation_cfg['recent_validation_event_end_pos']}")
                        recent_results = run_benchmark_dataset(
                            X=csv_meta["X"], y=csv_meta["y"], dataset_name=recent_name,
                            banks=banks, readouts=readouts,
                            n_train=args.n_train, n_test=args.n_test, seeds=seeds,
                            kpi_weights=kpi_w,
                            progress_cb=_progress if show_progress else None,
                            deep_presets=deep_presets, custom_deep_cfg=custom_cfg,
                            deep_preset_cfgs=deep_preset_cfgs,
                            lcs_presets=lcs_presets, custom_lcs_cfg=custom_lcs_cfg,
                            lcs_preset_cfgs=lcs_preset_cfgs,
                            kan_presets=kan_presets,
                            kan_preset_cfgs=kan_preset_cfgs,
                            hybrid_specs=hybrid_specs,
                            kan_hybrid_specs=kan_hybrid_specs,
                            target_window_cfg=recent_validation_cfg,
                            metric_mode=args.metric_mode,
                            metric_threshold=metric_threshold,
                            metric_prediction_threshold=metric_prediction_threshold,
                            metric_score_mode=metric_score_mode,
                            context_datetimes=csv_meta.get("context_datetimes"),
                            training_weight_cfg=training_weight_cfg,
                            trial_filter=getattr(args, "_inherit_trial_filter", None),
                            n_jobs=jobs,
                            feature_selection_cfg=feature_selection_cfg,
                        )
                        for r in recent_results:
                            r.setdefault("extra", {})
                            r["extra"]["recent_validation_info"] = {
                                "event_start_pos": int(recent_validation_cfg["recent_validation_event_start_pos"]),
                                "event_end_pos": int(recent_validation_cfg["recent_validation_event_end_pos"]),
                                "event_count": int(recent_validation_cfg["event_count"]),
                                "requested_event_count": int(recent_validation_cfg.get("requested_event_count", recent_validation_cfg["event_count"])),
                                "pre_records": int(recent_validation_cfg["pre_records"]),
                                "post_records": int(recent_validation_cfg["post_records"]),
                                "validation_max_lookback_records": int(recent_validation_cfg.get("validation_max_lookback_records", 0)),
                                "autoclip_event_count": bool(recent_validation_cfg.get("autoclip_event_count", False)),
                                "random_negative_count_requested": int(recent_validation_cfg.get("random_negative_count", 0)),
                                "random_negative_count_used": int(recent_window_info.get("random_negative_count_used", 0)),
                                "random_negative_indices": list(recent_window_info.get("random_negative_indices", [])),
                                "random_negative_seed": int(recent_validation_cfg.get("random_negative_seed", 0)),
                                "ranking_weight": float(args.recent_validation_weight),
                            }
                            r["extra"]["ranking_weight"] = float(args.recent_validation_weight)
                        results.extend(recent_results)
                else:
                    results = run_benchmark_dataset(
                        X=csv_meta["X"], y=csv_meta["y"], dataset_name=os.path.basename(task_name),
                        banks=banks, readouts=readouts,
                        n_train=args.n_train, n_test=args.n_test, seeds=seeds,
                        kpi_weights=kpi_w,
                        progress_cb=_progress if show_progress else None,
                        deep_presets=deep_presets, custom_deep_cfg=custom_cfg,
                        deep_preset_cfgs=deep_preset_cfgs,
                        lcs_presets=lcs_presets, custom_lcs_cfg=custom_lcs_cfg,
                        lcs_preset_cfgs=lcs_preset_cfgs,
                        kan_presets=kan_presets,
                        kan_preset_cfgs=kan_preset_cfgs,
                        hybrid_specs=hybrid_specs,
                        kan_hybrid_specs=kan_hybrid_specs,
                        target_window_cfg=target_window_cfg,
                        metric_mode=args.metric_mode,
                        metric_threshold=metric_threshold,
                        metric_prediction_threshold=metric_prediction_threshold,
                        metric_score_mode=metric_score_mode,
                        context_datetimes=csv_meta.get("context_datetimes"),
                        training_weight_cfg=training_weight_cfg,
                        trial_filter=getattr(args, "_inherit_trial_filter", None),
                        n_jobs=jobs,
                        feature_selection_cfg=feature_selection_cfg,
                    )
                    if recent_validation_cfg is not None:
                        print("Recent validation: gia' rappresentata dal test principale"
                              " (nessun backtest separato attivo)")
            else:
                metric_profile = resolve_metric_profile(
                    generate_dataset(task_name, args.n_train, seed=seeds[0], noise_std=args.noise)[1],
                    mode=args.metric_mode, threshold=metric_threshold,
                    prediction_threshold=metric_prediction_threshold,
                    score_mode=metric_score_mode,
                )
                metric_profile["readability_weight"] = float(
                    getattr(args, "readability_weight", 0.0) or 0.0
                )
                metric_profile["readability_floor"] = float(
                    getattr(args, "readability_floor", 0.0) or 0.0
                )
                _set_immediate_inversion_context(
                    args=args, metric_profile=metric_profile,
                    kpi_weights=kpi_w, csv_meta=None,
                )
                print("Metriche auto: "
                      + _describe_metric_choice(
                          generate_dataset(task_name, args.n_train, seed=seeds[0], noise_std=args.noise)[1],
                          metric_profile, args.metric_mode
                      ))
                _print_metric_legend(metric_profile)
                results = run_benchmark(
                    task_name=task_name, banks=banks, readouts=readouts,
                    n_train=args.n_train, n_test=args.n_test, seeds=seeds,
                    noise_std=args.noise, kpi_weights=kpi_w,
                    progress_cb=_progress if show_progress else None,
                    deep_presets=deep_presets, custom_deep_cfg=custom_cfg,
                    deep_preset_cfgs=deep_preset_cfgs,
                    lcs_presets=lcs_presets, custom_lcs_cfg=custom_lcs_cfg,
                    lcs_preset_cfgs=lcs_preset_cfgs,
                    kan_presets=kan_presets,
                    kan_preset_cfgs=kan_preset_cfgs,
                    hybrid_specs=hybrid_specs,
                    kan_hybrid_specs=kan_hybrid_specs,
                    metric_mode=args.metric_mode,
                    metric_threshold=metric_threshold,
                    metric_prediction_threshold=metric_prediction_threshold,
                    metric_score_mode=metric_score_mode,
                    trial_filter=getattr(args, "_inherit_trial_filter", None),
                    n_jobs=jobs,
                )

            inverted_twins = _build_inverted_twins(
                results, metric_profile, kpi_w, csv_meta, args
            )
            if inverted_twins:
                results = list(results) + inverted_twins
                inv_groups = sorted({
                    (t.get("bank"), t.get("readout"))
                    for t in inverted_twins
                })
                print(f"Inverted twins: {len(inverted_twins)} trial twin generati"
                      f" ({len(inv_groups)} bank/readout)")

            _ensure_trial_serials(results)
            for r in results:
                if csv_meta is not None:
                    r.setdefault("extra", {})
                    r["extra"].update({
                        "dataset_path": csv_meta["path"],
                        "target_col": csv_meta["target_col"],
                        "skip_cols": csv_meta["skip_cols"],
                    })
                    if "feature_cols" not in r["extra"]:
                        r["extra"]["feature_cols"] = csv_meta["feature_cols"]
                insert_result(conn, r)

            all_results.extend(results)
            agg = aggregate_results(results)
            if agg:
                task_summaries.append({
                    "task": task_name,
                    "winner": agg[0],
                    "significant": significance(agg),
                })
                if csv_meta is not None and (
                    getattr(args, "cmd", "") == "train-max"
                    or forecast_window_cfg is not None
                    or _final_eval_enabled(args)
                ):
                    best_trials = _select_best_trials_for_agg(results, agg)
                    if best_trials:
                        dataset_path = csv_meta["path"]
                        if dataset_path not in artifact_run_dirs:
                            inherit_parent_dirs = getattr(args, "_inherit_parent_run_dirs", {}) or {}
                            inherit_level_no = int(getattr(args, "_inherit_level_no", 0) or 0)
                            artifact_run_dirs[dataset_path] = ensure_run_dir(
                                dataset_path, args.cmd, run_stamp,
                                parent_dir=inherit_parent_dirs.get(dataset_path),
                                level=inherit_level_no,
                            )
                            artifact_index_rows[dataset_path] = []
                            write_run_signature(
                                artifact_run_dirs[dataset_path],
                                _build_run_signature_payload(args, dataset_path=dataset_path),
                            )
                            print(f"Artifact dir: {artifact_run_dirs[dataset_path]}")
                        chart_paths = _export_summary_charts(
                            artifact_run_dirs[dataset_path],
                            task_name,
                            results,
                            agg,
                            csv_meta,
                        )
                        print(f"Ranking plot:      {chart_paths['ranking_all_variants_png']}")
                        print(f"Technique plot:    {chart_paths['ranking_by_technique_png']}")
                        if chart_paths.get("lcs_rules_map_png"):
                            print(f"LCS rules plot:    {chart_paths['lcs_rules_map_png']}")
                        keep_set, best_idx_set, worst_idx_set = _classify_keep_set(
                            best_trials, args
                        )
                        keep_active = (
                            int(getattr(args, "keep_best", 0) or 0) > 0
                            or int(getattr(args, "keep_worst", 0) or 0) > 0
                        )
                        if keep_active:
                            print(
                                f"Keep filter: best={len(best_idx_set)}"
                                f" worst={len(worst_idx_set)}"
                                f" total_kept={len(keep_set)}/{len(best_trials)}"
                                " (LCS/hybrid sempre inclusi)"
                            )
                        all_trials_csv_rows = []
                        collage_tiles = []
                        collage_best_idx = set()
                        collage_worst_idx = set()
                        task_label = os.path.splitext(os.path.basename(task_name))[0]
                        for trial_pos, (winner_row, best_trial) in enumerate(best_trials):
                            in_keep = trial_pos in keep_set
                            if forecast_window is not None and in_keep:
                                _populate_requested_forecast(
                                    best_trial, csv_meta, forecast_window, args,
                                    deep_preset_cfgs, custom_cfg,
                                    metric_profile=metric_profile,
                                    training_weight_cfg=training_weight_cfg,
                                )
                                fc_info = best_trial.get("extra", {}).get("forecast_info", {})
                                print("Forecast fit risolto:"
                                      f" bank={best_trial['bank']}"
                                      f" readout={best_trial['readout']}"
                                      f" mode={fc_info.get('trainset_mode')}"
                                      f" fit_start={fc_info.get('fit_start')}"
                                      f" fit_end={fc_info.get('fit_end')}"
                                      f" fit_rows={fc_info.get('fit_rows')}")
                            window_trials = _collect_window_trials_for_combined(
                                results, best_trial["bank"], best_trial["readout"],
                                best_trial.get("seed"),
                            )
                            validation_segments = []
                            for wt in window_trials:
                                role = wt["role"]
                                if role == "backtest":
                                    label = f"backtest_w{wt['window_no']}"
                                elif role == "recent_val":
                                    label = "recent_validation"
                                else:
                                    label = "test"
                                validation_segments.append({"label": label,
                                                            "trial": wt["trial"]})

                            csv_segments = []
                            for spec in validation_segments:
                                tr = spec["trial"]
                                seg_art = tr.get("_artifacts", {}) or {}
                                seg_idx = seg_art.get("test_indices", [])
                                if seg_idx is None or len(seg_idx) == 0:
                                    continue
                                ctx_vals = csv_meta.get("context_values")
                                row_indices_full = csv_meta.get("row_indices")
                                seg_ctx = []
                                seg_rows = []
                                for ix in seg_idx:
                                    try:
                                        seg_ctx.append(ctx_vals[int(ix)] if ctx_vals is not None else None)
                                    except (IndexError, TypeError, ValueError):
                                        seg_ctx.append(None)
                                    try:
                                        seg_rows.append(int(row_indices_full[int(ix)])
                                                        if row_indices_full is not None else int(ix))
                                    except (IndexError, TypeError, ValueError):
                                        seg_rows.append(int(ix))
                                csv_segments.append({
                                    "label": spec["label"],
                                    "indices": list(seg_idx),
                                    "y_true": list(seg_art.get("y_true_test", [])),
                                    "y_pred": list(seg_art.get("y_pred_test", [])),
                                    "context": seg_ctx,
                                    "row_indices": seg_rows,
                                })
                            all_trials_csv_rows.append({
                                "rank": trial_pos + 1,
                                "trial_id": f"R{trial_pos + 1:03d}",
                                "trial_serial": (best_trial.get("extra", {}) or {}).get("trial_serial"),
                                "bank": best_trial.get("bank"),
                                "readout": best_trial.get("readout"),
                                "seed": best_trial.get("seed"),
                                "kpi_mean": winner_row.get("kpi_mean"),
                                "segments": csv_segments,
                            })

                            if not in_keep:
                                continue

                            tile_val_segs = []
                            for spec in validation_segments:
                                tr = spec["trial"]
                                seg_art = tr.get("_artifacts", {}) or {}
                                seg_idx = seg_art.get("test_indices", [])
                                if seg_idx is None or len(seg_idx) == 0:
                                    continue
                                ctx_slice = []
                                ctx_vals = csv_meta.get("context_values")
                                for ix in seg_idx:
                                    try:
                                        ctx_slice.append(ctx_vals[int(ix)] if ctx_vals is not None else None)
                                    except (IndexError, TypeError, ValueError):
                                        ctx_slice.append(None)
                                tile_val_segs.append({
                                    "label": spec["label"],
                                    "y_true": list(seg_art.get("y_true_test", [])),
                                    "y_pred": list(seg_art.get("y_pred_test", [])),
                                    "context": ctx_slice,
                                })
                            tile_val_panel = {
                                "title": "VALIDATION",
                                "subtitle": "",
                                "segments": tile_val_segs,
                            }
                            tile_fc_panel = None
                            fc_idx = best_trial.get("_artifacts", {}).get("forecast_indices")
                            fc_pred = best_trial.get("_artifacts", {}).get("y_pred_forecast")
                            if fc_idx is not None and fc_pred is not None and len(fc_idx) > 0:
                                fc_ctx = []
                                ctx_vals = csv_meta.get("context_values")
                                for ix in fc_idx:
                                    try:
                                        fc_ctx.append(ctx_vals[int(ix)] if ctx_vals is not None else None)
                                    except (IndexError, TypeError, ValueError):
                                        fc_ctx.append(None)
                                yt_fc = best_trial.get("_artifacts", {}).get("y_true_forecast")
                                if yt_fc is None:
                                    yt_fc_list = []
                                else:
                                    yt_fc_list = list(yt_fc)
                                tile_fc_panel = {
                                    "title": "FORECAST",
                                    "subtitle": "",
                                    "segments": [{
                                        "label": "forecast",
                                        "y_true": yt_fc_list,
                                        "y_pred": list(fc_pred),
                                        "context": fc_ctx,
                                    }],
                                }
                            tile_pos = len(collage_tiles)
                            collage_tiles.append({
                                "title": (f"#{trial_pos + 1} {_display_bank(best_trial.get('bank',''))}"
                                          f" / {best_trial.get('readout','')} / seed{best_trial.get('seed','')}"),
                                "subtitle": (f"kpi_mean={winner_row.get('kpi_mean', 0.0):.4f}"
                                             f"  mse={best_trial.get('mse_test', 0.0):.4f}"),
                                "validation_panel": tile_val_panel,
                                "forecast_panel": tile_fc_panel,
                            })
                            if trial_pos in best_idx_set:
                                collage_best_idx.add(tile_pos)
                            elif trial_pos in worst_idx_set:
                                collage_worst_idx.add(tile_pos)

                            exported = export_best_trial(
                                artifact_run_dirs[dataset_path],
                                os.path.splitext(os.path.basename(task_name))[0],
                                best_trial,
                                csv_meta,
                                validation_segments=validation_segments,
                                plot_autoscale=not getattr(args, "no_plot_autoscale", False),
                                rank_idx=trial_pos + 1,
                            )
                            signature_payload = _build_best_trial_signature(
                                args, task_name, best_trial, winner_row, csv_meta
                            )
                            signature_payload.update({
                                "test_csv": exported["test_csv"],
                                "test_png": exported["test_png"],
                                "validation_combined_csv": exported.get("validation_combined_csv"),
                                "forecast_csv": exported.get("forecast_csv"),
                                "forecast_png": exported.get("forecast_png"),
                                "best_rules_json": exported.get("best_rules_json"),
                            })
                            write_json(exported["json"], signature_payload)
                            artifact_index_rows[dataset_path].append({
                                "task": task_name,
                                "dataset_path": csv_meta["path"],
                                "target_col": csv_meta["target_col"],
                                "context_col": csv_meta.get("context_col"),
                                "bank": best_trial["bank"],
                                "readout": best_trial["readout"],
                                "seed": best_trial["seed"],
                                "trial_serial": best_trial.get("extra", {}).get("trial_serial"),
                                "inverted_twin": bool(best_trial.get("extra", {}).get("inverted_twin")),
                                "inverted_from_trial_serial": best_trial.get("extra", {}).get("inverted_from_trial_serial"),
                                "overall": best_trial["overall_kpi"],
                                "overall_mean": winner_row["kpi_mean"],
                                "overall_std": winner_row["kpi_std"],
                                "mse_test": best_trial["mse_test"],
                                "mse_mean": winner_row["mse_test_mean"],
                                "mse_std": winner_row["mse_test_std"],
                                "mae_test": best_trial["mae_test"],
                                "mae_mean": winner_row.get("mae_test_mean"),
                                "r2": best_trial["r2"],
                                "r2_mean": winner_row.get("r2_mean"),
                                "score_kind": best_trial.get("extra", {}).get("score_kind"),
                                "score_label": best_trial.get("extra", {}).get("score_label"),
                                "event_precision": best_trial.get("extra", {}).get("event_precision"),
                                "event_recall": best_trial.get("extra", {}).get("event_recall"),
                                "event_f1": best_trial.get("extra", {}).get("event_f1"),
                                "event_bal_acc": best_trial.get("extra", {}).get("event_bal_acc"),
                                "event_specificity": best_trial.get("extra", {}).get("event_specificity"),
                                "positive_mae": best_trial.get("extra", {}).get("positive_mae"),
                                "model_config": _trial_model_config(best_trial),
                                "split_info": best_trial.get("extra", {}).get("split_info"),
                                "forecast_info": best_trial.get("extra", {}).get("forecast_info"),
                                "score_components": best_trial.get("extra", {}).get("score_components"),
                                "params": json_safe(vars(args)),
                                "rerun_cli": shlex.join([sys.executable] + sys.argv),
                                "test_csv": exported["test_csv"],
                                "test_png": exported["test_png"],
                                "validation_combined_csv": exported.get("validation_combined_csv"),
                                "forecast_csv": exported.get("forecast_csv"),
                                "forecast_png": exported.get("forecast_png"),
                                "best_rules_json": exported.get("best_rules_json"),
                                "signature_json": exported["json"],
                            })
                            print(f"Test export:       {exported['test_csv']}")
                            if exported.get("validation_combined_csv"):
                                print(f"Validation combo:  {exported['validation_combined_csv']}")
                            print(f"Test plot:         {exported['test_png']}")
                            print(f"Best combo sign:   {exported['json']}")
                            if exported.get("forecast_csv"):
                                print(f"Forecast export:   {exported['forecast_csv']}")
                            if exported.get("forecast_png"):
                                print(f"Forecast plot:     {exported['forecast_png']}")
                            if exported.get("best_rules_json"):
                                print(f"LCS rules export:  {exported['best_rules_json']}")
                            try:
                                write_run_index_csv(
                                    artifact_run_dirs[dataset_path],
                                    artifact_index_rows[dataset_path],
                                )
                            except Exception as _flush_err:
                                print(f"[warn] incremental index flush failed: {_flush_err}")

                            if all_trials_csv_rows and not getattr(args, "no_all_trials_csv", False):
                                try:
                                    _partial_task_dir = os.path.join(
                                        artifact_run_dirs[dataset_path], safe_slug(task_label)
                                    )
                                    os.makedirs(_partial_task_dir, exist_ok=True)
                                    _partial_csv = os.path.join(
                                        _partial_task_dir, "all_trials_validation.csv"
                                    )
                                    write_all_trials_validation_csv(
                                        _partial_csv, all_trials_csv_rows, csv_meta=csv_meta
                                    )
                                except Exception as _flush_err:
                                    print(f"[warn] partial all-trials csv flush failed: {_flush_err}")

                        # Export inverted twins that didn't rank into best_trials.
                        # Include anche i twin creati immediatamente durante il progress.
                        all_inverted_twins = [
                            r for r in results
                            if (r.get("extra", {}) or {}).get("inverted_twin")
                        ]
                        if all_inverted_twins:
                            _in_best_ids = {id(bt) for _, bt in best_trials}
                            _unranked_twins = [t for t in all_inverted_twins
                                               if id(t) not in _in_best_ids]
                            if _unranked_twins:
                                print(f"Inverted twins non-ranked: esporto {len(_unranked_twins)} twin...")
                                for _twin in _unranked_twins:
                                    try:
                                        _tw_art = _twin.get("_artifacts", {}) or {}
                                        _tw_idx = list(_tw_art.get("test_indices") or [])
                                        _tw_ctx_vals = csv_meta.get("context_values")
                                        _tw_row_idx = csv_meta.get("row_indices")
                                        _tw_seg_ctx, _tw_seg_rows = [], []
                                        for _ix in _tw_idx:
                                            try:
                                                _tw_seg_ctx.append(
                                                    _tw_ctx_vals[int(_ix)] if _tw_ctx_vals is not None else None)
                                            except (IndexError, TypeError, ValueError):
                                                _tw_seg_ctx.append(None)
                                            try:
                                                _tw_seg_rows.append(
                                                    int(_tw_row_idx[int(_ix)]) if _tw_row_idx is not None else int(_ix))
                                            except (IndexError, TypeError, ValueError):
                                                _tw_seg_rows.append(int(_ix))
                                        _tw_segs = [{
                                            "label": "test",
                                            "indices": _tw_idx,
                                            "y_true": list(_tw_art.get("y_true_test", [])),
                                            "y_pred": list(_tw_art.get("y_pred_test", [])),
                                            "context": _tw_seg_ctx,
                                            "row_indices": _tw_seg_rows,
                                        }] if _tw_idx else []
                                        _tw_exported = export_best_trial(
                                            artifact_run_dirs[dataset_path],
                                            os.path.splitext(os.path.basename(task_name))[0],
                                            _twin,
                                            csv_meta,
                                            plot_autoscale=not getattr(args, "no_plot_autoscale", False),
                                        )
                                        print(f"  INV saved: {_tw_exported['test_csv']}")
                                        all_trials_csv_rows.append({
                                            "rank": None,
                                            "trial_id": (
                                                f"T{int((_twin.get('extra', {}) or {}).get('trial_serial', 0)):05d}_"
                                                f"INV_{safe_slug(_twin.get('bank', ''))}"
                                                f"_seed{_twin.get('seed', '')}"
                                            ),
                                            "trial_serial": (_twin.get("extra", {}) or {}).get("trial_serial"),
                                            "bank": _twin.get("bank"),
                                            "readout": _twin.get("readout"),
                                            "seed": _twin.get("seed"),
                                            "kpi_mean": _twin.get("overall_kpi"),
                                            "segments": _tw_segs,
                                        })
                                    except Exception as _tw_err:
                                        print(f"  [warn] twin export failed: {_tw_err}")

                        if all_trials_csv_rows and not getattr(args, "no_all_trials_csv", False):
                            task_artifact_dir = os.path.join(
                                artifact_run_dirs[dataset_path], safe_slug(task_label)
                            )
                            os.makedirs(task_artifact_dir, exist_ok=True)
                            all_csv_path = os.path.join(
                                task_artifact_dir, "all_trials_validation.csv"
                            )
                            write_all_trials_validation_csv(
                                all_csv_path, all_trials_csv_rows, csv_meta=csv_meta
                            )
                            print(f"All trials CSV:    {all_csv_path}")

                        if collage_tiles and not getattr(args, "no_collage", False):
                            task_artifact_dir = os.path.join(
                                artifact_run_dirs[dataset_path], safe_slug(task_label)
                            )
                            os.makedirs(task_artifact_dir, exist_ok=True)
                            collage_path = os.path.join(
                                task_artifact_dir, "all_trials_collage.png"
                            )
                            write_collage_png(
                                collage_path, collage_tiles,
                                best_indices=collage_best_idx,
                                worst_indices=collage_worst_idx,
                                autoscale=not getattr(args, "no_plot_autoscale", False),
                                columns=2,
                            )
                            print(f"Collage PNG:       {collage_path}")

                        final_eval_export = _export_final_evaluation(
                            artifact_run_dirs[dataset_path],
                            task_name,
                            results,
                            agg,
                            csv_meta,
                            [trial for _, trial in best_trials],
                            metric_profile,
                            args,
                        )
                        if final_eval_export:
                            for phase in ("validation", "forecast"):
                                phase_export = final_eval_export.get(phase)
                                if not phase_export:
                                    continue
                                print(f"Final eval {phase}: {phase_export['csv']}")
                                print(f"Final eval plot:   {phase_export['png']}")
                            if final_eval_export.get("json"):
                                print(f"Final eval sign:   {final_eval_export['json']}")
                        if not getattr(args, "no_export_best_by_bank", False):
                            best_by_bank = _select_best_trials_per_bank_from_agg(results, agg)
                            if best_by_bank:
                                bank_dir = os.path.join(artifact_run_dirs[dataset_path], "best_by_bank")
                                print(f"Best-by-bank dir:  {bank_dir}")
                                bank_index_rows = []
                                for winner_row, best_trial in best_by_bank:
                                    if (forecast_window is not None
                                            and "forecast_indices" not in best_trial.get("_artifacts", {})):
                                        _populate_requested_forecast(
                                            best_trial, csv_meta, forecast_window, args,
                                            deep_preset_cfgs, custom_cfg,
                                            metric_profile=metric_profile,
                                            training_weight_cfg=training_weight_cfg,
                                        )
                                    recent_trial = _select_recent_validation_trial(
                                        results, best_trial["bank"], best_trial["readout"]
                                    )
                                    bank_window_trials = _collect_window_trials_for_combined(
                                        results, best_trial["bank"], best_trial["readout"],
                                        best_trial.get("seed"),
                                    )
                                    bank_segments = []
                                    for wt in bank_window_trials:
                                        if wt["role"] == "backtest":
                                            lbl = f"backtest_w{wt['window_no']}"
                                        elif wt["role"] == "recent_val":
                                            lbl = "recent_validation"
                                        else:
                                            lbl = "test"
                                        bank_segments.append({"label": lbl, "trial": wt["trial"]})
                                    autoscale_flag = not getattr(args, "no_plot_autoscale", False)
                                    exported = export_best_trial(
                                        bank_dir,
                                        os.path.splitext(os.path.basename(task_name))[0],
                                        best_trial,
                                        csv_meta,
                                        validation_segments=bank_segments,
                                        plot_autoscale=autoscale_flag,
                                    )
                                    bank_signature_payload = _build_best_trial_signature(
                                        args, task_name, best_trial, winner_row, csv_meta
                                    )
                                    bank_signature_payload.update({
                                        "test_csv": exported["test_csv"],
                                        "test_png": exported["test_png"],
                                        "validation_combined_csv": exported.get("validation_combined_csv"),
                                        "forecast_csv": exported.get("forecast_csv"),
                                        "forecast_png": exported.get("forecast_png"),
                                        "best_rules_json": exported.get("best_rules_json"),
                                    })
                                    write_json(exported["json"], bank_signature_payload)
                                    recent_exported = {}
                                    if recent_trial is not None:
                                        recent_dir = os.path.join(bank_dir, "recent_validation")
                                        recent_exported = export_best_trial(
                                            recent_dir,
                                            os.path.splitext(os.path.basename(task_name))[0],
                                            recent_trial,
                                            csv_meta,
                                            plot_autoscale=autoscale_flag,
                                        )
                                        recent_signature_payload = _build_best_trial_signature(
                                            args, task_name, recent_trial, winner_row, csv_meta
                                        )
                                        recent_signature_payload.update({
                                            "test_csv": recent_exported["test_csv"],
                                            "test_png": recent_exported["test_png"],
                                            "validation_combined_csv": recent_exported.get("validation_combined_csv"),
                                            "forecast_csv": recent_exported.get("forecast_csv"),
                                            "forecast_png": recent_exported.get("forecast_png"),
                                            "best_rules_json": recent_exported.get("best_rules_json"),
                                        })
                                        write_json(recent_exported["json"], recent_signature_payload)
                                    bank_index_rows.append({
                                        "task": task_name,
                                        "bank": best_trial["bank"],
                                        "readout": best_trial["readout"],
                                        "seed": best_trial["seed"],
                                        "trial_serial": best_trial.get("extra", {}).get("trial_serial"),
                                        "inverted_twin": bool(best_trial.get("extra", {}).get("inverted_twin")),
                                        "inverted_from_trial_serial": best_trial.get("extra", {}).get("inverted_from_trial_serial"),
                                        "overall": best_trial["overall_kpi"],
                                        "overall_mean": winner_row["kpi_mean"],
                                        "score_kind": best_trial.get("extra", {}).get("score_kind"),
                                        "event_precision": best_trial.get("extra", {}).get("event_precision"),
                                        "event_recall": best_trial.get("extra", {}).get("event_recall"),
                                        "event_f1": best_trial.get("extra", {}).get("event_f1"),
                                        "event_bal_acc": best_trial.get("extra", {}).get("event_bal_acc"),
                                        "event_specificity": best_trial.get("extra", {}).get("event_specificity"),
                                        "model_config": _trial_model_config(best_trial),
                                        "test_csv": exported["test_csv"],
                                        "test_png": exported["test_png"],
                                        "forecast_csv": exported.get("forecast_csv"),
                                        "forecast_png": exported.get("forecast_png"),
                                        "best_rules_json": exported.get("best_rules_json"),
                                        "recent_validation_csv": recent_exported.get("test_csv"),
                                        "recent_validation_png": recent_exported.get("test_png"),
                                        "recent_validation_forecast_csv": recent_exported.get("forecast_csv"),
                                        "recent_validation_forecast_png": recent_exported.get("forecast_png"),
                                    })
                                    print("Best-by-bank export:"
                                          f" {_display_bank(best_trial['bank'])}/{best_trial['readout']}"
                                          f" test={exported['test_png']}"
                                          f"{' forecast=' + exported['forecast_png'] if exported.get('forecast_png') else ''}")
                                    if recent_exported:
                                        print("Recent validation export:"
                                              f" {_display_bank(best_trial['bank'])}/{best_trial['readout']}"
                                              f" test={recent_exported['test_png']}"
                                              f"{' forecast=' + recent_exported['forecast_png'] if recent_exported.get('forecast_png') else ''}")
                                write_run_index_csv(bank_dir, bank_index_rows)
            print()
            print_leaderboard(agg)
            if len(tasks) > 1:
                _print_task_eta(idx, len(tasks), started_at)

        if len(task_summaries) > 1:
            print()
            print_task_summary(task_summaries)
        if len(all_results) > 1:
            print()
            print_global_summary(all_results)
        for dataset_path, run_dir in artifact_run_dirs.items():
            index_path = write_run_index_csv(run_dir, artifact_index_rows.get(dataset_path, []))
            artifact_index_paths[dataset_path] = index_path
            print(f"Best trials index: {index_path}")
        if getattr(args, "cmd", "") == "train-max":
            print()
            print("Output finali:")
            print(f"DB risultati: {os.path.abspath(args.db)}")
            if artifact_index_paths:
                for dataset_path, index_path in artifact_index_paths.items():
                    print(f"Best trials list: {index_path}")
    finally:
        conn.close()

    args._artifact_index_paths = dict(artifact_index_paths)
    _run_post_hybrid_artifacts(args, artifact_index_paths)

    auto_levels = max(0, int(getattr(args, "auto_inherit_levels", 0) or 0))
    if auto_levels <= 0 or not artifact_index_paths:
        return
    current_indices = dict(artifact_index_paths)
    for level in range(1, auto_levels + 1):
        if not current_indices:
            break
        next_indices = {}
        parent_dirs = {ds: os.path.dirname(idx_path)
                       for ds, idx_path in current_indices.items()}
        for dataset_path, index_path in list(current_indices.items()):
            print()
            print("=" * 80)
            print(f"Auto-inherit level {level}/{auto_levels}  (subfolder L{level:02d})")
            print(f"Source index: {index_path}")
            print("=" * 80)
            sub_args = copy.deepcopy(args)
            sub_args.inherit = index_path
            sub_args.inherit_from = ""
            sub_args.auto_inherit_levels = 0
            sub_args._inherit_parent_run_dirs = {dataset_path: parent_dirs[dataset_path]}
            sub_args._inherit_level_no = level
            if hasattr(sub_args, "_inherit_trial_filter"):
                delattr(sub_args, "_inherit_trial_filter")
            if hasattr(sub_args, "_inherit_summary"):
                delattr(sub_args, "_inherit_summary")
            cmd_train(sub_args)
            sub_indices = getattr(sub_args, "_artifact_index_paths", {}) or {}
            next_indices.update(sub_indices)
        current_indices = next_indices


def print_leaderboard(agg):
    print("=" * 150)
    if any(r.get("weighted_ranking") for r in agg):
        print("Ranking recency-aware: medie pesate con ranking_weight per finestra")
    print(f"{'#':<3}{'Bank':<18}{'Readout':<20}"
          f"{'MSE mean ± std ↓':<22}{'Overall ↑':<44}"
          f"{'inf μs':<10}{'params':<10}")
    print("-" * 150)
    for i, r in enumerate(agg):
        bank = _display_bank(r["bank"])
        mse = f"{r['mse_test_mean']:.4f} ± {r['mse_test_std']:.4f}"
        overall = _format_overall_detail(r)
        print(f"{i+1:<3}{bank:<18}{r['readout']:<20}"
              f"{mse:<22}{overall:<44}"
              f"{r['inference_us']:<10.1f}{r['n_params']:<10}")
    print("=" * 150)
    if agg:
        w = agg[0]
        bank = _display_bank(w["bank"])
        sig = significance(agg)
        tag = "[SIGNIFICATIVO]" if sig else "[dentro il rumore tra seed]"
        print(f"Vincitore: {bank}/{w['readout']}  Overall={w['kpi_mean']:.4f}  {tag}")
        print(f"Metriche winner: MAE={w['mae_test_mean']:.4f}  R2={w['r2_mean']:.4f}")
        if w.get("target_mode") == "event":
            print("Event metrics winner: "
                  f"P={w.get('event_precision_mean', 0.0):.4f}  "
                  f"R={w.get('event_recall_mean', 0.0):.4f}  "
                  f"F1={w.get('event_f1_mean', 0.0):.4f}  "
                  f"BalAcc={w.get('event_bal_acc_mean', 0.0):.4f}  "
                  f"Spec={w.get('event_specificity_mean', 0.0):.4f}  "
                  f"PosMAE={w.get('positive_mae_mean', 0.0):.4f}")


def print_task_summary(task_summaries):
    print("RIEPILOGO FINALE PER TASK")
    print("=" * 150)
    print(f"{'Task':<18}{'Bank':<18}{'Readout':<20}{'MSE ↓':<18}{'Overall ↑':<44}{'Esito':<24}")
    print("-" * 150)
    for summary in task_summaries:
        winner = summary["winner"]
        bank = _display_bank(winner["bank"])
        outcome = "significativo" if summary["significant"] else "nel rumore"
        print(f"{summary['task']:<18}{bank:<18}{winner['readout']:<20}"
              f"{winner['mse_test_mean']:<18.4f}{_format_overall_detail(winner):<44}{outcome:<24}")
    print("=" * 150)


def print_global_summary(all_results):
    def _speed_adj(score, inf_us):
        # composito velocita': score * 100 / (100 + inf_us). 100us = -50%.
        return float(score) * 100.0 / (100.0 + max(0.0, float(inf_us or 0.0)))

    print("RANKING GLOBALE CROSS-TASK (BANK + READOUT)")
    print("=" * 170)
    global_agg = _aggregate_by_bank_readout(all_results)
    print(f"{'#':<3}{'Bank':<18}{'Readout':<20}{'Overall ↑':<44}{'MSE ↓':<10}"
          f"{'inf μs':<10}{'params':<10}{'KPI/v ↑':<10}{'Task':<6}{'Run':<6}")
    print("-" * 170)
    for i, r in enumerate(global_agg, start=1):
        bank = _display_bank(r["bank"])
        kpi_v = _speed_adj(r.get("kpi_mean", 0.0), r.get("inference_us", 0.0))
        print(f"{i:<3}{bank:<18}{r['readout']:<20}"
              f"{_format_overall_detail(r):<44}{r['mse_test_mean']:<10.4f}"
              f"{r.get('inference_us', 0.0):<10.1f}{r.get('n_params', 0):<10}"
              f"{kpi_v:<10.4f}"
              f"{r['n_tasks']:<6}{r['n_runs']:<6}")
    print("=" * 170)

    print("RANKING GLOBALE CROSS-BANK")
    print("=" * 170)
    bank_agg = _aggregate_by_bank(all_results)
    print(f"{'#':<3}{'Bank':<18}{'Overall ↑':<12}{'MSE ↓':<10}"
          f"{'inf μs':<10}{'train s':<10}{'params':<10}{'KPI/v ↑':<10}"
          f"{'Task':<6}{'Run':<6}{'Readout':<8}")
    print("-" * 170)
    for i, r in enumerate(bank_agg, start=1):
        bank = _display_bank(r["bank"])
        kpi_v = _speed_adj(r.get("kpi_mean", 0.0), r.get("inference_us", 0.0))
        print(f"{i:<3}{bank:<18}{r['kpi_mean']:<12.4f}{r['mse_test_mean']:<10.4f}"
              f"{r.get('inference_us', 0.0):<10.1f}{r.get('train_s', 0.0):<10.3f}"
              f"{r.get('n_params', 0):<10}{kpi_v:<10.4f}"
              f"{r['n_tasks']:<6}{r['n_runs']:<6}{r['readouts']:<8}")
    print("=" * 170)

    # Riferimento: mostra backends interpretabili / hybrid in evidenza per il confronto
    # accuratezza vs velocita'.
    lcs_hybrid = [r for r in bank_agg
                  if r["bank"] in ("__lcs__", "__hybrid__", "__kan__", "__kan_hybrid__")]
    if lcs_hybrid:
        print()
        print("RIFERIMENTO INTERPRETABILE / HYBRID (per giudicare il compromesso "
              "accuratezza vs velocita')")
        print("-" * 170)
        for r in lcs_hybrid:
            bank = _display_bank(r["bank"])
            kpi_v = _speed_adj(r.get("kpi_mean", 0.0), r.get("inference_us", 0.0))
            print(f"   {bank:<18}Overall={r['kpi_mean']:.4f}  "
                  f"inf={r.get('inference_us', 0.0):.1f}μs  "
                  f"params={r.get('n_params', 0)}  "
                  f"KPI/velocita'={kpi_v:.4f}")

    if bank_agg:
        winner_score = bank_agg[0]
        bank_w_score = _display_bank(winner_score["bank"])
        print()
        print(f"Best bank by SCORE:  {bank_w_score}  "
              f"Overall={winner_score['kpi_mean']:.4f}  "
              f"inf={winner_score.get('inference_us', 0.0):.1f}μs  "
              f"params={winner_score.get('n_params', 0)}")
        winner_kpi = max(bank_agg,
                         key=lambda r: _speed_adj(r.get("kpi_mean", 0.0),
                                                  r.get("inference_us", 0.0)))
        bank_w_kpi = _display_bank(winner_kpi["bank"])
        kpi_v = _speed_adj(winner_kpi.get("kpi_mean", 0.0),
                           winner_kpi.get("inference_us", 0.0))
        print(f"Best bank by KPI/v:  {bank_w_kpi}  "
              f"KPI/velocita'={kpi_v:.4f}  "
              f"(Overall={winner_kpi['kpi_mean']:.4f}, "
              f"inf={winner_kpi.get('inference_us', 0.0):.1f}μs, "
              f"params={winner_kpi.get('n_params', 0)})")


def cmd_top(args):
    conn = init_db(args.db)
    rows = query_top(conn, task_name=args.task, limit=args.limit)
    conn.close()
    print(f"{'Bank':<18}{'Readout':<20}{'Task':<18}{'MSE ↓':<12}{'Overall ↑':<12}{'N':<5}")
    print("-" * 85)
    for bank, readout, task, mse, kpi, n in rows:
        bank_d = _display_bank(bank)
        print(f"{bank_d:<18}{readout:<20}{task:<18}{mse:<12.4f}{kpi:<12.4f}{n:<5}")


def cmd_train_max(args):
    csv_task_mode = bool(args.task and is_csv_task(args.task))
    if not csv_task_mode:
        args.task = ",".join(TASKS.keys())
    args.banks = ",".join(BANKS.keys())
    args.readouts = ",".join(READOUTS.keys())
    args.deep_presets = ",".join(DEEP_PRESETS.keys())
    if args.enable_lcs_in_max:
        args.lcs_presets = ",".join(LCS_PRESETS.keys())
        args.all_lcs_presets = True
    else:
        args.lcs_presets = ""
        args.all_lcs_presets = False
    if getattr(args, "enable_kan_in_max", False):
        args.enable_kan = True
        args.kan_presets = ",".join(KAN_PRESETS.keys())
        args.all_kan_presets = True
    else:
        args.all_kan_presets = False
    args.all_tasks = not csv_task_mode
    args.all_banks = True
    args.all_readouts = True
    args.all_deep_presets = True
    cmd_train(args)


def _add_preset_arg(parser):
    """Argomento --preset documentato. L'espansione vera avviene prima di
    parse_args() in main(); qui lo registriamo solo per --help e per non
    far fallire il parsing nei rari casi in cui resti residuo."""
    parser.add_argument("--preset", default=None,
                        help=("preset di flag predefiniti (componibili: --preset N1,N2). "
                              "Vedi 'python cli.py train --list-presets' per la lista. "
                              "I flag espliciti dopo --preset sovrascrivono i preset."))
    parser.add_argument("--list-presets", action="store_true",
                        help="elenca i CLI preset disponibili e termina")


def _add_train_args(parser, require_task=True):
    if require_task:
        parser.add_argument("--task", required=True,
                            help="task singolo o lista CSV, es: friedman1,poly3")
    else:
        parser.add_argument("--task", default="",
                            help="opzionale: override task CSV; default = tutti")
        parser.add_argument("--all-tasks", action="store_true",
                            help="usa tutti i task disponibili")
        parser.add_argument("--all-banks", action="store_true",
                            help="usa tutti i feature bank disponibili")
        parser.add_argument("--all-readouts", action="store_true",
                            help="usa tutti i readout disponibili")
        parser.add_argument("--all-deep-presets", action="store_true",
                            help="usa tutti i preset deep end-to-end disponibili")
        parser.add_argument("--all-lcs-presets", action="store_true",
                            help=argparse.SUPPRESS)

    parser.add_argument("--banks", default="")
    parser.add_argument("--no-banks", action="store_true",
                        help="non esegue trial bank+readout puri; utile per LCS/hybrid/deep mirati")
    parser.add_argument("--readouts", default="ridge")
    parser.add_argument("--seeds", default="5",
                        help=("interpretazione flessibile: '5' = 5 seed [0..4]; "
                              "'4:3' = 3 seed a partire dalla base 4 [4,5,6]; "
                              "'1,2,9' = lista esatta; '@4' o 'seed:4' = base 4 con --seed-count seed derivati"))
    parser.add_argument("--seed-count", type=int, default=None,
                        help="con --seeds '@4' o 'seed:N', numero di seed derivati (default: 5)")
    parser.add_argument("--jobs", type=int, default=1,
                        help=("numero di processi paralleli per i seed. 1 = sequenziale; "
                              "0 o valore negativo = tutti i core disponibili. Utile per LCS/hybrid CPU-bound"))
    parser.add_argument("--n-train", type=int, default=500)
    parser.add_argument("--n-test", type=int, default=500)
    parser.add_argument("--noise", type=float, default=0.0)
    parser.add_argument("--db", default="results.db")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--inherit", "--inherit-from", dest="inherit", default="",
                        help=("path a best_trials_index.csv o alla sua directory: eredita "
                              "parametri e limita il run ai migliori trial del run precedente"))
    parser.add_argument("--best", type=int, default=5,
                        help="con --inherit, numero di best combinazioni da riprovare")
    parser.add_argument("--shape-weight", type=float, default=0.6,
                        help=("peso di shape_overall (picchi+depressioni topologiche) nello "
                              "Overall: 0=ignora, 1=solo shape. Default 0.6"))
    parser.add_argument("--no-plot-autoscale", action="store_true",
                        help=("disattiva il rescale automatico della curva predicted sul "
                              "min-max della actual nel grafico combinato"))
    parser.add_argument("--inherit-best-bank", action="store_true",
                        help=("con --inherit, aggiunge anche il migliore per ciascun bank/famiglia "
                              "oltre ai top-N (default: off, restano solo i top-N esatti)"))
    parser.add_argument("--inherit-no-best-bank", action="store_true",
                        help="alias storico, ora ridondante: il default e' gia' senza best-bank")
    parser.add_argument("--target_cols_list", default="",
                        help="CSV mode: target column name, o lista CSV. Default = ultima colonna")
    parser.add_argument("--skip_cols_list", default="",
                        help="CSV mode: colonne da escludere dalle feature, separate da virgole")
    parser.add_argument("--feature-selection-k-best", type=int, default=None,
                        help="seleziona le migliori K feature basandosi su discrete mutual information")
    parser.add_argument("--feature-selection-threshold", type=float, default=None,
                        help="seleziona le feature con mutual information >= soglia")
    parser.add_argument("--feature-selection-percentile", type=float, default=None,
                        help="seleziona la frazione percentuale migliore di feature (es. 0.15 per il top 15%%)")
    parser.add_argument("--feature-selection-min-features", type=int, default=None,
                        help="numero minimo elastico di feature da mantenere (fallback se troppe poche passano la soglia)")
    parser.add_argument("--feature-selection-max-features", type=int, default=None,
                        help="numero massimo elastico di feature da mantenere (cap se troppe passano la soglia)")
    parser.add_argument("--w-mse", type=float, default=0.7)
    parser.add_argument("--w-speed", type=float, default=0.2)
    parser.add_argument("--w-params", type=float, default=0.1)
    parser.add_argument("--metric-mode", default="auto", choices=["auto", "regression", "event"],
                        help="scelta automatica o forzata delle metriche/ranking")
    parser.add_argument("--metric-target-threshold", type=float, default=None,
                        help="soglia evento per metriche target-aware; default auto dal target")
    parser.add_argument("--metric-prediction-threshold", type=float, default=0.5,
                        help=("soglia per trasformare predizioni continue in eventi; "
                              "default 0.5 per evitare che rumore positivo >0.1 conti come evento"))
    parser.add_argument("--event-score-mode", default="isolation",
                        choices=["isolation", "legacy", "additive"],
                        help=("scoring eventi: isolation premia precision/specificita' e segnali puliti; "
                              "legacy/additive usa la vecchia miscela recall/fit"))
    parser.add_argument("--no-final-evaluation", action="store_true",
                        help=("non esportare il PNG/CSV finale overall rank-weighted "
                              "(default: attivo per CSV train/train-max/inherit)"))
    parser.add_argument("--final-eval-rank-power", type=float, default=1.0,
                        help=("potenza del peso di rank nella final evaluation: "
                              "1.0 = proporzionale al rank inverso, 0 = tutti uguali"))
    parser.add_argument("--final-eval-low-threshold", type=float, default=1e-9,
                        help=("soglia molto bassa sul totale stimato del trial: sotto questa "
                              "soglia il trial entra in reverse mode se la negative inertia e' attiva"))
    parser.add_argument("--no-final-eval-negative-inertia", action="store_true",
                        help="disattiva il reverse mode automatico per trial quasi sempre negativi")
    parser.add_argument("--final-eval-negative-weight", type=float, default=3.0,
                        help="moltiplicatore di peso per i trial usati in reverse mode")
    parser.add_argument("--no-final-eval-shape-filter", action="store_true",
                        help=("disattiva il filtro shape-aware sul final evaluation. "
                              "Quando attivo (default): trial con 0 picchi predetti in validation "
                              "vengono esclusi; i top per shape_overall sono inclusi normalmente; "
                              "i bottom (con picchi presenti) sono usati invertiti via negative_weight; "
                              "i mediocri sono esclusi."))
    parser.add_argument("--final-eval-best-fraction", type=float, default=0.25,
                        help=("frazione di trial top per shape_overall inclusi nel final eval "
                              "quando il filtro shape e' attivo (default 0.25)"))
    parser.add_argument("--final-eval-worst-fraction", type=float, default=0.10,
                        help=("frazione di trial bottom per shape_overall (con almeno un picco "
                              "predetto) usati invertiti nel final eval (default 0.10)"))
    parser.add_argument("--final-eval-shape-power", type=float, default=0.0,
                        help=("esponente per pesare i trial inclusi in base al loro shape_overall: "
                              "weight *= shape_overall**power (solo gruppo 'include', non sui invertiti). "
                              "0 = disattivato/peso uniforme entro il gruppo (default), "
                              "1 = peso lineare in shape_overall, "
                              "2+ = enfasi crescente sui top per shape. "
                              "Esempio: --final-eval-shape-power 1.5 fa contare il top-1 molto piu' "
                              "del rank piu' basso entro il top-fraction."))
    parser.add_argument("--readability-weight", type=float, default=0.0,
                        help=("peso della componente 'leggibilita' della curva predetta "
                              "nel composito di event mode. Misura quanto la pred e' "
                              "silenziosa nelle zone calme (quiet_fidelity) e quanto i "
                              "picchi svettano sul fondo (peak_separation_score). "
                              "Default 0.0 = comportamento legacy. Valori sani: 0.25-0.40. "
                              "Esempio: 0.35 -> score = 0.65*legacy + 0.35*readability."))
    parser.add_argument("--readability-floor", type=float, default=0.0,
                        help=("soglia di leggibilita' minima sotto la quale lo score "
                              "viene penalizzato moltiplicando per readability/floor. "
                              "Default 0.0 = nessuna penalita'. Esempio: 0.3 -> i trial "
                              "con readability<0.3 vedono lo score scalato verso 0. "
                              "Penalizzazione soft (mai esclusione) per preservare "
                              "tracciabilita' nei dati per pubblicazione."))
    parser.add_argument("--keep-best", type=int, default=0,
                        help=("limita gli export per-trial (CSV+PNG individuali) ai top-N "
                              "trial per ranking. 0 = nessun filtro (default). LCS/hybrid "
                              "sono sempre esportati come riferimento."))
    parser.add_argument("--keep-worst", type=int, default=0,
                        help=("aggiunge agli export per-trial i bottom-N trial per ranking. "
                              "0 = nessuno (default). Utile per ispezionare i trial peggiori."))
    parser.add_argument("--no-collage", action="store_true",
                        help=("disattiva la generazione del collage PNG complessivo "
                              "(2 colonne, bordo verde sui best, bordo rosso sui worst)."))
    parser.add_argument("--no-all-trials-csv", action="store_true",
                        help="disattiva la scrittura di all_trials_validation.csv accodato.")
    parser.add_argument("--invert-twin-enabled", dest="invert_twin_enabled",
                        action="store_true", default=True,
                        help=("genera 'twin invertiti' per i trial peggiori (per shape_overall) "
                              "che hanno varianza nei pred. Il twin entra nel ranking come "
                              "bank<NOME>__INV con metriche ricalcolate. Default ON."))
    parser.add_argument("--no-invert-twin", dest="invert_twin_enabled",
                        action="store_false",
                        help="disattiva la generazione di twin invertiti.")
    parser.add_argument("--invert-twin-min-std", type=float, default=1e-6,
                        help=("soglia minima di std(y_pred_test) sotto la quale un trial e' "
                              "considerato 'piatto' e quindi NON viene invertito. Default 1e-6."))
    parser.add_argument("--invert-twin-immediate-threshold", type=float, default=0.0,
                        help=("se >0, appena un trial ha Overall <= soglia e predizione non piatta "
                              "con almeno un picco, genera subito il twin invertito e lo scrive in "
                              "incremental_trials.csv. 0 = disattivato (default)."))
    parser.add_argument("--invert-twin-fraction", type=float, default=None,
                        help=("frazione di trial bottom (per shape_overall) candidati a twin. "
                              "Default = --final-eval-worst-fraction."))
    parser.add_argument("--auto-inherit-levels", type=int, default=0,
                        help=("numero di passate di inheritance automatiche da eseguire dopo "
                              "il run principale (train o train-max). 0 = disattivato (default). "
                              "1 = una passata di inheritance L1 sul best_trials_index appena "
                              "prodotto. N = N passate ricorsive: ogni livello eredita dal "
                              "best_trials_index del livello precedente. Esempio: "
                              "--auto-inherit-levels 1 (la modalita' tipica)."))
    parser.add_argument("--post-hybrid-artifacts", action="store_true",
                        help=("dopo il run principale, esegue automaticamente "
                              "post_hybrid_artifacts.py sul best_trials_index prodotto. "
                              "Alternativa leggera ad auto-inherit quando vuoi fondere artifact "
                              "gia' esportati senza rifare sublevel."))
    parser.add_argument("--post-hybrid-mode", default="artifacts",
                        choices=["artifacts", "smart", "both"],
                        help=("post-hybrid: quale runner finale invocare. artifacts = proposta/classico, "
                              "smart = selezione smart finale, both = esegue entrambi."))
    parser.add_argument("--post-hybrid-proposal-only", action="store_true",
                        help="post-hybrid: scrive solo le coppie candidate, senza generare la fusione finale")
    parser.add_argument("--post-hybrid-out-dir", default="",
                        help=("post-hybrid: directory output; default = post_hybrid_checks o "
                              "post_hybrid_checks_smart accanto al best_trials_index"))
    parser.add_argument("--post-hybrid-logic", default="and",
                        choices=["and", "or", "weighted", "sure", "conservative"],
                        help="post-hybrid: logica di fusione")
    parser.add_argument("--post-hybrid-normalize", default="auto",
                        choices=["auto", "none", "binary", "minmax"],
                        help="post-hybrid: normalizzazione degli score sorgente")
    parser.add_argument("--post-hybrid-score-column", default="predicted",
                        choices=["predicted", "pred_recalibrated"],
                        help="post-hybrid: colonna score da leggere dai CSV artifact")
    parser.add_argument("--post-hybrid-alpha", type=float, default=0.5,
                        help="post-hybrid: peso del primo artifact per logic=weighted")
    parser.add_argument("--post-hybrid-threshold", type=float, default=0.5,
                        help="post-hybrid: soglia finale iniziale, prima della calibrazione")
    parser.add_argument("--post-hybrid-calibrate", default="validation",
                        choices=["none", "validation"],
                        help="post-hybrid: calibrazione soglie sulla validation allineata")
    parser.add_argument("--post-hybrid-calibrate-metric", default="f1",
                        choices=["f1", "f05", "bal_acc", "precision", "recall"],
                        help="post-hybrid: metrica da massimizzare in calibrazione")
    parser.add_argument("--post-hybrid-min-recall", type=float, default=0.0,
                        help="post-hybrid: recall minima richiesta durante la calibrazione")
    parser.add_argument("--post-hybrid-top-candidates", type=int, default=30,
                        help="post-hybrid: massimo numero di artifact candidati da simulare")
    parser.add_argument("--post-hybrid-top-pairs", type=int, default=20,
                        help="post-hybrid: numero di coppie candidate da salvare")
    parser.add_argument("--post-hybrid-max-rules", type=int, default=20,
                        help="post-hybrid: massimo numero di regole positive LCS da derivare/esporre")
    parser.add_argument("--post-hybrid-max-peaks", type=int, default=1,
                        help="smart mode: massimo numero di picchi accettati nel forecast quality/filter")
    parser.add_argument("--post-hybrid-final-peak-max", type=int, default=0,
                        help="smart mode: massimo numero di picchi nel merge finale shape/peak; 0 = usa max-peaks")
    parser.add_argument("--post-hybrid-peak-and", action="store_true", default=False,
                        help="smart mode: usa overlap di picchi locali per la logica 'and' nel forecast "
                             "invece di threshold-AND punto per punto.")
    parser.add_argument("--post-hybrid-peak-window", type=int, default=1,
                        help="smart mode peak-and: finestra massima (cascata 0→N). "
                             "Prova window=0 poi 1...N; usa il primo con overlap. "
                             "Se nessuno → fallback automatico a or. Default=1.")
    parser.add_argument("--post-hybrid-peak-floor", type=float, default=0.30,
                        help="smart mode peak-and: frazione del proprio range [0,1] sotto cui un punto non è picco "
                             "(self-normalization: 0.30 = top 70%% della variazione del segnale). Default=0.30.")
    parser.add_argument("--post-hybrid-peak-max", type=int, default=1,
                        help="smart mode peak-and: numero massimo di picchi in output (AND o OR fallback). "
                             "Rank per self-norm within-signal. Default=1.")
    parser.add_argument("--post-hybrid-forecast-guard", default="auto",
                        choices=["auto", "off"],
                        help="post-hybrid: guard anti-degenerazione forecast durante la proposta coppie")
    parser.add_argument("--forecast-common-window", action="store_true",
                        help=("dopo smart fusion, deduce la finestra forecast comune tra il forecast "
                              "smart finale e i CSV passati con --forecast-common-source"))
    parser.add_argument("--forecast-common-source", dest="forecast_common_sources",
                        action="append", default=[],
                        help="CSV forecast sorgente per common window; ripetibile o separato da virgole")
    parser.add_argument("--forecast-common-out-dir", default="",
                        help="directory output common window; default = smart_out_dir/common_detected_window")
    parser.add_argument("--forecast-common-score-column", default="auto",
                        help="colonna score forecast da usare; auto cerca predicted/pred/pred_recalibrated")
    parser.add_argument("--forecast-common-threshold", type=float, default=0.5,
                        help="soglia usata per consensus_count nel CSV common window")
    parser.add_argument("--always-include", default=_ALWAYS_INCLUDE_DEFAULT,
                        help=("lista comma-separated di banks da includere SEMPRE in ogni step "
                              "di inheritance (manuale o auto-multilevel), oltre ai top-best per "
                              "score. Token speciali: 'lcs' -> __lcs__, 'lcs_hybrid' (o 'hybrid') "
                              "-> __hybrid__, 'kan' -> __kan__, 'kan_hybrid' -> __kan_hybrid__. "
                              "Default: '" + _ALWAYS_INCLUDE_DEFAULT + "'. "
                              "Vale anche per i livelli auto successivi al primo."))
    parser.add_argument("--no-always-include", action="store_true",
                        help="disattiva il meccanismo --always-include (nessun bank forzato)")
    parser.add_argument("--target-window-threshold", type=float, default=None,
                        help="CSV benchmark: target >= soglia conta come evento; default 0 se usi event-count")
    parser.add_argument("--target-window-event-count", type=int, default=0,
                        help="CSV benchmark: quanti eventi includere nella finestra target/test")
    parser.add_argument("--target-window-event-start", type=int, default=None,
                        help="CSV benchmark mobile: start evento, es. -5 = quinto evento partendo dall'ultimo")
    parser.add_argument("--target-window-pre-records", type=int, default=0,
                        help="CSV benchmark: quanti record includere prima dell'evento start")
    parser.add_argument("--target-window-post-records", type=int, default=0,
                        help="CSV benchmark mobile: quanti record includere dopo l'evento end")
    parser.add_argument("--suppress-autodate-clipping", action="store_true",
                        help="disattiva il clipping automatico della target window a data/ora corrente")
    parser.add_argument("--force-autoclip", action="store_true",
                        help="forza il clipping automatico della target window a data/ora corrente")
    parser.add_argument("--no-autoclip", action="store_true",
                        help="disattiva sempre il clipping automatico della target window")
    parser.add_argument("--time-series", default="auto", choices=["auto", "on", "off"],
                        help=("policy anti-leak temporale: auto rileva date monotone, on forza,"
                              " off disattiva"))
    parser.add_argument("--allow-train-after-test", action="store_true",
                        help=("permette righe di train dopo test/forecast; stampa comunque un warning"
                              " per possibile leak temporale"))
    parser.add_argument("--train-start-date", default="",
                        help="CSV temporali: data iniziale opzionale del dataset effettivo; se omessa usa l'inizio del file")
    parser.add_argument("--train-end-date", default="",
                        help="CSV temporali: data finale opzionale del dataset effettivo; se omessa usa la fine del file")
    parser.add_argument("--forecast-start-date", default="",
                        help="CSV artifacts: esporta anche una previsione sul range date a partire da questa data")
    parser.add_argument("--forecast-end-date", default="",
                        help="CSV artifacts: fine opzionale del range forecast; se omessa usa fino alla fine del dataset")
    parser.add_argument("--forecast-trainset", default="train+test",
                        choices=["train+test", "train2test", "train2forecast"],
                        help=("quando chiedi un forecast rifitta il best model con: "
                              "train+test = usa le finestre originali train e test prima del forecast; "
                              "train2test = range continuo dalla prima riga train all'ultima riga test; "
                              "train2forecast = range continuo dalla prima riga train all'ultima riga prima del forecast"))
    parser.add_argument("--no-export-best-by-bank", action="store_true",
                        help="non creare la sottocartella artifact best_by_bank")
    parser.add_argument("--backtest-event-windows", action="store_true",
                        help="CSV: valuta su molte finestre evento storiche walk-forward")
    parser.add_argument("--backtest-event-count", type=int, default=0,
                        help="eventi per finestra backtest; default = target-window-event-count o 1")
    parser.add_argument("--backtest-pre-records", type=int, default=-1,
                        help="record prima della finestra evento; default = target-window-pre-records")
    parser.add_argument("--backtest-post-records", type=int, default=-1,
                        help="record dopo la finestra evento; default = target-window-post-records")
    parser.add_argument("--backtest-step-events", type=int, default=1,
                        help=("passo in eventi tra finestre backtest; 1 permette overlap "
                              "quando event-count > 1"))
    parser.add_argument("--backtest-min-train-events", type=int, default=4,
                        help=("numero minimo di eventi storici prima di ogni finestra backtest; "
                              "abbassalo se vuoi includere finestre piu' recenti con pochi eventi"))
    parser.add_argument("--backtest-max-windows", type=int, default=0,
                        help="limita alle ultime N finestre backtest; 0 = tutte")
    parser.add_argument("--backtest-include-final-window", action="store_true",
                        help="include anche la final target window nel backtest")
    parser.add_argument("--backtest-recency-weight", default="none",
                        choices=["none", "linear", "exp"],
                        help="pesa le finestre backtest piu' recenti nel ranking aggregato")
    parser.add_argument("--backtest-recency-strength", type=float, default=1.0,
                        help="intensita' del peso recency: linear=1+s*t, exp=e^(s*t)")
    parser.add_argument("--recent-validation-window", action="store_true",
                        help="aggiunge una validation recente uniforme prima del forecast")
    parser.add_argument("--recent-validation-event-count", type=int, default=0,
                        help="eventi nella validation recente; default = target/backtest event-count")
    parser.add_argument("--recent-validation-pre-records", type=int, default=-1,
                        help="record prima della validation recente; default = target pre-records")
    parser.add_argument("--recent-validation-post-records", type=int, default=-1,
                        help="record dopo la validation recente; default = target post-records")
    parser.add_argument("--recent-validation-min-train-events", type=int, default=-1,
                        help="min eventi prima della validation recente; default = backtest-min-train-events")
    parser.add_argument("--recent-validation-weight", type=float, default=2.0,
                        help="peso della validation recente nel ranking aggregato")
    parser.add_argument("--recent-validation-skip-if-unavailable", action="store_true",
                        help=("se la recent validation non ha eventi compatibili con i vincoli "
                              "(es. validation-max-lookback), non abortisce il run e prosegue "
                              "senza quella validation. Utile per controlli reverse/random."))
    parser.add_argument("--recent-validation-random-negatives", type=int, default=0,
                        help=("aggiunge N record non-evento scelti casualmente tra gli eventi "
                              "della recent validation isolata, per testare anche falsi positivi"))
    parser.add_argument("--recent-validation-random-seed", type=int, default=8675309,
                        help="seed riproducibile per --recent-validation-random-negatives")
    parser.add_argument("--validation-max-lookback-records", type=int, default=0,
                        help=("limita backtest/recent validation agli ultimi N record prima del "
                              "forecast/target anchor; se event_count e' troppo largo lo riduce "
                              "automaticamente fino a 1. 0 = disattivato"))
    parser.add_argument("--no-train-sample-weighting", action="store_true",
                        help="disattiva i pesi di training recency/event-based")
    parser.add_argument("--train-recency-weight", default="exp",
                        choices=["none", "linear", "exp"],
                        help="peso campioni recenti durante il training")
    parser.add_argument("--train-recency-strength", type=float, default=1.0,
                        help="intensita' recency nel training: linear=1+s*t, exp=e^(s*t)")
    parser.add_argument("--train-event-weight", default="auto",
                        help="peso eventi positivi nel training: auto, none, oppure numero")
    parser.add_argument("--train-max-event-weight", type=float, default=8.0,
                        help="cap per --train-event-weight auto")

    parser.add_argument("--deep-presets", default="",
                        help="comma-separated tra: tiny,small,default,deep,wide")
    parser.add_argument("--deep-preset-configs-json", default="",
                        help="JSON con preset DeepConfig aggiuntivi usabili da --deep-presets e hybrid deep")
    parser.add_argument("--deep-custom", action="store_true",
                        help="attiva DeepNet custom con i flag sotto")
    parser.add_argument("--deep-hidden", default="",
                        help="es: 128,64,32 (vuoto=auto)")
    parser.add_argument("--deep-activation", default="gelu",
                        choices=list(ACTIVATIONS.keys()) if ACTIVATIONS else ["gelu"])
    parser.add_argument("--deep-dropout", type=float, default=0.0)
    parser.add_argument("--deep-batch-norm", action="store_true")
    parser.add_argument("--max-iter", type=int, default=None,
                        help=("override unico del numero massimo di iterazioni/epoche "
                              "per modelli iterativi (mlp sklearn, readout torch, deep preset/custom)"))
    parser.add_argument("--deep-epochs", type=int, default=200)
    parser.add_argument("--deep-batch-size", type=int, default=64)
    parser.add_argument("--deep-lr", type=float, default=1e-3)
    parser.add_argument("--deep-weight-decay", type=float, default=1e-4)
    parser.add_argument("--deep-device", default="auto", choices=["auto", "cpu", "cuda", "xpu"])
    parser.add_argument("--deep-validation-metric", default="mse",
                        choices=["mse", "f1", "event_composite"],
                        help="metrica validation/early-stopping DeepNet")
    parser.add_argument("--deep-validation-threshold", type=float, default=None,
                        help=("soglia per validation DeepNet event-based; default = deep-val/metric/"
                              "target/lcs threshold, fallback 0.5"))
    parser.add_argument("--deep-target-window-threshold", dest="target_window_threshold",
                        type=float, help=argparse.SUPPRESS)
    parser.add_argument("--deep-target-window-event-count", dest="target_window_event_count",
                        type=int, help=argparse.SUPPRESS)
    parser.add_argument("--deep-target-window-event-start", dest="target_window_event_start",
                        type=int, help=argparse.SUPPRESS)
    parser.add_argument("--deep-target-window-pre-records", dest="target_window_pre_records",
                        type=int, help=argparse.SUPPRESS)
    parser.add_argument("--deep-target-window-post-records", dest="target_window_post_records",
                        type=int, help=argparse.SUPPRESS)
    parser.add_argument("--deep-val-target-threshold", dest="deep_val_target_threshold",
                        type=float, default=None,
                        help="validation DeepNet: soglia evento; default = target/lcs threshold")
    parser.add_argument("--deep-val-event-count", dest="deep_val_event_count",
                        type=int, default=0,
                        help="validation DeepNet: ultimi N eventi dentro il train; default = lcs-val-event-count")
    parser.add_argument("--deep-val-pre-records", dest="deep_val_pre_records",
                        type=int, default=-1,
                        help="validation DeepNet event-window: record prima; default = lcs-val-pre-records")
    parser.add_argument("--deep-val-post-records", dest="deep_val_post_records",
                        type=int, default=-1,
                        help="validation DeepNet event-window: record dopo; default = lcs-val-post-records")

    parser.add_argument("--enable-kan", action="store_true",
                        help="abilita KAN come backend/readout interpretabile sperimentale")
    parser.add_argument("--kan-presets", default="tiny",
                        help="preset KAN separati da virgola, es: tiny,small")
    parser.add_argument("--all-kan-presets", action="store_true",
                        help="usa tutti i preset KAN disponibili")
    parser.add_argument("--hybrid-kan", action="store_true",
                        help="crea trial ibridi KAN + bank/deep analoghi agli hybrid LCS")
    parser.add_argument("--enable-kan-in-max", action="store_true",
                        help="train-max: include anche KAN readout/backend")
    parser.add_argument("--kan-device", default="cpu", choices=["cpu", "cuda", "xpu", "auto"],
                        help="device KAN; default cpu per stabilita' nei run paralleli; xpu usa Intel GPU")
    parser.add_argument("--kan-quiet", action="store_true",
                        help=("sopprime il refresh/progress per-epoca interno di pykan anche con --verbose; "
                              "resta visibile il progresso per-trial del CLI. Utile per log lunghi."))

    parser.add_argument("--lcs-presets", default="",
                        help="comma-separated tra: tiny,default,large,wide")
    parser.add_argument("--lcs-custom", action="store_true",
                        help="attiva UCS custom con i flag sotto")
    parser.add_argument("--lcs-population-size", type=int, default=500)
    parser.add_argument("--lcs-epochs", type=int, default=100)
    parser.add_argument("--lcs-ga-frequency", type=int, default=50)
    parser.add_argument("--lcs-mutation-rate", type=float, default=0.04)
    parser.add_argument("--lcs-crossover-rate", type=float, default=0.8)
    parser.add_argument("--lcs-wildcard-prob", type=float, default=0.5)
    parser.add_argument("--lcs-positive-wildcard-prob", type=float, default=None,
                        help="wildcard prob solo per covering di eventi positivi; default = --lcs-wildcard-prob")
    parser.add_argument("--lcs-positive-covering-multiplier", type=int, default=1,
                        help="quante regole candidate creare quando si copre un evento positivo")
    parser.add_argument("--lcs-tournament-size", type=int, default=5)
    parser.add_argument("--lcs-seed", type=int, default=0)
    parser.add_argument("--lcs-binary-threshold", type=float, default=None,
                        help="soglia di binarizzazione UCS; default target-window-threshold se fornito, altrimenti 0.1")
    parser.add_argument("--lcs-validation-split", type=float, default=0.2,
                        help="quota train usata come validation interna LCS per restore best")
    parser.add_argument("--lcs-val-event-count", type=int, default=0,
                        help="validation LCS: ultimi N eventi dentro il train; 0 usa validation-split")
    parser.add_argument("--lcs-val-event-start", type=int, default=None,
                        help="validation LCS mobile: start evento, es. -2 = penultimo evento disponibile nel train")
    parser.add_argument("--lcs-val-pre-records", type=int, default=0,
                        help="validation LCS event-window: record prima dell'evento start")
    parser.add_argument("--lcs-val-post-records", type=int, default=0,
                        help="validation LCS event-window: record dopo l'evento end")
    parser.add_argument("--isolated-event-windows", action="store_true",
                        help=("granular event windows: la validation e il test usano micro-finestre "
                              "per ogni evento (ev-pre .. ev+post) invece di un blocco continuo; "
                              "riduce i falsi positivi quando gli eventi sono distanti tra loro"))
    parser.add_argument("--lcs-early-stop-patience", type=int, default=25,
                        help="epoche senza miglioramento validation prima dello stop LCS; 0 disattiva")
    parser.add_argument("--lcs-no-restore-best", action="store_true",
                        help="disattiva il ripristino della popolazione LCS migliore su validation")
    parser.add_argument("--lcs-no-final-retrain", action="store_true",
                        help="disattiva il retrain finale LCS su tutto il train fino al best epoch")
    parser.add_argument("--lcs-fitness-mode", default="event", choices=["event", "accuracy"],
                        help="fitness interna LCS: event usa F1/recall/balanced accuracy; accuracy usa balanced accuracy")
    parser.add_argument("--lcs-positive-weight", default="auto",
                        help="peso positivi LCS: auto oppure numero, es. 10")
    parser.add_argument("--lcs-max-positive-weight", type=float, default=20.0,
                        help="cap per --lcs-positive-weight auto")
    parser.add_argument("--lcs-positive-replay", default="auto",
                        help="replay positivi per epoca LCS: auto oppure intero, es. 12")
    parser.add_argument("--lcs-max-positive-replay", type=int, default=20,
                        help="cap per --lcs-positive-replay auto")
    parser.add_argument("--lcs-positive-vote-weight", default="auto",
                        help="moltiplicatore voto azione positiva LCS: auto oppure numero, es. 3")
    parser.add_argument("--lcs-max-positive-vote-weight", type=float, default=6.0,
                        help="cap per --lcs-positive-vote-weight auto")
    parser.add_argument("--lcs-selection-metric", default="event_composite",
                        choices=["event_composite", "event_composite_additive", "f1", "bal_acc"],
                        help=("metrica LCS per fitness/selection: event_composite = F1*BalAcc,"
                              " additive mantiene la formula precedente"))
    parser.add_argument("--lcs-export-rule-count", type=int, default=20,
                        help="numero massimo di best_rules LCS esportate nei JSON/artifact")
    parser.add_argument("--lcs-max-active-conditions", type=int, default=0,
                        help=("budget regola: cap sul numero massimo di condizioni non-wildcard"
                              " per ogni regola LCS; 0 = nessun cap. Forza la GA a scegliere"
                              " quali feature contano davvero, rendendo le best_rules leggibili."
                              " Default 0; valori sani: 6-12."))
    parser.add_argument("--lcs-min-fitness-for-subsumption", type=float, default=0.9,
                        help=("fitness minima per applicare subsumption (generalizzazione)."
                              " Default 0.9 e' molto restrittivo: solo regole quasi perfette"
                              " inglobano le piu' specifiche. Abbassare (es. 0.6-0.75) aiuta"
                              " la GA a generalizzare prima e produce regole piu' leggibili."))
    parser.add_argument("--hybrid-lcs", action="store_true",
                        help="aggiunge trial ibridi LCS + bank/deep senza rimuovere LCS puro")
    parser.add_argument("--hybrid-modes", default="and,weighted",
                        help="comma-separated: and,or,weighted")
    parser.add_argument("--hybrid-alphas", default="0.5",
                        help="alpha per weighted hybrid, comma-separated; alpha pesa LCS")
    parser.add_argument("--hybrid-threshold", type=float, default=0.5,
                        help="soglia finale del weighted hybrid")
    parser.add_argument("--hybrid-partners", default="",
                        help=("partner manuali, es. passthrough:ridge,random_projection:ridge,deep:tiny; "
                              "vuoto = banks/readouts correnti + deep presets correnti"))
    parser.add_argument("--enable-lcs-in-max", action="store_true",
                        help="train-max: include anche tutti i preset LCS/UCS")


def main():
    p = argparse.ArgumentParser(prog="pulsar",
        description="Feature-bank benchmark vs deep learning")
    sub = p.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("list", help="Lista task/banks/readouts/deep presets")
    p1.set_defaults(func=cmd_list)

    p2 = sub.add_parser("generate", help="Genera CSV dataset")
    p2.add_argument("--task", required=True)
    p2.add_argument("--n", type=int, default=1000)
    p2.add_argument("--seed", type=int, default=0)
    p2.add_argument("--noise", type=float, default=0.0)
    p2.add_argument("--out", default="dataset.csv")
    p2.set_defaults(func=cmd_generate)

    p3 = sub.add_parser("train", help="Benchmark completo")
    _add_preset_arg(p3)
    _add_train_args(p3, require_task=False)
    p3.set_defaults(func=cmd_train)

    p4 = sub.add_parser("train-max", help="Run massimo: tutti i task, bank, readout e preset deep")
    _add_preset_arg(p4)
    _add_train_args(p4, require_task=False)
    p4.set_defaults(func=cmd_train_max)

    p5 = sub.add_parser("top", help="Leaderboard dal DB")
    p5.add_argument("--task", default=None)
    p5.add_argument("--limit", type=int, default=20)
    p5.add_argument("--db", default="results.db")
    p5.set_defaults(func=cmd_top)

    p6 = sub.add_parser(
        "explore-constants",
        help="Esplora costanti sismiche evento-evento su CSV",
    )
    from seismic_constant_explorer import add_arguments as _add_constant_explorer_args
    _add_constant_explorer_args(p6)
    p6.set_defaults(func=cmd_explore_constants)

    p7 = sub.add_parser(
        "constant-forecast",
        help="Forecast sperimentale walk-forward da costante sismica focus",
    )
    from seismic_constant_forecaster import add_arguments as _add_constant_forecast_args
    _add_constant_forecast_args(p7)
    p7.set_defaults(func=cmd_constant_forecast)

    raw = list(sys.argv[1:])
    if "--list-presets" in raw:
        _print_presets_and_exit()
    try:
        expanded = _expand_preset_argv(raw)
    except ValueError as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        sys.exit(2)
    args = p.parse_args(expanded)
    if getattr(args, "list_presets", False):
        _print_presets_and_exit()
    args.func(args)


if __name__ == "__main__":
    main()

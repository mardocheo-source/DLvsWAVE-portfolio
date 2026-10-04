#!/usr/bin/env python3
"""Ensemble "smart" di 1 analog (BANK) + 1 interpretable/digital backend, scelti col best overall validation
ma con shape penalty che esclude predizioni patologiche (flat / saturate / stuck).

Output: <run_dir>/post_hybrid_checks_smart/
"""

import argparse
import csv
import json
import os
import shlex
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_hybrid_artifacts as pha
from post_hybrid_pair_special import (
    find_candidate, synthesize_meta_from_csv, load_candidate_any,
)


FAMILY_BANKS_PURE = {
    "chebyshev", "prime_fourier", "random_fourier", "random_projection",
    "morlet_wavelet", "passthrough",
}

METRIC_SPECS = [
    ("f1", "F1"),
    ("recall", "Recall"),
    ("precision", "Precision"),
    ("bal_acc", "BalAcc"),
]


def parse_float_or_auto(value):
    text = str(value).strip().lower()
    if text == "auto":
        return "auto"
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            f"expected float or 'auto', got {value!r}"
        ) from exc


def unique_output_dir(run_dir, base_name="post_hybrid_checks_smart"):
    """Crea un path nuovo: <base>_<timestamp>_<seriale>."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for i in range(1, 1000):
        candidate = run_dir / f"{base_name}_{stamp}_{i:03d}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"impossibile trovare output dir libera per {base_name}_{stamp}")


def write_invocation_files(out_dir, argv, *, cwd):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = shlex.join(argv)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_name = f"run_command_{stamp}.sh"
    with open(out_dir / script_name, "w") as fh:
        fh.write("#!/bin/bash\n")
        fh.write(f"# Auto-generated command script\n")
        fh.write(command + "\n")
    os.chmod(out_dir / script_name, 0o755)
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cwd": str(cwd),
        "argv": list(argv),
        "command": command,
    }
    with open(out_dir / "run_command.json", "w") as fh:
        json.dump(payload, fh, indent=2)


def candidate_source_path(cand):
    path = cand.get("path")
    if path and os.path.exists(path):
        return path
    meta = cand.get("meta", {}) or {}
    for key in ("test_json", "signature_json", "test_csv", "validation_combined_csv"):
        path = meta.get(key)
        if path and os.path.exists(path):
            return path
    return None


def source_config_digest(meta):
    cfg = meta.get("model_config", {}) or {}
    hybrid_cfg = cfg.get("hybrid_cfg", {}) or {}
    return {
        "label": pha._artifact_label(meta),
        "bank": meta.get("bank"),
        "readout": meta.get("readout"),
        "seed": meta.get("seed"),
        "best_rules_json": meta.get("best_rules_json"),
        "score_components": meta.get("score_components", {}),
        "trial_metrics": meta.get("trial_metrics", {}),
        "lcs_cfg": cfg.get("lcs_cfg", {}),
        "hybrid_cfg": hybrid_cfg,
        "hybrid_lcs_label": hybrid_cfg.get("lcs_label"),
        "hybrid_mode": hybrid_cfg.get("mode"),
        "hybrid_alpha": hybrid_cfg.get("alpha"),
        "hybrid_partner": hybrid_cfg.get("partner"),
    }


def write_source_bundle(out_dir, cand_a, cand_b, rules_a, rules_b, *,
                        max_rules, argv=None, cwd=None):
    """Copia artifact originali e salva regole/config coinvolte nel merge."""
    sources_dir = Path(out_dir) / "sources"
    source_a_dir = sources_dir / "source_a"
    source_b_dir = sources_dir / "source_b"
    source_a_dir.mkdir(parents=True, exist_ok=True)
    source_b_dir.mkdir(parents=True, exist_ok=True)

    path_a = candidate_source_path(cand_a)
    path_b = candidate_source_path(cand_b)
    manifest_a = pha._collect_artifact_sources(cand_a["meta"], path_a, str(source_a_dir))
    manifest_b = pha._collect_artifact_sources(cand_b["meta"], path_b, str(source_b_dir))

    involved = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "command": shlex.join(argv) if argv else None,
        "cwd": str(cwd) if cwd else None,
        "source_a": source_config_digest(cand_a["meta"]),
        "source_b": source_config_digest(cand_b["meta"]),
        "source_a_manifest": manifest_a,
        "source_b_manifest": manifest_b,
        "source_a_positive_rules": pha._positive_rules(rules_a, max_rules),
        "source_b_positive_rules": pha._positive_rules(rules_b, max_rules),
    }
    with open(sources_dir / "involved_rules_and_artifacts.json", "w") as fh:
        json.dump(involved, fh, indent=2, default=str)
    return {
        "sources_dir": str(sources_dir),
        "source_a_manifest": manifest_a,
        "source_b_manifest": manifest_b,
        "involved_rules_json": str(sources_dir / "involved_rules_and_artifacts.json"),
    }


def family_of(meta):
    bank = str(meta.get("bank", "") or "")
    if bank == "__lcs__":
        return "LCS"
    if bank == "__hybrid__":
        return "HYBRID"
    if bank == "__kan__":
        return "KAN"
    if bank == "__kan_hybrid__":
        return "KAN_HYBRID"
    if bank in FAMILY_BANKS_PURE:
        return "BANK"
    if not bank:
        return "END_TO_END"
    return "OTHER"


def _write_rows_csv(csv_path, rows):
    """Sovrascrive un CSV mantenendo le stesse colonne ma con valori aggiornati."""
    if not rows or not csv_path:
        return
    fieldnames = [k for k in rows[0].keys() if not k.startswith("_")]
    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames if k in row})


def publish_canonical_forecast_alias(out_dir, result, *, pair_name=None):
    """Copia il forecast vincente con nome stabile per gli step successivi."""
    fc_csv = (result or {}).get("forecast_csv")
    if not fc_csv or not os.path.exists(fc_csv):
        return None
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    canonical = out_dir / "smart_fusion_final__forecast.csv"
    shutil.copy2(fc_csv, canonical)
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "canonical_forecast_csv": str(canonical),
        "source_forecast_csv": str(fc_csv),
        "pair_name": pair_name or (result.get("summary", {}) or {}).get("pair"),
        "selected_logic": result.get("selected_logic") or (result.get("summary", {}) or {}).get("logic"),
        "selected_alpha": result.get("selected_alpha") or (result.get("summary", {}) or {}).get("alpha"),
        "summary_json": result.get("summary_json"),
    }
    manifest_path = out_dir / "smart_fusion_final__forecast_manifest.json"
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)
    result["canonical_forecast_csv"] = str(canonical)
    result["canonical_forecast_manifest"] = str(manifest_path)
    return str(canonical)


def read_predictions(csv_path, score_column="pred"):
    if not csv_path or not os.path.exists(csv_path):
        return []
    rows = pha._read_rows(csv_path, has_segment=False) or []
    if not rows and not str(csv_path).endswith(".csv"):
        return []
    if not rows:
        # fallback senza segment
        with open(csv_path, "r", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
    out = []
    for r in rows:
        v = r.get(score_column) or r.get("predicted") or r.get("pred")
        try:
            v = float(v)
            if v == v:  # not NaN
                out.append(v)
        except Exception:
            continue
    return out


def longest_constant_run(values, eps=1e-9):
    if not values:
        return 0
    best = cur = 1
    for i in range(1, len(values)):
        if abs(values[i] - values[i - 1]) <= eps:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 1
    return best


def count_peaks(values, threshold, max_consecutive):
    """Conta picchi validi e plateau.

    Picco = sequenza consecutiva di valori >= threshold, lunghezza tra 1 e max_consecutive.
    Plateau = run >= threshold con lunghezza > max_consecutive (un picco "stirato" che
    non rappresenta un evento puntuale).

    Bordo: una run all'inizio o alla fine della serie viene comunque contata
    (non si vede la "depressione esterna", la trattiamo come picco se rispetta
    max_consecutive, plateau altrimenti).

    Returns: dict con n_peaks, n_plateau, max_run_len.
    """
    if not values:
        return {"n_peaks": 0, "n_plateau": 0, "max_run_len": 0}
    peaks = 0
    plateaus = 0
    max_run = 0
    in_peak = False
    cur_run = 0
    for v in values:
        if v >= threshold:
            if not in_peak:
                in_peak = True
                cur_run = 1
            else:
                cur_run += 1
        else:
            if in_peak:
                if cur_run > max_consecutive:
                    plateaus += 1
                else:
                    peaks += 1
                if cur_run > max_run:
                    max_run = cur_run
                cur_run = 0
                in_peak = False
    if in_peak:
        if cur_run > max_consecutive:
            plateaus += 1
        else:
            peaks += 1
        if cur_run > max_run:
            max_run = cur_run
    return {"n_peaks": peaks, "n_plateau": plateaus, "max_run_len": max_run}


def longest_run_in_band(values, lo, hi):
    """Lunghezza massima di una run consecutiva con valori in [lo, hi]."""
    if not values:
        return 0
    best = cur = 0
    for v in values:
        if lo <= v <= hi:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def shape_quality(pred_values, *, prediction_threshold=0.5,
                  flat_range_threshold=0.3,
                  saturated_max_ratio=0.6,
                  stuck_max_ratio=0.5,
                  neutral_band=0.10,
                  neutral_band_max_ratio=0.25,
                  max_peaks=1,
                  max_consecutive=2,
                  enforce_peak_limit=True,
                  min_length=3):
    """Restituisce (quality in [0,1], dict_diagnostico). 1=sana, 0=patologica."""
    n = len(pred_values)
    if n < min_length:
        return 1.0, {"reason": "too_short", "n": n}

    rng = max(pred_values) - min(pred_values)
    saturated_ratio = sum(1 for v in pred_values if v >= prediction_threshold) / n
    longest_run = longest_constant_run(pred_values)
    stuck_ratio = longest_run / n
    peaks_info = count_peaks(pred_values, prediction_threshold, max_consecutive)
    # Neutral-band run: valori "indecisi" (entro ±neutral_band dal prediction_threshold)
    # Una predizione costantemente vicina al threshold è il segnale "non so" del modello
    # — peggio dei valori costantemente bassi (il modello sa che non è evento).
    neutral_lo = prediction_threshold - neutral_band
    neutral_hi = prediction_threshold + neutral_band
    neutral_run = longest_run_in_band(pred_values, neutral_lo, neutral_hi)
    neutral_run_ratio = neutral_run / n

    flat_pen = 0.0
    if rng < flat_range_threshold:
        flat_pen = (flat_range_threshold - rng) / flat_range_threshold

    sat_pen = 0.0
    if saturated_ratio > saturated_max_ratio:
        sat_pen = min(1.0, (saturated_ratio - saturated_max_ratio) /
                      (1.0 - saturated_max_ratio))

    stuck_pen = 0.0
    if stuck_ratio > stuck_max_ratio:
        stuck_pen = min(1.0, (stuck_ratio - stuck_max_ratio) /
                        (1.0 - stuck_max_ratio))

    # Penalty per troppi picchi: SOLO se enforce_peak_limit (default solo sul forecast).
    # Sul validation è naturale avere molti picchi reali.
    peak_pen = 0.0
    n_peaks = peaks_info["n_peaks"]
    if enforce_peak_limit and n_peaks > max_peaks:
        excess = n_peaks - max_peaks
        peak_pen = min(1.0, excess / max(1, max_peaks))

    # Penalty per plateau (run > max_consecutive): applicato sempre (anche in validation
    # un "high risk" prolungato 5+ settimane consecutive è non realistico).
    plateau_pen = min(1.0, peaks_info["n_plateau"] * 0.4)

    # Penalty per "neutral band" run lunghe: il modello è indeciso sopra/sotto threshold.
    # Patologico quando >25% del segnale è bloccato attorno a 0.5.
    neutral_pen = 0.0
    if neutral_run_ratio > neutral_band_max_ratio:
        neutral_pen = min(1.0, (neutral_run_ratio - neutral_band_max_ratio) /
                          (1.0 - neutral_band_max_ratio))

    quality = 1.0 - max(flat_pen, sat_pen, stuck_pen, peak_pen, plateau_pen, neutral_pen)
    quality = max(0.0, min(1.0, quality))
    diag = {
        "n": n,
        "range": rng,
        "saturated_ratio": saturated_ratio,
        "longest_run": longest_run,
        "stuck_ratio": stuck_ratio,
        "neutral_run": neutral_run,
        "neutral_run_ratio": neutral_run_ratio,
        "n_peaks": n_peaks,
        "n_plateau": peaks_info["n_plateau"],
        "max_run_len": peaks_info["max_run_len"],
        "flat_penalty": flat_pen,
        "saturated_penalty": sat_pen,
        "stuck_penalty": stuck_pen,
        "neutral_penalty": neutral_pen,
        "peak_penalty": peak_pen,
        "plateau_penalty": plateau_pen,
        "quality": quality,
    }
    return quality, diag


def discover_all_candidates(run_dir, dataset_subfolder, score_column,
                            forecast_guard, forecast_flat_eps,
                            forecast_high_ratio):
    """Scopre tutti i *test.json (o fallback CSV) e ne carica i meta."""
    search_dirs = [
        run_dir / dataset_subfolder,
        run_dir / "best_by_bank" / dataset_subfolder,
    ]
    seen = set()
    candidates = []
    # primo: JSON veri
    for d in search_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*__test.json")):
            if p.name in seen:
                continue
            seen.add(p.name)
            cand = load_candidate_any(
                ("json", p), score_column,
                forecast_guard, forecast_flat_eps, forecast_high_ratio,
            )
            if cand is not None:
                cand["family"] = family_of(cand["meta"])
                candidates.append(cand)
    # fallback: CSV → meta sintetico, solo se basename non già visto
    for d in search_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*__test.csv")):
            stem = p.name[: -len("__test.csv")]
            base_json = stem + "__test.json"
            if base_json in seen or p.name in seen:
                continue
            seen.add(p.name)
            cand = load_candidate_any(
                ("csv", p), score_column,
                forecast_guard, forecast_flat_eps, forecast_high_ratio,
            )
            if cand is not None:
                cand["family"] = family_of(cand["meta"])
                candidates.append(cand)
    return candidates


def peak_strength(values, prediction_threshold=0.5):
    """Misura la 'forza' del picco massimo nel segnale.

    Score = (max - mean) normalizzato sul range, premia segnali con un picco
    pronunciato emergente dal baseline. Utile per il forecast quando vogliamo
    'il picco con maggior probabilità', anche se in lettura analogica.
    """
    if not values:
        return 0.0
    vmax = max(values)
    vmin = min(values)
    vmean = sum(values) / len(values)
    rng = vmax - vmin
    if rng <= 1e-9:
        return 0.0
    # peak height above baseline, normalized by range
    raw = (vmax - vmean) / rng
    # bonus se il max è sopra threshold (segnale "attivo")
    if vmax >= prediction_threshold:
        raw += 0.2
    return float(min(1.0, max(0.0, raw)))


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def _find_peaks_normalized(seq, floor=0.30):
    """Trova massimi locali nel segnale self-normalizzato al proprio range [0,1].

    Ogni segnale viene prima normalizzato nel suo stesso range (vmin→0, vmax→1),
    poi si cercano i massimi locali. In questo modo:
    - Un analogico debole 0.06-0.11 viene portato a 0.0-1.0: il picco a 0.07
      diventa ~0.50 e viene rilevato con floor=0.30
    - Un ibrido binario 0/1 rimane 0/1: i picchi a 1.0 sono sempre rilevati
    - Completamente indipendente dall'ampiezza assoluta del segnale

    floor (default 0.30): frazione del proprio range sotto cui un punto NON è
    considerato picco. 0.30 = "solo il top 70% del range conta come picco".

    Segnale costante (rng<1e-9) → nessun picco (niente da confrontare).
    """
    if not seq:
        return set()
    vmin = min(seq)
    vmax = max(seq)
    rng = vmax - vmin
    if rng < 1e-9:
        return set()
    norm = [(v - vmin) / rng for v in seq]
    n = len(norm)
    peaks = set()
    for i in range(n):
        left = norm[i - 1] if i > 0 else -1.0
        right = norm[i + 1] if i < n - 1 else -1.0
        if norm[i] >= floor and (norm[i] > left or norm[i] > right):
            peaks.add(i)
    return peaks


def _peak_overlap_combine(scores_a, scores_b, *, threshold, alpha, window=1,
                           floor=0.30, thr_a=None, thr_b=None,
                           conf_a=None, conf_b=None, max_peaks=1):
    """Combina via overlap di picchi AND: entrambi devono avere un picco locale nella
    stessa finestra ±window. Rank overlap events per self-norm strength (scala omogenea).

    Ranking usa le self-norm values di ciascun segnale nel proprio range [0,1] →
    un analogico 0.06-0.11 e un ibrido 0/1 sono confrontabili perché entrambi
    normalizzati al loro range. max_peaks: quanti overlap events tenere (top N).

    scores_a/b: segnali da usare per peak detection (tipicamente raw pre-norm).
    conf_a/b:   valori per la confidence del merge (se None usa scores_a/b).
    Restituisce (pred, conf_out) — pred tutto zero se nessun overlap trovato.
    """
    peaks_a = _find_peaks_normalized(scores_a, floor=floor)
    peaks_b = _find_peaks_normalized(scores_b, floor=floor)
    na = _self_norm_seq(scores_a)
    nb = _self_norm_seq(scores_b)
    ca = conf_a if conf_a is not None else scores_a
    cb = conf_b if conf_b is not None else scores_b
    n = len(scores_a)

    # Trova overlap events: per ogni coppia (p∈A, q∈B) con |p-q|≤window
    # usa posizione A come centro canonico, forza = max(norm_a[p], norm_b[q])
    overlap_strength = {}
    for p in peaks_a:
        for q in peaks_b:
            if abs(p - q) <= window:
                strength = max(na[p] if p < len(na) else 0.0,
                               nb[q] if q < len(nb) else 0.0)
                if p not in overlap_strength or strength > overlap_strength[p]:
                    overlap_strength[p] = strength

    if not overlap_strength:
        # Nessun overlap: restituisce tutto zero; il chiamante gestisce il fallback
        return [0.0] * n, [alpha * ca[i] + (1.0 - alpha) * cb[i] for i in range(n)]

    # Seleziona top max_peaks centri per self-norm strength
    ranked_centers = sorted(overlap_strength, key=lambda c: overlap_strength[c], reverse=True)
    selected_centers = set(ranked_centers[:max_peaks])

    # Espandi i centri selezionati per ±window
    active_set = set()
    for c in selected_centers:
        for offset in range(-window, window + 1):
            idx = c + offset
            if 0 <= idx < n:
                active_set.add(idx)

    pred = [1.0 if i in active_set else 0.0 for i in range(n)]
    conf_out = [alpha * ca[i] + (1.0 - alpha) * cb[i] for i in range(n)]
    return pred, conf_out


def _self_norm_seq(seq):
    """Normalizza una sequenza nel proprio range [0,1]. Sequenza costante → tutti zero."""
    if not seq:
        return []
    vmin = min(seq)
    vmax = max(seq)
    rng = vmax - vmin
    if rng < 1e-9:
        return [0.0] * len(seq)
    return [(v - vmin) / rng for v in seq]


def _peak_or_select(scores_a, scores_b, *, floor, max_peaks, window, alpha,
                    conf_a=None, conf_b=None):
    """OR fallback con peak detection: unione picchi A∪B, ranking per self-norm
    within-signal (scala omogenea), top max_peaks centri espansi per ±window.

    Ogni picco porta la propria self-norm strength (norm_a per picchi solo in A,
    norm_b per picchi solo in B, max(norm_a, norm_b) per picchi condivisi).

    IMPORTANTE: richiede che ENTRAMBI i segnali abbiano almeno un picco.
    Se uno dei segnali è piatto (nessun picco rilevato), restituisce (None, None)
    → il chiamante cade nel fallback threshold-OR puro.
    Questo evita falsi positivi quando un candidato è flat (es. LCS con forecast=0).
    """
    peaks_a = _find_peaks_normalized(scores_a, floor=floor)
    peaks_b = _find_peaks_normalized(scores_b, floor=floor)
    if not peaks_a or not peaks_b:
        return None, None
    all_peaks = peaks_a | peaks_b
    if not all_peaks:
        return None, None
    na = _self_norm_seq(scores_a)
    nb = _self_norm_seq(scores_b)

    def _strength(p):
        in_a = p in peaks_a
        in_b = p in peaks_b
        sa = na[p] if (in_a and p < len(na)) else 0.0
        sb = nb[p] if (in_b and p < len(nb)) else 0.0
        return max(sa, sb)

    ranked = sorted(all_peaks, key=_strength, reverse=True)
    selected = set(ranked[:max_peaks])
    n = len(scores_a)
    ca = conf_a if conf_a is not None else scores_a
    cb = conf_b if conf_b is not None else scores_b
    active_set = set()
    for c in selected:
        for offset in range(-window, window + 1):
            idx = c + offset
            if 0 <= idx < n:
                active_set.add(idx)
    pred = [1.0 if i in active_set else 0.0 for i in range(n)]
    conf_out = [alpha * ca[i] + (1.0 - alpha) * cb[i] for i in range(n)]
    return pred, conf_out


def metric_blend(metrics):
    """Compatta le metriche binarie validation in uno score 0..1."""
    if not metrics:
        return 0.0
    return clamp01(
        0.32 * metrics.get("f1", 0.0)
        + 0.26 * metrics.get("bal_acc", 0.0)
        + 0.24 * metrics.get("recall", 0.0)
        + 0.18 * metrics.get("precision", 0.0)
    )


def resolve_cascade_threshold(best_a, best_b, requested):
    if requested != "auto":
        return {
            "mode": "manual",
            "resolved": float(requested),
            "components": {},
        }
    avg_quality = 0.5 * (
        float(best_a["quality"].get("overall_quality", 0.0) or 0.0)
        + float(best_b["quality"].get("overall_quality", 0.0) or 0.0)
    )
    avg_validation = 0.5 * (
        float(best_a.get("validation_score", 0.0) or 0.0)
        + float(best_b.get("validation_score", 0.0) or 0.0)
    )
    min_sanity = min(
        float(best_a.get("source_sanity", 0.0) or 0.0),
        float(best_b.get("source_sanity", 0.0) or 0.0),
    )
    avg_smart = 0.5 * (
        clamp01(best_a.get("smart_score", 0.0) or 0.0)
        + clamp01(best_b.get("smart_score", 0.0) or 0.0)
    )
    resolved = clamp01(
        max(
            0.30,
            0.38 * avg_quality
            + 0.27 * avg_validation
            + 0.20 * min_sanity
            + 0.15 * avg_smart
            - 0.04,
        )
    )
    return {
        "mode": "auto",
        "resolved": resolved,
        "components": {
            "avg_quality": avg_quality,
            "avg_validation": avg_validation,
            "min_sanity": min_sanity,
            "avg_smart": avg_smart,
        },
    }


def named_metric_bests(named_metrics):
    best = {}
    for key, _ in METRIC_SPECS:
        winner = {"name": "-", "value": 0.0}
        for name, metrics in named_metrics:
            value = float((metrics or {}).get(key, 0.0) or 0.0)
            if value > winner["value"]:
                winner = {"name": str(name), "value": value}
        best[key] = winner
    return best


def dual_metrics_delta_report(current_metrics, immediate_named, cumulative_named,
                              *, current_label):
    immediate_best = named_metric_bests(immediate_named)
    cumulative_best = named_metric_bests(cumulative_named)
    lines = []
    lines.append(f"METRIC PROGRESSION REPORT  [{current_label}]")
    lines.append(
        f"{'metric':<10} {'current':>8} {'prev_best':>22} {'Δprev':>8} "
        f"{'orig_best':>22} {'Δcum':>8}  verdict"
    )
    improved_prev = 0
    improved_cum = 0
    for key, label in METRIC_SPECS:
        current = float((current_metrics or {}).get(key, 0.0) or 0.0)
        prev = immediate_best.get(key, {"name": "-", "value": 0.0})
        orig = cumulative_best.get(key, {"name": "-", "value": 0.0})
        delta_prev = current - prev["value"]
        delta_cum = current - orig["value"]
        if delta_prev > 1e-9:
            improved_prev += 1
        if delta_cum > 1e-9:
            improved_cum += 1
        if delta_prev > 1e-9 and delta_cum > 1e-9:
            verdict = "gain both"
        elif delta_cum > 1e-9:
            verdict = "gain cum"
        elif abs(delta_prev) < 1e-3 and abs(delta_cum) < 1e-3:
            verdict = "flat"
        else:
            verdict = "down"
        prev_ref = f"{prev['name'][:14]:<14} {prev['value']:.3f}"
        orig_ref = f"{orig['name'][:14]:<14} {orig['value']:.3f}"
        lines.append(
            f"{label:<10} {current:>8.3f} {prev_ref:>22} {delta_prev:+8.3f} "
            f"{orig_ref:>22} {delta_cum:+8.3f}  {verdict}"
        )
    lines.append("")
    lines.append(
        f"Immediate gains: {improved_prev}/{len(METRIC_SPECS)}  |  "
        f"Cumulative gains: {improved_cum}/{len(METRIC_SPECS)}"
    )
    return "\n".join(lines), {
        "current_label": current_label,
        "current_metrics": {
            key: float((current_metrics or {}).get(key, 0.0) or 0.0)
            for key, _ in METRIC_SPECS
        },
        "immediate_best_metrics": {
            key: immediate_best.get(key, {}).get("value", 0.0)
            for key, _ in METRIC_SPECS
        },
        "immediate_best_sources": {
            key: immediate_best.get(key, {}).get("name", "-")
            for key, _ in METRIC_SPECS
        },
        "cumulative_best_metrics": {
            key: cumulative_best.get(key, {}).get("value", 0.0)
            for key, _ in METRIC_SPECS
        },
        "cumulative_best_sources": {
            key: cumulative_best.get(key, {}).get("name", "-")
            for key, _ in METRIC_SPECS
        },
    }


def source_sanity_score(quality, metrics):
    """Quanto e' guardabile/affidabile il singolo artifact prima del merge."""
    vd = quality.get("validation_diag", {}) or {}
    fd = quality.get("forecast_diag", {}) or {}
    score = float(quality.get("overall_quality", 0.0) or 0.0)

    # Plateau/stuck in validation: e' il caso brutto visto nei PNG, dove il
    # candidato rimane appeso vicino a una decisione piatta e poi satura.
    stuck = float(vd.get("stuck_ratio", 0.0) or 0.0)
    neutral = float(vd.get("neutral_run_ratio", 0.0) or 0.0)
    plateau = int(vd.get("n_plateau", 0) or 0)
    sat_ratio = float(vd.get("saturated_ratio", 0.0) or 0.0)
    rng = float(vd.get("range", 0.0) or 0.0)

    # Auto-scarto totale per curve piatte, ostruite o palesemente aliene
    if stuck >= 0.70 or sat_ratio >= 0.70 or rng < 0.05:
        score = 0.0
    elif stuck >= 0.60:
        score = min(score, 0.18)
    if neutral >= 0.45:
        score = min(score, 0.12)
    elif neutral >= 0.30:
        score = min(score, 0.25)
    if plateau > 0:
        score = min(score, 0.30)

    # Anche forecast con plateau eccessivo non deve diventare "best source".
    f_stuck = float(fd.get("stuck_ratio", 0.0) or 0.0)
    if int(fd.get("n_plateau", 0) or 0) > 0 or f_stuck >= 0.6:
        score = min(score, 0.20)

    f1 = float(metrics.get("f1", 0.0) or 0.0)
    precision = float(metrics.get("precision", 0.0) or 0.0)
    recall = float(metrics.get("recall", 0.0) or 0.0)
    if f1 < 0.25 and precision < 0.25:
        score = min(score, 0.18)
    if recall == 0.0:
        score = min(score, 0.20)
    return clamp01(score)


def merge_confidence(score_a, score_b, logic, alpha):
    logic = str(logic).lower()
    if logic in ("and", "sure"):
        return min(score_a, score_b)
    if logic in ("or", "conservative"):
        return max(score_a, score_b)
    if logic == "weighted":
        return float(alpha) * score_a + (1.0 - float(alpha)) * score_b
    return 0.5 * (score_a + score_b)


def active_runs(values, threshold=0.5):
    runs = []
    start = None
    for i, v in enumerate(values):
        if v >= threshold:
            if start is None:
                start = i
        elif start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(values) - 1))
    return runs


def peak_profile(pred_values, confidences=None, *, threshold=0.5,
                 max_consecutive=2):
    """Diagnostica picchi forecast con probabilita/confidenza del merge."""
    if confidences is None:
        confidences = pred_values
    runs = active_runs(pred_values, threshold)
    peaks = []
    for start, end in runs:
        conf_slice = confidences[start:end + 1] or [0.0]
        best_offset, best_conf = max(enumerate(conf_slice), key=lambda x: x[1])
        peaks.append({
            "start": start,
            "end": end,
            "length": end - start + 1,
            "best_index": start + best_offset,
            "best_confidence": float(best_conf),
            "mean_confidence": float(sum(conf_slice) / len(conf_slice)),
            "is_plateau": (end - start + 1) > max_consecutive,
        })
    peaks.sort(key=lambda p: (p["best_confidence"], p["mean_confidence"]),
               reverse=True)
    return {
        "active_count": len([v for v in pred_values if v >= threshold]),
        "active_ratio": (
            sum(1 for v in pred_values if v >= threshold) / len(pred_values)
            if pred_values else 0.0
        ),
        "n_runs": len(runs),
        "n_plateau": sum(1 for p in peaks if p["is_plateau"]),
        "top_confidence": peaks[0]["best_confidence"] if peaks else 0.0,
        "top_index": peaks[0]["best_index"] if peaks else None,
        "peaks": peaks,
    }


def peak_count_fit(profile, max_peaks):
    n = int(profile.get("n_runs", 0) or 0)
    plateaus = int(profile.get("n_plateau", 0) or 0)
    if max_peaks <= 0:
        return 1.0
    if n == max_peaks and plateaus == 0:
        return 1.0
    if n == 0:
        return 0.35
    excess = max(0, n - max_peaks)
    return clamp01(1.0 - 0.30 * excess - 0.35 * plateaus)


def forecast_eval_from_values(values, args):
    if not values:
        return {
            "rows": 0,
            "active_ratio": 0.0,
            "range": 0.0,
            "guard": {"mode": args.forecast_guard, "penalty": 0.0,
                      "bonus": 0.0, "flags": []},
        }
    frange = max(values) - min(values)
    active = sum(1 for v in values if v >= args.prediction_threshold)
    stats = {
        "rows": len(values),
        "range": frange,
        "active_ratio_raw": active / len(values),
        "active_raw": active,
    }
    return {
        "rows": len(values),
        "active_ratio": active / len(values),
        "range": frange,
        "guard": pha._forecast_guard_from_stats(
            stats, mode=args.forecast_guard,
            flat_eps=args.forecast_flat_eps,
            high_ratio=args.forecast_high_ratio,
        ),
    }


def forecast_predictions_for_sim(cand_a, cand_b, sim, args, logic, alpha):
    fc_a = cand_a["meta"].get("forecast_csv")
    fc_b = cand_b["meta"].get("forecast_csv")
    if not (fc_a and fc_b and os.path.exists(fc_a) and os.path.exists(fc_b)):
        return [], []
    rows_fc_a = pha._read_rows(fc_a, has_segment=False)
    rows_fc_b = pha._read_rows(fc_b, has_segment=False)
    aligned_fc = pha._align_rows(rows_fc_a, rows_fc_b, has_segment=False)
    raw_thr_a = pha._artifact_threshold(cand_a["meta"])
    raw_thr_b = pha._artifact_threshold(cand_b["meta"])
    raw_scores_a = []
    raw_scores_b = []
    scores_a = []
    scores_b = []
    for a, b in aligned_fc:
        raw_a = pha._score_value(a, args.score_column)
        raw_b = pha._score_value(b, args.score_column)
        raw_scores_a.append(float(raw_a) if raw_a is not None else 0.0)
        raw_scores_b.append(float(raw_b) if raw_b is not None else 0.0)
        scores_a.append(pha._apply_normalizer(
            raw_a, sim["normalizer_a"], raw_threshold=raw_thr_a,
            normalized_threshold=sim["threshold"],
        ))
        scores_b.append(pha._apply_normalizer(
            raw_b, sim["normalizer_b"], raw_threshold=raw_thr_b,
            normalized_threshold=sim["threshold"],
        ))
    if getattr(args, "peak_and", False) and logic == "and" and scores_a:
        # Peak detection sui raw scores (pre-normalizzazione) per preservare la
        # struttura del picco anche in segnali con ampiezza bassa (< threshold).
        # Cascata window=0..peak_window: usa il primo che trova overlap AND.
        # Se nessuno → fallback peak-OR (unione picchi, rank self-norm, top max_peaks).
        floor = getattr(args, "peak_floor", 0.30)
        max_win = getattr(args, "peak_window", 1)
        max_peaks = getattr(args, "peak_max", 1)
        peak_result = None
        for w in range(max_win + 1):
            candidate, cand_conf = _peak_overlap_combine(
                raw_scores_a, raw_scores_b,
                threshold=raw_thr_a,
                alpha=alpha,
                window=w,
                floor=floor,
                thr_a=raw_thr_a,
                thr_b=raw_thr_b,
                conf_a=scores_a,
                conf_b=scores_b,
                max_peaks=max_peaks,
            )
            if sum(candidate) > 0:
                peak_result = (candidate, cand_conf)
                break
        if peak_result is not None:
            return peak_result
        # Nessun overlap AND a nessun window → fallback peak-OR (rank self-norm)
        or_pred, or_conf = _peak_or_select(
            raw_scores_a, raw_scores_b,
            floor=floor, max_peaks=max_peaks, window=max_win,
            alpha=alpha, conf_a=scores_a, conf_b=scores_b,
        )
        if or_pred is not None:
            return or_pred, or_conf
        # Nessun picco affatto → or puro
        pred = [pha._combine(sa, sb, "or", alpha, sim["threshold"],
                             threshold_a=sim.get("threshold_a"),
                             threshold_b=sim.get("threshold_b"))
                for sa, sb in zip(scores_a, scores_b)]
        conf = [merge_confidence(sa, sb, "or", alpha)
                for sa, sb in zip(scores_a, scores_b)]
        return pred, conf
    pred = [pha._combine(sa, sb, logic, alpha, sim["threshold"],
                         threshold_a=sim.get("threshold_a"),
                         threshold_b=sim.get("threshold_b"))
            for sa, sb in zip(scores_a, scores_b)]
    conf = [merge_confidence(sa, sb, logic, alpha)
            for sa, sb in zip(scores_a, scores_b)]
    return pred, conf


def simulate_merge_profile(args, cand_a, cand_b, logic, alpha, shape_kwargs):
    sim = pha._simulate_pair(
        cand_a["meta"], cand_b["meta"],
        logic=logic, normalize=args.normalize, score_column=args.score_column,
        alpha=alpha, threshold=args.threshold,
        calibrate_mode=args.calibrate_mode,
        calibrate_metric=args.calibrate_metric,
        min_recall=args.min_recall,
        actual_threshold=args.actual_threshold,
        forecast_guard=args.forecast_guard,
        forecast_flat_eps=args.forecast_flat_eps,
        forecast_high_ratio=args.forecast_high_ratio,
    )
    if sim is None:
        return None
    pred_fc, conf_fc = forecast_predictions_for_sim(
        cand_a, cand_b, sim, args, logic, alpha,
    )
    fc_q, fc_diag = shape_quality(
        pred_fc, enforce_peak_limit=True, **shape_kwargs,
    )
    profile = peak_profile(
        pred_fc, conf_fc, threshold=args.prediction_threshold,
        max_consecutive=args.max_consecutive,
    )
    metrics_score = metric_blend(sim["metrics"])
    peak_signal = clamp01(
        0.65 * profile["top_confidence"]
        + 0.25 * peak_strength(conf_fc, args.prediction_threshold)
        + 0.10 * peak_count_fit(profile, args.max_peaks)
    )
    return {
        "sim": sim,
        "logic": logic,
        "alpha": alpha,
        "forecast_pred": pred_fc,
        "forecast_conf": conf_fc,
        "forecast_quality": fc_q,
        "forecast_diag": fc_diag,
        "peak_profile": profile,
        "metrics_score": metrics_score,
        "peak_signal": peak_signal,
        "max_peaks": args.max_peaks,
    }


def merge_selection_score(profile, preference):
    """Punteggio auto-logic: shape/peak sono priorita, non filtri ciechi."""
    fc_q = profile["forecast_quality"]
    metrics_score = profile["metrics_score"]
    peak_signal = profile["peak_signal"]
    count_fit = peak_count_fit(profile["peak_profile"], profile.get("max_peaks", 1))
    active_ratio = profile["peak_profile"].get("active_ratio", 0.0)
    high_active_pen = max(0.0, active_ratio - 0.55) / 0.45
    no_signal_pen = 0.20 if profile["peak_profile"].get("active_count", 0) == 0 else 0.0
    sanity = clamp01(fc_q + 0.20 * count_fit - 0.35 * high_active_pen - no_signal_pen)
    if preference == "peak":
        score = (
            0.38 * peak_signal
            + 0.26 * sanity
            + 0.24 * metrics_score
            + 0.12 * count_fit
        )
    elif preference == "final":
        score = (
            0.42 * sanity
            + 0.26 * metrics_score
            + 0.20 * peak_signal
            + 0.12 * count_fit
        )
    else:
        score = (
            0.50 * sanity
            + 0.24 * metrics_score
            + 0.16 * count_fit
            + 0.10 * peak_signal
        )
    guard = profile["sim"]["forecast_eval"]["guard"]
    return clamp01(score + guard.get("bonus", 0.0) - guard.get("penalty", 0.0))


def choose_top_forecast_peaks(rows, args, logic, alpha):
    """Se max_peaks impone un solo picco, tiene le finestre piu' probabili."""
    if not rows or args.max_peaks <= 0:
        return rows, {}
    pred = []
    conf = []
    for r in rows:
        try:
            p = float(r.get("predicted", 0.0) or 0.0)
            sa = float(r.get("a_score", 0.0) or 0.0)
            sb = float(r.get("b_score", 0.0) or 0.0)
        except Exception:
            p, sa, sb = 0.0, 0.0, 0.0
        pred.append(p)
        conf.append(merge_confidence(sa, sb, logic, alpha))
    runs = active_runs(pred, args.prediction_threshold)
    windows = []
    width = max(1, args.max_consecutive)
    for start, end in runs:
        best = None
        for w_start in range(start, end + 1):
            w_end = min(end, w_start + width - 1)
            score = sum(conf[w_start:w_end + 1])
            item = (score, max(conf[w_start:w_end + 1]), w_start, w_end)
            if best is None or item > best:
                best = item
        if best is not None:
            windows.append(best)
    if len(windows) <= args.max_peaks and all(
        (end - start + 1) <= args.max_consecutive for start, end in runs
    ):
        return rows, {
            "enabled": True,
            "changed": False,
            "reason": "already_within_peak_limit",
            "before": peak_profile(pred, conf, threshold=args.prediction_threshold,
                                   max_consecutive=args.max_consecutive),
        }
    windows.sort(reverse=True)
    keep = set()
    for _, _, start, end in windows[:args.max_peaks]:
        keep.update(range(start, end + 1))
    changed = False
    for i, r in enumerate(rows):
        new_pred = 1.0 if i in keep else 0.0
        old_pred = pred[i]
        if abs(old_pred - new_pred) > 1e-12:
            changed = True
        r["predicted"] = new_pred
        actual = float(r.get("actual_event", 0.0) or 0.0)
        r["error"] = new_pred - actual
    after_pred = [float(r.get("predicted", 0.0) or 0.0) for r in rows]
    return rows, {
        "enabled": True,
        "changed": changed,
        "reason": "kept_highest_confidence_peak_windows",
        "max_peaks": args.max_peaks,
        "max_consecutive": args.max_consecutive,
        "before": peak_profile(pred, conf, threshold=args.prediction_threshold,
                               max_consecutive=args.max_consecutive),
        "after": peak_profile(after_pred, conf, threshold=args.prediction_threshold,
                              max_consecutive=args.max_consecutive),
    }


def candidate_metrics_dict(meta, score_column="pred", actual_threshold=None,
                           prediction_threshold=0.5):
    """Calcola metriche binarie del singolo candidato sul validation_combined."""
    val_csv = meta.get("validation_combined_csv")
    if not val_csv or not os.path.exists(val_csv):
        return {}
    rows = pha._read_rows(val_csv, has_segment=True) or []
    if not rows:
        return {}
    actual = []
    pred = []
    raw_thr = pha._artifact_threshold(meta) if actual_threshold is None else actual_threshold
    for r in rows:
        a = r.get("_actual")
        try:
            a = float(a)
        except Exception:
            continue
        if a != a:
            continue
        v = pha._score_value(r, score_column)
        actual.append(1.0 if a >= raw_thr else 0.0)
        pred.append(1.0 if v >= prediction_threshold else 0.0)
    return pha._event_metrics(actual, pred)


def metrics_delta_report(merge_metrics, a_metrics, b_metrics):
    """Stampa un confronto leggibile: merge vs A vs B per vedere se la fusione
    ha portato un vantaggio reale."""
    keys = ["f1", "recall", "precision", "bal_acc"]
    lines = []
    lines.append(f"{'metric':>10s} {'A':>8s} {'B':>8s} {'MERGE':>8s}  vsA      vsB     verdict")
    any_gain = False
    for k in keys:
        a = float(a_metrics.get(k, 0.0) or 0.0)
        b = float(b_metrics.get(k, 0.0) or 0.0)
        m = float(merge_metrics.get(k, 0.0) or 0.0)
        d_a = m - a
        d_b = m - b
        verdict = "✓ gain" if (m > max(a, b)) else ("≈ tie" if abs(m - max(a,b)) < 1e-3 else "✗ no gain")
        if m > max(a, b):
            any_gain = True
        lines.append(f"{k:>10s} {a:>8.3f} {b:>8.3f} {m:>8.3f}  {d_a:+.3f}  {d_b:+.3f}  {verdict}")
    lines.append("")
    lines.append("MERGE FRUTTUOSO" if any_gain else "merge non ha migliorato nessuna metrica chiave")
    return "\n".join(lines)


def evaluate_candidate_quality(cand, score_column, **shape_kwargs):
    val_csv = cand["meta"].get("validation_combined_csv")
    fc_csv = cand["meta"].get("forecast_csv")
    val_preds = read_predictions(val_csv, score_column)
    fc_preds = read_predictions(fc_csv, score_column)
    # Validation: NON applicare il limite sul numero di picchi (sono storia reale)
    val_q, val_diag = shape_quality(val_preds, enforce_peak_limit=False, **shape_kwargs)
    # Forecast: applica TUTTI i limiti (max_peaks è proprio per la finestra futura)
    fc_q, fc_diag = shape_quality(fc_preds, enforce_peak_limit=True, **shape_kwargs)
    # Forecast pesa di più: il problema visto era proprio nel forecast saturo.
    overall_q = (val_q * 0.4 + fc_q * 0.6)
    return {
        "validation_quality": val_q,
        "forecast_quality": fc_q,
        "overall_quality": overall_q,
        "validation_diag": val_diag,
        "forecast_diag": fc_diag,
        "validation_n": len(val_preds),
        "forecast_n": len(fc_preds),
    }


def select_best_in_family(candidates, family, *, min_quality, score_column,
                          shape_kwargs, actual_threshold=None,
                          prediction_threshold=0.5, verbose=True):
    pool = [c for c in candidates if c["family"] == family]
    if not pool:
        return None, []
    enriched = []
    for c in pool:
        q = evaluate_candidate_quality(c, score_column, **shape_kwargs)
        cscore = float(c["info"].get("candidate_score", 0.0) or 0.0)
        metrics = candidate_metrics_dict(
            c["meta"], score_column, actual_threshold, prediction_threshold,
        )
        validation_score = metric_blend(metrics)
        source_sanity = source_sanity_score(q, metrics)
        smart = (
            0.42 * validation_score
            + 0.33 * source_sanity
            + 0.25 * clamp01(cscore)
        )
        enriched.append({
            "cand": c,
            "candidate_score": cscore,
            "validation_score": validation_score,
            "validation_metrics": metrics,
            "source_sanity": source_sanity,
            "quality": q,
            "smart_score": smart,
        })
    enriched.sort(key=lambda r: r["smart_score"], reverse=True)
    if verbose:
        print(f"\n  Famiglia {family}: {len(enriched)} candidati")
        for e in enriched:
            label = pha._artifact_label(e["cand"]["meta"])
            q = e["quality"]
            mark = "✓" if q["overall_quality"] >= min_quality else "✗"
            print(f"    {mark} smart={e['smart_score']:+.4f}  cand={e['candidate_score']:.4f}  "
                  f"qual={q['overall_quality']:.3f}  (val={q['validation_quality']:.3f} "
                  f"fc={q['forecast_quality']:.3f})  bin={e['validation_score']:.3f}  "
                  f"src={e['source_sanity']:.3f}  {label[:50]}")
            vm = e["validation_metrics"]
            print(f"        bin val: f1={vm.get('f1',0):.3f} p={vm.get('precision',0):.3f} "
                  f"r={vm.get('recall',0):.3f} bal={vm.get('bal_acc',0):.3f}")
            vd = q["validation_diag"]; fd = q["forecast_diag"]
            print(f"        diag val: range={vd.get('range',0):.2f} sat={vd.get('saturated_ratio',0):.2f} "
                  f"stuck={vd.get('stuck_ratio',0):.2f} neutral={vd.get('neutral_run_ratio',0):.2f} "
                  f"peaks={vd.get('n_peaks',0)} plateau={vd.get('n_plateau',0)}")
            print(f"        diag fc : range={fd.get('range',0):.2f} sat={fd.get('saturated_ratio',0):.2f} "
                  f"stuck={fd.get('stuck_ratio',0):.2f} neutral={fd.get('neutral_run_ratio',0):.2f} "
                  f"peaks={fd.get('n_peaks',0)} plateau={fd.get('n_plateau',0)}")
    accepted = [e for e in enriched if e["quality"]["overall_quality"] >= min_quality]
    if accepted:
        return accepted[0], enriched
    if enriched:
        if verbose:
            print(f"  ⚠ Nessun {family} >= min_quality={min_quality} → fallback al top assoluto "
                  f"({pha._artifact_label(enriched[0]['cand']['meta'])} "
                  f"qual={enriched[0]['quality']['overall_quality']:.3f})")
        return enriched[0], enriched
    return None, []


def fuse_pair(cand_a, cand_b, args, out_dir, score_column):
    sim = pha._simulate_pair(
        cand_a["meta"], cand_b["meta"],
        logic=args.logic, normalize=args.normalize, score_column=score_column,
        alpha=args.alpha, threshold=args.threshold,
        calibrate_mode=args.calibrate_mode,
        calibrate_metric=args.calibrate_metric,
        min_recall=args.min_recall,
        actual_threshold=args.actual_threshold,
        forecast_guard=args.forecast_guard,
        forecast_flat_eps=args.forecast_flat_eps,
        forecast_high_ratio=args.forecast_high_ratio,
    )
    if sim is None:
        sys.exit("Simulazione fallita.")
    label_a = pha._artifact_label(cand_a["meta"])
    label_b = pha._artifact_label(cand_b["meta"])
    pair_name = f"smart__{label_a}_X_{label_b}__{args.logic}__{args.normalize}".replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    write_invocation_files(
        out_dir,
        getattr(args, "invocation_argv", sys.argv),
        cwd=getattr(args, "invocation_cwd", os.getcwd()),
    )

    raw_thr_a = pha._artifact_threshold(cand_a["meta"])
    raw_thr_b = pha._artifact_threshold(cand_b["meta"])
    eff_actual = (
        args.actual_threshold if args.actual_threshold is not None
        else min(raw_thr_a, raw_thr_b)
    )

    val_a_rows = pha._read_rows(cand_a["meta"]["validation_combined_csv"], has_segment=True)
    val_b_rows = pha._read_rows(cand_b["meta"]["validation_combined_csv"], has_segment=True)
    aligned_val = pha._align_rows(val_a_rows, val_b_rows, has_segment=True)
    out_val = pha._build_output_rows(
        aligned_val,
        score_col=score_column,
        norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
        raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
        actual_threshold=eff_actual,
        threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
        threshold=sim["threshold"], logic=args.logic, alpha=args.alpha,
        has_segment=True,
    )
    val_csv = out_dir / f"{pair_name}__validation_combined.csv"
    pha._write_csv(str(val_csv), out_val, has_segment=True)

    out_forecast = []
    fc_csv = out_dir / f"{pair_name}__forecast.csv"
    fc_a = cand_a["meta"].get("forecast_csv")
    fc_b = cand_b["meta"].get("forecast_csv")
    if fc_a and fc_b and os.path.exists(fc_a) and os.path.exists(fc_b):
        rows_fc_a = pha._read_rows(fc_a, has_segment=False)
        rows_fc_b = pha._read_rows(fc_b, has_segment=False)
        aligned_fc = pha._align_rows(rows_fc_a, rows_fc_b, has_segment=False)
        out_forecast = pha._build_output_rows(
            aligned_fc,
            score_col=score_column,
            norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
            raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
            actual_threshold=eff_actual,
            threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
            threshold=sim["threshold"], logic=args.logic, alpha=args.alpha,
            has_segment=False,
        )
        out_forecast, peak_choice = choose_top_forecast_peaks(
            out_forecast, args, args.logic, args.alpha,
        )
        pha._write_csv(str(fc_csv), out_forecast, has_segment=False)
    else:
        peak_choice = {"enabled": False, "reason": "missing_forecast"}

    rules_a = pha._load_rules(cand_a["meta"])
    rules_b = pha._load_rules(cand_b["meta"])
    derived_rules = pha._derive_rules(
        cand_a["meta"], cand_b["meta"], rules_a, rules_b,
        logic=args.logic, max_rules=args.max_rules,
    )
    rules_path = out_dir / f"{pair_name}__derived_rules.json"
    with open(rules_path, "w") as fh:
        json.dump(derived_rules, fh, indent=2)
    source_bundle = write_source_bundle(
        out_dir, cand_a, cand_b, rules_a, rules_b,
        max_rules=max(1, args.max_rules),
        argv=getattr(args, "invocation_argv", None),
        cwd=getattr(args, "invocation_cwd", None),
    )

    # Calcola metriche dei singoli A e B per popolare il diagram correttamente
    a_solo = candidate_metrics_dict(cand_a["meta"], score_column,
                                    eff_actual, args.threshold)
    b_solo = candidate_metrics_dict(cand_b["meta"], score_column,
                                    eff_actual, args.threshold)
    summary = {
        "pair": f"{pair_name}\n[Used Logic: {args.logic.upper()} | Alpha: {args.alpha} | Norm: {args.normalize}]",
        "candidate_a": label_a,
        "candidate_b": label_b,
        "family_a": cand_a["family"],
        "family_b": cand_b["family"],
        "logic": args.logic,
        "normalization_requested": args.normalize,
        "normalize": args.normalize,
        "alpha": args.alpha,
        "threshold": sim["threshold"],
        "threshold_a": sim["threshold_a"],
        "threshold_b": sim["threshold_b"],
        "metrics": sim["metrics"],
        # Campi che _write_lineage_diagram si aspetta:
        "validation_metrics": sim["metrics"],
        "source_validation_metrics": {"a": a_solo, "b": b_solo},
        "disagreement": sim["disagreement"],
        "forecast_eval": (
            forecast_eval_from_values(
                [float(r.get("predicted", 0.0) or 0.0) for r in out_forecast],
                args,
            ) if out_forecast else sim["forecast_eval"]
        ),
        "forecast_eval_pre_peak_choice": sim["forecast_eval"],
        "forecast_peak_choice": peak_choice,
        "source_bundle": source_bundle,
    }
    summary_path = out_dir / f"{pair_name}__summary.json"
    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    cmp_png = out_dir / f"{pair_name}__lineage_comparison.png"
    try:
        pha._write_lineage_comparison_png(
            str(cmp_png), cand_a["meta"], cand_b["meta"],
            out_val, out_forecast, score_column=score_column, summary=summary,
        )
    except Exception as exc:
        print(f"  [warn] lineage_comparison failed: {exc}")

    diag_png = out_dir / f"{pair_name}__lineage_diagram.png"
    try:
        pha._write_lineage_diagram(str(diag_png), cand_a["meta"], cand_b["meta"], summary)
    except Exception as exc:
        print(f"  [warn] lineage_diagram failed: {exc}")

    result = {
        "summary": summary,
        "summary_json": str(summary_path),
        "validation_csv": str(val_csv),
        "forecast_csv": str(fc_csv) if out_forecast else None,
        "rules": str(rules_path),
        "comparison_png": str(cmp_png) if cmp_png.exists() else None,
        "diagram_png": str(diag_png) if diag_png.exists() else None,
    }
    publish_canonical_forecast_alias(out_dir, result, pair_name=pair_name)
    return result


def best_effort_double(args, candidates, shape_kwargs, cascade_log):
    """Quando la cascata non produce coppia valida: cerca DUE coppie distinte:
       - shape_winner: pair che minimizza n_peaks nel forecast (priorità a forma sana)
       - peak_winner:  pair che massimizza peak_strength del forecast (priorità al picco principale)

    Genera DUE folder gemelli con PNG/CSV/summary, e un summary globale che spiega.
    """
    bar = "=" * 72
    print(bar)
    print("BEST-EFFORT DOUBLE — cascata fallita, due output complementari")
    print(bar)
    if len(candidates) < 2:
        sys.exit("Meno di 2 candidati totali: impossibile generare neanche best-effort.")
    write_invocation_files(
        args.output_dir,
        getattr(args, "invocation_argv", sys.argv),
        cwd=getattr(args, "invocation_cwd", os.getcwd()),
    )

    # Pre-calc qualità di ogni candidato
    enriched = []
    for c in candidates:
        q = evaluate_candidate_quality(c, args.score_column, **shape_kwargs)
        fc_csv = c["meta"].get("forecast_csv")
        fc_preds = read_predictions(fc_csv, args.score_column) if fc_csv else []
        ps = peak_strength(fc_preds, args.prediction_threshold)
        metrics = candidate_metrics_dict(
            c["meta"], args.score_column,
            args.actual_threshold, args.prediction_threshold,
        )
        validation_score = metric_blend(metrics)
        source_sanity = source_sanity_score(q, metrics)
        enriched.append({
            "cand": c,
            "quality": q,
            "peak_strength": ps,
            "validation_score": validation_score,
            "validation_metrics": metrics,
            "source_sanity": source_sanity,
            "smart": c["info"].get("candidate_score", 0.0) * q["overall_quality"],
        })

    # CROSS-FAMILY FORZATO: ANALOG vs DIGITAL/INTERPRETABLE
    # ANALOG = {BANK}, DIGITAL = {LCS, HYBRID, KAN, KAN_HYBRID}
    ANALOG = {"BANK"}
    DIGITAL = {"LCS", "HYBRID", "KAN", "KAN_HYBRID"}

    def is_cross_family(ea, eb):
        fa, fb = ea["cand"]["family"], eb["cand"]["family"]
        return (fa in ANALOG and fb in DIGITAL) or (fb in ANALOG and fa in DIGITAL)

    def analog_digital(ea, eb):
        if ea["cand"]["family"] in ANALOG:
            return ea, eb
        return eb, ea

    def analog_shape_component(e):
        info_shape = e["cand"]["info"].get("shape_overall", e["quality"]["overall_quality"])
        return clamp01(0.60 * e["source_sanity"] + 0.25 * e["quality"]["overall_quality"] + 0.15 * info_shape)

    def analog_peak_component(e):
        info_peak = e["cand"]["info"].get("peak_score", e["peak_strength"])
        return clamp01(0.55 * e["peak_strength"] + 0.45 * info_peak)

    def digital_logic_component(e):
        cscore = clamp01(e["cand"]["info"].get("candidate_score", 0.0))
        return clamp01(0.40 * e["validation_score"] + 0.30 * cscore + 0.30 * e["source_sanity"])

    def pair_score_with_components(merge_score, ea, eb, preference):
        analog, digital = analog_digital(ea, eb)
        a_shape = analog_shape_component(analog)
        a_validation = analog["validation_score"]
        d_logic = digital_logic_component(digital)
        source_gate = min(analog["source_sanity"], digital["source_sanity"])
        if preference == "peak":
            a_peak = analog_peak_component(analog)
            score = (
                0.48 * merge_score
                + 0.24 * a_peak
                + 0.14 * a_validation
                + 0.08 * a_shape
                + 0.06 * d_logic
            )
        else:
            score = (
                0.42 * merge_score
                + 0.24 * a_shape
                + 0.22 * a_validation
                + 0.12 * d_logic
            )
        return clamp01(score * (0.20 + 0.80 * source_gate))

    logic_trials = [("and", 0.5), ("or", 0.5),
                    ("weighted", 0.35), ("weighted", 0.5), ("weighted", 0.75)]

    def best_pair_profile(ea, eb, preference):
        best = None
        for logic, alpha in logic_trials:
            profile = simulate_merge_profile(
                args, ea["cand"], eb["cand"], logic, alpha, shape_kwargs,
            )
            if profile is None:
                continue
            merge_score = merge_selection_score(profile, preference)
            score = pair_score_with_components(
                merge_score, ea, eb, preference,
            )
            profile["merge_selection_score"] = merge_score
            profile["component_adjusted_score"] = score
            item = (score, profile)
            if best is None or item[0] > best[0]:
                best = item
        return best

    n = len(enriched)
    shape_pairs = []
    peak_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            ea, eb = enriched[i], enriched[j]
            if not is_cross_family(ea, eb):
                continue
            shape_best = best_pair_profile(ea, eb, "shape")
            if shape_best is not None:
                shape_score, shape_profile = shape_best
                # Il best shape resta dominante, ma deve portarsi dietro validation
                # binaria e forecast sensato.
                shape_pairs.append((shape_score, ea, eb, shape_profile))
            peak_best = best_pair_profile(ea, eb, "peak")
            if peak_best is not None:
                peak_score, peak_profile_best = peak_best
                peak_pairs.append((peak_score, ea, eb, peak_profile_best))

    if not shape_pairs:
        sys.exit("Nessuna coppia cross-family (ANALOG⊗DIGITAL/INTERPRETABLE) disponibile.")
    shape_pairs.sort(key=lambda x: x[0], reverse=True)

    if not peak_pairs:
        peak_pairs = list(shape_pairs)
        print("  ⚠ Nessuna simulazione peak valida: uso il ranking shape come fallback")
    else:
        peak_pairs.sort(key=lambda x: x[0], reverse=True)

    s_score, s_a, s_b, s_profile = shape_pairs[0]

    def candidate_config_key(e, include_seed=False):
        meta = e["cand"]["meta"]
        key = (
            str(meta.get("bank", "")),
            str(meta.get("readout", "")),
        )
        if include_seed:
            key += (str(meta.get("seed", "")),)
        return key

    def pair_config_key(pair, include_seed=False):
        _, ea, eb, _ = pair
        return frozenset([
            candidate_config_key(ea, include_seed=include_seed),
            candidate_config_key(eb, include_seed=include_seed),
        ])

    def pair_analog_entry(pair):
        _, ea, eb, _ = pair
        analog, _digital = analog_digital(ea, eb)
        return analog

    shape_pair = shape_pairs[0]
    shape_analog_key = candidate_config_key(pair_analog_entry(shape_pair), include_seed=False)
    shape_pair_key = pair_config_key(shape_pair, include_seed=False)
    peak_pair = None
    diversity_reason = "peak_top"
    for candidate_pair in peak_pairs:
        if candidate_config_key(pair_analog_entry(candidate_pair), include_seed=False) != shape_analog_key:
            peak_pair = candidate_pair
            diversity_reason = "forced_different_analog_config"
            break
    if peak_pair is None:
        for candidate_pair in peak_pairs:
            if pair_config_key(candidate_pair, include_seed=False) != shape_pair_key:
                peak_pair = candidate_pair
                diversity_reason = "forced_different_pair_config"
                break
    if peak_pair is None:
        peak_pair = peak_pairs[0]
        diversity_reason = "fallback_same_config"

    p_score, p_a, p_b, p_profile = peak_pair
    if diversity_reason != "peak_top":
        print(f"  [diversity] peak_winner selection: {diversity_reason}")

    def unique_analog_entries(entries):
        seen = set()
        out = []
        for e in entries:
            if e["cand"]["family"] not in ANALOG:
                continue
            key = candidate_config_key(e, include_seed=False)
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
        return out

    analog_anchor_pool = unique_analog_entries([s_a, s_b, p_a, p_b])
    analog_anchor = None
    if analog_anchor_pool:
        analog_anchor = max(
            analog_anchor_pool,
            key=lambda e: (
                0.45 * analog_shape_component(e)
                + 0.35 * analog_peak_component(e)
                + 0.20 * e["validation_score"]
            ),
        )
        print("  [analog-anchor] candidata analogica forzabile: "
              f"{pha._artifact_label(analog_anchor['cand']['meta'])}")
    print(f"  shape_winner: {pha._artifact_label(s_a['cand']['meta'])}  ⊗  "
          f"{pha._artifact_label(s_b['cand']['meta'])}  shape_score={s_score:.3f}  "
          f"logic={s_profile['logic']} α={s_profile['alpha']:.2f}  "
          f"peaks={s_profile['peak_profile']['n_runs']} active={s_profile['peak_profile']['active_count']}")
    print(f"  peak_winner : {pha._artifact_label(p_a['cand']['meta'])}  ⊗  "
          f"{pha._artifact_label(p_b['cand']['meta'])}  peak_score={p_score:.3f}  "
          f"logic={p_profile['logic']} α={p_profile['alpha']:.2f}  "
          f"peaks={p_profile['peak_profile']['n_runs']} active={p_profile['peak_profile']['active_count']}")

    shape_component_lineage = [
        f"A: {pha._artifact_label(s_a['cand']['meta'])}",
        f"B: {pha._artifact_label(s_b['cand']['meta'])}",
        f"selected: {s_profile['logic']} alpha={s_profile['alpha']:.2f}",
    ]
    peak_component_lineage = [
        f"A: {pha._artifact_label(p_a['cand']['meta'])}",
        f"B: {pha._artifact_label(p_b['cand']['meta'])}",
        f"selected: {p_profile['logic']} alpha={p_profile['alpha']:.2f}",
    ]

    out_root = args.output_dir
    out_root.mkdir(parents=True, exist_ok=True)

    results = []
    for label, (a, b) in [("shape_winner", (s_a, s_b)), ("peak_winner", (p_a, p_b))]:
        sub = out_root / f"{label}_merge"
        if sub.exists():
            shutil.rmtree(sub, ignore_errors=True)
        sub.mkdir(parents=True, exist_ok=True)
        print(f"\n  [internal] {label}: calcolo persistente in {sub}")
        if args.auto_best_logic:
            pref = "peak" if label == "peak_winner" else "shape"
            res = run_auto_best_logic(args, a["cand"], b["cand"], sub,
                                      shape_kwargs, preference=pref)
        else:
            res = fuse_pair(a["cand"], b["cand"], args, sub, args.score_column)
        results.append({"label": label, "result": res})

    # FINAL COMBO: merge dei due merge (shape_winner_merge ⊗ peak_winner_merge)
    final_meta = {}
    if len(results) == 2:
        sw, pw = results[0]["result"], results[1]["result"]
        sw_meta = {
            "bank": "__shape_winner_merge__",
            "readout": "shape_winner",
            "seed": -1,
            "display_label": "shape_winner merge",
            "component_lineage": shape_component_lineage,
            "validation_combined_csv": sw["validation_csv"],
            "forecast_csv": sw["forecast_csv"],
            "actual_threshold": pha._artifact_threshold({}, fallback=args.prediction_threshold),
            "prediction_threshold": args.threshold,
        }
        pw_meta = {
            "bank": "__peak_winner_merge__",
            "readout": "peak_winner",
            "seed": -2,
            "display_label": "peak_winner merge",
            "component_lineage": peak_component_lineage,
            "validation_combined_csv": pw["validation_csv"],
            "forecast_csv": pw["forecast_csv"],
            "actual_threshold": pha._artifact_threshold({}, fallback=args.prediction_threshold),
            "prediction_threshold": args.threshold,
        }
        sw_cand = {"meta": sw_meta, "family": "MERGE_SHAPE",
                   "info": {"candidate_score": s_score}, "path": sw["validation_csv"]}
        pw_cand = {"meta": pw_meta, "family": "MERGE_PEAK",
                   "info": {"candidate_score": p_score}, "path": pw["validation_csv"]}
        final_dir = out_root / "smart_result"
        final_dir.mkdir(exist_ok=True)
        print(f"\n  → smart_result: fusione a due stadi shape⊗peak in {final_dir}")
        try:
            sw_runs = sw.get("summary", {}).get("forecast_peak_choice", {}).get("after", {}).get("n_runs", 0)
            if not sw_runs:
                sw_runs = sw.get("summary", {}).get("forecast_peak_choice", {}).get("before", {}).get("n_runs", 0)
            pw_runs = pw.get("summary", {}).get("forecast_peak_choice", {}).get("after", {}).get("n_runs", 0)
            if not pw_runs:
                pw_runs = pw.get("summary", {}).get("forecast_peak_choice", {}).get("before", {}).get("n_runs", 0)

            final_args = argparse.Namespace(**vars(args))
            final_shape_kwargs = dict(shape_kwargs)
            requested_final_peak_max = int(getattr(args, "final_peak_max", 0) or 0)
            force_single_peak_or = requested_final_peak_max <= 0 and sw_runs == 1 and pw_runs == 1
            if requested_final_peak_max > 0:
                print(f"  [info] final combo: max picchi forzato a {requested_final_peak_max}.")
                final_args.max_peaks = requested_final_peak_max
                final_args.peak_max = requested_final_peak_max
                final_shape_kwargs["max_peaks"] = requested_final_peak_max
            elif force_single_peak_or:
                print("  [info] shape_winner e peak_winner hanno 1 picco a testa: ammetto 2 picchi e provo logica OR per final combo.")
                final_args.max_peaks = 2
                final_args.peak_max = 2
                final_shape_kwargs["max_peaks"] = 2
                final_args.logic = "or"
                # Volendo potremmo bypassare l'auto se volessimo solo "or", ma lo testiamo
            
            if args.auto_best_logic and not force_single_peak_or:
                stage_dir = final_dir / "shape_peak_stage"
                if stage_dir.exists():
                    shutil.rmtree(stage_dir, ignore_errors=True)
                stage_dir.mkdir(parents=True, exist_ok=True)
                final_res = run_auto_best_logic(final_args, sw_cand, pw_cand, stage_dir,
                                                final_shape_kwargs, preference="final")
            else:
                stage_dir = final_dir / "shape_peak_stage"
                if stage_dir.exists():
                    shutil.rmtree(stage_dir, ignore_errors=True)
                stage_dir.mkdir(parents=True, exist_ok=True)
                final_res = fuse_pair(sw_cand, pw_cand, final_args, stage_dir, final_args.score_column)

            shape_peak_stage_res = final_res
            if analog_anchor is not None and final_res.get("validation_csv") and final_res.get("forecast_csv"):
                analog_dir = final_dir / "analog_forced_final"
                if analog_dir.exists():
                    shutil.rmtree(analog_dir, ignore_errors=True)
                analog_dir.mkdir(parents=True, exist_ok=True)
                print("  [analog-anchor] final combo forzato con candidata analogica: "
                      f"{pha._artifact_label(analog_anchor['cand']['meta'])}")
                stage_component_lineage = [
                    "shape: " + " | ".join(shape_component_lineage[:2]),
                    "peak: " + " | ".join(peak_component_lineage[:2]),
                    f"anchor: {pha._artifact_label(analog_anchor['cand']['meta'])}",
                ]
                stage_meta = {
                    "bank": "__shape_peak_merge__",
                    "readout": "shape_peak_stage",
                    "seed": -3,
                    "display_label": "shape_peak stage",
                    "component_lineage": stage_component_lineage,
                    "validation_combined_csv": final_res["validation_csv"],
                    "forecast_csv": final_res["forecast_csv"],
                    "actual_threshold": pha._artifact_threshold({}, fallback=args.prediction_threshold),
                    "prediction_threshold": args.threshold,
                }
                stage_cand = {
                    "meta": stage_meta,
                    "family": "MERGE_FINAL_STAGE",
                    "info": {"candidate_score": final_res["summary"].get("merge_quality", 0.0)},
                    "path": final_res["validation_csv"],
                }
                if args.auto_best_logic and not force_single_peak_or:
                    final_res = run_auto_best_logic(
                        final_args, stage_cand, analog_anchor["cand"], analog_dir,
                        final_shape_kwargs, preference="final",
                    )
                else:
                    final_res = fuse_pair(
                        stage_cand, analog_anchor["cand"], final_args,
                        analog_dir, final_args.score_column,
                    )
                final_res["summary"]["forced_analog_anchor"] = {
                    "enabled": True,
                    "label": pha._artifact_label(analog_anchor["cand"]["meta"]),
                    "family": analog_anchor["cand"]["family"],
                    "bank": analog_anchor["cand"]["meta"].get("bank"),
                    "readout": analog_anchor["cand"]["meta"].get("readout"),
                    "seed": analog_anchor["cand"]["meta"].get("seed"),
                    "stage_summary_json": shape_peak_stage_res.get("summary_json"),
                    "stage_forecast_csv": shape_peak_stage_res.get("forecast_csv"),
                }
            elif analog_anchor is None:
                final_res["summary"]["forced_analog_anchor"] = {
                    "enabled": False,
                    "reason": "no_analog_candidate_available",
                }

            # delta vs le sorgenti originali vere (s_a, s_b)
            orig_a = candidate_metrics_dict(s_a["cand"]["meta"], args.score_column, args.actual_threshold, args.prediction_threshold)
            orig_b = candidate_metrics_dict(s_b["cand"]["meta"], args.score_column, args.actual_threshold, args.prediction_threshold)
            final_delta = metrics_delta_report(
                final_res["summary"]["metrics"], orig_a, orig_b
            )
            print("  Δ smart_result vs sorgenti originali A e B:")
            print(final_delta)
            with open(final_dir / "metrics_delta.txt", "w") as fh:
                fh.write(final_delta + "\n")

            final_res["summary"]["bar_chart_mode"] = "dual_source"
            final_res["summary"]["bar_chart_title"] = "Smart merge vs original sources"
            final_res["summary"]["bar_chart_source_a_metrics"] = orig_a
            final_res["summary"]["bar_chart_source_a_label"] = pha._artifact_label(s_a["cand"]["meta"])
            final_res["summary"]["bar_chart_source_b_metrics"] = orig_b
            final_res["summary"]["bar_chart_source_b_label"] = pha._artifact_label(s_b["cand"]["meta"])
            final_res["summary"]["bar_chart_current_label"] = "Smart merge"
            final_res["summary"]["bar_chart_current_metrics"] = (
                final_res["summary"].get("validation_metrics") or final_res["summary"]["metrics"]
            )
            final_res["summary"]["result_delta_label"] = "Δ vs original sources (A / B):"
            final_res["summary"]["forecast_note"] = (
                "Two-stage internal merge (shape-best ⊗ peak-best); "
                "chart compares result against the true original sources."
            )
            if final_res.get("diagram_png"):
                pha._write_lineage_diagram(
                    final_res["diagram_png"],
                    s_a["cand"]["meta"],
                    s_b["cand"]["meta"],
                    final_res["summary"],
                )
            if final_res.get("summary_json"):
                with open(final_res["summary_json"], "w") as fh:
                    json.dump(final_res["summary"], fh, indent=2, default=str)
            publish_canonical_forecast_alias(final_dir, final_res)
            if final_res.get("canonical_forecast_csv"):
                top_alias = out_root / "smart_fusion_final__forecast.csv"
                shutil.copy2(final_res["canonical_forecast_csv"], top_alias)
            final_meta = {
                "lineage_comparison_png": final_res.get("comparison_png"),
                "lineage_diagram_png": final_res.get("diagram_png"),
                "forecast_csv": final_res.get("forecast_csv"),
                "canonical_forecast_csv": final_res.get("canonical_forecast_csv"),
                "shape_peak_stage": {
                    "summary_json": shape_peak_stage_res.get("summary_json"),
                    "forecast_csv": shape_peak_stage_res.get("forecast_csv"),
                    "comparison_png": shape_peak_stage_res.get("comparison_png"),
                },
                "forced_analog_anchor": final_res["summary"].get("forced_analog_anchor"),
                "metrics": final_res["summary"]["metrics"],
                "selected_logic": final_res.get("selected_logic", final_res["summary"].get("logic")),
                "selected_alpha": final_res.get("selected_alpha", final_res["summary"].get("alpha")),
                "forecast_peak_choice": final_res["summary"].get("forecast_peak_choice"),
            }
        except Exception as exc:
            print(f"  [warn] smart_result fallito: {exc}")
            final_meta = {"error": str(exc)}

    shape_result = results[0]["result"] if len(results) > 0 else {}
    peak_result = results[1]["result"] if len(results) > 1 else {}
    summary = {
        "mode": "best_effort_double",
        "cascade_log": cascade_log + ["best_effort"],
        "reason": "Nessuna coppia primaria/cascade ha prodotto merge valido.",
        "constraint": "cross-family ANALOG{BANK} ⊗ DIGITAL{LCS,HYBRID,KAN,KAN_HYBRID} forced",
        "peak_winner_diversity_reason": diversity_reason,
        "forced_analog_anchor_label": (
            pha._artifact_label(analog_anchor["cand"]["meta"]) if analog_anchor is not None else None
        ),
        "shape_winner": {
            "a": pha._artifact_label(s_a["cand"]["meta"]),
            "a_family": s_a["cand"]["family"],
            "b": pha._artifact_label(s_b["cand"]["meta"]),
            "b_family": s_b["cand"]["family"],
            "shape_score": s_score,
            "ranking_logic": s_profile["logic"],
            "ranking_alpha": s_profile["alpha"],
            "selected_logic": shape_result.get("selected_logic", s_profile["logic"]),
            "selected_alpha": shape_result.get("selected_alpha", s_profile["alpha"]),
            "forecast_peaks": (
                shape_result.get("summary", {}).get("forecast_peak_choice", {}).get("after")
                or shape_result.get("summary", {}).get("forecast_peak_choice", {}).get("before")
                or s_profile["peak_profile"]
            ),
            "validation_metrics": shape_result.get("summary", {}).get(
                "metrics", s_profile["sim"]["metrics"],
            ),
        },
        "peak_winner": {
            "a": pha._artifact_label(p_a["cand"]["meta"]),
            "a_family": p_a["cand"]["family"],
            "b": pha._artifact_label(p_b["cand"]["meta"]),
            "b_family": p_b["cand"]["family"],
            "peak_score": p_score,
            "ranking_logic": p_profile["logic"],
            "ranking_alpha": p_profile["alpha"],
            "selected_logic": peak_result.get("selected_logic", p_profile["logic"]),
            "selected_alpha": peak_result.get("selected_alpha", p_profile["alpha"]),
            "forecast_peaks": (
                peak_result.get("summary", {}).get("forecast_peak_choice", {}).get("after")
                or peak_result.get("summary", {}).get("forecast_peak_choice", {}).get("before")
                or p_profile["peak_profile"]
            ),
            "validation_metrics": peak_result.get("summary", {}).get(
                "metrics", p_profile["sim"]["metrics"],
            ),
        },
        "smart_result": final_meta,
    }
    with open(out_root / "best_effort_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2, default=str)
    print(f"\n  Summary: {out_root / 'best_effort_summary.json'}")


def run_auto_best_logic(args, cand_a, cand_b, out_dir, shape_kwargs,
                        preference="shape"):
    """Estrae la logica di auto-best-logic in funzione standalone (riusabile)."""
    import tempfile, shutil
    combos = [("and", 0.5), ("or", 0.5),
              ("weighted", 0.35), ("weighted", 0.5), ("weighted", 0.75)]
    tried = []
    for logic, alpha in combos:
        tmp = Path(tempfile.mkdtemp(prefix=f"smart_try_{logic}_a{alpha}_"))
        args_try = argparse.Namespace(**vars(args))
        args_try.logic = logic
        args_try.alpha = alpha
        try:
            r = fuse_pair(cand_a, cand_b, args_try, tmp, args.score_column)
        except SystemExit:
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        mv = read_predictions(r["validation_csv"], "predicted")
        rows_fc = pha._read_rows(r["forecast_csv"], has_segment=False) if r["forecast_csv"] else []
        # Se peak_and + logic and: sovrascrivi le predizioni del forecast con peak overlap
        # prima di valutare fc_q, così il punteggio riflette la logica corretta.
        # Semantica --peak-window N: prova window=0,1,...,N in cascata, usa il primo
        # che trova almeno 1 overlap. Se nessuno trova overlap → fallback automatico a or.
        if getattr(args, "peak_and", False) and logic == "and" and rows_fc:
            fc_sa = [float(row.get("a_score") or 0.0) for row in rows_fc]
            fc_sb = [float(row.get("b_score") or 0.0) for row in rows_fc]
            floor = getattr(args, "peak_floor", 0.30)
            max_win = getattr(args, "peak_window", 1)
            max_peaks = getattr(args, "peak_max", 1)
            peak_pred = None
            used_window = None
            for w in range(max_win + 1):
                candidate, _ = _peak_overlap_combine(
                    fc_sa, fc_sb,
                    threshold=args.threshold, alpha=alpha,
                    window=w, floor=floor, max_peaks=max_peaks,
                )
                if sum(candidate) > 0:
                    peak_pred = candidate
                    used_window = w
                    break
            if peak_pred is None or sum(peak_pred) == 0:
                # Nessun overlap AND → fallback peak-OR (rank self-norm, top max_peaks)
                or_pred, _ = _peak_or_select(
                    fc_sa, fc_sb,
                    floor=floor, max_peaks=max_peaks, window=max_win, alpha=alpha,
                )
                if or_pred is not None and sum(or_pred) > 0:
                    peak_pred = or_pred
                    used_window = "or_peak"
                else:
                    # Nessun picco affatto → threshold-OR puro
                    thr = float(args.threshold)
                    peak_pred = [1.0 if (sa >= thr or sb >= thr) else 0.0
                                 for sa, sb in zip(fc_sa, fc_sb)]
                    used_window = "or_thr"
            if used_window not in ("or_peak", "or_thr"):
                print(f"      [peak_and] overlap trovato a window={used_window} → "
                      f"{int(sum(peak_pred))} punto/i attivi")
            elif used_window == "or_peak":
                print(f"      [peak_and] nessun overlap AND → fallback OR picchi "
                      f"({int(sum(peak_pred))} attivi)")
            else:
                print(f"      [peak_and] nessun picco → fallback OR threshold")
            for row, pp in zip(rows_fc, peak_pred):
                row["predicted"] = pp
                row["_predicted"] = pp
            if r["forecast_csv"]:
                _write_rows_csv(r["forecast_csv"], rows_fc)
            # Rigenera il PNG con le predizioni peak_and aggiornate
            if r.get("comparison_png"):
                try:
                    out_val_png = (pha._read_rows(r["validation_csv"], has_segment=False)
                                   if r.get("validation_csv") else [])
                    pha._write_lineage_comparison_png(
                        r["comparison_png"],
                        cand_a["meta"], cand_b["meta"],
                        out_val_png, rows_fc,
                        score_column=args.score_column,
                        summary=r["summary"],
                    )
                except Exception as exc:
                    print(f"  [warn] lineage_comparison peak regen: {exc}")
        mf = [float(row.get("_predicted") or row.get("predicted") or 0.0) for row in rows_fc]
        mvq, _ = shape_quality(mv, enforce_peak_limit=False, **shape_kwargs)
        mfq, _ = shape_quality(mf, enforce_peak_limit=True, **shape_kwargs)
        combo_q = mvq * 0.4 + mfq * 0.6
        f1 = r["summary"]["metrics"].get("f1", 0)
        recall = r["summary"]["metrics"].get("recall", 0)
        bal = r["summary"]["metrics"].get("bal_acc", 0)
        conf = []
        for row in rows_fc:
            try:
                sa = float(row.get("a_score", 0.0) or 0.0)
                sb = float(row.get("b_score", 0.0) or 0.0)
            except Exception:
                sa, sb = 0.0, 0.0
            conf.append(merge_confidence(sa, sb, logic, alpha))
        prof = peak_profile(
            mf, conf, threshold=args.prediction_threshold,
            max_consecutive=args.max_consecutive,
        )
        score_profile = {
            "forecast_quality": mfq,
            "metrics_score": metric_blend(r["summary"]["metrics"]),
            "peak_signal": clamp01(
                0.65 * prof["top_confidence"]
                + 0.25 * peak_strength(conf, args.prediction_threshold)
                + 0.10 * peak_count_fit(prof, args.max_peaks)
            ),
            "peak_profile": prof,
            "sim": {"forecast_eval": r["summary"].get("forecast_eval", {})},
            "max_peaks": args.max_peaks,
        }
        auto_score = merge_selection_score(score_profile, preference)
        print(f"    {logic:>8s} α={alpha:.2f}  val_q={mvq:.3f} fc_q={mfq:.3f}  "
              f"auto={auto_score:.3f}  peaks={prof['n_runs']} active={prof['active_count']}/{len(mf)}  "
              f"f1={f1:.3f} r={recall:.3f} bal={bal:.3f}")
        tried.append((auto_score, combo_q, logic, alpha, tmp, r, mvq, mfq))
    if not tried:
        sys.exit("Nessuna logica ha prodotto un merge valido.")
    # Con peak_and attivo: se almeno un combo AND ha trovato overlap (mfq>0)
    # forza la selezione solo tra combo AND — così peak_winner e shape_winner
    # usano entrambi l'AND confermato, non l'OR che attiva picchi non confermati.
    if getattr(args, "peak_and", False):
        and_tried = [(s, q, l, a, t, r2, mv, mf)
                     for s, q, l, a, t, r2, mv, mf in tried if l == "and"]
        if and_tried and any(mf > 0 for *_, mf in and_tried):
            tried = and_tried
    tried.sort(key=lambda x: x[0], reverse=True)
    auto_score, combo_q, logic, alpha, tmp, r, mvq, mfq = tried[0]
    print(f"    ★ {logic} α={alpha} auto={auto_score:.3f} combo_q={combo_q:.3f} preference={preference}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in tmp.iterdir():
        dest = out_dir / f.name
        if f.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(f, dest)
        else:
            shutil.copy2(f, dest)
    for _, _, _, _, t, *_ in tried:
        shutil.rmtree(t, ignore_errors=True)
    for k, v in list(r.items()):
        if isinstance(v, str) and str(tmp) in v:
            r[k] = v.replace(str(tmp), str(out_dir))
    r["selected_logic"] = logic
    r["selected_alpha"] = alpha
    r["selected_auto_score"] = auto_score
    r["selected_preference"] = preference
    r["merge_val_quality"] = mvq
    r["merge_fc_quality"] = mfq
    publish_canonical_forecast_alias(out_dir, r)
    return r


def main():
    ap = argparse.ArgumentParser(
        description="Ensemble smart: 1 analog + 1 interpretable/digital backend, best overall + shape filter.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--dataset-subfolder",
                    default="master_with_usgs_core_astrofmt_reduced")
    ap.add_argument("--out-dir", default=None,
                    help="Directory output assoluta/relativa. Se impostata ha priorita' su --out-subdir.")
    ap.add_argument("--out-subdir", default=None,
                    help="Cartella output sotto run_dir. Se omesso crea "
                         "post_hybrid_checks_smart_<timestamp>_<seriale>.")

    # Famiglie scelte (default 1 BANK + 1 LCS)
    ap.add_argument("--family-a", default="BANK",
                    choices=["BANK", "LCS", "HYBRID", "KAN", "KAN_HYBRID", "END_TO_END"])
    ap.add_argument("--family-b", default="LCS",
                    choices=["BANK", "LCS", "HYBRID", "KAN", "KAN_HYBRID", "END_TO_END"])
    ap.add_argument("--cascade", action="store_true", default=True,
                    help="Cascata: se BANK⊗LCS non valido prova BANK⊗HYBRID, "
                         "poi best-effort doppio (shape + peak winner)")
    ap.add_argument("--no-cascade", dest="cascade", action="store_false")
    ap.add_argument("--cascade-min-merge-quality", type=parse_float_or_auto, default="auto",
                    help="Sotto questo merge_quality scatta il prossimo livello cascata; usa auto per soglia adattiva")

    # Shape penalty
    ap.add_argument("--prediction-threshold", type=float, default=0.5)
    ap.add_argument("--flat-range-threshold", type=float, default=0.3,
                    help="Range max-min minimo per non essere considerato flat")
    ap.add_argument("--saturated-max-ratio", type=float, default=0.6,
                    help="Max frazione di punti sopra threshold prima di penalty")
    ap.add_argument("--stuck-max-ratio", type=float, default=0.5,
                    help="Max frazione di run identici consecutivi prima di penalty")
    ap.add_argument("--neutral-band", type=float, default=0.10,
                    help="Banda ±N attorno a prediction_threshold (es. 0.10 → 0.40..0.60). "
                         "Run lunghe in questa banda = modello indeciso, penalizzato.")
    ap.add_argument("--neutral-band-max-ratio", type=float, default=0.25,
                    help="Max frazione di run consecutiva nella neutral-band prima di penalty")
    ap.add_argument("--max-peaks", type=int, default=1,
                    help="N° massimo di picchi accettati nel forecast (default 1 = trova IL picco maggiore)")
    ap.add_argument("--max-consecutive", type=int, default=2,
                    help="N° massimo di valori alti consecutivi che formano UN picco (default 2). "
                         "Run più lunghe diventano 'plateau' e penalizzano la quality.")
    ap.add_argument("--min-quality", type=float, default=0.3,
                    help="Quality minima per accettare un candidato (0..1)")

    # Fusione
    ap.add_argument("--logic", default="and", choices=["and", "or", "weighted"])
    ap.add_argument("--normalize", default="auto",
                    choices=["auto", "minmax", "zscore", "rank", "binary"])
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--calibrate-mode", default="threshold_search")
    ap.add_argument("--calibrate-metric", default="f1")
    ap.add_argument("--min-recall", type=float, default=0.0)
    ap.add_argument("--actual-threshold", type=float, default=None)
    ap.add_argument("--score-column", default="pred")

    ap.add_argument("--forecast-guard", default="off",
                    choices=["off", "soft", "strict"])
    ap.add_argument("--forecast-flat-eps", type=float, default=1e-6)
    ap.add_argument("--forecast-high-ratio", type=float, default=0.8)
    ap.add_argument("--max-rules", type=int, default=20)
    ap.add_argument("--auto-best-logic", action="store_true", default=True,
                    help="Prova and/or/weighted×3α e tiene la combo con merge_quality più alta")
    ap.add_argument("--no-auto-best-logic", dest="auto_best_logic", action="store_false")
    ap.add_argument("--peak-and", action="store_true", default=False,
                    help="Usa overlap di picchi locali per la logica 'and' nel forecast invece "
                         "di threshold-AND punto per punto. Più sensibile per segnali con picco "
                         "pronunciato che non supera la soglia su entrambi i candidati.")
    ap.add_argument("--peak-window", type=int, default=1,
                    help="Finestra MASSIMA da provare (cascata 0→N): prova window=0 prima, "
                         "poi 1, ..., fino a N. Usa il primo che trova overlap. "
                         "Se nessuno trova overlap → fallback automatico a or. Default=1.")
    ap.add_argument("--peak-floor", type=float, default=0.30,
                    help="Frazione del proprio range [0,1] sotto cui un punto NON è picco (self-norm). "
                         "0.30 = solo il top 70%% della variazione del segnale. Default=0.30.")
    ap.add_argument("--peak-max", type=int, default=1,
                    help="Numero massimo di picchi da tenere nell'output (AND o OR fallback). "
                         "Rank per self-norm strength within-signal: top N centri attivati. "
                         "Default=1 (comportamento precedente). 2 = cerca fino a 2 picchi.")
    ap.add_argument("--final-peak-max", type=int, default=0,
                    help="Numero massimo di picchi nel final combo shape⊗peak; 0 = usa la logica automatica.")
    args = ap.parse_args()
    args.invocation_argv = [sys.executable] + list(sys.argv)
    args.invocation_cwd = os.getcwd()

    if not args.run_dir.exists():
        sys.exit(f"run_dir non esiste: {args.run_dir}")
    if args.out_dir:
        args.output_dir = Path(args.out_dir)
        args.out_subdir = args.output_dir.name
    elif args.out_subdir:
        args.output_dir = args.run_dir / args.out_subdir
    else:
        args.output_dir = unique_output_dir(args.run_dir, "post_hybrid_checks_smart")
        args.out_subdir = args.output_dir.name

    bar = "=" * 72
    print(bar)
    print("POST-HYBRID PAIR SMART — selezione con shape filter")
    print(bar)
    print(f"  run_dir              : {args.run_dir}")
    print(f"  dataset subfolder    : {args.dataset_subfolder}")
    print(f"  output dir           : {args.output_dir}")
    print(f"  pair                 : {args.family_a} ⊗ {args.family_b}")
    print(f"  prediction threshold : {args.prediction_threshold}")
    print(f"  flat range thresh    : {args.flat_range_threshold}")
    print(f"  saturated max ratio  : {args.saturated_max_ratio}")
    print(f"  stuck max ratio      : {args.stuck_max_ratio}")
    print(f"  max peaks (forecast) : {args.max_peaks}")
    print(f"  max consec per peak  : {args.max_consecutive}  (run più lunghe → plateau)")
    print(f"  min quality          : {args.min_quality}")
    print(f"  logic / normalize    : {args.logic} / {args.normalize}")
    print(bar)

    candidates = discover_all_candidates(
        args.run_dir, args.dataset_subfolder, args.score_column,
        args.forecast_guard, args.forecast_flat_eps, args.forecast_high_ratio,
    )
    print(f"\nTotale candidati scoperti: {len(candidates)}")
    fam_counts = {}
    for c in candidates:
        fam_counts[c["family"]] = fam_counts.get(c["family"], 0) + 1
    for f, n in sorted(fam_counts.items()):
        print(f"  {f}: {n}")

    shape_kwargs = dict(
        prediction_threshold=args.prediction_threshold,
        flat_range_threshold=args.flat_range_threshold,
        saturated_max_ratio=args.saturated_max_ratio,
        stuck_max_ratio=args.stuck_max_ratio,
        neutral_band=args.neutral_band,
        neutral_band_max_ratio=args.neutral_band_max_ratio,
        max_peaks=args.max_peaks,
        max_consecutive=args.max_consecutive,
    )

    def try_combo(fam_a, fam_b, label):
        ba, _ = select_best_in_family(
            candidates, fam_a, min_quality=args.min_quality,
            score_column=args.score_column, shape_kwargs=shape_kwargs,
            actual_threshold=args.actual_threshold,
            prediction_threshold=args.prediction_threshold,
            verbose=(label == "primary"),
        )
        bb, _ = select_best_in_family(
            candidates, fam_b, min_quality=args.min_quality,
            score_column=args.score_column, shape_kwargs=shape_kwargs,
            actual_threshold=args.actual_threshold,
            prediction_threshold=args.prediction_threshold,
            verbose=(label == "primary"),
        )
        return ba, bb

    best_a, best_b = try_combo(args.family_a, args.family_b, "primary")
    chosen_pair_label = f"{args.family_a}⊗{args.family_b}"
    cascade_log = [chosen_pair_label]

    if args.cascade and (best_a is None or best_b is None):
        print(f"\n[cascade] {chosen_pair_label} ha famiglie vuote, provo BANK⊗HYBRID")
        best_a, best_b = try_combo("BANK", "HYBRID", "cascade1")
        chosen_pair_label = "BANK⊗HYBRID"
        cascade_log.append(chosen_pair_label)

    if best_a is None or best_b is None:
        if args.cascade:
            print(f"\n[cascade] anche cascade fallisce su famiglie vuote → vado in best-effort doppio")
            return best_effort_double(args, candidates, shape_kwargs, cascade_log)
        sys.exit(f"Famiglia {args.family_a} o {args.family_b} senza candidati.")

    print(bar)
    print("SCELTI:")
    print(f"  {args.family_a}  →  {pha._artifact_label(best_a['cand']['meta'])}")
    print(f"            smart={best_a['smart_score']:+.4f}  qual={best_a['quality']['overall_quality']:.3f}")
    print(f"  {args.family_b}  →  {pha._artifact_label(best_b['cand']['meta'])}")
    print(f"            smart={best_b['smart_score']:+.4f}  qual={best_b['quality']['overall_quality']:.3f}")
    print(bar)

    cascade_threshold = resolve_cascade_threshold(best_a, best_b, args.cascade_min_merge_quality)
    args.cascade_min_merge_quality_resolved = cascade_threshold["resolved"]
    if args.cascade:
        if cascade_threshold["mode"] == "auto":
            comps = cascade_threshold["components"]
            print(
                "  auto cascade threshold resolved="
                f"{cascade_threshold['resolved']:.3f}  "
                f"(avg_quality={comps['avg_quality']:.3f} avg_validation={comps['avg_validation']:.3f} "
                f"min_sanity={comps['min_sanity']:.3f} avg_smart={comps['avg_smart']:.3f})"
            )
        else:
            print(f"  cascade threshold      : {cascade_threshold['resolved']:.3f}")
        print(bar)

    out_dir = args.output_dir
    write_invocation_files(out_dir, args.invocation_argv, cwd=args.invocation_cwd)

    if args.auto_best_logic:
        print(bar)
        print(f"AUTO-BEST-LOGIC: provo 5 combo, tengo la migliore per merge_quality")
        print(bar)
        res = run_auto_best_logic(args, best_a["cand"], best_b["cand"], out_dir,
                                  shape_kwargs, preference="final")
        merge_val_q = res.get("merge_val_quality", 0.0)
        merge_fc_q = res.get("merge_fc_quality", 0.0)
        args.logic = res.get("selected_logic", args.logic)
        args.alpha = res.get("selected_alpha", args.alpha)
    else:
        res = fuse_pair(best_a["cand"], best_b["cand"], args, out_dir, args.score_column)
        merge_val = read_predictions(res["validation_csv"], "predicted")
        merge_fc = read_predictions(res["forecast_csv"], "predicted") if res["forecast_csv"] else []
        merge_val_q, _ = shape_quality(merge_val, enforce_peak_limit=False, **shape_kwargs)
        merge_fc_q, _ = shape_quality(merge_fc, enforce_peak_limit=True, **shape_kwargs)

    combo_q_final = merge_val_q * 0.4 + merge_fc_q * 0.6
    if args.cascade and combo_q_final < args.cascade_min_merge_quality_resolved:
        print(f"\n[cascade] merge {chosen_pair_label} combo_q={combo_q_final:.3f} "
              f"< {args.cascade_min_merge_quality_resolved:.3f} → trigger best-effort doppio")
        # cleanup output incompleto
        import shutil
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        return best_effort_double(args, candidates, shape_kwargs, cascade_log)

    # Delta report: merge vs A vs B
    a_metrics = candidate_metrics_dict(best_a["cand"]["meta"], args.score_column,
                                       args.actual_threshold, args.prediction_threshold)
    b_metrics = candidate_metrics_dict(best_b["cand"]["meta"], args.score_column,
                                       args.actual_threshold, args.prediction_threshold)
    delta = metrics_delta_report(res["summary"]["metrics"], a_metrics, b_metrics)
    print()
    print(bar)
    print("DELTA METRICHE  (merge vs candidato A vs candidato B)")
    print(bar)
    print(delta)
    with open(out_dir / "metrics_delta.txt", "w") as fh:
        fh.write(delta)

    print()
    print(bar)
    print("DONE")
    print(bar)
    print(f"  out_dir          : {out_dir}")
    print(f"  pair             : {res['summary']['pair']}")
    print(f"  metrics          : {res['summary']['metrics']}")
    print(f"  threshold        : {res['summary']['threshold']:.4f}  "
          f"(A={res['summary']['threshold_a']:.4f}  B={res['summary']['threshold_b']:.4f})")
    print(f"  merge val quality: {merge_val_q:.3f}")
    print(f"  merge fc  quality: {merge_fc_q:.3f}")
    if res.get("comparison_png"):
        print(f"  comparison       : {res['comparison_png']}")
    if res.get("diagram_png"):
        print(f"  diagram          : {res['diagram_png']}")
    print(bar)


if __name__ == "__main__":
    main()

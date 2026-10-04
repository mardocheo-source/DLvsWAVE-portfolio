#!/usr/bin/env python3
"""Fonde DUE artifact espliciti in una cartella `post_hybrid_checks_special/`.

Esempio:
    python3 post_hybrid_pair_special.py \\
      /path/to/pulsar_train-max_best_trials_<ts> \\
      --candidate-a "passthrough__torch_tiny__seed4" \\
      --candidate-b "hyb_default_dntiny_w0p50__seed5"

I "candidate-*" sono substring matchati contro il nome del file `*__test.json`
trovato dentro `<run_dir>/<dataset_subfolder>/` o `<run_dir>/best_by_bank/<dataset_subfolder>/`.
Se i match non sono unici lo script lista cosa ha trovato e si ferma.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_hybrid_artifacts as pha


def find_candidate(run_dir, dataset_subfolder, pattern):
    """Cerca prima *test.json, poi (fallback) *test.csv e ricostruisce un meta sintetico."""
    search_dirs = [
        run_dir / dataset_subfolder,
        run_dir / "best_by_bank" / dataset_subfolder,
        run_dir / "best_by_bank" / "recent_validation" / dataset_subfolder,
    ]
    matches = []
    seen_basenames = set()
    # primo passaggio: file JSON veri
    for d in search_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*__test.json")):
            if pattern not in p.name:
                continue
            if p.name in seen_basenames:
                continue
            seen_basenames.add(p.name)
            matches.append(("json", p))
    if matches:
        return matches
    # fallback: file CSV → meta sintetico
    for d in search_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*__test.csv")):
            if pattern not in p.name:
                continue
            if p.name in seen_basenames:
                continue
            seen_basenames.add(p.name)
            matches.append(("csv", p))
    return matches


def synthesize_meta_from_csv(test_csv_path):
    """Costruisce un meta dict minimo a partire dal *test.csv (i path correlati per
    nome convenzione: <stem>__validation_combined.csv, <stem>__forecast.csv)."""
    base = test_csv_path.parent
    stem = test_csv_path.name[:-len("__test.csv")]
    val = base / f"{stem}__test__validation_combined.csv"
    fc = base / f"{stem}__forecast.csv"
    if not val.exists():
        return None
    parts = stem.split("__")
    score = parts[0] if parts and parts[0].replace(".", "").isdigit() else ""
    bank = parts[1] if len(parts) > 1 else ""
    readout = parts[2] if len(parts) > 2 else ""
    seed_str = parts[3] if len(parts) > 3 else "seed?"
    seed = int(seed_str.replace("seed", "")) if seed_str.startswith("seed") and seed_str[4:].isdigit() else seed_str
    meta = {
        "bank": bank,
        "readout": readout,
        "seed": seed,
        "validation_combined_csv": str(val),
        "forecast_csv": str(fc) if fc.exists() else None,
        "test_csv": str(test_csv_path),
        "_synthesized": True,
        "_score_label": score,
    }
    return meta


def load_candidate_any(spec, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio):
    kind, path = spec
    if kind == "json":
        return pha._load_candidate(
            str(path), score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio,
        )
    meta = synthesize_meta_from_csv(path)
    if meta is None:
        return None
    info = pha._candidate_score(
        meta, score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio,
    )
    info.update({
        "json_path": None,
        "label": pha._artifact_label(meta),
        "bank": meta.get("bank", ""),
        "readout": meta.get("readout", ""),
        "seed": meta.get("seed", ""),
    })
    return {"path": str(path), "meta": meta, "info": info}


def main():
    ap = argparse.ArgumentParser(
        description="Fusione speciale di due artifact espliciti.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--dataset-subfolder", default="master_with_usgs_core_astrofmt_reduced")
    ap.add_argument("--candidate-a", required=True,
                    help="Substring del filename test.json del candidato A")
    ap.add_argument("--candidate-b", required=True,
                    help="Substring del filename test.json del candidato B")
    ap.add_argument("--out-subdir", default="post_hybrid_checks_special")
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
    args = ap.parse_args()

    if not args.run_dir.exists():
        sys.exit(f"run_dir non esiste: {args.run_dir}")

    matches_a = find_candidate(args.run_dir, args.dataset_subfolder, args.candidate_a)
    matches_b = find_candidate(args.run_dir, args.dataset_subfolder, args.candidate_b)

    def report(label, pattern, matches):
        if len(matches) == 1:
            kind, p = matches[0]
            tag = "[json]" if kind == "json" else "[csv-synth]"
            print(f"  {label}  '{pattern}'  →  {tag}  {p}")
            return matches[0]
        if len(matches) == 0:
            print(f"  {label}  '{pattern}'  →  NESSUN MATCH")
            return None
        print(f"  {label}  '{pattern}'  →  AMBIGUO ({len(matches)} match):")
        for kind, m in matches:
            tag = "[json]" if kind == "json" else "[csv-synth]"
            print(f"      - {tag}  {m}")
        return None

    print("=" * 72)
    print("POST-HYBRID PAIR SPECIAL — risoluzione candidati")
    print("=" * 72)
    a_spec = report("Candidate A", args.candidate_a, matches_a)
    b_spec = report("Candidate B", args.candidate_b, matches_b)
    if a_spec is None or b_spec is None:
        sys.exit("Risoluzione candidati fallita: rendi i pattern più specifici.")
    a_path = a_spec[1]
    b_path = b_spec[1]

    cand_a = load_candidate_any(
        a_spec, args.score_column, args.forecast_guard,
        args.forecast_flat_eps, args.forecast_high_ratio,
    )
    cand_b = load_candidate_any(
        b_spec, args.score_column, args.forecast_guard,
        args.forecast_flat_eps, args.forecast_high_ratio,
    )
    if cand_a is None or cand_b is None:
        sys.exit("Caricamento candidati fallito (validation_combined o forecast mancanti).")

    sim = pha._simulate_pair(
        cand_a["meta"], cand_b["meta"],
        logic=args.logic, normalize=args.normalize, score_column=args.score_column,
        alpha=args.alpha, threshold=args.threshold,
        calibrate_mode=args.calibrate_mode, calibrate_metric=args.calibrate_metric,
        min_recall=args.min_recall, actual_threshold=args.actual_threshold,
        forecast_guard=args.forecast_guard,
        forecast_flat_eps=args.forecast_flat_eps,
        forecast_high_ratio=args.forecast_high_ratio,
    )
    if sim is None:
        sys.exit("Simulazione fallita (validation rows non allineabili).")

    out_dir = args.run_dir / args.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    label_a = pha._artifact_label(cand_a["meta"])
    label_b = pha._artifact_label(cand_b["meta"])
    pair_name = f"{label_a}_X_{label_b}__{args.logic}__{args.normalize}".replace("/", "_")

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
        score_col=args.score_column,
        norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
        raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
        actual_threshold=eff_actual,
        threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
        threshold=sim["threshold"],
        logic=args.logic, alpha=args.alpha,
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
            score_col=args.score_column,
            norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
            raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
            actual_threshold=eff_actual,
            threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
            threshold=sim["threshold"],
            logic=args.logic, alpha=args.alpha,
            has_segment=False,
        )
        pha._write_csv(str(fc_csv), out_forecast, has_segment=False)

    rules_a = pha._load_rules(cand_a["meta"])
    rules_b = pha._load_rules(cand_b["meta"])
    derived_rules = pha._derive_rules(
        cand_a["meta"], cand_b["meta"], rules_a, rules_b,
        logic=args.logic, max_rules=args.max_rules,
    )
    rules_path = out_dir / f"{pair_name}__derived_rules.json"
    with open(rules_path, "w") as fh:
        json.dump(derived_rules, fh, indent=2)

    summary = {
        "pair": pair_name,
        "candidate_a_path": str(a_path),
        "candidate_b_path": str(b_path),
        "candidate_a_label": label_a,
        "candidate_b_label": label_b,
        "logic": args.logic,
        "normalize": args.normalize,
        "alpha": args.alpha,
        "threshold": sim["threshold"],
        "threshold_a": sim["threshold_a"],
        "threshold_b": sim["threshold_b"],
        "metrics": sim["metrics"],
        "disagreement": sim["disagreement"],
        "forecast_eval": sim["forecast_eval"],
    }
    summary_path = out_dir / f"{pair_name}__summary.json"
    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    cmp_png = out_dir / f"{pair_name}__lineage_comparison.png"
    try:
        pha._write_lineage_comparison_png(
            str(cmp_png), cand_a["meta"], cand_b["meta"],
            out_val, out_forecast,
            score_column=args.score_column, summary=summary,
        )
    except Exception as exc:
        print(f"  [warn] lineage_comparison failed: {exc}")

    diag_png = out_dir / f"{pair_name}__lineage_diagram.png"
    try:
        pha._write_lineage_diagram(str(diag_png), cand_a["meta"], cand_b["meta"], summary)
    except Exception as exc:
        print(f"  [warn] lineage_diagram failed: {exc}")

    bar = "=" * 72
    print()
    print(bar)
    print("DONE — fusione in:")
    print(bar)
    print(f"  out_dir    : {out_dir}")
    print(f"  pair       : {pair_name}")
    print(f"  metrics    : {sim['metrics']}")
    print(f"  threshold  : {sim['threshold']:.4f}  (A={sim['threshold_a']:.4f}  B={sim['threshold_b']:.4f})")
    print(f"  validation : {val_csv.name}")
    if out_forecast:
        print(f"  forecast   : {fc_csv.name}")
    print(f"  rules      : {rules_path.name}")
    print(f"  summary    : {summary_path.name}")
    if cmp_png.exists():
        print(f"  comparison : {cmp_png.name}")
    if diag_png.exists():
        print(f"  diagram    : {diag_png.name}")
    print(bar)


if __name__ == "__main__":
    main()

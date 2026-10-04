#!/usr/bin/env python3
"""Multi-level merge pipeline operating on a completed train-max run.

Riusa le funzioni di fusione di post_hybrid_artifacts.py senza ri-trainare.

Pool building (configurabile, default a1):
    - tutti i 'best_by_bank' (analogici puri + 1 lcs + 1 hybrid)
    - top-K LCS dal main folder (default 5)
    - top-K HYBRID dal main folder (default 5)

Pair selection (b1):
    - itertools.combinations sul pool
    - cross-family bonus AMPLIFICATO (bank-pure + lcs + hybrid + merged)

Multi-level chain (c1+c3):
    - level 1: coppie tra candidati del pool iniziale
    - level 2: coppie di fusioni di livello 1
    - level N: ricorsivo, fino a --chain-levels N (default 2)
    - ad ogni livello: top-K coppie sopravvivono e diventano input per il livello successivo

Output:
    <run_dir>/merge_pipeline/
      pool.json
      level1/<pair>__... (PNG, CSV, JSON come post_hybrid_checks)
      level2/<pair>__...
      chain_diagram.png        # diagramma globale dell'intera catena
      summary.json
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# import as library
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_hybrid_artifacts as pha


def family_of(meta):
    bank = str(meta.get("bank", "") or "")
    readout = str(meta.get("readout", "") or "")
    if bank.startswith("__merged_L"):
        return bank
    if bank == "__lcs__":
        return "LCS"
    if bank == "__hybrid__":
        return "HYBRID"
    if not bank and readout.startswith("deepnet"):
        return "END_TO_END"
    if bank:
        return "BANK"
    return "OTHER"


def cross_family_bonus(meta_a, meta_b, base_bonus, cross_bonus):
    """b1: cross-family bonus aumentato."""
    fa = family_of(meta_a)
    fb = family_of(meta_b)
    if fa == fb:
        return base_bonus
    return base_bonus + cross_bonus


def find_candidate_jsons(run_dir, dataset_subfolder):
    main_dir = run_dir / dataset_subfolder
    bank_dir = run_dir / "best_by_bank" / dataset_subfolder
    paths = []
    if main_dir.exists():
        paths.extend(sorted(main_dir.glob("*__test.json")))
    if bank_dir.exists():
        paths.extend(sorted(bank_dir.glob("*__test.json")))
    seen = set()
    unique = []
    for p in paths:
        key = p.resolve()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def build_pool(run_dir, dataset_subfolder, *, max_bank_pure, max_lcs, max_hybrid,
               max_end_to_end, score_column, forecast_guard, forecast_flat_eps,
               forecast_high_ratio):
    json_paths = find_candidate_jsons(run_dir, dataset_subfolder)
    loaded = []
    for p in json_paths:
        item = pha._load_candidate(
            str(p), score_column, forecast_guard, forecast_flat_eps, forecast_high_ratio,
        )
        if item is not None:
            item["family"] = family_of(item["meta"])
            loaded.append(item)

    by_family = {}
    for item in loaded:
        by_family.setdefault(item["family"], []).append(item)

    quota = {
        "BANK": max_bank_pure,
        "LCS": max_lcs,
        "HYBRID": max_hybrid,
        "END_TO_END": max_end_to_end,
    }

    pool = []
    seen_paths = set()
    for fam, cap in quota.items():
        items = by_family.get(fam, [])
        items.sort(key=lambda c: c["info"]["candidate_score"], reverse=True)
        for it in items[:cap]:
            if it["path"] in seen_paths:
                continue
            pool.append(it)
            seen_paths.add(it["path"])

    pool.sort(key=lambda c: c["info"]["candidate_score"], reverse=True)
    return pool, by_family


def evaluate_pairs(pool, *, logic, normalize, alpha, threshold, calibrate_mode,
                   calibrate_metric, min_recall, actual_threshold, score_column,
                   forecast_guard, forecast_flat_eps, forecast_high_ratio,
                   cross_bonus, top_pairs):
    proposals = []
    n = len(pool)
    for i in range(n):
        for j in range(i + 1, n):
            ca = pool[i]
            cb = pool[j]
            sim = pha._simulate_pair(
                ca["meta"], cb["meta"],
                logic=logic, normalize=normalize, score_column=score_column,
                alpha=alpha, threshold=threshold,
                calibrate_mode=calibrate_mode, calibrate_metric=calibrate_metric,
                min_recall=min_recall, actual_threshold=actual_threshold,
                forecast_guard=forecast_guard,
                forecast_flat_eps=forecast_flat_eps,
                forecast_high_ratio=forecast_high_ratio,
            )
            if sim is None:
                continue
            metrics = sim["metrics"]
            pair_guard = sim["forecast_eval"]["guard"]
            base_kind = pha._pair_kind_bonus(ca["meta"], cb["meta"])
            kind_bonus = cross_family_bonus(
                ca["meta"], cb["meta"], base_kind, cross_bonus,
            )
            score = (
                pha._metric_value(metrics, calibrate_metric)
                + 0.10 * sim["disagreement"]
                + pair_guard["bonus"]
                - pair_guard["penalty"]
                + kind_bonus
            )
            proposals.append({
                "a": ca, "b": cb, "sim": sim,
                "pair_score": float(score),
                "kind_bonus": float(kind_bonus),
                "metrics": metrics,
                "fa": ca["family"], "fb": cb["family"],
            })
    proposals.sort(key=lambda p: p["pair_score"], reverse=True)
    if top_pairs and top_pairs > 0:
        proposals = proposals[:top_pairs]
    return proposals


def export_pair(prop, level, out_dir, *, score_column, logic, normalize, alpha,
                threshold, calibrate_mode, calibrate_metric, min_recall,
                actual_threshold, forecast_guard, forecast_flat_eps,
                forecast_high_ratio, max_rules):
    a, b, sim = prop["a"], prop["b"], prop["sim"]
    label_a = pha._artifact_label(a["meta"])
    label_b = pha._artifact_label(b["meta"])
    pair_name = f"L{level}__{label_a}_X_{label_b}__{logic}__{normalize}"
    pair_name = pair_name.replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    val_a_rows = pha._read_rows(a["meta"]["validation_combined_csv"], has_segment=True)
    val_b_rows = pha._read_rows(b["meta"]["validation_combined_csv"], has_segment=True)
    aligned_val = pha._align_rows(val_a_rows, val_b_rows, has_segment=True)

    raw_thr_a = pha._artifact_threshold(a["meta"])
    raw_thr_b = pha._artifact_threshold(b["meta"])
    eff_actual = actual_threshold if actual_threshold is not None else min(raw_thr_a, raw_thr_b)
    out_val = pha._build_output_rows(
        aligned_val,
        score_col=score_column, norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
        raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
        actual_threshold=eff_actual,
        threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
        threshold=sim["threshold"], logic=logic, alpha=alpha,
        has_segment=True,
    )
    val_csv = out_dir / f"{pair_name}__validation_combined.csv"
    pha._write_csv(str(val_csv), out_val, has_segment=True)

    out_forecast = []
    fc_csv = out_dir / f"{pair_name}__forecast.csv"
    fc_a = a["meta"].get("forecast_csv")
    fc_b = b["meta"].get("forecast_csv")
    if fc_a and fc_b and os.path.exists(fc_a) and os.path.exists(fc_b):
        rows_fc_a = pha._read_rows(fc_a, has_segment=False)
        rows_fc_b = pha._read_rows(fc_b, has_segment=False)
        aligned_fc = pha._align_rows(rows_fc_a, rows_fc_b, has_segment=False)
        out_forecast = pha._build_output_rows(
            aligned_fc,
            score_col=score_column, norm_a=sim["normalizer_a"], norm_b=sim["normalizer_b"],
            raw_thr_a=raw_thr_a, raw_thr_b=raw_thr_b,
            actual_threshold=eff_actual,
            threshold_a=sim["threshold_a"], threshold_b=sim["threshold_b"],
            threshold=sim["threshold"], logic=logic, alpha=alpha,
            has_segment=False,
        )
        pha._write_csv(str(fc_csv), out_forecast, has_segment=False)

    rules_a = pha._load_rules(a["meta"])
    rules_b = pha._load_rules(b["meta"])
    derived_rules = pha._derive_rules(
        a["meta"], b["meta"], rules_a, rules_b, logic=logic, max_rules=max_rules,
    )
    rules_path = out_dir / f"{pair_name}__derived_rules.json"
    with open(rules_path, "w") as fh:
        json.dump(derived_rules, fh, indent=2)

    summary = {
        "level": level,
        "pair": pair_name,
        "source_a": pha._artifact_label(a["meta"]),
        "source_b": pha._artifact_label(b["meta"]),
        "family_a": a["family"],
        "family_b": b["family"],
        "logic": logic, "normalize": normalize, "alpha": alpha,
        "threshold": sim["threshold"],
        "threshold_a": sim["threshold_a"],
        "threshold_b": sim["threshold_b"],
        "metrics": sim["metrics"],
        "disagreement": sim["disagreement"],
        "forecast_eval": sim["forecast_eval"],
        "pair_score": prop["pair_score"],
        "kind_bonus": prop["kind_bonus"],
    }
    summary_path = out_dir / f"{pair_name}__summary.json"
    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2)

    cmp_png = out_dir / f"{pair_name}__lineage_comparison.png"
    try:
        pha._write_lineage_comparison_png(
            str(cmp_png), a["meta"], b["meta"], out_val, out_forecast,
            score_column=score_column, summary=summary,
        )
    except Exception as exc:
        print(f"  [warn] lineage_comparison failed: {exc}")

    diag_png = out_dir / f"{pair_name}__lineage_diagram.png"
    try:
        pha._write_lineage_diagram(str(diag_png), a["meta"], b["meta"], summary)
    except Exception as exc:
        print(f"  [warn] lineage_diagram failed: {exc}")

    merged_meta = {
        "bank": f"__merged_L{level}__",
        "readout": pair_name,
        "seed": -level,
        "validation_combined_csv": str(val_csv),
        "forecast_csv": str(fc_csv) if out_forecast else None,
        "actual_threshold": actual_threshold if actual_threshold is not None else min(raw_thr_a, raw_thr_b),
        "prediction_threshold": sim["threshold"],
        "_merged_from": [a["meta"], b["meta"]],
        "_merged_pair_name": pair_name,
        "_merged_level": level,
        "_merged_metrics": sim["metrics"],
    }
    merged_meta_path = out_dir / f"{pair_name}__test.json"
    with open(merged_meta_path, "w") as fh:
        json.dump(merged_meta, fh, indent=2)

    return {
        "summary": summary,
        "merged_meta": merged_meta,
        "merged_meta_path": str(merged_meta_path),
        "validation_combined_csv": str(val_csv),
        "forecast_csv": str(fc_csv) if out_forecast else None,
        "lineage_comparison_png": str(cmp_png) if cmp_png.exists() else None,
        "lineage_diagram_png": str(diag_png) if diag_png.exists() else None,
    }


def merged_to_pool_item(merged_meta, info_score):
    return {
        "path": merged_meta.get("_merged_pair_name", ""),
        "meta": merged_meta,
        "info": {"candidate_score": float(info_score)},
        "family": str(merged_meta.get("bank", "")),
    }


def write_chain_diagram(path, all_levels):
    """Diagramma globale di tutta la catena: nodi (sources + merged) + archi."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        print(f"  [warn] PIL not available, chain diagram skipped: {path}")
        return
    if not all_levels:
        return

    margin = 30
    col_w = 280
    row_h = 70
    n_cols = len(all_levels) + 1
    max_rows = max(len(level) * 2 for level in all_levels) + 2
    W = margin * 2 + col_w * n_cols
    H = margin * 2 + row_h * max(8, max_rows)

    img = Image.new("RGB", (W, H), (250, 250, 252))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        font_t = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except Exception:
        font = font_b = font_t = ImageFont.load_default()

    fam_colors = {
        "BANK": (200, 230, 250),
        "LCS": (250, 220, 200),
        "HYBRID": (220, 250, 200),
        "END_TO_END": (245, 215, 245),
        "OTHER": (230, 230, 230),
    }

    sources = {}
    for L_idx, level_results in enumerate(all_levels, start=1):
        for r in level_results:
            sa = r["summary"]["source_a"]
            sb = r["summary"]["source_b"]
            sources.setdefault(sa, r["summary"]["family_a"])
            sources.setdefault(sb, r["summary"]["family_b"])

    box_w = col_w - 30
    box_h = 50
    label_to_box = {}

    src_list = list(sources.items())
    for idx, (label, fam) in enumerate(src_list):
        x = margin + 10
        y = margin + idx * (box_h + 12) + 30
        col = fam_colors.get(fam.split("_")[0] if fam not in fam_colors else fam, fam_colors["OTHER"])
        if fam.startswith("__merged"):
            col = (255, 245, 200)
        draw.rectangle([x, y, x + box_w, y + box_h], fill=col, outline=(60, 70, 85))
        draw.text((x + 6, y + 4), f"[{fam}]", font=font_b, fill=(60, 70, 85))
        text = label if len(label) < 38 else label[:36] + ".."
        draw.text((x + 6, y + 22), text, font=font, fill=(20, 20, 30))
        label_to_box[label] = (x + box_w, y + box_h // 2)

    draw.text((margin + 10, 8), "SOURCES", font=font_t, fill=(40, 40, 50))

    for L_idx, level_results in enumerate(all_levels, start=1):
        col_x = margin + col_w * L_idx + 10
        draw.text((col_x, 8), f"LEVEL {L_idx} MERGES", font=font_t, fill=(40, 40, 50))
        for r_idx, r in enumerate(level_results):
            y = margin + r_idx * (box_h + 18) + 30
            x = col_x
            sm = r["summary"]
            col = (255, 245, 200)
            draw.rectangle([x, y, x + box_w, y + box_h], fill=col, outline=(60, 70, 85))
            metrics = sm["metrics"]
            draw.text(
                (x + 6, y + 4),
                f"L{L_idx}  score={sm['pair_score']:.3f}  f1={metrics.get('f1',0):.2f}  bal={metrics.get('balanced_accuracy',0):.2f}",
                font=font_b, fill=(60, 70, 85),
            )
            draw.text(
                (x + 6, y + 22),
                f"{sm['family_a']} ⊗ {sm['family_b']}  recall={metrics.get('recall',0):.2f}",
                font=font, fill=(20, 20, 30),
            )
            label_to_box[sm["pair"]] = (x + box_w, y + box_h // 2)
            input_x = x
            for src_label in (sm["source_a"], sm["source_b"]):
                src_pos = label_to_box.get(src_label)
                if src_pos is None:
                    continue
                draw.line([src_pos[0], src_pos[1], input_x, y + box_h // 2],
                          fill=(120, 130, 145), width=1)

    img.save(path)


def main():
    p = argparse.ArgumentParser(
        description="Multi-level merge pipeline su un run train-max completato.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("run_dir", type=Path, help="Path della cartella pulsar_train-max_best_trials_<ts>")
    p.add_argument("--dataset-subfolder", default="master_with_usgs_core_astrofmt_reduced",
                   help="Nome del subfolder col dataset (es. master_with_usgs_core_astrofmt_reduced)")

    p.add_argument("--max-bank-pure", type=int, default=99)
    p.add_argument("--max-lcs", type=int, default=5)
    p.add_argument("--max-hybrid", type=int, default=5)
    p.add_argument("--max-end-to-end", type=int, default=2)

    p.add_argument("--chain-levels", type=int, default=2,
                   help="Quanti livelli di fusione concatenati (>=1)")
    p.add_argument("--top-pairs-per-level", type=int, default=8,
                   help="Quante coppie tenere per livello (input al livello successivo)")

    p.add_argument("--cross-family-bonus", type=float, default=0.20,
                   help="b1: bonus aggiunto al pair_score quando le due fonti sono di famiglie diverse")

    p.add_argument("--logic", default="and", choices=["and", "or", "weighted"])
    p.add_argument("--normalize", default="auto",
                   choices=["auto", "minmax", "zscore", "rank", "binary"])
    p.add_argument("--alpha", type=float, default=0.5)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--calibrate-mode", default="threshold_search")
    p.add_argument("--calibrate-metric", default="f1")
    p.add_argument("--min-recall", type=float, default=0.0)
    p.add_argument("--actual-threshold", type=float, default=None)
    p.add_argument("--score-column", default="pred")

    p.add_argument("--forecast-guard", default="off",
                   choices=["off", "soft", "strict"])
    p.add_argument("--forecast-flat-eps", type=float, default=1e-6)
    p.add_argument("--forecast-high-ratio", type=float, default=0.8)
    p.add_argument("--max-rules", type=int, default=20)

    p.add_argument("--out-subdir", default="merge_pipeline",
                   help="Subfolder dentro run_dir per gli output")
    args = p.parse_args()

    if not args.run_dir.exists():
        sys.exit(f"run_dir non esiste: {args.run_dir}")
    if args.chain_levels < 1:
        sys.exit("--chain-levels deve essere >= 1")

    out_root = args.run_dir / args.out_subdir
    out_root.mkdir(parents=True, exist_ok=True)

    bar = "=" * 72
    print(bar)
    print("MERGE PIPELINE — chosen configuration")
    print(bar)
    print(f"  run_dir            : {args.run_dir}")
    print(f"  dataset subfolder  : {args.dataset_subfolder}")
    print(f"  pool quotas        : BANK={args.max_bank_pure}  LCS={args.max_lcs}  "
          f"HYBRID={args.max_hybrid}  END_TO_END={args.max_end_to_end}")
    print(f"  chain levels       : {args.chain_levels}")
    print(f"  top pairs / level  : {args.top_pairs_per_level}")
    print(f"  cross-family bonus : +{args.cross_family_bonus}")
    print(f"  logic / normalize  : {args.logic} / {args.normalize}")
    print(f"  output dir         : {out_root}")
    print(bar)

    pool, by_family = build_pool(
        args.run_dir, args.dataset_subfolder,
        max_bank_pure=args.max_bank_pure,
        max_lcs=args.max_lcs,
        max_hybrid=args.max_hybrid,
        max_end_to_end=args.max_end_to_end,
        score_column=args.score_column,
        forecast_guard=args.forecast_guard,
        forecast_flat_eps=args.forecast_flat_eps,
        forecast_high_ratio=args.forecast_high_ratio,
    )

    print()
    print("POOL BUILT:")
    fam_counts = {}
    for it in pool:
        fam_counts[it["family"]] = fam_counts.get(it["family"], 0) + 1
    for fam, n in sorted(fam_counts.items()):
        print(f"  {fam:>14s}  : {n}")
    print(f"  {'TOTAL':>14s}  : {len(pool)}")

    if len(pool) < 2:
        sys.exit("Pool con meno di 2 candidati: impossibile fondere")

    pool_snapshot = []
    for it in pool:
        pool_snapshot.append({
            "path": it["path"],
            "family": it["family"],
            "label": pha._artifact_label(it["meta"]),
            "candidate_score": it["info"]["candidate_score"],
        })
    with open(out_root / "pool.json", "w") as fh:
        json.dump(pool_snapshot, fh, indent=2)

    all_levels_results = []
    current_pool = pool
    for level in range(1, args.chain_levels + 1):
        print()
        print(bar)
        print(f"LEVEL {level}  —  {len(current_pool)} candidates → "
              f"C({len(current_pool)},2)={len(current_pool)*(len(current_pool)-1)//2} possible pairs")
        print(bar)

        proposals = evaluate_pairs(
            current_pool,
            logic=args.logic, normalize=args.normalize, alpha=args.alpha,
            threshold=args.threshold,
            calibrate_mode=args.calibrate_mode,
            calibrate_metric=args.calibrate_metric,
            min_recall=args.min_recall,
            actual_threshold=args.actual_threshold,
            score_column=args.score_column,
            forecast_guard=args.forecast_guard,
            forecast_flat_eps=args.forecast_flat_eps,
            forecast_high_ratio=args.forecast_high_ratio,
            cross_bonus=args.cross_family_bonus,
            top_pairs=args.top_pairs_per_level,
        )

        if not proposals:
            print(f"  Nessuna coppia valida al livello {level}: stop.")
            break

        print(f"  Top {len(proposals)} pair_score:")
        for prop in proposals:
            m = prop["metrics"]
            print(f"    {prop['fa']:>14s} ⊗ {prop['fb']:<14s}  score={prop['pair_score']:+.3f}  "
                  f"f1={m.get('f1',0):.3f}  recall={m.get('recall',0):.3f}  "
                  f"bal={m.get('balanced_accuracy',0):.3f}  "
                  f"kind_bonus={prop['kind_bonus']:+.3f}")

        level_dir = out_root / f"level{level}"
        level_results = []
        for prop in proposals:
            res = export_pair(
                prop, level, level_dir,
                score_column=args.score_column, logic=args.logic,
                normalize=args.normalize, alpha=args.alpha,
                threshold=args.threshold,
                calibrate_mode=args.calibrate_mode,
                calibrate_metric=args.calibrate_metric,
                min_recall=args.min_recall,
                actual_threshold=args.actual_threshold,
                forecast_guard=args.forecast_guard,
                forecast_flat_eps=args.forecast_flat_eps,
                forecast_high_ratio=args.forecast_high_ratio,
                max_rules=args.max_rules,
            )
            level_results.append(res)

        all_levels_results.append(level_results)

        next_pool = [merged_to_pool_item(r["merged_meta"], r["summary"]["pair_score"])
                     for r in level_results]
        for it in current_pool[: max(2, len(next_pool))]:
            next_pool.append(it)
        current_pool = next_pool

    chain_png = out_root / "chain_diagram.png"
    write_chain_diagram(str(chain_png), all_levels_results)

    summary_global = {
        "config": vars(args),
        "pool_size": len(pool),
        "pool_by_family": fam_counts,
        "levels": [
            {
                "level": L_idx,
                "n_pairs": len(level_results),
                "pairs": [r["summary"] for r in level_results],
            }
            for L_idx, level_results in enumerate(all_levels_results, start=1)
        ],
        "chain_diagram": str(chain_png),
    }
    with open(out_root / "summary.json", "w") as fh:
        json.dump(summary_global, fh, indent=2, default=str)

    print()
    print(bar)
    print("DONE")
    print(bar)
    print(f"  output dir         : {out_root}")
    print(f"  chain diagram      : {chain_png}")
    print(f"  summary.json       : {out_root / 'summary.json'}")
    print(f"  per-level dirs     :")
    for L_idx, level_results in enumerate(all_levels_results, start=1):
        print(f"    level{L_idx}/  ({len(level_results)} merges)")
    print(bar)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create readable LCS rule and KAN surrogate interpretation reports."""
from __future__ import annotations

import argparse
import csv
import json
import textwrap
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def to_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out
    except Exception:
        return default


def find_trial_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in sorted(root.rglob("best_trials_index.csv")):
        for row in read_csv(index):
            row["_index_path"] = str(index)
            rows.append(row)
    return rows


def readable_lcs_rules(root: Path, max_rules: int) -> list[dict[str, object]]:
    rows = find_trial_rows(root)
    lcs_rows = [r for r in rows if r.get("best_rules_json") and Path(r["best_rules_json"]).exists()]
    lcs_rows.sort(key=lambda r: to_float(r.get("overall")), reverse=True)
    out: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    for row in lcs_rows:
        rules_path = row["best_rules_json"]
        if rules_path in seen_paths:
            continue
        seen_paths.add(rules_path)
        rules = load_json(Path(rules_path))
        if not isinstance(rules, list):
            continue
        for rule in rules[:max_rules]:
            conditions = rule.get("active_conditions_human") or rule.get("conditions_human") or []
            action = int(rule.get("action", 0) or 0)
            out.append({
                "source": row.get("_index_path"),
                "bank": row.get("bank"),
                "readout": row.get("readout"),
                "seed": row.get("seed"),
                "trial_serial": row.get("trial_serial"),
                "overall": to_float(row.get("overall")),
                "action": "above/positive" if action == 1 else "below/negative",
                "rule_rank": rule.get("rank"),
                "rule_fitness": rule.get("fitness"),
                "rule_accuracy": rule.get("accuracy"),
                "rule_f1": rule.get("rule_f1"),
                "rule_bal_acc": rule.get("rule_bal_acc"),
                "conditions": conditions,
                "plain_language": (
                    f"If {' AND '.join(conditions) if conditions else 'the learned wildcard pattern matches'}, "
                    f"then vote {('ABOVE/positive' if action == 1 else 'BELOW/negative')}."
                ),
            })
            if len(out) >= max_rules:
                return out
    return out


def readable_kan_surrogates(root: Path, max_items: int) -> list[dict[str, object]]:
    rows = find_trial_rows(root)
    kan_rows = [r for r in rows if str(r.get("bank")) == "__kan__" or str(r.get("bank")) == "(kan)"]
    kan_rows.sort(key=lambda r: to_float(r.get("overall")), reverse=True)
    out: list[dict[str, object]] = []
    for row in kan_rows[:max_items]:
        cfg = {}
        model_config = load_json_text(row.get("model_config", ""))
        if isinstance(model_config, dict):
            cfg = model_config.get("kan_cfg") or {}
        out.append({
            "source": row.get("_index_path"),
            "bank": row.get("bank"),
            "readout": row.get("readout"),
            "seed": row.get("seed"),
            "trial_serial": row.get("trial_serial"),
            "overall": to_float(row.get("overall")),
            "mse_test": to_float(row.get("mse_test")),
            "r2": to_float(row.get("r2")),
            "forecast_csv": row.get("forecast_csv"),
            "validation_csv": row.get("validation_combined_csv"),
            "kan_width": cfg.get("hidden_width"),
            "kan_layers": cfg.get("hidden_layers"),
            "kan_grid": cfg.get("grid"),
            "kan_epochs": cfg.get("epochs"),
            "plain_language": (
                "KAN surrogate note: this is a spline neural model, not an exported "
                "symbolic rule. Interpret it as a smooth coordinate/support response "
                f"learned by {row.get('readout')} seed={row.get('seed')} with "
                f"overall={to_float(row.get('overall')):.3f}."
            ),
        })
    return out


def load_json_text(text: str) -> object:
    try:
        return json.loads(text)
    except Exception:
        return None


def write_png(path: Path, lcs_rules: list[dict[str, object]],
              kan_items: list[dict[str, object]], title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, PNG skipped: {exc}")
        return

    fig, axes = plt.subplots(2, 1, figsize=(14, 10.5))
    fig.suptitle(title, fontsize=15, fontweight="bold")

    ax = axes[0]
    ax.set_axis_off()
    ax.set_title("LCS readable rules (native symbolic export)", loc="left", fontsize=12, fontweight="bold")
    y = 0.95
    if not lcs_rules:
        ax.text(0.02, y, "No LCS rules found.", va="top", fontsize=10)
    for rule in lcs_rules[:8]:
        text = (
            f"#{rule.get('rule_rank')} {rule.get('action')} | "
            f"overall={rule.get('overall'):.3f} acc={to_float(rule.get('rule_accuracy')):.3f} "
            f"f1={to_float(rule.get('rule_f1')):.3f}\n"
            f"{rule.get('plain_language')}"
        )
        wrapped = "\n".join(textwrap.wrap(text, width=140))
        ax.text(0.02, y, wrapped, va="top", fontsize=8.6, family="monospace")
        y -= 0.105
        if y < 0.04:
            break

    ax = axes[1]
    ax.set_axis_off()
    ax.set_title("KAN readable surrogate summary (not native symbolic rules)", loc="left", fontsize=12, fontweight="bold")
    y = 0.95
    if not kan_items:
        ax.text(0.02, y, "No KAN trials found.", va="top", fontsize=10)
    for item in kan_items[:8]:
        text = (
            f"{item.get('readout')} seed={item.get('seed')} overall={item.get('overall'):.3f} "
            f"width={item.get('kan_width')} grid={item.get('kan_grid')} epochs={item.get('kan_epochs')}\n"
            f"{item.get('plain_language')}"
        )
        wrapped = "\n".join(textwrap.wrap(text, width=140))
        ax.text(0.02, y, wrapped, va="top", fontsize=8.6, family="monospace")
        y -= 0.105
        if y < 0.04:
            break

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kan-root", type=Path, default=None)
    ap.add_argument("--lcs-root", type=Path, default=None)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="method_rules_summary")
    ap.add_argument("--max-rules", type=int, default=12)
    ap.add_argument("--title", default="Method rule summary")
    args = ap.parse_args()

    lcs_rules = readable_lcs_rules(args.lcs_root, args.max_rules) if args.lcs_root else []
    kan_items = readable_kan_surrogates(args.kan_root, args.max_rules) if args.kan_root else []
    payload = {
        "lcs_rules": lcs_rules,
        "kan_surrogate_summary": kan_items,
        "note": (
            "LCS rules are native symbolic best_rules exports. KAN entries are "
            "surrogate-readable summaries because the current KAN backend does not "
            "export symbolic coordinate rules."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.output_dir / f"{args.output_prefix}.json"
    out_md = args.output_dir / f"{args.output_prefix}.md"
    out_png = args.output_dir / f"{args.output_prefix}.png"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_png(out_png, lcs_rules, kan_items, args.title)

    md = [f"# {args.title}", "", payload["note"], ""]
    md.append("## LCS Native Rules")
    if not lcs_rules:
        md.append("No LCS rules found.")
    for rule in lcs_rules:
        md.append(
            f"- rank `{rule.get('rule_rank')}` action `{rule.get('action')}` "
            f"overall `{rule.get('overall'):.4f}`: {rule.get('plain_language')}"
        )
    md.extend(["", "## KAN Surrogate Summary"])
    if not kan_items:
        md.append("No KAN trials found.")
    for item in kan_items:
        md.append(
            f"- `{item.get('readout')}` seed `{item.get('seed')}` overall "
            f"`{item.get('overall'):.4f}`: {item.get('plain_language')}"
        )
    out_md.write_text("\n".join(md) + "\n")
    print(f"JSON: {out_json}")
    print(f"PNG:  {out_png}")
    print(f"MD:   {out_md}")


if __name__ == "__main__":
    main()

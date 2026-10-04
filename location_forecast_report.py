#!/usr/bin/env python3
"""Build a focused location/depth forecast report from a DLvsWAVE run."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path


def parse_dt(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:10], "%Y-%m-%d")


def parse_optional_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return parse_dt(value)


def in_window(dt: datetime, start: datetime | None, end: datetime | None) -> bool:
    if start is not None and dt < start:
        return False
    if end is not None and dt.date() > end.date():
        return False
    return True


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path and path.exists():
            return path
    return None


def find_forecast_csv(run_dir: Path) -> Path:
    candidates = [
        run_dir / "master_with_usgs_core_astrofmt" / "master_with_usgs_core_astrofmt__final_evaluation__forecast.csv",
    ]
    found = first_existing(candidates)
    if found is not None:
        return found
    index = run_dir / "best_trials_index.csv"
    if index.exists():
        rows = read_rows(index)
        for row in rows:
            fc = row.get("forecast_csv") or ""
            if fc and os.path.exists(fc):
                return Path(fc)
    raise SystemExit(f"No forecast CSV found under {run_dir}")


def find_validation_csv(run_dir: Path) -> Path | None:
    candidate = run_dir / "master_with_usgs_core_astrofmt" / "master_with_usgs_core_astrofmt__final_evaluation__validation.csv"
    if candidate.exists():
        return candidate
    index = run_dir / "best_trials_index.csv"
    if index.exists():
        for row in read_rows(index):
            val = row.get("validation_combined_csv") or row.get("test_csv") or ""
            if val and os.path.exists(val):
                return Path(val)
    return None


def find_trial_metrics(run_dir: Path, forecast_path: Path | None) -> dict[str, object]:
    index = run_dir / "best_trials_index.csv"
    if not index.exists():
        return {}
    rows = read_rows(index)
    if not rows:
        return {}
    selected = None
    if forecast_path is not None:
        target = str(forecast_path)
        for row in rows:
            if str(row.get("forecast_csv") or "") == target:
                selected = row
                break
    if selected is None:
        selected = rows[0]

    def f(key: str) -> float | None:
        return optional_float(selected.get(key))

    return {
        "bank": selected.get("bank"),
        "readout": selected.get("readout"),
        "seed": selected.get("seed"),
        "trial_serial": selected.get("trial_serial"),
        "overall": f("overall"),
        "overall_mean": f("overall_mean"),
        "overall_std": f("overall_std"),
        "event_precision": f("event_precision"),
        "event_recall": f("event_recall"),
        "event_f1": f("event_f1"),
        "event_bal_acc": f("event_bal_acc"),
        "event_specificity": f("event_specificity"),
        "mse_test": f("mse_test"),
        "best_rules_json": selected.get("best_rules_json") or "",
        "signature_json": selected.get("signature_json") or "",
    }


def score_column(row: dict[str, str], requested: str) -> str:
    if requested != "auto":
        return requested
    for key in ("predicted", "pred_recalibrated", "pred", "score"):
        if key in row:
            return key
    for key, value in row.items():
        if key in {"date", "context", "row_index", "phase", "actual", "actual_raw"}:
            continue
        try:
            float(value)
            return key
        except Exception:
            pass
    raise ValueError("No numeric prediction column found")


def date_column(row: dict[str, str]) -> str:
    for key in ("date", "context", "time", "timestamp"):
        if key in row:
            return key
    raise ValueError("No date/context column found")


def to_float(value: str, default: float = 0.0) -> float:
    try:
        out = float(value)
        if math.isfinite(out):
            return out
    except Exception:
        pass
    return default


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
        if math.isfinite(out):
            return out
    except Exception:
        return None
    return None


def inverse_value(pred: float, meta: dict[str, object]) -> float:
    if meta.get("mode") == "binary":
        return max(0.0, min(1.0, pred))
    if meta.get("mode") == "analog" and meta.get("analog_scale") == "minmax":
        # Newer DLvsWAVE artifact CSVs are already decoded to physical
        # latitude/longitude/depth. Older runs stored the internal [0, 1]
        # target, so keep backwards compatibility by decoding only values that
        # still look like normalized model output.
        if pred < -0.25 or pred > 1.25:
            return pred
        lo = float(meta["clip_min"])
        hi = float(meta["clip_max"])
        clipped = max(0.0, min(1.0, pred))
        return lo + clipped * (hi - lo)
    return pred


def binary_decision_label(probability: float, meta: dict[str, object]) -> str:
    direction = str(meta.get("binary_direction") or "above")
    positive = "above" if direction == "above" else "below"
    negative = "below" if direction == "above" else "above"
    return positive if probability >= 0.5 else negative


def write_png(path: Path, rows: list[dict[str, object]], meta: dict[str, object],
              focus_start: datetime | None, focus_end: datetime | None,
              title: str, *, value_key: str = "estimated_value",
              y_label: str | None = None) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable, PNG skipped: {exc}")
        return
    if not rows:
        return
    dates = [parse_dt(str(r["date"])) for r in rows]
    values = [float(r[value_key]) for r in rows]
    focus_values = [
        (parse_dt(str(r["date"])), float(r[value_key]))
        for r in rows
        if int(r.get("focus_window", 0) or 0) == 1
    ]

    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.plot(dates, values, marker="o", color="#dc2626", linewidth=2.0,
            label=f"estimated {meta.get('target_source')}")
    if focus_start is not None and focus_end is not None:
        ax.axvspan(focus_start, focus_end, color="#fee2e2", alpha=0.55,
                   label="focus time window")
    if focus_values:
        ax.scatter([d for d, _ in focus_values], [v for _, v in focus_values],
                   s=95, facecolors="none", edgecolors="black", linewidths=1.8,
                   label="focus points")
    threshold = optional_float(meta.get("decision_threshold"))
    if meta.get("mode") == "binary":
        ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.2,
                   label=f"decision line: {meta.get('target_source')} "
                         f"{'>=' if meta.get('binary_direction') == 'above' else '<='} "
                         f"{threshold if threshold is not None else meta.get('decision_threshold_requested', '')}")
        ax.set_ylim(-0.05, 1.05)
        ax.set_ylabel(y_label or "probability / binary score")
    else:
        if threshold is not None:
            ax.axhline(threshold, color="#111827",
                       linestyle="--", linewidth=1.2,
                       label=f"reference threshold: {meta.get('target_source')}={threshold}")
        ax.set_ylabel(y_label or str(meta.get("target_source")))
    ax.set_title(title)
    ax.set_xlabel("point date = START of forecast window")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_validation_report(run_dir: Path, meta: dict[str, object],
                            output_dir: Path, output_prefix: str,
                            forecast_start: datetime | None) -> tuple[str, str]:
    validation_path = find_validation_csv(run_dir)
    if validation_path is None:
        return "", ""
    rows_in = read_rows(validation_path)
    if not rows_in:
        return "", ""
    dcol = date_column(rows_in[0])
    scol = score_column(rows_in[0], "auto")
    out_rows = []
    leaked_rows = []
    for row in rows_in:
        dt = parse_dt(row[dcol])
        if forecast_start is not None and dt >= forecast_start:
            leaked_rows.append(dt.date().isoformat())
            continue
        actual_raw = to_float(row.get("actual", "0"))
        predicted_raw = to_float(row.get(scol, "0"))
        out_rows.append({
            "date": dt.date().isoformat(),
            "row_index": row.get("row_index", ""),
            "actual_raw": actual_raw,
            "predicted_raw": predicted_raw,
            "actual_value": inverse_value(actual_raw, meta),
            "predicted_value": inverse_value(predicted_raw, meta),
        })
    if not out_rows:
        if leaked_rows:
            raise SystemExit(
                "Validation leakage detected: validation CSV contains only forecast-window "
                f"rows at/after {forecast_start.date().isoformat()}: {leaked_rows[:8]}"
            )
        return "", ""
    if leaked_rows:
        raise SystemExit(
            "Validation leakage detected: validation CSV contains forecast-window rows "
            f"at/after {forecast_start.date().isoformat()}: {leaked_rows[:8]}"
        )
    out_csv = output_dir / f"{output_prefix}__validation_location_scale.csv"
    out_png = output_dir / f"{output_prefix}__validation_location_scale.png"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date", "row_index", "actual_raw", "predicted_raw",
                "actual_value", "predicted_value",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        dates = [parse_dt(str(r["date"])) for r in out_rows]
        actual = [float(r["actual_value"]) for r in out_rows]
        pred = [float(r["predicted_value"]) for r in out_rows]
        fig, ax = plt.subplots(figsize=(11.5, 5.3))
        ax.plot(dates, actual, marker="o", linewidth=1.9, color="#2563eb", label="actual")
        ax.plot(dates, pred, marker="o", linewidth=1.7, color="#dc2626", label="predicted")
        threshold = optional_float(meta.get("decision_threshold"))
        if threshold is not None and meta.get("mode") != "binary":
            ax.axhline(threshold, color="#111827", linestyle="--", linewidth=1.1,
                       label=f"threshold {threshold:g}")
        if meta.get("mode") == "binary":
            ax.axhline(0.5, color="#111827", linestyle="--", linewidth=1.1,
                       label="binary decision line")
            ax.set_ylim(-0.05, 1.05)
            ax.set_ylabel("probability / binary class")
        else:
            ax.set_ylabel(str(meta.get("target_source")))
        ax.set_title(f"{meta.get('target_source')} validation in location scale")
        ax.set_xlabel("historical validation date")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()
        fig.savefig(out_png, dpi=160)
        plt.close(fig)
    except Exception as exc:
        print(f"[warn] validation PNG skipped: {exc}")
        out_png = Path("")
    return str(out_csv), str(out_png) if out_png else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--prepared-json", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--output-prefix", default="location_forecast")
    ap.add_argument("--forecast-csv", type=Path, default=None)
    ap.add_argument("--score-column", default="auto")
    ap.add_argument("--focus-start-date", default="")
    ap.add_argument("--focus-end-date", default="")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    meta = json.loads(args.prepared_json.read_text())
    fc_path = args.forecast_csv if args.forecast_csv else find_forecast_csv(args.run_dir)
    fc_rows = read_rows(fc_path)
    if not fc_rows:
        raise SystemExit(f"Forecast CSV is empty: {fc_path}")
    dcol = date_column(fc_rows[0])
    scol = score_column(fc_rows[0], args.score_column)
    focus_start = parse_optional_dt(args.focus_start_date or str(meta.get("focus_start_date") or ""))
    focus_end = parse_optional_dt(args.focus_end_date or str(meta.get("focus_end_date") or ""))

    rows: list[dict[str, object]] = []
    threshold = optional_float(meta.get("decision_threshold"))
    for row in fc_rows:
        dt = parse_dt(row[dcol])
        pred = to_float(row.get(scol, "0"))
        estimated = inverse_value(pred, meta)
        decision = ""
        if threshold is not None:
            if meta.get("mode") == "binary":
                decision = binary_decision_label(estimated, meta)
            else:
                if str(meta.get("binary_direction") or "above") == "above":
                    decision = "above" if estimated >= threshold else "below"
                else:
                    decision = "below" if estimated <= threshold else "above"
        rows.append({
            "date": dt.date().isoformat(),
            "row_index": row.get("row_index", ""),
            "predicted_raw": pred,
            "estimated_value": estimated,
            "focus_window": 1 if in_window(dt, focus_start, focus_end) else 0,
            "decision_vs_threshold": decision,
        })

    focus_rows = [r for r in rows if int(r["focus_window"]) == 1]
    values = [float(r["estimated_value"]) for r in focus_rows or rows]
    summary = {
        "target_source": meta.get("target_source"),
        "mode": meta.get("mode"),
        "forecast_csv": str(fc_path),
        "validation_csv": str(find_validation_csv(args.run_dir) or ""),
        "validation_metrics": find_trial_metrics(args.run_dir, fc_path),
        "prepared_json": str(args.prepared_json),
        "focus_start_date": None if focus_start is None else focus_start.date().isoformat(),
        "focus_end_date": None if focus_end is None else focus_end.date().isoformat(),
        "focus_rows": len(focus_rows),
        "estimated_mean": sum(values) / len(values) if values else None,
        "estimated_min": min(values) if values else None,
        "estimated_max": max(values) if values else None,
        "estimated_peak_date": max((r for r in (focus_rows or rows)),
                                   key=lambda r: float(r["estimated_value"]))["date"] if rows else None,
        "decision_threshold": threshold,
        "decision_threshold_requested": meta.get("decision_threshold_requested"),
        "decision_threshold_info": meta.get("decision_threshold_info"),
        "binary_direction": meta.get("binary_direction"),
    }
    if threshold is not None and values:
        if meta.get("mode") == "binary":
            summary["focus_decision"] = binary_decision_label(float(summary["estimated_mean"]), meta)
        else:
            if str(meta.get("binary_direction") or "above") == "above":
                summary["focus_decision"] = "above" if summary["estimated_mean"] >= threshold else "below"
            else:
                summary["focus_decision"] = "below" if summary["estimated_mean"] <= threshold else "above"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.output_dir / f"{args.output_prefix}.csv"
    out_json = args.output_dir / f"{args.output_prefix}.json"
    out_png = args.output_dir / f"{args.output_prefix}.png"
    out_md = args.output_dir / f"{args.output_prefix}.md"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "row_index", "predicted_raw", "estimated_value",
                        "focus_window", "decision_vs_threshold"],
        )
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    title = args.title or (
        f"{meta.get('target_source')} localization forecast "
        f"({meta.get('mode')})"
    )
    write_png(out_png, rows, meta, focus_start, focus_end, title)
    validation_csv, validation_png = write_validation_report(
        args.run_dir, meta, args.output_dir, args.output_prefix, parse_optional_dt(meta.get("forecast_start_date"))
    )
    summary["validation_location_scale_csv"] = validation_csv
    summary["validation_location_scale_png"] = validation_png
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    decision_line = ""
    if "focus_decision" in summary:
        sign = ">=" if meta.get("binary_direction") == "above" else "<="
        decision_line = (
            f"- focus decision: `{meta.get('target_source')} {sign} "
            f"{threshold}` -> **{summary['focus_decision']}**\n"
        )
    out_md.write_text(
        f"# {title}\n\n"
        "Experimental second-stage localization report. Training rows are seismic-only; "
        "forecast rows are retained only for projection.\n\n"
        f"- target: `{meta.get('target_source')}`\n"
        f"- mode: `{meta.get('mode')}`\n"
        f"- focus window: `{summary['focus_start_date']}` -> `{summary['focus_end_date']}`\n"
        f"- focus estimated mean: `{summary['estimated_mean']}`\n"
        f"- focus estimated min/max: `{summary['estimated_min']}` / `{summary['estimated_max']}`\n"
        f"- peak estimated date in reported rows: `{summary['estimated_peak_date']}`\n"
        f"{decision_line}"
        f"- source forecast: `{fc_path}`\n"
        f"- validation location-scale CSV: `{validation_csv}`\n"
        f"- validation location-scale PNG: `{validation_png}`\n"
        f"- prepared metadata: `{args.prepared_json}`\n\n"
        "Point semantics: every forecast date is the START of its forecast window.\n",
    )
    print(f"CSV:  {out_csv}")
    print(f"JSON: {out_json}")
    print(f"PNG:  {out_png}")
    print(f"MD:   {out_md}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build one readable validation+forecast dashboard for a DLvsWAVE run."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "context" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"context": "date"})
    if "date" not in df.columns:
        raise ValueError(f"CSV has no date/context column: {path}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df


def _score_col(df: pd.DataFrame) -> str:
    for col in ("pred_recalibrated", "predicted", "pred"):
        if col in df.columns:
            return col
    raise ValueError(f"No prediction column found in columns: {list(df.columns)}")


def _label_from_row(row: pd.Series) -> str:
    bank = str(row.get("bank", "")).replace("__", "")
    readout = str(row.get("readout", ""))
    seed = row.get("seed", "")
    overall = row.get("overall", "")
    try:
        overall_text = f"{float(overall):.3f}"
    except Exception:
        overall_text = str(overall)
    return f"T{int(row.get('trial_serial', 0)):05d} {bank}/{readout} seed={seed} score={overall_text}"


def _plot_series(ax, df: pd.DataFrame, y_col: str, label: str, *, color=None, lw=1.8, alpha=1.0, marker="o"):
    ax.plot(df["date"], df[y_col], label=label, color=color, lw=lw, alpha=alpha, marker=marker, ms=4)


def _style_date_axis(ax):
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.grid(True, color="#d7dde5", linewidth=0.8, alpha=0.6)


def build_dashboard(run_dir: Path, output_png: Path, output_csv: Path | None, top_n: int, title: str) -> dict:
    best_index = run_dir / "best_trials_index.csv"
    if not best_index.exists():
        raise FileNotFoundError(f"best_trials_index.csv not found in {run_dir}")
    best = pd.read_csv(best_index)
    best = best.sort_values("overall", ascending=False).head(top_n).copy()

    dataset_dirs = [p for p in run_dir.iterdir() if p.is_dir()]
    final_validation = None
    final_forecast = None
    for d in dataset_dirs:
        candidates_val = list(d.glob("*__final_evaluation__validation.csv"))
        candidates_fc = list(d.glob("*__final_evaluation__forecast.csv"))
        if candidates_val and candidates_fc:
            final_validation = candidates_val[0]
            final_forecast = candidates_fc[0]
            break
    if final_validation is None or final_forecast is None:
        raise FileNotFoundError(f"Final evaluation validation/forecast CSV not found below {run_dir}")

    val_final = _read_csv(final_validation)
    fc_final = _read_csv(final_forecast)
    final_val_col = _score_col(val_final)
    final_fc_col = _score_col(fc_final)

    trial_validations: list[tuple[str, pd.DataFrame, str]] = []
    trial_forecasts: list[tuple[str, pd.DataFrame, str]] = []
    rows_out: list[dict] = []

    for _, row in best.iterrows():
        label = _label_from_row(row)
        val_path = Path(str(row.get("validation_combined_csv", "")))
        fc_path = Path(str(row.get("forecast_csv", "")))
        if val_path.exists():
            vdf = _read_csv(val_path)
            trial_validations.append((label, vdf, _score_col(vdf)))
        if fc_path.exists():
            fdf = _read_csv(fc_path)
            trial_forecasts.append((label, fdf, _score_col(fdf)))
            for _, item in fdf.iterrows():
                rows_out.append(
                    {
                        "source": label,
                        "phase": "forecast_trial",
                        "date": item["date"].date().isoformat(),
                        "predicted": float(item[_score_col(fdf)]),
                        "overall": float(row.get("overall", math.nan)),
                    }
                )

    for _, item in fc_final.iterrows():
        rows_out.append(
            {
                "source": "FINAL rank-weighted ensemble",
                "phase": "forecast_final",
                "date": item["date"].date().isoformat(),
                "predicted": float(item[final_fc_col]),
                "overall": "",
            }
        )

    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(16, 13), constrained_layout=True)
    fig.suptitle(title, fontsize=18, fontweight="bold")

    ax = axes[0]
    if "actual" in val_final.columns:
        _plot_series(ax, val_final, "actual", "actual/event", color="#2563eb", lw=2.2)
    elif "actual_raw" in val_final.columns:
        _plot_series(ax, val_final, "actual_raw", "actual raw", color="#2563eb", lw=2.2)
    _plot_series(ax, val_final, final_val_col, "final validation prediction", color="#dc2626", lw=2.2)
    ax.axhline(0.5, color="#374151", linestyle="--", linewidth=1.1, label="decision 0.5")
    ax.set_title("Final evaluation validation")
    ax.set_ylabel("score")
    ax.legend(loc="upper left", fontsize=9)
    _style_date_axis(ax)

    ax = axes[1]
    for label, df, col in trial_validations:
        ax.plot(df["date"], df[col], lw=1.2, alpha=0.55, marker=".", label=label)
    if "actual" in val_final.columns:
        ax.plot(val_final["date"], val_final["actual"], color="#111827", lw=2.2, marker="o", label="actual/event")
    ax.axhline(0.5, color="#374151", linestyle="--", linewidth=1.1)
    ax.set_title(f"Top {len(trial_validations)} validation trials")
    ax.set_ylabel("score")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    _style_date_axis(ax)

    ax = axes[2]
    _plot_series(ax, fc_final, final_fc_col, "FINAL rank-weighted forecast", color="#16a34a", lw=2.6)
    ax.axhline(0.5, color="#374151", linestyle="--", linewidth=1.1, label="decision 0.5")
    ax.set_title("Final forecast with real dates")
    ax.set_ylabel("risk score")
    ax.legend(loc="upper left", fontsize=9)
    _style_date_axis(ax)

    ax = axes[3]
    for label, df, col in trial_forecasts:
        ax.plot(df["date"], df[col], lw=1.3, alpha=0.75, marker="o", ms=3, label=label)
    ax.plot(fc_final["date"], fc_final[final_fc_col], color="#111827", lw=2.5, marker="s", label="FINAL ensemble")
    ax.axhline(0.5, color="#374151", linestyle="--", linewidth=1.1)
    ax.set_title(f"Top {len(trial_forecasts)} forecasts compared")
    ax.set_ylabel("risk score")
    ax.set_xlabel("Each point/date is the START of its forecast window")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    _style_date_axis(ax)

    fig.savefig(output_png, dpi=170)
    plt.close(fig)

    if output_csv is not None:
        with output_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["source", "phase", "date", "predicted", "overall"])
            writer.writeheader()
            writer.writerows(rows_out)

    manifest = {
        "run_dir": str(run_dir),
        "best_trials_index": str(best_index),
        "final_validation_csv": str(final_validation),
        "final_forecast_csv": str(final_forecast),
        "output_png": str(output_png),
        "output_csv": str(output_csv) if output_csv else None,
        "top_n": top_n,
        "trial_forecasts": [str(Path(str(row.get("forecast_csv", "")))) for _, row in best.iterrows()],
        "trial_validations": [str(Path(str(row.get("validation_combined_csv", "")))) for _, row in best.iterrows()],
    }
    manifest_path = output_png.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a single validation+forecast dashboard PNG for a run.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-png", default="")
    parser.add_argument("--output-csv", default="")
    parser.add_argument("--top-n", type=int, default=6)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    output_png = Path(args.output_png) if args.output_png else run_dir / "forecast_validation_dashboard.png"
    output_csv = Path(args.output_csv) if args.output_csv else output_png.with_suffix(".csv")
    title = args.title or f"Forecast/validation dashboard - {run_dir.name}"
    manifest = build_dashboard(run_dir, output_png, output_csv, args.top_n, title)
    print(f"PNG:  {manifest['output_png']}")
    print(f"CSV:  {manifest['output_csv']}")
    print(f"JSON: {Path(manifest['output_png']).with_suffix('.json')}")


if __name__ == "__main__":
    main()

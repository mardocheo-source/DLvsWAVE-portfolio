#!/usr/bin/env python3
"""Peak-consensus forecast fusion for DLvsWAVE forecast artifacts.

This is intentionally different from the rank-weighted final evaluation curve:
each source forecast is normalized independently, converted to peak votes, and
then merged by date. The final score is proportional to peak consensus.
"""

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
import numpy as np
import pandas as pd
import textwrap


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "context" in df.columns and "date" not in df.columns:
        df = df.rename(columns={"context": "date"})
    if "date" not in df.columns:
        raise ValueError(f"Missing date/context column: {path}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def _score_col(df: pd.DataFrame) -> str:
    for col in ("pred_recalibrated", "predicted", "pred"):
        if col in df.columns:
            return col
    raise ValueError(f"No prediction column found: {list(df.columns)}")


def _norm01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values, dtype=float)
    lo = float(np.nanmin(values[finite]))
    hi = float(np.nanmax(values[finite]))
    if abs(hi - lo) < 1e-12:
        return np.zeros_like(values, dtype=float)
    out = (values - lo) / (hi - lo)
    return np.clip(out, 0.0, 1.0)


def _detect_peaks(y_norm: np.ndarray, floor: float, max_peaks: int, min_separation: int) -> set[int]:
    if len(y_norm) == 0 or float(np.nanmax(y_norm)) < floor:
        return set()
    candidates: list[tuple[float, int]] = []
    n = len(y_norm)
    for i, value in enumerate(y_norm):
        if not np.isfinite(value) or value < floor:
            continue
        left = y_norm[i - 1] if i > 0 else -np.inf
        right = y_norm[i + 1] if i + 1 < n else -np.inf
        if value >= left and value >= right and (value > left or value > right):
            candidates.append((float(value), i))
    if not candidates:
        max_idx = int(np.nanargmax(y_norm))
        if y_norm[max_idx] >= floor:
            candidates.append((float(y_norm[max_idx]), max_idx))
    selected: list[int] = []
    for _, idx in sorted(candidates, reverse=True):
        if all(abs(idx - kept) >= min_separation for kept in selected):
            selected.append(idx)
        if max_peaks > 0 and len(selected) >= max_peaks:
            break
    return set(selected)


def _label_from_row(row: pd.Series) -> str:
    bank = str(row.get("bank", "")).replace("__", "")
    readout = str(row.get("readout", ""))
    seed = row.get("seed", "")
    overall = row.get("overall", "")
    try:
        score = f"{float(overall):.3f}"
    except Exception:
        score = str(overall)
    return f"T{int(row.get('trial_serial', 0)):05d} {bank}/{readout} seed={seed} score={score}"


def _safe_col_name(label: str) -> str:
    out = []
    for ch in label.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {"/", " ", "-", "_"}:
            out.append("_")
    text = "".join(out).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text[:80] or "source"


def _wrap_label(label: str, width: int = 38) -> str:
    return "\n".join(textwrap.wrap(label, width=width, break_long_words=False)) or label


def _source_forecasts_from_run(run_dir: Path, top_n: int, include_final: bool) -> list[tuple[str, Path, float]]:
    best_index = run_dir / "best_trials_index.csv"
    if not best_index.exists():
        raise FileNotFoundError(f"Missing best_trials_index.csv: {best_index}")
    best = pd.read_csv(best_index).sort_values("overall", ascending=False).head(top_n)
    sources: list[tuple[str, Path, float]] = []
    for _, row in best.iterrows():
        path = Path(str(row.get("forecast_csv", "")))
        if path.exists():
            sources.append((_label_from_row(row), path, float(row.get("overall", 0.0))))
    if include_final:
        for dataset_dir in [p for p in run_dir.iterdir() if p.is_dir()]:
            matches = list(dataset_dir.glob("*__final_evaluation__forecast.csv"))
            if matches:
                sources.append(("FINAL rank-weighted ensemble", matches[0], 1.0))
                break
    return sources


def _align_sources(sources: list[tuple[str, Path, float]]) -> tuple[pd.DatetimeIndex, list[dict]]:
    loaded = []
    all_dates: pd.DatetimeIndex | None = None
    for label, path, weight in sources:
        df = _read_csv(path)
        col = _score_col(df)
        dates = pd.DatetimeIndex(df["date"])
        all_dates = dates if all_dates is None else all_dates.union(dates)
        loaded.append({"label": label, "path": path, "weight": weight, "df": df, "col": col})
    if all_dates is None:
        raise ValueError("No source forecasts found")
    all_dates = all_dates.sort_values()
    for item in loaded:
        df = item["df"].set_index("date").reindex(all_dates)
        y_raw = pd.to_numeric(df[item["col"]], errors="coerce").interpolate(limit_direction="both").fillna(0.0)
        item["dates"] = all_dates
        item["raw"] = y_raw.to_numpy(dtype=float)
        item["norm"] = _norm01(item["raw"])
    return all_dates, loaded


def build_peak_consensus(
    run_dir: Path | None,
    forecast_csvs: list[Path],
    output_prefix: Path,
    top_n: int,
    include_final: bool,
    peak_floor: float,
    max_peaks_per_source: int,
    peak_window: int,
    min_votes: str,
    title: str,
) -> dict:
    if run_dir is not None:
        sources = _source_forecasts_from_run(run_dir, top_n=top_n, include_final=include_final)
    else:
        sources = [(path.stem, path, 1.0) for path in forecast_csvs]
    dates, loaded = _align_sources(sources)

    n_sources = len(loaded)
    if n_sources == 0:
        raise ValueError("No forecast sources available")
    if min_votes == "all":
        min_vote_count = n_sources
    else:
        min_vote_count = max(1, int(min_votes))

    for item in loaded:
        peaks = _detect_peaks(
            item["norm"],
            floor=peak_floor,
            max_peaks=max_peaks_per_source,
            min_separation=max(1, int(peak_window) + 1),
        )
        item["peaks"] = peaks

    rows = []
    discrete_rows = []
    for i, day in enumerate(dates):
        voters = []
        weighted_vote = 0.0
        total_weight = sum(float(item["weight"]) for item in loaded)
        max_norm = 0.0
        mean_norm = 0.0
        discrete_row = {"date": day.date().isoformat()}
        for item in loaded:
            near_peak = any(abs(i - p) <= peak_window for p in item["peaks"])
            discrete_row[_safe_col_name(item["label"])] = int(near_peak)
            max_norm = max(max_norm, float(item["norm"][i]))
            mean_norm += float(item["norm"][i])
            if near_peak:
                voters.append(item["label"])
                weighted_vote += float(item["weight"])
        mean_norm /= n_sources
        vote_count = len(voters)
        consensus = vote_count / float(n_sources)
        weighted_consensus = weighted_vote / total_weight if total_weight > 0 else consensus
        final_support = consensus if vote_count >= min_vote_count else 0.0
        rows.append(
            {
                "date": day.date().isoformat(),
                "peak_vote_count": vote_count,
                "source_count": n_sources,
                "peak_consensus": consensus,
                "weighted_peak_consensus": weighted_consensus,
                "final_peak_support": final_support,
                "max_normalized_signal": max_norm,
                "mean_normalized_signal": mean_norm,
                "active": int(vote_count >= min_vote_count),
                "voters": " | ".join(voters),
            }
        )
        discrete_row["peak_vote_count"] = vote_count
        discrete_row["source_count"] = n_sources
        discrete_row["peak_consensus"] = consensus
        discrete_row["weighted_peak_consensus"] = weighted_consensus
        discrete_row["final_peak_support"] = final_support
        discrete_row["active"] = int(vote_count >= min_vote_count)
        discrete_rows.append(discrete_row)

    out_df = pd.DataFrame(rows)
    discrete_df = pd.DataFrame(discrete_rows)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_prefix.with_suffix(".csv")
    discrete_csv_path = output_prefix.with_name(output_prefix.name + "_discrete").with_suffix(".csv")
    json_path = output_prefix.with_suffix(".json")
    png_path = output_prefix.with_suffix(".png")
    discrete_png_path = output_prefix.with_name(output_prefix.name + "_discrete").with_suffix(".png")
    out_df.to_csv(csv_path, index=False)
    discrete_df.to_csv(discrete_csv_path, index=False)

    manifest = {
        "run_dir": str(run_dir) if run_dir else None,
        "sources": [
            {
                "label": item["label"],
                "path": str(item["path"]),
                "weight": item["weight"],
                "peak_dates": [dates[i].date().isoformat() for i in sorted(item["peaks"])],
            }
            for item in loaded
        ],
        "top_n": top_n,
        "include_final": include_final,
        "peak_floor": peak_floor,
        "max_peaks_per_source": max_peaks_per_source,
        "peak_window": peak_window,
        "min_votes": min_votes,
        "min_vote_count": min_vote_count,
        "csv": str(csv_path),
        "discrete_csv": str(discrete_csv_path),
        "png": str(png_path),
        "discrete_png": str(discrete_png_path),
    }
    json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    fig, axes = plt.subplots(3, 1, figsize=(16, 11), constrained_layout=True, sharex=True)
    fig.suptitle(title, fontsize=18, fontweight="bold")

    ax = axes[0]
    for item in loaded:
        ax.plot(dates, item["norm"], lw=1.4, alpha=0.65, marker="o", ms=3, label=item["label"])
        if item["peaks"]:
            peak_idx = sorted(item["peaks"])
            ax.scatter(dates[peak_idx], item["norm"][peak_idx], s=70, edgecolor="black", facecolor="none", zorder=4)
    ax.axhline(peak_floor, color="#475569", linestyle="--", lw=1.1, label=f"peak floor {peak_floor:g}")
    ax.set_ylabel("normalized source forecast")
    ax.set_title("Normalized forecasts and detected peaks")
    ax.legend(loc="upper left", fontsize=7, ncol=2)
    ax.grid(True, color="#d7dde5", linewidth=0.8, alpha=0.6)

    ax = axes[1]
    x = pd.to_datetime(out_df["date"])
    ax.bar(x, out_df["peak_consensus"], width=18, color="#dc2626", alpha=0.75, label="peak vote consensus")
    ax.plot(x, out_df["weighted_peak_consensus"], color="#111827", marker="o", lw=2, label="weighted consensus")
    ax.axhline(min_vote_count / float(n_sources), color="#475569", linestyle="--", lw=1.1, label=f"active threshold {min_vote_count}/{n_sources}")
    ax.set_ylim(-0.02, 1.05)
    ax.set_ylabel("0..1 consensus")
    ax.set_title("Peak votes by forecast date")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, color="#d7dde5", linewidth=0.8, alpha=0.6)

    ax = axes[2]
    ax.plot(x, out_df["final_peak_support"], color="#16a34a", lw=2.5, marker="s", label="FINAL peak-consensus support")
    ax.plot(x, out_df["max_normalized_signal"], color="#f97316", lw=1.6, marker="o", alpha=0.8, label="max normalized signal")
    active = out_df["active"].to_numpy(dtype=bool)
    if active.any():
        ax.scatter(x[active], out_df.loc[active, "final_peak_support"], s=110, edgecolor="black", facecolor="none", zorder=5, label="active consensus peaks")
    ax.set_ylim(-0.02, 1.05)
    ax.set_ylabel("final support")
    ax.set_title("Final 0..1 peak-consensus forecast")
    ax.set_xlabel("Each point/date is the START of its forecast window")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, color="#d7dde5", linewidth=0.8, alpha=0.6)

    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.savefig(png_path, dpi=170)
    plt.close(fig)

    # Separate discrete 0/1 view: one row per source forecast, one column per date.
    source_labels = [item["label"] for item in loaded]
    source_cols = [_safe_col_name(label) for label in source_labels]
    matrix = discrete_df[source_cols].to_numpy(dtype=float).T if source_cols else np.zeros((0, len(dates)))
    fig_h = max(5.5, 2.7 + 0.55 * max(1, len(source_labels)))
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(16, fig_h),
        gridspec_kw={"height_ratios": [max(1.5, 0.55 * max(1, len(source_labels))), 2.2]},
        constrained_layout=True,
        sharex=True,
    )
    fig.suptitle(title + " - discretized 0/1 peak votes", fontsize=17, fontweight="bold")

    ax = axes[0]
    ax.imshow(matrix, aspect="auto", cmap=matplotlib.colors.ListedColormap(["#e5e7eb", "#dc2626"]), vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(source_labels)))
    ax.set_yticklabels([_wrap_label(label) for label in source_labels], fontsize=8)
    ax.set_title("Discretized source forecasts: 0 = low, 1 = detected peak")
    ax.set_ylabel("source forecast")
    ax.set_xticks(np.arange(len(dates)))
    ax.set_xticklabels([d.date().isoformat() for d in dates], rotation=45, ha="right", fontsize=8)
    for y in range(len(source_labels)):
        for x_i in range(len(dates)):
            ax.text(
                x_i,
                y,
                "1" if matrix[y, x_i] >= 0.5 else "0",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if matrix[y, x_i] >= 0.5 else "#374151",
                fontweight="bold" if matrix[y, x_i] >= 0.5 else "normal",
            )

    ax = axes[1]
    x_num = np.arange(len(dates))
    ax.bar(x_num, discrete_df["peak_consensus"], color="#dc2626", alpha=0.75, label="vote consensus = votes/sources")
    ax.plot(x_num, discrete_df["final_peak_support"], color="#16a34a", marker="s", lw=2.4, label="final active support")
    ax.axhline(min_vote_count / float(n_sources), color="#374151", linestyle="--", lw=1.1, label=f"active threshold {min_vote_count}/{n_sources}")
    for x_i, row in discrete_df.iterrows():
        ax.text(
            x_i,
            min(1.02, float(row["peak_consensus"]) + 0.04),
            f"{int(row['peak_vote_count'])}/{n_sources}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold" if int(row["active"]) else "normal",
        )
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("0..1")
    ax.set_title("Overlap of 0/1 peak votes")
    ax.set_xticks(x_num)
    ax.set_xticklabels([d.date().isoformat() for d in dates], rotation=45, ha="right")
    ax.set_xlabel("Each point/date is the START of its forecast window")
    ax.grid(True, axis="y", color="#d7dde5", linewidth=0.8, alpha=0.65)
    ax.legend(loc="upper left", fontsize=9)

    fig.savefig(discrete_png_path, dpi=170)
    plt.close(fig)

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuse forecast CSVs by normalized peak consensus.")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--forecast-csv", action="append", default=[])
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--top-n", type=int, default=6)
    parser.add_argument("--include-final", action="store_true")
    parser.add_argument("--peak-floor", type=float, default=0.55)
    parser.add_argument("--max-peaks-per-source", type=int, default=2)
    parser.add_argument("--peak-window", type=int, default=0)
    parser.add_argument("--min-votes", default="2", help="integer vote threshold or 'all'")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else None
    forecast_csvs = [Path(p) for p in args.forecast_csv]
    title = args.title or "Normalized peak-consensus forecast fusion"
    manifest = build_peak_consensus(
        run_dir=run_dir,
        forecast_csvs=forecast_csvs,
        output_prefix=Path(args.output_prefix),
        top_n=args.top_n,
        include_final=args.include_final,
        peak_floor=args.peak_floor,
        max_peaks_per_source=args.max_peaks_per_source,
        peak_window=args.peak_window,
        min_votes=args.min_votes,
        title=title,
    )
    print(f"CSV:  {manifest['csv']}")
    print(f"DISCRETE CSV: {manifest['discrete_csv']}")
    print(f"JSON: {Path(manifest['csv']).with_suffix('.json')}")
    print(f"PNG:  {manifest['png']}")
    print(f"DISCRETE PNG: {manifest['discrete_png']}")


if __name__ == "__main__":
    main()

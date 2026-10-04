"""Publication-style Phase 1 versus Phase 2 comparison chart."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def set_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "figure.titlesize": 14,
            "grid.alpha": 0.30,
            "grid.linestyle": "--",
        }
    )


def _successful(frame: pd.DataFrame) -> pd.DataFrame:
    objective = pd.to_numeric(frame.get("objective_loss"), errors="coerce")
    mask = objective.notna() & np.isfinite(objective) & (objective < 500)
    if "status" in frame.columns:
        mask &= frame["status"].fillna("success").eq("success")
    return frame.loc[mask].copy()


def _fmt(value: object, digits: int = 4, percent: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not np.isfinite(number):
        return "N/A"
    return f"{number * 100:.1f}%" if percent else f"{number:.{digits}f}"


def plot_phase2_convergence_report(
    phase1_trials_csv: Path | str,
    phase2_dir: Path | str,
    model_type: str,
    output_png: Path | str,
    output_pdf: Path | str | None = None,
) -> dict[str, str]:
    """Render the comparison and return paths; raise on missing successful data."""
    normalized_model = "deep_learning" if model_type.lower() == "deep" else model_type.lower()
    phase1_path = Path(phase1_trials_csv)
    phase2_path = Path(phase2_dir)
    output_png_path = Path(output_png)
    meta_csv = phase2_path / f"meta_trials_{normalized_model}.csv"
    if not phase1_path.exists():
        raise FileNotFoundError(f"Phase 1 trials not found: {phase1_path}")
    if not meta_csv.exists():
        raise FileNotFoundError(f"Phase 2 trials not found: {meta_csv}")

    phase1 = _successful(pd.read_csv(phase1_path))
    phase2_all = pd.read_csv(meta_csv)
    phase2 = _successful(phase2_all)
    if phase1.empty:
        raise ValueError("Phase 1 CSV has no successful finite trials")
    if phase2.empty:
        raise ValueError("Phase 2 has no successful trials to plot")

    phase1_loss = pd.to_numeric(phase1["objective_loss"])
    phase2_loss = pd.to_numeric(phase2["objective_loss"])
    phase1_best = float(phase1_loss.min())
    phase2_best = float(phase2_loss.min())
    phase1_winner = phase1.loc[phase1_loss.idxmin()]
    phase2_winner = phase2.loc[phase2_loss.idxmin()]

    set_publication_style()
    figure, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=160)
    figure.suptitle(
        f"DLVS-Wave Phase 2 Deep Meta-Optimization [{normalized_model.upper()}]\n"
        f"Phase 1: {len(phase1)} successful (best {phase1_best:.4f}) · "
        f"Phase 2: {len(phase2)}/{len(phase2_all)} successful (best {phase2_best:.4f})",
        y=0.985,
        fontweight="bold",
    )

    axis = axes[0, 0]
    phase1_x = np.arange(len(phase1))
    phase2_x = len(phase1) + np.arange(len(phase2))
    axis.plot(phase1_x, phase1_loss.cummin(), color="#0369A1", label="Phase 1 cumulative best")
    axis.plot(phase2_x, phase2_loss.cummin(), color="#DC2626", label="Phase 2 cumulative best")
    axis.axhline(phase1_best, color="#0369A1", linestyle=":", alpha=0.7)
    axis.axvline(len(phase1) - 0.5, color="#475569", linestyle="--", label="Phase hand-off")
    axis.set(title="Sequential convergence", xlabel="Successful evaluated trials", ylabel="Objective loss")
    axis.grid(True)
    axis.legend()

    axis = axes[0, 1]
    boxes = axis.boxplot(
        [phase1_loss.values, phase2_loss.values],
        tick_labels=[f"Phase 1\nN={len(phase1)}", f"Phase 2\nN={len(phase2)}"],
        patch_artist=True,
        widths=0.45,
        showmeans=True,
    )
    for box, color in zip(boxes["boxes"], ("#0EA5E9", "#EF4444")):
        box.set_facecolor(color)
        box.set_alpha(0.38)
    axis.set(title="Successful-search distributions", ylabel="Objective loss")
    axis.grid(True, axis="y")

    axis = axes[1, 0]
    required_metrics = {"val_mse", "val_f1_score"}
    if required_metrics.issubset(phase1.columns) and required_metrics.issubset(phase2.columns):
        axis.scatter(
            phase1["val_mse"], phase1["val_f1_score"] * 100, color="#0284C7", alpha=0.30, s=24,
            label="Phase 1",
        )
        axis.scatter(
            phase2["val_mse"], phase2["val_f1_score"] * 100, color="#DC2626", alpha=0.70, s=38,
            marker="^", label="Phase 2",
        )
        axis.scatter(
            [phase2_winner["val_mse"]], [phase2_winner["val_f1_score"] * 100],
            color="#F59E0B", edgecolors="black", s=170, marker="*", zorder=5, label="Phase 2 best objective",
        )
        axis.legend()
    else:
        axis.text(0.5, 0.5, "MSE/F1 columns unavailable", ha="center", va="center", transform=axis.transAxes)
    axis.set(
        title="Validation trade-off (not a claimed Pareto frontier)",
        xlabel="Validation MSE (lower is better)",
        ylabel="Validation F1 (%) (higher is better)",
    )
    axis.grid(True)

    axis = axes[1, 1]
    axis.axis("off")
    rows = [
        ["Metric / parameter", "Phase 1 best", "Phase 2 best", "Phase 2 − Phase 1"],
        ["Objective loss", _fmt(phase1_best), _fmt(phase2_best), _fmt(phase2_best - phase1_best)],
        ["Validation MSE", _fmt(phase1_winner.get("val_mse")), _fmt(phase2_winner.get("val_mse")),
         _fmt(float(phase2_winner.get("val_mse", np.nan)) - float(phase1_winner.get("val_mse", np.nan)))],
        ["Validation F1", _fmt(phase1_winner.get("val_f1_score"), percent=True),
         _fmt(phase2_winner.get("val_f1_score"), percent=True),
         _fmt(float(phase2_winner.get("val_f1_score", np.nan)) - float(phase1_winner.get("val_f1_score", np.nan)), percent=True)],
        ["Depression MAE", _fmt(phase1_winner.get("val_depression_mae")),
         _fmt(phase2_winner.get("val_depression_mae")),
         _fmt(float(phase2_winner.get("val_depression_mae", np.nan)) - float(phase1_winner.get("val_depression_mae", np.nan)))],
        ["Train start", str(phase1_winner.get("train_start_date", "N/A")),
         str(phase2_winner.get("train_start_date", "N/A")), "—"],
        ["Window before / after", f"{phase1_winner.get('window_before', 'N/A')} / {phase1_winner.get('window_after', 'N/A')}",
         f"{phase2_winner.get('window_before', 'N/A')} / {phase2_winner.get('window_after', 'N/A')}", "—"],
        ["Background ratio", _fmt(phase1_winner.get("background_sample_ratio"), digits=2),
         _fmt(phase2_winner.get("background_sample_ratio"), digits=2),
         _fmt(float(phase2_winner.get("background_sample_ratio", np.nan)) - float(phase1_winner.get("background_sample_ratio", np.nan)), digits=2)],
    ]
    table = axis.table(cellText=rows, loc="center", cellLoc="center", colWidths=[0.29, 0.24, 0.24, 0.23])
    table.auto_set_font_size(False)
    table.set_fontsize(8.4)
    table.scale(1.0, 1.52)
    for column in range(4):
        table[(0, column)].set_facecolor("#1E293B")
        table[(0, column)].set_text_props(color="white", fontweight="bold")
    for row in range(1, len(rows)):
        for column in range(4):
            table[(row, column)].set_facecolor("#F8FAFC" if row % 2 == 0 else "#FFFFFF")

    figure.text(
        0.5,
        0.012,
        "Caution: Phase 2 reuses the Phase 1 selection-validation protocol; confirm the winner on an untouched later time block.",
        ha="center",
        fontsize=8.5,
        color="#7F1D1D",
    )
    figure.tight_layout(rect=[0.0, 0.035, 1.0, 0.95])
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_png_path, dpi=200, bbox_inches="tight")
    paths = {"png": str(output_png_path)}
    if output_pdf is not None:
        pdf_path = Path(output_pdf)
        figure.savefig(pdf_path, bbox_inches="tight")
        paths["pdf"] = str(pdf_path)
    plt.close(figure)
    return paths

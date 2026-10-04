import os
import re
import json
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from pathlib import Path
from matplotlib.patches import Rectangle

# Min-max scaling helper (global)
def global_minmax(series, full_df_series):
    lo = full_df_series.min()
    hi = full_df_series.max()
    if abs(hi - lo) < 1e-12:
        return np.zeros_like(series)
    return (series - lo) / (hi - lo)

def parse_args():
    parser = argparse.ArgumentParser(description="Generate ensemble risk analysis from multiple resolutions.")
    parser.add_argument("--run-dir", default="/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-cpu3-nohist-hyper-top50-20260612-013405", help="Path to the run directory containing <num>d folders.")
    parser.add_argument("--output-dir", default=None, help="Path to the output directory. Defaults to <run-dir>/fusion.")
    parser.add_argument("--score-col", default="adjusted_target_score", help="Score column to analyze (e.g., adjusted_target_score or target_fused_score).")
    parser.add_argument("--title", default=None, help="Custom title for the ensemble chart. If not set, generated automatically.")
    parser.add_argument("--interp-kind", default="linear", choices=["linear", "nearest", "zero", "slinear", "quadratic", "cubic", "previous", "next"], help="SciPy interpolation kind (default: linear).")
    parser.add_argument("--res-weights", default=None, help="Comma-separated custom resolution weights (e.g. 0.5,1.0,1.5). Must match number of folders.")
    parser.add_argument("--threshold", default=None, help="Custom magnitude threshold (e.g., 7.9). If not provided, deduced from countercheck plan.")
    parser.add_argument("--region", default=None, help="Custom region name (e.g., Japan). If not provided, deduced from countercheck plan.")
    return parser.parse_args()

def main():
    args = parse_args()
    run_dir = Path(args.run_dir)
    score_col = args.score_col
    interp_kind = args.interp_kind
    
    if not run_dir.exists():
        raise SystemExit(f"Error: Run directory {run_dir} does not exist.")
        
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "fusion"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Detect resolution folders (e.g., 30d, 7d, 3d)
    folders = []
    for p in run_dir.iterdir():
        if p.is_dir():
            m = re.match(r'^(\d+)d$', p.name)
            if m:
                days = int(m.group(1))
                csv_file = p / "target_risk_adjudication_timeline.csv"
                if csv_file.exists():
                    folders.append((days, p, csv_file))
                    
    if not folders:
        raise SystemExit(f"Error: No resolution subdirectories (e.g., '30d') containing target_risk_adjudication_timeline.csv found in {run_dir}")
        
    # Sort folders by days in descending order (e.g., 30d, 7d, 3d)
    folders.sort(key=lambda x: x[0], reverse=True)
    N = len(folders)
    print(f"Detected {N} resolution folders: {[f'{d}d' for d, _, _ in folders]}")
    
    # 2. Assign weights (custom vs dynamic resolution gradient)
    if args.res_weights:
        res_weights = [float(w.strip()) for w in args.res_weights.split(",")]
        if len(res_weights) != N:
            raise SystemExit(f"Error: Number of custom weights ({len(res_weights)}) does not match number of detected folders ({N})")
    else:
        if N == 1:
            res_weights = [1.0]
        else:
            res_weights = np.linspace(0.5, 1.5, N)
        
    print(f"Using resolution weights: {list(res_weights)}")
    
    # 3. Read target grid (highest resolution = last folder in sorted list)
    target_days, target_folder, target_csv = folders[-1]
    print(f"Target grid: {target_days}d ({target_folder})")
    
    grid_df = pd.read_csv(target_csv)
    grid_df['date_parsed'] = pd.to_datetime(grid_df['date'])
    grid_df['timestamp'] = grid_df['date_parsed'].map(lambda x: x.timestamp())
    grid_df = grid_df.sort_values('date_parsed').copy()
    
    grid_timestamps = grid_df['timestamp'].values
    
    # 4. Load all files and prepare interpolation functions
    interpolated_scores = []
    interpolated_consensus = []
    
    # Keep track of global min/max for each run to normalize
    for j, (days, folder, csv_path) in enumerate(folders):
        df = pd.read_csv(csv_path)
        df['date_parsed'] = pd.to_datetime(df['date'])
        df['timestamp'] = df['date_parsed'].map(lambda x: x.timestamp())
        
        # Parse scores
        scores = df[score_col].values
        # Global min/max normalization
        lo, hi = df[score_col].min(), df[score_col].max()
        if abs(hi - lo) < 1e-12:
            norm_scores = np.zeros_like(scores)
        else:
            norm_scores = (scores - lo) / (hi - lo)
            
        # Interpolate normalized scores using specified interp_kind
        f_score = interp1d(df['timestamp'].values, norm_scores, kind=interp_kind, fill_value="extrapolate")
        interp_score_grid = f_score(grid_timestamps)
        interpolated_scores.append(interp_score_grid)
        
        # Interpolate consensus using specified interp_kind
        f_cons = interp1d(df['timestamp'].values, df['target_consensus'].values, kind=interp_kind, fill_value="extrapolate")
        interp_cons_grid = np.clip(f_cons(grid_timestamps), 0, 1)
        interpolated_consensus.append(interp_cons_grid)
        
    # 5. Compute ensemble contributions and total risk
    contr_list = []
    for j in range(N):
        c = (interpolated_scores[j] * interpolated_consensus[j] * res_weights[j]) / float(N)
        contr_list.append(c)
        
    ensemble_risk = sum(contr_list)
    ensemble_risk_scaled = global_minmax(ensemble_risk, pd.Series(ensemble_risk))
    
    # 6. Save results to CSV
    output_df = pd.DataFrame({
        'date': grid_df['date'].values,
        'window_end': grid_df['window_end'].values,
        'ensemble_risk': ensemble_risk,
        'ensemble_risk_scaled': ensemble_risk_scaled
    })
    
    for j, (days, _, _) in enumerate(folders):
        output_df[f'c_{days}d'] = interpolated_consensus[j]
        output_df[f'norm_{days}d'] = interpolated_scores[j]
        output_df[f'contr_{days}d'] = contr_list[j]
        
    csv_out = output_dir / "ensemble_timeline_results.csv"
    output_df.to_csv(csv_out, index=False)
    print(f"Saved timeline CSV to {csv_out}")
    
    # 7. Detect local peaks (y[i] > y[i-1] and y[i] > y[i+1])
    peak_indices = []
    for i in range(1, len(ensemble_risk) - 1):
        if ensemble_risk[i] > ensemble_risk[i-1] and ensemble_risk[i] > ensemble_risk[i+1]:
            peak_indices.append(i)
            
    # Find global absolute peak index
    abs_peak_idx = np.argmax(ensemble_risk)
    max_val = ensemble_risk[abs_peak_idx]
    
    # 8. Deduce binary threshold and region from countercheck plan jsons (no hardcoding)
    threshold = args.threshold if getattr(args, 'threshold', None) else None
    region = args.region if getattr(args, 'region', None) else None
    
    # If not provided, try to load from countercheck_plan.json
    if threshold is None or region is None:
        for j, (days, folder, csv_path) in enumerate(folders):
            plan_json = csv_path.parent / "countercheck_plan.json"
            if plan_json.exists():
                try:
                    with open(plan_json) as f:
                        plan_data = json.load(f)
                    if threshold is None:
                        val = plan_data.get("binary_threshold")
                        if val is not None:
                            threshold = str(val)
                            print(f"Deduced magnitude threshold: M{threshold} (from {plan_json.name})")
                    if region is None:
                        zones = plan_data.get("target_zones")
                        if zones and isinstance(zones, list):
                            region = ", ".join([z.title() for z in zones])
                            print(f"Deduced region: {region} (from {plan_json.name})")
                except Exception as e:
                    print(f"Warning: failed to read from {plan_json}: {e}")
                    
    # Fallbacks if still None
    if threshold is None:
        threshold = "7.9"
    if region is None:
        region = "Japan"
                
    # Prepare dangerous slots list
    dangerous_slots = []
    for idx in peak_indices:
        slot_date = grid_df['date'].values[idx]
        slot_end = grid_df['window_end'].values[idx]
        risk_val = ensemble_risk[idx]
        is_abs = (idx == abs_peak_idx)
        label = "[ABSOLUTE PEAK]" if is_abs else "[LOCAL PEAK]"
        dangerous_slots.append({
            'text': f"Slot {slot_date} -> {slot_end} (Risk: {risk_val*100:.1f}%) {label}",
            'is_absolute': is_abs
        })
        
    # Sort chronologically by the text value (starts with date)
    dangerous_slots.sort(key=lambda x: x['text'])
    
    # ----------------- PLOTTING -----------------
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    fig, ax = plt.subplots(figsize=(12, 7.8))
    
    dates_str = [d.strftime('%Y-%m-%d') for d in pd.to_datetime(grid_df['date'].values)]
    x_indices = np.arange(len(dates_str))
    bar_width = 0.55
    
    # Premium color palette
    colors = ['#4c78a8', '#f58518', '#72b7b2', '#e15759', '#b279a2', '#59a14f', '#edc948']
    
    # Plot stacked bars
    bottoms = np.zeros(len(grid_df))
    for j in range(N):
        days, _, _ = folders[j]
        contr = contr_list[j]
        color = colors[j % len(colors)]
        ax.bar(x_indices, contr, width=bar_width, bottom=bottoms,
               label=f"{days}d (Resolution Weight = {res_weights[j]:.2f})",
               color=color, zorder=3)
        bottoms += contr
        
    # Plot envelope line
    line_ens = ax.plot(x_indices, ensemble_risk, color='#e15759', linewidth=3.0, marker='o', markersize=8, label='Ensemble Risk Envelope', zorder=4)
    
    # Draw borders and text labels for PEAK bars
    for idx in peak_indices:
        total_height = ensemble_risk[idx]
        rect = Rectangle((idx - bar_width/2.0, 0), bar_width, total_height,
                         facecolor='none', edgecolor='#222222', linewidth=3.0, linestyle='-', zorder=5)
        ax.add_patch(rect)
        
        if idx == abs_peak_idx:
            # 1. Determine which stack segment total_height / 2.0 falls into to select text color
            target_y = total_height / 2.0
            segment_color = "#72b7b2"  # fallback
            stack_bottom = 0.0
            for j in range(N):
                contr_val = contr_list[j][idx]
                stack_top = stack_bottom + contr_val
                if stack_bottom <= target_y <= stack_top:
                    segment_color = colors[j % len(colors)]
                    break
                stack_bottom = stack_top
                
            # Parse hex to RGB and compute luminance
            try:
                hex_color = segment_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                luminance = 0.299 * (r / 255.0) + 0.587 * (g / 255.0) + 0.114 * (b / 255.0)
                contrast_color = '#111111' if luminance > 0.55 else '#ffffff'
            except Exception:
                contrast_color = '#ffffff'

            # Draw quota annotation with arrow pointing to the absolute peak bar (without repeating percentage)
            ax.annotate(f"M{threshold}+\n[ABS PEAK]",
                        xy=(idx, total_height),
                        xytext=(idx, total_height + 0.16),
                        arrowprops=dict(facecolor='#222222', shrink=0.05, width=1.2, headwidth=5),
                        ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#222222',
                        bbox=dict(boxstyle="round,pad=0.3", fc="#ffdddd", ec="#e15759", alpha=0.9),
                        zorder=6)
            
            # Write vertical risk percentage inside the bar (negative vertical = rotation=-90, no bbox, high contrast)
            ax.text(idx, total_height / 2.0, f"{max_val*100:.1f}%",
                    ha='center', va='center', rotation=-90, color=contrast_color, fontweight='bold', fontsize=11,
                    zorder=6)
        else:
            # Standard peak label above bar
            ax.text(idx, total_height + 0.02, "[PEAK]", ha='center', va='bottom', fontsize=9.5, fontweight='bold', color='#222222', zorder=6)
        
    # Configure axes and custom/auto title
    plot_title = args.title if args.title else f"{region} M{threshold}+ Risk Ensemble (Stacked Resolution Gradient - {score_col.replace('_', ' ').title()})"
    ax.set_title(plot_title, fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel("Weighted Risk (Consensus + Resolution Gradient)", fontsize=12)
    ax.set_xlabel("Forecast Window Start Date", fontsize=12)
    
    # Increase Y limit to 1.25 to leave ample empty space at the top of the axes
    ax.set_ylim(-0.02, 1.25)
    
    ax.set_xticks(x_indices)
    ax.set_xticklabels(dates_str, rotation=45)
    ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='none')
    ax.grid(True, axis='y', alpha=0.3)
    
    # Place dynamic legend INSIDE the axes at the top-left area
    x_box_pos = 0.02
    y_box_pos = 0.95  # Start from near the top of the axes
    
    # Draw background box (Rectangle) in axis coordinates
    # We dynamically compute height based on the number of lines
    box_height = 0.06 + len(dangerous_slots) * 0.045
    rect_box = Rectangle((0.015, y_box_pos - box_height + 0.02), 0.58, box_height,
                         transform=ax.transAxes, facecolor='#fcf8f2', edgecolor='#f58518',
                         alpha=0.95, linewidth=1.2, zorder=5)
    ax.add_patch(rect_box)
    
    # Render dynamic legend text inside axes
    ax.text(x_box_pos, y_box_pos, "DANGEROUS TIME SLOTS (DYNAMICALLY DETECTED BY PYTHON):",
            transform=ax.transAxes, fontsize=9.5, fontweight='bold', family='monospace', color='#222222',
            va='top', zorder=6)
             
    current_y = y_box_pos
    for slot in dangerous_slots:
        current_y -= 0.042
        text_str = f"• {slot['text']}"
        if slot['is_absolute']:
            # Render absolute peak in red and italic!
            ax.text(x_box_pos, current_y, text_str, transform=ax.transAxes,
                    fontsize=9.0, fontweight='bold', style='italic', family='monospace', color='#e15759',
                    va='top', zorder=6)
        else:
            ax.text(x_box_pos, current_y, text_str, transform=ax.transAxes,
                    fontsize=9.0, fontweight='normal', style='normal', family='monospace', color='#222222',
                    va='top', zorder=6)
                     
    # Use standard bottom margins to comfortably fit rotated dates (no overlapping)
    plt.subplots_adjust(bottom=0.16, left=0.08, right=0.95, top=0.92)
    
    png_out = output_dir / "ensemble_chart.png"
    plt.savefig(png_out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {png_out}")
    
    # 8. Write report in English
    md_out = output_dir / "ensemble_risk_analysis.md"
    
    legend_title = "DANGEROUS TIME SLOTS (DYNAMICALLY DETECTED BY PYTHON):"
    legend_body = "\n".join([f"• {slot['text']}" for slot in dangerous_slots])
    full_legend_text = f"{legend_title}\n{legend_body}"
    
    md_content = f"""# {region} M{threshold}+ Risk Ensemble Analysis (Resolution Gradient)

This document presents the synthesis and analysis of the ensemble of the {N} temporal resolutions ({', '.join([f'{d}d' for d, _, _ in folders])}) for the analysis **{run_dir.name}**.

---

## 1. Ponderation and Calculation Methodology

1. **Recalibration [0, 1]:** Each series is normalized individually using its global minimum and maximum values.
2. **Combined Weighting:**
   The weight of each run at every time slot is the product of:
   * **Consensus (`target_consensus`):** fraction of models in consensus, from 0.0 to 1.0.
   * **Resolution Gradient ($R$):** Linearly spaced weights between 0.5 (lowest resolution) and 1.5 (highest resolution) unless overridden by `--res-weights`.
3. **Ensemble Bar Calculation (Weighted Sum / {N}):**
   The total bar height represents the weighted average risk:
   $$Ensemble\\_Risk = \\frac{{\\sum R_j \\cdot w_{{cons, j}} \\cdot N_j}}{{{N}}}$$
   This value varies linearly between **0%** and **100%**, giving more weight to high-resolution (more precise) estimates.

---

## 2. Timeline Results ({score_col.replace('_', ' ').title()})

| Start Date | Consensus ({'/'.join([f'{d}d' for d, _, _ in folders])}) | Score Norm ({'/'.join([f'{d}d' for d, _, _ in folders])}) | Risk Ensemble | Scaled Risk |
| :--- | :---: | :---: | :---: | :---: |
"""

    for idx, row in output_df.iterrows():
        cons_parts = [f"{row[f'c_{d}d']:.2f}" for d, _, _ in folders]
        norm_parts = [f"{row[f'norm_{d}d']:.2f}" for d, _, _ in folders]
        cons_str = " / ".join(cons_parts)
        norm_str = " / ".join(norm_parts)
        
        is_peak = idx in peak_indices
        is_abs_peak = idx == abs_peak_idx
        if is_abs_peak:
            peak_marker = " [ABS PEAK]"
        elif is_peak:
            peak_marker = " [PEAK]"
        else:
            peak_marker = ""
            
        md_content += f"| **{row['date']}**{peak_marker} | {cons_str} | {norm_str} | **{row['ensemble_risk'] * 100:.2f}%** | {row['ensemble_risk_scaled'] * 100:.2f}% |\n"

    md_content += f"""
The complete timeline CSV is available at:
* [ensemble_timeline_results.csv](file://{csv_out.absolute()})

---

## 3. Dangerous Time Slots (Dynamically Detected Peaks)

The following time slots were identified by the Python script:

```text
{full_legend_text}
```

---

## 4. Ensemble Stacked Bar Chart (with Peak Borders)

The chart below shows the stacked risk components for each time slot. The columns highlighted with a bold black border represent **local peaks** (points where risk is strictly higher than both the preceding and succeeding days). The absolute maximum peak is labeled as **[ABS PEAK]**.

![Ensemble Chart Stacked Peak](file://{png_out.absolute()})
"""
    md_out.write_text(md_content)
    print(f"Saved report to {md_out}")

if __name__ == "__main__":
    main()

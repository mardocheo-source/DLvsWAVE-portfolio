#!/usr/bin/env bash
# DLvsWAVE train-max run
# Generated: 2026-04-28 21:34:14 (local)
# Dataset:   master_with_usgs_core.csv (Japan FY2026 30D L5 H OVN)
# Notes:     keep-best 3 / keep-worst 2; LCS rule cap 8; subsumption 0.7;
#            twin invertito ON; auto-inherit L01.
# Usage:     bash commands/train-max_20260428-213414.sh   (lancia da DLvsWAVE/)

set -e

cd "$(dirname "$0")/.."

# PYTHONUNBUFFERED + python -u per evitare il buffering quando l'output
# passa dentro `tee` (altrimenti non vedi nulla a video finche' non riempie
# il buffer di Python, che con piu' di 100 trial significa silenzio lungo).
export PYTHONUNBUFFERED=1

./.venv/bin/python -u cli.py train-max \
  --task /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/master_with_usgs_core.csv \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  --metric-mode auto --metric-target-threshold 0.1 --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 --target-window-event-count 1 \
  --target-window-pre-records 5 --target-window-post-records 3 \
  --isolated-event-windows \
  --backtest-event-windows --backtest-event-count 2 --backtest-step-events 1 \
  --backtest-pre-records 5 --backtest-post-records 3 \
  --backtest-min-train-events 2 --backtest-max-windows 1 \
  --backtest-recency-weight exp --backtest-recency-strength 1.0 \
  --recent-validation-window --recent-validation-event-count 1 \
  --recent-validation-pre-records 5 --recent-validation-post-records 3 \
  --recent-validation-weight 3.0 \
  --train-recency-weight exp --train-recency-strength 1.0 \
  --train-event-weight auto --train-max-event-weight 8.0 \
  --forecast-start-date 2026-03-05 --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --enable-lcs-in-max --hybrid-lcs \
  --hybrid-partners passthrough:ridge,random_projection:ridge,deep:tiny,deep:small \
  --hybrid-modes and,weighted --hybrid-alphas 0.35,0.5,0.75 --hybrid-threshold 0.5 \
  --final-eval-rank-power 1.0 --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight 3.0 \
  --final-eval-best-fraction 0.25 --final-eval-worst-fraction 0.10 \
  --final-eval-shape-power 1.5 \
  --auto-inherit-levels 1 \
  --best 5 --seeds 4:4 --max-iter 300 \
  --keep-best 3 --keep-worst 2 \
  --invert-twin-min-std 1e-4 \
  --lcs-max-active-conditions 8 \
  --lcs-min-fitness-for-subsumption 0.7 \
  --db japan_trainmax_v3.db \
  --verbose 2>&1 | tee /tmp/dlvswave_run_20260428-213414.log

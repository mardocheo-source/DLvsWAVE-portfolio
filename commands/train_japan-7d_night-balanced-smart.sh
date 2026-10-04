#!/usr/bin/env bash
# DLvsWAVE night run bilanciato per Japan 7D.
# Per seed: 4 BANK + 4 LCS + 4 HYBRID = 12 trial.
# Con --seeds 4:4 e backtest(1)+recent(1): circa 96 trial benchmark totali.
set -e

cd "$(dirname "$0")/.."

export PYTHONUNBUFFERED=1

./.venv/bin/python -u cli.py train \
  --task /mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-7d-focus-noise/master_with_usgs_core_astrofmt.csv \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  --banks passthrough,random_projection,chebyshev,morlet_wavelet \
  --readouts torch_tiny \
  --lcs-presets tiny,default,large,wide \
  --hybrid-lcs \
  --hybrid-partners morlet_wavelet:torch_wide \
  --hybrid-modes weighted \
  --hybrid-alphas 0.5 \
  --hybrid-threshold 0.5 \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 \
  --target-window-event-count 1 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --isolated-event-windows \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 2 \
  --backtest-max-windows 1 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  --recent-validation-window \
  --recent-validation-event-count 1 \
  --recent-validation-pre-records 5 \
  --recent-validation-post-records 3 \
  --recent-validation-weight 3.0 \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --final-eval-rank-power 1.0 \
  --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight 3.0 \
  --final-eval-best-fraction 0.30 \
  --final-eval-worst-fraction 0.12 \
  --final-eval-shape-power 1.5 \
  --auto-inherit-levels 0 \
  --best 8 \
  --seeds 4:4 \
  --max-iter 300 \
  --keep-best 4 \
  --keep-worst 3 \
  --invert-twin-min-std 1e-4 \
  --lcs-max-active-conditions 8 \
  --lcs-min-fitness-for-subsumption 0.65 \
  --readability-weight 0.35 \
  --readability-floor 0.3 \
  --db japan_train_balanced_7d_mag80_night.db \
  --post-hybrid-artifacts \
  --post-hybrid-mode smart \
  --verbose 2>&1 | tee /tmp/dlvswave_run_japan_7d_night_balanced_smart.log
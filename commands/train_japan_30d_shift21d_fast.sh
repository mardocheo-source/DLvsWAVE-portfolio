#!/usr/bin/env bash
# Pulsar training Japan MAG8.0+ - master 30d shift+21d - forecast Apr-Sep 2026.
#
# Prerequisite master:
#   ./commands/create_master_japan_mag80_30d_shift21d.sh
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/train_japan_30d_shift21d_fast.sh
set -euo pipefail

cd "$(dirname "$0")/.."

MASTER="${MASTER:-/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift21d/master_with_usgs_core_astrofmt.csv}"
LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_30d_shift21d_fast.log}"
DB_FILE="${DB_FILE:-japan_30d_shift21d_fast.db}"

[[ -f "$MASTER" ]] || {
    echo "[ERROR] Master not found: $MASTER" >&2
    echo "        Run first: ./commands/create_master_japan_mag80_30d_shift21d.sh" >&2
    echo "        Expected training-ready master: master_with_usgs_core_astrofmt.csv" >&2
    exit 1
}

[[ -x ./.venv/bin/python ]] || {
    echo "[ERROR] Python venv not found/executable: ./.venv/bin/python" >&2
    exit 1
}

echo "======================================================================"
echo " Japan 30d shift+21d - Pulsar fast training"
echo " Master: $MASTER"
echo " Forecast: 2026-04-01 -> 2026-09-30"
echo " DB: $DB_FILE"
echo " Log: $LOG_FILE"
echo " Jobs: 4"
echo "======================================================================"

export PYTHONUNBUFFERED=1
# Con --jobs 4 limitiamo i thread interni di BLAS/Torch per evitare
# oversubscription: 4 processi restano davvero ~4 CPU invece di esplodere.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

./.venv/bin/python -u cli.py train \
  --task "$MASTER" \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  \
  --banks passthrough,chebyshev,morlet_wavelet \
  --readouts torch_tiny,ridge \
  --lcs-presets tiny,default \
  --hybrid-lcs \
  --hybrid-partners morlet_wavelet:torch_wide,passthrough:ridge,deep:tiny \
  --hybrid-modes weighted,and \
  --hybrid-alphas 0.35,0.5 \
  --hybrid-threshold 0.5 \
  \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 \
  --target-window-event-count 1 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --isolated-event-windows \
  \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 2 \
  --backtest-max-windows 1 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  \
  --recent-validation-window \
  --recent-validation-event-count 1 \
  --recent-validation-pre-records 5 \
  --recent-validation-post-records 3 \
  --recent-validation-weight 3.0 \
  \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  \
  --forecast-start-date 2026-04-01 \
  --forecast-end-date 2026-09-30 \
  --forecast-trainset train2forecast \
  \
  --final-eval-rank-power 1.0 \
  --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight 3.0 \
  --final-eval-best-fraction 0.30 \
  --final-eval-worst-fraction 0.12 \
  --final-eval-shape-power 1.5 \
  --readability-weight 0.35 \
  --readability-floor 0.3 \
  \
  --auto-inherit-levels 0 \
  --seeds 4:4 \
  --max-iter 150 \
  --jobs 4 \
  --best 8 \
  --keep-best 3 \
  --keep-worst 2 \
  --invert-twin-min-std 1e-4 \
  --invert-twin-immediate-threshold 0.08 \
  --lcs-max-active-conditions 8 \
  --lcs-min-fitness-for-subsumption 0.65 \
  \
  --post-hybrid-artifacts \
  --post-hybrid-mode both \
  --post-hybrid-logic and \
  --post-hybrid-normalize auto \
  --post-hybrid-forecast-guard auto \
  --post-hybrid-peak-and \
  --post-hybrid-peak-window 1 \
  --post-hybrid-peak-floor 0.30 \
  --post-hybrid-peak-max 1 \
  --forecast-common-window \
  --forecast-common-source "/mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/pulsar_train-max_best_trials_20260429-183538/post_hybrid_checks12/auto_torch_tiny_X_hyb_default_dntiny_w0p50__and__auto__forecast.csv" \
  --forecast-common-source "/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift15d/pulsar_train_best_trials_20260504-203350/post_hybrid_checks_smart_v13/final_combo/smart____shape_winner_merge__ _ shape_winner _ seed-1_X___peak_winner_merge__ _ peak_winner _ seed-2__and__auto__forecast.csv" \
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

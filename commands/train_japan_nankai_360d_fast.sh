#!/usr/bin/env bash
# Pulsar training for Japan/Nankai historical annual master at 360d resolution.
#
# One record = one 360-day period; date is the period START.
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/train_japan_nankai_360d_fast.sh
set -euo pipefail

cd "$(dirname "$0")/.."

MASTER="${MASTER:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d/master_with_usgs_core_astrofmt.csv}"
LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_fast.log}"
DB_FILE="${DB_FILE:-japan_nankai_360d_fast.db}"
FORECAST_START="${FORECAST_START:-2023-01-01}"
FORECAST_END="${FORECAST_END:-2035-12-31}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-30}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-5}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-3}"

[[ -f "$MASTER" ]] || {
    echo "[ERROR] Master not found: $MASTER" >&2
    echo "        Run first: ./commands/create_master_japan_nankai_360d.sh" >&2
    exit 1
}

[[ -x ./.venv/bin/python ]] || {
    echo "[ERROR] Python venv not found/executable: ./.venv/bin/python" >&2
    exit 1
}

echo "======================================================================"
echo " Japan/Nankai 360d annual - Pulsar training"
echo " Master:        $MASTER"
echo " Forecast:      $FORECAST_START -> $FORECAST_END"
echo " Val lookback:  $VALIDATION_MAX_LOOKBACK_RECORDS records"
echo " Val events:    $VALIDATION_EVENT_COUNT event(s), pre=$VALIDATION_PRE_RECORDS post=$VALIDATION_POST_RECORDS"
echo " Target events: $TARGET_EVENT_COUNT event(s)"
echo " Record meaning: date is period START; one row = one 360d period"
echo " DB:            $DB_FILE"
echo " Log:           $LOG_FILE"
echo " Jobs:          4"
echo "======================================================================"

export PYTHONUNBUFFERED=1
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
  --target-window-event-count "$TARGET_EVENT_COUNT" \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --isolated-event-windows \
  \
  --backtest-event-count 1 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 2 \
  --backtest-max-windows 1 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  \
  --recent-validation-window \
  --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
  --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
  --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
  --recent-validation-weight 3.0 \
  --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
  \
  --lcs-val-event-count "$VALIDATION_EVENT_COUNT" \
  --lcs-val-pre-records "$VALIDATION_PRE_RECORDS" \
  --lcs-val-post-records "$VALIDATION_POST_RECORDS" \
  --deep-validation-metric event_composite \
  --deep-val-event-count "$VALIDATION_EVENT_COUNT" \
  --deep-val-pre-records "$VALIDATION_PRE_RECORDS" \
  --deep-val-post-records "$VALIDATION_POST_RECORDS" \
  \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  \
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date "$FORECAST_END" \
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
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

#!/usr/bin/env bash
# Longer Japan/Nankai 360d annual training profile.
#
# Compared with train_japan_nankai_360d_fast.sh this expands BANK/readout/hybrid
# combinations, while keeping LCS deliberately compact:
#   - only one small LCS preset by default
#   - only 4 active LCS conditions
#   - only 5 exported LCS rules
# Smart post-hybrid accepts up to 3 candidate peaks; the final merge keeps up to 2.
set -euo pipefail

cd "$(dirname "$0")/.."

MASTER="${MASTER:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d/master_with_usgs_core_astrofmt.csv}"
LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_long.log}"
DB_FILE="${DB_FILE:-japan_nankai_360d_long.db}"
FORECAST_START="${FORECAST_START:-2023-01-01}"
FORECAST_END="${FORECAST_END:-2035-12-31}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-30}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-5}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-3}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-0}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-8675309}"
RECENT_VALIDATION_SKIP_IF_UNAVAILABLE="${RECENT_VALIDATION_SKIP_IF_UNAVAILABLE:-0}"

BANKS="${BANKS:-passthrough,random_fourier,prime_fourier,chebyshev,morlet_wavelet,random_projection}"
READOUTS="${READOUTS:-ridge,linear,torch_tiny,torch_small}"
LCS_PRESETS_RUN="${LCS_PRESETS_RUN:-tiny}"
HYBRID_PARTNERS="${HYBRID_PARTNERS:-morlet_wavelet:torch_wide,passthrough:ridge,chebyshev:torch_small,random_fourier:ridge,random_projection:torch_tiny,prime_fourier:ridge,deep:tiny,deep:small}"
HYBRID_MODES="${HYBRID_MODES:-and,or,weighted}"
HYBRID_ALPHAS="${HYBRID_ALPHAS:-0.25,0.35,0.5,0.65}"

SEEDS_SPEC="${SEEDS_SPEC:-4:8}"
MAX_ITER="${MAX_ITER:-240}"
JOBS="${JOBS:-4}"
BEST_N="${BEST_N:-16}"
KEEP_BEST="${KEEP_BEST:-5}"
KEEP_WORST="${KEEP_WORST:-2}"

LCS_MAX_ACTIVE_CONDITIONS="${LCS_MAX_ACTIVE_CONDITIONS:-4}"
LCS_MIN_FITNESS_FOR_SUBSUMPTION="${LCS_MIN_FITNESS_FOR_SUBSUMPTION:-0.55}"
LCS_EXPORT_RULE_COUNT="${LCS_EXPORT_RULE_COUNT:-5}"

POST_HYBRID_TOP_CANDIDATES="${POST_HYBRID_TOP_CANDIDATES:-60}"
POST_HYBRID_TOP_PAIRS="${POST_HYBRID_TOP_PAIRS:-40}"
POST_HYBRID_MAX_RULES="${POST_HYBRID_MAX_RULES:-5}"
POST_HYBRID_MAX_PEAKS="${POST_HYBRID_MAX_PEAKS:-3}"
POST_HYBRID_PEAK_MAX="${POST_HYBRID_PEAK_MAX:-3}"
POST_HYBRID_FINAL_PEAK_MAX="${POST_HYBRID_FINAL_PEAK_MAX:-2}"

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
echo " Japan/Nankai 360d annual - Pulsar LONG training"
echo " Master:        $MASTER"
echo " Forecast:      $FORECAST_START -> $FORECAST_END"
echo " Val lookback:  $VALIDATION_MAX_LOOKBACK_RECORDS records"
echo " Val events:    $VALIDATION_EVENT_COUNT event(s), pre=$VALIDATION_PRE_RECORDS post=$VALIDATION_POST_RECORDS"
echo " Val negatives: random=$RECENT_VALIDATION_RANDOM_NEGATIVES seed=$RECENT_VALIDATION_RANDOM_SEED"
echo " Target events: $TARGET_EVENT_COUNT event(s)"
echo " Banks:         $BANKS"
echo " Readouts:      $READOUTS"
echo " LCS presets:   $LCS_PRESETS_RUN"
echo " Hybrid modes:  $HYBRID_MODES"
echo " Hybrid alphas: $HYBRID_ALPHAS"
echo " Seeds:         $SEEDS_SPEC"
echo " Max iter:      $MAX_ITER"
echo " Jobs:          $JOBS"
echo " LCS rules:     export=$LCS_EXPORT_RULE_COUNT active_conditions=$LCS_MAX_ACTIVE_CONDITIONS"
echo " Smart peaks:   candidates=$POST_HYBRID_MAX_PEAKS final=$POST_HYBRID_FINAL_PEAK_MAX"
echo " DB:            $DB_FILE"
echo " Log:           $LOG_FILE"
echo "======================================================================"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

EXTRA_TRAIN_ARGS=()
if [[ "$RECENT_VALIDATION_SKIP_IF_UNAVAILABLE" == "1" || "$RECENT_VALIDATION_SKIP_IF_UNAVAILABLE" == "true" ]]; then
  EXTRA_TRAIN_ARGS+=(--recent-validation-skip-if-unavailable)
fi

./.venv/bin/python -u cli.py train \
  --task "$MASTER" \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  \
  --banks "$BANKS" \
  --readouts "$READOUTS" \
  --lcs-presets "$LCS_PRESETS_RUN" \
  --hybrid-lcs \
  --hybrid-partners "$HYBRID_PARTNERS" \
  --hybrid-modes "$HYBRID_MODES" \
  --hybrid-alphas "$HYBRID_ALPHAS" \
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
  --recent-validation-random-negatives "$RECENT_VALIDATION_RANDOM_NEGATIVES" \
  --recent-validation-random-seed "$RECENT_VALIDATION_RANDOM_SEED" \
  --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
  \
  --lcs-val-event-count "$VALIDATION_EVENT_COUNT" \
  --lcs-val-pre-records "$VALIDATION_PRE_RECORDS" \
  --lcs-val-post-records "$VALIDATION_POST_RECORDS" \
  --lcs-export-rule-count "$LCS_EXPORT_RULE_COUNT" \
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
  --seeds "$SEEDS_SPEC" \
  --max-iter "$MAX_ITER" \
  --jobs "$JOBS" \
  --best "$BEST_N" \
  --keep-best "$KEEP_BEST" \
  --keep-worst "$KEEP_WORST" \
  --invert-twin-min-std 1e-4 \
  --invert-twin-immediate-threshold 0.08 \
  --lcs-max-active-conditions "$LCS_MAX_ACTIVE_CONDITIONS" \
  --lcs-min-fitness-for-subsumption "$LCS_MIN_FITNESS_FOR_SUBSUMPTION" \
  \
  --post-hybrid-artifacts \
  --post-hybrid-mode both \
  --post-hybrid-logic and \
  --post-hybrid-normalize auto \
  --post-hybrid-forecast-guard auto \
  --post-hybrid-top-candidates "$POST_HYBRID_TOP_CANDIDATES" \
  --post-hybrid-top-pairs "$POST_HYBRID_TOP_PAIRS" \
  --post-hybrid-max-rules "$POST_HYBRID_MAX_RULES" \
  --post-hybrid-max-peaks "$POST_HYBRID_MAX_PEAKS" \
  --post-hybrid-final-peak-max "$POST_HYBRID_FINAL_PEAK_MAX" \
  --post-hybrid-peak-and \
  --post-hybrid-peak-window 1 \
  --post-hybrid-peak-floor 0.30 \
  --post-hybrid-peak-max "$POST_HYBRID_PEAK_MAX" \
  "${EXTRA_TRAIN_ARGS[@]}" \
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

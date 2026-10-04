#!/usr/bin/env bash
# Modular second-stage localization/depth forecast from an existing master CSV.
#
# It does not change cli.py.  It first prepares a location-specific CSV that:
#   - keeps historical rows only when mag >= EVENT_MAG_THRESHOLD
#   - keeps requested forecast rows for projection
#   - creates location_target from latitude/longitude/depth
#   - skips all original seismic columns during training
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
MASTER_CSV="${MASTER_CSV:-}"
[[ -n "$MASTER_CSV" ]] || {
  echo "[ERROR] MASTER_CSV is required" >&2
  echo "Example: MASTER_CSV=/path/master_with_usgs_core_astrofmt.csv LOCATION_TARGET=latitude LOCATION_MODE=analog ./commands/run_location_forecast_from_master.sh" >&2
  exit 2
}
[[ -f "$MASTER_CSV" ]] || { echo "[ERROR] MASTER_CSV not found: $MASTER_CSV" >&2; exit 2; }

LOCATION_TARGET="${LOCATION_TARGET:-latitude}"        # latitude | longitude | depth
LOCATION_MODE="${LOCATION_MODE:-analog}"              # analog | binary
LOCATION_TARGET_NAME="${LOCATION_TARGET_NAME:-location_target}"
LOCATION_DIRECTION="${LOCATION_DIRECTION:-above}"     # above | below, binary/threshold reporting
LOCATION_DECISION_THRESHOLD="${LOCATION_DECISION_THRESHOLD:-}"
EVENT_MAG_THRESHOLD="${EVENT_MAG_THRESHOLD:-0.1}"
FORECAST_START="${FORECAST_START:-2026-08-01}"
FORECAST_END="${FORECAST_END:-2026-08-30}"
FOCUS_START="${FOCUS_START:-}"
FOCUS_END="${FOCUS_END:-}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-4}"

ANALOG_SCALE="${ANALOG_SCALE:-minmax}"                # minmax | none
CLIP_MIN="${CLIP_MIN:-}"
CLIP_MAX="${CLIP_MAX:-}"

KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
KAN_DEVICE="${KAN_DEVICE:-cpu}"
KAN_QUIET="${KAN_QUIET:-0}"
SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15}"
MAX_ITER="${MAX_ITER:-1200}"
JOBS="${JOBS:-2}"
BEST_N="${BEST_N:-80}"
KEEP_BEST="${KEEP_BEST:-80}"

ENABLE_KAN="${ENABLE_KAN:-1}"

# Optional symbolic comparison.  LCS is meaningful only for binary location
# targets by default, because analog location targets are continuous min/max
# scaled values.  Set ENABLE_LCS_FOR_ANALOG=1 only for experimental debugging.
ENABLE_LCS="${ENABLE_LCS:-0}"
ENABLE_LCS_HYBRID="${ENABLE_LCS_HYBRID:-0}"
ENABLE_LCS_FOR_ANALOG="${ENABLE_LCS_FOR_ANALOG:-0}"
LCS_POPULATION_SIZE="${LCS_POPULATION_SIZE:-40}"
LCS_GA_FREQUENCY="${LCS_GA_FREQUENCY:-120}"
LCS_TOURNAMENT_SIZE="${LCS_TOURNAMENT_SIZE:-3}"
LCS_WILDCARD_PROB="${LCS_WILDCARD_PROB:-0.65}"
LCS_EARLY_STOP_PATIENCE="${LCS_EARLY_STOP_PATIENCE:-12}"
LCS_MAX_ACTIVE_CONDITIONS="${LCS_MAX_ACTIVE_CONDITIONS:-2}"
LCS_EXPORT_RULE_COUNT="${LCS_EXPORT_RULE_COUNT:-5}"
LCS_MIN_FITNESS_FOR_SUBSUMPTION="${LCS_MIN_FITNESS_FOR_SUBSUMPTION:-0.65}"
LCS_HYBRID_PARTNERS="${LCS_HYBRID_PARTNERS:-passthrough:ridge}"
LCS_HYBRID_MODES="${LCS_HYBRID_MODES:-and}"
LCS_HYBRID_ALPHAS="${LCS_HYBRID_ALPHAS:-0.5}"
LCS_HYBRID_THRESHOLD="${LCS_HYBRID_THRESHOLD:-0.5}"

STAMP="$(date +%Y%m%d-%H%M%S)"
MASTER_STEM="$(basename "$(dirname "$MASTER_CSV")")"
OUT_DIR="${OUT_DIR:-$(dirname "$MASTER_CSV")/location_${LOCATION_TARGET}_${LOCATION_MODE}_$STAMP}"
PREP_CSV="$OUT_DIR/prepared_${LOCATION_TARGET}_${LOCATION_MODE}.csv"
PREP_JSON="$OUT_DIR/prepared_${LOCATION_TARGET}_${LOCATION_MODE}.json"
DB_FILE="${DB_FILE:-$OUT_DIR/location_${LOCATION_TARGET}_${LOCATION_MODE}.db}"
LOG_FILE="${LOG_FILE:-$OUT_DIR/location_${LOCATION_TARGET}_${LOCATION_MODE}.log}"
REPORT_DIR="$OUT_DIR/location_report"

mkdir -p "$OUT_DIR"

echo "======================================================================"
echo " Location/depth second-stage forecast"
echo " Master:        $MASTER_CSV"
echo " Target:        $LOCATION_TARGET"
echo " Mode:          $LOCATION_MODE"
echo " Event filter:  mag >= $EVENT_MAG_THRESHOLD"
echo " Forecast:      $FORECAST_START -> $FORECAST_END"
echo " Focus window:  ${FOCUS_START:-'(none)'} -> ${FOCUS_END:-'(none)'}"
echo " Out:           $OUT_DIR"
echo " KAN device:    $KAN_DEVICE"
echo "======================================================================"

PREP_ARGS=(
  "$PYTHON_BIN" "$PWD/prepare_location_target_master.py"
  --input-csv "$MASTER_CSV"
  --output-csv "$PREP_CSV"
  --output-json "$PREP_JSON"
  --target-source "$LOCATION_TARGET"
  --mode "$LOCATION_MODE"
  --target-name "$LOCATION_TARGET_NAME"
  --event-mag-threshold "$EVENT_MAG_THRESHOLD"
  --forecast-start-date "$FORECAST_START"
  --forecast-end-date "$FORECAST_END"
  --validation-event-count "$VALIDATION_EVENT_COUNT"
  --analog-scale "$ANALOG_SCALE"
)
[[ -n "$FOCUS_START" ]] && PREP_ARGS+=(--focus-start-date "$FOCUS_START")
[[ -n "$FOCUS_END" ]] && PREP_ARGS+=(--focus-end-date "$FOCUS_END")
[[ -n "$CLIP_MIN" ]] && PREP_ARGS+=(--clip-min "$CLIP_MIN")
[[ -n "$CLIP_MAX" ]] && PREP_ARGS+=(--clip-max "$CLIP_MAX")
if [[ "$LOCATION_MODE" == "binary" ]]; then
  [[ -n "$LOCATION_DECISION_THRESHOLD" ]] || {
    echo "[ERROR] LOCATION_DECISION_THRESHOLD is required in binary mode" >&2
    exit 2
  }
  PREP_ARGS+=(--decision-threshold "$LOCATION_DECISION_THRESHOLD")
  PREP_ARGS+=(--binary-direction "$LOCATION_DIRECTION")
elif [[ -n "$LOCATION_DECISION_THRESHOLD" ]]; then
  PREP_ARGS+=(--decision-threshold "$LOCATION_DECISION_THRESHOLD")
  PREP_ARGS+=(--binary-direction "$LOCATION_DIRECTION")
fi

"${PREP_ARGS[@]}"

N_TRAIN="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1]))["recommended_n_train"])' "$PREP_JSON")"
N_TEST="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1]))["recommended_n_test"])' "$PREP_JSON")"
SKIP_COLS="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1]))["skip_cols_list"])' "$PREP_JSON")"

if [[ "$LOCATION_MODE" == "binary" ]]; then
  METRIC_MODE="${METRIC_MODE:-event}"
  METRIC_TARGET_THRESHOLD="${METRIC_TARGET_THRESHOLD:-0.5}"
  METRIC_PREDICTION_THRESHOLD="${METRIC_PREDICTION_THRESHOLD:-0.5}"
else
  METRIC_MODE="${METRIC_MODE:-regression}"
  METRIC_TARGET_THRESHOLD="${METRIC_TARGET_THRESHOLD:-}"
  METRIC_PREDICTION_THRESHOLD="${METRIC_PREDICTION_THRESHOLD:-0.5}"
fi

echo ""
echo "[train] n_train=$N_TRAIN n_test=$N_TEST skip_cols=$SKIP_COLS"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

TRAIN_ARGS=(
  "$PYTHON_BIN" -u cli.py train
  --task "$PREP_CSV"
  --target_cols_list "$LOCATION_TARGET_NAME"
  --skip_cols_list "$SKIP_COLS"
  --no-banks
  --metric-mode "$METRIC_MODE"
  --metric-prediction-threshold "$METRIC_PREDICTION_THRESHOLD"
  --target-window-threshold 0.0
  --target-window-event-count "$VALIDATION_EVENT_COUNT"
  --target-window-pre-records 0
  --target-window-post-records 0
  --isolated-event-windows
  --time-series on
  --forecast-start-date "$FORECAST_START"
  --forecast-end-date "$FORECAST_END"
  --forecast-trainset train2forecast
  --n-train "$N_TRAIN"
  --n-test "$N_TEST"
  --final-eval-rank-power 1.0
  --final-eval-best-fraction 0.50
  --final-eval-worst-fraction 0.0
  --final-eval-shape-power 0.5
  --readability-weight 0.25
  --readability-floor 0.3
  --seeds "$SEEDS_SPEC"
  --max-iter "$MAX_ITER"
  --jobs "$JOBS"
  --best "$BEST_N"
  --keep-best "$KEEP_BEST"
  --keep-worst 0
  --no-invert-twin
  --no-export-best-by-bank
  --no-collage
  --db "$DB_FILE"
  --verbose
)
if [[ "$ENABLE_KAN" == "1" ]]; then
  TRAIN_ARGS+=(
    --enable-kan
    --kan-presets "$KAN_PRESETS_RUN"
    --kan-device "$KAN_DEVICE"
  )
  if [[ "$KAN_QUIET" == "1" || "$KAN_QUIET" == "true" || "$KAN_QUIET" == "yes" ]]; then
    TRAIN_ARGS+=(--kan-quiet)
  fi
fi
[[ -n "$METRIC_TARGET_THRESHOLD" ]] && TRAIN_ARGS+=(--metric-target-threshold "$METRIC_TARGET_THRESHOLD")

if [[ "$ENABLE_LCS" == "1" || "$ENABLE_LCS_HYBRID" == "1" ]]; then
  if [[ "$LOCATION_MODE" == "binary" || "$ENABLE_LCS_FOR_ANALOG" == "1" ]]; then
    LCS_THRESHOLD="${METRIC_TARGET_THRESHOLD:-0.5}"
    TRAIN_ARGS+=(
      --lcs-custom
      --lcs-population-size "$LCS_POPULATION_SIZE"
      --lcs-ga-frequency "$LCS_GA_FREQUENCY"
      --lcs-tournament-size "$LCS_TOURNAMENT_SIZE"
      --lcs-wildcard-prob "$LCS_WILDCARD_PROB"
      --lcs-early-stop-patience "$LCS_EARLY_STOP_PATIENCE"
      --lcs-max-active-conditions "$LCS_MAX_ACTIVE_CONDITIONS"
      --lcs-export-rule-count "$LCS_EXPORT_RULE_COUNT"
      --lcs-min-fitness-for-subsumption "$LCS_MIN_FITNESS_FOR_SUBSUMPTION"
      --lcs-binary-threshold "$LCS_THRESHOLD"
    )
    if [[ "$ENABLE_LCS_HYBRID" == "1" ]]; then
      TRAIN_ARGS+=(
        --hybrid-lcs
        --hybrid-partners "$LCS_HYBRID_PARTNERS"
        --hybrid-modes "$LCS_HYBRID_MODES"
        --hybrid-alphas "$LCS_HYBRID_ALPHAS"
        --hybrid-threshold "$LCS_HYBRID_THRESHOLD"
      )
    fi
  else
    echo "[warn] ENABLE_LCS requested but LOCATION_MODE=$LOCATION_MODE; skipping LCS for analog target."
    echo "       Set ENABLE_LCS_FOR_ANALOG=1 only if you explicitly want analog binarization."
  fi
fi

"${TRAIN_ARGS[@]}" 2>&1 | tee "$LOG_FILE"

find_latest_run_dir() {
  local base_dir="$1"
  local latest=""
  shopt -s nullglob
  local candidates=("$base_dir"/pulsar_train*_best_trials_*)
  shopt -u nullglob
  if (( ${#candidates[@]} == 0 )); then
    return 1
  fi
  latest="$(printf '%s\n' "${candidates[@]}" | sort | tail -n 1)"
  [[ -d "$latest" ]] || return 1
  printf '%s\n' "$latest"
}

RUN_DIR="$(find_latest_run_dir "$OUT_DIR")"

"$PYTHON_BIN" "$PWD/location_forecast_report.py" \
  --run-dir "$RUN_DIR" \
  --prepared-json "$PREP_JSON" \
  --output-dir "$REPORT_DIR" \
  --output-prefix "location_${LOCATION_TARGET}_${LOCATION_MODE}_forecast" \
  --focus-start-date "$FOCUS_START" \
  --focus-end-date "$FOCUS_END" \
  --title "${MASTER_STEM}: ${LOCATION_TARGET} ${LOCATION_MODE} localization forecast"

{
  echo "# Location Forecast Run"
  echo ""
  echo "- master: \`$MASTER_CSV\`"
  echo "- prepared CSV: \`$PREP_CSV\`"
  echo "- prepared JSON: \`$PREP_JSON\`"
  echo "- run dir: \`$RUN_DIR\`"
  echo "- report dir: \`$REPORT_DIR\`"
  echo "- target: \`$LOCATION_TARGET\`"
  echo "- mode: \`$LOCATION_MODE\`"
  echo "- event filter: \`mag >= $EVENT_MAG_THRESHOLD\`"
  echo "- forecast: \`$FORECAST_START -> $FORECAST_END\`"
  echo "- focus: \`${FOCUS_START:-none} -> ${FOCUS_END:-none}\`"
  echo "- KAN: \`ENABLE_KAN=$ENABLE_KAN\`"
  echo "- KAN device: \`$KAN_DEVICE\`"
  echo "- KAN quiet: \`$KAN_QUIET\`"
  echo "- LCS: \`ENABLE_LCS=$ENABLE_LCS ENABLE_LCS_HYBRID=$ENABLE_LCS_HYBRID\`"
  echo ""
  echo "Training skips original seismic/context columns: \`$SKIP_COLS\`."
} > "$OUT_DIR/location_run_manifest.md"

echo ""
echo "======================================================================"
echo " Location forecast ready"
echo " Run:      $RUN_DIR"
echo " Report:   $REPORT_DIR/location_${LOCATION_TARGET}_${LOCATION_MODE}_forecast.md"
echo " PNG:      $REPORT_DIR/location_${LOCATION_TARGET}_${LOCATION_MODE}_forecast.png"
echo " Manifest: $OUT_DIR/location_run_manifest.md"
echo "======================================================================"

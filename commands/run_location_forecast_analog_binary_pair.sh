#!/usr/bin/env bash
# Run both analog and binary second-stage localization forecasts.
#
# Required:
#   MASTER_CSV=/path/master_with_usgs_core_astrofmt.csv
#   LOCATION_TARGET=latitude|longitude|depth
#   LOCATION_DECISION_THRESHOLD=<physical threshold for binary mode>
#   or LOCATION_DECISION_THRESHOLD=median for an auto-balanced historical median
#
# Optional examples:
#   FOCUS_START=2026-08-07 FOCUS_END=2026-08-11
#   FORECAST_START=2026-08-01 FORECAST_END=2026-08-30
set -euo pipefail

cd "$(dirname "$0")/.."

MASTER_CSV="${MASTER_CSV:-}"
LOCATION_TARGET="${LOCATION_TARGET:-latitude}"
LOCATION_DECISION_THRESHOLD="${LOCATION_DECISION_THRESHOLD:-}"
LOCATION_DIRECTION="${LOCATION_DIRECTION:-above}"

[[ -n "$MASTER_CSV" ]] || {
  echo "[ERROR] MASTER_CSV is required" >&2
  exit 2
}
[[ -f "$MASTER_CSV" ]] || {
  echo "[ERROR] MASTER_CSV not found: $MASTER_CSV" >&2
  exit 2
}
[[ -n "$LOCATION_DECISION_THRESHOLD" ]] || {
  echo "[ERROR] LOCATION_DECISION_THRESHOLD is required for the binary half of this pair run" >&2
  echo "Example: LOCATION_DECISION_THRESHOLD=37, or LOCATION_DECISION_THRESHOLD=median" >&2
  exit 2
}

STAMP="$(date +%Y%m%d-%H%M%S)"
PAIR_ROOT="${PAIR_ROOT:-$(dirname "$MASTER_CSV")/localization_${LOCATION_TARGET}_analog_binary_complete_$STAMP}"
ANALOG_OUT_DIR="$PAIR_ROOT/analog"
BINARY_OUT_DIR="$PAIR_ROOT/binary_${LOCATION_DIRECTION}_${LOCATION_DECISION_THRESHOLD}"
FUSION_OUT_DIR="$PAIR_ROOT/final_location_fusion"

mkdir -p "$PAIR_ROOT"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PAIR_ROOT/.matplotlib}"
mkdir -p "$MPLCONFIGDIR"

echo "======================================================================"
echo " Complete localization forecast: analog + binary + fusion"
echo " Master:       $MASTER_CSV"
echo " Target:       $LOCATION_TARGET"
echo " Binary:       $LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD"
echo " Pair root:    $PAIR_ROOT"
echo "======================================================================"

COMMON_ENV=(
  MASTER_CSV="$MASTER_CSV"
  LOCATION_TARGET="$LOCATION_TARGET"
  EVENT_MAG_THRESHOLD="${EVENT_MAG_THRESHOLD:-0.1}"
  FORECAST_START="${FORECAST_START:-2026-08-01}"
  FORECAST_END="${FORECAST_END:-2026-08-30}"
  FOCUS_START="${FOCUS_START:-}"
  FOCUS_END="${FOCUS_END:-}"
  VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-4}"
  KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
  SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15}"
  MAX_ITER="${MAX_ITER:-1200}"
  JOBS="${JOBS:-2}"
  BEST_N="${BEST_N:-80}"
  KEEP_BEST="${KEEP_BEST:-80}"
  ENABLE_KAN="${ENABLE_KAN:-1}"
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
  PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
)

echo ""
echo "[1/2] Analog localization forecast..."
env "${COMMON_ENV[@]}" \
  LOCATION_MODE=analog \
  LOCATION_DECISION_THRESHOLD="$LOCATION_DECISION_THRESHOLD" \
  LOCATION_DIRECTION="$LOCATION_DIRECTION" \
  OUT_DIR="$ANALOG_OUT_DIR" \
  "$PWD/commands/run_location_forecast_from_master.sh"

echo ""
echo "[2/2] Binary localization forecast..."
env "${COMMON_ENV[@]}" \
  LOCATION_MODE=binary \
  LOCATION_DECISION_THRESHOLD="$LOCATION_DECISION_THRESHOLD" \
  LOCATION_DIRECTION="$LOCATION_DIRECTION" \
  OUT_DIR="$BINARY_OUT_DIR" \
  "$PWD/commands/run_location_forecast_from_master.sh"

ANALOG_REPORT_DIR="$ANALOG_OUT_DIR/location_report"
BINARY_REPORT_DIR="$BINARY_OUT_DIR/location_report"
ANALOG_REPORT_PREFIX="location_${LOCATION_TARGET}_analog_forecast"
BINARY_REPORT_PREFIX="location_${LOCATION_TARGET}_binary_forecast"

echo ""
echo "[3/3] Final analog/binary localization fusion..."
"${PYTHON_BIN:-$PWD/.venv/bin/python}" "$PWD/location_analog_binary_fusion.py" \
  --analog-csv "$ANALOG_REPORT_DIR/${ANALOG_REPORT_PREFIX}.csv" \
  --analog-json "$ANALOG_REPORT_DIR/${ANALOG_REPORT_PREFIX}.json" \
  --binary-csv "$BINARY_REPORT_DIR/${BINARY_REPORT_PREFIX}.csv" \
  --binary-json "$BINARY_REPORT_DIR/${BINARY_REPORT_PREFIX}.json" \
  --output-dir "$FUSION_OUT_DIR" \
  --output-prefix "final_${LOCATION_TARGET}_analog_binary_localization_fusion" \
  --title "${LOCATION_TARGET} analog + binary localization fusion"

{
  echo "# Complete Location Analog/Binary Fusion"
  echo ""
  echo "- master: \`$MASTER_CSV\`"
  echo "- target: \`$LOCATION_TARGET\`"
  echo "- binary threshold: \`$LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD\`"
  echo "- forecast: \`${FORECAST_START:-2026-08-01} -> ${FORECAST_END:-2026-08-30}\`"
  echo "- focus: \`${FOCUS_START:-none} -> ${FOCUS_END:-none}\`"
  echo "- analog dir: \`$ANALOG_OUT_DIR\`"
  echo "- binary dir: \`$BINARY_OUT_DIR\`"
  echo "- final fusion dir: \`$FUSION_OUT_DIR\`"
  echo ""
  echo "Interpretation: analog estimates the physical value; binary answers the threshold question. "
  echo "The final fusion combines analog threshold support and binary probability into one report."
} > "$PAIR_ROOT/localization_complete_manifest.md"

echo ""
echo "======================================================================"
echo " Complete localization run ready"
echo " Root:     $PAIR_ROOT"
echo " Analog:   $ANALOG_OUT_DIR/location_report/location_${LOCATION_TARGET}_analog_forecast.md"
echo " Binary:   $BINARY_OUT_DIR/location_report/location_${LOCATION_TARGET}_binary_forecast.md"
echo " Fusion:   $FUSION_OUT_DIR/final_${LOCATION_TARGET}_analog_binary_localization_fusion.md"
echo " PNG:      $FUSION_OUT_DIR/final_${LOCATION_TARGET}_analog_binary_localization_fusion.png"
echo " Manifest: $PAIR_ROOT/localization_complete_manifest.md"
echo "======================================================================"

#!/usr/bin/env bash
# Full localization pipeline:
#   vertical master:   analog + binary -> local fusion
#   horizontal master: analog + binary -> local fusion
#   final fusion:      vertical local fusion + horizontal local fusion
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
LOCATION_TARGET="${LOCATION_TARGET:-latitude}"
LOCATION_DECISION_THRESHOLD="${LOCATION_DECISION_THRESHOLD:-median}"
LOCATION_DIRECTION="${LOCATION_DIRECTION:-above}"

VERTICAL_MASTER_CSV="${VERTICAL_MASTER_CSV:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-1d-august-observer-autoclip-vertical-kan-recentweighted/master_with_usgs_core_astrofmt.csv}"
HORIZONTAL_MASTER_CSV="${HORIZONTAL_MASTER_CSV:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-1d-august-observer-autoclip-horizontal-kan-recentweighted/master_with_usgs_core_astrofmt.csv}"

[[ -f "$VERTICAL_MASTER_CSV" ]] || { echo "[ERROR] VERTICAL_MASTER_CSV not found: $VERTICAL_MASTER_CSV" >&2; exit 2; }
[[ -f "$HORIZONTAL_MASTER_CSV" ]] || { echo "[ERROR] HORIZONTAL_MASTER_CSV not found: $HORIZONTAL_MASTER_CSV" >&2; exit 2; }
[[ -n "$LOCATION_DECISION_THRESHOLD" ]] || { echo "[ERROR] LOCATION_DECISION_THRESHOLD is required" >&2; exit 2; }

STAMP="$(date +%Y%m%d-%H%M%S)"
ROOT_DIR="${ROOT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/localization_${LOCATION_TARGET}_vertical_horizontal_analog_binary_complete_$STAMP}"
VERTICAL_ROOT="$ROOT_DIR/vertical_autoclip"
HORIZONTAL_ROOT="$ROOT_DIR/horizontal_autoclip"
FINAL_OUT_DIR="$ROOT_DIR/final_vertical_horizontal_location_fusion"
mkdir -p "$ROOT_DIR"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT_DIR/.matplotlib}"
mkdir -p "$MPLCONFIGDIR"

echo "======================================================================"
echo " Full vertical/horizontal localization pipeline"
echo " Target:     $LOCATION_TARGET"
echo " Condition:  $LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD"
echo " Vertical:   $VERTICAL_MASTER_CSV"
echo " Horizontal: $HORIZONTAL_MASTER_CSV"
echo " Root:       $ROOT_DIR"
echo "======================================================================"

COMMON_ENV=(
  LOCATION_TARGET="$LOCATION_TARGET"
  LOCATION_DECISION_THRESHOLD="$LOCATION_DECISION_THRESHOLD"
  LOCATION_DIRECTION="$LOCATION_DIRECTION"
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
  PYTHON_BIN="$PYTHON_BIN"
  MPLCONFIGDIR="$MPLCONFIGDIR"
)

echo ""
echo "[1/3] Vertical auto-clip localization fusion..."
env "${COMMON_ENV[@]}" \
  MASTER_CSV="$VERTICAL_MASTER_CSV" \
  PAIR_ROOT="$VERTICAL_ROOT" \
  "$PWD/commands/run_location_forecast_analog_binary_pair.sh"

echo ""
echo "[2/3] Horizontal auto-clip localization fusion..."
env "${COMMON_ENV[@]}" \
  MASTER_CSV="$HORIZONTAL_MASTER_CSV" \
  PAIR_ROOT="$HORIZONTAL_ROOT" \
  "$PWD/commands/run_location_forecast_analog_binary_pair.sh"

VERTICAL_PREFIX="final_${LOCATION_TARGET}_analog_binary_localization_fusion"
HORIZONTAL_PREFIX="final_${LOCATION_TARGET}_analog_binary_localization_fusion"
VERTICAL_FUSION_DIR="$VERTICAL_ROOT/final_location_fusion"
HORIZONTAL_FUSION_DIR="$HORIZONTAL_ROOT/final_location_fusion"

echo ""
echo "[3/3] Final vertical/horizontal localization fusion + lineage..."
"$PYTHON_BIN" "$PWD/location_vertical_horizontal_fusion.py" \
  --vertical-csv "$VERTICAL_FUSION_DIR/${VERTICAL_PREFIX}.csv" \
  --vertical-json "$VERTICAL_FUSION_DIR/${VERTICAL_PREFIX}.json" \
  --horizontal-csv "$HORIZONTAL_FUSION_DIR/${HORIZONTAL_PREFIX}.csv" \
  --horizontal-json "$HORIZONTAL_FUSION_DIR/${HORIZONTAL_PREFIX}.json" \
  --output-dir "$FINAL_OUT_DIR" \
  --output-prefix "final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion" \
  --title "${LOCATION_TARGET} vertical vs horizontal localization fusion"

{
  echo "# Full Vertical/Horizontal Localization Pipeline"
  echo ""
  echo "- vertical master: \`$VERTICAL_MASTER_CSV\`"
  echo "- horizontal master: \`$HORIZONTAL_MASTER_CSV\`"
  echo "- target: \`$LOCATION_TARGET\`"
  echo "- condition: \`$LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD\`"
  echo "- forecast: \`${FORECAST_START:-2026-08-01} -> ${FORECAST_END:-2026-08-30}\`"
  echo "- focus: \`${FOCUS_START:-none} -> ${FOCUS_END:-none}\`"
  echo "- vertical fusion: \`$VERTICAL_FUSION_DIR/${VERTICAL_PREFIX}.md\`"
  echo "- horizontal fusion: \`$HORIZONTAL_FUSION_DIR/${HORIZONTAL_PREFIX}.md\`"
  echo "- final fusion: \`$FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion.md\`"
  echo "- lineage: \`$FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion__lineage.png\`"
  echo ""
  echo "This report is a second-stage experimental localization signal. It is not a deterministic earthquake forecast."
} > "$ROOT_DIR/localization_vertical_horizontal_complete_manifest.md"

echo ""
echo "======================================================================"
echo " Full localization pipeline ready"
echo " Root:     $ROOT_DIR"
echo " Final:    $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion.md"
echo " PNG:      $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion.png"
echo " Lineage:  $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion__lineage.png"
echo " Manifest: $ROOT_DIR/localization_vertical_horizontal_complete_manifest.md"
echo "======================================================================"

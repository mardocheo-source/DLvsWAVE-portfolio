#!/usr/bin/env bash
# Binary-only symbolic localization pipeline:
#   vertical master:   binary LCS/LCS-hybrid -> binary-only local report
#   horizontal master: binary LCS/LCS-hybrid -> binary-only local report
#   final fusion:      vertical symbolic support + horizontal symbolic support
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
ROOT_DIR="${ROOT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/localization_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_$STAMP}"
VERTICAL_ROOT="$ROOT_DIR/vertical_autoclip_binary_lcs"
HORIZONTAL_ROOT="$ROOT_DIR/horizontal_autoclip_binary_lcs"
VERTICAL_FUSION_DIR="$VERTICAL_ROOT/final_location_fusion"
HORIZONTAL_FUSION_DIR="$HORIZONTAL_ROOT/final_location_fusion"
FINAL_OUT_DIR="$ROOT_DIR/final_vertical_horizontal_location_fusion"
mkdir -p "$ROOT_DIR" "$VERTICAL_FUSION_DIR" "$HORIZONTAL_FUSION_DIR" "$FINAL_OUT_DIR"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT_DIR/.matplotlib}"
mkdir -p "$MPLCONFIGDIR"

COMMON_ENV=(
  LOCATION_TARGET="$LOCATION_TARGET"
  LOCATION_MODE=binary
  LOCATION_DECISION_THRESHOLD="$LOCATION_DECISION_THRESHOLD"
  LOCATION_DIRECTION="$LOCATION_DIRECTION"
  EVENT_MAG_THRESHOLD="${EVENT_MAG_THRESHOLD:-0.1}"
  FORECAST_START="${FORECAST_START:-2026-08-01}"
  FORECAST_END="${FORECAST_END:-2026-08-30}"
  FOCUS_START="${FOCUS_START:-}"
  FOCUS_END="${FOCUS_END:-}"
  VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-4}"
  ENABLE_KAN=0
  ENABLE_LCS=1
  ENABLE_LCS_HYBRID="${ENABLE_LCS_HYBRID:-1}"
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
  SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15}"
  MAX_ITER="${MAX_ITER:-1200}"
  JOBS="${JOBS:-2}"
  BEST_N="${BEST_N:-80}"
  KEEP_BEST="${KEEP_BEST:-80}"
  PYTHON_BIN="$PYTHON_BIN"
  MPLCONFIGDIR="$MPLCONFIGDIR"
)

echo "======================================================================"
echo " Vertical/horizontal LCS binary-only localization pipeline"
echo " Target:     $LOCATION_TARGET"
echo " Condition:  $LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD"
echo " Root:       $ROOT_DIR"
echo " Note:       LCS is binary-only here; no analog coordinate is estimated."
echo "======================================================================"

run_binary_lcs_side() {
  local side="$1"
  local master="$2"
  local out_dir="$3"
  local fusion_dir="$4"
  echo ""
  echo "[$side] Binary LCS/LCS-hybrid localization forecast..."
  env "${COMMON_ENV[@]}" \
    MASTER_CSV="$master" \
    OUT_DIR="$out_dir" \
    "$PWD/commands/run_location_forecast_from_master.sh"

  local report_dir="$out_dir/location_report"
  local prefix="location_${LOCATION_TARGET}_binary_forecast"
  "$PYTHON_BIN" "$PWD/location_binary_only_fusion.py" \
    --binary-csv "$report_dir/${prefix}.csv" \
    --binary-json "$report_dir/${prefix}.json" \
    --output-dir "$fusion_dir" \
    --output-prefix "final_${LOCATION_TARGET}_binary_only_localization_fusion" \
    --title "$side LCS/LCS-hybrid binary-only localization fusion" \
    --method-label "LCS/LCS-hybrid"
}

run_binary_lcs_side "vertical" "$VERTICAL_MASTER_CSV" "$VERTICAL_ROOT" "$VERTICAL_FUSION_DIR"
run_binary_lcs_side "horizontal" "$HORIZONTAL_MASTER_CSV" "$HORIZONTAL_ROOT" "$HORIZONTAL_FUSION_DIR"

PREFIX="final_${LOCATION_TARGET}_binary_only_localization_fusion"

echo ""
echo "[final] Vertical/horizontal symbolic fusion..."
"$PYTHON_BIN" "$PWD/location_vertical_horizontal_fusion.py" \
  --vertical-csv "$VERTICAL_FUSION_DIR/${PREFIX}.csv" \
  --vertical-json "$VERTICAL_FUSION_DIR/${PREFIX}.json" \
  --horizontal-csv "$HORIZONTAL_FUSION_DIR/${PREFIX}.csv" \
  --horizontal-json "$HORIZONTAL_FUSION_DIR/${PREFIX}.json" \
  --output-dir "$FINAL_OUT_DIR" \
  --output-prefix "final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion" \
  --title "${LOCATION_TARGET} vertical vs horizontal LCS binary-only localization fusion"

{
  echo "# Vertical/Horizontal LCS Binary-Only Localization Pipeline"
  echo ""
  echo "- vertical master: \`$VERTICAL_MASTER_CSV\`"
  echo "- horizontal master: \`$HORIZONTAL_MASTER_CSV\`"
  echo "- target: \`$LOCATION_TARGET\`"
  echo "- condition: \`$LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD\`"
  echo "- forecast: \`${FORECAST_START:-2026-08-01} -> ${FORECAST_END:-2026-08-30}\`"
  echo "- focus: \`${FOCUS_START:-none} -> ${FOCUS_END:-none}\`"
  echo "- final fusion: \`$FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion.md\`"
  echo ""
  echo "LCS/LCS-hybrid is only used on the binary threshold task. Metrics labeled unary/binary-only are not analog coordinate estimates."
} > "$ROOT_DIR/localization_lcs_binary_only_manifest.md"

echo ""
echo "======================================================================"
echo " LCS binary-only localization pipeline ready"
echo " Root:     $ROOT_DIR"
echo " Final:    $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion.md"
echo " PNG:      $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion.png"
echo " Lineage:  $FINAL_OUT_DIR/final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion__lineage.png"
echo " Manifest: $ROOT_DIR/localization_lcs_binary_only_manifest.md"
echo "======================================================================"

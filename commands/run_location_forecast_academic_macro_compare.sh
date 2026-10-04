#!/usr/bin/env bash
# Academic macro comparison:
#   1) KAN-only localization pipeline, analog + binary, vertical + horizontal
#   2) LCS/LCS-hybrid-only localization pipeline, binary-only, vertical + horizontal
#   3) Final KAN-vs-LCS system comparison report
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

STAMP="$(date +%Y%m%d-%H%M%S)"
ROOT_DIR="${ROOT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/localization_${LOCATION_TARGET}_academic_kan_vs_lcs_macro_$STAMP}"
KAN_ROOT="$ROOT_DIR/kan_only"
LCS_ROOT="$ROOT_DIR/lcs_binary_only"
COMPARISON_DIR="$ROOT_DIR/final_kan_vs_lcs_system_comparison"
RULES_DIR="$ROOT_DIR/method_rules_summary"
mkdir -p "$ROOT_DIR" "$COMPARISON_DIR" "$RULES_DIR"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$ROOT_DIR/.matplotlib}"
mkdir -p "$MPLCONFIGDIR"

COMMON_ENV=(
  LOCATION_TARGET="$LOCATION_TARGET"
  LOCATION_DECISION_THRESHOLD="$LOCATION_DECISION_THRESHOLD"
  LOCATION_DIRECTION="$LOCATION_DIRECTION"
  VERTICAL_MASTER_CSV="$VERTICAL_MASTER_CSV"
  HORIZONTAL_MASTER_CSV="$HORIZONTAL_MASTER_CSV"
  EVENT_MAG_THRESHOLD="${EVENT_MAG_THRESHOLD:-0.1}"
  FORECAST_START="${FORECAST_START:-2026-08-01}"
  FORECAST_END="${FORECAST_END:-2026-08-30}"
  FOCUS_START="${FOCUS_START:-}"
  FOCUS_END="${FOCUS_END:-}"
  VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-4}"
  SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15}"
  MAX_ITER="${MAX_ITER:-1200}"
  JOBS="${JOBS:-2}"
  BEST_N="${BEST_N:-80}"
  KEEP_BEST="${KEEP_BEST:-80}"
  PYTHON_BIN="$PYTHON_BIN"
  MPLCONFIGDIR="$MPLCONFIGDIR"
)

echo "======================================================================"
echo " Academic localization macro comparison"
echo " Target:     $LOCATION_TARGET"
echo " Condition:  $LOCATION_TARGET $([[ "$LOCATION_DIRECTION" == "above" ]] && echo '>=' || echo '<=') $LOCATION_DECISION_THRESHOLD"
echo " Root:       $ROOT_DIR"
echo "======================================================================"

echo ""
echo "[1/3] KAN-only macro pipeline..."
env "${COMMON_ENV[@]}" \
  ROOT_DIR="$KAN_ROOT" \
  ENABLE_KAN=1 \
  ENABLE_LCS=0 \
  ENABLE_LCS_HYBRID=0 \
  KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}" \
  "$PWD/commands/run_location_forecast_vertical_horizontal_complete.sh"

echo ""
echo "[2/3] LCS/LCS-hybrid binary-only macro pipeline..."
env "${COMMON_ENV[@]}" \
  ROOT_DIR="$LCS_ROOT" \
  ENABLE_LCS_HYBRID="${ENABLE_LCS_HYBRID:-1}" \
  LCS_POPULATION_SIZE="${LCS_POPULATION_SIZE:-40}" \
  LCS_GA_FREQUENCY="${LCS_GA_FREQUENCY:-120}" \
  LCS_TOURNAMENT_SIZE="${LCS_TOURNAMENT_SIZE:-3}" \
  LCS_WILDCARD_PROB="${LCS_WILDCARD_PROB:-0.65}" \
  LCS_EARLY_STOP_PATIENCE="${LCS_EARLY_STOP_PATIENCE:-12}" \
  LCS_MAX_ACTIVE_CONDITIONS="${LCS_MAX_ACTIVE_CONDITIONS:-2}" \
  LCS_EXPORT_RULE_COUNT="${LCS_EXPORT_RULE_COUNT:-5}" \
  LCS_MIN_FITNESS_FOR_SUBSUMPTION="${LCS_MIN_FITNESS_FOR_SUBSUMPTION:-0.65}" \
  LCS_HYBRID_PARTNERS="${LCS_HYBRID_PARTNERS:-passthrough:ridge}" \
  LCS_HYBRID_MODES="${LCS_HYBRID_MODES:-and}" \
  LCS_HYBRID_ALPHAS="${LCS_HYBRID_ALPHAS:-0.5}" \
  LCS_HYBRID_THRESHOLD="${LCS_HYBRID_THRESHOLD:-0.5}" \
  "$PWD/commands/run_location_forecast_vertical_horizontal_lcs_binary_only.sh"

KAN_PREFIX="final_${LOCATION_TARGET}_vertical_horizontal_localization_fusion"
LCS_PREFIX="final_${LOCATION_TARGET}_vertical_horizontal_lcs_binary_only_fusion"
KAN_FINAL_DIR="$KAN_ROOT/final_vertical_horizontal_location_fusion"
LCS_FINAL_DIR="$LCS_ROOT/final_vertical_horizontal_location_fusion"

echo ""
echo "[3/3] Final KAN-vs-LCS system comparison..."
"$PYTHON_BIN" "$PWD/location_system_comparison.py" \
  --kan-csv "$KAN_FINAL_DIR/${KAN_PREFIX}.csv" \
  --kan-json "$KAN_FINAL_DIR/${KAN_PREFIX}.json" \
  --lcs-csv "$LCS_FINAL_DIR/${LCS_PREFIX}.csv" \
  --lcs-json "$LCS_FINAL_DIR/${LCS_PREFIX}.json" \
  --output-dir "$COMPARISON_DIR" \
  --output-prefix "final_${LOCATION_TARGET}_kan_only_vs_lcs_binary_only_system_comparison" \
  --title "${LOCATION_TARGET} KAN-only vs LCS binary-only localization comparison"

echo ""
echo "[extra] Method rules/readability report..."
"$PYTHON_BIN" "$PWD/location_rules_summary.py" \
  --kan-root "$KAN_ROOT" \
  --lcs-root "$LCS_ROOT" \
  --output-dir "$RULES_DIR" \
  --output-prefix "final_${LOCATION_TARGET}_kan_lcs_rules_summary" \
  --title "${LOCATION_TARGET} KAN surrogate vs LCS rule summary" \
  --max-rules "${RULE_SUMMARY_MAX_RULES:-12}"

{
  echo "# Academic KAN vs LCS Localization Macro Comparison"
  echo ""
  echo "- KAN-only root: \`$KAN_ROOT\`"
  echo "- LCS binary-only root: \`$LCS_ROOT\`"
  echo "- final comparison: \`$COMPARISON_DIR/final_${LOCATION_TARGET}_kan_only_vs_lcs_binary_only_system_comparison.md\`"
  echo "- rules summary: \`$RULES_DIR/final_${LOCATION_TARGET}_kan_lcs_rules_summary.md\`"
  echo ""
  echo "KAN-only uses analog + binary localization fusion. LCS/LCS-hybrid is evaluated as a binary-only/unary threshold method because it does not estimate a continuous coordinate in this pipeline."
} > "$ROOT_DIR/academic_macro_comparison_manifest.md"

echo ""
echo "======================================================================"
echo " Academic macro comparison ready"
echo " Root:       $ROOT_DIR"
echo " KAN final:  $KAN_FINAL_DIR/${KAN_PREFIX}.md"
echo " LCS final:  $LCS_FINAL_DIR/${LCS_PREFIX}.md"
echo " Compare:    $COMPARISON_DIR/final_${LOCATION_TARGET}_kan_only_vs_lcs_binary_only_system_comparison.md"
echo " PNG:        $COMPARISON_DIR/final_${LOCATION_TARGET}_kan_only_vs_lcs_binary_only_system_comparison.png"
echo " Rules:      $RULES_DIR/final_${LOCATION_TARGET}_kan_lcs_rules_summary.md"
echo " Rules PNG:  $RULES_DIR/final_${LOCATION_TARGET}_kan_lcs_rules_summary.png"
echo " Manifest:   $ROOT_DIR/academic_macro_comparison_manifest.md"
echo "======================================================================"

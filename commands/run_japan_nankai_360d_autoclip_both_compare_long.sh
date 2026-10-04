#!/usr/bin/env bash
# Run both Japan/Nankai 360d auto-clip variants with the LONG training profile,
# then compare their final smart-fusion forecasts with forecast_common_window.py.
#
# Variants:
#   vertical   = preserve 1498 history, remove unavailable JPL bodies
#   horizontal = preserve bodies, clip date range when Horizons requires it
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
VERTICAL_OUT_DIR="${VERTICAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-autoclip-vertical-long}"
HORIZONTAL_OUT_DIR="${HORIZONTAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-autoclip-horizontal-long}"
COMPARE_ROOT="${COMPARE_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-autoclip-comparison-long}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPARE_DIR="${COMPARE_DIR:-$COMPARE_ROOT/comparison_$STAMP}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"

START_DATE="${START_DATE:-1498-01-01}"
END_DATE="${END_DATE:-2035-12-31}"
FORECAST_START="${FORECAST_START:-2023-01-01}"
FORECAST_END="${FORECAST_END:-2035-12-31}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-30}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-5}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-3}"

SKIP_VERTICAL="${SKIP_VERTICAL:-0}"
SKIP_HORIZONTAL="${SKIP_HORIZONTAL:-0}"
SKIP_RUNS="${SKIP_RUNS:-0}"
SKIP_MASTER="${SKIP_MASTER:-0}"
THRESHOLD="${THRESHOLD:-0.5}"

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

find_smart_forecast() {
    local run_dir="$1"
    local preferred="$run_dir/post_hybrid_checks_smart/smart_fusion_final__forecast.csv"
    local found=""
    if [[ -f "$preferred" ]]; then
        printf '%s\n' "$preferred"
        return 0
    fi
    found="$(find "$run_dir/post_hybrid_checks_smart" -type f -name 'smart_fusion_final__forecast.csv' 2>/dev/null | sort | tail -n 1 || true)"
    [[ -n "$found" && -f "$found" ]] || return 1
    printf '%s\n' "$found"
}

run_variant() {
    local label="$1"
    local out_dir="$2"
    local auto_clip="$3"
    local db_file="$4"
    local log_file="$5"
    local master_path="$out_dir/master_with_usgs_core_astrofmt.csv"

    if [[ "$SKIP_MASTER" != "1" ]]; then
        echo ""
        echo "[$label] Creating 360d master with auto-clip=$auto_clip..."
        env \
            OUT_DIR="$out_dir" \
            MASTER_OUT="$master_path" \
            START_DATE="$START_DATE" \
            END_DATE="$END_DATE" \
            AUTO_CLIP="$auto_clip" \
            ON_BODY_ERROR="${ON_BODY_ERROR:-fail}" \
            "$PWD/commands/create_master_japan_nankai_360d.sh"
    else
        echo ""
        echo "[$label] Master creation skipped: $master_path"
    fi

    echo ""
    echo "[$label] Running LONG training..."
    env \
        MASTER="$master_path" \
        DB_FILE="$db_file" \
        LOG_FILE="$log_file" \
        FORECAST_START="$FORECAST_START" \
        FORECAST_END="$FORECAST_END" \
        VALIDATION_MAX_LOOKBACK_RECORDS="$VALIDATION_MAX_LOOKBACK_RECORDS" \
        VALIDATION_EVENT_COUNT="$VALIDATION_EVENT_COUNT" \
        VALIDATION_PRE_RECORDS="$VALIDATION_PRE_RECORDS" \
        VALIDATION_POST_RECORDS="$VALIDATION_POST_RECORDS" \
        "$PWD/commands/train_japan_nankai_360d_long.sh"
}

echo "======================================================================"
echo " Japan/Nankai 360d - LONG auto-clip vertical + horizontal + comparison"
echo " Vertical out:    $VERTICAL_OUT_DIR"
echo " Horizontal out:  $HORIZONTAL_OUT_DIR"
echo " Compare out:     $COMPARE_DIR"
echo " Date coverage:   $START_DATE -> $END_DATE"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " Val lookback:    $VALIDATION_MAX_LOOKBACK_RECORDS"
echo " Val events:      $VALIDATION_EVENT_COUNT"
echo " Long profile:    more banks/readouts/hybrid, compact LCS, smart 3 peaks, final 2 peaks"
echo "======================================================================"

if [[ "$SKIP_RUNS" != "1" && "$SKIP_VERTICAL" != "1" ]]; then
    run_variant \
        "1/3 vertical" \
        "$VERTICAL_OUT_DIR" \
        "vertical" \
        "${VERTICAL_DB_FILE:-japan_nankai_360d_autoclip_vertical_long.db}" \
        "${VERTICAL_LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_autoclip_vertical_long.log}"
else
    echo ""
    echo "[1/3] Vertical auto-clip pipeline skipped."
fi

if [[ "$SKIP_RUNS" != "1" && "$SKIP_HORIZONTAL" != "1" ]]; then
    run_variant \
        "2/3 horizontal" \
        "$HORIZONTAL_OUT_DIR" \
        "horizontal" \
        "${HORIZONTAL_DB_FILE:-japan_nankai_360d_autoclip_horizontal_long.db}" \
        "${HORIZONTAL_LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_autoclip_horizontal_long.log}"
else
    echo ""
    echo "[2/3] Horizontal auto-clip pipeline skipped."
fi

echo ""
echo "[3/3] Comparing latest smart-fusion forecasts..."
VERTICAL_RUN="$(find_latest_run_dir "$VERTICAL_OUT_DIR")" || {
    echo "[ERROR] No vertical run directory found under: $VERTICAL_OUT_DIR" >&2
    exit 1
}
HORIZONTAL_RUN="$(find_latest_run_dir "$HORIZONTAL_OUT_DIR")" || {
    echo "[ERROR] No horizontal run directory found under: $HORIZONTAL_OUT_DIR" >&2
    exit 1
}
VERTICAL_FORECAST="$(find_smart_forecast "$VERTICAL_RUN")" || {
    echo "[ERROR] No vertical smart_fusion_final__forecast.csv found in: $VERTICAL_RUN" >&2
    exit 1
}
HORIZONTAL_FORECAST="$(find_smart_forecast "$HORIZONTAL_RUN")" || {
    echo "[ERROR] No horizontal smart_fusion_final__forecast.csv found in: $HORIZONTAL_RUN" >&2
    exit 1
}

mkdir -p "$COMPARE_DIR"
SOURCE_MANIFEST="$COMPARE_DIR/source_forecasts.txt"
{
    printf 'vertical_run=%s\n' "$VERTICAL_RUN"
    printf 'vertical_forecast=%s\n' "$VERTICAL_FORECAST"
    printf 'horizontal_run=%s\n' "$HORIZONTAL_RUN"
    printf 'horizontal_forecast=%s\n' "$HORIZONTAL_FORECAST"
} > "$SOURCE_MANIFEST"

"$PYTHON_BIN" "$PWD/forecast_common_window.py" \
    "$VERTICAL_FORECAST" \
    "$HORIZONTAL_FORECAST" \
    --output-csv "$COMPARE_DIR/vertical_vs_horizontal_common_detected_window.csv" \
    --output-png "$COMPARE_DIR/vertical_vs_horizontal_common_detected_window.png" \
    --output-json "$COMPARE_DIR/vertical_vs_horizontal_common_detected_window.json" \
    --score-column auto \
    --threshold "$THRESHOLD" \
    --title "Japan/Nankai 360d LONG vertical vs horizontal common forecast window"

echo ""
echo "======================================================================"
echo " LONG comparison ready"
echo " Vertical forecast:   $VERTICAL_FORECAST"
echo " Horizontal forecast: $HORIZONTAL_FORECAST"
echo " Source manifest:     $SOURCE_MANIFEST"
echo " CSV:                 $COMPARE_DIR/vertical_vs_horizontal_common_detected_window.csv"
echo " PNG:                 $COMPARE_DIR/vertical_vs_horizontal_common_detected_window.png"
echo " JSON:                $COMPARE_DIR/vertical_vs_horizontal_common_detected_window.json"
echo "======================================================================"

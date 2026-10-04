#!/usr/bin/env bash
# Japan/Nankai observer-frame vertical vs horizontal auto-clip comparison.
#
# This is intentionally short and KAN-only:
#   1. build vertical auto-clip master
#   2. run short KAN-only train/validation/forecast
#   3. build horizontal auto-clip master, where temporal errors clip dates and
#      non-temporal errors fall back to vertical body removal
#   4. run short KAN-only train/validation/forecast
#   5. compare the two KAN strength-fused forecasts
#   6. write a Markdown explanation of clipping decisions
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
VERTICAL_OUT_DIR="${VERTICAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-observer-japan-center-autoclip-vertical-kan-short}"
HORIZONTAL_OUT_DIR="${HORIZONTAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-observer-japan-center-autoclip-horizontal-kan-short}"
COMPARE_ROOT="${COMPARE_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-360d-observer-japan-center-autoclip-kan-short-comparison}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPARE_DIR="${COMPARE_DIR:-$COMPARE_ROOT/comparison_$STAMP}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"

START_DATE="${START_DATE:-1498-01-01}"
END_DATE="${END_DATE:-2035-12-31}"
FORECAST_START="${FORECAST_START:-2023-01-01}"
FORECAST_END="${FORECAST_END:-2035-12-31}"

OBSERVER_LAT="${OBSERVER_LAT:-34.5}"
OBSERVER_LON="${OBSERVER_LON:-137.5}"
OBSERVER_ELEVATION="${OBSERVER_ELEVATION:-0}"
OBSERVER_ALIAS="${OBSERVER_ALIAS:-japan_center}"

SEEDS_SPEC="${SEEDS_SPEC:-4,5,6}"
MAX_ITER="${MAX_ITER:-45}"
JOBS="${JOBS:-1}"
KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small}"
BEST_N="${BEST_N:-12}"
KEEP_BEST="${KEEP_BEST:-12}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-30}"
TARGET_PRE_RECORDS="${TARGET_PRE_RECORDS:-5}"
TARGET_POST_RECORDS="${TARGET_POST_RECORDS:-3}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-5}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-3}"
BACKTEST_PRE_RECORDS="${BACKTEST_PRE_RECORDS:-5}"
BACKTEST_POST_RECORDS="${BACKTEST_POST_RECORDS:-3}"
THRESHOLD="${THRESHOLD:-0.5}"

SKIP_VERTICAL="${SKIP_VERTICAL:-0}"
SKIP_HORIZONTAL="${SKIP_HORIZONTAL:-0}"
SKIP_RUNS="${SKIP_RUNS:-0}"
SKIP_MASTER="${SKIP_MASTER:-0}"

FUSION_PY="${FUSION_PY:-$PWD/kan_forecast_strength_fusion.py}"
SUMMARY_PY="${SUMMARY_PY:-$PWD/summarize_autoclip_manifests.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python venv not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$FUSION_PY" ]] || { echo "[ERROR] FUSION_PY not found: $FUSION_PY" >&2; exit 1; }
[[ -f "$SUMMARY_PY" ]] || { echo "[ERROR] SUMMARY_PY not found: $SUMMARY_PY" >&2; exit 1; }

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

train_kan_short() {
    local label="$1"
    local master_path="$2"
    local out_dir="$3"
    local db_file="$4"
    local log_file="$5"

    echo ""
    echo "[$label] KAN-only short train/validation/forecast..."
    export PYTHONUNBUFFERED=1
    export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
    export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
    export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
    export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

    "$PYTHON_BIN" -u cli.py train \
      --task "$master_path" \
      --target_cols_list mag \
      --skip_cols_list date,depth,latitude,longitude \
      --no-banks \
      --enable-kan \
      --kan-presets "$KAN_PRESETS_RUN" \
      --kan-device cpu \
      --metric-mode auto \
      --metric-target-threshold 0.1 \
      --metric-prediction-threshold 0.5 \
      --event-score-mode isolation \
      --target-window-threshold 0.1 \
      --target-window-event-count "$TARGET_EVENT_COUNT" \
      --target-window-pre-records "$TARGET_PRE_RECORDS" \
      --target-window-post-records "$TARGET_POST_RECORDS" \
      --isolated-event-windows \
      --backtest-event-count 1 \
      --backtest-step-events 1 \
      --backtest-pre-records "$BACKTEST_PRE_RECORDS" \
      --backtest-post-records "$BACKTEST_POST_RECORDS" \
      --backtest-min-train-events 2 \
      --backtest-max-windows 3 \
      --backtest-recency-weight exp \
      --backtest-recency-strength 1.0 \
      --recent-validation-window \
      --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
      --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
      --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
      --recent-validation-weight 3.5 \
      --recent-validation-random-negatives 0 \
      --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
      --forecast-start-date "$FORECAST_START" \
      --forecast-end-date "$FORECAST_END" \
      --forecast-trainset train2forecast \
      --train-recency-weight exp \
      --train-recency-strength 1.0 \
      --train-event-weight auto \
      --train-max-event-weight 8.0 \
      --final-eval-rank-power 1.0 \
      --final-eval-best-fraction 0.50 \
      --final-eval-worst-fraction 0.0 \
      --final-eval-shape-power 1.5 \
      --readability-weight 0.35 \
      --readability-floor 0.3 \
      --seeds "$SEEDS_SPEC" \
      --max-iter "$MAX_ITER" \
      --jobs "$JOBS" \
      --best "$BEST_N" \
      --keep-best "$KEEP_BEST" \
      --keep-worst 0 \
      --no-invert-twin \
      --no-export-best-by-bank \
      --no-collage \
      --db "$db_file" \
      --verbose \
      2>&1 | tee "$log_file"
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
        echo "[$label] Creating observer 360d master with auto-clip=$auto_clip..."
        env \
            OUT_DIR="$out_dir" \
            MASTER_OUT="$master_path" \
            START_DATE="$START_DATE" \
            END_DATE="$END_DATE" \
            AUTO_CLIP="$auto_clip" \
            ON_BODY_ERROR=fail \
            OBSERVER_LAT="$OBSERVER_LAT" \
            OBSERVER_LON="$OBSERVER_LON" \
            OBSERVER_ELEVATION="$OBSERVER_ELEVATION" \
            OBSERVER_ALIAS="$OBSERVER_ALIAS" \
            "$PWD/commands/create_master_japan_nankai_360d_observer_japan.sh"
    else
        echo ""
        echo "[$label] Master creation skipped: $master_path"
    fi

    train_kan_short "$label" "$master_path" "$out_dir" "$db_file" "$log_file"
}

echo "======================================================================"
echo " Japan/Nankai 360d OBSERVER - KAN-only SHORT vertical/horizontal compare"
echo " Observer:        $OBSERVER_ALIAS lat=$OBSERVER_LAT lon=$OBSERVER_LON elev=${OBSERVER_ELEVATION}km"
echo " Vertical out:    $VERTICAL_OUT_DIR"
echo " Horizontal out:  $HORIZONTAL_OUT_DIR"
echo " Compare out:     $COMPARE_DIR"
echo " Date coverage:   $START_DATE -> $END_DATE"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " KAN:             presets=$KAN_PRESETS_RUN seeds=$SEEDS_SPEC iter=$MAX_ITER jobs=$JOBS"
echo "======================================================================"

if [[ "$SKIP_RUNS" != "1" && "$SKIP_VERTICAL" != "1" ]]; then
    run_variant \
        "1/3 observer vertical" \
        "$VERTICAL_OUT_DIR" \
        "vertical" \
        "${VERTICAL_DB_FILE:-$VERTICAL_OUT_DIR/japan_nankai_360d_observer_vertical_kan_short.db}" \
        "${VERTICAL_LOG_FILE:-$VERTICAL_OUT_DIR/kan_short_train.log}"
else
    echo ""
    echo "[1/3] Observer vertical pipeline skipped."
fi

if [[ "$SKIP_RUNS" != "1" && "$SKIP_HORIZONTAL" != "1" ]]; then
    run_variant \
        "2/3 observer horizontal" \
        "$HORIZONTAL_OUT_DIR" \
        "horizontal" \
        "${HORIZONTAL_DB_FILE:-$HORIZONTAL_OUT_DIR/japan_nankai_360d_observer_horizontal_kan_short.db}" \
        "${HORIZONTAL_LOG_FILE:-$HORIZONTAL_OUT_DIR/kan_short_train.log}"
else
    echo ""
    echo "[2/3] Observer horizontal pipeline skipped."
fi

echo ""
echo "[3/3] KAN strength fusion + vertical/horizontal common-window comparison..."
VERTICAL_RUN="$(find_latest_run_dir "$VERTICAL_OUT_DIR")" || {
    echo "[ERROR] No vertical run directory found under: $VERTICAL_OUT_DIR" >&2
    exit 1
}
HORIZONTAL_RUN="$(find_latest_run_dir "$HORIZONTAL_OUT_DIR")" || {
    echo "[ERROR] No horizontal run directory found under: $HORIZONTAL_OUT_DIR" >&2
    exit 1
}

"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$VERTICAL_RUN/best_trials_index.csv" \
  --output-dir "$VERTICAL_RUN/kan_360d_strength_fusion" \
  --output-prefix kan_360d_strength_fusion \
  --score-column auto \
  --top-n 0 \
  --threshold "$THRESHOLD" \
  --max-peaks 1 \
  --title "Japan/Nankai 360d observer vertical KAN-only forecast fusion"

"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$HORIZONTAL_RUN/best_trials_index.csv" \
  --output-dir "$HORIZONTAL_RUN/kan_360d_strength_fusion" \
  --output-prefix kan_360d_strength_fusion \
  --score-column auto \
  --top-n 0 \
  --threshold "$THRESHOLD" \
  --max-peaks 1 \
  --title "Japan/Nankai 360d observer horizontal KAN-only forecast fusion"

VERTICAL_FORECAST="$VERTICAL_RUN/kan_360d_strength_fusion/kan_360d_strength_fusion.csv"
HORIZONTAL_FORECAST="$HORIZONTAL_RUN/kan_360d_strength_fusion/kan_360d_strength_fusion.csv"
VERTICAL_MANIFEST="$VERTICAL_OUT_DIR/master_with_usgs_core_astrofmt_manifest.json"
HORIZONTAL_MANIFEST="$HORIZONTAL_OUT_DIR/master_with_usgs_core_astrofmt_manifest.json"

mkdir -p "$COMPARE_DIR"
SOURCE_MANIFEST="$COMPARE_DIR/source_forecasts.txt"
{
    printf 'observer=%s,%s,%s,%s\n' "$OBSERVER_ALIAS" "$OBSERVER_LAT" "$OBSERVER_LON" "$OBSERVER_ELEVATION"
    printf 'vertical_run=%s\n' "$VERTICAL_RUN"
    printf 'vertical_forecast=%s\n' "$VERTICAL_FORECAST"
    printf 'vertical_master_manifest=%s\n' "$VERTICAL_MANIFEST"
    printf 'horizontal_run=%s\n' "$HORIZONTAL_RUN"
    printf 'horizontal_forecast=%s\n' "$HORIZONTAL_FORECAST"
    printf 'horizontal_master_manifest=%s\n' "$HORIZONTAL_MANIFEST"
} > "$SOURCE_MANIFEST"

"$PYTHON_BIN" "$PWD/forecast_common_window.py" \
    "$VERTICAL_FORECAST" \
    "$HORIZONTAL_FORECAST" \
    --output-csv "$COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.csv" \
    --output-png "$COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.png" \
    --output-json "$COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.json" \
    --score-column fused_score \
    --threshold "$THRESHOLD" \
    --title "Japan/Nankai 360d OBSERVER KAN-only vertical vs horizontal common forecast window"

"$PYTHON_BIN" "$SUMMARY_PY" \
    --vertical-manifest "$VERTICAL_MANIFEST" \
    --horizontal-manifest "$HORIZONTAL_MANIFEST" \
    --common-csv "$COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.csv" \
    --output-md "$COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_clip_report.md" \
    --title "Japan/Nankai 360d Observer KAN-only Auto-Clip Comparison"

echo ""
echo "======================================================================"
echo " KAN-only SHORT comparison ready"
echo " Vertical forecast:   $VERTICAL_FORECAST"
echo " Horizontal forecast: $HORIZONTAL_FORECAST"
echo " Source manifest:     $SOURCE_MANIFEST"
echo " CSV:                 $COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.csv"
echo " PNG:                 $COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.png"
echo " JSON:                $COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_common_detected_window.json"
echo " MD report:           $COMPARE_DIR/observer_vertical_vs_horizontal_kan_short_clip_report.md"
echo "======================================================================"

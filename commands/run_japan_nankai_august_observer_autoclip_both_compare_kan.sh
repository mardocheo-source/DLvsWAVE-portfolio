#!/usr/bin/env bash
# Japan/Nankai August KAN-only vertical/horizontal auto-clip comparison.
#
# Master is sparse:
#   - ±18 days around historical Japan/Nankai M8+ events by default
#   - forecast grid 2026-08-01 -> 2026-08-30
#   - configurable STEP_DAYS cadence
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
START_DATE="${START_DATE:-1498-01-01}"
END_DATE="${END_DATE:-2035-12-31}"
FORECAST_START="${FORECAST_START:-2026-08-01}"
FORECAST_END="${FORECAST_END:-2026-08-30}"
STEP_DAYS="${STEP_DAYS:-3}"
STEP_TAG="${STEP_DAYS}d"
VERTICAL_OUT_DIR="${VERTICAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-${STEP_TAG}-august-observer-autoclip-vertical-kan-short}"
HORIZONTAL_OUT_DIR="${HORIZONTAL_OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-${STEP_TAG}-august-observer-autoclip-horizontal-kan-short}"
COMPARE_ROOT="${COMPARE_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-${STEP_TAG}-august-observer-autoclip-kan-short-comparison}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPARE_DIR="${COMPARE_DIR:-$COMPARE_ROOT/comparison_$STAMP}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
EVENT_WINDOW_DAYS_BEFORE="${EVENT_WINDOW_DAYS_BEFORE:-18}"
EVENT_WINDOW_DAYS_AFTER="${EVENT_WINDOW_DAYS_AFTER:-18}"

OBSERVER_LAT="${OBSERVER_LAT:-34.5}"
OBSERVER_LON="${OBSERVER_LON:-137.5}"
OBSERVER_ELEVATION="${OBSERVER_ELEVATION:-0}"
OBSERVER_ALIAS="${OBSERVER_ALIAS:-japan_center}"

SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35}"
MAX_ITER="${MAX_ITER:-3600}"
JOBS="${JOBS:-2}"
KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
BEST_N="${BEST_N:-160}"
KEEP_BEST="${KEEP_BEST:-160}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-1400}"
TARGET_PRE_RECORDS="${TARGET_PRE_RECORDS:-6}"
TARGET_POST_RECORDS="${TARGET_POST_RECORDS:-6}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"
BACKTEST_PRE_RECORDS="${BACKTEST_PRE_RECORDS:-6}"
BACKTEST_POST_RECORDS="${BACKTEST_POST_RECORDS:-6}"
BACKTEST_RECENCY_STRENGTH="${BACKTEST_RECENCY_STRENGTH:-1.0}"
RECENT_VALIDATION_WEIGHT="${RECENT_VALIDATION_WEIGHT:-4.0}"
TRAIN_RECENCY_STRENGTH="${TRAIN_RECENCY_STRENGTH:-1.0}"
TRAIN_MAX_EVENT_WEIGHT="${TRAIN_MAX_EVENT_WEIGHT:-8.0}"
THRESHOLD="${THRESHOLD:-0.5}"

SKIP_VERTICAL="${SKIP_VERTICAL:-0}"
SKIP_HORIZONTAL="${SKIP_HORIZONTAL:-0}"
SKIP_RUNS="${SKIP_RUNS:-0}"
SKIP_MASTER="${SKIP_MASTER:-0}"

FUSION_PY="${FUSION_PY:-$PWD/kan_forecast_strength_fusion.py}"
SUMMARY_PY="${SUMMARY_PY:-$PWD/summarize_autoclip_manifests.py}"
LINEAGE_PY="${LINEAGE_PY:-$PWD/kan_vertical_horizontal_lineage.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python venv not executable: $PYTHON_BIN" >&2; exit 1; }

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
    local db_file="$3"
    local log_file="$4"

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
      --backtest-max-windows 6 \
      --backtest-recency-weight exp \
      --backtest-recency-strength "$BACKTEST_RECENCY_STRENGTH" \
      --recent-validation-window \
      --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
      --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
      --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
      --recent-validation-weight "$RECENT_VALIDATION_WEIGHT" \
      --recent-validation-random-negatives 0 \
      --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
      --forecast-start-date "$FORECAST_START" \
      --forecast-end-date "$FORECAST_END" \
      --forecast-trainset train2forecast \
      --train-recency-weight exp \
      --train-recency-strength "$TRAIN_RECENCY_STRENGTH" \
      --train-event-weight auto \
      --train-max-event-weight "$TRAIN_MAX_EVENT_WEIGHT" \
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
        echo "[$label] Creating sparse ${STEP_TAG} observer master with auto-clip=$auto_clip..."
        env \
            OUT_DIR="$out_dir" \
            MASTER_OUT="$master_path" \
            START_DATE="$START_DATE" \
            END_DATE="$END_DATE" \
            FORECAST_START="$FORECAST_START" \
            FORECAST_END="$FORECAST_END" \
            STEP_DAYS="$STEP_DAYS" \
            EVENT_WINDOW_DAYS_BEFORE="$EVENT_WINDOW_DAYS_BEFORE" \
            EVENT_WINDOW_DAYS_AFTER="$EVENT_WINDOW_DAYS_AFTER" \
            AUTO_CLIP="$auto_clip" \
            ON_BODY_ERROR=fail \
            OBSERVER_LAT="$OBSERVER_LAT" \
            OBSERVER_LON="$OBSERVER_LON" \
            OBSERVER_ELEVATION="$OBSERVER_ELEVATION" \
            OBSERVER_ALIAS="$OBSERVER_ALIAS" \
            "$PWD/commands/create_master_japan_nankai_august_observer_japan_sparse.sh"
    else
        echo ""
        echo "[$label] Master creation skipped: $master_path"
    fi

    train_kan_short "$label" "$master_path" "$db_file" "$log_file"
}

echo "======================================================================"
echo " Japan/Nankai ${STEP_TAG} August OBSERVER - KAN-only vertical/horizontal compare"
echo " Event meat:      -${EVENT_WINDOW_DAYS_BEFORE}d / +${EVENT_WINDOW_DAYS_AFTER}d"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " Step:            ${STEP_DAYS}d"
echo " Vertical out:    $VERTICAL_OUT_DIR"
echo " Horizontal out:  $HORIZONTAL_OUT_DIR"
echo " Compare out:     $COMPARE_DIR"
echo " KAN:             presets=$KAN_PRESETS_RUN seeds=$SEEDS_SPEC iter=$MAX_ITER jobs=$JOBS"
echo " Validation meat: target pre/post=$TARGET_PRE_RECORDS/$TARGET_POST_RECORDS recent pre/post=$VALIDATION_PRE_RECORDS/$VALIDATION_POST_RECORDS"
echo " Weights:         train_recency=$TRAIN_RECENCY_STRENGTH train_event_max=$TRAIN_MAX_EVENT_WEIGHT recent_val=$RECENT_VALIDATION_WEIGHT backtest_recency=$BACKTEST_RECENCY_STRENGTH"
echo "======================================================================"

if [[ "$SKIP_RUNS" != "1" && "$SKIP_VERTICAL" != "1" ]]; then
    run_variant "1/3 observer vertical ${STEP_TAG}" "$VERTICAL_OUT_DIR" "vertical" \
        "${VERTICAL_DB_FILE:-$VERTICAL_OUT_DIR/japan_nankai_${STEP_TAG}_observer_vertical_kan_short.db}" \
        "${VERTICAL_LOG_FILE:-$VERTICAL_OUT_DIR/kan_short_train.log}"
fi

if [[ "$SKIP_RUNS" != "1" && "$SKIP_HORIZONTAL" != "1" ]]; then
    run_variant "2/3 observer horizontal ${STEP_TAG}" "$HORIZONTAL_OUT_DIR" "horizontal" \
        "${HORIZONTAL_DB_FILE:-$HORIZONTAL_OUT_DIR/japan_nankai_${STEP_TAG}_observer_horizontal_kan_short.db}" \
        "${HORIZONTAL_LOG_FILE:-$HORIZONTAL_OUT_DIR/kan_short_train.log}"
fi

echo ""
echo "[3/3] KAN strength fusion + vertical/horizontal common-window comparison..."
VERTICAL_RUN="$(find_latest_run_dir "$VERTICAL_OUT_DIR")" || { echo "[ERROR] No vertical run under $VERTICAL_OUT_DIR" >&2; exit 1; }
HORIZONTAL_RUN="$(find_latest_run_dir "$HORIZONTAL_OUT_DIR")" || { echo "[ERROR] No horizontal run under $HORIZONTAL_OUT_DIR" >&2; exit 1; }

"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$VERTICAL_RUN/best_trials_index.csv" \
  --output-dir "$VERTICAL_RUN/kan_${STEP_TAG}_august_strength_fusion" \
  --output-prefix "kan_${STEP_TAG}_august_strength_fusion" \
  --score-column auto \
  --top-n 0 \
  --threshold "$THRESHOLD" \
  --max-peaks 1 \
  --title "Japan/Nankai August 2026 ${STEP_TAG} observer vertical KAN-only forecast fusion"

"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$HORIZONTAL_RUN/best_trials_index.csv" \
  --output-dir "$HORIZONTAL_RUN/kan_${STEP_TAG}_august_strength_fusion" \
  --output-prefix "kan_${STEP_TAG}_august_strength_fusion" \
  --score-column auto \
  --top-n 0 \
  --threshold "$THRESHOLD" \
  --max-peaks 1 \
  --title "Japan/Nankai August 2026 ${STEP_TAG} observer horizontal KAN-only forecast fusion"

VERTICAL_FORECAST="$VERTICAL_RUN/kan_${STEP_TAG}_august_strength_fusion/kan_${STEP_TAG}_august_strength_fusion.csv"
HORIZONTAL_FORECAST="$HORIZONTAL_RUN/kan_${STEP_TAG}_august_strength_fusion/kan_${STEP_TAG}_august_strength_fusion.csv"
VERTICAL_MANIFEST="$VERTICAL_OUT_DIR/master_with_usgs_core_astrofmt_manifest.json"
HORIZONTAL_MANIFEST="$HORIZONTAL_OUT_DIR/master_with_usgs_core_astrofmt_manifest.json"

mkdir -p "$COMPARE_DIR"
SOURCE_MANIFEST="$COMPARE_DIR/source_forecasts.txt"
{
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
    --output-csv "$COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.csv" \
    --output-png "$COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.png" \
    --output-json "$COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.json" \
    --score-column fused_score \
    --source-labels "vertical autoclip,horizontal autoclip" \
    --threshold "$THRESHOLD" \
    --title "Japan/Nankai August 2026 ${STEP_TAG} OBSERVER KAN-only vertical vs horizontal common forecast window"

"$PYTHON_BIN" "$SUMMARY_PY" \
    --vertical-manifest "$VERTICAL_MANIFEST" \
    --horizontal-manifest "$HORIZONTAL_MANIFEST" \
    --common-csv "$COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.csv" \
    --output-md "$COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_clip_report.md" \
    --title "Japan/Nankai August 2026 ${STEP_TAG} Observer KAN-only Auto-Clip Comparison"

"$PYTHON_BIN" "$LINEAGE_PY" \
    --vertical-run "$VERTICAL_RUN" \
    --horizontal-run "$HORIZONTAL_RUN" \
    --vertical-manifest "$VERTICAL_MANIFEST" \
    --horizontal-manifest "$HORIZONTAL_MANIFEST" \
    --output-dir "$COMPARE_DIR/vertical_horizontal_kan_lineage" \
    --name "observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_lineage" \
    --logic weighted \
    --alpha 0.5 \
    --threshold "$THRESHOLD" \
    --normalize auto \
    --score-column predicted \
    --calibrate validation \
    --calibrate-metric f1 \
    --comparison-report-dir "$COMPARE_DIR"

echo ""
echo "======================================================================"
echo " Correct ${STEP_TAG} August KAN-only comparison ready"
echo " CSV:       $COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.csv"
echo " PNG:       $COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.png"
echo " JSON:      $COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_common_detected_window.json"
echo " MD report: $COMPARE_DIR/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_short_clip_report.md"
echo " Lineage:   $COMPARE_DIR/vertical_horizontal_kan_lineage/observer_vertical_vs_horizontal_${STEP_TAG}_august_kan_lineage__lineage_comparison.png"
echo " Val qual:  $COMPARE_DIR/vertical_horizontal_validation_fusion_quality.md"
echo " Val paths: $COMPARE_DIR/vertical_horizontal_validation_fusion_quality_paths.txt"
echo "======================================================================"

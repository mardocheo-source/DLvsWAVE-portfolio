#!/usr/bin/env bash
# Japan/Nankai 3-day August 2026 micro-check, KAN-only.
#
# Purpose:
#   Use the existing reliable macro forecast as context, then run a narrow
#   KAN-only microscope over 2026-08-01 -> 2026-08-30.
#
# Master policy:
#   - historical Japan/Nankai M8+ events only
#   - no global negative anchors
#   - no random in-between/background records
#   - ±10 days around each historical event
#   - 3-day forecast grid over August 2026
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-3d-august-kan-microcheck}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"

FORECAST_START="${FORECAST_START:-2026-08-01}"
FORECAST_END="${FORECAST_END:-2026-08-30}"
STEP_INTERVAL="${STEP_INTERVAL:-3d}"
TIME_BEFORE="${TIME_BEFORE:-10d}"
TIME_AFTER="${TIME_AFTER:-10d}"
NASA_PLACE="${NASA_PLACE:-fullAstroJapan}"
OBSERVER_GEO="${OBSERVER_GEO:-34.5,137.5,0,japan_center}"
MAX_WORKERS="${MAX_WORKERS:-4}"
QUANT_BINS="${QUANT_BINS:-4}"
REBUILD_MASTER="${REBUILD_MASTER:-0}"
CLEAN_BODIES_ON_REBUILD="${CLEAN_BODIES_ON_REBUILD:-1}"
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-1,2,3,4,13,19,31,43}"
BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.14 2.21 2.22 2.3 3.1}"
OBSERVER_LEVELS="${OBSERVER_LEVELS:-2.21}"
USE_SECONDARY_BODIES="${USE_SECONDARY_BODIES:-0}"
BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-4.1 4.31 4.32 4.33 4.34 4.4 5.11 5.22 6.11 6.14 6.21 6.22 7.1}"

SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11,12,13,14,15}"
MAX_ITER="${MAX_ITER:-120}"
JOBS="${JOBS:-1}"
KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
KEEP_BEST="${KEEP_BEST:-24}"
BEST_N="${BEST_N:-24}"
TARGET_PRE_RECORDS="${TARGET_PRE_RECORDS:-4}"
TARGET_POST_RECORDS="${TARGET_POST_RECORDS:-0}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-4}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-0}"
BACKTEST_PRE_RECORDS="${BACKTEST_PRE_RECORDS:-4}"
BACKTEST_POST_RECORDS="${BACKTEST_POST_RECORDS:-0}"

ADD_USGS_PY="${ADD_USGS_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/add_usgs_core_columns_to_master.py}"
CONV_PY="${CONV_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/convert_astro_columns_to_standard.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"
SANITIZE_PY="${SANITIZE_PY:-$PWD/sanitize_numeric_master.py}"
FUSION_PY="${FUSION_PY:-$PWD/kan_forecast_strength_fusion.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python venv not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$ASTRO_ROOT/nasaDb.py" ]] || { echo "[ERROR] nasaDb.py not found: $ASTRO_ROOT/nasaDb.py" >&2; exit 1; }
[[ -f "$EVENTS_CSV" ]] || { echo "[ERROR] EVENTS_CSV not found: $EVENTS_CSV" >&2; exit 1; }
[[ -f "$ADD_USGS_PY" ]] || { echo "[ERROR] ADD_USGS_PY not found: $ADD_USGS_PY" >&2; exit 1; }
[[ -f "$CONV_PY" ]] || { echo "[ERROR] CONV_PY not found: $CONV_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] QUANT_PY not found: $QUANT_PY" >&2; exit 1; }
[[ -f "$SANITIZE_PY" ]] || { echo "[ERROR] SANITIZE_PY not found: $SANITIZE_PY" >&2; exit 1; }
[[ -f "$FUSION_PY" ]] || { echo "[ERROR] FUSION_PY not found: $FUSION_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
cp "$EVENTS_CSV" "$OUT_DIR/earthquakes.RAW.csv"

echo "======================================================================"
echo " Japan/Nankai 3d August 2026 KAN-only micro-check"
echo " Output dir:        $OUT_DIR"
echo " Events:            $EVENTS_CSV"
echo " Master:            $MASTER_OUT"
echo " Forecast:          $FORECAST_START -> $FORECAST_END"
echo " Step/window:       $STEP_INTERVAL, event meat before=$TIME_BEFORE after=$TIME_AFTER"
echo " Background:        none; no random in-between records"
echo " Astro bodies:      primary='$BODY_PRIMARY_LEVELS' secondary_enabled=$USE_SECONDARY_BODIES"
echo " Validation meat:   target pre/post=$TARGET_PRE_RECORDS/$TARGET_POST_RECORDS recent pre/post=$VALIDATION_PRE_RECORDS/$VALIDATION_POST_RECORDS"
echo " KAN presets:       $KAN_PRESETS_RUN"
echo " Seeds/iter/jobs:   $SEEDS_SPEC / $MAX_ITER / $JOBS"
echo " Fusion:            KAN-only strength + consensus, max one peak"
echo "======================================================================"

if [[ "$REBUILD_MASTER" == "1" || ! -f "$MASTER_OUT" ]]; then
  if [[ "$CLEAN_BODIES_ON_REBUILD" == "1" ]]; then
    case "$OUT_DIR" in
      "$ASTRO_ROOT"/DB/*)
        rm -rf "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"
        ;;
      *)
        echo "[ERROR] Refusing to clean nasa_bodies outside ASTRO_ROOT/DB: $OUT_DIR" >&2
        exit 1
        ;;
    esac
  fi
  mkdir -p "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"

  NASA_EXTRA_ARGS=(
    --ephemerides_fields "$EPHEMERIDES_FIELDS"
    --body_primary_levels
  )
  read -r -a BODY_PRIMARY_LEVELS_ARRAY <<< "$BODY_PRIMARY_LEVELS"
  NASA_EXTRA_ARGS+=("${BODY_PRIMARY_LEVELS_ARRAY[@]}")
  NASA_EXTRA_ARGS+=(--observer_levels)
  read -r -a OBSERVER_LEVELS_ARRAY <<< "$OBSERVER_LEVELS"
  NASA_EXTRA_ARGS+=("${OBSERVER_LEVELS_ARRAY[@]}")
  if [[ "$USE_SECONDARY_BODIES" == "1" || "$USE_SECONDARY_BODIES" == "true" ]]; then
    NASA_EXTRA_ARGS+=(--body_secondary_levels)
    read -r -a BODY_SECONDARY_LEVELS_ARRAY <<< "$BODY_SECONDARY_LEVELS"
    NASA_EXTRA_ARGS+=("${BODY_SECONDARY_LEVELS_ARRAY[@]}")
  else
    # Empty nargs list overrides fullAstroJapan secondaries; disable-extra-bodies
    # also removes always-added comet/TNO bodies in nasaDb.py.
    NASA_EXTRA_ARGS+=(--body_secondary_levels)
    NASA_EXTRA_ARGS+=(--disable-extra-bodies)
  fi

  echo ""
  echo "[1/6] NASA/JPL ephemerides via nasaDb.py (sparse event windows + August forecast only)..."
  "$PYTHON_BIN" "$ASTRO_ROOT/nasaDb.py" \
    --csv_file "$OUT_DIR/earthquakes.RAW.csv" \
    --datetime_column time \
    --time_before "$TIME_BEFORE" \
    --time_after "$TIME_AFTER" \
    --step_interval "$STEP_INTERVAL" \
    --start_date "$FORECAST_START" \
    --end_date "$FORECAST_END" \
    --place "$NASA_PLACE" \
    --observer-geo="$OBSERVER_GEO" \
    --bodies_dir "$OUT_DIR/nasa_bodies" \
    --backup_dir "$OUT_DIR/nasa_bodies_backup" \
    --master_output "$OUT_DIR/nasa_master_focus_sparse.csv" \
    --raw_output "$OUT_DIR/nasa_master_focus_sparse.Raw.csv" \
    --command_script "$OUT_DIR/2-nasa_download.replay.sh" \
    --max_workers "$MAX_WORKERS" \
    --progress \
    --chunk-manifest \
    "${NASA_EXTRA_ARGS[@]}"

  echo ""
  echo "[2/6] Add USGS core columns..."
  "$PYTHON_BIN" "$ADD_USGS_PY" \
    --nasa-master "$OUT_DIR/nasa_master_focus_sparse.csv" \
    --usgs-events "$OUT_DIR/earthquakes.RAW.csv" \
    --output "$OUT_DIR/master_with_usgs_core.csv"

  echo ""
  echo "[3/6] Convert legacy NASA columns to astrofmt..."
  "$PYTHON_BIN" "$CONV_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core.csv" \
    --output-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv"

  echo ""
  echo "[4/6] Quartile quantization and numeric sanitization..."
  "$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --output-csv "$MASTER_OUT" \
    --bins "$QUANT_BINS"
  SANITIZED_TMP="$OUT_DIR/master_with_usgs_core_astrofmt.sanitized.tmp.csv"
  "$PYTHON_BIN" "$SANITIZE_PY" \
    --input-csv "$MASTER_OUT" \
    --output-csv "$SANITIZED_TMP" \
    --report-json "$OUT_DIR/master_with_usgs_core_astrofmt_sanitize_report.json" \
    --skip-cols date
  mv "$SANITIZED_TMP" "$MASTER_OUT"
else
  echo "[1-4/6] Existing master found, skip rebuild: $MASTER_OUT"
fi

echo ""
echo "[5/6] KAN-only training and August forecast..."
LOG_FILE="$OUT_DIR/kan_micro_train.log"
DB_FILE="$OUT_DIR/japan_nankai_3d_august_kan_microcheck.db"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

"$PYTHON_BIN" -u cli.py train \
  --task "$MASTER_OUT" \
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
  --target-window-event-count 2 \
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
  --backtest-recency-strength 1.0 \
  --recent-validation-window \
  --recent-validation-event-count 2 \
  --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
  --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
  --recent-validation-weight 4.0 \
  --recent-validation-random-negatives 0 \
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
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

RUN_DIR="$(find "$OUT_DIR" -maxdepth 1 -type d -name 'pulsar_train*_best_trials_*' | sort | tail -n 1)"
[[ -n "$RUN_DIR" && -f "$RUN_DIR/best_trials_index.csv" ]] || {
  echo "[ERROR] Cannot find latest run/best_trials_index.csv under $OUT_DIR" >&2
  exit 1
}

echo ""
echo "[6/6] KAN-only strength fusion over August forecast..."
"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$RUN_DIR/best_trials_index.csv" \
  --output-dir "$RUN_DIR/kan_august_micro_strength_fusion" \
  --score-column auto \
  --top-n 0 \
  --threshold 0.5 \
  --max-peaks 1 \
  --title "Japan/Nankai August 2026 3d KAN-only micro forecast"

echo ""
echo "======================================================================"
echo " KAN-only August micro-check ready"
echo " Run dir: $RUN_DIR"
echo " Fusion: $RUN_DIR/kan_august_micro_strength_fusion"
echo " Log:    $LOG_FILE"
echo "======================================================================"

#!/usr/bin/env bash
# Japan/Nankai 3-day micro forecast, KAN-only, narrow July/August 2026 range.
#
# Scope:
#   - historical rows: only sparse windows around Japan/Nankai M8+ events
#   - no random/background/negative-anchor records
#   - event context: 6 slots before + 6 slots after each event, with 3d slots
#   - forecast rows: real timeline starts from 2026-07-22 through late August
#   - validation: exactly 2 recent historical events
#   - purpose: locate the likely 3d range inside the narrowed July/August period
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-3d-jul22-aug12-kan-micro4h}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"

MIN_HISTORICAL_DATE="${MIN_HISTORICAL_DATE:-1903-01-01}"
FORECAST_START="${FORECAST_START:-2026-07-22}"
FORECAST_END="${FORECAST_END:-2026-08-31}"
STEP_INTERVAL="${STEP_INTERVAL:-3d}"
EVENT_SLOT_COUNT="${EVENT_SLOT_COUNT:-6}"
TIME_BEFORE="${TIME_BEFORE:-18d}"
TIME_AFTER="${TIME_AFTER:-18d}"
NASA_PLACE="${NASA_PLACE:-fullAstroJapan}"
OBSERVER_GEO="${OBSERVER_GEO:-34.5,137.5,0,japan_center}"
MAX_WORKERS="${MAX_WORKERS:-4}"
QUANT_BINS="${QUANT_BINS:-4}"
REBUILD_MASTER="${REBUILD_MASTER:-0}"
CLEAN_BODIES_ON_REBUILD="${CLEAN_BODIES_ON_REBUILD:-1}"

# Keep the master light: a focused set of physical/vector fields and no
# secondary bodies unless explicitly enabled.
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-1,2,3,4,13,19,31,43}"
BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.14 2.21 2.22 2.3 3.1}"
OBSERVER_LEVELS="${OBSERVER_LEVELS:-2.21}"
USE_SECONDARY_BODIES="${USE_SECONDARY_BODIES:-0}"
BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-4.1 4.31 4.32 4.33 4.34 4.4 5.11 5.22 6.11 6.14 6.21 6.22 7.1}"

# This is intentionally capped for a 4-5h style run on CPU. Increase only if
# the first pass is too short or too flat.
KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
KAN_DEVICE="${KAN_DEVICE:-cpu}"
KAN_QUIET="${KAN_QUIET:-0}"
SEEDS_SPEC="${SEEDS_SPEC:-4:18}"
MAX_ITER="${MAX_ITER:-900}"
JOBS="${JOBS:-3}"
BEST_N="${BEST_N:-24}"
KEEP_BEST="${KEEP_BEST:-8}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
TARGET_PRE_RECORDS="${TARGET_PRE_RECORDS:-6}"
TARGET_POST_RECORDS="${TARGET_POST_RECORDS:-6}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"

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
"$PYTHON_BIN" - "$EVENTS_CSV" "$OUT_DIR/earthquakes.RAW.csv" "$MIN_HISTORICAL_DATE" <<'PY'
import sys
import pandas as pd

src, dst, min_date = sys.argv[1:4]
df = pd.read_csv(src)
if "time" not in df.columns:
    raise SystemExit(f"[ERROR] Missing required 'time' column in {src}")

times = pd.to_datetime(df["time"], errors="coerce", utc=True)
min_ts = pd.Timestamp(min_date, tz="UTC")
kept = df.loc[times >= min_ts].copy()
if kept.empty:
    raise SystemExit(f"[ERROR] No events remain after MIN_HISTORICAL_DATE={min_date}")

kept.to_csv(dst, index=False)
print(f"[events] kept {len(kept)}/{len(df)} rows with time >= {min_date}")
print(f"[events] output: {dst}")
PY

LOG_FILE="${LOG_FILE:-$OUT_DIR/kan_3d_jul22_aug12_micro4h.log}"
DB_FILE="${DB_FILE:-$OUT_DIR/japan_nankai_3d_jul22_aug12_kan_micro4h.db}"

cat > "$OUT_DIR/RUN_THIS_PIPELINE.sh" <<EOF
#!/usr/bin/env bash
cd "$(pwd)"
OUT_DIR="$OUT_DIR" \\
FORECAST_START="$FORECAST_START" FORECAST_END="$FORECAST_END" \\
MIN_HISTORICAL_DATE="$MIN_HISTORICAL_DATE" \\
EVENT_SLOT_COUNT="$EVENT_SLOT_COUNT" TIME_BEFORE="$TIME_BEFORE" TIME_AFTER="$TIME_AFTER" \\
TARGET_EVENT_COUNT="$TARGET_EVENT_COUNT" VALIDATION_EVENT_COUNT="$VALIDATION_EVENT_COUNT" \\
TARGET_PRE_RECORDS="$TARGET_PRE_RECORDS" TARGET_POST_RECORDS="$TARGET_POST_RECORDS" \\
VALIDATION_PRE_RECORDS="$VALIDATION_PRE_RECORDS" VALIDATION_POST_RECORDS="$VALIDATION_POST_RECORDS" \\
SEEDS_SPEC="$SEEDS_SPEC" MAX_ITER="$MAX_ITER" JOBS="$JOBS" \\
KAN_PRESETS_RUN="$KAN_PRESETS_RUN" KAN_DEVICE="$KAN_DEVICE" KAN_QUIET="$KAN_QUIET" \\
./commands/run_japan_nankai_3d_jul22_aug12_kan_micro4h.sh
EOF
chmod +x "$OUT_DIR/RUN_THIS_PIPELINE.sh"

cat > "$OUT_DIR/pipeline_notes.md" <<EOF
# Japan/Nankai 3d Jul22-End-August KAN Micro Forecast

- Forecast rows use real timeline dates from ${FORECAST_START} through ${FORECAST_END}.
- Historical event rows are clipped to events on/after ${MIN_HISTORICAL_DATE}, avoiding
  very old synthetic windows that are outside reliable Horizons coverage for several bodies.
- Historical master rows are sparse: only ${EVENT_SLOT_COUNT} slots before and
  ${EVENT_SLOT_COUNT} slots after each historical event, step ${STEP_INTERVAL}.
- No random/background/negative-anchor historical records are added.
- Validation uses ${VALIDATION_EVENT_COUNT} events only.
- KAN presets: ${KAN_PRESETS_RUN}; seeds: ${SEEDS_SPEC}; max_iter: ${MAX_ITER};
  jobs: ${JOBS}.
- Re-run command: \`RUN_THIS_PIPELINE.sh\`.
EOF

echo "======================================================================"
echo " Japan/Nankai 3d Jul22-End-August 2026 KAN micro forecast"
echo " Output dir:        $OUT_DIR"
echo " Events:            $EVENTS_CSV"
echo " Historical clip:   >= $MIN_HISTORICAL_DATE"
echo " Master:            $MASTER_OUT"
echo " Forecast:          $FORECAST_START -> $FORECAST_END"
echo " Step/window:       $STEP_INTERVAL, event slots=$EVENT_SLOT_COUNT before/after ($TIME_BEFORE/$TIME_AFTER)"
echo " Background:        none; no random in-between records"
echo " Astro bodies:      primary='$BODY_PRIMARY_LEVELS' secondary_enabled=$USE_SECONDARY_BODIES"
echo " Validation events: $VALIDATION_EVENT_COUNT"
echo " Validation slots:  target pre/post=$TARGET_PRE_RECORDS/$TARGET_POST_RECORDS recent pre/post=$VALIDATION_PRE_RECORDS/$VALIDATION_POST_RECORDS"
echo " KAN presets:       $KAN_PRESETS_RUN"
echo " KAN device:        $KAN_DEVICE"
echo " KAN quiet:         $KAN_QUIET"
echo " Seeds/iter/jobs:   $SEEDS_SPEC / $MAX_ITER / $JOBS"
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
    NASA_EXTRA_ARGS+=(--body_secondary_levels)
    NASA_EXTRA_ARGS+=(--disable-extra-bodies)
  fi

  echo ""
  echo "[1/6] NASA/JPL ephemerides via nasaDb.py (sparse event windows + isolated forecast only)..."
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
echo "[5/6] KAN-only training and isolated forecast..."
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

KAN_EXTRA_ARGS=()
if [[ "$KAN_QUIET" == "1" || "$KAN_QUIET" == "true" || "$KAN_QUIET" == "yes" ]]; then
  KAN_EXTRA_ARGS+=(--kan-quiet)
fi

"$PYTHON_BIN" -u cli.py train \
  --task "$MASTER_OUT" \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  --no-banks \
  --enable-kan \
  --kan-presets "$KAN_PRESETS_RUN" \
  --kan-device "$KAN_DEVICE" \
  "${KAN_EXTRA_ARGS[@]}" \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 \
  --target-window-event-count "$TARGET_EVENT_COUNT" \
  --target-window-pre-records "$TARGET_PRE_RECORDS" \
  --target-window-post-records "$TARGET_POST_RECORDS" \
  --isolated-event-windows \
  --recent-validation-window \
  --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
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
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

RUN_DIR="$(find "$OUT_DIR" -maxdepth 1 -type d -name 'pulsar_train*_best_trials_*' | sort | tail -n 1)"
[[ -n "$RUN_DIR" && -f "$RUN_DIR/best_trials_index.csv" ]] || {
  echo "[ERROR] Cannot find latest run/best_trials_index.csv under $OUT_DIR" >&2
  exit 1
}

echo ""
echo "[6/6] KAN-only strength fusion over isolated forecast..."
"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$RUN_DIR/best_trials_index.csv" \
  --output-dir "$RUN_DIR/kan_jul22_aug12_micro_strength_fusion" \
  --score-column auto \
  --top-n 0 \
  --threshold 0.5 \
  --max-peaks 1 \
  --title "Japan/Nankai 2026-07-22 to 2026-08-31 3d KAN micro forecast"

echo ""
echo "======================================================================"
echo " KAN-only Jul22-End-August micro forecast ready"
echo " Run dir: $RUN_DIR"
echo " Fusion: $RUN_DIR/kan_jul22_aug12_micro_strength_fusion"
echo " Log:    $LOG_FILE"
echo " Re-run: $OUT_DIR/RUN_THIS_PIPELINE.sh"
echo "======================================================================"

#!/usr/bin/env bash
# Japan M8.0+ monthly KAN forecast using worldwide M8.0+ negative anchors.
#
# Important: the master is first built from real worldwide M8.0+ event dates.
# After the master exists, non-Japan positive bins are silenced to mag=0 and
# seismic fields 0, preserving the astronomical rows while making the target
# Japan-only.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_EVENTS="${SRC_EVENTS:-$ASTRO_ROOT/DB/WORLD-MAG7.7-1900-2025-10-01/earthquakes.RAW.csv}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-mag80plus-world-m8-neganchors-30d-geocentric-kan-long}"
STABLE_EPHEMERIDES_CSV="${STABLE_EPHEMERIDES_CSV:-$(pwd)/resources/japan_nankai_stable_geocentric_ephemerides.csv}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"

START_DATE="${START_DATE:-1900-01-01}"
END_DATE="${END_DATE:-2026-12-31}"
FORECAST_START="${FORECAST_START:-2026-05-01}"
FORECAST_END="${FORECAST_END:-2026-12-31}"
STEP_DAYS="${STEP_DAYS:-30}"
MIN_MAG="${MIN_MAG:-8.0}"
QUANT_BINS="${QUANT_BINS:-4}"

JAPAN_LAT_MIN="${JAPAN_LAT_MIN:-28}"
JAPAN_LAT_MAX="${JAPAN_LAT_MAX:-44}"
JAPAN_LON_MIN="${JAPAN_LON_MIN:-128}"
JAPAN_LON_MAX="${JAPAN_LON_MAX:-147}"

AUTO_CLIP="${AUTO_CLIP:-horizontal}"
MOON_CENTER="${MOON_CENTER:-earth}"
REFPLANE="${REFPLANE:-earth}"
ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"
EXCLUDE_BODIES="${EXCLUDE_BODIES:-}"

KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
KAN_QUIET="${KAN_QUIET:-1}"
SEEDS_SPEC="${SEEDS_SPEC:-4:48}"
MAX_ITER="${MAX_ITER:-3600}"
JOBS="${JOBS:-3}"
BEST_N="${BEST_N:-80}"
KEEP_BEST="${KEEP_BEST:-12}"
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-2}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-2}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-600}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-12}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-20260518}"

PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
BUILDER_PY="${BUILDER_PY:-$(pwd)/build_jpl_safe_360d_master.py}"
FILTER_EVENTS_PY="${FILTER_EVENTS_PY:-$(pwd)/filter_earthquake_events.py}"
MASK_MASTER_PY="${MASK_MASTER_PY:-$(pwd)/mask_master_non_japan_events.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$SRC_EVENTS" ]] || { echo "[ERROR] SRC_EVENTS not found: $SRC_EVENTS" >&2; exit 1; }
[[ -f "$STABLE_EPHEMERIDES_CSV" ]] || { echo "[ERROR] STABLE_EPHEMERIDES_CSV not found: $STABLE_EPHEMERIDES_CSV" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] QUANT_PY not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
LOG_FILE="${LOG_FILE:-$OUT_DIR/japan_mag80_world_m8_neganchors_30d_kan_long.log}"
DB_FILE="${DB_FILE:-$OUT_DIR/japan_mag80_world_m8_neganchors_30d_kan_long.db}"
EVENTS_FILTERED="$OUT_DIR/earthquakes_world_mag80plus_real.RAW.csv"
FLOAT_MASTER_REAL="$OUT_DIR/master_world_m8plus_real_astrofmt_float.csv"
MASTER_REAL="$OUT_DIR/master_world_m8plus_real_astrofmt.csv"
MASTER="$OUT_DIR/master_with_usgs_core_astrofmt.csv"

cat > "$OUT_DIR/RUN_THIS_PIPELINE.sh" <<EOF
#!/usr/bin/env bash
cd "$(pwd)"
OUT_DIR="$OUT_DIR" \\
SRC_EVENTS="$SRC_EVENTS" \\
FORECAST_START="$FORECAST_START" FORECAST_END="$FORECAST_END" \\
SEEDS_SPEC="$SEEDS_SPEC" MAX_ITER="$MAX_ITER" JOBS="$JOBS" \\
KAN_PRESETS_RUN="$KAN_PRESETS_RUN" \\
./commands/run_japan_mag80_world_m8_neganchors_30d_kan_long.sh
EOF
chmod +x "$OUT_DIR/RUN_THIS_PIPELINE.sh"

cat > "$OUT_DIR/pipeline_notes.md" <<EOF
# Japan M8.0+ from Worldwide M8.0+ Negative Anchors

This run asks a Japan-only question: whether Japan has a magnitude >= ${MIN_MAG}
event during ${FORECAST_START} -> ${FORECAST_END}.

The master is intentionally built in two phases:

1. Build astronomy on the real worldwide M8.0+ event timeline. This gives
   the model the astronomical context around large non-Japan earthquakes too.
2. Post-edit the final master so only events inside the Japan box remain
   positive. Non-Japan event bins are converted to \`mag=0\` and
   \`depth=latitude=longitude=0\`, becoming negative anchors/noise.

Configuration:

- Master cadence: ${STEP_DAYS} days.
- Date semantics: each row date is the START of its ${STEP_DAYS}-day period.
- Japan box: lat ${JAPAN_LAT_MIN}..${JAPAN_LAT_MAX}, lon ${JAPAN_LON_MIN}..${JAPAN_LON_MAX}.
- Ephemerides: stable Earth-centered/geocentric JPL vectors from
  \`$STABLE_EPHEMERIDES_CSV\`.
- Training target: \`mag\`.
- Training features skip seismic columns: \`date,depth,latitude,longitude\`.
- Validation/target events: last ${TARGET_EVENT_COUNT} Japan-positive bins.
- Model family: KAN only, presets \`${KAN_PRESETS_RUN}\`, seeds \`${SEEDS_SPEC}\`,
  max_iter \`${MAX_ITER}\`, jobs \`${JOBS}\`.

Re-run command is stored in \`RUN_THIS_PIPELINE.sh\`.
EOF

echo "======================================================================"
echo " Japan M8.0+ 30d KAN with worldwide M8+ negative anchors"
echo " Output dir: $OUT_DIR"
echo " Forecast:   $FORECAST_START -> $FORECAST_END"
echo " Japan box:  lat $JAPAN_LAT_MIN..$JAPAN_LAT_MAX lon $JAPAN_LON_MIN..$JAPAN_LON_MAX"
echo " KAN:        presets=$KAN_PRESETS_RUN seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS"
echo " KAN quiet:  $KAN_QUIET"
echo "======================================================================"

echo "[1/5] Filter real worldwide mag >= $MIN_MAG events..."
"$PYTHON_BIN" "$FILTER_EVENTS_PY" \
  --input-csv "$SRC_EVENTS" \
  --output-csv "$EVENTS_FILTERED" \
  --manifest-json "$OUT_DIR/filtered_world_m8plus_events_manifest.json" \
  --min-mag "$MIN_MAG" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --title "real worldwide mag >= $MIN_MAG events before Japan-only masking"

echo "[2/5] Build 30d stable geocentric master from real worldwide events..."
"$PYTHON_BIN" "$BUILDER_PY" \
  --safe-ephemerides-csv "$STABLE_EPHEMERIDES_CSV" \
  --events-csv "$EVENTS_FILTERED" \
  --output-float-csv "$FLOAT_MASTER_REAL" \
  --manifest-json "$OUT_DIR/master_world_m8plus_real_astrofmt_manifest.json" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --step-days "$STEP_DAYS" \
  --moon-center "$MOON_CENTER" \
  --exclude-bodies "$EXCLUDE_BODIES" \
  --on-body-error "$ON_BODY_ERROR" \
  --auto-clip "$AUTO_CLIP" \
  --refplane "$REFPLANE"

echo "[3/5] Quantize astro features before Japan-only masking..."
"$PYTHON_BIN" "$QUANT_PY" \
  --input-csv "$FLOAT_MASTER_REAL" \
  --output-csv "$MASTER_REAL" \
  --bins "$QUANT_BINS"

echo "[4/5] Silence non-Japan M8+ bins in final training master..."
"$PYTHON_BIN" "$MASK_MASTER_PY" \
  --input-csv "$MASTER_REAL" \
  --output-csv "$MASTER" \
  --manifest-json "$OUT_DIR/japan_only_negative_anchor_mask_manifest.json" \
  --events-csv "$EVENTS_FILTERED" \
  --step-days "$STEP_DAYS" \
  --japan-lat-min "$JAPAN_LAT_MIN" \
  --japan-lat-max "$JAPAN_LAT_MAX" \
  --japan-lon-min "$JAPAN_LON_MIN" \
  --japan-lon-max "$JAPAN_LON_MAX" \
  --positive-threshold 0.1

echo "[5/5] Train KAN-only Japan monthly forecast..."
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
  --task "$MASTER" \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  --no-banks \
  --enable-kan \
  --kan-presets "$KAN_PRESETS_RUN" \
  --kan-device cpu \
  "${KAN_EXTRA_ARGS[@]}" \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 \
  --target-window-event-count "$TARGET_EVENT_COUNT" \
  --target-window-pre-records "$VALIDATION_PRE_RECORDS" \
  --target-window-post-records "$VALIDATION_POST_RECORDS" \
  --isolated-event-windows \
  --recent-validation-window \
  --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
  --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
  --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
  --recent-validation-weight 3.0 \
  --recent-validation-random-negatives "$RECENT_VALIDATION_RANDOM_NEGATIVES" \
  --recent-validation-random-seed "$RECENT_VALIDATION_RANDOM_SEED" \
  --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date "$FORECAST_END" \
  --forecast-trainset train2forecast \
  --final-eval-rank-power 1.0 \
  --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight 3.0 \
  --final-eval-best-fraction 0.50 \
  --final-eval-worst-fraction 0.0 \
  --final-eval-shape-power 0.8 \
  --readability-weight 0.30 \
  --readability-floor 0.25 \
  --seeds "$SEEDS_SPEC" \
  --max-iter "$MAX_ITER" \
  --jobs "$JOBS" \
  --best "$BEST_N" \
  --keep-best "$KEEP_BEST" \
  --keep-worst 0 \
  --no-invert-twin \
  --db "$DB_FILE" \
  --verbose \
  2>&1 | tee "$LOG_FILE"

echo ""
echo "======================================================================"
echo " Japan M8.0+ negative-anchor 30d KAN run ready"
echo " Root:     $OUT_DIR"
echo " Master:   $MASTER"
echo " Mask doc: $OUT_DIR/japan_only_negative_anchor_mask_manifest.json"
echo " Log:      $LOG_FILE"
echo " Re-run:   $OUT_DIR/RUN_THIS_PIPELINE.sh"
echo "======================================================================"

#!/usr/bin/env bash
# Worldwide M8.5+ monthly KAN forecast, May-Dec 2026.
#
# Scope:
#   - target: any real worldwide earthquake with mag >= 8.5
#   - frame: stable Earth-centered/geocentric JPL vectors
#   - cadence: 30 days; each row date is the START of the forecast/training period
#   - forecast: 2026-05-01 -> 2026-12-31
#   - model family: KAN only, deliberately long-ish CPU run
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_EVENTS="${SRC_EVENTS:-$ASTRO_ROOT/DB/WORLD-MAG8.5-1900-2025-09-30/earthquakes.RAW.csv}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/world-mag85plus-30d-geocentric-kan-long}"
STABLE_EPHEMERIDES_CSV="${STABLE_EPHEMERIDES_CSV:-$(pwd)/resources/japan_nankai_stable_geocentric_ephemerides.csv}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"

START_DATE="${START_DATE:-1900-01-01}"
END_DATE="${END_DATE:-2026-12-31}"
FORECAST_START="${FORECAST_START:-2026-05-01}"
FORECAST_END="${FORECAST_END:-2026-12-31}"
STEP_DAYS="${STEP_DAYS:-30}"
MIN_MAG="${MIN_MAG:-8.5}"
QUANT_BINS="${QUANT_BINS:-4}"

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
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-3}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-3}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-1}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-1}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-600}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-12}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-20260518}"

PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
BUILDER_PY="${BUILDER_PY:-$(pwd)/build_jpl_safe_360d_master.py}"
FILTER_EVENTS_PY="${FILTER_EVENTS_PY:-$(pwd)/filter_earthquake_events.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$SRC_EVENTS" ]] || { echo "[ERROR] SRC_EVENTS not found: $SRC_EVENTS" >&2; exit 1; }
[[ -f "$STABLE_EPHEMERIDES_CSV" ]] || { echo "[ERROR] STABLE_EPHEMERIDES_CSV not found: $STABLE_EPHEMERIDES_CSV" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] QUANT_PY not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
LOG_FILE="${LOG_FILE:-$OUT_DIR/world_mag85plus_30d_kan_long.log}"
DB_FILE="${DB_FILE:-$OUT_DIR/world_mag85plus_30d_kan_long.db}"
EVENTS_FILTERED="$OUT_DIR/earthquakes_world_mag85plus.RAW.csv"
FLOAT_MASTER="$OUT_DIR/master_with_usgs_core_astrofmt_float.csv"
MASTER="$OUT_DIR/master_with_usgs_core_astrofmt.csv"

cat > "$OUT_DIR/RUN_THIS_PIPELINE.sh" <<EOF
#!/usr/bin/env bash
cd "$(pwd)"
OUT_DIR="$OUT_DIR" \\
SRC_EVENTS="$SRC_EVENTS" \\
FORECAST_START="$FORECAST_START" FORECAST_END="$FORECAST_END" \\
SEEDS_SPEC="$SEEDS_SPEC" MAX_ITER="$MAX_ITER" JOBS="$JOBS" \\
KAN_PRESETS_RUN="$KAN_PRESETS_RUN" \\
./commands/run_world_mag85_30d_kan_long.sh
EOF
chmod +x "$OUT_DIR/RUN_THIS_PIPELINE.sh"

cat > "$OUT_DIR/pipeline_notes.md" <<EOF
# Worldwide M8.5+ 30d KAN Forecast

This run asks a global question: whether the Earth timeline contains one or
more worldwide earthquakes with magnitude >= ${MIN_MAG} during ${FORECAST_START}
-> ${FORECAST_END}.

- Master cadence: ${STEP_DAYS} days.
- Date semantics: each row date is the START of its ${STEP_DAYS}-day period.
- Spatial scope: planet Earth / worldwide, no Japan filter.
- Ephemerides: stable Earth-centered/geocentric JPL vectors from
  \`$STABLE_EPHEMERIDES_CSV\`.
- Training target: \`mag\`.
- Event encoding: the source list is filtered to mag >= ${MIN_MAG}; therefore
  \`mag > 0\` means a target event bin.
- Training features skip seismic columns: \`date,depth,latitude,longitude\`.
- Model family: KAN only, presets \`${KAN_PRESETS_RUN}\`, seeds \`${SEEDS_SPEC}\`,
  max_iter \`${MAX_ITER}\`, jobs \`${JOBS}\`.

Re-run command is stored in \`RUN_THIS_PIPELINE.sh\`.
EOF

echo "======================================================================"
echo " Worldwide M8.5+ 30d geocentric KAN forecast"
echo " Output dir: $OUT_DIR"
echo " Forecast:   $FORECAST_START -> $FORECAST_END"
echo " KAN:        presets=$KAN_PRESETS_RUN seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS"
echo " KAN quiet:  $KAN_QUIET"
echo "======================================================================"

echo "[1/4] Filter worldwide mag >= $MIN_MAG events..."
"$PYTHON_BIN" "$FILTER_EVENTS_PY" \
  --input-csv "$SRC_EVENTS" \
  --output-csv "$EVENTS_FILTERED" \
  --manifest-json "$OUT_DIR/filtered_events_manifest.json" \
  --min-mag "$MIN_MAG" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --title "worldwide mag >= $MIN_MAG events for 30d KAN forecast"

echo "[2/4] Build 30d stable geocentric master..."
"$PYTHON_BIN" "$BUILDER_PY" \
  --safe-ephemerides-csv "$STABLE_EPHEMERIDES_CSV" \
  --events-csv "$EVENTS_FILTERED" \
  --output-float-csv "$FLOAT_MASTER" \
  --manifest-json "$OUT_DIR/master_with_usgs_core_astrofmt_manifest.json" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --step-days "$STEP_DAYS" \
  --moon-center "$MOON_CENTER" \
  --exclude-bodies "$EXCLUDE_BODIES" \
  --on-body-error "$ON_BODY_ERROR" \
  --auto-clip "$AUTO_CLIP" \
  --refplane "$REFPLANE"

echo "[3/4] Quantize astro features..."
"$PYTHON_BIN" "$QUANT_PY" \
  --input-csv "$FLOAT_MASTER" \
  --output-csv "$MASTER" \
  --bins "$QUANT_BINS"

echo "[4/4] Train KAN-only monthly forecast..."
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
echo " Worldwide M8.5+ 30d KAN run ready"
echo " Root:    $OUT_DIR"
echo " Master:  $MASTER"
echo " Log:     $LOG_FILE"
echo " Re-run:  $OUT_DIR/RUN_THIS_PIPELINE.sh"
echo "======================================================================"

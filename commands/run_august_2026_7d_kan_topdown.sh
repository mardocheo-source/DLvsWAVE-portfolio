#!/usr/bin/env bash
# Top-down August 2026 pipeline:
# reusable solar-system master -> fast 7d timing KAN -> seismic-only history
# -> latitude/longitude KAN -> combined coordinates.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
SOURCE_MASTER="${SOURCE_MASTER:-/mnt/git0/git/repository/astro-USGS2/DB/world-mag85plus-7d-jul-aug-time-travel-ribbon-kan-xpu-1h/master_with_usgs_core_astrofmt.csv}"
OUT_DIR="${OUT_DIR:-$PWD/DB/2026-08-worldwide-m85-7d-kan-topdown}"
# The reusable weekly master is Wednesday-aligned. The 2026-07-29 slot covers
# August 1-4, so it must be included for complete August coverage.
FORECAST_START="${FORECAST_START:-2026-07-29}"
FORECAST_END="${FORECAST_END:-2026-08-31}"
EVENT_MAG_THRESHOLD="${EVENT_MAG_THRESHOLD:-0.1}"
STEP_DAYS="${STEP_DAYS:-7}"

RUN_TIMING="${RUN_TIMING:-1}"
RUN_LOCATION="${RUN_LOCATION:-1}"
TIMING_FORECAST_CSV="${TIMING_FORECAST_CSV:-}"
TIMING_VALIDATION_CSV="${TIMING_VALIDATION_CSV:-}"

KAN_DEVICE="${KAN_DEVICE:-auto}"
TIMING_KAN_PRESETS="${TIMING_KAN_PRESETS:-tiny}"
TIMING_SEEDS="${TIMING_SEEDS:-4,5,6,7}"
TIMING_MAX_ITER="${TIMING_MAX_ITER:-180}"
TIMING_JOBS="${TIMING_JOBS:-1}"
TIMING_BEST="${TIMING_BEST:-8}"
TIMING_KEEP_BEST="${TIMING_KEEP_BEST:-4}"

LOCATION_KAN_PRESETS="${LOCATION_KAN_PRESETS:-tiny}"
LOCATION_SEEDS="${LOCATION_SEEDS:-4,5,6,7}"
LOCATION_MAX_ITER="${LOCATION_MAX_ITER:-180}"
LOCATION_JOBS="${LOCATION_JOBS:-1}"
LOCATION_BEST="${LOCATION_BEST:-8}"
LOCATION_KEEP_BEST="${LOCATION_KEEP_BEST:-4}"
LOCATION_VALIDATION_EVENTS="${LOCATION_VALIDATION_EVENTS:-4}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python not executable: $PYTHON_BIN" >&2; exit 2; }
[[ -f "$SOURCE_MASTER" ]] || {
  echo "[ERROR] Reusable source master not found: $SOURCE_MASTER" >&2
  echo "Set SOURCE_MASTER to a 7-day astrofmt master covering August 2026." >&2
  exit 2
}

TIMING_DIR="$OUT_DIR/01_timing"
LOCATION_DIR="$OUT_DIR/02_location"
TIMING_MASTER="$TIMING_DIR/master_with_usgs_core_astrofmt.csv"
SEISMIC_MASTER="$LOCATION_DIR/seismic_history_with_forecast_grid.csv"
SEISMIC_MANIFEST="$LOCATION_DIR/seismic_history_with_forecast_grid_manifest.json"
FOCUS_JSON="$TIMING_DIR/timing_focus_window.json"
FOCUS_ENV="$TIMING_DIR/timing_focus_window.env"

mkdir -p "$TIMING_DIR" "$LOCATION_DIR"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$OUT_DIR/.matplotlib}"
mkdir -p "$MPLCONFIGDIR"
cp "$SOURCE_MASTER" "$TIMING_MASTER"

echo "======================================================================"
echo " August 2026 top-down 7d KAN forecast"
echo " L0 outcome:       timing first, then latitude/longitude"
echo " Reusable master:  $SOURCE_MASTER"
echo " Forecast:         $FORECAST_START -> $FORECAST_END"
echo " Cadence:          ${STEP_DAYS}d"
echo " August coverage:  slot starts Jul 29, Aug 5, 12, 19, 26"
echo " KAN device:       $KAN_DEVICE"
echo " Output:           $OUT_DIR"
echo "======================================================================"

find_latest_run_dir() {
  local base_dir="$1"
  local latest=""
  shopt -s nullglob
  local candidates=("$base_dir"/pulsar_train*_best_trials_*)
  shopt -u nullglob
  (( ${#candidates[@]} > 0 )) || return 1
  latest="$(printf '%s\n' "${candidates[@]}" | sort | tail -n 1)"
  [[ -d "$latest" ]] || return 1
  printf '%s\n' "$latest"
}

find_final_forecast() {
  local run_dir="$1"
  local found=""
  found="$(find "$run_dir" -type f -name '*__final_evaluation__forecast.csv' | sort | head -n 1)"
  [[ -n "$found" && -f "$found" ]] || return 1
  printf '%s\n' "$found"
}

if [[ "$RUN_TIMING" == "1" ]]; then
  echo ""
  echo "[L1 timing] KAN-only on the complete 7d astronomical grid."
  echo "            Seismic coordinates are excluded from timing features."
  export PYTHONUNBUFFERED=1
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
  export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

  "$PYTHON_BIN" -u cli.py train \
    --task "$TIMING_MASTER" \
    --target_cols_list mag \
    --skip_cols_list date,depth,latitude,longitude \
    --no-banks \
    --enable-kan \
    --kan-presets "$TIMING_KAN_PRESETS" \
    --kan-device "$KAN_DEVICE" \
    --kan-quiet \
    --metric-mode event \
    --metric-target-threshold "$EVENT_MAG_THRESHOLD" \
    --metric-prediction-threshold 0.5 \
    --event-score-mode isolation \
    --target-window-threshold "$EVENT_MAG_THRESHOLD" \
    --target-window-event-count 3 \
    --target-window-pre-records 4 \
    --target-window-post-records 4 \
    --isolated-event-windows \
    --recent-validation-window \
    --recent-validation-event-count 3 \
    --recent-validation-pre-records 4 \
    --recent-validation-post-records 4 \
    --recent-validation-random-negatives 12 \
    --recent-validation-random-seed 20260728 \
    --validation-max-lookback-records 9000 \
    --train-recency-weight exp \
    --train-recency-strength 1.0 \
    --train-event-weight auto \
    --train-max-event-weight 8.0 \
    --forecast-start-date "$FORECAST_START" \
    --forecast-end-date "$FORECAST_END" \
    --forecast-trainset train2forecast \
    --final-eval-best-fraction 0.5 \
    --final-eval-worst-fraction 0.0 \
    --final-eval-shape-power 0.8 \
    --seeds "$TIMING_SEEDS" \
    --max-iter "$TIMING_MAX_ITER" \
    --jobs "$TIMING_JOBS" \
    --best "$TIMING_BEST" \
    --keep-best "$TIMING_KEEP_BEST" \
    --keep-worst 0 \
    --no-invert-twin \
    --no-export-best-by-bank \
    --no-collage \
    --db "$TIMING_DIR/timing.db" \
    --verbose \
    2>&1 | tee "$TIMING_DIR/timing.log"

  TIMING_RUN_DIR="$(find_latest_run_dir "$TIMING_DIR")" || {
    echo "[ERROR] timing run directory not found under $TIMING_DIR" >&2
    exit 1
  }
  TIMING_FORECAST_CSV="$(find_final_forecast "$TIMING_RUN_DIR")" || {
    echo "[ERROR] final timing forecast not found under $TIMING_RUN_DIR" >&2
    exit 1
  }
elif [[ -z "$TIMING_FORECAST_CSV" ]]; then
  TIMING_RUN_DIR="$(find_latest_run_dir "$TIMING_DIR")" || {
    echo "[ERROR] RUN_TIMING=0 requires TIMING_FORECAST_CSV or an existing timing run." >&2
    exit 2
  }
  TIMING_FORECAST_CSV="$(find_final_forecast "$TIMING_RUN_DIR")" || {
    echo "[ERROR] existing timing forecast not found under $TIMING_RUN_DIR" >&2
    exit 2
  }
fi

[[ -f "$TIMING_FORECAST_CSV" ]] || {
  echo "[ERROR] timing forecast CSV not found: $TIMING_FORECAST_CSV" >&2
  exit 2
}
if [[ -z "$TIMING_VALIDATION_CSV" ]]; then
  TIMING_VALIDATION_CSV="${TIMING_FORECAST_CSV/__forecast.csv/__validation.csv}"
fi
[[ -f "$TIMING_VALIDATION_CSV" ]] || {
  echo "[ERROR] timing validation CSV not found: $TIMING_VALIDATION_CSV" >&2
  exit 2
}

echo ""
echo "[L2 focus] Rank August slots and inherit the strongest 7-day window."
"$PYTHON_BIN" select_forecast_focus_window.py \
  --forecast-csv "$TIMING_FORECAST_CSV" \
  --output-json "$FOCUS_JSON" \
  --output-env "$FOCUS_ENV" \
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date "$FORECAST_END" \
  --cadence-days "$STEP_DAYS"
# Generated locally by select_forecast_focus_window.py; contains four scalar assignments.
source "$FOCUS_ENV"

echo ""
echo "[L3 data] Derive one reusable location master."
echo "          Historical rows: earthquakes only; future rows: projection grid only."
"$PYTHON_BIN" prepare_seismic_projection_master.py \
  --input-csv "$TIMING_MASTER" \
  --output-csv "$SEISMIC_MASTER" \
  --manifest-json "$SEISMIC_MANIFEST" \
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date "$FORECAST_END" \
  --event-mag-threshold "$EVENT_MAG_THRESHOLD"

if [[ "$RUN_LOCATION" == "1" ]]; then
  for target in latitude longitude; do
    target_dir="$LOCATION_DIR/$target"
    echo ""
    echo "[L4 location/$target] KAN regression using the shared seismic-history master."
    env \
      MASTER_CSV="$SEISMIC_MASTER" \
      OUT_DIR="$target_dir" \
      LOCATION_TARGET="$target" \
      LOCATION_MODE=analog \
      EVENT_MAG_THRESHOLD="$EVENT_MAG_THRESHOLD" \
      FORECAST_START="$FORECAST_START" \
      FORECAST_END="$FORECAST_END" \
      FOCUS_START="$FOCUS_START" \
      FOCUS_END="$FOCUS_END" \
      VALIDATION_EVENT_COUNT="$LOCATION_VALIDATION_EVENTS" \
      KAN_PRESETS_RUN="$LOCATION_KAN_PRESETS" \
      KAN_DEVICE="$KAN_DEVICE" \
      KAN_QUIET=1 \
      SEEDS_SPEC="$LOCATION_SEEDS" \
      MAX_ITER="$LOCATION_MAX_ITER" \
      JOBS="$LOCATION_JOBS" \
      BEST_N="$LOCATION_BEST" \
      KEEP_BEST="$LOCATION_KEEP_BEST" \
      ENABLE_KAN=1 \
      ENABLE_LCS=0 \
      ENABLE_LCS_HYBRID=0 \
      PYTHON_BIN="$PYTHON_BIN" \
      "$PWD/commands/run_location_forecast_from_master.sh"
  done

  echo ""
  echo "[L5 output] Combine independent latitude/longitude estimates."
  "$PYTHON_BIN" combine_location_coordinates.py \
    --latitude-csv "$LOCATION_DIR/latitude/location_report/location_latitude_analog_forecast.csv" \
    --longitude-csv "$LOCATION_DIR/longitude/location_report/location_longitude_analog_forecast.csv" \
    --output-csv "$LOCATION_DIR/august_2026_location_coordinates.csv" \
    --output-json "$LOCATION_DIR/august_2026_location_coordinates.json" \
    --output-md "$LOCATION_DIR/august_2026_location_coordinates.md"

  echo ""
  echo "[L6 quality] Create combined timing/location forecast and validation dashboard."
  DASHBOARD_DIR="$OUT_DIR/03_dashboard"
  mkdir -p "$DASHBOARD_DIR"
  "$PYTHON_BIN" topdown_forecast_validation_dashboard.py \
    --timing-validation-csv "$TIMING_VALIDATION_CSV" \
    --timing-forecast-csv "$TIMING_FORECAST_CSV" \
    --latitude-validation-csv "$LOCATION_DIR/latitude/location_report/location_latitude_analog_forecast__validation_location_scale.csv" \
    --latitude-forecast-csv "$LOCATION_DIR/latitude/location_report/location_latitude_analog_forecast.csv" \
    --longitude-validation-csv "$LOCATION_DIR/longitude/location_report/location_longitude_analog_forecast__validation_location_scale.csv" \
    --longitude-forecast-csv "$LOCATION_DIR/longitude/location_report/location_longitude_analog_forecast.csv" \
    --forecast-start-date "$FORECAST_START" \
    --forecast-end-date "$FORECAST_END" \
    --timing-threshold 0.5 \
    --output-png "$DASHBOARD_DIR/topdown_forecast_validation_dashboard.png" \
    --output-json "$DASHBOARD_DIR/topdown_forecast_validation_dashboard.json" \
    --output-md "$DASHBOARD_DIR/topdown_forecast_validation_dashboard.md"
fi

{
  echo "# August 2026 7d KAN top-down run"
  echo ""
  echo "- reusable source master: \`$SOURCE_MASTER\`"
  echo "- timing forecast: \`$TIMING_FORECAST_CSV\`"
  echo "- timing validation: \`$TIMING_VALIDATION_CSV\`"
  echo "- selected focus: \`$FOCUS_START -> $FOCUS_END\`"
  echo "- timing peak score: \`$TIMING_PEAK_SCORE\`"
  echo "- seismic-history projection master: \`$SEISMIC_MASTER\`"
  echo "- seismic master manifest: \`$SEISMIC_MANIFEST\`"
  echo "- location stage executed: \`$RUN_LOCATION\`"
  if [[ "$RUN_LOCATION" == "1" ]]; then
    echo "- forecast/validation dashboard: \`$OUT_DIR/03_dashboard/topdown_forecast_validation_dashboard.png\`"
  fi
  echo ""
  echo "The source master is copied, never modified. The location master removes all "
  echo "historical non-earthquake rows and retains future rows only for astronomical projection."
} > "$OUT_DIR/run_manifest.md"

echo ""
echo "======================================================================"
echo " Top-down pipeline ready"
echo " Focus:          $FOCUS_START -> $FOCUS_END"
echo " Timing score:   $TIMING_PEAK_SCORE"
echo " Seismic master: $SEISMIC_MASTER"
echo " Manifest:       $OUT_DIR/run_manifest.md"
if [[ "$RUN_LOCATION" == "1" ]]; then
  echo " Coordinates:    $LOCATION_DIR/august_2026_location_coordinates.csv"
  echo " Dashboard:      $OUT_DIR/03_dashboard/topdown_forecast_validation_dashboard.png"
fi
echo "======================================================================"

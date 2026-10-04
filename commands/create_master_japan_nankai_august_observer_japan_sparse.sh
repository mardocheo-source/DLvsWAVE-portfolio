#!/usr/bin/env bash
# Create Japan/Nankai sparse observer-frame master:
#   - configurable STEP_DAYS cadence
#   - only ±10 days around historical events by default
#   - plus forecast grid 2026-08-01 -> 2026-08-30
#   - supports vertical/horizontal auto-clip from build_jpl_observer_360d_master.py
set -euo pipefail

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
SAFE_EPHEMERIDES_CSV="${SAFE_EPHEMERIDES_CSV:-$SRC_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv}"
PYTHON_BIN="${PYTHON_BIN:-$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python}"

START_DATE="${START_DATE:-1498-01-01}"
END_DATE="${END_DATE:-2035-12-31}"
FORECAST_START="${FORECAST_START:-2026-08-01}"
FORECAST_END="${FORECAST_END:-2026-08-30}"
STEP_DAYS="${STEP_DAYS:-3}"
STEP_TAG="${STEP_DAYS}d"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-${STEP_TAG}-august-observer-japan-sparse}"
EVENT_WINDOW_DAYS_BEFORE="${EVENT_WINDOW_DAYS_BEFORE:-10}"
EVENT_WINDOW_DAYS_AFTER="${EVENT_WINDOW_DAYS_AFTER:-10}"
QUANT_BINS="${QUANT_BINS:-4}"

OBSERVER_LAT="${OBSERVER_LAT:-34.5}"
OBSERVER_LON="${OBSERVER_LON:-137.5}"
OBSERVER_ELEVATION="${OBSERVER_ELEVATION:-0}"
OBSERVER_ALIAS="${OBSERVER_ALIAS:-japan_center}"
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-1,2,3,4,13,19,31,43}"
EXCLUDE_BODIES="${EXCLUDE_BODIES:-earth}"
ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"
AUTO_CLIP="${AUTO_CLIP:-vertical}"

BUILDER_PY="${BUILDER_PY:-$(cd "$(dirname "$0")/.." && pwd)/build_jpl_observer_360d_master.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$EVENTS_CSV" ]] || { echo "[ERROR] EVENTS_CSV not found: $EVENTS_CSV" >&2; exit 1; }
[[ -f "$SAFE_EPHEMERIDES_CSV" ]] || { echo "[ERROR] SAFE_EPHEMERIDES_CSV not found: $SAFE_EPHEMERIDES_CSV" >&2; exit 1; }
[[ -f "$BUILDER_PY" ]] || { echo "[ERROR] BUILDER_PY not found: $BUILDER_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] QUANT_PY not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
cp "$EVENTS_CSV" "$OUT_DIR/earthquakes.RAW.csv"
cp "$SAFE_EPHEMERIDES_CSV" "$OUT_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv"

echo "======================================================================"
echo " Japan/Nankai sparse ${STEP_TAG} August observer master"
echo " Output dir:       $OUT_DIR"
echo " Date coverage:    $START_DATE -> $END_DATE"
echo " Event meat:       -${EVENT_WINDOW_DAYS_BEFORE}d / +${EVENT_WINDOW_DAYS_AFTER}d"
echo " Forecast:         $FORECAST_START -> $FORECAST_END"
echo " Step interval:    ${STEP_DAYS}d"
echo " Observer:         $OBSERVER_ALIAS lat=$OBSERVER_LAT lon=$OBSERVER_LON elev=${OBSERVER_ELEVATION}km"
echo " Auto clip:        $AUTO_CLIP"
echo "======================================================================"

"$PYTHON_BIN" "$BUILDER_PY" \
    --safe-ephemerides-csv "$OUT_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv" \
    --events-csv "$OUT_DIR/earthquakes.RAW.csv" \
    --output-float-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --manifest-json "$OUT_DIR/master_with_usgs_core_astrofmt_manifest.json" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --step-days "$STEP_DAYS" \
    --sparse-event-windows \
    --event-window-days-before "$EVENT_WINDOW_DAYS_BEFORE" \
    --event-window-days-after "$EVENT_WINDOW_DAYS_AFTER" \
    --forecast-start-date "$FORECAST_START" \
    --forecast-end-date "$FORECAST_END" \
    --observer-lat "$OBSERVER_LAT" \
    --observer-lon "$OBSERVER_LON" \
    --observer-elevation "$OBSERVER_ELEVATION" \
    --observer-alias "$OBSERVER_ALIAS" \
    --ephemerides-fields "$EPHEMERIDES_FIELDS" \
    --exclude-bodies "$EXCLUDE_BODIES" \
    --on-body-error "$ON_BODY_ERROR" \
    --auto-clip "$AUTO_CLIP"

MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
"$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --output-csv "$MASTER_OUT" \
    --bins "$QUANT_BINS"

echo "Master ready: $MASTER_OUT"
echo "Rows:         $(wc -l < "$MASTER_OUT")"
echo "First date:   $(awk -F',' 'NR==2{print $1}' "$MASTER_OUT")"
echo "Last date:    $(awk -F',' 'END{print $1}' "$MASTER_OUT")"

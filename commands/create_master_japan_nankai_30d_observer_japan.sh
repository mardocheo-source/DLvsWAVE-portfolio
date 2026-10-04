#!/usr/bin/env bash
# Create Japan/Nankai historical master at 30d resolution using JPL Horizons
# topocentric/observer ephemerides from the approximate center of Japan.
#
# Semantics:
#   - one record is one 30-day period
#   - the date column is the START of that period
#   - astronomical features are observer-frame ephemerides from:
#       lat=34.5, lon=137.5, elevation=0 km, alias=japan_center
#   - seismic target columns are assigned with left-bin logic:
#       event_date in [record_date, next_record_date) -> that record
set -euo pipefail

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-30d-observer-japan-center}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
SAFE_EPHEMERIDES_CSV="${SAFE_EPHEMERIDES_CSV:-$SRC_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -x "$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python" ]]; then
        PYTHON_BIN="$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi

START_DATE="${START_DATE:-1498-01-01}"
END_DATE="${END_DATE:-2035-12-31}"
STEP_DAYS="${STEP_DAYS:-30}"
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

[[ -d "$ASTRO_ROOT" ]] || { echo "[ERROR] ASTRO_ROOT not found: $ASTRO_ROOT" >&2; exit 1; }
[[ -f "$EVENTS_CSV" ]] || { echo "[ERROR] EVENTS_CSV not found: $EVENTS_CSV" >&2; exit 1; }
[[ -f "$SAFE_EPHEMERIDES_CSV" ]] || { echo "[ERROR] SAFE_EPHEMERIDES_CSV not found: $SAFE_EPHEMERIDES_CSV" >&2; exit 1; }
[[ -f "$BUILDER_PY" ]] || { echo "[ERROR] Script not found: $BUILDER_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] Script not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
cp "$EVENTS_CSV" "$OUT_DIR/earthquakes.RAW.csv"
cp "$SAFE_EPHEMERIDES_CSV" "$OUT_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv"

echo "======================================================================"
echo " Japan/Nankai 30d master - observer frame"
echo " Output dir:       $OUT_DIR"
echo " Events CSV:       $EVENTS_CSV"
echo " Safe JPL notes:   $SAFE_EPHEMERIDES_CSV"
echo " Date coverage:    $START_DATE -> $END_DATE"
echo " Step interval:    ${STEP_DAYS}d"
echo " Record meaning:   date is period START; one row = one ${STEP_DAYS}d period"
echo " JPL mode:         topocentric ephemerides from terrestrial observer"
echo " Observer:         $OBSERVER_ALIAS lat=$OBSERVER_LAT lon=$OBSERVER_LON elev=${OBSERVER_ELEVATION}km"
echo " Ephem fields:     $EPHEMERIDES_FIELDS"
echo " Exclude bodies:   ${EXCLUDE_BODIES:-none}"
echo " On body error:    $ON_BODY_ERROR"
echo " Auto clip:        $AUTO_CLIP"
echo "======================================================================"

echo ""
echo "[1/2] JPL observer ephemerides master at ${STEP_DAYS}d cadence..."
"$PYTHON_BIN" "$BUILDER_PY" \
    --safe-ephemerides-csv "$OUT_DIR/jpl_safe_ephemerides_for_japan_historical_model.csv" \
    --events-csv "$OUT_DIR/earthquakes.RAW.csv" \
    --output-float-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --manifest-json "$OUT_DIR/master_with_usgs_core_astrofmt_manifest.json" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --step-days "$STEP_DAYS" \
    --observer-lat "$OBSERVER_LAT" \
    --observer-lon "$OBSERVER_LON" \
    --observer-elevation "$OBSERVER_ELEVATION" \
    --observer-alias "$OBSERVER_ALIAS" \
    --ephemerides-fields "$EPHEMERIDES_FIELDS" \
    --exclude-bodies "$EXCLUDE_BODIES" \
    --on-body-error "$ON_BODY_ERROR" \
    --auto-clip "$AUTO_CLIP"

MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
echo ""
echo "[2/2] Quantize astro features (bins=$QUANT_BINS) -> $MASTER_OUT"
"$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --output-csv "$MASTER_OUT" \
    --bins "$QUANT_BINS"

echo ""
echo "======================================================================"
echo " Observer 30d master ready: $MASTER_OUT"
echo " Rows:                      $(wc -l < "$MASTER_OUT")"
echo " Columns:                   $(head -1 "$MASTER_OUT" | tr ',' '\n' | wc -l)"
echo " First date:                $(awk -F',' 'NR==2{print $1}' "$MASTER_OUT")"
echo " Last date:                 $(awk -F',' 'END{print $1}' "$MASTER_OUT")"
echo " Event bins:                $(awk -F',' 'NR>1 && $2+0>0{n++} END{print n+0}' "$MASTER_OUT")"
echo " Observer:                  $OBSERVER_ALIAS ($OBSERVER_LAT,$OBSERVER_LON,$OBSERVER_ELEVATION km)"
echo "======================================================================"

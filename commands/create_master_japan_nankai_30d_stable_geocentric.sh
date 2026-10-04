#!/usr/bin/env bash
# Create Japan/Nankai 30d master with stable Earth-centered JPL vectors.
#
# This variant intentionally avoids topocentric apparent coordinates and fragile
# small-body/satellite ephemerides for a 1498+ historical model.
set -euo pipefail

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-30d-stable-geocentric}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
WORLD_NEGATIVE_EVENTS_CSV="${WORLD_NEGATIVE_EVENTS_CSV:-$ASTRO_ROOT/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv}"
STABLE_EPHEMERIDES_CSV="${STABLE_EPHEMERIDES_CSV:-$(cd "$(dirname "$0")/.." && pwd)/resources/japan_nankai_stable_geocentric_ephemerides.csv}"
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
MOON_CENTER="${MOON_CENTER:-earth}"
EXCLUDE_BODIES="${EXCLUDE_BODIES:-}"
ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"
AUTO_CLIP="${AUTO_CLIP:-vertical}"
REFPLANE="${REFPLANE:-earth}"
AUGMENT_NEGATIVE_EVENTS="${AUGMENT_NEGATIVE_EVENTS:-1}"
NEGATIVE_MIN_MAG="${NEGATIVE_MIN_MAG:-8.0}"
NEGATIVE_MAX_EVENTS="${NEGATIVE_MAX_EVENTS:-48}"
NEGATIVE_DEDUPE_DAYS="${NEGATIVE_DEDUPE_DAYS:-30}"
NEGATIVE_JAPAN_LAT_MIN="${NEGATIVE_JAPAN_LAT_MIN:-28}"
NEGATIVE_JAPAN_LAT_MAX="${NEGATIVE_JAPAN_LAT_MAX:-44}"
NEGATIVE_JAPAN_LON_MIN="${NEGATIVE_JAPAN_LON_MIN:-128}"
NEGATIVE_JAPAN_LON_MAX="${NEGATIVE_JAPAN_LON_MAX:-147}"

BUILDER_PY="${BUILDER_PY:-$(cd "$(dirname "$0")/.." && pwd)/build_jpl_safe_360d_master.py}"
NEGATIVE_EVENTS_BUILDER_PY="${NEGATIVE_EVENTS_BUILDER_PY:-$(cd "$(dirname "$0")/.." && pwd)/make_japan_nankai_negative_anchor_events.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"

[[ -d "$ASTRO_ROOT" ]] || { echo "[ERROR] ASTRO_ROOT not found: $ASTRO_ROOT" >&2; exit 1; }
[[ -f "$EVENTS_CSV" ]] || { echo "[ERROR] EVENTS_CSV not found: $EVENTS_CSV" >&2; exit 1; }
[[ -f "$STABLE_EPHEMERIDES_CSV" ]] || { echo "[ERROR] STABLE_EPHEMERIDES_CSV not found: $STABLE_EPHEMERIDES_CSV" >&2; exit 1; }
[[ -f "$BUILDER_PY" ]] || { echo "[ERROR] Script not found: $BUILDER_PY" >&2; exit 1; }
[[ -f "$NEGATIVE_EVENTS_BUILDER_PY" ]] || { echo "[ERROR] Script not found: $NEGATIVE_EVENTS_BUILDER_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] Script not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR"
cp "$EVENTS_CSV" "$OUT_DIR/earthquakes_japan_positive.RAW.csv"
cp "$STABLE_EPHEMERIDES_CSV" "$OUT_DIR/jpl_stable_geocentric_ephemerides.csv"

MASTER_EVENTS_CSV="$OUT_DIR/earthquakes.RAW.csv"
if [[ "$AUGMENT_NEGATIVE_EVENTS" == "1" || "$AUGMENT_NEGATIVE_EVENTS" == "true" ]]; then
    [[ -f "$WORLD_NEGATIVE_EVENTS_CSV" ]] || { echo "[ERROR] WORLD_NEGATIVE_EVENTS_CSV not found: $WORLD_NEGATIVE_EVENTS_CSV" >&2; exit 1; }
    cp "$WORLD_NEGATIVE_EVENTS_CSV" "$OUT_DIR/earthquakes_global_negative_anchor_source.RAW.csv"
    echo "[0/2] Build Japan-positive + global non-Japan M8+ negative-anchor event list..."
    "$PYTHON_BIN" "$NEGATIVE_EVENTS_BUILDER_PY" \
        --japan-events-csv "$EVENTS_CSV" \
        --world-events-csv "$WORLD_NEGATIVE_EVENTS_CSV" \
        --output-csv "$MASTER_EVENTS_CSV" \
        --manifest-json "$OUT_DIR/negative_anchor_events_manifest.json" \
        --min-mag "$NEGATIVE_MIN_MAG" \
        --max-negative-events "$NEGATIVE_MAX_EVENTS" \
        --dedupe-days "$NEGATIVE_DEDUPE_DAYS" \
        --japan-lat-min "$NEGATIVE_JAPAN_LAT_MIN" \
        --japan-lat-max "$NEGATIVE_JAPAN_LAT_MAX" \
        --japan-lon-min "$NEGATIVE_JAPAN_LON_MIN" \
        --japan-lon-max "$NEGATIVE_JAPAN_LON_MAX"
else
    cp "$EVENTS_CSV" "$MASTER_EVENTS_CSV"
fi

echo "======================================================================"
echo " Japan/Nankai 30d master - stable geocentric vectors"
echo " Output dir:      $OUT_DIR"
echo " Events CSV:      $MASTER_EVENTS_CSV"
echo " Japan positives: $EVENTS_CSV"
echo " Neg anchors:     ${AUGMENT_NEGATIVE_EVENTS} (world=$WORLD_NEGATIVE_EVENTS_CSV, min_mag=$NEGATIVE_MIN_MAG, max=$NEGATIVE_MAX_EVENTS)"
echo " Japan bbox:      lat ${NEGATIVE_JAPAN_LAT_MIN}..${NEGATIVE_JAPAN_LAT_MAX}, lon ${NEGATIVE_JAPAN_LON_MIN}..${NEGATIVE_JAPAN_LON_MAX}"
echo " Stable JPL CSV:  $STABLE_EPHEMERIDES_CSV"
echo " Date coverage:   $START_DATE -> $END_DATE"
echo " Step interval:   ${STEP_DAYS}d"
echo " Record meaning:  date is period START; one row = one ${STEP_DAYS}d period"
echo " JPL mode:        geometric vectors, ICRF/J2000, Earth center @399"
echo " Refplane:        $REFPLANE"
echo " Moon center:     $MOON_CENTER"
echo " Exclude bodies:  ${EXCLUDE_BODIES:-none}"
echo " On body error:   $ON_BODY_ERROR"
echo " Auto clip:       $AUTO_CLIP"
echo "======================================================================"

echo ""
echo "[1/2] JPL stable geocentric vectors at ${STEP_DAYS}d cadence..."
"$PYTHON_BIN" "$BUILDER_PY" \
    --safe-ephemerides-csv "$OUT_DIR/jpl_stable_geocentric_ephemerides.csv" \
    --events-csv "$MASTER_EVENTS_CSV" \
    --output-float-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --manifest-json "$OUT_DIR/master_with_usgs_core_astrofmt_manifest.json" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --step-days "$STEP_DAYS" \
    --moon-center "$MOON_CENTER" \
    --exclude-bodies "$EXCLUDE_BODIES" \
    --on-body-error "$ON_BODY_ERROR" \
    --auto-clip "$AUTO_CLIP" \
    --refplane "$REFPLANE"

MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
echo ""
echo "[2/2] Quantize astro features (bins=$QUANT_BINS) -> $MASTER_OUT"
"$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --output-csv "$MASTER_OUT" \
    --bins "$QUANT_BINS"

echo ""
echo "======================================================================"
echo " Stable geocentric 30d master ready: $MASTER_OUT"
echo " Rows:                            $(wc -l < "$MASTER_OUT")"
echo " Columns:                         $(head -1 "$MASTER_OUT" | tr ',' '\n' | wc -l)"
echo " First date:                      $(awk -F',' 'NR==2{print $1}' "$MASTER_OUT")"
echo " Last date:                       $(awk -F',' 'END{print $1}' "$MASTER_OUT")"
echo " Event bins:                      $(awk -F',' 'NR>1 && $2+0>0{n++} END{print n+0}' "$MASTER_OUT")"
echo "======================================================================"

#!/usr/bin/env bash
# Create a Japan/Nankai 7d diagnostic master using the legacy nasaDb.py
# fullAstroJapan ephemerides set plus global non-Japan M8+ negative anchors.
set -euo pipefail

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_DIR="${SRC_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-historical-events-search}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-nankai-big-one-7d-fullastrojapan-neganchors}"
EVENTS_CSV="${EVENTS_CSV:-$SRC_DIR/earthquakes.RAW.csv}"
WORLD_NEGATIVE_EVENTS_CSV="${WORLD_NEGATIVE_EVENTS_CSV:-$ASTRO_ROOT/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -x "$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python" ]]; then
        PYTHON_BIN="$(cd "$(dirname "$0")/.." && pwd)/.venv/bin/python"
    else
        PYTHON_BIN="python3"
    fi
fi

# Horizontal/full strategy: keep the richer fullAstroJapan body set, but start
# in the modern instrumented era instead of forcing fragile 1498+ ephemerides.
START_DATE="${START_DATE:-1904-01-01}"
END_DATE="${END_DATE:-2026-12-31}"
FORECAST_CONTEXT_START="${FORECAST_CONTEXT_START:-2026-07-01}"
FORECAST_CONTEXT_END="${FORECAST_CONTEXT_END:-2026-09-30}"

STEP_INTERVAL="${STEP_INTERVAL:-7d}"
TIME_BEFORE="${TIME_BEFORE:-42d}"
TIME_AFTER="${TIME_AFTER:-42d}"
NASA_PLACE="${NASA_PLACE:-fullAstroJapan}"
OBSERVER_GEO="${OBSERVER_GEO:-34.5,137.5,0,japan_center}"
MAX_WORKERS="${MAX_WORKERS:-4}"

QUANT_BINS="${QUANT_BINS:-4}"
AUGMENT_NEGATIVE_EVENTS="${AUGMENT_NEGATIVE_EVENTS:-1}"
NEGATIVE_MIN_MAG="${NEGATIVE_MIN_MAG:-8.0}"
NEGATIVE_MAX_EVENTS="${NEGATIVE_MAX_EVENTS:-48}"
NEGATIVE_DEDUPE_DAYS="${NEGATIVE_DEDUPE_DAYS:-30}"
NEGATIVE_JAPAN_LAT_MIN="${NEGATIVE_JAPAN_LAT_MIN:-28}"
NEGATIVE_JAPAN_LAT_MAX="${NEGATIVE_JAPAN_LAT_MAX:-44}"
NEGATIVE_JAPAN_LON_MIN="${NEGATIVE_JAPAN_LON_MIN:-128}"
NEGATIVE_JAPAN_LON_MAX="${NEGATIVE_JAPAN_LON_MAX:-147}"

RANDOM_BACKGROUND="${RANDOM_BACKGROUND:-1460d}"
RANDOM_EVENT_WINDOW="${RANDOM_EVENT_WINDOW:-90d}"
RANDOM_EVENT_COUNT="${RANDOM_EVENT_COUNT:-8}"
QUIET_WINDOW_RADIUS="${QUIET_WINDOW_RADIUS:-7d}"

NEGATIVE_EVENTS_BUILDER_PY="${NEGATIVE_EVENTS_BUILDER_PY:-$(cd "$(dirname "$0")/.." && pwd)/make_japan_nankai_negative_anchor_events.py}"
SANITIZE_PY="${SANITIZE_PY:-$(cd "$(dirname "$0")/.." && pwd)/sanitize_numeric_master.py}"
ADD_USGS_PY="${ADD_USGS_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/add_usgs_core_columns_to_master.py}"
CONV_PY="${CONV_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/convert_astro_columns_to_standard.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"

[[ -d "$ASTRO_ROOT" ]] || { echo "[ERROR] ASTRO_ROOT not found: $ASTRO_ROOT" >&2; exit 1; }
[[ -f "$ASTRO_ROOT/nasaDb.py" ]] || { echo "[ERROR] nasaDb.py not found in $ASTRO_ROOT" >&2; exit 1; }
[[ -f "$EVENTS_CSV" ]] || { echo "[ERROR] EVENTS_CSV not found: $EVENTS_CSV" >&2; exit 1; }
[[ -f "$NEGATIVE_EVENTS_BUILDER_PY" ]] || { echo "[ERROR] Script not found: $NEGATIVE_EVENTS_BUILDER_PY" >&2; exit 1; }
[[ -f "$SANITIZE_PY" ]] || { echo "[ERROR] Script not found: $SANITIZE_PY" >&2; exit 1; }
[[ -f "$ADD_USGS_PY" ]] || { echo "[ERROR] Script not found: $ADD_USGS_PY" >&2; exit 1; }
[[ -f "$CONV_PY" ]] || { echo "[ERROR] Script not found: $CONV_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] Script not found: $QUANT_PY" >&2; exit 1; }

mkdir -p "$OUT_DIR" "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"
cp "$EVENTS_CSV" "$OUT_DIR/earthquakes_japan_positive_source.RAW.csv"

MASTER_EVENTS_CSV="$OUT_DIR/earthquakes.RAW.csv"
if [[ "$AUGMENT_NEGATIVE_EVENTS" == "1" || "$AUGMENT_NEGATIVE_EVENTS" == "true" ]]; then
    [[ -f "$WORLD_NEGATIVE_EVENTS_CSV" ]] || { echo "[ERROR] WORLD_NEGATIVE_EVENTS_CSV not found: $WORLD_NEGATIVE_EVENTS_CSV" >&2; exit 1; }
    cp "$WORLD_NEGATIVE_EVENTS_CSV" "$OUT_DIR/earthquakes_global_negative_anchor_source.RAW.csv"
    echo "[0/4] Build 1904+ Japan positives + global non-Japan M8+ negative-anchor event list..."
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
        --japan-lon-max "$NEGATIVE_JAPAN_LON_MAX" \
        --start-date "$START_DATE" \
        --end-date "$END_DATE"
else
    cp "$EVENTS_CSV" "$MASTER_EVENTS_CSV"
fi

echo "======================================================================"
echo " Japan/Nankai 7d master - nasaDb fullAstroJapan + negative anchors"
echo " Output dir:       $OUT_DIR"
echo " Events CSV:       $MASTER_EVENTS_CSV"
echo " Date coverage:    $START_DATE -> $END_DATE"
echo " Forecast context: $FORECAST_CONTEXT_START -> $FORECAST_CONTEXT_END"
echo " Step interval:    $STEP_INTERVAL"
echo " Event window:     before=$TIME_BEFORE after=$TIME_AFTER"
echo " nasaDb place:     $NASA_PLACE"
echo " Observer geo:     ${OBSERVER_GEO:-nasaDb preset default}"
echo " Neg anchors:      enabled=$AUGMENT_NEGATIVE_EVENTS min_mag=$NEGATIVE_MIN_MAG max=$NEGATIVE_MAX_EVENTS"
echo " Random context:   background=$RANDOM_BACKGROUND event_window=$RANDOM_EVENT_WINDOW event_count=$RANDOM_EVENT_COUNT"
echo "======================================================================"

NASA_ARGS=(
    "$ASTRO_ROOT/nasaDb.py"
    --csv_file "$MASTER_EVENTS_CSV"
    --datetime_column time
    --time_before "$TIME_BEFORE"
    --time_after "$TIME_AFTER"
    --step_interval "$STEP_INTERVAL"
    --start_date "$FORECAST_CONTEXT_START"
    --end_date "$FORECAST_CONTEXT_END"
    --place "$NASA_PLACE"
    --bodies_dir "$OUT_DIR/nasa_bodies"
    --backup_dir "$OUT_DIR/nasa_bodies_backup"
    --master_output "$OUT_DIR/nasa_master_focus_sparse.csv"
    --raw_output "$OUT_DIR/nasa_master_focus_sparse.Raw.csv"
    --command_script "$OUT_DIR/2-nasa_download.replay.sh"
    --random-background "$RANDOM_BACKGROUND"
    --quiet-background-percent 0.0
    --quiet-window-radius "$QUIET_WINDOW_RADIUS"
    --random-event-window "$RANDOM_EVENT_WINDOW"
    --random-event-count "$RANDOM_EVENT_COUNT"
    --background-output "$OUT_DIR/nasa_background_sparse.csv"
    --max_workers "$MAX_WORKERS"
    --progress
    --chunk-manifest
)

if [[ -n "$OBSERVER_GEO" ]]; then
    NASA_ARGS+=(--observer-geo="$OBSERVER_GEO")
fi

echo ""
echo "[1/4] NASA/JPL ephemerides via nasaDb.py..."
"$PYTHON_BIN" "${NASA_ARGS[@]}"

[[ -f "$OUT_DIR/nasa_master_focus_sparse.csv" ]] || { echo "[ERROR] nasa_master_focus_sparse.csv was not created." >&2; exit 1; }

echo ""
echo "[2/4] Add USGS core columns with left-bin event semantics..."
"$PYTHON_BIN" "$ADD_USGS_PY" \
    --nasa-master "$OUT_DIR/nasa_master_focus_sparse.csv" \
    --usgs-events "$MASTER_EVENTS_CSV" \
    --output "$OUT_DIR/master_with_usgs_core.csv"

echo ""
echo "[3/4] Convert legacy NASA columns to astrofmt..."
"$PYTHON_BIN" "$CONV_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core.csv" \
    --output-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv"

MASTER_OUT="${MASTER_OUT:-$OUT_DIR/master_with_usgs_core_astrofmt.csv}"
echo ""
echo "[4/4] Quartile quantization (bins=$QUANT_BINS) -> $MASTER_OUT"
"$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
    --output-csv "$MASTER_OUT" \
    --bins "$QUANT_BINS"

echo ""
echo "[4b/4] Sanitize numeric blanks for DLvsWAVE loader..."
SANITIZED_TMP="$OUT_DIR/master_with_usgs_core_astrofmt.sanitized.tmp.csv"
"$PYTHON_BIN" "$SANITIZE_PY" \
    --input-csv "$MASTER_OUT" \
    --output-csv "$SANITIZED_TMP" \
    --report-json "$OUT_DIR/master_with_usgs_core_astrofmt_sanitize_report.json" \
    --skip-cols date
mv "$SANITIZED_TMP" "$MASTER_OUT"

echo ""
echo "======================================================================"
echo " FullAstroJapan 7d master ready: $MASTER_OUT"
echo " Rows:       $(wc -l < "$MASTER_OUT")"
echo " Columns:    $(head -1 "$MASTER_OUT" | tr ',' '\n' | wc -l)"
echo " First date: $(awk -F',' 'NR==2{print $1}' "$MASTER_OUT")"
echo " Last date:  $(awk -F',' 'END{print $1}' "$MASTER_OUT")"
echo " Event bins: $(awk -F',' 'NR>1 && $2+0>0{n++} END{print n+0}' "$MASTER_OUT")"
echo "======================================================================"

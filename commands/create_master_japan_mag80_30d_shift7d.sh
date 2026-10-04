#!/usr/bin/env bash
# Create Japan MAG8.0+ master at 30d resolution with a +7d shifted grid.
#
# Shift logic: TIME_BEFORE=173d instead of 180d (180 - 7 = 173).
#
# Usage:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/create_master_japan_mag80_30d_shift7d.sh
set -euo pipefail

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/japan-mag80-1900plus-30d-shift7d}"
PYTHON_BIN="${PYTHON_BIN:-python}"

START_DATE="${START_DATE:-1904-01-01}"
END_DATE="${END_DATE:-2026-12-31}"
MIN_MAG="${MIN_MAG:-8.0}"
LAT_MIN="${LAT_MIN:-20}"
LAT_MAX="${LAT_MAX:-40}"
LON_MIN="${LON_MIN:--179}"
LON_MAX="${LON_MAX:-179}"

STEP_INTERVAL="30d"
TIME_BEFORE="173d"
TIME_AFTER="240d"
TEST_START_DATE="${TEST_START_DATE:-2026-01-01}"
TEST_END_DATE="${TEST_END_DATE:-2026-12-31}"

ADD_USGS_PY="${ADD_USGS_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/add_usgs_core_columns_to_master.py}"
CONV_PY="${CONV_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/convert_astro_columns_to_standard.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"
QUANT_BINS="${QUANT_BINS:-4}"

REF_USGS="$ASTRO_ROOT/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/earthquakes.RAW.csv"

[[ -d "$ASTRO_ROOT" ]] || { echo "[ERROR] ASTRO_ROOT not found: $ASTRO_ROOT" >&2; exit 1; }
[[ -f "$ADD_USGS_PY" ]] || { echo "[ERROR] Script not found: $ADD_USGS_PY" >&2; exit 1; }
[[ -f "$CONV_PY" ]] || { echo "[ERROR] Script not found: $CONV_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] Script not found: $QUANT_PY" >&2; exit 1; }
[[ -f "$ASTRO_ROOT/nasaDb.py" ]] || { echo "[ERROR] nasaDb.py not found in $ASTRO_ROOT" >&2; exit 1; }

mkdir -p "$OUT_DIR" "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"

echo "============================================================"
echo " Japan MAG8.0+ 30d shift+7d - master creation"
echo " Output dir:  $OUT_DIR"
echo " TIME_BEFORE: $TIME_BEFORE (shift +7d vs original 180d)"
echo " QUANT_BINS:  $QUANT_BINS"
echo "============================================================"

echo ""
echo "[1/4] USGS earthquakes..."
if [[ -f "$REF_USGS" ]]; then
    cp "$REF_USGS" "$OUT_DIR/earthquakes.RAW.csv"
    echo "[INFO] Reused earthquakes.RAW.csv from reference run."
else
    echo "[INFO] Reference file not found, downloading from USGS..."
    "$PYTHON_BIN" "$ASTRO_ROOT/usgsDb.py" \
        --starttime "$START_DATE" \
        --endtime "$END_DATE" \
        --lat-min "$LAT_MIN" \
        --lat-max "$LAT_MAX" \
        --lon-min "$LON_MIN" \
        --lon-max "$LON_MAX" \
        --min-mag "$MIN_MAG" \
        --max-mag 10.0 \
        --output-folder "$OUT_DIR" \
        --raw-output "$OUT_DIR/earthquakes.RAW.csv" \
        --grouped-output "$OUT_DIR/earthquakesGrouped.1.csv" \
        --grouping-days 1 \
        --expand 0.0 \
        --overwrite
fi

[[ -f "$OUT_DIR/earthquakes.RAW.csv" ]] || { echo "[ERROR] earthquakes.RAW.csv was not created." >&2; exit 1; }
echo "[OK] USGS: $(wc -l < "$OUT_DIR/earthquakes.RAW.csv") rows including header"

echo ""
echo "[2/4] NASA ephemerides with 30d grid shift+7d..."
"$PYTHON_BIN" "$ASTRO_ROOT/nasaDb.py" \
    --csv_file "$OUT_DIR/earthquakes.RAW.csv" \
    --datetime_column time \
    --time_before "$TIME_BEFORE" \
    --time_after "$TIME_AFTER" \
    --step_interval "$STEP_INTERVAL" \
    --start_date "$TEST_START_DATE" \
    --end_date "$TEST_END_DATE" \
    --observer-geo="34.5,137.5,0,japan" \
    --place earthFull \
    --bodies_dir "$OUT_DIR/nasa_bodies" \
    --backup_dir "$OUT_DIR/nasa_bodies_backup" \
    --master_output "$OUT_DIR/nasa_master_focus_sparse.csv" \
    --raw_output "$OUT_DIR/nasa_master_focus_sparse.Raw.csv" \
    --command_script "$OUT_DIR/2-nasa_download.replay.sh" \
    --random-background 730d \
    --quiet-background-percent 0.0 \
    --quiet-window-radius 7d \
    --random-event-window 120d \
    --random-event-count 4 \
    --background-output "$OUT_DIR/nasa_background_sparse.csv" \
    --max_workers 4 \
    --progress \
    --chunk-manifest

[[ -f "$OUT_DIR/nasa_master_focus_sparse.csv" ]] || { echo "[ERROR] nasa_master_focus_sparse.csv was not created." >&2; exit 1; }
echo "[OK] NASA master: $(wc -l < "$OUT_DIR/nasa_master_focus_sparse.csv") rows"

echo ""
echo "[3/4] Build master with USGS core + astro column format..."
"$PYTHON_BIN" "$ADD_USGS_PY" \
    --nasa-master "$OUT_DIR/nasa_master_focus_sparse.csv" \
    --usgs-events "$OUT_DIR/earthquakes.RAW.csv" \
    --output "$OUT_DIR/master_with_usgs_core.csv"

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
echo "============================================================"
echo " Master ready for training: $MASTER_OUT"
echo " Rows:       $(wc -l < "$MASTER_OUT")"
echo " Columns:    $(head -1 "$MASTER_OUT" | tr ',' '\n' | wc -l)"
echo " First date: $(awk -F',' 'NR==2{print $1}' "$MASTER_OUT")"
echo " Last date:  $(awk -F',' 'END{print $1}' "$MASTER_OUT")"
echo "============================================================"

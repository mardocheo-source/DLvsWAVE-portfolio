#!/usr/bin/env bash
# Stable-geocentric 30d Japan/Nankai validation-variant pipeline.
#
# Builds a stable Earth-centered vector master, runs normal/reverse/random
# validation variants, then produces a common forecast-window consensus.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
MASTER_ROOT="${MASTER_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-30d-stable-geocentric-neganchors}"
BASE_MASTER="${BASE_MASTER:-$MASTER_ROOT/master_with_usgs_core_astrofmt.csv}"
OUT_ROOT="${OUT_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-30d-stable-geocentric-neganchors-validation-variants-future-long}"
COMPARE_ROOT="${COMPARE_ROOT:-$OUT_ROOT/final_variant_consensus}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPARE_DIR="${COMPARE_DIR:-$COMPARE_ROOT/consensus_$STAMP}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"

FORECAST_START="${FORECAST_START:-2026-02-01}"
FORECAST_END="${FORECAST_END:-2026-12-31}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-240}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-8}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-8675309}"
RECENT_VALIDATION_SKIP_IF_UNAVAILABLE="${RECENT_VALIDATION_SKIP_IF_UNAVAILABLE:-1}"
RANDOM_SEED="${RANDOM_SEED:-8675309}"
THRESHOLD="${THRESHOLD:-0.5}"
SKIP_MASTER="${SKIP_MASTER:-0}"
SKIP_RUNS="${SKIP_RUNS:-0}"
ALLOW_TRAIN_AFTER_TEST="${ALLOW_TRAIN_AFTER_TEST:-0}"
AUTO_CLIP_FIRST="${AUTO_CLIP_FIRST:-vertical}"
AUTO_CLIP_MARS_FALLBACK="${AUTO_CLIP_MARS_FALLBACK:-horizontal}"
AUGMENT_NEGATIVE_EVENTS="${AUGMENT_NEGATIVE_EVENTS:-1}"
WORLD_NEGATIVE_EVENTS_CSV="${WORLD_NEGATIVE_EVENTS_CSV:-$ASTRO_ROOT/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv}"
NEGATIVE_MIN_MAG="${NEGATIVE_MIN_MAG:-8.0}"
NEGATIVE_MAX_EVENTS="${NEGATIVE_MAX_EVENTS:-48}"
NEGATIVE_DEDUPE_DAYS="${NEGATIVE_DEDUPE_DAYS:-30}"
NEGATIVE_JAPAN_LAT_MIN="${NEGATIVE_JAPAN_LAT_MIN:-28}"
NEGATIVE_JAPAN_LAT_MAX="${NEGATIVE_JAPAN_LAT_MAX:-44}"
NEGATIVE_JAPAN_LON_MIN="${NEGATIVE_JAPAN_LON_MIN:-128}"
NEGATIVE_JAPAN_LON_MAX="${NEGATIVE_JAPAN_LON_MAX:-147}"

if [[ "$ALLOW_TRAIN_AFTER_TEST" == "1" || "$ALLOW_TRAIN_AFTER_TEST" == "true" ]]; then
    echo "[ERROR] Validation variants forbid train-after-test." >&2
    echo "        reverse/random are serial-slot robustness checks; training must remain before test slots." >&2
    exit 1
fi

manifest_path() {
    printf '%s\n' "$MASTER_ROOT/master_with_usgs_core_astrofmt_manifest.json"
}

manifest_clipped_mars() {
    local manifest="$1"
    [[ -f "$manifest" ]] || return 1
    "$PYTHON_BIN" - "$manifest" <<'PY'
import json
import sys
path = sys.argv[1]
data = json.load(open(path))
for item in data.get("skipped_body_specs", []):
    name = str(item.get("body_name", "")).lower()
    reason = str(item.get("reason", "")).lower()
    if "mars" in name and ("clip" in reason or "horizons" in reason or "error" in reason):
        raise SystemExit(0)
raise SystemExit(1)
PY
}

build_master() {
    local auto_clip="$1"
    echo "[master] Creating stable geocentric 30d master with AUTO_CLIP=$auto_clip"
    env \
        OUT_DIR="$MASTER_ROOT" \
        MASTER_OUT="$BASE_MASTER" \
        STEP_DAYS=30 \
        AUTO_CLIP="$auto_clip" \
        AUGMENT_NEGATIVE_EVENTS="$AUGMENT_NEGATIVE_EVENTS" \
        WORLD_NEGATIVE_EVENTS_CSV="$WORLD_NEGATIVE_EVENTS_CSV" \
        NEGATIVE_MIN_MAG="$NEGATIVE_MIN_MAG" \
        NEGATIVE_MAX_EVENTS="$NEGATIVE_MAX_EVENTS" \
        NEGATIVE_DEDUPE_DAYS="$NEGATIVE_DEDUPE_DAYS" \
        NEGATIVE_JAPAN_LAT_MIN="$NEGATIVE_JAPAN_LAT_MIN" \
        NEGATIVE_JAPAN_LAT_MAX="$NEGATIVE_JAPAN_LAT_MAX" \
        NEGATIVE_JAPAN_LON_MIN="$NEGATIVE_JAPAN_LON_MIN" \
        NEGATIVE_JAPAN_LON_MAX="$NEGATIVE_JAPAN_LON_MAX" \
        "$PWD/commands/create_master_japan_nankai_30d_stable_geocentric.sh"
}

if [[ ! -f "$BASE_MASTER" ]]; then
    if [[ "$SKIP_MASTER" == "1" ]]; then
        echo "[ERROR] BASE_MASTER not found and SKIP_MASTER=1: $BASE_MASTER" >&2
        exit 1
    fi
    build_master "$AUTO_CLIP_FIRST"
    if manifest_clipped_mars "$(manifest_path)"; then
        echo "[master] Mars was clipped by AUTO_CLIP=$AUTO_CLIP_FIRST; rebuilding with AUTO_CLIP=$AUTO_CLIP_MARS_FALLBACK"
        build_master "$AUTO_CLIP_MARS_FALLBACK"
    fi
else
    echo "[master] Existing base master found: $BASE_MASTER"
    if [[ "$SKIP_MASTER" != "1" ]] && manifest_clipped_mars "$(manifest_path)"; then
        echo "[master] Existing manifest shows Mars clipped; rebuilding with AUTO_CLIP=$AUTO_CLIP_MARS_FALLBACK"
        build_master "$AUTO_CLIP_MARS_FALLBACK"
    fi
fi

[[ -f "$BASE_MASTER" ]] || {
    echo "[ERROR] BASE_MASTER not found after master step: $BASE_MASTER" >&2
    exit 1
}

find_latest_run_dir() {
    local base_dir="$1"
    local latest=""
    shopt -s nullglob
    local candidates=("$base_dir"/pulsar_train*_best_trials_*)
    shopt -u nullglob
    if (( ${#candidates[@]} == 0 )); then
        return 1
    fi
    latest="$(printf '%s\n' "${candidates[@]}" | sort | tail -n 1)"
    [[ -d "$latest" ]] || return 1
    printf '%s\n' "$latest"
}

find_smart_forecast() {
    local run_dir="$1"
    local preferred="$run_dir/post_hybrid_checks_smart/smart_fusion_final__forecast.csv"
    local found=""
    if [[ -f "$preferred" ]]; then
        printf '%s\n' "$preferred"
        return 0
    fi
    found="$(find "$run_dir/post_hybrid_checks_smart" -type f -name 'smart_fusion_final__forecast.csv' 2>/dev/null | sort | tail -n 1 || true)"
    [[ -n "$found" && -f "$found" ]] || return 1
    printf '%s\n' "$found"
}

assert_forecast_rows_not_remapped() {
    local mapping_csv="$1"
    [[ -f "$mapping_csv" ]] || return 0
    "$PYTHON_BIN" - "$mapping_csv" <<'PY'
import csv
import sys
path = sys.argv[1]
bad = []
with open(path, newline="") as f:
    for row in csv.DictReader(f):
        if row.get("is_forecast_row") == "1" and row.get("slot_index") != row.get("source_index"):
            bad.append(row)
if bad:
    print(f"[ERROR] forecast rows remapped in {path}: {len(bad)}", file=sys.stderr)
    print(bad[:3], file=sys.stderr)
    raise SystemExit(2)
print(f"[OK] leak guard: forecast rows unchanged in {path}")
PY
}

prepare_variant() {
    local variant="$1"
    local variant_dir="$OUT_ROOT/$variant"
    local master_path="$variant_dir/master_with_usgs_core_astrofmt.csv"
    local mapping_path="$variant_dir/validation_variant_mapping.csv"
    mkdir -p "$variant_dir"
    if [[ "$variant" == "normal" ]]; then
        cp "$BASE_MASTER" "$master_path"
        {
            printf '{\n'
            printf '  "variant": "normal",\n'
            printf '  "input_csv": "%s",\n' "$BASE_MASTER"
            printf '  "output_csv": "%s",\n' "$master_path"
            printf '  "leakage_guard": "unchanged baseline; forecast rows are original",\n'
            printf '  "train_after_test_allowed": false,\n'
            printf '  "validation_axis": "serial_slot_order",\n'
            printf '  "forecast_start_date": "%s"\n' "$FORECAST_START"
            printf '}\n'
        } > "$variant_dir/validation_variant_manifest.json"
    else
        "$PYTHON_BIN" "$PWD/make_validation_variant_master.py" \
            --input-csv "$BASE_MASTER" \
            --output-csv "$master_path" \
            --manifest-json "$variant_dir/validation_variant_manifest.json" \
            --mapping-csv "$mapping_path" \
            --variant "$variant" \
            --forecast-start-date "$FORECAST_START" \
            --random-seed "$RANDOM_SEED" >&2
        assert_forecast_rows_not_remapped "$mapping_path" >&2
    fi
    printf '%s\n' "$master_path"
}

run_variant() {
    local variant="$1"
    local master_path="$2"
    local log_file="/tmp/dlvswave_japan_nankai_30d_stable_geocentric_${variant}_validation_zoom_long.log"
    local db_file="japan_nankai_30d_stable_geocentric_${variant}_validation_zoom_long.db"
    local out_dir="$OUT_ROOT/$variant"

    echo ""
    echo "[$variant] stable geocentric 30d ZOOM LONG training"
    echo "  master: $master_path"
    echo "  out:    $out_dir"
    echo "  log:    $log_file"
    env \
        MASTER="$master_path" \
        LOG_FILE="$log_file" \
        DB_FILE="$db_file" \
        FORECAST_START="$FORECAST_START" \
        FORECAST_END="$FORECAST_END" \
        VALIDATION_MAX_LOOKBACK_RECORDS="$VALIDATION_MAX_LOOKBACK_RECORDS" \
        VALIDATION_EVENT_COUNT="$VALIDATION_EVENT_COUNT" \
        VALIDATION_PRE_RECORDS="$VALIDATION_PRE_RECORDS" \
        VALIDATION_POST_RECORDS="$VALIDATION_POST_RECORDS" \
        RECENT_VALIDATION_RANDOM_NEGATIVES="$RECENT_VALIDATION_RANDOM_NEGATIVES" \
        RECENT_VALIDATION_RANDOM_SEED="$RECENT_VALIDATION_RANDOM_SEED" \
        RECENT_VALIDATION_SKIP_IF_UNAVAILABLE="$RECENT_VALIDATION_SKIP_IF_UNAVAILABLE" \
        "$PWD/commands/train_japan_nankai_30d_zoom_long.sh"
}

echo "======================================================================"
echo " Japan/Nankai stable-geocentric 30d - validation variants ZOOM LONG"
echo " Base master:     $BASE_MASTER"
echo " Output root:     $OUT_ROOT"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " Variants:        normal, reverse, random(seed=$RANDOM_SEED)"
echo " Leak guard:      forecast rows are never shuffled; mapping is checked"
echo " Train/test:      train-after-test forbidden; validation uses serial slot order"
echo " Val negatives:   random=$RECENT_VALIDATION_RANDOM_NEGATIVES seed=$RECENT_VALIDATION_RANDOM_SEED"
echo " Event anchors:   global non-Japan M8+ as mag=0 count<=${NEGATIVE_MAX_EVENTS} enabled=$AUGMENT_NEGATIVE_EVENTS"
echo " Japan bbox:      lat ${NEGATIVE_JAPAN_LAT_MIN}..${NEGATIVE_JAPAN_LAT_MAX}, lon ${NEGATIVE_JAPAN_LON_MIN}..${NEGATIVE_JAPAN_LON_MAX}"
echo " Auto clip:       first=$AUTO_CLIP_FIRST mars_fallback=$AUTO_CLIP_MARS_FALLBACK"
echo "======================================================================"

declare -A VARIANT_MASTER
for variant in normal reverse random; do
    VARIANT_MASTER[$variant]="$(prepare_variant "$variant")"
done

if [[ "$SKIP_RUNS" != "1" ]]; then
    for variant in normal reverse random; do
        run_variant "$variant" "${VARIANT_MASTER[$variant]}"
    done
else
    echo "[SKIP] Training runs skipped; using latest runs under variant folders."
fi

echo ""
echo "[consensus] Collecting final smart forecasts..."
mkdir -p "$COMPARE_DIR"
SOURCE_MANIFEST="$COMPARE_DIR/source_forecasts.txt"
: > "$SOURCE_MANIFEST"
FORECASTS=()
for variant in normal reverse random; do
    run_dir="$(find_latest_run_dir "$OUT_ROOT/$variant")" || {
        echo "[ERROR] No run directory found for variant=$variant under $OUT_ROOT/$variant" >&2
        exit 1
    }
    forecast="$(find_smart_forecast "$run_dir")" || {
        echo "[ERROR] No smart_fusion_final__forecast.csv for variant=$variant in $run_dir" >&2
        exit 1
    }
    FORECASTS+=("$forecast")
    {
        printf '%s_run=%s\n' "$variant" "$run_dir"
        printf '%s_forecast=%s\n' "$variant" "$forecast"
        printf '%s_master=%s\n' "$variant" "${VARIANT_MASTER[$variant]}"
    } >> "$SOURCE_MANIFEST"
done

"$PYTHON_BIN" "$PWD/forecast_common_window.py" \
    "${FORECASTS[@]}" \
    --output-csv "$COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.csv" \
    --output-png "$COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.png" \
    --output-json "$COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.json" \
    --score-column auto \
    --threshold "$THRESHOLD" \
    --title "Japan/Nankai 30d stable geocentric normal vs reverse vs random consensus"

echo ""
echo "======================================================================"
echo " Stable geocentric 30d validation-variant consensus ready"
echo " Source manifest: $SOURCE_MANIFEST"
echo " CSV:             $COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.csv"
echo " PNG:             $COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.png"
echo " JSON:            $COMPARE_DIR/normal_reverse_random_30d_stable_geocentric_common_detected_window.json"
echo "======================================================================"

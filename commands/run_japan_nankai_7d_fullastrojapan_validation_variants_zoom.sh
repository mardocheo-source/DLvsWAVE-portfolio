#!/usr/bin/env bash
# FullAstroJapan 7d Japan/Nankai diagnostic pipeline:
# master -> normal/reverse/random validation variants -> common-window consensus.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
MASTER_ROOT="${MASTER_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-7d-fullastrojapan-neganchors}"
BASE_MASTER="${BASE_MASTER:-$MASTER_ROOT/master_with_usgs_core_astrofmt.csv}"
OUT_ROOT="${OUT_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-7d-fullastrojapan-neganchors-validation-variants-zoom}"
COMPARE_ROOT="${COMPARE_ROOT:-$OUT_ROOT/final_variant_consensus}"
STAMP="$(date +%Y%m%d-%H%M%S)"
COMPARE_DIR="${COMPARE_DIR:-$COMPARE_ROOT/consensus_$STAMP}"
PYTHON_BIN="${PYTHON_BIN:-$PWD/.venv/bin/python}"
SANITIZE_PY="${SANITIZE_PY:-$PWD/sanitize_numeric_master.py}"

FORECAST_START="${FORECAST_START:-2026-07-01}"
FORECAST_END="${FORECAST_END:-2026-09-30}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-1400}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-4}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-4}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-12}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-8675309}"
RECENT_VALIDATION_SKIP_IF_UNAVAILABLE="${RECENT_VALIDATION_SKIP_IF_UNAVAILABLE:-1}"
RANDOM_SEED="${RANDOM_SEED:-8675309}"
THRESHOLD="${THRESHOLD:-0.5}"
SKIP_MASTER="${SKIP_MASTER:-0}"
SKIP_RUNS="${SKIP_RUNS:-0}"
ALLOW_TRAIN_AFTER_TEST="${ALLOW_TRAIN_AFTER_TEST:-0}"

if [[ "$ALLOW_TRAIN_AFTER_TEST" == "1" || "$ALLOW_TRAIN_AFTER_TEST" == "true" ]]; then
    echo "[ERROR] Validation variants forbid train-after-test." >&2
    exit 1
fi

build_master() {
    echo "[master] Creating fullAstroJapan 7d negative-anchor master"
    env \
        OUT_DIR="$MASTER_ROOT" \
        MASTER_OUT="$BASE_MASTER" \
        FORECAST_CONTEXT_START="$FORECAST_START" \
        FORECAST_CONTEXT_END="$FORECAST_END" \
        "$PWD/commands/create_master_japan_nankai_7d_fullastrojapan_neganchors.sh"
}

if [[ ! -f "$BASE_MASTER" ]]; then
    if [[ "$SKIP_MASTER" == "1" ]]; then
        echo "[ERROR] BASE_MASTER not found and SKIP_MASTER=1: $BASE_MASTER" >&2
        exit 1
    fi
    build_master
else
    echo "[master] Existing base master found: $BASE_MASTER"
fi

[[ -f "$BASE_MASTER" ]] || {
    echo "[ERROR] BASE_MASTER not found after master step: $BASE_MASTER" >&2
    exit 1
}

echo "[master] Sanitizing base master numeric blanks before variant split..."
SANITIZED_TMP="$MASTER_ROOT/master_with_usgs_core_astrofmt.sanitized.tmp.csv"
"$PYTHON_BIN" "$SANITIZE_PY" \
    --input-csv "$BASE_MASTER" \
    --output-csv "$SANITIZED_TMP" \
    --report-json "$MASTER_ROOT/master_with_usgs_core_astrofmt_sanitize_report.json" \
    --skip-cols date
mv "$SANITIZED_TMP" "$BASE_MASTER"

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
    local log_file="/tmp/dlvswave_japan_nankai_7d_fullastro_${variant}_validation_zoom.log"
    local db_file="japan_nankai_7d_fullastro_${variant}_validation_zoom.db"
    local out_dir="$OUT_ROOT/$variant"

    echo ""
    echo "[$variant] fullAstroJapan 7d diagnostic training"
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
        "$PWD/commands/train_japan_nankai_7d_zoom_long.sh"
}

echo "======================================================================"
echo " Japan/Nankai fullAstroJapan 7d - validation variants diagnostic zoom"
echo " Base master:     $BASE_MASTER"
echo " Output root:     $OUT_ROOT"
echo " Forecast:        $FORECAST_START -> $FORECAST_END"
echo " Variants:        normal, reverse, random(seed=$RANDOM_SEED)"
echo " Leak guard:      forecast rows are never shuffled; mapping is checked"
echo " Train/test:      train-after-test forbidden"
echo " Val negatives:   random=$RECENT_VALIDATION_RANDOM_NEGATIVES seed=$RECENT_VALIDATION_RANDOM_SEED"
echo " KAN inherited:   enable=${ENABLE_KAN:-0} presets=${KAN_PRESETS_RUN:-tiny} hybrid=${HYBRID_KAN:-0}"
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
    --output-csv "$COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.csv" \
    --output-png "$COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.png" \
    --output-json "$COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.json" \
    --score-column auto \
    --threshold "$THRESHOLD" \
    --title "Japan/Nankai 7d fullAstroJapan normal vs reverse vs random consensus"

echo ""
echo "======================================================================"
echo " FullAstroJapan 7d validation-variant consensus ready"
echo " Source manifest: $SOURCE_MANIFEST"
echo " CSV:             $COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.csv"
echo " PNG:             $COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.png"
echo " JSON:            $COMPARE_DIR/normal_reverse_random_7d_fullastrojapan_common_detected_window.json"
echo "======================================================================"

#!/usr/bin/env bash
# Overnight XPU launcher for Japan-zone M7.9+ 30d + 7d proximity counterchecks.
# Creates an isolated macro root under DB, with separate 30d/ and 7d/ roots.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"
DB_ROOT="${DB_ROOT:-/mnt/git0/git/repository/astro-USGS2/DB}"
MACRO_ROOT="${MACRO_ROOT:-$DB_ROOT/japan-zone-mag79plus-proximity-xpu-night-$RUN_STAMP}"
ROOT_30D="$MACRO_ROOT/30d"
ROOT_7D="$MACRO_ROOT/7d"

RUN_30D="${RUN_30D:-1}"
RUN_7D="${RUN_7D:-1}"
PROGRESS_FILTER="${PROGRESS_FILTER:-1}"
VARIANTS_PER_PHASE="${VARIANTS_PER_PHASE:-5}"

# Compact KAN+Deep hybrid is enabled by default for the proximity night batch.
# With one Deep partner and one weighted mode, each seed trains pure KAN plus
# one KAN-hybrid companion per KAN preset.  The default seed span is therefore
# shorter than the KAN-only night profile to keep the trial budget comparable.
HYBRID_KAN="${HYBRID_KAN:-1}"
DEEP_PRESETS_RUN="${DEEP_PRESETS_RUN:-tiny}"
HYBRID_KAN_PARTNERS="${HYBRID_KAN_PARTNERS:-deep:tiny}"
HYBRID_KAN_MODES="${HYBRID_KAN_MODES:-weighted}"
HYBRID_KAN_ALPHAS="${HYBRID_KAN_ALPHAS:-0.5}"
HYBRID_KAN_THRESHOLD="${HYBRID_KAN_THRESHOLD:-0.5}"
DEEP_DEVICE="${DEEP_DEVICE:-xpu}"
if [[ "$HYBRID_KAN" == "1" || "$HYBRID_KAN" == "true" || "$HYBRID_KAN" == "yes" ]]; then
  SEEDS_SPEC="${SEEDS_SPEC:-4:63}"
  TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-420}"
else
  SEEDS_SPEC="${SEEDS_SPEC:-4:123}"
  TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-360}"
fi
MAX_ITER="${MAX_ITER:-900}"
BEST_N="${BEST_N:-72}"
KEEP_BEST="${KEEP_BEST:-20}"
KEEP_WORST="${KEEP_WORST:-6}"

# Keep validation symmetric across main history, no-history, and proximity
# variants.  The context width is intentionally exposed so the same launcher can
# widen the non-event shoulders around each seismic event without editing code.
TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-6}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-6}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-2600}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-24}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-20260608}"
COUNTER_MIN_EVENTS="${COUNTER_MIN_EVENTS:-12}"

PYTHON_BIN="${PYTHON_BIN:-${HOME}/venvs/dlvswave-xpu/bin/python}"
SRC_EVENTS="${SRC_EVENTS:-$MACRO_ROOT/earthquakes.RAW.csv}"

REBUILD_CATALOG="${REBUILD_CATALOG:-0}"
if [[ ! -f "$SRC_EVENTS" || "$REBUILD_CATALOG" == "1" || "$REBUILD_CATALOG" == "true" ]]; then
  echo "======================================================================"
  echo "[catalog] Downloading/rebuilding raw earthquakes catalog to $SRC_EVENTS..."
  echo "======================================================================"
  ASTRO_ROOT_DIR="/mnt/git0/git/repository/astro-USGS2"
  ASTRO_PYTHON="$ASTRO_ROOT_DIR/.venv312/bin/python"
  if [[ ! -x "$ASTRO_PYTHON" ]]; then
    ASTRO_PYTHON="python3"
  fi
  mkdir -p "$(dirname "$SRC_EVENTS")"
  (
    cd "$ASTRO_ROOT_DIR"
    "$ASTRO_PYTHON" usgsDb.py \
      --starttime 1900-01-01 \
      --endtime "$(date +%Y-%m-%d)" \
      --min-mag 7.7 \
      --max-mag 10.0 \
      --zones world \
      --zones-csv usgs_download/zones/zones.csv \
      --raw-output "$SRC_EVENTS" \
      --no-map \
      --no-event-map \
      --overwrite
  )
fi



# XPU only. No CPU auto-selection pretest in the night batch.
export DEVICE_MODE=xpu
export KAN_DEVICE=xpu
export KAN_QUIET="${KAN_QUIET:-1}"
export JOBS="${JOBS:-2}"
export ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-2}"
export METRIC_TEST_JOBS="${METRIC_TEST_JOBS:-1}"
export METRIC_TEST_CPU_JOBS="${METRIC_TEST_CPU_JOBS:-1}"
export CPU_SPEED_TEST="${CPU_SPEED_TEST:-0}"
export METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-0}"

export AUTO_DEVICE_SELECT=0


# Rebuild from a stable post-1903 start so Horizons coverage is less likely to
# drop secondary bodies. The master is fetched daily and then slot-aggregated.
START_DATE="${START_DATE:-1903-01-01}"
REBUILD_MASTER="${REBUILD_MASTER:-1}"
NASA_DAILY_MASTER_MODE="${NASA_DAILY_MASTER_MODE:-1}"
NASA_SLOT_ADVANCED_STATS="${NASA_SLOT_ADVANCED_STATS:-1}"
NASA_SLOT_ADVANCED_GROUP_SIZE="${NASA_SLOT_ADVANCED_GROUP_SIZE:-4}"
NASA_SLOT_AGGREGATION="${NASA_SLOT_AGGREGATION:-median}"

# Patient NASA/JPL downloads.
MAX_WORKERS="${MAX_WORKERS:-3}"
MAX_RETRIES="${MAX_RETRIES:-8}"
SLEEP_TIME="${SLEEP_TIME:-1.5}"

# Broader but bounded body set after 1903.
NASA_PLACE="${NASA_PLACE:-japan}"
NASA_AUTO_OBSERVER_FROM_TARGET="${NASA_AUTO_OBSERVER_FROM_TARGET:-1}"
NASA_OBSERVER_ALIAS="${NASA_OBSERVER_ALIAS:-target_centroid}"
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-3,4,20,27}"
BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.13 2.14 2.21 2.22 2.3 3.1}"
BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-4.1 4.31 4.32 4.33 4.34 4.4 5.11 5.22 6.11 6.14}"

# More horizontal-history features. The augmenter resolves astrofmt body:* cols.
HISTORY_MODE="${HISTORY_MODE:-fibonacci-gold}"
HISTORY_VALUE="${HISTORY_VALUE:-1280}"
HISTORY_ENABLE_SEISMIC="${HISTORY_ENABLE_SEISMIC:-1}"
HISTORY_ENABLE_ASTRO="${HISTORY_ENABLE_ASTRO:-1}"
HISTORY_ASTRO_BODIES="${HISTORY_ASTRO_BODIES:-301,599,101955,499,299,699,502,136199}"
HISTORY_ASTRO_FIELDS="${HISTORY_ASTRO_FIELDS:-RA_rate,DEC_rate,AZ,EL,delta,delta_rate,sunTargetPA,velocityPA,_slot4_min,_slot4_max,_slot4_mean}"

# Binary detection must keep non-event context rows.
ROW_FILTER="${ROW_FILTER:-none}"
HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-random-sparse}"
HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE:-12}"
HISTORY_KEEP_NEIGHBOR_RECORDS="${HISTORY_KEEP_NEIGHBOR_RECORDS:-6}"
HISTORY_KEEP_RECENT_NEGATIVES="${HISTORY_KEEP_RECENT_NEGATIVES:-12}"

mkdir -p "$MACRO_ROOT"

PLAN_COMMON_ARGS=(
  --target-zones japan
  --counter-count 3
  --proximity-deg 45
  --counter-min-events "$COUNTER_MIN_EVENTS"
  --src-events "$SRC_EVENTS"
  --min-mag 7.9
  --binary-threshold 7.9
  --device xpu
  --out-of-region-mode neutralize-seismic
  --row-filter "$ROW_FILTER"
  --history-negative-sampling-mode "$HISTORY_NEGATIVE_SAMPLING_MODE"
  --rebuild-master "$REBUILD_MASTER"
  --nasa-daily-master-mode "$NASA_DAILY_MASTER_MODE"
  --nasa-slot-advanced-stats "$NASA_SLOT_ADVANCED_STATS"
  --extra-env "PYTHON_BIN=$PYTHON_BIN"
  --extra-env "KAN_DEVICE=xpu"
  --extra-env "KAN_QUIET=$KAN_QUIET"
  --extra-env "JOBS=$JOBS"
  --extra-env "HYBRID_KAN=$HYBRID_KAN"
  --extra-env "DEEP_PRESETS_RUN=$DEEP_PRESETS_RUN"
  --extra-env "DEEP_DEVICE=$DEEP_DEVICE"
  --extra-env "HYBRID_KAN_PARTNERS=$HYBRID_KAN_PARTNERS"
  --extra-env "HYBRID_KAN_MODES=$HYBRID_KAN_MODES"
  --extra-env "HYBRID_KAN_ALPHAS=$HYBRID_KAN_ALPHAS"
  --extra-env "HYBRID_KAN_THRESHOLD=$HYBRID_KAN_THRESHOLD"
  --extra-env "START_DATE=$START_DATE"
  --extra-env "MAX_WORKERS=$MAX_WORKERS"
  --extra-env "MAX_RETRIES=$MAX_RETRIES"
  --extra-env "SLEEP_TIME=$SLEEP_TIME"
  --extra-env "NASA_SLOT_ADVANCED_GROUP_SIZE=$NASA_SLOT_ADVANCED_GROUP_SIZE"
  --extra-env "NASA_SLOT_AGGREGATION=$NASA_SLOT_AGGREGATION"
  --extra-env "NASA_PLACE=$NASA_PLACE"
  --extra-env "NASA_AUTO_OBSERVER_FROM_TARGET=$NASA_AUTO_OBSERVER_FROM_TARGET"
  --extra-env "NASA_OBSERVER_ALIAS=$NASA_OBSERVER_ALIAS"
  --extra-env "EPHEMERIDES_FIELDS=$EPHEMERIDES_FIELDS"
  --extra-env "BODY_PRIMARY_LEVELS=$BODY_PRIMARY_LEVELS"
  --extra-env "BODY_SECONDARY_LEVELS=$BODY_SECONDARY_LEVELS"
  --extra-env "ENABLE_BINARY_TARGET=1"
  --extra-env "ENABLE_HORIZONTAL_HISTORY=1"
  --extra-env "HISTORY_MODE=$HISTORY_MODE"
  --extra-env "HISTORY_VALUE=$HISTORY_VALUE"
  --extra-env "HISTORY_ENABLE_SEISMIC=$HISTORY_ENABLE_SEISMIC"
  --extra-env "HISTORY_ENABLE_ASTRO=$HISTORY_ENABLE_ASTRO"
  --extra-env "HISTORY_ASTRO_BODIES=$HISTORY_ASTRO_BODIES"
  --extra-env "HISTORY_ASTRO_FIELDS=$HISTORY_ASTRO_FIELDS"
  --extra-env "HISTORY_RANDOM_NEGATIVES_PER_POSITIVE=$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE"
  --extra-env "HISTORY_KEEP_NEIGHBOR_RECORDS=$HISTORY_KEEP_NEIGHBOR_RECORDS"
  --extra-env "HISTORY_KEEP_RECENT_NEGATIVES=$HISTORY_KEEP_RECENT_NEGATIVES"
  --extra-env "TARGET_EVENT_COUNT=$TARGET_EVENT_COUNT"
  --extra-env "VALIDATION_EVENT_COUNT=$VALIDATION_EVENT_COUNT"
  --extra-env "VALIDATION_PRE_RECORDS=$VALIDATION_PRE_RECORDS"
  --extra-env "VALIDATION_POST_RECORDS=$VALIDATION_POST_RECORDS"
  --extra-env "VALIDATION_MAX_LOOKBACK_RECORDS=$VALIDATION_MAX_LOOKBACK_RECORDS"
  --extra-env "RECENT_VALIDATION_RANDOM_NEGATIVES=$RECENT_VALIDATION_RANDOM_NEGATIVES"
  --extra-env "RECENT_VALIDATION_RANDOM_SEED=$RECENT_VALIDATION_RANDOM_SEED"
  --extra-env "SEEDS_SPEC=$SEEDS_SPEC"
  --extra-env "MAX_ITER=$MAX_ITER"
  --extra-env "BEST_N=$BEST_N"
  --extra-env "KEEP_BEST=$KEEP_BEST"
  --extra-env "KEEP_WORST=$KEEP_WORST"
  --extra-env "CPU_SPEED_TEST=0"
  --extra-env "METRIC_TEST_CPU_COMPARE=0"
  --extra-env "AUTO_DEVICE_SELECT=0"
)

make_plan_if_needed() {
  local phase="$1"
  local root="$2"
  local label="$3"
  local wrapper="$4"
  local step="$5"
  local forecast_start="$6"
  local forecast_end="$7"
  local events_end="$8"
  local forecast_label="$9"
  local time_before="${10}"
  local time_after="${11}"

  if [[ -f "$root/countercheck_plan.json" && "${REPLAN:-1}" != "1" ]]; then
    echo "[plan] Existing plan kept: $root/countercheck_plan.json"
    return
  fi

  "$PYTHON_BIN" geographic_countercheck.py plan \
    --output-root "$root" \
    --base-run-label "$label" \
    --pipeline-wrapper "$wrapper" \
    --step-interval "$step" \
    --forecast-start "$forecast_start" \
    --forecast-end "$forecast_end" \
    --events-end-date "$events_end" \
    --forecast-label "$forecast_label" \
    --time-before "$time_before" \
    --time-after "$time_after" \
    "${PLAN_COMMON_ARGS[@]}"

  echo "[plan] Created: $root/countercheck_plan.json"
}

run_macro_with_progress() {
  local phase_no="$1"
  local phase_name="$2"
  local macro="$3"

  if [[ "$PROGRESS_FILTER" != "1" ]]; then
    "$macro"
    return $?
  fi

  set +e
  stdbuf -oL -eL "$macro" 2>&1 | python3 -u countercheck_progress_filter.py \
    --phase-no "$phase_no" \
    --phase-name "$phase_name" \
    --variants "$VARIANTS_PER_PHASE" \
    --trials-per-variant "$TRIALS_PER_VARIANT"
  local macro_status=${PIPESTATUS[0]}
  set -e
  return "$macro_status"
}

cat > "$MACRO_ROOT/NIGHT_RUN_SPEC.md" <<EOF
# Japan-zone M7.9+ XPU Night Run

- Created: $(date -Is)
- Macro root: \`$MACRO_ROOT\`
- 30d root: \`$ROOT_30D\`
- 7d root: \`$ROOT_7D\`
- Run selection in maps: latest subrun per variant inside each phase root.
- Estimated total runtime: about 8 hours on the current Arc/XPU box.
- Calibration source: recent compact XPU run was about 69 min for 30d and about 69 min for 7d at 144 trials/variant.
- Night budget: \`$TRIALS_PER_VARIANT\` trials/variant, \`$MAX_ITER\` max_iter.
- Validation: target events=\`$TARGET_EVENT_COUNT\`, validation events=\`$VALIDATION_EVENT_COUNT\`, context=\`$VALIDATION_PRE_RECORDS\`/\`$VALIDATION_POST_RECORDS\` records.
- Counter minimum events: \`$COUNTER_MIN_EVENTS\`.
- Out-of-region seismic handling: \`neutralize-seismic\`.
- Hybrid KAN: \`$HYBRID_KAN\`; deep presets=\`$DEEP_PRESETS_RUN\`;
  partners=\`$HYBRID_KAN_PARTNERS\`; modes=\`$HYBRID_KAN_MODES\`;
  alphas=\`$HYBRID_KAN_ALPHAS\`.
- Start date: \`$START_DATE\`
- Bodies primary: \`$BODY_PRIMARY_LEVELS\`
- Bodies secondary: \`$BODY_SECONDARY_LEVELS\`
- History bodies: \`$HISTORY_ASTRO_BODIES\`
- History fields: \`$HISTORY_ASTRO_FIELDS\`
EOF

echo "======================================================================"
echo " Japan-zone M7.9+ 30d + 7d proximity NIGHT XPU run"
echo " Macro root:       $MACRO_ROOT"
echo " 30d root:         $ROOT_30D"
echo " 7d root:          $ROOT_7D"
echo " Start date:       $START_DATE"
echo " Device:           xpu jobs=$JOBS"
echo " Rebuild master:   $REBUILD_MASTER daily=$NASA_DAILY_MASTER_MODE"
echo " NASA retry:       workers=$MAX_WORKERS retries=$MAX_RETRIES sleep=$SLEEP_TIME"
echo " Bodies primary:   $BODY_PRIMARY_LEVELS"
echo " Bodies secondary: $BODY_SECONDARY_LEVELS"
echo " History bodies:   $HISTORY_ASTRO_BODIES"
echo " History fields:   $HISTORY_ASTRO_FIELDS"
echo " Sparse context:   mode=$HISTORY_NEGATIVE_SAMPLING_MODE per_pos=$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE neighbor=$HISTORY_KEEP_NEIGHBOR_RECORDS recent=$HISTORY_KEEP_RECENT_NEGATIVES"
echo " Validation:       target_events=$TARGET_EVENT_COUNT validation_events=$VALIDATION_EVENT_COUNT pre/post=$VALIDATION_PRE_RECORDS/$VALIDATION_POST_RECORDS recent_neg=$RECENT_VALIDATION_RANDOM_NEGATIVES"
echo " Counter min:      events=$COUNTER_MIN_EVENTS"
echo " OOR seismic:      neutralize-seismic"
echo " Hybrid KAN:       enabled=$HYBRID_KAN deep=$DEEP_PRESETS_RUN partners='$HYBRID_KAN_PARTNERS' modes=$HYBRID_KAN_MODES alphas=$HYBRID_KAN_ALPHAS"
echo " KAN budget:       seeds=$SEEDS_SPEC max_iter=$MAX_ITER trials/variant~$TRIALS_PER_VARIANT"
echo " Expected runtime: about 8 hours total on the current XPU machine."
echo "======================================================================"

make_plan_if_needed \
  "30d" \
  "$ROOT_30D" \
  "japan-zone-mag79plus-night-${RUN_STAMP}-30d" \
  "commands/run_world_mag79_japan_30d_may_dec_horizontal_binary_xpu.sh" \
  "30d" \
  "2026-04-30" \
  "2026-12-31" \
  "2026-04-29" \
  "May-Dec 2026, 30d night XPU richer horizontal history" \
  "180d" \
  "180d"

make_plan_if_needed \
  "7d" \
  "$ROOT_7D" \
  "japan-zone-mag79plus-night-${RUN_STAMP}-7d" \
  "commands/run_world_mag79_japan_aug_sep_7d_horizontal_binary_xpu.sh" \
  "7d" \
  "2026-07-27" \
  "2026-10-05" \
  "2026-07-26" \
  "Aug-Sep 2026, 7d night XPU richer horizontal history" \
  "42d" \
  "42d"

if [[ "$RUN_30D" == "1" ]]; then
  echo
  echo "======================================================================"
  echo "[1/2] Starting 30d night run"
  echo "======================================================================"
  run_macro_with_progress "1" "30d-night" "$ROOT_30D/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
fi

if [[ "$RUN_7D" == "1" ]]; then
  echo
  echo "======================================================================"
  echo "[2/2] Starting 7d night run"
  echo "======================================================================"
  run_macro_with_progress "2" "7d-night" "$ROOT_7D/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
fi

echo
echo "======================================================================"
echo " Japan-zone M7.9+ night batch complete"
echo " Macro root: $MACRO_ROOT"
echo " 30d maps:   $ROOT_30D/maps"
echo " 7d maps:    $ROOT_7D/maps"
echo "======================================================================"

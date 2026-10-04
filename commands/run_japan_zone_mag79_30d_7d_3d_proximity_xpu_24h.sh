#!/usr/bin/env bash
# Overnight XPU launcher for Japan-zone M7.9+ 30d + 7d + 3d proximity counterchecks (24-hour budget).
# Creates an isolated macro root under DB, with separate 30d/, 7d/ and 3d/ roots.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"
DB_ROOT="${DB_ROOT:-/mnt/git0/git/repository/astro-USGS2/DB}"
MACRO_ROOT="${MACRO_ROOT:-$DB_ROOT/japan-zone-mag79plus-proximity-xpu-24h-$RUN_STAMP}"
ROOT_30D="$MACRO_ROOT/30d"
ROOT_7D="$MACRO_ROOT/7d"
ROOT_3D="$MACRO_ROOT/3d"

RUN_30D="${RUN_30D:-1}"
RUN_7D="${RUN_7D:-1}"
RUN_3D="${RUN_3D:-1}"
TOTAL_PHASES=0
[[ "$RUN_30D" == "1" ]] && TOTAL_PHASES=$((TOTAL_PHASES + 1))
[[ "$RUN_7D" == "1" ]] && TOTAL_PHASES=$((TOTAL_PHASES + 1))
[[ "$RUN_3D" == "1" ]] && TOTAL_PHASES=$((TOTAL_PHASES + 1))
TOTAL_PHASES="${TOTAL_PHASES:-1}"
PROGRESS_FILTER="${PROGRESS_FILTER:-1}"
VARIANTS_PER_PHASE="${VARIANTS_PER_PHASE:-5}"
VARIANT_MODE="${VARIANT_MODE:-all}"
COUNTER_COUNT="${COUNTER_COUNT:-3}"
USE_PREVIOUS_PEAK="${USE_PREVIOUS_PEAK:-0}"

# Scale trial and iteration budgets for 24-hour run.
HYBRID_KAN="${HYBRID_KAN:-1}"
KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
DEEP_PRESETS_RUN="${DEEP_PRESETS_RUN:-tiny}"
HYBRID_KAN_PARTNERS="${HYBRID_KAN_PARTNERS:-deep:tiny}"
HYBRID_KAN_MODES="${HYBRID_KAN_MODES:-weighted}"
HYBRID_KAN_ALPHAS="${HYBRID_KAN_ALPHAS:-0.5}"
HYBRID_KAN_THRESHOLD="${HYBRID_KAN_THRESHOLD:-0.5}"
DEEP_DEVICE="${DEEP_DEVICE:-xpu}"
if [[ "$HYBRID_KAN" == "1" || "$HYBRID_KAN" == "true" || "$HYBRID_KAN" == "yes" ]]; then
  SEEDS_SPEC="${SEEDS_SPEC:-4:123}"
  TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-720}"
else
  SEEDS_SPEC="${SEEDS_SPEC:-4:243}"
  TRIALS_PER_VARIANT="${TRIALS_PER_VARIANT:-720}"
fi
MAX_ITER="${MAX_ITER:-1200}"
BEST_N="${BEST_N:-72}"
KEEP_BEST="${KEEP_BEST:-24}"
KEEP_WORST="${KEEP_WORST:-6}"
FUSION_INVERSE_WORST_N="${FUSION_INVERSE_WORST_N:-1}"
FINAL_EVAL_NEGATIVE_WEIGHT="${FINAL_EVAL_NEGATIVE_WEIGHT:-3.0}"
FINAL_EVAL_BEST_FRACTION="${FINAL_EVAL_BEST_FRACTION:-0.50}"
FINAL_EVAL_WORST_FRACTION="${FINAL_EVAL_WORST_FRACTION:-0.0}"
FINAL_EVAL_SHAPE_POWER="${FINAL_EVAL_SHAPE_POWER:-0.8}"
HYPER_PRETEST="${HYPER_PRETEST:-0}"
HYPER_PRETEST_TOP_N="${HYPER_PRETEST_TOP_N:-5}"
HYPER_PRETEST_SEEDS="${HYPER_PRETEST_SEEDS:-3}"
HYPER_PRETEST_EPOCHS="${HYPER_PRETEST_EPOCHS:-80}"
HYPER_PRETEST_FULL_EPOCHS="${HYPER_PRETEST_FULL_EPOCHS:-240}"
HYPER_PRETEST_DEVICE="${HYPER_PRETEST_DEVICE:-cpu}"

# Symmetric validation settings across cadences.
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



# Accelerator/device defaults.
export KAN_DEVICE="${KAN_DEVICE:-xpu}"
export DEVICE_MODE="${DEVICE_MODE:-$KAN_DEVICE}"
export KAN_QUIET="${KAN_QUIET:-1}"
# TEST: Impostato a 2 parallel jobs per sfruttare in parallelo la VRAM della Intel Arc con stabilità di memoria
export JOBS="${JOBS:-2}"
export ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-2}"

export METRIC_TEST_JOBS="${METRIC_TEST_JOBS:-1}"
export METRIC_TEST_CPU_JOBS="${METRIC_TEST_CPU_JOBS:-2}"
export CPU_SPEED_TEST="${CPU_SPEED_TEST:-0}"
export METRIC_TEST="${METRIC_TEST:-0}"
export METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-1}"
export METRIC_TEST_CPU_COMPARE_MARKER="${METRIC_TEST_CPU_COMPARE_MARKER:-$MACRO_ROOT/.metric_cpu_compare_done}"
export AUTO_DEVICE_SELECT="${AUTO_DEVICE_SELECT:-1}"
export AUTO_DEVICE_ENV="${AUTO_DEVICE_ENV:-$MACRO_ROOT/device_autoselect.env}"

# One-shot MI feature selection: build a reduced master first, then run metric/full train on it.
export FEATURE_PRESELECT="${FEATURE_PRESELECT:-1}"
export FEATURE_PRESELECT_REBUILD="${FEATURE_PRESELECT_REBUILD:-1}"
export FEATURE_SELECTION_K_BEST="${FEATURE_SELECTION_K_BEST-}"
export FEATURE_SELECTION_THRESHOLD="${FEATURE_SELECTION_THRESHOLD-}"
export FEATURE_SELECTION_PERCENTILE="${FEATURE_SELECTION_PERCENTILE-}"
if [[ -z "$FEATURE_SELECTION_K_BEST" && -z "$FEATURE_SELECTION_THRESHOLD" && -z "$FEATURE_SELECTION_PERCENTILE" ]]; then
  export FEATURE_SELECTION_PERCENTILE="0.15"
fi
export FEATURE_SELECTION_MIN_FEATURES="${FEATURE_SELECTION_MIN_FEATURES:-10}"
export FEATURE_SELECTION_MAX_FEATURES="${FEATURE_SELECTION_MAX_FEATURES:-50}"

RUN_PROFILE_NAME="${RUN_PROFILE_NAME:-manual}"
RUN_COMMAND_HINT="${RUN_COMMAND_HINT:-commands/run_japan_zone_mag79_30d_7d_3d_proximity_xpu_24h.sh}"
RUN_COMMAND_REASON="${RUN_COMMAND_REASON:-MI one-shot shortlist, then KAN/Deep full train.}"


# Rebuild from stable post-1903 start.
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

# Observer settings.
NASA_PLACE="${NASA_PLACE:-japan}"
NASA_AUTO_OBSERVER_FROM_TARGET="${NASA_AUTO_OBSERVER_FROM_TARGET:-1}"
NASA_OBSERVER_ALIAS="${NASA_OBSERVER_ALIAS:-target_centroid}"
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-3,4,20,27}"
BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.21 2.14 2.22 2.3 3.1}"
BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-4.1 4.31 4.32 4.33 4.34 4.4 5.11 5.22 6.11 6.14}"

# Horizontal-history settings.
HISTORY_MODE="${HISTORY_MODE:-fibonacci-gold}"
HISTORY_VALUE="${HISTORY_VALUE:-1280}"
HISTORY_ENABLE_SEISMIC="${HISTORY_ENABLE_SEISMIC:-1}"
HISTORY_ENABLE_ASTRO="${HISTORY_ENABLE_ASTRO:-1}"
HISTORY_ASTRO_BODIES="${HISTORY_ASTRO_BODIES:-301,599,101955,499,299,699,502,136199}"
HISTORY_ASTRO_FIELDS="${HISTORY_ASTRO_FIELDS:-RA_rate,DEC_rate,AZ,EL,delta,delta_rate,sunTargetPA,velocityPA,_slot4_min,_slot4_max,_slot4_mean}"

# Row filter and sparse sampling.
ROW_FILTER="${ROW_FILTER:-none}"
HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-random-sparse}"
HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE:-12}"
HISTORY_KEEP_NEIGHBOR_RECORDS="${HISTORY_KEEP_NEIGHBOR_RECORDS:-6}"
HISTORY_KEEP_RECENT_NEGATIVES="${HISTORY_KEEP_RECENT_NEGATIVES:-12}"

mkdir -p "$MACRO_ROOT"

PLAN_COMMON_ARGS=(
  --target-zones japan
  --counter-count "$COUNTER_COUNT"
  --variant-mode "$VARIANT_MODE"
  --proximity-deg 45
  --counter-min-events "$COUNTER_MIN_EVENTS"
  --src-events "$SRC_EVENTS"
  --min-mag 7.9
  --binary-threshold 7.9
  --device "$KAN_DEVICE"
  --out-of-region-mode neutralize-seismic
  --row-filter "$ROW_FILTER"
  --history-negative-sampling-mode "$HISTORY_NEGATIVE_SAMPLING_MODE"
  --rebuild-master "$REBUILD_MASTER"
  --nasa-daily-master-mode "$NASA_DAILY_MASTER_MODE"
  --nasa-slot-advanced-stats "$NASA_SLOT_ADVANCED_STATS"
  --extra-env "PYTHON_BIN=$PYTHON_BIN"
  --extra-env "KAN_DEVICE=$KAN_DEVICE"
  --extra-env "KAN_QUIET=$KAN_QUIET"
  --extra-env "JOBS=$JOBS"
  --extra-env "METRIC_TEST=$METRIC_TEST"
  --extra-env "METRIC_TEST_JOBS=$METRIC_TEST_JOBS"
  --extra-env "METRIC_TEST_CPU_COMPARE=$METRIC_TEST_CPU_COMPARE"
  --extra-env "METRIC_TEST_CPU_JOBS=$METRIC_TEST_CPU_JOBS"
  --extra-env "METRIC_TEST_CPU_COMPARE_MARKER=$METRIC_TEST_CPU_COMPARE_MARKER"
  --extra-env "AUTO_DEVICE_SELECT=$AUTO_DEVICE_SELECT"
  --extra-env "AUTO_DEVICE_ENV=$AUTO_DEVICE_ENV"
  --extra-env "FEATURE_PRESELECT=$FEATURE_PRESELECT"
  --extra-env "FEATURE_PRESELECT_REBUILD=$FEATURE_PRESELECT_REBUILD"
  --extra-env "FEATURE_SELECTION_K_BEST=$FEATURE_SELECTION_K_BEST"
  --extra-env "FEATURE_SELECTION_THRESHOLD=$FEATURE_SELECTION_THRESHOLD"
  --extra-env "FEATURE_SELECTION_PERCENTILE=$FEATURE_SELECTION_PERCENTILE"
  --extra-env "FEATURE_SELECTION_MIN_FEATURES=$FEATURE_SELECTION_MIN_FEATURES"
  --extra-env "FEATURE_SELECTION_MAX_FEATURES=$FEATURE_SELECTION_MAX_FEATURES"
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
  --extra-env "FUSION_INVERSE_WORST_N=$FUSION_INVERSE_WORST_N"
  --extra-env "FINAL_EVAL_NEGATIVE_WEIGHT=$FINAL_EVAL_NEGATIVE_WEIGHT"
  --extra-env "FINAL_EVAL_BEST_FRACTION=$FINAL_EVAL_BEST_FRACTION"
  --extra-env "FINAL_EVAL_WORST_FRACTION=$FINAL_EVAL_WORST_FRACTION"
  --extra-env "FINAL_EVAL_SHAPE_POWER=$FINAL_EVAL_SHAPE_POWER"
  --extra-env "HYPER_PRETEST=$HYPER_PRETEST"
  --extra-env "HYPER_PRETEST_TOP_N=$HYPER_PRETEST_TOP_N"
  --extra-env "HYPER_PRETEST_SEEDS=$HYPER_PRETEST_SEEDS"
  --extra-env "HYPER_PRETEST_EPOCHS=$HYPER_PRETEST_EPOCHS"
  --extra-env "HYPER_PRETEST_FULL_EPOCHS=$HYPER_PRETEST_FULL_EPOCHS"
  --extra-env "HYPER_PRETEST_DEVICE=$HYPER_PRETEST_DEVICE"
  --extra-env "KAN_PRESETS_RUN=$KAN_PRESETS_RUN"
  --extra-env "CPU_SPEED_TEST=0"
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
    --total-phases "$TOTAL_PHASES" \
    --variants "$VARIANTS_PER_PHASE" \
    --trials-per-variant "$TRIALS_PER_VARIANT"
  local macro_status=${PIPESTATUS[0]}
  set -e
  return "$macro_status"
}

cat > "$MACRO_ROOT/24H_RUN_SPEC.md" <<EOF
# Japan-zone M7.9+ XPU 24h Run

- Created: $(date -Is)
- Profile: \`$RUN_PROFILE_NAME\`
- Command hint: \`$RUN_COMMAND_HINT\`
- Macro root: \`$MACRO_ROOT\`
- 30d root: \`$ROOT_30D\`
- 7d root: \`$ROOT_7D\`
- 3d root: \`$ROOT_3D\`
- Run selection in maps: latest subrun per variant inside each phase root.
- Variant mode: \`$VARIANT_MODE\`; counter count=\`$COUNTER_COUNT\`.
- Estimated total runtime: about 24 hours on the current XPU machine.
- Budget: \`$TRIALS_PER_VARIANT\` trials/variant, \`$MAX_ITER\` max_iter.
- Validation: target events=\`$TARGET_EVENT_COUNT\`, validation events=\`$VALIDATION_EVENT_COUNT\`, context=\`$VALIDATION_PRE_RECORDS\`/\`$VALIDATION_POST_RECORDS\` records.
- Counter minimum events: \`$COUNTER_MIN_EVENTS\`.
- Out-of-region seismic handling: \`neutralize-seismic\`.
- Peak inheritance: \`$USE_PREVIOUS_PEAK\`
- Hybrid KAN: \`$HYBRID_KAN\`; deep presets=\`$DEEP_PRESETS_RUN\`;
  KAN presets=\`$KAN_PRESETS_RUN\`;
  partners=\`$HYBRID_KAN_PARTNERS\`; modes=\`$HYBRID_KAN_MODES\`;
  alphas=\`$HYBRID_KAN_ALPHAS\`.
- Feature preselect: \`$FEATURE_PRESELECT\`; k_best=\`${FEATURE_SELECTION_K_BEST:-none}\`;
  threshold=\`${FEATURE_SELECTION_THRESHOLD:-none}\`; percentile=\`${FEATURE_SELECTION_PERCENTILE:-none}\`;
  min/max=\`$FEATURE_SELECTION_MIN_FEATURES/$FEATURE_SELECTION_MAX_FEATURES\`.
- Metric pretest: \`$METRIC_TEST\`; CPU compare: \`$METRIC_TEST_CPU_COMPARE\`; cpu_jobs=\`$METRIC_TEST_CPU_JOBS\`;
  auto_select=\`$AUTO_DEVICE_SELECT\`; auto_env=\`$AUTO_DEVICE_ENV\`.
- Start date: \`$START_DATE\`
- Bodies primary: \`$BODY_PRIMARY_LEVELS\`
- Bodies secondary: \`$BODY_SECONDARY_LEVELS\`
- History bodies: \`$HISTORY_ASTRO_BODIES\`
- History fields: \`$HISTORY_ASTRO_FIELDS\`
EOF

cat > "$MACRO_ROOT/RUN_COMMAND_AND_FEATURE_POLICY.md" <<EOF
# Run Command And Feature Policy

- Created: $(date -Is)
- Profile: \`$RUN_PROFILE_NAME\`
- Macro root: \`$MACRO_ROOT\`
- Launcher command:

\`\`\`bash
$RUN_COMMAND_HINT
\`\`\`

## Why This Profile

$RUN_COMMAND_REASON

## Feature Selection

This run uses a one-shot MI preselect before the full train. The selector ranks
features by discrete mutual information on the training window, writes the full
ranking, materializes a reduced master CSV, and then KAN/Deep train on that
same reduced CSV.

Current knobs:

\`\`\`bash
FEATURE_PRESELECT=$FEATURE_PRESELECT
FEATURE_PRESELECT_REBUILD=$FEATURE_PRESELECT_REBUILD
FEATURE_SELECTION_K_BEST=${FEATURE_SELECTION_K_BEST:-}
FEATURE_SELECTION_THRESHOLD=${FEATURE_SELECTION_THRESHOLD:-}
FEATURE_SELECTION_PERCENTILE=${FEATURE_SELECTION_PERCENTILE:-}
FEATURE_SELECTION_MIN_FEATURES=$FEATURE_SELECTION_MIN_FEATURES
FEATURE_SELECTION_MAX_FEATURES=$FEATURE_SELECTION_MAX_FEATURES
\`\`\`

Policy:

- If \`FEATURE_SELECTION_K_BEST\` is set, it wins over percentile and threshold.
- The top-50 profile deliberately keeps a broader shortlist than top-10 because
  weak individual features can still be useful in combination for KAN/Deep.
- \`FEATURE_SELECTION_MIN_FEATURES\` and \`FEATURE_SELECTION_MAX_FEATURES\`
  are guardrails, not a combinatorial optimizer.
- The actual selected list is written per variant in
  \`feature_preselect_mi_ranking.csv\`, \`feature_preselect_manifest.json\`,
  and \`feature_preselect_report.md\`.

## Train Flow

\`\`\`bash
VARIANT_MODE=$VARIANT_MODE
COUNTER_COUNT=$COUNTER_COUNT
KAN_DEVICE=$KAN_DEVICE
DEEP_DEVICE=$DEEP_DEVICE
JOBS=$JOBS
ACCELERATOR_JOBS=$ACCELERATOR_JOBS
METRIC_TEST=$METRIC_TEST
METRIC_TEST_CPU_COMPARE=$METRIC_TEST_CPU_COMPARE
AUTO_DEVICE_SELECT=$AUTO_DEVICE_SELECT
SEEDS_SPEC=$SEEDS_SPEC
MAX_ITER=$MAX_ITER
BEST_N=$BEST_N
KEEP_BEST=$KEEP_BEST
KEEP_WORST=$KEEP_WORST
FUSION_INVERSE_WORST_N=$FUSION_INVERSE_WORST_N
FINAL_EVAL_NEGATIVE_WEIGHT=$FINAL_EVAL_NEGATIVE_WEIGHT
FINAL_EVAL_BEST_FRACTION=$FINAL_EVAL_BEST_FRACTION
FINAL_EVAL_WORST_FRACTION=$FINAL_EVAL_WORST_FRACTION
FINAL_EVAL_SHAPE_POWER=$FINAL_EVAL_SHAPE_POWER
\`\`\`

## Hyper Pretest

\`\`\`bash
HYPER_PRETEST=$HYPER_PRETEST
HYPER_PRETEST_TOP_N=$HYPER_PRETEST_TOP_N
HYPER_PRETEST_SEEDS=$HYPER_PRETEST_SEEDS
HYPER_PRETEST_EPOCHS=$HYPER_PRETEST_EPOCHS
HYPER_PRETEST_FULL_EPOCHS=$HYPER_PRETEST_FULL_EPOCHS
HYPER_PRETEST_DEVICE=$HYPER_PRETEST_DEVICE
\`\`\`

With \`METRIC_TEST=0\`, the run skips the short metric pretest and goes from
the MI shortlist directly to the full train.
EOF

echo "======================================================================"
echo " Japan-zone M7.9+ 30d + 7d + 3d proximity 24H XPU run"
echo " Macro root:       $MACRO_ROOT"
echo " Profile:          $RUN_PROFILE_NAME"
echo " Command hint:     $RUN_COMMAND_HINT"
echo " 30d root:         $ROOT_30D"
echo " 7d root:          $ROOT_7D"
echo " 3d root:          $ROOT_3D"
echo " Start date:       $START_DATE"
echo " Device:           $KAN_DEVICE jobs=$JOBS"
echo " Rebuild master:   $REBUILD_MASTER daily=$NASA_DAILY_MASTER_MODE"
echo " NASA retry:       workers=$MAX_WORKERS retries=$MAX_RETRIES sleep=$SLEEP_TIME"
echo " Bodies primary:   $BODY_PRIMARY_LEVELS"
echo " Bodies secondary: $BODY_SECONDARY_LEVELS"
echo " History bodies:   $HISTORY_ASTRO_BODIES"
echo " History fields:   $HISTORY_ASTRO_FIELDS"
echo " Sparse context:   mode=$HISTORY_NEGATIVE_SAMPLING_MODE per_pos=$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE neighbor=$HISTORY_KEEP_NEIGHBOR_RECORDS recent=$HISTORY_KEEP_RECENT_NEGATIVES"
echo " Validation:       target_events=$TARGET_EVENT_COUNT validation_events=$VALIDATION_EVENT_COUNT pre/post=$VALIDATION_PRE_RECORDS/$VALIDATION_POST_RECORDS recent_neg=$RECENT_VALIDATION_RANDOM_NEGATIVES"
echo " Counter min:      events=$COUNTER_MIN_EVENTS"
echo " Variant mode:     $VARIANT_MODE counters=$COUNTER_COUNT"
echo " OOR seismic:      neutralize-seismic"
echo " Peak inheritance: $USE_PREVIOUS_PEAK"
echo " Hybrid KAN:       enabled=$HYBRID_KAN deep=$DEEP_PRESETS_RUN partners='$HYBRID_KAN_PARTNERS' modes=$HYBRID_KAN_MODES alphas=$HYBRID_KAN_ALPHAS"
echo " KAN presets:      $KAN_PRESETS_RUN"
echo " Feature preselect: enabled=$FEATURE_PRESELECT k_best=${FEATURE_SELECTION_K_BEST:-none} threshold=${FEATURE_SELECTION_THRESHOLD:-none} percentile=${FEATURE_SELECTION_PERCENTILE:-none} min/max=$FEATURE_SELECTION_MIN_FEATURES/$FEATURE_SELECTION_MAX_FEATURES"
echo " Metric pretest:    enabled=$METRIC_TEST cpu_compare=$METRIC_TEST_CPU_COMPARE cpu_jobs=$METRIC_TEST_CPU_JOBS auto_select=$AUTO_DEVICE_SELECT"
echo " KAN budget:       seeds=$SEEDS_SPEC max_iter=$MAX_ITER trials/variant~$TRIALS_PER_VARIANT"
echo " Expected runtime: about 24 hours total on the current XPU machine."
echo "======================================================================"

# 30d phase planning (always runs first, with static default dates or custom overrides)
FORECAST_START_30D="${FORECAST_START_30D:-2026-04-30}"
FORECAST_END_30D="${FORECAST_END_30D:-2026-12-31}"
EVENTS_END_30D="${EVENTS_END_30D:-2026-04-29}"

make_plan_if_needed \
  "30d" \
  "$ROOT_30D" \
  "japan-zone-mag79plus-24h-${RUN_STAMP}-30d" \
  "commands/run_world_mag79_japan_30d_may_dec_horizontal_binary_xpu.sh" \
  "30d" \
  "$FORECAST_START_30D" \
  "$FORECAST_END_30D" \
  "$EVENTS_END_30D" \
  "May-Dec 2026, 30d 24H XPU richer horizontal history" \
  "180d" \
  "180d"

ACTIVE_PHASE_NO=0

if [[ "$RUN_30D" == "1" ]]; then
  ACTIVE_PHASE_NO=$((ACTIVE_PHASE_NO + 1))
  echo
  echo "======================================================================"
  echo "[$ACTIVE_PHASE_NO/$TOTAL_PHASES] Starting 30d 24H run"
  echo "======================================================================"
  run_macro_with_progress "$ACTIVE_PHASE_NO" "30d-24h" "$ROOT_30D/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
fi

# 7d phase planning & execution
if [[ "$RUN_7D" == "1" ]]; then
  FORECAST_START_7D="${FORECAST_START_7D:-2026-07-27}"
  FORECAST_END_7D="${FORECAST_END_7D:-2026-10-05}"
  EVENTS_END_7D="${EVENTS_END_7D:-2026-07-26}"

  if [[ "$USE_PREVIOUS_PEAK" == "1" || "$USE_PREVIOUS_PEAK" == "true" ]]; then
    echo
    echo "======================================================================"
    echo "[peak-inheritance] Resolving peak of 30d run for 7d focus window..."
    echo "======================================================================"
    # Try resolving peak from ROOT_30D
    if eval $("$PYTHON_BIN" inherit_forecast_peak.py --prev-phase-dir "$ROOT_30D"); then
      FORECAST_START_7D="$FORECAST_START"
      FORECAST_END_7D="$FORECAST_END"
      EVENTS_END_7D="$EVENTS_END"
      echo "[peak-inheritance] Inherited dates: start=$FORECAST_START_7D, end=$FORECAST_END_7D, events_end=$EVENTS_END_7D"
    else
      echo "[peak-inheritance] Warning: peak inheritance failed. Falling back to default dates."
    fi
  fi

  make_plan_if_needed \
    "7d" \
    "$ROOT_7D" \
    "japan-zone-mag79plus-24h-${RUN_STAMP}-7d" \
    "commands/run_world_mag79_japan_aug_sep_7d_horizontal_binary_xpu.sh" \
    "7d" \
    "$FORECAST_START_7D" \
    "$FORECAST_END_7D" \
    "$EVENTS_END_7D" \
    "Aug-Sep 2026, 7d 24H XPU richer horizontal history" \
    "42d" \
    "42d"

  ACTIVE_PHASE_NO=$((ACTIVE_PHASE_NO + 1))
  echo
  echo "======================================================================"
  echo "[$ACTIVE_PHASE_NO/$TOTAL_PHASES] Starting 7d 24H run"
  echo "======================================================================"
  run_macro_with_progress "$ACTIVE_PHASE_NO" "7d-24h" "$ROOT_7D/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
fi

# 3d phase planning & execution
if [[ "$RUN_3D" == "1" ]]; then
  FORECAST_START_3D="${FORECAST_START_3D:-2026-07-31}"
  FORECAST_END_3D="${FORECAST_END_3D:-2026-09-02}"
  EVENTS_END_3D="${EVENTS_END_3D:-2026-07-30}"

  if [[ "$USE_PREVIOUS_PEAK" == "1" || "$USE_PREVIOUS_PEAK" == "true" ]]; then
    echo
    echo "======================================================================"
    echo "[peak-inheritance] Resolving peak of 7d run for 3d focus window..."
    echo "======================================================================"
    # Try resolving peak from ROOT_7D
    if eval $("$PYTHON_BIN" inherit_forecast_peak.py --prev-phase-dir "$ROOT_7D"); then
      FORECAST_START_3D="$FORECAST_START"
      FORECAST_END_3D="$FORECAST_END"
      EVENTS_END_3D="$EVENTS_END"
      echo "[peak-inheritance] Inherited dates: start=$FORECAST_START_3D, end=$FORECAST_END_3D, events_end=$EVENTS_END_3D"
    else
      echo "[peak-inheritance] Warning: peak inheritance failed. Falling back to default dates."
    fi
  fi

  make_plan_if_needed \
    "3d" \
    "$ROOT_3D" \
    "japan-zone-mag79plus-24h-${RUN_STAMP}-3d" \
    "commands/run_world_mag79_japan_aug_3d_horizontal_binary_xpu.sh" \
    "3d" \
    "$FORECAST_START_3D" \
    "$FORECAST_END_3D" \
    "$EVENTS_END_3D" \
    "Aug 2026, 3d 24H XPU richer horizontal history" \
    "18d" \
    "18d"

  ACTIVE_PHASE_NO=$((ACTIVE_PHASE_NO + 1))
  echo
  echo "======================================================================"
  echo "[$ACTIVE_PHASE_NO/$TOTAL_PHASES] Starting 3d 24H run"
  echo "======================================================================"
  run_macro_with_progress "$ACTIVE_PHASE_NO" "3d-24h" "$ROOT_3D/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
fi

echo
echo "======================================================================"
echo "[ensemble] Running automatic multi-resolution fusion..."
echo "======================================================================"
# Run the ensemble script using the python environment, with fallback to local venv
if ! "$PYTHON_BIN" generate_ensemble.py --run-dir "$MACRO_ROOT"; then
  echo "[ensemble] Fallback to local .venv python..."
  .venv/bin/python generate_ensemble.py --run-dir "$MACRO_ROOT"
fi

echo
echo "======================================================================"
echo " Japan-zone M7.9+ 24H run complete"
echo " Macro root: $MACRO_ROOT"
echo " 30d maps:   $ROOT_30D/maps"
echo " 7d maps:    $ROOT_7D/maps"
echo " 3d maps:    $ROOT_3D/maps"
echo " Fusion:     $MACRO_ROOT/fusion"
echo "======================================================================"


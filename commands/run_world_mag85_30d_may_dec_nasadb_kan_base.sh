#!/usr/bin/env bash
# Shared worldwide M8.5+ 30d traditional nasaDb KAN forecast.
#
# Uses the legacy/fast nasaDb.py path with visible progress:
# nasaDb.py -> add USGS core -> convert astrofmt -> quantize -> KAN train.
set -euo pipefail

cd "$(dirname "$0")/.."

METRIC_TEST="${METRIC_TEST:-1}"
CLI_BINARY_TARGET_COL=""
CLI_TARGET_COL=""
CLI_BINARY_SOURCE_COL=""
CLI_BINARY_THRESHOLD=""
CLI_BINARY_OPERATOR=""
CLI_ROW_FILTER=""
CLI_FORECAST_FILTER=""
CLI_ZONES_CSV=""
CLI_TARGET_REGION=""
CLI_TARGET_ZONES=""
CLI_OUT_OF_REGION_MODE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --metric-test|-metric-test)
      METRIC_TEST=1
      shift
      ;;
    --no-metric-test)
      METRIC_TEST=0
      shift
      ;;
    --binary-target-col)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --binary-target-col" >&2; exit 1; }
      CLI_BINARY_TARGET_COL="$2"
      shift 2
      ;;
    --target-col)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --target-col" >&2; exit 1; }
      CLI_TARGET_COL="$2"
      shift 2
      ;;
    --binary-source-col)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --binary-source-col" >&2; exit 1; }
      CLI_BINARY_SOURCE_COL="$2"
      shift 2
      ;;
    --binary-threshold)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --binary-threshold" >&2; exit 1; }
      CLI_BINARY_THRESHOLD="$2"
      shift 2
      ;;
    --binary-operator)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --binary-operator" >&2; exit 1; }
      CLI_BINARY_OPERATOR="$2"
      shift 2
      ;;
    --row-filter)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --row-filter" >&2; exit 1; }
      CLI_ROW_FILTER="$2"
      shift 2
      ;;
    --forecast-filter)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --forecast-filter" >&2; exit 1; }
      CLI_FORECAST_FILTER="$2"
      shift 2
      ;;
    --zones-csv)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --zones-csv" >&2; exit 1; }
      CLI_ZONES_CSV="$2"
      shift 2
      ;;
    --target-region)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --target-region" >&2; exit 1; }
      CLI_TARGET_REGION="$2"
      shift 2
      ;;
    --target-zones)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --target-zones" >&2; exit 1; }
      CLI_TARGET_ZONES="$2"
      shift 2
      ;;
    --out-of-region-mode)
      [[ $# -ge 2 ]] || { echo "[ERROR] Missing value for --out-of-region-mode" >&2; exit 1; }
      CLI_OUT_OF_REGION_MODE="$2"
      shift 2
      ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      echo "        Supported: --metric-test, -metric-test, --no-metric-test," >&2
      echo "                   --binary-target-col NAME, --target-col NAME," >&2
      echo "                   --binary-source-col NAME, --binary-threshold VALUE," >&2
      echo "                   --binary-operator OP, --row-filter EXPR, --forecast-filter EXPR," >&2
      echo "                   --zones-csv PATH, --target-region EXPR_OR_ZONES," >&2
      echo "                   --target-zones ZONES, --out-of-region-mode MODE" >&2
      echo "        Metric pretest runs by default; use --no-metric-test to skip it." >&2
      exit 1
      ;;
  esac
done

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"
SRC_EVENTS="${SRC_EVENTS:-$ASTRO_ROOT/DB/WORLD-MAG8.5-1900-2025-09-30/earthquakes.RAW.csv}"
RUN_LABEL="${RUN_LABEL:-world-mag85plus-30d-may-dec-nasadb-kan}"
OUT_DIR="${OUT_DIR:-$ASTRO_ROOT/DB/$RUN_LABEL}"
PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
FUSION_TITLE="${FUSION_TITLE:-Worldwide M8.5+ May-Dec 2026 30d traditional nasaDb KAN forecast}"
FUSION_RANK_MODE="${FUSION_RANK_MODE:-validation-quality}"
FUSION_INVERSE_WORST_N="${FUSION_INVERSE_WORST_N:-1}"

MIN_MAG="${MIN_MAG:-8.5}"
START_DATE="${START_DATE:-1903-01-01}"
EVENTS_END_DATE="${EVENTS_END_DATE:-2026-04-29}"
FORECAST_START="${FORECAST_START:-2026-04-30}"
FORECAST_END="${FORECAST_END:-2026-12-31}"
FORECAST_LABEL="${FORECAST_LABEL:-May-Dec 2026}"
STEP_INTERVAL="${STEP_INTERVAL:-30d}"
TIME_BEFORE="${TIME_BEFORE:-180d}"
TIME_AFTER="${TIME_AFTER:-180d}"
NASA_DAILY_MASTER_MODE="${NASA_DAILY_MASTER_MODE:-1}"
NASA_SLOT_AGGREGATION="${NASA_SLOT_AGGREGATION:-median}"
NASA_SLOT_ADVANCED_STATS="${NASA_SLOT_ADVANCED_STATS:-1}"
NASA_SLOT_ADVANCED_GROUP_SIZE="${NASA_SLOT_ADVANCED_GROUP_SIZE:-4}"

NASA_PLACE="${NASA_PLACE:-earthFull}"
EPHEMERIDES_FIELDS="${EPHEMERIDES_FIELDS:-1,2,3,4,13,19,31,43}"
BODY_PRIMARY_LEVELS="${BODY_PRIMARY_LEVELS:-1.0 2.11 2.12 2.14 2.21 2.22 2.3 3.1}"
BODY_SECONDARY_LEVELS="${BODY_SECONDARY_LEVELS:-4.1 4.31 4.32 4.33 4.34 4.4 5.11 5.22 6.11 6.14 6.21 6.22}"
OBSERVER_LEVELS="${OBSERVER_LEVELS:-1.0}"
NASA_AUTO_OBSERVER_FROM_TARGET="${NASA_AUTO_OBSERVER_FROM_TARGET:-0}"
NASA_OBSERVER_GEO="${NASA_OBSERVER_GEO:-}"
NASA_OBSERVER_ALIAS="${NASA_OBSERVER_ALIAS:-target_centroid}"
MAX_WORKERS="${MAX_WORKERS:-4}"
SLEEP_TIME="${SLEEP_TIME:-1.0}"
MAX_RETRIES="${MAX_RETRIES:-4}"
REBUILD_MASTER="${REBUILD_MASTER:-1}"
QUANT_BINS="${QUANT_BINS:-4}"

ENABLE_BINARY_TARGET="${ENABLE_BINARY_TARGET:-0}"
ENABLE_HORIZONTAL_HISTORY="${ENABLE_HORIZONTAL_HISTORY:-0}"
HISTORY_MODE="${HISTORY_MODE:-fibonacci-gold}"
HISTORY_VALUE="${HISTORY_VALUE:-1280}"
HISTORY_SPACER_DAYS="${HISTORY_SPACER_DAYS:-0}"
HISTORY_ENABLE_SEISMIC="${HISTORY_ENABLE_SEISMIC:-1}"
HISTORY_ENABLE_ASTRO="${HISTORY_ENABLE_ASTRO:-1}"
HISTORY_ASTRO_BODIES="${HISTORY_ASTRO_BODIES:-301,599,99942}"
HISTORY_ASTRO_FIELDS="${HISTORY_ASTRO_FIELDS:-RA,DEC,r,r_rate,ObsEclLon,ObsEclLat}"
HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-none}"
HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE:-8}"
HISTORY_RANDOM_NEGATIVE_SEED="${HISTORY_RANDOM_NEGATIVE_SEED:-20260608}"
HISTORY_KEEP_NEIGHBOR_RECORDS="${HISTORY_KEEP_NEIGHBOR_RECORDS:-2}"
HISTORY_KEEP_RECENT_NEGATIVES="${HISTORY_KEEP_RECENT_NEGATIVES:-6}"
DEFAULT_BINARY_TARGET_COL="target"
BINARY_TARGET_COL="${BINARY_TARGET_COL:-target}"
BINARY_SOURCE_COL="${BINARY_SOURCE_COL:-mag}"
BINARY_THRESHOLD="${BINARY_THRESHOLD:-}"
BINARY_OPERATOR="${BINARY_OPERATOR:->=}"
ROW_FILTER="${ROW_FILTER:-auto}"
FORECAST_FILTER="${FORECAST_FILTER:-none}"
ZONES_CSV="${ZONES_CSV:-$PWD/resources/seismic_zones.csv}"
TARGET_REGION="${TARGET_REGION:-}"
TARGET_ZONES="${TARGET_ZONES:-}"
OUT_OF_REGION_MODE="${OUT_OF_REGION_MODE:-keep}"
FORECAST_TARGET_VALUE="${FORECAST_TARGET_VALUE:-0}"
TARGET_COL="${TARGET_COL:-mag}"
SKIP_COLS_LIST="${SKIP_COLS_LIST:-date,depth,latitude,longitude}"
METRIC_TARGET_THRESHOLD="${METRIC_TARGET_THRESHOLD:-0.1}"
METRIC_PREDICTION_THRESHOLD="${METRIC_PREDICTION_THRESHOLD:-0.5}"
TARGET_WINDOW_THRESHOLD="${TARGET_WINDOW_THRESHOLD:-$METRIC_TARGET_THRESHOLD}"

if [[ -n "$CLI_BINARY_TARGET_COL" ]]; then
  OLD_BINARY_TARGET_COL="$BINARY_TARGET_COL"
  BINARY_TARGET_COL="$CLI_BINARY_TARGET_COL"
  if [[ -z "$CLI_TARGET_COL" && ( "$TARGET_COL" == "$OLD_BINARY_TARGET_COL" || "$TARGET_COL" == "$DEFAULT_BINARY_TARGET_COL" || "$TARGET_COL" == "mag" ) ]]; then
    TARGET_COL="$BINARY_TARGET_COL"
  fi
fi
if [[ -n "$CLI_BINARY_SOURCE_COL" ]]; then
  BINARY_SOURCE_COL="$CLI_BINARY_SOURCE_COL"
fi
if [[ -n "$CLI_BINARY_THRESHOLD" ]]; then
  BINARY_THRESHOLD="$CLI_BINARY_THRESHOLD"
fi
if [[ -n "$CLI_BINARY_OPERATOR" ]]; then
  BINARY_OPERATOR="$CLI_BINARY_OPERATOR"
fi
if [[ -n "$CLI_ROW_FILTER" ]]; then
  ROW_FILTER="$CLI_ROW_FILTER"
fi
if [[ -n "$CLI_FORECAST_FILTER" ]]; then
  FORECAST_FILTER="$CLI_FORECAST_FILTER"
fi
if [[ -n "$CLI_ZONES_CSV" ]]; then
  ZONES_CSV="$CLI_ZONES_CSV"
fi
if [[ -n "$CLI_TARGET_REGION" ]]; then
  TARGET_REGION="$CLI_TARGET_REGION"
fi
if [[ -n "$CLI_TARGET_ZONES" ]]; then
  TARGET_ZONES="$CLI_TARGET_ZONES"
fi
if [[ -n "$CLI_OUT_OF_REGION_MODE" ]]; then
  OUT_OF_REGION_MODE="$CLI_OUT_OF_REGION_MODE"
fi
if [[ -n "$CLI_TARGET_COL" ]]; then
  TARGET_COL="$CLI_TARGET_COL"
fi

if [[ "$ENABLE_HORIZONTAL_HISTORY" == "1" || "$ENABLE_HORIZONTAL_HISTORY" == "true" || "$ENABLE_HORIZONTAL_HISTORY" == "yes" ]]; then
  ENABLE_BINARY_TARGET=1
fi
if [[ "$ENABLE_BINARY_TARGET" == "1" || "$ENABLE_BINARY_TARGET" == "true" || "$ENABLE_BINARY_TARGET" == "yes" ]]; then
  if [[ -n "$CLI_TARGET_COL" && -z "$CLI_BINARY_SOURCE_COL" && "$CLI_TARGET_COL" != "$BINARY_TARGET_COL" ]]; then
    case "$CLI_TARGET_COL" in
      mag|latitude|longitude|depth)
        BINARY_SOURCE_COL="$CLI_TARGET_COL"
        TARGET_COL="$BINARY_TARGET_COL"
        ;;
    esac
  fi
  if [[ "$TARGET_COL" == "mag" ]]; then
    TARGET_COL="$BINARY_TARGET_COL"
  fi
  if [[ "$SKIP_COLS_LIST" == "date,depth,latitude,longitude" ]]; then
    SKIP_COLS_LIST="date,mag,depth,latitude,longitude"
  fi
  if [[ "$BINARY_TARGET_COL" != "$TARGET_COL" ]]; then
    case ",$SKIP_COLS_LIST," in
      *",$BINARY_TARGET_COL,"*) ;;
      *) SKIP_COLS_LIST="$SKIP_COLS_LIST,$BINARY_TARGET_COL" ;;
    esac
  fi
  if [[ "$METRIC_TARGET_THRESHOLD" == "0.1" ]]; then
    METRIC_TARGET_THRESHOLD=0.5
  fi
  if [[ "$TARGET_WINDOW_THRESHOLD" == "0.1" ]]; then
    TARGET_WINDOW_THRESHOLD=0.5
  fi
fi

KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
KAN_DEVICE="${KAN_DEVICE:-cpu}"
KAN_QUIET="${KAN_QUIET:-1}"
HYBRID_KAN="${HYBRID_KAN:-0}"
DEEP_PRESETS_RUN="${DEEP_PRESETS_RUN:-tiny,small}"
DEEP_PRESET_CONFIGS_JSON="${DEEP_PRESET_CONFIGS_JSON:-}"
HYBRID_KAN_PARTNERS="${HYBRID_KAN_PARTNERS:-deep:tiny,deep:small}"
HYBRID_KAN_MODES="${HYBRID_KAN_MODES:-and,weighted}"
HYBRID_KAN_ALPHAS="${HYBRID_KAN_ALPHAS:-0.5}"
HYBRID_KAN_THRESHOLD="${HYBRID_KAN_THRESHOLD:-0.5}"
DEEP_DEVICE="${DEEP_DEVICE:-auto}"
SEEDS_SPEC="${SEEDS_SPEC:-4:24}"
MAX_ITER="${MAX_ITER:-1200}"
JOBS="${JOBS:-3}"
BEST_N="${BEST_N:-36}"
KEEP_BEST="${KEEP_BEST:-8}"
KEEP_WORST="${KEEP_WORST:-3}"
FINAL_EVAL_NEGATIVE_WEIGHT="${FINAL_EVAL_NEGATIVE_WEIGHT:-3.0}"
FINAL_EVAL_BEST_FRACTION="${FINAL_EVAL_BEST_FRACTION:-0.50}"
FINAL_EVAL_WORST_FRACTION="${FINAL_EVAL_WORST_FRACTION:-0.0}"
FINAL_EVAL_SHAPE_POWER="${FINAL_EVAL_SHAPE_POWER:-0.8}"
METRIC_TEST_TMP_DIR="${METRIC_TEST_TMP_DIR:-/tmp/dlvswave_metric_tests}"
METRIC_TEST_PRESETS="${METRIC_TEST_PRESETS:-tiny,small,wide}"
METRIC_TEST_SEEDS="${METRIC_TEST_SEEDS:-4:4}"
METRIC_TEST_MAX_ITER="${METRIC_TEST_MAX_ITER:-180}"
METRIC_TEST_BEST_N="${METRIC_TEST_BEST_N:-12}"
METRIC_TEST_KEEP_BEST="${METRIC_TEST_KEEP_BEST:-4}"
METRIC_TEST_JOBS="${METRIC_TEST_JOBS:-$JOBS}"
METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-0}"
METRIC_TEST_CPU_JOBS="${METRIC_TEST_CPU_JOBS:-6}"
METRIC_TEST_CPU_COMPARE_ONCE="${METRIC_TEST_CPU_COMPARE_ONCE:-1}"
METRIC_TEST_CPU_COMPARE_MARKER="${METRIC_TEST_CPU_COMPARE_MARKER:-}"
AUTO_DEVICE_SELECT="${AUTO_DEVICE_SELECT:-0}"
AUTO_DEVICE_ENV="${AUTO_DEVICE_ENV:-}"
FEATURE_PRESELECT="${FEATURE_PRESELECT:-1}"
FEATURE_PRESELECT_REBUILD="${FEATURE_PRESELECT_REBUILD:-1}"
HYPER_PRETEST="${HYPER_PRETEST:-0}"
HYPER_PRETEST_PY="${HYPER_PRETEST_PY:-$PWD/select_deep_hyperparams.py}"
HYPER_PRETEST_TOP_N="${HYPER_PRETEST_TOP_N:-5}"
HYPER_PRETEST_SEEDS="${HYPER_PRETEST_SEEDS:-3}"
HYPER_PRETEST_EPOCHS="${HYPER_PRETEST_EPOCHS:-80}"
HYPER_PRETEST_FULL_EPOCHS="${HYPER_PRETEST_FULL_EPOCHS:-240}"
HYPER_PRETEST_DEVICE="${HYPER_PRETEST_DEVICE:-cpu}"

TARGET_EVENT_COUNT="${TARGET_EVENT_COUNT:-2}"
VALIDATION_EVENT_COUNT="${VALIDATION_EVENT_COUNT:-2}"
VALIDATION_PRE_RECORDS="${VALIDATION_PRE_RECORDS:-2}"
VALIDATION_POST_RECORDS="${VALIDATION_POST_RECORDS:-2}"
VALIDATION_MAX_LOOKBACK_RECORDS="${VALIDATION_MAX_LOOKBACK_RECORDS:-1800}"
RECENT_VALIDATION_RANDOM_NEGATIVES="${RECENT_VALIDATION_RANDOM_NEGATIVES:-12}"
RECENT_VALIDATION_RANDOM_SEED="${RECENT_VALIDATION_RANDOM_SEED:-20260608}"

FILTER_EVENTS_PY="${FILTER_EVENTS_PY:-$PWD/filter_earthquake_events.py}"
ADD_USGS_PY="${ADD_USGS_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/add_usgs_core_columns_to_master.py}"
CONV_PY="${CONV_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/convert_astro_columns_to_standard.py}"
QUANT_PY="${QUANT_PY:-$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py}"
SANITIZE_PY="${SANITIZE_PY:-$PWD/sanitize_numeric_master.py}"
FUSION_PY="${FUSION_PY:-$PWD/kan_forecast_strength_fusion.py}"
AUGMENT_HISTORY_PY="${AUGMENT_HISTORY_PY:-$PWD/augment_horizontal_history_master.py}"
AGGREGATE_NASA_PY="${AGGREGATE_NASA_PY:-$PWD/aggregate_nasadb_daily_master.py}"
FEATURE_PRESELECT_PY="${FEATURE_PRESELECT_PY:-$PWD/select_mi_feature_master.py}"

[[ -x "$PYTHON_BIN" ]] || { echo "[ERROR] Python not executable: $PYTHON_BIN" >&2; exit 1; }
[[ -f "$SRC_EVENTS" ]] || { echo "[ERROR] SRC_EVENTS not found: $SRC_EVENTS" >&2; exit 1; }
[[ -f "$ASTRO_ROOT/nasaDb.py" ]] || { echo "[ERROR] nasaDb.py not found: $ASTRO_ROOT/nasaDb.py" >&2; exit 1; }
[[ -f "$FILTER_EVENTS_PY" ]] || { echo "[ERROR] FILTER_EVENTS_PY not found: $FILTER_EVENTS_PY" >&2; exit 1; }
[[ -f "$ADD_USGS_PY" ]] || { echo "[ERROR] ADD_USGS_PY not found: $ADD_USGS_PY" >&2; exit 1; }
[[ -f "$CONV_PY" ]] || { echo "[ERROR] CONV_PY not found: $CONV_PY" >&2; exit 1; }
[[ -f "$QUANT_PY" ]] || { echo "[ERROR] QUANT_PY not found: $QUANT_PY" >&2; exit 1; }
[[ -f "$SANITIZE_PY" ]] || { echo "[ERROR] SANITIZE_PY not found: $SANITIZE_PY" >&2; exit 1; }
[[ -f "$FUSION_PY" ]] || { echo "[ERROR] FUSION_PY not found: $FUSION_PY" >&2; exit 1; }
[[ -f "$AUGMENT_HISTORY_PY" ]] || { echo "[ERROR] AUGMENT_HISTORY_PY not found: $AUGMENT_HISTORY_PY" >&2; exit 1; }
[[ -f "$AGGREGATE_NASA_PY" ]] || { echo "[ERROR] AGGREGATE_NASA_PY not found: $AGGREGATE_NASA_PY" >&2; exit 1; }
[[ -f "$FEATURE_PRESELECT_PY" ]] || { echo "[ERROR] FEATURE_PRESELECT_PY not found: $FEATURE_PRESELECT_PY" >&2; exit 1; }
if [[ "$HYPER_PRETEST" == "1" || "$HYPER_PRETEST" == "true" || "$HYPER_PRETEST" == "yes" ]]; then
  [[ -f "$HYPER_PRETEST_PY" ]] || { echo "[ERROR] HYPER_PRETEST_PY not found: $HYPER_PRETEST_PY" >&2; exit 1; }
fi

mkdir -p "$OUT_DIR"
LOG_FILE="${LOG_FILE:-$OUT_DIR/${RUN_LABEL}.log}"
DB_FILE="${DB_FILE:-$OUT_DIR/${RUN_LABEL}.db}"
EVENTS_FILTERED="$OUT_DIR/earthquakes_world_mag85plus_train_until_${EVENTS_END_DATE}.RAW.csv"
NASA_MASTER_DAILY="$OUT_DIR/nasa_master_focus_daily_1d.csv"
NASA_MASTER="$OUT_DIR/nasa_master_focus_sparse.csv"
MASTER_CORE="$OUT_DIR/master_with_usgs_core.csv"
FLOAT_MASTER="$OUT_DIR/master_with_usgs_core_astrofmt_float.csv"
HISTORY_FLOAT_MASTER="$OUT_DIR/master_with_usgs_core_astrofmt_horizontal_history_float.csv"
MASTER="$OUT_DIR/master_with_usgs_core_astrofmt.csv"
PRESELECT_MASTER="$OUT_DIR/master_with_usgs_core_astrofmt.mi_features.csv"
PRESELECT_RANKING="$OUT_DIR/feature_preselect_mi_ranking.csv"
PRESELECT_MANIFEST="$OUT_DIR/feature_preselect_manifest.json"
PRESELECT_REPORT="$OUT_DIR/feature_preselect_report.md"
HYPER_PRETEST_CSV="$OUT_DIR/deep_hyper_pretest_ranking.csv"
HYPER_PRETEST_JSON="$OUT_DIR/deep_hyper_pretest_manifest.json"
HYPER_PRESET_JSON="$OUT_DIR/deep_hyper_selected_presets.json"

if [[ "$NASA_DAILY_MASTER_MODE" == "1" || "$NASA_DAILY_MASTER_MODE" == "true" || "$NASA_DAILY_MASTER_MODE" == "yes" ]]; then
  NASA_FETCH_STEP_INTERVAL="1d"
  NASA_FETCH_START_DATE="$START_DATE"
  NASA_FETCH_END_DATE="$FORECAST_END"
  NASA_FETCH_TIME_BEFORE="0d"
  NASA_FETCH_TIME_AFTER="0d"
else
  NASA_FETCH_STEP_INTERVAL="$STEP_INTERVAL"
  NASA_FETCH_START_DATE="$FORECAST_START"
  NASA_FETCH_END_DATE="$FORECAST_END"
  NASA_FETCH_TIME_BEFORE="$TIME_BEFORE"
  NASA_FETCH_TIME_AFTER="$TIME_AFTER"
fi

: > "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

cat > "$OUT_DIR/RUN_THIS_PIPELINE.sh" <<EOF
#!/usr/bin/env bash
cd "$(pwd)"
RUN_LABEL="$RUN_LABEL" \\
OUT_DIR="$OUT_DIR" \\
FUSION_TITLE="$FUSION_TITLE" \\
FUSION_RANK_MODE="$FUSION_RANK_MODE" \\
FUSION_INVERSE_WORST_N="$FUSION_INVERSE_WORST_N" \\
PYTHON_BIN="$PYTHON_BIN" KAN_DEVICE="$KAN_DEVICE" KAN_QUIET="$KAN_QUIET" JOBS="$JOBS" \\
HYBRID_KAN="$HYBRID_KAN" DEEP_PRESETS_RUN="$DEEP_PRESETS_RUN" DEEP_DEVICE="$DEEP_DEVICE" \\
HYBRID_KAN_PARTNERS="$HYBRID_KAN_PARTNERS" HYBRID_KAN_MODES="$HYBRID_KAN_MODES" \\
HYBRID_KAN_ALPHAS="$HYBRID_KAN_ALPHAS" HYBRID_KAN_THRESHOLD="$HYBRID_KAN_THRESHOLD" \\
BODY_SECONDARY_LEVELS="$BODY_SECONDARY_LEVELS" \\
NASA_PLACE="$NASA_PLACE" OBSERVER_LEVELS="$OBSERVER_LEVELS" \\
NASA_AUTO_OBSERVER_FROM_TARGET="$NASA_AUTO_OBSERVER_FROM_TARGET" \\
NASA_OBSERVER_GEO="$NASA_OBSERVER_GEO" NASA_OBSERVER_ALIAS="$NASA_OBSERVER_ALIAS" \\
ENABLE_BINARY_TARGET="$ENABLE_BINARY_TARGET" ENABLE_HORIZONTAL_HISTORY="$ENABLE_HORIZONTAL_HISTORY" \\
HISTORY_MODE="$HISTORY_MODE" HISTORY_VALUE="$HISTORY_VALUE" HISTORY_SPACER_DAYS="$HISTORY_SPACER_DAYS" \\
HISTORY_ENABLE_SEISMIC="$HISTORY_ENABLE_SEISMIC" HISTORY_ENABLE_ASTRO="$HISTORY_ENABLE_ASTRO" \\
HISTORY_ASTRO_BODIES="$HISTORY_ASTRO_BODIES" HISTORY_ASTRO_FIELDS="$HISTORY_ASTRO_FIELDS" \\
HISTORY_NEGATIVE_SAMPLING_MODE="$HISTORY_NEGATIVE_SAMPLING_MODE" \\
HISTORY_RANDOM_NEGATIVES_PER_POSITIVE="$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE" \\
HISTORY_KEEP_NEIGHBOR_RECORDS="$HISTORY_KEEP_NEIGHBOR_RECORDS" HISTORY_KEEP_RECENT_NEGATIVES="$HISTORY_KEEP_RECENT_NEGATIVES" \\
BINARY_TARGET_COL="$BINARY_TARGET_COL" BINARY_SOURCE_COL="$BINARY_SOURCE_COL" \\
BINARY_THRESHOLD="$BINARY_THRESHOLD" BINARY_OPERATOR="$BINARY_OPERATOR" \\
ROW_FILTER="$ROW_FILTER" FORECAST_FILTER="$FORECAST_FILTER" \\
ZONES_CSV="$ZONES_CSV" TARGET_REGION="$TARGET_REGION" TARGET_ZONES="$TARGET_ZONES" \\
OUT_OF_REGION_MODE="$OUT_OF_REGION_MODE" \\
FORECAST_TARGET_VALUE="$FORECAST_TARGET_VALUE" \\
TARGET_COL="$TARGET_COL" SKIP_COLS_LIST="$SKIP_COLS_LIST" \\
METRIC_TARGET_THRESHOLD="$METRIC_TARGET_THRESHOLD" METRIC_PREDICTION_THRESHOLD="$METRIC_PREDICTION_THRESHOLD" \\
TARGET_WINDOW_THRESHOLD="$TARGET_WINDOW_THRESHOLD" \\
SEEDS_SPEC="$SEEDS_SPEC" MAX_ITER="$MAX_ITER" BEST_N="$BEST_N" KEEP_BEST="$KEEP_BEST" KEEP_WORST="$KEEP_WORST" \\
FINAL_EVAL_NEGATIVE_WEIGHT="$FINAL_EVAL_NEGATIVE_WEIGHT" FINAL_EVAL_BEST_FRACTION="$FINAL_EVAL_BEST_FRACTION" \\
FINAL_EVAL_WORST_FRACTION="$FINAL_EVAL_WORST_FRACTION" FINAL_EVAL_SHAPE_POWER="$FINAL_EVAL_SHAPE_POWER" \\
REBUILD_MASTER="$REBUILD_MASTER" METRIC_TEST="$METRIC_TEST" \\
NASA_DAILY_MASTER_MODE="$NASA_DAILY_MASTER_MODE" NASA_SLOT_AGGREGATION="$NASA_SLOT_AGGREGATION" \\
NASA_SLOT_ADVANCED_STATS="$NASA_SLOT_ADVANCED_STATS" NASA_SLOT_ADVANCED_GROUP_SIZE="$NASA_SLOT_ADVANCED_GROUP_SIZE" \\
METRIC_TEST_PRESETS="$METRIC_TEST_PRESETS" METRIC_TEST_SEEDS="$METRIC_TEST_SEEDS" \\
METRIC_TEST_MAX_ITER="$METRIC_TEST_MAX_ITER" METRIC_TEST_JOBS="$METRIC_TEST_JOBS" \\
METRIC_TEST_CPU_COMPARE="$METRIC_TEST_CPU_COMPARE" METRIC_TEST_CPU_JOBS="$METRIC_TEST_CPU_JOBS" \\
METRIC_TEST_CPU_COMPARE_ONCE="$METRIC_TEST_CPU_COMPARE_ONCE" \\
METRIC_TEST_CPU_COMPARE_MARKER="$METRIC_TEST_CPU_COMPARE_MARKER" \\
AUTO_DEVICE_SELECT="$AUTO_DEVICE_SELECT" AUTO_DEVICE_ENV="$AUTO_DEVICE_ENV" \\
FEATURE_PRESELECT="$FEATURE_PRESELECT" FEATURE_PRESELECT_REBUILD="$FEATURE_PRESELECT_REBUILD" \\
FEATURE_SELECTION_K_BEST="${FEATURE_SELECTION_K_BEST:-}" FEATURE_SELECTION_THRESHOLD="${FEATURE_SELECTION_THRESHOLD:-}" \\
FEATURE_SELECTION_PERCENTILE="${FEATURE_SELECTION_PERCENTILE:-}" \\
FEATURE_SELECTION_MIN_FEATURES="${FEATURE_SELECTION_MIN_FEATURES:-}" FEATURE_SELECTION_MAX_FEATURES="${FEATURE_SELECTION_MAX_FEATURES:-}" \\
HYPER_PRETEST="$HYPER_PRETEST" HYPER_PRETEST_TOP_N="$HYPER_PRETEST_TOP_N" HYPER_PRETEST_SEEDS="$HYPER_PRETEST_SEEDS" \\
HYPER_PRETEST_EPOCHS="$HYPER_PRETEST_EPOCHS" HYPER_PRETEST_FULL_EPOCHS="$HYPER_PRETEST_FULL_EPOCHS" \\
HYPER_PRETEST_DEVICE="$HYPER_PRETEST_DEVICE" \\
./commands/run_world_mag85_30d_may_dec_nasadb_kan_base.sh
EOF
chmod +x "$OUT_DIR/RUN_THIS_PIPELINE.sh"

cat > "$OUT_DIR/pipeline_notes.md" <<EOF
# Worldwide M8.5+ 30d Traditional nasaDb KAN Forecast

- Target: worldwide earthquakes with magnitude >= ${MIN_MAG}.
- Forecast label: ${FORECAST_LABEL}.
- Technical forecast rows: ${FORECAST_START} -> ${FORECAST_END}.
- Note: nasaDb aligns 30d rows to its fixed 1900-01-01 grid; the first
  May-covering slot starts on ${FORECAST_START}.
- Horizontal history enabled: ${ENABLE_HORIZONTAL_HISTORY}; binary target: ${ENABLE_BINARY_TARGET}
  binary column: \`${BINARY_TARGET_COL}\`; target column: \`${TARGET_COL}\`.
- Binary source: \`${BINARY_SOURCE_COL}\`, operator: \`${BINARY_OPERATOR}\`,
  threshold: \`${BINARY_THRESHOLD:-auto}\`.
- Historical row filter: \`${ROW_FILTER}\`; forecast filter: \`${FORECAST_FILTER}\`.
- Target region: \`${TARGET_REGION}\`; target zones: \`${TARGET_ZONES}\`;
  zones CSV: \`${ZONES_CSV}\`.
- Out-of-region mode: \`${OUT_OF_REGION_MODE}\`.
- Forecast target placeholder: \`${FORECAST_TARGET_VALUE}\`.
- Traditional displacement is not used: row dates remain real. If horizontal
  history is enabled, time-travel values are extra columns only.
- Horizontal history mode: ${HISTORY_MODE}, value=${HISTORY_VALUE},
  spacer_days=${HISTORY_SPACER_DAYS}.
- Horizontal seismic history: ${HISTORY_ENABLE_SEISMIC}; horizontal astro
  history: ${HISTORY_ENABLE_ASTRO}; compact astro bodies:
  \`${HISTORY_ASTRO_BODIES}\`; fields: \`${HISTORY_ASTRO_FIELDS}\`.
- Sparse negative sampling: ${HISTORY_NEGATIVE_SAMPLING_MODE},
  random_negatives_per_positive=${HISTORY_RANDOM_NEGATIVES_PER_POSITIVE},
  neighbor_records=${HISTORY_KEEP_NEIGHBOR_RECORDS},
  recent_negatives=${HISTORY_KEEP_RECENT_NEGATIVES}.
- KAN hybrid enabled: ${HYBRID_KAN}; deep presets: \`${DEEP_PRESETS_RUN}\`;
  partners: \`${HYBRID_KAN_PARTNERS}\`; modes: \`${HYBRID_KAN_MODES}\`;
  alphas: \`${HYBRID_KAN_ALPHAS}\`; deep device: \`${DEEP_DEVICE}\`.
- NASA daily mode: ${NASA_DAILY_MASTER_MODE}; fetch step=${NASA_FETCH_STEP_INTERVAL},
  fetch range ${NASA_FETCH_START_DATE} -> ${NASA_FETCH_END_DATE},
  slot aggregation=${NASA_SLOT_AGGREGATION} on step ${STEP_INTERVAL},
  advanced_slot_stats=${NASA_SLOT_ADVANCED_STATS} (group_size=${NASA_SLOT_ADVANCED_GROUP_SIZE}).
- Historical ephemerides/events are post-1903.
- nasaDb windows around events: ${TIME_BEFORE} before and ${TIME_AFTER} after,
  step ${STEP_INTERVAL}.
- Validation: ${VALIDATION_EVENT_COUNT} events, with ${VALIDATION_PRE_RECORDS}
  records before and ${VALIDATION_POST_RECORDS} records after.
- Astronomy path: legacy \`nasaDb.py\` with progress, max_workers=${MAX_WORKERS}.
- Observer: place=${NASA_PLACE}, observer_levels=${OBSERVER_LEVELS},
  auto_target_centroid=${NASA_AUTO_OBSERVER_FROM_TARGET},
  explicit_observer_geo=\`${NASA_OBSERVER_GEO:-none}\`.
- Bodies: stable primary bodies plus legacy-safe secondary subset:
  \`${BODY_SECONDARY_LEVELS}\`.
- Extra bodies are disabled intentionally; VP113/TG387 are included through
  explicit secondary levels, while Halley is not auto-added.
- KAN: device=${KAN_DEVICE}, presets=${KAN_PRESETS_RUN}, seeds=${SEEDS_SPEC},
  max_iter=${MAX_ITER}, jobs=${JOBS}, keep_best=${KEEP_BEST},
  keep_worst=${KEEP_WORST}.
- Feature preselect: ${FEATURE_PRESELECT}; k_best=${FEATURE_SELECTION_K_BEST:-none},
  threshold=${FEATURE_SELECTION_THRESHOLD:-none}, percentile=${FEATURE_SELECTION_PERCENTILE:-none},
  min=${FEATURE_SELECTION_MIN_FEATURES:-none}, max=${FEATURE_SELECTION_MAX_FEATURES:-none}.
- Fusion: rank_mode=${FUSION_RANK_MODE}, inverse_worst_n=${FUSION_INVERSE_WORST_N}.
  The inverse-worst contribution uses \`1 - minmax(forecast_score)\` for the
  worst exported KAN sources and is printed inside the fusion PNG.
- Metric pretest: ${METRIC_TEST}; it runs by default and writes logs plus
  \`metric_test_summary.txt\` under \`${METRIC_TEST_TMP_DIR}\`.

Re-run command: \`RUN_THIS_PIPELINE.sh\`.
EOF

echo "======================================================================"
echo " Worldwide M8.5+ 30d traditional nasaDb KAN forecast"
echo " Output dir:       $OUT_DIR"
echo " Forecast label:   $FORECAST_LABEL"
echo " Forecast rows:    $FORECAST_START -> $FORECAST_END"
echo " Events cutoff:    $EVENTS_END_DATE"
echo " Time travel:      none"
echo " Horizontal hist:  enable=$ENABLE_HORIZONTAL_HISTORY mode=$HISTORY_MODE value=$HISTORY_VALUE seismic=$HISTORY_ENABLE_SEISMIC astro=$HISTORY_ENABLE_ASTRO"
echo " Target:           $TARGET_COL binary_col=$BINARY_TARGET_COL source=$BINARY_SOURCE_COL op='$BINARY_OPERATOR' bin_threshold=${BINARY_THRESHOLD:-auto}"
echo " Target metrics:   target=$METRIC_TARGET_THRESHOLD pred=$METRIC_PREDICTION_THRESHOLD row_filter='$ROW_FILTER' forecast_filter='$FORECAST_FILTER'"
echo " Target region:    region='$TARGET_REGION' zones='$TARGET_ZONES' zones_csv=$ZONES_CSV"
echo " Out region mode:  $OUT_OF_REGION_MODE"
echo " Forecast target:  placeholder=$FORECAST_TARGET_VALUE"
echo " Sparse negatives: $HISTORY_NEGATIVE_SAMPLING_MODE per_pos=$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE neighbor=$HISTORY_KEEP_NEIGHBOR_RECORDS recent=$HISTORY_KEEP_RECENT_NEGATIVES"
echo " NASA mode:        daily_mode=$NASA_DAILY_MASTER_MODE fetch_step=$NASA_FETCH_STEP_INTERVAL range=$NASA_FETCH_START_DATE->$NASA_FETCH_END_DATE"
echo " NASA slots:       aggregation=$NASA_SLOT_AGGREGATION slot_step=$STEP_INTERVAL advanced_stats=$NASA_SLOT_ADVANCED_STATS group_size=$NASA_SLOT_ADVANCED_GROUP_SIZE"
echo " NASA:             place=$NASA_PLACE observer_levels=$OBSERVER_LEVELS workers=$MAX_WORKERS"
echo " Bodies:           primary='$BODY_PRIMARY_LEVELS' secondary='$BODY_SECONDARY_LEVELS'"
echo " Validation:       events=$VALIDATION_EVENT_COUNT pre=$VALIDATION_PRE_RECORDS post=$VALIDATION_POST_RECORDS"
echo " KAN:              device=$KAN_DEVICE presets=$KAN_PRESETS_RUN seeds=$SEEDS_SPEC max_iter=$MAX_ITER jobs=$JOBS"
echo " Feature preselect: enabled=$FEATURE_PRESELECT k_best=${FEATURE_SELECTION_K_BEST:-none} threshold=${FEATURE_SELECTION_THRESHOLD:-none} percentile=${FEATURE_SELECTION_PERCENTILE:-none} min=${FEATURE_SELECTION_MIN_FEATURES:-none} max=${FEATURE_SELECTION_MAX_FEATURES:-none}"
echo " Hybrid KAN:       enabled=$HYBRID_KAN partners='$HYBRID_KAN_PARTNERS' modes=$HYBRID_KAN_MODES alphas=$HYBRID_KAN_ALPHAS deep=$DEEP_PRESETS_RUN"
echo " Fusion rank:      $FUSION_RANK_MODE"
echo " Fusion inverse:   inverse_worst_n=$FUSION_INVERSE_WORST_N formula='1-minmax(score)'"
echo " Metric pretest:   $METRIC_TEST"
echo " Rebuild master:   $REBUILD_MASTER"
echo " Log:              $LOG_FILE"
echo "======================================================================"

if [[ "$REBUILD_MASTER" == "1" || "$REBUILD_MASTER" == "true" || "$REBUILD_MASTER" == "yes" || ! -f "$MASTER" ]]; then
  echo ""
  echo "[1/6] Filter worldwide mag >= $MIN_MAG events for anti-leak training..."
  "$PYTHON_BIN" "$FILTER_EVENTS_PY" \
    --input-csv "$SRC_EVENTS" \
    --output-csv "$EVENTS_FILTERED" \
    --manifest-json "$OUT_DIR/filtered_events_manifest.json" \
    --min-mag "$MIN_MAG" \
    --start-date "$START_DATE" \
    --end-date "$EVENTS_END_DATE" \
    --title "worldwide mag >= $MIN_MAG events, traditional 30d May-Dec forecast"

  rm -rf "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"
  mkdir -p "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"

  RESOLVED_NASA_OBSERVER_GEO="$NASA_OBSERVER_GEO"
  if [[ -z "$RESOLVED_NASA_OBSERVER_GEO" && ( "$NASA_AUTO_OBSERVER_FROM_TARGET" == "1" || "$NASA_AUTO_OBSERVER_FROM_TARGET" == "true" || "$NASA_AUTO_OBSERVER_FROM_TARGET" == "yes" ) ]]; then
    RESOLVED_NASA_OBSERVER_GEO="$("$PYTHON_BIN" - \
      "$EVENTS_FILTERED" "$ZONES_CSV" "$TARGET_ZONES" "$TARGET_REGION" \
      "$NASA_OBSERVER_ALIAS" "$OUT_DIR/nasa_observer_manifest.json" <<'PY'
import csv
import json
import math
import sys
from pathlib import Path

events_csv = Path(sys.argv[1])
zones_csv = Path(sys.argv[2]) if sys.argv[2] else Path("")
target_zones = [x.strip().lower() for x in sys.argv[3].split(",") if x.strip()]
target_region = sys.argv[4].strip()
alias = sys.argv[5].strip() or "target_centroid"
manifest_path = Path(sys.argv[6])

def read_float(row, key):
    try:
        value = float(row.get(key, "nan"))
    except ValueError:
        return math.nan
    return value if math.isfinite(value) else math.nan

zones = {}
if zones_csv and zones_csv.exists():
    with zones_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            zid = str(row.get("zone_id", "")).strip()
            name = str(row.get("name", "")).strip()
            if not zid:
                continue
            spec = {
                "zone_id": zid,
                "name": name,
                "latitude_min": float(row["latitude_min"]),
                "latitude_max": float(row["latitude_max"]),
                "longitude_min": float(row["longitude_min"]),
                "longitude_max": float(row["longitude_max"]),
                "depth_min": float(row["depth_min"]) if str(row.get("depth_min", "")).strip() else None,
                "depth_max": float(row["depth_max"]) if str(row.get("depth_max", "")).strip() else None,
            }
            zones[zid.lower()] = spec
            if name:
                zones[name.lower()] = spec

selected = []
for token in target_zones:
    if token in zones:
        selected.append(zones[token])

events = []
if selected and events_csv.exists():
    with events_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            lat = read_float(row, "latitude")
            lon = read_float(row, "longitude")
            dep = read_float(row, "depth")
            mag = read_float(row, "mag")
            if not all(math.isfinite(x) for x in (lat, lon, dep, mag)):
                continue
            for z in selected:
                if not (z["latitude_min"] <= lat <= z["latitude_max"]):
                    continue
                if not (z["longitude_min"] <= lon <= z["longitude_max"]):
                    continue
                if z["depth_min"] is not None and dep < z["depth_min"]:
                    continue
                if z["depth_max"] is not None and dep > z["depth_max"]:
                    continue
                events.append({"lat": lat, "lon": lon, "depth": dep, "mag": mag})
                break

payload = {
    "mode": "target_event_centroid",
    "events_csv": str(events_csv),
    "zones_csv": str(zones_csv),
    "target_zones": target_zones,
    "target_region": target_region,
    "resolved_zones": selected,
    "event_count": len(events),
    "observer_geo": "",
    "fallback": "",
}
if events:
    lat = sum(e["lat"] for e in events) / len(events)
    lon = sum(e["lon"] for e in events) / len(events)
    payload.update({
        "centroid_latitude": lat,
        "centroid_longitude": lon,
        "centroid_elevation": 0.0,
        "observer_alias": alias,
        "observer_geo": f"{lat:.6f},{lon:.6f},0,{alias}",
    })
    print(payload["observer_geo"])
else:
    payload["fallback"] = "no_events_in_target_zones_or_no_target_zones"

manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
PY
)"
  fi

  NASA_EXTRA_ARGS=(
    --ephemerides_fields "$EPHEMERIDES_FIELDS"
    --body_primary_levels
  )
  read -r -a BODY_PRIMARY_LEVELS_ARRAY <<< "$BODY_PRIMARY_LEVELS"
  NASA_EXTRA_ARGS+=("${BODY_PRIMARY_LEVELS_ARRAY[@]}")
  NASA_EXTRA_ARGS+=(--body_secondary_levels)
  read -r -a BODY_SECONDARY_LEVELS_ARRAY <<< "$BODY_SECONDARY_LEVELS"
  NASA_EXTRA_ARGS+=("${BODY_SECONDARY_LEVELS_ARRAY[@]}")
  if [[ -n "$RESOLVED_NASA_OBSERVER_GEO" ]]; then
    NASA_EXTRA_ARGS+=("--observer-geo=$RESOLVED_NASA_OBSERVER_GEO")
    echo "[observer] NASA/JPL custom observer from target events: $RESOLVED_NASA_OBSERVER_GEO"
    echo "[observer] manifest: $OUT_DIR/nasa_observer_manifest.json"
  else
    NASA_EXTRA_ARGS+=(--observer_levels)
    read -r -a OBSERVER_LEVELS_ARRAY <<< "$OBSERVER_LEVELS"
    NASA_EXTRA_ARGS+=("${OBSERVER_LEVELS_ARRAY[@]}")
    echo "[observer] NASA/JPL preset observers: place=$NASA_PLACE observer_levels=$OBSERVER_LEVELS"
  fi
  NASA_EXTRA_ARGS+=(--disable-extra-bodies)

  echo ""
  echo "[2/6] NASA/JPL ephemerides via nasaDb.py with visible progress..."
  "$PYTHON_BIN" "$ASTRO_ROOT/nasaDb.py" \
    --csv_file "$EVENTS_FILTERED" \
    --datetime_column time \
    --time_before "$NASA_FETCH_TIME_BEFORE" \
    --time_after "$NASA_FETCH_TIME_AFTER" \
    --step_interval "$NASA_FETCH_STEP_INTERVAL" \
    --start_date "$NASA_FETCH_START_DATE" \
    --end_date "$NASA_FETCH_END_DATE" \
    --place "$NASA_PLACE" \
    --bodies_dir "$OUT_DIR/nasa_bodies" \
    --backup_dir "$OUT_DIR/nasa_bodies_backup" \
    --master_output "$NASA_MASTER_DAILY" \
    --raw_output "$OUT_DIR/nasa_master_focus_sparse.Raw.csv" \
    --command_script "$OUT_DIR/2-nasa_download.replay.sh" \
    --max_workers "$MAX_WORKERS" \
    --sleep_time "$SLEEP_TIME" \
    --max_retries "$MAX_RETRIES" \
    --progress \
    --chunk-manifest \
    --clean_bodies \
    --add-graph "$OUT_DIR/nasa_event_vs_astro.png" \
    "${NASA_EXTRA_ARGS[@]}"

  [[ -f "$NASA_MASTER_DAILY" ]] || { echo "[ERROR] NASA daily master not created: $NASA_MASTER_DAILY" >&2; exit 1; }

  if [[ "$NASA_DAILY_MASTER_MODE" == "1" || "$NASA_DAILY_MASTER_MODE" == "true" || "$NASA_DAILY_MASTER_MODE" == "yes" ]]; then
    if [[ "$NASA_SLOT_AGGREGATION" != "median" ]]; then
      echo "[ERROR] Unsupported NASA_SLOT_AGGREGATION: $NASA_SLOT_AGGREGATION (supported: median)" >&2
      exit 1
    fi
    echo ""
    echo "[2b/6] Aggregate daily NASA master to slot medians (${STEP_INTERVAL})..."
    "$PYTHON_BIN" "$AGGREGATE_NASA_PY" \
      --input-csv "$NASA_MASTER_DAILY" \
      --output-csv "$NASA_MASTER" \
      --manifest-json "$OUT_DIR/nasa_slot_aggregation_manifest.json" \
      --slot-start-date "$START_DATE" \
      --slot-end-date "$FORECAST_END" \
      --slot-step-interval "$STEP_INTERVAL" \
      --advanced-body-stats "$NASA_SLOT_ADVANCED_STATS" \
      --advanced-group-size "$NASA_SLOT_ADVANCED_GROUP_SIZE"
  else
    cp "$NASA_MASTER_DAILY" "$NASA_MASTER"
  fi

  [[ -f "$NASA_MASTER" ]] || { echo "[ERROR] NASA slot master not created: $NASA_MASTER" >&2; exit 1; }

  echo ""
  echo "[3/6] Add USGS core columns and convert to astrofmt..."
  "$PYTHON_BIN" "$ADD_USGS_PY" \
    --nasa-master "$NASA_MASTER" \
    --usgs-events "$EVENTS_FILTERED" \
    --output "$MASTER_CORE"

  "$PYTHON_BIN" "$CONV_PY" \
    --input-csv "$MASTER_CORE" \
    --output-csv "$FLOAT_MASTER"

  echo ""
  MASTER_FOR_QUANT="$FLOAT_MASTER"
  if [[ "$ENABLE_BINARY_TARGET" == "1" || "$ENABLE_BINARY_TARGET" == "true" || "$ENABLE_BINARY_TARGET" == "yes" ]]; then
    HISTORY_ARGS=(
      --input-csv "$FLOAT_MASTER"
      --output-csv "$HISTORY_FLOAT_MASTER"
      --manifest-json "$OUT_DIR/horizontal_history_manifest.json"
      --events-csv "$EVENTS_FILTERED"
      --min-mag "$MIN_MAG"
      --binary-target-col "$BINARY_TARGET_COL"
      --binary-source-col "$BINARY_SOURCE_COL"
      --binary-operator "$BINARY_OPERATOR"
      --row-filter "$ROW_FILTER"
      --forecast-filter "$FORECAST_FILTER"
      --zones-csv "$ZONES_CSV"
      --target-region "$TARGET_REGION"
      --target-zones "$TARGET_ZONES"
      --out-of-region-mode "$OUT_OF_REGION_MODE"
      --forecast-target-value "$FORECAST_TARGET_VALUE"
      --history-mode "$HISTORY_MODE"
      --history-value "$HISTORY_VALUE"
      --history-spacer-days "$HISTORY_SPACER_DAYS"
      --astro-bodies "$HISTORY_ASTRO_BODIES"
      --astro-fields "$HISTORY_ASTRO_FIELDS"
      --negative-sampling-mode "$HISTORY_NEGATIVE_SAMPLING_MODE"
      --random-negatives-per-positive "$HISTORY_RANDOM_NEGATIVES_PER_POSITIVE"
      --random-negative-seed "$HISTORY_RANDOM_NEGATIVE_SEED"
      --keep-neighbor-records "$HISTORY_KEEP_NEIGHBOR_RECORDS"
      --keep-recent-negatives "$HISTORY_KEEP_RECENT_NEGATIVES"
      --forecast-start-date "$FORECAST_START"
      --forecast-end-date "$FORECAST_END"
    )
    if [[ -n "$BINARY_THRESHOLD" ]]; then
      HISTORY_ARGS+=(--binary-threshold "$BINARY_THRESHOLD")
    fi
    if [[ "$HISTORY_ENABLE_SEISMIC" == "1" || "$HISTORY_ENABLE_SEISMIC" == "true" || "$HISTORY_ENABLE_SEISMIC" == "yes" ]]; then
      HISTORY_ARGS+=(--enable-seismic-history)
    fi
    if [[ "$ENABLE_HORIZONTAL_HISTORY" == "1" || "$ENABLE_HORIZONTAL_HISTORY" == "true" || "$ENABLE_HORIZONTAL_HISTORY" == "yes" ]]; then
      if [[ "$HISTORY_ENABLE_ASTRO" == "1" || "$HISTORY_ENABLE_ASTRO" == "true" || "$HISTORY_ENABLE_ASTRO" == "yes" ]]; then
        HISTORY_ARGS+=(--enable-astro-history)
      fi
    else
      HISTORY_ARGS+=(--history-mode none)
    fi

    echo "[4a/6] Add binary target and compact horizontal-history columns..."
    "$PYTHON_BIN" "$AUGMENT_HISTORY_PY" "${HISTORY_ARGS[@]}"
    MASTER_FOR_QUANT="$HISTORY_FLOAT_MASTER"
  fi

  echo ""
  echo "[4b/6] Quantize and sanitize numeric master..."
  "$PYTHON_BIN" "$QUANT_PY" \
    --input-csv "$MASTER_FOR_QUANT" \
    --output-csv "$MASTER" \
    --bins "$QUANT_BINS" \
    --skip-cols "$BINARY_TARGET_COL"

  SANITIZED_TMP="$OUT_DIR/master_with_usgs_core_astrofmt.sanitized.tmp.csv"
  "$PYTHON_BIN" "$SANITIZE_PY" \
    --input-csv "$MASTER" \
    --output-csv "$SANITIZED_TMP" \
    --report-json "$OUT_DIR/master_with_usgs_core_astrofmt_sanitize_report.json" \
    --skip-cols date
  mv "$SANITIZED_TMP" "$MASTER"
else
  echo "[1-4/6] Existing master found, skip rebuild: $MASTER"
fi

echo ""
echo "[target-report] Resolve target/feature selection..."
"$PYTHON_BIN" - \
  "$MASTER" "$TARGET_COL" "$SKIP_COLS_LIST" \
  "$METRIC_TARGET_THRESHOLD" "$METRIC_PREDICTION_THRESHOLD" \
  "$OUT_DIR/target_selection_report.json" "$OUT_DIR/target_selection_report.md" \
  "$BINARY_TARGET_COL" "$BINARY_SOURCE_COL" "$BINARY_OPERATOR" "${BINARY_THRESHOLD:-auto}" \
  "$ROW_FILTER" "$FORECAST_FILTER" "$TARGET_REGION" "$TARGET_ZONES" "$OUT_OF_REGION_MODE" <<'PY'
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

master = Path(sys.argv[1])
target_col = sys.argv[2]
skip_cols = [c.strip() for c in sys.argv[3].split(",") if c.strip()]
target_threshold = float(sys.argv[4])
prediction_threshold = float(sys.argv[5])
json_out = Path(sys.argv[6])
md_out = Path(sys.argv[7])
binary_target_col = sys.argv[8]
binary_source_col = sys.argv[9]
binary_operator = sys.argv[10]
binary_threshold = sys.argv[11]
row_filter = sys.argv[12]
forecast_filter = sys.argv[13]
target_region = sys.argv[14]
target_zones = sys.argv[15]
out_of_region_mode = sys.argv[16]

with master.open(newline="") as f:
    reader = csv.DictReader(f)
    header = list(reader.fieldnames or [])
    rows = list(reader)

if target_col not in header:
    raise SystemExit(f"[target-report] ERROR: target column not found: {target_col}")
missing_skip = [c for c in skip_cols if c not in header]
if missing_skip:
    raise SystemExit(f"[target-report] ERROR: skip columns not found: {missing_skip}")

feature_cols = [c for c in header if c != target_col and c not in skip_cols]
values = []
for row in rows:
    try:
        value = float(row.get(target_col, "nan"))
    except (TypeError, ValueError):
        value = float("nan")
    values.append(value)

finite = [v for v in values if math.isfinite(v)]
positive_count = sum(1 for v in finite if v >= target_threshold)
zero_count = sum(1 for v in finite if v == 0.0)
one_count = sum(1 for v in finite if v == 1.0)
unique_values = sorted(set(finite))
is_binary_01 = bool(finite) and set(unique_values).issubset({0.0, 1.0})
counter = Counter(finite)
top_values = [
    {"value": value, "count": count}
    for value, count in counter.most_common(20)
]

report = {
    "master": str(master),
    "rows": len(rows),
    "columns": len(header),
    "target_col": target_col,
    "binary_target_col": binary_target_col,
    "binary_source_col": binary_source_col,
    "binary_operator": binary_operator,
    "binary_threshold": binary_threshold,
    "row_filter": row_filter,
    "forecast_filter": forecast_filter,
    "target_region": target_region,
    "target_zones": target_zones,
    "out_of_region_mode": out_of_region_mode,
    "skip_cols": skip_cols,
    "feature_count": len(feature_cols),
    "feature_cols_sample": feature_cols[:40],
    "metric_target_threshold": target_threshold,
    "metric_prediction_threshold": prediction_threshold,
    "finite_target_rows": len(finite),
    "positive_rows_by_threshold": positive_count,
    "positive_fraction_by_threshold": (positive_count / len(finite)) if finite else 0.0,
    "zero_rows": zero_count,
    "one_rows": one_count,
    "is_binary_0_1": is_binary_01,
    "target_min": min(finite) if finite else None,
    "target_max": max(finite) if finite else None,
    "target_top_values": top_values,
}

json_out.write_text(json.dumps(report, indent=2) + "\n")
md_lines = [
    "# Target Selection Report",
    "",
    f"- Master: `{master}`",
    f"- Rows: {len(rows)}",
    f"- Columns: {len(header)}",
    f"- Target column: `{target_col}`",
    f"- Binary target column: `{binary_target_col}`",
    f"- Binary source column: `{binary_source_col}`",
    f"- Binary operator: `{binary_operator}`",
    f"- Binary threshold: `{binary_threshold}`",
    f"- Row filter: `{row_filter}`",
    f"- Forecast filter: `{forecast_filter}`",
    f"- Target region: `{target_region}`",
    f"- Target zones: `{target_zones}`",
    f"- Out-of-region mode: `{out_of_region_mode}`",
    f"- Target threshold: `{target_threshold}`",
    f"- Prediction threshold: `{prediction_threshold}`",
    f"- Binary 0/1 target: `{str(is_binary_01).lower()}`",
    f"- Positive rows by threshold: {positive_count}/{len(finite)}",
    f"- Feature columns used: {len(feature_cols)}",
    f"- Skip columns: `{','.join(skip_cols)}`",
    "",
    "## Target Distribution",
    "",
    "| value | count |",
    "|---:|---:|",
]
for item in top_values:
    md_lines.append(f"| {item['value']} | {item['count']} |")
md_lines.extend([
    "",
    "## Feature Sample",
    "",
])
for col in feature_cols[:40]:
    md_lines.append(f"- `{col}`")
md_out.write_text("\n".join(md_lines) + "\n")

print(f"[target-report] target={target_col} binary={is_binary_01} positives={positive_count}/{len(finite)} features={len(feature_cols)}")
print(f"[target-report] json={json_out}")
print(f"[target-report] md={md_out}")
PY

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"

TRAIN_MASTER="$MASTER"
FEATURE_SELECTION_REQUESTED=0
if [[ -n "${FEATURE_SELECTION_K_BEST:-}" || -n "${FEATURE_SELECTION_THRESHOLD:-}" || -n "${FEATURE_SELECTION_PERCENTILE:-}" || -n "${FEATURE_SELECTION_MIN_FEATURES:-}" || -n "${FEATURE_SELECTION_MAX_FEATURES:-}" ]]; then
  FEATURE_SELECTION_REQUESTED=1
fi
FEATURE_SELECTION_MATERIALIZED=0
if [[ "$FEATURE_SELECTION_REQUESTED" == "1" && ( "$FEATURE_PRESELECT" == "1" || "$FEATURE_PRESELECT" == "true" || "$FEATURE_PRESELECT" == "yes" ) ]]; then
  if [[ "$FEATURE_PRESELECT_REBUILD" == "1" || "$FEATURE_PRESELECT_REBUILD" == "true" || "$FEATURE_PRESELECT_REBUILD" == "yes" || ! -f "$PRESELECT_MASTER" ]]; then
    echo ""
    echo "[feature-preselect] One-shot MI feature selection before metric/full training..."
    FEATURE_PRESELECT_ARGS=()
    if [[ -n "${FEATURE_SELECTION_THRESHOLD:-}" ]]; then
      FEATURE_PRESELECT_ARGS+=(--threshold "$FEATURE_SELECTION_THRESHOLD")
    fi
    if [[ -n "${FEATURE_SELECTION_K_BEST:-}" ]]; then
      FEATURE_PRESELECT_ARGS+=(--k-best "$FEATURE_SELECTION_K_BEST")
    fi
    if [[ -n "${FEATURE_SELECTION_PERCENTILE:-}" ]]; then
      FEATURE_PRESELECT_ARGS+=(--percentile "$FEATURE_SELECTION_PERCENTILE")
    fi
    if [[ -n "${FEATURE_SELECTION_MIN_FEATURES:-}" ]]; then
      FEATURE_PRESELECT_ARGS+=(--min-features "$FEATURE_SELECTION_MIN_FEATURES")
    fi
    if [[ -n "${FEATURE_SELECTION_MAX_FEATURES:-}" ]]; then
      FEATURE_PRESELECT_ARGS+=(--max-features "$FEATURE_SELECTION_MAX_FEATURES")
    fi
    "$PYTHON_BIN" "$FEATURE_PRESELECT_PY" \
      --input-csv "$MASTER" \
      --output-csv "$PRESELECT_MASTER" \
      --ranking-csv "$PRESELECT_RANKING" \
      --manifest-json "$PRESELECT_MANIFEST" \
      --report-md "$PRESELECT_REPORT" \
      --target-col "$TARGET_COL" \
      --skip-cols-list "$SKIP_COLS_LIST" \
      "${FEATURE_PRESELECT_ARGS[@]}" \
      --target-threshold "$TARGET_WINDOW_THRESHOLD" \
      --target-event-count "$TARGET_EVENT_COUNT" \
      --target-pre-records "$VALIDATION_PRE_RECORDS" \
      --target-post-records "$VALIDATION_POST_RECORDS" \
      --isolated-event-windows
  else
    echo "[feature-preselect] Reusing existing selected-feature master: $PRESELECT_MASTER"
  fi
  TRAIN_MASTER="$PRESELECT_MASTER"
  FEATURE_SELECTION_MATERIALIZED=1
  echo "[feature-preselect] Training master: $TRAIN_MASTER"
  echo "[feature-preselect] Report: $PRESELECT_REPORT"
fi

if [[ "$HYPER_PRETEST" == "1" || "$HYPER_PRETEST" == "true" || "$HYPER_PRETEST" == "yes" ]]; then
  if [[ ! -f "$HYPER_PRESET_JSON" || "$FEATURE_PRESELECT_REBUILD" == "1" || "$FEATURE_PRESELECT_REBUILD" == "true" || "$FEATURE_PRESELECT_REBUILD" == "yes" ]]; then
    echo ""
    echo "[hyper-pretest] Deep hyperparameter pretest before full training..."
    "$PYTHON_BIN" "$HYPER_PRETEST_PY" \
      --input-csv "$TRAIN_MASTER" \
      --output-csv "$HYPER_PRETEST_CSV" \
      --output-json "$HYPER_PRETEST_JSON" \
      --preset-json "$HYPER_PRESET_JSON" \
      --target-col "$TARGET_COL" \
      --skip-cols-list "$SKIP_COLS_LIST" \
      --target-threshold "$TARGET_WINDOW_THRESHOLD" \
      --target-event-count "$TARGET_EVENT_COUNT" \
      --target-pre-records "$VALIDATION_PRE_RECORDS" \
      --target-post-records "$VALIDATION_POST_RECORDS" \
      --isolated-event-windows \
      --seeds "$HYPER_PRETEST_SEEDS" \
      --top-n "$HYPER_PRETEST_TOP_N" \
      --device "$HYPER_PRETEST_DEVICE" \
      --pretest-epochs "$HYPER_PRETEST_EPOCHS" \
      --full-epochs "$HYPER_PRETEST_FULL_EPOCHS"
  else
    echo "[hyper-pretest] Reusing existing selected deep presets: $HYPER_PRESET_JSON"
  fi
  DEEP_PRESET_CONFIGS_JSON="$HYPER_PRESET_JSON"
  HYPER_SELECTED_PRESETS="$("$PYTHON_BIN" - "$HYPER_PRESET_JSON" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
print(",".join(str(p.get("name")) for p in data.get("presets", []) if p.get("name")))
PY
)"
  if [[ -n "$HYPER_SELECTED_PRESETS" ]]; then
    DEEP_PRESETS_RUN="$HYPER_SELECTED_PRESETS"
    HYBRID_KAN_PARTNERS="$(printf '%s' "$HYPER_SELECTED_PRESETS" | awk -F, '{for (i=1;i<=NF;i++) printf "%sdeep:%s", (i==1?"":","), $i}')"
    echo "[hyper-pretest] Selected deep presets: $DEEP_PRESETS_RUN"
    echo "[hyper-pretest] Preset config JSON: $DEEP_PRESET_CONFIGS_JSON"
  fi
fi

KAN_EXTRA_ARGS=()
if [[ "$KAN_QUIET" == "1" || "$KAN_QUIET" == "true" || "$KAN_QUIET" == "yes" ]]; then
  KAN_EXTRA_ARGS+=(--kan-quiet)
fi

if [[ "$FEATURE_SELECTION_MATERIALIZED" != "1" ]]; then
  if [[ -n "${FEATURE_SELECTION_K_BEST:-}" ]]; then
    KAN_EXTRA_ARGS+=(--feature-selection-k-best "$FEATURE_SELECTION_K_BEST")
  fi
  if [[ -n "${FEATURE_SELECTION_THRESHOLD:-}" ]]; then
    KAN_EXTRA_ARGS+=(--feature-selection-threshold "$FEATURE_SELECTION_THRESHOLD")
  fi
  if [[ -n "${FEATURE_SELECTION_PERCENTILE:-}" ]]; then
    KAN_EXTRA_ARGS+=(--feature-selection-percentile "$FEATURE_SELECTION_PERCENTILE")
  fi
  if [[ -n "${FEATURE_SELECTION_MIN_FEATURES:-}" ]]; then
    KAN_EXTRA_ARGS+=(--feature-selection-min-features "$FEATURE_SELECTION_MIN_FEATURES")
  fi
  if [[ -n "${FEATURE_SELECTION_MAX_FEATURES:-}" ]]; then
    KAN_EXTRA_ARGS+=(--feature-selection-max-features "$FEATURE_SELECTION_MAX_FEATURES")
  fi
fi

KAN_HYBRID_ARGS=()
if [[ "$HYBRID_KAN" == "1" || "$HYBRID_KAN" == "true" || "$HYBRID_KAN" == "yes" ]]; then
  KAN_HYBRID_ARGS+=(
    --hybrid-kan
    --deep-presets "$DEEP_PRESETS_RUN"
    --deep-device "$DEEP_DEVICE"
    --deep-val-target-threshold "$TARGET_WINDOW_THRESHOLD"
    --deep-val-event-count "$VALIDATION_EVENT_COUNT"
    --deep-val-pre-records "$VALIDATION_PRE_RECORDS"
    --deep-val-post-records "$VALIDATION_POST_RECORDS"
    --deep-validation-metric event_composite
    --deep-validation-threshold "$METRIC_PREDICTION_THRESHOLD"
    --hybrid-partners "$HYBRID_KAN_PARTNERS"
    --hybrid-modes "$HYBRID_KAN_MODES"
    --hybrid-alphas "$HYBRID_KAN_ALPHAS"
    --hybrid-threshold "$HYBRID_KAN_THRESHOLD"
  )
  if [[ -n "$DEEP_PRESET_CONFIGS_JSON" ]]; then
    KAN_HYBRID_ARGS+=(--deep-preset-configs-json "$DEEP_PRESET_CONFIGS_JSON")
  fi
fi

if [[ "$METRIC_TEST" == "1" || "$METRIC_TEST" == "true" || "$METRIC_TEST" == "yes" ]]; then
  METRIC_STAMP="$(date +%Y%m%d-%H%M%S)"
  METRIC_DIR="$METRIC_TEST_TMP_DIR/${RUN_LABEL}_${KAN_DEVICE}_${METRIC_STAMP}"
  METRIC_MASTER="$METRIC_DIR/master_with_usgs_core_astrofmt.metric_test.csv"
  METRIC_LOG="$METRIC_DIR/${RUN_LABEL}_${KAN_DEVICE}_metric_test.log"
  METRIC_DB="$METRIC_DIR/${RUN_LABEL}_${KAN_DEVICE}_metric_test.db"
  METRIC_SUMMARY="$METRIC_DIR/metric_test_summary.txt"
  mkdir -p "$METRIC_DIR"
  cp "$TRAIN_MASTER" "$METRIC_MASTER"

  echo ""
  echo "[metric-test] Short KAN pretest before full run"
  echo " Metric dir:   $METRIC_DIR"
  echo " Metric log:   $METRIC_LOG"
  echo " KAN:          device=$KAN_DEVICE presets=$METRIC_TEST_PRESETS seeds=$METRIC_TEST_SEEDS max_iter=$METRIC_TEST_MAX_ITER jobs=$METRIC_TEST_JOBS"

  METRIC_TEST_STARTED=$SECONDS
  "$PYTHON_BIN" -u cli.py train \
    --task "$METRIC_MASTER" \
    --target_cols_list "$TARGET_COL" \
    --skip_cols_list "$SKIP_COLS_LIST" \
    --no-banks \
    --enable-kan \
    --kan-presets "$METRIC_TEST_PRESETS" \
    --kan-device "$KAN_DEVICE" \
    "${KAN_EXTRA_ARGS[@]}" \
    --metric-mode auto \
    --metric-target-threshold "$METRIC_TARGET_THRESHOLD" \
    --metric-prediction-threshold "$METRIC_PREDICTION_THRESHOLD" \
    --event-score-mode isolation \
    --target-window-threshold "$TARGET_WINDOW_THRESHOLD" \
    --target-window-event-count "$TARGET_EVENT_COUNT" \
    --target-window-pre-records "$VALIDATION_PRE_RECORDS" \
    --target-window-post-records "$VALIDATION_POST_RECORDS" \
    --isolated-event-windows \
    --recent-validation-window \
    --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
    --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
    --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
    --recent-validation-weight 3.0 \
    --recent-validation-random-negatives "$RECENT_VALIDATION_RANDOM_NEGATIVES" \
    --recent-validation-random-seed "$RECENT_VALIDATION_RANDOM_SEED" \
    --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
    --train-recency-weight exp \
    --train-recency-strength 1.0 \
    --train-event-weight auto \
    --train-max-event-weight 8.0 \
    --forecast-start-date "$FORECAST_START" \
    --forecast-end-date "$FORECAST_END" \
    --forecast-trainset train2forecast \
    --final-eval-rank-power 1.0 \
    --final-eval-low-threshold 1e-9 \
    --final-eval-negative-weight "$FINAL_EVAL_NEGATIVE_WEIGHT" \
    --final-eval-best-fraction "$FINAL_EVAL_BEST_FRACTION" \
    --final-eval-worst-fraction "$FINAL_EVAL_WORST_FRACTION" \
    --final-eval-shape-power "$FINAL_EVAL_SHAPE_POWER" \
    --readability-weight 0.30 \
    --readability-floor 0.25 \
    --seeds "$METRIC_TEST_SEEDS" \
    --max-iter "$METRIC_TEST_MAX_ITER" \
    --jobs "$METRIC_TEST_JOBS" \
    --best "$METRIC_TEST_BEST_N" \
    --keep-best "$METRIC_TEST_KEEP_BEST" \
    --keep-worst 0 \
    --no-invert-twin \
    --no-export-best-by-bank \
    --db "$METRIC_DB" \
    --verbose \
    2>&1 | tee "$METRIC_LOG"
  METRIC_TEST_ELAPSED=$((SECONDS - METRIC_TEST_STARTED))

  METRIC_RUN_DIR="$(find "$METRIC_DIR" -maxdepth 1 -type d -name 'pulsar_train*_best_trials_*' | sort | tail -n 1)"
  if [[ -n "$METRIC_RUN_DIR" && -f "$METRIC_RUN_DIR/best_trials_index.csv" ]]; then
    "$PYTHON_BIN" - \
      "$METRIC_RUN_DIR/best_trials_index.csv" \
      "$METRIC_SUMMARY" \
      "$METRIC_TEST_ELAPSED" \
      "$METRIC_LOG" \
      "$METRIC_TEST_PRESETS" \
      "$METRIC_TEST_SEEDS" \
      "$KAN_PRESETS_RUN" \
      "$SEEDS_SPEC" <<'PY'
import csv
import sys
from pathlib import Path

idx = Path(sys.argv[1])
out = Path(sys.argv[2])
elapsed = max(0.0, float(sys.argv[3]))
metric_log = Path(sys.argv[4])
metric_presets = [x for x in sys.argv[5].split(",") if x.strip()]
metric_seeds_spec = sys.argv[6]
full_presets = [x for x in sys.argv[7].split(",") if x.strip()]
full_seeds_spec = sys.argv[8]

def count_seeds(spec: str) -> int:
    text = str(spec or "").strip()
    if not text:
        return 0
    if "," in text:
        return len([x for x in text.split(",") if x.strip()])
    if ":" in text:
        _, count = text.split(":", 1)
        return int(count)
    if text.startswith("@") or text.startswith("seed:"):
        return 1
    return int(text)

with idx.open(newline="") as f:
    rows = list(csv.DictReader(f))
rows.sort(key=lambda r: float(r.get("overall") or r.get("score") or "-999"), reverse=True)
top = rows[:5]
metric_trials = 0
if metric_log.exists():
    import re
    matches = list(re.finditer(r"\[\s*(\d+)/(\d+)\]\s+[0-9.]+%", metric_log.read_text(errors="replace")))
    if matches:
        metric_trials = int(matches[-1].group(1))
metric_trials = metric_trials or (len(metric_presets) * count_seeds(metric_seeds_spec))
full_trials = len(full_presets) * count_seeds(full_seeds_spec)
sec_per_trial = elapsed / metric_trials if metric_trials else 0.0
trials_per_min = 60.0 / sec_per_trial if sec_per_trial else 0.0
estimated_full = sec_per_trial * full_trials if full_trials else 0.0

def fmt(seconds: float) -> str:
    seconds = int(round(max(0.0, seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"

lines = [f"source={idx}"]
lines.extend([
    f"elapsed={fmt(elapsed)}",
    f"metric_trials={metric_trials}",
    f"metric_sec_per_trial={sec_per_trial:.3f}",
    f"metric_trials_per_min={trials_per_min:.2f}",
    f"full_trials={full_trials}",
    f"estimated_full_train_time={fmt(estimated_full)}",
])
for i, row in enumerate(top, 1):
    lines.append(
        " ".join(
            [
                f"rank={i}",
                f"overall={row.get('overall') or row.get('score')}",
                f"preset={row.get('preset') or row.get('readout')}",
                f"seed={row.get('seed')}",
                f"f1={row.get('f1')}",
                f"recall={row.get('recall')}",
                f"bal={row.get('bal_acc')}",
            ]
        )
    )
out.write_text("\n".join(lines) + "\n")
print("[metric-test] summary:")
print(out.read_text())
PY
  else
    echo "[metric-test] Warning: best_trials_index.csv not found under $METRIC_DIR"
  fi

  if [[ "$METRIC_TEST_CPU_COMPARE" == "1" || "$METRIC_TEST_CPU_COMPARE" == "true" || "$METRIC_TEST_CPU_COMPARE" == "yes" ]]; then
    if [[ "$KAN_DEVICE" == "cpu" ]]; then
      echo "[speed-test] CPU comparison skipped: main KAN_DEVICE is already cpu."
    elif [[ "$METRIC_TEST_CPU_COMPARE_ONCE" != "0" && -n "$METRIC_TEST_CPU_COMPARE_MARKER" && -f "$METRIC_TEST_CPU_COMPARE_MARKER" ]]; then
      echo "[speed-test] CPU comparison skipped: already completed for this batch."
    else
      METRIC_CPU_DIR="$METRIC_DIR/cpu_compare_jobs${METRIC_TEST_CPU_JOBS}"
      METRIC_CPU_MASTER="$METRIC_CPU_DIR/master_with_usgs_core_astrofmt.metric_test.csv"
      METRIC_CPU_LOG="$METRIC_CPU_DIR/${RUN_LABEL}_cpu_metric_test.log"
      METRIC_CPU_DB="$METRIC_CPU_DIR/${RUN_LABEL}_cpu_metric_test.db"
      mkdir -p "$METRIC_CPU_DIR"
      cp "$TRAIN_MASTER" "$METRIC_CPU_MASTER"

      echo ""
      echo "[speed-test] CPU comparison pretest before full run"
      echo "[speed-test] CPU: device=cpu presets=$METRIC_TEST_PRESETS seeds=$METRIC_TEST_SEEDS max_iter=$METRIC_TEST_MAX_ITER jobs=$METRIC_TEST_CPU_JOBS"

      METRIC_CPU_STARTED=$SECONDS
      "$PYTHON_BIN" -u cli.py train \
        --task "$METRIC_CPU_MASTER" \
        --target_cols_list "$TARGET_COL" \
        --skip_cols_list "$SKIP_COLS_LIST" \
        --no-banks \
        --enable-kan \
        --kan-presets "$METRIC_TEST_PRESETS" \
        --kan-device cpu \
        "${KAN_EXTRA_ARGS[@]}" \
        --metric-mode auto \
        --metric-target-threshold "$METRIC_TARGET_THRESHOLD" \
        --metric-prediction-threshold "$METRIC_PREDICTION_THRESHOLD" \
        --event-score-mode isolation \
        --target-window-threshold "$TARGET_WINDOW_THRESHOLD" \
        --target-window-event-count "$TARGET_EVENT_COUNT" \
        --target-window-pre-records "$VALIDATION_PRE_RECORDS" \
        --target-window-post-records "$VALIDATION_POST_RECORDS" \
        --isolated-event-windows \
        --recent-validation-window \
        --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
        --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
        --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
        --recent-validation-weight 3.0 \
        --recent-validation-random-negatives "$RECENT_VALIDATION_RANDOM_NEGATIVES" \
        --recent-validation-random-seed "$RECENT_VALIDATION_RANDOM_SEED" \
        --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
        --train-recency-weight exp \
        --train-recency-strength 1.0 \
        --train-event-weight auto \
        --train-max-event-weight 8.0 \
        --forecast-start-date "$FORECAST_START" \
        --forecast-end-date "$FORECAST_END" \
        --forecast-trainset train2forecast \
        --final-eval-rank-power 1.0 \
        --final-eval-low-threshold 1e-9 \
        --final-eval-negative-weight "$FINAL_EVAL_NEGATIVE_WEIGHT" \
        --final-eval-best-fraction "$FINAL_EVAL_BEST_FRACTION" \
        --final-eval-worst-fraction "$FINAL_EVAL_WORST_FRACTION" \
        --final-eval-shape-power "$FINAL_EVAL_SHAPE_POWER" \
        --readability-weight 0.30 \
        --readability-floor 0.25 \
        --seeds "$METRIC_TEST_SEEDS" \
        --max-iter "$METRIC_TEST_MAX_ITER" \
        --jobs "$METRIC_TEST_CPU_JOBS" \
        --best "$METRIC_TEST_BEST_N" \
        --keep-best "$METRIC_TEST_KEEP_BEST" \
        --keep-worst 0 \
        --no-invert-twin \
        --no-export-best-by-bank \
        --db "$METRIC_CPU_DB" \
        --verbose \
        2>&1 | tee "$METRIC_CPU_LOG"
      METRIC_CPU_ELAPSED=$((SECONDS - METRIC_CPU_STARTED))

      "$PYTHON_BIN" - \
        "$METRIC_SUMMARY" \
        "$METRIC_CPU_LOG" \
        "$METRIC_CPU_ELAPSED" \
        "$METRIC_TEST_PRESETS" \
        "$METRIC_TEST_SEEDS" \
        "$METRIC_TEST_CPU_JOBS" \
        "$AUTO_DEVICE_SELECT" \
        "${AUTO_DEVICE_ENV:-$METRIC_DIR/device_autoselect.env}" \
        "$KAN_DEVICE" \
        "$JOBS" <<'PY'
import re
import sys
from pathlib import Path

xpu_summary = Path(sys.argv[1])
cpu_log = Path(sys.argv[2])
cpu_elapsed = max(0.0, float(sys.argv[3]))
presets = [x for x in sys.argv[4].split(",") if x.strip()]
seeds_spec = sys.argv[5]
cpu_jobs = sys.argv[6]
auto_select = str(sys.argv[7]).lower() in {"1", "true", "yes", "auto"}
auto_env = Path(sys.argv[8])
primary_device = sys.argv[9]
primary_jobs = sys.argv[10]

def count_seeds(spec: str) -> int:
    text = str(spec or "").strip()
    if not text:
        return 0
    if "," in text:
        return len([x for x in text.split(",") if x.strip()])
    if ":" in text:
        _, count = text.split(":", 1)
        return int(count)
    if text.startswith("@") or text.startswith("seed:"):
        return 1
    return int(text)

def read_summary_value(path: Path, key: str) -> float:
    if not path.exists():
        return 0.0
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(key + "="):
            try:
                return float(line.split("=", 1)[1])
            except ValueError:
                return 0.0
    return 0.0

def fmt(seconds: float) -> str:
    seconds = int(round(max(0.0, seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"

xpu_sec = read_summary_value(xpu_summary, "metric_sec_per_trial")
full_trials = read_summary_value(xpu_summary, "full_trials")
text = cpu_log.read_text(errors="replace") if cpu_log.exists() else ""
matches = list(re.finditer(r"\[\s*(\d+)/(\d+)\]\s+[0-9.]+%", text))
cpu_trials = int(matches[-1].group(1)) if matches else len(presets) * count_seeds(seeds_spec)
cpu_sec = cpu_elapsed / cpu_trials if cpu_trials else 0.0
cpu_tpm = 60.0 / cpu_sec if cpu_sec else 0.0
xpu_tpm = 60.0 / xpu_sec if xpu_sec else 0.0
speedup = cpu_sec / xpu_sec if cpu_sec and xpu_sec else 0.0
xpu_est = xpu_sec * full_trials if xpu_sec and full_trials else 0.0
cpu_est = cpu_sec * full_trials if cpu_sec and full_trials else 0.0

print(f"[speed-test] {primary_device} metric speed: {xpu_sec:.3f}s/tr ({xpu_tpm:.2f} tr/min)")
print(f"[speed-test] CPU metric speed: {cpu_sec:.3f}s/tr ({cpu_tpm:.2f} tr/min, jobs={cpu_jobs})")
if speedup:
    if speedup >= 1.0:
        print(f"[speed-test] {primary_device} is faster than CPU jobs={cpu_jobs}: {speedup:.2f}x")
    else:
        print(f"[speed-test] CPU jobs={cpu_jobs} is faster than {primary_device}: {1.0 / speedup:.2f}x")
        print(f"[speed-test] {primary_device} relative speed vs CPU jobs={cpu_jobs}: {speedup:.2f}x")
if xpu_est and cpu_est:
    print(f"[speed-test] Estimated full train: {primary_device} {fmt(xpu_est)} vs CPU jobs={cpu_jobs} {fmt(cpu_est)}")
if auto_select and speedup:
    if speedup >= 1.0:
        chosen_device = primary_device
        chosen_jobs = primary_jobs
        chosen_sec = xpu_sec
        reason = f"{primary_device} faster than CPU jobs={cpu_jobs}: {speedup:.2f}x"
    else:
        chosen_device = "cpu"
        chosen_jobs = cpu_jobs
        chosen_sec = cpu_sec
        reason = f"CPU jobs={cpu_jobs} faster than {primary_device}: {1.0 / speedup:.2f}x"
    auto_env.parent.mkdir(parents=True, exist_ok=True)
    auto_env.write_text(
        "\n".join(
            [
                f"AUTO_SELECTED_DEVICE={chosen_device}",
                f"AUTO_SELECTED_JOBS={chosen_jobs}",
                f"AUTO_SELECTED_SEC_PER_TRIAL={chosen_sec:.6f}",
                f"AUTO_SELECTED_REASON={reason!r}",
            ]
        )
        + "\n"
    )
    print(f"[device-auto] selected {chosen_device} jobs={chosen_jobs} ({reason})")
    print(f"[device-auto] env={auto_env}")
PY
      if [[ "$METRIC_TEST_CPU_COMPARE_ONCE" != "0" && -n "$METRIC_TEST_CPU_COMPARE_MARKER" ]]; then
        mkdir -p "$(dirname "$METRIC_TEST_CPU_COMPARE_MARKER")"
        touch "$METRIC_TEST_CPU_COMPARE_MARKER"
      fi
    fi
  fi
fi

if [[ "$AUTO_DEVICE_SELECT" == "1" || "$AUTO_DEVICE_SELECT" == "true" || "$AUTO_DEVICE_SELECT" == "yes" ]]; then
  AUTO_DEVICE_ENV_RESOLVED="${AUTO_DEVICE_ENV:-${METRIC_DIR:-$OUT_DIR}/device_autoselect.env}"
  if [[ -f "$AUTO_DEVICE_ENV_RESOLVED" ]]; then
    # shellcheck disable=SC1090
    source "$AUTO_DEVICE_ENV_RESOLVED"
    KAN_DEVICE="${AUTO_SELECTED_DEVICE:-$KAN_DEVICE}"
    JOBS="${AUTO_SELECTED_JOBS:-$JOBS}"
    echo "[device-auto] full training will use device=$KAN_DEVICE jobs=$JOBS"
    if [[ -n "${AUTO_SELECTED_REASON:-}" ]]; then
      echo "[device-auto] reason: $AUTO_SELECTED_REASON"
    fi
  else
    echo "[device-auto] warning: auto selection requested but no env file found; keeping device=$KAN_DEVICE jobs=$JOBS"
  fi
fi

echo ""
if [[ "$HYBRID_KAN" == "1" || "$HYBRID_KAN" == "true" || "$HYBRID_KAN" == "yes" ]]; then
  echo "[5/6] Train KAN + Deep hybrid monthly forecast..."
else
  echo "[5/6] Train KAN-only monthly forecast..."
fi

"$PYTHON_BIN" -u cli.py train \
  --task "$TRAIN_MASTER" \
  --target_cols_list "$TARGET_COL" \
  --skip_cols_list "$SKIP_COLS_LIST" \
  --no-banks \
  --enable-kan \
  --kan-presets "$KAN_PRESETS_RUN" \
  --kan-device "$KAN_DEVICE" \
  "${KAN_EXTRA_ARGS[@]}" \
  "${KAN_HYBRID_ARGS[@]}" \
  --metric-mode auto \
  --metric-target-threshold "$METRIC_TARGET_THRESHOLD" \
  --metric-prediction-threshold "$METRIC_PREDICTION_THRESHOLD" \
  --event-score-mode isolation \
  --target-window-threshold "$TARGET_WINDOW_THRESHOLD" \
  --target-window-event-count "$TARGET_EVENT_COUNT" \
  --target-window-pre-records "$VALIDATION_PRE_RECORDS" \
  --target-window-post-records "$VALIDATION_POST_RECORDS" \
  --isolated-event-windows \
  --recent-validation-window \
  --recent-validation-event-count "$VALIDATION_EVENT_COUNT" \
  --recent-validation-pre-records "$VALIDATION_PRE_RECORDS" \
  --recent-validation-post-records "$VALIDATION_POST_RECORDS" \
  --recent-validation-weight 3.0 \
  --recent-validation-random-negatives "$RECENT_VALIDATION_RANDOM_NEGATIVES" \
  --recent-validation-random-seed "$RECENT_VALIDATION_RANDOM_SEED" \
  --validation-max-lookback-records "$VALIDATION_MAX_LOOKBACK_RECORDS" \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date "$FORECAST_END" \
  --forecast-trainset train2forecast \
  --final-eval-rank-power 1.0 \
  --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight "$FINAL_EVAL_NEGATIVE_WEIGHT" \
  --final-eval-best-fraction "$FINAL_EVAL_BEST_FRACTION" \
  --final-eval-worst-fraction "$FINAL_EVAL_WORST_FRACTION" \
  --final-eval-shape-power "$FINAL_EVAL_SHAPE_POWER" \
  --readability-weight 0.30 \
  --readability-floor 0.25 \
  --seeds "$SEEDS_SPEC" \
  --max-iter "$MAX_ITER" \
  --jobs "$JOBS" \
  --best "$BEST_N" \
  --keep-best "$KEEP_BEST" \
  --keep-worst "$KEEP_WORST" \
  --no-invert-twin \
  --no-export-best-by-bank \
  --db "$DB_FILE" \
  --verbose

RUN_DIR="$(find "$OUT_DIR" -maxdepth 1 -type d -name 'pulsar_train*_best_trials_*' | sort | tail -n 1)"
[[ -n "$RUN_DIR" && -f "$RUN_DIR/best_trials_index.csv" ]] || {
  echo "[ERROR] Cannot find latest run/best_trials_index.csv under $OUT_DIR" >&2
  exit 1
}

echo ""
if [[ "$HYBRID_KAN" == "1" || "$HYBRID_KAN" == "true" || "$HYBRID_KAN" == "yes" ]]; then
  echo "[6/6] KAN + Deep hybrid strength fusion over monthly forecast..."
else
  echo "[6/6] KAN-only strength fusion over monthly forecast..."
fi
"$PYTHON_BIN" "$FUSION_PY" \
  --index-csv "$RUN_DIR/best_trials_index.csv" \
  --output-dir "$RUN_DIR/kan_may_dec_30d_strength_fusion" \
  --score-column auto \
  --top-n 0 \
  --threshold 0.5 \
  --max-peaks 2 \
  --rank-mode "$FUSION_RANK_MODE" \
  --inverse-worst-n "$FUSION_INVERSE_WORST_N" \
  --title "$FUSION_TITLE"

echo ""
echo "======================================================================"
echo " Worldwide M8.5+ 30d traditional nasaDb KAN run ready"
echo " Root:    $OUT_DIR"
echo " Run dir: $RUN_DIR"
echo " Master:  $MASTER"
if [[ "$TRAIN_MASTER" != "$MASTER" ]]; then
  echo " Train:   $TRAIN_MASTER"
fi
echo " Fusion:  $RUN_DIR/kan_may_dec_30d_strength_fusion"
echo " Log:     $LOG_FILE"
echo " Re-run:  $OUT_DIR/RUN_THIS_PIPELINE.sh"
echo "======================================================================"

#!/usr/bin/env bash
# Japan-zone M7.9+ profile: CPU3, no-history only, MI top-50, Deep hyper-pretest, direct full train.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"
DB_ROOT="${DB_ROOT:-/mnt/git0/git/repository/astro-USGS2/DB}"

export RUN_STAMP
export DB_ROOT
export MACRO_ROOT="${MACRO_ROOT:-$DB_ROOT/japan-zone-mag79plus-cpu3-nohist-hyper-top50-$RUN_STAMP}"

export RUN_PROFILE_NAME="${RUN_PROFILE_NAME:-cpu3_nohistory_hyper_top50}"
export RUN_COMMAND_HINT="${RUN_COMMAND_HINT:-commands/run_japan_zone_mag79_cpu3_nohistory_hyper_top50.sh}"
export RUN_COMMAND_REASON="${RUN_COMMAND_REASON:-Run only the no-history target variant, use MI top-50 feature preselect, run a lightweight DeepNet hyperparameter pretest that emits CSV/JSON manifests and generated deep presets, then spend the full train budget on fewer seeds but many KAN/deep/hybrid hyperparameter combinations. Worst-trial inversion/penalty is disabled because sparse saved bad trials can mislead forecast fusion.}"

export KAN_DEVICE="${KAN_DEVICE:-cpu}"
export DEEP_DEVICE="${DEEP_DEVICE:-cpu}"
export JOBS="${JOBS:-3}"
export ACCELERATOR_JOBS="${ACCELERATOR_JOBS:-3}"

export VARIANT_MODE="${VARIANT_MODE:-no-history-only}"
export VARIANTS_PER_PHASE="${VARIANTS_PER_PHASE:-1}"
export COUNTER_COUNT="${COUNTER_COUNT:-0}"

export METRIC_TEST="${METRIC_TEST:-0}"
export METRIC_TEST_CPU_COMPARE="${METRIC_TEST_CPU_COMPARE:-0}"
export AUTO_DEVICE_SELECT="${AUTO_DEVICE_SELECT:-0}"

export FEATURE_PRESELECT="${FEATURE_PRESELECT:-1}"
export FEATURE_PRESELECT_REBUILD="${FEATURE_PRESELECT_REBUILD:-1}"
export FEATURE_SELECTION_K_BEST="${FEATURE_SELECTION_K_BEST:-50}"
export FEATURE_SELECTION_THRESHOLD="${FEATURE_SELECTION_THRESHOLD-}"
export FEATURE_SELECTION_PERCENTILE="${FEATURE_SELECTION_PERCENTILE-}"
export FEATURE_SELECTION_MIN_FEATURES="${FEATURE_SELECTION_MIN_FEATURES:-10}"
export FEATURE_SELECTION_MAX_FEATURES="${FEATURE_SELECTION_MAX_FEATURES:-50}"

export HYPER_PRETEST="${HYPER_PRETEST:-1}"
export HYPER_PRETEST_TOP_N="${HYPER_PRETEST_TOP_N:-5}"
export HYPER_PRETEST_SEEDS="${HYPER_PRETEST_SEEDS:-3}"
export HYPER_PRETEST_EPOCHS="${HYPER_PRETEST_EPOCHS:-80}"
export HYPER_PRETEST_FULL_EPOCHS="${HYPER_PRETEST_FULL_EPOCHS:-240}"
export HYPER_PRETEST_DEVICE="${HYPER_PRETEST_DEVICE:-cpu}"

export HYBRID_KAN="${HYBRID_KAN:-1}"
export KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny,small,wide}"
export DEEP_PRESETS_RUN="${DEEP_PRESETS_RUN:-tiny,small,wide,default,deep}"
export HYBRID_KAN_PARTNERS="${HYBRID_KAN_PARTNERS:-deep:tiny,deep:small,deep:wide,deep:default,deep:deep}"
export HYBRID_KAN_MODES="${HYBRID_KAN_MODES:-weighted}"
export HYBRID_KAN_ALPHAS="${HYBRID_KAN_ALPHAS:-0.35,0.5,0.65}"
export HYBRID_KAN_THRESHOLD="${HYBRID_KAN_THRESHOLD:-0.5}"

export SEEDS_SPEC="${SEEDS_SPEC:-4:4}"
export MAX_ITER="${MAX_ITER:-1500}"
export BEST_N="${BEST_N:-160}"
export KEEP_BEST="${KEEP_BEST:-80}"
export KEEP_WORST="${KEEP_WORST:-0}"
export FUSION_INVERSE_WORST_N="${FUSION_INVERSE_WORST_N:-0}"
export FINAL_EVAL_NEGATIVE_WEIGHT="${FINAL_EVAL_NEGATIVE_WEIGHT:-0.0}"
export FINAL_EVAL_BEST_FRACTION="${FINAL_EVAL_BEST_FRACTION:-0.75}"
export FINAL_EVAL_WORST_FRACTION="${FINAL_EVAL_WORST_FRACTION:-0.0}"
export FINAL_EVAL_SHAPE_POWER="${FINAL_EVAL_SHAPE_POWER:-0.5}"

export RUN_30D="${RUN_30D:-1}"
export RUN_7D="${RUN_7D:-1}"
export RUN_3D="${RUN_3D:-1}"

echo "======================================================================"
echo " Japan-zone M7.9+ CPU3 no-history hyper top-50 wrapper"
echo " Macro root:       $MACRO_ROOT"
echo " Device:           KAN=$KAN_DEVICE Deep=$DEEP_DEVICE jobs=$JOBS"
echo " Variants:         mode=$VARIANT_MODE counters=$COUNTER_COUNT"
echo " Feature policy:   k_best=$FEATURE_SELECTION_K_BEST min/max=$FEATURE_SELECTION_MIN_FEATURES/$FEATURE_SELECTION_MAX_FEATURES"
echo " Hyper pretest:    enabled=$HYPER_PRETEST top_n=$HYPER_PRETEST_TOP_N seeds=$HYPER_PRETEST_SEEDS"
echo " Full train:       seeds=$SEEDS_SPEC max_iter=$MAX_ITER best=$BEST_N keep_best=$KEEP_BEST keep_worst=$KEEP_WORST"
echo " Final eval:       neg_weight=$FINAL_EVAL_NEGATIVE_WEIGHT worst_frac=$FINAL_EVAL_WORST_FRACTION"
echo "======================================================================"

commands/run_japan_zone_mag79_30d_7d_3d_proximity_xpu_24h.sh "$@"

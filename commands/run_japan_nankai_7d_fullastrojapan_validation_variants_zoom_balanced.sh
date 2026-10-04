#!/usr/bin/env bash
# Balanced FullAstroJapan 7d Japan/Nankai validation-variants pipeline.
#
# This is a fairness-oriented wrapper around:
#   run_japan_nankai_7d_fullastrojapan_validation_variants_zoom.sh
#
# Per seed, with the defaults below, the rough trial budget is:
#   analog bank/readout: 5 banks x 2 readouts = 10
#   LCS family:          1 pure LCS + 5 partners x 3 modes = 16
#   KAN family:          1 pure KAN + 5 partners x 3 modes = 16
#
# So KAN is still tested as a real competitor, but does not get the much larger
# search budget caused by multiple KAN presets and multiple weighted alphas.
set -euo pipefail

cd "$(dirname "$0")/.."

ASTRO_ROOT="${ASTRO_ROOT:-/mnt/git0/git/repository/astro-USGS2}"

export OUT_ROOT="${OUT_ROOT:-$ASTRO_ROOT/DB/japan-nankai-big-one-7d-fullastrojapan-neganchors-validation-variants-zoom-balanced}"
export COMPARE_ROOT="${COMPARE_ROOT:-$OUT_ROOT/final_variant_consensus}"

export ENABLE_KAN="${ENABLE_KAN:-1}"
export HYBRID_KAN="${HYBRID_KAN:-1}"
export ENABLE_KAN_IN_MAX="${ENABLE_KAN_IN_MAX:-1}"
export KAN_PRESETS_RUN="${KAN_PRESETS_RUN:-tiny}"
export KAN_DEVICE="${KAN_DEVICE:-cpu}"

export BANKS="${BANKS:-passthrough,random_fourier,prime_fourier,chebyshev,morlet_wavelet}"
export READOUTS="${READOUTS:-ridge,linear}"
export HYBRID_PARTNERS="${HYBRID_PARTNERS:-passthrough:ridge,random_fourier:ridge,prime_fourier:linear,chebyshev:ridge,morlet_wavelet:linear}"
export HYBRID_MODES="${HYBRID_MODES:-and,or,weighted}"
export HYBRID_ALPHAS="${HYBRID_ALPHAS:-0.5}"

export SEEDS_SPEC="${SEEDS_SPEC:-4,5,6,7,8,9,10,11}"
export MAX_ITER="${MAX_ITER:-160}"
export JOBS="${JOBS:-1}"

export LCS_CUSTOM="${LCS_CUSTOM:-1}"
export LCS_POPULATION_SIZE="${LCS_POPULATION_SIZE:-40}"
export LCS_GA_FREQUENCY="${LCS_GA_FREQUENCY:-120}"
export LCS_MAX_ACTIVE_CONDITIONS="${LCS_MAX_ACTIVE_CONDITIONS:-2}"
export LCS_EXPORT_RULE_COUNT="${LCS_EXPORT_RULE_COUNT:-4}"

echo "======================================================================"
echo " Japan/Nankai 7d validation variants - BALANCED KAN/LCS budget"
echo " Output root:    $OUT_ROOT"
echo " Per seed budget: analog=10, LCS-family=16, KAN-family=16"
echo " KAN:            enable=$ENABLE_KAN presets=$KAN_PRESETS_RUN hybrid=$HYBRID_KAN"
echo " Banks:          $BANKS"
echo " Readouts:       $READOUTS"
echo " Hybrid partners:$HYBRID_PARTNERS"
echo " Hybrid modes:   $HYBRID_MODES alpha=$HYBRID_ALPHAS"
echo " Seeds/iter/jobs:$SEEDS_SPEC / $MAX_ITER / $JOBS"
echo "======================================================================"

exec "$PWD/commands/run_japan_nankai_7d_fullastrojapan_validation_variants_zoom.sh"

#!/usr/bin/env bash
# Japan/Nankai 360d pipeline variant:
# keep the original 1498 historical start and exclude Mars if Horizons lacks
# Mars vectors before A.D. 1600.
set -euo pipefail

cd "$(dirname "$0")/.."

export START_DATE="${START_DATE:-1498-01-01}"
export OUT_DIR="${OUT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d-from1498-no-mars}"
export DB_FILE="${DB_FILE:-japan_nankai_360d_from1498_no_mars.db}"
export LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_from1498_no_mars.log}"
export EXCLUDE_BODIES="${EXCLUDE_BODIES:-mars}"
export ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"

./commands/run_japan_nankai_360d_final.sh

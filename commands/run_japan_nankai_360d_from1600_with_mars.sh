#!/usr/bin/env bash
# Japan/Nankai 360d pipeline variant:
# keep Mars and start after the Horizons lower bound reported for Mars.
set -euo pipefail

cd "$(dirname "$0")/.."

export START_DATE="${START_DATE:-1600-01-02}"
export OUT_DIR="${OUT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d-from1600-with-mars}"
export DB_FILE="${DB_FILE:-japan_nankai_360d_from1600_with_mars.db}"
export LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_from1600_with_mars.log}"
export EXCLUDE_BODIES="${EXCLUDE_BODIES:-}"
export ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"

./commands/run_japan_nankai_360d_final.sh

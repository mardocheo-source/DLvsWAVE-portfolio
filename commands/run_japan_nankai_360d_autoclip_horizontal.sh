#!/usr/bin/env bash
# Japan/Nankai 360d pipeline variant:
# auto-clip horizontally, meaning the requested date range is shortened when
# Horizons reports a parsable per-body temporal bound.
set -euo pipefail

cd "$(dirname "$0")/.."

export START_DATE="${START_DATE:-1498-01-01}"
export OUT_DIR="${OUT_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-big-one-360d-autoclip-horizontal}"
export DB_FILE="${DB_FILE:-japan_nankai_360d_autoclip_horizontal.db}"
export LOG_FILE="${LOG_FILE:-/tmp/dlvswave_japan_nankai_360d_autoclip_horizontal.log}"
export AUTO_CLIP="${AUTO_CLIP:-horizontal}"
export ON_BODY_ERROR="${ON_BODY_ERROR:-fail}"

./commands/run_japan_nankai_360d_final.sh

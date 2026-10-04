#!/usr/bin/env bash
# japan_shift7d_full.sh
#
# Pipeline Japan 30d shift+7d (TIME_BEFORE=173d)
# Per triangolazione temporale del forecast: confronta con shift+14d, +15d, +21d.
#
# Uso:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./examples/japan_shift7d_full.sh
set -euo pipefail
cd "$(dirname "$0")/.."

EVENTS="/mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/earthquakes.RAW.csv"

./commands/run_japan_30d_pipeline.sh \
  --events         "$EVENTS" \
  --shift-days     7 \
  --forecast-start 2026-04-01 \
  --forecast-end   2026-09-30 \
  --db             japan_30d_shift7d.db

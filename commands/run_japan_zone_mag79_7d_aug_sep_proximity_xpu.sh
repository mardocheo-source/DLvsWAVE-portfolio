#!/usr/bin/env bash
# Convenience launcher for the prepared 7d Japan/proximity countercheck macro.
set -euo pipefail

cd "$(dirname "$0")/.."

MACRO="/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-7d-aug-sep-proximity-check/RUN_GEOGRAPHIC_COUNTERCHECK.sh"
HISTORY_NEGATIVE_SAMPLING_MODE="${HISTORY_NEGATIVE_SAMPLING_MODE:-none}"
export HISTORY_NEGATIVE_SAMPLING_MODE
NASA_DAILY_MASTER_MODE="${NASA_DAILY_MASTER_MODE:-1}"
NASA_SLOT_ADVANCED_STATS="${NASA_SLOT_ADVANCED_STATS:-1}"
export NASA_DAILY_MASTER_MODE NASA_SLOT_ADVANCED_STATS

echo "======================================================================"
echo " Japan-zone M7.9+ 7d Aug-Sep 2026 proximity countercheck XPU"
echo " Macro: $MACRO"
echo " Note:  forecast grid is 2026-07-27 -> 2026-10-05,"
echo "        covering requested Aug-Sep 2026 at true 7d nasaDb cadence."
echo "======================================================================"

exec "$MACRO"

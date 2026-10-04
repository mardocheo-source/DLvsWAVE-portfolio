#!/usr/bin/env bash
# japan_shift15d_full.sh
#
# Pipeline completa Japan MAG8.0+ — griglia 30d shift+15d
# Master creation + training Pulsar + smart merge forecast apr-set 2026
#
# Durata attesa: ~6-8h (2-4h master NASA + 3.5-4h training)
# Output: pulsar_train_best_trials_*/post_hybrid_checks_smart/smart_result/
#
# Uso:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./examples/japan_shift15d_full.sh
set -euo pipefail
cd "$(dirname "$0")/.."

EVENTS="/mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/earthquakes.RAW.csv"

./commands/run_japan_30d_pipeline.sh \
  --events         "$EVENTS" \
  --shift-days     15 \
  --forecast-start 2026-04-01 \
  --forecast-end   2026-09-30 \
  --db             japan_30d_shift15d.db

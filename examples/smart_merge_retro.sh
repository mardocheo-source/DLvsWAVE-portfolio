#!/usr/bin/env bash
# smart_merge_retro.sh
#
# Esegui lo smart merge su un training già completato, senza rifare il training.
# Utile per:
#   - ricalcolare il merge con parametri diversi (peak-max, peak-floor, ecc.)
#   - testare nuove versioni di post_hybrid_pair_smart.py
#   - rigenerare i PNG/report dopo modifiche ai diagrammi
#
# Uso:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   RUN_DIR=/path/to/pulsar_train_best_trials_YYYYMMDD-HHMMSS \
#   ./examples/smart_merge_retro.sh
#
# Oppure con variabile inline:
#   ./examples/smart_merge_retro.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# ── Configura qui il run dir del training ─────────────────────────────────────
RUN_DIR="${RUN_DIR:-/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift15d/pulsar_train_best_trials_20260504-203350}"
OUT_DIR="/tmp/smart_merge_retro_$(date +%Y%m%d-%H%M%S)"

[[ -d "$RUN_DIR" ]] || { echo "[ERRORE] RUN_DIR non trovato: $RUN_DIR" >&2; exit 1; }

echo "======================================================================"
echo " Smart merge retro"
echo " RUN_DIR: $RUN_DIR"
echo " OUT_DIR: $OUT_DIR"
echo "======================================================================"

./.venv/bin/python post_hybrid_pair_smart.py \
  "$RUN_DIR" \
  --dataset-subfolder master_with_usgs_core_astrofmt \
  --out-dir       "$OUT_DIR" \
  --score-column  predicted \
  --peak-and \
  --peak-window   1 \
  --peak-floor    0.30 \
  --peak-max      1

echo ""
echo "Output: $OUT_DIR"
FORECAST=$(find "$OUT_DIR/smart_result" -name "*forecast.csv" 2>/dev/null | head -1)
if [[ -n "$FORECAST" ]]; then
    echo "Forecast:"
    cat "$FORECAST"
fi

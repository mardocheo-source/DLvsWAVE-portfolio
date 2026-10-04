#!/usr/bin/env bash
# Pulsar training Japan MAG8.0+ — master 30d shift+15d — forecast apr-set 2026
#
# Durata attesa: ~3.5-4h
#   Trial: 4 seed × (3 bank × 2 readout + 2 LCS + 3 hybrid partner) × 2 pass
#   Master: 1428 records a 30d (vs 5062 a 7d → ~3.5x più veloce per trial)
#   max-iter=150 su LCS per compensare i 4 seed
#
# Feature: solo astronomiche — skip_cols include date,depth,latitude,longitude
# Forecast: 2026-04-01 → 2026-09-30
# Merge finale: post-hybrid-mode both (artifacts + smart)
#   - artifacts: genera post_hybrid_pair_proposals.csv (best hybrid/LCS × best analog)
#   - smart: shape_quality() penalizza segnali piatti/saturi/stuck nel forecast
#   - post-hybrid-forecast-guard auto: esclude forecast degeneri
#   - recent-validation-weight 3.0: validation include evento finale recente
#
# Hybrid partners (vs run originale):
#   deep:tiny       → genera hyb_*_dntiny_w0p50 (vincitore nel run di riferimento F1=0.857)
#   passthrough:ridge → analog di riferimento classico per il pair selection
#   morlet_wavelet:torch_wide → analog wavelet
#
# Prerequisito: master creato con:
#   astro-USGS2/commands/create_master_japan_mag80_30d_shift15d.sh
#
# Uso:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/train_japan_30d_shift15d_fast.sh
set -e

cd "$(dirname "$0")/.."

MASTER="${MASTER:-/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift15d/master_with_usgs_core_astrofmt.csv}"

[[ -f "$MASTER" ]] || {
    echo "[ERRORE] Master non trovato: $MASTER" >&2
    echo "         Esegui prima: astro-USGS2/commands/create_master_japan_mag80_30d_shift15d.sh" >&2
    echo "         Il master training-ready e': master_with_usgs_core_astrofmt.csv" >&2
    echo "         (feature astronomiche quantizzate a quartili 0-3, sismiche float)" >&2
    exit 1
}

echo "======================================================================"
echo " Japan 30d shift+15d — Pulsar fast training"
echo " Master: $MASTER"
echo " Forecast: 2026-04-01 → 2026-09-30"
echo " Trial: 4 seed × (3 bank × 2 readout + 2 LCS + 3 hybrid)  Atteso ~3.5-4h"
echo "======================================================================"

export PYTHONUNBUFFERED=1

./.venv/bin/python -u cli.py train \
  --task "$MASTER" \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  \
  --banks passthrough,chebyshev,morlet_wavelet \
  --readouts torch_tiny,ridge \
  --lcs-presets tiny,default \
  --hybrid-lcs \
  --hybrid-partners morlet_wavelet:torch_wide,passthrough:ridge,deep:tiny \
  --hybrid-modes weighted,and \
  --hybrid-alphas 0.35,0.5 \
  --hybrid-threshold 0.5 \
  \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --metric-prediction-threshold 0.5 \
  --event-score-mode isolation \
  --target-window-threshold 0.1 \
  --target-window-event-count 1 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --isolated-event-windows \
  \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 2 \
  --backtest-max-windows 1 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  \
  --recent-validation-window \
  --recent-validation-event-count 1 \
  --recent-validation-pre-records 5 \
  --recent-validation-post-records 3 \
  --recent-validation-weight 3.0 \
  \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  \
  --forecast-start-date 2026-04-01 \
  --forecast-end-date 2026-09-30 \
  --forecast-trainset train2forecast \
  \
  --final-eval-rank-power 1.0 \
  --final-eval-low-threshold 1e-9 \
  --final-eval-negative-weight 3.0 \
  --final-eval-best-fraction 0.30 \
  --final-eval-worst-fraction 0.12 \
  --final-eval-shape-power 1.5 \
  --readability-weight 0.35 \
  --readability-floor 0.3 \
  \
  --auto-inherit-levels 0 \
  --seeds 4:4 \
  --max-iter 150 \
  --best 8 \
  --keep-best 3 \
  --keep-worst 2 \
  --invert-twin-min-std 1e-4 \
  --lcs-max-active-conditions 8 \
  --lcs-min-fitness-for-subsumption 0.65 \
  \
  --post-hybrid-artifacts \
  --post-hybrid-mode both \
  --post-hybrid-logic and \
  --post-hybrid-normalize auto \
  --post-hybrid-forecast-guard auto \
  --post-hybrid-peak-and \
  --post-hybrid-peak-window 1 \
  --post-hybrid-peak-floor 0.30 \
  --post-hybrid-peak-max 1 \
  # Obiettivo: trovare il "big one" di agosto (1 picco AND confermato).
  # Per affinare la finestra temporale: run shiftati +7d, +14d, +21d
  # a confronto per vedere quale shift mostra agosto più robusto.
  \
  --db japan_30d_shift15d_fast.db \
  --verbose \
  2>&1 | tee /tmp/dlvswave_japan_30d_shift15d_fast.log

#!/usr/bin/env bash
# run_japan_30d_pipeline.sh
#
# Pipeline completa: master 30d shift+Nd → training Pulsar → smart merge.
# Un singolo script parametrico per run comparativi con shift differenti
# (es. +7d, +14d, +15d, +21d) senza duplicare script.
#
# Uso:
#   cd /mnt/git0/git/repository/DLvsWAVE
#   ./commands/run_japan_30d_pipeline.sh --events /path/to/earthquakes.RAW.csv
#
# Argomenti:
#   --events PATH         File eventi sismici (USGS RAW CSV).
#                         Obbligatorio se --skip-master non è passato e
#                         il file di riferimento storico non è presente.
#   --out-dir PATH        Cartella output master [default auto da --shift-days]
#   --shift-days N        Shift griglia NASA in giorni [default: 15]
#                         TIME_BEFORE = 180 − N giorni
#   --forecast-start DATE Data inizio forecast [default: 2026-04-01]
#   --forecast-end   DATE Data fine forecast   [default: 2026-09-30]
#   --db NAME             Nome SQLite DB training [default: japan_30d_shift{N}d.db]
#   --seeds S             Range semi Pulsar [default: 4:4]
#   --max-iter N          Iterazioni LCS [default: 150]
#   --skip-master         Salta creazione master (usa master già presente)
#   --help                Mostra questo aiuto
#
# Esempio run shift+7d:
#   ./commands/run_japan_30d_pipeline.sh \
#     --events /path/to/earthquakes.RAW.csv \
#     --shift-days 7 \
#     --forecast-start 2026-04-01 \
#     --forecast-end 2026-09-30
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DLVSWAVE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ASTRO_ROOT="$(cd "$DLVSWAVE_ROOT/../astro-USGS2" && pwd)"

# ── Default parametri ─────────────────────────────────────────────────────────
EVENTS_CSV=""
SHIFT_DAYS=15
OUT_DIR=""                   # calcolato dopo il parse
FORECAST_START="2026-04-01"
FORECAST_END="2026-09-30"
DB_NAME=""                   # calcolato dopo il parse
SEEDS="4:4"
MAX_ITER=150
SKIP_MASTER=0

# Parametri NASA (raramente da cambiare)
STEP_INTERVAL="30d"
TIME_AFTER="240d"
TEST_START_DATE="2026-01-01"
TEST_END_DATE="2026-12-31"
QUANT_BINS=4

# Script build master (path standard)
ADD_USGS_PY="$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/add_usgs_core_columns_to_master.py"
CONV_PY="$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/convert_astro_columns_to_standard.py"
QUANT_PY="$ASTRO_ROOT/DB/world-mag85-7d-to-2026-05/quantize_master_quartiles.py"

# Riferimento USGS (riusato se disponibile e --events non passato)
REF_USGS_DEFAULT="$ASTRO_ROOT/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/earthquakes.RAW.csv"

# ── Parse argomenti ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --events)         EVENTS_CSV="$2";       shift 2 ;;
        --out-dir)        OUT_DIR="$2";           shift 2 ;;
        --shift-days)     SHIFT_DAYS="$2";        shift 2 ;;
        --forecast-start) FORECAST_START="$2";    shift 2 ;;
        --forecast-end)   FORECAST_END="$2";      shift 2 ;;
        --db)             DB_NAME="$2";           shift 2 ;;
        --seeds)          SEEDS="$2";             shift 2 ;;
        --max-iter)       MAX_ITER="$2";          shift 2 ;;
        --skip-master)    SKIP_MASTER=1;          shift ;;
        --help|-h)        sed -n '2,/^set /{ /^set /q; s/^# \?//; p }' "$0"; exit 0 ;;
        *) echo "[ERRORE] Argomento sconosciuto: $1" >&2; exit 1 ;;
    esac
done

# ── Valori derivati ───────────────────────────────────────────────────────────
TIME_BEFORE_DAYS=$(( 180 - SHIFT_DAYS ))
TIME_BEFORE="${TIME_BEFORE_DAYS}d"

[[ -z "$OUT_DIR" ]] && \
    OUT_DIR="$ASTRO_ROOT/DB/japan-mag80-1900plus-30d-shift${SHIFT_DAYS}d"

[[ -z "$DB_NAME" ]] && \
    DB_NAME="japan_30d_shift${SHIFT_DAYS}d.db"

MASTER="$OUT_DIR/master_with_usgs_core_astrofmt.csv"
LOG="/tmp/dlvswave_japan_30d_shift${SHIFT_DAYS}d_$(date +%Y%m%d-%H%M%S).log"

echo "======================================================================"
echo " Japan 30d shift+${SHIFT_DAYS}d — Pipeline master + training + smart merge"
echo " ASTRO_ROOT:       $ASTRO_ROOT"
echo " OUT_DIR (master): $OUT_DIR"
echo " EVENTS_CSV:       ${EVENTS_CSV:-(usa REF_USGS storico o download USGS)}"
echo " TIME_BEFORE:      $TIME_BEFORE  (180 − $SHIFT_DAYS = $TIME_BEFORE_DAYS gg)"
echo " STEP_INTERVAL:    $STEP_INTERVAL"
echo " FORECAST:         $FORECAST_START → $FORECAST_END"
echo " DB:               $DB_NAME"
echo " SEEDS:            $SEEDS   MAX_ITER: $MAX_ITER"
echo " SKIP_MASTER:      $SKIP_MASTER"
echo " LOG:              $LOG"
echo "======================================================================"

# ── FASE 1: Creazione master ──────────────────────────────────────────────────
if [[ $SKIP_MASTER -eq 0 ]]; then
    echo ""
    echo "[1/2] Creazione master 30d shift+${SHIFT_DAYS}d..."

    [[ -f "$ADD_USGS_PY" ]] || { echo "[ERRORE] Non trovato: $ADD_USGS_PY" >&2; exit 1; }
    [[ -f "$CONV_PY" ]]     || { echo "[ERRORE] Non trovato: $CONV_PY" >&2; exit 1; }
    [[ -f "$QUANT_PY" ]]    || { echo "[ERRORE] Non trovato: $QUANT_PY" >&2; exit 1; }
    [[ -f "$ASTRO_ROOT/nasaDb.py" ]] || { echo "[ERRORE] nasaDb.py non trovato in $ASTRO_ROOT" >&2; exit 1; }

    mkdir -p "$OUT_DIR" "$OUT_DIR/nasa_bodies" "$OUT_DIR/nasa_bodies_backup"

    # ── Step 1: USGS events ──────────────────────────────────────────────────
    echo ""
    echo "[1a] USGS events..."
    if [[ -n "$EVENTS_CSV" && -f "$EVENTS_CSV" ]]; then
        cp "$EVENTS_CSV" "$OUT_DIR/earthquakes.RAW.csv"
        echo "[INFO] Usato --events: $EVENTS_CSV"
    elif [[ -f "$REF_USGS_DEFAULT" ]]; then
        cp "$REF_USGS_DEFAULT" "$OUT_DIR/earthquakes.RAW.csv"
        echo "[INFO] Usato file di riferimento storico: $REF_USGS_DEFAULT"
    else
        echo "[INFO] --events non passato e ref storico assente → download da USGS..."
        python "$ASTRO_ROOT/usgsDb.py" \
            --starttime 1904-01-01 --endtime 2026-12-31 \
            --lat-min 20 --lat-max 40 --lon-min -179 --lon-max 179 \
            --min-mag 8.0 --max-mag 10.0 \
            --raw-output "$OUT_DIR/earthquakes.RAW.csv" \
            --grouped-output "$OUT_DIR/earthquakesGrouped.1.csv" \
            --grouping-days 1 --expand 0.0 --overwrite
    fi

    [[ -f "$OUT_DIR/earthquakes.RAW.csv" ]] || \
        { echo "[ERRORE] earthquakes.RAW.csv non creato." >&2; exit 1; }
    echo "[OK] USGS: $(wc -l < "$OUT_DIR/earthquakes.RAW.csv") righe"

    # ── Step 2: NASA ephemeris ────────────────────────────────────────────────
    echo ""
    echo "[1b] NASA effemeridi (TIME_BEFORE=$TIME_BEFORE step=$STEP_INTERVAL)..."
    echo "     Stima: 2-4 ore (download fresco da JPL Horizons)."

    python "$ASTRO_ROOT/nasaDb.py" \
        --csv_file           "$OUT_DIR/earthquakes.RAW.csv" \
        --datetime_column    time \
        --time_before        "$TIME_BEFORE" \
        --time_after         "$TIME_AFTER" \
        --step_interval      "$STEP_INTERVAL" \
        --start_date         "$TEST_START_DATE" \
        --end_date           "$TEST_END_DATE" \
        --observer-geo="34.5,137.5,0,japan" \
        --place              earthFull \
        --bodies_dir         "$OUT_DIR/nasa_bodies" \
        --backup_dir         "$OUT_DIR/nasa_bodies_backup" \
        --master_output      "$OUT_DIR/nasa_master_focus_sparse.csv" \
        --raw_output         "$OUT_DIR/nasa_master_focus_sparse.Raw.csv" \
        --command_script     "$OUT_DIR/2-nasa_download.replay.sh" \
        --random-background  730d \
        --quiet-background-percent 0.0 \
        --quiet-window-radius 7d \
        --random-event-window 120d \
        --random-event-count 4 \
        --background-output  "$OUT_DIR/nasa_background_sparse.csv" \
        --max_workers 4 --progress --chunk-manifest

    [[ -f "$OUT_DIR/nasa_master_focus_sparse.csv" ]] || \
        { echo "[ERRORE] nasa_master_focus_sparse.csv non creato." >&2; exit 1; }
    echo "[OK] NASA master: $(wc -l < "$OUT_DIR/nasa_master_focus_sparse.csv") righe"

    # ── Step 3: Build master + convert colonne ────────────────────────────────
    echo ""
    echo "[1c] Build master (add USGS core + astrofmt)..."

    python "$ADD_USGS_PY" \
        --nasa-master "$OUT_DIR/nasa_master_focus_sparse.csv" \
        --usgs-events "$OUT_DIR/earthquakes.RAW.csv" \
        --output      "$OUT_DIR/master_with_usgs_core.csv"

    python "$CONV_PY" \
        --input-csv  "$OUT_DIR/master_with_usgs_core.csv" \
        --output-csv "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv"

    # ── Step 4: Quantizzazione quartile ──────────────────────────────────────
    echo ""
    echo "[1d] Quantizzazione quartile (bins=$QUANT_BINS) → $MASTER"

    python "$QUANT_PY" \
        --input-csv  "$OUT_DIR/master_with_usgs_core_astrofmt_float.csv" \
        --output-csv "$MASTER" \
        --bins       "$QUANT_BINS"

    N_ROWS=$(wc -l < "$MASTER")
    N_COLS=$(head -1 "$MASTER" | tr ',' '\n' | wc -l)
    FIRST_DATE=$(awk -F',' 'NR==2{print $1}' "$MASTER")
    LAST_DATE=$(awk -F',' 'END{print $1}' "$MASTER")
    echo "[OK] Master: $N_ROWS righe  $N_COLS colonne  $FIRST_DATE → $LAST_DATE"
else
    echo "[SKIP] Creazione master saltata."
fi

# ── Verifica master ───────────────────────────────────────────────────────────
[[ -f "$MASTER" ]] || {
    echo "[ERRORE] Master non trovato: $MASTER" >&2
    echo "         Rimuovi --skip-master o passa --out-dir corretto." >&2
    exit 1
}

# ── FASE 2: Training Pulsar + smart merge ─────────────────────────────────────
echo ""
echo "[2/2] Training Pulsar + smart merge..."
echo "  Master: $MASTER"
echo "  DB:     $DB_NAME"
echo "  Log:    $LOG"
echo ""

export PYTHONUNBUFFERED=1

"$DLVSWAVE_ROOT/.venv/bin/python" -u "$DLVSWAVE_ROOT/cli.py" train \
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
  --forecast-start-date "$FORECAST_START" \
  --forecast-end-date   "$FORECAST_END" \
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
  --seeds "$SEEDS" \
  --max-iter "$MAX_ITER" \
  --best 8 \
  --keep-best 3 \
  --keep-worst 2 \
  --invert-twin-min-std 1e-4 \
  --lcs-max-active-conditions 8 \
  --lcs-min-fitness-for-subsumption 0.65 \
  \
  --post-hybrid-artifacts \
  --post-hybrid-mode smart \
  --post-hybrid-logic and \
  --post-hybrid-normalize auto \
  --post-hybrid-forecast-guard auto \
  --post-hybrid-peak-and \
  --post-hybrid-peak-window 1 \
  --post-hybrid-peak-floor 0.30 \
  --post-hybrid-peak-max 1 \
  \
  --db "$DB_NAME" \
  --verbose \
  2>&1 | tee "$LOG"

echo ""
echo "======================================================================"
echo " PIPELINE COMPLETATA"
echo " Log:    $LOG"
echo " Master: $MASTER"
RUN_DIR=$(find "$DLVSWAVE_ROOT" -maxdepth 2 -name "pulsar_train_best_trials_*" -type d \
          2>/dev/null | sort -r | head -1)
if [[ -n "$RUN_DIR" ]]; then
    SMART_OUT="$RUN_DIR/post_hybrid_checks_smart"
    echo " Smart merge output: $SMART_OUT"
    if [[ -d "$SMART_OUT/smart_result" ]]; then
        FC=$(find "$SMART_OUT/smart_result" -name "*forecast.csv" | head -1)
        [[ -n "$FC" ]] && echo " Forecast CSV: $FC"
    fi
fi
echo "======================================================================"

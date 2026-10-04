# Smart Merge Pipeline — Japan 30d Seismic Forecast

Documentazione della pipeline completa per forecast sismico Japan MAG8.0+
a risoluzione 30d con selezione automatica della coppia via **smart merge**.

---

## Indice

1. [Architettura](#architettura)
2. [Script unificato `run_japan_30d_pipeline.sh`](#script-unificato)
3. [Esempi rapidi](#esempi-rapidi)
4. [Smart merge standalone (`post_hybrid_pair_smart.py`)](#smart-merge-standalone)
5. [Output: struttura e report](#output-struttura-e-report)
6. [Peak-AND: rilevamento picchi auto-normalizzato](#peak-and)
7. [Triangolazione shift: trovare il big one](#triangolazione-shift)

---

## Architettura

```
earthquakes.RAW.csv          (eventi USGS Japan MAG>=8.0)
        │
        ▼
  nasaDb.py                  Step 1-4: master creation
  (TIME_BEFORE = 180 − shift_days, step = 30d)
        │
        ▼
  master_with_usgs_core_astrofmt.csv   (~1428 righe, ~357 colonne)
        │
        ▼
  cli.py train               Training Pulsar: BANK ⊗ LCS ⊗ HYBRID
  (4 semi × 3 bank × 2 readout + 2 LCS + 3 hybrid partner)
        │
        ▼
  post_hybrid_pair_smart.py  Smart merge automatico
  (selezione coppia BANK⊗HYBRID, fusione a due stadi interna)
        │
        ▼
  smart_result/              Forecast apr-set 2026 + lineage diagram
```

### Fusione a due stadi (interna)

Lo smart merge esegue tre passi **senza scrivere cartelle intermedie**:

1. **Shape winner** (tmpdir): seleziona la coppia con forecast più "sano"
   (shape_quality: penalizza segnali piatti, saturi, stuck)
2. **Peak winner** (tmpdir): seleziona la coppia con picco principale più forte
3. **Smart result** (disco): merge dei due merge con `peak_and` → **1 sola cartella**

Il `best_effort_summary.json` nella root contiene i dettagli interni per debug.

---

## Script unificato

```
commands/run_japan_30d_pipeline.sh
```

**Parametri principali:**

| Argomento | Default | Descrizione |
|-----------|---------|-------------|
| `--events PATH` | *(ref storico o download)* | CSV eventi USGS (earthquakes.RAW.csv) |
| `--out-dir PATH` | `DB/japan-mag80-1900plus-30d-shift{N}d` | Cartella master output |
| `--shift-days N` | `15` | Shift griglia NASA in giorni (TIME_BEFORE = 180−N) |
| `--forecast-start DATE` | `2026-04-01` | Inizio finestra forecast |
| `--forecast-end DATE` | `2026-09-30` | Fine finestra forecast |
| `--db NAME` | `japan_30d_shift{N}d.db` | DB SQLite training |
| `--seeds S` | `4:4` | Range semi Pulsar |
| `--max-iter N` | `150` | Iterazioni max LCS |
| `--skip-master` | *(off)* | Salta creazione master (usa esistente) |

**Comportamento `--events`:**
1. Se `--events PATH` passato → usa quel file
2. Se il file di riferimento storico esiste → lo copia
3. Altrimenti → download fresco da USGS

---

## Esempi rapidi

### Run standard shift+15d (prima esecuzione)

```bash
cd /mnt/git0/git/repository/DLvsWAVE
./commands/run_japan_30d_pipeline.sh \
  --events /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/earthquakes.RAW.csv \
  --shift-days 15 \
  --forecast-start 2026-04-01 \
  --forecast-end   2026-09-30
```

### Riusa master esistente (solo training + smart merge)

```bash
./commands/run_japan_30d_pipeline.sh \
  --shift-days 15 \
  --skip-master
```

### Run shift+7d per triangolazione

```bash
./commands/run_japan_30d_pipeline.sh \
  --events ./earthquakes.RAW.csv \
  --shift-days 7 \
  --db japan_30d_shift7d.db
```

### Run shift+21d per triangolazione

```bash
./commands/run_japan_30d_pipeline.sh \
  --events ./earthquakes.RAW.csv \
  --shift-days 21 \
  --db japan_30d_shift21d.db
```

### Run personalizzato: DB e cartella espliciti

```bash
./commands/run_japan_30d_pipeline.sh \
  --events ./earthquakes.RAW.csv \
  --out-dir /mnt/data/japan_shift14d \
  --shift-days 14 \
  --forecast-start 2026-06-01 \
  --forecast-end   2026-12-31 \
  --db japan_shift14d_v2.db \
  --seeds 4:8 \
  --max-iter 200
```

---

## Smart merge standalone

Usa `post_hybrid_pair_smart.py` direttamente su un run già completato:

```bash
cd /mnt/git0/git/repository/DLvsWAVE

# Run dir del training (contiene best_trials_index.json)
RUN_DIR=/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-30d-shift15d/pulsar_train_best_trials_YYYYMMDD-HHMMSS
OUT=/tmp/my_smart_merge

./.venv/bin/python post_hybrid_pair_smart.py \
  "$RUN_DIR" \
  --dataset-subfolder master_with_usgs_core_astrofmt \
  --out-dir "$OUT" \
  --score-column predicted \
  --peak-and \
  --peak-window 1 \
  --peak-floor  0.30 \
  --peak-max    1
```

**Argomenti chiave:**

| Flag | Descrizione |
|------|-------------|
| `--peak-and` | Abilita rilevamento picchi AND tra i due segnali |
| `--peak-window N` | Finestra temporale (bin) per l'overlap AND (default 1) |
| `--peak-floor F` | Soglia minima normalizzata per essere un picco (default 0.30) |
| `--peak-max N` | Numero massimo di picchi in output (default 1) |
| `--auto-best-logic` | Prova 5 combo logica/alpha, sceglie la migliore |
| `--cascade` | Se merge principale fallisce → best-effort doppio |

---

## Output: struttura e report

Dopo lo smart merge, la cartella `post_hybrid_checks_smart/` contiene:

```
post_hybrid_checks_smart/
├── smart_result/
│   ├── *__forecast.csv              ← predizioni forecast per bin
│   ├── *__validation_combined.csv   ← predizioni validation
│   ├── *__lineage_diagram.png       ← diagramma architettura fusione
│   ├── *__lineage_comparison.png    ← timeline validation + forecast
│   ├── *__summary.json              ← metriche e parametri completi
│   └── metrics_delta.txt            ← Δ metriche vs A e vs B
└── best_effort_summary.json         ← dettagli interni shape/peak winner
```

### Formato forecast CSV

```
date,row_index,actual,actual_event,a_raw,b_raw,a_score,b_score,predicted,error
2026-04-18,1418,0.0,0.0,0.06,0.0,0.16,0.0,0.0,0.0
2026-07-17,1421,0.0,0.0,0.11,1.0,0.20,1.0,1.0,1.0
```

`predicted=1.0` indica una finestra a rischio elevato nel periodo corrispondente.

### Report `dual_source`

Il lineage diagram mostra:
- **Candidate A** (blu): sorgente analogica originale (es. passthrough)
- **Candidate B** (arancio): sorgente digitale originale (es. hybrid/LCS)
- **Result box** (verde): metriche finali con Δ vs A e Δ vs B separati
- **Bar chart** (3 barre): Source A (grigio) · Source B (blu) · Smart merge (verde)

Le metriche di A e B sono **diverse** perché provengono dai modelli originali,
non da intermediari. Il gain è calcolato rispetto alle vere baseline.

---

## Peak-AND

### Principio

Invece di usare una soglia fissa, ogni segnale è **auto-normalizzato** nel suo
range `[0,1]` prima del rilevamento picchi. Questo rende la selezione
indipendente dalla scala (passthrough 0.06-0.11 = hybrid 0/1).

### Cascata finestre

```
window=0: cerca overlap esatto tra i due segnali
window=1: espande di ±1 bin
...
window=N: espande di ±N bin
→ primo overlap trovato → usa quella finestra
→ nessun overlap AND → fallback peak-OR (richiede picchi in entrambi)
→ nessun picco in uno dei due → fallback OR threshold puro
```

### Ranking quando max_peaks > 1

Se esistono più overlap AND, vengono classificati per forza del segnale
(max del valore auto-normalizzato tra i due candidati nel punto di overlap).
Vengono tenuti i primi `peak_max` picchi.

---

## Triangolazione shift

Per localizzare temporalmente un evento atteso (es. "big one di agosto 2026"),
eseguire run con shift diversi e confrontare dove appare il picco forecast:

```bash
# Shift +7d  → TIME_BEFORE=173d → bin centrati intorno al 7° del mese
./commands/run_japan_30d_pipeline.sh --events ./eq.csv --shift-days  7

# Shift +14d → TIME_BEFORE=166d → bin centrati intorno al 14°
./commands/run_japan_30d_pipeline.sh --events ./eq.csv --shift-days 14

# Shift +15d → TIME_BEFORE=165d → bin centrati intorno al 15°
./commands/run_japan_30d_pipeline.sh --events ./eq.csv --shift-days 15

# Shift +21d → TIME_BEFORE=159d → bin centrati intorno al 21°
./commands/run_japan_30d_pipeline.sh --events ./eq.csv --shift-days 21
```

Confrontare i file `smart_result/*forecast.csv` di ogni run:
se il picco `predicted=1.0` appare in agosto in **almeno 2-3 run** su 4
con shift diversi, il segnale è robusto rispetto alla scelta del bin.

---

## File correlati

| File | Descrizione |
|------|-------------|
| `commands/run_japan_30d_pipeline.sh` | Script pipeline unificato |
| `commands/train_japan_30d_shift15d_fast.sh` | Solo training (shift+15d) |
| `post_hybrid_pair_smart.py` | Smart merge: selezione + fusione coppia |
| `post_hybrid_artifacts.py` | Rendering diagrammi lineage |
| `docs/pulsar_cli_recipes.md` | Ricette CLI generiche Pulsar |
| `POST_HYBRID_ARTIFACTS.md` | Documentazione merge base |

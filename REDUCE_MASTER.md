# reduce_master.py — riduzione master CSV per training

Script che riduce un master CSV settimanale (date + target sismici + colonne
efemeridi) tenendo **solo l'essenziale** per addestrare reti / sistemi esperti:

- gli **eventi-picco** (mag sopra una soglia)
- una **finestra di contesto** attorno a ogni picco
- un **campionamento intelligente** dei record-valle nei gap tra picchi
  (proporzionale alla lunghezza del gap, con jitter sul conteggio E sulle
  posizioni → niente pattern regolare imparabile)
- **tutta la coda futura** (definita per data o per "dopo l'ultimo picco")
- opzionale: **normalizzazione** in `[0,1]` e/o **binning a quantili**
  (con output `0/0.25/0.5/0.75/1` per `qbins=5`, ad esempio)

Lo script vive in `DLvsWAVE/reduce_master.py` ed è invocabile direttamente con
`python3` (richiede solo `pandas` + `numpy`).

---

## Flag

| Flag | Default | Significato |
|---|---|---|
| `master` (posizionale) | — | Path del master CSV da ridurre |
| `--out PATH` | — | Output esplicito. Indipendentemente, lo script scrive **sempre** anche `<input>_reduced.csv` accanto all'originale |
| `--peak-col NAME` | `mag` | Colonna usata per detectare i picchi |
| `--peak-threshold FLOAT` | `0.1` | Una riga è picco se `peak-col >= threshold` |
| `--window N` | `6` | Mantiene `±N` record attorno a ogni picco |
| `--valley-density FRAC` | `0.05` | Frazione del gap da campionare come valle (5% = 0.05) |
| `--valley-jitter FRAC` | `0.3` | Rumore random sul conteggio per gap (`±30%`) |
| `--valley-positions {jittered,random,even}` | `jittered` | Come distribuire i record scelti |
| `--per-gap-min N` | `1` | Floor minimo per gap non vuoto |
| `--per-gap-max N` | nessuno | Ceiling opzionale per gap (safety net) |
| `--global-valley-cap N` | nessuno | Tetto totale di valli tra primo e ultimo picco (shrink proporzionale se superato) |
| `--seed INT` | auto | Seed RNG. Se omesso usa `time` e lo stampa: ri-passalo per riprodurre |
| `--future-mode {tail,cutoff,both}` | **richiesto** | Come preservare la "parte futuro" |
| `--future-tail-keep` | `all` | Se `tail/both`: `all`, `none`, o un intero N |
| `--future-from YYYY-MM-DD` | — | Se `cutoff/both`: tutto da quella data in poi è preservato 1:1 |
| `--normalize` | off | Normalizza min-max in `[0,1]` le colonne numeriche |
| `--normalize-exclude col1,col2,...` | `""` | Aggiunge colonne all'exclude list di default |
| `--qbins N` | `0` (off) | Quantile-binning con N bin (≥2). Sostituisce i valori |
| `--qbins-output {norm,idx}` | `norm` | `norm` → bin position in `[0,1]` (es. `qbins=5` → `0/0.25/0.5/0.75/1`); `idx` → indice intero `0..N-1` |

### Colonne escluse di default da normalize / qbins
`date, mag, depth, latitude, longitude` — le 4 sismiche più la data restano
sempre intatte. `--normalize-exclude` **aggiunge** ad esse, non sostituisce.

### Modalità di futuro
- **`tail`**: il "futuro" sono i record dopo l'ultimo picco. Quanti tenerne:
  `--future-tail-keep all|none|N`.
- **`cutoff`**: il "futuro" è tutto da `--future-from YYYY-MM-DD` in poi.
- **`both`**: applica entrambi (utile se vuoi cutoff per data MA anche garantire
  che la coda dopo l'ultimo picco storico sia preservata).

### Normalize + qbins insieme
Non sono mutuamente esclusivi. Se passi entrambi, `--normalize` viene applicato
prima e `--qbins` opera sui valori già normalizzati. (Matematicamente i quantili
sono invarianti per trasformazioni monotone, quindi il risultato finale è
equivalente al solo qbins; ma l'ordine è esplicito per chiarezza.)

---

## Esempio: pipeline completa Japan 7D

Pipeline end-to-end dalla generazione del master alla riduzione al training,
**saltando il forecast vecchio** (lo step `4-forecast.sh` della cartella).

```bash
# Cartella di lavoro del dataset
DATA=/mnt/git0/git/repository/astro-USGS2/DB/japan-mag80-1900plus-7d-focus-noise

# 1) Genera il master fmt (USGS + NASA context + build) — NO forecast vecchio
"$DATA/1-usgs_download.sh"
"$DATA/2-nasa_download_context.sh"
"$DATA/3-build_master_with_usgs_core.sh"
# → produce: $DATA/master_with_usgs_core_astrofmt.csv

# 2) Riduzione del master
"$DATA/reduce.sh"
# → produce: $DATA/master_with_usgs_core_astrofmt_reduced.csv
# (peaks + ±6 contesto + valli proporzionali jittered + futuro dal 2025-04-01,
#  qbins=5 → tutte le efemeridi mappate in {0, 0.25, 0.5, 0.75, 1.0})

# 3) Train-max sul master ridotto (DB e log separati dal run "full")
bash /mnt/git0/git/repository/DLvsWAVE/commands/train-max_japan-7d_reduced.sh
# → DB:  japan_trainmax_7d_mag80_reduced.db
# → log: /tmp/dlvswave_run_japan_7d_reduced.log
```

### Contenuto di `reduce.sh` (nella cartella del master)
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MASTER="$SCRIPT_DIR/master_with_usgs_core_astrofmt.csv"
REDUCER="/mnt/git0/git/repository/DLvsWAVE/reduce_master.py"

python3 "$REDUCER" "$MASTER" \
  --peak-threshold 0.1 \
  --window 6 \
  --valley-density 0.05 \
  --valley-jitter 0.3 \
  --valley-positions jittered \
  --per-gap-min 1 \
  --qbins 5 \
  --future-mode cutoff \
  --future-from 2025-04-01
```

### Differenze tra `train-max_japan-7d.sh` (full) e `_reduced.sh`
Lo script `_reduced` è identico al full tranne:
- `--task` punta al `*_reduced.csv`
- `--db japan_trainmax_7d_mag80_reduced.db` (DB separato → confronti puliti)
- log su `/tmp/dlvswave_run_japan_7d_reduced.log`

Tutti gli altri flag (target, hybrid, LCS, finestre di backtest…) restano
invariati.

---

## Output stampato (esempio reale)

```
======================================================================
REDUCE MASTER — chosen configuration
======================================================================
  input               : .../master_with_usgs_core_astrofmt.csv
  peak detection      : 'mag' >= 0.1
  context window      : ±6 records around each peak
  valley density      : 0.050  (5.0% of each gap)
  valley jitter       : ±30% on the per-gap count
  valley positions    : jittered
  per-gap min / max   : 1 / no cap
  RNG seed            : 3904539163  (auto from time — pass --seed 3904539163 to reproduce)
  future-mode         : cutoff
    future-from       : 2025-04-01  (rows from this date kept 1:1)
  quantile bins       : 5  (output=norm)
======================================================================

======================================================================
RESULTS
======================================================================
  original rows           : 5062
  peaks (mag>=0.1)        : 9
  context kept (±6)       : 117
  gaps between peaks      : 8
  gap lengths (free recs) : min=52  max=1299  mean=439.0  median=317
  valley count per gap    : min=4   max=80    mean=22.8   median=13
  valleys sampled (tot)   : 182
  future cutoff kept      : 91
  final rows              : 390
  reduction               : 92.3% smaller (390/5062 = 7.7% kept)
  transformed columns     : 331 numeric cols
    quantile-binned       : 331 cols into 5 bins, output=norm
======================================================================
```

Il blocco "valley count per gap" mostra che i conteggi **non** sono costanti
(min=4, max=80) — proprio perché proporzionali alla lunghezza del gap +
jitter, evitando pattern artificiali "1 evento, N record fissi, 1 evento…"
che la rete potrebbe imparare.

---

## Ricette rapide

**Più carne attorno ai picchi**
```bash
--window 12 --valley-density 0.10
```

**Output a 4 quartili veri (`{0, 0.333, 0.666, 1.0}`)**
```bash
--qbins 4
```

**Solo normalizzazione, niente binning**
```bash
--normalize
```

**Riproducibile bit a bit**
```bash
--seed 42
```

**Tetto duro: max 50 valli per gap, max 1000 totali**
```bash
--per-gap-max 50 --global-valley-cap 1000
```

**Preserva tutto dal 2025-04-01 in poi E i record dopo l'ultimo picco storico**
```bash
--future-mode both --future-from 2025-04-01 --future-tail-keep all
```

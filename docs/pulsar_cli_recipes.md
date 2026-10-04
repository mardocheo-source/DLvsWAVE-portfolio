# Pulsar CLI recipes

Comandi pronti da copiare. Cambia solo:

- `DATASET`
- `TARGET`
- `SKIP_COLS`
- `DB_NAME`
- eventualmente soglie, date e preset.

Nei comandi sotto, il forecast da aprile usa `2026-03-05` per includere la prima
riga reale disponibile `2026-04-03` nel dataset Japan attuale.

## Placeholder comuni

```bash
DATASET=/path/to/master_with_usgs_core_astrofmt.csv
TARGET=mag
SKIP_COLS=date,depth,latitude,longitude
DB_NAME=my_run.db
```

## 1. Reference run completo Japan/eventi rari

Uso consigliato per run notturno ragionevole, con:

- backtest event-window;
- recent validation;
- ranking recency-aware;
- training sample weighting recency/event;
- DeepNet event-composite;
- LCS custom interpretabile;
- forecast da aprile 2026.

```bash
./.venv/bin/python cli.py train \
  --task /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/master_with_usgs_core_astrofmt.csv \
  --target_cols_list mag \
  --skip_cols_list date,depth,latitude,longitude \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 4 \
  --backtest-max-windows 5 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  --recent-validation-window \
  --recent-validation-weight 2.5 \
  --train-recency-weight exp \
  --train-recency-strength 1.0 \
  --train-event-weight auto \
  --train-max-event-weight 8.0 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough,random_projection,morlet_wavelet \
  --readouts ridge \
  --deep-presets tiny \
  --deep-val-event-count 2 \
  --deep-val-pre-records 5 \
  --deep-val-post-records 3 \
  --deep-validation-metric event_composite \
  --deep-validation-threshold 0.1 \
  --lcs-custom \
  --lcs-population-size 800 \
  --lcs-epochs 140 \
  --lcs-ga-frequency 150 \
  --lcs-wildcard-prob 0.94 \
  --lcs-positive-wildcard-prob 0.99 \
  --lcs-positive-covering-multiplier 8 \
  --lcs-mutation-rate 0.012 \
  --lcs-crossover-rate 0.8 \
  --lcs-tournament-size 9 \
  --lcs-binary-threshold 0.1 \
  --lcs-val-event-count 2 \
  --lcs-val-pre-records 5 \
  --lcs-val-post-records 3 \
  --lcs-early-stop-patience 25 \
  --lcs-fitness-mode event \
  --lcs-selection-metric event_composite \
  --lcs-positive-weight auto \
  --lcs-positive-replay auto \
  --lcs-positive-vote-weight auto \
  --hybrid-lcs \
  --hybrid-partners passthrough:ridge,random_projection:ridge,deep:tiny \
  --hybrid-modes and,weighted \
  --hybrid-alphas 0.5,0.75 \
  --hybrid-threshold 0.5 \
  --seeds 2 \
  --db japan_mag_lcs_v26_recency_training_forecast_from_20260403.db \
  --verbose
```

## 2. Stesso run, ma senza pesi nel training

Serve per capire se il weighting recency/event sta aiutando davvero.

```bash
./.venv/bin/python cli.py train \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-step-events 1 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 4 \
  --backtest-max-windows 5 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.0 \
  --recent-validation-window \
  --recent-validation-weight 2.5 \
  --no-train-sample-weighting \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough,random_projection,morlet_wavelet \
  --readouts ridge \
  --deep-presets tiny \
  --deep-validation-metric event_composite \
  --deep-validation-threshold 0.1 \
  --lcs-custom \
  --lcs-population-size 800 \
  --lcs-epochs 140 \
  --lcs-ga-frequency 150 \
  --lcs-wildcard-prob 0.94 \
  --lcs-positive-wildcard-prob 0.99 \
  --lcs-positive-covering-multiplier 8 \
  --lcs-binary-threshold 0.1 \
  --lcs-selection-metric event_composite \
  --seeds 2 \
  --db DB_NAME \
  --verbose
```

## 3. Rapido smoke test sintetico LCS

Serve dopo modifiche al codice. Atteso: LCS deve imparare bene `step_fn`.

```bash
./.venv/bin/python cli.py train \
  --task step_fn \
  --n-train 500 \
  --n-test 200 \
  --seeds 3 \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --banks passthrough \
  --readouts ridge \
  --lcs-presets default \
  --db smoke_step_fn_lcs.db
```

## 4. Run rapido CSV solo baseline

Serve per controllare dataset, finestre e forecast senza aspettare LCS/DeepNet.

```bash
./.venv/bin/python cli.py train \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough,random_projection,morlet_wavelet \
  --readouts ridge \
  --seeds 2 \
  --db DB_NAME \
  --verbose
```

## 5. Run LCS-only interpretabile

Serve quando vuoi concentrarti sulle regole e su `best_rules.json`.

```bash
./.venv/bin/python cli.py train \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-max-windows 5 \
  --backtest-recency-weight exp \
  --recent-validation-window \
  --recent-validation-weight 2.5 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough \
  --readouts ridge \
  --lcs-custom \
  --lcs-population-size 800 \
  --lcs-epochs 140 \
  --lcs-ga-frequency 150 \
  --lcs-wildcard-prob 0.94 \
  --lcs-positive-wildcard-prob 0.99 \
  --lcs-positive-covering-multiplier 8 \
  --lcs-mutation-rate 0.012 \
  --lcs-crossover-rate 0.8 \
  --lcs-tournament-size 9 \
  --lcs-binary-threshold 0.1 \
  --lcs-val-event-count 2 \
  --lcs-val-pre-records 5 \
  --lcs-val-post-records 3 \
  --lcs-selection-metric event_composite \
  --lcs-positive-weight auto \
  --lcs-positive-replay auto \
  --lcs-positive-vote-weight auto \
  --seeds 3 \
  --db DB_NAME \
  --verbose
```

Nota: `--banks passthrough --readouts ridge` resta nel comando per avere almeno
un baseline veloce accanto a LCS.

## 6. Run piu' robusto ma piu' lento

Da usare di notte quando vuoi piu' stabilita' sulle seed e una LCS piu' ampia.

```bash
./.venv/bin/python cli.py train \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-min-train-events 4 \
  --backtest-max-windows 8 \
  --backtest-recency-weight exp \
  --backtest-recency-strength 1.25 \
  --recent-validation-window \
  --recent-validation-weight 3.0 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough,random_projection,morlet_wavelet \
  --readouts ridge \
  --deep-presets tiny,small \
  --deep-validation-metric event_composite \
  --deep-validation-threshold 0.1 \
  --lcs-custom \
  --lcs-population-size 1200 \
  --lcs-epochs 180 \
  --lcs-ga-frequency 150 \
  --lcs-wildcard-prob 0.95 \
  --lcs-positive-wildcard-prob 0.99 \
  --lcs-positive-covering-multiplier 10 \
  --lcs-mutation-rate 0.012 \
  --lcs-crossover-rate 0.8 \
  --lcs-tournament-size 9 \
  --lcs-binary-threshold 0.1 \
  --lcs-val-event-count 2 \
  --lcs-val-pre-records 5 \
  --lcs-val-post-records 3 \
  --lcs-selection-metric event_composite \
  --seeds 4 \
  --db DB_NAME \
  --verbose
```

## 7. Hybrid LCS + modelli scettici

Serve quando LCS becca gli eventi ma produce troppi positivi. `and` aumenta lo
scetticismo, `weighted` cerca una via intermedia.

```bash
./.venv/bin/python cli.py train \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --backtest-event-windows \
  --backtest-event-count 2 \
  --backtest-pre-records 5 \
  --backtest-post-records 3 \
  --backtest-max-windows 5 \
  --backtest-recency-weight exp \
  --recent-validation-window \
  --recent-validation-weight 2.5 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --banks passthrough,random_projection,morlet_wavelet \
  --readouts ridge \
  --deep-presets tiny \
  --deep-validation-metric event_composite \
  --deep-validation-threshold 0.1 \
  --lcs-custom \
  --lcs-population-size 800 \
  --lcs-epochs 140 \
  --lcs-ga-frequency 150 \
  --lcs-wildcard-prob 0.94 \
  --lcs-positive-wildcard-prob 0.99 \
  --lcs-positive-covering-multiplier 8 \
  --lcs-binary-threshold 0.1 \
  --lcs-selection-metric event_composite \
  --hybrid-lcs \
  --hybrid-partners passthrough:ridge,random_projection:ridge,deep:tiny \
  --hybrid-modes and,weighted \
  --hybrid-alphas 0.5,0.75 \
  --hybrid-threshold 0.5 \
  --seeds 2 \
  --db DB_NAME \
  --verbose
```

## 8. train-max con LCS abilitato

Per sweep piu' ampio. LCS entra in `train-max` solo con
`--enable-lcs-in-max`.

```bash
./.venv/bin/python cli.py train-max \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --metric-mode auto \
  --metric-target-threshold 0.1 \
  --target-window-threshold 0.1 \
  --target-window-event-count 2 \
  --target-window-pre-records 5 \
  --target-window-post-records 3 \
  --forecast-start-date 2026-03-05 \
  --forecast-end-date 2026-12-30 \
  --forecast-trainset train2forecast \
  --enable-lcs-in-max \
  --max-iter 500 \
  --seeds 2 \
  --db DB_NAME \
  --verbose
```

## 9. Refinement mirato da un run precedente

`--inherit` prende il `best_trials_index.csv` di un run precedente, eredita i
parametri salvati e rilancia solo le migliori combinazioni. Di default non
aggiunge il best di ogni bank: usa solo i top-N esatti, cosi' resta piu' libero
e mirato.

```bash
./.venv/bin/python cli.py train \
  --inherit /path/to/pulsar_train-max_best_trials_YYYYMMDD-HHMMSS \
  --best 8 \
  --seeds 4:4 \
  --db DB_NAME \
  --verbose
```

Interpretazione seed utile:

- `--seeds 4` = quattro seed, `[0,1,2,3]`;
- `--seeds 4:4` = quattro seed da base 4, `[4,5,6,7]`;
- `--seeds 1,7,19` = lista esatta.

Per includere anche il migliore di ogni bank oltre ai top-N:

```bash
--inherit-best-bank
```

## 10. Final evaluation overall

Nei run CSV la final evaluation e' attiva di default e produce, accanto ai PNG
dei singoli trial, CSV/PNG overall separati per validation e forecast:

```text
TASK__final_evaluation.json
TASK__final_evaluation__validation.csv
TASK__final_evaluation__validation.png
TASK__final_evaluation__forecast.csv
TASK__final_evaluation__forecast.png
```

Il consenso pesa ogni trial in base al ranking finale e al peso della finestra
validation/backtest. I trial con stima totale quasi nulla entrano, di default,
in reverse mode con peso piu' alto per sfruttare l'inerzia negativa.

Flag principali:

```bash
--final-eval-rank-power 1.0 \
--final-eval-low-threshold 1e-9 \
--final-eval-negative-weight 3.0
```

Per disattivare solo il reverse mode:

```bash
--no-final-eval-negative-inertia
```

Per disattivare tutta la final evaluation:

```bash
--no-final-evaluation
```

## 11. Controllare leaderboard dal DB

```bash
./.venv/bin/python cli.py top \
  --db DB_NAME \
  --limit 20
```

## 12. CLI presets (modo rapido)

Per evitare lunghe catene di flag, usa `--preset NAME` (componibile con
virgola: `--preset N1,N2`). Lista:

```bash
./.venv/bin/python cli.py train --list-presets
```

Preset disponibili (vedi `cli.py` `PRESETS` per il dettaglio):

- `japan-event-base` — fondamenta Japan event-based: target window 1 evento,
  backtest 1 finestra, recent validation, ranking + training recency-aware.
  Niente forecast/hybrid/LCS/seeds. Usalo come base o estendilo.
- `japan-event` — base + forecast 2026 + hybrid LCS esteso (passthrough +
  random_projection + deep tiny + deep small) + final-eval default + 4 seed da
  base 4 + max-iter 300.
- `japan-event-l1` — `japan-event` + `--auto-inherit-levels 1`. Modalita'
  consigliata per il run di riferimento.
- `japan-event-l3` — `japan-event` + `--auto-inherit-levels 3`. Refinement
  aggressivo a 3 livelli.
- `japan-event-fast` — solo baselines + LCS default, no hybrid, 2 seed,
  max-iter 100. Per smoke test di finestre/forecast.
- `shape-strict` — shape filter aggressivo (best=0.15, worst=0.05, power=2.0).
  Componibile con qualunque preset.
- `shape-off` — disattiva shape filter (ritorno al comportamento legacy
  negative-inertia). Componibile.
- `hybrid-deep-extended` — sostituisce/forza i partner hybrid a tiny + small +
  default + wide (nessun bank classico). Componibile.

### Esempi d'uso

Reference run (modalita' tipica):

```bash
./.venv/bin/python cli.py train-max \
  --preset japan-event-l1 \
  --task DATASET \
  --target_cols_list TARGET \
  --skip_cols_list SKIP_COLS \
  --db DB_NAME \
  --verbose
```

Reference run con shape filter aggressivo (per academia, plot piu' nitidi):

```bash
./.venv/bin/python cli.py train-max \
  --preset japan-event-l1,shape-strict \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db DB_NAME
```

Override esplicito sopra il preset (l'utente vince sempre):

```bash
./.venv/bin/python cli.py train-max \
  --preset japan-event-l1 \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --seeds 8:8 --max-iter 500 \
  --db DB_NAME
```

Smoke test rapido sul dataset corrente:

```bash
./.venv/bin/python cli.py train \
  --preset japan-event-fast \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db smoke_test.db
```

Confronto vecchio vs nuovo final-eval (stesso run, due DB):

```bash
./.venv/bin/python cli.py train-max --preset japan-event-l1 \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db japan_with_shape_filter.db
./.venv/bin/python cli.py train-max --preset japan-event-l1,shape-off \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db japan_legacy_negative_inertia.db
```

Refinement aggressivo a 3 livelli (notturno):

```bash
./.venv/bin/python cli.py train-max --preset japan-event-l3 \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db japan_l3.db
```

Hybrid esteso con tutti i preset DeepNet (no banks classici come partner):

```bash
./.venv/bin/python cli.py train-max --preset japan-event-l1,hybrid-deep-extended \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  --db japan_hybrid_full.db
```

## 13. Auto-inheritance multilivello (manuale)

Senza preset, attivi N passate di inheritance dopo il run principale con:

```bash
./.venv/bin/python cli.py train-max \
  --task DATASET --target_cols_list TARGET --skip_cols_list SKIP_COLS \
  ... [tutti gli altri flag] ... \
  --auto-inherit-levels 1 \
  --best 5 \
  --db DB_NAME
```

Ogni livello prende il `best_trials_index.csv` del precedente, ne legge i top
`--best` per score, e per default include sempre il miglior LCS e LCS-hybrid
(`--always-include lcs,lcs_hybrid`). Per estendere o disattivare:

```bash
--always-include lcs,lcs_hybrid,mag,wave   # forza anche bank classici
--no-always-include                         # solo top-N puri
```

I file di output di ogni livello sono in directory artifact separate
(`pulsar_train_best_trials_<timestamp>`), il database e' lo stesso (se passi
lo stesso `--db`). Per confrontare livelli, cambia `--db` o consulta gli
`artifact_index_paths` stampati alla fine di ciascun livello.

## 14. Shape filter sul final evaluation

Default attivo. Penalizza forecast con poca variazione predetta e ammette il
ribaltamento dei trial "peggiori sui picchi" (potenzialmente invertibili).

Knob:

```bash
--final-eval-best-fraction 0.25     # top X% per shape_overall -> include
--final-eval-worst-fraction 0.10    # bottom Y% (con picchi) -> invert
--final-eval-shape-power 0.0        # 0=uniforme; 1.5..2 = enfasi sui top dello shape
--no-final-eval-shape-filter        # ritorno al comportamento legacy
```

Quando attivo, sostituisce la logica `negative_inertia` (basata su
`total_estimation`) con un classificatore basato su `shape_overall` e
`detect_topological_peaks`. Il sottotitolo del PNG riporta:

```
shape_filter=on best=0.25 worst=0.10 shape_power=1.5
included=12 inverted=4 excluded=24
```

Il JSON di firma riporta `shape_filter.excluded_reasons` con
`no_predicted_peaks`, `mediocre`, `no_validation`.

## Note pratiche

- Se vuoi partire dalla prima riga reale dopo aprile 1 nel dataset Japan attuale,
  usa `--forecast-start-date 2026-03-05`; il forecast risolve a `2026-04-03`.
- Se vedi grafici best-by-bank molto vecchi, guarda anche
  `best_by_bank/recent_validation/`.
- Se LCS predice troppi `1`, prova ad abbassare `--recent-validation-weight` o
  disattivare il training event weighting per confronto.
- Se vuoi confronto storico puro senza preferenza recente, usa:

```bash
--backtest-recency-weight none \
--no-train-sample-weighting
```

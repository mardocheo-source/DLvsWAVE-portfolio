# Examples

Script pronti da eseguire per la pipeline Japan 30d forecast.

## Script disponibili

| Script | Descrizione | Durata |
|--------|-------------|--------|
| `japan_shift15d_full.sh` | Pipeline completa shift+15d (master + training + smart merge) | ~7h |
| `japan_shift7d_full.sh`  | Pipeline completa shift+7d (triangolazione) | ~7h |
| `japan_shift21d_full.sh` | Pipeline completa shift+21d (triangolazione) | ~7h |
| `smart_merge_retro.sh`   | Solo smart merge su training già completato | ~1 min |

## Uso rapido

```bash
cd /mnt/git0/git/repository/DLvsWAVE

# Pipeline completa shift+15d (default)
./examples/japan_shift15d_full.sh

# Solo smart merge su run esistente
RUN_DIR=/path/to/pulsar_train_best_trials_YYYYMMDD-HHMMSS \
  ./examples/smart_merge_retro.sh
```

## Triangolazione shift

Per localizzare temporalmente un evento previsto, esegui 3-4 run con shift diversi
e confronta dove appare `predicted=1` nel `smart_result/*forecast.csv`:

```bash
./examples/japan_shift7d_full.sh   # TIME_BEFORE=173d
./examples/japan_shift15d_full.sh  # TIME_BEFORE=165d
./examples/japan_shift21d_full.sh  # TIME_BEFORE=159d
```

Se il picco appare in agosto in ≥2 run su 3, il segnale è robusto.

## Documentazione completa

→ `docs/smart_merge_pipeline.md`

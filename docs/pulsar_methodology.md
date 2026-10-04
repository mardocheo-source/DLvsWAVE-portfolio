# Pulsar: logica benchmark, LCS, backtest e forecast

Questo documento descrive la logica usata nel benchmark Pulsar dopo
l'introduzione di LCS/UCS, finestre evento, ranking recency-aware e pesi di
training. L'obiettivo e' confrontare famiglie di modelli diverse in modo piu'
equo quando il target e' raro/sparso, per esempio eventi con `mag >= 0.1`.

## Flusso generale

Pulsar prende un dataset CSV, sceglie un target e costruisce feature numeriche.
Le colonne escluse con `--skip_cols_list` non entrano nel modello.

Il benchmark puo' usare:

- una finestra test finale ricavata dagli eventi;
- piu' finestre backtest storiche;
- una recent validation window vicina al forecast;
- una forecast window finale, dove il modello viene rifittato e poi predice le
  righe future richieste.

Il ranking finale e' calcolato sulle metriche test/validation disponibili, non
sulle metriche forecast. Il forecast e' un output operativo: mostra cosa il
modello scelto vede nel periodo richiesto.

## Target event-based

Con target sparsi/zero-inflated, `--metric-mode auto` tende a scegliere metriche
event-based. La soglia evento e' controllata da:

```bash
--metric-target-threshold 0.1
--target-window-threshold 0.1
```

Per LCS il target continuo viene binarizzato con:

```bash
--lcs-binary-threshold 0.1
```

Quindi, per LCS, le predizioni sono solo `0` o `1`. Questo e' voluto: e' un
classificatore binario di eventi.

## Famiglie di modelli

### Feature bank + readout

Esempi:

- `passthrough + ridge`
- `random_projection + ridge`
- `morlet_wavelet + ridge`

La feature bank trasforma le feature originali. Il readout finale impara la
mappa verso il target. Per `ridge` e `linear`, i pesi di training recency/event
sono passati come `sample_weight`.

Questa famiglia e' veloce, stabile e spesso un buon baseline.

### DeepNet end-to-end

Esempio:

- `(end-to-end) deepnet_tiny`

DeepNet usa direttamente le feature originali. Internamente scala le feature e
scala anche il target durante il training. Quando si usa una metrica di
validazione event-based, la soglia raw viene convertita nella scala interna, in
modo che `0.1` resti semanticamente `0.1` anche se il target e' scalato.

Con:

```bash
--deep-validation-metric event_composite
--deep-validation-threshold 0.1
```

DeepNet sceglie il best state con una metrica anti-degenerazione:

```text
score = F1 * balanced_accuracy
```

La loss rimane tracciata nella history, ma l'early stopping puo' usare la metrica
event-based.

### LCS / UCS

Esempio:

- `(lcs) ucs_custom`

LCS usa regole a intervalli sulle feature continue. Ogni regola ha:

- condizioni sui campi numerici;
- azione `0` o `1`;
- fitness;
- esperienza;
- numerosity;
- metriche interne TP/TN/FP/FN.

Il voto finale e' pesato da fitness, numerosity e, se attivo, da
`positive_vote_weight`. Le regole migliori vengono esportate in `best_rules.json`.

LCS ha una validation interna per scegliere il best snapshot e poi, di default,
fa final retrain su tutto il train fino al best epoch:

```bash
--lcs-val-event-count 2
--lcs-val-pre-records 5
--lcs-val-post-records 3
--lcs-early-stop-patience 25
```

La metrica default LCS per selection/fitness event-based e':

```text
event_composite = F1 * balanced_accuracy
```

La vecchia formula additiva resta disponibile con:

```bash
--lcs-selection-metric event_composite_additive
```

### Hybrid LCS + partner

Gli ibridi sono una quarta famiglia di concorrenti. LCS resta comunque in
leaderboard come modello puro.

Un trial hybrid allena, sulla stessa finestra train:

1. un LCS;
2. un partner, per esempio `passthrough:ridge`, `random_projection:ridge` o
   `deep:tiny`;
3. una combinazione finale senza usare la finestra test per scegliere.

Modalita disponibili:

- `and`: evento solo se LCS e partner sono positivi;
- `or`: evento se LCS o partner sono positivi;
- `weighted`: `alpha * LCS + (1 - alpha) * partner_score`, poi threshold.

Esempio:

```bash
--hybrid-lcs
--hybrid-partners passthrough:ridge,random_projection:ridge,deep:tiny
--hybrid-modes and,weighted
--hybrid-alphas 0.5,0.75
--hybrid-threshold 0.5
```

Questo serve quando LCS ha alta recall ma troppi falsi positivi: il partner puo'
fare da filtro o fine tuning. Anche gli ibridi rispettano la policy anti-leak:
vengono allenati solo sul train della finestra corrente e rifittati prima del
forecast con il trainset scelto.

## Metrica event_composite

La metrica attuale per evitare soluzioni degeneri e':

```text
score = F1 * balanced_accuracy
```

Questo penalizza:

- predire sempre `0`, perche' F1 va a zero;
- predire sempre `1`, perche' precision e balanced accuracy restano deboli;
- modelli che prendono solo recall ma generano troppi falsi positivi.

La formula non ha pesi da tunare.

## Backtest event-window

Con:

```bash
--backtest-event-windows
--backtest-event-count 2
--backtest-pre-records 5
--backtest-post-records 3
```

Pulsar costruisce piu' finestre storiche basate su eventi. Ogni finestra:

1. allena il modello solo sul passato prima della finestra;
2. testa sul blocco evento;
3. salva metriche comparabili fra modelli.

Le finestre possono sovrapporsi: `--backtest-step-events 1` con
`--backtest-event-count 2` produce finestre adiacenti di due eventi, quindi
la seconda finestra puo' riusare come primo evento l'evento finale della
precedente. Se hai pochi eventi storici e vuoi evitare di scendere troppo nel
passato, riduci `--backtest-min-train-events` oppure imposta
`--backtest-include-final-window` quando vuoi includere anche la finestra
target finale nel backtest.

Questo e' importante per evitare leakage temporale.

## Ranking recency-aware

Se il fenomeno cambia nel tempo, non tutte le finestre storiche devono pesare
uguale. Con:

```bash
--backtest-recency-weight exp
--backtest-recency-strength 1.0
```

le finestre piu' recenti pesano di piu' nel ranking aggregato.

Modalita disponibili:

- `none`: tutte le finestre pesano uguale;
- `linear`: peso `1 + strength * progress`;
- `exp`: peso `exp(strength * progress)`.

La recent validation window puo' pesare ancora di piu':

```bash
--recent-validation-window
--recent-validation-weight 2.5
```

Questa finestra e' costruita prima del forecast, con lo stesso numero eventi e
gli stessi pre/post records. Serve sia per il ranking sia per avere un grafico
recente leggibile dall'utente.

## Final evaluation overall

Nei run CSV `train`, `train-max` e `--inherit`, Pulsar esporta di default anche
una sintesi overall del comportamento dei trial:

- `TASK__final_evaluation.json`
- `TASK__final_evaluation__validation.csv/png`
- `TASK__final_evaluation__forecast.csv/png`

Validation e forecast sono esportati in grafici separati, per evitare che righe
storiche e righe forecast finiscano sullo stesso asse temporale. La curva e'
costruita come ensemble pesato dei trial disponibili. Ogni contributo usa:

```text
final_weight = rank_weight * window_weight
```

`rank_weight` deriva dal ranking aggregato finale: il rank 1 pesa piu' del rank
2, il rank 2 piu' del rank 3, e cosi' via. La forma e' controllata da:

```bash
--final-eval-rank-power 1.0
```

`window_weight` e' il peso gia' usato dal ranking per backtest/recent validation,
quindi le finestre recenti e la recent validation continuano a contare di piu'
anche nella final evaluation. Le righe forecast dei best trial vengono esportate
nel file forecast dedicato quando il forecast e' disponibile.

Per target event-based, la final evaluation normalizza le predizioni continue in
segnale evento usando `--metric-prediction-threshold`; la curva blu e' l'evento
reale binario, la curva rossa e' il consenso pesato dei trial.

### Shape filter (default attivo)

Il filtro di forma classifica ogni trial in base al comportamento dei picchi
sulla validation, e include nella final evaluation solo quelli che aggiungono
segnale leggibile. La motivazione operativa e' accademica: un forecast finale
"frastagliato" con poca variazione reale, anche se piazzato in alto da metriche
di regressione, non e' fidabile per un ricercatore. Meglio plot puliti e
nitidi, costruiti da pochi trial coerenti.

Logica per ogni trial:

1. Si contano i picchi topologici nella predizione di validation
   (`detect_topological_peaks`). Se sono zero -> il trial e' escluso (variazione
   assente o segnale degenerato).
2. I trial con almeno un picco vengono ordinati per `shape_overall` (media tra
   `peak_score` e `depression_score`) decrescente:
   - top `--final-eval-best-fraction` (default 0.25) -> **include**: peso pieno
     `rank_weight * window_weight`. I picchi/depressioni della predizione
     coincidono con quelli reali, anche solo near-peak.
   - bottom `--final-eval-worst-fraction` (default 0.10) -> **invert**: i picchi
     sono lontani dal reale, ma se invertiti combaciano. Il segnale viene
     ribaltato e pesato `negative_weight` volte.
   - resto -> **exclude**: i mediocri non aggiungono segnale.

Knob:

```bash
--final-eval-best-fraction 0.25
--final-eval-worst-fraction 0.10
--final-eval-shape-power 0.0      # >0: weight *= shape_overall**power
                                  # solo nel gruppo include, non sui invertiti.
                                  # 0 = peso uniforme entro top-fraction
                                  # 1 = lineare in shape_overall
                                  # 1.5..2.0 = enfasi forte sui top
--no-final-eval-shape-filter      # disattiva, torna al comportamento legacy
```

Quando il filtro e' attivo, il sottotitolo del PNG mostra
`shape_filter=on best=... worst=... shape_power=... included=N inverted=M
excluded=K`. Il JSON di firma include `shape_filter.excluded_reasons` con il
conteggio per causa (`no_predicted_peaks`, `mediocre`, ecc.).

### Negative inertia (legacy, attivo solo con shape filter off)

Comportamento preesistente: se il totale stimato da un trial e' sotto una
soglia molto bassa, quel trial viene letto in reverse mode (segnale invertito,
peso `negative_weight`). Quando il shape filter e' attivo (default), questa
logica e' sostituita dal classificatore include/invert/exclude descritto sopra.
Quando si usa `--no-final-eval-shape-filter`, la negative inertia legacy resta
attiva.

Flag principali:

```bash
--final-eval-low-threshold 1e-9
--final-eval-negative-weight 3.0
--no-final-eval-negative-inertia
--no-final-evaluation
```

Nel CSV le colonne `reverse_weight` e `reverse_contributors` indicano quanta
parte del consenso arriva dall'inversione (sia shape-filter che legacy).

## Auto-inheritance multilivello

Dopo `train` o `train-max`, Pulsar puo' eseguire automaticamente N passate di
inheritance ricorsivo sul `best_trials_index.csv` appena prodotto.

```bash
--auto-inherit-levels 1     # 1 livello (uso tipico)
--auto-inherit-levels 3     # refinement aggressivo
--auto-inherit-levels 0     # disattivato (default)
```

Ogni livello eredita dal best index del livello precedente, esattamente come
una chiamata manuale `--inherit ...`: filtra i trial alle migliori
`(bank, readout)` per score e ne ricicla i `params` salvati. La ricorsione
condivide la stessa configurazione di partenza (target window, finestre, ecc.)
ma restringe progressivamente la lista di trial.

### Always-include

Per evitare che LCS o l'hybrid LCS escano dalla lista di refinement quando non
sono i top assoluti, il default `--always-include lcs,lcs_hybrid` forza
l'inclusione del miglior trial per ciascuno di questi bank in ogni livello di
inheritance. Token speciali risolti: `lcs` -> `__lcs__`, `lcs_hybrid` (alias
`hybrid`) -> `__hybrid__`. Altri valori sono trattati come bank name letterale.

```bash
--always-include lcs,lcs_hybrid,mag,wave   # estendi
--no-always-include                         # disattiva il forzaggio
```

`always_include` e' nella `inherit_keys` quindi si propaga a tutti i livelli
auto-multilevel senza ripeterlo.

## CLI presets

Per evitare catene di 30+ flag, Pulsar definisce dei preset componibili in
`PRESETS` (in `cli.py`). Si attivano con `--preset NAME` (anche piu' separati
da virgola). Gli argomenti utente passati dopo `--preset` sovrascrivono
sempre i valori del preset.

```bash
python cli.py train --list-presets                               # elenco
python cli.py train --preset japan-event-l1 --task X --db Y      # uso base
python cli.py train --preset japan-event-l1,shape-strict --task X --db Y
```

Vedi `docs/pulsar_cli_recipes.md` sezione "12. CLI presets" per la lista
completa e gli esempi.

## Training sample weighting

Il ranking recency-aware sceglie meglio, ma non cambia come i modelli imparano.
Per questo e' stata aggiunta anche la pesatura dei campioni durante il training.

Di default, nei run CSV, Pulsar applica:

```bash
--train-recency-weight exp
--train-recency-strength 1.0
--train-event-weight auto
--train-max-event-weight 8.0
```

Il peso finale e':

```text
sample_weight = recency_weight * event_weight
```

poi normalizzato a media 1.

Effetto per famiglia:

- `ridge` / `linear`: usa `sample_weight` nativo;
- DeepNet: usa loss MSE pesata;
- LCS: usa replay probabilistico extra dei campioni pesati, oltre al replay dei
  positivi.

Per disattivare tutto:

```bash
--no-train-sample-weighting
```

## Forecast window

Il forecast usa solo righe presenti nel CSV. Se chiedi:

```bash
--forecast-start-date 2026-04-01
```

ma la prima riga disponibile e' `2026-04-03`, allora il forecast parte da
`2026-04-03`.

Per includere sicuramente la riga di aprile nel dataset attuale, usare:

```bash
--forecast-start-date 2026-03-05
```

Questo esclude `2026-03-04` e include `2026-04-03`.

Con:

```bash
--forecast-trainset train2forecast
```

il modello finale viene rifittato su tutte le righe disponibili prima della
forecast window, senza includere le righe forecast.

## Artifact prodotti

Quando c'e' forecast, train-max o final evaluation attiva, Pulsar salva artifact
nella directory `pulsar_train_best_trials_*` accanto al dataset.

Output principali:

- test CSV/PNG del best trial;
- forecast CSV/PNG;
- final evaluation CSV/PNG/JSON overall;
- firma JSON del trial;
- `best_rules.json` se il modello e' LCS;
- `best_by_bank/` con il migliore per ogni famiglia bank;
- `best_by_bank/recent_validation/` con grafici recenti uniformi per controllo
  visivo umano.

Il grafico storico migliore puo' essere vecchio perche' rappresenta il best
trial su una finestra backtest. Il grafico in `recent_validation/` serve invece
a controllare il comportamento vicino al forecast.

## Interpretazione prudente

Questi modelli non dimostrano causalita' fisica. Il benchmark aiuta a confrontare
pattern storici e a generare segnali operativi, ma non puo' certificare se un
evento e' foreshock o se avverra' un evento maggiore.

Per decisioni reali, usare sempre fonti sismologiche ufficiali e trattare i
risultati come segnali sperimentali.

# Post Hybrid Artifacts

`post_hybrid_artifacts.py` combina due artifact gia' esportati da DLvsWAVE senza rifare training.

L'idea e':

```text
artifact A prediction
+ artifact B prediction
+ normalizzazione
+ calibrazione soglie su validation
+ logica AND / OR / weighted
= nuovo validation + nuovo forecast + nuove regole derivate
```

Il tool non modifica i modelli originali. Legge i loro CSV/JSON esportati, calcola una nuova fusione e salva nuovi artifact.

## Input Attesi

Ogni artifact deve essere un file:

```text
...__test.json
```

Il JSON deve puntare almeno a:

```text
validation_combined_csv
forecast_csv
```

Se contiene anche:

```text
best_rules_json
```

il tool produce un `__derived_rules.json` con le regole LCS coinvolte nella fusione.

## Comando Base

```bash
python3 post_hybrid_artifacts.py \
  --a /path/to/A__test.json \
  --b /path/to/B__test.json \
  --logic and \
  --normalize auto \
  --out-dir /path/to/post_hybrid_checks \
  --name my_post_hybrid
```

Output:

```text
my_post_hybrid__validation_combined.csv
my_post_hybrid__forecast.csv
my_post_hybrid__combined.png
my_post_hybrid__lineage_diagram.png
my_post_hybrid__lineage_comparison.png
my_post_hybrid__derived_rules.json
my_post_hybrid__summary.json
my_post_hybrid__sources/
```

La cartella `__sources/` contiene due sottocartelle, una per ciascun artifact sorgente:

```text
my_post_hybrid__sources/
  source_a__.../
    source_manifest.json
    artifact originale .json
    test CSV
    validation CSV
    forecast CSV
    PNG combinato
    best_rules.json se presente
  source_b__.../
    source_manifest.json
    ...
```

Questo rende il merge ispezionabile: puoi aprire il post-hybrid e vedere subito da quali due artifact deriva, con i loro CSV/PNG/regole originali copiati accanto al risultato.

## PNG Di Spiegazione

Ogni merge genera anche due PNG esplicativi in inglese.

### `__lineage_diagram.png`

Diagramma di flusso della decisione:

```text
Candidate A  --->  Final Post-Hybrid Gate  --->  Result
Candidate B  ---/
```

Mostra:

```text
bank/readout/seed di A
bank/readout/seed di B
metriche validation di Candidate A
metriche validation di Candidate B
reassessment pre-merge di Candidate A/B sul validation set allineato
se un candidato e' hybrid, il suo LCS interno, partner, mode, alpha e threshold
merge finale usato da post_hybrid_artifacts.py
normalizzazione
calibrazione
soglie A/B
selection score della coppia
metriche finali validation
delta +x/-x rispetto al miglior candidato sorgente
giudizio automatico del miglioramento o del trade-off
result box diviso in descrizione testuale a sinistra e confronto metriche a destra
linea tratteggiata interna, linea orizzontale di riferimento Fusion nel grafico, timestamp locale in footer
barre leggibili anche in stampa bianco/nero: Fusion pieno, A diagonale fine, B quasi vuoto con bordo
```

Il `selection score` non e' il KPI originale del singolo artifact. E' il punteggio usato dalla routine di scansione per ordinare le coppie, basato su simulazione post-hybrid, shape, depression, forecast guard e complementarita'.

Le frecce sono disegnate a gomito per rendere chiaro il flusso:

```text
Candidate A
          \ 
           -> Final Post-Hybrid Gate -> Result
          /
Candidate B
```

Nei box Candidate A/B compaiono solo metriche rivalutate prima del merge:

```text
Pre-merge validation F1
Pre-merge recall
Pre-merge precision
Pre-merge balanced accuracy
Pre-merge prediction threshold
```

Questo reassessment usa il validation CSV combinato dell'artifact e viene fatto prima della fusione. Serve a evitare confusione tra:

```text
metriche originali del singolo artifact
metriche al threshold calibrato del merge
metriche pre-merge sullo stesso validation set usato dalla fusione
```

Nel box `Result`, i valori tra parentesi indicano il delta rispetto al miglior valore tra Candidate A e Candidate B nel reassessment pre-merge:

```text
F1=0.857 (+0.123)
Precision=0.750 (-0.050)
```

I delta positivi sono verdi e in grassetto; i delta negativi sono rossi e in grassetto.

Il giudizio automatico e' meccanico: confronta F1, recall, precision e balanced accuracy finali contro le metriche pre-merge migliori dei sorgenti e descrive se il merge e' un miglioramento netto, un miglioramento con trade-off, un match, oppure una fusione selettiva non migliorativa.

Il diagramma include anche un mini grafico a barre nel riquadro `Result`:

```text
per ogni metrica: Fusion / Candidate A / Candidate B
```

I valori sono le metriche del reassessment pre-merge per A/B e le metriche finali post-hybrid per Fusion. Le metriche candidate sono colorate rispetto all'altro candidato: verde se migliori o uguali, rosso se inferiori.

Il verdetto automatico e' dentro `Result`, in corsivo grassetto. E' verde se la fusione migliora almeno una metrica rispetto ai candidati pre-merge, rosso se la fusione e' sfavorevole su tutte le metriche principali.

### `__lineage_comparison.png`

Grafico comparativo:

```text
Candidate A validation
Candidate B validation
Final post-hybrid validation
Candidate A forecast
Candidate B forecast
Final post-hybrid forecast
```

Serve a vedere visivamente da dove deriva il risultato finale e come la logica di merge impatta davvero il forecast.

## Normalizzazione

`--normalize` decide come trasformare le predizioni prima della fusione.

```text
auto    binary se la predizione e' gia' 0/1, altrimenti minmax
binary  trasforma in 0/1 usando la soglia evento dell'artifact
minmax  scala i valori continui nel range 0..1 usando la validation
none    usa i valori grezzi
```

Nel caso che abbiamo testato:

```text
A = hybrid LCS default + deep:tiny
B = passthrough + torch_tiny
```

`auto` ha fatto:

```text
A -> binary
B -> minmax
```

Questo e' utile perche' `torch_tiny` porta informazione continua, mentre l'hybrid LCS era gia' un segnale evento 0/1.

## Calibrazione

La calibrazione e' attiva per default:

```text
--calibrate validation
--calibrate-metric f1
```

Quindi, se non specifichi altro, il tool cerca su validation le soglie migliori per massimizzare F1.

Per disattivarla:

```bash
--calibrate none
```

Per usare un'altra metrica:

```bash
--calibrate-metric bal_acc
--calibrate-metric precision
--calibrate-metric recall
--calibrate-metric f05
```

La calibrazione non e' cosmetica: le soglie trovate sulla validation vengono applicate anche al forecast.

## Logiche Di Fusione

```text
and       evento solo se A e B confermano
sure      alias di and
or        evento se A oppure B conferma
weighted  media pesata degli score normalizzati
```

Per rare events, `and` e' di solito il primo candidato serio, perche' riduce falsi positivi.

`or` e' utile come stress test, ma tende ad accendere troppi punti.

## Esempio Reale

Artifact usati:

```text
A = 0.615__hybrid__hyb_default_dntiny_w0p50__seed5__test.json
B = 0.831__passthrough__torch_tiny__seed4__test.json
```

Comando:

```bash
python3 post_hybrid_artifacts.py \
  --a /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/pulsar_train-max_best_trials_20260429-183538/master_with_usgs_core/0.615__hybrid__hyb_default_dntiny_w0p50__seed5__test.json \
  --b /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/pulsar_train-max_best_trials_20260429-183538/master_with_usgs_core/0.831__passthrough__torch_tiny__seed4__test.json \
  --logic and \
  --normalize auto \
  --out-dir /mnt/git0/git/repository/astro-USGS2/DB/agentic_runs/JAPAN-2026-FULLYEAR-30D-L5-H-OVN-NOPACK_20260408-132232/L1/energy-entry-main/pulsar_train-max_best_trials_20260429-183538/post_hybrid_checks \
  --name lcsdeep_tinyXpassthrough_torchtiny__and_auto_default_cal
```

Risultato osservato:

```text
f1        = 0.857
recall    = 1.000
precision = 0.750
bal_acc   = 0.979
tp=3 fp=1 tn=23 fn=0
```

Soglie calibrate:

```text
threshold_a = 0.5
threshold_b = 0.8406104014789999
```

Forecast finale:

```text
2026-08-01 -> predicted=1
2026-08-31 -> predicted=1
gli altri punti -> predicted=0
```

## Regole Derivate

Se uno dei due artifact contiene LCS, il tool salva:

```text
__derived_rules.json
```

In `and`, una regola LCS positiva viene annotata come:

```text
regola LCS gated by artifact B
```

cioe':

```text
la regola LCS sopravvive solo se anche l'altro artifact conferma
```

Importante: questo non e' retraining LCS. Gli export contengono le `best_rules`, ma non il firing completo di ogni regola su ogni punto. Quindi il file e' un rule set derivato dalla fusione, non una nuova popolazione LCS riaddestrata.

## Scelta Automatica Delle Coppie

Il tool puo' anche scandagliare una cartella o un `best_trials_index.csv` e proporre coppie candidate.

Da cartella:

```bash
python3 post_hybrid_artifacts.py \
  --scan-dir /path/to/pulsar_run/master_with_usgs_core \
  --proposal-only \
  --logic and \
  --normalize auto
```

Da index:

```bash
python3 post_hybrid_artifacts.py \
  --index-csv /path/to/pulsar_run/best_trials_index.csv \
  --proposal-only \
  --logic and \
  --normalize auto
```

Scrive:

```text
post_hybrid_checks/post_hybrid_pair_proposals.csv
```

Se togli `--proposal-only`, prende la prima coppia proposta e genera direttamente gli artifact post-hybrid.

La scansione non prende semplicemente il rank 1 e rank 2 originali. Il processo e':

```text
1. carica artifact con validation e forecast disponibili
2. calcola un punteggio candidato non basato solo su overall
3. prende i migliori candidati
4. simula tutte le coppie tra quei candidati
5. calibra le soglie su validation
6. ordina le coppie per selection score post-hybrid
7. se non usi --proposal-only, fonde la coppia rank 1
```

## Come Vengono Proposte Le Coppie

La selezione automatica evita di usare solo `overall`.

Ogni artifact viene valutato con:

```text
overall
event_f1
event_recall
event_bal_acc
shape_overall
peak_score
depression_score
forecast non piatto
```

Poi il tool simula la fusione di coppie candidate e ordina per:

```text
F1 post-hybrid calibrato
balanced accuracy
recall
precision
shape media
depression minima tra i due
forecast non piatto
bonus di complementarita' tra famiglie diverse
```

Questo e' pensato proprio per evitare il caso in cui un artifact vince per KPI, ma visivamente e' troppo piatto o cattura solo un segmento troppo facile.

## Forecast Guard

Nella scelta automatica e' attivo per default:

```text
--forecast-guard auto
```

Questo controllo non richiede che il forecast abbia picchi. Sarebbe pericoloso: se il futuro e' davvero quieto, un buon modello puo' produrre un forecast piatto basso.

Il guard serve solo come anti-degenerazione:

```text
piatto basso          -> accettabile
variabile            -> piccolo bonus
piatto alto          -> penalita'
quasi tutto positivo -> penalita'
```

Quindi il forecast non viene usato per rendere il risultato piu' accattivante. La qualita' resta guidata dalla validation; il forecast guard evita solo coppie che accendono quasi tutto o che sembrano patologicamente piatte alte.

Per disattivarlo:

```bash
--forecast-guard off
```

Parametri:

```text
--forecast-flat-eps 1e-9
--forecast-high-ratio 0.8
```

`forecast-high-ratio` indica la quota di punti positivi oltre cui un forecast piatto/quasi alto viene considerato sospetto.

Con logica `and`, il forecast finale viene comunque ricalcolato cosi':

```text
forecast_final = forecast_A conferma AND forecast_B conferma
```

Quindi un picco futuro viene eliminato automaticamente se non e' confermato da entrambi. Il guard non forza questa eliminazione: la logica di fusione la fa gia'. Il guard serve solo a ordinare meglio le coppie candidate.

## Lettura Consigliata

Per rare events, una coppia buona dovrebbe avere:

```text
buon recall sugli eventi
buon peak_score
depression_score non nullo
shape_overall decente
forecast non completamente piatto
complementarita' tra segnali
```

Il giudizio visivo resta importante: la shortlist automatica serve a ridurre lo spazio di ricerca, non a sostituire la revisione dei PNG.

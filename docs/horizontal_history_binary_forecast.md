# Horizontal History Binary Forecast

Questa pipeline mantiene la data reale di ogni riga e aggiunge memoria storica
compatta in colonne extra. Il forecast resta leggibile sulla timeline reale:
le righe future sono ancora `2026-05-01`, `2026-05-31`, ecc.; il time-travel
entra solo come feature.

## Idea

Il master puo' contenere sismica analogica (`mag`, `depth`, `latitude`,
`longitude`) e feature astronomiche. Il training usa invece un target binario
stabile:

```text
target = binary_source_col binary_operator binary_threshold
```

Esempi:

```text
target = mag >= 8.5
target = latitude >= 11
target = mag >= 7.9 AND dentro zona japan
```

Il nome della colonna resta sempre `target` di default. Il significato viene
tracciato nei report, non nel nome della colonna.

## File Generati

- `master_with_usgs_core_astrofmt_float.csv`: master float universale, con
  sismica e astro originali.
- `master_with_usgs_core_astrofmt_horizontal_history_float.csv`: master
  specializzato non quantizzato con `target`, storia orizzontale e derivate
  presente-passato.
- `master_with_usgs_core_astrofmt.csv`: master quantizzato/sanitizzato usato
  dal training. Quando la history e' attiva, viene creato dopo
  `master_with_usgs_core_astrofmt_horizontal_history_float.csv`, quindi la
  quantizzazione vede anche `tt_seis_*`, `tt_astro_*` e `tt_stitch_*`.
- `horizontal_history_manifest.json`: descrive target, zone, filtri,
  neutralizzazione, storia orizzontale.
- `target_selection_report.json` e `target_selection_report.md`: descrivono
  quale grandezza e' stata usata come target, soglie, distribuzione 0/1, skip
  columns e feature effettive.

## Target

Argomenti principali:

```bash
--binary-target-col target
--binary-source-col mag
--binary-operator '>='
--binary-threshold 8.5
```

Nel wrapper binario puoi usare la scorciatoia:

```bash
--target-col mag --binary-threshold 8.5
```

In questo caso il wrapper interpreta `mag` come sorgente analogica e usa
comunque `target` come colonna finale 0/1.

Campi sismici esclusi dalle feature:

```text
date,mag,depth,latitude,longitude
```

Questo evita leakage: il modello non vede direttamente la grandezza usata per
costruire `target`.

## Filtri

Sintassi:

```text
campo:(>a and <b); altro_campo:(>=x and <=y)
```

- `and` dentro le parentesi combina piu' condizioni sulla stessa colonna.
- `;` combina colonne diverse con AND.
- `OR` combina blocchi alternativi.

Esempio con OR:

```bash
--row-filter 'latitude:(>-60 and <65); longitude:(>90 and <180) OR latitude:(>-60 and <65); longitude:(>-180 and <-60)'
```

`--row-filter` filtra righe storiche extra, non definisce il target. Di default
per i run regionali a magnitudo alta va lasciato `none`: il catalogo eventi e'
gia' limitato da `MIN_MAG`, mentre il modello deve vedere anche record `0`
vicini agli eventi e negativi sparsi in mezzo.

Quando `HISTORY_NEGATIVE_SAMPLING_MODE=random-sparse`, il generatore protegge
automaticamente:

- positivi `target=1`;
- righe prima/dopo ogni positivo, secondo `HISTORY_KEEP_NEIGHBOR_RECORDS`;
- righe forecast;
- negativi recenti pre-forecast.

Questo evita che un filtro troppo aggressivo elimini proprio l'informazione
"vicino ma non evento". Per filtrare anche le righe future usa
`--forecast-filter`.

## Zone CSV

File default:

```text
resources/seismic_zones.csv
```

Schema:

```text
zone_id,name,latitude_min,latitude_max,longitude_min,longitude_max,depth_min,depth_max,notes
```

`depth_min/depth_max` sono opzionali concettualmente, ma nel CSV default sono
presenti per permettere stratificazioni 3D.

Usare una zona:

```bash
--target-zones japan
```

Usare piu' zone come macro-zona unica:

```bash
--target-zones japan,japan_nankai,japan_tohoku
```

Usare una regione custom senza CSV:

```bash
--target-region 'latitude:(>26.5 and <48.5); longitude:(>122.7 and <151); depth:(>=0 and <=700)'
```

## Out-Of-Region Mode

Per target regionali puoi mantenere gli eventi fuori regione come negativi
duri. Questo serve a insegnare:

```text
grande evento nel mondo != grande evento nella zona target
```

Modalita':

```bash
--out-of-region-mode keep
--out-of-region-mode neutralize-seismic
```

Con `neutralize-seismic`, le righe storiche fuori regione restano nel master ma
i campi:

```text
mag,depth,latitude,longitude
```

diventano `0`. Il contesto astro e la storia orizzontale restano disponibili.
Le righe forecast non vengono neutralizzate in questo passaggio.

## Storia Orizzontale

Quando `ENABLE_HORIZONTAL_HISTORY=1`, il pipeline aggiunge:

- `tt_days_back`: offset storico.
- `tt_lookup_delta_days`: distanza tra data storica richiesta e riga master
  usata come lookup.
- `tt_seis_*`: ultimo evento sismico prima della data storica:
  `has_prior`, `delta_days`, `mag`, `depth`, `latitude`, `longitude`.
- `tt_astro_<body>_<field>`: feature astro storiche per pochi corpi.
- `tt_stitch_<body>_radec_sep_deg`: cucitura presente-passato per ogni corpo,
  cioe' separazione RA/DEC tra stato corrente e storico.

Default:

```bash
HISTORY_MODE=fibonacci-gold
HISTORY_VALUE=1280
HISTORY_ASTRO_BODIES=301,599,99942
HISTORY_ASTRO_FIELDS=RA,DEC,r,r_rate,ObsEclLon,ObsEclLat
```

Corpi default:

- `301`: Moon
- `599`: Jupiter
- `99942`: Apophis

Sono stati scelti per coprire un corpo vicino, un pianeta principale e un corpo
secondario gia' presente nei master recenti.

## Casi Pratici

### Worldwide M8.5+

```bash
cd /mnt/git0/git/repository/DLvsWAVE

./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 8.5
```

### Ring Of Fire M8.5+

```bash
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 8.5 \
  --target-zones ring_pacific_west,ring_pacific_east
```

Equivalente senza CSV:

```bash
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 8.5 \
  --row-filter 'latitude:(>-60 and <65); longitude:(>90 and <180) OR latitude:(>-60 and <65); longitude:(>-180 and <-60)'
```

### Japan M7.9+ Con Negativi Globali Neutri

Usa un catalogo sorgente mondiale piu' largo, ad esempio `WORLD-MAG7.7`, poi
filtra a `7.9` nel pipeline.

```bash
SRC_EVENTS=/mnt/git0/git/repository/astro-USGS2/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv \
MIN_MAG=7.9 \
RUN_LABEL=japan-zone-mag79plus-30d-may-dec-horizontal-binary-kan-xpu \
OUT_DIR=/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-30d-may-dec-horizontal-binary-kan-xpu \
HISTORY_NEGATIVE_SAMPLING_MODE=none \
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 7.9 \
  --target-zones japan \
  --out-of-region-mode neutralize-seismic \
  --row-filter none
```

Comportamento:

- `target=1`: evento `M7.9+` dentro `japan`.
- `target=0`: evento `M7.9+` fuori `japan`.
- fuori regione: `mag/depth/latitude/longitude = 0` se neutralizzato.
- forecast: resta libero, con `target=0` solo come placeholder ignoto.

### Japan Nankai Shallow/Intermediate

```bash
SRC_EVENTS=/mnt/git0/git/repository/astro-USGS2/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv \
MIN_MAG=7.9 \
RUN_LABEL=japan-nankai-mag79plus-30d-horizontal-binary-kan-xpu \
OUT_DIR=/mnt/git0/git/repository/astro-USGS2/DB/japan-nankai-mag79plus-30d-horizontal-binary-kan-xpu \
HISTORY_NEGATIVE_SAMPLING_MODE=none \
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 7.9 \
  --target-zones japan_nankai \
  --out-of-region-mode neutralize-seismic \
  --row-filter none
```

### Custom 3D Zone

```bash
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh \
  --target-col mag \
  --binary-threshold 7.9 \
  --target-region 'latitude:(>28 and <37); longitude:(>128 and <143); depth:(>=0 and <=120)' \
  --out-of-region-mode neutralize-seismic \
  --row-filter none
```

## Negativi Sparsi

Per problemi globali molto sbilanciati puoi ridurre gli zeri storici:

```bash
HISTORY_NEGATIVE_SAMPLING_MODE=random-sparse
HISTORY_RANDOM_NEGATIVES_PER_POSITIVE=8
HISTORY_KEEP_NEIGHBOR_RECORDS=2
HISTORY_KEEP_RECENT_NEGATIVES=6
```

Per problemi regionali compatti con fuori-zona come hard negatives, spesso e'
meglio:

```bash
HISTORY_NEGATIVE_SAMPLING_MODE=random-sparse
ROW_FILTER=none
```

cosi' restano i negativi essenziali attorno agli eventi, una quota di negativi
sparsi e le righe forecast. Usa `HISTORY_NEGATIVE_SAMPLING_MODE=none` solo se
vuoi tenere tutti gli eventi fuori regione disponibili come esempi negativi e
accetti un master piu' grande.

## Grafici E CSV

Nei grafici validation:

- blu `actual`: `0/1` del target binario;
- rosso `predicted`: score/probabilita' stimata dal modello.

Nel forecast:

- `actual` futuro e' placeholder `0`, perche' il futuro e' ignoto;
- la curva utile e' `predicted`;
- la data sull'asse X resta la data reale dello slot forecast.

Nel CSV forecast:

- `date` e' la data reale della timeline corrente;
- `predicted` o colonne equivalenti sono lo score previsto;
- la semantica del target va letta da `target_selection_report.*`.

La KAN strength fusion usa i forecast dei trial esportati e, di default,
ordina/seleziona le sorgenti con:

```bash
--rank-mode validation-quality
--inverse-worst-n 1
```

Questa modalita' usa solo qualita' validation/evento:

```text
F1, recall, balanced accuracy, precision, specificity
```

e non usa velocita', tempo di training, numero parametri o `KPI/v`. Questo e'
importante per il forecast: il modello deve contribuire per qualita' del
segnale, non perche' e' piu' economico da eseguire.

`--inverse-worst-n 1` e' attivo di default: il peggior forecast KAN esportato
viene usato come contro-segnale, con formula:

```text
inverse contribution = 1 - minmax(forecast_score)
```

In pratica, se un trial ha mostrato qualita' validation bassa, il suo forecast
puo' essere informativo al contrario. La fusione finale sottrae/rovescia quel
segnale senza usare velocita' o `KPI/v` per decidere il peso. Per disattivare
questo comportamento:

```bash
--inverse-worst-n 0
```

Nelle pipeline shell il valore e' controllato da:

```bash
FUSION_INVERSE_WORST_N=1
```

Il PNG di fusion riporta esplicitamente gli argomenti applicati, ad esempio
`rank-mode=validation-quality; inverse-worst-n=1; applied=1`, cosi' il grafico
resta leggibile anche senza aprire il JSON.

## Strategie Consigliate

1. Usa target binario per detection, non regressione analogica, quando l'evento
   e' raro.
2. Per regioni specifiche, usa un catalogo mondiale piu' largo e
   `target-zones`: la rete vede eventi globali simili ma deve imparare a
   distinguere quelli nella zona.
3. Usa `neutralize-seismic` quando vuoi che i fuori-zona siano negativi neutri
   ma mantengano il contesto astro/storico.
4. Usa `depth_min/depth_max` per separare shallow/intermediate/deep, soprattutto
   in subduzione.
5. Non filtrare il forecast futuro a meno che tu voglia esplicitamente leggere
   solo una zona: lascia `--forecast-filter none` per preservare la timeline.
6. Confronta sempre almeno tre run:
   - globale;
   - macro-zona;
   - zona specifica con hard negatives fuori-zona.

## Geographic Counter-Check

Per dare un credibility grade geografico, puoi creare run comparativi automatici
con:

- zona target principale con horizontal history;
- stessa zona senza horizontal history;
- proximity counter-zone vicine ma non sovrapposte alla main, con horizontal
  history.

Questa non e' solo una "zona alternativa": e' un false-positive test
settoriale. La domanda diventa:

```text
se il segnale vero e' nella zona main, il modello accende anche zone vicine
che non includono la main?
```

Se la risposta e' no, il modello sta sagomando meglio la geografia. Se la
risposta e' si', il forecast puo' avere segnale temporale ma poca precisione
settoriale, a meno che esista davvero un secondo evento vicino/fuori zona.

Questo misura due margini:

- `horizontal_gain`: quanto migliora la storia orizzontale rispetto al run
  senza storia;
- `geographic_margin`: quanto la zona target batte le zone vicine.

Dal run notturno XPU Giappone/proximity, il confronto viene mantenuto
simmetrico impostando gli stessi conteggi per tutte le varianti:

```bash
TARGET_EVENT_COUNT=2
VALIDATION_EVENT_COUNT=2
VALIDATION_PRE_RECORDS=6
VALIDATION_POST_RECORDS=6
OUT_OF_REGION_MODE=neutralize-seismic
```

`VALIDATION_PRE_RECORDS` e `VALIDATION_POST_RECORDS` possono essere alzati per
insegnare meglio il contorno "vicino ma non evento". Gli eventi sismici fuori
dalla zona target restano nel tracciato temporale, ma con colonne sismiche
neutralizzate, cosi' diventano esempi negativi realistici invece di sparire.

Il batch notturno puo' usare anche una famiglia KAN+Deep ibrida. Nel profilo
compatto attuale:

```bash
HYBRID_KAN=1
DEEP_PRESETS_RUN=tiny
DEEP_DEVICE=xpu
HYBRID_KAN_PARTNERS=deep:tiny
HYBRID_KAN_MODES=weighted
HYBRID_KAN_ALPHAS=0.5
```

`cli.py` registra questi trial come bank `__kan_hybrid__`. Per tornare al puro
KAN basta lanciare con `HYBRID_KAN=0`.

Preparare un piano Giappone M7.9+:

```bash
python geographic_countercheck.py plan \
  --output-root /mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-geo-countercheck \
  --base-run-label japan-zone-mag79plus-geo-countercheck \
  --target-zones japan \
  --counter-count 3 \
  --counter-source proximity \
  --proximity-gap-deg 1.0 \
  --proximity-rings 4 \
  --proximity-lateral-fracs 0,0.25,0.5,0.75,1,-0.25,-0.5,-0.75,-1 \
  --proximity-directions east,west,north,south,ne,nw,se,sw \
  --counter-min-events auto \
  --counter-min-event-frac 0.35 \
  --counter-min-target-span-frac 0.75 \
  --counter-min-target-decades-frac 0.60 \
  --src-events /mnt/git0/git/repository/astro-USGS2/DB/WORLD-MAG7.7-1900-2025-10-01-MERGED/earthquakes.RAW.csv \
  --min-mag 7.9 \
  --binary-threshold 7.9 \
  --device xpu
```

Il comando crea:

```text
countercheck_plan.json
countercheck_plan.csv
countercheck_zones.csv
countercheck_counter_stats.csv
RUN_GEOGRAPHIC_COUNTERCHECK.sh
```

Lanciare tutto:

```bash
/mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-geo-countercheck/RUN_GEOGRAPHIC_COUNTERCHECK.sh
```

Rigenerare solo il report dopo run completati:

```bash
python geographic_countercheck.py report \
  --plan-json /mnt/git0/git/repository/astro-USGS2/DB/japan-zone-mag79plus-geo-countercheck/countercheck_plan.json
```

Il report finale:

```text
countercheck_report.json
countercheck_report.md
```

Il grade e' euristico. Dal countercheck aggiornato non usa piu' solo il picco
validation/fusion: quando disponibili, i report calcolano:

```text
credibility_score = 0.60 * fused_forecast_validation_score
                  + 0.40 * trial_generalization_score
```

`trial_generalization_score` e' derivato da `overall_mean`, `overall_std`,
`mse_mean`, `mse_std`, `event_f1` e `event_bal_acc` nel
`best_trials_index.csv`. Questo penalizza i trial che sembrano ottimi su poche
finestre validation ma sono instabili o peggiori nella media.

Il grade:

- `A`: target forte, gain positivo, counter-zone piu' deboli;
- `B`: target forte ma uno dei margini non e' chiarissimo;
- `C`: segnale presente ma non molto separato;
- `D`: segnale debole;
- `incomplete`: mancano artefatti dei run.

Nel report, per le proximity counter-zone guarda soprattutto:

- `geographic_margin`: main score meno counter score piu' forte;
- `delta vs main`: distanza temporale tra il picco della counter-zone e il
  picco main;
- forecast PNG/CSV di ogni counter-zone: un picco forte nella zona vicina
  nello stesso periodo del main e' un possibile falso positivo geografico.

Il planner controlla anche la storia sismica delle counter-zone prima di
lanciare i run:

- `--counter-min-events auto`: minimo eventi derivato dalla main; per target
  con abbastanza storia usa almeno 8 eventi o `--counter-min-event-frac`.
- `--counter-min-target-span-frac`: span temporale minimo della counter come
  frazione dello span della main.
- `--counter-min-target-decades-frac`: decadi minime della counter come
  frazione delle decadi della main.
- `--counter-max-main-date-overlap-frac`: evita che validation/counter usino
  quasi le stesse date evento della main.
- `--proximity-rings`: quanti anelli vicini scandire attorno alla main;
- `--proximity-lateral-fracs`: offset laterali per cercare zone vicine ricche
  senza entrare nella main.
- `--counter-overlap-relax-frac`: se non trova abbastanza zone pulite, puo'
  rilassare solo l'overlap tra counter-zone valide, ma non con la main salvo
  `--allow-overlap-counters`.

Prima di lanciare ore di calcolo, apri:

```text
countercheck_counter_stats.csv
```

e verifica `event_count`, `year_span`, `decade_count`,
`main_date_overlap_frac` e
`selection_reason`. Idealmente vuoi `strict_stats_no_counter_overlap`.
`stats_relaxed_counter_overlap` e' accettabile quando serve la terza counter,
perche' sovrappone tra loro zone valide ma mantiene la main esclusa.

## Limiti

Questo processo migliora la definizione del problema, ma non garantisce una
previsione fisica corretta. Gli eventi M8+ sono rari, e i backtest possono
sembrare molto buoni per overfitting se le finestre sono poche.

Controlli minimi:

- backtest su eventi non usati per scegliere la strategia;
- confronto contro run senza storia orizzontale;
- confronto contro shuffled/random negatives;
- stabilita' su seed diversi;
- verifica che i picchi forecast siano robusti tra `tiny`, `small`, `wide`.

## Comandi Base

XPU:

```bash
cd /mnt/git0/git/repository/DLvsWAVE
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh
```

CPU:

```bash
cd /mnt/git0/git/repository/DLvsWAVE
./commands/run_world_mag85_30d_may_dec_horizontal_binary_cpu.sh
```

Disattivare il pretest:

```bash
./commands/run_world_mag85_30d_may_dec_horizontal_binary_xpu.sh --no-metric-test
```

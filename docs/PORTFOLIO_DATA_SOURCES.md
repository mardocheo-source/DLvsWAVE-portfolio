# Scientific data acquisition and redistribution scope

| Source | Acquisition in this repository | Processing and provenance | Public-copy scope |
| --- | --- | --- | --- |
| USGS earthquake catalog | `DLVS-Wave-v2/src/production_inputs.py::load_catalog` uses the [FDSN Event API](https://earthquake.usgs.gov/fdsnws/event/1/), bounded time slices and a 20,000-row response-cap check | Request URL, acquisition time, row count and SHA256 receipts; UTC timestamp parsing, numeric conversion, missing-value handling, ID deduplication and coordinate normalization | Downloader/processing code included; no archived raw catalog, bulk CSV or SQLite research database redistributed |
| NASA/JPL Horizons ephemerides | `DLVS-Wave-v2/src/horizons.py` and `production_inputs.py::load_astronomy` use `astroquery.jplhorizons.Horizons` with explicit objects, epochs and observer configuration | Retry/pacing and error handling in the fetcher; cached manifests, observer contracts and checksum checks in the maintained pipeline | Code included; cached ephemeris exports and original master tables excluded |
| Existing merged scientific tables | `aggregate_nasadb_daily_master.py`, `extract_earthquake_events.py` and `research_pipeline/scientific/derive_aligned_jpl_master.py` | Daily aggregation and alignment, extraction of compact event catalogs, configurable column/date handling | Processing code included; input tables excluded |
| Synthetic regression tasks | `tasks.py`; verified example uses `friedman1` | Deterministic seed selection and separate generated train/test samples in the benchmark | Generator code and small aggregate verification metrics included; no third-party real-data dump needed |

Authoritative references: [USGS copyright guidance](https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted), [USGS access controls and copyrights](https://www.usgs.gov/data-management/access-controls-and-copyrights), [Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html), [Horizons API documentation](https://ssd-api.jpl.nasa.gov/doc/horizons.html).

USGS states that its authored/produced information is generally in the U.S. public domain and asks for credit; third-party content can have separate restrictions. That statement is not applied indiscriminately to every collected file. Horizons is attributed to NASA/JPL; no blanket license is asserted for all JPL materials or input ephemeris products. Consult the original service documentation and relevant model/data references before redistributing outputs.

Imported assets such as `resources/world_basemap_gshhs_c.json`, `resources/seismic_zones.csv` and precomputed ephemeris CSVs are excluded from this edition because their individual redistribution provenance was not established. Their source workflows require those assets to be separately supplied or rights-checked. No NASA imagery, logos or third-party geographic dataset is bundled under a new license.

## Temporal interpretation

`production_inputs.py` explicitly records that its catalog is a later-retrieved historical catalog filtered by earthquake occurrence time, not an archived as-of publication snapshot. A catalog cutoff therefore does not prove that every record was available to an analyst on that historical date. Time offsets for ephemerides, coordinate frames and catalog revisions matter when interpreting retrospective experiments.

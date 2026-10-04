# DLVS-Wave v2.0 - Core Engine Source Modules (`src/`)

This directory contains the modular, highly decoupled source engines of DLVS-Wave v2.0:

| Module | Responsibility | Anti-Leakage / Indexing Role |
| :--- | :--- | :--- |
| [`naming.py`](naming.py) | Hierarchical naming validator & parser | Validates `_shift_m*` (past) and `_shift_p*` (future) tags |
| [`seismic.py`](seismic.py) | USGS FDSN seismic query & spatial filtering | Emits canonical `seis_core_*` fields + `seis_core_place` |
| [`horizons.py`](horizons.py) | NASA JPL Horizons multi-threaded ephemerides | Topocentric observer, jittered backoff, fault tolerance |
| [`indexing.py`](indexing.py) | Shift Lag/Lead Engine & Anti-Leakage Verifier | Computes shifted twin features, audits causal boundaries, generates `master_schema_config.json` |
| [`resampling.py`](resampling.py) | Vertical temporal window summarizer ($N$ days) | Enforces **Safety Lock** on bit-packed data & recalculates shifted indices |
| [`compression.py`](compression.py) | 2-bit Quantization & 16-bit Bit-Packing | Strict **Family Isolation** (Astro containers vs Seismic Lag containers vs Untouched core) |
| [`master_fusion.py`](master_fusion.py) | Master creation & chronological fusion | Merges ephemeris + seismic + index shifts |
| [`optimizer.py`](optimizer.py) | Optuna hierarchical prefix search | Searches prefix trees across astro and seismic lag features |
| [`visualization.py`](visualization.py) | Parametric map visualization | Straight linear connectors, de-clustered peak spotting, bottom-right summary box |
| [`reporting.py`](reporting.py) | Markdown decodification manifest generator | Emits container decodification matrix & quantile codebook |
| [`pipeline.py`](pipeline.py) | Master pipeline orchestrator | Glues all modules end-to-end |

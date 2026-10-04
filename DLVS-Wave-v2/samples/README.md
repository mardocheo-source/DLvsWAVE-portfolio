# DLVS-Wave v2.0 - Curated Reference Samples

This directory contains lightweight, end-to-end reproducible reference sample cases for DLVS-Wave v2.0. These samples serve as the canonical blueprint for production runs and testing without cluttering the core repository with heavy century-long datasets.

---

## 1. Sample Directories

1. **[`sample_1_japan_tohoku/`](./sample_1_japan_tohoku/)**:
   - **Region**: Japan (Tohoku Offshore Subduction Zone)
   - **Bounding Box**: Lat `[35.0, 42.0]`, Lon `[138.0, 145.0]` (Sub-ROI: `[37.5, 39.5]`, `[140.5, 143.0]`)
   - **Date Range**: `2024-01-01` to `2024-05-01`
   - **Celestial Bodies**: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn
   - **Features**: Straight leader lines pointing to peak magnitude earthquake dot perimeter, lower-right summary card, Causal Anti-Data-Leakage shift audit, family-isolated 16-bit bit-packing, 7D and 30D scale inheritance.

2. **[`sample_2_italy_central/`](./sample_2_italy_central/)**:
   - **Region**: Central Italy (Apennines Fault System)
   - **Bounding Box**: Lat `[40.0, 45.0]`, Lon `[10.0, 16.0]` (Sub-ROI: `[42.0, 43.5]`, `[12.5, 14.0]`)
   - **Date Range**: `2024-01-01` to `2024-05-01`
   - **Celestial Bodies**: Sun, Moon, Venus, Mars, Jupiter, Saturn, Ceres
   - **Features**: Topocentric observer coordinates, automated zero-variance pruning, lossless codebook mapping, and prefix-guided Optuna exploration.

---

## 2. Each Sample Directory Contains:

* **Step-by-Step Executable Scripts**:
  - `01_extract_seismic.sh`: Modulo 1 USGS Seismic Extraction
  - `02_render_map.sh`: Modulo 7 Parametric Map Rendering (Leader lines & Summary card)
  - `03_fetch_horizons.sh`: Modulo 2 JPL Horizons Ephemeris Fetcher
  - `04_fuse_and_compress_master.sh`: Modulo 5 & 10 Sanitization, Shift Indexing & 1D Bit-Packing
  - `05_resample_30d_and_compress.sh`: Modulo 3 Multi-scale Temporal Resampling (7D / 30D)
  - `06_run_optuna_optimizer.sh`: Modulo 6 Optuna Prefix Optimizer
  - `reproduce_run.sh` / `run_full_sequence.sh`: One-click bash script to reproduce the entire pipeline.
* **Artifacts & Data**:
  - `seismic_events.csv`: USGS earthquake catalog
  - `seismic_events_map.png`: Publication-grade map visualization
  - `master_1d_uncompressed.csv` & `master_1d_packed_16bit.csv`
  - `master_1d_anti_leakage_audit.md` (Anti-data-leakage compliance report)
  - `master_1d_manifest.md` & `master_1d_codebook.json` (Decodification companion)
  - `master_7d_summarized_packed_16bit.csv` & `master_30d_summarized_packed_16bit.csv`
  - `RUN_STEP_BY_STEP_GUIDE.md`: Full Markdown documentation for reproduction.

---

## 3. How to Run a Sample

To execute any sample from scratch:
```bash
cd DLVS-Wave-v2/samples/sample_1_japan_tohoku
bash run_full_sequence.sh
```
Or run each modular step sequentially (`bash 01_extract_seismic.sh`, `bash 02_render_map.sh`, etc.).

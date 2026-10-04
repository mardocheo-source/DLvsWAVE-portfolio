# Run Documentation & Step-by-Step Execution Guide: Run_2_Italy_Central

This directory contains the full pipeline outputs, step-by-step Bash scripts, and decodification manifests for **Run_2_Italy_Central**.

---

## 1. Parameters & Configuration

| Parameter | Configured Value |
| :--- | :--- |
| **Run Name** | `Run_2_Italy_Central` |
| **Timespan** | `2024-01-01` to `2024-05-01` |
| **Primary Bounding Box** | Lat `[41.0, 44.5]`, Lon `[11.5, 15.0]` |
| **Nested Sub-ROI Box** | Lat `[42.0, 43.5]`, Lon `[12.5, 14.0]` |
| **Magnitude Threshold** | $M \ge 2.8$ |
| **Topocentric Observer** | Lat `42.75°N`, Lon `13.25°E` |
| **Celestial Bodies** | `sun,moon,venus,mars,jupiter,saturn,ceres` |
| **Max Major Peaks Spotting** | `1` mainshock peaks with linear leader lines |
| **Anti-Data-Leakage Mode** | Enabled (Zero Future Seismic Feature Leakage) |

---

## 2. Step-by-Step Bash Execution Scripts

You can execute every step individually or all together via Bash:

```bash
# === LAUNCH EVERYTHING IN SEQUENCE ===
./run_full_sequence.sh
```

### Individual Step Scripts:

1. **Step 1: Extract Seismic Events from USGS FDSN**
   ```bash
   ./01_extract_seismic.sh
   ```
   * *Output*: `seismic_events.csv`

2. **Step 2: Render Parametric Geographic Map**
   ```bash
   ./02_render_map.sh
   ```
   * *Output*: `seismic_events_map.png` (Aging Fading, Auto Color-by, Nested Sub-Box, Summary Box, Peak Leader Lines)

3. **Step 3: Fetch Parallel JPL Horizons Ephemerides**
   ```bash
   ./03_fetch_horizons.sh
   ```
   * *Output*: `ephemerides_daily.csv`, `horizons_report.json`

4. **Step 4: Master Chronological Fusion, Shift Indexing & Bit-Packing**
   ```bash
   ./04_fuse_and_compress_master.sh
   ```
   * *Output*: `master_1d_uncompressed.csv`, `master_1d_anti_leakage_audit.md`, `master_1d_schema_config.json`, `master_1d_packed_16bit.csv`, `master_1d_codebook.json`, `master_1d_manifest.md`

5. **Step 5: 30-Day Resampling, Scale-Inherited Shifts & Manifest**
   ```bash
   ./05_resample_30d_and_compress.sh
   ```
   * *Output*: `master_30d_summarized.csv`, `master_30d_summarized_packed_16bit.csv`, `master_30d_summarized_manifest.md`

6. **Step 6: Optuna Hierarchical Prefix Search**
   ```bash
   ./06_run_optuna_optimizer.sh
   ```
   * *Output*: `optuna_summary.json`

---

## 3. Directory Artifacts

| File | Purpose / Description |
| :--- | :--- |
| [`seismic_events.csv`](seismic_events.csv) | Catalog of earthquake records filtered in bounding box |
| [`seismic_events_map.png`](seismic_events_map.png) | High-res geographic activity map with summary card and peak leader lines |
| [`horizons_report.json`](horizons_report.json) | Audit telemetry of parallel NASA JPL Horizons calls |
| [`master_1d_uncompressed.csv`](master_1d_uncompressed.csv) | Daily full-precision float Master CSV with historical shifts |
| [`master_1d_anti_leakage_audit.md`](master_1d_anti_leakage_audit.md) | **Anti-Data-Leakage Causal Audit Report** |
| [`master_1d_schema_config.json`](master_1d_schema_config.json) | Shift parameters schema for dynamic cross-resolution inheritance |
| [`master_1d_packed_16bit.csv`](master_1d_packed_16bit.csv) | 2-bit quantized Master packed into 16-bit uint containers |
| [`master_1d_manifest.md`](master_1d_manifest.md) | **Markdown Decodification Matrix** with exact quantile edges |
| [`master_30d_summarized.csv`](master_30d_summarized.csv) | 30-day temporal window with min/max/mean/median + inherited shifts |
| [`master_30d_summarized_packed_16bit.csv`](master_30d_summarized_packed_16bit.csv) | 16-bit compressed 30-day Master |
| [`master_30d_summarized_manifest.md`](master_30d_summarized_manifest.md) | 30-day Decodification Matrix |
| [`optuna_summary.json`](optuna_summary.json) | Best feature prefix subset selected by Optuna |

# DLVS-Wave v2.0 - Complete CLI & Bash Command Runbook

This document details all bash scripts, CLI commands, and automated runners created for **DLVS-Wave v2.0**.
Every script is **self-contained**: it automatically detects and uses the appropriate Python virtual environment (`.venv/bin/python3`) without requiring manual activation.

---

## 1. Master All-in-One Execution Script

To execute the entire test suite, production pipelines, and century-scale datasets from the terminal:

```bash
/mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/run_all_master_pipelines.sh
```

---

## 2. Per-Run Reproduction Scripts

Every run directory contains two standalone Bash scripts:
1. `reproduce_run.sh`: Reproduces all artifacts (seismic events, map, ephemerides, 16-bit bit-packed master, 30-day summarization, and markdown manifests).
2. `reproduce_map_only.sh`: Fast (1-second) map regeneration applying the latest visual specs (aging fading, auto color-by, nested sub-ROI box).

### Production Runs
* **Run 1 - Japan (Tohoku)**:
  ```bash
  # Full Pipeline Reproduction
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/production_runs/run_1_japan_tohoku/reproduce_run.sh

  # Fast Map Only (1 second)
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/production_runs/run_1_japan_tohoku/reproduce_map_only.sh
  ```
* **Run 2 - Central Italy**:
  ```bash
  # Full Pipeline Reproduction
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/production_runs/run_2_italy_central/reproduce_run.sh

  # Fast Map Only (1 second)
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/production_runs/run_2_italy_central/reproduce_map_only.sh
  ```

### Century-Scale Multi-Country Tests (1900–2030)
* **Location 1 - Japan (Tohoku/Honshu)**:
  ```bash
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/tests_env/multi_country_century_tests/loc1_japan_tohoku_1900_2030/reproduce_map_only.sh
  ```
* **Location 2 - USA (California - San Andreas)**:
  ```bash
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/tests_env/multi_country_century_tests/loc2_usa_california_1900_2030/reproduce_map_only.sh
  ```
* **Location 3 - Mediterranean (Aegean / Hellenic Arc)**:
  ```bash
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/tests_env/multi_country_century_tests/loc3_mediterranean_hellenic_1900_2030/reproduce_map_only.sh
  ```
* **Location 4 - South America (Chile - Nazca Subduction)**:
  ```bash
  /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/tests_env/multi_country_century_tests/loc4_chile_subduction_1900_2030/reproduce_map_only.sh
  ```

---

## 3. Step-by-Step Individual CLI Commands

### Step 1: Extract Seismic Events (USGS FDSN)
```bash
/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3 /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/src/seismic.py \
    --min-lat 35.0 --max-lat 41.5 \
    --min-lon 138.0 --max-lon 145.0 \
    --min-magnitude 5.5 \
    --start-time "1900-01-01" \
    --end-time "2030-12-31" \
    --output-csv "seismic_events.csv"
```

### Step 2: Render Parametric Geographic Map
```bash
/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3 /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/src/visualization.py \
    --input-csv "seismic_events.csv" \
    --output-png "seismic_events_map.png" \
    --min-lat 35.0 --max-lat 41.5 \
    --min-lon 138.0 --max-lon 145.0 \
    --margin-deg 1.5 \
    --size-by magnitude \
    --color-by auto \
    --min-alpha 0.30 \
    --max-alpha 0.95 \
    --sub-min-lat 37.0 --sub-max-lat 40.0 \
    --sub-min-lon 140.0 --sub-max-lon 143.5 \
    --title "Japan Tohoku Earthquakes (1900-2030) - Map"
```

### Step 3: Fetch Parallel JPL Horizons Ephemerides
```bash
/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3 /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/src/horizons.py \
    --start-time "1900-01-01" \
    --stop-time "2030-12-31" \
    --step-size "1d" \
    --observer-type topocentric \
    --lat 38.25 --lon 141.5 --elevation-km 0.05 \
    --bodies "sun,moon,mercury,venus,mars,jupiter,saturn" \
    --output-csv "ephemerides_daily.csv" \
    --output-report "horizons_report.json"
```

### Step 4: Resample & Temporal Summarization (30 Days)
```bash
/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3 /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/src/resampling.py \
    --input-csv "master_1d_uncompressed.csv" \
    --output-csv "master_30d_summarized.csv" \
    --window-days 30 \
    --aggregations "min,max,mean,median"
```

### Step 5: 2-Bit / 16-Bit Quantization & Bit-Packing Compression
```bash
/mnt/git0/git/repository/DLvsWAVE/.venv/bin/python3 /mnt/git0/git/repository/DLvsWAVE/DLVS-Wave-v2/src/compression.py \
    --input-csv "master_1d_uncompressed.csv" \
    --output-csv "master_1d_packed_16bit.csv" \
    --output-codebook "master_1d_codebook.json" \
    --bits-per-field 2 \
    --fields-per-container 8 \
    --container-dtype uint16
```

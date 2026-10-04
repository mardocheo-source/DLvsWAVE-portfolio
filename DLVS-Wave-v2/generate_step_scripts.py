import json
from pathlib import Path

base_dir = Path(__file__).resolve().parent

runs = [
    {
        "dir": base_dir / "samples" / "sample_1_japan_tohoku",
        "sub_box": {"sub_min_lat": 37.5, "sub_max_lat": 39.5, "sub_min_lon": 140.5, "sub_max_lon": 143.0},
        "bodies": "sun,moon,mercury,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "samples" / "sample_2_italy_central",
        "sub_box": {"sub_min_lat": 42.0, "sub_max_lat": 43.5, "sub_min_lon": 12.5, "sub_max_lon": 14.0},
        "bodies": "sun,moon,venus,mars,jupiter,saturn,ceres",
        "max_peaks": 1,
    },
    {
        "dir": base_dir / "production_runs" / "run_1_japan_tohoku",
        "sub_box": {"sub_min_lat": 37.5, "sub_max_lat": 39.5, "sub_min_lon": 140.5, "sub_max_lon": 143.0},
        "bodies": "sun,moon,mercury,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "production_runs" / "run_2_italy_central",
        "sub_box": {"sub_min_lat": 42.0, "sub_max_lat": 43.5, "sub_min_lon": 12.5, "sub_max_lon": 14.0},
        "bodies": "sun,moon,venus,mars,jupiter,saturn,ceres",
        "max_peaks": 1,
    },
    {
        "dir": base_dir / "tests_env" / "demo_visual_run",
        "sub_box": {"sub_min_lat": 36.8, "sub_max_lat": 37.8, "sub_min_lon": 136.5, "sub_max_lon": 137.8},
        "bodies": "sun,moon,mercury,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "tests_env" / "multi_country_century_tests" / "loc1_japan_tohoku_1900_2030",
        "sub_box": {"sub_min_lat": 37.0, "sub_max_lat": 40.0, "sub_min_lon": 140.0, "sub_max_lon": 143.5},
        "bodies": "sun,moon,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "tests_env" / "multi_country_century_tests" / "loc2_usa_california_1900_2030",
        "sub_box": {"sub_min_lat": 33.5, "sub_max_lat": 37.0, "sub_min_lon": -121.0, "sub_max_lon": -116.5},
        "bodies": "sun,moon,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "tests_env" / "multi_country_century_tests" / "loc3_mediterranean_hellenic_1900_2030",
        "sub_box": {"sub_min_lat": 35.5, "sub_max_lat": 39.0, "sub_min_lon": 21.0, "sub_max_lon": 26.5},
        "bodies": "sun,moon,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
    {
        "dir": base_dir / "tests_env" / "multi_country_century_tests" / "loc4_chile_subduction_1900_2030",
        "sub_box": {"sub_min_lat": -33.5, "sub_max_lat": -27.0, "sub_min_lon": -74.0, "sub_max_lon": -70.0},
        "bodies": "sun,moon,venus,mars,jupiter,saturn",
        "max_peaks": 2,
    },
]

for r in runs:
    d = r["dir"]
    if not d.exists():
        continue
    summary_file = d / "pipeline_run_summary.json"
    if not summary_file.exists():
        continue
    with open(summary_file) as f:
        s = json.load(f)

    box = s["bounding_box"]
    dates_raw = s["date_range"]
    if isinstance(dates_raw, list):
        start_date, end_date = dates_raw[0], dates_raw[1]
    elif isinstance(dates_raw, dict):
        start_date, end_date = dates_raw.get("start"), dates_raw.get("end")
    else:
        start_date, end_date = "2024-01-01", "2024-04-30"

    obs = s.get("observer", {})
    bodies = r["bodies"]
    sub = r["sub_box"]
    max_peaks = r.get("max_peaks", 2)

    # 01_extract_seismic.sh
    s1 = f"""#!/usr/bin/env bash
# Step 1: Seismic Catalog Extraction from USGS (Modulo 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 1/6] Extracting Seismic Events from USGS ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/seismic.py" \\
    --min-lat {box["min_lat"]} --max-lat {box["max_lat"]} \\
    --min-lon {box["min_lon"]} --max-lon {box["max_lon"]} \\
    --start-date {start_date} --end-date {end_date} \\
    --min-mag 4.0 \\
    --output-csv "$SCRIPT_DIR/seismic_events.csv"

echo ">>> Step 1 Complete: Saved to $SCRIPT_DIR/seismic_events.csv"
"""

    # 02_render_map.sh
    s2 = f"""#!/usr/bin/env bash
# Step 2: Advanced Parametric Mapping (Aging Fading, Sub-ROI Box & Leader Lines) (Modulo 7)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 2/6] Rendering High-Definition Parametric Seismic Map ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/visualization.py" \\
    --input-csv "$SCRIPT_DIR/seismic_events.csv" \\
    --output-map "$SCRIPT_DIR/seismic_events_map.png" \\
    --map-title "Seismic Activity Map ({d.name.replace('_', ' ').title()})" \\
    --min-lat {box["min_lat"]} --max-lat {box["max_lat"]} \\
    --min-lon {box["min_lon"]} --max-lon {box["max_lon"]} \\
    --enable-time-aging \\
    --sub-min-lat {sub["sub_min_lat"]} --sub-max-lat {sub["sub_max_lat"]} \\
    --sub-min-lon {sub["sub_min_lon"]} --sub-max-lon {sub["sub_max_lon"]} \\
    --sub-box-label "Sub-ROI Target" \\
    --max-annotated-peaks {max_peaks}

echo ">>> Step 2 Complete: High-res map generated at $SCRIPT_DIR/seismic_events_map.png"
"""

    # 03_fetch_horizons.sh
    s3 = f"""#!/usr/bin/env bash
# Step 3: Parallel Ephemerides Extraction from JPL Horizons (Modulo 2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 3/6] Fetching Ephemerides from NASA JPL Horizons ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/horizons.py" \\
    --start-time {start_date} --stop-time {end_date} --step-size 1d \\
    --observer-type {obs.get("type", "geocentric")} \\
    --observer-lat {obs.get("lat", 0.0)} --observer-lon {obs.get("lon", 0.0)} --observer-elevation-km {obs.get("elevation_km", 0.0)} \\
    --bodies {bodies} \\
    --output-csv "$SCRIPT_DIR/ephemerides_daily.csv" \\
    --output-report "$SCRIPT_DIR/horizons_report.json"

echo ">>> Step 3 Complete: Ephemerides saved to $SCRIPT_DIR/ephemerides_daily.csv"
"""

    # 04_fuse_and_compress_master.sh
    s4 = f"""#!/usr/bin/env bash
# Step 4: Chronological Fusion, Shift Indexing, Anti-Leakage Audit & 1D Bit-Packing (Modulo 5, 8, 9, 10)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 4/6] Chronological Master Fusion, Shift Generation & Astro Bit-Packing ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/master_fusion.py" \\
    --astro-csv "$SCRIPT_DIR/ephemerides_daily.csv" \\
    --seis-csv "$SCRIPT_DIR/seismic_events.csv" \\
    --output-dir "$SCRIPT_DIR" \\
    --base-filename master_1d \\
    --bits-per-field 2 \\
    --fields-per-container 8 \\
    --container-dtype uint16 \\
    --astro-min-step -5 --astro-max-step 5 --astro-step-days 7 \\
    --seis-min-step -5 --seis-max-step 0 --seis-step-days 7

echo ">>> Step 4 Complete: 1D Uncompressed & Bit-Packed Masters + Audit Report generated in $SCRIPT_DIR"
"""

    # 05_resample_30d_and_compress.sh
    s5 = f"""#!/usr/bin/env bash
# Step 5: Multi-Scale Temporal Resampling (30-Day Window) & Scale Inheritance (Modulo 3 & 4)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 5/6] Temporal Summarization (30d) & Scale-Inherited Shifts ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/resampling.py" \\
    --input-csv "$SCRIPT_DIR/master_1d_uncompressed.csv" \\
    --output-csv "$SCRIPT_DIR/master_30d_summarized.csv" \\
    --window-days 30 \\
    --aggregations min max mean median \\
    --recalculate-shifts \\
    --shift-config-path "$SCRIPT_DIR/master_1d_schema_config.json"

echo "=== Compressing 30-Day Summarized Master into Astro Bit-Packed Containers ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/compression.py" \\
    --input-csv "$SCRIPT_DIR/master_30d_summarized.csv" \\
    --output-csv "$SCRIPT_DIR/master_30d_summarized_packed_16bit.csv" \\
    --output-codebook "$SCRIPT_DIR/master_30d_summarized_codebook.json" \\
    --bits-per-field 2 \\
    --fields-per-container 8 \\
    --container-dtype uint16

echo ">>> Step 5 Complete: 30D Master & Codebook created in $SCRIPT_DIR"
"""

    # 06_run_optuna_optimizer.sh
    s6 = f"""#!/usr/bin/env bash
# Step 6: Hierarchical Optuna Feature Selection (Modulo 6)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DLVS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/DLVS-Wave-v2"
PYTHON_BIN="${{PYTHON_BIN:-$(which python3)}}"

echo "=== [Step 6/6] Running Hierarchical Prefix Optimization (Optuna) ==="
"$PYTHON_BIN" "$DLVS_ROOT/src/optimizer.py" \\
    --input-csv "$SCRIPT_DIR/master_1d_uncompressed.csv" \\
    --target-col seis_core_magnitude \\
    --n-trials 50 \\
    --output-summary "$SCRIPT_DIR/optuna_summary.json"

echo ">>> Step 6 Complete: Optimal feature subset saved in $SCRIPT_DIR/optuna_summary.json"
"""

    for fname, content in [
        ("01_extract_seismic.sh", s1),
        ("02_render_map.sh", s2),
        ("03_fetch_horizons.sh", s3),
        ("04_fuse_and_compress_master.sh", s4),
        ("05_resample_30d_and_compress.sh", s5),
        ("06_run_optuna_optimizer.sh", s6),
    ]:
        p = d / fname
        p.write_text(content, encoding="utf-8")
        p.chmod(0o755)

print("All step-by-step reproduction scripts generated successfully across all run directories!")

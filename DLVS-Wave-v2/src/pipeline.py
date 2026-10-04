"""Unified Pipeline Orchestrator for DLVS-Wave v2.0.

Coordinates:
  1. Seismic extraction (Modulo 1)
  2. NASA JPL Horizons parallel fetch (Modulo 2)
  3. Master chronological fusion (Modulo 5)
  4. 2-bit / 16-bit Bit-packing compression (Modulo 4)
  5. 30-day temporal summarization (Modulo 3)
  6. Optuna hierarchical prefix optimization (Modulo 6)
  7. Parametric seismic mapping (Modulo 7)
  8. Master manifest reporting (Modulo 8)
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

import pandas as pd

from compression import BitPackingConfig, compress_dataset
from horizons import (
    STANDARD_BASE_BODIES,
    STANDARD_EXPANDED_BODIES,
    BodyTarget,
    HorizonsFetcher,
    HorizonsObserverConfig,
)
from master_fusion import MasterBuilder, MasterFusionResult
from optimizer import PrefixFeatureOptimizer
from reporting import generate_master_manifest
from resampling import TemporalSummarizer, ResamplingConfig
from seismic import SeismicExtractor, SeismicQueryConfig
from visualization import plot_seismic_map

logger = logging.getLogger("dlvs_wave.pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass
class PipelineRunConfig:
    run_name: str
    output_dir: Path
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    min_magnitude: float
    start_time: str
    stop_time: str
    bodies: Sequence[BodyTarget] = field(default_factory=lambda: list(STANDARD_BASE_BODIES))
    window_days_summary: int = 30
    bits_per_field: int = 2
    fields_per_container: int = 8  # 8 x 2-bit = 16-bit container
    run_optuna: bool = False
    optuna_trials: int = 10
    generate_map: bool = True
    map_margin_deg: float = 1.5


@dataclass
class PipelineRunSummary:
    run_name: str
    date_range: tuple[str, str]
    bounding_box: dict[str, float]
    observer_coords: dict[str, float]
    seismic_events_count: int
    ephemeris_days_count: int
    raw_master_shape: tuple[int, int]
    raw_master_path: str
    packed_16bit_master_shape: tuple[int, int]
    packed_16bit_master_path: str
    master_manifest_path: str
    summarized_30d_master_shape: tuple[int, int]
    summarized_30d_master_path: str
    summarized_30d_packed_shape: tuple[int, int]
    summarized_30d_packed_path: str
    summarized_30d_manifest_path: str
    horizons_report_path: str
    codebook_path: str
    seismic_map_path: str | None
    raw_size_bytes: int
    packed_size_bytes: int
    size_reduction_pct: float
    optuna_best_score: float | None = None
    optuna_selected_features_count: int | None = None


def execute_pipeline(config: PipelineRunConfig) -> PipelineRunSummary:
    """Executes full end-to-end DLVS-Wave v2.0 pipeline."""
    out_dir = Path(config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"=== Starting Pipeline Run: {config.run_name} ===")

    # Calculate center of bounding box for topocentric observer
    center_lat = round((config.min_lat + config.max_lat) / 2.0, 4)
    center_lon = round((config.min_lon + config.max_lon) / 2.0, 4)
    logger.info(f"Topocentric observer centered at Lat: {center_lat}, Lon: {center_lon}")

    # 1. Modulo 1: Extract Seismic Events
    logger.info("Step 1: Extracting seismic events...")
    seis_cfg = SeismicQueryConfig(
        min_lat=config.min_lat,
        max_lat=config.max_lat,
        min_lon=config.min_lon,
        max_lon=config.max_lon,
        min_magnitude=config.min_magnitude,
        start_time=config.start_time,
        end_time=config.stop_time,
    )
    seis_extractor = SeismicExtractor(seis_cfg)
    df_seis = seis_extractor.extract()
    seis_path = out_dir / "seismic_events.csv"
    seis_extractor.save(df_seis, seis_path)
    logger.info(f"Seismic extraction complete: {len(df_seis)} events saved to {seis_path.name}")

    # Render parametric seismic map
    seismic_map_path = None
    if config.generate_map:
        try:
            logger.info("Step 1b: Rendering parametric seismic event map...")
            map_img_path = out_dir / "seismic_events_map.png"
            plot_seismic_map(
                df_seis=df_seis,
                min_lat=config.min_lat,
                max_lat=config.max_lat,
                min_lon=config.min_lon,
                max_lon=config.max_lon,
                margin_deg=config.map_margin_deg,
                observer_lat=center_lat,
                observer_lon=center_lon,
                output_path=map_img_path,
                title=f"{config.run_name} - Seismic Activity & Topocentric Observer",
            )
            seismic_map_path = str(map_img_path)
        except Exception as e:
            logger.warning(f"Map generation encountered warning: {e}")

    # 2. Modulo 2: NASA JPL Horizons Parallel Fetch
    logger.info("Step 2: Fetching JPL Horizons ephemerides in parallel...")
    astro_cfg = HorizonsObserverConfig(
        start_time=config.start_time,
        stop_time=config.stop_time,
        step_size="1d",
        observer_type="topocentric",
        lat=center_lat,
        lon=center_lon,
        elevation_km=0.05,
    )
    horizons_fetcher = HorizonsFetcher(astro_cfg)
    df_astro, horizons_report = horizons_fetcher.fetch_all(bodies=config.bodies)
    horizons_rep_path = out_dir / "horizons_report.json"
    horizons_fetcher.save_report(horizons_report, horizons_rep_path)
    logger.info(f"Horizons ephemerides fetched: {len(df_astro)} days, {len(df_astro.columns)} cols.")

    # 3. Modulo 5: Master Fusion (1-day raw and 1-day packed)
    logger.info("Step 3: Master Chronological Fusion...")
    pack_cfg = BitPackingConfig(
        bits_per_field=config.bits_per_field,
        fields_per_container=config.fields_per_container,
        container_dtype="uint16",
    )
    builder = MasterBuilder(packing_config=pack_cfg)
    df_master_raw, df_master_packed, fusion_res = builder.build_and_save(
        df_astro=df_astro,
        df_seis=df_seis,
        output_dir=out_dir,
        base_filename="master_1d",
    )

    # 4. Modulo 3: 30-Day Temporal Summarization
    logger.info(f"Step 4: Generating {config.window_days_summary}-day Summarization...")
    resample_cfg = ResamplingConfig(
        window_days=config.window_days_summary,
        aggregations=("min", "max", "mean", "median"),
    )
    summarizer = TemporalSummarizer(resample_cfg)
    df_summarized = summarizer.summarize(df_master_raw)
    summarized_path = out_dir / f"master_{config.window_days_summary}d_summarized.csv"
    summarizer.save(df_summarized, summarized_path)

    # Compress summarized dataset
    sum_packed_path = out_dir / f"master_{config.window_days_summary}d_summarized_packed_16bit.csv"
    sum_codebook_path = out_dir / f"master_{config.window_days_summary}d_summarized_codebook.json"
    sum_manifest_path = out_dir / f"master_{config.window_days_summary}d_summarized_manifest.md"
    df_sum_packed, sum_codebook, _, _ = compress_dataset(
        df_summarized,
        bits_per_field=config.bits_per_field,
        fields_per_container=config.fields_per_container,
        container_dtype="uint16",
        output_csv_path=sum_packed_path,
        output_codebook_path=sum_codebook_path,
    )
    generate_master_manifest(
        df_uncompressed=df_summarized,
        df_packed=df_sum_packed,
        codebook=sum_codebook,
        output_md_path=sum_manifest_path,
        master_name=f"Master {config.window_days_summary}D Summarized",
    )

    # 5. Modulo 6: Optuna Feature Optimization (Optional)
    optuna_best_score = None
    optuna_selected_count = None
    if config.run_optuna and not df_master_raw.empty:
        logger.info(f"Step 5: Running Optuna Prefix Optimization ({config.optuna_trials} trials)...")
        optimizer = PrefixFeatureOptimizer(df_master_raw, target_col="seis_core_magnitude")
        summary, best_feats, _ = optimizer.optimize(n_trials=config.optuna_trials)
        optuna_best_score = summary["best_score"]
        optuna_selected_count = len(best_feats)
        optuna_out = out_dir / "optuna_summary.json"
        with optuna_out.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    # Summary Record
    run_summary = PipelineRunSummary(
        run_name=config.run_name,
        date_range=(config.start_time, config.stop_time),
        bounding_box={
            "min_lat": config.min_lat,
            "max_lat": config.max_lat,
            "min_lon": config.min_lon,
            "max_lon": config.max_lon,
            "min_magnitude": config.min_magnitude,
        },
        observer_coords={"lat": center_lat, "lon": center_lon, "elevation_km": 0.05},
        seismic_events_count=len(df_seis),
        ephemeris_days_count=len(df_astro),
        raw_master_shape=df_master_raw.shape,
        raw_master_path=str(fusion_res.master_uncompressed_path),
        packed_16bit_master_shape=df_master_packed.shape,
        packed_16bit_master_path=str(fusion_res.master_packed_path),
        master_manifest_path=str(fusion_res.manifest_md_path),
        summarized_30d_master_shape=df_summarized.shape,
        summarized_30d_master_path=str(summarized_path),
        summarized_30d_packed_shape=df_sum_packed.shape,
        summarized_30d_packed_path=str(sum_packed_path),
        summarized_30d_manifest_path=str(sum_manifest_path),
        horizons_report_path=str(horizons_rep_path),
        codebook_path=str(fusion_res.codebook_path),
        seismic_map_path=seismic_map_path,
        raw_size_bytes=fusion_res.uncompressed_size_bytes,
        packed_size_bytes=fusion_res.packed_size_bytes,
        size_reduction_pct=fusion_res.size_reduction_pct,
        optuna_best_score=optuna_best_score,
        optuna_selected_features_count=optuna_selected_count,
    )

    summary_file = out_dir / "pipeline_run_summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(asdict(run_summary), f, indent=2)

    logger.info(f"=== Pipeline Run {config.run_name} Completed Successfully! ===")
    return run_summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DLVS-Wave v2.0 Unified End-to-End Pipeline CLI")
    p.add_argument("--run-name", required=True, help="Name of the pipeline run")
    p.add_argument("--output-dir", required=True, help="Output directory to save all datasets and reports")
    p.add_argument("--min-lat", type=float, required=True, help="Bounding box min latitude")
    p.add_argument("--max-lat", type=float, required=True, help="Bounding box max latitude")
    p.add_argument("--min-lon", type=float, required=True, help="Bounding box min longitude")
    p.add_argument("--max-lon", type=float, required=True, help="Bounding box max longitude")
    p.add_argument("--min-magnitude", type=float, default=3.0, help="Magnitude threshold floor (default: 3.0)")
    p.add_argument("--start-time", required=True, help="Start date/time (e.g. 1900-01-01)")
    p.add_argument("--stop-time", required=True, help="Stop date/time (e.g. 2030-12-31)")
    p.add_argument("--bodies", default="sun,moon,mercury,venus,mars,jupiter,saturn", help="Comma-separated celestial bodies")
    p.add_argument("--window-days-summary", type=int, default=30, help="Summarization window in days (default: 30)")
    p.add_argument("--bits-per-field", type=int, default=2, help="Quantization bits per field (default: 2)")
    p.add_argument("--fields-per-container", type=int, default=8, help="Fields packed into uint16 container (default: 8)")
    p.add_argument("--run-optuna", action="store_true", help="Run Optuna prefix feature optimization")
    p.add_argument("--optuna-trials", type=int, default=8, help="Number of Optuna trials (default: 8)")
    p.add_argument("--no-map", action="store_true", help="Disable map generation")
    p.add_argument("--map-margin-deg", type=float, default=1.5, help="Map margin in degrees (default: 1.5)")
    return p


def main() -> None:
    args = build_parser().parse_args()
    body_names = [b.strip().lower() for b in args.bodies.split(",") if b.strip()]
    catalog = {b.name: b for b in STANDARD_EXPANDED_BODIES}
    selected_bodies = [catalog[name] for name in body_names if name in catalog]
    if not selected_bodies:
        selected_bodies = STANDARD_BASE_BODIES

    cfg = PipelineRunConfig(
        run_name=args.run_name,
        output_dir=Path(args.output_dir),
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        min_magnitude=args.min_magnitude,
        start_time=args.start_time,
        stop_time=args.stop_time,
        bodies=selected_bodies,
        window_days_summary=args.window_days_summary,
        bits_per_field=args.bits_per_field,
        fields_per_container=args.fields_per_container,
        run_optuna=args.run_optuna,
        optuna_trials=args.optuna_trials,
        generate_map=not args.no_map,
        map_margin_deg=args.map_margin_deg,
    )
    summary = execute_pipeline(cfg)
    print(f"\nPipeline Run '{summary.run_name}' Finished Successfully!")
    print(f"Output Directory: {args.output_dir}")
    print(f"Master Uncompressed: {summary.raw_master_path} ({summary.raw_size_bytes:,} bytes)")
    print(f"Master 16-Bit Packed: {summary.packed_16bit_master_path} ({summary.packed_size_bytes:,} bytes, {summary.size_reduction_pct}% reduction)")


if __name__ == "__main__":
    main()

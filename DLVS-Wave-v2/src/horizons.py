"""Modulo 2: NASA JPL Horizons Parallel & Fault-Tolerant Ephemerides Fetcher.

Provides topocentric and geocentric ephemeris fetching for celestial bodies.
Features:
  - Multi-threaded parallel downloading via ThreadPoolExecutor with pacing and retries.
  - Fault tolerance: Failed or timed-out bodies do not crash the pipeline.
  - Comprehensive error & audit reporting in JSON and logs.
  - Standardized hierarchical naming: astro_<body_name>_<metric>.
"""
from __future__ import annotations
import argparse

import concurrent.futures
import json
import logging
import math
import random
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from astroquery.jplhorizons import Horizons, conf

from naming import build_field_name

logger = logging.getLogger("dlvs_wave.horizons")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass(frozen=True)
class BodyTarget:
    name: str
    command: str
    body_type: str = "planet"
    id_type: str | None = None
    is_optional: bool = False


STANDARD_BASE_BODIES: list[BodyTarget] = [
    BodyTarget(name="sun", command="10", body_type="star"),
    BodyTarget(name="moon", command="301", body_type="moon"),
    BodyTarget(name="mercury", command="199", body_type="planet"),
    BodyTarget(name="venus", command="299", body_type="planet"),
    BodyTarget(name="mars", command="499", body_type="planet"),
    BodyTarget(name="jupiter", command="599", body_type="planet"),
    BodyTarget(name="saturn", command="699", body_type="planet"),
]

STANDARD_EXPANDED_BODIES: list[BodyTarget] = [
    *STANDARD_BASE_BODIES,
    BodyTarget(name="uranus", command="799", body_type="planet"),
    BodyTarget(name="neptune", command="899", body_type="planet"),
    BodyTarget(name="ceres", command="1", body_type="asteroid", id_type="smallbody"),
    BodyTarget(name="pallas", command="2", body_type="asteroid", id_type="smallbody"),
    BodyTarget(name="vesta", command="4", body_type="asteroid", id_type="smallbody"),
]


@dataclass
class HorizonsObserverConfig:
    start_time: str
    stop_time: str
    step_size: str = "1d"
    observer_type: str = "topocentric"  # "topocentric" or "geocentric"
    lat: float = 0.0
    lon: float = 0.0
    elevation_km: float = 0.0
    quantities: str = "1,2,4,9,14,19,20,23,24,25"
    max_workers: int = 3
    timeout_seconds: int = 120
    max_retries: int = 3
    retry_delay_seconds: float = 2.0


@dataclass
class BodyFetchResult:
    body_name: str
    command: str
    success: bool
    row_count: int = 0
    column_count: int = 0
    columns: list[str] = field(default_factory=list)
    error_message: str | None = None
    elapsed_seconds: float = 0.0


@dataclass
class HorizonsExecutionReport:
    timestamp_utc: str
    total_bodies_requested: int
    successful_bodies: list[str]
    failed_bodies: list[str]
    body_results: dict[str, Any]
    total_elapsed_seconds: float
    output_columns: list[str]


class HorizonsFetcher:
    """Parallel, fault-tolerant manager for JPL Horizons ephemerides."""

    def __init__(self, config: HorizonsObserverConfig) -> None:
        self.config = config
        # Configure astroquery timeout
        conf.timeout = self.config.timeout_seconds

    def _get_location_param(self) -> dict[str, float] | str:
        if self.config.observer_type.lower() == "topocentric":
            return {
                "lon": float(self.config.lon),
                "lat": float(self.config.lat),
                "elevation": float(self.config.elevation_km),
            }
        return "500@399"

    def _parse_horizons_table(self, table: Any, body: BodyTarget) -> pd.DataFrame:
        """Extracts and standardizes numeric columns according to naming convention."""
        df_raw = table.to_pandas()
        
        # Determine date / time column
        if "datetime_str" in df_raw.columns:
            date_series = df_raw["datetime_str"].astype(str).str.strip()
            try:
                dates = pd.to_datetime(date_series, errors="coerce").dt.strftime("%Y-%m-%d")
            except Exception:
                dates = date_series.str.slice(0, 10)
        else:
            dates = [f"day_{i}" for i in range(len(df_raw))]

        out_df = pd.DataFrame({"date": dates})

        mapping = {
            "RA": "ra_icrf",
            "DEC": "dec_icrf",
            "RA_app": "ra_app",
            "DEC_app": "dec_app",
            "AZ": "azim",
            "EL": "elev",
            "V": "app_mag",
            "surfbright": "surf_bright",
            "delta": "dist",
            "delta_rate": "dist_rate",
            "r": "helio_dist",
            "r_rate": "helio_dist_rate",
            "alpha": "phase_angle",
            "elong": "elong",
            "lunar_illum": "illum_frac",
            "illum_frac": "illum_frac",
            "GlxLon": "gal_lon",
            "GlxLat": "gal_lat",
        }

        for raw_col, metric_name in mapping.items():
            if raw_col in df_raw.columns:
                std_col = build_field_name("astro", body.name, metric_name)
                val = pd.to_numeric(df_raw[raw_col], errors="coerce")
                if val.notna().any():
                    out_df[std_col] = val.astype(float)

        # Derived eclipse flag if present
        if "elongFlag" in df_raw.columns:
            std_col = build_field_name("astro", body.name, "eclipse_flag")
            flag_val = df_raw["elongFlag"].astype(str).str.strip()
            out_df[std_col] = flag_val.isin(["/", "*", "d", "c"]).astype(float)

        return out_df

    def fetch_single_body(self, body: BodyTarget) -> tuple[pd.DataFrame | None, BodyFetchResult]:
        """Fetches single celestial body with retry mechanism and error handling."""
        start_t = time.time()
        location = self._get_location_param()
        epochs = {
            "start": self.config.start_time,
            "stop": self.config.stop_time,
            "step": self.config.step_size,
        }

        last_error = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                time.sleep(random.uniform(0.1, 0.4))
                kwargs = {
                    "id": body.command,
                    "location": location,
                    "epochs": epochs,
                }
                if body.id_type:
                    kwargs["id_type"] = body.id_type
                
                obj = Horizons(**kwargs)
                table = obj.ephemerides(quantities=self.config.quantities, cache=False)
                df_body = self._parse_horizons_table(table, body)
                
                elapsed = time.time() - start_t
                res = BodyFetchResult(
                    body_name=body.name,
                    command=body.command,
                    success=True,
                    row_count=len(df_body),
                    column_count=len(df_body.columns) - 1,
                    columns=[c for c in df_body.columns if c != "date"],
                    elapsed_seconds=round(elapsed, 3),
                )
                logger.info(f"Successfully fetched {body.name} ({len(df_body)} rows, {res.column_count} fields) in {elapsed:.2f}s")
                return df_body, res
            except Exception as exc:
                last_error = exc
                logger.warning(f"Attempt {attempt}/{self.config.max_retries} failed for {body.name}: {exc}")
                if attempt < self.config.max_retries:
                    backoff = self.config.retry_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                    time.sleep(backoff)

        elapsed = time.time() - start_t
        err_msg = str(last_error) if last_error else "Unknown error"
        res = BodyFetchResult(
            body_name=body.name,
            command=body.command,
            success=False,
            error_message=err_msg,
            elapsed_seconds=round(elapsed, 3),
        )
        logger.error(f"Horizons fetch failed for {body.name} ({body.command}) after {elapsed:.2f}s: {err_msg}")
        return None, res

    def fetch_all(
        self,
        bodies: Sequence[BodyTarget] = STANDARD_BASE_BODIES,
    ) -> tuple[pd.DataFrame, HorizonsExecutionReport]:
        """Fetches multiple celestial bodies concurrently and merges on date."""
        start_all = time.time()
        logger.info(f"Starting parallel fetch for {len(bodies)} bodies with max_workers={self.config.max_workers}")

        results: dict[str, BodyFetchResult] = {}
        dataframes: dict[str, pd.DataFrame] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_body = {}
            for idx, body in enumerate(bodies):
                time.sleep(0.15)
                future = executor.submit(self.fetch_single_body, body)
                future_to_body[future] = body

            for future in concurrent.futures.as_completed(future_to_body):
                body = future_to_body[future]
                try:
                    df_b, res = future.result()
                    results[body.name] = res
                    if df_b is not None:
                        dataframes[body.name] = df_b
                except Exception as exc:
                    results[body.name] = BodyFetchResult(
                        body_name=body.name,
                        command=body.command,
                        success=False,
                        error_message=f"Thread execution error: {exc}",
                    )

        # Merge successful dataframes on date
        merged_df = pd.DataFrame()
        for b_name, df_b in dataframes.items():
            if merged_df.empty:
                merged_df = df_b.copy()
            else:
                cols_to_use = [c for c in df_b.columns if c not in merged_df.columns or c == "date"]
                merged_df = pd.merge(merged_df, df_b[cols_to_use], on="date", how="outer")

        if not merged_df.empty:
            merged_df.sort_values(by="date", inplace=True)
            merged_df.reset_index(drop=True, inplace=True)

        successful = [name for name, r in results.items() if r.success]
        failed = [name for name, r in results.items() if not r.success]
        total_elapsed = round(time.time() - start_all, 3)

        report = HorizonsExecutionReport(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            total_bodies_requested=len(bodies),
            successful_bodies=successful,
            failed_bodies=failed,
            body_results={k: asdict(v) for k, v in results.items()},
            total_elapsed_seconds=total_elapsed,
            output_columns=list(merged_df.columns),
        )

        return merged_df, report

    def save_report(self, report: HorizonsExecutionReport, output_path: str | Path) -> Path:
        """Saves JSON execution report."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NASA JPL Horizons Ephemerides Fetcher CLI for DLVS-Wave v2.0")
    p.add_argument("--start-time", required=True, help="Start date/epoch (e.g. 1900-01-01)")
    p.add_argument("--stop-time", required=True, help="Stop date/epoch (e.g. 2030-12-31)")
    p.add_argument("--step-size", default="1d", help="Ephemeris step size (default: 1d)")
    p.add_argument("--observer-type", choices=("topocentric", "geocentric"), default="topocentric")
    p.add_argument("--lat", type=float, default=0.0, help="Observer latitude (deg N)")
    p.add_argument("--lon", type=float, default=0.0, help="Observer longitude (deg E)")
    p.add_argument("--elevation-km", type=float, default=0.0, help="Observer elevation in km")
    p.add_argument("--bodies", default="sun,moon,mercury,venus,mars,jupiter,saturn", help="Comma-separated list of body names")
    p.add_argument("--max-workers", type=int, default=3, help="Max parallel worker threads")
    p.add_argument("--timeout-seconds", type=int, default=120, help="Per-request timeout in seconds")
    p.add_argument("--output-csv", required=True, help="Path to save merged ephemerides CSV")
    p.add_argument("--output-report", default=None, help="Path to save Horizons JSON audit report")
    return p


def main() -> None:
    args = build_parser().parse_args()
    body_names = [b.strip().lower() for b in args.bodies.split(",") if b.strip()]
    catalog = {b.name: b for b in STANDARD_EXPANDED_BODIES}
    selected_bodies = [catalog[name] for name in body_names if name in catalog]
    if not selected_bodies:
        selected_bodies = STANDARD_BASE_BODIES

    cfg = HorizonsObserverConfig(
        start_time=args.start_time,
        stop_time=args.stop_time,
        step_size=args.step_size,
        observer_type=args.observer_type,
        lat=args.lat,
        lon=args.lon,
        elevation_km=args.elevation_km,
        max_workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
    )
    fetcher = HorizonsFetcher(cfg)
    df_astro, report = fetcher.fetch_all(bodies=selected_bodies)
    
    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_astro.to_csv(out_csv, index=False)
    print(f"Fetched {len(df_astro)} days across {len(df_astro.columns)} columns. Saved to: {out_csv}")

    if args.output_report:
        fetcher.save_report(report, args.output_report)
        print(f"Execution report saved to: {args.output_report}")


if __name__ == "__main__":
    main()

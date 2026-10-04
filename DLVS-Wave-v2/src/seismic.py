"""Modulo 1: Seismic Event Extraction Engine for DLVS-Wave v2.0.

Extracts seismic events within a spatial bounding box and magnitude threshold.
Strictly outputs canonical seismic core columns:
  - time, date
  - seis_core_id
  - seis_core_latitude
  - seis_core_longitude
  - seis_core_depth
  - seis_core_magnitude
  - seis_core_place (optional/metadata)
"""
from __future__ import annotations

import argparse
import csv
import io
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests

from naming import SEISMIC_CORE_FIELDS

USGS_FDSN_URL = "https://earthquake.usgov/fdsnws/event/1/query" if False else "https://earthquake.usgs.gov/fdsnws/event/1/query"


@dataclass
class SeismicQueryConfig:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    min_magnitude: float = 0.0
    start_time: str | None = None
    end_time: str | None = None
    source_csv: str | Path | None = None
    timeout_seconds: int = 30


class SeismicExtractor:
    """Extracts earthquake events from USGS FDSN service or local catalog files."""

    def __init__(self, config: SeismicQueryConfig) -> None:
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if self.config.min_lat > self.config.max_lat:
            raise ValueError(f"min_lat ({self.config.min_lat}) > max_lat ({self.config.max_lat})")
        if self.config.min_lon > self.config.max_lon:
            raise ValueError(f"min_lon ({self.config.min_lon}) > max_lon ({self.config.max_lon})")

    def fetch_from_usgs(self) -> pd.DataFrame:
        """Queries USGS FDSN Web API and returns raw dataframe."""
        params = {
            "format": "csv",
            "minlatitude": self.config.min_lat,
            "maxlatitude": self.config.max_lat,
            "minlongitude": self.config.min_lon,
            "maxlongitude": self.config.max_lon,
            "minmagnitude": self.config.min_magnitude,
            "orderby": "time-asc",
        }
        if self.config.start_time:
            params["starttime"] = self.config.start_time
        if self.config.end_time:
            params["endtime"] = self.config.end_time

        resp = requests.get(USGS_FDSN_URL, params=params, timeout=self.config.timeout_seconds)
        if resp.status_code == 204 or len(resp.text.strip()) == 0:
            return pd.DataFrame(columns=["time", "latitude", "longitude", "depth", "mag", "id", "place"])
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text))
        return df

    def fetch_from_local_csv(self, path: Path | str) -> pd.DataFrame:
        """Reads seismic events from local CSV and normalizes column headers."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Local seismic file not found: {p}")
        df = pd.read_csv(p)
        return df

    def extract(self) -> pd.DataFrame:
        """Extracts and filters seismic events, returning standardized DataFrame."""
        if self.config.source_csv:
            df_raw = self.fetch_from_local_csv(self.config.source_csv)
        else:
            df_raw = self.fetch_from_usgs()

        if df_raw.empty:
            return pd.DataFrame(columns=["date", "time", *SEISMIC_CORE_FIELDS, "seis_core_place"])

        col_map: dict[str, str] = {}
        for c in df_raw.columns:
            cl = c.strip().lower()
            if cl in ("time", "date", "datetime", "timestamp", "origintime"):
                col_map["time"] = c
            elif cl in ("lat", "latitude"):
                col_map["latitude"] = c
            elif cl in ("lon", "longitude", "lng"):
                col_map["longitude"] = c
            elif cl in ("depth", "depth_km", "depthkm"):
                col_map["depth"] = c
            elif cl in ("mag", "magnitude", "mw", "ml", "ms"):
                col_map["mag"] = c
            elif cl in ("id", "eventid", "event_id"):
                col_map["id"] = c
            elif cl in ("place", "location", "region", "seis_core_place"):
                col_map["place"] = c

        time_col = col_map.get("time", "time")
        lat_col = col_map.get("latitude", "latitude")
        lon_col = col_map.get("longitude", "longitude")
        depth_col = col_map.get("depth", "depth")
        mag_col = col_map.get("mag", "mag")
        id_col = col_map.get("id", "id") if "id" in col_map else None
        place_col = col_map.get("place", None)

        records = []
        for idx, row in df_raw.iterrows():
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
                depth = float(row[depth_col])
                mag = float(row[mag_col])
            except (ValueError, TypeError, KeyError):
                continue

            if not (math.isfinite(lat) and math.isfinite(lon) and math.isfinite(depth) and math.isfinite(mag)):
                continue

            if not (self.config.min_lat <= lat <= self.config.max_lat):
                continue
            if not (self.config.min_lon <= lon <= self.config.max_lon):
                continue
            if mag < self.config.min_magnitude:
                continue

            raw_time_str = str(row[time_col]).strip() if time_col in row else ""
            try:
                dt = pd.to_datetime(raw_time_str, utc=True)
                time_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                time_iso = raw_time_str
                date_str = raw_time_str[:10] if len(raw_time_str) >= 10 else raw_time_str

            event_id = str(row[id_col]) if id_col and id_col in row and pd.notna(row[id_col]) else f"ev_{idx}"
            place_str = str(row[place_col]).strip() if place_col and place_col in row and pd.notna(row[place_col]) else ""

            records.append({
                "date": date_str,
                "time": time_iso,
                "seis_core_id": event_id,
                "seis_core_latitude": lat,
                "seis_core_longitude": lon,
                "seis_core_depth": depth,
                "seis_core_magnitude": mag,
                "seis_core_place": place_str,
            })

        df_out = pd.DataFrame(records)
        if not df_out.empty:
            df_out.sort_values(by=["date", "time"], inplace=True)
            df_out.reset_index(drop=True, inplace=True)
        else:
            df_out = pd.DataFrame(columns=["date", "time", *SEISMIC_CORE_FIELDS, "seis_core_place"])
        return df_out

    def save(self, df: pd.DataFrame, output_path: str | Path, output_format: Literal["csv", "excel"] = "csv") -> Path:
        """Saves the extracted seismic dataframe to CSV or Excel."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if output_format.lower() == "excel" or out.suffix.lower() in (".xlsx", ".xls"):
            df.to_excel(out, index=False)
        else:
            df.to_csv(out, index=False)
        return out


def extract_seismic_events(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    min_magnitude: float = 0.0,
    start_time: str | None = None,
    end_time: str | None = None,
    source_csv: str | Path | None = None,
    output_path: str | Path | None = None,
    output_format: Literal["csv", "excel"] = "csv",
) -> tuple[pd.DataFrame, Path | None]:
    config = SeismicQueryConfig(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        min_magnitude=min_magnitude,
        start_time=start_time,
        end_time=end_time,
        source_csv=source_csv,
    )
    extractor = SeismicExtractor(config)
    df = extractor.extract()
    saved_path = None
    if output_path:
        saved_path = extractor.save(df, output_path, output_format=output_format)
    return df, saved_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Seismic Event Extraction CLI for DLVS-Wave v2.0")
    p.add_argument("--min-lat", type=float, required=True, help="Minimum latitude")
    p.add_argument("--max-lat", type=float, required=True, help="Maximum latitude")
    p.add_argument("--min-lon", type=float, required=True, help="Minimum longitude")
    p.add_argument("--max-lon", type=float, required=True, help="Maximum longitude")
    p.add_argument("--min-magnitude", type=float, default=0.0, help="Magnitude threshold floor (default: 0.0)")
    p.add_argument("--start-time", default=None, help="Start date/time (e.g. 1900-01-01)")
    p.add_argument("--end-time", default=None, help="End date/time (e.g. 2030-12-31)")
    p.add_argument("--source-csv", default=None, help="Optional local catalog CSV path")
    p.add_argument("--output-csv", required=True, help="Output CSV path for seismic events")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df, saved = extract_seismic_events(
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        min_magnitude=args.min_magnitude,
        start_time=args.start_time,
        end_time=args.end_time,
        source_csv=args.source_csv,
        output_path=args.output_csv,
    )
    print(f"Extracted {len(df)} seismic records. Saved to: {saved}")


if __name__ == "__main__":
    main()

"""Modulo 3: Temporal Resampling, Scale Aggregation, Safety Locks & Peak Seismic Coupling for DLVS-Wave v2.0.

Provides:
  - Multi-scale window summarization (e.g. 7d, 30d, 90d, 180d).
  - Four canonical statistical aggregations for continuous astronomical features: min, max, mean, median.
  - Physical Peak Seismic Coupling:
      * For any time slot/window, identifies the maximum magnitude peak earthquake.
      * Transports the exact, untouched original 3D coordinates (latitude, longitude, depth) and magnitude
        of that peak earthquake together into the window record (never averaged or leveled).
      * Windows with zero seismic activity receive strictly 0.0 across all seismic dimensions.
  - Dynamic Scale-Inherited Shift Re-calculation (Modulo 9 integration).
  - Canonical Front-Positioning: date -> all seis_* features -> astro_* features.
  - Safety Lock Anti-Resampling Binario: raises ValueError if input contains bit-packed fields (packed_*).
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from indexing import HistoricalShiftEngine, ShiftParameters
from naming import INDEX_FIELDS, build_field_name, parse_field_name, reorder_master_dataframe

logger = logging.getLogger("dlvs_wave.resampling")


@dataclass
class ResamplingConfig:
    window_days: int = 30
    aggregations: Sequence[str] = ("min", "max", "mean", "median")
    date_col: str = "date"
    recalculate_shifts: bool = False
    shift_config_path: str | Path | None = None


class TemporalSummarizer:
    """Aggregates high-frequency daily time series into multi-day window summaries with Peak Seismic Coupling."""

    def __init__(self, config: ResamplingConfig | None = None) -> None:
        self.config = config or ResamplingConfig()

    def _check_safety_lock(self, df: pd.DataFrame) -> None:
        """Enforces Safety Lock: prevents binary packed columns from being resampled."""
        packed_cols = [c for c in df.columns if c.startswith("packed_")]
        if packed_cols:
            raise ValueError(
                f"SAFETY LOCK ACTIVATED: Attempted to resample a DataFrame containing {len(packed_cols)} bit-packed integer containers "
                f"({packed_cols[:3]}...). Temporal resampling (min, max, mean, median) must ONLY be run on uncompressed raw decimal datasets! "
                "Resampling quantized bitfields produces mathematically corrupted features."
            )

    def summarize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executes windowed temporal summarization with scale inheritance and Physical Peak Seismic Coupling."""
        if df.empty:
            raise ValueError("Input DataFrame is empty.")

        self._check_safety_lock(df)

        if self.config.date_col not in df.columns:
            raise ValueError(f"Date column '{self.config.date_col}' missing from DataFrame.")

        df_work = df.copy()
        df_work[self.config.date_col] = pd.to_datetime(df_work[self.config.date_col])
        df_work.sort_values(by=self.config.date_col, inplace=True)
        df_work.set_index(self.config.date_col, inplace=True)

        freq_str = f"{self.config.window_days}D"
        grouper = pd.Grouper(freq=freq_str)

        # 1. Separate Continuous Astro Features from Discrete Seismic Features
        astro_cols = [
            c for c in df_work.columns
            if c.startswith("astro_") and "_shift_" not in c and pd.api.types.is_numeric_dtype(df_work[c])
        ]
        seis_core_cols = [
            c for c in ("seis_core_magnitude", "seis_core_latitude", "seis_core_longitude", "seis_core_depth")
            if c in df_work.columns
        ]
        # Binary study metadata are discrete flags.  They are transported with
        # a weekly maximum and are never averaged into an artificial value.
        seis_indicator_cols = [
            c for c in df_work.columns
            if c.startswith("seis_")
            and c not in seis_core_cols
            and "_shift_" not in c
            and pd.api.types.is_numeric_dtype(df_work[c])
        ]

        # 2. Continuous Astro Aggregations (min, max, mean, median)
        astro_dfs = []
        if astro_cols:
            for agg in self.config.aggregations:
                s = df_work.groupby(grouper)[astro_cols].agg(agg)
                renamed_cols = []
                for col in astro_cols:
                    parsed = parse_field_name(col)
                    if parsed:
                        renamed_cols.append(build_field_name(
                            prefix=parsed.prefix,
                            group_or_body=parsed.group_or_body,
                            metric=parsed.metric,
                            aggregation=agg,
                        ))
                    else:
                        renamed_cols.append(f"{col}_{agg}")
                s.columns = renamed_cols
                astro_dfs.append(s)
            df_astro_res = pd.concat(astro_dfs, axis=1)
        else:
            df_astro_res = pd.DataFrame(index=df_work.groupby(grouper).size().index)

        # 3. Physical Peak Seismic Coupling (Exact, unblended peak earthquake of each window)
        if seis_core_cols and "seis_core_magnitude" in df_work.columns:
            peak_indices = df_work.groupby(grouper)["seis_core_magnitude"].idxmax()
            df_peaks = df_work.loc[peak_indices, seis_core_cols].copy()
            df_peaks.index = df_astro_res.index

            # For windows with 0 earthquakes, zero out all seismic coordinates
            max_mags = df_work.groupby(grouper)["seis_core_magnitude"].max()
            zero_windows = max_mags[max_mags == 0.0].index
            df_peaks.loc[zero_windows, seis_core_cols] = 0.0
        else:
            df_peaks = pd.DataFrame(index=df_astro_res.index)

        if seis_indicator_cols:
            df_indicators = df_work.groupby(grouper)[seis_indicator_cols].max()
        else:
            df_indicators = pd.DataFrame(index=df_astro_res.index)

        df_resampled = pd.concat([df_peaks, df_indicators, df_astro_res], axis=1).reset_index()
        df_resampled[self.config.date_col] = df_resampled[self.config.date_col].dt.strftime("%Y-%m-%d")

        logger.info(
            f"Resampled {len(df)} daily rows into {len(df_resampled)} {self.config.window_days}-day windows "
            f"with Physical Peak Seismic Coupling ({len(df_resampled.columns) - 1} features)."
        )

        # 4. Dynamic Scale Inheritance: recalculate shifted features on resampled multi-day resolution
        if self.config.recalculate_shifts:
            if self.config.shift_config_path and Path(self.config.shift_config_path).exists():
                engine = HistoricalShiftEngine.load_schema_config(self.config.shift_config_path)
                engine.params.astro_step_days = self.config.window_days
                engine.params.seis_step_days = self.config.window_days
                engine.params.temporal_resolution = f"{self.config.window_days}d"
            else:
                params = ShiftParameters(
                    astro_step_days=self.config.window_days,
                    seis_step_days=self.config.window_days,
                    temporal_resolution=f"{self.config.window_days}d",
                )
                engine = HistoricalShiftEngine(params)

            df_resampled, _ = engine.apply_shifts(df_resampled)
            logger.info(f"Re-applied shifted features on resampled {self.config.window_days}d scale: now {len(df_resampled.columns)} cols.")

        df_resampled = reorder_master_dataframe(df_resampled)
        return df_resampled

    def save(self, df: pd.DataFrame, output_path: str | Path) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        return out


def resample_master(
    df: pd.DataFrame,
    window_days: int = 30,
    aggregations: Sequence[str] = ("min", "max", "mean", "median"),
    recalculate_shifts: bool = False,
    shift_config_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, Path | None]:
    config = ResamplingConfig(
        window_days=window_days,
        aggregations=aggregations,
        recalculate_shifts=recalculate_shifts,
        shift_config_path=shift_config_path,
    )
    summarizer = TemporalSummarizer(config)
    df_res = summarizer.summarize(df)

    saved_path = None
    if output_path:
        saved_path = summarizer.save(df_res, output_path)

    return df_res, saved_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Temporal Resampling & Scale Inheritance CLI for DLVS-Wave v2.0")
    p.add_argument("--input-csv", required=True, help="Path to input raw uncompressed CSV dataset")
    p.add_argument("--output-csv", required=True, help="Path to save resampled CSV dataset")
    p.add_argument("--window-days", type=int, default=30, help="Resampling window size in days (default: 30)")
    p.add_argument("--aggregations", nargs="+", default=["min", "max", "mean", "median"], help="List of statistical aggregations")
    p.add_argument("--recalculate-shifts", action="store_true", help="Recalculate historical/future shifts on the resampled scale")
    p.add_argument("--shift-config-path", help="Path to JSON shift schema configuration file")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df = pd.read_csv(args.input_csv)
    df_res, saved_path = resample_master(
        df=df,
        window_days=args.window_days,
        aggregations=args.aggregations,
        recalculate_shifts=args.recalculate_shifts,
        shift_config_path=args.shift_config_path,
        output_path=args.output_csv,
    )
    print(f"Resampled dataset successfully saved -> {saved_path} ({len(df)} rows -> {len(df_res)} rows, {len(df_res.columns)} features)")


if __name__ == "__main__":
    main()

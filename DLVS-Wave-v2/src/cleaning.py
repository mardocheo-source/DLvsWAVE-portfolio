"""Modulo 10: Master Sanitization, Alphanumeric Encoding & Zero-Variance Pruning Engine.

Provides:
  - Alphanumeric flag & string serialization to clean numeric floats (e.g. /L -> 1, /T -> 2, * -> 3).
  - Time-series forward-fill and gap interpolation for continuous physical features (astro_*).
  - Discrete zero-fill for point-event seismic features (seis_*) - strictly preventing artificial repeated events.
  - Zero-variance / constant column pruning (drops all uninformative flat columns).
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from naming import DEFAULT_SEISMIC_CORE_FIELDS, SEISMIC_CORE_FIELDS

logger = logging.getLogger("dlvs_wave.cleaning")

# Known astronomical flag mappings from JPL Horizons
FLAG_MAPPINGS: dict[str, float] = {
    "/l": 1.0,
    "/t": 2.0,
    "*": 3.0,
    "a": 4.0,
    "c": 5.0,
    "n": 6.0,
    "day": 1.0,
    "twilight": 2.0,
    "night": 3.0,
    "m": 1.0,
    "r": 2.0,
    "t": 3.0,
    "le": 4.0,
    "te": 5.0,
    "d": 6.0,
    "p": 9.0,
    "u": 11.0,
    "-": 0.0,
    "none": 0.0,
    "nan": 0.0,
    "": 0.0,
}

PROTECTED_CORE_COLUMNS = (
    "date",
    "time",
    *DEFAULT_SEISMIC_CORE_FIELDS,
)


@dataclass
class CleaningReport:
    original_rows: int
    original_cols: int
    encoded_string_cols: list[str]
    pruned_constant_cols: list[str]
    remaining_cols: int
    total_pruned_count: int


class MasterSanitizer:
    """Cleans, encodes alphanumeric flags, and prunes constant zero-variance columns."""

    def __init__(self, protected_cols: Sequence[str] | None = None) -> None:
        self.protected_cols = set(protected_cols or PROTECTED_CORE_COLUMNS)

    def _sanitize_string_value(self, val: Any) -> float:
        """Converts alphanumeric flags or strings to deterministic numeric float."""
        if pd.isna(val) or val is None:
            return 0.0

        if isinstance(val, (int, float, np.number)):
            return float(val) if not np.isnan(val) else 0.0

        s = str(val).strip().lower()
        if not s:
            return 0.0

        if s in FLAG_MAPPINGS:
            return FLAG_MAPPINGS[s]

        try:
            return float(s)
        except ValueError:
            pass

        return float(abs(hash(s)) % 1000 + 1)

    def sanitize_and_prune(self, df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
        """Performs full master sanitization, string encoding, and zero-variance pruning."""
        if df.empty:
            return df.copy(), CleaningReport(0, 0, [], [], 0, 0)

        df_work = df.copy()
        orig_rows, orig_cols = df_work.shape

        encoded_cols = []
        # 1. Alphanumeric & String Encoding
        for col in df_work.columns:
            if col in ("date", "time"):
                continue

            if df_work[col].dtype == object or not pd.api.types.is_numeric_dtype(df_work[col]):
                df_work[col] = df_work[col].apply(self._sanitize_string_value).astype(float)
                encoded_cols.append(col)

        # 2. Impute NaNs with strict domain separation:
        # - Seismic features are discrete events: missing days are strictly 0.0 (NO EVENT). NEVER ffill!
        # - Astro features are continuous physical time-series: ffill -> bfill -> 0.0.
        for col in df_work.columns:
            if col in ("date", "time"):
                continue

            if pd.api.types.is_numeric_dtype(df_work[col]):
                if col.startswith("seis_"):
                    df_work[col] = df_work[col].fillna(0.0)
                else:
                    df_work[col] = df_work[col].ffill().bfill().fillna(0.0)

        # 3. Prune Constant / Zero-Variance Columns
        pruned_cols = []
        cols_to_keep = []

        for col in df_work.columns:
            if col in self.protected_cols:
                cols_to_keep.append(col)
                continue

            unique_count = df_work[col].nunique(dropna=False)
            if unique_count <= 1:
                pruned_cols.append(col)
            else:
                if pd.api.types.is_numeric_dtype(df_work[col]):
                    std_val = float(df_work[col].std(ddof=0))
                    if std_val < 1e-12:
                        pruned_cols.append(col)
                        continue
                cols_to_keep.append(col)

        df_clean = df_work[cols_to_keep].copy()

        report = CleaningReport(
            original_rows=orig_rows,
            original_cols=orig_cols,
            encoded_string_cols=encoded_cols,
            pruned_constant_cols=pruned_cols,
            remaining_cols=len(df_clean.columns),
            total_pruned_count=len(pruned_cols),
        )

        logger.info(
            f"Master Sanitizer: Processed {orig_cols} cols -> Pruned {len(pruned_cols)} zero-variance cols "
            f"({len(encoded_cols)} string cols encoded). Clean Master has {len(df_clean.columns)} cols."
        )
        return df_clean, report


def sanitize_master(
    df: pd.DataFrame,
    protected_cols: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    sanitizer = MasterSanitizer(protected_cols)
    df_clean, report = sanitizer.sanitize_and_prune(df)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(out, index=False)
    return df_clean, report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Master Sanitization & Zero-Variance Pruning CLI for DLVS-Wave v2.0")
    p.add_argument("--input-csv", required=True, help="Path to input master CSV dataset")
    p.add_argument("--output-csv", required=True, help="Path to save sanitized and pruned master CSV")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df = pd.read_csv(args.input_csv)
    df_clean, rep = sanitize_master(df, output_path=args.output_csv)
    print(f"Master Sanitized: {rep.original_cols} -> {rep.remaining_cols} cols (Pruned {rep.total_pruned_count} constant cols).")


if __name__ == "__main__":
    main()

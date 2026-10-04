"""Modulo 9: Historical & Future Shift Indexing and Anti-Data-Leakage Engine for DLVS-Wave v2.0.

Provides:
  - Generation of horizontal time-shifted twin features (_shift_m* and _shift_p*).
  - Strict enforcement of Causal Anti-Data-Leakage protocol:
      * Astro fields allow both past and future shifts (deterministic celestial mechanics).
      * Seismic fields strictly restrict predictive features to past shifts (Δt <= 0).
  - Zero-fill for discrete seismic shift gaps (no artificial repeated events).
  - Generation of companion Markdown Anti-Data-Leakage audit reports.
  - JSON schema configuration export/loading for multi-scale inheritance.
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from naming import build_field_name, parse_field_name

logger = logging.getLogger("dlvs_wave.indexing")


@dataclass
class ShiftParameters:
    # Astro parameters (Past & Future shifts allowed)
    astro_min_step: int = -5
    astro_max_step: int = 5
    astro_step_days: int = 7

    # Seismic parameters (Past shifts strictly allowed, future strictly prohibited unless retroactive target)
    seis_min_step: int = -5
    seis_max_step: int = 0
    seis_step_days: int = 7

    allow_future_seismic: bool = False
    temporal_resolution: str = "1d"  # "1d", "7d", "30d"


class HistoricalShiftEngine:
    """Generates time-shifted features while enforcing causal anti-data-leakage constraints."""

    def __init__(self, params: ShiftParameters | None = None) -> None:
        self.params = params or ShiftParameters()

    def _calculate_offsets(self, min_step: int, max_step: int, step_days: int) -> list[int]:
        """Computes list of integer day offsets."""
        return [step * step_days for step in range(min_step, max_step + 1) if step != 0]

    @staticmethod
    def _infer_cadence_days(date_values: pd.Series) -> int | None:
        """Return the exact regular row cadence, expressed in calendar days."""
        parsed = pd.to_datetime(date_values, errors="coerce")
        if parsed.isna().any() or parsed.duplicated().any() or len(parsed) < 2:
            return None
        deltas = parsed.sort_values().diff().dropna().dt.days
        if deltas.empty or deltas.nunique() != 1 or int(deltas.iloc[0]) <= 0:
            return None
        return int(deltas.iloc[0])

    @staticmethod
    def _shift_by_calendar_days(
        values: pd.Series,
        dates: pd.Series,
        offset_days: int,
        cadence_days: int | None,
    ) -> pd.Series:
        """Align ``values(t + offset_days)`` to each target date ``t``.

        The old row-based implementation was only correct for a daily grid.
        For example, a 91-day offset on a weekly master is 13 rows, not 91.
        """
        if cadence_days and offset_days % cadence_days == 0:
            return values.shift(-int(offset_days // cadence_days))

        parsed = pd.to_datetime(dates, errors="coerce")
        if parsed.isna().any() or parsed.duplicated().any():
            raise ValueError("Calendar shift indexing requires unique, valid dates")
        lookup = pd.Series(values.to_numpy(), index=parsed)
        requested = parsed + pd.to_timedelta(int(offset_days), unit="D")
        return pd.Series(lookup.reindex(requested).to_numpy(), index=values.index)

    def apply_shifts(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Applies horizontal historical/future shifts with strict domain-separated gap handling."""
        if df.empty:
            return df.copy(), {}

        if "date" not in df.columns:
            raise ValueError("Input DataFrame must have a 'date' column for shift indexing.")

        cadence_days = self._infer_cadence_days(df["date"])

        astro_offsets = self._calculate_offsets(
            self.params.astro_min_step, self.params.astro_max_step, self.params.astro_step_days
        )
        seis_offsets = self._calculate_offsets(
            self.params.seis_min_step, self.params.seis_max_step, self.params.seis_step_days
        )

        astro_base_cols = [c for c in df.columns if c.startswith("astro_") and "_shift_" not in c]
        seis_base_cols = [
            c for c in df.columns 
            if c.startswith("seis_") and c in ("seis_core_magnitude", "seis_core_depth", "seis_core_magnitude_max", "seis_core_magnitude_mean")
        ]

        new_features: dict[str, pd.Series] = {}
        generated_astro_shifts = 0
        generated_seis_shifts = 0
        future_seis_count = 0

        # 1. Generate Astronomical Shifts (Past + Future)
        for offset_days in astro_offsets:
            dir_tag = "p" if offset_days > 0 else "m"
            tag = f"_shift_{dir_tag}{abs(offset_days)}d"

            for col in astro_base_cols:
                new_col = f"{col}{tag}"
                new_features[new_col] = self._shift_by_calendar_days(
                    df[col], df["date"], offset_days, cadence_days
                )
                generated_astro_shifts += 1

        # 2. Generate Seismic Shifts (Past strictly, unless future explicitly allowed)
        for offset_days in seis_offsets:
            if offset_days > 0 and not self.params.allow_future_seismic:
                logger.warning(f"Anti-Leakage Block: Skipping future seismic shift (+{offset_days}d)")
                continue

            dir_tag = "p" if offset_days > 0 else "m"
            tag = f"_shift_{dir_tag}{abs(offset_days)}d"

            if offset_days > 0:
                future_seis_count += 1

            for col in seis_base_cols:
                new_col = f"{col}{tag}"
                # Gaps from shift are filled with 0.0 (no earthquake occurred)
                new_features[new_col] = self._shift_by_calendar_days(
                    df[col], df["date"], offset_days, cadence_days
                ).fillna(0.0)
                generated_seis_shifts += 1

        if new_features:
            df_new = pd.DataFrame(new_features, index=df.index)
            df_out = pd.concat([df, df_new], axis=1)
        else:
            df_out = df

        audit_meta = {
            "total_original_columns": len(df.columns),
            "total_output_columns": len(df_out.columns),
            "generated_astro_shifts": generated_astro_shifts,
            "generated_seismic_shifts": generated_seis_shifts,
            "future_seismic_shifts_count": future_seis_count,
            "astro_day_offsets": astro_offsets,
            "seismic_day_offsets": seis_offsets,
            "inferred_row_cadence_days": cadence_days,
            "astro_row_offsets": [
                int(value // cadence_days) if cadence_days and value % cadence_days == 0 else None
                for value in astro_offsets
            ],
            "seismic_row_offsets": [
                int(value // cadence_days) if cadence_days and value % cadence_days == 0 else None
                for value in seis_offsets
            ],
            "anti_leakage_status": "PASSED (Zero Future Seismic Leakage)" if future_seis_count == 0 else "WARNING (Future Seismic Included)",
            "allow_future_seismic": self.params.allow_future_seismic,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Shift Engine: Generated {generated_astro_shifts} astro shifts + {generated_seis_shifts} seismic shifts. "
            f"Anti-Leakage: {audit_meta['anti_leakage_status']}"
        )
        return df_out, audit_meta

    def generate_anti_leakage_audit_report(self, audit_meta: dict[str, Any], output_path: str | Path) -> Path:
        """Generates Markdown Anti-Data-Leakage Audit Manifest."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Master Dataset Anti-Data-Leakage & Causal Indexing Audit",
            "",
            f"**Audit Status**: `{audit_meta.get('anti_leakage_status', 'N/A')}`  ",
            f"**Execution Timestamp**: `{audit_meta.get('timestamp_utc', 'N/A')}`",
            "",
            "---",
            "",
            "## 1. Executive Summary & Compliance Verdict",
            "",
            f"- **Original Feature Columns**: `{audit_meta.get('total_original_columns', 0)}`",
            f"- **Final Master Columns**: `{audit_meta.get('total_output_columns', 0)}`",
            f"- **Astronomical Shift Features Generated**: `{audit_meta.get('generated_astro_shifts', 0)}` (Past & Future Leads)",
            f"- **Seismic Shift Features Generated**: `{audit_meta.get('generated_seismic_shifts', 0)}` (Historical Lags strictly)",
            f"- **Future Seismic Features Blocked/Allowed**: `{audit_meta.get('future_seismic_shifts_count', 0)}`",
            "",
            "> [!IMPORTANT]",
            "> **Causal Anti-Data-Leakage Protocol**: In predictive time series forecasting, future celestial configurations ($+N\\text{d}$) are deterministic and physically valid. Future seismic events ($+N\\text{d}$) are strictly non-causal and would constitute data leakage.",
            "",
            "---",
            "",
            "## 2. Shift Offsets Matrix",
            "",
            f"- **Astronomical Offsets (days)**: `{audit_meta.get('astro_day_offsets', [])}`",
            f"- **Seismic Offsets (days)**: `{audit_meta.get('seismic_day_offsets', [])}`",
            f"- **Inferred Row Cadence (days)**: `{audit_meta.get('inferred_row_cadence_days')}`",
            f"- **Astronomical Offsets (rows)**: `{audit_meta.get('astro_row_offsets', [])}`",
            f"- **Seismic Offsets (rows)**: `{audit_meta.get('seismic_row_offsets', [])}`",
            "",
            "---",
            "*Report automatically generated by DLVS-Wave v2.0 Historical Shift Engine (Modulo 9).*",
        ]

        with out.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return out

    def save_schema_config(self, output_path: str | Path) -> Path:
        """Exports shift hyperparameter configuration for multi-scale inheritance."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(asdict(self.params), f, indent=2)
        return out

    @classmethod
    def load_schema_config(cls, path: str | Path) -> HistoricalShiftEngine:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        params = ShiftParameters(**data)
        return cls(params)

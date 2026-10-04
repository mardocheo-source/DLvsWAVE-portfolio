"""Modulo 12: Master Pretreatment Engine & Pi-Zipper Sub-Sampling for DLVS-Wave v2.0.

Provides:
  1. Modality Target Isolation:
      - 'energetic': Targets seis_core_magnitude (or energy metric), stripping all other seismic dimensions.
      - 'location': Targets seis_core_latitude, longitude, depth, or discrete zone_id, stripping other seismic fields.
  2. Automated Date Balancing (eval_min_events..eval_max_events):
      - Intelligently balances train_start_date/end_date and eval_start_date/end_date to capture exactly between
        eval_min_events (default 3) and eval_max_events (default 5) major events (M >= min_magnitude_threshold).
  3. Peak Event Context Corridors [t - window_before, t + window_after] around events >= min_magnitude_threshold (100% kept).
  4. Pi-Zipper Continuous Stepping Formula in Millesimi (/ 1000.0) ("Cerniera di Pi"):
      - Traverses the chronological sequence of in-between background gaps like a continuous zipper.
      - The stepping stride across calm periods is modulated deterministically by the 3-digit millesimi triplets of Pi.
  5. Evaluation Window Corridor Mode ("corridors" vs "continuous"):
      - Slices evaluation timeline into focused windows around the key validation events (span = max(window_before, window_after)).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.base import ModelMetrics
from models.engine import ForecastingEngine, ModelType

logger = logging.getLogger("dlvs_wave.pretreatment")

# 100 consecutive 3-digit triplets in millesimi from fractional expansion of Pi (3.141592653589793...)
PI_DIGIT_TRIPLETS: tuple[int, ...] = (
    141, 592, 653, 589, 793, 238, 462, 643, 383, 279,
    502, 884, 197, 169, 399, 375, 105, 820, 974, 944,
    592, 307, 816, 406, 286, 208, 998, 628,  34, 825,
    342, 117,  67, 982, 148,  86, 513, 282, 306, 647,
     93, 844, 609, 550, 582, 231, 725, 359, 408, 128,
    481, 117, 450, 284, 102, 701, 938, 521, 105, 559,
    644, 622, 948, 954, 930, 381, 964, 428, 810, 975,
    665, 933, 446, 128, 475, 648, 233, 786, 783, 165,
    271, 201, 909, 145, 648, 566, 923, 460, 348, 610,
    454, 326, 648, 213, 393, 607, 260, 249, 141, 273,
)


@dataclass
class PretreatmentConfig:
    """Configuration parameters for dataset pre-treatment, corridors, and Pi-Zipper sampling."""
    mode: Literal["energetic", "location"] = "energetic"
    target_col: str = "seis_core_magnitude"
    train_start_date: str | None = None
    train_end_date: str | None = None
    eval_start_date: str | None = None
    eval_end_date: str | None = None
    min_magnitude_threshold: float = 6.9  # Default M >= 6.9+ for high-impact events
    window_before: int = 4  # Number of steps/indices before peak event (Corridor 2a)
    window_after: int = 3   # Number of steps/indices after peak event (Corridor 2b)
    background_sample_ratio: float = 0.10  # Fraction of background calm records to keep
    background_chunk_size: int = 1  # Consecutive quiet rows retained per Pi-Zipper position
    seed: int = 42
    date_col: str = "date"
    eval_min_events: int = 3  # Minimum major events required in validation
    eval_max_events: int = 5  # Maximum major events allowed in validation
    auto_balance_dates: bool = False  # Search for best balanced train/eval temporal cutoffs
    eval_window_mode: Literal["corridors", "continuous"] = "corridors"  # Focus eval on peak windows vs continuous timeline
    eval_corridor_span: int | None = None  # Window size around eval events (default: max(window_before, window_after))
    eval_event_dates: Sequence[str] | None = None  # Optional exact held-out event dates; disables automatic event discovery
    mandatory_negative_col: str | None = None  # Foreign hard negatives kept at 100% in training
    excluded_feature_cols: Sequence[str] = ()  # Numeric audit/label columns never admitted as predictors


@dataclass
class PretreatmentResult:
    """Packaged output of pre-treatment ready for model training and forecasting."""
    train_df: pd.DataFrame
    eval_df: pd.DataFrame
    target_col: str
    feature_cols: list[str]
    total_raw_rows: int
    train_corridor_rows: int
    train_background_rows: int
    train_final_rows: int
    eval_rows: int
    eval_major_events_count: int
    study_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary_markdown(self) -> str:
        return (
            f"### Pretreatment Summary (Study: `{self.study_id}`)\n"
            f"| Attribute | Value |\n"
            f"| :--- | :--- |\n"
            f"| **Modality Mode** | `{self.metadata.get('mode', 'energetic')}` |\n"
            f"| **Target Field** | `{self.target_col}` |\n"
            f"| **Threshold $M_{{thresh}}$** | $\\ge {self.metadata.get('min_magnitude_threshold', 6.9)}$ |\n"
            f"| **Active Features** | {len(self.feature_cols)} features |\n"
            f"| **Total Raw Master Rows** | {self.total_raw_rows} |\n"
            f"| **Train Event Corridors (100% kept)** | {self.train_corridor_rows} rows |\n"
            f"| **Train Background Samples ($\\\\pi$-Zipper)** | {self.train_background_rows} rows |\n"
            f"| **Final Training Set Size** | **{self.train_final_rows} rows** |\n"
            f"| **Evaluation Set Size** | **{self.eval_rows} rows ({self.eval_major_events_count} major events, mode='{self.metadata.get('eval_window_mode', 'corridors')}')** |\n"
        )


class MasterPretreatmentEngine:
    """Pre-treatment and Pi-Zipper Context Corridor Sub-Sampling Engine in Millesimi."""

    def __init__(self, config: PretreatmentConfig | None = None) -> None:
        self.config = config or PretreatmentConfig()

    @staticmethod
    def _sample_pi_zipper_with_audit(
        background_indices: Sequence[int],
        sample_ratio: float = 0.10,
        seed: int = 42,
        chunk_size: int = 1,
    ) -> tuple[list[int], list[dict[str, int | float]]]:
        """Samples background indices using a continuous Pi-modulated stepping sequence in Millesimi (/ 1000.0)."""
        if not background_indices:
            return [], []

        if sample_ratio >= 1.0:
            return list(background_indices), []
        if sample_ratio <= 0.0:
            return [], []

        chunk_size = max(1, int(chunk_size))
        base_stride = max(chunk_size, int(round(chunk_size / sample_ratio)))
        sampled: list[int] = []
        cursor = 0
        pi_idx = 0
        seed_offset = seed % len(PI_DIGIT_TRIPLETS)
        n_bg = len(background_indices)
        audit: list[dict[str, int | float]] = []

        while cursor < n_bg:
            pi_triplet = PI_DIGIT_TRIPLETS[(pi_idx + seed_offset) % len(PI_DIGIT_TRIPLETS)]
            pi_frac = pi_triplet / 1000.0
            jitter = int(round((pi_frac - 0.5) * (base_stride * 0.5)))
            step = max(1, base_stride + jitter)
            chosen_positions = [cursor]
            while len(chosen_positions) < chunk_size:
                next_position = chosen_positions[-1] + 1
                if next_position >= n_bg:
                    break
                if int(background_indices[next_position]) != int(background_indices[chosen_positions[-1]]) + 1:
                    break
                chosen_positions.append(next_position)
            for position in chosen_positions:
                sampled.append(background_indices[position])
                audit.append({
                    "sample_number": len(sampled) - 1,
                    "source_index": int(background_indices[position]),
                    "pi_triplet": int(pi_triplet),
                    "pi_fraction": float(pi_frac),
                    "base_stride": int(base_stride),
                    "jitter": int(jitter),
                    "step": int(step),
                    "chunk_size": int(len(chosen_positions)),
                })
            cursor += step
            pi_idx += 1

        return sampled, audit

    @staticmethod
    def sample_pi_zipper(
        background_indices: Sequence[int],
        sample_ratio: float = 0.10,
        seed: int = 42,
        chunk_size: int = 1,
    ) -> list[int]:
        """Backward-compatible public Pi-Zipper sampler."""
        sampled, _ = MasterPretreatmentEngine._sample_pi_zipper_with_audit(
            background_indices, sample_ratio, seed, chunk_size
        )
        return sampled

    def _isolate_modality_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strips non-target seismic columns according to energetic vs location modality."""
        df_out = df.copy()
        target = self.config.target_col

        seis_cols = [c for c in df_out.columns if c.startswith("seis_")]
        cols_to_drop = [c for c in seis_cols if c != target]
        if cols_to_drop:
            df_out.drop(columns=cols_to_drop, inplace=True, errors="ignore")
            logger.info(f"Modality '{self.config.mode}': Isolated target '{target}'. Dropped {len(cols_to_drop)} non-target seismic columns.")

        return df_out

    def _auto_balance_temporal_cutoffs(self, df: pd.DataFrame, date_col: str, target_col: str) -> tuple[str, str, str, str]:
        """Automatically balances train and eval temporal dates to capture between eval_min_events and eval_max_events."""
        mag_series = df[target_col] if target_col in df.columns else pd.Series(0.0, index=df.index)
        event_indices = df.index[mag_series >= self.config.min_magnitude_threshold].tolist()

        if len(event_indices) == 0:
            # Fallback if no events above threshold
            split_idx = int(len(df) * 0.8)
            t_start = df[date_col].iloc[0].strftime("%Y-%m-%d")
            t_end = df[date_col].iloc[split_idx - 1].strftime("%Y-%m-%d")
            e_start = df[date_col].iloc[split_idx].strftime("%Y-%m-%d")
            e_end = df[date_col].iloc[-1].strftime("%Y-%m-%d")
            return t_start, t_end, e_start, e_end

        # Select target number of validation events between [min_events, max_events]
        target_n_val = min(self.config.eval_max_events, max(self.config.eval_min_events, max(1, len(event_indices) // 5)))
        target_n_val = min(target_n_val, max(1, len(event_indices) - 1))  # Ensure at least 1 in train

        val_event_indices = event_indices[-target_n_val:]
        first_val_idx = val_event_indices[0]

        # Place eval start just before first val event (using window_before)
        w_span = max(self.config.window_before, self.config.window_after)
        eval_start_idx = max(0, first_val_idx - w_span)
        train_end_idx = max(0, eval_start_idx - 1)

        t_start = self.config.train_start_date or df[date_col].iloc[0].strftime("%Y-%m-%d")
        t_end = df[date_col].iloc[train_end_idx].strftime("%Y-%m-%d")
        e_start = df[date_col].iloc[eval_start_idx].strftime("%Y-%m-%d")
        e_end = self.config.eval_end_date or df[date_col].iloc[-1].strftime("%Y-%m-%d")

        logger.info(
            f"Auto-Balanced Temporal Dates: {len(event_indices)} total M>={self.config.min_magnitude_threshold} events -> "
            f"Train: [{t_start} .. {t_end}] ({len(event_indices) - target_n_val} events), "
            f"Eval: [{e_start} .. {e_end}] ({target_n_val} events)."
        )
        return t_start, t_end, e_start, e_end

    def process(self, df_or_csv: pd.DataFrame | str | Path, study_name: str | None = None) -> PretreatmentResult:
        """Executes full pre-treatment pipeline: modality isolation, chronological split, corridors, and Pi-Zipper."""
        if isinstance(df_or_csv, (str, Path)):
            df_raw = pd.read_csv(df_or_csv, low_memory=False)
        else:
            df_raw = df_or_csv.copy()

        date_col = self.config.date_col
        if date_col not in df_raw.columns:
            if "datetime" in df_raw.columns:
                date_col = "datetime"
            else:
                date_col = df_raw.columns[0]

        target_col = self.config.target_col
        if target_col not in df_raw.columns:
            raise ValueError(f"Target column '{target_col}' not present in dataset. Columns: {list(df_raw.columns[:8])}...")

        # 1. Modality Feature Isolation
        df_isolated = self._isolate_modality_columns(df_raw)

        # 2. Chronological Ordering & Auto Date Balancing
        df_isolated[date_col] = pd.to_datetime(df_isolated[date_col])
        df_isolated.sort_values(by=date_col, inplace=True)
        df_isolated.reset_index(drop=True, inplace=True)

        if self.config.auto_balance_dates or (self.config.eval_start_date is None and self.config.train_end_date is None):
            t_start, t_end, e_start, e_end = self._auto_balance_temporal_cutoffs(df_isolated, date_col, target_col)
            self.config.train_start_date = self.config.train_start_date or t_start
            self.config.train_end_date = t_end
            self.config.eval_start_date = e_start
            self.config.eval_end_date = self.config.eval_end_date or e_end

        mask_train = df_isolated[date_col] >= pd.to_datetime(self.config.train_start_date)
        if self.config.train_end_date:
            mask_train &= df_isolated[date_col] <= pd.to_datetime(self.config.train_end_date)

        mask_eval = df_isolated[date_col] >= pd.to_datetime(self.config.eval_start_date)
        if self.config.eval_end_date:
            mask_eval &= df_isolated[date_col] <= pd.to_datetime(self.config.eval_end_date)

        df_train_raw = df_isolated[mask_train].copy().reset_index(drop=True)
        df_eval_raw = df_isolated[mask_eval].copy().reset_index(drop=True)

        if len(df_train_raw) == 0:
            raise ValueError("Training partition is empty. Check train_start_date and train_end_date!")
        if len(df_eval_raw) == 0:
            raise ValueError("Evaluation partition is empty. Check eval_start_date and eval_end_date!")

        # 3. Peak Event Corridor Extraction & Pi-Zipper Sub-Sampling (Training set)
        mag_train_series = df_train_raw[target_col] if target_col in df_train_raw.columns else pd.Series(0.0, index=df_train_raw.index)
        event_indices_train = df_train_raw.index[mag_train_series >= self.config.min_magnitude_threshold].tolist()

        corridor_indices_set: set[int] = set()
        n_train = len(df_train_raw)
        w_before = self.config.window_before
        w_after = self.config.window_after

        for e_idx in event_indices_train:
            start_i = max(0, e_idx - w_before)
            end_i = min(n_train - 1, e_idx + w_after)
            for k in range(start_i, end_i + 1):
                corridor_indices_set.add(k)

        all_train_indices = set(range(n_train))
        background_indices = sorted(list(all_train_indices - corridor_indices_set))

        mandatory_negative_indices: list[int] = []
        if self.config.mandatory_negative_col:
            if self.config.mandatory_negative_col not in df_train_raw.columns:
                raise ValueError(
                    f"Mandatory-negative column '{self.config.mandatory_negative_col}' is absent"
                )
            mandatory_negative_indices = df_train_raw.index[
                pd.to_numeric(
                    df_train_raw[self.config.mandatory_negative_col], errors="coerce"
                ).fillna(0).gt(0)
            ].tolist()
            background_indices = sorted(
                set(background_indices) - set(mandatory_negative_indices)
            )

        sampled_background, pi_zipper_audit = self._sample_pi_zipper_with_audit(
            background_indices=background_indices,
            sample_ratio=self.config.background_sample_ratio,
            seed=self.config.seed,
            chunk_size=self.config.background_chunk_size,
        )

        final_train_indices = sorted(list(
            corridor_indices_set.union(sampled_background).union(mandatory_negative_indices)
        ))
        df_train_final = df_train_raw.iloc[final_train_indices].copy().reset_index(drop=True)

        # 4. Evaluation Window Corridor Slicing (if eval_window_mode == 'corridors')
        mag_eval_series = df_eval_raw[target_col] if target_col in df_eval_raw.columns else pd.Series(0.0, index=df_eval_raw.index)
        if self.config.eval_event_dates:
            requested_dates = pd.to_datetime(list(self.config.eval_event_dates)).normalize()
            requested_set = set(requested_dates)
            matched_mask = df_eval_raw[date_col].dt.normalize().isin(requested_set)
            event_indices_eval = df_eval_raw.index[
                matched_mask & mag_eval_series.ge(self.config.min_magnitude_threshold)
            ].tolist()
            if len(event_indices_eval) != len(requested_set):
                matched_dates = df_eval_raw.loc[event_indices_eval, date_col].dt.strftime("%Y-%m-%d").tolist()
                raise ValueError(
                    "Exact validation events are incomplete or not positive: "
                    f"requested={sorted(value.date().isoformat() for value in requested_set)}, "
                    f"matched={matched_dates}"
                )
        else:
            event_indices_eval = df_eval_raw.index[
                mag_eval_series >= self.config.min_magnitude_threshold
            ].tolist()
        eval_events_count = len(event_indices_eval)

        if self.config.eval_window_mode == "corridors" and len(event_indices_eval) > 0:
            eval_w_span = self.config.eval_corridor_span or max(w_before, w_after)
            eval_corridor_indices_set: set[int] = set()
            n_eval = len(df_eval_raw)
            for ev_idx in event_indices_eval:
                s_i = max(0, ev_idx - eval_w_span)
                e_i = min(n_eval - 1, ev_idx + eval_w_span)
                for k in range(s_i, e_i + 1):
                    eval_corridor_indices_set.add(k)
            final_eval_indices = sorted(list(eval_corridor_indices_set))
            df_eval_final = df_eval_raw.iloc[final_eval_indices].copy().reset_index(drop=True)
            if self.config.eval_event_dates:
                expected_eval_rows = len(event_indices_eval) * (2 * int(eval_w_span) + 1)
                if len(df_eval_final) != expected_eval_rows:
                    raise ValueError(
                        f"Expected exactly {expected_eval_rows} validation rows from the frozen corridors; "
                        f"got {len(df_eval_final)}"
                    )
            logger.info(f"Eval Window Mode 'corridors': Sliced {len(df_eval_raw)} raw eval rows into {len(df_eval_final)} corridor rows around {eval_events_count} key events.")
        else:
            df_eval_final = df_eval_raw.copy().reset_index(drop=True)

        df_train_final[date_col] = df_train_final[date_col].dt.strftime("%Y-%m-%d")
        df_eval_final[date_col] = df_eval_final[date_col].dt.strftime("%Y-%m-%d")

        feature_cols = [
            c for c in df_train_final.columns
            if c not in (date_col, "time", target_col, *self.config.excluded_feature_cols)
            and pd.api.types.is_numeric_dtype(df_train_final[c])
        ]

        study_id = study_name or f"Study_{self.config.mode}_{target_col}_T{len(df_train_final)}_E{len(df_eval_final)}"

        res = PretreatmentResult(
            train_df=df_train_final,
            eval_df=df_eval_final,
            target_col=target_col,
            feature_cols=feature_cols,
            total_raw_rows=len(df_raw),
            train_corridor_rows=len(corridor_indices_set),
            train_background_rows=len(sampled_background),
            train_final_rows=len(df_train_final),
            eval_rows=len(df_eval_final),
            eval_major_events_count=eval_events_count,
            study_id=study_id,
            metadata={
                **asdict(self.config),
                "mandatory_negative_rows": len(mandatory_negative_indices),
                "pi_zipper_audit": pi_zipper_audit,
                "pi_triplets_used": [row["pi_triplet"] for row in pi_zipper_audit],
            },
        )
        logger.info(
            f"Pretreatment Complete -> Train: {res.train_final_rows} rows, Eval: {res.eval_rows} rows ({res.eval_major_events_count} major events). "
            f"Active features: {len(feature_cols)}."
        )
        return res

    def run_study(
        self,
        df_or_csv: pd.DataFrame | str | Path,
        model_type: str | ModelType = "kan",
        study_name: str | None = None,
        epochs: int = 80,
        output_dir: str | Path | None = None,
        **tunable_params: Any,
    ) -> tuple[ModelMetrics, pd.DataFrame, PretreatmentResult]:
        """Runs end-to-end Pretreatment -> Training on Filtered Stream -> Validation Evaluation on Full Stream."""
        p_res = self.process(df_or_csv, study_name=study_name)

        engine = ForecastingEngine(model_type=model_type, **tunable_params)

        train_info = engine.model.fit(
            X_train=p_res.train_df[p_res.feature_cols],
            y_train=p_res.train_df[p_res.target_col],
            feature_names=p_res.feature_cols,
            target_name=p_res.target_col,
            epochs=epochs,
            **tunable_params,
        )

        metrics, df_eval_comp = engine.model.evaluate(
            X_val=p_res.eval_df[p_res.feature_cols],
            y_val=p_res.eval_df[p_res.target_col],
        )

        df_out = pd.DataFrame({
            "date": p_res.eval_df[self.config.date_col].values,
            "actual": df_eval_comp["actual"].values,
            f"predicted_{p_res.target_col}": df_eval_comp["predicted"].values,
            "error": df_eval_comp["error"].values,
            "abs_error": df_eval_comp["abs_error"].values,
        })

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            df_out.to_csv(out_p / f"{p_res.study_id}_validation.csv", index=False)
            p_res.train_df.to_csv(out_p / f"{p_res.study_id}_train_pretreated.csv", index=False)
            metrics_payload = {
                "study_id": p_res.study_id,
                "model": engine.model.name,
                "tunable_params": engine.model.get_tunable_params(),
                "pretreatment": asdict(self.config),
                "metrics": metrics.to_dict(),
                "train_info": train_info,
            }
            with open(out_p / f"{p_res.study_id}_metrics.json", "w", encoding="utf-8") as f:
                json.dump(metrics_payload, f, indent=2)

        return metrics, df_out, p_res


def build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DLVS-Wave v2.0 Master Pretreatment Engine & Pi-Zipper Sub-Sampler (Millesimi)")
    p.add_argument("--input-csv", required=True, help="Path to input master CSV dataset")
    p.add_argument("--mode", choices=["energetic", "location"], default="energetic", help="Forecasting modality")
    p.add_argument("--target-col", default="seis_core_magnitude", help="Target column name")
    p.add_argument("--train-start-date", help="Training start date (YYYY-MM-DD)")
    p.add_argument("--train-end-date", help="Training end date (YYYY-MM-DD)")
    p.add_argument("--eval-start-date", help="Evaluation start date (YYYY-MM-DD)")
    p.add_argument("--eval-end-date", help="Evaluation end date (YYYY-MM-DD)")
    p.add_argument("--min-mag-threshold", type=float, default=6.9, help="Minimum magnitude threshold for peak corridors (default 6.9)")
    p.add_argument("--eval-min-events", type=int, default=3, help="Minimum major events in validation set (default 3)")
    p.add_argument("--eval-max-events", type=int, default=5, help="Maximum major events in validation set (default 5)")
    p.add_argument("--auto-balance-dates", action="store_true", help="Automatically search for best balanced train/eval temporal cutoffs")
    p.add_argument("--eval-window-mode", choices=["corridors", "continuous"], default="corridors", help="Validation mode: sliced peak corridors vs continuous timeline")
    p.add_argument("--eval-corridor-span", type=int, help="Window size around eval events (default max(window_before, window_after))")
    p.add_argument("--window-before", type=int, default=4, help="Context indices before event (2a)")
    p.add_argument("--window-after", type=int, default=3, help="Context indices after event (2b)")
    p.add_argument("--background-ratio", type=float, default=0.10, help="Background sampling ratio (3)")
    p.add_argument("--seed", type=int, default=42, help="Random seed for Pi-zipper formula")
    p.add_argument("--model-type", choices=["kan", "lcs", "deep_learning"], default="kan", help="ML model paradigm")
    p.add_argument("--output-dir", help="Output directory to save study results")
    p.add_argument("--epochs", type=int, default=80, help="Training epochs")
    p.add_argument("--param1", type=float, help="First tunable parameter")
    p.add_argument("--param2", type=float, help="Second tunable parameter")
    return p


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = build_cli_parser().parse_args()

    cfg = PretreatmentConfig(
        mode=args.mode,
        target_col=args.target_col,
        train_start_date=args.train_start_date,
        train_end_date=args.train_end_date,
        eval_start_date=args.eval_start_date,
        eval_end_date=args.eval_end_date,
        min_magnitude_threshold=args.min_mag_threshold,
        eval_min_events=args.eval_min_events,
        eval_max_events=args.eval_max_events,
        auto_balance_dates=args.auto_balance_dates,
        eval_window_mode=args.eval_window_mode,
        eval_corridor_span=args.eval_corridor_span,
        window_before=args.window_before,
        window_after=args.window_after,
        background_sample_ratio=args.background_ratio,
        seed=args.seed,
    )
    engine = MasterPretreatmentEngine(cfg)

    tunable_params: dict[str, Any] = {}
    if args.param1 is not None:
        tunable_params["param1"] = args.param1
    if args.param2 is not None:
        tunable_params["param2"] = args.param2

    metrics, df_val, p_res = engine.run_study(
        df_or_csv=args.input_csv,
        model_type=args.model_type,
        epochs=args.epochs,
        output_dir=args.output_dir,
        **tunable_params,
    )
    print("\n" + p_res.summary_markdown())
    print(metrics.summary_markdown(f"Validation Performance ({args.model_type.upper()})"))
    print(f"\nSample Predictions:\n{df_val.head(5)}")


if __name__ == "__main__":
    main()

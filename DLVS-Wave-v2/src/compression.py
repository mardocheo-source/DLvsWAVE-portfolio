"""Modulo 4: Quantization and Integer Bit-Packing Compression Engine for DLVS-Wave v2.0.

Provides:
  - Continuous astronomical feature quantization to K quantiles/bins (e.g. 2-bit = 4 bins: 0, 1, 2, 3).
  - Robust quantile edge calculation with strict monotonicity (no degenerate collapsed edges).
  - Automatic zero-variance column exclusion (prevents constant 65535 bitfield containers).
  - Full Preservation of Seismic Data in Chiaro:
      * ALL Seismic features (seis_core_magnitude, seis_core_latitude, seis_core_longitude, seis_core_depth,
        summarized seismic metrics, and historical seismic shifts) are kept 100% in plain numeric format in chiaro.
      * Seismic features are positioned immediately following date for instant inspection.
      * Bit-packing is applied strictly to continuous astronomical feature matrices (packed_astro_container_*).
  - Reverse unpacking for lossless verification of discrete representations.
  - JSON Codebook export containing quantile bin thresholds and container mappings.
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

from naming import DEFAULT_SEISMIC_CORE_FIELDS, order_master_columns, reorder_master_dataframe

logger = logging.getLogger("dlvs_wave.compression")


@dataclass
class BitPackingConfig:
    bits_per_field: int = 2          # 2 bits = 4 quantiles
    fields_per_container: int = 8    # 8 fields x 2 bits = 16-bit integer container
    container_dtype: str = "uint16"  # uint8, uint16, uint32, uint64
    prefix_container_name: str = "packed_astro_container"
    date_col: str = "date"
    isolated_families: bool = True   # Astro feature container isolation
    prune_zero_variance: bool = True # Automatically drop flat constant columns


@dataclass
class CompressionCodebook:
    bits_per_field: int
    num_bins: int
    fields_per_container: int
    container_dtype: str
    containers: dict[str, list[str]]
    quantile_edges: dict[str, list[float]]
    total_original_features: int
    total_packed_features: int
    compression_ratio_fields: float
    untouched_seismic_columns: list[str] = field(default_factory=list)
    pruned_constant_columns: list[str] = field(default_factory=list)
    quantile_fit_row_count: int = 0
    quantile_fit_start_date: str | None = None
    quantile_fit_end_date: str | None = None


class QuantizedBitPacker:
    """Quantizes continuous decimal fields and packs them into integer bitfields."""

    def __init__(self, config: BitPackingConfig | None = None) -> None:
        self.config = config or BitPackingConfig()
        self.num_bins = 2 ** self.config.bits_per_field
        self.mask = (1 << self.config.bits_per_field) - 1

    def _compute_quantiles(self, series: pd.Series) -> list[float]:
        """Calculates bin cutoffs using empirical quantiles with strict monotonicity."""
        valid = series.dropna().to_numpy(dtype=float)
        if len(valid) == 0:
            return [float(i) for i in range(1, self.num_bins)]

        min_v = float(np.min(valid))
        max_v = float(np.max(valid))
        if max_v <= min_v:
            return [min_v + (i * 1e-6) for i in range(1, self.num_bins)]

        quantiles = np.linspace(0.0, 1.0, self.num_bins + 1)[1:-1]
        edges = [float(np.percentile(valid, q * 100)) for q in quantiles]

        # Enforce strict monotonicity to prevent bin collapse
        for i in range(1, len(edges)):
            if edges[i] <= edges[i - 1]:
                edges[i] = edges[i - 1] + 1e-6
        return edges

    def _quantize_series(self, series: pd.Series, edges: list[float]) -> np.ndarray:
        """Converts continuous values into discrete bin indices 0..(num_bins-1)."""
        valid = series.fillna(0.0).to_numpy(dtype=float)
        bins = np.digitize(valid, bins=edges, right=False)
        bins = np.clip(bins, 0, self.num_bins - 1)
        return bins.astype(np.uint64)

    def pack(
        self,
        df: pd.DataFrame,
        feature_cols: Sequence[str] | None = None,
        fit_mask: Sequence[bool] | pd.Series | np.ndarray | None = None,
    ) -> tuple[pd.DataFrame, CompressionCodebook]:
        """Quantizes and packs continuous astronomical features into integer containers.

        Seismic features are strictly preserved in chiaro (uncompressed) as primary columns.
        When ``fit_mask`` is supplied, quantile edges and variance pruning are
        fitted only on those rows, then applied unchanged to the full timeline.
        This prevents validation or prospective rows from influencing the
        representation learned for a strict chronological experiment.
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty.")

        # Identify all seismic columns to preserve in chiaro
        seis_cols_in_df = [c for c in df.columns if c.startswith("seis_")]

        if feature_cols is None:
            # Only pack non-seismic, non-index continuous features
            feature_cols = [
                c for c in df.columns
                if c not in (self.config.date_col, "time")
                and not c.startswith("seis_")
                and not c.startswith("packed_")
                and pd.api.types.is_numeric_dtype(df[c])
            ]

        if fit_mask is None:
            fit_frame = df
            normalized_fit_mask = np.ones(len(df), dtype=bool)
        else:
            normalized_fit_mask = np.asarray(fit_mask, dtype=bool)
            if normalized_fit_mask.shape != (len(df),):
                raise ValueError("fit_mask must contain exactly one boolean per dataframe row")
            if not normalized_fit_mask.any():
                raise ValueError("fit_mask selected zero rows")
            fit_frame = df.loc[normalized_fit_mask]

        # 1. Filter out zero-variance constant columns
        pruned_constant = []
        valid_feature_cols = []
        if self.config.prune_zero_variance:
            for c in feature_cols:
                if fit_frame[c].nunique(dropna=False) <= 1 or (
                    pd.api.types.is_numeric_dtype(fit_frame[c])
                    and float(fit_frame[c].std(ddof=0)) < 1e-12
                ):
                    pruned_constant.append(c)
                else:
                    valid_feature_cols.append(c)
        else:
            valid_feature_cols = list(feature_cols)

        if not valid_feature_cols and feature_cols:
            logger.warning("No variable astro feature columns found to pack after pruning.")
            valid_feature_cols = list(feature_cols)
            pruned_constant = []

        quantile_edges: dict[str, list[float]] = {}
        quantized_arrays: dict[str, np.ndarray] = {}

        for col in valid_feature_cols:
            edges = self._compute_quantiles(fit_frame[col])
            quantile_edges[col] = edges
            quantized_arrays[col] = self._quantize_series(df[col], edges)

        M = self.config.fields_per_container
        B = self.config.bits_per_field
        containers_mapping: dict[str, list[str]] = {}

        out_dict: dict[str, Any] = {}
        if self.config.date_col in df.columns:
            out_dict[self.config.date_col] = df[self.config.date_col].values
        if "time" in df.columns:
            out_dict["time"] = df["time"].values

        # All seismic columns stay 100% in chiaro right after date
        for s_col in seis_cols_in_df:
            out_dict[s_col] = df[s_col].values

        np_dtype = getattr(np, self.config.container_dtype, np.uint16)
        total_containers = (len(valid_feature_cols) + M - 1) // M if valid_feature_cols else 0

        for container_idx in range(total_containers):
            group_cols = list(valid_feature_cols[container_idx * M : (container_idx + 1) * M])
            container_name = f"packed_astro_container_{container_idx:03d}"
            containers_mapping[container_name] = group_cols

            packed_array = np.zeros(len(df), dtype=np.uint64)
            for shift_idx, col_name in enumerate(group_cols):
                val = quantized_arrays[col_name]
                packed_array |= (val << (shift_idx * B))

            out_dict[container_name] = packed_array.astype(np_dtype)

        out_df = pd.DataFrame(out_dict)
        out_df = reorder_master_dataframe(out_df)

        ratio = round(len(valid_feature_cols) / max(1, total_containers), 2) if total_containers > 0 else 1.0
        codebook = CompressionCodebook(
            bits_per_field=B,
            num_bins=self.num_bins,
            fields_per_container=M,
            container_dtype=self.config.container_dtype,
            containers=containers_mapping,
            quantile_edges=quantile_edges,
            total_original_features=len(valid_feature_cols),
            total_packed_features=total_containers,
            compression_ratio_fields=ratio,
            untouched_seismic_columns=seis_cols_in_df,
            pruned_constant_columns=pruned_constant,
            quantile_fit_row_count=int(normalized_fit_mask.sum()),
            quantile_fit_start_date=(
                str(pd.to_datetime(df.loc[normalized_fit_mask, self.config.date_col]).min().date())
                if self.config.date_col in df.columns else None
            ),
            quantile_fit_end_date=(
                str(pd.to_datetime(df.loc[normalized_fit_mask, self.config.date_col]).max().date())
                if self.config.date_col in df.columns else None
            ),
        )

        logger.info(
            f"Bit-Packing: Packed {len(valid_feature_cols)} astro fields into {total_containers} "
            f"{self.config.container_dtype} containers ({ratio}x reduction). Preserved {len(seis_cols_in_df)} seismic fields in chiaro. Pruned {len(pruned_constant)} constant fields."
        )
        return out_df, codebook

    def unpack(self, packed_df: pd.DataFrame, codebook: CompressionCodebook) -> pd.DataFrame:
        """Decompresses packed integer containers back to discrete quantile indices."""
        out_dict: dict[str, Any] = {}
        if self.config.date_col in packed_df.columns:
            out_dict[self.config.date_col] = packed_df[self.config.date_col].values
        if "time" in packed_df.columns:
            out_dict["time"] = packed_df["time"].values

        for s_col in codebook.untouched_seismic_columns:
            if s_col in packed_df.columns:
                out_dict[s_col] = packed_df[s_col].values

        B = codebook.bits_per_field
        mask = (1 << B) - 1

        for container_name, orig_cols in codebook.containers.items():
            if container_name not in packed_df.columns:
                continue
            packed_vals = packed_df[container_name].to_numpy(dtype=np.uint64)
            for shift_idx, col_name in enumerate(orig_cols):
                discrete_vals = (packed_vals >> (shift_idx * B)) & mask
                out_dict[col_name] = discrete_vals.astype(np.uint8)

        out_df = pd.DataFrame(out_dict)
        return reorder_master_dataframe(out_df)

    def save_codebook(self, codebook: CompressionCodebook, output_path: str | Path) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(asdict(codebook), f, indent=2)
        return out

    def load_codebook(self, path: str | Path) -> CompressionCodebook:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return CompressionCodebook(**data)


def compress_dataset(
    df: pd.DataFrame,
    bits_per_field: int = 2,
    fields_per_container: int = 8,
    container_dtype: str = "uint16",
    isolated_families: bool = True,
    prune_zero_variance: bool = True,
    output_csv_path: str | Path | None = None,
    output_codebook_path: str | Path | None = None,
) -> tuple[pd.DataFrame, CompressionCodebook, Path | None, Path | None]:
    config = BitPackingConfig(
        bits_per_field=bits_per_field,
        fields_per_container=fields_per_container,
        container_dtype=container_dtype,
        isolated_families=isolated_families,
        prune_zero_variance=prune_zero_variance,
    )
    packer = QuantizedBitPacker(config)
    packed_df, codebook = packer.pack(df)

    saved_csv = None
    saved_codebook = None
    if output_csv_path:
        saved_csv = Path(output_csv_path)
        saved_csv.parent.mkdir(parents=True, exist_ok=True)
        packed_df.to_csv(saved_csv, index=False)

    if output_codebook_path:
        saved_codebook = packer.save_codebook(codebook, output_codebook_path)

    return packed_df, codebook, saved_csv, saved_codebook


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Quantization & Astro Bit-Packing CLI for DLVS-Wave v2.0")
    p.add_argument("--input-csv", required=True, help="Path to uncompressed input CSV dataset")
    p.add_argument("--output-csv", required=True, help="Path to save the packed CSV dataset")
    p.add_argument("--output-codebook", required=True, help="Path to save the JSON compression codebook")
    p.add_argument("--bits-per-field", type=int, default=2, help="Quantization bits per field (default: 2)")
    p.add_argument("--fields-per-container", type=int, default=8, help="Fields per container (default: 8)")
    p.add_argument("--container-dtype", choices=("uint8", "uint16", "uint32", "uint64"), default="uint16", help="Unsigned integer container type (default: uint16)")
    p.add_argument("--isolated-families", action="store_true", help="Enable isolated family container partitioning")
    p.add_argument("--no-prune-zero-variance", action="store_true", help="Disable automatic zero-variance pruning")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df = pd.read_csv(args.input_csv)
    packed_df, codebook, saved_csv, saved_cb = compress_dataset(
        df=df,
        bits_per_field=args.bits_per_field,
        fields_per_container=args.fields_per_container,
        container_dtype=args.container_dtype,
        isolated_families=args.isolated_families,
        prune_zero_variance=not args.no_prune_zero_variance,
        output_csv_path=args.output_csv,
        output_codebook_path=args.output_codebook,
    )
    print(f"Dataset successfully packed -> {saved_csv} ({codebook.total_original_features} active astro cols -> {codebook.total_packed_features} containers, preserved {len(codebook.untouched_seismic_columns)} seismic fields in chiaro, pruned {len(codebook.pruned_constant_columns)} constant fields)")
    print(f"Codebook successfully saved -> {saved_cb}")


if __name__ == "__main__":
    main()

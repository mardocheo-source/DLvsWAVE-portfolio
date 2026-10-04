"""Modulo 8: Master Decodification Manifest Generator for DLVS-Wave v2.0.

Generates comprehensive Markdown companion documentation for fused master datasets, detailing:
  - Dataset dimensions, timestamps, and size reduction stats.
  - Tracked celestial bodies, prefix groups, and feature inventories.
  - Preserved Seismic Core and Historical Shift features in chiaro.
  - Container-by-container bit decodification tables (bit ranges, shift offsets, quantile thresholds).
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from compression import CompressionCodebook
from naming import parse_field_name

logger = logging.getLogger("dlvs_wave.reporting")


class MasterManifestGenerator:
    """Produces GitHub-flavored Markdown decodification manifest reports."""

    def __init__(self, master_name: str = "Master Dataset") -> None:
        self.master_name = master_name

    def generate_manifest_markdown(
        self,
        df_uncompressed: pd.DataFrame,
        df_packed: pd.DataFrame,
        codebook: CompressionCodebook,
        output_md_path: str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        out = Path(output_md_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        meta = metadata or {}
        date_min = df_uncompressed["date"].min() if "date" in df_uncompressed.columns else "N/A"
        date_max = df_uncompressed["date"].max() if "date" in df_uncompressed.columns else "N/A"

        # Discover bodies and features
        body_features: dict[str, list[str]] = {}
        for col in df_uncompressed.columns:
            if col in ("date", "time"):
                continue
            parsed = parse_field_name(col)
            if parsed is not None:
                body_features.setdefault(parsed.group_key, []).append(col)
            else:
                body_features.setdefault("other", []).append(col)

        lines: list[str] = []
        lines.append(f"# DLVS-Wave v2.0 Master Manifest & Decodification Report: {self.master_name}")
        lines.append("")
        lines.append(f"> **Generated at**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  ")
        lines.append(f"> **Chronological Timeline**: `{date_min}` to `{date_max}` (`{len(df_uncompressed)}` time steps)")
        lines.append("")

        # 1. Overview Table
        lines.append("## 1. Dataset Dimensions & Compression Summary")
        lines.append("")
        raw_size = meta.get("raw_size_bytes", len(df_uncompressed.to_csv().encode("utf-8")))
        packed_size = meta.get("packed_size_bytes", len(df_packed.to_csv().encode("utf-8")))
        red_pct = meta.get("size_reduction_pct", round((1 - packed_size / max(1, raw_size)) * 100, 2))

        lines.append("| Dimension | Raw Uncompressed | Quantized Bit-Packed (2-Bit / 16-Bit) | Reduction Ratio |")
        lines.append("| :--- | :--- | :--- | :--- |")
        lines.append(f"| **Feature Columns** | `{df_uncompressed.shape[1]}` columns | `{df_packed.shape[1]}` columns | **{codebook.compression_ratio_fields}x fewer fields** |")
        lines.append(f"| **Record Count** | `{df_uncompressed.shape[0]}` rows | `{df_packed.shape[0]}` rows | 1:1 Synchronized |")
        lines.append(f"| **Storage Size** | `{raw_size:,} bytes` | `{packed_size:,} bytes` | **{red_pct}% space saved** |")
        lines.append(f"| **Container Type** | `Float64` | `{codebook.container_dtype}` (`{codebook.bits_per_field}` bits/field, `{codebook.num_bins}` quantiles) | Compact Binary |")
        lines.append("")

        # 2. Preserved Seismic Features in Chiaro
        seis_in_chiaro = codebook.untouched_seismic_columns if hasattr(codebook, "untouched_seismic_columns") else [c for c in df_packed.columns if c.startswith("seis_")]
        if seis_in_chiaro:
            lines.append("## 2. Preserved Seismic Features (In Chiaro / Uncompressed)")
            lines.append("")
            lines.append("All seismic parameters (core 3D coordinates + magnitude and historical lag shifts) are preserved uncompressed as leading columns immediately following `date` for instant inspection:")
            lines.append("")
            for s_col in seis_in_chiaro:
                lines.append(f"- **`{s_col}`**")
            lines.append("")

        # 3. Celestial Bodies & Groups
        lines.append("## 3. Tracked Astronomical Bodies & Feature Groups Catalog")
        lines.append("")
        lines.append("| Prefix / Body Group | Fields Count | Sample Features Included |")
        lines.append("| :--- | :--- | :--- |")
        for grp, feats in sorted(body_features.items()):
            if grp.startswith("seis_"):
                continue
            sample = ", ".join([f"`{f.split('_')[-1]}`" for f in feats[:4]])
            if len(feats) > 4:
                sample += f", ... (+{len(feats)-4} more)"
            lines.append(f"| **`{grp}`** | {len(feats)} | {sample} |")
        lines.append("")

        # 4. Decodification Matrix
        lines.append("## 4. Container Decodification Matrix & Quantile Codebook")
        lines.append("")
        lines.append("This matrix allows 100% exact decompression of packed integer fields into their discrete quantile bins `[0, 1, 2, 3]`.")
        lines.append("")

        for container_name, orig_cols in codebook.containers.items():
            lines.append(f"### Container: `{container_name}` (`{codebook.container_dtype}`)")
            lines.append("| Bit Range | Shift Offset | Original Feature Name | Quantile 25% ($q_{25}$) | Median 50% ($q_{50}$) | Quantile 75% ($q_{75}$) |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            
            B = codebook.bits_per_field
            for idx, col in enumerate(orig_cols):
                bit_start = idx * B
                bit_end = bit_start + B - 1
                edges = codebook.quantile_edges.get(col, [0.0, 0.0, 0.0])
                e25 = f"{edges[0]:.5g}" if len(edges) > 0 else "N/A"
                e50 = f"{edges[1]:.5g}" if len(edges) > 1 else "N/A"
                e75 = f"{edges[2]:.5g}" if len(edges) > 2 else "N/A"
                lines.append(f"| `Bits {bit_start}-{bit_end}` | `>> {bit_start}` | `{col}` | `{e25}` | `{e50}` | `{e75}` |")
            lines.append("")

        content = "\n".join(lines)
        with out.open("w", encoding="utf-8") as f:
            f.write(content)

        return out


def generate_master_manifest(
    df_uncompressed: pd.DataFrame,
    df_packed: pd.DataFrame,
    codebook: CompressionCodebook,
    output_md_path: str | Path,
    master_name: str = "Master Dataset",
    metadata: dict[str, Any] | None = None,
) -> Path:
    gen = MasterManifestGenerator(master_name=master_name)
    return gen.generate_manifest_markdown(
        df_uncompressed=df_uncompressed,
        df_packed=df_packed,
        codebook=codebook,
        output_md_path=output_md_path,
        metadata=metadata,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Master Manifest Generator CLI for DLVS-Wave v2.0")
    p.add_argument("--uncompressed-csv", required=True, help="Path to raw uncompressed CSV dataset")
    p.add_argument("--packed-csv", required=True, help="Path to packed CSV dataset")
    p.add_argument("--codebook-json", required=True, help="Path to JSON codebook file")
    p.add_argument("--output-md", required=True, help="Output path for markdown manifest report")
    p.add_argument("--master-name", default="Master Dataset", help="Display title for master dataset")
    return p


def main() -> None:
    args = build_parser().parse_args()
    df_u = pd.read_csv(args.uncompressed_csv)
    df_p = pd.read_csv(args.packed_csv)
    with open(args.codebook_json, "r", encoding="utf-8") as f:
        cb_dict = json.load(f)
    codebook = CompressionCodebook(**cb_dict)

    out = generate_master_manifest(
        df_uncompressed=df_u,
        df_packed=df_p,
        codebook=codebook,
        output_md_path=args.output_md,
        master_name=args.master_name,
    )
    print(f"Manifest successfully generated -> {out}")


if __name__ == "__main__":
    main()

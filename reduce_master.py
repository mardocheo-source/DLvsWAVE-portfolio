#!/usr/bin/env python3
"""Reduce a master CSV to peak events + context window + sampled valley records.

Valley sampling (designed to avoid teaching the net a regular pattern):
    - count per gap = round(gap_len * --valley-density) * (1 +/- --valley-jitter)
      so longer gaps yield proportionally more records, with random noise
    - positions = jittered-equispaced (default), random, or even (deterministic)
    - --per-gap-min / --per-gap-max are optional safety bounds
    - --global-valley-cap shrinks proportionally if total exceeds the cap
    - --seed is printed every run; reuse it to reproduce a sampling
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_NORMALIZE_EXCLUDE = ["date", "mag", "depth", "latitude", "longitude"]


def parse_args():
    p = argparse.ArgumentParser(
        description="Reduce a master CSV by keeping peaks + context + sampled valleys.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("master", type=Path, help="Input master CSV path")
    p.add_argument("--out", type=Path, default=None,
                   help="Explicit output path. The default '<input>_reduced.csv' is ALSO written.")

    p.add_argument("--peak-col", default="mag",
                   help="Column used to detect peak events")
    p.add_argument("--peak-threshold", type=float, default=0.1,
                   help="Rows with peak-col >= threshold are peaks")

    p.add_argument("--window", type=int, default=6,
                   help="Records kept on EACH side of every peak (=> ±window)")

    p.add_argument("--valley-density", type=float, default=0.05,
                   help="Fraction of each gap to sample as valley records (0.05 = 5%%)")
    p.add_argument("--valley-jitter", type=float, default=0.3,
                   help="Random noise on the per-gap count, +/- this fraction (0.3 = +/-30%%)")
    p.add_argument("--valley-positions", choices=["jittered", "random", "even"],
                   default="jittered",
                   help="How to place the chosen records inside the gap")
    p.add_argument("--per-gap-min", type=int, default=1,
                   help="Min valley records per non-empty gap (safety floor)")
    p.add_argument("--per-gap-max", type=int, default=None,
                   help="Optional max valley records per gap (safety ceiling, default: none)")
    p.add_argument("--global-valley-cap", type=int, default=None,
                   help="Cap on TOTAL valley records between first and last peak (proportional shrink)")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed; if omitted, derived from time and printed for reproducibility")

    p.add_argument("--future-mode", required=True, choices=["tail", "cutoff", "both"],
                   help="REQUIRED. How to preserve the 'future' portion of the series")
    p.add_argument("--future-tail-keep", default="all",
                   help="For tail/both: 'all', 'none', or integer N records after last peak")
    p.add_argument("--future-from", default=None,
                   help="For cutoff/both: ISO date YYYY-MM-DD; rows from that date onward kept 1:1")

    p.add_argument("--normalize", action="store_true",
                   help="Min-max normalize numeric columns into [0,1]")
    p.add_argument("--normalize-exclude", default="",
                   help="Comma-separated EXTRA columns to exclude (added to default list)")

    p.add_argument("--qbins", type=int, default=0,
                   help="Number of quantile bins (>=2). 0 disables. Replaces values with bin position")
    p.add_argument("--qbins-output", choices=["norm", "idx"], default="norm",
                   help="'norm' = bin position normalized to [0,1] (e.g. qbins=5 -> 0/0.25/0.5/0.75/1); "
                        "'idx' = raw integer index 0..N-1")

    return p.parse_args()


def parse_tail_keep(value, available_count):
    if value == "all":
        return available_count
    if value == "none":
        return 0
    try:
        n = int(value)
    except ValueError:
        sys.exit(f"--future-tail-keep must be 'all', 'none', or an integer (got {value!r})")
    if n < 0:
        sys.exit("--future-tail-keep integer must be >= 0")
    return min(n, available_count)


def equispaced_indices(length, n_take):
    if n_take <= 0 or length == 0:
        return np.array([], dtype=int)
    n_take = min(n_take, length)
    return np.unique(np.linspace(0, length - 1, n_take).round().astype(int))


def pick_count(gap_len, density, jitter, gmin, gmax, rng):
    if gap_len <= 0:
        return 0
    target = max(gmin, int(round(gap_len * density)))
    if jitter > 0:
        noise = 1.0 + rng.uniform(-jitter, jitter)
        target = int(round(target * noise))
    target = max(gmin, target)
    if gmax is not None:
        target = min(target, gmax)
    return min(target, gap_len)


def pick_positions(free_indices, n_take, mode, rng):
    if n_take <= 0 or len(free_indices) == 0:
        return np.array([], dtype=int)
    n_take = min(n_take, len(free_indices))
    if mode == "even":
        sel = equispaced_indices(len(free_indices), n_take)
    elif mode == "random":
        sel = np.sort(rng.choice(len(free_indices), size=n_take, replace=False))
    else:  # jittered
        anchors = np.linspace(0, len(free_indices) - 1, n_take)
        step = (len(free_indices) - 1) / max(1, n_take)
        offsets = rng.uniform(-step / 2, step / 2, size=n_take)
        sel = np.clip(np.round(anchors + offsets).astype(int), 0, len(free_indices) - 1)
        sel = np.unique(sel)
    return free_indices[sel]


def main():
    args = parse_args()

    if args.qbins == 1 or args.qbins < 0:
        sys.exit("--qbins must be 0 (disabled) or >= 2")
    if args.future_mode in ("cutoff", "both") and not args.future_from:
        sys.exit("--future-from YYYY-MM-DD is required when --future-mode is 'cutoff' or 'both'")
    if args.window < 0:
        sys.exit("--window must be >= 0")
    if args.valley_density < 0 or args.valley_density > 1:
        sys.exit("--valley-density must be in [0, 1]")
    if args.valley_jitter < 0 or args.valley_jitter > 1:
        sys.exit("--valley-jitter must be in [0, 1]")
    if args.per_gap_min < 0:
        sys.exit("--per-gap-min must be >= 0")
    if args.per_gap_max is not None and args.per_gap_max < args.per_gap_min:
        sys.exit("--per-gap-max must be >= --per-gap-min")

    seed = args.seed if args.seed is not None else int(time.time() * 1000) & 0xFFFFFFFF
    rng = np.random.default_rng(seed)

    extras = [c.strip() for c in args.normalize_exclude.split(",") if c.strip()]
    exclude_cols = sorted(set(DEFAULT_NORMALIZE_EXCLUDE) | set(extras))

    bar = "=" * 72
    print(bar)
    print("REDUCE MASTER — chosen configuration")
    print(bar)
    print(f"  input               : {args.master}")
    print(f"  peak detection      : {args.peak_col!r} >= {args.peak_threshold}")
    print(f"  context window      : ±{args.window} records around each peak")
    print(f"  valley density      : {args.valley_density:.3f}  ({args.valley_density*100:.1f}% of each gap)")
    print(f"  valley jitter       : ±{args.valley_jitter*100:.0f}% on the per-gap count")
    print(f"  valley positions    : {args.valley_positions}")
    print(f"  per-gap min / max   : {args.per_gap_min} / "
          f"{args.per_gap_max if args.per_gap_max is not None else 'no cap'}")
    print(f"  global valley cap   : {args.global_valley_cap if args.global_valley_cap is not None else 'none'}"
          f"  (proportional shrink if exceeded)")
    print(f"  RNG seed            : {seed}"
          + ("  (auto from time — pass --seed {0} to reproduce)".format(seed) if args.seed is None else "  (user-provided)"))
    print(f"  future-mode         : {args.future_mode}")
    if args.future_mode in ("tail", "both"):
        print(f"    tail-keep         : {args.future_tail_keep}  (records after last peak)")
    if args.future_mode in ("cutoff", "both"):
        print(f"    future-from       : {args.future_from}  (rows from this date kept 1:1)")
    if args.normalize or args.qbins >= 2:
        print(f"  transform exclude   : {exclude_cols}"
              + (f"  (default + extras {extras})" if extras else "  (default)"))
    print(f"  normalize [0,1]     : {'on' if args.normalize else 'off'}")
    print(f"  quantile bins       : {args.qbins if args.qbins >= 2 else 'off'}"
          + (f"  (output={args.qbins_output})" if args.qbins >= 2 else "")
          + ("  (applied AFTER normalize)" if (args.normalize and args.qbins >= 2) else ""))
    print(f"  output (default)    : {args.master.with_name(args.master.stem + '_reduced.csv')}")
    if args.out is not None:
        print(f"  output (--out)      : {args.out}")
    print(bar)

    if not args.master.exists():
        sys.exit(f"input not found: {args.master}")
    df = pd.read_csv(args.master)
    if "date" not in df.columns:
        sys.exit("input CSV must have a 'date' column")
    if args.peak_col not in df.columns:
        sys.exit(f"peak column {args.peak_col!r} not in CSV")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    n_orig = len(df)

    peak_idx = np.where(df[args.peak_col].values >= args.peak_threshold)[0]
    n_peaks = len(peak_idx)
    if n_peaks == 0:
        sys.exit(f"no peaks found ({args.peak_col} >= {args.peak_threshold})")

    keep = np.zeros(n_orig, dtype=bool)

    n_window_added = 0
    for p in peak_idx:
        lo = max(0, p - args.window)
        hi = min(n_orig, p + args.window + 1)
        n_window_added += int((~keep[lo:hi]).sum())
        keep[lo:hi] = True

    valley_indices_per_gap = []
    gap_lengths = []
    for i in range(len(peak_idx) - 1):
        a, b = peak_idx[i], peak_idx[i + 1]
        gap_range = np.arange(a + 1, b)
        free = gap_range[~keep[gap_range]]
        gap_lengths.append(len(free))
        if len(free) == 0:
            valley_indices_per_gap.append(np.array([], dtype=int))
            continue
        n_take = pick_count(len(free), args.valley_density, args.valley_jitter,
                            args.per_gap_min, args.per_gap_max, rng)
        chosen = pick_positions(free, n_take, args.valley_positions, rng)
        valley_indices_per_gap.append(chosen)

    valley_before_cap = sum(len(v) for v in valley_indices_per_gap)
    if args.global_valley_cap is not None and valley_before_cap > args.global_valley_cap:
        ratio = args.global_valley_cap / valley_before_cap
        shrunk = []
        for chosen in valley_indices_per_gap:
            if len(chosen) == 0:
                shrunk.append(chosen)
                continue
            n = max(1, int(round(len(chosen) * ratio)))
            shrunk.append(pick_positions(chosen, n, args.valley_positions, rng))
        valley_indices_per_gap = shrunk
    valley_after_cap = sum(len(v) for v in valley_indices_per_gap)

    for arr in valley_indices_per_gap:
        keep[arr] = True

    n_future_tail = 0
    n_future_cutoff = 0

    if args.future_mode in ("tail", "both"):
        last_peak = peak_idx[-1]
        future_range = np.arange(last_peak + 1, n_orig)
        free = future_range[~keep[future_range]]
        n_take = parse_tail_keep(args.future_tail_keep, len(free))
        if n_take > 0:
            tail_chosen = free[-n_take:]
            keep[tail_chosen] = True
            n_future_tail = len(tail_chosen)

    if args.future_mode in ("cutoff", "both"):
        cutoff = pd.to_datetime(args.future_from)
        cutoff_mask = (df["date"] >= cutoff).values
        new_kept = cutoff_mask & ~keep
        n_future_cutoff = int(new_kept.sum())
        keep |= cutoff_mask

    out = df[keep].copy().reset_index(drop=True)

    transform_cols = []
    if args.normalize or args.qbins >= 2:
        for col in out.columns:
            if col in exclude_cols:
                continue
            if pd.api.types.is_numeric_dtype(out[col]):
                transform_cols.append(col)

    norm_skipped_constant = 0
    if args.normalize:
        for col in transform_cols:
            mn, mx = out[col].min(), out[col].max()
            if pd.isna(mn) or pd.isna(mx) or mx == mn:
                out[col] = 0.0
                norm_skipped_constant += 1
            else:
                out[col] = (out[col] - mn) / (mx - mn)

    qbin_failed = 0
    if args.qbins >= 2:
        denom = max(1, args.qbins - 1)
        for col in transform_cols:
            try:
                idx = pd.qcut(out[col], q=args.qbins, labels=False, duplicates="drop")
                if args.qbins_output == "norm":
                    out[col] = idx.astype(float) / denom
                else:
                    out[col] = idx
            except Exception:
                out[col] = 0.0 if args.qbins_output == "norm" else 0
                qbin_failed += 1

    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    out_paths = [args.master.with_name(args.master.stem + "_reduced.csv")]
    if args.out is not None and args.out != out_paths[0]:
        out_paths.append(args.out)

    for op in out_paths:
        op.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(op, index=False)

    n_final = len(out)
    n_gaps = max(0, n_peaks - 1)
    counts_per_gap = [len(v) for v in valley_indices_per_gap]
    avg_valley = (valley_after_cap / n_gaps) if n_gaps > 0 else 0.0

    def _stats(arr):
        if not arr:
            return "n/a"
        a = np.asarray(arr)
        return f"min={a.min()} max={a.max()} mean={a.mean():.1f} median={int(np.median(a))}"

    print()
    print(bar)
    print("RESULTS")
    print(bar)
    print(f"  original rows           : {n_orig}")
    print(f"  peaks ({args.peak_col}>={args.peak_threshold})           : {n_peaks}")
    print(f"  context kept (±{args.window})       : {n_window_added}  (new rows from peak windows)")
    print(f"  gaps between peaks      : {n_gaps}")
    print(f"  gap lengths (free recs) : {_stats(gap_lengths)}")
    print(f"  valley count per gap    : {_stats(counts_per_gap)}")
    print(f"  valleys sampled (tot)   : {valley_after_cap}"
          + (f"  (capped from {valley_before_cap})" if valley_after_cap != valley_before_cap else "")
          + f"  avg/gap={avg_valley:.2f}")
    print(f"  future tail kept        : {n_future_tail}")
    print(f"  future cutoff kept      : {n_future_cutoff}")
    print(f"  final rows              : {n_final}")
    if n_orig > 0:
        kept_pct = 100.0 * n_final / n_orig
        print(f"  reduction               : {100 - kept_pct:.1f}% smaller "
              f"({n_final}/{n_orig} = {kept_pct:.1f}% kept)")
    if args.normalize or args.qbins >= 2:
        print(f"  transformed columns     : {len(transform_cols)} numeric cols (excluded: {exclude_cols})")
        if args.normalize:
            print(f"    normalized to [0,1]   : {len(transform_cols) - norm_skipped_constant} cols"
                  + (f"  ({norm_skipped_constant} constant => set to 0.0)" if norm_skipped_constant else ""))
        if args.qbins >= 2:
            output_desc = (f"normalized to [0,1] in {args.qbins} steps "
                           f"(0, {1/(args.qbins-1):.3f}, ..., 1)") if args.qbins_output == "norm" \
                          else f"raw indices 0..{args.qbins-1}"
            print(f"    quantile-binned       : {len(transform_cols) - qbin_failed} cols into {args.qbins} bins, "
                  f"output={args.qbins_output} ({output_desc})"
                  + (f"  ({qbin_failed} failed => set to 0)" if qbin_failed else ""))
    print(f"  written to              :")
    for op in out_paths:
        print(f"    - {op}")
    print(bar)


if __name__ == "__main__":
    main()

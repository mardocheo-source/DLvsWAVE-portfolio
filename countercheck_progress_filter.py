#!/usr/bin/env python3
"""Compact terminal progress filter for geographic countercheck macro runs."""

from __future__ import annotations

import argparse
import re
import sys
import time


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def make_bar(done: int, total: int, width: int = 34) -> str:
    total = max(1, total)
    ratio = min(1.0, max(0.0, done / total))
    filled = int(round(ratio * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def is_important(line: str) -> bool:
    needles = (
        "[ERROR]",
        "ERROR:",
        "Traceback",
        "Exception",
        "ModuleNotFoundError",
        "command not found",
        "usage:",
        "error:",
        "No such file",
        "failed",
        "failed:",
        "Cannot find",
        "Permission denied",
    )
    return any(needle in line for needle in needles)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-no", required=True)
    parser.add_argument("--phase-name", required=True)
    parser.add_argument("--total-phases", type=int, default=0)
    parser.add_argument("--variants", type=int, default=5)
    parser.add_argument("--trials-per-variant", type=int, default=360)
    args = parser.parse_args()

    progress_re = re.compile(r"^\[\s*(\d+)\s*/\s*(\d+)\]\s+")
    run_re = re.compile(r"^Run\s+([^:]+):")

    observed_variant_total = max(1, args.trials_per_variant)
    variant_idx = 0
    variant_name = "preparing"
    completed_trials = 0
    current_done = 0
    current_total = observed_variant_total
    counting_main_train = False
    seen_main_progress = False
    phase_total_label = str(args.total_phases or "?")
    start_time = time.monotonic()
    last_render = ""

    def newline_if_needed() -> None:
        nonlocal last_render
        if last_render:
            sys.stdout.write("\n")
            sys.stdout.flush()
            last_render = ""

    def render(extra: str = "") -> None:
        nonlocal last_render
        remaining_variants = max(0, args.variants - max(variant_idx, 1))
        expected_total = max(
            1,
            completed_trials + max(current_total, current_done) + remaining_variants * observed_variant_total,
        )
        done_total = min(expected_total, completed_trials + current_done)
        pct = 100.0 * done_total / expected_total
        elapsed = max(0.001, time.monotonic() - start_time)
        eta = (elapsed / done_total) * max(0, expected_total - done_total) if done_total else 0.0
        variant_display = min(max(variant_idx, 1), args.variants)
        msg = (
            f"\r{args.phase_no}/{phase_total_label} {args.phase_name:>3} "
            f"{make_bar(done_total, expected_total)} "
            f"{done_total:4d}/{expected_total:<4d} trial "
            f"{pct:5.1f}%  manca {fmt_duration(eta):>8s}  "
            f"var {variant_display}/{args.variants} {variant_name}"
        )
        if extra:
            msg += f"  {extra}"
        pad = max(0, len(last_render) - len(msg))
        sys.stdout.write(msg + " " * pad)
        sys.stdout.flush()
        last_render = msg

    print(
        f"{args.phase_no}/{phase_total_label} {args.phase_name}: progress filter active "
        f"({args.variants} varianti, circa {args.variants * observed_variant_total} main-trial; "
        "il totale si aggiorna quando il train stampa i trial reali)"
    )
    render("preparazione")

    for raw in sys.stdin:
        line = raw.rstrip("\n")

        m_run = run_re.search(line)
        if m_run:
            if seen_main_progress:
                completed_trials += max(current_total, current_done)
            variant_idx += 1
            variant_name = m_run.group(1).strip()
            current_done = 0
            current_total = observed_variant_total
            counting_main_train = False
            seen_main_progress = False
            newline_if_needed()
            print(f"{args.phase_no}/{phase_total_label} {args.phase_name}: variante {variant_idx}/{args.variants} -> {variant_name}")
            render("build/master")
            continue

        if "[5/6] Train KAN-only" in line or "[5/6] Train KAN + Deep hybrid" in line:
            counting_main_train = True
            current_done = 0
            render("training")
            continue

        if "[6/6] KAN-only" in line or "[6/6] KAN + Deep hybrid" in line:
            counting_main_train = False
            newline_if_needed()
            print(f"{args.phase_no}/{phase_total_label} {args.phase_name}: fusione dei modelli")
            render("fusion")
            continue

        m_progress = progress_re.search(line)
        if m_progress and counting_main_train:
            done = int(m_progress.group(1))
            total = int(m_progress.group(2))
            seen_main_progress = True
            observed_variant_total = max(observed_variant_total, total)
            current_done = done
            current_total = max(1, total)
            render()
            continue

        if "Summarize countercheck results" in line:
            if seen_main_progress:
                completed_trials += current_done
                current_done = 0
                seen_main_progress = False
            newline_if_needed()
            print(f"{args.phase_no}/{phase_total_label} {args.phase_name}: composizione report e mappe")
            render("report")
            continue

        if "Adjudicate target-zone risk" in line:
            newline_if_needed()
            print(f"{args.phase_no}/{phase_total_label} {args.phase_name}: risk adjudication")
            render("risk")
            continue

        if "run ready" in line.lower():
            if seen_main_progress:
                current_done = max(current_total, current_done)
                render("done")
            continue

        if line.startswith("[speed-test]"):
            newline_if_needed()
            print(line)
            render("speed-test")
            continue

        if line.startswith("[device-auto]"):
            newline_if_needed()
            print(line)
            render("device-auto")
            continue

        if line.startswith("[metric-test] Short KAN pretest"):
            newline_if_needed()
            print(line)
            render("metric-test")
            continue

        if is_important(line):
            newline_if_needed()
            print(line)

    if seen_main_progress:
        completed_trials += current_done
    current_remaining = max(0, current_total - current_done) if variant_idx > 0 else 0
    expected_total = max(
        1,
        completed_trials + current_remaining + max(0, args.variants - variant_idx) * observed_variant_total,
    )
    done_total = min(expected_total, completed_trials)
    newline_if_needed()
    elapsed = fmt_duration(time.monotonic() - start_time)
    print(f"{args.phase_no}/{phase_total_label} {args.phase_name}: completato {done_total}/{expected_total} main-trial in {elapsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

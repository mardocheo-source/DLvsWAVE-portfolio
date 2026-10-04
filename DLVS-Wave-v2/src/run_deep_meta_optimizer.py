#!/usr/bin/env python3
"""Command-line entry point for Phase 2 deep meta-optimization."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.meta_optimizer.engine import DeepMetaOptimizer
from src.meta_optimizer.plotting import plot_phase2_convergence_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine Phase 1 DLVS-Wave trials with a deep surrogate and active search",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-trials-csv", required=True, help="Phase 1 optuna_trials_<model>.csv")
    parser.add_argument("--input-master", required=True, help="Summarized packed master CSV")
    parser.add_argument("--model-type", required=True, choices=["kan", "deep_learning", "deep", "lcs"])
    parser.add_argument("--target-col", default="seis_core_magnitude")
    parser.add_argument("--min-mag-threshold", type=float, default=6.9)
    parser.add_argument("--eval-events", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "xpu"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-meta-trials", type=int, default=None, help="Cap total attempts, including resumed ones")
    parser.add_argument("--candidate-batch-size", type=int, default=4)
    parser.add_argument("--retrain-frequency", type=int, default=5, help="Successful trials between surrogate retrains")
    parser.add_argument("--surrogate-epochs", type=int, default=100)
    parser.add_argument("--retrain-epochs", type=int, default=40)
    parser.add_argument("--model-epochs", type=int, default=None, help="Override model epochs (mainly for smoke tests)")
    parser.add_argument("--no-resume", action="store_true", help="Ignore an existing Phase 2 trials CSV")
    parser.add_argument("--no-plots", action="store_true", help="Skip PNG/PDF report generation")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    optimizer = DeepMetaOptimizer(
        input_trials_csv=args.input_trials_csv,
        master_df=args.input_master,
        model_type=args.model_type,
        target_col=args.target_col,
        min_mag_threshold=args.min_mag_threshold,
        eval_events=args.eval_events,
        timeout_seconds=args.timeout_seconds,
        output_dir=args.output_dir,
        device=args.device,
        retrain_frequency=args.retrain_frequency,
        seed=args.seed,
        max_meta_trials=args.max_meta_trials,
        surrogate_epochs=args.surrogate_epochs,
        retrain_epochs=args.retrain_epochs,
        candidate_batch_size=args.candidate_batch_size,
        model_epochs=args.model_epochs,
        resume=not args.no_resume,
    )
    results = optimizer.run()

    if not args.no_plots and results["successful_meta_trials"]:
        try:
            paths = plot_phase2_convergence_report(
                phase1_trials_csv=args.input_trials_csv,
                phase2_dir=optimizer.output_dir,
                model_type=optimizer.model_type,
                output_png=optimizer.output_dir / f"phase2_{optimizer.model_type}_convergence_report.png",
                output_pdf=optimizer.output_dir / f"phase2_{optimizer.model_type}_convergence_report.pdf",
            )
            print(f"Comparison chart: {paths['png']}")
        except Exception as exc:
            logging.getLogger("dlvs_wave.meta_optimizer.cli").warning("Plot generation failed: %s", exc)

    phase2_text = (
        f"{results['phase2_best_objective_loss']:.6f}"
        if results["phase2_best_objective_loss"] is not None
        else "N/A"
    )
    print("\nPHASE 2 DEEP META-OPTIMIZATION COMPLETE")
    print(f"Model: {results['model_type']} | Device: {results['actual_device']}")
    print(f"Attempts: {results['meta_iterations']} | Successful: {results['successful_meta_trials']}")
    print(f"Phase 1 best: {results['phase1_best_objective_loss']:.6f} | Phase 2 best: {phase2_text}")
    print(f"Overall winner: {results['winner']} | Overall objective: {results['best_objective_loss']:.6f}")
    print(f"Artifacts: {optimizer.output_dir}")
    return 0 if results["successful_meta_trials"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

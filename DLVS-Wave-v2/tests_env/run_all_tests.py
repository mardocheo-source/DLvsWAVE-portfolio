"""Master test runner for the DLVS-Wave v2.0 validation suites."""
import sys
import time
from pathlib import Path

# Add src and tests_env to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "tests_env"))

from test_modulo1_seismic import test_seismic_extractor
from test_modulo2_horizons import test_horizons_parallel_and_fault_tolerance
from test_modulo3_resampling import test_temporal_resampling, test_peak_seismic_coupling
from test_modulo4_compression import test_bit_packing_and_decompression
from test_modulo5_pipeline import test_micro_master_and_optuna
from test_modulo7_visualization import test_seismic_mapping
from test_modulo8_reporting import test_manifest_reporting
from test_modulo9_indexing_and_anti_leakage import (
    test_shift_generation_and_anti_leakage,
    test_discrete_seismic_shift_fidelity,
    test_front_positioned_seismic_preservation,
    test_resampling_safety_lock_and_inheritance,
)
from test_modulo10_sanitization_and_pruning import (
    test_alphanumeric_encoding_and_pruning,
    test_packed_containers_contain_no_degenerate_65535,
)
from test_modulo11_models import (
    test_kan_model,
    test_lcs_model,
    test_deep_learning_model,
    test_forecasting_engine_modes,
)
from test_modulo12_pretreatment import (
    test_pi_zipper_stepping,
    test_event_corridor_extraction,
    test_modality_isolation_location,
    test_study_execution_on_real_samples,
    test_auto_date_balancing_and_eval_corridors,
)
from test_modulo13_visualizer import (
    test_visualizer_validation_stacked,
    test_visualizer_pure_forecast,
    test_visualizer_sliced_corridors,
)
from test_modulo14_meta_optimizer import run_modulo14_suite
from test_modulo15_temporal_horizons import run_modulo15_suite
from test_modulo16_phase2_pipeline import run_modulo16_suite


def run_modulo3_suite():
    test_temporal_resampling()
    test_peak_seismic_coupling()


def run_modulo9_suite():
    test_shift_generation_and_anti_leakage()
    test_discrete_seismic_shift_fidelity()
    test_front_positioned_seismic_preservation()
    test_resampling_safety_lock_and_inheritance()


def run_modulo10_suite():
    test_alphanumeric_encoding_and_pruning()
    test_packed_containers_contain_no_degenerate_65535()


def run_modulo11_suite():
    test_kan_model()
    test_lcs_model()
    test_deep_learning_model()
    test_forecasting_engine_modes()


def run_modulo12_suite():
    test_pi_zipper_stepping()
    test_event_corridor_extraction()
    test_modality_isolation_location()
    test_study_execution_on_real_samples()
    test_auto_date_balancing_and_eval_corridors()


def run_modulo13_suite():
    test_visualizer_validation_stacked()
    test_visualizer_pure_forecast()
    test_visualizer_sliced_corridors()


def run_all():
    print("===========================================================================")
    print("STARTING DLVS-WAVE V2.0 MASTER VALIDATION SUITE (16 Moduli / 15 Suites)")
    print("===========================================================================")

    suites = [
        ("Modulo 1 (Seismic Extractor)", test_seismic_extractor),
        ("Modulo 2 (Horizons Parallel & Fault Tolerance)", test_horizons_parallel_and_fault_tolerance),
        ("Modulo 3 (Temporal Resampling & Peak Seismic Coupling)", run_modulo3_suite),
        ("Modulo 4 (2-Bit Quantization & Bit-Packing)", test_bit_packing_and_decompression),
        ("Modulo 5 & 6 (Pipeline Fusion & Optuna Prefix Optimizer)", test_micro_master_and_optuna),
        ("Modulo 7 (Parametric Seismic Mapping & Geography)", test_seismic_mapping),
        ("Modulo 8 (Master Decodification Manifest Generator)", test_manifest_reporting),
        ("Modulo 9 (Shift Indexing, Anti-Leakage & Seismic Preservation)", run_modulo9_suite),
        ("Modulo 10 (Sanitization, Alphanumeric Encoding & Pruning)", run_modulo10_suite),
        ("Modulo 11 (AI Models: KAN, LCS, Deep Learning & Unified Engine)", run_modulo11_suite),
        ("Modulo 12 (Pretreatment, Peak Corridors & Pi-Zipper Sub-Sampling)", run_modulo12_suite),
        ("Modulo 13 (Forecasting Visualizer & Dual Stacked Panels)", run_modulo13_suite),
        ("Modulo 14 (Deep Surrogate Meta-Optimizer)", run_modulo14_suite),
        ("Modulo 15 (Progressive Temporal Horizons & Forecast Report Pages)", run_modulo15_suite),
        ("Modulo 16 (Phase 2 Finalization, Ensemble & Vertical Forecast Dates)", run_modulo16_suite),
    ]

    total_start = time.time()
    passed = 0

    for idx, (name, func) in enumerate(suites, 1):
        print(f"\n[{idx}/{len(suites)}] RUNNING TEST: {name}")
        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            print(f"[{idx}/{len(suites)}] >>> PASSED ({elapsed:.2f}s) <<<")
            passed += 1
        except Exception as e:
            elapsed = time.time() - t0
            print(f"[{idx}/{len(suites)}] >>> FAILED ({elapsed:.2f}s): {e} <<<")
            import traceback
            traceback.print_exc()

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 75)
    if passed == len(suites):
        print(f"ALL {passed}/{len(suites)} TESTS PASSED SUCCESSFULLY IN {total_elapsed:.2f}s!")
        print("DLVS-WAVE V2.0 FULL SYSTEM + AI ENGINE + VISUALIZER IS FULLY VALIDATED.")
    else:
        print(f"TEST SUITE FINISHED WITH FAILURES: {passed}/{len(suites)} passed in {total_elapsed:.2f}s.")
    print("=" * 75)


if __name__ == "__main__":
    run_all()

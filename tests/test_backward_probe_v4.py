import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "DB/japan-m79plus-7d-aug2026-common-backward-v4/pipeline/backward_probe.py"
)
SPEC = importlib.util.spec_from_file_location("backward_probe_v4", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def summary(mean=0.5, lcs=0.5, kan=0.5, deep=0.5):
    systems = {name: mean for name in MODULE.SYSTEMS}
    return {
        "mean": mean,
        "worst": mean,
        "systems": systems,
        "families": {"lcs": lcs, "kan": kan, "deep": deep},
    }


def test_fast_accepts_small_paired_loss():
    passed, guard = MODULE.acceptance(
        summary(),
        summary(mean=0.499, lcs=0.499, kan=0.5, deep=0.501),
        native=False,
        current=summary(),
    )
    assert passed
    assert guard["mean_loss"] < MODULE.FAST_MEAN_TOLERANCE


def test_fast_protects_harmful_family_loss():
    passed, guard = MODULE.acceptance(
        summary(),
        summary(mean=0.499, lcs=0.47, kan=0.51, deep=0.51),
        native=False,
        current=summary(),
    )
    assert not passed
    assert guard["family_losses"]["lcs"] > MODULE.FAST_FAMILY_TOLERANCE


def test_native_audit_has_separate_prudent_guard():
    passed, _ = MODULE.acceptance(
        summary(),
        summary(mean=0.495, lcs=0.49, kan=0.5, deep=0.5),
        native=True,
    )
    assert passed

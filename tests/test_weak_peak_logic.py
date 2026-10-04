from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from weak_peak_logic import WeakPeakConfig, WeakPeakLogicOperator


class WeakPeakLogicTests(unittest.TestCase):
    def test_weak_local_peak_is_promoted(self):
        scores = np.asarray([0.01, 0.04, 0.10, 0.03, 0.01])
        operator = WeakPeakLogicOperator(
            WeakPeakConfig(
                weak_threshold=0.08,
                strong_threshold=0.70,
                min_prominence=0.04,
                event_radius=1,
            )
        )
        prediction = operator.transform(scores)
        self.assertEqual(prediction.tolist(), [0, 0, 1, 0, 0])

    def test_non_peak_weak_score_is_not_promoted(self):
        scores = np.asarray([0.01, 0.10, 0.12, 0.11, 0.01])
        operator = WeakPeakLogicOperator(
            WeakPeakConfig(
                weak_threshold=0.08,
                strong_threshold=0.70,
                min_prominence=0.03,
                event_radius=1,
            )
        )
        self.assertEqual(operator.transform(scores).sum(), 0)

    def test_fit_and_serialization_preserve_contract(self):
        scores = np.asarray([0.01, 0.04, 0.11, 0.03, 0.01, 0.02, 0.09, 0.02])
        target = np.asarray([0, 0, 1, 0, 0, 0, 1, 0])
        operator = WeakPeakLogicOperator().fit(scores, target)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator.json"
            operator.save(path)
            loaded = WeakPeakLogicOperator.load(path)
            np.testing.assert_array_equal(
                operator.transform(scores), loaded.transform(scores)
            )


if __name__ == "__main__":
    unittest.main()

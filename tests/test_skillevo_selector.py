"""Selector, calibration, and statistics tests for SkillEvo."""
from __future__ import annotations

import random
import unittest

from skillevo import stats
from skillevo.features import FEATURE_NAMES
from skillevo.selector import (
    CalibratedSelector,
    FixedSelector,
    IsotonicCalibrator,
    LogisticSelector,
    TemperatureCalibrator,
)


def _row(**values):
    row = {name: 0.0 for name in FEATURE_NAMES}
    row.update(values)
    return row


class SelectorTest(unittest.TestCase):
    def setUp(self):
        rng = random.Random(4)
        self.rows, self.labels = [], []
        for _ in range(240):
            match = rng.choice([0.0, 1.0])
            semantic = rng.random()
            score = 0.65 * match + 0.35 * semantic
            row = _row(bias=1.0, semantic=semantic, semantic_rank=semantic,
                       target_match=match, family_match=match, input_match=match,
                       mechanism_match=match, history_success=0.5,
                       history_recent=0.5, history_family_success=0.5)
            self.rows.append(row)
            self.labels.append(1 if rng.random() < score else 0)

    def test_logistic_learns_signal(self):
        model = LogisticSelector(l2=1.0).fit(self.rows, self.labels)
        correct = sum(
            int((model.predict_proba(row) >= 0.5) == bool(label))
            for row, label in zip(self.rows, self.labels)
        )
        self.assertGreater(correct / len(self.rows), 0.8)

    def test_calibrators_bounded_and_monotone(self):
        probabilities = [index / 20 for index in range(20)]
        labels = [1 if probability > 0.5 else 0 for probability in probabilities]
        temperature = TemperatureCalibrator().fit(probabilities, labels)
        isotonic = IsotonicCalibrator().fit(probabilities, labels)
        transformed = [isotonic.transform(value) for value in probabilities]
        self.assertEqual(transformed, sorted(transformed))
        for value in probabilities:
            self.assertGreaterEqual(temperature.transform(value), 0.0)
            self.assertLessEqual(temperature.transform(value), 1.0)

    def test_calibrated_wrapper(self):
        base = LogisticSelector(l2=1.0).fit(self.rows, self.labels)
        wrapper = CalibratedSelector(base, "temperature").fit_calibrator(self.rows, self.labels)
        for row in self.rows[:20]:
            self.assertGreaterEqual(wrapper.predict_proba(row), 0.0)
            self.assertLessEqual(wrapper.predict_proba(row), 1.0)

    def test_fixed_selector(self):
        row = _row(bias=1.0, semantic=0.7)
        self.assertAlmostEqual(FixedSelector("s", "semantic").predict_proba(row), 0.7)
        random_selector = FixedSelector("r", "random", seed=2)
        self.assertGreaterEqual(random_selector.predict_proba(row), 0.0)


class StatsTest(unittest.TestCase):
    def test_ranking_metrics(self):
        scores = [0.1, 0.2, 0.8, 0.9]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(stats.auroc(scores, labels), 1.0)
        self.assertAlmostEqual(stats.auprc(scores, labels), 1.0)
        self.assertAlmostEqual(stats.brier([1.0, 0.0], [1, 0]), 0.0)
        self.assertAlmostEqual(stats.ece([0.2, 0.8], [0, 1], bins=2), 0.2)

    def test_mcnemar(self):
        result = stats.mcnemar([1] * 10, [0] * 10)
        self.assertEqual(result["b"], 10)
        self.assertLess(result["p"], 0.01)

    def test_bootstrap(self):
        values = [0.0] * 20 + [1.0] * 20
        low, high = stats.bootstrap_ci(values, samples=500, seed=3)
        self.assertLessEqual(low, high)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)


if __name__ == "__main__":
    unittest.main()

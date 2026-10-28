"""Risk-coverage tests."""
from __future__ import annotations

import unittest

from skillevo.risk import curve


def _row(score, utility, success, family="change", baseline=0.3):
    return {
        "score_model": score,
        "utility": utility,
        "success": success,
        "family": family,
        "baseline_score": baseline,
        "attempts": 1,
    }


class RiskTest(unittest.TestCase):
    def test_curve_and_coverage(self):
        rows = [
            _row(0.9, 0.2, 1),
            _row(0.8, 0.1, 1),
            _row(0.7, -0.1, 0),
            _row(0.2, 0.0, 1),
        ]
        result = curve(rows)
        self.assertAlmostEqual(result["metrics"]["coverage"], 1.0)
        self.assertGreaterEqual(result["metrics"]["coverage@5%"], 0.25)
        self.assertLessEqual(result["metrics"]["coverage@5%"], 1.0)
        self.assertGreater(result["metrics"]["risk_auc"], 0.0)
        self.assertEqual(result["curve"][0]["coverage"], 0.0)

    def test_empty(self):
        self.assertEqual(curve([])["curve"], [])


if __name__ == "__main__":
    unittest.main()

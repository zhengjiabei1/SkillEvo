"""End-to-end smoke test for the SkillEvo runner and report builder."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from skillevo.experiment import Config, run
from skillevo.report import generate


class ExperimentSmokeTest(unittest.TestCase):
    def test_tiny_run_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Config(
                seeds=[0],
                counts={"source_train": 1, "source_val": 1, "target_dev": 1,
                        "target_test": 1, "stream": 1},
                k=2,
                budget=2,
                output=folder,
                include_ablations=False,
            )
            results = run(config)
            self.assertIn("aggregate", results)
            self.assertIn("methods", results["aggregate"])
            self.assertTrue((Path(folder) / "results.json").exists())
            self.assertTrue((Path(folder) / "tables" / "methods.csv").exists())
            report = generate(Path(folder) / "results.json")
            self.assertTrue(report.exists())
            text = report.read_text(encoding="utf-8")
            self.assertIn("SkillEvo experiment report", text)
            self.assertTrue((Path(folder) / "figures" / "methods.svg").exists())
            payload = json.loads((Path(folder) / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["config"]["seeds"], [0])


if __name__ == "__main__":
    unittest.main()

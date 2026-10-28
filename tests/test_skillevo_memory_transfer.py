"""Memory, transfer diagnosis, and planner integration tests."""
from __future__ import annotations

import unittest

from skillevo.features import MemoryStats
from skillevo.memory import ExperienceMemory, beta_mean
from skillevo.planner import Retriever, baseline, run_skill, select_and_run
from skillevo.raster import generate_scene
from skillevo.selector import FixedSelector
from skillevo.tasks import build_task_specs, expert_pipeline, generic_pipeline
from skillevo.transfer import beta_cdf, beta_ppf, compatibility, diagnose
from skillevo.types import Outcome, TaskSpec


def _outcome(skill_id="s1", family="change", success=True, utility=0.2, step=0):
    return Outcome(
        task_id=f"t{step}",
        task_family=family,
        target="change",
        skill_id=skill_id,
        kind="pipeline",
        success=success,
        metric=0.8,
        baseline_metric=0.4,
        utility=utility,
        step=step,
        extra={"signature": skill_id},
    )


class MemoryTest(unittest.TestCase):
    def test_dedup_and_stats(self):
        flat = ExperienceMemory("flat")
        dedup = ExperienceMemory("tiered_dedup")
        for step in range(12):
            outcome = _outcome(success=step % 3 != 0, utility=0.1, step=step)
            flat.ingest(outcome)
            dedup.ingest(outcome)
        self.assertEqual(flat.snapshot()["retained"], 12)
        self.assertLessEqual(dedup.snapshot()["retained"], flat.snapshot()["retained"])
        stats = dedup.stats("s1", "change")
        self.assertIsInstance(stats, MemoryStats)
        self.assertGreater(stats.uses, 0)
        self.assertGreater(dedup.snapshot()["duplicate_ratio"], 0.0)

    def test_capacity_and_none(self):
        memory = ExperienceMemory("full", capacity=5, prune_to=3)
        for step in range(30):
            memory.ingest(_outcome(success=step % 2 == 0, utility=0.1 * (step % 4), step=step))
        self.assertLessEqual(memory.snapshot()["retained"], 5)
        none = ExperienceMemory("none")
        none.ingest(_outcome())
        self.assertEqual(none.stats("s1").uses, 0)
        self.assertAlmostEqual(beta_mean(2, 4), 3 / 6)


class TransferTest(unittest.TestCase):
    def test_beta_functions(self):
        self.assertAlmostEqual(beta_cdf(0.5, 1.0, 1.0), 0.5, places=5)
        self.assertAlmostEqual(beta_ppf(0.5, 1.0, 1.0), 0.5, places=3)

    def test_diagnosis_positive_and_negative(self):
        specs = build_task_specs(0, {"source_train": 1, "source_val": 1, "target_dev": 1,
                                     "target_test": 1, "stream": 1})
        change_spec = next(spec for spec in specs["source_train"] if spec.family == "change")
        landcover_spec = next(spec for spec in specs["source_train"] if spec.family == "landcover")
        skill = expert_pipeline(change_spec)
        positive = diagnose(skill, "change", [change_spec, change_spec], [0.3, 0.4])
        negative = diagnose(skill, "landcover", [landcover_spec, landcover_spec], [-0.1, -0.2])
        self.assertEqual(positive.status, "transferable")
        self.assertEqual(negative.status, "blocked")
        self.assertGreater(positive.score, negative.score)
        self.assertGreaterEqual(compatibility(skill, change_spec), 0.5)


class PlannerTest(unittest.TestCase):
    def test_run_and_select(self):
        spec = next(spec for spec in build_task_specs(0, {"source_train": 1, "source_val": 1,
                                                          "target_dev": 1, "target_test": 1,
                                                          "stream": 1})["source_train"]
                    if spec.family == "landcover")
        scene = generate_scene(spec)
        skill = expert_pipeline(spec)
        result = run_skill(spec, scene, skill)
        self.assertGreater(result.score, 0.0)
        base, _ = baseline(spec, scene)
        self.assertGreater(result.score, base)
        library = [skill, generic_pipeline(spec)]
        retriever = Retriever(library)
        memory = ExperienceMemory("none")
        selection = select_and_run(spec, scene, retriever, FixedSelector("semantic", "semantic"),
                                   memory, k=2, budget=1)
        self.assertIn(selection.skill_id, {item.skill_id for item in library})


if __name__ == "__main__":
    unittest.main()

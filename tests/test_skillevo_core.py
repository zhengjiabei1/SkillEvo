"""Core simulator, operation, and grading tests for SkillEvo."""
from __future__ import annotations

import math
import unittest

from skillevo.ops import (
    Context,
    compute_index,
    grade,
    majority_filter,
    otsu_threshold,
    remove_small,
)
from skillevo.raster import generate_scene
from skillevo.tasks import build_library, build_task_specs, expert_pipeline
from skillevo.types import CLASS_INDEX, TaskSpec


class RasterTest(unittest.TestCase):
    def setUp(self):
        self.spec = TaskSpec(task_id="unit-landcover", family="landcover", split="test", seed=3, size=24)

    def test_deterministic_scene(self):
        left = generate_scene(self.spec)
        right = generate_scene(self.spec)
        self.assertEqual(left.truth, right.truth)
        self.assertEqual(left.post["nir"], right.post["nir"])

    def test_all_classes_and_samples(self):
        scene = generate_scene(self.spec)
        self.assertEqual(len(scene.truth), scene.n_pixels)
        self.assertGreaterEqual(len(set(scene.truth)), 4)
        self.assertTrue(scene.samples)
        self.assertEqual(len(scene.samples), len(scene.sample_labels))
        self.assertTrue(all(0 <= index < scene.n_pixels for index in scene.samples))

    def test_bitemporal_change_nonempty(self):
        spec = TaskSpec(task_id="unit-change", family="change", split="test", seed=4, size=24,
                        change_type="deforest")
        scene = generate_scene(spec)
        self.assertEqual(len(scene.change_mask), scene.n_pixels)
        self.assertGreater(sum(scene.change_mask), 0)
        self.assertGreater(sum(1 for value in scene.truth if value), 0)

    def test_expert_pipeline_runs(self):
        scene = generate_scene(self.spec)
        skill = expert_pipeline(self.spec)
        ctx = __import__("skillevo.ops", fromlist=["execute_skill"]).execute_skill(skill, self.spec, scene)
        metric = grade(scene, ctx.map)
        self.assertGreater(metric["score"], 0.5)


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.spec = TaskSpec(task_id="unit-water", family="water", split="test", seed=5, size=24)
        self.scene = generate_scene(self.spec)

    def test_index_ranges(self):
        for index in ("ndvi", "ndwi", "ndbi", "nbr", "bsi", "brightness", "evi"):
            values = compute_index(self.scene, index, "post")
            self.assertEqual(len(values), self.scene.n_pixels)
            self.assertTrue(all(math.isfinite(value) for value in values))
            self.assertLessEqual(max(values), 1.5)
            self.assertGreaterEqual(min(values), -1.5)

    def test_otsu_bimodal(self):
        values = [0.1] * 80 + [0.8] * 20
        threshold = otsu_threshold(values)
        self.assertGreater(threshold, 0.1)
        self.assertLess(threshold, 0.8)

    def test_filters(self):
        size = 5
        data = [0] * (size * size)
        data[12] = 1
        cleaned = remove_small(data, size, min_size=3)
        self.assertEqual(sum(cleaned), 0)
        block = [0] * (size * size)
        for y in range(1, 4):
            for x in range(1, 4):
                block[y * size + x] = 1
        self.assertEqual(sum(majority_filter(block, size)), 9)

    def test_grade(self):
        scene = self.scene
        exact = grade(scene, scene.truth)
        self.assertAlmostEqual(exact["score"], 1.0)
        zeros = [0] * scene.n_pixels
        missing = grade(scene, zeros)
        self.assertLessEqual(missing["score"], 1.0)


class LibraryTest(unittest.TestCase):
    def test_deduplicates_by_signature(self):
        splits = build_task_specs(0, {"source_train": 3, "source_val": 1, "target_dev": 1,
                                      "target_test": 1, "stream": 1})
        library = build_library(splits["source_train"])
        self.assertTrue(library)
        signatures = [skill.signature for skill in library]
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertTrue(all(skill.kind == "pipeline" for skill in library))


if __name__ == "__main__":
    unittest.main()

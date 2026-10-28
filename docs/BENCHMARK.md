# Benchmark

SkillEvo generates deterministic multi-band scenes and evaluates whether a
library of historical analysis skills can be reused on new tasks. This note
documents the task families, scene model, splits, metrics, and evaluation
details.

## Task families

| Family | Input | Target | Metric | Acceptance |
|---|---|---|---|---|
| `landcover` | single date | six land-cover classes | overall accuracy | 0.78 |
| `crop` | single date | crop / non-crop | F1 | 0.55 |
| `water` | single date | water | F1 | 0.65 |
| `flood` | single date | post-event water | F1 | 0.60 |
| `change` | two dates | any class change | F1 | 0.40 |
| `urban` | two dates | new urban | F1 | 0.45 |
| `burn` | two dates | burn scar | F1 | 0.50 |

Each family has a visible metadata record: family, target, input kind, bands,
season, region, cloud fraction, resolution, and an evidence hint (for example,
`ndwi` or `ndvi_change`). The hidden truth is a class map or a binary mask.

## Scene model

Scenes are 32 x 32 pixels with six bands: blue, green, red, NIR, SWIR1, and
SWIR2. Generation proceeds in four stages.

1. **Land cover.** A class map is built from water bodies, forest patches,
   agricultural fields, urban cores, bare soil, and a grass background. Region
   and class priors vary by task.
2. **Spectra.** Each class has a mean reflectance signature. A scene-level gain,
   seasonal factor, local class variation, smooth spatial texture, and per-pixel
   noise are applied. Optional cloud masks brighten visible bands and attenuate
   NIR.
3. **Change.** Bi-temporal scenes apply one of five changes: urban expansion,
   deforestation, crop rotation, flooding, or fire. A non-degenerate change mask
   is guaranteed.
4. **Reference samples.** A stratified sample of labelled pixels is provided
   for supervised skills such as nearest-centroid classification.

The generator is seeded from the task specification, so a task always produces
the same scene. No external data or network access is required.

## Skills and library

A skill is a complete analysis recipe. Primitives include:

- `index`: NDVI, NDWI, NDBI, NBR, NDMI, BSI, brightness, EVI;
- `temporal_diff`, `temporal_ratio`, `spectral_change`;
- `threshold`: Otsu, percentile, mean plus standard deviation, or fixed;
- `classify`: nearest centroid over selected bands and indices;
- `smooth`, `remove_small`, `fill_holes`, `morph`.

Reference recipes are induced from source tasks and canonicalized. Recipes with
the same signature are merged. A run has about 20 skills. The library stores
provenance, input requirements, targets, and a description used only for
retrieval.

## Splits

Per seed:

| Split | Tasks | Purpose |
|---|---:|---|
| `source_train` | 70 | induce the library and fit the selector |
| `source_val` | 28 | calibrate reuse probabilities |
| `target_dev` | 56 | transfer probes and optional target calibration |
| `target_test` | 42 | final evaluation |
| `stream` | 56 | prequential memory evaluation |

Source and target tasks use disjoint scene seeds and parameter combinations.
The default experiment uses seeds 0, 1, and 2.

## Metrics

- **Success:** fraction of tasks with `q(s, t) >= tau_f`.
- **Score:** mean task metric.
- **Negative transfer:** a selected skill falls back because it is incompatible,
  or its utility is below -0.02.
- **AUROC / AUPRC:** candidate-level ranking quality; labels are whether each
  candidate solves the task.
- **Brier / NLL / ECE:** probabilistic calibration of reuse predictions.
- **P@1 / NDCG@5:** top-1 and top-5 ranking quality.
- **Memory:** retained records, estimated characters, duplicate ratio, and
  compression ratio.

Confidence intervals use 2,000 task-level bootstrap resamples. Paired success
uses an exact McNemar test; paired scores use a 5,000-draw sign-flip
permutation test.

## Evaluation details

The candidate pool is the top eight skills by description embedding. Main
results use top-1 selection. A budgeted variant retries up to three candidates
and keeps the best outcome. The oracle bound executes every retrieved candidate.

Transfer diagnosis uses the target development split. For each skill and target
family, the agent measures utility on eight probe tasks, computes a
Beta-binomial posterior with a structural prior, and gates blocked skills before
reranking. Thresholds are fixed on development data.

## Reproducibility

The benchmark is deterministic for a fixed seed and uses only the Python
standard library. The committed run can be reproduced with:

```bash
python -m skillevo experiment --seeds 0,1,2 --output experiments
python -m skillevo report
```

Task-level records are in `experiments/results.json`; the generated report is
`experiments/REPORT.md`.

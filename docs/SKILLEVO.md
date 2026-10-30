# SkillEvo

SkillEvo is a research module for **calibrated skill selection and tiered memory
in tool-using agents**, with a spatiotemporal case study. The benchmark
generates small multi-band scenes, the agent composes remote-sensing
operations, and every experiment runs on a CPU without an LLM or a GPU.

The module asks three questions:

1. Given a library of procedures induced from past tasks, can a small calibrated
   discriminator predict whether a procedure will be reusable on a new task
   better than embedding similarity?
2. Can a two-tier memory (short-term episodes, consolidated long-term
   experience) keep the same task success with a much smaller footprint and
   better-calibrated reuse probabilities?
3. Can a transferability score estimated on a small target probe split isolate
   skills that do not transfer across task families, and reduce negative
   transfer?

## Quick start

```bash
python -m skillevo experiment --seeds 0,1,2 --output experiments
python -m skillevo report
```

The first command writes `experiments/results.json` and CSV tables; the
second writes `REPORT.md` and SVG figures. The committed run takes about 5.5
minutes on a laptop CPU and produces the numbers used in `paper/skillevo.md`.

## Benchmark

Each task is a 32 × 32 pixel, six-band scene with a hidden thematic target.
Seven families cover single-date and bi-temporal analysis:

| Family | Input | Target | Metric |
|---|---|---|---|
| `landcover` | single date | six land-cover classes | overall accuracy |
| `crop` | single date | crop / non-crop | F1 |
| `water` | single date | water | F1 |
| `flood` | single date | post-event water | F1 |
| `change` | two dates | any class change | F1 |
| `urban` | two dates | new urban | F1 |
| `burn` | two dates | burn scar | F1 |

Scenes contain class-specific spectral signatures, spatially contiguous land
cover, agricultural fields, seasonal illumination, sensor gain, noise, optional
clouds, and controlled bi-temporal changes (urban expansion, deforestation,
rotation, flooding, fire). The same task specification always produces the same
scene.

A **skill** is a complete analysis recipe: a sequence of primitives such as
`index`, `temporal_diff`, `spectral_change`, `threshold`, `classify`, `smooth`,
`remove_small`, and `fill_holes`. The library is induced from reference
solutions on source tasks and deduplicated by a canonical signature. A typical
run has about 20 distinct recipes.

The **generic baseline** is a fixed NDVI threshold with no cleanup. It is
intentionally weak: the benchmark measures whether historical skills add value
over a domain-agnostic fallback, not whether a strong hand-coded pipeline can
solve the scene.

## Method

### Calibrated skill selector

For a candidate skill `s` and a new task `t`, the selector estimates
`P(reuse(s, t) = 1)`. It uses three groups of features:

- **Retrieval:** cosine similarity from a hashed description embedding and its
  rank among candidates.
- **Compatibility:** target match, source-family match, input-kind match,
  spectral-mechanism match, band coverage, adaptivity, and operation cost.
- **Experience (optional):** Beta-smoothed success and utility statistics,
  recency, coverage, duplicate rate, novelty, and family-conditioned success
  from the tiered memory. The default selector uses the structural set; the
  memory variant is used for the streaming experiment and the ablation.

The model is a small L2-regularised logistic regression fitted with IRLS. A
post-hoc calibrator is fitted on a held-out source split: temperature scaling
(one parameter) or isotonic regression (pool-adjacent-violators). The default
selector uses the structural feature set with isotonic calibration; the
memory-enabled variant and the feature-subset ablation are reported separately.

### Tiered experience memory

- **Short-term memory** keeps the last 24 outcomes verbatim, so recent failures
  and successes can change the next decision.
- **Long-term memory** keeps consolidated outcome records with a bounded
  capacity. `tiered` truncates old records, `tiered_dedup` collapses duplicate
  `(skill, family, target, success, utility bucket)` records, and `full`
  additionally prunes low-utility records during consolidation.

The stream experiment is prequential: a skill is selected before the outcome is
observed, then the outcome is ingested. This measures calibration and memory
growth without leaking test labels into the current decision.

### Cross-task transfer diagnosis

For each candidate skill and target family, a small probe split (eight target
development tasks per family) provides utility deltas. A Beta-binomial posterior
over positive transfer is combined with a structural compatibility prior:

```
compatibility = 0.30 * target_match + 0.15 * family_match
              + 0.15 * input_match + 0.30 * mechanism_match
              + 0.10 * band_coverage
score = 0.60 * compatibility + 0.40 * normalised_probe_utility
```

A skill is `blocked` when compatibility is low and probe utility is weak,
`transferable` when structural and empirical evidence agree (or when strong
probe evidence overrides a weak prior), and `uncertain` otherwise. The gate
removes blocked skills before reranking; uncertain skills are down-weighted.

## Protocol

- Three seeds (0, 1, 2).
- Per seed: 70 source training tasks, 28 source validation tasks, 56 target
  development tasks, 42 target test tasks, 56 stream tasks.
- Candidate pool: top eight skills by description embedding.
- Top-1 selection for the main table; a budgeted variant retries up to three
  candidates.
- Success thresholds are family-specific and fixed before the final run
  (`landcover` 0.78 OA, `crop` 0.55 F1, `water` 0.65, `flood` 0.60, `change`
  0.40, `urban` 0.45, `burn` 0.50).
- 95% confidence intervals use 2,000 bootstrap resamples over tasks; paired
  success uses an exact McNemar test and paired scores use a sign-flip
  permutation test (5,000 draws).

## Results

The committed run (`experiments/results.json`) gives:

| Method | Success | Score | AUROC | Brier | ECE |
|---|---:|---:|---:|---:|---:|
| Random candidate | 0.349 | 0.389 | 0.495 | 0.334 | 0.284 |
| Description embedding | 0.500 | 0.505 | 0.666 | 0.233 | 0.152 |
| Frequency prior | 0.540 | 0.524 | 0.509 | 0.246 | 0.138 |
| Logistic, uncalibrated | 0.683 | 0.632 | 0.842 | 0.164 | 0.120 |
| + temperature scaling | 0.683 | 0.632 | 0.842 | 0.165 | 0.105 |
| + isotonic calibration | 0.675 | 0.629 | 0.842 | 0.156 | 0.063 |
| + target-dev calibration | 0.683 | 0.632 | 0.841 | 0.157 | 0.087 |
| Budgeted retry (3) | 0.746 | 0.701 | 0.842 | 0.156 | 0.063 |
| Oracle candidate bound | 0.802 | 0.753 | - | - | - |

The calibrated selector improves top-1 success by 17.5 percentage points over
embedding similarity (McNemar p < 0.001) and score by 0.124 (permutation
p = 0.0002). Ranking quality improves from AUROC 0.666 to 0.842 and Brier score
from 0.233 to 0.156; isotonic calibration reduces ECE from 0.120 to 0.063.

The transfer gate improves success from 0.675 to 0.698 and reduces negative
transfer from 0.056 to 0.048. The transferability matrix shows the expected
block structure: land-cover classifiers transfer strongly to water/flood
(probe utility 0.90/0.92) but not to change/urban/burn (0.03/0.05/0.08); water
skills transfer to flood (0.60) but not back to change (−0.11); change and burn
detectors transfer to each other (0.28/0.23).

The memory stream has essentially flat success (0.774 with no memory, 0.774 with
tiered memory, 0.774 with full memory) but much better calibration: ECE falls
from 0.232 (no memory) to 0.120 (full) and 0.113 (flat). The full store keeps
109 records / 9,987 characters versus 616 records / 57,315 characters for flat
memory, a 5.7× reduction at equal success.

## Interpretation

The feature ablation is important: the structural feature set is the default
selector and reaches 0.675 top-1 success; adding historical outcome features
lowers static success to 0.611. In this benchmark, structural features carry
most of the selection signal; historical features mainly improve calibration in
the streaming setting and enable bounded memory. We report this rather than
hiding it. The transfer gate still adds value because it turns compatibility and
probe evidence into an explicit, auditable decision.

The synthetic scenes are a **controlled diagnostic benchmark**, not a substitute
for real remote-sensing evaluation. The benchmark is useful because the ground
truth, change type, spectral mechanism, and scene difficulty are known; it is
not evidence that the method will improve a production land-cover or change
detection system. A real-data extension should replace `generate_scene` with a
GeoTIFF loader and keep the same task/skill interfaces.

## Real-data extension

`skillevo.raster.load_geotiff` is an optional hook. A real adapter should expose
the same `Scene` fields:

- `pre`/`post`: band name → flat list of reflectance values,
- `classes_pre`/`classes_post`: land-cover labels,
- `truth`/`truth_kind`: target map and `multiclass`/`binary`,
- `samples`/`sample_labels`: labelled reference pixels for supervised skills.

Tasks can then be built from GeoTIFF pairs and labelled masks without changing
the selector, memory, or transfer code.

## Files

| Path | Purpose |
|---|---|
| `skillevo/raster.py` | scene generator and optional real-data hook |
| `skillevo/ops.py` | primitive operations, filters, grading |
| `skillevo/tasks.py` | task families, reference recipes, library induction |
| `skillevo/features.py` | embeddings, memory statistics, selector features |
| `skillevo/selector.py` | logistic discriminator and calibrators |
| `skillevo/memory.py` | short-term and long-term experience memory |
| `skillevo/transfer.py` | Beta-binomial transfer diagnosis and gates |
| `skillevo/planner.py` | retrieval, execution, oracle and budgeted selection |
| `skillevo/experiment.py` | full protocol, tables, JSON |
| `skillevo/report.py` | Markdown report and SVG figures |
| `experiments/` | committed results, tables, figures |
| `paper/` | manuscript draft, bibliography, figures |

## Limitations

- Synthetic 32 × 32 scenes; no real sensor noise, terrain, or co-registration
  error.
- No LLM in the loop; skills are deterministic programs, not free-form plans.
- The library is small (about 20 skills), and success thresholds are
  hand-specified.
- Transfer probes use eight tasks per family; the posterior is intentionally
  conservative but still noisy.
- The structural-only ablation is competitive with the full selector; the paper
  reports this openly.

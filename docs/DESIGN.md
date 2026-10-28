# Design

SkillEvo is a benchmark and reference implementation for selecting and reusing
analysis skills across spatiotemporal tasks. This note describes the problem
formulation, the three modules, and the main design decisions.

## Problem

Let `L = {s_1, ..., s_n}` be a library of executable skills. A skill is a macro
of primitive operations with a canonical signature, an input kind (single-date
or bi-temporal), required bands, target labels, and provenance. A task has a
family, a target, an input kind, band metadata, and a hidden ground-truth map.
Executing a skill on a task yields a prediction and a task metric
`q(s, t)` (overall accuracy for multiclass maps, F1 for binary maps).

A task is solved when `q(s, t) >= tau_f`, where `tau_f` is a family-specific
acceptance threshold. The reuse label is:

```text
y(s, t) = 1[ q(s, t) >= tau_f ]
```

A retriever returns a candidate set. The selector estimates
`p(s, t) = P(y = 1 | t, s)`. The agent executes the highest-scoring candidate,
or retries up to a small budget.

The baseline is description retrieval: rank candidates by cosine similarity
between hashed task and skill text. Both the baseline and the selector use the
same candidate pool, so the comparison isolates the reranker.

## Skill library

Source tasks are solved by reference recipes. A recipe is a sequence of
primitives such as `index(ndwi)`, `threshold(otsu)`, `spectral_change`,
`classify(nearest_centroid)`, `smooth(majority)`, `remove_small`, and
`fill_holes`. Recipes and parameter variants are canonicalized; identical
signatures are merged. A typical run has about 20 skills.

The generic fallback is a fixed NDVI threshold without cleanup. It is
intentionally weak: the benchmark measures the value of historical skills, not
the strength of a hand-coded pipeline.

## Calibrated selector

The default discriminator is an L2-regularised logistic model fitted by
iteratively reweighted least squares with class-balanced weights. Features fall
into three groups.

**Retrieval.** Cosine similarity from a hashed description embedding and its
rank among candidates.

**Compatibility.** Target match, source-family match, input-kind match,
spectral-mechanism match (for example, NDWI for water, spectral distance for
change, nearest centroid for land cover), band coverage, adaptivity, and
operation cost.

**Experience (optional memory variant).** Beta-smoothed success rate, mean
utility, utility standard deviation, evidence strength, recency, family
coverage, duplicate rate, novelty, recent success, and family-conditioned
success from memory.

The model outputs a logit. A post-hoc calibrator maps it to a probability.
Temperature scaling learns one scalar `T` by minimizing negative log-likelihood
on a held-out source split:

```text
p_T = sigmoid(logit / T)
```

Isotonic regression fits a monotone step function with pool-adjacent-violators.
The default selector uses the structural feature set and isotonic calibration.
The memory-enabled variant and the feature-subset ablation are reported
separately.

## Tiered memory

Memory receives an outcome record after each execution: skill, task family,
target, success, utility, and a timestamp.

- **Short-term:** the last `W = 24` records, verbatim.
- **Long-term:** consolidated records with a bounded capacity. Policies:
  - `tiered`: bounded FIFO truncation;
  - `tiered_dedup`: collapse records with the same skill, family, target,
    success, and utility bucket;
  - `full`: dedup plus utility-aware pruning during consolidation.

Statistics are computed from the long-term store, while the short-term store
supplies recency and recent-success features. The split separates recent
episodic evidence from consolidated semantic evidence.

## Cross-task transfer diagnosis

For a candidate skill and target family, the agent runs the skill on a small
probe split of target development tasks. Let `u_i` be the utility delta on probe
`i`, `n` the number of probes, and `k` the number of positive deltas. A Beta
posterior is:

```text
alpha = 1 + 2c + k
beta  = 1 + 2(1 - c) + (n - k)
```

where `c` is a structural compatibility score:

```text
c = 0.30 * target_match + 0.15 * family_match + 0.15 * input_match
  + 0.30 * mechanism_match + 0.10 * band_coverage
```

The transferability score combines compatibility and normalized probe utility:

```text
r = 0.60c + 0.40 * clip((mean_u + 0.10) / 0.60, 0, 1)
```

A skill is:

- **blocked** if `c < 0.35` and `mean_u < 0.25`;
- **transferable** if strong probe evidence (`mean_u >= 0.25`, positive rate
  `>= 0.75`) overrides a weak prior, or if structural compatibility and positive
  utility agree, or if partial compatibility (`c >= 0.35`) meets positive
  utility (`mean_u > 0.10`);
- **uncertain** otherwise.

Blocked skills are removed before reranking; uncertain skills are down-weighted.
Thresholds are fixed on development data and are not tuned on the test split.

## Evaluation summary

The committed run uses three seeds, 70 source training tasks per seed, 28 source
validation tasks, 56 target development tasks, 42 target test tasks, and 56
stream tasks. The candidate pool is the top eight skills by description
embedding.

| Method | Success | Score | AUROC | Brier | ECE |
|---|---:|---:|---:|---:|---:|
| Description embedding | 0.500 | 0.505 | 0.666 | 0.233 | 0.152 |
| Logistic, uncalibrated | 0.683 | 0.632 | 0.842 | 0.164 | 0.120 |
| + isotonic calibration | 0.675 | 0.629 | 0.842 | 0.156 | 0.063 |
| Budgeted retry (3) | 0.746 | 0.701 | 0.842 | 0.156 | 0.063 |
| Oracle candidate bound | 0.802 | 0.753 | - | - | - |

The transfer gate raises success from 0.675 to 0.698 and lowers negative
transfer from 0.056 to 0.048. The memory stream keeps success essentially flat
and reduces calibration error from 0.232 (no memory) to about 0.12, while using
about 5.7x less storage than flat memory.

## Design notes

Structural compatibility carries most of the static selection signal in this
benchmark. Adding historical outcome features lowers static top-1 success from
0.675 to 0.611, but history improves calibration when memory is updated online.
The default selector therefore uses the structural set; history is treated as a
calibration and memory mechanism.

The benchmark is intentionally small and controlled. It isolates selection and
transfer effects rather than measuring operational mapping accuracy.

## Limitations

- Synthetic 32 x 32 scenes; no real sensor noise, terrain, or co-registration
  error.
- Skills are deterministic programs, not free-form plans.
- The library has about 20 skills, and acceptance thresholds are
  family-specific.
- Transfer probes use eight tasks per family; the posterior is conservative but
  noisy.
- Gating can isolate non-transferable skills, but it cannot create a skill that
  is absent from the library.

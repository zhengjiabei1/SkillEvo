# Reproducibility

SkillEvo runs on CPU with the Python standard library. No model API, browser,
GPU, or third-party runtime dependency is required.

## Environment

- Python 3.11 or newer.
- Any operating system with a standard CPython build.
- About 1 GB of free disk space for the generated results.

The committed run was produced on macOS with CPython 3.13. The experiments are
deterministic for a fixed seed.

## Commands

```bash
python -m skillevo experiment --seeds 0,1,2 --output experiments
python -m skillevo report
python -m unittest discover -s tests
```

The experiment takes about 5.5 minutes on a laptop CPU. The report command
rebuilds `experiments/REPORT.md` and the SVG figures from
`experiments/results.json`.

## Outputs

```text
experiments/
  results.json           task-level records and cross-seed aggregate
  REPORT.md              generated tables and figure links
  tables/
    methods.csv
    transfer_gate.csv
    transfer_pairs.csv
    memory_stream.csv
    paired_tests.csv
  figures/
    methods.svg
    reliability.svg
    ablation.svg
    memory.svg
    transfer_heatmap.svg
```

`results.json` is the source of truth. It contains every method, gate, pair,
stream, and ablation record, plus the aggregate used by the report.

## Configuration

The experiment configuration is a Python dataclass in
`skillevo/experiment.py`:

```python
Config(
    seeds=[0, 1, 2],
    counts={
        "source_train": 10,
        "source_val": 4,
        "target_dev": 8,
        "target_test": 6,
        "stream": 8,
    },
    k=8,
    budget=3,
    output="experiments",
)
```

`counts` are tasks per family. `k` is the candidate pool size. `budget` is the
maximum number of candidates tried by the budgeted variant.

## Tests

```bash
python -m unittest discover -s tests -p 'test_skillevo_*.py'
```

The suite covers scene determinism, primitive operations, grading, library
deduplication, the selector and calibrators, memory policies, transfer
diagnosis, planner integration, an end-to-end smoke run, and report generation.

## Notes

- Figures are generated as SVG. Any SVG renderer can convert them to PNG.
- If you change the code, rerun the experiment before comparing numbers with
  the committed report.

# Submission checklist

## Current target

- **Primary:** IEEE JSTARS (methods + Earth-observation applications).
- **Alternatives:** *International Journal of Applied Earth Observation and Geoinformation* (JAG), *Remote Sensing* (MDPI), IEEE GRSL (short format).

## Artifacts in this repository

- [x] Manuscript source (`paper/skillevo.tex`) and readable draft (`paper/skillevo.md`).
- [x] Bibliography (`paper/refs.bib`).
- [x] Figures (`paper/figures/`).
- [x] Deterministic benchmark and experiment runner (`skillevo/`).
- [x] Task-level results (`experiments/results.json`).
- [x] Generated tables and report (`experiments/REPORT.md`, `tables/`).
- [x] Tests (`tests/test_skillevo_*.py`).
- [x] Reproduction commands (README, Appendix A).
- [x] Cover letter draft (`paper/cover_letter.md`).

## Before submission

- [ ] Add a real-data case study. The synthetic benchmark is the main scientific
      weakness for an Earth-observation journal. At minimum, run one
      land-cover and one change-detection dataset (e.g., EuroSAT/UC Merced and
      LEVIR-CD/OSCD) through the same task/skill interfaces.
- [ ] Add a stronger baseline. Options: an LLM planner with the same tools, a
      learned-to-rank model, or a CLIP/RemoteCLIP text-image retriever. The
      current embedding baseline is deliberately simple and should be labelled
      as such.
- [ ] Increase statistical power. Three seeds and 126 target tasks are adequate
      for a diagnostic paper but modest for a journal. Add seeds or task
      families.
- [ ] Compile the LaTeX source and check the IEEEtran page limit. The local
      environment does not include a TeX distribution.
- [ ] Add author affiliation, ORCID, funding, and conflict-of-interest
      statements required by the venue.
- [ ] Add a data/code availability statement with a repository DOI (Zenodo or
      equivalent), not only a GitHub URL.
- [ ] Check whether the venue requires a separate graphical abstract or
      highlights.
- [ ] Re-run `python -m skillevo experiment` after any code change and confirm
      that the manuscript numbers match `experiments/results.json`.

## Claims to keep honest

- The benchmark is synthetic; it is not a remote-sensing leaderboard.
- The structural feature set is the default selector; adding historical outcome features does not improve static top-1 success.
- Memory mainly improves calibration and footprint, not raw success.
- Gating isolates non-transferable skills; it cannot create transferable skills
  that are absent from the library.
- The transfer probe split is small (8 tasks per family).

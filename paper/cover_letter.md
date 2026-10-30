# Cover letter (draft)

Dear Editor,

We submit “SkillEvo: Calibrated Skill Selection and Tiered Experience Memory for Cross-Task Transfer in Spatiotemporal Agents” for consideration as a research article.

The manuscript studies a practical failure mode of skill-reuse agents for geospatial analysis: a procedure can be lexically similar to a task description and still be non-reusable because its input regime, spectral mechanism, or target semantics are incompatible. We replace similarity-only retrieval with a small calibrated reuse discriminator, add a two-tier experience memory, and introduce a compatibility-aware Beta-binomial transfer diagnosis that gates non-transferable skills before execution.

The main findings are:

- A calibrated discriminator raises top-1 success from 0.500 to 0.675 over description embeddings on a controlled seven-family benchmark, improves AUROC from 0.666 to 0.842, and reduces expected calibration error from 0.152 to 0.063.
- Transfer gating raises success to 0.698 and lowers negative transfer from 0.056 to 0.048.
- Tiered memory preserves success while reducing the retained experience footprint by 5.7× relative to flat memory, and substantially improves calibration over a no-memory agent.
- A feature ablation shows that structural compatibility carries most of the selection signal in this benchmark; historical statistics mainly improve calibration and enable bounded memory. We report this negative result explicitly.

We are explicit that the benchmark is synthetic and diagnostic. It is designed to isolate selection and transfer effects, not to claim state-of-the-art land-cover or change-detection accuracy. The code, deterministic benchmark, task-level results, and reproduction commands are released with the manuscript. The interfaces accept real GeoTIFF data, and a real-data case study is the natural next step.

The manuscript is original, is not under consideration elsewhere, and all authors approve the submission. We have no conflicts of interest to declare.

Sincerely,

Jiabei Zheng  
Independent Researcher

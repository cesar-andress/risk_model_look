# risk_model_look

Replication package (code, configs, scripts, docs, and frozen protocol manifests)
for the empirical study:

**When Validity Criteria Disagree: Evaluating Line-Level Explanations for Just-in-Time Defect Prediction**

## What this repository is

Public-facing research infrastructure for:

- acquiring/validating public JIT-Defects4J / JIT-Fine resources (without
  redistributing restricted raw dumps by default);
- training a decoder-only commit-risk classifier (M1: Qwen2.5-Coder-7B QLoRA);
- evaluating line-level attributions under **Attribution Protocol V1.2** and
  **Statistical Protocol V1.1**.

## What this repository is not

- It does **not** automatically redistribute raw datasets (`data/raw/` is
  gitignored). Upstream license/redistribution rights must be verified before
  any public dump.
- It does **not** ship base LLM weights or LoRA adapters by default.
- Manuscript LaTeX currently lives in a sibling path `../paper/` (papers
  monorepo). Integration into `paper/` inside this repository is planned
  (`docs/PAPER_INTEGRATION_PLAN.md`) but **not yet executed**.

## Current phase

Empirical study closed for EMSE. See `docs/FINAL_VENUE_DECISION.md`,
`docs/EMSE_FINAL_ANALYSIS_LOCK.md`, and `docs/AMENDMENT_AND_PROVENANCE_LOG.md`.
Attribution infrastructure is on `main`. A pre-existing worktree
`parallel/attribution-infra` is historical; do not use it for new work.

## Hard constraints

- Do not commit secrets, adapters, or Hugging Face caches.
- Do not claim unfinished experiments as completed.
- External protocol timestamp remains PENDING (not external preregistration).

## Quick start

1. Create the environment from `environment.yml` (or the fallback in
   `docs/ENVIRONMENT_REPORT.md`).
2. `pytest -q` (CPU protocol/unit tests).
3. Follow `REPRODUCIBILITY.md` for dataset digests, training, and evaluation
   sequencing (validation rehearsal before TEST attribution).

GPU smoke / full training require an NVIDIA machine and are **not** part of the
default CPU CI path.

## Dataset restrictions

JIT-Defects4J / JIT-Fine materials are obtained via documented acquisition
scripts and hash checks. Treat redistribution as **restricted until verified**.

## Citation

See `CITATION.cff`. Paper DOI / Zenodo DOI: **TBD** (do not invent).

## License

Code license status: **TBD** (`NOASSERTION` in CITATION.cff until chosen).

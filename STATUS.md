# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

DATASET provenance/semantics phase complete. Next: DATASET acquisition (download `data.zip` under frozen protocol) — not started.

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | IN_PROGRESS |
| DATASET_PROVENANCE_GATE | PASS |
| DATASET_ACQUISITION_GATE | NOT_STARTED |
| DATASET_SCHEMA_VALIDATION_GATE | NOT_STARTED |
| TOKEN_LINE_MAPPING_GATE | NOT_STARTED |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

DATASET_PROVENANCE_GATE completed. Do not start acquisition until orchestrator opens DATASET_ACQUISITION_GATE.

# Completed work

- Environment bootstrap + Qwen 4-bit smoke (prior task).
- Systematic literature search / novelty audit (prior task); NOVELTY_GATE PASS.
- JIT-Fine defining publication verified (DOI 10.1145/3540250.3549165).
- Authoritative upstream frozen: `jacknichao/JIT-Fine@584799fdec6095ab75a45fd2a5f8db5b12163aa5`.
- Remote `data.zip` identified without download (size + git blob SHA-1).
- Author-provided split / line-label / localization-subset / license evidence documented.
- Manifest + provenance report + schema contract + acquisition plan written.

# Blockers

- Archive not yet downloaded; pickle internals / counts / valid carve / SHA-256 deferred to acquisition.
- Dataset/code redistribution license NOT_ESTABLISHED (blocks public raw redistribution, not local acquisition decision).
- JITEC full-text access incomplete (novelty residual; unrelated to this gate).

# Decisions frozen

- Separate code and paper roots.
- ENVIRONMENT_GATE remains PASS (not reopened).
- NOVELTY_GATE remains PASS (not reopened).
- Novelty framing must use compositional / intersection claim, not unqualified primacy.
- Dataset: JIT-Defects4J from jacknichao/JIT-Fine frozen SHA; AUTHOR_PROVIDED split; added-lines primary for JIT-Fine-compatible localization eval; no raw redistribution without license.

# Decisions pending

- Whether/when to open DATASET_ACQUISITION_GATE.
- Whether to include ApacheJIT / ReDef as secondary corpora.
- Journal selection.
- Public release timing.

# Last updated

2026-09-29T23:55:00+02:00

# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

GROUND_TRUTH_LINEAGE_GATE and CANONICAL_DIFF_GATE closed **FAIL**. TOKEN_LINE_MAPPING_GATE remains IN_PROGRESS. Nominal RQ1 N=475 retained (not silently reduced).

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | PASS |
| DATASET_PROVENANCE_GATE | PASS |
| DATASET_ACQUISITION_GATE | PASS |
| DATASET_SCHEMA_VALIDATION_GATE | PASS |
| DIFF_RECONSTRUCTION_GATE | FAIL |
| GROUND_TRUTH_LINEAGE_GATE | FAIL |
| CANONICAL_DIFF_GATE | FAIL |
| TOKEN_LINE_MAPPING_GATE | IN_PROGRESS |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Escalate unresolved Layer-A→Git positive mappings (247/2111) and partial A↔B lineage; orchestrator decides whether a high-confidence RQ1 subset is acceptable. Do not tokenize yet.

# Completed work

- Identified Layer A nested JSON as richest authoritative line-label source (475/475 coverage).
- Canonical first-parent Git diffs for 27319/27319; root-commit extraction fixed.
- File-aware exact mapping: 1864/2111 positives mapped; 352 commits POSITIVE_GT_COMPLETE.

# Blockers

- GROUND_TRUTH_LINEAGE_GATE FAIL: A↔B PARTIAL; 246 ambiguous + 1 missing Layer-A positives.
- CANONICAL_DIFF_GATE FAIL: GT↔canonical mapping incomplete (criterion F).
- CONTEXT_POLICY OPEN.

# Decisions frozen

- PRIMARY_RQ1_POPULATION_NOMINAL = 475; no predicted-positive conditioning.
- CANONICAL_MODEL_INPUT_SOURCE = ordered first-parent Git diff.
- GROUND_TRUTH_SOURCE = Layer A JSON (intent); mapping incomplete.
- Set-equivalence vs upstream sets is diagnostic only.

# Decisions pending

- Whether orchestrator accepts a high-confidence RQ1 subset
- CONTEXT_POLICY
- Journal selection

# Last updated

2026-09-30T08:25:00+02:00

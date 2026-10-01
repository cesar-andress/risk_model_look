# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

Residual closure **FAIL** (18498/18615). Complete-case readiness **PASS** (N=413).  
TOKEN_LINE_MAPPING_GATE remains IN_PROGRESS — awaiting orchestrator RQ1 population decision before tokenizer work.

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
| JITBLOCK_REPLICATION_AUDIT_GATE | PASS |
| RQ1_LABEL_UNIVERSE_GATE | PASS |
| POLICY_A_CANONICAL_BRIDGE_GATE | FAIL |
| POLICY_A_RESIDUAL_CLOSURE_GATE | FAIL |
| POLICY_A_COMPLETE_CASE_READINESS_GATE | PASS |
| TOKEN_LINE_MAPPING_GATE | IN_PROGRESS |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Orchestrator decision: keep primary RQ1 = full Policy A (with unmapped residual excluded from scores) vs adopt POLICY_A_COMPLETE_CASE (N=413) as primary analysis population. Then TOKEN_LINE_MAPPING.

# Completed work

- Residual closure: +31 recovered (18 transform, 13 positional); missing positive recovered; 94 dataset-canonical conflicts; 2060/2060 positives mapped; complete-case bias audit (21/21 projects).

# Blockers

- 117 Policy-A rows still without unique canonical ID (94 conflict + 22 ambiguous + 1 unresolved).
- Historical FAIL gates retained.
- CONTEXT_POLICY OPEN.

# Decisions frozen

- PRIMARY_RQ1_POLICY = POLICY_A universe definition (18615/2060/16555) unchanged.
- CANONICAL_MODEL_INPUT_SOURCE = ordered first-parent Git reconstruction.
- UNKNOWN ≠ NEGATIVE.
- Stop further speculative reconstruction loops.

# Decisions pending

- Whether POLICY_A_COMPLETE_CASE (413) becomes primary RQ1 population
- CONTEXT_POLICY

# Last updated

2026-10-01T05:45:00+02:00

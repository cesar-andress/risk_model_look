# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository (training): `/home/cesar/papers/risk_model_look/risk_model_look`
- Parallel engineering worktree: `/home/cesar/papers/risk_model_look/risk_model_look_parallel` (branch `parallel/attribution-infra`)
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase (this worktree)

ATTRIBUTION_INFRASTRUCTURE_GATE engineering.  
FULL_TRAINING_GATE status is owned by the **primary training worktree** — do not modify it here.  
Do not load 7B models or launch GPU attribution while training runs.

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
| TOKEN_LINE_MAPPING_GATE | PASS |
| PILOT_TRAINING_GATE | PASS |
| PILOT_GATE | PASS |
| FULL_TRAINING_GATE | (see primary training worktree; do not edit from parallel) |
| TRAINING_GATE | (see primary training worktree) |
| ATTRIBUTION_INFRASTRUCTURE_GATE | PASS |
| ATTRIBUTION_RESULTS_GATE | NOT_STARTED |
| RQ1_RESULTS_GATE | NOT_STARTED |
| ATTRIBUTION_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

ATTRIBUTION_INFRASTRUCTURE_GATE — interfaces, metrics, synthetic tests, docs. No scientific attribution results.

# Completed work

- Frozen PRIMARY_RQ1 = complete-case N=413; canonical_v1; token-line mapping PASS.
- M1 QLoRA pilot PASS (see primary tree reports).
- Parallel worktree attribution infrastructure under development.

# Blockers

- Llama tokenizer ACCESS_BLOCKED (M3).
- Historical FAIL gates retained.
- Final M1 adapters unresolved until FULL_TRAINING_GATE completes in primary tree.

# Decisions frozen

- PRIMARY_RQ1_POLICY=POLICY_A_COMPLETE_CASE; CHANGED_ONLY; max_length 2048; Qwen rev `c03e6d358207…`.
- M1 explanation target: `s = logit_1 - logit_0`.
- Occlusion sign: `delta = s(x) - s(x\\R)`; positive supports buggy.

# Last updated

2026-10-01 (parallel attribution infrastructure)

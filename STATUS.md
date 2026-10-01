# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

PILOT_TRAINING_GATE closed **PASS** (technical pipeline + ADEQUATE validation ranking on natural-prevalence Stage B).  
Next: FULL_TRAINING_GATE — do not start until explicitly requested.  
ATTRIBUTION_GATE = NOT_STARTED.

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
| FULL_TRAINING_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| ATTRIBUTION_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

FULL_TRAINING_GATE (not started). Do not run full 16374 training or attribution until requested.

# Completed work

- Frozen PRIMARY_RQ1 = complete-case N=413; canonical_v1; token-line mapping PASS.
- M1 QLoRA pilot: Stage A 32/32 overfit; Stage B N=2048 natural prevalence; full valid 5465.
- Validation: ROC-AUC≈0.778, PR-AUC≈0.218 (ADEQUATE ranking); hard@0.5 all-negative.
- TEST_INFERENCE_EXECUTED=NO.

# Blockers

- Llama tokenizer ACCESS_BLOCKED (M3 generalization blocked).
- Historical FAIL gates retained.
- Pilot hard threshold 0.5 not useful (scores <0.25); imbalance strategy deferred.

# Decisions frozen

- PRIMARY_RQ1_POLICY=POLICY_A_COMPLETE_CASE; CHANGED_ONLY; max_length 2048; Qwen rev `c03e6d358207…`.
- Label tokens 15/16; restricted two-class softmax; QLoRA NF4 r=16.
- Pilot settings are not claimed optimized hyperparameters.

# Last updated

2026-10-01T11:33:14+02:00

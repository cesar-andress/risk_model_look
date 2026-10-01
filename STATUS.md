# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

TOKEN_LINE_MAPPING_GATE closed **PASS**.  
Next: PILOT_GATE (training) — do not start until explicitly requested.

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
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

PILOT_TRAINING_GATE (not started).

# Completed work

- Frozen PRIMARY_RQ1 = complete-case N=413 (13412/1712/11700).
- Built `canonical_v1` JSONL (27319); deterministic.
- Qwen fast offset mapping 27319/27319; 100/100 sample; label tokens 0/1 single-token.
- Truncation audits 2048/4096 + CTX3.

# Blockers

- Llama tokenizer ACCESS_BLOCKED (M3 generalization blocked).
- Historical FAIL gates retained (document recovery path).
- RQ1_VISIBLE_N_2048=304 / _4096=345 under CHANGED_ONLY (explicit truncation scope).

# Decisions frozen

- PRIMARY_RQ1_POLICY=POLICY_A_COMPLETE_CASE; N=413; ORIGINAL=475; excluded=62 mapping-incomplete.
- CANONICAL_MODEL_INPUT_SOURCE=ordered first-parent Git; CHANGED_ONLY primary; CTX3 ablation; MAX_LENGTH 2048/4096.
- STABLE_LINE_ID_V1 includes ordered_position; CONTEXT_POLICY closed (0 / 3).
- Reconstruction stop rule engaged.

# Last updated

2026-10-01T07:45:00+02:00

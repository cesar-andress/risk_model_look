# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

RQ1_LABEL_UNIVERSE_GATE closed **PASS**.  
POLICY_A_CANONICAL_BRIDGE_GATE closed **FAIL** (18467/18615; producer ABSENT).  
TOKEN_LINE_MAPPING_GATE remains **IN_PROGRESS** — tokenizer offset mapping not started.

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
| TOKEN_LINE_MAPPING_GATE | IN_PROGRESS |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Resolve Policy-A → canonical line-ID residual (148 NOT_FOUND) or obtain orchestrator decision on COMPLETE_POLICY_A subset before tokenization.

# Completed work

- Policy-A bridge audit: paper-faithful Layer-A/Git linkage; 18467 unique maps; 0 collisions; RQ1 mask contract; JIT-Block producer ABSENT documented.
- Prior: JIT-Block audit PASS; RQ1 universe Policy A PASS.

# Blockers

- 148 Policy-A rows without deterministic Git location (1 positive).
- JIT-Block producer absent at `d82cc67…`.
- Historical FAIL gates remain (set EQ / Layer-A→Git incomplete) — do not erase.
- CONTEXT_POLICY OPEN.

# Decisions frozen

- PRIMARY_RQ1_POLICY = POLICY_A; N=475; 18615/2060/16555/0 unknown within universe.
- UNKNOWN / full-Git extras ≠ NEGATIVE (`NOT_IN_RQ1_UNIVERSE`).
- CANONICAL_MODEL_INPUT_SOURCE = ordered first-parent Git reconstruction.
- N=352 and N=58 not primary.

# Decisions pending

- Whether to accept COMPLETE_POLICY_A_COMMIT_COUNT=403 (or other residual policy)
- CONTEXT_POLICY
- Journal selection

# Last updated

2026-10-01T05:30:00+02:00

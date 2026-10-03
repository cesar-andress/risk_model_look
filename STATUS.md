# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

FULL_TRAINING_GATE closed **PASS**. `M1_TEST_LOCKED=TRUE`.  
M1_FREEZE_AND_ATTRIBUTION_GPU_READINESS_GATE = **IN_PROGRESS**.  
ATTRIBUTION_RESULTS_GATE = **NOT_STARTED**.  
VALIDATION_ATTRIBUTION_REHEARSAL = **NOT_STARTED**. Do not start N=64 automatically.

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | PASS |
| TOKEN_LINE_MAPPING_GATE | PASS |
| PILOT_TRAINING_GATE | PASS |
| PILOT_GATE | PASS |
| FULL_TRAINING_GATE | PASS |
| TRAINING_GATE | PASS |
| M1_TEST_LOCKED | TRUE |
| M1_FREEZE_AND_ATTRIBUTION_GPU_READINESS_GATE | IN_PROGRESS |
| ATTRIBUTION_RESULTS_GATE | NOT_STARTED |
| VALIDATION_ATTRIBUTION_REHEARSAL | NOT_STARTED |
| ATTRIBUTION_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Locked M1

- Config hash: `7f51052379822e8261bbd738f164035474029e75c2c1eda997c3f5dcfec418c2`
- Seeds: {13,42,73}; class policy NATURAL_PREVALENCE
- Test ROC-AUC: 0.8088 ± 0.0067
- Test PR-AUC: 0.2489 ± 0.0033
- PERFORMANCE_SANITY_REVIEW_REQUIRED: FALSE

# Last updated

2026-10-03T08:09:02+02:00

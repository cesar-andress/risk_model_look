# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

JITBLOCK_REPLICATION_AUDIT_GATE and RQ1_LABEL_UNIVERSE_GATE closed **PASS**.  
TOKEN_LINE_MAPPING_GATE remains IN_PROGRESS — tokenizer offset mapping not started.  
Primary RQ1 scientifically defensible under Policy A (N=475 labelled universe).

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
| TOKEN_LINE_MAPPING_GATE | IN_PROGRESS |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Proceed to TOKEN_LINE_MAPPING_GATE over Policy A universe (\(U_{\mathrm{JITFINE}}\) labelled added lines on 475 commits), without treating full-Git unknowns as negatives.

# Completed work

- JIT-Block audit: DOI 10.1111/exsy.13702; repo frozen `d82cc67…`; 178 clean exclusions verified; 475/475 positives retained; line-label pickle BYTE_IDENTICAL.
- RQ1 label universe: Policy A N=475 fully labelled; Policy B invalid; Policy C N=58; Policy D IFA/effort invalid.
- Metric guard refuses UNKNOWN for IFA/effort metrics.

# Blockers

- Historical FAIL gates remain (set EQ / Layer-A→Git incomplete) — do not erase.
- Full-Git effort metrics still invalid without Policy C.
- CONTEXT_POLICY OPEN.

# Decisions frozen

- PRIMARY_RQ1_POPULATION_NOMINAL = 475; no predicted-positive conditioning.
- Primary RQ1 evaluation universe = JIT-Fine labelled added-line rows (Policy A).
- CANONICAL_MODEL_INPUT_SOURCE = ordered first-parent Git diff.
- UNKNOWN ≠ NEGATIVE; effort/IFA must refuse UNKNOWN.

# Decisions pending

- CONTEXT_POLICY
- Whether to report Policy C as ablation
- Journal selection

# Last updated

2026-10-01T04:50:00+02:00

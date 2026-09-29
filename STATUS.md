# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

DIFF_RECONSTRUCTION_GATE closed FAIL. TOKEN_LINE_MAPPING_GATE remains IN_PROGRESS — tokenizer offset mapping not started. Escalation required before treating full N=475 as mapped usable.

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
| TOKEN_LINE_MAPPING_GATE | IN_PROGRESS |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Escalate incomplete positive-label mapping (235/475 usable under exact-unique rule). Do not implement `build_dataset.py` or tokenizer mapping until reconstruction strategy is resolved.

# Completed work

- Environment, novelty, provenance, acquisition, schema gates.
- Diff reconstruction audit: Git mirrors for 21 projects; first-parent diffs; set EQ ~32%; line-label map for 475; contracts and report written.
- PRIMARY_RQ1_POPULATION frozen at nominal N=475 without predicted-positive conditioning.

# Blockers

- DIFF_RECONSTRUCTION_GATE FAIL: 308 ambiguous + 294 missing positive label rows; set equivalence incomplete under documented normalization.
- Upstream set representation destroys order/file/hunk/multiplicity.
- CONTEXT_POLICY still OPEN.

# Decisions frozen

- Author split membership frozen (no cross-split commit overlap).
- Commit/line labels are float `{0.0,1.0}`.
- Primary key = commit hash.
- No raw redistribution; extracted pickles and source repos gitignored.
- LOCALIZATION_DENOMINATOR_DECISION: CLOSED (nominal N=475; no predicted-positive conditioning).
- Parent strategy: first_parent.

# Decisions pending

- CONTEXT_POLICY
- Accept subset RQ1 (N=235) vs further extraction reverse-engineering
- ApacheJIT / ReDef secondary corpora
- Journal selection

# Last updated

2026-09-30T00:30:00+02:00

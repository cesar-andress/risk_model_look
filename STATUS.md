# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

DATASET schema validation complete. DATASET_GATE PASS. Next: TOKEN_LINE_MAPPING_GATE (not started).

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | PASS |
| DATASET_PROVENANCE_GATE | PASS |
| DATASET_ACQUISITION_GATE | PASS |
| DATASET_SCHEMA_VALIDATION_GATE | PASS |
| TOKEN_LINE_MAPPING_GATE | NOT_STARTED |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

DATASET_SCHEMA_VALIDATION_GATE closed. Do not implement build_dataset.py until orchestrator opens the next gate.

# Completed work

- Environment, novelty, provenance, acquisition gates.
- Extracted seven JIT-Fine members; static pickle PASS; schema/split/line-label audit complete.
- Empirical profile: 27319 commits / 2332 positives / 21 projects; L0–L4 measured.

# Blockers

- LOCALIZATION_DENOMINATOR_DECISION still OPEN.
- Change lines stored as sets (order not preserved) — mapping design needed next.
- Line-label artifact covers test positives only.

# Decisions frozen

- Author split membership frozen (no cross-split commit overlap).
- Commit/line labels are float `{0.0,1.0}`.
- Primary key = commit hash.
- No raw redistribution; extracted pickles gitignored.

# Decisions pending

- LOCALIZATION_DENOMINATOR_DECISION
- Line-order / file-path recovery strategy for explanations
- ApacheJIT / ReDef secondary corpora
- Journal selection

# Last updated

2026-09-30T00:05:00+02:00

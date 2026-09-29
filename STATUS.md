# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

DATASET acquisition complete (archive frozen, unextracted). Next: DATASET_SCHEMA_VALIDATION_GATE.

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | IN_PROGRESS |
| DATASET_PROVENANCE_GATE | PASS |
| DATASET_ACQUISITION_GATE | PASS |
| DATASET_SCHEMA_VALIDATION_GATE | NOT_STARTED |
| TOKEN_LINE_MAPPING_GATE | NOT_STARTED |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

DATASET_ACQUISITION_GATE closed. Do not open schema validation until orchestrator starts that gate.

# Completed work

- Environment bootstrap + Qwen 4-bit smoke.
- Novelty audit (NOVELTY_GATE PASS).
- Dataset provenance freeze (DATASET_PROVENANCE_GATE PASS).
- Downloaded and verified `data/raw/upstream/data.zip` (size + Git blob SHA-1 + SHA-256/512 + ZIP integrity/path-safety + inventory).
- Acquisition script + unit tests; full pytest PASS.

# Blockers

- Schema/pickle inspection not started (intentional).
- Dataset/code redistribution license NOT_ESTABLISHED.

# Decisions frozen

- Separate code and paper roots.
- ENVIRONMENT / NOVELTY / DATASET_PROVENANCE gates remain PASS (not reopened).
- Local archive path: `data/raw/upstream/data.zip`; SHA-256 `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`.
- No raw redistribution; archive unextracted; no pickle executed at acquisition.

# Decisions pending

- Controlled extraction + schema validation protocol.
- Whether to include ApacheJIT / ReDef as secondary corpora.
- Journal selection.
- Public release timing.

# Last updated

2026-09-29T23:53:00+02:00

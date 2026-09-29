# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

These roots are independent artifacts of the same study. The manuscript is not inside the replication repository.

# Current phase

T0/T1 — bootstrap and environment (**acceptance checks executed**)

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | UNRESOLVED |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | NOT_STARTED |
| TOKEN_LINE_MAPPING_GATE | NOT_STARTED |
| PILOT_GATE | NOT_STARTED |
| TRAINING_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Current task

Bootstrap acceptance criteria: **completed for ENVIRONMENT_GATE**.

Remaining hard stop before scientific experiments: resolve NOVELTY_GATE with a dated auditable literature-search report; then dataset provenance / token–line mapping gates.

# Completed work

- Inspected both roots; preserved pre-existing code README and nested git history.
- Created repository scaffold (`configs/`, `data/`, `docs/`, `results/`, `scripts/`, `src/*`, `tests/`, `artifacts/`).
- Added hygiene `.gitignore`, `README.md`, `REPRODUCE.md`, protocol/ledger/gate docs.
- Created `environment.yml` + uv fallback `.venv` (conda/mamba absent).
- `pytest -q` PASS.
- `scripts/smoke_qwen_4bit.py` PASS on RTX 4090 (genuine 4-bit NF4 Qwen2.5-Coder-7B-Instruct).
- Minimal LaTeX scaffold under paper root; optional compile succeeded.
- Recorded `docs/ENVIRONMENT_REPORT.md`.

# Blockers

- NOVELTY_GATE remains UNRESOLVED (conflicting project-note states; no auditable search report provided to this agent).
- JIT-Defects4J authoritative URL / schema / label semantics / JIT-Fine split: still TO VERIFY.
- Do not start training or attribution until novelty + dataset gates clear.

# Decisions frozen

- Separate code and paper roots.
- No dataset download in bootstrap.
- Novelty not marked verified.
- No journal template lock.
- No public push/release in this phase.
- No scientific attribution/training implementation yet.

# Decisions pending

- Novelty gate resolution by orchestrator.
- Dataset provenance and redistribution rights.
- Final class-imbalance training strategy (validation-only).
- Journal selection.
- Public GitHub/Zenodo release timing.

# Last updated

2026-09-29T23:24:30+02:00

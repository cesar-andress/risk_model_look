# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

T0/T1 complete for environment; novelty audit complete. Next: dataset provenance gate (not started).

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
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

NOVELTY_GATE audit acceptance criteria executed. Do not advance DATASET_GATE in this task.

# Completed work

- Environment bootstrap + Qwen 4-bit smoke (prior task).
- Systematic literature search log (Crossref, OpenAlex, arXiv, Semantic Scholar, DBLP, publisher/conference pages, Zenodo replication inspection).
- Screening table for C1–C10 and near candidates.
- Collision matrix + novelty map; faithfulness and architecture typologies separated.
- Jacobian Scopes IG-baseline claim verified as PARTIAL/YES in LLM next-token setting.
- Provisional novelty claim narrowed; broad “first …” framing dropped.

# Blockers

- JIT-Defects4J authoritative URL / schema / label semantics / JIT-Fine split still TO VERIFY (DATASET_GATE).
- JITEC full-text access incomplete (does not overturn PASS, but leaves UNKNOWN cells).

# Decisions frozen

- Separate code and paper roots.
- ENVIRONMENT_GATE remains PASS (not reopened).
- Novelty framing must use compositional / intersection claim, not unqualified primacy.
- XMENTOR “sign agreement” is not treated as equivalent to RQ3 D/E.
- CoScoreX EASE transformer paper and CoScoreX ICSME RF paper are distinct studies.

# Decisions pending

- Dataset provenance and redistribution rights.
- Whether to include ApacheJIT / ReDef as secondary corpora.
- Journal selection.
- Public release timing.

# Last updated

2026-09-29T23:45:00+02:00

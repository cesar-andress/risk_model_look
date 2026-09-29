# DECISION_LOG.md

Non-trivial bootstrap decisions. Format: datetime | decision | reason | alternatives | reversible | gate affected.

---

## 2026-09-29T23:18:00+02:00 — Separate code and paper roots

- **Decision:** Keep replication code at `/home/cesar/papers/risk_model_look/risk_model_look` and manuscript at `/home/cesar/papers/risk_model_look/paper` without nesting or symlinks.
- **Reason:** Public replication hygiene; manuscript LaTeX must not ship inside the software/data repo by default.
- **Alternatives considered:** Single monorepo with `paper/`; symlink between roots.
- **Reversible:** Yes, with explicit later decision.
- **Gate affected:** RELEASE_GATE, PAPER_GATE

## 2026-09-29T23:18:00+02:00 — No dataset download yet

- **Decision:** Do not download JIT-Defects4J or any other dataset during bootstrap.
- **Reason:** Authoritative URL, schema, label semantics, and split files are TO VERIFY; license/redistribution unknown.
- **Alternatives considered:** Partial download “for exploration.”
- **Reversible:** Yes.
- **Gate affected:** DATASET_GATE

## 2026-09-29T23:18:00+02:00 — Novelty gate unresolved

- **Decision:** Record NOVELTY_GATE as UNRESOLVED despite conflicting project-note statements.
- **Reason:** No dated auditable literature-search report is available to this execution agent; task forbids declaring novelty.
- **Alternatives considered:** Treat plan date 2026-09-29 as verification (rejected).
- **Reversible:** Yes, when orchestrator supplies the report.
- **Gate affected:** NOVELTY_GATE

## 2026-09-29T23:18:00+02:00 — No journal template selected

- **Decision:** Use a minimal generic `article` LaTeX scaffold in the paper root.
- **Reason:** Journal selection (IST/JSS/EMSE/other) is deferred.
- **Alternatives considered:** elsarticle / Springer class premature lock-in.
- **Reversible:** Yes.
- **Gate affected:** PAPER_GATE

## 2026-09-29T23:18:00+02:00 — No GitHub/Zenodo release in this phase

- **Decision:** Do not create releases, Zenodo deposits, or DOIs; do not push.
- **Reason:** Bootstrap only; release hygiene gate not started. Existing remote (if any) is left untouched and unused for push in this task.
- **Alternatives considered:** Push bootstrap commit to origin (rejected by task/workspace policy for this phase).
- **Reversible:** Yes later under RELEASE_GATE.
- **Gate affected:** RELEASE_GATE

## 2026-09-29T23:18:00+02:00 — No scientific experiment implementation yet

- **Decision:** Source packages remain placeholders; only structure tests and a 4-bit load smoke script are allowed.
- **Reason:** Novelty unresolved; dataset/protocol facts TO VERIFY; task prohibits attribution/training/metrics code.
- **Alternatives considered:** Stub metric APIs (rejected as premature).
- **Reversible:** Yes after gates clear.
- **Gate affected:** XAI_GATE, TRAINING_GATE, ANALYSIS_GATE

## 2026-09-29T23:18:00+02:00 — Environment tool: uv + venv fallback

- **Decision:** Provide `environment.yml` for conda/mamba reproducibility, but create the working environment with `uv` + Python 3.11 `.venv` because conda/mamba were absent at inspection.
- **Reason:** Machine had `uv` and system Python 3.10/3.11/3.12; default `python3` on PATH was unusable (3.6 / segfaulting pip).
- **Alternatives considered:** Install miniconda without explicit request (deferred); use system Python 3.6 (impossible for stack).
- **Reversible:** Yes (can recreate with conda later from `environment.yml`).
- **Gate affected:** ENVIRONMENT_GATE

## 2026-09-29T23:18:00+02:00 — Ignore raw data by default

- **Decision:** `.gitignore` excludes `data/raw/**` while retaining `.gitkeep`.
- **Reason:** Do not assume JIT-Defects4J license permits redistribution.
- **Alternatives considered:** Commit sample raw slices (rejected).
- **Reversible:** Yes after license verification and explicit release decision.
- **Gate affected:** DATASET_GATE, RELEASE_GATE

## 2026-09-29T23:24:30+02:00 — ENVIRONMENT_GATE marked PASS after executed checks

- **Decision:** Set ENVIRONMENT_GATE=PASS after `pytest -q` and `scripts/smoke_qwen_4bit.py` both exited 0 on this host.
- **Reason:** Acceptance criteria require executed checks, not aspirational docs.
- **Alternatives considered:** Leave PENDING despite PASS logs (rejected).
- **Reversible:** Yes if a later machine fails the same smoke.
- **Gate affected:** ENVIRONMENT_GATE

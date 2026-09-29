# risk_model_look

Replication package (code, configs, scripts, reproducible results) for the empirical study:

**Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction**

## What this repository is

Public-facing research infrastructure for training and evaluating explanation methods on decoder-only LLM commit-risk classifiers.

## What this repository is not

- It is **not** the manuscript source. Manuscript LaTeX lives in a separate path: `../paper/` (sibling of this repository root under the study workspace).
- It does **not** redistribute raw datasets by default (`data/raw/` is gitignored). Dataset license and redistribution rights are **TO VERIFY**.
- It does **not** yet contain scientific experiment implementations beyond environment/plumbing smoke tests.

## Current phase

`T0/T1` — bootstrap and environment. See `STATUS.md`.

## Hard gates (do not skip)

| Gate | Status (see STATUS.md) |
|------|------------------------|
| Novelty | UNRESOLVED |
| Environment | PENDING until smoke tests pass |
| Dataset | NOT_STARTED |
| Token–line mapping | NOT_STARTED |

## Quick start (after environment is ready)

1. Read `STATUS.md` and `docs/NOVELTY_GATE.md`.
2. Create the Python environment from `environment.yml` (conda/mamba) **or** the documented `uv`/venv fallback in `docs/ENVIRONMENT_REPORT.md`.
3. Run plumbing tests: `pytest -q`
4. Run GPU smoke (target machine with NVIDIA GPU): `python scripts/smoke_qwen_4bit.py`

## Reproduction notes

See `REPRODUCE.md`. Scientific protocols (pre-experimental) are in `docs/EXPERIMENT_PROTOCOL_V0.md`.

## Integrity

Unknown facts remain UNKNOWN / TODO / TO VERIFY. Do not invent dataset statistics, DOIs, results, or novelty claims.

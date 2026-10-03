# ZENODO_RELEASE_PLAN.md

**Status:** preparation only — **no DOI created, no upload**.  
**Date:** 2026-10-01

---

## Archive contents (planned)

### YES (include)

- Source code (`src/`, `scripts/`, `tests/`)
- Configs (`configs/`)
- Documentation (`docs/`, `README.md`, `REPRODUCIBILITY.md`)
- Protocol freeze manifests + SHA-256 digests
- Small CSV/JSON audit summaries already tracked under `artifacts/**` (non-weight)
- Paper LaTeX sources (after integration) + TBD macros
- Result **tables/aggregates** after evaluation completes (not raw per-token dumps)

### NO (exclude)

- `data/raw/**` if redistribution prohibited / unverified (default)
- Full `data/processed/**` blobs (JSONL, pkl caches)
- Model base weights (Qwen) — re-download from upstream revision pin
- LoRA adapters / checkpoints (`.safetensors`) unless license + size explicitly approved
- Secrets, `.env`, API keys
- Agent/tooling dirs (`.cursor/`, etc.)
- Training logs / wandb

---

## Metadata draft (placeholders)

| Field | Draft |
|-------|-------|
| Title | Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction — Replication Package |
| Creators | César Andrés (ORCID 0009-0001-8968-3404) — confirm coauthors before deposit |
| Description | Code, configs, protocols, and reproducibility materials for evaluating line-level attributions of a decoder-only JIT defect-risk classifier on public JIT-Defects4J / JIT-Fine resources. Raw dataset redistributed only as permitted by upstream licenses. |
| Keywords | just-in-time defect prediction; explainable AI; faithfulness; Integrated Gradients; large language models; software engineering |
| Related publication | TBD (DOI of paper when available) |
| License | TBD — prefer permissive code license (MIT/Apache-2.0) after legal check; dataset remains under upstream terms |
| Version | v0.1.0-pre-results (draft) |

**Do not invent a Zenodo DOI.**

---

## Pre-upload checklist

- [ ] `main` contains attribution V1.2 + stats V1.1 + training entrypoints
- [ ] Large-file audit clean for tracked paths
- [ ] LICENSE chosen and added
- [ ] CITATION.cff filled
- [ ] Dataset redistribution statement verified
- [ ] Results frozen (post-experiment) or clearly marked pre-results
- [ ] Owner approval for public visibility

---

## Upload action

**Not performed.** Requires separate owner-authorized gate.

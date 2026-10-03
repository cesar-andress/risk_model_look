# GITHUB_RELEASE_PLAN.md

**Status:** preparation only — **no push, no GitHub Release created**.  
**Date:** 2026-10-01  
**Remote:** `git@github.com-ucjc:cesar-andress/risk_model_look.git`

---

## Current remote state

- `origin/main` still at bootstrap `1475896`
- Local `main` is **12 commits ahead** (dataset/model gates) + dirty training WIP
- `parallel/attribution-infra` is **7 commits ahead of local main**

Public GitHub does **not** yet reflect the scientific infrastructure built locally.

---

## Proposed release sequence (owner-approved)

1. Complete M1 training; commit safe entrypoints/manifests on `main`.
2. Fast-forward merge `parallel/attribution-infra` into `main` (`MERGE_PLAN.md`).
3. Optional: integrate `paper/` (`PAPER_INTEGRATION_PLAN.md`).
4. Tag annotated pre-results freeze, e.g. `v0.1.0-pre-results` (local first).
5. `git push origin main` **only when owner authorizes** (this hygiene gate forbids push).
6. Create GitHub Release from that tag with notes linking Zenodo (when DOI exists).

---

## Release notes skeleton

```
## risk_model_look vX.Y.Z

### Included
- Dataset provenance + Policy A bridging
- M1 Qwen QLoRA training entrypoints
- Attribution Protocol V1.2 + Statistical Protocol V1.1
- CPU tests for metrics/protocols

### Not included
- Raw JIT-Defects4J redistribution (acquire via documented scripts)
- Model adapters / base weights
- Final empirical result tables (if still TBD)
```

---

## Branch policy after release prep

- Development tip: `main`
- Keep `parallel/attribution-infra` until FF verified, then archive/delete **only with owner approval**
- Avoid long-lived feature branches unless needed

---

## Explicit non-actions in this gate

- No `git push`
- No GitHub Release UI/API call
- No force-push
- No rewriting `origin/main` history

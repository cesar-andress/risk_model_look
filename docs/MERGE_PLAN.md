# MERGE_PLAN.md

**Status:** PLAN ONLY — **human approval required** before any merge.  
**Date:** 2026-10-01  
**Destructive actions:** none performed.

---

## Commit graph (simplified)

```
* 678034d parallel/attribution-infra  docs: N8 Liang ledger
* 3fa90de  tag: pre-attribution-protocol-v1.2
* 5afac7d  Claude design review archive
* e063904  Freeze statistical protocol
* 10b69e3  Attribution V1.1
* ce0785d  Freeze attribution protocol
* 0c136ab  Attribution + RQ infra
* 9c93eaa  main  Validate Qwen M1 QLoRA training pipeline
* 373db91  Canonical dataset + token-line mapping
* … dataset provenance chain …
* 1475896  origin/main  first commit
```

Merge-base(`main`, `parallel/attribution-infra`) = **`9c93eaa`** (= current `main` tip).

---

## Candidate merge strategy (recommended)

### Phase 0 — wait for training (BLOCKING)

1. Let `run_m1_final.py` finish or reach a safe checkpoint.
2. Do **not** `git checkout`, `reset`, or clean `artifacts/m1_final/` meanwhile.

### Phase 1 — freeze training artifacts on `main` (owner-approved)

Small commits on `main` only, e.g.:

1. `gitignore: keep m1_final adapters and result dumps out of git`
2. `Add M1 final training entrypoints and configs` (scripts/configs/tests only)
3. `Record M1 final training status / hashes` (manifests, not weights)

**Exclude from Git:** adapter weights, encoded caches, raw dumps (already intended by `.gitignore`).

### Phase 2 — integrate parallel (preferred: fast-forward)

```bash
# ONLY after main working tree clean:
cd risk_model_look
git merge --ff-only parallel/attribution-infra
```

**Expected conflicts:** **none** for committed content (FF).  
**Residual risk:** uncommitted local edits on `main` that overlap parallel paths (currently: `.gitignore`, `STATUS.md`, `docs/DECISION_LOG.md`, `docs/EXPERIMENT_PROTOCOL_V0.md`, `src/models/qwen_m1.py`, `src/eval/classification_metrics.py`). Resolve these **before** FF by committing or stashing with owner review.

### Phase 3 — retain branch

Keep `parallel/attribution-infra` until:

- FF verified;
- `pytest` (CPU) green on integrated `main`;
- freeze tag `pre-attribution-protocol-v1.2` still reachable from `main`.

**Do not delete** the branch until the above checklist passes.

---

## Alternative if FF blocked

`git merge parallel/attribution-infra` (non-FF) only if new commits appear on `main` after `9c93eaa` that are not ancestors of parallel. Then resolve conflicts file-by-file; prefer parallel for attribution/stats, prefer main for training.

Cherry-pick list (if merge deferred): the 7 SHAs above, in order `0c136ab` → `678034d`.

---

## Files affected (summary)

| Family | Action |
|--------|--------|
| `src/attribution/**`, metrics, stats, cohorts, experiments | add from parallel |
| `configs/attribution|stats|validation/**` | add |
| protocol docs + freeze artifacts | add |
| tests/test_*attribution* / stats | add |
| `.gitignore` | **manual combine** main (m1_final) + parallel (attribution results) |
| training scripts on main (uncommitted) | commit on main first |

---

## Conflicts expected

| Area | Likelihood | Notes |
|------|------------|-------|
| Committed tree FF | Low / none | parallel strictly ahead |
| Dirty `.gitignore` | Medium | both sides edited; combine rules |
| Dirty `STATUS.md` / decision log | Medium | narrative merge |
| Dirty `qwen_m1.py` / metrics | Medium | training edits vs parallel untouched copies — commit training side first |

---

## Recommended order

1. Finish / safely stop needing live edits from training.
2. Commit training-side hygiene on `main` (small commits).
3. `git merge --ff-only parallel/attribution-infra`.
4. Run CPU `pytest -q` (no GPU / no Qwen load beyond existing unit stubs).
5. Draft paper integration (separate plan) — **not** part of this merge.
6. Only then consider retiring the parallel **worktree directory** (keep branch tag).

---

## Explicit non-goals for this plan

- No `git push`
- No history rewrite
- No deleting `parallel/attribution-infra`
- No moving paper yet
- No Zenodo upload

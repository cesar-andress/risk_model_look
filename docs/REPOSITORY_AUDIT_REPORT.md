# REPOSITORY_AUDIT_REPORT.md

**Audit date:** 2026-10-01  
**Mode:** read-only audit (no merges, no deletes, no pushes)  
**Active training:** PID 2454911 `scripts/run_m1_final.py` in `risk_model_look/` worktree — **untouched**

---

## A. Repositories detected

| Path | Role |
|------|------|
| `/home/cesar/papers/risk_model_look/risk_model_look` | Primary code Git worktree (`main`) |
| `/home/cesar/papers/risk_model_look/risk_model_look_parallel` | Linked Git worktree (`parallel/attribution-infra`) |
| `/home/cesar/papers/risk_model_look/paper` | Manuscript sources (tracked in **papers monorepo**, not in code Git) |
| `/home/cesar/papers` | Parent monorepo hosting `risk_model_look/paper` |
| `/home/cesar/papers/risk_model_look/` | Workspace wrapper (no `.git` of its own) |

Shared remote for code worktrees: `git@github.com-ucjc:cesar-andress/risk_model_look.git`

---

## B. Git roots

1. **Code repo:** `risk_model_look/.git` with worktrees:
   - `.../risk_model_look` → `main`
   - `.../risk_model_look_parallel` → `parallel/attribution-infra`
2. **Papers monorepo:** `/home/cesar/papers/.git` → branch `paper/pre-results-draft` (contains paper path)

---

## C. Branches (code repo)

| Branch | Location | Notes |
|--------|----------|-------|
| `main` | primary worktree | 12 commits ahead of `origin/main` |
| `parallel/attribution-infra` | parallel worktree | 7 commits ahead of `main` |
| `origin/main` | remote | at bootstrap tip `1475896` |

No other local branches listed.

Papers monorepo branch of interest: `paper/pre-results-draft`.

---

## D. Current HEAD commits

| Ref | SHA |
|-----|-----|
| `main` | `9c93eaab01882fa3c3ea997854fa2d01a4ee14de` |
| `parallel/attribution-infra` | `678034d684f4ec209c9f68b130f9706c80af00b3` |
| `origin/main` | `1475896` (first commit) |
| papers `paper/pre-results-draft` | `7ae4bb286` (SOTA refresh) |

**Merge-base(`main`, `parallel/attribution-infra`) = `9c93eaa` = current `main` HEAD.**  
Therefore parallel is a **strict fast-forward candidate** onto `main` (once `main` working tree is clean / training-safe).

---

## E–G. Dirty working trees / uncommitted changes

### `main` worktree — **DIRTY** (training in progress)

Modified:

- `.gitignore`, `STATUS.md`, `docs/DECISION_LOG.md`, `docs/EXPERIMENT_PROTOCOL_V0.md`
- `src/eval/classification_metrics.py`, `src/models/qwen_m1.py`

Untracked (training-related — **do not disturb**):

- `artifacts/m1_final/`
- `configs/train/qwen_m1_final.yaml`
- `scripts/finalize_m1_full_training_gate.py`
- `scripts/run_m1_final.py`
- `src/train/m1_final.py`
- `tests/test_m1_final.py`

### `parallel/attribution-infra` worktree — **CLEAN** (at audit start)

### Papers monorepo — unrelated dirty paths under `earnbench/` (out of scope)

---

## F. Remotes

| Repo | Remote |
|------|--------|
| code | `origin` → `git@github.com-ucjc:cesar-andress/risk_model_look.git` |
| papers | **no push remote configured** (local monorepo policy) |

---

## H. Relationship among branches

```
origin/main (1475896)
    └── … dataset/model gates …
            └── main / 9c93eaa  ←── training worktree (DIRTY)
                    └── parallel/attribution-infra / 678034d
                          (7 commits: attribution V1→V1.2, stats V1.1, reviews, ledger N8)
```

**Paper** is **not** a branch of the code repo. It lives under `/home/cesar/papers` on `paper/pre-results-draft` and currently references code protocols by hash/path documentation only.

---

## I. Files only in parallel (vs main)

~105 paths added on `main...parallel` (selected families):

- `src/attribution/**`, `src/metrics/{faithfulness,localization,polarity,...}.py`
- `src/stats/**`, `src/cohorts/**`, `src/experiments/**`
- `configs/attribution/**`, `configs/stats/**`, `configs/validation/**`
- `docs/ATTRIBUTION_PROTOCOL_V1*.md`, `docs/STATISTICAL_ANALYSIS_PROTOCOL_V1*.md`
- `artifacts/attribution_protocol/**`, `artifacts/statistical_protocol/**`, freeze bundle
- CPU tests for protocols/metrics

## J. Files only in main (vs parallel tip)

**None in committed history** (`main` ⊆ ancestor of parallel).  
**Uncommitted / untracked on main only:** M1 final training scripts, configs, adapters under `artifacts/m1_final/`.

## K. Differing files (committed)

7 modified paths on the parallel side (mostly docs/STATUS/gitignore deltas). Full diffstat: **112 files, +12176 / −59**.

---

## Immediate hygiene implications

1. **Do not merge** while `main` is dirty and M1 training is writing `artifacts/m1_final/`.
2. After training: commit M1 final plumbing on `main`, then **fast-forward** `main` to `parallel/attribution-infra` (or merge `--ff-only`).
3. Paper integration is a **separate** monorepo→code-repo import plan (see `PAPER_INTEGRATION_PLAN.md`).
4. Keep `parallel/attribution-infra` until fast-forward verified and unique value confirmed integrated.

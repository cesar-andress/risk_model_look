# GITIGNORE_AUDIT.md

**Date:** 2026-10-01  
**Refs compared:** dirty `main` worktree `.gitignore` vs committed parallel `.gitignore`

---

## Already covered (good)

- Agent tooling (`.cursor/`, `.claude/`, …)
- Secrets (`.env`, keys, credentials)
- Python caches / venvs
- HF caches; `*.safetensors` / `*.bin` / `*.pt`
- wandb / mlruns
- `data/raw/**`, `data/processed/**` with `.gitkeep` exceptions
- Archives `*.zip` / `*.tar*`

## Gaps / combine-on-merge items

| Topic | main (dirty) | parallel | Recommendation |
|-------|--------------|----------|----------------|
| `artifacts/m1_final/adapters/` | present | missing | **Keep main rules** on merge |
| blanket `data/results/` ignore | present | replaced by attribution-specific allowkeep | Prefer parallel’s finer `data/results/attribution/**` + keep ignoring other result dumps |
| LaTeX build products | absent | absent | **Add** `*.aux`, `*.bbl`, `*.blg`, `*.fdb_latexmk`, `*.fls`, `*.synctex.gz`, `paper/**/*.pdf` (or `paper/main.pdf`) before paper import |
| `CITATION.cff` / `LICENSE` | n/a | n/a | do not ignore |
| Protocol hash JSON | tracked | tracked | do not ignore |

## Must NOT exclude

- `src/`, `configs/`, `tests/`, `docs/`
- Small manifests under `artifacts/**` (acquisition digests, protocol freeze)
- `generated/result_macros.tex` once paper is imported

## Action in this hygiene gate

Documentation only — **no `.gitignore` write on the training worktree**.
Apply combined rules in the post-training commit on `main` before FF merge.

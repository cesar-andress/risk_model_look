# PAPER_INTEGRATION_PLAN.md

**Status:** PLAN ONLY — **do not move paper yet**.  
**Date:** 2026-10-01

---

## Current state

| Item | Value |
|------|-------|
| Paper path | `/home/cesar/papers/risk_model_look/paper` |
| Git home | `/home/cesar/papers` monorepo |
| Branch | `paper/pre-results-draft` |
| HEAD (audit) | `7ae4bb286` |
| Own `.git`? | **No** |
| Code repo awareness | README says manuscript is sibling `../paper/` |

Preferred end state (target):

```
risk_model_look/   # code Git root
  paper/
    main.tex
    sections/
    tables/
    figures/
    refs.bib
    docs/
  src/ configs/ scripts/ tests/ docs/ ...
```

---

## Audit findings

### History

- Paper history lives in the **papers monorepo**, interleaved with other projects.
- Importing via `git subtree` / filter-repo can preserve paper commits but requires careful path filtering (`risk_model_look/paper/**` → `paper/**`).
- Simpler alternative: snapshot import (lose monorepo history) + keep monorepo as archival mirror — **owner choice**.

### References / relative paths

- LaTeX uses relative `\input{sections/...}`, `\bibliography{refs}` — portable if whole `paper/` tree moves intact.
- Docs cite protocol hashes (Attribution V1.2 / Stats V1.1) — independent of filesystem once code is merged.
- Code README currently points to `../paper/` — must update after move.

### Build scripts

- `paper/scripts/check_paper_placeholders.py`
- Build: `pdflatex` + `bibtex` (no Makefile yet)
- Generated: `main.pdf`, `main.aux`, `*.fls`, etc. — must stay **gitignored** in code repo

### Generated artifacts to exclude on import

```
paper/main.pdf
paper/main.aux paper/main.bbl paper/main.blg
paper/main.fdb_latexmk paper/main.fls paper/main.log paper/main.out
```

Keep: `generated/result_macros.tex` (TBD macros are source-of-truth placeholders).

---

## Recommended integration procedure (after owner approval)

1. Ensure attribution/stats FF into code `main` completed.
2. Decide history strategy: **subtree filter** vs **snapshot**.
3. Add `paper/` to code repo `.gitignore` exceptions carefully; ignore LaTeX build products.
4. Copy or subtree-add sources.
5. Update code `README.md` / `REPRODUCIBILITY.md` paper-build section.
6. Optionally keep papers monorepo path as a thin pointer README (“canonical tree moved”).
7. Verify `pdflatex` build from `risk_model_look/paper`.
8. Do **not** push until release gate.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Monorepo still edited in parallel | Freeze paper branch or dual-commit policy until cutover |
| Public release hygiene | Keep `.cursor/`, agent configs out of code repo (already gitignored) |
| Premature result macros | Leave TBD; submission mode must fail while TBD remain |

---

## Decision required from owner

- [ ] Preserve full paper git history via filter/subtree?
- [ ] Or snapshot import + archive monorepo history?
- [ ] Timing: before vs after M1 results land?

**No move performed in this hygiene pass.**

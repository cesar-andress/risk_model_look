# REPOSITORY_FINAL_STATE.md

**Hygiene gate date:** 2026-10-01  
**Merges performed:** none  
**Pushes performed:** none  
**Training disturbed:** no

---

## Target final structure (desired)

```
~/papers/risk_model_look/
  risk_model_look/          # ONE git root, branch main
    .git/
    src/ configs/ scripts/ tests/ docs/ artifacts/
    paper/                  # after approved integration
    README.md LICENSE CITATION.cff REPRODUCIBILITY.md
  data/                     # optional workspace data outside git
    raw/ processed/
```

**Current reality differs:** two worktrees + paper in papers monorepo.

---

## Current tree (workspace)

```
risk_model_look/                 # wrapper (no .git)
  plan_paper_jit_explicaciones.md
  paper/                         # papers monorepo path
  risk_model_look/               # worktree main @ 9c93eaa (DIRTY; training)
  risk_model_look_parallel/      # worktree parallel/attribution-infra @ 678034d+
```

---

## Branches / HEADs (after this hygiene doc commit on parallel)

| Ref | Role | Dirty? |
|-----|------|--------|
| `main` @ `9c93eaa` | training + dataset history | YES (M1 final WIP) |
| `parallel/attribution-infra` @ `7431a59` | attribution V1.2 + stats V1.1 + hygiene docs | clean after hygiene commits |
| `origin/main` @ `1475896` | remote lagging | — |
| papers `paper/pre-results-draft` @ `7ae4bb286` | manuscript | — |

---

## Tests run this gate

**None** (no integration executed; GPU/Qwen load forbidden; training isolation prioritized).

## Paper build this gate

**Not re-run** (paper untouched scientifically; last known build was 21 pages at SOTA refresh).

---

## Release readiness

| Item | Status |
|------|--------|
| Structure understood | YES |
| Merge plan | YES (`docs/MERGE_PLAN.md`) |
| Paper integration plan | YES (not moved) |
| Zenodo plan | YES (no DOI) |
| GitHub release plan | YES (no push) |
| Large-file audit | YES |
| CITATION.cff | YES (draft) |
| REPRODUCIBILITY.md | YES (pre-results honest) |
| LICENSE | **MISSING** (blocker for public release) |
| Single `main` with attribution | **NOT YET** (await training + FF) |
| Paper inside code repo | **NOT YET** |

**Overall:** hygiene **planning PASS**; release **NOT READY**.

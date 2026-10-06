# PUBLIC_ARTIFACT_AUDIT.md

Date: 2026-10-06  
Task: SUPERPROMPT 34 — final release candidate  
Public candidate HEAD: `ed01acc7dba490a18023d84ede531e844a86533d` (content RC `9cb86a8`)

## Scope

- **Current tracked tree:** full `git ls-files` scan for secret/credential patterns
- **Git history:** `git grep` over recent commits for private-key / token patterns
- **Release-tree hygiene:** see `docs/PUBLIC_RELEASE_TREE_MANIFEST.md`

## Checks

| Check | Result |
|-------|--------|
| Secrets / credentials (tracked tree) | **0** findings |
| Secrets / credentials (history sample patterns) | **0** findings |
| Raw third-party dataset redistribution | **NO** (`data/raw/**` gitignored except README/`.gitkeep`) |
| Model weights / LoRA adapters tracked | **NO** |
| Manuscript TeX/PDF in public repo | **NO** |
| Fake / placeholder DOI | **NO** (real Zenodo DOI `10.5281/zenodo.23196604` verified) |
| Accidental large tracked blobs (>5 MiB) | **NO** |
| Stale root `STATUS.md` / `REPRODUCE.md` | **REMOVED** |
| Internal venue/attack/process docs | **REMOVED** (manifest) |
| Version metadata | **1.0.0** / date **2026-10-06** / DOI **10.5281/zenodo.23196604** (concept **10.5281/zenodo.23196603**) |
| License | **MIT** (scoped; see README + `THIRD_PARTY_NOTICES.md`) |
| Freeze JSON rewritten | **NO** |
| Fresh-clone env from `environment.yml` | see `FRESH_CLONE_REPRODUCTION_REPORT.md` |

## Expected release exclusions

Raw JIT dumps, base weights, adapters, caches, `.env`, and private manuscript sources remain out of the public tree.

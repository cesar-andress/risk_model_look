# PUBLIC_ARTIFACT_AUDIT.md

Date: 2026-10-06  
Task: SUPERPROMPT 33 — MIT license scoping (pre-release; no tag/Zenodo)  
Public HEAD: see git after commit on `main`

## Checks

| Check | Result |
|-------|--------|
| Secrets / credentials in tracked files | NONE found in release-facing README/CITATION/.zenodo/LICENSE |
| Raw third-party dataset redistribution | NO (`data/raw/**` gitignored; only `.gitkeep` + README tracked) |
| Model weights / LoRA adapters tracked | NO (`*.safetensors` gitignored; none in `git ls-files`) |
| Manuscript TeX/PDF in public repo | NO (private sibling `../paper/`) |
| Fake / placeholder DOI | NO (`CITATION.cff` / `.zenodo.json` have no DOI) |
| Large accidental caches staged | NO |
| Localhost-only reproduction dependency | NO (headline printer uses tracked JSON) |
| Freeze hash documentation | YES (README: scientific `885540b8…` vs file-byte `aff72921…`) |
| License (author-owned software) | **MIT** (`LICENSE`); scope documented in README + `THIRD_PARTY_NOTICES.md` |
| Zenodo record license | `mit` — honest for planned software-only deposit excluding raw data/weights/manuscript |
| Mixed-license metadata conflict | NO (payload scoped; exclusions documented) |
| Fresh-clone headline path | PASS (see `FRESH_CLONE_REPRODUCTION_REPORT.md`) |
| Non-GPU tests | see FRESH_CLONE report / this gate run |

## Licensing scope (summary)

- MIT covers author-owned software and tracked author-owned compact result artifacts.
- Upstream JIT-Fine / JIT-Defects4J dumps are **not** redistributed and **not** relicensed.
- Third-party model weights and dependencies remain under upstream terms.
- Manuscript is **not** under MIT.

# ZENODO_RELEASE_PLAN.md

**Status:** **PUBLISHED** — GitHub tag `v1.0.0` archived via Zenodo.  
**Updated:** 2026-10-06

---

## Published identifiers (authoritative)

| Field | Value |
|-------|-------|
| Version | `1.0.0` |
| Git tag | `v1.0.0` |
| Zenodo version DOI | **10.5281/zenodo.23196604** |
| Zenodo concept DOI | **10.5281/zenodo.23196603** |
| Landing page | https://doi.org/10.5281/zenodo.23196604 |
| GitHub | https://github.com/cesar-andress/risk_model_look |
| License (record) | MIT (author-owned software + tracked compact artifacts) |

Use the **version DOI** when citing this release. Use the **concept DOI** only when citing the series of all versions.

---

## License scope (unchanged)

| Scope | License |
|-------|---------|
| Author-owned software | **MIT** |
| Tracked author-owned compact result artifacts | **MIT** |
| Upstream JIT-Fine / JIT-Defects4J raw dumps | **Not redistributed; not relicensed** |
| Third-party model weights / dependencies | Upstream licenses |
| Manuscript / publisher article | **Not** under MIT |

---

## Archive contents (as tagged)

### Included

- Source code (`src/`, `scripts/`, `tests/`)
- Configs (`configs/`)
- Documentation (`docs/`, `README.md`, `REPRODUCIBILITY.md`, `THIRD_PARTY_NOTICES.md`)
- `LICENSE` (MIT), `CITATION.cff`, `.zenodo.json`
- Protocol freeze manifests + digests
- Compact tracked `artifacts/**` summaries (non-weight)

### Excluded (gitignored / out of tree)

- Raw `data/raw/**` dumps
- Base model weights / LoRA adapters
- Manuscript LaTeX/PDF
- Secrets, bulk raw attribution jobs

---

## Release checklist

- [x] LICENSE = MIT
- [x] README licensing scope + `THIRD_PARTY_NOTICES.md`
- [x] Tag `v1.0.0`
- [x] Zenodo deposition via GitHub integration
- [x] Real DOI received: `10.5281/zenodo.23196604`
- [x] Citation/release metadata updated with the real DOI
- [ ] Related publication DOI (journal article) — when the paper is published

---

## Completed order

1. Artifact-aware Claude review  
2. Release candidate gate  
3. Tag `v1.0.0`  
4. GitHub / Zenodo archive  
5. Real DOI captured  
6. Metadata updated on `main` with the real DOI  

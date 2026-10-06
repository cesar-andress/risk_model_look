# ZENODO_RELEASE_PLAN.md

**Status:** preparation only — **no DOI created, no upload**.  
**Updated:** 2026-10-06 (SUPERPROMPT 33 — MIT for author-owned software)

---

## License (author decision)

| Scope | License |
|-------|---------|
| Author-owned software (`src/`, `scripts/`, `tests/`, `configs/`, author docs) | **MIT** (`LICENSE`) |
| Tracked author-owned compact result artifacts under `artifacts/**` | **MIT** (with the package) |
| Upstream JIT-Fine / JIT-Defects4J raw dumps | **Not redistributed; not relicensed** |
| Third-party model weights / dependencies | Upstream licenses |
| Manuscript / publisher article | **Not** under MIT; not in this deposit |

Record-level Zenodo field: `license: mit` is honest **only** because the planned
deposit excludes raw third-party data, model weights, adapters, and the
manuscript. If those were added later, re-evaluate before upload
(`MIXED_LICENSE_METADATA_CONFLICT` if a single global MIT would misrepresent
the payload).

**Do not invent a Zenodo DOI.**

---

## Archive contents (planned)

### YES (include)

- Source code (`src/`, `scripts/`, `tests/`)
- Configs (`configs/`)
- Documentation (`docs/`, `README.md`, `REPRODUCIBILITY.md`, `THIRD_PARTY_NOTICES.md`)
- `LICENSE` (MIT), `CITATION.cff`, `.zenodo.json`
- Protocol freeze manifests + SHA-256 digests
- Small CSV/JSON audit summaries already tracked under `artifacts/**` (non-weight)

### NO (exclude)

- `data/raw/**` (raw JIT dumps — gitignored; upstream terms)
- Full `data/processed/**` blobs (JSONL, pkl caches)
- Model base weights (Qwen) — re-download from upstream revision pin
- LoRA adapters / checkpoints (`.safetensors`)
- Manuscript LaTeX / PDF / publisher-formatted article (private sibling `../paper/`)
- Secrets, `.env`, API keys
- Agent/tooling dirs (`.cursor/`, etc.)
- Training logs / wandb
- Bulk TEST attribution raw jobs (`artifacts/test_attribution/raw/`)

---

## Metadata draft

| Field | Draft |
|-------|-------|
| Title | When Validity Criteria Disagree: Evaluating Line-Level Explanations for Just-in-Time Defect Prediction — Replication Package |
| Creators | César Andrés (ORCID 0009-0001-8968-3404) |
| Description | See `.zenodo.json` |
| Keywords | just-in-time defect prediction; explainable AI; faithfulness; Integrated Gradients; large language models; software engineering |
| Related publication | TBD (DOI of paper when available — never invent) |
| License | **mit** (author-owned software + tracked compact artifacts only) |
| Version | **1.0.0** (metadata ready; tag/upload not performed in SP34) |

---

## Future release order (do not reorder)

1. Final artifact-aware Claude review
2. Authorize release
3. Tag `v1.0.0`
4. GitHub Release
5. Zenodo deposition
6. Receive real DOI from Zenodo
7. Update citation/release metadata with the real DOI if required

No circular/fake DOI workflow. No tag/Release/Zenodo until Claude authorizes.

---

## Pre-upload checklist

- [x] LICENSE = MIT (author-owned software)
- [x] README licensing scope + `THIRD_PARTY_NOTICES.md`
- [x] CITATION.cff `license: MIT` (no DOI)
- [x] `.zenodo.json` `license: mit` with mixed-scope notes
- [x] Dataset redistribution statement verified (raw dumps not tracked)
- [x] Results freeze documented (two hashes; NUMERICAL_GATE = FAIL)
- [ ] Owner approval after Claude artifact-aware review
- [ ] Tag `v1.0.0` / GitHub Release / Zenodo (blocked until authorized)

---

## Upload action

**Not performed.** Requires separate owner-authorized gate after Claude review.

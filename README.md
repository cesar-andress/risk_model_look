# risk_model_look

Replication package for:

**When Validity Criteria Disagree: Evaluating Line-Level Explanations for Just-in-Time Defect Prediction**

Author: César Andrés (ORCID 0009-0001-8968-3404), CRIA-BDHS / Escuela Politécnica Superior de Tecnología y Ciencia, Universidad Camilo José Cela.

Target venue: Empirical Software Engineering (EMSE). Version: **1.0.0**.  
Zenodo DOI: [10.5281/zenodo.23196604](https://doi.org/10.5281/zenodo.23196604)  
(Concept DOI for all versions: [10.5281/zenodo.23196603](https://doi.org/10.5281/zenodo.23196603).)

## What this repository is

Public code, configs, frozen protocols, tests, and **tracked result summaries** for:

- public JIT-Defects4J / JIT-Fine resources (without redistributing restricted raw dumps);
- one NF4 Qwen2.5-Coder-7B QLoRA classifier;
- line-level attributions under Attribution Protocol V1.2 and Statistical Protocol V1.1.

## What this repository is not

- It does not redistribute raw datasets by default (`data/raw/` is gitignored).
- It does not ship base LLM weights or LoRA adapters.
- Manuscript LaTeX lives in the private sibling `../paper/`.
- Bulk TEST attribution jobs (`artifacts/test_attribution/raw/`) are gitignored.

## Headline numbers without GPU

From a clone of `main`, using Python 3.11 from `environment.yml` (or `.venv`):

```bash
python3 -m pytest -m "cpu or not gpu" -q
python3 scripts/print_headline_from_tracked.py
```

That printer reads only tracked JSON/CSV under `artifacts/` (RQ1 summary, RQ2 stats, seed stability, EMSE freeze). It does **not** require raw jobs or a GPU.

## Final evidence freeze (two hashes)

File: `artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json`

| Hash | Meaning |
|------|---------|
| `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78` | Scientific freeze identifier (`freeze_sha256` **inside** the JSON). Use this in manuscript claims and provenance. |
| `aff72921d3fd8ca41d6b80db58cf377b052959c9c0ad869e1d35dc4fc56214ce` | SHA-256 of the JSON **file bytes** (includes the `freeze_sha256` field). Use this to verify the file was not altered. |

They differ by construction. NUMERICAL_GATE = FAIL.

## Hard constraints

- Do not commit secrets, adapters, or Hugging Face caches.
- Do not claim unfinished experiments as completed.

## Dataset restrictions

This package does **not** relicense or redistribute upstream JIT-Defects4J / JIT-Fine raw dumps.
Obtain those from their upstream distributors under their own terms.
Tracked derived summaries in `artifacts/` are project outputs for reproduction of the frozen tables.

## Citation

See `CITATION.cff`. Prefer the version DOI for this release:

```
Andrés, C. (2026). When Validity Criteria Disagree: Evaluating Line-Level
Explanations for Just-in-Time Defect Prediction — Replication Package
(v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.23196604
```

## Licensing

This is a **mixed-scope** package. The MIT grant does **not** cover everything you
might obtain when reproducing the study.

| Material | Covered by MIT (`LICENSE`)? |
|----------|-----------------------------|
| **A. Author-owned software** (`src/`, `scripts/`, `tests/`, `configs/`, author docs in this repo) | **Yes** — MIT, Copyright (c) 2026 César Andrés |
| **B. Third-party datasets** (JIT-Fine / JIT-Defects4J upstream dumps) | **No** — not relicensed; subject to upstream terms |
| **C. Raw JIT-Fine / JIT-Defects4J material** | **Not redistributed** here (`data/raw/**` gitignored except placeholders/README) |
| **D. Third-party model weights / software** (e.g. Qwen base; PyPI/conda deps) | **No** — respective upstream licenses |
| **E. Manuscript / article** (private sibling `../paper/`) | **No** — not under this MIT software license; reuse by authors/publisher |
| **F. Derived compact result artifacts** tracked under `artifacts/**` (CSV/JSON summaries, freeze manifests) | **Yes** — author-owned study outputs released under MIT with this package |

See also `THIRD_PARTY_NOTICES.md` and `docs/ZENODO_RELEASE_PLAN.md`.

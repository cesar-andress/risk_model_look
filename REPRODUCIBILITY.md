# REPRODUCIBILITY.md

Venue: EMSE. Empirical execution is closed. Do not start new GPU scientific runs.

## Licensing (reproduction context)

| Layer | How to obtain | License note |
|-------|---------------|--------------|
| Author-owned code + docs in this clone | This repository | **MIT** (`LICENSE`) |
| Frozen compact outputs under tracked `artifacts/**` | This repository | Author-owned; released under **MIT** with the package |
| Upstream JIT-Defects4J / JIT-Fine raw data | External distributors | **Not** redistributed / **not** relicensed here |
| Base model weights (Qwen pin) | Hugging Face / upstream | Upstream model license |
| LoRA adapters / bulk raw attribution jobs | Local-only / not default clone | Not part of the default MIT code deposit |
| Manuscript LaTeX/PDF | Private sibling `../paper/` | **Not** covered by this MIT software license |

See `THIRD_PARTY_NOTICES.md` and the Licensing section of `README.md`.

Published archive: Zenodo DOI
[10.5281/zenodo.23196604](https://doi.org/10.5281/zenodo.23196604)
(v1.0.0; concept DOI [10.5281/zenodo.23196603](https://doi.org/10.5281/zenodo.23196603)).

## Existing-data path (clone of origin/main, no GPU, no raw jobs)

```bash
python3 -m pytest -m "cpu or not gpu" -q
python3 scripts/print_headline_from_tracked.py
```

Tracked inputs include:

- `artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json`
- `artifacts/emse_final/emse_final_diagnostics.json`
- `artifacts/test_attribution/summaries/rq1_summary.csv`
- `artifacts/test_attribution/summaries/rq1_secondary_metrics.json`
- `artifacts/test_attribution/summaries/rq2_excluded_3.json`
- `artifacts/test_attribution/statistics/rq2_stats.json`
- `artifacts/test_attribution/metrics/stability/seed_stability.json`
- `artifacts/tosem_extension/cpu_reanalysis.json`

## Regenerating diagnostics (local raw jobs required; not a clone default)

`scripts/emse_final_diagnostics.py` and `scripts/tosem_extension_cpu_reanalysis.py` need gitignored `artifacts/test_attribution/raw/` plus a local tokenizer. They are not required to read the frozen headline tables.

## GPU path (only if reproducing jobs from scratch)

M1 QLoRA (`scripts/run_m1_final.py`) then `scripts/run_test_attribution.py`. Hardware used originally: NVIDIA RTX 4090. Do not train a second decoder. Obtain base weights and (if used) adapters under their own terms; they are outside the MIT software grant for this repository.

## Environment

`environment.yml` (Python 3.11). Seeds: 13, 42, 73. Score \(s=\ell_1-\ell_0\).

## Provenance

`docs/AMENDMENT_AND_PROVENANCE_LOG.md`. NUMERICAL_GATE = FAIL.

## Paper build

Private sibling `../paper/`: `make pdf`. Manuscript reuse is separate from the MIT software license.

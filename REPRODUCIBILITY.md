# REPRODUCIBILITY.md

Empirical study **closed** (EMSE reframe). No further experimental expansion.

## Existing-data path (no GPU)

From the nested code repository root:

```bash
python -m pytest -m "cpu or not gpu" -q
python scripts/tosem_extension_cpu_reanalysis.py   # owed baselines already frozen
python scripts/emse_final_diagnostics.py           # EMSE A–K diagnostics (CPU, tokenizer)
```

Requires local TEST attribution jobs under `artifacts/test_attribution/raw/` (gitignored bulk), cohort JSON, M1 `test_predictions.csv`, and the numerical `artifacts/tosem_extension/numerical_rows.jsonl` already produced.

Do **not** rerun training, TEST attribution, IG, or the numerical GPU script unless reproducing those artifacts from scratch.

## GPU path (only if artifacts are missing)

Expected order: M1 QLoRA training (`scripts/run_m1_final.py`) then `scripts/run_test_attribution.py` then optional `scripts/tosem_numerical_and_random.py`.
Hardware used here: NVIDIA RTX 4090; NF4 Qwen2.5-Coder-7B. Full attribution TEST is many GPU-hours (design projection ~100 h). Do not start a second decoder.

## Environment

See `environment.yml` and `.venv` (Python 3.11, PyTorch 2.6+cu124 in the development lock). CPU tests: `pytest -q`.

Seeds: 13, 42, 73. Score \(s=\ell_1-\ell_0\).

## Provenance

See `docs/AMENDMENT_AND_PROVENANCE_LOG.md`.

NUMERICAL_GATE = FAIL (do not reinterpret).

## Paper build

Sibling `../paper/`:

```bash
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

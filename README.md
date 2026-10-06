# risk_model_look

Replication package for:

**When Validity Criteria Disagree: Evaluating Line-Level Explanations for Just-in-Time Defect Prediction**

Author: César Andrés (ORCID 0009-0001-8968-3404), CRIA-BDHS / Escuela Politécnica Superior de Tecnología y Ciencia, Universidad Camilo José Cela.

Target venue: Empirical Software Engineering (EMSE). Version: pre-v1.0.0. No DOI.

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

Final evidence freeze SHA-256: `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78`  
(`artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json`). NUMERICAL_GATE = FAIL.

## Hard constraints

- Do not commit secrets, adapters, or Hugging Face caches.
- Do not claim unfinished experiments as completed.

## Dataset restrictions

Treat upstream JIT-Defects4J / JIT-Fine redistribution as restricted until verified.

## Citation

See `CITATION.cff`. No paper/Zenodo DOI is minted yet.

## License

`LICENSE` is `NOASSERTION` until a SPDX identifier is chosen for v1.0.0.

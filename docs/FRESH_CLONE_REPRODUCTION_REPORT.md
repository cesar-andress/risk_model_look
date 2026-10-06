# Fresh-clone reproduction report

Date: 2026-10-06  
Task: SUPERPROMPT 34 — definitive release-candidate gate  
Clone: `/tmp/rml_fresh_clone_sp34`  
Remote: `git@github.com-ucjc:cesar-andress/risk_model_look.git` branch `main`  
Candidate HEAD: `9cb86a8e768b46e80160163a288820592fa3ec28`  
No files were copied from the working tree into the clone.

## Clean environment (not the project `.venv`)

```bash
# micromamba from environment.yml (Python 3.11)
export MAMBA_ROOT_PREFIX=$HOME/micromamba
micromamba create -y -n rml_sp34_rc -f environment.yml
# interpreter:
#   $MAMBA_ROOT_PREFIX/envs/rml_sp34_rc/bin/python  →  Python 3.11.17
```

Creation: **PASS** (exit 0). Required scientific packages importable:
`datasets`, `accelerate`, `peft`, `bitsandbytes`, `captum`, `torch`, `transformers`.

## Commands

```bash
git clone --branch main --single-branch <origin> /tmp/rml_fresh_clone_sp34
cd /tmp/rml_fresh_clone_sp34
CUDA_VISIBLE_DEVICES= python scripts/print_headline_from_tracked.py
CUDA_VISIBLE_DEVICES= PYTHONPATH=. python -m pytest -m "cpu or not gpu" -q
```

Headline printer: **PASS** (tracked JSON/CSV only; attention Recall@20%=0.354).  
Tests: **231 passed**, 0 failed, 0 skipped (includes one new structure test after removing stale root files; prior baseline was 230).  
No GPU scientific run. No raw data download required for this path.

## Licensing / release metadata present

- `LICENSE` MIT; `THIRD_PARTY_NOTICES.md`; README Licensing table  
- `CITATION.cff` / `.zenodo.json` version **1.0.0**, date **2026-10-06**, **no DOI**  
- Stale `STATUS.md` / `REPRODUCE.md` absent  

## Freeze identifiers

- `freeze_sha256` = `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78`
- JSON file-byte SHA-256 = `aff72921d3fd8ca41d6b80db58cf377b052959c9c0ad869e1d35dc4fc56214ce`
- `NUMERICAL_GATE` = FAIL

Undocumented local dependency: **NO**.  
Verdict: **PASS**.

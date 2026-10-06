# Fresh-clone reproduction report

Date: 2026-10-06  
Clone: `/tmp/rml_fresh_clone_20261006b`  
Remote: `git@github.com-ucjc:cesar-andress/risk_model_look.git` branch `main`  
HEAD: `f1844b9857fd3196d6a4631cc60b229bb393b74e`  
No files were copied from the working tree into the clone.

## Commands (as written in README / REPRODUCIBILITY.md)

```bash
git clone --branch main --single-branch <origin> /tmp/rml_fresh_clone_20261006b
cd /tmp/rml_fresh_clone_20261006b
python3.11 scripts/print_headline_from_tracked.py
```

Headline printer: **PASS** (stdlib + tracked JSON/CSV only). Runtime ~0.02 s.  
`artifacts/test_attribution/raw/` absent, as expected.

Bare `python3.11 -m pytest -m "cpu or not gpu" -q` **fails collection** (`ModuleNotFoundError: torch`). That is documented in `environment.yml` / `docs/ENVIRONMENT_REPORT.md`, not an undocumented local file.

Tests with the documented Python 3.11 environment (interpreter from the author's `environment.yml` / `.venv`, clone as cwd, no extra data files):

```bash
<env>/bin/python -m pytest -m "cpu or not gpu" -q
```

Result: **230 passed**, 0 failed, ~3 s. No GPU scientific run.

## Reproduced outputs (tracked data)

- Freeze identifier `freeze_sha256` = `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78`
- JSON file SHA-256 = `aff72921d3fd8ca41d6b80db58cf377b052959c9c0ad869e1d35dc4fc56214ce`
- `NUMERICAL_GATE` = FAIL
- RQ1 N=304 Recall@20: attention 0.354, Grad×Input 0.331, occlusion 0.315; last-four-layer attention 0.362; length 0.395; random 0.312
- RQ1 secondary (frozen job fields): attention Top1/5/10 0.423/0.760/0.870, IFA 4.12, Effort@20%Recall 0.453
- RQ2 Attention vs Grad×Input: n_included=472, n_excluded=3 (OOM IDs in `rq2_excluded_3.json`)
- TEST all-line seed Spearman pair means: Attention 0.607/0.633/0.632; Grad×Input 0.189/0.178/0.140; occlusion 0.243/0.257/0.327
- EMSE RQ1 ≥5 mean_across_commits: Attention 0.608 (N=202); Grad×Input 0.119 (N=202); occlusion 0.023 (N=189)

Undocumented local dependency: **NO**.

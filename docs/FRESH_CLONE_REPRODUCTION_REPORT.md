# Fresh-clone reproduction report

Date: 2026-10-06  
Task: SUPERPROMPT 33 (MIT license scoping)  
Clone: `/tmp/rml_fresh_clone_sp33`  
Remote: `git@github.com-ucjc:cesar-andress/risk_model_look.git` branch `main`  
HEAD: `41a79cefaa82a261f2d8897bf705fd79246a76ea`  
No files were copied from the working tree into the clone.

## Commands (as written in README / REPRODUCIBILITY.md)

```bash
git clone --branch main --single-branch <origin> /tmp/rml_fresh_clone_sp33
cd /tmp/rml_fresh_clone_sp33
python3.11 scripts/print_headline_from_tracked.py
```

Headline printer: **PASS** (stdlib + tracked JSON/CSV only).  
`artifacts/test_attribution/raw/` absent, as expected.  
LoRA adapters absent, as expected.

Tests with the documented Python 3.11 environment (interpreter from the author's
`environment.yml` / `.venv`, clone as cwd, no extra data files):

```bash
<env>/bin/python -m pytest -m "cpu or not gpu" -q
```

Result: **230 passed**, 0 failed, 0 skipped (marker selection). No GPU scientific run.

## Licensing files present

- `LICENSE` — MIT, Copyright (c) 2026 César Andrés
- `THIRD_PARTY_NOTICES.md` — datasets / models / deps / manuscript exclusions
- `CITATION.cff` — `license: MIT`, no DOI
- `.zenodo.json` — `license: mit`, no DOI
- README Licensing table — mixed-scope (software MIT; data/models/manuscript excluded)

## Reproduced outputs (tracked data)

- Freeze identifier `freeze_sha256` = `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78`
- JSON file SHA-256 = `aff72921d3fd8ca41d6b80db58cf377b052959c9c0ad869e1d35dc4fc56214ce`
- `NUMERICAL_GATE` = FAIL
- RQ1 N=304 Recall@20: attention 0.354, Grad×Input 0.331, occlusion 0.315; random baseline path intact

Undocumented local dependency: **NO**.  
Verdict: **PASS**.

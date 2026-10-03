# LARGE_FILE_AUDIT.md

**Scan date:** 2026-10-01  
**Scope:** `risk_model_look/`, `risk_model_look_parallel/`, `paper/` (excluding `.git` / `.venv`)  
**Action:** report only — **no deletions**

---

## Summary

| Threshold | Count (approx.) |
|-----------|----------------:|
| ≥ 10 MiB | 47 |
| ≥ 100 MiB | 8 |

**Git-tracked files ≥ 1 MiB:** **none** (good). Large objects live on disk under gitignored paths.

---

## Files ≥ 100 MiB (unsuitable for Git)

| ≈MiB | Path (main worktree) |
|-----:|------|
| 748 | `data/processed/canonical_v1/train.jsonl` |
| 277 | `data/processed/canonical_v1/test.jsonl` |
| 210 | `data/processed/canonical_v1/valid.jsonl` |
| 154 | `artifacts/pilot_training/stage_{a,b}_adapter/adapter_model.safetensors` |
| 154 | `artifacts/m1_final/adapters/seed_13/epoch_1/adapter_model.safetensors` |
| 150 | `data/processed/canonical_v1/m1_encoded_cache/train_ml2048.pkl` |
| 103 | `data/raw/upstream/jitfine_src/JIT-Fine.git/objects/pack/*.pack` |

---

## Notable 10–100 MiB classes

- `data/raw/source_repos/**/*.pack` — cloned project histories
- `data/raw/upstream/**` — JIT-Fine archives / pickles / JSON
- `data/raw/external/jitblock/**` — external audit archives
- `data/processed/**/m1_encoded_cache/*.pkl`
- `data/raw/derived_audit/**` large JSONL mappings

`paper/main.pdf` is small (<1 MiB class for this scan) but must remain untracked as a build product when paper is imported.

---

## Git suitability verdict

| Class | Enter Git? |
|-------|------------|
| Source, configs, tests, docs, small manifests/hashes | YES |
| Protocol freeze JSON/SHA manifests | YES (already) |
| Raw/processed datasets, packs, zip | **NO** |
| LoRA / safetensors / bins | **NO** |
| Encoded caches / score dumps | **NO** |
| Hugging Face / wandb caches | **NO** |

---

## Release implication

Zenodo/GitHub release should ship **code + manifests + small provenance digests**, with dataset acquisition scripts — not the 748 MiB JSONL blobs or adapters — unless a separate controlled artifact deposit is approved later.

# ATTRIBUTION_ENGINE_DESIGN.md

**Gate:** ATTRIBUTION_ENGINEERING_OPTIMIZATION_GATE  
**Branch:** `parallel/attribution-infra`  
**Date:** 2026-10-01  

Scientific contracts remain Attribution Protocol **V1.2** /
Statistical Protocol **V1.1**. This document describes **execution
infrastructure only**.

---

## Architecture

```
scripts/run_attribution.py
        │
        ▼
src/experiments/runner_core.py  (AttributionEngine)
        │
        ├── run_store.py      isolated runs/ + manifest + resume guards
        ├── job_state.py      PENDING→RUNNING→DONE/FAILED/OOM/NONCONVERGED
        ├── attribution_cache.py  versioned scientific cache keys
        ├── attribution_cost.py   dry-run / planner estimates
        ├── batching.py         IG stack + occlusion batch helpers
        └── aggregate_attribution_results.py  JSONL index (no metric recompute)
```

Real Qwen backends are **not** wired here. Default executor is deterministic
CPU toy logic so the engine can be tested without loading 7B weights.

---

## Cache design

`EngineCacheKey` hashes:

model_hash, adapter_hash, dataset_version, commit_id, method, granularity,
protocol_hash, renderer_version, token_mapping_version, perturbation_operator,
configuration_hash, seed.

Layout:

`artifacts/attribution_cache/<method>/<model16>/<protocol16>/<commit__seed__gran__cfg__digest>.json`

Checksummed payloads; never key only by commit ID.

---

## Resume logic

1. `--resume` loads latest `runs/attribution_run_*`.
2. Compares protocol/config/model/adapter/stats/dataset/method/cohort/seed/granularity.
3. Mismatch → **STOP** (`RESUME BLOCKED`).
4. `DONE` / `NONCONVERGED` units are not re-executed (unless `--force`).
5. `FAILED` / `OOM` / crashed `RUNNING` / `PENDING` retry.

---

## Rollback / isolation

Each invocation without `--resume` creates a new
`runs/attribution_run_<timestamp>/` with:

- `manifest.json`, `config` hooks, `logs/`, `summaries/`, `checkpoints/job_ledger.json`, `cache_index.json`

Failed runs do not mutate prior run directories. `--force` overwrites cache
entries explicitly.

---

## Dry-run

`--dry-run` prints an ATTRIBUTION PLAN (forwards/backwards/IG/occlusion/storage)
and **does not** load a model or write run dirs.

---

## Batching

- Occlusion: construct perturbed inputs, score in batches; delta semantics
  unchanged (`s(x)-s(x\\R)`).
- IG: stack interpolation points for a supplied alpha schedule; **does not**
  change 50→100 Gauss–Legendre protocol — caller supplies protocol alphas.

---

## Frozen M1 GPU backend

`src/experiments/m1_backend.py` loads the **selected** QLoRA adapter from
`artifacts/m1_final/final_model_manifest.json`.

Before any forward it verifies:

- base model id + immutable revision `c03e6d358207e414f1eca0bb1891e29f1db0e242`
- adapter `adapter_model.safetensors` SHA-256
- scientific config hash
- Attribution Protocol V1.2 / Statistical Protocol V1.1 hashes

Mismatch raises `FrozenM1Mismatch` (hard fail). TEST records are refused.

CLI: `scripts/run_attribution.py --backend frozen_m1 --seed 13 ...`
(default payloads are stamped `NOT_SCIENTIFIC_RESULT` unless `--scientific`).

Inference stack used in the engineering GPU benchmark:

- NF4 weights, bf16 compute, double quant
- SDPA for forwards/backwards
- last-layer attention via Q/K recompute (no `output_attentions=True`)
- gradient checkpointing for Grad×Input / IG
- IG Gauss–Legendre 50 (chunk=1 selected; chunk=4 is faster but NF4-noisy)
- occlusion `SEGMENT_DELETE_V1` with padded batched scoring (batch 4)

## ENGINEERING BENCHMARK vs SCIENTIFIC ATTRIBUTION REHEARSAL

| | Engineering GPU benchmark | Validation rehearsal N=64 |
|--|--|--|
| Path | `artifacts/attribution_gpu_benchmark/` | not started |
| Label | `NOT_SCIENTIFIC_RESULT` | scientific protocol |
| Split | validation only, N≤10 | frozen rehearsal cohort |
| IG steps | 4-step micro + one 50-step runtime | 50 then 100 retry |
| Purpose | throughput, VRAM, resume | RQ-ready attributions |

Do **not** feed benchmark JSONL into RQ aggregators (guard in
`aggregate_attribution_results.py`).

GPU benchmark (RTX 4090, seed 13 / epoch 2, 2026-10-03): see
`artifacts/attribution_gpu_benchmark/throughput.json` and
`cost_projection.json`. Peak VRAM ~16 GiB allocated at 2048 tokens.
Conservative 3-seed IG@2048 projection is on the order of ~25 GPU-hours
for RQ1+RQ234 methods combined; the 219-token 50-step timing must not be
extrapolated as if it were full 2048.

## Resume

`--resume` skips `DONE` / `NONCONVERGED` ledger units. Adapter directories
are hashed via `adapter_model.safetensors` (not `"NONE"`).


`src/experiments/attribution_cost.py` estimates pass counts for planner use
before expensive launches.

---

## Workflow (after M1)

1. `python scripts/run_attribution.py --dry-run ...`
2. Validation rehearsal config: `configs/attribution/validation_rehearsal_v1.yaml`
3. Execute with `--resume` until complete
4. Then test config: `configs/attribution/test_execution_v1.yaml`

---

## Benchmarks

`scripts/benchmark_attribution_engine.py` writes
`artifacts/benchmarks/attribution_engine_benchmark.json` (CPU toy timings).

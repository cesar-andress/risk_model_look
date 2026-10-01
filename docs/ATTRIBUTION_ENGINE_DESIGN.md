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

## Cost estimator

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

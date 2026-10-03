#!/usr/bin/env python3
"""CPU benchmarks for attribution engine primitives (toy model only)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.attribution.occlusion import OcclusionUnit, RegionSpec, remove_region_structured
from src.attribution.toy_model import TinyCausalScorer
from src.experiments.batching import (
    ig_accumulate_from_batched_grads,
    ig_interpolation_points,
    occlude_regions_batched,
    plan_batches,
)
from src.experiments.attribution_cache import (
    AttributionCacheStore,
    CacheEntry,
    build_engine_cache_key,
)


def _try_import_toy():
    try:
        from src.attribution.toy_model import TinyCausalScorer

        return TinyCausalScorer
    except Exception:
        return None


def bench_forward_backward(n: int = 200) -> dict:
    x = torch.randn(32, 64, requires_grad=True)
    w = torch.randn(64, 1)
    t0 = time.perf_counter()
    for _ in range(n):
        y = x @ w
        y.sum().backward(retain_graph=False)
        if x.grad is not None:
            x.grad = None
    dt = time.perf_counter() - t0
    return {
        "forward_backward_iters": n,
        "seconds": dt,
        "fwd_bwd_per_sec": n / dt if dt > 0 else None,
    }


def bench_ig_steps(n_steps: int = 50, repeats: int = 20) -> dict:
    emb = torch.randn(1, 16, 32, requires_grad=True)
    base = torch.zeros_like(emb)
    alphas = [(i + 0.5) / n_steps for i in range(n_steps)]
    weights = [1.0 / n_steps] * n_steps
    t0 = time.perf_counter()
    for _ in range(repeats):
        pts = ig_interpolation_points(emb, base, alphas)
        # fake grads = pts for speed measurement of stack/accumulate path
        grads = pts.detach().clone()
        delta = emb.detach() - base
        _ = ig_accumulate_from_batched_grads(grads, delta=delta, weights=weights)
    dt = time.perf_counter() - t0
    total_steps = n_steps * repeats
    return {
        "ig_steps_total": total_steps,
        "seconds": dt,
        "ig_step_per_sec": total_steps / dt if dt > 0 else None,
    }


def bench_occlusion(n_regions: int = 32, repeats: int = 30) -> dict:
    from src.attribution.occlusion import ToyStructuredCommit

    commit = ToyStructuredCommit(
        message="m",
        files={
            "a.py": [
                {
                    "stable_line_id": f"L{i}",
                    "hunk_id": "H0",
                    "change_type": "ADD",
                    "text": f"x={i}",
                }
                for i in range(n_regions)
            ]
        },
    )
    regions = [
        RegionSpec(unit=OcclusionUnit.LINE, region_id=f"L{i}", stable_line_ids=(f"L{i}",))
        for i in range(n_regions)
    ]

    def score_fn(c):
        return float(len(c.message) + sum(len(v) for v in c.files.values()))

    t0 = time.perf_counter()
    for _ in range(repeats):
        occlude_regions_batched(
            commit,
            regions,
            score_fn=score_fn,
            remove_fn=remove_region_structured,
            batch_size=8,
        )
    dt = time.perf_counter() - t0
    total = n_regions * repeats
    return {
        "occlusion_region_evals": total,
        "seconds": dt,
        "occlusion_region_per_sec": total / dt if dt > 0 else None,
        "batch_plan": plan_batches(n_regions, 8).__dict__,
    }


def bench_cache(tmpdir: Path, n: int = 100) -> dict:
    store = AttributionCacheStore(tmpdir / "cache")
    t_w0 = time.perf_counter()
    keys = []
    for i in range(n):
        key = build_engine_cache_key(
            model_hash="M",
            adapter_hash="A",
            dataset_version="D",
            commit_id=f"C{i}",
            method="attention",
            granularity="LINE",
            configuration={"i": i},
            seed=13,
        )
        keys.append(key)
        store.write(
            key,
            CacheEntry(
                cache_key=key.digest(),
                key_fields=key.__dict__,
                status="DONE",
                result_summary={"i": i},
                checksum="",
                metadata={},
            ),
            force=True,
        )
    t_w = time.perf_counter() - t_w0
    t_r0 = time.perf_counter()
    for key in keys:
        assert store.read(key) is not None
    t_r = time.perf_counter() - t_r0
    return {
        "cache_writes": n,
        "cache_write_per_sec": n / t_w if t_w > 0 else None,
        "cache_reads": n,
        "cache_read_per_sec": n / t_r if t_r > 0 else None,
        "write_seconds": t_w,
        "read_seconds": t_r,
    }


def main() -> int:
    out_dir = REPO_ROOT / "artifacts" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {
        "forward_backward": bench_forward_backward(),
        "ig_path": bench_ig_steps(),
        "occlusion": bench_occlusion(),
        "cache": bench_cache(out_dir),
        "toy_model_available": _try_import_toy() is not None,
    }
    path = out_dir / "attribution_engine_benchmark.json"
    path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

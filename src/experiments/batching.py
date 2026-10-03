"""Batching helpers that preserve scientific semantics.

These utilities prepare batched tensors / score calls. They do not change
IG step counts, baselines, or perturbation operator definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

import torch
from torch import Tensor

from src.attribution.occlusion import (
    OcclusionResult,
    RegionSpec,
    RemoveCallable,
    ScoreCallable,
    signed_occlusion_delta,
)


@dataclass(frozen=True)
class BatchPlan:
    batch_size: int
    n_items: int
    n_batches: int


def plan_batches(n_items: int, batch_size: int) -> BatchPlan:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if n_items < 0:
        raise ValueError("n_items must be >= 0")
    n_batches = (n_items + batch_size - 1) // batch_size if n_items else 0
    return BatchPlan(batch_size=batch_size, n_items=n_items, n_batches=n_batches)


def chunked(items: Sequence[Any], batch_size: int) -> list[Sequence[Any]]:
    plan = plan_batches(len(items), batch_size)
    return [items[i : i + batch_size] for i in range(0, plan.n_items, batch_size)]


def occlude_regions_batched(
    structured_input: Any,
    regions: Sequence[RegionSpec],
    *,
    score_fn: ScoreCallable,
    remove_fn: RemoveCallable,
    batch_score_fn: Callable[[Sequence[Any]], Sequence[float]] | None = None,
    batch_size: int = 8,
) -> list[OcclusionResult]:
    """Batched occlusion: one baseline score + batched perturbed scores.

    Scientific semantics match sequential ``occlude_region``:
    delta_R = s(x) - s(x_without_R).
    """
    s_full = float(score_fn(structured_input))
    results: list[OcclusionResult] = []
    for batch in chunked(list(regions), batch_size):
        perturbed = [remove_fn(structured_input, r) for r in batch]
        if batch_score_fn is None:
            scores = [float(score_fn(p)) for p in perturbed]
        else:
            scores = [float(s) for s in batch_score_fn(perturbed)]
        for region, s_without in zip(batch, scores):
            delta = signed_occlusion_delta(s_full, s_without)
            results.append(
                OcclusionResult(
                    region=region,
                    s_full=s_full,
                    s_without=float(s_without),
                    delta=delta,
                    signed=True,
                    metadata={
                        "batched": True,
                        "batch_size": batch_size,
                        "perturbation": "structured_remove",
                    },
                )
            )
    return results


def ig_interpolation_points(
    embeddings: Tensor,
    baseline: Tensor,
    alphas: Sequence[float],
) -> Tensor:
    """Stack interpolated embeddings for batched IG steps.

    Returns tensor shaped (n_alphas, *embeddings.shape).
    Does not change Gauss–Legendre node selection — caller supplies alphas.
    """
    if embeddings.shape != baseline.shape:
        raise ValueError("embeddings and baseline shapes must match")
    points = []
    for a in alphas:
        # x_alpha = baseline + alpha * (x - baseline)
        points.append(baseline + float(a) * (embeddings - baseline))
    return torch.stack(points, dim=0)


def ig_accumulate_from_batched_grads(
    grads: Tensor,
    *,
    delta: Tensor,
    weights: Sequence[float],
) -> Tensor:
    """Accumulate IG from batched grads (n_steps, *embed_shape) and GL weights."""
    if grads.shape[0] != len(weights):
        raise ValueError("grads batch must match weights length")
    acc = torch.zeros_like(grads[0])
    for i, w in enumerate(weights):
        acc = acc + float(w) * grads[i]
    return acc * delta


def clear_cuda_cache_if_available() -> bool:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        return True
    return False


def memory_snapshot() -> dict[str, float | None]:
    if not torch.cuda.is_available():
        return {"peak_allocated_bytes": None, "peak_reserved_bytes": None, "device": None}
    return {
        "peak_allocated_bytes": float(torch.cuda.max_memory_allocated()),
        "peak_reserved_bytes": float(torch.cuda.max_memory_reserved()),
        "device": torch.cuda.current_device(),
    }

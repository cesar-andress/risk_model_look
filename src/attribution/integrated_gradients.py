"""Integrated Gradients against input embeddings (generic module).

Baselines are explicit options — never silently chosen as scientific defaults
without protocol recording.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

import torch
from torch import Tensor

from src.attribution.base import AttributionResult, ScoreSpace, TargetDefinition
from src.attribution.targets import M1_RISK_LOGIT_CONTRAST


class IGBaselineStrategy(str, Enum):
    ZERO_EMBEDDING = "ZERO_EMBEDDING"
    PAD_TOKEN_EMBEDDING = "PAD_TOKEN_EMBEDDING"
    EXPLICIT_TENSOR = "EXPLICIT_TENSOR"


ScoreFn = Callable[[Tensor], Tensor]


def resolve_baseline(
    embeddings: Tensor,
    *,
    strategy: IGBaselineStrategy,
    pad_embedding: Tensor | None = None,
    explicit_baseline: Tensor | None = None,
) -> Tensor:
    if strategy == IGBaselineStrategy.ZERO_EMBEDDING:
        return torch.zeros_like(embeddings)
    if strategy == IGBaselineStrategy.PAD_TOKEN_EMBEDDING:
        if pad_embedding is None:
            raise ValueError("pad_embedding required for PAD_TOKEN_EMBEDDING")
        # pad_embedding: (D,) or (1,1,D) or (1,T,D)
        pe = pad_embedding
        if pe.dim() == 1:
            pe = pe.view(1, 1, -1).expand_as(embeddings)
        elif pe.dim() == 2:
            pe = pe.unsqueeze(0).expand_as(embeddings)
        elif pe.shape != embeddings.shape:
            pe = pe.expand_as(embeddings)
        return pe.to(dtype=embeddings.dtype, device=embeddings.device)
    if strategy == IGBaselineStrategy.EXPLICIT_TENSOR:
        if explicit_baseline is None:
            raise ValueError("explicit_baseline required for EXPLICIT_TENSOR")
        if explicit_baseline.shape != embeddings.shape:
            raise ValueError("explicit_baseline shape must match embeddings")
        return explicit_baseline.to(dtype=embeddings.dtype, device=embeddings.device)
    raise ValueError(f"Unknown baseline strategy: {strategy}")


def integrated_gradients(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    steps: int = 32,
    baseline_strategy: IGBaselineStrategy = IGBaselineStrategy.ZERO_EMBEDDING,
    pad_embedding: Tensor | None = None,
    explicit_baseline: Tensor | None = None,
    method_name: str = "integrated_gradients",
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
) -> AttributionResult:
    """IG attributions (signed) with completeness diagnostic in metadata.

    Attribution object: input embeddings. Token score = sum over embedding dims.
    """
    if steps < 1:
        raise ValueError("steps must be >= 1")
    x = embeddings.detach()
    baseline = resolve_baseline(
        x,
        strategy=baseline_strategy,
        pad_embedding=pad_embedding,
        explicit_baseline=explicit_baseline,
    )
    delta = x - baseline
    total_grad = torch.zeros_like(x)
    for i in range(1, steps + 1):
        alpha = float(i) / float(steps)
        x_alpha = (baseline + alpha * delta).requires_grad_(True)
        s = score_fn(x_alpha)
        (g,) = torch.autograd.grad(s, x_alpha, retain_graph=False)
        total_grad = total_grad + g
    avg_grad = total_grad / float(steps)
    attr = delta * avg_grad  # (B,T,D)
    token_scores = attr[0].sum(dim=-1).detach().cpu()

    with torch.no_grad():
        f_x = float(score_fn(x).detach().cpu())
        f_b = float(score_fn(baseline).detach().cpu())
    completeness_gap = float(token_scores.sum()) - (f_x - f_b)

    meta: dict[str, Any] = {
        "steps": steps,
        "baseline_strategy": baseline_strategy.value,
        "f_input": f_x,
        "f_baseline": f_b,
        "sum_attributions": float(token_scores.sum()),
        "completeness_gap": completeness_gap,
        "completeness_target": f_x - f_b,
        "reduction": "SUM_OVER_EMBEDDING_DIM",
        "abs_applied": False,
        "note": "Baseline is a protocol option; not a frozen scientific default.",
    }
    return AttributionResult(
        method_name=method_name,
        score_space=ScoreSpace.TOKEN,
        signed=True,
        target_definition=target,
        token_scores=token_scores.tolist(),
        metadata=meta,
    )


def completeness_holds(
    result: AttributionResult,
    *,
    atol: float = 1e-3,
    rtol: float = 1e-3,
) -> bool:
    """True if sum(attr) ≈ f(input) - f(baseline) within tolerance."""
    gap = float(result.metadata["completeness_gap"])
    target = float(result.metadata["completeness_target"])
    return abs(gap) <= (atol + rtol * abs(target))

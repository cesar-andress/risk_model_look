"""Vanilla gradient and Grad×Input primitives against risk logit contrast.

Preferred attribution object: input embedding tensor.
For Grad×Input, token score = sum over embedding dimensions (preserves sign).
Do NOT take abs() in the core method.
"""

from __future__ import annotations

from typing import Any, Callable

import torch
from torch import Tensor

from src.attribution.base import AttributionResult, ScoreSpace, TargetDefinition
from src.attribution.targets import M1_RISK_LOGIT_CONTRAST, risk_logit_contrast


ScoreFn = Callable[[Tensor], Tensor]
"""Maps embeddings (1, T, D) -> scalar tensor s(x)."""


def extract_embedding_gradient(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    create_graph: bool = False,
) -> Tensor:
    """Return ∂s/∂embeddings with shape matching ``embeddings``.

    ``embeddings`` must require grad (or a leaf clone is created).
    """
    if embeddings.dim() != 3:
        raise ValueError(f"expected (B,T,D) embeddings, got {tuple(embeddings.shape)}")
    emb = embeddings
    if not emb.requires_grad:
        emb = emb.detach().requires_grad_(True)
    s = score_fn(emb)
    if s.numel() != 1:
        raise ValueError("score_fn must return a scalar")
    (grad,) = torch.autograd.grad(s, emb, create_graph=create_graph, retain_graph=False)
    assert grad is not None
    return grad


def vanilla_gradient_token_scores(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    method_name: str = "gradient",
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
    metadata: dict[str, Any] | None = None,
) -> AttributionResult:
    """Token score = sum_d ∂s/∂e_{t,d} (signed)."""
    grad = extract_embedding_gradient(embeddings, score_fn)
    # Use batch 0 for single-example attribution infrastructure.
    g0 = grad[0]
    scores = g0.sum(dim=-1).detach().cpu().tolist()
    meta = {"reduction": "SUM_OVER_EMBEDDING_DIM", "abs_applied": False}
    if metadata:
        meta.update(metadata)
    return AttributionResult(
        method_name=method_name,
        score_space=ScoreSpace.TOKEN,
        signed=True,
        target_definition=target,
        token_scores=scores,
        metadata=meta,
    )


def grad_x_input_token_scores(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    method_name: str = "grad_x_input",
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
    metadata: dict[str, Any] | None = None,
) -> AttributionResult:
    """Token score = sum_d (e_{t,d} * ∂s/∂e_{t,d}); sign preserved."""
    emb = embeddings
    if not emb.requires_grad:
        emb = emb.detach().requires_grad_(True)
    grad = extract_embedding_gradient(emb, score_fn)
    prod = emb * grad
    scores = prod[0].sum(dim=-1).detach().cpu().tolist()
    meta = {
        "reduction": "SUM_OVER_EMBEDDING_DIM",
        "abs_applied": False,
        "formula": "sum_d e * ds/de",
    }
    if metadata:
        meta.update(metadata)
    return AttributionResult(
        method_name=method_name,
        score_space=ScoreSpace.TOKEN,
        signed=True,
        target_definition=target,
        token_scores=scores,
        metadata=meta,
    )


def risk_contrast_score_fn_from_logits_fn(
    logits_fn: Callable[[Tensor], tuple[Tensor, Tensor]],
) -> ScoreFn:
    """Wrap a function returning (logit_0, logit_1) into s = l1 - l0."""

    def score_fn(embeddings: Tensor) -> Tensor:
        l0, l1 = logits_fn(embeddings)
        return l1 - l0

    return score_fn


def numpy_risk_from_torch_logits(logit_0: float, logit_1: float) -> float:
    return risk_logit_contrast(logit_0, logit_1)

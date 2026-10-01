"""Integrated Gradients with frozen protocol options (CPU-safe module).

Primary baseline: ZERO_EMBEDDING (canonical/reproducible; NOT assumed neutral).
Integration: GAUSS_LEGENDRE. Completeness + adaptive 50→100 retry.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

import numpy as np
import torch
from torch import Tensor

from src.attribution.base import AttributionResult, ScoreSpace, TargetDefinition
from src.attribution.targets import M1_RISK_LOGIT_CONTRAST


class IGBaselineStrategy(str, Enum):
    ZERO_EMBEDDING = "ZERO_EMBEDDING"
    PAD_TOKEN_EMBEDDING = "PAD_TOKEN_EMBEDDING"
    EXPLICIT_TENSOR = "EXPLICIT_TENSOR"


class IntegrationRule(str, Enum):
    GAUSS_LEGENDRE = "GAUSS_LEGENDRE"
    RIEMANN = "RIEMANN"  # diagnostic only; not primary protocol


ScoreFn = Callable[[Tensor], Tensor]

IG_INITIAL_STEPS = 50
IG_RETRY_STEPS = 100
IG_REL_TOL = 0.05
IG_ABS_FLOOR = 1e-6


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


def gauss_legendre_unit_interval(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Nodes/weights on [0, 1] from Gauss–Legendre on [-1, 1]."""
    if n < 1:
        raise ValueError("n must be >= 1")
    x, w = np.polynomial.legendre.leggauss(n)
    # Map [-1,1] -> [0,1]: t = (x+1)/2, dt = dx/2
    t = 0.5 * (x + 1.0)
    wt = 0.5 * w
    return t.astype(np.float64), wt.astype(np.float64)


def _accumulate_ig(
    embeddings: Tensor,
    baseline: Tensor,
    score_fn: ScoreFn,
    *,
    steps: int,
    rule: IntegrationRule,
) -> Tensor:
    """Return attribution tensor (B,T,D) without completeness metadata."""
    x = embeddings.detach()
    delta = x - baseline
    if rule == IntegrationRule.GAUSS_LEGENDRE:
        alphas, weights = gauss_legendre_unit_interval(steps)
        total = torch.zeros_like(x)
        for a, w in zip(alphas, weights):
            x_a = (baseline + float(a) * delta).requires_grad_(True)
            s = score_fn(x_a)
            (g,) = torch.autograd.grad(s, x_a, retain_graph=False)
            total = total + float(w) * g
        return delta * total
    if rule == IntegrationRule.RIEMANN:
        total_grad = torch.zeros_like(x)
        for i in range(1, steps + 1):
            alpha = float(i) / float(steps)
            x_alpha = (baseline + alpha * delta).requires_grad_(True)
            s = score_fn(x_alpha)
            (g,) = torch.autograd.grad(s, x_alpha, retain_graph=False)
            total_grad = total_grad + g
        avg_grad = total_grad / float(steps)
        return delta * avg_grad
    raise ValueError(f"Unknown integration rule: {rule}")


def completeness_errors(
    attr_sum: float,
    f_input: float,
    f_baseline: float,
    *,
    abs_floor: float = IG_ABS_FLOOR,
) -> dict[str, float]:
    target_delta = f_input - f_baseline
    e_abs = abs(attr_sum - target_delta)
    e_rel = e_abs / max(abs(target_delta), abs_floor)
    return {
        "target_delta": float(target_delta),
        "attr_sum": float(attr_sum),
        "E_abs": float(e_abs),
        "E_rel": float(e_rel),
    }


def integrated_gradients(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    steps: int = IG_INITIAL_STEPS,
    baseline_strategy: IGBaselineStrategy = IGBaselineStrategy.ZERO_EMBEDDING,
    pad_embedding: Tensor | None = None,
    explicit_baseline: Tensor | None = None,
    integration_rule: IntegrationRule = IntegrationRule.GAUSS_LEGENDRE,
    method_name: str = "integrated_gradients",
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
) -> AttributionResult:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    x = embeddings.detach()
    baseline = resolve_baseline(
        x,
        strategy=baseline_strategy,
        pad_embedding=pad_embedding,
        explicit_baseline=explicit_baseline,
    )
    attr = _accumulate_ig(
        x, baseline, score_fn, steps=steps, rule=integration_rule
    )
    token_scores = attr[0].sum(dim=-1).detach().cpu()
    with torch.no_grad():
        f_x = float(score_fn(x).detach().cpu())
        f_b = float(score_fn(baseline).detach().cpu())
    errs = completeness_errors(float(token_scores.sum()), f_x, f_b)
    meta: dict[str, Any] = {
        "steps": steps,
        "baseline_strategy": baseline_strategy.value,
        "integration_rule": integration_rule.value,
        "f_input": f_x,
        "f_baseline": f_b,
        "sum_attributions": float(token_scores.sum()),
        "completeness_gap": float(token_scores.sum()) - (f_x - f_b),
        "completeness_target": f_x - f_b,
        **errs,
        "reduction": "SUM_OVER_EMBEDDING_DIM",
        "abs_applied": False,
        "IG_NONCONVERGED": False,
        "note": "ZERO_EMBEDDING is reproducible, not assumed semantically neutral.",
    }
    return AttributionResult(
        method_name=method_name,
        score_space=ScoreSpace.TOKEN,
        signed=True,
        target_definition=target,
        token_scores=token_scores.tolist(),
        metadata=meta,
    )


def integrated_gradients_with_retry(
    embeddings: Tensor,
    score_fn: ScoreFn,
    *,
    initial_steps: int = IG_INITIAL_STEPS,
    retry_steps: int = IG_RETRY_STEPS,
    rel_tol: float = IG_REL_TOL,
    baseline_strategy: IGBaselineStrategy = IGBaselineStrategy.ZERO_EMBEDDING,
    pad_embedding: Tensor | None = None,
    explicit_baseline: Tensor | None = None,
    integration_rule: IntegrationRule = IntegrationRule.GAUSS_LEGENDRE,
    method_name: str = "integrated_gradients",
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
) -> AttributionResult:
    """Protocol adaptive retry: 50 → 100 steps; else IG_NONCONVERGED."""
    first = integrated_gradients(
        embeddings,
        score_fn,
        steps=initial_steps,
        baseline_strategy=baseline_strategy,
        pad_embedding=pad_embedding,
        explicit_baseline=explicit_baseline,
        integration_rule=integration_rule,
        method_name=method_name,
        target=target,
    )
    e_rel = float(first.metadata["E_rel"])
    if e_rel <= rel_tol:
        meta = dict(first.metadata)
        meta.update({"retry_applied": False, "accepted_steps": initial_steps})
        return AttributionResult(
            method_name=first.method_name,
            score_space=first.score_space,
            signed=first.signed,
            target_definition=first.target_definition,
            token_scores=first.token_scores,
            metadata=meta,
        )
    second = integrated_gradients(
        embeddings,
        score_fn,
        steps=retry_steps,
        baseline_strategy=baseline_strategy,
        pad_embedding=pad_embedding,
        explicit_baseline=explicit_baseline,
        integration_rule=integration_rule,
        method_name=method_name,
        target=target,
    )
    e_rel2 = float(second.metadata["E_rel"])
    meta = dict(second.metadata)
    meta.update(
        {
            "retry_applied": True,
            "initial_steps": initial_steps,
            "initial_E_rel": e_rel,
            "accepted_steps": retry_steps,
            "IG_NONCONVERGED": e_rel2 > rel_tol,
        }
    )
    return AttributionResult(
        method_name=second.method_name,
        score_space=second.score_space,
        signed=second.signed,
        target_definition=second.target_definition,
        token_scores=second.token_scores,
        metadata=meta,
    )


def completeness_holds(
    result: AttributionResult,
    *,
    rel_tol: float = IG_REL_TOL,
) -> bool:
    return float(result.metadata["E_rel"]) <= rel_tol and not bool(
        result.metadata.get("IG_NONCONVERGED", False)
    )

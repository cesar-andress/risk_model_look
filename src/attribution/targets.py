"""Canonical explanation targets for M1.

Preferred scalar for gradient-based and perturbation methods:

    s(x) = logit_1(x) - logit_0(x)

This is signed and monotonic with the restricted two-class probability
p_buggy = softmax([l0, l1])[1].

Primary attribution must NOT use generated-token likelihood, argmax class
alone, or full-vocabulary probability as the target.
"""

from __future__ import annotations

import math
from typing import Sequence

from src.attribution.base import TargetDefinition

M1_RISK_LOGIT_CONTRAST = TargetDefinition(
    name="risk_logit_contrast",
    formula="s(x) = logit_1(x) - logit_0(x)",
    signed=True,
    notes=(
        "Canonical M1 explanation target. Equivalent to logit(p_buggy/(1-p_buggy)) "
        "for the restricted two-class softmax over label tokens 0 and 1."
    ),
)


def risk_logit_contrast(logit_0: float, logit_1: float) -> float:
    """Pure function: s = l1 - l0."""
    return float(logit_1) - float(logit_0)


def p_buggy_from_logits(logit_0: float, logit_1: float) -> float:
    """Restricted two-class probability p_buggy = softmax([l0, l1])[1]."""
    l0 = float(logit_0)
    l1 = float(logit_1)
    m = max(l0, l1)
    e0 = math.exp(l0 - m)
    e1 = math.exp(l1 - m)
    return e1 / (e0 + e1)


def logit_of_odds(p: float, *, eps: float = 1e-12) -> float:
    """logit(p / (1-p)) = log(p) - log(1-p), with clamp for numerical safety."""
    p = min(max(float(p), eps), 1.0 - eps)
    return math.log(p) - math.log(1.0 - p)


def verify_logit_odds_identity(
    logit_0: float,
    logit_1: float,
    *,
    atol: float = 1e-9,
    rtol: float = 1e-9,
) -> dict[str, float | bool]:
    """Check logit(p_buggy/(1-p_buggy)) == l1 - l0 within tolerance."""
    p = p_buggy_from_logits(logit_0, logit_1)
    left = logit_of_odds(p)
    right = risk_logit_contrast(logit_0, logit_1)
    ok = abs(left - right) <= (atol + rtol * abs(right))
    return {
        "p_buggy": p,
        "logit_odds": left,
        "risk_logit_contrast": right,
        "abs_diff": abs(left - right),
        "ok": ok,
    }


def score_from_logits(
    logit_0: float,
    logit_1: float,
    *,
    space: str = "logit_contrast",
) -> float:
    """Score in logit-contrast or probability space."""
    if space == "logit_contrast":
        return risk_logit_contrast(logit_0, logit_1)
    if space == "probability":
        return p_buggy_from_logits(logit_0, logit_1)
    raise ValueError(f"Unknown score space: {space!r}")


def batch_risk_logit_contrast(
    logits_01: Sequence[Sequence[float]],
) -> list[float]:
    """Vectorized convenience: each row is [l0, l1]."""
    out: list[float] = []
    for row in logits_01:
        if len(row) != 2:
            raise ValueError("each row must be [logit_0, logit_1]")
        out.append(risk_logit_contrast(row[0], row[1]))
    return out

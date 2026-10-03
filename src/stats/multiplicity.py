"""Holm FWER multiplicity correction (Protocol V1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


ALPHA = 0.05


@dataclass(frozen=True)
class HolmItem:
    name: str
    raw_p: float
    adjusted_p: float
    family: str
    role: str  # PRIMARY | SECONDARY | SENSITIVITY | EXPLORATORY


def holm_adjust(
    named_pvalues: Sequence[tuple[str, float]],
    *,
    alpha: float = ALPHA,
    family: str,
    role: str = "PRIMARY",
) -> list[HolmItem]:
    """Holm step-down adjustment within one family.

    Do not mix PRIMARY and SENSITIVITY in the same call.
    """
    if role == "PRIMARY" and family == "SENSITIVITY":
        raise ValueError("Do not mix primary role into SENSITIVITY family call")
    items = [(name, float(p)) for name, p in named_pvalues]
    m = len(items)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: items[i][1])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        # Holm: p_adj = max_{j<=i} ( (m-j+1) * p_(j) )
        factor = m - rank
        cand = min(1.0, factor * items[idx][1])
        running = max(running, cand)
        adjusted[idx] = running
    # Enforce monotonicity in sorted order (already via running max)
    return [
        HolmItem(
            name=items[i][0],
            raw_p=items[i][1],
            adjusted_p=float(adjusted[i]),
            family=family,
            role=role,
        )
        for i in range(m)
    ]


def format_p(p: float) -> str:
    if p != p:  # NaN
        return "NA"
    if p < 0.001:
        return "p < 0.001"
    return f"p = {p:.3f}"

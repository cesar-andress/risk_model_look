"""Token-budget prefix selection and absolute perturbation faithfulness (V1.2)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence


PRIMARY_TOKEN_BUDGET_FRACTIONS = (0.10, 0.20, 0.30, 0.50)


def token_budget(total_tokens: int, f: float) -> int:
    """budget_tokens = max(1, ceil(f*T)) for T>0; else 0."""
    if total_tokens < 0:
        raise ValueError("total_tokens must be >= 0")
    if total_tokens == 0:
        return 0
    if f < 0:
        raise ValueError("f must be >= 0")
    return max(1, int(math.ceil(f * total_tokens)))


@dataclass(frozen=True)
class TokenBudgetPrefix:
    fraction: float
    target_token_budget: int
    region_ids: tuple[str, ...]
    realized_token_count: int
    overshoot: int


def select_token_budget_prefix(
    ranked_region_ids: Sequence[str],
    region_token_counts: Sequence[int],
    *,
    fraction: float,
    total_tokens: int | None = None,
) -> TokenBudgetPrefix:
    """TOKEN_BUDGET_PREFIX_V1: smallest prefix with cumulative tokens >= budget.

    Does not split semantic regions.
    """
    if len(ranked_region_ids) != len(region_token_counts):
        raise ValueError("region ids / token counts length mismatch")
    ids = list(ranked_region_ids)
    toks = [int(t) for t in region_token_counts]
    if any(t < 0 for t in toks):
        raise ValueError("token counts must be >= 0")
    t_total = int(total_tokens) if total_tokens is not None else int(sum(toks))
    budget = token_budget(t_total, float(fraction))
    if budget == 0 or not ids:
        return TokenBudgetPrefix(
            fraction=float(fraction),
            target_token_budget=budget,
            region_ids=tuple(),
            realized_token_count=0,
            overshoot=0,
        )
    cum = 0
    selected: list[str] = []
    for rid, tc in zip(ids, toks):
        selected.append(rid)
        cum += tc
        if cum >= budget:
            break
    return TokenBudgetPrefix(
        fraction=float(fraction),
        target_token_budget=budget,
        region_ids=tuple(selected),
        realized_token_count=cum,
        overshoot=max(0, cum - budget),
    )


def abs_perturbation_impact(score_full: float, score_perturbed: float) -> float:
    """ABS_PERTURBATION_IMPACT_f = abs(s(x) - s(x_perturbed_f))."""
    return abs(float(score_full) - float(score_perturbed))


def positive_evidence_drop(score_full: float, score_perturbed: float) -> float:
    """POSITIVE_EVIDENCE_DROP_f = s(x) - s(x_perturbed_f) (directional)."""
    return float(score_full) - float(score_perturbed)


def abs_insertion_gain(score_insert: float, score_base: float) -> float:
    """ABS_INSERTION_GAIN_f = abs(s(x_insert_f) - s(base))."""
    return abs(float(score_insert) - float(score_base))


@dataclass
class AbsoluteFaithfulnessCurve:
    fractions: tuple[float, ...] = PRIMARY_TOKEN_BUDGET_FRACTIONS
    impacts: dict[float, float] = field(default_factory=dict)
    prefixes: dict[float, TokenBudgetPrefix] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def evaluate_abs_deletion_curve(
    ranked_region_ids: Sequence[str],
    region_token_counts: Sequence[int],
    *,
    score_full: float,
    score_blanked_fn: Callable[[Sequence[str]], float],
    fractions: Sequence[float] = PRIMARY_TOKEN_BUDGET_FRACTIONS,
) -> AbsoluteFaithfulnessCurve:
    """Primary RQ2 curve under TOKEN_BUDGET_PREFIX_V1 + ABS impact."""
    curve = AbsoluteFaithfulnessCurve(fractions=tuple(float(f) for f in fractions))
    t_total = int(sum(int(t) for t in region_token_counts))
    for frac in fractions:
        pref = select_token_budget_prefix(
            ranked_region_ids,
            region_token_counts,
            fraction=float(frac),
            total_tokens=t_total,
        )
        curve.prefixes[float(frac)] = pref
        if not pref.region_ids:
            curve.impacts[float(frac)] = 0.0
            continue
        s_p = float(score_blanked_fn(list(pref.region_ids)))
        curve.impacts[float(frac)] = abs_perturbation_impact(score_full, s_p)
    curve.metadata["construct"] = "ABSOLUTE_PERTURBATION_FAITHFULNESS"
    curve.metadata["budgeting"] = "TOKEN_BUDGET_PREFIX_V1"
    curve.metadata["operator"] = "PAYLOAD_BLANK_V1"
    return curve


def abs_deletion_aopc(impacts: dict[float, float]) -> float:
    """ABS_DELETION_AOPC = mean_f ABS_PERTURBATION_IMPACT_f."""
    if not impacts:
        return 0.0
    return float(sum(impacts.values()) / len(impacts))


def token_matched_random_regions(
    region_ids: Sequence[str],
    region_token_counts: Sequence[int],
    *,
    target_tokens: int,
    seed: int,
    trials: int = 256,
) -> tuple[list[str], int]:
    """Deterministic random region set closest to target payload token count.

    Does not split regions. Returns (region_ids, abs_token_diff).
    """
    import numpy as np

    ids = list(region_ids)
    toks = [int(t) for t in region_token_counts]
    n = len(ids)
    if n == 0:
        return [], abs(int(target_tokens))
    if len(toks) != n:
        raise ValueError("length mismatch")
    rng = np.random.default_rng(int(seed))
    best: list[str] | None = None
    best_diff = float("inf")
    best_tok = 0
    # Greedy random prefixes of shuffled order until >= target, then record.
    for _ in range(max(1, trials)):
        order = rng.permutation(n)
        cum = 0
        selected_idx: list[int] = []
        for i in order:
            selected_idx.append(int(i))
            cum += toks[int(i)]
            if cum >= target_tokens or len(selected_idx) == n:
                break
        diff = abs(cum - target_tokens)
        if diff < best_diff:
            best_diff = diff
            best_tok = cum
            best = [ids[i] for i in sorted(selected_idx)]
        if diff == 0:
            break
    assert best is not None
    return best, int(abs(best_tok - target_tokens))

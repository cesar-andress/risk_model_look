"""RQ3 polarity analysis over signed region scores."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PolaritySummary:
    n: int
    fraction_positive: float
    fraction_negative: float
    fraction_near_zero: float
    top_positive: tuple[tuple[str, float], ...]
    top_negative: tuple[tuple[str, float], ...]
    epsilon: float


def polarity_summary(
    region_scores: Mapping[str, float],
    *,
    epsilon: float,
    top_k: int = 5,
) -> PolaritySummary:
    """Polarity fractions with explicit near-zero epsilon (required)."""
    if epsilon < 0:
        raise ValueError("epsilon must be >= 0")
    items = list(region_scores.items())
    n = len(items)
    if n == 0:
        return PolaritySummary(0, 0.0, 0.0, 0.0, (), (), epsilon)
    pos = [(k, v) for k, v in items if v > epsilon]
    neg = [(k, v) for k, v in items if v < -epsilon]
    near = [(k, v) for k, v in items if abs(v) <= epsilon]
    pos_sorted = sorted(pos, key=lambda kv: (-kv[1], kv[0]))[:top_k]
    neg_sorted = sorted(neg, key=lambda kv: (kv[1], kv[0]))[:top_k]
    return PolaritySummary(
        n=n,
        fraction_positive=len(pos) / n,
        fraction_negative=len(neg) / n,
        fraction_near_zero=len(near) / n,
        top_positive=tuple(pos_sorted),
        top_negative=tuple(neg_sorted),
        epsilon=epsilon,
    )


def _sign(v: float, epsilon: float) -> int:
    if v > epsilon:
        return 1
    if v < -epsilon:
        return -1
    return 0


def sign_agreement(
    attribution_scores: Mapping[str, float],
    occlusion_deltas: Mapping[str, float],
    *,
    epsilon: float,
) -> dict[str, float | int]:
    """Sign agreement between attribution a_R and occlusion delta_R.

    Caveat: this is agreement under the chosen epsilon, not causal correctness.
    """
    if epsilon < 0:
        raise ValueError("epsilon must be >= 0")
    keys = sorted(set(attribution_scores) & set(occlusion_deltas))
    if not keys:
        return {
            "n_compared": 0,
            "sign_agreement": 0.0,
            "positive_precision_like": 0.0,
            "negative_agreement": 0.0,
            "coverage_excluding_near_zero": 0.0,
            "caveat": "not_causal_correctness",
        }
    agree = 0
    covered = 0
    attr_pos = 0
    attr_pos_agree = 0
    both_neg = 0
    for k in keys:
        sa = _sign(float(attribution_scores[k]), epsilon)
        sd = _sign(float(occlusion_deltas[k]), epsilon)
        if sa == 0 or sd == 0:
            continue
        covered += 1
        if sa == sd:
            agree += 1
        if sa == 1:
            attr_pos += 1
            if sd == 1:
                attr_pos_agree += 1
        if sa == -1 and sd == -1:
            both_neg += 1
    return {
        "n_compared": len(keys),
        "n_covered_nonzero": covered,
        "sign_agreement": (agree / covered) if covered else 0.0,
        "positive_precision_like": (attr_pos_agree / attr_pos) if attr_pos else 0.0,
        "negative_agreement": (both_neg / covered) if covered else 0.0,
        "coverage_excluding_near_zero": covered / len(keys),
        "epsilon": epsilon,
        "caveat": "not_causal_correctness",
    }


def method_sign_agreement(
    scores_a: Mapping[str, float],
    scores_b: Mapping[str, float],
    *,
    epsilon: float,
) -> dict[str, float | int]:
    """Pairwise sign agreement between two attribution methods."""
    return sign_agreement(scores_a, scores_b, epsilon=epsilon)

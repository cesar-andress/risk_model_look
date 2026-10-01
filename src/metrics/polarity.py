"""RQ3 polarity with frozen RELATIVE_POLARITY_EPS_V1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class PolarityClass(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEAR_ZERO = "NEAR_ZERO"


def relative_polarity_epsilon(scores: Mapping[str, float]) -> float:
    """epsilon = max(1e-8, 1e-6 * M) with M = max|score|; M==0 => all near-zero."""
    if not scores:
        return 1e-8
    m = max(abs(float(v)) for v in scores.values())
    if m == 0.0:
        return 0.0  # every score is exactly zero → all NEAR_ZERO under classify
    return max(1e-8, 1e-6 * m)


def classify_polarity(score: float, epsilon: float, *, all_zero_universe: bool = False) -> PolarityClass:
    if all_zero_universe or epsilon == 0.0:
        # Protocol: if M == 0, all regions are NEAR_ZERO
        return PolarityClass.NEAR_ZERO
    if score > epsilon:
        return PolarityClass.POSITIVE
    if score < -epsilon:
        return PolarityClass.NEGATIVE
    return PolarityClass.NEAR_ZERO


def classify_region_scores(region_scores: Mapping[str, float]) -> dict[str, PolarityClass]:
    if not region_scores:
        return {}
    m = max(abs(float(v)) for v in region_scores.values())
    if m == 0.0:
        return {k: PolarityClass.NEAR_ZERO for k in region_scores}
    eps = relative_polarity_epsilon(region_scores)
    return {k: classify_polarity(float(v), eps) for k, v in region_scores.items()}


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
    epsilon: float | None = None,
    top_k: int = 5,
) -> PolaritySummary:
    """If epsilon is None, use RELATIVE_POLARITY_EPS_V1 from the score set."""
    items = list(region_scores.items())
    n = len(items)
    if n == 0:
        return PolaritySummary(0, 0.0, 0.0, 0.0, (), (), 1e-8)
    classes = classify_region_scores(region_scores)
    eps = relative_polarity_epsilon(region_scores) if epsilon is None else float(epsilon)
    # If caller overrides epsilon, reclassify with that epsilon (except M==0)
    m = max(abs(float(v)) for v in region_scores.values())
    if m == 0.0:
        classes = {k: PolarityClass.NEAR_ZERO for k in region_scores}
        eps = 0.0
    elif epsilon is not None:
        classes = {k: classify_polarity(float(v), eps) for k, v in region_scores.items()}
    pos = [(k, float(region_scores[k])) for k, c in classes.items() if c == PolarityClass.POSITIVE]
    neg = [(k, float(region_scores[k])) for k, c in classes.items() if c == PolarityClass.NEGATIVE]
    near = [k for k, c in classes.items() if c == PolarityClass.NEAR_ZERO]
    pos_sorted = sorted(pos, key=lambda kv: (-kv[1], kv[0]))[:top_k]
    neg_sorted = sorted(neg, key=lambda kv: (kv[1], kv[0]))[:top_k]
    return PolaritySummary(
        n=n,
        fraction_positive=len(pos) / n,
        fraction_negative=len(neg) / n,
        fraction_near_zero=len(near) / n,
        top_positive=tuple(pos_sorted),
        top_negative=tuple(neg_sorted),
        epsilon=eps,
    )


def sign_agreement(
    attribution_scores: Mapping[str, float],
    occlusion_deltas: Mapping[str, float],
    *,
    epsilon: float | None = None,
) -> dict[str, float | int | str]:
    """Strict sign agreement excluding NEAR_ZERO on either side.

    Caveat: agreement ≠ causal correctness.
    """
    keys = sorted(set(attribution_scores) & set(occlusion_deltas))
    if not keys:
        return {
            "n_compared": 0,
            "n_covered_nonzero": 0,
            "agreement_coverage": 0.0,
            "sign_agreement": 0.0,
            "positive_agreement": 0.0,
            "negative_agreement": 0.0,
            "near_zero_frequency_attr": 0.0,
            "near_zero_frequency_occ": 0.0,
            "caveat": "not_causal_correctness",
        }
    # Classify each side independently with its own relative epsilon (protocol)
    attr_cls = classify_region_scores({k: float(attribution_scores[k]) for k in keys})
    occ_cls = classify_region_scores({k: float(occlusion_deltas[k]) for k in keys})
    # Optional shared override epsilon for synthetic tests
    if epsilon is not None:
        attr_cls = {k: classify_polarity(float(attribution_scores[k]), float(epsilon)) for k in keys}
        occ_cls = {k: classify_polarity(float(occlusion_deltas[k]), float(epsilon)) for k in keys}

    nz_attr = sum(1 for k in keys if attr_cls[k] == PolarityClass.NEAR_ZERO)
    nz_occ = sum(1 for k in keys if occ_cls[k] == PolarityClass.NEAR_ZERO)
    covered = [
        k
        for k in keys
        if attr_cls[k] != PolarityClass.NEAR_ZERO and occ_cls[k] != PolarityClass.NEAR_ZERO
    ]
    agree = sum(1 for k in covered if attr_cls[k] == occ_cls[k])
    pos_pairs = [k for k in covered if attr_cls[k] == PolarityClass.POSITIVE]
    pos_agree = sum(1 for k in pos_pairs if occ_cls[k] == PolarityClass.POSITIVE)
    neg_pairs = [k for k in covered if attr_cls[k] == PolarityClass.NEGATIVE]
    neg_agree = sum(1 for k in neg_pairs if occ_cls[k] == PolarityClass.NEGATIVE)
    return {
        "n_compared": len(keys),
        "n_covered_nonzero": len(covered),
        "agreement_coverage": len(covered) / len(keys),
        "sign_agreement": (agree / len(covered)) if covered else 0.0,
        "positive_agreement": (pos_agree / len(pos_pairs)) if pos_pairs else 0.0,
        "negative_agreement": (neg_agree / len(neg_pairs)) if neg_pairs else 0.0,
        "near_zero_frequency_attr": nz_attr / len(keys),
        "near_zero_frequency_occ": nz_occ / len(keys),
        "epsilon_rule": "RELATIVE_POLARITY_EPS_V1" if epsilon is None else "OVERRIDE",
        "caveat": "not_causal_correctness",
    }


def method_sign_agreement(
    scores_a: Mapping[str, float],
    scores_b: Mapping[str, float],
    *,
    epsilon: float | None = None,
) -> dict[str, float | int | str]:
    return sign_agreement(scores_a, scores_b, epsilon=epsilon)


def attention_top2_hunk_negative_occlusion_fraction(
    attention_hunk_scores: Mapping[str, float],
    occlusion_hunk_deltas: Mapping[str, float],
) -> dict[str, float | int | str | list[str]]:
    """RQ3 ATTENTION_TOP2_HUNK_OCCLUSION_SIGN_V1.

    Top-2 hunks by attention (RAW descending). Among those with resolvable
    occlusion deltas, report fraction classified NEGATIVE under
    RELATIVE_POLARITY_EPS_V1 applied to the occlusion delta set used.
    """
    if not attention_hunk_scores:
        return {
            "metric": "ATTENTION_TOP2_HUNK_OCCLUSION_SIGN_V1",
            "n_top": 0,
            "top_hunk_ids": [],
            "fraction_negative_occlusion": 0.0,
            "n_negative": 0,
            "n_near_zero": 0,
            "n_scored": 0,
        }
    ranked = sorted(
        attention_hunk_scores.items(),
        key=lambda kv: (-float(kv[1]), str(kv[0])),
    )
    top2 = [h for h, _ in ranked[:2]]
    deltas = {h: float(occlusion_hunk_deltas[h]) for h in top2 if h in occlusion_hunk_deltas}
    # Classify using relative eps over the available top-2 deltas (and note missing)
    classes = classify_region_scores(deltas) if deltas else {}
    n_neg = sum(1 for c in classes.values() if c == PolarityClass.NEGATIVE)
    n_near = sum(1 for c in classes.values() if c == PolarityClass.NEAR_ZERO)
    n_scored = len(classes)
    # Fraction among scored non-near-zero? Protocol: fraction of top-2 whose class is NEGATIVE
    # Near-zero excluded from numerator; denominator is len(top2) with note — report both.
    return {
        "metric": "ATTENTION_TOP2_HUNK_OCCLUSION_SIGN_V1",
        "n_top": len(top2),
        "top_hunk_ids": top2,
        "fraction_negative_occlusion": (n_neg / len(top2)) if top2 else 0.0,
        "fraction_negative_among_scored_non_near_zero": (
            n_neg / max(1, n_scored - n_near)
        )
        if (n_scored - n_near) > 0
        else 0.0,
        "n_negative": n_neg,
        "n_near_zero": n_near,
        "n_scored": n_scored,
        "n_missing_occlusion": len(top2) - n_scored,
    }

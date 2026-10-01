"""RQ2 faithfulness metrics (prediction-perturbation).

Separated from localization/plausibility metrics. Do not call Top-k accuracy
"faithfulness".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Sequence

import numpy as np


class FaithfulnessScoreSpace(str, Enum):
    PROBABILITY = "probability"
    LOGIT_CONTRAST = "logit_contrast"


DEFAULT_PERTURBATION_FRACTIONS = (0.05, 0.10, 0.20, 0.30, 0.50)


@dataclass(frozen=True)
class FaithfulnessPair:
    """Precomputed scores for a full input and a perturbed variant."""

    score_full: float
    score_perturbed: float
    space: FaithfulnessScoreSpace


def comprehensiveness(score_full: float, score_without_R: float) -> float:
    """comprehensiveness = score(x) - score(x \\ R).

    Higher positive value ⇒ selected region removal reduces buggy evidence.
    Pure metric over precomputed scores; no model required.
    """
    return float(score_full) - float(score_without_R)


def sufficiency(
    score_full: float,
    score_R_only: float,
    *,
    form: str = "full_minus_region_only",
) -> dict[str, float | str]:
    """Sufficiency primitive with explicit form/sign documentation.

    Conventional form implemented here:

        sufficiency_raw = score(x) - score(R_only)

    Interpretation (documented, not mixed silently):
      - If scores are risk (higher = more buggy evidence):
        * Lower sufficiency_raw means R_only nearly recovers full score
          (R is more "sufficient" as an explanation under this form).
        * Therefore lower-is-more-sufficient for this raw definition.
      - Callers needing higher-is-better should use ``sufficiency_higher_better``
        = -sufficiency_raw, which is returned alongside.

    Do not mix orientations without recording which field is used.
    """
    if form != "full_minus_region_only":
        raise ValueError(f"Unsupported sufficiency form: {form}")
    raw = float(score_full) - float(score_R_only)
    return {
        "form": form,
        "sufficiency_raw_full_minus_region_only": raw,
        "orientation_raw": "lower_is_more_sufficient",
        "sufficiency_higher_better": -raw,
        "orientation_higher_better": "higher_is_more_sufficient",
        "score_full": float(score_full),
        "score_R_only": float(score_R_only),
    }


@dataclass
class PerturbationCurve:
    """Top-k / top-p removal curve container (no scientific results)."""

    fractions: tuple[float, ...] = DEFAULT_PERTURBATION_FRACTIONS
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST
    comprehensiveness_values: dict[float, float] = field(default_factory=dict)
    sufficiency_higher_better_values: dict[float, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def evaluate_removal_curve(
    ranked_region_ids: Sequence[str],
    *,
    score_full: float,
    score_without_fn: Callable[[Sequence[str]], float],
    score_only_fn: Callable[[Sequence[str]], float],
    fractions: Sequence[float] = DEFAULT_PERTURBATION_FRACTIONS,
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST,
) -> PerturbationCurve:
    """Evaluate comprehensiveness/sufficiency at configured removal fractions."""
    n = len(ranked_region_ids)
    curve = PerturbationCurve(fractions=tuple(fractions), space=space)
    for frac in fractions:
        k = max(1, int(round(frac * n))) if n else 0
        selected = list(ranked_region_ids[:k])
        if not selected:
            continue
        s_wo = float(score_without_fn(selected))
        s_only = float(score_only_fn(selected))
        curve.comprehensiveness_values[float(frac)] = comprehensiveness(score_full, s_wo)
        suf = sufficiency(score_full, s_only)
        curve.sufficiency_higher_better_values[float(frac)] = float(
            suf["sufficiency_higher_better"]
        )
    curve.metadata["n_regions"] = n
    return curve


def random_region_selection(
    region_ids: Sequence[str],
    k: int,
    *,
    seed: int,
) -> list[str]:
    """Deterministic random-region selection using an explicit seed."""
    if k < 0:
        raise ValueError("k must be >= 0")
    ids = list(region_ids)
    rng = np.random.default_rng(seed)
    if k >= len(ids):
        return ids
    idx = rng.choice(len(ids), size=k, replace=False)
    return [ids[i] for i in sorted(idx)]


def length_matched_random_selection(
    region_ids: Sequence[str],
    *,
    n_lines: int,
    seed: int,
    token_counts: Sequence[int] | None = None,
    token_budget: int | None = None,
    token_tolerance: float = 0.25,
) -> list[str]:
    """Random control matched approximately on line count and optionally tokens.

    When ``token_budget`` is set, prefers subsets whose total tokens are within
    ``token_tolerance`` relative error of the budget among line-count matches;
    falls back to closest token sum if none within tolerance.
    """
    ids = list(region_ids)
    n = len(ids)
    if n_lines < 0:
        raise ValueError("n_lines must be >= 0")
    if n_lines > n:
        raise ValueError("n_lines exceeds available regions")
    rng = np.random.default_rng(seed)
    if token_counts is None or token_budget is None:
        idx = rng.choice(n, size=n_lines, replace=False)
        return [ids[i] for i in sorted(idx)]
    if len(token_counts) != n:
        raise ValueError("token_counts length mismatch")

    # Sample multiple candidates deterministically; pick best token match.
    best: list[str] | None = None
    best_err = float("inf")
    trials = min(256, max(32, n * 2))
    for t in range(trials):
        idx = rng.choice(n, size=n_lines, replace=False)
        chosen = [ids[i] for i in idx]
        tok = sum(token_counts[i] for i in idx)
        err = abs(tok - token_budget) / max(1, token_budget)
        if err < best_err:
            best_err = err
            best = [ids[i] for i in sorted(idx)]
        if err <= token_tolerance:
            return [ids[i] for i in sorted(idx)]
    assert best is not None
    return best

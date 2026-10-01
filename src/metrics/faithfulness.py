"""RQ2 faithfulness metrics (prediction-perturbation).

Primary score space (frozen): LOGIT_CONTRAST.
Secondary: RESTRICTED_BINARY_PROBABILITY.
Localization / plausibility is NOT faithfulness (ERASER distinction).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Sequence

import numpy as np


class FaithfulnessScoreSpace(str, Enum):
    LOGIT_CONTRAST = "LOGIT_CONTRAST"
    RESTRICTED_BINARY_PROBABILITY = "RESTRICTED_BINARY_PROBABILITY"
    # legacy alias
    PROBABILITY = "RESTRICTED_BINARY_PROBABILITY"


FAITHFULNESS_PRIMARY_SCORE_SPACE = FaithfulnessScoreSpace.LOGIT_CONTRAST
FAITHFULNESS_SECONDARY_SCORE_SPACE = FaithfulnessScoreSpace.RESTRICTED_BINARY_PROBABILITY

DEFAULT_PERTURBATION_FRACTIONS = (0.05, 0.10, 0.20, 0.30, 0.50)


@dataclass(frozen=True)
class FaithfulnessPair:
    score_full: float
    score_perturbed: float
    space: FaithfulnessScoreSpace


def comprehensiveness(score_full: float, score_without_R: float) -> float:
    """COMP(R) = s(x) - s(x \\ R). Signed; do NOT abs under this name."""
    return float(score_full) - float(score_without_R)


def sufficiency_raw(score_full: float, score_R_only: float) -> float:
    """SUFF_RAW(R) = s(x) - s(R_only). Closer to zero ⇒ more sufficient."""
    return float(score_full) - float(score_R_only)


def sufficiency_error(score_full: float, score_R_only: float) -> float:
    """SUFF_ERROR(R) = abs(s(x) - s(R_only)). Higher is NOT better."""
    return abs(sufficiency_raw(score_full, score_R_only))


def sufficiency(
    score_full: float,
    score_R_only: float,
    *,
    form: str = "full_minus_region_only",
) -> dict[str, float | str]:
    if form != "full_minus_region_only":
        raise ValueError(f"Unsupported sufficiency form: {form}")
    raw = sufficiency_raw(score_full, score_R_only)
    err = sufficiency_error(score_full, score_R_only)
    return {
        "form": form,
        "SUFF_RAW": raw,
        "SUFF_ERROR": err,
        "orientation_raw": "closer_to_zero_is_more_sufficient",
        "orientation_error": "lower_is_better_nondirectional_error",
        # retained for older callers
        "sufficiency_raw_full_minus_region_only": raw,
        "sufficiency_higher_better": -err,  # only as convenience; prefer SUFF_ERROR
        "score_full": float(score_full),
        "score_R_only": float(score_R_only),
    }


@dataclass
class PerturbationCurve:
    fractions: tuple[float, ...] = DEFAULT_PERTURBATION_FRACTIONS
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST
    comprehensiveness_values: dict[float, float] = field(default_factory=dict)
    sufficiency_raw_values: dict[float, float] = field(default_factory=dict)
    sufficiency_error_values: dict[float, float] = field(default_factory=dict)
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
        curve.sufficiency_raw_values[float(frac)] = sufficiency_raw(score_full, s_only)
        curve.sufficiency_error_values[float(frac)] = sufficiency_error(score_full, s_only)
    curve.metadata["n_regions"] = n
    return curve


def random_region_selection(
    region_ids: Sequence[str],
    k: int,
    *,
    seed: int,
) -> list[str]:
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
    best: list[str] | None = None
    best_err = float("inf")
    trials = min(256, max(32, n * 2))
    for _ in range(trials):
        idx = rng.choice(n, size=n_lines, replace=False)
        tok = sum(token_counts[i] for i in idx)
        err = abs(tok - token_budget) / max(1, token_budget)
        if err < best_err:
            best_err = err
            best = [ids[i] for i in sorted(idx)]
        if err <= token_tolerance:
            return [ids[i] for i in sorted(idx)]
    assert best is not None
    return best

"""RQ2 faithfulness metrics — Protocol V1.1 amendments.

Primary fractions: 10%, 20%, 30%, 50%.
Rounding: k = max(1, ceil(f * N)).
Deletion / insertion curves + AOPC summaries.
Primary operator: PAYLOAD_BLANK_V1 (not SEGMENT_DELETE_V1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Sequence

import numpy as np


class FaithfulnessScoreSpace(str, Enum):
    LOGIT_CONTRAST = "LOGIT_CONTRAST"
    RESTRICTED_BINARY_PROBABILITY = "RESTRICTED_BINARY_PROBABILITY"
    PROBABILITY = "RESTRICTED_BINARY_PROBABILITY"


FAITHFULNESS_PRIMARY_SCORE_SPACE = FaithfulnessScoreSpace.LOGIT_CONTRAST
FAITHFULNESS_SECONDARY_SCORE_SPACE = FaithfulnessScoreSpace.RESTRICTED_BINARY_PROBABILITY

# V1.1 primary fractions (5% removed)
DEFAULT_PERTURBATION_FRACTIONS = (0.10, 0.20, 0.30, 0.50)
PRIMARY_FAITHFULNESS_FRACTIONS = DEFAULT_PERTURBATION_FRACTIONS


def fraction_to_k(n: int, f: float) -> int:
    """Frozen rounding: k = max(1, ceil(f * N)) for N > 0; else 0."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if n == 0:
        return 0
    if f < 0:
        raise ValueError("f must be >= 0")
    return max(1, int(math.ceil(f * n)))


def comprehensiveness(score_full: float, score_without_R: float) -> float:
    return float(score_full) - float(score_without_R)


def sufficiency_raw(score_full: float, score_R_only: float) -> float:
    return float(score_full) - float(score_R_only)


def sufficiency_error(score_full: float, score_R_only: float) -> float:
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
        "sufficiency_raw_full_minus_region_only": raw,
        "sufficiency_higher_better": -err,
        "score_full": float(score_full),
        "score_R_only": float(score_R_only),
    }


@dataclass
class PerturbationCurve:
    fractions: tuple[float, ...] = PRIMARY_FAITHFULNESS_FRACTIONS
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST
    comprehensiveness_values: dict[float, float] = field(default_factory=dict)
    sufficiency_raw_values: dict[float, float] = field(default_factory=dict)
    sufficiency_error_values: dict[float, float] = field(default_factory=dict)
    deletion_drops: dict[float, float] = field(default_factory=dict)
    insertion_gains: dict[float, float] = field(default_factory=dict)
    ks: dict[float, int] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def evaluate_removal_curve(
    ranked_region_ids: Sequence[str],
    *,
    score_full: float,
    score_without_fn: Callable[[Sequence[str]], float],
    score_only_fn: Callable[[Sequence[str]], float],
    fractions: Sequence[float] = PRIMARY_FAITHFULNESS_FRACTIONS,
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST,
) -> PerturbationCurve:
    n = len(ranked_region_ids)
    curve = PerturbationCurve(fractions=tuple(fractions), space=space)
    for frac in fractions:
        k = fraction_to_k(n, float(frac))
        curve.ks[float(frac)] = k
        selected = list(ranked_region_ids[:k])
        if not selected:
            continue
        s_wo = float(score_without_fn(selected))
        s_only = float(score_only_fn(selected))
        d = comprehensiveness(score_full, s_wo)
        curve.comprehensiveness_values[float(frac)] = d
        curve.deletion_drops[float(frac)] = d
        curve.sufficiency_raw_values[float(frac)] = sufficiency_raw(score_full, s_only)
        curve.sufficiency_error_values[float(frac)] = sufficiency_error(score_full, s_only)
    curve.metadata["n_regions"] = n
    curve.metadata["fraction_rounding"] = "max(1, ceil(f*N))"
    curve.metadata["perturbation_operator"] = "PAYLOAD_BLANK_V1"
    return curve


def evaluate_deletion_curve(
    ranked_region_ids: Sequence[str],
    *,
    score_full: float,
    score_blanked_fn: Callable[[Sequence[str]], float],
    fractions: Sequence[float] = PRIMARY_FAITHFULNESS_FRACTIONS,
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST,
) -> PerturbationCurve:
    """Deletion: blank top-k payloads; D(f) = s(x) - s(blanked_top_k)."""
    n = len(ranked_region_ids)
    curve = PerturbationCurve(fractions=tuple(fractions), space=space)
    for frac in fractions:
        k = fraction_to_k(n, float(frac))
        curve.ks[float(frac)] = k
        selected = list(ranked_region_ids[:k])
        s_f = float(score_blanked_fn(selected)) if selected else float(score_full)
        d = float(score_full) - s_f
        curve.deletion_drops[float(frac)] = d
        curve.comprehensiveness_values[float(frac)] = d
    curve.metadata["curve"] = "DELETION_CURVE_V1"
    curve.metadata["n_regions"] = n
    return curve


def evaluate_insertion_curve(
    ranked_region_ids: Sequence[str],
    *,
    score_empty: float,
    score_restored_fn: Callable[[Sequence[str]], float],
    fractions: Sequence[float] = PRIMARY_FAITHFULNESS_FRACTIONS,
    space: FaithfulnessScoreSpace = FaithfulnessScoreSpace.LOGIT_CONTRAST,
) -> PerturbationCurve:
    """Insertion: from all-blank, restore top-k; I(f) = s_restored - s_empty."""
    n = len(ranked_region_ids)
    curve = PerturbationCurve(fractions=tuple(fractions), space=space)
    for frac in fractions:
        k = fraction_to_k(n, float(frac))
        curve.ks[float(frac)] = k
        selected = list(ranked_region_ids[:k])
        s_f = float(score_restored_fn(selected)) if selected else float(score_empty)
        curve.insertion_gains[float(frac)] = s_f - float(score_empty)
    curve.metadata["curve"] = "INSERTION_CURVE_V1"
    curve.metadata["n_regions"] = n
    return curve


def aopc_deletion(deletion_drops: dict[float, float]) -> float:
    """AOPC_deletion = mean_f D(f) over evaluated fractions."""
    if not deletion_drops:
        return 0.0
    return float(sum(deletion_drops.values()) / len(deletion_drops))


def aopc_insertion(insertion_gains: dict[float, float]) -> float:
    """AOPC_insertion = mean_f I(f) over evaluated fractions."""
    if not insertion_gains:
        return 0.0
    return float(sum(insertion_gains.values()) / len(insertion_gains))


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

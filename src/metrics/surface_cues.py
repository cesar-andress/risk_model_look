"""RQ4 surface-cue / semantic-category attribution mass summaries.

High attribution mass is NOT proof of spuriousness.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from src.attribution.aggregate import SEMANTIC_CATEGORIES, aggregate_tokens_by_category
from src.attribution.aggregate import LineReduction


def category_mass_summary(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, float]]:
    """Signed sum, absolute mass, and normalized absolute mass per category."""
    signed = aggregate_tokens_by_category(
        token_scores, token_map, reduction=LineReduction.SUM
    )
    abs_mass = {c: 0.0 for c in SEMANTIC_CATEGORIES}
    for score, meta in zip(token_scores, token_map):
        cat = str(meta.get("segment_type"))
        if cat in abs_mass:
            abs_mass[cat] += abs(float(score))
    total_abs = sum(abs_mass.values())
    norm = {
        c: (abs_mass[c] / total_abs if total_abs > 0 else 0.0) for c in SEMANTIC_CATEGORIES
    }
    return {
        "signed_sum": signed,
        "absolute_mass": abs_mass,
        "normalized_absolute_mass": norm,
        "note": "High mass ≠ proof of spuriousness",
    }

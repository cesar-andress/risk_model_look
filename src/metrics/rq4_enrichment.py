"""RQ4 attribution enrichment and category ablation helpers (V1.2)."""

from __future__ import annotations

from typing import Mapping, Sequence

from src.attribution.aggregate import SEMANTIC_CATEGORIES


# Explicit prompt/template category (structured_diff SegmentType).
PROMPT_TEMPLATE_CATEGORY = "PROMPT_INSTRUCTION"

RQ4_CATEGORIES_V1_2: tuple[str, ...] = tuple(
    dict.fromkeys(
        list(SEMANTIC_CATEGORIES)
        + [PROMPT_TEMPLATE_CATEGORY, "SPECIAL_TOKEN"]
    )
)


def token_share(
    token_map: Sequence[Mapping[str, object]],
    category: str,
) -> float:
    n = len(token_map)
    if n == 0:
        return 0.0
    c = sum(1 for m in token_map if str(m.get("segment_type")) == category)
    return float(c) / float(n)


def abs_mass_share(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
    category: str,
) -> float:
    if len(token_scores) != len(token_map):
        raise ValueError("length mismatch")
    total = sum(abs(float(s)) for s in token_scores)
    if total <= 0:
        return 0.0
    mass = 0.0
    for s, m in zip(token_scores, token_map):
        if str(m.get("segment_type")) == category:
            mass += abs(float(s))
    return float(mass) / float(total)


def attribution_enrichment(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
    category: str,
) -> float | None:
    """ATTRIBUTION_ENRICHMENT_C = abs_mass_share / token_share if token_share > 0."""
    ts = token_share(token_map, category)
    if ts <= 0:
        return None
    return float(abs_mass_share(token_scores, token_map, category) / ts)


def enrichment_table(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
    categories: Sequence[str] | None = None,
) -> dict[str, dict[str, float | None]]:
    cats = list(categories) if categories is not None else list(RQ4_CATEGORIES_V1_2)
    out: dict[str, dict[str, float | None]] = {}
    for c in cats:
        ts = token_share(token_map, c)
        ms = abs_mass_share(token_scores, token_map, c)
        enr = (ms / ts) if ts > 0 else None
        out[c] = {
            "token_share": ts,
            "abs_mass_share": ms,
            "ATTRIBUTION_ENRICHMENT_C": enr,
        }
    return out


def category_ablation_delta(
    score_full: float,
    score_without_category: float,
) -> float:
    """Delta_category = s(x) - s(x_without_category_information)."""
    return float(score_full) - float(score_without_category)


def assert_prompt_template_accounted(categories_present: Sequence[str]) -> bool:
    """True if PROMPT_INSTRUCTION or SPECIAL_TOKEN appears in category inventory."""
    s = set(str(c) for c in categories_present)
    return PROMPT_TEMPLATE_CATEGORY in s or "SPECIAL_TOKEN" in s

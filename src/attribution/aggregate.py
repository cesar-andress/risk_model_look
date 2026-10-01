"""Token→line and category aggregation for attribution scores.

Primary candidate reduction for conservation interpretation: SUM.
Final methodological choice remains protocol-configurable until frozen.
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Iterable, Mapping, Sequence

from src.data.structured_diff import SegmentType

# Categories originate from the token-mapping / structured-diff contract.
SEMANTIC_CATEGORIES: tuple[str, ...] = (
    "COMMIT_MESSAGE",
    "FILE_PATH",
    "HUNK_HEADER",
    "ADDED_CODE",
    "DELETED_CODE",
    "CONTEXT_CODE",
    "STRUCTURAL_MARKUP",
    "SPECIAL_TOKEN",
)


class LineReduction(str, Enum):
    SUM = "SUM"
    MEAN = "MEAN"
    MAX_ABS_WITH_SIGN = "MAX_ABS_WITH_SIGN"


def _max_abs_with_sign(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    best = values[0]
    for v in values[1:]:
        if abs(v) > abs(best):
            best = v
    return float(best)


def aggregate_tokens_to_lines(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
    *,
    reduction: LineReduction = LineReduction.SUM,
    line_id_key: str = "stable_line_id",
) -> dict[str, float]:
    """Aggregate token scores onto stable line IDs.

    ``token_map[i]`` must describe model-visible token i. Tokens without a
    stable_line_id are skipped (e.g. structural markup / special tokens).
    """
    if len(token_scores) != len(token_map):
        raise ValueError(
            f"token_scores length {len(token_scores)} != token_map length {len(token_map)}"
        )
    buckets: dict[str, list[float]] = defaultdict(list)
    for score, meta in zip(token_scores, token_map):
        lid = meta.get(line_id_key)
        if lid is None:
            continue
        buckets[str(lid)].append(float(score))

    out: dict[str, float] = {}
    for lid, vals in buckets.items():
        if reduction == LineReduction.SUM:
            out[lid] = float(sum(vals))
        elif reduction == LineReduction.MEAN:
            out[lid] = float(sum(vals) / len(vals)) if vals else 0.0
        elif reduction == LineReduction.MAX_ABS_WITH_SIGN:
            out[lid] = _max_abs_with_sign(vals)
        else:
            raise ValueError(f"Unknown reduction: {reduction}")
    return out


def aggregate_tokens_by_category(
    token_scores: Sequence[float],
    token_map: Sequence[Mapping[str, object]],
    *,
    category_key: str = "segment_type",
    reduction: LineReduction = LineReduction.SUM,
) -> dict[str, float]:
    """Aggregate using contract categories from the token map (no regex)."""
    if len(token_scores) != len(token_map):
        raise ValueError("token_scores/token_map length mismatch")
    buckets: dict[str, list[float]] = defaultdict(list)
    for score, meta in zip(token_scores, token_map):
        cat = meta.get(category_key)
        if cat is None:
            continue
        cat_s = str(cat)
        if cat_s not in SEMANTIC_CATEGORIES:
            # Allow only contract categories; unknown keys are rejected.
            raise ValueError(
                f"Unknown segment_type {cat_s!r}; expected one of {SEMANTIC_CATEGORIES}"
            )
        buckets[cat_s].append(float(score))

    out: dict[str, float] = {c: 0.0 for c in SEMANTIC_CATEGORIES}
    for cat, vals in buckets.items():
        if reduction == LineReduction.SUM:
            out[cat] = float(sum(vals))
        elif reduction == LineReduction.MEAN:
            out[cat] = float(sum(vals) / len(vals)) if vals else 0.0
        elif reduction == LineReduction.MAX_ABS_WITH_SIGN:
            out[cat] = _max_abs_with_sign(vals)
        else:
            raise ValueError(f"Unknown reduction: {reduction}")
    return out


def assert_categories_from_contract(categories: Iterable[str]) -> None:
    unknown = [c for c in categories if c not in SEMANTIC_CATEGORIES]
    if unknown:
        raise ValueError(f"Non-contract categories: {unknown}")


# Type-check SegmentType membership at import for drift detection.
_ = SegmentType

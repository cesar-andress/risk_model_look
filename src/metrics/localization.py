"""RQ1 localization / plausibility metrics (Policy-A universe).

These are NOT faithfulness metrics. Ranking transforms are explicit parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from src.metrics.label_universe_guard import (
    GroundTruthStatus,
    UnknownGroundTruthError,
    assert_no_unknown_labels,
    effort_at_20pct_recall_requires_known_negatives,
    ifa_requires_known_negatives,
    recall_at_20pct_effort_requires_known_negatives,
)

# RQ1 statuses from frozen contract
RQ1_POSITIVE = "RQ1_POSITIVE"
RQ1_NEGATIVE = "RQ1_NEGATIVE"
NOT_IN_RQ1_UNIVERSE = "NOT_IN_RQ1_UNIVERSE"

# IFA indexing: matches existing label_universe_guard (0-based false-alarm count).
# If first ranked candidate is positive, IFA = 0.
# Flag retained for protocol visibility; convention follows project guard + JIT-Fine style.
IFA_INDEXING = "ZERO_BASED_FALSE_ALARM_COUNT"
IFA_INDEXING_DECISION_REQUIRED = False  # resolved via existing project guard


class RankingTransform(str, Enum):
    SIGNED_DESCENDING = "SIGNED_DESCENDING"
    ABS_DESCENDING = "ABS_DESCENDING"
    POSITIVE_PART_DESCENDING = "POSITIVE_PART_DESCENDING"


@dataclass(frozen=True)
class RankedCandidate:
    region_id: str
    raw_score: float
    rank_score: float
    label: GroundTruthStatus
    stable_order: int  # secondary key for deterministic ties


def ranking_score(raw: float, transform: RankingTransform) -> float:
    if transform == RankingTransform.SIGNED_DESCENDING:
        return float(raw)
    if transform == RankingTransform.ABS_DESCENDING:
        return abs(float(raw))
    if transform == RankingTransform.POSITIVE_PART_DESCENDING:
        return max(0.0, float(raw))
    raise ValueError(f"Unknown ranking transform: {transform}")


def filter_rq1_universe(
    region_ids: Sequence[str],
    scores: Sequence[float],
    rq1_statuses: Sequence[str],
    *,
    stable_orders: Sequence[int] | None = None,
) -> list[tuple[str, float, GroundTruthStatus, int]]:
    """Keep only RQ1_POSITIVE / RQ1_NEGATIVE; never include NOT_IN_RQ1_UNIVERSE."""
    if not (len(region_ids) == len(scores) == len(rq1_statuses)):
        raise ValueError("region_ids, scores, rq1_statuses length mismatch")
    if stable_orders is None:
        stable_orders = list(range(len(region_ids)))
    out: list[tuple[str, float, GroundTruthStatus, int]] = []
    for rid, sc, st, ord_i in zip(region_ids, scores, rq1_statuses, stable_orders):
        if st == NOT_IN_RQ1_UNIVERSE:
            continue
        if st == RQ1_POSITIVE:
            lab = GroundTruthStatus.POSITIVE
        elif st == RQ1_NEGATIVE:
            lab = GroundTruthStatus.NEGATIVE
        else:
            raise ValueError(f"Unexpected rq1_status {st!r}")
        out.append((rid, float(sc), lab, int(ord_i)))
    return out


def rank_candidates(
    items: Sequence[tuple[str, float, GroundTruthStatus, int]],
    *,
    transform: RankingTransform,
) -> list[RankedCandidate]:
    """Deterministic ranking: primary rank_score DESC, secondary stable_order ASC."""
    ranked = [
        RankedCandidate(
            region_id=rid,
            raw_score=raw,
            rank_score=ranking_score(raw, transform),
            label=lab,
            stable_order=ord_i,
        )
        for rid, raw, lab, ord_i in items
    ]
    ranked.sort(key=lambda c: (-c.rank_score, c.stable_order, c.region_id))
    return ranked


def top_k_hit(ranked: Sequence[RankedCandidate], k: int) -> float:
    """1.0 if any of top-k is POSITIVE else 0.0 (commit-level hit)."""
    assert_no_unknown_labels([c.label for c in ranked], metric_name=f"Top-{k}")
    top = ranked[:k]
    return 1.0 if any(c.label == GroundTruthStatus.POSITIVE for c in top) else 0.0


def compute_rq1_localization_metrics(
    region_ids: Sequence[str],
    scores: Sequence[float],
    rq1_statuses: Sequence[str],
    *,
    transform: RankingTransform,
    stable_orders: Sequence[int] | None = None,
) -> dict[str, float | int | str]:
    """Policy-A RQ1 metrics with label-universe guard.

    Raises UnknownGroundTruthError if UNKNOWN labels appear (should not for
    primary complete-case universe).
    """
    items = filter_rq1_universe(
        region_ids, scores, rq1_statuses, stable_orders=stable_orders
    )
    if not items:
        raise ValueError("empty RQ1 candidate universe after filtering")
    ranked = rank_candidates(items, transform=transform)
    labels = [c.label for c in ranked]
    # Guard: refuse UNKNOWN
    assert_no_unknown_labels(labels, metric_name="RQ1")
    n_pos = sum(1 for lab in labels if lab == GroundTruthStatus.POSITIVE)
    if n_pos == 0:
        raise ValueError(
            "no-positive invalid case for primary RQ1 localization metrics "
            "(complete-case positives expected)"
        )
    return {
        "n_candidates": len(ranked),
        "n_positives": n_pos,
        "ranking_transform": transform.value,
        "tie_break": "rank_score_DESC then stable_order_ASC then region_id_ASC",
        "ifa_indexing": IFA_INDEXING,
        "top1": top_k_hit(ranked, 1),
        "top5": top_k_hit(ranked, 5),
        "top10": top_k_hit(ranked, 10),
        "ifa": float(ifa_requires_known_negatives(labels)),
        "recall_at_20pct_effort": recall_at_20pct_effort_requires_known_negatives(labels),
        "effort_at_20pct_recall": effort_at_20pct_recall_requires_known_negatives(labels),
    }


__all__ = [
    "RankingTransform",
    "compute_rq1_localization_metrics",
    "filter_rq1_universe",
    "rank_candidates",
    "IFA_INDEXING",
    "IFA_INDEXING_DECISION_REQUIRED",
    "UnknownGroundTruthError",
    "RQ1_POSITIVE",
    "RQ1_NEGATIVE",
    "NOT_IN_RQ1_UNIVERSE",
]

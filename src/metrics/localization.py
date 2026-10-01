"""RQ1 localization / plausibility metrics (Policy-A universe).

PRIMARY ranking for signed methods: ABS_DESCENDING (where evidence is).
Polarity / buggy-supporting ranking is SECONDARY (SIGNED_POSITIVE_DESCENDING).
These are NOT faithfulness metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import numpy as np

from src.metrics.label_universe_guard import (
    GroundTruthStatus,
    UnknownGroundTruthError,
    assert_no_unknown_labels,
    effort_at_20pct_recall_requires_known_negatives,
    ifa_requires_known_negatives,
    recall_at_20pct_effort_requires_known_negatives,
)

RQ1_POSITIVE = "RQ1_POSITIVE"
RQ1_NEGATIVE = "RQ1_NEGATIVE"
NOT_IN_RQ1_UNIVERSE = "NOT_IN_RQ1_UNIVERSE"

IFA_INDEXING = "ZERO_BASED_FALSE_ALARM_COUNT"
IFA_INDEXING_DECISION_REQUIRED = False

# Frozen protocol populations
RQ1_COMPLETE_CASE_N = 413
RQ1_VISIBLE_N_2048 = 304
RQ1_VISIBLE_N_4096 = 345

PRIMARY_RQ1_RANK_TRANSFORM_SIGNED = "ABS_DESCENDING"
PRIMARY_RQ1_RANK_TRANSFORM_ATTENTION = "RAW_DESCENDING"
SENSITIVITY_RQ1_RANK_TRANSFORM_SIGNED = "SIGNED_POSITIVE_DESCENDING"

RANDOM_BASELINE_REPEATS = 100


class RankingTransform(str, Enum):
    ABS_DESCENDING = "ABS_DESCENDING"
    SIGNED_POSITIVE_DESCENDING = "SIGNED_POSITIVE_DESCENDING"
    RAW_DESCENDING = "RAW_DESCENDING"  # attention / nonnegative
    SIGNED_DESCENDING = "SIGNED_DESCENDING"  # alias semantics: same as SIGNED_POSITIVE
    POSITIVE_PART_DESCENDING = "POSITIVE_PART_DESCENDING"


@dataclass(frozen=True)
class RankedCandidate:
    region_id: str
    raw_score: float
    rank_score: float
    label: GroundTruthStatus
    ordered_position: int


def ranking_score(raw: float, transform: RankingTransform | str) -> float:
    t = RankingTransform(transform)
    if t == RankingTransform.ABS_DESCENDING:
        return abs(float(raw))
    if t in (
        RankingTransform.SIGNED_POSITIVE_DESCENDING,
        RankingTransform.SIGNED_DESCENDING,
        RankingTransform.RAW_DESCENDING,
    ):
        return float(raw)
    if t == RankingTransform.POSITIVE_PART_DESCENDING:
        return max(0.0, float(raw))
    raise ValueError(f"Unknown ranking transform: {transform}")

def filter_rq1_universe(
    region_ids: Sequence[str],
    scores: Sequence[float],
    rq1_statuses: Sequence[str],
    *,
    ordered_positions: Sequence[int] | None = None,
    stable_orders: Sequence[int] | None = None,  # alias
) -> list[tuple[str, float, GroundTruthStatus, int]]:
    if not (len(region_ids) == len(scores) == len(rq1_statuses)):
        raise ValueError("region_ids, scores, rq1_statuses length mismatch")
    if ordered_positions is None:
        ordered_positions = stable_orders if stable_orders is not None else list(range(len(region_ids)))
    out: list[tuple[str, float, GroundTruthStatus, int]] = []
    for rid, sc, st, ord_i in zip(region_ids, scores, rq1_statuses, ordered_positions):
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
    transform: RankingTransform | str,
) -> list[RankedCandidate]:
    """Tie-break: rank_score DESC, ordered_position ASC, region_id ASC."""
    ranked = [
        RankedCandidate(
            region_id=rid,
            raw_score=raw,
            rank_score=ranking_score(raw, transform),
            label=lab,
            ordered_position=ord_i,
        )
        for rid, raw, lab, ord_i in items
    ]
    ranked.sort(key=lambda c: (-c.rank_score, c.ordered_position, c.region_id))
    return ranked


def top_k_hit(ranked: Sequence[RankedCandidate], k: int) -> float:
    assert_no_unknown_labels([c.label for c in ranked], metric_name=f"Top-{k}")
    top = ranked[:k]
    return 1.0 if any(c.label == GroundTruthStatus.POSITIVE for c in top) else 0.0


def compute_rq1_localization_metrics(
    region_ids: Sequence[str],
    scores: Sequence[float],
    rq1_statuses: Sequence[str],
    *,
    transform: RankingTransform | str,
    ordered_positions: Sequence[int] | None = None,
    stable_orders: Sequence[int] | None = None,
) -> dict[str, float | int | str]:
    items = filter_rq1_universe(
        region_ids,
        scores,
        rq1_statuses,
        ordered_positions=ordered_positions,
        stable_orders=stable_orders,
    )
    if not items:
        raise ValueError("empty RQ1 candidate universe after filtering")
    ranked = rank_candidates(items, transform=transform)
    labels = [c.label for c in ranked]
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
        "ranking_transform": str(RankingTransform(transform).value),
        "tie_break": "rank_score_DESC then ordered_position_ASC then stable_line_id_ASC",
        "ifa_indexing": IFA_INDEXING,
        "top1": top_k_hit(ranked, 1),
        "top5": top_k_hit(ranked, 5),
        "top10": top_k_hit(ranked, 10),
        "ifa": float(ifa_requires_known_negatives(labels)),
        "recall_at_20pct_effort": recall_at_20pct_effort_requires_known_negatives(labels),
        "effort_at_20pct_recall": effort_at_20pct_recall_requires_known_negatives(labels),
    }


def random_baseline_seed(commit_id: str, repeat_index: int) -> int:
    """Deterministic seed independent of GPU training RNG / PYTHONHASHSEED."""
    import hashlib

    payload = f"RQ1_RANDOM_V1|{commit_id}|{int(repeat_index)}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def random_line_rankings(
    region_ids: Sequence[str],
    rq1_statuses: Sequence[str],
    *,
    commit_id: str,
    repeats: int = RANDOM_BASELINE_REPEATS,
    ordered_positions: Sequence[int] | None = None,
) -> list[list[str]]:
    """Return ``repeats`` deterministic permutations of RQ1 candidate IDs."""
    items = filter_rq1_universe(
        region_ids,
        [0.0] * len(region_ids),
        rq1_statuses,
        ordered_positions=ordered_positions,
    )
    ids = [rid for rid, _, _, _ in items]
    out: list[list[str]] = []
    for r in range(repeats):
        rng = np.random.default_rng(random_baseline_seed(commit_id, r))
        perm = list(ids)
        rng.shuffle(perm)
        out.append(perm)
    return out


__all__ = [
    "RankingTransform",
    "compute_rq1_localization_metrics",
    "filter_rq1_universe",
    "rank_candidates",
    "random_line_rankings",
    "random_baseline_seed",
    "IFA_INDEXING",
    "IFA_INDEXING_DECISION_REQUIRED",
    "UnknownGroundTruthError",
    "RQ1_POSITIVE",
    "RQ1_NEGATIVE",
    "NOT_IN_RQ1_UNIVERSE",
    "PRIMARY_RQ1_RANK_TRANSFORM_SIGNED",
    "RANDOM_BASELINE_REPEATS",
]

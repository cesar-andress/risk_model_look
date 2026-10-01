"""RQ1 localization metric tests (CPU)."""

from __future__ import annotations

import pytest

from src.metrics.label_universe_guard import UnknownGroundTruthError
from src.metrics.localization import (
    IFA_INDEXING,
    IFA_INDEXING_DECISION_REQUIRED,
    NOT_IN_RQ1_UNIVERSE,
    RQ1_NEGATIVE,
    RQ1_POSITIVE,
    RankingTransform,
    compute_rq1_localization_metrics,
    filter_rq1_universe,
    rank_candidates,
)


pytestmark = pytest.mark.cpu


def test_ifa_indexing_documented() -> None:
    assert IFA_INDEXING == "ZERO_BASED_FALSE_ALARM_COUNT"
    assert IFA_INDEXING_DECISION_REQUIRED is False


def test_excludes_not_in_universe() -> None:
    items = filter_rq1_universe(
        ["a", "b", "c"],
        [0.9, 0.1, 0.8],
        [RQ1_POSITIVE, NOT_IN_RQ1_UNIVERSE, RQ1_NEGATIVE],
    )
    assert [x[0] for x in items] == ["a", "c"]


def test_tie_break_stable_order() -> None:
    from src.metrics.label_universe_guard import GroundTruthStatus

    items = [
        ("L2", 1.0, GroundTruthStatus.NEGATIVE, 2),
        ("L1", 1.0, GroundTruthStatus.POSITIVE, 1),
    ]
    ranked = rank_candidates(items, transform=RankingTransform.SIGNED_DESCENDING)
    assert [c.region_id for c in ranked] == ["L1", "L2"]


def test_single_buggy_line_metrics() -> None:
    m = compute_rq1_localization_metrics(
        ["p", "n1", "n2", "n3", "n4"],
        [0.9, 0.8, 0.7, 0.6, 0.5],
        [RQ1_POSITIVE, RQ1_NEGATIVE, RQ1_NEGATIVE, RQ1_NEGATIVE, RQ1_NEGATIVE],
        transform=RankingTransform.SIGNED_DESCENDING,
    )
    assert m["top1"] == 1.0
    assert m["ifa"] == 0.0


def test_multiple_buggy_and_ties() -> None:
    ids = [f"L{i}" for i in range(10)]
    scores = [1.0] * 10  # all ties → stable_order decides
    statuses = [RQ1_NEGATIVE] * 10
    statuses[3] = RQ1_POSITIVE
    statuses[7] = RQ1_POSITIVE
    m = compute_rq1_localization_metrics(
        ids,
        scores,
        statuses,
        transform=RankingTransform.ABS_DESCENDING,
        stable_orders=list(range(10)),
    )
    assert m["ifa"] == 3.0
    assert m["n_positives"] == 2


def test_small_commit_and_rounding_boundary() -> None:
    # n=5 → 20% effort k = max(1, int(1.0)) = 1
    m = compute_rq1_localization_metrics(
        ["a", "b", "c", "d", "e"],
        [0.1, 0.9, 0.2, 0.3, 0.4],
        [RQ1_NEGATIVE, RQ1_POSITIVE, RQ1_NEGATIVE, RQ1_NEGATIVE, RQ1_NEGATIVE],
        transform=RankingTransform.SIGNED_DESCENDING,
    )
    assert m["recall_at_20pct_effort"] == 1.0  # top-1 is positive
    # n_pos=1 → need max(1, int(0.2))=1; effort = 1/5
    assert m["effort_at_20pct_recall"] == pytest.approx(0.2)


def test_all_positive_universe() -> None:
    m = compute_rq1_localization_metrics(
        ["a", "b", "c"],
        [0.3, 0.2, 0.1],
        [RQ1_POSITIVE, RQ1_POSITIVE, RQ1_POSITIVE],
        transform=RankingTransform.SIGNED_DESCENDING,
    )
    assert m["ifa"] == 0.0
    assert m["top1"] == 1.0


def test_no_positive_invalid() -> None:
    with pytest.raises(ValueError, match="no-positive"):
        compute_rq1_localization_metrics(
            ["a", "b"],
            [0.9, 0.1],
            [RQ1_NEGATIVE, RQ1_NEGATIVE],
            transform=RankingTransform.SIGNED_DESCENDING,
        )


def test_ranking_transform_positive_part() -> None:
    m = compute_rq1_localization_metrics(
        ["neg_strong", "pos_weak"],
        [-5.0, 0.1],
        [RQ1_NEGATIVE, RQ1_POSITIVE],
        transform=RankingTransform.POSITIVE_PART_DESCENDING,
    )
    # positive part of -5 is 0; of 0.1 is 0.1 → pos ranks first
    assert m["top1"] == 1.0
    assert m["ifa"] == 0.0


def test_unknown_still_guarded_via_effort_path() -> None:
    # Direct guard still active
    from src.metrics.label_universe_guard import (
        GroundTruthStatus,
        ifa_requires_known_negatives,
    )

    with pytest.raises(UnknownGroundTruthError):
        ifa_requires_known_negatives(
            [GroundTruthStatus.NEGATIVE, GroundTruthStatus.UNKNOWN]
        )

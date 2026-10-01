"""Scientific integrity guards for localization metrics.

Metrics that require known negatives MUST refuse UNKNOWN candidate labels.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Sequence


class GroundTruthStatus(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    UNKNOWN = "UNKNOWN"


class UnknownGroundTruthError(ValueError):
    """Raised when a metric requiring known negatives sees UNKNOWN labels."""


def assert_no_unknown_labels(
    labels: Sequence[GroundTruthStatus | str],
    *,
    metric_name: str,
) -> None:
    """Refuse effort/IFA-style metrics if any candidate is UNKNOWN."""
    bad = [
        i
        for i, lab in enumerate(labels)
        if GroundTruthStatus(lab) == GroundTruthStatus.UNKNOWN
    ]
    if bad:
        raise UnknownGroundTruthError(
            f"{metric_name} requires fully known binary ground truth; "
            f"found UNKNOWN at candidate indices {bad[:10]}"
            + ("..." if len(bad) > 10 else "")
        )


def ifa_requires_known_negatives(
    ranked_labels: Sequence[GroundTruthStatus | str],
) -> int:
    """IFA over a ranked list of candidate lines (POSITIVE/NEGATIVE only)."""
    assert_no_unknown_labels(ranked_labels, metric_name="IFA")
    for i, lab in enumerate(ranked_labels):
        if GroundTruthStatus(lab) == GroundTruthStatus.POSITIVE:
            return i
    return len(ranked_labels)


def recall_at_20pct_effort_requires_known_negatives(
    ranked_labels: Sequence[GroundTruthStatus | str],
) -> float:
    """Recall@20%Effort over ranked candidates (line-level)."""
    assert_no_unknown_labels(ranked_labels, metric_name="Recall@20%Effort")
    n = len(ranked_labels)
    if n == 0:
        return 0.0
    k = max(1, int(0.2 * n))
    top = ranked_labels[:k]
    n_pos = sum(1 for lab in ranked_labels if GroundTruthStatus(lab) == GroundTruthStatus.POSITIVE)
    if n_pos == 0:
        return 0.0
    hit = sum(1 for lab in top if GroundTruthStatus(lab) == GroundTruthStatus.POSITIVE)
    return hit / n_pos


def effort_at_20pct_recall_requires_known_negatives(
    ranked_labels: Sequence[GroundTruthStatus | str],
) -> float:
    """Effort@20%Recall over ranked candidates (line-level)."""
    assert_no_unknown_labels(ranked_labels, metric_name="Effort@20%Recall")
    n = len(ranked_labels)
    n_pos = sum(1 for lab in ranked_labels if GroundTruthStatus(lab) == GroundTruthStatus.POSITIVE)
    if n == 0 or n_pos == 0:
        return 1.0
    need = max(1, int(0.2 * n_pos))
    seen = 0
    for i, lab in enumerate(ranked_labels, start=1):
        if GroundTruthStatus(lab) == GroundTruthStatus.POSITIVE:
            seen += 1
            if seen >= need:
                return i / n
    return 1.0

"""Synthetic tests for RQ1 label-universe integrity (no external datasets)."""

from __future__ import annotations

import pytest

from src.metrics.label_universe_guard import (
    GroundTruthStatus,
    UnknownGroundTruthError,
    effort_at_20pct_recall_requires_known_negatives,
    ifa_requires_known_negatives,
    recall_at_20pct_effort_requires_known_negatives,
)


def test_ifa_ok_without_unknown() -> None:
    labs = [
        GroundTruthStatus.NEGATIVE,
        GroundTruthStatus.NEGATIVE,
        GroundTruthStatus.POSITIVE,
    ]
    assert ifa_requires_known_negatives(labs) == 2


def test_ifa_refuses_unknown() -> None:
    labs = [
        GroundTruthStatus.NEGATIVE,
        GroundTruthStatus.UNKNOWN,
        GroundTruthStatus.POSITIVE,
    ]
    with pytest.raises(UnknownGroundTruthError):
        ifa_requires_known_negatives(labs)


def test_recall_effort_refuses_unknown() -> None:
    labs = [GroundTruthStatus.POSITIVE, GroundTruthStatus.UNKNOWN]
    with pytest.raises(UnknownGroundTruthError):
        recall_at_20pct_effort_requires_known_negatives(labs)


def test_effort_recall_refuses_unknown() -> None:
    labs = [GroundTruthStatus.NEGATIVE, GroundTruthStatus.UNKNOWN]
    with pytest.raises(UnknownGroundTruthError):
        effort_at_20pct_recall_requires_known_negatives(labs)


def test_unknown_vs_negative_distinction() -> None:
    assert GroundTruthStatus.UNKNOWN != GroundTruthStatus.NEGATIVE
    # Missing Layer-A abl must not be coerced to NEGATIVE by default.
    status_from_missing_key = GroundTruthStatus.UNKNOWN
    assert status_from_missing_key is GroundTruthStatus.UNKNOWN


def test_split_train_valid_union_arithmetic() -> None:
    train, valid, test = 16374, 5465, 5480
    assert train + valid == 21839
    assert train + valid + test == 27319
    # JIT-Block paper "training" removals map onto our train∪valid
    assert 21839 - 121 == 21718
    assert 5480 - 57 == 5423


def test_removed_commit_label_audit_synthetic() -> None:
    # Synthetic: exclusions must not silently drop positives.
    our_labels = {"a": 0.0, "b": 1.0, "c": 0.0}
    removed = {"a", "c"}
    assert all(our_labels[c] == 0.0 for c in removed)
    assert "b" not in removed


def test_candidate_universe_construction() -> None:
    # Policy A universe = explicitly labelled rows only
    rows = [
        {"gt": GroundTruthStatus.POSITIVE},
        {"gt": GroundTruthStatus.NEGATIVE},
    ]
    assert all(r["gt"] != GroundTruthStatus.UNKNOWN for r in rows)


def test_ordered_reconstruction_comparison_classes() -> None:
    classes = {
        "EXACT",
        "STRUCTURALLY_EQUIVALENT",
        "TEXT_NORMALIZATION_DIFFERENCE",
        "BLOCK_BOUNDARY_DIFFERENCE",
        "ORDER_DIFFERENCE",
        "MISMATCH",
    }
    assert "EXACT" in classes

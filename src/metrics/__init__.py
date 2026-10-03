"""Metrics package: localization (plausibility) vs faithfulness kept separate."""

from src.metrics.label_universe_guard import (
    GroundTruthStatus,
    UnknownGroundTruthError,
    assert_no_unknown_labels,
)

__all__ = [
    "GroundTruthStatus",
    "UnknownGroundTruthError",
    "assert_no_unknown_labels",
]

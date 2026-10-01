"""File-path category scaffold for RQ4 (heuristic NOT frozen).

Default category is UNKNOWN. Do not silently classify by '/test/' alone.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class FileCategory(str, Enum):
    UNKNOWN = "UNKNOWN"
    # Reserved for a future audited classifier — not assigned by default:
    PRODUCTION = "PRODUCTION"
    TEST = "TEST"
    OTHER = "OTHER"


class FileCategoryClassifier(Protocol):
    def categorize(self, path: str) -> FileCategory: ...


class DefaultUnknownClassifier:
    """Scaffold classifier: always UNKNOWN until an audited rule is adopted."""

    def categorize(self, path: str) -> FileCategory:
        _ = path
        return FileCategory.UNKNOWN


def get_default_classifier() -> FileCategoryClassifier:
    return DefaultUnknownClassifier()

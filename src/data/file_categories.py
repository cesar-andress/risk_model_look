"""File-path category scaffold for RQ4.

Protocol V1.1: test-file category status = PENDING_AUDIT.
Default classifier returns UNKNOWN. Do not silently classify by '/test/' alone.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol

TEST_FILE_CATEGORY_STATUS = "PENDING_AUDIT"


class FileCategory(str, Enum):
    UNKNOWN = "UNKNOWN"
    PRODUCTION = "PRODUCTION"
    TEST = "TEST"
    OTHER = "OTHER"


class FileCategoryClassifier(Protocol):
    def categorize(self, path: str) -> FileCategory: ...


class DefaultUnknownClassifier:
    """Scaffold classifier: always UNKNOWN until an audited rule is adopted."""

    status = TEST_FILE_CATEGORY_STATUS

    def categorize(self, path: str) -> FileCategory:
        _ = path
        return FileCategory.UNKNOWN


def get_default_classifier() -> FileCategoryClassifier:
    return DefaultUnknownClassifier()


def test_file_category_audit_status() -> str:
    return TEST_FILE_CATEGORY_STATUS

"""Common attribution result abstraction.

Signedness is never inferred from method names; callers must set ``signed``
explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ScoreSpace(str, Enum):
    """Where token/line scores live."""

    TOKEN = "TOKEN"
    LINE = "LINE"
    HUNK = "HUNK"
    CATEGORY = "CATEGORY"
    REGION = "REGION"


@dataclass(frozen=True)
class TargetDefinition:
    """Scalar explanation target for attribution methods."""

    name: str
    formula: str
    signed: bool
    notes: str = ""


@dataclass(frozen=True)
class AttributionResult:
    """Standardized attribution object.

    ``token_scores``: one scalar per model-visible input token (length N).
    Absolute-value transforms for ranking belong in evaluation, not here.
    """

    method_name: str
    score_space: ScoreSpace
    signed: bool
    target_definition: TargetDefinition
    token_scores: Sequence[float]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.signed, bool):
            raise TypeError("signed must be an explicit bool; never infer from method_name")
        object.__setattr__(self, "token_scores", tuple(float(x) for x in self.token_scores))
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")

    @property
    def n_tokens(self) -> int:
        return len(self.token_scores)

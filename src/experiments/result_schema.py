"""Stable row-level result schema for attribution experiment outputs.

Raw result rows must live under Git-ignored ``data/results/attribution/``.
Commit only schema definitions and aggregates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

SCHEMA_VERSION = "attribution_result_row_v1"

REQUIRED_FIELDS = (
    "experiment_id",
    "model_id",
    "model_seed",
    "commit_id",
    "method",
    "granularity",
    "region_id",
    "raw_score",
    "signed_score",
    "rank_score",
    "rq1_status",
)


@dataclass
class AttributionResultRow:
    experiment_id: str
    model_id: str
    model_seed: int
    commit_id: str
    method: str
    granularity: str  # TOKEN | LINE | HUNK | CATEGORY | ...
    region_id: str
    raw_score: float | None  # None => TBD/NA, never invent 0 for missing
    signed_score: float | None
    rank_score: float | None
    rq1_status: str  # RQ1_POSITIVE | RQ1_NEGATIVE | NOT_IN_RQ1_UNIVERSE | NA
    schema_version: str = SCHEMA_VERSION
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in row:
            errors.append(f"missing:{f}")
    # Missing scientific values must be None/"NA"/"TBD", never silently 0
    for score_key in ("raw_score", "signed_score", "rank_score"):
        if score_key in row and row[score_key] == 0:
            # 0 is a valid measured score; placeholder must use None
            pass
        if score_key in row and row[score_key] is False:
            errors.append(f"invalid_placeholder:{score_key}")
    return errors


def schema_spec() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "fields": [f.name for f in fields(AttributionResultRow)],
        "required": list(REQUIRED_FIELDS),
        "storage": "data/results/attribution/ (gitignored raw rows)",
        "missing_value_policy": "use null/NA/TBD; never fabricate 0 for unknown results",
    }

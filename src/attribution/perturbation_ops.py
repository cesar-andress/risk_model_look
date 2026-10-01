"""Perturbation operators: SEGMENT_DELETE_V1 vs PAYLOAD_BLANK_V1.

Occlusion attribution uses SEGMENT_DELETE_V1.
Primary RQ2 faithfulness uses PAYLOAD_BLANK_V1 (distinct operator).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from src.attribution.occlusion import (
    OcclusionUnit,
    RegionSpec,
    ToyStructuredCommit,
)


class PerturbationOperator(str, Enum):
    SEGMENT_DELETE_V1 = "SEGMENT_DELETE_V1"
    PAYLOAD_BLANK_V1 = "PAYLOAD_BLANK_V1"


BLANK_PAYLOAD_TOKEN = ""  # empty payload string; marker/structure retained in renderers


@dataclass(frozen=True)
class OperatorSpec:
    name: PerturbationOperator
    retains_structure: bool
    removes_segment: bool
    notes: str


OPERATOR_SPECS: Mapping[PerturbationOperator, OperatorSpec] = {
    PerturbationOperator.SEGMENT_DELETE_V1: OperatorSpec(
        name=PerturbationOperator.SEGMENT_DELETE_V1,
        retains_structure=False,
        removes_segment=True,
        notes="Remove complete semantic segment (marker+payload); cleanup empty hunk/file.",
    ),
    PerturbationOperator.PAYLOAD_BLANK_V1: OperatorSpec(
        name=PerturbationOperator.PAYLOAD_BLANK_V1,
        retains_structure=True,
        removes_segment=False,
        notes="Blank payloads only; keep structural markers / file/hunk scaffolding.",
    ),
}


def apply_segment_delete(
    commit: ToyStructuredCommit,
    region: RegionSpec,
) -> ToyStructuredCommit:
    """SEGMENT_DELETE_V1 on toy structured commits (same semantics as occlusion remove)."""
    from src.attribution.occlusion import remove_region_structured

    return remove_region_structured(commit, region)


def apply_payload_blank(
    commit: ToyStructuredCommit,
    region_ids: Sequence[str],
    *,
    id_key: str = "stable_line_id",
) -> ToyStructuredCommit:
    """PAYLOAD_BLANK_V1: blank payloads for listed line IDs; keep structure."""
    out = commit.clone()
    drop = set(region_ids)
    for path, lines in out.files.items():
        for ln in lines:
            if ln.get(id_key) in drop:
                ln["text"] = BLANK_PAYLOAD_TOKEN
                ln["payload_blanked"] = True
    # Do NOT remove empty hunks/files — structure retained
    return out


def apply_payload_blank_all(commit: ToyStructuredCommit) -> ToyStructuredCommit:
    ids = [
        str(ln["stable_line_id"])
        for lines in commit.files.values()
        for ln in lines
        if ln.get("stable_line_id") is not None
    ]
    return apply_payload_blank(commit, ids)


def restore_payloads_from_original(
    blanked: ToyStructuredCommit,
    original: ToyStructuredCommit,
    region_ids: Sequence[str],
    *,
    id_key: str = "stable_line_id",
) -> ToyStructuredCommit:
    """Insertion step: restore selected region payloads from the original commit."""
    out = blanked.clone()
    want = set(region_ids)
    orig_by_id: dict[str, dict[str, Any]] = {}
    for lines in original.files.values():
        for ln in lines:
            sid = ln.get(id_key)
            if sid is not None:
                orig_by_id[str(sid)] = ln
    for path, lines in out.files.items():
        for ln in lines:
            sid = ln.get(id_key)
            if sid is not None and str(sid) in want and str(sid) in orig_by_id:
                src = orig_by_id[str(sid)]
                ln["text"] = src.get("text", "")
                ln.pop("payload_blanked", None)
    return out


def diff_polarity_swap_v1(commit: ToyStructuredCommit) -> ToyStructuredCommit:
    """DIFF_POLARITY_SWAP_V1: swap added↔deleted roles on toy commits."""
    out = commit.clone()
    for path, lines in out.files.items():
        for ln in lines:
            ct = ln.get("change_type")
            if ct == "added":
                ln["change_type"] = "deleted"
                if ln.get("category") == "ADDED_CODE":
                    ln["category"] = "DELETED_CODE"
            elif ct == "deleted":
                ln["change_type"] = "added"
                if ln.get("category") == "DELETED_CODE":
                    ln["category"] = "ADDED_CODE"
    return out

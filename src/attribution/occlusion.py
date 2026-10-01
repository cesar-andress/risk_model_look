"""Signed occlusion / perturbation primitives.

Frozen sign convention
----------------------
For region R and score s(x) = logit_1(x) - logit_0(x):

    delta_R = s(x) - s(x_without_R)

Interpretation (FROZEN — do not invert later):
  delta > 0  → region supports buggy prediction (removing it lowers risk)
  delta < 0  → region suppresses buggy / supports clean prediction

Perturbation policy: operate on the structured input representation, then
re-render/re-tokenize. Do NOT replace arbitrary token IDs with zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence


class OcclusionUnit(str, Enum):
    TOKEN = "TOKEN"
    LINE = "LINE"
    HUNK = "HUNK"
    MESSAGE = "MESSAGE"
    FILE_PATH = "FILE_PATH"
    FILE = "FILE"


SIGN_CONVENTION = {
    "delta_definition": "delta_R = s(x) - s(x_without_R)",
    "s_definition": "s = logit_1 - logit_0",
    "delta_positive": "region supports buggy prediction",
    "delta_negative": "region suppresses buggy prediction / supports clean",
    "frozen": True,
}


@dataclass(frozen=True)
class RegionSpec:
    """API-level region definition for occlusion."""

    unit: OcclusionUnit
    region_id: str
    # Structured pointers (not raw token-zeroing)
    stable_line_ids: tuple[str, ...] = ()
    hunk_ids: tuple[str, ...] = ()
    file_ids: tuple[str, ...] = ()
    token_indices: tuple[int, ...] = ()
    include_message: bool = False
    include_file_paths: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OcclusionResult:
    region: RegionSpec
    s_full: float
    s_without: float
    delta: float
    signed: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def supports_buggy(self) -> bool:
        return self.delta > 0

    @property
    def suppresses_buggy(self) -> bool:
        return self.delta < 0


ScoreCallable = Callable[[Any], float]
"""Maps a structured/rendered input representation to s = logit_1 - logit_0."""

RemoveCallable = Callable[[Any, RegionSpec], Any]
"""Returns a new structured input with the region removed cleanly."""


def signed_occlusion_delta(s_full: float, s_without: float) -> float:
    """Pure metric: delta_R = s(x) - s(x_without_R)."""
    return float(s_full) - float(s_without)


def occlude_region(
    structured_input: Any,
    region: RegionSpec,
    *,
    score_fn: ScoreCallable,
    remove_fn: RemoveCallable,
) -> OcclusionResult:
    """Apply structured removal then score; never zero-out token IDs here."""
    s_full = float(score_fn(structured_input))
    without = remove_fn(structured_input, region)
    s_without = float(score_fn(without))
    delta = signed_occlusion_delta(s_full, s_without)
    return OcclusionResult(
        region=region,
        s_full=s_full,
        s_without=s_without,
        delta=delta,
        signed=True,
        metadata={"sign_convention": SIGN_CONVENTION, "perturbation": "structured_remove"},
    )


# ---------------------------------------------------------------------------
# Deterministic structured removal helpers for synthetic / unit tests
# ---------------------------------------------------------------------------


@dataclass
class ToyStructuredCommit:
    """Minimal structured commit for occlusion unit tests (not production render)."""

    message: str
    files: dict[str, list[dict[str, Any]]]
    # files[path] = list of line dicts:
    #   {stable_line_id, hunk_id, change_type, text, category, effect?}

    def clone(self) -> "ToyStructuredCommit":
        files = {p: [dict(line) for line in lines] for p, lines in self.files.items()}
        return ToyStructuredCommit(message=self.message, files=files)


def remove_region_structured(
    commit: ToyStructuredCommit,
    region: RegionSpec,
) -> ToyStructuredCommit:
    """Clean structured removal by unit type; then caller re-scores."""
    out = commit.clone()
    if region.unit == OcclusionUnit.MESSAGE or region.include_message:
        out.message = ""
    if region.unit == OcclusionUnit.FILE_PATH or region.include_file_paths:
        # Drop path strings but keep contents under a placeholder file id if needed.
        # For FILE_PATH unit with explicit file_ids: rename path payload to empty marker.
        renamed: dict[str, list[dict[str, Any]]] = {}
        for path, lines in out.files.items():
            if not region.file_ids or path in region.file_ids:
                renamed[""] = renamed.get("", []) + lines
            else:
                renamed[path] = lines
        if region.unit == OcclusionUnit.FILE_PATH:
            out.files = renamed
    if region.unit == OcclusionUnit.FILE:
        for fid in region.file_ids:
            out.files.pop(fid, None)
    if region.unit == OcclusionUnit.HUNK:
        for path in list(out.files):
            out.files[path] = [
                ln for ln in out.files[path] if ln.get("hunk_id") not in region.hunk_ids
            ]
    if region.unit == OcclusionUnit.LINE:
        drop = set(region.stable_line_ids)
        for path in list(out.files):
            out.files[path] = [
                ln for ln in out.files[path] if ln.get("stable_line_id") not in drop
            ]
    if region.unit == OcclusionUnit.TOKEN:
        # Token-level structured occlusion is expressed by tagging token indices
        # on lines; for toy commits we remove whole lines carrying those tokens.
        # Production path must re-tokenize after structured edits, not zero IDs.
        raise NotImplementedError(
            "TOKEN unit requires token_map-aware structured edit + re-tokenize; "
            "use LINE/HUNK/MESSAGE/FILE units or a custom remove_fn"
        )
    # Drop empty files
    out.files = {p: lines for p, lines in out.files.items() if lines}
    return out


def default_toy_scorer(effects: Mapping[str, float]) -> ScoreCallable:
    """Score = sum of per-line effects still present (+ optional message effect)."""

    def score_fn(commit: ToyStructuredCommit) -> float:
        total = float(effects.get("__message__", 0.0)) if commit.message else 0.0
        for lines in commit.files.values():
            for ln in lines:
                sid = ln.get("stable_line_id")
                total += float(effects.get(sid, 0.0))
        return total

    return score_fn


def make_line_region(stable_line_id: str) -> RegionSpec:
    return RegionSpec(
        unit=OcclusionUnit.LINE,
        region_id=stable_line_id,
        stable_line_ids=(stable_line_id,),
    )


def make_hunk_region(hunk_id: str, line_ids: Sequence[str] = ()) -> RegionSpec:
    return RegionSpec(
        unit=OcclusionUnit.HUNK,
        region_id=hunk_id,
        hunk_ids=(hunk_id,),
        stable_line_ids=tuple(line_ids),
    )

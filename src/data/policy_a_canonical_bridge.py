"""Policy-A → canonical Git line-ID bridge (audit only; no tokenization).

JIT-Block producer code is ABSENT from hangters/JIT-Block@d82cc67.
This module implements the paper-described matching intent using our
canonical first-parent Git diffs, preserving Layer-B (commit_id, idx) as
immutable source-row IDs. Matching uses only verified deterministic
transforms — no fuzzy / first-hit heuristics.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from src.data.git_diff_reconstruction import (
    DiffLine,
    git_diff_against_parent,
    normalize_line,
    parse_unified_diff,
    stable_line_id,
)


def punct_space(text: str) -> str:
    """Insert spaces around non-word chars; collapse whitespace."""
    s = re.sub(r"([^\w\s])", r" \1 ", text, flags=re.UNICODE)
    return " ".join(s.split())


def text_variants(text: str) -> set[str]:
    """Deterministic variants for exact matching (no fuzzy)."""
    return {
        text,
        punct_space(text),
        punct_space(text.replace("_", " ")),
        " ".join(text.split()),
        normalize_line(text),
        punct_space(normalize_line(text)),
        normalize_line(punct_space(text)),
    }


@dataclass(frozen=True)
class PolicyARow:
    commit_id: str
    idx: int
    changed_type: str
    label: float
    raw_changed_line: str
    changed_line: str


@dataclass
class BridgeResult:
    commit_id: str
    idx: int
    label: float
    mapping_status: str
    path_status: str | None
    canonical_line_id: str | None
    file_path: str | None
    hunk_index: int | None
    new_lineno: int | None
    old_lineno: int | None
    occurrence_index: int | None
    text_status: str | None
    provenance_method: str


def load_canonical_added_java(
    git_dir: Any,
    commit: str,
    parent: str | None,
) -> list[DiffLine]:
    diff = git_diff_against_parent(git_dir, commit, parent)
    lines = parse_unified_diff(diff)
    return [ln for ln in lines if ln.change_type == "added" and ln.file_path.endswith(".java")]


def map_policy_a_rows_to_git(
    rows: list[PolicyARow],
    git_lines: list[DiffLine],
) -> list[BridgeResult]:
    """Map Policy-A ADDED rows to canonical Git added lines.

    Primary key after match: file + linenos + occurrence (via DiffLine).
    Matching edges: exact equality after verified variants.
    Duplicate handling: equal-multiplicity order zip, then unique neighbor
    sequence windows — never arbitrary first-hit.
    """
    if not rows:
        return []

    var_to_gis: dict[str, list[int]] = defaultdict(list)
    g_vars: list[set[str]] = []
    for gi, gl in enumerate(git_lines):
        vs = text_variants(gl.raw_text)
        g_vars.append(vs)
        for v in vs:
            var_to_gis[v].append(gi)

    n = len(rows)
    a_vars = [text_variants(r.raw_changed_line) for r in rows]
    used_g: set[int] = set()
    assignment: dict[int, tuple[int, str, str]] = {}  # ai -> (gi, status, provenance)

    def cands_for(ai: int) -> list[int]:
        return sorted(
            {
                gi
                for v in a_vars[ai]
                for gi in var_to_gis.get(v, [])
                if gi not in used_g and (a_vars[ai] & g_vars[gi])
            }
        )

    # Pass 1: unique exact candidate
    for ai in range(n):
        cands = cands_for(ai)
        if len(cands) == 1:
            gi = cands[0]
            used_g.add(gi)
            assignment[ai] = (gi, "RECOVERED_EXACT_BY_JITBLOCK", "unique_exact_variant")
        elif len(cands) == 0:
            assignment[ai] = (-1, "NOT_FOUND", "no_exact_variant")

    # Pass 2: multiplicity zip (group by shared variants).
    # Allow |PolicyA| <= |Git| using Git diff order as occurrence authority
    # when extras are unlabelled Git lines outside U_JITFINE.
    remaining = [ai for ai in range(n) if ai not in assignment]
    processed_groups: set[frozenset[int]] = set()
    for ai in remaining:
        group = frozenset(
            aj
            for aj in remaining
            if aj not in assignment and (a_vars[ai] & a_vars[aj])
        )
        if not group or group in processed_groups:
            continue
        processed_groups.add(group)
        g_idxs = sorted(
            {
                gi
                for aj in group
                for v in a_vars[aj]
                for gi in var_to_gis.get(v, [])
                if gi not in used_g and (a_vars[aj] & g_vars[gi])
            }
        )
        a_idxs = sorted(group)
        if len(a_idxs) > 0 and len(a_idxs) <= len(g_idxs):
            status = (
                "RECOVERED_EXACT_DUPLICATE_DISAMBIGUATED"
                if len(a_idxs) == len(g_idxs)
                else "RECOVERED_EXACT_SEQUENCE_DISAMBIGUATED"
            )
            prov = (
                "equal_multiplicity_order_zip"
                if len(a_idxs) == len(g_idxs)
                else "git_order_prefix_zip"
            )
            for aj, gi in zip(a_idxs, g_idxs[: len(a_idxs)]):
                used_g.add(gi)
                assignment[aj] = (gi, status, prov)

    # Pass 3: sequence disambiguation with neighbor anchors
    for i in range(n):
        if i in assignment:
            continue
        prev_g = None
        next_g = None
        for j in range(i - 1, -1, -1):
            if j in assignment and assignment[j][0] >= 0:
                prev_g = assignment[j][0]
                break
        for j in range(i + 1, n):
            if j in assignment and assignment[j][0] >= 0:
                next_g = assignment[j][0]
                break
        lo = (prev_g + 1) if prev_g is not None else 0
        hi = next_g if next_g is not None else len(git_lines)
        cands = [
            gi
            for gi in range(lo, hi)
            if gi not in used_g and (a_vars[i] & g_vars[gi])
        ]
        if len(cands) == 1:
            gi = cands[0]
            used_g.add(gi)
            assignment[i] = (
                gi,
                "RECOVERED_EXACT_SEQUENCE_DISAMBIGUATED",
                "unique_neighbor_window",
            )

    def make_result(ai: int) -> BridgeResult:
        r = rows[ai]
        gi, status, provenance = assignment.get(ai, (-1, "AMBIGUOUS", "unresolved"))
        if gi < 0:
            return BridgeResult(
                commit_id=r.commit_id,
                idx=r.idx,
                label=r.label,
                mapping_status=status,
                path_status=None,
                canonical_line_id=None,
                file_path=None,
                hunk_index=None,
                new_lineno=None,
                old_lineno=None,
                occurrence_index=None,
                text_status=None,
                provenance_method=provenance,
            )
        gl = git_lines[gi]
        cid = stable_line_id(
            r.commit_id,
            gl.file_path,
            gl.hunk_index,
            gl.change_type,
            gl.old_lineno,
            gl.new_lineno,
            gl.occurrence_index,
        )
        if r.raw_changed_line == gl.raw_text:
            ts = "RAW_EXACT"
        elif r.raw_changed_line in text_variants(gl.raw_text):
            ts = "UPSTREAM_TRANSFORM_EXACT"
        else:
            ts = "TEXT_CONFLICT"
        return BridgeResult(
            commit_id=r.commit_id,
            idx=r.idx,
            label=r.label,
            mapping_status=status,
            path_status="PATH_EXACT",
            canonical_line_id=cid,
            file_path=gl.file_path,
            hunk_index=gl.hunk_index,
            new_lineno=gl.new_lineno,
            old_lineno=gl.old_lineno,
            occurrence_index=gl.occurrence_index,
            text_status=ts,
            provenance_method=provenance,
        )

    return [make_result(ai) for ai in range(n)]


class RQ1CandidateMask:
    """Mask over canonical added lines for a test-positive commit."""

    RQ1_POSITIVE = "RQ1_POSITIVE"
    RQ1_NEGATIVE = "RQ1_NEGATIVE"
    NOT_IN_RQ1_UNIVERSE = "NOT_IN_RQ1_UNIVERSE"

    @staticmethod
    def classify(
        *,
        in_policy_a: bool,
        label: float | None,
    ) -> str:
        if not in_policy_a:
            return RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE
        if label == 1.0:
            return RQ1CandidateMask.RQ1_POSITIVE
        if label == 0.0:
            return RQ1CandidateMask.RQ1_NEGATIVE
        # Must never treat missing as negative
        return RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE


def collision_audit(results: Iterable[BridgeResult]) -> dict[str, int]:
    by_id: dict[str, list[tuple[str, int]]] = defaultdict(list)
    zero = multi_row = 0
    mapped = 0
    for r in results:
        if r.canonical_line_id is None:
            zero += 1
            continue
        mapped += 1
        by_id[r.canonical_line_id].append((r.commit_id, r.idx))
    collisions = sum(1 for v in by_id.values() if len(v) > 1)
    return {
        "mapped_rows": mapped,
        "zero_map": zero,
        "unique_canonical_ids": len(by_id),
        "collision_ids": collisions,
        "rows_in_collisions": sum(len(v) for v in by_id.values() if len(v) > 1),
    }


def flatten_block_added_texts(blocks: Any) -> list[str]:
    """Flatten JIT-Block released codes structure to ordered added texts."""
    out: list[str] = []
    for b in blocks:
        for j in range(0, len(b), 2):
            if b[j] == "added_code":
                out.append(b[j + 1])
    return out

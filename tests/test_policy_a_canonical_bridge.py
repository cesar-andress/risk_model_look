"""Tests for Policy-A → canonical Git line-ID bridge (no tokenization)."""

from __future__ import annotations

from src.data.git_diff_reconstruction import DiffLine, stable_line_id
from src.data.policy_a_canonical_bridge import (
    BridgeResult,
    PolicyARow,
    RQ1CandidateMask,
    collision_audit,
    map_policy_a_rows_to_git,
    punct_space,
    text_variants,
)


def _gl(
    raw: str,
    *,
    file: str = "A.java",
    hunk: int = 0,
    new: int = 1,
    occ: int = 0,
) -> DiffLine:
    return DiffLine(
        change_type="added",
        file_path=file,
        hunk_index=hunk,
        old_lineno=None,
        new_lineno=new,
        raw_text=raw,
        norm_text=raw.strip(),
        occurrence_index=occ,
    )


def _row(idx: int, raw: str, label: float = 0.0) -> PolicyARow:
    return PolicyARow(
        commit_id="c" * 40,
        idx=idx,
        changed_type="added",
        label=label,
        raw_changed_line=raw,
        changed_line=raw,
    )


def test_source_row_id_preserved_in_bridge_result():
    git = [_gl("foo();", new=10)]
    rows = [_row(7, punct_space("foo();"), label=1.0)]
    out = map_policy_a_rows_to_git(rows, git)
    assert len(out) == 1
    assert out[0].idx == 7
    assert out[0].commit_id == "c" * 40
    assert out[0].canonical_line_id is not None


def test_instrumentation_metadata_transparent_fields():
    """BridgeResult carries audit metadata without altering scientific IDs."""
    git = [_gl("x = 1;", new=3)]
    rows = [_row(0, punct_space("x = 1;"))]
    out = map_policy_a_rows_to_git(rows, git)[0]
    assert out.provenance_method
    assert out.mapping_status.startswith("RECOVERED")
    assert out.canonical_line_id == stable_line_id(
        "c" * 40, "A.java", 0, "added", None, 3, 0
    )


def test_duplicate_identical_added_lines_equal_multiplicity():
    git = [
        _gl("}", new=1, occ=0),
        _gl("}", new=2, occ=1),
    ]
    rows = [
        _row(0, "}"),
        _row(1, "}"),
    ]
    out = map_policy_a_rows_to_git(rows, git)
    assert all(r.canonical_line_id for r in out)
    assert out[0].canonical_line_id != out[1].canonical_line_id
    assert out[0].new_lineno == 1
    assert out[1].new_lineno == 2


def test_same_line_in_two_files_unique_by_path():
    git = [
        _gl("return 1;", file="A.java", new=1),
        _gl("return 1;", file="B.java", new=1),
    ]
    # Without file constraint, two cands → may need multiplicity if 2 rows
    rows = [_row(0, punct_space("return 1;")), _row(1, punct_space("return 1;"))]
    out = map_policy_a_rows_to_git(rows, git)
    assert {r.file_path for r in out} == {"A.java", "B.java"}


def test_same_line_twice_one_file_occurrence():
    git = [
        _gl("i++;", new=5, occ=0),
        _gl("i++;", new=9, occ=1),
    ]
    rows = [_row(0, punct_space("i++;")), _row(1, punct_space("i++;"))]
    out = map_policy_a_rows_to_git(rows, git)
    assert [r.new_lineno for r in out] == [5, 9]


def test_path_reconciliation_exact():
    git = [_gl("a;", file="pkg/X.java", new=1)]
    rows = [_row(0, punct_space("a;"))]
    out = map_policy_a_rows_to_git(rows, git)[0]
    assert out.path_status == "PATH_EXACT"
    assert out.file_path == "pkg/X.java"


def test_canonical_line_id_linkage():
    git = [_gl("z;", new=42, occ=0)]
    rows = [_row(3, punct_space("z;"), label=1.0)]
    out = map_policy_a_rows_to_git(rows, git)[0]
    assert out.canonical_line_id.endswith("|occ0")
    assert "|new42|" in out.canonical_line_id


def test_collision_audit_detects_duplicate_claims():
    results = [
        BridgeResult(
            commit_id="c" * 40,
            idx=0,
            label=1.0,
            mapping_status="RECOVERED_EXACT_BY_JITBLOCK",
            path_status="PATH_EXACT",
            canonical_line_id="ID1",
            file_path="A.java",
            hunk_index=0,
            new_lineno=1,
            old_lineno=None,
            occurrence_index=0,
            text_status="RAW_EXACT",
            provenance_method="t",
        ),
        BridgeResult(
            commit_id="c" * 40,
            idx=1,
            label=0.0,
            mapping_status="RECOVERED_EXACT_BY_JITBLOCK",
            path_status="PATH_EXACT",
            canonical_line_id="ID1",
            file_path="A.java",
            hunk_index=0,
            new_lineno=1,
            old_lineno=None,
            occurrence_index=0,
            text_status="RAW_EXACT",
            provenance_method="t",
        ),
        BridgeResult(
            commit_id="c" * 40,
            idx=2,
            label=0.0,
            mapping_status="NOT_FOUND",
            path_status=None,
            canonical_line_id=None,
            file_path=None,
            hunk_index=None,
            new_lineno=None,
            old_lineno=None,
            occurrence_index=None,
            text_status=None,
            provenance_method="t",
        ),
    ]
    audit = collision_audit(results)
    assert audit["collision_ids"] == 1
    assert audit["zero_map"] == 1
    assert audit["mapped_rows"] == 2


def test_rq1_mask_positive_negative_not_in_universe():
    assert (
        RQ1CandidateMask.classify(in_policy_a=True, label=1.0)
        == RQ1CandidateMask.RQ1_POSITIVE
    )
    assert (
        RQ1CandidateMask.classify(in_policy_a=True, label=0.0)
        == RQ1CandidateMask.RQ1_NEGATIVE
    )
    assert (
        RQ1CandidateMask.classify(in_policy_a=False, label=None)
        == RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE
    )


def test_git_added_outside_policy_a_is_not_rq1_negative():
    """Critical: unlabelled Git added line must never become RQ1_NEGATIVE."""
    assert (
        RQ1CandidateMask.classify(in_policy_a=False, label=0.0)
        == RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE
    )
    assert (
        RQ1CandidateMask.classify(in_policy_a=False, label=1.0)
        == RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE
    )


def test_text_variants_deterministic_not_fuzzy():
    raw = "foo.bar();"
    vs = text_variants(raw)
    assert punct_space(raw) in vs
    assert raw in vs

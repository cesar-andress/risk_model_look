"""Synthetic tests for ground-truth lineage helpers (no real repos / raw dumps)."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from scripts.audit_ground_truth_lineage import (
    LayerALine,
    flatten_layer_a_commit,
    line_variants,
    map_a_to_git,
    paths_equivalent,
    preprocess_code_line,
    punct_space,
)
from src.data.git_diff_reconstruction import DiffLine, stable_line_id


def test_flatten_preserves_labels_and_order() -> None:
    payload = {
        "added": {"a/A.java": ["x", "y", "x"]},
        "deleted": {},
        "added_buggy_level": {
            "a/A.java": {"added_buggy": ["x"], "added_clean": ["y", "x"]}
        },
    }
    rows = flatten_layer_a_commit("proj", "c0", payload)
    assert [r.text for r in rows] == ["x", "y", "x"]
    assert [r.label for r in rows] == [1.0, 0.0, 0.0]
    assert [r.occurrence_index for r in rows] == [0, 0, 1]


def test_punct_space_and_preprocess() -> None:
    assert punct_space("foo();") == "foo ( ) ;"
    out = preprocess_code_line('x = "hi";')
    assert "<STR>" in out


def test_duplicate_same_file_occurrence_mapping() -> None:
    a_rows = [
        LayerALine("p", "c", "A.java", "added", "foo", 1.0, 0),
        LayerALine("p", "c", "A.java", "added", "foo", 0.0, 1),
    ]
    git = [
        DiffLine("added", "A.java", 0, None, 1, "foo", "foo", 0),
        DiffLine("added", "A.java", 0, None, 2, "foo", "foo", 1),
    ]
    mapped = map_a_to_git(a_rows, git)
    assert all(m["git"] is not None for m in mapped)
    assert mapped[0]["git"].new_lineno == 1
    assert mapped[1]["git"].new_lineno == 2


def test_same_text_different_files() -> None:
    a_rows = [
        LayerALine("p", "c", "A.java", "added", "foo", 1.0, 0),
        LayerALine("p", "c", "B.java", "added", "foo", 1.0, 0),
    ]
    git = [
        DiffLine("added", "A.java", 0, None, 1, "foo", "foo", 0),
        DiffLine("added", "B.java", 0, None, 1, "foo", "foo", 0),
    ]
    mapped = map_a_to_git(a_rows, git)
    assert mapped[0]["git"].file_path == "A.java"
    assert mapped[1]["git"].file_path == "B.java"


def test_nonunique_alignment_rejected() -> None:
    a_rows = [LayerALine("p", "c", "A.java", "added", "foo", 1.0, 0)]
    git = [
        DiffLine("added", "A.java", 0, None, 1, "foo", "foo", 0),
        DiffLine("added", "A.java", 0, None, 2, "foo", "foo", 1),
    ]
    mapped = map_a_to_git(a_rows, git)
    assert mapped[0]["status"] == "AMBIGUOUS"


def test_sequence_disambiguation_unique() -> None:
    # Two identical foos in Git; A has only one foo between unique anchors →
    # neighbor window collapses to a single exact candidate.
    a_rows = [
        LayerALine("p", "c", "A.java", "added", "a", 0.0, 0),
        LayerALine("p", "c", "A.java", "added", "foo", 1.0, 0),
        LayerALine("p", "c", "A.java", "added", "b", 0.0, 0),
        LayerALine("p", "c", "A.java", "added", "foo", 0.0, 1),
    ]
    git = [
        DiffLine("added", "A.java", 0, None, 1, "a", "a", 0),
        DiffLine("added", "A.java", 0, None, 2, "foo", "foo", 0),
        DiffLine("added", "A.java", 0, None, 3, "b", "b", 0),
        DiffLine("added", "A.java", 0, None, 4, "foo", "foo", 1),
    ]
    mapped = map_a_to_git(a_rows, git)
    assert mapped[1]["git"] is not None
    assert mapped[1]["git"].new_lineno == 2
    assert mapped[3]["git"] is not None
    assert mapped[3]["git"].new_lineno == 4


def test_path_equivalence_exact_only() -> None:
    assert paths_equivalent("a/B.java", "a/B.java") == "EXACT_PATH"
    assert paths_equivalent("a/B.java", "c/B.java") is None


def test_lineage_label_preservation() -> None:
    payload = {
        "added": {"F.java": ["bug", "ok"]},
        "deleted": {},
        "added_buggy_level": {"F.java": {"added_buggy": ["bug"], "added_clean": ["ok"]}},
    }
    rows = flatten_layer_a_commit("p", "c", payload)
    assert sum(1 for r in rows if r.label == 1.0) == 1


def test_canonical_stable_line_ids_unique() -> None:
    lines = [
        DiffLine("added", "A.java", 0, None, 1, "x", "x", 0),
        DiffLine("added", "A.java", 0, None, 2, "x", "x", 1),
    ]
    ids = [
        stable_line_id("c", l.file_path, l.hunk_index, l.change_type, l.old_lineno, l.new_lineno, l.occurrence_index)
        for l in lines
    ]
    assert len(ids) == len(set(ids))


def test_line_variants_include_punct_space() -> None:
    assert punct_space("a();") in line_variants("a();")

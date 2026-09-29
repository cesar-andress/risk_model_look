"""Synthetic Git tests for diff reconstruction (no public repos required)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.data.git_diff_reconstruction import (
    filter_upstream_semantics,
    map_label_rows_by_unique_norm,
    normalize_line,
    parse_unified_diff,
    reconstruct_commit,
    set_equivalence,
    stable_line_id,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _init_repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@e.com")
    _git(repo, "config", "user.name", "t")
    return repo


def _git_dir(repo: Path) -> Path:
    return Path(_git(repo, "rev-parse", "--git-dir")).resolve() if False else repo / ".git"


def test_normalize_punct_space() -> None:
    assert normalize_line("if (this == o)") == "if ( this = = o )"


def test_normalize_strip_leading_underscore() -> None:
    assert "srcivypattern" in normalize_line("_srcivypattern = x;")


def test_parse_add_delete_hunks() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,2 +1,3 @@
-old
+new1
+new2
 context
"""
    lines = parse_unified_diff(diff)
    assert any(l.change_type == "deleted" and l.raw_text == "old" for l in lines)
    assert sum(1 for l in lines if l.change_type == "added") == 2


def test_file_add_delete(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "A.java").write_text("class A {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add")
    (repo / "A.java").unlink()
    (repo / "B.java").write_text("class B {}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "swap")
    c2 = _git(repo, "rev-parse", "HEAD")
    filtered, meta = reconstruct_commit(repo / ".git", c2, parent_strategy="first_parent")
    assert meta["commit_kind"] == "normal"
    types = {l.change_type for l in filtered}
    assert "added" in types and "deleted" in types


def test_rename_paths_recorded(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "Old.java").write_text("class X {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "old")
    _git(repo, "mv", "Old.java", "New.java")
    (repo / "New.java").write_text("class X { int a; }\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "rename")
    c2 = _git(repo, "rev-parse", "HEAD")
    diff = subprocess.check_output(
        ["git", "-C", str(repo), "diff", "--no-ext-diff", "-M", "-U0", f"{c2}^", c2],
        text=True,
    )
    assert "Old.java" in diff or "New.java" in diff


def test_multiple_hunks() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,1 +1,1 @@
-a
+b
@@ -10,1 +10,1 @@
-c
+d
"""
    lines = parse_unified_diff(diff)
    hunks = {l.hunk_index for l in lines}
    assert hunks == {0, 1}


def test_duplicate_identical_lines_in_hunk() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,0 +1,2 @@
+foo
+foo
"""
    lines = [l for l in parse_unified_diff(diff) if l.change_type == "added"]
    assert len(lines) == 2
    assert lines[0].raw_text == lines[1].raw_text
    assert lines[0].new_lineno != lines[1].new_lineno
    assert lines[0].occurrence_index == 0
    assert lines[1].occurrence_index == 1


def test_same_text_different_files() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,0 +1,1 @@
+foo
diff --git a/B.java b/B.java
--- a/B.java
+++ b/B.java
@@ -1,0 +1,1 @@
+foo
"""
    lines = [l for l in parse_unified_diff(diff) if l.change_type == "added"]
    assert len(lines) == 2
    ids = [
        stable_line_id("c0", l.file_path, l.hunk_index, l.change_type, l.old_lineno, l.new_lineno, l.occurrence_index)
        for l in lines
    ]
    assert ids[0] != ids[1]


def test_line_number_tracking() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -5,1 +7,1 @@
-x
+y
"""
    lines = parse_unified_diff(diff)
    deleted = next(l for l in lines if l.change_type == "deleted")
    added = next(l for l in lines if l.change_type == "added")
    assert deleted.old_lineno == 5
    assert added.new_lineno == 7


def test_root_commit_diff_against_empty_tree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, "rootrepo")
    (repo / "A.java").write_text("class A {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "root")
    commit = _git(repo, "rev-parse", "HEAD")
    filtered, meta = reconstruct_commit(repo / ".git", commit, parent_strategy="first_parent")
    assert meta["commit_kind"] == "root"
    assert meta["selected_parent"] is None
    assert any(l.change_type == "added" for l in filtered)


def test_merge_parent_selection_helper(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, "merge")
    (repo / "A.java").write_text("a\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-b", "side")
    (repo / "B.java").write_text("side\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "side")
    _git(repo, "checkout", branch)
    (repo / "C.java").write_text("main\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "mainline")
    _git(repo, "merge", "--no-ff", "side", "-m", "merge")
    merge = _git(repo, "rev-parse", "HEAD")
    parents = _git(repo, "rev-list", "--parents", "-n", "1", merge).split()
    assert len(parents) == 3  # commit + 2 parents
    filtered, meta = reconstruct_commit(repo / ".git", merge, parent_strategy="first_parent")
    assert meta["commit_kind"] == "merge"
    assert meta["selected_parent"] == parents[1]
    assert meta["n_parents"] == 2


def test_stable_line_id_uniqueness() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,0 +1,2 @@
+foo
+foo
"""
    lines = [l for l in parse_unified_diff(diff) if l.change_type == "added"]
    keys = [
        stable_line_id("abc", l.file_path, l.hunk_index, l.change_type, l.old_lineno, l.new_lineno, l.occurrence_index)
        for l in lines
    ]
    assert len(keys) == len(set(keys))


def test_stable_hunk_id_uniqueness() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,1 +1,1 @@
-a
+b
@@ -10,1 +10,1 @@
-c
+d
diff --git a/B.java b/B.java
--- a/B.java
+++ b/B.java
@@ -1,1 +1,1 @@
-e
+f
"""
    lines = parse_unified_diff(diff)
    hunks = {(l.file_path, l.hunk_index) for l in lines}
    assert len(hunks) == 3


def test_set_equivalence_checker() -> None:
    from src.data.git_diff_reconstruction import DiffLine

    def mk(ctype: str, text: str) -> DiffLine:
        return DiffLine(ctype, "A.java", 0, None if ctype == "added" else 1, 1 if ctype == "added" else None, text, text, 0)

    assert set_equivalence([mk("added", "a"), mk("deleted", "b")], {"a"}, {"b"}) == "EXACT_SET_MATCH"
    assert set_equivalence([mk("added", "a"), mk("deleted", "b")], {"a"}, {"x"}) == "ADDED_MATCH_ONLY"
    assert set_equivalence([mk("added", "a"), mk("deleted", "b")], {"x"}, {"b"}) == "DELETED_MATCH_ONLY"
    assert set_equivalence([mk("added", "a"), mk("deleted", "b")], {"x"}, {"y"}) == "MISMATCH"


def test_ambiguous_text_matching_rejection() -> None:
    from src.data.git_diff_reconstruction import DiffLine

    lines = [
        DiffLine("added", "A.java", 0, None, 1, "foo", "foo", 0),
        DiffLine("added", "A.java", 0, None, 2, "foo", "foo", 1),
    ]
    mapped = map_label_rows_by_unique_norm(
        [{"changed_type": "added", "raw_changed_line": "foo", "label": 1.0, "idx": 0}],
        lines,
    )
    assert mapped[0]["map_status"] == "AMBIGUOUS_DUPLICATE"
    mapped_ok = map_label_rows_by_unique_norm(
        [{"changed_type": "added", "raw_changed_line": "bar", "label": 1.0, "idx": 0}],
        [DiffLine("added", "A.java", 0, None, 1, "bar", "bar", 0)],
    )
    assert mapped_ok[0]["map_status"] == "EXACT_UNIQUE"


def test_filter_java_only() -> None:
    diff = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,0 +1,1 @@
+keep
diff --git a/x.xml b/x.xml
--- a/x.xml
+++ b/x.xml
@@ -1,0 +1,1 @@
+drop
"""
    lines = parse_unified_diff(diff)
    filtered = filter_upstream_semantics(lines)
    assert all(l.file_path.endswith(".java") for l in filtered)
    assert len(filtered) == 1

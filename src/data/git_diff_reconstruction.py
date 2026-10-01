"""Git diff reconstruction helpers for JIT-Defects4J (audit, not preprocessing)."""

from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


# Empirically validated against frozen added_code/removed_code sets on sample commits.
# Insert spaces around non-word characters, then collapse whitespace.
_PUNCT_RE = re.compile(r"([^\w\s])", flags=re.UNICODE)
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def normalize_line(text: str) -> str:
    """Punctuation spacing used by JIT-Fine line strings.

    Additionally strips a single leading underscore from identifier tokens and
    collapses spaces introduced inside double-quoted literals. Empirically
    required for many older Apache Ivy-style field names (_foo → foo), but
    still insufficient for full-corpus set equivalence.
    """
    s = " ".join(_PUNCT_RE.sub(r" \1 ", text).split())
    toks = []
    for t in s.split():
        if t.startswith("_") and len(t) > 1 and t[1].isalpha():
            t = t[1:]
        toks.append(t)
    s = " ".join(toks)
    s = re.sub(r'"\s+([^"]*?)\s+"', r'"\1"', s)
    return s


def is_filtered_java_line(raw: str) -> bool:
    """Return True if line should be EXCLUDED from upstream set representation."""
    t = raw.strip()
    if not t:
        return True
    if t.startswith("//"):
        return True
    if t.startswith("/*") or t.startswith("*") or t.endswith("*/"):
        return True
    return False


def keep_file(path: str | None) -> bool:
    return bool(path) and path.endswith(".java")


@dataclass
class DiffLine:
    change_type: str  # added | deleted
    file_path: str
    hunk_index: int
    old_lineno: int | None
    new_lineno: int | None
    raw_text: str
    norm_text: str
    occurrence_index: int  # 0-based among same (change_type, norm_text) in commit


def parse_unified_diff(
    diff_text: str, *, include_context: bool = False
) -> list[DiffLine]:
    """Parse `git show` / `git diff` into ordered lines.

    Default: added/deleted only. With include_context=True, also emit
    change_type='context' for lines starting with a space (-U<n> diffs).
    """
    rows: list[dict[str, Any]] = []
    file_old: str | None = None
    file_new: str | None = None
    hunk_idx = -1
    old_ln = 0
    new_ln = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            file_old = file_new = None
            continue
        if line.startswith("--- "):
            path = line[4:]
            if path.startswith("a/"):
                path = path[2:]
            file_old = None if path == "/dev/null" else path
            continue
        if line.startswith("+++ "):
            path = line[4:]
            if path.startswith("b/"):
                path = path[2:]
            file_new = None if path == "/dev/null" else path
            continue
        m = _HUNK_RE.match(line)
        if m:
            hunk_idx += 1
            old_ln = int(m.group(1))
            new_ln = int(m.group(3))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            fp = file_new or file_old or ""
            rows.append(
                {
                    "change_type": "added",
                    "file_path": fp,
                    "hunk_index": hunk_idx,
                    "old_lineno": None,
                    "new_lineno": new_ln,
                    "raw_text": line[1:],
                    "norm_text": normalize_line(line[1:]),
                }
            )
            new_ln += 1
            continue
        if line.startswith("-") and not line.startswith("---"):
            fp = file_new or file_old or ""
            rows.append(
                {
                    "change_type": "deleted",
                    "file_path": fp,
                    "hunk_index": hunk_idx,
                    "old_lineno": old_ln,
                    "new_lineno": None,
                    "raw_text": line[1:],
                    "norm_text": normalize_line(line[1:]),
                }
            )
            old_ln += 1
            continue
        if line.startswith(" "):
            if include_context:
                fp = file_new or file_old or ""
                rows.append(
                    {
                        "change_type": "context",
                        "file_path": fp,
                        "hunk_index": hunk_idx,
                        "old_lineno": old_ln,
                        "new_lineno": new_ln,
                        "raw_text": line[1:],
                        "norm_text": normalize_line(line[1:]),
                    }
                )
            old_ln += 1
            new_ln += 1
    # occurrence indices
    occ: dict[tuple[str, str], int] = defaultdict(int)
    out: list[DiffLine] = []
    for r in rows:
        key = (r["change_type"], r["norm_text"])
        idx = occ[key]
        occ[key] += 1
        out.append(
            DiffLine(
                change_type=r["change_type"],
                file_path=r["file_path"],
                hunk_index=r["hunk_index"],
                old_lineno=r["old_lineno"],
                new_lineno=r["new_lineno"],
                raw_text=r["raw_text"],
                norm_text=r["norm_text"],
                occurrence_index=idx,
            )
        )
    return out


def filter_upstream_semantics(lines: Iterable[DiffLine]) -> list[DiffLine]:
    """Apply Java path + comment/blank filters matching JIT-Fine set construction."""
    kept: list[DiffLine] = []
    occ: dict[tuple[str, str], int] = defaultdict(int)
    for ln in lines:
        if not keep_file(ln.file_path):
            continue
        if not ln.norm_text:
            continue
        if is_filtered_java_line(ln.raw_text):
            continue
        key = (ln.change_type, ln.norm_text)
        idx = occ[key]
        occ[key] += 1
        kept.append(
            DiffLine(
                change_type=ln.change_type,
                file_path=ln.file_path,
                hunk_index=ln.hunk_index,
                old_lineno=ln.old_lineno,
                new_lineno=ln.new_lineno,
                raw_text=ln.raw_text,
                norm_text=ln.norm_text,
                occurrence_index=idx,
            )
        )
    return kept


def sets_from_filtered(lines: Iterable[DiffLine]) -> tuple[set[str], set[str]]:
    added = {ln.norm_text for ln in lines if ln.change_type == "added"}
    deleted = {ln.norm_text for ln in lines if ln.change_type == "deleted"}
    return added, deleted


def git_show_numstat_parents(git_dir: Path, commit: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "--git-dir", str(git_dir), "rev-list", "--parents", "-n", "1", commit],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    parts = out.split()
    return parts[1:]  # parents


def git_diff_against_parent(git_dir: Path, commit: str, parent: str | None) -> str:
    """Deterministic no-color unified diff with zero context."""
    cmd = [
        "git",
        "--git-dir",
        str(git_dir),
        "-c",
        "color.ui=false",
        "-c",
        "diff.external=",
        "-c",
        "core.quotepath=false",
    ]
    if parent is None:
        # Root commit: compare against the empty tree object written into this repo.
        empty = subprocess.check_output(
            ["git", "--git-dir", str(git_dir), "mktree"],
            input=b"",
        ).decode().strip()
        cmd += ["diff", "--no-ext-diff", "--no-textconv", "-U0", empty, commit]
    else:
        cmd += ["diff", "--no-ext-diff", "--no-textconv", "-U0", parent, commit]
    return subprocess.check_output(cmd, text=True, errors="replace", stderr=subprocess.DEVNULL)


def reconstruct_commit(
    git_dir: Path,
    commit: str,
    *,
    parent_strategy: str = "first_parent",
) -> tuple[list[DiffLine], dict[str, Any]]:
    parents = git_show_numstat_parents(git_dir, commit)
    meta = {
        "n_parents": len(parents),
        "parents": parents,
        "parent_strategy": parent_strategy,
        "selected_parent": None,
    }
    if not parents:
        parent = None
        meta["commit_kind"] = "root"
    elif len(parents) == 1:
        parent = parents[0]
        meta["commit_kind"] = "normal"
    else:
        meta["commit_kind"] = "merge"
        if parent_strategy == "first_parent":
            parent = parents[0]
        else:
            raise ValueError(f"unsupported parent_strategy={parent_strategy}")
    meta["selected_parent"] = parent
    diff_text = git_diff_against_parent(git_dir, commit, parent)
    raw_lines = parse_unified_diff(diff_text)
    filtered = filter_upstream_semantics(raw_lines)
    return filtered, meta


def set_equivalence(
    filtered: list[DiffLine],
    upstream_added: set[str],
    upstream_deleted: set[str],
) -> str:
    a, d = sets_from_filtered(filtered)
    am = a == upstream_added
    dm = d == upstream_deleted
    if am and dm:
        return "EXACT_SET_MATCH"
    if am and not dm:
        return "ADDED_MATCH_ONLY"
    if dm and not am:
        return "DELETED_MATCH_ONLY"
    if not filtered and not upstream_added and not upstream_deleted:
        return "NO_DIFF"
    return "MISMATCH"


def stable_line_id(
    commit_hash: str,
    file_path: str,
    hunk_index: int,
    change_type: str,
    old_lineno: int | None,
    new_lineno: int | None,
    occurrence_index: int,
) -> str:
    ol = "NA" if old_lineno is None else str(old_lineno)
    nl = "NA" if new_lineno is None else str(new_lineno)
    return f"{commit_hash}|{file_path}|h{hunk_index}|{change_type}|old{ol}|new{nl}|occ{occurrence_index}"


def map_label_rows_by_unique_norm(
    label_rows: list[dict[str, Any]],
    filtered: list[DiffLine],
) -> list[dict[str, Any]]:
    """Map label rows (raw_changed_line, changed_type, label, idx) to filtered diff lines.

    Primary rule: exact unique norm_text within change_type.
    Duplicate texts → AMBIGUOUS_DUPLICATE unless a single occurrence remains after
    matching labeled rows greedily is disallowed — we reject arbitrary first-hit.
    """
    by_key: dict[tuple[str, str], list[DiffLine]] = defaultdict(list)
    for ln in filtered:
        by_key[(ln.change_type, ln.norm_text)].append(ln)

    results = []
    for row in label_rows:
        ctype = "added" if row["changed_type"] == "added" else "deleted"
        norm = row["raw_changed_line"]
        cands = by_key.get((ctype, norm), [])
        if not cands:
            results.append({**row, "map_status": "MISSING_DIFF_LINE", "diff_line": None})
        elif len(cands) == 1:
            results.append({**row, "map_status": "EXACT_UNIQUE", "diff_line": cands[0]})
        else:
            results.append({**row, "map_status": "AMBIGUOUS_DUPLICATE", "diff_line": None})
    return results


# Canonical Apache GitHub mapping for the 21 JIT-Defects4J projects.
PROJECT_REPO_URLS: dict[str, str] = {
    "ant-ivy": "https://github.com/apache/ant-ivy.git",
    "commons-bcel": "https://github.com/apache/commons-bcel.git",
    "commons-beanutils": "https://github.com/apache/commons-beanutils.git",
    "commons-codec": "https://github.com/apache/commons-codec.git",
    "commons-collections": "https://github.com/apache/commons-collections.git",
    "commons-compress": "https://github.com/apache/commons-compress.git",
    "commons-configuration": "https://github.com/apache/commons-configuration.git",
    "commons-dbcp": "https://github.com/apache/commons-dbcp.git",
    "commons-digester": "https://github.com/apache/commons-digester.git",
    "commons-io": "https://github.com/apache/commons-io.git",
    "commons-jcs": "https://github.com/apache/commons-jcs.git",
    "commons-lang": "https://github.com/apache/commons-lang.git",
    "commons-math": "https://github.com/apache/commons-math.git",
    "commons-net": "https://github.com/apache/commons-net.git",
    "commons-scxml": "https://github.com/apache/commons-scxml.git",
    "commons-validator": "https://github.com/apache/commons-validator.git",
    "commons-vfs": "https://github.com/apache/commons-vfs.git",
    "giraph": "https://github.com/apache/giraph.git",
    "gora": "https://github.com/apache/gora.git",
    "opennlp": "https://github.com/apache/opennlp.git",
    "parquet-mr": "https://github.com/apache/parquet-mr.git",
}

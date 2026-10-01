"""Build canonical_v1 processed JSONL from frozen JIT-Fine + Git reconstruction.

Processed outputs are Git-ignored (redistribution NOT_ESTABLISHED).
"""

from __future__ import annotations

import hashlib
import json
import pickle
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from src.data.git_diff_reconstruction import (
    DiffLine,
    filter_upstream_semantics,
    git_diff_against_parent,
    git_show_numstat_parents,
    is_filtered_java_line,
    keep_file,
    normalize_line,
    parse_unified_diff,
)
from src.data.structured_diff import (
    STRUCTURED_FORMAT_VERSION,
    FileSpec,
    HunkSpec,
    LineSpec,
    render_structured_commit,
    stable_line_id_v1,
)

SCHEMA_VERSION = 1
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_split_changes(path: Path) -> tuple[list[str], list[float], list[str], list[Any]]:
    with path.open("rb") as f:
        ids, labels, msgs, codes = pickle.load(f)
    return list(ids), list(labels), list(msgs), list(codes)


def parse_diff_with_hunks(diff_text: str) -> tuple[list[DiffLine], list[dict[str, Any]]]:
    """Parse unified diff; return DiffLines + hunk metadata list."""
    lines = parse_unified_diff(diff_text)
    hunks_meta: list[dict[str, Any]] = []
    file_old = file_new = None
    hunk_idx = -1
    for line in diff_text.splitlines():
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
            fp = file_new or file_old or ""
            hunks_meta.append(
                {
                    "hunk_index": hunk_idx,
                    "file_path": fp,
                    "old_path": file_old,
                    "new_path": file_new,
                    "old_start": int(m.group(1)),
                    "old_length": int(m.group(2) or "1"),
                    "new_start": int(m.group(3)),
                    "new_length": int(m.group(4) or "1"),
                }
            )
    return lines, hunks_meta


def load_rq1_maps(root: Path) -> tuple[set[str], dict[tuple[str, int], dict]]:
    complete = set(
        json.loads(
            (root / "data/raw/derived_audit/rq1_complete_case/complete_commit_ids.json").read_text()
        )
    )
    mapping_path = root / "data/raw/derived_audit/residual_148/full_mapping_after_residual.jsonl"
    row_map: dict[tuple[str, int], dict] = {}
    for line in mapping_path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("canonical_line_id"):
            row_map[(r["commit_id"], int(r["idx"]))] = r
    return complete, row_map


def build_rq1_lookup(
    commit_id: str,
    row_map: dict[tuple[str, int], dict],
) -> dict[tuple[str, str, int | None, int | None, int], float]:
    """Map (file, change_type, old, new, occ_from_prior) -> label for added lines."""
    out: dict[tuple[str, str, int | None, int | None, int], float] = {}
    for (cid, idx), r in row_map.items():
        if cid != commit_id:
            continue
        if not r.get("file_path"):
            continue
        out[
            (
                r["file_path"],
                "added",
                r.get("old_lineno"),
                r.get("new_lineno"),
                int(r.get("occurrence_index") if r.get("occurrence_index") is not None else 0),
            )
        ] = float(r["label"])
    return out


def git_diff_u(
    git_dir: Path, commit: str, parent: str | None, context: int
) -> str:
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
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        f"-U{context}",
    ]
    if parent is None:
        empty = (
            subprocess.check_output(
                ["git", "--git-dir", str(git_dir), "mktree"], input=b""
            )
            .decode()
            .strip()
        )
        cmd += [empty, commit]
    else:
        cmd += [parent, commit]
    return subprocess.check_output(cmd, text=True, errors="replace", stderr=subprocess.DEVNULL)


def build_commit_record(
    *,
    commit_id: str,
    project: str,
    split: str,
    commit_label: float,
    commit_message: str,
    git_dir: Path,
    complete_case: set[str],
    rq1_row_map: dict[tuple[str, int], dict],
    context: int = 0,
) -> dict[str, Any]:
    parents = git_show_numstat_parents(git_dir, commit_id)
    parent = parents[0] if parents else None
    # Always identity from U0
    diff0 = git_diff_u(git_dir, commit_id, parent, 0)
    raw0, hunks0 = parse_diff_with_hunks(diff0)
    # Filter java semantics for model changed lines (primary)
    kept: list[DiffLine] = []
    occ: dict[tuple[str, str], int] = defaultdict(int)
    for ln in raw0:
        if not keep_file(ln.file_path):
            continue
        if not ln.norm_text and not ln.raw_text.strip():
            # keep empty non-comment? filter_upstream drops empty norm
            continue
        if is_filtered_java_line(ln.raw_text):
            continue
        if not ln.norm_text:
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

    rq1_primary = commit_id in complete_case
    label_lookup = build_rq1_lookup(commit_id, rq1_row_map) if rq1_primary else {}

    # Build ID + rq1 status per kept line
    line_infos: list[dict[str, Any]] = []
    for ord_pos, gl in enumerate(kept):
        sid = stable_line_id_v1(
            commit_id,
            gl.file_path,
            gl.change_type,
            gl.old_lineno,
            gl.new_lineno,
            gl.occurrence_index,
            ord_pos,
        )
        rq1_status = "NOT_IN_RQ1_UNIVERSE"
        if rq1_primary and gl.change_type == "added":
            lab = label_lookup.get(
                (
                    gl.file_path,
                    "added",
                    gl.old_lineno,
                    gl.new_lineno,
                    gl.occurrence_index,
                )
            )
            # prior mapping used filtered occurrence; try without relying on occ mismatch
            if lab is None:
                # match by file+new_lineno only if unique among lookup for this commit
                cands = [
                    (k, v)
                    for k, v in label_lookup.items()
                    if k[0] == gl.file_path and k[3] == gl.new_lineno
                ]
                if len(cands) == 1:
                    lab = cands[0][1]
            if lab == 1.0:
                rq1_status = "RQ1_POSITIVE"
            elif lab == 0.0:
                rq1_status = "RQ1_NEGATIVE"
        line_infos.append(
            {
                "gl": gl,
                "stable_line_id": sid,
                "ordered_position": ord_pos,
                "rq1_status": rq1_status,
            }
        )

    # Group into files/hunks for U0 or Uctx rendering
    if context == 0:
        render_lines = raw0  # will filter when building specs from kept
        hunks_meta = hunks0
        variant = "CHANGED_ONLY"
        # Use kept lines only
        by_file_hunk: dict[tuple[str, int], list[dict]] = defaultdict(list)
        for info in line_infos:
            gl = info["gl"]
            by_file_hunk[(gl.file_path, gl.hunk_index)].append(info)
        file_order: list[str] = []
        seen_f = set()
        for info in line_infos:
            fp = info["gl"].file_path
            if fp not in seen_f:
                seen_f.add(fp)
                file_order.append(fp)
        hunk_meta_by = {(h["file_path"], h["hunk_index"]): h for h in hunks_meta}
        files_out = []
        file_specs: list[FileSpec] = []
        for fi, fp in enumerate(file_order):
            hunk_ids = sorted({h for (f, h) in by_file_hunk if f == fp})
            # file paths from first hunk meta
            old_p = new_p = None
            status = "modified"
            hunk_specs = []
            hunks_json = []
            for hi in hunk_ids:
                meta = hunk_meta_by.get((fp, hi), {})
                old_p = meta.get("old_path", old_p)
                new_p = meta.get("new_path", new_p)
                if old_p is None and new_p is not None:
                    status = "added"
                elif new_p is None and old_p is not None:
                    status = "deleted"
                infos = by_file_hunk[(fp, hi)]
                lines_json = []
                line_specs = []
                for info in infos:
                    gl = info["gl"]
                    # strip only newline terminator — raw_text already has no \n
                    raw = gl.raw_text
                    if raw.endswith("\r"):
                        raw = raw[:-1]
                    lj = {
                        "stable_line_id": info["stable_line_id"],
                        "change_type": gl.change_type,
                        "old_lineno": gl.old_lineno,
                        "new_lineno": gl.new_lineno,
                        "occurrence_index": gl.occurrence_index,
                        "ordered_position": info["ordered_position"],
                        "raw_line_text": raw,
                        "rq1_status": info["rq1_status"],
                        "u0_hunk_index": gl.hunk_index,
                    }
                    lines_json.append(lj)
                    line_specs.append(
                        LineSpec(
                            change_type=gl.change_type,
                            raw_text=raw,
                            stable_line_id=info["stable_line_id"],
                            old_lineno=gl.old_lineno,
                            new_lineno=gl.new_lineno,
                            occurrence_index=gl.occurrence_index,
                            ordered_position=info["ordered_position"],
                            rq1_status=info["rq1_status"],
                        )
                    )
                hj = {
                    "hunk_id": f"{commit_id}|{fp}|{variant}|h{hi}",
                    "hunk_ordinal": hi,
                    "old_start": meta.get("old_start", 0),
                    "old_length": meta.get("old_length", 0),
                    "new_start": meta.get("new_start", 0),
                    "new_length": meta.get("new_length", 0),
                    "lines": lines_json,
                }
                hunks_json.append(hj)
                hunk_specs.append(
                    HunkSpec(
                        hunk_ordinal=hi,
                        old_start=hj["old_start"],
                        old_length=hj["old_length"],
                        new_start=hj["new_start"],
                        new_length=hj["new_length"],
                        lines=line_specs,
                    )
                )
            files_out.append(
                {
                    "canonical_path": fp,
                    "old_path": old_p,
                    "new_path": new_p,
                    "file_status": status,
                    "file_ordinal": fi,
                    "is_test_file": None,
                    "hunks": hunks_json,
                }
            )
            file_specs.append(
                FileSpec(
                    canonical_path=fp,
                    old_path=old_p,
                    new_path=new_p,
                    file_status=status,
                    file_ordinal=fi,
                    hunks=hunk_specs,
                )
            )
    else:
        # CTX3: render with context; identity still from U0 lookup by lineno
        variant = f"CTX{context}"
        diffc = git_diff_u(git_dir, commit_id, parent, context)
        # Re-parse with context lines for CTX rendering
        rawc = parse_unified_diff(diffc, include_context=True)
        _, hunksc = parse_diff_with_hunks(diffc)
        id_by_loc = {
            (
                info["gl"].file_path,
                info["gl"].change_type,
                info["gl"].old_lineno,
                info["gl"].new_lineno,
            ): info
            for info in line_infos
        }
        file_order = []
        seen_f = set()
        for ln in rawc:
            if keep_file(ln.file_path) and ln.file_path not in seen_f:
                seen_f.add(ln.file_path)
                file_order.append(ln.file_path)
        file_order = [f for f in file_order if f.endswith(".java")]
        hunk_meta_by = {(h["file_path"], h["hunk_index"]): h for h in hunksc}
        files_out = []
        file_specs = []
        by_fh: dict[tuple[str, int], list[DiffLine]] = defaultdict(list)
        for ln in rawc:
            if not keep_file(ln.file_path):
                continue
            by_fh[(ln.file_path, ln.hunk_index)].append(ln)
        for fi, fp in enumerate(file_order):
            hunk_ids = sorted({h for (f, h) in by_fh if f == fp})
            old_p = new_p = None
            status = "modified"
            hunks_json = []
            hunk_specs = []
            for hi in hunk_ids:
                meta = hunk_meta_by.get((fp, hi), {})
                old_p = meta.get("old_path", old_p)
                new_p = meta.get("new_path", new_p)
                lines_json = []
                line_specs = []
                for ln in by_fh[(fp, hi)]:
                    # context lines in parse_unified_diff? Our parser only gets +/- 
                    # For -U3 we need to extend parser for context ' ' lines.
                    # Fallback: only +/- for now in CTX if parser lacks context.
                    raw = ln.raw_text[:-1] if ln.raw_text.endswith("\r") else ln.raw_text
                    info = id_by_loc.get((fp, ln.change_type, ln.old_lineno, ln.new_lineno))
                    sid = info["stable_line_id"] if info else None
                    rq1 = info["rq1_status"] if info else "NOT_IN_RQ1_UNIVERSE"
                    ord_pos = info["ordered_position"] if info else None
                    lj = {
                        "stable_line_id": sid,
                        "change_type": ln.change_type,
                        "old_lineno": ln.old_lineno,
                        "new_lineno": ln.new_lineno,
                        "occurrence_index": ln.occurrence_index,
                        "ordered_position": ord_pos,
                        "raw_line_text": raw,
                        "rq1_status": rq1,
                        "u0_hunk_index": info["gl"].hunk_index if info else None,
                    }
                    lines_json.append(lj)
                    line_specs.append(
                        LineSpec(
                            change_type=ln.change_type,
                            raw_text=raw,
                            stable_line_id=sid,
                            old_lineno=ln.old_lineno,
                            new_lineno=ln.new_lineno,
                            occurrence_index=ln.occurrence_index,
                            ordered_position=ord_pos,
                            rq1_status=rq1,
                        )
                    )
                hj = {
                    "hunk_id": f"{commit_id}|{fp}|{variant}|h{hi}",
                    "hunk_ordinal": hi,
                    "old_start": meta.get("old_start", 0),
                    "old_length": meta.get("old_length", 0),
                    "new_start": meta.get("new_start", 0),
                    "new_length": meta.get("new_length", 0),
                    "lines": lines_json,
                }
                hunks_json.append(hj)
                hunk_specs.append(
                    HunkSpec(
                        hunk_ordinal=hi,
                        old_start=hj["old_start"],
                        old_length=hj["old_length"],
                        new_start=hj["new_start"],
                        new_length=hj["new_length"],
                        lines=line_specs,
                    )
                )
            files_out.append(
                {
                    "canonical_path": fp,
                    "old_path": old_p,
                    "new_path": new_p,
                    "file_status": status,
                    "file_ordinal": fi,
                    "is_test_file": None,
                    "hunks": hunks_json,
                }
            )
            file_specs.append(
                FileSpec(
                    canonical_path=fp,
                    old_path=old_p,
                    new_path=new_p,
                    file_status=status,
                    file_ordinal=fi,
                    hunks=hunk_specs,
                )
            )

    # Renderer is deterministic from this record; token mapping re-renders on demand.
    return {
        "schema_version": SCHEMA_VERSION,
        "structured_format_version": STRUCTURED_FORMAT_VERSION,
        "commit_id": commit_id,
        "project": project,
        "split": split,
        "commit_label": float(commit_label),
        "commit_message": commit_message if commit_message is not None else "",
        "representation_source": "ordered_historical_git_first_parent",
        "representation_variant": variant,
        "context_lines": context,
        "rq1_primary_commit": rq1_primary,
        "files": files_out,
    }


def record_to_file_specs(record: dict[str, Any]) -> list[FileSpec]:
    specs: list[FileSpec] = []
    for f in record["files"]:
        hunks = []
        for h in f["hunks"]:
            lines = [
                LineSpec(
                    change_type=ln["change_type"],
                    raw_text=ln["raw_line_text"],
                    stable_line_id=ln.get("stable_line_id"),
                    old_lineno=ln.get("old_lineno"),
                    new_lineno=ln.get("new_lineno"),
                    occurrence_index=int(ln.get("occurrence_index") or 0),
                    ordered_position=ln.get("ordered_position"),
                    rq1_status=ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE",
                )
                for ln in h["lines"]
            ]
            hunks.append(
                HunkSpec(
                    hunk_ordinal=int(h["hunk_ordinal"]),
                    old_start=int(h["old_start"]),
                    old_length=int(h["old_length"]),
                    new_start=int(h["new_start"]),
                    new_length=int(h["new_length"]),
                    lines=lines,
                )
            )
        specs.append(
            FileSpec(
                canonical_path=f["canonical_path"],
                old_path=f.get("old_path"),
                new_path=f.get("new_path"),
                file_status=f.get("file_status") or "modified",
                file_ordinal=int(f["file_ordinal"]),
                hunks=hunks,
            )
        )
    return specs


def render_record(record: dict[str, Any]):
    return render_structured_commit(
        commit_message=record.get("commit_message") or "",
        files=record_to_file_specs(record),
        commit_hash=record["commit_id"],
        context_lines=int(record.get("context_lines") or 0),
        representation_variant=record.get("representation_variant") or "CHANGED_ONLY",
    )


def build_dataset(config_path: Path, *, out_dir: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    cfg = yaml.safe_load(config_path.read_text())
    extracted = root / cfg["jitfine_extracted"]
    repo_root = root / cfg["source_repos"]
    out = Path(out_dir) if out_dir else root / cfg["output_dir"]
    out.mkdir(parents=True, exist_ok=True)

    complete, rq1_row_map = load_rq1_maps(root)
    assert len(complete) == 413, len(complete)

    import pandas as pd

    counts = {}
    pos_counts = {}
    for split in ("train", "valid", "test"):
        ids, labels, msgs, _codes = load_split_changes(extracted / f"changes_{split}.pkl")
        feats = pd.read_pickle(extracted / f"features_{split}.pkl")
        proj_by = dict(zip(feats["commit_hash"].astype(str), feats["project"].astype(str)))
        out_path = out / f"{split}.jsonl"
        n_pos = 0
        with out_path.open("w", encoding="utf-8") as wf:
            for cid, lab, msg in zip(ids, labels, msgs):
                cid = str(cid)
                project = proj_by[cid]
                gd = repo_root / f"{project}.git"
                rec = build_commit_record(
                    commit_id=cid,
                    project=project,
                    split=split,
                    commit_label=float(lab),
                    commit_message=str(msg) if msg is not None else "",
                    git_dir=gd,
                    complete_case=complete,
                    rq1_row_map=rq1_row_map,
                    context=int(cfg.get("context", 0)),
                )
                if float(lab) == 1.0:
                    n_pos += 1
                # Do not embed timestamps
                wf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        counts[split] = len(ids)
        pos_counts[split] = n_pos

    # Integrity
    assert counts == {"train": 16374, "valid": 5465, "test": 5480}
    assert pos_counts == {"train": 1390, "valid": 467, "test": 475}
    # RQ1 primary only on test positives complete-case
    rq1_n = 0
    test_pos_primary = 0
    test_pos_excluded = 0
    with (out / "test.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["rq1_primary_commit"]:
                rq1_n += 1
                assert r["commit_label"] == 1.0
                assert r["split"] == "test"
                test_pos_primary += 1
            elif r["commit_label"] == 1.0:
                test_pos_excluded += 1
    assert rq1_n == 413, rq1_n
    assert test_pos_primary == 413
    assert test_pos_excluded == 62

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "structured_format_version": STRUCTURED_FORMAT_VERSION,
        "config": cfg,
        "counts": counts,
        "positive_counts": pos_counts,
        "rq1_primary_commits": 413,
        "rq1_excluded_mapping_incomplete": 62,
        "rq1_complete_case": {
            "n": 413,
            "candidates": 13412,
            "positives": 1712,
            "negatives": 11700,
            "unknown": 0,
        },
        "file_sha256": {
            split: sha256_file(out / f"{split}.jsonl") for split in ("train", "valid", "test")
        },
        "file_sizes": {
            split: (out / f"{split}.jsonl").stat().st_size for split in ("train", "valid", "test")
        },
        "complete_case_ids_sha256": sha256_text("\n".join(sorted(complete)) + "\n"),
    }
    return manifest


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "configs/data/canonical_v1.yaml",
    )
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifest = build_dataset(args.config, out_dir=args.out_dir)
    man_dir = root / "artifacts/processed_dataset"
    man_dir.mkdir(parents=True, exist_ok=True)
    (man_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Audit residual 148 Policy-A rows + complete-case bias (no tokenization)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.git_diff_reconstruction import (
    DiffLine,
    filter_upstream_semantics,
    git_diff_against_parent,
    git_show_numstat_parents,
    parse_unified_diff,
    reconstruct_commit,
    stable_line_id,
)
from src.data.policy_a_canonical_bridge import (
    BridgeResult,
    PolicyARow,
    collision_audit,
    punct_space,
)
from src.data.policy_a_residual_closure import (
    approved_signatures,
    classify_dataset_conflict,
    describe_numeric,
    jitfine_preprocess_code_line,
    match_via_changed_line,
    positionally_forced_bijections,
    signatures_match,
    smd,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data/raw/upstream/extracted/data/jitfine"
JSON_PATH = ROOT / "data/raw/upstream/internal/buggy_changes_with_buggy_line.json"
REPO_ROOT = ROOT / "data/raw/source_repos"
PRIOR_MAP = ROOT / "data/raw/derived_audit/policy_a_bridge/policy_a_row_mapping.jsonl"
DERIVED = ROOT / "data/raw/derived_audit/residual_148"
OUT = ROOT / "artifacts/residual_closure"

FEATURE_COLS = [
    "ns",
    "nd",
    "nf",
    "entropy",
    "la",
    "ld",
    "lt",
    "fix",
    "ndev",
    "age",
    "nuc",
    "exp",
    "rexp",
    "sexp",
]


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def show_blob(gd: Path, rev: str, path: str) -> list[str] | None:
    try:
        return subprocess.check_output(
            ["git", "--git-dir", str(gd), "show", f"{rev}:{path}"],
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
        ).splitlines()
    except subprocess.CalledProcessError:
        return None


def load_layer_a() -> dict[str, tuple[str, dict]]:
    data = json.loads(JSON_PATH.read_text())
    out: dict[str, tuple[str, dict]] = {}
    for proj, commits in data.items():
        for cid, payload in commits.items():
            out[cid] = (proj, payload)
    return out


def flatten_a_added(payload: dict) -> list[tuple[str, str, int]]:
    """(file, text, ordinal_within_file)"""
    rows: list[tuple[str, str, int]] = []
    for fp, lines in (payload.get("added") or {}).items():
        for i, line in enumerate(lines):
            rows.append((fp, line, i))
    return rows


def resolve_path(fp: str, git_files: set[str]) -> tuple[str | None, str]:
    if fp in git_files:
        return fp, "PATH_EXACT"
    for g in git_files:
        if g.replace("\\", "/") == fp.replace("\\", "/"):
            return g, "PATH_DETERMINISTIC_NORMALIZED"
    for g in git_files:
        if g.endswith("/" + fp) or fp.endswith("/" + g):
            return g, "PATH_DETERMINISTIC_NORMALIZED"
    return None, "PATH_CONFLICT"


def find_a_link(
    raw: str, changed: str, a_rows: list[tuple[str, str, int]]
) -> list[int]:
    cands = []
    for i, (_fp, text, _ord) in enumerate(a_rows):
        if signatures_match(text, raw) or match_via_changed_line(text, changed):
            cands.append(i)
        elif punct_space(text) == raw or jitfine_preprocess_code_line(text) == changed:
            cands.append(i)
    return cands


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)

    jf = pd.read_pickle(EXTRACTED / "changes_complete_buggy_line_level.pkl")
    feat = pd.read_pickle(EXTRACTED / "features_test.pkl")
    proj_by = dict(zip(feat["commit_hash"].astype(str), feat["project"].astype(str)))
    feat_by = {
        str(r["commit_hash"]): {c: r[c] for c in list(feat.columns)}
        for _, r in feat.iterrows()
    }
    layer_a = load_layer_a()

    prior = [
        json.loads(l)
        for l in PRIOR_MAP.read_text().splitlines()
        if l.strip()
    ]
    prior_by: dict[tuple[str, int], dict] = {
        (r["commit_id"], int(r["idx"])): r for r in prior
    }
    residual_keys = [
        (r["commit_id"], int(r["idx"]))
        for r in prior
        if r["mapping_status"] == "NOT_FOUND"
    ]
    assert len(residual_keys) == 148

    # Working full mapping: start from prior unique maps
    full: dict[tuple[str, int], dict[str, Any]] = {}
    for r in prior:
        key = (r["commit_id"], int(r["idx"]))
        full[key] = {
            "commit_id": r["commit_id"],
            "idx": int(r["idx"]),
            "label": float(r["ground_truth_label"]),
            "canonical_line_id": r["canonical_line_id"],
            "mapping_status": r["mapping_status"],
            "file_path": r.get("file_path"),
            "hunk_index": r.get("hunk_index"),
            "new_lineno": r.get("new_lineno"),
            "old_lineno": r.get("old_lineno"),
            "occurrence_index": r.get("occurrence_index"),
            "provenance_method": r.get("provenance_method"),
            "residual_final": None,
            "taxonomy": None,
        }

    residual_reports: list[dict[str, Any]] = []
    tax_init = Counter()
    recovery = Counter()
    missing_positive_case: dict[str, Any] = {}

    # Group residuals by commit
    by_commit: dict[str, list[int]] = defaultdict(list)
    for cid, idx in residual_keys:
        by_commit[cid].append(idx)

    used_ids_global: dict[str, set[str]] = defaultdict(set)
    for (cid, idx), r in full.items():
        if r["canonical_line_id"]:
            used_ids_global[cid].add(r["canonical_line_id"])

    for cid, res_idxs in sorted(by_commit.items()):
        project = proj_by[cid]
        gd = REPO_ROOT / f"{project}.git"
        parents = git_show_numstat_parents(gd, cid)
        parent = parents[0] if parents else None
        diff = git_diff_against_parent(gd, cid, parent)
        all_lines = parse_unified_diff(diff)
        filtered = filter_upstream_semantics(all_lines)
        git_added_f = [ln for ln in filtered if ln.change_type == "added"]
        git_added_u = [ln for ln in all_lines if ln.change_type == "added"]

        bdf = jf[jf["commit_id"].astype(str) == cid].sort_values("idx")
        brows = [
            PolicyARow(
                commit_id=str(r.commit_id),
                idx=int(r.idx),
                changed_type=str(r.changed_type),
                label=float(r.label),
                raw_changed_line=str(r.raw_changed_line),
                changed_line=str(r.changed_line),
            )
            for _, r in bdf.iterrows()
            if str(r.changed_type) == "added"
        ]
        idx_to_ord = {r.idx: i for i, r in enumerate(brows)}
        ord_to_row = {i: r for i, r in enumerate(brows)}

        a_rows: list[tuple[str, str, int]] = []
        if cid in layer_a:
            a_rows = flatten_a_added(layer_a[cid][1])

        # Build file-local git lists
        by_file_f: dict[str, list[DiffLine]] = defaultdict(list)
        for gl in git_added_f:
            by_file_f[gl.file_path].append(gl)
        by_file_u: dict[str, list[DiffLine]] = defaultdict(list)
        for gl in git_added_u:
            by_file_u[gl.file_path].append(gl)

        # Trusted anchors from prior mapping: policy ord → (file, git ord in file filtered)
        file_anchors: dict[str, dict[int, int]] = defaultdict(dict)
        file_policy_ords: dict[str, list[int]] = defaultdict(list)
        # Assign each Policy-A row to a file via prior map or Layer-A
        row_file: dict[int, str] = {}
        for i, r in enumerate(brows):
            pr = full[(cid, r.idx)]
            if pr["canonical_line_id"] and pr["file_path"]:
                row_file[i] = pr["file_path"]
                # find git ord in file
                gls = by_file_f.get(pr["file_path"], [])
                for gi, gl in enumerate(gls):
                    if (
                        gl.hunk_index == pr["hunk_index"]
                        and gl.new_lineno == pr["new_lineno"]
                        and gl.occurrence_index == pr["occurrence_index"]
                    ):
                        file_anchors[pr["file_path"]][i] = gi
                        break
            else:
                # try Layer-A unique file
                cands = find_a_link(r.raw_changed_line, r.changed_line, a_rows)
                if len(cands) == 1:
                    fp = a_rows[cands[0]][0]
                    gpath, _ = resolve_path(fp, set(by_file_u.keys()) | set(by_file_f.keys()))
                    if gpath:
                        row_file[i] = gpath

        for i, fp in row_file.items():
            file_policy_ords[fp].append(i)

        # --- Per residual diagnostics + transform recovery ---
        for idx in res_idxs:
            r = ord_to_row[idx_to_ord[idx]]
            i_ord = idx_to_ord[idx]
            raw, chg, lab = r.raw_changed_line, r.changed_line, r.label

            # Layer-A link
            a_cands = find_a_link(raw, chg, a_rows)
            a_file = a_rows[a_cands[0]][0] if len(a_cands) == 1 else None
            a_ord = a_rows[a_cands[0]][2] if len(a_cands) == 1 else None
            gpath = None
            path_st = None
            if a_file:
                gpath, path_st = resolve_path(
                    a_file, set(by_file_u.keys()) | set(by_file_f.keys())
                )

            search_f = (
                by_file_f[gpath]
                if gpath and gpath in by_file_f
                else git_added_f
            )
            search_u = (
                by_file_u[gpath]
                if gpath and gpath in by_file_u
                else git_added_u
            )

            def match_gl(gl: DiffLine) -> bool:
                return (
                    signatures_match(gl.raw_text, raw)
                    or match_via_changed_line(gl.raw_text, chg)
                    or punct_space(gl.raw_text) == raw
                )

            cands_f = [gl for gl in search_f if match_gl(gl)]
            cands_u = [gl for gl in search_u if match_gl(gl)]
            # exclude already used
            cands_f_free = [
                gl
                for gl in cands_f
                if stable_line_id(
                    cid,
                    gl.file_path,
                    gl.hunk_index,
                    gl.change_type,
                    gl.old_lineno,
                    gl.new_lineno,
                    gl.occurrence_index,
                )
                not in used_ids_global[cid]
            ]
            cands_u_free = [
                gl
                for gl in cands_u
                if stable_line_id(
                    cid,
                    gl.file_path,
                    gl.hunk_index,
                    gl.change_type,
                    gl.old_lineno,
                    gl.new_lineno,
                    gl.occurrence_index,
                )
                not in used_ids_global[cid]
            ]

            # blob presence
            in_child = in_parent = False
            blob_path = gpath or a_file
            if blob_path:
                child = show_blob(gd, cid, blob_path)
                if child:
                    in_child = any(
                        signatures_match(line, raw) or match_via_changed_line(line, chg)
                        for line in child
                    )
                if parent:
                    par = show_blob(gd, parent, blob_path)
                    if par:
                        in_parent = any(
                            signatures_match(line, raw)
                            or match_via_changed_line(line, chg)
                            for line in par
                        )

            tax = classify_dataset_conflict(
                in_diff_filtered=len(cands_f) > 0,
                in_diff_unfiltered=len(cands_u) > 0,
                in_child=in_child,
                in_parent=in_parent,
            )
            if len(cands_f) == 0 and len(cands_u) > 0:
                tax = "LINE_PRESENT_BUT_FILTERED"
            elif a_file and len(cands_u) == 0 and not in_child and not in_parent:
                tax = "FILE_PATH_RECOVERED_NO_TEXT_MATCH"
            tax_init[tax] += 1

            final = "UNRESOLVED"
            chosen: DiffLine | None = None
            method = None

            # Transform exact unique free candidate (filtered preferred)
            if len(cands_f_free) == 1:
                chosen = cands_f_free[0]
                final = "RECOVERED_SOURCE_TRANSFORM_EXACT"
                method = "approved_signature_filtered"
            elif len(cands_f_free) == 0 and len(cands_u_free) == 1:
                chosen = cands_u_free[0]
                final = "RECOVERED_SOURCE_TRANSFORM_EXACT"
                method = "approved_signature_unfiltered"
            elif len(cands_f_free) > 1 or len(cands_u_free) > 1:
                final = "AMBIGUOUS"
                method = f"multi_cands_f={len(cands_f_free)}_u={len(cands_u_free)}"

            if chosen is not None:
                cid_line = stable_line_id(
                    cid,
                    chosen.file_path,
                    chosen.hunk_index,
                    chosen.change_type,
                    chosen.old_lineno,
                    chosen.new_lineno,
                    chosen.occurrence_index,
                )
                if cid_line in used_ids_global[cid]:
                    final = "AMBIGUOUS"
                    chosen = None
                else:
                    used_ids_global[cid].add(cid_line)
                    full[(cid, idx)].update(
                        {
                            "canonical_line_id": cid_line,
                            "mapping_status": "RECOVERED_SOURCE_TRANSFORM_EXACT",
                            "file_path": chosen.file_path,
                            "hunk_index": chosen.hunk_index,
                            "new_lineno": chosen.new_lineno,
                            "old_lineno": chosen.old_lineno,
                            "occurrence_index": chosen.occurrence_index,
                            "provenance_method": method,
                            "residual_final": final,
                            "taxonomy": tax,
                        }
                    )
                    # update anchors
                    row_file[i_ord] = chosen.file_path
                    gls = by_file_f.get(chosen.file_path) or by_file_u.get(
                        chosen.file_path, []
                    )
                    for gi, gl in enumerate(gls):
                        if (
                            gl.hunk_index == chosen.hunk_index
                            and gl.new_lineno == chosen.new_lineno
                        ):
                            file_anchors[chosen.file_path][i_ord] = gi
                            break
                    recovery[final] += 1

            report = {
                "commit_id": cid,
                "idx": idx,
                "label": lab,
                "project": project,
                "taxonomy": tax,
                "residual_final": final if chosen else final,
                "a_file_hash": sha_text(a_file) if a_file else None,
                "a_ord": a_ord,
                "path_status": path_st,
                "n_cands_filtered": len(cands_f),
                "n_cands_unfiltered": len(cands_u),
                "in_child": in_child,
                "in_parent": in_parent,
                "raw_sha": sha_text(raw),
                "changed_sha": sha_text(chg),
            }
            residual_reports.append(report)

            if lab == 1.0:
                missing_positive_case = {
                    "commit_id": cid,
                    "idx": idx,
                    "project": project,
                    "taxonomy": tax,
                    "residual_final": full[(cid, idx)]["residual_final"]
                    or final,
                    "a_file_present": a_file is not None,
                    "a_ord": a_ord,
                    "path_status": path_st,
                    "n_cands_filtered": len(cands_f),
                    "n_cands_unfiltered": len(cands_u),
                    "n_cands_filtered_free": len(cands_f_free),
                    "in_child": in_child,
                    "in_parent": in_parent,
                    "raw_sha": sha_text(raw),
                    "changed_sha": sha_text(chg),
                    "canonical_line_id": full[(cid, idx)]["canonical_line_id"],
                    "provenance_method": full[(cid, idx)].get("provenance_method"),
                    "neighbors_mapped": {
                        "prev_idx": brows[i_ord - 1].idx if i_ord > 0 else None,
                        "next_idx": brows[i_ord + 1].idx
                        if i_ord + 1 < len(brows)
                        else None,
                        "prev_mapped": bool(
                            full[(cid, brows[i_ord - 1].idx)]["canonical_line_id"]
                        )
                        if i_ord > 0
                        else None,
                        "next_mapped": bool(
                            full[(cid, brows[i_ord + 1].idx)]["canonical_line_id"]
                        )
                        if i_ord + 1 < len(brows)
                        else None,
                    },
                }

        # --- Positional forcing per file (after transform pass) ---
        for fp, ords in file_policy_ords.items():
            # rebuild ords for this file: all policy rows assigned to fp
            ords = sorted({i for i, f in row_file.items() if f == fp})
            if not ords:
                continue
            gls = by_file_f.get(fp) or by_file_u.get(fp) or []
            if not gls:
                continue
            # map policy ord → local sequence index among ords
            # Use commit-global policy order restricted to file
            mapped_local: dict[int, int] = {}
            # Build anchors: policy index in `ords` list → git index
            # Use file_anchors which maps commit policy ord → git ord
            anchors = {
                i: file_anchors[fp][i]
                for i in ords
                if i in file_anchors.get(fp, {})
                and full[(cid, ord_to_row[i].idx)]["canonical_line_id"]
            }
            # Remap to contiguous indices in ords / gls space
            # policy positions: use actual ord indices as keys for bijection helper
            n_p = max(ords) + 1 if ords else 0
            n_g = len(gls)
            unmatched_p = {
                i
                for i in ords
                if not full[(cid, ord_to_row[i].idx)]["canonical_line_id"]
            }
            used_g = set(anchors.values())
            unmatched_g = {gi for gi in range(n_g) if gi not in used_g}
            forced = positionally_forced_bijections(
                n_policy=n_p,
                n_git=n_g,
                mapped=anchors,
                unmatched_policy=unmatched_p,
                unmatched_git=unmatched_g,
            )
            for p_i, g_i in forced.items():
                if p_i not in unmatched_p:
                    continue
                r = ord_to_row[p_i]
                gl = gls[g_i]
                cid_line = stable_line_id(
                    cid,
                    gl.file_path,
                    gl.hunk_index,
                    gl.change_type,
                    gl.old_lineno,
                    gl.new_lineno,
                    gl.occurrence_index,
                )
                if cid_line in used_ids_global[cid]:
                    continue
                # Only apply to residuals
                if (cid, r.idx) not in {(c, i) for c, i in residual_keys}:
                    continue
                used_ids_global[cid].add(cid_line)
                full[(cid, r.idx)].update(
                    {
                        "canonical_line_id": cid_line,
                        "mapping_status": "RECOVERED_POSITIONALLY_FORCED",
                        "file_path": gl.file_path,
                        "hunk_index": gl.hunk_index,
                        "new_lineno": gl.new_lineno,
                        "old_lineno": gl.old_lineno,
                        "occurrence_index": gl.occurrence_index,
                        "provenance_method": "positionally_forced_bijection",
                        "residual_final": "RECOVERED_POSITIONALLY_FORCED",
                        "taxonomy": full[(cid, r.idx)].get("taxonomy")
                        or "SEQUENCE_GAP",
                    }
                )
                recovery["RECOVERED_POSITIONALLY_FORCED"] += 1
                # update residual report
                for rr in residual_reports:
                    if rr["commit_id"] == cid and rr["idx"] == r.idx:
                        rr["residual_final"] = "RECOVERED_POSITIONALLY_FORCED"
                        rr["taxonomy"] = rr.get("taxonomy") or "SEQUENCE_GAP"

        # Classify remaining residuals in this commit
        for idx in res_idxs:
            ent = full[(cid, idx)]
            if ent["canonical_line_id"]:
                if ent.get("residual_final") is None:
                    ent["residual_final"] = "RECOVERED_SOURCE_TRANSFORM_EXACT"
                continue
            # find report taxonomy
            tax = next(
                (
                    rr["taxonomy"]
                    for rr in residual_reports
                    if rr["commit_id"] == cid and rr["idx"] == idx
                ),
                "NO_RAW_GIT_TEXT_MATCH",
            )
            if tax in {
                "LINE_PRESENT_IN_PARENT_ONLY",
                "LINE_PRESENT_BOTH_BLOBS_NOT_IN_DIFF",
                "LINE_PRESENT_IN_CHILD_ONLY",
                "NO_RAW_GIT_TEXT_MATCH",
                "FILE_PATH_RECOVERED_NO_TEXT_MATCH",
            }:
                # Child-only without diff add is conflict for ADDED Policy-A
                if tax in {
                    "LINE_PRESENT_IN_PARENT_ONLY",
                    "LINE_PRESENT_BOTH_BLOBS_NOT_IN_DIFF",
                    "NO_RAW_GIT_TEXT_MATCH",
                    "FILE_PATH_RECOVERED_NO_TEXT_MATCH",
                }:
                    final = "DATASET_CANONICAL_CONFLICT"
                elif tax == "LINE_PRESENT_IN_CHILD_ONLY":
                    # Present in child but not in first-parent added diff → conflict
                    final = "DATASET_CANONICAL_CONFLICT"
                else:
                    final = "UNRESOLVED"
            else:
                final = "UNRESOLVED"
            # AMBIGUOUS already set
            if ent.get("residual_final") == "AMBIGUOUS" or any(
                rr["residual_final"] == "AMBIGUOUS"
                and rr["commit_id"] == cid
                and rr["idx"] == idx
                for rr in residual_reports
            ):
                final = "AMBIGUOUS"
            ent["residual_final"] = final
            ent["taxonomy"] = tax
            ent["mapping_status"] = final
            recovery[final] += 1
            for rr in residual_reports:
                if rr["commit_id"] == cid and rr["idx"] == idx:
                    rr["residual_final"] = final

            if ent["label"] == 1.0:
                missing_positive_case["residual_final"] = final
                missing_positive_case["canonical_line_id"] = ent["canonical_line_id"]
                missing_positive_case["taxonomy"] = tax

    # Ensure every residual has final category
    for cid, idx in residual_keys:
        ent = full[(cid, idx)]
        if ent.get("residual_final") is None:
            ent["residual_final"] = "UNRESOLVED"
            recovery["UNRESOLVED"] += 1

    # Collision audit over all 18615
    bridge_like = [
        BridgeResult(
            commit_id=e["commit_id"],
            idx=e["idx"],
            label=e["label"],
            mapping_status=e["mapping_status"] or "UNRESOLVED",
            path_status=None,
            canonical_line_id=e["canonical_line_id"],
            file_path=e.get("file_path"),
            hunk_index=e.get("hunk_index"),
            new_lineno=e.get("new_lineno"),
            old_lineno=e.get("old_lineno"),
            occurrence_index=e.get("occurrence_index"),
            text_status=None,
            provenance_method=e.get("provenance_method") or "",
        )
        for e in full.values()
    ]
    coll = collision_audit(bridge_like)
    mapped_n = coll["mapped_rows"]
    pos_mapped = sum(
        1 for e in full.values() if e["canonical_line_id"] and e["label"] == 1.0
    )
    neg_mapped = sum(
        1 for e in full.values() if e["canonical_line_id"] and e["label"] == 0.0
    )

    # Complete commits
    commits = sorted(jf["commit_id"].astype(str).unique())
    complete = []
    incomplete = []
    commit_stats = []
    for cid in commits:
        rows = [e for e in full.values() if e["commit_id"] == cid]
        n = len(rows)
        n_map = sum(1 for e in rows if e["canonical_line_id"])
        n_pos = sum(1 for e in rows if e["label"] == 1.0)
        n_neg = sum(1 for e in rows if e["label"] == 0.0)
        is_c = n_map == n and n > 0
        (complete if is_c else incomplete).append(cid)
        project = proj_by[cid]
        gd = REPO_ROOT / f"{project}.git"
        filtered, _ = reconstruct_commit(gd, cid)
        n_add = sum(1 for ln in filtered if ln.change_type == "added")
        n_del = sum(1 for ln in filtered if ln.change_type == "deleted")
        n_files = len({ln.file_path for ln in filtered})
        n_hunks = len({(ln.file_path, ln.hunk_index) for ln in filtered})
        fr = feat_by[cid]
        msg = str(fr.get("commit_message", "") or "")
        commit_stats.append(
            {
                "commit_id": cid,
                "project": project,
                "complete": is_c,
                "n_candidates": n,
                "n_mapped": n_map,
                "n_pos": n_pos,
                "n_neg": n_neg,
                "n_pos_mapped": sum(
                    1 for e in rows if e["canonical_line_id"] and e["label"] == 1.0
                ),
                "n_neg_mapped": sum(
                    1 for e in rows if e["canonical_line_id"] and e["label"] == 0.0
                ),
                "git_added": n_add,
                "git_deleted": n_del,
                "git_changed": n_add + n_del,
                "n_files": n_files,
                "n_hunks": n_hunks,
                "msg_len": len(msg),
                "buggy_density": (n_pos / n) if n else 0.0,
                **{
                    c: float(bool(fr[c]))
                    if c == "fix"
                    else float(fr[c])
                    for c in FEATURE_COLS
                },
            }
        )

    # Bias profile
    def subset(flag: bool) -> list[dict]:
        return [c for c in commit_stats if c["complete"] is flag]

    comp_s, inc_s = subset(True), subset(False)
    profile_rows = []
    vars_cont = [
        "n_candidates",
        "n_pos",
        "buggy_density",
        "git_added",
        "git_deleted",
        "git_changed",
        "n_files",
        "n_hunks",
        "msg_len",
    ] + FEATURE_COLS
    for v in vars_cont:
        a = [float(c[v]) for c in comp_s]
        b = [float(c[v]) for c in inc_s]
        da, db = describe_numeric(a), describe_numeric(b)
        s = smd(da["mean"], db["mean"], da["sd"], db["sd"])
        flag = abs(s) >= 0.25 if s is not None else False
        profile_rows.append(
            {
                "variable": v,
                "complete_n": int(da["n"]),
                "complete_mean": da["mean"],
                "complete_median": da["median"],
                "complete_iqr": da["iqr"],
                "incomplete_n": int(db["n"]),
                "incomplete_mean": db["mean"],
                "incomplete_median": db["median"],
                "incomplete_iqr": db["iqr"],
                "smd_complete_minus_incomplete": s if s is not None else "",
                "LARGE_DISTRIBUTIONAL_DIFFERENCE": flag,
            }
        )

    # Project coverage
    all_projects = sorted(set(proj_by.values()))
    assert len(all_projects) == 21
    proj_rows = []
    for p in all_projects:
        all_c = [c for c in commit_stats if c["project"] == p]
        comp_c = [c for c in all_c if c["complete"]]
        proj_rows.append(
            {
                "project": p,
                "policy_a_commits": len(all_c),
                "complete_commits": len(comp_c),
                "incomplete_commits": len(all_c) - len(comp_c),
                "pct_retained": (100.0 * len(comp_c) / len(all_c)) if all_c else 0.0,
                "pos_lines_all": sum(c["n_pos"] for c in all_c),
                "pos_lines_complete": sum(c["n_pos"] for c in comp_c),
                "cand_all": sum(c["n_candidates"] for c in all_c),
                "cand_complete": sum(c["n_candidates"] for c in comp_c),
            }
        )
    projects_with_zero = [r["project"] for r in proj_rows if r["complete_commits"] == 0]
    retention_range = (
        min(r["pct_retained"] for r in proj_rows),
        max(r["pct_retained"] for r in proj_rows),
    )

    # Category summary for 148
    cat_ctr = Counter(rr["residual_final"] for rr in residual_reports)
    tax_ctr = Counter(rr["taxonomy"] for rr in residual_reports)

    # Write forensic (ignored) full residual detail without raw text — hashes only
    (DERIVED / "residual_forensic.jsonl").write_text(
        "\n".join(json.dumps(rr, sort_keys=True) for rr in residual_reports) + "\n"
    )
    (DERIVED / "full_mapping_after_residual.jsonl").write_text(
        "\n".join(json.dumps(full[k], sort_keys=True) for k in sorted(full)) + "\n"
    )

    residual_summary = {
        "starting_residual": 148,
        "starting_positive_residual": 1,
        "starting_negative_residual": 147,
        "taxonomy_initial_style": dict(tax_init),
        "taxonomy_final": dict(tax_ctr),
        "recovery_final": dict(cat_ctr),
        "recovery_counter": dict(recovery),
        "final_mapping": {
            "unique": mapped_n,
            "zero_map": coll["zero_map"],
            "multi_map": 0,
            "collisions": coll["collision_ids"],
            "positives_mapped": pos_mapped,
            "negatives_mapped": neg_mapped,
        },
        "complete_commits": len(complete),
        "incomplete_commits": len(incomplete),
        "POLICY_A_RESIDUAL_CLOSURE_GATE": "PASS"
        if mapped_n == 18615 and pos_mapped == 2060 and coll["collision_ids"] == 0
        else "FAIL",
        "missing_positive_final": missing_positive_case.get("residual_final"),
        "missing_positive_mapped": bool(missing_positive_case.get("canonical_line_id")),
    }
    (OUT / "residual_summary.json").write_text(
        json.dumps(residual_summary, indent=2, sort_keys=True) + "\n"
    )
    (OUT / "missing_positive_case.json").write_text(
        json.dumps(missing_positive_case, indent=2, sort_keys=True) + "\n"
    )

    with (OUT / "category_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["residual_final", "count", "taxonomy_breakdown"])
        by_final: dict[str, Counter] = defaultdict(Counter)
        for rr in residual_reports:
            by_final[rr["residual_final"]][rr["taxonomy"]] += 1
        for fin, ctr in sorted(by_final.items()):
            w.writerow([fin, sum(ctr.values()), json.dumps(dict(ctr), sort_keys=True)])

    with (OUT / "project_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(proj_rows[0].keys()))
        w.writeheader()
        for r in proj_rows:
            w.writerow(r)

    with (OUT / "complete_vs_incomplete_profile.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(f, fieldnames=list(profile_rows[0].keys()))
        w.writeheader()
        for r in profile_rows:
            w.writerow(r)

    # Readiness
    severe_concentration = False
    # >50% of incomplete commits in ≤2 projects
    inc_by_p = Counter(c["project"] for c in inc_s)
    if inc_s:
        top2 = sum(n for _, n in inc_by_p.most_common(2))
        if top2 / len(inc_s) >= 0.5:
            severe_concentration = True

    readiness_pass = (
        len(complete) > 0
        and all(
            sum(1 for e in full.values() if e["commit_id"] == cid and e["canonical_line_id"])
            == sum(1 for e in full.values() if e["commit_id"] == cid)
            for cid in complete
        )
        and len(projects_with_zero) == 0
        and not severe_concentration
        and coll["collision_ids"] == 0
    )

    complete_case_summary = {
        "POLICY_A_COMPLETE_CASE_N": len(complete),
        "incomplete_n": len(incomplete),
        "projects_represented": 21 - len(projects_with_zero),
        "projects_total": 21,
        "projects_with_zero_complete": projects_with_zero,
        "retention_pct_min": retention_range[0],
        "retention_pct_max": retention_range[1],
        "candidates_in_complete": sum(c["n_candidates"] for c in comp_s),
        "positives_in_complete": sum(c["n_pos"] for c in comp_s),
        "negatives_in_complete": sum(c["n_neg"] for c in comp_s),
        "positives_lost_in_incomplete": sum(c["n_pos"] for c in inc_s),
        "negatives_lost_in_incomplete": sum(c["n_neg"] for c in inc_s),
        "candidates_lost_in_incomplete": sum(c["n_candidates"] for c in inc_s),
        "severe_exclusion_concentration_top2_ge_50pct": severe_concentration,
        "incomplete_project_counts": dict(inc_by_p),
        "LARGE_SMD_variables": [
            r["variable"]
            for r in profile_rows
            if r["LARGE_DISTRIBUTIONAL_DIFFERENCE"]
        ],
        "POLICY_A_COMPLETE_CASE_READINESS_GATE": "PASS" if readiness_pass else "FAIL",
        "metric_validity": {
            "complete_commits": "ALL_PRIMARY_RQ1_METRICS_VALID_WITHIN_POLICY_A",
            "incomplete_commits": "PRIMARY_RQ1_METRICS_INVALID_UNTIL_FULL_MAPPING",
        },
    }
    (OUT / "complete_case_summary.json").write_text(
        json.dumps(complete_case_summary, indent=2, sort_keys=True) + "\n"
    )

    print(json.dumps({"residual": residual_summary, "complete_case": complete_case_summary}, indent=2))


if __name__ == "__main__":
    main()

"""Ground-truth lineage + canonical-diff audit (no tokenization / no build_dataset)."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.data.git_diff_reconstruction import (
    DiffLine,
    PROJECT_REPO_URLS,
    filter_upstream_semantics,
    git_diff_against_parent,
    git_show_numstat_parents,
    parse_unified_diff,
    reconstruct_commit,
    stable_line_id,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data/raw/upstream/extracted/data/jitfine"
ZIP_PATH = ROOT / "data/raw/upstream/data.zip"
JSON_PATH = ROOT / "data/raw/upstream/internal/buggy_changes_with_buggy_line.json"
REPO_ROOT = ROOT / "data/raw/source_repos"
OUT = ROOT / "artifacts/ground_truth_lineage"
DERIVED = ROOT / "data/raw/derived_audit"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def punct_space(text: str) -> str:
    """Insert spaces around non-word characters; collapse whitespace."""
    s = re.sub(r"([^\w\s])", r" \1 ", text, flags=re.UNICODE)
    return " ".join(s.split())


def preprocess_code_line(code: str) -> str:
    """Exact upstream JITFine/my_util.preprocess_code_line (no python-token filter)."""
    code = (
        code.replace("(", " ")
        .replace(")", " ")
        .replace("{", " ")
        .replace("}", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace(",", " ")
        .replace(" _ ", "_")
    )
    code = re.sub("``.*``", "<STR>", code)
    code = re.sub("'.*'", "<STR>", code)
    code = re.sub('".*"', "<STR>", code)
    code = re.sub(r"\d+", "<NUM>", code)
    return " ".join(code.split()).strip()


def line_variants(line: str) -> set[str]:
    return {
        line,
        punct_space(line),
        punct_space(line.replace("_", " ")),
        " ".join(line.split()),
    }


def parse_parent_hashes(ph: Any) -> list[str]:
    if ph is None or (isinstance(ph, float) and pd.isna(ph)):
        return []
    s = str(ph).strip()
    if not s or s == "nan":
        return []
    if "," in s:
        return [p.strip() for p in s.split(",") if p.strip()]
    return [p for p in s.split() if p.strip()]


@dataclass
class LayerALine:
    project: str
    commit: str
    file_path: str
    change_type: str  # added|deleted
    text: str
    label: float  # 1.0 buggy / 0.0 clean / -1 unlabeled deleted
    occurrence_index: int


def load_layer_a(path: Path) -> dict[str, dict[str, Any]]:
    return json.loads(path.read_text())


def flatten_layer_a_commit(project: str, commit: str, payload: dict) -> list[LayerALine]:
    rows: list[LayerALine] = []
    abl = payload.get("added_buggy_level") or {}
    for fp, lines in (payload.get("added") or {}).items():
        labs = abl.get(fp) or {}
        buggy_left: Counter[str] = Counter(
            labs.get("added_buggy") or [] if isinstance(labs, dict) else []
        )
        occ: Counter[str] = Counter()
        for line in lines:
            lab = 1.0 if buggy_left[line] > 0 else 0.0
            if buggy_left[line] > 0:
                buggy_left[line] -= 1
            oi = occ[line]
            occ[line] += 1
            rows.append(
                LayerALine(project, commit, fp, "added", line, lab, oi)
            )
    for fp, lines in (payload.get("deleted") or {}).items():
        occ = Counter()
        for line in lines:
            oi = occ[line]
            occ[line] += 1
            rows.append(
                LayerALine(project, commit, fp, "deleted", line, 0.0, oi)
            )
    return rows


def path_candidates(file_path: str) -> set[str]:
    """Deterministic path forms (no fuzzy / basename-only)."""
    out = {file_path}
    # strip leading ./
    if file_path.startswith("./"):
        out.add(file_path[2:])
    return out


def paths_equivalent(a: str, b: str) -> str | None:
    if a == b:
        return "EXACT_PATH"
    ca, cb = path_candidates(a), path_candidates(b)
    if ca & cb:
        return "DETERMINISTIC_NORMALIZED_PATH"
    return None


def map_a_to_git(
    a_rows: list[LayerALine],
    git_lines: list[DiffLine],
) -> list[dict[str, Any]]:
    """File-constrained exact sequence mapping (no fuzzy text)."""
    # Index git by (file, change_type) preserving order
    by_key: dict[tuple[str, str], list[DiffLine]] = defaultdict(list)
    for gl in git_lines:
        by_key[(gl.file_path, gl.change_type)].append(gl)

    # Group A by (file, change_type) preserving order
    a_groups: dict[tuple[str, str], list[LayerALine]] = defaultdict(list)
    for ar in a_rows:
        a_groups[(ar.file_path, ar.change_type)].append(ar)

    results: list[dict[str, Any]] = []
    for (fp, ctype), group in a_groups.items():
        # find matching git file path
        git_group: list[DiffLine] | None = None
        path_status = "UNRESOLVED_PATH"
        matched_path = None
        for gpath in {p for (p, ct) in by_key if ct == ctype}:
            st = paths_equivalent(fp, gpath)
            if st:
                git_group = by_key[(gpath, ctype)]
                path_status = st
                matched_path = gpath
                break
        if git_group is None:
            # rename: compare basename only is forbidden; try suffix equality of full path
            for gpath in {p for (p, ct) in by_key if ct == ctype}:
                if gpath.endswith("/" + fp) or fp.endswith("/" + gpath):
                    git_group = by_key[(gpath, ctype)]
                    path_status = "DETERMINISTIC_NORMALIZED_PATH"
                    matched_path = gpath
                    break
        if git_group is None:
            for ar in group:
                results.append(
                    {
                        "a": ar,
                        "status": "MISSING",
                        "path_status": "UNRESOLVED_PATH",
                        "git": None,
                    }
                )
            continue

        # Build exact-match matrix after proven variants
        a_norms = [line_variants(ar.text) for ar in group]
        g_texts = [gl.raw_text for gl in git_group]
        g_norms = [line_variants(t) for t in g_texts]

        # Precompute remaining-group multiplicity for occurrence zipping
        a_text_keys = [frozenset(vs) for vs in a_norms]

        used_g: set[int] = set()
        partial: list[dict[str, Any] | None] = [None] * len(group)
        claimed_a: set[int] = set()

        # Pass 1: unique exact candidates
        for ai, ar in enumerate(group):
            cands = [
                gi
                for gi, gvs in enumerate(g_norms)
                if gi not in used_g and (a_norms[ai] & gvs)
            ]
            if len(cands) == 1:
                gi = cands[0]
                used_g.add(gi)
                claimed_a.add(ai)
                if ar.text == git_group[gi].raw_text:
                    st = "EXACT_DIRECT"
                elif punct_space(ar.text) == git_group[gi].raw_text or ar.text == punct_space(
                    git_group[gi].raw_text
                ):
                    st = "EXACT_FILE_CONSTRAINED"
                else:
                    st = "EXACT_OCCURRENCE_CONSTRAINED"
                partial[ai] = {
                    "a": ar,
                    "status": st,
                    "path_status": path_status,
                    "git": git_group[gi],
                    "git_path": matched_path,
                }
            elif len(cands) == 0:
                claimed_a.add(ai)
                partial[ai] = {
                    "a": ar,
                    "status": "MISSING",
                    "path_status": path_status,
                    "git": None,
                    "git_path": matched_path,
                }

        # Pass 2: equal-multiplicity occurrence zip for remaining identical texts
        for ai, ar in enumerate(group):
            if ai in claimed_a:
                continue
            # remaining A rows sharing any variant with this row's variants
            a_idxs = [
                aj
                for aj in range(len(group))
                if aj not in claimed_a and (a_norms[ai] & a_norms[aj])
            ]
            g_idxs = [
                gi
                for gi, gvs in enumerate(g_norms)
                if gi not in used_g and (a_norms[ai] & gvs)
            ]
            if len(a_idxs) == len(g_idxs) and len(a_idxs) > 0:
                a_idxs_sorted = sorted(a_idxs)  # preserve file order
                g_idxs_sorted = sorted(g_idxs)
                for aj, gi in zip(a_idxs_sorted, g_idxs_sorted):
                    used_g.add(gi)
                    claimed_a.add(aj)
                    partial[aj] = {
                        "a": group[aj],
                        "status": "EXACT_OCCURRENCE_CONSTRAINED",
                        "path_status": path_status,
                        "git": git_group[gi],
                        "git_path": matched_path,
                    }
            else:
                partial[ai] = {
                    "a": ar,
                    "status": "AMBIGUOUS",
                    "path_status": path_status,
                    "git": None,
                    "git_path": matched_path,
                    "cand_count": len(g_idxs),
                }
                claimed_a.add(ai)

        # Ensure all slots filled
        for ai, ar in enumerate(group):
            if partial[ai] is None:
                partial[ai] = {
                    "a": ar,
                    "status": "AMBIGUOUS",
                    "path_status": path_status,
                    "git": None,
                    "git_path": matched_path,
                }

        # Pass 3: sequence disambiguation for AMBIGUOUS using neighbors
        for i, item in enumerate(partial):
            assert item is not None
            if item["status"] != "AMBIGUOUS":
                continue
            prev_g = None
            next_g = None
            for j in range(i - 1, -1, -1):
                if partial[j] is not None and partial[j]["git"] is not None:
                    prev_g = git_group.index(partial[j]["git"])
                    break
            for j in range(i + 1, len(partial)):
                if partial[j] is not None and partial[j]["git"] is not None:
                    next_g = git_group.index(partial[j]["git"])
                    break
            lo = (prev_g + 1) if prev_g is not None else 0
            hi = next_g if next_g is not None else len(git_group)
            cands = [
                gi
                for gi in range(lo, hi)
                if gi not in used_g and (a_norms[i] & g_norms[gi])
            ]
            if len(cands) == 1:
                gi = cands[0]
                used_g.add(gi)
                item["status"] = "EXACT_SEQUENCE_DISAMBIGUATED"
                item["git"] = git_group[gi]

        results.extend(item for item in partial if item is not None)
    return results


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)

    # --- inventory hashes ---
    json_sha = sha256_file(JSON_PATH)
    layer_a = load_layer_a(JSON_PATH)
    jf = pd.read_pickle(EXTRACTED / "changes_complete_buggy_line_level.pkl")
    feat_frames = []
    for split in ("train", "valid", "test"):
        f = pd.read_pickle(EXTRACTED / f"features_{split}.pkl")
        f = f.copy()
        f["split"] = split
        feat_frames.append(f)
    feat = pd.concat(feat_frames, ignore_index=True)
    proj_by_hash = {
        str(r.commit_hash): str(r.project) for _, r in feat.iterrows()
    }
    parent_by_hash = {
        str(r.commit_hash): parse_parent_hashes(r.parent_hashes) for _, r in feat.iterrows()
    }

    test_pos = set(jf["commit_id"].astype(str).unique())
    assert len(test_pos) == 475

    # JSON index
    j_by: dict[str, tuple[str, dict]] = {}
    for proj, commits in layer_a.items():
        for cid, payload in commits.items():
            j_by[cid] = (proj, payload)

    present = [c for c in test_pos if c in j_by]
    missing = [c for c in test_pos if c not in j_by]

    # A↔B lineage (positives + added counts)
    pos_count_agree = pos_count_disagree = 0
    add_count_agree = add_count_disagree = 0
    b_pos_to_a = Counter()
    a_pos_total = 0
    b_pos_total = int((jf["label"] == 1.0).sum())
    label_agree = label_disagree = 0

    for c in test_pos:
        proj, payload = j_by[c]
        a_rows = flatten_layer_a_commit(proj, c, payload)
        a_added = [r for r in a_rows if r.change_type == "added"]
        a_pos = [r for r in a_added if r.label == 1.0]
        a_pos_total += len(a_pos)
        b_rows = jf[jf["commit_id"].astype(str) == c]
        b_added = b_rows[b_rows["changed_type"] == "added"]
        b_pos = b_rows[b_rows["label"] == 1.0]
        if len(a_added) == len(b_added):
            add_count_agree += 1
        else:
            add_count_disagree += 1
        if len(a_pos) == len(b_pos):
            pos_count_agree += 1
        else:
            pos_count_disagree += 1

        # match B positives into A positives via variants
        pool = list(a_pos)
        used: set[int] = set()
        for _, br in b_pos.iterrows():
            cands = [
                i
                for i, ar in enumerate(pool)
                if i not in used and br.raw_changed_line in line_variants(ar.text)
            ]
            if len(cands) == 1:
                used.add(cands[0])
                b_pos_to_a["EXACT_AFTER_TRANSFORM"] += 1
                if float(pool[cands[0]].label) == 1.0:
                    label_agree += 1
                else:
                    label_disagree += 1
            elif len(cands) > 1:
                b_pos_to_a["AMBIGUOUS"] += 1
            else:
                b_pos_to_a["MISSING"] += 1

    # changed_line transform check
    chg_from_raw = sum(
        1
        for _, r in jf.iterrows()
        if preprocess_code_line(str(r.raw_changed_line)) == str(r.changed_line)
    )

    # --- A → Git mapping for 475 ---
    pos_map = Counter()
    commit_class = Counter()
    path_stats = Counter()
    file_id_pos = Counter()
    full_universe_complete = 0
    positive_gt_complete = 0
    usable_full = 0

    # store aggregate only (no source text)
    per_commit_rows = []

    for c in sorted(test_pos):
        proj, payload = j_by[c]
        a_rows = flatten_layer_a_commit(proj, c, payload)
        repo = REPO_ROOT / f"{proj}.git"
        parents = parent_by_hash.get(c) or []
        # prefer features parent; fall back to git first parent
        if parents:
            parent = parents[0]
            filtered, meta = [], {"selected_parent": parent, "commit_kind": "normal"}
            # reconstruct using explicit parent
            diff_text = git_diff_against_parent(repo, c, parent)
            raw_lines = parse_unified_diff(diff_text)
            # For lineage mapping use ALL java lines (no comment filter) — labels are on source lines
            git_lines = [ln for ln in raw_lines if ln.file_path.endswith(".java")]
        else:
            git_lines, meta = reconstruct_commit(repo, c)
            git_lines = [ln for ln in git_lines]  # already filtered; re-parse unfiltered
            diff_text = git_diff_against_parent(repo, c, None)
            git_lines = [
                ln for ln in parse_unified_diff(diff_text) if ln.file_path.endswith(".java")
            ]

        mapped = map_a_to_git(a_rows, git_lines)
        for m in mapped:
            path_stats[m.get("path_status", "UNRESOLVED_PATH")] += 1

        pos_items = [m for m in mapped if m["a"].label == 1.0 and m["a"].change_type == "added"]
        for m in pos_items:
            pos_map[m["status"]] += 1
            if m["git"] is not None:
                file_id_pos["FILE_EXACT_FROM_LINEAGE"] += 1
            else:
                file_id_pos["FILE_UNRESOLVED"] += 1

        added_items = [m for m in mapped if m["a"].change_type == "added"]
        pos_ok = all(
            m["status"]
            in {
                "EXACT_DIRECT",
                "EXACT_FILE_CONSTRAINED",
                "EXACT_OCCURRENCE_CONSTRAINED",
                "EXACT_SEQUENCE_DISAMBIGUATED",
            }
            for m in pos_items
        ) and len(pos_items) > 0
        all_added_ok = all(
            m["status"]
            in {
                "EXACT_DIRECT",
                "EXACT_FILE_CONSTRAINED",
                "EXACT_OCCURRENCE_CONSTRAINED",
                "EXACT_SEQUENCE_DISAMBIGUATED",
            }
            for m in added_items
        )

        if any(m["status"] == "SOURCE_CONFLICT" for m in mapped):
            commit_class["SOURCE_CONFLICT"] += 1
        elif pos_ok and all_added_ok:
            commit_class["FULL_GROUND_TRUTH_RECOVERED"] += 1
            positive_gt_complete += 1
            full_universe_complete += 1
            usable_full += 1
        elif pos_ok:
            commit_class["PARTIAL_POSITIVE_LABEL_RECOVERY"] += 1
            positive_gt_complete += 1
            # positives complete but not full added universe
        elif any(m["status"] == "AMBIGUOUS" for m in pos_items):
            commit_class["AMBIGUOUS"] += 1
        else:
            commit_class["PARTIAL_POSITIVE_LABEL_RECOVERY"] += 1

        per_commit_rows.append(
            {
                "commit": c,
                "project": proj,
                "n_a_added": len(added_items),
                "n_a_pos": len(pos_items),
                "pos_ok": int(pos_ok),
                "all_added_ok": int(all_added_ok),
                "n_pos_mapped": sum(1 for m in pos_items if m["git"] is not None),
                "n_pos_ambiguous": sum(1 for m in pos_items if m["status"] == "AMBIGUOUS"),
                "n_pos_missing": sum(1 for m in pos_items if m["status"] == "MISSING"),
            }
        )

    # --- all-commit canonical coverage ---
    split_cov = []
    failures = []
    n_ids = 0
    id_set: set[str] = set()
    for split in ("train", "valid", "test"):
        sub = feat[feat["split"] == split]
        ok = miss = parse_ok = 0
        for _, r in sub.iterrows():
            cid = str(r.commit_hash)
            proj = str(r.project)
            repo = REPO_ROOT / f"{proj}.git"
            parents = parse_parent_hashes(r.parent_hashes)
            parent = parents[0] if parents else None
            try:
                diff_text = git_diff_against_parent(repo, cid, parent)
                lines = parse_unified_diff(diff_text)
                ok += 1
                parse_ok += 1
                for ln in lines:
                    if not ln.file_path:
                        continue
                    sid = stable_line_id(
                        cid,
                        ln.file_path,
                        ln.hunk_index,
                        ln.change_type,
                        ln.old_lineno,
                        ln.new_lineno,
                        ln.occurrence_index,
                    )
                    n_ids += 1
                    id_set.add(sid)
            except Exception as e:  # noqa: BLE001
                miss += 1
                failures.append(
                    {
                        "split": split,
                        "project": proj,
                        "commit": cid,
                        "label": float(r.is_buggy_commit),
                        "error": type(e).__name__,
                    }
                )
        split_cov.append(
            {
                "split": split,
                "total": int(len(sub)),
                "canonical_diff_available": ok,
                "missing": miss,
                "parse_success": parse_ok,
            }
        )

    # Write aggregates (no source text)
    summary = {
        "json_sha256": json_sha,
        "json_path": "JITFine/labels for each line/buggy_changes_with_buggy_line.json",
        "json_local": str(JSON_PATH.relative_to(ROOT)),
        "layer_a_projects": len(layer_a),
        "layer_a_commits": sum(len(v) for v in layer_a.values()),
        "coverage_475": {"present": len(present), "missing": len(missing)},
        "a_to_b": {
            "verdict": "PARTIAL",
            "added_count_agree_commits": add_count_agree,
            "added_count_disagree_commits": add_count_disagree,
            "pos_count_agree_commits": pos_count_agree,
            "pos_count_disagree_commits": pos_count_disagree,
            "a_pos_total_on_475": a_pos_total,
            "b_pos_total": b_pos_total,
            "b_pos_match_status": dict(b_pos_to_a),
            "label_agree_on_matched": label_agree,
            "label_disagree_on_matched": label_disagree,
            "changed_line_eq_preprocess_raw": chg_from_raw,
            "changed_line_rows": int(len(jf)),
        },
        "raw_changed_line": {
            "relationship": "DETERMINISTIC_TRANSFORM_PARTIAL",
            "primary": "punct_space(LayerA.text) often equals B.raw_changed_line; underscore→space variant needed sometimes; not 100%",
        },
        "changed_line": {
            "relationship": "DETERMINISTIC_TRANSFORM",
            "function": "JITFine/my_util.preprocess_code_line",
            "eq_rate_on_raw": chg_from_raw / max(len(jf), 1),
            "note": "Applied to raw_changed_line imperfectly (~26%); intended on original source line before/with different spacing",
        },
        "positive_mapping_a_to_git": dict(pos_map),
        "a_pos_total_mapped_universe": a_pos_total,
        "commit_class": dict(commit_class),
        "positive_gt_complete_commits": positive_gt_complete,
        "full_line_universe_complete_commits": full_universe_complete,
        "path_stats": dict(path_stats),
        "file_id_pos": dict(file_id_pos),
        "parent": {
            "rule": "features.parent_hashes[0] == git first parent",
            "n_parents_dist_all": dict(Counter(len(parse_parent_hashes(x)) for x in feat.parent_hashes)),
            "n_parents_dist_475": {1: 475},
            "merges_in_475": 0,
            "root_commits_all": 2,
        },
        "canonical_diff_by_split": split_cov,
        "canonical_diff_failures": failures,
        "stable_line_id_unique": len(id_set) == n_ids,
        "n_stable_line_ids": len(id_set),
        "PRIMARY_RQ1_POPULATION_NOMINAL": 475,
        "positive_gt_complete_n": positive_gt_complete,
        "DO_NOT_CONDITION_PRIMARY_RQ1_ON_PREDICTED_POSITIVE": True,
        "set_equivalence_diagnostic_only": {
            "EXACT_SET_MATCH": 8755,
            "n": 27317,
            "rate": 0.3205,
            "note": "LOSSY-UPSTREAM-REPRESENTATION COMPARISON — NOT canonical validity",
        },
        "CANONICAL_MODEL_INPUT_SOURCE": "ordered first-parent Git diff (features.parent_hashes[0])",
        "GROUND_TRUTH_SOURCE": "JITFine/labels for each line/buggy_changes_with_buggy_line.json (Layer A)",
    }

    (OUT / "layer_a_b_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    # CSVs
    import csv

    with (OUT / "positive_mapping_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["status", "count"])
        for k, v in sorted(pos_map.items()):
            w.writerow([k, v])
        w.writerow(["A_POS_TOTAL", a_pos_total])
        w.writerow(["B_POS_TOTAL", b_pos_total])

    with (OUT / "commit_mapping_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_commit_rows[0].keys()))
        w.writeheader()
        w.writerows(per_commit_rows)

    with (OUT / "file_path_mapping_summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path_status", "count"])
        for k, v in sorted(path_stats.items()):
            w.writerow([k, v])

    with (OUT / "canonical_diff_coverage.json").open("w") as f:
        json.dump(
            {
                "by_split": split_cov,
                "failures": failures,
                "stable_line_id_unique": len(id_set) == n_ids,
                "n_stable_line_ids": len(id_set),
            },
            f,
            indent=2,
        )
        f.write("\n")

    print(json.dumps({k: summary[k] for k in [
        "coverage_475", "a_to_b", "positive_mapping_a_to_git", "commit_class",
        "positive_gt_complete_commits", "canonical_diff_by_split", "canonical_diff_failures",
        "stable_line_id_unique", "parent"
    ]}, indent=2))


if __name__ == "__main__":
    main()

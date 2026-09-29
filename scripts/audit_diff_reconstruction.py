#!/usr/bin/env python3
"""Audit exact Git diff reconstruction vs frozen JIT-Fine sets + 475 line-label mapping."""

from __future__ import annotations

import csv
import json
import pickle
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.git_diff_reconstruction import (  # noqa: E402
    PROJECT_REPO_URLS,
    filter_upstream_semantics,
    map_label_rows_by_unique_norm,
    parse_unified_diff,
    reconstruct_commit,
    set_equivalence,
    sets_from_filtered,
    stable_line_id,
)

EXTRACTED = ROOT / "data/raw/upstream/extracted/data/jitfine"
REPOS = ROOT / "data/raw/source_repos"
ART = ROOT / "artifacts/diff_reconstruction"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_mirror(project: str, url: str) -> Path:
    REPOS.mkdir(parents=True, exist_ok=True)
    dest = REPOS / f"{project}.git"
    if (dest / "HEAD").exists() or (dest / "objects").exists():
        return dest
    print(f"cloning {project} ...", flush=True)
    subprocess.check_call(
        ["git", "clone", "--mirror", url, str(dest)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return dest


def commit_exists(git_dir: Path, commit: str) -> bool:
    try:
        subprocess.check_call(
            ["git", "--git-dir", str(git_dir), "cat-file", "-e", f"{commit}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def load_split(split: str):
    ids, labels, msgs, codes = pickle.load(open(EXTRACTED / f"changes_{split}.pkl", "rb"))
    feats = pickle.load(open(EXTRACTED / f"features_{split}.pkl", "rb"))
    # feats is DataFrame
    return [str(x) for x in ids], [float(x) for x in labels], codes, feats


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    # Clone all
    repo_status = []
    for project, url in PROJECT_REPO_URLS.items():
        try:
            path = ensure_mirror(project, url)
            head = subprocess.check_output(
                ["git", "--git-dir", str(path), "rev-parse", "HEAD"], text=True
            ).strip()
            repo_status.append(
                {
                    "dataset_project_name": project,
                    "canonical_repository_url": url,
                    "evidence_for_mapping": "Apache project name convention + commit object presence checks; LLTC4J/JIT-Fine Java OSS projects",
                    "repository_host": "github.com/apache",
                    "default_branch": "HEAD",
                    "current_remote_HEAD": head,
                    "mapping_status": "STRONGLY_CORROBORATED",
                    "notes": "Historical commit hashes are scientific objects; HEAD not frozen as input",
                    "local_mirror": str(path),
                    "fetch_timestamp": utc_now(),
                }
            )
        except subprocess.CalledProcessError as e:
            repo_status.append(
                {
                    "dataset_project_name": project,
                    "canonical_repository_url": url,
                    "evidence_for_mapping": "name-based Apache mapping",
                    "repository_host": "github.com/apache",
                    "default_branch": "",
                    "current_remote_HEAD": "",
                    "mapping_status": "UNRESOLVED",
                    "notes": f"clone failed: {e}",
                    "local_mirror": "",
                    "fetch_timestamp": utc_now(),
                }
            )

    # Write project map CSV
    map_path = ROOT / "docs/PROJECT_REPOSITORY_MAP.csv"
    fields = [
        "dataset_project_name",
        "canonical_repository_url",
        "evidence_for_mapping",
        "repository_host",
        "default_branch",
        "current_remote_HEAD",
        "mapping_status",
        "notes",
    ]
    with map_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in repo_status:
            w.writerow({k: r.get(k, "") for k in fields})

    git_dirs = {
        r["dataset_project_name"]: Path(r["local_mirror"])
        for r in repo_status
        if r["mapping_status"] != "UNRESOLVED" and r["local_mirror"]
    }

    # Load all commits with project from features
    split_rows = []
    all_records = []  # per-commit audit
    parent_kinds = Counter()
    eq_counts = Counter()
    mult_commits = 0
    mult_test_pos = 0

    for split in ("train", "valid", "test"):
        ids, labels, codes, feats = load_split(split)
        proj_by_hash = dict(
            zip(feats["commit_hash"].astype(str), feats["project"].astype(str))
        )
        found = missing = unresolved = 0
        for cid, lab, code in zip(ids, labels, codes):
            project = proj_by_hash.get(cid)
            if project not in git_dirs:
                unresolved += 1
                all_records.append(
                    {
                        "split": split,
                        "commit": cid,
                        "project": project,
                        "label": lab,
                        "status": "UNAVAILABLE",
                        "eq": "UNAVAILABLE",
                    }
                )
                continue
            gd = git_dirs[project]
            if not commit_exists(gd, cid):
                missing += 1
                all_records.append(
                    {
                        "split": split,
                        "commit": cid,
                        "project": project,
                        "label": lab,
                        "status": "MISSING_COMMIT",
                        "eq": "UNAVAILABLE",
                    }
                )
                continue
            found += 1
            try:
                filtered, meta = reconstruct_commit(gd, cid, parent_strategy="first_parent")
            except subprocess.CalledProcessError:
                all_records.append(
                    {
                        "split": split,
                        "commit": cid,
                        "project": project,
                        "label": lab,
                        "status": "DIFF_ERROR",
                        "eq": "UNAVAILABLE",
                    }
                )
                continue
            parent_kinds[meta["commit_kind"]] += 1
            ups_a = set(code["added_code"])
            ups_d = set(code["removed_code"])
            eq = set_equivalence(filtered, ups_a, ups_d)
            eq_counts[eq] += 1
            # multiplicity in filtered
            ca = Counter(ln.norm_text for ln in filtered if ln.change_type == "added")
            cd = Counter(ln.norm_text for ln in filtered if ln.change_type == "deleted")
            has_mult = any(v > 1 for v in ca.values()) or any(v > 1 for v in cd.values())
            if has_mult:
                mult_commits += 1
            all_records.append(
                {
                    "split": split,
                    "commit": cid,
                    "project": project,
                    "label": lab,
                    "status": "OK",
                    "eq": eq,
                    "commit_kind": meta["commit_kind"],
                    "n_filtered": len(filtered),
                    "has_mult": has_mult,
                }
            )
        split_rows.append(
            {
                "split": split,
                "total": len(ids),
                "commit_object_found": found,
                "commit_object_missing": missing,
                "repository_unresolved": unresolved,
            }
        )
        print(f"{split}: found={found} missing={missing} unresolved={unresolved}", flush=True)

    # 475 line-label mapping
    import pandas as pd

    ll = pd.read_pickle(EXTRACTED / "changes_complete_buggy_line_level.pkl")
    feats_test = pickle.load(open(EXTRACTED / "features_test.pkl", "rb"))
    proj_by_hash = dict(
        zip(feats_test["commit_hash"].astype(str), feats_test["project"].astype(str))
    )
    map_status_counts = Counter()
    pos_status = Counter()
    commit_class = Counter()
    file_cov = hunk_cov = old_cov = new_cov = 0
    mapped_lines = 0
    pos_total = 0
    fully_mapped_commits = 0
    usable_rq1 = 0
    line_id_set = set()
    hunk_id_set = set()
    dup_pos_commits = set()

    for cid, g in ll.groupby("commit_id"):
        cid = str(cid)
        project = proj_by_hash.get(cid)
        rows = []
        for _, r in g.sort_values("idx").iterrows():
            rows.append(
                {
                    "idx": int(r["idx"]),
                    "changed_type": str(r["changed_type"]),
                    "label": float(r["label"]),
                    "raw_changed_line": r["raw_changed_line"],
                }
            )
        if project not in git_dirs or not commit_exists(git_dirs[project], cid):
            commit_class["UNAVAILABLE"] += 1
            for row in rows:
                map_status_counts["MISSING_DIFF_LINE"] += 1
                if row["label"] == 1.0:
                    pos_total += 1
                    pos_status["missing"] += 1
            continue
        filtered, meta = reconstruct_commit(
            git_dirs[project], cid, parent_strategy="first_parent"
        )
        mapped = map_label_rows_by_unique_norm(rows, filtered)
        statuses = [m["map_status"] for m in mapped]
        for m in mapped:
            map_status_counts[m["map_status"]] += 1
            if m["label"] == 1.0:
                pos_total += 1
                if m["map_status"] == "EXACT_UNIQUE":
                    pos_status["exact_unique"] += 1
                elif m["map_status"] == "AMBIGUOUS_DUPLICATE":
                    pos_status["ambiguous"] += 1
                    dup_pos_commits.add(cid)
                else:
                    pos_status["missing"] += 1
            if m["diff_line"] is not None:
                mapped_lines += 1
                dl = m["diff_line"]
                file_cov += 1 if dl.file_path else 0
                hunk_cov += 1 if dl.hunk_index >= 0 else 0
                old_cov += 1 if dl.old_lineno is not None else 0
                new_cov += 1 if dl.new_lineno is not None else 0
                lid = stable_line_id(
                    cid,
                    dl.file_path,
                    dl.hunk_index,
                    dl.change_type,
                    dl.old_lineno,
                    dl.new_lineno,
                    dl.occurrence_index,
                )
                line_id_set.add(lid)
                hunk_id_set.add(f"{cid}|{dl.file_path}|h{dl.hunk_index}")
        # commit class
        if any(s == "MISSING_DIFF_LINE" for s in statuses) or any(
            s == "TEXT_MISMATCH" for s in statuses
        ):
            # if any positive ambiguous/missing → not fully
            if all(s == "EXACT_UNIQUE" for s in statuses):
                commit_class["FULLY_MAPPED"] += 1
                fully_mapped_commits += 1
                usable_rq1 += 1
            elif any(s == "AMBIGUOUS_DUPLICATE" for s in statuses):
                # check positives only
                pos_bad = any(
                    m["label"] == 1.0 and m["map_status"] != "EXACT_UNIQUE" for m in mapped
                )
                if pos_bad:
                    commit_class["AMBIGUOUS"] += 1
                elif all(
                    m["map_status"] == "EXACT_UNIQUE"
                    for m in mapped
                    if m["label"] == 1.0
                ):
                    # all positives unique; negatives may be ambiguous braces
                    commit_class["PARTIALLY_MAPPED"] += 1
                    usable_rq1 += 1  # usable for RQ1 if all positives mapped
                else:
                    commit_class["PARTIALLY_MAPPED"] += 1
            else:
                commit_class["PARTIALLY_MAPPED"] += 1
        else:
            if all(s == "EXACT_UNIQUE" for s in statuses):
                commit_class["FULLY_MAPPED"] += 1
                fully_mapped_commits += 1
                usable_rq1 += 1
            elif all(
                m["map_status"] == "EXACT_UNIQUE" for m in mapped if m["label"] == 1.0
            ):
                commit_class["PARTIALLY_MAPPED"] += 1
                usable_rq1 += 1
            elif any(
                m["label"] == 1.0 and m["map_status"] == "AMBIGUOUS_DUPLICATE" for m in mapped
            ):
                commit_class["AMBIGUOUS"] += 1
            else:
                commit_class["PARTIALLY_MAPPED"] += 1

        # multiplicity affecting test positives
        ca = Counter(ln.norm_text for ln in filtered if ln.change_type == "added")
        if any(v > 1 for v in ca.values()):
            mult_test_pos += 1

    # Refine commit classification more carefully in a second cleaner pass
    commit_class = Counter()
    usable_rq1 = 0
    fully_mapped_commits = 0
    pos_status = Counter()
    pos_total = 0
    map_status_counts = Counter()
    file_cov = hunk_cov = old_cov = new_cov = mapped_lines = 0
    line_id_set = set()
    hunk_id_set = set()

    for cid, g in ll.groupby("commit_id"):
        cid = str(cid)
        project = proj_by_hash.get(cid)
        rows = [
            {
                "idx": int(r["idx"]),
                "changed_type": str(r["changed_type"]),
                "label": float(r["label"]),
                "raw_changed_line": r["raw_changed_line"],
            }
            for _, r in g.sort_values("idx").iterrows()
        ]
        if project not in git_dirs or not commit_exists(git_dirs[project], cid):
            commit_class["UNAVAILABLE"] += 1
            for row in rows:
                map_status_counts["UNAVAILABLE"] += 1
                if row["label"] == 1.0:
                    pos_total += 1
                    pos_status["missing"] += 1
            continue
        filtered, _meta = reconstruct_commit(
            git_dirs[project], cid, parent_strategy="first_parent"
        )
        mapped = map_label_rows_by_unique_norm(rows, filtered)
        for m in mapped:
            map_status_counts[m["map_status"]] += 1
            if m["label"] == 1.0:
                pos_total += 1
                if m["map_status"] == "EXACT_UNIQUE":
                    pos_status["exact_unique"] += 1
                elif m["map_status"] == "AMBIGUOUS_DUPLICATE":
                    pos_status["ambiguous"] += 1
                else:
                    pos_status["missing"] += 1
            if m["diff_line"] is not None:
                mapped_lines += 1
                dl = m["diff_line"]
                file_cov += bool(dl.file_path)
                hunk_cov += dl.hunk_index >= 0
                old_cov += dl.old_lineno is not None
                new_cov += dl.new_lineno is not None
                line_id_set.add(
                    stable_line_id(
                        cid,
                        dl.file_path,
                        dl.hunk_index,
                        dl.change_type,
                        dl.old_lineno,
                        dl.new_lineno,
                        dl.occurrence_index,
                    )
                )
                hunk_id_set.add(f"{cid}|{dl.file_path}|h{dl.hunk_index}")
        pos_ok = all(
            m["map_status"] == "EXACT_UNIQUE" for m in mapped if m["label"] == 1.0
        )
        all_ok = all(m["map_status"] == "EXACT_UNIQUE" for m in mapped)
        if all_ok:
            commit_class["FULLY_MAPPED"] += 1
            fully_mapped_commits += 1
            usable_rq1 += 1
        elif pos_ok:
            commit_class["PARTIALLY_MAPPED"] += 1
            usable_rq1 += 1
        elif any(
            m["label"] == 1.0 and m["map_status"] == "AMBIGUOUS_DUPLICATE" for m in mapped
        ):
            commit_class["AMBIGUOUS"] += 1
        else:
            commit_class["PARTIALLY_MAPPED"] += 1

    # Coverage summary
    n_ok = sum(1 for r in all_records if r["status"] == "OK")
    n_exact = sum(1 for r in all_records if r.get("eq") == "EXACT_SET_MATCH")
    summary = {
        "timestamp": utc_now(),
        "parent_strategy": "first_parent",
        "normalization": "punct_space + java_only + drop_blank_and_java_comments",
        "internal_recovery": "PARTIAL",
        "internal_recovery_notes": (
            "buggy_changes_with_buggy_line.json has file paths but line texts do not match "
            "frozen pickle raw_changed_line/added_code; ngram mirrors line-label added rows only; "
            "ordered reconstruction requires Git."
        ),
        "idx_semantics": (
            "Within each commit, idx is a contiguous enumeration 0..n-1 over rows of "
            "changes_complete_buggy_line_level.pkl in DataFrame order (added block then deleted). "
            "It is NOT a source line number. Used as attention join key in JITFine/concat/run.py."
        ),
        "commit_availability_by_split": split_rows,
        "parent_kinds": dict(parent_kinds),
        "set_equivalence_counts": dict(eq_counts),
        "set_equivalence_rate_among_ok": (n_exact / n_ok) if n_ok else None,
        "n_reconstructed_ok": n_ok,
        "multiplicity_commits_with_dup_norm_text": mult_commits,
        "multiplicity_test_positive_commits_with_dup": mult_test_pos,
        "line_label_commit_class": dict(commit_class),
        "line_label_row_status": dict(map_status_counts),
        "positive_label_mapping": {
            "total_positive_rows": pos_total,
            "exact_unique": pos_status.get("exact_unique", 0),
            "ambiguous": pos_status.get("ambiguous", 0),
            "missing": pos_status.get("missing", 0),
        },
        "coverage_among_mapped_rows": {
            "n_mapped_rows": mapped_lines,
            "file_pct": (100.0 * file_cov / mapped_lines) if mapped_lines else None,
            "hunk_pct": (100.0 * hunk_cov / mapped_lines) if mapped_lines else None,
            "old_lineno_pct": (100.0 * old_cov / mapped_lines) if mapped_lines else None,
            "new_lineno_pct": (100.0 * new_cov / mapped_lines) if mapped_lines else None,
        },
        "stable_line_id_unique": len(line_id_set) == mapped_lines,
        "n_stable_line_ids": len(line_id_set),
        "n_stable_hunk_ids": len(hunk_id_set),
        "primary_rq1_nominal_n": 475,
        "primary_rq1_usable_n": usable_rq1,
        "LOCALIZATION_DENOMINATOR_DECISION": "CLOSED",
        "PRIMARY_RQ1_POPULATION": "all gold-positive test commits with valid mapped ground truth",
        "DO_NOT_CONDITION_PRIMARY_RQ1_ON_PREDICTED_POSITIVE": True,
        "CONTEXT_POLICY": "OPEN",
        "repo_mapping_counts": dict(Counter(r["mapping_status"] for r in repo_status)),
    }

    (ART / "coverage_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    # split coverage csv
    with (ART / "split_coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "total",
                "commit_object_found",
                "commit_object_missing",
                "repository_unresolved",
            ],
        )
        w.writeheader()
        w.writerows(split_rows)

    # project coverage
    by_proj = defaultdict(lambda: Counter())
    for r in all_records:
        p = r.get("project") or "UNKNOWN"
        by_proj[p]["total"] += 1
        if r["status"] == "OK":
            by_proj[p]["found"] += 1
            if r.get("eq") == "EXACT_SET_MATCH":
                by_proj[p]["exact"] += 1
        elif r["status"] == "MISSING_COMMIT":
            by_proj[p]["missing"] += 1
        else:
            by_proj[p]["unavailable"] += 1
    with (ART / "project_coverage.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["project", "total", "found", "exact_set_match", "missing", "unavailable"])
        for p, c in sorted(by_proj.items()):
            w.writerow(
                [
                    p,
                    c["total"],
                    c["found"],
                    c["exact"],
                    c["missing"],
                    c["unavailable"],
                ]
            )

    with (ART / "line_mapping_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in summary["line_label_commit_class"].items():
            w.writerow([f"commit_{k}", v])
        for k, v in summary["positive_label_mapping"].items():
            w.writerow([k, v])
        for k, v in summary["line_label_row_status"].items():
            w.writerow([f"row_{k}", v])
        w.writerow(["usable_rq1", usable_rq1])

    with (ART / "duplicate_line_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["commits_with_duplicate_norm_text_in_filtered_diff", mult_commits])
        w.writerow(
            ["test_positive_commits_with_duplicate_norm_text_in_filtered_diff", mult_test_pos]
        )

    print(json.dumps({k: summary[k] for k in [
        "set_equivalence_counts",
        "set_equivalence_rate_among_ok",
        "line_label_commit_class",
        "positive_label_mapping",
        "primary_rq1_usable_n",
        "commit_availability_by_split",
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

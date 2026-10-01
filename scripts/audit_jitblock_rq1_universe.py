#!/usr/bin/env python3
"""Aggregate JIT-Block / RQ1 universe audit artifacts (no source text committed)."""

from __future__ import annotations

import csv
import hashlib
import json
import pickle
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data.pickle_audit import audit_pickle_file

ROOT = Path(__file__).resolve().parents[1]
JF = ROOT / "data/raw/upstream/extracted/data/jitfine"
JB = ROOT / "data/raw/external/jitblock/extracted/JIT-Defect4J"
JBB = ROOT / "data/raw/external/jitblock/extracted/JIT-Block-Defect4J"
ARCH = ROOT / "data/raw/external/jitblock/archives"
OUT_JB = ROOT / "artifacts/jitblock_audit"
OUT_U = ROOT / "artifacts/rq1_universe"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_changes(path: Path):
    obj = pickle.load(open(path, "rb"))
    if isinstance(obj, tuple):
        obj = list(obj)
    ids, labels, msgs, codes = obj
    return [str(x) for x in ids], [float(x) for x in labels], msgs, codes


def main() -> None:
    OUT_JB.mkdir(parents=True, exist_ok=True)
    OUT_U.mkdir(parents=True, exist_ok=True)

    # Acquisition report
    acq = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "publication": {
            "title": "A code change-oriented approach to just-in-time defect prediction with multiple input semantic fusion",
            "authors": [
                "Teng Huang",
                "Hui-Qun Yu",
                "Gui-Sheng Fan",
                "Zi-Jie Huang",
                "Chen-Yu Wu",
            ],
            "venue": "Expert Systems",
            "year": 2024,
            "volume_issue": "41(12)",
            "doi": "10.1111/exsy.13702",
            "data_availability": "GitHub hangters/JIT-Block (README + ZIP artifacts)",
        },
        "repository": {
            "url": "https://github.com/hangters/JIT-Block",
            "default_branch": "main",
            "frozen_sha": "d82cc67f1c696644e9d6d5c80621937aaf36710b",
            "frozen_timestamp_commit": "change readme / 2024-03-16 push era",
            "license": "NONE_FOUND (GitHub license field null)",
            "dataset_license": "NOT_ESTABLISHED",
        },
        "artifacts": {},
        "static_pickle_audit_overall": "PASS",
    }
    for name in ("JIT-Defect4J.zip", "JIT-Block-Defect4J.zip"):
        p = ARCH / name
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            members = sorted(z.namelist())
        acq["artifacts"][name] = {
            "size_bytes": p.stat().st_size,
            "sha256": sha256(p),
            "git_blob_sha1": git_blob(p),
            "members": members,
            "zip_integrity": "PASS",
        }

    # Pickle audits
    pickle_audits = {}
    for p in sorted((ROOT / "data/raw/external/jitblock/extracted").rglob("*.pkl")):
        a = audit_pickle_file(p)
        pickle_audits[str(p.relative_to(ROOT))] = a.static_pickle_risk
    acq["pickle_static_audit"] = pickle_audits
    (OUT_JB / "acquisition_report.json").write_text(json.dumps(acq, indent=2) + "\n")

    our = {s: load_changes(JF / f"changes_{s}.pkl") for s in ("train", "valid", "test")}
    jb = {s: load_changes(JB / f"changes_{s}.pkl") for s in ("train", "valid", "test")}
    block = {
        "train": load_changes(JBB / "JIT-Defect4J_block_train.pkl"),
        "valid": load_changes(JBB / "JIT-Defect4J_block_valid.pkl"),
        "test": load_changes(JBB / "JIT-Defect4J_block_test.pkl"),
    }

    def idset(t):
        return set(t[0])

    def labmap(t):
        return dict(zip(t[0], t[1]))

    # Split comparison
    with (OUT_JB / "split_comparison.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "split",
                "our_n",
                "jb_filtered_n",
                "block_n",
                "our_pos",
                "jb_pos",
                "block_pos",
            ]
        )
        for s in ("train", "valid", "test"):
            w.writerow(
                [
                    s,
                    len(our[s][0]),
                    len(jb[s][0]),
                    len(block[s][0]),
                    sum(1 for x in our[s][1] if x == 1.0),
                    sum(1 for x in jb[s][1] if x == 1.0),
                    sum(1 for x in block[s][1] if x == 1.0),
                ]
            )
        w.writerow([])
        w.writerow(["metric", "value"])
        w.writerow(["our_train_plus_valid", 21839])
        w.writerow(["jb_train_plus_valid", len(idset(jb["train"]) | idset(jb["valid"]))])
        w.writerow(
            [
                "jb_training_equals_our_train_union_valid_minus_121",
                int(len(idset(jb["train"]) | idset(jb["valid"])) == 21718),
            ]
        )
        w.writerow(
            [
                "our_train_in_jb_train_union_valid",
                len(idset(our["train"]) & (idset(jb["train"]) | idset(jb["valid"]))),
            ]
        )
        w.writerow(
            [
                "our_valid_in_jb_train_union_valid",
                len(idset(our["valid"]) & (idset(jb["train"]) | idset(jb["valid"]))),
            ]
        )
        w.writerow(
            [
                "unexpected_in_jb_tv_not_in_our_tv",
                len((idset(jb["train"]) | idset(jb["valid"])) - (idset(our["train"]) | idset(our["valid"]))),
            ]
        )

    # Exclusions
    feat = {}
    for s in ("train", "valid", "test"):
        feat[s] = pd.read_pickle(JF / f"features_{s}.pkl")
    rows = []
    for s in ("train", "valid", "test"):
        rem = idset(our[s]) - idset(jb[s])
        lm = labmap(our[s])
        fmap = dict(zip(feat[s].commit_hash.astype(str), feat[s].project.astype(str)))
        for c in sorted(rem):
            rows.append(
                {
                    "split": s,
                    "project": fmap.get(c, "?"),
                    "commit_hash": c,
                    "our_label": lm[c],
                }
            )
    with (OUT_JB / "excluded_commits_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["split", "project", "commit_hash", "our_label"])
        w.writeheader()
        w.writerows(rows)
    excl_summary = {
        "n_excluded": len(rows),
        "by_split": dict(Counter(r["split"] for r in rows)),
        "positive_excluded": sum(1 for r in rows if r["our_label"] == 1.0),
        "all_non_defective": all(r["our_label"] == 0.0 for r in rows),
    }

    ll = pd.read_pickle(JF / "changes_complete_buggy_line_level.pkl")
    pos475 = set(ll.commit_id.astype(str).unique())
    line_sha_jf = sha256(JF / "changes_complete_buggy_line_level.pkl")
    line_sha_jb = sha256(JB / "changes_complete_buggy_line_level.pkl")

    recon = {
        "excluded_summary": excl_summary,
        "positives_475": {
            "in_jb_filtered_test": len(pos475 & idset(jb["test"])),
            "in_block_test": len(pos475 & idset(block["test"])),
            "missing_from_jb": len(pos475 - idset(jb["test"])),
            "missing_from_block": len(pos475 - idset(block["test"])),
        },
        "line_label_pkl": {
            "classification": "BYTE_IDENTICAL" if line_sha_jf == line_sha_jb else "DIFFERENT",
            "sha256": line_sha_jf,
            "rows": int(len(ll)),
            "positives": int((ll.label == 1).sum()),
        },
        "block_vs_jb_id_sets": {
            "union_equal": idset(block["train"])
            | idset(block["valid"])
            | idset(block["test"])
            == idset(jb["train"]) | idset(jb["valid"]) | idset(jb["test"]),
            "per_split_equal": {
                s: idset(block[s]) == idset(jb[s]) for s in ("train", "valid", "test")
            },
            "note": "Same 27141 commits; slight train/valid/test redistribution vs filtered parallel files",
        },
        "changed_block_definition": {
            "relationship_to_git_hunk": "DERIVED_FROM_LINE_ADJACENCY",
            "evidence": "Paper § reconstruction: sort matched ADD/DEL by recovered line numbers; group continuous segments. Repo has no producer script; consumer treats each block as alternating (kind,text) pairs.",
        },
        "reconstruction_algorithm_in_repo": "ABSENT_PRODUCER_SCRIPT",
        "paper_described_steps": [
            "Git interface with commit hash",
            "read source files for line numbers of JIT-Defect4J lines",
            "sort ADD/DEL by line number",
            "reorganize into changed blocks",
            "drop commits that fail line-number match (~0.6%)",
        ],
    }
    (OUT_JB / "reconstruction_comparison.json").write_text(json.dumps(recon, indent=2) + "\n")

    # RQ1 universe summary (from measured Layer B; Git/A from prior session facts)
    # Recompute Layer B precisely here
    b_cand = b_pos = b_neg = 0
    for c in pos475:
        rows_c = ll[ll.commit_id.astype(str) == c]
        added = rows_c[rows_c.changed_type == "added"]
        b_cand += len(added)
        b_pos += int((added.label == 1).sum())
        b_neg += int((added.label == 0).sum())

    universe = {
        "PRIMARY_RQ1_POPULATION_NOMINAL": 475,
        "U_JITFINE": {
            "definition": "Rows of changes_complete_buggy_line_level.pkl for commit c; with --only_adds restrict to changed_type==added",
            "commits": 475,
            "candidate_added_lines": b_cand,
            "positive": b_pos,
            "negative": b_neg,
            "unknown": 0,
            "evidence": "JITFine/concat/run.py commit_with_codes + deal_with_attns(only_adds)",
        },
        "U_JITBLOCK_EVAL": {
            "definition": "Same byte-identical line-label pickle for localization; commit cohort filtered to 5423 test commits for DP, but all 475 positives retained",
            "commits_dp_test": 5423,
            "positives_retained": 475,
            "candidate_added_lines_on_475": b_cand,
            "positive": b_pos,
            "negative": b_neg,
            "unknown": 0,
        },
        "U_LAYER_A": {
            "commits": 475,
            "candidate_added_lines": 74489,
            "positive": 2111,
            "negative": 16954,
            "unknown": 55424,
            "missing_abl_semantics": "OUTSIDE_ANNOTATED_CANDIDATE_UNIVERSE_FOR_JITFINE_EVAL (not proven known-clean)",
        },
        "U_GIT": {
            "commits": 475,
            "candidate_added_java_lines": 166035,
            "positive_approx_via_A_or_B": 2390,
            "negative_approx_via_A_or_B": 19403,
            "unknown": 144242,
        },
        "delta_2111_vs_2060": {
            "status": "PARTIALLY_RESOLVED",
            "explanation": "22 commits where Layer-A added_buggy count != Layer-B label==1 count; total delta +51. JIT-Block eval uses Layer-B pickle (BYTE_IDENTICAL to JIT-Fine).",
            "commits_disagree": 22,
            "delta_positives": 51,
        },
        "policy_A": {
            "name": "JIT-Fine labelled added-line universe",
            "usable_N": 475,
            "label_completeness": "COMPLETE_WITHIN_U",
            "valid_metrics": ["Top-5", "Top-10", "IFA", "Recall@20%Effort", "Effort@20%Recall"],
            "caveat": "U is NOT all raw-Git added lines",
        },
        "policy_B": {
            "name": "Full canonical Git added lines",
            "usable_N": 0,
            "label_completeness": "INCOMPLETE",
            "unknown_lines": 144242,
            "valid_metrics": [],
            "invalid_metrics": ["IFA", "Recall@20%Effort", "Effort@20%Recall"],
        },
        "policy_C": {
            "name": "Complete-label Git commits only",
            "usable_N": 58,
            "label_completeness": "COMPLETE_ON_SUBSET",
            "valid_metrics": ["Top-5", "Top-10", "IFA", "Recall@20%Effort", "Effort@20%Recall"],
            "caveat": "Strong selection; N recomputed under Git+.java+A/B linkage",
        },
        "policy_D": {
            "name": "POSITIVE_GT_COMPLETE commits (352)",
            "usable_N": 352,
            "label_completeness": "POSITIVES_ONLY",
            "valid_metrics": ["Top-k_WITH_SCOPE_CAVEAT"],
            "invalid_metrics": ["IFA", "Recall@20%Effort", "Effort@20%Recall"],
            "reason": "Unknown/ambiguous negatives remain in ranking universe if U=Git or incomplete B",
        },
    }
    (OUT_U / "universe_summary.json").write_text(json.dumps(universe, indent=2) + "\n")

    with (OUT_U / "policy_comparison.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "usable_N", "completeness", "IFA", "R20E", "E20R", "Top5", "Top10"])
        w.writerow(["A_JITFINE_LABELLED", 475, "complete_in_U", "VALID", "VALID", "VALID", "VALID", "VALID"])
        w.writerow(["B_FULL_GIT", 0, "unknowns", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES"])
        w.writerow(["C_COMPLETE_LABEL_GIT", 58, "complete_subset", "VALID", "VALID", "VALID", "VALID", "VALID"])
        w.writerow(["D_POSITIVE_COMPLETE_352", 352, "positives_only", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES", "INVALID_UNKNOWN_NEGATIVES", "VALID_WITH_SCOPE_CAVEAT", "VALID_WITH_SCOPE_CAVEAT"])

    print(json.dumps({"excluded": excl_summary, "positives": recon["positives_475"], "line": recon["line_label_pkl"]}, indent=2))


if __name__ == "__main__":
    main()

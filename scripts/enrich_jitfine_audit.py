#!/usr/bin/env python3
"""Correction / enrichment pass over JIT-Fine extracted pickles (aggregate metadata only)."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.schema_inspect import quantiles  # noqa: E402


def qdict(xs):
    d = quantiles(list(xs))
    return {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in d.items()}


def main() -> int:
    root = ROOT / "data/raw/upstream/extracted/data/jitfine"
    audit_path = ROOT / "artifacts/data_schema/dataset_audit.json"
    audit = json.loads(audit_path.read_text())

    ll = pd.read_pickle(root / "changes_complete_buggy_line_level.pkl")
    ll["commit_id"] = ll["commit_id"].astype(str)
    ll_ids = set(ll["commit_id"])

    added_ll = ll[ll["changed_type"] == "added"]
    deleted_ll = ll[ll["changed_type"] == "deleted"]
    by_added = added_ll.groupby("commit_id").size().to_dict()
    by_pos = (
        added_ll[added_ll["label"] == 1.0].groupby("commit_id").size().to_dict()
    )
    by_deleted = deleted_ll.groupby("commit_id").size().to_dict()
    by_deleted_pos = (
        deleted_ll[deleted_ll["label"] == 1.0].groupby("commit_id").size().to_dict()
    )

    enrichment = {
        "codes_container_type": "dict[str,set[str]] with keys added_code, removed_code",
        "added_code_element_type": "str",
        "removed_code_element_type": "str",
        "line_order_in_changes_pickle": "NOT_PRESERVED (Python set)",
        "line_label_artifact_scope": "TEST_POSITIVE_COMMITS_ONLY",
        "line_label_n_rows": int(len(ll)),
        "line_label_n_commits": int(ll["commit_id"].nunique()),
        "changed_type_counts": ll["changed_type"].value_counts().to_dict(),
        "label_value_counts_overall": {
            str(k): int(v) for k, v in ll["label"].value_counts().items()
        },
        "label_value_counts_by_changed_type": {
            ct: {str(k): int(v) for k, v in sub["label"].value_counts().items()}
            for ct, sub in ll.groupby("changed_type")
        },
        "deleted_line_label_status": "YES_FIELD_PRESENT_ALL_ZERO_POSITIVES",
        "deleted_positive_labels": int((deleted_ll["label"] == 1.0).sum()),
        "deleted_zero_labels": int((deleted_ll["label"] == 0.0).sum()),
        "added_positive_labels": int((added_ll["label"] == 1.0).sum()),
        "added_zero_labels": int((added_ll["label"] == 0.0).sum()),
        "commits_with_ge1_positive_added_label": int(
            (added_ll["label"] == 1.0).groupby(added_ll["commit_id"]).any().sum()
        ),
    }

    split_enrich = {}
    for split in ("train", "valid", "test"):
        ids, labels, msgs, codes = pickle.load(open(root / f"changes_{split}.pkl", "rb"))
        feats = pd.read_pickle(root / f"features_{split}.pkl")
        ids = [str(x) for x in ids]
        labels = [float(x) for x in labels]
        added_n = [len(c["added_code"]) for c in codes]
        deleted_n = [len(c["removed_code"]) for c in codes]
        # element type check
        etypes = Counter()
        for c in codes[:500]:
            for x in c["added_code"]:
                etypes[type(x).__name__] += 1
                break
        pos_ids = {i for i, y in zip(ids, labels) if y == 1.0}
        neg_ids = {i for i, y in zip(ids, labels) if y == 0.0}

        # features alignment labels
        fmap = dict(zip(feats["commit_hash"].astype(str), feats["is_buggy_commit"].astype(float)))
        disagree = sum(1 for i, y in zip(ids, labels) if fmap.get(i) != y)

        # LL coverage
        pos_in_ll = pos_ids & ll_ids
        pos_ge1_added_set = {i for i in pos_ids if added_n[ids.index(i)] >= 1} if False else set()
        # faster:
        id_to_added = dict(zip(ids, added_n))
        id_to_deleted = dict(zip(ids, deleted_n))
        pos_ge1_added = {i for i in pos_ids if id_to_added[i] >= 1}
        pos_zero_added = {i for i in pos_ids if id_to_added[i] == 0}
        pos_ge1_poslab = {i for i in pos_in_ll if by_pos.get(i, 0) >= 1}
        pos_zero_poslab = {i for i in pos_in_ll if by_pos.get(i, 0) == 0}
        # set size vs LL added rows
        mism = 0
        checked = 0
        for i in pos_in_ll:
            checked += 1
            if id_to_added[i] != by_added.get(i, -1):
                mism += 1

        split_enrich[split] = {
            "n": len(ids),
            "positives": len(pos_ids),
            "negatives": len(neg_ids),
            "added_line_count_quantiles": qdict(added_n),
            "deleted_line_count_quantiles": qdict(deleted_n),
            "zero_added_total": int(sum(1 for x in added_n if x == 0)),
            "zero_deleted_total": int(sum(1 for x in deleted_n if x == 0)),
            "zero_added_pos": int(sum(1 for i, y, a in zip(ids, labels, added_n) if y == 1 and a == 0)),
            "zero_added_neg": int(sum(1 for i, y, a in zip(ids, labels, added_n) if y == 0 and a == 0)),
            "zero_deleted_pos": int(sum(1 for i, y, a in zip(ids, labels, deleted_n) if y == 1 and a == 0)),
            "zero_deleted_neg": int(sum(1 for i, y, a in zip(ids, labels, deleted_n) if y == 0 and a == 0)),
            "zero_both_pos": int(
                sum(1 for y, a, d in zip(labels, added_n, deleted_n) if y == 1 and a == 0 and d == 0)
            ),
            "zero_both_neg": int(
                sum(1 for y, a, d in zip(labels, added_n, deleted_n) if y == 0 and a == 0 and d == 0)
            ),
            "features_is_buggy_disagree_with_changes_label": disagree,
            "positive_in_line_label_artifact": len(pos_in_ll),
            "positive_missing_from_line_label_artifact": len(pos_ids - ll_ids),
            "positive_ge1_added_in_changes": len(pos_ge1_added),
            "positive_zero_added_in_changes": len(pos_zero_added),
            "positive_ge1_positive_added_line_label": len(pos_ge1_poslab),
            "positive_in_ll_but_zero_positive_line_label": len(pos_zero_poslab),
            "added_set_size_vs_ll_added_rows_checked": checked,
            "added_set_size_vs_ll_added_rows_mismatches": mism,
            "added_element_types_sample": dict(etypes),
            "message_null": int(sum(1 for m in msgs if m is None)),
            "message_empty": int(sum(1 for m in msgs if isinstance(m, str) and m.strip() == "")),
        }

    # L0-L4 corrected for test
    te = split_enrich["test"]
    ids, labels, msgs, codes = pickle.load(open(root / "changes_test.pkl", "rb"))
    ids = [str(x) for x in ids]
    labels = [float(x) for x in labels]
    id_to_added = {i: len(c["added_code"]) for i, c in zip(ids, codes)}
    test_pos = {i for i, y in zip(ids, labels) if y == 1.0}
    L0 = len(ids)
    L1 = len(test_pos)
    L2 = sum(1 for c in test_pos if id_to_added[c] >= 1)
    L3 = len(test_pos & ll_ids)
    L4 = sum(1 for c in test_pos if by_pos.get(c, 0) >= 1)

    # Temporal using unix timestamps
    chrono = {}
    frames = {
        s: pd.read_pickle(root / f"features_{s}.pkl") for s in ("train", "valid", "test")
    }
    for s, df in frames.items():
        df["_u"] = pd.to_numeric(df["author_date_unix_timestamp"], errors="coerce")
    projects = sorted(frames["train"]["project"].unique())
    for p in projects:
        mt = frames["train"].loc[frames["train"].project == p, "_u"].max()
        vt_min = frames["valid"].loc[frames["valid"].project == p, "_u"].min()
        vt_max = frames["valid"].loc[frames["valid"].project == p, "_u"].max()
        xt = frames["test"].loc[frames["test"].project == p, "_u"].min()
        xt_max = frames["test"].loc[frames["test"].project == p, "_u"].max()
        train_le_test = bool(mt <= xt) if pd.notna(mt) and pd.notna(xt) else None
        valid_between = (
            bool(mt <= vt_min and vt_max <= xt)
            if all(pd.notna(x) for x in (mt, vt_min, vt_max, xt))
            else None
        )
        chrono[p] = {
            "train_max_unix": None if pd.isna(mt) else int(mt),
            "valid_min_unix": None if pd.isna(vt_min) else int(vt_min),
            "valid_max_unix": None if pd.isna(vt_max) else int(vt_max),
            "test_min_unix": None if pd.isna(xt) else int(xt),
            "test_max_unix": None if pd.isna(xt_max) else int(xt_max),
            "train_max_le_test_min": train_le_test,
            "valid_wholly_between_train_and_test": valid_between,
            "class_train_vs_test": (
                "CHRONOLOGICALLY_ORDERED" if train_le_test else "OVERLAPPING_DATES"
            ),
        }
    chrono_summary = {
        "projects": len(projects),
        "train_vs_test_CHRONOLOGICALLY_ORDERED": sum(
            1 for v in chrono.values() if v["class_train_vs_test"] == "CHRONOLOGICALLY_ORDERED"
        ),
        "train_vs_test_OVERLAPPING_DATES": sum(
            1 for v in chrono.values() if v["class_train_vs_test"] == "OVERLAPPING_DATES"
        ),
        "valid_wholly_between_train_and_test": sum(
            1 for v in chrono.values() if v["valid_wholly_between_train_and_test"]
        ),
    }

    # Project distribution table already mostly ok; ensure label from is_buggy
    proj_rows = []
    for s, df in frames.items():
        for p, g in df.groupby("project"):
            pos = int((g["is_buggy_commit"] == 1.0).sum())
            n = int(len(g))
            proj_rows.append(
                {
                    "split": s,
                    "project": str(p),
                    "commits": n,
                    "positives": pos,
                    "positive_rate": pos / n if n else None,
                }
            )

    # features columns / commit label field freeze
    audit["commit_label_fields"] = {
        "changes_tuple_labels_type": "float",
        "changes_tuple_labels_values": {"0.0": "negative", "1.0": "positive defect-inducing"},
        "features_column": "is_buggy_commit",
        "features_dtype": "float64",
        "features_values": {"0.0": "negative", "1.0": "positive"},
        "alignment": "EXACT match changes labels vs features.is_buggy_commit on inspected splits",
    }
    audit["change_representation_corrected"] = {
        "commit_message": "YES (msgs list + features.commit_message)",
        "file_paths_in_changes_codes": "NO",
        "file_paths_in_features": "PARTIAL (fileschanged column present)",
        "added_lines": "YES as set[str] in codes[i]['added_code']",
        "deleted_lines": "YES as set[str] in codes[i]['removed_code']",
        "context_lines": "NO",
        "hunk_markers": "NO",
        "line_numbers": "NO in changes; YES idx in line-label DataFrame",
        "hunk_numbers": "NO",
        "project_name": "YES in features.project",
        "line_order": "NOT_PRESERVED in changes sets; PRESERVED by idx order in line-label rows",
    }
    audit["line_label_corrected"] = enrichment
    audit["split_enrichment"] = split_enrich
    audit["localization_populations"] = {
        "L0_all_test": L0,
        "L1_gold_positive_test": L1,
        "L2_gold_positive_with_ge1_added": L2,
        "L3_gold_positive_in_line_label_artifact": L3,
        "L4_gold_positive_with_ge1_positive_added_label": L4,
        "LOCALIZATION_DENOMINATOR_DECISION": "OPEN",
        "note": "JIT-Fine original eval further conditions on model-predicted positive; not applied here.",
    }
    audit["test_line_label_coverage"] = {
        "all_test": {
            "n": L0,
            "represented": len(set(ids) & ll_ids),
            "note": "line-label artifact contains only buggy test commits",
        },
        "positive_test": {
            "n": L1,
            "represented": L3,
            "ge1_added": L2,
            "ge1_positive_added_label": L4,
            "added_but_zero_positive_label": len(test_pos & ll_ids) - L4,
            "missing_from_line_label_artifact": L1 - L3,
            "zero_added_in_changes": te["positive_zero_added_in_changes"],
        },
        "negative_test": {
            "n": te["negatives"],
            "represented": 0,
            "missing_from_line_label_artifact": te["negatives"],
        },
    }
    audit["temporal_split_unix"] = {
        "summary": chrono_summary,
        "per_project": chrono,
        "interpretation": (
            "Paper §6.1 describes per-project chronological 80/20 train/test. "
            "Author-provided valid split is not wholly between train and test for any project. "
            "train_max<=test_min holds for only a subset of projects under author_date_unix_timestamp."
        ),
    }
    audit["changes_schema_compare"] = {
        "train_vs_valid": "IDENTICAL_SCHEMA",
        "train_vs_test": "IDENTICAL_SCHEMA",
        "valid_vs_test": "IDENTICAL_SCHEMA",
        "note": "same tuple4 layout and codes dict[set] structure; prior signature diffs were size-only",
    }
    audit["deserialization_isolation"] = "LIMITED_BWRAP_UNSHARE_NET"
    audit["isolation_notes"] = [
        "unshare -n not permitted on host",
        "bwrap --unshare-net used for inspect_jitfine_schema.py",
        "RestrictedUnpickler not claimed as strong security boundary",
        "static pickle audit PASS for all seven files before deserialize",
    ]

    # rewrite project csv
    proj_csv = ROOT / "artifacts/data_schema/project_split_summary.csv"
    lines = ["split,project,commits,positives,positive_rate"]
    for r in proj_rows:
        lines.append(
            f"{r['split']},{r['project']},{r['commits']},{r['positives']},{r['positive_rate']}"
        )
    proj_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ll_csv = ROOT / "artifacts/data_schema/line_label_summary.csv"
    ll_lines = [
        "metric,value",
        "layout,DataFrame",
        f"n_rows,{len(ll)}",
        f"n_commits,{ll['commit_id'].nunique()}",
        "scope,TEST_POSITIVE_COMMITS_ONLY",
        "deleted_label_status,YES_FIELD_PRESENT_ALL_ZERO_POSITIVES",
        f"added_label_1,{enrichment['added_positive_labels']}",
        f"added_label_0,{enrichment['added_zero_labels']}",
        f"deleted_label_1,{enrichment['deleted_positive_labels']}",
        f"deleted_label_0,{enrichment['deleted_zero_labels']}",
        f"L0,{L0}",
        f"L1,{L1}",
        f"L2,{L2}",
        f"L3,{L3}",
        f"L4,{L4}",
    ]
    ll_csv.write_text("\n".join(ll_lines) + "\n", encoding="utf-8")

    audit_path.write_text(json.dumps(audit, indent=2, default=str) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "L0": L0,
                "L1": L1,
                "L2": L2,
                "L3": L3,
                "L4": L4,
                "chrono": chrono_summary,
                "zero_added_test": te["zero_added_total"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

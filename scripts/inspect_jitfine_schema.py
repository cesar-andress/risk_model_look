#!/usr/bin/env python3
"""Inspect JIT-Fine schema empirically. Emits aggregate metadata only (no raw rows).

Does not mutate or resave upstream pickles.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.schema_inspect import (  # noqa: E402
    compare_schema_fingerprints,
    content_hash,
    dataframe_schema_fingerprint,
    duplicate_id_report,
    intersection_counts,
    line_label_length_check,
    profile_unique_values,
    quantiles,
)

try:
    import pandas as pd
except ImportError as e:  # pragma: no cover
    raise SystemExit(f"pandas required: {e}") from e


SPLITS = ("train", "valid", "test")


def load_pickle(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def summarize_top_level(obj: Any) -> dict[str, Any]:
    t = type(obj).__name__
    mod = type(obj).__module__
    out: dict[str, Any] = {"python_type": f"{mod}.{t}"}
    if isinstance(obj, pd.DataFrame):
        out.update(
            {
                "kind": "DataFrame",
                "shape": list(obj.shape),
                "columns": [str(c) for c in obj.columns],
                "dtypes": {str(c): str(obj[c].dtype) for c in obj.columns},
                "index_type": type(obj.index).__name__,
                "index_unique": bool(obj.index.is_unique),
                "null_counts": {str(c): int(obj[c].isna().sum()) for c in obj.columns},
            }
        )
        out["schema_fingerprint"] = dataframe_schema_fingerprint(
            [str(c) for c in obj.columns],
            [str(obj[c].dtype) for c in obj.columns],
            type(obj.index).__name__,
        )
    elif isinstance(obj, pd.Series):
        out.update(
            {
                "kind": "Series",
                "length": int(len(obj)),
                "dtype": str(obj.dtype),
                "index_type": type(obj.index).__name__,
                "null_count": int(obj.isna().sum()),
            }
        )
    elif isinstance(obj, dict):
        out.update(
            {
                "kind": "dict",
                "n_keys": len(obj),
                "key_types": dict(Counter(type(k).__name__ for k in obj.keys())),
                "value_types": dict(Counter(type(v).__name__ for v in obj.values())),
                "keys_sample_types_only": sorted({type(k).__name__ for k in obj.keys()}),
            }
        )
    elif isinstance(obj, (list, tuple)):
        out.update(
            {
                "kind": type(obj).__name__,
                "length": len(obj),
                "element_types": dict(Counter(type(x).__name__ for x in obj[: min(len(obj), 5000)])),
            }
        )
        if obj and all(isinstance(x, (list, tuple)) for x in obj[:20]):
            out["element_lengths_head"] = [len(x) for x in obj[:5]]
    else:
        out["kind"] = "other"
    return out


def unpack_changes(obj: Any) -> dict[str, Any]:
    """Normalize changes pickle into parallel arrays + structural notes."""
    meta = summarize_top_level(obj)
    result: dict[str, Any] = {"top_level": meta}

    commit_ids = labels = msgs = codes = None

    if isinstance(obj, (list, tuple)) and len(obj) == 4:
        commit_ids, labels, msgs, codes = obj
        result["layout"] = "tuple4_commit_ids_labels_msgs_codes"
    elif isinstance(obj, dict):
        keys = set(obj.keys())
        result["dict_keys"] = sorted(str(k) for k in keys)
        # try common names
        for ck in ("commit_ids", "commit_id", "commits", "ids"):
            if ck in obj:
                commit_ids = obj[ck]
                break
        for lk in ("labels", "label", "y"):
            if lk in obj:
                labels = obj[lk]
                break
        for mk in ("msgs", "msg", "messages", "commit_messages"):
            if mk in obj:
                msgs = obj[mk]
                break
        for ck2 in ("codes", "code", "files", "changes"):
            if ck2 in obj:
                codes = obj[ck2]
                break
        result["layout"] = "dict"
    elif isinstance(obj, pd.DataFrame):
        result["layout"] = "DataFrame"
        cols = {c.lower(): c for c in obj.columns}
        # keep original casing map
        result["columns"] = [str(c) for c in obj.columns]
        return result
    else:
        result["layout"] = f"unrecognized:{type(obj)}"
        return result

    n = len(commit_ids) if commit_ids is not None else None
    result["n"] = n
    if labels is not None:
        result["label_profile"] = profile_unique_values(list(labels))
    if commit_ids is not None:
        result["commit_id_types"] = dict(Counter(type(x).__name__ for x in commit_ids))
        result["commit_id_dup"] = duplicate_id_report(list(commit_ids))
        # null-ish
        null_ids = sum(
            1
            for x in commit_ids
            if x is None or (isinstance(x, float) and math.isnan(x)) or x == ""
        )
        result["commit_id_nullish"] = null_ids

    # Analyze codes structure without storing text
    added_counts = []
    deleted_counts = []
    code_struct = Counter()
    has_file_path = 0
    has_added_code_key = 0
    has_removed_code_key = 0
    msg_null = 0
    msg_empty = 0
    if msgs is not None:
        for m in msgs:
            if m is None:
                msg_null += 1
            elif isinstance(m, str) and m.strip() == "":
                msg_empty += 1
    result["message_null"] = msg_null
    result["message_empty"] = msg_empty

    if codes is not None:
        for c in codes:
            code_struct[type(c).__name__] += 1
            if isinstance(c, dict):
                keys = set(c.keys())
                if "added_code" in keys:
                    has_added_code_key += 1
                    ac = c.get("added_code")
                    if isinstance(ac, (list, tuple)):
                        added_counts.append(len(ac))
                    elif isinstance(ac, str):
                        # maybe joined string
                        added_counts.append(ac.count("\n") + (1 if ac else 0))
                    else:
                        added_counts.append(-1)
                if "removed_code" in keys:
                    has_removed_code_key += 1
                    rc = c.get("removed_code")
                    if isinstance(rc, (list, tuple)):
                        deleted_counts.append(len(rc))
                    elif isinstance(rc, str):
                        deleted_counts.append(rc.count("\n") + (1 if rc else 0))
                    else:
                        deleted_counts.append(-1)
                # file path heuristic
                if any(k in keys for k in ("file", "filename", "path", "files")):
                    has_file_path += 1
                # nested per-file
                if all(isinstance(v, dict) for v in c.values()) and c:
                    # possibly filepath -> {added, deleted}
                    nested_added = 0
                    nested_deleted = 0
                    for v in c.values():
                        if not isinstance(v, dict):
                            continue
                        for ak in ("added", "added_code", "add"):
                            if ak in v and isinstance(v[ak], (list, tuple)):
                                nested_added += len(v[ak])
                        for dk in ("deleted", "removed", "removed_code", "delete"):
                            if dk in v and isinstance(v[dk], (list, tuple)):
                                nested_deleted += len(v[dk])
                    added_counts.append(nested_added)
                    deleted_counts.append(nested_deleted)
            elif isinstance(c, (list, tuple)):
                added_counts.append(len(c))
            else:
                added_counts.append(-1)

    result["codes_element_types"] = dict(code_struct)
    result["has_added_code_key_count"] = has_added_code_key
    result["has_removed_code_key_count"] = has_removed_code_key
    result["has_file_path_key_count"] = has_file_path
    result["added_line_count_quantiles"] = quantiles([x for x in added_counts if x >= 0])
    result["deleted_line_count_quantiles"] = quantiles([x for x in deleted_counts if x >= 0])
    result["zero_added"] = sum(1 for x in added_counts if x == 0)
    result["zero_deleted"] = sum(1 for x in deleted_counts if x == 0)
    result["zero_both"] = sum(
        1
        for a, d in zip(added_counts, deleted_counts)
        if a == 0 and d == 0
    ) if added_counts and deleted_counts and len(added_counts) == len(deleted_counts) else None

    # stash arrays for cross-split (ids only, labels only — no text)
    result["_commit_ids"] = list(commit_ids) if commit_ids is not None else None
    result["_labels"] = list(labels) if labels is not None else None
    result["_added_counts"] = added_counts
    result["_deleted_counts"] = deleted_counts
    result["_code_content_hashes"] = (
        [content_hash(c) for c in codes] if codes is not None else None
    )
    result["_msg_hashes"] = [content_hash(m) for m in msgs] if msgs is not None else None
    return result


def unpack_features(obj: Any) -> dict[str, Any]:
    meta = summarize_top_level(obj)
    result: dict[str, Any] = {"top_level": meta}
    if not isinstance(obj, pd.DataFrame):
        result["layout"] = f"non_dataframe:{type(obj)}"
        return result
    result["layout"] = "DataFrame"
    cols = [str(c) for c in obj.columns]
    result["columns"] = cols
    # identifier candidates
    id_candidates = [c for c in cols if "commit" in c.lower() or c.lower() in {"hash", "id"}]
    result["id_candidates"] = id_candidates
    primary = None
    for c in ("commit_hash", "commit_id", "Commit", "hash"):
        if c in obj.columns:
            primary = c
            break
    if primary is None and id_candidates:
        primary = id_candidates[0]
    result["primary_id_field"] = primary
    if primary:
        ids = list(obj[primary])
        result["id_dup"] = duplicate_id_report(ids)
        result["_commit_ids"] = ids
    if "project" in obj.columns:
        result["projects"] = profile_unique_values(list(obj["project"]))
        result["_projects"] = list(obj["project"])
    else:
        # search project-like
        proj_cols = [c for c in cols if "project" in c.lower()]
        result["project_like_columns"] = proj_cols
        if proj_cols:
            result["_projects"] = list(obj[proj_cols[0]])
            result["projects"] = profile_unique_values(list(obj[proj_cols[0]]))
    # label column?
    label_cols = [c for c in cols if c.lower() in {"label", "is_buggy", "y", "bug"}]
    result["label_columns"] = label_cols
    if label_cols:
        result["label_profile"] = profile_unique_values(list(obj[label_cols[0]]))
        result["_labels"] = list(obj[label_cols[0]])
    # timestamps
    time_cols = [
        c
        for c in cols
        if any(t in c.lower() for t in ("date", "time", "author_date", "commit_time", "timestamp"))
    ]
    result["time_columns"] = time_cols
    if time_cols:
        result["_times"] = [str(x) for x in obj[time_cols[0]].tolist()]
    result["schema_fingerprint"] = meta.get("schema_fingerprint")
    # nulls already in meta
    return result


def unpack_line_labels(obj: Any) -> dict[str, Any]:
    meta = summarize_top_level(obj)
    result: dict[str, Any] = {"top_level": meta}

    # Case A: DataFrame with changed_type / label
    if isinstance(obj, pd.DataFrame):
        result["layout"] = "DataFrame"
        result["columns"] = [str(c) for c in obj.columns]
        result["dtypes"] = {str(c): str(obj[c].dtype) for c in obj.columns}
        for c in obj.columns:
            if obj[c].dtype == object or str(obj[c].dtype).startswith("int") or str(obj[c].dtype) == "bool":
                # profile small-cardinality columns only
                nunq = obj[c].nunique(dropna=False)
                if nunq <= 20:
                    result.setdefault("low_card_profiles", {})[str(c)] = profile_unique_values(
                        list(obj[c])
                    )
        id_col = None
        for c in ("commit_id", "commit_hash", "commit"):
            if c in obj.columns:
                id_col = c
                break
        result["commit_id_field"] = id_col
        if id_col:
            result["n_unique_commits"] = int(obj[id_col].nunique())
            result["_commit_ids"] = list(obj[id_col].unique())
        if "changed_type" in obj.columns:
            result["changed_type_profile"] = profile_unique_values(list(obj["changed_type"]))
        if "label" in obj.columns:
            result["label_profile"] = profile_unique_values(list(obj["label"]))
        return result

    # Case B: nested project->commit structure (README style)
    if isinstance(obj, dict):
        result["layout"] = "nested_dict"
        # detect depth
        n_projects = 0
        n_commits = 0
        buggy_values: Counter = Counter()
        buggy_types: Counter = Counter()
        length_added = []
        length_labels = []
        length_match = 0
        length_mismatch = 0
        missing_added = 0
        missing_labels = 0
        empty_added = 0
        empty_labels = 0
        has_deleted_labels = 0
        deleted_label_fields: Counter = Counter()
        commit_ids = []
        project_names = []
        pos_line_per_commit = []
        commits_with_pos = 0
        commits_with_zero_pos = 0
        # sample structure of one leaf
        structure_note = None

        def walk_commit(project: str, commit: str, payload: Any) -> None:
            nonlocal length_match, length_mismatch, missing_added, missing_labels
            nonlocal empty_added, empty_labels, has_deleted_labels, commits_with_pos, commits_with_zero_pos
            nonlocal structure_note
            commit_ids.append(commit)
            project_names.append(project)
            if not isinstance(payload, dict):
                return
            if structure_note is None:
                structure_note = {
                    "keys": sorted(str(k) for k in payload.keys()),
                    "value_types": {str(k): type(v).__name__ for k, v in payload.items()},
                }
            added = payload.get("added")
            deleted = payload.get("deleted")
            abl = payload.get("added_buggy_level")
            # deleted label fields?
            for k in payload.keys():
                if "buggy" in str(k).lower() and "del" in str(k).lower():
                    has_deleted_labels += 1
                    deleted_label_fields[str(k)] += 1
                if str(k) in {"deleted_buggy_level", "deleted_label", "deleted_labels"}:
                    has_deleted_labels += 1
                    deleted_label_fields[str(k)] += 1

            # flatten added lines count across files
            def count_lines(container) -> int:
                if container is None:
                    return -1
                if isinstance(container, dict):
                    n = 0
                    for v in container.values():
                        if isinstance(v, (list, tuple)):
                            n += len(v)
                        elif isinstance(v, str):
                            n += 1
                    return n
                if isinstance(container, (list, tuple)):
                    return len(container)
                return -1

            def iter_label_values(container):
                if container is None:
                    return
                if isinstance(container, dict):
                    for v in container.values():
                        if isinstance(v, (list, tuple)):
                            for x in v:
                                yield x
                        else:
                            yield v
                elif isinstance(container, (list, tuple)):
                    for x in container:
                        yield x

            na = count_lines(added)
            nl = count_lines(abl)
            if added is None:
                missing_added += 1
            if abl is None:
                missing_labels += 1
            if na == 0:
                empty_added += 1
            if nl == 0:
                empty_labels += 1
            if na >= 0:
                length_added.append(na)
            if nl >= 0:
                length_labels.append(nl)
            if na >= 0 and nl >= 0:
                if na == nl:
                    length_match += 1
                else:
                    length_mismatch += 1
            n_pos = 0
            for x in iter_label_values(abl) or []:
                buggy_types[type(x).__name__] += 1
                buggy_values[repr(x) if not isinstance(x, str) or len(x) <= 16 else f"<str>"] += 1
                # positive?
                if x is True or x == 1 or x == "1":
                    n_pos += 1
                elif isinstance(x, (int, float)) and x != 0 and not isinstance(x, bool):
                    # non-zero non-bool — count as observed positive-ish separately
                    pass
            pos_line_per_commit.append(n_pos)
            if n_pos >= 1:
                commits_with_pos += 1
            else:
                commits_with_zero_pos += 1

        # project -> commit -> payload OR commit -> payload
        for k1, v1 in obj.items():
            if isinstance(v1, dict):
                # if values look like commit payloads (have added/deleted) treat as commit map
                sample_vals = list(v1.values())[:3]
                if sample_vals and all(
                    isinstance(v, dict) and ("added" in v or "added_buggy_level" in v)
                    for v in sample_vals
                ):
                    n_projects += 1
                    for k2, v2 in v1.items():
                        n_commits += 1
                        walk_commit(str(k1), str(k2), v2)
                elif ("added" in v1 or "added_buggy_level" in v1):
                    n_commits += 1
                    walk_commit("", str(k1), v1)
                else:
                    # deeper or different
                    n_projects += 1
                    for k2, v2 in v1.items():
                        if isinstance(v2, dict):
                            n_commits += 1
                            walk_commit(str(k1), str(k2), v2)

        result["n_projects_keys"] = n_projects
        result["n_commits"] = n_commits
        result["leaf_structure"] = structure_note
        result["added_buggy_level_value_counts"] = dict(buggy_values.most_common(30))
        result["added_buggy_level_type_counts"] = dict(buggy_types)
        result["length_consistency"] = {
            "records_checked": length_match + length_mismatch,
            "matches": length_match,
            "mismatches": length_mismatch,
            "missing_added": missing_added,
            "missing_label_vector": missing_labels,
            "empty_added": empty_added,
            "empty_labels": empty_labels,
        }
        result["deleted_label_status"] = (
            "YES" if has_deleted_labels else "NO"
        )
        result["deleted_label_fields"] = dict(deleted_label_fields)
        result["commits_with_ge1_positive_line"] = commits_with_pos
        result["commits_with_zero_positive_line"] = commits_with_zero_pos
        result["positive_added_lines_quantiles"] = quantiles(pos_line_per_commit)
        result["added_line_count_quantiles"] = quantiles([x for x in length_added if x >= 0])
        result["_commit_ids"] = commit_ids
        result["_projects"] = project_names
        result["_pos_line_counts"] = pos_line_per_commit
        result["_added_counts"] = length_added
        return result

    # Case C: list of records
    if isinstance(obj, (list, tuple)):
        result["layout"] = "sequence"
        result["length"] = len(obj)
        if not obj:
            return result
        el0 = obj[0]
        result["element0_type"] = type(el0).__name__
        if isinstance(el0, (list, tuple)):
            result["element0_length"] = len(el0)
            result["tuple_field_types"] = [type(x).__name__ for x in el0]
            # Heuristic from JIT-Fine run.py: commit_id, idx, changed_type, label, raw, changed
            commit_ids = []
            changed_types = []
            labels = []
            for item in obj:
                if not isinstance(item, (list, tuple)) or len(item) < 4:
                    continue
                commit_ids.append(item[0])
                changed_types.append(item[2])
                labels.append(item[3])
            result["changed_type_profile"] = profile_unique_values(changed_types)
            result["label_profile"] = profile_unique_values(labels)
            result["n_unique_commits"] = len(set(commit_ids))
            result["_commit_ids"] = list(set(commit_ids))
            # per-commit aggregates for added labels
            by_commit_added_pos = defaultdict(int)
            by_commit_added = defaultdict(int)
            by_commit_deleted = defaultdict(int)
            for item in obj:
                if not isinstance(item, (list, tuple)) or len(item) < 4:
                    continue
                cid, ctype, lab = item[0], item[2], item[3]
                if ctype == "added":
                    by_commit_added[cid] += 1
                    if lab == 1 or lab is True:
                        by_commit_added_pos[cid] += 1
                elif ctype == "deleted":
                    by_commit_deleted[cid] += 1
            result["commits_with_ge1_positive_added"] = sum(
                1 for c, n in by_commit_added_pos.items() if n >= 1
            )
            result["commits_with_added_but_zero_pos"] = sum(
                1
                for c, n in by_commit_added.items()
                if n >= 1 and by_commit_added_pos.get(c, 0) == 0
            )
            result["_by_commit_added"] = dict(by_commit_added)
            result["_by_commit_added_pos"] = dict(by_commit_added_pos)
            result["_by_commit_deleted"] = dict(by_commit_deleted)
        elif isinstance(el0, dict):
            result["element0_keys"] = sorted(el0.keys())
        return result

    result["layout"] = f"unrecognized:{type(obj)}"
    return result


def strip_private(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--extract-root",
        type=Path,
        default=ROOT / "data/raw/upstream/extracted",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/data_schema/dataset_audit.json",
    )
    args = ap.parse_args()

    audit: dict[str, Any] = {
        "deserialization_isolation": "LIMITED",
        "isolation_notes": [],
        "changes": {},
        "features": {},
        "line_labels": {},
    }

    # Load all changes/features
    changes_raw = {}
    features_raw = {}
    for split in SPLITS:
        cpath = args.extract_root / f"data/jitfine/changes_{split}.pkl"
        fpath = args.extract_root / f"data/jitfine/features_{split}.pkl"
        print(f"loading {cpath.name} ...", flush=True)
        cobj = load_pickle(cpath)
        print(f"loading {fpath.name} ...", flush=True)
        fobj = load_pickle(fpath)
        cu = unpack_changes(cobj)
        fu = unpack_features(fobj)
        changes_raw[split] = cu
        features_raw[split] = fu
        audit["changes"][split] = strip_private(cu)
        audit["features"][split] = strip_private(fu)

    print("loading line labels ...", flush=True)
    ll_path = args.extract_root / "data/jitfine/changes_complete_buggy_line_level.pkl"
    ll_obj = load_pickle(ll_path)
    ll = unpack_line_labels(ll_obj)
    audit["line_labels"] = strip_private(ll)

    # Schema comparison
    ch_fps = {
        s: audit["changes"][s]["top_level"].get("schema_fingerprint")
        or content_hash(
            (
                audit["changes"][s].get("layout"),
                audit["changes"][s]["top_level"].get("python_type"),
                audit["changes"][s]["top_level"].get("length"),
            )
        )
        for s in SPLITS
    }
    # Better: structural layout equality
    def changes_struct_sig(s):
        d = audit["changes"][s]
        return content_hash(
            (
                d.get("layout"),
                d["top_level"].get("python_type"),
                d["top_level"].get("kind"),
                d.get("codes_element_types"),
                d.get("label_profile", {}).get("type_counts"),
            )
        )

    c_sigs = {s: changes_struct_sig(s) for s in SPLITS}
    audit["changes_schema_compare"] = {
        "train_vs_valid": compare_schema_fingerprints(c_sigs["train"], c_sigs["valid"])
        if c_sigs["train"] == c_sigs["valid"]
        else (
            "IDENTICAL_SCHEMA"
            if c_sigs["train"] == c_sigs["valid"]
            else "COMPATIBLE_SCHEMA"
            if audit["changes"]["train"].get("layout") == audit["changes"]["valid"].get("layout")
            else "SCHEMA_DRIFT"
        ),
        "train_vs_test": (
            "IDENTICAL_SCHEMA"
            if c_sigs["train"] == c_sigs["test"]
            else "COMPATIBLE_SCHEMA"
            if audit["changes"]["train"].get("layout") == audit["changes"]["test"].get("layout")
            else "SCHEMA_DRIFT"
        ),
        "valid_vs_test": (
            "IDENTICAL_SCHEMA"
            if c_sigs["valid"] == c_sigs["test"]
            else "COMPATIBLE_SCHEMA"
            if audit["changes"]["valid"].get("layout") == audit["changes"]["test"].get("layout")
            else "SCHEMA_DRIFT"
        ),
        "signatures": c_sigs,
    }
    f_fps = {s: audit["features"][s].get("schema_fingerprint") for s in SPLITS}
    audit["features_schema_compare"] = {
        "train_vs_valid": compare_schema_fingerprints(f_fps["train"] or "", f_fps["valid"] or "")
        if f_fps["train"] and f_fps["valid"]
        else "UNKNOWN",
        "train_vs_test": compare_schema_fingerprints(f_fps["train"] or "", f_fps["test"] or "")
        if f_fps["train"] and f_fps["test"]
        else "UNKNOWN",
        "valid_vs_test": compare_schema_fingerprints(f_fps["valid"] or "", f_fps["test"] or "")
        if f_fps["valid"] and f_fps["test"]
        else "UNKNOWN",
        "fingerprints": f_fps,
    }

    # Primary keys and intersections from changes
    id_sets = {}
    label_maps = {}
    for s in SPLITS:
        ids = changes_raw[s].get("_commit_ids") or []
        labs = changes_raw[s].get("_labels") or []
        id_sets[s] = set(ids)
        label_maps[s] = dict(zip(ids, labs))
    audit["primary_key"] = {
        "field": "commit_id_from_changes_tuple_position0",
        "uniqueness": {s: changes_raw[s].get("commit_id_dup") for s in SPLITS},
        "note": "empirically from changes pickle; confirm against features.commit_hash",
    }
    audit["split_intersections"] = {
        "train_valid": intersection_counts(id_sets["train"], id_sets["valid"]),
        "train_test": intersection_counts(id_sets["train"], id_sets["test"]),
        "valid_test": intersection_counts(id_sets["valid"], id_sets["test"]),
    }

    # Split counts
    split_summary = []
    for s in SPLITS:
        labs = changes_raw[s].get("_labels") or []
        pos = sum(1 for x in labs if x == 1 or x is True)
        neg = sum(1 for x in labs if x == 0 or x is False)
        n = len(labs)
        split_summary.append(
            {
                "split": s,
                "n": n,
                "positives": pos,
                "negatives": neg,
                "positive_rate": (pos / n) if n else None,
            }
        )
    audit["split_counts"] = {
        "by_split": split_summary,
        "n_total_author_split": sum(x["n"] for x in split_summary),
        "positives_total": sum(x["positives"] for x in split_summary),
        "negatives_total": sum(x["negatives"] for x in split_summary),
    }

    # changes ↔ features alignment
    alignment = {}
    for s in SPLITS:
        cids = changes_raw[s].get("_commit_ids") or []
        fids = features_raw[s].get("_commit_ids") or []
        same_n = len(cids) == len(fids)
        same_order = same_n and all(a == b for a, b in zip(cids, fids))
        set_c, set_f = set(cids), set(fids)
        only_c = len(set_c - set_f)
        only_f = len(set_f - set_c)
        if same_order:
            verdict = "EXACT_ALIGNMENT"
        elif set_c == set_f and not same_order:
            verdict = "KEY_ALIGNMENT_DIFFERENT_ORDER"
        elif only_c == 0 or only_f == 0:
            verdict = "PARTIAL_ALIGNMENT"
        else:
            verdict = "MISMATCH"
        # label consistency if both have labels
        label_disagree = None
        if features_raw[s].get("_labels") is not None:
            fl = dict(zip(fids, features_raw[s]["_labels"]))
            disagree = 0
            checked = 0
            for cid, lab in zip(cids, changes_raw[s].get("_labels") or []):
                if cid in fl:
                    checked += 1
                    if fl[cid] != lab:
                        # also allow 1/True etc carefully — count raw inequality only
                        if fl[cid] != lab:
                            disagree += 1
            label_disagree = {"checked": checked, "disagree_raw": disagree}
        alignment[s] = {
            "verdict": verdict,
            "changes_n": len(cids),
            "features_n": len(fids),
            "only_in_changes": only_c,
            "only_in_features": only_f,
            "label_consistency": label_disagree,
            "features_primary_id_field": features_raw[s].get("primary_id_field"),
        }
    audit["changes_features_alignment"] = alignment

    # Projects
    project_info = {}
    for s in SPLITS:
        projs = features_raw[s].get("_projects")
        if projs is None:
            project_info[s] = {"available": False}
            continue
        cids = features_raw[s].get("_commit_ids") or []
        labs = features_raw[s].get("_labels")
        if labs is None:
            labs = changes_raw[s].get("_labels") or [None] * len(cids)
        by_p = defaultdict(lambda: {"n": 0, "pos": 0})
        for cid, p, lab in zip(cids, projs, labs):
            by_p[str(p)]["n"] += 1
            if lab == 1 or lab is True:
                by_p[str(p)]["pos"] += 1
        project_info[s] = {
            "available": True,
            "n_projects": len(by_p),
            "projects": {
                k: {
                    "commits": v["n"],
                    "positives": v["pos"],
                    "positive_rate": v["pos"] / v["n"] if v["n"] else None,
                }
                for k, v in sorted(by_p.items())
            },
        }
    all_proj = set()
    for s in SPLITS:
        if project_info[s].get("available"):
            all_proj |= set(project_info[s]["projects"].keys())
    shared = None
    if all(project_info[s].get("available") for s in SPLITS):
        sets = [set(project_info[s]["projects"].keys()) for s in SPLITS]
        shared = {
            "train_valid_test": sorted(sets[0] & sets[1] & sets[2]),
            "n_overall": len(all_proj),
        }
    audit["projects"] = {"by_split": project_info, "overall": shared}

    # Temporal
    temporal = {}
    for s in SPLITS:
        times = features_raw[s].get("_times")
        projs = features_raw[s].get("_projects")
        if not times or not projs:
            temporal[s] = {"status": "TIMESTAMP_UNAVAILABLE"}
            continue
        temporal[s] = {"status": "PRESENT", "time_column": audit["features"][s].get("time_columns")}
    # per-project chronology across splits if times exist
    chrono_projects = {}
    if all(
        features_raw[s].get("_times") and features_raw[s].get("_projects") for s in SPLITS
    ):
        # parse as pandas to_datetime if possible
        per = defaultdict(lambda: {sp: [] for sp in SPLITS})
        for s in SPLITS:
            for p, t in zip(features_raw[s]["_projects"], features_raw[s]["_times"]):
                per[str(p)][s].append(pd.to_datetime(t, errors="coerce"))
        for p, d in per.items():
            def mx(xs):
                xs = [x for x in xs if pd.notna(x)]
                return max(xs) if xs else None

            def mn(xs):
                xs = [x for x in xs if pd.notna(x)]
                return min(xs) if xs else None

            mt, mv, xt, xv, mte, xtest = (
                mx(d["train"]),
                mn(d["valid"]),
                mx(d["valid"]),
                mn(d["test"]),
                mx(d["train"]),
                mn(d["test"]),
            )
            # train max <= valid min <= ... rough
            ordered = True
            issues = []
            if mt is not None and mv is not None and mt > mv:
                ordered = False
                issues.append("train_max_gt_valid_min")
            if xt is not None and xv is not None and xt > xv:
                ordered = False
                issues.append("valid_max_gt_test_min")
            # also train vs test
            if mt is not None and xv is not None and mt > xv:
                ordered = False
                issues.append("train_max_gt_test_min")
            chrono_projects[p] = {
                "class": "CHRONOLOGICALLY_ORDERED" if ordered else "OVERLAPPING_DATES",
                "issues": issues,
            }
    audit["temporal_split"] = {
        "by_split_availability": temporal,
        "per_project": chrono_projects,
        "summary": {
            "CHRONOLOGICALLY_ORDERED": sum(
                1 for v in chrono_projects.values() if v["class"] == "CHRONOLOGICALLY_ORDERED"
            ),
            "OVERLAPPING_DATES": sum(
                1 for v in chrono_projects.values() if v["class"] == "OVERLAPPING_DATES"
            ),
            "n_projects_checked": len(chrono_projects),
        },
    }

    # Line-label coverage vs test
    test_ids = id_sets["test"]
    test_labels = label_maps["test"]
    test_pos = {c for c, y in test_labels.items() if y == 1 or y is True}
    test_neg = {c for c, y in test_labels.items() if y == 0 or y is False}
    ll_ids = set(ll.get("_commit_ids") or [])
    by_added = ll.get("_by_commit_added") or {}
    by_pos = ll.get("_by_commit_added_pos") or {}
    # For nested dict layout, build maps from parallel arrays
    if not by_added and ll.get("_commit_ids") and ll.get("_added_counts") is not None:
        by_added = dict(zip(ll["_commit_ids"], ll["_added_counts"]))
        by_pos = dict(zip(ll["_commit_ids"], ll.get("_pos_line_counts") or []))

    def cov(commits):
        represented = commits & ll_ids
        with_added = {c for c in represented if by_added.get(c, 0) >= 1}
        with_pos = {c for c in represented if by_pos.get(c, 0) >= 1}
        added_zero_pos = {c for c in with_added if by_pos.get(c, 0) == 0}
        missing = commits - ll_ids
        return {
            "n": len(commits),
            "represented": len(represented),
            "ge1_added": len(with_added),
            "ge1_positive_added_label": len(with_pos),
            "added_but_zero_positive_label": len(added_zero_pos),
            "missing_from_line_label_artifact": len(missing),
        }

    audit["test_line_label_coverage"] = {
        "all_test": cov(test_ids),
        "positive_test": cov(test_pos),
        "negative_test": cov(test_neg),
    }

    # L0-L4
    # Need added counts from changes_test
    test_added = {}
    if changes_raw["test"].get("_commit_ids") and changes_raw["test"].get("_added_counts"):
        test_added = dict(
            zip(changes_raw["test"]["_commit_ids"], changes_raw["test"]["_added_counts"])
        )
    L0 = len(test_ids)
    L1 = len(test_pos)
    L2 = sum(1 for c in test_pos if test_added.get(c, 0) >= 1)
    L3 = len(test_pos & ll_ids)
    L4 = sum(1 for c in test_pos if by_pos.get(c, 0) >= 1)
    audit["localization_populations"] = {
        "L0_all_test": L0,
        "L1_gold_positive_test": L1,
        "L2_gold_positive_with_ge1_added": L2,
        "L3_gold_positive_in_line_label_artifact": L3,
        "L4_gold_positive_with_ge1_positive_added_label": L4,
        "LOCALIZATION_DENOMINATOR_DECISION": "OPEN",
        "note": "JIT-Fine original eval further conditions on model-predicted positive; not applied here.",
    }

    # Duplicates
    audit["duplicates"] = {
        "commit_ids": {s: changes_raw[s].get("commit_id_dup") for s in SPLITS},
        "change_content_hash_collisions": {},
    }
    for s in SPLITS:
        hashes = changes_raw[s].get("_code_content_hashes") or []
        c = Counter(hashes)
        multi = sum(1 for v in c.values() if v > 1)
        audit["duplicates"]["change_content_hash_collisions"][s] = {
            "n_unique_hashes": len(c),
            "n_hashes_with_multiplicity_gt1": multi,
        }

    # Zero-add by label
    zero_add = {}
    for s in SPLITS:
        ids = changes_raw[s].get("_commit_ids") or []
        labs = changes_raw[s].get("_labels") or []
        adds = changes_raw[s].get("_added_counts") or []
        dels = changes_raw[s].get("_deleted_counts") or []
        z = {"zero_added_pos": 0, "zero_added_neg": 0, "zero_deleted_pos": 0, "zero_deleted_neg": 0, "zero_both_pos": 0, "zero_both_neg": 0}
        for lab, a, d in zip(labs, adds, dels if len(dels) == len(adds) else [None] * len(adds)):
            is_pos = lab == 1 or lab is True
            if a == 0:
                z["zero_added_pos" if is_pos else "zero_added_neg"] += 1
            if d == 0:
                z["zero_deleted_pos" if is_pos else "zero_deleted_neg"] += 1
            if a == 0 and d == 0:
                z["zero_both_pos" if is_pos else "zero_both_neg"] += 1
        zero_add[s] = z
    audit["zero_add_empty"] = zero_add

    # Positives without positive line labels (among those in LL artifact)
    pos_all = set()
    for s in SPLITS:
        for c, y in label_maps[s].items():
            if y == 1 or y is True:
                pos_all.add(c)
    pos_in_ll = pos_all & ll_ids
    pos_with = sum(1 for c in pos_in_ll if by_pos.get(c, 0) >= 1)
    pos_zero = sum(1 for c in pos_in_ll if by_pos.get(c, 0) == 0)
    audit["positives_line_label_status"] = {
        "positives_in_any_split_and_ll": len(pos_in_ll),
        "with_ge1_positive_line": pos_with,
        "with_zero_positive_line": pos_zero,
    }

    # Change vs line-label text consistency via content structure hashes where possible
    # For nested LL we don't have easy per-line alignment to changes codes; report commit overlap only
    audit["change_line_label_commit_overlap"] = {
        s: {
            "changes_commits": len(id_sets[s]),
            "also_in_line_label": len(id_sets[s] & ll_ids),
            "missing_in_line_label": len(id_sets[s] - ll_ids),
        }
        for s in SPLITS
    }

    # Published comparison placeholders
    audit["published_count_comparison"] = [
        {
            "claim": "21 Java projects",
            "source": "Ni et al. ESEC/FSE 2022 §4 / provenance report",
            "published_value": 21,
            "archive_value": shared["n_overall"] if shared else None,
            "status": None,
        },
        {
            "claim": "secondary literature ~27319 commits / 2332 defective",
            "source": "DATASET_PROVENANCE_REPORT secondary citation note (not paper table total)",
            "published_value": {"commits": 27319, "defective": 2332},
            "archive_value": {
                "commits": audit["split_counts"]["n_total_author_split"],
                "defective": audit["split_counts"]["positives_total"],
            },
            "status": None,
        },
    ]
    for row in audit["published_count_comparison"]:
        if row["claim"].startswith("21"):
            av = row["archive_value"]
            row["status"] = "MATCH" if av == 21 else (
                "UNEXPLAINED_DIFFERENCE" if av is not None else "TIMESTAMP_UNAVAILABLE"
            )
            if av is None:
                row["status"] = "EXPLAINED_DIFFERENCE"
                row["explanation"] = "project field unavailable in inspected features"
            elif av != 21:
                row["explanation"] = f"archive projects={av}"
        else:
            ac = row["archive_value"]["commits"]
            ad = row["archive_value"]["defective"]
            if ac == 27319 and ad == 2332:
                row["status"] = "MATCH"
            else:
                row["status"] = "EXPLAINED_DIFFERENCE" if ac else "UNEXPLAINED_DIFFERENCE"
                row["explanation"] = (
                    "Secondary approximate totals vs author-provided train+valid+test sum; "
                    f"archive commits={ac}, defective={ad}"
                )

    # Path adequacy for test-file RQ4
    audit["file_path_adequacy_for_rq4"] = {
        "in_changes_codes": "UNKNOWN",
        "note": "see has_file_path_key_count in changes summaries",
        "has_file_path_key_count_train": audit["changes"]["train"].get("has_file_path_key_count"),
    }
    if audit["changes"]["train"].get("has_file_path_key_count", 0) > 0:
        audit["file_path_adequacy_for_rq4"]["in_changes_codes"] = "YES"
    else:
        audit["file_path_adequacy_for_rq4"]["in_changes_codes"] = "NO"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, indent=2, default=str) + "\n", encoding="utf-8")

    # CSV summaries
    split_csv = args.out.parent / "split_summary.csv"
    lines = ["split,n,positives,negatives,positive_rate"]
    for row in split_summary:
        lines.append(
            f"{row['split']},{row['n']},{row['positives']},{row['negatives']},{row['positive_rate']}"
        )
    split_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    proj_csv = args.out.parent / "project_split_summary.csv"
    plines = ["split,project,commits,positives,positive_rate"]
    for s in SPLITS:
        info = project_info[s]
        if not info.get("available"):
            continue
        for proj, st in info["projects"].items():
            plines.append(
                f"{s},{proj},{st['commits']},{st['positives']},{st['positive_rate']}"
            )
    proj_csv.write_text("\n".join(plines) + "\n", encoding="utf-8")

    ll_csv = args.out.parent / "line_label_summary.csv"
    ll_lines = [
        "metric,value",
        f"layout,{audit['line_labels'].get('layout')}",
        f"n_commits,{audit['line_labels'].get('n_commits') or audit['line_labels'].get('n_unique_commits')}",
        f"deleted_label_status,{audit['line_labels'].get('deleted_label_status')}",
        f"L0,{L0}",
        f"L1,{L1}",
        f"L2,{L2}",
        f"L3,{L3}",
        f"L4,{L4}",
        f"test_pos_represented,{audit['test_line_label_coverage']['positive_test']['represented']}",
        f"test_pos_ge1_pos_label,{audit['test_line_label_coverage']['positive_test']['ge1_positive_added_label']}",
        f"test_pos_added_zero_pos_label,{audit['test_line_label_coverage']['positive_test']['added_but_zero_positive_label']}",
        f"test_pos_missing,{audit['test_line_label_coverage']['positive_test']['missing_from_line_label_artifact']}",
    ]
    ll_csv.write_text("\n".join(ll_lines) + "\n", encoding="utf-8")

    print(json.dumps({"wrote": str(args.out), "split_counts": audit["split_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

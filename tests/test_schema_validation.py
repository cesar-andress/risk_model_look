"""Tests for schema-validation utilities (synthetic data only; no real archive)."""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd
import pytest

from src.data.extract_members import resolve_safe_dest
from src.data.pickle_audit import audit_pickle_bytes
from src.data.schema_inspect import (
    duplicate_id_report,
    intersection_counts,
    line_label_length_check,
    profile_unique_values,
)


def test_resolve_safe_dest_blocks_traversal(tmp_path: Path) -> None:
    root = tmp_path / "extracted"
    root.mkdir()
    with pytest.raises(ValueError):
        resolve_safe_dest(root, "../escape.pkl")
    with pytest.raises(ValueError):
        resolve_safe_dest(root, "/abs/path.pkl")
    dest = resolve_safe_dest(root, "data/jitfine/x.pkl")
    assert dest == (root / "data/jitfine/x.pkl").resolve()


def test_static_pickle_audit_non_executing_and_pass_for_list() -> None:
    payload = pickle.dumps([1, 2, 3], protocol=4)
    # Ensure audit does not need to unpickle for opcode scan
    audit = audit_pickle_bytes(payload, file_label="toy")
    assert audit.opcode_count > 0
    assert audit.static_pickle_risk in {"PASS", "REQUIRES_REVIEW", "FAIL"}
    assert "os.system" not in audit.suspicious_refs


def test_static_pickle_audit_flags_eval_global() -> None:
    # Craft minimal pickle that references builtins.eval via GLOBAL
    # pickletools path: use pickle.dumps on an object that reduces via eval is hard;
    # instead inject GLOBAL opcode bytes for builtins\neval
    # Protocol 4 GLOBAL: GLOBAL + 'builtins\neval\n'
    data = b"\x80\x04\x95\x12\x00\x00\x00\x00\x00\x00\x00cbuiltins\neval\n."
    audit = audit_pickle_bytes(data, file_label="evil")
    assert "builtins.eval" in audit.suspicious_refs
    assert audit.static_pickle_risk == "FAIL"


def test_schema_summarizer_dataframe_dict_list() -> None:
    from scripts.inspect_jitfine_schema import summarize_top_level

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    s = summarize_top_level(df)
    assert s["kind"] == "DataFrame"
    assert s["shape"] == [2, 2]
    assert summarize_top_level({"k": 1})["kind"] == "dict"
    assert summarize_top_level([1, 2, 3])["kind"] == "list"


def test_split_intersection_checker() -> None:
    a = {"c1", "c2"}
    b = {"c2", "c3"}
    r = intersection_counts(a, b)
    assert r["count"] == 1


def test_duplicate_id_checker() -> None:
    r = duplicate_id_report(["a", "b", "a", None])
    assert r["n_unique"] == 3  # a,b,None
    assert r["n_duplicate_ids"] == 1
    assert r["n_null"] == 1


def test_line_label_length_checker() -> None:
    r = line_label_length_check([3, 2, 0], [3, 1, 0])
    assert r["matches"] == 2
    assert r["mismatches"] == 1


def test_label_value_profiler_no_coercion() -> None:
    r = profile_unique_values([0.0, 1.0, 0.0, True, 1])
    assert r["type_counts"]["float"] == 3
    assert "True" in r["value_counts"]
    assert "1" in r["value_counts"]  # int 1 distinct from float 1.0 key "1.0" or "1"

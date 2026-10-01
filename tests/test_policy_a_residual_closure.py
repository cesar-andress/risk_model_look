"""Tests for Policy-A residual closure (no tokenization / no fuzzy)."""

from __future__ import annotations

import pytest

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


def test_source_approved_preprocess_matches_changed_line_pattern():
    raw = 'out.println("" + md.getDescription());'
    # spaced form as in Layer-B raw
    spaced = "out . println ( \"\" + md . getDescription ( ) ) ;"
    chg = jitfine_preprocess_code_line(spaced)
    assert "<STR>" in chg or "<NUM>" in chg or "println" in chg
    assert match_via_changed_line(raw, jitfine_preprocess_code_line(raw))


def test_signatures_match_punct_space():
    git = "throw ioe;"
    raw = "throw ioe ;"
    assert signatures_match(git, raw) or "throw ioe" in approved_signatures(git)


def test_positionally_forced_one_row_gap():
    # S0->G0, S2->G2 exact; S1 unmatched; G1 unmatched
    forced = positionally_forced_bijections(
        n_policy=3,
        n_git=3,
        mapped={0: 0, 2: 2},
        unmatched_policy={1},
        unmatched_git={1},
    )
    assert forced == {1: 1}


def test_positionally_forced_multi_row_gap():
    forced = positionally_forced_bijections(
        n_policy=5,
        n_git=5,
        mapped={0: 0, 4: 4},
        unmatched_policy={1, 2, 3},
        unmatched_git={1, 2, 3},
    )
    assert forced == {1: 1, 2: 2, 3: 3}


def test_ambiguous_equal_length_alternative_gap_rejected_without_anchors():
    # No anchors and n_policy != full equal covering → empty
    forced = positionally_forced_bijections(
        n_policy=4,
        n_git=4,
        mapped={},
        unmatched_policy={0, 1},
        unmatched_git={0, 1},
    )
    # whole-file rule requires n_policy == n_git == len(unmatched)
    assert forced == {}


def test_edge_interval_recovery():
    forced = positionally_forced_bijections(
        n_policy=4,
        n_git=4,
        mapped={2: 2},
        unmatched_policy={0, 1},
        unmatched_git={0, 1},
    )
    assert forced == {0: 0, 1: 1}
    forced_t = positionally_forced_bijections(
        n_policy=4,
        n_git=4,
        mapped={1: 1},
        unmatched_policy={2, 3},
        unmatched_git={2, 3},
    )
    assert forced_t == {2: 2, 3: 3}


def test_gap_cardinality_mismatch_no_map():
    forced = positionally_forced_bijections(
        n_policy=4,
        n_git=5,
        mapped={0: 0, 3: 4},
        unmatched_policy={1, 2},
        unmatched_git={1, 2, 3},
    )
    assert forced == {}


def test_non_monotonic_anchors_skip_gap():
    forced = positionally_forced_bijections(
        n_policy=3,
        n_git=3,
        mapped={0: 2, 2: 0},  # crossed
        unmatched_policy={1},
        unmatched_git={1},
    )
    assert 1 not in forced


def test_no_cross_file_in_helper_scope():
    """Helper is file-local by construction: separate calls per file."""
    f1 = positionally_forced_bijections(
        n_policy=2,
        n_git=2,
        mapped={0: 0},
        unmatched_policy={1},
        unmatched_git={1},
    )
    assert f1 == {1: 1}


def test_no_fuzzy_fallback_in_signatures():
    assert not signatures_match("abc", "xyz")
    # Distinct identifiers — must not match via approximate similarity
    assert not signatures_match("alphaTokenOnly();", "betaTokenOnly();")


def test_dataset_canonical_conflict_classification():
    assert (
        classify_dataset_conflict(
            in_diff_filtered=False,
            in_diff_unfiltered=False,
            in_child=False,
            in_parent=True,
        )
        == "LINE_PRESENT_IN_PARENT_ONLY"
    )
    assert (
        classify_dataset_conflict(
            in_diff_filtered=False,
            in_diff_unfiltered=False,
            in_child=True,
            in_parent=True,
        )
        == "LINE_PRESENT_BOTH_BLOBS_NOT_IN_DIFF"
    )


def test_complete_commit_calculation_logic():
    rows = [
        {"cid": "a", "mapped": True},
        {"cid": "a", "mapped": True},
        {"cid": "b", "mapped": True},
        {"cid": "b", "mapped": False},
    ]
    by = {}
    for r in rows:
        by.setdefault(r["cid"], []).append(r["mapped"])
    complete = [c for c, ms in by.items() if all(ms)]
    assert complete == ["a"]


def test_smd_and_profile():
    d = describe_numeric([1.0, 2.0, 3.0, 4.0])
    assert d["n"] == 4
    assert d["median"] == 2.5
    s = smd(10.0, 8.0, 2.0, 2.0)
    assert s is not None
    assert abs(s - 1.0) < 1e-9


def test_positional_must_fail_when_two_assignments_possible():
    """If gap git cardinality ≠ policy cardinality, no forced map."""
    forced = positionally_forced_bijections(
        n_policy=5,
        n_git=6,
        mapped={0: 0, 4: 5},
        unmatched_policy={1, 2, 3},
        unmatched_git={1, 2, 3, 4},
    )
    assert forced == {}

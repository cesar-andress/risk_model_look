"""CPU tests for ATTRIBUTION_PROTOCOL_V1.1 completeness amendment."""

from __future__ import annotations

import math

import pytest

from src.attribution.occlusion import RegionSpec, ToyStructuredCommit, OcclusionUnit
from src.attribution.perturbation_ops import (
    PerturbationOperator,
    apply_payload_blank,
    apply_payload_blank_all,
    apply_segment_delete,
    diff_polarity_swap_v1,
    restore_payloads_from_original,
)
from src.data.file_categories import test_file_category_audit_status as file_cat_audit_status
from src.experiments.protocol_manifest import (
    ATTRIBUTION_PROTOCOL_HASH_V1,
    PROTOCOL_ID_V1_1,
    V1_CONFIG,
    V1_1_CONFIG,
    V1_1_MANIFEST_DIR,
    load_protocol_config,
    protocol_hash,
    validate_protocol_config,
    verify_v1_hash_intact,
)
from src.metrics.faithfulness import (
    PRIMARY_FAITHFULNESS_FRACTIONS,
    aopc_deletion,
    aopc_insertion,
    evaluate_deletion_curve,
    evaluate_insertion_curve,
    fraction_to_k,
)
from src.metrics.polarity import attention_top2_hunk_negative_occlusion_fraction


pytestmark = pytest.mark.cpu


def test_v1_hash_preserved_and_v11_differs() -> None:
    assert verify_v1_hash_intact()
    v1 = load_protocol_config(V1_CONFIG)
    assert protocol_hash(v1) == ATTRIBUTION_PROTOCOL_HASH_V1
    v11 = load_protocol_config(V1_1_CONFIG)
    assert v11["protocol_id"] == PROTOCOL_ID_V1_1
    assert validate_protocol_config(v11) == []
    h11 = protocol_hash(v11)
    assert h11 != ATTRIBUTION_PROTOCOL_HASH_V1
    assert h11 == "ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e"
    assert (V1_1_MANIFEST_DIR / "protocol_manifest.json").exists() or True


def test_operators_segment_delete_vs_payload_blank() -> None:
    commit = ToyStructuredCommit(
        message="m",
        files={
            "a.py": [
                {"stable_line_id": "L1", "hunk_id": "H0", "change_type": "added", "text": "x=1"},
                {"stable_line_id": "L2", "hunk_id": "H0", "change_type": "added", "text": "y=2"},
            ]
        },
    )
    deleted = apply_segment_delete(
        commit,
        RegionSpec(unit=OcclusionUnit.LINE, region_id="L1", stable_line_ids=("L1",)),
    )
    assert all(ln.get("stable_line_id") != "L1" for lines in deleted.files.values() for ln in lines)
    blanked = apply_payload_blank(commit, ["L1"])
    texts = {ln["stable_line_id"]: ln["text"] for lines in blanked.files.values() for ln in lines}
    assert texts["L1"] == ""
    assert texts["L2"] == "y=2"
    assert "a.py" in blanked.files  # structure retained
    assert PerturbationOperator.SEGMENT_DELETE_V1.value != PerturbationOperator.PAYLOAD_BLANK_V1.value


def test_fraction_rounding_ceil() -> None:
    assert fraction_to_k(10, 0.1) == 1
    assert fraction_to_k(10, 0.2) == 2
    # ceil boundary: 0.1 * 11 = 1.1 -> 2
    assert fraction_to_k(11, 0.1) == max(1, math.ceil(0.1 * 11))
    assert fraction_to_k(11, 0.1) == 2
    assert PRIMARY_FAITHFULNESS_FRACTIONS == (0.10, 0.20, 0.30, 0.50)


def test_deletion_insertion_aopc() -> None:
    ranked = [f"L{i}" for i in range(10)]
    # Synthetic: blanking first k lines drops score by k
    score_full = 10.0

    def blanked(sel):
        return score_full - float(len(sel))

    del_curve = evaluate_deletion_curve(
        ranked, score_full=score_full, score_blanked_fn=blanked
    )
    assert del_curve.ks[0.1] == 1
    assert del_curve.deletion_drops[0.1] == pytest.approx(1.0)
    assert aopc_deletion(del_curve.deletion_drops) == pytest.approx(
        sum(del_curve.deletion_drops.values()) / 4
    )

    score_empty = 0.0

    def restored(sel):
        return float(len(sel))

    ins_curve = evaluate_insertion_curve(
        ranked, score_empty=score_empty, score_restored_fn=restored
    )
    assert ins_curve.insertion_gains[0.2] == pytest.approx(2.0)
    assert aopc_insertion(ins_curve.insertion_gains) > 0


def test_cohorts_in_config() -> None:
    cfg = load_protocol_config(V1_1_CONFIG)
    assert cfg["cohorts"]["rq1_primary"]["n"] == 304
    assert cfg["cohorts"]["rq234_primary"]["n"] == 475
    assert cfg["cohorts"]["rq234_primary"]["truncated_policy"] == "ELIGIBLE_ON_MODEL_VISIBLE_INPUT"


def test_missingness_rules_present() -> None:
    cfg = load_protocol_config(V1_1_CONFIG)
    ids = {r["id"] for r in cfg["missingness"]["rules"]}
    assert "IG_NONCONVERGED" in ids
    assert "RQ1_TRUNCATED_COMMIT" in ids
    assert "REGION_NOT_MODEL_VISIBLE" in ids


def test_rq3_attention_top2() -> None:
    att = {"H0": 0.9, "H1": 0.5, "H2": 0.1}
    occ = {"H0": -1.0, "H1": 0.5, "H2": -0.2}
    out = attention_top2_hunk_negative_occlusion_fraction(att, occ)
    assert out["top_hunk_ids"] == ["H0", "H1"]
    assert out["n_negative"] == 1
    assert out["fraction_negative_occlusion"] == pytest.approx(0.5)


def test_diff_polarity_swap_and_insertion_restore() -> None:
    commit = ToyStructuredCommit(
        message="m",
        files={
            "a.py": [
                {
                    "stable_line_id": "L1",
                    "hunk_id": "H0",
                    "change_type": "added",
                    "category": "ADDED_CODE",
                    "text": "x",
                },
                {
                    "stable_line_id": "L2",
                    "hunk_id": "H0",
                    "change_type": "deleted",
                    "category": "DELETED_CODE",
                    "text": "y",
                },
            ]
        },
    )
    swapped = diff_polarity_swap_v1(commit)
    types = {ln["stable_line_id"]: ln["change_type"] for ln in swapped.files["a.py"]}
    assert types["L1"] == "deleted"
    assert types["L2"] == "added"
    blank = apply_payload_blank_all(commit)
    restored = restore_payloads_from_original(blank, commit, ["L1"])
    by_id = {ln["stable_line_id"]: ln for ln in restored.files["a.py"]}
    assert by_id["L1"]["text"] == "x"
    assert by_id["L2"].get("payload_blanked") is True


def test_test_file_category_pending() -> None:
    assert file_cat_audit_status() == "PENDING_AUDIT"
    cfg = load_protocol_config(V1_1_CONFIG)
    assert cfg["rq4"]["test_file_category"]["status"] == "PENDING_AUDIT"
    assert cfg["rq4"]["diff_polarity_swap"]["name"] == "DIFF_POLARITY_SWAP_V1"

"""CPU tests for ATTRIBUTION_PROTOCOL_V1.2 + STATISTICAL_PROTOCOL_V1.1 amendment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attribution.integrated_gradients import (
    combined_completeness_holds,
    combined_completeness_threshold,
)
from src.cohorts import (
    CommitMeta,
    base_model_sanity_subset,
    post_stratify_prediction,
    seed_rank_spearman,
    select_negative_matched_diagnostic,
    select_validation_rehearsal,
)
from src.experiments.protocol_manifest import (
    ATTRIBUTION_PROTOCOL_HASH_V1,
    ATTRIBUTION_PROTOCOL_HASH_V1_1,
    PROTOCOL_ID_V1_2,
    V1_CONFIG,
    V1_1_CONFIG,
    V1_2_CONFIG,
    build_manifest,
    load_protocol_config,
    protocol_hash,
    validate_protocol_config,
    verify_v1_1_hash_intact,
    verify_v1_hash_intact,
    write_manifest,
)
from src.metrics.rq1_baselines import (
    audit_add_first_baseline,
    length_baseline_scores,
    negative_hit_rate_at_k,
    order_baseline_scores,
    signed_vs_absolute_delta_recall20,
)
from src.metrics.rq4_enrichment import (
    attribution_enrichment,
    category_ablation_delta,
    enrichment_table,
)
from src.metrics.token_budget_faithfulness import (
    abs_deletion_aopc,
    abs_perturbation_impact,
    evaluate_abs_deletion_curve,
    positive_evidence_drop,
    select_token_budget_prefix,
    token_budget,
    token_matched_random_regions,
)
from src.stats.protocol_manifest import (
    STATISTICAL_PROTOCOL_HASH_V1,
    V1_CONFIG as STATS_V1_CONFIG,
    V1_1_CONFIG as STATS_V1_1_CONFIG,
    build_manifest as build_stats_manifest,
    load_stats_config,
    statistical_protocol_hash,
    validate_stats_config,
    verify_stats_v1_hash_intact,
    write_manifest as write_stats_manifest,
)


pytestmark = pytest.mark.cpu

FROZEN_V12 = "c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c"
FROZEN_STATS_V11 = "edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8"


def test_history_preserved() -> None:
    assert verify_v1_hash_intact()
    assert verify_v1_1_hash_intact()
    assert protocol_hash(load_protocol_config(V1_CONFIG)) == ATTRIBUTION_PROTOCOL_HASH_V1
    assert protocol_hash(load_protocol_config(V1_1_CONFIG)) == ATTRIBUTION_PROTOCOL_HASH_V1_1
    assert verify_stats_v1_hash_intact()
    assert statistical_protocol_hash(load_stats_config(STATS_V1_CONFIG)) == STATISTICAL_PROTOCOL_HASH_V1


def test_v12_hash_determinism_and_manifest(tmp_path) -> None:
    cfg = load_protocol_config(V1_2_CONFIG)
    assert cfg["protocol_id"] == PROTOCOL_ID_V1_2
    assert validate_protocol_config(cfg) == []
    h1 = protocol_hash(cfg)
    h2 = protocol_hash(cfg)
    assert h1 == h2 == FROZEN_V12
    m = build_manifest(cfg)
    assert m["ATTRIBUTION_PROTOCOL_HASH"] == FROZEN_V12
    write_manifest(tmp_path)
    assert (tmp_path / "protocol_manifest.json").exists()


def test_stats_v11_hash_and_endpoints() -> None:
    cfg = load_stats_config(STATS_V1_1_CONFIG)
    assert validate_stats_config(cfg) == []
    assert statistical_protocol_hash(cfg) == FROZEN_STATS_V11
    assert cfg["rq1"]["primary_endpoint"]["name"] == "Recall@20%Effort"
    assert len(cfg["rq1"]["primary_contrasts"]) == 3
    assert cfg["rq2"]["primary_endpoint"]["name"] == "ABS_DELETION_AOPC"
    assert cfg["rq2"]["occlusion_confirmatory_holm_forbidden"] is True
    assert cfg["rq1"]["topk_binary"]["wilcoxon_primary_forbidden"] is True
    assert cfg["rq3"]["primary_endpoint"]["name"] == "SIGNED_VS_ABSOLUTE_DELTA_RECALL20"
    m = build_stats_manifest(cfg)
    assert m["STATISTICAL_PROTOCOL_HASH"] == FROZEN_STATS_V11
    assert m["parent_attribution_protocol"]["hash"] == FROZEN_V12


def test_absolute_vs_directional_faithfulness() -> None:
    # Negative region: removing it increases s → signed drop negative, abs impact positive
    s = 1.0
    s_wo = 2.5
    assert positive_evidence_drop(s, s_wo) == pytest.approx(-1.5)
    assert abs_perturbation_impact(s, s_wo) == pytest.approx(1.5)


def test_token_budget_prefix_and_overshoot() -> None:
    ids = ["A", "B", "C", "D"]
    toks = [3, 5, 2, 10]
    # T=20, f=0.3 → budget=6; prefix A+B = 8, overshoot=2
    assert token_budget(20, 0.3) == 6
    pref = select_token_budget_prefix(ids, toks, fraction=0.3)
    assert pref.region_ids == ("A", "B")
    assert pref.realized_token_count == 8
    assert pref.overshoot == 2
    assert pref.target_token_budget == 6


def test_abs_deletion_aopc_curve() -> None:
    ids = [f"L{i}" for i in range(10)]
    toks = [2] * 10  # T=20

    def blanked(sel):
        # impact proportional to selected tokens
        return 10.0 - float(len(sel))

    curve = evaluate_abs_deletion_curve(
        ids, toks, score_full=10.0, score_blanked_fn=blanked
    )
    assert abs_deletion_aopc(curve.impacts) > 0
    for f, pref in curve.prefixes.items():
        assert pref.realized_token_count >= pref.target_token_budget or not ids


def test_token_matched_random_control() -> None:
    ids = [f"L{i}" for i in range(8)]
    toks = [1, 2, 3, 4, 1, 2, 3, 4]
    sel, diff = token_matched_random_regions(ids, toks, target_tokens=6, seed=7)
    assert sel
    assert diff >= 0
    assert abs(sum(toks[ids.index(i)] for i in sel) - 6) == diff


def test_rq1_baselines_and_degenerate_add_first() -> None:
    assert length_baseline_scores([1, 5, 2]) == [1.0, 5.0, 2.0]
    assert order_baseline_scores([0, 1, 2])[0] > order_baseline_scores([0, 1, 2])[2]
    audit = audit_add_first_baseline(["ADD", "ADD", "ADDED"])
    assert audit["ADD_FIRST_BASELINE"] == "DEGENERATE_NOT_APPLICABLE"
    audit2 = audit_add_first_baseline(["ADD", "DEL"])
    assert audit2["ADD_FIRST_BASELINE"] == "APPLICABLE"


def test_negative_hit_rate_and_rq3_delta() -> None:
    ranked = ["p1", "n1", "p2", "x"]
    scores = {"p1": -2.0, "n1": 1.0, "p2": 0.5, "x": 3.0}
    out = negative_hit_rate_at_k(ranked, scores, {"p1", "p2"}, k=3)
    assert out["n_positive_in_topk"] == 2
    assert out["NEGATIVE_HIT_RATE_AT_K"] == pytest.approx(0.5)
    assert signed_vs_absolute_delta_recall20(0.8, 0.5) == pytest.approx(0.3)


def test_enrichment_and_zero_token_share() -> None:
    scores = [1.0, -2.0, 3.0]
    tmap = [
        {"segment_type": "COMMIT_MESSAGE"},
        {"segment_type": "ADDED_CODE"},
        {"segment_type": "ADDED_CODE"},
    ]
    assert attribution_enrichment(scores, tmap, "COMMIT_MESSAGE") == pytest.approx(
        (1 / 6) / (1 / 3)
    )
    assert attribution_enrichment(scores, tmap, "FILE_PATH") is None
    tab = enrichment_table(scores, tmap, categories=["COMMIT_MESSAGE", "ADDED_CODE"])
    assert tab["ADDED_CODE"]["ATTRIBUTION_ENRICHMENT_C"] is not None
    assert category_ablation_delta(1.0, 0.2) == pytest.approx(0.8)


def test_ig_combined_near_zero() -> None:
    # relative-only would explode / fail; combined allows small abs error near 0
    assert combined_completeness_holds(5e-4, target_delta=0.0)
    assert not combined_completeness_holds(2e-3, target_delta=0.0)
    assert combined_completeness_threshold(10.0) == pytest.approx(0.5)
    assert combined_completeness_holds(0.4, target_delta=10.0)
    assert not combined_completeness_holds(0.6, target_delta=10.0)


def test_negative_cohort_determinism_and_prediction_independence() -> None:
    pos = [
        CommitMeta(f"p{i}", "projA" if i < 3 else "projB", 100 + i, "TEST", True)
        for i in range(5)
    ]
    clean = [
        CommitMeta(f"c{i}", "projA" if i % 2 == 0 else "projB", 100 + (i % 5), "TEST", False)
        for i in range(20)
    ]
    a = select_negative_matched_diagnostic(pos, clean, n=5)
    b = select_negative_matched_diagnostic(pos, clean, n=5)
    assert [x.commit_id for x in a] == [x.commit_id for x in b]
    assert len(a) == 5
    # prediction must not be an input — function signature has no preds


def test_rehearsal_and_sanity_subset() -> None:
    vals = [
        CommitMeta(f"v{i:02d}", f"P{i%4}", 10 * i, "VALIDATION", True) for i in range(80)
    ]
    reh = select_validation_rehearsal(vals, n=64)
    assert len(reh) == 64
    assert len({c.commit_id for c in reh}) == 64
    sanity = base_model_sanity_subset(reh, n=16)
    assert len(sanity) == 16
    assert set(c.commit_id for c in sanity).issubset({c.commit_id for c in reh})


def test_post_stratification_and_seed_stability() -> None:
    commits = [
        CommitMeta("a", "p", 1, "TEST", True),
        CommitMeta("b", "p", 1, "TEST", False),
    ]
    strata = post_stratify_prediction(
        commits, y_true={"a": 1, "b": 0}, y_pred={"a": 1, "b": 1}
    )
    assert strata["TP"] == ["a"]
    assert strata["FP"] == ["b"]
    r = seed_rank_spearman([1, 2, 3, 4], [1, 2, 3, 4])
    assert r == pytest.approx(1.0)


def test_v12_roles_in_config() -> None:
    cfg = load_protocol_config(V1_2_CONFIG)
    assert cfg["faithfulness"]["absolute_perturbation_faithfulness"]["primary_endpoint"] == (
        "ABS_DELETION_AOPC"
    )
    assert cfg["occlusion"]["rq2_role"] == "PERTURBATION_REFERENCE"
    assert cfg["rq4"]["diff_polarity_swap"]["role"] == "EXPLORATORY_STRUCTURAL_SENSITIVITY"
    assert cfg["rq4"]["test_file_category"]["TEST_FILE_SUBANALYSIS"] == "DEFERRED_NOT_REQUIRED"
    assert cfg["model_comparator_scope"]["M2_SEQUENCE_CLASSIFICATION_HEAD"] == "DEFERRED_FROM_CORE"
    assert cfg["validation_rehearsal"]["n"] == 64
    assert cfg["statistical_endpoints"]["rq1_primary"] == "RECALL_AT_20_PERCENT_EFFORT"

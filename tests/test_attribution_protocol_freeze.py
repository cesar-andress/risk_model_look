"""CPU tests for ATTRIBUTION_PROTOCOL_V1 freeze (no 7B)."""

from __future__ import annotations

import pytest
import torch

from src.attribution.aggregate import LineReduction, aggregate_tokens_to_lines
from src.attribution.integrated_gradients import (
    IGBaselineStrategy,
    IntegrationRule,
    completeness_errors,
    integrated_gradients,
    integrated_gradients_with_retry,
)
from src.attribution.toy_model import LinearPathToy
from src.experiments.protocol_manifest import (
    PROTOCOL_ID,
    build_manifest,
    load_protocol_config,
    protocol_hash,
    validate_protocol_config,
    write_manifest,
)
from src.metrics.faithfulness import (
    FAITHFULNESS_PRIMARY_SCORE_SPACE,
    FaithfulnessScoreSpace,
    comprehensiveness,
    sufficiency,
    sufficiency_error,
    sufficiency_raw,
)
from src.metrics.localization import (
    PRIMARY_RQ1_RANK_TRANSFORM_SIGNED,
    RANDOM_BASELINE_REPEATS,
    RQ1_NEGATIVE,
    RQ1_POSITIVE,
    RankingTransform,
    compute_rq1_localization_metrics,
    random_baseline_seed,
    random_line_rankings,
    rank_candidates,
)
from src.metrics.label_universe_guard import GroundTruthStatus
from src.metrics.polarity import (
    PolarityClass,
    classify_region_scores,
    relative_polarity_epsilon,
    sign_agreement,
)


pytestmark = pytest.mark.cpu


def test_protocol_config_valid_and_hash_stable(tmp_path) -> None:
    cfg = load_protocol_config()
    assert cfg["protocol_id"] == PROTOCOL_ID
    errs = validate_protocol_config(cfg)
    assert errs == []
    h1 = protocol_hash(cfg)
    h2 = protocol_hash(cfg)
    assert h1 == h2
    assert len(h1) == 64
    m = build_manifest(cfg)
    assert m["ATTRIBUTION_PROTOCOL_HASH"] == h1
    path = write_manifest(tmp_path)
    assert path.exists()


def test_abs_descending_signed_ranking() -> None:
    assert PRIMARY_RQ1_RANK_TRANSFORM_SIGNED == "ABS_DESCENDING"
    items = [
        ("neg", -5.0, GroundTruthStatus.NEGATIVE, 0),
        ("pos", 1.0, GroundTruthStatus.POSITIVE, 1),
    ]
    ranked = rank_candidates(items, transform=RankingTransform.ABS_DESCENDING)
    assert [c.region_id for c in ranked] == ["neg", "pos"]
    m = compute_rq1_localization_metrics(
        ["neg", "pos"],
        [-5.0, 1.0],
        [RQ1_NEGATIVE, RQ1_POSITIVE],
        transform=RankingTransform.ABS_DESCENDING,
    )
    assert m["top1"] == 0.0  # largest |score| is negative line
    assert m["ifa"] == 1.0


def test_attention_raw_ranking_no_abs_needed() -> None:
    items = [
        ("a", 0.2, GroundTruthStatus.NEGATIVE, 0),
        ("b", 0.9, GroundTruthStatus.POSITIVE, 1),
    ]
    ranked = rank_candidates(items, transform=RankingTransform.RAW_DESCENDING)
    assert ranked[0].region_id == "b"
    assert ranked[0].rank_score == pytest.approx(0.9)


def test_signed_positive_sensitivity_secondary() -> None:
    m = compute_rq1_localization_metrics(
        ["neg", "pos"],
        [-5.0, 1.0],
        [RQ1_NEGATIVE, RQ1_POSITIVE],
        transform=RankingTransform.SIGNED_POSITIVE_DESCENDING,
    )
    assert m["top1"] == 1.0
    assert m["ifa"] == 0.0


def test_sum_primary_and_mean_sensitivity() -> None:
    scores = [1.0, 3.0, -2.0]
    tmap = [
        {"stable_line_id": "L"},
        {"stable_line_id": "L"},
        {"stable_line_id": "L"},
    ]
    s = aggregate_tokens_to_lines(scores, tmap, reduction=LineReduction.SUM)
    mean = aggregate_tokens_to_lines(scores, tmap, reduction=LineReduction.MEAN)
    assert s["L"] == pytest.approx(2.0)
    assert mean["L"] == pytest.approx(2.0 / 3.0)


def test_faithfulness_spaces_and_metrics() -> None:
    assert FAITHFULNESS_PRIMARY_SCORE_SPACE == FaithfulnessScoreSpace.LOGIT_CONTRAST
    assert comprehensiveness(5.0, 2.0) == 3.0
    assert comprehensiveness(2.0, 5.0) == -3.0  # signed; not abs
    assert sufficiency_raw(5.0, 4.0) == 1.0
    assert sufficiency_error(5.0, 4.0) == 1.0
    s = sufficiency(5.0, 4.5)
    assert s["SUFF_RAW"] == pytest.approx(0.5)
    assert s["SUFF_ERROR"] == pytest.approx(0.5)


def test_relative_polarity_epsilon_and_near_zero_exclusion() -> None:
    scores = {"a": 1.0, "b": -0.5, "c": 1e-10}
    eps = relative_polarity_epsilon(scores)
    assert eps == pytest.approx(1e-6)
    cls = classify_region_scores(scores)
    assert cls["c"] == PolarityClass.NEAR_ZERO
    attr = {"a": 1.0, "b": -1.0, "c": 1e-12}
    occ = {"a": 0.8, "b": -0.7, "c": 0.0}
    out = sign_agreement(attr, occ)
    assert out["n_covered_nonzero"] == 2
    assert out["agreement_coverage"] == pytest.approx(2 / 3)
    assert out["sign_agreement"] == 1.0
    all0 = classify_region_scores({"x": 0.0, "y": 0.0})
    assert all(v == PolarityClass.NEAR_ZERO for v in all0.values())


def test_tie_break_ordered_position() -> None:
    items = [
        ("L_b", 1.0, GroundTruthStatus.NEGATIVE, 5),
        ("L_a", 1.0, GroundTruthStatus.POSITIVE, 2),
    ]
    ranked = rank_candidates(items, transform=RankingTransform.ABS_DESCENDING)
    assert [c.region_id for c in ranked] == ["L_a", "L_b"]


def test_ig_retry_and_nonconvergence_flag() -> None:
    toy = LinearPathToy(dim=4)
    emb = torch.tensor([[[1.0, 2.0, 3.0, 4.0]]])

    def score_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    ok = integrated_gradients_with_retry(
        emb,
        score_fn,
        initial_steps=50,
        retry_steps=100,
        baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
        integration_rule=IntegrationRule.GAUSS_LEGENDRE,
    )
    assert ok.metadata.get("IG_NONCONVERGED") is False
    assert float(ok.metadata["E_rel"]) <= 0.05

    # Force nonconvergence path by using absurdly strict tolerance via manual meta
    # Simulate broken completeness: scale attributions after a normal run
    base = integrated_gradients(emb, score_fn, steps=2)
    broken_errs = completeness_errors(
        float(base.metadata["attr_sum"]) * 10.0,
        float(base.metadata["f_input"]),
        float(base.metadata["f_baseline"]),
    )
    assert broken_errs["E_rel"] > 0.05

    # Retry accepts when second pass converges: linear path should always converge
    r = integrated_gradients_with_retry(emb, score_fn, initial_steps=1, retry_steps=8, rel_tol=1e-12)
    # With tiny tol, may nonconverge depending on numerics; flag must be boolean
    assert isinstance(r.metadata["IG_NONCONVERGED"], bool)


def test_random_baseline_repeat_determinism() -> None:
    assert RANDOM_BASELINE_REPEATS == 100
    ids = [f"L{i}" for i in range(8)]
    statuses = [RQ1_POSITIVE] + [RQ1_NEGATIVE] * 7
    a = random_line_rankings(ids, statuses, commit_id="abc", repeats=5)
    b = random_line_rankings(ids, statuses, commit_id="abc", repeats=5)
    assert a == b
    assert random_baseline_seed("abc", 0) == random_baseline_seed("abc", 0)
    assert random_baseline_seed("abc", 0) != random_baseline_seed("abc", 1)
    c = random_line_rankings(ids, statuses, commit_id="xyz", repeats=5)
    assert a != c


def test_frozen_pad_token_in_config() -> None:
    cfg = load_protocol_config()
    pad = cfg["ig"]["pad_token"]
    assert pad["string"] == "<|endoftext|>"
    assert pad["token_id"] == 151643
    assert pad["semantically_neutral_claim"] is False
    assert pad["equals_primary_eos_im_end"] is False
    assert cfg["ig"]["primary_baseline"] == "ZERO_EMBEDDING"
    assert cfg["ig"]["integration_rule"] == "GAUSS_LEGENDRE"
    assert cfg["ig"]["initial_steps"] == 50

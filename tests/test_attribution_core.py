"""CPU-safe attribution core tests (no 7B models)."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from src.attribution.attention import (
    AttentionAttributionConfig,
    HeadAggregation,
    LayerSelection,
    QueryPositionPolicy,
    attention_token_scores_from_maps,
    resolve_query_index,
)
from src.attribution.gradients import grad_x_input_token_scores, vanilla_gradient_token_scores
from src.attribution.integrated_gradients import (
    IGBaselineStrategy,
    completeness_holds,
    integrated_gradients,
)
from src.attribution.occlusion import (
    OcclusionUnit,
    RegionSpec,
    ToyStructuredCommit,
    make_line_region,
    occlude_region,
    remove_region_structured,
    signed_occlusion_delta,
    default_toy_scorer,
)
from src.attribution.targets import (
    p_buggy_from_logits,
    risk_logit_contrast,
    verify_logit_odds_identity,
)
from src.attribution.toy_model import LinearPathToy, TinyCausalScorer


pytestmark = pytest.mark.cpu


def test_risk_logit_odds_identity_grid() -> None:
    for l0, l1 in [(-1.0, 2.0), (0.0, 0.0), (3.0, -1.5), (10.0, 10.1), (-5.0, -5.2)]:
        info = verify_logit_odds_identity(l0, l1, atol=1e-9, rtol=1e-9)
        assert info["ok"]
        p = p_buggy_from_logits(l0, l1)
        assert 0.0 < p < 1.0 or abs(p - 0.5) < 1e-12 or p == pytest.approx(
            1.0 / (1.0 + np.exp(-(l1 - l0)))
        )


def test_risk_contrast_pure() -> None:
    assert risk_logit_contrast(1.0, 4.0) == 3.0


def test_query_position_requires_classification_index() -> None:
    with pytest.raises(ValueError):
        resolve_query_index(
            policy=QueryPositionPolicy.FIRST_ASSISTANT_CLASSIFICATION_TOKEN,
            classification_query_index=None,
            explicit_query_index=None,
            seq_len=10,
        )
    assert (
        resolve_query_index(
            policy=QueryPositionPolicy.FIRST_ASSISTANT_CLASSIFICATION_TOKEN,
            classification_query_index=7,
            explicit_query_index=None,
            seq_len=10,
        )
        == 7
    )


def test_attention_last_mean_shapes() -> None:
    # (layers, heads, q, k)
    maps = np.zeros((3, 2, 5, 5), dtype=np.float64)
    maps[-1, 0, 4, :] = [0.1, 0.2, 0.3, 0.4, 0.0]
    maps[-1, 1, 4, :] = [0.0, 0.0, 0.0, 0.0, 1.0]
    cfg = AttentionAttributionConfig(
        layer_selection=LayerSelection.LAST,
        head_aggregation=HeadAggregation.MEAN,
        query_position_policy=QueryPositionPolicy.FIRST_ASSISTANT_CLASSIFICATION_TOKEN,
        signed=False,
    )
    res = attention_token_scores_from_maps(maps, config=cfg, classification_query_index=4)
    assert res.signed is False
    assert len(res.token_scores) == 5
    assert res.token_scores[4] == pytest.approx(0.5)
    assert res.metadata["query_index"] == 4


def test_gradient_and_grad_x_input_signs() -> None:
    toy = LinearPathToy(dim=4)
    # embeddings: token0 positive via e0·w, token1 negative via e1·w
    emb = torch.tensor([[[1.0, 0, 0, 0], [0.0, 2.0, 0, 0]]], requires_grad=True)

    def score_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    g = vanilla_gradient_token_scores(emb, score_fn)
    assert g.signed is True
    # For s = sum_{t,d} e_{t,d} w_d, ∂s/∂e_{t,d} = w_d for every t,
    # so sum_d grad is identical across tokens (= sum w).
    w_sum = float(toy.w.detach().sum())
    assert g.token_scores[0] == pytest.approx(w_sum)
    assert g.token_scores[1] == pytest.approx(w_sum)

    gxi = grad_x_input_token_scores(emb, score_fn)
    assert gxi.signed is True
    assert gxi.token_scores[0] == pytest.approx(1.0)  # 1 * 1
    assert gxi.token_scores[1] == pytest.approx(-1.0)  # 2 * -0.5
    # Core must not abs
    assert gxi.token_scores[1] < 0


def test_ig_completeness_toy() -> None:
    toy = LinearPathToy(dim=4)
    emb = torch.tensor([[[1.0, 2.0, 3.0, 4.0], [0.5, -1.0, 0.0, 2.0]]])

    def score_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    from src.attribution.integrated_gradients import (
        IGBaselineStrategy,
        IntegrationRule,
        completeness_holds,
        integrated_gradients,
    )

    res = integrated_gradients(
        emb,
        score_fn,
        steps=32,
        baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
        integration_rule=IntegrationRule.GAUSS_LEGENDRE,
    )
    assert res.signed is True
    assert completeness_holds(res, rel_tol=1e-4)


def test_ig_interpolation_chunk_matches_sequential() -> None:
    toy = LinearPathToy(dim=4)
    emb = torch.tensor([[[1.0, 2.0, 3.0, 4.0], [0.5, -1.0, 0.0, 2.0]]])

    def score_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    from src.attribution.integrated_gradients import (
        IGBaselineStrategy,
        IntegrationRule,
        integrated_gradients,
    )

    a = integrated_gradients(
        emb,
        score_fn,
        steps=8,
        baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
        integration_rule=IntegrationRule.GAUSS_LEGENDRE,
        interpolation_chunk=1,
    )
    b = integrated_gradients(
        emb,
        score_fn,
        steps=8,
        baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
        integration_rule=IntegrationRule.GAUSS_LEGENDRE,
        interpolation_chunk=4,
    )
    assert a.token_scores == pytest.approx(b.token_scores, abs=1e-5, rel=1e-5)


def test_ig_completeness_fails_when_broken() -> None:
    toy = LinearPathToy(dim=4)
    emb = torch.tensor([[[1.0, 1.0, 1.0, 1.0]]])

    def score_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    from src.attribution.integrated_gradients import (
        IGBaselineStrategy,
        completeness_holds,
        integrated_gradients,
    )

    res = integrated_gradients(
        emb, score_fn, steps=8, baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING
    )
    broken = type(res)(
        method_name=res.method_name,
        score_space=res.score_space,
        signed=res.signed,
        target_definition=res.target_definition,
        token_scores=[2.0 * x for x in res.token_scores],
        metadata={
            **dict(res.metadata),
            "sum_attributions": 2.0 * float(res.metadata["sum_attributions"]),
            "attr_sum": 2.0 * float(res.metadata["attr_sum"]),
            "E_rel": 1.0,
            "E_abs": 999.0,
            "completeness_gap": 2.0 * float(res.metadata["sum_attributions"])
            - float(res.metadata["completeness_target"]),
            "IG_NONCONVERGED": False,
        },
    )
    assert not completeness_holds(broken, rel_tol=1e-5)


def test_signed_occlusion_convention() -> None:
    effects = {"L_pos": 2.0, "L_neg": -1.0, "L_zero": 0.0}
    commit = ToyStructuredCommit(
        message="fix",
        files={
            "a.py": [
                {"stable_line_id": "L_pos", "hunk_id": "H0", "text": "x=1"},
                {"stable_line_id": "L_neg", "hunk_id": "H0", "text": "y=2"},
                {"stable_line_id": "L_zero", "hunk_id": "H0", "text": "z=3"},
            ]
        },
    )
    score_fn = default_toy_scorer(effects)
    r = occlude_region(
        commit,
        make_line_region("L_pos"),
        score_fn=score_fn,
        remove_fn=remove_region_structured,
    )
    assert r.delta == pytest.approx(2.0)
    assert r.supports_buggy
    r2 = occlude_region(
        commit,
        make_line_region("L_neg"),
        score_fn=score_fn,
        remove_fn=remove_region_structured,
    )
    assert r2.delta == pytest.approx(-1.0)
    assert r2.suppresses_buggy
    assert signed_occlusion_delta(5.0, 3.0) == 2.0


def test_occlusion_units_api() -> None:
    for u in OcclusionUnit:
        assert isinstance(u.value, str)
    commit = ToyStructuredCommit(
        message="hello",
        files={"f.py": [{"stable_line_id": "L1", "hunk_id": "H1", "text": "a"}]},
    )
    msg_region = RegionSpec(unit=OcclusionUnit.MESSAGE, region_id="msg", include_message=True)
    out = remove_region_structured(commit, msg_region)
    assert out.message == ""


def test_tiny_causal_attention_maps() -> None:
    m = TinyCausalScorer(dim=8, vocab=16, n_layers=2, n_heads=2)
    ids = torch.tensor([[1, 2, 3, 4]])
    emb = m.embeddings(ids)
    maps = m.attention_maps(emb)
    assert maps.shape == (2, 2, 4, 4)
    # classification query = last position
    q = 3
    cfg = AttentionAttributionConfig(
        layer_selection=LayerSelection.FINAL_K_MEAN,
        final_k=2,
        head_aggregation=HeadAggregation.MEAN,
        signed=False,
    )
    res = attention_token_scores_from_maps(
        maps.detach().numpy(), config=cfg, classification_query_index=q
    )
    assert len(res.token_scores) == 4

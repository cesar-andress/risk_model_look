"""End-to-end synthetic attribution regression (CPU only)."""

from __future__ import annotations

import pytest
import torch

from src.attribution.aggregate import LineReduction, aggregate_tokens_to_lines
from src.attribution.gradients import grad_x_input_token_scores
from src.attribution.occlusion import (
    ToyStructuredCommit,
    default_toy_scorer,
    make_line_region,
    occlude_region,
    remove_region_structured,
)
from src.attribution.toy_model import LinearPathToy
from src.metrics.localization import (
    RQ1_NEGATIVE,
    RQ1_POSITIVE,
    RankingTransform,
    compute_rq1_localization_metrics,
)
from src.metrics.polarity import sign_agreement
from src.metrics.surface_cues import category_mass_summary


pytestmark = pytest.mark.cpu


def _toy_commit() -> tuple[ToyStructuredCommit, dict[str, float]]:
    """One message, one file, one hunk, ADD/DEL lines with known effects."""
    effects = {
        "ADD_BUG": 3.0,  # positive risk
        "DEL_CLEAN": -2.0,  # negative risk
        "ADD_NEUTRAL": 0.0,  # no effect
        "__message__": 0.0,
    }
    commit = ToyStructuredCommit(
        message="fix null deref",
        files={
            "Foo.java": [
                {
                    "stable_line_id": "ADD_BUG",
                    "hunk_id": "H0",
                    "change_type": "added",
                    "text": "x.f();",
                    "category": "ADDED_CODE",
                },
                {
                    "stable_line_id": "DEL_CLEAN",
                    "hunk_id": "H0",
                    "change_type": "deleted",
                    "text": "if (x!=null)",
                    "category": "DELETED_CODE",
                },
                {
                    "stable_line_id": "ADD_NEUTRAL",
                    "hunk_id": "H0",
                    "change_type": "added",
                    "text": "int y=0;",
                    "category": "ADDED_CODE",
                },
            ]
        },
    )
    return commit, effects


def test_synthetic_attribution_e2e() -> None:
    commit, effects = _toy_commit()
    score_fn = default_toy_scorer(effects)

    # --- tokens / attributions via Grad×Input on a linear embedding path ---
    # Map 4 tokens: msg, add_bug, del_clean, add_neutral
    toy = LinearPathToy(dim=4)
    # Construct embeddings so Grad×Input token scores match intended polarity:
    # token scores ≈ [0, +3, -2, 0] after sum_d e*w with w=[1,-0.5,0.25,0]
    emb = torch.zeros(1, 4, 4)
    emb[0, 1, 0] = 3.0  # → score contrib +3
    emb[0, 2, 1] = 4.0  # w1=-0.5 → contrib -2
    emb[0, 3, :] = 0.0

    def s_fn(e: torch.Tensor) -> torch.Tensor:
        return toy.score(e)

    attr = grad_x_input_token_scores(emb, s_fn)
    assert attr.signed is True
    token_scores = list(attr.token_scores)
    assert token_scores[1] == pytest.approx(3.0)
    assert token_scores[2] == pytest.approx(-2.0)
    assert token_scores[3] == pytest.approx(0.0)

    token_map = [
        {"segment_type": "COMMIT_MESSAGE", "stable_line_id": None},
        {"segment_type": "ADDED_CODE", "stable_line_id": "ADD_BUG"},
        {"segment_type": "DELETED_CODE", "stable_line_id": "DEL_CLEAN"},
        {"segment_type": "ADDED_CODE", "stable_line_id": "ADD_NEUTRAL"},
    ]
    line_scores = aggregate_tokens_to_lines(
        token_scores, token_map, reduction=LineReduction.SUM
    )
    assert line_scores["ADD_BUG"] == pytest.approx(3.0)
    assert line_scores["DEL_CLEAN"] == pytest.approx(-2.0)
    assert line_scores["ADD_NEUTRAL"] == pytest.approx(0.0)

    # --- signed occlusion ---
    d_pos = occlude_region(
        commit,
        make_line_region("ADD_BUG"),
        score_fn=score_fn,
        remove_fn=remove_region_structured,
    )
    d_neg = occlude_region(
        commit,
        make_line_region("DEL_CLEAN"),
        score_fn=score_fn,
        remove_fn=remove_region_structured,
    )
    d_zero = occlude_region(
        commit,
        make_line_region("ADD_NEUTRAL"),
        score_fn=score_fn,
        remove_fn=remove_region_structured,
    )
    assert d_pos.delta == pytest.approx(3.0)
    assert d_neg.delta == pytest.approx(-2.0)
    assert d_zero.delta == pytest.approx(0.0)

    # --- RQ1 ranking (synthetic labels) ---
    m = compute_rq1_localization_metrics(
        ["ADD_BUG", "DEL_CLEAN", "ADD_NEUTRAL"],
        [line_scores["ADD_BUG"], line_scores["DEL_CLEAN"], line_scores["ADD_NEUTRAL"]],
        [RQ1_POSITIVE, RQ1_NEGATIVE, RQ1_NEGATIVE],
        transform=RankingTransform.SIGNED_DESCENDING,
    )
    assert m["top1"] == 1.0
    assert m["ifa"] == 0.0

    # --- polarity agreement attribution vs occlusion ---
    occ = {
        "ADD_BUG": d_pos.delta,
        "DEL_CLEAN": d_neg.delta,
        "ADD_NEUTRAL": d_zero.delta,
    }
    agree = sign_agreement(line_scores, occ)
    assert agree["sign_agreement"] == 1.0
    assert agree["caveat"] == "not_causal_correctness"

    # --- RQ4 category aggregation ---
    mass = category_mass_summary(token_scores, token_map)
    assert mass["signed_sum"]["ADDED_CODE"] == pytest.approx(3.0)
    assert mass["signed_sum"]["DELETED_CODE"] == pytest.approx(-2.0)
    assert mass["absolute_mass"]["ADDED_CODE"] == pytest.approx(3.0)

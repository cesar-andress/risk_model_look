"""RQ2 faithfulness metric tests (CPU)."""

from __future__ import annotations

import pytest

from src.metrics.faithfulness import (
    DEFAULT_PERTURBATION_FRACTIONS,
    FaithfulnessScoreSpace,
    comprehensiveness,
    evaluate_removal_curve,
    length_matched_random_selection,
    random_region_selection,
    sufficiency,
)


pytestmark = pytest.mark.cpu


def test_comprehensiveness_definition() -> None:
    assert comprehensiveness(5.0, 2.0) == 3.0


def test_sufficiency_orientations_documented() -> None:
    s = sufficiency(5.0, 4.5)
    assert s["orientation_raw"] == "lower_is_more_sufficient"
    assert s["sufficiency_raw_full_minus_region_only"] == pytest.approx(0.5)
    assert s["sufficiency_higher_better"] == pytest.approx(-0.5)


def test_perturbation_curve_defaults() -> None:
    regions = [f"r{i}" for i in range(20)]
    effects = {r: 1.0 for r in regions}
    effects["r0"] = 5.0

    def without(sel):
        return sum(v for k, v in effects.items() if k not in sel)

    def only(sel):
        return sum(effects[k] for k in sel)

    curve = evaluate_removal_curve(
        regions,
        score_full=sum(effects.values()),
        score_without_fn=without,
        score_only_fn=only,
        space=FaithfulnessScoreSpace.LOGIT_CONTRAST,
    )
    assert curve.fractions == DEFAULT_PERTURBATION_FRACTIONS
    assert 0.2 in curve.comprehensiveness_values
    assert curve.comprehensiveness_values[0.05] > 0


def test_random_baseline_deterministic() -> None:
    ids = [f"L{i}" for i in range(50)]
    a = random_region_selection(ids, 5, seed=123)
    b = random_region_selection(ids, 5, seed=123)
    c = random_region_selection(ids, 5, seed=124)
    assert a == b
    assert a != c
    assert len(a) == 5


def test_length_matched_token_budget() -> None:
    ids = [f"L{i}" for i in range(10)]
    toks = [10] * 10
    sel = length_matched_random_selection(
        ids, n_lines=3, seed=0, token_counts=toks, token_budget=30
    )
    assert len(sel) == 3
    # all tokens 10 → any 3 lines sum to 30
    assert sum(toks[ids.index(x)] for x in sel) == 30

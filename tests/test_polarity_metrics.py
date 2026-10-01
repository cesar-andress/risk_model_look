"""RQ3 polarity / sign-agreement tests (CPU)."""

from __future__ import annotations

import pytest

from src.metrics.polarity import polarity_summary, sign_agreement
from src.metrics.surface_cues import category_mass_summary
from src.data.file_categories import FileCategory, get_default_classifier


pytestmark = pytest.mark.cpu


def test_polarity_requires_epsilon() -> None:
    s = polarity_summary({"a": 1.0, "b": -0.5, "c": 0.001}, epsilon=0.01)
    assert s.fraction_positive == pytest.approx(1 / 3)
    assert s.fraction_negative == pytest.approx(1 / 3)
    assert s.fraction_near_zero == pytest.approx(1 / 3)


def test_sign_agreement_not_causal_claim() -> None:
    attr = {"L1": 2.0, "L2": -1.0, "L3": 0.0}
    occ = {"L1": 1.5, "L2": -0.2, "L3": 0.01}
    out = sign_agreement(attr, occ, epsilon=0.05)
    assert out["caveat"] == "not_causal_correctness"
    assert out["sign_agreement"] == 1.0
    assert out["n_covered_nonzero"] == 2


def test_surface_category_mass() -> None:
    scores = [1.0, -0.5, 2.0, 0.25]
    tmap = [
        {"segment_type": "ADDED_CODE", "stable_line_id": "a"},
        {"segment_type": "DELETED_CODE", "stable_line_id": "b"},
        {"segment_type": "COMMIT_MESSAGE"},
        {"segment_type": "STRUCTURAL_MARKUP"},
    ]
    mass = category_mass_summary(scores, tmap)
    assert mass["signed_sum"]["ADDED_CODE"] == 1.0
    assert mass["absolute_mass"]["DELETED_CODE"] == 0.5
    assert mass["normalized_absolute_mass"]["COMMIT_MESSAGE"] == pytest.approx(2.0 / 3.75)


def test_file_classifier_scaffold_unknown() -> None:
    clf = get_default_classifier()
    assert clf.categorize("src/test/Foo.java") == FileCategory.UNKNOWN
    assert clf.categorize("src/main/Foo.java") == FileCategory.UNKNOWN

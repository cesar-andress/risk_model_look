"""Guards and frozen semantics for the validation attribution rehearsal."""

from __future__ import annotations

import pytest

from src.attribution.attention import LayerSelection, select_layers
from src.cohorts import CommitMeta, select_validation_rehearsal
from src.experiments.aggregate_attribution_results import aggregate_method_results
from src.experiments.rehearsal_pipeline import refuse_test_split, sha256_json


def test_last4_mean_uses_final_four_layers() -> None:
    ids = select_layers(28, layer_selection=LayerSelection.FINAL_K_MEAN, final_k=4)
    assert ids == [24, 25, 26, 27]
    last = select_layers(28, layer_selection=LayerSelection.LAST, final_k=1)
    assert last == [27]


def test_refuse_test_split() -> None:
    with pytest.raises(RuntimeError, match="TEST"):
        refuse_test_split([{"split": "test", "commit_id": "x"}])
    refuse_test_split([{"split": "valid", "commit_id": "x"}])


def test_rehearsal_rows_not_aggregatable_as_rq(tmp_path) -> None:
    p = tmp_path / "x.jsonl"
    p.write_text(
        '{"method":"attention","PURPOSE":"REHEARSAL","NOT_TEST_RESULT":true,"status":"DONE"}\n',
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="rehearsal"):
        aggregate_method_results(p)


def test_cohort_selector_deterministic() -> None:
    vals = [
        CommitMeta(f"v{i:03d}", f"P{i%5}", 8 * i + 3, "VALIDATION", True) for i in range(120)
    ]
    a = [c.commit_id for c in select_validation_rehearsal(vals, n=64)]
    b = [c.commit_id for c in select_validation_rehearsal(vals, n=64)]
    assert a == b
    assert len(a) == 64


def test_sha256_json_stable() -> None:
    assert sha256_json({"a": 1, "b": [2]}) == sha256_json({"b": [2], "a": 1})

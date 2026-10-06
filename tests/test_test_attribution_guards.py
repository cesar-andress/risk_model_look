from src.experiments.missingness_validity import attribution_job_is_valid, faith_aopc_is_valid
from src.experiments.rehearsal_pipeline import refuse_test_split
from src.experiments.test_io import require_test_split
import pytest


def test_rehearsal_still_blocks_test() -> None:
    with pytest.raises(RuntimeError, match="TEST"):
        refuse_test_split([{"split": "test", "commit_id": "x"}])


def test_test_path_requires_test_split() -> None:
    require_test_split([{"split": "test", "commit_id": "x"}])
    with pytest.raises(RuntimeError, match="non-TEST"):
        require_test_split([{"split": "valid", "commit_id": "x"}])


def test_ig_nonconverged_cannot_enter_method_valid_contrast() -> None:
    bad = {
        "status": "NONCONVERGED",
        "missingness_code": "IG_NONCONVERGED",
        "ig": {"IG_NONCONVERGED": True, "retry_applied": True},
        "rq1": {"recall_at_20pct_effort": 0.25},
        "line_scores_sum": {"L1": 1.0},
    }
    assert attribution_job_is_valid(bad, "ig") is False
    ok = {
        "status": "DONE",
        "missingness_code": "OK",
        "ig": {"IG_NONCONVERGED": False, "retry_applied": True},
        "rq1": {"recall_at_20pct_effort": 0.25},
    }
    assert attribution_job_is_valid(ok, "ig") is True
    assert attribution_job_is_valid({"status": "DONE", "missingness_code": "OK"}, "attention") is True
    faith_ok_on_bad_ig = {
        "missingness_code": "OK",
        "aopc": 0.4,
        "ranking_from": {
            "attribution_status": "NONCONVERGED",
            "attribution_missingness": "IG_NONCONVERGED",
        },
    }
    assert faith_aopc_is_valid(faith_ok_on_bad_ig, "ig", bad) is False
    faith_ok_on_ok_ig = {
        "missingness_code": "OK",
        "aopc": 0.4,
        "ranking_from": {"attribution_status": "DONE", "attribution_missingness": "OK"},
    }
    assert faith_aopc_is_valid(faith_ok_on_ok_ig, "ig", ok) is True

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

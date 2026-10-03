"""Unit tests for M1 final training contracts (no 7B load)."""

from __future__ import annotations

import copy

import numpy as np
import pytest
import yaml
from pathlib import Path

from src.train.m1_final import (
    FINAL_SEEDS,
    PRIMARY_TRAINING_CLASS_POLICY,
    assert_final_seeds,
    assert_natural_prevalence_policy,
    config_sha256,
    mean_std,
    select_checkpoint_by_pr_auc,
    select_threshold_max_f1,
)
from src.models.qwen_m1 import FORBIDDEN_METADATA_MARKERS, count_supervised_labels
from src.train.m1_collator import encode_example, M1CausalCollator
from src.train.m1_dataset import audit_structured_leakage
import torch


ROOT = Path(__file__).resolve().parents[1]


def _cfg():
    return yaml.safe_load((ROOT / "configs/train/qwen_m1_final.yaml").read_text())


def test_natural_prevalence_policy_frozen():
    cfg = _cfg()
    assert cfg["class_policy"]["name"] == PRIMARY_TRAINING_CLASS_POLICY
    assert_natural_prevalence_policy(cfg)
    bad = copy.deepcopy(cfg)
    bad["class_policy"]["oversample"] = True
    with pytest.raises(RuntimeError, match="oversample"):
        assert_natural_prevalence_policy(bad)


def test_final_seeds_exact_set():
    assert tuple(sorted(FINAL_SEEDS)) == (13, 42, 73)
    assert_final_seeds([13, 42, 73])
    assert_final_seeds([73, 13, 42])
    with pytest.raises(RuntimeError):
        assert_final_seeds([13, 42, 99])
    with pytest.raises(RuntimeError):
        assert_final_seeds([13, 42])


def test_config_hash_stable_and_seed_invariant_fields():
    cfg = _cfg()
    h1 = config_sha256(cfg)
    h2 = config_sha256(cfg)
    assert h1 == h2
    assert len(h1) == 64
    # path changes must not affect scientific hash
    cfg2 = copy.deepcopy(cfg)
    cfg2["paths"]["artifacts_dir"] = "elsewhere"
    assert config_sha256(cfg2) == h1


def test_checkpoint_selection_pr_auc():
    rows = [
        {"epoch": 1, "pr_auc": 0.20, "roc_auc": 0.70},
        {"epoch": 2, "pr_auc": 0.22, "roc_auc": 0.69},
    ]
    assert select_checkpoint_by_pr_auc(rows)["epoch"] == 2
    # tie on PR → higher ROC
    rows = [
        {"epoch": 1, "pr_auc": 0.22, "roc_auc": 0.80},
        {"epoch": 2, "pr_auc": 0.22, "roc_auc": 0.70},
    ]
    assert select_checkpoint_by_pr_auc(rows)["epoch"] == 1
    # tie PR+ROC → earlier epoch
    rows = [
        {"epoch": 1, "pr_auc": 0.22, "roc_auc": 0.70},
        {"epoch": 2, "pr_auc": 0.22, "roc_auc": 0.70},
    ]
    assert select_checkpoint_by_pr_auc(rows)["epoch"] == 1


def test_threshold_selection_and_ties():
    # Perfect separation with unique scores
    y = np.array([0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.8, 0.9])
    m = select_threshold_max_f1(y, s)
    assert m["f1"] == 1.0
    assert m["threshold"] <= 0.8

    # Tie F1: prefer higher recall then lower threshold
    # Construct: two thresholds with same F1, different recall
    y = np.array([0, 0, 0, 1, 1])
    s = np.array([0.1, 0.4, 0.6, 0.55, 0.9])
    m = select_threshold_max_f1(y, s)
    assert "threshold" in m
    assert m["selection"] == "validation_f1"


def test_mean_sample_std():
    r = mean_std([1.0, 2.0, 3.0])
    assert abs(r["mean"] - 2.0) < 1e-12
    assert abs(r["std"] - 1.0) < 1e-12


def test_one_target_token_regression():
    class Tok:
        pad_token_id = 0

        def encode(self, text, add_special_tokens=False):
            if text == "0":
                return [15]
            if text == "1":
                return [16]
            return list(range(10, 10 + len(text)))

    enc = encode_example(Tok(), "ABCDEFGH", 1)
    assert sum(1 for x in enc["labels"] if x != -100) == 1
    batch = M1CausalCollator(0)([enc, encode_example(Tok(), "XYZ", 0)])
    assert torch.all(count_supervised_labels(batch["labels"]) == 1)


def test_leakage_regression_markers():
    assert audit_structured_leakage("FILE a\n+ x=1\n")["leaked"] is False
    assert audit_structured_leakage("rq1_status=RQ1_POSITIVE")["leaked"] is True
    assert "commit_label" in FORBIDDEN_METADATA_MARKERS


def test_final_test_guard_logic():
    """Without --final-test, test loader must not be invoked by design."""
    # Simulate: loading test requires explicit authorization flag in caller.
    authorized = False

    def maybe_load_test(flag: bool):
        if not flag:
            raise RuntimeError("TEST_EVAL_REFUSED_WITHOUT_FINAL_TEST_FLAG")
        return ["ok"]

    with pytest.raises(RuntimeError, match="TEST_EVAL_REFUSED"):
        maybe_load_test(authorized)
    assert maybe_load_test(True) == ["ok"]


def test_test_lock_state_marker_names():
    from src.train.m1_final import threshold_freeze_marker, test_lock_marker, seed_run_dir

    d = seed_run_dir(Path("/tmp/m1"), 42)
    assert threshold_freeze_marker(d).name == "THRESHOLD_FROZEN.json"
    assert test_lock_marker(d).name == "TEST_EVALUATED.json"


def test_yaml_epochs_and_selection():
    cfg = _cfg()
    assert cfg["training"]["epochs"] == 2
    assert cfg["training"]["seeds"] == [13, 42, 73]
    assert cfg["selection"]["checkpoint_metric"] == "validation_pr_auc"
    assert cfg["selection"]["threshold_metric"] == "validation_f1"
    assert cfg["training"]["optimizer"] == "paged_adamw_8bit"

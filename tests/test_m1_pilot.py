"""Unit tests for M1 QLoRA pilot contracts (no full 7B load)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from src.eval.classification_metrics import (
    compute_classification_metrics,
    metrics_at_threshold,
)
from src.models.qwen_m1 import (
    FORBIDDEN_METADATA_MARKERS,
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    LORA_TARGET_MODULES,
    count_supervised_labels,
    restricted_p_buggy,
)
from src.train.m1_collator import M1CausalCollator, encode_example, encode_prompt_only
from src.train.m1_dataset import (
    audit_structured_leakage,
    sample_stage_a,
    sample_stage_b,
    stage_b_stats,
)
from src.train.train_m1 import hash_checkpoint_dir, sha256_file


class FakeTok:
    """Minimal tokenizer stub: encode chars as ord%100 + offset; pad=0."""

    pad_token_id = 0
    eos_token_id = 1

    def encode(self, text, add_special_tokens=False):
        # Map '0'->15, '1'->16 to match contract for label tests
        if text == "0":
            return [LABEL_TOKEN_ID_0]
        if text == "1":
            return [LABEL_TOKEN_ID_1]
        return [10 + (i % 50) for i in range(len(text))]

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False):
        ids = self.encode(text, add_special_tokens=add_special_tokens)
        out = {"input_ids": ids}
        if return_offsets_mapping:
            out["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return out

    def decode(self, ids, skip_special_tokens=False):
        return "x" * len(ids)


def test_restricted_softmax_equal():
    l0 = torch.tensor([0.0, 1.0])
    l1 = torch.tensor([0.0, 1.0])
    p = restricted_p_buggy(l0, l1)
    assert torch.allclose(p, torch.tensor([0.5, 0.5]))


def test_restricted_softmax_l1_greater():
    p = restricted_p_buggy(torch.tensor([0.0]), torch.tensor([2.0]))
    assert float(p) > 0.5


def test_restricted_softmax_l1_less():
    p = restricted_p_buggy(torch.tensor([2.0]), torch.tensor([0.0]))
    assert float(p) < 0.5


def test_encode_example_one_supervised_label():
    tok = FakeTok()
    enc = encode_example(tok, "PROMPTTEXT", 1, max_length=2048)
    assert sum(1 for x in enc["labels"] if x != -100) == 1
    assert enc["labels"][-1] == LABEL_TOKEN_ID_1
    assert enc["input_ids"][-1] == LABEL_TOKEN_ID_1
    enc0 = encode_example(tok, "PROMPTTEXT", 0, max_length=2048)
    assert enc0["labels"][-1] == LABEL_TOKEN_ID_0


def test_collator_padding_and_single_label():
    tok = FakeTok()
    feats = [
        encode_example(tok, "AAAA", 0),
        encode_example(tok, "BBBBBBBB", 1),
    ]
    batch = M1CausalCollator(pad_token_id=0)(feats)
    assert batch["input_ids"].shape[0] == 2
    assert torch.all(count_supervised_labels(batch["labels"]) == 1)
    # pad positions have labels -100
    for i, f in enumerate(feats):
        n = len(f["input_ids"])
        assert torch.all(batch["labels"][i, n:] == -100)


def test_logit_position_synthetic():
    """Logits at last prompt token predict the first assistant/class token."""
    # prompt_len=4, then target at index 4; causal: logits[3] predicts token[4]
    prompt_len = 4
    target_pos = prompt_len
    # synthetic logits [1, T, V]
    V = 32
    logits = torch.zeros(1, 6, V)
    logits[0, prompt_len - 1, LABEL_TOKEN_ID_1] = 10.0
    logits[0, prompt_len - 1, LABEL_TOKEN_ID_0] = 0.0
    # Guard: wrong positions must not be used
    logits[0, prompt_len, LABEL_TOKEN_ID_0] = 99.0  # post-target
    logits[0, prompt_len - 2, LABEL_TOKEN_ID_0] = 99.0  # earlier prompt
    last_idx = prompt_len - 1
    l0 = logits[0, last_idx, LABEL_TOKEN_ID_0]
    l1 = logits[0, last_idx, LABEL_TOKEN_ID_1]
    p = float(restricted_p_buggy(l0, l1))
    assert p > 0.9
    # labels contract: only target_pos supervised
    labels = torch.full((1, 6), -100)
    labels[0, target_pos] = LABEL_TOKEN_ID_1
    assert int(count_supervised_labels(labels)[0]) == 1


def test_metadata_leakage_detection():
    clean = "FILE: a.java\nHUNK\n+ int x = 0;\n- int y = 1;\n"
    assert audit_structured_leakage(clean)["leaked"] is False
    dirty = clean + "rq1_status=RQ1_POSITIVE\n"
    r = audit_structured_leakage(dirty)
    assert r["leaked"] is True
    assert "rq1_status" in r["hits"]
    for m in FORBIDDEN_METADATA_MARKERS:
        assert m  # markers non-empty


def test_lora_target_modules_list():
    assert set(LORA_TARGET_MODULES) == {
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    }


def test_parameter_audit_logic():
    """Freeze/accounting logic without loading 7B."""
    from src.models.qwen_m1 import parameter_audit

    class P(torch.nn.Parameter):
        pass

    model = MagicMock()
    params = []
    # base frozen
    p1 = torch.nn.Parameter(torch.zeros(10), requires_grad=False)
    p2 = torch.nn.Parameter(torch.zeros(5), requires_grad=True)  # lora
    p3 = torch.nn.Parameter(torch.zeros(5), requires_grad=True)

    def named_parameters():
        yield ("model.layers.0.self_attn.q_proj.weight", p1)
        yield ("model.layers.0.self_attn.q_proj.lora_A.default.weight", p2)
        yield ("model.layers.0.mlp.gate_proj.lora_B.default.weight", p3)
        for m in LORA_TARGET_MODULES:
            if m in ("q_proj", "gate_proj"):
                continue
            yield (
                f"model.layers.0.xx.{m}.lora_A.default.weight",
                torch.nn.Parameter(torch.zeros(3), requires_grad=True),
            )

    model.named_parameters = named_parameters
    audit = parameter_audit(model)
    assert audit["trainable_params"] > 0
    assert audit["total_params"] > audit["trainable_params"]
    assert audit["all_intended_families_present"]


def _fake_records(n_pos=20, n_neg=100, n_projects=21):
    recs = []
    projects = [f"p{i}" for i in range(n_projects)]
    for i in range(n_pos):
        recs.append(
            {
                "commit_id": f"pos{i:04d}",
                "commit_label": 1.0,
                "project": projects[i % n_projects],
            }
        )
    for i in range(n_neg):
        recs.append(
            {
                "commit_id": f"neg{i:04d}",
                "commit_label": 0.0,
                "project": projects[i % n_projects],
            }
        )
    return recs


def test_stage_a_sampling_deterministic():
    recs = _fake_records()
    a1 = sample_stage_a(recs, seed=42)
    a2 = sample_stage_a(recs, seed=42)
    assert [r["commit_id"] for r in a1] == [r["commit_id"] for r in a2]
    assert len(a1) == 32
    assert sum(1 for r in a1 if r["commit_label"] == 1.0) == 16
    assert len({r["commit_id"] for r in a1}) == 32


def test_stage_b_sampling_deterministic_natural():
    recs = _fake_records(n_pos=200, n_neg=2000, n_projects=21)
    b1 = sample_stage_b(recs, seed=42, n=256)
    b2 = sample_stage_b(recs, seed=42, n=256)
    assert [r["commit_id"] for r in b1] == [r["commit_id"] for r in b2]
    st = stage_b_stats(b1)
    assert st["n"] == 256
    # natural prevalence ~ 200/2200 ≈ 0.0909
    assert 0.05 < st["prevalence"] < 0.15
    assert st["n_projects"] >= 15  # prefer coverage


def test_classification_metrics_basic():
    y = np.array([0, 0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.4, 0.6, 0.9])
    m = compute_classification_metrics(y, s)
    assert m["n"] == 5
    assert m["positives"] == 2
    assert 0.0 <= m["roc_auc"] <= 1.0
    assert m["at_0_5"]["f1"] > 0
    assert "PILOT_DIAGNOSTIC_ONLY" in m["threshold_diagnostic_max_f1"]["note"]


def test_checkpoint_hashing(tmp_path: Path):
    f = tmp_path / "adapter_model.safetensors"
    f.write_bytes(b"abc123")
    (tmp_path / "adapter_config.json").write_text('{"r":16}\n')
    h1 = sha256_file(f)
    h2 = hashlib.sha256(b"abc123").hexdigest()
    assert h1 == h2
    d = hash_checkpoint_dir(tmp_path)
    assert "adapter_model.safetensors" in d
    assert d["adapter_model.safetensors"] == h2


def test_test_split_load_blocked():
    from src.train.m1_dataset import load_split_records

    with pytest.raises(RuntimeError, match="TEST SPLIT"):
        load_split_records(Path("/tmp"), "test")


def test_prompt_only_shorter_than_train_seq():
    tok = FakeTok()
    prompt = encode_prompt_only(tok, "HELLO", max_length=2048)
    full = encode_example(tok, "HELLO", 1, max_length=2048)
    assert len(prompt) == full["prompt_len"]
    assert len(full["input_ids"]) == len(prompt) + 1

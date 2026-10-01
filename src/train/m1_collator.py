"""Collator for M1 causal classification: one supervised label per example."""

from __future__ import annotations

from typing import Any

import torch

from src.models.qwen_m1 import LABEL_TOKEN_ID_0, LABEL_TOKEN_ID_1


def encode_example(
    tokenizer,
    prompt_text: str,
    label: int,
    *,
    max_length: int = 2048,
    token_id_0: int = LABEL_TOKEN_ID_0,
    token_id_1: int = LABEL_TOKEN_ID_1,
) -> dict[str, Any]:
    """Build input_ids / labels for prompt + single classification token.

    Labels: -100 everywhere except the classification token position.
    """
    target_id = token_id_1 if int(label) == 1 else token_id_0
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    # Total sequence = prompt + 1 label; enforce max_length
    if len(prompt_ids) > max_length - 1:
        prompt_ids = prompt_ids[: max_length - 1]
    input_ids = prompt_ids + [target_id]
    labels = [-100] * len(prompt_ids) + [target_id]
    assert sum(1 for x in labels if x != -100) == 1
    assert labels[-1] == target_id
    return {
        "input_ids": input_ids,
        "labels": labels,
        "prompt_len": len(prompt_ids),
        "target_id": target_id,
        "label": int(label),
    }


def encode_prompt_only(
    tokenizer,
    prompt_text: str,
    *,
    max_length: int = 2048,
) -> list[int]:
    ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    if len(ids) > max_length - 1:
        ids = ids[: max_length - 1]
    return ids


class M1CausalCollator:
    """Pad batch; mask labels on pad positions with -100."""

    def __init__(self, pad_token_id: int):
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        max_len = max(len(f["input_ids"]) for f in features)
        bsz = len(features)
        input_ids = torch.full((bsz, max_len), self.pad_token_id, dtype=torch.long)
        attention_mask = torch.zeros((bsz, max_len), dtype=torch.long)
        labels = torch.full((bsz, max_len), -100, dtype=torch.long)
        for i, f in enumerate(features):
            n = len(f["input_ids"])
            input_ids[i, :n] = torch.tensor(f["input_ids"], dtype=torch.long)
            attention_mask[i, :n] = 1
            labels[i, :n] = torch.tensor(f["labels"], dtype=torch.long)
        # Assertions: exactly one supervised label per row
        n_sup = (labels != -100).sum(dim=1)
        if not torch.all(n_sup == 1):
            raise AssertionError(f"expected 1 supervised label/example, got {n_sup.tolist()}")
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def prompt_batch(
    tokenizer,
    prompt_texts: list[str],
    *,
    max_length: int = 2048,
) -> dict[str, torch.Tensor]:
    """Batch of prompt-only sequences for scoring (no label appended)."""
    encoded = [encode_prompt_only(tokenizer, t, max_length=max_length) for t in prompt_texts]
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    max_len = max(len(x) for x in encoded)
    bsz = len(encoded)
    input_ids = torch.full((bsz, max_len), pad_id, dtype=torch.long)
    attention_mask = torch.zeros((bsz, max_len), dtype=torch.long)
    for i, ids in enumerate(encoded):
        input_ids[i, : len(ids)] = torch.tensor(ids, dtype=torch.long)
        attention_mask[i, : len(ids)] = 1
    return {"input_ids": input_ids, "attention_mask": attention_mask}

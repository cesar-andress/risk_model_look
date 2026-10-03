"""Qwen M1 causal next-token binary classifier (QLoRA)."""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

# Frozen identifier + immutable revision (hub snapshot SHA)
QWEN_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
QWEN_REVISION = "c03e6d358207e414f1eca0bb1891e29f1db0e242"

LABEL_TOKEN_ID_0 = 15
LABEL_TOKEN_ID_1 = 16

LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]

# Metadata keys / strings that must never appear as structured prompt content
# from our renderer (natural source-code hits of "bug"/"0"/"1" are allowed).
FORBIDDEN_METADATA_MARKERS = [
    "commit_label",
    "is_buggy_commit",
    "rq1_status",
    "RQ1_POSITIVE",
    "RQ1_NEGATIVE",
    "NOT_IN_RQ1_UNIVERSE",
    "rq1_primary_commit",
    "stable_line_id",
    "ground_truth",
]


def verify_label_token_ids(tokenizer) -> tuple[int, int]:
    """Re-verify single-token '0'/'1' under the live tokenizer."""
    ids0 = tokenizer.encode("0", add_special_tokens=False)
    ids1 = tokenizer.encode("1", add_special_tokens=False)
    if len(ids0) != 1 or len(ids1) != 1:
        raise RuntimeError(f"multi-token labels: 0={ids0} 1={ids1}")
    if ids0[0] != LABEL_TOKEN_ID_0 or ids1[0] != LABEL_TOKEN_ID_1:
        raise RuntimeError(
            f"label ID drift: got {ids0[0]}/{ids1[0]} expected "
            f"{LABEL_TOKEN_ID_0}/{LABEL_TOKEN_ID_1}"
        )
    if ids0[0] == ids1[0]:
        raise RuntimeError("label tokens not distinct")
    return ids0[0], ids1[0]


def restricted_p_buggy(logit_0: torch.Tensor, logit_1: torch.Tensor) -> torch.Tensor:
    """Two-class softmax over (l0, l1); returns P(class=1)."""
    stacked = torch.stack([logit_0, logit_1], dim=-1)
    return F.softmax(stacked, dim=-1)[..., 1]


def bitsandbytes_nf4_config():
    from transformers import BitsAndBytesConfig

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


def load_base_nf4(
    *,
    model_id: str = QWEN_MODEL_ID,
    revision: str = QWEN_REVISION,
    device_map: str | dict[str, Any] = "auto",
):
    """Load frozen NF4 base without LoRA."""
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        quantization_config=bitsandbytes_nf4_config(),
        device_map=device_map,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    if hasattr(model, "config"):
        model.config.use_cache = False
    return model


def load_qlora_model(
    *,
    model_id: str = QWEN_MODEL_ID,
    revision: str = QWEN_REVISION,
    lora_r: int = 16,
    lora_alpha: int = 16,
    lora_dropout: float = 0.05,
    device_map: str | dict[str, Any] = "auto",
    for_training: bool = True,
):
    """Load NF4 QLoRA model with intended LoRA targets; base frozen."""
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    model = load_base_nf4(model_id=model_id, revision=revision, device_map=device_map)
    if for_training:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
    lora = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=list(LORA_TARGET_MODULES),
    )
    model = get_peft_model(model, lora)
    return model


def load_qlora_from_adapter(
    adapter_dir: str,
    *,
    model_id: str = QWEN_MODEL_ID,
    revision: str = QWEN_REVISION,
    device_map: str | dict[str, Any] = "auto",
    is_trainable: bool = False,
):
    """Reload NF4 base + saved LoRA adapter."""
    from peft import PeftModel

    base = load_base_nf4(model_id=model_id, revision=revision, device_map=device_map)
    model = PeftModel.from_pretrained(base, adapter_dir, is_trainable=is_trainable)
    if is_trainable:
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
        if hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        model.train()
    return model


def parameter_audit(model) -> dict[str, Any]:
    total = 0
    trainable = 0
    trainable_names = []
    frozen_base_ok = True
    for name, p in model.named_parameters():
        n = p.numel()
        total += n
        if p.requires_grad:
            trainable += n
            trainable_names.append(name)
            if "lora_" not in name.lower():
                # prepare_model_for_kbit may leave layernorm etc.; flag non-lora
                if "lora" not in name.lower():
                    frozen_base_ok = False
        else:
            if "lora_" in name.lower():
                frozen_base_ok = False
    families = {m: 0 for m in LORA_TARGET_MODULES}
    for name in trainable_names:
        for m in LORA_TARGET_MODULES:
            if f".{m}." in name or name.endswith(f".{m}.weight"):
                # peft names like ...q_proj.lora_A...
                if m in name:
                    families[m] += 1
    for m in LORA_TARGET_MODULES:
        # count occurrences in trainable names
        families[m] = sum(1 for n in trainable_names if m in n)
    return {
        "total_params": int(total),
        "trainable_params": int(trainable),
        "trainable_pct": float(100.0 * trainable / total) if total else 0.0,
        "lora_family_trainable_tensors": families,
        "n_trainable_tensors": len(trainable_names),
        "all_intended_families_present": all(v > 0 for v in families.values()),
        "no_non_lora_trainable_strict": all("lora" in n.lower() for n in trainable_names),
    }


def score_prompt_logits(
    model,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    token_id_0: int = LABEL_TOKEN_ID_0,
    token_id_1: int = LABEL_TOKEN_ID_1,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Score first assistant token from prompt-only batch.

    input_ids: [B, T] prompt with generation prompt (NO label appended).
    Returns (p_buggy [B], l0 [B], l1 [B]) using logits at last real token
    (predicting the next / first assistant content token).
    """
    out = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = out.logits  # [B, T, V]
    # Position of last prompt token = index of last attended token
    # logits[b, pos] predicts token at pos+1
    last_idx = attention_mask.sum(dim=1) - 1  # [B]
    batch = torch.arange(input_ids.size(0), device=input_ids.device)
    last_logits = logits[batch, last_idx]  # [B, V]
    l0 = last_logits[:, token_id_0]
    l1 = last_logits[:, token_id_1]
    p = restricted_p_buggy(l0, l1)
    return p, l0, l1


def count_supervised_labels(labels: torch.Tensor) -> torch.Tensor:
    """Per-row count of non -100 labels."""
    return (labels != -100).sum(dim=-1)

"""M1 QLoRA training loop utilities (pilot stages A/B)."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from src.models.qwen_m1 import (
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    count_supervised_labels,
    score_prompt_logits,
)
from src.train.m1_collator import M1CausalCollator, encode_example, prompt_batch
from src.train.m1_dataset import (
    build_chat_prompt_text,
    commit_label_int,
    render_and_truncate_prompt,
)


def set_seed(seed: int = 42) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    # Deterministic settings (not claiming universal bitwise GPU determinism)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    try:
        from transformers import set_seed as hf_set_seed

        hf_set_seed(seed)
    except Exception:
        pass
    return {
        "seed": seed,
        "cudnn_deterministic": True,
        "cudnn_benchmark": False,
        "note": "Not claiming universal bitwise GPU determinism",
    }


class M1EncodedDataset(Dataset):
    def __init__(self, examples: list[dict[str, Any]]):
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.examples[idx]


def prepare_examples(
    tokenizer,
    records: list[dict[str, Any]],
    *,
    max_length: int = 2048,
) -> list[dict[str, Any]]:
    out = []
    for rec in records:
        prompt, _tr = render_and_truncate_prompt(tokenizer, rec, max_length=max_length)
        label = commit_label_int(rec)
        enc = encode_example(tokenizer, prompt, label, max_length=max_length)
        enc["commit_id"] = rec["commit_id"]
        enc["project"] = rec["project"]
        enc["prompt_text"] = prompt
        out.append(enc)
    return out


def build_optimizer(model, *, lr: float, weight_decay: float = 0.0):
    """Prefer paged_adamw_8bit; fall back to AdamW."""
    try:
        import bitsandbytes as bnb

        opt = bnb.optim.PagedAdamW8bit(
            [p for p in model.parameters() if p.requires_grad],
            lr=lr,
            weight_decay=weight_decay,
        )
        return opt, "paged_adamw_8bit"
    except Exception:
        opt = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad],
            lr=lr,
            weight_decay=weight_decay,
        )
        return opt, "AdamW"


def linear_warmup_scheduler(optimizer, *, num_warmup: int, num_training: int):
    from torch.optim.lr_scheduler import LambdaLR

    def lr_lambda(step: int):
        if num_training <= 0:
            return 1.0
        if step < num_warmup:
            return float(step) / float(max(1, num_warmup))
        return max(0.0, float(num_training - step) / float(max(1, num_training - num_warmup)))

    return LambdaLR(optimizer, lr_lambda)


def train_steps(
    model,
    dataloader: DataLoader,
    optimizer,
    scheduler,
    *,
    max_steps: int,
    grad_accum: int = 16,
    max_grad_norm: float = 1.0,
    device: torch.device,
    eval_fn: Callable[[], dict[str, Any]] | None = None,
    eval_every: int = 10,
    early_stop_perfect: bool = False,
    one_pass_only: bool = False,
) -> dict[str, Any]:
    """Train with microbatch size from dataloader and gradient accumulation.

    One optimizer step = ``grad_accum`` microbatches (effective batch).
    If ``one_pass_only``, stop after exhausting the dataloader once (partial
    final accumulation still steps if any grads pending).
    """
    model.train()
    history = []
    step = 0
    initial_loss = None
    final_loss = None
    nan_inf = False
    grad_norms = []
    perfect_streak = 0
    stopped_early = False
    grad_audit = None
    micro_losses: list[float] = []
    optimizer.zero_grad(set_to_none=True)

    data_iter = iter(dataloader)
    exhausted = False
    pending_micro = 0

    while step < max_steps and not exhausted:
        try:
            batch = next(data_iter)
        except StopIteration:
            if one_pass_only:
                exhausted = True
                # flush remaining grads as a final (possibly smaller) step
                if pending_micro > 0 and step < max_steps:
                    gn = torch.nn.utils.clip_grad_norm_(
                        [p for p in model.parameters() if p.requires_grad], max_grad_norm
                    )
                    gnv = float(gn.detach().cpu()) if torch.is_tensor(gn) else float(gn)
                    if not np.isfinite(gnv):
                        nan_inf = True
                        break
                    grad_norms.append(gnv)
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad(set_to_none=True)
                    step += 1
                    loss_val = float(np.mean(micro_losses)) if micro_losses else None
                    if loss_val is not None:
                        if initial_loss is None:
                            initial_loss = loss_val
                        final_loss = loss_val
                    history.append(
                        {
                            "step": step,
                            "loss": loss_val,
                            "grad_norm": gnv,
                            "lr": float(scheduler.get_last_lr()[0]),
                            "microbatches": pending_micro,
                            "flushed_partial": True,
                        }
                    )
                break
            data_iter = iter(dataloader)
            batch = next(data_iter)

        batch = {k: v.to(device) for k, v in batch.items()}
        assert torch.all(count_supervised_labels(batch["labels"]) == 1)

        outputs = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"],
        )
        loss = outputs.loss / float(grad_accum)
        if not torch.isfinite(loss):
            nan_inf = True
            break
        loss_val = float(outputs.loss.detach().cpu())
        micro_losses.append(loss_val)
        loss.backward()
        pending_micro += 1

        if grad_audit is None:
            fam = {
                m: 0.0
                for m in [
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ]
            }
            for name, p in model.named_parameters():
                if p.grad is None or not p.requires_grad:
                    continue
                g = float(p.grad.detach().float().norm().cpu())
                for m in fam:
                    if m in name and "lora_" in name.lower():
                        fam[m] = max(fam[m], g)
            grad_audit = {
                "lora_family_grad_norm_max": fam,
                "all_families_nonzero": all(v > 0 for v in fam.values()),
            }

        if pending_micro < grad_accum:
            continue

        gn = torch.nn.utils.clip_grad_norm_(
            [p for p in model.parameters() if p.requires_grad], max_grad_norm
        )
        gnv = float(gn.detach().cpu()) if torch.is_tensor(gn) else float(gn)
        if not np.isfinite(gnv):
            nan_inf = True
            break
        grad_norms.append(gnv)

        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        step += 1
        avg_loss = float(np.mean(micro_losses[-grad_accum:]))
        if initial_loss is None:
            initial_loss = avg_loss
        final_loss = avg_loss
        pending_micro = 0

        row: dict[str, Any] = {
            "step": step,
            "loss": avg_loss,
            "grad_norm": gnv,
            "lr": float(scheduler.get_last_lr()[0]),
        }

        if eval_fn is not None and (step % eval_every == 0 or step == max_steps):
            model.eval()
            ev = eval_fn()
            model.train()
            row["eval"] = ev
            if early_stop_perfect and ev.get("accuracy") == 1.0:
                perfect_streak += 1
                if perfect_streak >= 2:
                    history.append(row)
                    stopped_early = True
                    break
            else:
                perfect_streak = 0

        history.append(row)

    return {
        "steps": step,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "nan_inf": nan_inf,
        "median_grad_norm": float(np.median(grad_norms)) if grad_norms else None,
        "max_grad_norm_obs": float(np.max(grad_norms)) if grad_norms else None,
        "history": history,
        "grad_audit": grad_audit,
        "stopped_early": stopped_early,
    }


@torch.no_grad()
def predict_records(
    model,
    tokenizer,
    records: list[dict[str, Any]],
    *,
    max_length: int = 2048,
    batch_size: int = 1,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    """Score records → (y_true, p_buggy). Never pass test records here intentionally."""
    model.eval()
    ys = []
    ps = []
    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        prompts = []
        for rec in chunk:
            prompt, _ = render_and_truncate_prompt(tokenizer, rec, max_length=max_length)
            prompts.append(prompt)
            ys.append(commit_label_int(rec))
        batch = prompt_batch(tokenizer, prompts, max_length=max_length)
        batch = {k: v.to(device) for k, v in batch.items()}
        p, _l0, _l1 = score_prompt_logits(model, batch["input_ids"], batch["attention_mask"])
        ps.extend(p.detach().float().cpu().tolist())
    return np.asarray(ys, dtype=int), np.asarray(ps, dtype=float)


@torch.no_grad()
def predict_encoded_prompts(
    model,
    tokenizer,
    examples: list[dict[str, Any]],
    *,
    max_length: int = 2048,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    ys = []
    ps = []
    for ex in examples:
        batch = prompt_batch(tokenizer, [ex["prompt_text"]], max_length=max_length)
        batch = {k: v.to(device) for k, v in batch.items()}
        p, _, _ = score_prompt_logits(model, batch["input_ids"], batch["attention_mask"])
        ys.append(ex["label"])
        ps.append(float(p[0].cpu()))
    return np.asarray(ys, dtype=int), np.asarray(ps, dtype=float)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_checkpoint_dir(ckpt_dir: Path) -> dict[str, str]:
    out = {}
    for p in sorted(ckpt_dir.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(ckpt_dir))] = sha256_file(p)
    return out


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

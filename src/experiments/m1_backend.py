"""Frozen M1 QLoRA backend for attribution execution.

Verifies base revision, adapter hash, config hash, and protocol hashes
before any forward. Does not change scientific definitions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from transformers import AutoTokenizer

from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    STATISTICAL_PROTOCOL_HASH,
)
from src.models.qwen_m1 import (
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    QWEN_MODEL_ID,
    QWEN_REVISION,
    load_qlora_from_adapter,
    parameter_audit,
    score_prompt_logits,
    verify_label_token_ids,
)
from src.train.m1_dataset import render_and_truncate_prompt

NOT_SCIENTIFIC = "NOT_SCIENTIFIC_RESULT"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class FrozenM1Mismatch(RuntimeError):
    """Hard failure: frozen identity does not match the requested backend."""


@dataclass
class FrozenM1Identity:
    seed: int
    selected_epoch: int
    adapter_dir: Path
    adapter_sha256: str
    config_hash: str
    base_model: str
    base_revision: str


def load_final_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "artifacts" / "m1_final" / "final_model_manifest.json"
    if not path.is_file():
        raise FrozenM1Mismatch(f"missing final M1 manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_frozen_identity(repo_root: Path, seed: int) -> FrozenM1Identity:
    man = load_final_manifest(repo_root)
    per = man["per_seed"][str(seed)]
    adapter_dir = repo_root / per["adapter_dir"]
    return FrozenM1Identity(
        seed=seed,
        selected_epoch=int(per["selected_epoch"]),
        adapter_dir=adapter_dir,
        adapter_sha256=str(per["adapter_model_sha256"]),
        config_hash=str(man["scientific_config_hash"]),
        base_model=str(man["base_model"]["identifier"]),
        base_revision=str(man["base_model"]["immutable_revision"]),
    )


def verify_frozen_identity(
    ident: FrozenM1Identity,
    *,
    protocol_hash: str,
    stats_hash: str,
    expected_config_hash: str | None = None,
) -> dict[str, Any]:
    if ident.base_model != QWEN_MODEL_ID:
        raise FrozenM1Mismatch(f"base model mismatch: {ident.base_model}")
    if ident.base_revision != QWEN_REVISION:
        raise FrozenM1Mismatch(
            f"base revision mismatch: {ident.base_revision} != {QWEN_REVISION}"
        )
    weights = ident.adapter_dir / "adapter_model.safetensors"
    if not weights.is_file():
        raise FrozenM1Mismatch(f"adapter missing: {weights}")
    got = sha256_file(weights)
    if got != ident.adapter_sha256:
        raise FrozenM1Mismatch(
            f"adapter hash mismatch seed={ident.seed}: {got} != {ident.adapter_sha256}"
        )
    if protocol_hash != ATTRIBUTION_PROTOCOL_HASH:
        raise FrozenM1Mismatch("attribution protocol hash mismatch")
    if stats_hash != STATISTICAL_PROTOCOL_HASH:
        raise FrozenM1Mismatch("statistical protocol hash mismatch")
    if expected_config_hash and expected_config_hash != ident.config_hash:
        raise FrozenM1Mismatch("scientific config hash mismatch")
    return {
        "seed": ident.seed,
        "selected_epoch": ident.selected_epoch,
        "adapter_dir": str(ident.adapter_dir),
        "adapter_sha256": got,
        "config_hash": ident.config_hash,
        "base_revision": ident.base_revision,
        "protocol_hash": protocol_hash,
        "stats_hash": stats_hash,
        "verified": True,
    }


class FrozenM1Bundle:
    def __init__(
        self,
        *,
        repo_root: Path,
        seed: int = 13,
        attn_implementation: str = "sdpa",
        device_map: str | dict[str, Any] = "auto",
        protocol_hash: str = ATTRIBUTION_PROTOCOL_HASH,
        stats_hash: str = STATISTICAL_PROTOCOL_HASH,
    ):
        self.repo_root = Path(repo_root)
        self.ident = resolve_frozen_identity(self.repo_root, seed)
        self.verification = verify_frozen_identity(
            self.ident,
            protocol_hash=protocol_hash,
            stats_hash=stats_hash,
            expected_config_hash=self.ident.config_hash,
        )
        self.attn_implementation = attn_implementation
        self.tokenizer = AutoTokenizer.from_pretrained(
            QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True
        )
        verify_label_token_ids(self.tokenizer)
        self.model = load_qlora_from_adapter(
            str(self.ident.adapter_dir),
            model_id=QWEN_MODEL_ID,
            revision=QWEN_REVISION,
            device_map=device_map,
            is_trainable=False,
            attn_implementation=attn_implementation,
        )
        self.model.eval()
        if hasattr(self.model, "enable_input_require_grads"):
            self.model.enable_input_require_grads()
        if hasattr(self.model, "gradient_checkpointing_enable"):
            self.model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        self.parameter_audit = parameter_audit(self.model)
        self.embed = self.model.get_input_embeddings()

    def encode(
        self, rec: dict[str, Any], *, max_length: int
    ) -> dict[str, Any]:
        prompt, trunc = render_and_truncate_prompt(
            self.tokenizer, rec, max_length=max_length
        )
        enc = self.tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
        device = next(self.model.parameters()).device
        input_ids = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "prompt": prompt,
            "truncation": trunc,
            "n_tokens": int(attention_mask.sum().item()),
        }

    def score_ids(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return score_prompt_logits(self.model, input_ids, attention_mask)

    def risk_from_ids(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> torch.Tensor:
        _, l0, l1 = self.score_ids(input_ids, attention_mask)
        return l1 - l0

    def embeddings(self, input_ids: torch.Tensor) -> torch.Tensor:
        return self.embed(input_ids)

    def risk_from_embeddings(
        self,
        embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
        *,
        reduce: str = "sum",
    ) -> torch.Tensor:
        b = embeddings.size(0)
        if attention_mask.size(0) == 1 and b > 1:
            attention_mask = attention_mask.expand(b, -1)
        out = self.model(
            inputs_embeds=embeddings,
            attention_mask=attention_mask,
            use_cache=False,
        )
        last_idx = attention_mask.sum(dim=1) - 1
        batch = torch.arange(b, device=embeddings.device)
        last_logits = out.logits[batch, last_idx]
        s = last_logits[:, LABEL_TOKEN_ID_1] - last_logits[:, LABEL_TOKEN_ID_0]
        if reduce == "sum":
            return s.sum()
        if reduce == "none":
            return s
        raise ValueError(reduce)

    def attention_token_scores(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> list[float]:
        """Last-layer mean-head attention at the classification query index.

        Recomputes only the last-layer query-key scores (no
        ``output_attentions=True``), matching ATTENTION_LAST_MEAN_HEAD without
        materialising every layer's T×T map.
        """
        from transformers.models.qwen2.modeling_qwen2 import apply_rotary_pos_emb

        captured: dict[str, Any] = {}
        last_attn = self.model.get_base_model().model.layers[-1].self_attn

        def _pre(_mod, args, kwargs):
            hidden = args[0] if args else kwargs.get("hidden_states")
            pos = None
            if len(args) > 1:
                pos = args[1]
            pos = kwargs.get("position_embeddings", pos)
            captured["hidden"] = hidden
            captured["pos"] = pos

        handle = last_attn.register_forward_pre_hook(_pre, with_kwargs=True)
        try:
            self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_attentions=False,
                use_cache=False,
            )
        finally:
            handle.remove()
        hidden = captured.get("hidden")
        pos = captured.get("pos")
        if hidden is None or pos is None:
            raise RuntimeError("failed to capture last-layer attention inputs")
        cos, sin = pos
        b, t_full, _ = hidden.shape
        t = int(attention_mask.sum().item())
        q_idx = t - 1
        hidden_shape = (b, t_full, -1, last_attn.head_dim)
        query_states = last_attn.q_proj(hidden).view(hidden_shape).transpose(1, 2)
        key_states = last_attn.k_proj(hidden).view(hidden_shape).transpose(1, 2)
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)
        n_rep = query_states.size(1) // key_states.size(1)
        if n_rep > 1:
            key_states = key_states.repeat_interleave(n_rep, dim=1)
        q_row = query_states[0, :, q_idx, :].to(torch.float32)
        k_all = key_states[0, :, :t, :].to(torch.float32)
        attn = torch.matmul(q_row.unsqueeze(1), k_all.transpose(-1, -2)).squeeze(1)
        attn = attn * float(last_attn.scaling)
        weights = torch.softmax(attn, dim=-1)
        scores = weights.mean(dim=0).detach().cpu().tolist()
        return scores

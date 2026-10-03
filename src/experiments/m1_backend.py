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


def transformer_layers(model) -> Any:
    core = model
    if hasattr(core, "get_base_model"):
        core = core.get_base_model()
    if hasattr(core, "model") and hasattr(core.model, "layers"):
        return core.model.layers
    raise RuntimeError("cannot locate transformer layers")


def _qk_mean_head_scores(
    attn_mod,
    hidden: torch.Tensor,
    pos: Any,
    attention_mask: torch.Tensor,
) -> torch.Tensor:
    """Mean-head softmax(Q K^T) at the classification query (last visible token)."""
    from transformers.models.qwen2.modeling_qwen2 import apply_rotary_pos_emb

    cos, sin = pos
    b, t_full, _ = hidden.shape
    t = int(attention_mask.sum().item())
    q_idx = t - 1
    hidden_shape = (b, t_full, -1, attn_mod.head_dim)
    query_states = attn_mod.q_proj(hidden).view(hidden_shape).transpose(1, 2)
    key_states = attn_mod.k_proj(hidden).view(hidden_shape).transpose(1, 2)
    query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)
    n_rep = query_states.size(1) // key_states.size(1)
    if n_rep > 1:
        key_states = key_states.repeat_interleave(n_rep, dim=1)
    q_row = query_states[0, :, q_idx, :].to(torch.float32)
    k_all = key_states[0, :, :t, :].to(torch.float32)
    scores = torch.matmul(q_row.unsqueeze(1), k_all.transpose(-1, -2)).squeeze(1)
    scores = scores * float(attn_mod.scaling)
    weights = torch.softmax(scores, dim=-1)
    return weights.mean(dim=0)


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
        load_adapter: bool = True,
    ):
        self.repo_root = Path(repo_root)
        self.load_adapter = bool(load_adapter)
        self.attn_implementation = attn_implementation
        self.tokenizer = AutoTokenizer.from_pretrained(
            QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True
        )
        verify_label_token_ids(self.tokenizer)
        if load_adapter:
            self.ident = resolve_frozen_identity(self.repo_root, seed)
            self.verification = verify_frozen_identity(
                self.ident,
                protocol_hash=protocol_hash,
                stats_hash=stats_hash,
                expected_config_hash=self.ident.config_hash,
            )
            self.model = load_qlora_from_adapter(
                str(self.ident.adapter_dir),
                model_id=QWEN_MODEL_ID,
                revision=QWEN_REVISION,
                device_map=device_map,
                is_trainable=False,
                attn_implementation=attn_implementation,
            )
        else:
            from src.models.qwen_m1 import load_base_nf4

            man = load_final_manifest(self.repo_root)
            if str(man["base_model"]["identifier"]) != QWEN_MODEL_ID:
                raise FrozenM1Mismatch("base model mismatch")
            if str(man["base_model"]["immutable_revision"]) != QWEN_REVISION:
                raise FrozenM1Mismatch("base revision mismatch")
            if protocol_hash != ATTRIBUTION_PROTOCOL_HASH:
                raise FrozenM1Mismatch("attribution protocol hash mismatch")
            if stats_hash != STATISTICAL_PROTOCOL_HASH:
                raise FrozenM1Mismatch("statistical protocol hash mismatch")
            self.ident = FrozenM1Identity(
                seed=-1,
                selected_epoch=-1,
                adapter_dir=self.repo_root,
                adapter_sha256="BASE_NO_ADAPTER",
                config_hash=str(man["scientific_config_hash"]),
                base_model=QWEN_MODEL_ID,
                base_revision=QWEN_REVISION,
            )
            self.verification = {
                "seed": None,
                "adapter_sha256": "BASE_NO_ADAPTER",
                "config_hash": self.ident.config_hash,
                "base_revision": QWEN_REVISION,
                "protocol_hash": protocol_hash,
                "stats_hash": stats_hash,
                "verified": True,
                "load_adapter": False,
            }
            self.model = load_base_nf4(
                model_id=QWEN_MODEL_ID,
                revision=QWEN_REVISION,
                device_map=device_map,
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
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        *,
        layer_selection: str = "LAST",
        final_k: int = 4,
    ) -> list[float]:
        """Mean-head attention at the classification query index.

        LAST realizes ATTENTION_LAST_MEAN_HEAD. FINAL_K_MEAN with final_k=4
        realizes ATTENTION_LAST4_MEAN (mean of the last four layers). Query
        index is the last visible prompt token (first assistant class token).
        """
        from src.attribution.attention import LayerSelection, select_layers

        layers = transformer_layers(self.model)
        n_layers = len(layers)
        if layer_selection in ("LAST", LayerSelection.LAST.value):
            layer_ids = select_layers(
                n_layers, layer_selection=LayerSelection.LAST, final_k=1
            )
        elif layer_selection in ("FINAL_K_MEAN", LayerSelection.FINAL_K_MEAN.value):
            layer_ids = select_layers(
                n_layers,
                layer_selection=LayerSelection.FINAL_K_MEAN,
                final_k=final_k,
            )
        else:
            raise ValueError(f"unknown layer_selection {layer_selection}")
        captured: dict[int, tuple[Any, Any, Any]] = {}

        def _make_pre(idx: int):
            def _pre(_mod, args, kwargs):
                hidden = args[0] if args else kwargs.get("hidden_states")
                pos = None
                if len(args) > 1:
                    pos = args[1]
                pos = kwargs.get("position_embeddings", pos)
                captured[idx] = (hidden, pos, _mod)

            return _pre

        handles = []
        for idx in layer_ids:
            handles.append(
                layers[idx].self_attn.register_forward_pre_hook(
                    _make_pre(idx), with_kwargs=True
                )
            )
        try:
            self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_attentions=False,
                use_cache=False,
            )
        finally:
            for h in handles:
                h.remove()
        per_layer: list[torch.Tensor] = []
        for idx in layer_ids:
            if idx not in captured:
                raise RuntimeError(f"failed to capture attention inputs layer={idx}")
            hidden, pos, attn_mod = captured[idx]
            if hidden is None or pos is None:
                raise RuntimeError(f"empty attention capture layer={idx}")
            per_layer.append(
                _qk_mean_head_scores(attn_mod, hidden, pos, attention_mask)
            )
        stacked = torch.stack(per_layer, dim=0)
        return stacked.mean(dim=0).detach().cpu().tolist()

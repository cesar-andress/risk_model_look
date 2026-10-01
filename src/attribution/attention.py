"""Attention-based token attribution interfaces (no large-model execution).

For M1, the default query position is the model position that produces the
first assistant classification-token logits — not all output positions, not a
teacher-forced target token, and not an arbitrary final sequence index unless
explicitly configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from src.attribution.base import AttributionResult, ScoreSpace, TargetDefinition
from src.attribution.targets import M1_RISK_LOGIT_CONTRAST


class HeadAggregation(str, Enum):
    MEAN = "MEAN"
    MAX = "MAX"


class LayerSelection(str, Enum):
    LAST = "LAST"
    FINAL_K_MEAN = "FINAL_K_MEAN"


class QueryPositionPolicy(str, Enum):
    """Where attention is read for explanation."""

    FIRST_ASSISTANT_CLASSIFICATION_TOKEN = "FIRST_ASSISTANT_CLASSIFICATION_TOKEN"
    EXPLICIT_INDEX = "EXPLICIT_INDEX"


@dataclass(frozen=True)
class AttentionAttributionConfig:
    """Configuration dimensions for attention attribution experiments.

    No strategy is declared scientifically best here; the experiment protocol
    compares predefined strategies later.
    """

    layer_selection: LayerSelection = LayerSelection.LAST
    final_k: int = 1
    head_aggregation: HeadAggregation = HeadAggregation.MEAN
    query_position_policy: QueryPositionPolicy = (
        QueryPositionPolicy.FIRST_ASSISTANT_CLASSIFICATION_TOKEN
    )
    explicit_query_index: int | None = None
    # Attention attribution scores are typically non-negative; signed=False by default.
    signed: bool = False
    method_name: str = "attention"


def resolve_query_index(
    *,
    policy: QueryPositionPolicy,
    classification_query_index: int | None,
    explicit_query_index: int | None,
    seq_len: int,
) -> int:
    """Resolve the attention query row index under the configured policy."""
    if policy == QueryPositionPolicy.FIRST_ASSISTANT_CLASSIFICATION_TOKEN:
        if classification_query_index is None:
            raise ValueError(
                "classification_query_index required for "
                "FIRST_ASSISTANT_CLASSIFICATION_TOKEN policy"
            )
        q = int(classification_query_index)
    elif policy == QueryPositionPolicy.EXPLICIT_INDEX:
        if explicit_query_index is None:
            raise ValueError("explicit_query_index required for EXPLICIT_INDEX policy")
        q = int(explicit_query_index)
    else:
        raise ValueError(f"Unknown query position policy: {policy}")
    if q < 0 or q >= seq_len:
        raise IndexError(f"query index {q} out of range for seq_len={seq_len}")
    return q


def select_layers(
    n_layers: int,
    *,
    layer_selection: LayerSelection,
    final_k: int,
) -> list[int]:
    if n_layers <= 0:
        raise ValueError("n_layers must be positive")
    if layer_selection == LayerSelection.LAST:
        return [n_layers - 1]
    if layer_selection == LayerSelection.FINAL_K_MEAN:
        k = max(1, min(int(final_k), n_layers))
        return list(range(n_layers - k, n_layers))
    raise ValueError(f"Unknown layer selection: {layer_selection}")


def aggregate_heads(attn_heads: np.ndarray, how: HeadAggregation) -> np.ndarray:
    """attn_heads: (n_heads, key_len) at a fixed query position."""
    if attn_heads.ndim != 2:
        raise ValueError(f"expected (heads, keys), got shape {attn_heads.shape}")
    if how == HeadAggregation.MEAN:
        return attn_heads.mean(axis=0)
    if how == HeadAggregation.MAX:
        return attn_heads.max(axis=0)
    raise ValueError(f"Unknown head aggregation: {how}")


def attention_token_scores_from_maps(
    attention_maps: Sequence[np.ndarray] | np.ndarray,
    *,
    config: AttentionAttributionConfig,
    classification_query_index: int | None,
    target: TargetDefinition = M1_RISK_LOGIT_CONTRAST,
) -> AttributionResult:
    """Build token scores from precomputed attention tensors.

    ``attention_maps`` shape: (n_layers, n_heads, q_len, k_len) or a list of
    per-layer (n_heads, q_len, k_len) arrays.
    """
    if isinstance(attention_maps, np.ndarray):
        layers = [attention_maps[i] for i in range(attention_maps.shape[0])]
    else:
        layers = list(attention_maps)
    n_layers = len(layers)
    if n_layers == 0:
        raise ValueError("empty attention maps")
    q_len, k_len = layers[0].shape[-2], layers[0].shape[-1]
    q = resolve_query_index(
        policy=config.query_position_policy,
        classification_query_index=classification_query_index,
        explicit_query_index=config.explicit_query_index,
        seq_len=q_len,
    )
    layer_ids = select_layers(
        n_layers,
        layer_selection=config.layer_selection,
        final_k=config.final_k,
    )
    per_layer: list[np.ndarray] = []
    for li in layer_ids:
        heads_at_q = layers[li][:, q, :]  # (heads, keys)
        per_layer.append(aggregate_heads(heads_at_q, config.head_aggregation))
    scores = np.mean(np.stack(per_layer, axis=0), axis=0)
    if scores.shape[0] != k_len:
        raise RuntimeError("aggregated attention length mismatch")
    meta: dict[str, Any] = {
        "layer_ids": layer_ids,
        "query_index": q,
        "query_position_policy": config.query_position_policy.value,
        "head_aggregation": config.head_aggregation.value,
        "layer_selection": config.layer_selection.value,
        "final_k": config.final_k,
        "note": "Infrastructure only; no scientific ranking of strategies.",
    }
    return AttributionResult(
        method_name=config.method_name,
        score_space=ScoreSpace.TOKEN,
        signed=config.signed,
        target_definition=target,
        token_scores=scores.tolist(),
        metadata=meta,
    )


def preset_configs() -> Mapping[str, AttentionAttributionConfig]:
    """Named presets for protocol comparison (not ranked)."""
    return {
        "attention_last_mean": AttentionAttributionConfig(
            layer_selection=LayerSelection.LAST,
            head_aggregation=HeadAggregation.MEAN,
            method_name="attention_last_mean",
        ),
        "attention_last_max": AttentionAttributionConfig(
            layer_selection=LayerSelection.LAST,
            head_aggregation=HeadAggregation.MAX,
            method_name="attention_last_max",
        ),
        "attention_last4_mean": AttentionAttributionConfig(
            layer_selection=LayerSelection.FINAL_K_MEAN,
            final_k=4,
            head_aggregation=HeadAggregation.MEAN,
            method_name="attention_last4_mean",
        ),
    }

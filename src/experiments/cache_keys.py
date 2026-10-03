"""Cache key contracts for occlusion and attribution.

Never key only by commit ID — incompatible scientific reuse must be prevented.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


def _stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OcclusionCacheKey:
    model_checkpoint_hash: str
    dataset_version: str
    representation: str  # e.g. CHANGED_ONLY / CTX3
    commit_id: str
    region_definition: str
    perturbation_policy: str
    prompt_version: str
    score_target: str = "risk_logit_contrast"
    max_length: int = 2048

    def digest(self) -> str:
        return _stable_hash(asdict(self))


@dataclass(frozen=True)
class AttributionCacheKey:
    model_checkpoint_hash: str
    dataset_version: str
    representation: str
    commit_id: str
    method_id: str
    method_config_hash: str
    target: str
    prompt_version: str
    tokenizer_id: str
    max_length: int = 2048
    # Attention / gradient / IG specific knobs serialized into method_config_hash
    family: str = "unspecified"  # attention | gradient | ig | ...

    def digest(self) -> str:
        return _stable_hash(asdict(self))


CACHE_CONTRACT = {
    "occlusion_required_fields": [
        "model_checkpoint_hash",
        "dataset_version",
        "representation",
        "commit_id",
        "region_definition",
        "perturbation_policy",
        "prompt_version",
    ],
    "attribution_required_fields": [
        "model_checkpoint_hash",
        "dataset_version",
        "representation",
        "commit_id",
        "method_id",
        "method_config_hash",
        "target",
        "prompt_version",
        "tokenizer_id",
    ],
    "prohibited": ["key_only_by_commit_id"],
}

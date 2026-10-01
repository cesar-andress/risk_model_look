"""Versioned scientific cache keys for the attribution engine.

Never key only by commit ID.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    RENDERER_VERSION,
    TOKEN_MAPPING_VERSION,
)


def stable_json_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EngineCacheKey:
    """Full scientific identity for a cacheable attribution unit."""

    model_hash: str
    adapter_hash: str
    dataset_version: str
    commit_id: str
    method: str
    granularity: str
    protocol_hash: str
    renderer_version: str
    token_mapping_version: str
    perturbation_operator: str
    configuration_hash: str
    seed: int

    def digest(self) -> str:
        return stable_json_hash(asdict(self))

    def relative_cache_path(self) -> Path:
        # artifacts/attribution_cache/method/model/protocol_hash/commit_id.json
        # include seed+granularity+config in filename to avoid collisions
        fname = (
            f"{self.commit_id}__seed{self.seed}__{self.granularity}__"
            f"{self.configuration_hash[:12]}__{self.digest()[:16]}.json"
        )
        return Path(self.method) / self.model_hash[:16] / self.protocol_hash[:16] / fname


def build_engine_cache_key(
    *,
    model_hash: str,
    adapter_hash: str,
    dataset_version: str,
    commit_id: str,
    method: str,
    granularity: str,
    configuration: dict[str, Any],
    seed: int,
    protocol_hash: str = ATTRIBUTION_PROTOCOL_HASH,
    renderer_version: str = RENDERER_VERSION,
    token_mapping_version: str = TOKEN_MAPPING_VERSION,
    perturbation_operator: str = "NONE",
) -> EngineCacheKey:
    cfg_hash = stable_json_hash(configuration)
    return EngineCacheKey(
        model_hash=model_hash,
        adapter_hash=adapter_hash,
        dataset_version=dataset_version,
        commit_id=commit_id,
        method=method,
        granularity=granularity,
        protocol_hash=protocol_hash,
        renderer_version=renderer_version,
        token_mapping_version=token_mapping_version,
        perturbation_operator=perturbation_operator,
        configuration_hash=cfg_hash,
        seed=seed,
    )


@dataclass
class CacheEntry:
    cache_key: str
    key_fields: dict[str, Any]
    status: str
    result_summary: dict[str, Any]
    checksum: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "key_fields": self.key_fields,
            "status": self.status,
            "result_summary": self.result_summary,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CacheEntry":
        return cls(
            cache_key=d["cache_key"],
            key_fields=d["key_fields"],
            status=d["status"],
            result_summary=d.get("result_summary") or {},
            checksum=d["checksum"],
            metadata=d.get("metadata") or {},
        )


class AttributionCacheStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def path_for(self, key: EngineCacheKey) -> Path:
        return self.root / key.relative_cache_path()

    def write(self, key: EngineCacheKey, entry: CacheEntry, *, force: bool = False) -> Path:
        path = self.path_for(key)
        if path.exists() and not force:
            raise FileExistsError(f"cache entry exists (use force): {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = entry.to_dict()
        # checksum over scientific payload excluding checksum field
        chk_src = {k: v for k, v in payload.items() if k != "checksum"}
        payload["checksum"] = stable_json_hash(chk_src)
        entry.checksum = payload["checksum"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def read(self, key: EngineCacheKey) -> CacheEntry | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        chk = data.get("checksum")
        chk_src = {k: v for k, v in data.items() if k != "checksum"}
        if chk != stable_json_hash(chk_src):
            raise ValueError(f"cache checksum mismatch: {path}")
        return CacheEntry.from_dict(data)

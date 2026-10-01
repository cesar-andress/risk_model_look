"""Statistical protocol manifest + deterministic SHA-256 hash.

V1 is historically frozen. Current after reviewer amendment: V1.1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.experiments.protocol_manifest import (
    PROTOCOL_ID_V1_2,
    V1_2_CONFIG,
    protocol_hash as attribution_protocol_hash,
    load_protocol_config as load_attr_config,
)

ROOT = Path(__file__).resolve().parents[2]
V1_CONFIG = ROOT / "configs" / "stats" / "attribution_stats_v1.yaml"
V1_1_CONFIG = ROOT / "configs" / "stats" / "attribution_stats_v1_1.yaml"
DEFAULT_CONFIG = V1_1_CONFIG
MANIFEST_DIR = ROOT / "artifacts" / "statistical_protocol"
V1_1_MANIFEST_DIR = ROOT / "artifacts" / "statistical_protocol" / "v1_1"

STATISTICAL_PROTOCOL_ID_V1 = "STATISTICAL_ANALYSIS_PROTOCOL_V1"
STATISTICAL_PROTOCOL_ID = "STATISTICAL_ANALYSIS_PROTOCOL_V1_1"
STATISTICAL_PROTOCOL_HASH_V1 = (
    "22816586bb5688b6595d4cd10c86ead079274aa6b1827a50b2d7b0cf7b090c07"
)


def load_stats_config(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("stats config must be a mapping")
    return data


def canonicalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): canonicalize(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [canonicalize(x) for x in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return float(f"{obj:.12g}")
    return obj


def canonical_json_bytes(config: dict[str, Any]) -> bytes:
    return json.dumps(
        canonicalize(config), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def statistical_protocol_hash(config: dict[str, Any] | None = None) -> str:
    cfg = config if config is not None else load_stats_config()
    return hashlib.sha256(canonical_json_bytes(cfg)).hexdigest()


def verify_stats_v1_hash_intact() -> bool:
    return statistical_protocol_hash(load_stats_config(V1_CONFIG)) == STATISTICAL_PROTOCOL_HASH_V1


def parent_attribution_protocol(config: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = config if config is not None else load_stats_config()
    parent = cfg.get("parent_attribution_protocol") or {}
    return {
        "protocol_id": str(parent.get("protocol_id", "")),
        "hash": str(parent.get("hash", "")),
    }


def sync_parent_attribution_hash(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill parent attribution hash from frozen V1.2 config."""
    cfg = dict(config if config is not None else load_stats_config())
    attr = load_attr_config(V1_2_CONFIG)
    h = attribution_protocol_hash(attr)
    cfg["parent_attribution_protocol"] = {
        "protocol_id": PROTOCOL_ID_V1_2,
        "hash": h,
    }
    return cfg


def validate_stats_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pid = config.get("protocol_id")
    if pid == STATISTICAL_PROTOCOL_ID_V1:
        if (config.get("inference") or {}).get("primary_unit") != "COMMIT":
            errors.append("unit")
        return errors

    if pid != STATISTICAL_PROTOCOL_ID:
        errors.append("protocol_id")
    if config.get("amended_from_hash") != STATISTICAL_PROTOCOL_HASH_V1:
        errors.append("amended_from_hash")
    if not verify_stats_v1_hash_intact():
        errors.append("stats_v1_drift")

    parent = parent_attribution_protocol(config)
    if parent["protocol_id"] != PROTOCOL_ID_V1_2:
        errors.append("parent_id")
    if parent["hash"] in {"", "PENDING_COMPUTE"}:
        errors.append("parent_hash_pending")

    rq1 = config.get("rq1") or {}
    if (rq1.get("primary_endpoint") or {}).get("name") != "Recall@20%Effort":
        errors.append("rq1_primary")
    if len(rq1.get("primary_contrasts") or []) != 3:
        errors.append("rq1_contrasts")
    if not (rq1.get("topk_binary") or {}).get("wilcoxon_primary_forbidden"):
        errors.append("topk_wilcoxon")

    rq2 = config.get("rq2") or {}
    if (rq2.get("primary_endpoint") or {}).get("name") != "ABS_DELETION_AOPC":
        errors.append("rq2_primary")
    if not rq2.get("occlusion_confirmatory_holm_forbidden"):
        errors.append("occ_holm")

    rq3 = config.get("rq3") or {}
    if (rq3.get("primary_endpoint") or {}).get("name") != "SIGNED_VS_ABSOLUTE_DELTA_RECALL20":
        errors.append("rq3_primary")

    rq4 = config.get("rq4") or {}
    if (rq4.get("diff_polarity_swap") or {}).get("role") != "EXPLORATORY_STRUCTURAL_SENSITIVITY":
        errors.append("rq4_swap")

    fam = (config.get("multiplicity") or {}).get("families") or {}
    if "RQ1_PRIMARY" not in fam or "RQ2_PRIMARY" not in fam:
        errors.append("families")
    return errors


def build_manifest(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = sync_parent_attribution_hash(config)
    errs = validate_stats_config(cfg)
    if errs:
        raise ValueError(f"stats protocol validation failed: {errs}")
    h = statistical_protocol_hash(cfg)
    return {
        "protocol_id": STATISTICAL_PROTOCOL_ID,
        "STATISTICAL_PROTOCOL_HASH": h,
        "STATISTICAL_PROTOCOL_HASH_V1": STATISTICAL_PROTOCOL_HASH_V1,
        "parent_attribution_protocol": parent_attribution_protocol(cfg),
        "config_path": str(DEFAULT_CONFIG.relative_to(ROOT)),
        "v1_config_path": str(V1_CONFIG.relative_to(ROOT)),
        "canonical_sha256": h,
        "validation_errors": [],
        "frozen_highlights": {
            "rq1_primary": "Recall@20%Effort",
            "rq1_contrasts": 3,
            "rq2_primary": "ABS_DELETION_AOPC",
            "rq2_contrasts": 2,
            "rq3_primary": "SIGNED_VS_ABSOLUTE_DELTA_RECALL20",
            "rq4": "estimation_focused",
            "occlusion_rq2": "reference_not_confirmatory",
        },
    }


def write_manifest(out_dir: Path | None = None) -> Path:
    cfg = sync_parent_attribution_hash()
    # Persist synced parent hash into yaml
    import yaml as _yaml

    V1_1_CONFIG.write_text(
        "# STATISTICAL_ANALYSIS_PROTOCOL_V1.1 — Adversarial-review amendment (pre-result).\n"
        "# Parent STATISTICAL_PROTOCOL_V1 hash:\n"
        f"#   {STATISTICAL_PROTOCOL_HASH_V1}\n"
        "# Do NOT overwrite configs/stats/attribution_stats_v1.yaml.\n\n"
        + _yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    out = out_dir or V1_1_MANIFEST_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(cfg)
    path = out / "statistical_protocol_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "statistical_protocol_canonical.json").write_bytes(canonical_json_bytes(cfg) + b"\n")
    # Root pointer for current stats protocol
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (MANIFEST_DIR / "statistical_protocol_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (MANIFEST_DIR / "CURRENT_STATISTICAL_PROTOCOL").write_text(
        f"{STATISTICAL_PROTOCOL_ID}\n{manifest['STATISTICAL_PROTOCOL_HASH']}\n",
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    assert verify_stats_v1_hash_intact()
    p = write_manifest()
    m = json.loads(p.read_text(encoding="utf-8"))
    print("V1", m["STATISTICAL_PROTOCOL_HASH_V1"])
    print("V1.1", m["STATISTICAL_PROTOCOL_HASH"])
    print(m["parent_attribution_protocol"])
    print(p)

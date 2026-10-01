"""Statistical protocol manifest + deterministic SHA-256 hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "stats" / "attribution_stats_v1.yaml"
MANIFEST_DIR = ROOT / "artifacts" / "statistical_protocol"

STATISTICAL_PROTOCOL_ID = "STATISTICAL_ANALYSIS_PROTOCOL_V1"
PARENT_ATTR_ID = "ATTRIBUTION_PROTOCOL_V1_1"
PARENT_ATTR_HASH = "ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e"


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


def parent_attribution_protocol(config: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = config if config is not None else load_stats_config()
    parent = cfg.get("parent_attribution_protocol") or {}
    return {
        "protocol_id": str(parent.get("protocol_id", "")),
        "hash": str(parent.get("hash", "")),
    }


def verify_parent_attribution_hash(config: dict[str, Any] | None = None) -> bool:
    p = parent_attribution_protocol(config)
    return p["protocol_id"] == PARENT_ATTR_ID and p["hash"] == PARENT_ATTR_HASH


REQUIRED = (
    "protocol_id",
    "parent_attribution_protocol",
    "inference",
    "seed_aggregation",
    "paired_test",
    "effect_sizes",
    "bootstrap",
    "multiplicity",
    "rq1",
    "rq2",
    "rq3",
    "rq4",
)


def validate_stats_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for k in REQUIRED:
        if k not in config:
            errors.append(f"missing:{k}")
    if config.get("protocol_id") != STATISTICAL_PROTOCOL_ID:
        errors.append("protocol_id")
    if not verify_parent_attribution_hash(config):
        errors.append("parent_hash")
    if (config.get("inference") or {}).get("primary_unit") != "COMMIT":
        errors.append("unit")
    if (config.get("seed_aggregation") or {}).get("min_common_valid_seeds") != 2:
        errors.append("min_seeds")
    if (config.get("paired_test") or {}).get("zero_method") != "PRATT":
        errors.append("pratt")
    if (config.get("bootstrap") or {}).get("repeats") != 10000:
        errors.append("boot_repeats")
    if (config.get("multiplicity") or {}).get("method") != "HOLM_FWER_V1":
        errors.append("holm")
    if (config.get("effect_sizes") or {}).get("primary_paired") != (
        "MATCHED_PAIRS_RANK_BISERIAL_CORRELATION"
    ):
        errors.append("rrb")
    if (config.get("reporting") or {}).get("scott_knott_esd_primary") is not False:
        errors.append("scott_knott")
    return errors


def build_manifest(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config if config is not None else load_stats_config()
    errs = validate_stats_config(cfg)
    if errs:
        raise ValueError(f"stats protocol validation failed: {errs}")
    h = statistical_protocol_hash(cfg)
    return {
        "protocol_id": STATISTICAL_PROTOCOL_ID,
        "STATISTICAL_PROTOCOL_HASH": h,
        "parent_attribution_protocol": parent_attribution_protocol(cfg),
        "config_path": str(DEFAULT_CONFIG.relative_to(ROOT)),
        "canonical_sha256": h,
        "validation_errors": [],
        "scipy_version_at_freeze": cfg.get("scipy_version_at_freeze"),
        "frozen_highlights": {
            "unit": "COMMIT",
            "min_common_valid_seeds": 2,
            "wilcoxon": "PRATT",
            "effect": "MATCHED_PAIRS_RANK_BISERIAL_CORRELATION",
            "bootstrap_repeats": 10000,
            "holm_alpha": 0.05,
            "cliffs_delta": "SECONDARY_LEGACY",
            "scott_knott_primary": False,
        },
    }


def write_manifest(out_dir: Path | None = None) -> Path:
    out = out_dir or MANIFEST_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    path = out / "statistical_protocol_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cfg = load_stats_config()
    (out / "statistical_protocol_canonical.json").write_bytes(
        canonical_json_bytes(cfg) + b"\n"
    )
    return path


if __name__ == "__main__":
    p = write_manifest()
    m = json.loads(p.read_text(encoding="utf-8"))
    print(m["STATISTICAL_PROTOCOL_HASH"])
    print(m["parent_attribution_protocol"])
    print(p)

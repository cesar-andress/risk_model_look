"""Canonical attribution protocol manifest + deterministic SHA-256 hash.

V1 is historically frozen and must not be overwritten.
Current scientific protocol after amendment: V1.1.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1_1.yaml"
V1_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1.yaml"
V1_ARCHIVE_DIR = ROOT / "artifacts" / "attribution_protocol" / "v1"
V1_1_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol" / "v1_1"
DEFAULT_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol"

PROTOCOL_ID_V1 = "ATTRIBUTION_PROTOCOL_V1"
PROTOCOL_ID_V1_1 = "ATTRIBUTION_PROTOCOL_V1_1"
PROTOCOL_ID = PROTOCOL_ID_V1_1  # current

# Frozen historical hash — never recompute into this constant from V1.1.
ATTRIBUTION_PROTOCOL_HASH_V1 = (
    "73f0f891683f926a39d68b078f6e2770a1b42181ba1a9f56575c5556cba4794d"
)


def load_protocol_config(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("protocol config must be a mapping")
    return data


def canonicalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): canonicalize(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [canonicalize(x) for x in obj]
    if isinstance(obj, tuple):
        return [canonicalize(x) for x in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return float(f"{obj:.12g}")
    return obj


def canonical_json_bytes(config: dict[str, Any]) -> bytes:
    canon = canonicalize(config)
    return json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def protocol_hash(config: dict[str, Any] | None = None) -> str:
    cfg = config if config is not None else load_protocol_config()
    return hashlib.sha256(canonical_json_bytes(cfg)).hexdigest()


def verify_v1_hash_intact() -> bool:
    """Recompute hash of frozen V1 config; must equal historical constant."""
    cfg = load_protocol_config(V1_CONFIG)
    return protocol_hash(cfg) == ATTRIBUTION_PROTOCOL_HASH_V1


REQUIRED_TOP_LEVEL_V1_1 = (
    "protocol_id",
    "amends",
    "amended_from_hash",
    "target",
    "rq1",
    "cohorts",
    "aggregation",
    "attention",
    "ig",
    "occlusion",
    "faithfulness",
    "polarity",
    "perturbation_operators",
    "missingness",
    "rq4",
    "random_baselines",
    "methods_primary",
)


def validate_protocol_config(config: dict[str, Any]) -> list[str]:
    """Validate current (V1.1) protocol config."""
    errors: list[str] = []
    pid = config.get("protocol_id")
    if pid == PROTOCOL_ID_V1:
        # Historical V1 validation subset
        if config.get("target", {}).get("name") != "RISK_LOGIT_CONTRAST_V1":
            errors.append("v1_target")
        return errors

    for key in REQUIRED_TOP_LEVEL_V1_1:
        if key not in config:
            errors.append(f"missing:{key}")
    if pid != PROTOCOL_ID_V1_1:
        errors.append("protocol_id_mismatch")
    if config.get("amends") != PROTOCOL_ID_V1:
        errors.append("amends")
    if config.get("amended_from_hash") != ATTRIBUTION_PROTOCOL_HASH_V1:
        errors.append("amended_from_hash")

    target = config.get("target") or {}
    if target.get("name") != "RISK_LOGIT_CONTRAST_V1":
        errors.append("target_name")

    cohorts = config.get("cohorts") or {}
    rq1c = cohorts.get("rq1_primary") or {}
    rq234 = cohorts.get("rq234_primary") or {}
    if rq1c.get("n") != 304:
        errors.append("cohort_rq1_n")
    if rq234.get("n") != 475:
        errors.append("cohort_rq234_n")
    if rq234.get("truncated_policy") != "ELIGIBLE_ON_MODEL_VISIBLE_INPUT":
        errors.append("cohort_truncated_policy")

    ops = config.get("perturbation_operators") or {}
    if ops.get("occlusion_attribution") != "SEGMENT_DELETE_V1":
        errors.append("op_occlusion")
    if ops.get("faithfulness_evaluation_primary") != "PAYLOAD_BLANK_V1":
        errors.append("op_faithfulness")

    faith = config.get("faithfulness") or {}
    if faith.get("primary_fractions") != [0.10, 0.20, 0.30, 0.50]:
        errors.append("faith_fractions")
    if "ceil" not in str(faith.get("fraction_rounding", "")).lower():
        errors.append("faith_rounding")
    if faith.get("perturbation_operator_primary") != "PAYLOAD_BLANK_V1":
        errors.append("faith_operator")
    if "deletion_curve" not in faith or "insertion_curve" not in faith:
        errors.append("faith_curves")

    pol = config.get("polarity") or {}
    if "rq3_attention_top2_hunks" not in pol:
        errors.append("rq3_top2")

    rq4 = config.get("rq4") or {}
    dps = rq4.get("diff_polarity_swap") or {}
    if dps.get("name") != "DIFF_POLARITY_SWAP_V1":
        errors.append("rq4_swap")
    tfc = rq4.get("test_file_category") or {}
    if tfc.get("status") != "PENDING_AUDIT":
        errors.append("rq4_testfile_pending")

    miss = config.get("missingness") or {}
    if not miss.get("rules"):
        errors.append("missingness_rules")

    # No TBD leftovers in frozen fields
    def find_tbd(o: Any, path: str = "") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                find_tbd(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                find_tbd(v, f"{path}[{i}]")
        elif isinstance(o, str) and o.startswith("TBD"):
            errors.append(f"tbd:{path}")

    find_tbd(config)
    return errors


def build_manifest(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config if config is not None else load_protocol_config()
    errs = validate_protocol_config(cfg)
    if errs:
        raise ValueError(f"protocol validation failed: {errs}")
    if not verify_v1_hash_intact():
        raise RuntimeError("V1 config hash drift — refuse to amend")
    h = protocol_hash(cfg)
    return {
        "protocol_id": PROTOCOL_ID_V1_1,
        "ATTRIBUTION_PROTOCOL_HASH": h,
        "ATTRIBUTION_PROTOCOL_HASH_V1": ATTRIBUTION_PROTOCOL_HASH_V1,
        "amends": PROTOCOL_ID_V1,
        "config_path": str(DEFAULT_CONFIG.relative_to(ROOT)),
        "v1_config_path": str(V1_CONFIG.relative_to(ROOT)),
        "canonical_sha256": h,
        "validation_errors": [],
        "v1_hash_intact": True,
        "frozen_highlights": {
            "target": "RISK_LOGIT_CONTRAST_V1",
            "rq1_n": 304,
            "rq234_n": 475,
            "occlusion_operator": "SEGMENT_DELETE_V1",
            "faithfulness_operator": "PAYLOAD_BLANK_V1",
            "rq2_fractions": [0.10, 0.20, 0.30, 0.50],
            "fraction_rounding": "ceil",
            "diff_polarity_swap": "DIFF_POLARITY_SWAP_V1",
            "test_file_category": "PENDING_AUDIT",
        },
    }


def write_manifest(out_dir: Path | None = None) -> Path:
    out = out_dir or V1_1_MANIFEST_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    path = out / "protocol_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cfg = load_protocol_config()
    (out / "protocol_canonical.json").write_bytes(canonical_json_bytes(cfg) + b"\n")
    # Pointer at protocol root for current version
    root = DEFAULT_MANIFEST_DIR
    root.mkdir(parents=True, exist_ok=True)
    (root / "protocol_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "CURRENT_PROTOCOL").write_text(
        f"{PROTOCOL_ID_V1_1}\n{manifest['ATTRIBUTION_PROTOCOL_HASH']}\n", encoding="utf-8"
    )
    return path


if __name__ == "__main__":
    assert verify_v1_hash_intact(), "V1 hash must remain intact"
    p = write_manifest()
    m = json.loads(p.read_text(encoding="utf-8"))
    print("V1", m["ATTRIBUTION_PROTOCOL_HASH_V1"])
    print("V1.1", m["ATTRIBUTION_PROTOCOL_HASH"])
    print(p)

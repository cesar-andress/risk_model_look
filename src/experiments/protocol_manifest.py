"""Canonical attribution protocol manifest + deterministic SHA-256 hash.

V1 and V1.1 are historically frozen and must not be overwritten.
Current scientific protocol after reviewer amendment: V1.2.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
V1_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1.yaml"
V1_1_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1_1.yaml"
V1_2_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1_2.yaml"
DEFAULT_CONFIG = V1_2_CONFIG
V1_ARCHIVE_DIR = ROOT / "artifacts" / "attribution_protocol" / "v1"
V1_1_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol" / "v1_1"
V1_2_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol" / "v1_2"
DEFAULT_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol"

PROTOCOL_ID_V1 = "ATTRIBUTION_PROTOCOL_V1"
PROTOCOL_ID_V1_1 = "ATTRIBUTION_PROTOCOL_V1_1"
PROTOCOL_ID_V1_2 = "ATTRIBUTION_PROTOCOL_V1_2"
PROTOCOL_ID = PROTOCOL_ID_V1_2

ATTRIBUTION_PROTOCOL_HASH_V1 = (
    "73f0f891683f926a39d68b078f6e2770a1b42181ba1a9f56575c5556cba4794d"
)
ATTRIBUTION_PROTOCOL_HASH_V1_1 = (
    "ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e"
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
    return protocol_hash(load_protocol_config(V1_CONFIG)) == ATTRIBUTION_PROTOCOL_HASH_V1


def verify_v1_1_hash_intact() -> bool:
    return protocol_hash(load_protocol_config(V1_1_CONFIG)) == ATTRIBUTION_PROTOCOL_HASH_V1_1


def validate_protocol_config(config: dict[str, Any]) -> list[str]:
    """Validate protocol config by version."""
    errors: list[str] = []
    pid = config.get("protocol_id")
    if pid == PROTOCOL_ID_V1:
        if config.get("target", {}).get("name") != "RISK_LOGIT_CONTRAST_V1":
            errors.append("v1_target")
        return errors

    if pid == PROTOCOL_ID_V1_1:
        # Historical V1.1 checks (unchanged contract)
        if config.get("amended_from_hash") != ATTRIBUTION_PROTOCOL_HASH_V1:
            errors.append("amended_from_hash")
        ops = config.get("perturbation_operators") or {}
        if ops.get("faithfulness_evaluation_primary") != "PAYLOAD_BLANK_V1":
            errors.append("op_faithfulness")
        faith = config.get("faithfulness") or {}
        if faith.get("primary_fractions") != [0.10, 0.20, 0.30, 0.50]:
            errors.append("faith_fractions")
        return errors

    if pid != PROTOCOL_ID_V1_2:
        errors.append("protocol_id_mismatch")
        return errors

    if config.get("amends") != PROTOCOL_ID_V1_1:
        errors.append("amends")
    if config.get("amended_from_hash") != ATTRIBUTION_PROTOCOL_HASH_V1_1:
        errors.append("amended_from_hash")
    if not verify_v1_hash_intact():
        errors.append("v1_hash_drift")
    if not verify_v1_1_hash_intact():
        errors.append("v1_1_hash_drift")

    faith = config.get("faithfulness") or {}
    abs_f = faith.get("absolute_perturbation_faithfulness") or {}
    if abs_f.get("primary_endpoint") != "ABS_DELETION_AOPC":
        errors.append("rq2_primary_endpoint")
    if abs_f.get("name") != "ABSOLUTE_PERTURBATION_FAITHFULNESS":
        errors.append("abs_faith_name")
    bud = faith.get("primary_budgeting") or {}
    if bud.get("name") != "TOKEN_BUDGET_PREFIX_V1":
        errors.append("token_budget")
    dir_f = faith.get("directional_faithfulness") or {}
    if not dir_f.get("attention_comparison_forbidden"):
        errors.append("directional_attention_forbidden")

    rq1 = config.get("rq1") or {}
    construct = rq1.get("construct") or {}
    if construct.get("primary_endpoint") != "RECALL_AT_20_PERCENT_EFFORT":
        errors.append("rq1_primary_endpoint")
    if construct.get("is_faithfulness") is not False:
        errors.append("rq1_not_faithfulness")

    occ = config.get("occlusion") or {}
    if occ.get("rq2_role") != "PERTURBATION_REFERENCE":
        errors.append("occlusion_rq2_role")

    rq4 = config.get("rq4") or {}
    dps = rq4.get("diff_polarity_swap") or {}
    if dps.get("role") != "EXPLORATORY_STRUCTURAL_SENSITIVITY":
        errors.append("swap_exploratory")
    tfc = rq4.get("test_file_category") or {}
    if tfc.get("TEST_FILE_SUBANALYSIS") != "DEFERRED_NOT_REQUIRED":
        errors.append("test_file_deferred")
    if "enrichment" not in rq4:
        errors.append("enrichment")

    ig = config.get("ig") or {}
    comp = ig.get("completeness") or {}
    if comp.get("criterion_name") != "COMBINED_ABS_REL_TOL_V1_2":
        errors.append("ig_combined")

    if (config.get("validation_rehearsal") or {}).get("n") != 64:
        errors.append("rehearsal_n")
    neg = (config.get("cohorts") or {}).get("negative_matched_diagnostic") or {}
    if neg.get("n") != 475:
        errors.append("neg_cohort_n")

    scope = config.get("model_comparator_scope") or {}
    if scope.get("M2_SEQUENCE_CLASSIFICATION_HEAD") != "DEFERRED_FROM_CORE":
        errors.append("m2_deferred")
    if scope.get("ENCODER_BASELINE") != "REQUIRED":
        errors.append("encoder_required")

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
    if not verify_v1_1_hash_intact():
        raise RuntimeError("V1.1 config hash drift — refuse to amend")
    h = protocol_hash(cfg)
    return {
        "protocol_id": PROTOCOL_ID_V1_2,
        "ATTRIBUTION_PROTOCOL_HASH": h,
        "ATTRIBUTION_PROTOCOL_HASH_V1": ATTRIBUTION_PROTOCOL_HASH_V1,
        "ATTRIBUTION_PROTOCOL_HASH_V1_1": ATTRIBUTION_PROTOCOL_HASH_V1_1,
        "amends": PROTOCOL_ID_V1_1,
        "config_path": str(DEFAULT_CONFIG.relative_to(ROOT)),
        "v1_config_path": str(V1_CONFIG.relative_to(ROOT)),
        "v1_1_config_path": str(V1_1_CONFIG.relative_to(ROOT)),
        "canonical_sha256": h,
        "validation_errors": [],
        "v1_hash_intact": True,
        "v1_1_hash_intact": True,
        "frozen_highlights": {
            "target": "RISK_LOGIT_CONTRAST_V1",
            "rq1_primary_endpoint": "RECALL_AT_20_PERCENT_EFFORT",
            "rq2_primary_endpoint": "ABS_DELETION_AOPC",
            "rq2_budgeting": "TOKEN_BUDGET_PREFIX_V1",
            "occlusion_rq2_role": "PERTURBATION_REFERENCE",
            "ig_completeness": "COMBINED_ABS_REL_TOL_V1_2",
            "validation_rehearsal_n": 64,
            "negative_diagnostic_n": 475,
            "m2": "DEFERRED_FROM_CORE",
            "encoder_baseline": "REQUIRED",
        },
    }


def write_manifest(out_dir: Path | None = None) -> Path:
    out = out_dir or V1_2_MANIFEST_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    path = out / "protocol_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cfg = load_protocol_config()
    (out / "protocol_canonical.json").write_bytes(canonical_json_bytes(cfg) + b"\n")
    root = DEFAULT_MANIFEST_DIR
    root.mkdir(parents=True, exist_ok=True)
    (root / "protocol_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "CURRENT_PROTOCOL").write_text(
        f"{PROTOCOL_ID_V1_2}\n{manifest['ATTRIBUTION_PROTOCOL_HASH']}\n", encoding="utf-8"
    )
    return path


if __name__ == "__main__":
    assert verify_v1_hash_intact(), "V1 hash must remain intact"
    assert verify_v1_1_hash_intact(), "V1.1 hash must remain intact"
    p = write_manifest()
    m = json.loads(p.read_text(encoding="utf-8"))
    print("V1", m["ATTRIBUTION_PROTOCOL_HASH_V1"])
    print("V1.1", m["ATTRIBUTION_PROTOCOL_HASH_V1_1"])
    print("V1.2", m["ATTRIBUTION_PROTOCOL_HASH"])
    print(p)

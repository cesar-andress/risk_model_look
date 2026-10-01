"""Canonical attribution protocol manifest + deterministic SHA-256 hash.

Future scientific attribution runs MUST embed ATTRIBUTION_PROTOCOL_HASH.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "attribution" / "m1_methods_v1.yaml"
DEFAULT_MANIFEST_DIR = ROOT / "artifacts" / "attribution_protocol"
PROTOCOL_ID = "ATTRIBUTION_PROTOCOL_V1"


def load_protocol_config(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("protocol config must be a mapping")
    return data


def canonicalize(obj: Any) -> Any:
    """JSON-serializable canonical form (sorted keys; stable scalars)."""
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
        # Avoid binary float drift in hash: fixed decimal representation
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


REQUIRED_TOP_LEVEL = (
    "protocol_id",
    "target",
    "rq1",
    "aggregation",
    "attention",
    "ig",
    "occlusion",
    "faithfulness",
    "polarity",
    "random_baselines",
    "methods_primary",
)


def validate_protocol_config(config: dict[str, Any]) -> list[str]:
    """Return list of validation errors (empty => OK)."""
    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL:
        if key not in config:
            errors.append(f"missing:{key}")
    if config.get("protocol_id") != PROTOCOL_ID:
        errors.append("protocol_id_mismatch")

    target = config.get("target") or {}
    if target.get("name") != "RISK_LOGIT_CONTRAST_V1":
        errors.append("target_name")

    rq1 = config.get("rq1") or {}
    if rq1.get("primary_rank_transform_signed_methods") != "ABS_DESCENDING":
        errors.append("rq1_signed_primary_ranking")
    if rq1.get("primary_rank_transform_attention") != "RAW_DESCENDING":
        errors.append("rq1_attention_ranking")
    if rq1.get("sensitivity_rank_transform_signed_methods") != "SIGNED_POSITIVE_DESCENDING":
        errors.append("rq1_sensitivity_ranking")
    if rq1.get("primary_fully_visible_n_2048") != 304:
        errors.append("rq1_n_2048")
    if rq1.get("ablation_fully_visible_n_4096") != 345:
        errors.append("rq1_n_4096")

    agg = config.get("aggregation") or {}
    if agg.get("line_reduction_primary") != "SUM":
        errors.append("agg_primary")
    if agg.get("line_reduction_sensitivity") != "MEAN":
        errors.append("agg_sensitivity")
    if agg.get("frozen") is not True:
        errors.append("agg_not_frozen")

    att = config.get("attention") or {}
    if att.get("primary_preset") != "ATTENTION_LAST_MEAN_HEAD":
        errors.append("attention_primary")
    if att.get("sensitivity_preset") != "ATTENTION_LAST4_MEAN":
        errors.append("attention_sensitivity")

    faith = config.get("faithfulness") or {}
    if faith.get("primary_score_space") != "LOGIT_CONTRAST":
        errors.append("faith_primary_space")
    if faith.get("secondary_score_space") != "RESTRICTED_BINARY_PROBABILITY":
        errors.append("faith_secondary_space")

    ig = config.get("ig") or {}
    if ig.get("primary_baseline") != "ZERO_EMBEDDING":
        errors.append("ig_primary_baseline")
    if ig.get("secondary_baseline") != "PAD_TOKEN_EMBEDDING":
        errors.append("ig_secondary_baseline")
    if ig.get("initial_steps") != 50:
        errors.append("ig_steps")
    if ig.get("retry_steps") != 100:
        errors.append("ig_retry")
    if ig.get("integration_rule") != "GAUSS_LEGENDRE":
        errors.append("ig_integration")
    pad = ig.get("pad_token") or {}
    if pad.get("token_id") != 151643 or pad.get("string") != "<|endoftext|>":
        errors.append("ig_pad_token")
    if pad.get("semantically_neutral_claim") is not False:
        errors.append("ig_pad_neutral_claim")

    pol = config.get("polarity") or {}
    if pol.get("rule_name") != "RELATIVE_POLARITY_EPS_V1":
        errors.append("polarity_rule")

    rb = config.get("random_baselines") or {}
    if rb.get("rq1_repeats") != 100:
        errors.append("random_repeats")

    # No TBD placeholders for frozen fields
    blob = json.dumps(config)
    if "TBD_PROTOCOL" in blob or "TBD" in blob.split('"near_zero')[0]:
        # allow TBD only if somehow leftover; scan key values
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
    h = protocol_hash(cfg)
    return {
        "protocol_id": PROTOCOL_ID,
        "ATTRIBUTION_PROTOCOL_HASH": h,
        "config_path": str(DEFAULT_CONFIG.relative_to(ROOT)),
        "canonical_sha256": h,
        "validation_errors": [],
        "frozen_highlights": {
            "target": "RISK_LOGIT_CONTRAST_V1",
            "rq1_signed_ranking": "ABS_DESCENDING",
            "line_reduction": "SUM",
            "attention_primary": "ATTENTION_LAST_MEAN_HEAD",
            "faithfulness_space": "LOGIT_CONTRAST",
            "ig_primary_baseline": "ZERO_EMBEDDING",
            "ig_steps": 50,
            "polarity": "RELATIVE_POLARITY_EPS_V1",
            "rq1_visible_2048": 304,
        },
    }


def write_manifest(out_dir: Path | None = None) -> Path:
    out = out_dir or DEFAULT_MANIFEST_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    path = out / "protocol_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Also store canonical JSON used for the hash (reproducibility)
    cfg = load_protocol_config()
    (out / "protocol_canonical.json").write_bytes(canonical_json_bytes(cfg) + b"\n")
    return path


if __name__ == "__main__":
    p = write_manifest()
    m = json.loads(p.read_text(encoding="utf-8"))
    print(m["ATTRIBUTION_PROTOCOL_HASH"])
    print(p)

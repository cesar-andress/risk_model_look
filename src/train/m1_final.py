"""Selection, config hashing, and final-training policies for M1."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

FINAL_SEEDS = (13, 42, 73)
PRIMARY_TRAINING_CLASS_POLICY = "NATURAL_PREVALENCE"


def canonicalize_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Drop seed-specific / path-only fields for shared scientific hash."""
    c = copy.deepcopy(cfg)
    # Paths and runtime-only fields excluded from scientific hash
    c.pop("paths", None)
    if "training" in c and isinstance(c["training"], dict):
        # seeds list stays (frozen set); per-run seed is not in shared config file
        c["training"].pop("gpu", None)
    return c


def config_sha256(cfg: dict[str, Any]) -> str:
    blob = json.dumps(canonicalize_config(cfg), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def assert_natural_prevalence_policy(cfg: dict[str, Any]) -> None:
    pol = cfg.get("class_policy") or {}
    if pol.get("name") != PRIMARY_TRAINING_CLASS_POLICY:
        raise RuntimeError(f"class policy must be {PRIMARY_TRAINING_CLASS_POLICY}")
    for k in ("oversample", "undersample", "class_weights", "focal_loss"):
        if pol.get(k):
            raise RuntimeError(f"forbidden class policy flag enabled: {k}")


def assert_final_seeds(seeds: list[int] | tuple[int, ...]) -> None:
    if tuple(sorted(seeds)) != tuple(sorted(FINAL_SEEDS)):
        raise RuntimeError(f"seeds must be exactly {FINAL_SEEDS}, got {seeds}")


def select_checkpoint_by_pr_auc(
    epoch_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """epoch_metrics: list of {epoch, pr_auc, roc_auc, ...}.

    Primary: highest PR-AUC.
    Tie: higher ROC-AUC, then earlier epoch.
    """
    if not epoch_metrics:
        raise ValueError("empty epoch_metrics")
    best = None
    for m in epoch_metrics:
        if best is None:
            best = m
            continue
        if m["pr_auc"] > best["pr_auc"]:
            best = m
        elif m["pr_auc"] == best["pr_auc"]:
            if m["roc_auc"] > best["roc_auc"]:
                best = m
            elif m["roc_auc"] == best["roc_auc"] and m["epoch"] < best["epoch"]:
                best = m
    assert best is not None
    return best


def select_threshold_max_f1(
    y_true: np.ndarray, y_score: np.ndarray
) -> dict[str, Any]:
    """Official validation threshold: max F1 at distinct score values.

    Tie-break: higher F1 → higher recall → lower threshold.
    Candidates: unique scores plus 0.0 and 1.0.
    """
    from src.eval.classification_metrics import metrics_at_threshold_full

    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    uniq = np.unique(y_score)
    candidates = np.unique(np.concatenate([[0.0, 1.0], uniq]))
    best = None
    for t in candidates:
        m = metrics_at_threshold_full(y_true, y_score, float(t))
        if best is None:
            best = m
            continue
        if m["f1"] > best["f1"]:
            best = m
        elif m["f1"] == best["f1"]:
            if m["recall"] > best["recall"]:
                best = m
            elif m["recall"] == best["recall"] and m["threshold"] < best["threshold"]:
                best = m
    assert best is not None
    best["selection"] = "validation_f1"
    best["tie_break"] = ["higher_f1", "higher_recall", "lower_threshold"]
    best["candidate_count"] = int(len(candidates))
    return best


def mean_std(values: list[float]) -> dict[str, float | None]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": None, "std": None, "n": 0}
    if len(arr) == 1:
        return {"mean": float(arr[0]), "std": 0.0, "n": 1}
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)),  # sample SD
        "n": int(len(arr)),
    }


def require_paged_adamw_8bit():
    """Final training requires the pilot-validated optimizer."""
    try:
        import bitsandbytes as bnb

        _ = bnb.optim.PagedAdamW8bit
        return True
    except Exception as e:
        raise RuntimeError(
            "paged_adamw_8bit required for FULL_TRAINING_GATE but unavailable"
        ) from e


def seed_run_dir(artifacts_dir: Path, seed: int) -> Path:
    return artifacts_dir / f"seed_{seed}"


def seed_complete_marker(run_dir: Path) -> Path:
    return run_dir / "SEED_COMPLETE.json"


def threshold_freeze_marker(run_dir: Path) -> Path:
    return run_dir / "THRESHOLD_FROZEN.json"


def test_lock_marker(run_dir: Path) -> Path:
    return run_dir / "TEST_EVALUATED.json"

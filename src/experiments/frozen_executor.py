"""Executor that binds AttributionEngine to the frozen M1 adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.experiments.job_state import JobUnit
from src.experiments.m1_backend import FrozenM1Bundle, NOT_SCIENTIFIC
from src.experiments.runner_core import UNIT_RESULT_SCHEMA_VERSION
from src.train.m1_dataset import load_valid_records


def index_valid_by_commit(repo_root: Path) -> dict[str, dict[str, Any]]:
    recs = load_valid_records(repo_root / "data" / "processed" / "canonical_v1")
    return {r["commit_id"]: r for r in recs}


def make_frozen_m1_executor(
    bundle: FrozenM1Bundle,
    *,
    records: dict[str, dict[str, Any]],
    max_length: int = 2048,
    scientific: bool = False,
):
    """Real-model executor.

    Default ``scientific=False`` stamps NOT_SCIENTIFIC_RESULT. Scientific
    rehearsal must pass scientific=True explicitly and use frozen protocol
    settings; this helper still refuses TEST records.
    """

    def executor(unit: JobUnit, key, out_path: Path) -> dict[str, Any]:
        rec = records.get(unit.commit_id)
        if rec is None:
            raise KeyError(f"commit not in validation index: {unit.commit_id}")
        if str(rec.get("split")) == "test":
            raise RuntimeError("TEST attribution blocked in frozen M1 executor")
        batch = bundle.encode(rec, max_length=max_length)
        method = unit.method.lower()
        if method == "attention":
            scores = bundle.attention_token_scores(
                batch["input_ids"], batch["attention_mask"]
            )
            summary = {"n_tokens": batch["n_tokens"], "n_scores": len(scores)}
        else:
            raise RuntimeError(
                f"executor method {unit.method} not wired for production jobs; "
                "use the GPU benchmark script or a method-specific scientific runner"
            )
        payload = {
            "schema_version": UNIT_RESULT_SCHEMA_VERSION,
            "experiment_id": unit.unit_id,
            "commit_id": unit.commit_id,
            "seed": unit.seed,
            "method": unit.method,
            "granularity": unit.granularity,
            "protocol_hash": key.protocol_hash,
            "model_hash": key.model_hash,
            "status": "DONE",
            "missingness_code": "OK",
            "summary_metrics": summary,
            "n_tokens": batch["n_tokens"],
        }
        if not scientific:
            payload["label"] = NOT_SCIENTIFIC
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return payload

    return executor

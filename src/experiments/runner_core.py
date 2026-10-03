"""Core attribution runner (execution infra; toy/synthetic capable).

Scientific model backends plug in later. This module never loads Qwen.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from src.experiments.attribution_cache import (
    AttributionCacheStore,
    CacheEntry,
    EngineCacheKey,
    build_engine_cache_key,
    stable_json_hash,
)
from src.experiments.attribution_cost import (
    estimate_attribution_cost,
    format_attribution_plan,
)
from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    METHOD_SPECIFIC_MISSINGNESS_POLICY,
    RENDERER_VERSION,
    STATISTICAL_PROTOCOL_HASH,
    TOKEN_MAPPING_VERSION,
)
from src.experiments.job_state import JobUnit
from src.experiments.run_store import (
    AttributionRunStore,
    RunIdentity,
    file_sha256,
    find_latest_run,
    load_run_for_resume,
    new_run_dir,
)

logger = logging.getLogger("attribution_engine")


UNIT_RESULT_SCHEMA_VERSION = "attribution_unit_result_v1"


@dataclass
class RunnerConfig:
    model_checkpoint: str
    seed: int
    cohort: str
    method: str
    granularity: str
    protocol_hash: str = ATTRIBUTION_PROTOCOL_HASH
    stats_hash: str = STATISTICAL_PROTOCOL_HASH
    output_dir: str = "runs"
    cache_dir: str = "artifacts/attribution_cache"
    results_dir: str = "artifacts/attribution_results"
    dataset_version: str = "JIT_DEFECTS4J_CANONICAL_V1"
    model_identifier: str = "toy_or_unspecified"
    model_revision: str = "NONE"
    adapter_path: str | None = None
    perturbation_operator: str = "NONE"
    max_items: int | None = None
    batch_size: int = 8
    workers: int = 1
    force: bool = False
    resume: bool = False
    dry_run: bool = False
    mean_regions_per_commit: float = 20.0
    ig_steps: int = 50
    configuration: dict[str, Any] = field(default_factory=dict)
    commit_ids: list[str] = field(default_factory=list)

    def configuration_hash(self) -> str:
        payload = {
            "method": self.method,
            "granularity": self.granularity,
            "cohort": self.cohort,
            "batch_size": self.batch_size,
            "perturbation_operator": self.perturbation_operator,
            "ig_steps": self.ig_steps,
            "dataset_version": self.dataset_version,
            "renderer_version": RENDERER_VERSION,
            "token_mapping_version": TOKEN_MAPPING_VERSION,
            "extra": self.configuration,
        }
        return stable_json_hash(payload)


UnitExecutor = Callable[[JobUnit, EngineCacheKey, Path], dict[str, Any]]


def default_toy_executor(unit: JobUnit, key: EngineCacheKey, out_path: Path) -> dict[str, Any]:
    """Deterministic synthetic attribution unit (no neural net)."""
    # Stable pseudo-scores from hashes — not scientific results.
    digest = key.digest()
    scores = []
    n = 5
    for i in range(n):
        raw = int(digest[i * 2 : i * 2 + 2], 16) / 255.0 - 0.5
        scores.append(
            {
                "region_id": f"R{i}",
                "raw_score": raw,
                "signed_score": raw,
                "rank_score": abs(raw),
            }
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
        "missingness_policy": METHOD_SPECIFIC_MISSINGNESS_POLICY,
        "regions": scores,
        "summary_metrics": {
            "n_regions": n,
            "max_abs": max(abs(s["raw_score"]) for s in scores),
        },
        "raw_scores_location": str(out_path),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


class AttributionEngine:
    def __init__(
        self,
        cfg: RunnerConfig,
        *,
        repo_root: Path,
        executor: UnitExecutor | None = None,
    ):
        self.cfg = cfg
        self.repo_root = Path(repo_root)
        self.executor = executor or default_toy_executor
        self.cache = AttributionCacheStore(Path(cfg.cache_dir))
        self.model_hash = file_sha256(Path(cfg.model_checkpoint)) if cfg.model_checkpoint not in (
            "",
            "TOY",
            "NONE",
        ) else "TOY_MODEL"
        if cfg.model_checkpoint in ("", "TOY", "NONE"):
            self.model_hash = "TOY_MODEL"
        self.adapter_hash = file_sha256(Path(cfg.adapter_path) if cfg.adapter_path else None)

    def _identity(self) -> RunIdentity:
        return RunIdentity(
            protocol_hash=self.cfg.protocol_hash,
            stats_hash=self.cfg.stats_hash,
            model_hash=self.model_hash,
            adapter_hash=self.adapter_hash,
            configuration_hash=self.cfg.configuration_hash(),
            dataset_version=self.cfg.dataset_version,
            cohort=self.cfg.cohort,
            method=self.cfg.method,
            granularity=self.cfg.granularity,
            seed=self.cfg.seed,
        )

    def resolve_commit_ids(self) -> list[str]:
        ids = list(self.cfg.commit_ids)
        if not ids:
            # Placeholder synthetic cohort for engine tests / dry-run without data.
            n = {"validation_rehearsal": 64, "rq1_primary": 304, "test_positives": 475}.get(
                self.cfg.cohort, 8
            )
            ids = [f"SYNTH_COMMIT_{i:04d}" for i in range(n)]
        if self.cfg.max_items is not None:
            ids = ids[: self.cfg.max_items]
        return ids

    def dry_run_plan(self) -> str:
        ids = self.resolve_commit_ids()
        est = estimate_attribution_cost(
            n_commits=len(ids),
            methods=[self.cfg.method],
            n_seeds=1,
            mean_regions_per_commit=self.cfg.mean_regions_per_commit,
            granularity=self.cfg.granularity,
            ig_steps=self.cfg.ig_steps,
        )
        header = format_attribution_plan(est, method_label=self.cfg.method)
        return (
            header
            + f"\nCohort id: {self.cfg.cohort}\n"
            + f"Commit units (this seed): {len(ids)}\n"
            + f"Protocol: {self.cfg.protocol_hash}\n"
            + f"Stats: {self.cfg.stats_hash}\n"
            + "Model load: SKIPPED (dry-run)\n"
        )

    def _open_store(self) -> AttributionRunStore:
        identity = self._identity()
        base = Path(self.cfg.output_dir)
        if self.cfg.resume:
            latest = find_latest_run(base)
            if latest is None:
                raise FileNotFoundError(f"no run to resume under {base}")
            store = load_run_for_resume(latest)
            store.assert_resume_compatible(identity)
            logger.info("resuming run %s", store.run_dir)
            return store

        if self.cfg.force:
            # Explicit new run even if previous exists
            pass
        run_dir = new_run_dir(base)
        store = AttributionRunStore(run_dir=run_dir, identity=identity)
        store.ensure_layout()
        store.build_manifest(
            repo_root=self.repo_root,
            model_identifier=self.cfg.model_identifier,
            model_revision=self.cfg.model_revision,
            extra={"force": self.cfg.force, "batch_size": self.cfg.batch_size},
        )
        store.save_manifest()
        # seed ledger
        for cid in self.resolve_commit_ids():
            store.ledger.upsert(
                JobUnit(
                    commit_id=cid,
                    seed=self.cfg.seed,
                    method=self.cfg.method,
                    granularity=self.cfg.granularity,
                )
            )
        store.save_ledger()
        return store

    def _cache_key_for(self, unit: JobUnit) -> EngineCacheKey:
        return build_engine_cache_key(
            model_hash=self.model_hash,
            adapter_hash=self.adapter_hash,
            dataset_version=self.cfg.dataset_version,
            commit_id=unit.commit_id,
            method=unit.method,
            granularity=unit.granularity,
            configuration={
                "batch_size": self.cfg.batch_size,
                "ig_steps": self.cfg.ig_steps,
                "extra": self.cfg.configuration,
            },
            seed=unit.seed,
            protocol_hash=self.cfg.protocol_hash,
            perturbation_operator=self.cfg.perturbation_operator,
        )

    def run(self) -> dict[str, Any]:
        if self.cfg.dry_run:
            plan = self.dry_run_plan()
            print(plan)
            return {"dry_run": True, "plan": plan}

        store = self._open_store()
        results_root = Path(self.cfg.results_dir) / store.run_dir.name
        results_root.mkdir(parents=True, exist_ok=True)
        jsonl_path = results_root / "method_results.jsonl"
        cache_index: dict[str, str] = {}

        # On resume, only process unfinished
        todo = []
        for u in store.ledger.units.values():
            if u.status == "DONE" and not self.cfg.force:
                continue
            if u.status in ("SKIPPED", "NONCONVERGED") and not self.cfg.force:
                # NONCONVERGED is terminal scientific missingness — do not auto-retry
                # unless force. FAILED/OOM/RUNNING/PENDING retry.
                if u.status == "NONCONVERGED":
                    continue
            if u.status == "SKIPPED":
                continue
            todo.append(u)

        log_path = store.logs_dir / "engine.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(),
            ],
            force=True,
        )

        for unit in sorted(todo, key=lambda x: x.unit_id):
            key = self._cache_key_for(unit)
            unit.cache_key = key.digest()
            unit.mark_running()
            store.save_ledger()
            out_path = results_root / f"{unit.commit_id}__{unit.method}__{unit.granularity}.json"
            try:
                cached = None if self.cfg.force else self.cache.read(key)
                if cached is not None and cached.status == "DONE":
                    unit.mark_done(
                        result_path=str(cached.metadata.get("result_path", "")),
                        missingness_code=cached.metadata.get("missingness_code", "OK"),
                    )
                    cache_index[unit.unit_id] = key.digest()
                    logger.info("cache hit %s", unit.unit_id)
                else:
                    payload = self.executor(unit, key, out_path)
                    status = payload.get("status", "DONE")
                    miss = payload.get("missingness_code", "OK")
                    if status == "DONE":
                        unit.mark_done(result_path=str(out_path), missingness_code=miss)
                    elif status == "NONCONVERGED":
                        unit.mark_terminal(
                            "NONCONVERGED",
                            missingness_code="IG_NONCONVERGED",
                            result_path=str(out_path),
                            error_message=payload.get("error_message"),
                        )
                    elif status == "OOM":
                        unit.mark_terminal(
                            "OOM",
                            missingness_code="OOM",
                            result_path=str(out_path),
                            error_message=payload.get("error_message"),
                        )
                    else:
                        unit.mark_terminal(
                            "FAILED",
                            missingness_code=payload.get("missingness_code", "ENGINE_ERROR"),
                            result_path=str(out_path),
                            error_message=payload.get("error_message", status),
                        )
                    entry = CacheEntry(
                        cache_key=key.digest(),
                        key_fields=key.__dict__,
                        status=unit.status,
                        result_summary=payload.get("summary_metrics") or {},
                        checksum="",
                        metadata={
                            "result_path": str(out_path),
                            "missingness_code": unit.missingness_code,
                        },
                    )
                    try:
                        self.cache.write(key, entry, force=self.cfg.force or cached is not None)
                    except FileExistsError:
                        if self.cfg.force:
                            self.cache.write(key, entry, force=True)
                        else:
                            raise
                    cache_index[unit.unit_id] = key.digest()
                    # append jsonl summary row
                    row = {
                        "experiment_id": store.manifest.get("run_id"),
                        "commit_id": unit.commit_id,
                        "seed": unit.seed,
                        "method": unit.method,
                        "granularity": unit.granularity,
                        "protocol_hash": self.cfg.protocol_hash,
                        "model_hash": self.model_hash,
                        "status": unit.status,
                        "raw_scores_location": unit.result_path,
                        "summary_metrics": payload.get("summary_metrics"),
                        "missingness_code": unit.missingness_code,
                    }
                    with open(jsonl_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(row, sort_keys=True) + "\n")
                    logger.info(
                        "finished %s status=%s", unit.unit_id, unit.status
                    )
            except MemoryError as e:
                unit.mark_terminal("OOM", error_message=str(e), missingness_code="OOM")
                logger.exception("OOM on %s", unit.unit_id)
            except Exception as e:
                unit.mark_terminal(
                    "FAILED", error_message=str(e), missingness_code="ENGINE_ERROR"
                )
                logger.exception("failure on %s", unit.unit_id)
            store.save_ledger()

        store.cache_index_path.write_text(
            json.dumps(cache_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        summary = {
            "run_dir": str(store.run_dir),
            "counts": store.ledger.counts(),
            "results_jsonl": str(jsonl_path),
        }
        (store.summaries_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return summary

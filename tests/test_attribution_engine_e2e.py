"""CPU-only tests for the attribution execution engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attribution.occlusion import OcclusionUnit, RegionSpec, remove_region_structured
from src.attribution.occlusion import ToyStructuredCommit
from src.experiments.attribution_cache import (
    AttributionCacheStore,
    CacheEntry,
    build_engine_cache_key,
)
from src.experiments.attribution_cost import estimate_attribution_cost
from src.experiments.batching import occlude_regions_batched, plan_batches
from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    STATISTICAL_PROTOCOL_HASH,
)
from src.experiments.job_state import JobLedger, JobUnit
from src.experiments.run_store import RunIdentity, new_run_dir
from src.experiments.runner_core import AttributionEngine, RunnerConfig


def test_cache_key_same_config_same_digest():
    a = build_engine_cache_key(
        model_hash="M1",
        adapter_hash="A1",
        dataset_version="D1",
        commit_id="C1",
        method="ig",
        granularity="LINE",
        configuration={"ig_steps": 50},
        seed=13,
        protocol_hash=ATTRIBUTION_PROTOCOL_HASH,
    )
    b = build_engine_cache_key(
        model_hash="M1",
        adapter_hash="A1",
        dataset_version="D1",
        commit_id="C1",
        method="ig",
        granularity="LINE",
        configuration={"ig_steps": 50},
        seed=13,
        protocol_hash=ATTRIBUTION_PROTOCOL_HASH,
    )
    assert a.digest() == b.digest()


def test_cache_key_changes_with_model_protocol_renderer():
    base = dict(
        adapter_hash="A1",
        dataset_version="D1",
        commit_id="C1",
        method="ig",
        granularity="LINE",
        configuration={"ig_steps": 50},
        seed=13,
    )
    k0 = build_engine_cache_key(model_hash="M1", protocol_hash="P1", **base)
    k1 = build_engine_cache_key(model_hash="M2", protocol_hash="P1", **base)
    k2 = build_engine_cache_key(model_hash="M1", protocol_hash="P2", **base)
    k3 = build_engine_cache_key(
        model_hash="M1", protocol_hash="P1", renderer_version="OTHER", **base
    )
    assert len({k0.digest(), k1.digest(), k2.digest(), k3.digest()}) == 4


def test_job_state_machine_and_ledger(tmp_path: Path):
    u = JobUnit(commit_id="C", seed=13, method="attention", granularity="LINE")
    u.mark_running()
    assert u.status == "RUNNING"
    u.mark_done(result_path="x.json")
    assert u.status == "DONE"
    led = JobLedger()
    led.upsert(u)
    path = tmp_path / "ledger.json"
    led.save(path)
    led2 = JobLedger.load(path)
    assert led2.get(u.unit_id).status == "DONE"


def test_resume_identity_mismatch_stops(tmp_path: Path):
    run_dir = new_run_dir(tmp_path)
    ident = RunIdentity(
        protocol_hash=ATTRIBUTION_PROTOCOL_HASH,
        stats_hash=STATISTICAL_PROTOCOL_HASH,
        model_hash="M",
        adapter_hash="A",
        configuration_hash="CFG",
        dataset_version="D",
        cohort="validation_rehearsal",
        method="attention",
        granularity="LINE",
        seed=13,
    )
    from src.experiments.run_store import AttributionRunStore

    store = AttributionRunStore(run_dir=run_dir, identity=ident)
    store.build_manifest(
        repo_root=Path("."),
        model_identifier="toy",
        model_revision="NONE",
    )
    store.save_manifest()
    other = RunIdentity(**{**ident.__dict__, "model_hash": "OTHER"})
    with pytest.raises(RuntimeError, match="RESUME BLOCKED"):
        store.assert_resume_compatible(other)


def test_dry_run_no_model_load(tmp_path: Path):
    cfg = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="validation_rehearsal",
        method="integrated_gradients",
        granularity="LINE",
        output_dir=str(tmp_path / "runs"),
        dry_run=True,
        max_items=10,
    )
    engine = AttributionEngine(cfg, repo_root=tmp_path)
    out = engine.run()
    assert out["dry_run"] is True
    assert "forward passes" in out["plan"]
    assert not list((tmp_path / "runs").glob("*")) if (tmp_path / "runs").exists() else True


def test_runner_resume_and_cache(tmp_path: Path):
    runs = tmp_path / "runs"
    cache = tmp_path / "cache"
    results = tmp_path / "results"
    cfg = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="tiny",
        method="attention",
        granularity="LINE",
        output_dir=str(runs),
        cache_dir=str(cache),
        results_dir=str(results),
        commit_ids=["C0", "C1", "C2"],
        max_items=3,
    )
    engine = AttributionEngine(cfg, repo_root=tmp_path)
    summary1 = engine.run()
    assert summary1["counts"]["DONE"] == 3

    # Second run with resume should reuse DONE units
    cfg2 = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="tiny",
        method="attention",
        granularity="LINE",
        output_dir=str(runs),
        cache_dir=str(cache),
        results_dir=str(results),
        commit_ids=["C0", "C1", "C2"],
        resume=True,
    )
    engine2 = AttributionEngine(cfg2, repo_root=tmp_path)
    summary2 = engine2.run()
    assert summary2["counts"]["DONE"] == 3


def test_rollback_isolation_new_run_dir(tmp_path: Path):
    runs = tmp_path / "runs"
    cfg = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="tiny",
        method="attention",
        granularity="LINE",
        output_dir=str(runs),
        cache_dir=str(tmp_path / "cache"),
        results_dir=str(tmp_path / "results"),
        commit_ids=["C0"],
    )
    AttributionEngine(cfg, repo_root=tmp_path).run()
    AttributionEngine(cfg, repo_root=tmp_path).run()
    dirs = sorted(runs.glob("attribution_run_*"))
    assert len(dirs) == 2
    # first run ledger untouched by second
    led1 = json.loads((dirs[0] / "checkpoints" / "job_ledger.json").read_text())
    assert led1["units"][0]["status"] == "DONE"


def test_failure_recovery_records_failed(tmp_path: Path):
    def bad_executor(unit, key, out_path):
        raise RuntimeError("boom")

    cfg = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="tiny",
        method="attention",
        granularity="LINE",
        output_dir=str(tmp_path / "runs"),
        cache_dir=str(tmp_path / "cache"),
        results_dir=str(tmp_path / "results"),
        commit_ids=["C0"],
    )
    summary = AttributionEngine(cfg, repo_root=tmp_path, executor=bad_executor).run()
    assert summary["counts"]["FAILED"] == 1


def test_occlusion_batched_matches_sequential_semantics():
    commit = ToyStructuredCommit(
        message="m",
        files={
            "a.py": [
                {"stable_line_id": "L0", "hunk_id": "H0", "change_type": "ADD", "text": "a"},
                {"stable_line_id": "L1", "hunk_id": "H0", "change_type": "ADD", "text": "b"},
            ]
        },
    )
    regions = [
        RegionSpec(unit=OcclusionUnit.LINE, region_id="L0", stable_line_ids=("L0",)),
        RegionSpec(unit=OcclusionUnit.LINE, region_id="L1", stable_line_ids=("L1",)),
    ]

    def score_fn(c):
        return float(sum(len(v) for v in c.files.values()))

    batched = occlude_regions_batched(
        commit, regions, score_fn=score_fn, remove_fn=remove_region_structured, batch_size=2
    )
    assert len(batched) == 2
    assert batched[0].delta == score_fn(commit) - score_fn(
        remove_region_structured(commit, regions[0])
    )


def test_cost_estimator_positive():
    est = estimate_attribution_cost(
        n_commits=475,
        methods=["attention", "integrated_gradients", "occlusion"],
        n_seeds=3,
        ig_steps=50,
    )
    assert est.forward_passes > 0
    assert est.ig_step_evals == 475 * 3 * 50


def test_batch_plan():
    assert plan_batches(10, 8).n_batches == 2

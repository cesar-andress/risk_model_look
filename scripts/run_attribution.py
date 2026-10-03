#!/usr/bin/env python3
"""Resumable attribution execution runner (engineering infra).

Does not modify scientific protocols. Default executor is CPU toy/synthetic;
wire a real backend after M1 completes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    STATISTICAL_PROTOCOL_HASH,
)
from src.experiments.runner_core import AttributionEngine, RunnerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Attribution execution engine")
    p.add_argument("--model-checkpoint", default="TOY", help="Checkpoint path or TOY")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--cohort", required=True, help="e.g. validation_rehearsal, test_positives")
    p.add_argument("--method", required=True)
    p.add_argument("--granularity", default="LINE")
    p.add_argument("--protocol-hash", default=ATTRIBUTION_PROTOCOL_HASH)
    p.add_argument("--stats-hash", default=STATISTICAL_PROTOCOL_HASH)
    p.add_argument("--output-dir", default="runs")
    p.add_argument("--cache-dir", default="artifacts/attribution_cache")
    p.add_argument("--results-dir", default="artifacts/attribution_results")
    p.add_argument("--adapter-path", default=None)
    p.add_argument("--dataset-version", default="JIT_DEFECTS4J_CANONICAL_V1")
    p.add_argument("--model-identifier", default="toy_or_unspecified")
    p.add_argument("--model-revision", default="NONE")
    p.add_argument("--perturbation-operator", default="NONE")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-items", type=int, default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--mean-regions", type=float, default=20.0)
    p.add_argument("--ig-steps", type=int, default=50)
    p.add_argument(
        "--commit-id",
        action="append",
        default=[],
        help="Optional explicit commit id (repeatable). Default: synthetic cohort sizes.",
    )
    p.add_argument(
        "--backend",
        default="toy",
        choices=["toy", "frozen_m1"],
        help="toy = synthetic CPU executor; frozen_m1 = selected QLoRA adapter",
    )
    p.add_argument(
        "--scientific",
        action="store_true",
        help="Allow unlabeled scientific payloads. Default stamps NOT_SCIENTIFIC_RESULT.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if "test" in args.cohort.lower() and args.backend == "frozen_m1":
        raise SystemExit("TEST attribution is blocked in this runner path")
    if args.protocol_hash != ATTRIBUTION_PROTOCOL_HASH and not args.dry_run:
        print(
            f"WARNING: protocol-hash != frozen V1.2\n"
            f"  got:  {args.protocol_hash}\n"
            f"  want: {ATTRIBUTION_PROTOCOL_HASH}",
            file=sys.stderr,
        )
    cfg = RunnerConfig(
        model_checkpoint=args.model_checkpoint,
        seed=args.seed,
        cohort=args.cohort,
        method=args.method,
        granularity=args.granularity,
        protocol_hash=args.protocol_hash,
        stats_hash=args.stats_hash,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        results_dir=args.results_dir,
        dataset_version=args.dataset_version,
        model_identifier=args.model_identifier,
        model_revision=args.model_revision,
        adapter_path=args.adapter_path,
        perturbation_operator=args.perturbation_operator,
        max_items=args.max_items,
        batch_size=args.batch_size,
        workers=args.workers,
        force=args.force,
        resume=args.resume,
        dry_run=args.dry_run,
        mean_regions_per_commit=args.mean_regions,
        ig_steps=args.ig_steps,
        commit_ids=list(args.commit_id),
    )
    executor = None
    if args.backend == "frozen_m1" and not args.dry_run:
        from src.experiments.frozen_executor import (
            index_valid_by_commit,
            make_frozen_m1_executor,
        )
        from src.experiments.m1_backend import FrozenM1Bundle

        bundle = FrozenM1Bundle(
            repo_root=REPO_ROOT,
            seed=args.seed,
            protocol_hash=args.protocol_hash,
            stats_hash=args.stats_hash,
        )
        cfg.model_identifier = bundle.ident.base_model
        cfg.model_revision = bundle.ident.base_revision
        cfg.adapter_path = str(bundle.ident.adapter_dir)
        cfg.model_checkpoint = str(bundle.ident.adapter_dir)
        records = index_valid_by_commit(REPO_ROOT)
        executor = make_frozen_m1_executor(
            bundle,
            records=records,
            max_length=2048,
            scientific=bool(args.scientific),
        )
    engine = AttributionEngine(cfg, repo_root=REPO_ROOT, executor=executor)
    summary = engine.run()
    if not args.dry_run:
        print(json_dumps(summary))
    return 0


def json_dumps(obj: object) -> str:
    import json

    return json.dumps(obj, indent=2, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())

"""Isolated attribution run directories, manifests, and resume guards."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    ENGINE_VERSION,
    STATISTICAL_PROTOCOL_HASH,
)
from src.experiments.job_state import JobLedger, utc_now_iso


def _git_info(repo_root: Path) -> dict[str, str]:
    def _run(args: list[str]) -> str:
        try:
            out = subprocess.check_output(
                args, cwd=str(repo_root), stderr=subprocess.DEVNULL, text=True
            )
            return out.strip()
        except Exception:
            return "UNKNOWN"

    return {
        "git_commit": _run(["git", "rev-parse", "HEAD"]),
        "git_branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "git_dirty": "true" if _run(["git", "status", "--porcelain"]) else "false",
    }


def file_sha256(path: Path | None) -> str:
    if path is None:
        return "NONE"
    p = Path(path)
    if p.is_dir():
        for name in ("adapter_model.safetensors", "pytorch_model.bin"):
            cand = p / name
            if cand.is_file():
                p = cand
                break
        else:
            return "NONE"
    if not p.is_file():
        return "NONE"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RunIdentity:
    protocol_hash: str
    stats_hash: str
    model_hash: str
    adapter_hash: str
    configuration_hash: str
    dataset_version: str
    cohort: str
    method: str
    granularity: str
    seed: int
    engine_version: str = ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AttributionRunStore:
    run_dir: Path
    identity: RunIdentity
    manifest: dict[str, Any] = field(default_factory=dict)
    ledger: JobLedger = field(default_factory=JobLedger)

    @property
    def jobs_path(self) -> Path:
        return self.run_dir / "checkpoints" / "job_ledger.json"

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    @property
    def config_path(self) -> Path:
        return self.run_dir / "config.yaml"

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def summaries_dir(self) -> Path:
        return self.run_dir / "summaries"

    @property
    def cache_index_path(self) -> Path:
        return self.run_dir / "cache_index.json"

    def ensure_layout(self) -> None:
        for p in (
            self.run_dir,
            self.logs_dir,
            self.summaries_dir,
            self.run_dir / "checkpoints",
        ):
            p.mkdir(parents=True, exist_ok=True)

    def build_manifest(
        self,
        *,
        repo_root: Path,
        model_identifier: str,
        model_revision: str,
        hardware: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        git = _git_info(repo_root)
        run_id = self.run_dir.name
        hw = hardware or {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        }
        self.manifest = {
            "run_id": run_id,
            "timestamp": utc_now_iso(),
            "git_commit": git["git_commit"],
            "branch": git["git_branch"],
            "git_dirty": git["git_dirty"],
            "protocol_hash": self.identity.protocol_hash,
            "statistics_hash": self.identity.stats_hash,
            "model_identifier": model_identifier,
            "model_revision": model_revision,
            "model_hash": self.identity.model_hash,
            "adapter_hash": self.identity.adapter_hash,
            "dataset_version": self.identity.dataset_version,
            "cohort": self.identity.cohort,
            "method": self.identity.method,
            "granularity": self.identity.granularity,
            "seed": self.identity.seed,
            "configuration_hash": self.identity.configuration_hash,
            "engine_version": self.identity.engine_version,
            "hardware": hw,
            "software_versions": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "random_seeds": {"model_seed": self.identity.seed},
        }
        if extra:
            self.manifest["extra"] = extra
        return self.manifest

    def save_manifest(self) -> None:
        self.ensure_layout()
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def save_ledger(self) -> None:
        self.ensure_layout()
        self.ledger.save(self.jobs_path)

    def load_ledger(self) -> None:
        if self.jobs_path.exists():
            self.ledger = JobLedger.load(self.jobs_path)

    def assert_resume_compatible(self, other: RunIdentity) -> None:
        checks = [
            ("protocol_hash", self.identity.protocol_hash, other.protocol_hash),
            ("configuration_hash", self.identity.configuration_hash, other.configuration_hash),
            ("model_hash", self.identity.model_hash, other.model_hash),
            ("adapter_hash", self.identity.adapter_hash, other.adapter_hash),
            ("stats_hash", self.identity.stats_hash, other.stats_hash),
            ("dataset_version", self.identity.dataset_version, other.dataset_version),
            ("method", self.identity.method, other.method),
            ("cohort", self.identity.cohort, other.cohort),
            ("granularity", self.identity.granularity, other.granularity),
            ("seed", str(self.identity.seed), str(other.seed)),
        ]
        mismatches = [name for name, a, b in checks if a != b]
        if mismatches:
            raise RuntimeError(
                "RESUME BLOCKED: identity mismatch on " + ", ".join(mismatches)
            )


def new_run_dir(base: Path, *, timestamp: str | None = None) -> Path:
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = Path(base) / f"attribution_run_{ts}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def find_latest_run(base: Path) -> Path | None:
    base = Path(base)
    if not base.exists():
        return None
    runs = sorted(
        [p for p in base.iterdir() if p.is_dir() and p.name.startswith("attribution_run_")],
        key=lambda p: p.name,
    )
    return runs[-1] if runs else None


def load_run_for_resume(run_dir: Path) -> AttributionRunStore:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    identity = RunIdentity(
        protocol_hash=manifest["protocol_hash"],
        stats_hash=manifest["statistics_hash"],
        model_hash=manifest["model_hash"],
        adapter_hash=manifest["adapter_hash"],
        configuration_hash=manifest["configuration_hash"],
        dataset_version=manifest["dataset_version"],
        cohort=manifest["cohort"],
        method=manifest["method"],
        granularity=manifest["granularity"],
        seed=int(manifest["seed"]),
        engine_version=manifest.get("engine_version", ENGINE_VERSION),
    )
    store = AttributionRunStore(run_dir=run_dir, identity=identity, manifest=manifest)
    store.load_ledger()
    return store


DEFAULT_PROTOCOL = ATTRIBUTION_PROTOCOL_HASH
DEFAULT_STATS = STATISTICAL_PROTOCOL_HASH

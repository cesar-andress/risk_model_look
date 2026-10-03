"""Job unit state machine for attribution execution."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.experiments.engine_constants import JOB_STATES, MISSINGNESS_CODES


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class JobUnit:
    commit_id: str
    seed: int
    method: str
    granularity: str
    status: str = "PENDING"
    start_time: str | None = None
    end_time: str | None = None
    error_message: str | None = None
    result_path: str | None = None
    missingness_code: str = "OK"
    cache_key: str | None = None
    attempt: int = 0

    def __post_init__(self) -> None:
        if self.status not in JOB_STATES:
            raise ValueError(f"invalid status: {self.status}")
        if self.missingness_code not in MISSINGNESS_CODES:
            raise ValueError(f"invalid missingness: {self.missingness_code}")

    @property
    def unit_id(self) -> str:
        return f"{self.commit_id}|{self.seed}|{self.method}|{self.granularity}"

    def mark_running(self) -> None:
        self.status = "RUNNING"
        self.start_time = utc_now_iso()
        self.attempt += 1
        self.error_message = None

    def mark_done(self, *, result_path: str, missingness_code: str = "OK") -> None:
        self.status = "DONE"
        self.end_time = utc_now_iso()
        self.result_path = result_path
        self.missingness_code = missingness_code
        self.error_message = None

    def mark_terminal(
        self,
        status: str,
        *,
        error_message: str | None = None,
        missingness_code: str = "ENGINE_ERROR",
        result_path: str | None = None,
    ) -> None:
        if status not in ("FAILED", "OOM", "NONCONVERGED", "SKIPPED"):
            raise ValueError(f"not a terminal failure status: {status}")
        self.status = status
        self.end_time = utc_now_iso()
        self.error_message = error_message
        self.missingness_code = missingness_code
        if result_path is not None:
            self.result_path = result_path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JobUnit":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class JobLedger:
    units: dict[str, JobUnit] = field(default_factory=dict)

    def upsert(self, unit: JobUnit) -> None:
        self.units[unit.unit_id] = unit

    def get(self, unit_id: str) -> JobUnit | None:
        return self.units.get(unit_id)

    def pending_or_retryable(self) -> list[JobUnit]:
        out: list[JobUnit] = []
        for u in self.units.values():
            if u.status in ("PENDING", "RUNNING", "FAILED", "OOM"):
                # RUNNING after crash is treated as retryable on resume
                out.append(u)
        return out

    def counts(self) -> dict[str, int]:
        c = {s: 0 for s in JOB_STATES}
        for u in self.units.values():
            c[u.status] = c.get(u.status, 0) + 1
        return c

    def to_list(self) -> list[dict[str, Any]]:
        return [u.to_dict() for u in sorted(self.units.values(), key=lambda x: x.unit_id)]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"units": self.to_list()}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "JobLedger":
        data = json.loads(path.read_text(encoding="utf-8"))
        ledger = cls()
        for row in data.get("units", []):
            u = JobUnit.from_dict(row)
            ledger.upsert(u)
        return ledger

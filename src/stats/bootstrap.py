"""Commit-cluster bootstrap (Protocol V1)."""

from __future__ import annotations

import hashlib
from typing import Callable, Mapping, Sequence

import numpy as np

BOOTSTRAP_REPEATS = 10000
CI_PERCENTILES = (2.5, 97.5)


def derive_bootstrap_seed(
    statistical_protocol_hash: str,
    rq: str,
    metric: str,
    comparison_id: str,
) -> int:
    """Deterministic RNG seed from protocol hash + analysis identifiers."""
    payload = f"{statistical_protocol_hash}|{rq}|{metric}|{comparison_id}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def paired_commit_bootstrap_percentile(
    commit_ids: Sequence[str],
    statistic_fn: Callable[[Sequence[str]], float],
    *,
    rng_seed: int,
    repeats: int = BOOTSTRAP_REPEATS,
    percentiles: tuple[float, float] = CI_PERCENTILES,
) -> dict[str, float | int]:
    """PAIRED_COMMIT_BOOTSTRAP_PERCENTILE_V1.

    Resamples commits with replacement. ``statistic_fn`` receives the resampled
    commit-id list and must use cluster semantics (all seeds for a commit stay
    together) — the function is responsible for looking up commit-level aggregates.
    """
    ids = list(commit_ids)
    n = len(ids)
    if n == 0:
        return {
            "n_commits": 0,
            "repeats": repeats,
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "point": float("nan"),
        }
    rng = np.random.default_rng(rng_seed)
    point = float(statistic_fn(ids))
    samples = np.empty(repeats, dtype=float)
    for i in range(repeats):
        draw = rng.choice(ids, size=n, replace=True)
        samples[i] = float(statistic_fn(list(draw)))
    lo, hi = np.percentile(samples, list(percentiles))
    return {
        "n_commits": n,
        "repeats": repeats,
        "point": point,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "method": "PAIRED_COMMIT_BOOTSTRAP_PERCENTILE_V1",
    }


def cluster_mean_of_commit_values(
    commit_values: Mapping[str, float],
    sampled_commit_ids: Sequence[str],
) -> float:
    """Helper: mean of pre-aggregated commit-level values under a bootstrap draw."""
    if not sampled_commit_ids:
        return float("nan")
    return float(np.mean([commit_values[c] for c in sampled_commit_ids]))


def assert_cluster_keeps_seeds_together(
    commit_to_seed_rows: Mapping[str, Sequence[tuple[int, float]]],
    sampled_commits: Sequence[str],
) -> list[tuple[str, int, float]]:
    """Regression helper: expanding a commit draw yields all seed rows for that commit."""
    out: list[tuple[str, int, float]] = []
    for cid in sampled_commits:
        for seed, val in commit_to_seed_rows[cid]:
            out.append((cid, seed, float(val)))
    return out

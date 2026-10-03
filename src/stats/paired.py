"""Paired commit-level aggregation and Wilcoxon signed-rank (Protocol V1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
from scipy import stats

MIN_COMMON_VALID_SEEDS = 2
WILCOXON_ZERO_METHOD = "pratt"
LOW_N_THRESHOLD = 30


@dataclass(frozen=True)
class CommitPairDiff:
    commit_id: str
    diff: float
    n_common_seeds: int
    seeds_used: tuple[int, ...]


@dataclass(frozen=True)
class PairwiseInclusion:
    n_total_candidate: int
    n_included: int
    n_excluded_missingness: int
    commit_diffs: tuple[CommitPairDiff, ...]
    low_power_exploratory: bool


def common_valid_seeds(
    a_by_seed: Mapping[int, float | None],
    b_by_seed: Mapping[int, float | None],
) -> list[int]:
    """Seeds where both A and B have non-None valid values."""
    keys = sorted(set(a_by_seed) & set(b_by_seed))
    return [s for s in keys if a_by_seed[s] is not None and b_by_seed[s] is not None]


def commit_paired_difference(
    a_by_seed: Mapping[int, float | None],
    b_by_seed: Mapping[int, float | None],
    *,
    commit_id: str,
    min_common: int = MIN_COMMON_VALID_SEEDS,
) -> CommitPairDiff | None:
    """Mean over common-valid seeds of (A_seed - B_seed). Exclude if < min_common."""
    seeds = common_valid_seeds(a_by_seed, b_by_seed)
    if len(seeds) < min_common:
        return None
    diffs = [float(a_by_seed[s]) - float(b_by_seed[s]) for s in seeds]  # type: ignore[arg-type]
    return CommitPairDiff(
        commit_id=commit_id,
        diff=float(np.mean(diffs)),
        n_common_seeds=len(seeds),
        seeds_used=tuple(seeds),
    )


def build_pairwise_commit_diffs(
    per_commit_method_a: Mapping[str, Mapping[int, float | None]],
    per_commit_method_b: Mapping[str, Mapping[int, float | None]],
    *,
    min_common: int = MIN_COMMON_VALID_SEEDS,
) -> PairwiseInclusion:
    """Aggregate A−B to one difference per commit (no seed×commit flattening)."""
    commits = sorted(set(per_commit_method_a) | set(per_commit_method_b))
    included: list[CommitPairDiff] = []
    for cid in commits:
        a = per_commit_method_a.get(cid, {})
        b = per_commit_method_b.get(cid, {})
        d = commit_paired_difference(a, b, commit_id=cid, min_common=min_common)
        if d is not None:
            included.append(d)
    n_inc = len(included)
    return PairwiseInclusion(
        n_total_candidate=len(commits),
        n_included=n_inc,
        n_excluded_missingness=len(commits) - n_inc,
        commit_diffs=tuple(included),
        low_power_exploratory=n_inc < LOW_N_THRESHOLD,
    )


@dataclass(frozen=True)
class WilcoxonResult:
    status: str  # OK | ALL_ZERO_DIFFERENCES
    n: int
    n_zero_diffs: int
    statistic: float | None
    p_value: float
    raw_diffs: tuple[float, ...]
    low_power_exploratory: bool


def wilcoxon_signed_rank(
    commit_diffs: Sequence[float],
    *,
    alternative: str = "two-sided",
    zero_method: str = WILCOXON_ZERO_METHOD,
) -> WilcoxonResult:
    """Two-sided Wilcoxon signed-rank with Pratt zero handling."""
    diffs = [float(x) for x in commit_diffs]
    n = len(diffs)
    n_zero = sum(1 for d in diffs if d == 0.0)
    low = n < LOW_N_THRESHOLD
    if n == 0:
        return WilcoxonResult(
            status="EMPTY",
            n=0,
            n_zero_diffs=0,
            statistic=None,
            p_value=float("nan"),
            raw_diffs=(),
            low_power_exploratory=True,
        )
    if all(d == 0.0 for d in diffs):
        return WilcoxonResult(
            status="ALL_ZERO_DIFFERENCES",
            n=n,
            n_zero_diffs=n_zero,
            statistic=0.0,
            p_value=1.0,
            raw_diffs=tuple(diffs),
            low_power_exploratory=low,
        )
    # scipy: zero_method in {'wilcox','pratt','zsplit'}; use asymptotic (no mode switch by p)
    res = stats.wilcoxon(
        diffs,
        alternative=alternative,
        zero_method=zero_method,
        method="asymptotic",
    )
    return WilcoxonResult(
        status="OK",
        n=n,
        n_zero_diffs=n_zero,
        statistic=float(res.statistic),
        p_value=float(res.pvalue),
        raw_diffs=tuple(diffs),
        low_power_exploratory=low,
    )


def one_sample_wilcoxon_against_zero(
    commit_values: Sequence[float],
    *,
    zero_method: str = WILCOXON_ZERO_METHOD,
) -> WilcoxonResult:
    """One-sample Wilcoxon signed-rank of values vs 0 (e.g. polarity-swap deltas)."""
    return wilcoxon_signed_rank(commit_values, zero_method=zero_method)


def collapse_random_baseline_perms(
    per_commit_perm_metrics: Mapping[str, Sequence[float]],
) -> dict[str, float]:
    """Collapse 100 random perms → expected commit-level baseline (mean)."""
    return {cid: float(np.mean(vals)) for cid, vals in per_commit_perm_metrics.items()}


def descriptive_seed_summary(
    values_by_seed: Mapping[int, float],
) -> dict[str, float]:
    """Per-seed values already given; report mean ± sample SD across seeds."""
    arr = np.asarray(list(values_by_seed.values()), dtype=float)
    if len(arr) == 0:
        return {"mean": float("nan"), "sd": float("nan"), "n_seeds": 0}
    if len(arr) == 1:
        return {"mean": float(arr[0]), "sd": 0.0, "n_seeds": 1}
    return {
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)),
        "n_seeds": int(len(arr)),
    }

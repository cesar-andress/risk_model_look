"""RQ-level statistical orchestration stubs (no real result consumption).

Entrypoint scaffolding for regenerating tables from frozen result files later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from src.stats.effect_sizes import (
    direction_of_better_performance,
    matched_pairs_rank_biserial,
    point_biserial_correlation,
    raw_difference_summary,
)
from src.stats.multiplicity import holm_adjust
from src.stats.paired import (
    MIN_COMMON_VALID_SEEDS,
    build_pairwise_commit_diffs,
    collapse_random_baseline_perms,
    one_sample_wilcoxon_against_zero,
    wilcoxon_signed_rank,
)


RQ1_PRIMARY_ENDPOINTS = (
    ("Top-1", "HIGHER_BETTER"),
    ("Top-5", "HIGHER_BETTER"),
    ("Top-10", "HIGHER_BETTER"),
    ("IFA", "LOWER_BETTER"),
    ("Recall@20%Effort", "HIGHER_BETTER"),
    ("Effort@20%Recall", "LOWER_BETTER"),
)

RQ2_PRIMARY_ENDPOINTS = (
    ("DELETION_AOPC", "HIGHER_BETTER"),
    ("INSERTION_AOPC", "HIGHER_BETTER"),
)


@dataclass(frozen=True)
class PairwiseReport:
    method_a: str
    method_b: str
    metric: str
    family: str
    role: str
    n_total: int
    n_included: int
    n_excluded: int
    low_power_exploratory: bool
    wilcoxon_status: str
    p_raw: float
    n_zero_diffs: int
    rank_biserial: float
    direction_of_better: str
    raw_summary: dict[str, float]


def analyze_pairwise_commit_methods(
    *,
    method_a: str,
    method_b: str,
    metric: str,
    metric_direction: str,
    per_commit_a: Mapping[str, Mapping[int, float | None]],
    per_commit_b: Mapping[str, Mapping[int, float | None]],
    family: str,
    role: str = "PRIMARY",
    min_common: int = MIN_COMMON_VALID_SEEDS,
) -> PairwiseReport:
    """Primary paired analysis path (synthetic or frozen results)."""
    inc = build_pairwise_commit_diffs(per_commit_a, per_commit_b, min_common=min_common)
    diffs = [c.diff for c in inc.commit_diffs]
    w = wilcoxon_signed_rank(diffs)
    rrb = matched_pairs_rank_biserial(diffs)
    # first larger if mean diff > 0
    first_larger = (float(sum(diffs) / len(diffs)) > 0) if diffs else False
    direction = direction_of_better_performance(
        metric_direction=metric_direction,  # type: ignore[arg-type]
        first_method_larger=first_larger,
    )
    return PairwiseReport(
        method_a=method_a,
        method_b=method_b,
        metric=metric,
        family=family,
        role=role,
        n_total=inc.n_total_candidate,
        n_included=inc.n_included,
        n_excluded=inc.n_excluded_missingness,
        low_power_exploratory=inc.low_power_exploratory or w.low_power_exploratory,
        wilcoxon_status=w.status,
        p_raw=w.p_value,
        n_zero_diffs=w.n_zero_diffs,
        rank_biserial=rrb if w.status != "ALL_ZERO_DIFFERENCES" else 0.0,
        direction_of_better=direction,
        raw_summary=raw_difference_summary(diffs),
    )


def apply_family_holm(
    reports: Sequence[PairwiseReport],
    *,
    family: str,
) -> list[tuple[PairwiseReport, float]]:
    """Attach Holm-adjusted p within one family (PRIMARY only)."""
    subset = [r for r in reports if r.family == family and r.role == "PRIMARY"]
    adjusted = holm_adjust(
        [(f"{r.method_a}__{r.method_b}__{r.metric}", r.p_raw) for r in subset],
        family=family,
        role="PRIMARY",
    )
    by_name = {h.name: h.adjusted_p for h in adjusted}
    out = []
    for r in subset:
        key = f"{r.method_a}__{r.method_b}__{r.metric}"
        out.append((r, by_name[key]))
    return out


def rq4_point_biserial_per_seed(
    mass_by_seed: Mapping[int, Sequence[float]],
    correct_by_seed: Mapping[int, Sequence[int]],
) -> dict[int, float]:
    return {
        s: point_biserial_correlation(mass_by_seed[s], correct_by_seed[s])
        for s in sorted(set(mass_by_seed) & set(correct_by_seed))
    }


def rq4_polarity_swap_inference(
    commit_delta_logit: Mapping[str, float],
) -> dict:
    vals = list(commit_delta_logit.values())
    w = one_sample_wilcoxon_against_zero(vals)
    return {
        "wilcoxon": w,
        "rank_biserial": matched_pairs_rank_biserial(vals),
        "raw": raw_difference_summary(vals),
        "role": "PRIMARY",
    }


def prepare_random_baseline_for_inference(
    per_commit_perms: Mapping[str, Sequence[float]],
) -> dict[str, float]:
    return collapse_random_baseline_perms(per_commit_perms)

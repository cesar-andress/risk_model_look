"""Effect sizes for paired commit-level comparisons (Protocol V1)."""

from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

MetricDirection = Literal["HIGHER_BETTER", "LOWER_BETTER"]


def matched_pairs_rank_biserial(
    paired_diffs: Sequence[float],
) -> float:
    """Matched-pairs rank-biserial correlation (Kerby / Wilcoxon-compatible).

    Orientation (frozen): positive ⇒ first-listed method has larger metric
    (more positive A−B differences dominate ranks). Does NOT flip for
    lower-is-better; use ``direction_of_better_performance`` separately.
    """
    diffs = np.asarray(list(paired_diffs), dtype=float)
    n = len(diffs)
    if n == 0:
        return float("nan")
    if np.all(diffs == 0):
        return 0.0
    # Exclude zeros from ranking for classic paired rrb = (T_plus - T_minus) / T
    nonzero = diffs[diffs != 0]
    if len(nonzero) == 0:
        return 0.0
    abs_ranks = stats_rankdata(np.abs(nonzero))
    t_plus = float(abs_ranks[nonzero > 0].sum()) if np.any(nonzero > 0) else 0.0
    t_minus = float(abs_ranks[nonzero < 0].sum()) if np.any(nonzero < 0) else 0.0
    t = t_plus + t_minus
    if t == 0:
        return 0.0
    return (t_plus - t_minus) / t


def stats_rankdata(x: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata

    return rankdata(x, method="average")


def direction_of_better_performance(
    *,
    metric_direction: MetricDirection,
    first_method_larger: bool,
) -> str:
    """Map raw orientation to which method is better (does not flip diffs)."""
    if metric_direction == "HIGHER_BETTER":
        return "FIRST_BETTER" if first_method_larger else "SECOND_BETTER"
    # LOWER_BETTER: larger raw metric is worse
    return "SECOND_BETTER" if first_method_larger else "FIRST_BETTER"


def raw_difference_summary(paired_diffs: Sequence[float]) -> dict[str, float]:
    arr = np.asarray(list(paired_diffs), dtype=float)
    if len(arr) == 0:
        return {
            "median_paired_diff": float("nan"),
            "mean_paired_diff": float("nan"),
            "iqr_paired_diff": float("nan"),
            "n": 0,
        }
    q75, q25 = np.percentile(arr, [75, 25])
    return {
        "median_paired_diff": float(np.median(arr)),
        "mean_paired_diff": float(np.mean(arr)),
        "iqr_paired_diff": float(q75 - q25),
        "n": int(len(arr)),
    }


def cliffs_delta_unpaired(
    x: Sequence[float],
    y: Sequence[float],
) -> float:
    """Cliff's δ as SECONDARY_LEGACY_EFFECT_SIZE only (not primary; unpaired)."""
    xs = list(x)
    ys = list(y)
    if not xs or not ys:
        return float("nan")
    more = less = 0
    for a in xs:
        for b in ys:
            if a > b:
                more += 1
            elif a < b:
                less += 1
    n = len(xs) * len(ys)
    return (more - less) / n if n else float("nan")


def point_biserial_correlation(
    continuous: Sequence[float],
    binary: Sequence[int],
) -> float:
    """Point-biserial correlation (PRIMARY RQ4 association measure)."""
    x = np.asarray(list(continuous), dtype=float)
    y = np.asarray(list(binary), dtype=float)
    if len(x) != len(y) or len(x) < 2:
        return float("nan")
    if np.unique(y).size < 2:
        return float("nan")
    # Equivalent to Pearson(x, y) with y in {0,1}
    if np.std(x, ddof=1) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])

"""RQ1 trivial localization baselines and length confound diagnostics (V1.2)."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from src.metrics.localization import RankingTransform, ranking_score


def length_baseline_scores(payload_token_counts: Sequence[int]) -> list[float]:
    """B_LENGTH: higher score = more visible payload tokens."""
    return [float(t) for t in payload_token_counts]


def order_baseline_scores(ordered_positions: Sequence[int]) -> list[float]:
    """B_ORDER: earlier ordered_position ranks first via higher score = -position."""
    return [-float(p) for p in ordered_positions]


def audit_add_first_baseline(
    change_types: Sequence[str],
) -> dict[str, object]:
    """If all candidates are added lines, ADD_FIRST is DEGENERATE_NOT_APPLICABLE."""
    types = [str(c).upper() for c in change_types]
    if not types:
        return {
            "ADD_FIRST_BASELINE": "DEGENERATE_NOT_APPLICABLE",
            "reason": "empty_candidate_set",
            "n": 0,
            "n_added": 0,
        }
    n_added = sum(1 for t in types if t in {"ADD", "ADDED", "ADDED_CODE", "+"})
    if n_added == len(types):
        return {
            "ADD_FIRST_BASELINE": "DEGENERATE_NOT_APPLICABLE",
            "reason": "all_rq1_candidates_are_added_lines",
            "n": len(types),
            "n_added": n_added,
        }
    return {
        "ADD_FIRST_BASELINE": "APPLICABLE",
        "reason": "mixed_change_types",
        "n": len(types),
        "n_added": n_added,
        "ranking": "ADD_before_other_change_types",
    }


def add_first_scores(change_types: Sequence[str]) -> list[float] | None:
    audit = audit_add_first_baseline(change_types)
    if audit["ADD_FIRST_BASELINE"] == "DEGENERATE_NOT_APPLICABLE":
        return None
    scores: list[float] = []
    for t in change_types:
        tu = str(t).upper()
        scores.append(1.0 if tu in {"ADD", "ADDED", "ADDED_CODE", "+"} else 0.0)
    return scores


def abs_attr_vs_length_spearman(
    abs_attributions: Sequence[float],
    payload_token_counts: Sequence[int],
) -> float | None:
    """Commit-level Spearman between |attr| and payload token count."""
    if len(abs_attributions) != len(payload_token_counts):
        raise ValueError("length mismatch")
    n = len(abs_attributions)
    if n < 2:
        return None
    a = np.asarray([abs(float(x)) for x in abs_attributions], dtype=float)
    b = np.asarray([float(t) for t in payload_token_counts], dtype=float)
    if np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return None
    # Rank correlation via scipy if available; else numpy fallback
    try:
        from scipy.stats import spearmanr

        r, _ = spearmanr(a, b)
        if r is None or (isinstance(r, float) and np.isnan(r)):
            return None
        return float(r)
    except Exception:
        ra = a.argsort().argsort().astype(float)
        rb = b.argsort().argsort().astype(float)
        ra = (ra - ra.mean()) / (ra.std() or 1.0)
        rb = (rb - rb.mean()) / (rb.std() or 1.0)
        return float(np.mean(ra * rb))


def negative_hit_rate_at_k(
    ranked_region_ids_abs: Sequence[str],
    signed_scores: dict[str, float],
    positive_ids: set[str],
    *,
    k: int,
    eps: float = 0.0,
) -> dict[str, float | int]:
    """Among labelled-positive lines in absolute top-k, fraction with negative signed attr."""
    top = list(ranked_region_ids_abs[:k])
    pos_in_top = [rid for rid in top if rid in positive_ids]
    if not pos_in_top:
        return {
            "k": k,
            "n_positive_in_topk": 0,
            "n_negative_signed": 0,
            "NEGATIVE_HIT_RATE_AT_K": float("nan"),
        }
    n_neg = sum(1 for rid in pos_in_top if float(signed_scores.get(rid, 0.0)) < -float(eps))
    return {
        "k": k,
        "n_positive_in_topk": len(pos_in_top),
        "n_negative_signed": n_neg,
        "NEGATIVE_HIT_RATE_AT_K": float(n_neg) / float(len(pos_in_top)),
    }


def signed_vs_absolute_delta_recall20(
    recall_signed_positive: float,
    recall_abs: float,
) -> float:
    """SIGNED_VS_ABSOLUTE_DELTA_RECALL20 primary RQ3 endpoint."""
    return float(recall_signed_positive) - float(recall_abs)


def ensure_ranking_transform_known(name: str) -> RankingTransform:
    return RankingTransform(name)


def score_for_baseline(raw: float, transform: str) -> float:
    return ranking_score(raw, transform)

"""Deterministic cohorts for V1.2: negative matched diagnostic + rehearsal."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class CommitMeta:
    commit_id: str
    project: str
    visible_token_count: int
    split: str
    is_positive: bool


def _stable_key(*parts: object) -> str:
    payload = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def select_negative_matched_diagnostic(
    positives: Sequence[CommitMeta],
    clean_pool: Sequence[CommitMeta],
    *,
    n: int = 475,
) -> list[CommitMeta]:
    """NEGATIVE_MATCHED_DIAGNOSTIC_V1.

    One-to-one against positives using: same project preferred, nearest visible
    token count, commit_id ASC tie-break. Prediction-independent.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    pos = list(positives)[:n]
    pool = [c for c in clean_pool if (not c.is_positive and c.split.upper() == "TEST")]
    used: set[str] = set()
    selected: list[CommitMeta] = []
    for p in pos:
        candidates = [c for c in pool if c.commit_id not in used]
        if not candidates:
            break
        same = [c for c in candidates if c.project == p.project]
        cand = same if same else candidates

        def key(c: CommitMeta) -> tuple:
            return (abs(int(c.visible_token_count) - int(p.visible_token_count)), c.commit_id)

        best = sorted(cand, key=key)[0]
        used.add(best.commit_id)
        selected.append(best)
    return selected


def select_validation_rehearsal(
    val_positives: Sequence[CommitMeta],
    *,
    n: int = 64,
) -> list[CommitMeta]:
    """ATTRIBUTION_VALIDATION_REHEARSAL_N=64 with project + length-quartile coverage."""
    pool = [c for c in val_positives if c.is_positive and c.split.upper() in {"VAL", "VALID", "VALIDATION"}]
    if not pool:
        pool = [c for c in val_positives if c.is_positive]
    if not pool:
        return []
    # Quartiles by visible tokens
    ordered = sorted(pool, key=lambda c: (c.visible_token_count, c.commit_id))
    q = max(1, len(ordered) // 4)
    buckets: list[list[CommitMeta]] = [
        ordered[0:q],
        ordered[q : 2 * q],
        ordered[2 * q : 3 * q],
        ordered[3 * q :],
    ]
    # Round-robin across projects within buckets for coverage
    selected: list[CommitMeta] = []
    seen: set[str] = set()
    # Prefer unique projects first
    projects = sorted({c.project for c in ordered})
    for proj in projects:
        for b in buckets:
            for c in b:
                if c.project == proj and c.commit_id not in seen:
                    selected.append(c)
                    seen.add(c.commit_id)
                    break
            if len(selected) >= n:
                return selected[:n]
    for b in buckets:
        for c in sorted(b, key=lambda x: x.commit_id):
            if c.commit_id not in seen:
                selected.append(c)
                seen.add(c.commit_id)
            if len(selected) >= n:
                return selected[:n]
    return selected[:n]


def base_model_sanity_subset(
    rehearsal: Sequence[CommitMeta],
    *,
    n: int = 16,
) -> list[CommitMeta]:
    """Deterministic 16 of 64 validation rehearsal commits."""
    ordered = sorted(rehearsal, key=lambda c: (_stable_key("sanity", c.commit_id), c.commit_id))
    return list(ordered[:n])


def post_stratify_prediction(
    commits: Sequence[CommitMeta],
    *,
    y_true: Mapping[str, int],
    y_pred: Mapping[str, int],
) -> dict[str, list[str]]:
    """TP/FN/FP/TN after predictions locked. Does not select the cohort."""
    out = {"TP": [], "FN": [], "FP": [], "TN": []}
    for c in commits:
        yt = int(y_true[c.commit_id])
        yp = int(y_pred[c.commit_id])
        if yt == 1 and yp == 1:
            out["TP"].append(c.commit_id)
        elif yt == 1 and yp == 0:
            out["FN"].append(c.commit_id)
        elif yt == 0 and yp == 1:
            out["FP"].append(c.commit_id)
        else:
            out["TN"].append(c.commit_id)
    return out


def seed_rank_spearman(
    ranks_a: Sequence[float],
    ranks_b: Sequence[float],
) -> float | None:
    import numpy as np

    if len(ranks_a) != len(ranks_b) or len(ranks_a) < 2:
        return None
    a = np.asarray(ranks_a, dtype=float)
    b = np.asarray(ranks_b, dtype=float)
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

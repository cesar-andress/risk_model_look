"""Classification metrics for M1 pilot (validation only)."""

from __future__ import annotations

from typing import Any

import numpy as np


def _safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def _safe_ap(y_true: np.ndarray, y_score: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score

    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(average_precision_score(y_true, y_score))


def confusion_at_threshold(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5
) -> dict[str, int]:
    y_pred = (y_score >= threshold).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def metrics_at_threshold(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float = 0.5
) -> dict[str, Any]:
    cm = confusion_at_threshold(y_true, y_score, threshold)
    tp, tn, fp, fn = cm["tp"], cm["tn"], cm["fp"], cm["fn"]
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    sens = rec
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    bal_acc = 0.5 * (sens + spec)
    pos_rate = float((y_score >= threshold).mean())
    return {
        "threshold": float(threshold),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "balanced_accuracy": float(bal_acc),
        "positive_prediction_rate": float(pos_rate),
        "confusion_matrix": cm,
    }


def brier_score(y_true: np.ndarray, y_score: np.ndarray) -> float:
    return float(np.mean((y_score - y_true.astype(float)) ** 2))


def score_distribution(y_score: np.ndarray) -> dict[str, float]:
    qs = np.quantile(y_score, [0.01, 0.05, 0.50, 0.95, 0.99])
    return {
        "min": float(np.min(y_score)),
        "p01": float(qs[0]),
        "p05": float(qs[1]),
        "median": float(qs[2]),
        "p95": float(qs[3]),
        "p99": float(qs[4]),
        "max": float(np.max(y_score)),
    }


def class_score_stats(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, Any]:
    out = {}
    for c in (0, 1):
        s = y_score[y_true == c]
        if len(s) == 0:
            out[str(c)] = None
            continue
        out[str(c)] = {
            "n": int(len(s)),
            "mean": float(s.mean()),
            "median": float(np.median(s)),
            "std": float(s.std()),
            "min": float(s.min()),
            "max": float(s.max()),
        }
    return out


def best_f1_threshold(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, Any]:
    """Diagnostic-only: threshold maximizing F1 on the given split."""
    # Dense grid on unique scores + endpoints
    uniq = np.unique(y_score)
    candidates = np.unique(
        np.concatenate([[0.0, 1.0], uniq, (uniq[:-1] + uniq[1:]) / 2 if len(uniq) > 1 else uniq])
    )
    best = None
    for t in candidates:
        m = metrics_at_threshold(y_true, y_score, float(t))
        if best is None or m["f1"] > best["f1"]:
            best = m
    assert best is not None
    best["note"] = "PILOT_DIAGNOSTIC_ONLY"
    return best


def compute_classification_metrics(
    y_true: np.ndarray, y_score: np.ndarray, *, threshold: float = 0.5
) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    n = len(y_true)
    n_pos = int((y_true == 1).sum())
    prevalence = n_pos / n if n else 0.0
    at05 = metrics_at_threshold(y_true, y_score, threshold)
    hard_both = bool(
        ((y_score >= threshold).any()) and ((y_score < threshold).any())
    )
    return {
        "n": n,
        "positives": n_pos,
        "negatives": n - n_pos,
        "prevalence": float(prevalence),
        "pr_baseline_prevalence": float(prevalence),
        "roc_auc": _safe_auc(y_true, y_score),
        "pr_auc": _safe_ap(y_true, y_score),
        "brier": brier_score(y_true, y_score),
        "at_0_5": at05,
        "score_distribution": score_distribution(y_score),
        "score_by_true_class": class_score_stats(y_true, y_score),
        "both_hard_classes_at_0_5": hard_both,
        "threshold_diagnostic_max_f1": best_f1_threshold(y_true, y_score),
    }

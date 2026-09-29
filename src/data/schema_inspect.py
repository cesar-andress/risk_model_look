"""Schema summarization and split-integrity helpers (no dataset mutation)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Hashable, Iterable, Sequence
import hashlib
import math


def value_type_name(x: Any) -> str:
    return type(x).__name__


def profile_unique_values(values: Iterable[Any], *, max_report: int = 50) -> dict[str, Any]:
    """Profile raw unique values without coercion. Caps reported keys."""
    counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for v in values:
        type_counts[value_type_name(v)] += 1
        # Represent value safely for JSON keys
        if isinstance(v, (bool, int, float)) and not isinstance(v, bool):
            key = repr(v)
        elif isinstance(v, bool):
            key = repr(v)
        elif v is None:
            key = "None"
        elif isinstance(v, str) and len(v) <= 32:
            key = repr(v)
        else:
            key = f"<{value_type_name(v)}>"
        counts[key] += 1
    # Fix bool before int in isinstance — redo properly
    return _profile_unique_values_fixed(values, max_report=max_report)


def _profile_unique_values_fixed(values: Iterable[Any], *, max_report: int = 50) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for v in values:
        type_counts[type(v).__name__] += 1
        if v is None:
            key = "None"
        elif isinstance(v, bool):
            key = "True" if v else "False"
        elif isinstance(v, int):
            key = str(v)
        elif isinstance(v, float):
            key = repr(v)
        elif isinstance(v, str) and len(v) <= 32:
            key = repr(v)
        else:
            key = f"<{type(v).__name__}>"
        counts[key] += 1
    items = counts.most_common(max_report)
    return {
        "n": sum(counts.values()),
        "n_unique_keys_reported": len(items),
        "n_unique_total": len(counts),
        "type_counts": dict(type_counts),
        "value_counts": {k: v for k, v in items},
    }


def quantiles(xs: Sequence[float | int]) -> dict[str, float]:
    if not xs:
        return {
            "min": math.nan,
            "p25": math.nan,
            "median": math.nan,
            "mean": math.nan,
            "p75": math.nan,
            "p90": math.nan,
            "p95": math.nan,
            "p99": math.nan,
            "max": math.nan,
            "n": 0,
        }
    ys = sorted(float(x) for x in xs)

    def q(p: float) -> float:
        if len(ys) == 1:
            return ys[0]
        idx = p * (len(ys) - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return ys[lo]
        w = idx - lo
        return ys[lo] * (1 - w) + ys[hi] * w

    return {
        "min": ys[0],
        "p25": q(0.25),
        "median": q(0.5),
        "mean": sum(ys) / len(ys),
        "p75": q(0.75),
        "p90": q(0.90),
        "p95": q(0.95),
        "p99": q(0.99),
        "max": ys[-1],
        "n": len(ys),
    }


def content_hash(obj: Any) -> str:
    """Stable hash of exact repr/bytes of a structure without storing content."""
    if isinstance(obj, (bytes, bytearray)):
        raw = bytes(obj)
    else:
        raw = repr(obj).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(raw).hexdigest()


def intersection_counts(a: set[Hashable], b: set[Hashable]) -> dict[str, Any]:
    inter = a & b
    return {
        "count": len(inter),
        "example_ids_hashed": sorted(hashlib.sha256(str(x).encode()).hexdigest() for x in list(inter)[:5]),
    }


def duplicate_id_report(ids: Sequence[Hashable]) -> dict[str, Any]:
    c = Counter(ids)
    dups = {k: v for k, v in c.items() if v > 1}
    return {
        "n": len(ids),
        "n_unique": len(c),
        "n_null": sum(1 for x in ids if x is None or (isinstance(x, float) and math.isnan(x))),
        "n_duplicate_ids": len(dups),
        "n_extra_rows_from_duplicates": sum(v - 1 for v in dups.values()),
    }


def line_label_length_check(
    added_lengths: Sequence[int],
    label_lengths: Sequence[int],
) -> dict[str, Any]:
    n = min(len(added_lengths), len(label_lengths))
    matches = sum(1 for i in range(n) if added_lengths[i] == label_lengths[i])
    mismatches = n - matches
    return {
        "records_checked": n,
        "matches": matches,
        "mismatches": mismatches,
        "added_len_series_n": len(added_lengths),
        "label_len_series_n": len(label_lengths),
    }


def dataframe_schema_fingerprint(columns: Sequence[str], dtypes: Sequence[str], index_type: str) -> str:
    payload = "|".join(columns) + "||" + "|".join(dtypes) + "||" + index_type
    return hashlib.sha256(payload.encode()).hexdigest()


def compare_schema_fingerprints(a: str, b: str) -> str:
    if a == b:
        return "IDENTICAL_SCHEMA"
    return "SCHEMA_DRIFT"

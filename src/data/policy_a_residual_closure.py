"""Policy-A residual closure: transform ledger + positional forced mapping.

No fuzzy matching. No tokenization.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from src.data.git_diff_reconstruction import DiffLine, normalize_line, stable_line_id
from src.data.policy_a_canonical_bridge import punct_space


# --- Source-derived transforms (see docs/RESIDUAL_TRANSFORMS_LEDGER.md) ---

_PUNCT_RE = re.compile(r"([^\w\s])", flags=re.UNICODE)


def jitfine_preprocess_code_line(code: str, remove_python_common_tokens: bool = False) -> str:
    """Exact copy of JITFine/my_util.preprocess_code_line @ 584799f…"""
    code = (
        code.replace("(", " ")
        .replace(")", " ")
        .replace("{", " ")
        .replace("}", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace(".", " ")
        .replace(":", " ")
        .replace(";", " ")
        .replace(",", " ")
        .replace(" _ ", "_")
    )
    code = re.sub("``.*``", "<STR>", code)
    code = re.sub("'.*'", "<STR>", code)
    code = re.sub('".*"', "<STR>", code)
    code = re.sub(r"\d+", "<NUM>", code)
    code = " ".join(code.split())
    if remove_python_common_tokens:
        # Java dataset path uses remove_python_common_tokens=False in concat.
        return code.strip()
    return code.strip()


def punct_space_transform(text: str) -> str:
    """DIFF_NORMALIZATION / Layer-B raw spacing (empirically verified)."""
    return punct_space(text)


def underscore_as_separator(text: str) -> str:
    """Observed ESCAPE_PATTERN → ESCAPE PATTERN variant (LINE_LABEL_TRANSFORM)."""
    return punct_space(text.replace("_", " "))


def whitespace_collapse(text: str) -> str:
    return " ".join(text.split())


def approved_signatures(text: str) -> set[str]:
    """Exact equality signatures only — source-approved transforms."""
    out = {
        text,
        whitespace_collapse(text),
        punct_space_transform(text),
        underscore_as_separator(text),
        normalize_line(text),
        jitfine_preprocess_code_line(text),
        jitfine_preprocess_code_line(punct_space_transform(text)),
        jitfine_preprocess_code_line(whitespace_collapse(text)),
        punct_space_transform(normalize_line(text)),
    }
    return out


def signatures_match(a: str, b: str) -> bool:
    return bool(approved_signatures(a) & approved_signatures(b))


def match_via_changed_line(git_raw: str, changed_line: str) -> bool:
    """Match Git raw to Layer-B changed_line via preprocess (upstream path)."""
    return jitfine_preprocess_code_line(git_raw) == changed_line or (
        jitfine_preprocess_code_line(punct_space_transform(git_raw)) == changed_line
    )


@dataclass(frozen=True)
class Anchor:
    policy_ord: int  # 0-based ordinal in Policy-A added sequence for commit
    git_ord: int  # 0-based ordinal in canonical Git added sequence (file-local or commit)


def positionally_forced_bijections(
    *,
    n_policy: int,
    n_git: int,
    mapped: dict[int, int],
    unmatched_policy: set[int],
    unmatched_git: set[int],
) -> dict[int, int]:
    """Return policy_ord → git_ord for uniquely forced gaps between anchors.

    mapped: already trusted policy_ord → git_ord (exact).
    A gap between consecutive anchors (in policy order) maps iff the open
    interval of unmatched policy indices and unmatched git indices between the
    corresponding git anchors have equal cardinality and yield one monotonic
    bijection. Rejects if any alternative equal-length interval exists.
    """
    if n_policy == 0 or n_git == 0:
        return {}

    anchors = sorted((p, g) for p, g in mapped.items())
    forced: dict[int, int] = {}

    def gap_map(
        p_lo: int,
        p_hi: int,
        g_lo: int,
        g_hi: int,
    ) -> dict[int, int] | None:
        """Open interval (p_lo, p_hi) × (g_lo, g_hi)."""
        p_idx = sorted(
            i for i in range(p_lo + 1, p_hi) if i in unmatched_policy
        )
        g_idx = sorted(i for i in range(g_lo + 1, g_hi) if i in unmatched_git)
        if len(p_idx) == 0:
            return {}
        if len(p_idx) != len(g_idx):
            return None
        # Unique monotonic bijection by order
        return dict(zip(p_idx, g_idx))

    # Interior gaps between consecutive anchors
    for (p0, g0), (p1, g1) in zip(anchors, anchors[1:]):
        if g0 >= g1:
            continue  # non-monotonic anchors — skip
        # Check uniqueness: only this git interval between g0 and g1
        cand = gap_map(p0, p1, g0, g1)
        if cand is None:
            continue
        # Alternative intervals forbidden by construction (anchors fix bounds).
        # Extra guard: no other unmatched git outside (g0,g1) with same count
        # that could also host — not applicable with fixed anchors.
        forced.update(cand)

    # Leading edge: before first anchor
    if anchors:
        p_first, g_first = anchors[0]
        p_idx = sorted(i for i in range(0, p_first) if i in unmatched_policy)
        g_idx = sorted(i for i in range(0, g_first) if i in unmatched_git)
        if len(p_idx) > 0 and len(p_idx) == len(g_idx):
            # Ensure no alternative: only one leading interval exists
            forced.update(dict(zip(p_idx, g_idx)))
        # Trailing edge
        p_last, g_last = anchors[-1]
        p_idx = sorted(i for i in range(p_last + 1, n_policy) if i in unmatched_policy)
        g_idx = sorted(i for i in range(g_last + 1, n_git) if i in unmatched_git)
        if len(p_idx) > 0 and len(p_idx) == len(g_idx):
            forced.update(dict(zip(p_idx, g_idx)))
    else:
        # No anchors: whole-file equal cardinality only
        p_idx = sorted(unmatched_policy)
        g_idx = sorted(unmatched_git)
        if len(p_idx) == len(g_idx) and len(p_idx) > 0 and len(p_idx) == n_policy == n_git:
            forced.update(dict(zip(p_idx, g_idx)))

    return forced


def smd(mean_a: float, mean_b: float, sd_a: float, sd_b: float) -> float | None:
    """Standardized mean difference (pooled SD)."""
    import math

    pooled = math.sqrt((sd_a**2 + sd_b**2) / 2.0)
    if pooled == 0:
        return 0.0 if mean_a == mean_b else None
    return (mean_a - mean_b) / pooled


def describe_numeric(vals: list[float]) -> dict[str, float]:
    import statistics

    if not vals:
        return {"n": 0, "mean": 0.0, "median": 0.0, "iqr": 0.0, "sd": 0.0}
    xs = sorted(vals)
    n = len(xs)
    mean = sum(xs) / n
    median = statistics.median(xs)
    q1 = statistics.median(xs[: n // 2]) if n >= 2 else xs[0]
    q3 = statistics.median(xs[(n + 1) // 2 :]) if n >= 2 else xs[0]
    sd = statistics.pstdev(xs) if n >= 2 else 0.0
    return {
        "n": float(n),
        "mean": float(mean),
        "median": float(median),
        "iqr": float(q3 - q1),
        "sd": float(sd),
    }


def classify_dataset_conflict(
    *,
    in_diff_filtered: bool,
    in_diff_unfiltered: bool,
    in_child: bool,
    in_parent: bool,
) -> str:
    if in_diff_filtered or in_diff_unfiltered:
        return "PRESENT_IN_DIFF"
    if in_child and not in_parent:
        return "LINE_PRESENT_IN_CHILD_ONLY"
    if in_parent and not in_child:
        return "LINE_PRESENT_IN_PARENT_ONLY"
    if in_child and in_parent:
        return "LINE_PRESENT_BOTH_BLOBS_NOT_IN_DIFF"
    return "NO_RAW_GIT_TEXT_MATCH"

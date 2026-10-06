"""Frozen METHOD_SPECIFIC_MISSINGNESS_V1_1 validity masks.

IG_NONCONVERGED is excluded only from analyses requiring valid IG
(m1_methods_v1_2.yaml missingness.rules.IG_NONCONVERGED;
ATTRIBUTION_PROTOCOL_V1 §8). Stored per-job metrics on a nonconverged unit
must not enter confirmatory method comparisons.
"""

from __future__ import annotations

from typing import Any, Mapping


def attribution_job_is_valid(unit: Mapping[str, Any] | None, method: str) -> bool:
    """True iff this seed/method unit is a protocol-valid observation."""
    if not unit:
        return False
    code = unit.get("missingness_code") or "OTHER"
    if unit.get("status") != "DONE" or code != "OK":
        return False
    if method == "ig":
        igm = unit.get("ig") or {}
        if igm.get("IG_NONCONVERGED") or unit.get("status") == "NONCONVERGED":
            return False
        if code == "IG_NONCONVERGED":
            return False
    return True


def faith_aopc_is_valid(
    faith: Mapping[str, Any] | None,
    method: str,
    attribution_unit: Mapping[str, Any] | None,
) -> bool:
    """AOPC may be used only if faithfulness succeeded on a valid attribution."""
    if not faith:
        return False
    if faith.get("missingness_code") != "OK" or faith.get("aopc") is None:
        return False
    if not attribution_job_is_valid(attribution_unit, method):
        return False
    ranking = faith.get("ranking_from") or {}
    if ranking.get("attribution_status") == "NONCONVERGED":
        return False
    if ranking.get("attribution_missingness") == "IG_NONCONVERGED":
        return False
    return True

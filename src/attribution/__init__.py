"""Attribution interfaces and primitives (CPU-safe infrastructure).

Does not load large LLMs. Scientific results are out of scope for this package
until ATTRIBUTION_RESULTS_GATE.
"""

from src.attribution.base import AttributionResult, ScoreSpace, TargetDefinition
from src.attribution.targets import (
    M1_RISK_LOGIT_CONTRAST,
    p_buggy_from_logits,
    risk_logit_contrast,
    verify_logit_odds_identity,
)

__all__ = [
    "AttributionResult",
    "ScoreSpace",
    "TargetDefinition",
    "M1_RISK_LOGIT_CONTRAST",
    "p_buggy_from_logits",
    "risk_logit_contrast",
    "verify_logit_odds_identity",
]

"""Versioned attribution method registry (no performance claims)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.attribution.targets import M1_RISK_LOGIT_CONTRAST

REGISTRY_VERSION = "1"


@dataclass(frozen=True)
class MethodSpec:
    method_id: str
    signedness: str  # "signed" | "unsigned" | "configurable"
    requires_grad: bool
    requires_forward_passes: int  # nominal / per-example lower bound (0 if N/A)
    supports_line: bool
    supports_hunk: bool
    default_aggregation: str
    target: str
    notes: str = ""


def build_m1_method_registry() -> dict[str, MethodSpec]:
    target = M1_RISK_LOGIT_CONTRAST.name
    specs = [
        MethodSpec(
            method_id="attention_last",
            signedness="unsigned",
            requires_grad=False,
            requires_forward_passes=1,
            supports_line=True,
            supports_hunk=True,
            default_aggregation="SUM",
            target=target,
            notes="Last-layer attention; head agg protocol-configurable.",
        ),
        MethodSpec(
            method_id="attention_last4",
            signedness="unsigned",
            requires_grad=False,
            requires_forward_passes=1,
            supports_line=True,
            supports_hunk=True,
            default_aggregation="SUM",
            target=target,
            notes="Mean over final-4 layers; not declared scientifically best.",
        ),
        MethodSpec(
            method_id="gradient",
            signedness="signed",
            requires_grad=True,
            requires_forward_passes=1,
            supports_line=True,
            supports_hunk=True,
            default_aggregation="SUM",
            target=target,
        ),
        MethodSpec(
            method_id="grad_x_input",
            signedness="signed",
            requires_grad=True,
            requires_forward_passes=1,
            supports_line=True,
            supports_hunk=True,
            default_aggregation="SUM",
            target=target,
        ),
        MethodSpec(
            method_id="integrated_gradients",
            signedness="signed",
            requires_grad=True,
            requires_forward_passes=0,  # steps-dependent; see compute_plan
            supports_line=True,
            supports_hunk=True,
            default_aggregation="SUM",
            target=target,
            notes="Forward/backward count = IG steps; baseline protocol option.",
        ),
        MethodSpec(
            method_id="occlusion_line",
            signedness="signed",
            requires_grad=False,
            requires_forward_passes=0,  # 1 + n_regions; see compute_plan
            supports_line=True,
            supports_hunk=False,
            default_aggregation="N/A",
            target=target,
        ),
        MethodSpec(
            method_id="occlusion_hunk",
            signedness="signed",
            requires_grad=False,
            requires_forward_passes=0,
            supports_line=False,
            supports_hunk=True,
            default_aggregation="N/A",
            target=target,
        ),
    ]
    return {s.method_id: s for s in specs}


def registry_as_jsonable() -> dict[str, Any]:
    reg = build_m1_method_registry()
    return {
        "registry_version": REGISTRY_VERSION,
        "methods": {k: asdict(v) for k, v in reg.items()},
    }

"""Cost / pass-count estimator for attribution execution planning.

Does not change scientific protocol settings; estimates only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

from src.experiments.engine_constants import ATTRIBUTION_PROTOCOL_HASH


@dataclass(frozen=True)
class AttributionCostEstimate:
    n_commits: int
    n_seeds: int
    methods: tuple[str, ...]
    granularity: str
    mean_regions_per_commit: float
    ig_steps: int
    ig_retry_steps: int
    forward_passes: int
    backward_passes: int
    ig_step_evals: int
    occlusion_evals: int
    estimated_result_rows: int
    estimated_storage_bytes: int
    notes: str
    protocol_hash: str = ATTRIBUTION_PROTOCOL_HASH

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm_methods(methods: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({m.strip() for m in methods if m.strip()}))


def estimate_attribution_cost(
    *,
    n_commits: int,
    methods: Sequence[str],
    n_seeds: int = 1,
    mean_regions_per_commit: float = 20.0,
    granularity: str = "LINE",
    ig_steps: int = 50,
    ig_retry_steps: int = 100,
    ig_retry_fraction: float = 0.0,
    bytes_per_result_row: int = 256,
    bytes_per_raw_score_vector: int = 4096,
) -> AttributionCostEstimate:
    if min(n_commits, n_seeds, mean_regions_per_commit, ig_steps) < 0:
        raise ValueError("counts must be non-negative")
    methods_t = _norm_methods(methods)
    fwd = 0
    bwd = 0
    ig_evals = 0
    occ_evals = 0
    notes: list[str] = []

    units = n_commits * n_seeds
    regions = mean_regions_per_commit

    for m in methods_t:
        ml = m.lower()
        if "attention" in ml:
            fwd += units
            notes.append(f"{m}:1fwd/unit")
        elif "grad_x_input" in ml or "grad×input" in ml or ml in {"gxi", "gradxinput"}:
            fwd += units
            bwd += units
            notes.append(f"{m}:1fwd+1bwd/unit")
        elif ml in {"gradient", "vanilla_gradient", "vanilla_grad"}:
            fwd += units
            bwd += units
            notes.append(f"{m}:1fwd+1bwd/unit")
        elif "integrated" in ml or ml == "ig":
            # Primary path: ig_steps; optional expected retry mass
            primary = units * ig_steps
            retry = int(round(units * ig_retry_fraction * ig_retry_steps))
            ig_evals += primary + retry
            fwd += primary + retry
            bwd += primary + retry
            notes.append(
                f"{m}:{ig_steps} steps (+{ig_retry_fraction:.0%}@{ig_retry_steps} expected)"
            )
        elif "occlusion" in ml or "perturb" in ml:
            # 1 baseline + 1 per region (batched implementation still counts evals)
            per = 1.0 + regions
            occ_evals += int(round(units * per))
            fwd += int(round(units * per))
            notes.append(f"{m}:1+regions forwards ({granularity})")
        else:
            fwd += units
            notes.append(f"{m}:1fwd/unit(default)")

    result_rows = int(round(units * len(methods_t) * max(regions, 1.0)))
    storage = result_rows * bytes_per_result_row + units * len(methods_t) * bytes_per_raw_score_vector

    return AttributionCostEstimate(
        n_commits=n_commits,
        n_seeds=n_seeds,
        methods=methods_t,
        granularity=granularity,
        mean_regions_per_commit=mean_regions_per_commit,
        ig_steps=ig_steps,
        ig_retry_steps=ig_retry_steps,
        forward_passes=fwd,
        backward_passes=bwd,
        ig_step_evals=ig_evals,
        occlusion_evals=occ_evals,
        estimated_result_rows=result_rows,
        estimated_storage_bytes=storage,
        notes="; ".join(notes),
    )


def format_attribution_plan(est: AttributionCostEstimate, *, method_label: str | None = None) -> str:
    methods = ", ".join(est.methods) if est.methods else (method_label or "?")
    return "\n".join(
        [
            "ATTRIBUTION PLAN",
            "",
            f"Method: {methods}",
            f"Cohort commits: {est.n_commits}",
            f"Seeds: {est.n_seeds}",
            f"Granularity: {est.granularity}",
            f"Mean regions/commit: {est.mean_regions_per_commit}",
            "",
            "Estimated:",
            f"  forward passes: {est.forward_passes}",
            f"  backward passes: {est.backward_passes}",
            f"  IG step evals: {est.ig_step_evals}",
            f"  occlusion evals: {est.occlusion_evals}",
            f"  result rows: {est.estimated_result_rows}",
            f"  storage bytes: {est.estimated_storage_bytes}",
            "",
            f"Notes: {est.notes}",
            f"Protocol hash: {est.protocol_hash}",
        ]
    )

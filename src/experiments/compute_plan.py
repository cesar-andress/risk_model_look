"""Static compute-planning utility (no GPU execution).

Use before launching attribution jobs to avoid millions of 7B forwards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ComputeEstimate:
    n_commits: int
    n_candidate_regions_per_commit: float
    ig_steps: int
    occlusion_granularity: str
    forward_passes: int
    backward_passes: int
    notes: str


def estimate_attribution_compute(
    *,
    n_commits: int,
    n_candidate_regions_per_commit: float,
    ig_steps: int = 32,
    include_attention: bool = True,
    include_gradient: bool = True,
    include_grad_x_input: bool = True,
    include_ig: bool = True,
    include_occlusion: bool = True,
    occlusion_granularity: str = "LINE",
) -> ComputeEstimate:
    """Estimate forward/backward passes for planned M1 attribution methods.

    Assumptions (documented, approximate):
      - attention / gradient / Grad×Input: 1 forward (+1 backward for grad family)
        per commit
      - IG: ``ig_steps`` forwards with grad each (counted as forward+backward each)
      - occlusion: 1 full forward + 1 forward per region (mean regions × commits)
    """
    if n_commits < 0 or n_candidate_regions_per_commit < 0 or ig_steps < 0:
        raise ValueError("counts/steps must be non-negative")

    fwd = 0
    bwd = 0
    notes_parts: list[str] = []

    if include_attention:
        fwd += n_commits
        notes_parts.append("attention:1fwd/commit")
    if include_gradient:
        fwd += n_commits
        bwd += n_commits
        notes_parts.append("gradient:1fwd+1bwd/commit")
    if include_grad_x_input:
        # Often shares the gradient forward; count separately for upper bound.
        fwd += n_commits
        bwd += n_commits
        notes_parts.append("grad_x_input:1fwd+1bwd/commit(upper)")
    if include_ig:
        fwd += n_commits * ig_steps
        bwd += n_commits * ig_steps
        notes_parts.append(f"ig:{ig_steps}fwd+bwd/commit")
    if include_occlusion:
        regions = int(round(n_commits * n_candidate_regions_per_commit))
        fwd += n_commits + regions
        notes_parts.append(
            f"occlusion:1+regions forwards ({occlusion_granularity})"
        )

    return ComputeEstimate(
        n_commits=n_commits,
        n_candidate_regions_per_commit=n_candidate_regions_per_commit,
        ig_steps=ig_steps,
        occlusion_granularity=occlusion_granularity,
        forward_passes=fwd,
        backward_passes=bwd,
        notes="; ".join(notes_parts),
    )


def estimate_as_dict(**kwargs) -> dict:
    return asdict(estimate_attribution_compute(**kwargs))

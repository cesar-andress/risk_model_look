"""CPU tests for compute planner and cache key contracts."""

from __future__ import annotations

import pytest

from src.experiments.cache_keys import AttributionCacheKey, OcclusionCacheKey
from src.experiments.compute_plan import estimate_attribution_compute
from src.experiments.result_schema import SCHEMA_VERSION, schema_spec


pytestmark = pytest.mark.cpu


def test_compute_estimate_scales() -> None:
    est = estimate_attribution_compute(
        n_commits=10,
        n_candidate_regions_per_commit=5,
        ig_steps=4,
        include_attention=True,
        include_gradient=True,
        include_grad_x_input=False,
        include_ig=True,
        include_occlusion=True,
    )
    # attention 10 + grad 10 + ig 40 + occlusion 10+50 = 120 fwd
    assert est.forward_passes == 120
    assert est.backward_passes == 10 + 40


def test_cache_keys_not_commit_only() -> None:
    a = OcclusionCacheKey(
        model_checkpoint_hash="abc",
        dataset_version="canonical_v1",
        representation="CHANGED_ONLY",
        commit_id="c1",
        region_definition="LINE:L1",
        perturbation_policy="structured_remove",
        prompt_version="1",
    )
    b = OcclusionCacheKey(
        model_checkpoint_hash="DEF",
        dataset_version="canonical_v1",
        representation="CHANGED_ONLY",
        commit_id="c1",
        region_definition="LINE:L1",
        perturbation_policy="structured_remove",
        prompt_version="1",
    )
    assert a.digest() != b.digest()
    att = AttributionCacheKey(
        model_checkpoint_hash="abc",
        dataset_version="canonical_v1",
        representation="CHANGED_ONLY",
        commit_id="c1",
        method_id="grad_x_input",
        method_config_hash="cfg",
        target="risk_logit_contrast",
        prompt_version="1",
        tokenizer_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        family="gradient",
    )
    assert "c1" in att.digest() or len(att.digest()) == 64
    assert schema_spec()["schema_version"] == SCHEMA_VERSION

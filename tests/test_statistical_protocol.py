"""CPU synthetic tests for STATISTICAL_ANALYSIS_PROTOCOL_V1."""

from __future__ import annotations

import pytest

from src.stats.bootstrap import (
    BOOTSTRAP_REPEATS,
    assert_cluster_keeps_seeds_together,
    derive_bootstrap_seed,
    paired_commit_bootstrap_percentile,
)
from src.stats.effect_sizes import (
    cliffs_delta_unpaired,
    direction_of_better_performance,
    matched_pairs_rank_biserial,
    point_biserial_correlation,
    raw_difference_summary,
)
from src.stats.multiplicity import format_p, holm_adjust
from src.stats.paired import (
    MIN_COMMON_VALID_SEEDS,
    build_pairwise_commit_diffs,
    collapse_random_baseline_perms,
    commit_paired_difference,
    descriptive_seed_summary,
    one_sample_wilcoxon_against_zero,
    wilcoxon_signed_rank,
)
from src.stats.protocol_manifest import (
    STATISTICAL_PROTOCOL_HASH_V1,
    V1_CONFIG as STATS_V1_CONFIG,
    V1_1_CONFIG as STATS_V1_1_CONFIG,
    build_manifest,
    statistical_protocol_hash,
    validate_stats_config,
    verify_stats_v1_hash_intact,
    write_manifest,
    load_stats_config,
)
from src.stats.rq_analysis import analyze_pairwise_commit_methods, apply_family_holm


pytestmark = pytest.mark.cpu


def test_protocol_hash_determinism(tmp_path) -> None:
    assert verify_stats_v1_hash_intact()
    cfg_v1 = load_stats_config(STATS_V1_CONFIG)
    assert statistical_protocol_hash(cfg_v1) == STATISTICAL_PROTOCOL_HASH_V1
    cfg = load_stats_config(STATS_V1_1_CONFIG)
    assert validate_stats_config(cfg) == []
    h1 = statistical_protocol_hash(cfg)
    h2 = statistical_protocol_hash(cfg)
    assert h1 == h2
    m = build_manifest(cfg)
    assert m["parent_attribution_protocol"]["protocol_id"] == "ATTRIBUTION_PROTOCOL_V1_2"
    assert m["STATISTICAL_PROTOCOL_HASH_V1"] == STATISTICAL_PROTOCOL_HASH_V1
    write_manifest(tmp_path)


def test_three_seed_aggregation_and_min_common() -> None:
    assert MIN_COMMON_VALID_SEEDS == 2
    # commit with only 1 common seed → excluded
    d = commit_paired_difference(
        {13: 1.0, 42: None},
        {13: 0.5, 42: 0.2},
        commit_id="c0",
    )
    assert d is None
    d2 = commit_paired_difference(
        {13: 1.0, 42: 2.0, 73: 3.0},
        {13: 0.0, 42: 1.0, 73: 2.0},
        commit_id="c1",
    )
    assert d2 is not None
    assert d2.diff == pytest.approx(1.0)
    assert d2.n_common_seeds == 3


def test_no_pseudoreplication_n_equals_commits_not_seed_rows() -> None:
    """3 seeds × 10 commits must yield N=10 for inference, not N=30."""
    commits = [f"c{i}" for i in range(10)]
    per_a: dict[str, dict[int, float | None]] = {}
    per_b: dict[str, dict[int, float | None]] = {}
    for i, cid in enumerate(commits):
        # Strong within-seed separation that would look like N=30 if flattened
        per_a[cid] = {13: 10.0 + i, 42: 10.0 + i, 73: 10.0 + i}
        per_b[cid] = {13: 0.0 + i, 42: 0.0 + i, 73: 0.0 + i}
    inc = build_pairwise_commit_diffs(per_a, per_b)
    assert inc.n_included == 10
    assert len(inc.commit_diffs) == 10
    # Flattened row count would be 30 — production path must not use that N
    flattened_n = sum(len(common) for common in ([13, 42, 73] for _ in commits))
    assert flattened_n == 30
    assert inc.n_included != flattened_n
    w = wilcoxon_signed_rank([c.diff for c in inc.commit_diffs])
    assert w.n == 10


def test_wilcoxon_zeros_and_all_zero() -> None:
    w = wilcoxon_signed_rank([0.0, 0.0, 0.0, 0.0])
    assert w.status == "ALL_ZERO_DIFFERENCES"
    assert w.p_value == 1.0
    assert matched_pairs_rank_biserial([0.0, 0.0]) == 0.0
    w2 = wilcoxon_signed_rank([1.0, 0.0, -0.5, 2.0])
    assert w2.n_zero_diffs == 1
    assert w2.status == "OK"


def test_rank_biserial_orientation_and_lower_is_better() -> None:
    # A larger than B → positive rrb
    r = matched_pairs_rank_biserial([2.0, 1.0, 3.0])
    assert r > 0
    assert (
        direction_of_better_performance(
            metric_direction="HIGHER_BETTER", first_method_larger=True
        )
        == "FIRST_BETTER"
    )
    assert (
        direction_of_better_performance(
            metric_direction="LOWER_BETTER", first_method_larger=True
        )
        == "SECOND_BETTER"
    )
    s = raw_difference_summary([1.0, 2.0, 3.0, 4.0])
    assert s["median_paired_diff"] == pytest.approx(2.5)


def test_bootstrap_config_cluster_and_deterministic_seed() -> None:
    assert BOOTSTRAP_REPEATS == 10000
    h = statistical_protocol_hash()
    s1 = derive_bootstrap_seed(h, "RQ1", "Top-5", "A__B")
    s2 = derive_bootstrap_seed(h, "RQ1", "Top-5", "A__B")
    s3 = derive_bootstrap_seed(h, "RQ1", "Top-5", "A__C")
    assert s1 == s2
    assert s1 != s3
    commit_vals = {f"c{i}": float(i) for i in range(5)}
    # Use small repeats in unit test for speed but assert config default is 10000
    out = paired_commit_bootstrap_percentile(
        list(commit_vals),
        lambda ids: sum(commit_vals[c] for c in ids) / len(ids),
        rng_seed=s1,
        repeats=200,
    )
    assert out["n_commits"] == 5
    assert out["ci_low"] <= out["point"] <= out["ci_high"]
    rows = assert_cluster_keeps_seeds_together(
        {"c0": [(13, 1.0), (42, 2.0), (73, 3.0)], "c1": [(13, 0.0)]},
        ["c0", "c0", "c1"],
    )
    assert rows.count(("c0", 13, 1.0)) == 2
    assert len([r for r in rows if r[0] == "c0"]) == 6  # 2 draws × 3 seeds


def test_holm_family_separation() -> None:
    items = holm_adjust(
        [("a", 0.01), ("b", 0.04), ("c", 0.03)],
        family="RQ1_PRIMARY",
        role="PRIMARY",
    )
    by = {i.name: i.adjusted_p for i in items}
    assert by["a"] <= by["c"] <= by["b"] or by["a"] <= by["b"]
    assert format_p(0.0004) == "p < 0.001"
    with pytest.raises(ValueError):
        holm_adjust([("x", 0.1)], family="SENSITIVITY", role="PRIMARY")


def test_random_baseline_collapse_not_pseudoreplicated() -> None:
    perms = {"c1": [0.1] * 100, "c2": [0.5] * 50 + [0.7] * 50}
    collapsed = collapse_random_baseline_perms(perms)
    assert collapsed["c1"] == pytest.approx(0.1)
    assert len(collapsed) == 2  # commit-level, not 150 rows


def test_missingness_intersection_and_low_n() -> None:
    per_a = {
        "c0": {13: 1.0, 42: 1.0},
        "c1": {13: 1.0},  # only 1 common
        "c2": {13: 2.0, 42: 2.0, 73: 2.0},
    }
    per_b = {
        "c0": {13: 0.0, 42: 0.0},
        "c1": {13: 0.0, 42: None},
        "c2": {13: 1.0, 42: 1.0, 73: 1.0},
    }
    inc = build_pairwise_commit_diffs(per_a, per_b)
    assert inc.n_total_candidate == 3
    assert inc.n_included == 2
    assert inc.n_excluded_missingness == 1
    # N=2 < 30
    assert inc.low_power_exploratory is True


def test_point_biserial_and_polarity_swap_wilcoxon() -> None:
    r = point_biserial_correlation([1.0, 2.0, 3.0, 4.0], [0, 0, 1, 1])
    assert r > 0
    w = one_sample_wilcoxon_against_zero([0.5, 0.2, 0.1, 0.3, 0.4])
    assert w.status == "OK"
    assert w.p_value < 1.0


def test_cliffs_delta_is_secondary_available() -> None:
    d = cliffs_delta_unpaired([3, 4, 5], [1, 2, 2])
    assert d > 0


def test_end_to_end_pairwise_report_and_holm() -> None:
    commits = [f"c{i}" for i in range(40)]
    per_a = {c: {13: 1.0, 42: 1.0, 73: 1.0} for c in commits}
    per_b = {c: {13: 0.0, 42: 0.0, 73: 0.0} for c in commits}
    rep = analyze_pairwise_commit_methods(
        method_a="A",
        method_b="B",
        metric="Top-5",
        metric_direction="HIGHER_BETTER",
        per_commit_a=per_a,
        per_commit_b=per_b,
        family="RQ1_PRIMARY",
    )
    assert rep.n_included == 40
    assert rep.low_power_exploratory is False
    assert rep.rank_biserial > 0
    adjusted = apply_family_holm([rep], family="RQ1_PRIMARY")
    assert adjusted[0][1] <= 1.0


def test_descriptive_seed_summary() -> None:
    s = descriptive_seed_summary({13: 1.0, 42: 3.0, 73: 5.0})
    assert s["mean"] == pytest.approx(3.0)
    assert s["n_seeds"] == 3

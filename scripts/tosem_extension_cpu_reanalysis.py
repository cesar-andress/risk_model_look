#!/usr/bin/env python3
"""CPU reanalysis for TOSEM extension gate 1. Reads existing TEST jobs only."""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from src.experiments.engine_constants import STATISTICAL_PROTOCOL_HASH
from src.experiments.missingness_validity import attribution_job_is_valid, faith_aopc_is_valid
from src.experiments.rehearsal_pipeline import iter_lines
from src.experiments.test_io import load_test_records
from src.metrics.localization import RANDOM_BASELINE_REPEATS, RankingTransform, compute_rq1_localization_metrics
from src.metrics.polarity import relative_polarity_epsilon
from src.metrics.rq1_baselines import length_baseline_scores, negative_hit_rate_at_k, order_baseline_scores
from src.stats.bootstrap import derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.effect_sizes import matched_pairs_rank_biserial
from src.stats.paired import build_pairwise_commit_diffs, wilcoxon_signed_rank
from src.stats.rq_analysis import analyze_pairwise_commit_methods

OUT = ROOT / "artifacts" / "tosem_extension"
ATTR = ROOT / "artifacts" / "test_attribution"
SEEDS = (13, 42, 73)
STAT = STATISTICAL_PROTOCOL_HASH
PARENT_FREEZE = "a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19"
LOCK_COMMIT = "840bb45eda317908d7f953e67f27dafbad1c5cf6"
LOCK_SHA = "855415e785b41d3a6a233b33fb624da76cc35f48f7beedbe13b16498aca31540"


def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def unit(pop, seed, method, cid, ml=2048):
    return ATTR / "raw" / pop / f"seed_{seed}" / method / f"ml{ml}_{cid}.json"


def faith(seed, method, cid):
    return ATTR / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / method / f"{cid}.json"


def perm_seed(cid: str, rep: int) -> int:
    h = hashlib.sha256(f"{STAT}|B_RANDOM|{cid}|{rep}".encode()).hexdigest()
    return int(h[:8], 16)


def contrast_pack(per_a, per_b, *, metric, family, role, rq, comparison_id):
    report = analyze_pairwise_commit_methods(
        method_a="A",
        method_b="B",
        metric=metric,
        metric_direction="HIGHER_BETTER",
        per_commit_a=per_a,
        per_commit_b=per_b,
        family=family,
        role=role,
    )
    inc = build_pairwise_commit_diffs(per_a, per_b)
    diffs = {c.commit_id: c.diff for c in inc.commit_diffs}
    seed = derive_bootstrap_seed(STAT, rq, metric, comparison_id)
    boot = paired_commit_bootstrap_percentile(
        list(diffs),
        lambda ids: float(np.mean([diffs[i] for i in ids])),
        rng_seed=seed,
    )
    return {
        "n_included": report.n_included,
        "n_excluded": report.n_excluded,
        "low_power_exploratory": report.low_power_exploratory,
        "p_raw": report.p_raw,
        "rank_biserial": report.rank_biserial,
        "mean_diff": report.raw_summary.get("mean") if isinstance(report.raw_summary, dict) else None,
        "bootstrap": boot,
        "role": role,
        "family": family,
        "wilcoxon_status": report.wilcoxon_status,
    }


def mean_ge2(by_cid_seed: dict, cids) -> tuple[float | None, int]:
    vals = []
    for cid in cids:
        xs = [by_cid_seed.get(cid, {}).get(s) for s in SEEDS]
        xs = [x for x in xs if x is not None]
        if len(xs) >= 2:
            vals.append(sum(xs) / len(xs))
    if not vals:
        return None, 0
    return float(sum(vals) / len(vals)), len(vals)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cohorts = loadj(ATTR / "cohorts" / "COHORT_INTEGRITY.json")
    pos = cohorts["positive_475"]["commit_ids"]
    rq1 = set(cohorts["rq1_primary_304"]["commit_ids"])
    rq1_l = cohorts["rq1_primary_304"]["commit_ids"]
    vis4096 = cohorts["rq1_4096_345"]["commit_ids"]
    recs = load_test_records(
        scientific_test_gate=True,
        processed_dir=ROOT / "data" / "processed" / "canonical_v1",
    )
    index = {r["commit_id"]: r for r in recs}
    project_of = {r["commit_id"]: r.get("project") or r.get("repo") or "UNKNOWN" for r in recs}

    from transformers import AutoTokenizer
    from src.models.qwen_m1 import QWEN_MODEL_ID, QWEN_REVISION
    from src.experiments.test_io import encode_test_with_map

    tok = AutoTokenizer.from_pretrained(QWEN_MODEL_ID, revision=QWEN_REVISION, local_files_only=True)

    recall = defaultdict(lambda: defaultdict(dict))
    aopc = defaultdict(lambda: defaultdict(dict))
    enrich = defaultdict(lambda: defaultdict(list))  # cat -> list of commit-mean
    neghit5 = defaultdict(lambda: defaultdict(dict))
    neghit10 = defaultdict(lambda: defaultdict(dict))
    rec4096 = defaultdict(lambda: defaultdict(dict))
    clean_n = defaultdict(int)

    rq2_stats = loadj(ATTR / "statistics" / "rq2_stats.json")
    rq1_stats = loadj(ATTR / "statistics" / "rq1_stats.json")
    stab = loadj(ATTR / "metrics" / "stability" / "seed_stability.json")

    # --- existing AOPC / recall / enrichment / 4096 / clean ---
    for seed in SEEDS:
        for method in ("attention", "grad_x_input", "occlusion", "gradient", "attention_last4"):
            for cid in pos:
                u = loadj(unit("positive_475", seed, method, cid))
                if not u:
                    continue
                if attribution_job_is_valid(u, method):
                    rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                    if rec20 is not None:
                        recall[method][cid][seed] = float(rec20)
                    table = u.get("rq4_enrichment") or {}
                    if cid in rq1:
                        for cat, row in table.items():
                            en = row.get("ATTRIBUTION_ENRICHMENT_C") if isinstance(row, dict) else None
                            if en is not None:
                                enrich[(method, cat)][cid].append(float(en))
                    scores = {k: float(v) for k, v in (u.get("line_scores_sum") or {}).items()}
                    rec = index.get(cid)
                    if rec and cid in rq1 and scores:
                        drop = set(u.get("dropped_line_ids") or [])
                        pos_ids = set()
                        items = []
                        for _f, _h, ln in iter_lines(rec):
                            sid = ln.get("stable_line_id")
                            if not sid or sid in drop or sid not in scores:
                                continue
                            st = ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE"
                            if st == "NOT_IN_RQ1_UNIVERSE":
                                continue
                            items.append(sid)
                            if st == "RQ1_POSITIVE":
                                pos_ids.add(sid)
                        ranked_abs = sorted(items, key=lambda s: (-abs(scores[s]), s))
                        eps = relative_polarity_epsilon(scores)
                        h5 = negative_hit_rate_at_k(ranked_abs, scores, pos_ids, k=5, eps=eps)
                        h10 = negative_hit_rate_at_k(ranked_abs, scores, pos_ids, k=10, eps=eps)
                        if h5["n_positive_in_topk"]:
                            neghit5[method][cid][seed] = float(h5["NEGATIVE_HIT_RATE_AT_K"])
                        if h10["n_positive_in_topk"]:
                            neghit10[method][cid][seed] = float(h10["NEGATIVE_HIT_RATE_AT_K"])
                f = loadj(faith(seed, method, cid))
                if faith_aopc_is_valid(f, method, u):
                    aopc[method][cid][seed] = float(f["aopc"])
        for method in ("attention", "grad_x_input"):
            for cid in vis4096:
                u = loadj(unit("rq1_4096", seed, method, cid, ml=4096))
                if u and attribution_job_is_valid(u, method):
                    rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                    if rec20 is not None:
                        rec4096[method][cid][seed] = float(rec20)
        for method in ("attention", "grad_x_input", "occlusion"):
            d = ATTR / "raw" / "matched_clean" / f"seed_{seed}" / method
            if d.is_dir():
                clean_n[f"{method}_{seed}"] = sum(1 for p in d.glob("*.json") if loadj(p) and loadj(p).get("status") == "DONE")

    # token maps for baselines (CPU tokenizer)
    base_len = defaultdict(dict)  # cid -> recall (deterministic, seed-free)
    base_ord = defaultdict(dict)
    base_rnd = defaultdict(dict)

    for i, cid in enumerate(rq1_l):
        rec = index[cid]
        packed = encode_test_with_map(tok, rec, max_length=2048)
        dropped = set((packed.get("truncation") or {}).get("dropped_line_ids") or [])
        counts = defaultdict(int)
        for row in packed.get("token_map") or []:
            sid = row.get("stable_line_id")
            if sid and row.get("payload"):
                counts[sid] += 1
        ids, statuses, orders, lens = [], [], [], []
        for _f, _h, ln in iter_lines(rec):
            sid = ln.get("stable_line_id")
            if not sid or sid in dropped:
                continue
            st = ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE"
            if st == "NOT_IN_RQ1_UNIVERSE":
                continue
            ids.append(sid)
            statuses.append(st)
            orders.append(int(ln.get("ordered_position") or 0))
            lens.append(int(counts.get(sid, 0)))
        if not ids:
            continue
        m_len = compute_rq1_localization_metrics(
            ids, length_baseline_scores(lens), statuses, transform=RankingTransform.RAW_DESCENDING, ordered_positions=orders
        )
        m_ord = compute_rq1_localization_metrics(
            ids, order_baseline_scores(orders), statuses, transform=RankingTransform.RAW_DESCENDING, ordered_positions=orders
        )
        base_len[cid] = float(m_len["recall_at_20pct_effort"])
        base_ord[cid] = float(m_ord["recall_at_20pct_effort"])
        rnds = []
        n = len(ids)
        for rep in range(RANDOM_BASELINE_REPEATS):
            rng = np.random.default_rng(perm_seed(cid, rep))
            perm = rng.permutation(n)
            scores = [0.0] * n
            for rank, idx in enumerate(perm):
                scores[int(idx)] = float(n - rank)
            m = compute_rq1_localization_metrics(
                ids, scores, statuses, transform=RankingTransform.RAW_DESCENDING, ordered_positions=orders
            )
            rnds.append(float(m["recall_at_20pct_effort"]))
        base_rnd[cid] = float(np.mean(rnds))
        if (i + 1) % 50 == 0:
            print(f"baselines {i+1}/{len(rq1_l)}", flush=True)

    def as_per_commit_const(d):
        return {cid: {s: float(d[cid]) for s in SEEDS} for cid in d}

    per_len = as_per_commit_const(base_len)
    per_ord = as_per_commit_const(base_ord)
    per_rnd = as_per_commit_const(base_rnd)

    def method_per(method):
        return {cid: recall[method].get(cid, {}) for cid in rq1_l}

    rq1_vs_base = {}
    for method in ("attention", "grad_x_input", "occlusion"):
        for bname, per_b in (("B_LENGTH", per_len), ("B_ORDER", per_ord), ("B_RANDOM", per_rnd)):
            rq1_vs_base[f"{method}_vs_{bname}"] = contrast_pack(
                method_per(method),
                per_b,
                metric="recall_at_20pct_effort",
                family="SENSITIVITY",
                role="BASELINE",
                rq="RQ1",
                comparison_id=f"{method}__{bname}",
            )

    # RQ2 on 304
    per_att_aopc = {cid: aopc["attention"].get(cid, {}) for cid in rq1_l}
    per_gxi_aopc = {cid: aopc["grad_x_input"].get(cid, {}) for cid in rq1_l}
    rq2_on_304 = contrast_pack(
        per_att_aopc,
        per_gxi_aopc,
        metric="ABS_DELETION_AOPC",
        family="SENSITIVITY",
        role="SECONDARY_REQUIRED",
        rq="RQ2_ON_RQ1_SUBSET",
        comparison_id="attention__grad_x_input_ABS_DELETION_AOPC_rq1subset",
    )

    # 4096
    def method_mean_4096(m):
        return mean_ge2(rec4096[m], vis4096)

    att4096, n_att4096 = method_mean_4096("attention")
    gxi4096, n_gxi4096 = method_mean_4096("grad_x_input")
    per_att_4096 = {cid: rec4096["attention"].get(cid, {}) for cid in vis4096}
    per_gxi_4096 = {cid: rec4096["grad_x_input"].get(cid, {}) for cid in vis4096}
    rq1_4096_contrast = contrast_pack(
        per_att_4096,
        per_gxi_4096,
        metric="recall_at_20pct_effort",
        family="SENSITIVITY",
        role="SENSITIVITY",
        rq="RQ1_4096",
        comparison_id="attention__grad_x_input_4096",
    )

    # enrichment means (attention, RQ1 commits)
    enrich_out = {}
    for (method, cat), bycid in enrich.items():
        if method != "attention":
            continue
        vals = [float(np.mean(v)) for v in bycid.values() if v]
        enrich_out[cat] = {"n": len(vals), "mean": float(np.mean(vals)) if vals else None}

    def hit_summary(store, method):
        m, n = mean_ge2(store[method], rq1_l)
        return {"mean": m, "n": n}

    # project-clustered bootstrap of existing RQ2 diffs
    inc = build_pairwise_commit_diffs(
        {cid: aopc["attention"].get(cid, {}) for cid in pos},
        {cid: aopc["grad_x_input"].get(cid, {}) for cid in pos},
    )
    diff_map = {c.commit_id: c.diff for c in inc.commit_diffs}
    proj_groups = defaultdict(list)
    for cid in diff_map:
        proj_groups[str(project_of.get(cid, "UNKNOWN"))].append(cid)
    projects = list(proj_groups)
    rng = np.random.default_rng(derive_bootstrap_seed(STAT, "RQ2", "ABS_DELETION_AOPC", "project_clustered"))
    samples = []
    n_p = len(projects)
    for _ in range(10000):
        draw_p = rng.choice(projects, size=n_p, replace=True)
        ids = []
        for p in draw_p:
            ids.extend(proj_groups[p])
        if not ids:
            continue
        samples.append(float(np.mean([diff_map[i] for i in ids])))
    samples = np.asarray(samples)
    clustered = {
        "n_commits": len(diff_map),
        "n_projects": n_p,
        "point": float(np.mean(list(diff_map.values()))),
        "ci_low": float(np.percentile(samples, 2.5)),
        "ci_high": float(np.percentile(samples, 97.5)),
        "role": "PROJECT-CLUSTERED SENSITIVITY",
        "replaces_primary": False,
    }

    planned_rb = {
        "rq1_att_gxi": rq1_stats["contrasts"][0]["rank_biserial"],
        "rq1_att_ig": rq1_stats["contrasts"][1]["rank_biserial"],
        "rq1_att_occ": rq1_stats["contrasts"][2]["rank_biserial"],
        "rq2_att_gxi": rq2_stats["contrasts"][0]["rank_biserial"],
        "rq2_att_ig": rq2_stats["contrasts"][1]["rank_biserial"],
    }

    ig_small = {
        "role": "EXPLORATORY SMALL-N DIAGNOSTIC",
        "n_rq1": 2,
        "n_rq2": 3,
        "note": "Exact Wilcoxon on N=2/3 is essentially uninformative for confirmatory inference; frozen Holm provenance is retained and not replaced.",
    }

    payload = {
        "SPLIT": "TEST",
        "SCIENTIFIC_RESULT": True,
        "NOT_VALIDATION_REHEARSAL": True,
        "parent_freeze_sha256": PARENT_FREEZE,
        "lock_commit": LOCK_COMMIT,
        "lock_sha256": LOCK_SHA,
        "created": datetime.now(timezone.utc).isoformat(),
        "rq1_baselines": {
            "N": 304,
            "B_LENGTH_mean_recall20": float(np.mean(list(base_len.values()))) if base_len else None,
            "B_ORDER_mean_recall20": float(np.mean(list(base_ord.values()))) if base_ord else None,
            "B_RANDOM_mean_recall20": float(np.mean(list(base_rnd.values()))) if base_rnd else None,
            "n_commits_scored": len(base_len),
            "contrasts_vs_methods": rq1_vs_base,
        },
        "rq2_on_rq1_304": rq2_on_304,
        "rq1_4096": {
            "attention_mean_recall20": att4096,
            "grad_x_input_mean_recall20": gxi4096,
            "n_attention": n_att4096,
            "n_gxi": n_gxi4096,
            "contrast": rq1_4096_contrast,
        },
        "enrichment_attention_rq1": enrich_out,
        "negative_hit_rate": {
            m: {"at5": hit_summary(neghit5, m), "at10": hit_summary(neghit10, m)}
            for m in ("grad_x_input", "occlusion", "gradient")
        },
        "matched_clean_done_counts": dict(clean_n),
        "matched_clean_note": "Cheap attribution only; no gold RQ1 labels on clean commits; matching rule unchanged.",
        "rank_biserial_planned": planned_rb,
        "project_clustered_rq2_att_gxi": clustered,
        "seed_stability_non_ig": {k: stab["pairs_by_method"][k] for k in ("attention", "grad_x_input", "occlusion")},
        "ig_small_n": ig_small,
        "rq3_family_audit": "MANUSCRIPT_WORDING_ERROR",
        "original_rq2_att_gxi": rq2_stats["contrasts"][0],
    }
    (OUT / "cpu_reanalysis.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print("wrote", OUT / "cpu_reanalysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

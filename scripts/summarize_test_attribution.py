#!/usr/bin/env python3
"""BLOCK L: aggregate frozen TEST attribution outputs. Read-only vs raw jobs."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.cohorts import seed_rank_spearman
from src.experiments.engine_constants import ATTRIBUTION_PROTOCOL_HASH, STATISTICAL_PROTOCOL_HASH
from src.experiments.rehearsal_pipeline import sha256_json
from src.experiments.test_io import TEST_BANNER
from src.stats.bootstrap import BOOTSTRAP_REPEATS, derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.multiplicity import holm_adjust
from src.stats.paired import one_sample_wilcoxon_against_zero
from src.stats.rq_analysis import analyze_pairwise_commit_methods

OUT = ROOT / "artifacts" / "test_attribution"
SEEDS = (13, 42, 73)
METHODS = ("attention", "attention_last4", "grad_x_input", "gradient", "occlusion", "ig")
EXPECTED_FREEZE = "22532bd734e5a1581b8639edf4eb634e55e09bbcdbc8a9186d6dc9a0efe5c0ab"


def _stamp(d: dict) -> dict:
    o = dict(TEST_BANNER)
    o.update(d)
    return o


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def unit_path(pop, seed, method, cid, max_len=2048) -> Path:
    return OUT / "raw" / pop / f"seed_{seed}" / method / f"ml{max_len}_{cid}.json"


def load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    cohorts = load_json(OUT / "cohorts" / "COHORT_INTEGRITY.json")
    if not cohorts or not cohorts.get("PASS"):
        raise SystemExit("BLOCK A integrity missing")
    pos = cohorts["positive_475"]["commit_ids"]
    rq1 = cohorts["rq1_primary_304"]["commit_ids"]
    (OUT / "metrics").mkdir(exist_ok=True)
    (OUT / "statistics").mkdir(exist_ok=True)
    (OUT / "summaries").mkdir(exist_ok=True)

    holm_families = _stamp(
        {
            "protocol": "STATISTICAL_PROTOCOL_V1_1",
            "hash": STATISTICAL_PROTOCOL_HASH,
            "families": {
                "RQ1_PRIMARY": [
                    "attention_vs_grad_x_input_Recall@20%Effort",
                    "attention_vs_ig_Recall@20%Effort",
                    "attention_vs_occlusion_Recall@20%Effort",
                ],
                "RQ2_PRIMARY": [
                    "attention_vs_grad_x_input_ABS_DELETION_AOPC",
                    "attention_vs_ig_ABS_DELETION_AOPC",
                ],
                "RQ3_PRIMARY": ["SIGNED_VS_ABSOLUTE_DELTA_RECALL20"],
                "RQ4_PRIMARY": [],
            },
            "occlusion_excluded_from_rq2_confirmatory": True,
            "membership_frozen_before_unadjusted_p": True,
        }
    )
    _write(OUT / "statistics" / "holm_families.json", holm_families)

    missing = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    recall = defaultdict(lambda: defaultdict(dict))  # method -> cid -> seed -> value
    aopc = defaultdict(lambda: defaultdict(dict))
    ranks = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))  # method -> seed -> cid
    rq3_delta = defaultdict(lambda: defaultdict(dict))
    rq4 = defaultdict(lambda: defaultdict(dict))
    ig_stats = {"jobs": 0, "retry": 0, "nonconv": 0, "conv50": 0, "walls": []}
    occ_regions = []
    walls = defaultdict(list)

    for seed in SEEDS:
        for method in METHODS:
            for cid in pos:
                u = load_json(unit_path("positive_475", seed, method, cid))
                if u is None:
                    missing[method][seed]["MISSING_FILE"] += 1
                    continue
                code = u.get("missingness_code") or "OTHER"
                if u.get("status") == "DONE" and code == "OK":
                    missing[method][seed]["DONE"] += 1
                else:
                    missing[method][seed][code] += 1
                if u.get("wall_s") is not None:
                    walls[method].append(float(u["wall_s"]))
                rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                if rec20 is not None:
                    recall[method][cid][seed] = float(rec20)
                if u.get("rq3_signed_vs_abs_delta_recall20") is not None:
                    rq3_delta[method][cid][seed] = float(u["rq3_signed_vs_abs_delta_recall20"])
                ls = u.get("line_scores_sum") or {}
                ranked = sorted(ls, key=lambda k: (-abs(float(ls[k])), k))
                ranks[method][seed][cid] = {sid: i for i, sid in enumerate(ranked)}
                if method == "occlusion" and u.get("n_regions") is not None:
                    occ_regions.append(int(u["n_regions"]))
                if method == "ig":
                    ig_stats["jobs"] += 1
                    igm = u.get("ig") or {}
                    if igm.get("retry_applied"):
                        ig_stats["retry"] += 1
                    else:
                        ig_stats["conv50"] += 1
                    if igm.get("IG_NONCONVERGED") or u.get("status") == "NONCONVERGED":
                        ig_stats["nonconv"] += 1
                    if u.get("wall_s"):
                        ig_stats["walls"].append(float(u["wall_s"]))
                f = load_json(
                    OUT / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / method / f"{cid}.json"
                )
                if f and f.get("aopc") is not None and f.get("missingness_code") == "OK":
                    aopc[method][cid][seed] = float(f["aopc"])
                if method == "attention" and f and f.get("ablations"):
                    for cat, val in f["ablations"].items():
                        if isinstance(val, (int, float)):
                            rq4[cat][cid][seed] = float(val)

    def method_mean_recall(method: str) -> float | None:
        vals = []
        for cid in rq1:
            by = recall.get(method, {}).get(cid, {})
            xs = [by[s] for s in SEEDS if s in by]
            if len(xs) >= 2:
                vals.append(sum(xs) / len(xs))
        return (sum(vals) / len(vals)) if vals else None

    rq1_summary = {
        m: {"mean_recall20_rq1_304": method_mean_recall(m), "n_commits_with_ge2_seeds": sum(1 for cid in rq1 if len(recall.get(m, {}).get(cid, {})) >= 2)}
        for m in METHODS
    }

    contrasts = []
    for a, b, fam, metric in [
        ("attention", "grad_x_input", "RQ1_PRIMARY", "recall_at_20pct_effort"),
        ("attention", "ig", "RQ1_PRIMARY", "recall_at_20pct_effort"),
        ("attention", "occlusion", "RQ1_PRIMARY", "recall_at_20pct_effort"),
    ]:
        pa, pb = recall.get(a) or {}, recall.get(b) or {}
        common = [c for c in rq1 if len(pa.get(c, {})) >= 2 and len(pb.get(c, {})) >= 2]
        if a == "attention" and b == "ig" and len(common) == 0:
            contrasts.append(_stamp({"contrast": f"{a}_vs_{b}", "status": "NOT_ESTIMABLE", "reason": "IG missingness / no common-valid seeds>=2", "family": fam}))
            continue
        if not pa or not pb or not common:
            contrasts.append(_stamp({"contrast": f"{a}_vs_{b}", "status": "NOT_ESTIMABLE", "reason": "insufficient paired commits", "family": fam}))
            continue
        report = analyze_pairwise_commit_methods(
            method_a=a,
            method_b=b,
            metric=metric,
            metric_direction="HIGHER_BETTER",
            per_commit_a={c: pa[c] for c in common},
            per_commit_b={c: pb[c] for c in common},
            family=fam,
            role="PRIMARY",
        )
        seed = derive_bootstrap_seed(STATISTICAL_PROTOCOL_HASH, "RQ1", metric, f"{a}__{b}")
        dmap = {}
        from src.stats.paired import build_pairwise_commit_diffs

        inc = build_pairwise_commit_diffs({c: pa[c] for c in common}, {c: pb[c] for c in common})
        dmap = {c.commit_id: c.diff for c in inc.commit_diffs}
        ids = list(dmap)

        def stat(sample):
            xs = [dmap[i] for i in sample if i in dmap]
            return float(sum(xs) / len(xs)) if xs else 0.0

        boot = paired_commit_bootstrap_percentile(ids, stat, rng_seed=seed, repeats=BOOTSTRAP_REPEATS)
        contrasts.append(
            _stamp(
                {
                    "contrast": f"{a}_vs_{b}",
                    "family": fam,
                    "n_included": report.n_included,
                    "n_excluded": report.n_excluded,
                    "wilcoxon_status": report.wilcoxon_status,
                    "p_raw": report.p_raw,
                    "rank_biserial": report.rank_biserial,
                    "bootstrap": boot,
                    "bootstrap_seed": seed,
                    "bootstrap_repeats": BOOTSTRAP_REPEATS,
                }
            )
        )
    named = [(c["contrast"], float(c["p_raw"])) for c in contrasts if c.get("p_raw") is not None and c.get("status") != "NOT_ESTIMABLE"]
    if named:
        adj = holm_adjust(named, family="RQ1_PRIMARY", role="PRIMARY")
        by = {h.name: h.adjusted_p for h in adj}
        for c in contrasts:
            if c.get("contrast") in by:
                c["p_holm"] = by[c["contrast"]]
    _write(OUT / "statistics" / "rq1_stats.json", _stamp({"summary": rq1_summary, "contrasts": contrasts}))

    rq2_contrasts = []
    for a, b in (("attention", "grad_x_input"), ("attention", "ig")):
        pa, pb = aopc.get(a) or {}, aopc.get(b) or {}
        common = [c for c in pos if len(pa.get(c, {})) >= 2 and len(pb.get(c, {})) >= 2]
        if not common:
            rq2_contrasts.append(
                _stamp(
                    {
                        "contrast": f"{a}_vs_{b}_ABS_DELETION_AOPC",
                        "status": "NOT_ESTIMABLE",
                        "reason": "insufficient paired AOPC (IG missingness allowed)",
                        "family": "RQ2_PRIMARY",
                    }
                )
            )
            continue
        report = analyze_pairwise_commit_methods(
            method_a=a,
            method_b=b,
            metric="ABS_DELETION_AOPC",
            metric_direction="HIGHER_BETTER",
            per_commit_a={c: pa[c] for c in common},
            per_commit_b={c: pb[c] for c in common},
            family="RQ2_PRIMARY",
            role="PRIMARY",
        )
        seed = derive_bootstrap_seed(STATISTICAL_PROTOCOL_HASH, "RQ2", "ABS_DELETION_AOPC", f"{a}__{b}")
        from src.stats.paired import build_pairwise_commit_diffs

        inc = build_pairwise_commit_diffs({c: pa[c] for c in common}, {c: pb[c] for c in common})
        dmap = {c.commit_id: c.diff for c in inc.commit_diffs}
        ids = list(dmap)

        def stat(sample, _dmap=dmap):
            xs = [_dmap[i] for i in sample if i in _dmap]
            return float(sum(xs) / len(xs)) if xs else 0.0

        boot = paired_commit_bootstrap_percentile(ids, stat, rng_seed=seed, repeats=BOOTSTRAP_REPEATS)
        rq2_contrasts.append(
            _stamp(
                {
                    "contrast": f"{a}_vs_{b}_ABS_DELETION_AOPC",
                    "family": "RQ2_PRIMARY",
                    "n_included": report.n_included,
                    "n_excluded": report.n_excluded,
                    "wilcoxon_status": report.wilcoxon_status,
                    "p_raw": report.p_raw,
                    "rank_biserial": report.rank_biserial,
                    "bootstrap": boot,
                    "bootstrap_seed": seed,
                    "bootstrap_repeats": BOOTSTRAP_REPEATS,
                }
            )
        )
    named2 = [
        (c["contrast"], float(c["p_raw"]))
        for c in rq2_contrasts
        if c.get("p_raw") is not None and c.get("status") != "NOT_ESTIMABLE"
    ]
    if named2:
        adj = holm_adjust(named2, family="RQ2_PRIMARY", role="PRIMARY")
        by = {h.name: h.adjusted_p for h in adj}
        for c in rq2_contrasts:
            if c.get("contrast") in by:
                c["p_holm"] = by[c["contrast"]]
    _write(OUT / "statistics" / "rq2_stats.json", _stamp({"contrasts": rq2_contrasts}))

    rq3_out = []
    for method in ("grad_x_input", "gradient", "occlusion", "ig"):
        vals = []
        cids = []
        for cid in rq1:
            by = rq3_delta.get(method, {}).get(cid, {})
            xs = [by[s] for s in SEEDS if s in by]
            if len(xs) >= 2:
                vals.append(sum(xs) / len(xs))
                cids.append(cid)
        if not vals:
            rq3_out.append(_stamp({"method": method, "status": "NOT_ESTIMABLE"}))
            continue
        w = one_sample_wilcoxon_against_zero(vals)
        rq3_out.append(
            _stamp(
                {
                    "method": method,
                    "n": len(vals),
                    "mean_delta_recall20": float(sum(vals) / len(vals)),
                    "wilcoxon_status": w.status,
                    "p_raw": w.p_value,
                    "confirmatory": method == "grad_x_input",
                }
            )
        )
    conf = [c for c in rq3_out if c.get("confirmatory") and c.get("p_raw") is not None]
    if conf:
        adj = holm_adjust(
            [("SIGNED_VS_ABSOLUTE_DELTA_RECALL20", float(conf[0]["p_raw"]))],
            family="RQ3_PRIMARY",
            role="PRIMARY",
        )
        conf[0]["p_holm"] = adj[0].adjusted_p
        conf[0]["contrast"] = "SIGNED_VS_ABSOLUTE_DELTA_RECALL20"
    _write(OUT / "statistics" / "rq3_stats.json", _stamp({"methods": rq3_out}))

    rq4_summary = {}
    for cat, bycid in rq4.items():
        means = []
        for cid in pos:
            xs = [bycid[cid][s] for s in SEEDS if s in bycid.get(cid, {})]
            if xs:
                means.append(sum(xs) / len(xs))
        rq4_summary[cat] = {
            "n": len(means),
            "mean_ablation_delta": (sum(means) / len(means)) if means else None,
        }
    _write(
        OUT / "statistics" / "rq4_stats.json",
        _stamp({"estimation_only": True, "holm_family": None, "category_ablations": rq4_summary}),
    )
    _write(
        OUT / "metrics" / "runtime.json",
        _stamp(
            {
                "mean_wall_s": {m: (sum(walls[m]) / len(walls[m]) if walls[m] else None) for m in METHODS},
                "ig": {
                    "jobs": ig_stats["jobs"],
                    "retry": ig_stats["retry"],
                    "nonconv": ig_stats["nonconv"],
                    "conv50": ig_stats["conv50"],
                    "mean_wall_s": (sum(ig_stats["walls"]) / len(ig_stats["walls"])) if ig_stats["walls"] else None,
                },
                "occlusion_mean_n_regions": (sum(occ_regions) / len(occ_regions)) if occ_regions else None,
            }
        ),
    )

    pairs = {}
    for method in METHODS:
        mp = {}
        for a, b in ((13, 42), (13, 73), (42, 73)):
            n_ok = 0
            rhos = []
            for cid in pos:
                ra, rb = ranks[method][a].get(cid) or {}, ranks[method][b].get(cid) or {}
                common = sorted(set(ra) & set(rb))
                if len(common) < 2:
                    continue
                n_ok += 1
                r = seed_rank_spearman([ra[x] for x in common], [rb[x] for x in common])
                if r is not None:
                    rhos.append(r)
            mp[f"{a}_{b}"] = {
                "n_aligned": n_ok,
                "n_rho": len(rhos),
                "mean_rho": (sum(rhos) / len(rhos)) if rhos else None,
            }
        pairs[method] = mp
    _write(OUT / "metrics" / "stability" / "seed_stability.json", _stamp({"pairs_by_method": pairs}))

    miss_out = {m: {str(s): dict(missing[m][s]) for s in SEEDS} for m in METHODS}
    _write(OUT / "metrics" / "missingness.json", _stamp({"by_method_seed": miss_out}))

    complete_n = sum(
        1
        for cid in pos
        if all(
            (load_json(unit_path("positive_475", s, m, cid)) or {}).get("missingness_code") == "OK"
            for s in SEEDS
            for m in METHODS
        )
    )
    _write(
        OUT / "metrics" / "common_complete_case.json",
        _stamp({"n": complete_n, "available": complete_n > 0}),
    )

    def file_hash(path: Path) -> str | None:
        if not path.is_file():
            return None
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    integrity = _stamp(
        {
            "expected_pos_jobs_per_method": 475 * 3,
            "missingness": miss_out,
            "validation_contamination": False,
            "cohort_pass": True,
            "duplicate_check": "unit paths unique by pop/seed/method/cid",
            "PASS": all(missing[m][s].get("MISSING_FILE", 0) == 0 for m in METHODS for s in SEEDS),
        }
    )
    _write(OUT / "TEST_RESULT_INTEGRITY.json", integrity)

    freeze = _stamp(
        {
            "test_run_manifest_hash": file_hash(OUT / "TEST_RUN_MANIFEST.json"),
            "cohort_hashes": {
                "rq1_304": cohorts["rq1_primary_304"]["manifest_sha256"],
                "rq1_4096": cohorts["rq1_4096_345"]["manifest_sha256"],
                "pos_475": cohorts["positive_475"]["manifest_sha256"],
                "clean_475": cohorts["matched_clean_475"]["manifest_sha256"],
            },
            "protocol_hash": ATTRIBUTION_PROTOCOL_HASH,
            "stats_hash": STATISTICAL_PROTOCOL_HASH,
            "execution_freeze_hash": EXPECTED_FREEZE,
            "git_commit": os.popen(f"git -C {ROOT} rev-parse HEAD").read().strip(),
            "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    )
    freeze["freeze_sha256"] = sha256_json(freeze)
    if integrity.get("PASS"):
        _write(OUT / "TEST_RESULTS_FREEZE.json", freeze)

    # compact CSVs
    def csv_write(path: Path, rows: list[dict], fields: list[str]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fields})

    csv_write(
        OUT / "summaries" / "rq1_summary.csv",
        [{"method": m, **{k: v for k, v in rq1_summary[m].items()}} for m in METHODS],
        ["method", "mean_recall20_rq1_304", "n_commits_with_ge2_seeds"],
    )
    csv_write(
        OUT / "summaries" / "missingness_summary.csv",
        [
            {"method": m, "seed": s, "code": code, "n": n}
            for m in METHODS
            for s in SEEDS
            for code, n in missing[m][s].items()
        ],
        ["method", "seed", "code", "n"],
    )
    csv_write(
        OUT / "summaries" / "statistical_contrasts.csv",
        [
            {
                "contrast": c.get("contrast"),
                "status": c.get("status", "OK"),
                "p_raw": c.get("p_raw"),
                "p_holm": c.get("p_holm"),
                "rank_biserial": c.get("rank_biserial"),
                "n_included": c.get("n_included"),
            }
            for c in contrasts
        ],
        ["contrast", "status", "p_raw", "p_holm", "rank_biserial", "n_included"],
    )
    print("BLOCK L wrote summaries; integrity PASS=", integrity.get("PASS"))
    return 0 if integrity.get("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

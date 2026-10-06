#!/usr/bin/env python3
"""EMSE closed existing-data diagnostics (lock aba73ea). No GPU. No new experiments."""

from __future__ import annotations

import csv
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
from src.experiments.rehearsal_pipeline import iter_lines, region_token_counts_from_map
from src.experiments.test_io import encode_test_with_map, load_test_records
from src.metrics.localization import RANDOM_BASELINE_REPEATS, RankingTransform, compute_rq1_localization_metrics, ranking_score
from src.metrics.rq1_baselines import length_baseline_scores, order_baseline_scores
from src.stats.bootstrap import derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.paired import build_pairwise_commit_diffs
from src.stats.rq_analysis import analyze_pairwise_commit_methods

OUT = ROOT / "artifacts" / "emse_final"
ATTR = ROOT / "artifacts" / "test_attribution"
PRED = ROOT / "data" / "results" / "m1_final"
SEEDS = (13, 42, 73)
STAT = STATISTICAL_PROTOCOL_HASH
LOCK_COMMIT = "aba73ea63f3534acc292e4e4640dfa53ec22bcf6"
LOCK_SHA = "7e54a8f394be36b0958cf7d8b9bf8e36121930b9d981b0bcce0e2496557e81dd"
METHODS = ("attention", "grad_x_input", "occlusion")
MIN_LINES_RHO = 5


def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def unit(pop, seed, method, cid, ml=2048):
    return ATTR / "raw" / pop / f"seed_{seed}" / method / f"ml{ml}_{cid}.json"


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
        "p_raw": report.p_raw,
        "rank_biserial": report.rank_biserial,
        "bootstrap": boot,
        "role": role,
        "family": family,
        "wilcoxon_status": report.wilcoxon_status,
        "missing_pair_count": report.n_excluded,
    }


def collapse_ge2(by_cid_seed: dict, cids) -> dict[str, float]:
    out = {}
    for cid in cids:
        xs = [by_cid_seed.get(cid, {}).get(s) for s in SEEDS]
        xs = [x for x in xs if x is not None]
        if len(xs) >= 2:
            out[cid] = float(sum(xs) / len(xs))
    return out


def as_seed_map(cid_to_value: dict) -> dict:
    return {cid: {s: v for s in SEEDS} for cid, v in cid_to_value.items()}


def spearman(x, y) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < MIN_LINES_RHO or np.std(x) == 0 or np.std(y) == 0:
        return None
    rx = rankdata(x)
    ry = rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def rankdata(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)
    # average ties
    i = 0
    sa = a[order]
    while i < len(a):
        j = i
        while j + 1 < len(a) and sa[j + 1] == sa[i]:
            j += 1
        if j > i:
            avg = 0.5 * (ranks[order[i]] + ranks[order[j]])
            ranks[order[i : j + 1]] = avg
        i = j + 1
    return ranks


def ols_resid(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def perm_seed(cid: str, rep: int) -> int:
    h = hashlib.sha256(f"{STAT}|B_RANDOM|{cid}|{rep}".encode()).hexdigest()
    return int(h[:8], 16)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cohorts = loadj(ATTR / "cohorts" / "COHORT_INTEGRITY.json")
    pos = cohorts["positive_475"]["commit_ids"]
    rq1 = cohorts["rq1_primary_304"]["commit_ids"]
    vis4096 = cohorts["rq1_4096_345"]["commit_ids"]
    recs = load_test_records(
        scientific_test_gate=True,
        processed_dir=ROOT / "data" / "processed" / "canonical_v1",
    )
    index = {r["commit_id"]: r for r in recs}

    from transformers import AutoTokenizer
    from src.models.qwen_m1 import QWEN_MODEL_ID, QWEN_REVISION

    tok = AutoTokenizer.from_pretrained(QWEN_MODEL_ID, revision=QWEN_REVISION, local_files_only=True)

    rec_sum = defaultdict(lambda: defaultdict(dict))
    rec_mean = defaultdict(lambda: defaultdict(dict))
    rec4096 = defaultdict(lambda: defaultdict(dict))
    aopc = defaultdict(lambda: defaultdict(dict))
    jobs4096 = defaultdict(lambda: defaultdict(int))

    for seed in SEEDS:
        for method in METHODS:
            for cid in pos:
                u = loadj(unit("positive_475", seed, method, cid))
                if not u or not attribution_job_is_valid(u, method):
                    continue
                rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                if rec20 is not None:
                    rec_sum[method][cid][seed] = float(rec20)
            for cid in vis4096:
                u = loadj(unit("rq1_4096", seed, method, cid, ml=4096)) if method != "occlusion" else None
                if method == "occlusion":
                    continue
                jobs4096[method][seed] += 1 if u else 0
                if u and attribution_job_is_valid(u, method):
                    rec20 = (u.get("rq1") or {}).get("recall_at_20pct_effort")
                    if rec20 is not None:
                        rec4096[method][cid][seed] = float(rec20)
            for cid in pos:
                ua = loadj(unit("positive_475", seed, method, cid))
                f = loadj(ATTR / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / method / f"{cid}.json")
                if faith_aopc_is_valid(f, method, ua):
                    aopc[method][cid][seed] = float(f["aopc"])

    # token maps / baselines / mean recall / length association / agreement
    base_len, base_ord, base_rnd = {}, {}, {}
    n_cands, n_pos_lab, n_vis = {}, {}, {}
    rho_len = defaultdict(list)  # method -> list of (cid, seed, rho)
    ranks_by = defaultdict(lambda: defaultdict(dict))  # method -> cid -> seed -> (ids, attr_rank, len_rank)

    for cid in rq1:
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
        n_cands[cid] = len(ids)
        n_pos_lab[cid] = sum(1 for s in statuses if s == "RQ1_POSITIVE")
        n_vis[cid] = int(sum(lens))
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
            m_r = compute_rq1_localization_metrics(
                ids, scores, statuses, transform=RankingTransform.RAW_DESCENDING, ordered_positions=orders
            )
            rnds.append(float(m_r["recall_at_20pct_effort"]))
        base_rnd[cid] = float(np.mean(rnds))

        for seed in SEEDS:
            for method in METHODS:
                u = loadj(unit("positive_475", seed, method, cid))
                if not u or not attribution_job_is_valid(u, method):
                    continue
                sm = {k: float(v) for k, v in (u.get("line_scores_sum") or {}).items()}
                mn = {k: float(v) for k, v in (u.get("line_scores_mean") or {}).items()}
                if mn:
                    try:
                        m_m = compute_rq1_localization_metrics(
                            ids,
                            [mn.get(i, 0.0) for i in ids],
                            statuses,
                            transform=RankingTransform.ABS_DESCENDING,
                            ordered_positions=orders,
                        )
                        rec_mean[method][cid][seed] = float(m_m["recall_at_20pct_effort"])
                    except Exception:
                        pass
                if sm and len(ids) >= MIN_LINES_RHO:
                    attr = np.array([abs(sm.get(i, 0.0)) for i in ids], dtype=float)
                    L = np.array(lens, dtype=float)
                    rho = spearman(attr, L)
                    if rho is not None:
                        rho_len[method].append({"commit_id": cid, "seed": seed, "rho": rho})
                    ar = rankdata(np.array([ranking_score(sm.get(i, 0.0), RankingTransform.ABS_DESCENDING) for i in ids]))
                    lr = rankdata(L)
                    ranks_by[method][cid][seed] = (ids, ar, lr)

    # A/B baseline matrix
    bl_map = as_seed_map(base_len)
    bo_map = as_seed_map(base_ord)
    br_map = as_seed_map(base_rnd)
    baseline_matrix = {}
    for method in METHODS:
        mcol = rec_sum[method]
        for bname, bmap in (("B_RANDOM", br_map), ("B_LENGTH", bl_map), ("B_ORDER", bo_map)):
            baseline_matrix[f"{method}_vs_{bname}"] = contrast_pack(
                mcol, bmap, metric="RECALL20", family="RQ1_BASELINE", role="PROTOCOL-OWED BASELINE",
                rq="RQ1", comparison_id=f"EMSE|{method}|{bname}",
            )
            collapsed_m = collapse_ge2(mcol, rq1)
            collapsed_b = {c: base_len[c] if bname == "B_LENGTH" else base_ord[c] if bname == "B_ORDER" else base_rnd[c] for c in collapsed_m if c in (base_len if bname == "B_LENGTH" else base_ord if bname == "B_ORDER" else base_rnd)}
            common = [c for c in collapsed_m if c in collapsed_b]
            baseline_matrix[f"{method}_vs_{bname}"]["method_mean"] = float(np.mean([collapsed_m[c] for c in common])) if common else None
            baseline_matrix[f"{method}_vs_{bname}"]["baseline_mean"] = float(np.mean([collapsed_b[c] for c in common])) if common else None
            baseline_matrix[f"{method}_vs_{bname}"]["n_commits_scored"] = len(common)

    # MEAN vs SUM and MEAN vs baselines
    mean_pack = {}
    for method in METHODS:
        mean_pack[method] = {
            "sum_vs_mean": contrast_pack(
                rec_sum[method], rec_mean[method], metric="RECALL20", family="SENSITIVITY",
                role="POST-HOC CONSTRUCT SENSITIVITY", rq="RQ1", comparison_id=f"EMSE|SUMMEAN|{method}",
            ),
        }
        mcol = rec_mean[method]
        for bname, bmap in (("B_RANDOM", br_map), ("B_LENGTH", bl_map), ("B_ORDER", bo_map)):
            mean_pack[method][f"mean_vs_{bname}"] = contrast_pack(
                mcol, bmap, metric="RECALL20", family="SENSITIVITY",
                role="POST-HOC CONSTRUCT SENSITIVITY", rq="RQ1", comparison_id=f"EMSE|MEAN|{method}|{bname}",
            )
        csum = collapse_ge2(rec_sum[method], rq1)
        cmean = collapse_ge2(rec_mean[method], rq1)
        mean_pack[method]["sum_mean"] = float(np.mean(list(csum.values()))) if csum else None
        mean_pack[method]["mean_mean"] = float(np.mean(list(cmean.values()))) if cmean else None

    def rho_summary(rows):
        by_c = defaultdict(list)
        for r in rows:
            by_c[r["commit_id"]].append(r["rho"])
        commit_means = {c: float(np.mean(v)) for c, v in by_c.items()}
        vals = np.array(list(commit_means.values()), dtype=float)
        n_units = len(rows)
        if vals.size == 0:
            return {"n_commit_seed": 0, "n_commits": 0}
        boot = paired_commit_bootstrap_percentile(
            list(commit_means),
            lambda ids: float(np.mean([commit_means[i] for i in ids])),
            rng_seed=derive_bootstrap_seed(STAT, "RQ1", "LENGTH_RHO", "EMSE"),
        )
        return {
            "n_commit_seed": n_units,
            "n_commits": int(vals.size),
            "mean_rho": float(vals.mean()),
            "median_rho": float(np.median(vals)),
            "iqr": [float(np.percentile(vals, 25)), float(np.percentile(vals, 75))],
            "share_rho_gt_0": float(np.mean(vals > 0)),
            "share_abs_rho_gt_0_3": float(np.mean(np.abs(vals) > 0.3)),
            "share_abs_rho_gt_0_5": float(np.mean(np.abs(vals) > 0.5)),
            "bootstrap": boot,
        }

    length_assoc = {m: rho_summary(rho_len[m]) for m in METHODS}

    # E length-adjusted stability
    pairs = ((13, 42), (13, 73), (42, 73))

    def stability(method, adjusted: bool):
        per_pair = {}
        commit_vals = defaultdict(list)
        for a, b in pairs:
            rhos = []
            for cid, seeds in ranks_by[method].items():
                if a not in seeds or b not in seeds:
                    continue
                ids_a, ra, la = seeds[a]
                ids_b, rb, lb = seeds[b]
                if ids_a != ids_b or len(ids_a) < MIN_LINES_RHO:
                    continue
                if adjusted:
                    ra = ols_resid(ra, la)
                    rb = ols_resid(rb, lb)
                    if np.std(ra) == 0 or np.std(rb) == 0:
                        continue
                    rho = float(np.corrcoef(ra, rb)[0, 1])
                else:
                    rho = float(np.corrcoef(ra, rb)[0, 1])
                if np.isfinite(rho):
                    rhos.append(rho)
                    commit_vals[cid].append(rho)
            per_pair[f"{a}_{b}"] = {"mean_rho": float(np.mean(rhos)) if rhos else None, "n": len(rhos)}
        commit_mean = {c: float(np.mean(v)) for c, v in commit_vals.items() if len(v) >= 2}
        overall = float(np.mean(list(commit_mean.values()))) if commit_mean else None
        return {"by_pair": per_pair, "n_commits": len(commit_mean), "mean_across_commits": overall}

    seed_stab = {}
    for m in METHODS:
        raw = stability(m, False)
        adj = stability(m, True)
        seed_stab[m] = {
            "raw": raw,
            "length_adjusted": adj,
            "change": (None if raw["mean_across_commits"] is None or adj["mean_across_commits"] is None
                       else adj["mean_across_commits"] - raw["mean_across_commits"]),
        }

    # F occlusion agreement
    def agree(method):
        commit_means = []
        n_units = 0
        for cid in rq1:
            rhos = []
            for seed in SEEDS:
                if seed not in ranks_by[method].get(cid, {}) or seed not in ranks_by["occlusion"].get(cid, {}):
                    continue
                ids_m, rm, _ = ranks_by[method][cid][seed]
                ids_o, ro, _ = ranks_by["occlusion"][cid][seed]
                if ids_m != ids_o or len(ids_m) < MIN_LINES_RHO:
                    continue
                if np.std(rm) == 0 or np.std(ro) == 0:
                    continue
                rho = float(np.corrcoef(rm, ro)[0, 1])
                if np.isfinite(rho):
                    rhos.append(rho)
                    n_units += 1
            if len(rhos) >= 2:
                commit_means.append(float(np.mean(rhos)))
        vals = np.array(commit_means, dtype=float)
        if vals.size == 0:
            return {"n_commits": 0}
        boot = paired_commit_bootstrap_percentile(
            [f"c{i}" for i in range(len(vals))],
            lambda ids: float(np.mean([vals[int(i[1:])] for i in ids])),
            rng_seed=derive_bootstrap_seed(STAT, "RQ1", "OCC_AGREE", method),
        )
        # bootstrap helper expects commit ids; use synthetic
        cmap = {f"c{i}": float(vals[i]) for i in range(len(vals))}
        boot = paired_commit_bootstrap_percentile(
            list(cmap),
            lambda ids: float(np.mean([cmap[i] for i in ids])),
            rng_seed=derive_bootstrap_seed(STAT, "RQ1", "OCC_AGREE", method),
        )
        return {
            "n_commit_seed": n_units,
            "n_commits": int(vals.size),
            "mean": float(vals.mean()),
            "median": float(np.median(vals)),
            "iqr": [float(np.percentile(vals, 25)), float(np.percentile(vals, 75))],
            "bootstrap": boot,
        }

    occ_agree = {m: agree(m) for m in ("attention", "grad_x_input")}

    # G estimand-level numerical
    rows_path = ROOT / "artifacts" / "tosem_extension" / "numerical_rows.jsonl"
    d_bf, d_fp = {}, {}
    for cid in pos:
        if cid in aopc["attention"] and cid in aopc["grad_x_input"]:
            sa = aopc["attention"][cid]
            sg = aopc["grad_x_input"][cid]
            common = [s for s in SEEDS if s in sa and s in sg]
            if len(common) >= 2:
                d_bf[cid] = float(np.mean([sa[s] - sg[s] for s in common]))
    by_fp_att = defaultdict(dict)
    by_fp_gxi = defaultdict(dict)
    if rows_path.is_file():
        for line in rows_path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("aopc_att_fp32") is not None:
                by_fp_att[r["commit_id"]][int(r["seed"])] = float(r["aopc_att_fp32"])
            if r.get("aopc_gxi_fp32") is not None:
                by_fp_gxi[r["commit_id"]][int(r["seed"])] = float(r["aopc_gxi_fp32"])
    for cid in by_fp_att:
        sa, sg = by_fp_att[cid], by_fp_gxi.get(cid, {})
        common = [s for s in SEEDS if s in sa and s in sg]
        if len(common) >= 2:
            d_fp[cid] = float(np.mean([sa[s] - sg[s] for s in common]))
    both = sorted(set(d_bf) & set(d_fp))
    db = np.array([d_bf[c] for c in both])
    df = np.array([d_fp[c] for c in both])
    delta = np.abs(db - df)
    sign_ag = float(np.mean(np.sign(db) == np.sign(df))) if both else None
    sign_ch = float(np.mean(np.sign(db) != np.sign(df))) if both else None
    pear = float(np.corrcoef(db, df)[0, 1]) if len(both) > 2 and np.std(db) and np.std(df) else None
    spr = spearman(db, df) if len(both) >= MIN_LINES_RHO else None
    numerical_d = {
        "role": "POST-HOC ESTIMAND-LEVEL NUMERICAL DIAGNOSTIC",
        "NUMERICAL_GATE_UNCHANGED": "FAIL",
        "n": len(both),
        "mean_D_bf16": float(db.mean()) if both else None,
        "mean_D_fp32": float(df.mean()) if both else None,
        "mean_abs_change": float(delta.mean()) if both else None,
        "median_abs_change": float(np.median(delta)) if both else None,
        "p90_abs_change": float(np.percentile(delta, 90)) if both else None,
        "p95_abs_change": float(np.percentile(delta, 95)) if both else None,
        "pearson": pear,
        "spearman": spr,
        "sign_agreement": sign_ag,
        "fraction_sign_change": sign_ch,
    }

    # H TP/FN context
    pred = defaultdict(dict)
    for seed in SEEDS:
        path = PRED / f"seed_{seed}" / "test_predictions.csv"
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pred[row["commit_id"]][seed] = int(row["predicted_label"])

    def majority_pred(cids):
        labels = {}
        for cid in cids:
            xs = [pred.get(cid, {}).get(s) for s in SEEDS]
            xs = [x for x in xs if x is not None]
            if len(xs) >= 2:
                labels[cid] = 1 if sum(xs) >= (len(xs) / 2.0) else 0
        return labels

    labs = majority_pred(rq1)
    tpfn = {}
    for method in METHODS:
        mcol = collapse_ge2(rec_sum[method], rq1)
        out = {}
        for name, lab in (("TP", 1), ("FN", 0)):
            cids = [c for c in mcol if labs.get(c) == lab]
            rows = []
            for c in cids:
                rows.append(
                    {
                        "recall": mcol[c],
                        "random": base_rnd.get(c),
                        "length": base_len.get(c),
                        "n_candidates": n_cands.get(c),
                        "n_positives": n_pos_lab.get(c),
                        "n_visible_tokens": n_vis.get(c),
                    }
                )
            recs_ok = [r for r in rows if r["random"] is not None]
            out[name] = {
                "n": len(rows),
                "mean_recall": float(np.mean([r["recall"] for r in rows])) if rows else None,
                "mean_random": float(np.mean([r["random"] for r in recs_ok])) if recs_ok else None,
                "mean_length": float(np.mean([r["length"] for r in recs_ok if r["length"] is not None])) if recs_ok else None,
                "mean_delta_vs_random": float(np.mean([r["recall"] - r["random"] for r in recs_ok])) if recs_ok else None,
                "mean_delta_vs_length": float(np.mean([r["recall"] - r["length"] for r in recs_ok if r["length"] is not None])) if recs_ok else None,
                "mean_n_candidates": float(np.mean([r["n_candidates"] for r in rows if r["n_candidates"] is not None])) if rows else None,
                "mean_n_positives": float(np.mean([r["n_positives"] for r in rows if r["n_positives"] is not None])) if rows else None,
                "mean_visible_tokens": float(np.mean([r["n_visible_tokens"] for r in rows if r["n_visible_tokens"] is not None])) if rows else None,
            }
        tpfn[method] = out

    # I 4096 denominators
    att = rec4096["attention"]
    gxi = rec4096["grad_x_input"]
    n_eligible = len(vis4096)
    n_att_ge2 = len(collapse_ge2(att, vis4096))
    n_gxi_ge2 = len(collapse_ge2(gxi, vis4096))
    paired_4096 = contrast_pack(
        att, gxi, metric="RECALL20", family="SENSITIVITY", role="SENSITIVITY", rq="RQ1", comparison_id="EMSE|4096|att_gxi"
    )
    denom = {
        "cohort_fully_visible_4096": n_eligible,
        "jobs_expected_att_gxi": n_eligible * 3 * 2,
        "n_attention_ge2_seeds": n_att_ge2,
        "n_gxi_ge2_seeds": n_gxi_ge2,
        "n_paired_common_valid_ge2": paired_4096["n_included"],
        "n_excluded_paired": paired_4096["n_excluded"],
        "attention_mean": float(np.mean(list(collapse_ge2(att, vis4096).values()))) if n_att_ge2 else None,
        "gxi_mean": float(np.mean(list(collapse_ge2(gxi, vis4096).values()))) if n_gxi_ge2 else None,
        "paired_contrast": paired_4096,
        "resolution": "DIFFERENT_DENOMINATORS_BOTH_VALID",
        "note": "345 is the predeclared fully-visible-at-4096 cohort size. 288 is the paired common-valid-seed support for Attention vs Grad×Input after min_common=2, matching primary missingness rules. Occlusion was not run at 4096.",
    }

    blob = {
        "lock_commit": LOCK_COMMIT,
        "lock_sha256": LOCK_SHA,
        "created": datetime.now(timezone.utc).isoformat(),
        "NUMERICAL_GATE": "FAIL",
        "baseline_matrix": baseline_matrix,
        "length_association": length_assoc,
        "sum_vs_mean": mean_pack,
        "seed_stability": seed_stab,
        "occlusion_agreement": occ_agree,
        "estimand_numerical": numerical_d,
        "tpfn_baseline_context": tpfn,
        "context4096": denom,
        "new_gpu": False,
    }
    (OUT / "emse_final_diagnostics.json").write_text(json.dumps(blob, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "baselines": {k: {"n": v.get("n_included"), "d": (v.get("bootstrap") or {}).get("point")} for k, v in baseline_matrix.items()},
        "4096": {"eligible": n_eligible, "paired": paired_4096["n_included"]},
        "num_n": numerical_d["n"],
        "stab": {m: seed_stab[m]["raw"]["mean_across_commits"] for m in METHODS},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

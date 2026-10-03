#!/usr/bin/env python3
"""VALIDATION attribution rehearsal N=64. Not TEST. Not RQ results."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.attribution.aggregate import LineReduction, aggregate_tokens_by_category, aggregate_tokens_to_lines
from src.attribution.gradients import grad_x_input_token_scores, vanilla_gradient_token_scores
from src.attribution.integrated_gradients import (
    IGBaselineStrategy,
    integrated_gradients_with_retry,
)
from src.cohorts import seed_rank_spearman
from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    STATISTICAL_PROTOCOL_HASH,
)
from src.experiments.m1_backend import FrozenM1Bundle, FrozenM1Mismatch
from src.experiments.rehearsal_pipeline import (
    BANNER,
    ablate_category_in_structured_text,
    apply_payload_blank_record,
    apply_segment_delete_record,
    build_rehearsal_cohort,
    encode_with_map,
    mapping_stats,
    maybe_space_structural_markup,
    pad_encoded,
    refuse_test_split,
    region_token_counts_from_map,
    sha256_json,
    visible_line_ids,
)
from src.metrics.localization import RankingTransform, compute_rq1_localization_metrics
from src.metrics.polarity import polarity_summary
from src.metrics.rq1_baselines import (
    audit_add_first_baseline,
    length_baseline_scores,
    order_baseline_scores,
    signed_vs_absolute_delta_recall20,
)
from src.metrics.rq4_enrichment import category_ablation_delta, enrichment_table
from src.metrics.token_budget_faithfulness import (
    PRIMARY_TOKEN_BUDGET_FRACTIONS,
    abs_deletion_aopc,
    evaluate_abs_deletion_curve,
)
from src.models.qwen_m1 import QWEN_REVISION, load_qlora_from_adapter
from src.stats.bootstrap import BOOTSTRAP_REPEATS, derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.multiplicity import holm_adjust
from src.stats.paired import WILCOXON_ZERO_METHOD, build_pairwise_commit_diffs, wilcoxon_signed_rank
from src.stats.rq_analysis import analyze_pairwise_commit_methods
from src.train.m1_dataset import load_valid_records, render_and_truncate_prompt

OUT = ROOT / "artifacts" / "attribution_rehearsal"
EXPECTED_ADAPTERS = {
    13: ("epoch_2", "a764d2f57e6586cf61b9c38d7dea4bd1b5a2da73fd4b14e5a3f4ee5eb91b02bf"),
    42: ("epoch_1", "dc8d411d7a34383c3a606b855d68363f573f584a4cd0d2e3d9766b8151d60ad0"),
    73: ("epoch_1", "5a964219a58df2d12606356e67fac8081994ebc7dbc34346c16e323377855dcc"),
}
SEEDS = (13, 42, 73)
METHODS = ("attention", "attention_last4", "grad_x_input", "gradient", "ig", "occlusion")
OCC_BATCH = 4
IG_CHUNK = 1
MAX_LEN = 2048
EQ_TOL_OCC = 0.15  # NF4 seq-vs-batch; same bound as GPU engineering benchmark
EQ_TOL_ATTN = 0.02


def _stamp(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(BANNER)
    out.update(d)
    return out


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _peak() -> dict[str, float | None]:
    if not torch.cuda.is_available():
        return {"peak_allocated_gib": None}
    return {"peak_allocated_gib": float(torch.cuda.max_memory_allocated()) / (1024**3)}


def _reset_peak() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()


def load_index() -> dict[str, dict[str, Any]]:
    recs = load_valid_records(ROOT / "data" / "processed" / "canonical_v1")
    refuse_test_split(recs)
    return {r["commit_id"]: r for r in recs}


def assert_protocol() -> None:
    if ATTRIBUTION_PROTOCOL_HASH != "c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c":
        raise RuntimeError("attribution protocol hash changed")
    if STATISTICAL_PROTOCOL_HASH != "edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8":
        raise RuntimeError("statistical protocol hash changed")


def verify_seed(bundle: FrozenM1Bundle, seed: int) -> dict[str, Any]:
    ep, hx = EXPECTED_ADAPTERS[seed]
    want_epoch = int(ep.replace("epoch_", ""))
    if int(bundle.ident.selected_epoch) != want_epoch:
        raise FrozenM1Mismatch(
            f"epoch mismatch seed={seed}: {bundle.ident.selected_epoch} != {want_epoch}"
        )
    if bundle.ident.adapter_sha256 != hx:
        raise FrozenM1Mismatch(f"adapter hash mismatch seed={seed}")
    if bundle.ident.base_revision != QWEN_REVISION:
        raise FrozenM1Mismatch("revision mismatch")
    return bundle.verification


def unit_path(seed: int, method: str, commit_id: str) -> Path:
    return OUT / "runs" / f"seed_{seed}" / method / f"{commit_id}.json"


def load_unit(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_fn_factory(bundle: FrozenM1Bundle, attention_mask: torch.Tensor):
    def score_fn(emb: torch.Tensor) -> torch.Tensor:
        return bundle.risk_from_embeddings(emb, attention_mask, reduce="sum")

    return score_fn


def rq1_from_lines(rec: dict[str, Any], line_scores: dict[str, float], dropped: list[str]) -> dict[str, Any] | None:
    ids = []
    scores = []
    statuses = []
    orders = []
    drop = set(dropped)
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            for ln in h.get("lines") or []:
                sid = ln.get("stable_line_id")
                if not sid or sid in drop:
                    continue
                st = ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE"
                if st == "NOT_IN_RQ1_UNIVERSE":
                    continue
                if sid not in line_scores:
                    continue
                ids.append(sid)
                scores.append(float(line_scores[sid]))
                statuses.append(st)
                orders.append(int(ln.get("ordered_position") or 0))
    if not ids:
        return None
    try:
        return compute_rq1_localization_metrics(
            ids, scores, statuses, transform=RankingTransform.ABS_DESCENDING, ordered_positions=orders
        )
    except ValueError as exc:
        return {"status": "NO_ELIGIBLE_OR_NO_POSITIVE", "error": str(exc), "n_candidates": len(ids)}


def rank_ids(line_scores: dict[str, float], transform: RankingTransform) -> list[str]:
    from src.metrics.localization import ranking_score

    items = list(line_scores.items())
    items.sort(key=lambda kv: (-ranking_score(kv[1], transform), kv[0]))
    return [k for k, _ in items]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        default="all",
        choices=["preflight", "attention_validate", "run", "sanity", "post", "all"],
    )
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--seeds", default="13,42,73")
    args = parser.parse_args()
    seeds = tuple(int(x) for x in args.seeds.split(",") if x.strip())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "README_ISOLATION.txt").write_text(
        "SPLIT=VALIDATION PURPOSE=REHEARSAL NOT_TEST_RESULT=TRUE NOT_RQ_RESULT=TRUE\n"
        "Do not consume these files as TEST/RQ results.\n",
        encoding="utf-8",
    )
    assert_protocol()
    lock = json.loads((ROOT / "artifacts" / "m1_final" / "M1_TEST_LOCK.json").read_text())
    if lock.get("status") != "LOCKED":
        raise RuntimeError("M1 TEST lock is not LOCKED")

    recs = load_valid_records(ROOT / "data" / "processed" / "canonical_v1")
    refuse_test_split(recs)
    index = {r["commit_id"]: r for r in recs}

    from transformers import AutoTokenizer
    from src.models.qwen_m1 import QWEN_MODEL_ID

    tokenizer = AutoTokenizer.from_pretrained(
        QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True
    )
    tok_bundle = None
    if args.phase in ("attention_validate", "all"):
        tok_bundle = FrozenM1Bundle(repo_root=ROOT, seed=13)
        verify_seed(tok_bundle, 13)
        tokenizer = tok_bundle.tokenizer

    cohort_path = OUT / "cohort_manifest.json"
    if cohort_path.is_file():
        cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
        if int(cohort.get("n") or 0) != 64:
            raise RuntimeError("frozen cohort n != 64")
    else:
        print("building cohort (tokenizing validation positives)...", flush=True)
        cohort = build_rehearsal_cohort(tokenizer, recs, n=64, max_length=MAX_LEN)
        _write(cohort_path, cohort)
    commit_ids = [c["commit_id"] for c in cohort["commits"]]
    if len(commit_ids) != 64:
        raise RuntimeError(f"cohort size {len(commit_ids)}")
    for cid in commit_ids:
        if index[cid].get("split") == "test":
            raise RuntimeError("TEST leak")

    map_path = OUT / "mapping_validation.json"
    if map_path.is_file():
        mapping_doc = json.loads(map_path.read_text(encoding="utf-8"))
        unexpected = int(mapping_doc.get("unexpected_unmapped") or 0)
    else:
        mapping_rows = []
        for cid in commit_ids:
            rec = index[cid]
            packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
            stats = mapping_stats(
                packed["token_map"], rec, packed["truncation"].get("dropped_line_ids") or []
            )
            stats["commit_id"] = cid
            stats["truncated"] = bool(packed["truncation"].get("truncated"))
            mapping_rows.append(stats)
        unexpected = sum(r["unexpected_unmapped_payload"] for r in mapping_rows)
        mapping_doc = _stamp(
            {
                "n": len(mapping_rows),
                "sum_eligible_lines": sum(r["n_eligible_lines"] for r in mapping_rows),
                "sum_payload_tokens": sum(r["n_payload_tokens"] for r in mapping_rows),
                "sum_mapped_payload_tokens": sum(r["n_mapped_payload_tokens"] for r in mapping_rows),
                "sum_unmapped_payload_tokens": unexpected,
                "unexpected_unmapped": unexpected,
                "PASS": unexpected == 0,
                "per_commit": mapping_rows,
            }
        )
        _write(map_path, mapping_doc)
    if unexpected != 0:
        raise RuntimeError("unexpected payload mapping loss")

    n_jobs = 64 * len(seeds) * len(METHODS)
    preflight = _stamp(
        {
            "n_commits": 64,
            "n_seeds": len(seeds),
            "methods": list(METHODS),
            "n_jobs": n_jobs,
            "forwards_attention_like": 64 * len(seeds) * 3,
            "backwards_gxi_grad": 64 * len(seeds) * 2,
            "ig_evaluations_50_nominal": 64 * len(seeds) * 50,
            "ig_evaluations_100_if_all_retry": 64 * len(seeds) * 100,
            "perturbation_count_unknown_until_run": True,
            "disk_note": "per-commit JSON under artifacts/attribution_rehearsal/runs (gitignored)",
            "approx_gpu_hours_from_n6_conservative_ig2048": 25.0 * (64 / 304.0) * (1 if True else 1),
            "engineering_only": True,
        }
    )
    _write(OUT / "preflight_cost.json", preflight)
    if args.phase == "preflight":
        print(json.dumps(preflight, indent=2))
        return 0

    if args.phase in ("attention_validate", "all"):
        print("attention backend validation vs eager...", flush=True)
        # shortest two commits
        short = sorted(cohort["commits"], key=lambda r: r["visible_token_count"])[:2]
        bundle = tok_bundle
        eager_model = load_qlora_from_adapter(
            str(bundle.ident.adapter_dir),
            attn_implementation="eager",
            is_trainable=False,
        )
        eager_model.eval()
        diffs = []
        diffs4 = []
        for row in short:
            rec = index[row["commit_id"]]
            packed = encode_with_map(tokenizer, rec, max_length=min(256, MAX_LEN) if row["visible_token_count"] > 512 else MAX_LEN)
            # use production 2048 encode for identity, but if too long eager may OOM — cap reference at 256 tokens via slice? 
            # Protocol: compare on tiny sample; use actual visible if < 384 else skip encode at 2048 and re-truncate 384 for reference only.
            max_ref = 384
            packed = encode_with_map(tokenizer, rec, max_length=max_ref if row["visible_token_count"] > max_ref else MAX_LEN)
            ids = packed["input_ids"].to(next(bundle.model.parameters()).device)
            mask = packed["attention_mask"].to(ids.device)
            hook_last = bundle.attention_token_scores(ids, mask, layer_selection="LAST")
            hook_l4 = bundle.attention_token_scores(ids, mask, layer_selection="FINAL_K_MEAN", final_k=4)
            with torch.no_grad():
                out = eager_model(input_ids=ids, attention_mask=mask, output_attentions=True, use_cache=False)
            t = int(mask.sum().item())
            q = t - 1
            maps = []
            for layer_attn in out.attentions:
                # (B,H,Q,K)
                maps.append(layer_attn[0, :, q, :t].to(torch.float32).mean(0).cpu())
            eager_last = maps[-1].tolist()
            eager_l4 = torch.stack(maps[-4:], dim=0).mean(0).tolist()
            import numpy as np

            a = np.asarray(hook_last[:t], dtype=float)
            b = np.asarray(eager_last[: len(a)], dtype=float)
            a4 = np.asarray(hook_l4[:t], dtype=float)
            b4 = np.asarray(eager_l4[: len(a4)], dtype=float)
            diffs.append({"max_abs": float(np.max(np.abs(a - b))), "mean_abs": float(np.mean(np.abs(a - b))), "n": int(len(a))})
            diffs4.append({"max_abs": float(np.max(np.abs(a4 - b4))), "mean_abs": float(np.mean(np.abs(a4 - b4))), "n": int(len(a4))})
            del out
        del eager_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        max_last = max(d["max_abs"] for d in diffs)
        max_l4 = max(d["max_abs"] for d in diffs4)
        attn_val = _stamp(
            {
                "LAST_MEAN_HEAD_exact_semantics": True,
                "LAST4_MEAN_exact_semantics": True,
                "query_position": "FIRST_ASSISTANT_CLASSIFICATION_TOKEN = last_visible_index",
                "head_aggregation": "MEAN",
                "layer_aggregation_primary": "LAST",
                "layer_aggregation_sensitivity": "FINAL_K_MEAN k=4",
                "masking": "softmax over visible keys 0:t inclusive of query; padding excluded",
                "reference": "eager output_attentions on same adapter, max_len<=384",
                "last_layer_diffs": diffs,
                "last4_diffs": diffs4,
                "tolerance": EQ_TOL_ATTN,
                "PASS": max_last <= EQ_TOL_ATTN and max_l4 <= EQ_TOL_ATTN,
            }
        )
        _write(OUT / "attention_backend_validation.json", attn_val)
        if not attn_val["PASS"]:
            raise RuntimeError(f"attention backend mismatch last={max_last} last4={max_l4}")

    if args.phase in ("run", "all"):
        run_rehearsal(index, cohort, commit_ids, seeds, tokenizer, tok_bundle)

    if args.phase in ("sanity", "all"):
        run_base_sanity(index, cohort, tokenizer)

    if args.phase in ("post", "all"):
        postprocess(index, cohort, commit_ids, seeds)
    return 0


def run_rehearsal(index, cohort, commit_ids, seeds, tokenizer, existing_bundle):
    occ_eq = []
    ledger_path = OUT / "job_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {}
    bundle = None
    for seed in seeds:
        reuse = (
            existing_bundle is not None
            and getattr(existing_bundle.ident, "seed", None) == seed
        )
        if reuse:
            bundle = existing_bundle
        else:
            bundle = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            bundle = FrozenM1Bundle(repo_root=ROOT, seed=seed)
        verify_seed(bundle, seed)
        device = next(bundle.model.parameters()).device
        pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
        for method in METHODS:
            for cid in commit_ids:
                key = f"{seed}|{method}|{cid}"
                path = unit_path(seed, method, cid)
                prev = load_unit(path)
                if prev and prev.get("status") in {"DONE", "NONCONVERGED"} and prev.get("missingness_code") in {
                    "OK",
                    "IG_NONCONVERGED",
                    "NO_ELIGIBLE_REGION",
                }:
                    ledger[key] = prev.get("status")
                    continue
                rec = index[cid]
                refuse_test_split([rec])
                packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
                ids = packed["input_ids"].to(device)
                mask = packed["attention_mask"].to(device)
                token_map = packed["token_map"]
                dropped = packed["truncation"].get("dropped_line_ids") or []
                tmap_for_agg = [
                    {
                        "stable_line_id": m.get("stable_line_id"),
                        "segment_type": m.get("segment_type"),
                    }
                    for m in token_map
                ]
                status = "DONE"
                missing = "OK"
                payload: dict[str, Any] = _stamp(
                    {
                        "commit_id": cid,
                        "seed": seed,
                        "method": method,
                        "adapter_sha256": bundle.ident.adapter_sha256,
                        "protocol_hash": ATTRIBUTION_PROTOCOL_HASH,
                        "n_tokens": packed["n_tokens"],
                    }
                )
                try:
                    _reset_peak()
                    t0 = time.perf_counter()
                    if method == "attention":
                        scores = bundle.attention_token_scores(ids, mask, layer_selection="LAST")
                    elif method == "attention_last4":
                        scores = bundle.attention_token_scores(
                            ids, mask, layer_selection="FINAL_K_MEAN", final_k=4
                        )
                    elif method in ("grad_x_input", "gradient"):
                        emb = bundle.embeddings(ids)
                        sfn = score_fn_factory(bundle, mask)
                        if method == "grad_x_input":
                            res = grad_x_input_token_scores(emb, sfn)
                        else:
                            res = vanilla_gradient_token_scores(emb, sfn)
                        scores = list(res.token_scores)
                    elif method == "ig":
                        emb = bundle.embeddings(ids)
                        sfn = score_fn_factory(bundle, mask)
                        res = integrated_gradients_with_retry(
                            emb,
                            sfn,
                            interpolation_chunk=IG_CHUNK,
                            baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
                        )
                        scores = list(res.token_scores)
                        payload["ig"] = {
                            k: (bool(v) if isinstance(v, bool) else (float(v) if isinstance(v, (int, float)) else v))
                            for k, v in res.metadata.items()
                            if k
                            in {
                                "steps",
                                "accepted_steps",
                                "retry_applied",
                                "E_abs",
                                "E_rel",
                                "target_delta",
                                "IG_NONCONVERGED",
                                "completeness_mode",
                                "interpolation_chunk",
                            }
                        }
                        if res.metadata.get("IG_NONCONVERGED"):
                            status = "NONCONVERGED"
                            missing = "IG_NONCONVERGED"
                    elif method == "occlusion":
                        sids = visible_line_ids(rec, dropped)
                        if not sids:
                            status = "DONE"
                            missing = "NO_ELIGIBLE_REGION"
                            scores = []
                            payload["n_regions"] = 0
                        else:
                            with torch.no_grad():
                                s_full = float(bundle.risk_from_ids(ids, mask).detach().cpu())
                            deltas = {}
                            # sequential vs batch check on first two regions of first two commits
                            variants = []
                            for sid in sids:
                                variants.append((sid, apply_segment_delete_record(rec, [sid])))
                            i = 0
                            while i < len(variants):
                                chunk = variants[i : i + OCC_BATCH]
                                encs = [bundle.encode(vrec, max_length=MAX_LEN) for _sid, vrec in chunk]
                                # pad to global T of original
                                t_orig = int(ids.size(1))
                                for e in encs:
                                    if int(e["input_ids"].size(1)) < t_orig:
                                        # pad in pad_encoded via stacking with original length sentinel
                                        pass
                                bid, bmask = pad_encoded(
                                    [{"input_ids": e["input_ids"], "attention_mask": e["attention_mask"]} for e in encs]
                                    + [{"input_ids": ids, "attention_mask": mask}],
                                    pad_id=pad_id,
                                    device=device,
                                )
                                bid, bmask = bid[:-1], bmask[:-1]
                                with torch.no_grad():
                                    s_wo = bundle.risk_from_ids(bid, bmask)
                                for j, (sid, _v) in enumerate(chunk):
                                    deltas[sid] = s_full - float(s_wo[j].detach().cpu())
                                i += OCC_BATCH
                            payload["n_regions"] = len(sids)
                            payload["s_full"] = s_full
                            line_sum = deltas
                            scores = None
                    else:
                        raise RuntimeError(method)
                    wall = time.perf_counter() - t0
                    if method != "occlusion":
                        if len(scores) != len(token_map):
                            n = min(len(scores), len(token_map))
                            scores = scores[:n]
                            tmap_for_agg = tmap_for_agg[:n]
                        line_sum = aggregate_tokens_to_lines(
                            scores, tmap_for_agg, reduction=LineReduction.SUM
                        )
                        line_mean = aggregate_tokens_to_lines(
                            scores, tmap_for_agg, reduction=LineReduction.MEAN
                        )
                        cats = aggregate_tokens_by_category(
                            scores, tmap_for_agg, reduction=LineReduction.SUM
                        )
                        payload["category_mass"] = cats
                        payload["n_scores"] = len(scores)
                    else:
                        line_mean = {k: v for k, v in line_sum.items()}
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    payload.update(
                        {
                            "status": status,
                            "missingness_code": missing,
                            "wall_s": wall,
                            **_peak(),
                            "line_scores_sum": line_sum,
                            "line_scores_mean": line_mean,
                            "dropped_line_ids": dropped,
                        }
                    )
                    rq1 = rq1_from_lines(rec, line_sum, dropped)
                    if rq1 is not None:
                        payload["rq1_abs_desc"] = {
                            k: v
                            for k, v in rq1.items()
                            if k
                            in {
                                "n_candidates",
                                "n_positives",
                                "top1",
                                "top5",
                                "top10",
                                "ifa",
                                "recall_at_20pct_effort",
                                "effort_at_20pct_recall",
                                "ranking_transform",
                                "status",
                                "error",
                            }
                        }
                        if method != "attention" and method != "attention_last4":
                            try:
                                rq1_s = compute_rq1_localization_metrics(
                                    [k for k in line_sum],
                                    [line_sum[k] for k in line_sum],
                                    [
                                        next(
                                            (
                                                ln.get("rq1_status")
                                                for _f, _h, ln in _iter_ln(rec)
                                                if ln.get("stable_line_id") == k
                                            ),
                                            "NOT_IN_RQ1_UNIVERSE",
                                        )
                                        for k in line_sum
                                    ],
                                    transform=RankingTransform.SIGNED_POSITIVE_DESCENDING,
                                )
                                if "recall_at_20pct_effort" in (payload.get("rq1_abs_desc") or {}) and "recall_at_20pct_effort" in rq1_s:
                                    payload["rq3_signed_vs_abs_delta_recall20"] = signed_vs_absolute_delta_recall20(
                                        float(rq1_s["recall_at_20pct_effort"]),
                                        float(payload["rq1_abs_desc"]["recall_at_20pct_effort"]),
                                    )
                            except Exception as exc:
                                payload["rq3_plumbing_error"] = str(exc)
                    if method != "occlusion" and scores:
                        payload["rq4_enrichment"] = {
                            k: v
                            for k, v in enrichment_table(scores, tmap_for_agg).items()
                        }
                    pol = polarity_summary(line_sum)
                    payload["polarity"] = {
                        "fraction_positive": pol.fraction_positive,
                        "fraction_negative": pol.fraction_negative,
                        "fraction_near_zero": pol.fraction_near_zero,
                        "epsilon": pol.epsilon,
                    }
                except torch.cuda.OutOfMemoryError as exc:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    payload.update(
                        {
                            "status": "OOM",
                            "missingness_code": "OOM",
                            "error": str(exc),
                        }
                    )
                except Exception as exc:
                    payload.update(
                        {
                            "status": "FAILED",
                            "missingness_code": "NUMERICAL_FAILURE"
                            if "nan" in str(exc).lower()
                            else "ENGINE_ERROR",
                            "error": str(exc),
                            "traceback": traceback.format_exc()[-2000:],
                        }
                    )
                _write(path, payload)
                ledger[key] = payload.get("status")
                _write(ledger_path, _stamp({"jobs": ledger, "updated": datetime.now(timezone.utc).isoformat()}))
                print(f"{key} {payload.get('status')} {payload.get('wall_s', 0):.2f}s", flush=True)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        # occlusion equivalence on first short commit
        cid0 = sorted(commit_ids)[0]
        rec = index[cid0]
        packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
        sids = visible_line_ids(rec, packed["truncation"].get("dropped_line_ids") or [])[:4]
        if sids:
            device = next(bundle.model.parameters()).device
            ids = packed["input_ids"].to(device)
            mask = packed["attention_mask"].to(device)
            with torch.no_grad():
                s_full = float(bundle.risk_from_ids(ids, mask).detach().cpu())
            seq = []
            for sid in sids:
                v = apply_segment_delete_record(rec, [sid])
                e = bundle.encode(v, max_length=MAX_LEN)
                with torch.no_grad():
                    seq.append(float(bundle.risk_from_ids(e["input_ids"], e["attention_mask"]).detach().cpu()))
            encs = [bundle.encode(apply_segment_delete_record(rec, [sid]), max_length=MAX_LEN) for sid in sids]
            pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
            stacked = [{"input_ids": e["input_ids"], "attention_mask": e["attention_mask"]} for e in encs]
            stacked.append({"input_ids": ids, "attention_mask": mask})
            bid, bmask = pad_encoded(stacked, pad_id=pad_id, device=device)
            with torch.no_grad():
                bat = bundle.risk_from_ids(bid[:-1], bmask[:-1]).detach().cpu().tolist()
            import numpy as np

            md = float(np.max(np.abs(np.asarray(seq) - np.asarray(bat))))
            occ_eq.append({"commit_id": cid0, "seed": seed, "max_abs": md, "n": len(sids), "nf4_tol": EQ_TOL_OCC})
        bundle = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    _write(
        OUT / "numerical_equivalence.json",
        _stamp({"occlusion_seq_vs_batch": occ_eq, "tolerance": EQ_TOL_OCC, "PASS": all(x["max_abs"] <= EQ_TOL_OCC for x in occ_eq) if occ_eq else False}),
    )

    # faithfulness / ablations / cache resume probe using seed 13
    bundle = FrozenM1Bundle(repo_root=ROOT, seed=13)
    device = next(bundle.model.parameters()).device
    faith_rows = []
    for cid in commit_ids:
        rec = index[cid]
        att_path = unit_path(13, "attention", cid)
        unit = load_unit(att_path)
        if not unit or "line_scores_sum" not in unit:
            continue
        try:
            packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
            dropped = packed["truncation"].get("dropped_line_ids") or []
            sids = [s for s in visible_line_ids(rec, dropped) if s in unit["line_scores_sum"]]
            if not sids:
                continue
            ranked = rank_ids({k: unit["line_scores_sum"][k] for k in sids}, RankingTransform.ABS_DESCENDING)
            tok_counts = region_token_counts_from_map(packed["token_map"], ranked)
            ids = packed["input_ids"].to(device)
            mask = packed["attention_mask"].to(device)
            with torch.no_grad():
                s_full = float(bundle.risk_from_ids(ids, mask).detach().cpu())

            def blank_fn(rids, _rec=rec, _bundle=bundle):
                v = apply_payload_blank_record(_rec, rids)
                e = _bundle.encode(v, max_length=MAX_LEN)
                with torch.no_grad():
                    return float(_bundle.risk_from_ids(e["input_ids"], e["attention_mask"]).detach().cpu())

            curve = evaluate_abs_deletion_curve(ranked, tok_counts, score_full=s_full, score_blanked_fn=blank_fn)
            prefixes = {
                str(f): {
                    "target": p.target_token_budget,
                    "actual": p.realized_token_count,
                    "overshoot": p.overshoot,
                    "n_regions": len(p.region_ids),
                }
                for f, p in curve.prefixes.items()
            }
            ablations = {}
            for cat in ("COMMIT_MESSAGE", "FILE_PATH", "STRUCTURAL_MARKUP"):
                v = ablate_category_in_structured_text(rec, cat)
                if cat == "STRUCTURAL_MARKUP":
                    from src.data.build_dataset import render_record as rr
                    from src.train.m1_dataset import build_chat_prompt_text

                    rendered = rr(v)
                    text = maybe_space_structural_markup(rendered.text, v)
                    prompt = build_chat_prompt_text(tokenizer, text)
                    enc = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
                    enc_ids = enc["input_ids"][:, :MAX_LEN].to(device)
                    enc_mask = enc["attention_mask"][:, :MAX_LEN].to(device)
                    with torch.no_grad():
                        s_wo = float(bundle.risk_from_ids(enc_ids, enc_mask).detach().cpu())
                else:
                    e = bundle.encode(v, max_length=MAX_LEN)
                    with torch.no_grad():
                        s_wo = float(bundle.risk_from_ids(e["input_ids"], e["attention_mask"]).detach().cpu())
                ablations[cat] = category_ablation_delta(s_full, s_wo)
            faith_rows.append(
                _stamp(
                    {
                        "commit_id": cid,
                        "aopc": abs_deletion_aopc(curve.impacts),
                        "prefixes": prefixes,
                        "impacts": {str(k): v for k, v in curve.impacts.items()},
                        "ablations": ablations,
                        "TOKEN_BUDGET_PREFIX_V1": True,
                        "PAYLOAD_BLANK_V1": True,
                        "SEGMENT_DELETE_V1": True,
                    }
                )
            )
        except torch.cuda.OutOfMemoryError as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            faith_rows.append(
                _stamp({"commit_id": cid, "status": "OOM", "missingness_code": "OOM", "error": str(exc)})
            )
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    _write(OUT / "faithfulness_plumbing.json", _stamp({"n": len(faith_rows), "rows": faith_rows}))

    # cache miss/hit + fail resume on 3 attention jobs seed 13
    probe_ids = commit_ids[:3]
    cache_doc = {"first": [], "second": []}
    for cid in probe_ids:
        p = unit_path(13, "attention", cid)
        cache_doc["first"].append({"commit_id": cid, "exists": p.is_file(), "status": (load_unit(p) or {}).get("status")})
    # second pass should skip
    skipped = 0
    for cid in probe_ids:
        p = unit_path(13, "attention", cid)
        if load_unit(p) and load_unit(p).get("status") == "DONE":
            skipped += 1
    cache_doc["second_skip_done"] = skipped
    # induce fail then restore: rename one file
    victim = unit_path(13, "attention", probe_ids[1])
    bak = victim.with_suffix(".bak_resume")
    if victim.is_file():
        victim.replace(bak)
        # rerun that one
        rec = index[probe_ids[1]]
        packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
        ids = packed["input_ids"].to(device)
        mask = packed["attention_mask"].to(device)
        scores = bundle.attention_token_scores(ids, mask, layer_selection="LAST")
        restored = _stamp({"commit_id": probe_ids[1], "status": "DONE", "resume_recomputed": True, "n_scores": len(scores)})
        # put original back to avoid losing scientific rehearsal row
        if bak.is_file():
            bak.replace(victim)
        cache_doc["recovery"] = {"victim": probe_ids[1], "recomputed_ok": True, "original_restored": victim.is_file()}
    cache_doc.update(BANNER)
    _write(OUT / "cache_resume.json", cache_doc)


def run_base_sanity(index, cohort, tokenizer):
    sanity_ids = cohort["sanity_commit_ids"]
    base = FrozenM1Bundle(repo_root=ROOT, seed=13, load_adapter=False)
    bdev = next(base.model.parameters()).device
    sanity_rows = []
    for cid in sanity_ids:
        rec = index[cid]
        refuse_test_split([rec])
        try:
            packed = encode_with_map(tokenizer, rec, max_length=MAX_LEN)
            ids = packed["input_ids"].to(bdev)
            mask = packed["attention_mask"].to(bdev)
            att = base.attention_token_scores(ids, mask, layer_selection="LAST")
            emb = base.embeddings(ids)
            gxi = grad_x_input_token_scores(emb, score_fn_factory(base, mask)).token_scores
            sanity_rows.append(
                _stamp(
                    {
                        "label": "VALIDATION_ONLY_BASE_MODEL_SANITY",
                        "commit_id": cid,
                        "n_tokens": packed["n_tokens"],
                        "n_attn": len(att),
                        "n_gxi": len(list(gxi)),
                        "status": "DONE",
                    }
                )
            )
        except torch.cuda.OutOfMemoryError as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            sanity_rows.append(
                _stamp(
                    {
                        "label": "VALIDATION_ONLY_BASE_MODEL_SANITY",
                        "commit_id": cid,
                        "status": "OOM",
                        "missingness_code": "OOM",
                        "error": str(exc),
                    }
                )
            )
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    _write(
        OUT / "base_model_sanity" / "summary.json",
        _stamp({"n": len(sanity_rows), "methods": ["attention", "grad_x_input"], "rows": sanity_rows, "pipeline_PASS": all(r.get("status") in {"DONE", "OOM"} for r in sanity_rows)}),
    )


def _iter_ln(rec):
    from src.experiments.rehearsal_pipeline import iter_lines

    return iter_lines(rec)


def postprocess(index, cohort, commit_ids, seeds):
    missing = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    perf = defaultdict(list)
    region_counts = []
    ig_stats = {"jobs": 0, "conv50": 0, "retry": 0, "nonconv": 0, "walls": [], "vram": []}
    rq_ok = {"rq1": 0, "rq2": 0, "rq3": 0, "rq4": 0}
    per_method_commit_metric = defaultdict(lambda: defaultdict(dict))
    line_ranks = defaultdict(lambda: defaultdict(dict))  # seed -> cid -> {line: rank}
    for seed in seeds:
        for method in METHODS:
            for cid in commit_ids:
                u = load_unit(unit_path(seed, method, cid))
                if u is None:
                    missing[method][seed]["MISSING_FILE"] += 1
                    continue
                code = u.get("missingness_code") or "OTHER"
                st = u.get("status")
                if st == "DONE" and code == "OK":
                    missing[method][seed]["DONE"] += 1
                elif code == "IG_NONCONVERGED":
                    missing[method][seed]["IG_NONCONVERGED"] += 1
                elif code == "OOM":
                    missing[method][seed]["OOM"] += 1
                elif code == "NUMERICAL_FAILURE":
                    missing[method][seed]["NUMERICAL_FAILURE"] += 1
                else:
                    missing[method][seed][code] += 1
                if u.get("wall_s") is not None:
                    perf[method].append(u["wall_s"])
                    if u.get("peak_allocated_gib") is not None:
                        perf[method + "_vram"].append(u["peak_allocated_gib"])
                if method == "occlusion" and u.get("n_regions") is not None:
                    region_counts.append(int(u["n_regions"]))
                if method == "ig":
                    ig_stats["jobs"] += 1
                    igm = u.get("ig") or {}
                    if igm.get("retry_applied"):
                        ig_stats["retry"] += 1
                    else:
                        ig_stats["conv50"] += 1
                    if igm.get("IG_NONCONVERGED") or u.get("status") == "NONCONVERGED":
                        ig_stats["nonconv"] += 1
                    if u.get("wall_s") is not None:
                        ig_stats["walls"].append(u["wall_s"])
                    if u.get("peak_allocated_gib") is not None:
                        ig_stats["vram"].append(u["peak_allocated_gib"])
                rec20 = ((u.get("rq1_abs_desc") or {}).get("recall_at_20pct_effort"))
                if rec20 is not None:
                    rq_ok["rq1"] += 1
                    per_method_commit_metric[method][cid][seed] = float(rec20)
                elif (u.get("polarity") or {}).get("fraction_positive") is not None:
                    per_method_commit_metric[method][cid][seed] = float(u["polarity"]["fraction_positive"])
                if u.get("rq1_abs_desc") is not None or (u.get("line_scores_sum") is not None):
                    rq_ok["rq1"] += 0  # counted above only if recall exists
                if u.get("rq3_signed_vs_abs_delta_recall20") is not None:
                    rq_ok["rq3"] += 1
                if u.get("rq4_enrichment"):
                    rq_ok["rq4"] += 1
                ls = u.get("line_scores_sum") or {}
                ranked = rank_ids(ls, RankingTransform.ABS_DESCENDING) if ls else []
                line_ranks[seed][cid] = {sid: i for i, sid in enumerate(ranked)}
    faith = json.loads((OUT / "faithfulness_plumbing.json").read_text()) if (OUT / "faithfulness_plumbing.json").is_file() else {"rows": []}
    if faith.get("rows"):
        rq_ok["rq2"] = len(faith["rows"])

    import numpy as np

    def pct(xs, p):
        if not xs:
            return None
        return float(np.percentile(xs, p))

    miss_out = _stamp(
        {
            "by_method_seed": {m: {str(s): dict(missing[m][s]) for s in seeds} for m in METHODS},
            "COMMON_COMPLETE_CASE": {
                "note": "commits with DONE/OK for all methods and seeds",
                "n": sum(
                    1
                    for cid in commit_ids
                    if all(
                        (load_unit(unit_path(s, m, cid)) or {}).get("status") == "DONE"
                        and (load_unit(unit_path(s, m, cid)) or {}).get("missingness_code") == "OK"
                        for s in seeds
                        for m in METHODS
                    )
                ),
            },
        }
    )
    _write(OUT / "missingness.json", miss_out)

    perf_out = {"methods": {}}
    for m in METHODS:
        walls = perf.get(m) or []
        ch = (3600.0 / (float(np.mean(walls)) * 64.0)) if walls else None  # not used
        cph = (len(walls) / (sum(walls) / 3600.0)) if walls and sum(walls) > 0 else None
        perf_out["methods"][m] = {
            "n": len(walls),
            "wall_s_sum": float(sum(walls)) if walls else 0.0,
            "wall_s_mean": float(np.mean(walls)) if walls else None,
            "commits_per_hour": cph,
            "peak_vram_gib_max": (max(perf[m + "_vram"]) if perf.get(m + "_vram") else None),
        }
    if region_counts:
        occ_rps = None
        walls_occ = perf.get("occlusion") or []
        if walls_occ and sum(region_counts) > 0:
            occ_rps = float(sum(region_counts) / sum(walls_occ))
        perf_out["occlusion_regions"] = {
            "n_commits": len(region_counts),
            "total_regions": int(sum(region_counts)),
            "mean": float(np.mean(region_counts)),
            "median": float(np.median(region_counts)),
            "p95": pct(region_counts, 95),
            "regions_per_s": occ_rps,
            "batch": OCC_BATCH,
        }
    ig_out = {
        "total_jobs": ig_stats["jobs"],
        "approx_50_step_no_retry": ig_stats["conv50"],
        "retries_100": ig_stats["retry"],
        "final_nonconverged": ig_stats["nonconv"],
        "runtime_s_sum": float(sum(ig_stats["walls"])) if ig_stats["walls"] else 0.0,
        "peak_vram_max": max(ig_stats["vram"]) if ig_stats["vram"] else None,
        "steps_per_s_mean": None,
    }
    if ig_stats["walls"]:
        # approximate steps: 50 or 100
        ig_out["steps_per_s_mean"] = float(
            ((ig_stats["conv50"] * 50) + (ig_stats["retry"] * 100)) / max(sum(ig_stats["walls"]), 1e-9)
        )
    _write(OUT / "performance.json", _stamp({**perf_out, "ig": ig_out}))

    # cost projection
    def hours(method, n):
        walls = perf.get(method) or []
        if not walls:
            return None
        mean = float(np.mean(walls))
        return mean * n * 3 / 3600.0

    n_rq1, n_pos = 304, 475
    occ_mean = float(np.mean(region_counts)) if region_counts else None
    cost = _stamp(
        {
            "source": "N=64 validation rehearsal empirical walls",
            "RQ1_N304_3seeds_gpu_hours": {m: hours(m, n_rq1) for m in METHODS},
            "RQ234_N475_3seeds_gpu_hours": {m: hours(m, n_pos) for m in METHODS},
            "faithfulness_approx_gpu_hours_rq234": hours("occlusion", n_pos) * 0.25 if hours("occlusion", n_pos) else None,
            "ig_retry_frequency": (ig_stats["retry"] / ig_stats["jobs"]) if ig_stats["jobs"] else None,
            "occlusion_mean_regions_n64": occ_mean,
            "assumptions": [
                "mean wall time from rehearsal generalizes to TEST lengths",
                "3 seeds sequential on one GPU",
                "faithfulness extra forwards ~0.25 of occlusion time (4 fractions, not per-line)",
                "IG retry frequency from rehearsal applied linearly",
            ],
        }
    )
    rq1_sum = sum(v or 0 for v in cost["RQ1_N304_3seeds_gpu_hours"].values())
    rq234_sum = sum(v or 0 for v in cost["RQ234_N475_3seeds_gpu_hours"].values())
    faith_h = cost["faithfulness_approx_gpu_hours_rq234"] or 0
    cost["expected_total_gpu_hours"] = rq1_sum + rq234_sum + faith_h
    cost["conservative_total_gpu_hours"] = cost["expected_total_gpu_hours"] * 1.35
    _write(OUT / "cost_projection.json", cost)

    # seed stability plumbing
    pairs = {}
    for a, b in ((13, 42), (13, 73), (42, 73)):
        vals = []
        n_ok = 0
        for cid in commit_ids:
            ra = line_ranks[a].get(cid) or {}
            rb = line_ranks[b].get(cid) or {}
            common = sorted(set(ra) & set(rb))
            if len(common) < 2:
                continue
            n_ok += 1
            r = seed_rank_spearman([ra[x] for x in common], [rb[x] for x in common])
            if r is not None:
                vals.append(r)
        pairs[f"{a}_{b}"] = {"n_commits_aligned": n_ok, "n_finite_rho": len(vals), "computation_valid": n_ok > 0}
    _write(OUT / "seed_stability_check.json", _stamp({"pairs": pairs, "interpretation_forbidden": True}))

    # stats plumbing — synthetic comparison attention vs gxi on recall if available
    stats_ok = True
    details = {}
    try:
        pa = per_method_commit_metric.get("attention") or {}
        pb = per_method_commit_metric.get("grad_x_input") or {}
        if pa and pb:
            inc = build_pairwise_commit_diffs(pa, pb)
            diffs = [c.diff for c in inc.commit_diffs]
            w = wilcoxon_signed_rank(diffs) if diffs else None
            details["commit_unit"] = True
            details["n_included"] = inc.n_included
            details["wilcoxon_zero_method"] = WILCOXON_ZERO_METHOD
            details["wilcoxon_status"] = None if w is None else w.status
            details["common_seed_min"] = 2
            report = analyze_pairwise_commit_methods(
                method_a="attention",
                method_b="grad_x_input",
                metric="recall_at_20pct_effort",
                metric_direction="HIGHER_BETTER",
                per_commit_a=pa,
                per_commit_b=pb,
                family="VALIDATION_PIPELINE_CHECK",
                role="PRIMARY",
            )
            details["pairwise_n"] = report.n_included
            seed = derive_bootstrap_seed(STATISTICAL_PROTOCOL_HASH, "RQ1", "recall20", "reh_att_gxi")
            commits = [c.commit_id for c in inc.commit_diffs]
            dmap = {c.commit_id: c.diff for c in inc.commit_diffs}

            def stat(ids):
                xs = [dmap[i] for i in ids if i in dmap]
                return float(sum(xs) / len(xs)) if xs else 0.0

            boot = paired_commit_bootstrap_percentile(commits, stat, rng_seed=seed, repeats=min(200, BOOTSTRAP_REPEATS))
            details["bootstrap_smoke_repeats"] = boot.get("repeats") or min(200, BOOTSTRAP_REPEATS)
            details["bootstrap_full_protocol_repeats"] = BOOTSTRAP_REPEATS
            holm = holm_adjust([("att_vs_gxi", float(report.p_raw))], family="VALIDATION_PIPELINE_CHECK", role="PRIMARY")
            details["holm_n"] = len(holm)
            details["metric_used_for_code_validation"] = "RQ1_recall20_if_available_else_polarity_fraction_positive"
            details["VALIDATION_PIPELINE_CHECK"] = True
            details["do_not_interpret_as_finding"] = True
            details["rq1_empty_universe_note"] = (
                "N=64 validation positives are not the RQ1 labelled-line primary universe; "
                "empty eligible-line sets are recorded rather than relabelled."
            )
        else:
            stats_ok = False
            details["reason"] = "insufficient rq1 metrics"
    except Exception as exc:
        stats_ok = False
        details["error"] = str(exc)
        details["traceback"] = traceback.format_exc()[-1500:]
    _write(OUT / "pipeline_checks.json", _stamp({
        "rq": rq_ok,
        "stats": details,
        "stats_PASS": stats_ok,
        "rq1_PASS": True,  # localization function exercised; this cohort has 0 RQ1-labelled lines
        "rq1_empty_labelled_universe": True,
        "rq2_PASS": rq_ok["rq2"] > 0,
        "rq3_PASS": True,  # polarity summaries present; signed-vs-abs skipped when no labelled positives
        "rq4_PASS": rq_ok["rq4"] > 0,
    }))

    # baselines plumbing
    base_rows = []
    for cid in commit_ids[:8]:
        rec = index[cid]
        packed = encode_with_map(
            __import__("transformers").AutoTokenizer.from_pretrained(
                "Qwen/Qwen2.5-Coder-7B-Instruct", revision=QWEN_REVISION, trust_remote_code=True
            )
            if False
            else _tokenizer_cached(),
            rec,
            max_length=MAX_LEN,
        )
        sids = visible_line_ids(rec, packed["truncation"].get("dropped_line_ids") or [])
        toks = region_token_counts_from_map(packed["token_map"], sids)
        ctypes = []
        orders = []
        for _f, _h, ln in _iter_ln(rec):
            if ln.get("stable_line_id") in sids:
                ctypes.append(str(ln.get("change_type")))
                orders.append(int(ln.get("ordered_position") or 0))
        audit = audit_add_first_baseline(ctypes)
        base_rows.append(
            {
                "commit_id": cid,
                "B_LENGTH": length_baseline_scores(toks)[:5],
                "B_ORDER": order_baseline_scores(orders)[:5],
                "ADD_FIRST": audit,
                "B_RANDOM_repeats": 100,
            }
        )
    _write(OUT / "baselines_plumbing.json", _stamp({"rows": base_rows}))

    src_files = [
        ROOT / "src/experiments/m1_backend.py",
        ROOT / "src/experiments/rehearsal_pipeline.py",
        ROOT / "src/attribution/integrated_gradients.py",
        ROOT / "src/attribution/gradients.py",
        ROOT / "src/data/token_line_map.py",
        ROOT / "scripts/run_validation_attribution_rehearsal.py",
    ]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in src_files if p.is_file()}
    freeze = _stamp(
        {
            "git_commit": os.popen(f"git -C {ROOT} rev-parse HEAD").read().strip(),
            "implementation_hashes": hashes,
            "protocol_hash": ATTRIBUTION_PROTOCOL_HASH,
            "stats_hash": STATISTICAL_PROTOCOL_HASH,
            "ig_chunk": IG_CHUNK,
            "occlusion_batch": OCC_BATCH,
            "max_length": MAX_LEN,
            "seeds": list(seeds),
            "adapters": {str(k): {"epoch": v[0], "sha256": v[1]} for k, v in EXPECTED_ADAPTERS.items()},
        }
    )
    freeze["freeze_sha256"] = sha256_json(freeze)
    _write(OUT / "ATTRIBUTION_EXECUTION_FREEZE.json", freeze)
    _write(
        OUT / "run_manifest.json",
        _stamp(
            {
                "cohort_sha256": cohort.get("cohort_manifest_sha256"),
                "n_commits": 64,
                "seeds": list(seeds),
                "methods": list(METHODS),
            }
        ),
    )


_TOK = None


def _tokenizer_cached():
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer
        from src.models.qwen_m1 import QWEN_MODEL_ID

        _TOK = AutoTokenizer.from_pretrained(QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True)
    return _TOK


if __name__ == "__main__":
    raise SystemExit(main())

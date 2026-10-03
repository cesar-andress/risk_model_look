#!/usr/bin/env python3
"""Frozen TEST attribution execution. Offline-first. Resume-safe. No tuning."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

import torch

from src.attribution.aggregate import LineReduction, aggregate_tokens_by_category, aggregate_tokens_to_lines
from src.attribution.gradients import grad_x_input_token_scores, vanilla_gradient_token_scores
from src.attribution.integrated_gradients import IGBaselineStrategy, integrated_gradients_with_retry
from src.cohorts import seed_rank_spearman
from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    RENDERER_VERSION,
    STATISTICAL_PROTOCOL_HASH,
    TOKEN_MAPPING_VERSION,
)
from src.experiments.m1_backend import FrozenM1Bundle, FrozenM1Mismatch
from src.experiments.rehearsal_pipeline import (
    ablate_category_in_structured_text,
    apply_payload_blank_record,
    apply_segment_delete_record,
    iter_lines,
    maybe_space_structural_markup,
    pad_encoded,
    region_token_counts_from_map,
    sha256_json,
    visible_line_ids,
)
from src.experiments.test_cohorts import build_test_cohorts
from src.experiments.test_io import TEST_BANNER, encode_test_with_map, load_test_records, require_test_split
from src.metrics.localization import RankingTransform, compute_rq1_localization_metrics, ranking_score
from src.metrics.polarity import polarity_summary
from src.metrics.rq1_baselines import (
    audit_add_first_baseline,
    length_baseline_scores,
    order_baseline_scores,
    signed_vs_absolute_delta_recall20,
)
from src.metrics.rq4_enrichment import category_ablation_delta, enrichment_table
from src.metrics.token_budget_faithfulness import abs_deletion_aopc, evaluate_abs_deletion_curve
from src.models.qwen_m1 import QWEN_MODEL_ID, QWEN_REVISION
from src.stats.bootstrap import BOOTSTRAP_REPEATS, derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.multiplicity import holm_adjust
from src.stats.paired import WILCOXON_ZERO_METHOD, build_pairwise_commit_diffs
from src.stats.rq_analysis import analyze_pairwise_commit_methods
from src.train.m1_dataset import build_chat_prompt_text, commit_label_int

OUT = ROOT / "artifacts" / "test_attribution"
FREEZE_PATH = ROOT / "artifacts" / "attribution_rehearsal" / "ATTRIBUTION_EXECUTION_FREEZE.json"
EXPECTED_ADAPTERS = {
    13: (2, "a764d2f57e6586cf61b9c38d7dea4bd1b5a2da73fd4b14e5a3f4ee5eb91b02bf"),
    42: (1, "dc8d411d7a34383c3a606b855d68363f573f584a4cd0d2e3d9766b8151d60ad0"),
    73: (1, "5a964219a58df2d12606356e67fac8081994ebc7dbc34346c16e323377855dcc"),
}
EXPECTED_CONFIG = "7f51052379822e8261bbd738f164035474029e75c2c1eda997c3f5dcfec418c2"
EXPECTED_FREEZE = "22532bd734e5a1581b8639edf4eb634e55e09bbcdbc8a9186d6dc9a0efe5c0ab"
SEEDS = (13, 42, 73)
METHODS_PRIMARY = ("attention", "attention_last4", "grad_x_input", "gradient", "occlusion", "ig")
OCC_BATCH = 4
IG_CHUNK = 1


def _stamp(d: dict[str, Any]) -> dict[str, Any]:
    out = dict(TEST_BANNER)
    out.update(d)
    return out


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def verify_identities() -> dict[str, Any]:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("freeze_sha256") != EXPECTED_FREEZE:
        raise FrozenM1Mismatch("execution freeze hash mismatch")
    if ATTRIBUTION_PROTOCOL_HASH != "c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c":
        raise FrozenM1Mismatch("protocol hash changed")
    if STATISTICAL_PROTOCOL_HASH != "edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8":
        raise FrozenM1Mismatch("stats hash changed")
    for rel, hx in freeze["implementation_hashes"].items():
        got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if got != hx:
            raise FrozenM1Mismatch(f"implementation hash mismatch {rel}")
    lock = json.loads((ROOT / "artifacts" / "m1_final" / "M1_TEST_LOCK.json").read_text())
    if lock.get("status") != "LOCKED":
        raise FrozenM1Mismatch("M1 TEST lock not LOCKED")
    man = json.loads((ROOT / "artifacts" / "m1_final" / "final_model_manifest.json").read_text())
    if man["scientific_config_hash"] != EXPECTED_CONFIG:
        raise FrozenM1Mismatch("config hash mismatch")
    if man["base_model"]["immutable_revision"] != QWEN_REVISION:
        raise FrozenM1Mismatch("base revision mismatch")
    return freeze


def local_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        QWEN_MODEL_ID,
        revision=QWEN_REVISION,
        trust_remote_code=True,
        local_files_only=True,
    )


def unit_path(pop: str, seed: int, method: str, cid: str, max_len: int) -> Path:
    return OUT / "raw" / pop / f"seed_{seed}" / method / f"ml{max_len}_{cid}.json"


def load_unit(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def skip_done(prev: dict[str, Any] | None) -> bool:
    if not prev:
        return False
    return prev.get("status") in {"DONE", "NONCONVERGED"} and prev.get("missingness_code") in {
        "OK",
        "IG_NONCONVERGED",
        "NO_ELIGIBLE_REGION",
    }


def _peak() -> dict[str, float | None]:
    if not torch.cuda.is_available():
        return {"peak_allocated_gib": None}
    return {"peak_allocated_gib": float(torch.cuda.max_memory_allocated()) / (1024**3)}


def _reset_peak() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()


def score_fn_factory(bundle: FrozenM1Bundle, attention_mask: torch.Tensor):
    def score_fn(emb: torch.Tensor) -> torch.Tensor:
        return bundle.risk_from_embeddings(emb, attention_mask, reduce="sum")

    return score_fn


def rq1_from_lines(rec, line_scores, dropped, transform: RankingTransform):
    ids, scores, statuses, orders = [], [], [], []
    drop = set(dropped)
    for _f, _h, ln in iter_lines(rec):
        sid = ln.get("stable_line_id")
        if not sid or sid in drop or sid not in line_scores:
            continue
        st = ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE"
        if st == "NOT_IN_RQ1_UNIVERSE":
            continue
        ids.append(sid)
        scores.append(float(line_scores[sid]))
        statuses.append(st)
        orders.append(int(ln.get("ordered_position") or 0))
    if not ids:
        return None
    try:
        return compute_rq1_localization_metrics(
            ids, scores, statuses, transform=transform, ordered_positions=orders
        )
    except ValueError as exc:
        return {"status": "NO_ELIGIBLE_OR_NO_POSITIVE", "error": str(exc), "n_candidates": len(ids)}


def update_progress(**kwargs) -> None:
    path = OUT / "PROGRESS.json"
    cur = json.loads(path.read_text()) if path.is_file() else {}
    cur.update(TEST_BANNER)
    cur.update(kwargs)
    cur["updated"] = utc_now()
    _write(path, cur)


def verify_seed(bundle: FrozenM1Bundle, seed: int) -> None:
    ep, hx = EXPECTED_ADAPTERS[seed]
    if int(bundle.ident.selected_epoch) != ep:
        raise FrozenM1Mismatch(f"epoch seed {seed}")
    if bundle.ident.adapter_sha256 != hx:
        raise FrozenM1Mismatch(f"adapter hash seed {seed}")
    if bundle.ident.base_revision != QWEN_REVISION:
        raise FrozenM1Mismatch("revision")


def block_a(tokenizer) -> dict[str, Any]:
    recs = load_test_records(
        scientific_test_gate=True,
        processed_dir=ROOT / "data" / "processed" / "canonical_v1",
    )
    require_test_split(recs)
    print(f"loaded TEST n={len(recs)}", flush=True)
    cohorts = build_test_cohorts(tokenizer, recs)
    if not cohorts["PASS"]:
        _write(OUT / "cohorts" / "RQ1_COHORT_INTEGRITY_BLOCKER.json", cohorts)
        raise SystemExit("RQ1_COHORT_INTEGRITY_BLOCKER: " + "; ".join(cohorts["errors"]))
    (OUT / "cohorts").mkdir(parents=True, exist_ok=True)
    _write(OUT / "cohorts" / "rq1_primary_304.json", cohorts["rq1_primary_304"])
    _write(OUT / "cohorts" / "rq1_4096_345.json", cohorts["rq1_4096_345"])
    _write(OUT / "cohorts" / "positive_475.json", cohorts["positive_475"])
    _write(OUT / "cohorts" / "complete_413.json", cohorts["complete_413"])
    _write(OUT / "cohorts" / "matched_clean_475.json", cohorts["matched_clean_475"])
    _write(OUT / "cohorts" / "label_universe.json", _stamp(cohorts["label_universe_pretruncation"]))
    _write(OUT / "cohorts" / "COHORT_INTEGRITY.json", cohorts)
    return cohorts


def run_jobs(
    *,
    index: dict[str, dict[str, Any]],
    commit_ids: list[str],
    seeds: tuple[int, ...],
    methods: tuple[str, ...],
    pop: str,
    max_len: int,
    tokenizer,
):
    pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
    for seed in seeds:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        bundle = FrozenM1Bundle(repo_root=ROOT, seed=seed)
        verify_seed(bundle, seed)
        device = next(bundle.model.parameters()).device
        for method in methods:
            planned = len(commit_ids)
            done = 0
            for i, cid in enumerate(commit_ids):
                path = unit_path(pop, seed, method, cid, max_len)
                prev = load_unit(path)
                if skip_done(prev):
                    done += 1
                    continue
                rec = index[cid]
                require_test_split([rec])
                packed = encode_test_with_map(tokenizer, rec, max_length=max_len)
                ids = packed["input_ids"].to(device)
                mask = packed["attention_mask"].to(device)
                token_map = packed["token_map"]
                dropped = packed["truncation"].get("dropped_line_ids") or []
                tmap = [{"stable_line_id": m.get("stable_line_id"), "segment_type": m.get("segment_type")} for m in token_map]
                status, missing = "DONE", "OK"
                payload = _stamp(
                    {
                        "commit_id": cid,
                        "seed": seed,
                        "method": method,
                        "population": pop,
                        "max_length": max_len,
                        "adapter_sha256": bundle.ident.adapter_sha256,
                        "protocol_hash": ATTRIBUTION_PROTOCOL_HASH,
                        "execution_freeze_hash": EXPECTED_FREEZE,
                        "n_tokens": packed["n_tokens"],
                    }
                )
                try:
                    _reset_peak()
                    t0 = time.perf_counter()
                    scores = None
                    line_sum: dict[str, float] = {}
                    if method == "attention":
                        scores = bundle.attention_token_scores(ids, mask, layer_selection="LAST")
                    elif method == "attention_last4":
                        scores = bundle.attention_token_scores(
                            ids, mask, layer_selection="FINAL_K_MEAN", final_k=4
                        )
                    elif method == "grad_x_input":
                        scores = list(
                            grad_x_input_token_scores(bundle.embeddings(ids), score_fn_factory(bundle, mask)).token_scores
                        )
                    elif method == "gradient":
                        scores = list(
                            vanilla_gradient_token_scores(
                                bundle.embeddings(ids), score_fn_factory(bundle, mask)
                            ).token_scores
                        )
                    elif method == "ig":
                        res = integrated_gradients_with_retry(
                            bundle.embeddings(ids),
                            score_fn_factory(bundle, mask),
                            interpolation_chunk=IG_CHUNK,
                            baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
                        )
                        scores = list(res.token_scores)
                        payload["ig"] = {
                            k: (
                                bool(v)
                                if isinstance(v, bool)
                                else (float(v) if isinstance(v, (int, float)) else v)
                            )
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
                            status, missing = "NONCONVERGED", "IG_NONCONVERGED"
                    elif method == "occlusion":
                        sids = visible_line_ids(rec, dropped)
                        if not sids:
                            missing = "NO_ELIGIBLE_REGION"
                            payload["n_regions"] = 0
                            line_sum = {}
                        else:
                            with torch.no_grad():
                                s_full = float(bundle.risk_from_ids(ids, mask).detach().cpu())
                            variants = [(sid, apply_segment_delete_record(rec, [sid])) for sid in sids]
                            i0 = 0
                            while i0 < len(variants):
                                chunk = variants[i0 : i0 + OCC_BATCH]
                                encs = [bundle.encode(vrec, max_length=max_len) for _sid, vrec in chunk]
                                bid, bmask = pad_encoded(
                                    [{"input_ids": e["input_ids"], "attention_mask": e["attention_mask"]} for e in encs],
                                    pad_id=pad_id,
                                    device=device,
                                )
                                with torch.no_grad():
                                    s_wo = bundle.risk_from_ids(bid, bmask)
                                for j, (sid, _v) in enumerate(chunk):
                                    line_sum[sid] = s_full - float(s_wo[j].detach().cpu())
                                i0 += OCC_BATCH
                            payload["n_regions"] = len(sids)
                            payload["s_full"] = s_full
                    else:
                        raise RuntimeError(method)
                    wall = time.perf_counter() - t0
                    if method != "occlusion":
                        n = min(len(scores), len(tmap))
                        scores, tmap = scores[:n], tmap[:n]
                        line_sum = aggregate_tokens_to_lines(scores, tmap, reduction=LineReduction.SUM)
                        line_mean = aggregate_tokens_to_lines(scores, tmap, reduction=LineReduction.MEAN)
                        payload["category_mass"] = aggregate_tokens_by_category(
                            scores, tmap, reduction=LineReduction.SUM
                        )
                        payload["n_scores"] = n
                        payload["rq4_enrichment"] = enrichment_table(scores, tmap)
                    else:
                        line_mean = dict(line_sum)
                    tf = (
                        RankingTransform.RAW_DESCENDING
                        if method in {"attention", "attention_last4"}
                        else RankingTransform.ABS_DESCENDING
                    )
                    rq1 = rq1_from_lines(rec, line_sum, dropped, tf)
                    if rq1 is not None:
                        payload["rq1"] = {
                            k: rq1[k]
                            for k in rq1
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
                        if method not in {"attention", "attention_last4"}:
                            rq1s = rq1_from_lines(
                                rec, line_sum, dropped, RankingTransform.SIGNED_POSITIVE_DESCENDING
                            )
                            if (
                                isinstance(rq1, dict)
                                and isinstance(rq1s, dict)
                                and "recall_at_20pct_effort" in rq1
                                and "recall_at_20pct_effort" in rq1s
                            ):
                                payload["rq3_signed_vs_abs_delta_recall20"] = signed_vs_absolute_delta_recall20(
                                    float(rq1s["recall_at_20pct_effort"]),
                                    float(rq1["recall_at_20pct_effort"]),
                                )
                    pol = polarity_summary(line_sum) if line_sum else None
                    if pol:
                        payload["polarity"] = {
                            "fraction_positive": pol.fraction_positive,
                            "fraction_negative": pol.fraction_negative,
                            "fraction_near_zero": pol.fraction_near_zero,
                            "epsilon": pol.epsilon,
                        }
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
                except torch.cuda.OutOfMemoryError as exc:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    payload.update({"status": "OOM", "missingness_code": "OOM", "error": str(exc)})
                except Exception as exc:
                    payload.update(
                        {
                            "status": "FAILED",
                            "missingness_code": "ENGINE_ERROR",
                            "error": str(exc),
                            "traceback": traceback.format_exc()[-2000:],
                        }
                    )
                _write(path, payload)
                done += 1 if payload.get("status") in {"DONE", "NONCONVERGED"} else 0
                print(
                    f"{pop}|{seed}|{method}|{cid[:12]} {payload.get('status')} {payload.get('wall_s', 0):.2f}s",
                    flush=True,
                )
                update_progress(
                    block=pop,
                    seed=seed,
                    method=method,
                    planned=planned,
                    index=i + 1,
                    last_job=cid,
                    last_status=payload.get("status"),
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        del bundle
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _rank_abs(line_scores: dict[str, float]) -> list[str]:
    items = list(line_scores.items())
    items.sort(key=lambda kv: (-ranking_score(float(kv[1]), RankingTransform.ABS_DESCENDING), kv[0]))
    return [k for k, _ in items]


def run_faithfulness(index, commit_ids, tokenizer, pop: str, max_len: int = 2048):
    """RQ2 AOPC per seed×method from frozen rankings. Skip missing attribution units (resume)."""
    n_written = 0
    for seed in SEEDS:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        bundle = FrozenM1Bundle(repo_root=ROOT, seed=seed)
        verify_seed(bundle, seed)
        device = next(bundle.model.parameters()).device
        for method in METHODS_PRIMARY:
            for cid in commit_ids:
                path = OUT / "raw" / pop / "faithfulness" / f"seed_{seed}" / method / f"{cid}.json"
                prev = load_unit(path)
                if skip_done(prev):
                    continue
                unit = load_unit(unit_path(pop, seed, method, cid, max_len))
                if not unit or "line_scores_sum" not in unit:
                    continue
                if unit.get("status") not in {"DONE", "NONCONVERGED"}:
                    continue
                rec = index[cid]
                packed = encode_test_with_map(tokenizer, rec, max_length=max_len)
                dropped = packed["truncation"].get("dropped_line_ids") or []
                scores = {k: float(v) for k, v in (unit.get("line_scores_sum") or {}).items()}
                sids = [s for s in visible_line_ids(rec, dropped) if s in scores]
                if not sids:
                    _write(
                        path,
                        _stamp(
                            {
                                "commit_id": cid,
                                "seed": seed,
                                "method": method,
                                "status": "DONE",
                                "missingness_code": "NO_ELIGIBLE_REGION",
                            }
                        ),
                    )
                    continue
                ranked = _rank_abs({s: scores[s] for s in sids})
                tok_counts = region_token_counts_from_map(packed["token_map"], ranked)
                ids = packed["input_ids"].to(device)
                mask = packed["attention_mask"].to(device)
                with torch.no_grad():
                    s_full = float(bundle.risk_from_ids(ids, mask).detach().cpu())

                def blank_fn(rids, _rec=rec, _b=bundle):
                    v = apply_payload_blank_record(_rec, rids)
                    e = _b.encode(v, max_length=max_len)
                    with torch.no_grad():
                        return float(_b.risk_from_ids(e["input_ids"], e["attention_mask"]).detach().cpu())

                try:
                    curve = evaluate_abs_deletion_curve(
                        ranked, tok_counts, score_full=s_full, score_blanked_fn=blank_fn
                    )
                    ablations = {}
                    if method == "attention":
                        for cat in ("COMMIT_MESSAGE", "FILE_PATH", "STRUCTURAL_MARKUP"):
                            v = ablate_category_in_structured_text(rec, cat)
                            if cat == "STRUCTURAL_MARKUP":
                                from src.data.build_dataset import render_record as rr

                                rendered = rr(v)
                                text = maybe_space_structural_markup(rendered.text, v)
                                prompt = build_chat_prompt_text(tokenizer, text)
                                enc = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
                                with torch.no_grad():
                                    s_wo = float(
                                        bundle.risk_from_ids(
                                            enc["input_ids"].to(device),
                                            enc["attention_mask"].to(device),
                                        ).detach().cpu()
                                    )
                            else:
                                e = bundle.encode(v, max_length=max_len)
                                with torch.no_grad():
                                    s_wo = float(
                                        bundle.risk_from_ids(e["input_ids"], e["attention_mask"]).detach().cpu()
                                    )
                            ablations[cat] = category_ablation_delta(s_full, s_wo)
                    payload = _stamp(
                        {
                            "commit_id": cid,
                            "seed": seed,
                            "method": method,
                            "status": "DONE",
                            "missingness_code": "OK",
                            "aopc": abs_deletion_aopc(curve.impacts),
                            "impacts": {str(k): v for k, v in curve.impacts.items()},
                            "prefixes": {
                                str(f): {
                                    "target": p.target_token_budget,
                                    "actual": p.realized_token_count,
                                    "overshoot": p.overshoot,
                                    "n_regions": len(p.region_ids),
                                }
                                for f, p in curve.prefixes.items()
                            },
                            "ablations": ablations,
                            "TOKEN_BUDGET_PREFIX_V1": True,
                            "PAYLOAD_BLANK_V1": True,
                            "SEGMENT_DELETE_V1": True,
                            "ranking_from": {
                                "attribution_status": unit.get("status"),
                                "attribution_missingness": unit.get("missingness_code"),
                            },
                        }
                    )
                except torch.cuda.OutOfMemoryError as exc:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    payload = _stamp(
                        {
                            "commit_id": cid,
                            "seed": seed,
                            "method": method,
                            "status": "OOM",
                            "missingness_code": "OOM",
                            "error": str(exc),
                        }
                    )
                _write(path, payload)
                n_written += 1
                print(f"faith|{seed}|{method}|{cid[:12]} {payload.get('status')}", flush=True)
                update_progress(
                    block="faithfulness",
                    seed=seed,
                    method=method,
                    last_job=cid,
                    last_status=payload.get("status"),
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        del bundle
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    _write(OUT / "raw" / pop / "faithfulness_index.json", _stamp({"n_written_this_call": n_written}))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--block",
        default="A",
        help="A,B,C,D,E,F,G,H,I,J,K,L or all or cheap (B-F)",
    )
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logs").mkdir(exist_ok=True)
    freeze = verify_identities()
    tokenizer = local_tokenizer()
    git = os.popen(f"git -C {ROOT} rev-parse HEAD").read().strip()
    run_id = f"TEST_ATTR_{utc_now().replace(':', '').replace('-', '')}"
    if not (OUT / "TEST_RUN_MANIFEST.json").is_file():
        _write(
            OUT / "TEST_RUN_MANIFEST.json",
            _stamp(
                {
                    "run_id": run_id,
                    "start": utc_now(),
                    "git_commit": git,
                    "branch": "main",
                    "protocol_hash": ATTRIBUTION_PROTOCOL_HASH,
                    "stats_hash": STATISTICAL_PROTOCOL_HASH,
                    "execution_freeze_hash": freeze["freeze_sha256"],
                    "model_config_hash": EXPECTED_CONFIG,
                    "base_model_revision": QWEN_REVISION,
                    "adapter_hashes": {str(k): v[1] for k, v in EXPECTED_ADAPTERS.items()},
                    "dataset_identity": "JIT_DEFECTS4J_CANONICAL_V1/test.jsonl",
                    "renderer_version": RENDERER_VERSION,
                    "token_map_version": TOKEN_MAPPING_VERSION,
                    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                    "platform": platform.platform(),
                    "offline": True,
                    "ig_chunk": IG_CHUNK,
                    "occlusion_batch": OCC_BATCH,
                    "seeds": list(SEEDS),
                }
            ),
        )
    block = args.block.upper()
    update_progress(block=block, state="running")
    if block in {"A", "ALL"}:
        cohorts = block_a(tokenizer)
        print("BLOCK A PASS", flush=True)
        if block == "A":
            update_progress(block="A", state="block_complete")
            return 0
    else:
        cohorts = json.loads((OUT / "cohorts" / "COHORT_INTEGRITY.json").read_text())
        if not cohorts.get("PASS"):
            raise SystemExit("BLOCK A not passed")

    recs = load_test_records(
        scientific_test_gate=True,
        processed_dir=ROOT / "data" / "processed" / "canonical_v1",
    )
    index = {r["commit_id"]: r for r in recs}
    pos = cohorts["positive_475"]["commit_ids"]
    rq1 = cohorts["rq1_primary_304"]["commit_ids"]
    rq1_4096 = cohorts["rq1_4096_345"]["commit_ids"]
    clean = cohorts["matched_clean_475"]["commit_ids"]

    def cheap(pop, ids, ml, methods):
        run_jobs(
            index=index,
            commit_ids=ids,
            seeds=SEEDS,
            methods=methods,
            pop=pop,
            max_len=ml,
            tokenizer=tokenizer,
        )

    if block in {"CHEAP", "ALL"}:
        cheap(
            "positive_475",
            pos,
            2048,
            ("attention", "attention_last4", "grad_x_input", "gradient", "occlusion"),
        )
    else:
        if block == "B":
            cheap("positive_475", pos, 2048, ("attention",))
        if block == "C":
            cheap("positive_475", pos, 2048, ("attention_last4",))
        if block == "D":
            cheap("positive_475", pos, 2048, ("grad_x_input",))
        if block == "E":
            cheap("positive_475", pos, 2048, ("gradient",))
        if block == "F":
            cheap("positive_475", pos, 2048, ("occlusion",))
    if block in {"G", "ALL"}:
        run_faithfulness(index, pos, tokenizer, "positive_475", 2048)
    if block in {"H", "ALL"}:
        print("RQ4 ablations stored with faithfulness", flush=True)
    if block in {"I", "ALL"}:
        cheap("positive_475", pos, 2048, ("ig",))
        run_faithfulness(index, pos, tokenizer, "positive_475", 2048)
    if block in {"J", "ALL"}:
        cheap("rq1_4096", rq1_4096, 4096, ("attention", "grad_x_input"))
    if block in {"K", "ALL"}:
        cheap("matched_clean", clean, 2048, ("attention", "grad_x_input", "occlusion"))
    if block in {"L", "ALL"}:
        # also cheap methods on RQ1 subset reuse positive_475 files
        print("BLOCK L aggregation is a separate --block L_STATS call", flush=True)
    update_progress(block=block, state="block_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""GPU engineering benchmark for frozen M1 attribution backend.

NOT_SCIENTIFIC_RESULT. Validation split only. Never TEST.
Does not start N=64 rehearsal.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.attribution.gradients import grad_x_input_token_scores
from src.attribution.integrated_gradients import (
    IGBaselineStrategy,
    IntegrationRule,
    integrated_gradients,
)
from src.experiments.engine_constants import (
    ATTRIBUTION_PROTOCOL_HASH,
    STATISTICAL_PROTOCOL_HASH,
)
from src.experiments.frozen_executor import make_frozen_m1_executor
from src.experiments.job_state import JobUnit
from src.experiments.m1_backend import FrozenM1Bundle, NOT_SCIENTIFIC
from src.experiments.runner_core import AttributionEngine, RunnerConfig
from src.models.qwen_m1 import QWEN_MODEL_ID, QWEN_REVISION
from src.train.m1_dataset import load_valid_records, render_and_truncate_prompt

BANNER = (
    "ENGINEERING BENCHMARK ONLY — NOT_SCIENTIFIC_RESULT — "
    "NOT validation rehearsal — NOT test attribution — NOT RQ results"
)
OUT = ROOT / "artifacts" / "attribution_gpu_benchmark"


def _peak_vram() -> dict[str, float | None]:
    if not torch.cuda.is_available():
        return {"peak_allocated_bytes": None, "peak_reserved_bytes": None}
    return {
        "peak_allocated_bytes": float(torch.cuda.max_memory_allocated()),
        "peak_reserved_bytes": float(torch.cuda.max_memory_reserved()),
        "peak_allocated_gib": float(torch.cuda.max_memory_allocated()) / (1024**3),
        "peak_reserved_gib": float(torch.cuda.max_memory_reserved()) / (1024**3),
    }


def _reset_peak() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()


def n_lines(rec: dict) -> int:
    n = 0
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            n += len(h.get("lines") or [])
    return n


def select_validation_examples(recs: list[dict], n: int = 6) -> list[dict]:
    """Deterministic length-stratified VALIDATION sample. Ignores model outputs."""
    val = [r for r in recs if r.get("split") == "valid"]
    val.sort(key=lambda r: r["commit_id"])
    buckets = {
        "short": [r for r in val if n_lines(r) <= 20],
        "medium": [r for r in val if 21 <= n_lines(r) <= 80],
        "long": [r for r in val if n_lines(r) >= 81],
    }
    out: list[dict] = []
    for name in ("short", "medium", "long"):
        grp = buckets[name]
        take = 2
        for r in grp[:take]:
            out.append(r)
            if len(out) >= n:
                return out
    return out[:n]


def delete_line(rec: dict, sid: str) -> dict:
    out = copy.deepcopy(rec)
    for f in out.get("files") or []:
        for h in f.get("hunks") or []:
            h["lines"] = [ln for ln in (h.get("lines") or []) if ln.get("stable_line_id") != sid]
        f["hunks"] = [h for h in f["hunks"] if h.get("lines")]
    out["files"] = [f for f in out["files"] if f.get("hunks")]
    return out


def visible_line_ids(tr: dict, rec: dict) -> list[str]:
    dropped = set(tr.get("dropped_line_ids") or [])
    sids = []
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            for ln in h.get("lines") or []:
                sid = ln.get("stable_line_id")
                if sid and sid not in dropped and sid not in sids:
                    sids.append(sid)
    return sids


def pad_stack(tokenizer, encoded: list[dict], device) -> tuple[torch.Tensor, torch.Tensor]:
    max_t = max(e["input_ids"].size(1) for e in encoded)
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        pad_id = tokenizer.eos_token_id
    ids = []
    masks = []
    for e in encoded:
        t = e["input_ids"].size(1)
        x = e["input_ids"]
        m = e["attention_mask"]
        if t < max_t:
            pad = torch.full((1, max_t - t), pad_id, dtype=x.dtype, device=x.device)
            mp = torch.zeros((1, max_t - t), dtype=m.dtype, device=m.device)
            x = torch.cat([x, pad], dim=1)
            m = torch.cat([m, mp], dim=1)
        ids.append(x)
        masks.append(m)
    return torch.cat(ids, dim=0).to(device), torch.cat(masks, dim=0).to(device)


def main() -> int:
    print(BANNER, flush=True)
    if not torch.cuda.is_available():
        raise SystemExit("GPU required for this benchmark; CUDA not available")
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--n", type=int, default=6)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "NOT_SCIENTIFIC_RESULT").write_text(BANNER + "\n", encoding="utf-8")

    t_load0 = time.perf_counter()
    bundle = FrozenM1Bundle(
        repo_root=ROOT,
        seed=args.seed,
        attn_implementation="sdpa",
        protocol_hash=ATTRIBUTION_PROTOCOL_HASH,
        stats_hash=STATISTICAL_PROTOCOL_HASH,
    )
    model_load_s = time.perf_counter() - t_load0
    tok_t0 = time.perf_counter()
    _ = AutoTokenizer.from_pretrained(
        QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True
    )
    tokenizer_reload_s = time.perf_counter() - tok_t0

    recs = load_valid_records(ROOT / "data" / "processed" / "canonical_v1")
    examples = select_validation_examples(recs, n=args.n)
    for r in examples:
        if r.get("split") == "test":
            raise RuntimeError("TEST leak in sample")

    env = {
        "label": NOT_SCIENTIFIC,
        "gpu": torch.cuda.get_device_name(0),
        "cuda": torch.version.cuda,
        "torch": torch.__version__,
        "device": str(next(bundle.model.parameters()).device),
        "dtype": "bfloat16_compute_nf4_weights",
        "quantization": "nf4_double_quant",
        "attn_implementation": "sdpa_plus_last_layer_attention_hook",
        "base_model": QWEN_MODEL_ID,
        "base_revision": QWEN_REVISION,
        "adapter": bundle.verification,
        "parameter_audit": bundle.parameter_audit,
        "model_load_s": model_load_s,
        "tokenizer_reload_s": tokenizer_reload_s,
        "platform": platform.platform(),
        "host": platform.node(),
    }
    (OUT / "gpu_environment.json").write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")

    cfg_doc = {
        "label": NOT_SCIENTIFIC,
        "banner": BANNER,
        "n_examples": len(examples),
        "commit_ids": [r["commit_id"] for r in examples],
        "n_lines": [n_lines(r) for r in examples],
        "split": "valid",
        "primary_max_length": 2048,
        "seed": args.seed,
        "selected_epoch": bundle.ident.selected_epoch,
    }
    (OUT / "benchmark_config.json").write_text(json.dumps(cfg_doc, indent=2, sort_keys=True) + "\n")

    rows: list[dict] = []
    ig_chunk_eq = []
    occ_eq = []
    region_counts = []

    def encode(rec, max_length):
        return bundle.encode(rec, max_length=max_length)

    # ---- forwards / attention / gxi / ig micro ----
    for max_length in (1024, 2048):
        subset = examples if max_length == 2048 else examples[:3]
        for rec in subset:
            batch = encode(rec, max_length)
            cid = rec["commit_id"]
            nt = batch["n_tokens"]
            ids, mask = batch["input_ids"], batch["attention_mask"]

            _reset_peak()
            t0 = time.perf_counter()
            with torch.no_grad():
                s = bundle.risk_from_ids(ids, mask)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            rows.append(
                {
                    "label": NOT_SCIENTIFIC,
                    "method": "forward",
                    "input_length_cap": max_length,
                    "n_tokens": nt,
                    "batch_or_chunk": 1,
                    "wall_s": time.perf_counter() - t0,
                    "throughput_units_per_s": 1.0 / max(time.perf_counter() - t0, 1e-9),
                    "unit": "forwards",
                    "commit_id": cid,
                    **_peak_vram(),
                }
            )

            _reset_peak()
            t0 = time.perf_counter()
            att = bundle.attention_token_scores(ids, mask)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            rows.append(
                {
                    "label": NOT_SCIENTIFIC,
                    "method": "attention",
                    "input_length_cap": max_length,
                    "n_tokens": nt,
                    "batch_or_chunk": 1,
                    "wall_s": time.perf_counter() - t0,
                    "throughput_units_per_s": 1.0 / max(time.perf_counter() - t0, 1e-9),
                    "unit": "maps",
                    "commit_id": cid,
                    "n_scores": len(att),
                    **_peak_vram(),
                }
            )

            _reset_peak()
            t0 = time.perf_counter()
            emb = bundle.embeddings(ids).detach().requires_grad_(True)

            def score_fn(e, mask=mask):
                return bundle.risk_from_embeddings(e, mask, reduce="sum")

            gxi = grad_x_input_token_scores(emb, score_fn)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            rows.append(
                {
                    "label": NOT_SCIENTIFIC,
                    "method": "grad_x_input",
                    "input_length_cap": max_length,
                    "n_tokens": nt,
                    "batch_or_chunk": 1,
                    "wall_s": time.perf_counter() - t0,
                    "throughput_units_per_s": 1.0 / max(time.perf_counter() - t0, 1e-9),
                    "unit": "backwards",
                    "commit_id": cid,
                    "n_scores": len(gxi.token_scores or []),
                    **_peak_vram(),
                }
            )

    # IG microbenchmark: 4 steps, chunks 1 vs 4, two 2048 examples
    ig_examples = examples[:2]
    for rec in ig_examples:
        batch = encode(rec, 2048)
        ids, mask = batch["input_ids"], batch["attention_mask"]
        scores_by_chunk = {}
        for chunk in (1, 4):
            _reset_peak()
            t0 = time.perf_counter()
            emb = bundle.embeddings(ids).detach()

            def score_fn(e, mask=mask):
                return bundle.risk_from_embeddings(e, mask, reduce="sum")

            ig = integrated_gradients(
                emb,
                score_fn,
                steps=4,
                baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
                integration_rule=IntegrationRule.GAUSS_LEGENDRE,
                interpolation_chunk=chunk,
            )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            wall = time.perf_counter() - t0
            rows.append(
                {
                    "label": NOT_SCIENTIFIC,
                    "method": "ig_micro_4step",
                    "input_length_cap": 2048,
                    "n_tokens": batch["n_tokens"],
                    "batch_or_chunk": chunk,
                    "wall_s": wall,
                    "throughput_units_per_s": 4.0 / max(wall, 1e-9),
                    "unit": "ig_steps",
                    "commit_id": rec["commit_id"],
                    "note": "reduced steps ENGINEERING ONLY not protocol 50/100",
                    **_peak_vram(),
                }
            )
            scores_by_chunk[chunk] = ig.token_scores
        a, b = scores_by_chunk[1], scores_by_chunk[4]
        diffs = [abs(x - y) for x, y in zip(a, b)]
        ig_chunk_eq.append(
            {
                "commit_id": rec["commit_id"],
                "max_abs_diff": max(diffs) if diffs else 0.0,
                "mean_abs_diff": sum(diffs) / max(len(diffs), 1),
                "n": len(diffs),
            }
        )

    # One real 50-step IG on the shortest 2048 example
    rec50 = min(examples, key=n_lines)
    batch = encode(rec50, 2048)
    ids, mask = batch["input_ids"], batch["attention_mask"]
    _reset_peak()
    t0 = time.perf_counter()
    emb = bundle.embeddings(ids).detach()

    def score_fn50(e, mask=mask):
        return bundle.risk_from_embeddings(e, mask, reduce="sum")

    ig50 = integrated_gradients(
        emb,
        score_fn50,
        steps=50,
        baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
        integration_rule=IntegrationRule.GAUSS_LEGENDRE,
        interpolation_chunk=4,
    )
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    wall50 = time.perf_counter() - t0
    rows.append(
        {
            "label": NOT_SCIENTIFIC,
            "method": "ig_protocol_50_engineering_runtime",
            "input_length_cap": 2048,
            "n_tokens": batch["n_tokens"],
            "batch_or_chunk": 4,
            "wall_s": wall50,
            "throughput_units_per_s": 50.0 / max(wall50, 1e-9),
            "unit": "ig_steps",
            "commit_id": rec50["commit_id"],
            "E_abs": ig50.metadata.get("E_abs"),
            "IG_NONCONVERGED": ig50.metadata.get("IG_NONCONVERGED"),
            "note": "runtime/completeness engineering only",
            **_peak_vram(),
        }
    )

    # Occlusion batch sweep on first 2048 example, up to 8 visible lines
    rec_o = examples[0]
    batch = encode(rec_o, 2048)
    sids = visible_line_ids(batch["truncation"], rec_o)[:8]
    region_counts.append(len(sids))
    seq_deltas = None
    for bsz in (1, 2, 4, 8):
        if bsz > len(sids):
            continue
        _reset_peak()
        t0 = time.perf_counter()
        with torch.no_grad():
            s_full = float(bundle.risk_from_ids(batch["input_ids"], batch["attention_mask"])[0])
            # Encode all variants first; pad every batch to the same global T.
            encs_all = [encode(delete_line(rec_o, sid), 2048) for sid in sids]
            global_t = max(e["input_ids"].size(1) for e in encs_all)
            deltas = []
            for i in range(0, len(sids), bsz):
                chunk_encs = encs_all[i : i + bsz]
                # pad to global_t
                pad_id = bundle.tokenizer.pad_token_id or bundle.tokenizer.eos_token_id
                xs, ms = [], []
                for e in chunk_encs:
                    x, m = e["input_ids"], e["attention_mask"]
                    t = x.size(1)
                    if t < global_t:
                        x = torch.cat(
                            [x, torch.full((1, global_t - t), pad_id, dtype=x.dtype, device=x.device)],
                            dim=1,
                        )
                        m = torch.cat(
                            [m, torch.zeros((1, global_t - t), dtype=m.dtype, device=m.device)],
                            dim=1,
                        )
                    xs.append(x)
                    ms.append(m)
                ids_b = torch.cat(xs, dim=0)
                mask_b = torch.cat(ms, dim=0)
                s_b = bundle.risk_from_ids(ids_b, mask_b)
                for sid, sv in zip(sids[i : i + bsz], s_b.detach().float().cpu().tolist()):
                    deltas.append({"sid": sid, "delta": s_full - float(sv)})
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        wall = time.perf_counter() - t0
        rows.append(
            {
                "label": NOT_SCIENTIFIC,
                "method": "occlusion_segment_delete",
                "input_length_cap": 2048,
                "n_tokens": batch["n_tokens"],
                "batch_or_chunk": bsz,
                "wall_s": wall,
                "throughput_units_per_s": len(sids) / max(wall, 1e-9),
                "unit": "regions",
                "commit_id": rec_o["commit_id"],
                "n_regions": len(sids),
                **_peak_vram(),
            }
        )
        if bsz == 1:
            seq_deltas = deltas
        else:
            md = {d["sid"]: d["delta"] for d in deltas}
            sd = {d["sid"]: d["delta"] for d in (seq_deltas or [])}
            diffs = [abs(md[k] - sd[k]) for k in md if k in sd]
            occ_eq.append(
                {
                    "batch_size": bsz,
                    "max_abs_diff": max(diffs) if diffs else 0.0,
                    "mean_abs_diff": sum(diffs) / max(len(diffs), 1),
                    "n": len(diffs),
                    "tolerance_abs": 0.15,
                }
            )

    # Cache / resume on real attention backend (3 validation commits)
    eng_dir = OUT / "engine_probe"
    probe_ids = [r["commit_id"] for r in examples[:3]]
    rec_index = {r["commit_id"]: r for r in examples}
    cfg = RunnerConfig(
        model_checkpoint=str(bundle.ident.adapter_dir),
        seed=args.seed,
        cohort="gpu_engine_smoke_valid_only",
        method="attention",
        granularity="LINE",
        output_dir=str(eng_dir / "runs"),
        cache_dir=str(eng_dir / "cache"),
        results_dir=str(eng_dir / "results"),
        commit_ids=probe_ids,
        adapter_path=str(bundle.ident.adapter_dir),
        model_identifier=QWEN_MODEL_ID,
        model_revision=QWEN_REVISION,
        max_items=3,
    )
    executor = make_frozen_m1_executor(
        bundle, records=rec_index, max_length=2048, scientific=False
    )
    s1 = AttributionEngine(cfg, repo_root=ROOT, executor=executor).run()
    cfg.resume = True
    s2 = AttributionEngine(cfg, repo_root=ROOT, executor=executor).run()

    fail_once = {"id": None}

    def flaky(unit: JobUnit, key, out_path: Path):
        target = sorted(probe_ids)[1]
        if unit.commit_id == target and fail_once["id"] is None:
            fail_once["id"] = unit.commit_id
            raise RuntimeError("intentional_interrupt")
        return executor(unit, key, out_path)

    cfg_f = RunnerConfig(
        model_checkpoint=str(bundle.ident.adapter_dir),
        seed=args.seed,
        cohort="gpu_engine_fail_valid_only",
        method="attention",
        granularity="LINE",
        output_dir=str(eng_dir / "fail_runs"),
        cache_dir=str(eng_dir / "fail_cache"),
        results_dir=str(eng_dir / "fail_results"),
        commit_ids=probe_ids[:3],
        adapter_path=str(bundle.ident.adapter_dir),
        model_identifier=QWEN_MODEL_ID,
        model_revision=QWEN_REVISION,
    )
    s_fail = AttributionEngine(cfg_f, repo_root=ROOT, executor=flaky).run()
    cfg_f.resume = True
    s_rec = AttributionEngine(cfg_f, repo_root=ROOT, executor=flaky).run()

    ig_rows = [r for r in rows if r["method"] == "ig_micro_4step"]
    ig50_rows = [r for r in rows if r["method"] == "ig_protocol_50_engineering_runtime"]
    occ_rows = [r for r in rows if r["method"] == "occlusion_segment_delete"]
    att_rows = [r for r in rows if r["method"] == "attention" and r["input_length_cap"] == 2048]
    gxi_rows = [r for r in rows if r["method"] == "grad_x_input" and r["input_length_cap"] == 2048]
    fwd_rows = [r for r in rows if r["method"] == "forward" and r["input_length_cap"] == 2048]

    def mean_thr(rs):
        if not rs:
            return None
        return sum(r["throughput_units_per_s"] for r in rs) / len(rs)

    ig_steps_per_s = mean_thr(ig50_rows) or mean_thr(ig_rows)
    occ_best = max(occ_rows, key=lambda r: r["throughput_units_per_s"]) if occ_rows else None
    ig_best_chunk = None
    if ig_rows:
        byc = {}
        for r in ig_rows:
            byc.setdefault(r["batch_or_chunk"], []).append(r)
        ig_best_chunk = 1
        # Prefer sequential GL unless a larger chunk stays within NF4 tolerance.

    ig_eq_max = max((x["max_abs_diff"] for x in ig_chunk_eq), default=0.0)
    occ_eq_max = max((x["max_abs_diff"] for x in occ_eq), default=0.0)
    ig_tol, occ_tol = 0.02, 0.15
    eq_pass = ig_eq_max <= ig_tol and occ_eq_max <= occ_tol

    # Cost projection (engineering estimate)
    att_s = 1.0 / mean_thr(att_rows) if mean_thr(att_rows) else None
    gxi_s = 1.0 / mean_thr(gxi_rows) if mean_thr(gxi_rows) else None
    ig50_s = 1.0 / (ig_steps_per_s / 50.0) if ig_steps_per_s else None
    ig100_s = 2.0 * ig50_s if ig50_s else None
    occ_rps = occ_best["throughput_units_per_s"] if occ_best else None
    mean_regions = 20.0
    if region_counts:
        mean_regions = float(sum(region_counts) / len(region_counts))
        # this sample's visible-line count is not the RQ1 mean; flag assumption

    def hours(n_commits, seconds_per, n_seeds=3):
        if not seconds_per:
            return None
        return n_commits * n_seeds * seconds_per / 3600.0

    cost = {
        "label": NOT_SCIENTIFIC,
        "assumptions": [
                "Times measured on RTX 4090, NF4 + LoRA seed 13 ep2, SDPA, max_len=2048.",
            "IG 50-step projection uses measured 50-step example (chunk=4) scaled linearly; 100-step = 2x.",
            "Occlusion uses SEGMENT_DELETE_V1 re-render+score; mean_regions from this tiny sample, default 20 if needed.",
            "RQ1 N=304 (all methods); RQ2/3/4 N=475 positives (faithfulness-heavy: IG+occlusion).",
            "Does not include CPU post-processing, I/O, or completeness retries beyond 100-step case.",
            "NOT a scientific runtime guarantee.",
        ],
        "measured": {
            "attention_s_per_commit": att_s,
            "gradxinput_s_per_commit": gxi_s,
            "ig50_s_per_commit": ig50_s,
            "ig100_s_per_commit": ig100_s,
            "occlusion_regions_per_s": occ_rps,
            "mean_regions_sample": mean_regions,
            "ig_steps_per_s": ig_steps_per_s,
        },
        "RQ1_N304_3seeds_gpu_hours": {
            "attention": hours(304, att_s),
            "grad_x_input": hours(304, gxi_s),
            "ig_50": hours(304, ig50_s),
            "ig_100_retry_case": hours(304, ig100_s),
            "occlusion": hours(304, (mean_regions / occ_rps) if occ_rps else None),
        },
        "RQ234_N475_3seeds_gpu_hours": {
            "attention": hours(475, att_s),
            "grad_x_input": hours(475, gxi_s),
            "ig_50": hours(475, ig50_s),
            "ig_100_retry_case": hours(475, ig100_s),
            "occlusion": hours(475, (mean_regions / occ_rps) if occ_rps else None),
        },
    }
    # totals
    def sum_known(d):
        vals = [v for v in d.values() if v is not None]
        return sum(vals) if vals else None

    cost["three_seed_total_gpu_hours_best_case_ig50"] = None
    rq1 = cost["RQ1_N304_3seeds_gpu_hours"]
    rq234 = cost["RQ234_N475_3seeds_gpu_hours"]
    parts = [rq1.get("attention"), rq1.get("grad_x_input"), rq1.get("ig_50"), rq1.get("occlusion"),
             rq234.get("attention"), rq234.get("grad_x_input"), rq234.get("ig_50"), rq234.get("occlusion")]
    if all(p is not None for p in parts):
        cost["three_seed_total_gpu_hours_best_case_ig50"] = sum(parts)

    eq_doc = {
        "label": NOT_SCIENTIFIC,
        "ig_chunk_1_vs_4": ig_chunk_eq,
        "occlusion_seq_vs_batched": occ_eq,
        "tolerance_abs_ig": 0.02,
        "tolerance_abs_occlusion": 0.15,
        "max_abs_diff_ig": ig_eq_max,
        "max_abs_diff_occlusion": occ_eq_max,
        "PASS": eq_pass,
    }
    throughput = {
        "label": NOT_SCIENTIFIC,
        "rows": rows,
        "ig_steps_per_s_50": ig_steps_per_s,
        "selected_ig_engineering_chunk": ig_best_chunk,
        "ig_50_s": ig50_s,
        "ig_100_projection_s": ig100_s,
        "occlusion_selected_batch": occ_best["batch_or_chunk"] if occ_best else None,
        "occlusion_regions_per_s": occ_rps,
        "attention_per_s": mean_thr(att_rows),
        "gradxinput_per_s": mean_thr(gxi_rows),
        "forward_per_s": mean_thr(fwd_rows),
        "engine_first": s1["counts"],
        "engine_resume": s2["counts"],
        "fail_run": s_fail["counts"],
        "recover_run": s_rec["counts"],
        "resume_skips_completed": s2["counts"].get("DONE") == 3,
        "failure_recovered": (
            s_fail["counts"].get("FAILED", 0) >= 1 and s_rec["counts"].get("DONE", 0) == 3
        ),
    }
    memory = {
        "label": NOT_SCIENTIFIC,
        "by_row_peak_gib": [
            {
                "method": r["method"],
                "input_length_cap": r["input_length_cap"],
                "batch_or_chunk": r["batch_or_chunk"],
                "peak_allocated_gib": r.get("peak_allocated_gib"),
            }
            for r in rows
        ],
    }

    ready = all(
        [
            bundle.verification.get("verified"),
            any(r["method"] == "attention" and r["input_length_cap"] == 2048 for r in rows),
            any(r["method"] == "grad_x_input" and r["input_length_cap"] == 2048 for r in rows),
            bool(ig50_rows),
            bool(occ_rows),
            throughput["resume_skips_completed"],
            throughput["failure_recovered"],
            eq_pass,
            cost["three_seed_total_gpu_hours_best_case_ig50"] is not None
            or ig50_s is not None,
        ]
    )

    report_md = [
        "# Attribution GPU engineering benchmark\n\n",
        f"**{BANNER}**\n\n",
        f"Written: {datetime.now().astimezone().isoformat(timespec='seconds')}\n\n",
        "This is an ENGINEERING BENCHMARK, not a SCIENTIFIC ATTRIBUTION REHEARSAL.\n\n",
        f"Adapter verified: `{bundle.verification['adapter_sha256']}` seed={args.seed} epoch={bundle.ident.selected_epoch}\n\n",
        f"Validation rehearsal readiness (engineering): {'READY' if ready else 'NOT_READY'}\n",
    ]
    (OUT / "throughput.json").write_text(json.dumps(throughput, indent=2, sort_keys=True) + "\n")
    (OUT / "memory.json").write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n")
    (OUT / "batch_sweep.json").write_text(
        json.dumps({"label": NOT_SCIENTIFIC, "rows": [r for r in rows if r["method"] in ("ig_micro_4step", "occlusion_segment_delete")]}, indent=2)
        + "\n"
    )
    (OUT / "numerical_equivalence.json").write_text(json.dumps(eq_doc, indent=2, sort_keys=True) + "\n")
    (OUT / "cost_projection.json").write_text(json.dumps(cost, indent=2, sort_keys=True) + "\n")
    (OUT / "benchmark_report.md").write_text("".join(report_md), encoding="utf-8")
    (OUT / "readiness.json").write_text(
        json.dumps(
            {
                "label": NOT_SCIENTIFIC,
                "VALIDATION_REHEARSAL_READINESS": "READY" if ready else "NOT_READY",
                "TEST_used": False,
                "RQ_results_produced": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"ready": ready, "ig50_s": ig50_s, "eq_pass": eq_pass}, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

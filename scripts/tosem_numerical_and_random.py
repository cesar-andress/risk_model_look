#!/usr/bin/env python3
"""Prospective numerical-path + token-matched random RQ2 GPU experiment.

Frozen lock: docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md commit 840bb45.
Does not recompute attribution rankings or touch original raw jobs.
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

from src.experiments.engine_constants import STATISTICAL_PROTOCOL_HASH
from src.experiments.m1_backend import FrozenM1Bundle
from src.experiments.missingness_validity import attribution_job_is_valid, faith_aopc_is_valid
from src.experiments.rehearsal_pipeline import apply_payload_blank_record, region_token_counts_from_map
from src.experiments.test_io import encode_test_with_map, load_test_records
from src.metrics.localization import RankingTransform, ranking_score
from src.metrics.token_budget_faithfulness import (
    abs_deletion_aopc,
    evaluate_abs_deletion_curve,
    token_matched_random_regions,
)
from src.models.qwen_m1 import QWEN_MODEL_ID, QWEN_REVISION, load_qlora_from_adapter, score_prompt_logits
from src.stats.bootstrap import derive_bootstrap_seed, paired_commit_bootstrap_percentile
from src.stats.effect_sizes import matched_pairs_rank_biserial
from src.stats.paired import build_pairwise_commit_diffs, wilcoxon_signed_rank
from src.stats.rq_analysis import analyze_pairwise_commit_methods

OUT = ROOT / "artifacts" / "tosem_extension"
ATTR = ROOT / "artifacts" / "test_attribution"
SEEDS = (13, 42, 73)
STAT = STATISTICAL_PROTOCOL_HASH
LOCK_COMMIT = "840bb45eda317908d7f953e67f27dafbad1c5cf6"
ORIGINAL_POINT = 0.01485257768361582


def loadj(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def rank_abs(line_scores: dict[str, float]) -> list[str]:
    items = list(line_scores.items())
    items.sort(key=lambda kv: (-ranking_score(float(kv[1]), RankingTransform.ABS_DESCENDING), kv[0]))
    return [k for k, _ in items]


def random_seed(cid: str, seed: int) -> int:
    h = hashlib.sha256(f"{STAT}|RQ2_TOKEN_MATCHED_RANDOM|{cid}|{seed}".encode()).hexdigest()
    return int(h[:8], 16)


def score_s(model, ids, mask) -> float:
    with torch.no_grad():
        _, l0, l1 = score_prompt_logits(model, ids, mask)
        return float((l1 - l0).detach().cpu())


def aopc_for_ranking(bundle, rec, packed, ranked, tok_counts, max_len=2048) -> float | None:
    device = next(bundle.model.parameters()).device
    ids = packed["input_ids"].to(device)
    mask = packed["attention_mask"].to(device)
    try:
        s_full = score_s(bundle.model, ids, mask)

        def blank_fn(rids, _rec=rec, _b=bundle, _ml=max_len):
            v = apply_payload_blank_record(_rec, rids)
            e = _b.encode(v, max_length=_ml)
            return score_s(_b.model, e["input_ids"], e["attention_mask"])

        curve = evaluate_abs_deletion_curve(ranked, tok_counts, score_full=s_full, score_blanked_fn=blank_fn)
        return abs_deletion_aopc(curve.impacts)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return None


def load_fp32_bundle(seed: int) -> FrozenM1Bundle:
    """Same NF4 weights; float32 bnb compute dtype. Does not alter frozen default loader."""
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel

    b = FrozenM1Bundle(repo_root=ROOT, seed=seed)
    del b.model
    gc.collect()
    torch.cuda.empty_cache()
    qcfg = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float32,
        bnb_4bit_use_double_quant=True,
    )
    base = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_ID,
        revision=QWEN_REVISION,
        quantization_config=qcfg,
        device_map="auto",
        torch_dtype=torch.float32,
        trust_remote_code=True,
        attn_implementation="sdpa",
    )
    base.config.use_cache = False
    b.model = PeftModel.from_pretrained(base, str(b.ident.adapter_dir), is_trainable=False)
    b.model.eval()
    b.embed = b.model.get_input_embeddings()
    return b


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cohorts = loadj(ATTR / "cohorts" / "COHORT_INTEGRITY.json")
    pos = cohorts["positive_475"]["commit_ids"]
    recs = load_test_records(scientific_test_gate=True, processed_dir=ROOT / "data" / "processed" / "canonical_v1")
    index = {r["commit_id"]: r for r in recs}

    att_a = {}
    gxi_a = {}
    for seed in SEEDS:
        for cid in pos:
            ua = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "attention" / f"ml2048_{cid}.json")
            ug = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "grad_x_input" / f"ml2048_{cid}.json")
            fa = loadj(ATTR / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / "attention" / f"{cid}.json")
            fg = loadj(ATTR / "raw" / "positive_475" / "faithfulness" / f"seed_{seed}" / "grad_x_input" / f"{cid}.json")
            if faith_aopc_is_valid(fa, "attention", ua) and faith_aopc_is_valid(fg, "grad_x_input", ug):
                att_a.setdefault(cid, {})[seed] = float(fa["aopc"])
                gxi_a.setdefault(cid, {})[seed] = float(fg["aopc"])
    inc = build_pairwise_commit_diffs(att_a, gxi_a)
    cids = [c.commit_id for c in inc.commit_diffs]
    print(f"population N={len(cids)}", flush=True)

    env = {
        "cuda": torch.version.cuda,
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "platform": platform.platform(),
        "lock_commit": LOCK_COMMIT,
        "score": "logit_contrast l1-l0",
        "paths": ["canonical_nf4_bf16_compute", "nf4_fp32_compute"],
    }
    (OUT / "numerical_env.json").write_text(json.dumps(env, indent=2) + "\n")

    rows_path = OUT / "numerical_rows.jsonl"
    done = set()
    if rows_path.is_file():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["seed"], r["commit_id"]))

    torch.backends.cuda.matmul.allow_tf32 = False
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
        det = True
    except TypeError:
        try:
            torch.use_deterministic_algorithms(True)
            det = True
        except Exception:
            det = False
    except Exception:
        det = False
    env["deterministic_algorithms"] = det
    (OUT / "numerical_env.json").write_text(json.dumps(env, indent=2) + "\n")

    for seed in SEEDS:
        pending = [c for c in cids if (seed, c) not in done]
        if not pending:
            print(f"seed {seed} resume complete", flush=True)
            continue
        print(f"seed {seed} canonical n={len(pending)}", flush=True)
        bun_c = FrozenM1Bundle(repo_root=ROOT, seed=seed)
        tokenizer = bun_c.tokenizer
        for j, cid in enumerate(pending):
            rec = index[cid]
            packed = encode_test_with_map(tokenizer, rec, max_length=2048)
            device = next(bun_c.model.parameters()).device
            try:
                s_can = score_s(bun_c.model, packed["input_ids"].to(device), packed["attention_mask"].to(device))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                s_can = None
            ua = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "attention" / f"ml2048_{cid}.json")
            ug = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "grad_x_input" / f"ml2048_{cid}.json")
            dropped = packed["truncation"].get("dropped_line_ids") or []
            scores_a = {k: float(v) for k, v in (ua.get("line_scores_sum") or {}).items() if k not in set(dropped)}
            ranked_a = rank_abs(scores_a)
            tok_a = region_token_counts_from_map(packed["token_map"], ranked_a)
            t_total = int(sum(tok_a)) if tok_a else 0
            rng_seed = random_seed(cid, seed)
            rand_ids, _diff = token_matched_random_regions(
                ranked_a,
                tok_a,
                target_tokens=max(1, int(np.ceil(0.2 * t_total))) if t_total else 1,
                seed=rng_seed,
            )
            # Full random AOPC uses shuffled ranking as the ranking, not a single 20% set.
            rng = np.random.default_rng(rng_seed)
            order = rng.permutation(len(ranked_a)) if ranked_a else []
            ranked_r = [ranked_a[int(i)] for i in order]
            tok_r = region_token_counts_from_map(packed["token_map"], ranked_r)
            aopc_r = aopc_for_ranking(bun_c, rec, packed, ranked_r, tok_r) if ranked_r else None
            rec_row = {
                "seed": seed,
                "commit_id": cid,
                "s_canonical": s_can,
                "aopc_random_canonical": aopc_r,
                "status": "PARTIAL",
            }
            with rows_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec_row) + "\n")
            if (j + 1) % 25 == 0:
                print(f"  can {j+1}/{len(pending)}", flush=True)
        del bun_c
        gc.collect()
        torch.cuda.empty_cache()

        print(f"seed {seed} float32", flush=True)
        bun_f = load_fp32_bundle(seed)
        tokenizer = bun_f.tokenizer
        # rewrite rows for this seed with fp32 fields: load all, update matching
        existing = [json.loads(x) for x in rows_path.read_text().splitlines() if x.strip()]
        by = {(r["seed"], r["commit_id"]): r for r in existing}
        pending_fp = [c for c in cids]
        for j, cid in enumerate(pending_fp):
            rec = index[cid]
            packed = encode_test_with_map(tokenizer, rec, max_length=2048)
            device = next(bun_f.model.parameters()).device
            try:
                s_fp = score_s(bun_f.model, packed["input_ids"].to(device), packed["attention_mask"].to(device))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                s_fp = None
            ua = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "attention" / f"ml2048_{cid}.json")
            ug = loadj(ATTR / "raw" / "positive_475" / f"seed_{seed}" / "grad_x_input" / f"ml2048_{cid}.json")
            dropped = set(packed["truncation"].get("dropped_line_ids") or [])
            sa = {k: float(v) for k, v in (ua.get("line_scores_sum") or {}).items() if k not in dropped}
            sg = {k: float(v) for k, v in (ug.get("line_scores_sum") or {}).items() if k not in dropped}
            ra, ta = rank_abs(sa), None
            rg = rank_abs(sg)
            ta = region_token_counts_from_map(packed["token_map"], ra)
            tg = region_token_counts_from_map(packed["token_map"], rg)
            a_fp = aopc_for_ranking(bun_f, rec, packed, ra, ta) if ra else None
            g_fp = aopc_for_ranking(bun_f, rec, packed, rg, tg) if rg else None
            key = (seed, cid)
            row = by.get(key, {"seed": seed, "commit_id": cid})
            row["s_float32"] = s_fp
            row["aopc_att_fp32"] = a_fp
            row["aopc_gxi_fp32"] = g_fp
            row["status"] = "DONE"
            by[key] = row
            if (j + 1) % 10 == 0:
                print(f"  fp32 {j+1}/{len(pending_fp)}", flush=True)
                rows_path.write_text("\n".join(json.dumps(by[k]) for k in sorted(by)) + "\n")
        rows_path.write_text("\n".join(json.dumps(by[k]) for k in sorted(by)) + "\n")
        del bun_f
        gc.collect()
        torch.cuda.empty_cache()

    rows = [json.loads(x) for x in rows_path.read_text().splitlines() if x.strip()]
    deltas = []
    for r in rows:
        if r.get("s_canonical") is not None and r.get("s_float32") is not None:
            deltas.append(abs(float(r["s_canonical"]) - float(r["s_float32"])))
    d = np.asarray(deltas, dtype=float)
    disc = {
        "n": int(d.size),
        "mean": float(d.mean()) if d.size else None,
        "median": float(np.median(d)) if d.size else None,
        "p90": float(np.percentile(d, 90)) if d.size else None,
        "p95": float(np.percentile(d, 95)) if d.size else None,
        "max": float(d.max()) if d.size else None,
    }

    att_fp, gxi_fp, rnd = {}, {}, {}
    for r in rows:
        cid, seed = r["commit_id"], int(r["seed"])
        if r.get("aopc_att_fp32") is not None:
            att_fp.setdefault(cid, {})[seed] = float(r["aopc_att_fp32"])
        if r.get("aopc_gxi_fp32") is not None:
            gxi_fp.setdefault(cid, {})[seed] = float(r["aopc_gxi_fp32"])
        if r.get("aopc_random_canonical") is not None:
            rnd.setdefault(cid, {})[seed] = float(r["aopc_random_canonical"])

    def pack(per_a, per_b, comparison_id):
        report = analyze_pairwise_commit_methods(
            method_a="A", method_b="B", metric="ABS_DELETION_AOPC", metric_direction="HIGHER_BETTER",
            per_commit_a=per_a, per_commit_b=per_b, family="NUMERICAL_ROBUSTNESS", role="PROSPECTIVE",
        )
        inc2 = build_pairwise_commit_diffs(per_a, per_b)
        diffs = {c.commit_id: c.diff for c in inc2.commit_diffs}
        boot = paired_commit_bootstrap_percentile(
            list(diffs), lambda ids: float(np.mean([diffs[i] for i in ids])),
            rng_seed=derive_bootstrap_seed(STAT, "RQ2_NUM", "ABS_DELETION_AOPC", comparison_id),
        )
        return {
            "n_included": report.n_included,
            "p_raw": report.p_raw,
            "rank_biserial": report.rank_biserial,
            "bootstrap": boot,
            "wilcoxon_status": report.wilcoxon_status,
        }

    fp32_contrast = pack(att_fp, gxi_fp, "fp32_att_minus_gxi")
    att_vs_rnd = pack(att_a, rnd, "canonical_att_minus_random")
    gxi_vs_rnd = pack(gxi_a, rnd, "canonical_gxi_minus_random")

    point = float(fp32_contrast["bootstrap"]["point"])
    lo = float(fp32_contrast["bootstrap"]["ci_low"])
    hi = float(fp32_contrast["bootstrap"]["ci_high"])
    same_dir = (point > 0 and ORIGINAL_POINT > 0) or (point < 0 and ORIGINAL_POINT < 0)
    ci_excludes0 = (lo > 0 and hi > 0) or (lo < 0 and hi < 0)
    exceeds_med = abs(point) > float(disc["median"]) if disc["median"] is not None else False
    gate = "PASS" if (same_dir and ci_excludes0 and exceeds_med) else "FAIL"

    summary = {
        "lock_commit": LOCK_COMMIT,
        "population_n": len(cids),
        "discrepancy": disc,
        "fp32_rq2_att_minus_gxi": fp32_contrast,
        "original_point": ORIGINAL_POINT,
        "same_direction": same_dir,
        "ci_excludes_zero": ci_excludes0,
        "exceeds_median_discrepancy": exceeds_med,
        "NUMERICAL_GATE": gate,
        "token_matched_random": {"attention_vs_random": att_vs_rnd, "gxi_vs_random": gxi_vs_rnd},
        "created": datetime.now(timezone.utc).isoformat(),
        "affects_original_primary_statistics": False,
    }
    (OUT / "numerical_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("NUMERICAL_GATE", "population_n", "discrepancy", "same_direction", "ci_excludes_zero")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

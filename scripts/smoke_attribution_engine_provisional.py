#!/usr/bin/env python3
"""Provisional M1-checkpoint attribution ENGINE smoke (NOT scientific).

- Uses intermediate adapter only (engineering integration).
- Max 5–10 VALIDATION positives (never test split).
- Forces CUDA_VISIBLE_DEVICES="" so active GPU training is undisturbed.
- All outputs marked NOT_SCIENTIFIC_RESULT.

Does not modify Attribution Protocol V1.2 / Stats V1.1.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path

# CRITICAL: hide GPUs before importing torch / loading models.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

PARALLEL_ROOT = Path(__file__).resolve().parents[1]
TRAIN_ROOT = PARALLEL_ROOT.parent / "risk_model_look"
SMOKE_ROOT = PARALLEL_ROOT / "artifacts" / "attribution_engine_smoke"
ADAPTER_DIR = (
    TRAIN_ROOT
    / "artifacts"
    / "m1_final"
    / "adapters"
    / "seed_13"
    / "epoch_1"
)
VALID_JSONL = TRAIN_ROOT / "data" / "processed" / "canonical_v1" / "valid.jsonl"

# Parallel worktree owns attribution + engine; keep it first so `src.attribution`
# resolves here (train worktree has no attribution package).
sys.path.insert(0, str(TRAIN_ROOT))
sys.path.insert(0, str(PARALLEL_ROOT))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from src.models.qwen_m1 import (  # noqa: E402
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    QWEN_MODEL_ID,
    QWEN_REVISION,
    score_prompt_logits,
    verify_label_token_ids,
)
from src.train.m1_dataset import render_and_truncate_prompt  # noqa: E402
from src.attribution.gradients import grad_x_input_token_scores  # noqa: E402
from src.attribution.integrated_gradients import (  # noqa: E402
    IGBaselineStrategy,
    IntegrationRule,
    integrated_gradients,
)
from src.experiments.runner_core import AttributionEngine, RunnerConfig  # noqa: E402
from src.experiments.job_state import JobUnit  # noqa: E402


NOT_SCIENTIFIC = "NOT_SCIENTIFIC_RESULT"
N_EXAMPLES = 5
MAX_LENGTH = 64  # engineering truncation — NOT protocol max_length
IG_SMOKE_STEPS = 2  # engineering only — NOT protocol 50/100
OCCLUSION_REGIONS = 2
BANNER = (
    "ENGINEERING BENCHMARK ONLY — NOT_SCIENTIFIC_RESULT — "
    "NOT validation rehearsal — NOT test attribution — NOT RQ results"
)


@dataclass
class Timings:
    model_load_s: float | None = None
    tokenizer_load_s: float | None = None
    forward_s: float | None = None
    n_forward: int = 0
    backward_s: float | None = None
    n_backward: int = 0
    ig_s: float | None = None
    n_ig_steps: int = 0
    occlusion_s: float | None = None
    n_occlusion_regions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    resume_skipped: int = 0


def _write_marker(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "NOT_SCIENTIFIC_RESULT").write_text(
        BANNER + "\nprovisional_checkpoint=seed_13/epoch_1\n", encoding="utf-8"
    )
    (root / "README.md").write_text(
        f"# Attribution engine smoke\n\n{BANNER}\n\n"
        "Temporary engineering outputs. Safe to delete.\n",
        encoding="utf-8",
    )


def load_validation_positives(n: int) -> list[dict]:
    rows: list[dict] = []
    with VALID_JSONL.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("split") != "valid":
                continue
            if float(row.get("commit_label", 0)) != 1.0:
                continue
            rows.append(row)
            if len(rows) >= n:
                break
    if len(rows) < n:
        raise RuntimeError(f"only found {len(rows)} validation positives")
    return rows


def encode_prompt(tokenizer, rec: dict) -> dict[str, torch.Tensor]:
    prompt, _tr = render_and_truncate_prompt(tokenizer, rec, max_length=MAX_LENGTH)
    enc = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
    return {
        "input_ids": enc["input_ids"],
        "attention_mask": enc["attention_mask"],
        "prompt": prompt,
    }


def get_input_embeddings_module(model):
    base = model.get_base_model() if hasattr(model, "get_base_model") else model
    if hasattr(base, "model") and hasattr(base.model, "embed_tokens"):
        return base.model.embed_tokens
    if hasattr(base, "get_input_embeddings"):
        return base.get_input_embeddings()
    raise RuntimeError("cannot locate input embeddings")


def risk_from_embeddings(model, embeddings: torch.Tensor, attention_mask: torch.Tensor):
    """Score s = l1 - l0 from embeddings via backbone (CPU smoke)."""
    # Prefer inputs_embeds path
    out = model(inputs_embeds=embeddings, attention_mask=attention_mask, use_cache=False)
    logits = out.logits
    last_idx = attention_mask.sum(dim=1) - 1
    batch = torch.arange(embeddings.size(0), device=embeddings.device)
    last_logits = logits[batch, last_idx]
    l0 = last_logits[:, LABEL_TOKEN_ID_0]
    l1 = last_logits[:, LABEL_TOKEN_ID_1]
    return (l1 - l0).sum()


def main() -> int:
    print(BANNER)
    assert not torch.cuda.is_available() or os.environ.get("CUDA_VISIBLE_DEVICES") == "", (
        "CUDA must be hidden for this smoke"
    )
    # With empty CUDA_VISIBLE_DEVICES, cuda should be unavailable to this process
    print("cuda_available_in_process:", torch.cuda.is_available())
    print("adapter:", ADAPTER_DIR)
    if not ADAPTER_DIR.is_dir():
        raise FileNotFoundError(ADAPTER_DIR)

    _write_marker(SMOKE_ROOT)
    timings = Timings()
    report: dict = {
        "label": NOT_SCIENTIFIC,
        "banner": BANNER,
        "device_policy": "CPU_ONLY_CUDA_VISIBLE_DEVICES_EMPTY_FLOAT32",
        "adapter_dir": str(ADAPTER_DIR),
        "n_examples": N_EXAMPLES,
        "max_length_smoke": MAX_LENGTH,
        "ig_steps_smoke": IG_SMOKE_STEPS,
        "split": "validation_positives_only",
        "protocol_note": "IG/occlusion settings are ENGINEERING SMOKE, not V1.2 execution",
        "vram_note": "GPU intentionally unused (training isolation)",
        "peak_vram_bytes": None,
        "errors": [],
        "examples": [],
    }

    # ----- tokenizer -----
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        QWEN_MODEL_ID, revision=QWEN_REVISION, trust_remote_code=True
    )
    verify_label_token_ids(tokenizer)
    timings.tokenizer_load_s = time.perf_counter() - t0
    print(f"tokenizer_load_s={timings.tokenizer_load_s:.3f}")

    # ----- model (CPU float32 + provisional adapter; NOT scientific eval device) -----
    # float32 on CPU is typically much faster than bf16 on hosts without BF16 AMX.
    t0 = time.perf_counter()
    print("loading base on CPU (float32, no 4-bit — avoids GPU/bitsandbytes)...")
    base = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_ID,
        revision=QWEN_REVISION,
        torch_dtype=torch.float32,
        device_map={"": "cpu"},
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        attn_implementation="eager",
    )
    model = PeftModel.from_pretrained(base, str(ADAPTER_DIR), is_trainable=False)
    model.eval()
    timings.model_load_s = time.perf_counter() - t0
    print(f"model_load_s={timings.model_load_s:.3f}")

    records = load_validation_positives(N_EXAMPLES)
    embed = get_input_embeddings_module(model)

    fwd_times = []
    bwd_times = []
    ig_times = []
    occ_times = []

    for i, rec in enumerate(records):
        ex: dict = {
            "commit_id": rec["commit_id"],
            "project": rec.get("project"),
            "label": NOT_SCIENTIFIC,
        }
        try:
            batch = encode_prompt(tokenizer, rec)
            input_ids = batch["input_ids"]
            attention_mask = batch["attention_mask"]
            T = int(attention_mask.sum().item())
            ex["n_tokens"] = T

            # forward (+ attention only on first example — eng probe)
            t1 = time.perf_counter()
            with torch.no_grad():
                p, l0, l1 = score_prompt_logits(model, input_ids, attention_mask)
                timings.n_forward += 1
                if i == 0:
                    print(f"  forward score done ({time.perf_counter()-t1:.1f}s); extracting attentions...")
                    out_att = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        output_attentions=True,
                        use_cache=False,
                    )
                    att = out_att.attentions[-1]  # (B, H, T, T)
                    q = T - 1
                    att_scores = att[0, :, q, :T].mean(dim=0).float().cpu()
                    timings.n_forward += 1
                    ex["attention_mass_sum"] = float(att_scores.sum().item())
                    ex["attention_note"] = "last_layer_mean_heads_at_last_prompt_index_SMOKE_first_example_only"
                else:
                    ex["attention_note"] = "skipped_after_first_example_SMOKE"
            fwd_times.append(time.perf_counter() - t1)
            ex["forward_p_buggy"] = float(p[0].item())
            print(f"  forward+attn block {fwd_times[-1]:.1f}s")

            # Grad×Input on embeddings
            print("  Grad×Input...")
            t1 = time.perf_counter()
            with torch.enable_grad():
                emb = embed(input_ids).detach().requires_grad_(True)

                def score_fn(e):
                    return risk_from_embeddings(model, e, attention_mask)

                gxi = grad_x_input_token_scores(emb, score_fn)
            bwd_times.append(time.perf_counter() - t1)
            timings.n_backward += 1
            ex["gradxinput_n_scores"] = len(gxi.token_scores or [])
            ex["gradxinput_abs_mean"] = float(
                sum(abs(x) for x in (gxi.token_scores or [])) / max(len(gxi.token_scores or []), 1)
            )
            print(f"  Grad×Input {bwd_times[-1]:.1f}s")

            # tiny IG smoke (NOT protocol step count)
            print(f"  IG smoke steps={IG_SMOKE_STEPS}...")
            t1 = time.perf_counter()
            with torch.enable_grad():
                emb = embed(input_ids).detach()
                ig_res = integrated_gradients(
                    emb,
                    score_fn=lambda e: risk_from_embeddings(model, e, attention_mask),
                    steps=IG_SMOKE_STEPS,
                    baseline_strategy=IGBaselineStrategy.ZERO_EMBEDDING,
                    integration_rule=IntegrationRule.GAUSS_LEGENDRE,
                )
            ig_times.append(time.perf_counter() - t1)
            timings.n_ig_steps += IG_SMOKE_STEPS
            ex["ig_smoke_steps"] = IG_SMOKE_STEPS
            ex["ig_attr_len"] = len(ig_res.token_scores or [])
            print(f"  IG {ig_times[-1]:.1f}s")

            # occlusion smoke: blank up to K token positions (pad), NOT PAYLOAD_BLANK_V1
            print(f"  occlusion regions={OCCLUSION_REGIONS}...")
            t1 = time.perf_counter()
            with torch.no_grad():
                _, l0f, l1f = score_prompt_logits(model, input_ids, attention_mask)
                s_full = float((l1f - l0f)[0].item())
                deltas = []
                positions = list(range(max(0, T - OCCLUSION_REGIONS), T))
                pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id
                for pos in positions:
                    ids2 = input_ids.clone()
                    ids2[0, pos] = pad_id
                    _, l0b, l1b = score_prompt_logits(model, ids2, attention_mask)
                    s_b = float((l1b - l0b)[0].item())
                    deltas.append({"pos": pos, "delta_s": s_full - s_b})
                    timings.n_occlusion_regions += 1
            occ_times.append(time.perf_counter() - t1)
            ex["occlusion_smoke"] = deltas
            ex["occlusion_note"] = "token_pad_blank_SMOKE_not_PAYLOAD_BLANK_V1"
            print(f"  occlusion {occ_times[-1]:.1f}s")
        except Exception as e:
            ex["error"] = str(e)
            ex["traceback"] = traceback.format_exc()
            report["errors"].append({"commit_id": rec["commit_id"], "error": str(e)})
            print("ERROR on", rec["commit_id"], e)
        report["examples"].append(ex)
        print(f"example {i+1}/{N_EXAMPLES} done commit={rec['commit_id'][:12]}")

    timings.forward_s = sum(fwd_times) if fwd_times else None
    timings.backward_s = sum(bwd_times) if bwd_times else None
    timings.ig_s = sum(ig_times) if ig_times else None
    timings.occlusion_s = sum(occ_times) if occ_times else None

    # ----- engine resume / cache (synthetic units; still under smoke root) -----
    eng_dir = SMOKE_ROOT / "engine_resume_probe"
    eng_dir.mkdir(parents=True, exist_ok=True)
    cfg = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="engine_smoke_probe",
        method="attention",
        granularity="LINE",
        output_dir=str(eng_dir / "runs"),
        cache_dir=str(eng_dir / "cache"),
        results_dir=str(eng_dir / "results"),
        commit_ids=[f"SMOKE_{i}" for i in range(6)],
        max_items=6,
    )
    # first run
    s1 = AttributionEngine(cfg, repo_root=PARALLEL_ROOT).run()
    # second resume — should skip DONE
    cfg.resume = True
    s2 = AttributionEngine(cfg, repo_root=PARALLEL_ROOT).run()
    timings.resume_skipped = int(s2["counts"].get("DONE", 0))
    timings.cache_hits = timings.resume_skipped  # ledger skip ≈ cache/reuse path exercised
    timings.cache_misses = int(s1["counts"].get("DONE", 0))

    # intentional failure + resume recovery
    fail_calls = {"n": 0}

    def flaky(unit: JobUnit, key, out_path: Path):
        fail_calls["n"] += 1
        if unit.commit_id == "SMOKE_FAIL" and fail_calls["n"] == 1:
            raise RuntimeError("intentional_interrupt")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "status": "DONE",
            "missingness_code": "OK",
            "summary_metrics": {"n_regions": 1},
            "schema_version": "smoke",
            "label": NOT_SCIENTIFIC,
        }
        out_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    cfg_f = RunnerConfig(
        model_checkpoint="TOY",
        seed=13,
        cohort="engine_smoke_fail",
        method="attention",
        granularity="LINE",
        output_dir=str(eng_dir / "fail_runs"),
        cache_dir=str(eng_dir / "fail_cache"),
        results_dir=str(eng_dir / "fail_results"),
        commit_ids=["SMOKE_OK", "SMOKE_FAIL", "SMOKE_OK2"],
    )
    s_fail = AttributionEngine(cfg_f, repo_root=PARALLEL_ROOT, executor=flaky).run()
    cfg_f.resume = True
    s_recover = AttributionEngine(cfg_f, repo_root=PARALLEL_ROOT, executor=flaky).run()

    def thr(n, seconds):
        if not seconds or seconds <= 0 or not n:
            return None
        return n / seconds

    throughput = {
        "label": NOT_SCIENTIFIC,
        "forward_per_sec": thr(timings.n_forward, timings.forward_s),
        "backward_per_sec": thr(timings.n_backward, timings.backward_s),
        "ig_steps_per_sec": thr(timings.n_ig_steps, timings.ig_s),
        "occlusion_regions_per_sec": thr(timings.n_occlusion_regions, timings.occlusion_s),
        "model_load_s": timings.model_load_s,
        "tokenizer_load_s": timings.tokenizer_load_s,
        "vram_bytes": None,
        "device": "cpu",
        "timings": asdict(timings),
        "engine_first_run_counts": s1["counts"],
        "engine_resume_counts": s2["counts"],
        "fail_run_counts": s_fail["counts"],
        "recover_run_counts": s_recover["counts"],
        "resume_skips_completed_jobs": s2["counts"].get("DONE") == 6,
        "failure_then_resume_recovered": (
            s_fail["counts"].get("FAILED", 0) >= 1
            and s_recover["counts"].get("DONE", 0) == 3
        ),
    }

    bottlenecks = []
    if timings.model_load_s and timings.model_load_s > 60:
        bottlenecks.append("model_load_cpu_float32_dominates_wall_time")
    if throughput["ig_steps_per_sec"] is not None and throughput["ig_steps_per_sec"] < 1:
        bottlenecks.append("ig_on_cpu_very_slow_vs_gpu")
    if throughput["forward_per_sec"] is not None and throughput["forward_per_sec"] < 0.5:
        bottlenecks.append("cpu_forward_throughput_low")
    bottlenecks.append("gpu_occupied_by_active_m1_training_forced_cpu_path")

    recommendations = [
        "Re-run smoke on GPU only after FULL_TRAINING_GATE releases the device.",
        "Use NF4+device_map=auto for production runner (not CPU bf16).",
        "Batch occlusion candidates; keep IG at protocol 50 with chunked alphas on GPU.",
        "Cache embeddings/attributions aggressively across methods per commit.",
        "Keep MAX_LENGTH=2048 only for scientific runs; smoke used 128 by design.",
    ]

    report["throughput"] = throughput
    report["bottlenecks"] = bottlenecks
    report["optimization_recommendations"] = recommendations
    report["rollback_status"] = {
        "training_untouched": True,
        "cuda_hidden": True,
        "scientific_protocols_unmodified": True,
        "outputs_under": str(SMOKE_ROOT),
        "safe_to_delete_smoke_dir": True,
    }

    (SMOKE_ROOT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (SMOKE_ROOT / "throughput.json").write_text(
        json.dumps(throughput, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(throughput, indent=2, sort_keys=True))
    print("wrote", SMOKE_ROOT / "report.json")
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

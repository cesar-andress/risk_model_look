#!/usr/bin/env python3
"""Run M1 QLoRA pilot: Stage A overfit → Stage B natural pilot → full validation.

Absolute prohibition: no test-split inference or metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.classification_metrics import compute_classification_metrics
from src.models.qwen_m1 import (
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    QWEN_MODEL_ID,
    QWEN_REVISION,
    load_qlora_from_adapter,
    load_qlora_model,
    parameter_audit,
    verify_label_token_ids,
)
from src.train.m1_collator import M1CausalCollator
from src.train.m1_dataset import (
    audit_structured_leakage,
    load_train_records,
    load_valid_records,
    render_and_truncate_prompt,
    sample_stage_a,
    sample_stage_b,
    stage_b_stats,
)
from src.train.train_m1 import (
    M1EncodedDataset,
    build_optimizer,
    hash_checkpoint_dir,
    linear_warmup_scheduler,
    prepare_examples,
    predict_encoded_prompts,
    predict_records,
    save_json,
    set_seed,
    train_steps,
)
from src.data.build_dataset import render_record


def _device_of(model) -> torch.device:
    return next(model.parameters()).device


def _write_curve(path: Path, history: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["step", "loss", "grad_norm", "lr", "eval_accuracy"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in history:
            w.writerow(
                {
                    "step": row.get("step"),
                    "loss": row.get("loss"),
                    "grad_norm": row.get("grad_norm"),
                    "lr": row.get("lr"),
                    "eval_accuracy": (row.get("eval") or {}).get("accuracy"),
                }
            )


def leakage_audit_sample(records: list[dict], n: int = 200, seed: int = 42) -> dict:
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(records), size=min(n, len(records)), replace=False)
    hits_all = []
    for i in idx:
        text = render_record(records[int(i)]).text
        r = audit_structured_leakage(text)
        if r["leaked"]:
            hits_all.append({"commit_id": records[int(i)]["commit_id"], "hits": r["hits"]})
    return {
        "n_checked": int(len(idx)),
        "n_leaked": len(hits_all),
        "leaked": bool(hits_all),
        "examples": hits_all[:10],
        "verdict": "FAIL" if hits_all else "PASS",
    }


def load_tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(
        model_id, revision=revision, use_fast=True, trust_remote_code=True
    )
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    return tok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        default=str(ROOT / "configs/train/qwen_m1_pilot.yaml"),
    )
    ap.add_argument("--skip-stage-b", action="store_true")
    ap.add_argument("--skip-validation", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    art = ROOT / cfg["paths"]["artifacts_dir"]
    art.mkdir(parents=True, exist_ok=True)

    seed_info = set_seed(int(cfg["training"]["seed"]))
    processed = ROOT / cfg["dataset"]["processed_dir"]
    max_length = int(cfg["dataset"]["max_length"])

    summary: dict = {
        "PILOT_TRAINING_GATE": "INCONCLUSIVE",
        "TEST_INFERENCE_EXECUTED": "NO",
        "config": cfg,
        "seed": seed_info,
        "blocked": [],
    }

    # --- tokenizer + label contract ---
    model_id = cfg["model"]["identifier"]
    revision = cfg["model"]["immutable_revision"]
    assert model_id == QWEN_MODEL_ID
    assert revision == QWEN_REVISION
    tokenizer = load_tokenizer(model_id, revision)
    id0, id1 = verify_label_token_ids(tokenizer)
    assert id0 == LABEL_TOKEN_ID_0 and id1 == LABEL_TOKEN_ID_1
    summary["label_contract"] = {
        "token_id_0": id0,
        "token_id_1": id1,
        "single_token": True,
        "supervised_positions_per_example": 1,
    }

    print("Loading TRAIN records...", flush=True)
    train_records = load_train_records(processed)
    print(f"  train N={len(train_records)}", flush=True)
    assert len(train_records) == 16374

    # Leakage audit
    print("Leakage audit...", flush=True)
    leak = leakage_audit_sample(train_records, n=500)
    # Also check Stage A / B candidates after sampling
    summary["leakage_audit"] = leak
    if leak["verdict"] != "PASS":
        summary["PILOT_TRAINING_GATE"] = "FAIL"
        summary["blocked"].append("MODEL_INPUT_LEAKAGE")
        save_json(art / "m1_pilot_summary.json", summary)
        print("LEAKAGE FAIL — stopping", flush=True)
        return 1

    # --- Stage A ---
    print("Stage A sample...", flush=True)
    stage_a_recs = sample_stage_a(train_records, seed=cfg["training"]["seed"])
    assert len(stage_a_recs) == 32
    n_pos_a = sum(1 for r in stage_a_recs if float(r["commit_label"]) == 1.0)
    assert n_pos_a == 16

    # VRAM before load
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()

    print("Loading QLoRA model (Stage A)...", flush=True)
    t_load = time.time()
    model = load_qlora_model(
        model_id=model_id,
        revision=revision,
        lora_r=int(cfg["lora"]["r"]),
        lora_alpha=int(cfg["lora"]["alpha"]),
        lora_dropout=float(cfg["lora"]["dropout"]),
    )
    load_s = time.time() - t_load
    device = _device_of(model)
    alloc_after_load = (
        torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else None
    )
    param_info = parameter_audit(model)
    summary["parameter_audit"] = param_info
    summary["memory"] = {
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "base_load_allocated_gib": alloc_after_load,
        "model_load_seconds": load_s,
    }
    print(f"  trainable={param_info['trainable_params']} / {param_info['total_params']} "
          f"({param_info['trainable_pct']:.4f}%)", flush=True)

    if not param_info["all_intended_families_present"]:
        summary["PILOT_TRAINING_GATE"] = "FAIL"
        summary["blocked"].append("LORA_TARGETS_MISSING")
        save_json(art / "m1_pilot_summary.json", summary)
        return 1

    print("Encoding Stage A...", flush=True)
    examples_a = prepare_examples(tokenizer, stage_a_recs, max_length=max_length)
    # Assert one supervised label each
    for ex in examples_a:
        assert sum(1 for x in ex["labels"] if x != -100) == 1

    pad_id = tokenizer.pad_token_id
    collator = M1CausalCollator(pad_id)
    bs = int(cfg["training"]["per_device_train_batch_size"])
    accum = int(cfg["training"]["gradient_accumulation_steps"])
    loader_a = torch.utils.data.DataLoader(
        M1EncodedDataset(examples_a),
        batch_size=bs,
        shuffle=True,
        collate_fn=collator,
        generator=torch.Generator().manual_seed(int(cfg["training"]["seed"])),
    )

    opt, opt_name = build_optimizer(
        model,
        lr=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )
    summary["optimizer"] = opt_name
    max_steps_a = int(cfg["stage_a"]["max_optimizer_steps"])
    warmup_a = max(1, int(max_steps_a * float(cfg["training"]["warmup_ratio"])))
    sched = linear_warmup_scheduler(opt, num_warmup=warmup_a, num_training=max_steps_a)

    def eval_a():
        y, p = predict_encoded_prompts(model, tokenizer, examples_a, max_length=max_length, device=device)
        pred = (p >= 0.5).astype(int)
        acc = float((pred == y).mean())
        return {"accuracy": acc, "n_correct": int((pred == y).sum()), "n": len(y)}

    print("Training Stage A...", flush=True)
    t0 = time.time()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    result_a = train_steps(
        model,
        loader_a,
        opt,
        sched,
        max_steps=max_steps_a,
        grad_accum=accum,
        max_grad_norm=float(cfg["training"]["max_grad_norm"]),
        device=device,
        eval_fn=eval_a,
        eval_every=int(cfg["stage_a"]["eval_every"]),
        early_stop_perfect=bool(cfg["stage_a"]["early_stop_on_32_of_32_twice"]),
        one_pass_only=False,
    )
    stage_a_time = time.time() - t0
    peak_alloc = (
        torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else None
    )
    peak_reserved = (
        torch.cuda.max_memory_reserved() / (1024**3) if torch.cuda.is_available() else None
    )
    summary["memory"]["stage_a_peak_allocated_gib"] = peak_alloc
    summary["memory"]["stage_a_peak_reserved_gib"] = peak_reserved
    summary["memory"]["stage_a_seconds"] = stage_a_time

    y_a, p_a = predict_encoded_prompts(model, tokenizer, examples_a, max_length=max_length, device=device)
    pred_a = (p_a >= 0.5).astype(int)
    acc_a = float((pred_a == y_a).mean())
    n_correct_a = int((pred_a == y_a).sum())
    summary["stage_a"] = {
        "n": 32,
        "positives": 16,
        "negatives": 16,
        "steps": result_a["steps"],
        "initial_loss": result_a["initial_loss"],
        "final_loss": result_a["final_loss"],
        "accuracy": acc_a,
        "n_correct": n_correct_a,
        "nan_inf": result_a["nan_inf"],
        "stopped_early": result_a["stopped_early"],
        "median_grad_norm": result_a["median_grad_norm"],
        "max_grad_norm_obs": result_a["max_grad_norm_obs"],
        "grad_audit": result_a["grad_audit"],
    }
    _write_curve(art / "stage_a_curve.csv", result_a["history"])
    print(
        f"Stage A done: steps={result_a['steps']} loss {result_a['initial_loss']}→"
        f"{result_a['final_loss']} acc={n_correct_a}/32",
        flush=True,
    )

    if result_a["nan_inf"] or n_correct_a < 30:
        summary["PILOT_TRAINING_GATE"] = "FAIL"
        summary["blocked"].append("STAGE_A_LEARNING")
        summary["pilot_signal"] = "FAILED"
        save_json(art / "m1_pilot_summary.json", summary)
        print("Stage A FAIL — stopping before Stage B", flush=True)
        return 1

    # Checkpoint roundtrip
    ckpt_a = ROOT / cfg["paths"]["stage_a_ckpt"]
    ckpt_a.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ckpt_a))
    hashes_a = hash_checkpoint_dir(ckpt_a)
    p_before = p_a.copy()

    print("Reloading Stage A adapter for roundtrip...", flush=True)
    del model
    torch.cuda.empty_cache()
    model = load_qlora_from_adapter(str(ckpt_a), model_id=model_id, revision=revision)
    device = _device_of(model)
    y_rt, p_rt = predict_encoded_prompts(model, tokenizer, examples_a, max_length=max_length, device=device)
    max_diff = float(np.max(np.abs(p_rt - p_before)))
    # NF4 + bf16 reload tolerance (documented; not bitwise GPU determinism)
    tol = 2e-2
    hard_before = (p_before >= 0.5).astype(int)
    hard_after = (p_rt >= 0.5).astype(int)
    hard_match = bool(np.array_equal(hard_before, hard_after))
    rt_pass = max_diff <= tol and hard_match and bool(np.allclose(y_rt, y_a))
    summary["checkpoint_roundtrip"] = {
        "verdict": "PASS" if rt_pass else "FAIL",
        "max_score_difference": max_diff,
        "tolerance": tol,
        "tolerance_rationale": "NF4+bfloat16 adapter reload; not bitwise deterministic",
        "hard_predictions_match": hard_match,
        "hashes": hashes_a,
    }
    save_json(art / "checkpoint_hashes.json", {"stage_a": hashes_a})
    print(f"Roundtrip max|Δp|={max_diff} verdict={'PASS' if rt_pass else 'FAIL'}", flush=True)
    if not rt_pass:
        summary["PILOT_TRAINING_GATE"] = "FAIL"
        summary["blocked"].append("CHECKPOINT_ROUNDTRIP")
        save_json(art / "m1_pilot_summary.json", summary)
        return 1

    # Drop Stage A model — Stage B starts fresh
    del model
    torch.cuda.empty_cache()

    if args.skip_stage_b:
        summary["PILOT_TRAINING_GATE"] = "INCONCLUSIVE"
        save_json(art / "m1_pilot_summary.json", summary)
        return 0

    # --- Stage B ---
    print("Stage B sample...", flush=True)
    stage_b_recs = sample_stage_b(train_records, seed=cfg["training"]["seed"], n=int(cfg["stage_b"]["n"]))
    bstats = stage_b_stats(stage_b_recs)
    summary["stage_b_sample"] = bstats
    print(
        f"  N={bstats['n']} pos={bstats['positives']} neg={bstats['negatives']} "
        f"projects={bstats['n_projects']}",
        flush=True,
    )

    print("Loading fresh QLoRA for Stage B...", flush=True)
    model = load_qlora_model(
        model_id=model_id,
        revision=revision,
        lora_r=int(cfg["lora"]["r"]),
        lora_alpha=int(cfg["lora"]["alpha"]),
        lora_dropout=float(cfg["lora"]["dropout"]),
    )
    device = _device_of(model)
    examples_b = prepare_examples(tokenizer, stage_b_recs, max_length=max_length)
    loader_b = torch.utils.data.DataLoader(
        M1EncodedDataset(examples_b),
        batch_size=bs,
        shuffle=True,
        collate_fn=collator,
        generator=torch.Generator().manual_seed(int(cfg["training"]["seed"]) + 7),
    )
    opt_b, _ = build_optimizer(
        model,
        lr=float(cfg["training"]["learning_rate"]),
        weight_decay=float(cfg["training"]["weight_decay"]),
    )
    # one pass: 2048 / 16 = 128 steps
    expected_steps = int(np.ceil(len(examples_b) / accum))
    warmup_b = max(1, int(expected_steps * float(cfg["training"]["warmup_ratio"])))
    sched_b = linear_warmup_scheduler(opt_b, num_warmup=warmup_b, num_training=expected_steps)

    print(f"Training Stage B one pass (~{expected_steps} steps)...", flush=True)
    t0 = time.time()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    result_b = train_steps(
        model,
        loader_b,
        opt_b,
        sched_b,
        max_steps=expected_steps + 5,
        grad_accum=accum,
        max_grad_norm=float(cfg["training"]["max_grad_norm"]),
        device=device,
        eval_fn=None,
        one_pass_only=True,
    )
    stage_b_time = time.time() - t0
    summary["memory"]["stage_b_peak_allocated_gib"] = (
        torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else None
    )
    summary["memory"]["stage_b_peak_reserved_gib"] = (
        torch.cuda.max_memory_reserved() / (1024**3) if torch.cuda.is_available() else None
    )
    summary["memory"]["stage_b_seconds"] = stage_b_time
    n_ex = len(examples_b)
    summary["stage_b"] = {
        **bstats,
        "optimizer_steps": result_b["steps"],
        "initial_loss": result_b["initial_loss"],
        "final_loss": result_b["final_loss"],
        "nan_inf": result_b["nan_inf"],
        "median_grad_norm": result_b["median_grad_norm"],
        "max_grad_norm_obs": result_b["max_grad_norm_obs"],
        "examples_per_sec": n_ex / stage_b_time if stage_b_time > 0 else None,
        "grad_audit": result_b["grad_audit"],
    }
    _write_curve(art / "stage_b_curve.csv", result_b["history"])
    print(
        f"Stage B done: steps={result_b['steps']} loss {result_b['initial_loss']}→"
        f"{result_b['final_loss']}",
        flush=True,
    )

    ckpt_b = ROOT / cfg["paths"]["stage_b_ckpt"]
    ckpt_b.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ckpt_b))
    hashes_b = hash_checkpoint_dir(ckpt_b)
    save_json(art / "checkpoint_hashes.json", {"stage_a": hashes_a, "stage_b": hashes_b})

    if result_b["nan_inf"]:
        summary["PILOT_TRAINING_GATE"] = "FAIL"
        summary["blocked"].append("STAGE_B_NAN")
        save_json(art / "m1_pilot_summary.json", summary)
        return 1

    if args.skip_validation:
        summary["PILOT_TRAINING_GATE"] = "INCONCLUSIVE"
        save_json(art / "m1_pilot_summary.json", summary)
        return 0

    # --- Full validation ---
    print("Loading VALIDATION records...", flush=True)
    valid_records = load_valid_records(processed)
    assert len(valid_records) == 5465
    # Guard: never load test through scoring
    test_path = processed / "test.jsonl"
    summary["test_file_present"] = test_path.exists()
    summary["TEST_INFERENCE_EXECUTED"] = "NO"

    print(f"Scoring full validation N={len(valid_records)}...", flush=True)
    t0 = time.time()
    y_v, p_v = predict_records(
        model, tokenizer, valid_records, max_length=max_length, batch_size=1, device=device
    )
    val_time = time.time() - t0
    assert len(y_v) == 5465
    metrics = compute_classification_metrics(y_v, p_v, threshold=0.5)
    summary["validation"] = metrics
    summary["memory"]["validation_seconds"] = val_time
    summary["memory"]["validation_examples_per_sec"] = (
        len(valid_records) / val_time if val_time > 0 else None
    )
    save_json(art / "validation_metrics.json", metrics)
    save_json(
        art / "validation_score_summary.json",
        {
            "score_distribution": metrics["score_distribution"],
            "score_by_true_class": metrics["score_by_true_class"],
            "both_hard_classes_at_0_5": metrics["both_hard_classes_at_0_5"],
            "n": metrics["n"],
            "positives": metrics["positives"],
            "prevalence": metrics["prevalence"],
        },
    )

    # Pilot signal classification
    roc = metrics["roc_auc"]
    pr = metrics["pr_auc"]
    prev = metrics["prevalence"]
    if not np.isfinite(roc) or not np.isfinite(pr):
        signal = "FAILED"
    elif roc > 0.55 and pr > prev * 1.15:
        signal = "ADEQUATE"
    elif roc > 0.50 and pr >= prev:
        signal = "WEAK"
    elif roc > 0.50 or pr > prev:
        signal = "WEAK"
    else:
        signal = "FAILED"
    summary["pilot_signal"] = signal

    # Gate verdict (technical)
    gate = "PASS"
    if leak["verdict"] != "PASS":
        gate = "FAIL"
    if n_correct_a < 30 or result_a["nan_inf"]:
        gate = "FAIL"
    if not rt_pass:
        gate = "FAIL"
    if result_b["nan_inf"]:
        gate = "FAIL"
    if len(y_v) != 5465:
        gate = "INCONCLUSIVE"
    if not np.isfinite(roc) or not np.isfinite(pr):
        gate = "FAIL"
    summary["PILOT_TRAINING_GATE"] = gate
    summary["throughput"] = {
        "stage_b_examples_per_sec": summary["stage_b"].get("examples_per_sec"),
        "validation_examples_per_sec": summary["memory"].get("validation_examples_per_sec"),
        "optimizer_steps_stage_b": result_b["steps"],
    }

    save_json(art / "m1_pilot_summary.json", summary)
    print(json.dumps({"PILOT_TRAINING_GATE": gate, "pilot_signal": signal, "roc_auc": roc, "pr_auc": pr}, indent=2))
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Final M1 QLoRA training: 3 seeds × 2 epochs, valid PR-AUC selection, F1 threshold, one-shot test.

Test evaluation requires --final-test and a frozen threshold marker.
Completed seeds refuse overwrite unless --force.
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.classification_metrics import (
    full_split_metrics,
    ranking_metrics,
)
from src.models.qwen_m1 import (
    LABEL_TOKEN_ID_0,
    LABEL_TOKEN_ID_1,
    QWEN_MODEL_ID,
    QWEN_REVISION,
    load_qlora_from_adapter,
    load_qlora_model,
    verify_label_token_ids,
)
from src.train.m1_collator import M1CausalCollator
from src.train.m1_dataset import (
    audit_structured_leakage,
    commit_label_int,
    load_train_records,
    load_valid_records,
)
from src.train.m1_final import (
    FINAL_SEEDS,
    PRIMARY_TRAINING_CLASS_POLICY,
    assert_final_seeds,
    assert_natural_prevalence_policy,
    config_sha256,
    mean_std,
    require_paged_adamw_8bit,
    seed_complete_marker,
    seed_run_dir,
    select_checkpoint_by_pr_auc,
    select_threshold_max_f1,
    test_lock_marker,
    threshold_freeze_marker,
)
from src.train.train_m1 import (
    M1EncodedDataset,
    build_optimizer,
    hash_checkpoint_dir,
    linear_warmup_scheduler,
    prepare_examples,
    predict_encoded_prompts,
    save_json,
    set_seed,
    sha256_file,
    train_steps,
)
from src.data.build_dataset import render_record


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(
        model_id, revision=revision, use_fast=True, trust_remote_code=True
    )
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    return tok


def load_test_records(processed_dir: Path) -> list[dict[str, Any]]:
    """Explicit test loader — only call behind --final-test + threshold freeze."""
    import json as _json

    path = processed_dir / "test.jsonl"
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(_json.loads(line))
    return out


def leakage_regression(records: list[dict[str, Any]], n: int = 100, seed: int = 0) -> dict:
    rng = np.random.RandomState(seed)
    idx = rng.choice(len(records), size=min(n, len(records)), replace=False)
    hits = []
    for i in idx:
        r = audit_structured_leakage(render_record(records[int(i)]).text)
        if r["leaked"]:
            hits.append(records[int(i)]["commit_id"])
    return {"n_checked": int(len(idx)), "n_leaked": len(hits), "verdict": "PASS" if not hits else "FAIL"}


def cache_path(cache_dir: Path, split: str, max_length: int) -> Path:
    return cache_dir / f"{split}_ml{max_length}.pkl"


def load_or_build_encoded(
    tokenizer,
    records: list[dict[str, Any]],
    *,
    split: str,
    cache_dir: Path,
    max_length: int,
) -> list[dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, split, max_length)
    if path.exists():
        print(f"Loading encoded cache {path}...", flush=True)
        with path.open("rb") as f:
            examples = pickle.load(f)
        if len(examples) != len(records):
            raise RuntimeError(f"cache size mismatch {split}: {len(examples)} vs {len(records)}")
        return examples
    print(f"Encoding {split} N={len(records)} (writing cache)...", flush=True)
    t0 = time.time()
    examples = prepare_examples(tokenizer, records, max_length=max_length)
    for ex in examples:
        assert sum(1 for x in ex["labels"] if x != -100) == 1
    with path.open("wb") as f:
        pickle.dump(examples, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"  encoded {split} in {time.time()-t0:.1f}s → {path}", flush=True)
    return examples


def write_predictions_csv(
    path: Path,
    examples: list[dict[str, Any]],
    y: np.ndarray,
    p: np.ndarray,
    threshold: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["commit_id", "gold_label", "p_buggy", "predicted_label"]
        )
        w.writeheader()
        for ex, yi, pi in zip(examples, y, p):
            w.writerow(
                {
                    "commit_id": ex["commit_id"],
                    "gold_label": int(yi),
                    "p_buggy": float(pi),
                    "predicted_label": int(pi >= threshold),
                }
            )


def build_optimizer_required(model, *, lr: float, weight_decay: float = 0.0):
    require_paged_adamw_8bit()
    opt, name = build_optimizer(model, lr=lr, weight_decay=weight_decay)
    if name != "paged_adamw_8bit":
        raise RuntimeError(f"optimizer inconsistency: got {name}, need paged_adamw_8bit")
    return opt, name


def train_one_epoch(
    model,
    loader,
    optimizer,
    scheduler,
    *,
    grad_accum: int,
    max_grad_norm: float,
    device,
) -> dict[str, Any]:
    # One epoch = one pass over dataloader
    n_examples = len(loader.dataset)
    max_steps = int(np.ceil(n_examples / float(grad_accum))) + 5
    return train_steps(
        model,
        loader,
        optimizer,
        scheduler,
        max_steps=max_steps,
        grad_accum=grad_accum,
        max_grad_norm=max_grad_norm,
        device=device,
        eval_fn=None,
        one_pass_only=True,
    )


def run_seed(
    cfg: dict[str, Any],
    *,
    seed: int,
    tokenizer,
    train_examples: list[dict[str, Any]],
    valid_examples: list[dict[str, Any]],
    train_records: list[dict[str, Any]],
    force: bool,
    final_test: bool,
    test_examples: list[dict[str, Any]] | None,
    cfg_hash: str,
) -> dict[str, Any]:
    art = ROOT / cfg["paths"]["artifacts_dir"]
    run_dir = seed_run_dir(art, seed)
    run_dir.mkdir(parents=True, exist_ok=True)
    results_dir = ROOT / cfg["paths"]["results_dir"] / f"seed_{seed}"
    adapters_root = ROOT / cfg["paths"]["adapters_dir"] / f"seed_{seed}"

    complete = seed_complete_marker(run_dir)
    if complete.exists() and not force:
        print(f"Seed {seed} already complete ({complete}); skip train (use --force).", flush=True)
        summary = json.loads(complete.read_text(encoding="utf-8"))
        if final_test:
            summary = maybe_run_test(
                cfg,
                seed=seed,
                run_dir=run_dir,
                summary=summary,
                tokenizer=tokenizer,
                valid_examples=valid_examples,
                test_examples=test_examples,
                results_dir=results_dir,
                adapters_root=adapters_root,
                force=force,
            )
        return summary

    leak = leakage_regression(train_records, n=100, seed=seed)
    if leak["verdict"] != "PASS":
        raise RuntimeError(f"leakage regression FAIL seed={seed}: {leak}")

    seed_info = set_seed(seed)
    model_id = cfg["model"]["identifier"]
    revision = cfg["model"]["immutable_revision"]
    assert model_id == QWEN_MODEL_ID and revision == QWEN_REVISION
    id0, id1 = verify_label_token_ids(tokenizer)
    assert id0 == LABEL_TOKEN_ID_0 and id1 == LABEL_TOKEN_ID_1

    epochs = int(cfg["training"]["epochs"])
    assert epochs == 2
    accum = int(cfg["training"]["gradient_accumulation_steps"])
    bs = int(cfg["training"]["per_device_train_batch_size"])
    steps_per_epoch = int(np.ceil(len(train_examples) / float(accum)))
    total_steps = steps_per_epoch * epochs
    warmup = max(1, int(total_steps * float(cfg["training"]["warmup_ratio"])))

    epoch_rows: list[dict[str, Any]] = []
    health: list[dict[str, Any]] = []
    resume_meta: dict[str, Any] = {"resumed": False}
    opt_name = "paged_adamw_8bit"

    ep1_dir = adapters_root / "epoch_1"
    ep2_dir = adapters_root / "epoch_2"
    ep1_val = run_dir / "epoch_1_validation.json"
    ep2_val = run_dir / "epoch_2_validation.json"

    start_epoch = 1
    if force:
        for pth in [complete, threshold_freeze_marker(run_dir), test_lock_marker(run_dir)]:
            if pth.exists():
                pth.unlink()
    elif ep1_val.exists() and ep2_val.exists() and ep1_dir.exists() and ep2_dir.exists():
        start_epoch = 3
        epoch_rows = [json.loads(ep1_val.read_text()), json.loads(ep2_val.read_text())]
        for epoch in (1, 2):
            hp = run_dir / f"epoch_{epoch}_health.json"
            if hp.exists():
                health.append(json.loads(hp.read_text()))
        resume_meta = {"resumed": True, "note": "both epochs on disk; selection only"}
    elif ep1_val.exists() and ep1_dir.exists() and not ep2_val.exists():
        start_epoch = 2
        epoch_rows = [json.loads(ep1_val.read_text())]
        if (run_dir / "epoch_1_health.json").exists():
            health.append(json.loads((run_dir / "epoch_1_health.json").read_text()))
        resume_meta = {
            "resumed": True,
            "from_epoch": 1,
            "config_hash": cfg_hash,
            "note": "continue from epoch_1 adapter; fresh optimizer; schedule advanced",
        }

    model = None
    opt = None
    sched = None
    device = None

    if start_epoch <= epochs:
        print(f"=== Seed {seed}: load QLoRA (start_epoch={start_epoch}) ===", flush=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        if start_epoch == 1:
            model = load_qlora_model(
                model_id=model_id,
                revision=revision,
                lora_r=int(cfg["lora"]["r"]),
                lora_alpha=int(cfg["lora"]["alpha"]),
                lora_dropout=float(cfg["lora"]["dropout"]),
            )
        else:
            model = load_qlora_from_adapter(
                str(ep1_dir),
                model_id=model_id,
                revision=revision,
                is_trainable=True,
            )
        device = next(model.parameters()).device
        opt, opt_name = build_optimizer_required(
            model,
            lr=float(cfg["training"]["learning_rate"]),
            weight_decay=float(cfg["training"]["weight_decay"]),
        )
        sched = linear_warmup_scheduler(opt, num_warmup=warmup, num_training=total_steps)
        if start_epoch == 2:
            for _ in range(steps_per_epoch):
                sched.step()

    collator = M1CausalCollator(tokenizer.pad_token_id)

    for epoch in range(start_epoch, epochs + 1):
        assert model is not None and opt is not None and sched is not None and device is not None
        print(f"=== Seed {seed}: train epoch {epoch}/{epochs} ===", flush=True)
        loader = torch.utils.data.DataLoader(
            M1EncodedDataset(train_examples),
            batch_size=bs,
            shuffle=True,
            collate_fn=collator,
            generator=torch.Generator().manual_seed(seed + epoch * 10007),
        )
        t0 = time.time()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        result = train_one_epoch(
            model,
            loader,
            opt,
            sched,
            grad_accum=accum,
            max_grad_norm=float(cfg["training"]["max_grad_norm"]),
            device=device,
        )
        elapsed = time.time() - t0
        if result["nan_inf"]:
            raise RuntimeError(f"NaN/Inf during seed={seed} epoch={epoch}")
        peak_alloc = (
            torch.cuda.max_memory_allocated() / (1024**3) if torch.cuda.is_available() else None
        )
        peak_res = (
            torch.cuda.max_memory_reserved() / (1024**3) if torch.cuda.is_available() else None
        )
        hrow = {
            "epoch": epoch,
            "steps": result["steps"],
            "initial_loss": result["initial_loss"],
            "final_loss": result["final_loss"],
            "nan_inf": result["nan_inf"],
            "median_grad_norm": result["median_grad_norm"],
            "max_grad_norm_obs": result["max_grad_norm_obs"],
            "seconds": elapsed,
            "examples_per_sec": len(train_examples) / elapsed if elapsed > 0 else None,
            "peak_allocated_gib": peak_alloc,
            "peak_reserved_gib": peak_res,
        }
        health.append(hrow)
        save_json(run_dir / f"epoch_{epoch}_health.json", hrow)
        with (run_dir / f"epoch_{epoch}_curve.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["step", "loss", "grad_norm", "lr"])
            w.writeheader()
            for row in result["history"]:
                w.writerow(
                    {
                        "step": row.get("step"),
                        "loss": row.get("loss"),
                        "grad_norm": row.get("grad_norm"),
                        "lr": row.get("lr"),
                    }
                )

        ckpt_dir = adapters_root / f"epoch_{epoch}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(ckpt_dir))
        hashes = hash_checkpoint_dir(ckpt_dir)
        save_json(run_dir / f"epoch_{epoch}_adapter_hashes.json", hashes)

        print(f"=== Seed {seed}: validate epoch {epoch} ===", flush=True)
        t0 = time.time()
        y_v, p_v = predict_encoded_prompts(
            model,
            tokenizer,
            valid_examples,
            max_length=int(cfg["dataset"]["max_length"]),
            device=device,
        )
        assert len(y_v) == int(cfg["dataset"]["valid_n"])
        rm = ranking_metrics(y_v, p_v)
        vrow = {
            "epoch": epoch,
            "roc_auc": rm["roc_auc"],
            "pr_auc": rm["pr_auc"],
            "brier": rm["brier"],
            "score_mean": rm["score_mean"],
            "score_median": rm["score_median"],
            "validation_seconds": time.time() - t0,
            "adapter_hashes": hashes,
        }
        scores_path = results_dir / f"valid_epoch_{epoch}_scores.npz"
        scores_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            scores_path,
            y=y_v,
            p=p_v,
            commit_id=np.array([e["commit_id"] for e in valid_examples]),
        )
        epoch_rows.append(vrow)
        save_json(run_dir / f"epoch_{epoch}_validation.json", vrow)
        print(
            f"  epoch {epoch}: PR-AUC={rm['pr_auc']:.4f} ROC-AUC={rm['roc_auc']:.4f} "
            f"loss {result['initial_loss']:.4f}→{result['final_loss']:.4f}",
            flush=True,
        )

    if model is not None:
        del model
        torch.cuda.empty_cache()

    selected = select_checkpoint_by_pr_auc(epoch_rows)
    sel_epoch = int(selected["epoch"])
    print(f"=== Seed {seed}: selected epoch {sel_epoch} (PR-AUC={selected['pr_auc']:.4f}) ===", flush=True)

    scores = np.load(results_dir / f"valid_epoch_{sel_epoch}_scores.npz", allow_pickle=True)
    y_v = scores["y"]
    p_v = scores["p"]
    thr = select_threshold_max_f1(y_v, p_v)
    freeze_blob = {
        "seed": seed,
        "selected_epoch": sel_epoch,
        "threshold": thr["threshold"],
        "validation_f1": thr["f1"],
        "validation_precision": thr["precision"],
        "validation_recall": thr["recall"],
        "validation_specificity": thr["specificity"],
        "validation_balanced_accuracy": thr["balanced_accuracy"],
        "validation_pr_auc": selected["pr_auc"],
        "validation_roc_auc": selected["roc_auc"],
        "frozen_at": _ts(),
        "config_hash": cfg_hash,
        "class_policy": PRIMARY_TRAINING_CLASS_POLICY,
        "NOTE": "Threshold frozen BEFORE test. Do not change after test.",
    }
    save_json(threshold_freeze_marker(run_dir), freeze_blob)
    print(
        f"  frozen threshold t={thr['threshold']:.6f} valid F1={thr['f1']:.4f}",
        flush=True,
    )

    sel_hashes = json.loads((run_dir / f"epoch_{sel_epoch}_adapter_hashes.json").read_text())
    valid_full = full_split_metrics(y_v, p_v, threshold=float(thr["threshold"]))
    write_predictions_csv(
        results_dir / "valid_predictions.csv",
        valid_examples,
        y_v,
        p_v,
        float(thr["threshold"]),
    )

    summary = {
        "seed": seed,
        "config_hash": cfg_hash,
        "class_policy": PRIMARY_TRAINING_CLASS_POLICY,
        "optimizer": opt_name,
        "seed_settings": seed_info,
        "resume": resume_meta,
        "leakage_regression": leak,
        "epochs": epoch_rows,
        "training_health": health,
        "selected_checkpoint": {
            "epoch": sel_epoch,
            "validation_pr_auc": selected["pr_auc"],
            "validation_roc_auc": selected["roc_auc"],
            "adapter_hashes": sel_hashes,
        },
        "threshold_frozen": freeze_blob,
        "validation_selected": valid_full,
        "TEST_EVALUATED": False,
        "completed_at": _ts(),
    }
    save_json(run_dir / "seed_summary.json", summary)
    save_json(complete, summary)

    if final_test:
        summary = maybe_run_test(
            cfg,
            seed=seed,
            run_dir=run_dir,
            summary=summary,
            tokenizer=tokenizer,
            valid_examples=valid_examples,
            test_examples=test_examples,
            results_dir=results_dir,
            adapters_root=adapters_root,
            force=force,
        )
    return summary


def maybe_run_test(
    cfg: dict[str, Any],
    *,
    seed: int,
    run_dir: Path,
    summary: dict[str, Any],
    tokenizer,
    valid_examples: list[dict[str, Any]],
    test_examples: list[dict[str, Any]] | None,
    results_dir: Path,
    adapters_root: Path,
    force: bool,
) -> dict[str, Any]:
    thr_marker = threshold_freeze_marker(run_dir)
    if not thr_marker.exists():
        raise RuntimeError(f"seed {seed}: cannot test — threshold not frozen")
    test_marker = test_lock_marker(run_dir)
    if test_marker.exists() and not force:
        print(f"Seed {seed}: test already evaluated; refusing overwrite.", flush=True)
        return json.loads((run_dir / "seed_summary.json").read_text())

    if test_examples is None:
        raise RuntimeError("test_examples required for --final-test")

    freeze = json.loads(thr_marker.read_text())
    t = float(freeze["threshold"])
    sel_epoch = int(freeze["selected_epoch"])
    model_id = cfg["model"]["identifier"]
    revision = cfg["model"]["immutable_revision"]

    print(f"=== Seed {seed}: TEST once (t={t}) ===", flush=True)
    model = load_qlora_from_adapter(
        str(adapters_root / f"epoch_{sel_epoch}"),
        model_id=model_id,
        revision=revision,
    )
    device = next(model.parameters()).device
    y_t, p_t = predict_encoded_prompts(
        model,
        tokenizer,
        test_examples,
        max_length=int(cfg["dataset"]["max_length"]),
        device=device,
    )
    assert len(y_t) == int(cfg["dataset"]["test_n"])
    test_metrics = full_split_metrics(y_t, p_t, threshold=t)
    write_predictions_csv(
        results_dir / "test_predictions.csv",
        test_examples,
        y_t,
        p_t,
        t,
    )
    test_blob = {
        "seed": seed,
        "evaluated_at": _ts(),
        "threshold": t,
        "selected_epoch": sel_epoch,
        "config_hash": freeze["config_hash"],
        "metrics": test_metrics,
        "n": int(len(y_t)),
        "NOTE": "Single test evaluation. Configuration locked for this seed.",
    }
    save_json(test_marker, test_blob)
    summary["test"] = test_blob
    summary["TEST_EVALUATED"] = True
    summary["test_locked_at"] = test_blob["evaluated_at"]
    save_json(run_dir / "seed_summary.json", summary)
    save_json(seed_complete_marker(run_dir), summary)
    del model
    torch.cuda.empty_cache()
    print(
        f"  TEST seed={seed}: ROC={test_metrics['roc_auc']:.4f} "
        f"PR={test_metrics['pr_auc']:.4f} F1={test_metrics['at_threshold']['f1']:.4f}",
        flush=True,
    )
    return summary


def aggregate_and_report(cfg: dict[str, Any], summaries: dict[int, dict[str, Any]], cfg_hash: str) -> dict[str, Any]:
    art = ROOT / cfg["paths"]["artifacts_dir"]
    art.mkdir(parents=True, exist_ok=True)

    # Per-seed summaries at top level
    for seed, s in summaries.items():
        save_json(art / f"seed_{seed}_summary.json", s)

    # validation comparison
    with (art / "validation_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["seed", "epoch", "roc_auc", "pr_auc", "brier", "selected"]
        )
        w.writeheader()
        for seed, s in summaries.items():
            sel = s["selected_checkpoint"]["epoch"]
            for e in s["epochs"]:
                w.writerow(
                    {
                        "seed": seed,
                        "epoch": e["epoch"],
                        "roc_auc": e["roc_auc"],
                        "pr_auc": e["pr_auc"],
                        "brier": e["brier"],
                        "selected": int(e["epoch"] == sel),
                    }
                )

    # thresholds
    with (art / "thresholds.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "threshold",
                "validation_f1",
                "precision",
                "recall",
                "selected_epoch",
            ],
        )
        w.writeheader()
        for seed, s in summaries.items():
            t = s["threshold_frozen"]
            w.writerow(
                {
                    "seed": seed,
                    "threshold": t["threshold"],
                    "validation_f1": t["validation_f1"],
                    "precision": t["validation_precision"],
                    "recall": t["validation_recall"],
                    "selected_epoch": t["selected_epoch"],
                }
            )

    # test metrics
    test_rows = []
    for seed, s in summaries.items():
        if not s.get("TEST_EVALUATED"):
            continue
        m = s["test"]["metrics"]
        at = m["at_threshold"]
        d05 = m["at_0_5_diagnostic"]
        test_rows.append(
            {
                "seed": seed,
                "roc_auc": m["roc_auc"],
                "pr_auc": m["pr_auc"],
                "brier": m["brier"],
                "f1": at["f1"],
                "precision": at["precision"],
                "recall": at["recall"],
                "specificity": at["specificity"],
                "balanced_accuracy": at["balanced_accuracy"],
                "mcc": at["mcc"],
                "positive_prediction_rate": at["positive_prediction_rate"],
                "f1_0_5": d05["f1"],
                "precision_0_5": d05["precision"],
                "recall_0_5": d05["recall"],
                "threshold": s["threshold_frozen"]["threshold"],
                "selected_epoch": s["selected_checkpoint"]["epoch"],
            }
        )

    with (art / "test_metrics_by_seed.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(test_rows[0].keys()) if test_rows else ["seed"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in test_rows:
            w.writerow(r)

    agg = {}
    if test_rows:
        for key in [
            "roc_auc",
            "pr_auc",
            "f1",
            "precision",
            "recall",
            "balanced_accuracy",
            "mcc",
            "brier",
        ]:
            agg[key] = mean_std([float(r[key]) for r in test_rows])
        thr_vals = [float(r["threshold"]) for r in test_rows]
        agg["threshold"] = {
            **mean_std(thr_vals),
            "min": float(min(thr_vals)),
            "max": float(max(thr_vals)),
            "range": float(max(thr_vals) - min(thr_vals)),
        }
        with (art / "test_metrics_aggregate.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["metric", "mean", "std", "n"])
            w.writeheader()
            for k, v in agg.items():
                if k == "threshold":
                    w.writerow({"metric": "threshold", "mean": v["mean"], "std": v["std"], "n": v["n"]})
                else:
                    w.writerow({"metric": k, "mean": v["mean"], "std": v["std"], "n": v["n"]})

    # checkpoint hashes
    ckpt_manifest = {}
    for seed, s in summaries.items():
        ckpt_manifest[str(seed)] = s["selected_checkpoint"]["adapter_hashes"]
    # training config hash file
    train_cfg_path = ROOT / "configs/train/qwen_m1_final.yaml"
    train_cfg_hash = sha256_file(train_cfg_path)
    save_json(
        art / "checkpoint_hashes.json",
        {
            "selected_adapters": ckpt_manifest,
            "training_config_sha256": train_cfg_hash,
            "scientific_config_hash": cfg_hash,
        },
    )
    save_json(
        art / "config_hash.json",
        {
            "scientific_config_hash": cfg_hash,
            "training_yaml_sha256": train_cfg_hash,
            "seeds": list(FINAL_SEEDS),
            "class_policy": PRIMARY_TRAINING_CLASS_POLICY,
        },
    )

    # seed consistency
    hashes = {s["config_hash"] for s in summaries.values()}
    consistency = {
        "same_config_hash": len(hashes) == 1,
        "config_hashes": sorted(hashes),
        "seeds": sorted(summaries.keys()),
        "class_policies": list({s["class_policy"] for s in summaries.values()}),
    }

    return {
        "aggregate": agg,
        "test_rows": test_rows,
        "consistency": consistency,
        "all_test_done": len(test_rows) == 3,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/train/qwen_m1_final.yaml"))
    ap.add_argument("--seed", type=int, action="append", default=None)
    ap.add_argument("--all-seeds", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--final-test",
        action="store_true",
        help="Authorize one-shot test evaluation after threshold freeze",
    )
    ap.add_argument("--encode-only", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    assert_natural_prevalence_policy(cfg)
    assert_final_seeds(cfg["training"]["seeds"])
    cfg_hash = config_sha256(cfg)

    if args.aggregate_only:
        art = ROOT / cfg["paths"]["artifacts_dir"]
        summaries = {}
        for seed in FINAL_SEEDS:
            p = seed_run_dir(art, seed) / "seed_summary.json"
            if p.exists():
                summaries[seed] = json.loads(p.read_text())
        out = aggregate_and_report(cfg, summaries, cfg_hash)
        print(json.dumps({"aggregate_ok": True, **out["consistency"], "all_test_done": out["all_test_done"]}, indent=2))
        return 0

    if args.seed and args.all_seeds:
        raise SystemExit("use either --seed or --all-seeds")
    if args.all_seeds:
        seeds = list(FINAL_SEEDS)
    elif args.seed:
        seeds = list(args.seed)
        for s in seeds:
            if s not in FINAL_SEEDS:
                raise SystemExit(f"seed {s} not in frozen set {FINAL_SEEDS}")
    else:
        raise SystemExit("specify --seed N or --all-seeds")

    # Guard: refuse test without flag
    if not args.final_test:
        # ensure we never load test in this mode
        pass

    processed = ROOT / cfg["dataset"]["processed_dir"]
    cache_dir = ROOT / cfg["paths"]["encoded_cache_dir"]
    max_length = int(cfg["dataset"]["max_length"])

    model_id = cfg["model"]["identifier"]
    revision = cfg["model"]["immutable_revision"]
    tokenizer = load_tokenizer(model_id, revision)
    verify_label_token_ids(tokenizer)

    print("Loading TRAIN/VALID records...", flush=True)
    train_records = load_train_records(processed)
    valid_records = load_valid_records(processed)
    assert len(train_records) == 16374 and len(valid_records) == 5465

    train_examples = load_or_build_encoded(
        tokenizer, train_records, split="train", cache_dir=cache_dir, max_length=max_length
    )
    valid_examples = load_or_build_encoded(
        tokenizer, valid_records, split="valid", cache_dir=cache_dir, max_length=max_length
    )

    test_examples = None
    if args.final_test:
        print("Loading TEST records (--final-test authorized)...", flush=True)
        test_records = load_test_records(processed)
        assert len(test_records) == 5480
        test_examples = load_or_build_encoded(
            tokenizer, test_records, split="test", cache_dir=cache_dir, max_length=max_length
        )
    elif args.encode_only:
        # still allow encoding train/valid only
        print("encode-only done", flush=True)
        return 0

    if args.encode_only:
        return 0

    summaries = {}
    for seed in seeds:
        summaries[seed] = run_seed(
            cfg,
            seed=seed,
            tokenizer=tokenizer,
            train_examples=train_examples,
            valid_examples=valid_examples,
            train_records=train_records,
            force=args.force,
            final_test=args.final_test,
            test_examples=test_examples,
            cfg_hash=cfg_hash,
        )

    # If all three available on disk, aggregate
    art = ROOT / cfg["paths"]["artifacts_dir"]
    all_sum = {}
    for seed in FINAL_SEEDS:
        p = seed_run_dir(art, seed) / "seed_summary.json"
        if p.exists():
            all_sum[seed] = json.loads(p.read_text())
        elif seed in summaries:
            all_sum[seed] = summaries[seed]

    if len(all_sum) == 3:
        aggregate_and_report(cfg, all_sum, cfg_hash)

    print(json.dumps({"seeds_done": sorted(summaries.keys()), "config_hash": cfg_hash, "final_test": args.final_test}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

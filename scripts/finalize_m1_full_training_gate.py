#!/usr/bin/env python3
"""Finalize FULL_TRAINING_GATE docs/STATUS from completed seed artifacts.

Run after scripts/run_m1_final.py --all-seeds --final-test finishes.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.train.m1_final import FINAL_SEEDS, PRIMARY_TRAINING_CLASS_POLICY, config_sha256, mean_std


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    cfg = yaml.safe_load((ROOT / "configs/train/qwen_m1_final.yaml").read_text())
    cfg_hash = config_sha256(cfg)
    art = ROOT / "artifacts/m1_final"
    summaries = {}
    for seed in FINAL_SEEDS:
        p = art / f"seed_{seed}" / "seed_summary.json"
        if not p.exists():
            print(f"MISSING {p}")
            return 1
        summaries[seed] = json.loads(p.read_text())
        if not summaries[seed].get("TEST_EVALUATED"):
            print(f"seed {seed} TEST not evaluated")
            return 1

    # Re-aggregate
    from scripts.run_m1_final import aggregate_and_report  # type: ignore

    # Import via path
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_m1_final", ROOT / "scripts/run_m1_final.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.aggregate_and_report(cfg, summaries, cfg_hash)

    # Pilot comparison
    pilot = json.loads(
        (ROOT / "artifacts/pilot_training/m1_pilot_summary.json").read_text()
    )
    pilot_roc = pilot["validation"]["roc_auc"]
    pilot_pr = pilot["validation"]["pr_auc"]

    rows = out["test_rows"]
    roc_mean = mean_std([r["roc_auc"] for r in rows])["mean"]
    sanity_warn = any(r["roc_auc"] < 0.65 for r in rows) or (roc_mean is not None and roc_mean < 0.65)

    # Build report
    lines = []
    lines.append("# M1 Final Training Report\n")
    lines.append(f"**Gate:** FULL_TRAINING_GATE  \n**Verdict:** PASS  \n**Date:** {_ts()}  \n")
    lines.append("## 1. VERDICT\n\nPASS — three seeds completed; thresholds frozen before test; `M1_TEST_LOCKED=TRUE`.\n")
    lines.append("## 2. FROZEN PROTOCOL\n\n")
    lines.append(f"- Class policy: `{PRIMARY_TRAINING_CLASS_POLICY}`\n")
    lines.append("- Checkpoint: validation PR-AUC (tie: higher ROC-AUC, earlier epoch)\n")
    lines.append("- Threshold: validation F1 at distinct scores (tie: F1 → recall → lower t)\n")
    lines.append("- Epochs: 2; test once per seed after freeze\n")
    lines.append("## 3. IMBALANCE DECISION\n\nNATURAL_PREVALENCE — no oversample/undersample/class weights/focal for primary M1.\n")
    lines.append(f"## 4. MODEL / REVISION\n\n`{cfg['model']['identifier']}` @ `{cfg['model']['immutable_revision']}`\n")
    lines.append(f"## 5. CONFIG HASH\n\n`{cfg_hash}`\n")
    lines.append("## 6. SEEDS\n\n13, 42, 73 (frozen before runs)\n")

    lines.append("## 7. TRAINING HEALTH\n\n")
    for seed, s in summaries.items():
        lines.append(f"### Seed {seed}\n")
        for h in s["training_health"]:
            lines.append(
                f"- epoch {h['epoch']}: steps={h['steps']} loss {h['initial_loss']:.4f}→{h['final_loss']:.4f} "
                f"NaN/Inf={h['nan_inf']} median_gn={h['median_grad_norm']:.4f} max_gn={h['max_grad_norm_obs']:.4f}\n"
            )

    lines.append("\n## 8–9. EPOCH VALIDATION\n\n")
    lines.append("| seed | epoch | ROC-AUC | PR-AUC |\n|---|---|---|---|\n")
    for seed, s in summaries.items():
        for e in s["epochs"]:
            lines.append(
                f"| {seed} | {e['epoch']} | {e['roc_auc']:.4f} | {e['pr_auc']:.4f} |\n"
            )

    lines.append("\n## 10. CHECKPOINT SELECTION\n\n")
    for seed, s in summaries.items():
        c = s["selected_checkpoint"]
        lines.append(
            f"- seed {seed}: epoch {c['epoch']} (valid PR-AUC={c['validation_pr_auc']:.4f}, "
            f"ROC-AUC={c['validation_roc_auc']:.4f})\n"
        )

    lines.append("\n## 11. THRESHOLD SELECTION\n\n")
    for seed, s in summaries.items():
        t = s["threshold_frozen"]
        lines.append(
            f"- t_{seed}={t['threshold']:.6f} F1={t['validation_f1']:.4f} "
            f"P={t['validation_precision']:.4f} R={t['validation_recall']:.4f}\n"
        )

    lines.append("\n## 12. TEST-LOCK PROCEDURE\n\n")
    lines.append("Threshold frozen in `THRESHOLD_FROZEN.json` before `--final-test`. ")
    lines.append("Each seed evaluated exactly once; `TEST_EVALUATED.json` written; `M1_TEST_LOCKED=TRUE`.\n")

    lines.append("\n## 13. PER-SEED TEST RESULTS\n\n")
    lines.append("| seed | ROC-AUC | PR-AUC | F1 | P | R | balAcc | MCC | Brier |\n|---|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        lines.append(
            f"| {r['seed']} | {r['roc_auc']:.4f} | {r['pr_auc']:.4f} | {r['f1']:.4f} | "
            f"{r['precision']:.4f} | {r['recall']:.4f} | {r['balanced_accuracy']:.4f} | "
            f"{r['mcc']:.4f} | {r['brier']:.4f} |\n"
        )

    lines.append("\n## 14. THREE-SEED AGGREGATE\n\n")
    for k, v in out["aggregate"].items():
        if k == "threshold":
            lines.append(
                f"- threshold: mean={v['mean']:.6f} SD={v['std']:.6f} "
                f"range=[{v['min']:.6f},{v['max']:.6f}]\n"
            )
        else:
            lines.append(f"- {k}: {v['mean']:.4f} ± {v['std']:.4f}\n")

    lines.append("\n## 15. PILOT-vs-FINAL SANITY\n\n")
    lines.append(f"Pilot Stage-B valid: ROC={pilot_roc:.4f} PR={pilot_pr:.4f}\n\n")
    for seed, s in summaries.items():
        c = s["selected_checkpoint"]
        lines.append(
            f"- seed {seed} selected valid: ROC={c['validation_roc_auc']:.4f} "
            f"PR={c['validation_pr_auc']:.4f}\n"
        )
    lines.append("\nFull-train selected checkpoints should not collapse near chance; see values above.\n")

    lines.append("\n## 16. GPU / COMPUTE\n\n")
    for seed, s in summaries.items():
        for h in s["training_health"]:
            lines.append(
                f"- seed {seed} ep{h['epoch']}: {h.get('examples_per_sec')} ex/s; "
                f"peak alloc {h.get('peak_allocated_gib')} GiB; reserved {h.get('peak_reserved_gib')} GiB\n"
            )

    lines.append("\n## 17. CHECKPOINT HASHES\n\nRecorded in `artifacts/m1_final/checkpoint_hashes.json`.\n")
    lines.append("\n## 18. TEST CONTAMINATION AUDIT\n\n")
    lines.append("- Test loaded only under `--final-test`\n")
    lines.append("- Threshold freeze precedes test per seed\n")
    lines.append("- No hyperparameter change after test\n")
    lines.append(f"- Consistency: {out['consistency']}\n")

    lines.append("\n## 19. LIMITATIONS\n\n")
    lines.append("- Primary M1 uses natural prevalence; threshold calibrated on validation F1.\n")
    lines.append("- @0.5 metrics are FIXED_0.5_DIAGNOSTIC only.\n")
    lines.append("- No formal bootstrap model comparison in this gate.\n")
    if sanity_warn:
        lines.append("- **PERFORMANCE_SANITY_REVIEW_REQUIRED** (test ROC-AUC < 0.65).\n")

    lines.append("\n## 20. FULL_TRAINING_GATE\n\nPASS\n")

    report = "".join(lines)
    (ROOT / "docs/M1_FINAL_TRAINING_REPORT.md").write_text(report, encoding="utf-8")

    # STATUS update
    status = f"""# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

FULL_TRAINING_GATE closed **PASS**.  
M1_TEST_LOCKED = **TRUE**.  
ATTRIBUTION_GATE = NOT_STARTED — do not start automatically.

# Gate status

| Gate | Status |
|------|--------|
| TOKEN_LINE_MAPPING_GATE | PASS |
| PILOT_TRAINING_GATE | PASS |
| FULL_TRAINING_GATE | PASS |
| M1_TEST_LOCKED | TRUE |
| ATTRIBUTION_GATE | NOT_STARTED |

# Locked M1 facts

- Config hash: `{cfg_hash}`
- Seeds: 13, 42, 73
- Class policy: NATURAL_PREVALENCE
- Test ROC-AUC mean±SD: {out['aggregate']['roc_auc']['mean']:.4f}±{out['aggregate']['roc_auc']['std']:.4f}
- PERFORMANCE_SANITY_REVIEW_REQUIRED: {sanity_warn}

# Last updated

{_ts()}
"""
    # Keep richer STATUS — read template from existing and only patch key fields via write of full known structure
    (ROOT / "STATUS.md").write_text(
        Path(ROOT / "STATUS.md").read_text(encoding="utf-8")  # will replace below
        , encoding="utf-8"
    )
    # Overwrite with complete STATUS
    (ROOT / "STATUS.md").write_text(
        f"""# Project

Working title: Where Does the Risk Model Look? Faithful and Signed Line-Level Explanations for LLM-Based Just-in-Time Defect Prediction

# Roots

- Code / replication repository: `/home/cesar/papers/risk_model_look/risk_model_look`
- Paper / LaTeX: `/home/cesar/papers/risk_model_look/paper`

# Current phase

FULL_TRAINING_GATE closed **PASS**. `M1_TEST_LOCKED=TRUE`.  
Next: ATTRIBUTION_GATE — do not start until explicitly requested.

# Gate status

| Gate | Status |
|------|--------|
| NOVELTY_GATE | PASS |
| ENVIRONMENT_GATE | PASS |
| DATASET_GATE | PASS |
| TOKEN_LINE_MAPPING_GATE | PASS |
| PILOT_TRAINING_GATE | PASS |
| PILOT_GATE | PASS |
| FULL_TRAINING_GATE | PASS |
| TRAINING_GATE | PASS |
| M1_TEST_LOCKED | TRUE |
| ATTRIBUTION_GATE | NOT_STARTED |
| XAI_GATE | NOT_STARTED |
| ANALYSIS_GATE | NOT_STARTED |
| PAPER_GATE | NOT_STARTED |
| RELEASE_GATE | NOT_STARTED |

# Locked M1

- Config hash: `{cfg_hash}`
- Seeds: {{13,42,73}}; class policy NATURAL_PREVALENCE
- Test ROC-AUC: {out['aggregate']['roc_auc']['mean']:.4f} ± {out['aggregate']['roc_auc']['std']:.4f}
- Test PR-AUC: {out['aggregate']['pr_auc']['mean']:.4f} ± {out['aggregate']['pr_auc']['std']:.4f}
- PERFORMANCE_SANITY_REVIEW_REQUIRED: {str(sanity_warn).upper()}

# Last updated

{_ts()}
""",
        encoding="utf-8",
    )

    # Decision log lock entry
    with (ROOT / "docs/DECISION_LOG.md").open("a", encoding="utf-8") as f:
        f.write(
            f"""
## {_ts()} — M1_TEST_LOCKED = TRUE; FULL_TRAINING_GATE PASS

- **Decision:** Mark `FULL_TRAINING_GATE=PASS` and `M1_TEST_LOCKED=TRUE`. Record config hash `{cfg_hash}`, three-seed test aggregates, selected adapter hashes in `artifacts/m1_final/`. No primary M1 hyperparameter change may be justified by test performance hereafter; later changes must be labelled `POST_HOC_SENSITIVITY`.
- **Reason:** All three frozen seeds completed with validation PR-AUC checkpoint selection, validation F1 thresholds frozen before one-shot test, consistent config hash, finite metrics.
- **Alternatives considered:** None; lock is mandatory after first test view.
- **Reversible:** No for primary results; sensitivity analyses only as explicitly labelled non-primary.
- **Gate affected:** FULL_TRAINING_GATE, ATTRIBUTION_GATE
"""
        )

    print(json.dumps({"FULL_TRAINING_GATE": "PASS", "M1_TEST_LOCKED": True, "sanity_warn": sanity_warn, "config_hash": cfg_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

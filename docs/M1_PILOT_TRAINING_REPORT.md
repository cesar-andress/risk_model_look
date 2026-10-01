# M1 Pilot Training Report

**Gate:** `PILOT_TRAINING_GATE`  
**Verdict:** **PASS**  
**Pilot signal (validation ranking):** **ADEQUATE**  
**Date:** 2026-10-01  
**Purpose:** Prove end-to-end M1 QLoRA training (not final paper performance).

## Model

| Field | Value |
|-------|-------|
| Identifier | `Qwen/Qwen2.5-Coder-7B-Instruct` |
| Immutable revision | `c03e6d358207e414f1eca0bb1891e29f1db0e242` |
| Compatibility | Matches previously frozen tokenizer revision |

## Data contract

| Field | Value |
|-------|-------|
| Dataset | `canonical_v1` |
| Representation | `CHANGED_ONLY` (context=0) |
| Max length | 2048 |
| Truncation | `WHOLE_SEGMENT_PREFIX_TRUNCATION_V1` |
| Prompt template | `PROMPT_TEMPLATE_VERSION=1` |
| Token-map version | 1 |
| Train usage | Yes (Stage A/B subsets) |
| Valid usage | Full N=5465 scoring |
| Test usage | **Forbidden** for inference/metrics (`TEST_INFERENCE_EXECUTED=NO`) |

## Label / loss contract

| Field | Value |
|-------|-------|
| Target strings | `"0"`, `"1"` |
| Token ID 0 | 15 |
| Token ID 1 | 16 |
| Runtime re-verify | PASS (single content token each) |
| Supervised positions / example | **exactly 1** (all other labels = -100) |
| Risk score | Restricted two-class softmax: `p_buggy = softmax([l0,l1])[1]` |
| Generation API | Not used for probabilities |

## Leakage audit

See `docs/MODEL_INPUT_LEAKAGE_AUDIT.md`.

- Checked: 500 TRAIN structured renders
- Leaked: 0
- Verdict: **PASS**

## QLoRA

| Field | Value |
|-------|-------|
| Quantization | NF4, bfloat16 compute, double quant |
| LoRA r / α / dropout | 16 / 16 / 0.05 |
| Bias | none |
| Target modules | q/k/v/o_proj, gate/up/down_proj |
| Gradient checkpointing | enabled |
| Trainable / total | 40,370,176 / 4,393,342,464 (**0.9189%**) |
| Base frozen (non-LoRA trainable) | Yes (`no_non_lora_trainable_strict=True`) |
| Optimizer | `paged_adamw_8bit` |
| LR / warmup / scheduler / clip | 2e-4 / 0.03 / linear / 1.0 (PILOT settings) |
| Seed | 42 |

## Stage A — balanced tiny overfit

| Field | Value |
|-------|-------|
| N | 32 (16 pos / 16 neg), TRAIN only |
| Optimizer steps | 20 (early stop on 32/32 twice) |
| Initial → final loss | 7.838 → 0.044 |
| Accuracy | **32/32** |
| NaN / Inf | No |
| LoRA grads (all families) | Non-zero |

### Checkpoint roundtrip

| Field | Value |
|-------|-------|
| Verdict | PASS |
| Max \|Δp\| | 0.00221 |
| Tolerance | 0.02 (NF4+bf16; documented) |
| Hard predictions match | Yes |

## Stage B — natural-imbalance pilot

| Field | Value |
|-------|-------|
| Start | Fresh base + fresh LoRA (not Stage-A adapter) |
| N | 2048 |
| Positives / negatives | 174 / 1874 |
| Prevalence | 0.0850 (~ train natural) |
| Projects | **21 / 21** |
| Optimizer steps | 128 (one pass, eff. batch 16) |
| Initial → final loss | 6.480 → 0.482 |
| NaN / Inf | No |

## Validation (full frozen valid)

| Field | Value |
|-------|-------|
| N | 5465 |
| Positives | 467 |
| Prevalence / PR baseline | 0.0855 |
| ROC-AUC | **0.7778** |
| PR-AUC | **0.2181** (> prevalence) |
| F1 @ 0.5 | 0.0 |
| Precision / recall @ 0.5 | 0.0 / 0.0 |
| Balanced accuracy @ 0.5 | 0.5 |
| Brier | 0.0751 |
| Positive prediction rate @ 0.5 | 0.0 |
| Both hard classes @ 0.5 | **NO** (all predicted negative) |

Continuous ranking still separates classes (positives have higher mean/median `p_buggy` than negatives). Single-class hard predictions at 0.5 are expected under calibrated-low scores after natural-prevalence pilot; not treated as pipeline failure given Stage A + ranking metrics.

### Threshold diagnostic (PILOT_DIAGNOSTIC_ONLY)

| Field | Value |
|-------|-------|
| Threshold (max F1) | ≈ 0.0817 |
| F1 / P / R | 0.332 / 0.250 / 0.495 |
| Frozen for final experiment? | **No** |
| Applied to test? | **No** |

## Pilot signal

**ADEQUATE** — ROC-AUC ≫ chance; PR-AUC ≫ validation prevalence (0.218 vs 0.085).

## GPU / memory / throughput

| Field | Value |
|-------|-------|
| GPU | NVIDIA GeForce RTX 4090 |
| Base load allocated | ≈ 7.39 GiB |
| Stage A peak allocated / reserved | ≈ 13.04 / 22.13 GiB |
| Stage B peak allocated / reserved | ≈ 13.25 / 21.83 GiB |
| Stage B examples/sec | ≈ 0.76 |
| Validation examples/sec | ≈ 2.33 |

## Prohibitions respected

- No test inference / test metrics
- No imbalance strategy search
- No full 16374 training
- No attribution / M2 / M3 / baselines
- No change to frozen data/representation/prompt/token IDs

## Artifacts

- `artifacts/pilot_training/m1_pilot_summary.json`
- `artifacts/pilot_training/stage_a_curve.csv`
- `artifacts/pilot_training/stage_b_curve.csv`
- `artifacts/pilot_training/validation_metrics.json`
- `artifacts/pilot_training/validation_score_summary.json`
- `artifacts/pilot_training/checkpoint_hashes.json`
- Adapters (gitignored): `stage_a_adapter/`, `stage_b_adapter/`

## Next gate

`FULL_TRAINING_GATE` (not started).

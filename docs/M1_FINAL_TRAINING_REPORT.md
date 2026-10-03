# M1 Final Training Report
**Gate:** FULL_TRAINING_GATE  
**Verdict:** PASS  
**Date:** 2026-10-03T08:09:02+02:00  
## 1. VERDICT

PASS — three seeds completed; thresholds frozen before test; `M1_TEST_LOCKED=TRUE`.
## 2. FROZEN PROTOCOL

- Class policy: `NATURAL_PREVALENCE`
- Checkpoint: validation PR-AUC (tie: higher ROC-AUC, earlier epoch)
- Threshold: validation F1 at distinct scores (tie: F1 → recall → lower t)
- Epochs: 2; test once per seed after freeze
## 3. IMBALANCE DECISION

NATURAL_PREVALENCE — no oversample/undersample/class weights/focal for primary M1.
## 4. MODEL / REVISION

`Qwen/Qwen2.5-Coder-7B-Instruct` @ `c03e6d358207e414f1eca0bb1891e29f1db0e242`
## 5. CONFIG HASH

`7f51052379822e8261bbd738f164035474029e75c2c1eda997c3f5dcfec418c2`
## 6. SEEDS

13, 42, 73 (frozen before runs)
## 7. TRAINING HEALTH

### Seed 13
- epoch 1: steps=1024 loss 3.0100→0.3230 NaN/Inf=False median_gn=0.5111 max_gn=7.2237
- epoch 2: steps=1024 loss 0.2306→0.1958 NaN/Inf=False median_gn=0.5979 max_gn=2.6206
### Seed 42
- epoch 1: steps=1024 loss 3.4009→0.3258 NaN/Inf=False median_gn=0.5074 max_gn=5.8077
- epoch 2: steps=1024 loss 0.1758→0.1973 NaN/Inf=False median_gn=0.6703 max_gn=4.1456
### Seed 73
- epoch 1: steps=1024 loss 6.7959→0.3339 NaN/Inf=False median_gn=0.5136 max_gn=5.5009
- epoch 2: steps=1024 loss 0.0376→0.1968 NaN/Inf=False median_gn=0.6950 max_gn=5.6566

## 8–9. EPOCH VALIDATION

| seed | epoch | ROC-AUC | PR-AUC |
|---|---|---|---|
| 13 | 1 | 0.8472 | 0.3202 |
| 13 | 2 | 0.8588 | 0.3340 |
| 42 | 1 | 0.8339 | 0.3179 |
| 42 | 2 | 0.8461 | 0.3114 |
| 73 | 1 | 0.8444 | 0.3202 |
| 73 | 2 | 0.8476 | 0.3094 |

## 10. CHECKPOINT SELECTION

- seed 13: epoch 2 (valid PR-AUC=0.3340, ROC-AUC=0.8588)
- seed 42: epoch 1 (valid PR-AUC=0.3179, ROC-AUC=0.8339)
- seed 73: epoch 1 (valid PR-AUC=0.3202, ROC-AUC=0.8444)

## 11. THRESHOLD SELECTION

- t_13=0.123713 F1=0.4209 P=0.3309 R=0.5782
- t_42=0.152914 F1=0.3934 P=0.3103 R=0.5375
- t_73=0.146357 F1=0.3952 P=0.3140 R=0.5332

## 12. TEST-LOCK PROCEDURE

Threshold frozen in `THRESHOLD_FROZEN.json` before `--final-test`. Each seed evaluated exactly once; `TEST_EVALUATED.json` written; `M1_TEST_LOCKED=TRUE`.

## 13. PER-SEED TEST RESULTS

| seed | ROC-AUC | PR-AUC | F1 | P | R | balAcc | MCC | Brier |
|---|---|---|---|---|---|---|---|---|
| 13 | 0.8161 | 0.2528 | 0.3458 | 0.2555 | 0.5347 | 0.6934 | 0.2825 | 0.0739 |
| 42 | 0.8028 | 0.2469 | 0.3387 | 0.2598 | 0.4863 | 0.6774 | 0.2708 | 0.0714 |
| 73 | 0.8076 | 0.2471 | 0.3403 | 0.2582 | 0.4989 | 0.6814 | 0.2734 | 0.0712 |

## 14. THREE-SEED AGGREGATE

- roc_auc: 0.8088 ± 0.0067
- pr_auc: 0.2489 ± 0.0033
- f1: 0.3416 ± 0.0037
- precision: 0.2578 ± 0.0022
- recall: 0.5067 ± 0.0251
- balanced_accuracy: 0.6841 ± 0.0083
- mcc: 0.2756 ± 0.0061
- brier: 0.0722 ± 0.0015
- threshold: mean=0.140995 SD=0.015321 range=[0.123713,0.152914]

## 15. PILOT-vs-FINAL SANITY

Pilot Stage-B valid: ROC=0.7778 PR=0.2181

- seed 13 selected valid: ROC=0.8588 PR=0.3340
- seed 42 selected valid: ROC=0.8339 PR=0.3179
- seed 73 selected valid: ROC=0.8444 PR=0.3202

Full-train selected checkpoints should not collapse near chance; see values above.

## 16. GPU / COMPUTE

- seed 13 ep1: 0.7752200154291914 ex/s; peak alloc 13.07621955871582 GiB; reserved 21.40234375 GiB
- seed 13 ep2: 0.7557783683427338 ex/s; peak alloc 13.07607364654541 GiB; reserved 17.1953125 GiB
- seed 42 ep1: 0.7879116499800343 ex/s; peak alloc 19.347602367401123 GiB; reserved 22.12109375 GiB
- seed 42 ep2: 0.7766720546464058 ex/s; peak alloc 13.072182178497314 GiB; reserved 15.765625 GiB
- seed 73 ep1: 0.7882898756513858 ex/s; peak alloc 13.076218605041504 GiB; reserved 22.404296875 GiB
- seed 73 ep2: 0.7998935150036122 ex/s; peak alloc 13.07563829421997 GiB; reserved 17.181640625 GiB

## 17. CHECKPOINT HASHES

Recorded in `artifacts/m1_final/checkpoint_hashes.json`.

## 18. TEST CONTAMINATION AUDIT

- Test loaded only under `--final-test`
- Threshold freeze precedes test per seed
- No hyperparameter change after test
- Consistency: {'same_config_hash': True, 'config_hashes': ['7f51052379822e8261bbd738f164035474029e75c2c1eda997c3f5dcfec418c2'], 'seeds': [13, 42, 73], 'class_policies': ['NATURAL_PREVALENCE']}

## 19. LIMITATIONS

- Primary M1 uses natural prevalence; threshold calibrated on validation F1.
- @0.5 metrics are FIXED_0.5_DIAGNOSTIC only.
- No formal bootstrap model comparison in this gate.

## 20. FULL_TRAINING_GATE

PASS

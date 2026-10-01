# Table / figure schemas (placeholders = NA/TBD, never 0 for unknown)

## Table 1 — Dataset / cohorts

| Field | Value |
|-------|-------|
| train / valid / test | 16374 / 5465 / 5480 |
| ORIGINAL_RQ1_COHORT | 475 |
| PRIMARY_RQ1_N | 413 |
| RQ1_VISIBLE_N_2048 | 304 |
| predictive metrics | TBD |
| attribution metrics | TBD |

## Table 2 — Predictive performance by model

Columns: model, seed, split, PR-AUC, ROC-AUC, F1@thr, …  
Cells for final M1: **TBD** (FULL_TRAINING_GATE in progress). Never fill with 0.

## Table 3 — RQ1 localization

Columns: method, ranking_transform, Top-1/5/10, IFA, R@20%E, E@20%R, N.  
Values: **TBD**.

## Table 4 — RQ2 faithfulness

Columns: method, score_space, fraction, comprehensiveness, sufficiency_*.  
Values: **TBD**.

## Table 5 — RQ3 polarity

Columns: method, epsilon, frac+/−/0, sign_agreement_vs_occlusion.  
Values: **TBD**.

## Table 6 — Ablations

Columns: factor (context, max_len, aggregation, baseline, …), metric, value.  
Values: **TBD**.

Machine-readable stub: see `docs/schemas/tables_v0.json`.

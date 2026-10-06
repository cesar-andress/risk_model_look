# CONTEXT4096_DENOMINATOR_AUDIT.md

Task: EMSE-FINAL-ANALYSIS-CLOSURE  
Date (UTC): 2026-10-06  
Source: `artifacts/emse_final/emse_final_diagnostics.json` / `artifacts/test_attribution/cohorts/COHORT_INTEGRITY.json`

## Resolution

**DIFFERENT_DENOMINATORS_BOTH_VALID**

Correct manuscript reporting:

- Eligible 4096 fully-visible RQ1 cohort: **N = 345** (protocol `rq1_ablation_4096_fully_visible`).
- Paired Attention vs Grad×Input analysis after ≥2 common-valid seeds: **N = 288**.

Occlusion was not run at 4096.

## Trace

| Quantity | Value | Meaning |
|----------|-------|---------|
| Protocol / cohort list | 345 | Commits fully visible at 4096 under POLICY_A |
| Attention ≥2 valid seeds with Recall@20 | 288 | Method-valid support |
| Grad×Input ≥2 valid seeds | 288 | Method-valid support |
| Paired common-valid contrast | 288 | `n_included`; `n_excluded` = 0 in the paired object because candidates were already the overlapping valid set |
| Jobs expected att+gxi | 345 × 3 × 2 = 2070 | Planned raw jobs |

Earlier manuscript text that used **345** as the *paired contrast* N without stating the 288 common-valid support was **stale as a contrast denominator**, not as a cohort size.

## Manuscript rule

Always pair the two numbers: cohort 345; paired inferential N 288. Do not pick one.

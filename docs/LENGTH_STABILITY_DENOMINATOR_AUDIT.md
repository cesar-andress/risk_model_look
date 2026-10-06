# LENGTH_STABILITY_DENOMINATOR_AUDIT.md

Date (UTC): 2026-10-06  
Diagnostic: POST-HOC length association and length-adjusted seed stability  
Script: `scripts/emse_final_diagnostics.py` (`MIN_LINES_RHO = 5`)  
Canonical artifact: `artifacts/emse_final/emse_final_diagnostics.json` → `seed_stability`

## Starting N

RQ1 primary fully visible mapped TEST cohort: **304** (`cohorts/COHORT_INTEGRITY.json` `rq1_primary_304`).

## Filters (Attention / Grad×Input length-stability support)

Counted 2026-10-06 from the same tokenizer, 2048 encoding, and RQ1 status filter as the diagnostic.

| Step | Rule | Remaining | Removed |
|------|------|-----------|---------|
| 0 | RQ1 primary cohort | 304 | — |
| 1 | At least one RQ1 candidate line after 2048 drop | 304 | 0 empty |
| 2 | At least **five** RQ1 candidate lines (`MIN_LINES_RHO`) | **202** | **102** with 1–4 candidates |
| 3 | ≥2 valid attention seeds with `line_scores_sum` | 202 | 0 |
| 4 | All three seeds valid (observed) | 202 | 0 |

Spearman of attribution vs payload-token length additionally requires non-zero variance in both vectors; the reported `n_commits=202` matches step 2.

## Occlusion stability denominators

Same ≥5-line RQ1 universe (202) as Attention/Grad×Input, but occlusion seed-pair
support is thinner:

| Quantity | `n_commits` in diagnostics | Notes |
|----------|----------------------------|-------|
| Occlusion **length-adjusted** mean ρ | **199** | Canonical denominator for the length-residualized stability column |
| Occlusion **raw** mean ρ | **189** | Stricter: commit enters the commit-mean only if ≥2 seed-pairs have finite rank correlation (constant ranks / missing jobs / ID mismatches drop pairs) |

Manuscript Table (stability) reports occlusion length-adjusted **N=199** alongside
the raw and length-adjusted means from this diagnostic object.

## Why 304 ≠ 202

The primary RQ1 localization tables remain **N=304** (no five-line filter).  
Length correlation and residualized seed stability are undefined or noisy on 1–4-line diffs; the lock therefore required ≥5 lines. This is a **POST-HOC diagnostic denominator**, not a silent change of the primary cohort.

## Manuscript rule

State both: primary RQ1 **N=304**; length/stability diagnostic **N=202** for
Attention/Grad×Input; occlusion length-adjusted **N=199** (raw **N=189**).

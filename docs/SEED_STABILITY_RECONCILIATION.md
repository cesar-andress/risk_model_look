# SEED_STABILITY_RECONCILIATION.md

Date (UTC): 2026-10-06  
Resolution: **BOTH_VALID_DIFFERENT_ANALYSES**

Neither report is a computational error. They are two descriptive analyses of seed-to-seed rank agreement.

## Analysis A — TEST all-line descriptive (forensic-corrected TEST freeze)

Source: `artifacts/test_attribution/metrics/stability/seed_stability.json`  
Script: `scripts/summarize_test_attribution.py`  
Population: gold-positive TEST commits (`positive_475`), not the RQ1-304 subset.  
Lines: intersection of attributed `line_scores_sum` keys with at least two overlapping IDs (`len(common) < 2` skipped). Not restricted to RQ1 candidate labels. No minimum of five lines.  
Aggregator: mean Spearman across commits **within each seed pair**, reported separately (13–42, 13–73, 42–73).  
Support: `n_aligned` ≈ 473 per pair for attention / Grad×Input / occlusion.

Approximate mean ρ:

| Method | 13–42 | 13–73 | 42–73 |
|--------|-------|-------|-------|
| Attention | 0.607 | 0.633 | 0.632 |
| Grad×Input | 0.189 | 0.178 | 0.140 |
| Occlusion | 0.243 | 0.257 | 0.327 |

These are the “≈0.14–0.19 / ≈0.24–0.33” figures.

## Analysis B — EMSE POST-HOC RQ1 length-adjusted diagnostic

Source: `artifacts/emse_final/emse_final_diagnostics.json` `seed_stability`  
Script: `scripts/emse_final_diagnostics.py`  
Lock: `docs/EMSE_FINAL_ANALYSIS_LOCK.md`  
Population: RQ1 primary **N=304**, then only commits with **≥5 RQ1 candidate lines** after 2048 truncation (`MIN_LINES_RHO=5`).  
Lines: RQ1 universe only (not `NOT_IN_RQ1_UNIVERSE`), ranked by `ranking_score(·, ABS_DESCENDING)`.  
Aggregator: Pearson correlation of ranks (Spearman) per seed pair; then **commit-level mean over pairs with ≥2 finite pairs**; then mean across commits.  
Length-adjusted variant: OLS residual of attribution ranks on payload-token length ranks.

| Method | Raw mean ρ | Length-adj. | N commits (length-adj.) |
|--------|------------|-------------|-------------------------|
| Attention | 0.608 | 0.430 | 202 |
| Grad×Input | 0.119 | 0.087 | 202 |
| Occlusion | 0.023 | 0.020 | 199 (raw mean uses 189) |

## Why Grad×Input / occlusion look weaker in B

B drops 102 of 304 RQ1 commits with 1–4 labelled candidates (see `docs/LENGTH_STABILITY_DENOMINATOR_AUDIT.md`). It also ignores non-RQ1 attributed lines (markup, message, paths) that Analysis A includes. Occlusion’s higher A-analysis ρ is therefore not comparable to B’s 0.023.

## Manuscript rule

Headline EMSE stability numbers 0.608 / 0.119 / 0.023 **must** be labelled as Analysis B (RQ1, ≥5 candidates). Analysis A may be cited as the broader TEST all-line descriptive.

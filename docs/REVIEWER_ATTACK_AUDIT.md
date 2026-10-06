# REVIEWER_ATTACK_AUDIT.md

Date: 2026-10-06. No new experiments.

| # | Objection | Class |
|---|-----------|--------|
| 1 | Single model / dataset; cannot generalize to LLMs | LIMITATION_ONLY (explicit scope) |
| 2 | Encoder baseline missing | LIMITATION_ONLY (DOCUMENTED_PROTOCOL_LIMITATION; not a silent win) |
| 3 | SUM aggregation confounds length | ANSWERED (length baseline, ρ, MEAN sensitivity; lesson survives) |
| 4 | RQ2 pairwise attention>GxI is the story | ANSWERED (headline is vs-random + criterion disagreement) |
| 5 | Numerical gate FAIL kills RQ2 | PARTIALLY_ANSWERED (gate remains FAIL; estimand-level D similar is POST-HOC) |
| 6 | IG nonconvergence hides failure | ANSWERED (method-specific missingness; N=2/3 exploratory) |
| 7 | Process labels are not explanation GT | ANSWERED (stated; RQ1 is localization/plausibility) |
| 8 | Perturbations are OOD | LIMITATION_ONLY (intervention-specific; random control same class) |
| 9 | Seed instability means no effects | ANSWERED (distinguish ranking ρ vs commit-level estimands) |
| 10 | Wilcoxon vs bootstrap disagreement on random | PARTIALLY_ANSWERED (reported both; not star-picked) |

Submission blockers: **NONE** (encoder/operator are documented limitations, not integrity failures).

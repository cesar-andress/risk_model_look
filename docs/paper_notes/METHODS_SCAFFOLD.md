# Methods notes — ATTRIBUTION_PROTOCOL_V1.2 (no Results)

Maps to `docs/ATTRIBUTION_PROTOCOL_V1_2.md` and
`docs/STATISTICAL_ANALYSIS_PROTOCOL_V1_1.md`.

## Explanandum and M1

Explanation target remains \(s(x)=\ell_1(x)-\ell_0(x)\).

## RQ1 construct

RQ1 measures **localization / plausibility relative to line labels**.
It does **not** by itself establish explanation faithfulness.
Cross-RQ claims must consider RQ1 jointly with RQ2
(`RQ2_ON_RQ1_PRIMARY_SUBSET`, N=304).

Primary confirmatory endpoint: **Recall@20%Effort**.
Top-k / IFA / Effort@20%Recall are secondary with bootstrap CIs.
Trivial baselines: line length, canonical order, random; ADD-first only if not degenerate.

## Attention

Evaluate **the attention configurations specified here** (last-layer mean-head;
last-4 mean sensitivity). Do not claim results for “attention in general”.

## Faithfulness (RQ2)

Primary cross-method construct: **absolute perturbation faithfulness**
(`ABS_DELETION_AOPC`) under PAYLOAD_BLANK_V1 with **token-budget** prefixes.
Directional positive-evidence drop is secondary and signed-methods-only.
Occlusion is a **perturbation reference** in RQ2 (not a confirmatory Holm competitor).

## Length confounding

Primary RQ2 budgets are visible payload tokens, not region counts.
Region-fraction analysis is sensitivity. Token-matched random controls are required.

## Populations

Primary RQ2–RQ4 conclusions apply to **defect-inducing** TEST commits (N=475).
A matched **negative diagnostic** cohort (N=475) uses a reduced method set.
Do not generalize automatically to all clean commits.

## RQ4

Report token share, absolute mass share, and **enrichment**
(mass share / token share). Category ablations provide causal Δs.
DIFF_POLARITY_SWAP is exploratory structural sensitivity only.
Test-file heuristics are deferred.

## IG

Combined absolute/relative completeness criterion near zero targets.
Common-complete-case sensitivity for IG missingness.

## Seeds and sanity

Report seed-pair ranking Spearman stability; do not hide instability by averaging.
Base-vs-adapter sanity is validation-only on a small subset.

## Validation rehearsal

64 validation positives rehearse the pipeline before any test attribution.
Technical acceptance only; no method cherry-picking by rehearsal scores.

## Comparators

Encoder baseline remains required. M2 deferred from core.
Second decoder optional; otherwise claim scope is the Qwen-based classifier.

## Statistics

One primary endpoint per RQ; frozen primary contrasts; Top-k not Wilcoxon-primary.
See `STATISTICAL_ANALYSIS_PROTOCOL_V1_1`.

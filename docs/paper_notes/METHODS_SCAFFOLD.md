# Methods notes — ATTRIBUTION_PROTOCOL_V1 (no Results)

Protocol-aligned Methods language for the manuscript. Every statement maps to
the frozen config / `docs/ATTRIBUTION_PROTOCOL_V1.md`.

## Explanandum and M1

The M1 risk score explanation target is the risk logit contrast
\(s(x)=\ell_1(x)-\ell_0(x)\) (RISK_LOGIT_CONTRAST_V1), not a probability or
full-vocabulary score.

## Attention

Attention is evaluated as an internal importance proxy / baseline. Raw
attention is not presumed to be a faithful explanation; prediction-level
faithfulness is tested separately (RQ2). Jain & Wallace (2019) and Wiegreffe &
Pinter (2019) frame this debate; neither paper is treated as a universal
verdict for this study.

Primary attention aggregation: last-layer mean-head at the first assistant
classification-token position, summed to lines. Final-4-layer mean attention is
a predeclared sensitivity analysis.

## RQ1 vs RQ3 separation

Primary RQ1 ranking for signed attributions uses absolute line scores
(ABS_DESCENDING): localization of influential evidence regardless of polarity.
Directional / polarity questions are reserved for RQ3. A secondary
signed-positive ranking is predeclared and must not replace the primary after
results are observed.

## Faithfulness

Primary faithfulness perturbations use the same logit-contrast scalar.
Restricted binary \(p_{\mathrm{buggy}}\) is a secondary reporting space.
Localization against line labels (RQ1) is distinct from perturbation
faithfulness (RQ2), following the ERASER conceptual separation (DeYoung et al.,
2020).

## Integrated Gradients

Primary IG uses an explicit ZERO_EMBEDDING baseline with Gauss–Legendre
integration (50 steps; adaptive retry to 100 with a relative completeness
tolerance of 0.05). ZERO_EMBEDDING is treated as a reproducible baseline, not
an unquestioned semantically neutral reference; PAD-token embedding provides a
mandatory baseline sensitivity. Baseline dependence will be assessed rather than
resolved by picking the better-looking setting post hoc.

## RQ1 population

Primary localization requiring a fully visible candidate universe uses the
CHANGED_ONLY / 2048 fully visible complete-case population (\(N=304\)). The
4096 fully visible population (\(N=345\)) is a predeclared ablation.

## Aggregation

Token→line reduction primary is SUM; MEAN is a length-sensitivity diagnostic.

## Statistical analysis (pre-result freeze)

Commits are the primary inference unit; the three M1 seeds are repeated model
realizations and are not flattened into independent seed×commit rows.
Pairwise method comparisons use two-sided Wilcoxon signed-rank tests (Pratt
zero handling) on commit-level mean paired differences over common-valid seeds
(minimum two). Family-wise error is controlled by Holm correction within RQ
families. Confidence intervals use 10 000 commit-cluster percentile bootstrap
resamples. The primary paired effect size is the matched-pairs rank-biserial
correlation; Cliff's δ is legacy/secondary only. See
`docs/STATISTICAL_ANALYSIS_PROTOCOL_V1.md`.

# EMSE_FINAL_ANALYSIS_LOCK.md

Status: **FROZEN before new diagnostic outputs**  
Task: `EMSE-FINAL-ANALYSIS-CLOSURE-AND-MANUSCRIPT-REFRAME`  
Timestamp (UTC): 2026-10-06T10:55:00Z  
Canonical branch: `main`  
Parent HEAD: `265e45573a0e6d934e7fc0a2d65803ebe5987118`  
Venue target: **Empirical Software Engineering (EMSE)**  
Runner-up: IST. Third: JSS. **TOSEM is closed.** Do not restore it.

Parent corrected TEST freeze SHA-256: `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19`  
Parent corrective commit: `b9e59faa71435f31a656fd52b87481ec7e14a39c`  
TOSEM extension lock: `docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md` / `840bb45eda317908d7f953e67f27dafbad1c5cf6` / `855415e785b41d3a6a233b33fb624da76cc35f48f7beedbe13b16498aca31540`  
Parent extension freeze: `artifacts/tosem_extension/TOSEM_EXTENSION_RESULTS_FREEZE.json` / SHA-256 `5e5c67e068a668f046ca2c1efe04a6b03f1a147bb3f09ded54a1b9710561df9b`  

**NUMERICAL_GATE remains FAIL.** This lock does not create a replacement gate.

Score \(s=\ell_1-\ell_0\) (LOGIT_CONTRAST). Model: frozen M1 Qwen2.5-Coder-7B-Instruct QLoRA NF4, seeds {13,42,73}. IG closed.

## Stop rule

After the CLOSED list A–K below, no additional empirical analysis is authorized except to repair a data-integrity error, a numerical inconsistency, or an untraceable manuscript number. Reviewer interest is not sufficient. New hypotheses go to future work.

## Prohibited

Second decoder; second dataset; new attribution method; more seeds; IG rerun; new model family; new training; new broad perturbation sweep; new numerical pass/fail gate; TOSEM track restoration.

GPU is **not** authorized in this task. Encoder training is **not** authorized unless an executable frozen recipe is reconstructed without new choices (it is not; see Phase 1).

## Line-length definition (frozen before computation)

Canonical line length = number of **model-visible payload tokens** assigned to that source line on the 2048 encoding (`region_token_counts` / B_LENGTH definition in `src/metrics/rq1_baselines.py`). Do not switch to characters or non-whitespace tokens after seeing results.

## Residualization (Phase 5; frozen)

For each commit and seed pair with a common RQ1 candidate universe of size \(\ge 5\):

1. Rank lines by `ranking_score(·, ABS_DESCENDING)` for seed A and seed B (average ranks for ties).
2. Rank the same lines by payload-token length (average ranks for ties).
3. OLS-residualize each seed’s attribution rank vector on the length-rank vector (add intercept).
4. Pearson correlation of the two residual vectors is the length-adjusted cross-seed agreement for that commit×pair.
5. Aggregate as mean across commits of the three seed-pairs, requiring \(\ge 2\) seed-pairs with finite correlation.

Same implementation for attention, Grad×Input, and occlusion. No per-method tuning.

## MEAN aggregation (Phase 4; frozen)

Use stored `line_scores_mean` from existing TEST jobs (token MEAN already computed at attribution time). Do not re-infer. Primary SUM remains `line_scores_sum`. MEAN is **POST-HOC CONSTRUCT SENSITIVITY**.

## Multiplicity

Planned confirmatory Holm families are **not** modified. RQ1 B_LENGTH / B_ORDER / B_RANDOM were pre-specified as trivial baselines (`trivial_baselines_included` in Stats V1.1). Method-vs-baseline Wilcoxon/CI/rank-biserial are reported as **PROTOCOL-OWED BASELINE** quantities and are **not** merged into the original RQ1 Holm family of method-vs-method contrasts. Length-association, residualized stability, occlusion agreement, estimand-level numerical D, and TP/FN baseline context are **POST-HOC DIAGNOSTIC** unless a frozen protocol already defined them.

## Authorized closed list

A. Grad×Input vs random/length/order RQ1 (existing data; N=304 when method-valid).  
B. Occlusion vs random/length/order RQ1 (same).  
C. Attribution vs line-length Spearman within commit×seed (payload-token length).  
D. SUM vs MEAN Recall@20 sensitivity from stored line scores.  
E. Length-adjusted seed stability (residual ranks, above).  
F. Within-seed Spearman agreement of Attention and Grad×Input with occlusion.  
G. Descriptive estimand-level \(D_{\mathrm{bf16}}\) vs \(D_{\mathrm{fp32}}\) from existing numerical rows / original AOPC; **no new gate**.  
H. TP/FN stratum-specific random/length baselines for Attention (and GxI/occlusion if support permits).  
I. 4096 denominator reconciliation (345 vs 288).  
J. Float32 path provenance from code/lock (rankings reused vs recomputed).  
K. Encoder and operator-sensitivity resolution documents.

Nothing else.

## Official NUMERICAL_GATE wording (unchanged)

NUMERICAL_GATE = FAIL because \(|\text{mean paired RQ2 } \Delta|\) did not exceed median \(|s_{\mathrm{bf16}}-s_{\mathrm{fp32}}|\). Aggregate AOPC \(\Delta\) similarity across paths is POST-HOC INTERPRETATION only.

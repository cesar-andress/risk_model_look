# EMSE_FINAL_CLAIM_LEDGER.md

Freeze parent TEST: `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19`  
Diagnostics: `artifacts/emse_final/emse_final_diagnostics.json`  
NUMERICAL_GATE: FAIL  

Every Results claim must map here. Unsafe claims are omitted from the manuscript.

---

## L1. RQ1 method vs method (planned)

CLAIM: After Holm adjustment, Attention vs Grad×Input and Attention vs occlusion Recall@20 contrasts are not significant at α=0.05.  
RQ: RQ1  
EVIDENCE TYPE: PRESPECIFIED  
POPULATION: fully visible mapped TEST commits  
N: 304  
ESTIMATE / CI / rrb: Att−GxI Holm 0.6346210157258283, rrb=0.11956015282825459; Att−occ Holm 0.10621325463136139, rrb=0.19317906957994033  
SOURCE: `artifacts/test_attribution/statistics/rq1_stats.json`  
SAFE WORDING: Planned method-vs-method Holm tests on Recall@20 do not reject at α=0.05; intervals are not equivalence tests.  
LIMITATION: Does not imply methods are interchangeable.  
STATUS: SUPPORTED

## L2. Length baseline (central)

CLAIM: None of Attention, Grad×Input, or occlusion outperforms the payload-token line-length baseline on Recall@20 (paired Δ negative; CIs exclude 0 for all three).  
RQ: RQ1  
EVIDENCE TYPE: PROTOCOL-OWED  
N: 304  
Attention−length: −0.040019 [−0.076762, −0.003538] rrb=−0.1905 p_raw=0.146591  
GxI−length: −0.063451 [−0.101100, −0.026978] rrb=−0.2522 p_raw=0.006553  
Occ−length: −0.079981 [−0.124007, −0.036859] rrb=−0.2964 p_raw=0.002153  
SOURCE: `emse_final_diagnostics.json` `baseline_matrix`  
SAFE WORDING: A trivial ranking by visible payload-token length matches or exceeds the adequately supported attribution methods on Recall@20.  
STATUS: SUPPORTED

## L3. Order baseline

CLAIM: All three methods have higher Recall@20 than canonical order (CIs exclude 0).  
TYPE: PROTOCOL-OWED  
N: 304  
Att−order 0.070122 [0.031718, 0.108251] rrb=0.3785  
GxI−order 0.046689 [0.011470, 0.081687] rrb=0.2862  
Occ−order 0.030160 [0.004694, 0.055150] rrb=0.3037  
STATUS: SUPPORTED

## L4. Random baseline

CLAIM: Attention’s paired Δ vs 100-perm random has CI excluding 0; Wilcoxon-Pratt p=0.616. GxI and occlusion CIs include 0.  
TYPE: PROTOCOL-OWED  
N: 304  
Att−rand 0.042455 [0.015402, 0.070607] rrb=0.0477  
GxI−rand 0.019022 [−0.001382, 0.039382] rrb=0.0620  
Occ−rand 0.002493 [−0.022134, 0.027099] rrb=−0.1134  
SAFE WORDING: Under primary SUM aggregation, Attention exceeds the random localization baseline (CI excludes 0; Wilcoxon–Pratt does not); Grad×Input and occlusion do not. That SUM advantage does not persist under post-hoc MEAN aggregation (Attention mean R@20 0.291 vs random 0.312). Do not write aggregation-independent “Attention beats random.”  
STATUS: PARTIALLY_SUPPORTED

## L5. Length association

CLAIM: Within RQ1 candidate lines (≥5), Attention SUM scores correlate with payload-token length (median Spearman ρ=0.574, n_commits=202); GxI weaker (0.215); occlusion near 0 (0.071).  
TYPE: POST-HOC SENSITIVITY  
STATUS: SUPPORTED as association, not mechanism.

## L6. MEAN aggregation

CLAIM: MEAN token-to-line aggregation lowers Attention Recall@20 (0.355→0.291) and GxI (0.331→0.290); occlusion SUM=MEAN (line-level operator). MEAN vs length remains negative (Attention Δ=−0.104).  
TYPE: POST-HOC CONSTRUCT SENSITIVITY  
SAFE WORDING: Switching SUM→MEAN does not make methods outperform length.  
STATUS: SUPPORTED  
Structural-baseline lesson survives: YES (outcome A).

## L7. RQ2 vs random

CLAIM: Attention and Grad×Input both exceed token-matched random ABS_DELETION_AOPC.  
TYPE: PROTOCOL-OWED / robustness  
N: 472  
Att−rand 0.031868 [0.024894, 0.039129] rrb=0.4400  
GxI−rand 0.017015 [0.010505, 0.023702] rrb=0.2619  
STATUS: SUPPORTED

## L8. RQ2 Att vs GxI

CLAIM: Planned Holm contrast Att−GxI AOPC Δ=0.014853 [0.008011, 0.021694] N=472 rrb=0.224 Holm p=0.000144. Smaller than vs-random gaps. Not the headline.  
TYPE: PRESPECIFIED  
STATUS: SUPPORTED as a secondary pairwise contrast, not as “Attention is better” rhetoric.

## L9. Numerical gate

CLAIM: NUMERICAL_GATE=FAIL. Float32 scoring-only path Δ=0.015197 [0.008462, 0.021985] rrb=0.222. Median |Δs|=0.037056.  
POST-HOC: N=472 commit-level |D_bf16−D_fp32| mean 0.021129 median 0.016263 Spearman 0.904 sign agreement 82.4%.  
SAFE WORDING: The prospective gate failed because |mean AOPC Δ| did not exceed median |s| discrepancy. Rankings were not recomputed. Aggregate D was similar across compute dtypes (descriptive only).  
STATUS: SUPPORTED (gate FAIL); POST-HOC descriptive for estimand-level change.

## L10. Seed stability

CLAIM: On RQ1 lines ≥5, mean cross-seed ρ Attention 0.608 (length-adjusted 0.430); GxI 0.119 (0.087); occlusion 0.023 (0.020). Attention remains most stable after length adjustment.  
TYPE: POST-HOC DIAGNOSTIC (RQ1 ≥5-line universe, $N=202$; see `docs/SEED_STABILITY_RECONCILIATION.md` and `docs/LENGTH_STABILITY_DENOMINATOR_AUDIT.md`). Broader TEST all-line `seed_stability.json` is a different analysis ($n_{\mathrm{aligned}}\approx473$).  
STATUS: SUPPORTED as ranking instability, not as non-estimability of population means.

## L11. Occlusion agreement

CLAIM: Within-seed Spearman of ranks vs occlusion: Attention mean 0.084; GxI 0.014 (n_commits=202).  
TYPE: POST-HOC  
SAFE WORDING: Families do not identify the same lines; occlusion is not ground truth.  
STATUS: SUPPORTED

## L12. Polarity / RQ3

CLAIM: Confirmatory RQ3 family as executed has one member (Grad×Input signed vs absolute). Mean ΔRecall@20 GxI 0.003; not a large polarity gain. Negative-hit rates for GxI ≈0.47 at k=5/10.  
TYPE: PRESPECIFIED + DESCRIPTIVE  
STATUS: PARTIALLY_SUPPORTED (wording error if “each signed method” was confirmatory)

## L13. Surface cues / enrichment

CLAIM: Attention mass enrichment FILE_PATH 4.28; SPECIAL_TOKEN 3.19; COMMIT_MESSAGE 2.20 vs ADDED_CODE 0.65 (N=304). Descriptive.  
TYPE: PROTOCOL-OWED DESCRIPTIVE  
STATUS: SUPPORTED as descriptive enrichment, not as causal localization.

## L14. TP/FN

CLAIM: Attention Recall@20 TP n=97 mean 0.232 vs FN n=207 mean 0.412. FN diffs are smaller (mean 11.0 candidates vs 24.7; length baseline 0.460 vs 0.255).  
TYPE: POST-HOC  
SAFE WORDING: The TP/FN gap co-moves with structural size; not a primary contribution.  
STATUS: EXPLORATORY; interpretable PARTLY

## L15. 4096

CLAIM: Cohort N=345; paired Att vs GxI N=288; Δ=0.032885 [0.002034, 0.064285] p_raw=0.149 rrb=0.191  
TYPE: PRESPECIFIED sensitivity  
STATUS: SUPPORTED with dual denominators

## L16. IG

CLAIM: RQ1 N=2, RQ2 N=3, LOW_POWER_EXPLORATORY. Not confirmatory.  
STATUS: SUPPORTED as non-estimable for confirmation

## L17. Encoder / operator

CLAIM: Encoder not run (underspecified). RQ2 operator sensitivity not run (PAYLOAD_BLANK only).  
STATUS: UNSUPPORTED as completed analyses; documented limitations

## Unsafe (must not appear)

Attention is more faithful; IG confirms; methods equivalent; generalizes to LLMs; NUMERICAL_GATE_PASS; TOSEM-ready.

# TOSEM_EXTENSION_CLAIM_LEDGER.md

Gate: `TOSEM-EXTENSION-GATE-1`  
Parent corrected TEST freeze SHA-256: `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19`  
Extension freeze: `artifacts/tosem_extension/TOSEM_EXTENSION_RESULTS_FREEZE.json`  
Lock commit: `840bb45eda317908d7f953e67f27dafbad1c5cf6`  
IG closed. Numerical gate: **FAIL**. Manuscript Abstract/Conclusion not finalized.

Role tags: PRIMARY = forensic-corrected TEST; OWED = pre-specified completion; PROSPECTIVE = this lock; POST-HOC = labelled robustness.

---

## C1. RQ1 Attention vs Grad×Input Recall@20

- claim: No Holm-adjusted evidence that Attention and Grad×Input differ on primary RQ1 Recall@20.
- source: forensic-corrected `rq1_stats.json`
- pre-specified / prospective / post-hoc: pre-specified PRIMARY
- N: 304
- effect (mean paired Δ Attention−GxI): see freeze bootstrap in TEST stats (Holm p = 0.6346210157258283)
- CI: as in corrected freeze (includes 0 for this Holm-nonsignificant contrast; do not read as equivalence)
- effect size: rank-biserial 0.11956015282825459
- raw p / adjusted p: as freeze; Holm 0.6346210157258283
- robustness: 4096 ablation N=288 paired contrast p_raw=0.14933127140369587, rrb=0.19105046017137417
- manuscript-safe wording: On the 304-commit fully visible TEST cohort, the planned Attention vs Grad×Input Recall@20 contrast is not Holm-significant; the interval does not support a claim of superiority, and no equivalence margin was prospectively frozen.

## C2. RQ1 Attention vs occlusion Recall@20

- N: 304; Holm 0.10621325463136139; rank-biserial 0.19317906957994033
- role: pre-specified PRIMARY
- manuscript-safe wording: The planned Attention vs occlusion Recall@20 contrast is not Holm-significant after family adjustment.

## C3. RQ1 vs trivial baselines (owed)

- N: 304 commit unit
- B_LENGTH mean Recall@20: 0.39451224688884073
- B_ORDER: 0.2843718816686319
- B_RANDOM: 0.3120383124353343
- Attention vs B_LENGTH: Δ −0.040018820791057834, CI [−0.07690698991025774, −0.0033136757314070815], p_raw=0.14659086439420246, rrb=−0.19051454138702462
- Attention vs B_ORDER: Δ 0.07012154442915094, CI [0.03173009681806223, 0.10819659529603437], p_raw=1.1374784261765856e-06, rrb=0.37849079025549615
- Attention vs B_RANDOM: Δ 0.04245511366244853, CI [0.014464088222046458, 0.07079301949094426], p_raw=0.6159140888469415, rrb=0.04774831840255784
- Grad×Input and occlusion also lose to B_LENGTH (CI excludes 0) and beat B_ORDER.
- role: OWED BASELINE
- manuscript-safe wording: Adequately supported attribution methods do not uniformly beat trivial RQ1 baselines: length ranking matches or exceeds method Recall@20, while order ranking is worse. Wilcoxon p and bootstrap CI can disagree; do not treat non-rejection as equality.

## C4. RQ2 Attention vs Grad×Input ABS_DELETION_AOPC (original PRIMARY)

- N: 472
- effect: 0.01485257768361582
- CI: [0.008011122881355932, 0.02169403248587572]
- rank-biserial: 0.22405055170644086
- raw p: 7.181527188134527e-05; Holm: 0.00014363054376269053
- role: pre-specified PRIMARY (forensic-corrected freeze)
- robustness: common-cohort N=304 Δ 0.017064144736842105 CI [0.00839501096491228, 0.025664747807017545]; project-clustered CI [0.008050179834747484, 0.024664848777953073] on 21 projects
- numerical: float32 path Δ 0.015196705436975941 CI [0.008461699516928128, 0.02198519140987073], rrb=0.22249675140467431, same sign, CI excludes 0, but |Δ| 0.0152 does **not** exceed median |s_bf16−s_fp32| 0.03705596923828125
- manuscript-safe wording: The planned RQ2 Attention−Grad×Input AOPC contrast is Holm-significant on N=472, but the prospectively frozen numerical-path gate did not pass because the effect magnitude does not exceed the median execution-path discrepancy of the logit-contrast score s. Do not treat the original finding as robust to NF4 compute-dtype variation under that frozen criterion.

## C5. RQ2 token-matched random control (owed / 1-repeat freeze)

- N: 472
- Attention−random Δ 0.03186793785310735 CI [0.02489406779661017, 0.039129259357344626], rrb=0.4399873914546601
- Grad×Input−random Δ 0.017015360169491525 CI [0.010504943502824857, 0.023702330508474576], rrb=0.2618877668843029
- role: BASELINE / ROBUSTNESS (not merged into Holm)
- manuscript-safe wording: On the frozen one-repeat token-matched random ranking, both Attention and Grad×Input have higher ABS_DELETION_AOPC than the random control (CIs exclude 0).

## C6. Enrichment (owed descriptive)

- Attention RQ1 N=304 mean ATTRIBUTION_ENRICHMENT_C: FILE_PATH 4.278255112427914; SPECIAL_TOKEN 3.187135636260216; COMMIT_MESSAGE 2.2045030536055488; ADDED_CODE 0.6527608606796215
- role: DESCRIPTIVE
- manuscript-safe wording: Mean attention mass is enriched on file-path and special-token categories relative to added code; this is descriptive, not a causal localization claim.

## C7. Negative-hit rates (owed descriptive)

- Grad×Input @5 mean 0.4683874139626349 (n=226); @10 0.46787077426390405 (n=262)
- occlusion @5 0.2865804160324709 (n=219); @10 0.2677335835281572 (n=258)
- role: DESCRIPTIVE
- manuscript-safe wording: Among ranked positives in the top-k, a substantial fraction of Grad×Input hits are polarity-negative under the frozen epsilon; report both positive and negative evidence.

## C8. Matched-clean

- 475 commits × 3 seeds × attention/Grad×Input/occlusion DONE
- no gold RQ1 labels on clean; matching unchanged
- manuscript-safe wording: Cheap-method attributions exist on the matched-clean diagnostic set; they do not constitute RQ1 localization on negatives.

## C9. TP/FN stratification (POST-HOC)

- RQ1 Attention Recall@20: n_tp=97 mean 0.232; n_fn=207 mean 0.412; point-biserial −0.234
- role: POST-HOC ROBUSTNESS
- manuscript-safe wording: Among gold-positive RQ1 commits, mean Recall@20 is lower on true-positive predictions than on false negatives; strata are observational and not a primary estimand.

## C10. RQ3 family

- executed confirmatory family has one member (Grad×Input signed vs absolute)
- resolution: MANUSCRIPT_WORDING_ERROR if text implied every signed method
- do not expand family after seeing p-values

## C11. IG

- RQ1 N=2; RQ2 N=3; RQ3 secondary N=2; LOW_POWER_EXPLORATORY
- exact small-n Wilcoxon uninformative for confirmation
- not rerun; validity rules unchanged

## Prohibited claims

- Do not claim RQ2 is robust to numerical path.
- Do not claim attribution beats length.
- Do not claim RQ1 methods are equivalent.
- Do not claim TOSEM-ready.
- Do not execute a second decoder on the basis of this gate.

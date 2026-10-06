# AMENDMENT_AND_PROVENANCE_LOG.md

Public provenance trail (not a Results narrative).

| Object | Identifier |
|--------|------------|
| Original TEST freeze (superseded) | SHA-256 `8caad443f4a69d7040ae7e966053e12f83f33ce9dc11eb2ea029818ecc68ec95` |
| Reason for correction | IG valid-seed mask used a non-method-specific aggregation |
| Corrective commit | `b9e59faa71435f31a656fd52b87481ec7e14a39c` |
| Corrected TEST freeze | SHA-256 `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19` |
| Prospective robustness-extension protocol file | `docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md` commit `840bb45eda317908d7f953e67f27dafbad1c5cf6` SHA-256 `855415e785b41d3a6a233b33fb624da76cc35f48f7beedbe13b16498aca31540` (historical filename; venue is EMSE) |
| Extension results freeze | `artifacts/tosem_extension/TOSEM_EXTENSION_RESULTS_FREEZE.json` SHA-256 `5e5c67e068a668f046ca2c1efe04a6b03f1a147bb3f09ded54a1b9710561df9b` |
| NUMERICAL_GATE | **FAIL** |
| Float32 path | **SCORING_ONLY** |
| EMSE final-analysis lock | `docs/EMSE_FINAL_ANALYSIS_LOCK.md` commit `aba73ea63f3534acc292e4e4640dfa53ec22bcf6` SHA-256 `7e54a8f394be36b0958cf7d8b9bf8e36121930b9d981b0bcce0e2496557e81dd` |
| Final EMSE evidence freeze | `artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json` SHA-256 `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78` |
| Venue | EMSE |

## IG aggregation bug + correction

Pre-result IG validity used a non-method-specific mask. Corrected TEST freeze `a707e8e7…` at commit `b9e59fa`. Raw jobs were not overwritten. IG was not rerun.

## RQ wording reframe

**POST_OUTCOME_NARRATIVE_REWORDING.** Frozen estimands unchanged. Manuscript RQs were regrouped after results to foreground criterion disagreement. Not a change of Holm families.

## Encoder comparator

**PRE_SPECIFIED_BUT_UNDERSPECIFIED_LIMITATION.** `ENCODER_BASELINE = REQUIRED` before TEST; no executable recipe. Not executed.

## Operator sensitivity (SEGMENT_DELETE perturbation)

**PRE_SPECIFIED_BUT_UNDERSPECIFIED_LIMITATION.** Not executed. No new GPU.

## Random-control repeats

- RQ1 B_RANDOM: **100** permutations planned and executed.
- RQ2 token-matched random: extension protocol froze **1** ranking per commit×seed (not 100 GPU repeats). **OUTCOME_BLIND_PROTOCOL_SPECIFICATION** relative to that GPU run; not a post-outcome reduction of 100 to 1 after seeing AOPC.

## RQ3 family

Planned signed-versus-absolute ΔRecall@20 for signed methods. Estimable confirmatory member at N=304: Grad×Input. IG remains a family member at N=2 (LOW_POWER_EXPLORATORY). Occlusion signed vs absolute is not a distinct line-level contrast.

## 475 → 472

Primary RQ2 cohort is 475 defect-inducing TEST commits. Planned Attention vs Grad×Input AOPC uses N=472 because three commits have attention PAYLOAD_BLANK `missingness_code=OOM` on all seeds: `e21d4d43…`, `ab1ee1b6…`, `c4193c6e…`.

## MEAN aggregation vs length–attribution correlation

MEAN token-to-line reduction: **PRE_SPECIFIED_DIAGNOSTIC** in Attribution Protocol V1.2 (`line_reduction_sensitivity: MEAN` before TEST). The later analysis lock labelled MEAN as POST-HOC construct sensitivity; that lock file is not rewritten (its SHA-256 is frozen). The manuscript follows the earlier protocol: MEAN is a pre-specified construct sensitivity. Length–attribution Spearman on RQ1 ≥5 lines: **POST_HOC_DIAGNOSTIC**.

## Planned-but-unreported accounting

See manuscript Appendix `app:planned`. Secondary Top-k/IFA/Effort@20%Recall aggregated from frozen job `rq1` fields (no new rankings).

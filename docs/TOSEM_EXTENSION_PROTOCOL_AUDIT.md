# TOSEM_EXTENSION_PROTOCOL_AUDIT.md

Gate: `TOSEM-EXTENSION-GATE-1`  
Audit date (UTC): 2026-10-06T05:57:56Z  
Canonical branch: `main`  
HEAD at audit: `b9e59faa71435f31a656fd52b87481ec7e14a39c`  
Parent corrected TEST freeze SHA-256: `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19`  
Superseded freeze (provenance only): `8caad443f4a69d7040ae7e966053e12f83f33ce9dc11eb2ea029818ecc68ec95`

Ordering evidence: ATTRIBUTION_PROTOCOL_V1.2 / STATISTICAL_ANALYSIS_PROTOCOL_V1.1 committed `3fa90ded20e268fc7c3a88ee05896f92e63af2d1` on 2026-10-01 (before TEST attribution freeze `03be67d` and forensic repair `b9e59fa`).

This audit distinguishes protocol-owed items from post-hoc sensitivities. It does not change scientific definitions. IG is closed.

---

## 1. encoder baseline

ITEM: encoder baseline  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2 §Model scope; `configs/attribution/m1_methods_v1_2.yaml` `ENCODER_BASELINE: REQUIRED`; DECISION_LOG 2026-10-01  
SOURCE_VERSION: V1.2 / `c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c`  
SOURCE_COMMIT: `3fa90ded20e268fc7c3a88ee05896f92e63af2d1`  
TIMESTAMP / ORDERING EVIDENCE: 2026-10-01T22:37:51+02:00, before TEST  
PRE_SPECIFIED: YES (requirement) / UNCLEAR (executable recipe)  
CURRENT_STATUS: NOT_RUN  
NEW_GPU_COMPUTE_REQUIRED: YES (full second-model training + evaluation)  
SCIENTIFIC_ROLE: BASELINE  

Notes: EXPERIMENT_PROTOCOL_V0 leaves identity as “CodeBERT or UniXcoder — subject to later protocol verification”. No frozen encoder checkpoint, QLoRA recipe, or attribution contract exists at V1.2 specificity. Executing now would invent architecture. This gate does **not** execute a new encoder. Incomplete owed item at recipe level.

---

## 2. RQ1 random baseline

ITEM: B_RANDOM  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2 trivial baselines; STATISTICAL_ANALYSIS_PROTOCOL_V1.1 `trivial_baselines_included`; ATTRIBUTION_PROTOCOL_V1 §15 (100 deterministic perms); `src/stats/paired.py` `collapse_random_baseline_perms`  
SOURCE_VERSION: V1 / V1.2 / Stats V1.1  
SOURCE_COMMIT: `3fa90ded…` (V1.2); V1 historically frozen  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE (line scores + RQ1 labels in TEST attribution jobs; baseline rankings not yet aggregated)  
NEW_GPU_COMPUTE_REQUIRED: NO (CPU permutations of existing candidate universes)  
SCIENTIFIC_ROLE: BASELINE  

---

## 3. RQ1 length baseline

ITEM: B_LENGTH  
SOURCE_PROTOCOL: same as §2; `src/metrics/rq1_baselines.py` `length_baseline_scores`  
SOURCE_VERSION: V1.2  
SOURCE_COMMIT: `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: BASELINE  

---

## 4. RQ1 order baseline

ITEM: B_ORDER  
SOURCE_PROTOCOL: same as §2; `order_baseline_scores`  
SOURCE_VERSION: V1.2  
SOURCE_COMMIT: `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: BASELINE  

---

## 5. RQ2 token-matched random control

ITEM: token-matched random perturbation control  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1 §15 (“RQ2: length/candidate-count matched”); ADVERSARIAL_REVIEW_RESPONSE C2 ACCEPTED; `src/metrics/token_budget_faithfulness.py` `token_matched_random_regions`  
SOURCE_VERSION: V1 (pre-TEST); V1.2 preserved TOKEN_BUDGET_PREFIX_V1  
SOURCE_COMMIT: V1 freeze + `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: NOT_RUN (faith jobs store PAYLOAD_BLANK AOPC for attributed rankings only; no random control field)  
NEW_GPU_COMPUTE_REQUIRED: YES (score blanked inputs)  
SCIENTIFIC_ROLE: BASELINE / ROBUSTNESS  

Notes: V1 specifies 100 repeats for **RQ1** random, not for RQ2. RQ2 freeze in this extension uses **1** canonical token-matched random ranking per commit×seed (seed derived from protocol hash), not 100 GPU repeats.

---

## 6. RQ2 perturbation-operator sensitivity

ITEM: PAYLOAD_BLANK vs SEGMENT_DELETE as perturbation operators  
SOURCE_PROTOCOL: STATISTICAL_ANALYSIS_PROTOCOL_V1 §5 `SEGMENT_DELETE operator: RQ2_SENSITIVITY`; Stats V1.1 `OPERATOR_DEPENDENCE_DIAGNOSTIC` secondary  
SOURCE_VERSION: V1 / V1.1  
SOURCE_COMMIT: statistical protocol freeze; `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES (secondary/sensitivity)  
CURRENT_STATUS: NOT_RUN as a two-operator contrast. TEST faith uses `apply_payload_blank_record` only. Job flag `SEGMENT_DELETE_V1: true` is not evidence that structured deletion was the perturbation operator (occlusion uses SEGMENT_DELETE as **attribution** operator).  
NEW_GPU_COMPUTE_REQUIRED: YES (full second operator sweep)  
SCIENTIFIC_ROLE: SENSITIVITY  

This gate does **not** invent a broad operator sweep. Primary operator remains PAYLOAD_BLANK_V1. Second-operator GPU is deferred to stay inside the numerical-path compute envelope.

---

## 7. RQ2 analysis on the 304-commit RQ1 subset

ITEM: RQ2_ON_RQ1_PRIMARY_SUBSET  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2 Populations; Stats V1.1 `rq2_on_rq1_subset.role: SECONDARY_REQUIRED`  
SOURCE_VERSION: V1.2 / Stats V1.1  
SOURCE_COMMIT: `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE (faith AOPC on positive_475 includes the 304 ids)  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: SECONDARY / COMMON-COHORT SENSITIVITY  

---

## 8. enrichment

ITEM: ATTRIBUTION_ENRICHMENT_C  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2 RQ4; `src/metrics/rq4_enrichment.py`; jobs already store `rq4_enrichment`  
SOURCE_VERSION: V1.2  
SOURCE_COMMIT: `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE (per-job tables not aggregated in compact freeze)  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: DESCRIPTIVE  

---

## 9. negative-hit rates

ITEM: NEGATIVE_HIT_RATE_AT_K  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2 RQ1/RQ3 diagnostic; Stats V1.1 `NEGATIVE_HIT_RATE_AT_K`; `src/metrics/rq1_baselines.py`  
SOURCE_VERSION: V1.2 / Stats V1.1  
SOURCE_COMMIT: `3fa90ded…`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST  
PRE_SPECIFIED: YES  
CURRENT_STATUS: PARTIAL (jobs have `polarity` and signed `line_scores_sum`; rates not aggregated)  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: DESCRIPTIVE  

---

## 10. matched-clean analysis

ITEM: NEGATIVE_MATCHED_DIAGNOSTIC_V1  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2; `src/cohorts/select_negative_matched_diagnostic`; TEST block K raw exists (attention, Grad×Input, occlusion; N=475)  
SOURCE_VERSION: V1.2  
SOURCE_COMMIT: `3fa90ded…` / TEST execution `03be67d`  
TIMESTAMP / ORDERING EVIDENCE: matching rule frozen pre-TEST; jobs exist  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE (cheap attribution only; no RQ1 labels on clean; no faith AOPC on clean)  
NEW_GPU_COMPUTE_REQUIRED: NO for promised cheap-method dump; YES if one were to add RQ2 on clean (not promised as primary)  
SCIENTIFIC_ROLE: SENSITIVITY / DESCRIPTIVE  

---

## 11. 4096-context ablation

ITEM: RQ1 visibility 4096, N=345  
SOURCE_PROTOCOL: ATTRIBUTION_PROTOCOL_V1.2; ATTRIBUTION_PROTOCOL_V1 §14; TEST block J raw (`rq1_4096`, attention + Grad×Input, 345×3 seeds)  
SOURCE_VERSION: V1 / V1.2  
SOURCE_COMMIT: `3fa90ded…` / TEST `03be67d`  
TIMESTAMP / ORDERING EVIDENCE: pre-TEST; jobs exist  
PRE_SPECIFIED: YES  
CURRENT_STATUS: DATA_ALREADY_AVAILABLE  
NEW_GPU_COMPUTE_REQUIRED: NO  
SCIENTIFIC_ROLE: SENSITIVITY  

---

## Additional Phase-3 items (this prompt)

| Item | Pre-specified? | Role this gate |
|------|----------------|----------------|
| Rank-biserial for planned Wilcoxon-Pratt | YES (Stats V1 / V1.1); already in `rq1_stats.json` / `rq2_stats.json` | Report in extension tables |
| TP/FN stratification | Stats V1.1 `prediction_correctness_association` SECONDARY_ESTIMATION; review C3 post-stratification after lock | POST-HOC ROBUSTNESS unless using the frozen point-biserial role |
| Project-clustered sensitivity | NOT in frozen stats protocol as primary | NEW prospective robustness (this prompt) |
| Numerical-path RQ2 | NOT in original protocol | NEW prospective robustness (this prompt); only new GPU experiment that is authorized regardless |
| Second decoder | OPTIONAL / later gate | DRAFT only if numerical gate passes; do not execute |

## RQ3 family audit (protocol vs implementation)

Frozen `artifacts/test_attribution/statistics/holm_families.json` (TEST summarize): `RQ3_PRIMARY` has **one** member `SIGNED_VS_ABSOLUTE_DELTA_RECALL20`. Stats V1.1 yaml: `RQ3_PRIMARY: SIGNED_VS_ABSOLUTE_DELTA_RECALL20_for_signed_methods`. `rq3_stats.json` marks Grad×Input `confirmatory: true` and IG/occlusion/gradient `confirmatory: false`.

Resolution: family membership as **executed and frozen at TEST** is one confirmatory contrast (Grad×Input). Manuscript wording that every signed method is confirmatory is a **MANUSCRIPT_WORDING_ERROR**. This gate does **not** expand the family after seeing p-values.

## Encoder / second-model boundary

This gate will not train or evaluate an encoder or a second decoder. Encoder remains an incomplete protocol-owed **recipe** gap, not a silent cancellation of the V1.2 requirement.

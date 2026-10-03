# ATTRIBUTION_PROTOCOL_V1.2.md

Status: **FROZEN amendment** (pre-result; adversarial-review response)  
Gate: `REVIEWER_PROTOCOL_AMENDMENT_GATE`

## Version lineage

| Version | Status | Hash |
|---------|--------|------|
| **V1** | historically frozen | `73f0f891683f926a39d68b078f6e2770a1b42181ba1a9f56575c5556cba4794d` |
| **V1.1** | historically frozen | `ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e` |
| **V1.2** | **current** | `c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c` |

Config: `configs/attribution/m1_methods_v1_2.yaml`  
Manifest: `artifacts/attribution_protocol/v1_2/`

V1 and V1.1 files remain immutable. Future scientific runs MUST embed the **V1.2** hash.

---

## Preserved from V1.1

- Target \(s(x)=\ell_1-\ell_0\)
- RQ1 ABS_DESCENDING; SIGNED_POSITIVE_DESCENDING sensitivity
- SUM primary / MEAN sensitivity aggregation
- Attention LAST / LAST4
- IG ZERO primary / PAD sensitivity
- Occlusion attribution operator SEGMENT_DELETE_V1
- Faithfulness operator PAYLOAD_BLANK_V1
- RELATIVE_POLARITY_EPS_V1
- RQ1 N=304; 4096 ablation N=345
- Seeds {13,42,73}

## Amendment summary (construct fixes)

### RQ2 absolute vs directional faithfulness

- **PRIMARY (cross-method):** `ABSOLUTE_PERTURBATION_FAITHFULNESS`  
  `ABS_PERTURBATION_IMPACT_f = |s(x)-s(x_perturbed_f)|`  
  Summary: **`ABS_DELETION_AOPC`** under PAYLOAD_BLANK_V1 + **TOKEN_BUDGET_PREFIX_V1**.
- **SECONDARY (signed only):** `DIRECTIONAL_FAITHFULNESS` via `POSITIVE_EVIDENCE_DROP_f` with SIGNED_POSITIVE_DESCENDING. Attention is not compared on this endpoint.
- Insertion absolute gain: secondary only.
- Region-count fractions retained as **REGION_FRACTION_SENSITIVITY**.

### RQ1

- Construct: localization/plausibility ≠ faithfulness.
- Primary confirmatory endpoint: **Recall@20%Effort**.
- Trivial baselines: B_LENGTH, B_ORDER, B_RANDOM; B_ADD_FIRST audited (degenerate if all candidates are ADD).
- Length confound diagnostic: Spearman(|attr|, payload tokens).
- Signed hit diagnostic: NEGATIVE_HIT_RATE_AT_K (RQ3 diagnostic).

### Occlusion RQ2 role

`OCCLUSION_RQ2_ROLE = PERTURBATION_REFERENCE` — report estimates/CIs; no confirmatory Holm superiority claims in RQ2.

### RQ4

- Enrichment = abs_mass_share / token_share.
- Category ablations (MSG, FILE_PATH, STRUCTURAL_MARKUP) mandatory.
- PROMPT_INSTRUCTION accounted in categories.
- DIFF_POLARITY_SWAP = EXPLORATORY_STRUCTURAL_SENSITIVITY.
- TEST_FILE_SUBANALYSIS = DEFERRED_NOT_REQUIRED.

### Populations

- RQ2–RQ4 primary: 475 defect-inducing TEST commits (claim scope limited).
- NEGATIVE_MATCHED_DIAGNOSTIC_V1: 475 clean TEST matches (cheap methods only).
- RQ2_ON_RQ1_PRIMARY_SUBSET: N=304 secondary bridge.

### IG

Combined criterion: `E_abs <= max(1e-3, 0.05*|target_delta|)`; retry 100; else IG_NONCONVERGED.  
COMMON_COMPLETE_CASE_SENSITIVITY required.

### Validation rehearsal / sanity

64 validation positives before any test attribution; 16 for base-vs-adapter sanity (attention + Grad×Input only).

### Model scope

M2 = DEFERRED_FROM_CORE; ENCODER_BASELINE = REQUIRED; SECOND_DECODER = OPTIONAL.

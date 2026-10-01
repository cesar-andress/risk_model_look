# ATTRIBUTION_PROTOCOL_V1.1.md

Status: **FROZEN amendment** (pre-result)  
Gate: `ATTRIBUTION_PROTOCOL_AMENDMENT_GATE`

## Version lineage

| Version | Status | Hash |
|---------|--------|------|
| **V1** | historically frozen (do not overwrite) | `73f0f891683f926a39d68b078f6e2770a1b42181ba1a9f56575c5556cba4794d` |
**ATTRIBUTION_PROTOCOL_HASH (V1.1):** `ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e`

V1 files remain at `configs/attribution/m1_methods_v1.yaml` and
`artifacts/attribution_protocol/v1/`.  
V1.1 config: `configs/attribution/m1_methods_v1_1.yaml`.

V1.1 inherits all V1 freezes (target, ABS RQ1 ranking, SUM aggregation, IG
rules, polarity epsilon, etc.) and adds the completeness items below.

---

## Amendment summary

### Perturbation operators

| Use | Operator |
|-----|----------|
| Occlusion attribution (A5) | **SEGMENT_DELETE_V1** — remove complete semantic segment |
| Primary RQ2 faithfulness | **PAYLOAD_BLANK_V1** — blank payloads; retain structure |

These must not be conflated. Faithfulness must not self-evaluate the occlusion
deletion operator.

### RQ2 fractions and rounding

Primary fractions: **10%, 20%, 30%, 50%** (5% removed vs V1 list).  

\[
k = \max(1, \lceil f \cdot N\rceil)
\]

### Deletion / insertion / AOPC

- **Deletion:** blank top-k; \(D(f)=s(x)-s_f\); `AOPC_deletion = mean_f D(f)`.
- **Insertion:** from all-blank, restore top-k; \(I(f)=s_f-s_{\mathrm{empty}}\);
  `AOPC_insertion = mean_f I(f)`.
- Report both; do not cherry-pick.

### Cohorts

| RQ | Primary cohort |
|----|----------------|
| RQ1 | fully visible 2048 complete-case **N=304** (unchanged) |
| RQ2/RQ3/RQ4 | all **475** positive TEST commits; truncated commits eligible on **model-visible** input only |

### Missingness

Method-specific rules frozen (`METHOD_SPECIFIC_MISSINGNESS_V1_1`): IG_NONCONVERGED,
RQ1_TRUNCATED_COMMIT, REGION_NOT_MODEL_VISIBLE, EMPTY_CANDIDATE_SET,
ATTENTION_UNAVAILABLE, OCCLUSION_UNAVAILABLE — count/report; no silent imputation.

### RQ3 attention top-2 hunks

`ATTENTION_TOP2_HUNK_OCCLUSION_SIGN_V1`: fraction of top-2 attention hunks with
signed occlusion Δ classified NEGATIVE (suppresses buggy evidence).

### RQ4

- `DIFF_POLARITY_SWAP_V1`: ADD↔DEL swap probe (ablation).
- Test-file category: **PENDING_AUDIT** (default UNKNOWN; no `/test/`-only rule).

---

All other V1 prohibitions remain. Future attribution runs MUST embed the **V1.1** hash.

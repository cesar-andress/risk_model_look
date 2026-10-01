# RQ1_CANDIDATE_MASK_CONTRACT.md

Status: **FROZEN**

## Primary cohort

`PRIMARY_RQ1_POLICY = POLICY_A_COMPLETE_CASE`  
`PRIMARY_RQ1_N = 413` (of ORIGINAL_RQ1_COHORT = 475)

## Semantics

For every canonical changed line in a commit record:

| Value | Meaning |
|-------|---------|
| `RQ1_POSITIVE` | Mapped Policy-A candidate ∧ label==1.0 ∧ `rq1_primary_commit` |
| `RQ1_NEGATIVE` | Mapped Policy-A candidate ∧ label==0.0 ∧ `rq1_primary_commit` |
| `NOT_IN_RQ1_UNIVERSE` | Every other canonical line |

## Hard prohibitions

- `NOT_IN_RQ1_UNIVERSE` ≢ negative  
- No `UNKNOWN_AS_NEGATIVE`  
- Train/valid commits never `rq1_primary_commit`  
- Non-positive test commits never `rq1_primary_commit`  
- The 62 mapping-incomplete gold-positive test commits are `rq1_primary_commit=false` but remain in classification / RQ2–RQ4 unless later independently excluded  

## Truncation

If a RQ1 line falls beyond `WHOLE_SEGMENT_PREFIX_TRUNCATION_V1`, treat as
`RQ1_LINE_TRUNCATED` for usable-population accounting — do **not** relabel negative.
Primary metrics require fully visible candidate universes (`RQ1_VISIBLE_N`).

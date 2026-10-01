# ADVERSARIAL_REVIEW_RESPONSE.md

Response to Claude design review (2026-10-01), archived at  
`docs/reviews/CLAUDE_DESIGN_REVIEW_2026-10-01.md`.

Protocol result: **ATTRIBUTION_PROTOCOL_V1_2** + **STATISTICAL_PROTOCOL_V1_1**.

| ID | Disposition | Action |
|----|-------------|--------|
| C1 | **ACCEPTED** | Dual constructs: ABS_DELETION_AOPC primary; DIRECTIONAL_FAITHFULNESS secondary (signed only) |
| C2 | **ACCEPTED** | B_LENGTH/B_ORDER/B_RANDOM; ADD_FIRST audited; TOKEN_BUDGET_PREFIX_V1 primary; region-fraction sensitivity; token-matched random |
| C3 | **PARTIALLY_ACCEPTED** | Claim scope = defect-inducing commits; NEGATIVE_MATCHED_DIAGNOSTIC_V1 (N=475, cheap methods); TP/FN/FP/TN post-stratification after lock |
| C4 | **ACCEPTED** | RQ1 construct wording; RQ2_ON_RQ1_PRIMARY_SUBSET (N=304) required secondary |
| C5 | **ACCEPTED** | Keep ABS_DESCENDING primary; NEGATIVE_HIT_RATE_AT_K + SIGNED_POSITIVE ranking retained |
| C6 | **ACCEPTED** | Occlusion = PERTURBATION_REFERENCE in RQ2; OPERATOR_DEPENDENCE_DIAGNOSTIC; no RQ2 Holm superiority |
| C7 | **ACCEPTED** | DIFF_POLARITY_SWAP → EXPLORATORY_STRUCTURAL_SENSITIVITY |
| C8 | **ACCEPTED** | ATTRIBUTION_ENRICHMENT_C; category ablations; PROMPT_INSTRUCTION in categories |
| C9 | **ALREADY_ADDRESSED** | LAST + LAST4 already frozen; claim language limited to evaluated configs; no extra rollout |
| C10 | **ACCEPTED** | One primary endpoint/RQ; frozen contrasts; Top-k descriptive (no Wilcoxon primary) |
| C11 | **ACCEPTED** | Combined abs/rel IG criterion; COMMON_COMPLETE_CASE_SENSITIVITY |
| C12 | **PARTIALLY_ACCEPTED** | Keep N=304; 4096 ablation retained; characterization of excluded commits remains a reporting duty at analysis time |
| C13 | **ACCEPTED** | Seed-rank Spearman stability; base-vs-adapter sanity on validation subset |
| C14 | **ACCEPTED** | Validation rehearsal N=64 protocol; local freeze bundle + annotated tag; EXTERNAL_TIMESTAMP_STATUS=PENDING |

## Declined / deferred scope notes

| Item | Disposition | Rationale |
|------|-------------|-----------|
| Immediate second decoder / Llama | **DECLINED as blocker** | SECOND_DECODER=OPTIONAL; title/claim scope limited to Qwen unless added |
| M2 as core | **ACCEPTED removal** | M2=DEFERRED_FROM_CORE |
| External timestamp service in this gate | **PENDING** | Local tag is not external preregistration |

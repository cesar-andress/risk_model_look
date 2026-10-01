# STATISTICAL_ANALYSIS_PROTOCOL_V1.1.md

Status: **FROZEN amendment** (pre-result)  
Gate: `REVIEWER_PROTOCOL_AMENDMENT_GATE`  
Config: `configs/stats/attribution_stats_v1_1.yaml`  
Manifest: `artifacts/statistical_protocol/v1_1/`

| Version | Hash |
|---------|------|
| **V1** (historical) | `22816586bb5688b6595d4cd10c86ead079274aa6b1827a50b2d7b0cf7b090c07` |
| **V1.1** (current) | `edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8` |

Parent attribution: **ATTRIBUTION_PROTOCOL_V1_2** /  
`c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c`

Unchanged: COMMIT unit; ≥2 common seeds; Wilcoxon–Pratt; rank-biserial; 10k commit bootstrap; Holm α=0.05.

## Endpoint reduction

| RQ | Primary confirmatory endpoint | Primary contrasts |
|----|-------------------------------|-------------------|
| RQ1 | Recall@20%Effort | Attention vs Grad×Input; Attention vs IG; Attention vs occlusion |
| RQ2 | ABS_DELETION_AOPC | Attention vs Grad×Input; Attention vs IG (**occlusion excluded**) |
| RQ3 | SIGNED_VS_ABSOLUTE_DELTA_RECALL20 | signed methods (Wilcoxon) |
| RQ4 | estimation (+ category ablations); **no giant Holm family** | — |

## Binary Top-k

Top-k metrics are **secondary descriptive**: proportion + commit bootstrap CI; optional McNemar.  
**Wilcoxon is not the primary Top-k test** and carries no confirmatory Holm burden.

## RQ4 / swap

DIFF_POLARITY_SWAP removed from primary Holm.  
TEST_FILE_SUBANALYSIS deferred.

## Families

- `RQ1_PRIMARY`: 3 frozen contrasts on Recall@20%Effort  
- `RQ2_PRIMARY`: 2 frozen contrasts on ABS_DELETION_AOPC  
- `RQ3_PRIMARY`: signed-vs-absolute ΔRecall@20  
- `RQ4_PRIMARY`: NONE (estimation-focused)  
- `SENSITIVITY`: separate

# STATISTICAL_ANALYSIS_PROTOCOL_V1.md

Status: **FROZEN** (pre-result)  
Gate: `STATISTICAL_PROTOCOL_FREEZE_GATE`  
Config: `configs/stats/attribution_stats_v1.yaml`  
Manifest: `artifacts/statistical_protocol/statistical_protocol_manifest.json`  
**STATISTICAL_PROTOCOL_HASH:** `22816586bb5688b6595d4cd10c86ead079274aa6b1827a50b2d7b0cf7b090c07`

Parent: **ATTRIBUTION_PROTOCOL_V1_1** /  
`ae710257f6ab76e40f12977878c4ec57b2bf59acf2bf5d44d816d2461087670e`

No choice herein may depend on which method performs best.

---

## 1. Inference unit

**PRIMARY_STATISTICAL_UNIT = COMMIT.**

Do not treat `commit × model_seed` as independent observations (pseudoreplication).

## 2. Model-seed handling

Seeds {13, 42, 73} are repeated model realizations.

Pairwise A vs B: within each commit, average seed-level metric differences over
**common-valid seeds**; require **≥ 2** common valid seeds else exclude commit.
Report N_total, N_included, N_excluded. No imputation.

Descriptive tables: per seed + mean ± sample SD across seeds.  
Inference distributions: commit-level only (no flattening).

## 3. Missingness

Respect `METHOD_SPECIFIC_MISSINGNESS_V1_1`. Tabulate IG_NONCONVERGED, OOM,
NO_ELIGIBLE_REGION, NUMERICAL_FAILURE. Do not hide low-coverage methods.

If N_included < 30: flag **LOW_POWER_EXPLORATORY**.

## 4. RQ1 analysis

Population N=304. Primary endpoints: Top-1/5/10, IFA, Recall@20%Effort,
Effort@20%Recall with frozen directions (higher/lower better).

All unordered pairwise comparisons among PRIMARY methods (+ random as reference).
Primary test: Wilcoxon signed-rank (two-sided, Pratt).  
McNemar on Top-k: SECONDARY_DIAGNOSTIC only.  
Random baseline: collapse 100 perms → expected commit metric before inference.

## 5. RQ2 analysis

Population N=475 (validity-filtered). Primary: DELETION_AOPC, INSERTION_AOPC
under PAYLOAD_BLANK_V1 / LOGIT_CONTRAST (higher better).  
Fraction curves: descriptive + bootstrap CIs (not primary hypotheses).  
SEGMENT_DELETE operator: RQ2_SENSITIVITY. Sufficiency: SECONDARY.

## 6. RQ3 analysis

Attention top-2 negative-occlusion fraction: estimation + commit bootstrap CI;
no manufactured 50% null.  
Signed vs absolute ranking (ABS vs SIGNED_POSITIVE) on Top-5/10/R@20%E:
primary Wilcoxon; Holm family RQ3_PRIMARY.  
Sign agreement: estimation. Kendall τ: SECONDARY at commit unit.

## 7. RQ4 analysis

Category mass: descriptive/estimative (no giant pairwise matrix).  
Test-file: PENDING_AUDIT — no primary hypothesis.  
Prediction-correctness: point-biserial (PRIMARY), per seed + cluster bootstrap.  
Spearman vs risk logit: SECONDARY.  
DIFF_POLARITY_SWAP Δlogit: one-sample Wilcoxon vs 0 (PRIMARY).  
Category L1 original vs swap: SECONDARY.

## 8. Effect sizes

Primary paired: **matched-pairs rank-biserial** (positive = first method larger
raw metric). Report DIRECTION_OF_BETTER_PERFORMANCE separately for
lower-is-better. Never silently flip signs.  
Also: median/mean/IQR of paired differences.  
Cliff's δ: SECONDARY_LEGACY only.

## 9. Confidence intervals

**PAIRED_COMMIT_BOOTSTRAP_PERCENTILE_V1**: 10 000 resamples; 2.5/97.5 percentiles;
resample **commits**; keep seed rows together. Deterministic seeds from
SHA-256(protocol_hash|RQ|metric|comparison). No BCa shopping.

## 10. Multiplicity

**HOLM_FWER_V1**, α=0.05, families by RQ (RQ1/RQ2/RQ3/RQ4 primary) plus separate
SENSITIVITY family. Do not mix. Report raw and Holm-adjusted p; use `p < 0.001`
style; non-significance ≠ equivalence.

## 11. Sensitivity analyses

Tagged SECONDARY / SENSITIVITY / EXPLORATORY. Roles cannot change after seeing
values without amendment. Scott–Knott ESD is **not** primary (unused OK).

## 12. Prohibited post-hoc practices

Flattening seed×commit; imputation; switching Wilcoxon mode by p-value;
BCa vs percentile after results; BH instead of Holm; redefining directions;
promoting sufficiency; 50% null for attention polarity; treating random perms
as independent; Scott–Knott favorable ranking; “best” by mean alone; test-file
primary claims while PENDING_AUDIT.

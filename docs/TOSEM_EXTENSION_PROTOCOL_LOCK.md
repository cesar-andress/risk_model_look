# TOSEM_EXTENSION_PROTOCOL_LOCK.md

Status: **FROZEN before new GPU results**  
Gate: `TOSEM-EXTENSION-GATE-1`  
Timestamp (UTC): 2026-10-06T05:58:00Z  
Canonical branch: `main`  
Parent HEAD (no new GPU yet): `b9e59faa71435f31a656fd52b87481ec7e14a39c`  
Parent corrected TEST freeze SHA-256: `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19`  
Parent corrective commit: `b9e59faa71435f31a656fd52b87481ec7e14a39c`  
Superseded freeze (not current evidence): `8caad443f4a69d7040ae7e966053e12f83f33ce9dc11eb2ea029818ecc68ec95`  
Attribution protocol: V1.2 / `c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c`  
Statistical protocol: V1.1 / `edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8`  
Score \(s\): frozen LOGIT_CONTRAST \(s(x)=\ell_1-\ell_0\) (buggy minus clean class logits at the classification token).  
Model: frozen M1 Qwen2.5-Coder-7B-Instruct QLoRA NF4, revision `c03e6d358207e414f1eca0bb1891e29f1db0e242`, seeds {13,42,73}, selected adapters in `artifacts/m1_final`.  
IG: closed. No IG rerun, no validity change, no family drop.

This lock must be committed before inspecting new GPU numbers.

## A. Protocol-owed tasks that WILL run now

1. RQ1 B_RANDOM, B_LENGTH, B_ORDER on N=304 from existing TEST jobs + frozen baseline definitions (CPU).  
2. Aggregate RQ4 enrichment already stored in jobs (CPU).  
3. Aggregate NEGATIVE_HIT_RATE_AT_K @5/@10 from existing signed line scores on RQ1 N=304 (CPU; eps = frozen RELATIVE_POLARITY_EPS_V1 as stored/used in jobs, not tuned).  
4. RQ2 Attention vs Grad×Input on the same 304 RQ1 commits (CPU from existing faith AOPC). Label: COMMON-COHORT SENSITIVITY / SECONDARY_REQUIRED.  
5. RQ1 4096 ablation N=345 Attention vs Grad×Input from existing `raw/rq1_4096` (CPU).  
6. Matched-clean cheap-method descriptive summary from existing `raw/matched_clean` (CPU). No new matching.  
7. Report frozen rank-biserial already computed for planned paired contrasts; recompute identically if regenerating tables.  
8. RQ2 token-matched random control (GPU): **1** canonical random region set per commit×seed for the valid RQ2 Attention–Grad×Input population, token-budget matched via `token_matched_random_regions`, PAYLOAD_BLANK_V1, same fractions, ABS_DELETION_AOPC. RNG seed = first 8 hex of SHA256(`edbe4dca…` + `|RQ2_TOKEN_MATCHED_RANDOM|` + commit_id + `|` + str(seed)) parsed as uint32. Not optimized to enlarge the attribution effect. Compare attention AOPC and Grad×Input AOPC each vs this shared random AOPC (paired, commit unit, ≥2 common-valid seeds). Role: BASELINE / ROBUSTNESS. Not merged into original Holm families.

## B. Existing-data reanalyses that WILL run (not confirmatory promotions)

- TP/FN stratification of RQ1 Recall@20 and RQ2 AOPC using existing M1 TEST predictions vs gold labels. Label: POST-HOC ROBUSTNESS.  
- Project-clustered sensitivity: percentile bootstrap resampling **projects** (all commits of a sampled project kept together), 10_000 repeats, same paired Attention−Grad×Input RQ2 diffs as primary. Does not replace commit-level primary. Label: PROJECT-CLUSTERED SENSITIVITY.  
- Seed-stability report for attention, Grad×Input, occlusion from existing `seed_stability.json`.  
- RQ1 interval-based magnitude for Holm-non-significant planned contrasts; **no** retrospective equivalence test.  
- IG N=2/3: exploratory small-n diagnostic only; do not replace Holm provenance.

## C. Exact numerical-path experiment (only new robustness experiment authorized regardless of original protocol)

Question: is the paired Attention − Grad×Input RQ2 ABS_DELETION_AOPC difference larger than numerical/execution-path variation of the **same** frozen NF4 model?

Population: all commits in the existing valid RQ2 Attention vs Grad×Input contrast (`n_included` from corrected `rq2_stats.json`, expected 472). No subsampling. Seeds 13/42/73 under original validity. Unit: commit after collapsing ≥2 common-valid seeds.

Canonical path: TEST execution path — FrozenM1Bundle, NF4 weights, bfloat16 compute as currently loaded, batch size 1, evaluation mode, no dropout, no sampling.

Primary variant (frozen, unique confirmatory numerical comparison): **same NF4 weights**, float32 compute on the risk forward (`s=\ell_1-\ell_0`) without changing adapters, dataset, rankings, or PAYLOAD_BLANK semantics.

Descriptive diagnostics only (not pass-criterion shopping): batch size 1 vs 4 on identical packed sequences if memory allows; report only `|Δs|`.

Do **not** dequantize to a different weight representation and call it the same model.

## D–O. Frozen operational details

D. Population numerical + RQ2 random: RQ2 valid Att–GxI commits.  
E. Unit: COMMIT.  
F. Seeds: 13, 42, 73.  
G. Score: \(s=\ell_1-\ell_0\).  
H–I. Frozen M1 adapters + NF4.  
J. Canonical bf16 vs primary float32-compute.  
K. Inference: eval, deterministic where supported (`torch.use_deterministic_algorithms` if feasible; record if not).  
L. NUMERICAL_GATE_PASS iff BOTH: (1) float32-compute Att−GxI RQ2 effect has the **same sign** as original point estimate 0.01485257768361582 and its 95% commit-bootstrap CI excludes 0; AND (2) |mean paired RQ2 difference on float32 path| exceeds the **median** of `|s_canonical − s_float32|` over scored (commit, seed) pairs of unperturbed canonical encodings. p90/p95 of `|Δs|` are diagnostics only.  
M. Missingness: original validity; no imputation; OOM recorded; skip pair if either path missing.  
N. Stopping: do not expand to second decoder; if numerical+random GPU wall is materially beyond ~15 h because the design was misunderstood, STOP and report TECHNICAL incompleteness rather than widening scope.  
O. Multiplicity: numerical RQ2 contrast is a **separate prospective robustness** experiment; not merged into TEST Holm families.  
P. Inconvenient/null/fail: report NUMERICAL_GATE_FAIL; do not retune dtypes; do not rescue RQ2; do not start second decoder.

## Explicit prohibitions

- No second-decoder download/train/eval.  
- No encoder execution in this gate.  
- No IG rescue.  
- No new attribution method.  
- Do not overwrite forensic-corrected freeze; create a **new extension freeze** with parent pointers.  
- Do not finalize Abstract/Conclusion/submission Results narrative.

## Second-decoder protocol draft

Create `docs/SECOND_DECODER_REPLICATION_PROTOCOL_DRAFT.md` **only if** NUMERICAL_GATE_PASS. Do not execute it.

Lock file SHA-256 (bytes at freeze write): `d99857728a2febe8bb00e6be4192889ecb43a598ee8d6e77cad6aac0dc3dc37c`

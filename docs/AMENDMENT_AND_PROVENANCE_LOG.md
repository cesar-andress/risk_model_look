# AMENDMENT_AND_PROVENANCE_LOG.md

Public provenance trail (not a Results narrative).

## Identifier semantics (do not relabel without checking the computation)

Several stable identifiers in this package are **computed content hashes**, not
raw on-disk digests of a Markdown/YAML file path. Values below are **unchanged**;
only the documentation of their type is clarified.

| Human-readable name | Identifier | Type | Exact hashed object | Computation | Raw file-byte SHA? | File-byte SHA-256 (where useful) |
|---------------------|------------|------|---------------------|-------------|--------------------|----------------------------------|
| Attribution Protocol V1.2 | `c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c` | Protocol identifier | Canonicalized attribution protocol JSON | `src/experiments/protocol_manifest.py` → `protocol_hash` / `canonical_json_bytes` | **NO** | N/A (config object, not a single Markdown file) |
| Statistical Protocol V1.1 | `edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8` | Protocol identifier | Canonicalized stats-protocol JSON | `src/stats/protocol_manifest.py` → `statistical_protocol_hash` | **NO** | N/A |
| Corrected TEST freeze | `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19` | Freeze identifier (`freeze_sha256`) | Freeze JSON object after `sha256_json` over sorted keys (field written back into file) | `src/experiments/rehearsal_pipeline.py` → `sha256_json`; set in `scripts/summarize_test_attribution.py` | **NO** | `aba7894ddf05c4635d97dc4a57c48cd3b2717925b906994fc4f14e302ec12982` (`artifacts/test_attribution/TEST_RESULTS_FREEZE.json`) |
| Extension results freeze | `5e5c67e068a668f046ca2c1efe04a6b03f1a147bb3f09ded54a1b9710561df9b` | Freeze identifier (`freeze_sha256`) | Extension freeze object via `sha256_json` | same `sha256_json` pattern | **NO** | `741b63a1d74e3ee5d5e536c3a07fc690b672607628825e20ce5204aff096b026` (`artifacts/tosem_extension/TOSEM_EXTENSION_RESULTS_FREEZE.json`) |
| Final evidence freeze | `885540b87acee8190babe5592c20ed3bc456868da41866a7a047abbff53d4a78` | Freeze identifier (`freeze_sha256`) | Final freeze object via `sha256_json` | same pattern; field inside `EMSE_FINAL_RESULTS_FREEZE.json` | **NO** | `aff72921d3fd8ca41d6b80db58cf377b052959c9c0ad869e1d35dc4fc56214ce` (same JSON file bytes) |

Related **true file-byte** digests used in provenance (not the five identifiers above):

| Object | File-byte SHA-256 |
|--------|-------------------|
| `docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md` (historical filename) | `855415e785b41d3a6a233b33fb624da76cc35f48f7beedbe13b16498aca31540` |
| `docs/EMSE_FINAL_ANALYSIS_LOCK.md` | `7e54a8f394be36b0958cf7d8b9bf8e36121930b9d981b0bcce0e2496557e81dd` |

## Freeze snapshot vs later editorial docs

`artifacts/emse_final/EMSE_FINAL_RESULTS_FREEZE.json` embeds `file_sha256` entries for
documentation files (amendment log, claim ledger, encoder resolution, venue note,
etc.) as those files existed **at freeze time**.

Those documentation files may receive **editorial / release-only** updates after the
freeze (licensing notes, identifier semantics, claim-ledger transcription fixes,
release-tree hygiene). **Do not rewrite the freeze JSON** to chase documentation
edits. Frozen scientific results, cohorts, protocols, and the freeze identifiers
above are unchanged. Current documentation digests can be verified independently
with `sha256sum` on the shipped files.

## Compact provenance table

| Object | Identifier |
|--------|------------|
| Original TEST freeze (superseded) | freeze id `8caad443f4a69d7040ae7e966053e12f83f33ce9dc11eb2ea029818ecc68ec95` |
| Reason for correction | IG valid-seed mask used a non-method-specific aggregation |
| Corrective commit | `b9e59faa71435f31a656fd52b87481ec7e14a39c` |
| Corrected TEST freeze | freeze id `a707e8e7…` (see table above) |
| Extension protocol lock file | file-byte SHA-256 `855415e7…` (`docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md`) |
| Extension results freeze | freeze id `5e5c67e0…` |
| NUMERICAL_GATE | **FAIL** |
| Float32 path | **SCORING_ONLY** |
| Final-analysis lock | file-byte SHA-256 `7e54a8f3…` |
| Final evidence freeze | freeze id `885540b8…` / file-byte `aff72921…` |

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

Planned signed-versus-absolute ΔRecall@20 for signed methods. Estimable confirmatory member at N=304: Grad×Input. IG remains a family member at N=2 (LOW_POWER_EXPLORATORY). Signed occlusion vs absolute was computed and is reported descriptively outside the confirmatory family (Δ≈0, not confirmatory). SUM=MEAN for occlusion concerns aggregation, not sign.

## 475 → 472

Primary RQ2 cohort is 475 defect-inducing TEST commits. Planned Attention vs Grad×Input AOPC uses N=472 because three commits have attention PAYLOAD_BLANK `missingness_code=OOM` on all seeds:

- `e21d4d436b51d88f9554751982cd7b8552854c49`
- `ab1ee1b68b15234b62a840c4b1f6d2485d771450`
- `c4193c6e4ad3e5f526df5d1e0748abffcfd08bb2`

Source: `artifacts/test_attribution/summaries/rq2_excluded_3.json`.

## MEAN aggregation vs length–attribution correlation

MEAN token-to-line reduction: **PRE_SPECIFIED_DIAGNOSTIC** in Attribution Protocol V1.2 (`line_reduction_sensitivity: MEAN` before TEST). The later analysis lock labelled MEAN as POST-HOC construct sensitivity; that lock file is not rewritten (its digest is frozen). The manuscript follows the earlier protocol: MEAN is a pre-specified construct sensitivity. Length–attribution Spearman on RQ1 ≥5 lines: **POST_HOC_DIAGNOSTIC**.

## Diagnostic `n_included=304` / `n_excluded=56`

In `artifacts/emse_final/emse_final_diagnostics.json`, baseline and SUM-vs-MEAN
contrasts report `n_included=304` and `n_excluded=56` (`missing_pair_count=56`).

Definition (code, not a new analysis):

- Script: `scripts/emse_final_diagnostics.py` → `contrast_pack` →
  `src/stats/paired.py` → `build_pairwise_commit_diffs`.
- Candidate set = union of commit IDs present in either side of the paired maps
  (method Recall@20 seed map from `positive_475` jobs with a recorded metric,
  and/or RQ1 trivial-baseline map built on the primary RQ1 cohort).
- For these contrasts that union has size **360** (= 304 + 56).
- A commit is **included** only if it has ≥2 common-valid seeds
  (`MIN_COMMON_VALID_SEEDS = 2`) with finite paired values → **304** included
  (the primary RQ1 fully visible mapped cohort used for scored means).
- A commit is **excluded** when it lacks ≥2 common-valid seeds for that pair →
  **56** excluded (`n_excluded_missingness`).

This does not redefine the primary RQ1 localization table denominator (still N=304).

## Planned analyses and reporting status (public copy)

Statuses preserve the manuscript accounting classifications. No new experiment.

| Item | Original | Executed | Reported | Consequence / class |
|------|----------|----------|----------|---------------------|
| Encoder baseline | required | NO | limitation | **pre-specified but not executed** |
| SEGMENT_DELETE perturb. | diagnostic | NO | yes (not run) | **pre-specified but not executed** (PAYLOAD_BLANK only) |
| RQ1 B_RANDOM repeats | 100 | 100 | yes | **executed primary/secondary as specified** |
| RQ2 token-matched random | 1 in extension lock | 1 | yes | **executed** (not a 100-draw variance estimate) |
| Matched-clean | diagnostic | YES | Executed; no outcome reported | **executed diagnostic**; no gold RQ1 labels |
| Three-line context | predeclared | NO | yes (not run) | **pre-specified but not executed** |
| Top-k/IFA/Effort@20%R | secondary | YES | secondary table | **executed secondary** |
| Last-four-layer attention | sensitivity | YES | appendix | **executed** sensitivity (0.362 vs 0.354) |
| Pad-baseline IG | optional | NO | yes (not run) | **pre-specified but not executed** |
| Directional drop | secondary | NO | yes (not run) | **pre-specified but not executed** |
| Attention hunk polarity | secondary | NO | yes (not aggregated) | **not reported** as aggregate |
| Diff-polarity swap | exploratory | NO | yes (not run) | **exploratory**; not executed on TEST |
| RQ3 family | signed methods | PARTIAL | Methods/RQ3 table | GxI confirmatory; IG N=2 exploratory; occlusion **descriptive** |
| 475→472 | RQ2 cohort N=475 | YES (3 excluded) | Methods/RQ2 | 3 attention OOM commits |

Secondary Top-k/IFA/Effort@20%Recall were aggregated from frozen job `rq1` fields (no new rankings).

## Licensing (2026-10-06)

Author decision: **MIT** for author-owned software and tracked author-owned compact
result artifacts. Upstream JIT-Fine / JIT-Defects4J raw dumps, third-party model
weights, and the manuscript are **not** relicensed. See `LICENSE`, README
Licensing, `THIRD_PARTY_NOTICES.md`, and `docs/ZENODO_RELEASE_PLAN.md`.

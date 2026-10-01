# DECISION_LOG.md

Non-trivial bootstrap decisions. Format: datetime | decision | reason | alternatives | reversible | gate affected.

---

## 2026-09-29T23:18:00+02:00 — Separate code and paper roots

- **Decision:** Keep replication code at `/home/cesar/papers/risk_model_look/risk_model_look` and manuscript at `/home/cesar/papers/risk_model_look/paper` without nesting or symlinks.
- **Reason:** Public replication hygiene; manuscript LaTeX must not ship inside the software/data repo by default.
- **Alternatives considered:** Single monorepo with `paper/`; symlink between roots.
- **Reversible:** Yes, with explicit later decision.
- **Gate affected:** RELEASE_GATE, PAPER_GATE

## 2026-09-29T23:18:00+02:00 — No dataset download yet

- **Decision:** Do not download JIT-Defects4J or any other dataset during bootstrap.
- **Reason:** Authoritative URL, schema, label semantics, and split files are TO VERIFY; license/redistribution unknown.
- **Alternatives considered:** Partial download “for exploration.”
- **Reversible:** Yes.
- **Gate affected:** DATASET_GATE

## 2026-09-29T23:18:00+02:00 — Novelty gate unresolved

- **Decision:** Record NOVELTY_GATE as UNRESOLVED despite conflicting project-note statements.
- **Reason:** No dated auditable literature-search report is available to this execution agent; task forbids declaring novelty.
- **Alternatives considered:** Treat plan date 2026-09-29 as verification (rejected).
- **Reversible:** Yes, when orchestrator supplies the report.
- **Gate affected:** NOVELTY_GATE

## 2026-09-29T23:18:00+02:00 — No journal template selected

- **Decision:** Use a minimal generic `article` LaTeX scaffold in the paper root.
- **Reason:** Journal selection (IST/JSS/EMSE/other) is deferred.
- **Alternatives considered:** elsarticle / Springer class premature lock-in.
- **Reversible:** Yes.
- **Gate affected:** PAPER_GATE

## 2026-09-29T23:18:00+02:00 — No GitHub/Zenodo release in this phase

- **Decision:** Do not create releases, Zenodo deposits, or DOIs; do not push.
- **Reason:** Bootstrap only; release hygiene gate not started. Existing remote (if any) is left untouched and unused for push in this task.
- **Alternatives considered:** Push bootstrap commit to origin (rejected by task/workspace policy for this phase).
- **Reversible:** Yes later under RELEASE_GATE.
- **Gate affected:** RELEASE_GATE

## 2026-09-29T23:18:00+02:00 — No scientific experiment implementation yet

- **Decision:** Source packages remain placeholders; only structure tests and a 4-bit load smoke script are allowed.
- **Reason:** Novelty unresolved; dataset/protocol facts TO VERIFY; task prohibits attribution/training/metrics code.
- **Alternatives considered:** Stub metric APIs (rejected as premature).
- **Reversible:** Yes after gates clear.
- **Gate affected:** XAI_GATE, TRAINING_GATE, ANALYSIS_GATE

## 2026-09-29T23:18:00+02:00 — Environment tool: uv + venv fallback

- **Decision:** Provide `environment.yml` for conda/mamba reproducibility, but create the working environment with `uv` + Python 3.11 `.venv` because conda/mamba were absent at inspection.
- **Reason:** Machine had `uv` and system Python 3.10/3.11/3.12; default `python3` on PATH was unusable (3.6 / segfaulting pip).
- **Alternatives considered:** Install miniconda without explicit request (deferred); use system Python 3.6 (impossible for stack).
- **Reversible:** Yes (can recreate with conda later from `environment.yml`).
- **Gate affected:** ENVIRONMENT_GATE

## 2026-09-29T23:18:00+02:00 — Ignore raw data by default

- **Decision:** `.gitignore` excludes `data/raw/**` while retaining `.gitkeep`.
- **Reason:** Do not assume JIT-Defects4J license permits redistribution.
- **Alternatives considered:** Commit sample raw slices (rejected).
- **Reversible:** Yes after license verification and explicit release decision.
- **Gate affected:** DATASET_GATE, RELEASE_GATE

## 2026-09-29T23:24:30+02:00 — ENVIRONMENT_GATE marked PASS after executed checks

- **Decision:** Set ENVIRONMENT_GATE=PASS after `pytest -q` and `scripts/smoke_qwen_4bit.py` both exited 0 on this host.
- **Reason:** Acceptance criteria require executed checks, not aspirational docs.
- **Alternatives considered:** Leave PENDING despite PASS logs (rejected).
- **Reversible:** Yes if a later machine fails the same smoke.
- **Gate affected:** ENVIRONMENT_GATE

## 2026-09-29T23:45:00+02:00 — NOVELTY_GATE marked PASS after systematic audit

- **Decision:** Set NOVELTY_GATE=PASS; reject the broad provisional “first open comparison …” claim; adopt a compositional intersection claim.
- **Reason:** No public-data direct collision of JIT explanation faithfulness (A) with RQ3-equivalent signed/occlusion polarity (B) was found among inspected sources up to 2026-09-29.
- **Alternatives considered:** FAIL on XMENTOR “sign” (rejected: class B ≠ D/E); FAIL on EASE fidelity (rejected: not JIT commit-risk / not decoder-only); INCONCLUSIVE solely due to JITEC full-text gap (rejected: residual UNKNOWN does not establish A∧B).
- **Reversible:** Yes if a later primary source demonstrates A∧B.
- **Gate affected:** NOVELTY_GATE

## 2026-09-29T23:45:00+02:00 — Near-collisions recorded as must-cite / must-differentiate

- **Decision:** Treat R1, CodeFlowLM, JITEC, EASE 2026 transformer fidelity, XMENTOR, JIT-LSM, FoX, CfExplainer, and Pintore et al. as mandatory positioning literature; keep CoScoreX ICSME RF paper distinct from EASE transformer CoScoreX study.
- **Reason:** Each overlaps one RQ or method family without covering the planned intersection.
- **Alternatives considered:** Ignoring classical JIT XAI as “not LLM” (rejected: reviewers will ask).
- **Reversible:** No (citation set can grow, not shrink without justification).
- **Gate affected:** NOVELTY_GATE, PAPER_GATE

## 2026-09-29T23:45:00+02:00 — Jacobian Scopes / IG null-baseline project note

- **Decision:** Mark the plan’s IG-attention-sink warning as **PARTIAL support** from arXiv:2601.16407, not a JIT-specific empirical result.
- **Reason:** Paper shows IG path integration with null baseline is distorted by attention sink and can worsen AOPC in decoder LLMs; domain is next-token attribution, not commit-risk classification.
- **Alternatives considered:** Delete the threat entirely (rejected); treat as established for JIT classifiers (rejected).
- **Reversible:** Yes after JIT-specific IG baseline pilots.
- **Gate affected:** XAI_GATE (future), NOVELTY_GATE (integrity check)

## 2026-09-29T23:55:00+02:00 — Authoritative JIT-Fine upstream frozen

- **Decision:** Use `jacknichao/JIT-Fine` revision `584799fdec6095ab75a45fd2a5f8db5b12163aa5` as authoritative replication source; treat `tianc43/JIT-FINE` as third-party mirror (identical `data.zip` blob).
- **Reason:** Repo owned by Chao Ni (first author); created with FSE’22 materials; Crossref/ACM DOI verified.
- **Alternatives considered:** Prefer mirror by search rank (rejected); clone without SHA freeze (rejected).
- **Reversible:** Only if stronger author-issued archive (e.g. Zenodo) appears with contradictory content.
- **Gate affected:** DATASET_PROVENANCE_GATE

## 2026-09-29T23:55:00+02:00 — Canonical dataset spelling JIT-Defects4J

- **Decision:** Manuscript prose uses **JIT-Defects4J**; preserve **JIT-Defect4J** only when quoting upstream README.
- **Reason:** Paper spelling is JIT-Defects4J; README spelling differs but same artifact.
- **Alternatives considered:** Always use README spelling (rejected).
- **Reversible:** Yes for quoting policy; name itself is fixed by paper.
- **Gate affected:** DATASET_PROVENANCE_GATE, PAPER_GATE

## 2026-09-29T23:55:00+02:00 — Reuse author-provided split membership

- **Decision:** Freeze train/valid/test membership from author pickles under `data/jitfine/`; do not regenerate a new split.
- **Reason:** README/training commands reference materialized files; paper describes chronological 80/20; no checked-in generation script found.
- **Alternatives considered:** Re-implement §6.1 split ourselves (rejected for compatibility risk).
- **Reversible:** No for primary study once acquisition validates membership; secondary sensitivity analyses would need explicit new decision.
- **Gate affected:** DATASET_PROVENANCE_GATE, TRAINING_GATE

## 2026-09-29T23:55:00+02:00 — Line-label scope and localization subset

- **Decision:** For JIT-Fine-compatible localization evaluation, treat added lines as primary (`--only_adds`); positive commit/line labels mean defect-inducing (`label==1`); evaluate line metrics on TP predicted buggy commits per upstream `run.py`.
- **Reason:** Traced from paper task definition + `JITFine/concat/run.py` + line-label README.
- **Alternatives considered:** Rank all changed lines including deletes by default (rejected for default compatibility).
- **Reversible:** Ablations may include deletes later with explicit protocol note.
- **Gate affected:** DATASET_PROVENANCE_GATE, XAI_GATE, ANALYSIS_GATE

## 2026-09-29T23:55:00+02:00 — No raw redistribution without license

- **Decision:** Classify code/dataset licenses as NONE_FOUND and redistribution as NOT_ESTABLISHED; never commit/mirror `data.zip` or raw extracts to our GitHub/Zenodo; point replicators upstream.
- **Reason:** No LICENSE/COPYING at frozen revision; public download ≠ redistribution grant.
- **Alternatives considered:** Assume public GitHub implies redistributable (rejected).
- **Reversible:** Yes if explicit permission/license later established.
- **Gate affected:** DATASET_PROVENANCE_GATE, RELEASE_GATE

## 2026-09-29T23:55:00+02:00 — Defer archive inspection; do not download yet

- **Decision:** Mark DATASET_PROVENANCE_GATE=PASS without downloading `data.zip`; leave ACQUISITION/SCHEMA sub-gates NOT_STARTED.
- **Reason:** Provenance/semantics sufficiently documented from paper + remote code/docs + GitHub API metadata; pickle internals require acquisition phase.
- **Alternatives considered:** Download now to finish schema (rejected by task gate).
- **Reversible:** N/A (next gate opens acquisition).
- **Gate affected:** DATASET_GATE

## 2026-09-29T23:53:00+02:00 — Acquire frozen JIT-Fine data.zip

- **Decision:** Download `data.zip` from `jacknichao/JIT-Fine@584799fdec6095ab75a45fd2a5f8db5b12163aa5` to `data/raw/upstream/data.zip`; establish SHA-256 `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`; verify Git blob SHA-1 `6cd2f45d97a7c430533cde382be6bf42d9ff3649`.
- **Reason:** DATASET_ACQUISITION_GATE opened; immutable identity required before schema work.
- **Alternatives considered:** Nested revision subdirectory from earlier plan draft (superseded by gate-mandated flat path); mirror fallback (unnecessary — authoritative URL succeeded).
- **Reversible:** No for the frozen local bytes without a new acquisition decision.
- **Gate affected:** DATASET_ACQUISITION_GATE

## 2026-09-29T23:53:00+02:00 — Leave archive unextracted; defer pickle

- **Decision:** Do not extract `data.zip`; do not execute pickle/pandas/joblib/torch loads; schema remains unvalidated.
- **Reason:** Acquisition gate forbids extraction and pickle execution; schema is a separate gate.
- **Alternatives considered:** Peek pickles for early counts (rejected).
- **Reversible:** Yes under DATASET_SCHEMA_VALIDATION_GATE with controlled protocol.
- **Gate affected:** DATASET_ACQUISITION_GATE, DATASET_SCHEMA_VALIDATION_GATE

## 2026-09-29T23:53:00+02:00 — Redistribution policy unchanged after download

- **Decision:** Keep code/dataset licenses NONE_FOUND and redistribution NOT_ESTABLISHED; keep raw archive gitignored; do not upload to Zenodo/GitHub.
- **Reason:** Download does not grant redistribution rights.
- **Alternatives considered:** Treat public GitHub bytes as redistributable (rejected).
- **Reversible:** Yes if explicit license/permission later established.
- **Gate affected:** DATASET_ACQUISITION_GATE, RELEASE_GATE

## 2026-09-30T00:05:00+02:00 — Schema validation PASS; freeze empirical facts

- **Decision:** Mark DATASET_SCHEMA_VALIDATION_GATE=PASS and DATASET_GATE=PASS after seven-member extract + static pickle PASS + empirical audit.
- **Reason:** Commit IDs unique; split intersections empty; changes/features exact alignment; labels float {0.0,1.0}; line-label DataFrame usable for all 475 test positives (L4=475); published 27319/2332/21 MATCH.
- **Alternatives considered:** FAIL on chronological mismatch (rejected: DOCUMENTATION MISMATCH, not ID leakage).
- **Reversible:** No for measured counts without re-audit.
- **Gate affected:** DATASET_SCHEMA_VALIDATION_GATE, DATASET_GATE

## 2026-09-30T00:05:00+02:00 — Primary key and label coding frozen

- **Decision:** Primary key = `commit_hash` / changes commit-id string; commit and line labels are float `{0.0,1.0}` with 1.0 positive.
- **Reason:** Empirically unique; matches features.is_buggy_commit.
- **Alternatives considered:** project+commit composite (unnecessary for uniqueness).
- **Reversible:** Only if later artifact revision contradicts.
- **Gate affected:** DATASET_SCHEMA_VALIDATION_GATE

## 2026-09-30T00:05:00+02:00 — Line-label scope and quirks recorded

- **Decision:** Record that line-label pickle covers test positives only; deleted rows labeled 0.0 never 1.0; changes `added_code`/`removed_code` are sets (order not preserved).
- **Reason:** Empirically measured; impacts future token-line mapping and train/valid localization.
- **Alternatives considered:** Treating deleted as unlabeled (rejected: field present).
- **Reversible:** N/A (factual).
- **Gate affected:** DATASET_SCHEMA_VALIDATION_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-09-30T00:05:00+02:00 — LOCALIZATION_DENOMINATOR_DECISION remains OPEN

- **Decision:** Do not freeze RQ1 denominator; keep OPEN despite L0–L4 counts and JIT-Fine predicted-positive conditioning.
- **Reason:** Orchestrator must choose evaluation population explicitly.
- **Alternatives considered:** Silently adopt JIT-Fine TP-only subset (rejected).
- **Reversible:** Yes when orchestrator decides.
- **Gate affected:** ANALYSIS_GATE, XAI_GATE

## 2026-09-30T00:30:00+02:00 — LOCALIZATION_DENOMINATOR_DECISION CLOSED at N=475

- **Decision:** Freeze `PRIMARY_RQ1_POPULATION` = all gold-positive test commits with valid mapped ground truth; nominal N=475. Do **not** condition primary RQ1 on `model_predicted_positive` or classification correctness. TP/FN stratification may be secondary.
- **Reason:** Orchestrator methodological freeze; JIT-Fine TP-only subset is compatibility-only.
- **Alternatives considered:** Primary = predicted-positive ∩ gold-positive (rejected for primary RQ1).
- **Reversible:** Only with explicit protocol revision.
- **Gate affected:** ANALYSIS_GATE, XAI_GATE, DIFF_RECONSTRUCTION_GATE

## 2026-09-30T00:30:00+02:00 — Upstream sets insufficient; reconstruct via Git

- **Decision:** Do not use frozen `added_code`/`removed_code` sets as structured decoder input. Reconstruct ordered diffs from Apache Git mirrors under `data/raw/source_repos/` with `first_parent` and documented normalization.
- **Reason:** Sets discard order, multiplicity, file, hunk, and line numbers; internal JSON texts mismatch pickle labels (PARTIAL internal recovery only).
- **Alternatives considered:** Trust `buggy_changes_with_buggy_line.json` file keys (rejected: text mismatch); invent new normalization to force 100% set match (rejected).
- **Reversible:** If authoritative ordered patches appear in a future artifact revision.
- **Gate affected:** DIFF_RECONSTRUCTION_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-09-30T00:30:00+02:00 — Parent strategy first_parent

- **Decision:** Freeze parent selection as first parent (`commit^1` / first of `rev-list --parents`); root commits vs empty tree via `git mktree`.
- **Reason:** Standard Git first-parent diff; upstream merge rule not recovered as published extractor; empirical audit uses this reproducibly.
- **Alternatives considered:** All parents; merge-base (deferred without evidence).
- **Reversible:** If extraction-source evidence contradicts.
- **Gate affected:** DIFF_RECONSTRUCTION_GATE

## 2026-09-30T00:30:00+02:00 — Line identity design + DIFF_RECONSTRUCTION_GATE FAIL

- **Decision:** Adopt stable line ID `(commit, file, hunk, change_type, old_lineno, new_lineno, occurrence_index)` and hunk ID `(commit, file, hunk_index)`. Mark `DIFF_RECONSTRUCTION_GATE=FAIL` because positive GT mapping is incomplete (1458/2060 exact unique; usable RQ1 235/475; set EQ ≈32%). Keep `TOKEN_LINE_MAPPING_GATE=IN_PROGRESS`. Keep `CONTEXT_POLICY=OPEN`.
- **Reason:** Criterion I (essentially complete positive-label map without heuristics) unmet; ambiguity must not be hidden by first-hit matching.
- **Alternatives considered:** PASS with 99.5% commit reconstruction alone (rejected: RQ1 positives not essentially complete); fuzzy text map (rejected).
- **Reversible:** Yes if reverse-engineering recovers exact extractor equivalence and remaps positives.
- **Gate affected:** DIFF_RECONSTRUCTION_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-09-30T08:25:00+02:00 — Set-equivalence demoted to diagnostic; Layer A identified

- **Decision:** Whole-commit set equivalence to lossy `added_code`/`removed_code` is **diagnostic only**, not a validity criterion for this study. Identify Layer A nested JSON as richest authoritative line-label source. Freeze `CANONICAL_MODEL_INPUT_SOURCE` = ordered first-parent Git diff; `GROUND_TRUTH_SOURCE` intent = Layer A.
- **Reason:** Sets are known-lossy; paper does not require replicating JIT-Fine semantic-set inputs; needs authentic ordered diffs + trustworthy line GT.
- **Alternatives considered:** Keep set EQ as PASS/FAIL criterion (rejected).
- **Reversible:** No for diagnostic demotion without protocol revision.
- **Gate affected:** GROUND_TRUTH_LINEAGE_GATE, CANONICAL_DIFF_GATE

## 2026-09-30T08:25:00+02:00 — GROUND_TRUTH_LINEAGE_GATE / CANONICAL_DIFF_GATE FAIL

- **Decision:** Mark both gates **FAIL**. Do **not** redefine RQ1 N from 475 to mapped subset (352 POSITIVE_GT_COMPLETE / 109 FULL). Report unresolved: 246 ambiguous + 1 missing of 2111 Layer-A positives; A↔B PARTIAL (no published flatten script).
- **Reason:** Orchestrator—not the audit script—decides subset acceptability; essentially-complete positive mapping unmet.
- **Alternatives considered:** PASS with N=352 (forbidden by gate instructions).
- **Reversible:** Yes if mapping completes or orchestrator explicitly accepts a subset.
- **Gate affected:** GROUND_TRUTH_LINEAGE_GATE, CANONICAL_DIFF_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-10-01T04:50:00+02:00 — JIT-Block audit PASS; set EQ remains diagnostic

- **Decision:** Freeze JIT-Block evidence at `hangters/JIT-Block@d82cc67…` (DOI 10.1111/exsy.13702). Verify 178 exclusions are all non-defective (78 train / 43 valid / 57 test); all 475 positives retained; line-label pickle BYTE_IDENTICAL to JIT-Fine. Mark `JITBLOCK_REPLICATION_AUDIT_GATE=PASS`. Keep historical DIFF/LINEAGE/CANONICAL fails visible.
- **Reason:** External reconstruction corroborates Git recovery + exclusion claims without replacing our split.
- **Alternatives considered:** Adopt JIT-Block filtered cohort as primary split (rejected).
- **Reversible:** Yes with new revision freeze.
- **Gate affected:** JITBLOCK_REPLICATION_AUDIT_GATE

## 2026-10-01T04:50:00+02:00 — RQ1 universe Policy A; UNKNOWN≠NEGATIVE

- **Decision:** Freeze primary RQ1 candidate universe as \(U_{\mathrm{JITFINE}}\) labelled added rows on all 475 gold-positive test commits (18615 cand / 2060 pos / 16555 neg / 0 unknown). Full-Git effort/IFA invalid while unknowns remain. Policy C usable N=58 for optional full-Git ablation. Policy D (352) not valid for IFA/effort. Implement metric guard refusing UNKNOWN. Mark `RQ1_LABEL_UNIVERSE_GATE=PASS`.
- **Reason:** Published JIT-DL metrics are defined on the flat labelled pickle, not on all raw-Git lines; coercing missing abl to 0 is unjustified.
- **Alternatives considered:** Primary N=352 or N=109 (rejected for effort metrics / sample-size chasing).
- **Reversible:** Only with explicit protocol revision.
- **Gate affected:** RQ1_LABEL_UNIVERSE_GATE, ANALYSIS_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-10-01T05:30:00+02:00 — Policy A primary; bridge FAIL; tokenizer waits

- **Decision:** Confirm `PRIMARY_RQ1_POLICY=POLICY_A` (N=475; 18615/2060/16555/0). Reject N=352 and N=58 as primary. Full-Git unknowns stay `NOT_IN_RQ1_UNIVERSE`. Freeze `CANONICAL_MODEL_INPUT_SOURCE` = ordered historical first-parent Git reconstruction. Mark `POLICY_A_CANONICAL_BRIDGE_GATE=FAIL` (18467/18615 unique; 148 NOT_FOUND incl. 1 positive; JIT-Block producer ABSENT). Keep `TOKEN_LINE_MAPPING_GATE=IN_PROGRESS` without tokenizer work until bridge completeness is resolved by orchestrator.
- **Reason:** Policy A matches published labelled-universe metrics; Git reconstruction preserves files/hunks/linenos/duplicates for the decoder model; incomplete deterministic location recovery and missing producer block a PASS.
- **Alternatives considered:** Adopt COMPLETE_POLICY_A_COMMIT_COUNT=403 as new N (deferred to orchestrator); fuzzy matching (forbidden); treat unknowns as negative (forbidden).
- **Reversible:** Yes if residual 148 rows gain deterministic locations or orchestrator accepts an explicit subset.
- **Gate affected:** POLICY_A_CANONICAL_BRIDGE_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-10-01T05:45:00+02:00 — Residual closure FAIL; complete-case readiness PASS

- **Decision:** Close further reconstruction loops. Mark `POLICY_A_RESIDUAL_CLOSURE_GATE=FAIL` (final unique maps 18498/18615; zero-map 117; positives 2060/2060 including previously missing positive). Mark `POLICY_A_COMPLETE_CASE_READINESS_GATE=PASS` for N=413 complete commits (21/21 projects; size-associated exclusion bias documented). Do **not** auto-promote complete-case to primary. Do not tokenize until orchestrator chooses population policy.
- **Reason:** Source-approved transforms + positional bijections exhausted deterministic recovery; 94 rows are dataset-canonical conflicts vs first-parent adds; stop rule forbids endless recovery.
- **Alternatives considered:** Another fuzzy/heuristic pass (rejected); silent N=413 primary (rejected — orchestrator only).
- **Reversible:** Only if new authoritative producer evidence appears.
- **Gate affected:** POLICY_A_RESIDUAL_CLOSURE_GATE, POLICY_A_COMPLETE_CASE_READINESS_GATE, TOKEN_LINE_MAPPING_GATE

## 2026-10-01T07:45:00+02:00 — Complete-case primary RQ1; token-line mapping PASS

- **Decision:** Freeze `PRIMARY_RQ1_POLICY=POLICY_A_COMPLETE_CASE` (N=413; 13412/1712/11700; exclude 62 mapping-incomplete). Freeze CHANGED_ONLY + context 0 / CTX3 ablation / max_length 2048+4096 / STABLE_LINE_ID_V1 with `ordered_position`. Build `canonical_v1` deterministically. Mark `TOKEN_LINE_MAPPING_GATE=PASS` (Qwen fast offsets; 27319/27319; 100/100; label tokens 15/16). Llama ACCESS_BLOCKED. Do not train.
- **Reason:** Orchestrator stop rule; complete-case is the only fully linked labelled universe; bias documented; tokenizer evidence complete for M1.
- **Alternatives considered:** Keep N=475 with partial maps (invalid for primary metrics); fuzzy recovery (forbidden).
- **Reversible:** Only via explicit protocol amendment.
- **Gate affected:** TOKEN_LINE_MAPPING_GATE, PILOT_GATE, ANALYSIS_GATE

## 2026-10-01T11:33:14+02:00 — PILOT_TRAINING_GATE PASS (M1 QLoRA E2E)

- **Decision:** Mark `PILOT_TRAINING_GATE=PASS`. Freeze M1 pilot stack: Qwen rev `c03e6d358207e414f1eca0bb1891e29f1db0e242`, NF4 QLoRA r=16/α=16/dropout=0.05 on q/k/v/o/gate/up/down_proj, causal one-token targets 15/16, restricted two-class softmax, seed 42, max_length 2048, TRAIN+VALID only. Stage A N=32 (16/16) reached 32/32; Stage B N=2048 natural prevalence (174/1874, 21 projects) one pass 128 steps; full valid ROC-AUC≈0.778 PR-AUC≈0.218 (**ADEQUATE** ranking). Hard@0.5 predicts all-negative (max p≈0.24) — diagnostic threshold only, not frozen. Keep `FULL_TRAINING_GATE` / `ATTRIBUTION_GATE` = NOT_STARTED. No test inference.
- **Reason:** Gate purpose is pipeline correctness, not final paper metrics; Stage A + contracts + full-valid ranking prove M1 works end-to-end without leakage or test contamination.
- **Alternatives considered:** Tune LR/LoRA/imbalance to lift F1@0.5 (forbidden this gate); proceed to full 16374 train (forbidden until FULL_TRAINING_GATE).
- **Reversible:** Yes with explicit protocol amendment; do not silently change frozen data/prompt/token IDs.
- **Gate affected:** PILOT_TRAINING_GATE, FULL_TRAINING_GATE, ATTRIBUTION_GATE

## 2026-10-01 — ATTRIBUTION_INFRASTRUCTURE_GATE (parallel worktree)

- **Decision:** Implement attribution / RQ metric **infrastructure** on branch `parallel/attribution-infra` from committed base `9c93eaa`, without disturbing the primary training worktree. Canonical M1 explanation target = `s = logit_1 - logit_0`. Occlusion sign frozen as `delta = s(x) - s(x\\R)`. IFA indexing aligned with existing guard: `ZERO_BASED_FALSE_ALARM_COUNT`. Line aggregation candidates SUM/MEAN/MAX_ABS_WITH_SIGN (SUM primary *candidate*, not frozen). Adapter paths unresolved until FULL_TRAINING completes. Mark `ATTRIBUTION_RESULTS_GATE` / `RQ1_RESULTS_GATE` = NOT_STARTED. Do not load 7B or produce scientific attribution results in this gate.
- **Reason:** Parallel engineering while M1 final trains; interfaces and CPU synthetic tests only.
- **Alternatives considered:** Develop in training worktree (rejected — risk to live run); bind seed-13 intermediate adapters (rejected).
- **Reversible:** Yes via protocol amendment for metric/method freezes.
- **Gate affected:** ATTRIBUTION_INFRASTRUCTURE_GATE, ATTRIBUTION_RESULTS_GATE, RQ1_RESULTS_GATE

## 2026-10-01 — ATTRIBUTION_PROTOCOL_FREEZE_GATE

- **Decision:** Freeze ATTRIBUTION_PROTOCOL_V1 before any scientific M1 attribution results. Primary RQ1 ranking for signed methods = ABS_DESCENDING; attention = RAW_DESCENDING; secondary SIGNED_POSITIVE_DESCENDING. LINE_REDUCTION primary SUM / sensitivity MEAN. Attention primary ATTENTION_LAST_MEAN_HEAD (proxy, not presumed faithful). Faithfulness primary LOGIT_CONTRAST; secondary restricted binary probability. IG primary ZERO_EMBEDDING + GAUSS_LEGENDRE 50→100 retry (E_rel≤0.05) with PAD sensitivity; pad=`<|endoftext|>` id 151643 (special; not neutral). Polarity RELATIVE_POLARITY_EPS_V1. RQ1 visible N=304 (2048) / ablation 345 (4096). Random RQ1 repeats=100. All three M1 seeds aggregated. Hash recorded in artifacts/attribution_protocol/protocol_manifest.json.
- **Reason:** Separate where/magnitude (RQ1) from polarity (RQ3) and faithfulness (RQ2); prevent result-dependent methodological shopping.
- **Alternatives considered:** SIGNED primary RQ1 (rejected — bakes polarity); PAD as primary IG baseline (rejected — sensitivity only); MEAN as primary aggregation (rejected — different estimand).
- **Reversible:** Only via new hashed protocol version + orchestrator approval.
- **Gate affected:** ATTRIBUTION_PROTOCOL_FREEZE_GATE, ATTRIBUTION_RESULTS_GATE, RQ1_RESULTS_GATE

## 2026-10-01 — ATTRIBUTION_PROTOCOL_AMENDMENT_GATE (V1.1)

- **Decision:** Amend frozen V1 into ATTRIBUTION_PROTOCOL_V1.1 without overwriting V1. Preserve V1 hash `73f0f891…`. Distinguish SEGMENT_DELETE_V1 (occlusion) vs PAYLOAD_BLANK_V1 (primary RQ2). RQ2 fractions {10,20,30,50}% with k=max(1,ceil(fN)). Define deletion/insertion AOPC. RQ2/3/4 cohort = 475 positive TEST (truncated eligible on visible input); RQ1 primary remains N=304. Freeze missingness rules, ATTENTION_TOP2_HUNK_OCCLUSION_SIGN_V1, DIFF_POLARITY_SWAP_V1. Test-file category = PENDING_AUDIT.
- **Reason:** Completeness gaps that would otherwise force post-hoc operator/cohort choices after results.
- **Alternatives considered:** Reuse SEGMENT_DELETE for RQ2 (rejected — self-evaluation); shrink RQ234 to 304 (rejected — distinct estimand).
- **Reversible:** Only via new hashed protocol version.
- **Gate affected:** ATTRIBUTION_PROTOCOL_AMENDMENT_GATE, ATTRIBUTION_RESULTS_GATE

## 2026-10-01 — STATISTICAL_PROTOCOL_FREEZE_GATE

- **Decision:** Freeze STATISTICAL_ANALYSIS_PROTOCOL_V1 before scientific attribution results. PRIMARY_STATISTICAL_UNIT=COMMIT; min_common_valid_seeds=2; Wilcoxon two-sided Pratt; primary effect=matched-pairs rank-biserial; Cliff's δ secondary legacy only; bootstrap=10000 commit-cluster percentile; Holm FWER α=0.05 by RQ family; RQ endpoints/directions frozen; random perms collapsed before inference; Scott-Knott not primary; parent ATTRIBUTION_PROTOCOL_V1_1 hash ae710257…. Record STATISTICAL_PROTOCOL_HASH in artifacts/statistical_protocol/.
- **Reason:** Prevent pseudoreplication and result-dependent statistical shopping.
- **Alternatives considered:** Flatten seed×commit (rejected); Cliff's δ as primary (rejected — unpaired); BH instead of Holm (rejected).
- **Reversible:** Only via new hashed statistical protocol version.
- **Gate affected:** STATISTICAL_PROTOCOL_FREEZE_GATE, ATTRIBUTION_RESULTS_GATE, ANALYSIS_GATE

## 2026-10-01 — Claude pre-attribution design review archived

- Source: Claude review, verdict **B**.
- Artefact: `docs/reviews/CLAUDE_DESIGN_REVIEW_2026-10-01.md` (copy also under `paper/docs/`).
- BLOCKER flagged: **C1** (faithfulness sign / AOPC primary definition).
- Protocol hashes **unchanged** in this step; no test attribution opened.
- Recommended next gate: protocol amendment + validation rehearsal (C14) before test attribution.

# EXPERIMENT_PROTOCOL_V0.md

Pre-experimental protocol. Purpose: prevent accidental methodological drift before experiments begin.

Values below are **planned protocol**, not experimental results.

Anything marked **TO VERIFY FROM PRIMARY SOURCE** must be confirmed against the authoritative paper/dataset release before implementation.

---

## PRIMARY DATASET

- Name: **JIT-Defects4J** (canonical manuscript spelling; upstream README often writes JIT-Defect4J for the same artifact)
- Defining publication: Ni et al., ESEC/FSE 2022, DOI **10.1145/3540250.3549165**
- Authoritative upstream: `https://github.com/jacknichao/JIT-Fine` revision **`584799fdec6095ab75a45fd2a5f8db5b12163aa5`**
- Authoritative archive: `data.zip` (remote size 75326372 bytes; git blob SHA-1 `6cd2f45d97a7c430533cde382be6bf42d9ff3649`; **not downloaded yet**)
- Schema: expected contract in `docs/DATASET_SCHEMA_CONTRACT.md` — **NOT YET VALIDATED AGAINST ARCHIVE**
- Redistribution / license for packing raw data into this repo: **NOT_ESTABLISHED** (no LICENSE found; raw data remains gitignored; do not mirror to GitHub/Zenodo)

## SPLIT

- Policy: **USE AUTHOR-PROVIDED SPLIT MEMBERSHIP AS FROZEN**
- Source classification: **AUTHOR_PROVIDED**
- Train: `data/jitfine/changes_train.pkl`, `data/jitfine/features_train.pkl`
- Validation: `data/jitfine/changes_valid.pkl`, `data/jitfine/features_valid.pkl`
- Test: `data/jitfine/changes_test.pkl`, `data/jitfine/features_test.pkl`
- Line labels: `data/jitfine/changes_complete_buggy_line_level.pkl`
- Archive acquisition: **complete** — local `data/raw/upstream/data.zip`; SHA-256 `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`; Git blob SHA-1 verified; seven `data/jitfine/` members extracted and schema-validated.
- Measured sizes: train **16374**, valid **5465**, test **5480**, total **27319**; positives **2332** (train 1390 / valid 467 / test 475)
- Projects: **21** (all present in each split)
- Commit label coding: float `{0.0,1.0}` (`is_buggy_commit` / changes labels)
- Line-label artifact: DataFrame; float `{0.0,1.0}`; **test positives only**; deleted labels all `0.0`
- Change lines: `added_code`/`removed_code` as **`set[str]`** (order not preserved)
- Cross-split commit intersections: **0**
- L0–L4 (test): 5480 / 475 / 475 / 475 / 475
- Paper protocol (§6.1) chronological train≤test: only **10/21** projects under unix timestamps; valid not between train/test (**DOCUMENTATION MISMATCH**)
- **LOCALIZATION_DENOMINATOR_DECISION: CLOSED**
- **PRIMARY_RQ1_POPULATION:** all gold-positive test commits with valid mapped ground truth (nominal **N=475**)
- **DO_NOT_CONDITION_PRIMARY_RQ1_ON_PREDICTED_POSITIVE:** primary RQ1 localization must not require `model_predicted_positive` or classification correctness; TP/FN stratification may be secondary later
- Diff reconstruction (audit): usable exact-unique positive mapping currently **235/475** under documented Git+normalization; remainder escalated (see `docs/DIFF_RECONSTRUCTION_REPORT.md`); `DIFF_RECONSTRUCTION_GATE=FAIL`
- **CONTEXT_POLICY: OPEN**
- Pickle schemas / row-level exports: not for git; see `docs/DATASET_EMPIRICAL_PROFILE.md`

## LINE-LABEL SCOPE (FROZEN FOR JIT-FINE COMPATIBILITY)

- Commit positive label: defect-inducing / buggy commit (`label` / `is_buggy_commit` == `1.0`)
- Line positive label: buggy line (`label` == `1.0` on line-label DataFrame)
- Line-label file covers **test gold-positive commits only** (n=475)
- Deleted lines are labeled `0.0` (never `1.0`) in this artifact
- Primary evaluation scope for localization compatibility: **added lines** (JIT-Fine `--only_adds`)
- Changes pickle stores added/deleted texts as **sets** (order not preserved); use line-label `idx` for ordered lines where available

## LOCALIZATION SUBSET (FROZEN DENOMINATOR)

Measured test populations (do not silently drop):

- L0=5480, L1=475, L2=475, L3=475, L4=475

**LOCALIZATION_DENOMINATOR_DECISION: CLOSED**

- **PRIMARY_RQ1_POPULATION** = all gold-positive test commits with valid mapped ground truth
- Nominal N = **475**
- Do **not** condition primary RQ1 on predicted-positive or classification correctness
- Classification-correctness (TP/FN) stratification may be reported as a **secondary** analysis
- Exclusions from reconstruction/mapping failures must be explicit, counted, and reported (current exact-unique usable subset under audit: **235**; not a silent replacement of the denominator)

Reproduce JIT-Fine concat test subset only when explicitly comparing to JIT-Fine published localization numbers:

- gold label == 1 **and** model predicts 1 **and** `[ADD]` in tokens;
- with `--only_adds`, score only added lines
- That conditioning is **compatibility-only**, not the primary RQ1 denominator

## PRIMARY INPUT FORMAT

```
[MSG] commit message
[FILE] path
[HUNK n]
[ADD] added line
[DEL] deleted line
[CTX] context line
```

Every source line must eventually have a stable identity:

- commit
- file
- hunk
- line identifier
- line type
- text
- label where available

## TOKEN–LINE ALIGNMENT

- Must use tokenizer character offsets / `return_offsets_mapping` from a **fast** tokenizer.
- Heuristic token reconstruction is **prohibited**.

## SEQUENCE LENGTH

- Primary max length: **2048** tokens.
- Planned ablation: **4096** tokens if feasible.
- Truncation reporting is mandatory for any result that depends on tokenized commits:
  - percentage of commits truncated;
  - percentage of labeled lines lost through truncation.
- No published result may silently omit truncation effects.

## SEEDS

- **3** seeds per full model configuration.

## PRIMARY MODEL

- `Qwen2.5-Coder-7B-Instruct` (Hugging Face id planned: `Qwen/Qwen2.5-Coder-7B-Instruct`)

### Planned formulations (not implemented in bootstrap)

- **M1 (primary):** decoder-only causal LM fine-tuned to produce one classification token `"0"` or `"1"`; risk score from the two output logits.
- **M2:** same backbone with sequence-classification head.
- **M3:** Llama-3.1-8B with whichever formulation is selected later.
- **Encoder baseline:** CodeBERT or UniXcoder — subject to later protocol verification.

## INITIAL QLoRA TARGET CONFIGURATION

Initial protocol values only:

- 4-bit NF4
- LoRA r=16
- alpha=16–32
- dropout=0.05
- target modules: q / k / v / o / gate / up / down
- initial LR around 2e-4
- 1–2 epochs
- effective batch around 16
- gradient checkpointing

Checkpoint selection (later): validation **AUC-PR**.

## TEST SET DISCIPLINE

The test set must **never** be used to choose:

- thresholds
- aggregation variants
- hyperparameters
- top-k values
- stopping decisions

## CLASS IMBALANCE

Training strategy still to be finalized using **validation only**.

## ATTRIBUTION FAMILIES (planned; not implemented in bootstrap)

| ID | Method |
|----|--------|
| A0 | random |
| A1 | cheap heuristics |
| A2 | final-layer attention |
| A3 | all-layer attention |
| A4 | attention rollout |
| A5 | Gradient × Input |
| A6 | Integrated Gradients |
| A7 | signed line/hunk occlusion |
| A8 | encoder localization baseline |

### Aggregation

- Primary attention aggregation: R1 / Meta-style aggregation as the **predeclared main variant**.
- Other aggregation schemes are **ablations**, not silent replacements of the main variant.

## STATISTICS (applicability TO VERIFY before locking analysis code)

Planned, subject to verification of applicability:

- paired comparisons by commit
- Wilcoxon signed-rank
- Holm correction
- Cliff's delta
- 95% bootstrap CI
- 10,000 bootstrap resamples where computationally reasonable

## MUST VERIFY BEFORE IMPLEMENTATION (REMAINING)

Provenance-resolved (see `docs/DATASET_PROVENANCE_REPORT.md`):

- Defining publication + DOI
- Authoritative upstream + frozen revision
- Author-provided split file names + reuse policy
- Commit / line label high-level semantics
- JIT-Fine localization subset + `--only_adds` behavior
- License search result (NOT_ESTABLISHED)

Still required before/during later gates:

- Archive download integrity (size + SHA-256) — DATASET_ACQUISITION_GATE
- Pickle schema validation vs `DATASET_SCHEMA_CONTRACT.md` — DATASET_SCHEMA_VALIDATION_GATE
- Exact `added_buggy_level` coding and deleted-line label presence in zip
- Validation carve vs paper 80/20
- Exact JIT-Fine metric code vs paper Top-N wording (metrics gate)
- Exact JITLine metric definitions (R8 / baseline code)
- Exact published comparison numbers from primary tables

Do not infer unresolved items from memory.

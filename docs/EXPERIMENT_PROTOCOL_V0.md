# EXPERIMENT_PROTOCOL_V0.md

Pre-experimental protocol. Purpose: prevent accidental methodological drift before experiments begin.

Values below are **planned protocol**, not experimental results.

Anything marked **TO VERIFY FROM PRIMARY SOURCE** must be confirmed against the authoritative paper/dataset release before implementation.

---

## PRIMARY DATASET

- Name: JIT-Defects4J
- Authoritative download location: **TO VERIFY FROM PRIMARY SOURCE**
- Schema: **TO VERIFY FROM PRIMARY SOURCE**
- Redistribution / license for packing raw data into this repo: **TO VERIFY** (raw data gitignored by default)

## SPLIT

- Intent: reproduce the JIT-Fine train / validation / test split.
- Exact split files and hashes: **TO VERIFY FROM PRIMARY SOURCE**

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

## MUST VERIFY FROM PRIMARY SOURCE BEFORE IMPLEMENTATION

- Exact line-label semantics in JIT-Defects4J
- Whether evaluation is restricted exactly to added lines
- Exact JIT-Fine metric definitions
- Exact JITLine metric definitions
- Exact JIT-Fine train/validation/test split
- Exact published comparison numbers

Do not infer these from memory.

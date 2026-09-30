# LINE_LABEL_TRANSFORM_CONTRACT.md

Status: **PARTIALLY DETERMINISTIC — A↔B not fully closed**

## Layer A (source text)

Nested JSON `added[file][i]` / `deleted[file][i]` strings are **original source line texts** (no diff `+`/`-` prefix).

## `raw_changed_line` (Layer B)

| Field | Verdict |
|-------|---------|
| `RAW_LINE_TRANSFORM` | **DETERMINISTIC_TRANSFORM** (partial empirical coverage) |

Observed primary transform from Layer-A text:

1. Insert spaces around non-word characters: `re.sub(r'([^\w\s])', r' \1 ', text)`  
2. Collapse whitespace  
3. Sometimes treat `_` as a separator (`ESCAPE_PATTERN` → `ESCAPE PATTERN`)

**Not identity.** Exact 100% recovery of every B `raw_changed_line` from A was **not** achieved (string-literal edge cases remain).

Among B positive rows vs A `added_buggy` variants: **1865 / 2060** unique match; **48** ambiguous; **147** missing.

## `changed_line` (Layer B)

| Field | Verdict |
|-------|---------|
| Transform | **DETERMINISTIC_TRANSFORM** (upstream function identified) |

Exact function: `JITFine/my_util.py` → `preprocess_code_line`:

- replace `(){}[].,:;` with spaces  
- replace ` _ ` with `_`  
- regex `` ``.*`` ``, `'.*'`, `".*"` → `<STR>`  
- regex `\d+` → `<NUM>`  
- whitespace collapse  

Applying `preprocess_code_line(raw_changed_line)` equals `changed_line` for **6944 / 26104** rows (~26.6%). Higher agreement is expected when applied to the **original** Layer-A string before an alternate spacing pass; residual disagreement is recorded, not forced.

Used by JIT-Fine concat eval for tokenisation of labelled lines (`commit_with_codes`).

## Flattening pipeline A → B

| Status | Detail |
|--------|--------|
| Published script | **NOT FOUND** in frozen JIT-Fine history |
| Consumer | `JITFine/concat/run.py` reads B pickle |
| Empirical A↔B | **PARTIAL**: same 475 commits; pos counts agree on 453/475; added-line counts agree on only 125/475; B is not a lossless flatten of A `added` lists |

`A_TO_B_LINEAGE`: **PARTIAL**

## Label semantics in Layer A

For files present in `added_buggy_level`:

- `added_buggy` ∪ `added_clean` partitions that file’s `added` list (exact on audited files with abl)  
- Positive GT = membership in `added_buggy` (occurrence-aware)

For files **absent** from `added_buggy_level`: lines are **unlabeled** in Layer A (not proven known-negative).

Deleted lines: no positive labels in A or B.

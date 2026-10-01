# RESIDUAL_TRANSFORMS_LEDGER.md

Status: **CLOSED — source-derived only**  
Frozen JIT-Fine revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`  
Frozen JIT-Block revision: `d82cc67f1c696644e9d6d5c80621937aaf36710b` (consumer only)

Every transform below is traced to frozen source or a prior gate contract
validated against that source. No edit-distance / embedding / fuzzy rules.

---

## T1 — `jitfine_preprocess_code_line`

| Field | Value |
|-------|-------|
| Source file | `JITFine/my_util.py` |
| Function | `preprocess_code_line` |
| Revision | `584799f…` |
| Also present | `baselines/JITLine/my_util.py` (same body; optional Python-token filter unused for Java) |

Operations (exact order):

1. Replace each of `(){}[].,:;` with a space  
2. Replace substring ` _ ` with `_`  
3. Regex `` ``.*`` `` → `<STR>`  
4. Regex `'.*'` → `<STR>`  
5. Regex `".*"` → `<STR>`  
6. Regex `\d+` → `<NUM>`  
7. Split on whitespace and re-join with single spaces  

Used to compare Git raw text to Layer-B `changed_line`.

---

## T2 — `punct_space` / RAW_CHANGED_LINE spacing

| Field | Value |
|-------|-------|
| Evidence | `docs/DIFF_NORMALIZATION_CONTRACT.md` step 5; `docs/LINE_LABEL_TRANSFORM_CONTRACT.md` |
| Operation | `re.sub(r'([^\w\s])', r' \1 ', text)` then whitespace collapse |

Produces Layer-B `raw_changed_line` form from source / Git raw on matched samples.

---

## T3 — underscore-as-separator

| Field | Value |
|-------|-------|
| Evidence | `LINE_LABEL_TRANSFORM_CONTRACT.md` (ESCAPE_PATTERN → ESCAPE PATTERN) |
| Operation | `text.replace('_', ' ')` then T2 |

---

## T4 — `normalize_line`

| Field | Value |
|-------|-------|
| Source file | `src/data/git_diff_reconstruction.py` (this repo; encodes DIFF_NORMALIZATION steps 5–7) |
| Operations | T2 + strip one leading `_` from identifier tokens + collapse spaces inside `"..."` literals |

---

## T5 — whitespace collapse

| Field | Value |
|-------|-------|
| Source | Implicit in T1 step 7 and T2 |
| Operation | `" ".join(text.split())` |

---

## Explicitly excluded

- Levenshtein / edit distance  
- Token Jaccard / embeddings / LLM judgment  
- Basename-only path matching  
- Arbitrary regex not listed above  
- First-hit assignment among unordered duplicate candidates (without equal-cardinality
  positional bijection constraints)

---

## Signature equality rule

For strings \(a, b\): match iff

```
approved_signatures(a) ∩ approved_signatures(b) ≠ ∅
```

or

```
jitfine_preprocess_code_line(a) == Layer-B.changed_line
```

Implemented in `src/data/policy_a_residual_closure.py`.

# DATASET_SCHEMA_CONTRACT.md

**STATUS: EXPECTED_FROM_UPSTREAM_DOCUMENTATION — NOT YET VALIDATED AGAINST ARCHIVE**

Derived from JIT-Fine README, line-label README, `JITFine/my_util.py`, `JITFine/concat/run.py`, and Ni et al. ESEC/FSE 2022 — without opening `data.zip`.

---

## Commit-level change pickle (`changes_{train,valid,test}.pkl`)

Expected unpacked structure when loaded with `pandas.read_pickle` / tuple unpack in `TextDataset`:

| Field | Expected type | Semantics | Evidence | Required by our study? | Future transformation |
|-------|---------------|-----------|----------|------------------------|-----------------------|
| commit_ids | sequence aligned with other lists | Commit identifier (hash) | `my_util.py` `commit_ids, labels, msgs, codes = ddata` | yes | map to stable commit ID |
| labels | sequence of ints {0,1} | 1 = defect-inducing commit | `label = int(label)` | yes | keep binary |
| msgs | sequence of strings | Commit message | tokenization of `msg` | yes | become `[MSG]` field |
| codes / files | per-commit structure with `added_code`, `removed_code` | Changed line texts | `file_codes['added_code']`, `removed_code` | yes | map to `[ADD]`/`[DEL]`; may lack per-file path in this view — **UNCERTAIN** whether file path retained inside this pickle |

**Uncertainty:** Whether `codes` is a single dict of lists or per-file nested structure **REQUIRES_ACQUISITION_PHASE**.

---

## Expert feature pickle (`features_{train,valid,test}.pkl`)

| Field | Expected type | Semantics | Evidence | Required? | Future transformation |
|-------|---------------|-----------|----------|-----------|-----------------------|
| commit_hash | string | Join key to changes | `features_data['commit_hash']` | yes | identity |
| la, ld, nf, ns, nd, entropy, ndev, lt, nuc, age, exp, rexp, sexp, fix | numeric | Kamei-style expert features; `fix` cast via `float(bool(x))` | `manual_features_columns` | optional for M1 decoder-only path; useful for encoder baselines | scale as upstream or recompute |

---

## Line-label pickle (`changes_complete_buggy_line_level.pkl`)

From `commit_with_codes` loop:

| Field | Expected type | Semantics | Evidence | Required? | Future transformation |
|-------|---------------|-----------|----------|-----------|-----------------------|
| commit_id | string | Commit hash | unpack `item` | yes | join |
| idx | int/index | Line token/index alignment key | merge on `idx` | yes | map to our line IDs |
| changed_type | string | e.g. `'added'` (and likely deleted) | `--only_adds` filter | yes | preserve |
| label | int {0,1} | 1 = buggy line | metrics | yes | preserve |
| raw_changed_line | string | Original line text | unpack | yes | identity for mapping |
| changed_line | string | Possibly processed line | unpack | maybe | compare to raw |

---

## Original line-level JSON schema (repo doc; not zip)

From `JITFine/labels for each line/readme.md`:

| Path | Semantics | Required? |
|------|-----------|-----------|
| project → commit → added[filepath] | Added lines per file | yes (documentation of origin) |
| project → commit → deleted[filepath] | Deleted lines per file | yes |
| project → commit → added_buggy_level[filepath] | Class of each **added** line | yes |

**Uncertainty:** numeric/boolean coding of `added_buggy_level` **NOT YET VALIDATED**.

---

## Split artifacts

| Artifact | Role |
|----------|------|
| changes_train.pkl / features_train.pkl | Author-provided train membership |
| changes_valid.pkl / features_valid.pkl | Author-provided validation membership |
| changes_test.pkl / features_test.pkl | Author-provided test membership |

No regeneration contract until a generation script is found.

---

## Evaluation-facing derived fields (not stored)

| Name | Semantics |
|------|-----------|
| `[ADD]` / `[DEL]` tokens | Special tokens added by tokenizer in JIT-Fine |
| Attention-aligned line scores | Produced at test time from model attentions |
| only_adds subset | Filter to `changed_type == 'added'` |

---

## Validation checklist (acquisition phase)

- [ ] Confirm tuple arity/types of `changes_*.pkl`
- [ ] Confirm feature columns exactly match `manual_features_columns`
- [ ] Confirm line pickle column order/types
- [ ] Confirm `added_buggy_level` coding
- [ ] Confirm file paths present somewhere or only flattened line lists
- [ ] Confirm hunk identity absent/present

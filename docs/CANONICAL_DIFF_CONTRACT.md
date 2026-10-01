# CANONICAL_DIFF_CONTRACT.md

Status: **PROCEDURE FROZEN — mapping to Layer-A positives incomplete**

## CANONICAL_MODEL_INPUT_SOURCE (frozen intent)

```text
ordered first-parent Git unified diff
parent = features.parent_hashes[0]  # equals git first parent when present
root commits (2 / 27319): empty tree via `git mktree` (empty stdin)
```

Command:

```bash
git --git-dir <bare> -c color.ui=false -c diff.external= -c core.quotepath=false \
  diff --no-ext-diff --no-textconv -U0 <parent> <commit>
```

This study uses JIT-Fine **split**, **commit labels**, and **line labels**, but does **not** claim to replicate JIT-Fine’s lossy `added_code`/`removed_code` **set** input representation.

## Coverage

| Split | Total | Canonical diff available | Failures |
|-------|------:|-------------------------:|---------:|
| train | 16374 | 16374 | 0 |
| valid | 5465 | 5465 | 0 |
| test | 5480 | 5480 | 0 |
| **total** | **27319** | **27319** | **0** |

Previous opennlp/parquet-mr extraction failures were **root commits** hitting a non-local empty-tree OID; fixed via `git mktree`.

## Parent rule (lineage-supported)

- Dataset-wide: **27317** single-parent; **2** roots; **0** merges  
- Among 475 test positives: **all** single-parent  
- `features.parent_hashes[0]` matches Git first parent on audited samples  

**Frozen:** first parent / `parent_hashes[0]`.

## Retained fields

Per changed line: old/new path, hunk ordinal, change type, old/new lineno, ordered position, raw text.

Context lines recoverable with `-U<n>`; **CONTEXT_POLICY remains OPEN**.

## Stable line ID

```text
(commit_hash, canonical_file_path, hunk_index, change_type, old_lineno, new_lineno, occurrence_index)
```

Uniqueness over all reconstructed changed lines: **PASS** (`n_stable_line_ids = 5073440`).

## Set-equivalence diagnostic (NOT a validity criterion)

Historical: EXACT_SET_MATCH 8755/27317 ≈ 32.05% against lossy upstream sets.  
Label: **LOSSY-UPSTREAM-REPRESENTATION COMPARISON** — not canonical reconstruction validity.

## Ground-truth linkage

Canonical diffs are available for all commits. Policy-A (Layer-B) → canonical
line-ID bridge is **incomplete** (18467/18615; see
`POLICY_A_CANONICAL_BRIDGE_REPORT.md`). Layer-A file-aware lineage remains a
bridge aid, not the RQ1 label authority. RQ1 usable population is **not**
silently reduced to the mapped subset.

## Scope separation (frozen)

| Scope | Line set |
|-------|----------|
| RQ1 metrics | \(U_{\mathrm{JITFINE}}\) only (`RQ1_POSITIVE` ∪ `RQ1_NEGATIVE`) |
| RQ2–RQ4 | Full actual model input (may include `NOT_IN_RQ1_UNIVERSE`) |

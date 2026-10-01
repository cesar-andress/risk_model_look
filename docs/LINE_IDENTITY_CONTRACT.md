# LINE_IDENTITY_CONTRACT.md

Status: **STABLE_LINE_ID_V1 FROZEN**

## Motivation

Upstream `added_code`/`removed_code` are lossy sets. Canonical model lines come from
ordered first-parent Git reconstruction (CHANGED_ONLY / CTX3 rendering).

## STABLE_LINE_ID_V1 (context-invariant)

```
(
  commit_hash: str,
  canonical_file_path: str,
  change_type: str,           # added | deleted
  old_lineno: int | None,
  new_lineno: int | None,
  occurrence_index: int,      # among identical (change_type, norm_text) in U0 filtered stream
  ordered_position: int       # 0-based in U0 CHANGED_ONLY filtered changed-line stream
)
```

Human-readable:

```
{commit}|{file}|{change_type}|old{old_or_NA}|new{new_or_NA}|occ{occurrence}|ord{ordered_position}
```

**Why `ordered_position`:** without it, one duplicate key exists on commit
`725fd755…` (CR-mangled hunk headers reuse `new_lineno=422`). Hunk index is **not**
in the line ID because U0 vs U3 hunk boundaries differ.

Uniqueness: enforced over the filtered U0 stream used for model input.

## Hunk identity (separate)

```
hunk_id = (commit, file, representation_variant, hunk_ordinal)
```

U0 and U3 hunks are different objects when Git merges boundaries under context.

## RQ1 status on lines

Within PRIMARY_RQ1_N=413 complete-case commits only:

- `RQ1_POSITIVE` / `RQ1_NEGATIVE` for mapped Policy-A candidates  
- else `NOT_IN_RQ1_UNIVERSE` (never negative)

## Historical note

Earlier IDs included `hunk_index` in the line key; superseded by V1 above for
representation invariance.

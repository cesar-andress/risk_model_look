# LINE_IDENTITY_CONTRACT.md

Status: **DESIGNED — uniqueness proven only on successfully mapped reconstructed lines**

## Motivation

Upstream `added_code`/`removed_code` are Python `set`s: they destroy order, multiplicity, file, hunk, and line numbers.  
Stable scientific IDs must come from reconstructed Git diffs, not from line text.

## Preferred machine key (tuple)

```
(
  commit_hash: str,           # 40-hex
  canonical_file_path: str,   # path on the new side of the diff (+++), else old side
  hunk_index: int,            # 0-based ordinal of @@ hunk within the commit diff
  change_type: str,           # "added" | "deleted"
  old_lineno: int | None,     # deleted/context tracking; None for pure adds
  new_lineno: int | None,     # added tracking; None for pure deletes
  occurrence_index: int,      # 0-based among identical (change_type, norm_text) in commit
)
```

## Human-readable serialization

```
{commit_hash}|{canonical_file_path}|h{hunk_index}|{change_type}|old{old_or_NA}|new{new_or_NA}|occ{occurrence_index}
```

## Semantics

- **canonical_file_path:** for renames, use the new path (`+++ b/...`) when present; record old path separately in reconstruction metadata (do not collapse).
- **hunk_index:** ordinal of hunk headers in the deterministic `git diff -U0` stream (not Python object id).
- **occurrence_index:** disambiguates duplicate identical normalized texts within the same change_type.

## Uniqueness

Among reconstructed filtered lines where mapping succeeded, IDs are unique by construction of `(commit, file, hunk, type, linenos, occ)`.

Audit field: `stable_line_id_unique` in `artifacts/diff_reconstruction/coverage_summary.json`.

## Hunk identity

```
(commit_hash, canonical_file_path, hunk_index)
```

Serialized: `{commit}|{file}|h{hunk_index}`

## Handling gaps

- Missing old/new lineno → use `NA` in serialization; still require file+hunk+occ.
- Unmapped label rows → **no line ID assigned**; commit excluded from RQ1 usable set until resolved.

## Non-goals

- Do **not** use raw line text as primary ID.
- Do **not** assign IDs by first fuzzy text match.

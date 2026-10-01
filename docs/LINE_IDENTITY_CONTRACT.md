# LINE_IDENTITY_CONTRACT.md

Status: **CANONICAL ID FROZEN — Policy-A bridge incomplete (18467/18615)**

## Motivation

Upstream `added_code`/`removed_code` are lossy sets. Layer-A JSON restores file identity for labels. Canonical model lines come from Git diffs.

## Preferred machine key (canonical changed line)

```
(
  commit_hash: str,           # 40-hex
  canonical_file_path: str,   # path on the new side of the diff (+++), else old side
  hunk_index: int,            # 0-based ordinal of @@ hunk within the commit diff
  change_type: str,           # "added" | "deleted"
  old_lineno: int | None,
  new_lineno: int | None,
  occurrence_index: int,      # 0-based among identical (change_type, norm/raw) in commit stream
)
```

Human-readable:

```
{commit_hash}|{canonical_file_path}|h{hunk_index}|{change_type}|old{old_or_NA}|new{new_or_NA}|occ{occurrence_index}
```

## RQ1 candidate line ID

Same as above restricted to `change_type == "added"` **and** membership in
\(U_{\mathrm{JITFINE}}\) (Policy A Layer-B row), plus:

- `ordered_position` within the canonical added stream  
- `ground_truth_label` from Layer-B (`1.0` / `0.0`) when bridged  
- Source row ID `(commit_id, idx)` from Layer-B (immutable; **not** a lineno)

Canonical Git added lines **outside** Policy A are
`NOT_IN_RQ1_UNIVERSE` (never `RQ1_NEGATIVE`). See
`docs/RQ1_CANDIDATE_MASK_CONTRACT.md`.

## Semantics

- **canonical_file_path:** for renames, use new path (`+++`); record old path in reconstruction metadata.  
- **occurrence_index:** disambiguates duplicate identical texts.  
- Line **text is not** the primary ID.

## Uniqueness

Audited over all canonical changed lines in train/valid/test: **unique** (`stable_line_id_unique: true`, n=5073440).

## Hunk identity

```
(commit_hash, canonical_file_path, hunk_index)
```

Do **not** conflate with JIT-Block derived `JITBLOCK_BLOCK_ID` (adjacency
blocks after sorting recovered linenos).

## Ground-truth linkage status

Policy-A → canonical bridge (`POLICY_A_CANONICAL_BRIDGE_GATE`): **FAIL** —
**18467 / 18615** unique mappings; **148** NOT_FOUND; **0** collisions
(see `docs/POLICY_A_CANONICAL_BRIDGE_REPORT.md`). Unmapped Policy-A rows
receive **no** GT-linked line ID.

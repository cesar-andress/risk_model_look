# DIFF_NORMALIZATION_CONTRACT.md

Status: **EMPIRICALLY PARTIAL — NOT SUFFICIENT FOR FULL-CORPUS SET EQUIVALENCE**

## Goal

Transform raw Git unified-diff line text into the string form stored in frozen JIT-Fine:

- `codes[i]['added_code']` / `removed_code` (sets)
- `changes_complete_buggy_line_level.pkl` → `raw_changed_line`

## Verified transforms (traceable)

| Step | Transform | Evidence |
|------|-----------|----------|
| 1 | Unified diff via `git diff --no-ext-diff --no-textconv -U0 <parent> <commit>` | Matches deterministic reconstruction needs |
| 2 | Keep `.java` paths only | Matches fileschanged Java focus; non-Java (e.g. `changes.xml`) absent from sets |
| 3 | Drop blank lines | Empty norms never appear in sets |
| 4 | Drop Java `//`, `/*`, `*`, `*/` comment lines | Removes javadoc noise present in raw diffs but absent from sets on matched samples |
| 5 | Insert spaces around non-word chars, collapse whitespace | `if (this == o)` → `if ( this = = o )` equals `raw_changed_line` on commons-vfs sample |
| 6 | Strip one leading `_` from identifier tokens | Old Ivy fields `_srcivypattern` → `srcivypattern` in sets |
| 7 | Collapse spaces inside `"..."` literals | `" ivy "` → `"ivy"` |

## Explicitly **not** established as complete

- Full reverse-engineering of the original LLTC4J / JIT-Fine extraction pipeline source that produced the pickles
- Why many commits still MISMATCH after the above (~32% EXACT_SET_MATCH under first_parent)
- Whether some commits require non-first-parent merge bases
- Whether additional identifier rewrites exist beyond leading `_`

## Set comparison rule

Compare **sets** of normalized strings (upstream representation collapses multiplicity).

## Line-label mapping rule

Map `raw_changed_line` + `changed_type` onto filtered reconstructed lines by **exact unique** normalized text within the commit.  
Duplicate norms → `AMBIGUOUS_DUPLICATE` (no first-hit heuristic).

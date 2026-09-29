# DATASET_SCHEMA_CONTRACT.md

**STATUS: VALIDATED_AGAINST_FROZEN_ARCHIVE** (fields below marked VALIDATED were empirically verified 2026-09-29)

Archive SHA-256: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`

Normalization is **not** implemented in this gate.

---

## changes_{train,valid,test}.pkl

Top-level: `list` of 4 aligned sequences (**VALIDATED**).

| Upstream name / position | Actual type | Semantics | Nullability | Our future field | Evidence |
|--------------------------|-------------|-----------|-------------|------------------|----------|
| `[0]` commit ids | `list[str]` | commit hash | none observed | `commit_id` | schema audit |
| `[1]` labels | `list[float]` in `{0.0,1.0}` | defect-inducing if 1.0 | none | `commit_label` | profile |
| `[2]` msgs | `list[str]` | commit message | empty possible | `commit_message` | present |
| `[3]` codes | `list[dict]` | change payload | — | — | |
| `codes[i]['added_code']` | `set[str]` | added line texts | empty set possible | `added_lines` (order TBD) | **VALIDATED** |
| `codes[i]['removed_code']` | `set[str]` | deleted line texts | empty set possible | `deleted_lines` (order TBD) | **VALIDATED** |

File path / hunk / line number inside `codes`: **NO** (**VALIDATED**).  
Line order: **not preserved** in sets (**VALIDATED**).

---

## features_{train,valid,test}.pkl

Top-level: `pandas.DataFrame` (**VALIDATED**). Identical columns across splits.

| Upstream name | Actual type | Semantics | Our future field |
|---------------|-------------|-----------|------------------|
| project | object/str | project id | `project` |
| commit_hash | object/str | primary key | `commit_id` |
| author_date / author_date_unix_timestamp | object / numeric | timestamps | optional chronology checks |
| commit_message | object | message | may duplicate msgs |
| la, ld, nf, ns, nd, entropy, ndev, lt, nuc, age, exp, rexp, sexp | numeric | expert features | optional baselines |
| fileschanged | object | file path info (PARTIAL for RQ4) | future path parsing |
| fix | object/bool-like | fix indicator | optional |
| classification | object | classification string | optional |
| is_buggy_commit | float64 `{0.0,1.0}` | commit label | `commit_label` |

---

## changes_complete_buggy_line_level.pkl

Top-level: `pandas.DataFrame` 26104×6 (**VALIDATED**).

| Upstream name | Actual type | Semantics | Notes |
|---------------|-------------|-----------|-------|
| commit_id | object | commit hash | test positives only |
| idx | int64 | line order index | use for order |
| changed_type | object `added`/`deleted` | change kind | |
| label | float64 `{0.0,1.0}` | buggy line if 1.0 | deleted never 1.0 |
| raw_changed_line | object | original text | do not commit to git |
| changed_line | object | processed text | do not commit to git |

Nested `added_buggy_level`: **not present in this pickle** (that name is from upstream JSON docs).  
Equivalent: filter `changed_type=='added'` and read `label`.

---

## Split artifacts

Author-provided membership frozen. Counts VALIDATED in `docs/DATASET_EMPIRICAL_PROFILE.md`.

---

## Open (not normalized yet)

- Stable line IDs
- Recovering file paths per line
- Restoring line order for changes sets via LL `idx` / other sources
- LOCALIZATION_DENOMINATOR_DECISION

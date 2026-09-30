# LINE_LABEL_ARTIFACT_INVENTORY.md

Inventory of upstream line-level label artifacts relevant to JIT-Defects4J / JIT-Fine.

Frozen archive: `data/raw/upstream/data.zip`  
SHA-256: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`  
Upstream revision: `jacknichao/JIT-Fine@584799fdec6095ab75a45fd2a5f8db5b12163aa5`

---

## 1. `JITFine/labels for each line/buggy_changes_with_buggy_line.json`

| Field | Value |
|-------|-------|
| Path (upstream repo) | `JITFine/labels for each line/buggy_changes_with_buggy_line.json` |
| Local audit copy | `data/raw/upstream/internal/buggy_changes_with_buggy_line.json` |
| Container | JSON object |
| SHA-256 | `df15a48f70ecbdf6e5f855d4a6d7ba3f864244f6782922e0ee9faa7e4c8c8429` |
| Size | 55 374 948 bytes |
| Top-level schema | `project → commit_hash → {added, deleted, added_buggy_level}` |
| `added` / `deleted` | `filepath → list[str]` (order preserved; duplicates preserved) |
| `added_buggy_level` | `filepath → {added_buggy: list[str], added_clean: list[str]}` |
| Projects | **26** (superset of the 21 split projects) |
| Commits | **2456** |
| Contains file path? | **YES** |
| Contains order? | **YES** (list order within file) |
| Contains added labels? | **YES** (`added_buggy` / `added_clean`) |
| Contains deleted labels? | **NO** (deleted lists unlabeled) |
| Relationship to test split | All **475** gold-positive test commits present |
| Suspected role | **LAYER A — original nested line-level dataset** (documented in upstream `readme.md`) |
| Evidence | Author repo path + README structure; commit `4e84a50` “append line labels dataset” |
| Provenance class | **AUTHORITATIVE** |

Extra projects beyond the 21-split set: `archiva`, `deltaspike`, `eagle`, `jspwiki`, `systemml`.

---

## 2. `data/jitfine/changes_complete_buggy_line_level.pkl`

| Field | Value |
|-------|-------|
| Archive path | `data/jitfine/changes_complete_buggy_line_level.pkl` |
| SHA-256 | `479b61b138280105573cd4ea38ea6d656850e29f378e9aa63f1c86d195e6e88a` |
| Format | `pandas.DataFrame` 26104 × 6 |
| Columns | `commit_id`, `idx`, `changed_type`, `label`, `raw_changed_line`, `changed_line` |
| Commit coverage | **475** test positives only |
| File path? | **NO** |
| Order? | via `idx` within commit |
| Added labels? | **YES** (`label` float) |
| Deleted labels? | present as `0.0` only |
| Suspected role | **LAYER B — flattened evaluation table** for JIT-Fine concat attention metrics |
| Evidence | Consumed by `JITFine/concat/run.py` (`commit_with_codes`) |
| Provenance class | **AUTHORITATIVE** (released in `data.zip`) |

---

## 3. `data/jitline/changes_complete_buggy_line_level.pkl` (= ngram copy)

| Field | Value |
|-------|-------|
| Archive paths | `data/jitline/...` and `data/ngram/...` (**byte-identical**) |
| SHA-256 | `2d2add19a45ef870…` (shared) |
| Format | DataFrame 327572 × 6 |
| Columns | `commit_hash`, `idx`, `changed_type`, `is_buggy_line`, `raw_changed_line`, `code_change_remove_common_tokens` |
| Commit coverage | **5480** test commits (all test) |
| Positives | **2060** (`is_buggy_line==1`) — same count as JIT-Fine B positives |
| File path? | **NO** |
| Suspected role | Broader flat table for JITLine/ngram baselines; related to B but different column names / preprocessing column |
| Provenance class | **AUTHORITATIVE** (same `data.zip`) |

---

## 4. `data/ngram/test_data_*_onlyadds.txt`

| Field | Value |
|-------|-------|
| Files | `test_data_commit_onlyadds.txt`, `id_onlyadds.txt`, `label_onlyadds.txt`, `line_onlyadds.txt` |
| Role | Parallel arrays mirroring added-line rows (commit, idx, label, line) |
| File path? | **NO** |
| Suspected role | ngram baseline input; derivative of flat line labels |

---

## 5. Upstream documentation

| Path | Role |
|------|------|
| `JITFine/labels for each line/readme.md` | Documents Layer-A nested schema |
| `README.md` | Points eval to `data/jitfine/changes_complete_buggy_line_level.pkl` |

---

## 6. Not found in frozen history

No script in `jacknichao/JIT-Fine` history (`git log -S` / `-G` over all revisions) that **creates** `changes_complete_buggy_line_level.pkl` from the JSON. Flattening code is **absent** from the published tree; only **consumers** exist (`concat/run.py`).

---

## Ranking (richest → flattest)

1. **Layer A JSON** — file keys, order, buggy/clean lists  
2. JITLine/ngram flat pickle — all test commits, still no file keys  
3. JIT-Fine flat pickle — test positives only, eval consumer format  
4. ngram only-adds text dumps  

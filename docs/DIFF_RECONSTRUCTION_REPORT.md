# DIFF_RECONSTRUCTION_REPORT.md

**Gate:** `DIFF_RECONSTRUCTION_GATE`  
**Verdict:** **FAIL**  
**Date:** 2026-09-30  

---

## 1. VERDICT

**FAIL.**

Ordered Git diffs can be obtained for essentially all split commits (27317/27319 reconstructed under `first_parent`; 2 unavailable). Project mirrors and commit objects are available. Stable line/hunk IDs are well-defined on successfully mapped reconstructed lines. Structured `[MSG]/FILE]/HUNK]/ADD]/DEL]/CTX]` input is **partially** feasible from Git.

The gate nevertheless **FAILS criterion I**: positive ground-truth line mapping for the primary RQ1 population (475 gold-positive test commits) is **not** essentially complete without unsupported heuristics.

- Positive label rows: 2060 total; **1458** `EXACT_UNIQUE`; **308** `AMBIGUOUS_DUPLICATE`; **294** `MISSING_DIFF_LINE`
- Commit classes: **65** `FULLY_MAPPED`; **261** `PARTIALLY_MAPPED`; **149** `AMBIGUOUS`; **0** `UNAVAILABLE` (among the 475)
- Usable RQ1 (all positive rows `EXACT_UNIQUE`): **235 / 475**
- Full-corpus set equivalence vs frozen `added_code`/`removed_code`: **8755 / 27317 ≈ 32.0%** `EXACT_SET_MATCH`

---

## 2. WHY UPSTREAM SETS ARE INSUFFICIENT

Frozen `changes_*` store:

```text
codes[i] = { added_code: set[str], removed_code: set[str] }
```

This representation has lost:

- source-line order
- duplicate-line multiplicity
- file identity
- hunk identity
- original line numbers

It **must not** be the final structured decoder input. Sets remain useful only as an equivalence audit target against reconstructed diffs.

---

## 3. INTERNAL ARTIFACT RECOVERY SEARCH

Classification: **PARTIAL_INTERNAL_RECOVERY**.

| Candidate | Finding |
|-----------|---------|
| `changes_*.pkl` codes | Sets only — insufficient |
| `changes_complete_buggy_line_level.pkl` | Ordered rows with `idx`, `raw_changed_line`, labels; **no** file/hunk/linenos |
| `data/ngram/` only-adds text | Mirrors line-label added rows; no file/hunk |
| `buggy_changes_with_buggy_line.json` (internal) | File-keyed lists + buggy buckets; **texts do not match** frozen pickle `raw_changed_line` / `added_code` |
| `data/cc2vec`, `deepjit`, `deeper`, `la`, `jitline` | No richer ordered patch provenance established as equivalent to frozen JIT-Fine sets |

**Conclusion:** exact ordered reconstruction requires **source-repository Git diffs**. Internal artifacts alone are not sufficient for FULL recovery.

---

## 4. `idx` SEMANTICS

**Verified meaning:** within each `commit_id`, `idx` is a contiguous enumeration `0 .. n-1` over rows of `changes_complete_buggy_line_level.pkl` in DataFrame order (typically all **added** rows, then **deleted**).

- **Not** a source line number
- **Not** a hunk ordinal
- Empirically unique within commit; monotonic with gaps absent
- Used as an attention join key in upstream `JITFine/concat/run.py` (`deal_with_attns`)

**Do not** use `idx` as a Git line-number key. It may disambiguate order among label rows but does not locate file/hunk/lineno without an independent reconstruction map.

---

## 5. PROJECT → REPOSITORY PROVENANCE

File: `docs/PROJECT_REPOSITORY_MAP.csv`

| Status | Count |
|--------|------:|
| `STRONGLY_CORROBORATED` | 21 |
| `VERIFIED_FROM_UPSTREAM_METADATA` | 0 |
| `AMBIGUOUS` | 0 |
| `UNRESOLVED` | 0 |

All 21 projects mapped to `https://github.com/apache/<name>.git`. Evidence: Apache naming + **100% commit-object presence** in mirrored repos for the split hashes (see §6). Historical commit hashes are the scientific objects; remote HEAD is recorded only for fetch provenance, not as model input.

Clones live under gitignored `data/raw/source_repos/*.git` (bare mirrors).

---

## 6. COMMIT AVAILABILITY

| Split | Total | Found | Missing | Repo unresolved |
|-------|------:|------:|--------:|----------------:|
| train | 16374 | 16374 | 0 | 0 |
| valid | 5465 | 5465 | 0 | 0 |
| test | 5480 | 5480 | 0 | 0 |
| **total** | **27319** | **27319** | **0** | **0** |

Reconstruction OK (diff extracted): **27317**. **2** commits failed reconstruction extraction (`opennlp`×1, `parquet-mr`×1) despite object presence — classified unavailable for set-equivalence audit, not dropped from availability.

---

## 7. PARENT-SELECTION RULE

**Frozen rule:** `first_parent`.

| Kind | Count (among reconstructed) |
|------|----------------------------:|
| normal (1 parent) | 27317 |
| root / merge (explicitly tallied in this run) | 0 in successful path counter |

Upstream LLTC4J/JIT-Fine extraction source for merge handling was **not** recovered as an authoritative published script inside the frozen replication tree. Empirical default: Git `commit^1` / first parent of `rev-list --parents`. Root commits (if any) use empty-tree via `git mktree` with empty input.

**Merge handling:** first parent only. Not all-parents; not merge-base unless later evidence overturns this.

---

## 8. EXACT GIT DIFF PROCEDURE

Module: `src/data/git_diff_reconstruction.py`  
Script: `scripts/audit_diff_reconstruction.py`

Command (no color, no external diff, no textconv, zero context):

```bash
git --git-dir <bare> -c color.ui=false -c diff.external= -c core.quotepath=false \
  diff --no-ext-diff --no-textconv -U0 <parent> <commit>
```

Root: replace `<parent>` with empty tree OID from `git mktree` (empty stdin).

Parsed fields per changed line: file path, hunk index, change type (`added`/`deleted`), old/new lineno, raw text, normalized text, occurrence index.

---

## 9. UPSTREAM NORMALIZATION

See `docs/DIFF_NORMALIZATION_CONTRACT.md`.

Documented transforms (empirically partial):

1. `.java` paths only  
2. Drop blank lines  
3. Drop Java `//` / `/*` / `*` / `*/` comment lines  
4. Punctuation spacing + whitespace collapse  
5. Strip one leading `_` from identifier tokens  
6. Collapse spaces inside `"..."` literals  

**Status:** insufficient for full-corpus set equivalence (~32% `EXACT_SET_MATCH`). Further transforms **not invented** solely to raise match rate.

---

## 10. ALL-COMMIT SET EQUIVALENCE

Among reconstructed OK commits (n=27317):

| Status | Count |
|--------|------:|
| `EXACT_SET_MATCH` | 8755 |
| `ADDED_MATCH_ONLY` | 987 |
| `DELETED_MATCH_ONLY` | 6466 |
| `MISMATCH` | 11109 |
| Unavailable (reconstruction error) | 2 |

Exact-match rate among OK: **0.3205**.

---

## 11. DUPLICATE-LINE MULTIPLICITY

Upstream sets collapse multiplicity. Reconstructed filtered diffs:

| Metric | Value |
|--------|------:|
| Commits with duplicate normalized added/deleted text | 17373 |
| Test-positive commits with duplicate norm text | 376 |

Text-only mapping is therefore frequently ambiguous even when reconstruction is correct.

---

## 12. 475-COMMIT LINE-LABEL MAPPING

| Commit class | Count |
|--------------|------:|
| `FULLY_MAPPED` | 65 |
| `PARTIALLY_MAPPED` | 261 |
| `AMBIGUOUS` | 149 |
| `UNAVAILABLE` | 0 |
| **Total** | **475** |

Row statuses (all label rows): `EXACT_UNIQUE` 18217; `AMBIGUOUS_DUPLICATE` 3980; `MISSING_DIFF_LINE` 3907.

Primary rule: exact unique normalized text within `(change_type)` — **no** first-hit heuristic.

---

## 13. POSITIVE-LABEL MAPPING

| Metric | Count |
|--------|------:|
| Total positive rows | 2060 |
| Exact unique | 1458 |
| Exact disambiguated (index/metadata) | 0 |
| Ambiguous duplicate | 308 |
| Missing / mismatched | 294 |

**Hard requirement unmet:** not all positive GT lines map exactly uniquely.

Usable RQ1 commits (every positive row `EXACT_UNIQUE`): **235**.

---

## 14. FILE/HUNK/LINE-NUMBER COVERAGE

Among successfully mapped rows (n=18217):

| Field | Coverage |
|-------|---------:|
| File path | 100.0% |
| Hunk index | 100.0% |
| Old line number | 29.07% |
| New line number | 70.93% |

(Added lines carry `new_lineno`; deleted carry `old_lineno` — percentages reflect change-type mix among mapped rows.)

---

## 15. STABLE LINE ID

See `docs/LINE_IDENTITY_CONTRACT.md`.

Machine key:

```text
(commit_hash, canonical_file_path, hunk_index, change_type, old_lineno, new_lineno, occurrence_index)
```

Serialization:

```text
{commit}|{file}|h{hunk}|{type}|old{n|NA}|new{n|NA}|occ{i}
```

Uniqueness audit on mapped reconstructed lines: **`stable_line_id_unique: true`** (n=18217 IDs).

---

## 16. STABLE HUNK ID

```text
(commit_hash, canonical_file_path, hunk_index)
```

n_stable_hunk_ids audited among mapped lines: **3842** (unique by construction of ordinal hunk stream).

---

## 17. STRUCTURED INPUT FEASIBILITY

| Marker | Status | Note |
|--------|--------|------|
| `[MSG]` | **YES** | Commit message available via Git / features |
| `[FILE]` | **PARTIAL** | Recoverable from Git; not from frozen sets; mapping incomplete corpus-wide |
| `[HUNK n]` | **PARTIAL** | Recoverable from Git `-U0` hunk ordinals when reconstruction matches |
| `[ADD]` | **PARTIAL** | Ordered adds from Git; set EQ incomplete vs upstream |
| `[DEL]` | **PARTIAL** | Same |
| `[CTX]` | **YES** (capability) / policy **OPEN** | Deterministic with `-U<n>`; context count not frozen |

`CONTEXT_POLICY: OPEN`.

---

## 18. UNRECOVERED CASES

- **2** commits: reconstruction command failed (`opennlp`, `parquet-mr`) — escalate individually; not silently dropped.
- **~68%** of OK commits: set mismatch under documented normalization (extraction pipeline not fully reverse-engineered).
- **240** of 475 RQ1 commits: at least one positive label ambiguous or missing under exact unique text map.
- Internal JSON file paths **cannot** be used as authoritative for frozen pickle texts (cross-artifact mismatch).

---

## 19. BIAS AUDIT

Unavailable reconstruction (n=2) is **not** concentrated by split (objects found in all splits). Project concentration: single misses in `opennlp` and `parquet-mr` only. Label-bias of set-mismatch is not claimed as causal; mismatch rate is high across projects (see `project_coverage.csv`). Missingness of positive maps is widespread (149 ambiguous commits), not a single-project artifact.

No inferential statistics performed.

---

## 20. FROZEN FACTS

- `LOCALIZATION_DENOMINATOR_DECISION: CLOSED`
- `PRIMARY_RQ1_POPULATION` = all gold-positive test commits with valid mapped ground truth
- Nominal N = **475**; do **not** condition primary RQ1 on `model_predicted_positive` or classification correctness
- Mapped usable N under current exact-unique rule = **235** (remainder escalated, not silently dropped)
- Parent strategy = `first_parent`
- Sets are insufficient as decoder input
- `CONTEXT_POLICY: OPEN`

---

## 21. OPEN DECISIONS

1. **CONTEXT_POLICY** — how many context lines (`-U`) for model input / ablations  
2. Whether a **subset RQ1** (N=235) is acceptable vs further reverse-engineering of LLTC4J extraction  
3. Whether `idx`-ordered label rows can be linked via a stronger extractor than unique-norm text  
4. Handling of the 2 reconstruction-unavailable commits  
5. Secondary stratification by TP/FN after a classifier exists (explicitly secondary)

---

## 22. DIFF_RECONSTRUCTION_GATE

| Criterion | Result |
|-----------|--------|
| A ordered diff source identified | PASS (Git first-parent `-U0`) |
| B project mapping defensible | PASS (21 STRONGLY_CORROBORATED) |
| C parent strategy reproducible | PASS (`first_parent`) |
| D file/hunk recoverable | PARTIAL (when mapped) |
| E line numbers recoverable | PARTIAL (when mapped) |
| F set equivalence audit | FAIL (~32% exact) |
| G multiplicity quantified | PASS |
| H 475 audited | PASS |
| I positive GT essentially complete | **FAIL** |
| J stable line IDs unique | PASS (on mapped subset) |
| K structured input feasible | PARTIAL |
| L full pytest | PASS |

**Gate status: FAIL.**

`TOKEN_LINE_MAPPING_GATE` remains **IN_PROGRESS** (tokenizer offset mapping not started).

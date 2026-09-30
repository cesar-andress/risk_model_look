# GROUND_TRUTH_LINEAGE_REPORT.md

**Gates:** `GROUND_TRUTH_LINEAGE_GATE`, `CANONICAL_DIFF_GATE`  
**Date:** 2026-09-30  

---

## 1. VERDICT

| Gate | Verdict |
|------|---------|
| GROUND_TRUTH_LINEAGE_GATE | **FAIL** |
| CANONICAL_DIFF_GATE | **FAIL** |

**Why FAIL (lineage):** Layer A (nested JSON) is identified and covers all 475 commits with file identity, but A↔B is only **PARTIAL**, and file-aware A→Git mapping leaves **246 ambiguous + 1 missing** positive lines (of **2111** Layer-A positives). Criterion “essentially all positive rows mapped without unsupported heuristics” is **not** met. Nominal RQ1 N remains **475** (not reduced to a mapped subset).

**Why FAIL (canonical):** Canonical Git diffs are available for **27319/27319** with unique stable IDs and a lineage-supported parent rule, but ground-truth↔canonical mapping (gate criterion F) does not meet the required level.

---

## 2. WHY THE PREVIOUS DIFF GATE FAILED

`DIFF_RECONSTRUCTION_GATE` required whole-commit set equivalence to lossy `added_code`/`removed_code` **sets**. That criterion is **inappropriate** for scientific validity of this study: sets discard order/file/hunk/multiplicity. Set EQ (~32%) remains a **diagnostic only**.

---

## 3. ORIGINAL LINE-LABEL ARTIFACTS

See `docs/LINE_LABEL_ARTIFACT_INVENTORY.md`.

Primary: `JITFine/labels for each line/buggy_changes_with_buggy_line.json`.

---

## 4. RICHEST AUTHORITATIVE REPRESENTATION

**Layer A:** `buggy_changes_with_buggy_line.json`  
Provenance: **AUTHORITATIVE** (author repo + README; SHA-256 `df15a48f…8429`).

Schema: `project → commit → {added, deleted, added_buggy_level}` with file-keyed **lists**.

---

## 5. JSON / NESTED ARTIFACT SCHEMA

- `added[file]`: `list[str]`  
- `deleted[file]`: `list[str]`  
- `added_buggy_level[file]`: `{added_buggy: list[str], added_clean: list[str]}`  
- Not parallel int arrays; labels are **text lists** (multiplicity via repeated strings)  
- 26 projects / 2456 commits  

---

## 6. COVERAGE OF 475 TEST POSITIVES

| Metric | Value |
|--------|------:|
| Present in JSON | **475** |
| Missing | **0** |
| With added lines | 475 |
| With ≥1 positive (`added_buggy`) | 475 |

---

## 7. FLATTENING PIPELINE

No producer script in frozen JIT-Fine history. Consumers only (`JITFine/concat/run.py`).  
`A_TO_B_LINEAGE`: **PARTIAL**.

---

## 8. RAW_CHANGED_LINE TRANSFORM

`RAW_LINE_TRANSFORM`: **DETERMINISTIC_TRANSFORM** (partial coverage).  
Primary: punctuation spacing (± underscore-as-separator). Not full identity to Layer A.

---

## 9. CHANGED_LINE TRANSFORM

Upstream `preprocess_code_line` in `JITFine/my_util.py` (**DETERMINISTIC_TRANSFORM**).  
See `docs/LINE_LABEL_TRANSFORM_CONTRACT.md`.

---

## 10. A ↔ B LABEL LINEAGE

| Check | Result |
|-------|--------|
| Same 475 commits | YES |
| Added-row counts equal | 125 agree / 350 disagree |
| Positive counts equal | 453 agree / 22 disagree |
| A positives on 475 | **2111** |
| B positives | **2060** |
| B-pos → A-buggy (variant match) | 1865 exact / 48 amb / 147 miss |
| Label agree on matched | **1865 / 1865** (0 disagree) |

Verdict: **PARTIAL**.

---

## 11. FILE IDENTITY RECOVERY

From Layer A (native file keys), then A→Git:

| Scope | Result |
|-------|--------|
| Path status on A rows mapped | EXACT_PATH dominant (`path_stats`) |
| Positive rows with Git file | **1864 / 2111** `FILE_EXACT_FROM_LINEAGE` |
| Positive unresolved | **247** |

---

## 12. ORDER / MULTIPLICITY

Layer A preserves **within-file list order** and **duplicate texts**.  
Occurrence ordinals assigned within `(commit, file, change_type, text)`.  
B `idx` is a separate flattened enumeration — not proven identical to A file-major order.

---

## 13. FILE-PATH RECONCILIATION

| Class | Count (A rows touched) |
|-------|------------------------:|
| EXACT_PATH | 107273 |
| RENAMED_PATH | 0 |
| DETERMINISTIC_NORMALIZED_PATH | 0 |
| UNRESOLVED_PATH | (included in missing/ambiguous positives) |

No basename-only / fuzzy path matching used.

---

## 14. A/B ↔ GIT MAPPING

Method: commit → **file** → change_type → ordered exact variant match; monotonic neighbor disambiguation only when unique. **No** fuzzy/LLM/Levenshtein.

---

## 15. POSITIVE-LABEL RECOVERY (Layer A → Git)

Denominator = **2111** Layer-A positives on the 475 commits.

| Status | Count |
|--------|------:|
| EXACT_DIRECT | 56 |
| EXACT_FILE_CONSTRAINED | 72 |
| EXACT_OCCURRENCE_CONSTRAINED | 1707 |
| EXACT_SEQUENCE_DISAMBIGUATED | 29 |
| AMBIGUOUS | **246** |
| MISSING | **1** |
| SOURCE_CONFLICT | 0 |

Mapped exact-class total: **1864**. Unresolved: **247**.

---

## 16. NEGATIVE-LINE UNIVERSE

- Where `added_buggy_level` exists for a file: `added_clean` are **known-negative**; partition with `added_buggy` holds on audited files.  
- Files **without** `added_buggy_level`: **55424** added lines on the 475 commits are **unlabeled** in Layer A (must not be silently treated as negative).  
- Primary RQ1 ranks **added** lines; deleted lines are not positive GT.

---

## 17. COMMIT-LEVEL RQ1 RECOVERY

| Class | Count |
|-------|------:|
| FULL_GROUND_TRUTH_RECOVERED (all added A lines mapped) | 109 |
| PARTIAL_POSITIVE_LABEL_RECOVERY | 244 |
| AMBIGUOUS | 122 |
| SOURCE_CONFLICT | 0 |
| UNAVAILABLE | 0 |

| Notion | Count |
|--------|------:|
| POSITIVE_GT_COMPLETE | **352** |
| FULL_LINE_UNIVERSE_COMPLETE | **109** |

Nominal primary population remains **475**.

---

## 18. MERGE / PARENT VALIDATION

- Merges in 475: **0**  
- All 475: single parent  
- Full corpus: 27317 single-parent, 2 roots, 0 merges  
- Rule: `features.parent_hashes[0]` (= Git first parent)

---

## 19. TWO PREVIOUS EXTRACTION FAILURES

Both were **root commits** (empty parent). Cause: hardcoded empty-tree OID absent from bare repo.  
Fix: `git mktree` with empty stdin.  
Re-audit: **0** failures. Neither blocked RQ1 (roots are not among unresolved positive maps as a class).

---

## 20. ALL-COMMIT CANONICAL DIFF COVERAGE

27319 / 27319 available; parse success 27319; failures 0.

---

## 21. CANONICAL MODEL INPUT DECISION

`CANONICAL_MODEL_INPUT_SOURCE` = ordered first-parent Git diff.  
Does **not** require reproducing JIT-Fine sets.

`GROUND_TRUTH_SOURCE` = Layer A JSON.

---

## 22. STABLE LINE ID

`(commit_hash, canonical_file_path, hunk_index, change_type, old_lineno, new_lineno, occurrence_index)`  
Uniqueness: **PASS** (n=5 073 440).

---

## 23. PRIMARY RQ1 USABLE POPULATION

- Nominal N: **475** (unchanged)  
- POSITIVE_GT_COMPLETE: **352** (reported, **not** adopted as silent new denominator)  
- No predicted-positive conditioning  

Orchestrator must decide whether a high-confidence subset is acceptable; this gate does **not** redefine N.

---

## 24. REMAINING CONFLICTS

1. A↔B partial (flat pickle ≠ lossless flatten of JSON added lists)  
2. 247 Layer-A positives not uniquely mapped to Git  
3. Large unlabeled added-line mass (files without `added_buggy_level`)  
4. Flattening producer script absent from published history  

---

## 25. GROUND_TRUTH_LINEAGE_GATE

**FAIL** — richest artifact found and 475 covered, but positive→canonical mapping not essentially complete; A↔B not EXACT.

---

## 26. CANONICAL_DIFF_GATE

**FAIL** — procedure and full-split coverage succeed, but GT mapping criterion F fails.

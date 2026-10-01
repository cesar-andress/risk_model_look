# JITBLOCK_REPLICATION_AUDIT.md

**Gate:** `JITBLOCK_REPLICATION_AUDIT_GATE`  
**Verdict:** **PASS**  
**Date:** 2026-10-01  

---

## 1. Publication provenance

| Field | Value |
|-------|-------|
| Title | A code change-oriented approach to just-in-time defect prediction with multiple input semantic fusion |
| Authors | Teng Huang; Hui-Qun Yu; Gui-Sheng Fan; Zi-Jie Huang; Chen-Yu Wu |
| Venue | Expert Systems |
| Year | 2024 |
| Volume/Issue | 41(12) |
| DOI | **10.1111/exsy.13702** |
| Data availability | Public GitHub artifacts (`hangters/JIT-Block`) |

Verified via DOI/publisher indexing and author PDF (`huang.zj.cn/pdf/J26.pdf`).

---

## 2. Repository provenance

| Field | Value |
|-------|-------|
| URL | https://github.com/hangters/JIT-Block |
| Default branch | `main` |
| License | **NONE_FOUND** (GitHub `license` null) |
| Dataset license | **NOT_ESTABLISHED** |

---

## 3. Frozen revision

| Field | Value |
|-------|-------|
| Immutable SHA | `d82cc67f1c696644e9d6d5c80621937aaf36710b` |
| Note | HEAD at acquisition; scientific inputs are the ZIP blobs at this revision |

---

## 4. Public dataset artifacts

| Artifact | Role |
|----------|------|
| `JIT-Defect4J.zip` | Filtered baseline-style changes/features + **byte-identical** line-label pickle |
| `JIT-Block-Defect4J.zip` | Changed-block reconstructed train/valid/test + combined `features.pkl` |

---

## 5. Acquisition hashes

See `artifacts/jitblock_audit/acquisition_report.json`.

| ZIP | Size | SHA-256 | Git blob SHA-1 |
|-----|-----:|---------|----------------|
| JIT-Defect4J.zip | 20265192 | `1cbb8e43003813a32e960f1860f4ca3611b20701e48bdaa315d4084d7a927bf8` | `705f3e37ad029063c635960804e569f353be2afc` |
| JIT-Block-Defect4J.zip | 20122405 | `a1e45332e782728df03ab564210f8e4734eb673e087441dff4705e7c21857fbd` | `4de8924b59a3349c7a50f322a3c4c1d02c5d8a30` |

ZIP CRC integrity: PASS. Static pickle audit (existing protocol): **PASS** for all extracted members.

---

## 6. Exact reconstruction algorithm

**Producer script:** **ABSENT** from the frozen repository (only consumer `JITBlock/my_util.py` / `run.py`).

**Paper-described procedure** (Expert Systems 2024, reconstruction section):

1. Use Git with commit hash to recover source files  
2. Match JIT-Defect4J line texts to source to recover line numbers  
3. Sort added/deleted lines by line number  
4. Group into continuous **changed blocks**  
5. Remove commits that fail matching (~0.6%)

Classification of algorithm evidence: **AUTHOR_PAPER + RELEASED_OUTPUTS** (not runnable producer).

---

## 7. Changed-block definition

**Relationship to Git hunks:** `DERIVED_FROM_LINE_ADJACENCY` (not identical to Git hunks).

Evidence:

- Paper: continuous segment of ADD/DEL after sorting by recovered line numbers  
- Consumer schema: each block is a flat alternating tuple  
  `('added_code'|'removed_code', text, ...)`  
- Texts appear punctuation-spaced (like Layer-B `raw_changed_line`)

---

## 8. Split mapping

Paper “training = 21839 / testing = 5480” corresponds to our **train∪valid** and **test**.

Artifacts still ship **separate** train/valid/test files.

| Split | Our N | JIT-Block filtered N | Block N |
|-------|------:|---------------------:|--------:|
| train | 16374 | 16296 | 16284 |
| valid | 5465 | 5422 | 5428 |
| test | 5480 | 5423 | 5429 |
| train∪valid | 21839 | **21718** | 21712 |

`unexpected_training_commits` outside our train∪valid: **0**.

**Do not** overwrite our frozen train/valid/test with JIT-Block’s terminology.

---

## 9. 121 + 57 exclusions

Independently measured removals vs our frozen changes:

| Our split | Removed | Positives removed |
|-----------|--------:|------------------:|
| train | **78** | 0 |
| valid | **43** | 0 |
| test | **57** | 0 |
| train+valid | **121** | 0 |
| **total** | **178** | **0** |

Matches the publication’s 121 + 57.

---

## 10. Labels of excluded commits

All **178** excluded commits have our frozen commit label **0.0** (non-defect-inducing).  
Publication claim verified.

---

## 11. Original 475-positive coverage

| Variant | 475 present | Missing |
|---------|------------:|--------:|
| Filtered `JIT-Defect4J` test | 475 | 0 |
| Block `JIT-Block-Defect4J` test | 475 | 0 |

---

## 12. Ordered reconstruction schema

Block `codes[i]` = `list[block]`, block = alternating `(kind, text)` with `kind ∈ {added_code, removed_code}`.

| Field | Present |
|-------|---------|
| commit hash | YES |
| project | PARTIAL (via features) |
| commit message | YES |
| file path | **NO** |
| old/new path | **NO** |
| changed block | YES |
| ADD/DEL identity | YES |
| old/new line number | **NO** (used during construction; not stored in released pickle) |
| ordered position | YES (within/between blocks) |
| label (commit) | YES |
| line label | via separate BYTE_IDENTICAL pickle |

---

## 13. Line-label schema

`changes_complete_buggy_line_level.pkl` in `JIT-Defect4J.zip`:

- **BYTE_IDENTICAL** to our frozen JIT-Fine file  
- SHA-256 `479b61b138280105573cd4ea38ea6d656850e29f378e9aa63f1c86d195e6e88a`  
- 26104 rows; 2060 positives  

---

## 14. JIT-Fine ↔ JIT-Block label relationship

Localization evaluation uses the **same** Layer-B pickle.  
Filtered changes pickles drop 178 clean commits; positives untouched.

---

## 15. Our Git ↔ JIT-Block

- Commit availability / exclusions: aligned with paper; positives retained  
- Block texts often match filtered `added_code`/`removed_code` **sets**, but **1529/5423** test commits differ at set level (normalization/multiplicity/boundary)  
- No file paths / line numbers in released block pickle → cannot claim EXACT equivalence to our canonical Git diffs  
- Classification: **STRUCTURALLY_EQUIVALENT** intent (ordered ADD/DEL blocks) with **TEXT_NORMALIZATION_DIFFERENCE** / **BLOCK_BOUNDARY_DIFFERENCE** residual; **not EXACT** to our Git stream

---

## 16. Unresolved reconstruction cases

- Producer script absent → cannot re-run match failures line-by-line  
- Does not resolve our 247 unresolved Layer-A→Git positive maps (block covers ~1880/2111 A-pos texts; 231 still missing)  
- Slight train/valid/test redistribution between filtered and block ID sets (union identical 27141)

---

## 17. Evidence limitations

Third-party reconstruction; no license; no producer code; paper prose is the only algorithm source.

---

## 18. Gate verdict

**JITBLOCK_REPLICATION_AUDIT_GATE: PASS**

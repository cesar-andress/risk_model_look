# POLICY_A_RESIDUAL_CLOSURE_REPORT.md

**Gate:** `POLICY_A_RESIDUAL_CLOSURE_GATE`  
**Verdict:** **FAIL**  
**Date:** 2026-10-01  

Companion: `POLICY_A_COMPLETE_CASE_READINESS_GATE` = **PASS**  
(see `docs/POLICY_A_COMPLETE_CASE_BIAS_REPORT.md`).

---

## 1. Purpose

Final targeted recovery of the **148** Policy-A rows left `NOT_FOUND` by
`POLICY_A_CANONICAL_BRIDGE_GATE`, then bias-audit the complete-case subset.
No new broad reconstruction project. No tokenizer work.

---

## 2. Starting residual

| | Count |
|--|------:|
| Rows | 148 |
| Positives | 1 |
| Negatives | 147 |
| Commits touched | 72 |

Universe unchanged: 18615 / 2060 / 16555 / 0 unknown within Policy A.

---

## 3. Transform ledger

See `docs/RESIDUAL_TRANSFORMS_LEDGER.md`.

Used: T1 `preprocess_code_line` @ JIT-Fine `584799f…`; T2 punct_space; T3
underscore separator; T4 `normalize_line`; T5 whitespace collapse.

---

## 4. Residual taxonomy (diagnostic, pre-final)

| Category | Count |
|----------|------:|
| FILE_PATH_RECOVERED_NO_TEXT_MATCH | 74 |
| LINE_PRESENT_IN_PARENT_ONLY | 24 |
| PRESENT_IN_DIFF | 23 |
| LINE_PRESENT_BUT_FILTERED | 18 |
| LINE_PRESENT_BOTH_BLOBS_NOT_IN_DIFF | 6 |
| NO_RAW_GIT_TEXT_MATCH | 3 |

---

## 5. Recovery outcomes (final categories for all 148)

| Final category | Count |
|----------------|------:|
| RECOVERED_SOURCE_TRANSFORM_EXACT | 18 |
| RECOVERED_POSITIONALLY_FORCED | 13 |
| RECOVERED_SEQUENCE_FORCED | 0 |
| DATASET_CANONICAL_CONFLICT | 94 |
| AMBIGUOUS | 22 |
| UNRESOLVED | 1 |

Positional recovery required equal-cardinality unmatched intervals between
trusted anchors (same commit/file/change_type); rejected when non-unique.

---

## 6. Missing positive (special case)

| Field | Value |
|-------|-------|
| Commit | `cfa7c5e3bba0efbc88dfb2fcafb983723a1606bc` |
| idx | 2 |
| Project | (see `missing_positive_case.json`) |
| Prior status | NOT_FOUND |
| Final | **RECOVERED_SOURCE_TRANSFORM_EXACT** |
| Evidence | Unique free filtered Git candidate under approved signatures / preprocess↔`changed_line` |

Sanitized detail: `artifacts/residual_closure/missing_positive_case.json`.

---

## 7. Final Policy-A mapping (all 18615)

| Metric | Value |
|--------|------:|
| Unique mappings | **18498** |
| Zero-map | **117** |
| Multi-map | **0** |
| Collisions | **0** |
| Positives mapped | **2060 / 2060** |
| Negatives mapped | **16438 / 16555** |

---

## 8. Complete commits

| | Count |
|--|------:|
| POLICY_A_COMPLETE | **413** |
| Incomplete | **62** |

---

## 9. DATASET_CANONICAL_CONFLICT

94 residuals have no bijection to a first-parent canonical **added** line under
all verified transforms and positional constraints. Dominant diagnostics:

- file known but text absent from diff/blobs as added  
- text in parent only (not an add)  
- text in both blobs but not in first-parent added diff  

These remain Policy-A candidates scientifically; they are **unmapped**, not
relabelled and not moved to `NOT_IN_RQ1_UNIVERSE`.

---

## 10. Stop rule

Further speculative reconstruction is **not** recommended. Residual closure
FAIL is terminal for recovery loops; orchestrator decides primary vs
complete-case from the bias report.

---

## 11. POLICY_A_RESIDUAL_CLOSURE_GATE

**FAIL** — not 18615/18615.

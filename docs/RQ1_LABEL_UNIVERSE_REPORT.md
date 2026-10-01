# RQ1_LABEL_UNIVERSE_REPORT.md

**Gate:** `RQ1_LABEL_UNIVERSE_GATE`  
**Verdict:** **PASS**  
**Date:** 2026-10-01  

---

## 1. Scientific problem

IFA / Recall@20%Effort / Effort@20%Recall require a **fully binary-labelled candidate-line universe**.  
Positive-only completeness (N=352 or N=109) is insufficient if other ranked lines are UNKNOWN.

---

## 2. Original JIT-Fine candidate universe

**Definition (proven in `JITFine/concat/run.py`):**

\[
U_{\mathrm{JITFINE}}(c)=\{ \text{rows in } \texttt{changes\_complete\_buggy\_line\_level.pkl} \mid \texttt{commit\_id}=c \}
\]

With `--only_adds`, restrict to `changed_type == added`.

On our 475 positives:

| | Count |
|--|------:|
| Candidate added lines | **18615** |
| Positive | **2060** |
| Negative | **16555** |
| Unknown | **0** |

---

## 3. Layer-A universe

Nested JSON `added[file]` + `added_buggy_level`:

| | Count |
|--|------:|
| Candidate added | 74489 |
| Positive (`added_buggy`) | 2111 |
| Negative (`added_clean`) | 16954 |
| Unknown (no abl for file) | **55424** |

---

## 4. Layer-B universe

Flat eval pickle (see §2). Completely labelled within \(U_{\mathrm{JITFINE}}\).

---

## 5. JIT-Block universe

Uses **byte-identical** Layer-B pickle for localization.  
DP test cohort filtered to 5423 commits; **all 475 positives retained**.

---

## 6. Canonical Git universe

Java added lines from first-parent diffs on 475 commits:

| | Count |
|--|------:|
| Candidate added | 166035 |
| Approx known pos | 2390 |
| Approx known neg | 19403 |
| Unknown | **144242** |

---

## 7. Exact meaning of missing `added_buggy_level`

**Proven for JIT-Fine/JIT-Block evaluation:** those lines are **outside** \(U_{\mathrm{JITFINE}}\) (they do not appear as Layer-B rows).  

They are **not** proven known-clean merely by key absence.  
Status for full-Git analysis: **UNKNOWN** (must not coerce to 0).

Class: **C — outside the annotated candidate universe** for published JIT-DL metrics; **UNKNOWN** if ranking over full Git.

---

## 8. Positive label lineage

- Layer A: 2111 `added_buggy` texts on 475 commits  
- Layer B / JIT-Block eval: **2060**  
- Delta **+51** on **22** commits (A>B) — PARTIALLY_RESOLVED; eval uses 2060  

---

## 9. Negative label lineage

- In Layer B: `label==0` on added rows → known negative in \(U_{\mathrm{JITFINE}}\)  
- In Layer A files with abl: `added_clean` → known negative  
- Files without abl / Git lines not in B → not known negative  

---

## 10. Unknown lines

Dominant mass under Layer A (no abl) and full Git.  
Zero unknowns inside \(U_{\mathrm{JITFINE}}\) on the 475.

---

## 11. 2111-vs-2060 explanation

**PARTIALLY_RESOLVED.**  
22 commits disagree on positive counts (sum delta 51).  
JIT-Block does not introduce a third count; it uses Layer B (2060).  
Full flatten script still absent → not fully RESOLVED.

---

## 12. Policy A — original labelled universe

| | |
|--|--|
| Usable N | **475** |
| Completeness | complete within \(U_{\mathrm{JITFINE}}\) |
| Valid metrics | Top-5/10, IFA, R@20%E, E@20%R |
| Scope language | “localisation within JIT-Defects4J labelled added-line universe” — **not** “all raw-Git added lines annotated” |

**Scientifically defensible as primary RQ1** if scope is stated precisely.

---

## 13. Policy B — full canonical Git

| | |
|--|--|
| Usable N | **0** (for effort/IFA) |
| Unknown | 144242 |
| Valid metrics | none for IFA/effort |

Do **not** convert UNKNOWN→0.

---

## 14. Policy C — complete-label Git commits

| | |
|--|--|
| Usable N | **58** (recomputed) |
| Completeness | complete on subset |
| Valid metrics | Top-k + IFA/effort on that subset |
| Bias | strong selection vs 475 |

---

## 15. Policy D — positive-complete (352)

| | |
|--|--|
| Usable N | 352 |
| Top-k | VALID_WITH_SCOPE_CAVEAT only if ranking universe is fully defined |
| IFA/effort | **INVALID** if unknowns remain among candidates |

Not promoted solely for larger N.

---

## 16. Metric validity per policy

See `docs/RQ1_METRIC_VALIDITY_MATRIX.md` and `artifacts/rq1_universe/policy_comparison.csv`.

---

## 17. Selection-bias profile

- Policy C (N=58): tiny; project concentration likely  
- Policy D (N=352): drops commits with ambiguous/missing positive maps  
- Policy A (N=475): preserves all gold-positive test commits; universe ≠ full Git  

---

## 18. Scientifically defensible policies

1. **Primary recommendation:** Policy A (N=475) with explicit labelled-universe scope  
2. Optional ablation: Policy C (N=58) for full-Git effort metrics  
3. Reject Policy B until unknowns eliminated  
4. Do not use Policy D for IFA/effort  

---

## 19. Remaining blockers

- 2111 vs 2060 not fully closed (22 commits)  
- Layer-A→Git positive ambiguity (247) remains for full-Git linkage  
- JIT-Block producer script absent  

None of these block Policy A on \(U_{\mathrm{JITFINE}}\).

---

## 20. RQ1_LABEL_UNIVERSE_GATE

**PASS** — candidate universe, known pos/neg, unknowns, valid metrics, and usable N per policy are unambiguous.

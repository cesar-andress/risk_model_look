# POLICY_A_COMPLETE_CASE_BIAS_REPORT.md

**Gate:** `POLICY_A_COMPLETE_CASE_READINESS_GATE`  
**Verdict:** **PASS** (readiness only — **not** primary adoption)  
**Date:** 2026-10-01  

---

## 1. Definition

`POLICY_A_COMPLETE_CASE` = gold-positive test commits where **every** Policy-A
candidate row has exactly one canonical Git line ID after residual closure.

| Population | Commits | Candidates | Positives | Negatives |
|------------|--------:|-----------:|----------:|----------:|
| All Policy A | 475 | 18615 | 2060 | 16555 |
| Complete-case | **413** | 13412 | 1712 | 11700 |
| Incomplete (excluded) | 62 | 5203 | 348 | 4855 |

Do **not** silently make complete-case primary. Orchestrator decides.

---

## 2. Project coverage

| Metric | Value |
|--------|-------|
| Projects represented | **21 / 21** |
| Projects with 0 complete commits | **none** |
| Per-project retention | **50% – 100%** |

Incomplete commits spread across 18 projects; top-2 share of incomplete
commits **&lt; 50%** (no severe concentration flag).

Largest incomplete counts: commons-math (14), ant-ivy (10), commons-io (6),
parquet-mr (6).

---

## 3. Distributional profile (complete vs incomplete)

Criterion for `LARGE_DISTRIBUTIONAL_DIFFERENCE`: \(|\mathrm{SMD}| \ge 0.25\)
(descriptive; not a universal law).

Variables flagged (complete − incomplete SMD):

| Variable | Flag |
|----------|------|
| n_candidates (Policy-A rows/commit) | LARGE |
| buggy_density (pos/candidates) | LARGE |
| git_added | LARGE |
| git_changed | LARGE |
| la (lines added feature) | LARGE |

Full table: `artifacts/residual_closure/complete_vs_incomplete_profile.csv`.

Interpretation: incomplete commits tend to be **larger diffs / larger candidate
universes**. Mapping failure is associated with size, not a single project wipeout.

---

## 4. Label-difficulty profile

| | Complete (n=413) | Incomplete (n=62) |
|--|-----------------:|------------------:|
| Mean positive lines / commit | (see profile `n_pos`) | higher size-associated |
| Mean buggy density | lower/higher per SMD flag on `buggy_density` | flagged LARGE |
| Positives retained | 1712 | 348 lost from primary-complete scope |

Commit-level labels remain positive for all 475; difficulty shift is in
**line-level** positive counts/density and candidate size.

---

## 5. Metric validity

| Commit class | Primary RQ1 (Top-5/10, IFA, Recall@20%Effort, Effort@20%Recall) |
|--------------|------------------------------------------------------------------|
| POLICY_A_COMPLETE | **Valid within Policy-A scope** |
| Incomplete | **Invalid** for primary scores until full mapping |

Optional descriptive coverage reporting on incomplete commits is allowed;
partial maps must not become primary localization scores.

---

## 6. Readiness checklist

| Criterion | Status |
|-----------|--------|
| A. Complete-case exactly defined | YES (413) |
| B. All rows inside map uniquely | YES |
| C. All 21 projects represented | YES |
| D. Selection-bias audit complete | YES |
| E. No severe unexplained exclusion concentration | YES |
| F. No model outcomes used | YES |

**POLICY_A_COMPLETE_CASE_READINESS_GATE = PASS**

Adoption as primary RQ1 population remains an **orchestrator** decision given
size-associated exclusion bias (LARGE SMD on candidate/diff size).

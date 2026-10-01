# POLICY_A_CANONICAL_BRIDGE_REPORT.md

**Gate:** `POLICY_A_CANONICAL_BRIDGE_GATE`  
**Verdict:** **FAIL**  
**Date:** 2026-10-01  

---

## 1. VERDICT

**FAIL.** Deterministic Policy-A → canonical Git linkage reaches
**18467 / 18615** unique mappings (2059 / 2060 positives; 16408 / 16555 negatives;
403 / 475 commits complete; 0 ID collisions). Residual **148 NOT_FOUND**
(1 positive, 147 negatives; 72 commits) is **not** scientifically trivial.
JIT-Block reconstruction **producer code is ABSENT** at frozen revision, so
original-vs-instrumented BYTE_IDENTICAL reproduction of the producer cannot be
established.

---

## 2. SCIENTIFIC PURPOSE

Prove each Policy-A Layer-B row \((commit\_id, idx)\) maps to exactly one
stable canonical Git line ID before any tokenization, without treating full-Git
unknowns as negatives.

---

## 3. FROZEN POLICY-A UNIVERSE

| Quantity | Value |
|----------|------:|
| Commits | 475 |
| Candidate ADDED rows | 18615 |
| Positive | 2060 |
| Negative | 16555 |
| Unknown within universe | 0 |

Source: `changes_complete_buggy_line_level.pkl` (JIT-Fine; BYTE_IDENTICAL to
JIT-Block Layer-B). SHA-256
`479b61b138280105573cd4ea38ea6d656850e29f378e9aa63f1c86d195e6e88a`.

---

## 4. JIT-BLOCK PIPELINE TRACE

Frozen repo: `hangters/JIT-Block@d82cc67f1c696644e9d6d5c80621937aaf36710b`.

| Path | Role |
|------|------|
| `JITBlock/run.py` | Training / eval consumer |
| `JITBlock/my_util.py` | Load block pickles; preprocess |
| `JITBlock/model.py` | Model |

**Producer that builds block pickles from Git: ABSENT** (tree has 12 files; no
`reconstruct` / `build_block` script). Algorithm evidence class:
**AUTHOR_PAPER + RELEASED_OUTPUTS** (Expert Systems 2024 DOI 10.1111/exsy.13702):

1. Git commit → source files  
2. Match Defect4J line texts → recover line numbers  
3. Sort ADD/DEL by line number  
4. Group continuous **changed blocks**  
5. Drop commits that fail matching  

Released consumer schema discards file path and line numbers; only spaced texts
in alternating `('added_code'|'removed_code', text, …)` blocks remain.

**Data-flow (intended):**

Layer-B row → match object → source-file match → recovered location →
ordered change → changed block → serialized pickle (locations dropped).

---

## 5. INSTRUMENTATION METHOD

Because the producer is absent, an **instrumented copy of the producer cannot
be attached**. Instead:

1. Preserve Layer-B `(commit_id, idx)` as immutable SOURCE ROW ID.  
2. Bridge via Layer-A file identity (when uniquely / order-deterministically
   linked) then first-parent filtered Java Git diffs
   (`src/data/git_diff_reconstruction.py`).  
3. Fall back to direct Policy-A → Git exact-variant matching.  
4. Emit audit mapping under `data/raw/derived_audit/policy_a_bridge/` (gitignored).  
5. Compare Layer-B ADDED text bags to released
   `JIT-Defect4J_block_test.pkl` ADDED bags (scientific content check).

No matching text, ordering, or membership of released pickles was modified.

---

## 6. ORIGINAL-vs-INSTRUMENTED REPRODUCTION CHECK

| Check | Result |
|-------|--------|
| Run original producer | **IMPOSSIBLE** (ABSENT) |
| BYTE_IDENTICAL instrumented vs original producer output | **N/A** |
| Layer-B ADDED bag vs released block ADDED bag | **BAG_EQ = 342 / 475**; **BAG_NEQ = 133 / 475** |

Bag inequality on 133 commits shows Layer-B and released blocks are not
universally identical as multisets; locations still cannot be read from the
released pickle. This blocks a strong equivalence claim for a reconstructed
producer.

---

## 7. SOURCE ROW IDENTITY

`(commit_id, idx)` is carried unchanged on every bridge result.
`idx` is used only as SOURCE ROW ID (not a source line number).

---

## 8. RECOVERED SOURCE LOCATIONS

| Status | Count | Pos | Neg |
|--------|------:|----:|----:|
| RECOVERED_EXACT_BY_JITBLOCK | 16635 | — | — |
| RECOVERED_EXACT_SEQUENCE_DISAMBIGUATED | 1832 | — | — |
| RECOVERED_EXACT_DUPLICATE_DISAMBIGUATED | 0 | — | — |
| NOT_FOUND | 148 | 1 | 147 |
| AMBIGUOUS | 0 | 0 | 0 |

Provenance (mapped): mostly `layer_a_file_constrained`; also
`layer_a_order_occurrence`, `layer_a_git_order_sequence`; rare direct Git.

Transforms: `punct_space`, whitespace collapse, `normalize_line` (verified
upstream). No fuzzy / edit-distance matching.

---

## 9. PATH RECONCILIATION

| Status | Count |
|--------|------:|
| PATH_EXACT | 18467 |
| PATH_RENAME_RESOLVED | 0 |
| PATH_DETERMINISTIC_NORMALIZED | 0 |
| PATH_CONFLICT | 0 (among mapped) |

---

## 10. CANONICAL LINE-ID LINKAGE

Target ID:

```
(commit_hash, file_path, hunk_index, change_type, old_lineno, new_lineno, occurrence_index)
```

via `stable_line_id` on filtered first-parent Java added `DiffLine`s.
JIT-Block block IDs are **not** used as Git hunk IDs.

---

## 11. POSITIVE ROW COVERAGE

**2059 / 2060** mapped uniquely.

Unmapped positive: commit `cfa7c5e3bba0efbc88dfb2fcafb983723a1606bc`, `idx=2`,
text not present in first-parent added diff (filtered or unfiltered).

---

## 12. NEGATIVE ROW COVERAGE

**16408 / 16555** mapped uniquely; **147** NOT_FOUND.

---

## 13. DUPLICATE / OCCURRENCE HANDLING

When Git (or Layer-A) has **more** identical texts than Policy-A rows:

- Zip Policy-A / Layer-A order to the **prefix** of matching Git lines in diff
  order (line-number order within file).  
- Extra Git copies remain unlabelled → `NOT_IN_RQ1_UNIVERSE`.  
- Status: `RECOVERED_EXACT_SEQUENCE_DISAMBIGUATED`.  
- Never arbitrary unordered first-hit across files.

Equal multiplicity → `RECOVERED_EXACT_DUPLICATE_DISAMBIGUATED` (none remaining
after sequence pass in this run).

---

## 14. COLLISION AUDIT

| Metric | Value |
|--------|------:|
| Mapped rows | 18467 |
| Zero-map | 148 |
| Unique canonical IDs | 18467 |
| Collision IDs (claimed by >1 Policy-A row) | **0** |
| Multi-map rows | 0 |

---

## 15. COMMIT COMPLETENESS

| Metric | Value |
|--------|------:|
| COMPLETE_POLICY_A_COMMIT_COUNT | **403** |
| Incomplete | **72** |

Incomplete commits are **not** selected as a new primary RQ1 population in this
gate (orchestrator decision).

---

## 16. PROJECT DISTRIBUTION OF FAILURES

Top incomplete-commit projects (from `project_summary.csv` /
`commit_completeness_summary.csv`): commons-math (15), ant-ivy (10),
parquet-mr (9), commons-io (6), commons-net (6), commons-validator (5), …

---

## 17. RQ1 CANDIDATE MASK

See `docs/RQ1_CANDIDATE_MASK_CONTRACT.md`.

Over filtered Git ADDED lines on the 475 commits (audit counts):

| Mask | Count |
|------|------:|
| RQ1_POSITIVE | 2059 |
| RQ1_NEGATIVE | 16408 |
| NOT_IN_RQ1_UNIVERSE | 87038 |

---

## 18. CANONICAL MODEL INPUT SOURCE

**Frozen intent (unchanged):** ordered historical first-parent Git
reconstruction for all 27319 commits.

**Not claimed:** equivalence to JIT-Fine set encoding or JIT-Block changed
blocks as hunks.

`CONTEXT_POLICY` remains **OPEN**.

---

## 19. REMAINING BLOCKERS

1. **148** Policy-A rows with no exact deterministic Git location (includes **1**
   positive).  
2. JIT-Block **producer ABSENT** → cannot instrument pre-serialization locations.  
3. **133** commits where Layer-B ADDED bag ≠ released block ADDED bag.  
4. Tokenizer / offset mapping still blocked pending a complete bridge.

---

## 20. POLICY_A_CANONICAL_BRIDGE_GATE

**FAIL**

Strong target 18615/18615 not met; residual not negligible; producer
instrumentation equivalence not achievable from public tree.

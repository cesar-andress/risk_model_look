# DATASET_SCHEMA_VALIDATION_REPORT.md

Date: **2026-09-29**  
Archive SHA-256 reconfirmed: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`

---

## 1. EXECUTIVE VERDICT

**DATASET_SCHEMA_VALIDATION_GATE = PASS**

Author-provided JIT-Fine artifacts are structurally intelligible, internally consistent on commit IDs/labels/alignment, and usable for downstream preprocessing design. Important quirks (set-valued change lines; line labels only on test positives; partial chronological train/test overlap under unix timestamps; validation not between train and test) are documented as DATA QUIRK / DOCUMENTATION MISMATCH, not scientific blockers for freezing the author split membership.

---

## 2. FILES AND HASHES

Extracted only the seven JIT-Fine members to `data/raw/upstream/extracted/` (gitignored).  
Manifest: `artifacts/data_schema/extracted_files_manifest.csv`

| archive_path | sha256 |
|--------------|--------|
| data/jitfine/changes_train.pkl | 088898f4c87a59dfeaaabdbc48488b7e224ea7109ee453d0e8d244146b715f85 |
| data/jitfine/features_train.pkl | 0b9992d77cd07f45a71bd327a3d408ed3f0ab7a907ffdc10f9916a8f226dc42a |
| data/jitfine/changes_valid.pkl | dc9bb8f3390b74b5329a2186332466c22d78e71047521c56f1d8b598147c723b |
| data/jitfine/features_valid.pkl | e2ee48d5cd9e7f59bea726d4f6a71ef58712ae58d3388d8195a798369cf0d2cf |
| data/jitfine/changes_test.pkl | 23107219e63648b6516d74ff73b1e696c5e8eb368f6766c10e88d61dadb0809d |
| data/jitfine/features_test.pkl | 136eebbb1c1719bffbfed8f0d686e3c015c5756a7b3c43d6f700a07687ab58fa |
| data/jitfine/changes_complete_buggy_line_level.pkl | 479b61b138280105573cd4ea38ea6d656850e29f378e9aa63f1c86d195e6e88a |

---

## 3. PICKLE SAFETY AUDIT

See `docs/PICKLE_SECURITY_AUDIT.md`.  
All seven: **STATIC_PICKLE_RISK PASS**.  
Isolation: **LIMITED_BWRAP_UNSHARE_NET** (`unshare -n` denied; bwrap used).

---

## 4. TOP-LEVEL OBJECT TYPES

| Artifact | Type |
|----------|------|
| changes_{train,valid,test}.pkl | `list` length 4: `(commit_ids, labels, msgs, codes)` |
| features_{train,valid,test}.pkl | `pandas.DataFrame` |
| changes_complete_buggy_line_level.pkl | `pandas.DataFrame` (26104×6) |

Changes schemas across splits: **IDENTICAL_SCHEMA** (layout).  
Features schemas: **IDENTICAL_SCHEMA**.

---

## 5. AUTHOR SPLIT STRUCTURE

| Split | N | + | − | +rate |
|-------|---|----|----|------|
| train | 16374 | 1390 | 14984 | 8.49% |
| valid | 5465 | 467 | 4998 | 8.55% |
| test | 5480 | 475 | 5005 | 8.67% |
| total | 27319 | 2332 | 24987 | 8.54% |

---

## 6. PRIMARY KEY

**Frozen key:** `commit_hash` / changes commit id (40-char hex string).  
Project+commit not required for uniqueness within author splits.  
Duplicates within split: **0**. Null IDs: **0**.

---

## 7. SPLIT INTERSECTIONS

| Pair | Count |
|------|------:|
| train ∩ valid | 0 |
| train ∩ test | 0 |
| valid ∩ test | 0 |

No identical-commit leakage across author splits.

---

## 8. CHANGES / FEATURES ALIGNMENT

All splits: **EXACT_ALIGNMENT** (same length, same order, IDs equal).  
`is_buggy_commit` vs changes labels: **0 disagreements** (test checked; same float coding).

---

## 9. COMMIT LABEL SEMANTICS

- Changes labels: Python `float` in `{0.0, 1.0}`
- Features: `is_buggy_commit` float `{0.0, 1.0}`
- Positive = defect-inducing commit

---

## 10. CHANGE REPRESENTATION

Per commit, `codes[i]` is `dict` with:

- `added_code`: **`set[str]`**
- `removed_code`: **`set[str]`**

| Field | Present? |
|-------|----------|
| commit message | YES (`msgs` + `features.commit_message`) |
| file paths in codes | **NO** |
| file paths elsewhere | PARTIAL (`features.fileschanged`) |
| added lines | YES (set) |
| deleted lines | YES (set) |
| context lines | NO |
| hunk markers / hunk ids | NO |
| line numbers in changes | NO |
| project | YES (`features.project`) |

**Line order in changes pickle: NOT PRESERVED** (sets).  
Line-label DataFrame preserves order via `idx`.

---

## 11. LINE-LABEL SCHEMA

DataFrame columns:

`commit_id`, `idx`, `changed_type`, `label`, `raw_changed_line`, `changed_line`

Scope: **TEST gold-positive commits only** (475 commits).  
Train/valid positives are **absent** from this artifact.

There is no nested `added_buggy_level` object in this pickle; that name belongs to the separate JSON docs in the upstream repo. Equivalent coding here is the `label` column on rows with `changed_type=='added'`.

---

## 12. ADDED_BUGGY_LEVEL CODING

Observed `label` values (raw): **`0.0` and `1.0`** (`float64`).  
No other values.  
`1.0` = buggy/defect-inducing line; `0.0` = non-buggy line.

---

## 13. LINE-LABEL LENGTH CONSISTENCY

For all 475 overlapping positive test commits:

`len(added_code set)` == number of line-label rows with `changed_type=='added'`  
**mismatches: 0**

---

## 14. DELETED-LINE LABEL STATUS

**YES** — deleted rows exist with a `label` field.  
All deleted labels are **`0.0`** (7489/7489).  
Never treat deleted lines as “unlabeled”; they are explicitly labeled clean in this artifact.  
Positive deleted labels: **0**.

---

## 15. TEST-SET LINE-LABEL COVERAGE

| Group | n | in LL | ≥1 added | ≥1 +added label | missing |
|-------|---|------:|---------:|----------------:|--------:|
| all test | 5480 | 475 | — | — | 5005 (all negatives) |
| positive test | 475 | 475 | 475 | 475 | 0 |
| negative test | 5005 | 0 | — | — | 5005 |

Positives with zero positive line labels (among those in LL): **0**.

---

## 16. LOCALIZATION-ELIGIBLE POPULATIONS L0–L4

| ID | Count |
|----|------:|
| L0 | 5480 |
| L1 | 475 |
| L2 | 475 |
| L3 | 475 |
| L4 | 475 |

`LOCALIZATION_DENOMINATOR_DECISION: OPEN`  
(Original JIT-Fine eval further requires model-predicted positive.)

---

## 17. DUPLICATES

- Commit-ID duplicates within splits: none
- Identical change-content hashes shared by multiple commits: present at modest rates (see empirical profile)

---

## 18. MISSINGNESS

- Commit IDs: no nulls
- Labels: no nulls in changes/features/line-label
- Line-label raw/changed line columns: 0 nulls
- Features timestamps: present (`author_date`, `author_date_unix_timestamp`)

---

## 19. ZERO-ADD / EMPTY-CHANGE CASES

Test: 64 commits with empty `added_code` set — **all negatives**; **0** positives.  
Paper construction said commits with no added lines were filtered; residual zero-add negatives remain → **DATA QUIRK**.

---

## 20. PROJECT DISTRIBUTION

21 projects; all appear in train/valid/test.  
Per-project counts: `artifacts/data_schema/project_split_summary.csv`

---

## 21. TEMPORAL SPLIT AUDIT

Using `author_date_unix_timestamp`:

- train_max ≤ test_min: **10 ordered / 11 overlapping** projects
- valid wholly between train and test: **0 / 21**

Paper §6.1 chronological 80/20 is **not fully reflected** in the materialized three-way split under these timestamps → **DOCUMENTATION MISMATCH** (not automatic FAIL). Author membership remains frozen.

---

## 22. PUBLISHED COUNT COMPARISON

| Claim | Published | Archive | Status |
|-------|-----------|---------|--------|
| 21 Java projects | 21 | 21 | **MATCH** |
| ~27319 commits / 2332 defective (secondary note) | 27319 / 2332 | 27319 / 2332 | **MATCH** |

---

## 23. ANOMALIES

1. `added_code`/`removed_code` are **sets** (order lost) — DATA QUIRK / future mapping constraint  
2. Line-label pickle covers **test positives only** — REPRODUCIBLE LIMITATION for train/valid localization labels  
3. Chronological train≤test fails for 11/21 projects under unix timestamps — DOCUMENTATION MISMATCH  
4. Validation not between train and test — DOCUMENTATION MISMATCH vs naive 80/20+holdout story  
5. Zero-add negatives remain — DATA QUIRK vs filtering narrative  
6. ZIP also contains non-JIT-Fine trees (not extracted) — already noted at acquisition  

---

## 24. FROZEN FACTS

- Split sizes and rates above  
- Primary key = commit hash string  
- Label coding float `{0.0,1.0}`  
- Line labels: float `{0.0,1.0}` on DataFrame; added lines carry positives; deleted labeled 0.0 only  
- L0–L4 counts above  
- No cross-split commit ID overlap  

---

## 25. OPEN METHODOLOGICAL DECISIONS

- **LOCALIZATION_DENOMINATOR_DECISION: OPEN**
- How to recover line order / file paths for explanations given set-valued changes + `fileschanged`
- Whether train/valid localization evaluation is possible without additional label sources

---

## 26. DATASET_SCHEMA_VALIDATION_GATE

**PASS**

No scientific blocker from true train/test commit overlap, contradictory labels, or unusable line-label structure.

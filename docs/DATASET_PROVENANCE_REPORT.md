# DATASET_PROVENANCE_REPORT.md

Verification date: **2026-09-29**  
Scope: provenance/semantics only. **`data.zip` was NOT downloaded.**

---

## 1. DEFINING PUBLICATION

**SOURCE FACT**

- Title: *The best of both worlds: integrating semantic features with expert features for defect prediction and localization*
- Authors: Chao Ni, Wei Wang, Kaiwen Yang, Xin Xia, Kui Liu, David Lo
- Venue: Proceedings of the 30th ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering (ESEC/FSE 2022)
- Pages: 672–683
- DOI: **10.1145/3540250.3549165**
- Publisher: ACM
- Published-print: 2022-11-07; published-online: 2022-11-09 (Crossref)

**Evidence:** Crossref works API for the DOI; ACM landing URL `https://doi.org/10.1145/3540250.3549165`; author-hosted PDF `https://kui-liu.github.io/papers/2022-ni-best.pdf` (Kui Liu co-author page).

---

## 2. DATASET NAME

| Context | Spelling |
|---------|----------|
| Paper body / abstract | **JIT-Defects4J** |
| Upstream README | **JIT-Defect4J** |

**SOURCE FACT:** Both spellings refer to the same artifact constructed in this paper/replication package.

**OUR POLICY:** Manuscript prose uses **JIT-Defects4J**. Preserve **JIT-Defect4J** when quoting upstream README text.

---

## 3. DATASET ORIGIN

**SOURCE FACT (paper §4 + README):**

- Built on **LLTC4J** (Line-Labelled Tangled Commits for Java) by Herbold et al., which manually labels lines in **bug-fixing commits**.
- Extended by Ni et al. to:
  1. include **clean and buggy (defect-inducing) commits**;
  2. obtain **line labels in defect-introducing commits**.
- Labeling chain (paper §4 / Fig. 3 narrative):
  - LLTC4J labels modified lines in bug-fixing commits (consensus of ≥3 of 4 participants for types including contributing to bug-fixing).
  - Deleted lines contributing to bug-fixing are treated as defective evidence and mapped to bug-inducing commits (PyDriller; paper contrasts this with noisier plain SZZ pipelines).
  - Unlabeled lines in bug-inducing commits are treated as clean.
- Filters: Java files only; non-functional changes filtered; commits that add no new lines ignored (SZZ-style assumption that defects are introduced by additions); five LLTC4J projects removed for insufficient labeling; two removed for missing commits → **21 Java projects**.
- Published descriptive ranges (paper Table 2 narrative): commits per project 544–4,026; bug ratios ~1.76%–18.75% at commit level; line-level bug ratios ~3.77%–18.43%. Exact global totals **REQUIRES_ACQUISITION_PHASE** (secondary papers often cite ~27,319 commits / 2,332 defective — not re-counted here from archive).

**Do not simplify:** “manually labeled dataset” does **not** mean every BIC line was manually annotated from scratch; manual effort is primarily on LLTC4J bug-fixing lines, then mapped/extended.

---

## 4. AUTHORITATIVE REPLICATION SOURCE

| Repo | Status | Why |
|------|--------|-----|
| `jacknichao/JIT-Fine` | **AUTHORITATIVE** | Owner GitHub name **Chao Ni** (first author); repo description cites FSE’22 paper; created 2022-08-30 with replication materials |
| `tianc43/JIT-FINE` | **THIRD_PARTY_MIRROR** | Created 2023-12-22; shares historical commits and **identical** `data.zip` Git blob SHA; not selected as primary |

No LICENSE file; GitHub `license` metadata null.

---

## 5. IMMUTABLE REVISION

- Repository: `https://github.com/jacknichao/JIT-Fine`
- Branch: `master` (default)
- **Frozen commit SHA:** `584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- Timestamp: `2023-08-25T05:35:17Z` (README baseline-reference update; includes earlier `data.zip` from `4b78240…`)

No release tag found; SHA freeze is mandatory.

---

## 6. EXPECTED ARCHIVE

- Path: `data.zip`
- Remote size: **75,326,372** bytes
- Remote hash type: **git_blob_sha1**
- Remote hash: `6cd2f45d97a7c430533cde382be6bf42d9ff3649`
- Download URL at frozen revision:  
  `https://raw.githubusercontent.com/jacknichao/JIT-Fine/584799fdec6095ab75a45fd2a5f8db5b12163aa5/data.zip`
- **Downloaded in this task: false**

---

## 7. EXPECTED FILE INVENTORY

From README training/eval commands (after unzip):

- `data/jitfine/changes_train.pkl` + `features_train.pkl`
- `data/jitfine/changes_valid.pkl` + `features_valid.pkl`
- `data/jitfine/changes_test.pkl` + `features_test.pkl`
- `data/jitfine/changes_complete_buggy_line_level.pkl`

Also present in repo (outside zip; not downloaded):

- `JITFine/labels for each line/readme.md` (schema description)
- `JITFine/labels for each line/buggy_changes_with_buggy_line.json` (~55 MB; **not downloaded**)

---

## 8. COMMIT LABEL SEMANTICS

**SOURCE FACT**

- Task definition (paper): JIT-DP = identifying **defect-inducing commits**.
- Code (`JITFine/my_util.py`, `TextDataset`): each example has `label = int(label)`; metrics treat `label == 1` as defective.
- Feature frame uses `commit_hash` join to expert features (`la, ld, nf, …, fix`).

**Positive class:** defect-inducing / buggy commit (not merely “later bug-fixing commit”).

Presence of both classes in train/valid/test: **expected** from construction, but counts **REQUIRES_ACQUISITION_PHASE**.

---

## 9. LINE LABEL SEMANTICS

**SOURCE FACT — upstream line-label README structure:**

```
project → commit → added / deleted / added_buggy_level
  (files keyed by filepath)
```

**SOURCE FACT — paper:**

- Line-level ground truth supports JIT-DL on defect-inducing commits.
- Mapping originates from bug-fixing line labels; unlabeled BIC lines treated as clean.
- Commits with no added lines are filtered out of construction.

**SOURCE FACT — evaluation code (`JITFine/concat/run.py`):**

- Line pickle rows: `(commit_id, idx, changed_type, label, raw_changed_line, changed_line)`
- `--only_adds` filters `changed_type == 'added'`
- Metrics treat `label == 1` as buggy line

**OUR INTERPRETATION (for protocol freeze, pending archive validation):**

- Primary labelable/evaluable unit for localization compatibility with JIT-Fine eval: **added lines**
- Deleted lines exist in the change representation and may appear in line-label artifacts; default JIT-Fine test command uses `--only_adds`
- Exact encoding of `added_buggy_level` values **REQUIRES_ACQUISITION_PHASE** (do not assume without pickle/JSON inspection)

---

## 10. ORIGINAL SPLIT

**Paper §6.1 (SOURCE FACT):** time-aware per project — sort commits by timestamp ascending; top **80% train**, remaining **20% test**; concatenate across projects.

**Replication (SOURCE FACT):** materialized `changes_{train,valid,test}.pkl` + matching `features_*.pkl` paths in README.

**Classification:** **AUTHOR_PROVIDED** split membership files (not regenerated by a checked-in script in this repo).

**Gap:** how `valid` is carved relative to the paper’s 80/20 description is **UNKNOWN until archive/docs inspection** (no generation script found). Policy: still **reuse author-provided membership as frozen**.

Leakage dimensions documented by paper design: **time within project** for train vs test; commits from the **same project appear in both** train and test (cross-project pooling after per-project cut). File-/bug-ID separation: not claimed.

---

## 11. ORIGINAL LOCALIZATION SUBSET

Concise pseudocode of JIT-Fine concat test localization (from `run.py`):

```
for each test commit example:
  run model → pred, attentions
  if commit_label == 1 AND pred == 1 AND '[ADD]' in input_tokens:
      collect line scores from attentions aligned to change lines
      if only_adds:
          keep only changed_type == 'added'
      compute Top-5/Top-10, Recall@20%Effort, Effort@20%Recall, IFA
      vs line labels (label==1 buggy)
aggregate means over those commits
```

Implications:

- Localization metrics are computed on **true-positive predicted** buggy commits (not all buggy test commits).
- Default README eval enables `--only_adds`.

---

## 12. ORIGINAL METRICS RELEVANT TO COMPATIBILITY

### Used by JIT-Fine (paper §5.2 + results)

**Commit-level:** F1, AUC, Recall@20%Effort, Effort@20%Recall, Popt  

**Line-level:** Top-5, Top-10, Recall@20%Effort_line, Effort@20%Recall_line, IFA_line  

### Implementation note (SOURCE FACT vs prose)

Paper prose defines Top-N as the proportion of **actual defective lines** ranked in top-N (recall-like wording).  
Code `get_line_level_metrics` computes `sum(labels[:k]) / k` (precision-at-k style).  

**Flag for metrics gate:** reconcile paper wording vs code before claiming exact replication of published Top-N numbers.

### Used by JITLine (baseline / related)

JITLine metrics are invoked via `baselines/JITLine/*` and cited paper Pornprasit & Tantithamthavorn MSR 2021; do not attribute JITLine-only definitions to JIT-Fine without checking that baseline code.

### Planned by our study

Per `EXPERIMENT_PROTOCOL_V0.md` (unchanged scientifically here): localization + faithfulness + polarity metrics; compatibility subset should align with JIT-Fine line metrics **as implemented** when comparing to JIT-Fine numbers.

---

## 13. LICENSE / REDISTRIBUTION STATUS

| Layer | Classification |
|-------|----------------|
| Source code license | **NONE_FOUND** |
| Dataset license | **NONE_FOUND** |
| Raw redistribution | **NOT_ESTABLISHED** |
| Derived redistribution | **NOT_ESTABLISHED** |

**Conservative reproducibility consequence (not legal advice):**

- Do not commit `data.zip` or extracted raw data
- Do not mirror raw archive to our GitHub/Zenodo
- Point replicators to authoritative upstream at frozen SHA unless permission is later established
- Local scientific use of a download remains a separate later decision

---

## 14. KNOWN DATASET LIMITATIONS

Documented by authors / construction:

- Java-only OSS projects
- Residual missed bug-fixing commits possible even after LLTC4J manual process (paper threats)
- Commits without added lines excluded
- Tangled-commit mitigation improves on SZZ-only corpora but is not perfect certainty
- Secondary literature notes label-noise audits (e.g., CodeFlowLM) — treat as external warnings, not re-validated here

---

## 15. FACTS REQUIRING ARCHIVE INSPECTION

- Exact pickle schemas and dtypes
- Exact row counts / unique commit IDs
- Train∩valid∩test emptiness
- Label distributions; projects per split
- How `valid` relates to paper 80/20
- `added_buggy_level` value coding
- Whether deleted lines carry labels in `changes_complete_buggy_line_level.pkl`
- Duplicate commits; commits with zero added lines remaining
- Positive commits without positive line labels
- SHA-256 of `data.zip` after download
- Match to commonly cited totals (~27k commits)

---

## 16. FROZEN DECISIONS FOR OUR STUDY

1. Defining publication = Ni et al. ESEC/FSE 2022, DOI `10.1145/3540250.3549165`
2. Authoritative upstream = `jacknichao/JIT-Fine@584799fdec6095ab75a45fd2a5f8db5b12163aa5`
3. Canonical name = **JIT-Defects4J**
4. Reuse **author-provided** train/valid/test membership files
5. Localization compatibility default aligns with JIT-Fine `--only_adds` subset semantics
6. No raw redistribution until license established
7. No parser implementation until acquisition+schema validation

---

## 17. DATASET_PROVENANCE_GATE VERDICT

**PASS**

Criteria A–N satisfied at documentation level without downloading the archive. Remaining unknowns are explicitly deferred to acquisition/schema gates.

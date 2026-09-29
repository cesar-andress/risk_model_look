# DATASET_EMPIRICAL_PROFILE.md

Canonical measured profile of author-provided JIT-Fine / JIT-Defects4J artifacts.  
No raw rows / source lines / commit messages.

Archive SHA-256: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`

## Split sizes (changes_*.pkl)

| Split | N | Positives | Negatives | Positive rate |
|-------|---|-----------|-----------|---------------|
| train | 16374 | 1390 | 14984 | 0.08489 |
| valid | 5465 | 467 | 4998 | 0.08545 |
| test | 5480 | 475 | 5005 | 0.08668 |
| **total** | **27319** | **2332** | **24987** | **0.08536** |

## Projects

- Overall distinct projects in features: **21**
- All 21 appear in train, valid, and test

## Primary key

- Changes: commit id string at tuple position 0
- Features: `commit_hash`
- Uniqueness: **no duplicate IDs within any split**
- Cross-split intersections: train∩valid=0, train∩test=0, valid∩test=0

## Changes ↔ features

- **EXACT_ALIGNMENT** on all splits (same N, same order, IDs match)
- `changes` labels (`float` 0.0/1.0) match `features.is_buggy_commit` (0 disagreements on test)

## Commit labels

- Observed values: `0.0`, `1.0` (Python `float`)
- Semantics: `1.0` = defect-inducing commit

## Line-label artifact

- Type: `pandas.DataFrame` shape **26104 × 6**
- Columns: `commit_id`, `idx`, `changed_type`, `label`, `raw_changed_line`, `changed_line`
- Scope: **exactly the 475 gold-positive test commits** (not train/valid)
- `changed_type`: `added` 18615, `deleted` 7489
- `label`: `0.0` 24044, `1.0` 2060
- Added lines: 2060 positive / 16555 negative
- Deleted lines: **0** positive / 7489 negative (label field present; never 1.0)

## L0–L4 (test)

| Pop | Definition | Count |
|-----|------------|------:|
| L0 | all test commits | 5480 |
| L1 | gold-positive test | 475 |
| L2 | L1 with ≥1 added line in changes | 475 |
| L3 | L1 present in line-label artifact | 475 |
| L4 | L1 with ≥1 positive added-line label | 475 |

## Zero-add (test)

- Commits with zero `added_code` set size: **64** (all negatives; **0** positives)

## Added/deleted size quantiles (test changes; set cardinality)

| | min | p25 | median | mean | p75 | p90 | p95 | p99 | max |
|--|-----|-----|--------|------|-----|-----|-----|-----|-----|
| added | 0 | (see audit JSON) | 10 | 39.48 | (see JSON) | 94 | (see JSON) | 463.5 | 2735 |
| deleted | 0 | | 3 | 20.30 | | 40 | | 321.8 | 1985 |

Full quantiles: `artifacts/data_schema/dataset_audit.json` → `split_enrichment.*.*_quantiles`

## Temporal (unix author_date)

- train_max ≤ test_min: **10 / 21** projects ordered; **11 / 21** overlapping
- valid wholly between train and test: **0 / 21**

## Duplicates

- Duplicate commit IDs within splits: **0**
- Identical `codes` content hashes with multiplicity >1: train 240, valid 55, test 39 (hash collisions of set contents across different commits)

## LOCALIZATION_DENOMINATOR_DECISION

**OPEN** (JIT-Fine original eval further restricts to model-predicted positives)

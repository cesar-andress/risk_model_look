# PROCESSED_DATASET_CONTRACT.md

Status: **canonical_v1 frozen for TOKEN_LINE_MAPPING**

## Versions

| Field | Value |
|-------|-------|
| schema_version | 1 |
| STRUCTURED_FORMAT_VERSION | 1 |
| PROMPT_TEMPLATE_VERSION | 1 |
| TOKEN_MAP_VERSION | 1 |
| STABLE_LINE_ID_V1 | `(commit, file, change_type, old_lineno, new_lineno, occurrence_index, ordered_position)` |

`ordered_position` is required: without it, one U0 lineno collision exists under CR-mangled hunks (`725fd755…`).

## Sources

| Role | Source |
|------|--------|
| Split / commit label / message | Frozen JIT-Fine `changes_*.pkl` |
| Project | Frozen `features_*.pkl` |
| Model input lines | Ordered historical first-parent Git (`-U0` CHANGED_ONLY) |
| RQ1 labels | Policy-A complete-case mapping (413 commits) |

## Primary RQ1

| Field | Value |
|------:|
| ORIGINAL_RQ1_COHORT | 475 |
| PRIMARY_RQ1_N | **413** |
| RQ1_EXCLUDED_MAPPING_INCOMPLETE | 62 |
| candidates | **13412** |
| positives | **1712** |
| negatives | **11700** |
| unknown | **0** |

Exclusion reason: ground-truth-to-canonical-input mapping incompleteness (not noise filtering).

## Representation

- Primary: `CHANGED_ONLY` (context=0)
- Ablation: `CTX3` (context=3)
- Markers: `[MSG] [FILE] [HUNK] [ADD] [DEL] [CTX]`
- Max length primary 2048 / ablation 4096
- Truncation: `WHOLE_SEGMENT_PREFIX_TRUNCATION_V1`

## Build

```bash
PYTHONPATH=. python -m src.data.build_dataset --config configs/data/canonical_v1.yaml
```

Outputs under `data/processed/canonical_v1/` (**Git-ignored**).

Ordering: original JIT-Fine split order.

## Integrity

train/valid/test = 16374 / 5465 / 5480; positives 1390 / 467 / 475;  
`rq1_primary_commit=true` exactly 413 test positives.

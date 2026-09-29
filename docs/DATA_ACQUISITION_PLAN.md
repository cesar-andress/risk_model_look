# DATA_ACQUISITION_PLAN.md

Status: **EXECUTED — DATASET_ACQUISITION_GATE PASS (2026-09-29)**

## Goal

Acquire the authoritative JIT-Fine replication archive immutably, without contaminating git.

## Authoritative remote

- Repo: `https://github.com/jacknichao/JIT-Fine`
- Revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- Archive path: `data.zip`
- Expected size: `75326372` bytes
- Remote git blob SHA-1: `6cd2f45d97a7c430533cde382be6bf42d9ff3649`
- Download URL:  
  `https://raw.githubusercontent.com/jacknichao/JIT-Fine/584799fdec6095ab75a45fd2a5f8db5b12163aa5/data.zip`

## Local destinations (canonical for this gate)

- Raw archive: **`data/raw/upstream/data.zip`** (gitignored)
- Logs / inventory: `artifacts/data_acquisition/`
- Reproducible script: `scripts/acquire_jit_defects4j.py`

Note: an earlier draft of this plan used a nested revision subdirectory.  
The DATASET_ACQUISITION_GATE prompt froze the flat path `data/raw/upstream/data.zip`; that path is authoritative.

## Acquisition results (verified)

| Check | Result |
|-------|--------|
| Downloaded | yes (2026-09-29T21:51:51Z–21:51:55Z UTC) |
| Size | 75326372 (match) |
| Git blob SHA-1 | 6cd2f45d97a7c430533cde382be6bf42d9ff3649 (match) |
| SHA-256 | 9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47 |
| SHA-512 | ebab2a181e0e8de675142f166778d17a4d582ac8f045d5c8be19233e98ebf088b172bb0c475f2ab9854262979e25fa3712e20de3fd449e1572a16125ee2b45e9 |
| ZIP integrity (`testzip`) | PASS |
| ZIP path safety | PASS |
| Expected `data/jitfine/*.pkl` members | all 7 present |
| Extracted | **no** |
| Pickle executed | **no** |

## Still deferred to DATASET_SCHEMA_VALIDATION_GATE

- Extraction protocol
- Controlled pickle/schema inspection
- Row counts, label distributions, split intersections, etc.

## License (unchanged by download)

- code: NONE_FOUND
- dataset: NONE_FOUND
- raw redistribution: NOT_ESTABLISHED
- derived redistribution: NOT_ESTABLISHED

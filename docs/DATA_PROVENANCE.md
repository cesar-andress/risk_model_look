# DATA_PROVENANCE.md

Dataset provenance bookkeeping. **`data.zip` has not been downloaded.**

Authoritative detail lives in:

- `docs/DATASET_SOURCE_MANIFEST.json`
- `docs/DATASET_PROVENANCE_REPORT.md`
- `docs/DATASET_SCHEMA_CONTRACT.md`
- `docs/DATA_ACQUISITION_PLAN.md`

## Planned primary dataset

| Field | Value |
|-------|-------|
| Name | JIT-Defects4J (canonical); alias JIT-Defect4J in upstream README |
| Role | Primary empirical dataset (line-level labels for defect-inducing commits) |
| Defining publication | Ni et al., ESEC/FSE 2022, DOI 10.1145/3540250.3549165 |
| Authoritative source URL | `https://github.com/jacknichao/JIT-Fine` @ `584799fdec6095ab75a45fd2a5f8db5b12163aa5` |
| Archive | `data.zip` (75326372 bytes; git blob SHA-1 `6cd2f45d97a7c430533cde382be6bf42d9ff3649`) |
| License / redistribution | NONE_FOUND / NOT_ESTABLISHED — do not commit or mirror raw archive |
| Download performed | **Yes** (2026-09-29T21:51:51Z UTC); unextracted |
| Local path | `data/raw/upstream/data.zip` (gitignored) |
| SHA-256 | `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47` |
| Git blob SHA-1 | `6cd2f45d97a7c430533cde382be6bf42d9ff3649` (match) |
| Schema verified | **Yes** (DATASET_SCHEMA_VALIDATION_GATE PASS) |
| Label semantics verified | **Yes** (float {0.0,1.0}; line-label test-pos only) |
| Split files | AUTHOR_PROVIDED; train 16374 / valid 5465 / test 5480; intersections empty |

## Planned secondary datasets (optional; not started)

| Name | Role | Status |
|------|------|--------|
| ApacheJIT | Commit-level labels only; optional for faithfulness / surface-cue analyses | NOT_STARTED; source TO VERIFY |
| ReDef corpus | Optional generalization check (C/C++) | NOT_STARTED; source TO VERIFY |

## Rules

- Do not invent counts, defect rates, or split sizes here.
- Do not commit raw dumps until license and release policy are explicit.
- When a dataset is obtained, record: download URL, retrieval date, SHA-256, transforming scripts, and any filtering.

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
| Local path (planned) | `data/raw/upstream/jacknichao_JIT-Fine_584799fdec6095/` (gitignored) |
| Download performed | **No** |
| Schema verified | **No** (expected contract only) |
| Label semantics verified | **Yes at documentation level** (archive coding still pending) |
| Split files | AUTHOR_PROVIDED paths documented; contents not yet inspected |

## Planned secondary datasets (optional; not started)

| Name | Role | Status |
|------|------|--------|
| ApacheJIT | Commit-level labels only; optional for faithfulness / surface-cue analyses | NOT_STARTED; source TO VERIFY |
| ReDef corpus | Optional generalization check (C/C++) | NOT_STARTED; source TO VERIFY |

## Rules

- Do not invent counts, defect rates, or split sizes here.
- Do not commit raw dumps until license and release policy are explicit.
- When a dataset is obtained, record: download URL, retrieval date, SHA-256, transforming scripts, and any filtering.

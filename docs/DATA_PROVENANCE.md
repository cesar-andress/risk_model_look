# DATA_PROVENANCE.md

Dataset provenance bookkeeping. No dataset has been downloaded in the bootstrap phase.

## Planned primary dataset

| Field | Value |
|-------|-------|
| Name | JIT-Defects4J |
| Role | Primary empirical dataset (line-level labels for defect-inducing commits) |
| Authoritative source URL | **UNKNOWN — TO VERIFY** |
| License / redistribution | **UNKNOWN — TO VERIFY** |
| Local path (planned) | `data/raw/` (gitignored) |
| Download performed | **No** |
| Schema verified | **No** |
| Label semantics verified | **No** |
| Split files verified | **No** (JIT-Fine split intended; files TO VERIFY) |

## Planned secondary datasets (optional; not started)

| Name | Role | Status |
|------|------|--------|
| ApacheJIT | Commit-level labels only; optional for faithfulness / surface-cue analyses | NOT_STARTED; source TO VERIFY |
| ReDef corpus | Optional generalization check (C/C++) | NOT_STARTED; source TO VERIFY |

## Rules

- Do not invent counts, defect rates, or split sizes here.
- Do not commit raw dumps until license and release policy are explicit.
- When a dataset is obtained, record: download URL, retrieval date, checksum if available, transforming scripts, and any filtering.

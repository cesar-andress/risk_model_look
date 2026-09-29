# DATA_ACQUISITION_PLAN.md

Status: **PLANNED — NOT EXECUTED**

## Goal

Acquire the authoritative JIT-Fine replication archive immutably, without contaminating git, and prepare empirical schema validation.

## Authoritative remote

- Repo: `https://github.com/jacknichao/JIT-Fine`
- Revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- Archive path: `data.zip`
- Expected size: `75326372` bytes
- Remote git blob SHA-1: `6cd2f45d97a7c430533cde382be6bf42d9ff3649`
- Download URL:  
  `https://raw.githubusercontent.com/jacknichao/JIT-Fine/584799fdec6095ab75a45fd2a5f8db5b12163aa5/data.zip`

Do **not** use `tianc43/JIT-FINE` as primary (mirror with identical blob).

## Local destinations

- Raw archive: `data/raw/upstream/jacknichao_JIT-Fine_584799fdec6095/data.zip`
- Extracted (read-only intent): `data/raw/upstream/jacknichao_JIT-Fine_584799fdec6095/extracted/`
- Logs: `artifacts/data_acquisition/`
- Processed outputs (later gate): `data/processed/` only after schema validation

`data/raw/**` remains gitignored.

## Acquisition steps (next gate)

1. Create destination directories.
2. Download `data.zip` from the frozen URL to the raw path.
3. Record download timestamp (UTC).
4. Record byte size; assert equals `75326372` (or document mismatch).
5. Compute **SHA-256** of the local file; store in `artifacts/data_acquisition/data_zip_sha256.txt` and update manifest (`local_sha256`).
6. Optionally verify Git LFS/blob identity is consistent with expected size (blob SHA already known remotely).
7. Extract deterministically (e.g. `unzip` without modifying timestamps beyond unzip defaults); never edit extracted files.
8. Write inventory listing of extracted paths + sizes.

## Forbidden during acquisition

- Committing raw data or `data.zip`
- Uploading archive to Zenodo/GitHub Releases
- Mutating pickle contents
- Building `build_dataset.py` scientific transforms beyond read-only validators
- Training / attribution

## Post-download validations (must all be logged)

1. Archive size + SHA-256
2. File inventory vs expected JIT-Fine paths
3. Pickle object types / Python types
4. Row counts for train/valid/test changes and features
5. Unique commit IDs per split
6. Train ∩ valid ∩ test (must be empty for commit IDs)
7. Label distributions (commit-level)
8. Projects per split (if project field recoverable)
9. Exact line-level object structure (`changed_type`, labels, texts)
10. Missing values / join failures to features
11. Duplicate commit IDs
12. Commits with zero added lines
13. Positive commits without positive line labels
14. Line labels not matching change text
15. Comparison to published descriptive stats / commonly cited totals

## Exit criteria for DATASET_ACQUISITION_GATE

PASS only if download integrity checks succeed and inventory matches expected files.  
Schema deep validation may continue under DATASET_SCHEMA_VALIDATION_GATE.

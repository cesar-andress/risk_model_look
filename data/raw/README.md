# Raw data directory

The raw dataset archive itself is **deliberately untracked** by Git (`data/raw/**` in `.gitignore`, with exceptions only for this README and `.gitkeep`).

## Authoritative upstream

- Repository: `https://github.com/jacknichao/JIT-Fine`
- Frozen revision: `584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- Source archive path in that revision: `data.zip`
- Immutable raw/blob URL:  
  `https://raw.githubusercontent.com/jacknichao/JIT-Fine/584799fdec6095ab75a45fd2a5f8db5b12163aa5/data.zip`

## Local artifact (after acquisition)

- Path: `data/raw/upstream/data.zip` (gitignored)
- Size: `75326372` bytes
- Git blob SHA-1: `6cd2f45d97a7c430533cde382be6bf42d9ff3649`
- SHA-256: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`

Reproduce acquisition:

```bash
python scripts/acquire_jit_defects4j.py
```

Acquisition metadata: `artifacts/data_acquisition/`.

## Redistribution

Dataset/code license evidence remains **NONE_FOUND**.  
Raw redistribution: **NOT_ESTABLISHED**.  
Derived redistribution: **NOT_ESTABLISHED**.

Users must obtain the archive from the authoritative upstream source.  
Do **not** commit `data.zip`, extract trees, or `*.pkl` into this repository.  
Do **not** upload the raw archive to our Zenodo/GitHub release packages unless permission is later established.

Schema validation and extraction are separate gates and are not performed by the acquisition script.

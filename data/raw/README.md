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

- **Raw upstream dumps** (e.g. JIT-Fine `data.zip`, extract trees, `*.pkl`):
  **not redistributed** and **not relicensed** by this repository. Obtain them
  from the authoritative upstream under upstream terms. Dataset/code license
  evidence in the upstream tree remains as found there (`NONE_FOUND` in our
  acquisition audit).
- **Author-created compact derived summaries** tracked under `artifacts/**`
  (CSV/JSON tables and freeze manifests that do **not** embed upstream source
  text) are included under this repository’s documented **MIT** scope for
  author-owned materials (see root `README.md` Licensing and
  `THIRD_PARTY_NOTICES.md`). That grant does **not** convey rights over the
  upstream datasets.

Do **not** commit `data.zip`, extract trees, or `*.pkl` into this repository.  
Do **not** upload the raw archive to Zenodo/GitHub release packages unless
permission is later established.

Schema validation and extraction are separate gates and are not performed by the acquisition script.

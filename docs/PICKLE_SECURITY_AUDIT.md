# PICKLE_SECURITY_AUDIT.md

Verification date: **2026-09-29**

## Archive provenance

- Path: `data/raw/upstream/data.zip`
- SHA-256 reconfirmed before extraction: `9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47`
- Git blob SHA-1: `6cd2f45d97a7c430533cde382be6bf42d9ff3649`
- Upstream: `jacknichao/JIT-Fine@584799fdec6095ab75a45fd2a5f8db5b12163aa5`
- ZIP `testzip()`: PASS

## Files inspected (static)

| File | Protocol | Risk |
|------|----------|------|
| data/jitfine/changes_train.pkl | 4 | PASS |
| data/jitfine/features_train.pkl | 5 | PASS |
| data/jitfine/changes_valid.pkl | 4 | PASS |
| data/jitfine/features_valid.pkl | 5 | PASS |
| data/jitfine/changes_test.pkl | 4 | PASS |
| data/jitfine/features_test.pkl | 5 | PASS |
| data/jitfine/changes_complete_buggy_line_level.pkl | 5 | PASS |

Machine-readable detail: `artifacts/data_schema/pickle_static_audit.json`

## Referenced modules/globals (features / line-label; protocol 5)

Recovered STACK_GLOBAL targets include only scientific reconstruction helpers:

- `pandas.core.frame.DataFrame`
- `pandas.core.internals.managers.BlockManager`
- `pandas.core.indexes.*`
- `numpy.ndarray` / `numpy.core.multiarray._reconstruct` / `numpy.core.numeric._frombuffer`
- `builtins.slice`

Changes pickles (protocol 4) reconstruct nested builtins containers without recoverable third-party GLOBAL names in the static scan.

## Suspicious executable behavior

**None found.** No `os`/`subprocess`/`socket`/`eval`/`exec`/`ctypes`/`importlib` globals detected.

## Deserialization isolation actually used

| Mechanism | Result |
|-----------|--------|
| `unshare -n` | **Unavailable** (`Operation not permitted`) |
| `bwrap --unshare-net` | **Used** for `scripts/inspect_jitfine_schema.py` |
| Custom RestrictedUnpickler | **Not claimed** as a security boundary |

**DESERIALIZATION_ISOLATION: LIMITED_BWRAP_UNSHARE_NET**

Strong provenance + byte identity + static audit PASS were prerequisites. Isolation is defense-in-depth, not a proof of safety against malicious pickles in general.

## Limitations

- Static STACK_GLOBAL recovery is heuristic; false string pairs are filtered to plausible scientific module prefixes.
- OS-level sandboxing is limited to network unshare via bubblewrap on this host.
- Pickle remains an executable format; future loads should continue to prefer subprocess isolation.

## Overall

**STATIC_PICKLE_RISK (all seven): PASS**

# TOKEN_LINE_MAPPING_REPORT.md

**Gate:** `TOKEN_LINE_MAPPING_GATE`  
**Verdict:** **PASS**  
**Date:** 2026-10-01  

---

## Final primary RQ1

| Field | Value |
|-------|------:|
| ORIGINAL_RQ1_COHORT | 475 |
| PRIMARY_RQ1_POLICY | POLICY_A_COMPLETE_CASE |
| PRIMARY_RQ1_N | **413** |
| RQ1_EXCLUDED_MAPPING_INCOMPLETE | 62 |
| candidates | **13412** |
| positives | **1712** |
| negatives | **11700** |
| unknown | 0 |

Exclusion reason: ground-truth-to-canonical-input mapping incompleteness.  
Bias: incomplete commits tend to have larger candidate universes / diffs (see complete-case bias report).

## Processed dataset

| Split | Records | Positives | SHA-256 (prefix) |
|-------|--------:|----------:|------------------|
| train | 16374 | 1390 | `02e1533c…` |
| valid | 5465 | 467 | `eef7351b…` |
| test | 5480 | 475 | `8efc20c3…` |
| **total** | **27319** | **2332** | |

Deterministic rebuild: **True** (byte-identical SHA-256).

## Stable line ID

`STABLE_LINE_ID_V1` = `(commit, file, change_type, old_lineno, new_lineno, occurrence_index, ordered_position)`

Without `ordered_position`, 1 duplicate key exists under CR-mangled hunks. With it: unique over the filtered U0 stream used for model input.

## Structured format

Markers: `[MSG] [FILE] [HUNK] [ADD] [DEL] [CTX]`  
Primary context: **0** (CHANGED_ONLY)  
Ablation context: **3** (CTX3)  
Message source: JIT-Fine `msgs` (empty: train 9 / valid 6 / test 1; embedded newlines: 0)

## Qwen tokenizer

| Field | Value |
|-------|-------|
| ID | `Qwen/Qwen2.5-Coder-7B-Instruct` |
| Fast | YES |
| Hub refs/main | `c03e6d358207…` |
| Label token `0` | ID **15** (single) |
| Label token `1` | ID **16** (single) |

## Mapping audits

| Audit | Result |
|-------|--------|
| 100-commit exact | **100 / 100** |
| Full CHANGED_ONLY | **27319 / 27319** ok; mapping_error_events=0 |
| Cross-boundary same-line tokens | 2860509 (marker+payload; attributed to payload) |
| Pre-truncation RQ1 | 13412 / 13412 candidates (1712+11700) |

## Llama

`ACCESS_BLOCKED:OSError` — M3_GENERALIZATION_GATE remains blocked.

## RQ1 mask

`NOT_IN_RQ1_UNIVERSE` never coerced to negative.

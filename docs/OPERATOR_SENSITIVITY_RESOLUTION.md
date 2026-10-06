# OPERATOR_SENSITIVITY_RESOLUTION.md

Task: EMSE-FINAL-ANALYSIS-CLOSURE  
Date (UTC): 2026-10-06  
Lock: `docs/EMSE_FINAL_ANALYSIS_LOCK.md`

## Classification

**PRE_SPECIFIED_BUT_UNDERSPECIFIED** (as an executable two-operator RQ2 contrast)

Protocol-obligation outcome: **DOCUMENTED_PROTOCOL_LIMITATION**  
Not BLOCKS_SUBMISSION: the primary RQ2 operator is fully specified and was executed.

## What was specified

- Stats V1 / V1.1: RQ2 primary operator **PAYLOAD_BLANK_V1**; secondary list includes `OPERATOR_DEPENDENCE_DIAGNOSTIC`.
- Stats V1 text: `SEGMENT_DELETE operator: RQ2_SENSITIVITY`.
- ATTRIBUTION_PROTOCOL_V1.1/V1.2: occlusion *attribution* operator is **SEGMENT_DELETE_V1**; RQ2 perturbation is **PAYLOAD_BLANK_V1**.
- DECISION_LOG 2026-10-01: reuse of SEGMENT_DELETE for RQ2 perturbation was **rejected** (self-evaluation / circularity with occlusion).

## What was executed

TEST faithfulness jobs apply `apply_payload_blank_record` only. No second-operator AOPC matrix exists.

## Why not executed now

A SEGMENT_DELETE perturbation sweep would be new GPU work. The executable pairing of deletion semantics, token-budget matching, and missingness for a two-operator contrast was never frozen at TEST-execution specificity. Inventing it after observing PAYLOAD_BLANK results would be a new experiment, which this task forbids.

## Manuscript handling

Report RQ2 as **PAYLOAD_BLANK_V1** only. Describe operator dependence as an unexecuted secondary diagnostic. Do not claim a frozen operator-sensitivity result.

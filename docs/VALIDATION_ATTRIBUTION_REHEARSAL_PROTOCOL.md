# VALIDATION_ATTRIBUTION_REHEARSAL_PROTOCOL.md

Status: **FROZEN pre-test pipeline rehearsal** (not started)  
Gate: `VALIDATION_ATTRIBUTION_REHEARSAL_GATE = NOT_STARTED`  
Config: `configs/validation/attribution_rehearsal_v1.yaml`

## Timing

AFTER `FULL_TRAINING_GATE` completes, BEFORE any TEST attribution.

## Cohort

`ATTRIBUTION_VALIDATION_REHEARSAL_N = 64` positive validation commits.  
Deterministic selection with project + input-length quartile coverage.  
Selection independent of model predictions.

## Content

Full attribution pipeline on the 64 commits:

- attention primary + LAST4 sensitivity  
- vanilla gradient, Grad×Input  
- IG ZERO + PAD  
- line occlusion  
- PAYLOAD_BLANK faithfulness + SEGMENT_DELETE sensitivity  
- RQ metrics where labels/support permit  
- caching + stats plumbing  

## Base-model sanity

16 of the 64 commits; methods: attention primary + Grad×Input only.  
Compare adapted M1 vs frozen Qwen base (no LoRA). Validation-only; not a test result.

## May change

Implementation bugs, OOM engineering, cache keys, tensor positions, renderer corruption, numerical crashes, serialization errors.

## Must NOT change (result-driven)

Ranking definition, primary endpoint, IG baseline, faithfulness metric, polarity epsilon, method inclusion, statistical test — because a method looks poor.

Any genuine methodological change requires a new versioned protocol amendment **before** test attribution.

## Acceptance (technical)

Pipeline executes; schemas valid; cache round-trip; no label leakage; perturbations not corrupted; memory feasible; missingness recorded; IG convergence logic executes; stats pipeline accepts outputs.

**No** localization/faithfulness score threshold.

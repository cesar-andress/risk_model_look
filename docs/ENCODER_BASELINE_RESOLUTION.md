# ENCODER_BASELINE_RESOLUTION.md

Task: EMSE-FINAL-ANALYSIS-CLOSURE  
Date (UTC): 2026-10-06  
Lock: `docs/EMSE_FINAL_ANALYSIS_LOCK.md` (`aba73ea`)

## Classification

**PRE_SPECIFIED_BUT_UNDERSPECIFIED**

Protocol-obligation outcome: **DOCUMENTED_PROTOCOL_LIMITATION**  
Does **not** BLOCKS_SUBMISSION if the manuscript states that the encoder comparator was required in protocol but never given an executable identity/recipe, and is therefore a limitation rather than a completed baseline.

## What was specified (before TEST outcomes)

- ATTRIBUTION_PROTOCOL_V1.2 model scope: `ENCODER_BASELINE = REQUIRED` (`configs/attribution/m1_methods_v1_2.yaml`; protocol commit `3fa90ded…`).
- EXPERIMENT_PROTOCOL_V0: “Encoder baseline: CodeBERT or UniXcoder — subject to later protocol verification.”
- Role: contextual encoder comparator, not a second decoder.

## What is missing

- Frozen architecture choice (CodeBERT vs UniXcoder).
- Frozen checkpoint / training recipe (epochs, lr, inputs, head).
- Frozen attribution contract mapping encoder tokens onto JIT lines.
- Any cached encoder attribution jobs.

## Why faithful execution is impossible without a new analytical choice

Executing now would invent the identity and training protocol after TEST method rankings and baseline results were observed. That would not complete the frozen recipe; it would start a new experiment. This task forbids new model families and new training.

## Manuscript handling

State as a limitation: a pre-specified encoder comparator was not executable under the frozen protocols and was not run. Do not impute encoder numbers. Do not describe the study as a multi-architecture comparison.

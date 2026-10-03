# ATTRIBUTION_COMPUTE_PLAN.md

Static planning only. No GPU attribution runs under this gate.

## Estimator

`src/experiments/compute_plan.estimate_attribution_compute`

Inputs: `#commits`, mean `#candidate regions`, IG steps, occlusion granularity,
method inclusion flags.

Outputs: estimated forward/backward passes (upper-bound style for Grad×Input).

## Example (illustrative arithmetic, not a job launch)

For N=304 fully visible RQ1 commits, ~32 candidates/commit mean, IG steps=32,
all methods enabled: use the estimator before any 7B job.

## Cache contracts

### Occlusion

Key fields: model checkpoint hash, dataset version, representation, commit ID,
region definition, perturbation policy, prompt version (+ score target, max length).

### Attribution (attention / gradient / IG)

Key fields: model checkpoint hash, dataset version, representation, commit ID,
method id, method config hash, target, prompt version, tokenizer id, max length, family.

**Prohibited:** keying only by commit ID.

## Adapter binding

`configs/attribution/m1_methods_v1.yaml` uses
`adapter_path: RESOLVE_FROM_M1_FINAL_MANIFEST`.  
Do not bind seed-13 intermediate checkpoints.

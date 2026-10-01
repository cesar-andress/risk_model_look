# RQ1_CANDIDATE_MASK_CONTRACT.md

Status: **FROZEN (semantics)** — mask not yet applied to model scores.

## Purpose

Separate **RQ1 localisation evaluation** from the fuller canonical model-input
line set used by RQ2–RQ4.

## Domain

For every canonical **added** line in a gold-positive test commit (under the
frozen Git reconstruction), assign exactly one of:

| Value | Meaning |
|-------|---------|
| `RQ1_POSITIVE` | Line is in \(U_{\mathrm{JITFINE}}\) (Policy A) and Layer-B `label == 1.0` |
| `RQ1_NEGATIVE` | Line is in \(U_{\mathrm{JITFINE}}\) and Layer-B `label == 0.0` |
| `NOT_IN_RQ1_UNIVERSE` | Canonical Git added line with **no** Policy-A row mapping |

## Hard prohibitions

- **Never** map `NOT_IN_RQ1_UNIVERSE` → `RQ1_NEGATIVE`.
- **Never** use `UNKNOWN_AS_NEGATIVE`.
- Primary RQ1 metrics (Top-k, Recall@k, MRR, MAP, AUROC/AUPRC over labelled
  candidates) may consume only `RQ1_POSITIVE` ∪ `RQ1_NEGATIVE`.
- Effort / IFA over full Git ranking remain **invalid** while
  `NOT_IN_RQ1_UNIVERSE` lines exist (see `RQ1_METRIC_VALIDITY_MATRIX.md`).

## Abstraction

```
rq1_candidate_mask[canonical_line_id] ∈ {
  RQ1_POSITIVE,
  RQ1_NEGATIVE,
  NOT_IN_RQ1_UNIVERSE
}
```

Implemented as `RQ1CandidateMask.classify(in_policy_a=..., label=...)` in
`src/data/policy_a_canonical_bridge.py`.

## Relationship to scopes

| RQ | Ranking / attribution domain | Label mask |
|----|------------------------------|------------|
| RQ1 | Scores on \(U_{\mathrm{JITFINE}}\) only | this mask |
| RQ2–RQ4 | Full actual model input | mask unused for faithfulness/occlusion |

## Open

- `CONTEXT_POLICY` (context lines are always `NOT_IN_RQ1_UNIVERSE` if present).

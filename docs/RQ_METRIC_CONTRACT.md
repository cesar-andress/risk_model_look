# RQ_METRIC_CONTRACT.md

Status: **INFRASTRUCTURE** — definitions and guards only; no scientific results.

## Separation

| Module | Role |
|--------|------|
| `src/metrics/localization.py` | RQ1 plausibility / localization |
| `src/metrics/faithfulness.py` | RQ2 prediction-perturbation faithfulness |
| `src/metrics/polarity.py` | RQ3 signed polarity |
| `src/metrics/surface_cues.py` | RQ4 category mass |

Do **not** call localization accuracy “faithfulness”.

## RQ1 universe (Policy A)

Denominator / ranking domain: only `RQ1_POSITIVE` and `RQ1_NEGATIVE`.  
Never include `NOT_IN_RQ1_UNIVERSE`.  
Label-universe guard refuses `UNKNOWN` for IFA / effort metrics.

### Metrics

- Top-1, Top-5, Top-10 (commit-level hit in top-k)
- IFA
- Recall@20%Effort
- Effort@20%Recall

### Ranking transforms (explicit)

`SIGNED_DESCENDING` | `ABS_DESCENDING` | `POSITIVE_PART_DESCENDING`  
None silently chosen as sole primary in infrastructure.

### Tie handling

Primary key: `rank_score` descending.  
Secondary: `stable_order` ascending, then `region_id` ascending.  
Python’s sort stability must not define scientific outcomes alone.

### IFA indexing

**Convention:** `ZERO_BASED_FALSE_ALARM_COUNT`  
Matches `src/metrics/label_universe_guard.ifa_requires_known_negatives`:  
IFA = index of first positive in the ranked list (= number of negatives inspected before first buggy line).  
If the first candidate is positive, IFA = 0.  
If no positive exists, IFA = n (guarded separately for primary RQ1).

`IFA_INDEXING_DECISION_REQUIRED = false` under this project guard alignment.
If a future literature reconciliation requires one-based reporting, record a new
protocol decision before changing the metric.

### Effort definitions

- Recall@20%Effort: among ranked candidates, take \(k=\max(1,\lfloor 0.2 n\rfloor)\) top lines;
  recall = (# positives in top-k) / (# positives). Requires known binary labels.
- Effort@20%Recall: fraction of candidates inspected until
  \(\max(1,\lfloor 0.2\cdot n_{\mathrm{pos}}\rfloor)\) positives are found.

Rounding matches existing `label_universe_guard` (`int(0.2 * n)`).

## RQ2 faithfulness

Score spaces: `probability` and `logit_contrast` (primary space = TBD_PROTOCOL).

- **Comprehensiveness** = `score(x) - score(x \\ R)` (higher ⇒ removal reduces buggy evidence).
- **Sufficiency** form `full_minus_region_only` = `score(x) - score(R_only)`;
  raw orientation is lower-is-more-sufficient; also expose `sufficiency_higher_better = -raw`.

Perturbation fractions (defaults): 5%, 10%, 20%, 30%, 50%.

Random controls: deterministic seeded selection; optional length/token-matched random.

## RQ3 polarity

Fractions positive / negative / near-zero with **explicit** epsilon (no silent default).  
Sign agreement between attribution and occlusion Δ; coverage excluding near-zero.  
Not “causal correctness”.

## RQ4 surface cues

Signed sum, absolute mass, normalized absolute mass over semantic categories.  
Test-file classifier: scaffold only; default `UNKNOWN`.

# Methods scaffold (protocol-aligned notes)

Status: structured notes for manuscript Methods. **No Results.**  
Every statement maps to an already verified protocol / contract in the code repo.

## Dataset

- Primary public data: JIT-Defects4J / JIT-Fine author split (`changes_*.pkl`, features, line labels).
- Measured sizes: train 16374 / valid 5465 / test 5480; positives 2332.
- Line labels: test gold-positive commits only (n=475); deleted lines labelled 0.0.

## Canonical diff representation

- Ordered historical first-parent Git reconstruction; primary `CHANGED_ONLY` (context 0); ablation CTX3.
- Markers: `[MSG] [FILE] [HUNK] [ADD] [DEL] [CTX]`.
- Max length primary 2048; truncation `WHOLE_SEGMENT_PREFIX_TRUNCATION_V1`.
- Not equivalent to lossy JIT-Fine `added_code`/`removed_code` sets.

## RQ1 labelled universe

- Policy-A complete-case primary: N=413 of 475; candidates 13412 (1712 pos / 11700 neg / 0 unknown).
- Statuses: `RQ1_POSITIVE` / `RQ1_NEGATIVE` / `NOT_IN_RQ1_UNIVERSE` (never coerced to negative).

## Complete-case selection

- 62 excluded for GT↔canonical mapping incompleteness (not noise filtering).
- Bias: incomplete commits tend toward larger diffs / candidate universes (audited).

## Token-to-line mapping

- Fast tokenizer offsets; `TOKEN_MAP_VERSION=1`; Qwen2.5-Coder-7B-Instruct rev `c03e6d…`.
- Stable line ID V1 includes `ordered_position`.

## M1 formulation

- Causal next-token classification `"0"`/`"1"`; \(p_{\mathrm{buggy}}=\mathrm{softmax}([\ell_0,\ell_1])_1\).
- Explanation target: \(s=\ell_1-\ell_0\).

## Attribution methods (infrastructure)

Attention (explicit classification query position), vanilla gradient, Grad×Input,
Integrated Gradients (explicit baselines), signed structured occlusion (line/hunk/…).

## Localization metrics

Top-1/5/10, IFA (0-based false-alarm count), Recall@20%Effort, Effort@20%Recall;
ranking transform explicit; RQ1 universe guard active.

## Faithfulness metrics

Comprehensiveness and sufficiency in probability and logit-contrast spaces;
perturbation curves; seeded / length-matched random controls.

## Numerical model results

Deferred until `FULL_TRAINING_GATE` and `ATTRIBUTION_RESULTS_GATE`. Do not insert
live training metrics here.

# ATTRIBUTION_METHOD_CONTRACT.md

Status: **INFRASTRUCTURE FROZEN for interfaces**  
Gate: `ATTRIBUTION_INFRASTRUCTURE_GATE`  
Not: `ATTRIBUTION_RESULTS_GATE` / `RQ1_RESULTS_GATE`

## Explanation target (M1)

Canonical scalar:

\[
s(x) = \ell_1(x) - \ell_0(x)
\]

Identity (restricted two-class softmax over label tokens `0`/`1`):

\[
p_{\mathrm{buggy}} = \mathrm{softmax}([\ell_0,\ell_1])_1,
\quad
\mathrm{logit}\!\left(\frac{p_{\mathrm{buggy}}}{1-p_{\mathrm{buggy}}}\right) = \ell_1 - \ell_0
\]

Primary attribution must **not** use generated-token likelihood, argmax class alone,
or full-vocabulary probability as the target.

## Common result object

Fields: `method_name`, `score_space`, `signed` (explicit bool), `target_definition`,
`token_scores` (one scalar per model-visible input token), optional `metadata`.

Signedness is never inferred from method names.

## Attention

Query position (M1 default): **first assistant classification-token logits**.

Configurable: layer selection, head aggregation, query-position policy, token aggregation.

Presets (not ranked): last-layer mean-head; last-layer max-head; mean over final-k layers.

## Gradients

- Vanilla gradient on input embeddings; token score = sum over embedding dims.
- Grad×Input: \(e \odot \partial s/\partial e\), sum over dims; **sign preserved**; no `abs()` in core.

## Integrated Gradients

Configurable steps; baselines as explicit options:

- `ZERO_EMBEDDING`
- `PAD_TOKEN_EMBEDDING`

Completeness diagnostic: \(\sum_t a_t \approx s(x) - s(x')\).

## Occlusion (signed; frozen convention)

\[
\Delta_R = s(x) - s(x_{\setminus R})
\]

| Sign | Meaning |
|------|---------|
| \(\Delta_R > 0\) | region supports buggy prediction |
| \(\Delta_R < 0\) | region suppresses buggy / supports clean |

Units: `TOKEN`, `LINE`, `HUNK`, `MESSAGE`, `FILE_PATH`, `FILE`.

Removal operates on the **structured** representation then re-render/re-tokenize.
Do **not** zero arbitrary token IDs.

## Line aggregation

Reductions: `SUM`, `MEAN`, `MAX_ABS_WITH_SIGN` (protocol-configurable).
Primary *candidate*: `SUM` (conservation interpretability); not frozen yet.

## Categories (from token-map contract)

`COMMIT_MESSAGE`, `FILE_PATH`, `HUNK_HEADER`, `ADDED_CODE`, `DELETED_CODE`,
`CONTEXT_CODE`, `STRUCTURAL_MARKUP`, `SPECIAL_TOKEN`.

Do not recreate via regex on rendered strings.

## Method registry

Versioned specs record signedness, grad/forward requirements, line/hunk support,
default aggregation, target. No performance claims.

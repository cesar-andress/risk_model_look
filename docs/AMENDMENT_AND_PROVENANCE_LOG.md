# AMENDMENT_AND_PROVENANCE_LOG.md

Public provenance trail (not a Results narrative).

| Object | Identifier |
|--------|------------|
| Original TEST freeze (superseded) | SHA-256 `8caad443f4a69d7040ae7e966053e12f83f33ce9dc11eb2ea029818ecc68ec95` |
| Reason for correction | IG valid-seed mask used a non-method-specific aggregation (forensic gate) |
| Corrective commit | `b9e59faa71435f31a656fd52b87481ec7e14a39c` |
| Corrected TEST freeze | SHA-256 `a707e8e7016eb94eafe57c6e793e60fbd5cb9269eb6329cd79938e84e74b1a19` |
| TOSEM extension lock | `docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md` commit `840bb45eda317908d7f953e67f27dafbad1c5cf6` SHA-256 `855415e785b41d3a6a233b33fb624da76cc35f48f7beedbe13b16498aca31540` |
| Extension results freeze | `artifacts/tosem_extension/TOSEM_EXTENSION_RESULTS_FREEZE.json` SHA-256 `5e5c67e068a668f046ca2c1efe04a6b03f1a147bb3f09ded54a1b9710561df9b` |
| NUMERICAL_GATE | **FAIL** (not reinterpreted as pass) |
| EMSE final-analysis lock | `docs/EMSE_FINAL_ANALYSIS_LOCK.md` commit `aba73ea63f3534acc292e4e4640dfa53ec22bcf6` SHA-256 `7e54a8f394be36b0958cf7d8b9bf8e36121930b9d981b0bcce0e2496557e81dd` |
| Venue | EMSE; TOSEM track closed |

## Encoder baseline (required, not executed)

| Field | Value |
|-------|--------|
| Governance class | **PRE_SPECIFIED_BUT_UNDERSPECIFIED_LIMITATION** |
| Chronology | `ENCODER_BASELINE = REQUIRED` in ATTRIBUTION_PROTOCOL_V1.2 (commit `3fa90ded…`, before TEST). Identity left as “CodeBERT or UniXcoder — subject to later protocol verification” (EXPERIMENT_PROTOCOL_V0). No executable recipe was frozen before outcomes. |
| Not | POST_OUTCOME_PROTOCOL_DEVIATION (the recipe was never completed after seeing TEST rankings). |
| Also | Outcome-blind non-execution of a **required** comparator: TEST proceeded without it because the recipe was missing, not because results looked unfavourable. |
| Action | Do not invent CodeBERT/UniXcoder training now. |

See `docs/ENCODER_BASELINE_RESOLUTION.md`.

Raw TEST attribution jobs were not overwritten. Scientific definitions of RQ1/RQ2/RQ3 estimands were not changed. IG was not rerun.

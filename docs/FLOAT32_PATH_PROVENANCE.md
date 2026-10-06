# FLOAT32_PATH_PROVENANCE.md

Task: EMSE-FINAL-ANALYSIS-CLOSURE  
Date (UTC): 2026-10-06

## Classification

**SCORING_ONLY**

Rankings were **not** recomputed under float32.

## Evidence

`scripts/tosem_numerical_and_random.py` (lock `840bb45`):

1. Loads existing TEST jobs `line_scores_sum` for attention and Grad×Input.
2. Ranks with `rank_abs` on those frozen SUM scores (`RankingTransform.ABS_DESCENDING`).
3. Re-encodes the same commits and recomputes \(s=\ell_1-\ell_0\) and PAYLOAD_BLANK AOPC curves under:
   - canonical FrozenM1Bundle (NF4, bfloat16 compute);
   - a BitsAndBytes reload of the **same adapters** with `bnb_4bit_compute_dtype=torch.float32`.
4. Token-matched random rankings are generated from the frozen attention candidate universe, not from a new attribution method.

Lock `docs/TOSEM_EXTENSION_PROTOCOL_LOCK.md` states the primary variant keeps adapters, dataset, rankings, and PAYLOAD_BLANK semantics.

## Manuscript-safe wording

The float32 path recomputed perturbation scoring / AOPC evaluation for frozen attribution rankings; it is not a full re-attribution of tokens under float32 compute.

## NUMERICAL_GATE

Remains **FAIL**. This document does not change the gate.

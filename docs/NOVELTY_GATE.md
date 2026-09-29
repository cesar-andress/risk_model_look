# NOVELTY_GATE.md

## STATUS

**PASS**

Audit completed: **2026-09-29**.  
Literature cutoff: **2026-09-29**.  
Artifacts: `docs/literature_search_log.csv`, `docs/literature_screening.csv`, `docs/NOVELTY_COLLISION_MATRIX.md`, `docs/STATE_OF_ART_NOVELTY_MAP.md`.

## Collision rule applied

A **direct novelty collision** requires prior public work that evaluates **both**:

1. explanation faithfulness for JIT defect / commit-risk prediction on **public** data; **and**
2. signed / directional attribution equivalent to our RQ3 classes **D/E** (prediction change under removal/occlusion determining whether regions increase vs decrease risk; preferably line/hunk level).

**Result:** no inspected source satisfies both conditions.

## Critical candidates C1–C10

All classified in `docs/literature_screening.csv` (see also novelty map). None trigger FAIL.

Highest near-collisions: R1 (decoder attention + polarity gap, internal data), EASE 2026 (Comp/Suff method suite on non-JIT encoder models), JITEC/CodeFlowLM (public JIT-Defects4J localization without verified RQ2+RQ3).

## Project-note conflict resolution

Earlier notes both claimed a novelty check on 2026-09-29 **and** said a search was still pending. This gate supersedes both: an auditable search now exists; the old broad “first …” claim is **rejected** as unsafe.

## PROVISIONAL DEFENSIBLE NOVELTY CLAIM

Prior work separately studies attention highlighting for industrial decoder commit-risk models, public JIT line localization for encoder and prompted-LLM settings, and perturbation fidelity for encoder/encoder-decoder code models. This study targets their intersection: an open comparison of attention, gradient-based attribution, Integrated Gradients, and signed occlusion for fine-tuned decoder-only commit-risk classifiers on public line-labeled JIT data, jointly evaluating localization, prediction-perturbation faithfulness, and attribution polarity.

Avoid “first ever” / “no previous work” phrasing in the manuscript unless a later re-audit strengthens evidence.

## Remaining risks (do not reopen ENVIRONMENT_GATE)

- JITEC full text was not fully accessible; RQ2/RQ3 cells remain UNKNOWN rather than NO.
- Continuous monitoring needed for Rigby/Mockus/Abreu public follow-ups to R1.
- Reviewer conflation risks: transformer≠decoder-only LLM; XMENTOR sign agreement ≠ RQ3 polarity.

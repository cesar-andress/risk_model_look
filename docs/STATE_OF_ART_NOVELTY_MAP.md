# STATE_OF_ART_NOVELTY_MAP.md

Audit date: **2026-09-29**. Literature cutoff: **2026-09-29**.

This document attacks the provisional “first open comparison …” claim. Prefer a narrow true claim over a broad false “first”.

---

## 1. CLOSEST PRIOR WORK

1. **C1 — R1 / Meta (AIware 2026)** — decoder-only LLM commit-risk highlighting via last-layer attention; line/hunk aggregation; industrial expert-line evaluation; **internal** data; **no** faithfulness evaluation; polarity flagged as limitation/future work.
2. **C8 — CodeFlowLM (arXiv 2512.00231)** — public **JIT-Defects4J** localization with attention-based PLMs and **prompted** commercial LLMs; label-noise discussion; **no** fine-tuned decoder attribution fidelity/polarity.
3. **C4 — JITEC (JSEP 2026)** — public JIT-Defects4J unified prediction+localization using CodeBERT attention + LIME; closest **RQ1** public encoder localization competitor.
4. **C3 — EASE 2026 fidelity paper** — Comp/Suff comparison of attention/IG/LIME/SHAP/rollout on CodeBERT/GraphCodeBERT/CodeT5 (function defect / CodeXGLUE); closest **RQ2 method suite**, wrong task granularity and architecture class for our object of study.
5. **C5 — JIT-LSM (IST 2026)** — LLM+small-model hybrid for JIT localization on extended public data; evaluates **generated explanation quality**, not attribution faithfulness/polarity.

---

## 2. WHAT R1 ALREADY ESTABLISHES

- Attention from a fine-tuned decoder-only Diff Risk Score model can be aggregated to lines/hunks/files.
- Highlighting can be evaluated against expert-labeled risky lines (coverage vs review effort / ARP-style tradeoff).
- Scalability argument: attention is a byproduct of inference.
- Explicit non-claim: attention is **not** asserted as causally faithful.
- Explicit open problem: **directional ambiguity** (highlights may mark regions that decrease risk).
- Engineering surface cue: test-file path filtering.

## 3. WHAT JIT XAI PRIOR WORK ALREADY ESTABLISHES

- Feature-level JIT explanations with LIME/SHAP/PyExplainer/BreakDown/counterfactuals/formal methods (FoX, CfExplainer, XMENTOR, EvaluateXAI lineage).
- Public line-level localization for encoder / hybrid models on JIT-Defects4J (JIT-Fine, JIT-Smart, JITEC, CodeFlowLM attention baselines).
- Human-centered aggregation of conflicting feature explainers (XMENTOR), including **sign agreement** across LIME/SHAP/BreakDown.

## 4. WHAT GENERAL TRANSFORMER FIDELITY WORK ALREADY ESTABLISHES

- Comprehensiveness/Sufficiency (and related perturbation metrics) for CodeBERT/GraphCodeBERT/CodeT5-style models (EASE 2026 / CoScoreX transformer study).
- Separate ICSME CoScoreX study for **Random Forest module SDP** stability (must not be merged with the EASE transformer paper).
- Decoder-only attribution faithfulness tooling outside SE/JIT (Grad-ELLM; Jacobian Scopes AOPC).

## 5. WHAT LINE-LEVEL LOCALIZATION WORK ALREADY ESTABLISHES

- Effort-aware line metrics and attention/LIME localization on JIT-Defects4J.
- Vulnerability-domain Detection Alignment with attention / AttnLRP / IG (Pintore et al., 2026): methodologically adjacent, different task.

## 6. WHAT REMAINS UNTESTED (relative to planned study)

Intersection still not found in this audit:

- fine-tuned **decoder-only** commit-risk classifier;
- on **public** line-labeled JIT data;
- comparing attention / Grad×Input / IG / **signed occlusion**;
- with **prediction-perturbation faithfulness** (RQ2);
- and **explicit polarity** of highlighted regions via occlusion Δrisk (RQ3 D/E);
- plus surface-cue mass analysis (RQ4).

## 7. DIRECT COLLISIONS

**NONE** under the A∧B rule (public-data JIT faithfulness **and** RQ3-equivalent directional attribution).

## 8. NEAR-DIRECT COLLISIONS

- R1: decoder LLM + line/hunk attention + polarity gap stated, but internal data and no faithfulness.
- JITEC / CodeFlowLM: public JIT-Defects4J localization, but encoder/prompted-LLM objects and no (verified) RQ2+RQ3 suite.
- EASE 2026: almost our RQ2 method list, but function-level CodeXGLUE encoder/encoder-decoder defect models; no RQ3 polarity.
- XMENTOR: JIT + “sign”, but feature-level class-B sign agreement, not RQ3 D/E.
- JIT-LSM: “LLM + JIT localization”, but NL explanation quality ≠ attribution faithfulness.

## 9. CONTRIBUTIONS WE MUST NOT CLAIM

- “First explainable JIT defect prediction.”
- “First line-level JIT localization.”
- “First use of attention / LIME / IG / Comp/Suff in software defect models.”
- “First LLM for JIT localization.”
- “XMENTOR does not study signs” (false — it does, but differently).
- “No prior work discusses attention polarity” (R1 does, as limitation).
- Unqualified “first open reproducible comparison of attention, gradients, IG, and signed occlusion …” without scoping to **decoder-only fine-tuned commit-risk classifiers on public line-labeled JIT data with RQ2+RQ3**.

## 10. MINIMUM DEFENSIBLE CONTRIBUTION

Prior work separately studies (i) attention highlighting for industrial decoder commit-risk models, (ii) public JIT line localization for encoder/prompted-LLM settings, and (iii) perturbation fidelity for encoder/encoder-decoder code models. Under the 2026-09-29 audit, we did not find a public study that jointly evaluates localization, prediction-perturbation faithfulness, and signed/occlusion-based polarity for fine-tuned decoder-only commit-risk classifiers on line-labeled JIT data.

## 11. NOVELTY RISKS

- JITEC full text inaccessible here: if it already runs Comp/Suff + polarity on CodeBERT JIT-Defects4J, RQ1/RQ2 novelty narrows further (still not decoder-only).
- Rigby/Mockus/Abreu group may publish a public follow-up to R1 that closes polarity+fidelity; monitor continuously.
- Reviewers may collapse “transformer = LLM”; manuscript must keep architecture classes distinct.
- Reviewers may equate XMENTOR “sign agreement” with RQ3; manuscript must define RQ3 as occlusion/perturbation polarity (D/E), not explainer-consensus signs (B).

---

## RQ2 + RQ3 collision test (summary)

See `docs/NOVELTY_COLLISION_MATRIX.md`. No source simultaneously satisfies public-data JIT faithfulness and RQ3 D/E polarity.

## Faithfulness typology used in this audit

| Type | Examples in corpus |
|------|--------------------|
| PREDICTION PERTURBATION | EASE Comp/Suff; Jacobian Scopes AOPC; planned RQ2 |
| SURROGATE FIDELITY | CfExplainer local fitness; LIME/PyExplainer local models |
| FORMAL CORRECTNESS | FoX AXp/CXp |
| STABILITY / ROBUSTNESS | ICSME CoScoreX; EvaluateXAI consistency |
| HUMAN TRUST / PLAUSIBILITY | XMENTOR user study; JIT-LSM explanation coherence |
| GROUND-TRUTH LOCALIZATION | R1 O-RC coverage; JITEC/CodeFlowLM/Pintore DA |

These are not interchangeable.

## Architecture typology used in this audit

| Class | Examples |
|-------|----------|
| traditional ML | FoX LR/RF; XMENTOR GB; ICSME CoScoreX RF |
| encoder transformer | CodeBERT / GraphCodeBERT / UniXcoder (JITEC, EASE, CodeFlowLM baselines) |
| encoder-decoder | CodeT5 / CodeT5+ |
| decoder-only LLM | R1 DRS; DRS-OSS Llama-3.1-8B; planned Qwen2.5-Coder-7B |
| prompted proprietary LLM | CodeFlowLM GPT/Claude/Gemini localization |
| hybrid | JIT-LSM LLM+small model |

# NOVELTY_COLLISION_MATRIX.md

Cutoff: literature available up to **2026-09-29**.

Legend: `YES` / `NO` / `PARTIAL` / `UNKNOWN`

| Work | public JIT data | line labels | decoder-only fine-tuned classifier | attention | Grad×Input | IG | occlusion | line/hunk explanation | localization evaluation | faithfulness evaluation | signed attribution | explicit direction/polarity | surface-cue analysis | public replication |
|------|-----------------|-------------|------------------------------------|-----------|------------|----|-----------|-----------------------|-------------------------|-------------------------|--------------------|-----------------------------|----------------------|--------------------|
| C1 R1 Meta AIware'26 | NO | YES (internal O-RC) | YES | YES | NO | NO | NO | YES | YES | NO | NO | PARTIAL (limitation/future work) | PARTIAL | NO |
| C2 XMENTOR FORGE'26 | YES | NO | NO | NO | NO | NO | NO | NO (feature-level) | NO | NO | YES (feature signs) | PARTIAL (sign agreement = class B) | NO | PARTIAL |
| C3 EASE'26 transformer fidelity | NO (function CodeXGLUE defect, not JIT commit) | NO | NO | YES | UNKNOWN | YES | PARTIAL (masking) | PARTIAL (token) | NO | YES (Comp/Suff) | UNKNOWN | NO | NO | YES |
| C10 ICSME'26 CoScoreX RF | NO (module SDP) | NO | NO | NO | NO | NO | NO | NO | NO | PARTIAL (proxy/stability) | PARTIAL | PARTIAL (contrastive) | NO | YES |
| C4 JITEC JSEP'26 | YES (JIT-Defects4J) | YES | NO (CodeBERT hybrid) | YES | NO | NO | NO | YES | YES | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| C5 JIT-LSM IST'26 | YES (JIT-Defect-Extended) | YES | PARTIAL/UNKNOWN (LLM+small hybrid) | UNKNOWN | NO | NO | NO | PARTIAL | YES | NO (NL coherence) | NO | NO | UNKNOWN | UNKNOWN |
| C6 FoX TOSEM'24 | YES (OpenStack/Qt features) | NO | NO | NO | NO | NO | NO | NO | NO | YES (formal correctness) | PARTIAL | PARTIAL (feature CXp) | NO | YES |
| C7 CfExplainer JSS'24 | UNKNOWN | NO | NO | NO | NO | NO | NO | NO | NO | PARTIAL (surrogate fitness) | UNKNOWN | PARTIAL (feature CF) | NO | PARTIAL |
| C8 CodeFlowLM arXiv'25 | YES (JIT-Defects4J) | YES | NO (PLM + prompted LLMs) | YES | NO | NO | NO | YES | YES | NO | NO | NO | PARTIAL | UNKNOWN |
| C9 Pintore et al. ML'26 | NO (vuln datasets) | YES | NO | YES | NO | YES | NO | YES | YES | PARTIAL (Detection Alignment) | PARTIAL | NO | YES | YES |
| R3 DRS-OSS arXiv'25 | YES (ApacheJIT) | NO | YES | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO | YES |
| **PLANNED STUDY (this work)** | **YES (JIT-Defects4J planned)** | **YES** | **YES (Qwen2.5-Coder-7B; optional Llama-3.1-8B)** | **YES** | **YES** | **YES** | **YES (signed line/hunk)** | **YES** | **YES (RQ1)** | **YES (RQ2 Comp/Suff/AOPC)** | **YES** | **YES (RQ3 D/E)** | **YES (RQ4)** | **YES (intended)** |

## RQ2 + RQ3 collision test

**Direct collision rule:** prior public work evaluates **both** (A) explanation faithfulness for JIT defect/commit-risk on public data **and** (B) signed/directional attribution equivalent to our RQ3 (classes D/E: prediction change under removal/occlusion to determine whether a region increases/decreases risk, ideally at line/hunk level).

| Source with MEDIUM/HIGH RQ2 | Faithfulness type | Also RQ3 D/E? | Verdict |
|-----------------------------|-------------------|---------------|---------|
| C3 EASE'26 | PREDICTION PERTURBATION (Comp/Suff) on **non-JIT** CodeXGLUE function defect + transformers (encoder/encoder-decoder) | NO in inspected materials | **No direct collision** (fails A because not JIT commit-risk; fails B) |
| C6 FoX | FORMAL CORRECTNESS on classical JIT feature models | Feature-level contrastive only; not code hunk polarity | **No direct collision** |
| C7 CfExplainer | SURROGATE FIDELITY | Feature counterfactuals only | **No direct collision** |
| Jacobian Scopes / Grad-ELLM | PREDICTION PERTURBATION on decoder LLMs, non-JIT tasks | Not JIT polarity | **No direct collision** |
| C1 R1 | No faithfulness evaluation | Polarity identified as limitation/future work; internal data | **No direct collision** |
| C2 XMENTOR | No faithfulness | Sign agreement = class **B**, not D/E | **No direct collision** |

**Result:** no inspected source satisfies A∧B on public data as of 2026-09-29.

Caveat: C4 JITEC full text was ABSTRACT_ONLY for RQ2/RQ3 absences → cannot convert UNKNOWN→NO for those cells; even if later found to include Comp/Suff, RQ3 D/E remains unverified and would still need explicit polarity evaluation to collide.

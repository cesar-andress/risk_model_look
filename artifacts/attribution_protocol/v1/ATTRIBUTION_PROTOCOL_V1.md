# ATTRIBUTION_PROTOCOL_V1.md

Status: **FROZEN** (pre-result)  
Gate: `ATTRIBUTION_PROTOCOL_FREEZE_GATE`  
Config: `configs/attribution/m1_methods_v1.yaml`  
**ATTRIBUTION_PROTOCOL_HASH:** `73f0f891683f926a39d68b078f6e2770a1b42181ba1a9f56575c5556cba4794d`  
Manifest: `artifacts/attribution_protocol/protocol_manifest.json`

No scientific M1 attribution results may be produced under a different protocol
without a new hashed version.

---

## 1. Explanandum

Primary scalar target: **RISK_LOGIT_CONTRAST_V1**

\[
s(x) = \ell_1(x) - \ell_0(x)
\]

Used by gradient, Grad×Input, Integrated Gradients, and signed occlusion.  
Forbidden as primary: probability score, full-vocabulary score, generated-token
likelihood, argmax class alone.

---

## 2. RQ1 ranking semantics

RQ1 asks **where** influential evidence is located — not polarity.

| Method class | Primary rank transform |
|--------------|------------------------|
| Signed (grad, G×I, IG, occlusion) | `ABS_DESCENDING` (`rank_score = abs(signed_line_score)`) |
| Attention (nonnegative) | `RAW_DESCENDING` (no unnecessary abs) |

**Secondary sensitivity (signed methods only):** `SIGNED_POSITIVE_DESCENDING`  
— asks where evidence supports the buggy class. Must not replace ABS primary
after seeing results.

Tie-break (frozen): (1) rank_score DESC, (2) `ordered_position` ASC,
(3) `stable_line_id` ASC. IFA remains zero-based false-alarm count.

---

## 3. Line aggregation

- **Primary:** `SUM` (additive contribution / attention mass).
- **Sensitivity:** `MEAN` (average per-token importance — different question).
- `MAX_ABS_WITH_SIGN`: exploratory only; not a primary RQ metric.

Do not choose SUM vs MEAN based on RQ results later.

Occlusion lines already have a native region score (no token reduction).

---

## 4. Attention interpretation

Primary preset: **ATTENTION_LAST_MEAN_HEAD**  
(classification-query position; last layer; mean heads; SUM to lines).

Sensitivity: **ATTENTION_LAST4_MEAN**.

Language: attention is an **internal importance proxy / baseline**.  
Raw attention is **not** presumed faithful; faithfulness is tested in RQ2.  
Jain & Wallace (2019) and Wiegreffe & Pinter (2019) provide methodological
context — neither is framed as a universal final verdict.

---

## 5. Gradient methods

Vanilla gradient and Grad×Input against RISK_LOGIT_CONTRAST_V1 on input
embeddings; token score = sum over embedding dims; sign preserved (no abs in core).

---

## 6. Integrated Gradients

Compared method. Primary baseline: **ZERO_EMBEDDING**.  
Integration: **GAUSS_LEGENDRE**, initial steps **50**.  
Completeness: \(E_{\mathrm{abs}}=|\sum a - (s(x)-s(x'))|\),  
\(E_{\mathrm{rel}}=E_{\mathrm{abs}}/\max(|s(x)-s(x')|,10^{-6})\).

---

## 7. IG baseline sensitivity

Secondary baseline: **PAD_TOKEN_EMBEDDING**.

Frozen Qwen2.5-Coder-7B-Instruct (`c03e6d358207…`):

| Field | Value |
|-------|-------|
| pad string | `<\|endoftext\|>` |
| pad token ID | **151643** |
| special | yes |
| equals BOS ID | yes (151643) |
| equals primary EOS `<\|im_end\|>` | no (151645) |
| also in generation eos id list | yes |
| semantically neutral | **false** |

ZERO_EMBEDDING is reproducible, **not** assumed semantically neutral for
decoder LLMs (see Jacobian Scopes, arXiv:2601.16407 — not JIT-specific).  
If ZERO and PAD disagree substantially: report baseline dependence.  
Do **not** pick the better-looking baseline post hoc.

---

## 8. IG convergence

If \(E_{\mathrm{rel}}>0.05\) at 50 steps → retry **same** example at 100 steps.  
If still \(>0.05\): mark **IG_NONCONVERGED** (count/report; exclude only from
IG-required analyses; do not replace method). No increase beyond 100 without
orchestrator approval.

---

## 9. Occlusion intervention

\(\Delta_R = s(x) - s(x_{\setminus R})\). Positive supports buggy; negative
suppresses. No sign inversion.

Line removal: complete semantic segment (marker + payload), re-render/re-tokenize.  
Hunk: complete hunk. No token-ID zeroing.  
Empty hunk → remove; empty file with no hunks/changed lines → remove.  
Retain valid chat wrapper / FILE / HUNK structure where required.

---

## 10. Faithfulness score space

Primary: **LOGIT_CONTRAST**.  
Secondary: **RESTRICTED_BINARY_PROBABILITY** \(p_{\mathrm{buggy}}=\mathrm{softmax}([\ell_0,\ell_1])_1\).  
No full-vocabulary probability.

---

## 11. Comprehensiveness

\(\mathrm{COMP}(R)=s(x)-s(x\setminus R)\) (signed). Do not abs under this name.

---

## 12. Sufficiency

\(\mathrm{SUFF\_RAW}=s(x)-s(R_{\mathrm{only}})\) (closer to 0 ⇒ more sufficient).  
\(\mathrm{SUFF\_ERROR}=|\mathrm{SUFF\_RAW}|\) (higher is **not** better).

---

## 13. Polarity threshold

**RELATIVE_POLARITY_EPS_V1** (per commit × method × granularity):

\[
M=\max|\mathrm{score}|,\quad
\epsilon=\max(10^{-8},\,10^{-6}M)
\]

If \(M=0\): all **NEAR_ZERO**. Else POSITIVE / NEGATIVE / NEAR_ZERO as usual.  
Apply independently to attribution and occlusion. Sign agreement excludes pairs
with NEAR_ZERO on either side; report coverage.

---

## 14. RQ1 populations

Complete-case \(N=413\).  
Primary fully visible CHANGED_ONLY/2048: **\(N=304\)**.  
Ablation 4096: **\(N=345\)**.  
Do not silently score truncated partial universes as primary.

---

## 15. Random controls

RQ1 random baseline: **100** deterministic permutations per commit  
(seeds derived from commit id + repeat index).  
RQ2: length/candidate-count matched; seeds independent of training RNG.  
No result-dependent rerolling.

---

## 16. Seed handling

Attribution deterministic given checkpoint×commit×method (unless method is
stochastic by design).  
Explain **all three** M1 seeds {13,42,73}; aggregate across seeds.  
Never select a seed by test performance.

---

## 17. Predeclared sensitivities

- SIGNED_POSITIVE_DESCENDING RQ1 ranking  
- MEAN line reduction  
- ATTENTION_LAST4_MEAN  
- PAD IG baseline  
- probability-space faithfulness  
- 4096 representation ablation  
- hunk occlusion ablation  

---

## 18. Prohibited post-hoc choices

Choosing ranking / IG baseline / attention preset / 2048 vs 4096 / seed by
observed localization or faithfulness results; abs-ing comprehensiveness under
the same name; inverting occlusion sign; scoring partial truncated universes as
primary RQ1; binding intermediate seed-13 checkpoints as final adapters.

Execution order (attention → grad → G×I → occlusion → IG) is **scheduling
only** and must not influence which methods are reported.

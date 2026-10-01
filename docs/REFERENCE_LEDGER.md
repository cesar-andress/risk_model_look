# REFERENCE_LEDGER.md

Ledger only — **not** a bibliography and **not** `refs.bib`.

Cutoff for this verification pass: **2026-09-29**.

Status vocabulary:

- `VERIFIED_PRIMARY_SOURCE` — full text or equivalent primary extract inspected
- `VERIFIED_PUBLISHER` — official publisher/conference metadata inspected
- `VERIFIED_PREPRINT` — arXiv/Zenodo preprint inspected
- `METADATA_PARTIAL` — some fields still incomplete
- `FULL_TEXT_UNAVAILABLE` — could not obtain full text this audit
- `CLAIM_SUPPORT_UNVERIFIED` — existence OK; claim support not checked
- `DOI_NEEDS_CHECK` — DOI still uncertain
- `PRIMARY_SOURCE_REVIEW_NEEDED` — needs deeper claim-support reading

Do **not** invent missing author lists or DOIs.

---

## Core plan entries R1–R15

### R1

- Authors (verified from arXiv/OpenReview): Yalin Liu, Kosay Jabre, Rui Abreu, et al. (full list on arXiv HTML)
- Title: A Preliminary Study on Explaining Risk of Code Changes using LLM-Based Prediction Models
- Venue: AIware ’26 (ACM)
- DOI: 10.1145/3805760.3814916 (**verified** Crossref + arXiv related DOI)
- arXiv: 2607.02782 (v1 checked 2026-07-02 stamp on abs page)
- Status: VERIFIED_PRIMARY_SOURCE; VERIFIED_PUBLISHER

### R2

- Authors (plan): Abreu et al. — Crossref confirms ICSE-SEIP 2025 paper under this DOI
- Title: Moving Faster and Reducing Risk: Using LLMs in Release Deployment
- Venue: ICSE-SEIP 2025
- DOI: 10.1109/ICSE-SEIP66354.2025.00045
- Status: VERIFIED_PUBLISHER; PRIMARY_SOURCE_REVIEW_NEEDED (full SEIP text not re-read this pass beyond R1 citations)

### R3

- Authors: Sayedsalehi, Rigby, Mockus (as on arXiv)
- Title on arXiv HTML: DRS-OSS: Practical Diff Risk Scoring with LLMs (orchestrator also used longer tooling-oriented title variant — treat arXiv title as canonical until publisher version)
- arXiv: 2511.21964
- Status: VERIFIED_PRIMARY_SOURCE; METADATA_PARTIAL (final venue TBD)

### R4

- Authors: Monteiro, Cabral, Oliveira (as on arXiv)
- Title: CodeFlowLM: Incremental Just-In-Time Defect Prediction with Pretrained Language Models and Exploratory Insights into Defect Localization
- arXiv: 2512.00231
- Status: VERIFIED_PRIMARY_SOURCE; METADATA_PARTIAL

### R5

- Authors: Nam et al. (as in plan; full list PRIMARY_SOURCE_REVIEW_NEEDED)
- Title: ReDef: Do Code Language Models Truly Understand Code Changes for JIT-SDP?
- arXiv: 2509.09192
- Status: VERIFIED_PREPRINT (abs/metadata); PRIMARY_SOURCE_REVIEW_NEEDED for claim support

### R6

- Authors: Chao Ni, Wei Wang, Kaiwen Yang, Xin Xia, Kui Liu, David Lo
- Title: The best of both worlds: integrating semantic features with expert features for defect prediction and localization
- Venue: ESEC/FSE 2022, pages 672–683
- DOI: **10.1145/3540250.3549165** (verified Crossref works API + ACM DOI landing; author PDF https://kui-liu.github.io/papers/2022-ni-best.pdf inspected for dataset construction)
- Replication: `jacknichao/JIT-Fine` @ `584799fdec6095ab75a45fd2a5f8db5b12163aa5` (AUTHORITATIVE; Chao Ni)
- Status: VERIFIED_PUBLISHER; VERIFIED_PRIMARY_SOURCE (dataset provenance pass 2026-09-29). `refs.bib` not updated in this task.

### R7

- Title: JIT-Smart: A Multi-task Learning Framework for Just-in-Time Defect Prediction and Localization
- Venue: Proc. ACM Softw. Eng. (FSE) 2024
- DOI: 10.1145/3643727 (**verified** as ACM DOI form used by publisher)
- Authors: Xiangping Chen, Furen Xu, Yuan Huang, Neng Zhang, Zibin Zheng (from citing records; confirm on ACM page before bib insert)
- Status: VERIFIED_PUBLISHER; METADATA_PARTIAL; PRIMARY_SOURCE_REVIEW_NEEDED

### R8

- Authors: Pornprasit, Tantithamthavorn
- Title: JITLine (MSR 2021)
- arXiv: 2103.07068
- Status: VERIFIED_PREPRINT; PRIMARY_SOURCE_REVIEW_NEEDED for metric definitions

### R9

- Authors: Keshavarz, Nagappan
- Title: ApacheJIT
- Venue: MSR ’22
- DOI: 10.1145/3524842.3527996
- Status: VERIFIED_PUBLISHER; PRIMARY_SOURCE_REVIEW_NEEDED

### R10

- Authors: Lin et al.
- Title: CCT5
- Venue: ESEC/FSE 2023
- arXiv: 2305.10785
- Status: VERIFIED_PREPRINT; PRIMARY_SOURCE_REVIEW_NEEDED

### R11

- Authors: Marco Pintore, Giorgio Piras, Angelo Sotgiu, Maura Pintor, Battista Biggio
- Title: Evaluating line-level localization ability of learning-based code vulnerability detection models
- Venue: Machine Learning (Springer), 2026
- DOI: 10.1007/s10994-025-06902-1
- arXiv: 2510.11202
- Status: VERIFIED_PRIMARY_SOURCE; VERIFIED_PUBLISHER

### R12

- Title (plan): Grad-ELLM / Faithfulness Evaluation for Decoder-only LLM Attributions
- arXiv: 2601.03089
- Status: VERIFIED_PREPRINT; METADATA_PARTIAL (canonical title/authors to confirm on abs page before bib); CLAIM_SUPPORT_UNVERIFIED beyond relevance skim

### R13

- Title: Jacobian Scopes: token-level causal attributions in LLMs
- arXiv: 2601.16407
- Status: VERIFIED_PRIMARY_SOURCE
- **Integrity check (project IG-baseline note):** PARTIAL SUPPORT. Paper argues Integrated Gradients with a **null/zero baseline** introduces severe distortions in LLMs, notably **attention-sink** effects at low interpolation α, harming attribution quality/AOPC versus non-integrated Semantic Scope. This is **not** a JIT defect-prediction result; do not over-claim domain transfer.

### R14

- Authors: Jain, Wallace
- Title: Attention is not Explanation
- Venue: NAACL 2019
- arXiv: 1902.10186
- Status: VERIFIED_PREPRINT / established venue record; PRIMARY_SOURCE_REVIEW_NEEDED only if quoted precisely

### R15

- Title: Pre-trained Code Language Models for JIT-SDP: An Empirical Study
- Venue/publisher: Springer chapter, 2026
- DOI: 10.1007/978-3-032-15984-7_24
- Status: VERIFIED_PUBLISHER (DOI resolves); METADATA_PARTIAL; PRIMARY_SOURCE_REVIEW_NEEDED

---

## Newly required positioning sources (must-cite candidates)

### N1 — XMENTOR (C2)

- Authors: Saumendu Roy, Banani Roy, Chanchal Roy, Richard Bassey
- Title: XMENTOR: A Rank-Aware Aggregation Approach for Human-Centered Explainable AI in Just-in-Time Software Defect Prediction
- Venue: FORGE 2026
- DOI: 10.1145/3793655.3793736
- arXiv: 2602.22403 (v2 checked)
- Status: VERIFIED_PRIMARY_SOURCE; VERIFIED_PUBLISHER

### N2 — EASE 2026 transformer fidelity (C3)

- Authors: Saumendu Roy, Banani Roy, Chanchal K. Roy
- Title: How Faithful Are Post-hoc Explanations for Transformer-Based Software Models?
- Venue: EASE 2026
- Stable URLs: conference page; Zenodo replication 10.5281/zenodo.18358654
- ACM/IEEE DOI: UNKNOWN in this audit (conference paper; use conference+Zenodo until DOI minted/found)
- Status: VERIFIED_PUBLISHER; VERIFIED_PREPRINT (replication package inspected)

### N3 — CoScoreX ICSME 2026 RF study (C10) — DISTINCT from N2

- Title: CoScoreX: A Contextual and Contrastive Framework for Stable Post-hoc Explanations in Software Defect Prediction
- Venue: ICSME 2026
- Zenodo: 10.5281/zenodo.18899184
- Status: VERIFIED_PUBLISHER; METADATA_PARTIAL
- Note: Do **not** merge with N2.

### N4 — JITEC (C4)

- Authors: Yu Zhao, Xinyu Yuan, Lina Gong, Zhiqiu Huang
- Title: Enhance Expert-Semantic Feature Extraction and Combine Feature Importance and Attention Scores for Just-in-Time Defect Prediction and Localization
- Venue: Journal of Software: Evolution and Process, 2026
- DOI: 10.1002/smr.70118
- Status: VERIFIED_PUBLISHER; FULL_TEXT_UNAVAILABLE this audit (Wiley HTML timeout)

### N5 — JIT-LSM (C5)

- Authors: Yuan Huang, Mingxuan Chen, Xiangping Chen, Yi Liu
- Title: Towards integrating large model with small model for Just-in-Time Defect Prediction and Localization
- Venue: Information and Software Technology, 2026
- DOI: 10.1016/j.infsof.2026.108244
- Status: VERIFIED_PUBLISHER; FULL_TEXT_UNAVAILABLE this audit (ScienceDirect blocked/timeout); institutional abstract used

### N6 — FoX (C6)

- Authors: Jinqiang Yu, Michael Fu, Alexey Ignatiev, Chakkrit Tantithamthavorn, Peter Stuckey
- Title: A Formal Explainer for Just-In-Time Defect Predictions
- Venue: ACM TOSEM 33(7), 2024
- DOI: 10.1145/3664809
- Status: VERIFIED_PRIMARY_SOURCE; VERIFIED_PUBLISHER

### N7 — CfExplainer (C7)

- Authors: Fengyu Yang, Guangdong Zeng, Fa Zhong, Peng Xiao, Wei Zheng, Fuxing Qiu
- Title: CfExplainer: Explainable just-in-time defect prediction based on counterfactuals
- Venue: Journal of Systems and Software, 2024
- DOI: 10.1016/j.jss.2024.112182
- Status: VERIFIED_PUBLISHER; FULL_TEXT_UNAVAILABLE (publisher block); GitHub method page inspected → METADATA_PARTIAL

### R16 — JIT-Block (methodological prior / reconstruction evidence)

- Authors: Teng Huang, Hui-Qun Yu, Gui-Sheng Fan, Zi-Jie Huang, Chen-Yu Wu
- Title: A code change-oriented approach to just-in-time defect prediction with multiple input semantic fusion
- Venue: Expert Systems, 41(12), 2024
- DOI: **10.1111/exsy.13702** (verified publisher indexing + author PDF)
- Repository: https://github.com/hangters/JIT-Block @ `d82cc67f1c696644e9d6d5c80621937aaf36710b`
- Status: VERIFIED_PUBLISHER; VERIFIED_PRIMARY_SOURCE (author PDF + frozen repo artifacts audited 2026-10-01)
- Notes: Used as external reconstruction / label-universe evidence only; does not replace frozen JIT-Fine train/valid/test split. License NONE_FOUND on GitHub.

---

No entries were inserted into `paper/refs.bib` in this task.

---

## Attribution protocol freeze references (2026-10-01)

### R17 — Integrated Gradients (Sundararajan et al.)

- Authors: Mukund Sundararajan, Ankur Taly, Qiqi Yan
- Title: Axiomatic Attribution for Deep Networks
- Venue: ICML 2017 (PMLR 70:3319–3328)
- arXiv: 1703.01365
- Status: VERIFIED_PUBLISHER (PMLR); VERIFIED_PREPRINT (arXiv abs)
- Role: IG method definition / completeness axiom

### R14 (updated) — Jain & Wallace 2019

- Authors: Sarthak Jain, Byron C. Wallace
- Title: Attention is not Explanation
- Venue: NAACL 2019
- DOI: **10.18653/v1/N19-1357** (ACL Anthology verified)
- arXiv: 1902.10186
- Status: VERIFIED_PUBLISHER; VERIFIED_PREPRINT
- Role: methodological context — attention not presumed faithful; not a universal verdict

### R18 — Wiegreffe & Pinter 2019

- Authors: Sarah Wiegreffe, Yuval Pinter
- Title: Attention is not not Explanation
- Venue: EMNLP-IJCNLP 2019
- DOI: **10.18653/v1/D19-1002** (ACL Anthology verified)
- arXiv: 1908.04626
- Status: VERIFIED_PUBLISHER; VERIFIED_PREPRINT
- Role: methodological counterpoint to R14; not a universal verdict

### R19 — ERASER (DeYoung et al. 2020)

- Authors: Jay DeYoung, Sarthak Jain, Nazneen Fatema Rajani, Eric Lehman, Caiming Xiong, Richard Socher, Byron C. Wallace
- Title: ERASER: A Benchmark to Evaluate Rationalized NLP Models
- Venue: ACL 2020
- DOI: **10.18653/v1/2020.acl-main.408** (ACL Anthology verified)
- Status: VERIFIED_PUBLISHER
- Role: localization/plausibility vs faithfulness distinction; comprehensiveness/sufficiency vocabulary

### N8 — Liang et al. IST 2026 (PTM/fusion revisit)

- Authors: Yuguo Liang, Guisheng Fan, Huiqun Yu, Wentao Chen, Chengcheng Wu, Zijie Huang
- Title: Revisiting pre-trained models and feature fusion strategies for just-in-time defect prediction
- Venue: Information and Software Technology, 2026, volume 197, article/page 108170
- DOI: **10.1016/j.infsof.2026.108170** (verified Crossref 2026-10-01)
- Status: VERIFIED_PUBLISHER; FULL_TEXT_UNAVAILABLE / abstract empty in OpenAlex this audit
- Role: 2026 JIT landscape (PTM + feature fusion); not a novelty collision

### Refresh note (2026-10-01)

SOTA refresh for manuscript Related Work: see `paper/docs/SOTA_REFRESH_REPORT.md`.
Prior collision conclusion retained (no direct conjunction collision).
JITEC faithfulness/polarity cells remain UNCLEAR (abstract-only for those absences).

# REPRODUCIBILITY.md

Replication notes for **risk_model_look** (pre-results).  
This document does **not** claim that final TEST attribution or M1 final metrics are complete.

---

## 1. Environment

1. Create conda/mamba env from `environment.yml`, **or** follow `docs/ENVIRONMENT_REPORT.md` for `uv`/venv fallback.
2. Activate the environment.
3. Sanity: `pytest -q` (CPU tests; do not require GPU for protocol/unit suites).

Do not commit `.venv/` or Hugging Face caches.

---

## 2. Dataset acquisition

1. Read `data/raw/README.md` and provenance docs under `docs/`.
2. Run the documented acquisition scripts (see `docs/DATA_ACQUISITION_PLAN.md` / acquisition artifacts).
3. Verify archive digests against recorded SHA files under `artifacts/data_acquisition/`.
4. **Do not assume redistribution rights** for raw JIT-Defects4J content in a public dump.

Processed canonical JSONL and encoded caches are local build products (gitignored).

---

## 3. Hash / protocol verification

After attribution infra is on `main`:

- Attribution protocol current: **V1.2**  
  hash `c6496a67445f72fd93fcab6641a69483f2b85283a9b1582158d780ca9c3ee62c`
- Statistical protocol current: **V1.1**  
  hash `edbe4dcaf02e64f339c698315fb0f502b379a4a7403c57f3111944c31c7e11a8`
- Freeze bundle: `624eb6cedccc7c4c9bcf12903b6e671ae14d22bc7ae8a7895cb39c13759a32bb`  
  tag `pre-attribution-protocol-v1.2`

Confirm via `artifacts/attribution_protocol/` and `artifacts/protocol_freeze_bundle/`.

---

## 4. Training

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct` at pinned revision (see training configs / study design).
- Entry points: pilot scripts historically; **M1 final** entrypoints may exist as local WIP during training (`scripts/run_m1_final.py`) — treat as incomplete until committed on `main`.
- Seeds: `{13, 42, 73}` (protocol).
- **Do not publish adapter weights** by default.

---

## 5. Evaluation / attribution

1. Complete **validation attribution rehearsal** (N=64) before TEST attribution.
2. Run attribution under frozen V1.2 configs.
3. Aggregate with Stats V1.1 utilities.
4. Fill paper TBD macros only from frozen artifacts.

GPU evaluation is out of scope for this hygiene document.

---

## 6. Paper build

Manuscript currently lives at sibling `../paper/` (papers monorepo). After optional integration, build from `paper/`:

```bash
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Draft mode allows TBD macros; submission completeness checks must fail while TBD remain.

---

## 7. Limitations (current)

- Pre-results: empirical RQ tables are placeholders.
- Code `main` and attribution branch not yet fast-forwarded.
- Dataset license/redistribution: verify before any public dump.
- External protocol timestamp: PENDING (not claimed as preregistration).

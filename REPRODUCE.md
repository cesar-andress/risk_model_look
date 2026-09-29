# REPRODUCE.md

How to reproduce the **bootstrap / environment** layer of this project.

Scientific experiment reproduction (dataset build, training, attribution, metrics) is **not** available yet. Do not invent missing steps.

## Prerequisites

- Linux host with NVIDIA GPU (target: RTX 4090 class)
- Compatible NVIDIA driver
- Either:
  - `conda` / `mamba`, **or**
  - `uv` + Python 3.11 (fallback used when conda/mamba are absent; see `docs/ENVIRONMENT_REPORT.md`)
- Network access to Hugging Face Hub for `Qwen/Qwen2.5-Coder-7B-Instruct`
- Optional: `HF_TOKEN` environment variable if the Hub requires authentication (never commit the token)

## Environment creation

### Preferred: conda/mamba

```bash
conda env create -f environment.yml
conda activate risk_model_look
```

### Fallback: uv + venv (used on the bootstrap machine)

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements-bootstrap.txt
# PyTorch CUDA wheel index as recorded in docs/ENVIRONMENT_REPORT.md
```

Exact package versions that actually installed are recorded in `docs/ENVIRONMENT_REPORT.md` after bootstrap.

## Plumbing checks

From the repository root:

```bash
pytest -q
```

Expected: bootstrap structure and import tests pass. GPU absence must not fail the default suite.

## GPU smoke test (required for ENVIRONMENT_GATE)

```bash
python scripts/smoke_qwen_4bit.py
```

This loads `Qwen/Qwen2.5-Coder-7B-Instruct` in 4-bit NF4 and runs one tiny forward pass. It is **not** a scientific prediction.

Logs may be written under `artifacts/bootstrap/`.

## What is intentionally missing

- JIT-Defects4J download / schema verification
- Token–line mapping implementation
- Training / attribution / metrics code
- Result tables for RQs

See `STATUS.md` for gate status.

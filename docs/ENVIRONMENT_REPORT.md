# ENVIRONMENT_REPORT.md

Machine-observed environment at bootstrap. No secrets recorded.

## Timestamp

2026-09-29T21:24:18+00:00 (UTC)

## Platform

- OS: Linux-6.8.0-138-generic-x86_64-with-glibc2.35
- Host path for code root: `/home/cesar/papers/risk_model_look/risk_model_look`

## GPU / driver

- GPU: NVIDIA GeForce RTX 4090
- VRAM: 24564 MiB (~23.51 GiB; `torch` reported 25243287552 bytes)
- NVIDIA driver: 595.91.07
- `nvidia-smi` reported CUDA Version: 13.2 (driver capability string)
- System `nvcc` (toolkit on PATH): release 11.5 (not used for the PyTorch wheel install)
- PyTorch CUDA build used: 12.4 (`torch==2.6.0+cu124`)
- `torch.cuda.get_device_capability(0)`: (8, 9)

## Python tooling

- Default `python3` on PATH at inspection: `/usr/local/bin/python3` → 3.6.15 (unsuitable; `python3 -m pip` segfaulted)
- Available system interpreters: 3.10 / 3.11 / 3.12 under `/usr/bin`
- conda: **not found**
- mamba: **not found**
- uv: 0.11.16 (`/home/cesar/.local/bin/uv`)
- Working environment: `.venv` via `uv venv --python 3.11` (Python 3.11.15)

## Installed stack (working `.venv`)

| Package | Version |
|---------|---------|
| torch | 2.6.0+cu124 |
| transformers | 4.50.3 |
| bitsandbytes | 0.45.5 |
| captum | 0.7.0 |
| peft | 0.14.0 |
| accelerate | 1.2.1 |
| datasets | 3.1.0 |
| numpy | 2.2.6 |
| pandas | 2.2.3 |
| scipy | 1.15.3 |
| scikit-learn | 1.6.1 |

Torch CUDA available: **True** (`NVIDIA GeForce RTX 4090`).

`environment.yml` is the conda/mamba-oriented declaration. Exact bootstrap install used `uv` + `requirements-bootstrap.txt` + PyTorch cu124 wheel index because conda/mamba were absent.

## Hugging Face

- `HF_HOME` / `TRANSFORMERS_CACHE`: unset (default `~/.cache/huggingface`)
- Model download for smoke: `Qwen/Qwen2.5-Coder-7B-Instruct` (cached outside the git tree)
- Credential: `HF_TOKEN` environment variable **name** present; value never written to this repository

## Smoke test outcome (recorded)

- Script: `scripts/smoke_qwen_4bit.py`
- Result: **PASS**
- Quantization: 4-bit NF4 (`is_loaded_in_4bit=True`, `Bnb4BitHfQuantizer`)
- Peak allocated VRAM: **5.471 GiB**
- Log: `artifacts/bootstrap/smoke_qwen_4bit_20260929T212040Z.json`

## pytest

- Command: `pytest -q`
- Result: **PASS** (bootstrap structure + import tests)

## LaTeX (paper root; non-blocking)

- Engines available: `pdflatex`, `latexmk`, `lualatex`, `xelatex`
- Scaffold compile: `latexmk -pdf` on `../paper/main.tex` → success (empty bibliography warning expected)

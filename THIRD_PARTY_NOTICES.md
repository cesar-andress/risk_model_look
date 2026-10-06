# Third-party notices

This repository’s MIT license covers **author-owned software and documentation**
in this package (see `LICENSE` and the Licensing section of `README.md`).
It does **not** relicense the following upstream materials.

## Datasets

| Resource | Role | Redistribution in this repo | License / terms |
|----------|------|-----------------------------|-----------------|
| JIT-Defects4J / JIT-Fine | Public JIT line-labelled resource used by the study | Raw dumps **not** redistributed (`data/raw/**` gitignored except placeholders/README) | Upstream distributor terms (obtain separately) |

## Models

| Resource | Role | Redistribution in this repo | License / terms |
|----------|------|-----------------------------|-----------------|
| Qwen2.5-Coder-7B-Instruct (pinned revision) | Base decoder for the studied classifier | Base weights **not** shipped | Upstream Hugging Face / Alibaba model license |
| Author LoRA adapters | Fine-tuned adapters from this study | `.safetensors` **not** tracked / not in planned Zenodo payload by default | Author-owned; distribution not part of the default MIT code deposit |

## Software dependencies

Python packages listed in `environment.yml` / bootstrap requirements are
third-party and remain under their respective licenses. Installing them does
not place those packages under MIT.

## Manuscript

The EMSE manuscript LaTeX/PDF lives in a **private sibling** tree
(`../paper/`) and is **not** part of this software repository’s MIT grant.
Publication reuse follows the authors and journal, not this LICENSE file.

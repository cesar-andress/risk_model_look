"""Bootstrap: required Python packages import (CPU-safe)."""

from __future__ import annotations

import importlib
import pytest


REQUIRED_MODULES = [
    "numpy",
    "scipy",
    "pandas",
    "pyarrow",
    "sklearn",
    "yaml",
    "tqdm",
    "torch",
    "transformers",
    "tokenizers",
    "datasets",
    "accelerate",
    "peft",
    "bitsandbytes",
    "captum",
]


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_required_package_imports(module_name: str) -> None:
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_torch_import_does_not_require_cuda() -> None:
    import torch

    # Availability is informational; absence must not fail this suite.
    _ = torch.cuda.is_available()
    assert hasattr(torch, "tensor")

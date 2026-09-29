#!/usr/bin/env python3
"""Technical smoke test: load Qwen2.5-Coder-7B-Instruct in 4-bit NF4 and run one forward pass.

This is NOT a scientific prediction. Exit non-zero on failure.
Do not substitute a different model on failure.
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
PROMPT = """[MSG] fix null check
[FILE] Example.java
[HUNK 1]
[DEL] return obj.value;
[ADD] return obj == null ? null : obj.value;
"""

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "artifacts" / "bootstrap"


def _bytes_to_gib(n: int) -> float:
    return n / (1024**3)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOG_DIR / f"smoke_qwen_4bit_{stamp}.json"
    report: dict = {
        "timestamp_utc": stamp,
        "model_id": MODEL_ID,
        "status": "FAIL",
        "error": None,
    }

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        cuda_ok = bool(torch.cuda.is_available())
        report["cuda_available"] = cuda_ok
        if not cuda_ok:
            raise RuntimeError("CUDA is not available; cannot run 4-bit GPU smoke test.")

        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        total_vram = int(props.total_memory)
        report["gpu_name"] = gpu_name
        report["total_vram_bytes"] = total_vram
        report["total_vram_gib"] = round(_bytes_to_gib(total_vram), 3)
        print(f"GPU: {gpu_name}")
        print(f"Total VRAM: {report['total_vram_gib']:.3f} GiB")

        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()

        print(f"Loading tokenizer: {MODEL_ID}")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        print(f"Loading model in 4-bit NF4: {MODEL_ID}")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model.eval()

        # Quantization / dtype probes
        quant_flag = bool(getattr(model, "is_loaded_in_4bit", False))
        # Some transformers versions expose quantization via hf_quantizer
        hf_quant = getattr(model, "hf_quantizer", None)
        report["is_loaded_in_4bit"] = quant_flag
        report["hf_quantizer"] = type(hf_quant).__name__ if hf_quant is not None else None

        dtypes = sorted({str(p.dtype) for p in model.parameters()})
        report["parameter_dtypes"] = dtypes
        print(f"Parameter dtypes: {dtypes}")
        print(f"is_loaded_in_4bit: {quant_flag}")
        print(f"hf_quantizer: {report['hf_quantizer']}")

        if not quant_flag and hf_quant is None:
            raise RuntimeError(
                "Model does not report 4-bit quantization state "
                "(is_loaded_in_4bit=False and no hf_quantizer)."
            )

        inputs = tokenizer(PROMPT, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = model(**inputs)
            logits = outputs.logits

        if not torch.isfinite(logits).all():
            raise RuntimeError("Non-finite logits in smoke forward pass.")

        allocated = int(torch.cuda.memory_allocated())
        reserved = int(torch.cuda.memory_reserved())
        peak = int(torch.cuda.max_memory_allocated())
        report["allocated_vram_bytes"] = allocated
        report["reserved_vram_bytes"] = reserved
        report["peak_allocated_vram_bytes"] = peak
        report["allocated_vram_gib"] = round(_bytes_to_gib(allocated), 3)
        report["reserved_vram_gib"] = round(_bytes_to_gib(reserved), 3)
        report["peak_allocated_vram_gib"] = round(_bytes_to_gib(peak), 3)
        report["logits_shape"] = list(logits.shape)
        report["note"] = (
            "Technical smoke only. Logits/tokens are not scientific results."
        )
        report["status"] = "PASS"

        print(f"Logits shape: {tuple(logits.shape)} (finite=True)")
        print(f"Allocated VRAM: {report['allocated_vram_gib']:.3f} GiB")
        print(f"Reserved VRAM: {report['reserved_vram_gib']:.3f} GiB")
        print(f"Peak allocated VRAM: {report['peak_allocated_vram_gib']:.3f} GiB")
        print("SMOKE_RESULT=PASS")
        return 0

    except Exception as exc:  # noqa: BLE001 — surface exact blocker
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
        print(f"SMOKE_RESULT=FAIL", file=sys.stderr)
        print(report["error"], file=sys.stderr)
        print(report["traceback"], file=sys.stderr)
        return 1
    finally:
        log_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote log: {log_path}")


if __name__ == "__main__":
    raise SystemExit(main())

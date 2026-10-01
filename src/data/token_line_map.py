"""Exact Qwen token↔line mapping via offsets + structured span registry."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.data.build_dataset import render_record
from src.data.structured_diff import (
    PROMPT_TEMPLATE_VERSION,
    SYSTEM_INSTRUCTION,
    wrap_chat_plaintext,
)

TOKEN_MAP_VERSION = 1
QWEN_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
LLAMA_ID = "meta-llama/Llama-3.1-8B-Instruct"


@dataclass
class LabelTokenInfo:
    tokenizer_id: str
    token_id_0: int
    token_id_1: int
    single_token: bool
    eot_token_ids: list[int]


def load_tokenizer(model_id: str):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id, use_fast=True, trust_remote_code=True)
    if not tok.is_fast:
        raise RuntimeError(f"Fast tokenizer required for {model_id}")
    return tok


def verify_label_tokens(tok, model_id: str) -> LabelTokenInfo:
    """Verify '0' and '1' are single tokens at assistant generation start."""
    messages = wrap_chat_plaintext("PING")
    prompt = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    # Encode label candidates as if continuing generation
    ids0 = tok.encode("0", add_special_tokens=False)
    ids1 = tok.encode("1", add_special_tokens=False)
    # Also check with leading space variants some templates use
    ids0b = tok.encode("0", add_special_tokens=False)
    single = len(ids0) == 1 and len(ids1) == 1 and ids0[0] != ids1[0]
    eot = []
    for name in ("eos_token_id",):
        v = getattr(tok, name, None)
        if isinstance(v, int):
            eot.append(v)
    # Qwen im_end
    for s in ("<|im_end|>", "<|endoftext|>"):
        tid = tok.convert_tokens_to_ids(s)
        if isinstance(tid, int) and tid != tok.unk_token_id and tid not in eot:
            eot.append(tid)
    return LabelTokenInfo(
        tokenizer_id=model_id,
        token_id_0=ids0[0] if ids0 else -1,
        token_id_1=ids1[0] if ids1 else -1,
        single_token=single,
        eot_token_ids=eot,
    )


def build_chat_prompt(tok, structured_text: str) -> tuple[str, int]:
    """Return (full_prompt_text, structured_content_char_start_in_prompt)."""
    messages = wrap_chat_plaintext(structured_text)
    prompt = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    # Exact unique occurrence
    idx = prompt.find(structured_text)
    if idx < 0:
        raise RuntimeError("structured content not found verbatim in chat template")
    if prompt.find(structured_text, idx + 1) >= 0:
        raise RuntimeError("structured content not unique in chat template")
    return prompt, idx


def map_tokens_to_spans(
    tok,
    prompt: str,
    structured_offset: int,
    spans: list[Any],
    *,
    keep_token_rows: bool = True,
) -> dict[str, Any]:
    """Map tokenizer offsets to span registry (structured-relative)."""
    enc = tok(
        prompt,
        return_offsets_mapping=True,
        add_special_tokens=False,
        return_attention_mask=False,
    )
    input_ids = enc["input_ids"]
    offsets = enc["offset_mapping"]

    abs_spans = []
    for s in spans:
        d = s if isinstance(s, dict) else s.__dict__
        abs_spans.append(
            {
                "segment_type": d["segment_type"],
                "stable_line_id": d.get("stable_line_id"),
                "file_id": d.get("file_id"),
                "hunk_id": d.get("hunk_id"),
                "rq1_status": d.get("rq1_status"),
                "payload": d.get("payload"),
                "abs_start": structured_offset + d["char_start"],
                "abs_end": structured_offset + d["char_end"],
            }
        )

    code_payloads = [
        s
        for s in abs_spans
        if s.get("payload")
        and s.get("segment_type") in ("ADDED_CODE", "DELETED_CODE", "CONTEXT_CODE")
        and s.get("stable_line_id")
    ]
    struct_end = abs_spans[-1]["abs_end"] if abs_spans else structured_offset
    # Sorted by start for binary search (payloads disjoint & ordered in render)
    code_payloads.sort(key=lambda s: s["abs_start"])
    starts = [s["abs_start"] for s in code_payloads]

    import bisect

    def owners_for(a: int, b: int) -> set[int]:
        if not starts:
            return set()
        i = bisect.bisect_right(starts, a) - 1
        found: set[int] = set()
        if i < 0:
            i = 0
        while i < len(code_payloads) and code_payloads[i]["abs_start"] < b:
            s = code_payloads[i]
            if not (b <= s["abs_start"] or a >= s["abs_end"]):
                found.add(i)
            i += 1
            if len(found) > 1:
                break
        return found

    needed = []
    covered = []
    for s in code_payloads:
        payload = prompt[s["abs_start"] : s["abs_end"]]
        need = [i for i, ch in enumerate(payload) if not ch.isspace()]
        needed.append(need)
        covered.append(bytearray(len(payload)))

    token_rows = []
    errors = []
    cross_same = 0
    cross_line = 0
    cat_counts: dict[str, int] = {}

    def bump(cat: str) -> None:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    for ti, (tid, (a, b)) in enumerate(zip(input_ids, offsets)):
        if a == b:
            bump("SPECIAL_TOKEN")
            if keep_token_rows:
                token_rows.append(
                    {
                        "token_index": ti,
                        "token_id": tid,
                        "offset_start": a,
                        "offset_end": b,
                        "category": "SPECIAL_TOKEN",
                        "stable_line_id": None,
                    }
                )
            continue
        owners = owners_for(a, b)
        if len(owners) > 1:
            cross_line += 1
            errors.append({"type": "CROSS_LINE_TOKEN", "token_index": ti})
            bump("MAPPING_ERROR")
            if keep_token_rows:
                token_rows.append(
                    {
                        "token_index": ti,
                        "token_id": tid,
                        "offset_start": a,
                        "offset_end": b,
                        "category": "MAPPING_ERROR",
                        "stable_line_id": None,
                    }
                )
            continue
        if len(owners) == 1:
            pi = next(iter(owners))
            s = code_payloads[pi]
            # same-line marker overlap: token starts before payload
            if a < s["abs_start"] < b:
                cross_same += 1
            lo = max(a, s["abs_start"])
            hi = min(b, s["abs_end"])
            for c in range(lo, hi):
                covered[pi][c - s["abs_start"]] = 1
            cat = s["segment_type"]
            bump(cat)
            if keep_token_rows:
                token_rows.append(
                    {
                        "token_index": ti,
                        "token_id": tid,
                        "offset_start": a,
                        "offset_end": b,
                        "category": cat,
                        "stable_line_id": s["stable_line_id"],
                        "file_id": s.get("file_id"),
                        "hunk_id": s.get("hunk_id"),
                        "rq1_status": s.get("rq1_status"),
                    }
                )
            continue
        # Non-code: classify by first overlapping abs span
        cat = "SPECIAL_TOKEN" if a < structured_offset or a >= struct_end else "OTHER"
        for o in abs_spans:
            if b <= o["abs_start"] or a >= o["abs_end"]:
                continue
            st = o["segment_type"]
            if st == "COMMIT_MESSAGE":
                cat = "COMMIT_MESSAGE"
                break
            if st == "FILE_PATH":
                cat = "FILE_PATH"
                break
            if st == "HUNK_HEADER":
                cat = "HUNK_HEADER"
                break
            if st == "STRUCTURAL_MARKUP":
                cat = "STRUCTURAL_MARKUP"
                break
        bump(cat)
        if keep_token_rows:
            token_rows.append(
                {
                    "token_index": ti,
                    "token_id": tid,
                    "offset_start": a,
                    "offset_end": b,
                    "category": cat,
                    "stable_line_id": None,
                }
            )

    coverage_errors = 0
    for pi, need in enumerate(needed):
        if any(covered[pi][i] == 0 for i in need):
            coverage_errors += 1
            errors.append(
                {
                    "type": "LINE_COVERAGE",
                    "stable_line_id": code_payloads[pi]["stable_line_id"],
                }
            )

    return {
        "n_tokens": len(input_ids),
        "token_rows": token_rows,
        "category_counts": cat_counts,
        "errors": errors,
        "cross_boundary_same_line": cross_same,
        "cross_line_tokens": cross_line,
        "coverage_errors": coverage_errors,
        "ok": len(errors) == 0,
    }


def whole_segment_prefix_truncation(
    tok,
    prompt: str,
    structured_offset: int,
    spans: list[Any],
    max_length: int,
    reserve_completion: int = 2,
) -> dict[str, Any]:
    """WHOLE_SEGMENT_PREFIX_TRUNCATION_V1 — never cut mid code payload line."""
    budget = max_length - reserve_completion
    enc = tok(prompt, return_offsets_mapping=True, add_special_tokens=False)
    ids = enc["input_ids"]
    offsets = enc["offset_mapping"]
    if len(ids) <= budget:
        return {
            "truncated": False,
            "n_tokens_full": len(ids),
            "n_tokens_kept": len(ids),
            "cut_char": None,
            "dropped_line_ids": [],
        }
    # Find cut token
    cut_tok = budget
    cut_char = offsets[cut_tok - 1][1] if cut_tok > 0 else 0
    # If cut inside a code payload, drop that payload and everything after in structured region
    abs_payloads = []
    for s in spans:
        d = s if isinstance(s, dict) else s.__dict__
        if d.get("payload") and d.get("stable_line_id") and d.get("segment_type") in (
            "ADDED_CODE",
            "DELETED_CODE",
            "CONTEXT_CODE",
        ):
            abs_payloads.append(
                {
                    "stable_line_id": d["stable_line_id"],
                    "abs_start": structured_offset + d["char_start"],
                    "abs_end": structured_offset + d["char_end"],
                }
            )
    drop_from = None
    dropped = []
    for p in abs_payloads:
        if p["abs_start"] < cut_char <= p["abs_end"]:
            drop_from = p["abs_start"]
            break
    if drop_from is None:
        # cut between segments — keep tokens fully before cut_char
        drop_from = cut_char
    for p in abs_payloads:
        if p["abs_start"] >= drop_from:
            dropped.append(p["stable_line_id"])
    # Keep tokens whose offset_end <= drop_from, plus template tokens before structured
    kept_ids = []
    for tid, (a, b) in zip(ids, offsets):
        if b <= drop_from or (a == b and a < drop_from):
            kept_ids.append(tid)
        elif a >= drop_from:
            break
        else:
            # token crosses drop_from — drop it and rest
            break
    # Ensure we don't exceed budget
    kept_ids = kept_ids[:budget]
    return {
        "truncated": True,
        "n_tokens_full": len(ids),
        "n_tokens_kept": len(kept_ids),
        "cut_char": drop_from,
        "dropped_line_ids": dropped,
    }


def config_cache_key(cfg: dict[str, Any]) -> str:
    blob = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]

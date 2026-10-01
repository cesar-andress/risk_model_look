"""M1 dataset utilities: sampling, prompt build, leakage checks (train/valid only)."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Iterator

from src.data.build_dataset import render_record
from src.data.structured_diff import wrap_chat_plaintext
from src.data.token_line_map import whole_segment_prefix_truncation
from src.models.qwen_m1 import FORBIDDEN_METADATA_MARKERS

SPLIT_ALLOW = frozenset({"train", "valid"})


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_split_records(processed_dir: Path, split: str) -> list[dict[str, Any]]:
    if split not in SPLIT_ALLOW and split != "train":
        # Explicit: never load test through this helper for scoring paths.
        if split == "test":
            raise RuntimeError("TEST SPLIT LOAD BLOCKED in m1_dataset scoring helpers")
    path = processed_dir / f"{split}.jsonl"
    return list(iter_jsonl(path))


def load_train_records(processed_dir: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(processed_dir / "train.jsonl"))


def load_valid_records(processed_dir: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(processed_dir / "valid.jsonl"))


def commit_label_int(rec: dict[str, Any]) -> int:
    return int(float(rec["commit_label"]))


def build_chat_prompt_text(tokenizer, structured_text: str) -> str:
    messages = wrap_chat_plaintext(structured_text)
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def render_and_truncate_prompt(
    tokenizer,
    rec: dict[str, Any],
    *,
    max_length: int = 2048,
) -> tuple[str, dict[str, Any]]:
    """Render structured record → chat prompt, truncated for 1 label token."""
    rendered = render_record(rec)
    # Leakage audit on structured body (before chat wrap)
    leak = audit_structured_leakage(rendered.text)
    if leak["leaked"]:
        raise RuntimeError(f"metadata leakage in render: {leak['hits']}")
    prompt = build_chat_prompt_text(tokenizer, rendered.text)
    # Reserve 1 token for classification target
    budget = max_length - 1
    tr = whole_segment_prefix_truncation(
        tokenizer,
        prompt,
        # structured offset unused for cut logic when spans from render;
        # re-find structured content start
        prompt.find(rendered.text) if rendered.text in prompt else 0,
        [
            {
                "char_start": s.char_start,
                "char_end": s.char_end,
                "segment_type": s.segment_type,
                "stable_line_id": s.stable_line_id,
                "payload": s.payload,
            }
            for s in rendered.spans
        ],
        max_length=budget,
        reserve_completion=0,
    )
    if tr["truncated"]:
        # Rebuild prompt by keeping tokens — simpler: re-tokenize and decode prefix
        enc = tokenizer(prompt, add_special_tokens=False, return_offsets_mapping=True)
        ids = enc["input_ids"][: tr["n_tokens_kept"]]
        prompt = tokenizer.decode(ids, skip_special_tokens=False)
    return prompt, tr


def audit_structured_leakage(structured_text: str) -> dict[str, Any]:
    """Detect forbidden metadata markers in rendered structured content."""
    hits = [m for m in FORBIDDEN_METADATA_MARKERS if m in structured_text]
    return {"leaked": bool(hits), "hits": hits}


def sample_stage_a(
    train_records: list[dict[str, Any]],
    *,
    seed: int = 42,
    n_pos: int = 16,
    n_neg: int = 16,
) -> list[dict[str, Any]]:
    """Deterministic balanced Stage-A sample from TRAIN only."""
    rng = random.Random(seed)
    pos = [r for r in train_records if commit_label_int(r) == 1]
    neg = [r for r in train_records if commit_label_int(r) == 0]
    pos.sort(key=lambda r: r["commit_id"])
    neg.sort(key=lambda r: r["commit_id"])
    rng.shuffle(pos)
    rng.shuffle(neg)
    out = pos[:n_pos] + neg[:n_neg]
    if len(out) != n_pos + n_neg:
        raise RuntimeError("Stage A sample incomplete")
    ids = [r["commit_id"] for r in out]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate commit in Stage A")
    out.sort(key=lambda r: r["commit_id"])
    return out


def sample_stage_b(
    train_records: list[dict[str, Any]],
    *,
    seed: int = 42,
    n: int = 2048,
) -> list[dict[str, Any]]:
    """Deterministic stratified natural-prevalence Stage-B sample from TRAIN."""
    rng = random.Random(seed + 1)  # distinct stream from Stage A
    pos = [r for r in train_records if commit_label_int(r) == 1]
    neg = [r for r in train_records if commit_label_int(r) == 0]
    pos.sort(key=lambda r: r["commit_id"])
    neg.sort(key=lambda r: r["commit_id"])
    # Target ~ natural prevalence 1390/16374
    prev = len(pos) / max(len(train_records), 1)
    n_pos = int(round(n * prev))
    n_pos = max(1, min(n_pos, len(pos), n - 1))
    n_neg = n - n_pos
    if n_neg > len(neg):
        n_neg = len(neg)
        n_pos = n - n_neg
    rng.shuffle(pos)
    rng.shuffle(neg)
    out = pos[:n_pos] + neg[:n_neg]
    if len(out) != n:
        raise RuntimeError(f"Stage B size {len(out)} != {n}")
    ids = [r["commit_id"] for r in out]
    if len(set(ids)) != len(ids):
        raise RuntimeError("duplicate commit in Stage B")
    # Prefer project coverage: if missing projects, swap in from remainder
    have = {r["project"] for r in out}
    all_proj = {r["project"] for r in train_records}
    missing = sorted(all_proj - have)
    pool = [r for r in pos[n_pos:] + neg[n_neg:] if r["commit_id"] not in set(ids)]
    pool.sort(key=lambda r: r["commit_id"])
    for proj in missing:
        cand = [r for r in pool if r["project"] == proj]
        if not cand:
            continue
        # replace a random same-label example from a multi-represented project
        replacement = cand[0]
        for i, r in enumerate(out):
            if (
                commit_label_int(r) == commit_label_int(replacement)
                and sum(1 for x in out if x["project"] == r["project"]) > 1
            ):
                out[i] = replacement
                ids = [x["commit_id"] for x in out]
                pool = [x for x in pool if x["commit_id"] != replacement["commit_id"]]
                break
    out.sort(key=lambda r: r["commit_id"])
    return out


def stage_b_stats(recs: list[dict[str, Any]]) -> dict[str, Any]:
    n_pos = sum(1 for r in recs if commit_label_int(r) == 1)
    n_neg = len(recs) - n_pos
    projects = sorted({r["project"] for r in recs})
    return {
        "n": len(recs),
        "positives": n_pos,
        "negatives": n_neg,
        "prevalence": n_pos / len(recs) if recs else 0.0,
        "projects": projects,
        "n_projects": len(projects),
        "ids_sha256": hashlib.sha256(
            ("\n".join(r["commit_id"] for r in recs) + "\n").encode()
        ).hexdigest(),
    }

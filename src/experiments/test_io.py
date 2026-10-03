"""TEST-split I/O for the frozen attribution execution gate.

Does not modify rehearsal helpers. Validation rehearsal still refuses TEST.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from src.data.build_dataset import render_record
from src.data.token_line_map import build_chat_prompt, map_tokens_to_spans
from src.experiments.rehearsal_pipeline import PAYLOAD_SEGMENT_TYPES
from src.train.m1_dataset import render_and_truncate_prompt

TEST_BANNER = {
    "SPLIT": "TEST",
    "SCIENTIFIC_RESULT": True,
    "POST_TEST_TUNING_ALLOWED": False,
    "NOT_VALIDATION_REHEARSAL": True,
}


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_test_records(*, scientific_test_gate: bool, processed_dir: Path) -> list[dict[str, Any]]:
    if not scientific_test_gate:
        raise RuntimeError("TEST SPLIT LOAD BLOCKED without scientific_test_gate")
    recs = list(iter_jsonl(processed_dir / "test.jsonl"))
    require_test_split(recs)
    return recs


def require_test_split(records: Iterable[dict[str, Any]]) -> None:
    for rec in records:
        split = str(rec.get("split", "")).lower()
        if split != "test":
            raise RuntimeError(f"non-TEST record in TEST attribution path: {split!r} {rec.get('commit_id')}")


def encode_test_with_map(tokenizer, rec: dict[str, Any], *, max_length: int = 2048) -> dict[str, Any]:
    require_test_split([rec])
    rendered = render_record(rec)
    prompt, tr = render_and_truncate_prompt(tokenizer, rec, max_length=max_length)
    enc = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
    _full, structured_offset = build_chat_prompt(tokenizer, rendered.text)
    if rendered.text in prompt:
        off = prompt.find(rendered.text)
    else:
        off = structured_offset if structured_offset < len(prompt) else 0
    mapped = map_tokens_to_spans(
        tokenizer,
        prompt,
        off,
        [
            {
                "char_start": s.char_start,
                "char_end": s.char_end,
                "segment_type": s.segment_type,
                "stable_line_id": s.stable_line_id,
                "file_id": s.file_id,
                "hunk_id": s.hunk_id,
                "rq1_status": s.rq1_status,
                "payload": s.payload,
            }
            for s in rendered.spans
        ],
        keep_token_rows=True,
    )
    n_ids = int(enc["input_ids"].shape[1])
    rows = list(mapped["token_rows"])
    n = min(len(rows), n_ids)
    rows = rows[:n]
    token_map = []
    for i, row in enumerate(rows):
        cat = str(row.get("category") or row.get("segment_type") or "SPECIAL_TOKEN")
        if cat in {"OTHER", "MAPPING_ERROR"}:
            cat = "STRUCTURAL_MARKUP"
        token_map.append(
            {
                "token_index": i,
                "token_id": row.get("token_id"),
                "segment_type": cat,
                "stable_line_id": row.get("stable_line_id"),
                "rq1_status": row.get("rq1_status"),
                "payload": bool(row.get("stable_line_id")) and cat in PAYLOAD_SEGMENT_TYPES,
            }
        )
    while len(token_map) < n_ids:
        token_map.append(
            {
                "token_index": len(token_map),
                "token_id": None,
                "segment_type": "SPECIAL_TOKEN",
                "stable_line_id": None,
                "rq1_status": None,
                "payload": False,
            }
        )
    return {
        "input_ids": enc["input_ids"],
        "attention_mask": enc["attention_mask"],
        "prompt": prompt,
        "truncation": tr,
        "n_tokens": n_ids,
        "token_map": token_map,
        "map_ok": bool(mapped.get("ok")),
        "map_errors": mapped.get("errors") or [],
    }

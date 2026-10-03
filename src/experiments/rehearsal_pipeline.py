"""Validation attribution rehearsal helpers (pre-TEST qualification only)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.cohorts import CommitMeta, base_model_sanity_subset, select_validation_rehearsal
from src.data.build_dataset import render_record
from src.data.token_line_map import build_chat_prompt, map_tokens_to_spans
from src.train.m1_dataset import commit_label_int, render_and_truncate_prompt

BANNER = {
    "SPLIT": "VALIDATION",
    "PURPOSE": "REHEARSAL",
    "NOT_TEST_RESULT": True,
    "NOT_RQ_RESULT": True,
}

PAYLOAD_SEGMENT_TYPES = frozenset({"ADDED_CODE", "DELETED_CODE", "CONTEXT_CODE"})


def refuse_test_split(records: Iterable[dict[str, Any]]) -> None:
    for rec in records:
        split = str(rec.get("split", "")).lower()
        if split == "test":
            raise RuntimeError("TEST attribution blocked in validation rehearsal")
        if split not in {"valid", "val", "validation"}:
            raise RuntimeError(f"non-validation split in rehearsal: {split!r}")


def sha256_json(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def visible_token_count(tokenizer, rec: dict[str, Any], *, max_length: int = 2048) -> int:
    prompt, _tr = render_and_truncate_prompt(tokenizer, rec, max_length=max_length)
    enc = tokenizer(prompt, add_special_tokens=False)
    return int(len(enc["input_ids"]))


def build_rehearsal_cohort(
    tokenizer,
    valid_records: Sequence[dict[str, Any]],
    *,
    n: int = 64,
    max_length: int = 2048,
) -> dict[str, Any]:
    refuse_test_split(valid_records)
    positives = [r for r in valid_records if commit_label_int(r) == 1]
    metas: list[CommitMeta] = []
    token_by_id: dict[str, int] = {}
    for rec in positives:
        nt = visible_token_count(tokenizer, rec, max_length=max_length)
        token_by_id[rec["commit_id"]] = nt
        metas.append(
            CommitMeta(
                commit_id=rec["commit_id"],
                project=str(rec.get("project") or ""),
                visible_token_count=nt,
                split="VALIDATION",
                is_positive=True,
            )
        )
    selected = select_validation_rehearsal(metas, n=n)
    ordered_pool = sorted(metas, key=lambda c: (c.visible_token_count, c.commit_id))
    q = max(1, len(ordered_pool) // 4)
    cuts = [ordered_pool[min(len(ordered_pool) - 1, q * i)].visible_token_count for i in range(4)]

    def quartile(nt: int) -> str:
        if nt <= ordered_pool[q - 1].visible_token_count:
            return "Q1"
        if nt <= ordered_pool[2 * q - 1].visible_token_count:
            return "Q2"
        if nt <= ordered_pool[3 * q - 1].visible_token_count:
            return "Q3"
        return "Q4"

    rows = []
    for c in selected:
        rec = next(r for r in positives if r["commit_id"] == c.commit_id)
        rows.append(
            {
                **BANNER,
                "commit_id": c.commit_id,
                "project": c.project,
                "split": rec["split"],
                "validation_split_confirmed": rec["split"] == "valid",
                "commit_label": commit_label_int(rec),
                "positive_label_confirmed": commit_label_int(rec) == 1,
                "visible_token_count": c.visible_token_count,
                "length_quartile": quartile(c.visible_token_count),
                "selection_key": "project_round_robin_then_commit_id_within_length_quartiles",
                "rq1_primary_commit": rec.get("rq1_primary_commit"),
            }
        )
    sanity = base_model_sanity_subset(selected, n=16)
    payload = {
        **BANNER,
        "n": len(rows),
        "n_requested": n,
        "n_validation_positives_pool": len(positives),
        "projects": sorted({r["project"] for r in rows}),
        "quartiles": sorted({r["length_quartile"] for r in rows}),
        "quartile_cut_tokens": cuts,
        "max_length": max_length,
        "commits": rows,
        "sanity_commit_ids": [c.commit_id for c in sanity],
    }
    payload["cohort_manifest_sha256"] = sha256_json(
        {"commit_ids": [r["commit_id"] for r in rows], "n": len(rows)}
    )
    return payload


def encode_with_map(tokenizer, rec: dict[str, Any], *, max_length: int = 2048) -> dict[str, Any]:
    refuse_test_split([rec])
    rendered = render_record(rec)
    prompt, tr = render_and_truncate_prompt(tokenizer, rec, max_length=max_length)
    enc = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
    full_prompt, structured_offset = build_chat_prompt(tokenizer, rendered.text)
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
    if len(rows) != n_ids:
        # Truncated decode can drop trailing specials; align by min length.
        n = min(len(rows), n_ids)
        rows = rows[:n]
        if n_ids > n:
            pass
    token_map = []
    for i, row in enumerate(rows):
        cat = str(row.get("category") or row.get("segment_type") or "SPECIAL_TOKEN")
        if cat in {"OTHER", "MAPPING_ERROR"}:
            cat = "STRUCTURAL_MARKUP"
        token_map.append(
            {
                "token_index": i,
                "token_id": row.get("token_id"),
                "segment_type": cat if cat != "OTHER" else "STRUCTURAL_MARKUP",
                "stable_line_id": row.get("stable_line_id"),
                "rq1_status": row.get("rq1_status"),
                "payload": bool(row.get("stable_line_id"))
                and cat in PAYLOAD_SEGMENT_TYPES,
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
        "full_n_tokens": int(mapped.get("n_tokens") or n_ids),
    }


def mapping_stats(token_map: Sequence[dict[str, Any]], rec: dict[str, Any], dropped: Sequence[str]) -> dict[str, Any]:
    dropped_set = set(dropped)
    payload_tokens = [m for m in token_map if m.get("payload")]
    mapped_payload = [m for m in payload_tokens if m.get("stable_line_id")]
    unmapped_payload = [m for m in token_map if m.get("payload") and not m.get("stable_line_id")]
    eligible = []
    pos = neg = unknown = 0
    seen: set[str] = set()
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            for ln in h.get("lines") or []:
                sid = ln.get("stable_line_id")
                if not sid or sid in dropped_set or sid in seen:
                    continue
                seen.add(sid)
                st = ln.get("rq1_status") or "NOT_IN_RQ1_UNIVERSE"
                if st == "RQ1_POSITIVE":
                    pos += 1
                    eligible.append(sid)
                elif st == "RQ1_NEGATIVE":
                    neg += 1
                    eligible.append(sid)
                elif st == "NOT_IN_RQ1_UNIVERSE":
                    unknown += 1
                else:
                    unknown += 1
    return {
        "n_tokens": len(token_map),
        "n_payload_tokens": len(payload_tokens),
        "n_mapped_payload_tokens": len(mapped_payload),
        "n_unmapped_payload_tokens": len(unmapped_payload),
        "n_eligible_lines": len(eligible),
        "n_labelled_positive_lines": pos,
        "n_labelled_negative_lines": neg,
        "n_unknown_or_not_in_universe": unknown,
        "unexpected_unmapped_payload": len(unmapped_payload),
    }


def iter_lines(rec: dict[str, Any]):
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            for ln in h.get("lines") or []:
                yield f, h, ln


def visible_line_ids(rec: dict[str, Any], dropped: Sequence[str]) -> list[str]:
    drop = set(dropped)
    out: list[str] = []
    seen: set[str] = set()
    for _f, _h, ln in iter_lines(rec):
        sid = ln.get("stable_line_id")
        if sid and sid not in drop and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def apply_segment_delete_record(rec: dict[str, Any], region_ids: Sequence[str]) -> dict[str, Any]:
    drop = set(region_ids)
    out = copy.deepcopy(rec)
    for f in out.get("files") or []:
        for h in f.get("hunks") or []:
            h["lines"] = [ln for ln in (h.get("lines") or []) if ln.get("stable_line_id") not in drop]
        f["hunks"] = [h for h in f["hunks"] if h.get("lines")]
    out["files"] = [f for f in out["files"] if f.get("hunks")]
    return out


def apply_payload_blank_record(rec: dict[str, Any], region_ids: Sequence[str]) -> dict[str, Any]:
    drop = set(region_ids)
    out = copy.deepcopy(rec)
    for _f, _h, ln in iter_lines(out):
        if ln.get("stable_line_id") in drop:
            ln["raw_line_text"] = ""
            ln["payload_blanked"] = True
    return out


def ablate_category_in_structured_text(rec: dict[str, Any], category: str) -> dict[str, Any]:
    """Blank span payloads of ``category`` after render (causal ablation plumbing)."""
    out = copy.deepcopy(rec)
    if category == "COMMIT_MESSAGE":
        out["commit_message"] = ""
        return out
    if category == "FILE_PATH":
        for f in out.get("files") or []:
            f["canonical_path"] = ""
            f["new_path"] = ""
            f["old_path"] = ""
        return out
    if category == "STRUCTURAL_MARKUP":
        out["_ablate_structural_markup"] = True
        return out
    raise ValueError(category)


def maybe_space_structural_markup(prompt_structured: str, rec: dict[str, Any]) -> str:
    if not rec.get("_ablate_structural_markup"):
        return prompt_structured
    from src.data.structured_diff import MARKERS

    text = prompt_structured
    for marker in MARKERS.values():
        text = text.replace(marker, " " * len(marker))
    return text


def region_token_counts_from_map(token_map: Sequence[dict[str, Any]], region_ids: Sequence[str]) -> list[int]:
    counts = {rid: 0 for rid in region_ids}
    for m in token_map:
        sid = m.get("stable_line_id")
        if sid in counts and m.get("payload"):
            counts[str(sid)] += 1
    return [counts[rid] for rid in region_ids]


def pad_encoded(encoded: list[dict[str, Any]], *, pad_id: int, device) -> tuple[Any, Any]:
    import torch

    max_t = max(int(e["input_ids"].size(1)) for e in encoded)
    ids = []
    masks = []
    for e in encoded:
        x = e["input_ids"].to(device)
        m = e["attention_mask"].to(device)
        t = x.size(1)
        if t < max_t:
            pad = torch.full((1, max_t - t), pad_id, dtype=x.dtype, device=device)
            mp = torch.zeros((1, max_t - t), dtype=m.dtype, device=device)
            x = torch.cat([x, pad], dim=1)
            m = torch.cat([m, mp], dim=1)
        ids.append(x)
        masks.append(m)
    return torch.cat(ids, dim=0), torch.cat(masks, dim=0)

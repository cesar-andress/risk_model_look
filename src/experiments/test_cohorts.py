"""Deterministic TEST cohort reconstruction from frozen canonical_v1 + truncation rule."""

from __future__ import annotations

from typing import Any

from src.cohorts import CommitMeta, select_negative_matched_diagnostic
from src.data.build_dataset import render_record
from src.data.token_line_map import build_chat_prompt, whole_segment_prefix_truncation
from src.experiments.rehearsal_pipeline import sha256_json
from src.experiments.test_io import TEST_BANNER
from src.train.m1_dataset import commit_label_int


EXPECTED_TEST_N = 5480
EXPECTED_POS = 475
EXPECTED_NEG = 5005
EXPECTED_COMPLETE = 413
EXPECTED_VISIBLE_2048 = 304
EXPECTED_VISIBLE_4096 = 345
EXPECTED_PRE_CAND = 13412
EXPECTED_PRE_POS = 1712
EXPECTED_PRE_NEG = 11700


def rq1_lines(rec: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for f in rec.get("files") or []:
        for h in f.get("hunks") or []:
            for ln in h.get("lines") or []:
                if ln.get("rq1_status") in ("RQ1_POSITIVE", "RQ1_NEGATIVE"):
                    out.append(ln)
    return out


def truncation_for(tokenizer, rec: dict[str, Any], *, max_length: int) -> dict[str, Any]:
    rendered = render_record(rec)
    prompt, off = build_chat_prompt(tokenizer, rendered.text)
    return whole_segment_prefix_truncation(
        tokenizer, prompt, off, rendered.spans, max_length=max_length
    )


def fully_visible_rq1(tokenizer, rec: dict[str, Any], *, max_length: int) -> bool:
    if not rec.get("rq1_primary_commit"):
        return False
    tr = truncation_for(tokenizer, rec, max_length=max_length)
    dropped = set(tr.get("dropped_line_ids") or [])
    for ln in rq1_lines(rec):
        sid = ln.get("stable_line_id")
        if sid in dropped:
            return False
    return True


def pretruncation_universe(complete: list[dict[str, Any]]) -> dict[str, int]:
    cand = pos = neg = unk_as_neg = 0
    for rec in complete:
        for ln in rq1_lines(rec):
            cand += 1
            st = ln.get("rq1_status")
            if st == "RQ1_POSITIVE":
                pos += 1
            elif st == "RQ1_NEGATIVE":
                neg += 1
            else:
                unk_as_neg += 1
        for f in rec.get("files") or []:
            for h in f.get("hunks") or []:
                for ln in h.get("lines") or []:
                    if ln.get("rq1_status") not in ("RQ1_POSITIVE", "RQ1_NEGATIVE", "NOT_IN_RQ1_UNIVERSE", None):
                        unk_as_neg += 1
    return {
        "candidates": cand,
        "positives": pos,
        "negatives": neg,
        "unknown_contamination_count": unk_as_neg,
    }


def visible_token_count(tokenizer, rec: dict[str, Any], *, max_length: int = 2048) -> int:
    tr = truncation_for(tokenizer, rec, max_length=max_length)
    return int(tr.get("n_tokens_kept") or 0)


def build_test_cohorts(tokenizer, test_records: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(test_records)
    pos = [r for r in test_records if commit_label_int(r) == 1]
    neg = [r for r in test_records if commit_label_int(r) == 0]
    complete = [r for r in pos if r.get("rq1_primary_commit")]
    vis2048 = []
    vis4096 = []
    for i, r in enumerate(complete):
        if fully_visible_rq1(tokenizer, r, max_length=2048):
            vis2048.append(r)
        if fully_visible_rq1(tokenizer, r, max_length=4096):
            vis4096.append(r)
        if (i + 1) % 50 == 0:
            print(f"visibility {i+1}/{len(complete)} vis2048={len(vis2048)} vis4096={len(vis4096)}", flush=True)
    uni = pretruncation_universe(complete)
    print("computing visible token counts for matching...", flush=True)

    pos_meta = []
    for i, r in enumerate(pos):
        pos_meta.append(
            CommitMeta(
                commit_id=r["commit_id"],
                project=str(r.get("project") or ""),
                visible_token_count=visible_token_count(tokenizer, r, max_length=2048),
                split="TEST",
                is_positive=True,
            )
        )
        if (i + 1) % 50 == 0:
            print(f"pos tokens {i+1}/{len(pos)}", flush=True)
    clean_meta = []
    for i, r in enumerate(neg):
        clean_meta.append(
            CommitMeta(
                commit_id=r["commit_id"],
                project=str(r.get("project") or ""),
                visible_token_count=visible_token_count(tokenizer, r, max_length=2048),
                split="TEST",
                is_positive=False,
            )
        )
        if (i + 1) % 500 == 0:
            print(f"neg tokens {i+1}/{len(neg)}", flush=True)
    matched = select_negative_matched_diagnostic(pos_meta, clean_meta, n=475)

    errors = []
    if n != EXPECTED_TEST_N:
        errors.append(f"TEST n {n} != {EXPECTED_TEST_N}")
    if len(pos) != EXPECTED_POS:
        errors.append(f"positives {len(pos)} != {EXPECTED_POS}")
    if len(neg) != EXPECTED_NEG:
        errors.append(f"negatives {len(neg)} != {EXPECTED_NEG}")
    if len(complete) != EXPECTED_COMPLETE:
        errors.append(f"complete mapped {len(complete)} != {EXPECTED_COMPLETE}")
    if len(vis2048) != EXPECTED_VISIBLE_2048:
        errors.append(f"visible 2048 {len(vis2048)} != {EXPECTED_VISIBLE_2048}")
    if len(vis4096) != EXPECTED_VISIBLE_4096:
        errors.append(f"visible 4096 {len(vis4096)} != {EXPECTED_VISIBLE_4096}")
    if uni["candidates"] != EXPECTED_PRE_CAND:
        errors.append(f"candidates {uni['candidates']} != {EXPECTED_PRE_CAND}")
    if uni["positives"] != EXPECTED_PRE_POS:
        errors.append(f"pos lines {uni['positives']} != {EXPECTED_PRE_POS}")
    if uni["negatives"] != EXPECTED_PRE_NEG:
        errors.append(f"neg lines {uni['negatives']} != {EXPECTED_PRE_NEG}")
    if uni["unknown_contamination_count"] != 0:
        errors.append("UNKNOWN contamination")
    if len(matched) != 475:
        errors.append(f"matched clean {len(matched)} != 475")

    def pack(recs: list[dict[str, Any]], role: str) -> dict[str, Any]:
        ids = [r["commit_id"] for r in recs]
        body = {**TEST_BANNER, "role": role, "n": len(ids), "commit_ids": ids}
        body["manifest_sha256"] = sha256_json({"role": role, "commit_ids": ids})
        return body

    matched_ids = [c.commit_id for c in matched]
    out = {
        **TEST_BANNER,
        "errors": errors,
        "PASS": not errors,
        "test_n": n,
        "positive_n": len(pos),
        "negative_n": len(neg),
        "complete_mapped_n": len(complete),
        "rq1_primary_2048_n": len(vis2048),
        "rq1_4096_n": len(vis4096),
        "matched_clean_n": len(matched_ids),
        "label_universe_pretruncation": uni,
        "rq1_primary_304": pack(vis2048, "RQ1_PRIMARY_2048"),
        "rq1_4096_345": pack(vis4096, "RQ1_SENSITIVITY_4096"),
        "positive_475": pack(pos, "POSITIVE_TEST_475"),
        "complete_413": pack(complete, "RQ1_COMPLETE_MAPPED_413"),
        "matched_clean_475": {
            **TEST_BANNER,
            "role": "MATCHED_CLEAN_DIAGNOSTIC",
            "n": len(matched_ids),
            "commit_ids": matched_ids,
            "rule": "project_match then nearest visible_token_count then commit_id ASC",
            "manifest_sha256": sha256_json({"role": "MATCHED_CLEAN", "commit_ids": matched_ids}),
        },
    }
    return out

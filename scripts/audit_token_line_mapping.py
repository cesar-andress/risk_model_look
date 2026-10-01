"""Build canonical_v1 + run token-line / truncation audits."""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from src.data.build_dataset import build_commit_record, build_dataset, load_rq1_maps, render_record
from src.data.token_line_map import (
    LLAMA_ID,
    QWEN_ID,
    TOKEN_MAP_VERSION,
    build_chat_prompt,
    load_tokenizer,
    map_tokens_to_spans,
    verify_label_tokens,
    whole_segment_prefix_truncation,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_TM = ROOT / "artifacts/token_mapping"
OUT_PD = ROOT / "artifacts/processed_dataset"
CFG = ROOT / "configs/data/canonical_v1.yaml"
OUT_DIR = ROOT / "data/processed/canonical_v1"


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def rq1_lines(rec: dict) -> list[dict]:
    out = []
    for f in rec["files"]:
        for h in f["hunks"]:
            for ln in h["lines"]:
                if ln.get("rq1_status") in ("RQ1_POSITIVE", "RQ1_NEGATIVE"):
                    out.append(ln)
    return out


def audit_record(tok, rec: dict, *, keep_token_rows: bool = False) -> dict:
    rendered = render_record(rec)
    prompt, off = build_chat_prompt(tok, rendered.text)
    return map_tokens_to_spans(
        tok, prompt, off, rendered.spans, keep_token_rows=keep_token_rows
    )


def truncation_audit(tok, records: list[dict], max_length: int) -> dict:
    truncated = 0
    rq1_visible = 0
    cand_ret = cand_lost = pos_ret = pos_lost = neg_ret = neg_lost = 0
    commits_cand_loss = commits_pos_loss = 0
    n_rq1_commits = 0
    for rec in records:
        rendered = render_record(rec)
        prompt, off = build_chat_prompt(tok, rendered.text)
        tr = whole_segment_prefix_truncation(
            tok, prompt, off, rendered.spans, max_length=max_length
        )
        if tr["truncated"]:
            truncated += 1
        dropped = set(tr["dropped_line_ids"])
        if rec.get("rq1_primary_commit"):
            n_rq1_commits += 1
            lines = rq1_lines(rec)
            lost_any = False
            lost_pos = False
            for ln in lines:
                sid = ln["stable_line_id"]
                st = ln["rq1_status"]
                if sid in dropped:
                    lost_any = True
                    cand_lost += 1
                    if st == "RQ1_POSITIVE":
                        pos_lost += 1
                        lost_pos = True
                    else:
                        neg_lost += 1
                else:
                    cand_ret += 1
                    if st == "RQ1_POSITIVE":
                        pos_ret += 1
                    else:
                        neg_ret += 1
            if not lost_any:
                rq1_visible += 1
            else:
                commits_cand_loss += 1
            if lost_pos:
                commits_pos_loss += 1
    n = len(records)
    return {
        "max_length": max_length,
        "commits_total": n,
        "commits_truncated": truncated,
        "pct_truncated": (100.0 * truncated / n) if n else 0.0,
        "RQ1_VISIBLE_N": rq1_visible,
        "RQ1_commits": n_rq1_commits,
        "commits_losing_ge1_candidate": commits_cand_loss,
        "commits_losing_ge1_positive": commits_pos_loss,
        "candidates_retained": cand_ret,
        "candidates_lost": cand_lost,
        "positives_retained": pos_ret,
        "positives_lost": pos_lost,
        "negatives_retained": neg_ret,
        "negatives_lost": neg_lost,
    }


def sample_100(index_by_split: dict, seed: int = 20261001) -> list[str]:
    rng = random.Random(seed)
    by_proj: dict[str, list[str]] = defaultdict(list)
    rq1_ids = []
    for split, recs in index_by_split.items():
        for rec in recs:
            by_proj[rec["project"]].append(rec["commit_id"])
            if rec.get("rq1_primary_commit"):
                rq1_ids.append(rec["commit_id"])
    picks = []
    for p in sorted(by_proj):
        picks.append(rng.choice(by_proj[p]))
    pool = [cid for v in by_proj.values() for cid in v]
    rng.shuffle(pool)
    for cid in pool:
        if len(picks) >= 90:
            break
        if cid not in picks:
            picks.append(cid)
    rng.shuffle(rq1_ids)
    for cid in rq1_ids:
        if len(picks) >= 100:
            break
        if cid not in picks:
            picks.append(cid)
    while len(picks) < 100:
        picks.append(pool[len(picks) % len(pool)])
    return picks[:100]


def main() -> None:
    OUT_TM.mkdir(parents=True, exist_ok=True)
    OUT_PD.mkdir(parents=True, exist_ok=True)

    if (OUT_DIR / "test.jsonl").exists() and (OUT_PD / "manifest.json").exists():
        print("Reusing existing canonical_v1...")
        manifest = json.loads((OUT_PD / "manifest.json").read_text())
    else:
        print("Building canonical_v1...")
        manifest = build_dataset(CFG, out_dir=OUT_DIR)
        (OUT_PD / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
    print("manifest written", manifest.get("counts"))

    # Load index
    index: dict[str, dict] = {}
    by_split: dict[str, list] = {"train": [], "valid": [], "test": []}
    for split in ("train", "valid", "test"):
        for rec in iter_jsonl(OUT_DIR / f"{split}.jsonl"):
            index[rec["commit_id"]] = rec
            by_split[split].append(rec)
    assert len(index) == 27319

    # RQ1 pre-trunc counts
    rq1_cand = rq1_pos = rq1_neg = rq1_unmapped = 0
    outside_as_neg = 0
    for rec in by_split["test"]:
        if not rec["rq1_primary_commit"]:
            continue
        for f in rec["files"]:
            for h in f["hunks"]:
                for ln in h["lines"]:
                    st = ln.get("rq1_status")
                    if st == "RQ1_POSITIVE":
                        rq1_pos += 1
                        rq1_cand += 1
                        if not ln.get("stable_line_id"):
                            rq1_unmapped += 1
                    elif st == "RQ1_NEGATIVE":
                        rq1_neg += 1
                        rq1_cand += 1
                        if not ln.get("stable_line_id"):
                            rq1_unmapped += 1
                    elif st == "NOT_IN_RQ1_UNIVERSE":
                        pass
                    else:
                        outside_as_neg += 1
    print("RQ1 attach", rq1_cand, rq1_pos, rq1_neg, "unmapped", rq1_unmapped)

    print("Loading Qwen...")
    tok = load_tokenizer(QWEN_ID)
    label_info = verify_label_tokens(tok, QWEN_ID)

    picks = sample_100(by_split)
    pass_n = 0
    failures = []
    for cid in picks:
        res = audit_record(tok, index[cid], keep_token_rows=True)
        if res["ok"]:
            pass_n += 1
        else:
            failures.append({"commit_id": cid, "n_errors": len(res["errors"])})
    print("100-commit", pass_n)

    cat = Counter()
    mapping_errors = 0
    cross_same = 0
    commits_ok = 0
    commits_err = 0
    n_commits = 0
    for split in ("train", "valid", "test"):
        for rec in by_split[split]:
            n_commits += 1
            try:
                res = audit_record(tok, rec, keep_token_rows=False)
            except Exception:
                commits_err += 1
                mapping_errors += 1
                continue
            if res["ok"]:
                commits_ok += 1
            else:
                commits_err += 1
                mapping_errors += len(res["errors"])
            cross_same += res["cross_boundary_same_line"]
            cat.update(res.get("category_counts") or {})
            if n_commits % 500 == 0:
                print("map", n_commits, "ok", commits_ok, "err", commits_err, flush=True)

    trunc_rows = []
    for max_len in (2048, 4096):
        for split in ("train", "valid", "test"):
            tr = truncation_audit(tok, by_split[split], max_len)
            tr["split"] = split
            tr["representation"] = "CHANGED_ONLY"
            trunc_rows.append(tr)
        rq1_recs = [r for r in by_split["test"] if r["rq1_primary_commit"]]
        tr = truncation_audit(tok, rq1_recs, max_len)
        tr["split"] = "rq1_primary"
        tr["representation"] = "CHANGED_ONLY"
        trunc_rows.append(tr)
        print("trunc CHANGED_ONLY", max_len, "done")

    # CTX3 truncation (all commits)
    complete, rq1_map = load_rq1_maps(ROOT)
    ctx_recs = []
    print("CTX3 render...")
    for i, (cid, rec) in enumerate(index.items()):
        crec = build_commit_record(
            commit_id=cid,
            project=rec["project"],
            split=rec["split"],
            commit_label=rec["commit_label"],
            commit_message=rec["commit_message"],
            git_dir=ROOT / "data/raw/source_repos" / f"{rec['project']}.git",
            complete_case=complete,
            rq1_row_map=rq1_map,
            context=3,
        )
        ctx_recs.append(crec)
        if (i + 1) % 1000 == 0:
            print(" ctx", i + 1)
    for max_len in (2048, 4096):
        tr = truncation_audit(tok, ctx_recs, max_len)
        tr["split"] = "all"
        tr["representation"] = "CTX3"
        trunc_rows.append(tr)
        tr2 = truncation_audit(
            tok, [r for r in ctx_recs if r.get("rq1_primary_commit")], max_len
        )
        tr2["split"] = "rq1_primary"
        tr2["representation"] = "CTX3"
        trunc_rows.append(tr2)
        print("trunc CTX3", max_len, "done")

    llama_status = "ACCESS_BLOCKED"
    try:
        ltok = load_tokenizer(LLAMA_ID)
        li = verify_label_tokens(ltok, LLAMA_ID)
        llama_status = "PASS" if li.single_token else "FAIL"
    except Exception as e:
        llama_status = f"ACCESS_BLOCKED:{type(e).__name__}"

    # Determinism: rebuild once more to temp and compare SHA-256 (required for gate).
    import tempfile

    print("Determinism rebuild...")
    with tempfile.TemporaryDirectory() as td:
        m2 = build_dataset(CFG, out_dir=Path(td))
        det_ok = m2["file_sha256"] == manifest["file_sha256"]
    print("deterministic", det_ok, flush=True)

    gate = (
        label_info.single_token
        and pass_n == 100
        and commits_ok == 27319
        and rq1_cand == 13412
        and rq1_pos == 1712
        and rq1_neg == 11700
        and rq1_unmapped == 0
        and det_ok
        and outside_as_neg == 0
    )

    summary = {
        "TOKEN_LINE_MAPPING_GATE": "PASS" if gate else "FAIL",
        "TOKEN_MAP_VERSION": TOKEN_MAP_VERSION,
        "qwen": QWEN_ID,
        "qwen_fast": True,
        "label_tokens": {
            "token_id_0": label_info.token_id_0,
            "token_id_1": label_info.token_id_1,
            "single_token": label_info.single_token,
        },
        "deterministic_build": det_ok,
        "sample_100": {
            "passed": pass_n,
            "failures": failures[:10],
            "n_failures": len(failures),
        },
        "full_mapping": {
            "commits": n_commits,
            "commits_ok": commits_ok,
            "commits_err": commits_err,
            "mapping_error_events": mapping_errors,
            "cross_boundary_same_line_tokens": cross_same,
        },
        "pre_truncation_rq1": {
            "candidates": rq1_cand,
            "positives": rq1_pos,
            "negatives": rq1_neg,
            "unmapped": rq1_unmapped,
        },
        "llama": llama_status,
        "rq1_mask": "NOT_IN_RQ1_UNIVERSE_never_negative",
        "STABLE_LINE_ID_V1": (
            "(commit,file,change_type,old_lineno,new_lineno,occurrence_index,ordered_position)"
        ),
    }
    (OUT_TM / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    with (OUT_TM / "category_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "token_count"])
        for k, v in sorted(cat.items()):
            w.writerow([k, v])
    with (OUT_TM / "rq1_mapping_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in summary["pre_truncation_rq1"].items():
            w.writerow([k, v])
    with (OUT_TM / "truncation_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        fields = sorted({k for r in trunc_rows for k in r})
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in trunc_rows:
            w.writerow(r)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

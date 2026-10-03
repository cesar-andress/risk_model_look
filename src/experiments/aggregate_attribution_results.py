"""Aggregate attribution unit results into RQ table scaffolds (no science changes)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def aggregate_method_results(jsonl_path: Path) -> dict[str, Any]:
    rows = load_jsonl(jsonl_path)
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing: dict[str, int] = defaultdict(int)
    for r in rows:
        by_method[r.get("method", "?")].append(r)
        code = r.get("missingness_code") or "OK"
        if code != "OK":
            missing[code] += 1
    summary = {
        "n_rows": len(rows),
        "methods": {
            m: {
                "n": len(rs),
                "n_done": sum(1 for x in rs if x.get("status") == "DONE"),
                "n_failed": sum(1 for x in rs if x.get("status") in ("FAILED", "OOM")),
                "n_nonconverged": sum(1 for x in rs if x.get("status") == "NONCONVERGED"),
            }
            for m, rs in sorted(by_method.items())
        },
        "missingness_counts": dict(missing),
        "rq_table_hooks": {
            "rq1": "localization metrics computed offline from DONE rows",
            "rq2": "faithfulness metrics computed offline from DONE rows",
            "rq3": "polarity metrics computed offline from DONE rows",
            "rq4": "enrichment metrics computed offline from DONE rows",
        },
        "note": "This aggregator does not recompute scientific metrics; it indexes outputs.",
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aggregate attribution engine JSONL outputs")
    p.add_argument("--jsonl", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    summary = aggregate_method_results(args.jsonl)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["methods"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

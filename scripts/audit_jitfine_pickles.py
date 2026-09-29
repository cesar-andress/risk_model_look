#!/usr/bin/env python3
"""Static non-executing pickle audit for extracted JIT-Fine members."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.extract_members import JITFINE_MEMBERS  # noqa: E402
from src.data.pickle_audit import audit_pickle_file, audit_to_dict  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--extract-root",
        type=Path,
        default=ROOT / "data/raw/upstream/extracted",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/data_schema/pickle_static_audit.json",
    )
    args = p.parse_args()
    results = []
    worst = "PASS"
    for rel in JITFINE_MEMBERS:
        path = args.extract_root / rel
        if not path.is_file():
            print(f"FAIL: missing {path}", file=sys.stderr)
            return 1
        audit = audit_pickle_file(path)
        d = audit_to_dict(audit)
        d["file"] = rel
        results.append(d)
        if audit.static_pickle_risk == "FAIL":
            worst = "FAIL"
        elif audit.static_pickle_risk == "REQUIRES_REVIEW" and worst != "FAIL":
            worst = "REQUIRES_REVIEW"
        print(f"{rel}: {audit.static_pickle_risk} protocol={audit.pickle_protocol} opcodes={audit.opcode_count}")
    payload = {
        "overall_static_pickle_risk": worst,
        "files": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} overall={worst}")
    return 0 if worst != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())

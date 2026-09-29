#!/usr/bin/env python3
"""Extract the seven JIT-Fine members from the frozen data.zip."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.extract_members import (  # noqa: E402
    JITFINE_MEMBERS,
    extract_members,
    write_extracted_manifest_csv,
)

EXPECTED_SHA256 = "9e5ca1a393b70ee7e87c410b162005958775f3f3732f9f83da9dd24a7dfe2b47"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=Path, default=ROOT / "data/raw/upstream/data.zip")
    p.add_argument("--extract-root", type=Path, default=ROOT / "data/raw/upstream/extracted")
    p.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "artifacts/data_schema/extracted_files_manifest.csv",
    )
    args = p.parse_args()
    if not args.zip.is_file():
        print(f"FAIL: missing {args.zip}", file=sys.stderr)
        return 1
    digest = sha256_file(args.zip)
    if digest != EXPECTED_SHA256:
        print(f"FAIL: sha256 mismatch {digest}", file=sys.stderr)
        return 1
    rows = extract_members(args.zip, args.extract_root, JITFINE_MEMBERS)
    write_extracted_manifest_csv(rows, args.manifest)
    print(f"EXTRACTED {len(rows)} members -> {args.extract_root}")
    for r in rows:
        print(f"  {r['archive_path']} sha256={r['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

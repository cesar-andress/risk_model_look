"""Safe extraction of specific ZIP members (no extractall)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import zipfile


JITFINE_MEMBERS = (
    "data/jitfine/changes_train.pkl",
    "data/jitfine/features_train.pkl",
    "data/jitfine/changes_valid.pkl",
    "data/jitfine/features_valid.pkl",
    "data/jitfine/changes_test.pkl",
    "data/jitfine/features_test.pkl",
    "data/jitfine/changes_complete_buggy_line_level.pkl",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha512_bytes(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def resolve_safe_dest(extract_root: Path, member_name: str) -> Path:
    """Map archive member to dest under extract_root; refuse traversal."""
    root = extract_root.resolve()
    rel = PurePosixPath(member_name.replace("\\", "/"))
    if rel.is_absolute() or any(p == ".." for p in rel.parts):
        raise ValueError(f"unsafe member path: {member_name}")
    if not rel.parts:
        raise ValueError(f"empty member path: {member_name}")
    dest = (root.joinpath(*rel.parts)).resolve()
    try:
        dest.relative_to(root)
    except ValueError as e:
        raise ValueError(f"path escapes extract root: {member_name} -> {dest}") from e
    return dest


def extract_members(
    zip_path: Path,
    extract_root: Path,
    members: tuple[str, ...] = JITFINE_MEMBERS,
    *,
    refuse_unexplained_overwrite: bool = True,
) -> list[dict]:
    """Stream-extract named members; return per-file metadata."""
    extract_root.mkdir(parents=True, exist_ok=True)
    ts = utc_now()
    rows: list[dict] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        available = {i.filename for i in zf.infolist()}
        for name in members:
            if name not in available:
                raise FileNotFoundError(f"missing zip member: {name}")
            info = zf.getinfo(name)
            dest = resolve_safe_dest(extract_root, name)
            with zf.open(name, "r") as src:
                payload = src.read()
            if dest.exists() and refuse_unexplained_overwrite:
                if sha256_bytes(dest.read_bytes()) != sha256_bytes(payload):
                    raise FileExistsError(
                        f"refusing overwrite of unexplained existing file: {dest}"
                    )
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(payload)

            data = dest.read_bytes()
            rows.append(
                {
                    "archive_path": name,
                    "local_path_abs": str(dest),
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "sha256": sha256_bytes(data),
                    "sha512": sha512_bytes(data),
                    "extraction_timestamp": ts,
                }
            )
    return rows


def write_extracted_manifest_csv(rows: list[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "archive_path",
        "local_path_abs",
        "compressed_size",
        "uncompressed_size",
        "crc32",
        "sha256",
        "sha512",
        "extraction_timestamp",
    ]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join(str(r[c]).replace(",", ";") for c in cols))
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")

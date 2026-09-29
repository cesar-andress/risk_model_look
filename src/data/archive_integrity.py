"""Archive integrity helpers for JIT-Defects4J acquisition (no pickle)."""

from __future__ import annotations

import hashlib
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


EXPECTED_GIT_BLOB_SHA1 = "6cd2f45d97a7c430533cde382be6bf42d9ff3649"
EXPECTED_SIZE_BYTES = 75326372
# Exact member paths expected by provenance (JIT-Fine training/eval paths).
EXPECTED_JITFINE_MEMBERS = (
    "data/jitfine/changes_train.pkl",
    "data/jitfine/features_train.pkl",
    "data/jitfine/changes_valid.pkl",
    "data/jitfine/features_valid.pkl",
    "data/jitfine/changes_test.pkl",
    "data/jitfine/features_test.pkl",
    "data/jitfine/changes_complete_buggy_line_level.pkl",
)


def git_blob_sha1_bytes(data: bytes) -> str:
    """Git blob SHA-1: sha1(b'blob ' + size + b'\\0' + content)."""
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def git_blob_sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Streaming Git blob SHA-1 for a file on disk."""
    size = path.stat().st_size
    h = hashlib.sha1()
    h.update(b"blob " + str(size).encode("ascii") + b"\0")
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha512_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class IntegrityResult:
    size_bytes: int
    size_match: bool
    git_blob_sha1: str
    git_blob_match: bool
    sha256: str
    sha512: str


def verify_archive_file(
    path: Path,
    *,
    expected_size: int = EXPECTED_SIZE_BYTES,
    expected_git_blob_sha1: str = EXPECTED_GIT_BLOB_SHA1,
) -> IntegrityResult:
    size = path.stat().st_size
    blob = git_blob_sha1_file(path)
    return IntegrityResult(
        size_bytes=size,
        size_match=size == expected_size,
        git_blob_sha1=blob,
        git_blob_match=blob == expected_git_blob_sha1,
        sha256=sha256_file(path),
        sha512=sha512_file(path),
    )


def zip_integrity_ok(path: Path) -> bool:
    """Non-extracting CRC check via ZipFile.testzip()."""
    with zipfile.ZipFile(path, "r") as zf:
        bad = zf.testzip()
        return bad is None


@dataclass(frozen=True)
class ZipMemberMeta:
    archive_path: str
    is_directory: bool
    uncompressed_size: int
    compressed_size: int
    compression_method: int
    crc32: int


def list_zip_members(path: Path) -> list[ZipMemberMeta]:
    rows: list[ZipMemberMeta] = []
    with zipfile.ZipFile(path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            is_dir = name.endswith("/") or info.is_dir()
            rows.append(
                ZipMemberMeta(
                    archive_path=name,
                    is_directory=is_dir,
                    uncompressed_size=info.file_size,
                    compressed_size=info.compress_size,
                    compression_method=info.compress_type,
                    crc32=info.CRC,
                )
            )
    return rows


_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def audit_zip_path_safety(members: Iterable[ZipMemberMeta]) -> tuple[str, list[str]]:
    """Return (PASS|FAIL, list of issues). Does not extract."""
    issues: list[str] = []
    normalized_seen: dict[str, str] = {}
    casefold_seen: dict[str, str] = {}

    for m in members:
        name = m.archive_path
        if name.startswith("/") or name.startswith("\\"):
            issues.append(f"absolute_path:{name}")
        if _DRIVE_RE.match(name):
            issues.append(f"drive_letter_path:{name}")
        parts = PurePosixPath(name.replace("\\", "/")).parts
        if ".." in parts:
            issues.append(f"path_traversal:{name}")
        # Symlink detection: ZipInfo.external_attr high bits / create_system —
        # not always reliable; flag Unix symlink mode if present in name only via create_system
        # We cannot see external_attr from ZipMemberMeta; skip unless name suggests link.
        # Duplicate normalized paths:
        norm = str(PurePosixPath(name.replace("\\", "/")))
        if norm in normalized_seen and normalized_seen[norm] != name:
            issues.append(f"duplicate_normalized:{normalized_seen[norm]}|{name}")
        else:
            normalized_seen[norm] = name
        cf = norm.casefold()
        if cf in casefold_seen and casefold_seen[cf] != norm:
            issues.append(f"case_collision:{casefold_seen[cf]}|{norm}")
        else:
            casefold_seen[cf] = norm

    return ("FAIL" if issues else "PASS", issues)


def match_expected_pkl_members(members: Iterable[ZipMemberMeta]) -> tuple[list[str], list[str]]:
    """Match exact provenance paths under data/jitfine/ (no open/unpickle)."""
    files = {m.archive_path for m in members if not m.is_directory}
    found = [p for p in EXPECTED_JITFINE_MEMBERS if p in files]
    missing = [p for p in EXPECTED_JITFINE_MEMBERS if p not in files]
    return found, missing


def inventory_aggregates(members: list[ZipMemberMeta]) -> dict:
    files = [m for m in members if not m.is_directory]
    dirs = [m for m in members if m.is_directory]
    ext_counts: Counter[str] = Counter()
    for m in files:
        name = PurePosixPath(m.archive_path).name
        if "." in name:
            ext = "." + name.rsplit(".", 1)[-1].lower()
        else:
            ext = ""
        ext_counts[ext] += 1
    largest = sorted(files, key=lambda m: m.uncompressed_size, reverse=True)[:10]
    return {
        "total_entries": len(members),
        "directories": len(dirs),
        "files": len(files),
        "total_uncompressed_bytes": sum(m.uncompressed_size for m in members),
        "total_compressed_bytes": sum(m.compressed_size for m in members),
        "largest_files": [
            {"archive_path": m.archive_path, "uncompressed_size": m.uncompressed_size}
            for m in largest
        ],
        "file_extension_counts": dict(sorted(ext_counts.items())),
    }


def write_inventory_csv(members: list[ZipMemberMeta], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "archive_path,is_directory,uncompressed_size,compressed_size,compression_method,CRC32"
    ]
    for m in members:
        # Escape commas in paths if any
        path = m.archive_path.replace('"', '""')
        if "," in path:
            path = f'"{path}"'
        lines.append(
            f"{path},{str(m.is_directory).lower()},{m.uncompressed_size},"
            f"{m.compressed_size},{m.compression_method},{m.crc32:08x}"
        )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")

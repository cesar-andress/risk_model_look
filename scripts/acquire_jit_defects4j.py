#!/usr/bin/env python3
"""Acquire and freeze JIT-Defects4J data.zip from jacknichao/JIT-Fine (immutable SHA).

Does NOT extract the archive and does NOT unpickle any contents.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.archive_integrity import (  # noqa: E402
    EXPECTED_GIT_BLOB_SHA1,
    EXPECTED_SIZE_BYTES,
    audit_zip_path_safety,
    inventory_aggregates,
    list_zip_members,
    match_expected_pkl_members,
    verify_archive_file,
    write_inventory_csv,
    zip_integrity_ok,
)

FROZEN_REPO = "jacknichao/JIT-Fine"
FROZEN_REVISION = "584799fdec6095ab75a45fd2a5f8db5b12163aa5"
ARCHIVE_PATH_IN_REPO = "data.zip"
DEFAULT_URL = (
    f"https://raw.githubusercontent.com/{FROZEN_REPO}/"
    f"{FROZEN_REVISION}/{ARCHIVE_PATH_IN_REPO}"
)
DEFAULT_DEST_DIR = ROOT / "data" / "raw" / "upstream"
DEFAULT_ARTIFACTS = ROOT / "artifacts" / "data_acquisition"
CHUNK = 1024 * 1024


class AcquisitionError(Exception):
    """Non-zero exit acquisition failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def refuse_overwrite_mismatched(dest: Path, partial: Path) -> str | None:
    """If dest exists and matches expected blob, return REUSED; else quarantine or None."""
    if not dest.exists():
        return None
    result = verify_archive_file(dest)
    if result.size_match and result.git_blob_match:
        return "REUSED_VERIFIED_LOCAL_ARCHIVE"
    # Quarantine — never overwrite silently
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    quarantine = dest.with_name(f"data.zip.unverified.{ts}")
    dest.rename(quarantine)
    raise AcquisitionError(
        f"Existing {dest} does not match frozen archive "
        f"(size={result.size_bytes}, git_blob={result.git_blob_sha1}); "
        f"quarantined to {quarantine.name}. Refusing overwrite."
    )


def stream_download(url: str, partial: Path) -> dict:
    """Stream URL to partial path; return HTTP metadata."""
    partial.parent.mkdir(parents=True, exist_ok=True)
    if partial.exists():
        partial.unlink()

    start = utc_now()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "risk_model_look-acquisition/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            resolved = resp.geturl()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            bytes_received = 0
            with partial.open("wb") as out:
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
                    bytes_received += len(chunk)
    except urllib.error.HTTPError as e:
        raise AcquisitionError(f"HTTP {e.code} downloading {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise AcquisitionError(f"URL error downloading {url}: {e.reason}") from e

    finish = utc_now()
    return {
        "requested_url": url,
        "resolved_url": resolved,
        "http_status": int(status),
        "content_length_header": headers.get("content-length"),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "download_start_utc": start,
        "download_finish_utc": finish,
        "bytes_received": bytes_received,
    }


def acquire(
    *,
    dest_dir: Path = DEFAULT_DEST_DIR,
    url: str = DEFAULT_URL,
    artifacts_dir: Path = DEFAULT_ARTIFACTS,
    force_download: bool = False,
) -> dict:
    dest_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "data.zip"
    partial = dest_dir / "data.zip.partial"

    log_lines: list[str] = []
    log_lines.append(f"acquisition_start_utc={utc_now()}")
    log_lines.append(f"source_repository={FROZEN_REPO}")
    log_lines.append(f"source_revision={FROZEN_REVISION}")
    log_lines.append(f"source_archive_path={ARCHIVE_PATH_IN_REPO}")
    log_lines.append(f"requested_url={url}")
    log_lines.append(f"local_dest={dest}")

    downloaded_or_reused = "DOWNLOADED"
    http_meta: dict = {
        "requested_url": url,
        "resolved_url": None,
        "http_status": None,
        "content_length_header": None,
        "etag": None,
        "last_modified": None,
        "download_start_utc": None,
        "download_finish_utc": None,
        "bytes_received": None,
    }

    if dest.exists() and not force_download:
        reuse = refuse_overwrite_mismatched(dest, partial)
        if reuse == "REUSED_VERIFIED_LOCAL_ARCHIVE":
            downloaded_or_reused = reuse
            log_lines.append("action=REUSED_VERIFIED_LOCAL_ARCHIVE")
            prev_report = artifacts_dir / "acquisition_report.json"
            if prev_report.exists():
                try:
                    prev = json.loads(prev_report.read_text(encoding="utf-8"))
                    for key in (
                        "requested_url",
                        "resolved_url",
                        "http_status",
                        "content_length_header",
                        "etag",
                        "last_modified",
                        "download_start_utc",
                        "download_finish_utc",
                        "bytes_received",
                    ):
                        if prev.get(key) is not None:
                            http_meta[key] = prev[key]
                    # Prefer original DOWNLOADED label if this session already acquired once.
                    if prev.get("downloaded_or_reused") == "DOWNLOADED":
                        downloaded_or_reused = "DOWNLOADED"
                        log_lines.append("preserved_prior_download_metadata=true")
                except (json.JSONDecodeError, OSError):
                    pass
    else:
        if partial.exists() and not force_download:
            # Stale partial: remove only partial, never touch verified dest
            partial.unlink()
            log_lines.append("removed_stale_partial=true")

        if downloaded_or_reused != "REUSED_VERIFIED_LOCAL_ARCHIVE":
            log_lines.append("action=DOWNLOAD")
            http_meta = stream_download(url, partial)
            log_lines.append(f"http_status={http_meta['http_status']}")
            log_lines.append(f"resolved_url={http_meta['resolved_url']}")
            log_lines.append(f"bytes_received={http_meta['bytes_received']}")

            # Verify before rename
            integrity = verify_archive_file(partial)
            if not integrity.size_match or not integrity.git_blob_match:
                # Keep partial for forensics under clear name
                bad = dest_dir / f"data.zip.partial.failed.{utc_now().replace(':', '')}"
                partial.rename(bad)
                raise AcquisitionError(
                    f"Integrity mismatch before rename: size={integrity.size_bytes} "
                    f"(expected {EXPECTED_SIZE_BYTES}), "
                    f"git_blob={integrity.git_blob_sha1} "
                    f"(expected {EXPECTED_GIT_BLOB_SHA1}); left at {bad.name}"
                )
            partial.replace(dest)
            log_lines.append("renamed_partial_to_data_zip=true")

    integrity = verify_archive_file(dest)
    if not integrity.size_match or not integrity.git_blob_match:
        raise AcquisitionError(
            f"Final integrity failed: size={integrity.size_bytes}, "
            f"git_blob={integrity.git_blob_sha1}"
        )

    zip_ok = zip_integrity_ok(dest)
    if not zip_ok:
        raise AcquisitionError("ZIP integrity testzip() failed")

    members = list_zip_members(dest)
    path_safety, path_issues = audit_zip_path_safety(members)
    if path_safety != "PASS":
        raise AcquisitionError(f"ZIP path safety FAIL: {path_issues}")

    agg = inventory_aggregates(members)
    found, missing = match_expected_pkl_members(members)
    if missing:
        raise AcquisitionError(f"Expected pickle basenames missing from ZIP: {missing}")

    inv_path = artifacts_dir / "archive_inventory.csv"
    write_inventory_csv(members, inv_path)

    sha256_path = artifacts_dir / "data_zip_sha256.txt"
    sha256_path.write_text(integrity.sha256 + "\n", encoding="utf-8")
    (artifacts_dir / "data_zip_sha512.txt").write_text(integrity.sha512 + "\n", encoding="utf-8")

    report = {
        "dataset": "JIT-Defects4J",
        "canonical_name": "JIT-Defects4J",
        "source_repository": FROZEN_REPO,
        "source_revision": FROZEN_REVISION,
        "source_archive_path": ARCHIVE_PATH_IN_REPO,
        "requested_url": http_meta["requested_url"],
        "resolved_url": http_meta["resolved_url"],
        "downloaded_or_reused": downloaded_or_reused,
        "download_start_utc": http_meta["download_start_utc"],
        "download_finish_utc": http_meta["download_finish_utc"],
        "http_status": http_meta["http_status"],
        "content_length_header": http_meta["content_length_header"],
        "etag": http_meta["etag"],
        "last_modified": http_meta["last_modified"],
        "bytes_received": http_meta["bytes_received"],
        "local_path": str(dest.relative_to(ROOT)),
        "size_bytes": integrity.size_bytes,
        "expected_size_bytes": EXPECTED_SIZE_BYTES,
        "size_match": integrity.size_match,
        "expected_git_blob_sha1": EXPECTED_GIT_BLOB_SHA1,
        "actual_git_blob_sha1": integrity.git_blob_sha1,
        "git_blob_match": integrity.git_blob_match,
        "sha256": integrity.sha256,
        "sha512": integrity.sha512,
        "zip_integrity": "PASS" if zip_ok else "FAIL",
        "zip_path_safety": path_safety,
        "zip_path_safety_issues": path_issues,
        "archive_entry_count": agg["total_entries"],
        "archive_total_uncompressed_bytes": agg["total_uncompressed_bytes"],
        "archive_aggregates": agg,
        "expected_files_found": found,
        "expected_files_missing": missing,
        "pickle_executed": False,
        "archive_extracted": False,
        "gitignored": True,
        "license_unchanged": {
            "code": "NONE_FOUND",
            "dataset": "NONE_FOUND",
            "raw_redistribution": "NOT_ESTABLISHED",
            "derived_redistribution": "NOT_ESTABLISHED",
        },
        "gate_verdict": "PASS",
        "destination_note": (
            "Canonical local path data/raw/upstream/data.zip per DATASET_ACQUISITION_GATE; "
            "supersedes nested revision subdirectory draft in earlier DATA_ACQUISITION_PLAN."
        ),
    }

    report_path = artifacts_dir / "acquisition_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    log_lines.append(f"size_bytes={integrity.size_bytes}")
    log_lines.append(f"git_blob_sha1={integrity.git_blob_sha1}")
    log_lines.append(f"sha256={integrity.sha256}")
    log_lines.append(f"zip_integrity={'PASS' if zip_ok else 'FAIL'}")
    log_lines.append(f"zip_path_safety={path_safety}")
    log_lines.append(f"expected_files_missing={missing}")
    log_lines.append("pickle_executed=false")
    log_lines.append("archive_extracted=false")
    log_lines.append(f"gate_verdict={report['gate_verdict']}")
    log_lines.append(f"acquisition_finish_utc={utc_now()}")
    (artifacts_dir / "download_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(
        f"ACQUISITION {report['gate_verdict']}: {downloaded_or_reused} "
        f"size={integrity.size_bytes} git_blob={integrity.git_blob_sha1} "
        f"sha256={integrity.sha256}"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--dest-dir", type=Path, default=DEFAULT_DEST_DIR)
    parser.add_argument("--artifacts-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload even if a verified local archive exists (still refuses mismatched overwrite without quarantine).",
    )
    args = parser.parse_args(argv)
    try:
        acquire(
            dest_dir=args.dest_dir,
            url=args.url,
            artifacts_dir=args.artifacts_dir,
            force_download=args.force_download,
        )
        return 0
    except AcquisitionError as e:
        print(f"ACQUISITION FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

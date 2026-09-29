"""Unit tests for acquisition integrity helpers (no network, no real data.zip)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.data.archive_integrity import (
    EXPECTED_GIT_BLOB_SHA1,
    git_blob_sha1_bytes,
    git_blob_sha1_file,
    verify_archive_file,
)


def test_git_blob_sha1_matches_known_toy_bytes() -> None:
    data = b"hello\n"
    # echo -n 'hello\n' | git hash-object --stdin  => known for "hello\n"
    expected = hashlib.sha1(b"blob 6\0" + data).hexdigest()
    assert git_blob_sha1_bytes(data) == expected
    assert expected == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_git_blob_sha1_file_matches_bytes(tmp_path: Path) -> None:
    p = tmp_path / "toy.bin"
    data = b"abc" * 1000
    p.write_bytes(data)
    assert git_blob_sha1_file(p) == git_blob_sha1_bytes(data)


def test_verify_succeeds_for_matching_dummy(tmp_path: Path) -> None:
    # Craft a tiny file and verify against its own size/blob (not the real archive constants).
    p = tmp_path / "dummy.zip"
    content = b"PK\x03\x04dummy-not-a-real-zip"
    p.write_bytes(content)
    blob = git_blob_sha1_bytes(content)
    result = verify_archive_file(
        p, expected_size=len(content), expected_git_blob_sha1=blob
    )
    assert result.size_match is True
    assert result.git_blob_match is True
    assert result.git_blob_sha1 == blob
    assert len(result.sha256) == 64


def test_verify_fails_on_wrong_expected_hash(tmp_path: Path) -> None:
    p = tmp_path / "dummy.bin"
    p.write_bytes(b"x" * 32)
    result = verify_archive_file(
        p,
        expected_size=32,
        expected_git_blob_sha1="0" * 40,
    )
    assert result.size_match is True
    assert result.git_blob_match is False


def test_refuse_overwrite_mismatched_quarantines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.acquire_jit_defects4j as acq

    dest = tmp_path / "data.zip"
    dest.write_bytes(b"wrong-archive-bytes")
    partial = tmp_path / "data.zip.partial"

    with pytest.raises(acq.AcquisitionError, match="quarantined"):
        acq.refuse_overwrite_mismatched(dest, partial)

    assert not dest.exists()
    quarantined = list(tmp_path.glob("data.zip.unverified.*"))
    assert len(quarantined) == 1


def test_reuse_when_existing_matches_expected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.acquire_jit_defects4j as acq
    from src.data import archive_integrity as ai

    # Build a file whose blob we stub as matching EXPECTED via monkeypatch of verify.
    dest = tmp_path / "data.zip"
    dest.write_bytes(b"placeholder")
    partial = tmp_path / "data.zip.partial"

    class Fake:
        size_bytes = ai.EXPECTED_SIZE_BYTES
        size_match = True
        git_blob_sha1 = ai.EXPECTED_GIT_BLOB_SHA1
        git_blob_match = True
        sha256 = "a" * 64
        sha512 = "b" * 128

    monkeypatch.setattr(acq, "verify_archive_file", lambda path: Fake())
    assert acq.refuse_overwrite_mismatched(dest, partial) == "REUSED_VERIFIED_LOCAL_ARCHIVE"
    assert dest.exists()


def test_expected_blob_constant_unchanged() -> None:
    assert EXPECTED_GIT_BLOB_SHA1 == "6cd2f45d97a7c430533cde382be6bf42d9ff3649"

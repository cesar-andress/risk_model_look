"""Bootstrap: required project paths and bookkeeping files exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist() -> None:
    required = [
        "configs",
        "data/raw",
        "data/processed",
        "docs",
        "results",
        "scripts",
        "src",
        "src/data",
        "src/train",
        "src/eval",
        "src/xai",
        "src/metrics",
        "src/stats",
        "src/viz",
        "tests",
        "artifacts",
        "artifacts/bootstrap",
    ]
    missing = [p for p in required if not (ROOT / p).is_dir()]
    assert not missing, f"Missing directories: {missing}"


def test_required_files_exist() -> None:
    required = [
        "README.md",
        "REPRODUCE.md",
        "STATUS.md",
        "environment.yml",
        ".gitignore",
        "docs/EXPERIMENT_PROTOCOL_V0.md",
        "docs/REFERENCE_LEDGER.md",
        "docs/NOVELTY_GATE.md",
        "docs/DECISION_LOG.md",
        "docs/DATA_PROVENANCE.md",
        "docs/ENVIRONMENT_REPORT.md",
        "scripts/smoke_qwen_4bit.py",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    assert not missing, f"Missing files: {missing}"


def test_novelty_gate_resolved_pass() -> None:
    text = (ROOT / "docs/NOVELTY_GATE.md").read_text(encoding="utf-8")
    status_block = text.split("## STATUS", 1)[1].split("##", 1)[0]
    assert "**PASS**" in status_block
    assert "**UNRESOLVED**" not in status_block
    assert "PROVISIONAL DEFENSIBLE NOVELTY CLAIM" in text


def test_novelty_audit_artifacts_exist() -> None:
    required = [
        "docs/literature_search_log.csv",
        "docs/literature_screening.csv",
        "docs/NOVELTY_COLLISION_MATRIX.md",
        "docs/STATE_OF_ART_NOVELTY_MAP.md",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    assert not missing, f"Missing novelty audit artifacts: {missing}"


def test_gitignore_protects_sensitive_paths() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in [".cursor/", ".claude/", ".agents/", ".env", "data/raw/**", "wandb/"]:
        assert needle in text, f".gitignore missing pattern: {needle}"

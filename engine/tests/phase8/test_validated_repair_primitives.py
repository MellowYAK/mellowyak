from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from mellowyak_engine.repair_candidates.manifest import (
    CandidateManifestError,
    normalize_relative,
    safe_join,
    scan_workspace,
)
from mellowyak_engine.safe_apply.capability import (
    confirmation_digest,
    issue_confirmation,
    verify_confirmation,
)
from mellowyak_engine.safe_apply.journal import DurableJournal
from mellowyak_engine.safe_apply.preflight import PreflightError, digest_path, verify_expected


@pytest.mark.parametrize("value", ["../escape", "/absolute", "a/../b", "./file", "a\\b"])
def test_candidate_paths_reject_escape_and_noncanonical_values(value: str) -> None:
    with pytest.raises(CandidateManifestError, match="CANDIDATE_PATH_INVALID"):
        normalize_relative(value)


def test_candidate_manifest_is_deterministic_and_classifies_binary(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("stable\n", encoding="utf-8")
    (tmp_path / "a.bin").write_bytes(b"\x00fixture")
    first, first_digest = scan_workspace(tmp_path)
    second, second_digest = scan_workspace(tmp_path)
    assert first == second
    assert first_digest == second_digest
    assert [item.relative_path for item in first] == ["a.bin", "z.txt"]
    assert first[0].classification == "binary"
    assert first[1].classification == "text"


def test_candidate_manifest_rejects_sensitive_path(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DEMO_SECRET=must-not-export\n", encoding="utf-8")
    with pytest.raises(CandidateManifestError, match="CANDIDATE_SENSITIVE_PATH_REJECTED"):
        scan_workspace(tmp_path)


def test_candidate_manifest_rejects_symlink(tmp_path: Path, create_symlink) -> None:
    outside = tmp_path.parent / "outside-phase8.txt"
    outside.write_text("outside\n", encoding="utf-8")
    create_symlink(tmp_path / "escape", outside)
    with pytest.raises(CandidateManifestError, match="CANDIDATE_SYMLINK_REJECTED"):
        scan_workspace(tmp_path)


def test_candidate_manifest_rejects_hard_link(tmp_path: Path) -> None:
    original = tmp_path / "original.txt"
    original.write_text("same inode\n", encoding="utf-8")
    os.link(original, tmp_path / "linked.txt")
    with pytest.raises(CandidateManifestError, match="CANDIDATE_HARD_LINK_REJECTED"):
        scan_workspace(tmp_path)


def test_safe_join_stays_inside_workspace(tmp_path: Path) -> None:
    folder = tmp_path / "nested"
    folder.mkdir()
    assert safe_join(tmp_path, "nested/new.py") == folder / "new.py"


def test_confirmation_is_candidate_project_and_source_bound() -> None:
    nonce, expected = issue_confirmation("tx", "project", "candidate", "source")
    assert verify_confirmation(
        confirmation_digest(nonce, "tx", "project", "candidate", "source"), expected
    )
    assert not verify_confirmation(
        confirmation_digest(nonce, "tx", "other-project", "candidate", "source"), expected
    )
    assert not verify_confirmation(
        confirmation_digest(nonce, "tx", "project", "other-candidate", "source"), expected
    )
    assert not verify_confirmation(
        confirmation_digest(nonce, "tx", "project", "candidate", "other-source"), expected
    )


def test_durable_apply_journal_survives_reload(tmp_path: Path) -> None:
    path = tmp_path / "journal" / "tx.json"
    journal = DurableJournal.create(path, {"transaction_id": "tx", "state": "PREPARING"})
    journal.append("APPLY_STARTED", {"candidate_id": "candidate"})
    loaded = DurableJournal.load(path)
    assert loaded.payload["state"] == "APPLY_STARTED"
    assert loaded.payload["events"][0]["sequence"] == 1
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600


def test_preflight_rehash_blocks_digest_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "source.py"
    target.write_bytes(b"current")
    assert digest_path(target) == hashlib.sha256(b"current").hexdigest()
    with pytest.raises(PreflightError, match="APPLY_LIVE_DIGEST_MISMATCH"):
        verify_expected(target, hashlib.sha256(b"older").hexdigest(), "source.py")


def test_preflight_allows_exact_digest_and_missing_add(tmp_path: Path) -> None:
    target = tmp_path / "source.py"
    target.write_bytes(b"current")
    verify_expected(target, hashlib.sha256(b"current").hexdigest(), "source.py")
    verify_expected(tmp_path / "new.py", None, "new.py")

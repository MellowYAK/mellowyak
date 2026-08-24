from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mellowyak_engine.snapshots import (
    SnapshotStore,
    SnapshotStoreError,
    canonical_json,
)

FIXED_TIME = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _entry_map(result) -> dict[str, object]:
    return {entry.relative_path: entry for entry in result.manifest.entries}


def _source_signature(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(root).as_posix()
            result[relative] = (
                stat.S_IMODE(path.stat().st_mode),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return result


def test_content_addressed_dedup_binary_empty_and_canonical_manifest(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "alpha.txt").write_text("same bytes\n", encoding="utf-8")
    (project / "copy.txt").write_text("same bytes\n", encoding="utf-8")
    (project / "empty.txt").write_bytes(b"")
    binary = b"\x00\xff\x10MellowYak\x00"
    (project / "asset.bin").write_bytes(binary)
    store = SnapshotStore(tmp_path / "data", "project-1")

    first = store.capture(
        project,
        snapshot_id="snapshot-a",
        episode_id="episode-a",
        creation_reason="initial",
        runtime_profile_fingerprints=("python:one", "node:two", "python:one"),
        created_at=FIXED_TIME,
    )

    entries = _entry_map(first)
    assert entries["alpha.txt"].blob_sha256 == entries["copy.txt"].blob_sha256
    assert entries["asset.bin"].classification == "binary"
    assert store.object_path(entries["asset.bin"].blob_sha256).read_bytes() == binary
    assert first.stats.physical_objects_created == 3
    assert first.stats.deduplicated_objects == 1
    assert first.manifest.runtime_profile_fingerprints == ("node:two", "python:one")
    manifest_bytes = (tmp_path / "data" / first.manifest_path).read_bytes()
    assert manifest_bytes == canonical_json(first.manifest.to_dict()) + b"\n"
    assert json.loads(manifest_bytes)["manifest_digest"] == first.manifest.manifest_digest

    second = store.capture(
        project,
        snapshot_id="snapshot-b",
        parent_snapshot_id="snapshot-a",
        creation_reason="episode",
        created_at=FIXED_TIME,
    )
    assert second.stats.physical_objects_created == 0
    assert second.stats.deduplicated_objects == 4
    assert SnapshotStore(tmp_path / "data", "project-1").verify_snapshot("snapshot-b").valid


def test_manifest_represents_deletion_and_rename_without_copying_unchanged_blob(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "rename-me.txt").write_text("stable content", encoding="utf-8")
    (project / "delete-me.txt").write_text("removed content", encoding="utf-8")
    store = SnapshotStore(tmp_path / "data", "project-2")
    before = store.capture(project, snapshot_id="before", created_at=FIXED_TIME)
    before_entries = _entry_map(before)

    (project / "rename-me.txt").rename(project / "renamed.txt")
    (project / "delete-me.txt").unlink()
    (project / "new.txt").write_text("new content", encoding="utf-8")
    after = store.capture(
        project,
        snapshot_id="after",
        parent_snapshot_id="before",
        created_at=FIXED_TIME,
    )
    after_entries = _entry_map(after)

    assert "rename-me.txt" not in after_entries
    assert "delete-me.txt" not in after_entries
    assert after_entries["renamed.txt"].blob_sha256 == before_entries["rename-me.txt"].blob_sha256
    assert after.stats.physical_objects_created == 1
    assert after.stats.deduplicated_objects == 1
    marked = store.mark_referenced_objects()
    assert before_entries["delete-me.txt"].blob_sha256 in marked


def test_sensitive_ignore_symlink_artifact_large_and_nested_data_are_excluded(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".gitignore").write_text("ignored.txt\nignored-dir/\n", encoding="utf-8")
    (project / ".mellowyakignore").write_text("*.yak-secret\n", encoding="utf-8")
    (project / "safe.txt").write_text("public", encoding="utf-8")
    secret_value = "NEVER_PERSIST_THIS_SECRET_7F92"
    (project / ".env").write_text(f"TOKEN={secret_value}\n", encoding="utf-8")
    (project / "ignored.txt").write_text("ignored", encoding="utf-8")
    (project / "private.yak-secret").write_text("ignored", encoding="utf-8")
    (project / "cache.sqlite").write_bytes(b"sqlite artifact")
    (project / "too-large.txt").write_bytes(b"x" * 65)
    (project / "ignored-dir").mkdir()
    (project / "ignored-dir" / "nested.txt").write_text("ignored", encoding="utf-8")
    (project / ".codex").mkdir()
    (project / ".codex" / "credentials.json").write_text(secret_value, encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    os.symlink(outside, project / "outside-link")
    os.symlink(project / "safe.txt", project / "inside-link")
    data_root = project / ".mellowyak-data"
    store = SnapshotStore(data_root, "project-3", max_object_bytes=64)
    (data_root / "must-not-capture.txt").write_text(secret_value, encoding="utf-8")

    result = store.capture(project, snapshot_id="filtered", created_at=FIXED_TIME)

    included = set(_entry_map(result))
    assert included == {".gitignore", ".mellowyakignore", "safe.txt"}
    exclusions = {item.relative_path: item.reason for item in result.manifest.exclusions}
    assert exclusions[".env"] == "sensitive"
    assert exclusions["ignored.txt"] == "ignore_rule"
    assert exclusions["private.yak-secret"] == "ignore_rule"
    assert exclusions["outside-link"] == "symlink"
    assert exclusions["inside-link"] == "symlink"
    assert exclusions["cache.sqlite"] == "excluded_artifact"
    assert exclusions["too-large.txt"] == "oversized"
    assert exclusions[".mellowyak-data"] == "mellowyak_data_root"
    assert exclusions[".codex"] == "private_provider_directory"
    assert result.manifest.sensitive_count == 1
    manifest_text = Path(data_root / result.manifest_path).read_text(encoding="utf-8")
    assert secret_value not in manifest_text
    for object_file in store.objects_root.glob("*/*"):
        assert secret_value.encode() not in object_file.read_bytes()


def test_corruption_is_detected_and_blocks_materialization(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("print('ok')\n", encoding="utf-8")
    store = SnapshotStore(tmp_path / "data", "project-4")
    result = store.capture(project, snapshot_id="good", created_at=FIXED_TIME)
    digest = result.manifest.entries[0].blob_sha256
    store.object_path(digest).write_bytes(b"corrupt")

    verification = store.verify_snapshot("good")
    assert not verification.valid
    assert verification.manifest_valid
    assert verification.corrupt_objects == (digest,)
    with pytest.raises(SnapshotStoreError, match="SNAPSHOT_OBJECT_CORRUPT"):
        store.materialize("good", tmp_path / "restored", live_project_root=project)
    assert not (tmp_path / "restored").exists()


def test_materialization_is_byte_exact_and_never_mutates_live_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "nested").mkdir(parents=True)
    (project / "nested" / "payload.bin").write_bytes(bytes(range(256)))
    executable = project / "run.sh"
    executable.write_bytes(b"#!/bin/sh\nprintf ok\n")
    executable.chmod(0o751)
    before = _source_signature(project)
    store = SnapshotStore(tmp_path / "data", "project-5")
    result = store.capture(project, snapshot_id="restore-me", created_at=FIXED_TIME)

    destination = tmp_path / "materialized" / "restore-me"
    restored = store.materialize("restore-me", destination, live_project_root=project)

    assert restored == destination
    assert _source_signature(project) == before
    assert set(_source_signature(restored)) == set(before)
    for relative, (_, digest) in before.items():
        assert hashlib.sha256((restored / relative).read_bytes()).hexdigest() == digest
    assert stat.S_IMODE((restored / "run.sh").stat().st_mode) == 0o751
    assert result.manifest.entries
    with pytest.raises(
        SnapshotStoreError,
        match="SNAPSHOT_MATERIALIZATION_OVERLAPS_LIVE_PROJECT",
    ):
        store.materialize(
            "restore-me",
            project / "unsafe-restore",
            live_project_root=project,
        )
    assert _source_signature(project) == before


def test_reference_mark_and_sweep_never_deletes_manifest_or_external_references(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "source.txt").write_text("referenced", encoding="utf-8")
    store = SnapshotStore(tmp_path / "data", "project-6")
    snapshot = store.capture(project, snapshot_id="kept", created_at=FIXED_TIME)
    manifest_digest = snapshot.manifest.entries[0].blob_sha256
    orphan = store.put_bytes(b"orphan object")
    external = store.put_bytes(b"external evidence reference")

    marked = store.mark_referenced_objects(additional_references=(external.sha256,))
    assert marked == frozenset({manifest_digest, external.sha256})
    preview = store.sweep_unreferenced(marked, dry_run=True)
    assert preview.swept_objects == 1
    assert store.object_path(orphan.sha256).exists()

    swept = store.sweep_unreferenced(marked, dry_run=False)
    assert swept.swept_objects == 1
    assert not store.object_path(orphan.sha256).exists()
    assert store.object_path(manifest_digest).exists()
    assert store.object_path(external.sha256).exists()
    assert store.verify_snapshot("kept").valid

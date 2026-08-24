from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.db.models import (
    BehaviorVersion,
    Project,
    ProjectChange,
    ProtectedBehavior,
    RegressionFinding,
    SignalClassification,
    SnapshotObject,
    SourceSnapshot,
)
from mellowyak_engine.episodes import EpisodeService
from mellowyak_engine.repair_workspace import RepairWorkspaceService
from mellowyak_engine.snapshots import SnapshotService, SnapshotStore
from mellowyak_engine.storage.paths import StoragePaths

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
FIXED_TIME = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


@dataclass
class IntegrationRig:
    paths: StoragePaths
    database: LocalDatabase
    project_root: Path
    events: LocalEventBus
    snapshots: SnapshotService
    episodes: EpisodeService
    repairs: RepairWorkspaceService


@pytest.fixture
def rig(tmp_path: Path) -> IntegrationRig:
    project_root = tmp_path / "plain-non-git-project"
    project_root.mkdir()
    assert not (project_root / ".git").exists()
    paths = StoragePaths.create(tmp_path / "mellowyak-data")
    database = LocalDatabase(paths)
    assert database.migrate() == "0007_runtime_snapshot_probe_foundation"
    with database.sessions.begin() as session:
        session.add(
            Project(
                id=PROJECT_ID,
                display_name="Deterministic non-Git fixture",
                root_path=str(project_root),
                canonical_root_path=str(project_root.resolve()),
                repository_root_path=None,
                created_at=FIXED_TIME,
                updated_at=FIXED_TIME,
                monitoring_mode="paused",
                monitoring_status="paused",
                current_branch=None,
                current_head_sha=None,
                current_worktree_fingerprint=None,
                detection_payload_json="{}",
            )
        )
    events = LocalEventBus()
    snapshots = SnapshotService(database.sessions, paths.root, events)
    episodes = EpisodeService(database.sessions, events)
    episodes.bind_snapshot_callback(snapshots.create)
    fixture = IntegrationRig(
        paths=paths,
        database=database,
        project_root=project_root,
        events=events,
        snapshots=snapshots,
        episodes=episodes,
        repairs=RepairWorkspaceService(
            database.sessions,
            paths.root,
            events,
            opener=lambda _path: "TEST_NO_OPEN",
        ),
    )
    try:
        yield fixture
    finally:
        episodes.stop_all()
        database.engine.dispose()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _source_signature(root: Path) -> dict[str, tuple[int, int, int, str]]:
    result: dict[str, tuple[int, int, int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            metadata = path.stat()
            result[path.relative_to(root).as_posix()] = (
                stat.S_IMODE(metadata.st_mode),
                metadata.st_size,
                metadata.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return result


def _entry_digest(snapshot: dict[str, Any], relative_path: str) -> str:
    return str(
        next(
            entry["blob_digest"]
            for entry in snapshot["entries"]
            if entry["relative_path"] == relative_path
        )
    )


def test_database_snapshot_service_supports_non_git_identity_and_safe_materialization(
    rig: IntegrationRig,
) -> None:
    (rig.project_root / "app.py").write_text("print('non-git')\n", encoding="utf-8")
    binary = bytes(range(256))
    (rig.project_root / "asset.bin").write_bytes(binary)
    secret = "PHASE7_SECRET_MUST_NEVER_PERSIST_9D3A"
    (rig.project_root / ".env").write_text(f"TOKEN={secret}\n", encoding="utf-8")
    source_before = _source_signature(rig.project_root)

    snapshot = rig.snapshots.create(PROJECT_ID, creation_reason="INITIAL")

    assert snapshot["reused"] is False
    assert snapshot["git_anchor"] == {}
    assert snapshot["source_identity"]["schema"] == "mellowyak.source_identity.v2"
    assert snapshot["source_identity"]["kind"] == "SNAPSHOT"
    assert snapshot["source_identity"]["head_sha"] is None
    assert snapshot["source_identity"]["branch"] is None
    identity_payload = {
        key: value
        for key, value in snapshot["source_identity"].items()
        if key not in {"schema", "digest"}
    }
    assert (
        snapshot["source_identity"]["digest"]
        == hashlib.sha256(_canonical(identity_payload)).hexdigest()
    )
    assert {entry["relative_path"] for entry in snapshot["entries"]} == {
        "app.py",
        "asset.bin",
    }
    assert snapshot["sensitive_count"] == 1
    assert snapshot["verification"]["valid"] is True
    with rig.database.sessions() as session:
        row = session.get(SourceSnapshot, snapshot["id"])
        project = session.get(Project, PROJECT_ID)
        objects = session.scalars(
            select(SnapshotObject).where(SnapshotObject.project_id == PROJECT_ID)
        ).all()
        assert row is not None
        assert json.loads(row.source_identity_json) == snapshot["source_identity"]
        assert project is not None and project.current_head_sha is None
        assert project.current_worktree_fingerprint == snapshot["manifest_digest"]
        assert len(objects) == 2
        assert all(
            (rig.paths.root / item.object_relative_path)
            .resolve()
            .is_relative_to(rig.paths.root.resolve())
            for item in objects
        )

    materialized = rig.snapshots.materialize(PROJECT_ID, snapshot["id"])
    materialized_root = rig.paths.root / materialized["relative_path"]
    assert materialized["verified"] is True
    assert materialized["live_project_modified"] is False
    assert (materialized_root / "app.py").read_bytes() == (rig.project_root / "app.py").read_bytes()
    assert (materialized_root / "asset.bin").read_bytes() == binary
    assert not (materialized_root / ".env").exists()
    assert _source_signature(rig.project_root) == source_before
    assert secret.encode() not in rig.paths.sqlite_file.read_bytes()


def test_episode_coalescing_creates_one_snapshot_then_reuses_unchanged_state(
    rig: IntegrationRig,
) -> None:
    (rig.project_root / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    (rig.project_root / "package.json").write_text("{}\n", encoding="utf-8")
    baseline = rig.snapshots.create(PROJECT_ID, creation_reason="INITIAL")
    (rig.project_root / "app.py").write_text("VERSION = 2\n", encoding="utf-8")
    (rig.project_root / "package.json").write_text('{"scripts":{}}\n', encoding="utf-8")

    first_id = rig.episodes.record(PROJECT_ID, ["app.py", "package.json", "deleted.txt"])
    second_id = rig.episodes.record(PROJECT_ID, ["app.py"])
    assert first_id is not None and second_id == first_id
    first_episode = rig.episodes.stabilize_now(PROJECT_ID)

    assert first_episode is not None
    assert first_episode["status"] == "STABILIZED"
    assert first_episode["base_snapshot_id"] == baseline["id"]
    assert first_episode["resulting_snapshot_id"] != baseline["id"]
    assert first_episode["event_count"] == 4
    assert first_episode["modified_paths"] == ["app.py", "package.json"]
    assert first_episode["deleted_paths"] == ["deleted.txt"]
    assert first_episode["dependency_changes"] == ["package.json"]
    episode_snapshot = rig.snapshots.get(PROJECT_ID, first_episode["resulting_snapshot_id"])
    assert episode_snapshot["source_identity"]["episode_id"] == first_episode["id"]
    assert episode_snapshot["source_identity"]["parent_snapshot_id"] == baseline["id"]

    unchanged_episode_id = rig.episodes.record(PROJECT_ID, ["app.py"])
    unchanged_episode = rig.episodes.stabilize_now(PROJECT_ID)
    assert unchanged_episode is not None
    assert unchanged_episode["id"] == unchanged_episode_id
    assert unchanged_episode["status"] == "STABILIZED"
    assert unchanged_episode["base_snapshot_id"] == episode_snapshot["id"]
    assert unchanged_episode["resulting_snapshot_id"] == episode_snapshot["id"]
    with rig.database.sessions() as session:
        assert (
            session.scalar(
                select(func.count(SourceSnapshot.id)).where(SourceSnapshot.project_id == PROJECT_ID)
            )
            == 2
        )
        signals = session.scalars(
            select(SignalClassification)
            .where(SignalClassification.project_id == PROJECT_ID)
            .order_by(SignalClassification.created_at)
        ).all()
        regressions = session.scalar(
            select(func.count(RegressionFinding.id)).where(
                RegressionFinding.project_id == PROJECT_ID
            )
        )
        assert [item.state for item in signals] == ["WATCH", "WATCH"]
        assert regressions == 0


def test_repair_workspace_excludes_secrets_and_cannot_mutate_live_project(
    rig: IntegrationRig,
) -> None:
    safe_file = rig.project_root / "service.py"
    safe_file.write_text("RESULT = 'working'\n", encoding="utf-8")
    secret = "REPAIR_SECRET_MUST_NOT_LEAK_E71C"
    (rig.project_root / ".env").write_text(f"PASSWORD={secret}\n", encoding="utf-8")
    source_before = _source_signature(rig.project_root)
    snapshot = rig.snapshots.create(PROJECT_ID, creation_reason="INCIDENT")
    now = datetime.now(UTC)
    behavior_id = "22222222-2222-4222-8222-222222222222"
    version_id = "33333333-3333-4333-8333-333333333333"
    regression_id = "44444444-4444-4444-8444-444444444444"
    with rig.database.sessions.begin() as session:
        change = session.scalars(
            select(ProjectChange)
            .where(ProjectChange.project_id == PROJECT_ID)
            .order_by(ProjectChange.revision.desc())
            .limit(1)
        ).one()
        session.add(
            ProtectedBehavior(
                id=behavior_id,
                project_id=PROJECT_ID,
                stable_key="fixture-behavior",
                display_name="Fixture behavior",
                lifecycle_state="ACTIVE",
                current_version_id=version_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            BehaviorVersion(
                id=version_id,
                behavior_id=behavior_id,
                project_id=PROJECT_ID,
                version_number=1,
                title="Fixture behavior",
                description="Deterministic repair fixture",
                expected_outcome="The fixture remains working",
                criticality="HIGH",
                content_digest="a" * 64,
                source_revision_json=json.dumps(snapshot["source_identity"]),
                created_at=now,
            )
        )
        session.flush()
        session.add(
            RegressionFinding(
                id=regression_id,
                project_id=PROJECT_ID,
                change_id=change.id,
                behavior_id=behavior_id,
                behavior_version_id=version_id,
                status="CONFIRMED",
                decision_reason="A previously accepted check diverged reproducibly.",
                source_identity_json=json.dumps(snapshot["source_identity"]),
                created_at=now,
            )
        )

    repair = rig.repairs.create(PROJECT_ID, regression_id)
    workspace = rig.paths.root / repair["relative_path"]

    assert repair["status"] == "READY"
    assert repair["snapshot_id"] == snapshot["id"]
    assert (workspace / "current" / "service.py").read_bytes() == safe_file.read_bytes()
    assert not (workspace / "current" / ".env").exists()
    assert _source_signature(rig.project_root) == source_before
    for path in workspace.rglob("*"):
        if path.is_file() and not path.is_symlink():
            assert secret.encode() not in path.read_bytes()
    source_manifest = json.loads((workspace / "source-manifest.json").read_text(encoding="utf-8"))
    assert ".env" not in {entry["relative_path"] for entry in source_manifest["entries"]}

    (workspace / "current" / "service.py").write_text("RESULT = 'repair draft'\n", encoding="utf-8")
    assert safe_file.read_text(encoding="utf-8") == "RESULT = 'working'\n"
    assert _source_signature(rig.project_root) == source_before


def test_cleanup_sweeps_only_unreferenced_snapshot_objects(rig: IntegrationRig) -> None:
    version_file = rig.project_root / "version.txt"
    common_file = rig.project_root / "common.txt"
    common_file.write_text("shared forever\n", encoding="utf-8")
    version_file.write_text("version A\n", encoding="utf-8")
    pinned = rig.snapshots.create(PROJECT_ID, creation_reason="KNOWN_GOOD")
    version_file.write_text("version B\n", encoding="utf-8")
    removable = rig.snapshots.create(PROJECT_ID, creation_reason="EPISODE")
    version_file.write_text("version C\n", encoding="utf-8")
    current = rig.snapshots.create(PROJECT_ID, creation_reason="EPISODE")
    pinned_digest = _entry_digest(pinned, "version.txt")
    removable_digest = _entry_digest(removable, "version.txt")
    current_digest = _entry_digest(current, "version.txt")
    common_digest = _entry_digest(current, "common.txt")
    store = SnapshotStore(rig.paths.root, PROJECT_ID)
    with rig.database.sessions.begin() as session:
        project = session.get(Project, PROJECT_ID)
        assert project is not None
        project.snapshot_retention_days = 30
        project.snapshot_soft_cap_bytes = 5 * 1024 * 1024 * 1024
        session.get(SourceSnapshot, pinned["id"]).created_at = datetime.now(UTC) - timedelta(
            days=90
        )
        session.get(SourceSnapshot, removable["id"]).created_at = datetime.now(UTC) - timedelta(
            days=60
        )
        session.get(SourceSnapshot, current["id"]).created_at = datetime.now(UTC)

    result = rig.snapshots.cleanup(PROJECT_ID)

    assert result["removed_snapshots"] == 1
    assert result["swept_objects"] >= 1
    assert store.object_path(pinned_digest).is_file()
    assert not store.object_path(removable_digest).exists()
    assert store.object_path(current_digest).is_file()
    assert store.object_path(common_digest).is_file()
    assert store.verify_snapshot(pinned["id"]).valid
    assert store.verify_snapshot(current["id"]).valid
    with rig.database.sessions() as session:
        remaining = set(
            session.scalars(
                select(SourceSnapshot.id).where(SourceSnapshot.project_id == PROJECT_ID)
            ).all()
        )
        assert remaining == {pinned["id"], current["id"]}

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Project,
    ProjectChange,
    RuntimeProfile,
    RuntimeProfileVersion,
    SnapshotMilestone,
    SnapshotObject,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.db.models import (
    SnapshotEntry as SnapshotEntryRow,
)
from mellowyak_engine.snapshots.store import SnapshotStore
from mellowyak_engine.source_identity import source_identity


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


class SnapshotServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SnapshotService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events

    def _project(self, session: Session, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise SnapshotServiceError("PROJECT_NOT_FOUND")
        return project

    def _store(self, project_id: str) -> SnapshotStore:
        return SnapshotStore(self.data_root, project_id)

    @staticmethod
    def _latest(session: Session, project_id: str) -> SourceSnapshot | None:
        return session.scalars(
            select(SourceSnapshot)
            .where(SourceSnapshot.project_id == project_id)
            .order_by(SourceSnapshot.created_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _runtime_fingerprints(session: Session, project_id: str) -> tuple[str, ...]:
        rows = session.execute(
            select(RuntimeProfile, RuntimeProfileVersion)
            .join(
                RuntimeProfileVersion,
                RuntimeProfileVersion.id == RuntimeProfile.current_version_id,
            )
            .where(RuntimeProfile.project_id == project_id)
        ).all()
        return tuple(
            sorted(
                f"{profile.id}:{version.dependency_fingerprint or version.id}"
                for profile, version in rows
            )
        )

    def create(
        self,
        project_id: str,
        episode_id: str | None = None,
        creation_reason: str = "MANUAL_SAVE_POINT",
    ) -> dict[str, Any]:
        with self.sessions() as session:
            project = self._project(session, project_id)
            project_root = Path(project.canonical_root_path or project.root_path)
            previous = self._latest(session, project_id)
            parent_id = previous.id if previous else None
            runtime_fingerprints = self._runtime_fingerprints(session, project_id)
            git_available = bool(project.current_head_sha)
            git_anchor = (
                {
                    "branch": project.current_branch,
                    "head_sha": project.current_head_sha,
                    "worktree_fingerprint": project.current_worktree_fingerprint,
                }
                if git_available
                else None
            )
        self.events.publish("snapshot_capture_started", project_id, {"episode_id": episode_id})
        store = self._store(project_id)
        result = store.capture(
            project_root,
            parent_snapshot_id=parent_id,
            episode_id=episode_id,
            creation_reason=creation_reason,
            source_identity={
                "schema": "mellowyak.source_identity.capture.v1",
                "kind": "GIT_AND_SNAPSHOT" if git_available else "SNAPSHOT",
                "parent_snapshot_id": parent_id,
                "episode_id": episode_id,
            },
            git_anchor=git_anchor,
            runtime_profile_fingerprints=runtime_fingerprints,
        )
        manifest = result.manifest
        if previous is not None:
            try:
                previous_manifest = store.load_manifest(previous.id)
                prior_content = [entry.to_dict() for entry in previous_manifest.entries]
                current_content = [entry.to_dict() for entry in manifest.entries]
                if prior_content == current_content:
                    store.manifest_path(manifest.snapshot_id).unlink(missing_ok=True)
                    response = self.get(project_id, previous.id)
                    response["reused"] = True
                    self.events.publish(
                        "snapshot_reused",
                        project_id,
                        {"snapshot_id": previous.id, "episode_id": episode_id},
                    )
                    return response
            except Exception:
                # Corrupt previous state must not suppress a fresh verified snapshot.
                pass
        identity = source_identity(
            snapshot_id=manifest.snapshot_id,
            manifest_digest=manifest.manifest_digest,
            episode_id=episode_id,
            parent_snapshot_id=parent_id,
            git_available=git_available,
            head_sha=git_anchor.get("head_sha") if git_anchor else None,
            branch=git_anchor.get("branch") if git_anchor else None,
            worktree_fingerprint=git_anchor.get("worktree_fingerprint") if git_anchor else None,
        ).public_dict()
        exclusion_reasons = [item.reason for item in manifest.exclusions]
        with self.sessions.begin() as session:
            self._project(session, project_id)
            row = SourceSnapshot(
                id=manifest.snapshot_id,
                project_id=project_id,
                parent_snapshot_id=parent_id,
                episode_id=episode_id,
                manifest_digest=manifest.manifest_digest,
                creation_reason=creation_reason[:40],
                source_identity_json=_json(identity),
                git_anchor_json=_json(git_anchor or {}),
                runtime_profile_fingerprints_json=_json(list(runtime_fingerprints)),
                included_count=result.stats.included_files,
                excluded_count=result.stats.excluded_files,
                sensitive_count=result.stats.sensitive_files,
                unsupported_count=sum(
                    reason in {"excluded_artifact", "oversized", "non_regular"}
                    for reason in exclusion_reasons
                ),
                logical_bytes=result.stats.logical_bytes,
                physical_bytes_added=result.stats.physical_bytes_created,
                reused_bytes=result.stats.deduplicated_bytes,
                pinned=creation_reason in {"KNOWN_GOOD", "BASELINE", "INCIDENT"},
                integrity_status="VERIFIED",
                created_at=datetime.fromisoformat(manifest.created_at.replace("Z", "+00:00")),
            )
            session.add(row)
            # SQLite cannot infer insert order without an ORM relationship. Persist the
            # manifest row before entries that reference it.
            session.flush()
            object_counts: dict[str, int] = {}
            for entry in manifest.entries:
                object_counts[entry.blob_sha256] = object_counts.get(entry.blob_sha256, 0) + 1
                session.add(
                    SnapshotEntryRow(
                        id=str(uuid.uuid4()),
                        snapshot_id=row.id,
                        project_id=project_id,
                        relative_path=entry.relative_path,
                        blob_digest=entry.blob_sha256,
                        byte_size=entry.byte_size,
                        file_mode=entry.file_mode,
                        executable=entry.executable,
                        classification=entry.classification,
                    )
                )
            for digest, count in object_counts.items():
                object_row = session.scalars(
                    select(SnapshotObject).where(
                        SnapshotObject.project_id == project_id,
                        SnapshotObject.digest == digest,
                    )
                ).first()
                if object_row is None:
                    path = store.object_path(digest)
                    object_row = SnapshotObject(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        digest=digest,
                        byte_size=path.stat().st_size,
                        object_relative_path=path.relative_to(self.data_root).as_posix(),
                        reference_count=count,
                        integrity_status="VERIFIED",
                        created_at=datetime.now(UTC),
                        last_verified_at=datetime.now(UTC),
                    )
                    session.add(object_row)
                else:
                    object_row.reference_count += count
                    object_row.integrity_status = "VERIFIED"
                    object_row.last_verified_at = datetime.now(UTC)
            project = session.get(Project, project_id)
            if project is not None:
                project.current_worktree_fingerprint = (
                    project.current_worktree_fingerprint
                    if project.current_head_sha
                    else manifest.manifest_digest
                )
                project.updated_at = datetime.now(UTC)
                logical_key = hashlib.sha256(
                    f"{project_id}\0snapshot\0{manifest.manifest_digest}".encode()
                ).hexdigest()
                change = session.scalars(
                    select(ProjectChange).where(
                        ProjectChange.project_id == project_id,
                        ProjectChange.logical_key == logical_key,
                    )
                ).first()
                if change is None:
                    episode = session.get(SourceEpisode, episode_id) if episode_id else None
                    changed_paths = sorted(
                        set(
                            (_load(episode.added_paths_json, []) if episode else [])
                            + (_load(episode.modified_paths_json, []) if episode else [])
                            + (_load(episode.deleted_paths_json, []) if episode else [])
                        )
                    )
                    revision = (
                        int(
                            session.scalar(
                                select(func.max(ProjectChange.revision)).where(
                                    ProjectChange.project_id == project_id
                                )
                            )
                            or 0
                        )
                        + 1
                    )
                    now = datetime.now(UTC)
                    session.add(
                        ProjectChange(
                            id=f"chg-{logical_key[:32]}",
                            project_id=project_id,
                            logical_key=logical_key,
                            change_kind="snapshot_episode",
                            revision=revision,
                            base_head_sha=project.current_head_sha,
                            head_sha=project.current_head_sha,
                            worktree_fingerprint=manifest.manifest_digest,
                            changed_paths_json=_json(changed_paths),
                            status="change_detected" if changed_paths else "no_changes",
                            created_at=now,
                            updated_at=now,
                        )
                    )
        response = self.get(project_id, manifest.snapshot_id)
        response["reused"] = False
        self.events.publish(
            "snapshot_created",
            project_id,
            {
                "snapshot_id": manifest.snapshot_id,
                "logical_bytes": result.stats.logical_bytes,
                "physical_bytes_added": result.stats.physical_bytes_created,
            },
        )
        return response

    @staticmethod
    def _summary(row: SourceSnapshot) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "parent_snapshot_id": row.parent_snapshot_id,
            "episode_id": row.episode_id,
            "manifest_digest": row.manifest_digest,
            "creation_reason": row.creation_reason,
            "source_identity": _load(row.source_identity_json, {}),
            "git_anchor": _load(row.git_anchor_json, {}),
            "included_count": row.included_count,
            "excluded_count": row.excluded_count,
            "sensitive_count": row.sensitive_count,
            "unsupported_count": row.unsupported_count,
            "logical_bytes": row.logical_bytes,
            "physical_bytes_added": row.physical_bytes_added,
            "reused_bytes": row.reused_bytes,
            "pinned": row.pinned,
            "integrity_status": row.integrity_status,
            "created_at": row.created_at.isoformat(),
        }

    def list(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.project_id == project_id)
                .order_by(SourceSnapshot.created_at.desc())
                .limit(min(max(limit, 1), 200))
            ).all()
            return [self._summary(row) for row in rows]

    def get(self, project_id: str, snapshot_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            self._project(session, project_id)
            row = session.get(SourceSnapshot, snapshot_id)
            if row is None or row.project_id != project_id:
                raise SnapshotServiceError("SNAPSHOT_NOT_FOUND")
            verification = self._store(project_id).verify_snapshot(snapshot_id)
            row.integrity_status = "VERIFIED" if verification.valid else "CORRUPT"
            entries = session.scalars(
                select(SnapshotEntryRow)
                .where(SnapshotEntryRow.snapshot_id == snapshot_id)
                .order_by(SnapshotEntryRow.relative_path)
            ).all()
            response = self._summary(row)
            response["runtime_profile_fingerprints"] = _load(
                row.runtime_profile_fingerprints_json, []
            )
            response["entries"] = [
                {
                    "relative_path": item.relative_path,
                    "blob_digest": item.blob_digest,
                    "byte_size": item.byte_size,
                    "file_mode": item.file_mode,
                    "executable": item.executable,
                    "symlink_target": item.symlink_target,
                    "classification": item.classification,
                }
                for item in entries
            ]
            response["verification"] = {
                "valid": verification.valid,
                "missing_objects": list(verification.missing_objects),
                "corrupt_objects": list(verification.corrupt_objects),
                "error_code": verification.error_code,
            }
            return response

    def pin(self, project_id: str, snapshot_id: str, pinned: bool) -> dict[str, Any]:
        with self.sessions.begin() as session:
            self._project(session, project_id)
            row = session.get(SourceSnapshot, snapshot_id)
            if row is None or row.project_id != project_id:
                raise SnapshotServiceError("SNAPSHOT_NOT_FOUND")
            if not pinned:
                milestone_count = session.scalar(
                    select(func.count(SnapshotMilestone.id)).where(
                        SnapshotMilestone.snapshot_id == snapshot_id,
                        SnapshotMilestone.pinned.is_(True),
                    )
                )
                if milestone_count:
                    raise SnapshotServiceError("SNAPSHOT_REFERENCED_BY_MILESTONE")
            row.pinned = pinned
        return self.get(project_id, snapshot_id)

    def materialize(self, project_id: str, snapshot_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = self._project(session, project_id)
            row = session.get(SourceSnapshot, snapshot_id)
            if row is None or row.project_id != project_id:
                raise SnapshotServiceError("SNAPSHOT_NOT_FOUND")
            project_root = Path(project.canonical_root_path or project.root_path)
        destination_id = str(uuid.uuid4())
        destination = self._store(project_id).materialized_root / destination_id
        self._store(project_id).materialize(
            snapshot_id,
            destination,
            live_project_root=project_root,
        )
        detail = self.get(project_id, snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "relative_path": destination.relative_to(self.data_root).as_posix(),
            "file_count": detail["included_count"],
            "logical_bytes": detail["logical_bytes"],
            "verified": detail["integrity_status"] == "VERIFIED",
            "live_project_modified": False,
        }

    def cleanup(self, project_id: str) -> dict[str, int]:
        """Conservative age/cap cleanup; referenced or current snapshots stay pinned."""
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            rows = session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.project_id == project_id)
                .order_by(SourceSnapshot.created_at.desc())
            ).all()
            total = sum(row.logical_bytes for row in rows)
            cutoff = datetime.now(UTC) - timedelta(days=project.snapshot_retention_days)
            removable: list[SourceSnapshot] = []
            for index, row in enumerate(rows):
                created = row.created_at.replace(tzinfo=row.created_at.tzinfo or UTC)
                over_age = created < cutoff
                over_cap = total > project.snapshot_soft_cap_bytes
                if index and not row.pinned and (over_age or over_cap):
                    removable.append(row)
                    total -= row.logical_bytes
            removed_ids: list[str] = []
            for row in removable:
                entries = session.scalars(
                    select(SnapshotEntryRow).where(SnapshotEntryRow.snapshot_id == row.id)
                ).all()
                for entry in entries:
                    if entry.blob_digest:
                        object_row = session.scalars(
                            select(SnapshotObject).where(
                                SnapshotObject.project_id == project_id,
                                SnapshotObject.digest == entry.blob_digest,
                            )
                        ).first()
                        if object_row:
                            object_row.reference_count = max(0, object_row.reference_count - 1)
                    session.delete(entry)
                removed_ids.append(row.id)
                session.delete(row)
        store = self._store(project_id)
        for snapshot_id in removed_ids:
            store.manifest_path(snapshot_id).unlink(missing_ok=True)
        marked = store.mark_referenced_objects()
        gc = store.sweep_unreferenced(marked, dry_run=False)
        with self.sessions.begin() as session:
            stale_objects = session.scalars(
                select(SnapshotObject).where(
                    SnapshotObject.project_id == project_id,
                    SnapshotObject.reference_count <= 0,
                )
            ).all()
            for object_row in stale_objects:
                if not store.object_path(object_row.digest).exists():
                    session.delete(object_row)
        return {
            "removed_snapshots": len(removed_ids),
            "swept_objects": gc.swept_objects,
            "swept_bytes": gc.swept_bytes,
        }

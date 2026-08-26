from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Project,
    RegressionFinding,
    RepairWorkspace,
    RepairWorkspaceItem,
    RuntimeProfile,
    RuntimeProfileVersion,
    SignalClassification,
    SnapshotMilestone,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.snapshots.store import SnapshotStore


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class RepairWorkspaceServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RepairWorkspaceService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
        opener: Callable[[str], str],
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self.opener = opener

    def _safe_path(self, project_id: str, workspace_id: str) -> Path:
        expected_root = (self.data_root / "projects" / project_id / "repair-workspaces").resolve(
            strict=False
        )
        path = (expected_root / workspace_id).resolve(strict=False)
        try:
            path.relative_to(expected_root)
        except ValueError as error:
            raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_PATH_INVALID") from error
        return path

    def create(self, project_id: str, regression_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None or project.archived_at is not None:
                raise RepairWorkspaceServiceError("PROJECT_NOT_FOUND")
            regression = session.get(RegressionFinding, regression_id)
            if regression is None or regression.project_id != project_id:
                raise RepairWorkspaceServiceError("REGRESSION_NOT_FOUND")
            signal = session.scalars(
                select(SignalClassification)
                .where(
                    SignalClassification.project_id == project_id,
                    SignalClassification.regression_id == regression_id,
                    SignalClassification.state == "CONFIRMED",
                )
                .order_by(SignalClassification.created_at.desc())
                .limit(1)
            ).first()
            snapshot = (
                session.get(SourceSnapshot, signal.snapshot_id)
                if signal and signal.snapshot_id
                else session.scalars(
                    select(SourceSnapshot)
                    .where(SourceSnapshot.project_id == project_id)
                    .order_by(SourceSnapshot.created_at.desc())
                    .limit(1)
                ).first()
            )
            if snapshot is None:
                raise RepairWorkspaceServiceError("SNAPSHOT_NOT_FOUND")
            milestone = session.scalars(
                select(SnapshotMilestone)
                .where(
                    SnapshotMilestone.project_id == project_id,
                    SnapshotMilestone.status == "ACCEPTED",
                )
                .order_by(SnapshotMilestone.created_at.desc())
                .limit(1)
            ).first()
            episode = (
                session.get(SourceEpisode, snapshot.episode_id) if snapshot.episode_id else None
            )
            project_root = Path(project.canonical_root_path or project.root_path)
            source_identity = json.loads(snapshot.source_identity_json)
            runtime_profile_versions = [
                row.id
                for row in session.scalars(
                    select(RuntimeProfileVersion)
                    .join(
                        RuntimeProfile,
                        RuntimeProfile.current_version_id == RuntimeProfileVersion.id,
                    )
                    .where(RuntimeProfile.project_id == project_id)
                ).all()
            ]
            runtime_versions = session.scalars(
                select(RuntimeProfileVersion)
                .join(
                    RuntimeProfile,
                    RuntimeProfile.current_version_id == RuntimeProfileVersion.id,
                )
                .where(RuntimeProfile.project_id == project_id)
            ).all()
            changed_paths = sorted(
                set(
                    (json.loads(episode.modified_paths_json) if episode else [])
                    + (json.loads(episode.added_paths_json) if episode else [])
                    + (json.loads(episode.deleted_paths_json) if episode else [])
                )
            )[:500]
        workspace_id = str(uuid.uuid4())
        workspace = self._safe_path(project_id, workspace_id)
        workspace.mkdir(parents=True, mode=0o700)
        (workspace / "evidence").mkdir(mode=0o700)
        (workspace / "references").mkdir(mode=0o700)
        store = SnapshotStore(self.data_root, project_id)
        manifest = store.load_manifest(snapshot.id)
        store.materialize(snapshot.id, workspace / "current", live_project_root=project_root)
        incident = {
            "schema": "mellowyak.repair_incident.v1",
            "project_id": project_id,
            "regression_id": regression_id,
            "signal_id": signal.id if signal else None,
            "snapshot_id": snapshot.id,
            "source_identity": source_identity,
            "known_good_milestone_id": milestone.id if milestone else None,
            "what_worked": milestone.display_name if milestone else None,
            "current_failure": regression.decision_reason,
            "changed_paths": changed_paths,
            "unknowns": ["ROOT_CAUSE_NOT_PROVEN"],
        }
        safe_manifest = {
            "schema": "mellowyak.repair_source_manifest.v1",
            "snapshot_id": snapshot.id,
            "manifest_digest": snapshot.manifest_digest,
            "included_count": snapshot.included_count,
            "logical_bytes": snapshot.logical_bytes,
            "entries": [entry.to_dict() for entry in manifest.entries],
        }
        executable_checks: list[dict[str, Any]] = []
        for version in runtime_versions:
            for definition in json.loads(version.test_definitions_json or "[]"):
                if not isinstance(definition, dict) or definition.get("type") != "TEST":
                    continue
                executable_checks.append(
                    {
                        "id": f"runtime-test-{version.id}",
                        "type": "PROCESS",
                        "requirement": "REQUIRED",
                        "executable": version.executable_reference,
                        "argv": json.loads(version.argv_json or "[]"),
                        "cwd": version.relative_working_directory,
                        "expected_exit_code": int(definition.get("expected_exit_code", 0)),
                        "stdout_contains": definition.get("stdout_contains"),
                    }
                )
        validation = {
            "schema": "mellowyak.validation_plan.v1",
            "required_rechecks": ["ORIGINAL_FAILED_CHECK", "IMPACT_SELECTED_CHECKS"],
            "checks": executable_checks,
            "automatic_apply": False,
            "live_project_write_allowed": False,
        }
        instructions = """# MellowYak Repair Workspace

This workspace is an isolated local copy. Do not modify the live project.

## KEEP

- Preserve behavior that still passes its required checks.
- Preserve sensitive-file exclusions and local-only boundaries.

## RESTORE

- Restore the expected behavior described in `incident.json`.
- Use the Last Known Good milestone as evidence, not as a blind file restore.

## Required approach

1. Read `incident.json` and `validation-plan.json`.
2. Inspect only the relevant paths in `current/`.
3. Do not blindly restore old files.
4. Re-run the original failed check and the impacted checks.
5. Record unknowns; do not claim an unproven root cause.

This workspace never applies changes back to the live project.
"""
        payloads = {
            "incident.json": _canonical(incident) + b"\n",
            "source-manifest.json": _canonical(safe_manifest) + b"\n",
            "validation-plan.json": _canonical(validation) + b"\n",
            "MELLOWYAK_REPAIR.md": instructions.encode(),
        }
        for name, content in payloads.items():
            path = workspace / name
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        payload_digests = {
            name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()
        }
        digest = hashlib.sha256(_canonical(payload_digests)).hexdigest()
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            row = RepairWorkspace(
                id=workspace_id,
                project_id=project_id,
                regression_id=regression_id,
                signal_id=signal.id if signal else None,
                snapshot_id=snapshot.id,
                workspace_relative_path=workspace.relative_to(self.data_root).as_posix(),
                manifest_digest=digest,
                base_manifest_digest=snapshot.manifest_digest,
                workspace_manifest_digest=snapshot.manifest_digest,
                runtime_profile_versions_json=json.dumps(sorted(runtime_profile_versions)),
                validation_policy_json=json.dumps(
                    {
                        "required": ["ORIGINAL_FAILED_CHECK", "IMPACT_SELECTED_CHECKS"],
                        "network": "NO_EXTERNAL_EGRESS",
                        "checks": executable_checks,
                    },
                    sort_keys=True,
                ),
                status="READY",
                created_at=now,
                last_change_at=now,
            )
            session.add(row)
            workspace_items = [
                "MELLOWYAK_REPAIR.md",
                "incident.json",
                "source-manifest.json",
                "validation-plan.json",
                "current",
                "evidence",
                "references",
            ]
            for ordinal, name in enumerate(workspace_items):
                session.add(
                    RepairWorkspaceItem(
                        id=str(uuid.uuid4()),
                        workspace_id=workspace_id,
                        ordinal=ordinal,
                        item_type="DIRECTORY" if "." not in name else "DOCUMENT",
                        relative_reference=name,
                        reason="REPAIR_WORKSPACE_REQUIRED_ITEM",
                    )
                )
        self.events.publish(
            "repair_workspace_created",
            project_id,
            {"workspace_id": workspace_id, "snapshot_id": snapshot.id},
        )
        return self.get(project_id, workspace_id)

    def get(self, project_id: str, workspace_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RepairWorkspace, workspace_id)
            if row is None or row.project_id != project_id:
                raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_NOT_FOUND")
            items = session.scalars(
                select(RepairWorkspaceItem)
                .where(RepairWorkspaceItem.workspace_id == workspace_id)
                .order_by(RepairWorkspaceItem.ordinal)
            ).all()
            path = self._safe_path(project_id, workspace_id)
            instructions_path = path / "MELLOWYAK_REPAIR.md"
            instructions = (
                instructions_path.read_text(encoding="utf-8")
                if instructions_path.is_file() and not instructions_path.is_symlink()
                else None
            )
            return {
                "id": row.id,
                "project_id": row.project_id,
                "regression_id": row.regression_id,
                "signal_id": row.signal_id,
                "snapshot_id": row.snapshot_id,
                "relative_path": row.workspace_relative_path,
                "manifest_digest": row.manifest_digest,
                "base_manifest_digest": row.base_manifest_digest,
                "workspace_manifest_digest": row.workspace_manifest_digest,
                "runtime_profile_versions": json.loads(row.runtime_profile_versions_json),
                "validation_policy": json.loads(row.validation_policy_json),
                "status": row.status,
                "instructions": instructions,
                "items": [
                    {
                        "ordinal": item.ordinal,
                        "item_type": item.item_type,
                        "relative_reference": item.relative_reference,
                        "reason": item.reason,
                    }
                    for item in items
                ],
                "created_at": row.created_at.isoformat(),
                "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
            }

    def open(self, project_id: str, workspace_id: str, target: str) -> dict[str, str]:
        row = self.get(project_id, workspace_id)
        if row["deleted_at"] is not None:
            raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_DELETED")
        if target not in {"FOLDER", "DEFAULT_EDITOR", "TERMINAL"}:
            raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_OPEN_TARGET_INVALID")
        path = self._safe_path(project_id, workspace_id)
        method = self.opener(str(path))
        return {"status": "OPENED", "method": method, "target": target}

    def delete(self, project_id: str, workspace_id: str) -> dict[str, str]:
        path = self._safe_path(project_id, workspace_id)
        with self.sessions.begin() as session:
            row = session.get(RepairWorkspace, workspace_id)
            if row is None or row.project_id != project_id:
                raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_NOT_FOUND")
            if row.deleted_at is not None:
                return {"status": "DELETED"}
            row.status = "DELETED"
            row.deleted_at = datetime.now(UTC)
        if path.exists():
            if path.is_symlink():
                raise RepairWorkspaceServiceError("REPAIR_WORKSPACE_PATH_UNSAFE")
            shutil.rmtree(path)
        self.events.publish("repair_workspace_deleted", project_id, {"workspace_id": workspace_id})
        return {"status": "DELETED"}

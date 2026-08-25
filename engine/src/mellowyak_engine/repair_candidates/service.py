from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    RepairCandidate,
    RepairCandidateFile,
    RepairWorkspace,
    SourceSnapshot,
)
from mellowyak_engine.repair_candidates.diff import bounded_unified_diff
from mellowyak_engine.repair_candidates.manifest import (
    CandidateManifestError,
    WorkspaceEntry,
    safe_join,
    scan_workspace,
)
from mellowyak_engine.snapshots.store import SnapshotStore, canonical_json


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class RepairCandidateServiceError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        super().__init__(code)


class RepairCandidateService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events

    def _workspace(self, session: Session, project_id: str, workspace_id: str) -> RepairWorkspace:
        row = session.get(RepairWorkspace, workspace_id)
        if row is None or row.project_id != project_id or row.deleted_at is not None:
            raise RepairCandidateServiceError("REPAIR_WORKSPACE_NOT_FOUND")
        return row

    def _workspace_root(self, workspace: RepairWorkspace) -> Path:
        root = (self.data_root / workspace.workspace_relative_path / "current").resolve(strict=True)
        expected = (
            self.data_root / "projects" / workspace.project_id / "repair-workspaces"
        ).resolve()
        try:
            root.relative_to(expected)
        except ValueError as error:
            raise RepairCandidateServiceError("REPAIR_WORKSPACE_PATH_INVALID") from error
        return root

    def _changes(self, workspace: RepairWorkspace) -> tuple[list[dict[str, Any]], str, int, int]:
        store = SnapshotStore(self.data_root, workspace.project_id)
        base_manifest = store.load_manifest(workspace.snapshot_id)
        base = {entry.relative_path: entry for entry in base_manifest.entries}
        current_entries, workspace_digest = scan_workspace(self._workspace_root(workspace))
        current = {entry.relative_path: entry for entry in current_entries}
        deleted = set(base) - set(current)
        added = set(current) - set(base)
        modified = {
            path
            for path in set(base) & set(current)
            if base[path].blob_sha256 != current[path].digest
            or base[path].file_mode != current[path].file_mode
        }
        rename_pairs: list[tuple[str, str]] = []
        by_deleted_digest: dict[str, list[str]] = {}
        for path in deleted:
            by_deleted_digest.setdefault(base[path].blob_sha256, []).append(path)
        for destination in sorted(added):
            matches = by_deleted_digest.get(current[destination].digest, [])
            if len(matches) == 1:
                source = matches[0]
                rename_pairs.append((source, destination))
                deleted.remove(source)
                added.remove(destination)
                by_deleted_digest[current[destination].digest] = []
        rows: list[dict[str, Any]] = []
        for source, destination in rename_pairs:
            item = current[destination]
            rows.append(self._row(item, "RENAME", base[source].blob_sha256, source, destination))
        for path in sorted(deleted):
            entry = base[path]
            rows.append(
                {
                    "relative_path": path,
                    "operation": "DELETE",
                    "base_digest": entry.blob_sha256,
                    "candidate_digest": None,
                    "expected_live_digest": entry.blob_sha256,
                    "byte_size": 0,
                    "classification": "binary" if entry.classification == "binary" else "text",
                    "file_mode": entry.file_mode,
                    "executable": entry.executable,
                    "rename_source": None,
                    "rename_destination": None,
                    "validation_eligible": True,
                    "apply_eligible": True,
                    "exclusion_reason": None,
                    "warning_state": None,
                }
            )
        for path in sorted(added):
            rows.append(self._row(current[path], "ADD", None, None, None))
        for path in sorted(modified):
            base_entry = base[path]
            current_entry = current[path]
            operation = (
                "MODE_CHANGE" if base_entry.blob_sha256 == current_entry.digest else "MODIFY"
            )
            rows.append(self._row(current_entry, operation, base_entry.blob_sha256, None, None))
        rows.sort(key=lambda item: (str(item["relative_path"]), str(item["operation"])))
        for row in rows:
            if row["classification"] == "binary":
                row["apply_eligible"] = False
                row["warning_state"] = "BINARY_ADVANCED_CONFIRMATION_REQUIRED"
        if len(rows) > 250:
            raise RepairCandidateServiceError("CANDIDATE_FILE_COUNT_EXCEEDED")
        logical_bytes = sum(int(row["byte_size"]) for row in rows)
        if logical_bytes > 64 * 1024 * 1024:
            raise RepairCandidateServiceError("CANDIDATE_TOTAL_BYTES_EXCEEDED")
        return (
            rows,
            workspace_digest,
            logical_bytes,
            sum(row["classification"] == "binary" for row in rows),
        )

    @staticmethod
    def _row(
        entry: WorkspaceEntry,
        operation: str,
        base_digest: str | None,
        rename_source: str | None,
        rename_destination: str | None,
    ) -> dict[str, Any]:
        return {
            "relative_path": entry.relative_path,
            "operation": operation,
            "base_digest": base_digest,
            "candidate_digest": entry.digest,
            "expected_live_digest": base_digest,
            "byte_size": entry.byte_size,
            "classification": entry.classification,
            "file_mode": entry.file_mode,
            "executable": entry.executable,
            "rename_source": rename_source,
            "rename_destination": rename_destination,
            "validation_eligible": True,
            "apply_eligible": True,
            "exclusion_reason": None,
            "warning_state": None,
        }

    def create(self, project_id: str, workspace_id: str) -> dict[str, Any]:
        try:
            with self.sessions() as session:
                workspace = self._workspace(session, project_id, workspace_id)
                changes, workspace_digest, logical_bytes, binary_count = self._changes(workspace)
                revision = (
                    int(
                        session.scalar(
                            select(func.max(RepairCandidate.revision)).where(
                                RepairCandidate.workspace_id == workspace_id
                            )
                        )
                        or 0
                    )
                    + 1
                )
                source_snapshot = session.get(SourceSnapshot, workspace.snapshot_id)
                if source_snapshot is None:
                    raise RepairCandidateServiceError("SNAPSHOT_NOT_FOUND")
                base_digest = source_snapshot.manifest_digest
        except CandidateManifestError as error:
            raise RepairCandidateServiceError(error.code, error.path) from error
        candidate_payload = [
            {key: value for key, value in row.items() if key not in {"warning_state"}}
            for row in changes
        ]
        candidate_digest = hashlib.sha256(canonical_json(candidate_payload)).hexdigest()
        candidate_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        warnings = sorted({row["warning_state"] for row in changes if row["warning_state"]})
        limitations = ["BINARY_CHANGES_BLOCKED"] if binary_count else []
        with self.sessions.begin() as session:
            workspace = self._workspace(session, project_id, workspace_id)
            previous = session.scalars(
                select(RepairCandidate).where(
                    RepairCandidate.workspace_id == workspace_id,
                    RepairCandidate.state.in_(["VALIDATED", "VALIDATING"]),
                )
            ).all()
            for item in previous:
                item.state = "STALE"
                item.updated_at = now
            row = RepairCandidate(
                id=candidate_id,
                project_id=project_id,
                workspace_id=workspace_id,
                revision=revision,
                state="DRAFT",
                base_manifest_digest=base_digest,
                workspace_manifest_digest=workspace_digest,
                candidate_digest=candidate_digest,
                source_snapshot_id=workspace.snapshot_id,
                file_count=len(changes),
                logical_bytes=logical_bytes,
                binary_count=binary_count,
                warnings_json=_json(warnings),
                limitations_json=_json(limitations),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            for ordinal, item in enumerate(changes):
                session.add(
                    RepairCandidateFile(
                        id=str(uuid.uuid4()),
                        candidate_id=candidate_id,
                        ordinal=ordinal,
                        **item,
                    )
                )
            workspace.workspace_manifest_digest = workspace_digest
            workspace.last_change_at = now
            workspace.status = "CHANGED" if changes else "READY"
        self.events.publish(
            "candidate_created",
            project_id,
            {"candidate_id": candidate_id, "workspace_id": workspace_id, "revision": revision},
        )
        return self.get(project_id, candidate_id)

    def refresh(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            candidate = session.get(RepairCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            workspace_id = candidate.workspace_id
        result = self.create(project_id, workspace_id)
        self.events.publish("candidate_refreshed", project_id, {"candidate_id": result["id"]})
        return result

    def get(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RepairCandidate, candidate_id)
            if row is None or row.project_id != project_id:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            files = session.scalars(
                select(RepairCandidateFile)
                .where(RepairCandidateFile.candidate_id == candidate_id)
                .order_by(RepairCandidateFile.ordinal)
            ).all()
            return {
                "id": row.id,
                "project_id": row.project_id,
                "workspace_id": row.workspace_id,
                "revision": row.revision,
                "state": row.state,
                "base_manifest_digest": row.base_manifest_digest,
                "workspace_manifest_digest": row.workspace_manifest_digest,
                "candidate_digest": row.candidate_digest,
                "source_snapshot_id": row.source_snapshot_id,
                "file_count": row.file_count,
                "logical_bytes": row.logical_bytes,
                "binary_count": row.binary_count,
                "warnings": json.loads(row.warnings_json),
                "limitations": json.loads(row.limitations_json),
                "files": [
                    {
                        "ordinal": item.ordinal,
                        "relative_path": item.relative_path,
                        "operation": item.operation,
                        "base_digest": item.base_digest,
                        "candidate_digest": item.candidate_digest,
                        "expected_live_digest": item.expected_live_digest,
                        "byte_size": item.byte_size,
                        "classification": item.classification,
                        "file_mode": item.file_mode,
                        "executable": item.executable,
                        "rename_source": item.rename_source,
                        "rename_destination": item.rename_destination,
                        "validation_eligible": item.validation_eligible,
                        "apply_eligible": item.apply_eligible,
                        "exclusion_reason": item.exclusion_reason,
                        "warning_state": item.warning_state,
                        "excluded": item.excluded,
                    }
                    for item in files
                ],
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }

    def exclude(self, project_id: str, candidate_id: str, paths: list[str]) -> dict[str, Any]:
        with self.sessions.begin() as session:
            candidate = session.get(RepairCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            if candidate.state != "DRAFT":
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_IMMUTABLE")
            rows = session.scalars(
                select(RepairCandidateFile).where(
                    RepairCandidateFile.candidate_id == candidate_id,
                    RepairCandidateFile.relative_path.in_(paths),
                )
            ).all()
            for row in rows:
                row.excluded = True
                row.apply_eligible = False
                row.exclusion_reason = "USER_EXCLUDED"
        return self.get(project_id, candidate_id)

    def restore_workspace_file(
        self, project_id: str, candidate_id: str, relative_path: str
    ) -> dict[str, Any]:
        with self.sessions() as session:
            candidate = session.get(RepairCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            if candidate.state not in {"DRAFT", "VALIDATION_FAILED", "STALE"}:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_IMMUTABLE")
            workspace = self._workspace(session, project_id, candidate.workspace_id)
            file_row = session.scalars(
                select(RepairCandidateFile).where(
                    RepairCandidateFile.candidate_id == candidate_id,
                    RepairCandidateFile.relative_path == relative_path,
                )
            ).first()
            if file_row is None:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_FILE_NOT_FOUND")
            root = self._workspace_root(workspace)
            target = safe_join(root, relative_path)
            base_digest = file_row.base_digest
            mode = file_row.file_mode
        if base_digest is None:
            target.unlink(missing_ok=True)
        else:
            source = SnapshotStore(self.data_root, project_id).object_path(base_digest)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.mellowyak-restore-{uuid.uuid4().hex}")
            content = source.read_bytes()
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode or 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            target.chmod(stat.S_IMODE(mode or 0o600))
        return self.refresh(project_id, candidate_id)

    def diff(self, project_id: str, candidate_id: str, relative_path: str) -> dict[str, Any]:
        with self.sessions() as session:
            candidate = session.get(RepairCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            workspace = self._workspace(session, project_id, candidate.workspace_id)
            item = session.scalars(
                select(RepairCandidateFile).where(
                    RepairCandidateFile.candidate_id == candidate_id,
                    RepairCandidateFile.relative_path == relative_path,
                )
            ).first()
            if item is None:
                raise RepairCandidateServiceError("REPAIR_CANDIDATE_FILE_NOT_FOUND")
            root = self._workspace_root(workspace)
        before = (
            SnapshotStore(self.data_root, project_id).object_path(item.base_digest).read_bytes()
            if item.base_digest
            else b""
        )
        target = safe_join(root, relative_path)
        after = target.read_bytes() if target.is_file() and not target.is_symlink() else b""
        return {
            "candidate_id": candidate_id,
            "relative_path": relative_path,
            **bounded_unified_diff(
                before,
                after,
                before_name=f"base/{relative_path}",
                after_name=f"candidate/{relative_path}",
            ),
        }

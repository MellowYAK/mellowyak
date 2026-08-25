from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.db.models import RepairWorkspace
from mellowyak_engine.repair_candidates.manifest import (
    PRIVATE_SEGMENTS,
    normalize_relative,
    safe_join,
)
from mellowyak_engine.scanning.policy import is_sensitive_path
from mellowyak_engine.snapshots.store import canonical_json


class PortableRepairError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PortableRepairService:
    MAX_FILES = 100
    MAX_BYTES = 32 * 1024 * 1024

    def __init__(self, sessions: sessionmaker[Session], data_root: Path) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()

    def export(
        self,
        project_id: str,
        workspace_id: str,
        selected_paths: list[str],
    ) -> dict[str, Any]:
        with self.sessions() as session:
            workspace = session.get(RepairWorkspace, workspace_id)
            if workspace is None or workspace.project_id != project_id or workspace.deleted_at:
                raise PortableRepairError("REPAIR_WORKSPACE_NOT_FOUND")
            workspace_root = (self.data_root / workspace.workspace_relative_path).resolve(
                strict=True
            )
        unique = sorted(set(normalize_relative(path) for path in selected_paths))
        if len(unique) > self.MAX_FILES:
            raise PortableRepairError("PORTABLE_PACKAGE_FILE_LIMIT")
        export_id = str(uuid.uuid4())
        destination = self.data_root / "projects" / project_id / "portable-repairs" / export_id
        relevant = destination / "current-relevant-files"
        relevant.mkdir(parents=True, mode=0o700)
        manifest_items: list[dict[str, Any]] = []
        total = 0
        current_root = workspace_root / "current"
        for relative in unique:
            parts = PurePosixPath(relative).parts
            if is_sensitive_path(relative) or any(part in PRIVATE_SEGMENTS for part in parts):
                raise PortableRepairError("PORTABLE_PACKAGE_SENSITIVE_PATH_REJECTED")
            source = safe_join(current_root, relative, allow_missing=False)
            if source.is_symlink() or not source.is_file():
                raise PortableRepairError("PORTABLE_PACKAGE_FILE_INVALID")
            total += source.stat().st_size
            if total > self.MAX_BYTES:
                raise PortableRepairError("PORTABLE_PACKAGE_SIZE_LIMIT")
            target = relevant.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target, follow_symlinks=False)
            content_digest = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest_items.append(
                {
                    "relative_path": relative,
                    "byte_size": target.stat().st_size,
                    "sha256": content_digest,
                }
            )
        documents = {
            "MELLOWYAK_REPAIR.md": (
                b"# Portable MellowYak Repair Package\n\n"
                b"This package may not be independently runnable.\n\n"
                b"Preserve the requested new behavior.\n"
                b"Restore the failed protected behavior.\n"
                b"Do not blindly copy historical files.\n"
                b"Make the smallest relevant change.\n"
                b"Return changes to the isolated Repair Workspace.\n"
                b"Do not modify the live project.\n"
            ),
            "repair-context.json": canonical_json(
                {"schema": "mellowyak.portable_repair.v1", "workspace_id": workspace_id}
            )
            + b"\n",
            "validation-plan.json": (workspace_root / "validation-plan.json").read_bytes(),
            "unknowns.json": canonical_json(["PACKAGE_MAY_NOT_BE_INDEPENDENTLY_RUNNABLE"]) + b"\n",
            "manifest.json": canonical_json(
                {
                    "schema": "mellowyak.portable_repair_manifest.v1",
                    "workspace_id": workspace_id,
                    "items": manifest_items,
                    "absolute_paths_included": False,
                    "source_uploaded": False,
                }
            )
            + b"\n",
        }
        for name, content in documents.items():
            path = destination / name
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        return {
            "id": export_id,
            "workspace_id": workspace_id,
            "relative_path": destination.relative_to(self.data_root).as_posix(),
            "file_count": len(manifest_items),
            "logical_bytes": total,
            "uploaded": False,
        }

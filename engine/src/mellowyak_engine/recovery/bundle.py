from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.db.models import RecoveryBundle
from mellowyak_engine.snapshots.store import canonical_json


def _redact(value: Any, data_root: Path, project_root: Path) -> Any:
    if isinstance(value, dict):
        return {str(key): _redact(item, data_root, project_root) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, data_root, project_root) for item in value]
    if isinstance(value, str):
        return value.replace(str(data_root), "<DATA_ROOT>").replace(
            str(project_root), "<PROJECT_ROOT>"
        )
    return value


class RecoveryBundleService:
    FILES = (
        "transaction.json",
        "journal.json",
        "safety-snapshot.json",
        "affected-paths.json",
        "current-digests.json",
        "expected-digests.json",
        "diagnostics.json",
    )

    def __init__(self, sessions: sessionmaker[Session], data_root: Path) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()

    def create(
        self,
        project_id: str,
        transaction_id: str,
        project_root: Path,
        payloads: dict[str, Any],
    ) -> dict[str, Any]:
        bundle_id = str(uuid.uuid4())
        root = self.data_root / "projects" / project_id / "recovery-bundles" / bundle_id
        root.mkdir(parents=True, mode=0o700)
        readme = (
            "# MellowYak Recovery Bundle\n\n"
            "Manual recovery is required. Stop automated writes and inspect the exact "
            "affected paths.\n"
        )
        content_by_name: dict[str, bytes] = {"RECOVERY_README.md": readme.encode()}
        for name in self.FILES:
            safe = _redact(payloads.get(name, {}), self.data_root, project_root)
            content_by_name[name] = canonical_json(safe) + b"\n"
        for name, content in content_by_name.items():
            path = root / name
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        digest = hashlib.sha256(
            canonical_json(
                {
                    name: hashlib.sha256(content).hexdigest()
                    for name, content in content_by_name.items()
                }
            )
        ).hexdigest()
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.add(
                RecoveryBundle(
                    id=bundle_id,
                    transaction_id=transaction_id,
                    project_id=project_id,
                    relative_path=root.relative_to(self.data_root).as_posix(),
                    manifest_digest=digest,
                    status="READY",
                    created_at=now,
                )
            )
        return {
            "id": bundle_id,
            "transaction_id": transaction_id,
            "relative_path": root.relative_to(self.data_root).as_posix(),
            "manifest_digest": digest,
            "status": "READY",
            "created_at": now.isoformat(),
        }

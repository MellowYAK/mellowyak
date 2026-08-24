from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_PROJECT_BYTES = 500 * 1024 * 1024


class EvidenceStoreError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class StoredObject:
    sha256: str
    size_bytes: int
    object_key: str
    deduplicated: bool


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    @staticmethod
    def _project_segment(project_id: str) -> str:
        if not project_id or any(char not in "0123456789abcdef-" for char in project_id.lower()):
            raise EvidenceStoreError("EVIDENCE_PROJECT_ID_INVALID")
        return project_id.lower()

    def _project_root(self, project_id: str) -> Path:
        return self.root / self._project_segment(project_id)

    def _object_path(self, project_id: str, sha256: str) -> Path:
        if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
            raise EvidenceStoreError("EVIDENCE_SHA256_INVALID")
        return self._project_root(project_id) / "objects" / sha256[:2] / sha256

    def put(self, project_id: str, content: bytes) -> StoredObject:
        size = len(content)
        if size == 0 or size > MAX_ARTIFACT_BYTES:
            raise EvidenceStoreError("EVIDENCE_ARTIFACT_SIZE_INVALID")
        digest = hashlib.sha256(content).hexdigest()
        target = self._object_path(project_id, digest)
        object_key = target.relative_to(self.root).as_posix()
        if target.is_file():
            if self.verify(project_id, digest):
                return StoredObject(digest, size, object_key, True)
            raise EvidenceStoreError("EVIDENCE_OBJECT_HASH_MISMATCH")
        current_size = sum(
            item.stat().st_size
            for item in (self._project_root(project_id) / "objects").glob("*/*")
            if item.is_file() and not item.is_symlink()
        )
        if current_size + size > MAX_PROJECT_BYTES:
            raise EvidenceStoreError("EVIDENCE_PROJECT_LIMIT_EXCEEDED")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle, temporary_name = tempfile.mkstemp(prefix=".evidence-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                raise EvidenceStoreError("EVIDENCE_WRITE_VERIFICATION_FAILED")
            os.replace(temporary, target)
            target.chmod(0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredObject(digest, size, object_key, False)

    def read(self, project_id: str, sha256: str) -> bytes:
        path = self._object_path(project_id, sha256)
        if path.is_symlink() or not path.is_file():
            raise EvidenceStoreError("EVIDENCE_OBJECT_NOT_FOUND")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != sha256:
            raise EvidenceStoreError("EVIDENCE_OBJECT_HASH_MISMATCH")
        return content

    def verify(self, project_id: str, sha256: str) -> bool:
        try:
            self.read(project_id, sha256)
        except EvidenceStoreError:
            return False
        return True

    def delete(self, project_id: str, sha256: str) -> None:
        path = self._object_path(project_id, sha256)
        if path.is_symlink():
            raise EvidenceStoreError("EVIDENCE_SYMLINK_REJECTED")
        path.unlink(missing_ok=True)

    def bundle_manifest_path(self, project_id: str, bundle_id: str) -> Path:
        if not bundle_id or any(char not in "0123456789abcdef-" for char in bundle_id.lower()):
            raise EvidenceStoreError("EVIDENCE_BUNDLE_ID_INVALID")
        return self._project_root(project_id) / "bundles" / bundle_id / "manifest.json"

    def write_manifest(self, project_id: str, bundle_id: str, content: bytes) -> str:
        target = self.bundle_manifest_path(project_id, bundle_id)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        digest = hashlib.sha256(content).hexdigest()
        handle, temporary_name = tempfile.mkstemp(prefix=".manifest-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            target.chmod(0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return digest

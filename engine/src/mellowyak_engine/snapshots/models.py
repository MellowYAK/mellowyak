from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StoredSourceObject:
    sha256: str
    size_bytes: int
    object_key: str
    deduplicated: bool


@dataclass(frozen=True)
class SnapshotEntry:
    relative_path: str
    blob_sha256: str
    byte_size: int
    file_mode: int
    executable: bool
    classification: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "blob_sha256": self.blob_sha256,
            "byte_size": self.byte_size,
            "file_mode": self.file_mode,
            "executable": self.executable,
            "classification": self.classification,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SnapshotEntry:
        return cls(
            relative_path=str(value["relative_path"]),
            blob_sha256=str(value["blob_sha256"]),
            byte_size=int(value["byte_size"]),
            file_mode=int(value["file_mode"]),
            executable=bool(value["executable"]),
            classification=str(value["classification"]),
        )


@dataclass(frozen=True)
class SnapshotExclusion:
    relative_path: str
    reason: str
    byte_size: int | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "relative_path": self.relative_path,
            "reason": self.reason,
        }
        if self.byte_size is not None:
            result["byte_size"] = self.byte_size
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SnapshotExclusion:
        size = value.get("byte_size")
        return cls(
            relative_path=str(value["relative_path"]),
            reason=str(value["reason"]),
            byte_size=None if size is None else int(size),
        )


@dataclass(frozen=True)
class SnapshotManifest:
    schema_version: int
    snapshot_id: str
    project_id: str
    parent_snapshot_id: str | None
    manifest_digest: str
    episode_id: str | None
    creation_reason: str
    source_identity: dict[str, Any]
    git_anchor: dict[str, Any] | None
    entries: tuple[SnapshotEntry, ...]
    exclusions: tuple[SnapshotExclusion, ...]
    excluded_count: int
    sensitive_count: int
    runtime_profile_fingerprints: tuple[str, ...]
    created_at: str

    def digest_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "project_id": self.project_id,
            "parent_snapshot_id": self.parent_snapshot_id,
            "episode_id": self.episode_id,
            "creation_reason": self.creation_reason,
            "source_identity": self.source_identity,
            "git_anchor": self.git_anchor,
            "entries": [entry.to_dict() for entry in self.entries],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
            "excluded_count": self.excluded_count,
            "sensitive_count": self.sensitive_count,
            "runtime_profile_fingerprints": list(self.runtime_profile_fingerprints),
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, object]:
        result = self.digest_payload()
        result["manifest_digest"] = self.manifest_digest
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SnapshotManifest:
        git_anchor = value.get("git_anchor")
        source_identity = value.get("source_identity", {})
        return cls(
            schema_version=int(value["schema_version"]),
            snapshot_id=str(value["snapshot_id"]),
            project_id=str(value["project_id"]),
            parent_snapshot_id=(
                None
                if value.get("parent_snapshot_id") is None
                else str(value["parent_snapshot_id"])
            ),
            manifest_digest=str(value["manifest_digest"]),
            episode_id=None if value.get("episode_id") is None else str(value["episode_id"]),
            creation_reason=str(value["creation_reason"]),
            source_identity=dict(source_identity),
            git_anchor=None if git_anchor is None else dict(git_anchor),
            entries=tuple(SnapshotEntry.from_dict(dict(item)) for item in value["entries"]),
            exclusions=tuple(
                SnapshotExclusion.from_dict(dict(item)) for item in value.get("exclusions", [])
            ),
            excluded_count=int(value["excluded_count"]),
            sensitive_count=int(value["sensitive_count"]),
            runtime_profile_fingerprints=tuple(value.get("runtime_profile_fingerprints", [])),
            created_at=str(value["created_at"]),
        )


@dataclass(frozen=True)
class SnapshotCaptureStats:
    included_files: int
    excluded_files: int
    sensitive_files: int
    logical_bytes: int
    physical_objects_created: int
    physical_bytes_created: int
    deduplicated_objects: int
    deduplicated_bytes: int


@dataclass(frozen=True)
class SnapshotResult:
    manifest: SnapshotManifest
    manifest_path: str
    stats: SnapshotCaptureStats


@dataclass(frozen=True)
class SnapshotVerification:
    snapshot_id: str
    manifest_valid: bool
    objects_valid: bool
    missing_objects: tuple[str, ...] = ()
    corrupt_objects: tuple[str, ...] = ()
    error_code: str | None = None

    @property
    def valid(self) -> bool:
        return self.manifest_valid and self.objects_valid


@dataclass(frozen=True)
class GarbageCollectionStats:
    marked_objects: int
    retained_objects: int
    swept_objects: int
    swept_bytes: int
    skipped_entries: int
    dry_run: bool

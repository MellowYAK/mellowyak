from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from mellowyak_engine.scanning.policy import (
    DEFAULT_EXCLUDED_DIRS,
    EXCLUDED_EXTENSIONS,
    build_ignore_spec,
    is_generated_path,
    is_sensitive_path,
)
from mellowyak_engine.snapshots.errors import SnapshotStoreError
from mellowyak_engine.snapshots.models import (
    GarbageCollectionStats,
    SnapshotCaptureStats,
    SnapshotEntry,
    SnapshotExclusion,
    SnapshotManifest,
    SnapshotResult,
    SnapshotVerification,
    StoredSourceObject,
)

SNAPSHOT_SCHEMA_VERSION = 1
DEFAULT_MAX_OBJECT_BYTES = 10 * 1024 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 64 * 1024 * 1024
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_PRIVATE_DIRS = frozenset(
    {".aws", ".azure", ".claude", ".codex", ".cursor", ".gnupg", ".ssh"}
)


def canonical_json(value: object) -> bytes:
    """Encode a manifest payload identically across runs and supported platforms."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise SnapshotStoreError("SNAPSHOT_MANIFEST_VALUE_INVALID") from error


def _digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_segment(value: str, code: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value) or value in {".", ".."}:
        raise SnapshotStoreError(code)
    return value


def _validate_digest(value: str) -> str:
    if not _DIGEST.fullmatch(value):
        raise SnapshotStoreError("SNAPSHOT_SHA256_INVALID")
    return value


def _relative_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _normalized_relative(value: str) -> str:
    if "\\" in value:
        raise SnapshotStoreError("SNAPSHOT_ENTRY_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise SnapshotStoreError("SNAPSHOT_ENTRY_PATH_INVALID")
    normalized = path.as_posix()
    if normalized != value:
        raise SnapshotStoreError("SNAPSHOT_ENTRY_PATH_INVALID")
    return normalized


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


class SnapshotStore:
    """Filesystem-only content-addressed source snapshot storage.

    The store never writes to ``project_root``. Database reference tracking is deliberately
    outside this class: callers pass external reference digests into the conservative GC API.
    """

    def __init__(
        self,
        data_root: Path,
        project_id: str,
        *,
        max_object_bytes: int = DEFAULT_MAX_OBJECT_BYTES,
    ) -> None:
        if max_object_bytes <= 0:
            raise SnapshotStoreError("SNAPSHOT_MAX_OBJECT_SIZE_INVALID")
        self.data_root = data_root.expanduser().resolve()
        self.project_id = _validate_segment(project_id, "SNAPSHOT_PROJECT_ID_INVALID").lower()
        self.max_object_bytes = max_object_bytes
        self.project_store = self.data_root / "projects" / self.project_id
        self.objects_root = self.project_store / "source-objects"
        self.manifests_root = self.project_store / "source-manifests"
        self.materialized_root = self.project_store / "materialized"
        for directory in (
            self.data_root,
            self.project_store,
            self.objects_root,
            self.manifests_root,
            self.materialized_root,
        ):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if directory.is_symlink():
                raise SnapshotStoreError("SNAPSHOT_STORAGE_SYMLINK_REJECTED")

    def object_path(self, digest: str) -> Path:
        digest = _validate_digest(digest)
        return self.objects_root / digest[:2] / digest

    def manifest_path(self, snapshot_id: str) -> Path:
        snapshot_id = _validate_segment(snapshot_id, "SNAPSHOT_ID_INVALID")
        return self.manifests_root / f"{snapshot_id}.json"

    def _temporary_object(self) -> tuple[int, Path]:
        self.objects_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, name = tempfile.mkstemp(prefix=".source-object-", dir=self.objects_root)
        return descriptor, Path(name)

    def _finish_object(
        self,
        temporary: Path,
        *,
        digest: str,
        size_bytes: int,
    ) -> StoredSourceObject:
        target = self.object_path(digest)
        key = target.relative_to(self.data_root).as_posix()
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.is_symlink():
            raise SnapshotStoreError("SNAPSHOT_OBJECT_SYMLINK_REJECTED")
        if target.exists():
            if not target.is_file() or not self.verify_object(digest, expected_size=size_bytes):
                raise SnapshotStoreError("SNAPSHOT_OBJECT_CORRUPT", digest)
            temporary.unlink(missing_ok=True)
            return StoredSourceObject(digest, size_bytes, key, True)
        os.replace(temporary, target)
        target.chmod(0o600)
        _fsync_directory(target.parent)
        if not self.verify_object(digest, expected_size=size_bytes):
            raise SnapshotStoreError("SNAPSHOT_OBJECT_WRITE_VERIFICATION_FAILED", digest)
        return StoredSourceObject(digest, size_bytes, key, False)

    def put_bytes(self, content: bytes) -> StoredSourceObject:
        """Store a bounded object directly, primarily for imported local evidence."""

        if len(content) > self.max_object_bytes:
            raise SnapshotStoreError("SNAPSHOT_OBJECT_TOO_LARGE")
        digest = _digest_bytes(content)
        target = self.object_path(digest)
        key = target.relative_to(self.data_root).as_posix()
        if target.exists():
            if target.is_symlink() or not self.verify_object(digest, expected_size=len(content)):
                raise SnapshotStoreError("SNAPSHOT_OBJECT_CORRUPT", digest)
            return StoredSourceObject(digest, len(content), key, True)
        descriptor, temporary = self._temporary_object()
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if _digest_bytes(temporary.read_bytes()) != digest:
                raise SnapshotStoreError("SNAPSHOT_OBJECT_WRITE_VERIFICATION_FAILED")
            return self._finish_object(temporary, digest=digest, size_bytes=len(content))
        finally:
            temporary.unlink(missing_ok=True)

    def _put_source_file(
        self, source: Path, initial_stat: os.stat_result
    ) -> tuple[StoredSourceObject, bool]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            source_descriptor = os.open(source, flags)
        except OSError as error:
            raise SnapshotStoreError("SNAPSHOT_SOURCE_OPEN_FAILED") from error
        temporary_descriptor, temporary = self._temporary_object()
        digest = hashlib.sha256()
        size_bytes = 0
        binary = False
        try:
            with (
                os.fdopen(source_descriptor, "rb", closefd=True) as source_stream,
                os.fdopen(temporary_descriptor, "wb", closefd=True) as output,
            ):
                opened_stat = os.fstat(source_stream.fileno())
                if not stat.S_ISREG(opened_stat.st_mode):
                    raise SnapshotStoreError("SNAPSHOT_SOURCE_NOT_REGULAR")
                if (
                    opened_stat.st_dev != initial_stat.st_dev
                    or opened_stat.st_ino != initial_stat.st_ino
                ):
                    raise SnapshotStoreError("SNAPSHOT_SOURCE_CHANGED_DURING_CAPTURE")
                while chunk := source_stream.read(_COPY_CHUNK_BYTES):
                    size_bytes += len(chunk)
                    if size_bytes > self.max_object_bytes:
                        raise SnapshotStoreError("SNAPSHOT_OBJECT_TOO_LARGE")
                    if b"\0" in chunk:
                        binary = True
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
                final_stat = os.fstat(source_stream.fileno())
                if (
                    final_stat.st_dev != opened_stat.st_dev
                    or final_stat.st_ino != opened_stat.st_ino
                    or final_stat.st_size != opened_stat.st_size
                    or final_stat.st_mtime_ns != opened_stat.st_mtime_ns
                    or size_bytes != opened_stat.st_size
                ):
                    raise SnapshotStoreError("SNAPSHOT_SOURCE_CHANGED_DURING_CAPTURE")
            object_row = self._finish_object(
                temporary,
                digest=digest.hexdigest(),
                size_bytes=size_bytes,
            )
            return object_row, binary
        finally:
            temporary.unlink(missing_ok=True)

    def _data_root_relative_to(self, project_root: Path) -> PurePosixPath | None:
        if _relative_is_within(project_root, self.data_root):
            raise SnapshotStoreError("SNAPSHOT_PROJECT_INSIDE_DATA_ROOT")
        try:
            relative = self.data_root.relative_to(project_root)
        except ValueError:
            return None
        return PurePosixPath(relative.as_posix())

    def _iter_source(
        self, project_root: Path
    ) -> Iterator[tuple[Path | None, str, os.stat_result | None, str | None]]:
        ignore = build_ignore_spec(project_root)
        data_relative = self._data_root_relative_to(project_root)
        for current, directories, files in os.walk(project_root, topdown=True, followlinks=False):
            current_path = Path(current)
            try:
                current_resolved = current_path.resolve(strict=True)
            except OSError as error:
                raise SnapshotStoreError("SNAPSHOT_SOURCE_TRAVERSAL_FAILED") from error
            if not _relative_is_within(current_resolved, project_root):
                raise SnapshotStoreError("SNAPSHOT_SOURCE_ESCAPE_REJECTED")
            relative_dir = current_path.relative_to(project_root).as_posix()
            if relative_dir == ".":
                relative_dir = ""
            retained: list[str] = []
            for directory in sorted(directories):
                relative = f"{relative_dir}/{directory}".lstrip("/")
                candidate = current_path / directory
                pure_relative = PurePosixPath(relative)
                reason: str | None = None
                if directory in _PROVIDER_PRIVATE_DIRS:
                    reason = "private_provider_directory"
                elif data_relative is not None and pure_relative == data_relative:
                    reason = "mellowyak_data_root"
                elif directory in DEFAULT_EXCLUDED_DIRS:
                    reason = "excluded_directory"
                elif ignore.match_file(f"{relative}/"):
                    reason = "ignore_rule"
                elif candidate.is_symlink():
                    reason = "symlink"
                if reason is None:
                    retained.append(directory)
                else:
                    yield None, relative, None, reason
            directories[:] = retained
            for filename in sorted(files):
                source = current_path / filename
                relative = f"{relative_dir}/{filename}".lstrip("/")
                if ignore.match_file(relative):
                    yield None, relative, None, "ignore_rule"
                    continue
                if is_sensitive_path(relative):
                    yield None, relative, None, "sensitive"
                    continue
                try:
                    source_stat = source.lstat()
                except OSError:
                    yield None, relative, None, "unreadable"
                    continue
                if stat.S_ISLNK(source_stat.st_mode):
                    yield None, relative, source_stat, "symlink"
                    continue
                if not stat.S_ISREG(source_stat.st_mode):
                    yield None, relative, source_stat, "non_regular"
                    continue
                if source.suffix.lower() in EXCLUDED_EXTENSIONS or is_generated_path(relative):
                    yield None, relative, source_stat, "excluded_artifact"
                    continue
                if source_stat.st_size > self.max_object_bytes:
                    yield None, relative, source_stat, "oversized"
                    continue
                yield source, relative, source_stat, None

    def capture(
        self,
        project_root: Path,
        *,
        snapshot_id: str | None = None,
        parent_snapshot_id: str | None = None,
        episode_id: str | None = None,
        creation_reason: str = "manual",
        source_identity: Mapping[str, Any] | None = None,
        git_anchor: Mapping[str, Any] | None = None,
        runtime_profile_fingerprints: Iterable[str] = (),
        created_at: datetime | None = None,
    ) -> SnapshotResult:
        """Capture one immutable full-tree manifest without writing into the project."""

        try:
            root = project_root.expanduser().resolve(strict=True)
        except OSError as error:
            raise SnapshotStoreError("SNAPSHOT_PROJECT_ROOT_NOT_FOUND") from error
        if not root.is_dir():
            raise SnapshotStoreError("SNAPSHOT_PROJECT_ROOT_NOT_DIRECTORY")
        if snapshot_id is None:
            snapshot_id = str(uuid.uuid4())
        snapshot_id = _validate_segment(snapshot_id, "SNAPSHOT_ID_INVALID")
        if parent_snapshot_id is not None:
            parent_snapshot_id = _validate_segment(parent_snapshot_id, "SNAPSHOT_ID_INVALID")
            self.load_manifest(parent_snapshot_id)
        if self.manifest_path(snapshot_id).exists():
            raise SnapshotStoreError("SNAPSHOT_ALREADY_EXISTS")
        timestamp = created_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            raise SnapshotStoreError("SNAPSHOT_CREATED_AT_TIMEZONE_REQUIRED")
        created_at_value = timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")

        entries: list[SnapshotEntry] = []
        exclusions: list[SnapshotExclusion] = []
        physical_objects = 0
        physical_bytes = 0
        deduplicated_objects = 0
        deduplicated_bytes = 0
        logical_bytes = 0
        sensitive_count = 0
        for source, relative, source_stat, exclusion_reason in self._iter_source(root):
            relative = _normalized_relative(relative)
            if exclusion_reason is not None:
                if exclusion_reason == "sensitive":
                    sensitive_count += 1
                exclusions.append(
                    SnapshotExclusion(
                        relative,
                        exclusion_reason,
                        None if source_stat is None else source_stat.st_size,
                    )
                )
                continue
            if source is None or source_stat is None:
                raise SnapshotStoreError("SNAPSHOT_SOURCE_ENTRY_INVALID")
            stored, binary = self._put_source_file(source, source_stat)
            mode = stat.S_IMODE(source_stat.st_mode)
            entries.append(
                SnapshotEntry(
                    relative_path=relative,
                    blob_sha256=stored.sha256,
                    byte_size=stored.size_bytes,
                    file_mode=mode,
                    executable=bool(mode & 0o111),
                    classification="binary" if binary else "source",
                )
            )
            logical_bytes += stored.size_bytes
            if stored.deduplicated:
                deduplicated_objects += 1
                deduplicated_bytes += stored.size_bytes
            else:
                physical_objects += 1
                physical_bytes += stored.size_bytes

        entries.sort(key=lambda item: item.relative_path)
        exclusions.sort(key=lambda item: (item.relative_path, item.reason))
        manifest = SnapshotManifest(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            snapshot_id=snapshot_id,
            project_id=self.project_id,
            parent_snapshot_id=parent_snapshot_id,
            manifest_digest="",
            episode_id=episode_id,
            creation_reason=creation_reason,
            source_identity=dict(source_identity or {"kind": "filesystem"}),
            git_anchor=None if git_anchor is None else dict(git_anchor),
            entries=tuple(entries),
            exclusions=tuple(exclusions),
            excluded_count=len(exclusions),
            sensitive_count=sensitive_count,
            runtime_profile_fingerprints=tuple(sorted(set(runtime_profile_fingerprints))),
            created_at=created_at_value,
        )
        manifest = replace(
            manifest,
            manifest_digest=_digest_bytes(canonical_json(manifest.digest_payload())),
        )
        manifest_path = self._write_manifest(manifest)
        written_manifest = self.load_manifest(snapshot_id)
        if written_manifest != manifest:
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_WRITE_VERIFICATION_FAILED")
        return SnapshotResult(
            manifest=manifest,
            manifest_path=manifest_path.relative_to(self.data_root).as_posix(),
            stats=SnapshotCaptureStats(
                included_files=len(entries),
                excluded_files=len(exclusions),
                sensitive_files=sensitive_count,
                logical_bytes=logical_bytes,
                physical_objects_created=physical_objects,
                physical_bytes_created=physical_bytes,
                deduplicated_objects=deduplicated_objects,
                deduplicated_bytes=deduplicated_bytes,
            ),
        )

    def _write_manifest(self, manifest: SnapshotManifest) -> Path:
        target = self.manifest_path(manifest.snapshot_id)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.exists() or target.is_symlink():
            raise SnapshotStoreError("SNAPSHOT_ALREADY_EXISTS")
        content = canonical_json(manifest.to_dict()) + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(prefix=".source-manifest-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            target.chmod(0o600)
            _fsync_directory(target.parent)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def load_manifest(self, snapshot_id: str) -> SnapshotManifest:
        path = self.manifest_path(snapshot_id)
        if path.is_symlink() or not path.is_file():
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_NOT_FOUND")
        try:
            if path.stat().st_size > _MAX_MANIFEST_BYTES:
                raise SnapshotStoreError("SNAPSHOT_MANIFEST_TOO_LARGE")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise SnapshotStoreError("SNAPSHOT_MANIFEST_INVALID")
            manifest = SnapshotManifest.from_dict(value)
        except SnapshotStoreError:
            raise
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_INVALID") from error
        if manifest.schema_version != SNAPSHOT_SCHEMA_VERSION:
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_VERSION_UNSUPPORTED")
        if manifest.snapshot_id != snapshot_id or manifest.project_id != self.project_id:
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_IDENTITY_MISMATCH")
        _validate_digest(manifest.manifest_digest)
        expected = _digest_bytes(canonical_json(manifest.digest_payload()))
        if expected != manifest.manifest_digest:
            raise SnapshotStoreError("SNAPSHOT_MANIFEST_HASH_MISMATCH")
        paths: set[str] = set()
        previous_path = ""
        for entry in manifest.entries:
            relative = _normalized_relative(entry.relative_path)
            _validate_digest(entry.blob_sha256)
            if entry.byte_size < 0 or entry.byte_size > self.max_object_bytes:
                raise SnapshotStoreError("SNAPSHOT_ENTRY_SIZE_INVALID")
            if relative in paths or (previous_path and relative < previous_path):
                raise SnapshotStoreError("SNAPSHOT_ENTRY_ORDER_INVALID")
            paths.add(relative)
            previous_path = relative
        if manifest.excluded_count != len(manifest.exclusions):
            raise SnapshotStoreError("SNAPSHOT_EXCLUSION_COUNT_MISMATCH")
        for exclusion in manifest.exclusions:
            _normalized_relative(exclusion.relative_path)
        return manifest

    def verify_object(self, digest: str, *, expected_size: int | None = None) -> bool:
        path = self.object_path(digest)
        if path.is_symlink() or not path.is_file():
            return False
        sha256 = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as stream:
                while chunk := stream.read(_COPY_CHUNK_BYTES):
                    size += len(chunk)
                    sha256.update(chunk)
        except OSError:
            return False
        return sha256.hexdigest() == digest and (expected_size is None or size == expected_size)

    def verify_snapshot(self, snapshot_id: str) -> SnapshotVerification:
        try:
            manifest = self.load_manifest(snapshot_id)
        except SnapshotStoreError as error:
            return SnapshotVerification(
                snapshot_id=snapshot_id,
                manifest_valid=False,
                objects_valid=False,
                error_code=error.code,
            )
        missing: set[str] = set()
        corrupt: set[str] = set()
        expected: dict[str, int] = {}
        for entry in manifest.entries:
            expected.setdefault(entry.blob_sha256, entry.byte_size)
        for digest, size in expected.items():
            path = self.object_path(digest)
            if path.is_symlink() or not path.is_file():
                missing.add(digest)
            elif not self.verify_object(digest, expected_size=size):
                corrupt.add(digest)
        return SnapshotVerification(
            snapshot_id=snapshot_id,
            manifest_valid=True,
            objects_valid=not missing and not corrupt,
            missing_objects=tuple(sorted(missing)),
            corrupt_objects=tuple(sorted(corrupt)),
        )

    def _copy_verified_object(self, entry: SnapshotEntry, target: Path) -> None:
        source = self.object_path(entry.blob_sha256)
        if source.is_symlink() or not source.is_file():
            raise SnapshotStoreError("SNAPSHOT_OBJECT_NOT_FOUND", entry.blob_sha256)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".materialize-", dir=target.parent)
        temporary = Path(temporary_name)
        digest = hashlib.sha256()
        size = 0
        try:
            with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output:
                while chunk := input_stream.read(_COPY_CHUNK_BYTES):
                    size += len(chunk)
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if digest.hexdigest() != entry.blob_sha256 or size != entry.byte_size:
                raise SnapshotStoreError("SNAPSHOT_OBJECT_CORRUPT", entry.blob_sha256)
            temporary.chmod(entry.file_mode & 0o777)
            os.replace(temporary, target)
            _fsync_directory(target.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def materialize(
        self,
        snapshot_id: str,
        destination: Path,
        *,
        live_project_root: Path,
    ) -> Path:
        """Materialize into a fresh directory disjoint from the live source tree."""

        manifest = self.load_manifest(snapshot_id)
        try:
            live_root = live_project_root.expanduser().resolve(strict=True)
        except OSError as error:
            raise SnapshotStoreError("SNAPSHOT_LIVE_PROJECT_NOT_FOUND") from error
        requested_destination = destination.expanduser().absolute()
        if requested_destination.is_symlink():
            raise SnapshotStoreError("SNAPSHOT_MATERIALIZATION_SYMLINK_REJECTED")
        destination = requested_destination.resolve(strict=False)
        if _relative_is_within(destination, live_root) or _relative_is_within(
            live_root, destination
        ):
            raise SnapshotStoreError("SNAPSHOT_MATERIALIZATION_OVERLAPS_LIVE_PROJECT")
        if destination.exists() or destination.is_symlink():
            raise SnapshotStoreError("SNAPSHOT_MATERIALIZATION_DESTINATION_EXISTS")
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        stage = Path(
            tempfile.mkdtemp(prefix=".snapshot-materialize-", dir=destination.parent)
        ).resolve(strict=True)
        try:
            for entry in manifest.entries:
                relative = _normalized_relative(entry.relative_path)
                target = stage.joinpath(*PurePosixPath(relative).parts)
                if not _relative_is_within(target, stage):
                    raise SnapshotStoreError("SNAPSHOT_MATERIALIZATION_PATH_ESCAPE")
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                current = target.parent
                while current != stage:
                    if current.is_symlink():
                        raise SnapshotStoreError("SNAPSHOT_MATERIALIZATION_SYMLINK_REJECTED")
                    current = current.parent
                self._copy_verified_object(entry, target)
            os.replace(stage, destination)
            _fsync_directory(destination.parent)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return destination

    def _manifest_ids(self) -> tuple[str, ...]:
        result: list[str] = []
        for path in sorted(self.manifests_root.glob("*.json")):
            if path.is_symlink() or not path.is_file():
                raise SnapshotStoreError("SNAPSHOT_MANIFEST_DIRECTORY_UNSAFE")
            result.append(_validate_segment(path.stem, "SNAPSHOT_ID_INVALID"))
        return tuple(result)

    def mark_referenced_objects(
        self,
        *,
        snapshot_ids: Iterable[str] | None = None,
        additional_references: Iterable[str] = (),
    ) -> frozenset[str]:
        """Mark snapshot references plus caller-supplied DB/evidence/baseline references.

        When ``snapshot_ids`` is omitted every stored manifest is marked. Any corrupt manifest
        aborts marking, ensuring callers cannot sweep after an incomplete reference scan.
        """

        selected = self._manifest_ids() if snapshot_ids is None else tuple(snapshot_ids)
        marked = {_validate_digest(digest) for digest in additional_references}
        for snapshot_id in selected:
            manifest = self.load_manifest(snapshot_id)
            marked.update(entry.blob_sha256 for entry in manifest.entries)
        return frozenset(marked)

    def sweep_unreferenced(
        self,
        marked_objects: Collection[str],
        *,
        dry_run: bool = True,
    ) -> GarbageCollectionStats:
        """Sweep CAS files absent from both the supplied mark and every live manifest.

        Re-marking manifests here is intentional defense in depth: even an incomplete caller mark
        cannot delete an object referenced by a stored snapshot. Callers must still supply direct
        database, evidence, baseline, incident, and repair-workspace references.
        """

        supplied = {_validate_digest(digest) for digest in marked_objects}
        marked = set(self.mark_referenced_objects(additional_references=supplied))
        retained = 0
        swept = 0
        swept_bytes = 0
        skipped = 0
        for prefix in sorted(self.objects_root.iterdir()):
            if prefix.name.startswith(".source-object-"):
                skipped += 1
                continue
            if (
                prefix.is_symlink()
                or not prefix.is_dir()
                or not re.fullmatch(r"[0-9a-f]{2}", prefix.name)
            ):
                skipped += 1
                continue
            for candidate in sorted(prefix.iterdir()):
                if (
                    candidate.is_symlink()
                    or not candidate.is_file()
                    or not _DIGEST.fullmatch(candidate.name)
                    or candidate.name[:2] != prefix.name
                ):
                    skipped += 1
                    continue
                if candidate.name in marked:
                    retained += 1
                    continue
                size = candidate.stat().st_size
                swept += 1
                swept_bytes += size
                if not dry_run:
                    candidate.unlink()
            if not dry_run:
                try:
                    prefix.rmdir()
                except OSError:
                    pass
        if not dry_run:
            _fsync_directory(self.objects_root)
        return GarbageCollectionStats(
            marked_objects=len(marked),
            retained_objects=retained,
            swept_objects=swept,
            swept_bytes=swept_bytes,
            skipped_entries=skipped,
            dry_run=dry_run,
        )

    def collect_garbage(
        self,
        *,
        additional_references: Iterable[str] = (),
        dry_run: bool = True,
    ) -> GarbageCollectionStats:
        """Conservatively mark every manifest before sweeping unreferenced CAS objects."""

        marked = self.mark_referenced_objects(additional_references=additional_references)
        return self.sweep_unreferenced(marked, dry_run=dry_run)

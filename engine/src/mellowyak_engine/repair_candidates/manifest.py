from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mellowyak_engine.scanning.policy import is_sensitive_path
from mellowyak_engine.snapshots.store import canonical_json

MAX_CANDIDATE_FILES = 250
MAX_CANDIDATE_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PREVIEW_BYTES = 1024 * 1024
MAX_DIFF_LINES = 4000
PRIVATE_SEGMENTS = frozenset({".aws", ".azure", ".claude", ".codex", ".cursor", ".gnupg", ".ssh"})


class CandidateManifestError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        super().__init__(code)


@dataclass(frozen=True)
class WorkspaceEntry:
    relative_path: str
    digest: str
    byte_size: int
    file_mode: int
    executable: bool
    classification: str

    def public(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "digest": self.digest,
            "byte_size": self.byte_size,
            "file_mode": self.file_mode,
            "executable": self.executable,
            "classification": self.classification,
        }


def normalize_relative(value: str) -> str:
    if "\\" in value:
        raise CandidateManifestError("CANDIDATE_PATH_INVALID", value)
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise CandidateManifestError("CANDIDATE_PATH_INVALID", value)
    normalized = path.as_posix()
    if normalized != value:
        raise CandidateManifestError("CANDIDATE_PATH_INVALID", value)
    return normalized


def safe_join(root: Path, relative: str, *, allow_missing: bool = True) -> Path:
    relative = normalize_relative(relative)
    root = root.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise CandidateManifestError("CANDIDATE_PATH_ESCAPE_REJECTED", relative) from error
    if not allow_missing and not candidate.exists():
        raise CandidateManifestError("CANDIDATE_PATH_NOT_FOUND", relative)
    return candidate


def _digest_file(path: Path, size: int) -> tuple[str, str]:
    digest = hashlib.sha256()
    binary = False
    read = 0
    flags = os.O_RDONLY | (getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CandidateManifestError("CANDIDATE_FILE_OPEN_FAILED", path.name) from error
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_size != size:
            raise CandidateManifestError("CANDIDATE_FILE_CHANGED_DURING_READ", path.name)
        while chunk := stream.read(1024 * 1024):
            read += len(chunk)
            if read > MAX_FILE_BYTES:
                raise CandidateManifestError("CANDIDATE_FILE_TOO_LARGE", path.name)
            binary = binary or b"\0" in chunk
            digest.update(chunk)
        closed = os.fstat(stream.fileno())
        if closed.st_size != opened.st_size or closed.st_mtime_ns != opened.st_mtime_ns:
            raise CandidateManifestError("CANDIDATE_FILE_CHANGED_DURING_READ", path.name)
    return digest.hexdigest(), "binary" if binary else "text"


def scan_workspace(root: Path) -> tuple[tuple[WorkspaceEntry, ...], str]:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise CandidateManifestError("CANDIDATE_WORKSPACE_INVALID")
    entries: list[WorkspaceEntry] = []
    casefolded: dict[str, str] = {}
    total = 0
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained: list[str] = []
        for directory in sorted(directories):
            relative = (current_path / directory).relative_to(root).as_posix()
            if (current_path / directory).is_symlink():
                raise CandidateManifestError("CANDIDATE_SYMLINK_REJECTED", relative)
            if directory in PRIVATE_SEGMENTS or is_sensitive_path(relative):
                raise CandidateManifestError("CANDIDATE_SENSITIVE_PATH_REJECTED", relative)
            retained.append(directory)
        directories[:] = retained
        for filename in sorted(files):
            path = current_path / filename
            relative = normalize_relative(path.relative_to(root).as_posix())
            if is_sensitive_path(relative) or any(
                part in PRIVATE_SEGMENTS for part in PurePosixPath(relative).parts
            ):
                raise CandidateManifestError("CANDIDATE_SENSITIVE_PATH_REJECTED", relative)
            lowered = relative.casefold()
            if lowered in casefolded and casefolded[lowered] != relative:
                raise CandidateManifestError("CANDIDATE_CASE_COLLISION_REJECTED", relative)
            casefolded[lowered] = relative
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise CandidateManifestError("CANDIDATE_SYMLINK_REJECTED", relative)
            if not stat.S_ISREG(info.st_mode):
                raise CandidateManifestError("CANDIDATE_SPECIAL_FILE_REJECTED", relative)
            if info.st_nlink > 1:
                raise CandidateManifestError("CANDIDATE_HARD_LINK_REJECTED", relative)
            if info.st_size > MAX_FILE_BYTES:
                raise CandidateManifestError("CANDIDATE_FILE_TOO_LARGE", relative)
            total += info.st_size
            if total > MAX_CANDIDATE_BYTES:
                raise CandidateManifestError("CANDIDATE_TOTAL_BYTES_EXCEEDED")
            digest, classification = _digest_file(path, info.st_size)
            mode = stat.S_IMODE(info.st_mode)
            entries.append(
                WorkspaceEntry(
                    relative, digest, info.st_size, mode, bool(mode & 0o111), classification
                )
            )
            if len(entries) > MAX_CANDIDATE_FILES:
                raise CandidateManifestError("CANDIDATE_FILE_COUNT_EXCEEDED")
    entries.sort(key=lambda item: item.relative_path)
    digest = hashlib.sha256(canonical_json([entry.public() for entry in entries])).hexdigest()
    return tuple(entries), digest

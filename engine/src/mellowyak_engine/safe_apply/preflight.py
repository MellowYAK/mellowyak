from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from mellowyak_engine.repair_candidates.manifest import normalize_relative


class PreflightError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        super().__init__(code)


def safe_live_path(root: Path, relative: str) -> Path:
    relative = normalize_relative(relative)
    root = root.resolve(strict=True)
    candidate = root.joinpath(*relative.split("/"))
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise PreflightError("APPLY_PATH_ESCAPE_REJECTED", relative) from error
    if candidate.is_symlink():
        raise PreflightError("APPLY_SYMLINK_REJECTED", relative)
    return candidate


def digest_path(path: Path) -> str | None:
    if not path.exists():
        return None
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise PreflightError("APPLY_SYMLINK_REJECTED", path.name)
    if not stat.S_ISREG(info.st_mode):
        raise PreflightError("APPLY_SPECIAL_FILE_REJECTED", path.name)
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
        final = os.fstat(stream.fileno())
    if opened.st_size != final.st_size or opened.st_mtime_ns != final.st_mtime_ns:
        raise PreflightError("APPLY_PATH_CHANGED_DURING_HASH", path.name)
    return digest.hexdigest()


def verify_expected(path: Path, expected: str | None, relative: str) -> None:
    current = digest_path(path)
    if current != expected:
        raise PreflightError("APPLY_LIVE_DIGEST_MISMATCH", relative)

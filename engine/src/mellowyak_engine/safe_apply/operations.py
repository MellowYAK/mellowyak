from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

from mellowyak_engine.safe_apply.journal import fsync_directory
from mellowyak_engine.safe_apply.preflight import digest_path


class ApplyOperationError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        super().__init__(code)


def atomic_copy(source: Path, target: Path, expected_digest: str, mode: int) -> None:
    if source.is_symlink() or not source.is_file():
        raise ApplyOperationError("APPLY_CANDIDATE_SOURCE_INVALID", source.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.mellowyak-", dir=target.parent)
    temporary = Path(name)
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output:
            shutil.copyfileobj(input_stream, output, 1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        if digest_path(temporary) != expected_digest:
            raise ApplyOperationError("APPLY_TEMP_DIGEST_MISMATCH", target.name)
        temporary.chmod(stat.S_IMODE(mode or 0o600))
        os.replace(temporary, target)
        fsync_directory(target.parent)
        if digest_path(target) != expected_digest:
            raise ApplyOperationError("APPLY_FINAL_DIGEST_MISMATCH", target.name)
    finally:
        temporary.unlink(missing_ok=True)


def durable_delete(path: Path) -> None:
    path.unlink(missing_ok=True)
    fsync_directory(path.parent)

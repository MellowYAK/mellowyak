from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mellowyak_engine.runtime_adapters.base import SafeProcessRunner

MAX_METADATA_FILE_BYTES = 2 * 1024 * 1024
MAX_METADATA_ITEMS = 128


def relative_markers(project: Path, candidates: Iterable[str]) -> tuple[str, ...]:
    root = project.expanduser().resolve()
    markers: list[str] = []
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            markers.append(path.relative_to(root).as_posix())
    return tuple(markers[:MAX_METADATA_ITEMS])


def manifest_hashes(project: Path, candidates: Iterable[str]) -> dict[str, str]:
    root = project.expanduser().resolve()
    hashes: dict[str, str] = {}
    for candidate in candidates:
        path = (root / candidate).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file():
            continue
        hashes[path.relative_to(root).as_posix()] = hash_file(path)
        if len(hashes) >= MAX_METADATA_ITEMS:
            break
    return hashes


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_METADATA_FILE_BYTES:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def executable_on_path(*names: str) -> str | None:
    for name in names:
        located = shutil.which(name)
        if located:
            return str(Path(located).absolute())
    return None


def safe_metadata_command(
    *,
    runner: SafeProcessRunner,
    project: Path,
    executable: str | None,
    argv: tuple[str, ...],
    timeout_seconds: float = 3.0,
    output_limit_bytes: int = 32 * 1024,
) -> tuple[int, str, str] | None:
    if executable is None:
        return None
    try:
        execution = runner.run(
            executable=executable,
            argv=argv,
            project_root=project,
            relative_working_directory=".",
            timeout_seconds=timeout_seconds,
            output_limit_bytes=output_limit_bytes,
        )
    except (FileNotFoundError, OSError, ValueError):
        return None
    return execution.exit_code, execution.stdout.strip(), execution.stderr.strip()


def first_line(value: str, *, maximum: int = 256) -> str | None:
    line = next((item.strip() for item in value.splitlines() if item.strip()), "")
    return line[:maximum] if line else None


def stable_metadata(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(values)))[:MAX_METADATA_ITEMS]

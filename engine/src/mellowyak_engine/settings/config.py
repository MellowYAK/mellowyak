from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

ALLOWED_HOSTS = frozenset({"127.0.0.1", "::1"})
DEFAULT_ALLOWED_ORIGINS = (
    "tauri://localhost",
    "http://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)


def resolve_data_root(override: str | Path | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    environment_override = os.environ.get("MELLOWYAK_DATA_ROOT", "").strip()
    if environment_override:
        return Path(environment_override).expanduser().resolve()
    if os.name == "nt":
        # The per-user NSIS installer uses %LOCALAPPDATA%\MellowYak. Keep
        # mutable product data outside that installation directory so an
        # uninstall or upgrade cannot mistake user state for program files.
        return (
            Path(user_data_path("com.mellowyak.desktop", appauthor=False, roaming=False)) / "engine"
        ).resolve()
    return Path(user_data_path("MellowYak", appauthor=False, roaming=False)).resolve()


@dataclass(frozen=True)
class EngineSettings:
    data_root: Path
    session_token: str
    bind_host: str = "127.0.0.1"
    parent_pid: int | None = None
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS

    @classmethod
    def from_environment(cls) -> EngineSettings:
        token = os.environ.get("MELLOWYAK_SESSION_TOKEN", "")
        if len(token) < 32:
            raise RuntimeError("MELLOWYAK_SESSION_TOKEN_REQUIRED")
        host = os.environ.get("MELLOWYAK_BIND_HOST", "127.0.0.1").strip()
        if host not in ALLOWED_HOSTS:
            raise RuntimeError("MELLOWYAK_LOOPBACK_ONLY")
        raw_parent = os.environ.get("MELLOWYAK_PARENT_PID", "").strip()
        parent_pid = int(raw_parent) if raw_parent else None
        origins = tuple(
            item.strip()
            for item in os.environ.get(
                "MELLOWYAK_ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)
            ).split(",")
            if item.strip()
        )
        return cls(
            data_root=resolve_data_root(),
            session_token=token,
            bind_host=host,
            parent_pid=parent_pid,
            allowed_origins=origins,
        )

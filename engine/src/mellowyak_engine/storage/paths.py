from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoragePaths:
    root: Path
    database: Path
    evidence: Path
    projects: Path
    cache: Path
    logs: Path
    runtime: Path
    backups: Path

    @classmethod
    def create(cls, root: Path) -> StoragePaths:
        resolved = root.expanduser().resolve()
        paths = cls(
            root=resolved,
            database=resolved / "database",
            evidence=resolved / "evidence",
            projects=resolved / "projects",
            cache=resolved / "cache",
            logs=resolved / "logs",
            runtime=resolved / "runtime",
            backups=resolved / "backups",
        )
        resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
        for path in (
            paths.database,
            paths.evidence,
            paths.projects,
            paths.cache,
            paths.logs,
            paths.runtime,
            paths.backups,
        ):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return paths

    @property
    def sqlite_file(self) -> Path:
        return self.database / "mellowyak.sqlite3"

    def public_dict(self) -> dict[str, str]:
        return {
            "data_root": str(self.root),
            "database": str(self.database),
            "evidence": str(self.evidence),
            "projects": str(self.projects),
            "cache": str(self.cache),
            "logs": str(self.logs),
            "runtime": str(self.runtime),
            "backups": str(self.backups),
        }

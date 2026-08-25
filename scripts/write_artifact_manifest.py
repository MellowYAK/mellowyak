from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import tomllib


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "local"))
    parser.add_argument("--validation-status", default="NOT_RUN")
    arguments = parser.parse_args()
    root = arguments.root.resolve(strict=True)
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    repository_root = Path(__file__).resolve().parents[1]
    tauri_config = json.loads(
        (repository_root / "apps/desktop/src-tauri/tauri.conf.json").read_text(
            encoding="utf-8"
        )
    )
    engine_config = tomllib.loads(
        (repository_root / "engine/pyproject.toml").read_text(encoding="utf-8")
    )
    commit = arguments.commit
    if commit == "local":
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    tracked_status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    migration_files = sorted((repository_root / "engine/alembic/versions").glob("*.py"))
    schema_version = migration_files[-1].stem if migration_files else "UNKNOWN"
    payload = {
        "schema": "mellowyak.artifact_manifest.v2",
        "platform": arguments.platform,
        "source": {
            "commit": commit,
            "tracked_tree_clean": not bool(tracked_status),
        },
        "versions": {
            "application": tauri_config["version"],
            "engine": engine_config["project"]["version"],
            "database_schema": schema_version,
        },
        "validation": {
            "status": arguments.validation_status,
            "runtime_accepted": arguments.validation_status == "VERIFIED_WORKING",
        },
        "created_at": datetime.now(UTC).isoformat(),
        "files": files,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

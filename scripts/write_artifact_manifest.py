from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


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
    payload = {
        "schema": "mellowyak.artifact_manifest.v1",
        "platform": arguments.platform,
        "commit": arguments.commit,
        "created_at": datetime.now(UTC).isoformat(),
        "files": files,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

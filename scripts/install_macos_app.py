#!/usr/bin/env python3
"""Build only the macOS app bundle and install it into /Applications."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "desktop"
SOURCE = (
    DESKTOP / "src-tauri" / "target" / "release" / "bundle" / "macos" / "MellowYak.app"
)
APPLICATIONS = Path("/Applications")
TARGET = APPLICATIONS / "MellowYak.app"


def run(*command: str, cwd: Path = ROOT, check: bool = True) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=check)


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("install-macos is available only on macOS")
    use_existing = sys.argv[1:] == ["--from-existing"]
    if sys.argv[1:] and not use_existing:
        raise SystemExit("usage: install_macos_app.py [--from-existing]")
    if not use_existing:
        run(
            str(ROOT / "engine" / ".venv" / "bin" / "python"),
            str(ROOT / "scripts" / "build_engine.py"),
        )
        run("npm", "run", "tauri", "build", "--", "--bundles", "app", cwd=DESKTOP)
    if not SOURCE.is_dir():
        raise SystemExit(f"Built application is missing: {SOURCE}")

    subprocess.run(
        ["osascript", "-e", 'tell application "MellowYak" to quit'],
        check=False,
        capture_output=True,
    )
    for _ in range(40):
        running = subprocess.run(
            ["pgrep", "-x", "mellowyak-desktop"],
            check=False,
            capture_output=True,
        )
        if running.returncode != 0:
            break
        time.sleep(0.25)

    suffix = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    staging = APPLICATIONS / f".MellowYak-installing-{suffix}.app"
    backup = APPLICATIONS / f"MellowYak-previous-{suffix}.app"
    run("ditto", str(SOURCE), str(staging))
    previous_moved = False
    try:
        if TARGET.exists():
            os.replace(TARGET, backup)
            previous_moved = True
        os.replace(staging, TARGET)
    except Exception:
        if previous_moved and not TARGET.exists() and backup.exists():
            os.replace(backup, TARGET)
        raise
    run("open", str(TARGET))
    print(f"Installed: {TARGET}")
    if previous_moved:
        print(f"Recoverable previous version: {backup}")


if __name__ == "__main__":
    main()

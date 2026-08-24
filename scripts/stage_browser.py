#!/usr/bin/env python3
"""Stage the installed Playwright Chromium into Tauri package resources."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "apps" / "desktop" / "src-tauri" / ".browser-resources" / "browser"


def cache_root() -> Path:
    override = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if override and override != "0":
        return Path(override).expanduser().resolve()
    system = platform.system().lower()
    if system == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    if system == "windows":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def find_browser() -> tuple[Path, Path]:
    installs = sorted(cache_root().glob("chromium-*"), reverse=True)
    relative_candidates = (
        Path(
            "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/"
            "Google Chrome for Testing"
        ),
        Path(
            "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        Path("chrome-linux/chrome"),
        Path("chrome-linux64/chrome"),
        Path("chrome-win/chrome.exe"),
        Path("chrome-win64/chrome.exe"),
    )
    for install in installs:
        for relative in relative_candidates:
            if (install / relative).is_file():
                return install, relative
    raise SystemExit("Playwright Chromium is missing. Run: playwright install chromium")


def ensure_browser() -> None:
    if list(cache_root().glob("chromium-*")):
        return
    python = (
        ROOT
        / "engine"
        / ".venv"
        / ("Scripts/python.exe" if platform.system().lower() == "windows" else "bin/python")
    )
    if not python.is_file():
        raise SystemExit("Engine virtual environment is missing.")
    subprocess.run([str(python), "-m", "playwright", "install", "chromium"], check=True)


def main() -> None:
    ensure_browser()
    install, executable = find_browser()
    destination = STAGING / "chromium"
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True, mode=0o700)
    shutil.copytree(install, destination, symlinks=True)
    manifest = {
        "schema": "mellowyak.packaged_browser.v1",
        "engine": "chromium",
        "executable_relative": (Path("chromium") / executable).as_posix(),
    }
    (STAGING / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(destination / executable)


if __name__ == "__main__":
    main()

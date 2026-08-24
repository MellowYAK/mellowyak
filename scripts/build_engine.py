from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
DESKTOP_BINARIES = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
BUILD_ROOT = ENGINE / ".build" / "pyinstaller"


def run(*command: str, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        command, cwd=cwd, check=True, text=True, capture_output=True
    )
    return completed.stdout.strip()


def main() -> None:
    python = (
        ENGINE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not python.is_file():
        raise SystemExit("Run the development bootstrap before building the engine.")
    triple = run("rustc", "--print", "host-tuple")
    extension = ".exe" if os.name == "nt" else ""
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(python),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "mellowyak-engine",
            "--distpath",
            str(BUILD_ROOT / "dist"),
            "--workpath",
            str(BUILD_ROOT / "work"),
            "--specpath",
            str(BUILD_ROOT / "spec"),
            "--paths",
            str(ENGINE / "src"),
            "--add-data",
            f"{ENGINE / 'alembic'}{os.pathsep}alembic",
            "--add-data",
            f"{ENGINE / 'alembic.ini'}{os.pathsep}.",
            "--collect-all",
            "alembic",
            "--collect-all",
            "playwright",
            str(ENGINE / "src" / "mellowyak_engine" / "main.py"),
        ],
        cwd=ENGINE,
        check=True,
    )
    source = BUILD_ROOT / "dist" / f"mellowyak-engine{extension}"
    destination = DESKTOP_BINARIES / f"mellowyak-engine-{triple}{extension}"
    DESKTOP_BINARIES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(0o755)
    print(destination)


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
DESKTOP_BINARIES = ROOT / "apps" / "desktop" / "src-tauri" / "binaries"
MACOS_RESOURCES = (
    ROOT / "apps" / "desktop" / "src-tauri" / ".engine-resources" / "mellowyak-engine"
)
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
    staged_alembic = BUILD_ROOT / "staging" / "alembic"
    shutil.copytree(
        ENGINE / "alembic",
        staged_alembic,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    mode = "--onedir" if platform.system() == "Darwin" else "--onefile"
    subprocess.run(
        [
            str(python),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            mode,
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
            f"{staged_alembic}{os.pathsep}alembic",
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
    source_root = BUILD_ROOT / "dist" / "mellowyak-engine"
    source = (
        source_root / f"mellowyak-engine{extension}"
        if mode == "--onedir"
        else BUILD_ROOT / "dist" / f"mellowyak-engine{extension}"
    )
    destination = DESKTOP_BINARIES / f"mellowyak-engine-{triple}{extension}"
    DESKTOP_BINARIES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(0o755)
    if mode == "--onedir":
        shutil.rmtree(MACOS_RESOURCES, ignore_errors=True)
        shutil.copytree(source_root, MACOS_RESOURCES, symlinks=True)
        packaged = MACOS_RESOURCES / "mellowyak-engine"
        packaged.chmod(0o755)
        print(packaged)
    else:
        print(destination)


if __name__ == "__main__":
    main()

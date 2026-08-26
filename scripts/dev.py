#!/usr/bin/env python3
"""Cross-platform development entry point; never required by installed users."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
DESKTOP = ROOT / "apps" / "desktop"
VENV = ENGINE / ".venv"


def run(
    *command: str,
    cwd: Path = ROOT,
    environment: dict[str, str] | None = None,
) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True, env=environment)


def release_environment() -> dict[str, str]:
    environment = os.environ.copy()
    existing = [
        item
        for item in environment.get("CARGO_ENCODED_RUSTFLAGS", "").split("\x1f")
        if item
    ]
    existing.extend(
        [
            f"--remap-path-prefix={ROOT}=<SOURCE_ROOT>",
            f"--remap-path-prefix={Path.home() / '.cargo'}=<CARGO_HOME>",
        ]
    )
    environment["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(existing)
    if (
        sys.platform == "darwin"
        and not environment.get("APPLE_SIGNING_IDENTITY", "").strip()
    ):
        # Keep local packages structurally verifiable without pretending they
        # are Developer ID signed or notarized. Release jobs provide the real
        # identity explicitly and therefore never take this fallback.
        environment["APPLE_SIGNING_IDENTITY"] = "-"
    return environment


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def require_venv() -> str:
    python = venv_python()
    if not python.is_file():
        raise SystemExit(
            "Development environment missing. Run: python3 scripts/dev.py bootstrap"
        )
    return str(python)


def bootstrap() -> None:
    if sys.version_info < (3, 11):
        raise SystemExit(
            "Python 3.11+ is required; CI and release builds use Python 3.12."
        )
    if not VENV.exists():
        run(sys.executable, "-m", "venv", str(VENV))
    run(require_venv(), "-m", "pip", "install", "--upgrade", "pip")
    run(require_venv(), "-m", "pip", "install", "-e", ".[dev]", cwd=ENGINE)
    run("npm", "ci", cwd=DESKTOP)
    run(require_venv(), str(ROOT / "scripts" / "export_openapi.py"))
    run("npm", "run", "contract:generate", cwd=DESKTOP)
    run("cargo", "fetch", cwd=DESKTOP / "src-tauri")


def tests() -> None:
    run(require_venv(), "-m", "pytest", cwd=ENGINE)
    run("npm", "test", cwd=DESKTOP)


def lint() -> None:
    run(require_venv(), "-m", "ruff", "check", "engine", "scripts")
    run(require_venv(), "-m", "ruff", "format", "--check", "engine", "scripts")
    run("cargo", "fmt", "--check", cwd=DESKTOP / "src-tauri")


def typecheck() -> None:
    run("npm", "run", "typecheck", cwd=DESKTOP)
    run("cargo", "check", cwd=DESKTOP / "src-tauri")


def engine_build() -> None:
    run(require_venv(), str(ROOT / "scripts" / "build_engine.py"))


def desktop_build() -> None:
    run("npm", "run", "build", cwd=DESKTOP)
    run("cargo", "build", cwd=DESKTOP / "src-tauri")


def package() -> None:
    engine_build()
    environment = release_environment()
    run(
        "npm",
        "run",
        "tauri",
        "build",
        cwd=DESKTOP,
        environment=environment,
    )
    if sys.platform == "darwin":
        identity = environment.get("APPLE_SIGNING_IDENTITY", "-")
        for disk_image in sorted(
            (DESKTOP / "src-tauri" / "target" / "release" / "bundle" / "dmg").glob(
                "*.dmg"
            )
        ):
            command = ["codesign", "--force", "--sign", identity]
            if identity != "-":
                command.append("--timestamp")
            command.append(str(disk_image))
            run(*command)


def install_macos() -> None:
    run(require_venv(), str(ROOT / "scripts" / "install_macos_app.py"))


def development() -> None:
    engine_build()
    run("npm", "run", "tauri", "dev", cwd=DESKTOP)


def clean() -> None:
    generated = [
        ENGINE / ".build",
        DESKTOP / "dist",
        DESKTOP / "src-tauri" / "target",
        DESKTOP / "src-tauri" / "binaries",
    ]
    for path in generated:
        if path.exists():
            print(f"Removing generated output: {path.relative_to(ROOT)}")
            shutil.rmtree(path)


COMMANDS = {
    "bootstrap": bootstrap,
    "dev": development,
    "test": tests,
    "lint": lint,
    "typecheck": typecheck,
    "engine-build": engine_build,
    "desktop-build": desktop_build,
    "package": package,
    "install-macos": install_macos,
    "clean": clean,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    args = parser.parse_args()
    COMMANDS[args.command]()


if __name__ == "__main__":
    main()

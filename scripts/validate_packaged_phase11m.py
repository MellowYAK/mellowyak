#!/usr/bin/env python3
"""Validate Phase 11M macOS package identity, contents, and DMG structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
import tempfile
from pathlib import Path

FORBIDDEN_NAMES = {
    "mellowyak.db",
    "snapshots",
    "evidence",
    "repair-workspaces",
    "apply-journals",
    "recovery-bundles",
    "support-bundles",
    "browser-profile",
    "updater.key",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--dmg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    app = arguments.app.resolve()
    executable = app / "Contents/MacOS/mellowyak-desktop"
    engine = app / "Contents/Resources/engine/mellowyak-engine/mellowyak-engine"
    browser_manifest = app / "Contents/Resources/browser/manifest.json"
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    names = {path.name.lower() for path in app.rglob("*")}
    absolute_home = str(Path.home()).encode()
    small_text = b"\n".join(
        path.read_bytes()
        for path in app.rglob("*")
        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 2_000_000
    )
    checks = {
        "fresh_app_present": app.is_dir(),
        "fresh_dmg_present": arguments.dmg.is_file(),
        "intel_desktop": "x86_64" in run("file", str(executable)).stdout,
        "intel_engine": "x86_64" in run("file", str(engine)).stdout,
        "engine_resource_present": engine.is_file() and os.access(engine, os.X_OK),
        "browser_manifest_present": browser_manifest.is_file(),
        "version_preserved": info.get("CFBundleShortVersionString")
        == "0.5.0-preview.3",
        "bundle_identifier": info.get("CFBundleIdentifier") == "com.mellowyak.desktop",
        "codesign_structure_valid": run(
            "codesign", "--verify", "--deep", "--strict", str(app)
        ).returncode
        == 0,
        "dmg_codesign_structure_valid": run(
            "codesign", "--verify", str(arguments.dmg)
        ).returncode
        == 0,
        "no_forbidden_runtime_data_names": not bool(FORBIDDEN_NAMES & names),
        "no_user_home_build_path": absolute_home not in small_text,
        "no_database_payload": not any(
            path.suffix in {".db", ".sqlite", ".sqlite3"} for path in app.rglob("*")
        ),
    }
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase11m-dmg-") as temp:
        mount = Path(temp) / "mount"
        mount.mkdir()
        attached = run(
            "hdiutil",
            "attach",
            "-readonly",
            "-nobrowse",
            "-mountpoint",
            str(mount),
            str(arguments.dmg),
        )
        checks["dmg_readonly_mount"] = attached.returncode == 0
        if attached.returncode == 0:
            checks["dmg_application_present"] = (mount / "MellowYak.app").is_dir()
            checks["dmg_applications_link"] = (mount / "Applications").is_symlink()
            checks["dmg_hash_identity"] = sha256(
                mount / "MellowYak.app/Contents/MacOS/mellowyak-desktop"
            ) == sha256(executable)
            detached = run("hdiutil", "detach", str(mount))
            checks["dmg_clean_detach"] = detached.returncode == 0
        else:
            checks.update(
                {
                    "dmg_application_present": False,
                    "dmg_applications_link": False,
                    "dmg_hash_identity": False,
                    "dmg_clean_detach": False,
                }
            )
    report = {
        "schema": "mellowyak.phase11m.packaged-validation.v1",
        "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
        "checks": checks,
        "identities": {
            "desktop_sha256": sha256(executable),
            "engine_sha256": sha256(engine),
            "dmg_sha256": sha256(arguments.dmg),
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "VERIFIED_WORKING" else 1


if __name__ == "__main__":
    raise SystemExit(main())

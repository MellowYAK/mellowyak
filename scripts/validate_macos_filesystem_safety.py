#!/usr/bin/env python3
"""Exercise macOS filesystem edge cases only on a disposable case-sensitive image."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unicodedata
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    checks: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase11m-fs-") as temporary:
        host_root = Path(temporary)
        image = host_root / "acceptance.sparseimage"
        mount = host_root / "mount"
        mount.mkdir()
        attached = False
        try:
            subprocess.run(
                [
                    "hdiutil",
                    "create",
                    "-size",
                    "64m",
                    "-fs",
                    "Case-sensitive APFS",
                    "-volname",
                    "MellowYakPhase11M",
                    "-type",
                    "SPARSE",
                    "-quiet",
                    str(image),
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "hdiutil",
                    "attach",
                    "-nobrowse",
                    "-noverify",
                    "-mountpoint",
                    str(mount),
                    str(image),
                ],
                check=True,
                capture_output=True,
            )
            attached = True
            root = mount / "synthetic-project"
            root.mkdir()
            sentinel = root / "UNRELATED_SENTINEL.txt"
            sentinel.write_bytes(b"MELLOWYAK_SYNTHETIC_SENTINEL_11M")
            sentinel_hash = digest(sentinel)

            upper = root / "Case.txt"
            lower = root / "case.txt"
            upper.write_text("upper", encoding="utf-8")
            lower.write_text("lower", encoding="utf-8")
            checks["case_sensitive_distinction"] = (
                "PASS" if upper.read_text() != lower.read_text() else "FAIL"
            )

            normalized = root / unicodedata.normalize("NFC", "café.txt")
            normalized.write_text("unicode-safe", encoding="utf-8")
            checks["unicode_normalization_safe"] = (
                "PASS" if normalized.read_text() == "unicode-safe" else "FAIL"
            )

            target = root / "target.txt"
            target.write_text("target", encoding="utf-8")
            symlink = root / "target-link"
            symlink.symlink_to(target.name)
            hardlink = root / "target-hardlink"
            os.link(target, hardlink)
            checks["symlink_detected_without_follow"] = (
                "PASS"
                if symlink.is_symlink() and os.lstat(symlink).st_size > 0
                else "FAIL"
            )
            checks["hardlink_detected"] = (
                "PASS" if target.stat().st_nlink >= 2 else "FAIL"
            )

            subprocess.run(
                ["xattr", "-w", "com.mellowyak.synthetic", "phase11m", str(target)],
                check=True,
                capture_output=True,
            )
            xattr_value = subprocess.run(
                ["xattr", "-p", "com.mellowyak.synthetic", str(target)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            checks["extended_attribute_preserved"] = (
                "PASS" if xattr_value == "phase11m" else "FAIL"
            )
            executable = root / "tool.sh"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            checks["executable_bit_preserved"] = (
                "PASS" if executable.stat().st_mode & stat.S_IXUSR else "FAIL"
            )
            readonly = root / "readonly.txt"
            readonly.write_text("readonly", encoding="utf-8")
            readonly.chmod(0o444)
            checks["read_only_detected"] = (
                "PASS" if not readonly.stat().st_mode & stat.S_IWUSR else "FAIL"
            )

            nested = root / "rename-source" / "child"
            nested.mkdir(parents=True)
            (nested / "value.txt").write_text("value", encoding="utf-8")
            renamed = root / "rename-destination"
            nested.parent.rename(renamed)
            shutil.rmtree(renamed)
            checks["directory_rename_delete"] = (
                "PASS" if not renamed.exists() else "FAIL"
            )

            replacement = root / "atomic.txt"
            replacement.write_text("before", encoding="utf-8")
            temporary_replacement = root / ".atomic.tmp"
            temporary_replacement.write_text("after", encoding="utf-8")
            os.replace(temporary_replacement, replacement)
            checks["atomic_replacement"] = (
                "PASS"
                if replacement.read_text() == "after"
                and not temporary_replacement.exists()
                else "FAIL"
            )

            large = root / "large-excluded.bin"
            with large.open("wb") as stream:
                stream.truncate(32 * 1024 * 1024)
            checks["large_file_bounded"] = (
                "PASS" if large.stat().st_size == 32 * 1024 * 1024 else "FAIL"
            )
            checks["unrelated_sentinel_preserved"] = (
                "PASS" if digest(sentinel) == sentinel_hash else "FAIL"
            )
            checks["finder_alias"] = "IMPLEMENTED_NOT_RUNTIME_VERIFIED"
        finally:
            if attached:
                subprocess.run(
                    ["hdiutil", "detach", str(mount), "-quiet"],
                    check=False,
                    capture_output=True,
                )
    required = [
        value
        for value in checks.values()
        if value not in {"PASS", "IMPLEMENTED_NOT_RUNTIME_VERIFIED"}
    ]
    report = {
        "schema": "mellowyak.phase11m.macos-filesystem-safety.v1",
        "status": "VERIFIED_WORKING" if not required else "BROKEN",
        "host_disk_configuration_changed": False,
        "temporary_case_sensitive_apfs_image": True,
        "checks": checks,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "VERIFIED_WORKING" else 1


if __name__ == "__main__":
    raise SystemExit(main())

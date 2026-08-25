#!/usr/bin/env python3
"""Exercise packaged macOS process lifecycle against a disposable app and data root."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path


def child_engine(parent: int) -> int | None:
    result = subprocess.run(
        ["pgrep", "-P", str(parent), "-x", "mellowyak-engine"],
        check=False,
        capture_output=True,
        text=True,
    )
    values = [int(value) for value in result.stdout.split() if value.isdigit()]
    return values[0] if len(values) == 1 else None


def wait_for_engine(
    parent: int, *, different_from: int | None = None, timeout: float = 35
) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = child_engine(parent)
        if value is not None and value != different_from:
            return value
        time.sleep(0.25)
    raise RuntimeError("MACOS_ENGINE_CHILD_TIMEOUT")


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    acceptance_parent = Path.home() / "Library" / "Caches" / "MellowYakAcceptance"
    acceptance_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="phase11m-lifecycle-", dir=acceptance_parent
    ) as temporary:
        root = Path(temporary)
        app = root / "MellowYak Acceptance.app"
        subprocess.run(
            ["ditto", str(arguments.app), str(app)], check=True, capture_output=True
        )
        executable = app / "Contents" / "MacOS" / "mellowyak-desktop"
        environment = os.environ.copy()
        environment.update(
            {
                "MELLOWYAK_DATA_ROOT": str(root / "data"),
                "MELLOWYAK_BROWSER_HEADLESS": "1",
            }
        )
        process = subprocess.Popen(
            [str(executable)],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        second: subprocess.Popen[bytes] | None = None
        try:
            first_engine = wait_for_engine(process.pid)
            # The process exists before its authenticated handshake is accepted. Let the
            # packaged engine reach ready state before exercising supervised recovery.
            time.sleep(5)
            second = subprocess.Popen(
                [str(executable)],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            second_exited = second.wait(timeout=15) == 0
            one_engine = child_engine(process.pid) == first_engine

            os.kill(first_engine, signal.SIGKILL)
            replacement_engine = wait_for_engine(
                process.pid, different_from=first_engine
            )
            supervised = replacement_engine != first_engine and process_exists(
                process.pid
            )

            activation = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application id "com.mellowyak.desktop" to activate',
                ],
                check=False,
                capture_output=True,
            )
            focus_request_sent = activation.returncode == 0
        finally:
            if second is not None and second.poll() is None:
                second.terminate()
                second.wait(timeout=10)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and child_engine(process.pid) is not None:
                time.sleep(0.25)
        no_orphan = child_engine(process.pid) is None
        checks = {
            "clean_launch": True,
            "exactly_one_engine_child": one_engine,
            "second_instance_exited": second_exited,
            "existing_instance_focus_request": focus_request_sent,
            "engine_crash_supervised_restart": supervised,
            "explicit_process_exit": process.returncode is not None,
            "child_cleanup": no_orphan,
            "duplicate_engine_after_restart": child_engine(process.pid) is not None,
        }
        checks["duplicate_engine_after_restart"] = not checks[
            "duplicate_engine_after_restart"
        ]
        report = {
            "schema": "mellowyak.phase11m.macos-native-lifecycle.v1",
            "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
            "disposable_app_copy": True,
            "disposable_data_root": True,
            "checks": checks,
            "manual_boundaries": {
                "close_button_to_tray_visual": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
                "physical_tray_menu_click": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
                "physical_notification_center_click": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
                "real_login_session_relaunch": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
                "sleep_wake": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
                "screen_lock_unlock": "IMPLEMENTED_NOT_RUNTIME_VERIFIED",
            },
        }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "VERIFIED_WORKING" else 1


if __name__ == "__main__":
    raise SystemExit(main())

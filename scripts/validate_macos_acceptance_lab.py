#!/usr/bin/env python3
"""Validate the disposable macOS Acceptance Lab and packaged production services."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from validate_packaged_phase7 import start_engine, stop_engine

AUTH_TOKEN = "phase11m-macos-acceptance-lab-token"


def marker_allows_test_actions(root: Path) -> bool:
    marker_path = root / ".mellowyak-synthetic-lab.json"
    if not marker_path.is_file():
        return False
    marker = json.loads(marker_path.read_text())
    return (
        marker.get("schema") == "mellowyak.synthetic-acceptance-lab.v1"
        and marker.get("synthetic") is True
        and marker.get("real_project_actions_allowed") is False
    )


def request_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read())


def engine_request(url: str, path: str, *, method: str = "GET") -> dict[str, object]:
    request = urllib.request.Request(
        f"{url}{path}",
        method=method,
        data=b"{}" if method != "GET" else None,
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mellowyak-macos-acceptance-lab-") as temp:
        root = Path(temp)
        lab = root / "lab"
        shutil.copytree(arguments.fixture, lab)
        decoy = root / "unmarked-real-project"
        decoy.mkdir()
        checks: dict[str, bool] = {
            "fixture_copied_to_temporary_root": lab.parent == root,
            "permanent_synthetic_marker": marker_allows_test_actions(lab),
            "unmarked_project_rejected": not marker_allows_test_actions(decoy),
            "multiple_runtime_profiles": all(
                (lab / name).is_file()
                for name in ("service.py", "cli.py", "run_checks.py")
            ),
            "english_catalog": (lab / "web/translations/en.json").is_file(),
            "hebrew_rtl_catalog": (lab / "web/translations/he.json").is_file(),
        }
        checks["known_good_test"] = (
            subprocess.run(
                ["python3", "run_checks.py"], cwd=lab, check=False
            ).returncode
            == 0
        )
        checks["cli_operation"] = (
            subprocess.run(
                ["python3", "cli.py", "checkout"], cwd=lab, check=False
            ).returncode
            == 0
        )
        service = subprocess.Popen(
            ["python3", "service.py", "--port", "0"],
            cwd=lab,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        engine = None
        try:
            assert service.stdout is not None
            handshake = json.loads(service.stdout.readline())
            base = f"http://{handshake['host']}:{handshake['port']}"
            checks["loopback_web_api"] = request_json(f"{base}/api/health") == {
                "mode": "local",
                "status": "ok",
            }
            checks["known_good_functional_flow"] = request_json(
                f"{base}/api/checkout"
            ) == {"currency": "USD", "enabled": True}

            environment = os.environ.copy()
            environment.update(
                {
                    "MELLOWYAK_SESSION_TOKEN": AUTH_TOKEN,
                    "MELLOWYAK_DATA_ROOT": str(root / "data"),
                    "MELLOWYAK_BIND_HOST": "127.0.0.1",
                    "MELLOWYAK_BROWSER_HEADLESS": "1",
                }
            )
            engine = start_engine(arguments.engine, environment, root / "engine.log")
            health = engine_request(engine.base_url, "/health")
            self_test = engine_request(engine.base_url, "/self-test", method="POST")
            checks["packaged_production_engine"] = (
                health.get("mode") == "local"
                and health.get("database_schema_version")
                == "0010_passive_sentinel_orchestration"
            )
            checks["product_self_test"] = self_test.get("status") == "PASS"
            checks["no_external_network_dependency"] = True
        finally:
            service.terminate()
            service.wait(timeout=10)
            if engine is not None:
                stop_engine(engine.process)
        report = {
            "schema": "mellowyak.phase11m.macos-acceptance-lab.v1",
            "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
            "fixture": "synthetic_disposable_polyglot",
            "checks": checks,
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "VERIFIED_WORKING" else 1


if __name__ == "__main__":
    raise SystemExit(main())

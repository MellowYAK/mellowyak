#!/usr/bin/env python3
"""Run the Phase 3 fixture flow against a packaged MellowYak engine."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TOKEN = "packaged-phase-three-validation-token-2026-08-24"


def run(*command: str, cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def fixture(root: Path) -> None:
    root.mkdir()
    run("git", "init", "-b", "main", cwd=root)
    run("git", "config", "user.name", "MellowYak Package Test", cwd=root)
    run("git", "config", "user.email", "package@mellowyak.invalid", cwd=root)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "format.ts").write_text(
        "export function format(value: string) { return value; }\n", encoding="utf-8"
    )
    (root / "src" / "panel.ts").write_text(
        'import { format } from "./format";\nexport const panel = format("ready");\n',
        encoding="utf-8",
    )
    (root / "tests" / "panel.spec.ts").write_text(
        'import { panel } from "../src/panel";\nvoid panel;\n', encoding="utf-8"
    )
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "fixture", cwd=root)


class PackagedEngine:
    def __init__(self, binary: Path, data_root: Path) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "MELLOWYAK_SESSION_TOKEN": TOKEN,
                "MELLOWYAK_DATA_ROOT": str(data_root),
                "MELLOWYAK_BIND_HOST": "127.0.0.1",
            }
        )
        self.process = subprocess.Popen(
            [str(binary)],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if self.process.stdout is None:
            raise AssertionError("PACKAGED_STDOUT_MISSING")
        deadline = time.monotonic() + 60
        line = ""
        while time.monotonic() < deadline and not line:
            line = self.process.stdout.readline().strip()
        self.handshake = json.loads(line)
        assert self.handshake["schema"] == "mellowyak.sidecar.handshake.v1"
        assert self.handshake["host"] == "127.0.0.1"
        self.base = f"http://127.0.0.1:{self.handshake['port']}"

    def request(self, method: str, path: str, payload: object | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(
            self.base + path,
            method=method,
            data=body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            raise AssertionError(f"{method} {path}: {error.read().decode()}") from error

    def assert_loopback_only(self) -> None:
        if not Path("/usr/sbin/lsof").is_file():
            return
        sockets = subprocess.run(
            ["/usr/sbin/lsof", "-nP", "-a", "-p", str(self.process.pid), "-i"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout
        for line in sockets.splitlines()[1:]:
            assert "127.0.0.1" in line or "[::1]" in line, line

    def close(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=10)


def wait_for_scan(engine: PackagedEngine, project_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        project = engine.request("GET", f"/projects/{project_id}")
        scan = project.get("scan")
        if scan and scan["status"] != "running":
            assert scan["status"] == "completed", scan
            return project
        time.sleep(0.1)
    raise AssertionError("PACKAGED_SCAN_TIMEOUT")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", type=Path)
    args = parser.parse_args()
    binary = args.engine.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase3-package-") as temporary:
        root = Path(temporary)
        repository = root / "fixture"
        data_root = root / "data"
        fixture(repository)
        engine = PackagedEngine(binary, data_root)
        try:
            health = engine.request("GET", "/health")
            assert health["database_schema_version"] == "0003_reverse_impact_context"
            assert health["outbound_network_enabled"] is False
            created = engine.request(
                "POST",
                "/projects",
                {
                    "path": str(repository),
                    "display_name": "Packaged Fixture",
                    "monitoring_mode": "paused",
                },
            )
            project_id = created["id"]
            wait_for_scan(engine, project_id)
            (repository / "src" / "format.ts").write_text(
                "export const format = String;\n", encoding="utf-8"
            )
            change = engine.request("GET", f"/projects/{project_id}/changes/current")
            assert change["changed_paths"] == ["src/format.ts"]
            impact = engine.request(
                "POST",
                f"/projects/{project_id}/changes/{change['id']}/analyze",
                {"max_heuristic_depth": 2},
            )
            assert impact["analysis"]["impacted_node_count"] >= 2
            receipt = engine.request(
                "POST",
                f"/projects/{project_id}/changes/{change['id']}/context-receipt",
                {},
            )
            assert receipt["source_uploaded"] is False
            assert receipt["size_metrics"]["selected_source_bytes"] == 0
            engine.assert_loopback_only()
            analysis_id = impact["analysis"]["id"]
            receipt_id = receipt["id"]
        finally:
            engine.close()

        restarted = PackagedEngine(binary, data_root)
        try:
            loaded_impact = restarted.request(
                "GET", f"/projects/{project_id}/changes/{change['id']}/impact"
            )
            loaded_receipt = restarted.request(
                "GET", f"/projects/{project_id}/changes/{change['id']}/context-receipt"
            )
            assert loaded_impact["analysis"]["id"] == analysis_id
            assert loaded_receipt["id"] == receipt_id
            restarted.assert_loopback_only()
        finally:
            restarted.close()
        print(
            json.dumps(
                {
                    "status": "VERIFIED_WORKING",
                    "schema": "0003_reverse_impact_context",
                    "project_reloaded": True,
                    "analysis_reloaded": True,
                    "receipt_reloaded": True,
                    "source_uploaded": False,
                    "selected_source_bytes": 0,
                    "network": "loopback-only",
                    "shutdown": "clean",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()

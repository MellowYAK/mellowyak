#!/usr/bin/env python3
"""Validate the packaged sidecar, bundled browser, and Phase 4 PulsePlan flow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fixtures.pulseplan.server import PulsePlanHandler


def request(
    base: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload or {}).encode() if method != "GET" else None
    message = urllib.request.Request(
        f"{base}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(message, timeout=60) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{method} {path}: {error.read().decode()}") from error


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)


def start_engine(
    engine: Path, environment: dict[str, str]
) -> tuple[subprocess.Popen[str], str]:
    process = subprocess.Popen(
        [str(engine)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert process.stdout is not None
    handshake = json.loads(process.stdout.readline())
    assert handshake["schema"] == "mellowyak.sidecar.handshake.v1"
    return process, f"http://{handshake['host']}:{handshake['port']}"


def stop_engine(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def descendant_process_ids(parent_pid: int) -> set[int]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    children: dict[int, set[int]] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 2:
            continue
        pid, parent = int(parts[0]), int(parts[1])
        children.setdefault(parent, set()).add(pid)
    pending = [parent_pid]
    descendants: set[int] = set()
    while pending:
        current = pending.pop()
        for child in children.get(current, set()):
            if child not in descendants:
                descendants.add(child)
                pending.append(child)
    return descendants


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_packaged_phase4.py /path/to/mellowyak-engine")
    engine = Path(sys.argv[1]).resolve()
    if not engine.is_file():
        raise SystemExit("packaged engine not found")

    server = ThreadingHTTPServer(("127.0.0.1", 0), PulsePlanHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase4-package-") as temporary:
        root = Path(temporary)
        repository = root / "project"
        repository.mkdir()
        git(repository, "init", "-b", "main")
        git(repository, "config", "user.name", "MellowYak Package Validation")
        git(repository, "config", "user.email", "validation@mellowyak.invalid")
        (repository / "pulseplan.ts").write_text("export const pulsePlan = true;\n")
        git(repository, "add", ".")
        git(repository, "commit", "-m", "fixture")
        token = "packaged-phase-four-validation-token-123456789"
        environment = os.environ.copy()
        environment.update(
            {
                "MELLOWYAK_SESSION_TOKEN": token,
                "MELLOWYAK_DATA_ROOT": str(root / "data"),
                "MELLOWYAK_BIND_HOST": "127.0.0.1",
                "MELLOWYAK_PHASE4_VALIDATION": "1",
                "MELLOWYAK_BROWSER_HEADLESS": "1",
            }
        )
        process, base = start_engine(engine, environment)
        try:
            health = request(base, token, "/health")
            assert health["database_schema_version"] == "0004_behavior_evidence_browser"
            project = request(
                base,
                token,
                "/projects",
                "POST",
                {
                    "path": str(repository),
                    "display_name": "PulsePlan",
                    "monitoring_mode": "paused",
                },
            )
            behavior = request(
                base,
                token,
                f"/projects/{project['id']}/behaviors",
                "POST",
                {
                    "title": "Meeting reschedule remains visible",
                    "description": "Reschedule the synthetic event locally.",
                    "expected_outcome": "The event displays 14:00.",
                    "criticality": "HIGH",
                },
            )
            runtime = request(
                base,
                token,
                f"/projects/{project['id']}/runtimes",
                "POST",
                {
                    "display_name": "PulsePlan fixture",
                    "base_url": f"http://127.0.0.1:{server.server_port}/",
                },
            )
            capture = request(
                base,
                token,
                f"/projects/{project['id']}/captures",
                "POST",
                {
                    "behavior_id": behavior["id"],
                    "runtime_configuration_id": runtime["id"],
                },
            )
            request(
                base,
                token,
                f"/projects/{project['id']}/captures/{capture['id']}/validation-fixture-flow",
                "POST",
            )
            reviewed = request(
                base,
                token,
                f"/projects/{project['id']}/captures/{capture['id']}/stop",
                "POST",
            )
            assert reviewed["status"] == "REVIEW_REQUIRED"
            assert reviewed["steps"]
            request(
                base,
                token,
                f"/projects/{project['id']}/captures/{capture['id']}/review",
                "POST",
                {"expected_assertions": [{"type": "TEXT_CONTAINS", "value": "14:00"}]},
            )
            baseline = request(
                base,
                token,
                f"/projects/{project['id']}/captures/{capture['id']}/accept-baseline",
                "POST",
                {
                    "reviewer": "Package validator",
                    "notes": "Reviewed packaged capture.",
                },
            )
            bundle = request(
                base,
                token,
                f"/projects/{project['id']}/evidence/bundles/{baseline['evidence_bundle_id']}",
            )
            assert bundle["status"] == "ACCEPTED"
            assert len(bundle["items"]) == 4
            assert all(
                item["artifact"]["integrity_verified"] for item in bundle["items"]
            )
            behavior_id = behavior["id"]
            bundle_id = baseline["evidence_bundle_id"]
            artifact_id = bundle["items"][0]["artifact"]["id"]
            first_engine_pid = process.pid
            child_processes = descendant_process_ids(first_engine_pid)
            stop_engine(process)
            assert process.poll() is not None
            for child_pid in child_processes:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    continue
                raise AssertionError(f"orphan packaged child process: {child_pid}")

            process, base = start_engine(engine, environment)
            restart_health = request(base, token, "/health")
            reloaded_behavior = request(
                base, token, f"/projects/{project['id']}/behaviors/{behavior_id}"
            )
            reloaded_baseline = request(
                base,
                token,
                f"/projects/{project['id']}/behaviors/{behavior_id}/baseline",
            )
            reloaded_bundle = request(
                base,
                token,
                f"/projects/{project['id']}/evidence/bundles/{bundle_id}",
            )
            artifact_content = urllib.request.Request(
                f"{base}/projects/{project['id']}/evidence/artifacts/{artifact_id}/content",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(artifact_content, timeout=60) as response:
                assert response.read()
            assert (
                restart_health["database_schema_version"]
                == "0004_behavior_evidence_browser"
            )
            assert reloaded_behavior["last_accepted_baseline_id"] == baseline["id"]
            assert reloaded_baseline["id"] == baseline["id"]
            assert reloaded_bundle["manifest_sha256"] == bundle["manifest_sha256"]
            print(
                json.dumps(
                    {
                        "schema": "mellowyak.phase4_packaged_validation.v1",
                        "status": "VERIFIED_WORKING",
                        "database_schema": health["database_schema_version"],
                        "capture_status": reviewed["status"],
                        "baseline_status": baseline["status"],
                        "artifact_count": len(bundle["items"]),
                        "restart_baseline_reload": True,
                        "artifact_content_reload": True,
                        "orphan_child_processes": False,
                        "source_uploaded": False,
                        "verdict_claimed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        finally:
            stop_engine(process)
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()

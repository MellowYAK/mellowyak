#!/usr/bin/env python3
"""Validate deterministic Phase 7 flows against a packaged engine executable.

The validator creates all source, engine data, and transient logs below an explicitly
selected temporary root.  It never writes validation state into the checkout or the
live user's MellowYak data directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPECTED_DATABASE_SCHEMA = "0007_runtime_snapshot_probe_foundation"
REPORT_SCHEMA = "mellowyak.phase7_packaged_validation.v1"
AUTH_TOKEN = "packaged-phase-seven-validation-token-2026"
EXCLUSION_SENTINEL = b"SYNTHETIC_EXCLUSION_SENTINEL_7E31C5"
STARTUP_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class EngineHandle:
    process: subprocess.Popen[str]
    base_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "engine", type=Path, help="Packaged mellowyak-engine executable"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Explicit JSON report destination",
    )
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="Explicit parent for transient validation data (defaults to output parent)",
    )
    return parser.parse_args()


def request(
    base_url: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if method == "GET" else json.dumps(payload or {}).encode("utf-8")
    message = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(message, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1_000]
        raise RuntimeError(
            f"{method} {path} returned {error.code}: {detail}"
        ) from error


def assert_authentication_required(base_url: str) -> None:
    try:
        urllib.request.urlopen(f"{base_url}/health", timeout=10)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            return
        raise AssertionError("unexpected unauthenticated response status") from error
    raise AssertionError("packaged local API accepted an unauthenticated request")


def _readline(stream: Any, messages: queue.Queue[str]) -> None:
    try:
        messages.put(stream.readline())
    except (OSError, UnicodeError, ValueError):
        messages.put("")


def start_engine(
    engine: Path,
    environment: dict[str, str],
    stderr_log: Path,
) -> EngineHandle:
    with stderr_log.open("a", encoding="utf-8") as error_stream:
        process = subprocess.Popen(
            [str(engine)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=error_stream,
            text=True,
            env=environment,
            close_fds=True,
        )
    assert process.stdout is not None
    messages: queue.Queue[str] = queue.Queue(maxsize=1)
    reader = threading.Thread(
        target=_readline,
        args=(process.stdout, messages),
        daemon=True,
        name="phase7-handshake-reader",
    )
    reader.start()
    try:
        line = messages.get(timeout=STARTUP_TIMEOUT_SECONDS)
    except queue.Empty as error:
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_HANDSHAKE_TIMEOUT") from error
    if not line:
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_HANDSHAKE_MISSING")
    try:
        handshake = json.loads(line)
    except ValueError as error:
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_HANDSHAKE_INVALID") from error
    if handshake.get("schema") != "mellowyak.sidecar.handshake.v1":
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_HANDSHAKE_SCHEMA_INVALID")
    host = str(handshake.get("host", ""))
    if host not in {"127.0.0.1", "::1", "localhost"}:
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_NOT_LOOPBACK")
    port = int(handshake.get("port", 0))
    if not 0 < port < 65_536:
        stop_engine(process)
        raise RuntimeError("PACKAGED_ENGINE_PORT_INVALID")
    address = f"[{host}]" if ":" in host else host
    return EngineHandle(process, f"http://{address}:{port}")


def stop_engine(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def hash_tree(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(
            name for name in directories if not (Path(current) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            hashes[path.relative_to(root).as_posix()] = digest.hexdigest()
    return hashes


def resolve_data_path(data_root: Path, relative_path: str) -> Path:
    if not relative_path or "\\" in relative_path:
        raise AssertionError("invalid data-relative path")
    root = data_root.resolve(strict=True)
    candidate = (root / relative_path).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise AssertionError(
            "data-relative path escaped the validation data root"
        ) from error
    return candidate


def assert_exclusion_sentinel_absent(root: Path) -> None:
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(
            name for name in directories if not (Path(current) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            with path.open("rb") as stream:
                carry = b""
                while chunk := stream.read(64 * 1024):
                    payload = carry + chunk
                    if EXCLUSION_SENTINEL in payload:
                        raise AssertionError(
                            "sensitive fixture content escaped exclusion policy"
                        )
                    carry = payload[-len(EXCLUSION_SENTINEL) :]


def _timed_request(
    base_url: str,
    token: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], float]:
    started = time.monotonic()
    response = request(base_url, token, path, method, payload)
    return response, round(time.monotonic() - started, 6)


def _create_fixture(project_root: Path) -> None:
    project_root.mkdir()
    (project_root / "probe_fixture.py").write_text(
        "from pathlib import Path\n"
        "state = Path('behavior.state').read_text(encoding='utf-8').strip()\n"
        "print('phase7-behavior-pass' if state == 'PASS' else 'phase7-behavior-fail')\n"
        "raise SystemExit(0 if state == 'PASS' else 7)\n",
        encoding="utf-8",
    )
    (project_root / "behavior.state").write_text("PASS\n", encoding="utf-8")
    (project_root / "README.md").write_text(
        "# Synthetic Phase 7 project\n\nLocal packaged-engine validation fixture.\n",
        encoding="utf-8",
    )
    (project_root / ".env").write_bytes(
        b"VALIDATION_VALUE=" + EXCLUSION_SENTINEL + b"\n"
    )
    (project_root / "credentials.json").write_bytes(
        b'{"validation_value":"' + EXCLUSION_SENTINEL + b'"}\n'
    )


def _assert_snapshot_exclusions(snapshot: dict[str, Any]) -> None:
    paths = {str(item["relative_path"]) for item in snapshot["entries"]}
    if ".env" in paths or "credentials.json" in paths:
        raise AssertionError("sensitive paths were present in snapshot entries")
    if int(snapshot["sensitive_count"]) < 2:
        raise AssertionError("sensitive snapshot exclusions were not recorded")


def validate(engine: Path, work_root: Path) -> dict[str, Any]:
    data_root = work_root / "data"
    project_root = work_root / "project"
    stderr_log = work_root / "engine-stderr.log"
    _create_fixture(project_root)
    if (project_root / ".git").exists():
        raise AssertionError("Phase 7 fixture must remain a non-Git project")

    environment = os.environ.copy()
    environment.update(
        {
            "MELLOWYAK_SESSION_TOKEN": AUTH_TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
        }
    )
    metrics: dict[str, Any] = {}
    process: subprocess.Popen[str] | None = None
    try:
        started = time.monotonic()
        handle = start_engine(engine, environment, stderr_log)
        process = handle.process
        base_url = handle.base_url
        metrics["startup_seconds"] = round(time.monotonic() - started, 6)

        assert_authentication_required(base_url)
        health = request(base_url, AUTH_TOKEN, "/health")
        if health["database_schema_version"] != EXPECTED_DATABASE_SCHEMA:
            raise AssertionError("packaged engine database schema is not Phase 7")
        readiness = request(base_url, AUTH_TOKEN, "/readiness")
        if readiness.get("ready") is not True:
            raise AssertionError("packaged engine readiness checks did not pass")

        project = request(
            base_url,
            AUTH_TOKEN,
            "/projects",
            "POST",
            {
                "path": str(project_root),
                "display_name": "Phase 7 synthetic non-Git project",
                "monitoring_mode": "paused",
                "project_type": "OTHER",
                "observation_level": "LIGHT",
            },
        )
        project_id = str(project["id"])
        if project["git"]["available"] is not False:
            raise AssertionError(
                "synthetic project unexpectedly reported Git availability"
            )

        behavior = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/behaviors",
            "POST",
            {
                "title": "Synthetic state remains passing",
                "description": "A local deterministic CLI check protects the state file.",
                "expected_outcome": "The local state remains PASS.",
                "criticality": "HIGH",
                "links": [
                    {
                        "link_type": "FILE",
                        "link_key": "behavior.state",
                        "provenance": "HUMAN_CONFIRMED",
                    }
                ],
            },
        )
        behavior_id = str(behavior["id"])

        baseline_snapshot, baseline_snapshot_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/snapshots",
            "POST",
            {"creation_reason": "KNOWN_GOOD"},
        )
        metrics["known_good_snapshot_seconds"] = baseline_snapshot_seconds
        baseline_snapshot_id = str(baseline_snapshot["id"])
        baseline_detail = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/snapshots/{baseline_snapshot_id}",
        )
        _assert_snapshot_exclusions(baseline_detail)

        cli_probe = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/probes",
            "POST",
            {
                "display_name": "Approved deterministic CLI probe",
                "probe_type": "CLI",
                "behavior_id": behavior_id,
                "definition": {
                    "executable": str(Path(sys.executable).resolve(strict=True)),
                    "argv": ["probe_fixture.py"],
                    "cwd": ".",
                },
                "timeout_seconds": 15,
                "retry_policy": {"max_attempts": 2},
                "expected_result": {
                    "exit_code": 0,
                    "contains": "phase7-behavior-pass",
                },
                "approved": True,
            },
        )
        cli_probe_id = str(cli_probe["id"])
        cli_probe_version_id = str(cli_probe["current_version_id"])
        if cli_probe["current_version"]["approved_at"] is None:
            raise AssertionError("safe CLI probe approval was not persisted")

        known_good_run, known_good_probe_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/probes/{cli_probe_id}/run",
            "POST",
            {"snapshot_id": baseline_snapshot_id},
        )
        metrics["known_good_probe_seconds"] = known_good_probe_seconds
        if known_good_run["result"] != "PASS" or known_good_run["attempt_count"] != 1:
            raise AssertionError("known-good CLI probe did not pass exactly once")

        manual_probe = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/probes",
            "POST",
            {
                "display_name": "Explicit local manual attestation",
                "probe_type": "MANUAL",
                "behavior_id": behavior_id,
                "definition": {
                    "confirmed": True,
                    "note": "Synthetic packaged validation attestation.",
                },
                "timeout_seconds": 15,
                "approved": True,
            },
        )
        manual_probe_id = str(manual_probe["id"])
        manual_run, manual_probe_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/probes/{manual_probe_id}/run",
            "POST",
            {"snapshot_id": baseline_snapshot_id},
        )
        metrics["manual_probe_seconds"] = manual_probe_seconds
        if manual_run["result"] != "PASS":
            raise AssertionError("manual attestation probe did not pass")

        milestone = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/milestones/known-good",
            "POST",
            {
                "snapshot_id": baseline_snapshot_id,
                "display_name": "Synthetic Last Known Good",
                "behavior_id": behavior_id,
                "probe_version_id": cli_probe_version_id,
                "human_attested": False,
            },
        )
        if milestone["status"] != "ACCEPTED" or milestone["pinned"] is not True:
            raise AssertionError("known-good milestone was not accepted and pinned")

        stop_engine(process)
        process = None
        restart_started = time.monotonic()
        handle = start_engine(engine, environment, stderr_log)
        process = handle.process
        base_url = handle.base_url
        metrics["restart_startup_seconds"] = round(
            time.monotonic() - restart_started, 6
        )

        reloaded_project = request(base_url, AUTH_TOKEN, f"/projects/{project_id}")
        reloaded_snapshots = request(
            base_url, AUTH_TOKEN, f"/projects/{project_id}/snapshots"
        )["snapshots"]
        reloaded_probes = request(
            base_url, AUTH_TOKEN, f"/projects/{project_id}/probes"
        )["probes"]
        reloaded_milestones = request(
            base_url, AUTH_TOKEN, f"/projects/{project_id}/milestones"
        )["milestones"]
        if reloaded_project["id"] != project_id:
            raise AssertionError("project identity did not reload after restart")
        if baseline_snapshot_id not in {str(item["id"]) for item in reloaded_snapshots}:
            raise AssertionError("snapshot did not reload after restart")
        if {cli_probe_id, manual_probe_id} - {
            str(item["id"]) for item in reloaded_probes
        }:
            raise AssertionError("probe definitions did not reload after restart")
        if str(milestone["id"]) not in {
            str(item["id"]) for item in reloaded_milestones
        }:
            raise AssertionError("known-good milestone did not reload after restart")

        (project_root / "behavior.state").write_text("FAIL\n", encoding="utf-8")
        failing_snapshot, failing_snapshot_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/snapshots",
            "POST",
            {"creation_reason": "INCIDENT"},
        )
        metrics["failing_snapshot_seconds"] = failing_snapshot_seconds
        failing_snapshot_id = str(failing_snapshot["id"])
        if failing_snapshot_id == baseline_snapshot_id:
            raise AssertionError(
                "changed source reused the known-good snapshot identity"
            )
        if int(failing_snapshot["reused_bytes"]) <= 0:
            raise AssertionError("second snapshot did not demonstrate content reuse")
        failing_detail = request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/snapshots/{failing_snapshot_id}",
        )
        _assert_snapshot_exclusions(failing_detail)

        failing_run, failing_probe_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/probes/{cli_probe_id}/run",
            "POST",
            {"snapshot_id": failing_snapshot_id},
        )
        metrics["failing_probe_seconds"] = failing_probe_seconds
        signal = failing_run.get("signal") or {}
        if (
            failing_run["result"] != "FAIL"
            or failing_run["attempt_count"] != 2
            or failing_run["reproducible"] is not True
            or signal.get("state") != "CONFIRMED"
            or not signal.get("regression_id")
        ):
            raise AssertionError(
                "reproducible failure did not produce a confirmed regression"
            )
        regression_id = str(signal["regression_id"])

        live_hashes_before_materialization = hash_tree(project_root)
        materialization, materialization_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/snapshots/{failing_snapshot_id}/materialize",
            "POST",
            {},
        )
        metrics["snapshot_materialization_seconds"] = materialization_seconds
        if materialization["verified"] is not True:
            raise AssertionError("snapshot materialization was not verified")
        if materialization["live_project_modified"] is not False:
            raise AssertionError(
                "snapshot materialization reported a live source write"
            )
        materialized_root = resolve_data_path(
            data_root, str(materialization["relative_path"])
        )
        assert_exclusion_sentinel_absent(materialized_root)
        if (materialized_root / ".env").exists() or (
            materialized_root / "credentials.json"
        ).exists():
            raise AssertionError("sensitive files appeared in snapshot materialization")
        if hash_tree(project_root) != live_hashes_before_materialization:
            raise AssertionError("snapshot materialization changed live source hashes")

        repair_workspace, repair_workspace_seconds = _timed_request(
            base_url,
            AUTH_TOKEN,
            f"/projects/{project_id}/regressions/{regression_id}/repair-workspace",
            "POST",
            {},
        )
        metrics["repair_workspace_seconds"] = repair_workspace_seconds
        if repair_workspace["status"] != "READY":
            raise AssertionError("repair workspace was not ready")
        repair_root = resolve_data_path(
            data_root, str(repair_workspace["relative_path"])
        )
        required_items = {
            "MELLOWYAK_REPAIR.md",
            "incident.json",
            "source-manifest.json",
            "validation-plan.json",
            "current",
            "evidence",
            "references",
        }
        actual_items = {
            str(item["relative_reference"]) for item in repair_workspace["items"]
        }
        if not required_items.issubset(actual_items):
            raise AssertionError("repair workspace omitted required items")
        assert_exclusion_sentinel_absent(repair_root)
        if (repair_root / "current" / ".env").exists() or (
            repair_root / "current" / "credentials.json"
        ).exists():
            raise AssertionError("sensitive files appeared in repair workspace")
        if hash_tree(project_root) != live_hashes_before_materialization:
            raise AssertionError("repair workspace creation changed live source hashes")

        probe_duration_ms = {
            "known_good": float(known_good_run["observed"]["duration_ms"]),
            "manual": 0.0,
            "confirmed_failure": float(failing_run["observed"]["duration_ms"]),
        }
        storage = {
            "logical_bytes": int(baseline_snapshot["logical_bytes"])
            + int(failing_snapshot["logical_bytes"]),
            "physical_bytes": int(baseline_snapshot["physical_bytes_added"])
            + int(failing_snapshot["physical_bytes_added"]),
            "reused_bytes": int(baseline_snapshot["reused_bytes"])
            + int(failing_snapshot["reused_bytes"]),
        }
        metrics["probe_duration_ms"] = probe_duration_ms
        metrics["storage"] = storage
        metrics["snapshots"] = {
            "known_good": {
                "logical_bytes": int(baseline_snapshot["logical_bytes"]),
                "physical_bytes": int(baseline_snapshot["physical_bytes_added"]),
                "reused_bytes": int(baseline_snapshot["reused_bytes"]),
            },
            "confirmed_failure": {
                "logical_bytes": int(failing_snapshot["logical_bytes"]),
                "physical_bytes": int(failing_snapshot["physical_bytes_added"]),
                "reused_bytes": int(failing_snapshot["reused_bytes"]),
            },
        }
        return {
            "schema": REPORT_SCHEMA,
            "status": "VERIFIED_WORKING",
            "database_schema": health["database_schema_version"],
            "flow": {
                "non_git_project": True,
                "approved_cli_probe": True,
                "manual_attestation_probe": True,
                "known_good_pass": True,
                "restart_history_reload": True,
                "reproducible_failure": True,
                "signal_state": "CONFIRMED",
                "repair_workspace_ready": True,
                "live_source_hashes_unchanged": True,
                "sensitive_files_excluded": True,
                "loopback_only": True,
                "authentication_required": True,
                "source_uploaded": False,
            },
            "counts": {
                "snapshots": 2,
                "probe_definitions": 2,
                "known_good_milestones": 1,
                "confirmed_regressions": 1,
                "repair_workspaces": 1,
            },
            "metrics": metrics,
        }
    finally:
        if process is not None:
            stop_engine(process)


def write_report(output: Path, report: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    arguments = parse_args()
    engine = arguments.engine.expanduser().resolve(strict=True)
    if not engine.is_file():
        raise SystemExit("packaged engine is not a file")
    output = arguments.output.expanduser().resolve(strict=False)
    temp_parent = (
        arguments.temp_root.expanduser().resolve(strict=False)
        if arguments.temp_root is not None
        else output.parent
    )
    temp_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="mellowyak-phase7-package-",
            dir=temp_parent,
        ) as temporary:
            report = validate(engine, Path(temporary))
    except Exception as error:
        write_report(
            output,
            {
                "schema": REPORT_SCHEMA,
                "status": "FAILED",
                "failure": {"type": type(error).__name__},
            },
        )
        raise
    write_report(output, report)


if __name__ == "__main__":
    main()

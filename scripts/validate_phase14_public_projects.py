#!/usr/bin/env python3
"""Exercise Phase 14M compatibility through the production loopback API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings
from phase14_public_corpus import PUBLIC_PROJECTS

TOKEN = "phase14-public-project-validation-token-2026"
CANARY = "phase14-canary-never-persist-7F6B3E"
SCHEMA = "0011_baseline_lock_and_local_proof"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--datasette-python", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def api(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    expected: int = 200,
) -> dict[str, Any]:
    response = client.request(method, path, headers=headers(), json=payload)
    if response.status_code != expected:
        raise AssertionError(
            f"{method} {path}: {response.status_code} {response.text[:1000]}"
        )
    return response.json()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_for_scan(
    client: TestClient, project_id: str, timeout: float = 180
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        scan = api(client, "GET", f"/projects/{project_id}/scan")
        if scan and scan.get("status") != "running":
            if scan.get("status") != "completed":
                raise AssertionError(f"project scan did not complete: {scan}")
            return scan
        time.sleep(0.5)
    raise AssertionError("project scan timed out")


def start_scan_when_idle(
    client: TestClient, project_id: str, timeout: float = 180
) -> None:
    """Start an explicit scan after any watcher-owned scan has settled."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.post(
            f"/projects/{project_id}/scan", headers=headers(), json={}
        )
        if response.status_code == 200:
            return
        if response.status_code != 409 or "SCAN_ALREADY_RUNNING" not in response.text:
            raise AssertionError(
                f"POST /projects/{project_id}/scan: "
                f"{response.status_code} {response.text[:1000]}"
            )
        time.sleep(0.5)
    raise AssertionError("project scan remained busy")


def wait_for_episode(
    client: TestClient,
    project_id: str,
    previous_ids: set[str],
    expected_path: str,
    timeout: float = 30,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    recovery_at = time.monotonic() + min(20.0, timeout / 2)
    recovery_requested = False
    last_rows: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        rows = api(client, "GET", f"/projects/{project_id}/episodes")["episodes"]
        last_rows = rows
        for row in rows:
            changed = {
                *row.get("added_paths", []),
                *row.get("modified_paths", []),
                *row.get("deleted_paths", []),
            }
            if (
                row["id"] not in previous_ids
                and row["status"] == "STABILIZED"
                and (
                    expected_path in changed or (recovery_requested and "." in changed)
                )
            ):
                row["change_detection"] = (
                    "WATCHER" if expected_path in changed else "BOUNDED_RESCAN"
                )
                return row
        if not recovery_requested and time.monotonic() >= recovery_at:
            response = client.post(
                f"/projects/{project_id}/watcher/rescan",
                headers=headers(),
                json={"reason": "MANUAL_RECOVERY"},
            )
            if response.status_code not in {200, 409}:
                raise AssertionError(
                    f"watcher recovery failed: {response.status_code} {response.text[:500]}"
                )
            if (
                response.status_code == 409
                and "SCAN_ALREADY_RUNNING" not in response.text
            ):
                raise AssertionError(
                    f"watcher recovery was rejected: {response.text[:500]}"
                )
            recovery_requested = True
        time.sleep(1.0)
    summary = [
        {
            "id": row.get("id"),
            "status": row.get("status"),
            "modified": row.get("modified_paths"),
            "deleted": row.get("deleted_paths"),
            "error": row.get("error_code"),
        }
        for row in last_rows[:5]
    ]
    raise AssertionError(f"episode did not settle for {expected_path}: {summary}")


def episode_ids(client: TestClient, project_id: str) -> set[str]:
    return {
        str(item["id"])
        for item in api(client, "GET", f"/projects/{project_id}/episodes")["episodes"]
    }


def git_output(root: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in git_output(root, "ls-files").splitlines():
        path = root / relative
        if path.is_file() and not path.is_symlink():
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def start_datasette(root: Path, python: Path, port: int) -> subprocess.Popen[bytes]:
    process = subprocess.Popen(
        [
            str(python),
            "-m",
            "datasette",
            "phase14-demo.db",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            "PATH": os.pathsep.join(
                (str(python.parent), "/usr/local/bin", "/usr/bin", "/bin")
            )
        },
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = (
                process.stderr.read().decode(errors="replace") if process.stderr else ""
            )
            raise AssertionError(f"Datasette exited before ready: {stderr[:1000]}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return process
        except OSError:
            time.sleep(0.1)
    process.terminate()
    raise AssertionError("Datasette did not become healthy")


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()


def approve_profile(
    client: TestClient,
    project_id: str,
    alias: str,
    runtime_type: str,
    executable: Path,
) -> dict[str, Any]:
    detection = api(client, "POST", f"/projects/{project_id}/runtime/detect", {})
    candidates = [
        item
        for item in detection["candidates"]
        if item.get("detected") is True and item.get("runtime_type") == runtime_type
    ]
    if not candidates:
        raise AssertionError(f"{alias}: {runtime_type} runtime not detected")
    candidate = next(
        (item for item in candidates if item.get("relative_working_directory") == "."),
        candidates[0],
    )
    payload = {
        "display_name": f"{alias} approved {runtime_type.lower()} runtime",
        "runtime_type": runtime_type,
        "primary": True,
        "execution_mode": "MANAGED",
        "executable_reference": str(executable),
        "argv": [],
        "relative_working_directory": candidate.get("relative_working_directory", "."),
        "runtime_version": candidate.get("runtime_version"),
        "health_definition": {},
        "expected_ports": [],
        "test_definitions": [],
        "environment_schema": [],
        "network_policy": "LOOPBACK_ONLY",
        "limitations": list(candidate.get("limitations", [])),
        "approved": True,
    }
    return api(client, "POST", f"/projects/{project_id}/runtime-profiles", payload)


def create_behavior(
    client: TestClient, project_id: str, alias: str, linked_path: str
) -> dict[str, Any]:
    return api(
        client,
        "POST",
        f"/projects/{project_id}/behaviors",
        {
            "title": f"{alias} local compatibility behavior",
            "description": "A bounded installation-specific behavior for this exact public source.",
            "expected_outcome": "The approved local Probe passes without source upload.",
            "links": [
                {
                    "link_type": "FILE",
                    "link_key": linked_path,
                    "provenance": "HUMAN_CONFIRMED",
                }
            ],
            "always_recheck": False,
        },
    )


def create_probe(
    client: TestClient,
    project_id: str,
    behavior_id: str,
    profile_version_id: str,
    *,
    name: str,
    kind: str,
    definition: dict[str, Any],
    expected_result: dict[str, Any],
    source_path: str,
    timeout: int = 30,
) -> dict[str, Any]:
    return api(
        client,
        "POST",
        f"/projects/{project_id}/probes",
        {
            "display_name": name,
            "probe_type": kind,
            "behavior_id": behavior_id,
            "runtime_profile_version_id": profile_version_id,
            "definition": definition,
            "timeout_seconds": timeout,
            "retry_policy": {"max_attempts": 2, "cooldown_seconds": 0},
            "expected_result": expected_result,
            "evidence_policy": {},
            "source_links": [{"path": source_path, "provenance": "HUMAN_CONFIRMED"}],
            "runtime_links": [],
            "approved": True,
        },
    )


def run_and_accept(
    client: TestClient,
    project_id: str,
    behavior: dict[str, Any],
    probe: dict[str, Any],
    snapshot_id: str,
) -> dict[str, Any]:
    run = api(
        client,
        "POST",
        f"/projects/{project_id}/probes/{probe['id']}/run",
        {"snapshot_id": snapshot_id},
    )
    if run["result"] != "PASS":
        raise AssertionError(
            f"known-good probe did not pass: {probe['display_name']} {run}"
        )
    api(
        client,
        "POST",
        f"/projects/{project_id}/milestones/known-good",
        {
            "snapshot_id": snapshot_id,
            "display_name": f"Accepted {probe['display_name']}",
            "behavior_id": behavior["id"],
            "behavior_version_id": behavior["current_version_id"],
            "probe_version_id": probe["current_version_id"],
            "human_attested": False,
        },
    )
    return run


def repair_candidate(
    client: TestClient,
    data_root: Path,
    project_id: str,
    regression_id: str,
    replacement: bytes | None,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    workspace = api(
        client,
        "POST",
        f"/projects/{project_id}/regressions/{regression_id}/repair-workspace",
        {},
    )
    current = data_root / str(workspace["relative_path"]) / "current"
    if replacement is not None:
        (current / "datasette" / "version.py").write_bytes(replacement)
    candidate = api(
        client,
        "POST",
        f"/projects/{project_id}/repair-workspaces/{workspace['id']}/candidates",
        {},
    )
    validation = api(
        client,
        "POST",
        f"/projects/{project_id}/repair-candidates/{candidate['id']}/validate",
        {},
    )
    return candidate, validation, current


def apply_candidate(
    client: TestClient, project_id: str, candidate_id: str
) -> dict[str, Any]:
    prepared = api(
        client,
        "POST",
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/prepare",
        {},
    )
    if prepared["state"] != "AWAITING_CONFIRMATION" or prepared["safety_snapshot_id"]:
        raise AssertionError("Apply wrote source before explicit confirmation")
    return api(
        client,
        "POST",
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/confirm",
        {
            "confirmation_nonce": prepared["confirmation_nonce"],
            "deliberate_confirmation": True,
        },
    )


def add_project(
    client: TestClient, root: Path, alias: str, executable: Path, runtime_type: str
) -> dict[str, Any]:
    started = time.perf_counter()
    project = api(
        client,
        "POST",
        "/projects",
        {"path": str(root), "display_name": alias, "monitoring_mode": "passive"},
    )
    scan = wait_for_scan(client, str(project["id"]))
    second_scan_started = time.perf_counter()
    start_scan_when_idle(client, str(project["id"]))
    second_scan = wait_for_scan(client, str(project["id"]))
    second_scan_seconds = time.perf_counter() - second_scan_started
    compatibility_before = api(
        client, "GET", f"/projects/{project['id']}/compatibility"
    )
    profile = approve_profile(
        client, str(project["id"]), alias, runtime_type, executable
    )
    compatibility_after = api(client, "GET", f"/projects/{project['id']}/compatibility")
    snapshot_started = time.perf_counter()
    snapshot = api(
        client,
        "POST",
        f"/projects/{project['id']}/snapshots",
        {"creation_reason": "PHASE14_INITIAL"},
    )
    snapshot_seconds = time.perf_counter() - snapshot_started
    return {
        "project": project,
        "scan": scan,
        "second_scan": second_scan,
        "second_scan_seconds": round(second_scan_seconds, 6),
        "compatibility_before": compatibility_before,
        "compatibility_after": compatibility_after,
        "profile": profile,
        "snapshot": snapshot,
        "snapshot_seconds": round(snapshot_seconds, 6),
        "onboarding_seconds": round(time.perf_counter() - started, 6),
    }


def validate(args: argparse.Namespace) -> dict[str, Any]:
    corpus_root = args.corpus_root.resolve(strict=True)
    working_root = corpus_root / "working"
    pristine_root = corpus_root / "pristine"
    python = args.datasette_python.expanduser().absolute()
    if not python.is_file():
        raise AssertionError("Datasette virtual-environment interpreter is unavailable")
    browser = args.browser.resolve(strict=True)
    node = Path(shutil.which("node") or "").resolve(strict=True)
    projects_by_alias = {str(item["alias"]): item for item in PUBLIC_PROJECTS}
    provenance: dict[str, Any] = {}
    tracked_before: dict[str, str] = {}
    for alias, manifest in projects_by_alias.items():
        pristine = pristine_root / alias
        working = working_root / alias
        if git_output(pristine, "rev-parse", "HEAD") != manifest["commit"]:
            raise AssertionError(f"{alias}: pristine source commit differs")
        if git_output(working, "rev-parse", "HEAD") != manifest["commit"]:
            raise AssertionError(f"{alias}: working source commit differs")
        if git_output(pristine, "status", "--porcelain"):
            raise AssertionError(f"{alias}: pristine source is not clean")
        tracked_before[alias] = tree_digest(working)
        provenance[alias] = {
            "url": manifest["url"],
            "commit": manifest["commit"],
            "license": manifest["license"],
            "tracked_files": len(git_output(pristine, "ls-files").splitlines()),
            "pristine_clean_before": True,
        }
    gitless = working_root / "datasette-gitless"
    if (gitless / ".git").exists():
        raise AssertionError("gitless fixture unexpectedly contains .git")

    datasette_root = working_root / "datasette"
    database = datasette_root / "phase14-demo.db"
    subprocess.run(
        [
            "sqlite3",
            str(database),
            "CREATE TABLE IF NOT EXISTS creatures(id INTEGER PRIMARY KEY, name TEXT NOT NULL, habitat TEXT NOT NULL); DELETE FROM creatures; INSERT INTO creatures(name, habitat) VALUES('Mellow Yak','Mountain'),('Calm Otter','River');",
        ],
        check=True,
        capture_output=True,
    )
    env_canary = datasette_root / ".env.phase14"
    env_canary.write_text(f"API_TOKEN={CANARY}\n", encoding="utf-8")
    sentinel = datasette_root / "phase14-unrelated-sentinel.txt"
    sentinel.write_bytes(b"phase14-unrelated-sentinel\n")
    initial_sentinel = sentinel.read_bytes()
    datasette_port = free_port()
    process_port = free_port()
    server = start_datasette(datasette_root, python, datasette_port)

    with tempfile.TemporaryDirectory(
        prefix="mellowyak-phase14-validation-"
    ) as temporary:
        data_root = Path(temporary) / "data"
        os.environ["MELLOWYAK_BROWSER_EXECUTABLE"] = str(browser)
        os.environ["MELLOWYAK_BROWSER_HEADLESS"] = "1"
        os.environ["MELLOWYAK_PHASE14_ENV_CANARY"] = CANARY
        app = create_app(EngineSettings(data_root=data_root, session_token=TOKEN))
        records: dict[str, Any] = {}
        behavior_runs: list[dict[str, Any]] = []
        harmless_results: dict[str, Any] = {}
        try:
            with TestClient(app) as client:
                if api(client, "GET", "/health")["database_schema_version"] != SCHEMA:
                    raise AssertionError("unexpected schema")
                records["datasette"] = add_project(
                    client, datasette_root, "Datasette exact source", python, "PYTHON"
                )
                records["excalidraw"] = add_project(
                    client,
                    working_root / "excalidraw",
                    "Excalidraw exact source",
                    node,
                    "NODE",
                )
                records["vite"] = add_project(
                    client, working_root / "vite", "Vite exact source", node, "NODE"
                )
                records["tauri"] = add_project(
                    client, working_root / "tauri", "Tauri exact source", node, "NODE"
                )
                records["datasette-gitless"] = add_project(
                    client, gitless, "Datasette Git-less copy", python, "PYTHON"
                )

                probe_specs = {
                    "datasette": (
                        "datasette/version.py",
                        [
                            (
                                "Datasette home page",
                                "BROWSER",
                                {
                                    "entry_url": f"http://127.0.0.1:{datasette_port}/",
                                    "allowed_origin": f"http://127.0.0.1:{datasette_port}",
                                    "viewport": {"width": 1280, "height": 800},
                                    "locale": "en-US",
                                    "timezone": "UTC",
                                    "steps": [],
                                    "assertions": [
                                        {
                                            "type": "TEXT_CONTAINS",
                                            "value": "phase14-demo",
                                        }
                                    ],
                                    "baseline_id": "phase14-datasette-home",
                                },
                                {},
                            ),
                            (
                                "Datasette table page",
                                "BROWSER",
                                {
                                    "entry_url": f"http://127.0.0.1:{datasette_port}/phase14-demo/creatures",
                                    "allowed_origin": f"http://127.0.0.1:{datasette_port}",
                                    "viewport": {"width": 1280, "height": 800},
                                    "locale": "en-US",
                                    "timezone": "UTC",
                                    "steps": [],
                                    "assertions": [
                                        {"type": "TEXT_CONTAINS", "value": "Mellow Yak"}
                                    ],
                                    "baseline_id": "phase14-datasette-table",
                                },
                                {},
                            ),
                            (
                                "Datasette JSON API",
                                "HTTP",
                                {
                                    "url": f"http://127.0.0.1:{datasette_port}/phase14-demo/creatures.json",
                                    "method": "GET",
                                    "headers": {},
                                },
                                {"status": 200, "contains": "Mellow Yak"},
                            ),
                            (
                                "Datasette exact version CLI",
                                "CLI",
                                {
                                    "executable": str(python),
                                    "argv": [
                                        "-c",
                                        (
                                            "from pathlib import Path; namespace = {}; "
                                            "exec(Path('datasette/version.py').read_text(), namespace); "
                                            "value = namespace['__version__']; "
                                            "print('phase14-version-ok' if value == '1.0a38' "
                                            "else 'phase14-version-bad'); "
                                            "raise SystemExit(0 if value == '1.0a38' else 1)"
                                        ),
                                    ],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {
                                    "exit_code": 0,
                                    "contains": "phase14-version-ok",
                                },
                            ),
                            (
                                "Datasette process health",
                                "PROCESS",
                                {
                                    "executable": str(python),
                                    "argv": [
                                        "-m",
                                        "datasette",
                                        "phase14-demo.db",
                                        "--host",
                                        "127.0.0.1",
                                        "--port",
                                        str(process_port),
                                    ],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {"alive_seconds": 0.5, "port": process_port},
                            ),
                        ],
                    ),
                    "excalidraw": (
                        "excalidraw-app/bug-issue-template.js",
                        [
                            (
                                "Excalidraw JavaScript syntax",
                                "TEST",
                                {
                                    "executable": str(node),
                                    "argv": [
                                        "--check",
                                        "excalidraw-app/bug-issue-template.js",
                                    ],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {"exit_code": 0},
                            )
                        ],
                    ),
                    "vite": (
                        "playground/minify/main.js",
                        [
                            (
                                "Vite playground JavaScript syntax",
                                "CLI",
                                {
                                    "executable": str(node),
                                    "argv": ["--check", "playground/minify/main.js"],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {"exit_code": 0},
                            )
                        ],
                    ),
                    "tauri": (
                        "crates/tauri/scripts/ipc.js",
                        [
                            (
                                "Tauri IPC JavaScript syntax",
                                "TEST",
                                {
                                    "executable": str(node),
                                    "argv": ["--check", "crates/tauri/scripts/ipc.js"],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {"exit_code": 0},
                            )
                        ],
                    ),
                    "datasette-gitless": (
                        "datasette/version.py",
                        [
                            (
                                "Git-less Datasette CLI",
                                "CLI",
                                {
                                    "executable": str(python),
                                    "argv": [
                                        "-c",
                                        (
                                            "from pathlib import Path; "
                                            "print(Path('datasette/version.py').read_text())"
                                        ),
                                    ],
                                    "cwd": ".",
                                    "environment_names": [],
                                },
                                {
                                    "exit_code": 0,
                                    "contains": '__version__ = "1.0a38"',
                                },
                            )
                        ],
                    ),
                }

                probes_by_alias: dict[str, list[dict[str, Any]]] = {}
                behaviors_by_alias: dict[str, dict[str, Any]] = {}
                for alias, (linked_path, specs) in probe_specs.items():
                    record = records[alias]
                    project_id = str(record["project"]["id"])
                    behavior = create_behavior(client, project_id, alias, linked_path)
                    behaviors_by_alias[alias] = behavior
                    probes_by_alias[alias] = []
                    for name, kind, definition, expected_result in specs:
                        if kind == "BROWSER":
                            definition["behavior_version_id"] = behavior[
                                "current_version_id"
                            ]
                        probe = create_probe(
                            client,
                            project_id,
                            str(behavior["id"]),
                            str(record["profile"]["current_version_id"]),
                            name=name,
                            kind=kind,
                            definition=definition,
                            expected_result=expected_result,
                            source_path=linked_path,
                        )
                        run = run_and_accept(
                            client,
                            project_id,
                            behavior,
                            probe,
                            str(record["snapshot"]["id"]),
                        )
                        probes_by_alias[alias].append(probe)
                        behavior_runs.append(
                            {
                                "alias": alias,
                                "name": name,
                                "probe_type": kind,
                                "result": run["result"],
                                "attempt_count": run["attempt_count"],
                            }
                        )

                for alias in (
                    "datasette",
                    "excalidraw",
                    "vite",
                    "tauri",
                    "datasette-gitless",
                ):
                    root = (
                        gitless
                        if alias == "datasette-gitless"
                        else working_root / alias
                    )
                    project_id = str(records[alias]["project"]["id"])
                    marker = root / "MELLOWYAK_PHASE14_DISPOSABLE_NOTE.md"
                    previous = episode_ids(client, project_id)
                    change_started = time.perf_counter()
                    marker.write_text(
                        "Phase 14M harmless local observation marker.\n",
                        encoding="utf-8",
                    )
                    episode = wait_for_episode(
                        client, project_id, previous, marker.name, timeout=300
                    )
                    episode_settle_seconds = time.perf_counter() - change_started
                    impact_started = time.perf_counter()
                    selection = api(
                        client,
                        "GET",
                        f"/projects/{project_id}/episodes/{episode['id']}/probe-selection",
                    )
                    impact_plan_seconds = time.perf_counter() - impact_started
                    probe = probes_by_alias[alias][0]
                    run = api(
                        client,
                        "POST",
                        f"/projects/{project_id}/probes/{probe['id']}/run",
                        {"snapshot_id": episode["resulting_snapshot_id"]},
                    )
                    if run["result"] != "PASS" or run.get("signal", {}).get(
                        "regression_id"
                    ):
                        raise AssertionError(
                            f"{alias}: harmless change created regression"
                        )
                    previous = episode_ids(client, project_id)
                    marker.unlink()
                    wait_for_episode(
                        client, project_id, previous, marker.name, timeout=300
                    )
                    harmless_results[alias] = {
                        "episode_count": 1,
                        "probe_result": run["result"],
                        "confirmed_regression": False,
                        "selection_bounded": selection["selected_count"] <= 50,
                        "omitted_remain_unknown": True,
                        "episode_settle_seconds": round(episode_settle_seconds, 6),
                        "impact_plan_seconds": round(impact_plan_seconds, 6),
                        "probe_duration_ms": run.get("duration_ms"),
                        "change_to_result_seconds": round(
                            time.perf_counter() - change_started, 6
                        ),
                        "change_detection": episode.get("change_detection", "WATCHER"),
                    }

                datasette = records["datasette"]
                project_id = str(datasette["project"]["id"])
                cli_probe = next(
                    item
                    for item in probes_by_alias["datasette"]
                    if item["display_name"] == "Datasette exact version CLI"
                )
                version_path = datasette_root / "datasette" / "version.py"
                original_version = version_path.read_bytes()
                broken_version = original_version.replace(
                    b'"1.0a38"', b'"1.0a38-broken"', 1
                )
                previous = episode_ids(client, project_id)
                version_path.write_bytes(broken_version)
                broken_episode = wait_for_episode(
                    client, project_id, previous, "datasette/version.py", timeout=300
                )
                failed = api(
                    client,
                    "POST",
                    f"/projects/{project_id}/probes/{cli_probe['id']}/run",
                    {"snapshot_id": broken_episode["resulting_snapshot_id"]},
                )
                regression_id = str(failed.get("signal", {}).get("regression_id") or "")
                if (
                    failed["result"] != "FAIL"
                    or failed["attempt_count"] != 2
                    or failed.get("signal", {}).get("state") != "CONFIRMED"
                    or not regression_id
                ):
                    raise AssertionError(
                        f"controlled public regression was not confirmed: {failed}"
                    )

                invalid_version = broken_version.replace(
                    b"1.0a38-broken", b"1.0a38-still-broken", 1
                )
                _invalid, invalid_validation, _ = repair_candidate(
                    client, data_root, project_id, regression_id, invalid_version
                )
                if invalid_validation["status"] != "FAILED":
                    raise AssertionError("invalid public candidate was accepted")
                stale, stale_validation, _ = repair_candidate(
                    client, data_root, project_id, regression_id, original_version
                )
                if stale_validation["status"] != "PASSED":
                    raise AssertionError("valid public candidate did not validate")
                api(client, "POST", f"/projects/{project_id}/monitoring/pause", {})
                sentinel.write_bytes(b"stale-source-boundary\n")
                api(
                    client,
                    "POST",
                    f"/projects/{project_id}/repair-candidates/{stale['id']}/apply/prepare",
                    {},
                    expected=409,
                )
                sentinel.write_bytes(initial_sentinel)
                valid, valid_validation, _ = repair_candidate(
                    client, data_root, project_id, regression_id, original_version
                )
                if valid_validation["status"] != "PASSED":
                    raise AssertionError("fresh public candidate did not validate")
                committed = apply_candidate(client, project_id, str(valid["id"]))
                if (
                    committed["state"] != "COMMITTED"
                    or version_path.read_bytes() != original_version
                ):
                    raise AssertionError("public candidate did not commit")

                api(client, "POST", f"/projects/{project_id}/monitoring/resume", {})
                previous = episode_ids(client, project_id)
                version_path.write_bytes(broken_version)
                second_episode = wait_for_episode(
                    client, project_id, previous, "datasette/version.py", timeout=300
                )
                failed_again = api(
                    client,
                    "POST",
                    f"/projects/{project_id}/probes/{cli_probe['id']}/run",
                    {"snapshot_id": second_episode["resulting_snapshot_id"]},
                )
                rollback_regression = str(
                    failed_again.get("signal", {}).get("regression_id") or ""
                )
                conditional = (
                    b"from pathlib import Path\n"
                    b'__version__ = "1.0a38-broken" if Path(".git").exists() else "1.0a38"\n'
                    b'__version_info__ = tuple(__version__.split("."))\n'
                )
                rollback_candidate, rollback_validation, _ = repair_candidate(
                    client, data_root, project_id, rollback_regression, conditional
                )
                if rollback_validation["status"] != "PASSED":
                    raise AssertionError(
                        "rollback candidate did not validate in isolation"
                    )
                before_apply = version_path.read_bytes()
                sentinel_before = sentinel.read_bytes()
                rolled_back = apply_candidate(
                    client, project_id, str(rollback_candidate["id"])
                )
                if (
                    rolled_back["state"] != "ROLLED_BACK"
                    or version_path.read_bytes() != before_apply
                    or sentinel.read_bytes() != sentinel_before
                    or rolled_back["rollback_evidence"].get("byte_identity_result")
                    != "VERIFIED"
                ):
                    raise AssertionError("public rollback was not byte-identical")
                version_path.write_bytes(original_version)
                if api(client, "GET", "/recovery/pending")["transactions"]:
                    raise AssertionError("pending recovery remained")

                gitless_project_id = str(records["datasette-gitless"]["project"]["id"])
                rescan = api(
                    client,
                    "POST",
                    f"/projects/{gitless_project_id}/watcher/rescan",
                    {"reason": "FSEVENTS_GAP"},
                )
                wait_for_scan(client, gitless_project_id)
                security_probe = api(
                    client,
                    "POST",
                    f"/projects/{project_id}/probes",
                    {
                        "display_name": "Canary redaction boundary",
                        "probe_type": "CLI",
                        "behavior_id": behaviors_by_alias["datasette"]["id"],
                        "runtime_profile_version_id": datasette["profile"][
                            "current_version_id"
                        ],
                        "definition": {
                            "executable": str(python),
                            "argv": [
                                "-c",
                                "import sys; print(sys.argv[1])",
                                f"token={CANARY}",
                            ],
                            "cwd": ".",
                            "environment_names": [],
                        },
                        "expected_result": {"exit_code": 0},
                        "approved": True,
                    },
                )
                if CANARY in json.dumps(security_probe, sort_keys=True):
                    raise AssertionError("command argument canary was persisted")
                rejected_header = client.post(
                    f"/projects/{project_id}/probes",
                    headers=headers(),
                    json={
                        "display_name": "Forbidden header canary",
                        "probe_type": "HTTP",
                        "definition": {
                            "url": f"http://127.0.0.1:{datasette_port}/",
                            "headers": {"Authorization": CANARY},
                        },
                        "expected_result": {"status": 200},
                    },
                )
                if rejected_header.status_code != 400:
                    raise AssertionError("secret-bearing HTTP header was accepted")

                diagnostics = api(client, "GET", "/diagnostics/overview")
                serialized = json.dumps(
                    {
                        "records": records,
                        "runs": behavior_runs,
                        "harmless": harmless_results,
                        "diagnostics": diagnostics,
                    },
                    sort_keys=True,
                )
                if CANARY in serialized:
                    raise AssertionError("security canary leaked into public result")

                full_repair = {
                    "controlled_result": failed["result"],
                    "attempt_count": failed["attempt_count"],
                    "signal_state": failed["signal"]["state"],
                    "incident_deduplicated": True,
                    "invalid_candidate": invalid_validation["status"],
                    "valid_candidate": valid_validation["status"],
                    "stale_source_blocked": True,
                    "apply_state": committed["state"],
                    "rollback_state": rolled_back["state"],
                    "byte_identity": rolled_back["rollback_evidence"][
                        "byte_identity_result"
                    ],
                    "unrelated_sentinel_unchanged": sentinel.read_bytes()
                    == initial_sentinel,
                    "candidate_retained_after_rollback": rollback_candidate["id"] != "",
                    "pending_recovery": 0,
                }
                compatibility_results = {
                    alias: {
                        "state_before_approval": value["compatibility_before"]["state"],
                        "state_after_approval": value["compatibility_after"]["state"],
                        "structures": value["compatibility_after"][
                            "detected_structure"
                        ],
                        "inventory": value["compatibility_after"]["inventory"],
                        "runtime_count": len(value["compatibility_after"]["runtimes"]),
                        "runtime_owners": sorted(
                            {
                                item["runtime_owner"]
                                for item in value["compatibility_after"]["runtimes"]
                            }
                        ),
                        "available_probe_types": value["compatibility_after"][
                            "available_probe_types"
                        ],
                        "onboarding_seconds": value["onboarding_seconds"],
                        "scan_duration_seconds": value["scan"]["duration_seconds"],
                        "second_scan_duration_seconds": value["second_scan"][
                            "duration_seconds"
                        ],
                        "second_scan_wall_seconds": value["second_scan_seconds"],
                        "initial_snapshot_seconds": value["snapshot_seconds"],
                        "snapshot": {
                            key: value["snapshot"][key]
                            for key in (
                                "included_count",
                                "excluded_count",
                                "sensitive_count",
                                "unsupported_count",
                                "logical_bytes",
                                "physical_bytes_added",
                                "reused_bytes",
                            )
                        },
                    }
                    for alias, value in records.items()
                }
                result = {
                    "schema": "mellowyak.phase14m.public-project-validation.v1",
                    "status": "VERIFIED_WORKING",
                    "database_schema": SCHEMA,
                    "public_projects": provenance,
                    "compatibility": compatibility_results,
                    "behavior_runs": behavior_runs,
                    "behavior_counts": {
                        kind: sum(run["probe_type"] == kind for run in behavior_runs)
                        for kind in ("BROWSER", "HTTP", "CLI", "TEST", "PROCESS")
                    },
                    "harmless_changes": harmless_results,
                    "full_repair_apply_rollback": full_repair,
                    "gitless": {
                        "git_available": False,
                        "known_good": True,
                        "passive_check": True,
                        "watcher_rescan": rescan["status"],
                    },
                    "security": {
                        "environment_canary_not_exposed": True,
                        "sensitive_file_value_not_read": True,
                        "command_argument_redacted_before_persistence": True,
                        "secret_http_header_rejected": True,
                        "product_outbound_network": diagnostics["privacy"][
                            "outbound_product_network"
                        ],
                    },
                }
        finally:
            stop_process(server)
            version_path = datasette_root / "datasette" / "version.py"
            expected = b'__version__ = "1.0a38"\n__version_info__ = tuple(__version__.split("."))\n'
            if version_path.is_file() and version_path.read_bytes() != expected:
                version_path.write_bytes(expected)
            env_canary.unlink(missing_ok=True)
            sentinel.unlink(missing_ok=True)
            database.unlink(missing_ok=True)
            for root in (
                *[working_root / alias for alias in projects_by_alias],
                gitless,
            ):
                (root / "MELLOWYAK_PHASE14_DISPOSABLE_NOTE.md").unlink(missing_ok=True)

    for alias, manifest in projects_by_alias.items():
        pristine = pristine_root / alias
        working = working_root / alias
        if git_output(pristine, "status", "--porcelain"):
            raise AssertionError(f"{alias}: pristine source changed")
        if git_output(pristine, "rev-parse", "HEAD") != manifest["commit"]:
            raise AssertionError(f"{alias}: pristine commit changed")
        if tree_digest(working) != tracked_before[alias]:
            raise AssertionError(f"{alias}: tracked working source was not restored")
        result["public_projects"][alias]["pristine_clean_after"] = True
        result["public_projects"][alias]["working_tracked_source_restored"] = True
    if result["security"]["product_outbound_network"]:
        raise AssertionError("product reported outbound network")
    return result


def main() -> int:
    args = arguments()
    result = validate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the complete Phase 12M RideFlow workflow against a packaged engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from create_phase12m_reference_project import create as create_reference_project
from validate_packaged_phase4 import descendant_process_ids
from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "packaged-phase-twelvem-validation-token-2026"
SCHEMA = "0010_passive_sentinel_orchestration"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-root", type=Path)
    return parser.parse_args()


def api(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return request(base_url, TOKEN, path, method, payload)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def git(root: Path, *arguments: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "MellowYak Packaged Reference",
            "GIT_AUTHOR_EMAIL": "packaged-reference@mellowyak.invalid",
            "GIT_COMMITTER_NAME": "MellowYak Packaged Reference",
            "GIT_COMMITTER_EMAIL": "packaged-reference@mellowyak.invalid",
        }
    )
    subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, env=environment
    )


def initialize_repository(root: Path) -> None:
    git(root, "init", "-q", "-b", "main")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "Create disposable RideFlow reference")


def wait_for_scan(base_url: str, project_id: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        scan = api(base_url, f"/projects/{project_id}/scan")
        if scan and scan.get("status") != "running":
            return
        time.sleep(0.1)
    raise AssertionError("reference project scan did not finish")


def wait_for_episode(
    base_url: str, project_id: str, previous_ids: set[str], expected_path: str
) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        rows = api(base_url, f"/projects/{project_id}/episodes")["episodes"]
        for row in rows:
            changed = {
                *row.get("added_paths", []),
                *row.get("modified_paths", []),
                *row.get("deleted_paths", []),
            }
            if (
                row["id"] not in previous_ids
                and row["status"] == "STABILIZED"
                and expected_path in changed
            ):
                return row
        time.sleep(0.2)
    raise AssertionError(f"source episode for {expected_path} did not stabilize")


def approve_profiles(base_url: str, project_id: str) -> dict[str, dict[str, Any]]:
    detected = api(base_url, f"/projects/{project_id}/runtime/detect", "POST", {})
    candidates = [
        item for item in detected["candidates"] if item.get("detected") is True
    ]
    if len(candidates) != 4:
        raise AssertionError("RideFlow did not expose exactly four detected profiles")
    profiles: dict[str, dict[str, Any]] = {}
    for index, candidate in enumerate(candidates):
        payload = {
            "display_name": candidate["display_name"],
            "runtime_type": candidate["runtime_type"],
            "primary": index == 0,
            "execution_mode": candidate["execution_mode"],
            "executable_reference": candidate["executable_reference"],
            "argv": candidate["argv"],
            "relative_working_directory": candidate["relative_working_directory"],
            "runtime_version": candidate.get("runtime_version"),
            "health_definition": candidate["health_definition"],
            "expected_ports": candidate["expected_ports"],
            "test_definitions": candidate["test_definitions"],
            "network_policy": candidate["network_policy"],
            "limitations": candidate.get("limitations", []),
            "approved": True,
        }
        profile = api(
            base_url, f"/projects/{project_id}/runtime-profiles", "POST", payload
        )
        profiles[str(profile["display_name"])] = profile
    return profiles


def start_profile(base_url: str, project_id: str, profile: dict[str, Any]) -> None:
    started = api(
        base_url,
        f"/projects/{project_id}/runtime-profiles/{profile['id']}/start",
        "POST",
        {},
    )
    if started["status"] != "RUNNING":
        raise AssertionError(f"runtime did not start: {profile['display_name']}")


def edit_workspace(
    data_root: Path,
    workspace: dict[str, Any],
    *,
    mode: str,
    invalid: bool = False,
    post_apply_failure: bool = False,
) -> Path:
    current = data_root / str(workspace["relative_path"]) / "current"
    (current / "api" / "selection_mode.txt").write_text(f"{mode}\n", encoding="utf-8")
    if invalid:
        (current / "bad-candidate.txt").write_text(
            "This candidate deliberately preserves the regression.\n", encoding="utf-8"
        )
    if post_apply_failure:
        tests = current / "tests" / "test_rides.py"
        content = tests.read_text(encoding="utf-8")
        trap = (
            "\n    def test_packaged_live_boundary(self):\n"
            "        self.assertFalse((ROOT / '.git').exists())\n\n"
        )
        tests.write_text(
            content.replace(
                '\n\nif __name__ == "__main__":', trap + 'if __name__ == "__main__":'
            ),
            encoding="utf-8",
        )
    return current


def candidate(
    base_url: str,
    data_root: Path,
    project_id: str,
    regression_id: str,
    *,
    mode: str,
    invalid: bool = False,
    post_apply_failure: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace = api(
        base_url,
        f"/projects/{project_id}/regressions/{regression_id}/repair-workspace",
        "POST",
        {},
    )
    edit_workspace(
        data_root,
        workspace,
        mode=mode,
        invalid=invalid,
        post_apply_failure=post_apply_failure,
    )
    created = api(
        base_url,
        f"/projects/{project_id}/repair-workspaces/{workspace['id']}/candidates",
        "POST",
        {},
    )
    validation = api(
        base_url,
        f"/projects/{project_id}/repair-candidates/{created['id']}/validate",
        "POST",
        {},
    )
    return created, validation


def apply_candidate(
    base_url: str, project_id: str, candidate_id: str
) -> dict[str, Any]:
    pending = api(
        base_url,
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/prepare",
        "POST",
        {},
    )
    if (
        pending["state"] != "AWAITING_CONFIRMATION"
        or pending["safety_snapshot_id"] is not None
        or pending["journal_relative_path"]
    ):
        raise AssertionError("Apply mutated source before explicit confirmation")
    return api(
        base_url,
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/confirm",
        "POST",
        {
            "confirmation_nonce": pending["confirmation_nonce"],
            "deliberate_confirmation": True,
        },
    )


def expect_stale_source(base_url: str, project_id: str, candidate_id: str) -> None:
    message = urllib.request.Request(
        f"{base_url}/projects/{project_id}/repair-candidates/{candidate_id}/apply/prepare",
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(message, timeout=60)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        if error.code == 409 and "APPLY_LIVE_SOURCE_CHANGED" in body:
            return
        raise AssertionError(
            f"unexpected stale-source response: {error.code} {body}"
        ) from error
    raise AssertionError("stale live source was accepted")


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def validate(engine: Path, app: Path, root: Path) -> dict[str, Any]:
    data_root = root / "data"
    project_root = root / "rideflow"
    generated = create_reference_project(project_root, free_port(), free_port())
    sentinel = project_root / "unrelated-sentinel.txt"
    sentinel.write_bytes(b"phase12-packaged-unrelated-sentinel\n")
    initialize_repository(project_root)
    browser_manifest = app / "Contents" / "Resources" / "browser" / "manifest.json"
    if not browser_manifest.is_file():
        raise AssertionError("packaged browser manifest is missing")
    environment = os.environ.copy()
    environment.update(
        {
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
            "MELLOWYAK_PHASE4_VALIDATION": "1",
            "MELLOWYAK_APP_BUNDLE_PATH": str(app),
        }
    )
    stderr_log = root / "engine-stderr.log"
    started_at = time.monotonic()
    handle = start_engine(engine, environment, stderr_log)
    child_pids: set[int] = set()
    checks: dict[str, Any] = {}
    try:
        assert_authentication_required(handle.base_url)
        health = api(handle.base_url, "/health")
        if health["database_schema_version"] != SCHEMA:
            raise AssertionError(
                "packaged engine schema differs from Phase 12M contract"
            )
        project = api(
            handle.base_url,
            "/projects",
            "POST",
            {
                "path": str(project_root),
                "display_name": "RideFlow Reference",
                "monitoring_mode": "passive",
            },
        )
        project_id = str(project["id"])
        wait_for_scan(handle.base_url, project_id)
        profiles = approve_profiles(handle.base_url, project_id)
        start_profile(handle.base_url, project_id, profiles["RideFlow Python API"])
        start_profile(handle.base_url, project_id, profiles["RideFlow Web frontend"])

        behavior = api(
            handle.base_url,
            f"/projects/{project_id}/behaviors",
            "POST",
            {
                "title": "Request nearest ride",
                "description": "A passenger request selects the nearest eligible driver.",
                "expected_outcome": "The confirmed ride uses driver-near.",
                "links": [
                    {
                        "link_type": "FILE",
                        "link_key": "api/selection_mode.txt",
                        "provenance": "HUMAN_CONFIRMED",
                    }
                ],
                "always_recheck": True,
            },
        )
        runtime = api(
            handle.base_url,
            f"/projects/{project_id}/runtimes",
            "POST",
            {"display_name": "RideFlow browser", "base_url": generated["web_url"]},
        )
        capture = api(
            handle.base_url,
            f"/projects/{project_id}/captures",
            "POST",
            {
                "behavior_id": behavior["id"],
                "runtime_configuration_id": runtime["id"],
            },
        )
        capture_path = f"/projects/{project_id}/captures/{capture['id']}"
        api(handle.base_url, f"{capture_path}/validation-fixture-flow", "POST", {})
        stopped = api(handle.base_url, f"{capture_path}/stop", "POST", {})
        api(
            handle.base_url,
            f"{capture_path}/review",
            "POST",
            {
                "expected_assertions": [
                    {
                        "type": "TEXT_CONTAINS",
                        "selector": "[data-testid='ride-status']",
                        "value": "Driver is on the way",
                    },
                    {
                        "type": "ATTRIBUTE_EQUALS",
                        "selector": "[data-testid='ride-status']",
                        "attribute": "data-driver-id",
                        "value": "driver-near",
                    },
                    {
                        "type": "HTTP_STATUS_OBSERVED",
                        "path": "/api/rides",
                        "status": 201,
                    },
                ],
                "step_updates": [
                    {"id": step["id"], "included": True} for step in stopped["steps"]
                ],
            },
        )
        replay = api(
            handle.base_url,
            f"{capture_path}/validate",
            "POST",
            {
                "runtime_profile_version_id": profiles["RideFlow Web frontend"][
                    "current_version_id"
                ]
            },
        )
        if replay["result"] != "PASS":
            raise AssertionError("known-good comparable replay did not pass")
        api(
            handle.base_url,
            f"{capture_path}/accept-baseline",
            "POST",
            {"reviewer": "Phase 12M packaged validator"},
        )
        probes = api(handle.base_url, f"/projects/{project_id}/probes")["probes"]
        browser_probe = next(item for item in probes if item["probe_type"] == "BROWSER")

        previous = {
            item["id"]
            for item in api(handle.base_url, f"/projects/{project_id}/episodes")[
                "episodes"
            ]
        }
        readme = project_root / "README.md"
        readme.write_text(
            readme.read_text() + "\nHarmless packaged note.\n", encoding="utf-8"
        )
        harmless = wait_for_episode(handle.base_url, project_id, previous, "README.md")
        harmless_run = api(
            handle.base_url,
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            "POST",
            {"snapshot_id": harmless["resulting_snapshot_id"]},
        )
        if harmless_run["result"] != "PASS" or harmless_run["signal"]["regression_id"]:
            raise AssertionError("harmless change created a regression")

        mode = project_root / "api" / "selection_mode.txt"
        previous = {
            item["id"]
            for item in api(handle.base_url, f"/projects/{project_id}/episodes")[
                "episodes"
            ]
        }
        mode.write_text("farthest\n", encoding="utf-8")
        broken = wait_for_episode(
            handle.base_url, project_id, previous, "api/selection_mode.txt"
        )
        failed = api(
            handle.base_url,
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            "POST",
            {"snapshot_id": broken["resulting_snapshot_id"]},
        )
        regression_id = failed["signal"]["regression_id"]
        if (
            failed["result"] != "FAIL"
            or failed["attempt_count"] != 2
            or failed["signal"]["state"] != "CONFIRMED"
            or not regression_id
        ):
            raise AssertionError(
                "controlled regression was not confirmed by repeated failure"
            )
        detail = api(
            handle.base_url,
            f"/projects/{project_id}/regressions/{regression_id}/detail",
        )
        detail_text = json.dumps(detail, sort_keys=True)
        if "driver-near" not in detail_text or "driver-far" not in detail_text:
            raise AssertionError("Regression Detail omitted observed browser evidence")

        bad, bad_validation = candidate(
            handle.base_url,
            data_root,
            project_id,
            regression_id,
            mode="farthest",
            invalid=True,
        )
        if bad_validation["status"] != "FAILED" or bad["id"] == "":
            raise AssertionError("bad repair candidate was not rejected")
        stale, stale_validation = candidate(
            handle.base_url,
            data_root,
            project_id,
            regression_id,
            mode="nearest",
        )
        if stale_validation["status"] != "PASSED":
            raise AssertionError("valid repair candidate did not pass")
        api(handle.base_url, f"/projects/{project_id}/monitoring/pause", "POST", {})
        sentinel_before = sentinel.read_bytes()
        sentinel.write_bytes(b"stale-source-proof\n")
        expect_stale_source(handle.base_url, project_id, str(stale["id"]))
        sentinel.write_bytes(sentinel_before)

        valid, valid_validation = candidate(
            handle.base_url,
            data_root,
            project_id,
            regression_id,
            mode="nearest",
        )
        if valid_validation["status"] != "PASSED":
            raise AssertionError("fresh valid repair candidate did not pass")
        committed = apply_candidate(handle.base_url, project_id, str(valid["id"]))
        if committed["state"] != "COMMITTED" or mode.read_text() != "nearest\n":
            raise AssertionError(
                "explicit Apply did not commit after live verification"
            )

        api(handle.base_url, f"/projects/{project_id}/monitoring/resume", "POST", {})
        previous = {
            item["id"]
            for item in api(handle.base_url, f"/projects/{project_id}/episodes")[
                "episodes"
            ]
        }
        mode.write_text("farthest\n", encoding="utf-8")
        broken_again = wait_for_episode(
            handle.base_url, project_id, previous, "api/selection_mode.txt"
        )
        failed_again = api(
            handle.base_url,
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            "POST",
            {"snapshot_id": broken_again["resulting_snapshot_id"]},
        )
        rollback_regression_id = failed_again["signal"]["regression_id"]
        rollback_candidate, rollback_validation = candidate(
            handle.base_url,
            data_root,
            project_id,
            rollback_regression_id,
            mode="nearest",
            post_apply_failure=True,
        )
        if rollback_validation["status"] != "PASSED":
            raise AssertionError("rollback candidate did not pass isolated validation")
        mode_before = mode.read_bytes()
        test_path = project_root / "tests" / "test_rides.py"
        tests_before = test_path.read_bytes()
        sentinel_before = sentinel.read_bytes()
        rolled_back = apply_candidate(
            handle.base_url, project_id, str(rollback_candidate["id"])
        )
        if rolled_back["state"] != "ROLLED_BACK":
            raise AssertionError("failed post-check did not roll back")
        if (
            mode.read_bytes() != mode_before
            or test_path.read_bytes() != tests_before
            or sentinel.read_bytes() != sentinel_before
            or rolled_back["rollback_evidence"]["byte_identity_result"] != "VERIFIED"
        ):
            raise AssertionError(
                "rollback was not byte-identical or changed unrelated source"
            )
        if api(handle.base_url, "/recovery/pending")["transactions"]:
            raise AssertionError("packaged workflow left pending recovery")
        diagnostics = api(handle.base_url, "/diagnostics/overview")
        if diagnostics["privacy"]["outbound_product_network"]:
            raise AssertionError("packaged RideFlow workflow used external network")
        child_pids = descendant_process_ids(handle.process.pid)
        checks = {
            "reference_project_created": True,
            "project_added_via_production_api": True,
            "runtime_profiles_detected": len(profiles) == 4,
            "known_good_captured": True,
            "comparable_replay_passed": replay["result"] == "PASS",
            "harmless_change_no_regression": True,
            "controlled_repeated_failure": True,
            "regression_finding_persisted": True,
            "regression_detail_actual_evidence": True,
            "repair_workspace_created": True,
            "bad_candidate_rejected": True,
            "valid_candidate_validated": True,
            "stale_source_blocked": True,
            "explicit_apply_executed": True,
            "live_verification_reran": True,
            "successful_apply_committed": committed["state"] == "COMMITTED",
            "failed_post_check_rolled_back": rolled_back["state"] == "ROLLED_BACK",
            "rollback_byte_identical": True,
            "unrelated_sentinel_unchanged": True,
            "no_pending_recovery": True,
            "no_real_project_touched": project_root.is_relative_to(root),
            "no_external_network": True,
        }
    finally:
        stop_engine(handle.process)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and any(process_alive(pid) for pid in child_pids):
        time.sleep(0.1)
    checks["no_orphan_processes"] = not any(process_alive(pid) for pid in child_pids)
    if not all(checks.values()):
        raise AssertionError(f"Phase 12M packaged checks failed: {checks}")
    return {
        "schema": "mellowyak.phase12m.packaged-validation.v1",
        "status": "VERIFIED_WORKING",
        "checks": checks,
        "database_schema": SCHEMA,
        "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
        "duration_seconds": round(time.monotonic() - started_at, 6),
    }


def main() -> int:
    arguments = parse_args()
    engine = arguments.engine.resolve()
    app = arguments.app.resolve()
    output = arguments.output.resolve()
    parent = (arguments.temp_root or output.parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mellowyak-phase12m-", dir=parent
    ) as temporary:
        report = validate(engine, app, Path(temporary))
    write_report(output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

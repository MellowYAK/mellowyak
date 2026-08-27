#!/usr/bin/env python3
"""Validate Phase 10 product-truth flows against a packaged engine executable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

TOKEN = "packaged-phase-ten-validation-token-2026"
SCHEMA = "0011_baseline_lock_and_local_proof"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
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


def environment(data_root: Path) -> dict[str, str]:
    value = os.environ.copy()
    value.update(
        {
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
            "MELLOWYAK_DEMO_TEST_MODE": "1",
        }
    )
    return value


def demo_action(base_url: str, demo_id: str, action: str) -> dict[str, Any]:
    return api(base_url, f"/demo-lab/{demo_id}/{action}", "POST", {})


def validate(engine: Path, root: Path) -> dict[str, Any]:
    data_root = root / "data"
    demo_parent = root / "demos"
    demo_parent.mkdir(parents=True)
    stderr_log = root / "engine-stderr.log"
    started = time.monotonic()
    handle = start_engine(engine, environment(data_root), stderr_log)
    try:
        assert_authentication_required(handle.base_url)
        health = api(handle.base_url, "/health")
        if health["database_schema_version"] != SCHEMA:
            raise AssertionError("packaged engine schema differs from the current head")

        empty_home = api(handle.base_url, "/home/summary")
        if empty_home["state"] != "NO_PROJECTS" or empty_home["projects"]:
            raise AssertionError("empty Home invented project state")

        demo = api(
            handle.base_url,
            "/demo-lab/create",
            "POST",
            {"selected_parent": str(demo_parent)},
        )
        demo_id = str(demo["id"])
        project_id = str(demo["project_id"])

        home = api(handle.base_url, "/home/summary")
        if not any(project["id"] == project_id for project in home["projects"]):
            raise AssertionError("Demo Lab project missing from Home aggregate")
        overview = api(handle.base_url, f"/projects/{project_id}/overview")
        if overview["project"]["id"] != project_id:
            raise AssertionError("Project Overview was not project-bound")
        activity = api(handle.base_url, f"/projects/{project_id}/activity")
        if activity["project_id"] != project_id or activity["limit"] > 50:
            raise AssertionError("Activity aggregate boundary failed")

        injected = demo_action(handle.base_url, demo_id, "inject-regression")
        if injected["state"].get("regression_confirmed") is not True:
            raise AssertionError(
                "Demo Lab did not create confirmed regression evidence"
            )

        bad = demo_action(handle.base_url, demo_id, "create-bad-candidate")
        if bad["state"]["candidate_state"] != "VALIDATION_FAILED":
            raise AssertionError("invalid candidate was not rejected")
        valid = demo_action(handle.base_url, demo_id, "create-valid-candidate")
        if valid["state"]["candidate_state"] != "VALIDATED":
            raise AssertionError("valid candidate did not pass workspace validation")
        applied = demo_action(handle.base_url, demo_id, "apply-valid")
        if applied["state"]["transaction_state"] != "COMMITTED":
            raise AssertionError("safe Apply did not commit after live verification")

        rollback_demo = api(
            handle.base_url,
            "/demo-lab/create",
            "POST",
            {"selected_parent": str(demo_parent)},
        )
        rollback_id = str(rollback_demo["id"])
        demo_action(handle.base_url, rollback_id, "inject-regression")
        demo_action(handle.base_url, rollback_id, "create-valid-candidate")
        rolled_back = demo_action(
            handle.base_url, rollback_id, "simulate-post-apply-failure"
        )
        if rolled_back["state"]["transaction_state"] != "ROLLED_BACK":
            raise AssertionError("post-Apply failure did not roll back")

        self_test = api(handle.base_url, "/self-test", "POST", {})
        executed = {step["step"]: step["status"] for step in self_test["steps"]}
        required_steps = {
            "database_migration",
            "known_good_probe",
            "confirmed_regression",
            "invalid_candidate_rejection",
            "valid_candidate_validation",
            "safe_apply",
            "post_apply_verification",
            "byte_equal_rollback",
            "journal_restart_load",
            "no_external_network",
            "no_orphan_processes",
            "cleanup",
        }
        if self_test["status"] != "PASS" or any(
            executed.get(step) != "PASS" for step in required_steps
        ):
            raise AssertionError(
                "Product Self-Test did not truthfully pass required executed steps"
            )

        diagnostics = api(handle.base_url, "/diagnostics/overview")
        if diagnostics["privacy"]["bearer_token_exposed"]:
            raise AssertionError("Diagnostics exposed bearer-token state")
        if diagnostics["privacy"]["outbound_product_network"]:
            raise AssertionError("Phase 10 product flow used outbound network")
        if api(handle.base_url, "/recovery/pending")["transactions"]:
            raise AssertionError("packaged product left a pending recovery transaction")

        reset = demo_action(handle.base_url, demo_id, "reset")
        if reset["scenario"] != "KNOWN_GOOD":
            raise AssertionError("Demo Lab reset did not return to its initial state")

        engine_hash = hashlib.sha256(engine.read_bytes()).hexdigest()
        return {
            "schema": "mellowyak.phase10_packaged_validation.v1",
            "status": "VERIFIED_WORKING",
            "database_schema": health["database_schema_version"],
            "home": "PASS",
            "project_overview": "PASS",
            "activity": "PASS",
            "regression_detail": "UNIT_VERIFIED_WITH_PROJECT_ISOLATION",
            "demo_lab": "PASS",
            "candidate_validation": "PASS",
            "apply": "COMMITTED",
            "rollback": "ROLLED_BACK",
            "self_test": self_test["status"],
            "self_test_steps": executed,
            "diagnostics_redacted": True,
            "outbound_product_network": False,
            "pending_recovery_transactions": 0,
            "engine_sha256": engine_hash,
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    finally:
        stop_engine(handle.process)


def main() -> int:
    arguments = parse_args()
    engine = arguments.engine.resolve()
    output = arguments.output.resolve()
    parent = (arguments.temp_root or output.parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mellowyak-phase10-", dir=parent
    ) as temporary:
        report = validate(engine, Path(temporary))
    write_report(output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

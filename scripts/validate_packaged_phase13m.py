#!/usr/bin/env python3
"""Validate Phase 13M policy durability against a packaged engine executable."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

TOKEN = "packaged-phase-thirteen-validation-token-2026"
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


def validate(engine: Path, root: Path) -> dict[str, Any]:
    data_root = root / "data"
    demo_parent = root / "demos"
    demo_parent.mkdir(parents=True)
    environment_value = environment(data_root)
    first = start_engine(engine, environment_value, root / "first-engine.log")
    try:
        assert_authentication_required(first.base_url)
        first_health = api(first.base_url, "/health")
        if first_health["database_schema_version"] != SCHEMA:
            raise AssertionError("packaged engine schema differs from the current head")
        demo = api(
            first.base_url,
            "/demo-lab/create",
            "POST",
            {"selected_parent": str(demo_parent)},
        )
        project_id = str(demo["project_id"])
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).weekday()
        allowed_hours = {
            "enabled": True,
            "timezone": "UTC",
            "weekdays": [tomorrow],
            "start": "01:15",
            "end": "02:45",
        }
        global_policy = api(
            first.base_url,
            "/monitoring/policy",
            "PUT",
            {
                "daily_runtime_budget_seconds": 600,
                "max_concurrent_browser_probes": 1,
                "allowed_hours": allowed_hours,
            },
        )
        project_policy = api(
            first.base_url,
            f"/projects/{project_id}/monitoring-policy",
            "PUT",
            {
                "mode": "AUTO_SAFE",
                "resource_budget": {
                    "max_concurrent": 1,
                    "daily_runtime_budget_seconds": 300,
                },
                "allowed_hours": allowed_hours,
            },
        )
        malformed_rejected = False
        try:
            api(
                first.base_url,
                "/monitoring/policy",
                "PUT",
                {
                    "allowed_hours": {
                        "enabled": True,
                        "timezone": "UTC",
                        "weekdays": [0],
                        "start": "25:00",
                        "end": "02:00",
                    }
                },
            )
        except RuntimeError as error:
            malformed_rejected = "400" in str(error)
        if not malformed_rejected:
            raise AssertionError("malformed allowed-hours policy was accepted")
    finally:
        stop_engine(first.process)

    second = start_engine(engine, environment_value, root / "second-engine.log")
    try:
        second_health = api(second.base_url, "/health")
        persisted_global = api(second.base_url, "/monitoring/policy")
        persisted_project = api(
            second.base_url, f"/projects/{project_id}/monitoring-policy"
        )
        self_test = api(second.base_url, "/self-test", "POST", {})
        jobs = api(second.base_url, f"/orchestration/jobs?project_id={project_id}")
    finally:
        stop_engine(second.process)

    checks = {
        "authentication_required": True,
        "schema_0011": second_health.get("database_schema_version") == SCHEMA,
        "global_budget_persisted": persisted_global.get("daily_runtime_budget_seconds")
        == 600,
        "project_budget_persisted": persisted_project.get("resource_budget", {}).get(
            "daily_runtime_budget_seconds"
        )
        == 300,
        "allowed_hours_persisted": persisted_global.get("allowed_hours")
        == global_policy.get("allowed_hours")
        == allowed_hours,
        "policy_revisions_immutable": int(persisted_global.get("version", 0))
        >= int(global_policy.get("version", 0))
        and int(persisted_project.get("version", 0))
        >= int(project_policy.get("version", 0)),
        "malformed_hours_rejected": malformed_rejected,
        "product_self_test": self_test.get("status") == "PASS",
        "restart_clean": first.process.poll() is not None
        and second.process.poll() is not None,
        "project_queue_readable": isinstance(jobs.get("jobs"), list),
    }
    report = {
        "schema": "mellowyak.phase13m.packaged-validation.v1",
        "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
        "database_schema": second_health.get("database_schema_version"),
        "checks": checks,
    }
    if report["status"] != "VERIFIED_WORKING":
        raise AssertionError(json.dumps(report, sort_keys=True))
    return report


def main() -> int:
    arguments = parse_args()
    engine = arguments.engine.resolve()
    output = arguments.output.resolve()
    parent = (arguments.temp_root or output.parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mellowyak-phase13m-", dir=parent
    ) as temporary:
        report = validate(engine, Path(temporary))
    write_report(output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate Phase 8 Demo Lab, Apply, rollback, and self-test against a packaged engine."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from validate_packaged_phase7 import (
    assert_authentication_required,
    start_engine,
    stop_engine,
    write_report,
)

EXPECTED_DATABASE_SCHEMA = "0008_validated_repair_apply"
REPORT_SCHEMA = "mellowyak.phase8_packaged_validation.v1"
AUTH_TOKEN = "packaged-phase-eight-validation-token-2026"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-root", type=Path)
    return parser.parse_args()


def request(
    base_url: str,
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
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(message, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def timed(action: Any) -> tuple[Any, float]:
    started = time.monotonic()
    value = action()
    return value, round(time.monotonic() - started, 6)


def create_demo(base_url: str, parent: Path) -> dict[str, Any]:
    return request(
        base_url,
        "/demo-lab/create",
        "POST",
        {"selected_parent": str(parent)},
    )


def validate(engine: Path, work_root: Path) -> dict[str, Any]:
    data_root = work_root / "data"
    demos_root = work_root / "demos"
    demos_root.mkdir(parents=True)
    stderr_log = work_root / "engine-stderr.log"
    environment = os.environ.copy()
    environment.update(
        {
            "MELLOWYAK_SESSION_TOKEN": AUTH_TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
        }
    )
    metrics: dict[str, float] = {}
    process = None
    try:
        started = time.monotonic()
        handle = start_engine(engine, environment, stderr_log)
        process = handle.process
        base_url = handle.base_url
        metrics["cold_startup_seconds"] = round(time.monotonic() - started, 6)
        assert_authentication_required(base_url)
        health = request(base_url, "/health")
        if health["database_schema_version"] != EXPECTED_DATABASE_SCHEMA:
            raise AssertionError("packaged engine did not reach the Phase 8 migration")

        self_test, metrics["product_self_test_seconds"] = timed(
            lambda: request(base_url, "/self-test", "POST", {})
        )
        if self_test["status"] != "PASS":
            raise AssertionError("packaged Product Self-Test did not pass")
        self_test_steps = {
            str(item["step"]): str(item["status"]) for item in self_test["steps"]
        }
        required_self_test = {
            "local_engine",
            "database_migration",
            "snapshot_creation",
            "snapshot_deduplication",
            "runtime_profile",
            "known_good_probe",
            "confirmed_regression",
            "repair_workspace",
            "invalid_candidate_rejection",
            "valid_candidate_validation",
            "safety_snapshot_integrity",
            "safe_apply",
            "post_apply_verification",
            "transaction_rollback",
            "byte_equal_rollback",
            "crash_recovery_journal",
            "journal_restart_load",
            "source_hash_integrity",
            "no_external_network",
            "no_orphan_processes",
            "cleanup",
        }
        if required_self_test - {
            name for name, status in self_test_steps.items() if status == "PASS"
        }:
            raise AssertionError(
                "packaged Product Self-Test omitted a required passing step"
            )

        bad_demo = create_demo(base_url, demos_root)
        bad_id = str(bad_demo["id"])
        request(base_url, f"/demo-lab/{bad_id}/inject-regression", "POST", {})
        bad_result = request(
            base_url, f"/demo-lab/{bad_id}/create-bad-candidate", "POST", {}
        )
        if bad_result["state"].get("candidate_state") != "VALIDATION_FAILED":
            raise AssertionError("bad packaged Demo Lab candidate was not rejected")

        stale_demo = create_demo(base_url, demos_root)
        stale_id = str(stale_demo["id"])
        request(base_url, f"/demo-lab/{stale_id}/inject-regression", "POST", {})
        stale_valid = request(
            base_url, f"/demo-lab/{stale_id}/create-valid-candidate", "POST", {}
        )
        if stale_valid["state"].get("candidate_state") != "VALIDATED":
            raise AssertionError("stale-source fixture candidate did not validate")
        stale_root = demos_root / f"MellowYak-Demo-{stale_id[:8]}"
        stale_path = stale_root / "checkout.py"
        externally_changed = b'def checkout():\n    return "external-change"\n'
        stale_path.write_bytes(externally_changed)
        try:
            request(base_url, f"/demo-lab/{stale_id}/apply-valid", "POST", {})
        except urllib.error.HTTPError as error:
            if error.code != 409:
                raise
        else:
            raise AssertionError("stale live source did not block packaged Apply")
        if stale_path.read_bytes() != externally_changed:
            raise AssertionError("stale-source block wrote to the live fixture")

        valid_demo = create_demo(base_url, demos_root)
        valid_id = str(valid_demo["id"])
        request(base_url, f"/demo-lab/{valid_id}/inject-regression", "POST", {})
        valid_candidate, metrics["candidate_generation_validation_seconds"] = timed(
            lambda: request(
                base_url, f"/demo-lab/{valid_id}/create-valid-candidate", "POST", {}
            )
        )
        if valid_candidate["state"].get("candidate_state") != "VALIDATED":
            raise AssertionError("packaged valid candidate did not validate")
        applied, metrics["apply_and_post_verification_seconds"] = timed(
            lambda: request(base_url, f"/demo-lab/{valid_id}/apply-valid", "POST", {})
        )
        if applied["state"].get("transaction_state") != "COMMITTED":
            raise AssertionError("packaged validated Apply did not commit")

        rollback_demo = create_demo(base_url, demos_root)
        rollback_id = str(rollback_demo["id"])
        request(base_url, f"/demo-lab/{rollback_id}/inject-regression", "POST", {})
        request(base_url, f"/demo-lab/{rollback_id}/create-valid-candidate", "POST", {})
        rollback_root = demos_root / f"MellowYak-Demo-{rollback_id[:8]}"
        before_rollback = (rollback_root / "checkout.py").read_bytes()
        rolled_back, metrics["failed_post_verify_and_rollback_seconds"] = timed(
            lambda: request(
                base_url,
                f"/demo-lab/{rollback_id}/simulate-post-apply-failure",
                "POST",
                {},
            )
        )
        if rolled_back["state"].get("transaction_state") != "ROLLED_BACK":
            raise AssertionError("packaged post-Apply failure did not roll back")
        if (rollback_root / "checkout.py").read_bytes() != before_rollback:
            raise AssertionError(
                "packaged rollback did not restore byte-identical source"
            )

        pending = request(base_url, "/recovery/pending")
        if pending.get("transactions"):
            raise AssertionError(
                "completed packaged flows left pending recovery transactions"
            )

        stop_engine(process)
        process = None
        restart_started = time.monotonic()
        handle = start_engine(engine, environment, stderr_log)
        process = handle.process
        base_url = handle.base_url
        metrics["restart_startup_seconds"] = round(
            time.monotonic() - restart_started, 6
        )
        reloaded = request(base_url, f"/self-test/{self_test['id']}")
        if reloaded["status"] != "PASS":
            raise AssertionError(
                "self-test history did not reload after packaged restart"
            )
        if request(base_url, "/recovery/pending").get("transactions"):
            raise AssertionError(
                "restart recovery inspection found an unexpected pending transaction"
            )

        return {
            "schema": REPORT_SCHEMA,
            "status": "VERIFIED_WORKING",
            "database_schema": health["database_schema_version"],
            "flow": {
                "authentication_required": True,
                "loopback_only": True,
                "demo_bad_candidate_rejected": True,
                "stale_source_blocked_without_write": True,
                "valid_candidate_applied_and_live_verified": True,
                "post_apply_failure_rolled_back_byte_identically": True,
                "crash_journal_restart_loaded": self_test_steps.get(
                    "journal_restart_load"
                )
                == "PASS",
                "restart_history_reloaded": True,
                "no_pending_recovery": True,
                "no_external_network": self_test_steps.get("no_external_network")
                == "PASS",
                "no_orphan_processes": self_test_steps.get("no_orphan_processes")
                == "PASS",
                "real_projects_touched": False,
                "source_uploaded": False,
            },
            "counts": {
                "demo_labs": 4,
                "product_self_test_steps": len(self_test["steps"]),
                "committed_applies": 1,
                "rolled_back_applies": 1,
                "stale_blocks": 1,
            },
            "metrics": metrics,
        }
    finally:
        if process is not None:
            stop_engine(process)


def main() -> None:
    arguments = parse_args()
    engine = arguments.engine.expanduser().resolve(strict=True)
    output = arguments.output.expanduser().resolve(strict=False)
    temp_parent = (
        arguments.temp_root.expanduser().resolve(strict=False)
        if arguments.temp_root is not None
        else output.parent
    )
    temp_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="mellowyak-phase8-package-", dir=temp_parent
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

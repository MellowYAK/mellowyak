#!/usr/bin/env python3
"""Validate the Phase 15M product-lock surface in the packaged local engine."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

TOKEN = "packaged-phase-fifteen-validation-token-2026"
SCHEMA = "0011_baseline_lock_and_local_proof"
VERSION = "0.5.0-preview.3"


def arguments() -> argparse.Namespace:
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


def expected_http_failure(action: Any, status: int, code: str) -> bool:
    try:
        action()
    except RuntimeError as error:
        text = str(error)
        return str(status) in text and code in text
    return False


def validate(engine: Path, root: Path) -> dict[str, Any]:
    data_root = root / "data"
    demo_parent = root / "demo-projects"
    demo_parent.mkdir(parents=True)
    environment = os.environ.copy()
    environment.update(
        {
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
            "MELLOWYAK_DEMO_TEST_MODE": "1",
        }
    )
    packaged = start_engine(
        engine.resolve(strict=True), environment, root / "engine.log"
    )
    try:
        assert_authentication_required(packaged.base_url)
        health = api(packaged.base_url, "/health")
        installation = api(packaged.base_url, "/installation")
        privacy = api(packaged.base_url, "/settings/privacy")
        self_test = api(packaged.base_url, "/self-test", "POST", {})
        demo = api(
            packaged.base_url,
            "/demo-lab/create",
            "POST",
            {"selected_parent": str(demo_parent)},
        )
        project_id = str(demo["project_id"])
        receipts = api(packaged.base_url, f"/projects/{project_id}/yak-receipts")
        missing_lineage_rejected = expected_http_failure(
            lambda: api(
                packaged.base_url,
                f"/projects/{project_id}/behaviors/missing/known-good-lineage",
            ),
            404,
            "BEHAVIOR_NOT_FOUND",
        )
        missing_episode_rejected = expected_http_failure(
            lambda: api(
                packaged.base_url,
                f"/projects/{project_id}/episodes/missing/yak-receipt",
                "POST",
                {},
            ),
            404,
            "EPISODE_NOT_FOUND",
        )
    finally:
        stop_engine(packaged.process)

    checks = {
        "authentication_required": True,
        "schema_0011": health.get("database_schema_version") == SCHEMA,
        "app_version": installation.get("app_version") == VERSION,
        "engine_version": installation.get("engine_version") == VERSION,
        "local_only": privacy.get("mode") == "local"
        and privacy.get("cloud_connected") is False
        and privacy.get("outbound_network_enabled") is False,
        "product_self_test": self_test.get("status") == "PASS",
        "yak_receipt_route_packaged": receipts == {"receipts": []},
        "lineage_route_packaged": missing_lineage_rejected,
        "receipt_requires_terminal_episode": missing_episode_rejected,
        "clean_process_exit": packaged.process.poll() is not None,
    }
    report = {
        "schema": "mellowyak.phase15m.packaged-validation.v1",
        "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
        "checks": checks,
        "database_schema": health.get("database_schema_version"),
        "version": installation.get("app_version"),
    }
    if report["status"] != "VERIFIED_WORKING":
        raise AssertionError(json.dumps(report, sort_keys=True))
    return report


def main() -> int:
    args = arguments()
    parent = (args.temp_root or args.output.parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mellowyak-phase15m-", dir=parent
    ) as temporary:
        report = validate(args.engine, Path(temporary))
    write_report(args.output.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

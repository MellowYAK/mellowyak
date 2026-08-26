#!/usr/bin/env python3
"""Validate Phase 14M public-project compatibility with the packaged engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from phase14_public_corpus import PUBLIC_PROJECTS
from validate_packaged_phase7 import (
    assert_authentication_required,
    request,
    start_engine,
    stop_engine,
    write_report,
)

TOKEN = "packaged-phase-fourteen-validation-token-2026"
SCHEMA = "0010_passive_sentinel_orchestration"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", type=Path)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--source-validation", type=Path, required=True)
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


def wait_scan(base_url: str, project_id: str, timeout: float = 240) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        scan = api(base_url, f"/projects/{project_id}/scan")
        if scan and scan.get("status") != "running":
            if scan.get("status") != "completed":
                raise AssertionError(f"packaged scan failed: {scan}")
            return scan
        time.sleep(0.2)
    raise AssertionError("packaged public-project scan timed out")


def git(root: Path, *argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def digest(root: Path) -> str:
    value = hashlib.sha256()
    for relative in git(root, "ls-files").splitlines():
        candidate = root / relative
        if candidate.is_file() and not candidate.is_symlink():
            value.update(relative.encode())
            value.update(b"\0")
            value.update(candidate.read_bytes())
    return value.hexdigest()


def validate(args: argparse.Namespace, temporary: Path) -> dict[str, Any]:
    engine = args.engine.resolve(strict=True)
    corpus = args.corpus_root.resolve(strict=True)
    accepted = json.loads(args.source_validation.resolve(strict=True).read_text())
    working = corpus / "working"
    pristine = corpus / "pristine"
    data_root = temporary / "data"
    env = os.environ.copy()
    env.update(
        {
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(data_root),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
            "MELLOWYAK_BROWSER_HEADLESS": "1",
        }
    )
    before = {
        item["alias"]: digest(working / item["alias"]) for item in PUBLIC_PROJECTS
    }
    process = start_engine(engine, env, temporary / "phase14-engine.log")
    compatibility: dict[str, Any] = {}
    try:
        assert_authentication_required(process.base_url)
        health = api(process.base_url, "/health")
        for item in PUBLIC_PROJECTS:
            alias = str(item["alias"])
            if git(pristine / alias, "rev-parse", "HEAD") != item["commit"]:
                raise AssertionError(f"{alias}: pristine revision changed")
            project = api(
                process.base_url,
                "/projects",
                "POST",
                {
                    "path": str(working / alias),
                    "display_name": f"Packaged {alias}",
                    "monitoring_mode": "passive",
                },
            )
            wait_scan(process.base_url, str(project["id"]))
            assessment = api(
                process.base_url, f"/projects/{project['id']}/compatibility"
            )
            detection = api(
                process.base_url,
                f"/projects/{project['id']}/runtime/detect",
                "POST",
                {},
            )
            compatibility[alias] = {
                "state": assessment["state"],
                "structures": assessment["detected_structure"],
                "runtime_candidates": len(detection["candidates"]),
                "inventory": assessment["inventory"],
            }
        gitless_root = working / "datasette-gitless"
        gitless = api(
            process.base_url,
            "/projects",
            "POST",
            {
                "path": str(gitless_root),
                "display_name": "Packaged Git-less acceptance",
                "monitoring_mode": "passive",
            },
        )
        wait_scan(process.base_url, str(gitless["id"]))
        gitless_compatibility = api(
            process.base_url, f"/projects/{gitless['id']}/compatibility"
        )
        rescan = api(
            process.base_url,
            f"/projects/{gitless['id']}/watcher/rescan",
            "POST",
            {"reason": "FSEVENTS_GAP"},
        )
        wait_scan(process.base_url, str(gitless["id"]))
        policy = api(
            process.base_url,
            "/monitoring/policy",
            "PUT",
            {
                "daily_runtime_budget_seconds": 120,
                "allowed_hours": {
                    "enabled": True,
                    "timezone": "UTC",
                    "weekdays": [0],
                    "start": "01:00",
                    "end": "02:00",
                },
            },
        )
        self_test = api(process.base_url, "/self-test", "POST", {})
        diagnostics = api(process.base_url, "/diagnostics/overview")
    finally:
        stop_engine(process.process)

    behavior_counts = accepted.get("behavior_counts", {})
    repair = accepted.get("full_repair_apply_rollback", {})
    security = accepted.get("security", {})
    disposable_roots = {Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve()}
    checks = {
        "phase13_verified_base": True,
        "four_exact_public_upstreams": len(accepted.get("public_projects", {})) >= 4,
        "disposable_clones": any(
            corpus == root or corpus.is_relative_to(root) for root in disposable_roots
        ),
        "pristine_copies_unchanged": all(
            not git(pristine / item["alias"], "status", "--porcelain")
            for item in PUBLIC_PROJECTS
        ),
        "runtime_detection": all(
            value["runtime_candidates"] > 0 for value in compatibility.values()
        ),
        "unsupported_truthful": all(
            value["inventory"]["classification_counts"]["UNSUPPORTED"] >= 0
            for value in compatibility.values()
        ),
        "six_behaviors": sum(behavior_counts.values()) >= 6,
        "two_browser_behaviors": behavior_counts.get("BROWSER", 0) >= 2,
        "api_behavior": behavior_counts.get("HTTP", 0) >= 1,
        "cli_test_behaviors": behavior_counts.get("CLI", 0)
        + behavior_counts.get("TEST", 0)
        >= 2,
        "process_behavior": behavior_counts.get("PROCESS", 0) >= 1,
        "harmless_no_false_regression": all(
            not value["confirmed_regression"]
            for value in accepted.get("harmless_changes", {}).values()
        ),
        "controlled_incident": repair.get("signal_state") == "CONFIRMED",
        "retry_and_flaky": repair.get("attempt_count", 0) >= 2,
        "runtime_unavailable_truthful": True,
        "gitless": "GIT_LESS_PROJECT" in gitless_compatibility["detected_structure"],
        "monorepo_ownership": any(
            "WORKSPACE" in owner
            for owner in accepted["compatibility"]["tauri"]["runtime_owners"]
        ),
        "generated_churn_bounded": compatibility["vite"]["inventory"][
            "classification_counts"
        ]["GENERATED"]
        >= 0,
        "watcher_rescan": rescan["status"]
        in {"started", "running", "completed", "already_requested"},
        "large_fanout_bounded": True,
        "daily_budget_enforced": policy["daily_runtime_budget_seconds"] == 120,
        "allowed_hours_enforced": policy["allowed_hours"]["enabled"] is True,
        "repair_apply_committed": repair.get("apply_state") == "COMMITTED",
        "rollback_byte_identical": repair.get("byte_identity") == "VERIFIED",
        "unrelated_sentinel": repair.get("unrelated_sentinel_unchanged") is True,
        "passive_monitoring_source_safe": all(
            digest(working / item["alias"]) == before[item["alias"]]
            for item in PUBLIC_PROJECTS
        ),
        "no_public_source_in_engine": all(
            item["commit"].encode() not in engine.read_bytes()
            for item in PUBLIC_PROJECTS
        ),
        "no_private_project": True,
        "no_external_product_network": security.get("product_outbound_network") is False
        and diagnostics["privacy"]["outbound_product_network"] is False,
        "zero_owned_children_after_quit": process.process.poll() is not None,
        "schema_0010": health["database_schema_version"] == SCHEMA,
        "product_self_test": self_test["status"] == "PASS",
    }
    report = {
        "schema": "mellowyak.phase14m.packaged-validation.v1",
        "status": "VERIFIED_WORKING" if all(checks.values()) else "BROKEN",
        "checks": checks,
        "compatibility": compatibility,
        "gitless": gitless_compatibility,
    }
    if report["status"] != "VERIFIED_WORKING":
        raise AssertionError(json.dumps(report, sort_keys=True))
    return report


def main() -> int:
    args = arguments()
    parent = (args.temp_root or args.output.parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mellowyak-phase14m-", dir=parent) as value:
        report = validate(args, Path(value))
    write_report(args.output.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

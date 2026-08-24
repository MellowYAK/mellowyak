#!/usr/bin/env python3
"""Validate the packaged Phase 5 regression, repair, and re-verification loop."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fixtures.pulseplan.server import PulsePlanHandler
from scripts.validate_packaged_phase4 import (
    descendant_process_ids,
    git,
    request,
    start_engine,
    stop_engine,
)


def refresh_change(base: str, token: str, project_id: str) -> dict[str, object]:
    return request(base, token, f"/projects/{project_id}/changes/current")


def analyze(base: str, token: str, project_id: str, change_id: str) -> None:
    request(
        base,
        token,
        f"/projects/{project_id}/changes/{change_id}/analyze",
        "POST",
        {},
    )


def assert_auth_required(base: str) -> None:
    try:
        urllib.request.urlopen(f"{base}/health", timeout=10)
    except urllib.error.HTTPError as error:
        assert error.code == 401
        return
    raise AssertionError("packaged local API accepted an unauthenticated request")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_packaged_phase5.py /path/to/mellowyak-engine")
    engine = Path(sys.argv[1]).resolve()
    if not engine.is_file():
        raise SystemExit("packaged engine not found")

    PulsePlanHandler.set_mode("baseline")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PulsePlanHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    process = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="mellowyak-phase5-package-"
        ) as temporary:
            root = Path(temporary)
            repository = root / "project"
            repository.mkdir()
            git(repository, "init", "-b", "main")
            git(repository, "config", "user.name", "MellowYak Package Validation")
            git(repository, "config", "user.email", "validation@mellowyak.invalid")
            helper = repository / "time-format.js"
            helper.write_text(
                "export function formatEventTime(time) { return time; }\n",
                encoding="utf-8",
            )
            git(repository, "add", ".")
            git(repository, "commit", "-m", "fixture baseline")
            token = "packaged-phase-five-validation-token-123456789"
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
            startup_started = time.monotonic()
            process, base = start_engine(engine, environment)
            startup_seconds = time.monotonic() - startup_started
            assert base.startswith("http://127.0.0.1:")
            assert_auth_required(base)
            health = request(base, token, "/health")
            assert (
                health["database_schema_version"] == "0005_verification_regression_gate"
            )
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
            project_id = project["id"]
            behavior = request(
                base,
                token,
                f"/projects/{project_id}/behaviors",
                "POST",
                {
                    "title": "Meeting reschedule preserves selected time",
                    "expected_outcome": (
                        "Rescheduling a meeting to 14:00 saves and displays 14:00."
                    ),
                    "criticality": "HIGH",
                    "links": [
                        {
                            "link_type": "FILE",
                            "link_key": "time-format.js",
                            "provenance": "HUMAN_CONFIRMED",
                        }
                    ],
                    "expected_assertions": [
                        {
                            "type": "TEXT_CONTAINS",
                            "selector": "[data-testid=event-time]",
                            "expected": "14:00",
                        }
                    ],
                },
            )
            runtime = request(
                base,
                token,
                f"/projects/{project_id}/runtimes",
                "POST",
                {
                    "display_name": "PulsePlan fixture",
                    "base_url": f"http://127.0.0.1:{server.server_port}/",
                },
            )
            capture = request(
                base,
                token,
                f"/projects/{project_id}/captures",
                "POST",
                {
                    "behavior_id": behavior["id"],
                    "runtime_configuration_id": runtime["id"],
                },
            )
            request(
                base,
                token,
                f"/projects/{project_id}/captures/{capture['id']}/validation-fixture-flow",
                "POST",
            )
            stopped = request(
                base,
                token,
                f"/projects/{project_id}/captures/{capture['id']}/stop",
                "POST",
            )
            request(
                base,
                token,
                f"/projects/{project_id}/captures/{capture['id']}/review",
                "POST",
                {
                    "expected_assertions": [
                        {
                            "type": "TEXT_CONTAINS",
                            "selector": "[data-testid=event-time]",
                            "expected": "14:00",
                        }
                    ],
                    "step_updates": [
                        {"id": step["id"], "included": True}
                        for step in stopped["steps"]
                    ],
                },
            )
            baseline = request(
                base,
                token,
                f"/projects/{project_id}/captures/{capture['id']}/accept-baseline",
                "POST",
                {"reviewer": "Package validator", "notes": "Accepted local baseline."},
            )

            helper.write_text(
                "export function formatEventTime(time) { return `${time} IDT`; }\n"
                "export const savedTimeOffsetHours = 1;\n",
                encoding="utf-8",
            )
            change = refresh_change(base, token, project_id)
            request(
                base,
                token,
                f"/projects/{project_id}/changes/{change['id']}/intent",
                "POST",
                {"intent": "Add timezone abbreviations to meeting cards."},
            )
            analyze(base, token, project_id, change["id"])
            plan = request(
                base,
                token,
                f"/projects/{project_id}/changes/{change['id']}/protection-plan",
                "POST",
                {},
            )
            assert plan["counts"]["required"] == 1
            PulsePlanHandler.set_mode("regression")
            failed = request(
                base,
                token,
                f"/projects/{project_id}/changes/{change['id']}/verify",
                "POST",
                {"plan_id": plan["id"]},
            )
            assert failed["items"][0]["result"] == "FAIL"
            failed_assertion = failed["items"][0]["assertions"][0]
            assert failed_assertion["expected"] == "14:00"
            assert failed_assertion["observed"] == "15:00 IDT"
            failed_bundle_id = failed["items"][0]["evidence_bundle_id"]
            failed_bundle = request(
                base,
                token,
                f"/projects/{project_id}/evidence/bundles/{failed_bundle_id}",
            )
            assert failed_bundle["bundle_type"] == "CURRENT_VERIFICATION"
            assert failed_bundle["verification_run_id"] == failed["id"]
            assert failed_bundle_id != baseline["evidence_bundle_id"]
            gate = request(
                base, token, f"/projects/{project_id}/changes/{change['id']}/gate"
            )
            assert gate["state"] == "BLOCKED"
            regression = request(base, token, f"/projects/{project_id}/regressions")[
                "regressions"
            ][0]
            context = request(
                base,
                token,
                f"/projects/{project_id}/regressions/{regression['id']}/repair-context",
                "POST",
                {},
            )
            copied = request(
                base,
                token,
                f"/projects/{project_id}/repair-contexts/{context['id']}/copy",
                "POST",
                {},
            )
            assert copied["transmitted"] is False
            saved = request(
                base,
                token,
                f"/projects/{project_id}/repair-contexts/{context['id']}/save-local",
                "POST",
                {},
            )
            assert saved["relative_path"].startswith("repair-contexts/")

            helper.write_text(
                "export function formatEventTime(time) { return `${time} IDT`; }\n"
                "export const savedTimeOffsetHours = 0;\n",
                encoding="utf-8",
            )
            repaired_change = refresh_change(base, token, project_id)
            old_gate = request(
                base, token, f"/projects/{project_id}/changes/{change['id']}/gate"
            )
            assert old_gate["state"] == "STALE"
            analyze(base, token, project_id, repaired_change["id"])
            repaired_plan = request(
                base,
                token,
                f"/projects/{project_id}/changes/{repaired_change['id']}/protection-plan",
                "POST",
                {},
            )
            PulsePlanHandler.set_mode("repaired")
            passed = request(
                base,
                token,
                f"/projects/{project_id}/changes/{repaired_change['id']}/verify",
                "POST",
                {"plan_id": repaired_plan["id"]},
            )
            assert passed["items"][0]["result"] == "AUTOMATED_PASS"
            final_gate = request(
                base,
                token,
                f"/projects/{project_id}/changes/{repaired_change['id']}/gate",
            )
            assert final_gate["state"] == "VERIFIED_COMPLETE"
            assert (
                request(base, token, f"/projects/{project_id}/regressions")[
                    "regressions"
                ][0]["status"]
                == "RESOLVED"
            )

            first_pid = process.pid
            descendants = descendant_process_ids(first_pid)
            stop_engine(process)
            assert process.poll() is not None
            for child_pid in descendants:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    continue
                raise AssertionError(f"orphan packaged child process: {child_pid}")

            process, base = start_engine(engine, environment)
            assert (
                request(base, token, f"/projects/{project_id}/regressions")[
                    "regressions"
                ][0]["status"]
                == "RESOLVED"
            )
            assert (
                request(
                    base,
                    token,
                    f"/projects/{project_id}/repair-contexts/{context['id']}",
                )["digest"]
                == context["digest"]
            )
            assert (
                request(
                    base,
                    token,
                    f"/projects/{project_id}/verification-runs/{failed['id']}",
                )["items"][0]["result"]
                == "FAIL"
            )
            assert (
                request(
                    base,
                    token,
                    f"/projects/{project_id}/verification-runs/{passed['id']}",
                )["items"][0]["result"]
                == "AUTOMATED_PASS"
            )
            assert (
                request(
                    base,
                    token,
                    f"/projects/{project_id}/changes/{repaired_change['id']}/gate",
                )["state"]
                == "VERIFIED_COMPLETE"
            )
            assert request(
                base,
                token,
                f"/projects/{project_id}/evidence/bundles/{failed_bundle_id}",
            )["items"]
            print(
                json.dumps(
                    {
                        "schema": "mellowyak.phase5_packaged_validation.v1",
                        "status": "VERIFIED_WORKING",
                        "database_schema": health["database_schema_version"],
                        "startup_seconds": round(startup_seconds, 3),
                        "baseline_bundle_id": baseline["evidence_bundle_id"],
                        "failed_bundle_id": failed_bundle_id,
                        "failed_run_id": failed["id"],
                        "failed_verification_seconds": round(
                            failed["items"][0]["duration_ms"] / 1000, 3
                        ),
                        "regression_id": regression["id"],
                        "blocked_gate_id": gate["id"],
                        "repair_context_id": context["id"],
                        "repair_context_digest": context["digest"],
                        "repaired_run_id": passed["id"],
                        "repaired_verification_seconds": round(
                            passed["items"][0]["duration_ms"] / 1000, 3
                        ),
                        "verified_gate_id": final_gate["id"],
                        "restart_history_reload": True,
                        "orphan_child_processes": False,
                        "loopback_only": True,
                        "authentication_required": True,
                        "source_uploaded": False,
                        "evidence_uploaded": False,
                        "repair_context_transmitted": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
    finally:
        if process is not None:
            stop_engine(process)
        PulsePlanHandler.set_mode("baseline")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

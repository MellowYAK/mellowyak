from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.protection.policy import (
    ALGORITHM_VERSION,
    MAX_PLAN_ITEMS,
    MAX_REQUIRED_CHECKS,
    MAX_SUGGESTED_CHECKS,
    POLICY_VERSION,
)
from mellowyak_engine.settings.config import EngineSettings
from mellowyak_engine.verification.adapters.human_attestation import HumanAttestationAdapter
from mellowyak_engine.verification.assertions import evaluate_assertion

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fixtures.pulseplan.server import PulsePlanHandler  # noqa: E402

TOKEN = "phase-five-session-token-that-is-long-enough-12345"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "pulseplan-source"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MellowYak Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@mellowyak.invalid"], cwd=root, check=True)
    (root / "time-format.js").write_text(
        "export function formatEventTime(time) { return time; }\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    return root


@pytest.mark.parametrize(
    "table",
    [
        "protection_plans",
        "protection_plan_items",
        "verification_runs",
        "verification_run_items",
        "assertion_results",
        "human_verification_attestations",
        "regression_findings",
        "completion_gate_decisions",
        "repair_contexts",
        "repair_context_items",
        "reverification_links",
        "verification_audit_events",
    ],
)
def test_phase5_migration_contains_required_tables(tmp_path: Path, table: str) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / table, session_token=TOKEN))
    with app.state.runtime.database.engine.connect() as connection:
        names = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert table in names
    app.state.runtime.browser.close()


class FakeLocator:
    def __init__(self, visible: bool = True, text: str = "14:00 IDT", attribute: str = "ready"):
        self.visible = visible
        self.text = text
        self.attribute = attribute

    def is_visible(self, timeout: int) -> bool:
        return self.visible and timeout > 0

    def inner_text(self, timeout: int) -> str:
        assert timeout > 0
        return self.text

    def get_attribute(self, _name: str, timeout: int) -> str:
        assert timeout > 0
        return self.attribute


class FakePage:
    url = "http://127.0.0.1:8262/events/planning-sync"

    def __init__(self, locator: FakeLocator | None = None) -> None:
        self.value = locator or FakeLocator()

    def locator(self, _selector: str) -> FakeLocator:
        return self.value


@pytest.mark.parametrize(
    "assertion,expected",
    [
        ({"type": "URL_EQUALS", "expected": FakePage.url}, "PASS"),
        ({"type": "URL_EQUALS", "expected": "http://localhost/wrong"}, "FAIL"),
        ({"type": "URL_CONTAINS", "expected": "planning-sync"}, "PASS"),
        ({"type": "ELEMENT_VISIBLE", "selector": "#event"}, "PASS"),
        ({"type": "ELEMENT_HIDDEN", "selector": "#event"}, "FAIL"),
        ({"type": "TEXT_CONTAINS", "selector": "#event", "expected": "14:00"}, "PASS"),
        (
            {
                "type": "ATTRIBUTE_EQUALS",
                "selector": "#event",
                "attribute": "data-state",
                "expected": "ready",
            },
            "PASS",
        ),
        ({"type": "SCREENSHOT_REFERENCE"}, "NEEDS_REVIEW"),
        ({"type": "HUMAN_NOTE"}, "NEEDS_REVIEW"),
        ({"type": "UNSUPPORTED_ASSERTION"}, "INCONCLUSIVE"),
    ],
)
def test_assertion_contract(assertion: dict[str, str], expected: str) -> None:
    result = evaluate_assertion(FakePage(), assertion, [], "test-adapter-v1")
    assert result["result"] == expected
    assert result["adapter_version"] == "test-adapter-v1"


@pytest.mark.parametrize(
    "assertion,observations,expected",
    [
        (
            {"type": "API_CALL_OBSERVED", "method": "POST", "expected": "/events"},
            [{"kind": "request", "method": "POST", "url": "http://127.0.0.1/events"}],
            "PASS",
        ),
        (
            {"type": "API_CALL_OBSERVED", "method": "DELETE", "expected": "/events"},
            [{"kind": "request", "method": "POST", "url": "http://127.0.0.1/events"}],
            "FAIL",
        ),
        (
            {"type": "HTTP_STATUS_OBSERVED", "status": 204, "path": "/events"},
            [{"kind": "response", "status": 204, "url": "http://127.0.0.1/events"}],
            "PASS",
        ),
        (
            {"type": "HTTP_STATUS_OBSERVED", "status": 500, "path": "/events"},
            [{"kind": "response", "status": 204, "url": "http://127.0.0.1/events"}],
            "FAIL",
        ),
    ],
)
def test_network_assertion_contract(
    assertion: dict[str, object], observations: list[dict[str, object]], expected: str
) -> None:
    result = evaluate_assertion(FakePage(), assertion, observations, "test-adapter-v1")
    assert result["result"] == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (MAX_PLAN_ITEMS, 250),
        (MAX_REQUIRED_CHECKS, 50),
        (MAX_SUGGESTED_CHECKS, 100),
        (ALGORITHM_VERSION, "protection-selection-v1"),
        (POLICY_VERSION, "local-default-v1"),
    ],
)
def test_phase5_policy_contract(value: object, expected: object) -> None:
    assert value == expected


@pytest.mark.parametrize(
    "choice,expected",
    [
        ("WORKS", "HUMAN_ATTESTED_PASS"),
        ("DOES_NOT_WORK", "FAIL"),
        ("UNABLE_TO_VERIFY", "INCONCLUSIVE"),
        ("UNABLE_TO_DETERMINE", "INCONCLUSIVE"),
    ],
)
def test_human_attestation_adapter_contract(choice: str, expected: str) -> None:
    adapter = HumanAttestationAdapter()
    assert adapter.availability() == (True, None)
    assert adapter.normalize(choice, True, "Explicit local confirmation.") == expected


def test_pulseplan_regression_repair_and_reverification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MELLOWYAK_PHASE4_VALIDATION", "1")
    PulsePlanHandler.set_mode("baseline")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PulsePlanHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = repository(tmp_path)
    (root / ".mellowyak-reference-project.json").write_text(
        json.dumps(
            {
                "schema": "mellowyak.phase12.reference.v1",
                "synthetic": True,
                "product": "PulsePlan Reference",
                "fixture_scenario": "pulseplan",
            }
        ),
        encoding="utf-8",
    )
    try:
        app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
        if not app.state.runtime.verification.adapter.availability()[0]:
            pytest.skip("packaged Chromium is unavailable")
        with TestClient(app) as client:
            project = client.post(
                "/projects",
                headers=headers(),
                json={
                    "path": str(root),
                    "display_name": "PulsePlan",
                    "monitoring_mode": "paused",
                },
            ).json()
            project_id = project["id"]
            behavior_response = client.post(
                f"/projects/{project_id}/behaviors",
                headers=headers(),
                json={
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
            assert behavior_response.status_code == 200, behavior_response.text
            behavior = behavior_response.json()
            base_url = f"http://127.0.0.1:{server.server_port}/"
            runtime = client.post(
                f"/projects/{project_id}/runtimes",
                headers=headers(),
                json={"display_name": "PulsePlan fixture", "base_url": base_url},
            ).json()
            capture = client.post(
                f"/projects/{project_id}/captures",
                headers=headers(),
                json={
                    "behavior_id": behavior["id"],
                    "runtime_configuration_id": runtime["id"],
                },
            ).json()
            capture_id = capture["id"]
            flowed = client.post(
                f"/projects/{project_id}/captures/{capture_id}/validation-fixture-flow",
                headers=headers(),
            )
            assert flowed.status_code == 200, flowed.text
            stopped = client.post(
                f"/projects/{project_id}/captures/{capture_id}/stop", headers=headers()
            ).json()
            reviewed = client.post(
                f"/projects/{project_id}/captures/{capture_id}/review",
                headers=headers(),
                json={
                    "expected_assertions": [
                        {
                            "type": "TEXT_CONTAINS",
                            "selector": "[data-testid=event-time]",
                            "expected": "14:00",
                        }
                    ],
                    "step_updates": [
                        {"id": step["id"], "included": True} for step in stopped["steps"]
                    ],
                },
            )
            assert reviewed.status_code == 200, reviewed.text
            profile = client.post(
                f"/projects/{project_id}/runtime-profiles",
                headers=headers(),
                json={
                    "display_name": "PulsePlan browser replay",
                    "runtime_type": "GENERIC_PROCESS",
                    "execution_mode": "MANUAL",
                    "executable_reference": "python3",
                    "argv": ["-c", "print('browser replay profile')"],
                    "relative_working_directory": ".",
                    "network_policy": "LOOPBACK_ONLY",
                    "approved": True,
                },
            )
            assert profile.status_code == 200, profile.text
            validated = client.post(
                f"/projects/{project_id}/captures/{capture_id}/validate",
                headers=headers(),
                json={"runtime_profile_version_id": profile.json()["current_version_id"]},
            )
            assert validated.status_code == 200, validated.text
            assert validated.json()["result"] == "PASS"
            accepted = client.post(
                f"/projects/{project_id}/captures/{capture_id}/accept-baseline",
                headers=headers(),
                json={"reviewer": "Local reviewer", "notes": "Verified baseline."},
            )
            assert accepted.status_code == 200, accepted.text

            (root / "time-format.js").write_text(
                "export function formatEventTime(time) { return `${time} IDT`; }\n"
                "export const savedTimeOffsetHours = 1;\n",
                encoding="utf-8",
            )
            change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
            client.post(
                f"/projects/{project_id}/changes/{change['id']}/intent",
                headers=headers(),
                json={"intent": "Display the IDT timezone abbreviation."},
            )
            analysis = client.post(
                f"/projects/{project_id}/changes/{change['id']}/analyze",
                headers=headers(),
                json={},
            )
            assert analysis.status_code == 200, analysis.text
            plan = client.post(
                f"/projects/{project_id}/changes/{change['id']}/protection-plan",
                headers=headers(),
                json={},
            )
            assert plan.status_code == 200, plan.text
            assert plan.json()["counts"]["required"] == 1
            PulsePlanHandler.set_mode("regression")
            failed = client.post(
                f"/projects/{project_id}/changes/{change['id']}/verify",
                headers=headers(),
                json={"plan_id": plan.json()["id"]},
            )
            assert failed.status_code == 200, failed.text
            assert failed.json()["items"][0]["result"] == "FAIL", failed.json()
            gate = client.get(
                f"/projects/{project_id}/changes/{change['id']}/gate", headers=headers()
            ).json()
            assert gate["state"] == "BLOCKED"
            regressions = client.get(
                f"/projects/{project_id}/regressions", headers=headers()
            ).json()["regressions"]
            assert len(regressions) == 1
            context = client.post(
                f"/projects/{project_id}/regressions/{regressions[0]['id']}/repair-context",
                headers=headers(),
                json={},
            )
            assert context.status_code == 200, context.text
            context_json = context.json()
            assert context_json["schema_version"] == "mellowyak.repair_context.v1"
            assert context_json["payload"]["keep"] == "Display the IDT timezone abbreviation."
            assert all(
                not Path(path).is_absolute() for path in context_json["payload"]["relevant_files"]
            )
            assert TOKEN not in json.dumps(context_json)
            saved = client.post(
                f"/projects/{project_id}/repair-contexts/{context_json['id']}/save-local",
                headers=headers(),
                json={},
            ).json()
            assert saved["relative_path"].startswith("repair-contexts/")

            (root / "time-format.js").write_text(
                "export function formatEventTime(time) { return `${time} IDT`; }\n"
                "export const savedTimeOffsetHours = 0;\n",
                encoding="utf-8",
            )
            repaired_change = client.get(
                f"/projects/{project_id}/changes/current", headers=headers()
            ).json()
            client.post(
                f"/projects/{project_id}/changes/{repaired_change['id']}/analyze",
                headers=headers(),
                json={},
            )
            repaired_plan = client.post(
                f"/projects/{project_id}/changes/{repaired_change['id']}/protection-plan",
                headers=headers(),
                json={},
            ).json()
            PulsePlanHandler.set_mode("repaired")
            passed = client.post(
                f"/projects/{project_id}/changes/{repaired_change['id']}/verify",
                headers=headers(),
                json={"plan_id": repaired_plan["id"]},
            )
            assert passed.status_code == 200, passed.text
            assert passed.json()["items"][0]["result"] == "AUTOMATED_PASS"
            final_gate = client.get(
                f"/projects/{project_id}/changes/{repaired_change['id']}/gate",
                headers=headers(),
            ).json()
            assert final_gate["state"] == "VERIFIED_COMPLETE"
            preserved = client.get(f"/projects/{project_id}/regressions", headers=headers()).json()[
                "regressions"
            ]
            assert preserved[0]["status"] == "RESOLVED"
    finally:
        PulsePlanHandler.set_mode("baseline")
        server.shutdown()
        server.server_close()

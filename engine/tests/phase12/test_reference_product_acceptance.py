from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.models import RepairWorkspace
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase12-reference-product-acceptance-token"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _generator_module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "create_phase12m_reference_project.py"
    spec = importlib.util.spec_from_file_location("phase12_reference_acceptance_generator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git_init(root: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "MellowYak Reference",
            "GIT_AUTHOR_EMAIL": "reference@mellowyak.invalid",
            "GIT_COMMITTER_NAME": "MellowYak Reference",
            "GIT_COMMITTER_EMAIL": "reference@mellowyak.invalid",
        }
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=environment)
    subprocess.run(["git", "add", "."], cwd=root, check=True, env=environment)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Create disposable RideFlow reference"],
        cwd=root,
        check=True,
        env=environment,
    )


def _approve_profiles(client: TestClient, project_id: str) -> list[dict[str, object]]:
    detected = client.post(f"/projects/{project_id}/runtime/detect", headers=_headers())
    assert detected.status_code == 200, detected.text
    candidates = [item for item in detected.json()["candidates"] if item.get("detected") is True]
    assert len(candidates) == 4
    profiles: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates):
        created = client.post(
            f"/projects/{project_id}/runtime-profiles",
            headers=_headers(),
            json={
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
            },
        )
        assert created.status_code == 200, created.text
        profiles.append(created.json())
    return profiles


def _start_profile(client: TestClient, project_id: str, profile: dict[str, object]) -> None:
    started = client.post(
        f"/projects/{project_id}/runtime-profiles/{profile['id']}/start",
        headers=_headers(),
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "RUNNING"


def _episode(app, project_id: str, path: str) -> dict[str, object]:
    app.state.runtime.projects.refresh_git(project_id, [path])
    episode_id = app.state.runtime.episodes.record(project_id, [path])
    assert episode_id
    episode = app.state.runtime.episodes.stabilize_now(project_id)
    assert episode and episode["status"] == "STABILIZED"
    return episode


def _candidate(
    client: TestClient,
    app,
    project_id: str,
    regression_id: str,
    mode: str,
) -> tuple[dict[str, object], dict[str, object], Path]:
    workspace_response = client.post(
        f"/projects/{project_id}/regressions/{regression_id}/repair-workspace",
        headers=_headers(),
    )
    assert workspace_response.status_code == 200, workspace_response.text
    workspace = workspace_response.json()
    workspace_root = app.state.runtime.paths.root / workspace["relative_path"] / "current"
    selected_mode = "farthest" if mode == "bad" else mode
    (workspace_root / "api" / "selection_mode.txt").write_text(
        f"{selected_mode}\n", encoding="utf-8"
    )
    if mode == "bad":
        (workspace_root / "bad-candidate.txt").write_text(
            "Candidate deliberately leaves the deterministic regression in place.\n",
            encoding="utf-8",
        )
    candidate_response = client.post(
        f"/projects/{project_id}/repair-workspaces/{workspace['id']}/candidates",
        headers=_headers(),
    )
    assert candidate_response.status_code == 200, candidate_response.text
    candidate = candidate_response.json()
    validation_response = client.post(
        f"/projects/{project_id}/repair-candidates/{candidate['id']}/validate",
        headers=_headers(),
    )
    assert validation_response.status_code == 200, validation_response.text
    return candidate, validation_response.json(), workspace_root


def _apply(client: TestClient, project_id: str, candidate_id: str) -> dict[str, object]:
    prepared = client.post(
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/prepare",
        headers=_headers(),
    )
    assert prepared.status_code == 200, prepared.text
    pending = prepared.json()
    assert pending["state"] == "AWAITING_CONFIRMATION"
    assert pending["safety_snapshot_id"] is None
    assert pending["journal_relative_path"] == ""
    confirmed = client.post(
        f"/projects/{project_id}/repair-candidates/{candidate_id}/apply/confirm",
        headers=_headers(),
        json={
            "confirmation_nonce": pending["confirmation_nonce"],
            "deliberate_confirmation": True,
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def test_workflow_state_model_is_authenticated_and_authoritative(tmp_path: Path) -> None:
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        assert client.get("/workflow/state-model").status_code == 401
        response = client.get("/workflow/state-model", headers=_headers())
        assert response.status_code == 200
        model = response.json()
        assert set(model["apply"]["AWAITING_CONFIRMATION"]) == {
            "BLOCKED",
            "CANCELLED",
            "PREFLIGHT",
        }
        assert model["apply"]["COMMITTED"] == []
        assert "KNOWN_GOOD" in model["behavior"]
        assert "PRODUCTION_CHANNEL_UNPUBLISHED" in model["updater"]


def test_real_rideflow_known_good_regression_repair_apply_and_rollback(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MELLOWYAK_BROWSER_HEADLESS", "1")
    monkeypatch.setenv("MELLOWYAK_PHASE4_VALIDATION", "1")
    root = tmp_path / "rideflow"
    generated = _generator_module().create(root, 38371, 38372)
    _git_init(root)
    sentinel = root / "unrelated-sentinel.txt"
    sentinel.write_bytes(b"phase12-unrelated-sentinel\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=MellowYak Reference",
            "-c",
            "user.email=reference@mellowyak.invalid",
            "commit",
            "-q",
            "-m",
            "Add unrelated sentinel",
        ],
        cwd=root,
        check=True,
    )
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_response = client.post(
            "/projects",
            headers=_headers(),
            json={
                "path": str(root),
                "display_name": "RideFlow Reference",
                "monitoring_mode": "paused",
            },
        )
        assert project_response.status_code == 200, project_response.text
        project_id = project_response.json()["id"]
        profiles = _approve_profiles(client, project_id)
        by_name = {str(item["display_name"]): item for item in profiles}
        _start_profile(client, project_id, by_name["RideFlow Python API"])
        _start_profile(client, project_id, by_name["RideFlow Web frontend"])

        behavior_response = client.post(
            f"/projects/{project_id}/behaviors",
            headers=_headers(),
            json={
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
        assert behavior_response.status_code == 200, behavior_response.text
        behavior = behavior_response.json()
        runtime_response = client.post(
            f"/projects/{project_id}/runtimes",
            headers=_headers(),
            json={
                "display_name": "RideFlow browser",
                "base_url": generated["web_url"],
            },
        )
        assert runtime_response.status_code == 200, runtime_response.text
        runtime = runtime_response.json()
        capture_response = client.post(
            f"/projects/{project_id}/captures",
            headers=_headers(),
            json={
                "behavior_id": behavior["id"],
                "runtime_configuration_id": runtime["id"],
            },
        )
        assert capture_response.status_code == 200, capture_response.text
        capture_id = capture_response.json()["id"]
        fixture = client.post(
            f"/projects/{project_id}/captures/{capture_id}/validation-fixture-flow",
            headers=_headers(),
        )
        assert fixture.status_code == 200, fixture.text
        stopped = client.post(
            f"/projects/{project_id}/captures/{capture_id}/stop", headers=_headers()
        )
        assert stopped.status_code == 200, stopped.text
        reviewed = client.post(
            f"/projects/{project_id}/captures/{capture_id}/review",
            headers=_headers(),
            json={
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
                ]
            },
        )
        assert reviewed.status_code == 200, reviewed.text
        validated = client.post(
            f"/projects/{project_id}/captures/{capture_id}/validate",
            headers=_headers(),
            json={
                "runtime_profile_version_id": by_name["RideFlow Web frontend"]["current_version_id"]
            },
        )
        assert validated.status_code == 200, validated.text
        assert validated.json()["result"] == "PASS"
        accepted = client.post(
            f"/projects/{project_id}/captures/{capture_id}/accept-baseline",
            headers=_headers(),
            json={"reviewer": "Phase 12M local acceptance"},
        )
        assert accepted.status_code == 200, accepted.text
        probes = client.get(f"/projects/{project_id}/probes", headers=_headers()).json()["probes"]
        browser_probe = next(item for item in probes if item["probe_type"] == "BROWSER")

        readme = root / "README.md"
        readme.write_text(readme.read_text() + "\nHarmless documentation note.\n")
        harmless = _episode(app, project_id, "README.md")
        harmless_run = client.post(
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            headers=_headers(),
            json={"snapshot_id": harmless["resulting_snapshot_id"]},
        )
        assert harmless_run.status_code == 200, harmless_run.text
        assert harmless_run.json()["result"] == "PASS"
        assert harmless_run.json()["signal"]["regression_id"] is None

        mode = root / "api" / "selection_mode.txt"
        mode.write_text("farthest\n", encoding="utf-8")
        broken = _episode(app, project_id, "api/selection_mode.txt")
        failed = client.post(
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            headers=_headers(),
            json={"snapshot_id": broken["resulting_snapshot_id"]},
        )
        assert failed.status_code == 200, failed.text
        failure = failed.json()
        assert failure["result"] == "FAIL"
        assert failure["attempt_count"] == 2
        assert failure["signal"]["state"] == "CONFIRMED"
        regression_id = failure["signal"]["regression_id"]
        assert regression_id

        _, rejected_validation, _ = _candidate(client, app, project_id, regression_id, "bad")
        assert rejected_validation["status"] == "FAILED"
        valid_candidate, valid_validation, _ = _candidate(
            client, app, project_id, regression_id, "nearest"
        )
        assert valid_validation["status"] == "PASSED"
        committed = _apply(client, project_id, str(valid_candidate["id"]))
        assert committed["state"] == "COMMITTED"
        assert mode.read_text(encoding="utf-8") == "nearest\n"

        mode.write_text("farthest\n", encoding="utf-8")
        broken_again = _episode(app, project_id, "api/selection_mode.txt")
        failed_again = client.post(
            f"/projects/{project_id}/probes/{browser_probe['id']}/run",
            headers=_headers(),
            json={"snapshot_id": broken_again["resulting_snapshot_id"]},
        ).json()
        rollback_regression_id = failed_again["signal"]["regression_id"]
        assert rollback_regression_id
        rollback_candidate, rollback_validation, _ = _candidate(
            client, app, project_id, rollback_regression_id, "nearest"
        )
        assert rollback_validation["status"] == "PASSED"
        with app.state.runtime.database.sessions.begin() as session:
            workspace = session.get(RepairWorkspace, rollback_candidate["workspace_id"])
            assert workspace
            policy = json.loads(workspace.validation_policy_json)
            policy["checks"].append(
                {
                    "id": "forced-post-check-failure",
                    "type": "FILE_CONTAINS",
                    "requirement": "REQUIRED",
                    "path": "api/selection_mode.txt",
                    "expected": "post-check-must-fail",
                }
            )
            workspace.validation_policy_json = json.dumps(policy, sort_keys=True)
        before = mode.read_bytes()
        sentinel_before = sentinel.read_bytes()
        rolled_back = _apply(client, project_id, str(rollback_candidate["id"]))
        assert rolled_back["state"] == "ROLLED_BACK"
        assert mode.read_bytes() == before
        assert sentinel.read_bytes() == sentinel_before
        assert rolled_back["rollback_evidence"]["byte_identity_result"] == "VERIFIED"
        assert client.get("/recovery/pending", headers=_headers()).json()["transactions"] == []

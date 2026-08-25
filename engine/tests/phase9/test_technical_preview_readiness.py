from __future__ import annotations

import json
import subprocess
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.models import Alert
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-nine-session-token-that-is-long-enough-12345"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def repository(parent: Path, name: str, content: str = "baseline\n") -> Path:
    root = parent / name
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "MellowYak Test")
    git(root, "config", "user.email", "test@mellowyak.invalid")
    (root / "sentinel.txt").write_text(content, encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "baseline")
    return root


def connect(client: TestClient, root: Path, name: str = "Preview Fixture") -> str:
    response = client.post(
        "/projects",
        headers=headers(),
        json={"path": str(root), "display_name": name, "monitoring_mode": "paused"},
    )
    assert response.status_code == 200, response.text
    project_id = str(response.json()["id"])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        scan = client.get(f"/projects/{project_id}/scan", headers=headers()).json()
        if scan and scan["status"] != "running":
            return project_id
        time.sleep(0.02)
    raise AssertionError("scan did not finish")


def test_phase9_migration_first_run_and_replay(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    expected = {
        "onboarding_state",
        "technical_preview_preferences",
        "project_location_history",
        "diagnostic_runs",
        "support_bundle_records",
        "notification_activation_events",
        "update_validation_runs",
        "package_acceptance_runs",
    }
    with app.state.runtime.database.engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert expected <= tables
    with TestClient(app) as client:
        initial = client.get("/app/onboarding", headers=headers()).json()
        assert initial["requires_first_run"] is True
        completed = client.put(
            "/app/onboarding",
            headers=headers(),
            json={"current_step": "complete", "selected_path": "demo_lab", "completed": True},
        ).json()
        assert completed["completed"] is True
        replay = client.post("/app/onboarding/replay", headers=headers(), json={}).json()
        assert replay["completed"] is True
        assert replay["replay_active"] is True
        assert replay["requires_first_run"] is False


def test_disconnected_reconnect_and_identity_rejection_preserve_source(tmp_path: Path) -> None:
    source = repository(tmp_path, "source")
    relocated = tmp_path / "relocated"
    git(tmp_path, "clone", str(source), str(relocated))
    wrong = repository(tmp_path, "wrong", "wrong identity\n")
    source_head = git(source, "rev-parse", "HEAD")
    wrong_head = git(wrong, "rev-parse", "HEAD")
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, source)
        client.post(f"/projects/{project_id}/disconnect", headers=headers(), json={})
        disconnected = client.get("/projects/disconnected", headers=headers()).json()["projects"]
        assert disconnected[0]["state"] == "DISCONNECTED"
        assert disconnected[0]["source_modified"] is False

        rejected = client.post(
            f"/projects/{project_id}/relocate",
            headers=headers(),
            json={"path": str(wrong)},
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"] == "PROJECT_IDENTITY_MISMATCH"

        preview = client.get(
            f"/projects/{project_id}/identity-preview",
            headers=headers(),
            params={"path": str(relocated)},
        ).json()
        assert preview["matched"] is True
        accepted = client.post(
            f"/projects/{project_id}/reconnect",
            headers=headers(),
            json={"path": str(relocated)},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["source_moved"] is False

    assert git(source, "rev-parse", "HEAD") == source_head
    assert git(wrong, "rev-parse", "HEAD") == wrong_head
    assert (source / "sentinel.txt").read_text(encoding="utf-8") == "baseline\n"


def test_notification_routes_diagnostics_and_activity_modes(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        invalid = client.post(
            "/notifications/activate",
            headers=headers(),
            json={"route": {"screen": "../../private", "token": "secret"}},
        ).json()
        assert invalid["status"] == "REJECTED"
        assert invalid["route"] == {"screen": "alerts"}

        stale = client.post(
            "/notifications/activate",
            headers=headers(),
            json={"route": {"screen": "project", "project_id": "missing"}},
        ).json()
        assert stale["status"] == "STALE"
        assert stale["route"] == {"screen": "alerts"}

        first_id = connect(client, repository(tmp_path, "route-first"), "First")
        second_id = connect(client, repository(tmp_path, "route-second"), "Second")
        alert_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with app.state.runtime.database.sessions.begin() as session:
            session.add(
                Alert(
                    id=alert_id,
                    project_id=first_id,
                    severity="WARNING",
                    category="PROJECT",
                    title_key="alerts.projectError.title",
                    summary_key="alerts.projectError.summary",
                    parameters_json="{}",
                    route_json="{}",
                    deduplication_key=f"phase9-cross-project-{alert_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
        cross_project = client.post(
            "/notifications/activate",
            headers=headers(),
            json={
                "route": {
                    "screen": "project",
                    "project_id": second_id,
                    "alert_id": alert_id,
                }
            },
        ).json()
        assert cross_project["status"] == "REJECTED"
        assert cross_project["reason"] == "NOTIFICATION_CROSS_PROJECT"

        preferences = client.put(
            "/app/activity-mode",
            headers=headers(),
            json={"activity_mode": "battery_saver"},
        ).json()
        assert preferences["activity_mode"] == "battery_saver"
        assert "deep_runtime_observation" in preferences["deferred"]
        assert preferences["snapshot_correctness"] is True

        diagnostics = client.get("/diagnostics", headers=headers()).json()
        assert diagnostics["data_root"] == "<DATA_ROOT>"
        assert diagnostics["bearer_token_exposed"] is False
        assert diagnostics["tray"]["private_paths_exposed"] is False


def test_support_bundle_redacts_paths_and_secrets(tmp_path: Path) -> None:
    data_root = tmp_path / "private-data"
    source = repository(tmp_path, "private-source")
    app = create_app(EngineSettings(data_root=data_root, session_token=TOKEN))
    canary = "MELLOWYAK_SECRET_CANARY_82EFC1"
    (data_root / "logs" / "preview.jsonl").write_text(
        json.dumps(
            {
                "path": str(source),
                "authorization": f"Bearer {canary}",
                "password": canary,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with TestClient(app) as client:
        connect(client, source, "Private Fixture")
        exported = client.post("/diagnostics/support-bundle", headers=headers(), json={})
        assert exported.status_code == 200, exported.text
        result = exported.json()
        bundle = data_root / result["relative_path"]
        assert bundle.is_file()
        lookup = client.get(
            f"/diagnostics/support-bundles/{result['bundle_id']}", headers=headers()
        ).json()
        assert lookup["sha256"] == result["sha256"]
    raw = bundle.read_bytes()
    assert canary.encode() not in raw
    assert str(source).encode() not in raw
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        assert any(name.endswith("manifest.json") for name in names)
        assert not any("snapshot" in name or "evidence" in name for name in names)


def test_disposable_updater_fixtures_and_package_acceptance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MELLOWYAK_DEMO_TEST_MODE", "1")
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        expected = {
            "valid": "ACCEPTED",
            "invalid_signature": "REJECTED",
            "tampered": "REJECTED",
            "interrupted": "REJECTED_INCOMPLETE",
            "no_update": "NO_UPDATE",
        }
        for fixture, status in expected.items():
            result = client.post(
                "/updates/test/validate",
                headers=headers(),
                json={"fixture": fixture},
            ).json()
            assert result["status"] == status
            assert result["private_key_persisted"] is False
            assert result["production_configuration_changed"] is False
        package = client.post(
            "/package-acceptance/run",
            headers=headers(),
            json={
                "status": "PARTIAL",
                "summary": {"self_test": "PASS", "secret": "must-not-persist"},
            },
        ).json()
        assert package["summary"] == {"self_test": "PASS"}
        assert client.get("/package-acceptance", headers=headers()).json()["status"] == "PARTIAL"

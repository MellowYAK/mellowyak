from __future__ import annotations

import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-six-session-token-that-is-long-enough-12345"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MellowYak Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@mellowyak.invalid"], cwd=root, check=True)
    (root / "sentinel.txt").write_text("source must survive\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    return root


def connect_project(
    client: TestClient, root: Path, name: str = "Safe Project"
) -> dict[str, object]:
    response = client.post(
        "/projects",
        headers=headers(),
        json={"path": str(root), "display_name": name, "monitoring_mode": "paused"},
    )
    assert response.status_code == 200, response.text
    project = response.json()
    for _ in range(100):
        scan = client.get(f"/projects/{project['id']}/scan", headers=headers()).json()
        if scan and scan["status"] != "running":
            break
        time.sleep(0.02)
    return project


def test_phase6_migration_and_persistent_preferences(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    expected = {
        "alerts",
        "notification_preferences",
        "project_notification_preferences",
        "quiet_mode_state",
        "application_preferences",
        "project_lifecycle_events",
        "project_disconnection_records",
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
        settings = client.put(
            "/settings/notifications",
            headers=headers(),
            json={"hide_details": True, "critical_override": False},
        ).json()
        assert settings["hide_details"] is True
        quiet = client.post(
            "/settings/quiet-mode/start",
            headers=headers(),
            json={"duration": "until_off", "allow_critical": False},
        ).json()
        assert quiet["active"] is True and quiet["until_turned_off"] is True
        assert client.get("/settings/quiet-mode", headers=headers()).json()["active"] is True


def test_alert_deduplication_state_and_unread_count(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    service = app.state.runtime.productization
    first = service.create_alert(
        project_id=None,
        category="ENGINE",
        severity="WARNING",
        title_key="alerts.reviewTitle",
        summary_key="alerts.reviewSummary",
        deduplication_key="engine:review",
        route={"screen": "alerts"},
        parameters={"project": "Local"},
    )
    second = service.create_alert(
        project_id=None,
        category="ENGINE",
        severity="WARNING",
        title_key="alerts.reviewTitle",
        summary_key="alerts.reviewSummary",
        deduplication_key="engine:review",
        route={"screen": "alerts"},
        parameters={"project": "Local"},
    )
    assert first["id"] == second["id"]
    with TestClient(app) as client:
        assert client.get("/alerts/unread-count", headers=headers()).json() == {"count": 1}
        marked = client.post(f"/alerts/{first['id']}/read", headers=headers(), json={}).json()
        assert marked["read"] is True
        resolved = client.post(f"/alerts/{first['id']}/resolve", headers=headers(), json={}).json()
        assert resolved["resolved"] is True
        assert client.post("/alerts/clear-resolved", headers=headers(), json={}).json() == {
            "cleared": 1
        }


def test_disconnect_reconnect_and_local_delete_never_modify_source(tmp_path: Path) -> None:
    source = repository(tmp_path)
    original_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
    ).stdout.strip()
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project = connect_project(client, source)
        project_id = str(project["id"])
        disconnected = client.post(f"/projects/{project_id}/disconnect", headers=headers(), json={})
        assert disconnected.status_code == 200
        assert client.get("/projects", headers=headers()).json()["projects"] == []
        assert (
            client.post(f"/projects/{project_id}/reconnect", headers=headers(), json={}).status_code
            == 200
        )
        preview = client.get(f"/projects/{project_id}/deletion-preview", headers=headers()).json()
        assert preview["source_will_be_modified"] is False
        deleted = client.post(
            f"/projects/{project_id}/delete-local-data",
            headers=headers(),
            json={"confirmation": "Safe Project"},
        )
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/projects/{project_id}", headers=headers()).status_code == 404
    assert (source / "sentinel.txt").read_text(encoding="utf-8") == "source must survive\n"
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert current_head == original_head

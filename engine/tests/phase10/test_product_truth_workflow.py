from __future__ import annotations

import json
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.models import (
    BehaviorVersion,
    ProjectChange,
    ProtectedBehavior,
    RegressionFinding,
    SourceEpisode,
)
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-ten-session-token-that-is-long-enough-12345"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def repository(parent: Path, name: str) -> Path:
    root = parent / name
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MellowYak Test"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@mellowyak.invalid"],
        cwd=root,
        check=True,
    )
    (root / "checkout.py").write_text('def checkout():\n    return "ok"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=root, check=True, capture_output=True)
    return root


def connect(client: TestClient, root: Path, name: str) -> str:
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


def test_home_and_diagnostics_report_only_persisted_product_truth(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        empty = client.get("/home/summary", headers=headers())
        assert empty.status_code == 200
        assert empty.json()["state"] == "NO_PROJECTS"
        assert empty.json()["projects"] == []

        project_id = connect(client, repository(tmp_path, "source"), "Demo Fixture")
        app.state.runtime.productization.create_alert(
            project_id=project_id,
            category="ENGINE",
            severity="WARNING",
            title_key="alerts.reviewTitle",
            summary_key="alerts.reviewSummary",
            deduplication_key="phase10:review",
            route={"screen": "project", "project_id": project_id},
            parameters={},
        )

        home = client.get("/home/summary", headers=headers()).json()
        assert home["counts"]["needs_review"] == 1
        assert home["counts"]["paused"] == 1
        assert home["projects"][0]["id"] == project_id
        assert home["projects"][0]["state"] == "PAUSED"

        diagnostics = client.get("/diagnostics/overview", headers=headers()).json()
        assert diagnostics["counts"]["projects"] == 1
        assert diagnostics["privacy"]["bearer_token_exposed"] is False
        assert diagnostics["privacy"]["outbound_product_network"] is False
        assert {fact["key"] for fact in diagnostics["facts"]} >= {
            "local_api",
            "database",
            "storage",
            "browser_runtime",
            "runtime_adapter",
            "updater",
            "signing",
        }


def test_episode_activity_and_project_boundaries_are_exact(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        first_id = connect(client, repository(tmp_path, "first"), "First")
        second_id = connect(client, repository(tmp_path, "second"), "Second")
        episode_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with app.state.runtime.database.sessions.begin() as session:
            session.add(
                SourceEpisode(
                    id=episode_id,
                    project_id=first_id,
                    started_at=now,
                    ended_at=now,
                    event_count=2,
                    added_paths_json=json.dumps(["new.py"]),
                    modified_paths_json=json.dumps(["checkout.py"]),
                    deleted_paths_json="[]",
                    renamed_paths_json="[]",
                    dependency_changes_json="[]",
                    runtime_events_json="[]",
                    git_anchor_json=json.dumps({"branch": "main"}),
                    status="STABILIZED",
                )
            )

        activity = client.get(f"/projects/{first_id}/activity", headers=headers()).json()
        episode_items = [item for item in activity["items"] if item["entity_id"] == episode_id]
        assert len(episode_items) == 1
        assert episode_items[0]["event_type"] == "EPISODE_STABILIZED"
        assert episode_items[0]["facts"]["changed_count"] == 2

        detail = client.get(
            f"/projects/{first_id}/episodes/{episode_id}/summary", headers=headers()
        ).json()
        assert detail["changed"] == {
            "added": ["new.py"],
            "modified": ["checkout.py"],
            "deleted": [],
            "renamed": [],
            "dependencies": [],
        }
        assert detail["result"]["signal"] == "WATCH"
        assert detail["unknowns"] == ["ROOT_CAUSE_NOT_PROVEN"]

        cross_project = client.get(
            f"/projects/{second_id}/episodes/{episode_id}/summary", headers=headers()
        )
        assert cross_project.status_code == 404
        assert cross_project.json()["detail"] == "EPISODE_NOT_FOUND"


def test_regression_detail_preserves_evidence_and_rejects_cross_project_reads(
    tmp_path: Path,
) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        first_id = connect(client, repository(tmp_path, "regression-first"), "First")
        second_id = connect(client, repository(tmp_path, "regression-second"), "Second")
        now = datetime.now(UTC)
        behavior_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        change_id = uuid.uuid4().hex
        regression_id = str(uuid.uuid4())
        with app.state.runtime.database.sessions.begin() as session:
            session.add(
                ProjectChange(
                    id=change_id,
                    project_id=first_id,
                    logical_key="phase10-regression",
                    change_kind="working_tree",
                    revision=1,
                    worktree_fingerprint="a" * 64,
                    changed_paths_json=json.dumps(["checkout.py"]),
                    status="change_detected",
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                ProtectedBehavior(
                    id=behavior_id,
                    project_id=first_id,
                    stable_key="checkout-remains-available",
                    display_name="Checkout remains available",
                    lifecycle_state="PROTECTED",
                    current_version_id=version_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.flush()
            session.add(
                BehaviorVersion(
                    id=version_id,
                    behavior_id=behavior_id,
                    project_id=first_id,
                    version_number=1,
                    title="Checkout remains available",
                    description="Synthetic disposable fixture behavior",
                    expected_outcome="Checkout returns ok",
                    criticality="HIGH",
                    content_digest="b" * 64,
                    created_at=now,
                )
            )
            session.flush()
            session.add(
                RegressionFinding(
                    id=regression_id,
                    project_id=first_id,
                    change_id=change_id,
                    behavior_id=behavior_id,
                    behavior_version_id=version_id,
                    status="CONFIRMED",
                    decision_reason="DETERMINISTIC_CHECK_FAILED",
                    source_identity_json=json.dumps({"branch": "main", "head": "c" * 40}),
                    created_at=now,
                )
            )

        detail = client.get(
            f"/projects/{first_id}/regressions/{regression_id}/detail", headers=headers()
        ).json()
        assert detail["status"] == "CONFIRMED"
        assert detail["behavior"]["expected_outcome"] == "Checkout returns ok"
        assert detail["changed"]["paths"] == ["checkout.py"]
        assert detail["current"]["result"] == "FAIL"
        assert detail["unknowns"] == [
            "ROOT_CAUSE_NOT_PROVEN",
            "BLAST_RADIUS_MAY_BE_INCOMPLETE",
        ]

        cross_project = client.get(
            f"/projects/{second_id}/regressions/{regression_id}/detail", headers=headers()
        )
        assert cross_project.status_code == 404
        assert cross_project.json()["detail"] == "REGRESSION_NOT_FOUND"

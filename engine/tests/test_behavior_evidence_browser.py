from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from mellowyak_engine.api.app import create_app
from mellowyak_engine.behaviors.service import BehaviorServiceError, validate_loopback_runtime_url
from mellowyak_engine.db.models import BrowserCaptureSession, EvidenceArtifact
from mellowyak_engine.evidence.service import EvidenceServiceError
from mellowyak_engine.evidence.store import EvidenceStore, EvidenceStoreError
from mellowyak_engine.settings.config import EngineSettings

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fixtures.pulseplan.server import PulsePlanHandler  # noqa: E402

TOKEN = "phase-four-session-token-that-is-long-enough-12345"


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "MellowYak Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@mellowyak.invalid"], cwd=root, check=True)
    (root / "app.ts").write_text("export const ready = true;\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True)
    return root


def connect(client: TestClient, root: Path) -> str:
    response = client.post(
        "/projects",
        headers=headers(),
        json={"path": str(root), "display_name": "PulsePlan", "monitoring_mode": "paused"},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def create_behavior(client: TestClient, project_id: str) -> dict[str, object]:
    response = client.post(
        f"/projects/{project_id}/behaviors",
        headers=headers(),
        json={
            "title": "Task can be completed",
            "description": "Create a task and mark it complete.",
            "expected_outcome": "The task remains visible and completed.",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("criticality", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_behavior_criticality_values_persist(tmp_path: Path, criticality: str) -> None:
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        project_id = connect(client, repository(tmp_path))
        response = client.post(
            f"/projects/{project_id}/behaviors",
            headers=headers(),
            json={
                "title": f"{criticality} behavior",
                "expected_outcome": "The expected result remains present.",
                "criticality": criticality,
            },
        )
        assert response.status_code == 200, response.text
        behavior = response.json()
        assert behavior["current_version"]["criticality"] == criticality


@pytest.mark.parametrize(
    "value,code",
    [
        ("https://127.0.0.1:8080", "RUNTIME_LOOPBACK_HTTP_REQUIRED"),
        ("http://example.com:8080", "RUNTIME_LOOPBACK_HTTP_REQUIRED"),
        ("http://127.0.0.1", "RUNTIME_EXPLICIT_PORT_REQUIRED"),
        ("http://localhost", "RUNTIME_EXPLICIT_PORT_REQUIRED"),
        ("file:///tmp/index.html", "RUNTIME_LOOPBACK_HTTP_REQUIRED"),
        ("http://user:secret@localhost:8080", "RUNTIME_URL_INVALID"),
    ],
)
def test_runtime_url_rejects_unsafe_targets(value: str, code: str) -> None:
    with pytest.raises(BehaviorServiceError, match=code):
        validate_loopback_runtime_url(value)


@pytest.mark.parametrize(
    "value,normalized,origin",
    [
        ("http://127.0.0.1:8080", "http://127.0.0.1:8080/", "http://127.0.0.1:8080"),
        ("http://localhost:4173/app", "http://localhost:4173/app", "http://localhost:4173"),
    ],
)
def test_runtime_url_accepts_explicit_loopback(value: str, normalized: str, origin: str) -> None:
    assert validate_loopback_runtime_url(value) == (normalized, origin)


def test_behavior_draft_and_edits_create_immutable_versions(tmp_path: Path) -> None:
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        project_id = connect(client, repository(tmp_path))
        first = create_behavior(client, project_id)
        assert first["lifecycle_state"] == "DRAFT"
        assert first["baselines"] == []
        assert first["current_version"]["version_number"] == 1
        response = client.post(
            f"/projects/{project_id}/behaviors/{first['id']}/versions",
            headers=headers(),
            json={
                "title": "Task completion stays visible",
                "description": "Edited description.",
                "expected_outcome": "Edited outcome.",
            },
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["current_version"]["version_number"] == 2
        assert [item["version_number"] for item in updated["versions"]] == [2, 1]
        assert updated["versions"][1]["title"] == "Task can be completed"


def test_archived_behavior_cannot_be_edited(tmp_path: Path) -> None:
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        project_id = connect(client, repository(tmp_path))
        behavior = create_behavior(client, project_id)
        archived = client.post(
            f"/projects/{project_id}/behaviors/{behavior['id']}/archive", headers=headers()
        )
        assert archived.json()["lifecycle_state"] == "ARCHIVED"
        edited = client.post(
            f"/projects/{project_id}/behaviors/{behavior['id']}/versions",
            headers=headers(),
            json={"title": "No", "description": "", "expected_outcome": ""},
        )
        assert edited.status_code == 409
        assert edited.json()["detail"] == "BEHAVIOR_ARCHIVED"


def test_runtime_configuration_is_project_scoped_and_idempotent(tmp_path: Path) -> None:
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        project_id = connect(client, repository(tmp_path))
        first = client.post(
            f"/projects/{project_id}/runtimes",
            headers=headers(),
            json={"display_name": "PulsePlan", "base_url": "http://127.0.0.1:8262/app"},
        ).json()
        second = client.post(
            f"/projects/{project_id}/runtimes",
            headers=headers(),
            json={"display_name": "PulsePlan local", "base_url": "http://127.0.0.1:8262/"},
        ).json()
        assert second["id"] == first["id"]
        listing = client.get(f"/projects/{project_id}/runtimes", headers=headers()).json()
        assert len(listing["runtimes"]) == 1
        assert listing["runtimes"][0]["allowed_origin"] == "http://127.0.0.1:8262"


def test_evidence_store_is_content_addressed_atomic_and_deduplicated(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    payload = b"immutable browser evidence"
    first = store.put(str(uuid.uuid4()), payload)
    project_id = first.object_key.split("/")[0]
    second = store.put(project_id, payload)
    assert first.sha256 == hashlib.sha256(payload).hexdigest()
    assert second.sha256 == first.sha256
    assert second.deduplicated is True
    assert store.read(project_id, first.sha256) == payload
    assert not list((tmp_path / "evidence").rglob(".evidence-*"))


def test_evidence_store_detects_tampering(tmp_path: Path) -> None:
    project_id = str(uuid.uuid4())
    store = EvidenceStore(tmp_path / "evidence")
    stored = store.put(project_id, b"original")
    path = tmp_path / "evidence" / stored.object_key
    path.write_bytes(b"tampered")
    with pytest.raises(EvidenceStoreError, match="EVIDENCE_OBJECT_HASH_MISMATCH"):
        store.read(project_id, stored.sha256)


@pytest.mark.parametrize("payload", [b"", b"x" * (10 * 1024 * 1024 + 1)])
def test_evidence_store_enforces_artifact_limits(tmp_path: Path, payload: bytes) -> None:
    store = EvidenceStore(tmp_path / "evidence")
    with pytest.raises(EvidenceStoreError, match="EVIDENCE_ARTIFACT_SIZE_INVALID"):
        store.put(str(uuid.uuid4()), payload)


def test_evidence_store_rejects_symlink_reads(tmp_path: Path) -> None:
    project_id = str(uuid.uuid4())
    store = EvidenceStore(tmp_path / "evidence")
    digest = hashlib.sha256(b"outside").hexdigest()
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    target = tmp_path / "evidence" / project_id / "objects" / digest[:2] / digest
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    with pytest.raises(EvidenceStoreError, match="EVIDENCE_OBJECT_NOT_FOUND"):
        store.read(project_id, digest)


def test_evidence_metadata_excludes_object_paths_and_secrets(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        artifact = app.state.runtime.evidence.add_artifact(
            project_id, b'{"url":"http://localhost:8262/task"}', "application/json"
        )
        public = client.get(
            f"/projects/{project_id}/evidence/artifacts/{artifact['id']}", headers=headers()
        ).json()
        assert "object_key" not in public
        assert TOKEN not in json.dumps(public)
        assert public["integrity_verified"] is True


def test_unreferenced_artifact_can_be_deleted(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        artifact = app.state.runtime.evidence.add_artifact(project_id, b"temporary", "text/plain")
        response = client.delete(
            f"/projects/{project_id}/evidence/artifacts/{artifact['id']}", headers=headers()
        )
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"


def test_interrupted_capture_is_recovered_as_stale_source(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    app = create_app(EngineSettings(data_root=data_root, session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        behavior = create_behavior(client, project_id)
        runtime = client.post(
            f"/projects/{project_id}/runtimes",
            headers=headers(),
            json={"display_name": "Interrupted", "base_url": "http://127.0.0.1:8262"},
        ).json()
        capture_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with app.state.runtime.database.sessions.begin() as session:
            session.add(
                BrowserCaptureSession(
                    id=capture_id,
                    project_id=project_id,
                    behavior_id=behavior["id"],
                    behavior_version_id=behavior["current_version_id"],
                    runtime_configuration_id=runtime["id"],
                    status="RECORDING",
                    entry_url=runtime["base_url"],
                    source_revision_json=json.dumps(behavior["current_version"]["source_revision"]),
                    started_at=now,
                    updated_at=now,
                )
            )
    restarted = create_app(EngineSettings(data_root=data_root, session_token=TOKEN))
    with TestClient(restarted) as client:
        recovered = client.get(
            f"/projects/{project_id}/captures/{capture_id}", headers=headers()
        ).json()
        assert recovered["status"] == "STALE_SOURCE"
        assert recovered["error_code"] == "ENGINE_RESTARTED_DURING_CAPTURE"


def test_real_playwright_pulseplan_capture_and_baseline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MELLOWYAK_BROWSER_HEADLESS", "1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), PulsePlanHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
        monkeypatch.setenv("MELLOWYAK_PHASE4_VALIDATION", "1")
        with TestClient(app) as client:
            project_id = connect(client, repository(tmp_path))
            behavior = create_behavior(client, project_id)
            base_url = f"http://127.0.0.1:{server.server_port}/"
            runtime = client.post(
                f"/projects/{project_id}/runtimes",
                headers=headers(),
                json={"display_name": "PulsePlan fixture", "base_url": base_url},
            ).json()
            started = client.post(
                f"/projects/{project_id}/captures",
                headers=headers(),
                json={
                    "behavior_id": behavior["id"],
                    "runtime_configuration_id": runtime["id"],
                },
            )
            assert started.status_code == 200, started.text
            capture_id = started.json()["id"]
            paused = client.post(
                f"/projects/{project_id}/captures/{capture_id}/pause", headers=headers()
            )
            assert paused.status_code == 200 and paused.json()["paused"] is True
            resumed = client.post(
                f"/projects/{project_id}/captures/{capture_id}/resume", headers=headers()
            )
            assert resumed.status_code == 200 and resumed.json()["paused"] is False
            fixture_result = client.post(
                f"/projects/{project_id}/captures/{capture_id}/validation-fixture-flow",
                headers=headers(),
            )
            assert fixture_result.status_code == 200, fixture_result.text
            stopped = client.post(
                f"/projects/{project_id}/captures/{capture_id}/stop", headers=headers()
            )
            assert stopped.status_code == 200, stopped.text
            capture = stopped.json()
            assert capture["status"] == "REVIEW_REQUIRED"
            assert {step["event_type"] for step in capture["steps"]} >= {"click", "submit"}
            serialized = json.dumps(capture)
            assert '"time":"14:00"' not in serialized
            assert "authorization" not in serialized.lower()
            reviewed = client.post(
                f"/projects/{project_id}/captures/{capture_id}/review",
                headers=headers(),
                json={
                    "step_updates": [
                        {"id": capture["steps"][0]["id"], "label": "Open event", "included": True}
                    ],
                    "excluded_observation_ids": [capture["observations"][0]["id"]],
                    "expected_assertions": [{"type": "TEXT_CONTAINS", "value": "14:00"}],
                },
            )
            assert reviewed.status_code == 200, reviewed.text
            assert reviewed.json()["steps"][0]["label"] == "Open event"
            assert reviewed.json()["observations"][0]["included"] is False
            accepted = client.post(
                f"/projects/{project_id}/captures/{capture_id}/accept-baseline",
                headers=headers(),
                json={"reviewer": "Local reviewer", "notes": "Reviewed local evidence."},
            )
            assert accepted.status_code == 200, accepted.text
            baseline = accepted.json()
            assert baseline["status"] == "ACCEPTED"
            protected = client.get(
                f"/projects/{project_id}/behaviors/{behavior['id']}", headers=headers()
            ).json()
            assert protected["lifecycle_state"] == "PROTECTED"
            bundle = client.get(
                f"/projects/{project_id}/evidence/bundles/{baseline['evidence_bundle_id']}",
                headers=headers(),
            ).json()
            assert bundle["status"] == "ACCEPTED"
            assert len(bundle["items"]) == 4
            assert {item["item_type"] for item in bundle["items"]} >= {
                "start_screenshot",
                "final_screenshot",
            }
            assert all(item["artifact"]["integrity_verified"] for item in bundle["items"])
            assert all(item["artifact"]["capture_id"] == capture_id for item in bundle["items"])
            referenced_id = bundle["items"][0]["artifact"]["id"]
            deletion = client.delete(
                f"/projects/{project_id}/evidence/artifacts/{referenced_id}", headers=headers()
            )
            assert deletion.status_code == 409
            assert deletion.json()["detail"] == "EVIDENCE_REFERENCED_BY_ACCEPTED_BASELINE"
            impact = client.get(
                f"/projects/{project_id}/impact/search?query=Task", headers=headers()
            ).json()
            behavior_nodes = [
                item for item in impact["results"] if item["node"]["type"] == "BEHAVIOR"
            ]
            assert behavior_nodes
            assert {link["provenance"] for link in behavior_nodes[0]["relationships"]} >= {
                "RUNTIME_OBSERVED"
            }
            revoked = client.post(
                f"/projects/{project_id}/behaviors/{behavior['id']}/baseline/revoke",
                headers=headers(),
                json={"confirmation": True, "delete_evidence": False},
            )
            assert revoked.status_code == 200 and revoked.json()["status"] == "REVOKED"
            draft_again = client.get(
                f"/projects/{project_id}/behaviors/{behavior['id']}", headers=headers()
            ).json()
            assert draft_again["lifecycle_state"] == "DRAFT"
            assert draft_again["last_accepted_baseline_id"] is None
    finally:
        server.shutdown()
        server.server_close()


def test_phase4_tables_do_not_store_binary_artifact_blobs(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with app.state.runtime.database.engine.connect() as connection:
        rows = connection.exec_driver_sql("PRAGMA table_info(evidence_artifacts)").fetchall()
    columns = {row[1] for row in rows}
    assert "content" not in columns
    assert "blob" not in columns
    assert {"sha256", "size_bytes", "media_type", "object_key"}.issubset(columns)
    app.state.runtime.browser.close()


def test_artifact_row_is_unique_per_project_and_hash(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        first = app.state.runtime.evidence.add_artifact(project_id, b"same", "text/plain")
        second = app.state.runtime.evidence.add_artifact(project_id, b"same", "text/plain")
        assert first["id"] == second["id"]
        with app.state.runtime.database.sessions() as session:
            rows = session.scalars(
                select(EvidenceArtifact).where(EvidenceArtifact.project_id == project_id)
            ).all()
            assert len(rows) == 1


def test_acceptance_requires_review_required_capture(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        with pytest.raises(EvidenceServiceError, match="CAPTURE_NOT_FOUND"):
            app.state.runtime.evidence.accept_baseline(
                project_id, str(uuid.uuid4()), "Reviewer", "Notes"
            )


def test_phase4_endpoints_require_session_token(tmp_path: Path) -> None:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    with TestClient(app) as client:
        project_id = connect(client, repository(tmp_path))
        assert client.get(f"/projects/{project_id}/behaviors").status_code == 401
        assert client.get(f"/projects/{project_id}/runtimes").status_code == 401
        assert client.get(f"/projects/{project_id}/captures").status_code == 401

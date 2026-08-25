from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-eight-test-token-that-is-long-enough-123456"


def authorized() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def create_demo(client: TestClient, parent: Path) -> dict[str, object]:
    response = client.post(
        "/demo-lab/create",
        headers=authorized(),
        json={"selected_parent": str(parent)},
    )
    assert response.status_code == 200
    return response.json()


def demo_action(client: TestClient, demo_id: str, action: str) -> dict[str, object]:
    response = client.post(f"/demo-lab/{demo_id}/{action}", headers=authorized(), json={})
    assert response.status_code == 200
    return response.json()


def test_product_self_test_reports_only_executed_passing_disposable_steps(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    with TestClient(create_app(EngineSettings(data_root=data_root, session_token=TOKEN))) as client:
        response = client.post("/self-test", headers=authorized(), json={})
        assert response.status_code == 200
        report = response.json()
        assert report["status"] == "PASS"
        statuses = {item["step"]: item["status"] for item in report["steps"]}
        assert statuses["database_migration"] == "PASS"
        assert statuses["known_good_probe"] == "PASS"
        assert statuses["confirmed_regression"] == "PASS"
        assert statuses["invalid_candidate_rejection"] == "PASS"
        assert statuses["valid_candidate_validation"] == "PASS"
        assert statuses["safe_apply"] == "PASS"
        assert statuses["post_apply_verification"] == "PASS"
        assert statuses["byte_equal_rollback"] == "PASS"
        assert statuses["journal_restart_load"] == "PASS"
        assert statuses["no_external_network"] == "PASS"
        assert statuses["no_orphan_processes"] == "PASS"
        assert statuses["cleanup"] == "PASS"
        export = client.post(
            f"/self-test/{report['id']}/export", headers=authorized(), json={}
        ).json()
        assert export["private_paths_included"] is False
        assert not any(path.name.startswith("mellowyak-self-test-") for path in tmp_path.iterdir())


def test_demo_lab_rejects_bad_candidate_commits_valid_apply_and_rolls_back(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    demo_parent = tmp_path / "demos"
    demo_parent.mkdir()
    with TestClient(create_app(EngineSettings(data_root=data_root, session_token=TOKEN))) as client:
        demo = create_demo(client, demo_parent)
        demo_id = str(demo["id"])
        demo_action(client, demo_id, "inject-regression")
        bad = demo_action(client, demo_id, "create-bad-candidate")
        assert bad["state"]["candidate_state"] == "VALIDATION_FAILED"
        valid = demo_action(client, demo_id, "create-valid-candidate")
        assert valid["state"]["candidate_state"] == "VALIDATED"
        applied = demo_action(client, demo_id, "apply-valid")
        assert applied["state"]["transaction_state"] == "COMMITTED"

        rollback_demo = create_demo(client, demo_parent)
        rollback_id = str(rollback_demo["id"])
        demo_action(client, rollback_id, "inject-regression")
        demo_action(client, rollback_id, "create-valid-candidate")
        live_path = demo_parent / f"MellowYak-Demo-{rollback_id[:8]}" / "checkout.py"
        before = live_path.read_bytes()
        rolled_back = demo_action(client, rollback_id, "simulate-post-apply-failure")
        assert rolled_back["state"]["transaction_state"] == "ROLLED_BACK"
        assert live_path.read_bytes() == before
        assert client.get("/recovery/pending", headers=authorized()).json() == {"transactions": []}


def test_demo_lab_stale_source_blocks_apply_without_writing(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    demo_parent = tmp_path / "demos"
    demo_parent.mkdir()
    with TestClient(create_app(EngineSettings(data_root=data_root, session_token=TOKEN))) as client:
        demo = create_demo(client, demo_parent)
        demo_id = str(demo["id"])
        demo_action(client, demo_id, "inject-regression")
        demo_action(client, demo_id, "create-valid-candidate")
        live_path = demo_parent / f"MellowYak-Demo-{demo_id[:8]}" / "checkout.py"
        external = b'def checkout():\n    return "external-change"\n'
        live_path.write_bytes(external)
        blocked = client.post(f"/demo-lab/{demo_id}/apply-valid", headers=authorized(), json={})
        assert blocked.status_code == 409
        assert live_path.read_bytes() == external


def test_demo_crash_route_is_disabled_without_explicit_test_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MELLOWYAK_DEMO_TEST_MODE", raising=False)
    with TestClient(
        create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    ) as client:
        response = client.post(
            "/demo-lab/not-a-demo/test-crash/after_first_file_operation",
            headers=authorized(),
            json={},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "DEMO_TEST_MODE_DISABLED"

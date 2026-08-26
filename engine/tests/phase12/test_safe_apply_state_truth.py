from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase12-safe-apply-session-token-that-is-long-enough"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _demo(client: TestClient, parent: Path) -> dict[str, object]:
    created = client.post(
        "/demo-lab/create",
        headers=_headers(),
        json={"selected_parent": str(parent)},
    )
    assert created.status_code == 200, created.text
    demo = created.json()
    regression = client.post(f"/demo-lab/{demo['id']}/inject-regression", headers=_headers())
    assert regression.status_code == 200, regression.text
    candidate = client.post(f"/demo-lab/{demo['id']}/create-valid-candidate", headers=_headers())
    assert candidate.status_code == 200, candidate.text
    return candidate.json()


def test_apply_waits_for_confirmation_before_snapshot_journal_or_write(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    parent = tmp_path / "disposable"
    parent.mkdir(parents=True)
    with TestClient(create_app(EngineSettings(data_root=data_root, session_token=TOKEN))) as client:
        demo = _demo(client, parent)
        state = demo["state"]
        prepared = client.post(
            f"/projects/{demo['project_id']}/repair-candidates/{state['candidate_id']}/apply/prepare",
            headers=_headers(),
            json={},
        )
        assert prepared.status_code == 200, prepared.text
        transaction = prepared.json()
        assert transaction["state"] == "AWAITING_CONFIRMATION"
        assert transaction["safety_snapshot_id"] is None
        assert transaction["journal_relative_path"] == ""
        assert all(item["operation_state"] == "PENDING" for item in transaction["files"])
        assert not list(data_root.glob("projects/*/apply-journals/*/journal.json"))

        confirmed = client.post(
            f"/projects/{demo['project_id']}/repair-candidates/{state['candidate_id']}/apply/confirm",
            headers=_headers(),
            json={
                "confirmation_nonce": transaction["confirmation_nonce"],
                "deliberate_confirmation": True,
            },
        )
        assert confirmed.status_code == 200, confirmed.text
        result = confirmed.json()
        assert result["state"] == "COMMITTED"
        assert result["safety_snapshot_id"]
        assert result["journal_relative_path"]
        transition_events = [item["event_type"] for item in result["events"]]
        assert transition_events.index("STATE_SAFETY_SNAPSHOT") < transition_events.index(
            "STATE_JOURNAL_CREATED"
        )
        assert transition_events.index("STATE_JOURNAL_CREATED") < transition_events.index(
            "STATE_WRITING"
        )
        assert transition_events.index("STATE_WRITING") < transition_events.index(
            "STATE_VERIFYING_LIVE"
        )
        assert transition_events.index("STATE_VERIFYING_LIVE") < transition_events.index(
            "STATE_COMMITTED"
        )


def test_failed_live_verification_rolls_back_with_transaction_evidence(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    parent = tmp_path / "disposable"
    parent.mkdir(parents=True)
    with TestClient(create_app(EngineSettings(data_root=data_root, session_token=TOKEN))) as client:
        demo = _demo(client, parent)
        rolled_back = client.post(
            f"/demo-lab/{demo['id']}/simulate-post-apply-failure", headers=_headers()
        )
        assert rolled_back.status_code == 200, rolled_back.text
        state = rolled_back.json()["state"]
        transaction = client.get(
            f"/projects/{demo['project_id']}/apply-transactions/{state['transaction_id']}",
            headers=_headers(),
        )
        assert transaction.status_code == 200, transaction.text
        result = transaction.json()
        evidence = result["rollback_evidence"]
        assert result["state"] == "ROLLED_BACK"
        assert evidence["transaction_id"] == result["id"]
        assert evidence["reason"] == "POST_APPLY_VERIFICATION_FAILED"
        assert evidence["paths_written"]
        assert evidence["paths_restored"] == evidence["paths_written"]
        assert evidence["byte_identity_result"] == "VERIFIED"
        assert evidence["unrelated_path_result"] == "OUTSIDE_TRANSACTION_SCOPE_UNTOUCHED_BY_ENGINE"
        assert evidence["candidate_state"] == "RETAINED_AFTER_ROLLBACK"
        assert evidence["pending_recovery"] is False

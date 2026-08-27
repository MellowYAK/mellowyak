from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.models import (
    BaselineAttestation,
    BehaviorBaseline,
    BehaviorVersion,
    BrowserCaptureSession,
    EvidenceArtifact,
    EvidenceBundle,
    EvidenceBundleItem,
    OrchestrationJob,
    OrchestrationRun,
    ProbeDefinition,
    ProbeRun,
    ProbeVersion,
    Project,
    ProtectedBehavior,
    RuntimeConfiguration,
    RuntimeProfile,
    RuntimeProfileVersion,
    SourceEpisode,
)
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-fifteen-session-token-12345678901234567890"
PROJECT_ID = "phase15-project"
BEHAVIOR_ID = "phase15-behavior"
BEHAVIOR_VERSION_ID = "phase15-behavior-version"
OLD_CAPTURE_ID = "phase15-old-capture"
NEW_CAPTURE_ID = "phase15-new-capture"
OLD_BUNDLE_ID = "phase15-old-bundle"
NEW_BUNDLE_ID = "phase15-new-bundle"
OLD_BASELINE_ID = "phase15-old-baseline"
RUNTIME_PROFILE_VERSION_ID = "phase15-runtime-version"
PROBE_ID = "phase15-probe"
PROBE_VERSION_ID = "phase15-probe-version"
PASS_RUN_ID = "phase15-pass-run"
SOURCE = {
    "branch": "product/intel-mac-product-lock",
    "head_sha": "a" * 40,
    "worktree_fingerprint": "b" * 64,
}


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def seeded_client(tmp_path: Path) -> tuple[TestClient, object]:
    app = create_app(EngineSettings(data_root=tmp_path / "data", session_token=TOKEN))
    runtime = app.state.runtime
    now = datetime.now(UTC)
    source = json.dumps(SOURCE, sort_keys=True)
    with runtime.database.sessions.begin() as session:
        session.add(
            Project(
                id=PROJECT_ID,
                installation_id=runtime.installation_id,
                display_name="Phase 15 local fixture",
                root_path=str(tmp_path / "source"),
                canonical_root_path=str(tmp_path / "source"),
                repository_root_path=str(tmp_path / "source"),
                current_branch=str(SOURCE["branch"]),
                current_head_sha=str(SOURCE["head_sha"]),
                current_worktree_fingerprint=str(SOURCE["worktree_fingerprint"]),
                detection_payload_json="{}",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            RuntimeConfiguration(
                id="phase15-browser-runtime",
                project_id=PROJECT_ID,
                display_name="Local browser",
                base_url="http://127.0.0.1:4173",
                allowed_origin="http://127.0.0.1:4173",
                starting_path="/",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ProtectedBehavior(
                id=BEHAVIOR_ID,
                project_id=PROJECT_ID,
                stable_key="checkout",
                display_name="Checkout remains protected",
                lifecycle_state="KNOWN_GOOD",
                current_version_id=BEHAVIOR_VERSION_ID,
                last_accepted_baseline_id=OLD_BASELINE_ID,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            BehaviorVersion(
                id=BEHAVIOR_VERSION_ID,
                behavior_id=BEHAVIOR_ID,
                project_id=PROJECT_ID,
                version_number=2,
                title="Checkout remains protected",
                description="Local fixture",
                expected_outcome="Checkout succeeds",
                content_digest="c" * 64,
                source_revision_json=source,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            RuntimeProfile(
                id="phase15-runtime",
                project_id=PROJECT_ID,
                display_name="Approved local runtime",
                current_version_id=RUNTIME_PROFILE_VERSION_ID,
                primary=True,
                status="CONFIGURED",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            RuntimeProfileVersion(
                id=RUNTIME_PROFILE_VERSION_ID,
                profile_id="phase15-runtime",
                project_id=PROJECT_ID,
                version_number=1,
                runtime_type="NODE",
                adapter_version="1",
                execution_mode="LOCAL_PROCESS",
                argv_json="[]",
                relative_working_directory=".",
                runtime_version="22",
                health_definition_json="{}",
                expected_ports_json="[]",
                test_definitions_json="[]",
                environment_schema_json="[]",
                network_policy="LOOPBACK_ONLY",
                limitations_json="[]",
                approved_at=now,
                detected_at=now,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            ProbeDefinition(
                id=PROBE_ID,
                project_id=PROJECT_ID,
                behavior_id=BEHAVIOR_ID,
                display_name="Checkout probe",
                probe_type="BROWSER_REPLAY",
                current_version_id=PROBE_VERSION_ID,
                status="CONFIGURED",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            ProbeVersion(
                id=PROBE_VERSION_ID,
                probe_id=PROBE_ID,
                project_id=PROJECT_ID,
                version_number=1,
                runtime_profile_version_id=RUNTIME_PROFILE_VERSION_ID,
                definition_json="{}",
                approved_at=now,
                created_at=now,
            )
        )
        session.flush()
        for capture_id, status in ((OLD_CAPTURE_ID, "ACCEPTED"), (NEW_CAPTURE_ID, "VALIDATED")):
            session.add(
                BrowserCaptureSession(
                    id=capture_id,
                    project_id=PROJECT_ID,
                    behavior_id=BEHAVIOR_ID,
                    behavior_version_id=BEHAVIOR_VERSION_ID,
                    runtime_configuration_id="phase15-browser-runtime",
                    status=status,
                    entry_url="http://127.0.0.1:4173/checkout",
                    source_revision_json=source,
                    started_at=now,
                    stopped_at=now,
                    updated_at=now,
                    runtime_identity_json="{}",
                    expected_assertions_json="[]",
                )
            )
        session.flush()
        session.add(
            ProbeRun(
                id=PASS_RUN_ID,
                project_id=PROJECT_ID,
                probe_id=PROBE_ID,
                probe_version_id=PROBE_VERSION_ID,
                snapshot_id="phase15-snapshot",
                runtime_profile_version_id=RUNTIME_PROFILE_VERSION_ID,
                source_identity_json=source,
                status="COMPLETED",
                result="PASS",
                attempt_count=1,
                expected_json="{}",
                observed_json="{}",
                evidence_json="{}",
                limitations_json="[]",
                reproducible=True,
                started_at=now,
                completed_at=now,
            )
        )
        session.flush()
        for bundle_id, capture_id, verification_run_id in (
            (OLD_BUNDLE_ID, OLD_CAPTURE_ID, None),
            (NEW_BUNDLE_ID, NEW_CAPTURE_ID, PASS_RUN_ID),
        ):
            session.add(
                EvidenceBundle(
                    id=bundle_id,
                    project_id=PROJECT_ID,
                    capture_id=capture_id,
                    manifest_sha256=("d" if capture_id == OLD_CAPTURE_ID else "e") * 64,
                    status="ACCEPTED" if capture_id == OLD_CAPTURE_ID else "VALIDATED",
                    verification_run_id=verification_run_id,
                    created_at=now,
                )
            )
        session.flush()
        session.add(
            EvidenceArtifact(
                id="phase15-artifact",
                project_id=PROJECT_ID,
                sha256="f" * 64,
                size_bytes=12,
                media_type="application/json",
                object_key="objects/redacted-evidence",
                redaction_state="SAFE",
                capture_id=NEW_CAPTURE_ID,
                behavior_id=BEHAVIOR_ID,
                behavior_version_id=BEHAVIOR_VERSION_ID,
                source_identity_json=source,
                runtime_identity_json="{}",
                created_at=now,
            )
        )
        session.flush()
        session.add(
            EvidenceBundleItem(
                id="phase15-bundle-item",
                bundle_id=NEW_BUNDLE_ID,
                artifact_id="phase15-artifact",
                ordinal=1,
                item_type="ASSERTION",
            )
        )
        session.add(
            BaselineAttestation(
                id="phase15-old-attestation",
                project_id=PROJECT_ID,
                capture_id=OLD_CAPTURE_ID,
                status="ACCEPTED",
                reviewer="Local operator",
                notes="Initial Known Good",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            BehaviorBaseline(
                id=OLD_BASELINE_ID,
                project_id=PROJECT_ID,
                behavior_id=BEHAVIOR_ID,
                behavior_version_id=BEHAVIOR_VERSION_ID,
                evidence_bundle_id=OLD_BUNDLE_ID,
                attestation_id="phase15-old-attestation",
                status="ACCEPTED",
                source_revision_json=source,
                created_at=now,
            )
        )
    return TestClient(app), runtime


def test_known_good_requires_deliberate_verified_promotion(tmp_path: Path) -> None:
    client, runtime = seeded_client(tmp_path)
    base = f"/projects/{PROJECT_ID}/behaviors/{BEHAVIOR_ID}"

    lineage = client.get(f"{base}/known-good-lineage", headers=headers()).json()
    assert lineage["current_baseline_id"] == OLD_BASELINE_ID
    assert lineage["baselines"][0]["limitations"] == ["LEGACY_LINEAGE_ROOT"]

    bypass = client.post(
        f"/projects/{PROJECT_ID}/captures/{NEW_CAPTURE_ID}/accept-baseline",
        headers=headers(),
        json={"reviewer": "Local operator", "notes": "Must not bypass"},
    )
    assert bypass.status_code == 409
    assert bypass.json()["detail"] == "BASELINE_PROMOTION_REQUIRES_EXPECTED_CHANGE"

    missing_reason = client.post(
        f"{base}/change-decision",
        headers=headers(),
        json={"decision": "EXPECTED", "reason": ""},
    )
    assert missing_reason.status_code == 400

    stale_decision = client.post(
        f"{base}/change-decision",
        headers=headers(),
        json={"decision": "EXPECTED", "reason": "Approved product change"},
    ).json()
    with runtime.database.sessions.begin() as session:
        session.get(Project, PROJECT_ID).current_head_sha = "9" * 40
    stale = client.post(
        f"{base}/expected-change/reverify",
        headers=headers(),
        json={"decision_id": stale_decision["id"], "capture_id": NEW_CAPTURE_ID},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "PROMOTION_SOURCE_STALE"
    stale_lineage = client.get(f"{base}/known-good-lineage", headers=headers()).json()
    assert stale_lineage["active_decision"]["state"] == "PROMOTION_BLOCKED_STALE_SOURCE"

    with runtime.database.sessions.begin() as session:
        session.get(Project, PROJECT_ID).current_head_sha = str(SOURCE["head_sha"])
    decision = client.post(
        f"{base}/change-decision",
        headers=headers(),
        json={"decision": "EXPECTED", "reason": "Approved product change"},
    ).json()
    verified = client.post(
        f"{base}/expected-change/reverify",
        headers=headers(),
        json={"decision_id": decision["id"], "capture_id": NEW_CAPTURE_ID},
    )
    assert verified.status_code == 200
    verified_body = verified.json()
    assert verified_body["state"] == "PROMOTION_AWAITING_CONFIRMATION"
    assert verified_body["confirmation_nonce"]

    not_deliberate = client.post(
        f"{base}/known-good/promote",
        headers=headers(),
        json={
            "decision_id": decision["id"],
            "confirmation_nonce": verified_body["confirmation_nonce"],
            "deliberate_confirmation": False,
            "reviewer": "Local operator",
            "notes": "Reviewed",
        },
    )
    assert not_deliberate.status_code == 400

    promoted = client.post(
        f"{base}/known-good/promote",
        headers=headers(),
        json={
            "decision_id": decision["id"],
            "confirmation_nonce": verified_body["confirmation_nonce"],
            "deliberate_confirmation": True,
            "reviewer": "Local operator",
            "notes": "Reviewed",
        },
    )
    assert promoted.status_code == 200
    promoted_body = promoted.json()
    assert promoted_body["current_baseline_id"] != OLD_BASELINE_ID
    assert len(promoted_body["baselines"]) == 2
    old = next(item for item in promoted_body["baselines"] if item["id"] == OLD_BASELINE_ID)
    current = next(item for item in promoted_body["baselines"] if item["current"])
    assert old["status"] == "SUPERSEDED"
    assert current["supersedes_baseline_id"] == OLD_BASELINE_ID
    assert current["promotion_reason"] == "Approved product change"

    replay = client.post(
        f"{base}/known-good/promote",
        headers=headers(),
        json={
            "decision_id": decision["id"],
            "confirmation_nonce": verified_body["confirmation_nonce"],
            "deliberate_confirmation": True,
            "reviewer": "Local operator",
            "notes": "Replay must fail",
        },
    )
    assert replay.status_code == 409
    assert replay.json()["detail"] == "PROMOTION_CONFIRMATION_ALREADY_USED"


def test_yak_receipt_is_episode_bound_idempotent_and_path_free(tmp_path: Path) -> None:
    client, runtime = seeded_client(tmp_path)
    now = datetime.now(UTC)
    episode_id = "phase15-episode"
    orchestration_id = "phase15-orchestration"
    receipt_run_id = "phase15-receipt-pass-run"
    with runtime.database.sessions.begin() as session:
        session.add(
            SourceEpisode(
                id=episode_id,
                project_id=PROJECT_ID,
                started_at=now,
                ended_at=now,
                event_count=1,
                resulting_snapshot_id="phase15-resulting-snapshot",
                git_anchor_json="{}",
                status="STABILIZED",
            )
        )
        session.flush()
        session.add(
            ProbeRun(
                id=receipt_run_id,
                project_id=PROJECT_ID,
                probe_id=PROBE_ID,
                probe_version_id=PROBE_VERSION_ID,
                snapshot_id="phase15-resulting-snapshot",
                episode_id=episode_id,
                runtime_profile_version_id=RUNTIME_PROFILE_VERSION_ID,
                source_identity_json=json.dumps(SOURCE, sort_keys=True),
                status="COMPLETED",
                result="PASS",
                attempt_count=1,
                expected_json="{}",
                observed_json="{}",
                evidence_json="{}",
                limitations_json="[]",
                reproducible=True,
                started_at=now,
                completed_at=now,
            )
        )
        session.add(
            OrchestrationRun(
                id=orchestration_id,
                project_id=PROJECT_ID,
                episode_id=episode_id,
                resulting_snapshot_id="phase15-resulting-snapshot",
                source_identity_json=json.dumps(SOURCE, sort_keys=True),
                selected_behaviors_json=json.dumps([{"behavior_id": BEHAVIOR_ID}]),
                omitted_behaviors_json=json.dumps(
                    [{"behavior_id": "omitted-behavior", "reason": "BUDGET_DEFERRED"}]
                ),
                selected_probe_versions_json=json.dumps([PROBE_VERSION_ID]),
                state="COMPLETED",
                terminal_status="COMPLETE",
                created_at=now,
                updated_at=now,
                completed_at=now,
            )
        )
        session.flush()
        session.add(
            OrchestrationJob(
                id="phase15-job",
                orchestration_run_id=orchestration_id,
                project_id=PROJECT_ID,
                behavior_id=BEHAVIOR_ID,
                probe_id=PROBE_ID,
                probe_version_id=PROBE_VERSION_ID,
                runtime_profile_version_id=RUNTIME_PROFILE_VERSION_ID,
                snapshot_id="phase15-resulting-snapshot",
                source_identity_digest="8" * 64,
                state="COMPLETED",
                reason_code="IMPACT_SELECTED",
                probe_run_id=receipt_run_id,
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=now,
            )
        )

    path = f"/projects/{PROJECT_ID}/episodes/{episode_id}/yak-receipt"
    first = client.post(path, headers=headers())
    assert first.status_code == 200
    body = first.json()
    assert body["payload"]["protected_behaviors_considered"] == 2
    assert body["payload"]["checked"] == 1
    assert body["payload"]["passed"] == 1
    assert body["payload"]["omitted"] == 1
    assert body["payload"]["unknown"] == 1
    assert body["payload"]["source_modified_by_yak"] is False
    rendered = json.dumps(body, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "/Users/" not in rendered

    with runtime.database.sessions.begin() as session:
        session.get(ProbeRun, receipt_run_id).result = "FAIL"
    second = client.post(path, headers=headers())
    assert second.status_code == 200
    assert second.json()["id"] == body["id"]
    assert second.json()["digest"] == body["digest"]
    assert second.json()["payload"]["passed"] == 1

    listed = client.get(f"/projects/{PROJECT_ID}/yak-receipts", headers=headers())
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["receipts"]] == [body["id"]]

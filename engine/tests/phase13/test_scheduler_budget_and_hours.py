from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.db.models import (
    OrchestrationJob,
    OrchestrationJobAttempt,
    OrchestrationRun,
    ProbeDefinition,
    ProbeVersion,
    Project,
    ProtectedBehavior,
    SnapshotMilestone,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.noise_control.service import NoiseControlService
from mellowyak_engine.scheduling.policy import MonitoringPolicyService, _hours_status
from mellowyak_engine.scheduling.service import SchedulerService
from mellowyak_engine.storage.paths import StoragePaths


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def _seed(tmp_path: Path, clock: MutableClock) -> SimpleNamespace:
    database = LocalDatabase(StoragePaths.create(tmp_path / "data"))
    assert database.migrate() == "0011_baseline_lock_and_local_proof"
    events = LocalEventBus()
    project_id = str(uuid.uuid4())
    behavior_id = str(uuid.uuid4())
    probe_id = str(uuid.uuid4())
    probe_version_id = str(uuid.uuid4())
    snapshot_id = "a" * 64
    now = clock.value
    with database.sessions.begin() as session:
        session.add(
            Project(
                id=project_id,
                display_name="Scheduler fixture",
                root_path=str(tmp_path / "project"),
                canonical_root_path=str(tmp_path / "project"),
                repository_root_path=str(tmp_path / "project"),
                created_at=now,
                updated_at=now,
                monitoring_mode="passive",
                monitoring_status="active",
                detection_payload_json="{}",
            )
        )
        session.flush()
        session.add(
            ProtectedBehavior(
                id=behavior_id,
                project_id=project_id,
                stable_key="fixture",
                display_name="Fixture behavior",
                lifecycle_state="ACTIVE",
                current_version_id=str(uuid.uuid4()),
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            SourceSnapshot(
                id=snapshot_id,
                project_id=project_id,
                manifest_digest=snapshot_id,
                creation_reason="TEST",
                source_identity_json=json.dumps({"manifest_digest": snapshot_id}),
                created_at=now,
            )
        )
        session.flush()
        session.add(
            ProbeDefinition(
                id=probe_id,
                project_id=project_id,
                behavior_id=behavior_id,
                display_name="Fixture probe",
                probe_type="TEST",
                current_version_id=probe_version_id,
                status="CONFIGURED",
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            ProbeVersion(
                id=probe_version_id,
                probe_id=probe_id,
                project_id=project_id,
                version_number=1,
                definition_json='{"argv":[],"executable":"true"}',
                timeout_seconds=20,
                approved_at=now,
                created_at=now,
            )
        )
        session.flush()
        session.add(
            SnapshotMilestone(
                id=str(uuid.uuid4()),
                project_id=project_id,
                snapshot_id=snapshot_id,
                display_name="Known good",
                behavior_id=behavior_id,
                probe_version_id=probe_version_id,
                status="ACCEPTED",
                human_attested=True,
                created_at=now,
            )
        )
    policies = MonitoringPolicyService(database.sessions, events, clock=clock)
    policies.update_global(
        {
            "automatic_checking_enabled": True,
            "daily_runtime_budget_seconds": 60,
        }
    )
    policies.update_project(
        project_id,
        {
            "mode": "AUTO_SAFE",
            "resource_budget": {"max_concurrent": 1, "daily_runtime_budget_seconds": 60},
        },
    )
    policies.update_behavior(project_id, behavior_id, {"mode": "AUTOMATIC"})
    return SimpleNamespace(
        database=database,
        events=events,
        policies=policies,
        project_id=project_id,
        behavior_id=behavior_id,
        probe_id=probe_id,
        probe_version_id=probe_version_id,
        snapshot_id=snapshot_id,
    )


def _job(fixture: SimpleNamespace, *, state: str, started_at: datetime) -> str:
    episode_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    completed_at = started_at + timedelta(seconds=50) if state == "COMPLETED" else None
    with fixture.database.sessions.begin() as session:
        session.add(
            SourceEpisode(
                id=episode_id,
                project_id=fixture.project_id,
                started_at=started_at,
                ended_at=completed_at,
                resulting_snapshot_id=fixture.snapshot_id,
                status="STABILIZED",
            )
        )
        session.flush()
        session.add(
            OrchestrationRun(
                id=run_id,
                project_id=fixture.project_id,
                episode_id=episode_id,
                resulting_snapshot_id=fixture.snapshot_id,
                source_identity_json=json.dumps({"manifest_digest": fixture.snapshot_id}),
                state="PAUSED" if state == "DEFERRED" else "RUNNING",
                created_at=started_at,
                updated_at=started_at,
            )
        )
        session.flush()
        session.add(
            OrchestrationJob(
                id=job_id,
                orchestration_run_id=run_id,
                project_id=fixture.project_id,
                behavior_id=fixture.behavior_id,
                probe_id=fixture.probe_id,
                probe_version_id=fixture.probe_version_id,
                snapshot_id=fixture.snapshot_id,
                source_identity_digest=fixture.snapshot_id,
                priority=70,
                state=state,
                reason_code="TEST",
                defer_reason="OUTSIDE_ALLOWED_HOURS" if state == "DEFERRED" else None,
                created_at=started_at,
                updated_at=completed_at or started_at,
                started_at=started_at if state in {"RUNNING", "COMPLETED"} else None,
                completed_at=completed_at,
            )
        )
    return job_id


def _version(fixture: SimpleNamespace) -> ProbeVersion:
    with fixture.database.sessions() as session:
        return session.get(ProbeVersion, fixture.probe_version_id)


def _scheduler(fixture: SimpleNamespace) -> SchedulerService:
    unused = SimpleNamespace()
    return SchedulerService(
        fixture.database.sessions,
        fixture.events,
        unused,
        unused,
        unused,
        fixture.policies,
        str(uuid.uuid4()),
        worker_count=1,
        clock=fixture.policies._clock,
    )


def test_daily_budget_uses_persisted_duration_and_resets_at_local_day(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    _job(fixture, state="COMPLETED", started_at=clock.value - timedelta(seconds=50))

    exhausted = fixture.policies.eligibility(
        fixture.project_id, fixture.behavior_id, _version(fixture), "TEST"
    )
    assert exhausted["deferred"] is True
    assert "DAILY_RUNTIME_BUDGET_EXHAUSTED" in exhausted["reason_codes"]
    assert exhausted["runtime_budget"]["project_consumed_seconds"] == 50.0

    clock.value += timedelta(days=1)
    reset = fixture.policies.eligibility(
        fixture.project_id, fixture.behavior_id, _version(fixture), "TEST"
    )
    assert reset["eligible"] is True
    assert reset["runtime_budget"]["project_consumed_seconds"] == 0.0


def test_allowed_hours_reports_next_time_and_supports_overnight_and_dst() -> None:
    outside = _hours_status(
        datetime(2026, 8, 24, 6, 0, tzinfo=UTC),
        {
            "timezone": "Asia/Jerusalem",
            "weekdays": [0],
            "start": "10:00",
            "end": "17:00",
        },
    )
    assert outside["allowed"] is False
    assert outside["next_eligible_at"] == "2026-08-24T07:00:00+00:00"

    overnight = _hours_status(
        datetime(2026, 8, 21, 22, 30, tzinfo=UTC),
        {
            "timezone": "UTC",
            "weekdays": [4],
            "start": "22:00",
            "end": "02:00",
        },
    )
    assert overnight["allowed"] is True

    dst_gap = _hours_status(
        datetime(2026, 3, 8, 6, 0, tzinfo=UTC),
        {
            "timezone": "America/New_York",
            "weekdays": [6],
            "start": "02:30",
            "end": "04:00",
        },
    )
    assert dst_gap["allowed"] is False
    assert dst_gap["next_eligible_at"] == "2026-03-08T07:00:00+00:00"


def test_restart_accounts_interrupted_runtime_without_double_counting(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    job_id = _job(fixture, state="RUNNING", started_at=clock.value - timedelta(seconds=50))

    recovered = _scheduler(fixture).recover()
    assert recovered == {"recovered": 1, "stale": 0, "interrupted": 1}
    with fixture.database.sessions() as session:
        job = session.get(OrchestrationJob, job_id)
        attempt = session.scalar(
            select(OrchestrationJobAttempt).where(OrchestrationJobAttempt.job_id == job_id)
        )
        assert job is not None and job.state == "QUEUED" and job.started_at is None
        assert attempt is not None and attempt.reason == "ENGINE_RESTART_INTERRUPTED"

    exhausted = fixture.policies.eligibility(
        fixture.project_id, fixture.behavior_id, _version(fixture), "TEST"
    )
    assert exhausted["runtime_budget"]["project_consumed_seconds"] == 50.0
    assert "DAILY_RUNTIME_BUDGET_EXHAUSTED" in exhausted["reason_codes"]


def test_run_now_is_one_job_source_bound_bounded_and_durably_audited(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 20, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    fixture.policies.update_project(
        fixture.project_id,
        {
            "allowed_hours": {
                "timezone": "UTC",
                "weekdays": [2],
                "start": "09:00",
                "end": "17:00",
            }
        },
    )
    job_id = _job(fixture, state="DEFERRED", started_at=clock.value)

    result = _scheduler(fixture).run_now(fixture.project_id)
    assert result == {"status": "QUEUED_SOURCE_BOUND_OVERRIDE", "resumed_count": 1}
    with fixture.database.sessions() as session:
        job = session.get(OrchestrationJob, job_id)
        run = session.get(OrchestrationRun, job.orchestration_run_id if job else "")
        assert job is not None and job.state == "QUEUED"
        assert job.reason_code == "USER_RUN_NOW_OVERRIDE"
        assert run is not None
        audit = json.loads(run.scheduler_budget_json)["run_now_overrides"][0]
        assert audit["source_identity_digest"] == fixture.snapshot_id
        assert audit["bounded_seconds"] == 20
        assert audit["source_identity_rechecked"] is True


def test_flaky_classification_and_incident_dedup_survive_service_restart(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    noise = NoiseControlService(fixture.database.sessions)
    attempts = [
        {"result": "FAIL", "observed": {"code": 1}},
        {"result": "PASS", "observed": {"code": 0}},
    ]
    first_flaky = noise.classify_attempts(
        fixture.project_id,
        fixture.probe_id,
        fixture.snapshot_id,
        attempts,
        quarantine_threshold=2,
    )
    second_flaky = NoiseControlService(fixture.database.sessions).classify_attempts(
        fixture.project_id,
        fixture.probe_id,
        fixture.snapshot_id,
        attempts,
        quarantine_threshold=2,
    )
    assert first_flaky == {
        "classification": "FLAKY",
        "quarantined": False,
        "consecutive_flaky_count": 1,
    }
    assert second_flaky == {
        "classification": "FLAKY",
        "quarantined": True,
        "consecutive_flaky_count": 2,
    }

    first_incident = noise.record_incident(
        project_id=fixture.project_id,
        behavior_id=fixture.behavior_id,
        baseline_identity="known-good",
        source_identity_digest=fixture.snapshot_id,
        category="CONFIRMED",
        alert_id="alert-one",
        delivery_status="PERSISTED",
    )
    second_incident = NoiseControlService(fixture.database.sessions).record_incident(
        project_id=fixture.project_id,
        behavior_id=fixture.behavior_id,
        baseline_identity="known-good",
        source_identity_digest=fixture.snapshot_id,
        category="CONFIRMED",
        alert_id="alert-two",
        delivery_status="DELIVERED",
    )
    assert first_incident["deduplication_key"] == second_incident["deduplication_key"]
    assert second_incident["occurrence_count"] == 2
    assert second_incident["delivery_status"] == "DELIVERED"


def test_queue_deduplicates_current_work_and_marks_older_source_stale(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 12, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    old_job_id = _job(fixture, state="DEFERRED", started_at=clock.value)
    newer_digest = "b" * 64
    with fixture.database.sessions.begin() as session:
        old_job = session.get(OrchestrationJob, old_job_id)
        assert old_job is not None
        run_id = old_job.orchestration_run_id
        session.add(
            SourceSnapshot(
                id=newer_digest,
                project_id=fixture.project_id,
                manifest_digest=newer_digest,
                creation_reason="TEST",
                source_identity_json=json.dumps({"manifest_digest": newer_digest}),
                created_at=clock.value + timedelta(seconds=1),
            )
        )
    scheduler = _scheduler(fixture)
    values = {
        "orchestration_run_id": run_id,
        "project_id": fixture.project_id,
        "behavior_id": fixture.behavior_id,
        "probe_id": fixture.probe_id,
        "probe_version_id": fixture.probe_version_id,
        "runtime_profile_version_id": None,
        "snapshot_id": newer_digest,
        "source_identity_digest": newer_digest,
        "priority": 70,
        "reason_code": "CURRENT_SOURCE",
    }
    first = scheduler.enqueue(**values)
    duplicate = scheduler.enqueue(**values)
    assert first["id"] == duplicate["id"]
    with fixture.database.sessions() as session:
        old_job = session.get(OrchestrationJob, old_job_id)
        assert old_job is not None and old_job.state == "STALE"
        assert old_job.defer_reason == "SUPERSEDED_BY_NEW_EPISODE"


def test_worker_rechecks_policy_before_claiming_queued_work(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 8, 26, 10, 0, tzinfo=UTC))
    fixture = _seed(tmp_path, clock)
    fixture.policies.update_project(
        fixture.project_id,
        {
            "allowed_hours": {
                "timezone": "UTC",
                "weekdays": [2],
                "start": "09:00",
                "end": "17:00",
            }
        },
    )
    job_id = _job(fixture, state="QUEUED", started_at=clock.value)
    clock.value = datetime(2026, 8, 26, 20, 0, tzinfo=UTC)

    assert _scheduler(fixture)._claim() is None
    with fixture.database.sessions() as session:
        job = session.get(OrchestrationJob, job_id)
        assert job is not None and job.state == "DEFERRED"
        assert job.defer_reason == "OUTSIDE_ALLOWED_HOURS"

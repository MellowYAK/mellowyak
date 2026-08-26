from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    OrchestrationJob,
    OrchestrationJobAttempt,
    OrchestrationRun,
    SchedulerRecoveryRecord,
    SourceSnapshot,
)


def _now() -> datetime:
    return datetime.now(UTC)


class SchedulerService:
    """SQLite-backed fair queue with bounded worker and project concurrency."""

    TERMINAL = frozenset({"COMPLETED", "FAILED", "STALE", "CANCELLED", "BLOCKED"})

    def __init__(
        self,
        sessions: sessionmaker[Session],
        events: LocalEventBus,
        probes: Any,
        impact_memory: Any,
        noise_control: Any,
        engine_run_id: str,
        worker_count: int = 2,
    ) -> None:
        self.sessions = sessions
        self.events = events
        self.probes = probes
        self.impact_memory = impact_memory
        self.noise_control = noise_control
        self.engine_run_id = engine_run_id
        self.worker_count = max(1, min(worker_count, 2))
        self._stop = threading.Event()
        self._wake = threading.Condition()
        self._active_projects: set[str] = set()
        self._active_lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    @staticmethod
    def _public(row: OrchestrationJob) -> dict[str, Any]:
        return {
            "id": row.id,
            "orchestration_run_id": row.orchestration_run_id,
            "project_id": row.project_id,
            "behavior_id": row.behavior_id,
            "probe_id": row.probe_id,
            "probe_version_id": row.probe_version_id,
            "runtime_profile_version_id": row.runtime_profile_version_id,
            "snapshot_id": row.snapshot_id,
            "source_identity_digest": row.source_identity_digest,
            "priority": row.priority,
            "job_type": row.job_type,
            "idempotence": row.idempotence,
            "state": row.state,
            "reason_code": row.reason_code,
            "defer_reason": row.defer_reason,
            "probe_run_id": row.probe_run_id,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }

    def enqueue(
        self,
        *,
        orchestration_run_id: str,
        project_id: str,
        behavior_id: str | None,
        probe_id: str,
        probe_version_id: str,
        runtime_profile_version_id: str | None,
        snapshot_id: str,
        source_identity_digest: str,
        priority: int,
        reason_code: str,
        deferred: bool = False,
        defer_reason: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        job = OrchestrationJob(
            id=str(uuid.uuid4()),
            orchestration_run_id=orchestration_run_id,
            project_id=project_id,
            behavior_id=behavior_id,
            probe_id=probe_id,
            probe_version_id=probe_version_id,
            runtime_profile_version_id=runtime_profile_version_id,
            snapshot_id=snapshot_id,
            source_identity_digest=source_identity_digest,
            priority=max(1, min(priority, 100)),
            job_type="PROBE",
            idempotence="SAFE",
            state="DEFERRED" if deferred else "QUEUED",
            reason_code=reason_code,
            defer_reason=defer_reason,
            created_at=now,
            updated_at=now,
        )
        try:
            with self.sessions.begin() as session:
                older = session.scalars(
                    select(OrchestrationJob).where(
                        OrchestrationJob.project_id == project_id,
                        OrchestrationJob.state.in_(["QUEUED", "DEFERRED"]),
                        OrchestrationJob.source_identity_digest != source_identity_digest,
                    )
                ).all()
                for item in older:
                    item.state = "STALE"
                    item.defer_reason = "SUPERSEDED_BY_NEW_EPISODE"
                    item.updated_at = now
                    item.completed_at = now
                session.add(job)
                session.flush()
                value = self._public(job)
        except IntegrityError:
            with self.sessions() as session:
                existing = session.scalars(
                    select(OrchestrationJob).where(
                        OrchestrationJob.probe_version_id == probe_version_id,
                        OrchestrationJob.source_identity_digest == source_identity_digest,
                    )
                ).one()
                return self._public(existing)
        self.events.publish(
            "orchestration_deferred" if deferred else "orchestration_queued",
            project_id,
            {"job_id": value["id"], "reason_code": reason_code},
        )
        with self._wake:
            self._wake.notify_all()
        return value

    def start(self) -> None:
        if self._threads:
            return
        for index in range(self.worker_count):
            thread = threading.Thread(
                target=self._worker, name=f"mellowyak-sentinel-{index + 1}", daemon=True
            )
            self._threads.append(thread)
            thread.start()

    def _claim(self) -> dict[str, Any] | None:
        with self.sessions.begin() as session:
            candidates = session.scalars(
                select(OrchestrationJob)
                .where(OrchestrationJob.state == "QUEUED")
                .order_by(OrchestrationJob.priority.desc(), OrchestrationJob.created_at)
                .limit(50)
            ).all()
            for row in candidates:
                with self._active_lock:
                    if row.project_id in self._active_projects:
                        continue
                    self._active_projects.add(row.project_id)
                row.state = "RUNNING"
                row.started_at = _now()
                row.updated_at = row.started_at
                session.flush()
                return self._public(row)
        return None

    def _worker(self) -> None:
        while not self._stop.is_set():
            job = self._claim()
            if job is None:
                with self._wake:
                    self._wake.wait(timeout=1.0)
                continue
            try:
                self._execute(job)
            finally:
                with self._active_lock:
                    self._active_projects.discard(str(job["project_id"]))

    def _execute(self, job: dict[str, Any]) -> None:
        project_id = str(job["project_id"])
        with self.sessions() as session:
            latest = session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.project_id == project_id)
                .order_by(SourceSnapshot.created_at.desc())
                .limit(1)
            ).first()
        if latest is None or latest.manifest_digest != job["source_identity_digest"]:
            self._finish(str(job["id"]), "STALE", "SOURCE_IDENTITY_SUPERSEDED", None)
            self.events.publish("orchestration_job_stale", project_id, {"job_id": job["id"]})
            return
        self.events.publish(
            "automatic_probe_running",
            project_id,
            {"job_id": job["id"], "probe_id": job["probe_id"]},
        )
        started = _now()
        try:
            result = self.probes.run(project_id, str(job["probe_id"]), str(job["snapshot_id"]))
        except Exception as error:
            self._finish(str(job["id"]), "FAILED", type(error).__name__[:120], None)
            self.events.publish(
                "automatic_probe_failed",
                project_id,
                {"job_id": job["id"], "error_code": type(error).__name__[:80]},
            )
            return
        attempts = list(result.get("observed", {}).get("attempts", []))
        classification = self.noise_control.classify_attempts(
            project_id,
            str(job["probe_id"]),
            str(job["source_identity_digest"]),
            attempts or [{"result": result["result"], "observed": result.get("observed", {})}],
        )
        completed = _now()
        with self.sessions.begin() as session:
            for number, attempt in enumerate(attempts or [{"result": result["result"]}], start=1):
                session.add(
                    OrchestrationJobAttempt(
                        id=str(uuid.uuid4()),
                        job_id=str(job["id"]),
                        project_id=project_id,
                        attempt_number=number,
                        reason="AUTOMATIC_EPISODE_SELECTION",
                        result=str(attempt.get("result", "INCONCLUSIVE")),
                        classification=str(classification["classification"]),
                        details_json=json.dumps(attempt, sort_keys=True),
                        started_at=started,
                        completed_at=completed,
                    )
                )
        self.impact_memory.record_result(
            project_id,
            job.get("behavior_id"),
            str(job["source_identity_digest"]),
            str(result["id"]),
            str(result["result"]),
        )
        if classification["classification"] == "CONFIRMED":
            self.noise_control.record_incident(
                project_id=project_id,
                behavior_id=job.get("behavior_id"),
                baseline_identity=None,
                source_identity_digest=str(job["source_identity_digest"]),
                category="CONFIRMED",
                alert_id=None,
                delivery_status="PERSISTED",
            )
        self._finish(
            str(job["id"]), "COMPLETED", str(classification["classification"]), str(result["id"])
        )
        self.events.publish(
            "automatic_probe_completed",
            project_id,
            {
                "job_id": job["id"],
                "probe_run_id": result["id"],
                "result": result["result"],
                "classification": classification["classification"],
            },
        )

    def _finish(self, job_id: str, state: str, reason: str, probe_run_id: str | None) -> None:
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(OrchestrationJob, job_id)
            if row is None:
                return
            row.state = state
            row.reason_code = reason
            row.probe_run_id = probe_run_id
            row.updated_at = now
            row.completed_at = now
            run = session.get(OrchestrationRun, row.orchestration_run_id)
            if run:
                remaining = session.scalars(
                    select(OrchestrationJob).where(
                        OrchestrationJob.orchestration_run_id == run.id,
                        OrchestrationJob.id != row.id,
                        OrchestrationJob.state.not_in(self.TERMINAL),
                    )
                ).first()
                if remaining is None:
                    run.state = "COMPLETE"
                    run.terminal_status = "COMPLETED"
                    run.completed_at = now
                    run.updated_at = now

    def list(
        self, project_id: str | None = None, state: str | None = None, limit: int = 500
    ) -> list[dict[str, Any]]:
        with self.sessions() as session:
            query = select(OrchestrationJob)
            if project_id:
                query = query.where(OrchestrationJob.project_id == project_id)
            if state:
                query = query.where(OrchestrationJob.state == state)
            rows = session.scalars(
                query.order_by(OrchestrationJob.created_at.desc()).limit(max(1, min(limit, 1000)))
            ).all()
            return [self._public(row) for row in rows]

    def get(self, job_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(OrchestrationJob, job_id)
            if row is None:
                raise RuntimeError("ORCHESTRATION_JOB_NOT_FOUND")
            return self._public(row)

    def cancel(self, job_id: str) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(OrchestrationJob, job_id)
            if row is None:
                raise RuntimeError("ORCHESTRATION_JOB_NOT_FOUND")
            if row.state in self.TERMINAL:
                return self._public(row)
            if row.state == "RUNNING":
                self.probes.cancel(row.project_id, row.probe_id)
            row.state = "CANCELLED"
            row.updated_at = now
            row.completed_at = now
            session.flush()
            value = self._public(row)
        self.events.publish("orchestration_cancelled", value["project_id"], {"job_id": job_id})
        return value

    def resume_deferred(self, project_id: str | None = None) -> int:
        count = 0
        with self.sessions.begin() as session:
            query = select(OrchestrationJob).where(OrchestrationJob.state == "DEFERRED")
            if project_id:
                query = query.where(OrchestrationJob.project_id == project_id)
            for row in session.scalars(query).all():
                row.state = "QUEUED"
                row.defer_reason = None
                row.updated_at = _now()
                count += 1
        with self._wake:
            self._wake.notify_all()
        return count

    def recover(self) -> dict[str, int]:
        recovered = stale = interrupted = 0
        now = _now()
        with self.sessions.begin() as session:
            for row in session.scalars(
                select(OrchestrationJob).where(OrchestrationJob.state.in_(["QUEUED", "RUNNING"]))
            ).all():
                snapshot = session.get(SourceSnapshot, row.snapshot_id)
                if snapshot is None or snapshot.manifest_digest != row.source_identity_digest:
                    row.state = "STALE"
                    row.defer_reason = "RECOVERY_SOURCE_STALE"
                    stale += 1
                elif row.state == "RUNNING":
                    row.state = "QUEUED" if row.idempotence == "SAFE" else "BLOCKED"
                    row.defer_reason = (
                        "RECOVERED_INTERRUPTED_SAFE_JOB"
                        if row.idempotence == "SAFE"
                        else "INTERRUPTED_NON_IDEMPOTENT"
                    )
                    interrupted += 1
                    recovered += int(row.state == "QUEUED")
                else:
                    recovered += 1
                row.updated_at = now
            session.add(
                SchedulerRecoveryRecord(
                    id=str(uuid.uuid4()),
                    engine_run_id=self.engine_run_id,
                    recovered_count=recovered,
                    stale_count=stale,
                    interrupted_count=interrupted,
                    details_json=json.dumps({"idempotent_only": True}, sort_keys=True),
                    created_at=now,
                )
            )
        self.events.publish(
            "scheduler_recovered",
            None,
            {"recovered_count": recovered, "stale_count": stale, "interrupted_count": interrupted},
        )
        return {"recovered": recovered, "stale": stale, "interrupted": interrupted}

    def stop(self) -> None:
        self._stop.set()
        with self._wake:
            self._wake.notify_all()
        for thread in self._threads:
            thread.join(timeout=5)
        self._threads.clear()

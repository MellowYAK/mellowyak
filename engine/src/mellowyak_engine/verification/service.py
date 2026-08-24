from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from threading import Event
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    AssertionResult,
    BehaviorBaseline,
    BehaviorVersion,
    BrowserCaptureSession,
    BrowserCaptureStep,
    EvidenceBundle,
    HumanVerificationAttestation,
    ImpactAnalysis,
    Project,
    ProtectedBehavior,
    ProtectionPlan,
    ProtectionPlanItem,
    RegressionFinding,
    ReverificationLink,
    RuntimeConfiguration,
    VerificationAuditEvent,
    VerificationRun,
    VerificationRunItem,
)
from mellowyak_engine.evidence.service import EvidenceService
from mellowyak_engine.gate.service import GateService
from mellowyak_engine.regression.service import RegressionService
from mellowyak_engine.verification.adapters.base import ReplayInput
from mellowyak_engine.verification.adapters.browser_replay import BrowserReplayAdapter
from mellowyak_engine.verification.adapters.human_attestation import HumanAttestationAdapter

MAX_REQUIRED_CHECKS = 50
MAX_RUN_SECONDS = 15 * 60


class VerificationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _source_matches(project: Project, identity: dict[str, Any]) -> bool:
    return project.current_head_sha == identity.get(
        "head_sha"
    ) and project.current_worktree_fingerprint == identity.get("worktree_fingerprint")


class VerificationService:
    def __init__(
        self,
        sessions: sessionmaker,
        evidence: EvidenceService,
        events: LocalEventBus,
        gate: GateService,
        regressions: RegressionService,
        installation_id: str,
    ) -> None:
        self.sessions = sessions
        self.evidence = evidence
        self.events = events
        self.gate = gate
        self.regressions = regressions
        self.installation_id = installation_id
        self.adapter = BrowserReplayAdapter()
        self.human = HumanAttestationAdapter()
        self._cancel: dict[str, Event] = {}

    def start(
        self,
        project_id: str,
        change_id: str,
        plan_id: str,
        requested_item_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self.events.publish("verification_queued", project_id, {"plan_id": plan_id})
        now = _now()
        run_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            plan = session.get(ProtectionPlan, plan_id)
            if project is None:
                raise VerificationError("PROJECT_NOT_FOUND")
            if plan is None or plan.project_id != project_id or plan.change_id != change_id:
                raise VerificationError("PROTECTION_PLAN_NOT_FOUND")
            identity = json.loads(plan.source_identity_json)
            if plan.status == "STALE" or not _source_matches(project, identity):
                raise VerificationError("PROTECTION_PLAN_STALE")
            analysis = session.get(ImpactAnalysis, plan.impact_analysis_id)
            if (
                analysis is None
                or analysis.stale
                or analysis.scan_revision != identity.get("scan_revision")
            ):
                raise VerificationError("PROTECTION_PLAN_STALE")
            required = session.scalars(
                select(ProtectionPlanItem)
                .where(
                    ProtectionPlanItem.plan_id == plan_id,
                    ProtectionPlanItem.selection_class == "REQUIRED",
                )
                .order_by(ProtectionPlanItem.behavior_id)
                .limit(MAX_REQUIRED_CHECKS + 1)
            ).all()
            if requested_item_ids:
                requested = set(requested_item_ids)
                required = [item for item in required if item.id in requested]
                if len(required) != len(requested):
                    raise VerificationError("REQUIRED_PLAN_ITEM_NOT_FOUND")
            if len(required) > MAX_REQUIRED_CHECKS:
                raise VerificationError("REQUIRED_CHECK_LIMIT_EXCEEDED")
            for plan_item in required:
                behavior = session.get(ProtectedBehavior, plan_item.behavior_id)
                if (
                    behavior is None
                    or behavior.current_version_id != plan_item.behavior_version_id
                    or behavior.last_accepted_baseline_id != plan_item.baseline_id
                ):
                    raise VerificationError("PROTECTION_PLAN_STALE")
            reverification = bool(
                session.scalars(
                    select(RegressionFinding).where(
                        RegressionFinding.project_id == project_id,
                        RegressionFinding.behavior_id.in_([item.behavior_id for item in required]),
                        RegressionFinding.status == "DETECTED",
                    )
                ).first()
            )
            session.add(
                VerificationRun(
                    id=run_id,
                    project_id=project_id,
                    change_id=change_id,
                    plan_id=plan_id,
                    source_identity_json=_json(identity),
                    status="RUNNING",
                    started_at=now,
                    created_at=now,
                )
            )
            for plan_item in required:
                run_item = VerificationRunItem(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    plan_item_id=plan_item.id,
                    project_id=project_id,
                    behavior_id=plan_item.behavior_id,
                    behavior_version_id=plan_item.behavior_version_id,
                    result="NOT_RUN",
                    adapter=plan_item.verification_method,
                    adapter_version=(
                        self.adapter.version
                        if plan_item.verification_method == "BROWSER_REPLAY"
                        else self.human.version
                    ),
                    limitations_json="[]",
                )
                session.add(run_item)
                session.flush()
                plan_item.current_result_id = run_item.id
            self._audit(session, project_id, "verification_started", "run", run_id, {})
        cancel = Event()
        self._cancel[run_id] = cancel
        self.events.publish("verification_started", project_id, {"run_id": run_id})
        if reverification:
            self.events.publish("reverification_started", project_id, {"run_id": run_id})
        self.gate.evaluate(project_id, change_id, plan_id, run_id)
        try:
            self._execute(run_id, cancel)
        finally:
            self._cancel.pop(run_id, None)
        return self.get(project_id, change_id, run_id)

    def _execute(self, run_id: str, cancel: Event) -> None:
        run_started = time.monotonic()
        with self.sessions() as session:
            run = session.get(VerificationRun, run_id)
            if run is None:
                raise VerificationError("VERIFICATION_RUN_NOT_FOUND")
            item_ids = session.scalars(
                select(VerificationRunItem.id)
                .where(VerificationRunItem.run_id == run_id)
                .order_by(VerificationRunItem.id)
            ).all()
            project_id, change_id, plan_id = run.project_id, run.change_id, run.plan_id
        for item_id in item_ids:
            if cancel.is_set():
                self._mark_cancelled(run_id, item_ids)
                break
            if time.monotonic() - run_started >= MAX_RUN_SECONDS:
                self._mark_timeout(run_id)
                break
            self._execute_item(run_id, item_id, cancel)
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            if run is None:
                return
            if run.status != "CANCELLED":
                run.status = "COMPLETED"
                run.completed_at = _now()
                self._audit(
                    session,
                    run.project_id,
                    "verification_completed",
                    "run",
                    run_id,
                    {},
                )
        self.gate.evaluate(project_id, change_id, plan_id, run_id)
        self.events.publish("verification_completed", project_id, {"run_id": run_id})

    def _mark_timeout(self, run_id: str) -> None:
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            if run is None:
                return
            run.status = "ERROR"
            run.error_code = "VERIFICATION_RUN_TIMEOUT"
            run.completed_at = _now()
            rows = session.scalars(
                select(VerificationRunItem).where(
                    VerificationRunItem.run_id == run_id,
                    VerificationRunItem.result == "NOT_RUN",
                )
            ).all()
            for item in rows:
                item.result = "ERROR"
                item.failure_reason = "VERIFICATION_RUN_TIMEOUT"
                item.completed_at = _now()

    def _execute_item(self, run_id: str, item_id: str, cancel: Event) -> None:
        started = _now()
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            item = session.get(VerificationRunItem, item_id)
            if run is None or item is None:
                raise VerificationError("VERIFICATION_ITEM_NOT_FOUND")
            item.started_at = started
            project_id = run.project_id
            behavior_id = item.behavior_id
            if item.adapter == "HUMAN_ATTESTATION":
                item.result = "NEEDS_REVIEW"
                item.failure_reason = "HUMAN_ATTESTATION_REQUIRED"
                item.completed_at = _now()
                self.events.publish(
                    "behavior_check_completed",
                    project_id,
                    {"run_item_id": item_id, "result": "NEEDS_REVIEW"},
                )
                return
            request = self._replay_input(session, run, item)
            project_id = run.project_id
            source_identity = json.loads(run.source_identity_json)
            behavior_id = item.behavior_id
            behavior_version_id = item.behavior_version_id
        self.events.publish(
            "behavior_check_started",
            project_id,
            {"run_item_id": item_id, "behavior_id": behavior_id},
        )
        monotonic = time.monotonic()
        execution = self.adapter.execute(request, cancel)
        duration_ms = (time.monotonic() - monotonic) * 1000
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            item = session.get(VerificationRunItem, item_id)
            project = session.get(Project, project_id)
            behavior = session.get(ProtectedBehavior, behavior_id)
            if run is None or item is None or project is None or behavior is None:
                raise VerificationError("VERIFICATION_STATE_MISSING")
            if (
                not _source_matches(project, source_identity)
                or behavior.current_version_id != behavior_version_id
                or behavior.last_accepted_baseline_id != request.baseline_id
            ):
                execution.result = "STALE"
                execution.failure_reason = "SOURCE_IDENTITY_CHANGED_DURING_VERIFICATION"
            capture_id = str(uuid.uuid4())
            baseline = session.get(BehaviorBaseline, request.baseline_id)
            baseline_capture = self._baseline_capture(session, baseline)
            session.add(
                BrowserCaptureSession(
                    id=capture_id,
                    project_id=project_id,
                    behavior_id=behavior_id,
                    behavior_version_id=behavior_version_id,
                    runtime_configuration_id=baseline_capture.runtime_configuration_id,
                    status="VERIFICATION_COMPLETED",
                    entry_url=request.entry_url,
                    source_revision_json=_json(source_identity),
                    started_at=started,
                    stopped_at=_now(),
                    updated_at=_now(),
                    browser_version=str(execution.runtime_identity.get("browser_version", "")),
                    runtime_identity_json=_json(execution.runtime_identity),
                    expected_assertions_json=_json(request.assertions),
                )
            )
        artifacts: list[tuple[str, str]] = []
        evidence_refs: list[str] = []
        for item_type, content, media_type in execution.artifacts:
            artifact = self.evidence.add_artifact(
                project_id,
                content,
                media_type,
                capture_id=capture_id,
                behavior_id=behavior_id,
                behavior_version_id=behavior_version_id,
                source_identity=source_identity,
                runtime_identity=execution.runtime_identity,
                trust_source="CURRENT_VERIFICATION",
            )
            artifacts.append((item_type, artifact["id"]))
            evidence_refs.append(artifact["id"])
        bundle_id: str | None = None
        if artifacts:
            bundle = self.evidence.create_bundle(
                project_id,
                capture_id,
                artifacts,
                bundle_type="CURRENT_VERIFICATION",
                verification_run_id=run_id,
            )
            bundle_id = str(bundle["id"])
        with self.sessions.begin() as session:
            item = session.get(VerificationRunItem, item_id)
            if item is None:
                raise VerificationError("VERIFICATION_ITEM_NOT_FOUND")
            for ordinal, assertion in enumerate(execution.assertion_results, start=1):
                session.add(
                    AssertionResult(
                        id=str(uuid.uuid4()),
                        verification_run_item_id=item_id,
                        project_id=project_id,
                        ordinal=ordinal,
                        assertion_type=str(assertion["assertion_type"])[:40],
                        expected_json=_json(assertion.get("expected")),
                        observed_json=_json(assertion.get("observed")),
                        result=str(assertion["result"]),
                        evidence_references_json=_json(evidence_refs),
                        failure_reason=assertion.get("failure_reason"),
                        adapter_version=self.adapter.version,
                        started_at=datetime.fromisoformat(str(assertion["started_at"])),
                        completed_at=datetime.fromisoformat(str(assertion["completed_at"])),
                    )
                )
            item.result = execution.result
            item.evidence_bundle_id = bundle_id
            item.duration_ms = duration_ms
            item.limitations_json = _json(execution.limitations)
            item.failure_reason = execution.failure_reason
            item.completed_at = _now()
            self._audit(
                session,
                project_id,
                "verification_item_completed",
                "run_item",
                item_id,
                {"result": execution.result, "evidence_bundle_id": bundle_id},
            )
        for assertion in execution.assertion_results:
            event_name = {
                "PASS": "assertion_passed",
                "FAIL": "assertion_failed",
            }.get(assertion["result"])
            if event_name is None:
                continue
            self.events.publish(
                event_name,
                project_id,
                {"run_item_id": item_id, "assertion_type": assertion["assertion_type"]},
            )
        self.events.publish(
            "behavior_check_completed",
            project_id,
            {"run_item_id": item_id, "result": execution.result},
        )
        if execution.result == "FAIL":
            self.regressions.decide(project_id, run.change_id, item_id)
        elif execution.result == "AUTOMATED_PASS":
            self._resolve_prior_regression(project_id, behavior_id, run_id, item_id)

    def _replay_input(
        self, session: Any, run: VerificationRun, item: VerificationRunItem
    ) -> ReplayInput:
        behavior = session.get(ProtectedBehavior, item.behavior_id)
        version = session.get(BehaviorVersion, item.behavior_version_id)
        baseline = (
            session.get(BehaviorBaseline, behavior.last_accepted_baseline_id)
            if behavior and behavior.last_accepted_baseline_id
            else None
        )
        if (
            behavior is None
            or version is None
            or baseline is None
            or baseline.status != "ACCEPTED"
            or baseline.behavior_version_id != version.id
        ):
            raise VerificationError("COMPATIBLE_BASELINE_REQUIRED")
        capture = self._baseline_capture(session, baseline)
        runtime = session.get(RuntimeConfiguration, capture.runtime_configuration_id)
        if runtime is None:
            raise VerificationError("RUNTIME_CONFIGURATION_NOT_FOUND")
        steps = session.scalars(
            select(BrowserCaptureStep)
            .where(BrowserCaptureStep.capture_id == capture.id)
            .order_by(BrowserCaptureStep.ordinal)
        ).all()
        return ReplayInput(
            entry_url=capture.entry_url,
            allowed_origin=runtime.allowed_origin,
            viewport={"width": runtime.viewport_width, "height": runtime.viewport_height},
            locale=runtime.locale,
            timezone=runtime.timezone,
            steps=[
                {
                    "event_type": step.event_type,
                    "selector": step.selector,
                    "metadata": json.loads(step.metadata_json),
                    "included": step.included,
                }
                for step in steps
            ],
            assertions=json.loads(capture.expected_assertions_json),
            source_identity=json.loads(run.source_identity_json),
            behavior_version_id=version.id,
            baseline_id=baseline.id,
        )

    @staticmethod
    def _baseline_capture(session: Any, baseline: BehaviorBaseline | None) -> BrowserCaptureSession:
        if baseline is None:
            raise VerificationError("COMPATIBLE_BASELINE_REQUIRED")
        bundle = session.get(EvidenceBundle, baseline.evidence_bundle_id)
        capture = session.get(BrowserCaptureSession, bundle.capture_id) if bundle else None
        if capture is None:
            raise VerificationError("BASELINE_CAPTURE_NOT_FOUND")
        return capture

    def attest(
        self,
        project_id: str,
        change_id: str,
        run_id: str,
        run_item_id: str,
        result: str,
        note: str,
        confirmed: bool,
        evidence_reference: str | None = None,
    ) -> dict[str, Any]:
        normalized = result.upper().strip()
        try:
            mapped_result = self.human.normalize(normalized, confirmed, note)
        except ValueError:
            raise VerificationError("HUMAN_ATTESTATION_INVALID") from None
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            item = session.get(VerificationRunItem, run_item_id)
            project = session.get(Project, project_id)
            if (
                run is None
                or item is None
                or project is None
                or run.project_id != project_id
                or run.change_id != change_id
                or item.run_id != run_id
            ):
                raise VerificationError("VERIFICATION_ITEM_NOT_FOUND")
            identity = json.loads(run.source_identity_json)
            if not _source_matches(project, identity):
                raise VerificationError("VERIFICATION_SOURCE_STALE")
            session.add(
                HumanVerificationAttestation(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    verification_run_item_id=run_item_id,
                    installation_id=self.installation_id,
                    result=normalized,
                    note=note.strip(),
                    evidence_reference=evidence_reference,
                    confirmed=True,
                    source_identity_json=_json(identity),
                    created_at=_now(),
                )
            )
            item.result = mapped_result
            item.failure_reason = (
                "HUMAN_REPORTED_FAILURE" if normalized == "DOES_NOT_WORK" else None
            )
            item.completed_at = _now()
            plan_id = run.plan_id
            behavior_id = item.behavior_id
        if normalized == "DOES_NOT_WORK":
            self.regressions.decide(project_id, change_id, run_item_id)
        elif normalized == "WORKS":
            self._resolve_prior_regression(project_id, behavior_id, run_id, run_item_id)
        self.gate.evaluate(project_id, change_id, plan_id, run_id)
        return self.get(project_id, change_id, run_id)

    def cancel(self, project_id: str, change_id: str, run_id: str) -> dict[str, Any]:
        cancel = self._cancel.get(run_id)
        if cancel:
            cancel.set()
        with self.sessions() as session:
            run = session.get(VerificationRun, run_id)
            if run is None or run.project_id != project_id or run.change_id != change_id:
                raise VerificationError("VERIFICATION_RUN_NOT_FOUND")
        self._mark_cancelled(run_id, [])
        return self.get(project_id, change_id, run_id)

    def _mark_cancelled(self, run_id: str, item_ids: list[str]) -> None:
        project_id = None
        with self.sessions.begin() as session:
            run = session.get(VerificationRun, run_id)
            if run is None:
                return
            project_id = run.project_id
            run.status = "CANCELLED"
            run.cancelled_at = _now()
            rows = session.scalars(
                select(VerificationRunItem).where(VerificationRunItem.run_id == run_id)
            ).all()
            for item in rows:
                if item.result == "NOT_RUN" or item.id in item_ids:
                    item.result = "CANCELLED"
                    item.completed_at = _now()
        if project_id:
            self.events.publish("verification_cancelled", project_id, {"run_id": run_id})

    def _resolve_prior_regression(
        self, project_id: str, behavior_id: str, current_run_id: str, current_item_id: str
    ) -> None:
        with self.sessions.begin() as session:
            finding = session.scalars(
                select(RegressionFinding)
                .where(
                    RegressionFinding.project_id == project_id,
                    RegressionFinding.behavior_id == behavior_id,
                    RegressionFinding.status == "DETECTED",
                )
                .order_by(RegressionFinding.created_at.desc())
            ).first()
            if finding is None:
                return
            previous_item = session.get(VerificationRunItem, finding.verification_run_item_id)
            if previous_item is None or previous_item.run_id == current_run_id:
                return
            finding.status = "RESOLVED"
            finding.resolved_at = _now()
            finding.resolving_run_item_id = current_item_id
            session.add(
                ReverificationLink(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    regression_id=finding.id,
                    previous_run_id=previous_item.run_id,
                    current_run_id=current_run_id,
                    created_at=_now(),
                )
            )
        self.events.publish("regression_resolved", project_id, {"regression_id": finding.id})

    def get(self, project_id: str, change_id: str, run_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            run = session.get(VerificationRun, run_id)
            if run is None or run.project_id != project_id or run.change_id != change_id:
                raise VerificationError("VERIFICATION_RUN_NOT_FOUND")
            items = session.scalars(
                select(VerificationRunItem)
                .where(VerificationRunItem.run_id == run_id)
                .order_by(VerificationRunItem.id)
            ).all()
            return {
                "id": run.id,
                "project_id": run.project_id,
                "change_id": run.change_id,
                "plan_id": run.plan_id,
                "source_identity": json.loads(run.source_identity_json),
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "cancelled_at": run.cancelled_at,
                "error_code": run.error_code,
                "created_at": run.created_at,
                "items": [self._item_public(session, item) for item in items],
            }

    def get_for_project(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            run = session.get(VerificationRun, run_id)
            if run is None or run.project_id != project_id:
                raise VerificationError("VERIFICATION_RUN_NOT_FOUND")
            change_id = run.change_id
        return self.get(project_id, change_id, run_id)

    def retry(self, project_id: str, run_id: str) -> dict[str, Any]:
        previous = self.get_for_project(project_id, run_id)
        return self.start(project_id, previous["change_id"], previous["plan_id"])

    @staticmethod
    def _item_public(session: Any, item: VerificationRunItem) -> dict[str, Any]:
        assertions = session.scalars(
            select(AssertionResult)
            .where(AssertionResult.verification_run_item_id == item.id)
            .order_by(AssertionResult.ordinal)
        ).all()
        return {
            "id": item.id,
            "plan_item_id": item.plan_item_id,
            "behavior_id": item.behavior_id,
            "behavior_version_id": item.behavior_version_id,
            "result": item.result,
            "adapter": item.adapter,
            "adapter_version": item.adapter_version,
            "evidence_bundle_id": item.evidence_bundle_id,
            "duration_ms": item.duration_ms,
            "limitations": json.loads(item.limitations_json),
            "failure_reason": item.failure_reason,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "assertions": [
                {
                    "id": row.id,
                    "ordinal": row.ordinal,
                    "assertion_type": row.assertion_type,
                    "expected": json.loads(row.expected_json),
                    "observed": json.loads(row.observed_json),
                    "result": row.result,
                    "evidence_references": json.loads(row.evidence_references_json),
                    "failure_reason": row.failure_reason,
                }
                for row in assertions
            ],
        }

    @staticmethod
    def _audit(
        session: Any,
        project_id: str,
        event_type: str,
        subject_type: str,
        subject_id: str,
        details: dict[str, Any],
    ) -> None:
        session.add(
            VerificationAuditEvent(
                project_id=project_id,
                event_type=event_type,
                subject_type=subject_type,
                subject_id=subject_id,
                details_json=_json(details),
                created_at=_now(),
            )
        )

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    CompletionGateDecision,
    ImpactAnalysis,
    Project,
    ProtectedBehavior,
    ProtectionPlan,
    ProtectionPlanItem,
    VerificationRun,
    VerificationRunItem,
)
from mellowyak_engine.evidence.service import EvidenceService, EvidenceServiceError


class GateError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


class GateService:
    LIMITATIONS = [
        "Verified Complete covers only checks required by the current known Protection Plan.",
        "Unknown, unsupported, unprotected, and future source states are not proven safe.",
    ]

    def __init__(
        self, sessions: sessionmaker, events: LocalEventBus, evidence: EvidenceService
    ) -> None:
        self.sessions = sessions
        self.events = events
        self.evidence = evidence

    def evaluate(
        self, project_id: str, change_id: str, plan_id: str, run_id: str | None = None
    ) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            plan = session.get(ProtectionPlan, plan_id)
            if project is None:
                raise GateError("PROJECT_NOT_FOUND")
            if plan is None or plan.project_id != project_id or plan.change_id != change_id:
                raise GateError("PROTECTION_PLAN_NOT_FOUND")
            source = json.loads(plan.source_identity_json)
            current = {
                "head_sha": project.current_head_sha,
                "worktree_fingerprint": project.current_worktree_fingerprint,
            }
            items = session.scalars(
                select(ProtectionPlanItem).where(ProtectionPlanItem.plan_id == plan_id)
            ).all()
            analysis = session.get(ImpactAnalysis, plan.impact_analysis_id)
            stale_binding = bool(
                analysis is None
                or analysis.stale
                or analysis.scan_revision != source.get("scan_revision")
            )
            for plan_item in items:
                behavior = session.get(ProtectedBehavior, plan_item.behavior_id)
                if (
                    behavior is None
                    or behavior.current_version_id != plan_item.behavior_version_id
                    or behavior.last_accepted_baseline_id != plan_item.baseline_id
                ):
                    stale_binding = True
            required = [item for item in items if item.selection_class == "REQUIRED"]
            results: list[str] = []
            result_rows: list[VerificationRunItem | None] = []
            for item in required:
                result = (
                    session.get(VerificationRunItem, item.current_result_id)
                    if item.current_result_id
                    else None
                )
                result_rows.append(result)
                results.append(result.result if result else "NOT_RUN")
            if (
                plan.status == "STALE"
                or any(source.get(key) != value for key, value in current.items())
                or stale_binding
            ):
                state, reason = "STALE", "The source identity changed after this plan was created."
            elif (
                run_id
                and (run := session.get(VerificationRun, run_id))
                and run.status in {"QUEUED", "RUNNING"}
            ):
                state, reason = "VERIFYING", "Required checks are running."
            elif any(
                item.selection_class == "UNKNOWN" and item.criticality == "CRITICAL"
                for item in items
            ):
                state, reason = "NEEDS_REVIEW", "A critical unknown boundary requires review."
            elif not required:
                state, reason = (
                    "VERIFIED_COMPLETE",
                    "No behavior is required by the current known Protection Plan.",
                )
            elif any(result == "FAIL" for result in results):
                state, reason = (
                    "BLOCKED",
                    "A required Protected Behavior failed fresh verification.",
                )
            elif any(result == "STALE" for result in results):
                state, reason = (
                    "STALE",
                    "A required result is stale for the current source identity.",
                )
            elif any(
                result in {"INCONCLUSIVE", "ERROR", "NEEDS_REVIEW", "CANCELLED"}
                for result in results
            ):
                state, reason = "NEEDS_REVIEW", "A required check remains unresolved."
            elif any(result == "NOT_RUN" for result in results):
                state, reason = (
                    "RECHECK_REQUIRED",
                    "Required checks have not produced current evidence.",
                )
            elif all(result in {"AUTOMATED_PASS", "HUMAN_ATTESTED_PASS"} for result in results):
                evidence_intact = all(
                    row is not None
                    and (
                        row.result == "HUMAN_ATTESTED_PASS"
                        or self._evidence_intact(project_id, row.evidence_bundle_id)
                    )
                    for row in result_rows
                )
                if evidence_intact:
                    state, reason = (
                        "VERIFIED_COMPLETE",
                        "Every required check passed for this exact source identity.",
                    )
                else:
                    state, reason = "NEEDS_REVIEW", "Current verification evidence is not intact."
            else:
                state, reason = (
                    "NEEDS_REVIEW",
                    "The gate cannot support completion from the available evidence.",
                )
            payload = {
                "project_id": project_id,
                "change_id": change_id,
                "plan_id": plan_id,
                "verification_run_id": run_id,
                "state": state,
                "reason": reason,
                "source_identity": source,
                "limitations": self.LIMITATIONS,
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            existing = session.scalars(
                select(CompletionGateDecision).where(
                    CompletionGateDecision.project_id == project_id,
                    CompletionGateDecision.change_id == change_id,
                    CompletionGateDecision.decision_digest == digest,
                )
            ).first()
            if existing is None:
                existing = CompletionGateDecision(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    change_id=change_id,
                    plan_id=plan_id,
                    verification_run_id=run_id,
                    state=state,
                    reason=reason,
                    source_identity_json=json.dumps(source, sort_keys=True),
                    limitations_json=json.dumps(self.LIMITATIONS),
                    decision_digest=digest,
                    created_at=_now(),
                )
                session.add(existing)
                session.flush()
            blocked_before = bool(
                state == "STALE"
                and session.scalars(
                    select(CompletionGateDecision).where(
                        CompletionGateDecision.project_id == project_id,
                        CompletionGateDecision.change_id == change_id,
                        CompletionGateDecision.state == "BLOCKED",
                    )
                ).first()
            )
            response = self._public(existing)
        event = {
            "BLOCKED": "gate_blocked",
            "NEEDS_REVIEW": "gate_needs_review",
            "VERIFIED_COMPLETE": "verified_complete",
            "STALE": "verification_stale",
        }.get(state)
        if event:
            self.events.publish(
                event, project_id, {"change_id": change_id, "gate_id": response["id"]}
            )
        if blocked_before:
            self.events.publish(
                "source_changed_after_failure",
                project_id,
                {"change_id": change_id, "gate_id": response["id"]},
            )
        return response

    def _evidence_intact(self, project_id: str, bundle_id: str | None) -> bool:
        if not bundle_id:
            return False
        try:
            bundle = self.evidence.get_bundle(project_id, bundle_id)
        except EvidenceServiceError:
            return False
        return bool(
            bundle["bundle_type"] == "CURRENT_VERIFICATION"
            and bundle["items"]
            and all(item["artifact"]["integrity_verified"] for item in bundle["items"])
        )

    def latest(self, project_id: str, change_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.scalars(
                select(CompletionGateDecision)
                .where(
                    CompletionGateDecision.project_id == project_id,
                    CompletionGateDecision.change_id == change_id,
                )
                .order_by(CompletionGateDecision.created_at.desc())
            ).first()
            if row is None:
                raise GateError("GATE_DECISION_NOT_FOUND")
            plan_id = row.plan_id
            run_id = row.verification_run_id
        return self.evaluate(project_id, change_id, plan_id, run_id)

    @staticmethod
    def _public(row: CompletionGateDecision) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "change_id": row.change_id,
            "plan_id": row.plan_id,
            "verification_run_id": row.verification_run_id,
            "state": row.state,
            "reason": row.reason,
            "source_identity": json.loads(row.source_identity_json),
            "limitations": json.loads(row.limitations_json),
            "decision_digest": row.decision_digest,
            "created_at": row.created_at,
        }

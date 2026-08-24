from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    AssertionResult,
    BehaviorBaseline,
    ProtectedBehavior,
    RegressionFinding,
    VerificationRun,
    VerificationRunItem,
)


def _now() -> datetime:
    return datetime.now(UTC)


class RegressionService:
    def __init__(self, sessions: sessionmaker, events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    def decide(self, project_id: str, change_id: str, run_item_id: str) -> dict[str, Any] | None:
        with self.sessions.begin() as session:
            item = session.get(VerificationRunItem, run_item_id)
            run = session.get(VerificationRun, item.run_id) if item else None
            behavior = session.get(ProtectedBehavior, item.behavior_id) if item else None
            baseline = (
                session.get(BehaviorBaseline, behavior.last_accepted_baseline_id)
                if behavior and behavior.last_accepted_baseline_id
                else None
            )
            failed = session.scalars(
                select(AssertionResult).where(
                    AssertionResult.verification_run_item_id == run_item_id,
                    AssertionResult.result == "FAIL",
                )
            ).all()
            supported = bool(
                item
                and item.project_id == project_id
                and run
                and run.change_id == change_id
                and item.result == "FAIL"
                and behavior
                and behavior.project_id == project_id
                and behavior.lifecycle_state == "PROTECTED"
                and baseline
                and baseline.status == "ACCEPTED"
                and baseline.behavior_version_id == item.behavior_version_id
                and behavior.current_version_id == item.behavior_version_id
                and failed
            )
            if not supported:
                return None
            finding = RegressionFinding(
                id=str(uuid.uuid4()),
                project_id=project_id,
                change_id=change_id,
                behavior_id=item.behavior_id,
                behavior_version_id=item.behavior_version_id,
                baseline_id=baseline.id,
                verification_run_item_id=item.id,
                status="DETECTED",
                decision_reason=(
                    "A required deterministic assertion failed against the current exact "
                    "source identity while a compatible active Last Known Good exists."
                ),
                source_identity_json=json.dumps(
                    json.loads(run.source_identity_json)
                    | {"current_verification_run_item_id": item.id},
                    sort_keys=True,
                ),
                created_at=_now(),
            )
            session.add(finding)
            session.flush()
            response = self._public(finding)
        self.events.publish(
            "regression_detected",
            project_id,
            {"regression_id": response["id"], "change_id": change_id},
        )
        return response

    def list(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(RegressionFinding)
                .where(RegressionFinding.project_id == project_id)
                .order_by(RegressionFinding.created_at.desc())
            ).all()
            return [self._public(row) for row in rows]

    def get(self, project_id: str, regression_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RegressionFinding, regression_id)
            if row is None or row.project_id != project_id:
                raise RuntimeError("REGRESSION_NOT_FOUND")
            return self._public(row)

    @staticmethod
    def _public(row: RegressionFinding) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "change_id": row.change_id,
            "behavior_id": row.behavior_id,
            "behavior_version_id": row.behavior_version_id,
            "baseline_id": row.baseline_id,
            "verification_run_item_id": row.verification_run_item_id,
            "status": row.status,
            "decision_reason": row.decision_reason,
            "source_identity": json.loads(row.source_identity_json),
            "created_at": row.created_at,
            "resolved_at": row.resolved_at,
            "resolving_run_item_id": row.resolving_run_item_id,
        }

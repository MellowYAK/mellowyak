from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.db.models import ImpactMemoryRelation


class ImpactMemoryService:
    """Deterministic evidence-backed memory that enriches Probe selection."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def observe_selection(
        self,
        project_id: str,
        source_identity_digest: str,
        changed_paths: list[str],
        selected: list[dict[str, Any]],
        evidence_reference: str,
    ) -> None:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            for item in selected:
                behavior_id = item.get("behavior_id")
                if not behavior_id:
                    continue
                reason = str(item.get("reason", "STATIC_RELATION"))
                provenance = (
                    "EXPLICIT_BEHAVIOR_LINK"
                    if "LINK" in reason
                    else "TEST_RELATION"
                    if "TEST" in reason
                    else "STATIC_RELATION"
                )
                for path in changed_paths[:500]:
                    row = session.scalars(
                        select(ImpactMemoryRelation).where(
                            ImpactMemoryRelation.project_id == project_id,
                            ImpactMemoryRelation.source_key == path,
                            ImpactMemoryRelation.behavior_id == behavior_id,
                            ImpactMemoryRelation.provenance == provenance,
                            ImpactMemoryRelation.source_identity_digest == source_identity_digest,
                        )
                    ).first()
                    if row is None:
                        session.add(
                            ImpactMemoryRelation(
                                id=str(uuid.uuid4()),
                                project_id=project_id,
                                source_key=path,
                                behavior_id=behavior_id,
                                provenance=provenance,
                                source_identity_digest=source_identity_digest,
                                runtime_version_scope=None,
                                evidence_reference=evidence_reference,
                                active=True,
                                stale_reason=None,
                                reason=reason[:240],
                                first_observed_at=now,
                                last_observed_at=now,
                            )
                        )
                    else:
                        row.last_observed_at = now
                        row.active = True
                        row.stale_reason = None

    def record_result(
        self,
        project_id: str,
        behavior_id: str | None,
        source_identity_digest: str,
        probe_run_id: str,
        result: str,
    ) -> None:
        if not behavior_id or result not in {"PASS", "FAIL"}:
            return
        provenance = "HISTORICAL_PASS" if result == "PASS" else "HISTORICAL_FAILURE"
        now = datetime.now(UTC)
        key = f"probe-run:{probe_run_id}"
        with self.sessions.begin() as session:
            session.add(
                ImpactMemoryRelation(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    source_key=key,
                    behavior_id=behavior_id,
                    provenance=provenance,
                    source_identity_digest=source_identity_digest,
                    runtime_version_scope=None,
                    evidence_reference=probe_run_id,
                    active=True,
                    stale_reason=None,
                    reason="CURRENT_PROBE_RESULT_HISTORY",
                    first_observed_at=now,
                    last_observed_at=now,
                )
            )

    @staticmethod
    def _public(row: ImpactMemoryRelation) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "source_key": row.source_key,
            "behavior_id": row.behavior_id,
            "provenance": row.provenance,
            "source_identity_digest": row.source_identity_digest,
            "runtime_version_scope": row.runtime_version_scope,
            "evidence_reference": row.evidence_reference,
            "active": row.active,
            "stale_reason": row.stale_reason,
            "reason": row.reason,
            "first_observed_at": row.first_observed_at.isoformat(),
            "last_observed_at": row.last_observed_at.isoformat(),
        }

    def list(self, project_id: str, limit: int = 500) -> dict[str, Any]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ImpactMemoryRelation)
                .where(ImpactMemoryRelation.project_id == project_id)
                .order_by(ImpactMemoryRelation.last_observed_at.desc())
                .limit(max(1, min(limit, 1000)))
            ).all()
        return {
            "project_id": project_id,
            "relations": [self._public(row) for row in rows],
            "known_facts": ["IMPACT_MEMORY_IS_EVIDENCE_BACKED"],
            "unknowns": ["OMITTED_BEHAVIORS_WERE_NOT_VERIFIED"],
            "limitations": ["HISTORY_DOES_NOT_PROVE_CAUSATION"],
        }

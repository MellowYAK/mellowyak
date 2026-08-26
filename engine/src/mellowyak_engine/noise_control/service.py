from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.db.models import (
    AlertDeduplicationRecord,
    ProbeFlakinessRecord,
)


class NoiseControlService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    @staticmethod
    def incident_key(
        project_id: str,
        behavior_id: str | None,
        baseline_identity: str | None,
        source_identity_digest: str,
        category: str,
    ) -> str:
        raw = "\x00".join(
            [
                project_id,
                behavior_id or "-",
                baseline_identity or "-",
                source_identity_digest,
                category,
            ]
        )
        return f"sentinel:{hashlib.sha256(raw.encode()).hexdigest()}"

    def record_incident(
        self,
        *,
        project_id: str,
        behavior_id: str | None,
        baseline_identity: str | None,
        source_identity_digest: str,
        category: str,
        alert_id: str | None,
        delivery_status: str,
    ) -> dict[str, Any]:
        key = self.incident_key(
            project_id, behavior_id, baseline_identity, source_identity_digest, category
        )
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            row = session.get(AlertDeduplicationRecord, key)
            if row is None:
                row = AlertDeduplicationRecord(
                    deduplication_key=key,
                    project_id=project_id,
                    behavior_id=behavior_id,
                    baseline_identity=baseline_identity,
                    source_identity_digest=source_identity_digest,
                    signal_category=category,
                    alert_id=alert_id,
                    delivery_status=delivery_status,
                    occurrence_count=1,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(row)
            else:
                row.occurrence_count += 1
                row.last_seen_at = now
                row.alert_id = row.alert_id or alert_id
                if row.delivery_status == "PERSISTED":
                    row.delivery_status = delivery_status
            session.flush()
            return {
                "deduplication_key": key,
                "occurrence_count": row.occurrence_count,
                "delivery_status": row.delivery_status,
            }

    def classify_attempts(
        self,
        project_id: str,
        probe_id: str,
        source_identity_digest: str,
        attempts: list[dict[str, Any]],
        quarantine_threshold: int = 3,
    ) -> dict[str, Any]:
        results = [str(item.get("result", "INCONCLUSIVE")) for item in attempts]
        if "FAIL" in results and results[-1:] == ["PASS"]:
            classification = "FLAKY"
        elif results.count("FAIL") >= 2:
            reasons = {
                json.dumps(item.get("observed", {}), sort_keys=True)
                for item in attempts
                if item.get("result") == "FAIL"
            }
            classification = "CONFIRMED" if len(reasons) == 1 else "NEEDS_REVIEW"
        elif results == ["PASS"]:
            classification = "PASS"
        elif "CANCELLED" in results:
            classification = "CANCELLED"
        else:
            classification = "INCONCLUSIVE"
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            row = session.scalars(
                select(ProbeFlakinessRecord).where(
                    ProbeFlakinessRecord.probe_id == probe_id,
                    ProbeFlakinessRecord.source_identity_digest == source_identity_digest,
                )
            ).first()
            count = (row.consecutive_flaky_count if row else 0) + (
                1 if classification == "FLAKY" else 0
            )
            if classification != "FLAKY":
                count = 0
            if row is None:
                row = ProbeFlakinessRecord(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    probe_id=probe_id,
                    source_identity_digest=source_identity_digest,
                    classification=classification,
                    consecutive_flaky_count=count,
                    quarantined=count >= quarantine_threshold,
                    last_attempts_json=json.dumps(attempts, sort_keys=True),
                    updated_at=now,
                )
                session.add(row)
            else:
                row.classification = classification
                row.consecutive_flaky_count = count
                row.quarantined = count >= quarantine_threshold
                row.last_attempts_json = json.dumps(attempts, sort_keys=True)
                row.updated_at = now
            return {
                "classification": classification,
                "quarantined": row.quarantined,
                "consecutive_flaky_count": count,
            }

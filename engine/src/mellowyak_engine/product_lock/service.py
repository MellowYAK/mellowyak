from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    ApplyTransaction,
    BaselineAttestation,
    BehaviorBaseline,
    BehaviorChangeDecision,
    BrowserCaptureSession,
    EvidenceBundle,
    EvidenceBundleItem,
    OrchestrationJob,
    OrchestrationRun,
    ProbeDefinition,
    ProbeRun,
    ProbeVersion,
    Project,
    ProtectedBehavior,
    RegressionFinding,
    RuntimeProfileVersion,
    SourceEpisode,
    YakReceipt,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(value: str | None, fallback: object) -> Any:
    return json.loads(value) if value else fallback


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _source_identity(project: Project) -> dict[str, object]:
    return {
        "branch": project.current_branch,
        "head_sha": project.current_head_sha,
        "worktree_fingerprint": project.current_worktree_fingerprint,
    }


def _same_source(expected: dict[str, object], current: dict[str, object]) -> bool:
    return all(current.get(key) == value for key, value in expected.items())


class ProductLockError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProductLockService:
    """Protects an accepted Known Good from silent, in-place replacement."""

    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    @staticmethod
    def _behavior(session: Session, project_id: str, behavior_id: str) -> ProtectedBehavior:
        row = session.get(ProtectedBehavior, behavior_id)
        if row is None or row.project_id != project_id:
            raise ProductLockError("BEHAVIOR_NOT_FOUND")
        return row

    @staticmethod
    def _project(session: Session, project_id: str) -> Project:
        row = session.get(Project, project_id)
        if row is None or row.archived_at is not None:
            raise ProductLockError("PROJECT_NOT_FOUND")
        return row

    @staticmethod
    def _baseline_public(row: BehaviorBaseline, current_id: str | None) -> dict[str, object]:
        source = _load(row.source_revision_json, {})
        return {
            "id": row.id,
            "order": 0,
            "current": row.id == current_id,
            "status": row.status,
            "behavior_version_id": row.behavior_version_id,
            "evidence_bundle_id": row.evidence_bundle_id,
            "source_identity": source,
            "source_identity_alias": str(
                source.get("head_sha") or source.get("worktree_fingerprint") or "unknown"
            )[:12],
            "runtime_identity": _load(row.promotion_runtime_identity_json, {}),
            "verification_run_id": row.promotion_verification_run_id,
            "verification_result": "PASS"
            if row.promotion_verification_run_id
            else "LEGACY_ACCEPTED",
            "supersedes_baseline_id": row.supersedes_baseline_id,
            "promotion_reason": row.promotion_reason,
            "actor": row.promotion_actor or "LOCAL_OPERATOR",
            "accepted_at": row.created_at.isoformat(),
            "promotion_confirmed_at": row.promotion_confirmed_at.isoformat()
            if row.promotion_confirmed_at
            else None,
            "limitations": ["LEGACY_LINEAGE_ROOT"]
            if not row.supersedes_baseline_id and not row.promotion_decision_id
            else [],
        }

    def lineage(self, project_id: str, behavior_id: str) -> dict[str, object]:
        with self.sessions() as session:
            behavior = self._behavior(session, project_id, behavior_id)
            rows = session.scalars(
                select(BehaviorBaseline)
                .where(BehaviorBaseline.behavior_id == behavior_id)
                .order_by(BehaviorBaseline.created_at.desc(), BehaviorBaseline.id.desc())
            ).all()
            baselines = [
                self._baseline_public(row, behavior.last_accepted_baseline_id) for row in rows
            ]
            for order, item in enumerate(reversed(baselines), start=1):
                item["order"] = order
            decision = session.scalars(
                select(BehaviorChangeDecision)
                .where(BehaviorChangeDecision.behavior_id == behavior_id)
                .order_by(BehaviorChangeDecision.created_at.desc())
                .limit(1)
            ).first()
            return {
                "project_id": project_id,
                "behavior_id": behavior_id,
                "state": decision.state
                if decision
                else ("BASELINE_LOCKED" if rows else "NO_KNOWN_GOOD"),
                "current_baseline_id": behavior.last_accepted_baseline_id,
                "baselines": baselines,
                "active_decision": self._decision_public(decision, include_confirmation=False)
                if decision
                else None,
                "known_facts": [
                    "KNOWN_GOOD_RECORDS_ARE_IMMUTABLE",
                    "PROMOTION_REQUIRES_COMPARABLE_PASS",
                ],
                "unknowns": [] if rows else ["NO_ACCEPTED_KNOWN_GOOD"],
                "limitations": ["OLD_RECORDS_MAY_BE_LINEAGE_ROOTS_WITHOUT_PROMOTION_REASON"],
            }

    @staticmethod
    def _decision_public(
        row: BehaviorChangeDecision, *, include_confirmation: bool, nonce: str | None = None
    ) -> dict[str, object]:
        value: dict[str, object] = {
            "id": row.id,
            "project_id": row.project_id,
            "behavior_id": row.behavior_id,
            "previous_baseline_id": row.previous_baseline_id,
            "decision": row.decision,
            "state": row.state,
            "reason": row.reason,
            "source_identity": _load(row.source_identity_json, {}),
            "runtime_identity": _load(row.runtime_identity_json, {}),
            "capture_id": row.capture_id,
            "verification_run_id": row.verification_run_id,
            "promoted_baseline_id": row.promoted_baseline_id,
            "confirmation_expires_at": row.confirmation_expires_at.isoformat()
            if row.confirmation_expires_at
            else None,
            "confirmation_used": row.confirmation_used_at is not None,
            "actor": row.actor,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "known_facts": ["CURRENT_BASELINE_PRESERVED"],
            "unknowns": [],
            "limitations": [],
        }
        if include_confirmation:
            value["confirmation_nonce"] = nonce
        return value

    def decide(
        self, project_id: str, behavior_id: str, decision: str, reason: str
    ) -> dict[str, object]:
        normalized = decision.strip().upper()
        reason = reason.strip()
        if normalized not in {"EXPECTED", "REGRESSION", "UNSURE"}:
            raise ProductLockError("CHANGE_DECISION_INVALID")
        if normalized == "EXPECTED" and not reason:
            raise ProductLockError("PROMOTION_REASON_REQUIRED")
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            behavior = self._behavior(session, project_id, behavior_id)
            baseline_id = behavior.last_accepted_baseline_id
            baseline = session.get(BehaviorBaseline, baseline_id) if baseline_id else None
            if baseline is None or baseline.status not in {"ACCEPTED", "STALE"}:
                raise ProductLockError("BASELINE_NOT_FOUND")
            state = {
                "EXPECTED": "EXPECTED_CHANGE_SELECTED",
                "REGRESSION": "KEPT_CURRENT_BASELINE",
                "UNSURE": "CHANGE_REVIEW_REQUIRED",
            }[normalized]
            row = BehaviorChangeDecision(
                id=str(uuid.uuid4()),
                project_id=project_id,
                behavior_id=behavior_id,
                previous_baseline_id=baseline.id,
                decision=normalized,
                state=state,
                reason=reason,
                source_identity_json=_json(_source_identity(project)),
                runtime_identity_json="{}",
                actor="LOCAL_OPERATOR",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        self.events.publish(
            "behavior_change_decided",
            project_id,
            {"behavior_id": behavior_id, "decision_id": row.id, "decision": normalized},
        )
        return self._decision_public(row, include_confirmation=False)

    def reverify(
        self, project_id: str, behavior_id: str, decision_id: str, capture_id: str
    ) -> dict[str, object]:
        now = datetime.now(UTC)
        nonce = secrets.token_urlsafe(32)
        with self.sessions() as session:
            project = self._project(session, project_id)
            behavior = self._behavior(session, project_id, behavior_id)
            decision = session.get(BehaviorChangeDecision, decision_id)
            if (
                decision is None
                or decision.project_id != project_id
                or decision.behavior_id != behavior_id
            ):
                raise ProductLockError("CHANGE_DECISION_NOT_FOUND")
            if decision.decision != "EXPECTED" or decision.state != "EXPECTED_CHANGE_SELECTED":
                raise ProductLockError("EXPECTED_CHANGE_STATE_INVALID")
            if behavior.last_accepted_baseline_id != decision.previous_baseline_id:
                raise ProductLockError("CURRENT_BASELINE_CHANGED")
            expected_source = _load(decision.source_identity_json, {})
            current_source = _source_identity(project)
            if not _same_source(expected_source, current_source):
                decision.state = "PROMOTION_BLOCKED_STALE_SOURCE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_SOURCE_STALE")
            capture = session.get(BrowserCaptureSession, capture_id)
            if (
                capture is None
                or capture.project_id != project_id
                or capture.behavior_id != behavior_id
            ):
                raise ProductLockError("CAPTURE_NOT_FOUND")
            if (
                capture.status != "VALIDATED"
                or capture.behavior_version_id != behavior.current_version_id
            ):
                raise ProductLockError("EXPECTED_CHANGE_CAPTURE_NOT_VALIDATED")
            if not _same_source(_load(capture.source_revision_json, {}), current_source):
                decision.state = "PROMOTION_BLOCKED_STALE_SOURCE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_SOURCE_STALE")
            bundle = session.scalars(
                select(EvidenceBundle).where(EvidenceBundle.capture_id == capture_id)
            ).first()
            run = (
                session.get(ProbeRun, bundle.verification_run_id)
                if bundle and bundle.verification_run_id
                else None
            )
            if (
                run is None
                or run.project_id != project_id
                or run.status != "COMPLETED"
                or run.result != "PASS"
            ):
                decision.state = "PROMOTION_BLOCKED_NON_COMPARABLE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_COMPARABLE_PASS_REQUIRED")
            probe = session.get(ProbeDefinition, run.probe_id)
            version = session.get(ProbeVersion, run.probe_version_id)
            if (
                probe is None
                or version is None
                or probe.behavior_id != behavior_id
                or not run.runtime_profile_version_id
            ):
                decision.state = "PROMOTION_BLOCKED_NON_COMPARABLE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_COMPARABLE_PASS_REQUIRED")
            runtime_version = session.get(RuntimeProfileVersion, run.runtime_profile_version_id)
            if (
                runtime_version is None
                or runtime_version.project_id != project_id
                or runtime_version.approved_at is None
            ):
                decision.state = "PROMOTION_BLOCKED_NON_COMPARABLE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_RUNTIME_NOT_APPROVED")
            runtime_identity = {
                "runtime_profile_version_id": runtime_version.id,
                "runtime_type": runtime_version.runtime_type,
                "runtime_version": runtime_version.runtime_version,
                "adapter_version": runtime_version.adapter_version,
                "probe_id": probe.id,
                "probe_version_id": version.id,
                "probe_version_number": version.version_number,
            }
            decision.state = "PROMOTION_AWAITING_CONFIRMATION"
            decision.capture_id = capture_id
            decision.verification_run_id = run.id
            decision.runtime_identity_json = _json(runtime_identity)
            decision.confirmation_digest = hashlib.sha256(
                f"{decision.id}:{behavior_id}:{run.id}:{nonce}".encode()
            ).hexdigest()
            decision.confirmation_expires_at = now + timedelta(minutes=5)
            decision.updated_at = now
            session.commit()
        self.events.publish(
            "expected_change_verified",
            project_id,
            {"behavior_id": behavior_id, "decision_id": decision_id, "verification_run_id": run.id},
        )
        return self._decision_public(decision, include_confirmation=True, nonce=nonce)

    def promote(
        self,
        project_id: str,
        behavior_id: str,
        decision_id: str,
        confirmation_nonce: str,
        deliberate_confirmation: bool,
        reviewer: str,
        notes: str,
    ) -> dict[str, object]:
        now = datetime.now(UTC)
        if not deliberate_confirmation:
            raise ProductLockError("PROMOTION_DELIBERATE_CONFIRMATION_REQUIRED")
        if not reviewer.strip() or len(reviewer.strip()) > 240 or len(notes) > 4000:
            raise ProductLockError("ATTESTATION_INVALID")
        new_baseline_id = str(uuid.uuid4())
        with self.sessions() as session:
            project = self._project(session, project_id)
            behavior = self._behavior(session, project_id, behavior_id)
            decision = session.get(BehaviorChangeDecision, decision_id)
            if (
                decision is None
                or decision.project_id != project_id
                or decision.behavior_id != behavior_id
            ):
                raise ProductLockError("CHANGE_DECISION_NOT_FOUND")
            if decision.state != "PROMOTION_AWAITING_CONFIRMATION" or decision.confirmation_used_at:
                raise ProductLockError("PROMOTION_CONFIRMATION_ALREADY_USED")
            if (
                decision.confirmation_expires_at is None
                or decision.confirmation_expires_at.replace(tzinfo=UTC) <= now
            ):
                decision.state = "CANCELLED"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_CONFIRMATION_EXPIRED")
            expected_digest = hashlib.sha256(
                f"{decision.id}:{behavior_id}:{decision.verification_run_id}:{confirmation_nonce}".encode()
            ).hexdigest()
            if not secrets.compare_digest(expected_digest, decision.confirmation_digest or ""):
                raise ProductLockError("PROMOTION_CONFIRMATION_INVALID")
            if behavior.last_accepted_baseline_id != decision.previous_baseline_id:
                raise ProductLockError("CURRENT_BASELINE_CHANGED")
            current_source = _source_identity(project)
            if not _same_source(_load(decision.source_identity_json, {}), current_source):
                decision.state = "PROMOTION_BLOCKED_STALE_SOURCE"
                decision.updated_at = now
                session.commit()
                raise ProductLockError("PROMOTION_SOURCE_STALE")
            capture = session.get(BrowserCaptureSession, decision.capture_id)
            bundle = session.scalars(
                select(EvidenceBundle).where(EvidenceBundle.capture_id == decision.capture_id)
            ).first()
            run = session.get(ProbeRun, decision.verification_run_id)
            if (
                capture is None
                or bundle is None
                or run is None
                or run.result != "PASS"
                or run.status != "COMPLETED"
            ):
                raise ProductLockError("PROMOTION_COMPARABLE_PASS_REQUIRED")
            if (
                int(
                    session.scalar(
                        select(func.count())
                        .select_from(EvidenceBundleItem)
                        .where(EvidenceBundleItem.bundle_id == bundle.id)
                    )
                    or 0
                )
                == 0
            ):
                raise ProductLockError("EVIDENCE_BUNDLE_EMPTY")
            attestation_id = str(uuid.uuid4())
            session.add(
                BaselineAttestation(
                    id=attestation_id,
                    project_id=project_id,
                    capture_id=capture.id,
                    status="ACCEPTED",
                    reviewer=reviewer.strip(),
                    notes=notes.strip(),
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                BehaviorBaseline(
                    id=new_baseline_id,
                    project_id=project_id,
                    behavior_id=behavior_id,
                    behavior_version_id=capture.behavior_version_id,
                    evidence_bundle_id=bundle.id,
                    attestation_id=attestation_id,
                    status="ACCEPTED",
                    source_revision_json=_json(current_source),
                    supersedes_baseline_id=decision.previous_baseline_id,
                    promotion_reason=decision.reason,
                    promotion_decision_id=decision.id,
                    promotion_verification_run_id=run.id,
                    promotion_runtime_identity_json=decision.runtime_identity_json,
                    promotion_confirmed_at=now,
                    promotion_actor="LOCAL_OPERATOR",
                    created_at=now,
                )
            )
            previous = session.get(BehaviorBaseline, decision.previous_baseline_id)
            if previous is not None and previous.status != "REVOKED":
                previous.status = "SUPERSEDED"
            capture.status = "ACCEPTED"
            capture.updated_at = now
            bundle.status = "ACCEPTED"
            behavior.last_accepted_baseline_id = new_baseline_id
            behavior.lifecycle_state = "KNOWN_GOOD"
            behavior.updated_at = now
            decision.confirmation_used_at = now
            decision.promoted_baseline_id = new_baseline_id
            decision.state = "PROMOTED"
            decision.updated_at = now
            session.commit()
        self.events.publish(
            "known_good_promoted",
            project_id,
            {
                "behavior_id": behavior_id,
                "baseline_id": new_baseline_id,
                "supersedes": decision.previous_baseline_id,
            },
        )
        return self.lineage(project_id, behavior_id)


class YakReceiptService:
    """Builds and freezes one evidence-bound, path-free receipt per settled Episode."""

    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    @staticmethod
    def _public(row: YakReceipt) -> dict[str, object]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "episode_id": row.episode_id,
            "snapshot_id": row.snapshot_id,
            "source_identity": _load(row.source_identity_json, {}),
            "payload": _load(row.payload_json, {}),
            "digest": row.digest,
            "created_at": row.created_at.isoformat(),
            "known_facts": ["LOCAL_ONLY", "EPISODE_BOUND", "IMMUTABLE_AFTER_CREATION"],
            "unknowns": list(_load(row.payload_json, {}).get("unknown_reason_codes", [])),
            "limitations": ["OMITTED_AND_DEFERRED_BEHAVIORS_WERE_NOT_CHECKED"],
        }

    def get_or_create(self, project_id: str, episode_id: str) -> dict[str, object]:
        with self.sessions() as session:
            existing = session.scalars(
                select(YakReceipt).where(YakReceipt.episode_id == episode_id)
            ).first()
            if existing is not None:
                if existing.project_id != project_id:
                    raise ProductLockError("YAK_RECEIPT_NOT_FOUND")
                return self._public(existing)
            episode = session.get(SourceEpisode, episode_id)
            if episode is None or episode.project_id != project_id:
                raise ProductLockError("EPISODE_NOT_FOUND")
            run = session.scalars(
                select(OrchestrationRun).where(OrchestrationRun.episode_id == episode_id)
            ).first()
            if episode.status != "STABILIZED" or run is None or run.completed_at is None:
                raise ProductLockError("YAK_RECEIPT_EPISODE_NOT_TERMINAL")
            jobs = session.scalars(
                select(OrchestrationJob).where(OrchestrationJob.orchestration_run_id == run.id)
            ).all()
            probe_runs = {
                row.id: row
                for row in session.scalars(
                    select(ProbeRun).where(
                        ProbeRun.id.in_([job.probe_run_id for job in jobs if job.probe_run_id])
                    )
                ).all()
            }
            selected = _load(run.selected_behaviors_json, [])
            omitted = _load(run.omitted_behaviors_json, [])
            evidence: list[dict[str, object]] = []
            checked = passed = failed = runtime_unavailable = unknown = deferred = 0
            checked_run_ids: list[str] = []
            for job in jobs:
                probe_run = probe_runs.get(job.probe_run_id or "")
                if job.state == "DEFERRED":
                    deferred += 1
                elif probe_run is not None and probe_run.status == "COMPLETED":
                    checked += 1
                    checked_run_ids.append(probe_run.id)
                    if probe_run.result == "PASS":
                        passed += 1
                    elif probe_run.result == "FAIL":
                        failed += 1
                    elif probe_run.result == "RUNTIME_UNAVAILABLE":
                        runtime_unavailable += 1
                    else:
                        unknown += 1
                    evidence.append(
                        {
                            "behavior_id": job.behavior_id,
                            "probe_id": job.probe_id,
                            "probe_version_id": job.probe_version_id,
                            "run_id": probe_run.id,
                            "result": probe_run.result,
                            "comparable": probe_run.result in {"PASS", "FAIL"},
                            "limitations": _load(probe_run.limitations_json, []),
                        }
                    )
                elif job.state not in {"CANCELLED", "SUPERSEDED"}:
                    unknown += 1
            confirmed = (
                int(
                    session.scalar(
                        select(func.count())
                        .select_from(RegressionFinding)
                        .where(
                            RegressionFinding.project_id == project_id,
                            RegressionFinding.probe_run_id.in_(checked_run_ids),
                            RegressionFinding.status == "CONFIRMED",
                        )
                    )
                    or 0
                )
                if checked_run_ids
                else 0
            )
            omitted_count = len(omitted)
            unknown += omitted_count
            source_modified = bool(
                session.scalar(
                    select(func.count())
                    .select_from(ApplyTransaction)
                    .where(
                        ApplyTransaction.project_id == project_id,
                        ApplyTransaction.post_apply_snapshot_id == episode.resulting_snapshot_id,
                        ApplyTransaction.state == "COMMITTED",
                    )
                )
            )
            payload: dict[str, object] = {
                "schema": "mellowyak.yak_receipt.v1",
                "settled_at": episode.ended_at.isoformat()
                if episode.ended_at
                else run.completed_at.isoformat(),
                "protected_behaviors_considered": len(selected) + omitted_count,
                "checked": checked,
                "passed": passed,
                "failed": failed,
                "confirmed_regressions": confirmed,
                "deferred": deferred,
                "runtime_unavailable": runtime_unavailable,
                "omitted": omitted_count,
                "unknown": unknown,
                "unknown_reason_codes": sorted(
                    {str(item.get("reason", "OMITTED")) for item in omitted}
                ),
                "source_modified_by_yak": source_modified,
                "evidence": evidence,
                "omitted_behaviors": [
                    {
                        "behavior_id": item.get("behavior_id"),
                        "probe_id": item.get("probe_id"),
                        "reason": item.get("reason"),
                    }
                    for item in omitted
                ],
            }
            source_identity = _load(run.source_identity_json, {})
            identity = {
                "project_id": project_id,
                "episode_id": episode_id,
                "snapshot_id": episode.resulting_snapshot_id,
                "source_identity": source_identity,
                "payload": payload,
            }
            row = YakReceipt(
                id=str(uuid.uuid4()),
                project_id=project_id,
                episode_id=episode_id,
                snapshot_id=episode.resulting_snapshot_id,
                source_identity_json=_json(source_identity),
                payload_json=_json(payload),
                digest=_digest(identity),
                created_at=datetime.now(UTC),
            )
        with self.sessions.begin() as session:
            session.add(row)
        self.events.publish(
            "yak_receipt_created", project_id, {"episode_id": episode_id, "receipt_id": row.id}
        )
        return self._public(row)

    def list(self, project_id: str, limit: int = 100) -> list[dict[str, object]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(YakReceipt)
                .where(YakReceipt.project_id == project_id)
                .order_by(YakReceipt.created_at.desc())
                .limit(max(1, min(limit, 200)))
            ).all()
            return [self._public(row) for row in rows]

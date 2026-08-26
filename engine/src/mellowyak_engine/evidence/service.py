from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BaselineAttestation,
    BehaviorBaseline,
    BrowserCaptureSession,
    EvidenceArtifact,
    EvidenceAuditEvent,
    EvidenceBundle,
    EvidenceBundleItem,
    ProbeDefinition,
    ProbeRun,
    ProbeVersion,
    Project,
    ProtectedBehavior,
    RuntimeProfileVersion,
)
from mellowyak_engine.evidence.store import EvidenceStore, EvidenceStoreError

MAX_EVIDENCE_BUNDLE_BYTES = 250 * 1024 * 1024


class EvidenceServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


class EvidenceService:
    def __init__(self, sessions: sessionmaker, store: EvidenceStore, events: LocalEventBus) -> None:
        self.sessions = sessions
        self.store = store
        self.events = events

    def add_artifact(
        self,
        project_id: str,
        content: bytes,
        media_type: str,
        redaction_state: str = "REDACTED",
        capture_id: str | None = None,
        behavior_id: str | None = None,
        behavior_version_id: str | None = None,
        source_identity: dict[str, Any] | None = None,
        runtime_identity: dict[str, Any] | None = None,
        trust_source: str = "LOCAL_CAPTURE",
    ) -> dict[str, Any]:
        try:
            stored = self.store.put(project_id, content)
        except EvidenceStoreError as error:
            raise EvidenceServiceError(error.code) from error
        now = _now()
        with self.sessions.begin() as session:
            artifact = session.scalars(
                select(EvidenceArtifact).where(
                    EvidenceArtifact.project_id == project_id,
                    EvidenceArtifact.sha256 == stored.sha256,
                )
            ).first()
            if artifact is None:
                artifact = EvidenceArtifact(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    sha256=stored.sha256,
                    size_bytes=stored.size_bytes,
                    media_type=media_type[:120],
                    object_key=stored.object_key,
                    redaction_state=redaction_state[:40],
                    capture_id=capture_id,
                    behavior_id=behavior_id,
                    behavior_version_id=behavior_version_id,
                    source_identity_json=json.dumps(source_identity or {}, sort_keys=True),
                    runtime_identity_json=json.dumps(runtime_identity or {}, sort_keys=True),
                    trust_source=trust_source[:40],
                    created_at=now,
                )
                session.add(artifact)
                session.flush()
            self._audit(
                session,
                project_id,
                "artifact_reused" if stored.deduplicated else "artifact_created",
                "artifact",
                artifact.id,
                {"sha256": stored.sha256, "size_bytes": stored.size_bytes},
            )
            result = self._artifact_public(artifact, verified=True)
        return result

    def create_bundle(
        self,
        project_id: str,
        capture_id: str,
        items: list[tuple[str, str]],
        bundle_type: str = "BASELINE_CAPTURE",
        verification_run_id: str | None = None,
    ) -> dict[str, Any]:
        if not items:
            raise EvidenceServiceError("EVIDENCE_BUNDLE_EMPTY")
        bundle_id = str(uuid.uuid4())
        now = _now()
        with self.sessions.begin() as session:
            capture = session.get(BrowserCaptureSession, capture_id)
            if capture is None or capture.project_id != project_id:
                raise EvidenceServiceError("CAPTURE_NOT_FOUND")
            existing = session.scalars(
                select(EvidenceBundle).where(EvidenceBundle.capture_id == capture_id)
            ).first()
            if existing is not None:
                return self.get_bundle(project_id, existing.id)
            manifest_items: list[dict[str, Any]] = []
            resolved: list[tuple[str, EvidenceArtifact]] = []
            bundle_size = 0
            for item_type, artifact_id in items:
                artifact = session.get(EvidenceArtifact, artifact_id)
                if artifact is None or artifact.project_id != project_id:
                    raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
                if not self.store.verify(project_id, artifact.sha256):
                    raise EvidenceServiceError("EVIDENCE_OBJECT_HASH_MISMATCH")
                bundle_size += artifact.size_bytes
                if bundle_size > MAX_EVIDENCE_BUNDLE_BYTES:
                    raise EvidenceServiceError("EVIDENCE_BUNDLE_LIMIT_EXCEEDED")
                manifest_items.append(
                    {
                        "ordinal": len(manifest_items) + 1,
                        "item_type": item_type,
                        "artifact_id": artifact.id,
                        "sha256": artifact.sha256,
                        "size_bytes": artifact.size_bytes,
                        "media_type": artifact.media_type,
                    }
                )
                resolved.append((item_type, artifact))
            manifest = {
                "schema": "mellowyak.evidence_bundle.v1",
                "bundle_id": bundle_id,
                "project_id": project_id,
                "capture_id": capture_id,
                "bundle_type": bundle_type,
                "verification_run_id": verification_run_id,
                "source_revision": json.loads(capture.source_revision_json),
                "items": manifest_items,
            }
            payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            manifest_sha256 = self.store.write_manifest(project_id, bundle_id, payload)
            bundle = EvidenceBundle(
                id=bundle_id,
                project_id=project_id,
                capture_id=capture_id,
                manifest_sha256=manifest_sha256,
                status="CAPTURED",
                bundle_type=bundle_type[:40],
                verification_run_id=verification_run_id,
                created_at=now,
            )
            session.add(bundle)
            for ordinal, (item_type, artifact) in enumerate(resolved, start=1):
                session.add(
                    EvidenceBundleItem(
                        id=str(uuid.uuid4()),
                        bundle_id=bundle_id,
                        artifact_id=artifact.id,
                        ordinal=ordinal,
                        item_type=item_type[:40],
                    )
                )
            self._audit(
                session,
                project_id,
                "bundle_created",
                "bundle",
                bundle_id,
                {"manifest_sha256": manifest_sha256, "item_count": len(resolved)},
            )
        self.events.publish("evidence_bundle_created", project_id, {"bundle_id": bundle_id})
        return self.get_bundle(project_id, bundle_id)

    def accept_baseline(
        self,
        project_id: str,
        capture_id: str,
        reviewer: str,
        notes: str,
    ) -> dict[str, Any]:
        reviewer = reviewer.strip()
        notes = notes.strip()
        if not reviewer or len(reviewer) > 240 or len(notes) > 4000:
            raise EvidenceServiceError("ATTESTATION_INVALID")
        now = _now()
        baseline_id = str(uuid.uuid4())
        attestation_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            capture = session.get(BrowserCaptureSession, capture_id)
            if capture is None or capture.project_id != project_id:
                raise EvidenceServiceError("CAPTURE_NOT_FOUND")
            if capture.status != "VALIDATED":
                raise EvidenceServiceError("CAPTURE_REVIEW_REQUIRED")
            project = session.get(Project, project_id)
            if project is None or project.archived_at is not None:
                raise EvidenceServiceError("PROJECT_NOT_FOUND")
            current_source = {
                "branch": project.current_branch,
                "head_sha": project.current_head_sha,
                "worktree_fingerprint": project.current_worktree_fingerprint,
            }
            recorded_source = json.loads(capture.source_revision_json)
            if any(recorded_source.get(key) != current_source.get(key) for key in recorded_source):
                capture.status = "STALE_SOURCE"
                capture.updated_at = now
                raise EvidenceServiceError("CAPTURE_SOURCE_STALE")
            if (
                not capture.expected_assertions_json
                or json.loads(capture.expected_assertions_json) == []
            ):
                raise EvidenceServiceError("EXPECTED_ASSERTION_REQUIRED")
            bundle = session.scalars(
                select(EvidenceBundle).where(EvidenceBundle.capture_id == capture_id)
            ).first()
            if bundle is None:
                raise EvidenceServiceError("EVIDENCE_BUNDLE_NOT_FOUND")
            if not bundle.verification_run_id:
                raise EvidenceServiceError("COMPARABLE_REPLAY_PASS_REQUIRED")
            verification_run = session.get(ProbeRun, bundle.verification_run_id)
            if (
                verification_run is None
                or verification_run.project_id != project_id
                or verification_run.status != "COMPLETED"
                or verification_run.result != "PASS"
            ):
                raise EvidenceServiceError("COMPARABLE_REPLAY_PASS_REQUIRED")
            probe_version = session.get(ProbeVersion, verification_run.probe_version_id)
            probe = session.get(ProbeDefinition, verification_run.probe_id)
            if (
                probe_version is None
                or probe is None
                or probe.project_id != project_id
                or probe.behavior_id != capture.behavior_id
                or probe_version.runtime_profile_version_id is None
            ):
                raise EvidenceServiceError("COMPARABLE_REPLAY_BINDING_INVALID")
            replay_definition = json.loads(probe_version.definition_json)
            runtime_version = session.get(
                RuntimeProfileVersion, probe_version.runtime_profile_version_id
            )
            if (
                replay_definition.get("capture_id") != capture_id
                or runtime_version is None
                or runtime_version.project_id != project_id
                or runtime_version.approved_at is None
            ):
                raise EvidenceServiceError("COMPARABLE_REPLAY_BINDING_INVALID")
            bundle_items = int(
                session.scalar(
                    select(func.count())
                    .select_from(EvidenceBundleItem)
                    .where(EvidenceBundleItem.bundle_id == bundle.id)
                )
                or 0
            )
            if bundle_items == 0:
                raise EvidenceServiceError("EVIDENCE_BUNDLE_EMPTY")
            behavior = session.get(ProtectedBehavior, capture.behavior_id)
            if behavior is None or behavior.project_id != project_id:
                raise EvidenceServiceError("BEHAVIOR_NOT_FOUND")
            if behavior.current_version_id != capture.behavior_version_id:
                raise EvidenceServiceError("CAPTURE_BEHAVIOR_VERSION_STALE")
            attestation = BaselineAttestation(
                id=attestation_id,
                project_id=project_id,
                capture_id=capture_id,
                status="ACCEPTED",
                reviewer=reviewer,
                notes=notes,
                created_at=now,
                updated_at=now,
            )
            session.add(attestation)
            session.add(
                BehaviorBaseline(
                    id=baseline_id,
                    project_id=project_id,
                    behavior_id=capture.behavior_id,
                    behavior_version_id=capture.behavior_version_id,
                    evidence_bundle_id=bundle.id,
                    attestation_id=attestation_id,
                    status="ACCEPTED",
                    source_revision_json=capture.source_revision_json,
                    created_at=now,
                )
            )
            capture.status = "ACCEPTED"
            capture.updated_at = now
            bundle.status = "ACCEPTED"
            behavior.lifecycle_state = "KNOWN_GOOD"
            behavior.last_accepted_baseline_id = baseline_id
            behavior.updated_at = now
            self._audit(
                session,
                project_id,
                "baseline_accepted",
                "baseline",
                baseline_id,
                {"capture_id": capture_id, "attestation_id": attestation_id},
            )
        self.events.publish(
            "behavior_baseline_accepted",
            project_id,
            {"behavior_id": capture.behavior_id, "baseline_id": baseline_id},
        )
        return self.baseline(project_id, baseline_id)

    def bind_verification_run(
        self, project_id: str, capture_id: str, verification_run_id: str
    ) -> dict[str, Any]:
        """Bind a successful comparable replay to the immutable capture manifest."""

        with self.sessions.begin() as session:
            capture = session.get(BrowserCaptureSession, capture_id)
            run = session.get(ProbeRun, verification_run_id)
            bundle = session.scalars(
                select(EvidenceBundle).where(EvidenceBundle.capture_id == capture_id)
            ).first()
            if (
                capture is None
                or capture.project_id != project_id
                or run is None
                or run.project_id != project_id
                or run.status != "COMPLETED"
                or run.result != "PASS"
                or bundle is None
            ):
                raise EvidenceServiceError("COMPARABLE_REPLAY_PASS_REQUIRED")
            items = session.execute(
                select(EvidenceBundleItem, EvidenceArtifact)
                .join(EvidenceArtifact, EvidenceArtifact.id == EvidenceBundleItem.artifact_id)
                .where(EvidenceBundleItem.bundle_id == bundle.id)
                .order_by(EvidenceBundleItem.ordinal)
            ).all()
            manifest = {
                "schema": "mellowyak.evidence_bundle.v1",
                "bundle_id": bundle.id,
                "project_id": project_id,
                "capture_id": capture_id,
                "bundle_type": bundle.bundle_type,
                "verification_run_id": verification_run_id,
                "source_revision": json.loads(capture.source_revision_json),
                "items": [
                    {
                        "ordinal": item.ordinal,
                        "item_type": item.item_type,
                        "artifact_id": artifact.id,
                        "sha256": artifact.sha256,
                        "size_bytes": artifact.size_bytes,
                        "media_type": artifact.media_type,
                    }
                    for item, artifact in items
                ],
            }
            payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            bundle.manifest_sha256 = self.store.write_manifest(project_id, bundle.id, payload)
            bundle.verification_run_id = verification_run_id
            self._audit(
                session,
                project_id,
                "bundle_verification_bound",
                "bundle",
                bundle.id,
                {"verification_run_id": verification_run_id},
            )
            bundle_id = bundle.id
        return self.get_bundle(project_id, bundle_id)

    def revoke_baseline(
        self, project_id: str, behavior_id: str, delete_evidence: bool, confirmation: bool
    ) -> dict[str, Any]:
        if not confirmation:
            raise EvidenceServiceError("BASELINE_REVOCATION_CONFIRMATION_REQUIRED")
        now = _now()
        artifact_deletions: list[tuple[str, str]] = []
        with self.sessions.begin() as session:
            behavior = session.get(ProtectedBehavior, behavior_id)
            if behavior is None or behavior.project_id != project_id:
                raise EvidenceServiceError("BEHAVIOR_NOT_FOUND")
            baseline = (
                session.get(BehaviorBaseline, behavior.last_accepted_baseline_id)
                if behavior.last_accepted_baseline_id
                else None
            )
            if (
                baseline is None
                or baseline.project_id != project_id
                or baseline.status not in {"ACCEPTED", "STALE"}
            ):
                raise EvidenceServiceError("BASELINE_NOT_FOUND")
            baseline.status = "REVOKED"
            baseline.revoked_at = now
            behavior.last_accepted_baseline_id = None
            behavior.lifecycle_state = "DRAFT"
            behavior.updated_at = now
            bundle = session.get(EvidenceBundle, baseline.evidence_bundle_id)
            if bundle is not None:
                bundle.status = "REVOKED"
                if delete_evidence:
                    items = session.execute(
                        select(EvidenceBundleItem, EvidenceArtifact)
                        .join(
                            EvidenceArtifact, EvidenceArtifact.id == EvidenceBundleItem.artifact_id
                        )
                        .where(EvidenceBundleItem.bundle_id == bundle.id)
                    ).all()
                    for item, artifact in items:
                        artifact_deletions.append((artifact.id, artifact.sha256))
                        session.delete(item)
                        session.delete(artifact)
            self._audit(
                session,
                project_id,
                "baseline_revoked",
                "baseline",
                baseline.id,
                {"evidence_deleted": delete_evidence},
            )
        for _, digest in artifact_deletions:
            self.store.delete(project_id, digest)
        self.events.publish("evidence_revoked", project_id, {"behavior_id": behavior_id})
        return {"status": "REVOKED", "behavior_id": behavior_id}

    def list_evidence(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            bundles = session.scalars(
                select(EvidenceBundle)
                .where(EvidenceBundle.project_id == project_id)
                .order_by(EvidenceBundle.created_at.desc())
            ).all()
            artifacts = session.scalars(
                select(EvidenceArtifact)
                .where(EvidenceArtifact.project_id == project_id)
                .order_by(EvidenceArtifact.created_at.desc())
            ).all()
            return {
                "bundles": [
                    {
                        "id": row.id,
                        "capture_id": row.capture_id,
                        "manifest_sha256": row.manifest_sha256,
                        "status": row.status,
                        "bundle_type": row.bundle_type,
                        "verification_run_id": row.verification_run_id,
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in bundles
                ],
                "artifacts": [
                    self._artifact_public(row, self.store.verify(project_id, row.sha256))
                    for row in artifacts
                ],
            }

    def remove_review_artifact(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        delete_object = False
        sha256 = ""
        with self.sessions.begin() as session:
            artifact = session.get(EvidenceArtifact, artifact_id)
            if artifact is None or artifact.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
            item = session.scalars(
                select(EvidenceBundleItem).where(EvidenceBundleItem.artifact_id == artifact_id)
            ).first()
            if item is not None:
                bundle = session.get(EvidenceBundle, item.bundle_id)
                if bundle is None or bundle.status != "CAPTURED":
                    raise EvidenceServiceError("EVIDENCE_REFERENCED_BY_ACCEPTED_BASELINE")
                session.delete(item)
                session.flush()
                capture = session.get(BrowserCaptureSession, bundle.capture_id)
                if capture is None:
                    raise EvidenceServiceError("CAPTURE_NOT_FOUND")
                remaining = session.execute(
                    select(EvidenceBundleItem, EvidenceArtifact)
                    .join(EvidenceArtifact, EvidenceArtifact.id == EvidenceBundleItem.artifact_id)
                    .where(EvidenceBundleItem.bundle_id == bundle.id)
                    .order_by(EvidenceBundleItem.ordinal)
                ).all()
                manifest_items: list[dict[str, Any]] = []
                for ordinal, (remaining_item, remaining_artifact) in enumerate(remaining, start=1):
                    remaining_item.ordinal = ordinal
                    manifest_items.append(
                        {
                            "ordinal": ordinal,
                            "item_type": remaining_item.item_type,
                            "artifact_id": remaining_artifact.id,
                            "sha256": remaining_artifact.sha256,
                            "size_bytes": remaining_artifact.size_bytes,
                            "media_type": remaining_artifact.media_type,
                        }
                    )
                manifest = {
                    "schema": "mellowyak.evidence_bundle.v1",
                    "bundle_id": bundle.id,
                    "project_id": project_id,
                    "capture_id": capture.id,
                    "source_revision": json.loads(capture.source_revision_json),
                    "items": manifest_items,
                }
                payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
                bundle.manifest_sha256 = self.store.write_manifest(project_id, bundle.id, payload)
            remaining_references = int(
                session.scalar(
                    select(func.count())
                    .select_from(EvidenceBundleItem)
                    .where(EvidenceBundleItem.artifact_id == artifact_id)
                )
                or 0
            )
            sha256 = artifact.sha256
            if remaining_references == 0:
                session.delete(artifact)
                delete_object = True
            self._audit(session, project_id, "review_artifact_deleted", "artifact", artifact_id, {})
        if delete_object:
            self.store.delete(project_id, sha256)
        return {"status": "deleted", "artifact_id": artifact_id}

    def baseline(self, project_id: str, baseline_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(BehaviorBaseline, baseline_id)
            if row is None or row.project_id != project_id:
                raise EvidenceServiceError("BASELINE_NOT_FOUND")
            attestation = session.get(BaselineAttestation, row.attestation_id)
            return {
                "id": row.id,
                "project_id": row.project_id,
                "behavior_id": row.behavior_id,
                "behavior_version_id": row.behavior_version_id,
                "evidence_bundle_id": row.evidence_bundle_id,
                "status": row.status,
                "source_revision": json.loads(row.source_revision_json),
                "attestation": {
                    "id": attestation.id,
                    "status": attestation.status,
                    "reviewer": attestation.reviewer,
                    "notes": attestation.notes,
                    "created_at": attestation.created_at,
                },
                "created_at": row.created_at,
                "revoked_at": row.revoked_at,
            }

    def get_bundle(self, project_id: str, bundle_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            bundle = session.get(EvidenceBundle, bundle_id)
            if bundle is None or bundle.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_BUNDLE_NOT_FOUND")
            items = session.execute(
                select(EvidenceBundleItem, EvidenceArtifact)
                .join(EvidenceArtifact, EvidenceArtifact.id == EvidenceBundleItem.artifact_id)
                .where(EvidenceBundleItem.bundle_id == bundle_id)
                .order_by(EvidenceBundleItem.ordinal)
            ).all()
            return {
                "id": bundle.id,
                "project_id": bundle.project_id,
                "capture_id": bundle.capture_id,
                "manifest_sha256": bundle.manifest_sha256,
                "status": bundle.status,
                "bundle_type": bundle.bundle_type,
                "verification_run_id": bundle.verification_run_id,
                "items": [
                    {
                        "ordinal": item.ordinal,
                        "item_type": item.item_type,
                        "artifact": self._artifact_public(
                            artifact, self.store.verify(project_id, artifact.sha256)
                        ),
                    }
                    for item, artifact in items
                ],
                "created_at": bundle.created_at,
            }

    def artifact(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(EvidenceArtifact, artifact_id)
            if row is None or row.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
            verified = self.store.verify(project_id, row.sha256)
            return self._artifact_public(row, verified)

    def artifact_content(self, project_id: str, artifact_id: str) -> tuple[bytes, str]:
        with self.sessions() as session:
            row = session.get(EvidenceArtifact, artifact_id)
            if row is None or row.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
            try:
                return self.store.read(project_id, row.sha256), row.media_type
            except EvidenceStoreError as error:
                raise EvidenceServiceError(error.code) from error

    def artifact_local_path(self, project_id: str, artifact_id: str):  # type: ignore[no-untyped-def]
        with self.sessions() as session:
            row = session.get(EvidenceArtifact, artifact_id)
            if row is None or row.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
            path = (self.store.root / row.object_key).resolve()
            if not path.is_relative_to(self.store.root) or not path.is_file() or path.is_symlink():
                raise EvidenceServiceError("EVIDENCE_OBJECT_NOT_FOUND")
            return path

    def delete_artifact(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            artifact = session.get(EvidenceArtifact, artifact_id)
            if artifact is None or artifact.project_id != project_id:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_NOT_FOUND")
            accepted_refs = int(
                session.scalar(
                    select(func.count())
                    .select_from(EvidenceBundleItem)
                    .join(EvidenceBundle, EvidenceBundle.id == EvidenceBundleItem.bundle_id)
                    .join(
                        BehaviorBaseline,
                        BehaviorBaseline.evidence_bundle_id == EvidenceBundle.id,
                    )
                    .where(
                        EvidenceBundleItem.artifact_id == artifact_id,
                        BehaviorBaseline.status == "ACCEPTED",
                    )
                )
                or 0
            )
            any_refs = int(
                session.scalar(
                    select(func.count())
                    .select_from(EvidenceBundleItem)
                    .where(EvidenceBundleItem.artifact_id == artifact_id)
                )
                or 0
            )
            if accepted_refs:
                raise EvidenceServiceError("EVIDENCE_REFERENCED_BY_ACCEPTED_BASELINE")
            if any_refs:
                raise EvidenceServiceError("EVIDENCE_ARTIFACT_STILL_REFERENCED")
            sha256 = artifact.sha256
            session.delete(artifact)
            self._audit(
                session,
                project_id,
                "artifact_deleted",
                "artifact",
                artifact_id,
                {"sha256": sha256},
            )
        try:
            self.store.delete(project_id, sha256)
        except EvidenceStoreError as error:
            raise EvidenceServiceError(error.code) from error
        return {"status": "deleted", "artifact_id": artifact_id}

    @staticmethod
    def _artifact_public(row: EvidenceArtifact, verified: bool) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "sha256": row.sha256,
            "size_bytes": row.size_bytes,
            "media_type": row.media_type,
            "redaction_state": row.redaction_state,
            "capture_id": row.capture_id,
            "behavior_id": row.behavior_id,
            "behavior_version_id": row.behavior_version_id,
            "source_identity": json.loads(row.source_identity_json),
            "runtime_identity": json.loads(row.runtime_identity_json),
            "trust_source": row.trust_source,
            "local_reference": row.object_key,
            "integrity_verified": verified,
            "created_at": row.created_at,
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
            EvidenceAuditEvent(
                project_id=project_id,
                event_type=event_type,
                subject_type=subject_type,
                subject_id=subject_id,
                details_json=json.dumps(details, sort_keys=True),
                created_at=_now(),
            )
        )

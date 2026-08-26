from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Alert,
    ApplyJournalEvent,
    ApplyTransaction,
    ApplyTransactionFile,
    Project,
    RegressionFinding,
    RepairCandidate,
    RepairCandidateFile,
    RepairCandidateValidation,
    RepairWorkspace,
    RollbackRecord,
)
from mellowyak_engine.recovery.bundle import RecoveryBundleService
from mellowyak_engine.repair_validation.policy import checks_from_policy
from mellowyak_engine.repair_validation.service import RepairValidationService
from mellowyak_engine.safe_apply.capability import (
    confirmation_digest,
    issue_confirmation,
    verify_confirmation,
)
from mellowyak_engine.safe_apply.journal import DurableJournal
from mellowyak_engine.safe_apply.operations import ApplyOperationError, atomic_copy, durable_delete
from mellowyak_engine.safe_apply.preflight import (
    PreflightError,
    digest_path,
    safe_live_path,
    verify_expected,
)
from mellowyak_engine.snapshots.service import SnapshotService
from mellowyak_engine.snapshots.store import SnapshotStore, canonical_json
from mellowyak_engine.workflow.states import (
    APPLY_TRANSITIONS,
    ApplyState,
    TransitionError,
    transition,
)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SafeApplyServiceError(RuntimeError):
    def __init__(self, code: str, path: str | None = None) -> None:
        self.code = code
        self.path = path
        super().__init__(code)


class SafeApplyService:
    ACTIVE_STATES = {
        "AWAITING_CONFIRMATION",
        "PREFLIGHT",
        "SAFETY_SNAPSHOT",
        "JOURNAL_CREATED",
        "PREPARING",
        "WRITING",
        "CAPTURING_LIVE_SOURCE",
        "VERIFYING_LIVE",
        "ROLLING_BACK",
    }

    @staticmethod
    def _inject_fault(
        fault_injector: Callable[[str], None] | None,
        point: str,
    ) -> None:
        if fault_injector is not None:
            fault_injector(point)

    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
        snapshots: SnapshotService,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self.snapshots = snapshots
        self.recovery_bundles = RecoveryBundleService(sessions, data_root)

    def _candidate_context(
        self, session: Session, project_id: str, candidate_id: str
    ) -> tuple[
        RepairCandidate,
        RepairCandidateValidation,
        RepairWorkspace,
        Project,
        list[RepairCandidateFile],
    ]:
        candidate = session.get(RepairCandidate, candidate_id)
        if candidate is None or candidate.project_id != project_id:
            raise SafeApplyServiceError("REPAIR_CANDIDATE_NOT_FOUND")
        validation = session.scalars(
            select(RepairCandidateValidation)
            .where(
                RepairCandidateValidation.candidate_id == candidate_id,
                RepairCandidateValidation.status == "PASSED",
                RepairCandidateValidation.candidate_digest == candidate.candidate_digest,
            )
            .order_by(RepairCandidateValidation.completed_at.desc())
        ).first()
        if candidate.state != "VALIDATED" or validation is None:
            raise SafeApplyServiceError("APPLY_VALIDATED_CANDIDATE_REQUIRED")
        workspace = session.get(RepairWorkspace, candidate.workspace_id)
        project = session.get(Project, project_id)
        if workspace is None or workspace.deleted_at is not None:
            raise SafeApplyServiceError("REPAIR_WORKSPACE_NOT_FOUND")
        if project is None or project.archived_at is not None or not project.source_available:
            raise SafeApplyServiceError("PROJECT_NOT_AVAILABLE")
        files = list(
            session.scalars(
                select(RepairCandidateFile)
                .where(
                    RepairCandidateFile.candidate_id == candidate_id,
                    RepairCandidateFile.excluded.is_(False),
                )
                .order_by(RepairCandidateFile.ordinal)
            ).all()
        )
        if not files or any(not item.apply_eligible for item in files):
            raise SafeApplyServiceError("APPLY_INELIGIBLE_CANDIDATE")
        return candidate, validation, workspace, project, files

    def _journal_path(self, project_id: str, transaction_id: str) -> Path:
        root = (self.data_root / "projects" / project_id / "apply-journals").resolve(strict=False)
        path = (root / f"{transaction_id}.json").resolve(strict=False)
        try:
            path.relative_to(root)
        except ValueError as error:
            raise SafeApplyServiceError("APPLY_JOURNAL_PATH_INVALID") from error
        return path

    @staticmethod
    def _project_root(project: Project) -> Path:
        configured = Path(project.canonical_root_path or project.root_path)
        try:
            root = configured.resolve(strict=True)
        except OSError as error:
            raise SafeApplyServiceError("PROJECT_NOT_AVAILABLE") from error
        if not root.is_dir() or root != configured.expanduser().resolve(strict=True):
            raise SafeApplyServiceError("PROJECT_ROOT_RELOCATED")
        return root

    def _source_matches_snapshot(
        self, project_id: str, project_root: Path, snapshot_id: str
    ) -> bool:
        store = SnapshotStore(self.data_root, project_id)
        expected = store.load_manifest(snapshot_id)
        temporary_id = f"preflight-{uuid.uuid4()}"
        captured = store.capture(
            project_root,
            snapshot_id=temporary_id,
            creation_reason="APPLY_PREFLIGHT",
            source_identity={"kind": "apply_preflight"},
        )
        try:
            return [entry.to_dict() for entry in captured.manifest.entries] == [
                entry.to_dict() for entry in expected.entries
            ]
        finally:
            store.manifest_path(temporary_id).unlink(missing_ok=True)

    @staticmethod
    def _expected_for(item: RepairCandidateFile, path: str) -> str | None:
        if item.operation == "RENAME" and path == item.rename_source:
            return item.base_digest
        if item.operation == "ADD":
            return None
        return item.expected_live_digest

    @staticmethod
    def _affected_paths(files: list[RepairCandidateFile]) -> list[str]:
        paths: set[str] = set()
        for item in files:
            paths.add(item.relative_path)
            if item.rename_source:
                paths.add(item.rename_source)
        return sorted(paths)

    def _preflight_paths(
        self, project_root: Path, files: list[RepairCandidateFile]
    ) -> dict[str, str | None]:
        digests: dict[str, str | None] = {}
        for item in files:
            paths = [item.relative_path]
            if item.rename_source:
                paths.append(item.rename_source)
            for relative in paths:
                target = safe_live_path(project_root, relative)
                expected = self._expected_for(item, relative)
                verify_expected(target, expected, relative)
                digests[relative] = expected
                parent = target.parent
                if not os.access(parent, os.W_OK):
                    raise PreflightError("APPLY_PATH_NOT_WRITABLE", relative)
        return digests

    def prepare(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            candidate, validation, workspace, project, files = self._candidate_context(
                session, project_id, candidate_id
            )
            active = session.scalar(
                select(func.count(ApplyTransaction.id)).where(
                    ApplyTransaction.project_id == project_id,
                    ApplyTransaction.state.in_(self.ACTIVE_STATES),
                )
            )
            if active:
                raise SafeApplyServiceError("APPLY_TRANSACTION_ALREADY_ACTIVE")
            project_root = self._project_root(project)
            if not self._source_matches_snapshot(
                project_id, project_root, candidate.source_snapshot_id
            ):
                candidate_id_to_mark = candidate.id
                session.rollback()
                with self.sessions.begin() as stale_session:
                    stale_candidate = stale_session.get(RepairCandidate, candidate_id_to_mark)
                    if stale_candidate is not None:
                        stale_candidate.state = "STALE"
                        stale_candidate.updated_at = datetime.now(UTC)
                raise SafeApplyServiceError("APPLY_LIVE_SOURCE_CHANGED")
            try:
                self._preflight_paths(project_root, files)
            except PreflightError as error:
                raise SafeApplyServiceError(error.code, error.path) from error
            transaction_id = str(uuid.uuid4())
            nonce, nonce_digest = issue_confirmation(
                transaction_id,
                project_id,
                candidate_id,
                candidate.base_manifest_digest,
            )
            expires = datetime.now(UTC) + timedelta(minutes=5)
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            candidate, validation, _, _, files = self._candidate_context(
                session, project_id, candidate_id
            )
            transaction = ApplyTransaction(
                id=transaction_id,
                project_id=project_id,
                candidate_id=candidate_id,
                validation_id=validation.id,
                state="AWAITING_CONFIRMATION",
                expected_source_snapshot_id=candidate.source_snapshot_id,
                expected_source_manifest_digest=candidate.base_manifest_digest,
                confirmation_digest=nonce_digest,
                confirmation_expires_at=expires,
                journal_relative_path="",
                created_at=now,
                updated_at=now,
            )
            session.add(transaction)
            session.flush()
            for item in files:
                session.add(
                    ApplyTransactionFile(
                        id=str(uuid.uuid4()),
                        transaction_id=transaction_id,
                        ordinal=item.ordinal,
                        relative_path=item.relative_path,
                        operation=item.operation,
                        operation_state="PENDING",
                        original_digest=item.base_digest,
                        candidate_digest=item.candidate_digest,
                    )
                )
        self._journal_event(
            transaction_id,
            "STATE_AWAITING_CONFIRMATION",
            {
                "reason": "apply.confirmation_required",
                "evidence": [validation.id, candidate.source_snapshot_id],
            },
        )
        self.events.publish(
            "apply_prepared",
            project_id,
            {"transaction_id": transaction_id, "candidate_id": candidate_id},
        )
        result = self.get(project_id, transaction_id)
        result["confirmation_nonce"] = nonce
        result["capabilities"] = [
            "ANALYZE_REPAIR",
            "VALIDATE_REPAIR",
            "PREPARE_APPLY",
            "COMMIT_APPLY",
            "ROLLBACK_APPLY",
        ]
        return result

    def _journal_event(
        self, transaction_id: str, event_type: str, details: dict[str, Any] | None = None
    ) -> None:
        with self.sessions.begin() as session:
            sequence = (
                int(
                    session.scalar(
                        select(func.max(ApplyJournalEvent.sequence)).where(
                            ApplyJournalEvent.transaction_id == transaction_id
                        )
                    )
                    or 0
                )
                + 1
            )
            session.add(
                ApplyJournalEvent(
                    transaction_id=transaction_id,
                    sequence=sequence,
                    event_type=event_type,
                    details_json=_json(details or {}),
                    created_at=datetime.now(UTC),
                )
            )

    def _transition(
        self,
        project_id: str,
        transaction_id: str,
        target: ApplyState,
        *,
        reason: str,
        evidence: list[str] | tuple[str, ...] = (),
    ) -> None:
        """Persist one fail-closed Apply transition and its evidence-bound event."""

        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            row = self._load_transaction(session, project_id, transaction_id)
            try:
                record = transition(
                    APPLY_TRANSITIONS,
                    ApplyState(row.state),
                    target,
                    reason=reason,
                    evidence=evidence,
                    timestamp=now,
                )
            except (ValueError, TransitionError) as error:
                code = getattr(error, "code", "WORKFLOW_TRANSITION_INVALID")
                raise SafeApplyServiceError(str(code)) from error
            row.state = record.current.value
            row.updated_at = record.timestamp
        self._journal_event(
            transaction_id,
            f"STATE_{target.value}",
            {"reason": reason, "evidence": list(evidence)},
        )
        self.events.publish(
            "apply_state_changed",
            project_id,
            {
                "transaction_id": transaction_id,
                "state": target.value,
                "reason": reason,
                "evidence": list(evidence),
            },
        )

    def _load_transaction(
        self, session: Session, project_id: str, transaction_id: str
    ) -> ApplyTransaction:
        transaction = session.get(ApplyTransaction, transaction_id)
        if transaction is None or transaction.project_id != project_id:
            raise SafeApplyServiceError("APPLY_TRANSACTION_NOT_FOUND")
        return transaction

    def confirm(
        self,
        project_id: str,
        transaction_id: str,
        confirmation_nonce: str,
        *,
        fault_injector: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        with self.sessions() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            if transaction.state != "AWAITING_CONFIRMATION" or transaction.confirmation_used_at:
                raise SafeApplyServiceError("APPLY_CONFIRMATION_ALREADY_USED")
            expires = transaction.confirmation_expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if datetime.now(UTC) >= expires:
                raise SafeApplyServiceError("APPLY_CONFIRMATION_EXPIRED")
            provided = confirmation_digest(
                confirmation_nonce,
                transaction.id,
                transaction.project_id,
                transaction.candidate_id,
                transaction.expected_source_manifest_digest,
            )
            if not verify_confirmation(provided, transaction.confirmation_digest):
                raise SafeApplyServiceError("APPLY_CONFIRMATION_INVALID")
            candidate, validation, workspace, project, files = self._candidate_context(
                session, project_id, transaction.candidate_id
            )
            if validation.id != transaction.validation_id:
                raise SafeApplyServiceError("APPLY_VALIDATION_BINDING_INVALID")
            project_root = self._project_root(project)
            workspace_root = (
                self.data_root / workspace.workspace_relative_path / "current"
            ).resolve(strict=True)
            source_snapshot_id = transaction.expected_source_snapshot_id
            source_manifest_digest = transaction.expected_source_manifest_digest
            operation_payload = [
                {
                    "ordinal": item.ordinal,
                    "relative_path": item.relative_path,
                    "operation": item.operation,
                    "original_digest": item.base_digest,
                    "candidate_digest": item.candidate_digest,
                    "rename_source": item.rename_source,
                }
                for item in files
            ]
        confirmed_at = datetime.now(UTC)
        with self.sessions.begin() as session:
            confirmed = self._load_transaction(session, project_id, transaction_id)
            if confirmed.confirmation_used_at is not None:
                raise SafeApplyServiceError("APPLY_CONFIRMATION_ALREADY_USED")
            confirmed.confirmation_used_at = confirmed_at
            confirmed.updated_at = confirmed_at
        self._transition(
            project_id,
            transaction_id,
            ApplyState.PREFLIGHT,
            reason="apply.confirmation_consumed",
            evidence=[validation.id, source_snapshot_id],
        )
        if not self._source_matches_snapshot(project_id, project_root, source_snapshot_id):
            self._fail_without_write(transaction_id, candidate.id, "APPLY_LIVE_SOURCE_CHANGED")
            raise SafeApplyServiceError("APPLY_LIVE_SOURCE_CHANGED")
        try:
            expected_digests = self._preflight_paths(project_root, files)
        except PreflightError as error:
            self._fail_without_write(transaction_id, candidate.id, error.code)
            raise SafeApplyServiceError(error.code, error.path) from error
        safety = self.snapshots.create(
            project_id,
            creation_reason="PRE_APPLY_SAFETY",
            force_fresh=True,
        )
        self.snapshots.pin(project_id, str(safety["id"]), True)
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.safety_snapshot_id = str(safety["id"])
            transaction.updated_at = now
        self._transition(
            project_id,
            transaction_id,
            ApplyState.SAFETY_SNAPSHOT,
            reason="apply.safety_snapshot_created",
            evidence=[str(safety["id"])],
        )
        self.events.publish(
            "safety_snapshot_created",
            project_id,
            {"transaction_id": transaction_id, "snapshot_id": safety["id"]},
        )
        self._inject_fault(fault_injector, "after_safety_snapshot_before_journal")
        journal_path = self._journal_path(project_id, transaction_id)
        journal = DurableJournal.create(
            journal_path,
            {
                "schema": "mellowyak.apply_journal.v1",
                "transaction_id": transaction_id,
                "project_id": project_id,
                "candidate_id": candidate.id,
                "safety_snapshot_id": safety["id"],
                "expected_source_snapshot_id": source_snapshot_id,
                "expected_source_manifest_digest": source_manifest_digest,
                "expected_live_digests": expected_digests,
                "operations": operation_payload,
                "state": "JOURNAL_CREATED",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        relative_journal = journal_path.relative_to(self.data_root).as_posix()
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.journal_relative_path = relative_journal
            transaction.updated_at = datetime.now(UTC)
        self._transition(
            project_id,
            transaction_id,
            ApplyState.JOURNAL_CREATED,
            reason="apply.durable_journal_created",
            evidence=[relative_journal],
        )
        journal.append("JOURNAL_CREATED", {"relative_path": relative_journal})
        self._transition(
            project_id,
            transaction_id,
            ApplyState.PREPARING,
            reason="apply.preparing_writes",
            evidence=[str(safety["id"]), relative_journal],
        )
        journal.append("PREPARING")
        self._transition(
            project_id,
            transaction_id,
            ApplyState.WRITING,
            reason="apply.source_writes_started",
            evidence=[relative_journal],
        )
        journal.append("WRITING")
        self.events.publish("apply_started", project_id, {"transaction_id": transaction_id})
        self._inject_fault(fault_injector, "after_journal_before_first_write")
        try:
            self._apply_files(
                project_id,
                transaction_id,
                project_root,
                workspace_root,
                files,
                journal,
                fault_injector,
            )
        except (ApplyOperationError, PreflightError, OSError) as error:
            code = getattr(error, "code", "APPLY_WRITE_FAILED")
            journal.append("APPLY_FAILED", {"error_code": code})
            self._journal_event(transaction_id, "APPLY_FAILED", {"error_code": code})
            return self.rollback(project_id, transaction_id, reason=code)
        self._inject_fault(fault_injector, "after_all_writes_before_post_verify")
        return self._post_verify(
            project_id,
            transaction_id,
            project_root,
            workspace,
            journal,
            fault_injector=fault_injector,
        )

    def _fail_without_write(self, transaction_id: str, candidate_id: str, code: str) -> None:
        with self.sessions.begin() as session:
            transaction = session.get(ApplyTransaction, transaction_id)
            candidate = session.get(RepairCandidate, candidate_id)
            if transaction:
                transaction.state = "BLOCKED"
                transaction.error_code = code
                transaction.completed_at = datetime.now(UTC)
                transaction.updated_at = datetime.now(UTC)
            if candidate:
                candidate.state = "STALE"
                candidate.updated_at = datetime.now(UTC)

    def _apply_files(
        self,
        project_id: str,
        transaction_id: str,
        project_root: Path,
        workspace_root: Path,
        files: list[RepairCandidateFile],
        journal: DurableJournal,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        writes = [item for item in files if item.operation not in {"DELETE"}]
        deletions = [item for item in files if item.operation == "DELETE"]
        for item in writes:
            target = safe_live_path(project_root, item.relative_path)
            expected = None if item.operation in {"ADD", "RENAME"} else item.expected_live_digest
            verify_expected(target, expected, item.relative_path)
            if item.candidate_digest is None:
                raise ApplyOperationError("APPLY_CANDIDATE_DIGEST_MISSING", item.relative_path)
            source = workspace_root / item.relative_path
            atomic_copy(source, target, item.candidate_digest, item.file_mode)
            self._complete_file(transaction_id, item.ordinal)
            journal.append(
                "APPLY_FILE_COMPLETED", {"ordinal": item.ordinal, "operation": item.operation}
            )
            self._journal_event(
                transaction_id,
                "APPLY_FILE_COMPLETED",
                {"ordinal": item.ordinal, "operation": item.operation},
            )
            self.events.publish(
                "apply_file_completed",
                project_id,
                {"transaction_id": transaction_id, "ordinal": item.ordinal},
            )
            if len(writes) > 0 and item is writes[0]:
                self._inject_fault(fault_injector, "after_first_file_operation")
        for item in [*deletions, *[row for row in files if row.operation == "RENAME"]]:
            relative = item.rename_source if item.operation == "RENAME" else item.relative_path
            if relative is None:
                continue
            target = safe_live_path(project_root, relative)
            verify_expected(target, item.base_digest, relative)
            durable_delete(target)
            journal.append(
                "APPLY_DELETE_COMPLETED", {"ordinal": item.ordinal, "relative_path": relative}
            )
            self._journal_event(
                transaction_id,
                "APPLY_DELETE_COMPLETED",
                {"ordinal": item.ordinal, "relative_path": relative},
            )

    def _complete_file(self, transaction_id: str, ordinal: int) -> None:
        with self.sessions.begin() as session:
            row = session.scalars(
                select(ApplyTransactionFile).where(
                    ApplyTransactionFile.transaction_id == transaction_id,
                    ApplyTransactionFile.ordinal == ordinal,
                )
            ).first()
            if row:
                row.operation_state = "COMPLETED"

    def _post_verify(
        self,
        project_id: str,
        transaction_id: str,
        project_root: Path,
        workspace: RepairWorkspace,
        journal: DurableJournal,
        *,
        fault_injector: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        self._transition(
            project_id,
            transaction_id,
            ApplyState.CAPTURING_LIVE_SOURCE,
            reason="apply.live_source_capture_started",
            evidence=[transaction_id],
        )
        journal.append("CAPTURING_LIVE_SOURCE")
        self.events.publish(
            "apply_post_verification_started", project_id, {"transaction_id": transaction_id}
        )
        post_snapshot = self.snapshots.create(
            project_id, creation_reason="POST_APPLY_VERIFY", force_fresh=True
        )
        self._transition(
            project_id,
            transaction_id,
            ApplyState.VERIFYING_LIVE,
            reason="apply.live_source_captured",
            evidence=[str(post_snapshot["id"])],
        )
        journal.append("VERIFYING_LIVE", {"snapshot_id": post_snapshot["id"]})
        policy = json.loads(workspace.validation_policy_json or "{}")
        results: list[dict[str, Any]] = []
        for ordinal, check in enumerate(checks_from_policy(policy)):
            result, error_code, evidence = RepairValidationService._run_check(project_root, check)
            results.append(
                {
                    "ordinal": ordinal,
                    "check_type": check.check_type,
                    "requirement": check.requirement,
                    "result": result,
                    "error_code": error_code,
                    "evidence": evidence,
                }
            )
        required_pass = all(
            item["result"] == "PASS" for item in results if item["requirement"] == "REQUIRED"
        ) and bool(results)
        journal.append(
            "POST_VERIFICATION_COMPLETED",
            {
                "snapshot_id": post_snapshot["id"],
                "evidence_digest": hashlib.sha256(canonical_json(results)).hexdigest(),
                "passed": required_pass,
            },
        )
        self._journal_event(
            transaction_id,
            "POST_VERIFICATION_COMPLETED",
            {"snapshot_id": post_snapshot["id"], "passed": required_pass},
        )
        if not required_pass:
            return self.rollback(
                project_id,
                transaction_id,
                reason="POST_APPLY_VERIFICATION_FAILED",
                fault_injector=fault_injector,
            )
        completed = datetime.now(UTC)
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.post_apply_snapshot_id = str(post_snapshot["id"])
            transaction.completed_at = completed
            transaction.updated_at = completed
            candidate = session.get(RepairCandidate, transaction.candidate_id)
            if candidate:
                candidate.state = "APPLIED"
                candidate.updated_at = completed
                workspace_row = session.get(RepairWorkspace, candidate.workspace_id)
                if workspace_row and workspace_row.regression_id:
                    regression = session.get(RegressionFinding, workspace_row.regression_id)
                    if regression:
                        regression.status = "RESOLVED"
                        regression.resolved_at = completed
        verification_digest = hashlib.sha256(canonical_json(results)).hexdigest()
        self._transition(
            project_id,
            transaction_id,
            ApplyState.COMMITTED,
            reason="apply.live_verification_passed",
            evidence=[str(post_snapshot["id"]), verification_digest],
        )
        journal.append("COMMITTED", {"post_apply_snapshot_id": post_snapshot["id"]})
        self._journal_event(transaction_id, "APPLY_COMMITTED")
        self.events.publish("apply_committed", project_id, {"transaction_id": transaction_id})
        return self.get(project_id, transaction_id)

    def rollback(
        self,
        project_id: str,
        transaction_id: str,
        *,
        reason: str = "USER_REQUESTED",
        fault_injector: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        with self.sessions() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            if transaction.state in {"COMMITTED", "ROLLED_BACK", "CANCELLED"}:
                if transaction.state == "ROLLED_BACK":
                    return self.get(project_id, transaction_id)
                raise SafeApplyServiceError("ROLLBACK_TRANSACTION_STATE_INVALID")
            if not transaction.safety_snapshot_id:
                raise SafeApplyServiceError("ROLLBACK_SAFETY_SNAPSHOT_MISSING")
            candidate = session.get(RepairCandidate, transaction.candidate_id)
            project = session.get(Project, project_id)
            if candidate is None or project is None:
                raise SafeApplyServiceError("ROLLBACK_CONTEXT_MISSING")
            files = list(
                session.scalars(
                    select(RepairCandidateFile)
                    .where(
                        RepairCandidateFile.candidate_id == candidate.id,
                        RepairCandidateFile.excluded.is_(False),
                    )
                    .order_by(RepairCandidateFile.ordinal)
                ).all()
            )
            project_root = self._project_root(project)
            safety_snapshot_id = transaction.safety_snapshot_id
            journal = DurableJournal.load(self.data_root / transaction.journal_relative_path)
        started = datetime.now(UTC)
        rollback_id = str(uuid.uuid4())
        # A process can terminate after restoring the first file but before the
        # rollback is complete.  On restart the durable transaction is already
        # ROLLING_BACK, so resume the idempotent restore instead of attempting
        # an invalid ROLLING_BACK -> ROLLING_BACK state transition.
        if transaction.state != ApplyState.ROLLING_BACK:
            self._transition(
                project_id,
                transaction_id,
                ApplyState.ROLLING_BACK,
                reason=f"apply.rollback.{reason.lower()}",
                evidence=[transaction.safety_snapshot_id],
            )
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.error_code = reason
            transaction.updated_at = started
            session.add(
                RollbackRecord(
                    id=rollback_id,
                    transaction_id=transaction_id,
                    status="RUNNING",
                    restored_paths_json="[]",
                    unresolved_paths_json="[]",
                    started_at=started,
                )
            )
        journal.append("ROLLING_BACK", {"reason": reason})
        self._journal_event(transaction_id, "ROLLBACK_STARTED", {"reason": reason})
        self.events.publish("rollback_started", project_id, {"transaction_id": transaction_id})
        restored: list[str] = []
        unresolved: list[str] = []
        store = SnapshotStore(self.data_root, project_id)
        safety = store.load_manifest(safety_snapshot_id)
        safety_entries = {entry.relative_path: entry for entry in safety.entries}
        for relative in self._affected_paths(files):
            try:
                target = safe_live_path(project_root, relative)
                expected_current: set[str | None] = {None}
                for item in files:
                    if item.relative_path == relative:
                        expected_current.update({item.candidate_digest, item.base_digest})
                    if item.rename_source == relative:
                        expected_current.add(item.base_digest)
                current = digest_path(target)
                if current not in expected_current:
                    raise PreflightError("ROLLBACK_EXTERNAL_CHANGE_DETECTED", relative)
                entry = safety_entries.get(relative)
                if entry is None:
                    durable_delete(target)
                    if digest_path(target) is not None:
                        raise ApplyOperationError("ROLLBACK_DELETE_VERIFICATION_FAILED", relative)
                else:
                    source = store.object_path(entry.blob_sha256)
                    atomic_copy(source, target, entry.blob_sha256, entry.file_mode)
                restored.append(relative)
                journal.append("ROLLBACK_FILE_COMPLETED", {"relative_path": relative})
                if len(restored) == 1:
                    self._inject_fault(
                        fault_injector,
                        "during_rollback_after_first_restore",
                    )
            except (PreflightError, ApplyOperationError, OSError):
                unresolved.append(relative)
                break
        verification_payload = {
            relative: digest_path(safe_live_path(project_root, relative)) for relative in restored
        }
        expected_payload = {
            relative: (safety_entries[relative].blob_sha256 if relative in safety_entries else None)
            for relative in restored
        }
        if verification_payload != expected_payload:
            unresolved.extend(
                path
                for path in restored
                if verification_payload.get(path) != expected_payload.get(path)
            )
        if unresolved:
            return self._recovery_required(
                project_id,
                transaction_id,
                project_root,
                journal,
                sorted(set(unresolved)),
                verification_payload,
                expected_payload,
                rollback_id,
            )
        restored_snapshot = self.snapshots.create(
            project_id, creation_reason="APPLY_ROLLBACK", force_fresh=True
        )
        digest = hashlib.sha256(canonical_json(verification_payload)).hexdigest()
        completed = datetime.now(UTC)
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.completed_at = completed
            transaction.updated_at = completed
            candidate = session.get(RepairCandidate, transaction.candidate_id)
            if candidate:
                candidate.state = "RETAINED_AFTER_ROLLBACK"
                candidate.updated_at = completed
            record = session.get(RollbackRecord, rollback_id)
            if record:
                record.status = "COMPLETED"
                record.restored_paths_json = _json(restored)
                record.verification_digest = digest
                record.completed_at = completed
        self._transition(
            project_id,
            transaction_id,
            ApplyState.ROLLED_BACK,
            reason="apply.rollback.byte_identity_verified",
            evidence=[rollback_id, digest, str(restored_snapshot["id"])],
        )
        journal.append("ROLLED_BACK", {"snapshot_id": restored_snapshot["id"]})
        self._journal_event(transaction_id, "ROLLBACK_COMPLETED")
        self.events.publish("rollback_completed", project_id, {"transaction_id": transaction_id})
        return self.get(project_id, transaction_id)

    def _recovery_required(
        self,
        project_id: str,
        transaction_id: str,
        project_root: Path,
        journal: DurableJournal,
        unresolved: list[str],
        current: dict[str, str | None],
        expected: dict[str, str | None],
        rollback_id: str,
    ) -> dict[str, Any]:
        self._transition(
            project_id,
            transaction_id,
            ApplyState.RECOVERY_REQUIRED,
            reason="apply.rollback.identity_not_proven",
            evidence=[rollback_id, *unresolved],
        )
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            transaction.error_code = "ROLLBACK_IDENTITY_NOT_PROVEN"
            transaction.updated_at = datetime.now(UTC)
            record = session.get(RollbackRecord, rollback_id)
            if record:
                record.status = "RECOVERY_REQUIRED"
                record.unresolved_paths_json = _json(unresolved)
                record.completed_at = datetime.now(UTC)
            alert_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            session.add(
                Alert(
                    id=alert_id,
                    project_id=project_id,
                    severity="CRITICAL",
                    category="RECOVERY",
                    title_key="alerts.recoveryRequired.title",
                    summary_key="alerts.recoveryRequired.summary",
                    parameters_json=_json(
                        {"transaction_id": transaction_id, "path_count": len(unresolved)}
                    ),
                    route_json=_json({"screen": "repair", "transaction_id": transaction_id}),
                    deduplication_key=f"recovery-required:{transaction_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
        journal.append("RECOVERY_REQUIRED", {"unresolved_paths": unresolved})
        bundle = self.recovery_bundles.create(
            project_id,
            transaction_id,
            project_root,
            {
                "transaction.json": self.get(project_id, transaction_id),
                "journal.json": journal.payload,
                "safety-snapshot.json": {"snapshot_id": journal.payload.get("safety_snapshot_id")},
                "affected-paths.json": unresolved,
                "current-digests.json": current,
                "expected-digests.json": expected,
                "diagnostics.json": {"error_code": "ROLLBACK_IDENTITY_NOT_PROVEN"},
            },
        )
        self._journal_event(transaction_id, "RECOVERY_REQUIRED", {"bundle_id": bundle["id"]})
        self.events.publish("recovery_required", project_id, {"transaction_id": transaction_id})
        self.events.publish("recovery_bundle_created", project_id, {"bundle_id": bundle["id"]})
        return self.get(project_id, transaction_id)

    def cancel(self, project_id: str, transaction_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            if transaction.state != "AWAITING_CONFIRMATION":
                raise SafeApplyServiceError("APPLY_CANCEL_NOT_SAFE")
            transaction.completed_at = datetime.now(UTC)
            transaction.updated_at = datetime.now(UTC)
        self._transition(
            project_id,
            transaction_id,
            ApplyState.CANCELLED,
            reason="apply.confirmation_cancelled",
        )
        return self.get(project_id, transaction_id)

    def recover_pending(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = list(
                session.scalars(
                    select(ApplyTransaction).where(ApplyTransaction.state.in_(self.ACTIVE_STATES))
                ).all()
            )
        results: list[dict[str, Any]] = []
        for row in rows:
            if row.state == "AWAITING_CONFIRMATION":
                try:
                    results.append(self.cancel(row.project_id, row.id))
                except SafeApplyServiceError:
                    continue
            elif row.state in {"PREFLIGHT", "SAFETY_SNAPSHOT", "JOURNAL_CREATED", "PREPARING"}:
                with self.sessions.begin() as session:
                    current = self._load_transaction(session, row.project_id, row.id)
                    current.state = "CANCELLED"
                    current.error_code = "ENGINE_RESTARTED_BEFORE_WRITE"
                    current.completed_at = datetime.now(UTC)
                    current.updated_at = datetime.now(UTC)
                results.append(self.get(row.project_id, row.id))
            elif row.state in {"WRITING", "CAPTURING_LIVE_SOURCE", "ROLLING_BACK"}:
                try:
                    results.append(self.rollback(row.project_id, row.id, reason="CRASH_RECOVERY"))
                except SafeApplyServiceError:
                    continue
            elif row.state == "VERIFYING_LIVE":
                with self.sessions.begin() as session:
                    current = self._load_transaction(session, row.project_id, row.id)
                    current.state = "RECOVERY_REQUIRED"
                    current.error_code = "POST_VERIFY_INTERRUPTED"
                    current.updated_at = datetime.now(UTC)
                results.append(self.get(row.project_id, row.id))
        return results

    def pending(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ApplyTransaction)
                .where(ApplyTransaction.state.in_([*self.ACTIVE_STATES, "RECOVERY_REQUIRED"]))
                .order_by(ApplyTransaction.created_at)
            ).all()
            identities = [(row.project_id, row.id) for row in rows]
        return [self.get(project_id, transaction_id) for project_id, transaction_id in identities]

    def create_recovery_bundle(self, project_id: str, transaction_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            project = session.get(Project, project_id)
            if project is None:
                raise SafeApplyServiceError("PROJECT_NOT_FOUND")
            project_root = self._project_root(project)
            journal = DurableJournal.load(self.data_root / transaction.journal_relative_path)
        return self.recovery_bundles.create(
            project_id,
            transaction_id,
            project_root,
            {
                "transaction.json": self.get(project_id, transaction_id),
                "journal.json": journal.payload,
                "safety-snapshot.json": {"snapshot_id": transaction.safety_snapshot_id},
                "affected-paths.json": [
                    item["relative_path"] for item in self.get(project_id, transaction_id)["files"]
                ],
                "diagnostics.json": {"error_code": transaction.error_code},
            },
        )

    def resume_verification(self, project_id: str, transaction_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            transaction = self._load_transaction(session, project_id, transaction_id)
            if transaction.state not in {"VERIFYING_LIVE", "RECOVERY_REQUIRED"}:
                raise SafeApplyServiceError("APPLY_RESUME_STATE_INVALID")
            candidate = session.get(RepairCandidate, transaction.candidate_id)
            project = session.get(Project, project_id)
            if candidate is None or project is None:
                raise SafeApplyServiceError("APPLY_CONTEXT_MISSING")
            workspace = session.get(RepairWorkspace, candidate.workspace_id)
            if workspace is None:
                raise SafeApplyServiceError("REPAIR_WORKSPACE_NOT_FOUND")
            project_root = self._project_root(project)
            journal = DurableJournal.load(self.data_root / transaction.journal_relative_path)
        return self._post_verify(project_id, transaction_id, project_root, workspace, journal)

    def get(self, project_id: str, transaction_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = self._load_transaction(session, project_id, transaction_id)
            files = session.scalars(
                select(ApplyTransactionFile)
                .where(ApplyTransactionFile.transaction_id == transaction_id)
                .order_by(ApplyTransactionFile.ordinal)
            ).all()
            events = session.scalars(
                select(ApplyJournalEvent)
                .where(ApplyJournalEvent.transaction_id == transaction_id)
                .order_by(ApplyJournalEvent.sequence)
            ).all()
            rollbacks = session.scalars(
                select(RollbackRecord)
                .where(RollbackRecord.transaction_id == transaction_id)
                .order_by(RollbackRecord.started_at)
            ).all()
            candidate = session.get(RepairCandidate, row.candidate_id)
            workspace = session.get(RepairWorkspace, candidate.workspace_id) if candidate else None
            regression = (
                session.get(RegressionFinding, workspace.regression_id)
                if workspace and workspace.regression_id
                else None
            )
            latest_rollback = rollbacks[-1] if rollbacks else None
            restored_paths = (
                json.loads(latest_rollback.restored_paths_json) if latest_rollback else []
            )
            unresolved_paths = (
                json.loads(latest_rollback.unresolved_paths_json) if latest_rollback else []
            )
            rollback_evidence = {
                "transaction_id": row.id,
                "reason": row.error_code,
                "paths_written": [
                    item.relative_path for item in files if item.operation_state == "COMPLETED"
                ],
                "paths_restored": restored_paths,
                "byte_identity_result": (
                    "VERIFIED"
                    if latest_rollback
                    and latest_rollback.status == "COMPLETED"
                    and latest_rollback.verification_digest
                    and not unresolved_paths
                    else "NOT_VERIFIED"
                ),
                "unrelated_path_result": "OUTSIDE_TRANSACTION_SCOPE_UNTOUCHED_BY_ENGINE",
                "candidate_state": candidate.state if candidate else "UNKNOWN",
                "regression_state": regression.status if regression else "NOT_LINKED",
                "live_source_identity_after_restore": (
                    {"snapshot_id": row.safety_snapshot_id} if row.state == "ROLLED_BACK" else None
                ),
                "pending_recovery": row.state == "RECOVERY_REQUIRED",
            }
            return {
                "id": row.id,
                "project_id": row.project_id,
                "candidate_id": row.candidate_id,
                "validation_id": row.validation_id,
                "state": row.state,
                "expected_source_snapshot_id": row.expected_source_snapshot_id,
                "expected_source_manifest_digest": row.expected_source_manifest_digest,
                "safety_snapshot_id": row.safety_snapshot_id,
                "post_apply_snapshot_id": row.post_apply_snapshot_id,
                "confirmation_expires_at": row.confirmation_expires_at.isoformat(),
                "confirmation_used": row.confirmation_used_at is not None,
                "journal_relative_path": row.journal_relative_path,
                "error_code": row.error_code,
                "files": [
                    {
                        "ordinal": item.ordinal,
                        "relative_path": item.relative_path,
                        "operation": item.operation,
                        "operation_state": item.operation_state,
                        "original_digest": item.original_digest,
                        "candidate_digest": item.candidate_digest,
                    }
                    for item in files
                ],
                "events": [
                    {
                        "sequence": item.sequence,
                        "event_type": item.event_type,
                        "details": json.loads(item.details_json),
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in events
                ],
                "rollbacks": [
                    {
                        "id": item.id,
                        "status": item.status,
                        "restored_paths": json.loads(item.restored_paths_json),
                        "unresolved_paths": json.loads(item.unresolved_paths_json),
                        "verification_digest": item.verification_digest,
                    }
                    for item in rollbacks
                ],
                "rollback_evidence": rollback_evidence,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }

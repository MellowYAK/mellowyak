from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    RepairCandidate,
    RepairCandidateValidation,
    RepairCandidateValidationItem,
    RepairWorkspace,
)
from mellowyak_engine.repair_candidates.manifest import (
    CandidateManifestError,
    safe_join,
    scan_workspace,
)
from mellowyak_engine.repair_validation.policy import ValidationCheck, checks_from_policy
from mellowyak_engine.runtime_adapters import SafeProcessRunner
from mellowyak_engine.snapshots.store import canonical_json


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class RepairValidationServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RepairValidationService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self._cancelled: set[str] = set()

    def _load(
        self, session: Session, project_id: str, candidate_id: str
    ) -> tuple[RepairCandidate, RepairWorkspace, Path]:
        candidate = session.get(RepairCandidate, candidate_id)
        if candidate is None or candidate.project_id != project_id:
            raise RepairValidationServiceError("REPAIR_CANDIDATE_NOT_FOUND")
        workspace = session.get(RepairWorkspace, candidate.workspace_id)
        if workspace is None or workspace.deleted_at is not None:
            raise RepairValidationServiceError("REPAIR_WORKSPACE_NOT_FOUND")
        root = (self.data_root / workspace.workspace_relative_path / "current").resolve(strict=True)
        expected = (self.data_root / "projects" / project_id / "repair-workspaces").resolve()
        try:
            root.relative_to(expected)
        except ValueError as error:
            raise RepairValidationServiceError("REPAIR_WORKSPACE_PATH_INVALID") from error
        return candidate, workspace, root

    @staticmethod
    def _run_check(root: Path, check: ValidationCheck) -> tuple[str, str | None, dict[str, Any]]:
        if check.check_type == "PROCESS" and check.executable:
            try:
                execution = SafeProcessRunner().run(
                    executable=check.executable,
                    argv=list(check.argv),
                    project_root=root,
                    relative_working_directory=check.cwd,
                    environment_names=[],
                    timeout_seconds=120,
                    output_limit_bytes=32_768,
                )
            except (OSError, ValueError) as error:
                return (
                    "FAIL",
                    "VALIDATION_PROCESS_UNAVAILABLE",
                    {"check_id": check.check_id, "error_type": type(error).__name__},
                )
            stdout_matches = (
                check.stdout_contains is None or check.stdout_contains in execution.stdout
            )
            passed = (
                not execution.cancelled
                and not execution.timed_out
                and execution.exit_code == check.expected_exit_code
                and stdout_matches
            )
            return (
                "PASS" if passed else "FAIL",
                None if passed else "VALIDATION_PROCESS_EXPECTATION_NOT_MET",
                {
                    "check_id": check.check_id,
                    "exit_code": execution.exit_code,
                    "duration_ms": round(execution.duration_seconds * 1000, 3),
                    "timed_out": execution.timed_out,
                    "stdout_bytes": len(execution.stdout.encode("utf-8", errors="replace")),
                    "stderr_bytes": len(execution.stderr.encode("utf-8", errors="replace")),
                },
            )
        if check.check_type == "FILE_CONTAINS" and check.path and check.expected is not None:
            try:
                path = safe_join(root, check.path, allow_missing=False)
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError, CandidateManifestError):
                return "FAIL", "VALIDATION_FILE_UNREADABLE", {"check_id": check.check_id}
            passed = check.expected in content
            return (
                "PASS" if passed else "FAIL",
                None if passed else "VALIDATION_EXPECTATION_NOT_MET",
                {"check_id": check.check_id, "path": check.path},
            )
        if check.check_type == "FILE_NOT_CONTAINS" and check.path and check.expected is not None:
            try:
                path = safe_join(root, check.path, allow_missing=False)
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError, CandidateManifestError):
                return "FAIL", "VALIDATION_FILE_UNREADABLE", {"check_id": check.check_id}
            passed = check.expected not in content
            return (
                "PASS" if passed else "FAIL",
                None if passed else "VALIDATION_FORBIDDEN_CONTENT_FOUND",
                {"check_id": check.check_id, "path": check.path},
            )
        if check.check_type == "FILE_EXISTS" and check.path:
            try:
                passed = safe_join(root, check.path).is_file()
            except CandidateManifestError:
                passed = False
            return (
                "PASS" if passed else "FAIL",
                None if passed else "VALIDATION_FILE_MISSING",
                {"check_id": check.check_id, "path": check.path},
            )
        return "INCONCLUSIVE", "VALIDATION_RUNTIME_REQUIRES_REVIEW", {"check_id": check.check_id}

    def validate(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        validation_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            candidate, workspace, root = self._load(session, project_id, candidate_id)
            if candidate.state not in {"DRAFT", "VALIDATION_FAILED", "STALE"}:
                raise RepairValidationServiceError("REPAIR_CANDIDATE_STATE_INVALID")
            if candidate.file_count == 0:
                raise RepairValidationServiceError("REPAIR_CANDIDATE_EMPTY")
            if candidate.binary_count:
                raise RepairValidationServiceError("REPAIR_CANDIDATE_BINARY_BLOCKED")
            try:
                _, current_digest = scan_workspace(root)
            except CandidateManifestError as error:
                raise RepairValidationServiceError(error.code) from error
            if current_digest != candidate.workspace_manifest_digest:
                candidate.state = "STALE"
                candidate.updated_at = now
                self.events.publish("candidate_stale", project_id, {"candidate_id": candidate_id})
                raise RepairValidationServiceError("REPAIR_CANDIDATE_STALE")
            policy = json.loads(workspace.validation_policy_json or "{}")
            candidate.state = "VALIDATING"
            candidate.updated_at = now
            row = RepairCandidateValidation(
                id=validation_id,
                project_id=project_id,
                candidate_id=candidate_id,
                candidate_digest=candidate.candidate_digest,
                workspace_manifest_digest=current_digest,
                runtime_profile_versions_json=workspace.runtime_profile_versions_json,
                status="RUNNING",
                started_at=now,
                limitations_json="[]",
            )
            session.add(row)
        self.events.publish(
            "candidate_validation_started",
            project_id,
            {"candidate_id": candidate_id, "validation_id": validation_id},
        )
        results: list[dict[str, Any]] = []
        checks = checks_from_policy(policy)
        for ordinal, check in enumerate(checks):
            if validation_id in self._cancelled:
                results.append(
                    {
                        "ordinal": ordinal,
                        "check_type": check.check_type,
                        "requirement": check.requirement,
                        "status": "COMPLETED",
                        "result": "CANCELLED",
                        "duration_ms": 0.0,
                        "evidence": {"check_id": check.check_id},
                        "error_code": "VALIDATION_CANCELLED",
                    }
                )
                break
            started = time.monotonic()
            result, error_code, evidence = self._run_check(root, check)
            results.append(
                {
                    "ordinal": ordinal,
                    "check_type": check.check_type,
                    "requirement": check.requirement,
                    "status": "COMPLETED",
                    "result": result,
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                    "evidence": evidence,
                    "error_code": error_code,
                }
            )
            self.events.publish(
                "candidate_validation_step",
                project_id,
                {"validation_id": validation_id, "ordinal": ordinal, "result": result},
            )
        try:
            _, final_workspace_digest = scan_workspace(root)
        except CandidateManifestError as error:
            raise RepairValidationServiceError(error.code) from error
        required_pass = all(
            item["result"] == "PASS" for item in results if item["requirement"] == "REQUIRED"
        ) and bool(results)
        stale = final_workspace_digest != current_digest
        status = "STALE" if stale else ("PASSED" if required_pass else "FAILED")
        evidence_digest = hashlib.sha256(canonical_json(results)).hexdigest()
        completed = datetime.now(UTC)
        with self.sessions.begin() as session:
            validation = session.get(RepairCandidateValidation, validation_id)
            candidate = session.get(RepairCandidate, candidate_id)
            if validation is None or candidate is None:
                raise RepairValidationServiceError("VALIDATION_STATE_LOST")
            validation.status = status
            validation.completed_at = completed
            validation.evidence_digest = evidence_digest
            validation.limitations_json = _json(
                sorted({item["error_code"] for item in results if item["error_code"]})
            )
            for item in results:
                session.add(
                    RepairCandidateValidationItem(
                        id=str(uuid.uuid4()),
                        validation_id=validation_id,
                        ordinal=item["ordinal"],
                        check_type=item["check_type"],
                        requirement=item["requirement"],
                        status=item["status"],
                        result=item["result"],
                        duration_ms=item["duration_ms"],
                        evidence_json=_json(item["evidence"]),
                        error_code=item["error_code"],
                    )
                )
            candidate.state = (
                "STALE" if stale else ("VALIDATED" if required_pass else "VALIDATION_FAILED")
            )
            candidate.updated_at = completed
        event = (
            "candidate_validation_passed" if status == "PASSED" else "candidate_validation_failed"
        )
        self.events.publish(
            event, project_id, {"candidate_id": candidate_id, "validation_id": validation_id}
        )
        return self.get(project_id, validation_id)

    def cancel(self, project_id: str, candidate_id: str) -> dict[str, str]:
        with self.sessions() as session:
            candidate = session.get(RepairCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise RepairValidationServiceError("REPAIR_CANDIDATE_NOT_FOUND")
            validation = session.scalars(
                select(RepairCandidateValidation)
                .where(
                    RepairCandidateValidation.candidate_id == candidate_id,
                    RepairCandidateValidation.status == "RUNNING",
                )
                .order_by(RepairCandidateValidation.started_at.desc())
            ).first()
            if validation:
                self._cancelled.add(validation.id)
        return {"status": "CANCELLATION_REQUESTED"}

    def get(self, project_id: str, validation_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RepairCandidateValidation, validation_id)
            if row is None or row.project_id != project_id:
                raise RepairValidationServiceError("REPAIR_VALIDATION_NOT_FOUND")
            items = session.scalars(
                select(RepairCandidateValidationItem)
                .where(RepairCandidateValidationItem.validation_id == validation_id)
                .order_by(RepairCandidateValidationItem.ordinal)
            ).all()
            return {
                "id": row.id,
                "project_id": row.project_id,
                "candidate_id": row.candidate_id,
                "candidate_digest": row.candidate_digest,
                "workspace_manifest_digest": row.workspace_manifest_digest,
                "runtime_profile_versions": json.loads(row.runtime_profile_versions_json),
                "status": row.status,
                "evidence_digest": row.evidence_digest,
                "limitations": json.loads(row.limitations_json),
                "started_at": row.started_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "items": [
                    {
                        "ordinal": item.ordinal,
                        "check_type": item.check_type,
                        "requirement": item.requirement,
                        "status": item.status,
                        "result": item.result,
                        "duration_ms": item.duration_ms,
                        "evidence": json.loads(item.evidence_json),
                        "error_code": item.error_code,
                    }
                    for item in items
                ],
            }

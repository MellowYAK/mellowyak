from __future__ import annotations

import dataclasses
import hashlib
import ipaddress
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Project,
    RuntimeEvent,
    RuntimeProfile,
    RuntimeProfileVersion,
)
from mellowyak_engine.db.models import (
    RuntimeDetection as RuntimeDetectionRow,
)
from mellowyak_engine.db.models import (
    RuntimeInstance as RuntimeInstanceRow,
)
from mellowyak_engine.runtime_adapters import (
    DEFAULT_RUNTIME_ADAPTERS,
    RuntimeInstance,
    RuntimeProfileSpec,
    adapter_for_runtime,
)
from mellowyak_engine.runtime_adapters.base import (
    is_safe_environment_name,
    resolve_working_directory,
    validate_argv,
)
from mellowyak_engine.runtime_profiles.detection import RuntimeDetectionService

_EXECUTION_MODES = frozenset({"MANAGED", "EXTERNAL", "MANUAL"})
_NETWORK_POLICIES = frozenset({"LOOPBACK_ONLY"})
_DENIED_EXECUTABLES = frozenset(
    {
        "bash",
        "cmd",
        "cmd.exe",
        "csh",
        "dash",
        "fish",
        "nu",
        "powershell",
        "powershell.exe",
        "pwsh",
        "sh",
        "tcsh",
        "zsh",
    }
)
_SENSITIVE_FIELD = re.compile(
    r"token|secret|password|passwd|cookie|authorization|credential|api[_-]?key", re.I
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _safe_dataclass(value: Any) -> dict[str, Any]:
    result = dataclasses.asdict(value)
    for key in list(result):
        if key.startswith("_"):
            result.pop(key, None)
    for key, item in list(result.items()):
        if isinstance(item, Path):
            result[key] = str(item)
    return result


def _contains_sensitive_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _SENSITIVE_FIELD.search(str(key)) or _contains_sensitive_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_field(item) for item in value)
    return False


def _is_loopback_url(value: str) -> bool:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password or parsed.query:
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


class RuntimeProfileServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RuntimeProfileService:
    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events
        self.adapters = DEFAULT_RUNTIME_ADAPTERS
        self.detector = RuntimeDetectionService(self.adapters)
        self._managed: dict[str, tuple[Any, RuntimeProfileSpec, RuntimeInstance]] = {}

    @staticmethod
    def _project(session: Session, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise RuntimeProfileServiceError("PROJECT_NOT_FOUND")
        return project

    def detect(self, project_id: str) -> dict[str, Any]:
        started = datetime.now(UTC)
        detection_id = str(uuid.uuid4())
        self.events.publish("runtime_detection_started", project_id, {"detection_id": detection_id})
        with self.sessions() as session:
            project = self._project(session, project_id)
            root = Path(project.canonical_root_path or project.root_path)
        error_code = None
        try:
            report = self.detector.detect(root)
            candidates = []
            for item in report.detections:
                candidate = _safe_dataclass(item)
                candidate["confidence"] = str(item.confidence)
                candidate["markers"] = list(item.markers)
                candidate["reasons"] = list(item.reasons)
                candidate["limitations"] = list(item.limitations)
                candidate["metadata"] = dict(item.metadata)
                candidates.append(candidate)
            for failure in report.failures:
                candidates.append(
                    {
                        "runtime_type": "UNKNOWN",
                        "adapter_name": failure.adapter_name,
                        "confidence": "LOW",
                        "reasons": [],
                        "limitations": [failure.reason],
                    }
                )
            status = "COMPLETED"
        except (OSError, ValueError) as error:
            candidates = []
            status = "FAILED"
            error_code = type(error).__name__[:120]
        completed = datetime.now(UTC)
        with self.sessions.begin() as session:
            self._project(session, project_id)
            row = RuntimeDetectionRow(
                id=detection_id,
                project_id=project_id,
                status=status,
                candidates_json=_json(candidates),
                started_at=started,
                completed_at=completed,
                error_code=error_code,
            )
            session.add(row)
        self.events.publish(
            "runtime_detected",
            project_id,
            {"detection_id": detection_id, "candidate_count": len(candidates)},
        )
        return {
            "id": detection_id,
            "project_id": project_id,
            "status": status,
            "candidates": candidates,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "error_code": error_code,
        }

    def create_or_version(
        self,
        project_id: str,
        *,
        display_name: str,
        runtime_type: str,
        primary: bool,
        execution_mode: str,
        executable_reference: str | None,
        argv: list[str],
        relative_working_directory: str,
        runtime_version: str | None,
        dependency_fingerprint: str | None,
        health_definition: dict[str, Any],
        expected_ports: list[int],
        test_definitions: list[dict[str, Any]],
        environment_schema: list[str],
        network_policy: str,
        limitations: list[str],
        approved: bool,
    ) -> dict[str, Any]:
        if not isinstance(display_name, str):
            raise RuntimeProfileServiceError("RUNTIME_DISPLAY_NAME_REQUIRED")
        if not isinstance(runtime_type, str):
            raise RuntimeProfileServiceError("RUNTIME_ADAPTER_UNAVAILABLE")
        if not isinstance(execution_mode, str):
            raise RuntimeProfileServiceError("RUNTIME_EXECUTION_MODE_INVALID")
        if not isinstance(network_policy, str):
            raise RuntimeProfileServiceError("RUNTIME_NETWORK_POLICY_DENIED")
        if not isinstance(relative_working_directory, str):
            raise RuntimeProfileServiceError("RUNTIME_WORKING_DIRECTORY_INVALID")
        if not isinstance(health_definition, dict):
            raise RuntimeProfileServiceError("RUNTIME_HEALTH_DEFINITION_INVALID")
        if not isinstance(test_definitions, list) or any(
            not isinstance(item, dict) for item in test_definitions
        ):
            raise RuntimeProfileServiceError("RUNTIME_TEST_DEFINITION_INVALID")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) for item in limitations
        ):
            raise RuntimeProfileServiceError("RUNTIME_LIMITATIONS_INVALID")
        normalized_type = runtime_type.upper().replace("-", "_")
        normalized_name = display_name.strip()
        normalized_mode = execution_mode.strip().upper()
        normalized_network_policy = network_policy.strip().upper()
        if not normalized_name:
            raise RuntimeProfileServiceError("RUNTIME_DISPLAY_NAME_REQUIRED")
        if adapter_for_runtime(normalized_type, self.adapters) is None:
            raise RuntimeProfileServiceError("RUNTIME_ADAPTER_UNAVAILABLE")
        if normalized_mode not in _EXECUTION_MODES:
            raise RuntimeProfileServiceError("RUNTIME_EXECUTION_MODE_INVALID")
        if normalized_network_policy not in _NETWORK_POLICIES:
            raise RuntimeProfileServiceError("RUNTIME_NETWORK_POLICY_DENIED")
        if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
            raise RuntimeProfileServiceError("RUNTIME_ARGV_INVALID")
        try:
            validate_argv(argv)
        except ValueError as error:
            raise RuntimeProfileServiceError("RUNTIME_ARGV_INVALID") from error
        if executable_reference is not None:
            if not isinstance(executable_reference, str) or "\x00" in executable_reference:
                raise RuntimeProfileServiceError("RUNTIME_EXECUTABLE_INVALID")
            if Path(executable_reference.strip()).name.casefold() in _DENIED_EXECUTABLES:
                raise RuntimeProfileServiceError("RUNTIME_SHELL_EXECUTABLE_DENIED")
        if normalized_mode == "MANAGED" and not (executable_reference or "").strip():
            raise RuntimeProfileServiceError("RUNTIME_EXECUTABLE_REQUIRED")
        if not isinstance(environment_schema, list) or any(
            not isinstance(name, str) or not is_safe_environment_name(name)
            for name in environment_schema
        ):
            raise RuntimeProfileServiceError("RUNTIME_ENVIRONMENT_SECRET_NAME_DENIED")
        if not isinstance(expected_ports, list) or any(
            isinstance(port, bool) or not isinstance(port, int) or port < 1 or port > 65535
            for port in expected_ports
        ):
            raise RuntimeProfileServiceError("RUNTIME_EXPECTED_PORT_INVALID")
        if _contains_sensitive_field(health_definition) or _contains_sensitive_field(
            test_definitions
        ):
            raise RuntimeProfileServiceError("RUNTIME_SECRET_FIELD_DENIED")
        health_url = health_definition.get("url")
        if health_url is not None and (
            not isinstance(health_url, str) or not _is_loopback_url(health_url)
        ):
            raise RuntimeProfileServiceError("RUNTIME_LOOPBACK_HTTP_REQUIRED")
        if dependency_fingerprint is not None and not re.fullmatch(
            r"[0-9a-fA-F]{64}", dependency_fingerprint
        ):
            raise RuntimeProfileServiceError("RUNTIME_DEPENDENCY_FINGERPRINT_INVALID")
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            project_root = Path(project.canonical_root_path or project.root_path)
            try:
                resolve_working_directory(project_root, relative_working_directory)
            except (FileNotFoundError, NotADirectoryError, OSError, ValueError) as error:
                raise RuntimeProfileServiceError("RUNTIME_WORKING_DIRECTORY_INVALID") from error
            profile = session.scalars(
                select(RuntimeProfile).where(
                    RuntimeProfile.project_id == project_id,
                    RuntimeProfile.display_name == normalized_name[:240],
                )
            ).first()
            if primary:
                session.execute(
                    update(RuntimeProfile)
                    .where(RuntimeProfile.project_id == project_id)
                    .values(primary=False)
                )
            if profile is None:
                profile = RuntimeProfile(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    display_name=normalized_name[:240],
                    current_version_id="PENDING",
                    primary=primary,
                    status="CONFIGURED",
                    created_at=now,
                    updated_at=now,
                )
                session.add(profile)
                session.flush()
                version_number = 1
            else:
                version_number = (
                    int(
                        session.scalar(
                            select(func.max(RuntimeProfileVersion.version_number)).where(
                                RuntimeProfileVersion.profile_id == profile.id
                            )
                        )
                        or 0
                    )
                    + 1
                )
                profile.primary = primary
                profile.updated_at = now
                profile.status = "CONFIGURED"
            version_id = str(uuid.uuid4())
            adapter = adapter_for_runtime(normalized_type, self.adapters)
            session.add(
                RuntimeProfileVersion(
                    id=version_id,
                    profile_id=profile.id,
                    project_id=project_id,
                    version_number=version_number,
                    runtime_type=normalized_type,
                    adapter_version=str(adapter.version if adapter else "1"),
                    execution_mode=normalized_mode,
                    executable_reference=(executable_reference or "").strip() or None,
                    argv_json=_json(argv),
                    relative_working_directory=relative_working_directory,
                    runtime_version=runtime_version,
                    dependency_fingerprint=dependency_fingerprint
                    or hashlib.sha256(
                        _json(
                            {
                                "runtime_type": normalized_type,
                                "executable": executable_reference,
                                "argv": argv,
                            }
                        ).encode()
                    ).hexdigest(),
                    health_definition_json=_json(health_definition),
                    expected_ports_json=_json(expected_ports),
                    test_definitions_json=_json(test_definitions),
                    environment_schema_json=_json(sorted(set(environment_schema))),
                    network_policy=normalized_network_policy,
                    limitations_json=_json(limitations),
                    approved_at=now if approved else None,
                    detected_at=now,
                    created_at=now,
                )
            )
            profile.current_version_id = version_id
            project.runtime_setup_status = "READY_WITH_LIMITS" if limitations else "READY"
            project.updated_at = now
            profile_id = profile.id
        return self.get(project_id, profile_id)

    @staticmethod
    def _version(row: RuntimeProfileVersion) -> dict[str, Any]:
        return {
            "id": row.id,
            "version_number": row.version_number,
            "runtime_type": row.runtime_type,
            "adapter_version": row.adapter_version,
            "execution_mode": row.execution_mode,
            "executable_reference": row.executable_reference,
            "argv": _load(row.argv_json, []),
            "relative_working_directory": row.relative_working_directory,
            "runtime_version": row.runtime_version,
            "dependency_fingerprint": row.dependency_fingerprint,
            "health_definition": _load(row.health_definition_json, {}),
            "expected_ports": _load(row.expected_ports_json, []),
            "test_definitions": _load(row.test_definitions_json, []),
            "environment_schema": _load(row.environment_schema_json, []),
            "network_policy": row.network_policy,
            "limitations": _load(row.limitations_json, []),
            "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            "detected_at": row.detected_at.isoformat() if row.detected_at else None,
            "created_at": row.created_at.isoformat(),
        }

    def _serialize(self, session: Session, profile: RuntimeProfile) -> dict[str, Any]:
        versions = session.scalars(
            select(RuntimeProfileVersion)
            .where(RuntimeProfileVersion.profile_id == profile.id)
            .order_by(RuntimeProfileVersion.version_number.desc())
        ).all()
        current = next(row for row in versions if row.id == profile.current_version_id)
        return {
            "id": profile.id,
            "project_id": profile.project_id,
            "display_name": profile.display_name,
            "current_version_id": profile.current_version_id,
            "primary": profile.primary,
            "status": profile.status,
            "current_version": self._version(current),
            "versions": [self._version(row) for row in versions],
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }

    def list(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(RuntimeProfile)
                .where(RuntimeProfile.project_id == project_id)
                .order_by(RuntimeProfile.primary.desc(), RuntimeProfile.created_at)
            ).all()
            return [self._serialize(session, row) for row in rows]

    def get(self, project_id: str, profile_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            row = session.get(RuntimeProfile, profile_id)
            if row is None or row.project_id != project_id:
                raise RuntimeProfileServiceError("RUNTIME_PROFILE_NOT_FOUND")
            return self._serialize(session, row)

    def _spec(
        self, session: Session, project_id: str, profile_id: str
    ) -> tuple[RuntimeProfile, RuntimeProfileVersion, RuntimeProfileSpec]:
        project = self._project(session, project_id)
        profile = session.get(RuntimeProfile, profile_id)
        if profile is None or profile.project_id != project_id:
            raise RuntimeProfileServiceError("RUNTIME_PROFILE_NOT_FOUND")
        version = session.get(RuntimeProfileVersion, profile.current_version_id)
        if version is None:
            raise RuntimeProfileServiceError("RUNTIME_PROFILE_VERSION_NOT_FOUND")
        health = _load(version.health_definition_json, {})
        return (
            profile,
            version,
            RuntimeProfileSpec(
                profile_id=profile.id,
                project_root=Path(project.canonical_root_path or project.root_path),
                runtime_type=version.runtime_type,
                executable=version.executable_reference or "",
                argv=tuple(_load(version.argv_json, [])),
                relative_working_directory=version.relative_working_directory,
                approved=version.approved_at is not None,
                execution_mode=version.execution_mode,
                environment_names=tuple(_load(version.environment_schema_json, [])),
                expected_ports=tuple(_load(version.expected_ports_json, [])),
                health_url=health.get("url") if isinstance(health.get("url"), str) else None,
                network_policy=version.network_policy,
            ),
        )

    def validate(self, project_id: str, profile_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            profile, version, spec = self._spec(session, project_id, profile_id)
        adapter = adapter_for_runtime(version.runtime_type, self.adapters)
        if adapter is None:
            raise RuntimeProfileServiceError("RUNTIME_ADAPTER_UNAVAILABLE")
        validation = adapter.validate(spec)
        availability = adapter.availability(spec) if validation.valid else None
        status = "AVAILABLE" if availability and availability.available else "UNAVAILABLE"
        with self.sessions.begin() as session:
            row = session.get(RuntimeProfile, profile.id)
            project = session.get(Project, project_id)
            if row:
                row.status = status
                row.updated_at = datetime.now(UTC)
            if project:
                project.runtime_setup_status = (
                    "READY" if status == "AVAILABLE" else "READY_WITH_LIMITS"
                )
            session.add(
                RuntimeEvent(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    profile_id=profile_id,
                    event_type="PROFILE_VALIDATED",
                    severity="INFO" if validation.valid else "WARNING",
                    sanitized_details_json=_json(
                        {
                            "valid": validation.valid,
                            "errors": list(validation.errors),
                            "warnings": list(validation.warnings),
                            "available": bool(availability and availability.available),
                        }
                    ),
                    created_at=datetime.now(UTC),
                )
            )
        self.events.publish(
            "runtime_profile_validated",
            project_id,
            {"profile_id": profile_id, "status": status},
        )
        response = self.get(project_id, profile_id)
        response["validation"] = {
            "valid": validation.valid,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
            "available": bool(availability and availability.available),
            "reason": availability.reason if availability else None,
        }
        return response

    def start(self, project_id: str, profile_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            profile, version, spec = self._spec(session, project_id, profile_id)
        adapter = adapter_for_runtime(version.runtime_type, self.adapters)
        if adapter is None:
            raise RuntimeProfileServiceError("RUNTIME_ADAPTER_UNAVAILABLE")
        correlation_id = uuid.uuid4().hex
        result = adapter.start(spec, correlation_id)
        if result.instance is None:
            self.events.publish(
                "runtime_failed",
                project_id,
                {"profile_id": profile_id, "reason": result.reason},
            )
            raise RuntimeProfileServiceError(result.reason or "RUNTIME_START_FAILED")
        instance = result.instance
        row_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            session.add(
                RuntimeInstanceRow(
                    id=row_id,
                    project_id=project_id,
                    profile_id=profile_id,
                    profile_version_id=version.id,
                    correlation_id=correlation_id,
                    status="RUNNING",
                    process_id=instance.pid,
                    started_at=datetime.now(UTC),
                    sanitized_observation_json="{}",
                )
            )
            row = session.get(RuntimeProfile, profile.id)
            if row:
                row.status = "RUNNING"
        self._managed[profile_id] = (adapter, spec, instance)
        self.events.publish(
            "runtime_started",
            project_id,
            {"profile_id": profile_id, "instance_id": row_id},
        )
        return self.get_instance(project_id, row_id)

    @staticmethod
    def _instance(row: RuntimeInstanceRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "profile_id": row.profile_id,
            "profile_version_id": row.profile_version_id,
            "correlation_id": row.correlation_id,
            "status": row.status,
            "process_id": row.process_id,
            "started_at": row.started_at.isoformat(),
            "stopped_at": row.stopped_at.isoformat() if row.stopped_at else None,
            "exit_code": row.exit_code,
            "observation": _load(row.sanitized_observation_json, {}),
        }

    def instances(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(RuntimeInstanceRow)
                .where(RuntimeInstanceRow.project_id == project_id)
                .order_by(RuntimeInstanceRow.started_at.desc())
                .limit(100)
            ).all()
            return [self._instance(row) for row in rows]

    def get_instance(self, project_id: str, instance_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RuntimeInstanceRow, instance_id)
            if row is None or row.project_id != project_id:
                raise RuntimeProfileServiceError("RUNTIME_INSTANCE_NOT_FOUND")
            return self._instance(row)

    def stop(self, project_id: str, profile_id: str) -> dict[str, Any]:
        managed = self._managed.pop(profile_id, None)
        with self.sessions.begin() as session:
            profile = session.get(RuntimeProfile, profile_id)
            if profile is None or profile.project_id != project_id:
                raise RuntimeProfileServiceError("RUNTIME_PROFILE_NOT_FOUND")
            instance_row = session.scalars(
                select(RuntimeInstanceRow)
                .where(
                    RuntimeInstanceRow.project_id == project_id,
                    RuntimeInstanceRow.profile_id == profile_id,
                    RuntimeInstanceRow.status == "RUNNING",
                )
                .order_by(RuntimeInstanceRow.started_at.desc())
                .limit(1)
            ).first()
            exit_code = None
            if managed:
                adapter, _spec, instance = managed
                result = adapter.stop(instance)
                exit_code = result.exit_code
            if instance_row:
                instance_row.status = "STOPPED"
                instance_row.exit_code = exit_code
                instance_row.stopped_at = datetime.now(UTC)
            profile.status = "AVAILABLE"
            response = (
                self._instance(instance_row)
                if instance_row
                else {
                    "id": "",
                    "project_id": project_id,
                    "profile_id": profile_id,
                    "profile_version_id": profile.current_version_id,
                    "correlation_id": "",
                    "status": "STOPPED",
                    "process_id": None,
                    "started_at": datetime.now(UTC).isoformat(),
                    "stopped_at": datetime.now(UTC).isoformat(),
                    "exit_code": exit_code,
                    "observation": {},
                }
            )
        self.events.publish("runtime_stopped", project_id, {"profile_id": profile_id})
        return response

    def recover(self) -> int:
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(RuntimeInstanceRow).where(RuntimeInstanceRow.status == "RUNNING")
            ).all()
            for row in rows:
                row.status = "INTERRUPTED"
                row.stopped_at = datetime.now(UTC)
                row.process_id = None
            return len(rows)

    def stop_all(self) -> None:
        for profile_id, (_adapter, _spec, _instance) in list(self._managed.items()):
            with self.sessions() as session:
                profile = session.get(RuntimeProfile, profile_id)
                project_id = profile.project_id if profile else None
            if project_id:
                try:
                    self.stop(project_id, profile_id)
                except Exception:
                    pass

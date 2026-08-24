from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, delete, func, inspect, select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Alert,
    ApplicationPreference,
    EvidenceArtifact,
    EvidenceBundle,
    NotificationPreference,
    Project,
    ProjectDisconnectionRecord,
    ProjectLifecycleEvent,
    ProjectNotificationPreference,
    ProtectedBehavior,
    QuietModeState,
    RegressionFinding,
    RuntimeConfiguration,
)


class ProductizationError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


class ProductizationService:
    """Local-only desktop product state; never reads or mutates repository contents."""

    def __init__(self, sessions: sessionmaker, data_root: Path, events: LocalEventBus) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        now = _now()
        with self.sessions.begin() as session:
            if session.get(NotificationPreference, 1) is None:
                session.add(NotificationPreference(id=1, updated_at=now))
            if session.get(QuietModeState, 1) is None:
                session.add(QuietModeState(id=1, updated_at=now))
            if session.get(ApplicationPreference, 1) is None:
                session.add(ApplicationPreference(id=1, updated_at=now))

    @staticmethod
    def _alert(row: Alert) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "change_id": row.change_id,
            "behavior_id": row.behavior_id,
            "regression_id": row.regression_id,
            "gate_id": row.gate_id,
            "severity": row.severity,
            "category": row.category,
            "title_key": row.title_key,
            "summary_key": row.summary_key,
            "parameters": json.loads(row.parameters_json),
            "route": json.loads(row.route_json),
            "read": row.read_at is not None,
            "resolved": row.resolved_at is not None,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

    def create_alert(
        self,
        *,
        project_id: str | None,
        category: str,
        severity: str,
        title_key: str,
        summary_key: str,
        deduplication_key: str,
        route: dict[str, Any],
        parameters: dict[str, Any] | None = None,
        change_id: str | None = None,
        behavior_id: str | None = None,
        regression_id: str | None = None,
        gate_id: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            if project_id and session.get(Project, project_id) is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            row = session.scalar(select(Alert).where(Alert.deduplication_key == deduplication_key))
            if row is None:
                row = Alert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    change_id=change_id,
                    behavior_id=behavior_id,
                    regression_id=regression_id,
                    gate_id=gate_id,
                    severity=severity,
                    category=category,
                    title_key=title_key,
                    summary_key=summary_key,
                    parameters_json=json.dumps(parameters or {}, sort_keys=True),
                    route_json=json.dumps(route, sort_keys=True),
                    deduplication_key=deduplication_key,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                event_type = "alert_created"
            else:
                row.updated_at = now
                row.resolved_at = None
                row.parameters_json = json.dumps(parameters or {}, sort_keys=True)
                event_type = "alert_updated"
            session.flush()
            value = self._alert(row)
        self.events.publish(event_type, project_id, {"alert_id": value["id"]})
        self.events.publish("unread_count_changed", project_id, {"count": self.unread_count()})
        return value

    def list_alerts(
        self,
        *,
        project_id: str | None = None,
        state: str = "all",
        severity: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.sessions() as session:
            query = select(Alert)
            if project_id:
                query = query.where(Alert.project_id == project_id)
            if state == "unread":
                query = query.where(Alert.read_at.is_(None), Alert.resolved_at.is_(None))
            if state == "attention":
                query = query.where(
                    Alert.resolved_at.is_(None), Alert.severity.in_(["HIGH", "CRITICAL", "WARNING"])
                )
            if state == "resolved":
                query = query.where(Alert.resolved_at.is_not(None))
            if severity:
                query = query.where(Alert.severity == severity)
            if category:
                query = query.where(Alert.category == category)
            return [
                self._alert(row)
                for row in session.scalars(query.order_by(Alert.updated_at.desc()).limit(500)).all()
            ]

    def unread_count(self) -> int:
        with self.sessions() as session:
            return int(
                session.scalar(
                    select(func.count(Alert.id)).where(
                        Alert.read_at.is_(None), Alert.resolved_at.is_(None)
                    )
                )
                or 0
            )

    def set_alert_state(self, alert_id: str, action: str) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(Alert, alert_id)
            if row is None:
                raise ProductizationError("ALERT_NOT_FOUND")
            if action == "read":
                row.read_at = now
            elif action == "unread":
                row.read_at = None
            elif action == "resolve":
                row.resolved_at = now
                row.read_at = row.read_at or now
            else:
                raise ProductizationError("ALERT_ACTION_INVALID")
            row.updated_at = now
            project_id = row.project_id
            value = self._alert(row)
        self.events.publish(
            "alert_resolved" if action == "resolve" else "alert_updated",
            project_id,
            {"alert_id": alert_id},
        )
        self.events.publish("unread_count_changed", project_id, {"count": self.unread_count()})
        return value

    def clear_resolved(self) -> int:
        with self.sessions.begin() as session:
            count = int(
                session.scalar(select(func.count(Alert.id)).where(Alert.resolved_at.is_not(None)))
                or 0
            )
            session.execute(delete(Alert).where(Alert.resolved_at.is_not(None)))
        return count

    def notification_settings(self) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(NotificationPreference, 1)
            return {
                column.name: getattr(row, column.name)
                for column in row.__table__.columns
                if column.name not in {"id", "updated_at"}
            }

    def update_notification_settings(self, values: dict[str, bool]) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(NotificationPreference, 1)
            allowed = set(self.notification_settings())
            for key, value in values.items():
                if key in allowed:
                    setattr(row, key, bool(value))
            row.updated_at = _now()
        return self.notification_settings()

    def project_notifications(self, project_id: str, muted: bool | None = None) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            row = session.get(ProjectNotificationPreference, project_id)
            if row is None:
                row = ProjectNotificationPreference(
                    project_id=project_id, muted=project.notifications_muted, updated_at=_now()
                )
                session.add(row)
            if muted is not None:
                row.muted = muted
                row.updated_at = _now()
                project.notifications_muted = muted
            result = {"project_id": project_id, "muted": row.muted}
        if muted is not None:
            self.events.publish("project_muted" if muted else "project_unmuted", project_id, {})
        return result

    def quiet(self) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(QuietModeState, 1)
            if row.active and row.ends_at and row.ends_at <= now:
                row.active = False
                row.ends_at = None
                row.until_turned_off = False
                row.updated_at = now
            return {
                "active": row.active,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "ends_at": row.ends_at.isoformat() if row.ends_at else None,
                "until_turned_off": row.until_turned_off,
                "allow_critical": row.allow_critical,
                "remaining_seconds": max(0, int((row.ends_at - now).total_seconds()))
                if row.active and row.ends_at
                else None,
            }

    def start_quiet(self, duration: str, allow_critical: bool = False) -> dict[str, Any]:
        now = _now()
        ends = None
        if duration == "one_hour":
            ends = now + timedelta(hours=1)
        elif duration == "until_tomorrow":
            ends = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        elif duration != "until_off":
            raise ProductizationError("QUIET_DURATION_INVALID")
        with self.sessions.begin() as session:
            row = session.get(QuietModeState, 1)
            row.active = True
            row.started_at = now
            row.ends_at = ends
            row.until_turned_off = duration == "until_off"
            row.allow_critical = allow_critical
            row.updated_at = now
        self.events.publish("quiet_mode_started", None, {"duration": duration})
        return self.quiet()

    def stop_quiet(self) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(QuietModeState, 1)
            row.active = False
            row.ends_at = None
            row.until_turned_off = False
            row.updated_at = _now()
        self.events.publish("quiet_mode_ended", None, {})
        return self.quiet()

    def background(
        self, keep_running: bool | None = None, start_at_login: bool | None = None
    ) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(ApplicationPreference, 1)
            if keep_running is not None:
                row.keep_running_on_close = keep_running
            if start_at_login is not None:
                row.start_at_login = start_at_login
            row.updated_at = _now()
            return {
                "keep_running_on_close": row.keep_running_on_close,
                "start_at_login": row.start_at_login,
                "start_at_login_supported": True,
                "background_supported": True,
            }

    def capabilities(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            runtime = session.scalar(
                select(RuntimeConfiguration).where(
                    RuntimeConfiguration.project_id == project_id,
                )
            )
            local = Path(project.canonical_root_path or project.root_path).is_dir()
            return {
                "mode": "local_source_with_runtime" if runtime and local else "local_source",
                "source_available": local,
                "runtime_available": runtime is not None,
                "available": [
                    "git_observation",
                    "source_scan",
                    "impact",
                    "protected_behaviors",
                    "local_evidence",
                    "human_attestation",
                ]
                + (
                    [
                        "browser_capture",
                        "browser_replay",
                        "assertions",
                        "regression_detection",
                        "completion_gate",
                    ]
                    if runtime and local
                    else []
                ),
                "unavailable": ["automatic_browser_replay"],
                "future_only": ["runtime_only", "remote_without_checkout"],
                "source_remains_local": True,
            }

    def lifecycle_preview(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            behaviors = int(
                session.scalar(
                    select(func.count(ProtectedBehavior.id)).where(
                        ProtectedBehavior.project_id == project_id
                    )
                )
                or 0
            )
            evidence = int(
                session.scalar(
                    select(func.count(EvidenceBundle.id)).where(
                        EvidenceBundle.project_id == project_id
                    )
                )
                or 0
            )
            regressions = int(
                session.scalar(
                    select(func.count(RegressionFinding.id)).where(
                        RegressionFinding.project_id == project_id
                    )
                )
                or 0
            )
            return {
                "project_id": project_id,
                "project_name": project.display_name,
                "source_path": str(Path(project.root_path).name),
                "mellowyak_data_bytes": 0,
                "behavior_count": behaviors,
                "evidence_count": evidence,
                "regression_count": regressions,
                "source_will_be_modified": False,
            }

    def disconnect(self, project_id: str) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            project.disconnected_at = now
            project.monitoring_mode = "paused"
            project.monitoring_status = "disconnected"
            project.updated_at = now
            session.add(
                ProjectDisconnectionRecord(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    display_name=project.display_name,
                    repository_identity_json=json.dumps(
                        {
                            "head": project.current_head_sha,
                            "path_name": Path(project.root_path).name,
                        },
                        sort_keys=True,
                    ),
                    disconnected_at=now,
                )
            )
            session.add(
                ProjectLifecycleEvent(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    event_type="project_disconnected",
                    details_json="{}",
                    created_at=now,
                )
            )
        self.events.publish("project_disconnected", project_id, {})
        return {"project_id": project_id, "disconnected": True, "source_modified": False}

    def reconnect(self, project_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            project.disconnected_at = None
            project.monitoring_mode = "passive"
            project.monitoring_status = "active"
            project.updated_at = _now()
            record = session.scalar(
                select(ProjectDisconnectionRecord)
                .where(
                    ProjectDisconnectionRecord.project_id == project_id,
                    ProjectDisconnectionRecord.reconnected_at.is_(None),
                )
                .order_by(ProjectDisconnectionRecord.disconnected_at.desc())
            )
            if record:
                record.reconnected_at = _now()
        self.events.publish("project_reconnected", project_id, {})
        return {"project_id": project_id, "reconnected": True}

    def relocate(
        self, project_id: str, path: str, confirm_identity_change: bool = False
    ) -> dict[str, Any]:
        candidate = Path(path).expanduser().resolve()
        if not candidate.is_dir():
            raise ProductizationError("PROJECT_PATH_UNAVAILABLE")
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            old_git = Path(project.repository_root_path or project.root_path) / ".git"
            new_git = candidate / ".git"
            if old_git.exists() != new_git.exists() and not confirm_identity_change:
                raise ProductizationError("PROJECT_IDENTITY_CONFIRMATION_REQUIRED")
            project.root_path = str(candidate)
            project.canonical_root_path = str(candidate)
            project.repository_root_path = str(candidate)
            project.source_available = True
            project.updated_at = _now()
        self.events.publish("project_relocated", project_id, {})
        return {"project_id": project_id, "relocated": True, "source_modified": False}

    def delete_local_data(self, project_id: str, confirmation: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProductizationError("PROJECT_NOT_FOUND")
            if confirmation != project.display_name:
                raise ProductizationError("PROJECT_NAME_CONFIRMATION_REQUIRED")
            artifact_paths = [
                self.data_root / "evidence" / path
                for path in session.scalars(
                    select(EvidenceArtifact.object_key).where(
                        EvidenceArtifact.project_id == project_id
                    )
                ).all()
            ]
        engine = self.sessions.kw["bind"]
        inspector = inspect(engine)
        metadata = MetaData()
        metadata.reflect(bind=engine)
        selected: dict[str, set[Any]] = {"projects": {project_id}}
        with engine.connect() as connection:
            changed = True
            while changed:
                changed = False
                for name in inspector.get_table_names():
                    table = metadata.tables[name]
                    pk = list(table.primary_key.columns)
                    if len(pk) != 1:
                        continue
                    clauses = []
                    if "project_id" in table.c:
                        clauses.append(table.c.project_id == project_id)
                    for fk in inspector.get_foreign_keys(name):
                        parent = fk.get("referred_table")
                        columns = fk.get("constrained_columns") or []
                        if parent in selected and len(columns) == 1:
                            clauses.append(table.c[columns[0]].in_(selected[parent]))
                    if not clauses:
                        continue
                    from sqlalchemy import or_

                    values = set(connection.execute(select(pk[0]).where(or_(*clauses))).scalars())
                    before = len(selected.get(name, set()))
                    selected.setdefault(name, set()).update(values)
                    changed |= len(selected[name]) != before
        raw = engine.raw_connection()
        cursor = raw.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute("BEGIN IMMEDIATE")
            for name, values in sorted(selected.items(), key=lambda item: item[0] == "projects"):
                if not values:
                    continue
                marks = ",".join("?" for _ in values)
                pk = inspector.get_pk_constraint(name)["constrained_columns"][0]
                cursor.execute(f'DELETE FROM "{name}" WHERE "{pk}" IN ({marks})', tuple(values))
            raw.commit()
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception:
            raw.rollback()
            cursor.execute("PRAGMA foreign_keys=ON")
            raise
        finally:
            cursor.close()
            raw.close()
        for path in artifact_paths:
            resolved = path.resolve()
            if resolved.is_relative_to(self.data_root) and resolved.is_file():
                with self.sessions() as session:
                    if not session.scalar(
                        select(func.count(EvidenceArtifact.id)).where(
                            EvidenceArtifact.object_key
                            == str(path.relative_to(self.data_root / "evidence"))
                        )
                    ):
                        resolved.unlink(missing_ok=True)
        self.events.publish("project_data_deleted", project_id, {})
        return {"project_id": project_id, "deleted": True, "source_modified": False}

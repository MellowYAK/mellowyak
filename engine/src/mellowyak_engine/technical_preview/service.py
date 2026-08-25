from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import re
import shutil
import subprocess
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine import APP_VERSION, ENGINE_VERSION
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    Alert,
    ApplyTransaction,
    DiagnosticRun,
    EngineRun,
    NotificationActivationEvent,
    OnboardingState,
    PackageAcceptanceRun,
    ProductSelfTestRun,
    Project,
    ProjectFile,
    ProjectLocationHistory,
    ProtectedBehavior,
    QuietModeState,
    RegressionFinding,
    SnapshotObject,
    SupportBundleRecord,
    TechnicalPreviewPreference,
    UpdateValidationRun,
)
from mellowyak_engine.git.observer import observe_git


class TechnicalPreviewError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _tree_size(root: Path) -> int:
    total = 0
    if not root.exists():
        return total
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if not (Path(current) / name).is_symlink()]
        for name in files:
            path = Path(current) / name
            try:
                if not path.is_symlink():
                    total += path.stat().st_size
            except OSError:
                continue
    return total


def _safe_alias(path: Path, kind: str) -> str:
    return f"<{kind}>/{path.name}" if path.name else f"<{kind}>"


class TechnicalPreviewService:
    """Local-only product completion with privacy-safe diagnostics and route validation."""

    ROUTE_SCREENS = {
        "home",
        "projects",
        "alerts",
        "settings",
        "diagnostics",
        "technical-preview",
        "project",
        "change",
        "behaviors",
        "runtime",
        "recovery",
    }
    ACTIVITY_MODES = {"normal", "reduced", "battery_saver"}

    def __init__(
        self,
        sessions: sessionmaker,
        data_root: Path,
        schema_version: str,
        installation_id: str,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.schema_version = schema_version
        self.installation_id = installation_id
        self.events = events
        self.support_root = self.data_root / "support-bundles"
        self.support_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        now = _now()
        with self.sessions.begin() as session:
            if session.get(OnboardingState, 1) is None:
                session.add(OnboardingState(id=1, updated_at=now))
            if session.get(TechnicalPreviewPreference, 1) is None:
                session.add(TechnicalPreviewPreference(id=1, updated_at=now))

    def onboarding(self) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(OnboardingState, 1)
            return {
                "completed": row.completed,
                "current_step": row.current_step,
                "replay_active": row.replay_active,
                "selected_path": row.selected_path,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "requires_first_run": not row.completed,
                "source_modified": False,
            }

    def update_onboarding(
        self, *, current_step: str, selected_path: str | None, completed: bool
    ) -> dict[str, Any]:
        allowed = {"welcome", "choice", "privacy", "background", "notifications", "complete"}
        if current_step not in allowed:
            raise TechnicalPreviewError("ONBOARDING_STEP_INVALID")
        if selected_path not in {None, "real_project", "demo_lab", "existing_installation"}:
            raise TechnicalPreviewError("ONBOARDING_PATH_INVALID")
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(OnboardingState, 1)
            row.current_step = "complete" if completed else current_step
            row.selected_path = selected_path
            row.completed = completed
            row.completed_at = now if completed else None
            row.replay_active = False if completed else row.replay_active
            row.updated_at = now
        self.events.publish(
            "onboarding_completed" if completed else "onboarding_changed",
            None,
            {"step": current_step, "selected_path": selected_path},
        )
        return self.onboarding()

    def replay_onboarding(self) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(OnboardingState, 1)
            row.current_step = "welcome"
            row.replay_active = True
            row.updated_at = _now()
        self.events.publish("onboarding_replayed", None, {})
        return self.onboarding()

    def preferences(self, activity_mode: str | None = None) -> dict[str, Any]:
        if activity_mode is not None and activity_mode not in self.ACTIVITY_MODES:
            raise TechnicalPreviewError("ACTIVITY_MODE_INVALID")
        with self.sessions.begin() as session:
            row = session.get(TechnicalPreviewPreference, 1)
            if activity_mode is not None:
                row.activity_mode = activity_mode
                row.updated_at = _now()
            value = {
                "activity_mode": row.activity_mode,
                "notification_permission": row.notification_permission,
                "updater_state": row.updater_state,
                "last_update_check_at": row.last_update_check_at.isoformat()
                if row.last_update_check_at
                else None,
                "core_file_observation": True,
                "snapshot_correctness": True,
                "critical_alerts": True,
                "deferred": [
                    "deep_runtime_observation",
                    "noncritical_probes",
                    "rich_traces",
                    "update_checks",
                ]
                if row.activity_mode == "battery_saver"
                else [],
            }
        if activity_mode is not None:
            self.events.publish("battery_mode_changed", None, {"mode": activity_mode})
        return value

    def _last_disconnect(self, session: Any, project_id: str) -> datetime | None:
        from mellowyak_engine.db.models import ProjectDisconnectionRecord

        record = session.scalar(
            select(ProjectDisconnectionRecord)
            .where(ProjectDisconnectionRecord.project_id == project_id)
            .order_by(ProjectDisconnectionRecord.disconnected_at.desc())
        )
        return record.disconnected_at if record else None

    def disconnected_projects(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(select(Project).where(Project.archived_at.is_(None))).all()
            result: list[dict[str, Any]] = []
            for project in rows:
                root = Path(project.canonical_root_path or project.root_path)
                available = root.is_dir()
                if (
                    project.disconnected_at is None
                    and available
                    and project.monitoring_status == "active"
                ):
                    state = "CONNECTED"
                elif not available:
                    state = "MISSING"
                elif project.monitoring_status == "error":
                    state = "NEEDS_ATTENTION"
                elif project.monitoring_status != "active":
                    state = "DISCONNECTED" if project.disconnected_at else "PAUSED"
                else:
                    state = "CONNECTED"
                behavior_count = int(
                    session.scalar(
                        select(func.count(ProtectedBehavior.id)).where(
                            ProtectedBehavior.project_id == project.id
                        )
                    )
                    or 0
                )
                regression_count = int(
                    session.scalar(
                        select(func.count(RegressionFinding.id)).where(
                            RegressionFinding.project_id == project.id
                        )
                    )
                    or 0
                )
                retained_bytes = int(
                    session.scalar(
                        select(func.coalesce(func.sum(SnapshotObject.byte_size), 0)).where(
                            SnapshotObject.project_id == project.id
                        )
                    )
                    or 0
                )
                disconnected_at = project.disconnected_at or self._last_disconnect(
                    session, project.id
                )
                result.append(
                    {
                        "project_id": project.id,
                        "project_name": project.display_name,
                        "state": state,
                        "last_known_safe_path": _safe_alias(root, "PROJECT"),
                        "last_source_identity": {
                            "head_sha": project.current_head_sha,
                            "worktree_fingerprint": project.current_worktree_fingerprint,
                        },
                        "disconnect_time": disconnected_at.isoformat() if disconnected_at else None,
                        "data_retained": True,
                        "data_size_bytes": retained_bytes,
                        "behavior_count": behavior_count,
                        "regression_count": regression_count,
                        "last_activity": project.updated_at.isoformat()
                        if project.updated_at
                        else project.created_at.isoformat(),
                        "source_modified": False,
                    }
                )
            return result

    @staticmethod
    def _git_contains(root: Path, commit: str) -> bool:
        if not commit or not (root / ".git").exists():
            return False
        try:
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def identity_preview(self, project_id: str, path: str) -> dict[str, Any]:
        try:
            candidate = Path(path).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise TechnicalPreviewError("PROJECT_PATH_MISSING") from error
        if not candidate.is_dir():
            raise TechnicalPreviewError("PROJECT_PATH_NOT_DIRECTORY")
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise TechnicalPreviewError("PROJECT_NOT_FOUND")
            expected_head = project.current_head_sha
            stable_paths = session.scalars(
                select(ProjectFile.normalized_path)
                .where(ProjectFile.project_id == project_id, ProjectFile.deleted_at.is_(None))
                .limit(80)
            ).all()
        git = observe_git(candidate)
        matching_paths = sum(1 for relative in stable_paths if (candidate / relative).is_file())
        path_ratio = matching_paths / max(1, len(stable_paths))
        git_match = bool(expected_head and self._git_contains(candidate, expected_head))
        non_git_match = not expected_head and len(stable_paths) > 0 and path_ratio >= 0.8
        matched = git_match or non_git_match
        confidence = "HIGH" if git_match or path_ratio >= 0.95 else "MEDIUM" if matched else "LOW"
        return {
            "project_id": project_id,
            "candidate_path": _safe_alias(candidate, "SELECTED_FOLDER"),
            "matched": matched,
            "confidence": confidence,
            "expected": {"head_sha": expected_head, "stable_path_count": len(stable_paths)},
            "observed": {
                "git_available": git.available,
                "head_sha": git.head_sha,
                "expected_commit_present": git_match,
                "matching_stable_paths": matching_paths,
                "stable_path_ratio": round(path_ratio, 4),
            },
            "reason": "IDENTITY_MATCHED" if matched else "PROJECT_IDENTITY_MISMATCH",
            "source_modified": False,
        }

    def reconnect_or_relocate(self, project_id: str, path: str, action: str) -> dict[str, Any]:
        if action not in {"reconnect", "relocate"}:
            raise TechnicalPreviewError("PROJECT_LOCATION_ACTION_INVALID")
        preview = self.identity_preview(project_id, path)
        candidate = Path(path).expanduser().resolve(strict=True)
        now = _now()
        matched = bool(preview["matched"])
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise TechnicalPreviewError("PROJECT_NOT_FOUND")
            old = Path(project.canonical_root_path or project.root_path)
            session.add(
                ProjectLocationHistory(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    action=action,
                    old_location_alias=_safe_alias(old, "PROJECT"),
                    new_location_alias=_safe_alias(candidate, "SELECTED_FOLDER"),
                    expected_identity_json=_json(preview["expected"]),
                    observed_identity_json=_json(preview["observed"]),
                    decision="ACCEPTED" if matched else "REJECTED",
                    created_at=now,
                )
            )
            if matched:
                project.root_path = str(candidate)
                project.canonical_root_path = str(candidate)
                project.repository_root_path = str(candidate)
                project.source_available = True
                project.disconnected_at = None
                project.monitoring_mode = "passive"
                project.monitoring_status = "active"
                project.updated_at = now
        if not matched:
            self.events.publish("relocation_rejected", project_id, {"reason": preview["reason"]})
            raise TechnicalPreviewError("PROJECT_IDENTITY_MISMATCH")
        event = "project_reconnected" if action == "reconnect" else "project_relocated"
        self.events.publish(event, project_id, {"identity_confidence": preview["confidence"]})
        return {
            "project_id": project_id,
            "action": action,
            "identity": preview,
            "history_preserved": True,
            "source_moved": False,
            "source_copied": False,
            "source_deleted": False,
        }

    def tray_state(self) -> dict[str, Any]:
        with self.sessions() as session:
            projects = session.scalars(select(Project).where(Project.archived_at.is_(None))).all()
            unresolved = session.scalars(select(Alert).where(Alert.resolved_at.is_(None))).all()
            active_apply = int(
                session.scalar(
                    select(func.count(ApplyTransaction.id)).where(
                        ApplyTransaction.state.in_(
                            ["PREPARED", "APPLYING", "VERIFYING", "ROLLING_BACK"]
                        )
                    )
                )
                or 0
            )
            recovery = int(
                session.scalar(
                    select(func.count(ApplyTransaction.id)).where(
                        ApplyTransaction.state == "RECOVERY_REQUIRED"
                    )
                )
                or 0
            )
            critical = sum(1 for alert in unresolved if alert.severity == "CRITICAL")
            unread = sum(1 for alert in unresolved if alert.read_at is None)
            active = sum(1 for project in projects if project.monitoring_status == "active")
            paused = len(projects) - active
            quiet = session.get(QuietModeState, 1)
            quiet_active = bool(
                quiet
                and quiet.active
                and (quiet.until_turned_off or quiet.ends_at is None or quiet.ends_at > _now())
            )
            if recovery:
                state = "RECOVERY_REQUIRED"
            elif active_apply:
                state = "APPLY_IN_PROGRESS"
            elif critical:
                state = "REGRESSION_DETECTED"
            elif any(project.monitoring_status == "error" for project in projects):
                state = "ENGINE_ERROR"
            elif quiet_active:
                state = "QUIET"
            elif active:
                state = "MONITORING"
            else:
                state = "PAUSED"
            project_items = [
                {
                    "project_id": project.id,
                    "name": project.display_name[:48],
                    "monitoring_state": project.monitoring_status,
                    "muted": project.notifications_muted,
                }
                for project in projects[:12]
            ]
            recent = [
                {"alert_id": alert.id, "severity": alert.severity, "title_key": alert.title_key}
                for alert in unresolved[:5]
            ]
        return {
            "state": state,
            "unread_alert_count": unread,
            "critical_alert_count": critical,
            "active_project_count": active,
            "paused_project_count": paused,
            "quiet_mode_active": quiet_active,
            "projects": project_items,
            "recent_alerts": recent,
            "private_paths_exposed": False,
            "source_content_exposed": False,
        }

    def validate_notification_route(
        self, route: dict[str, Any], record: bool = True
    ) -> dict[str, Any]:
        allowed_keys = {
            "screen",
            "project_id",
            "change_id",
            "behavior_id",
            "regression_id",
            "gate_id",
            "alert_id",
            "runtime_error_id",
            "transaction_id",
        }
        status = "ACCEPTED"
        reason: str | None = None
        project_id = route.get("project_id")
        if set(route) - allowed_keys or route.get("screen") not in self.ROUTE_SCREENS:
            status, reason = "REJECTED", "NOTIFICATION_ROUTE_INVALID"
        elif any(
            not isinstance(value, str) or len(value) > 128 or "/" in value or "\\" in value
            for key, value in route.items()
            if key != "screen" and value is not None
        ):
            status, reason = "REJECTED", "NOTIFICATION_ROUTE_VALUE_INVALID"
        elif (
            route.get("screen") in {"project", "change", "behaviors", "runtime", "recovery"}
            and not project_id
        ):
            status, reason = "REJECTED", "NOTIFICATION_PROJECT_REQUIRED"
        if status == "ACCEPTED" and project_id:
            with self.sessions() as session:
                if session.get(Project, project_id) is None:
                    status, reason = "STALE", "NOTIFICATION_DESTINATION_MISSING"
                alert_id = route.get("alert_id")
                if alert_id:
                    alert = session.get(Alert, alert_id)
                    if alert is None:
                        status, reason = "STALE", "NOTIFICATION_DESTINATION_MISSING"
                    elif alert.project_id != project_id:
                        status, reason = "REJECTED", "NOTIFICATION_CROSS_PROJECT"
        result = {
            "status": status,
            "reason": reason,
            "route": route if status == "ACCEPTED" else {"screen": "alerts"},
            "source_content": False,
            "full_path": False,
            "secret": False,
        }
        if record:
            with self.sessions.begin() as session:
                session.add(
                    NotificationActivationEvent(
                        id=str(uuid.uuid4()),
                        project_id=project_id if status == "ACCEPTED" else None,
                        route_json=_json(result["route"]),
                        status=status,
                        reason=reason,
                        created_at=_now(),
                    )
                )
            self.events.publish(
                "notification_activated"
                if status == "ACCEPTED"
                else "notification_destination_missing",
                project_id if status == "ACCEPTED" else None,
                {"status": status, "reason": reason},
            )
        return result

    def diagnostics(self) -> dict[str, Any]:
        with self.sessions.begin() as session:
            counts = {
                "projects": int(session.scalar(select(func.count(Project.id))) or 0),
                "snapshot_objects": int(session.scalar(select(func.count(SnapshotObject.id))) or 0),
                "incomplete_transactions": int(
                    session.scalar(
                        select(func.count(ApplyTransaction.id)).where(
                            ApplyTransaction.state.in_(
                                ["PREPARED", "APPLYING", "VERIFYING", "ROLLING_BACK"]
                            )
                        )
                    )
                    or 0
                ),
                "recovery_required": int(
                    session.scalar(
                        select(func.count(ApplyTransaction.id)).where(
                            ApplyTransaction.state == "RECOVERY_REQUIRED"
                        )
                    )
                    or 0
                ),
            }
            last_self_test = session.scalar(
                select(ProductSelfTestRun).order_by(ProductSelfTestRun.created_at.desc())
            )
            recent_starts = session.scalars(
                select(EngineRun).order_by(EngineRun.started_at.desc()).limit(5)
            ).all()
            preferences = session.get(TechnicalPreviewPreference, 1)
            summary = {
                "desktop_version": APP_VERSION,
                "engine_version": ENGINE_VERSION,
                "schema_migration": self.schema_version,
                "installation_identity": self.installation_id,
                "local_api_state": "AUTHENTICATED_LOOPBACK",
                "loopback_address": "127.0.0.1:<ephemeral>",
                "bearer_token_exposed": False,
                "data_root": "<DATA_ROOT>",
                "data_root_size_bytes": _tree_size(self.data_root),
                "evidence_size_bytes": _tree_size(self.data_root / "evidence"),
                **counts,
                "browser_runtime_available": (self.data_root / "runtime").is_dir(),
                "runtime_adapter_available": True,
                "tray": self.tray_state(),
                "notification_permission": preferences.notification_permission,
                "updater_state": preferences.updater_state,
                "signing_state": "UNSIGNED_NOT_NOTARIZED",
                "platform": platform.system(),
                "architecture": platform.machine(),
                "recent_engine_starts": [row.started_at.isoformat() for row in recent_starts],
                "self_test_last_result": last_self_test.status if last_self_test else "NOT_RUN",
                "outbound_product_network": False,
                "cloud_connected": False,
            }
            run_id = str(uuid.uuid4())
            session.add(
                DiagnosticRun(
                    id=run_id,
                    status="COMPLETE",
                    summary_json=_json(summary),
                    created_at=_now(),
                )
            )
        self.events.publish("diagnostics_changed", None, {"run_id": run_id})
        return {"run_id": run_id, **summary}

    def storage_integrity(self) -> dict[str, Any]:
        database = self.data_root / "database" / "mellowyak.sqlite3"
        objects = self.data_root / "snapshots" / "objects"
        issues: list[str] = []
        if not database.is_file():
            issues.append("DATABASE_MISSING")
        for root in [self.data_root, self.support_root]:
            if root.is_symlink() or not root.resolve().is_relative_to(self.data_root):
                issues.append("STORAGE_CONFINEMENT_FAILED")
        return {
            "status": "PASS" if not issues else "FAIL",
            "checks": {
                "database_present": database.is_file(),
                "data_root_confined": not self.data_root.is_symlink(),
                "support_root_confined": self.support_root.resolve().is_relative_to(self.data_root),
                "snapshot_store_present_or_unused": objects.is_dir() or not objects.exists(),
            },
            "issues": issues,
            "source_modified": False,
        }

    @staticmethod
    def _redact_text(text: str, aliases: list[tuple[str, str]]) -> str:
        value = text
        for raw, alias in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
            if raw:
                value = value.replace(raw, alias)
        value = re.sub(
            r"(?i)(authorization|token|password|secret|cookie)(\s*[:=]\s*)[^\s,;]+",
            r"\1\2<REDACTED>",
            value,
        )
        value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/-]+", "Bearer <REDACTED>", value)
        return value

    def export_support_bundle(self) -> dict[str, Any]:
        bundle_id = str(uuid.uuid4())
        stamp = _now().strftime("%Y%m%dT%H%M%SZ")
        bundle_dir = self.support_root / f"MellowYak-Support-{stamp}-{bundle_id[:8]}"
        bundle_dir.mkdir(mode=0o700)
        (bundle_dir / "logs").mkdir(mode=0o700)
        aliases = [(str(Path.home()), "<HOME>"), (str(self.data_root), "<DATA_ROOT>")]
        with self.sessions() as session:
            projects = session.scalars(select(Project).order_by(Project.created_at)).all()
            aliases.extend(
                (str(Path(project.canonical_root_path or project.root_path)), f"<PROJECT_{index}>")
                for index, project in enumerate(projects, 1)
            )
            project_summary = [
                {
                    "project": f"<PROJECT_{index}>",
                    "name": project.display_name,
                    "monitoring_status": project.monitoring_status,
                    "source_available": Path(
                        project.canonical_root_path or project.root_path
                    ).is_dir(),
                    "head_sha": project.current_head_sha,
                    "source_included": False,
                }
                for index, project in enumerate(projects, 1)
            ]
            alerts = session.scalars(
                select(Alert).order_by(Alert.created_at.desc()).limit(100)
            ).all()
            alert_summary = [
                {
                    "severity": alert.severity,
                    "category": alert.category,
                    "title_key": alert.title_key,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in alerts
            ]
        diagnostics = self.diagnostics()
        payloads: dict[str, object] = {
            "app.json": {
                "desktop_version": APP_VERSION,
                "installation_identity": self.installation_id,
                "cloud_connected": False,
                "usage_reporting": False,
            },
            "engine.json": {
                "engine_version": ENGINE_VERSION,
                "schema_migration": self.schema_version,
                "loopback_only": True,
                "bearer_token_included": False,
            },
            "platform.json": {"system": platform.system(), "architecture": platform.machine()},
            "projects-summary.json": project_summary,
            "alerts-summary.json": alert_summary,
            "storage-summary.json": {
                "data_root": "<DATA_ROOT>",
                "size_bytes": diagnostics["data_root_size_bytes"],
                "source_included": False,
                "evidence_bytes_included": False,
            },
            "migrations.json": {"current": self.schema_version},
            "self-test-summary.json": {"last_result": diagnostics["self_test_last_result"]},
            "package-identities.json": {"runtime_package": "not_provided_by_engine"},
        }
        exported = ["README.md", *payloads]
        redaction_report = {
            "aliases": [alias for _, alias in aliases],
            "redacted_classes": [
                "home_paths",
                "project_paths",
                "data_root",
                "authorization",
                "tokens",
                "passwords",
                "secrets",
                "cookies",
            ],
            "excluded": [
                "source",
                "snapshot_bytes",
                "evidence_bytes",
                "repair_workspace_source",
                "candidate_contents",
                "provider_state",
                "browser_profiles",
            ],
        }
        payloads["redaction-report.json"] = redaction_report
        exported.append("redaction-report.json")
        for name, payload in payloads.items():
            text = self._redact_text(json.dumps(payload, indent=2, sort_keys=True), aliases)
            (bundle_dir / name).write_text(text + "\n", encoding="utf-8")
        readme = (
            "# MellowYak Support Bundle\n\n"
            "Local redacted diagnostics only. No source or evidence bytes are included.\n"
        )
        (bundle_dir / "README.md").write_text(readme, encoding="utf-8")
        redacted_logs: list[str] = []
        logs_root = self.data_root / "logs"
        for log_path in sorted(logs_root.glob("*.jsonl"))[-5:]:
            try:
                for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()[
                    -400:
                ]:
                    redacted_logs.append(self._redact_text(line, aliases))
            except OSError:
                continue
        (bundle_dir / "logs" / "redacted-logs.jsonl").write_text(
            "\n".join(redacted_logs) + ("\n" if redacted_logs else ""), encoding="utf-8"
        )
        exported.append("logs/redacted-logs.jsonl")
        manifest = {
            "schema": "mellowyak.support_bundle.v1",
            "bundle_id": bundle_id,
            "files": sorted(exported + ["manifest.json"]),
            "source_included": False,
            "evidence_bytes_included": False,
            "absolute_paths_included": False,
        }
        manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        (bundle_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
        archive = bundle_dir.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path in sorted(bundle_dir.rglob("*")):
                if path.is_file():
                    output.write(path, path.relative_to(bundle_dir.parent))
        shutil.rmtree(bundle_dir)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        relative = archive.relative_to(self.data_root).as_posix()
        with self.sessions.begin() as session:
            session.add(
                SupportBundleRecord(
                    id=bundle_id,
                    relative_path=relative,
                    manifest_sha256=digest,
                    status="COMPLETE",
                    created_at=_now(),
                )
            )
        self.events.publish("support_bundle_completed", None, {"bundle_id": bundle_id})
        return {
            "bundle_id": bundle_id,
            "relative_path": relative,
            "sha256": digest,
            "size_bytes": archive.stat().st_size,
            "manifest": manifest,
            "status": "COMPLETE",
        }

    def support_bundle(self, bundle_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(SupportBundleRecord, bundle_id)
            if row is None:
                raise TechnicalPreviewError("SUPPORT_BUNDLE_NOT_FOUND")
            path = (self.data_root / row.relative_path).resolve()
            if not path.is_relative_to(self.data_root) or not path.is_file():
                raise TechnicalPreviewError("SUPPORT_BUNDLE_MISSING")
            return {
                "bundle_id": row.id,
                "relative_path": row.relative_path,
                "sha256": row.manifest_sha256,
                "size_bytes": path.stat().st_size,
                "status": row.status,
            }

    def updater_status(self) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(TechnicalPreviewPreference, 1)
            return {
                "state": row.updater_state,
                "last_checked_at": row.last_update_check_at.isoformat()
                if row.last_update_check_at
                else None,
                "production_endpoint": "HTTPS_CONFIGURED",
                "signature_required": True,
                "production_public_key_preserved": True,
                "production_update_runtime_verified": False,
            }

    def record_update_check(self, result: str = "NO_UPDATE") -> dict[str, Any]:
        if result not in {"NO_UPDATE", "UPDATE_AVAILABLE", "CHECK_FAILED"}:
            raise TechnicalPreviewError("UPDATE_RESULT_INVALID")
        with self.sessions.begin() as session:
            row = session.get(TechnicalPreviewPreference, 1)
            row.updater_state = result.lower()
            row.last_update_check_at = _now()
            row.updated_at = _now()
        self.events.publish("update_check_completed", None, {"result": result})
        return self.updater_status()

    def validate_update_fixture(self, fixture: str) -> dict[str, Any]:
        allowed = {"valid", "invalid_signature", "tampered", "interrupted", "no_update"}
        if fixture not in allowed:
            raise TechnicalPreviewError("UPDATE_FIXTURE_INVALID")
        key = os.urandom(32)
        artifact = b"mellowyak-disposable-update-v0.2.0-preview.2"
        signature = hmac.new(key, artifact, hashlib.sha256).digest()
        candidate = artifact
        candidate_signature = signature
        expected = "ACCEPTED"
        if fixture == "invalid_signature":
            candidate_signature = hmac.new(os.urandom(32), artifact, hashlib.sha256).digest()
            expected = "REJECTED"
        elif fixture == "tampered":
            candidate = artifact + b"-tampered"
            expected = "REJECTED"
        elif fixture == "interrupted":
            candidate = artifact[: len(artifact) // 2]
            expected = "REJECTED_INCOMPLETE"
        elif fixture == "no_update":
            expected = "NO_UPDATE"
        verified = hmac.compare_digest(
            hmac.new(key, candidate, hashlib.sha256).digest(), candidate_signature
        )
        status = "NO_UPDATE" if fixture == "no_update" else "ACCEPTED" if verified else expected
        details = {
            "ephemeral_key": True,
            "private_key_persisted": False,
            "loopback_fixture": True,
            "production_configuration_changed": False,
            "artifact_sha256": hashlib.sha256(candidate).hexdigest(),
            "signature_verified": verified,
            "application_data_preserved": True,
            "source_projects_touched": False,
            "interrupted_download_safe": fixture != "interrupted" or not verified,
        }
        run_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            session.add(
                UpdateValidationRun(
                    id=run_id,
                    fixture=fixture,
                    status=status,
                    details_json=_json(details),
                    created_at=_now(),
                )
            )
        self.events.publish(
            "update_available" if status == "ACCEPTED" else "update_rejected",
            None,
            {"run_id": run_id, "status": status},
        )
        return {"run_id": run_id, "fixture": fixture, "status": status, **details}

    def package_acceptance(self) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.scalar(
                select(PackageAcceptanceRun).order_by(PackageAcceptanceRun.created_at.desc())
            )
            return {
                "status": row.status if row else "NOT_RUN",
                "run_id": row.id if row else None,
                "summary": json.loads(row.summary_json) if row else {},
                "current_platform": f"{platform.system()}-{platform.machine()}",
            }

    def record_package_acceptance(self, status: str, summary: dict[str, Any]) -> dict[str, Any]:
        if status not in {"PASS", "FAIL", "PARTIAL"}:
            raise TechnicalPreviewError("PACKAGE_ACCEPTANCE_STATUS_INVALID")
        run_id = str(uuid.uuid4())
        safe_summary = {
            key: value
            for key, value in summary.items()
            if key in {"self_test", "demo_lab", "apply", "rollback", "crash_recovery", "cleanup"}
        }
        with self.sessions.begin() as session:
            session.add(
                PackageAcceptanceRun(
                    id=run_id,
                    status=status,
                    summary_json=_json(safe_summary),
                    created_at=_now(),
                )
            )
        self.events.publish(
            "package_acceptance_completed", None, {"run_id": run_id, "status": status}
        )
        return {"run_id": run_id, "status": status, "summary": safe_summary}

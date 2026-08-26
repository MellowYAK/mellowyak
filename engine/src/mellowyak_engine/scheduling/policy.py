from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorMonitoringPolicy,
    MonitoringPolicy,
    Project,
    ProjectMonitoringPolicy,
    ProtectedBehavior,
    QuietModeState,
    SnapshotMilestone,
    TechnicalPreviewPreference,
)

PROJECT_MODES = frozenset(
    {"OBSERVE_ONLY", "ASK_BEFORE_CHECKS", "AUTO_SAFE", "MANUAL_ONLY", "PAUSED"}
)
BEHAVIOR_MODES = frozenset({"AUTOMATIC", "ASK", "MANUAL_ONLY", "DISABLED"})
RUNTIME_POLICIES = frozenset(
    {
        "REUSE_APPROVED_RUNNING_RUNTIME",
        "START_APPROVED_MANAGED_RUNTIME",
        "ASK_BEFORE_START",
        "NEVER_START_AUTOMATICALLY",
    }
)


class MonitoringPolicyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str) -> Any:
    return json.loads(value)


class MonitoringPolicyService:
    """Immutable policy revisions with conservative installation defaults."""

    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events
        self._ensure_global()

    def _ensure_global(self) -> None:
        with self.sessions.begin() as session:
            if session.scalar(select(func.count(MonitoringPolicy.id))) == 0:
                session.add(self._new_global(1, {}))

    @staticmethod
    def _new_global(version: int, values: dict[str, Any]) -> MonitoringPolicy:
        return MonitoringPolicy(
            id=str(uuid.uuid4()),
            version=version,
            source_observation_enabled=bool(values.get("source_observation_enabled", True)),
            automatic_checking_enabled=bool(values.get("automatic_checking_enabled", True)),
            default_project_mode=str(values.get("default_project_mode", "ASK_BEFORE_CHECKS")),
            max_concurrent_projects=max(1, min(int(values.get("max_concurrent_projects", 2)), 8)),
            max_concurrent_probes=max(1, min(int(values.get("max_concurrent_probes", 2)), 8)),
            max_concurrent_browser_probes=max(
                1, min(int(values.get("max_concurrent_browser_probes", 1)), 2)
            ),
            daily_runtime_budget_seconds=max(
                60, min(int(values.get("daily_runtime_budget_seconds", 3600)), 86_400)
            ),
            default_activity_mode=str(values.get("default_activity_mode", "normal")),
            allowed_hours_json=_json(values.get("allowed_hours", {})),
            battery_policy_json=_json(
                values.get("battery_policy", {"defer_noncritical_browser": True})
            ),
            quiet_policy_json=_json(
                values.get("quiet_policy", {"persist_alerts": True, "suppress_native": True})
            ),
            runtime_start_default=str(values.get("runtime_start_default", "ASK_BEFORE_START")),
            notification_policy_json=_json(
                values.get("notification_policy", {"confirmed": "native_once", "watch": "in_app"})
            ),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _global(row: MonitoringPolicy) -> dict[str, Any]:
        return {
            "id": row.id,
            "version": row.version,
            "source_observation_enabled": row.source_observation_enabled,
            "automatic_checking_enabled": row.automatic_checking_enabled,
            "default_project_mode": row.default_project_mode,
            "max_concurrent_projects": row.max_concurrent_projects,
            "max_concurrent_probes": row.max_concurrent_probes,
            "max_concurrent_browser_probes": row.max_concurrent_browser_probes,
            "daily_runtime_budget_seconds": row.daily_runtime_budget_seconds,
            "default_activity_mode": row.default_activity_mode,
            "allowed_hours": _load(row.allowed_hours_json),
            "battery_policy": _load(row.battery_policy_json),
            "quiet_policy": _load(row.quiet_policy_json),
            "runtime_start_default": row.runtime_start_default,
            "notification_policy": _load(row.notification_policy_json),
            "created_at": row.created_at.isoformat(),
        }

    def global_policy(self) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.scalars(
                select(MonitoringPolicy).order_by(MonitoringPolicy.version.desc()).limit(1)
            ).one()
            return self._global(row)

    def update_global(self, values: dict[str, Any]) -> dict[str, Any]:
        current = self.global_policy()
        merged = current | values
        if merged["default_project_mode"] not in PROJECT_MODES:
            raise MonitoringPolicyError("PROJECT_MONITORING_MODE_INVALID")
        if merged["runtime_start_default"] not in RUNTIME_POLICIES:
            raise MonitoringPolicyError("RUNTIME_START_POLICY_INVALID")
        with self.sessions.begin() as session:
            row = self._new_global(int(current["version"]) + 1, merged)
            session.add(row)
            session.flush()
            result = self._global(row)
        self.events.publish(
            "monitoring_policy_changed", None, {"scope": "GLOBAL", "version": result["version"]}
        )
        return result

    @staticmethod
    def _project_row(
        project_id: str, version: int, values: dict[str, Any]
    ) -> ProjectMonitoringPolicy:
        return ProjectMonitoringPolicy(
            id=str(uuid.uuid4()),
            project_id=project_id,
            version=version,
            mode=str(values.get("mode", "ASK_BEFORE_CHECKS")),
            settle_seconds=max(0.5, min(float(values.get("settle_seconds", 2.0)), 15.0)),
            max_episode_seconds=max(5, min(int(values.get("max_episode_seconds", 60)), 300)),
            max_checks_per_episode=max(1, min(int(values.get("max_checks_per_episode", 10)), 100)),
            max_automatic_duration_seconds=max(
                5, min(int(values.get("max_automatic_duration_seconds", 300)), 1800)
            ),
            runtime_start_policy=str(values.get("runtime_start_policy", "ASK_BEFORE_START")),
            network_policy=str(values.get("network_policy", "LOOPBACK_ONLY")),
            resource_budget_json=_json(values.get("resource_budget", {"max_concurrent": 1})),
            notification_policy_json=_json(values.get("notification_policy", {})),
            allowed_hours_json=_json(values.get("allowed_hours", {})),
            muted=bool(values.get("muted", False)),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _project(row: ProjectMonitoringPolicy) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "version": row.version,
            "mode": row.mode,
            "settle_seconds": row.settle_seconds,
            "max_episode_seconds": row.max_episode_seconds,
            "max_checks_per_episode": row.max_checks_per_episode,
            "max_automatic_duration_seconds": row.max_automatic_duration_seconds,
            "runtime_start_policy": row.runtime_start_policy,
            "network_policy": row.network_policy,
            "resource_budget": _load(row.resource_budget_json),
            "notification_policy": _load(row.notification_policy_json),
            "allowed_hours": _load(row.allowed_hours_json),
            "muted": row.muted,
            "created_at": row.created_at.isoformat(),
        }

    def project_policy(self, project_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            if session.get(Project, project_id) is None:
                raise MonitoringPolicyError("PROJECT_NOT_FOUND")
            row = session.scalars(
                select(ProjectMonitoringPolicy)
                .where(ProjectMonitoringPolicy.project_id == project_id)
                .order_by(ProjectMonitoringPolicy.version.desc())
                .limit(1)
            ).first()
            if row is None:
                row = self._project_row(
                    project_id, 1, {"mode": self.global_policy()["default_project_mode"]}
                )
                session.add(row)
                session.flush()
            return self._project(row)

    def update_project(self, project_id: str, values: dict[str, Any]) -> dict[str, Any]:
        current = self.project_policy(project_id)
        merged = current | values
        if merged["mode"] not in PROJECT_MODES:
            raise MonitoringPolicyError("PROJECT_MONITORING_MODE_INVALID")
        if merged["runtime_start_policy"] not in RUNTIME_POLICIES:
            raise MonitoringPolicyError("RUNTIME_START_POLICY_INVALID")
        with self.sessions.begin() as session:
            row = self._project_row(project_id, int(current["version"]) + 1, merged)
            session.add(row)
            session.flush()
            result = self._project(row)
        self.events.publish(
            "monitoring_policy_changed",
            project_id,
            {"scope": "PROJECT", "version": result["version"]},
        )
        return result

    @staticmethod
    def _behavior_row(
        project_id: str, behavior_id: str, version: int, values: dict[str, Any]
    ) -> BehaviorMonitoringPolicy:
        return BehaviorMonitoringPolicy(
            id=str(uuid.uuid4()),
            project_id=project_id,
            behavior_id=behavior_id,
            version=version,
            mode=str(values.get("mode", "ASK")),
            retry_policy_json=_json(
                values.get(
                    "retry_policy",
                    {"max_attempts": 2, "retry_delay_seconds": 1, "quarantine_threshold": 3},
                )
            ),
            max_duration_seconds=max(5, min(int(values.get("max_duration_seconds", 120)), 1800)),
            automatic_runtime_eligible=bool(values.get("automatic_runtime_eligible", False)),
            sentinel=bool(values.get("sentinel", False)),
            notification_escalation=str(values.get("notification_escalation", "CONFIRMED")),
            flaky_handling=str(values.get("flaky_handling", "BOUNDED_RETRY")),
            resolution_policy=str(values.get("resolution_policy", "COMPARABLE_PASS")),
            muted=bool(values.get("muted", False)),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _behavior(row: BehaviorMonitoringPolicy) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "behavior_id": row.behavior_id,
            "version": row.version,
            "mode": row.mode,
            "retry_policy": _load(row.retry_policy_json),
            "max_duration_seconds": row.max_duration_seconds,
            "automatic_runtime_eligible": row.automatic_runtime_eligible,
            "sentinel": row.sentinel,
            "notification_escalation": row.notification_escalation,
            "flaky_handling": row.flaky_handling,
            "resolution_policy": row.resolution_policy,
            "muted": row.muted,
            "created_at": row.created_at.isoformat(),
        }

    def behavior_policy(self, project_id: str, behavior_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            behavior = session.get(ProtectedBehavior, behavior_id)
            if behavior is None or behavior.project_id != project_id:
                raise MonitoringPolicyError("BEHAVIOR_NOT_FOUND")
            row = session.scalars(
                select(BehaviorMonitoringPolicy)
                .where(BehaviorMonitoringPolicy.behavior_id == behavior_id)
                .order_by(BehaviorMonitoringPolicy.version.desc())
                .limit(1)
            ).first()
            if row is None:
                row = self._behavior_row(project_id, behavior_id, 1, {})
                session.add(row)
                session.flush()
            return self._behavior(row)

    def update_behavior(
        self, project_id: str, behavior_id: str, values: dict[str, Any]
    ) -> dict[str, Any]:
        current = self.behavior_policy(project_id, behavior_id)
        merged = current | values
        if merged["mode"] not in BEHAVIOR_MODES:
            raise MonitoringPolicyError("BEHAVIOR_MONITORING_MODE_INVALID")
        with self.sessions.begin() as session:
            row = self._behavior_row(project_id, behavior_id, int(current["version"]) + 1, merged)
            session.add(row)
            session.flush()
            result = self._behavior(row)
        self.events.publish(
            "monitoring_policy_changed",
            project_id,
            {"scope": "BEHAVIOR", "behavior_id": behavior_id, "version": result["version"]},
        )
        return result

    def eligibility(
        self, project_id: str, behavior_id: str | None, probe_version: Any, probe_type: str
    ) -> dict[str, Any]:
        global_policy = self.global_policy()
        project_policy = self.project_policy(project_id)
        behavior_policy = self.behavior_policy(project_id, behavior_id) if behavior_id else None
        with self.sessions() as session:
            project = session.get(Project, project_id)
            mode = session.get(TechnicalPreviewPreference, 1)
            quiet = session.get(QuietModeState, 1)
            baseline = session.scalars(
                select(SnapshotMilestone)
                .where(
                    SnapshotMilestone.project_id == project_id,
                    SnapshotMilestone.probe_version_id == probe_version.id,
                    SnapshotMilestone.status == "ACCEPTED",
                )
                .limit(1)
            ).first()
        reasons: list[str] = []
        deferred = False
        if (
            project is None
            or project.disconnected_at is not None
            or project.monitoring_status != "active"
        ):
            reasons.append("PROJECT_NOT_ACTIVE")
        if not global_policy["automatic_checking_enabled"]:
            reasons.append("GLOBAL_AUTOMATIC_CHECKS_DISABLED")
        if project_policy["mode"] != "AUTO_SAFE":
            reasons.append(f"PROJECT_MODE_{project_policy['mode']}")
        if behavior_policy and behavior_policy["mode"] != "AUTOMATIC":
            reasons.append(f"BEHAVIOR_MODE_{behavior_policy['mode']}")
        if probe_version.approved_at is None:
            reasons.append("PROBE_VERSION_NOT_APPROVED")
        if baseline is None:
            reasons.append("KNOWN_GOOD_BASELINE_REQUIRED")
        if probe_version.runtime_profile_version_id and not (
            behavior_policy and behavior_policy["automatic_runtime_eligible"]
        ):
            reasons.append("AUTOMATIC_RUNTIME_NOT_APPROVED")
        activity = mode.activity_mode if mode else "normal"
        if (
            activity == "battery_saver"
            and probe_type == "BROWSER"
            and not (behavior_policy and behavior_policy["sentinel"])
        ):
            reasons.append("BATTERY_SAVER_NONCRITICAL_BROWSER")
            deferred = True
        return {
            "eligible": not reasons,
            "deferred": deferred,
            "reason_codes": reasons or ["AUTOMATIC_SAFE_ELIGIBLE"],
            "activity_mode": activity,
            "quiet_mode": bool(quiet and quiet.active),
            "policy_versions": {
                "global": global_policy["version"],
                "project": project_policy["version"],
                "behavior": behavior_policy["version"] if behavior_policy else None,
            },
        }

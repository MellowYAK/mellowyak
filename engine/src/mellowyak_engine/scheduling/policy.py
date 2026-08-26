from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorMonitoringPolicy,
    MonitoringPolicy,
    OrchestrationJob,
    OrchestrationJobAttempt,
    ProbeVersion,
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
DEFERRED_POLICY_REASONS = frozenset(
    {
        "BATTERY_SAVER_NONCRITICAL_BROWSER",
        "DAILY_RUNTIME_BUDGET_EXHAUSTED",
        "OUTSIDE_ALLOWED_HOURS",
    }
)
RUNTIME_ACCOUNTED_STATES = frozenset({"RUNNING", "COMPLETED", "FAILED", "CANCELLED"})
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class MonitoringPolicyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str) -> Any:
    return json.loads(value)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _clock_now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None:
        raise MonitoringPolicyError("SCHEDULER_CLOCK_MUST_BE_TIMEZONE_AWARE")
    return value.astimezone(UTC)


def _parse_hhmm(value: object) -> time:
    try:
        parsed = datetime.strptime(str(value), "%H:%M")
    except ValueError as error:
        raise MonitoringPolicyError("ALLOWED_HOURS_TIME_INVALID") from error
    return time(parsed.hour, parsed.minute)


def _allowed_hours(value: object) -> dict[str, Any]:
    if value in ({}, None):
        return {}
    if not isinstance(value, dict):
        raise MonitoringPolicyError("ALLOWED_HOURS_INVALID")
    enabled = bool(value.get("enabled", True))
    if not enabled:
        return {"enabled": False}
    timezone_name = str(value.get("timezone", "")).strip()
    if not timezone_name:
        raise MonitoringPolicyError("ALLOWED_HOURS_TIMEZONE_REQUIRED")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise MonitoringPolicyError("ALLOWED_HOURS_TIMEZONE_INVALID") from error
    start = _parse_hhmm(value.get("start", "00:00"))
    end = _parse_hhmm(value.get("end", "00:00"))
    raw_weekdays = value.get("weekdays", list(range(7)))
    if not isinstance(raw_weekdays, list) or not raw_weekdays:
        raise MonitoringPolicyError("ALLOWED_HOURS_WEEKDAYS_INVALID")
    weekdays: set[int] = set()
    for raw in raw_weekdays:
        day = _WEEKDAYS.get(str(raw).lower()) if isinstance(raw, str) else raw
        if not isinstance(day, int) or isinstance(day, bool) or day < 0 or day > 6:
            raise MonitoringPolicyError("ALLOWED_HOURS_WEEKDAYS_INVALID")
        weekdays.add(day)
    return {
        "enabled": True,
        "timezone": timezone_name,
        "weekdays": sorted(weekdays),
        "start": start.strftime("%H:%M"),
        "end": end.strftime("%H:%M"),
    }


def _system_zone() -> tuple[str, ZoneInfo]:
    candidates = [os.environ.get("TZ", "").strip()]
    try:
        resolved = str(Path("/etc/localtime").resolve())
        marker = "/zoneinfo/"
        if marker in resolved:
            candidates.append(resolved.split(marker, 1)[1])
    except OSError:
        pass
    for name in candidates:
        if not name:
            continue
        try:
            return name, ZoneInfo(name)
        except ZoneInfoNotFoundError:
            continue
    return "UTC", ZoneInfo("UTC")


def _local_boundary(day: date, local_time: time, zone: ZoneInfo) -> datetime:
    """Return a real local wall-clock boundary, advancing across DST gaps."""
    candidate = datetime.combine(day, local_time, tzinfo=zone)
    for _ in range(181):
        normalized = candidate.astimezone(UTC).astimezone(zone)
        if normalized.date() == candidate.date() and normalized.time().replace(
            tzinfo=None
        ) == candidate.time().replace(tzinfo=None):
            return candidate
        candidate += timedelta(minutes=1)
    return candidate


def _hours_status(now: datetime, config: dict[str, Any]) -> dict[str, Any]:
    normalized = _allowed_hours(config)
    if not normalized or not normalized.get("enabled", True):
        return {"allowed": True, "next_eligible_at": None, "configuration": normalized}
    zone = ZoneInfo(str(normalized["timezone"]))
    local_now = now.astimezone(zone)
    weekdays = set(normalized["weekdays"])
    start = _parse_hhmm(normalized["start"])
    end = _parse_hhmm(normalized["end"])
    current_time = local_now.timetz().replace(tzinfo=None)
    if start == end:
        allowed = local_now.weekday() in weekdays
    elif start < end:
        allowed = local_now.weekday() in weekdays and start <= current_time < end
    else:
        previous = (local_now.weekday() - 1) % 7
        allowed = (local_now.weekday() in weekdays and current_time >= start) or (
            previous in weekdays and current_time < end
        )
    next_eligible: datetime | None = None
    if not allowed:
        for offset in range(8):
            candidate_day = local_now.date() + timedelta(days=offset)
            if candidate_day.weekday() not in weekdays:
                continue
            candidate = _local_boundary(candidate_day, start, zone)
            if candidate > local_now:
                next_eligible = candidate.astimezone(UTC)
                break
    return {
        "allowed": allowed,
        "next_eligible_at": next_eligible.isoformat() if next_eligible else None,
        "configuration": normalized,
    }


def _overlap_seconds(
    started: datetime, completed: datetime, lower: datetime, upper: datetime
) -> float:
    start = max(_utc(started), lower)
    end = min(_utc(completed), upper)
    return max(0.0, (end - start).total_seconds())


def _resource_budget(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MonitoringPolicyError("PROJECT_RESOURCE_BUDGET_INVALID")
    normalized = dict(value)
    if "daily_runtime_budget_seconds" in normalized:
        try:
            budget = int(normalized["daily_runtime_budget_seconds"])
        except (TypeError, ValueError) as error:
            raise MonitoringPolicyError("PROJECT_DAILY_RUNTIME_BUDGET_INVALID") from error
        if budget < 60 or budget > 86_400:
            raise MonitoringPolicyError("PROJECT_DAILY_RUNTIME_BUDGET_INVALID")
        normalized["daily_runtime_budget_seconds"] = budget
    return normalized


class MonitoringPolicyService:
    """Immutable policy revisions with conservative installation defaults."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        events: LocalEventBus,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.sessions = sessions
        self.events = events
        self._clock = clock or (lambda: datetime.now(UTC))
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
            allowed_hours_json=_json(_allowed_hours(values.get("allowed_hours", {}))),
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
        _allowed_hours(merged.get("allowed_hours", {}))
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
            resource_budget_json=_json(
                _resource_budget(values.get("resource_budget", {"max_concurrent": 1}))
            ),
            notification_policy_json=_json(values.get("notification_policy", {})),
            allowed_hours_json=_json(_allowed_hours(values.get("allowed_hours", {}))),
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
        _allowed_hours(merged.get("allowed_hours", {}))
        _resource_budget(merged.get("resource_budget", {}))
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

    def _runtime_usage(
        self, project_id: str, now: datetime, timezone_name: str | None
    ) -> dict[str, Any]:
        resolved_timezone, zone = (
            (timezone_name, ZoneInfo(timezone_name)) if timezone_name else _system_zone()
        )
        local_now = now.astimezone(zone)
        lower = _local_boundary(local_now.date(), time.min, zone).astimezone(UTC)
        upper = _local_boundary(local_now.date() + timedelta(days=1), time.min, zone).astimezone(
            UTC
        )
        with self.sessions() as session:
            jobs = session.scalars(
                select(OrchestrationJob).where(
                    OrchestrationJob.started_at.is_not(None),
                    OrchestrationJob.state.in_(list(RUNTIME_ACCOUNTED_STATES)),
                )
            ).all()
            interrupted = session.scalars(
                select(OrchestrationJobAttempt).where(
                    OrchestrationJobAttempt.reason == "ENGINE_RESTART_INTERRUPTED"
                )
            ).all()
            versions = (
                {
                    row.id: row.timeout_seconds
                    for row in session.scalars(
                        select(ProbeVersion).where(
                            ProbeVersion.id.in_({job.probe_version_id for job in jobs})
                        )
                    ).all()
                }
                if jobs
                else {}
            )
        global_consumed = project_consumed = global_reserved = project_reserved = 0.0
        for job in jobs:
            started = _utc(job.started_at) if job.started_at else now
            if job.state == "RUNNING":
                elapsed = _overlap_seconds(started, now, lower, upper)
                reservation = max(elapsed, float(versions.get(job.probe_version_id, 0)))
                global_reserved += reservation
                if job.project_id == project_id:
                    project_reserved += reservation
            elif job.completed_at:
                duration = _overlap_seconds(started, job.completed_at, lower, upper)
                global_consumed += duration
                if job.project_id == project_id:
                    project_consumed += duration
        for attempt in interrupted:
            duration = _overlap_seconds(attempt.started_at, attempt.completed_at, lower, upper)
            global_consumed += duration
            if attempt.project_id == project_id:
                project_consumed += duration
        return {
            "local_day": local_now.date().isoformat(),
            "timezone": resolved_timezone,
            "global_consumed_seconds": round(global_consumed, 3),
            "global_reserved_seconds": round(global_reserved, 3),
            "project_consumed_seconds": round(project_consumed, 3),
            "project_reserved_seconds": round(project_reserved, 3),
        }

    def eligibility(
        self, project_id: str, behavior_id: str | None, probe_version: Any, probe_type: str
    ) -> dict[str, Any]:
        global_policy = self.global_policy()
        project_policy = self.project_policy(project_id)
        behavior_policy = self.behavior_policy(project_id, behavior_id) if behavior_id else None
        now = _clock_now(self._clock)
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
        blocking_reasons: list[str] = []
        deferred_reasons: list[str] = []
        if (
            project is None
            or project.disconnected_at is not None
            or project.monitoring_status != "active"
        ):
            blocking_reasons.append("PROJECT_NOT_ACTIVE")
        if not global_policy["automatic_checking_enabled"]:
            blocking_reasons.append("GLOBAL_AUTOMATIC_CHECKS_DISABLED")
        if project_policy["mode"] != "AUTO_SAFE":
            blocking_reasons.append(f"PROJECT_MODE_{project_policy['mode']}")
        if behavior_policy and behavior_policy["mode"] != "AUTOMATIC":
            blocking_reasons.append(f"BEHAVIOR_MODE_{behavior_policy['mode']}")
        if probe_version.approved_at is None:
            blocking_reasons.append("PROBE_VERSION_NOT_APPROVED")
        if baseline is None:
            blocking_reasons.append("KNOWN_GOOD_BASELINE_REQUIRED")
        if probe_version.runtime_profile_version_id and not (
            behavior_policy and behavior_policy["automatic_runtime_eligible"]
        ):
            blocking_reasons.append("AUTOMATIC_RUNTIME_NOT_APPROVED")
        activity = mode.activity_mode if mode else "normal"
        if (
            activity == "battery_saver"
            and probe_type == "BROWSER"
            and not (behavior_policy and behavior_policy["sentinel"])
        ):
            deferred_reasons.append("BATTERY_SAVER_NONCRITICAL_BROWSER")

        project_hours = (
            project_policy.get("allowed_hours") or global_policy.get("allowed_hours") or {}
        )
        hours = _hours_status(now, project_hours)
        if not hours["allowed"]:
            deferred_reasons.append("OUTSIDE_ALLOWED_HOURS")
        timezone_name = (
            str(hours["configuration"].get("timezone"))
            if hours["configuration"].get("timezone")
            else None
        )
        usage = self._runtime_usage(project_id, now, timezone_name)
        requested = min(
            int(project_policy["max_automatic_duration_seconds"]),
            int(getattr(probe_version, "timeout_seconds", 300)),
            int(behavior_policy["max_duration_seconds"]) if behavior_policy else 300,
        )
        resource_budget = project_policy.get("resource_budget", {})
        project_limit = int(
            resource_budget.get(
                "daily_runtime_budget_seconds", global_policy["daily_runtime_budget_seconds"]
            )
        )
        global_limit = int(global_policy["daily_runtime_budget_seconds"])
        global_projected = (
            usage["global_consumed_seconds"] + usage["global_reserved_seconds"] + requested
        )
        project_projected = (
            usage["project_consumed_seconds"] + usage["project_reserved_seconds"] + requested
        )
        if global_projected > global_limit or project_projected > project_limit:
            deferred_reasons.append("DAILY_RUNTIME_BUDGET_EXHAUSTED")
        reasons = blocking_reasons + deferred_reasons
        deferred = not blocking_reasons and bool(deferred_reasons)
        reason_details = [
            {
                "code": code,
                "message_key": f"phase13.reason.{code}",
                "known_fact": True,
                "safe_action": ("RUN_NOW" if code in DEFERRED_POLICY_REASONS else "REVIEW_POLICY"),
                "next_eligible_at": (
                    hours["next_eligible_at"] if code == "OUTSIDE_ALLOWED_HOURS" else None
                ),
            }
            for code in reasons
        ]
        return {
            "eligible": not reasons,
            "deferred": deferred,
            "reason_codes": reasons or ["AUTOMATIC_SAFE_ELIGIBLE"],
            "reason_details": reason_details,
            "activity_mode": activity,
            "quiet_mode": bool(quiet and quiet.active),
            "evaluated_at": now.isoformat(),
            "allowed_hours": hours,
            "runtime_budget": {
                **usage,
                "requested_reservation_seconds": requested,
                "global_limit_seconds": global_limit,
                "project_limit_seconds": project_limit,
                "global_projected_seconds": round(global_projected, 3),
                "project_projected_seconds": round(project_projected, 3),
            },
            "policy_versions": {
                "global": global_policy["version"],
                "project": project_policy["version"],
                "behavior": behavior_policy["version"] if behavior_policy else None,
            },
        }

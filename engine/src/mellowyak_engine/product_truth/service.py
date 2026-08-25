from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.db.models import (
    Alert,
    ApplyTransaction,
    BehaviorBaseline,
    BehaviorLink,
    BehaviorVersion,
    ProbeDefinition,
    ProbeRun,
    Project,
    ProjectChange,
    ProjectLifecycleEvent,
    ProtectedBehavior,
    RegressionFinding,
    RuntimeInstance,
    SignalClassification,
    SnapshotMilestone,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.technical_preview.service import TechnicalPreviewService


def _load(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class ProductTruthService:
    """Read-only product aggregates over the existing Phase 1–9 entities."""

    def __init__(
        self,
        sessions: sessionmaker,
        technical_preview: TechnicalPreviewService,
    ) -> None:
        self.sessions = sessions
        self.technical_preview = technical_preview

    @staticmethod
    def _project(session: Any, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise ValueError("PROJECT_NOT_FOUND")
        return project

    @staticmethod
    def _latest(session: Any, model: Any, project_id: str, order: Any) -> Any:
        return session.scalars(
            select(model).where(model.project_id == project_id).order_by(order.desc()).limit(1)
        ).first()

    @staticmethod
    def _count(session: Any, model: Any, *criteria: Any) -> int:
        return int(session.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)

    def _latest_check(self, session: Any, project_id: str) -> dict[str, Any] | None:
        run = self._latest(session, ProbeRun, project_id, ProbeRun.completed_at)
        if run is None:
            return None
        probe = session.get(ProbeDefinition, run.probe_id)
        behavior = session.get(ProtectedBehavior, probe.behavior_id) if probe else None
        duration_ms = None
        if run.started_at and run.completed_at:
            duration_ms = round((run.completed_at - run.started_at).total_seconds() * 1000, 1)
        return {
            "id": run.id,
            "name": probe.display_name if probe else run.probe_id,
            "behavior_id": behavior.id if behavior else None,
            "behavior_name": behavior.display_name if behavior else None,
            "result": run.result,
            "status": run.status,
            "source_identity": _load(run.source_identity_json, {}),
            "runtime_profile_version_id": run.runtime_profile_version_id,
            "duration_ms": duration_ms,
            "attempt_count": run.attempt_count,
            "expected": _load(run.expected_json, {}),
            "observed": _load(run.observed_json, {}),
            "evidence": _load(run.evidence_json, {}),
            "limitations": _load(run.limitations_json, []),
            "completed_at": _iso(run.completed_at),
        }

    def _project_summary(self, session: Any, project: Project) -> dict[str, Any]:
        project_id = project.id
        episode = self._latest(session, SourceEpisode, project_id, SourceEpisode.started_at)
        snapshot = self._latest(session, SourceSnapshot, project_id, SourceSnapshot.created_at)
        check = self._latest_check(session, project_id)
        runtime = self._latest(session, RuntimeInstance, project_id, RuntimeInstance.started_at)
        protected_count = self._count(
            session,
            ProtectedBehavior,
            ProtectedBehavior.project_id == project_id,
            ProtectedBehavior.lifecycle_state == "PROTECTED",
            ProtectedBehavior.archived_at.is_(None),
        )
        regression_count = self._count(
            session,
            RegressionFinding,
            RegressionFinding.project_id == project_id,
            RegressionFinding.resolved_at.is_(None),
        )
        recovery_count = self._count(
            session,
            ApplyTransaction,
            ApplyTransaction.project_id == project_id,
            ApplyTransaction.state == "FAILED_RECOVERY_REQUIRED",
        )
        storage_issue = bool(snapshot and snapshot.integrity_status != "VERIFIED")
        limitations: list[str] = []
        if protected_count == 0:
            limitations.append("NO_PROTECTED_BEHAVIORS")
        if project.runtime_setup_status != "READY":
            limitations.append(project.runtime_setup_status or "RUNTIME_NOT_CONFIGURED")
        if check is None:
            limitations.append("NO_CHECK_RESULT")
        elif check["result"] not in {"PASS", "PASSED"}:
            limitations.append(f"LATEST_CHECK_{check['result']}")
        if not project.source_available:
            state = "DISCONNECTED"
        elif project.monitoring_status != "active":
            state = "PAUSED"
        elif recovery_count or regression_count or storage_issue:
            state = "NEEDS_ATTENTION"
        elif limitations:
            state = "READY_WITH_LIMITS"
        else:
            state = "NO_CONFIRMED_ISSUE"
        last_activity = max(
            [
                value
                for value in (
                    project.updated_at,
                    episode.started_at if episode else None,
                    snapshot.created_at if snapshot else None,
                    runtime.started_at if runtime else None,
                )
                if value is not None
            ],
            default=project.created_at,
        )
        return {
            "id": project.id,
            "display_name": project.display_name,
            "state": state,
            "monitoring_state": project.monitoring_status,
            "source_available": project.source_available,
            "runtime_state": runtime.status if runtime else project.runtime_setup_status,
            "last_episode": self._episode_summary(session, episode) if episode else None,
            "last_save_point": self._snapshot_summary(snapshot),
            "protected_behavior_count": protected_count,
            "latest_check": check,
            "open_regression_count": regression_count,
            "recovery_required_count": recovery_count,
            "last_activity_at": _iso(last_activity),
            "limitations": limitations,
        }

    @staticmethod
    def _snapshot_summary(snapshot: SourceSnapshot | None) -> dict[str, Any] | None:
        if snapshot is None:
            return None
        return {
            "id": snapshot.id,
            "creation_reason": snapshot.creation_reason,
            "integrity_status": snapshot.integrity_status,
            "included_count": snapshot.included_count,
            "logical_bytes": snapshot.logical_bytes,
            "reused_bytes": snapshot.reused_bytes,
            "created_at": _iso(snapshot.created_at),
        }

    def _episode_summary(self, session: Any, episode: SourceEpisode) -> dict[str, Any]:
        checks = session.scalars(
            select(ProbeRun)
            .where(ProbeRun.project_id == episode.project_id, ProbeRun.episode_id == episode.id)
            .order_by(ProbeRun.started_at)
        ).all()
        signal = session.scalars(
            select(SignalClassification)
            .where(
                SignalClassification.project_id == episode.project_id,
                SignalClassification.episode_id == episode.id,
            )
            .order_by(SignalClassification.created_at.desc())
            .limit(1)
        ).first()
        added = _load(episode.added_paths_json, [])
        modified = _load(episode.modified_paths_json, [])
        deleted = _load(episode.deleted_paths_json, [])
        renamed = _load(episode.renamed_paths_json, [])
        return {
            "id": episode.id,
            "started_at": _iso(episode.started_at),
            "ended_at": _iso(episode.ended_at),
            "status": episode.status,
            "changed_count": len(added) + len(modified) + len(deleted) + len(renamed),
            "added_count": len(added),
            "modified_count": len(modified),
            "deleted_count": len(deleted),
            "dependency_change_count": len(_load(episode.dependency_changes_json, [])),
            "snapshot_id": episode.resulting_snapshot_id,
            "snapshot_reused": bool(
                episode.resulting_snapshot_id
                and episode.base_snapshot_id == episode.resulting_snapshot_id
            ),
            "checks_run": len(checks),
            "checks_passed": sum(run.result in {"PASS", "PASSED"} for run in checks),
            "checks_failed": sum(run.result in {"FAIL", "FAILED"} for run in checks),
            "signal": signal.state if signal else "WATCH",
            "error_code": episode.error_code,
        }

    @staticmethod
    def _activity(
        event_id: str,
        project_id: str,
        event_type: str,
        created_at: datetime,
        entity_type: str,
        entity_id: str | None,
        state: str,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": event_id,
            "project_id": project_id,
            "event_type": event_type,
            "created_at": _iso(created_at),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "state": state,
            "facts": facts,
        }

    def _project_activity(self, session: Any, project_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in session.scalars(
            select(SourceEpisode)
            .where(SourceEpisode.project_id == project_id)
            .order_by(SourceEpisode.started_at.desc())
            .limit(100)
        ).all():
            items.append(
                self._activity(
                    row.id,
                    project_id,
                    "EPISODE_STABILIZED" if row.ended_at else "EPISODE_STARTED",
                    row.ended_at or row.started_at,
                    "episode",
                    row.id,
                    self._episode_summary(session, row)["signal"],
                    self._episode_summary(session, row),
                )
            )
        for row in session.scalars(
            select(ProbeRun)
            .where(ProbeRun.project_id == project_id)
            .order_by(ProbeRun.started_at.desc())
            .limit(100)
        ).all():
            probe = session.get(ProbeDefinition, row.probe_id)
            items.append(
                self._activity(
                    row.id,
                    project_id,
                    "CHECK_COMPLETED",
                    row.completed_at or row.started_at or datetime.min,
                    "check",
                    row.id,
                    row.result,
                    {
                        "episode_id": row.episode_id,
                        "check_name": probe.display_name if probe else row.probe_id,
                        "attempt_count": row.attempt_count,
                    },
                )
            )
        for row in session.scalars(
            select(RegressionFinding)
            .where(RegressionFinding.project_id == project_id)
            .order_by(RegressionFinding.created_at.desc())
            .limit(50)
        ).all():
            items.append(
                self._activity(
                    row.id,
                    project_id,
                    "REGRESSION_RESOLVED" if row.resolved_at else "REGRESSION_CONFIRMED",
                    row.resolved_at or row.created_at,
                    "regression",
                    row.id,
                    "RESOLVED" if row.resolved_at else row.status,
                    {"behavior_id": row.behavior_id, "change_id": row.change_id},
                )
            )
        for row in session.scalars(
            select(ApplyTransaction)
            .where(ApplyTransaction.project_id == project_id)
            .order_by(ApplyTransaction.updated_at.desc())
            .limit(50)
        ).all():
            items.append(
                self._activity(
                    row.id,
                    project_id,
                    "APPLY_TRANSACTION",
                    row.updated_at,
                    "apply",
                    row.id,
                    row.state,
                    {"candidate_id": row.candidate_id, "error_code": row.error_code},
                )
            )
        for row in session.scalars(
            select(ProjectLifecycleEvent)
            .where(ProjectLifecycleEvent.project_id == project_id)
            .order_by(ProjectLifecycleEvent.created_at.desc())
            .limit(50)
        ).all():
            items.append(
                self._activity(
                    row.id,
                    project_id,
                    row.event_type,
                    row.created_at,
                    "project",
                    project_id,
                    row.event_type,
                    _load(row.details_json, {}),
                )
            )
        items.sort(key=lambda item: item["created_at"] or "", reverse=True)
        return items

    def home_summary(self) -> dict[str, Any]:
        with self.sessions() as session:
            projects = session.scalars(
                select(Project).where(Project.archived_at.is_(None)).order_by(Project.display_name)
            ).all()
            summaries = [self._project_summary(session, project) for project in projects]
            counts = {
                "monitored": sum(item["monitoring_state"] == "active" for item in summaries),
                "paused": sum(item["state"] == "PAUSED" for item in summaries),
                "disconnected": sum(item["state"] == "DISCONNECTED" for item in summaries),
                "needs_setup": sum(item["state"] == "READY_WITH_LIMITS" for item in summaries),
                "confirmed_regressions": sum(item["open_regression_count"] for item in summaries),
                "needs_review": self._count(
                    session,
                    Alert,
                    Alert.resolved_at.is_(None),
                    Alert.title_key == "alerts.reviewTitle",
                ),
                "blocked_or_recovery": sum(item["recovery_required_count"] for item in summaries),
                "unread_alerts": self._count(
                    session, Alert, Alert.read_at.is_(None), Alert.resolved_at.is_(None)
                ),
            }
            attention = [
                item for item in summaries if item["state"] in {"NEEDS_ATTENTION", "DISCONNECTED"}
            ]
            activity: list[dict[str, Any]] = []
            for project in projects:
                activity.extend(self._project_activity(session, project.id)[:5])
            activity.sort(key=lambda item: item["created_at"] or "", reverse=True)
            if counts["confirmed_regressions"] or counts["blocked_or_recovery"]:
                state = "NEEDS_ATTENTION"
            elif summaries and all(item["state"] == "NO_CONFIRMED_ISSUE" for item in summaries):
                state = "EVERYTHING_LOOKS_OKAY"
            elif summaries:
                state = "NO_CONFIRMED_ISSUE_FOUND"
            else:
                state = "NO_PROJECTS"
            return {
                "state": state,
                "counts": counts,
                "projects": summaries,
                "attention": attention,
                "recent_activity": activity[:20],
                "known": ["LOCAL_DATABASE", "REGISTERED_PROJECTS", "RECORDED_CHECKS"],
                "unknowns": [] if state == "EVERYTHING_LOOKS_OKAY" else ["INCOMPLETE_COVERAGE"],
            }

    def project_overview(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = self._project(session, project_id)
            summary = self._project_summary(session, project)
            milestone = self._latest(
                session, SnapshotMilestone, project_id, SnapshotMilestone.created_at
            )
            snapshots = session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.project_id == project_id)
                .order_by(SourceSnapshot.created_at.desc())
                .limit(5)
            ).all()
            checks = session.scalars(
                select(ProbeRun)
                .where(ProbeRun.project_id == project_id)
                .order_by(ProbeRun.started_at.desc())
                .limit(5)
            ).all()
            latest_checks = []
            for run in checks:
                probe = session.get(ProbeDefinition, run.probe_id)
                behavior = (
                    session.get(ProtectedBehavior, probe.behavior_id)
                    if probe and probe.behavior_id
                    else None
                )
                latest_checks.append(
                    {
                        "id": run.id,
                        "name": probe.display_name if probe else run.probe_id,
                        "behavior_id": probe.behavior_id if probe else None,
                        "behavior_name": behavior.display_name if behavior else None,
                        "result": run.result,
                        "status": run.status,
                        "source_identity": _load(run.source_identity_json, {}),
                        "runtime_profile_version_id": run.runtime_profile_version_id,
                        "duration_ms": None,
                        "attempt_count": run.attempt_count,
                        "expected": _load(run.expected_json, {}),
                        "observed": _load(run.observed_json, {}),
                        "evidence": {},
                        "limitations": _load(run.limitations_json, []),
                        "completed_at": _iso(run.completed_at),
                    }
                )
            return {
                "project": summary,
                "source_identity": {
                    "branch": project.current_branch,
                    "head_sha": project.current_head_sha,
                    "worktree_fingerprint": project.current_worktree_fingerprint,
                },
                "last_known_good": (
                    {
                        "id": milestone.id,
                        "snapshot_id": milestone.snapshot_id,
                        "display_name": milestone.display_name,
                        "status": milestone.status,
                        "human_attested": milestone.human_attested,
                        "created_at": _iso(milestone.created_at),
                    }
                    if milestone
                    else None
                ),
                "latest_checks": latest_checks,
                "storage": {
                    "snapshot_count": self._count(
                        session, SourceSnapshot, SourceSnapshot.project_id == project_id
                    ),
                    "logical_bytes": sum(row.logical_bytes for row in snapshots),
                    "integrity_state": (
                        "ATTENTION"
                        if any(row.integrity_status != "VERIFIED" for row in snapshots)
                        else "VERIFIED"
                    ),
                    "retention_days": project.snapshot_retention_days,
                    "soft_cap_bytes": project.snapshot_soft_cap_bytes,
                },
                "recent_activity": self._project_activity(session, project_id)[:8],
                "known": ["SOURCE_IDENTITY", "RECORDED_EPISODES", "RECORDED_CHECKS"],
                "unknowns": summary["limitations"],
            }

    def activity(self, project_id: str, offset: int, limit: int) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            items = self._project_activity(session, project_id)
            bounded_limit = min(max(limit, 1), 50)
            bounded_offset = max(offset, 0)
            page = items[bounded_offset : bounded_offset + bounded_limit]
            return {
                "project_id": project_id,
                "items": page,
                "offset": bounded_offset,
                "limit": bounded_limit,
                "total": len(items),
                "has_more": bounded_offset + len(page) < len(items),
            }

    def episode_detail(self, project_id: str, episode_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            episode = session.get(SourceEpisode, episode_id)
            if episode is None or episode.project_id != project_id:
                raise ValueError("EPISODE_NOT_FOUND")
            runs = session.scalars(
                select(ProbeRun)
                .where(ProbeRun.project_id == project_id, ProbeRun.episode_id == episode_id)
                .order_by(ProbeRun.started_at)
            ).all()
            checks: list[dict[str, Any]] = []
            checked_behaviors: set[str] = set()
            may_be_affected: list[dict[str, Any]] = []
            for run in runs:
                probe = session.get(ProbeDefinition, run.probe_id)
                behavior = (
                    session.get(ProtectedBehavior, probe.behavior_id)
                    if probe and probe.behavior_id
                    else None
                )
                if behavior:
                    checked_behaviors.add(behavior.id)
                    links = session.scalars(
                        select(BehaviorLink).where(BehaviorLink.behavior_id == behavior.id)
                    ).all()
                    may_be_affected.append(
                        {
                            "behavior_id": behavior.id,
                            "behavior_name": behavior.display_name,
                            "provenance": sorted({link.provenance for link in links})
                            or ["PROBE_SELECTION"],
                        }
                    )
                checks.append(self._check_public(session, run))
            all_behaviors = session.scalars(
                select(ProtectedBehavior).where(
                    ProtectedBehavior.project_id == project_id,
                    ProtectedBehavior.archived_at.is_(None),
                )
            ).all()
            not_checked = [
                {
                    "behavior_id": behavior.id,
                    "behavior_name": behavior.display_name,
                    "reason_code": "NO_PROBE_RUN_FOR_EPISODE",
                }
                for behavior in all_behaviors
                if behavior.id not in checked_behaviors
            ]
            signal = session.scalars(
                select(SignalClassification)
                .where(
                    SignalClassification.project_id == project_id,
                    SignalClassification.episode_id == episode_id,
                )
                .order_by(SignalClassification.created_at.desc())
                .limit(1)
            ).first()
            changed = {
                "added": _load(episode.added_paths_json, []),
                "modified": _load(episode.modified_paths_json, []),
                "deleted": _load(episode.deleted_paths_json, []),
                "renamed": _load(episode.renamed_paths_json, []),
                "dependencies": _load(episode.dependency_changes_json, []),
            }
            return {
                "project_id": project_id,
                "episode": self._episode_summary(session, episode),
                "changed": changed,
                "may_be_affected": may_be_affected,
                "checks": checks,
                "not_checked": not_checked,
                "result": {
                    "signal": signal.state if signal else "WATCH",
                    "reason_codes": _load(signal.reason_codes_json, [])
                    if signal
                    else ["FILES_CHANGED_ONLY"],
                    "friendly_key": signal.friendly_key if signal else "episode.result.watch",
                },
                "technical": {
                    "base_snapshot_id": episode.base_snapshot_id,
                    "resulting_snapshot_id": episode.resulting_snapshot_id,
                    "git_anchor": _load(episode.git_anchor_json, {}),
                    "runtime_events": _load(episode.runtime_events_json, []),
                    "truncated": False,
                },
                "unknowns": ["ROOT_CAUSE_NOT_PROVEN"],
            }

    def _check_public(self, session: Any, run: ProbeRun) -> dict[str, Any]:
        probe = session.get(ProbeDefinition, run.probe_id)
        behavior = (
            session.get(ProtectedBehavior, probe.behavior_id)
            if probe and probe.behavior_id
            else None
        )
        duration_ms = None
        if run.started_at and run.completed_at:
            duration_ms = round((run.completed_at - run.started_at).total_seconds() * 1000, 1)
        return {
            "id": run.id,
            "name": probe.display_name if probe else run.probe_id,
            "behavior_id": behavior.id if behavior else None,
            "behavior_name": behavior.display_name if behavior else None,
            "result": run.result,
            "status": run.status,
            "source_identity": _load(run.source_identity_json, {}),
            "runtime_profile_version_id": run.runtime_profile_version_id,
            "duration_ms": duration_ms,
            "attempt_count": run.attempt_count,
            "expected": _load(run.expected_json, {}),
            "observed": _load(run.observed_json, {}),
            "evidence": _load(run.evidence_json, {}),
            "limitations": _load(run.limitations_json, []),
            "completed_at": _iso(run.completed_at),
        }

    def regression_detail(self, project_id: str, regression_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            regression = session.get(RegressionFinding, regression_id)
            if regression is None or regression.project_id != project_id:
                raise ValueError("REGRESSION_NOT_FOUND")
            behavior = session.get(ProtectedBehavior, regression.behavior_id)
            version = session.get(BehaviorVersion, regression.behavior_version_id)
            baseline = (
                session.get(BehaviorBaseline, regression.baseline_id)
                if regression.baseline_id
                else None
            )
            run = (
                session.get(ProbeRun, regression.probe_run_id) if regression.probe_run_id else None
            )
            signal = (
                session.get(SignalClassification, regression.signal_classification_id)
                if regression.signal_classification_id
                else None
            )
            change = session.get(ProjectChange, regression.change_id)
            milestone = session.scalars(
                select(SnapshotMilestone)
                .where(
                    SnapshotMilestone.project_id == project_id,
                    SnapshotMilestone.behavior_id == regression.behavior_id,
                )
                .order_by(SnapshotMilestone.created_at.desc())
                .limit(1)
            ).first()
            return {
                "id": regression.id,
                "project_id": project_id,
                "status": regression.status,
                "behavior": {
                    "id": behavior.id if behavior else regression.behavior_id,
                    "name": behavior.display_name if behavior else regression.behavior_id,
                    "expected_outcome": version.expected_outcome if version else "",
                },
                "last_known_good": {
                    "baseline_id": baseline.id if baseline else None,
                    "status": baseline.status if baseline else "UNKNOWN",
                    "snapshot_id": milestone.snapshot_id if milestone else None,
                    "save_point_name": milestone.display_name if milestone else None,
                    "source_identity": _load(baseline.source_revision_json, {}) if baseline else {},
                    "created_at": _iso(baseline.created_at) if baseline else None,
                },
                "current": (
                    self._check_public(session, run)
                    if run
                    else {
                        "id": regression.verification_run_item_id or regression.id,
                        "name": behavior.display_name if behavior else regression.behavior_id,
                        "behavior_id": regression.behavior_id,
                        "behavior_name": behavior.display_name if behavior else None,
                        "result": "FAIL",
                        "status": regression.status,
                        "source_identity": _load(regression.source_identity_json, {}),
                        "runtime_profile_version_id": None,
                        "duration_ms": None,
                        "attempt_count": 1,
                        "expected": {"outcome": version.expected_outcome if version else ""},
                        "observed": {},
                        "evidence": {},
                        "limitations": ["LEGACY_VERIFICATION_RECORD"],
                        "completed_at": _iso(regression.created_at),
                    }
                ),
                "changed": {
                    "change_id": regression.change_id,
                    "paths": _load(change.changed_paths_json, []) if change else [],
                },
                "selection": {
                    "reason": regression.decision_reason,
                    "relation_provenance": sorted(
                        {
                            link.provenance
                            for link in session.scalars(
                                select(BehaviorLink).where(
                                    BehaviorLink.behavior_id == regression.behavior_id
                                )
                            ).all()
                        }
                    ),
                },
                "reason_codes": _load(signal.reason_codes_json, [])
                if signal
                else ["DETERMINISTIC_CHECK_FAILED"],
                "evidence_timeline": [
                    self._activity(
                        regression.id,
                        project_id,
                        "REGRESSION_CONFIRMED",
                        regression.created_at,
                        "regression",
                        regression.id,
                        regression.status,
                        {"attempt_count": run.attempt_count if run else 1},
                    )
                ],
                "unknowns": ["ROOT_CAUSE_NOT_PROVEN", "BLAST_RADIUS_MAY_BE_INCOMPLETE"],
            }

    def diagnostics_overview(self) -> dict[str, Any]:
        diagnostics = self.technical_preview.diagnostics()
        facts = [
            {
                "key": "local_api",
                "state": diagnostics["local_api_state"],
                "value": diagnostics["loopback_address"],
            },
            {
                "key": "database",
                "state": "READY",
                "value": diagnostics["schema_migration"],
            },
            {
                "key": "storage",
                "state": "READY",
                "value": diagnostics["data_root_size_bytes"],
            },
            {
                "key": "browser_runtime",
                "state": (
                    "AVAILABLE" if diagnostics["browser_runtime_available"] else "UNAVAILABLE"
                ),
                "value": diagnostics["browser_runtime_available"],
            },
            {
                "key": "runtime_adapter",
                "state": (
                    "AVAILABLE" if diagnostics["runtime_adapter_available"] else "UNAVAILABLE"
                ),
                "value": diagnostics["runtime_adapter_available"],
            },
            {
                "key": "updater",
                "state": diagnostics["updater_state"],
                "value": diagnostics["updater_state"],
            },
            {
                "key": "signing",
                "state": diagnostics["signing_state"],
                "value": diagnostics["signing_state"],
            },
        ]
        limitations = []
        if diagnostics["signing_state"] != "VERIFIED":
            limitations.append("SIGNING_NOT_VERIFIED")
        if diagnostics["platform"] != "Darwin" or diagnostics["architecture"] != "x86_64":
            limitations.append("PLATFORM_NOT_RUNTIME_VERIFIED")
        return {
            "facts": facts,
            "counts": {
                "projects": diagnostics["projects"],
                "snapshot_objects": diagnostics["snapshot_objects"],
                "incomplete_transactions": diagnostics["incomplete_transactions"],
                "recovery_required": diagnostics["recovery_required"],
            },
            "privacy": {
                "bearer_token_exposed": diagnostics["bearer_token_exposed"],
                "outbound_product_network": diagnostics["outbound_product_network"],
                "cloud_connected": diagnostics["cloud_connected"],
                "copy_redacted": True,
            },
            "platform": {
                "name": diagnostics["platform"],
                "architecture": diagnostics["architecture"],
                "signing": diagnostics["signing_state"],
            },
            "last_self_test": diagnostics["self_test_last_result"],
            "limitations": limitations,
        }

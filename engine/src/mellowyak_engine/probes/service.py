from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorLink,
    BehaviorVersion,
    ProbeDefinition,
    ProbeRun,
    ProbeVersion,
    Project,
    ProjectChange,
    ProtectedBehavior,
    ProtectionPlan,
    ProtectionPlanItem,
    RegressionFinding,
    RuntimeProfile,
    RuntimeProfileVersion,
    SignalClassification,
    SnapshotMilestone,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.probes.adapters import ProbeRequest, default_probe_registry
from mellowyak_engine.snapshots.service import SnapshotService

PROBE_TYPES = frozenset({"BROWSER", "HTTP", "CLI", "PROCESS", "TEST", "MANUAL"})
_SECRET_KEY = re.compile(r"token|secret|password|passwd|cookie|authorization|api[_-]?key", re.I)
_SECRET_VALUE = re.compile(
    r"(?i)(token|secret|password|passwd|authorization|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)"
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _SECRET_KEY.search(str(key)) else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value[:200]]
    if isinstance(value, str):
        return _SECRET_VALUE.sub(r"\1\2[REDACTED]", value[:32_768])
    return value


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _SECRET_KEY.search(str(key)) or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


class ProbeServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProbeService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        events: LocalEventBus,
        snapshots: SnapshotService,
        productization: Any | None = None,
    ) -> None:
        self.sessions = sessions
        self.events = events
        self.snapshots = snapshots
        self.productization = productization
        self.adapters = default_probe_registry()
        self._cancellations: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _project(session: Session, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise ProbeServiceError("PROJECT_NOT_FOUND")
        return project

    def create(
        self,
        project_id: str,
        display_name: str,
        probe_type: str,
        behavior_id: str | None,
        runtime_profile_version_id: str | None,
        definition: dict[str, Any],
        timeout_seconds: int,
        retry_policy: dict[str, Any],
        expected_result: dict[str, Any],
        evidence_policy: dict[str, Any],
        source_links: list[dict[str, Any]],
        runtime_links: list[dict[str, Any]],
        approved: bool,
    ) -> dict[str, Any]:
        normalized_type = probe_type.upper()
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ProbeServiceError("PROBE_DISPLAY_NAME_REQUIRED")
        if normalized_type not in PROBE_TYPES:
            raise ProbeServiceError("PROBE_TYPE_UNSUPPORTED")
        if _contains_forbidden_key(definition) or _contains_forbidden_key(expected_result):
            raise ProbeServiceError("PROBE_SECRET_FIELD_DENIED")
        if normalized_type in {"CLI", "PROCESS", "TEST"} and not approved:
            raise ProbeServiceError("PROBE_EXPLICIT_APPROVAL_REQUIRED")
        if normalized_type in {"CLI", "PROCESS", "TEST"}:
            executable = definition.get("executable")
            argv = definition.get("argv", [])
            if (
                not isinstance(executable, str)
                or not executable.strip()
                or "\x00" in executable
                or not isinstance(argv, list)
                or any(not isinstance(item, str) or "\x00" in item for item in argv)
            ):
                raise ProbeServiceError("PROBE_ARGV_INVALID")
            if "command" in definition:
                raise ProbeServiceError("PROBE_SHELL_COMMAND_DENIED")
        now = datetime.now(UTC)
        probe_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            self._project(session, project_id)
            if runtime_profile_version_id:
                runtime_version = session.get(RuntimeProfileVersion, runtime_profile_version_id)
                if runtime_version is None or runtime_version.project_id != project_id:
                    raise ProbeServiceError("RUNTIME_PROFILE_VERSION_NOT_FOUND")
            if behavior_id:
                behavior = session.get(ProtectedBehavior, behavior_id)
                if behavior is None or behavior.project_id != project_id:
                    raise ProbeServiceError("BEHAVIOR_NOT_FOUND")
            row = ProbeDefinition(
                id=probe_id,
                project_id=project_id,
                behavior_id=behavior_id,
                display_name=normalized_name[:240],
                probe_type=normalized_type,
                current_version_id=version_id,
                status="CONFIGURED",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.add(
                ProbeVersion(
                    id=version_id,
                    probe_id=probe_id,
                    project_id=project_id,
                    version_number=1,
                    runtime_profile_version_id=runtime_profile_version_id,
                    definition_json=_json(_sanitize(definition)),
                    timeout_seconds=max(1, min(timeout_seconds, 300)),
                    retry_policy_json=_json(_sanitize(retry_policy)),
                    expected_result_json=_json(_sanitize(expected_result)),
                    evidence_policy_json=_json(_sanitize(evidence_policy)),
                    source_links_json=_json(_sanitize(source_links)),
                    runtime_links_json=_json(_sanitize(runtime_links)),
                    approved_at=now if approved else None,
                    created_at=now,
                )
            )
        return self.get(project_id, probe_id)

    @staticmethod
    def _version(row: ProbeVersion) -> dict[str, Any]:
        return {
            "id": row.id,
            "version_number": row.version_number,
            "runtime_profile_version_id": row.runtime_profile_version_id,
            "definition": _load(row.definition_json, {}),
            "timeout_seconds": row.timeout_seconds,
            "retry_policy": _load(row.retry_policy_json, {}),
            "expected_result": _load(row.expected_result_json, {}),
            "evidence_policy": _load(row.evidence_policy_json, {}),
            "source_links": _load(row.source_links_json, []),
            "runtime_links": _load(row.runtime_links_json, []),
            "approved_at": row.approved_at.isoformat() if row.approved_at else None,
            "created_at": row.created_at.isoformat(),
        }

    def _serialize(self, session: Session, row: ProbeDefinition) -> dict[str, Any]:
        versions = session.scalars(
            select(ProbeVersion)
            .where(ProbeVersion.probe_id == row.id)
            .order_by(ProbeVersion.version_number.desc())
        ).all()
        current = next(item for item in versions if item.id == row.current_version_id)
        last_run = session.scalars(
            select(ProbeRun)
            .where(ProbeRun.probe_id == row.id)
            .order_by(ProbeRun.started_at.desc())
            .limit(1)
        ).first()
        return {
            "id": row.id,
            "project_id": row.project_id,
            "behavior_id": row.behavior_id,
            "display_name": row.display_name,
            "probe_type": row.probe_type,
            "current_version_id": row.current_version_id,
            "status": row.status,
            "current_version": self._version(current),
            "versions": [self._version(item) for item in versions],
            "last_run": self._run(last_run) if last_run else None,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }

    def list(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(ProbeDefinition)
                .where(ProbeDefinition.project_id == project_id)
                .order_by(ProbeDefinition.updated_at.desc())
            ).all()
            return [self._serialize(session, row) for row in rows]

    def get(self, project_id: str, probe_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            row = session.get(ProbeDefinition, probe_id)
            if row is None or row.project_id != project_id:
                raise ProbeServiceError("PROBE_NOT_FOUND")
            return self._serialize(session, row)

    def select_impacted(self, project_id: str, episode_id: str, limit: int = 50) -> dict[str, Any]:
        """Select bounded probes through existing behavior links and Protection Plans."""
        bounded_limit = max(1, min(limit, 100))
        with self.sessions() as session:
            self._project(session, project_id)
            episode = session.get(SourceEpisode, episode_id)
            if episode is None or episode.project_id != project_id:
                raise ProbeServiceError("EPISODE_NOT_FOUND")
            changed_paths = set(
                _load(episode.added_paths_json, [])
                + _load(episode.modified_paths_json, [])
                + _load(episode.deleted_paths_json, [])
            )
            snapshot = (
                session.get(SourceSnapshot, episode.resulting_snapshot_id)
                if episode.resulting_snapshot_id
                else None
            )
            change = (
                session.scalars(
                    select(ProjectChange)
                    .where(
                        ProjectChange.project_id == project_id,
                        ProjectChange.worktree_fingerprint == snapshot.manifest_digest,
                    )
                    .order_by(ProjectChange.created_at.desc())
                    .limit(1)
                ).first()
                if snapshot
                else None
            )
            plan = (
                session.scalars(
                    select(ProtectionPlan)
                    .where(
                        ProtectionPlan.project_id == project_id,
                        ProtectionPlan.change_id == change.id,
                        ProtectionPlan.status != "STALE",
                    )
                    .order_by(ProtectionPlan.created_at.desc())
                    .limit(1)
                ).first()
                if change
                else None
            )
            plan_items = (
                session.scalars(
                    select(ProtectionPlanItem).where(ProtectionPlanItem.plan_id == plan.id)
                ).all()
                if plan
                else []
            )
            plan_by_behavior = {item.behavior_id: item for item in plan_items}
            probes = session.scalars(
                select(ProbeDefinition).where(
                    ProbeDefinition.project_id == project_id,
                    ProbeDefinition.status == "CONFIGURED",
                )
            ).all()
            behavior_ids = {probe.behavior_id for probe in probes if probe.behavior_id}
            behaviors = {
                row.id: row
                for row in session.scalars(
                    select(ProtectedBehavior).where(ProtectedBehavior.id.in_(behavior_ids))
                ).all()
            }
            links_by_behavior: dict[str, list[BehaviorLink]] = {}
            if behavior_ids:
                for link in session.scalars(
                    select(BehaviorLink).where(
                        BehaviorLink.project_id == project_id,
                        BehaviorLink.behavior_id.in_(behavior_ids),
                    )
                ).all():
                    links_by_behavior.setdefault(link.behavior_id, []).append(link)
            ranked: list[tuple[int, str, ProbeDefinition, ProbeVersion]] = []
            for probe in probes:
                version = session.get(ProbeVersion, probe.current_version_id)
                if version is None:
                    continue
                score = 0
                reason = ""
                plan_item = plan_by_behavior.get(probe.behavior_id or "")
                if plan_item and plan_item.selection_class == "REQUIRED":
                    score, reason = 100, "PROTECTION_PLAN_REQUIRED"
                elif plan_item and plan_item.selection_class == "SUGGESTED":
                    score, reason = 75, "PROTECTION_PLAN_SUGGESTED"
                behavior_links = links_by_behavior.get(probe.behavior_id or "", [])
                for link in behavior_links:
                    if link.link_key in changed_paths or any(
                        path.endswith(link.link_key) for path in changed_paths
                    ):
                        candidate = 95 if link.provenance == "HUMAN_CONFIRMED" else 80
                        if candidate > score:
                            score = candidate
                            reason = f"BEHAVIOR_LINK_{link.provenance}"
                for source_link in _load(version.source_links_json, []):
                    if not isinstance(source_link, dict):
                        continue
                    path = source_link.get("path") or source_link.get("link_key")
                    if isinstance(path, str) and (
                        path in changed_paths or any(item.endswith(path) for item in changed_paths)
                    ):
                        provenance = str(source_link.get("provenance", "PARSED_STATIC"))
                        candidate = 90 if provenance == "HUMAN_CONFIRMED" else 70
                        if candidate > score:
                            score, reason = candidate, f"PROBE_SOURCE_LINK_{provenance}"
                behavior = behaviors.get(probe.behavior_id or "")
                if behavior and behavior.always_recheck and score < 85:
                    score, reason = 85, "CRITICAL_ALWAYS_RECHECK"
                if score:
                    ranked.append((score, reason, probe, version))
            ranked.sort(key=lambda item: (-item[0], item[2].id))
            selected = [
                {
                    "probe_id": probe.id,
                    "probe_version_id": version.id,
                    "behavior_id": probe.behavior_id,
                    "probe_type": probe.probe_type,
                    "reason": reason,
                    "automatic_eligible": version.approved_at is not None,
                }
                for _score, reason, probe, version in ranked[:bounded_limit]
            ]
            return {
                "project_id": project_id,
                "episode_id": episode_id,
                "change_id": change.id if change else None,
                "protection_plan_id": plan.id if plan else None,
                "changed_paths": sorted(changed_paths)[:500],
                "selected": selected,
                "selected_count": len(selected),
                "candidate_count": len(ranked),
                "truncated": len(ranked) > bounded_limit or bool(plan and plan.truncated),
                "unknown_count": plan.unknown_count if plan else 0,
            }

    @staticmethod
    def _run(row: ProbeRun) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "probe_id": row.probe_id,
            "probe_version_id": row.probe_version_id,
            "snapshot_id": row.snapshot_id,
            "episode_id": row.episode_id,
            "runtime_profile_version_id": row.runtime_profile_version_id,
            "source_identity": _load(row.source_identity_json, {}),
            "status": row.status,
            "result": row.result,
            "attempt_count": row.attempt_count,
            "expected": _load(row.expected_json, {}),
            "observed": _load(row.observed_json, {}),
            "evidence": _load(row.evidence_json, {}),
            "limitations": _load(row.limitations_json, []),
            "reproducible": row.reproducible,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "cancelled_at": row.cancelled_at.isoformat() if row.cancelled_at else None,
        }

    def run(self, project_id: str, probe_id: str, snapshot_id: str | None = None) -> dict[str, Any]:
        with self.sessions() as session:
            project = self._project(session, project_id)
            probe = session.get(ProbeDefinition, probe_id)
            if probe is None or probe.project_id != project_id:
                raise ProbeServiceError("PROBE_NOT_FOUND")
            version = session.get(ProbeVersion, probe.current_version_id)
            if version is None:
                raise ProbeServiceError("PROBE_VERSION_NOT_FOUND")
            if snapshot_id:
                snapshot = session.get(SourceSnapshot, snapshot_id)
                if snapshot is None or snapshot.project_id != project_id:
                    raise ProbeServiceError("SNAPSHOT_NOT_FOUND")
            else:
                snapshot = session.scalars(
                    select(SourceSnapshot)
                    .where(SourceSnapshot.project_id == project_id)
                    .order_by(SourceSnapshot.created_at.desc())
                    .limit(1)
                ).first()
            project_root = Path(project.canonical_root_path or project.root_path)
        if snapshot is None:
            self.snapshots.create(project_id, creation_reason="PROBE")
            with self.sessions() as session:
                snapshot = session.scalars(
                    select(SourceSnapshot)
                    .where(SourceSnapshot.project_id == project_id)
                    .order_by(SourceSnapshot.created_at.desc())
                    .limit(1)
                ).one()
        with self.sessions() as session:
            milestone = session.scalars(
                select(SnapshotMilestone)
                .where(
                    SnapshotMilestone.project_id == project_id,
                    SnapshotMilestone.probe_version_id == version.id,
                    SnapshotMilestone.status == "ACCEPTED",
                )
                .order_by(SnapshotMilestone.created_at.desc())
                .limit(1)
            ).first()
            baseline_pass = (
                session.scalars(
                    select(ProbeRun)
                    .where(
                        ProbeRun.project_id == project_id,
                        ProbeRun.probe_version_id == version.id,
                        ProbeRun.snapshot_id == milestone.snapshot_id,
                        ProbeRun.result == "PASS",
                    )
                    .order_by(ProbeRun.completed_at.desc())
                    .limit(1)
                ).first()
                if milestone
                else None
            )
        adapter = self.adapters.get(probe.probe_type)
        if adapter is None:
            raise ProbeServiceError("PROBE_ADAPTER_UNAVAILABLE")
        definition = _load(version.definition_json, {})
        expected = _load(version.expected_result_json, {})
        evidence_policy = _load(version.evidence_policy_json, {})
        retry_policy = _load(version.retry_policy_json, {})
        configured_attempts = int(retry_policy.get("max_attempts", 0) or 0)
        has_comparable_baseline = milestone is not None and baseline_pass is not None
        max_attempts = max(
            1,
            min(configured_attempts or (2 if has_comparable_baseline else 1), 3),
        )
        run_id = str(uuid.uuid4())
        cancelled = threading.Event()
        with self._lock:
            self._cancellations[run_id] = cancelled
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.add(
                ProbeRun(
                    id=run_id,
                    project_id=project_id,
                    probe_id=probe_id,
                    probe_version_id=version.id,
                    snapshot_id=snapshot.id,
                    episode_id=snapshot.episode_id,
                    runtime_profile_version_id=version.runtime_profile_version_id,
                    source_identity_json=snapshot.source_identity_json,
                    status="RUNNING",
                    result="NOT_RUN",
                    expected_json=version.expected_result_json,
                    started_at=now,
                )
            )
        self.events.publish("probe_queued", project_id, {"probe_id": probe_id, "run_id": run_id})
        self.events.publish("probe_started", project_id, {"probe_id": probe_id, "run_id": run_id})
        attempts: list[dict[str, Any]] = []
        execution = None
        try:
            for attempt in range(1, max_attempts + 1):
                execution = adapter.run(
                    ProbeRequest(
                        project_root=project_root,
                        probe_type=probe.probe_type,
                        definition=definition,
                        expected=expected,
                        evidence_policy=evidence_policy,
                        source_identity=_load(snapshot.source_identity_json, {}),
                        timeout_seconds=version.timeout_seconds,
                    ),
                    cancelled,
                )
                attempts.append(
                    {
                        "attempt": attempt,
                        "result": execution.result,
                        "observed": _sanitize(execution.observed),
                    }
                )
                if execution.result in {"PASS", "CANCELLED", "INCONCLUSIVE"}:
                    break
                if attempt < max_attempts:
                    self.events.publish(
                        "probe_retrying",
                        project_id,
                        {"probe_id": probe_id, "run_id": run_id, "attempt": attempt + 1},
                    )
        except (OSError, ValueError, RuntimeError) as error:
            from mellowyak_engine.probes.adapters import ProbeExecution

            execution = ProbeExecution(
                "INCONCLUSIVE",
                expected,
                {"error_code": str(error)[:120]},
                {},
                ("PROBE_ADAPTER_FAILED_OPEN",),
                retryable=False,
            )
            attempts.append(
                {"attempt": 1, "result": execution.result, "observed": execution.observed}
            )
        finally:
            with self._lock:
                self._cancellations.pop(run_id, None)
        assert execution is not None
        failure_count = sum(item["result"] == "FAIL" for item in attempts)
        reproducible = bool(has_comparable_baseline and failure_count >= 2)
        if execution.result == "FAIL":
            related_process_crash = (
                probe.probe_type == "PROCESS" and snapshot.episode_id is not None
            )
            signal_state = (
                "CONFIRMED"
                if reproducible
                else "HIGH"
                if has_comparable_baseline or related_process_crash
                else "SUSPECTED"
            )
            reason_codes = (
                ["PRIOR_PASS_REPRODUCIBLE_CURRENT_FAIL"]
                if reproducible
                else ["PRIOR_PASS_CURRENT_FAIL"]
                if has_comparable_baseline
                else ["CURRENT_EPISODE_PROCESS_STARTUP_FAILURE"]
                if related_process_crash
                else ["NON_COMPARABLE_PROBE_FAILURE"]
            )
        elif execution.result == "PASS":
            signal_state = "WATCH"
            reason_codes = ["CURRENT_PROBE_PASS"]
        else:
            signal_state = "SUSPECTED"
            reason_codes = ["PROBE_INCONCLUSIVE"]
        completed = datetime.now(UTC)
        signal_id = str(uuid.uuid4())
        regression_id: str | None = None
        with self.sessions.begin() as session:
            run = session.get(ProbeRun, run_id)
            if run is None:
                raise ProbeServiceError("PROBE_RUN_NOT_FOUND")
            run.status = "CANCELLED" if execution.result == "CANCELLED" else "COMPLETED"
            run.result = execution.result
            run.attempt_count = len(attempts)
            run.observed_json = _json(_sanitize(execution.observed) | {"attempts": attempts})
            run.evidence_json = _json(_sanitize(execution.evidence))
            run.limitations_json = _json(list(execution.limitations))
            run.reproducible = reproducible
            run.completed_at = completed
            if execution.result == "CANCELLED":
                run.cancelled_at = completed
            signal = SignalClassification(
                id=signal_id,
                project_id=project_id,
                episode_id=snapshot.episode_id,
                snapshot_id=snapshot.id,
                probe_run_id=run_id,
                state=signal_state,
                reason_codes_json=_json(reason_codes),
                evidence_json=_json(
                    {
                        "previous_milestone_id": milestone.id if milestone else None,
                        "previous_passing_probe_run_id": (
                            baseline_pass.id if baseline_pass else None
                        ),
                        "attempt_count": len(attempts),
                        "reproducible": reproducible,
                    }
                ),
                friendly_key=f"signal.{signal_state.lower()}.probe",
                technical_json=_json({"probe_id": probe_id, "attempts": attempts}),
                created_at=completed,
            )
            session.add(signal)
            session.flush()
            if reproducible and probe.behavior_id and milestone and milestone.behavior_version_id:
                change = session.scalars(
                    select(ProjectChange)
                    .where(
                        ProjectChange.project_id == project_id,
                        ProjectChange.worktree_fingerprint == snapshot.manifest_digest,
                    )
                    .order_by(ProjectChange.created_at.desc())
                    .limit(1)
                ).first()
                if change:
                    regression_id = str(uuid.uuid4())
                    session.add(
                        RegressionFinding(
                            id=regression_id,
                            project_id=project_id,
                            change_id=change.id,
                            behavior_id=probe.behavior_id,
                            behavior_version_id=milestone.behavior_version_id,
                            baseline_id=milestone.id,
                            verification_run_item_id=None,
                            probe_run_id=run_id,
                            signal_classification_id=signal_id,
                            status="CONFIRMED",
                            decision_reason=(
                                "A previously accepted probe passed at Last Known Good and "
                                "failed reproducibly for the current exact source identity."
                            ),
                            source_identity_json=snapshot.source_identity_json,
                            created_at=completed,
                        )
                    )
                    signal.regression_id = regression_id
        self.events.publish(
            "probe_passed" if execution.result == "PASS" else "probe_failed",
            project_id,
            {"probe_id": probe_id, "run_id": run_id},
        )
        self.events.publish(
            "signal_classified",
            project_id,
            {"signal_id": signal_id, "state": signal_state},
        )
        if regression_id:
            self.events.publish(
                "confirmed_regression",
                project_id,
                {"regression_id": regression_id, "probe_run_id": run_id},
            )
            if self.productization is not None:
                try:
                    incident_material = "\x00".join(
                        [
                            project_id,
                            probe.behavior_id or "-",
                            milestone.id if milestone else "-",
                            snapshot.manifest_digest,
                            "CONFIRMED_PROBE_REGRESSION",
                        ]
                    )
                    incident_key = hashlib.sha256(incident_material.encode()).hexdigest()
                    self.productization.create_alert(
                        project_id=project_id,
                        change_id=None,
                        regression_id=regression_id,
                        category="REGRESSION",
                        severity="CRITICAL",
                        title_key="alerts.confirmedProbeRegressionTitle",
                        summary_key="alerts.confirmedProbeRegressionSummary",
                        parameters={},
                        deduplication_key=f"probe-regression:{incident_key}",
                        route={
                            "screen": "change",
                            "project_id": project_id,
                            "regression_id": regression_id,
                        },
                    )
                except Exception:
                    pass
        response = self.get_run(project_id, run_id)
        response["signal"] = {
            "id": signal_id,
            "state": signal_state,
            "reason_codes": reason_codes,
            "regression_id": regression_id,
        }
        return response

    def get_run(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(ProbeRun, run_id)
            if row is None or row.project_id != project_id:
                raise ProbeServiceError("PROBE_RUN_NOT_FOUND")
            return self._run(row)

    def cancel(self, project_id: str, probe_id: str) -> dict[str, str]:
        with self._lock:
            run_ids = list(self._cancellations)
            for run_id in run_ids:
                with self.sessions() as session:
                    row = session.get(ProbeRun, run_id)
                    if row and row.project_id == project_id and row.probe_id == probe_id:
                        self._cancellations[run_id].set()
                        return {"status": "CANCELLING"}
        return {"status": "NOT_RUNNING"}

    def create_milestone(
        self,
        project_id: str,
        snapshot_id: str,
        display_name: str,
        behavior_id: str | None,
        behavior_version_id: str | None,
        probe_version_id: str | None,
        human_attested: bool,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            self._project(session, project_id)
            snapshot = session.get(SourceSnapshot, snapshot_id)
            if snapshot is None or snapshot.project_id != project_id:
                raise ProbeServiceError("SNAPSHOT_NOT_FOUND")
            if behavior_id:
                behavior = session.get(ProtectedBehavior, behavior_id)
                if behavior is None or behavior.project_id != project_id:
                    raise ProbeServiceError("BEHAVIOR_NOT_FOUND")
                behavior_version_id = behavior_version_id or behavior.current_version_id
            if behavior_version_id:
                behavior_version = session.get(BehaviorVersion, behavior_version_id)
                if (
                    behavior_version is None
                    or behavior_version.project_id != project_id
                    or (behavior_id and behavior_version.behavior_id != behavior_id)
                ):
                    raise ProbeServiceError("BEHAVIOR_VERSION_NOT_FOUND")
                behavior_id = behavior_id or behavior_version.behavior_id
            passing_run = None
            if probe_version_id:
                probe_version = session.get(ProbeVersion, probe_version_id)
                if probe_version is None or probe_version.project_id != project_id:
                    raise ProbeServiceError("PROBE_VERSION_NOT_FOUND")
                probe_definition = session.get(ProbeDefinition, probe_version.probe_id)
                if (
                    probe_definition is None
                    or probe_definition.project_id != project_id
                    or (
                        behavior_id is not None
                        and probe_definition.behavior_id is not None
                        and probe_definition.behavior_id != behavior_id
                    )
                ):
                    raise ProbeServiceError("PROBE_VERSION_NOT_FOUND")
                passing_run = session.scalars(
                    select(ProbeRun)
                    .where(
                        ProbeRun.project_id == project_id,
                        ProbeRun.probe_version_id == probe_version_id,
                        ProbeRun.snapshot_id == snapshot_id,
                        ProbeRun.result == "PASS",
                    )
                    .order_by(ProbeRun.completed_at.desc())
                    .limit(1)
                ).first()
            if passing_run is None and not human_attested:
                raise ProbeServiceError("MILESTONE_PASS_OR_ATTESTATION_REQUIRED")
            runtime_versions = session.scalars(
                select(RuntimeProfile.current_version_id).where(
                    RuntimeProfile.project_id == project_id
                )
            ).all()
            row = SnapshotMilestone(
                id=str(uuid.uuid4()),
                project_id=project_id,
                snapshot_id=snapshot_id,
                display_name=display_name.strip()[:240],
                behavior_id=behavior_id,
                behavior_version_id=behavior_version_id,
                probe_version_id=probe_version_id,
                runtime_profile_versions_json=_json(sorted(runtime_versions)),
                environment_summary_json=_json({"local_only": True}),
                limitations_json=_json(
                    ["MANUAL_NOT_AUTOMATED"] if human_attested and not passing_run else []
                ),
                status="ACCEPTED",
                human_attested=human_attested,
                pinned=True,
                created_at=now,
            )
            session.add(row)
            snapshot.pinned = True
            milestone_id = row.id
        self.events.publish(
            "milestone_accepted",
            project_id,
            {"milestone_id": milestone_id, "snapshot_id": snapshot_id},
        )
        return self.get_milestone(project_id, milestone_id)

    @staticmethod
    def _milestone(row: SnapshotMilestone) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "snapshot_id": row.snapshot_id,
            "display_name": row.display_name,
            "behavior_id": row.behavior_id,
            "behavior_version_id": row.behavior_version_id,
            "probe_version_id": row.probe_version_id,
            "runtime_profile_versions": _load(row.runtime_profile_versions_json, []),
            "environment_summary": _load(row.environment_summary_json, {}),
            "limitations": _load(row.limitations_json, []),
            "status": row.status,
            "human_attested": row.human_attested,
            "pinned": row.pinned,
            "created_at": row.created_at.isoformat(),
        }

    def milestones(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(SnapshotMilestone)
                .where(SnapshotMilestone.project_id == project_id)
                .order_by(SnapshotMilestone.created_at.desc())
            ).all()
            return [self._milestone(row) for row in rows]

    def get_milestone(self, project_id: str, milestone_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(SnapshotMilestone, milestone_id)
            if row is None or row.project_id != project_id:
                raise ProbeServiceError("MILESTONE_NOT_FOUND")
            return self._milestone(row)

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    OrchestrationJob,
    OrchestrationRun,
    ProbeDefinition,
    ProbeVersion,
    Project,
    SourceEpisode,
    SourceSnapshot,
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(value: str) -> Any:
    return json.loads(value)


class OrchestrationService:
    """Authoritative post-settle Passive Sentinel pipeline."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        events: LocalEventBus,
        probes: Any,
        policies: Any,
        scheduler: Any,
        impact_memory: Any,
    ) -> None:
        self.sessions = sessions
        self.events = events
        self.probes = probes
        self.policies = policies
        self.scheduler = scheduler
        self.impact_memory = impact_memory

    @staticmethod
    def _public(row: OrchestrationRun) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "episode_id": row.episode_id,
            "base_snapshot_id": row.base_snapshot_id,
            "resulting_snapshot_id": row.resulting_snapshot_id,
            "source_identity": _load(row.source_identity_json),
            "runtime_profile_versions": _load(row.runtime_profile_versions_json),
            "selected_behaviors": _load(row.selected_behaviors_json),
            "omitted_behaviors": _load(row.omitted_behaviors_json),
            "selected_probe_versions": _load(row.selected_probe_versions_json),
            "policy_versions": _load(row.policy_versions_json),
            "scheduler_budget": _load(row.scheduler_budget_json),
            "eligibility": _load(row.eligibility_json),
            "evidence_references": _load(row.evidence_references_json),
            "state": row.state,
            "terminal_status": row.terminal_status,
            "error_code": row.error_code,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }

    def handle_episode(self, project_id: str, episode_id: str) -> dict[str, Any]:
        """Called by EpisodeService after the immutable resulting snapshot exists."""
        project_policy = self.policies.project_policy(project_id)
        selection = self.probes.select_impacted(
            project_id, episode_id, limit=int(project_policy["max_checks_per_episode"])
        )
        with self.sessions() as session:
            episode = session.get(SourceEpisode, episode_id)
            project = session.get(Project, project_id)
            snapshot = (
                session.get(SourceSnapshot, episode.resulting_snapshot_id)
                if episode and episode.resulting_snapshot_id
                else None
            )
            if episode is None or project is None or snapshot is None:
                raise RuntimeError("ORCHESTRATION_SOURCE_NOT_READY")
            configured = session.scalars(
                select(ProbeDefinition).where(
                    ProbeDefinition.project_id == project_id, ProbeDefinition.status == "CONFIGURED"
                )
            ).all()
            configured_by_id = {item.id: item for item in configured}
            selected_rows: list[tuple[dict[str, Any], ProbeDefinition, ProbeVersion]] = []
            for item in selection["selected"]:
                probe = configured_by_id.get(str(item["probe_id"]))
                version = session.get(ProbeVersion, str(item["probe_version_id"]))
                if probe is not None and version is not None:
                    selected_rows.append((item, probe, version))
        selected_ids = {str(item[0]["probe_id"]) for item in selected_rows}
        omitted = [
            {
                "probe_id": probe.id,
                "behavior_id": probe.behavior_id,
                "reason": "NOT_SELECTED_BY_CURRENT_IMPACT",
            }
            for probe in configured
            if probe.id not in selected_ids
        ]
        eligibility: list[dict[str, Any]] = []
        for _item, probe, version in selected_rows:
            decision = self.policies.eligibility(
                project_id, probe.behavior_id, version, probe.probe_type
            )
            eligibility.append({"probe_id": probe.id, "behavior_id": probe.behavior_id, **decision})
        now = datetime.now(UTC)
        run_id = str(uuid.uuid4())
        selected_behaviors = [
            {"behavior_id": probe.behavior_id, "probe_id": probe.id, "reason": item["reason"]}
            for item, probe, _version in selected_rows
        ]
        state = "QUEUED" if any(item["eligible"] for item in eligibility) else "WAITING_FOR_POLICY"
        if any(item["deferred"] for item in eligibility):
            state = "PAUSED"
        policy_versions = {
            "global": self.policies.global_policy()["version"],
            "project": project_policy["version"],
            "behaviors": {
                item["behavior_id"]: item["policy_versions"]["behavior"]
                for item in eligibility
                if item["behavior_id"]
            },
        }
        row = OrchestrationRun(
            id=run_id,
            project_id=project_id,
            episode_id=episode_id,
            base_snapshot_id=episode.base_snapshot_id,
            resulting_snapshot_id=snapshot.id,
            source_identity_json=snapshot.source_identity_json,
            runtime_profile_versions_json=snapshot.runtime_profile_fingerprints_json,
            selected_behaviors_json=_json(selected_behaviors),
            omitted_behaviors_json=_json(omitted),
            selected_probe_versions_json=_json(
                [version.id for _item, _probe, version in selected_rows]
            ),
            policy_versions_json=_json(policy_versions),
            scheduler_budget_json=_json(
                {
                    "max_checks": project_policy["max_checks_per_episode"],
                    "selected": len(selected_rows),
                    "candidate_count": selection["candidate_count"],
                }
            ),
            eligibility_json=_json(eligibility),
            evidence_references_json=_json([snapshot.id]),
            state=state,
            terminal_status="NO_ELIGIBLE_CHECKS" if not selected_rows else None,
            created_at=now,
            updated_at=now,
            completed_at=now if not selected_rows else None,
        )
        with self.sessions.begin() as session:
            session.add(row)
        self.events.publish(
            "impact_plan_created",
            project_id,
            {"orchestration_run_id": run_id, "episode_id": episode_id},
        )
        self.events.publish(
            "checks_selected",
            project_id,
            {"orchestration_run_id": run_id, "selected_count": len(selected_rows)},
        )
        self.events.publish(
            "checks_omitted",
            project_id,
            {"orchestration_run_id": run_id, "omitted_count": len(omitted)},
        )
        self.impact_memory.observe_selection(
            project_id,
            snapshot.manifest_digest,
            list(selection["changed_paths"]),
            [item for item, _probe, _version in selected_rows],
            run_id,
        )
        queued_count = 0
        for (item, probe, version), decision in zip(selected_rows, eligibility, strict=True):
            if decision["eligible"] or decision["deferred"]:
                self.scheduler.enqueue(
                    orchestration_run_id=run_id,
                    project_id=project_id,
                    behavior_id=probe.behavior_id,
                    probe_id=probe.id,
                    probe_version_id=version.id,
                    runtime_profile_version_id=version.runtime_profile_version_id,
                    snapshot_id=snapshot.id,
                    source_identity_digest=snapshot.manifest_digest,
                    priority=90 if "CRITICAL" in str(item["reason"]) else 70,
                    reason_code=str(item["reason"]),
                    deferred=bool(decision["deferred"]),
                    defer_reason=decision["reason_codes"][0] if decision["deferred"] else None,
                )
                queued_count += 1
        return selection | {
            "orchestration_run_id": run_id,
            "queued_count": queued_count,
            "omitted": omitted,
            "eligibility": eligibility,
        }

    def list(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(OrchestrationRun)
                .where(OrchestrationRun.project_id == project_id)
                .order_by(OrchestrationRun.created_at.desc())
                .limit(max(1, min(limit, 500)))
            ).all()
            return [self._public(row) for row in rows]

    def get(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(OrchestrationRun, run_id)
            if row is None or row.project_id != project_id:
                raise RuntimeError("ORCHESTRATION_RUN_NOT_FOUND")
            value = self._public(row)
            jobs = session.scalars(
                select(OrchestrationJob).where(OrchestrationJob.orchestration_run_id == run_id)
            ).all()
            value["jobs"] = [self.scheduler._public(job) for job in jobs]
            value["known_facts"] = ["SOURCE_IDENTITY_BOUND", "RESULTS_CANNOT_CLASSIFY_NEWER_SOURCE"]
            value["unknowns"] = ["OMITTED_BEHAVIORS_WERE_NOT_VERIFIED"]
            value["limitations"] = ["AUTOMATIC_APPLY_IS_DISABLED"]
            return value

    def pause(self, project_id: str) -> dict[str, Any]:
        policy = self.policies.update_project(project_id, {"mode": "PAUSED"})
        self.events.publish(
            "orchestration_paused", project_id, {"policy_version": policy["version"]}
        )
        return policy

    def resume(self, project_id: str) -> dict[str, Any]:
        policy = self.policies.update_project(project_id, {"mode": "ASK_BEFORE_CHECKS"})
        self.events.publish(
            "orchestration_resumed", project_id, {"policy_version": policy["version"]}
        )
        return policy

    def run_now(self, project_id: str) -> dict[str, Any]:
        resumed = self.scheduler.resume_deferred(project_id)
        return {"status": "QUEUED_CURRENT_ELIGIBLE_WORK", "resumed_count": resumed}

    def impact_plan(self, project_id: str, episode_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.scalars(
                select(OrchestrationRun).where(
                    OrchestrationRun.project_id == project_id,
                    OrchestrationRun.episode_id == episode_id,
                )
            ).first()
            if row is None:
                raise RuntimeError("IMPACT_PLAN_NOT_FOUND")
            return self._public(row)

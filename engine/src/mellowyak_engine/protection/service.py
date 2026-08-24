from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorBaseline,
    BehaviorLink,
    BehaviorVersion,
    BrowserCaptureSession,
    EvidenceBundle,
    ImpactAnalysis,
    ImpactAnalysisPath,
    ImpactAnalysisResult,
    Project,
    ProjectChange,
    ProtectedBehavior,
    ProtectionPlan,
    ProtectionPlanItem,
)
from mellowyak_engine.protection.policy import (
    ALGORITHM_VERSION,
    HEURISTIC_PROVENANCE,
    MAX_PLAN_ITEMS,
    MAX_REQUIRED_CHECKS,
    MAX_SUGGESTED_CHECKS,
    PARSED_PROVENANCE,
    POLICY_VERSION,
    SKIPPED_REASON,
)


class ProtectionPlanError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _source_identity(
    project: Project, change: ProjectChange, analysis: ImpactAnalysis
) -> dict[str, Any]:
    return {
        "change_id": change.id,
        "head_sha": project.current_head_sha,
        "worktree_fingerprint": project.current_worktree_fingerprint,
        "scan_revision": analysis.scan_revision,
        "impact_analysis_id": analysis.id,
    }


class ProtectionPlanService:
    def __init__(self, sessions: sessionmaker, events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    def create(self, project_id: str, change_id: str) -> dict[str, Any]:
        self.events.publish("protection_plan_started", project_id, {"change_id": change_id})
        now = _now()
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            change = session.get(ProjectChange, change_id)
            if project is None or project.archived_at is not None:
                raise ProtectionPlanError("PROJECT_NOT_FOUND")
            if change is None or change.project_id != project_id:
                raise ProtectionPlanError("CHANGE_NOT_FOUND")
            analysis = session.scalars(
                select(ImpactAnalysis)
                .where(
                    ImpactAnalysis.project_id == project_id, ImpactAnalysis.change_id == change_id
                )
                .order_by(ImpactAnalysis.analysis_revision.desc())
            ).first()
            if analysis is None:
                raise ProtectionPlanError("FRESH_IMPACT_ANALYSIS_REQUIRED")
            if analysis.stale or analysis.status != "completed":
                raise ProtectionPlanError("FRESH_IMPACT_ANALYSIS_REQUIRED")
            if (
                analysis.head_sha != project.current_head_sha
                or analysis.worktree_fingerprint != project.current_worktree_fingerprint
            ):
                raise ProtectionPlanError("IMPACT_ANALYSIS_STALE")

            identity = _source_identity(project, change, analysis)
            behaviors = session.scalars(
                select(ProtectedBehavior)
                .where(
                    ProtectedBehavior.project_id == project_id,
                    ProtectedBehavior.lifecycle_state == "PROTECTED",
                )
                .order_by(ProtectedBehavior.stable_key)
            ).all()
            truncated = len(behaviors) > MAX_PLAN_ITEMS
            behaviors = behaviors[:MAX_PLAN_ITEMS]
            results = session.scalars(
                select(ImpactAnalysisResult).where(ImpactAnalysisResult.analysis_id == analysis.id)
            ).all()
            result_map: dict[str, list[ImpactAnalysisResult]] = {}
            for result in results:
                for key in {result.relative_path, result.display_name} - {None}:
                    result_map.setdefault(str(key), []).append(result)
            changed_paths = set(json.loads(change.changed_paths_json))
            binding_items: list[dict[str, Any]] = []
            selections: list[dict[str, Any]] = []
            for behavior in behaviors:
                version = session.get(BehaviorVersion, behavior.current_version_id)
                baseline = (
                    session.get(BehaviorBaseline, behavior.last_accepted_baseline_id)
                    if behavior.last_accepted_baseline_id
                    else None
                )
                if version is None:
                    continue
                links = session.scalars(
                    select(BehaviorLink).where(BehaviorLink.behavior_id == behavior.id)
                ).all()
                selected = self._select(
                    behavior, version, baseline, links, result_map, changed_paths, session
                )
                selections.append(selected)
                binding_items.append(
                    {
                        "behavior_id": behavior.id,
                        "version_id": version.id,
                        "baseline_id": baseline.id
                        if baseline and baseline.status == "ACCEPTED"
                        else None,
                    }
                )

            self._apply_limits(selections)
            binding = {
                "source": identity,
                "behaviors": binding_items,
                "algorithm": ALGORITHM_VERSION,
                "policy": POLICY_VERSION,
            }
            plan_id = str(uuid.uuid4())
            counts = {
                name: sum(item["selection_class"] == name for item in selections)
                for name in ("REQUIRED", "SUGGESTED", "SKIPPED", "NEEDS_REVIEW", "UNKNOWN")
            }
            plan = ProtectionPlan(
                id=plan_id,
                project_id=project_id,
                change_id=change_id,
                impact_analysis_id=analysis.id,
                source_identity_json=_json(identity),
                binding_digest=hashlib.sha256(_json(binding).encode()).hexdigest(),
                algorithm_version=ALGORITHM_VERSION,
                policy_version=POLICY_VERSION,
                status="READY",
                created_at=now,
                required_count=counts["REQUIRED"],
                suggested_count=counts["SUGGESTED"],
                skipped_count=counts["SKIPPED"],
                needs_review_count=counts["NEEDS_REVIEW"],
                unknown_count=counts["UNKNOWN"],
                truncated=truncated,
            )
            session.add(plan)
            for selected in selections:
                session.add(
                    ProtectionPlanItem(
                        id=str(uuid.uuid4()), plan_id=plan_id, project_id=project_id, **selected
                    )
                )
        self.events.publish(
            "protection_plan_ready", project_id, {"change_id": change_id, "plan_id": plan_id}
        )
        return self.get(project_id, change_id, plan_id)

    def _select(
        self,
        behavior: ProtectedBehavior,
        version: BehaviorVersion,
        baseline: BehaviorBaseline | None,
        links: list[BehaviorLink],
        result_map: dict[str, list[ImpactAnalysisResult]],
        changed_paths: set[str],
        session: Session,
    ) -> dict[str, Any]:
        selection = "SKIPPED"
        reason = SKIPPED_REASON
        provenance = "NONE"
        depth = 0
        stale = False
        unknown = False
        impact_path: list[dict[str, Any]] = []
        candidates: list[tuple[int, str, str, ImpactAnalysisResult | None]] = []
        if behavior.always_recheck:
            candidates.append((100, "REQUIRED", "Critical sentinel policy.", None))
        for link in links:
            if link.link_key in changed_paths and link.link_type in {"FILE", "SYMBOL"}:
                candidates.append((95, "REQUIRED", "Direct exact changed source link.", None))
            for result in result_map.get(link.link_key, []):
                if result.stale:
                    candidates.append(
                        (90, "NEEDS_REVIEW", "The linked source relation is stale.", result)
                    )
                elif result.unknown:
                    candidates.append(
                        (
                            85,
                            "UNKNOWN",
                            "An unknown impact boundary touches this behavior link.",
                            result,
                        )
                    )
                elif result.strongest_provenance in PARSED_PROVENANCE:
                    label = (
                        "Runtime-observed behavior connected through a current parsed relation."
                        if link.provenance == "RUNTIME_OBSERVED"
                        else "Current parsed impact relation selected this behavior."
                    )
                    candidates.append((80, "REQUIRED", label, result))
                elif result.strongest_provenance in HEURISTIC_PROVENANCE:
                    klass = "NEEDS_REVIEW" if version.criticality == "CRITICAL" else "SUGGESTED"
                    candidates.append(
                        (
                            70,
                            klass,
                            "A heuristic impact relation requires review."
                            if klass == "NEEDS_REVIEW"
                            else "A heuristic impact relation suggests this behavior.",
                            result,
                        )
                    )
        if candidates:
            _, selection, reason, result = sorted(candidates, key=lambda item: (-item[0], item[1]))[
                0
            ]
            if result is not None:
                provenance = result.strongest_provenance
                depth = result.minimum_depth
                stale = result.stale
                unknown = result.unknown
                path = session.scalars(
                    select(ImpactAnalysisPath)
                    .where(ImpactAnalysisPath.result_id == result.id)
                    .order_by(ImpactAnalysisPath.ordinal)
                ).first()
                impact_path = json.loads(path.path_json) if path else []
            elif behavior.always_recheck:
                provenance = "PROJECT_POLICY"
            else:
                provenance = "EXACT_LINK"
        baseline_capture = None
        if baseline and baseline.status == "ACCEPTED":
            bundle = session.get(EvidenceBundle, baseline.evidence_bundle_id)
            baseline_capture = (
                session.get(BrowserCaptureSession, bundle.capture_id) if bundle else None
            )
        automated = bool(
            baseline_capture
            and baseline_capture.runtime_configuration_id
            and json.loads(baseline_capture.expected_assertions_json)
        )
        return {
            "behavior_id": behavior.id,
            "behavior_version_id": version.id,
            "baseline_id": baseline.id if baseline and baseline.status == "ACCEPTED" else None,
            "selection_class": selection,
            "selection_reason": reason,
            "impact_path_json": _json(impact_path),
            "strongest_provenance": provenance,
            "relation_depth": depth,
            "stale_relation": stale,
            "unknown_boundary": unknown,
            "criticality": version.criticality,
            "verification_method": "BROWSER_REPLAY" if automated else "HUMAN_ATTESTATION",
        }

    @staticmethod
    def _apply_limits(items: list[dict[str, Any]]) -> None:
        required = suggested = 0
        for item in items:
            if item["selection_class"] == "REQUIRED":
                required += 1
                if required > MAX_REQUIRED_CHECKS:
                    item["selection_class"] = "NEEDS_REVIEW"
                    item["selection_reason"] = (
                        "Required-check safety limit requires explicit review."
                    )
            elif item["selection_class"] == "SUGGESTED":
                suggested += 1
                if suggested > MAX_SUGGESTED_CHECKS:
                    item["selection_class"] = "SKIPPED"
                    item["selection_reason"] = "Suggested-check safety limit omitted this item."

    def get(self, project_id: str, change_id: str, plan_id: str | None = None) -> dict[str, Any]:
        with self.sessions.begin() as session:
            query = select(ProtectionPlan).where(
                ProtectionPlan.project_id == project_id, ProtectionPlan.change_id == change_id
            )
            if plan_id:
                query = query.where(ProtectionPlan.id == plan_id)
            plan = session.scalars(query.order_by(ProtectionPlan.created_at.desc())).first()
            if plan is None:
                raise ProtectionPlanError("PROTECTION_PLAN_NOT_FOUND")
            self._refresh_staleness(session, plan)
            items = session.scalars(
                select(ProtectionPlanItem)
                .where(ProtectionPlanItem.plan_id == plan.id)
                .order_by(ProtectionPlanItem.selection_class, ProtectionPlanItem.behavior_id)
            ).all()
            return {
                "id": plan.id,
                "project_id": plan.project_id,
                "change_id": plan.change_id,
                "impact_analysis_id": plan.impact_analysis_id,
                "source_identity": json.loads(plan.source_identity_json),
                "binding_digest": plan.binding_digest,
                "algorithm_version": plan.algorithm_version,
                "policy_version": plan.policy_version,
                "status": plan.status,
                "created_at": plan.created_at,
                "stale_at": plan.stale_at,
                "counts": {
                    "required": plan.required_count,
                    "suggested": plan.suggested_count,
                    "skipped": plan.skipped_count,
                    "needs_review": plan.needs_review_count,
                    "unknown": plan.unknown_count,
                },
                "truncated": plan.truncated,
                "items": [self._item_public(session, item) for item in items],
            }

    def _refresh_staleness(self, session: Session, plan: ProtectionPlan) -> None:
        project = session.get(Project, plan.project_id)
        analysis = session.get(ImpactAnalysis, plan.impact_analysis_id)
        source = json.loads(plan.source_identity_json)
        stale = (
            project is None
            or analysis is None
            or analysis.stale
            or any(
                source.get(key) != value
                for key, value in {
                    "head_sha": project.current_head_sha if project else None,
                    "worktree_fingerprint": project.current_worktree_fingerprint
                    if project
                    else None,
                    "scan_revision": analysis.scan_revision if analysis else None,
                }.items()
            )
        )
        items = session.scalars(
            select(ProtectionPlanItem).where(ProtectionPlanItem.plan_id == plan.id)
        ).all()
        for item in items:
            behavior = session.get(ProtectedBehavior, item.behavior_id)
            if (
                behavior is None
                or behavior.current_version_id != item.behavior_version_id
                or behavior.last_accepted_baseline_id != item.baseline_id
            ):
                stale = True
        if stale and plan.status != "STALE":
            plan.status = "STALE"
            plan.stale_at = _now()

    @staticmethod
    def _item_public(session: Session, item: ProtectionPlanItem) -> dict[str, Any]:
        behavior = session.get(ProtectedBehavior, item.behavior_id)
        return {
            "id": item.id,
            "behavior_id": item.behavior_id,
            "behavior_name": behavior.display_name if behavior else item.behavior_id,
            "behavior_version_id": item.behavior_version_id,
            "baseline_id": item.baseline_id,
            "selection_class": item.selection_class,
            "selection_reason": item.selection_reason,
            "impact_path": json.loads(item.impact_path_json),
            "strongest_provenance": item.strongest_provenance,
            "relation_depth": item.relation_depth,
            "stale_relation": item.stale_relation,
            "unknown_boundary": item.unknown_boundary,
            "criticality": item.criticality,
            "verification_method": item.verification_method,
            "current_result_id": item.current_result_id,
        }

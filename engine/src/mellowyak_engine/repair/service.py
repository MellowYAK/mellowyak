from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    AssertionResult,
    BehaviorBaseline,
    BehaviorVersion,
    ContextReceipt,
    EvidenceBundleItem,
    ImpactAnalysisResult,
    Project,
    ProjectChange,
    ProtectionPlan,
    ProtectionPlanItem,
    RegressionFinding,
    RepairContext,
    RepairContextItem,
    VerificationRun,
    VerificationRunItem,
)

SCHEMA_VERSION = "mellowyak.repair_context.v1"
MAX_CONTEXT_BYTES = 256 * 1024
MISSING_INTENT = (
    "The requested new behavior was not described. Review the current diff before repair."
)
SECRET_PATTERN = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|authorization)\s*[:=]\s*[^\s,;]+"
)


class RepairContextError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _safe_text(value: str | None) -> str:
    return SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", value or "")


class RepairContextService:
    def __init__(
        self,
        sessions: sessionmaker,
        data_root: Path,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.root = (data_root / "repair-contexts").resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.events = events

    def create(self, project_id: str, regression_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            regression = session.get(RegressionFinding, regression_id)
            if regression is None or regression.project_id != project_id:
                raise RepairContextError("REGRESSION_NOT_FOUND")
            existing = session.scalars(
                select(RepairContext)
                .where(RepairContext.regression_id == regression_id)
                .order_by(RepairContext.created_at.desc())
            ).first()
            if existing is not None:
                return self._public(existing)
            project = session.get(Project, project_id)
            change = session.get(ProjectChange, regression.change_id)
            run_item = session.get(VerificationRunItem, regression.verification_run_item_id)
            run = session.get(VerificationRun, run_item.run_id) if run_item else None
            behavior_version = (
                session.get(BehaviorVersion, regression.behavior_version_id) if run_item else None
            )
            baseline = (
                session.get(BehaviorBaseline, regression.baseline_id)
                if regression.baseline_id
                else None
            )
            plan_item = session.get(ProtectionPlanItem, run_item.plan_item_id) if run_item else None
            plan = session.get(ProtectionPlan, run.plan_id) if run else None
            if not all(
                (project, change, run_item, run, behavior_version, baseline, plan_item, plan)
            ):
                raise RepairContextError("REGRESSION_CONTEXT_INCOMPLETE")
            assertions = session.scalars(
                select(AssertionResult)
                .where(
                    AssertionResult.verification_run_item_id == run_item.id,
                    AssertionResult.result == "FAIL",
                )
                .order_by(AssertionResult.ordinal)
            ).all()
            receipt = session.scalars(
                select(ContextReceipt)
                .where(
                    ContextReceipt.project_id == project_id,
                    ContextReceipt.change_id == change.id,
                )
                .order_by(ContextReceipt.created_at.desc())
            ).first()
            tests = session.scalars(
                select(ImpactAnalysisResult.relative_path)
                .where(
                    ImpactAnalysisResult.analysis_id == plan.impact_analysis_id,
                    ImpactAnalysisResult.node_type == "TEST",
                )
                .limit(50)
            ).all()
            baseline_refs = self._bundle_refs(session, baseline.evidence_bundle_id)
            current_refs = self._bundle_refs(session, run_item.evidence_bundle_id)
            changed_files = [
                str(path)
                for path in json.loads(change.changed_paths_json)
                if path and not Path(str(path)).is_absolute()
            ][:100]
            unknowns = []
            stale_boundaries = []
            if plan_item.unknown_boundary:
                unknowns.append(plan_item.selection_reason)
            if plan_item.stale_relation:
                stale_boundaries.append(plan_item.selection_reason)
            payload = {
                "schema": SCHEMA_VERSION,
                "project": {"id": project.id, "name": project.display_name},
                "change": {
                    "id": change.id,
                    "description": _safe_text(change.task_intent),
                },
                "current_source_identity": json.loads(run.source_identity_json),
                "change_intent": _safe_text(change.task_intent) or None,
                "failed_protected_behavior": {
                    "id": run_item.behavior_id,
                    "title": behavior_version.title,
                    "version_id": behavior_version.id,
                    "criticality": behavior_version.criticality,
                },
                "keep": _safe_text(change.task_intent) or MISSING_INTENT,
                "restore": _safe_text(behavior_version.expected_outcome),
                "last_known_good_identity": json.loads(baseline.source_revision_json),
                "baseline_evidence_references": baseline_refs,
                "current_failure_evidence_references": current_refs,
                "failed_assertions": [
                    {
                        "type": row.assertion_type,
                        "expected": json.loads(row.expected_json),
                        "observed": json.loads(row.observed_json),
                        "reason": row.failure_reason,
                    }
                    for row in assertions
                ],
                "impact_path": json.loads(plan_item.impact_path_json),
                "relevant_files": changed_files,
                "related_tests": [str(path) for path in tests if path],
                "context_receipt_reference": receipt.id if receipt else None,
                "unknowns": unknowns,
                "stale_boundaries": stale_boundaries,
                "required_final_rechecks": [
                    {
                        "behavior_id": run_item.behavior_id,
                        "behavior_version_id": run_item.behavior_version_id,
                    }
                ],
                "forbidden_assumptions": [
                    "Do not infer requirements absent from KEEP.",
                    "Do not treat unknown or stale relations as verified.",
                    "Do not replace fresh current evidence with Last Known Good evidence.",
                ],
                "content_budget": {
                    "maximum_bytes": MAX_CONTEXT_BYTES,
                    "source_contents_included": False,
                },
                "generated_at": regression.created_at.isoformat(),
            }
            payload["digest"] = hashlib.sha256(_canonical(payload)).hexdigest()
            encoded = _canonical(payload)
            if len(encoded) > MAX_CONTEXT_BYTES:
                raise RepairContextError("REPAIR_CONTEXT_LIMIT_EXCEEDED")
            context_id = str(uuid.uuid4())
            row = RepairContext(
                id=context_id,
                project_id=project_id,
                change_id=change.id,
                regression_id=regression_id,
                schema_version=SCHEMA_VERSION,
                source_identity_json=json.dumps(payload["current_source_identity"], sort_keys=True),
                payload_json=encoded.decode(),
                digest=str(payload["digest"]),
                size_bytes=len(encoded),
                created_at=regression.created_at,
            )
            session.add(row)
            references = [
                ("RELEVANT_FILE", path, "Changed file relevant to this repair.")
                for path in changed_files
            ] + [
                ("RELATED_TEST", str(path), "Related test selected by impact analysis.")
                for path in tests
                if path
            ]
            for ordinal, (item_type, reference, reason) in enumerate(references, start=1):
                session.add(
                    RepairContextItem(
                        id=str(uuid.uuid4()),
                        repair_context_id=context_id,
                        ordinal=ordinal,
                        item_type=item_type,
                        relative_reference=reference,
                        reason=reason,
                    )
                )
            session.flush()
            response = self._public(row)
        self.events.publish(
            "repair_context_ready",
            project_id,
            {"repair_context_id": context_id, "regression_id": regression_id},
        )
        return response

    @staticmethod
    def _bundle_refs(session: Any, bundle_id: str | None) -> list[str]:
        if not bundle_id:
            return []
        return list(
            session.scalars(
                select(EvidenceBundleItem.artifact_id)
                .where(EvidenceBundleItem.bundle_id == bundle_id)
                .order_by(EvidenceBundleItem.ordinal)
            ).all()
        )

    def get(self, project_id: str, context_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RepairContext, context_id)
            if row is None or row.project_id != project_id:
                raise RepairContextError("REPAIR_CONTEXT_NOT_FOUND")
            return self._public(row)

    def copy_payload(self, project_id: str, context_id: str) -> dict[str, Any]:
        context = self.get(project_id, context_id)
        return {
            "context_id": context_id,
            "text": json.dumps(context["payload"], indent=2, ensure_ascii=False),
            "transmitted": False,
        }

    def save_local(self, project_id: str, context_id: str) -> dict[str, Any]:
        context = self.get(project_id, context_id)
        target = (self.root / project_id / f"{context_id}.json").resolve()
        if self.root not in target.parents:
            raise RepairContextError("REPAIR_CONTEXT_PATH_INVALID")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(_canonical(context["payload"]))
        os.chmod(temporary, 0o600)
        temporary.replace(target)
        relative = str(target.relative_to(self.root.parent))
        with self.sessions.begin() as session:
            row = session.get(RepairContext, context_id)
            if row is not None:
                row.saved_relative_path = relative
        return {"context_id": context_id, "relative_path": relative, "saved": True}

    @staticmethod
    def _public(row: RepairContext) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "change_id": row.change_id,
            "regression_id": row.regression_id,
            "schema_version": row.schema_version,
            "source_identity": json.loads(row.source_identity_json),
            "payload": json.loads(row.payload_json),
            "digest": row.digest,
            "size_bytes": row.size_bytes,
            "saved_relative_path": row.saved_relative_path,
            "created_at": row.created_at,
        }

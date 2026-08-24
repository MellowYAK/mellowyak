from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorCandidate,
    BehaviorCandidateLink,
    ContextReceipt,
    ContextReceiptItem,
    ImpactAnalysis,
    ImpactAnalysisInput,
    ImpactAnalysisPath,
    ImpactAnalysisResult,
    ImpactEdge,
    ImpactNode,
    Project,
    ProjectChange,
    ProjectFile,
    ProjectGitSnapshot,
    ProjectScanRun,
    SourceEpisode,
    SourceSnapshot,
)
from mellowyak_engine.git.observer import committed_changed_paths, observe_git
from mellowyak_engine.impact.models import (
    ALGORITHM_VERSION,
    EdgeFact,
    NodeFact,
    TraversalPolicy,
)
from mellowyak_engine.impact.ranking import rank_result
from mellowyak_engine.impact.traversal import traverse

MAX_INTENT_CHARS = 2_000
MAX_RECEIPT_FILES = 20
MAX_RECEIPT_SYMBOLS = 20
MAX_RECEIPT_PATHS = 12
MAX_RECEIPT_SNIPPETS = 0
MAX_RECEIPT_SOURCE_BYTES = 0
MAX_RECEIPT_JSON_BYTES = 65_536


class ImpactServiceError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load_json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _changed_paths_from_state(state: object) -> list[str]:
    staged = [str(item).split(":", 1)[-1] for item in getattr(state, "staged", ())]
    return sorted(
        set(staged + list(getattr(state, "unstaged", ())) + list(getattr(state, "untracked", ())))
    )


def _stable_key(*values: str) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def _iso(value: datetime) -> str:
    return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).isoformat()


class ImpactService:
    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    @staticmethod
    def _project(session: Session, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise ImpactServiceError("PROJECT_NOT_FOUND")
        if not project.canonical_root_path:
            raise ImpactServiceError("PROJECT_ROOT_UNAVAILABLE")
        return project

    @staticmethod
    def _latest_scan(session: Session, project_id: str) -> ProjectScanRun | None:
        return session.scalars(
            select(ProjectScanRun)
            .where(ProjectScanRun.project_id == project_id, ProjectScanRun.status == "completed")
            .order_by(ProjectScanRun.completed_at.desc(), ProjectScanRun.started_at.desc())
            .limit(1)
        ).first()

    def current_change(self, project_id: str) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            root = Path(project.repository_root_path or project.canonical_root_path).resolve(
                strict=False
            )
            if not root.is_dir():
                raise ImpactServiceError("PROJECT_ROOT_UNAVAILABLE")
            state = observe_git(root)
            prior_snapshots = session.scalars(
                select(ProjectGitSnapshot)
                .where(ProjectGitSnapshot.project_id == project_id)
                .order_by(ProjectGitSnapshot.observed_at.desc())
                .limit(50)
            ).all()
            prior_head = next(
                (
                    row.head_sha
                    for row in prior_snapshots
                    if row.head_sha and row.head_sha != state.head_sha
                ),
                None,
            )
            if not state.available:
                source_snapshot = session.scalars(
                    select(SourceSnapshot)
                    .where(SourceSnapshot.project_id == project_id)
                    .order_by(SourceSnapshot.created_at.desc())
                    .limit(1)
                ).first()
                episode = session.scalars(
                    select(SourceEpisode)
                    .where(SourceEpisode.project_id == project_id)
                    .order_by(SourceEpisode.started_at.desc())
                    .limit(1)
                ).first()
                kind = "snapshot_episode"
                base_head = None
                changed_paths = (
                    sorted(
                        set(
                            _load_json(episode.added_paths_json, [])
                            + _load_json(episode.modified_paths_json, [])
                            + _load_json(episode.deleted_paths_json, [])
                        )
                    )
                    if episode
                    else []
                )
                exact_fingerprint = (
                    source_snapshot.manifest_digest
                    if source_snapshot is not None
                    else state.worktree_fingerprint
                )
                identity_material = (
                    f"snapshot:{source_snapshot.id if source_snapshot else 'PENDING'}:"
                    f"{exact_fingerprint}:{episode.id if episode else 'NO_EPISODE'}"
                )
            elif state.is_dirty:
                kind = "uncommitted_worktree"
                base_head = state.head_sha
                changed_paths = _changed_paths_from_state(state)
                exact_fingerprint = state.worktree_fingerprint
                identity_material = (
                    f"working:{state.head_sha or 'UNBORN'}:{state.worktree_fingerprint}"
                )
            else:
                kind = "committed"
                base_head = prior_head or state.head_sha
                changed_paths = list(committed_changed_paths(root, base_head, state.head_sha))
                exact_fingerprint = state.worktree_fingerprint
                identity_material = f"commit:{base_head or 'UNBORN'}:{state.head_sha or 'UNBORN'}"
            project.current_branch = state.branch
            project.current_head_sha = state.head_sha
            project.current_worktree_fingerprint = state.worktree_fingerprint
            project.updated_at = datetime.now(UTC)
            logical_key = _stable_key(project_id, identity_material)
            change = session.scalars(
                select(ProjectChange).where(
                    ProjectChange.project_id == project_id,
                    ProjectChange.logical_key == logical_key,
                )
            ).first()
            now = datetime.now(UTC)
            if change is None:
                revision = (
                    int(
                        session.scalar(
                            select(func.max(ProjectChange.revision)).where(
                                ProjectChange.project_id == project_id
                            )
                        )
                        or 0
                    )
                    + 1
                )
                change = ProjectChange(
                    id=f"chg-{logical_key[:32]}",
                    project_id=project_id,
                    logical_key=logical_key,
                    change_kind=kind,
                    revision=revision,
                    base_head_sha=base_head,
                    head_sha=state.head_sha,
                    worktree_fingerprint=exact_fingerprint,
                    changed_paths_json=_json(changed_paths),
                    status="change_detected" if changed_paths else "no_changes",
                    created_at=now,
                    updated_at=now,
                )
                session.add(change)
                self.events.publish(
                    "change_stabilized",
                    project_id,
                    {
                        "change_id": change.id,
                        "revision": revision,
                        "changed_file_count": len(changed_paths),
                    },
                )
            else:
                change.changed_paths_json = _json(changed_paths)
                change.updated_at = now
            stale_identity_reason = (
                "git_change_identity_changed" if state.available else "source_identity_changed"
            )
            session.execute(
                update(ImpactAnalysis)
                .where(
                    ImpactAnalysis.project_id == project_id,
                    ImpactAnalysis.change_id != change.id,
                    ImpactAnalysis.stale.is_(False),
                )
                .values(stale=True, stale_reasons_json=_json([stale_identity_reason]))
            )
            session.execute(
                update(ContextReceipt)
                .where(
                    ContextReceipt.project_id == project_id,
                    ContextReceipt.change_id != change.id,
                    ContextReceipt.stale.is_(False),
                )
                .values(stale=True)
            )
            return self._change_dict(change)

    @staticmethod
    def _change_dict(change: ProjectChange) -> dict[str, Any]:
        return {
            "id": change.id,
            "project_id": change.project_id,
            "change_kind": change.change_kind,
            "revision": change.revision,
            "base_head_sha": change.base_head_sha,
            "head_sha": change.head_sha,
            "worktree_fingerprint": change.worktree_fingerprint,
            "changed_paths": _load_json(change.changed_paths_json, []),
            "task_intent": change.task_intent,
            "status": change.status,
            "created_at": _iso(change.created_at),
            "updated_at": _iso(change.updated_at),
        }

    def get_change(self, project_id: str, change_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            self._project(session, project_id)
            change = session.get(ProjectChange, change_id)
            if change is None or change.project_id != project_id:
                raise ImpactServiceError("CHANGE_NOT_FOUND")
            return self._change_dict(change)

    def set_intent(self, project_id: str, change_id: str, intent: str | None) -> dict[str, Any]:
        normalized = " ".join((intent or "").split())
        if len(normalized) > MAX_INTENT_CHARS:
            raise ImpactServiceError("TASK_INTENT_TOO_LONG")
        with self.sessions.begin() as session:
            self._project(session, project_id)
            change = session.get(ProjectChange, change_id)
            if change is None or change.project_id != project_id:
                raise ImpactServiceError("CHANGE_NOT_FOUND")
            change.task_intent = normalized or None
            change.updated_at = datetime.now(UTC)
            return self._change_dict(change)

    def analyze(
        self,
        project_id: str,
        change_id: str,
        policy: TraversalPolicy | None = None,
    ) -> dict[str, Any]:
        bounded = (policy or TraversalPolicy()).bounded()
        self.events.publish("impact_analysis_started", project_id, {"change_id": change_id})
        with self.sessions.begin() as session:
            self._project(session, project_id)
            change = session.get(ProjectChange, change_id)
            if change is None or change.project_id != project_id:
                raise ImpactServiceError("CHANGE_NOT_FOUND")
            scan = self._latest_scan(session, project_id)
            if scan is None:
                raise ImpactServiceError("SOURCE_SCAN_REQUIRED")
            nodes = session.scalars(
                select(ImpactNode).where(ImpactNode.project_id == project_id)
            ).all()
            edges = session.scalars(
                select(ImpactEdge).where(ImpactEdge.project_id == project_id)
            ).all()
            node_facts = [
                NodeFact(row.id, row.node_type, row.label, row.relative_path, row.stale)
                for row in nodes
            ]
            edge_facts = [
                EdgeFact(
                    row.id,
                    row.source_node_id,
                    row.target_node_id,
                    row.edge_type,
                    row.provenance,
                    row.parser_adapter,
                    row.source_scan_revision,
                    row.stale,
                )
                for row in edges
            ]
            changed_paths = [str(item) for item in _load_json(change.changed_paths_json, [])]
            changed_node_ids = [
                row.id
                for row in nodes
                if row.node_type in {"FILE", "TEST"} and row.relative_path in changed_paths
            ]
            outcome = traverse(node_facts, edge_facts, changed_node_ids, bounded)
            changed_set = set(changed_paths)
            for result in outcome.results:
                score, reasons = rank_result(result, change.task_intent, changed_set)
                result.ranking_score = score
                result.ranking_reasons = reasons
            analysis_revision = (
                int(
                    session.scalar(
                        select(func.max(ImpactAnalysis.analysis_revision)).where(
                            ImpactAnalysis.project_id == project_id,
                            ImpactAnalysis.change_id == change_id,
                        )
                    )
                    or 0
                )
                + 1
            )
            analysis = ImpactAnalysis(
                id=str(uuid.uuid4()),
                project_id=project_id,
                change_id=change_id,
                analysis_revision=analysis_revision,
                base_head_sha=change.base_head_sha,
                head_sha=change.head_sha,
                worktree_fingerprint=change.worktree_fingerprint,
                scan_revision=scan.id,
                algorithm_version=ALGORITHM_VERSION,
                status="completed",
                changed_file_count=len(changed_paths),
                impacted_node_count=len(outcome.results),
                unknown_count=sum(item.unknown for item in outcome.results)
                + len(set(changed_paths) - {row.relative_path for row in nodes}),
                stale_count=sum(item.stale for item in outcome.results),
                heuristic_count=sum(
                    item.impact_class == "HEURISTICALLY_RELATED" for item in outcome.results
                ),
                truncated=outcome.truncated,
                truncation_reasons_json=_json(outcome.truncation_reasons),
                duration_ms=outcome.duration_ms,
                stale=False,
                stale_reasons_json="[]",
                created_at=datetime.now(UTC),
            )
            session.add(analysis)
            session.flush()
            session.add(
                ImpactAnalysisInput(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis.id,
                    project_id=project_id,
                    changed_files_json=_json(changed_paths),
                    task_intent=change.task_intent,
                    traversal_policy_json=_json(bounded.public_dict()),
                )
            )
            for result in outcome.results:
                row = ImpactAnalysisResult(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis.id,
                    project_id=project_id,
                    node_id=result.node.id,
                    node_type=result.node.node_type,
                    display_name=result.node.label,
                    relative_path=result.node.relative_path,
                    impact_class=result.impact_class,
                    minimum_depth=result.minimum_depth,
                    strongest_provenance=result.strongest_provenance,
                    stale=result.stale,
                    unknown=result.unknown,
                    explanation=result.explanation,
                    path_count=len(result.paths),
                    ranking_score=result.ranking_score,
                    ranking_reasons_json=_json(result.ranking_reasons),
                    unknown_reason=result.unknown_reason,
                )
                session.add(row)
                session.flush()
                for ordinal, path in enumerate(result.paths[: bounded.max_paths_per_result]):
                    session.add(
                        ImpactAnalysisPath(
                            id=str(uuid.uuid4()),
                            analysis_id=analysis.id,
                            result_id=row.id,
                            project_id=project_id,
                            ordinal=ordinal,
                            depth=len(path),
                            path_json=_json([step.public_dict() for step in path]),
                        )
                    )
            missing = sorted(set(changed_paths) - {row.relative_path for row in nodes})
            for relative in missing:
                session.add(
                    ImpactAnalysisResult(
                        id=str(uuid.uuid4()),
                        analysis_id=analysis.id,
                        project_id=project_id,
                        node_id=None,
                        node_type="UNKNOWN_REFERENCE",
                        display_name=PurePosixPath(relative).name,
                        relative_path=relative,
                        impact_class="UNKNOWN_BOUNDARY",
                        minimum_depth=0,
                        strongest_provenance="UNKNOWN",
                        stale=False,
                        unknown=True,
                        explanation=(
                            f"{relative} changed but is missing, deleted, excluded, "
                            f"or absent from scan revision {scan.id}."
                        ),
                        path_count=0,
                        ranking_score=60,
                        ranking_reasons_json=_json(
                            ["exact changed path", "missing from current source graph"]
                        ),
                        unknown_reason=(
                            "Changed file is missing, deleted, excluded, "
                            "or absent from the current scan."
                        ),
                    )
                )
            session.execute(
                update(ImpactAnalysis)
                .where(
                    ImpactAnalysis.project_id == project_id,
                    ImpactAnalysis.id != analysis.id,
                    ImpactAnalysis.scan_revision != scan.id,
                    ImpactAnalysis.stale.is_(False),
                )
                .values(stale=True, stale_reasons_json=_json(["scan_revision_changed"]))
            )
            session.execute(
                update(ContextReceipt)
                .where(
                    ContextReceipt.project_id == project_id,
                    ContextReceipt.analysis_id != analysis.id,
                    ContextReceipt.stale.is_(False),
                )
                .values(stale=True)
            )
            analysis_id = analysis.id
        self._discover_behavior_candidates(project_id, change_id, analysis_id)
        self.events.publish(
            "impact_analysis_completed",
            project_id,
            {"change_id": change_id, "analysis_id": analysis_id},
        )
        return self.get_impact(project_id, change_id, analysis_id)

    def _stale_reasons(self, session: Session, analysis: ImpactAnalysis) -> list[str]:
        reasons = list(_load_json(analysis.stale_reasons_json, []))
        project = self._project(session, analysis.project_id)
        latest_scan = self._latest_scan(session, analysis.project_id)
        if project.current_head_sha and project.current_head_sha != analysis.head_sha:
            reasons.append("git_head_changed")
        if (
            project.current_worktree_fingerprint
            and project.current_worktree_fingerprint != analysis.worktree_fingerprint
        ):
            reasons.append("worktree_fingerprint_changed")
        if latest_scan and latest_scan.id != analysis.scan_revision:
            reasons.append("scan_revision_changed")
        return sorted(set(reasons))

    def get_impact(
        self, project_id: str, change_id: str, analysis_id: str | None = None
    ) -> dict[str, Any]:
        with self.sessions.begin() as session:
            self._project(session, project_id)
            change = session.get(ProjectChange, change_id)
            if change is None or change.project_id != project_id:
                raise ImpactServiceError("CHANGE_NOT_FOUND")
            query = select(ImpactAnalysis).where(
                ImpactAnalysis.project_id == project_id, ImpactAnalysis.change_id == change_id
            )
            if analysis_id:
                query = query.where(ImpactAnalysis.id == analysis_id)
            analysis = session.scalars(
                query.order_by(ImpactAnalysis.analysis_revision.desc()).limit(1)
            ).first()
            if analysis is None:
                raise ImpactServiceError("IMPACT_ANALYSIS_NOT_FOUND")
            stale_reasons = self._stale_reasons(session, analysis)
            if stale_reasons and not analysis.stale:
                analysis.stale = True
                analysis.stale_reasons_json = _json(stale_reasons)
                self.events.publish(
                    "impact_analysis_stale",
                    project_id,
                    {"analysis_id": analysis.id, "reasons": stale_reasons},
                )
            rows = session.scalars(
                select(ImpactAnalysisResult)
                .where(
                    ImpactAnalysisResult.project_id == project_id,
                    ImpactAnalysisResult.analysis_id == analysis.id,
                )
                .order_by(
                    ImpactAnalysisResult.minimum_depth,
                    ImpactAnalysisResult.ranking_score.desc(),
                    ImpactAnalysisResult.relative_path,
                )
            ).all()
            return {
                "analysis": self._analysis_dict(analysis, stale_reasons),
                "results": [self._result_dict(row) for row in rows],
            }

    @staticmethod
    def _analysis_dict(analysis: ImpactAnalysis, stale_reasons: list[str]) -> dict[str, Any]:
        return {
            "id": analysis.id,
            "project_id": analysis.project_id,
            "change_id": analysis.change_id,
            "analysis_revision": analysis.analysis_revision,
            "base_head_sha": analysis.base_head_sha,
            "head_sha": analysis.head_sha,
            "worktree_fingerprint": analysis.worktree_fingerprint,
            "scan_revision": analysis.scan_revision,
            "algorithm_version": analysis.algorithm_version,
            "status": analysis.status,
            "changed_file_count": analysis.changed_file_count,
            "impacted_node_count": analysis.impacted_node_count,
            "unknown_count": analysis.unknown_count,
            "stale_count": analysis.stale_count,
            "heuristic_count": analysis.heuristic_count,
            "truncated": analysis.truncated,
            "truncation_reasons": _load_json(analysis.truncation_reasons_json, []),
            "duration_ms": analysis.duration_ms,
            "stale": analysis.stale or bool(stale_reasons),
            "stale_reasons": stale_reasons,
            "created_at": _iso(analysis.created_at),
        }

    @staticmethod
    def _result_dict(row: ImpactAnalysisResult) -> dict[str, Any]:
        return {
            "id": row.id,
            "node_id": row.node_id,
            "node_type": row.node_type,
            "display_name": row.display_name,
            "relative_path": row.relative_path,
            "impact_class": row.impact_class,
            "minimum_depth": row.minimum_depth,
            "strongest_provenance": row.strongest_provenance,
            "stale": row.stale,
            "unknown": row.unknown,
            "explanation": row.explanation,
            "path_count": row.path_count,
            "ranking_score": row.ranking_score,
            "ranking_reasons": _load_json(row.ranking_reasons_json, []),
            "unknown_reason": row.unknown_reason,
        }

    def paths(self, project_id: str, change_id: str) -> list[dict[str, Any]]:
        impact = self.get_impact(project_id, change_id)
        analysis_id = str(impact["analysis"]["id"])
        with self.sessions() as session:
            rows = session.execute(
                select(ImpactAnalysisPath, ImpactAnalysisResult)
                .join(ImpactAnalysisResult, ImpactAnalysisResult.id == ImpactAnalysisPath.result_id)
                .where(
                    ImpactAnalysisPath.project_id == project_id,
                    ImpactAnalysisPath.analysis_id == analysis_id,
                )
                .order_by(ImpactAnalysisPath.depth, ImpactAnalysisPath.ordinal)
            ).all()
            return [
                {
                    "id": path.id,
                    "result_id": result.id,
                    "result": result.display_name,
                    "impact_class": result.impact_class,
                    "depth": path.depth,
                    "steps": _load_json(path.path_json, []),
                }
                for path, result in rows
            ]

    def unknowns(self, project_id: str, change_id: str) -> list[dict[str, Any]]:
        impact = self.get_impact(project_id, change_id)
        return [item for item in impact["results"] if item["unknown"] or item["stale"]]

    def create_context_receipt(self, project_id: str, change_id: str) -> dict[str, Any]:
        impact = self.get_impact(project_id, change_id)
        analysis_data = impact["analysis"]
        analysis_id = str(analysis_data["id"])
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            change = session.get(ProjectChange, change_id)
            analysis = session.get(ImpactAnalysis, analysis_id)
            if change is None or analysis is None or change.project_id != project_id:
                raise ImpactServiceError("CHANGE_NOT_FOUND")
            constraints = {
                "max_files": MAX_RECEIPT_FILES,
                "max_symbols": MAX_RECEIPT_SYMBOLS,
                "max_snippets": MAX_RECEIPT_SNIPPETS,
                "max_source_bytes": MAX_RECEIPT_SOURCE_BYTES,
                "max_receipt_json_bytes": MAX_RECEIPT_JSON_BYTES,
                "source_content_included": False,
                "sensitive_content_eligible": False,
            }
            receipt_key = _stable_key(
                project_id,
                change_id,
                analysis_id,
                change.task_intent or "",
                _json(constraints),
            )
            existing = session.scalars(
                select(ContextReceipt).where(
                    ContextReceipt.project_id == project_id,
                    ContextReceipt.receipt_key == receipt_key,
                )
            ).first()
            if existing is not None:
                return self._receipt_dict(session, existing, project.display_name)

            results = session.scalars(
                select(ImpactAnalysisResult)
                .where(
                    ImpactAnalysisResult.project_id == project_id,
                    ImpactAnalysisResult.analysis_id == analysis_id,
                )
                .order_by(
                    ImpactAnalysisResult.ranking_score.desc(), ImpactAnalysisResult.relative_path
                )
            ).all()
            project_files = {
                row.relative_path: row
                for row in session.scalars(
                    select(ProjectFile).where(
                        ProjectFile.project_id == project_id, ProjectFile.deleted_at.is_(None)
                    )
                ).all()
            }
            selected: list[tuple[ImpactAnalysisResult, ProjectFile]] = []
            excluded: list[dict[str, str]] = []
            file_paths: set[str] = set()
            symbol_count = 0
            for result in results:
                relative = result.relative_path or ""
                file_row = project_files.get(relative)
                if result.unknown or result.stale:
                    excluded.append(
                        {"path": relative or result.display_name, "reason": "unknown_or_stale"}
                    )
                    continue
                if not relative or file_row is None:
                    excluded.append(
                        {
                            "path": relative or result.display_name,
                            "reason": "no_current_file_metadata",
                        }
                    )
                    continue
                if file_row.is_sensitive:
                    excluded.append({"path": relative, "reason": "sensitive_content_not_eligible"})
                    continue
                if result.node_type == "SYMBOL":
                    if symbol_count >= MAX_RECEIPT_SYMBOLS:
                        excluded.append({"path": relative, "reason": "symbol_budget"})
                        continue
                    symbol_count += 1
                elif relative not in file_paths and len(file_paths) >= MAX_RECEIPT_FILES:
                    excluded.append({"path": relative, "reason": "file_budget"})
                    continue
                selected.append((result, file_row))
                file_paths.add(relative)
            path_rows = session.execute(
                select(ImpactAnalysisPath, ImpactAnalysisResult)
                .join(ImpactAnalysisResult, ImpactAnalysisResult.id == ImpactAnalysisPath.result_id)
                .where(
                    ImpactAnalysisPath.project_id == project_id,
                    ImpactAnalysisPath.analysis_id == analysis_id,
                )
                .order_by(ImpactAnalysisPath.depth, ImpactAnalysisPath.ordinal)
                .limit(MAX_RECEIPT_PATHS)
            ).all()
            paths = [
                {
                    "id": path.id,
                    "result_id": result.id,
                    "result": result.display_name,
                    "impact_class": result.impact_class,
                    "depth": path.depth,
                    "steps": _load_json(path.path_json, []),
                }
                for path, result in path_rows
            ]
            unknowns = [
                {
                    "path": item["relative_path"] or item["display_name"],
                    "reason": item["unknown_reason"]
                    or ("stale relation" if item["stale"] else "unknown boundary"),
                }
                for item in impact["results"]
                if item["unknown"] or item["stale"]
            ]
            metrics = {
                "selected_files": len(file_paths),
                "selected_symbols": symbol_count,
                "related_tests": sum(result.node_type == "TEST" for result, _ in selected),
                "relationship_paths": len(paths),
                "unknown_boundaries": len(unknowns),
                "referenced_file_bytes": sum(row.size_bytes for _, row in selected),
                "selected_source_bytes": 0,
                "receipt_json_bytes": 0,
            }
            receipt = ContextReceipt(
                id=f"ctx-{receipt_key[:32]}",
                project_id=project_id,
                change_id=change_id,
                analysis_id=analysis_id,
                receipt_key=receipt_key,
                request_text=change.task_intent,
                source_revision_json=_json(
                    {
                        "base_head_sha": analysis.base_head_sha,
                        "head_sha": analysis.head_sha,
                        "worktree_fingerprint": analysis.worktree_fingerprint,
                        "scan_revision": analysis.scan_revision,
                        "algorithm_version": analysis.algorithm_version,
                    }
                ),
                constraints_json=_json(constraints),
                unknowns_json=_json(unknowns),
                excluded_context_json=_json(excluded),
                relationship_paths_json=_json(paths),
                size_metrics_json=_json(metrics),
                truncated=bool(excluded) or bool(analysis.truncated),
                stale=analysis.stale,
                created_at=datetime.now(UTC),
            )
            session.add(receipt)
            session.flush()
            for ordinal, (result, file_row) in enumerate(selected):
                reasons = _load_json(result.ranking_reasons_json, [])
                session.add(
                    ContextReceiptItem(
                        id=str(uuid.uuid4()),
                        receipt_id=receipt.id,
                        project_id=project_id,
                        ordinal=ordinal,
                        relative_path=file_row.relative_path,
                        item_type=result.node_type,
                        reason_selected=result.explanation,
                        relationship_provenance=result.strongest_provenance,
                        relevance_class=result.impact_class,
                        stale=result.stale,
                        size_bytes=file_row.size_bytes,
                        content_eligible=not file_row.is_sensitive,
                        selection_reasons_json=_json(reasons),
                    )
                )
            session.flush()
            payload = self._receipt_dict(session, receipt, project.display_name)
            encoded = _json(payload).encode()
            metrics["receipt_json_bytes"] = len(encoded)
            if len(encoded) > MAX_RECEIPT_JSON_BYTES:
                receipt.truncated = True
                excluded.append(
                    {"path": "relationship_paths", "reason": "receipt_json_byte_budget"}
                )
                receipt.relationship_paths_json = _json(paths[:3])
                receipt.excluded_context_json = _json(excluded)
            receipt.size_metrics_json = _json(metrics)
            payload = self._receipt_dict(session, receipt, project.display_name)
        self.events.publish(
            "context_receipt_generated",
            project_id,
            {"change_id": change_id, "receipt_id": payload["id"]},
        )
        return payload

    def get_context_receipt(self, project_id: str, change_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = self._project(session, project_id)
            receipt = session.scalars(
                select(ContextReceipt)
                .where(
                    ContextReceipt.project_id == project_id, ContextReceipt.change_id == change_id
                )
                .order_by(ContextReceipt.created_at.desc())
                .limit(1)
            ).first()
            if receipt is None:
                raise ImpactServiceError("CONTEXT_RECEIPT_NOT_FOUND")
            return self._receipt_dict(session, receipt, project.display_name)

    @staticmethod
    def _receipt_dict(
        session: Session, receipt: ContextReceipt, project_name: str
    ) -> dict[str, Any]:
        items = session.scalars(
            select(ContextReceiptItem)
            .where(
                ContextReceiptItem.project_id == receipt.project_id,
                ContextReceiptItem.receipt_id == receipt.id,
            )
            .order_by(ContextReceiptItem.ordinal)
        ).all()
        return {
            "schema": "mellowyak.context_receipt.v1",
            "id": receipt.id,
            "project": {"id": receipt.project_id, "name": project_name},
            "change_id": receipt.change_id,
            "analysis_id": receipt.analysis_id,
            "request": receipt.request_text,
            "source_revision": _load_json(receipt.source_revision_json, {}),
            "selected_files": [
                {
                    "relative_path": item.relative_path,
                    "type": item.item_type,
                    "reason_selected": item.reason_selected,
                    "relationship_provenance": item.relationship_provenance,
                    "relevance_class": item.relevance_class,
                    "stale": item.stale,
                    "size": item.size_bytes,
                    "content_eligible": item.content_eligible,
                    "selection_reasons": _load_json(item.selection_reasons_json, []),
                }
                for item in items
            ],
            "selected_symbols": [
                item.relative_path for item in items if item.item_type == "SYMBOL"
            ],
            "related_tests": [item.relative_path for item in items if item.item_type == "TEST"],
            "relationship_paths": _load_json(receipt.relationship_paths_json, []),
            "constraints": _load_json(receipt.constraints_json, {}),
            "unknowns": _load_json(receipt.unknowns_json, []),
            "excluded_context": _load_json(receipt.excluded_context_json, []),
            "selection_reasons": sorted(
                {reason for item in items for reason in _load_json(item.selection_reasons_json, [])}
            ),
            "size_metrics": _load_json(receipt.size_metrics_json, {}),
            "truncated": receipt.truncated,
            "stale": receipt.stale,
            "source_uploaded": False,
            "created_at": _iso(receipt.created_at),
        }

    @staticmethod
    def _candidate_title(value: str) -> str:
        stem = PurePosixPath(value).stem
        stem = re.sub(r"(?:\.test|\.spec|_test|^test_)", " ", stem, flags=re.IGNORECASE)
        words = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem).replace("_", " ").replace("-", " ")
        label = " ".join(words.split()).strip().capitalize()
        return label or "Observed test behavior"

    def _discover_behavior_candidates(
        self, project_id: str, change_id: str, analysis_id: str
    ) -> None:
        discovered = 0
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(ImpactAnalysisResult).where(
                    ImpactAnalysisResult.project_id == project_id,
                    ImpactAnalysisResult.analysis_id == analysis_id,
                    ImpactAnalysisResult.node_type == "TEST",
                    ImpactAnalysisResult.stale.is_(False),
                )
            ).all()
            for row in rows:
                source_key = row.relative_path or row.display_name
                candidate = session.scalars(
                    select(BehaviorCandidate).where(
                        BehaviorCandidate.project_id == project_id,
                        BehaviorCandidate.source_type == "test_name",
                        BehaviorCandidate.source_key == source_key,
                    )
                ).first()
                now = datetime.now(UTC)
                if candidate is None:
                    candidate = BehaviorCandidate(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        source_type="test_name",
                        source_key=source_key,
                        title=self._candidate_title(source_key),
                        status="CANDIDATE",
                        evidence_state="none",
                        verification_state="not_configured",
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(candidate)
                    session.flush()
                    discovered += 1
                link = session.scalars(
                    select(BehaviorCandidateLink).where(
                        BehaviorCandidateLink.project_id == project_id,
                        BehaviorCandidateLink.behavior_candidate_id == candidate.id,
                        BehaviorCandidateLink.change_id == change_id,
                        BehaviorCandidateLink.impact_node_id == row.node_id,
                        BehaviorCandidateLink.relation_type == "IMPACT_TEST_HINT",
                    )
                ).first()
                if link is None:
                    session.add(
                        BehaviorCandidateLink(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            behavior_candidate_id=candidate.id,
                            change_id=change_id,
                            impact_node_id=row.node_id,
                            relation_type="IMPACT_TEST_HINT",
                        )
                    )
        if discovered:
            self.events.publish(
                "behavior_candidate_discovered",
                project_id,
                {"count": discovered, "change_id": change_id},
            )

    def behavior_candidates(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(BehaviorCandidate)
                .where(BehaviorCandidate.project_id == project_id)
                .order_by(BehaviorCandidate.updated_at.desc(), BehaviorCandidate.title)
            ).all()
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "source_type": row.source_type,
                    "source_key": row.source_key,
                    "status": row.status,
                    "evidence": row.evidence_state,
                    "verification": row.verification_state,
                    "not_protected": True,
                    "created_at": _iso(row.created_at),
                    "updated_at": _iso(row.updated_at),
                }
                for row in rows
            ]

    def set_candidate_status(
        self, project_id: str, candidate_id: str, action: str
    ) -> dict[str, Any]:
        if action not in {"keep", "dismiss", "prepare"}:
            raise ImpactServiceError("BEHAVIOR_ACTION_INVALID")
        with self.sessions.begin() as session:
            self._project(session, project_id)
            row = session.get(BehaviorCandidate, candidate_id)
            if row is None or row.project_id != project_id:
                raise ImpactServiceError("BEHAVIOR_CANDIDATE_NOT_FOUND")
            now = datetime.now(UTC)
            row.status = {"keep": "CANDIDATE", "dismiss": "DISMISSED", "prepare": "PROMOTED_STUB"}[
                action
            ]
            row.kept_at = now if action in {"keep", "prepare"} else None
            row.updated_at = now
            return {
                "id": row.id,
                "status": row.status,
                "verification": row.verification_state,
                "not_protected": True,
            }

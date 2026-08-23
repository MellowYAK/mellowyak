from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    ImpactEdge,
    ImpactNode,
    Project,
    ProjectChangeObservation,
    ProjectFile,
    ProjectGitSnapshot,
    ProjectScanRun,
    ScanFinding,
)
from mellowyak_engine.git.observer import GitState, observe_git
from mellowyak_engine.scanning.policy import iter_candidates, language_for


class ProjectError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def privacy_safe_path(path: Path) -> str:
    resolved = path.resolve(strict=False)
    home = Path.home().resolve()
    try:
        relative = resolved.relative_to(home)
        return f"~/{relative.as_posix()}"
    except ValueError:
        return f"…/{resolved.name}"


def _manifest_hints(root: Path) -> tuple[list[str], list[str], list[str]]:
    frameworks: set[str] = set()
    tests: set[str] = set()
    runtimes: set[str] = set()
    package_json = root / "package.json"
    if package_json.is_file() and package_json.stat().st_size <= 256_000:
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
            dependencies = {
                str(item).lower()
                for group in ("dependencies", "devDependencies", "peerDependencies")
                for item in (payload.get(group, {}) if isinstance(payload, dict) else {})
            }
            for dependency, label in (
                ("react", "React"),
                ("vue", "Vue"),
                ("next", "Next.js"),
                ("svelte", "Svelte"),
                ("@angular/core", "Angular"),
                ("vite", "Vite"),
                ("express", "Express"),
            ):
                if dependency in dependencies:
                    frameworks.add(label)
            for dependency, label in (
                ("vitest", "Vitest"),
                ("jest", "Jest"),
                ("@playwright/test", "Playwright"),
                ("cypress", "Cypress"),
            ):
                if dependency in dependencies:
                    tests.add(label)
            runtimes.add("Node.js application hint")
        except (OSError, ValueError, TypeError):
            pass
    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and pyproject.stat().st_size <= 256_000:
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace").lower()
            for dependency, label in (
                ("fastapi", "FastAPI"),
                ("django", "Django"),
                ("flask", "Flask"),
            ):
                if dependency in text:
                    frameworks.add(label)
            for dependency, label in (("pytest", "pytest"), ("unittest", "unittest")):
                if dependency in text:
                    tests.add(label)
            runtimes.add("Python application hint")
        except OSError:
            pass
    if (root / "Cargo.toml").is_file():
        runtimes.add("Rust application hint")
    if (root / "composer.json").is_file():
        runtimes.add("PHP application hint")
    return sorted(frameworks), sorted(tests), sorted(runtimes)


class ProjectService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        installation_id: str,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.installation_id = installation_id
        self.events = events

    def validate_root(self, raw_path: str) -> Path:
        if not raw_path or "\x00" in raw_path:
            raise ProjectError("PROJECT_PATH_INVALID")
        candidate = Path(raw_path).expanduser()
        try:
            root = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as error:
            raise ProjectError("PROJECT_PATH_UNAVAILABLE") from error
        if not root.is_dir():
            raise ProjectError("PROJECT_PATH_NOT_DIRECTORY")
        if not os.access(root, os.R_OK | os.X_OK):
            raise ProjectError("PROJECT_PATH_UNREADABLE")
        return root

    def detect(self, raw_path: str) -> dict[str, Any]:
        root = self.validate_root(raw_path)
        git = observe_git(root)
        scan_root = Path(git.repository_root) if git.repository_root else root
        candidates, ignored_count = iter_candidates(scan_root)
        languages = Counter(
            language_for(item.absolute_path)
            for item in candidates[:10_000]
            if not item.symlink_outside and language_for(item.absolute_path) != "Unknown"
        )
        frameworks, tests, runtimes = _manifest_hints(scan_root)
        if any("test" in item.relative_path.lower() for item in candidates[:10_000]):
            tests.append("Test files detected")
        payload = {
            # These paths travel only over the authenticated loopback API. The
            # desktop must return the exact selected root when creating the
            # project; no source path is sent to a remote service.
            "selected_path": str(root),
            "repository_path": str(scan_root),
            "suggested_name": scan_root.name,
            "git": git.public_dict(),
            "languages": [name for name, _ in languages.most_common(12)],
            "language_counts": dict(languages),
            "frameworks": sorted(set(frameworks)),
            "tests": sorted(set(tests)),
            "runtime_hints": runtimes,
            "candidate_files": len(candidates),
            "ignored_paths": ignored_count,
            "relationship_coverage": "bounded deterministic adapters",
            "unsupported_coverage": "reported during initial scan",
            "source_remains_local": True,
        }
        self.events.publish("project_detection", None, {"git_available": git.available})
        return {"root": root, "repository_root": scan_root, "git_state": git, "public": payload}

    def _snapshot(self, session: Session, project: Project, state: GitState) -> ProjectGitSnapshot:
        snapshot = ProjectGitSnapshot(
            id=str(uuid.uuid4()),
            project_id=project.id,
            observed_at=datetime.now(UTC),
            branch=state.branch,
            head_sha=state.head_sha,
            is_detached=state.is_detached,
            is_dirty=state.is_dirty,
            staged_count=len(state.staged),
            unstaged_count=len(state.unstaged),
            untracked_count=len(state.untracked),
            ignored_count=state.ignored_count,
            worktree_fingerprint=state.worktree_fingerprint,
            status_payload=json.dumps(state.public_dict(), sort_keys=True, separators=(",", ":")),
        )
        session.add(snapshot)
        session.flush()
        return snapshot

    def create(self, raw_path: str, display_name: str, monitoring_mode: str) -> Project:
        if monitoring_mode not in {"passive", "paused"}:
            raise ProjectError("MONITORING_MODE_INVALID")
        detection = self.detect(raw_path)
        root: Path = detection["root"]
        repository_root: Path = detection["repository_root"]
        state: GitState = detection["git_state"]
        canonical = str(root)
        with self.sessions.begin() as session:
            duplicate = session.scalars(
                select(Project).where(
                    Project.canonical_root_path == canonical, Project.archived_at.is_(None)
                )
            ).first()
            if duplicate:
                raise ProjectError("PROJECT_ALREADY_CONNECTED")
            now = datetime.now(UTC)
            project = Project(
                id=str(uuid.uuid4()),
                installation_id=self.installation_id,
                display_name=(display_name.strip() or repository_root.name)[:240],
                root_path=canonical,
                canonical_root_path=canonical,
                repository_root_path=str(repository_root),
                created_at=now,
                updated_at=now,
                monitoring_mode=monitoring_mode,
                monitoring_status="active" if monitoring_mode == "passive" else "paused",
                current_branch=state.branch,
                current_head_sha=state.head_sha,
                current_worktree_fingerprint=state.worktree_fingerprint,
                detection_payload_json=json.dumps(
                    detection["public"], sort_keys=True, separators=(",", ":")
                ),
            )
            session.add(project)
            session.flush()
            self._snapshot(session, project, state)
            return project

    def get_model(self, project_id: str) -> Project:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None or project.archived_at is not None:
                raise ProjectError("PROJECT_NOT_FOUND")
            session.expunge(project)
            return project

    def refresh_git(
        self, project_id: str, changed_paths: list[str] | None = None
    ) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None or not project.canonical_root_path:
                raise ProjectError("PROJECT_NOT_FOUND")
            root = Path(project.canonical_root_path)
            if not root.is_dir():
                project.monitoring_status = "repository_unavailable"
                raise ProjectError("PROJECT_ROOT_UNAVAILABLE")
            state = observe_git(root)
            previous = project.current_worktree_fingerprint
            snapshot = self._snapshot(session, project, state)
            created_observation = False
            if previous and previous != state.worktree_fingerprint:
                existing = session.scalars(
                    select(ProjectChangeObservation).where(
                        ProjectChangeObservation.project_id == project_id,
                        ProjectChangeObservation.worktree_fingerprint == state.worktree_fingerprint,
                    )
                ).first()
                if existing is None:
                    session.add(
                        ProjectChangeObservation(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            observed_at=datetime.now(UTC),
                            previous_fingerprint=previous,
                            worktree_fingerprint=state.worktree_fingerprint,
                            changed_paths_json=json.dumps(
                                sorted(set(changed_paths or [])), separators=(",", ":")
                            ),
                            git_snapshot_id=snapshot.id,
                        )
                    )
                    created_observation = True
            project.current_branch = state.branch
            project.current_head_sha = state.head_sha
            project.current_worktree_fingerprint = state.worktree_fingerprint
            project.updated_at = datetime.now(UTC)
        if created_observation:
            self.events.publish(
                "git_state_change", project_id, {"fingerprint": state.worktree_fingerprint}
            )
        return state.public_dict()

    def _latest_git(self, session: Session, project_id: str) -> ProjectGitSnapshot | None:
        return session.scalars(
            select(ProjectGitSnapshot)
            .where(ProjectGitSnapshot.project_id == project_id)
            .order_by(ProjectGitSnapshot.observed_at.desc())
            .limit(1)
        ).first()

    def _latest_scan(self, session: Session, project_id: str) -> ProjectScanRun | None:
        return session.scalars(
            select(ProjectScanRun)
            .where(ProjectScanRun.project_id == project_id)
            .order_by(ProjectScanRun.started_at.desc())
            .limit(1)
        ).first()

    @staticmethod
    def _git_dict(snapshot: ProjectGitSnapshot | None) -> dict[str, Any]:
        if snapshot is None:
            return {
                "available": False,
                "branch": None,
                "head_sha": None,
                "is_detached": False,
                "is_dirty": False,
                "staged": [],
                "unstaged": [],
                "untracked": [],
                "ignored_count": 0,
                "worktree_fingerprint": "",
                "error": "GIT_UNAVAILABLE",
            }
        return json.loads(snapshot.status_payload)

    @staticmethod
    def _scan_dict(scan: ProjectScanRun | None) -> dict[str, Any] | None:
        if scan is None:
            return None
        return {
            "id": scan.id,
            "status": scan.status,
            "scan_version": scan.scan_version,
            "started_at": scan.started_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "total_candidates": scan.total_candidates,
            "processed_files": scan.processed_files,
            "included_files": scan.included_files,
            "excluded_files": scan.excluded_files,
            "binary_files": scan.binary_files,
            "sensitive_files": scan.sensitive_files,
            "failed_files": scan.failed_files,
            "unknown_items": scan.unknown_items,
            "unsupported_files": scan.unsupported_files,
            "test_files": scan.test_files,
            "relationship_count": scan.relationship_count,
            "duration_seconds": scan.duration_seconds,
            "error_summary": scan.error_summary,
        }

    def serialize(self, session: Session, project: Project) -> dict[str, Any]:
        detection = json.loads(project.detection_payload_json or "{}")
        latest_git = self._latest_git(session, project.id)
        latest_scan = self._latest_scan(session, project.id)
        return {
            "id": project.id,
            "display_name": project.display_name,
            "display_path": privacy_safe_path(
                Path(project.canonical_root_path or project.root_path)
            ),
            "repository_path": privacy_safe_path(
                Path(project.repository_root_path or project.root_path)
            ),
            "monitoring_mode": project.monitoring_mode,
            "monitoring_status": project.monitoring_status,
            "last_scan_status": project.last_scan_status,
            "last_scan_at": project.last_scan_at.isoformat() if project.last_scan_at else None,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "languages": detection.get("languages", []),
            "frameworks": detection.get("frameworks", []),
            "tests": detection.get("tests", []),
            "runtime_hints": detection.get("runtime_hints", []),
            "git": self._git_dict(latest_git),
            "scan": self._scan_dict(latest_scan),
            "source_remains_local": True,
        }

    def list(self) -> list[dict[str, Any]]:
        with self.sessions() as session:
            projects = session.scalars(
                select(Project)
                .where(Project.archived_at.is_(None))
                .order_by(Project.updated_at.desc())
            ).all()
            return [self.serialize(session, project) for project in projects]

    def get(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            project = session.get(Project, project_id)
            if project is None or project.archived_at is not None:
                raise ProjectError("PROJECT_NOT_FOUND")
            return self.serialize(session, project)

    def git(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            if session.get(Project, project_id) is None:
                raise ProjectError("PROJECT_NOT_FOUND")
            return self._git_dict(self._latest_git(session, project_id))

    def scan(self, project_id: str) -> dict[str, Any] | None:
        with self.sessions() as session:
            if session.get(Project, project_id) is None:
                raise ProjectError("PROJECT_NOT_FOUND")
            return self._scan_dict(self._latest_scan(session, project_id))

    def changes(self, project_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ProjectChangeObservation)
                .where(ProjectChangeObservation.project_id == project_id)
                .order_by(ProjectChangeObservation.observed_at.desc())
                .limit(min(limit, 100))
            ).all()
            return [
                {
                    "id": row.id,
                    "observed_at": row.observed_at.isoformat(),
                    "worktree_fingerprint": row.worktree_fingerprint,
                    "changed_paths": json.loads(row.changed_paths_json),
                }
                for row in rows
            ]

    def impact_summary(self, project_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            files = session.scalars(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id, ProjectFile.deleted_at.is_(None)
                )
            ).all()
            if session.get(Project, project_id) is None:
                raise ProjectError("PROJECT_NOT_FOUND")
            relationships = (
                session.scalar(
                    select(func.count(ImpactEdge.id)).where(
                        ImpactEdge.project_id == project_id, ImpactEdge.stale.is_(False)
                    )
                )
                or 0
            )
            unknown = (
                session.scalar(
                    select(func.count(ImpactNode.id)).where(
                        ImpactNode.project_id == project_id,
                        ImpactNode.node_type == "UNKNOWN_REFERENCE",
                        ImpactNode.stale.is_(False),
                    )
                )
                or 0
            )
            languages = Counter(item.language for item in files if item.language != "Unknown")
            return {
                "files_indexed": sum(
                    item.indexing_mode in {"indexed", "hashed_only"} for item in files
                ),
                "languages": len(languages),
                "language_counts": dict(languages),
                "direct_relationships": int(relationships),
                "tests_found": sum(item.is_test for item in files),
                "sensitive_files": sum(item.is_sensitive for item in files),
                "unknown_references": int(unknown),
                "unsupported_files": sum(
                    item.indexing_mode == "hashed_only"
                    and item.language not in {"JSON", "Markdown"}
                    for item in files
                ),
                "stale_relationships": int(
                    session.scalar(
                        select(func.count(ImpactEdge.id)).where(
                            ImpactEdge.project_id == project_id, ImpactEdge.stale.is_(True)
                        )
                    )
                    or 0
                ),
            }

    def impact_search(self, project_id: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
        term = query.strip()
        with self.sessions() as session:
            nodes = session.scalars(
                select(ImpactNode)
                .where(
                    ImpactNode.project_id == project_id,
                    ImpactNode.stale.is_(False),
                    or_(
                        ImpactNode.label.ilike(f"%{term}%"),
                        ImpactNode.stable_key.ilike(f"%{term}%"),
                    ),
                )
                .limit(min(limit, 100))
            ).all()
            results: list[dict[str, Any]] = []
            for node in nodes:
                outgoing = session.execute(
                    select(ImpactEdge, ImpactNode)
                    .join(ImpactNode, ImpactNode.id == ImpactEdge.target_node_id)
                    .where(ImpactEdge.source_node_id == node.id, ImpactEdge.stale.is_(False))
                    .limit(20)
                ).all()
                results.append(
                    {
                        "node": {
                            "type": node.node_type,
                            "label": node.label,
                            "relative_path": node.relative_path,
                        },
                        "relationships": [
                            {
                                "type": edge.edge_type,
                                "target_type": target.node_type,
                                "target": target.label,
                                "target_path": target.relative_path,
                                "provenance": edge.provenance,
                                "parser_adapter": edge.parser_adapter,
                            }
                            for edge, target in outgoing
                        ],
                    }
                )
            return results

    def findings(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ScanFinding)
                .where(ScanFinding.project_id == project_id)
                .order_by(ScanFinding.created_at.desc())
                .limit(min(limit, 200))
            ).all()
            return [
                {
                    "severity": row.severity,
                    "code": row.code,
                    "relative_path": row.relative_path,
                    "message": row.message,
                }
                for row in rows
            ]

    def set_monitoring(self, project_id: str, active: bool) -> dict[str, Any]:
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ProjectError("PROJECT_NOT_FOUND")
            project.monitoring_mode = "passive" if active else "paused"
            project.monitoring_status = "active" if active else "paused"
            project.updated_at = datetime.now(UTC)
        self.events.publish("monitoring_resumed" if active else "monitoring_paused", project_id, {})
        return {"monitoring_status": "active" if active else "paused"}

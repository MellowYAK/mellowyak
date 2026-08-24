from __future__ import annotations

import hashlib
import posixpath
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    ImpactEdge,
    ImpactNode,
    Project,
    ProjectFile,
    ProjectScanRun,
    ScanFinding,
)
from mellowyak_engine.scanning.adapters import ParseResult, adapter_for
from mellowyak_engine.scanning.policy import (
    EXCLUDED_EXTENSIONS,
    MAX_INDEXED_FILE_SIZE,
    MAX_PARSER_PAYLOAD,
    SCAN_PROGRESS_EVERY_FILES,
    Candidate,
    is_generated_path,
    is_sensitive_path,
    is_test_path,
    iter_candidates,
    language_for,
)

SCAN_VERSION = "source-scan-v1"


class ScanCancelled(Exception):
    pass


class SourceScanner:
    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    def _finding(
        self,
        session: Session,
        project_id: str,
        scan_id: str,
        code: str,
        message: str,
        relative_path: str | None = None,
        severity: str = "warning",
    ) -> None:
        session.add(
            ScanFinding(
                id=str(uuid.uuid4()),
                project_id=project_id,
                scan_id=scan_id,
                severity=severity,
                code=code,
                relative_path=relative_path,
                message=message,
                created_at=datetime.now(UTC),
            )
        )

    def _upsert_file(
        self,
        session: Session,
        project_id: str,
        scan_id: str,
        candidate: Candidate,
        *,
        language: str,
        size: int,
        digest: str | None,
        binary: bool,
        sensitive: bool,
        indexing_mode: str,
        parser_adapter: str | None,
    ) -> ProjectFile:
        normalized = candidate.relative_path.casefold()
        row = session.scalars(
            select(ProjectFile).where(
                ProjectFile.project_id == project_id,
                ProjectFile.normalized_path == normalized,
            )
        ).first()
        values = {
            "relative_path": candidate.relative_path,
            "language": language,
            "size_bytes": size,
            "content_sha256": digest,
            "is_test": is_test_path(candidate.relative_path),
            "is_generated": is_generated_path(candidate.relative_path),
            "is_binary": binary,
            "is_sensitive": sensitive,
            "indexing_mode": indexing_mode,
            "parser_adapter": parser_adapter,
            "last_seen_scan_id": scan_id,
            "deleted_at": None,
        }
        if row is None:
            row = ProjectFile(
                id=str(uuid.uuid4()),
                project_id=project_id,
                normalized_path=normalized,
                **values,
            )
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        session.flush()
        return row

    def _upsert_node(
        self,
        session: Session,
        project_id: str,
        scan_id: str,
        node_type: str,
        stable_key: str,
        label: str,
        relative_path: str | None,
    ) -> ImpactNode:
        node = session.scalars(
            select(ImpactNode).where(
                ImpactNode.project_id == project_id,
                ImpactNode.node_type == node_type,
                ImpactNode.stable_key == stable_key,
            )
        ).first()
        if node is None:
            node = ImpactNode(
                id=str(uuid.uuid4()),
                project_id=project_id,
                node_type=node_type,
                stable_key=stable_key,
                label=label,
                relative_path=relative_path,
                last_seen_scan_id=scan_id,
                stale=False,
            )
            session.add(node)
        else:
            node.label = label
            node.relative_path = relative_path
            node.last_seen_scan_id = scan_id
            node.stale = False
        session.flush()
        return node

    def _upsert_edge(
        self,
        session: Session,
        project_id: str,
        scan_id: str,
        source: ImpactNode,
        target: ImpactNode,
        edge_type: str,
        provenance: str,
        adapter: str,
    ) -> None:
        now = datetime.now(UTC)
        edge = session.scalars(
            select(ImpactEdge).where(
                ImpactEdge.project_id == project_id,
                ImpactEdge.source_node_id == source.id,
                ImpactEdge.target_node_id == target.id,
                ImpactEdge.edge_type == edge_type,
            )
        ).first()
        if edge is None:
            session.add(
                ImpactEdge(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=edge_type,
                    provenance=provenance,
                    confidence_class=provenance,
                    parser_adapter=adapter,
                    source_scan_revision=scan_id,
                    first_observed_at=now,
                    last_observed_at=now,
                    stale=False,
                )
            )
        else:
            edge.provenance = provenance
            edge.confidence_class = provenance
            edge.parser_adapter = adapter
            edge.source_scan_revision = scan_id
            edge.last_observed_at = now
            edge.stale = False

    @staticmethod
    def _resolve_reference(
        source: str, reference: str, paths: set[str], language: str
    ) -> str | None:
        source_parent = Path(source).parent
        candidates: list[Path] = []
        if language == "Python":
            if reference.startswith("."):
                levels = len(reference) - len(reference.lstrip("."))
                base = source_parent
                for _ in range(max(0, levels - 1)):
                    base = base.parent
                module = reference.lstrip(".").replace(".", "/")
                candidates.extend((base / f"{module}.py", base / module / "__init__.py"))
            else:
                module = reference.replace(".", "/")
                candidates.extend((Path(f"{module}.py"), Path(module) / "__init__.py"))
        elif reference.startswith("."):
            base = source_parent / reference
            candidates.append(base)
            candidates.extend(
                Path(f"{base}{suffix}") for suffix in (".ts", ".tsx", ".js", ".jsx", ".php")
            )
            candidates.extend(base / f"index{suffix}" for suffix in (".ts", ".tsx", ".js", ".jsx"))
        for candidate in candidates:
            normalized = posixpath.normpath(candidate.as_posix()).removeprefix("./")
            if normalized in paths:
                return normalized
        return None

    def _persist_graph(
        self,
        session: Session,
        project: Project,
        scan_id: str,
        parsed: dict[str, ParseResult],
        current_paths: set[str],
        full_scan: bool,
    ) -> tuple[int, int]:
        if full_scan:
            session.execute(
                update(ImpactNode).where(ImpactNode.project_id == project.id).values(stale=True)
            )
            session.execute(
                update(ImpactEdge).where(ImpactEdge.project_id == project.id).values(stale=True)
            )
        else:
            changed = tuple(parsed)
            if changed:
                changed_nodes = session.scalars(
                    select(ImpactNode.id).where(
                        ImpactNode.project_id == project.id,
                        ImpactNode.relative_path.in_(changed),
                    )
                ).all()
                if changed_nodes:
                    session.execute(
                        update(ImpactNode)
                        .where(ImpactNode.id.in_(changed_nodes))
                        .values(stale=True)
                    )
                    session.execute(
                        update(ImpactEdge)
                        .where(ImpactEdge.source_node_id.in_(changed_nodes))
                        .values(stale=True)
                    )

        project_node = self._upsert_node(
            session, project.id, scan_id, "PROJECT", "project", project.display_name, None
        )
        file_nodes: dict[str, ImpactNode] = {}
        for relative in sorted(current_paths):
            file_row = session.scalars(
                select(ProjectFile).where(
                    ProjectFile.project_id == project.id,
                    ProjectFile.relative_path == relative,
                    ProjectFile.deleted_at.is_(None),
                )
            ).first()
            node_type = "TEST" if file_row and file_row.is_test else "FILE"
            file_node = self._upsert_node(
                session, project.id, scan_id, node_type, relative, Path(relative).name, relative
            )
            file_nodes[relative] = file_node
            self._upsert_edge(
                session,
                project.id,
                scan_id,
                project_node,
                file_node,
                "CONTAINS",
                "STATIC_EXACT",
                "filesystem-inventory-v1",
            )

        unknown_count = 0
        for relative, result in parsed.items():
            source = file_nodes.get(relative)
            if source is None:
                continue
            for declaration in result.declarations:
                symbol = self._upsert_node(
                    session,
                    project.id,
                    scan_id,
                    declaration.node_type,
                    f"{relative}#{declaration.name}",
                    declaration.name,
                    relative,
                )
                self._upsert_edge(
                    session,
                    project.id,
                    scan_id,
                    source,
                    symbol,
                    "DECLARES",
                    result.provenance,
                    result.adapter,
                )
            file_row = session.scalars(
                select(ProjectFile).where(
                    ProjectFile.project_id == project.id,
                    ProjectFile.relative_path == relative,
                )
            ).one()
            for reference in result.references:
                resolved = self._resolve_reference(
                    relative, reference.value, current_paths, file_row.language
                )
                if resolved and resolved in file_nodes:
                    target = file_nodes[resolved]
                    edge_type = reference.relation
                else:
                    unknown_count += 1
                    target = self._upsert_node(
                        session,
                        project.id,
                        scan_id,
                        "UNKNOWN_REFERENCE",
                        f"{relative}?{reference.value}",
                        reference.value,
                        relative,
                    )
                    edge_type = "UNKNOWN_RELATION"
                self._upsert_edge(
                    session,
                    project.id,
                    scan_id,
                    source,
                    target,
                    edge_type,
                    result.provenance,
                    result.adapter,
                )
        session.flush()
        relationships = (
            session.scalar(
                select(func.count(ImpactEdge.id)).where(
                    ImpactEdge.project_id == project.id, ImpactEdge.stale.is_(False)
                )
            )
            or 0
        )
        return int(relationships), unknown_count

    def run(
        self,
        project_id: str,
        cancel: threading.Event,
        changed_paths: set[str] | None = None,
    ) -> str:
        started = time.monotonic()
        scan_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None or not project.canonical_root_path:
                raise KeyError("PROJECT_NOT_FOUND")
            root = Path(project.repository_root_path or project.canonical_root_path)
            if not root.is_dir():
                raise FileNotFoundError("PROJECT_ROOT_UNAVAILABLE")
            candidates, ignored_count = iter_candidates(root)
            if changed_paths is not None:
                normalized_changes = {Path(item).as_posix().lstrip("./") for item in changed_paths}
                candidates = [
                    item for item in candidates if item.relative_path in normalized_changes
                ]
            run = ProjectScanRun(
                id=scan_id,
                project_id=project_id,
                scan_version=SCAN_VERSION,
                status="running",
                started_at=datetime.now(UTC),
                total_candidates=len(candidates),
            )
            session.add(run)
            project.active_scan_id = scan_id
            project.last_scan_status = "running"
        self.events.publish(
            "scan_progress",
            project_id,
            {"scan_id": scan_id, "processed": 0, "total": len(candidates)},
        )

        parsed: dict[str, ParseResult] = {}
        counters = {
            "included_files": 0,
            "excluded_files": ignored_count,
            "binary_files": 0,
            "sensitive_files": 0,
            "failed_files": 0,
            "unsupported_files": 0,
            "test_files": 0,
        }
        try:
            for number, candidate in enumerate(candidates, start=1):
                if cancel.is_set():
                    raise ScanCancelled
                with self.sessions.begin() as session:
                    try:
                        if candidate.symlink_outside:
                            counters["excluded_files"] += 1
                            self._finding(
                                session,
                                project_id,
                                scan_id,
                                "SYMLINK_OUTSIDE_ROOT",
                                "Symlink target is outside the selected project root.",
                                candidate.relative_path,
                            )
                            continue
                        stat = candidate.absolute_path.stat(follow_symlinks=False)
                        size = stat.st_size
                        language = language_for(candidate.absolute_path)
                        sensitive = is_sensitive_path(candidate.relative_path)
                        generated = is_generated_path(candidate.relative_path)
                        if sensitive:
                            counters["sensitive_files"] += 1
                            counters["excluded_files"] += 1
                            self._upsert_file(
                                session,
                                project_id,
                                scan_id,
                                candidate,
                                language=language,
                                size=size,
                                digest=None,
                                binary=False,
                                sensitive=True,
                                indexing_mode="metadata_only_sensitive",
                                parser_adapter=None,
                            )
                            continue
                        if size > MAX_INDEXED_FILE_SIZE:
                            counters["excluded_files"] += 1
                            self._upsert_file(
                                session,
                                project_id,
                                scan_id,
                                candidate,
                                language=language,
                                size=size,
                                digest=None,
                                binary=False,
                                sensitive=False,
                                indexing_mode="excluded_oversized",
                                parser_adapter=None,
                            )
                            self._finding(
                                session,
                                project_id,
                                scan_id,
                                "OVERSIZED_FILE",
                                "File exceeds the bounded source indexing limit.",
                                candidate.relative_path,
                            )
                            continue
                        if (
                            candidate.absolute_path.suffix.lower() in EXCLUDED_EXTENSIONS
                            or generated
                        ):
                            counters["excluded_files"] += 1
                            self._upsert_file(
                                session,
                                project_id,
                                scan_id,
                                candidate,
                                language=language,
                                size=size,
                                digest=None,
                                binary=True,
                                sensitive=False,
                                indexing_mode="excluded_artifact",
                                parser_adapter=None,
                            )
                            continue
                        content = candidate.absolute_path.read_bytes()
                        binary = b"\0" in content[:8192]
                        if binary:
                            counters["binary_files"] += 1
                            counters["excluded_files"] += 1
                            self._upsert_file(
                                session,
                                project_id,
                                scan_id,
                                candidate,
                                language=language,
                                size=size,
                                digest=hashlib.sha256(content).hexdigest(),
                                binary=True,
                                sensitive=False,
                                indexing_mode="metadata_only_binary",
                                parser_adapter=None,
                            )
                            continue
                        digest = hashlib.sha256(content).hexdigest()
                        adapter = adapter_for(language)
                        parser_name = None
                        if adapter is not None and len(content) <= MAX_PARSER_PAYLOAD:
                            result = adapter.parse(content.decode("utf-8", errors="replace"))
                            parsed[candidate.relative_path] = result
                            parser_name = result.adapter
                            for warning in result.warnings:
                                self._finding(
                                    session,
                                    project_id,
                                    scan_id,
                                    "PARSER_WARNING",
                                    f"Parser reported {warning}.",
                                    candidate.relative_path,
                                )
                        elif language not in {"JSON", "Markdown", "YAML", "TOML"}:
                            counters["unsupported_files"] += 1
                        counters["included_files"] += 1
                        if is_test_path(candidate.relative_path):
                            counters["test_files"] += 1
                        self._upsert_file(
                            session,
                            project_id,
                            scan_id,
                            candidate,
                            language=language,
                            size=size,
                            digest=digest,
                            binary=False,
                            sensitive=False,
                            indexing_mode="indexed" if adapter else "hashed_only",
                            parser_adapter=parser_name,
                        )
                    except (OSError, PermissionError) as error:
                        counters["failed_files"] += 1
                        self._finding(
                            session,
                            project_id,
                            scan_id,
                            "FILE_READ_FAILED",
                            type(error).__name__,
                            candidate.relative_path,
                            "error",
                        )
                    finally:
                        run = session.get(ProjectScanRun, scan_id)
                        if run:
                            run.processed_files = number
                            for key, value in counters.items():
                                setattr(run, key, value)
                if number % SCAN_PROGRESS_EVERY_FILES == 0 or number == len(candidates):
                    self.events.publish(
                        "scan_progress",
                        project_id,
                        {"scan_id": scan_id, "processed": number, "total": len(candidates)},
                    )

            with self.sessions.begin() as session:
                project = session.get(Project, project_id)
                if project is None:
                    raise KeyError("PROJECT_NOT_FOUND")
                full_scan = changed_paths is None
                if full_scan:
                    session.execute(
                        update(ProjectFile)
                        .where(
                            ProjectFile.project_id == project_id,
                            ProjectFile.last_seen_scan_id != scan_id,
                            ProjectFile.deleted_at.is_(None),
                        )
                        .values(deleted_at=datetime.now(UTC))
                    )
                current_paths = set(
                    session.scalars(
                        select(ProjectFile.relative_path).where(
                            ProjectFile.project_id == project_id,
                            ProjectFile.deleted_at.is_(None),
                            ProjectFile.indexing_mode.in_(("indexed", "hashed_only")),
                        )
                    ).all()
                )
                relationships, unknown_count = self._persist_graph(
                    session, project, scan_id, parsed, current_paths, full_scan
                )
                run = session.get(ProjectScanRun, scan_id)
                if run is None:
                    raise RuntimeError("SCAN_RUN_MISSING")
                run.status = "completed"
                run.completed_at = datetime.now(UTC)
                run.relationship_count = relationships
                run.unknown_items = unknown_count
                run.duration_seconds = round(time.monotonic() - started, 4)
                project.active_scan_id = None
                project.last_scan_status = (
                    "ready_with_limits"
                    if unknown_count or counters["unsupported_files"] or counters["failed_files"]
                    else "ready"
                )
                project.last_scan_at = run.completed_at
                project.updated_at = run.completed_at
            self.events.publish(
                "scan_completion",
                project_id,
                {"scan_id": scan_id, "status": "completed"},
            )
        except ScanCancelled:
            with self.sessions.begin() as session:
                run = session.get(ProjectScanRun, scan_id)
                project = session.get(Project, project_id)
                if run:
                    run.status = "cancelled"
                    run.completed_at = datetime.now(UTC)
                    run.duration_seconds = round(time.monotonic() - started, 4)
                if project:
                    project.active_scan_id = None
                    project.last_scan_status = "scan_incomplete"
            self.events.publish(
                "scan_failure", project_id, {"scan_id": scan_id, "code": "CANCELLED"}
            )
        except Exception as error:
            with self.sessions.begin() as session:
                run = session.get(ProjectScanRun, scan_id)
                project = session.get(Project, project_id)
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now(UTC)
                    run.error_summary = type(error).__name__
                    run.duration_seconds = round(time.monotonic() - started, 4)
                if project:
                    project.active_scan_id = None
                    project.last_scan_status = "scan_incomplete"
            self.events.publish(
                "scan_failure", project_id, {"scan_id": scan_id, "code": type(error).__name__}
            )
        return scan_id


class ScanCoordinator:
    def __init__(self, scanner: SourceScanner) -> None:
        self.scanner = scanner
        self._jobs: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.Lock()

    def start(self, project_id: str, changed_paths: set[str] | None = None) -> str:
        with self._lock:
            existing = self._jobs.get(project_id)
            if existing and existing[0].is_alive():
                raise RuntimeError("SCAN_ALREADY_RUNNING")
            cancel = threading.Event()
            started = threading.Event()
            result: list[str] = []

            def execute() -> None:
                started.set()
                result.append(self.scanner.run(project_id, cancel, changed_paths))

            thread = threading.Thread(
                target=execute, name=f"mellowyak-scan-{project_id[:8]}", daemon=True
            )
            self._jobs[project_id] = (thread, cancel)
            thread.start()
        started.wait(timeout=1)
        return "started"

    def cancel(self, project_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(project_id)
            if not job or not job[0].is_alive():
                return False
            job[1].set()
            return True

    def stop_all(self) -> None:
        with self._lock:
            jobs = list(self._jobs.values())
        for _, cancel in jobs:
            cancel.set()
        for thread, _ in jobs:
            thread.join(timeout=5)

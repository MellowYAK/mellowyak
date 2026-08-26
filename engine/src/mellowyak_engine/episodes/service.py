from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import Project, SignalClassification, SourceEpisode, SourceSnapshot

SETTLE_SECONDS = 2.0
MAX_EPISODE_SECONDS = 60.0
MAX_EPISODE_PATHS = 5_000
DEPENDENCY_FILES = frozenset(
    {
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "uv.lock",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "composer.json",
        "composer.lock",
        "Gemfile",
        "Gemfile.lock",
        "pom.xml",
        "build.gradle",
    }
)


@dataclass
class _ActiveEpisode:
    episode_id: str
    opened_monotonic: float
    paths: set[str] = field(default_factory=set)
    event_count: int = 0
    timer: threading.Timer | None = None


SnapshotCallback = Callable[[str, str | None, str], dict[str, Any]]
SelectionCallback = Callable[[str, str], dict[str, Any]]


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EpisodeService:
    """Coalesces watcher hints; failures never propagate back to an editor thread."""

    def __init__(self, sessions: sessionmaker[Session], events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events
        self._active: dict[str, _ActiveEpisode] = {}
        self._lock = threading.RLock()
        self._snapshot_callback: SnapshotCallback | None = None
        self._selection_callback: SelectionCallback | None = None

    def bind_snapshot_callback(self, callback: SnapshotCallback) -> None:
        self._snapshot_callback = callback

    def bind_selection_callback(self, callback: SelectionCallback) -> None:
        self._selection_callback = callback

    def record(self, project_id: str, relative_paths: list[str]) -> str | None:
        normalized = {
            Path(path).as_posix().lstrip("/")
            for path in relative_paths
            if path and "\x00" not in path and not path.startswith("../")
        }
        if not normalized:
            return None
        import time

        now_mono = time.monotonic()
        with self._lock:
            active = self._active.get(project_id)
            if active is None or now_mono - active.opened_monotonic >= MAX_EPISODE_SECONDS:
                if active is not None:
                    self._stabilize_locked(project_id, active)
                active = self._open(project_id, now_mono)
            active.event_count += len(normalized)
            remaining = max(0, MAX_EPISODE_PATHS - len(active.paths))
            active.paths.update(sorted(normalized)[:remaining])
            if active.timer:
                active.timer.cancel()
            active.timer = threading.Timer(SETTLE_SECONDS, self._stabilize_safe, args=(project_id,))
            active.timer.daemon = True
            active.timer.start()
            self.events.publish(
                "episode_settling",
                project_id,
                {
                    "episode_id": active.episode_id,
                    "settle_seconds": SETTLE_SECONDS,
                    "changed_path_count": len(active.paths),
                },
            )
            return active.episode_id

    def _open(self, project_id: str, now_mono: float) -> _ActiveEpisode:
        episode_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise ValueError("PROJECT_NOT_FOUND")
            previous = session.scalars(
                select(SourceSnapshot)
                .where(SourceSnapshot.project_id == project_id)
                .order_by(SourceSnapshot.created_at.desc())
                .limit(1)
            ).first()
            session.add(
                SourceEpisode(
                    id=episode_id,
                    project_id=project_id,
                    started_at=datetime.now(UTC),
                    event_count=0,
                    base_snapshot_id=previous.id if previous else None,
                    git_anchor_json=_json(
                        {
                            "branch": project.current_branch,
                            "head_sha": project.current_head_sha,
                            "worktree_fingerprint": project.current_worktree_fingerprint,
                        }
                        if project.current_head_sha
                        else {}
                    ),
                    status="OPEN",
                )
            )
        active = _ActiveEpisode(episode_id=episode_id, opened_monotonic=now_mono)
        self._active[project_id] = active
        self.events.publish("episode_opened", project_id, {"episode_id": episode_id})
        return active

    def _stabilize_safe(self, project_id: str) -> None:
        try:
            self.stabilize_now(project_id)
        except Exception as error:
            self.events.publish(
                "snapshot_failed",
                project_id,
                {"error_code": type(error).__name__[:80]},
            )

    def stabilize_now(self, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            active = self._active.pop(project_id, None)
            if active is None:
                return None
            return self._stabilize_locked(project_id, active)

    def _stabilize_locked(self, project_id: str, active: _ActiveEpisode) -> dict[str, Any] | None:
        if active.timer:
            active.timer.cancel()
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            episode = session.get(SourceEpisode, active.episode_id)
            if project is None or episode is None:
                return None
            root = Path(project.canonical_root_path or project.root_path).resolve(strict=False)
            added: list[str] = []
            modified: list[str] = []
            deleted: list[str] = []
            for relative in sorted(active.paths):
                candidate = (root / relative).resolve(strict=False)
                try:
                    candidate.relative_to(root)
                except ValueError:
                    continue
                if not candidate.exists():
                    deleted.append(relative)
                else:
                    modified.append(relative)
            dependency = sorted(
                relative for relative in active.paths if Path(relative).name in DEPENDENCY_FILES
            )
            episode.event_count = active.event_count
            episode.added_paths_json = _json(added)
            episode.modified_paths_json = _json(modified)
            episode.deleted_paths_json = _json(deleted)
            episode.dependency_changes_json = _json(dependency)
            episode.ended_at = datetime.now(UTC)
            episode.status = "STABILIZING"
            base_snapshot_id = episode.base_snapshot_id
        snapshot: dict[str, Any] | None = None
        error_code: str | None = None
        if self._snapshot_callback is not None:
            try:
                snapshot = self._snapshot_callback(project_id, active.episode_id, "EPISODE")
            except Exception as error:
                error_code = type(error).__name__[:120]
        with self.sessions.begin() as session:
            episode = session.get(SourceEpisode, active.episode_id)
            if episode is None:
                return None
            episode.resulting_snapshot_id = str(snapshot["id"]) if snapshot else base_snapshot_id
            episode.status = "STABILIZED" if snapshot else "FAILED"
            episode.error_code = error_code
            signal = SignalClassification(
                id=str(uuid.uuid4()),
                project_id=project_id,
                episode_id=episode.id,
                snapshot_id=episode.resulting_snapshot_id,
                state="WATCH",
                reason_codes_json=_json(["SOURCE_FILES_CHANGED"]),
                evidence_json=_json(
                    {"event_count": active.event_count, "changed_path_count": len(active.paths)}
                ),
                friendly_key="signal.watch.fileChange",
                technical_json=_json(
                    {"paths": sorted(active.paths), "snapshot_created": bool(snapshot)}
                ),
                created_at=datetime.now(UTC),
            )
            session.add(signal)
            response = self._serialize(episode)
        self.events.publish(
            "episode_stabilized",
            project_id,
            {
                "episode_id": active.episode_id,
                "snapshot_id": response["resulting_snapshot_id"],
            },
        )
        self.events.publish("signal_classified", project_id, {"state": "WATCH"})
        if self._selection_callback is not None and snapshot is not None:
            try:
                selection = self._selection_callback(project_id, active.episode_id)
                self.events.publish(
                    "probe_selection_completed",
                    project_id,
                    {
                        "episode_id": active.episode_id,
                        "selected_count": selection["selected_count"],
                        "truncated": selection["truncated"],
                    },
                )
            except Exception as error:
                self.events.publish(
                    "probe_selection_failed",
                    project_id,
                    {
                        "episode_id": active.episode_id,
                        "error_code": type(error).__name__[:80],
                    },
                )
        return response

    def recover(self) -> int:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(SourceEpisode).where(SourceEpisode.status.in_(["OPEN", "STABILIZING"]))
            ).all()
            for row in rows:
                row.status = "FAILED"
                row.error_code = "ENGINE_RESTART_DURING_EPISODE"
                row.ended_at = now
            return len(rows)

    @staticmethod
    def _serialize(row: SourceEpisode) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "started_at": row.started_at.isoformat(),
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
            "event_count": row.event_count,
            "added_paths": json.loads(row.added_paths_json),
            "modified_paths": json.loads(row.modified_paths_json),
            "deleted_paths": json.loads(row.deleted_paths_json),
            "renamed_paths": json.loads(row.renamed_paths_json),
            "dependency_changes": json.loads(row.dependency_changes_json),
            "runtime_events": json.loads(row.runtime_events_json),
            "base_snapshot_id": row.base_snapshot_id,
            "resulting_snapshot_id": row.resulting_snapshot_id,
            "git_anchor": json.loads(row.git_anchor_json),
            "status": row.status,
            "error_code": row.error_code,
        }

    def list(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.scalars(
                select(SourceEpisode)
                .where(SourceEpisode.project_id == project_id)
                .order_by(SourceEpisode.started_at.desc())
                .limit(min(max(limit, 1), 200))
            ).all()
            return [self._serialize(row) for row in rows]

    def get(self, project_id: str, episode_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(SourceEpisode, episode_id)
            if row is None or row.project_id != project_id:
                raise ValueError("EPISODE_NOT_FOUND")
            return self._serialize(row)

    def stop_all(self) -> None:
        with self._lock:
            project_ids = list(self._active)
        for project_id in project_ids:
            self._stabilize_safe(project_id)

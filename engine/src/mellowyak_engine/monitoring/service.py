from __future__ import annotations

import threading
import time
from pathlib import Path

from watchfiles import watch

from mellowyak_engine.projects.service import ProjectError, ProjectService
from mellowyak_engine.scanning.policy import (
    DEFAULT_EXCLUDED_DIRS,
    WATCHER_DEBOUNCE_MS,
    build_ignore_spec,
)
from mellowyak_engine.scanning.service import ScanCoordinator

if False:  # pragma: no cover - import cycle guard for type checkers
    from mellowyak_engine.episodes.service import EpisodeService


class MonitoringService:
    def __init__(
        self,
        projects: ProjectService,
        scans: ScanCoordinator,
        episodes: EpisodeService | None = None,
    ) -> None:
        self.projects = projects
        self.scans = scans
        self.episodes = episodes
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.Lock()

    def _allowed_filter(self, root: Path):
        ignore = build_ignore_spec(root)

        def allowed(_change: object, raw_path: str) -> bool:
            path = Path(raw_path)
            try:
                relative = path.resolve(strict=False).relative_to(root).as_posix()
            except ValueError:
                return False
            if any(segment in DEFAULT_EXCLUDED_DIRS for segment in Path(relative).parts):
                return False
            return not ignore.match_file(relative)

        return allowed

    def _process(self, project_id: str, root: Path, raw_paths: set[str]) -> None:
        relative_paths: set[str] = set()
        for raw in raw_paths:
            try:
                relative_paths.add(Path(raw).resolve(strict=False).relative_to(root).as_posix())
            except ValueError:
                continue
        if not relative_paths:
            return
        try:
            self.projects.refresh_git(project_id, sorted(relative_paths))
            if self.episodes is not None:
                self.episodes.record(project_id, sorted(relative_paths))
            self.scans.start(project_id)
        except (ProjectError, RuntimeError, OSError):
            return

    def _watch(self, project_id: str, root: Path, stop: threading.Event) -> None:
        try:
            for changes in watch(
                root,
                watch_filter=self._allowed_filter(root),
                debounce=WATCHER_DEBOUNCE_MS,
                step=100,
                stop_event=stop,
                rust_timeout=1000,
                yield_on_timeout=False,
                recursive=True,
                ignore_permission_denied=True,
            ):
                self._process(project_id, root, {path for _, path in changes})
        except Exception:
            self._poll(project_id, stop)

    def _poll(self, project_id: str, stop: threading.Event) -> None:
        previous = ""
        while not stop.wait(2.0):
            try:
                state = self.projects.refresh_git(project_id)
            except (ProjectError, OSError):
                continue
            current = str(state["worktree_fingerprint"])
            if previous and current != previous:
                if self.episodes is not None:
                    self.episodes.record(project_id, ["."])
                try:
                    self.scans.start(project_id)
                except RuntimeError:
                    pass
            previous = current
            time.sleep(0)

    def start(self, project_id: str) -> bool:
        project = self.projects.get_model(project_id)
        if project.monitoring_mode != "passive" or not project.canonical_root_path:
            return False
        root = Path(project.repository_root_path or project.canonical_root_path).resolve(
            strict=False
        )
        if not root.is_dir():
            return False
        with self._lock:
            existing = self._workers.get(project_id)
            if existing and existing[0].is_alive():
                return True
            stop = threading.Event()
            thread = threading.Thread(
                target=self._watch,
                args=(project_id, root, stop),
                name=f"mellowyak-watch-{project_id[:8]}",
                daemon=True,
            )
            self._workers[project_id] = (thread, stop)
            thread.start()
            return True

    def pause(self, project_id: str) -> None:
        with self._lock:
            worker = self._workers.pop(project_id, None)
        if worker:
            worker[1].set()
            worker[0].join(timeout=5)

    def resume(self, project_id: str) -> bool:
        return self.start(project_id)

    def start_persisted(self) -> None:
        for project in self.projects.list():
            if project["monitoring_mode"] == "passive":
                self.start(str(project["id"]))

    def stop_all(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for _, stop in workers:
            stop.set()
        for thread, _ in workers:
            thread.join(timeout=5)

    def running(self, project_id: str) -> bool:
        with self._lock:
            worker = self._workers.get(project_id)
            return bool(worker and worker[0].is_alive())

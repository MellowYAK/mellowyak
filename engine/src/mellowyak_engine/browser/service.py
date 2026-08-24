from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.behaviors.service import BehaviorServiceError, validate_loopback_runtime_url
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorLink,
    BrowserCaptureSession,
    BrowserCaptureStep,
    Project,
    ProtectedBehavior,
    RuntimeConfiguration,
    RuntimeObservation,
)
from mellowyak_engine.evidence.service import EvidenceService, EvidenceServiceError

ACTIVE_CAPTURE_STATES = {"STARTING", "RECORDING", "STOPPING"}
TERMINAL_CAPTURE_STATES = {
    "REVIEW_REQUIRED",
    "ACCEPTED",
    "CANCELLED",
    "FAILED",
    "STALE_SOURCE",
}
MAX_CAPTURE_STEPS = 500
MAX_RUNTIME_OBSERVATIONS = 1000
MAX_SCREENSHOTS = 30
MAX_CAPTURE_DURATION_SECONDS = 10 * 60
BROWSER_STARTUP_TIMEOUT_SECONDS = 30
EVENT_COALESCE_WINDOW_SECONDS = 0.15


class BrowserCaptureError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


def _safe_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _source_revision(project: Project) -> dict[str, Any]:
    return {
        "branch": project.current_branch,
        "head_sha": project.current_head_sha,
        "worktree_fingerprint": project.current_worktree_fingerprint,
    }


def _browser_executable() -> str | None:
    override = os.environ.get("MELLOWYAK_BROWSER_EXECUTABLE", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    executable = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        resources = executable.parent.parent / "Resources" / "browser"
        manifest_path = resources / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                relative = Path(str(manifest.get("executable_relative", "")))
                candidate = (resources / relative).resolve()
                if candidate.is_relative_to(resources.resolve()):
                    candidates.append(candidate)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        candidates.extend(
            [
                resources
                / "chrome-mac-arm64"
                / "Google Chrome for Testing.app"
                / "Contents"
                / "MacOS"
                / "Google Chrome for Testing",
                resources
                / "chrome-mac"
                / "Google Chrome for Testing.app"
                / "Contents"
                / "MacOS"
                / "Google Chrome for Testing",
                resources / "chrome-linux" / "chrome",
                resources / "chrome-win64" / "chrome.exe",
            ]
        )
    candidates.extend(
        [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/chromium"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


@dataclass
class _WorkerRequest:
    action: str
    capture_id: str
    payload: dict[str, Any]
    result: queue.Queue[tuple[bool, Any]]


class _BrowserWorker:
    def __init__(self) -> None:
        self.requests: queue.Queue[_WorkerRequest | None] = queue.Queue()
        self.thread: threading.Thread | None = None
        self._start_lock = threading.Lock()

    def _ensure_started(self) -> None:
        with self._start_lock:
            if self.thread is None:
                self.thread = threading.Thread(
                    target=self._run, name="mellowyak-browser", daemon=True
                )
                self.thread.start()

    def call(self, action: str, capture_id: str, payload: dict[str, Any]) -> Any:
        self._ensure_started()
        result: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)
        self.requests.put(_WorkerRequest(action, capture_id, payload, result))
        ok, value = result.get(timeout=BROWSER_STARTUP_TIMEOUT_SECONDS)
        if ok:
            return value
        raise BrowserCaptureError(str(value))

    def close(self) -> None:
        if self.thread is None:
            return
        self.requests.put(None)
        self.thread.join(timeout=10)

    def _run(self) -> None:
        runtime: Any = None
        browser: Any = None
        sessions: dict[str, dict[str, Any]] = {}
        try:
            from playwright.sync_api import sync_playwright

            runtime = sync_playwright().start()
            executable_path = _browser_executable()
            browser = runtime.chromium.launch(
                headless=os.environ.get("MELLOWYAK_BROWSER_HEADLESS", "") == "1",
                executable_path=executable_path,
                args=["--disable-background-networking", "--no-first-run"],
            )
            while True:
                request = self.requests.get()
                if request is None:
                    break
                try:
                    if request.action == "start":
                        value = self._start(browser, sessions, request.capture_id, request.payload)
                    elif request.action == "stop":
                        value = self._stop(sessions, request.capture_id)
                    elif request.action == "cancel":
                        value = self._cancel(sessions, request.capture_id)
                    elif request.action == "pause":
                        value = self._pause(sessions, request.capture_id, True)
                    elif request.action == "resume":
                        value = self._pause(sessions, request.capture_id, False)
                    elif request.action == "fixture":
                        value = self._fixture(sessions, request.capture_id)
                    else:
                        raise BrowserCaptureError("BROWSER_ACTION_INVALID")
                    request.result.put((True, value))
                except Exception as error:
                    request.result.put((False, self._error_code(error)))
        except Exception:
            while True:
                request = self.requests.get()
                if request is None:
                    break
                request.result.put((False, "BROWSER_RUNTIME_UNAVAILABLE"))
        finally:
            for state in sessions.values():
                try:
                    state["context"].close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            if runtime is not None:
                try:
                    runtime.stop()
                except Exception:
                    pass

    @staticmethod
    def _error_code(error: Exception) -> str:
        if isinstance(error, BrowserCaptureError):
            return error.code
        return "BROWSER_RUNTIME_OPERATION_FAILED"

    @staticmethod
    def _start(
        browser: Any, sessions: dict[str, dict[str, Any]], capture_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        allowed_origin = payload["allowed_origin"]
        context = browser.new_context(
            accept_downloads=False,
            service_workers="block",
            viewport=payload["viewport"],
            locale=payload["locale"],
            timezone_id=payload["timezone"],
        )
        state: dict[str, Any] = {
            "context": context,
            "steps": [],
            "observations": [],
            "screenshots": [],
            "allowed_origin": allowed_origin,
            "paused": False,
            "capture_network": payload["capture_network"],
            "started_monotonic": time.monotonic(),
            "last_event_signature": None,
            "last_event_monotonic": 0.0,
        }

        def route_guard(route: Any, request: Any) -> None:
            parsed = urlsplit(request.url)
            origin = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else ""
            if origin == allowed_origin and parsed.scheme == "http":
                route.continue_()
            else:
                route.abort("blockedbyclient")
                if len(state["observations"]) < MAX_RUNTIME_OBSERVATIONS:
                    state["observations"].append(
                        {
                            "observation_type": "network_blocked",
                            "metadata": {
                                "method": request.method,
                                "resource_type": request.resource_type,
                                "url": _safe_url(request.url),
                            },
                        }
                    )

        context.route("**/*", route_guard)
        page = context.new_page()

        def observe_request(request: Any) -> None:
            if state["capture_network"] and len(state["observations"]) < MAX_RUNTIME_OBSERVATIONS:
                state["observations"].append(
                    {
                        "observation_type": "network_request",
                        "metadata": {
                            "method": request.method,
                            "resource_type": request.resource_type,
                            "url": _safe_url(request.url),
                        },
                    }
                )

        page.on("request", observe_request)
        page.on(
            "pageerror",
            lambda error: (
                state["observations"].append(
                    {"observation_type": "page_error", "metadata": {"name": type(error).__name__}}
                )
                if len(state["observations"]) < MAX_RUNTIME_OBSERVATIONS
                else None
            ),
        )

        def capture_event(_source: Any, event: Any) -> None:
            if (
                state["paused"]
                or not isinstance(event, dict)
                or len(state["steps"]) >= MAX_CAPTURE_STEPS
                or time.monotonic() - state["started_monotonic"] >= MAX_CAPTURE_DURATION_SECONDS
            ):
                return
            event_type = str(event.get("type", "interaction"))[:40]
            selector = str(event.get("selector", ""))[:1000] or None
            signature = (event_type, selector, _safe_url(page.url))
            captured_at = time.monotonic()
            if (
                signature == state["last_event_signature"]
                and captured_at - state["last_event_monotonic"] < EVENT_COALESCE_WINDOW_SECONDS
            ):
                return
            state["last_event_signature"] = signature
            state["last_event_monotonic"] = captured_at
            state["steps"].append(
                {
                    "event_type": event_type,
                    "page_url": _safe_url(page.url),
                    "selector": selector,
                    "metadata": {
                        "tag": str(event.get("tag", ""))[:80],
                        "role": str(event.get("role", ""))[:80],
                        "accessible_name": str(event.get("accessibleName", ""))[:240],
                    },
                }
            )

        page.expose_binding("__mellowyakCapture", capture_event)
        page.add_init_script(
            """
            (() => {
              const selectorFor = (el) => {
                if (!el || !el.tagName) return '';
                const explicitRole = el.getAttribute('role');
                const implicitRole = ({
                  BUTTON: 'button', A: 'link', SELECT: 'combobox',
                  TEXTAREA: 'textbox'
                })[el.tagName] || '';
                const role = explicitRole || implicitRole;
                const accessibleName = (el.getAttribute('aria-label') ||
                  ((el.tagName === 'BUTTON' || el.tagName === 'A')
                    ? (el.textContent || '').trim() : '')).slice(0, 240);
                if (role && accessibleName)
                  return 'role=' + role + '[name="' + accessibleName.replaceAll('"', '\\"') + '"]';
                const testid = el.getAttribute('data-testid');
                if (testid) return '[data-testid="' + CSS.escape(testid) + '"]';
                if (el.id) return '#' + CSS.escape(el.id);
                for (const attr of ['name', 'type']) {
                  const value = el.getAttribute(attr);
                  if (value) return el.tagName.toLowerCase() + '[' + attr + '="' +
                    CSS.escape(value) + '"]';
                }
                return el.tagName.toLowerCase();
              };
              for (const type of ['click', 'change', 'submit']) {
                document.addEventListener(type, (event) => {
                  window.__mellowyakCapture({
                    type,
                    selector: selectorFor(event.target),
                    tag: event.target?.tagName || '',
                    role: event.target?.getAttribute?.('role') || '',
                    accessibleName: event.target?.getAttribute?.('aria-label') || ''
                  });
                }, true);
              }
            })();
            """
        )
        page.goto(payload["entry_url"], wait_until="domcontentloaded", timeout=30000)
        page.evaluate(
            """() => document.querySelectorAll('input,textarea,[contenteditable=true]').forEach(
              el => { if (el.type === 'password' || /password|secret|token|one-time-code/i.test(
                `${el.name || ''} ${el.id || ''} ${el.autocomplete || ''}`))
                  el.style.filter='blur(12px)'; })"""
        )
        start_screenshot = (
            page.screenshot(type="png", full_page=False) if payload["capture_screenshots"] else None
        )
        state["start_screenshot"] = start_screenshot
        sessions[capture_id] = {**state, "page": page}
        return {"url": _safe_url(page.url), "browser_version": browser.version}

    @staticmethod
    def _stop(sessions: dict[str, dict[str, Any]], capture_id: str) -> dict[str, Any]:
        state = sessions.pop(capture_id, None)
        if state is None:
            raise BrowserCaptureError("CAPTURE_RUNTIME_NOT_ACTIVE")
        page = state["page"]
        page.evaluate(
            """
            () => {
              const fields = document.querySelectorAll(
                'input, textarea, [contenteditable="true"]'
              );
              fields.forEach((el) => {
                el.dataset.mellowyakPreviousFilter = el.style.filter || '';
                el.style.filter = 'blur(8px)';
              });
            }
            """
        )
        screenshot = page.screenshot(type="png", full_page=False)
        final_url = _safe_url(page.url)
        title = page.title()[:240]
        state["context"].close()
        return {
            "steps": state["steps"],
            "observations": state["observations"],
            "start_screenshot": state["start_screenshot"],
            "final_screenshot": screenshot,
            "final_url": final_url,
            "page_title": title,
        }

    @staticmethod
    def _cancel(sessions: dict[str, dict[str, Any]], capture_id: str) -> dict[str, Any]:
        state = sessions.pop(capture_id, None)
        if state is not None:
            state["context"].close()
        return {"status": "cancelled"}

    @staticmethod
    def _pause(
        sessions: dict[str, dict[str, Any]], capture_id: str, paused: bool
    ) -> dict[str, Any]:
        state = sessions.get(capture_id)
        if state is None:
            raise BrowserCaptureError("CAPTURE_RUNTIME_NOT_ACTIVE")
        state["paused"] = paused
        return {"status": "paused" if paused else "recording"}

    @staticmethod
    def _fixture(sessions: dict[str, dict[str, Any]], capture_id: str) -> dict[str, Any]:
        state = sessions.get(capture_id)
        if state is None:
            raise BrowserCaptureError("CAPTURE_RUNTIME_NOT_ACTIVE")
        page = state["page"]
        page.get_by_test_id("open-event").click()
        page.get_by_test_id("reschedule-event").click()
        page.get_by_test_id("time-select").select_option("14:00")
        page.get_by_test_id("save-reschedule").click()
        page.get_by_test_id("event-time").wait_for()
        if page.get_by_test_id("event-time").inner_text() != "14:00":
            raise BrowserCaptureError("FIXTURE_EXPECTED_RESULT_MISSING")
        return {"status": "fixture_completed"}


class BrowserCaptureService:
    def __init__(
        self,
        sessions: sessionmaker,
        evidence: EvidenceService,
        events: LocalEventBus,
    ) -> None:
        self.sessions = sessions
        self.evidence = evidence
        self.events = events
        self.worker = _BrowserWorker()
        self.recover_interrupted()

    def recover_interrupted(self) -> int:
        now = _now()
        with self.sessions.begin() as session:
            rows = session.scalars(
                select(BrowserCaptureSession).where(
                    BrowserCaptureSession.status.in_(ACTIVE_CAPTURE_STATES)
                )
            ).all()
            for row in rows:
                row.status = "STALE_SOURCE"
                row.error_code = "ENGINE_RESTARTED_DURING_CAPTURE"
                row.stopped_at = now
                row.updated_at = now
            return len(rows)

    def start(
        self,
        project_id: str,
        behavior_id: str,
        runtime_configuration_id: str,
        entry_url: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        capture_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            project = session.get(Project, project_id)
            behavior = session.get(ProtectedBehavior, behavior_id)
            runtime = session.get(RuntimeConfiguration, runtime_configuration_id)
            if project is None or project.archived_at is not None:
                raise BrowserCaptureError("PROJECT_NOT_FOUND")
            if behavior is None or behavior.project_id != project_id:
                raise BrowserCaptureError("BEHAVIOR_NOT_FOUND")
            if behavior.lifecycle_state == "ARCHIVED":
                raise BrowserCaptureError("BEHAVIOR_ARCHIVED")
            if runtime is None or runtime.project_id != project_id:
                raise BrowserCaptureError("RUNTIME_NOT_FOUND")
            target = entry_url.strip() if entry_url else runtime.base_url
            try:
                target, target_origin = validate_loopback_runtime_url(target)
            except BehaviorServiceError as error:
                raise BrowserCaptureError(error.code) from error
            if target_origin != runtime.allowed_origin:
                raise BrowserCaptureError("CAPTURE_ORIGIN_NOT_ALLOWED")
            active = session.scalars(
                select(BrowserCaptureSession).where(
                    BrowserCaptureSession.project_id == project_id,
                    BrowserCaptureSession.status.in_(ACTIVE_CAPTURE_STATES),
                )
            ).first()
            if active is not None:
                raise BrowserCaptureError("CAPTURE_ALREADY_ACTIVE")
            row = BrowserCaptureSession(
                id=capture_id,
                project_id=project_id,
                behavior_id=behavior_id,
                behavior_version_id=behavior.current_version_id,
                runtime_configuration_id=runtime_configuration_id,
                status="STARTING",
                entry_url=target,
                source_revision_json=json.dumps(_source_revision(project), sort_keys=True),
                started_at=now,
                updated_at=now,
            )
            session.add(row)
            runtime_options = {
                "allowed_origin": runtime.allowed_origin,
                "viewport_width": runtime.viewport_width,
                "viewport_height": runtime.viewport_height,
                "locale": runtime.locale,
                "timezone": runtime.timezone,
                "browser_type": runtime.browser_type,
                "capture_screenshots": runtime.capture_screenshots,
                "capture_network": runtime.capture_network,
            }
        try:
            worker_result = self.worker.call(
                "start",
                capture_id,
                {
                    "entry_url": target,
                    "allowed_origin": runtime_options["allowed_origin"],
                    "viewport": {
                        "width": runtime_options["viewport_width"],
                        "height": runtime_options["viewport_height"],
                    },
                    "locale": runtime_options["locale"],
                    "timezone": runtime_options["timezone"],
                    "capture_screenshots": runtime_options["capture_screenshots"],
                    "capture_network": runtime_options["capture_network"],
                },
            )
        except BrowserCaptureError as error:
            self._mark_failed(capture_id, error.code)
            raise
        with self.sessions.begin() as session:
            row = session.get(BrowserCaptureSession, capture_id)
            row.status = "RECORDING"
            row.browser_version = worker_result["browser_version"]
            row.runtime_identity_json = json.dumps(
                {
                    "origin": runtime_options["allowed_origin"],
                    "viewport": [
                        runtime_options["viewport_width"],
                        runtime_options["viewport_height"],
                    ],
                    "locale": runtime_options["locale"],
                    "timezone": runtime_options["timezone"],
                    "browser_type": runtime_options["browser_type"],
                },
                sort_keys=True,
            )
            row.updated_at = _now()
        self.events.publish("browser_capture_started", project_id, {"capture_id": capture_id})
        return self.get(project_id, capture_id)

    def run_fixture_flow(self, project_id: str, capture_id: str) -> dict[str, Any]:
        if os.environ.get("MELLOWYAK_PHASE4_VALIDATION", "") != "1":
            raise BrowserCaptureError("VALIDATION_MODE_REQUIRED")
        row = self._capture(project_id, capture_id)
        if row.status != "RECORDING":
            raise BrowserCaptureError("CAPTURE_NOT_RECORDING")
        return self.worker.call("fixture", capture_id, {})

    def stop(self, project_id: str, capture_id: str) -> dict[str, Any]:
        row = self._capture(project_id, capture_id)
        if row.status != "RECORDING":
            raise BrowserCaptureError("CAPTURE_NOT_RECORDING")
        with self.sessions.begin() as session:
            active = session.get(BrowserCaptureSession, capture_id)
            active.status = "STOPPING"
            active.updated_at = _now()
        try:
            result = self.worker.call("stop", capture_id, {})
            self._persist_result(row, result)
            snapshot = self.get(project_id, capture_id)
            if snapshot["source_stale"]:
                with self.sessions.begin() as session:
                    stale = session.get(BrowserCaptureSession, capture_id)
                    stale.status = "STALE_SOURCE"
                    stale.error_code = "SOURCE_IDENTITY_CHANGED"
                    stale.updated_at = _now()
        except (BrowserCaptureError, EvidenceServiceError) as error:
            self._mark_failed(capture_id, error.code)
            raise BrowserCaptureError(error.code) from error
        self.events.publish(
            "browser_capture_review_required", project_id, {"capture_id": capture_id}
        )
        return self.get(project_id, capture_id)

    def pause(self, project_id: str, capture_id: str) -> dict[str, Any]:
        row = self._capture(project_id, capture_id)
        if row.status != "RECORDING" or row.paused:
            raise BrowserCaptureError("CAPTURE_NOT_RECORDING")
        self.worker.call("pause", capture_id, {})
        with self.sessions.begin() as session:
            active = session.get(BrowserCaptureSession, capture_id)
            active.paused = True
            active.updated_at = _now()
        self.events.publish("browser_capture_paused", project_id, {"capture_id": capture_id})
        return self.get(project_id, capture_id)

    def resume(self, project_id: str, capture_id: str) -> dict[str, Any]:
        row = self._capture(project_id, capture_id)
        if row.status != "RECORDING" or not row.paused:
            raise BrowserCaptureError("CAPTURE_NOT_PAUSED")
        self.worker.call("resume", capture_id, {})
        with self.sessions.begin() as session:
            active = session.get(BrowserCaptureSession, capture_id)
            active.paused = False
            active.updated_at = _now()
        self.events.publish("browser_capture_resumed", project_id, {"capture_id": capture_id})
        return self.get(project_id, capture_id)

    def review(
        self,
        project_id: str,
        capture_id: str,
        step_updates: list[dict[str, Any]],
        excluded_observation_ids: list[str],
        expected_assertions: list[dict[str, Any]],
        notes: str,
    ) -> dict[str, Any]:
        allowed_assertions = {
            "URL_EQUALS",
            "URL_CONTAINS",
            "ELEMENT_VISIBLE",
            "ELEMENT_HIDDEN",
            "TEXT_CONTAINS",
            "ATTRIBUTE_EQUALS",
            "API_CALL_OBSERVED",
            "HTTP_STATUS_OBSERVED",
            "SCREENSHOT_REFERENCE",
            "HUMAN_NOTE",
        }
        if any(str(item.get("type", "")) not in allowed_assertions for item in expected_assertions):
            raise BrowserCaptureError("EXPECTED_ASSERTION_INVALID")
        with self.sessions.begin() as session:
            row = session.get(BrowserCaptureSession, capture_id)
            if row is None or row.project_id != project_id:
                raise BrowserCaptureError("CAPTURE_NOT_FOUND")
            if row.status != "REVIEW_REQUIRED":
                raise BrowserCaptureError("CAPTURE_REVIEW_REQUIRED")
            for update in step_updates:
                step = session.get(BrowserCaptureStep, str(update.get("id", "")))
                if step is not None and step.capture_id == capture_id:
                    step.included = bool(update.get("included", True))
                    step.label = str(update.get("label", ""))[:500]
            for observation_id in excluded_observation_ids:
                observation = session.get(RuntimeObservation, observation_id)
                if observation is not None and observation.capture_id == capture_id:
                    observation.included = False
            row.expected_assertions_json = json.dumps(expected_assertions, sort_keys=True)
            row.review_notes = notes[:4000]
            row.updated_at = _now()
        self.events.publish("browser_capture_review_ready", project_id, {"capture_id": capture_id})
        return self.get(project_id, capture_id)

    def cancel(self, project_id: str, capture_id: str) -> dict[str, Any]:
        row = self._capture(project_id, capture_id)
        if row.status not in ACTIVE_CAPTURE_STATES:
            raise BrowserCaptureError("CAPTURE_NOT_ACTIVE")
        self.worker.call("cancel", capture_id, {})
        now = _now()
        with self.sessions.begin() as session:
            active = session.get(BrowserCaptureSession, capture_id)
            active.status = "CANCELLED"
            active.stopped_at = now
            active.updated_at = now
        return self.get(project_id, capture_id)

    def list(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            ids = session.scalars(
                select(BrowserCaptureSession.id)
                .where(BrowserCaptureSession.project_id == project_id)
                .order_by(BrowserCaptureSession.started_at.desc())
            ).all()
        return [self.get(project_id, row_id) for row_id in ids]

    def get(self, project_id: str, capture_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(BrowserCaptureSession, capture_id)
            if row is None or row.project_id != project_id:
                raise BrowserCaptureError("CAPTURE_NOT_FOUND")
            project = session.get(Project, project_id)
            steps = session.scalars(
                select(BrowserCaptureStep)
                .where(BrowserCaptureStep.capture_id == capture_id)
                .order_by(BrowserCaptureStep.ordinal)
            ).all()
            observations = session.scalars(
                select(RuntimeObservation)
                .where(RuntimeObservation.capture_id == capture_id)
                .order_by(RuntimeObservation.observed_at)
            ).all()
            source = json.loads(row.source_revision_json)
            current = _source_revision(project)
            stale = any(source.get(key) != current.get(key) for key in source)
            return {
                "id": row.id,
                "project_id": row.project_id,
                "behavior_id": row.behavior_id,
                "behavior_version_id": row.behavior_version_id,
                "runtime_configuration_id": row.runtime_configuration_id,
                "status": row.status,
                "entry_url": row.entry_url,
                "source_revision": source,
                "source_stale": stale,
                "steps": [
                    {
                        "id": step.id,
                        "ordinal": step.ordinal,
                        "event_type": step.event_type,
                        "page_url": step.page_url,
                        "selector": step.selector,
                        "metadata": json.loads(step.metadata_json),
                        "occurred_at": step.occurred_at,
                        "included": step.included,
                        "label": step.label,
                    }
                    for step in steps
                ],
                "observations": [
                    {
                        "id": item.id,
                        "observation_type": item.observation_type,
                        "metadata": json.loads(item.metadata_json),
                        "observed_at": item.observed_at,
                        "included": item.included,
                    }
                    for item in observations
                ],
                "started_at": row.started_at,
                "stopped_at": row.stopped_at,
                "error_code": row.error_code,
                "paused": row.paused,
                "browser_version": row.browser_version,
                "expected_assertions": json.loads(row.expected_assertions_json),
            }

    def _capture(self, project_id: str, capture_id: str) -> BrowserCaptureSession:
        with self.sessions() as session:
            row = session.get(BrowserCaptureSession, capture_id)
            if row is None or row.project_id != project_id:
                raise BrowserCaptureError("CAPTURE_NOT_FOUND")
            session.expunge(row)
            return row

    def _persist_result(self, capture: BrowserCaptureSession, result: dict[str, Any]) -> None:
        source_identity = json.loads(capture.source_revision_json)
        runtime_identity = json.loads(capture.runtime_identity_json)
        artifact_context = {
            "capture_id": capture.id,
            "behavior_id": capture.behavior_id,
            "behavior_version_id": capture.behavior_version_id,
            "source_identity": source_identity,
            "runtime_identity": runtime_identity,
        }
        screenshot_items: list[tuple[str, str]] = []
        if result["start_screenshot"] is not None:
            start = self.evidence.add_artifact(
                capture.project_id, result["start_screenshot"], "image/png", **artifact_context
            )
            screenshot_items.append(("start_screenshot", start["id"]))
        final = self.evidence.add_artifact(
            capture.project_id, result["final_screenshot"], "image/png", **artifact_context
        )
        screenshot_items.append(("final_screenshot", final["id"]))
        steps_payload = json.dumps(result["steps"], sort_keys=True, separators=(",", ":")).encode()
        observations_payload = json.dumps(
            result["observations"], sort_keys=True, separators=(",", ":")
        ).encode()
        steps_artifact = self.evidence.add_artifact(
            capture.project_id, steps_payload, "application/json", **artifact_context
        )
        observations_artifact = self.evidence.add_artifact(
            capture.project_id, observations_payload, "application/json", **artifact_context
        )
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(BrowserCaptureSession, capture.id)
            for ordinal, step in enumerate(result["steps"][:MAX_CAPTURE_STEPS], start=1):
                session.add(
                    BrowserCaptureStep(
                        id=str(uuid.uuid4()),
                        capture_id=capture.id,
                        ordinal=ordinal,
                        event_type=step["event_type"],
                        page_url=step["page_url"],
                        selector=step["selector"],
                        metadata_json=json.dumps(step["metadata"], sort_keys=True),
                        occurred_at=now,
                        included=True,
                        label="",
                    )
                )
            for observation in result["observations"][:MAX_RUNTIME_OBSERVATIONS]:
                session.add(
                    RuntimeObservation(
                        id=str(uuid.uuid4()),
                        capture_id=capture.id,
                        observation_type=observation["observation_type"],
                        metadata_json=json.dumps(observation["metadata"], sort_keys=True),
                        observed_at=now,
                        included=True,
                    )
                )
            row.status = "REVIEW_REQUIRED"
            row.stopped_at = now
            row.updated_at = now
            observed_links = [("RUNTIME_ROUTE", urlsplit(result["final_url"]).path or "/")]
            observed_links.extend(
                ("API_ENDPOINT", urlsplit(item["metadata"].get("url", "")).path or "/")
                for item in result["observations"]
                if item["observation_type"] == "network_request"
            )
            observed_links.extend(
                ("UI_ELEMENT", step["selector"]) for step in result["steps"] if step.get("selector")
            )
            for link_type, link_key in dict.fromkeys(observed_links):
                exists = session.scalars(
                    select(BehaviorLink).where(
                        BehaviorLink.behavior_id == capture.behavior_id,
                        BehaviorLink.link_type == link_type,
                        BehaviorLink.link_key == link_key,
                    )
                ).first()
                if exists is None:
                    session.add(
                        BehaviorLink(
                            id=str(uuid.uuid4()),
                            behavior_id=capture.behavior_id,
                            project_id=capture.project_id,
                            link_type=link_type,
                            link_key=link_key[:1000],
                            provenance="RUNTIME_OBSERVED",
                            created_at=now,
                        )
                    )
        self.evidence.create_bundle(
            capture.project_id,
            capture.id,
            [
                *screenshot_items,
                ("interaction_steps", steps_artifact["id"]),
                ("runtime_observations", observations_artifact["id"]),
            ],
        )

    def _mark_failed(self, capture_id: str, code: str) -> None:
        now = _now()
        with self.sessions.begin() as session:
            row = session.get(BrowserCaptureSession, capture_id)
            if row is not None:
                row.status = "FAILED"
                row.error_code = code[:120]
                row.stopped_at = now
                row.updated_at = now

    def close(self) -> None:
        self.worker.close()

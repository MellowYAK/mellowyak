from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import (
    BehaviorBaseline,
    BehaviorCandidate,
    BehaviorLink,
    BehaviorVersion,
    Project,
    ProtectedBehavior,
    RuntimeConfiguration,
)


class BehaviorServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(UTC)


def _source_revision(project: Project) -> dict[str, Any]:
    return {
        "branch": project.current_branch,
        "head_sha": project.current_head_sha,
        "worktree_fingerprint": project.current_worktree_fingerprint,
    }


CRITICALITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
LINK_TYPES = {
    "FILE",
    "SYMBOL",
    "TEST",
    "ROUTE_HINT",
    "RUNTIME_ROUTE",
    "API_ENDPOINT",
    "UI_ELEMENT",
    "UNKNOWN_REFERENCE",
    "BEHAVIOR_CANDIDATE",
}
LINK_PROVENANCE = {
    "HUMAN_CONFIRMED",
    "RUNTIME_OBSERVED",
    "STATIC_PARSED",
    "STATIC_HEURISTIC",
    "TEST_DERIVED",
    "UNKNOWN",
}


def _version_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def validate_loopback_runtime_url(value: str) -> tuple[str, str]:
    raw = value.strip()
    parsed = urlsplit(raw)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise BehaviorServiceError("RUNTIME_LOOPBACK_HTTP_REQUIRED")
    if parsed.username or parsed.password or parsed.fragment:
        raise BehaviorServiceError("RUNTIME_URL_INVALID")
    try:
        port = parsed.port
    except ValueError as error:
        raise BehaviorServiceError("RUNTIME_PORT_INVALID") from error
    if port is None or not 1 <= port <= 65535:
        raise BehaviorServiceError("RUNTIME_EXPLICIT_PORT_REQUIRED")
    origin = f"http://{parsed.hostname}:{port}"
    normalized = f"{origin}{parsed.path or '/'}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized, origin


class BehaviorService:
    def __init__(self, sessions: sessionmaker, events: LocalEventBus) -> None:
        self.sessions = sessions
        self.events = events

    def _project(self, session: Any, project_id: str) -> Project:
        project = session.get(Project, project_id)
        if project is None or project.archived_at is not None:
            raise BehaviorServiceError("PROJECT_NOT_FOUND")
        return project

    def _behavior(self, session: Any, project_id: str, behavior_id: str) -> ProtectedBehavior:
        behavior = session.get(ProtectedBehavior, behavior_id)
        if behavior is None or behavior.project_id != project_id:
            raise BehaviorServiceError("BEHAVIOR_NOT_FOUND")
        return behavior

    def create_draft(
        self,
        project_id: str,
        title: str,
        description: str,
        expected_outcome: str,
        links: list[dict[str, str]] | None = None,
        criticality: str = "MEDIUM",
        persona: str = "",
        preconditions: str = "",
        starting_state: str = "",
        expected_assertions: list[dict[str, Any]] | None = None,
        created_by_type: str = "HUMAN",
        source_candidate_id: str | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        description = description.strip()
        expected_outcome = expected_outcome.strip()
        if not title or len(title) > 240:
            raise BehaviorServiceError("BEHAVIOR_TITLE_INVALID")
        if len(description) > 4000 or len(expected_outcome) > 4000:
            raise BehaviorServiceError("BEHAVIOR_CONTENT_TOO_LONG")
        criticality = criticality.upper().strip()
        if criticality not in CRITICALITIES:
            raise BehaviorServiceError("BEHAVIOR_CRITICALITY_INVALID")
        if len(persona) > 500 or len(preconditions) > 4000 or len(starting_state) > 4000:
            raise BehaviorServiceError("BEHAVIOR_CONTENT_TOO_LONG")
        behavior_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        now = _now()
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            behavior = ProtectedBehavior(
                id=behavior_id,
                project_id=project_id,
                stable_key=behavior_id,
                display_name=title,
                lifecycle_state="DRAFT",
                current_version_id=version_id,
                created_at=now,
                updated_at=now,
            )
            session.add(behavior)
            session.flush()
            version_payload = {
                "title": title,
                "description": description,
                "expected_outcome": expected_outcome,
                "criticality": criticality,
                "persona": persona.strip(),
                "preconditions": preconditions.strip(),
                "starting_state": starting_state.strip(),
                "expected_assertions": expected_assertions or [],
            }
            session.add(
                BehaviorVersion(
                    id=version_id,
                    behavior_id=behavior_id,
                    project_id=project_id,
                    version_number=1,
                    title=title,
                    description=description,
                    expected_outcome=expected_outcome,
                    criticality=criticality,
                    persona=persona.strip(),
                    preconditions=preconditions.strip(),
                    starting_state=starting_state.strip(),
                    expected_assertions_json=json.dumps(expected_assertions or [], sort_keys=True),
                    limitations_json=json.dumps(["AUTOMATIC_VERIFICATION_NOT_CONFIGURED"]),
                    verification_not_configured=True,
                    created_by_type=created_by_type[:40],
                    source_candidate_id=source_candidate_id,
                    content_digest=_version_digest(version_payload),
                    source_revision_json=json.dumps(_source_revision(project), sort_keys=True),
                    created_at=now,
                )
            )
            for link in links or []:
                link_type = str(link.get("link_type", "")).strip().upper()
                link_key = str(link.get("link_key", "")).strip()
                provenance = str(link.get("provenance", "HUMAN_CONFIRMED")).strip().upper()
                if link_type in LINK_TYPES and link_key and provenance in LINK_PROVENANCE:
                    session.add(
                        BehaviorLink(
                            id=str(uuid.uuid4()),
                            behavior_id=behavior_id,
                            project_id=project_id,
                            link_type=link_type[:40],
                            link_key=link_key[:1000],
                            provenance=provenance,
                            created_at=now,
                        )
                    )
        self.events.publish("behavior_draft_created", project_id, {"behavior_id": behavior_id})
        return self.get(project_id, behavior_id)

    def create_from_candidate(self, project_id: str, candidate_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            candidate = session.get(BehaviorCandidate, candidate_id)
            if candidate is None or candidate.project_id != project_id:
                raise BehaviorServiceError("BEHAVIOR_CANDIDATE_NOT_FOUND")
            existing = session.scalars(
                select(BehaviorLink).where(
                    BehaviorLink.project_id == project_id,
                    BehaviorLink.link_type == "BEHAVIOR_CANDIDATE",
                    BehaviorLink.link_key == candidate_id,
                )
            ).first()
            if existing is not None:
                return self.get(project_id, existing.behavior_id)
            title = candidate.title
        return self.create_draft(
            project_id,
            title,
            "",
            "",
            [
                {
                    "link_type": "BEHAVIOR_CANDIDATE",
                    "link_key": candidate_id,
                    "provenance": "STATIC_HEURISTIC",
                }
            ],
            created_by_type="CANDIDATE_PROMOTION",
            source_candidate_id=candidate_id,
        )

    def update(
        self,
        project_id: str,
        behavior_id: str,
        title: str,
        description: str,
        expected_outcome: str,
        criticality: str = "MEDIUM",
        persona: str = "",
        preconditions: str = "",
        starting_state: str = "",
        expected_assertions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        if not title or len(title) > 240:
            raise BehaviorServiceError("BEHAVIOR_TITLE_INVALID")
        if len(description) > 4000 or len(expected_outcome) > 4000:
            raise BehaviorServiceError("BEHAVIOR_CONTENT_TOO_LONG")
        criticality = criticality.upper().strip()
        if criticality not in CRITICALITIES:
            raise BehaviorServiceError("BEHAVIOR_CRITICALITY_INVALID")
        now = _now()
        version_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            project = self._project(session, project_id)
            behavior = self._behavior(session, project_id, behavior_id)
            if behavior.lifecycle_state == "ARCHIVED":
                raise BehaviorServiceError("BEHAVIOR_ARCHIVED")
            next_version = (
                int(
                    session.scalar(
                        select(func.max(BehaviorVersion.version_number)).where(
                            BehaviorVersion.behavior_id == behavior_id
                        )
                    )
                    or 0
                )
                + 1
            )
            previous_version_id = behavior.current_version_id
            version_payload = {
                "title": title,
                "description": description.strip(),
                "expected_outcome": expected_outcome.strip(),
                "criticality": criticality,
                "persona": persona.strip(),
                "preconditions": preconditions.strip(),
                "starting_state": starting_state.strip(),
                "expected_assertions": expected_assertions or [],
            }
            session.add(
                BehaviorVersion(
                    id=version_id,
                    behavior_id=behavior_id,
                    project_id=project_id,
                    version_number=next_version,
                    title=title,
                    description=description.strip(),
                    expected_outcome=expected_outcome.strip(),
                    criticality=criticality,
                    persona=persona.strip(),
                    preconditions=preconditions.strip(),
                    starting_state=starting_state.strip(),
                    expected_assertions_json=json.dumps(expected_assertions or [], sort_keys=True),
                    limitations_json=json.dumps(["AUTOMATIC_VERIFICATION_NOT_CONFIGURED"]),
                    verification_not_configured=True,
                    created_by_type="HUMAN",
                    content_digest=_version_digest(version_payload),
                    supersedes_version_id=previous_version_id,
                    source_revision_json=json.dumps(_source_revision(project), sort_keys=True),
                    created_at=now,
                )
            )
            behavior.current_version_id = version_id
            behavior.display_name = title
            if behavior.lifecycle_state == "PROTECTED":
                behavior.lifecycle_state = "DRAFT"
                if behavior.last_accepted_baseline_id:
                    previous_baseline = session.get(
                        BehaviorBaseline, behavior.last_accepted_baseline_id
                    )
                    if previous_baseline is not None:
                        previous_baseline.status = "STALE"
            behavior.updated_at = now
        self.events.publish(
            "behavior_version_created",
            project_id,
            {"behavior_id": behavior_id, "version_id": version_id},
        )
        return self.get(project_id, behavior_id)

    def archive(self, project_id: str, behavior_id: str) -> dict[str, Any]:
        now = _now()
        with self.sessions.begin() as session:
            behavior = self._behavior(session, project_id, behavior_id)
            behavior.lifecycle_state = "ARCHIVED"
            behavior.archived_at = now
            behavior.updated_at = now
        self.events.publish("behavior_archived", project_id, {"behavior_id": behavior_id})
        return self.get(project_id, behavior_id)

    def add_runtime(
        self,
        project_id: str,
        display_name: str,
        base_url: str,
        starting_path: str = "/",
        viewport_width: int = 1280,
        viewport_height: int = 800,
        locale: str = "en-US",
        timezone: str = "UTC",
        browser_type: str = "chromium",
        capture_screenshots: bool = True,
        capture_trace: bool = False,
        capture_video: bool = False,
        capture_network: bool = True,
    ) -> dict[str, Any]:
        normalized, origin = validate_loopback_runtime_url(base_url)
        display_name = display_name.strip()
        if not display_name or len(display_name) > 240:
            raise BehaviorServiceError("RUNTIME_NAME_INVALID")
        if (
            not starting_path.startswith("/")
            or not (320 <= viewport_width <= 3840)
            or not (240 <= viewport_height <= 2160)
        ):
            raise BehaviorServiceError("RUNTIME_CONFIGURATION_INVALID")
        if browser_type != "chromium":
            raise BehaviorServiceError("RUNTIME_BROWSER_UNSUPPORTED")
        now = _now()
        runtime_id = str(uuid.uuid4())
        with self.sessions.begin() as session:
            self._project(session, project_id)
            existing = session.scalars(
                select(RuntimeConfiguration).where(
                    RuntimeConfiguration.project_id == project_id,
                    RuntimeConfiguration.allowed_origin == origin,
                )
            ).first()
            if existing is not None:
                existing.display_name = display_name
                existing.base_url = normalized
                existing.starting_path = starting_path
                existing.viewport_width = viewport_width
                existing.viewport_height = viewport_height
                existing.locale = locale[:40]
                existing.timezone = timezone[:80]
                existing.capture_screenshots = capture_screenshots
                existing.capture_trace = capture_trace
                existing.capture_video = capture_video
                existing.capture_network = capture_network
                existing.updated_at = now
                runtime_id = existing.id
            else:
                session.add(
                    RuntimeConfiguration(
                        id=runtime_id,
                        project_id=project_id,
                        display_name=display_name,
                        base_url=normalized,
                        allowed_origin=origin,
                        starting_path=starting_path,
                        viewport_width=viewport_width,
                        viewport_height=viewport_height,
                        locale=locale[:40],
                        timezone=timezone[:80],
                        browser_type=browser_type,
                        capture_screenshots=capture_screenshots,
                        capture_trace=capture_trace,
                        capture_video=capture_video,
                        capture_network=capture_network,
                        created_at=now,
                        updated_at=now,
                    )
                )
        return self.runtime(project_id, runtime_id)

    def runtime(self, project_id: str, runtime_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(RuntimeConfiguration, runtime_id)
            if row is None or row.project_id != project_id:
                raise BehaviorServiceError("RUNTIME_NOT_FOUND")
            return self._runtime_public(row)

    def runtimes(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            rows = session.scalars(
                select(RuntimeConfiguration)
                .where(RuntimeConfiguration.project_id == project_id)
                .order_by(RuntimeConfiguration.created_at)
            ).all()
            return [self._runtime_public(row) for row in rows]

    def test_runtime(self, project_id: str, runtime_id: str) -> dict[str, Any]:
        runtime = self.runtime(project_id, runtime_id)
        validate_loopback_runtime_url(runtime["base_url"])
        try:
            with urlopen(Request(runtime["base_url"], method="GET"), timeout=3) as response:
                reachable = 200 <= response.status < 500
                status_code = response.status
        except OSError:
            reachable = False
            status_code = None
        return {
            "status": "reachable" if reachable else "unavailable",
            "runtime_id": runtime_id,
            "status_code": status_code,
        }

    def list(self, project_id: str) -> list[dict[str, Any]]:
        with self.sessions() as session:
            self._project(session, project_id)
            ids = session.scalars(
                select(ProtectedBehavior.id)
                .where(ProtectedBehavior.project_id == project_id)
                .order_by(ProtectedBehavior.updated_at.desc())
            ).all()
        return [self.get(project_id, behavior_id) for behavior_id in ids]

    def get(self, project_id: str, behavior_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            behavior = self._behavior(session, project_id, behavior_id)
            versions = session.scalars(
                select(BehaviorVersion)
                .where(BehaviorVersion.behavior_id == behavior_id)
                .order_by(BehaviorVersion.version_number.desc())
            ).all()
            links = session.scalars(
                select(BehaviorLink).where(BehaviorLink.behavior_id == behavior_id)
            ).all()
            baselines = session.scalars(
                select(BehaviorBaseline)
                .where(BehaviorBaseline.behavior_id == behavior_id)
                .order_by(BehaviorBaseline.created_at.desc())
            ).all()
            current = next(row for row in versions if row.id == behavior.current_version_id)
            return {
                "id": behavior.id,
                "project_id": behavior.project_id,
                "stable_key": behavior.stable_key,
                "display_name": behavior.display_name,
                "lifecycle_state": behavior.lifecycle_state,
                "current_version_id": behavior.current_version_id,
                "last_accepted_baseline_id": behavior.last_accepted_baseline_id,
                "current_version": self._version_public(current),
                "versions": [self._version_public(row) for row in versions],
                "links": [
                    {
                        "id": row.id,
                        "link_type": row.link_type,
                        "link_key": row.link_key,
                        "provenance": row.provenance,
                    }
                    for row in links
                ],
                "baselines": [
                    {
                        "id": row.id,
                        "status": row.status,
                        "behavior_version_id": row.behavior_version_id,
                        "evidence_bundle_id": row.evidence_bundle_id,
                        "created_at": row.created_at,
                    }
                    for row in baselines
                ],
                "created_at": behavior.created_at,
                "updated_at": behavior.updated_at,
                "archived_at": behavior.archived_at,
            }

    @staticmethod
    def _version_public(row: BehaviorVersion) -> dict[str, Any]:
        return {
            "id": row.id,
            "version_number": row.version_number,
            "title": row.title,
            "description": row.description,
            "expected_outcome": row.expected_outcome,
            "criticality": row.criticality,
            "persona": row.persona,
            "preconditions": row.preconditions,
            "starting_state": row.starting_state,
            "expected_assertions": json.loads(row.expected_assertions_json),
            "limitations": json.loads(row.limitations_json),
            "verification_not_configured": row.verification_not_configured,
            "created_by_type": row.created_by_type,
            "source_candidate_id": row.source_candidate_id,
            "content_digest": row.content_digest,
            "supersedes_version_id": row.supersedes_version_id,
            "source_revision": json.loads(row.source_revision_json),
            "created_at": row.created_at,
        }

    @staticmethod
    def _runtime_public(row: RuntimeConfiguration) -> dict[str, Any]:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "display_name": row.display_name,
            "base_url": row.base_url,
            "allowed_origin": row.allowed_origin,
            "starting_path": row.starting_path,
            "viewport_width": row.viewport_width,
            "viewport_height": row.viewport_height,
            "locale": row.locale,
            "timezone": row.timezone,
            "browser_type": row.browser_type,
            "capture_screenshots": row.capture_screenshots,
            "capture_trace": row.capture_trace,
            "capture_video": row.capture_video,
            "capture_network": row.capture_network,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

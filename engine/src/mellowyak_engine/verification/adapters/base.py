from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any, Protocol


@dataclass(frozen=True)
class ReplayInput:
    entry_url: str
    allowed_origin: str
    viewport: dict[str, int]
    locale: str
    timezone: str
    steps: list[dict[str, Any]]
    assertions: list[dict[str, Any]]
    source_identity: dict[str, Any]
    behavior_version_id: str
    baseline_id: str


@dataclass
class AdapterExecution:
    result: str
    assertion_results: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[tuple[str, bytes, str]] = field(default_factory=list)
    runtime_identity: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    failure_reason: str | None = None


class VerificationAdapter(Protocol):
    name: str
    version: str

    def availability(self) -> tuple[bool, str | None]: ...

    def execute(self, request: ReplayInput, cancel: Event) -> AdapterExecution: ...

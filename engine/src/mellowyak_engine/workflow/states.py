from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Generic, TypeVar


class BehaviorState(StrEnum):
    DRAFT = "DRAFT"
    CAPTURING = "CAPTURING"
    CAPTURED = "CAPTURED"
    VALIDATING = "VALIDATING"
    KNOWN_GOOD = "KNOWN_GOOD"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DISABLED = "DISABLED"
    INVALID = "INVALID"


class EpisodeState(StrEnum):
    OPEN = "OPEN"
    SETTLING = "SETTLING"
    STABILIZED = "STABILIZED"
    IMPACT_PENDING = "IMPACT_PENDING"
    CHECKS_RUNNING = "CHECKS_RUNNING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    CANCELLED = "CANCELLED"


class VerificationState(StrEnum):
    NOT_SELECTED = "NOT_SELECTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SKIPPED = "SKIPPED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    CANCELLED = "CANCELLED"


class RegressionState(StrEnum):
    NONE = "NONE"
    WATCH = "WATCH"
    SUSPECTED = "SUSPECTED"
    HIGH = "HIGH"
    CONFIRMED = "CONFIRMED"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class RepairWorkspaceState(StrEnum):
    CREATING = "CREATING"
    READY = "READY"
    CHANGED = "CHANGED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    INVALID = "INVALID"
    DELETED = "DELETED"


class CandidateState(StrEnum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    STALE = "STALE"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    RETAINED_AFTER_ROLLBACK = "RETAINED_AFTER_ROLLBACK"


class ApplyState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    PREFLIGHT = "PREFLIGHT"
    SAFETY_SNAPSHOT = "SAFETY_SNAPSHOT"
    JOURNAL_CREATED = "JOURNAL_CREATED"
    PREPARING = "PREPARING"
    WRITING = "WRITING"
    CAPTURING_LIVE_SOURCE = "CAPTURING_LIVE_SOURCE"
    VERIFYING_LIVE = "VERIFYING_LIVE"
    COMMITTED = "COMMITTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class UpdaterState(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"
    CHECKING = "CHECKING"
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    DOWNLOADING = "DOWNLOADING"
    VERIFYING_SIGNATURE = "VERIFYING_SIGNATURE"
    INSTALLING = "INSTALLING"
    RESTART_REQUIRED = "RESTART_REQUIRED"
    UPDATED = "UPDATED"
    NO_UPDATE = "NO_UPDATE"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    INCOMPLETE_DOWNLOAD = "INCOMPLETE_DOWNLOAD"
    FAILED = "FAILED"
    PRODUCTION_CHANNEL_UNPUBLISHED = "PRODUCTION_CHANNEL_UNPUBLISHED"


StateT = TypeVar("StateT", bound=StrEnum)


@dataclass(frozen=True)
class TransitionRecord(Generic[StateT]):
    previous: StateT
    current: StateT
    timestamp: datetime
    reason: str
    evidence: tuple[str, ...]


class TransitionError(RuntimeError):
    def __init__(self, previous: StrEnum, current: StrEnum, code: str) -> None:
        self.previous = previous
        self.current = current
        self.code = code
        super().__init__(code)


def _states(*values: StateT) -> frozenset[StateT]:
    return frozenset(values)


BEHAVIOR_TRANSITIONS = {
    BehaviorState.DRAFT: _states(BehaviorState.CAPTURING, BehaviorState.DISABLED),
    BehaviorState.CAPTURING: _states(
        BehaviorState.CAPTURED, BehaviorState.NEEDS_REVIEW, BehaviorState.INVALID
    ),
    BehaviorState.CAPTURED: _states(BehaviorState.VALIDATING, BehaviorState.INVALID),
    BehaviorState.VALIDATING: _states(
        BehaviorState.KNOWN_GOOD, BehaviorState.NEEDS_REVIEW, BehaviorState.INVALID
    ),
    BehaviorState.KNOWN_GOOD: _states(
        BehaviorState.CAPTURING, BehaviorState.NEEDS_REVIEW, BehaviorState.DISABLED
    ),
    BehaviorState.NEEDS_REVIEW: _states(
        BehaviorState.CAPTURING, BehaviorState.VALIDATING, BehaviorState.DISABLED
    ),
    BehaviorState.DISABLED: _states(BehaviorState.DRAFT, BehaviorState.KNOWN_GOOD),
    BehaviorState.INVALID: _states(BehaviorState.DRAFT, BehaviorState.DISABLED),
}

EPISODE_TRANSITIONS = {
    EpisodeState.OPEN: _states(EpisodeState.SETTLING, EpisodeState.CANCELLED),
    EpisodeState.SETTLING: _states(
        EpisodeState.STABILIZED, EpisodeState.INCOMPLETE, EpisodeState.CANCELLED
    ),
    EpisodeState.STABILIZED: _states(EpisodeState.IMPACT_PENDING, EpisodeState.INCOMPLETE),
    EpisodeState.IMPACT_PENDING: _states(
        EpisodeState.CHECKS_RUNNING, EpisodeState.COMPLETE, EpisodeState.INCOMPLETE
    ),
    EpisodeState.CHECKS_RUNNING: _states(
        EpisodeState.COMPLETE, EpisodeState.INCOMPLETE, EpisodeState.CANCELLED
    ),
    EpisodeState.COMPLETE: frozenset(),
    EpisodeState.INCOMPLETE: _states(EpisodeState.IMPACT_PENDING, EpisodeState.CANCELLED),
    EpisodeState.CANCELLED: frozenset(),
}

VERIFICATION_TRANSITIONS = {
    VerificationState.NOT_SELECTED: _states(VerificationState.QUEUED, VerificationState.SKIPPED),
    VerificationState.QUEUED: _states(
        VerificationState.RUNNING,
        VerificationState.CANCELLED,
        VerificationState.RUNTIME_UNAVAILABLE,
    ),
    VerificationState.RUNNING: _states(
        VerificationState.PASSED,
        VerificationState.FAILED,
        VerificationState.INCONCLUSIVE,
        VerificationState.RUNTIME_UNAVAILABLE,
        VerificationState.CANCELLED,
    ),
    VerificationState.PASSED: frozenset(),
    VerificationState.FAILED: frozenset(),
    VerificationState.INCONCLUSIVE: _states(VerificationState.QUEUED),
    VerificationState.SKIPPED: _states(VerificationState.QUEUED),
    VerificationState.RUNTIME_UNAVAILABLE: _states(VerificationState.QUEUED),
    VerificationState.CANCELLED: _states(VerificationState.QUEUED),
}

REGRESSION_TRANSITIONS = {
    RegressionState.NONE: _states(RegressionState.WATCH),
    RegressionState.WATCH: _states(
        RegressionState.NONE, RegressionState.SUSPECTED, RegressionState.HIGH
    ),
    RegressionState.SUSPECTED: _states(
        RegressionState.WATCH, RegressionState.HIGH, RegressionState.CONFIRMED
    ),
    RegressionState.HIGH: _states(
        RegressionState.WATCH, RegressionState.CONFIRMED, RegressionState.DISMISSED
    ),
    RegressionState.CONFIRMED: _states(
        RegressionState.REVIEWED, RegressionState.DISMISSED, RegressionState.RESOLVED
    ),
    RegressionState.REVIEWED: _states(
        RegressionState.CONFIRMED, RegressionState.DISMISSED, RegressionState.RESOLVED
    ),
    RegressionState.DISMISSED: _states(RegressionState.WATCH, RegressionState.CONFIRMED),
    RegressionState.RESOLVED: _states(RegressionState.WATCH),
}

REPAIR_WORKSPACE_TRANSITIONS = {
    RepairWorkspaceState.CREATING: _states(
        RepairWorkspaceState.READY, RepairWorkspaceState.INVALID, RepairWorkspaceState.DELETED
    ),
    RepairWorkspaceState.READY: _states(
        RepairWorkspaceState.CHANGED,
        RepairWorkspaceState.VALIDATING,
        RepairWorkspaceState.DELETED,
    ),
    RepairWorkspaceState.CHANGED: _states(
        RepairWorkspaceState.VALIDATING,
        RepairWorkspaceState.READY,
        RepairWorkspaceState.DELETED,
    ),
    RepairWorkspaceState.VALIDATING: _states(
        RepairWorkspaceState.VALIDATED,
        RepairWorkspaceState.INVALID,
        RepairWorkspaceState.CHANGED,
    ),
    RepairWorkspaceState.VALIDATED: _states(
        RepairWorkspaceState.CHANGED, RepairWorkspaceState.DELETED
    ),
    RepairWorkspaceState.INVALID: _states(
        RepairWorkspaceState.CHANGED, RepairWorkspaceState.DELETED
    ),
    RepairWorkspaceState.DELETED: frozenset(),
}

CANDIDATE_TRANSITIONS = {
    CandidateState.DRAFT: _states(CandidateState.GENERATING, CandidateState.REJECTED),
    CandidateState.GENERATING: _states(CandidateState.GENERATED, CandidateState.REJECTED),
    CandidateState.GENERATED: _states(
        CandidateState.VALIDATING, CandidateState.STALE, CandidateState.REJECTED
    ),
    CandidateState.VALIDATING: _states(
        CandidateState.VALIDATED, CandidateState.STALE, CandidateState.REJECTED
    ),
    CandidateState.VALIDATED: _states(
        CandidateState.APPLIED,
        CandidateState.STALE,
        CandidateState.REJECTED,
        CandidateState.RETAINED_AFTER_ROLLBACK,
    ),
    CandidateState.STALE: _states(CandidateState.GENERATING, CandidateState.REJECTED),
    CandidateState.REJECTED: frozenset(),
    CandidateState.APPLIED: frozenset(),
    CandidateState.RETAINED_AFTER_ROLLBACK: _states(
        CandidateState.VALIDATING, CandidateState.REJECTED
    ),
}

APPLY_TRANSITIONS = {
    ApplyState.NOT_STARTED: _states(ApplyState.AWAITING_CONFIRMATION, ApplyState.BLOCKED),
    ApplyState.AWAITING_CONFIRMATION: _states(
        ApplyState.PREFLIGHT, ApplyState.CANCELLED, ApplyState.BLOCKED
    ),
    ApplyState.PREFLIGHT: _states(
        ApplyState.SAFETY_SNAPSHOT, ApplyState.CANCELLED, ApplyState.BLOCKED
    ),
    ApplyState.SAFETY_SNAPSHOT: _states(
        ApplyState.JOURNAL_CREATED,
        ApplyState.ROLLING_BACK,
        ApplyState.RECOVERY_REQUIRED,
        ApplyState.CANCELLED,
    ),
    ApplyState.JOURNAL_CREATED: _states(
        ApplyState.PREPARING,
        ApplyState.ROLLING_BACK,
        ApplyState.RECOVERY_REQUIRED,
        ApplyState.CANCELLED,
    ),
    ApplyState.PREPARING: _states(
        ApplyState.WRITING,
        ApplyState.ROLLING_BACK,
        ApplyState.RECOVERY_REQUIRED,
        ApplyState.CANCELLED,
    ),
    ApplyState.WRITING: _states(
        ApplyState.CAPTURING_LIVE_SOURCE,
        ApplyState.ROLLING_BACK,
        ApplyState.RECOVERY_REQUIRED,
    ),
    ApplyState.CAPTURING_LIVE_SOURCE: _states(
        ApplyState.VERIFYING_LIVE,
        ApplyState.ROLLING_BACK,
        ApplyState.RECOVERY_REQUIRED,
    ),
    ApplyState.VERIFYING_LIVE: _states(
        ApplyState.COMMITTED, ApplyState.ROLLING_BACK, ApplyState.RECOVERY_REQUIRED
    ),
    ApplyState.COMMITTED: frozenset(),
    ApplyState.ROLLING_BACK: _states(ApplyState.ROLLED_BACK, ApplyState.RECOVERY_REQUIRED),
    ApplyState.ROLLED_BACK: frozenset(),
    ApplyState.RECOVERY_REQUIRED: _states(ApplyState.ROLLING_BACK),
    ApplyState.CANCELLED: frozenset(),
    ApplyState.BLOCKED: frozenset(),
}

UPDATER_TRANSITIONS = {
    UpdaterState.NOT_CHECKED: _states(
        UpdaterState.CHECKING, UpdaterState.PRODUCTION_CHANNEL_UNPUBLISHED
    ),
    UpdaterState.CHECKING: _states(
        UpdaterState.UP_TO_DATE,
        UpdaterState.NO_UPDATE,
        UpdaterState.UPDATE_AVAILABLE,
        UpdaterState.FAILED,
        UpdaterState.PRODUCTION_CHANNEL_UNPUBLISHED,
    ),
    UpdaterState.UP_TO_DATE: _states(UpdaterState.CHECKING),
    UpdaterState.UPDATE_AVAILABLE: _states(UpdaterState.DOWNLOADING, UpdaterState.CHECKING),
    UpdaterState.DOWNLOADING: _states(
        UpdaterState.VERIFYING_SIGNATURE,
        UpdaterState.INCOMPLETE_DOWNLOAD,
        UpdaterState.FAILED,
    ),
    UpdaterState.VERIFYING_SIGNATURE: _states(
        UpdaterState.INSTALLING, UpdaterState.INVALID_SIGNATURE, UpdaterState.FAILED
    ),
    UpdaterState.INSTALLING: _states(
        UpdaterState.RESTART_REQUIRED, UpdaterState.UPDATED, UpdaterState.FAILED
    ),
    UpdaterState.RESTART_REQUIRED: _states(UpdaterState.UPDATED),
    UpdaterState.UPDATED: _states(UpdaterState.CHECKING),
    UpdaterState.NO_UPDATE: _states(UpdaterState.CHECKING),
    UpdaterState.INVALID_SIGNATURE: _states(UpdaterState.CHECKING),
    UpdaterState.INCOMPLETE_DOWNLOAD: _states(UpdaterState.CHECKING),
    UpdaterState.FAILED: _states(UpdaterState.CHECKING),
    UpdaterState.PRODUCTION_CHANNEL_UNPUBLISHED: _states(UpdaterState.CHECKING),
}


def state_model() -> dict[str, dict[str, list[str]]]:
    """Return the serializable authoritative transition model used by product surfaces."""

    models: dict[str, Mapping[StrEnum, frozenset[StrEnum]]] = {
        "behavior": BEHAVIOR_TRANSITIONS,
        "episode": EPISODE_TRANSITIONS,
        "verification": VERIFICATION_TRANSITIONS,
        "regression": REGRESSION_TRANSITIONS,
        "repair_workspace": REPAIR_WORKSPACE_TRANSITIONS,
        "candidate": CANDIDATE_TRANSITIONS,
        "apply": APPLY_TRANSITIONS,
        "updater": UPDATER_TRANSITIONS,
    }
    return {
        name: {
            str(previous): sorted(str(current) for current in allowed)
            for previous, allowed in transitions.items()
        }
        for name, transitions in models.items()
    }


_TERMINAL_EVIDENCE_REQUIRED: frozenset[StrEnum] = frozenset(
    {
        VerificationState.PASSED,
        VerificationState.FAILED,
        VerificationState.INCONCLUSIVE,
        VerificationState.RUNTIME_UNAVAILABLE,
        RegressionState.CONFIRMED,
        RegressionState.DISMISSED,
        RegressionState.RESOLVED,
        CandidateState.VALIDATED,
        CandidateState.REJECTED,
        CandidateState.APPLIED,
        CandidateState.RETAINED_AFTER_ROLLBACK,
        ApplyState.COMMITTED,
        ApplyState.ROLLED_BACK,
        ApplyState.RECOVERY_REQUIRED,
        ApplyState.BLOCKED,
        UpdaterState.UPDATED,
        UpdaterState.INVALID_SIGNATURE,
        UpdaterState.INCOMPLETE_DOWNLOAD,
        UpdaterState.FAILED,
    }
)


def transition(
    transitions: Mapping[StateT, frozenset[StateT]],
    previous: StateT,
    current: StateT,
    *,
    reason: str,
    evidence: tuple[str, ...] | list[str] = (),
    timestamp: datetime | None = None,
) -> TransitionRecord[StateT]:
    """Validate and describe one authoritative transition.

    Callers persist the returned timestamp, reason, and evidence in their native
    entity/event model. This function never silently permits an unknown edge.
    """

    if not reason.strip():
        raise TransitionError(previous, current, "WORKFLOW_TRANSITION_REASON_REQUIRED")
    allowed = transitions.get(previous)
    if allowed is None or current not in allowed:
        raise TransitionError(previous, current, "WORKFLOW_TRANSITION_INVALID")
    normalized_evidence = tuple(item.strip() for item in evidence if item.strip())
    if current in _TERMINAL_EVIDENCE_REQUIRED and not normalized_evidence:
        raise TransitionError(previous, current, "WORKFLOW_TRANSITION_EVIDENCE_REQUIRED")
    at = timestamp or datetime.now(UTC)
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    return TransitionRecord(previous, current, at, reason.strip(), normalized_evidence)

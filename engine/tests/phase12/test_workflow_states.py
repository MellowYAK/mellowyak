from __future__ import annotations

import pytest

from mellowyak_engine.workflow.states import (
    APPLY_TRANSITIONS,
    BEHAVIOR_TRANSITIONS,
    CANDIDATE_TRANSITIONS,
    EPISODE_TRANSITIONS,
    REGRESSION_TRANSITIONS,
    REPAIR_WORKSPACE_TRANSITIONS,
    UPDATER_TRANSITIONS,
    VERIFICATION_TRANSITIONS,
    ApplyState,
    TransitionError,
    UpdaterState,
    VerificationState,
    transition,
)

MACHINES = (
    BEHAVIOR_TRANSITIONS,
    EPISODE_TRANSITIONS,
    VERIFICATION_TRANSITIONS,
    REGRESSION_TRANSITIONS,
    REPAIR_WORKSPACE_TRANSITIONS,
    CANDIDATE_TRANSITIONS,
    APPLY_TRANSITIONS,
    UPDATER_TRANSITIONS,
)


@pytest.mark.parametrize("machine", MACHINES)
def test_every_declared_transition_is_accepted(machine):
    for previous, targets in machine.items():
        for current in targets:
            record = transition(
                machine,
                previous,
                current,
                reason="phase12.test.transition",
                evidence=["phase12:test-evidence"],
            )
            assert record.previous == previous
            assert record.current == current
            assert record.timestamp.tzinfo is not None


def test_impossible_apply_transition_fails_closed():
    with pytest.raises(TransitionError, match="WORKFLOW_TRANSITION_INVALID"):
        transition(
            APPLY_TRANSITIONS,
            ApplyState.AWAITING_CONFIRMATION,
            ApplyState.COMMITTED,
            reason="phase12.test.invalid",
            evidence=["phase12:test-evidence"],
        )


def test_terminal_result_requires_evidence():
    with pytest.raises(TransitionError, match="WORKFLOW_TRANSITION_EVIDENCE_REQUIRED"):
        transition(
            VERIFICATION_TRANSITIONS,
            VerificationState.RUNNING,
            VerificationState.PASSED,
            reason="phase12.test.pass",
        )


def test_updater_states_are_distinct_and_reachable():
    sequence = (
        (UpdaterState.NOT_CHECKED, UpdaterState.CHECKING),
        (UpdaterState.CHECKING, UpdaterState.UPDATE_AVAILABLE),
        (UpdaterState.UPDATE_AVAILABLE, UpdaterState.DOWNLOADING),
        (UpdaterState.DOWNLOADING, UpdaterState.VERIFYING_SIGNATURE),
        (UpdaterState.VERIFYING_SIGNATURE, UpdaterState.INSTALLING),
        (UpdaterState.INSTALLING, UpdaterState.RESTART_REQUIRED),
        (UpdaterState.RESTART_REQUIRED, UpdaterState.UPDATED),
    )
    for previous, current in sequence:
        record = transition(
            UPDATER_TRANSITIONS,
            previous,
            current,
            reason="phase12.test.updater",
            evidence=["phase12:updater"] if current == UpdaterState.UPDATED else [],
        )
        assert record.current == current

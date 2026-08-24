# ADR-0008: non-verified behavior candidates

- Status: Accepted
- Date: 2026-08-24

## Context

Impacted test names can suggest behavior language, but a test filename is not proof that a behavior is correctly defined, protected or verified.

## Decision

Phase 3 may derive a local `BehaviorCandidate` from a non-stale impacted test. Its only states are `CANDIDATE`, `DISMISSED` and `PROMOTED_STUB`. The UI and API always report `not_protected: true` and `verification: not_configured`.

Keep restores candidate status, Dismiss records dismissal, and Prepare creates only a future-work stub. No action creates a Protected Behavior, evidence, Last Known Good state, PASS/FAIL result or verification gate.

## Consequences

- Candidate discovery is useful but cannot be presented as protection.
- Promotion to a real behavior is deferred to Phase 4 and requires a new schema and evidence semantics.
- Candidate facts remain project-scoped and restart-persistent.


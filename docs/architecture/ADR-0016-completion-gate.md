# ADR-0016 — Immutable local Completion Gate

Status: Accepted — 2026-08-24

## Decision

MellowYak's local gate records immutable NOT_EVALUATED/RECHECK_REQUIRED/VERIFYING/BLOCKED/NEEDS_REVIEW/VERIFIED_COMPLETE/STALE decisions. A FAIL blocks; an unresolved, error, cancelled, or human-review item needs review; missing required results require a recheck; stale identity stays stale. Suggested checks do not block.

VERIFIED_COMPLETE requires a fresh plan, matching behavior/baseline bindings, current exact source identity, all REQUIRED items in AUTOMATED_PASS or HUMAN_ATTESTED_PASS, and intact current evidence for automatic passes. Its UI limitation states that only the known current Protection Plan is covered. The gate does not control Git, CI, IDEs, or agents in Phase 5.

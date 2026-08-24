# ADR-0015 — Evidence-supported regression decisions

Status: Accepted — 2026-08-24

## Decision

`REGRESSION DETECTED` requires a current REQUIRED browser replay item, an active compatible accepted baseline for the current PROTECTED behavior version, an exact current source identity, and at least one supported deterministic assertion with result FAIL. Runtime failures, stale source, missing selectors, unsupported assertions, timeouts, browser errors, screenshots, and human-only notes cannot create this claim.

Regression findings are append-only decision records. Resolution links the original failed run to a later passing run; it never deletes the failure or replaces Last Known Good.

# ADR-0009: Protected behavior versioning

Date: 2026-08-24
Status: Accepted

## Decision

A behavior owns a stable identity and points at an immutable current `behavior_versions` row. Editing creates a new row with a deterministic content digest and `supersedes_version_id`; existing versions are never updated. Lifecycle is `DRAFT`, `PROTECTED`, or `ARCHIVED`. Only a human-accepted baseline for the current version makes the behavior `PROTECTED`. A definition change makes the prior baseline stale and the behavior a Draft.

Candidate preparation creates only a Draft and records candidate provenance. Criticality is descriptive and never a correctness verdict. Stored expected assertions are Phase 4 definitions only and are not executed.

## Consequences

History, definition identity, and Last Known Good lineage remain explainable. Phase 5 can later run fresh checks without reinterpreting a recording as verification.

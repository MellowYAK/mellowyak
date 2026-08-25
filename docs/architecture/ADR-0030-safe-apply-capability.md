# ADR-0030: Safe Apply capability boundary

Status: Accepted — 2026-08-25

## Decision

Analysis, validation, preparation, commit, and rollback are separate capabilities. `COMMIT_APPLY` requires a validated candidate, fresh live-source preflight, explicit deliberate confirmation, and a short-lived one-time nonce bound to transaction, project, candidate, and source-manifest digest.

No permanent or automatic Apply permission exists. A stale source, digest mismatch, relocation, unsafe path, unavailable project, or active transaction blocks all writes.

## Consequences

Reading or validating a candidate grants no live write access. Every Apply is a single visible transaction with an exact scope.

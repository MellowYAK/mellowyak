# ADR-0032: Transaction-scoped rollback

Status: Accepted — 2026-08-25

## Decision

Rollback may restore only paths changed by MellowYak's current Apply transaction, using the freshly created pre-apply Safety Snapshot. Restoration uses the same safe path resolution, atomic replacement, journaling, digest verification, and directory durability rules as Apply. Unrelated paths are never restored.

Rollback completion requires byte identity for every affected path. Failure becomes `FAILED_RECOVERY_REQUIRED`, raises a critical local alert, preserves evidence, and creates a Recovery Bundle.

## Consequences

This is not a general historical restore feature and never copies Last Known Good over the project.

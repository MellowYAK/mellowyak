# ADR-0031: Durable Apply journal and crash recovery

Status: Accepted — 2026-08-25

## Decision

Before the first write MellowYak creates a mode-0600, atomically replaced, fsynced JSON journal. It records transaction/source/safety identities, ordered operations, original and candidate hashes, state changes, and timestamps. Each completed operation is durably recorded.

Startup inspects incomplete transactions. No-write transactions are cancelled; partial writes roll back; completed writes without live verification become recovery-required; incomplete rollback continues only while safe preconditions hold. Success is never inferred after a crash without fresh verification.

## Consequences

Crash recovery is deterministic but cannot promise universal whole-filesystem atomicity. Unprovable state stops writes and produces a redacted Recovery Bundle.

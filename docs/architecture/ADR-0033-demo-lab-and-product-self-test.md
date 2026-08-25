# ADR-0033: Demo Lab and Product Self-Test

Status: Accepted — 2026-08-25

## Decision

Demo Lab is an explicitly created, clearly labeled, offline, dependency-light, non-Git synthetic project guarded by a fixture marker. Its controls cover regression, invalid and valid candidates, Apply, post-apply failure, rollback, and reset. They are unavailable to real projects.

Product Self-Test runs only in a generated temporary fixture. It checks snapshot/dedup, candidate identity, validation, Safety Snapshot, journal, Apply, live verification, rollback, restart loading, hash integrity, no network, no process ownership leak, and cleanup. It records only executed results and exports a redacted local report.

## Consequences

Operators can review the complete loop without a private project. Demo and self-test data never becomes an implicit real project and never uses a model or remote service.

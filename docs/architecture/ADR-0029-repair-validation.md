# ADR-0029: Repair validation

Status: Accepted — 2026-08-25

## Decision

Candidate validation is bound to candidate digest, workspace manifest digest, approved Runtime Profile versions, and an explicit validation policy. The original failed Probe is ordered first; all required impacted checks must pass. Suggested checks do not block unless promoted. Unknown external state remains inconclusive.

Workspace execution uses executable-plus-argv without a shell, a workspace working directory, a sanitized environment, bounded output/time, loopback-only policy, cancellation, and owned-process cleanup. Workspace evidence is independent from baseline and live verification evidence.

## Consequences

A PASS becomes `VALIDATED` only for the exact workspace bytes. Any later edit makes it stale. A workspace PASS is never proof that the live project passes.

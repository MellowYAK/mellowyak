# ADR-0014 — Local verification adapters

Status: Accepted — 2026-08-24

## Decision

The typed verification boundary accepts availability, a revision-bound request, cancellation, bounded execution, normalized results, evidence, limitations, and cleanup. Phase 5 implements Browser Replay and explicit Human Attestation. A general local-command adapter is intentionally omitted because safely approving arbitrary project executables is outside this phase.

Browser Replay uses the accepted baseline's steps and assertion definitions in a new ephemeral Chromium context. It accepts only the configured loopback HTTP origin, reuses no cookies or storage, stores no headers or bodies, redacts inputs before screenshots, closes all child resources, and creates a separate CURRENT_VERIFICATION bundle. Selector failures and unavailable runtimes are inconclusive, not regressions.

## Bounds

Browser concurrency never exceeds two (the initial runner is sequential), behavior timeout is 120 seconds, run timeout is 15 minutes, assertions are capped at 100, and a current evidence bundle is capped at 250 MiB.

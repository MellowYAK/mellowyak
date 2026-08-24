# ADR-0011: Local browser runtime

Date: 2026-08-24
Status: Accepted

## Decision

Phase 4 uses a lazily started Python Playwright Chromium worker. It starts only after user action, uses an ephemeral context, blocks downloads and service workers, and permits only the exact approved explicit-port `http://127.0.0.1` or `http://localhost` origin. The worker is owned by the engine and closes contexts/browser processes on stop, cancel, crash recovery, or engine shutdown.

The desktop package stages a matching Chromium executable and Playwright runtime. System Chrome is a development fallback, not packaged-runtime proof. No project shell command is executed and the user starts the local application separately.

## Consequences

Browser startup does not add engine-startup network traffic. External navigation is aborted. Windows, Linux, and Apple Silicon remain unverified until their package jobs actually run.

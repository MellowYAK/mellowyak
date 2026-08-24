# ADR-0025 — Universal probes and deterministic signal semantics

Status: Accepted — 2026-08-24

## Context

Phase 5 established Browser Replay and Human Attestation, but protected behavior is not limited to a
browser. APIs, CLIs, processes, and existing tests need one versioned evidence contract and must feed
the existing Protection Plan and regression engine rather than a parallel verifier.

## Decision

A stable `probe_definition` points to an immutable current `probe_version`. Runs bind the exact probe
version to a source snapshot/identity, optional Episode, and optional Runtime Profile version. The
runner enforces approval, timeout, cancellation, bounded evidence, retry policy, and child cleanup.

Supported Phase 7 probe types are:

- Browser — delegates to the existing bounded Browser Replay implementation when a compatible
  approved baseline and runtime are available;
- API — loopback HTTP by default, bounded assertions, and no authorization/cookie/secret fields;
- CLI — approved executable plus argv, confined working directory, no shell;
- Process — bounded liveness/exit/loopback-port or health observations for an approved process;
- Test — an approved existing test target, not the entire suite by default;
- Manual — explicit human attestation with exact snapshot/time and an automation limitation.

Definitions, expected results, retry/evidence policy, source/runtime links, approval, and limitations
are versioned. HTTP request/response bodies are not retained by default. CLI and test stdout/stderr are
bounded and sanitized. The full user environment is never inherited or persisted.

Impact-based selection follows existing Protection Plan and graph provenance in this order: direct
human links, runtime-observed links, parsed static links, relevant tests, critical always-recheck
behaviors, history, heuristics, then unknown review items. Selection is capped and reports truncation
and unknown boundaries; large fan-out never implies that every dependent surface was checked.

Signal classification is deterministic:

- file or impact change only: `WATCH`;
- one failure or anomaly without a comparable accepted baseline: `SUSPECTED`;
- a current related crash, or a prior PASS followed by one current FAIL: `HIGH`;
- comparable accepted PASS followed by reproducible current FAIL, or an existing supported Phase 5
  regression decision: `CONFIRMED`.

The user-facing product never displays a numeric confidence percentage. A confirmed result explains
what worked, the accepted Save Point, the exact check and identities, expected versus observed,
reproduction evidence, and remaining unknowns. It does not claim root cause unless proven.

## Consequences

A raw snapshot cannot become a behavioral baseline. “This works — save it” requires a passing
configured probe or explicit human attestation before creating a pinned known-good milestone.
Flakiness and unsupported execution remain inconclusive and cannot create `CONFIRMED`.

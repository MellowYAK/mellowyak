# ADR-0034: Technical Preview runtime and support boundary

Status: accepted for Phase 9
Date: 2026-08-25

## Context

The Phase 8 engine can validate a repair and deliberately apply it safely, but a
Technical Preview also needs coherent onboarding, long-running desktop lifecycle,
disconnected-project recovery, diagnostics, support export, installer migration, and
update evidence. Those surfaces can accidentally leak source/path information or
weaken identity and write safeguards.

## Decision

- Persist onboarding, location history, diagnostics/support metadata, notification
  activation, updater/package validation, and activity preferences in schema 0009.
- Existing installations skip first run; a user may replay it explicitly.
- Reconnect and relocate update only local metadata after project identity matches.
  They never move, copy, delete, or edit source.
- Native tray/notification payloads use translated summaries and stable identifiers,
  never source, evidence, tokens, or full paths.
- Validate every activation route against an allowlist and existing local entity.
- Support export is bounded/redacted and contains summaries rather than source or
  evidence bytes.
- Closing a window hides the UI; explicit Quit terminates the supervised sidecar.
- Production updates remain HTTPS and signature-enforced. Loopback HTTP and ephemeral
  keys are permitted only in an isolated validator that cannot alter production
  configuration.
- Platform workflow configuration is not runtime verification. Status is recorded
  per native platform.
- Activity modes may reduce polling, animation, and background work, but cannot
  disable recovery, integrity, identity, Apply, or explicit verification safeguards.

## Consequences

The Technical Preview can remain useful in the background and produce safer support
information without becoming a remote service. More metadata is persisted locally,
so migration, retention, deletion, and redaction require explicit tests. Public
release remains blocked on platform-native package, signing, updater, and operator
acceptance evidence.

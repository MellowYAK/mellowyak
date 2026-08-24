# ADR-0022 — Versioned multi-runtime profiles

Status: Accepted — 2026-08-24

## Context

A project can contain several independently useful runtimes. A desktop product may have a
Node/Tauri frontend and a Python engine; a service may expose an API and run a separate worker.
Language frequency is not reliable enough to decide which runtime is primary, and a saved shell
string is not a safe execution contract.

## Decision

Each project owns zero or more stable `runtime_profiles`. A profile points at one immutable current
`runtime_profile_versions` record. Editing a profile appends a numbered version so a probe run can
remain bound to the exact runtime definition that produced its evidence.

A profile version records:

- runtime and adapter type/version;
- managed, external, or manual execution mode;
- executable reference and argument array as separate fields;
- a project-relative working directory;
- runtime/dependency fingerprints;
- bounded health, port, and test definitions;
- names of approved environment variables, never their secret values;
- a local network policy, approval time, detection time, and explicit limitations.

The user chooses one primary profile and may keep secondary profiles. Detection only proposes
candidates; it does not start runtimes, install dependencies, or approve package scripts. Existing
projects without a profile remain source-monitored and display `Setup incomplete`.

All adapters implement the same bounded contract: detect, describe, validate, availability, start,
observe, run a supported probe, stop, fingerprint, sanitize, and cleanup. An unavailable or failed
adapter reports an explicit limitation and fails open: source monitoring, Episodes, snapshots, and
the desktop application continue.

Runtime execution uses an executable plus argv with no shell, a confined working directory, a
minimal allow-listed environment, bounded output/time, cancellation, and child cleanup. Provider
credentials, registry tokens, authentication headers, complete environments, and raw configuration
dumps are prohibited.

## Adapter scope

- Python: metadata and executable support for common manifests, local environments, versions,
  entry points, and pytest indicators.
- Node.js: metadata and executable support for package manifests, package-manager identity,
  versions, scripts, and test-framework indicators. Scripts require approval; install is never run.
- PHP: Composer/PHPUnit metadata plus bounded PHP CLI metadata when available. Raw `phpinfo()` and
  configuration values are never stored.
- Generic process: only an explicitly approved local executable/process.
- Ruby and Java: metadata detection may report execution unsupported in Phase 7.

## Consequences

Evidence can be compared only when source and runtime identities are compatible. A profile edit does
not rewrite historical evidence. Multiple runtimes add setup choices, so the wizard must keep novice
copy concise and expose technical details on demand. Runtime availability is platform-specific and
must be reported rather than inferred.

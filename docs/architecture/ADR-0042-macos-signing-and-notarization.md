# ADR-0042: macOS signing and notarization

Status: accepted policy; production execution depends on external Apple credentials.

## Decision

Public macOS artifacts require a Developer ID Application identity, hardened runtime, secure
timestamp, minimal entitlements, successful `notarytool` submission and a stapled ticket. The build
must not enable JIT, unsigned executable memory, disabled library validation or `get-task-allow`.

When credentials are absent, local packaging may use ad-hoc signing for structural validation only.
Reports disclose only credential presence/counts, never values or identity text, and label public
distribution `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.

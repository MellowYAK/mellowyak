# Security policy

MellowYak Phase 1 is a local foundation, not a production-security certification.

## Reporting

Do not publish a suspected vulnerability or private project evidence in a public issue. Use GitHub's private vulnerability reporting for this repository when available. Include version, platform, reproduction steps and impact; omit real source code, credentials and personal evidence.

## Implemented boundary

- The engine accepts loopback hosts only and selects a dynamic port.
- Every non-handshake API requires a random per-launch Bearer token.
- The token is process-memory-only and is redacted from application logs.
- Origin access is restricted to the desktop shell/development origins.
- The engine is supervised and stopped with its parent desktop process.
- Phase 1 has no remote account, cloud synchronization or telemetry uploader.

The application is currently unsigned and unnotarized. Packages produced by development builds are not release artifacts. Future connectors, execution arms and team services require separate threat models and explicit user consent.

## Prohibited legacy sources

APC `_codex_read.php`, `model_context.php`, and installation-wide authorization semantics from `api/model.php` and `api/ingest.php` are security blocked. They must not be introduced into MellowYak.

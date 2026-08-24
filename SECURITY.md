# Security policy

MellowYak Phase 3 is a local foundation, not a production-security certification.

## Reporting

Do not publish a suspected vulnerability or private project evidence in a public issue. Use GitHub's private vulnerability reporting for this repository when available. Include version, platform, reproduction steps and impact; omit real source code, credentials and personal evidence.

## Implemented boundary

- The engine accepts loopback hosts only and selects a dynamic port.
- Every non-handshake API requires a random per-launch Bearer token.
- The token is process-memory-only and is redacted from application logs.
- Origin access is restricted to the desktop shell/development origins.
- The engine is supervised and stopped with its parent desktop process.
- Project/change/impact APIs are scoped by project identity and reject cross-project records.
- Source traversal is confined to the selected repository; ignored, sensitive, binary, oversized and escaping-symlink inputs are excluded or reported.
- Reverse impact uses bounded deterministic traversal. Unknown and stale edges terminate authoritative traversal.
- Context Receipts persist metadata only, include zero source bytes, exclude sensitive content and open no network connection.
- Behavior candidates are explicitly unverified and not protected.
- Desktop setup starts the packaged engine asynchronously. Slow cold starts return `ENGINE_STARTING` to the UI instead of blocking AppKit setup or aborting the desktop process.
- The desktop updater accepts metadata only from the HTTPS MellowYak GitHub Releases endpoint and refuses update bundles that do not match the embedded public signing key. The private updater key is prohibited from source history and build logs.
- Phase 3 has no remote account, cloud synchronization, telemetry uploader, model call, connector, browser automation, test execution or completion gate. The release update check is the only configured non-loopback application request.

Local development packages remain unsigned and unnotarized and are not release artifacts. The updater minisign key does not replace required macOS notarization or Windows code signing. A public production release remains blocked until the platform signing credentials and updater private key are configured as repository secrets. Future connectors, execution arms and team services require separate threat models and explicit user consent.

## Prohibited legacy sources

APC `_codex_read.php`, `model_context.php`, and installation-wide authorization semantics from `api/model.php` and `api/ingest.php` are security blocked. They must not be introduced into MellowYak.

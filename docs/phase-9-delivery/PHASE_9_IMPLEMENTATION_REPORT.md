# Phase 9 implementation report

## Outcome

Phase 9 converts the verified Phase 8 local core into an installable Technical
Preview candidate for Intel macOS. It adds an upgrade-safe first run, disconnected
project recovery, dynamic tray state, route-safe notifications, diagnostics,
redacted support export, deterministic update validation, lifecycle controls,
activity modes, platform build configuration, and a complete delivery package.

The work remains local-first. It adds no model/provider SDK, prompt reader, cloud
sync, account, telemetry uploader, automatic source mutation, automatic Apply,
deployment, APC runtime dependency, or real-project fixture.

## Implemented product surfaces

### First Run

- Persists onboarding completion in migration `0009_technical_preview_readiness`.
- Offers project selection or a synthetic Demo Lab without silently adding source.
- Explains background behavior and privacy before completion.
- Supports replay from Technical Preview settings.
- Existing Phase 8 installations skip first run without losing identity or data.

### Disconnected Projects

- Keeps project history visible when the source root is unavailable.
- Previews stored project identity without revealing full paths in native surfaces.
- Reconnect accepts only a matching project identity.
- Relocate updates the recorded root while preserving history and never moving,
  copying, deleting, or rewriting source.
- Mismatch is a hard stop with no source write.

### Tray and lifecycle

- Derives translated native menu state from local project events.
- Provides monitoring, attention, project navigation, diagnostics, show/hide, and
  explicit Quit actions without placing source content or full paths in the menu.
- A second launch focuses the existing process rather than starting a second engine.
- Closing the final window hides it while the supervised engine remains available;
  explicit Quit terminates the desktop and owned sidecar.

### Notifications

- Notification payloads use stable local identifiers, never paths or source.
- Activation routes pass through a strict allowlist and entity lookup.
- Forged, stale, malformed, and cross-project routes are rejected safely.
- In-app alerts remain available when native notification activation is unavailable.
- The deterministic activation route is verified; a physical operating-system
  notification click is not claimed by this run.

### Diagnostics and support

- Adds storage-integrity, schema, runtime, package, updater, and local-status checks.
- Diagnostic copy data is bounded and redacted.
- Support bundles contain summaries, hashes, aliases, and redacted logs only.
- Bundles exclude source/evidence bytes, tokens, cookies, credentials, private keys,
  complete environment data, and full home paths.

### Updater and packaging

- Adds a disposable loopback-only signer/metadata validator with ephemeral keys.
- Proves valid signature acceptance and tamper, wrong-key, and interrupted-download
  rejection without altering production updater configuration.
- Configures macOS Intel/Apple Silicon, Windows x64, and Linux x64 build jobs and
  immutable artifact manifests.
- Adds minimal macOS Hardened Runtime entitlements and signing configuration without
  embedding credentials or claiming signing/notarization.

### Performance and accessibility

- Adds Active, Balanced, and Battery Saver preferences while retaining safety,
  recovery, project identity, and explicit verification behavior.
- Fixes a translated-alert polling regression by memoizing the i18n callbacks;
  packaged idle CPU fell from approximately 48% combined to 0.1% combined.
- Provides visible focus, meaningful keyboard order, reduced-motion behavior,
  zoom/reflow support, English base strings, Hebrew parity, and full Hebrew RTL.
- All visible GUI text remains translation-key driven.

## Storage and migration

Migration `0009_technical_preview_readiness` adds eight persisted areas:

1. onboarding state;
2. project location history;
3. diagnostic runs;
4. support bundle records;
5. notification activation events;
6. update validation runs;
7. package acceptance runs;
8. Technical Preview preferences.

The deterministic migration matrix covers empty databases and every predecessor
from 0001 through 0008. All paths reach 0009 and preserve prior records.

## APC boundary

No APC source, server, database, credentials, deployment, or runtime dependency was
read or changed in Phase 9. The product foundation inherited from earlier,
documented APC extraction phases remains subject to ADR-0003 and the migration
matrix. Phase 9 functionality was implemented directly in MellowYak so it is
portable and open-source safe.

# Phase 9 Execution Plan

Date: 2026-08-25

## Goal

Turn the verified Phase 8 local core into a coherent, source-safe Technical Preview candidate without connecting a real project, publishing a release, pushing Git, or changing APC.

## Bounded work

1. Add migration `0009_technical_preview_readiness` for onboarding, project-location history, diagnostic/support/update/package runs, notification activation, and activity preferences.
2. Complete first run with persisted completion and replay, retaining an upgrade-safe skip for existing installations.
3. Add a disconnected-project manager with identity preview, reconnect and relocate rejection on mismatch, retained-history summaries, and deletion preview.
4. Derive a privacy-safe tray state from local events and synchronize a dynamic translated native menu without exposing paths or source.
5. Validate notification routes in the engine and route activation to the existing desktop instance; retain in-app alerts when OS activation cannot be automated.
6. Persist close behavior and activity mode; preserve journals during shutdown and terminate children on explicit Quit.
7. Add Diagnostics, storage-integrity checks, safe diagnostics copy data, and redacted support bundles with canary-secret regression tests.
8. Add a disposable, loopback-only signed updater fixture and record production updater limitations without changing its public key.
9. Add clean-install, Phase 8 upgrade, same-version reinstall, removal-safety, package inventory, and current-platform packaged validators.
10. Measure package/startup/idle behavior and remove only demonstrably redundant build content.
11. Complete keyboard/focus/reduced-motion/zoom/RTL behavior and translation-key-only visible UI.
12. Configure Intel/Apple Silicon macOS, Windows x64, and Linux x64 build jobs with immutable manifests and honest remote-runtime status.
13. Add signing/notarization templates and audit scripts without credentials or fake attestations.
14. Run the full Phase 1–9 source and current-platform package gates, create deterministic screenshots and reports, then install only the validated app after backing up the current app.

## Architecture decisions

- All product data stays under the isolated local application data root.
- Reconnect and relocate never move, copy, or delete source; identity mismatch is a hard stop.
- Native route payloads contain stable local identifiers only and are allowlisted before navigation.
- Support exports contain summaries, hashes, aliases, and redacted logs; never source/evidence bytes, tokens, cookies, credentials, or full home paths.
- The production updater remains HTTPS and signature-enforced. Loopback/insecure transport exists only in a disposable test configuration.
- Tray refresh is driven by local state-change events; it does not include full paths or evidence.
- The supported runtime gate for this run is Intel macOS. Other platforms are workflow-configured until their native jobs run.

## Exclusions

No AI/model/provider SDK, prompts, chat connector, cloud sync, account, billing, autonomous source mutation, automatic Apply, Git push/commit generation for user projects, deployment, public release, or real-project validation.

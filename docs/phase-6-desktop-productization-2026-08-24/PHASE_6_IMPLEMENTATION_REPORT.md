# MellowYak Phase 6 — Desktop Productization Report

Date: 2026-08-24  
Branch: `product/desktop-productization-tray-notifications`  
Phase 5 base: `7fed80a136c52e00f15155f688bc099f925d9699`  
Safety tag: `phase-5-verification-regression-gate-verified-2026-08-24`

## Outcome

Phase 6 turns the verified local engine from Phase 1–5 into a coherent desktop product. It adds a global command center, project lifecycle operations, durable local alerts, persistent notification preferences, quiet mode, native tray/background lifecycle, start-at-login control, truthful capability modes, English/Hebrew RTL product surfaces, and a portable documentation bundle.

The implementation remains local-first. It does not add accounts, cloud sync, source upload, evidence upload, telemetry upload, or an external control plane. The APC repository was read-only and was not modified.

## Product shell and Command Center

The desktop header now uses the packaged MellowYak icon and provides global Home, Projects, Alerts, and Settings navigation. The Command Center is populated from real project and alert records and reports monitored/paused projects, active regressions, blocked gates, needs-review events, unread alerts, project health, and recent resolved outcomes. It does not invent health or completion states.

## Projects and lifecycle

The Projects screen supports local search, status filters, open project, open source folder, scan, pause/resume monitoring, per-project alert mute, disconnect, reconnect API, relocation API, and destructive local-data deletion. Disconnect preserves MellowYak records and pauses monitoring. Local-data deletion requires the exact project name and removes only MellowYak-owned database/evidence records. A dedicated automated test confirms that a source sentinel and Git HEAD remain unchanged.

## Capability modes

Each project exposes a derived capability mode:

- `local_source`: Git observation, source scan, impact, protected behaviors, local evidence, and human attestation.
- `local_source_with_runtime`: adds browser capture/replay, deterministic assertions, regression detection, and completion gate support.

Future or unavailable capabilities remain visibly unavailable. Automatic browser replay remains explicitly unavailable in the current product even when a local runtime is configured; the existing browser replay capability is bounded and operator-driven.

## Alerts Center

Alerts are stored in SQLite, deduplicated by a stable key, project-scoped when applicable, and carry category, severity, translation keys, translation parameters, source entity identifiers, and a local route. The inbox supports All, Unread, Attention, and Resolved filters plus open, read/unread, resolve, unread-count, and clear-resolved actions.

Verification can create a regression alert from an actual supported regression finding. Gate evaluation creates BLOCKED, NEEDS_REVIEW, or VERIFIED_COMPLETE alerts from the real gate state. Notification polling starts from an initial seen set so historical alerts are not re-notified merely because the app restarted.

## Quiet mode and notification preferences

Notification preferences persist per installation and cover regression, blocked gate, human review, project error, verified completion, resolved regression, project/behavior-name visibility, detail privacy, and critical override. Per-project mute and category preferences are applied before native delivery. Quiet Mode persists independently of monitoring and supports one hour, until tomorrow, until turned off, and explicit end. Quiet Mode suppresses native delivery only; it does not pause project monitoring or remove persistent in-app alerts.

## Tray, background lifecycle, and startup

The Tauri shell now provides a native tray/menu-bar menu whose visible strings come from separate English and Hebrew translation files. It can restore/focus the main window, open Alerts or Settings, start/end Quiet Mode, and explicitly quit. A left-click restores the main window. A second application launch focuses the existing instance. Closing the main window hides it when background monitoring is enabled; explicit Quit terminates the sidecar engine. Start at Login uses the Tauri autostart plugin and reports the actual OS result to the UI.

## Native notifications

The desktop polls newly created persistent alerts, applies global preferences and Quiet Mode, translates title/body through the selected GUI catalog, and invokes the OS notification provider. A pending in-app destination is retained. Exact click callbacks from the native notification are not claimed as verified because the current cross-platform notification plugin does not expose a verified click callback in this implementation; the persistent in-app alert always contains the exact project/change route.

## Translation-only GUI contract

All React GUI text is rendered through translation keys. English is the base catalog and Hebrew has the same complete key set with document-level RTL. The repository check `python3 scripts/check_ui_translation_keys.py` rejects static JSX text and hardcoded accessible attributes. Native tray strings are also loaded from translation resources rather than being embedded in Rust UI construction.

## Database migration

Migration `0006_desktop_productization` adds:

- project disconnect/source-availability/notification-mute fields;
- `alerts`;
- `notification_preferences`;
- `project_notification_preferences`;
- `quiet_mode_state`;
- `application_preferences`;
- `project_lifecycle_events`;
- `project_disconnection_records`.

Migrations `0001` through `0005` are retained in order.

## Privacy and security

- The engine remains bound to authenticated loopback only.
- The GUI stores no session token in local storage.
- Source and Git content are never deleted by project lifecycle operations.
- MellowYak data stays under the application data root, separate from source.
- Notifications can hide project/behavior details.
- No cloud endpoint, analytics service, account flow, APC credential, private path, or user dataset was added.
- Screenshots use only synthetic public fixtures.

## APC extraction

Phase 6 reused product lessons rather than copying APC code. See `APC_EXTRACTION_AND_HANDOFF.md` for the detailed provenance and separation record.

## Verification summary

The exact commands and final evidence are recorded in `VERIFICATION_EVIDENCE.md`. The Phase 6 screenshot catalog is in `PHASE_6_SCREEN_GUIDE.md` and `MellowYak-Phase-6-Screen-Guide.pdf`.

At the operator's final direction, no additional automated test pass was run after the last notification-preference UI refinements. The final packaged build is therefore handed off for explicit manual operator acceptance; earlier validation evidence is retained and clearly scoped in the evidence document.

## Known limitations

- macOS is the only locally packaged platform in this run; Windows and Linux remain workflow-configured but runtime-unverified here.
- Signing, notarization, and public release publishing are out of scope and unverified.
- Native-notification click callbacks are not claimed as verified; in-app alert routing is exact.
- Tray menu status is currently a translated local-monitoring status, not a continuously rebuilt per-project submenu.
- Relocation and reconnect exist in the engine API; the current Projects menu exposes disconnect and local-data deletion, while reconnect/relocate require the later disconnected-project management surface.
- Complete blast-radius knowledge, automatic repair, external merge enforcement, accounts, cloud sync, MCP/CLI, and provider connectors remain future work.

## Phase 7 recommendation

Phase 7 should first close the explicitly recorded desktop limitations: a disconnected-project manager with reconnect/relocate UI, dynamic tray counts/status, verified native-notification click callbacks per platform, Windows/Linux runtime packaging verification, signing/notarization, and updater verification. Connectors and value measurement should follow only after those desktop guarantees are evidence-backed.

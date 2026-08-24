# Phase 6 execution plan

Date: 2026-08-24. Base: `7fed80a136c52e00f15155f688bc099f925d9699` on `product/desktop-productization-tray-notifications`.

1. **Application shell** — add translated Home, Projects, Alerts, and Settings navigation plus contextual Overview, Changes, Impact, Behaviors, and Evidence routes; use compact responsive sidebar and useful populated/empty states.
2. **Project lifecycle** — distinguish pause, notification mute, disconnect-with-history, relocation, reconnect, and deliberate deletion of MellowYak-only data; preserve repository bytes and Git identity and reference-count evidence deletion.
3. **Local state** — migration `0006_desktop_productization` adds alerts, global/per-project notification preferences, Quiet Mode, application preferences, lifecycle/disconnection audit records, and disconnected/availability project metadata.
4. **Alerts and notifications** — derive persistent deduplicated privacy-safe alerts from real local events; apply global settings, project mute, cooldown, Quiet Mode, and optional critical override before native delivery.
5. **Tray and lifecycle** — Tauri owns a translated native tray, close-to-hide or close-to-quit behavior, explicit Quit cleanup, single-instance focus, optional autostart, native notification click routing, badge/state updates, and engine-child termination.
6. **Deep links and settings** — validate internal project/entity routes at the local API boundary; expose authenticated settings/background/autostart capabilities without accepting cross-project identifiers.
7. **Product explanation** — add capability profiles, cross-project attention, project health, regression story, recent Changes, Impact defaults, focused behavior workflows, and clear next actions.
8. **Verification and delivery** — targeted lifecycle/alert/Quiet/security/tray/UI tests during implementation; one final full suite; deterministic PulsePlan screenshot fixture; real rendered screenshot guide; fresh macOS app/DMG and packaged background/notification fallback validation.

Phase 6 excludes connectors, MCP/CLI, accounts/cloud, source or evidence upload, automatic repair, external merge gates, public release, signing, and notarization.

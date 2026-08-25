# Phase 11M macOS execution plan

Date: 2026-08-25. Branch: `product/macos-native-hardening`. Source baseline:
`phase-10-product-truth-verified-2026-08-25`.

1. Preserve the Phase 10 product truth, API, schema, local-only boundary and translation-key-only
   English/Hebrew RTL contract while fixing the First Run React warning and the production bundle
   advisory.
2. Replace the Intel macOS PyInstaller one-file engine with a packaged one-directory resource,
   instrument startup, supervise an unexpected engine exit, and retain the existing sidecar path on
   Windows and Linux.
3. Harden native macOS lifecycle, tray, LaunchAgent autostart and exact notification activation without
   putting paths, source, credentials or evidence in OS-visible payloads.
4. Build a disposable Mac Acceptance Lab and filesystem-safety harness, then exercise safe Apply,
   rollback, recovery, cleanup and product self-test only against synthetic projects.
5. Exercise a two-version loopback-only updater with ephemeral keys and real macOS updater artifact
   shape. Keep the production endpoint and public key unchanged.
6. Add Intel macOS CI, signing/notarization detection and structural checks. Record Apple Silicon,
   physical Notification Center interaction and Developer ID notarization as unverified unless the
   required hardware or credentials are genuinely available.
7. Build fresh app/DMG artifacts, install only after mandatory gates pass, capture synthetic screens,
   write the delivery record, create one local commit, and add the annotated verification tag only if
   every mandatory Intel macOS gate passes. Do not push or publish.

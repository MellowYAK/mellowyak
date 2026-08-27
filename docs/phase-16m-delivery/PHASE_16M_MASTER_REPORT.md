# MellowYak Phase 16M Master Report

## Current verdict

- Product: `INTEL_MAC_PHYSICAL_ACCEPTANCE_BLOCKED`
- Distribution: physical acceptance pending; `PUBLIC_MAC_DISTRIBUTION_BLOCKED`
- Reason: the automated preparation is complete, but no physical operator action has been recorded yet.
- No verified Phase 16 tag exists and nothing was pushed.

## Git provenance

- Repository: `https://github.com/MellowYAK/mellowyak.git`
- Branch: `product/intel-mac-product-lock`
- Phase 14 starting tag and commit: `phase-14m-real-world-compatibility-verified-2026-08-26` / `b978b021a80af3410ef97cf2cf7d0e93dc697597`
- Phase 15 implementation checkpoint: `e137000800e19416131248b06b39d709c0f4191f`
- Build commit: `e0110dc53f83c8a0dfb3135de0bbf44c68f6bffb`
- Final build commit: pending physical acceptance.
- Evidence commit: pending physical acceptance.
- Final verified tag: not created.
- Unrelated Finder Alias files under the Phase 5 screenshot directory were preserved untracked and excluded.

## Product identity

- Version: `0.5.0-preview.2`
- Database head: `0011_baseline_lock_and_local_proof`
- Host: macOS `26.5.2` build `25F84`, Intel `x86_64`
- Node: `v26.7.0`; npm: `11.19.0`; Python: `3.11.5`; Rust/Cargo: `1.98.0`
- The actual Node/npm toolchain differs from the Phase 15 expectation and is recorded rather than hidden.

## Automated regression and package gate

- Python: 210 passed, one third-party deprecation warning.
- React/Vitest: 29 passed.
- TypeScript, Vite, translation-key-only, English/Hebrew parity, Hebrew RTL, Ruff, Cargo format/check: PASS.
- OpenAPI was exported twice byte-identically: `d1a6a3deb87c5ab1c900dfaf3a5e52446bc1d738fc0bc39d2ee5e7fee3d6eedc`.
- Migration matrix: empty and every 0001–0010 input reached 0011 with data preserved.
- Phase 8–15 packaged validators: `VERIFIED_WORKING`.
- Product Self-Test: PASS.
- Updater E2E: `VERIFIED_WORKING`; production updater remains not configured.
- Automated installed lifecycle: `VERIFIED_WORKING`.
- External product network: false.
- Owned MellowYak processes after automated validation: zero.
- One validator-only defect was closed before the checkpoint: the Phase 14 public-source validator now expects schema 0011.

## Final Gate A artifacts

| Artifact | Identity |
|---|---|
| Application | `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`; 869,120 KiB |
| Desktop executable | 23,023,088 bytes; `b16b911f39787b57fc051b467fe503cbd9273f2c3031e79051187b1037dfdc2f`; x86_64 |
| Engine | 15,812,960 bytes; `8f5f2b3e5cb4928cb1882904406360fc54bef7734777f7eb3fa214bc6b6f438b`; x86_64 |
| Browser | Google Chrome for Testing 151.0.7922.34; 623,316 KiB app bundle; x86_64; launcher `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb` |
| DMG | `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.5.0-preview.2_x64.dmg`; 398,650,246 bytes; `37c6962e2fa8869ed91cd7b93eceee746d8a7968d70c7ed88f68d804c0da9cb8` |
| Installed app | `/Applications/MellowYak.app`; desktop and engine hashes exactly match the build |

The previous installed application was retained as a recoverable timestamped backup. The DMG is ad-hoc signed, structurally valid, mounts read-only, contains the exact app, and detaches cleanly.

## Native notification acceptance lab

- An opt-in, local-only lab was added for macOS native banner evidence. It is disabled unless `MELLOWYAK_ACCEPTANCE_LAB=native-notifications` is present.
- The tray exposes a translated `Show acceptance notification` action only in that lab. Triggering it after the app is in the background avoids macOS suppressing a foreground application's own banner.
- English and Hebrew contain exact key parity for the trigger and all seven scenarios; no GUI text is hardcoded.
- Seven genuine Notification Center banners were generated and visually inspected: information, warning, high priority, critical regression, critical recovery, engine error, and regression resolved.
- Privacy-preserving banner-only crops are in `images/native-notifications/`. Full-desktop captures were moved to Trash and are not delivery evidence.
- These images are supporting acceptance evidence. They do not convert the operator-only physical matrix to PASS.

## Physical environment and preservation

- Physical evidence directory: `images/physical/`.
- Screen Recording permission: unavailable; the operator must use a real macOS screenshot shortcut.
- Accessibility permission: available, but automation is not accepted as a physical click.
- Original Start at Login: disabled.
- Original close-to-tray: enabled.
- Original Quiet Mode: disabled.
- Original Activity Mode: normal.
- Original power: AC, internal battery present and fully charged.
- Original retained product data: present; one project record; no private data is copied into this report.
- An isolated acceptance data root and disposable marked fixture are prepared outside the repository.

## Physical acceptance

Every physical result is recorded in `PHASE_16M_PHYSICAL_ACCEPTANCE.md` and `PHASE_16M_EVIDENCE_MANIFEST.json`. At this checkpoint every physical item is `NOT_RUN`; no deterministic image or Accessibility event is counted as physical evidence.

## Security, privacy, and data retention

- The committed checkpoint was scanned for credentials, keys, databases, user source, browser profiles, generated apps/DMGs, runtime data, private absolute user paths, and APC data; none were included.
- MellowYak remains loopback-only, local-first, account-free, prompt-blind, Git-optional, and explicit before Apply.
- The acceptance fixture is disposable and contains no customer source or credential.
- Original application preferences and data-retention state are recorded locally for restoration.

## Distribution boundary

Developer ID is `NOT_CONFIGURED`; notarization is `NOT_RUN`; stapling is `NOT_RUN`; production updater signing is `NOT_CONFIGURED`; trusted public download is `NOT_VERIFIED`. See `PHASE_16M_DISTRIBUTION_BOUNDARY.md`.

## Next authorized action

Complete the physical matrix one operator action at a time. Do not create the verified tag until every mandatory applicable physical test passes against these exact installed hashes.

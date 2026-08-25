# Phase 9 Technical Preview delivery

Date: 2026-08-25
Version: `0.2.0-preview.1`
Current-platform result: **VERIFIED_WORKING on Intel macOS**

This folder is the portable Phase 9 handoff. It contains implementation, package,
security, updater, migration, screenshot, and current-platform acceptance evidence.
Every automated product flow used isolated synthetic data. No real project was
connected, no source was uploaded, no public release was created, and no Git push
was performed.

## Read first

- [Implementation report](PHASE_9_IMPLEMENTATION_REPORT.md)
- [Verification evidence](PHASE_9_VERIFICATION_EVIDENCE.md)
- [Platform matrix](PHASE_9_PLATFORM_MATRIX.md)
- [Signing and notarization status](PHASE_9_SIGNING_AND_NOTARIZATION_STATUS.md)
- [Package inventory](PHASE_9_PACKAGE_INVENTORY.md)
- [Updater validation](PHASE_9_UPDATE_VALIDATION.md)
- [Security review](PHASE_9_SECURITY_REVIEW.md)
- [Real-project acceptance guide](REAL_PROJECT_ACCEPTANCE_GUIDE.md)
- [Technical Preview release checklist](TECHNICAL_PREVIEW_RELEASE_CHECKLIST.md)

## Machine-readable evidence

- `PHASE_8_PACKAGED_VALIDATION.json`
- `PHASE_9_PACKAGED_VALIDATION.json`
- `PHASE_9_UPDATER_VALIDATION.json`
- `PHASE_9_MIGRATION_MATRIX.json`
- `PHASE_9_SCREENSHOT_MANIFEST.json`

## Visual delivery

- [Screen guide](PHASE_9_SCREEN_GUIDE.md)
- [PDF screen guide](MellowYak-Phase-9-Screen-Guide.pdf)
- [`screenshots/`](screenshots/) — 24 deterministic English/Hebrew product states

## Honest release boundary

The locally built application and DMG are unsigned and unnotarized. Gatekeeper
therefore rejects them as public-distribution artifacts. Apple Silicon macOS,
Windows x64, and Linux x64 workflows are configured but were not executed in this
local no-push run. The production updater is implemented and signature-enforced,
but end-to-end public release delivery is not runtime verified.

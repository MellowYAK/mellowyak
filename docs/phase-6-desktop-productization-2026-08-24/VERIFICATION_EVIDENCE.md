# Phase 6 build and verification evidence

## Final operator instruction

The operator explicitly requested that no further automated tests be run and that final validation be performed manually. The checks below are the completed validation snapshot from before the final notification-category/privacy refinements. They are historical evidence, not a claim that a post-refinement automated regression pass occurred.

## Completed checks

- `python3 scripts/check_ui_translation_keys.py` → `UI_TRANSLATION_KEYS_ONLY`.
- `engine/.venv/bin/ruff check engine/src engine/tests` → all checks passed.
- `engine/.venv/bin/python -m pytest -q engine/tests` → 109 tests passed; one upstream TestClient deprecation warning.
- `cargo check` in `apps/desktop/src-tauri` → completed successfully.
- `npm run typecheck` in `apps/desktop` → completed successfully.
- `npm test -- --run` in `apps/desktop` → 12 tests passed in the earlier Phase 6 validation snapshot.
- `node scripts/capture_phase6_delivery.mjs` → 12 PNG screenshots, Markdown/HTML guide, and PDF generated from synthetic data.

## Final packaging evidence

- Build command: `npm run tauri build -- --bundles app,dmg`.
- macOS application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`.
- Application bundle size: 721,292 KiB.
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`.
- DMG size: 388,739,117 bytes.
- DMG SHA-256: `e9829a44b18244f25818efe004cd58a433e95b8436e4c12d04e7d9af6a1f1d88`.
- Desktop executable SHA-256: `6f4f1115fc33078eacbda8d6e6d97876c317fb2b5fcf61249f36b41d9432c5a8`.
- Installed application: `/Applications/MellowYak.app` (721,292 KiB).
- Recoverable previous installation: `/Applications/MellowYak-previous-20260824-213121-74ba3c.app`.
- The newly installed application was opened after installation. Functional acceptance remains manual by operator instruction.

## Git safety evidence

- Branch: `product/desktop-productization-tray-notifications`.
- Phase 5 base: `7fed80a136c52e00f15155f688bc099f925d9699`.
- Safety tag: `phase-5-verification-regression-gate-verified-2026-08-24`.
- Phase 6 is delivered as the single commit containing this evidence file; the exact resulting hash is reported in the final handoff response.
- No push or release was performed.

## Honest platform status

- macOS Intel local build and local `/Applications` installation: completed; manual functional acceptance pending.
- Windows: workflow-configured, not runtime-verified in this local run.
- Linux: workflow-configured, not runtime-verified in this local run.
- Signing/notarization/public release: not performed.

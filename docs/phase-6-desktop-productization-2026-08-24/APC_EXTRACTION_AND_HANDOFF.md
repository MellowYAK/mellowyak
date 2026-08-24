# APC extraction and Phase 6 handoff

## Read-only source boundary

APC was treated only as a read-only reference. No APC file, database, deployment, Git branch, or server was modified. MellowYak remains a separate public repository and desktop product with its own local engine, schema, UI, packaging, tests, and release path.

## Lessons retained

- Local bridge/sidecar lifecycle informed the authenticated loopback engine and explicit process ownership.
- Project-state and operational-history lessons informed durable project lifecycle and alerts.
- Browser/runtime and evidence lessons from earlier phases remain behind explicit per-project capability checks.
- Completion/result history informed durable gate and regression alerts rather than transient toast-only state.
- Global project management lessons informed the Command Center and Projects screen.

## What was rebuilt cleanly

- Tauri tray/menu-bar integration, background close behavior, single-instance handling, native notifications, and autostart are new Rust/Tauri implementations.
- Alert, preference, quiet-mode, lifecycle, and disconnection records are new SQLAlchemy/Alembic models.
- Project disconnect, reconnect, relocate, and local-data deletion are new source-safe engine services.
- Command Center, Projects, Alerts, Settings, and Capabilities are new React components using MellowYak translation catalogs.
- No APC PHP route, MariaDB schema, Docker topology, remote control panel, credentials, private host address, or APC UI assets were copied.

## Handoff map

- Engine domain: `engine/src/mellowyak_engine/productization/`
- Migration: `engine/alembic/versions/0006_desktop_productization.py`
- API contracts: `engine/src/mellowyak_engine/api/app.py`, `api/schemas.py`
- Desktop API client: `apps/desktop/src/api.ts`
- Product screens: `apps/desktop/src/ProductScreens.tsx`
- Global integration: `apps/desktop/src/App.tsx`
- Product styling: `apps/desktop/src/product.css`
- GUI translations: `apps/desktop/src/i18n.ts`
- Native shell: `apps/desktop/src-tauri/src/lib.rs`
- Native tray translations: `apps/desktop/src-tauri/i18n/`
- Tests: `engine/tests/test_phase6_desktop_productization.py`
- Screenshot generator: `scripts/capture_phase6_delivery.mjs`

## Continuation rule

Continue on `product/desktop-productization-tray-notifications` from the single Phase 6 commit. Do not modify APC for MellowYak work. Preserve the translation-only GUI checker, local-data separation, source-safe deletion test, and explicit limitation language before adding Phase 7 features.

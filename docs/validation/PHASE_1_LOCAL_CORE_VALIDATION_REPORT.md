# Phase 1 local-core validation report

- Date: 2026-08-23
- Phase: Safe Extraction Boundary and Local Core Foundation
- Platform exercised: macOS 26.5.2, x86_64
- Result: VERIFIED_WORKING for the current-platform local foundation

## Starting Git state and safety actions

The MellowYak worktree was clean on `main` at `87ef4e9669c1ec76503860b44a24f9000cfa0684` (`docs: define MellowYak product contract`). `origin` remained `https://github.com/MellowYAK/mellowyak.git`. The recent history contained that commit and `4e8fa60 Initial commit`.

An annotated local recovery tag, `pre-mellowyak-local-core-2026-08-23`, was created at the clean starting commit. Local branch `product/local-core-foundation` was created and used. No remote, history, branch, tag, package or release was pushed. The sibling APC checkout remained read-only source material; no implementation command wrote to it.

## Implemented architecture

| Area | Status | Evidence |
|---|---|---|
| Tauri 2 / React / TypeScript / Vite desktop | VERIFIED_WORKING | Production frontend and Rust shell compiled; packaged app launched. |
| Managed Python sidecar | VERIFIED_WORKING | PyInstaller binary embedded in `.app` and DMG; stdout handshake and authenticated live API exercised. |
| Local process security | VERIFIED_WORKING | `lsof` showed only `TCP 127.0.0.1:56574 (LISTEN)` for final launch; wildcard bind and auth/origin negatives pass. |
| SQLite / SQLAlchemy / Alembic | VERIFIED_WORKING | Platform database created with `0001_local_core`, one installation identity and WAL/foreign-key/busy-timeout checks. |
| Restart persistence | VERIFIED_WORKING | Packaged app launched twice and retained the same installation identity; final database contained one installation and three engine runs. |
| First Setup UI | VERIFIED_WORKING | React tests render live contract values; packaged desktop window and engine launched together. Automated display screenshot was unavailable. |
| macOS `.app` and `.dmg` | VERIFIED_WORKING | Both built; mounted DMG contains desktop binary, engine binary, plist and icon. |
| Windows NSIS and Linux AppImage/deb | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Platform Tauri configs and CI matrix exist; not run locally. |

## Files created or modified

Root and policy: `.gitignore`, `README.md`, `PROJECT_INDEX.md`, `PRIVACY.md`, `SECURITY.md`, `CONTRIBUTING.md`.

Architecture/migration/validation: `docs/architecture/ADR-0001-local-first-desktop.md`, `docs/architecture/ADR-0002-local-process-security.md`, `docs/architecture/ADR-0003-apc-extraction-policy.md`, `docs/migration/APC_TO_MELLOWYAK_MATRIX.md`, `docs/migration/APC_EXTRACTION_BOUNDARY.md`, `docs/OPEN_SOURCE_LICENSE_DECISION.md`, and this report.

Engine: `engine/pyproject.toml`, `engine/alembic.ini`, `engine/alembic/env.py`, `engine/alembic/script.py.mako`, `engine/alembic/versions/0001_local_core.py`, all `__init__.py` files under `engine/src/mellowyak_engine/`, `api/app.py`, `api/schemas.py`, `core/lifecycle.py`, `core/logging.py`, `db/database.py`, `db/models.py`, `main.py`, `security/auth.py`, `settings/config.py`, `storage/paths.py`, plus `engine/tests/conftest.py`, `test_security_and_api.py`, `test_sidecar_lifecycle.py`, and `test_storage_and_database.py`.

Desktop: `apps/desktop/index.html`, `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx`, `src/api.ts`, `src/styles.css`, `src/test/setup.ts`, `src-tauri/Cargo.toml`, `Cargo.lock`, `build.rs`, `src/main.rs`, `src/lib.rs`, `capabilities/default.json`, `tauri.conf.json`, and the three platform files `tauri.macos.conf.json`, `tauri.windows.conf.json`, `tauri.linux.conf.json`. Desktop icons are `icons/32x32.png`, `128x128.png`, `128x128@2x.png`, `icon.png`, `icon.icns`, and `icon.ico`.

Contracts/build: `packages/contracts/openapi.json`, `packages/contracts/README.md`, `scripts/export_openapi.py`, `scripts/build_engine.py`, executable `scripts/dev.py`, `.github/workflows/ci.yml`, `.github/workflows/package-smoke.yml`, and replaceable `assets/brand/mellowyak-mark.svg`.

Generated TypeScript, Tauri schemas, sidecar binaries, build directories, installers, virtual environments, caches and local data are ignored and are not part of the commit.

## Commands and exact results

```text
engine/.venv/bin/pytest
17 passed, 1 Starlette/httpx deprecation warning

npm test
2 tests passed, 1 file passed

npm run typecheck
passed

npm run build
passed; 32 modules transformed

ruff check engine scripts
All checks passed

ruff format --check engine scripts
26 files already formatted

cargo fmt --check
passed

cargo check
passed (dev profile)

python scripts/build_engine.py
passed; x86_64-apple-darwin one-file sidecar produced

CI=true npm run tauri build -- --bundles dmg
passed

npm run tauri build -- --bundles app
passed
```

The first DMG attempt without non-interactive mode failed inside Tauri's Finder-layout script. It was not reported as success. Re-running with `CI=true` caused the official bundler to use its non-interactive path and completed successfully. The final DMG SHA-256 is `e69a8c9266b33fb52d158f0408a956323dcd7837864350c46486835ee1f57473` and its displayed size is 25 MB.

## Runtime evidence

- Data root: `~/Library/Application Support/MellowYak` (reported here in platform-relative form to avoid committing a user path).
- Database: `database/mellowyak.sqlite3`.
- Schema: `0001_local_core`.
- Logical folders created: database, evidence, projects, cache, logs, runtime and backups.
- Final live listener: IPv4 loopback only, dynamic port `56574` for that launch.
- Live health: `status=ready`, `mode=local`, `database_status=ready`, `cloud_connected=false`, `outbound_network_enabled=false`.
- DMG mount inspection found `MellowYak.app/Contents/MacOS/mellowyak-desktop` and bundled `mellowyak-engine`.
- Quitting the desktop left no `mellowyak-engine` process.

## Security and privacy evidence

Automated tests reject missing and invalid tokens, accept a valid token, reject an unapproved origin, reject `0.0.0.0`, verify token/path absence from structured logs, scan engine/UI/Rust source for known cloud/analytics endpoints and `localStorage`, and fail on any startup socket connection attempt. The packaged sidecar was also queried with its launch token; its structured ready log contained neither the token nor data path.

No connector, account, cloud sync, analytics, remote telemetry, source upload or outbound client exists. The unauthenticated `/handshake` response is deliberately minimal and contains only running/local/auth-required state; all application endpoints require the launch token.

## Unrun checks and limitations

- Windows NSIS and Linux AppImage/deb builds are UNKNOWN until their CI jobs execute.
- Python 3.12 CI compatibility is IMPLEMENTED_NOT_RUNTIME_VERIFIED locally; the exercised interpreter was Python 3.11.5.
- macOS package signing, notarization, clean-machine Gatekeeper installation and automatic updating are not implemented.
- The produced macOS artifacts are local generated outputs, not committed or published releases.
- Automated screen capture failed because the current execution session could not create an image from the display. UI contract rendering passed and the native application launched, but no screenshot is claimed.
- The Starlette TestClient emits one dependency deprecation warning; tests still pass.
- The placeholder yak mark is replaceable and is not final brand approval.
- No repository license exists; distribution rights remain an owner/legal decision.

## Blockers and next prerequisites

There is no blocker to closing Phase 1. Before a public release, execute all platform package workflows, test on clean machines, select a license, complete signing/notarization, and perform an independent security review.

Phase 2 must be a separate change. Its exact scope is Add Project, Git repository detection/observation, initial source scan, selective APC Project MAP extraction, and initial Impact Map foundations. It must not weaken the Phase 1 privacy/process boundary.

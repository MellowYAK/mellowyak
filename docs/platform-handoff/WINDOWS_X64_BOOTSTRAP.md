# MellowYak Windows x64 Bootstrap and Native Acceptance Handoff

## 1. Immutable source checkpoint

- Repository: `https://github.com/MellowYAK/mellowyak.git`
- Source tag: `phase-16m-intel-mac-technical-preview-accepted-with-limits-2026-08-28`
- Verified shipping-source commit: `a24d9f7e252c71f4d389493988ffd38075783807`
- Product version: `0.5.0-preview.3`
- Database head: `0011_baseline_lock_and_local_proof`
- Deterministic OpenAPI SHA-256: `608ced66dbc65676ab44abae5ed97f070b1ee41af7fc7db127fa35623a66949f`

The annotated tag is the complete shared-source and documentation checkpoint. The shipping application source is anchored at the commit above; subsequent commits through the tag contain closure documentation and PDF tooling, not shipping-source changes.

```powershell
git clone https://github.com/MellowYAK/mellowyak.git
Set-Location mellowyak
git checkout phase-16m-intel-mac-technical-preview-accepted-with-limits-2026-08-28
git merge-base --is-ancestor a24d9f7e252c71f4d389493988ffd38075783807 HEAD
```

## 2. Shared product architecture

MellowYak uses one shared repository: a React/TypeScript interface inside a Tauri desktop shell, a local Python/FastAPI engine, SQLite/Alembic durable state, a generated OpenAPI TypeScript contract, a managed Chromium launcher for browser-backed evidence, and platform-specific packaging/lifecycle adapters. Windows work must extend this source rather than fork the engine or product semantics.

## 3. Product invariants

Windows must preserve all of these invariants:

- Local-first and account-free operation.
- A loopback-only authenticated engine.
- Git is optional; local projects remain supported.
- Prompt-blind evidence and verification.
- Strict project isolation and exact source identity.
- Unknown remains unknown; absence of evidence is never promoted to PASS.
- No silent baseline replacement.
- No automatic Apply; Apply requires explicit confirmation.
- A Safety Snapshot and immutable journal precede mutation.
- Live verification follows Apply.
- Failed post-checks trigger byte-identical rollback.
- Project source is never uploaded.
- GUI text is translation-key-only.
- English/Hebrew catalog parity and Hebrew RTL are mandatory.
- Yak Receipts are immutable.
- No platform-support claim is made without native platform evidence.

## 4. Shared and platform-specific responsibilities

Shared code owns the product model, API, migrations, project identity, evidence, regression analysis, Apply/rollback transaction, receipts, localization catalogs, and UI behavior. Windows-specific code owns native paths, process supervision, single-instance activation, window/tray behavior, startup registration, notifications and activation routing, WebView2 integration, installer/uninstaller behavior, native filesystem link/reparse-point behavior, signing, updater trust, and Windows lifecycle evidence.

Do not modify shared semantics merely to accommodate a Windows wrapper. Any platform adapter must preserve the API and schema identities above.

## 5. Toolchain and bootstrap

Pinned toolchains are Node.js `22`, Python `3.12`, and Rust `1.98.0`. Use 64-bit Windows with PowerShell, Git, Python, Node/npm, Rustup/Cargo, Microsoft Visual Studio 2022 Build Tools with the C++ workload, and WebView2.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/bootstrap-windows.ps1 -NonInteractive
```

If prerequisites are missing, rerun with `-InstallMissing`, reopen PowerShell, and then run the non-interactive bootstrap again.

## 6. Source verification commands

```powershell
$Python = "engine/.venv/Scripts/python.exe"
& $Python -m pytest engine
& $Python -m ruff check engine scripts
& $Python -m ruff format --check engine scripts
& $Python scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate
& $Python scripts/check_ui_translation_keys.py
npm --prefix apps/desktop test
npm --prefix apps/desktop run typecheck
npm --prefix apps/desktop run build
cargo fmt --check --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
& $Python scripts/validate_migration_matrix.py
git diff --check
```

The frozen Intel Mac source gate recorded 211 Python tests, 30 React tests, exact English/Hebrew parity, Hebrew RTL, deterministic OpenAPI output, and successful empty/0001-0010 migrations to schema 0011. Windows must rerun these on Windows rather than inherit a platform PASS.

## 7. Existing Windows build path and current status

- `scripts/bootstrap-windows.ps1`: installs/prepares the exact source dependencies.
- `scripts/build-platform.ps1`: stages Chromium and the PyInstaller engine, then produces NSIS by default or MSI on request.
- `scripts/validate-windows.ps1`: verifies clean source identity, contracts, localization, TypeScript, Rust, sidecar presence, installer presence, and writes an artifact manifest.
- `apps/desktop/src-tauri/tauri.windows.conf.json`: selects NSIS, disables downgrade installation, and embeds the WebView2 Evergreen bootstrapper.
- `.github/workflows/windows-acceptance.yml`: accepts an exact `source_ref`, builds Windows x64, runs source/package validation, and uploads the installer and manifest.
- `.github/workflows/desktop-build.yml`: contains a Windows build lane from the same commit.

Current status: wrappers and CI definitions are present and source-reviewed, but no Windows package or lifecycle result from this checkpoint is accepted yet. Status remains `NOT_YET_NATIVELY_ACCEPTED` until Windows evidence exists.

Build and package-validation entry points:

```powershell
./scripts/build-platform.ps1 -Platform windows-x64 -Bundle nsis
./scripts/validate-windows.ps1 -ExpectedCommit (git rev-parse HEAD)
```

Do not pass `-LifecycleVerified` until the installed native lifecycle scope below has actually passed.

## 8. Native Windows acceptance scope

At minimum, record evidence for:

1. NSIS installation, first launch, uninstall, retained-data reinstall, and clean removal.
2. Exact installed desktop, engine, browser, installer, source commit, schema, and API identities.
3. One desktop process and one owned engine; second launch focuses the existing window.
4. Window close policy, tray restore, tray Quit, application Quit, crash cleanup, and supervised engine restart.
5. Startup enabled/disabled across real sign-out/sign-in and restart.
6. Windows notifications for information, warning, high, critical, recovery, engine error, and resolved states; click routing and stale-destination fallback.
7. Quiet Mode suppression while in-app evidence persists, followed by restored delivery.
8. Sleep/wake, lock/unlock, AC/battery transition, and queued-work recovery.
9. Local project add, disconnect, relocate/reconnect, identity mismatch rejection, and Windows link/reparse-point handling.
10. Full Apply transaction: explicit confirmation, Safety Snapshot, journal, successful live verification, forced post-check failure, and byte-identical rollback.
11. Updater success plus tamper, wrong-key, incomplete, and downgrade rejection without data or identity loss.
12. Loopback-only engine binding, authentication, no external product network, privacy scans, and cleanup.

Keep native automation, human physical, visual, functional, and cleanup axes independent.

## 9. Signing, SmartScreen, and updater boundary

Unsigned or locally signed installers are development artifacts only. Public Windows readiness requires an organization-controlled code-signing certificate, timestamped signatures on the installer and executables, SmartScreen/reputation validation, production Tauri updater signing keys, a trusted HTTPS update channel, and verification over the exact published bytes. Never commit private signing keys or passwords. Do not claim public Windows readiness from a successful local NSIS build.

## 10. CI/CD plan

1. Dispatch `windows-acceptance.yml` with the annotated source tag as `source_ref`.
2. Confirm the workflow resolves the exact tag and records the resulting commit in its manifest.
3. Keep source/package CI separate from native installed lifecycle acceptance.
4. Add Windows-native lifecycle and updater validators before promoting the manifest to `VERIFIED_WORKING`.
5. Upload immutable manifests and checksums keyed by commit; never upload databases, profiles, customer projects, or private acceptance roots.
6. Introduce signing secrets only in protected CI environments.
7. Publish installers or updater metadata only after signing, SmartScreen, updater-trust, and native acceptance gates pass.

## 11. Linux and Apple Silicon non-regression boundary

Linux x64 and Apple Silicon build paths exist in shared CI, but neither platform is natively accepted by this checkpoint. Windows changes must remain behind platform adapters, preserve shared tests/contracts/localization, and avoid declaring those platforms supported. Any change to shared engine, schema, API, Apply/rollback, project identity, or UI behavior requires cross-platform source gates and later native evidence on each claimed platform.

## 12. Handoff verdict

- Intel Mac product: `INTEL_MAC_TECHNICAL_PREVIEW_ACCEPTED_WITH_LIMITS`.
- Intel Mac automated/functional closure: `CLOSED`.
- Intel Mac human physical acceptance: `DEFERRED_POST_PREVIEW`.
- Public Mac distribution: `PUBLIC_MAC_DISTRIBUTION_BLOCKED`.
- Windows x64 implementation: `AUTHORIZED`.
- Windows x64 native acceptance: `NOT_YET_NATIVELY_ACCEPTED`.
- Linux x64 and Apple Silicon: `NOT_YET_NATIVELY_ACCEPTED`.
